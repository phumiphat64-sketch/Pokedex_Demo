"""Verification script for Pokedex Chatbot logic."""
import sys
from pathlib import Path

# Add project root to sys.path so 'src' can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.data_loader import load_data
from src.router_light import parse
from src.tools import execute

def run_tests():
    print("Loading data...")
    df = load_data()
    print(f"Data loaded: {len(df)} rows, {len(df.columns)} columns.")

    results = []

    # Test 1: Show info and weaknesses of Bulbasaur
    print("\n--- Test 1: Show info and weaknesses of Bulbasaur ---")
    q1 = parse(df, "Show info and weaknesses of Bulbasaur")
    print("Parsed query:", q1)
    ans1 = execute(df, q1)
    print("Answer text:\n", ans1.text)
    t1_pass = (
        q1.get("intent") == "profile"
        and "Bulbasaur" in (q1.get("names") or [])
        and "grass/poison" in ans1.text
        and "fire" in ans1.text and "flying" in ans1.text and "ice" in ans1.text and "psychic" in ans1.text
        and "grass" in ans1.text
        and ans1.radar == ["Bulbasaur"]
    )
    print("Test 1 Result:", "PASS" if t1_pass else "FAIL")
    results.append(("Show info and weaknesses of Bulbasaur", t1_pass))

    # Test 2: Top 5 fire-type Pokémon by Speed
    print("\n--- Test 2: Top 5 fire-type Pokémon by Speed ---")
    q2 = parse(df, "Top 5 fire-type Pokémon by Speed")
    print("Parsed query:", q2)
    ans2 = execute(df, q2)
    names2 = ans2.table["name"].tolist() if ans2.table is not None else []
    print("Top 5 names:", names2)
    expected_top5 = ["Talonflame", "Salazzle", "Houndoom", "Ninetales", "Infernape"]
    t2_pass = (
        q2.get("intent") == "rank"
        and q2.get("stat") == "speed"
        and q2.get("types") == ["fire"]
        and q2.get("n") == 5
        and names2 == expected_top5
    )
    print("Test 2 Result:", "PASS" if t2_pass else "FAIL")
    results.append(("Top 5 fire-type Pokémon by Speed", t2_pass))

    # Test 3: Which Pokémon are weak to water 4x?
    print("\n--- Test 3: Which Pokémon are weak to water 4x? ---")
    q3 = parse(df, "Which Pokémon are weak to water 4x?")
    print("Parsed query:", q3)
    ans3 = execute(df, q3)
    names3 = ans3.table["name"].tolist() if ans3.table is not None else []
    print(f"Total weak: {len(names3)}, starting with: {names3[:5]}")
    expected_start5 = ["Camerupt", "Rhyperior", "Golem", "Rhydon", "Magcargo"]
    t3_pass = (
        q3.get("intent") == "weak_to"
        and q3.get("types") == ["water"]
        and q3.get("multiplier") == 4.0
        and len(names3) == 12
        and names3[:5] == expected_start5
    )
    print("Test 3 Result:", "PASS" if t3_pass else "FAIL")
    results.append(("Which Pokémon are weak to water 4x?", t3_pass))

    # Test 4: Compare Pikachu and Raichu
    print("\n--- Test 4: Compare Pikachu and Raichu ---")
    q4 = parse(df, "Compare Pikachu and Raichu")
    print("Parsed query:", q4)
    ans4 = execute(df, q4)
    cols4 = list(ans4.table.columns) if ans4.table is not None else []
    print("Table columns:", cols4)
    print("Answer text:\n", ans4.text)
    t4_pass = (
        q4.get("intent") == "compare"
        and set(q4.get("names", [])) == {"Pikachu", "Raichu"}
        and "Pikachu" in cols4 and "Raichu" in cols4
        and ans4.radar == ["Pikachu", "Raichu"]
    )
    print("Test 4 Result:", "PASS" if t4_pass else "FAIL")
    results.append(("Compare Pikachu and Raichu", t4_pass))

    # Test 5: show info for bulbasur (fuzzy match)
    print("\n--- Test 5: show info for bulbasur (fuzzy match) ---")
    q5 = parse(df, "show info for bulbasur")
    print("Parsed query:", q5)
    ans5 = execute(df, q5)
    t5_pass = (
        q5.get("intent") == "profile"
        and q5.get("names") == ["Bulbasaur"]
        and ans5.radar == ["Bulbasaur"]
    )
    print("Test 5 Result:", "PASS" if t5_pass else "FAIL")
    results.append(("show info for bulbasur", t5_pass))

    # Test 6: Thai question: ตัวไหนแพ้ธาตุน้ำ 4 เท่าบ้าง
    print("\n--- Test 6: ตัวไหนแพ้ธาตุน้ำ 4 เท่าบ้าง ---")
    q6 = parse(df, "ตัวไหนแพ้ธาตุน้ำ 4 เท่าบ้าง")
    print("Parsed query:", q6)
    ans6 = execute(df, q6)
    names6 = ans6.table["name"].tolist() if ans6.table is not None else []
    print(f"Total weak: {len(names6)}, starting with: {names6[:5]}")
    t6_pass = (
        q6.get("intent") == "weak_to"
        and q6.get("types") == ["water"]
        and q6.get("multiplier") == 4.0
        and names6 == names3
    )
    print("Test 6 Result:", "PASS" if t6_pass else "FAIL")
    results.append(("ตัวไหนแพ้ธาตุน้ำ 4 เท่าบ้าง", t6_pass))

    print("\n================ SUMMARY ================")
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"[{status}] {name}")
    print("=========================================")
    if not all_passed:
        sys.exit(1)
    print("All test questions passed!")

if __name__ == "__main__":
    run_tests()
