"""Option 1 (lightweight, no GPU): rules + fuzzy matching turn a question into a query dict."""
from __future__ import annotations

import difflib
import re

import pandas as pd

from .vocab import (ASC_WORDS, LEGEND_WORDS, STAT_WORDS, STOP_WORDS, TYPE_WORDS,
                    WEAK_WORDS, scan)

try:  # rapidfuzz is faster; if it is not installed we fall back to Python's built-in difflib
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover
    fuzz = process = None


def _fuzzy_name(token: str, keys: list[str]) -> str | None:
    if process is not None:
        hit = process.extractOne(token, keys, scorer=fuzz.ratio, score_cutoff=82)
        return hit[0] if hit else None
    hit = difflib.get_close_matches(token, keys, n=1, cutoff=0.84)
    return hit[0] if hit else None


def resolve_name(df: pd.DataFrame, name: str) -> str | None:
    """A typed name (possibly misspelled) -> the real name in the CSV."""
    keys = df["name_key"].tolist()
    k = name.lower().strip()
    if k not in keys:
        k = _fuzzy_name(k, keys)
        if k is None:
            return None
    return df.loc[df["name_key"] == k, "name"].iloc[0]


def extract_names(df: pd.DataFrame, text: str, limit: int = 3) -> list[str]:
    low, keys = text.lower(), df["name_key"].tolist()
    found: list[tuple[int, str]] = []
    # 1) exact match (longest names first, e.g. 'Mr. Mime', 'Tapu Koko')
    for k in sorted(keys, key=len, reverse=True):
        m = re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", low)
        if m:
            found.append((m.start(), k))
            low = low[:m.start()] + " " * (m.end() - m.start()) + low[m.end():]
    # 2) small typos, e.g. 'bulbasur', 'pikacu'
    for m in re.finditer(r"[a-z][a-z'.\-]{3,}", low):
        tok = m.group()
        if tok in STOP_WORDS:
            continue
        k = _fuzzy_name(tok, keys)
        if k:
            found.append((m.start(), k))
    found.sort()
    out: list[str] = []
    for _, k in found:
        real = df.loc[df["name_key"] == k, "name"].iloc[0]
        if real not in out:
            out.append(real)
    return out[:limit]


def parse(df: pd.DataFrame, text: str) -> dict:
    low = text.lower()
    q = {"intent": "help", "names": extract_names(df, text), "types": [], "stat": None,
         "n": None, "ascending": False, "multiplier": None, "generation": None, "legendary": None,
         "filter_types": []}

    stats, stat_masked = scan(low, STAT_WORDS)  # scan stats first so 'น้ำหนัก' (weight) is not mistaken for 'น้ำ' (water)
    types, masked = scan(stat_masked, TYPE_WORDS)
    legend, _ = scan(masked, {"x": LEGEND_WORDS})
    q["stat"] = stats[0] if stats else None
    q["types"] = types
    q["legendary"] = True if legend else None
    q["ascending"] = any(w in low for w in ASC_WORDS)

    if m := re.search(r"(?:gen(?:eration)?|เจน(?:เนอเรชั่น)?|ภาค|รุ่น)\s*([1-7])", low):
        q["generation"] = int(m.group(1))
    if m := re.search(r"top\s*(\d+)|(\d+)\s*(?:อันดับ|ตัว|อัน|pokemon|pokémon|heaviest|lightest|fastest|slowest|strongest|highest|lowest)", low):
        q["n"] = min(int(m.group(1) or m.group(2)), 50)
    if m := re.search(r"(0\.25|0\.5|4|2)\s*(?:เท่า|x|×|times)|[x×]\s*(0\.25|0\.5|4|2)", low):
        q["multiplier"] = float(m.group(1) or m.group(2))
    elif "สี่เท่า" in low:
        q["multiplier"] = 4.0
    elif "สองเท่า" in low:
        q["multiplier"] = 2.0

    # (Thai keywords below are intentional: they let Thai questions work alongside English ones)
    weak = any(w in low for w in WEAK_WORDS)
    if len(q["names"]) >= 2:
        q["intent"] = "compare"
    elif len(q["names"]) == 1:
        q["intent"] = "profile"
    elif q["types"] and weak:
        # "fire-type that is weak to water": types before the weak-word filter the Pokémon, the type after is the attacker
        pos = min(low.find(w) for w in WEAK_WORDS if w in low)
        before, _ = scan(stat_masked[:pos], TYPE_WORDS)
        after, _ = scan(stat_masked[pos:], TYPE_WORDS)
        q["intent"] = "weak_to"
        q["types"], q["filter_types"] = (after or before)[:1], (before if after else [])
    elif q["stat"] or q["types"] or q["generation"] or q["legendary"]:
        q["intent"] = "rank"
    return q
