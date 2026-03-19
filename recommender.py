from copy import deepcopy


DISPLAY_NUTRIENTS = [
    ("protein_amino_acids", "protein", False),
    ("protein_amino_acids", "arginine", False),
    ("protein_amino_acids", "histidine", False),
    ("protein_amino_acids", "isoleucine", False),
    ("protein_amino_acids", "leucine", False),
    ("protein_amino_acids", "lysine", False),
    ("protein_amino_acids", "methionine_cystine", True),
    ("protein_amino_acids", "phenylalanine_tyrosine", True),
    ("protein_amino_acids", "threonine", False),
    ("protein_amino_acids", "tryptophan", False),
    ("protein_amino_acids", "valine", False),
    ("fat_fatty_acids", "fat", False),
    ("fat_fatty_acids", "linoleic_acid", False),
    ("minerals", "calcium", False),
    ("minerals", "phosphorus", False),
    ("minerals", "potassium", False),
    ("minerals", "sodium", False),
    ("minerals", "chloride", False),
    ("minerals", "magnesium", False),
    ("trace_elements", "copper", False),
    ("trace_elements", "iodine", False),
    ("trace_elements", "iron", False),
    ("trace_elements", "manganese", False),
    ("trace_elements", "selenium_wet", False),
    ("trace_elements", "zinc", False),
    ("vitamins", "vitamin_a", False),
    ("vitamins", "vitamin_d", False),
    ("vitamins", "vitamin_e", False),
    ("vitamins", "vitamin_b1", False),
    ("vitamins", "vitamin_b2", False),
    ("vitamins", "vitamin_b5", False),
    ("vitamins", "vitamin_b6", False),
    ("vitamins", "vitamin_b12", False),
    ("vitamins", "vitamin_b3", False),
    ("vitamins", "vitamin_b9", False),
    ("vitamins", "choline", False),
]


def scale_guideline_to_recipe(guideline_value, total_calories):
    if guideline_value is None:
        return None
    if total_calories is None or total_calories <= 0:
        return 0
    return guideline_value * (total_calories / 1000)


def calculate_total_calories(recipe, ingredients):
    total_calories = 0.0
    for item in recipe:
        ingredient_key = item["ingredient_key"]
        grams = item["grams"]
        kcal_per_100g = ingredients[ingredient_key]["energy_kcal"]["value"]
        if kcal_per_100g is not None:
            total_calories += (grams / 100) * kcal_per_100g
    return total_calories


def get_nutrient_total(recipe, ingredients, nutrient_key):
    total = 0.0
    for item in recipe:
        ingredient_key = item["ingredient_key"]
        grams = item["grams"]

        nutrient_data = ingredients[ingredient_key]["nutrients"].get(nutrient_key)
        if nutrient_data is not None:
            value = nutrient_data["value"]
            if value is not None:
                total += (grams / 100) * value
    return total


def get_derived_nutrient_total(recipe, ingredients, nutrient_key):
    if nutrient_key == "methionine_cystine":
        return (
            get_nutrient_total(recipe, ingredients, "methionine")
            + get_nutrient_total(recipe, ingredients, "cystine")
        )

    if nutrient_key == "phenylalanine_tyrosine":
        return (
            get_nutrient_total(recipe, ingredients, "phenylalanine")
            + get_nutrient_total(recipe, ingredients, "tyrosine")
        )

    return get_nutrient_total(recipe, ingredients, nutrient_key)


def get_nutrient_amount(recipe, ingredients, nutrient_key, derived=False):
    if derived:
        return get_derived_nutrient_total(recipe, ingredients, nutrient_key)
    return get_nutrient_total(recipe, ingredients, nutrient_key)


def add_ingredient_to_recipe_copy(recipe, ingredient_key, ingredient_name, grams):
    new_recipe = deepcopy(recipe)

    for item in new_recipe:
        if item["ingredient_key"] == ingredient_key:
            item["grams"] += grams
            return new_recipe

    new_recipe.append(
        {
            "ingredient_key": ingredient_key,
            "ingredient_name": ingredient_name,
            "grams": grams,
        }
    )
    return new_recipe


def get_ca_p_ratio(recipe, ingredients):
    calcium = get_nutrient_total(recipe, ingredients, "calcium")
    phosphorus = get_nutrient_total(recipe, ingredients, "phosphorus")
    if phosphorus <= 0:
        return None
    return calcium / phosphorus


