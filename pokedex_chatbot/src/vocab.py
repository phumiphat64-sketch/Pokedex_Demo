"""English + Thai vocabulary used to understand questions (edit/extend freely)."""
import re

TYPE_WORDS = {
    "fire": ["fire", "ธาตุไฟ", "ไฟ"],
    "water": ["water", "ธาตุน้ำ", "น้ำ"],
    "grass": ["grass", "ธาตุหญ้า", "หญ้า", "พืช"],
    "electric": ["electric", "ธาตุไฟฟ้า", "ไฟฟ้า", "สายฟ้า"],
    "ice": ["ice", "ธาตุน้ำแข็ง", "น้ำแข็ง"],
    "fighting": ["fighting", "ต่อสู้"],
    "poison": ["poison", "พิษ"],
    "ground": ["ground", "ดิน"],
    "flying": ["flying", "บิน"],
    "psychic": ["psychic", "จิต", "พลังจิต"],
    "bug": ["bug", "แมลง"],
    "rock": ["rock", "หิน"],
    "ghost": ["ghost", "ผี"],
    "dragon": ["dragon", "มังกร"],
    "dark": ["dark", "มืด"],
    "steel": ["steel", "เหล็ก"],
    "fairy": ["fairy", "แฟรี่"],
    "normal": ["normal", "นอร์มอล", "ปกติ"],
}

STAT_WORDS = {
    "sp_attack": ["sp. attack", "sp attack", "sp_attack", "special attack", "โจมตีพิเศษ"],
    "sp_defense": ["sp. defense", "sp defense", "sp_defense", "special defense", "ป้องกันพิเศษ"],
    "speed": ["speed", "fastest", "slowest", "ความเร็ว", "เร็ว", "ช้า"],
    "attack": ["attack", "โจมตี"],
    "defense": ["defense", "defence", "ป้องกัน"],
    "hp": ["hp", "เลือด", "พลังชีวิต"],
    "base_total": ["base total", "base_total", "total", "รวม", "แข็งแกร่ง", "strongest"],
    "weight_kg": ["weight", "heaviest", "lightest", "น้ำหนัก"],
    "height_m": ["height", "ส่วนสูง"],
}

WEAK_WORDS = ["แพ้", "จุดอ่อน", "weak to", "weak against", "weakness", "weaknesses"]
ASC_WORDS = ["ต่ำสุด", "น้อยสุด", "ต่ำที่สุด", "น้อยที่สุด", "ช้าสุด", "ช้าที่สุด",
             "เบาสุด", "เบาที่สุด", "lowest", "slowest", "least", "lightest"]
LEGEND_WORDS = ["legendary", "ในตำนาน", "ตำนาน"]

# English words that are NOT Pokémon names (stops fuzzy matching from guessing wrongly)
STOP_WORDS = {
    w for words in list(TYPE_WORDS.values()) + list(STAT_WORDS.values())
    for w in words if w.isascii()
} | {"top", "pokemon", "pokémon", "weak", "weakness", "compare", "stats", "info",
     "show", "list", "gen", "generation", "which", "with", "give", "tell", "about",
     "type", "types", "highest", "lowest", "fastest", "slowest", "heaviest", "lightest",
     "legendary", "weaknesses", "strongest", "have", "that", "from", "ranking"}


def scan(text: str, vocab: dict) -> tuple[list[str], str]:
    """Find vocab words (longest first). Returns (values in sentence order, text with matches blanked out).
    Blanking prevents double counting, e.g. 'น้ำแข็ง' (ice) is not counted again as 'น้ำ' (water)."""
    pairs = sorted(((k, v) for v, ks in vocab.items() for k in ks), key=lambda kv: -len(kv[0]))
    hits: list[tuple[int, str]] = []
    for key, val in pairs:
        pat = re.escape(key)
        if key.isascii():
            pat = rf"(?<![a-z0-9_]){pat}(?![a-z0-9_])"
        for m in re.finditer(pat, text):
            hits.append((m.start(), val))
            text = text[:m.start()] + " " * (m.end() - m.start()) + text[m.end():]
    hits.sort()
    ordered: list[str] = []
    for _, v in hits:
        if v not in ordered:
            ordered.append(v)
    return ordered, text
