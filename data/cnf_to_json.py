#!/usr/bin/env python3

import pandas as pd
import json
import re
import argparse
from pathlib import Path

TARGET_NUTRIENTS = [
    ("protein", "g"),
    ("arginine", "g"),
    ("histidine", "g"),
    ("isoleucine", "g"),
    ("leucine", "g"),
    ("lysine", "g"),
    ("methionine", "g"),
    ("cystine", "g"),
    ("phenylalanine", "g"),
    ("tyrosine", "g"),
    ("threonine", "g"),
    ("tryptophan", "g"),
    ("valine", "g"),
    ("fat", "g"),
    ("linoleic_acid", "g"),
    ("arachidonic_acid", "mg"),
    ("alpha_linolenic_acid", "g"),
    ("epa", "g"),
    ("dha", "g"),
    ("carbohydrate", "g"),
    ("calcium", "g"),
    ("phosphorus", "g"),
    ("potassium", "g"),
    ("sodium", "g"),
    ("chloride", "g"),
    ("magnesium", "g"),
    ("copper", "mg"),
    ("iodine", "mg"),
    ("iron", "mg"),
    ("manganese", "mg"),
    ("selenium_wet", "µg"),
    ("zinc", "mg"),
    ("vitamin_a", "IU"),
    ("vitamin_d", "IU"),
    ("vitamin_e", "IU"),
    ("vitamin_b1", "mg"),
    ("vitamin_b2", "mg"),
    ("vitamin_b5", "mg"),
    ("vitamin_b6", "mg"),
    ("vitamin_b12", "µg"),
    ("vitamin_b3", "mg"),
    ("vitamin_b9", "µg"),
    ("vitamin_b7", "µg"),
    ("choline", "mg"),
    ("vitamin_k", "µg"),
]

MAP = {
    "Protein": "protein",
    "Arginine": "arginine",
    "Histidine": "histidine",
    "Isoleucine": "isoleucine",
    "Leucine": "leucine",
    "Lysine": "lysine",
    "Methionine": "methionine",
    "Cystine": "cystine",
    "Phenylalanine": "phenylalanine",
    "Tyrosine": "tyrosine",
    "Threonine": "threonine",
    "Tryptophan": "tryptophan",
    "Valine": "valine",
    "Total Fat": "fat",
    "Carbohydrate": "carbohydrate",
    "Calcium, Ca": "calcium",
    "Phosphorus, P": "phosphorus",
    "Potassium, K": "potassium",
    "Sodium, Na": "sodium",
    "Magnesium, Mg": "magnesium",
    "Copper, Cu": "copper",
    "Iron, Fe": "iron",
    "Manganese, Mn": "manganese",
    "Selenium, Se": "selenium_wet",
    "Zinc, Zn": "zinc",
    "Niacin": "vitamin_b3",
    "Riboflavin": "vitamin_b2",
    "Thiamin": "vitamin_b1",
    "Vitamin B-6": "vitamin_b6",
    "Vitamin B-12": "vitamin_b12",
    "Pantothenic acid": "vitamin_b5",
    "Folacin, total": "vitamin_b9",
    "Choline, total": "choline",
    "Vitamin K": "vitamin_k",
    "18:2": "linoleic_acid",
    "20:4": "arachidonic_acid",
    "18:3": "alpha_linolenic_acid",
    "20:5n-3 (EPA)": "epa",
    "22:6n-3 (DHA)": "dha",
}


def clean_number(v):
    if v is None:
        return None
    if pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return float(v)

    s = str(v).strip()
    if s == "" or s.lower() in {"nan", "none", "null", "--"}:
        return None

    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def clean_text(v):
    if v is None or pd.isna(v):
        return ""
    return str(v).strip()


def smart_round(v, places=6):
    if v is None:
        return None
    v = round(float(v), places)
    if v.is_integer():
        return int(v)
    return v


def mg_to_g(v):
    v = clean_number(v)
    return None if v is None else v / 1000.0


def ug_to_IU_A(v):
    v = clean_number(v)
    return None if v is None else v * 3.333333


def ug_to_IU_D(v):
    v = clean_number(v)
    return None if v is None else v * 40.0


def mg_to_IU_E(v):
    v = clean_number(v)
    return None if v is None else v * 1.49


def make_key(name, code):
    first = clean_text(name).split(",")[0].lower()
    first = re.sub(r"[^a-z0-9]+", "_", first).strip("_")
    return f"{first}_{code}"


