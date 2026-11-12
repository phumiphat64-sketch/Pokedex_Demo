"""Option 2 (smart local LLM via Ollama).
Idea: the LLM only translates the question into JSON; the Pandas functions in tools.py compute the answer
(the LLM never writes code or guesses numbers, which is safer and more accurate).
Then the LLM rewrites the answer in a friendly Pokédex style."""
from __future__ import annotations

import json

import pandas as pd

from .data_loader import ALL_TYPES, RANKABLE
from .router_light import resolve_name
from .tools import Answer

try:
    import ollama
except ImportError:  # pragma: no cover
    ollama = None

DEFAULT_MODEL = "qwen2.5:7b"   # smaller machine / no GPU: "qwen2.5:3b" or "llama3.2:3b"

SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": ["profile", "compare", "rank", "weak_to", "help"]},
        "names": {"type": "array", "items": {"type": "string"}},
        "types": {"type": "array", "items": {"type": "string", "enum": ALL_TYPES}},
        "filter_types": {"type": "array", "items": {"type": "string", "enum": ALL_TYPES}},
        "stat": {"type": "string", "enum": RANKABLE},
        "n": {"type": "integer"},
        "ascending": {"type": "boolean"},
        "multiplier": {"type": "number"},
        "generation": {"type": "integer"},
        "legendary": {"type": "boolean"},
    },
    "required": ["intent"],
}

ROUTER_SYSTEM = f"""You convert a user's Pokédex question (Thai or English) into JSON. Output JSON only.
intent:
- profile: facts / weaknesses of ONE named Pokémon (names=[that name])
- compare: 2-3 named Pokémon (names=[...])
- rank: top-N / lowest-N by a stat, optionally filtered. stat is one of {RANKABLE}.
  types = Pokémon type filter, ascending=true only if user wants lowest/slowest/lightest.
- weak_to: Pokémon that are weak to an ATTACKING type. types=[the attacking type];
  multiplier=4 or 2 if the user says "4 เท่า"/"x4" or "2 เท่า"; filter_types = type of the Pokémon (if the user gives one).
- help: anything else (greetings, unrelated questions).
Types are English lowercase: {ALL_TYPES}. Thai hints: ไฟ=fire น้ำ=water หญ้า=grass ไฟฟ้า=electric น้ำแข็ง=ice
ต่อสู้=fighting พิษ=poison ดิน=ground บิน=flying จิต=psychic แมลง=bug หิน=rock ผี=ghost มังกร=dragon มืด=dark เหล็ก=steel นางฟ้า=fairy.
Use null-free JSON: omit fields that do not apply."""

NARRATE_SYSTEM = (
    "You are Rotom Pokédex. Answer in English, briefly, in a friendly Pokédex-encyclopedia tone. "
    "Use ONLY the data provided: never add numbers or facts that are not in the data. "
    "If a table is provided, summarize the highlights instead of copying the whole table."
)


def _check_ollama():
    if ollama is None:
        raise RuntimeError("The ollama library is not installed (pip install ollama) or the Ollama app is not running")


def parse_with_llm(df: pd.DataFrame, text: str, model: str = DEFAULT_MODEL) -> dict:
    _check_ollama()
    resp = ollama.chat(
        model=model,
        messages=[{"role": "system", "content": ROUTER_SYSTEM}, {"role": "user", "content": text}],
        format=SCHEMA,
        options={"temperature": 0},
    )
    return sanitize(df, json.loads(resp["message"]["content"]))


def sanitize(df: pd.DataFrame, raw: dict) -> dict:
    """Always validate LLM output before use: names must exist in the CSV and values must be in the allowed range."""
    names = [resolve_name(df, n) for n in raw.get("names", []) if isinstance(n, str)]
    q = {
        "intent": raw.get("intent", "help"),
        "names": [n for n in names if n],
        "types": [t for t in raw.get("types", []) if t in ALL_TYPES],
        "filter_types": [t for t in raw.get("filter_types", []) if t in ALL_TYPES],
        "stat": raw.get("stat") if raw.get("stat") in RANKABLE else None,
        "n": max(1, min(int(raw.get("n") or 5), 50)),
        "ascending": bool(raw.get("ascending", False)),
        "multiplier": raw.get("multiplier") if raw.get("multiplier") in (0.25, 0.5, 2, 4, 2.0, 4.0) else None,
        "generation": raw.get("generation") if raw.get("generation") in range(1, 8) else None,
        "legendary": True if raw.get("legendary") else None,
    }
    return q


def narrate(question: str, ans: Answer, model: str = DEFAULT_MODEL) -> str:
    _check_ollama()
    facts = ans.text
    if ans.table is not None:
        facts += "\n\nTable:\n" + ans.table.head(30).to_string(index=False)
    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": NARRATE_SYSTEM},
            {"role": "user", "content": f"Question: {question}\n\nPokédex data:\n{facts}"},
        ],
        options={"temperature": 0.3},
    )
    return resp["message"]["content"]