def evaluate_recipe(recipe, ingredients, guidelines):
    adult = guidelines["adult_maintenance"]
    total_calories = calculate_total_calories(recipe, ingredients)

    nutrient_results = []
    hits = 0

    for group_name, nutrient_key, derived in DISPLAY_NUTRIENTS:
        nutrient_info = adult[group_name][nutrient_key]

        amount = get_nutrient_amount(recipe, ingredients, nutrient_key, derived=derived)
        scaled_min = scale_guideline_to_recipe(nutrient_info["minimum"], total_calories)
        scaled_max = scale_guideline_to_recipe(nutrient_info["maximum"], total_calories)

        is_hit = False
        if scaled_min is not None and scaled_min > 0:
            if scaled_max is not None and scaled_max > 0:
                is_hit = scaled_min <= amount <= scaled_max
            else:
                is_hit = amount >= scaled_min

        if is_hit:
            hits += 1

        nutrient_results.append(
            {
                "nutrient_key": nutrient_key,
                "label": nutrient_info["label"],
                "amount": amount,
                "min": scaled_min,
                "max": scaled_max,
                "is_hit": is_hit,
                "is_below_min": scaled_min is not None and amount < scaled_min,
                "is_above_max": scaled_max is not None and scaled_max > 0 and amount > scaled_max,
                "deficit": max((scaled_min or 0) - amount, 0),
                "deficit_fraction": (
                    max((scaled_min or 0) - amount, 0) / scaled_min
                    if scaled_min not in (None, 0)
                    else 0
                ),
            }
        )

    #calcium to phosphorous ratio
    ratio = get_ca_p_ratio(recipe, ingredients)
    ratio_hit = ratio is not None and 1.0 <= ratio <= 2.0
    if ratio_hit:
        hits += 1

    nutrient_results.append(
        {
            "nutrient_key": "ca_p_ratio",
            "label": "Calcium : Phosphorus Ratio",
            "amount": ratio,
            "min": 1.0,
            "max": 2.0,
            "is_hit": ratio_hit,
            "is_below_min": ratio is None or ratio < 1.0,
            "is_above_max": ratio is not None and ratio > 2.0,
            "deficit": 0 if ratio_hit else 1,
            "deficit_fraction": 0 if ratio_hit else 1,
        }
    )

    total_targets = len(nutrient_results)
    percent = (hits / total_targets) * 100 if total_targets > 0 else 0

    return {
        "total_calories": total_calories,
        "hits": hits,
        "total_targets": total_targets,
        "percent": percent,
        "nutrient_results": nutrient_results,
    }


def get_candidate_amounts(ingredient_name):
    name = ingredient_name.lower()

    if "(supplement, averaged)" in name:
        return [0.5, 1, 2, 3, 4, 5, 6]

    if "salt" in name:
        return [0.5, 1, 2, 3, 4, 5, 6]

    if "oil" in name:
        return [1, 2, 5, 7, 10, 15]

    if "liver" in name or "kidney" in name:
        return [5, 10, 20, 30]

    return [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]


def get_improved_nutrients(before_eval, after_eval, top_n=3):
    before_map = {item["nutrient_key"]: item for item in before_eval["nutrient_results"]}
    after_map = {item["nutrient_key"]: item for item in after_eval["nutrient_results"]}

    improvements = []

    for nutrient_key, before_item in before_map.items():
        after_item = after_map[nutrient_key]

        before_gap = before_item["deficit_fraction"]
        after_gap = after_item["deficit_fraction"]
        improvement = before_gap - after_gap

        if improvement > 0:
            improvements.append((before_item["label"], improvement))

    improvements.sort(key=lambda x: x[1], reverse=True)
    return [label for label, _ in improvements[:top_n]]


def score_candidate(before_eval, after_eval):
    return after_eval["percent"] - before_eval["percent"]


def get_top_ingredient_suggestions(
    recipe,
    ingredients,
    guidelines,
    top_n=3,
    exclude_existing=False,
):
    if not recipe:
        return []

    before_eval = evaluate_recipe(recipe, ingredients, guidelines)
    existing_keys = {item["ingredient_key"] for item in recipe}

    suggestions = []

    for ingredient_key, ingredient_info in ingredients.items():
        ingredient_name = ingredient_info["name"]

        if exclude_existing and ingredient_key in existing_keys:
            continue

        for grams in get_candidate_amounts(ingredient_name):
            simulated_recipe = add_ingredient_to_recipe_copy(
                recipe=recipe,
                ingredient_key=ingredient_key,
                ingredient_name=ingredient_name,
                grams=grams,
            )

            after_eval = evaluate_recipe(simulated_recipe, ingredients, guidelines)
            delta = after_eval["percent"] - before_eval["percent"]

            if delta <= 0:
                continue

            improved_nutrients = get_improved_nutrients(before_eval, after_eval, top_n=3)
            score = score_candidate(before_eval, after_eval)

            suggestions.append(
                {
                    "ingredient_key": ingredient_key,
                    "ingredient_name": ingredient_name,
                    "grams": grams,
                    "before_percent": before_eval["percent"],
                    "after_percent": after_eval["percent"],
                    "delta_percent": delta,
                    "score": score,
                    "improved_nutrients": improved_nutrients,
                    "justification": (
                        "Improves " + ", ".join(improved_nutrients)
                        if improved_nutrients
                        else "Improves overall nutrient target coverage"
                    ),
                }
            )

    #keep only the best amount per ingredient
    best_by_ingredient = {}
    for suggestion in suggestions:
        key = suggestion["ingredient_key"]
        if key not in best_by_ingredient or suggestion["score"] > best_by_ingredient[key]["score"]:
            best_by_ingredient[key] = suggestion

    deduped = list(best_by_ingredient.values())
    deduped.sort(key=lambda x: (x["score"], x["delta_percent"]), reverse=True)

    return deduped[:top_n]