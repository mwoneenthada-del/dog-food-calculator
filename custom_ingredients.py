from typing import Dict, List


def get_supported_nutrients(ingredients: Dict) -> List[str]:
    nutrient_keys = set()

    for ingredient in ingredients.values():
        nutrient_keys.update(ingredient.get("nutrients", {}).keys())

    nutrient_keys.add("energy_kcal")

    return sorted(nutrient_keys)


def get_nutrient_labels(ingredients: Dict) -> Dict[str, str]:
    labels = {}

    for ingredient in ingredients.values():
        for nutrient_key in ingredient.get("nutrients", {}).keys():
            if nutrient_key not in labels:
                labels[nutrient_key] = nutrient_key.replace("_", " ").title()

    # overrides
    labels.update({
        "energy_kcal": "Calories",
        "selenium_wet": "Selenium",
        "vitamin_a": "Vitamin A",
        "vitamin_d": "Vitamin D",
        "vitamin_e": "Vitamin E",
        "vitamin_k": "Vitamin K",
        "vitamin_b1": "Vitamin B1",
        "vitamin_b2": "Vitamin B2",
        "vitamin_b3": "Vitamin B3",
        "vitamin_b5": "Vitamin B5",
        "vitamin_b6": "Vitamin B6",
        "vitamin_b7": "Vitamin B7",
        "vitamin_b9": "Vitamin B9",
        "vitamin_b12": "Vitamin B12",
        "epa": "EPA",
        "dha": "DHA",
        "alpha_linolenic_acid": "Alpha-Linolenic Acid",
        "linoleic_acid": "Linoleic Acid",
        "arachidonic_acid": "Arachidonic Acid",
    })

    return labels


def get_supported_units():
    return ["g", "mg", "µg", "IU", "kcal"]


def normalize_unit(unit: str) -> str:
    unit = unit.strip()
    aliases = {"ug": "µg", "mcg": "µg", "μg": "µg"}
    return aliases.get(unit, unit)


def convert_amount(amount: float, from_unit: str, to_unit: str) -> float:
    from_unit = normalize_unit(from_unit)
    to_unit = normalize_unit(to_unit)

    if from_unit == to_unit:
        return amount

    conversion_factors = {
        ("g", "mg"): 1000.0,
        ("g", "µg"): 1_000_000.0,
        ("mg", "g"): 1 / 1000.0,
        ("mg", "µg"): 1000.0,
        ("µg", "mg"): 1 / 1000.0,
        ("µg", "g"): 1 / 1_000_000.0,
    }

    if (from_unit, to_unit) not in conversion_factors:
        raise ValueError(f"Unsupported unit conversion: {from_unit} -> {to_unit}")

    return amount * conversion_factors[(from_unit, to_unit)]


def get_dataset_nutrient_units(ingredients: Dict) -> Dict[str, str]:
    units = {}
    for ingredient in ingredients.values():
        for k, v in ingredient["nutrients"].items():
            if k not in units:
                units[k] = v["unit"]
    return units


def get_supported_units_for_nutrient(nutrient_key: str, ingredients: Dict) -> List[str]:
    if nutrient_key == "energy_kcal":
        return ["kcal"]

    dataset_units = get_dataset_nutrient_units(ingredients)
    target_unit = normalize_unit(dataset_units.get(nutrient_key, ""))

    if target_unit == "g":
        return ["g", "mg", "µg"]
    if target_unit == "mg":
        return ["g", "mg", "µg"]
    if target_unit == "µg":
        return ["mg", "µg"]
    if target_unit == "IU":
        return ["IU"]

    return [target_unit] if target_unit else get_supported_units()


def build_empty_nutrients(ingredients: Dict) -> Dict:
    template = {}
    for ingredient in ingredients.values():
        for k, v in ingredient["nutrients"].items():
            if k not in template:
                template[k] = {"value": None, "unit": v["unit"]}
    return template


def build_custom_ingredient(
    name,
    serving_label,
    recipe_grams,
    nutrient_rows,
    ingredients,
    custom_index,
):
    display_name = name.strip()
    if serving_label.strip():
        display_name += f" [{serving_label.strip()}]"

    nutrients = build_empty_nutrients(ingredients)
    dataset_units = get_dataset_nutrient_units(ingredients)

    energy_kcal = {"value": 0.0, "unit": "kcal"}

    for row in nutrient_rows:
        key = row["nutrient"]
        amount = float(row["amount"])
        unit = normalize_unit(row["unit"])

        if amount <= 0:
            continue

        basis = recipe_grams if recipe_grams > 0 else 100.0

        if key == "energy_kcal":
            val = convert_amount(amount, unit, "kcal")
            energy_kcal["value"] = (val / basis) * 100
            continue

        if key not in dataset_units:
            raise ValueError(f"Unsupported nutrient: {key}")

        target_unit = dataset_units[key]
        val = convert_amount(amount, unit, target_unit)
        per_100g = (val / basis) * 100

        nutrients[key] = {"value": per_100g, "unit": target_unit}

    return f"custom_{custom_index}", {
        "name": display_name,
        "basis": "per_100g",
        "ignore_missing_warnings": True,
        "energy_kcal": energy_kcal,
        "nutrients": nutrients,
    }