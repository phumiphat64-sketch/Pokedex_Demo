"""Load and clean pokemon.csv (100% local)."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import numpy as np
import pandas as pd

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_PATH = _DATA_DIR / "pokemon_updated.csv" if (_DATA_DIR / "pokemon_updated.csv").is_file() else _DATA_DIR / "pokemon.csv"

# The column is `against_fight`, but type1/type2 use the value 'fighting', so we need a mapping.
AGAINST_TO_TYPE = {
    "bug": "bug", "dark": "dark", "dragon": "dragon", "electric": "electric",
    "fairy": "fairy", "fight": "fighting", "fire": "fire", "flying": "flying",
    "ghost": "ghost", "grass": "grass", "ground": "ground", "ice": "ice",
    "normal": "normal", "poison": "poison", "psychic": "psychic", "rock": "rock",
    "steel": "steel", "water": "water",
}
AGAINST_COLS = [f"against_{k}" for k in AGAINST_TO_TYPE]
ALL_TYPES = list(AGAINST_TO_TYPE.values())
TYPE_TO_AGAINST = {t: f"against_{k}" for k, t in AGAINST_TO_TYPE.items()}

STATS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
STAT_LABEL = {
    "hp": "HP", "attack": "Attack", "defense": "Defense",
    "sp_attack": "Sp. Attack", "sp_defense": "Sp. Defense", "speed": "Speed",
    "base_total": "Base Total", "weight_kg": "Weight (kg)", "height_m": "Height (m)",
}
RANKABLE = STATS + ["base_total", "weight_kg", "height_m"]


def _split_japanese(s) -> tuple[str, str]:
    """'Fushigidaneフシギダネ' -> ('Fushigidane', 'フシギダネ')"""
    if not isinstance(s, str):
        return "", ""
    m = re.match(r"^([^\u3040-\u30ff\u4e00-\u9fff]*)(.*)$", s)
    return m.group(1).strip(), m.group(2).strip()


def _first_int(v) -> float:
    """capture_rate is a string; Minior = '30 (Meteorite)255 (Core)' -> use the first number."""
    m = re.search(r"\d+", str(v))
    return float(m.group()) if m else np.nan


def load_data(path: Path | str = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)

    df["name_key"] = df["name"].str.lower()

    # type2: NaN means "no second type" (not missing data) -> empty string
    df["type2"] = df["type2"].fillna("")
    # 7 rows (e.g. Raichu, Diglett, Muk) have type2 == type1 -> treat as single-type
    df.loc[df["type2"] == df["type1"], "type2"] = ""
    df["types"] = [t1 if not t2 else f"{t1}/{t2}" for t1, t2 in zip(df["type1"], df["type2"])]

    # percentage_male: NaN means the Pokémon is genderless -> do NOT impute a mean
    df["is_genderless"] = df["percentage_male"].isna()

    # height_m / weight_kg: leave as NaN (never guess) and show "N/A" when answering

    # abilities: "['Overgrow', 'Chlorophyll']" -> a real list
    df["abilities"] = df["abilities"].apply(ast.literal_eval)

    df["capture_rate_num"] = df["capture_rate"].apply(_first_int)

    jp = [_split_japanese(s) for s in df["japanese_name"]]
    # In the CSV the ♂/♀ symbols of Nidoran became "?", so strip it from the romaji
    df["romaji"] = [a.rstrip("?") for a, _ in jp]
    df["kana"] = [b for _, b in jp]

    df["is_legendary"] = df["is_legendary"].astype(bool)
    return df


def weakness_profile(row: pd.Series) -> dict[float, list[str]]:
    """Group attacking types by multiplier, e.g. {4.0: ['ice'], 2.0: ['fire', 'flying'], 0.5: [...]}"""
    groups: dict[float, list[str]] = {}
    for col, t in zip(AGAINST_COLS, ALL_TYPES):
        groups.setdefault(float(row[col]), []).append(t)
    return groups


def fmt(v, suffix: str = "") -> str:
    return "N/A" if pd.isna(v) else f"{v:g}{suffix}"