def parse_file(file):
    df = pd.read_excel(file, header=None)

    name = clean_text(df.iloc[1, 0])

    code = None
    for i in range(min(15, len(df))):
        row = clean_text(df.iloc[i, 0])
        m = re.search(r"Food code\s*:\s*(\d+)", row, flags=re.I)
        if m:
            code = m.group(1)
            break

    if not name:
        raise ValueError("could not find food name")
    if not code:
        raise ValueError("could not find food code")

    header = None
    for i in range(len(df)):
        if clean_text(df.iloc[i, 0]) == "Nutrient name":
            header = i
            break

    if header is None:
        raise ValueError("could not find nutrient table")

    table = df.iloc[header + 1:, :3].copy()
    table.columns = ["nutrient", "unit", "value"]

    rows = {}
    for _, r in table.iterrows():
        nutrient = clean_text(r["nutrient"])
        unit = clean_text(r["unit"])
        value = clean_number(r["value"])

        if nutrient == "":
            continue

        rows[nutrient] = (value, unit)

    nutrients = {k: {"value": None, "unit": u} for k, u in TARGET_NUTRIENTS}

    for src, target in MAP.items():
        if src not in rows:
            continue

        v, u = rows[src]

        if target in ["calcium", "phosphorus", "potassium", "sodium", "magnesium"]:
            v = mg_to_g(v)
        elif target == "arachidonic_acid":
            v = None if v is None else v * 1000.0

        nutrients[target]["value"] = smart_round(v)

    energy = None
    if "Energy (kcal)" in rows:
        energy = clean_number(rows["Energy (kcal)"][0])

    if "Retinol" in rows:
        nutrients["vitamin_a"]["value"] = smart_round(ug_to_IU_A(rows["Retinol"][0]), 3)

    if "Vitamin D" in rows:
        nutrients["vitamin_d"]["value"] = smart_round(ug_to_IU_D(rows["Vitamin D"][0]), 3)
    elif "Vitamin D (IU)" in rows:
        nutrients["vitamin_d"]["value"] = smart_round(clean_number(rows["Vitamin D (IU)"][0]), 3)

    if "Tocopherol, alpha" in rows:
        nutrients["vitamin_e"]["value"] = smart_round(mg_to_IU_E(rows["Tocopherol, alpha"][0]), 3)

    key = make_key(name, code)

    return key, {
        "name": name,
        "basis": "per_100g",
        "energy_kcal": {"value": smart_round(energy, 3), "unit": "kcal"},
        "nutrients": nutrients,
    }


def json_atom(value):
    return json.dumps(value, ensure_ascii=False)


def format_foods_json(foods):
    lines = []
    lines.append("{")

    food_items = list(foods.items())
    for food_index, (food_key, food_data) in enumerate(food_items):
        food_comma = "," if food_index < len(food_items) - 1 else ""
        lines.append(f'  {json_atom(food_key)}: {{')
        lines.append(f'    "name": {json_atom(food_data["name"])},')
        lines.append(f'    "basis": {json_atom(food_data["basis"])},')

        energy = food_data["energy_kcal"]
        lines.append(
            f'    "energy_kcal": {{ "value": {json_atom(energy["value"])}, "unit": {json_atom(energy["unit"])} }},'
        )

        lines.append('    "nutrients": {')

        nutrient_items = list(food_data["nutrients"].items())
        for nutrient_index, (nutrient_key, nutrient_data) in enumerate(nutrient_items):
            nutrient_comma = "," if nutrient_index < len(nutrient_items) - 1 else ""
            lines.append(
                f'      {json_atom(nutrient_key)}: '
                f'{{ "value": {json_atom(nutrient_data["value"])}, "unit": {json_atom(nutrient_data["unit"])} }}{nutrient_comma}'
            )

        lines.append('    }')
        lines.append(f'  }}{food_comma}')

    lines.append("}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="folder with xls/xlsx files, or a single file")
    parser.add_argument("--output", default="foods.json")
    args = parser.parse_args()

    path = Path(args.path)

    if path.is_file():
        files = [path]
    else:
        files = sorted(list(path.glob("*.xls")) + list(path.glob("*.xlsx")))

    if not files:
        print("No Excel files found.")
        return

    foods = {}

    for f in files:
        try:
            k, v = parse_file(f)
            foods[k] = v
            print("OK ", f.name, "->", k)
        except Exception as e:
            print("ERR", f.name, e)

    output_text = format_foods_json(foods)

    with open(args.output, "w", encoding="utf-8") as fp:
        fp.write(output_text)

    print("DONE ->", args.output)


if __name__ == "__main__":
    main()