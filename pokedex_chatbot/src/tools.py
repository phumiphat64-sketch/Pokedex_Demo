"""Lookup / ranking / weakness functions — answers are computed from the DataFrame (an LLM never guesses numbers)."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .data_loader import (RANKABLE, STAT_LABEL, STATS, TYPE_TO_AGAINST,
                          fmt, weakness_profile)


@dataclass
class Answer:
    text: str                                        # Markdown answer (facts only)
    table: pd.DataFrame | None = None                # table shown under the answer
    radar: list[str] = field(default_factory=list)   # Pokémon names to draw on the radar chart


def get_row(df: pd.DataFrame, name: str):
    r = df[df["name_key"] == name.lower()]
    return None if r.empty else r.iloc[0]


# ---------- 1) Single-Pokémon lookup ----------
MULT_LABELS = [
    (4.0, "Very weak (×4)"), (2.0, "Weak (×2)"),
    (0.5, "Resists (×0.5)"), (0.25, "Strongly resists (×0.25)"), (0.0, "Immune (×0)"),
]


def weakness_text(row: pd.Series) -> str:
    g = weakness_profile(row)
    lines = [f"- **{label}:** {', '.join(g[m])}" for m, label in MULT_LABELS if m in g]
    return "\n".join(lines)


def profile(df: pd.DataFrame, name: str) -> Answer:
    r = get_row(df, name)
    if r is None:
        return Answer(f"Pokémon “{name}” was not found in pokemon.csv.")
    gender = "Genderless" if r["is_genderless"] else f"{r['percentage_male']:g}% male"
    legend = " · ⭐ Legendary" if r["is_legendary"] else ""
    stats = " | ".join(f"{STAT_LABEL[s]} **{int(r[s])}**" for s in STATS)
    text = (
        f"### #{int(r['pokedex_number']):03d} {r['name']} ({r['romaji']} / {r['kana']}){legend}\n"
        f"{r['classfication']} · Gen {int(r['generation'])} · Type: **{r['types']}**\n\n"
        f"- Height {fmt(r['height_m'], ' m')} · Weight {fmt(r['weight_kg'], ' kg')} · Gender: {gender}\n"
        f"- Abilities: {', '.join(r['abilities'])}\n"
        f"- Capture rate: {int(r['capture_rate_num'])} · Base egg steps: {int(r['base_egg_steps'])}\n"
        f"- {stats} | Base Total **{int(r['base_total'])}**\n\n"
        f"**Weaknesses / resistances (attacking types vs {r['name']})**\n{weakness_text(r)}"
    )
    return Answer(text, radar=[r["name"]])


def compare(df: pd.DataFrame, names: list[str]) -> Answer:
    rows = [get_row(df, n) for n in names[:3]]
    rows = [r for r in rows if r is not None]
    if len(rows) < 2:
        return Answer("Please name at least two Pokémon to compare.")
    table = pd.DataFrame(
        {r["name"]: [r["types"]] + [int(r[s]) for s in STATS] + [int(r["base_total"])] for r in rows},
        index=["Types"] + [STAT_LABEL[s] for s in STATS] + ["Base Total"],
    ).astype(str)
    a, b = rows[0], rows[1]
    lead = [f"{STAT_LABEL[s]}: {(a if a[s] > b[s] else b)['name']}" for s in STATS if a[s] != b[s]]
    text = f"### Compare {' vs '.join(r['name'] for r in rows)}\n"
    if lead:
        text += f"Leader per stat ({a['name']} vs {b['name']}) — " + " · ".join(lead)
    return Answer(text, table=table.reset_index(names="Stat"), radar=[r["name"] for r in rows])


# ---------- 2) Comparison / ranking ----------
def _filter(df, types=None, generation=None, legendary=None):
    d = df
    if types:
        if len(types) == 1:
            d = d[(d["type1"] == types[0]) | (d["type2"] == types[0])]
        else:  # two types given = must be exactly that pair
            d = d[d.apply(lambda r: set(types[:2]) == {r["type1"], r["type2"]}, axis=1)]
    if generation:
        d = d[d["generation"] == generation]
    if legendary is not None:
        d = d[d["is_legendary"] == legendary]
    return d


def rank(df, stat="base_total", n=5, ascending=False, types=None, generation=None, legendary=None) -> Answer:
    if stat not in RANKABLE:
        return Answer(f"Cannot rank by “{stat}” yet. Try one of: {', '.join(RANKABLE)}")
    d = _filter(df, types, generation, legendary).dropna(subset=[stat])
    d = d.sort_values([stat, "base_total"], ascending=[ascending, ascending]).head(n)
    cond = []
    if types: cond.append("type " + "/".join(types))
    if generation: cond.append(f"Gen {generation}")
    if legendary: cond.append("Legendary")
    title = f"Top {n} {'lowest' if ascending else 'highest'} {STAT_LABEL[stat]}" + (f" ({', '.join(cond)})" if cond else "")
    if d.empty:
        return Answer(f"{title}: no Pokémon match these filters.")
    cols = ["pokedex_number", "name", "types", stat] + (["base_total"] if stat != "base_total" else [])
    return Answer(f"### {title}", table=d[cols].reset_index(drop=True), radar=list(d["name"].head(3)))


# ---------- 3) Weakness analysis ----------
def weak_to(df, attack_type: str, multiplier: float | None = None, n: int = 30, filter_types=None) -> Answer:
    col = TYPE_TO_AGAINST[attack_type]
    base = _filter(df, filter_types)
    d = base[base[col] == multiplier] if multiplier else base[base[col] >= 2]
    d = d.sort_values([col, "base_total"], ascending=[False, False])
    label = f"×{multiplier:g}" if multiplier else "×2 or more"
    who = f"{'/'.join(filter_types)}-type " if filter_types else ""
    title = f"{len(d)} {who}Pokémon weak to {attack_type} ({label})"
    if d.empty:
        return Answer(title)
    shown = d.head(n)
    note = f" (showing first {n})" if len(d) > n else ""
    return Answer(f"### {title}{note}",
                  table=shown[["pokedex_number", "name", "types", col, "base_total"]].reset_index(drop=True))


HELP = (
    "Try asking things like:\n"
    "- `Show info and weaknesses of Bulbasaur`\n"
    "- `Top 5 fire-type Pokémon by Speed`\n"
    "- `Which Pokémon are weak to water 4x?`\n"
    "- `Compare Pikachu and Raichu`"
)


def execute(df: pd.DataFrame, q: dict) -> Answer:
    """Take a query dict (from the light router or the LLM) and call the function matching its intent."""
    intent, names = q.get("intent"), q.get("names") or []
    if intent == "profile" and names:
        return profile(df, names[0])
    if intent == "compare" and len(names) >= 2:
        return compare(df, names)
    if intent == "weak_to" and q.get("types"):
        return weak_to(df, q["types"][0], q.get("multiplier"), filter_types=q.get("filter_types"))
    if intent == "rank":
        return rank(df, q.get("stat") or "base_total", q.get("n") or 5, bool(q.get("ascending")),
                    q.get("types"), q.get("generation"), q.get("legendary"))
    return Answer("Sorry, I didn't understand that question.\n\n" + HELP)
