import json
import streamlit as st
import pandas as pd
from recommender import get_top_ingredient_suggestions
from recommender import evaluate_recipe
from custom_ingredients import (
    get_supported_nutrients,
    get_nutrient_labels,
    get_supported_units_for_nutrient,
    build_custom_ingredient,
)

st.set_page_config(page_title="Dog Food Calculator", layout="wide")

left, center, right = st.columns([1, 2, 1])

with center:

    #load ingredient data-----
    with open("data/ingredients.json", "r", encoding="utf-8") as f:
        ingredient_data = json.load(f)

    ingredients = ingredient_data["ingredients"]

    DISPLAYED_NUTRIENT_KEYS = [
        "arginine",
        "calcium",
        "carbohydrate",
        "chloride",
        "choline",
        "copper",
        "cystine",
        "energy_kcal",
        "fat",
        "histidine",
        "iodine",
        "iron",
        "isoleucine",
        "leucine",
        "linoleic_acid",
        "lysine",
        "magnesium",
        "manganese",
        "methionine",
        "phenylalanine",
        "phosphorus",
        "potassium",
        "protein",
        "selenium_wet",
        "sodium",
        "threonine",
        "tryptophan",
        "tyrosine",
        "valine",
        "vitamin_a",
        "vitamin_b1",
        "vitamin_b12",
        "vitamin_b2",
        "vitamin_b3",
        "vitamin_b5",
        "vitamin_b6",
        "vitamin_b9",
        "vitamin_d",
        "vitamin_e",
        "zinc",
    ]
    
    def get_calculator_nutrient_options():
        all_nutrients = get_supported_nutrients(ingredients)
        return [n for n in DISPLAYED_NUTRIENT_KEYS if n in all_nutrients]


    #load nutrient guidlines-----
    with open("data/guidelines.json", "r", encoding="utf-8") as f:
        guidelines = json.load(f)


    #session state-----
    if "custom_ingredients" not in st.session_state:
        st.session_state.custom_ingredients = {}

    if "custom_percent_rows" not in st.session_state:
        all_nutrients = get_calculator_nutrient_options()

        percent_nutrients = [
            n for n in all_nutrients
            if any(u in ["g", "mg", "mcg", "µg"]
                for u in get_supported_units_for_nutrient(n, ingredients))
        ]

        first_nutrient = percent_nutrients[0]

        st.session_state.custom_percent_rows = [
            {"nutrient": first_nutrient, "percent": 0.0}
        ]

    if "custom_nutrient_rows" not in st.session_state:
        first_nutrient = get_calculator_nutrient_options()[0]
        allowed_units = get_supported_units_for_nutrient(first_nutrient, ingredients)

        st.session_state.custom_nutrient_rows = [
            {"nutrient": first_nutrient, "amount": 0.0, "unit": allowed_units[0]}
        ]

    # --- merged ingredient dictionary ---
    all_ingredients = {**ingredients, **st.session_state.custom_ingredients}

    if "show_custom_dialog" not in st.session_state:
        st.session_state.show_custom_dialog = False

    if "recipe" not in st.session_state:
        st.session_state.recipe = []

    if "ingredient_suggestions" not in st.session_state:
        st.session_state.ingredient_suggestions = []

    if "suggestions_generated" not in st.session_state:
        st.session_state.suggestions_generated = False

    #helper functions-----
    def recipe_has_nutrients_but_no_calories():
        if not st.session_state.recipe:
            return False

        total_known_nutrients = 0.0

        for item in st.session_state.recipe:
            ingredient_key = item["ingredient_key"]

            for nutrient_data in all_ingredients[ingredient_key]["nutrients"].values():
                if nutrient_data is not None and nutrient_data.get("value") is not None:
                    total_known_nutrients += nutrient_data["value"]

        return total_known_nutrients > 0

    def get_next_available_percent_nutrient():
        all_nutrients = get_calculator_nutrient_options()

        nutrient_options = [
            n for n in all_nutrients
            if any(u in ["g", "mg", "mcg", "µg"]
                for u in get_supported_units_for_nutrient(n, ingredients))
        ]

        selected = {
            row["nutrient"]
            for row in st.session_state.custom_percent_rows
        }

        for nutrient in nutrient_options:
            if nutrient not in selected:
                return nutrient

        return None


    def add_custom_percent_row():
        next_nutrient = get_next_available_percent_nutrient()

        if next_nutrient is None:
            return

        st.session_state.custom_percent_rows.append(
            {
                "nutrient": next_nutrient,
                "percent": 0.0,
            }
        )


    def remove_custom_percent_row(index: int):
        if len(st.session_state.custom_percent_rows) > 1:
            st.session_state.custom_percent_rows.pop(index)


    def reset_custom_percent_rows():
        percent_nutrients = [
            n for n in get_calculator_nutrient_options()
            if any(u in ["g", "mg", "mcg", "µg"]
                for u in get_supported_units_for_nutrient(n, ingredients))
        ]

        first_nutrient = percent_nutrients[0]

        st.session_state.custom_percent_rows = [
            {"nutrient": first_nutrient, "percent": 0.0}
        ]


    def convert_percent_to_amount_unit(percent_value: float, serving_grams: float, nutrient_key: str):
        """
        Convert a label percentage into an absolute amount for the given serving.

        Example:
        - 40% calcium in a 5 g serving = 2 g calcium
        """
        amount_in_grams = serving_grams * (percent_value / 100.0)

        allowed_units = get_supported_units_for_nutrient(nutrient_key, ingredients)

        # Prefer smaller units for precision
        if "mg" in allowed_units:
            return amount_in_grams * 1000.0, "mg"
        elif "mcg" in allowed_units:
            return amount_in_grams * 1_000_000.0, "mcg"
        elif "µg" in allowed_units:
            return amount_in_grams * 1_000_000.0, "µg"
        elif "g" in allowed_units:
            return amount_in_grams, "g"
        else:
            return amount_in_grams, allowed_units[0]
        
    def get_next_available_nutrient():
        nutrient_options = get_calculator_nutrient_options()
        selected = {
            row["nutrient"]
            for row in st.session_state.custom_nutrient_rows
        }

        for nutrient in nutrient_options:
            if nutrient not in selected:
                return nutrient

        return None

    def add_custom_nutrient_row():
        next_nutrient = get_next_available_nutrient()

        if next_nutrient is None:
            return

        allowed_units = get_supported_units_for_nutrient(next_nutrient, ingredients)

        st.session_state.custom_nutrient_rows.append(
            {
                "nutrient": next_nutrient,
                "amount": 0.0,
                "unit": allowed_units[0]
            }
        )

    def remove_custom_nutrient_row(index: int):
        if len(st.session_state.custom_nutrient_rows) > 1:
            st.session_state.custom_nutrient_rows.pop(index)

    def reset_custom_nutrient_rows():
        first_nutrient = get_calculator_nutrient_options()[0]
        allowed_units = get_supported_units_for_nutrient(first_nutrient, ingredients)

        st.session_state.custom_nutrient_rows = [
            {"nutrient": first_nutrient, "amount": 0.0, "unit": allowed_units[0]}
        ]

    def add_ingredient_to_recipe(ingredient_key, grams, display_grams="auto"):

        ingredient_name = all_ingredients[ingredient_key]["name"]

        if display_grams == "auto":
            display_grams = grams

        for item in st.session_state.recipe:
            if item["ingredient_key"] == ingredient_key:
                item["grams"] += grams

                if item.get("display_grams") is not None and display_grams is not None:
                    item["display_grams"] += display_grams
                elif display_grams is None:
                    item["display_grams"] = None

                return

        st.session_state.recipe.append({
            "ingredient_key": ingredient_key,
            "ingredient_name": ingredient_name,
            "grams": grams,
            "display_grams": display_grams
        })

    if "pending_custom_ingredient_to_add" in st.session_state:
        pending = st.session_state.pending_custom_ingredient_to_add

        if pending["ingredient_key"] in all_ingredients:
            add_ingredient_to_recipe(
                pending["ingredient_key"],
                pending["grams"],
                pending.get("display_grams")
            )
            del st.session_state["pending_custom_ingredient_to_add"]


    def remove_ingredient_from_recipe(index: int):
        st.session_state.recipe.pop(index)


    def scale_guideline_to_recipe(guideline_value, total_calories):
        if guideline_value is None:
            return None
        if total_calories is None or total_calories <= 0:
            return None
        return guideline_value * (total_calories / 1000)
    
    def get_missing_nutrient_ingredients(nutrient_key):
        missing_ingredients = []

        for item in st.session_state.recipe:
            ingredient_key = item["ingredient_key"]
            ingredient_name = item["ingredient_name"]

            ingredient_info = all_ingredients[ingredient_key]

            if ingredient_info.get("ignore_missing_warnings", False):
                continue

            nutrient_data = ingredient_info["nutrients"].get(nutrient_key)

            if nutrient_data is None or nutrient_data["value"] is None:
                missing_ingredients.append(ingredient_name)

        return missing_ingredients
    
    def get_missing_derived_nutrient_ingredients(nutrient_key):
        if nutrient_key == "methionine_cystine":
            missing = set(get_missing_nutrient_ingredients("methionine"))
            missing.update(get_missing_nutrient_ingredients("cystine"))
            return sorted(missing)

        if nutrient_key == "phenylalanine_tyrosine":
            missing = set(get_missing_nutrient_ingredients("phenylalanine"))
            missing.update(get_missing_nutrient_ingredients("tyrosine"))
            return sorted(missing)

        return get_missing_nutrient_ingredients(nutrient_key)


    #calculate micronutrient totals------
    def get_nutrient_total_in_recipe(nutrient_key):
        total = 0.0

        for item in st.session_state.recipe:
            ingredient_key = item["ingredient_key"]
            grams = item["grams"]

            nutrient_data = all_ingredients[ingredient_key]["nutrients"].get(nutrient_key)

            if nutrient_data is not None:
                value = nutrient_data["value"]
                if value is not None:
                    total += (grams / 100) * value

        return total


    def get_derived_nutrient_total(nutrient_key):
        if nutrient_key == "methionine_cystine":
            methionine_total = get_nutrient_total_in_recipe("methionine")
            cystine_total = get_nutrient_total_in_recipe("cystine")
            return methionine_total + cystine_total

        if nutrient_key == "phenylalanine_tyrosine":
            phenylalanine_total = get_nutrient_total_in_recipe("phenylalanine")
            tyrosine_total = get_nutrient_total_in_recipe("tyrosine")
            return phenylalanine_total + tyrosine_total

        return get_nutrient_total_in_recipe(nutrient_key)


    def render_nutrient_row_desktop(label, amount, unit, min_value, max_value, missing_ingredients=None):
        progress_fraction = 0.0
        percent_label = "-"

        if max_value is not None and max_value <= 0:
            max_value = None

        if min_value is None or min_value <= 0:
            progress_fraction = 0.0
            percent_label = "-"
        else:
            if amount < min_value:
                percent = (amount / min_value) * 100
            else:
                percent = 100.0

                if max_value is not None and amount > max_value:
                    percent = (amount / max_value) * 100

            progress_fraction = min(percent / 100, 1.0)
            percent_label = f"{percent:.0f}%"

        col1, col2, col3, col4, col5 = st.columns([2.5, 1.5, 4, 1, 1])

        with col1:
            if missing_ingredients:
                tooltip_text = "Missing value for: " + ", ".join(missing_ingredients)
                st.markdown(
                    f"<span title='{tooltip_text}'>{label} *</span>",
                    unsafe_allow_html=True
                )
            else:
                st.write(label)

        with col2:
            st.write(f"{amount:.3f} {unit}")

        with col3:
            st.progress(progress_fraction)
            st.caption(percent_label)

        with col4:
            if min_value is not None:
                st.write(f"{min_value:.2f} {unit}")
            else:
                st.write("-")

        with col5:
            if max_value is not None:
                st.write(f"{max_value:.2f} {unit}")
            else:
                st.write("-")


    def render_nutrient_row_compact(label, amount, unit, min_value, max_value, missing_ingredients=None):
        progress_fraction = 0.0
        percent_label = "-"

        if max_value is not None and max_value <= 0:
            max_value = None

        if min_value is None or min_value <= 0:
            progress_fraction = 0.0
            percent_label = "-"
        else:
            if amount < min_value:
                percent = (amount / min_value) * 100
            else:
                percent = 100.0

                if max_value is not None and amount > max_value:
                    percent = (amount / max_value) * 100

            progress_fraction = min(percent / 100, 1.0)
            percent_label = f"{percent:.0f}%"

        if missing_ingredients:
            tooltip_text = "Missing value for: " + ", ".join(missing_ingredients)
            st.markdown(
                f"<span title='{tooltip_text}'><strong>{label} *</strong></span>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"**{label}**")

        amount_text = f"{amount:.3f} {unit}"
        min_text = f"{min_value:.2f} {unit}" if min_value is not None else "-"
        max_text = f"{max_value:.2f} {unit}" if max_value is not None else "-"

        st.caption(f"Amount: {amount_text} • Min: {min_text} • Max: {max_text}")
        st.progress(progress_fraction)
        st.caption(f"% of min: {percent_label}")
        st.markdown("---")


    def render_nutrient_row(label, amount, unit, min_value, max_value, missing_ingredients=None):
        if compact_view:
            render_nutrient_row_compact(
                label=label,
                amount=amount,
                unit=unit,
                min_value=min_value,
                max_value=max_value,
                missing_ingredients=missing_ingredients,
            )
        else:
            render_nutrient_row_desktop(
                label=label,
                amount=amount,
                unit=unit,
                min_value=min_value,
                max_value=max_value,
                missing_ingredients=missing_ingredients,
            )

    #app title-----
    st.title("Dog Food Nutrition Calculator")

    with st.expander("Quick Guide"):
        st.markdown("""

        *For educational use only. This tool does not replace veterinary advice and is not intended for puppies, pregnant dogs, or medically managed diets.*

        **Overview**
        - This calculator helps you check whether a homemade dog food recipe meets basic nutrient targets for healthy adult dogs based on FEDIAF guidelines.

        - Add ingredients to build your recipe, and the calculator compares nutrient totals against recommended ranges.

        - Nutrient targets are defined per 1000 kcal and are automatically scaled based on your recipe’s total calories.

        - Results help show where a recipe may be low or high in specific nutrients.

        **How to use**
        1. Add ingredients and amounts in grams to build your recipe.
        2. Review the nutrient sections to see how your recipe compares to recommended ranges.
        3. Use **Ingredient Suggestions** to identify possible ways to improve nutrient coverage.
        4. Use **Add Supplement** to enter custom supplements when needed.

        **How to read the results**
        - Progress bars show progress toward the recommended minimum for each nutrient.
        - If a nutrient has a maximum, values above that range indicate excess.
        - **Nutrient Target Coverage** shows the percentage of evaluated nutrients that fall within recommended ranges.

        **Important notes**
        - A `*` next to a nutrient means one or more ingredients are missing source data for that nutrient.
        - Supplements (custom or predefined) only include selected nutrients by design and do not trigger missing-data warnings.
        - Missing data may cause totals to be underestimated.
        - Ingredients labeled **“(supplement, averaged)”** are rough placeholders based on commercial products.
        - For better accuracy, enter your specific supplement using **Add Supplement**.

        ---

        **More details**
        - Additional information about data sources, calculations, and methodology is available at the bottom of the page.

        """)
    
    # top action tabs
    tab1, tab2, tab3 = st.tabs([
        "Add Ingredient",
        "Add Supplement",
        "Ingredient Suggestions"
    ])

    with tab1:
        #add ingredients form-----
        st.subheader("Add Ingredient")

        # st.caption("Tip: Type to search ingredients")

        ingredient_keys = list(ingredients.keys())

        with st.form("add_ingredient_form"):
            selected_ingredient = st.selectbox(
                "Ingredient",
                options=ingredient_keys,
                format_func=lambda key: ingredients[key]["name"]
            )

            grams = st.number_input(
                "Amount (grams)",
                min_value=0.0,
                value=100.0,
                step=10.0
            )

            submitted = st.form_submit_button("Add to recipe")

        if submitted:
            if grams <= 0:
                st.warning("Please enter an amount greater than 0 grams.")
            else:
                add_ingredient_to_recipe(selected_ingredient, grams)
                st.success(f"Added {ingredients[selected_ingredient]['name']} ({grams:.1f} g) to recipe.")


    with tab2:
        # --- Custom Ingredient Modal ---

        @st.dialog("Add Custom Supplement")
        def show_custom_ingredient_dialog():

            mode_options = {
                "amount": "Enter exact nutrient amounts",
                "percent": "Convert label percentages"
            }

            entry_mode = st.radio(
                "How do you want to enter nutrients?",
                options=list(mode_options.keys()),
                format_func=lambda key: mode_options[key],
                horizontal=True,
                help="Use 'exact amounts' if the label lists nutrients in mg, g, or IU. Use 'percentages' if the label lists nutrients as % and you know the serving weight."
            )

            st.markdown("---")

            if entry_mode == "amount":

                custom_name = st.text_input(
                    "Supplement name",
                    placeholder="Eggshell Powder"
                )

                recipe_grams = st.number_input(
                    "Serving weight in grams (optional)",
                    min_value=0.0,
                    value=0.0,
                    step=0.1
                )

                serving_label = st.text_input(
                    "Serving description (optional)",
                    placeholder="1 scoop"
                )

                nutrient_options = get_calculator_nutrient_options()
                nutrient_labels = get_nutrient_labels(ingredients)

                st.markdown("**Nutrients**")

                header1, header2, header3, header4 = st.columns([3, 2, 2, 1])
                with header1:
                    st.caption("Nutrient (type to search)")
                with header2:
                    st.caption("Amount")
                with header3:
                    st.caption("Unit")
                with header4:
                    st.caption("")

                for i, row in enumerate(st.session_state.custom_nutrient_rows):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                    with col1:
                        # get all currently selected nutrients
                        selected_nutrients = [
                            r["nutrient"] for r in st.session_state.custom_nutrient_rows
                        ]

                        # allow current row to keep its value
                        available_nutrients = [
                            n for n in nutrient_options
                            if n not in selected_nutrients or n == row["nutrient"]
                        ]

                        selected_nutrient = st.selectbox(
                            "Nutrient",
                            options=available_nutrients,
                            format_func=lambda key: nutrient_labels.get(key, key),
                            index=available_nutrients.index(row["nutrient"]) if row["nutrient"] in available_nutrients else 0,
                            key=f"custom_nutrient_{i}",
                            label_visibility="collapsed"
                        )

                        st.session_state.custom_nutrient_rows[i]["nutrient"] = selected_nutrient

                        allowed_units = get_supported_units_for_nutrient(selected_nutrient, ingredients)

                        if st.session_state.custom_nutrient_rows[i]["unit"] not in allowed_units:
                            st.session_state.custom_nutrient_rows[i]["unit"] = allowed_units[0]

                    with col2:
                        amount = st.number_input(
                            "Amount",
                            min_value=0.0,
                            value=float(row["amount"]),
                            step=0.1,
                            key=f"custom_amount_{i}",
                            label_visibility="collapsed"
                        )
                        st.session_state.custom_nutrient_rows[i]["amount"] = amount

                    with col3:

                        selected_unit = st.selectbox(
                            "Unit",
                            options=allowed_units,
                            index=allowed_units.index(row["unit"]) if row["unit"] in allowed_units else 0,
                            key=f"custom_unit_{i}",
                            label_visibility="collapsed"
                        )

                        st.session_state.custom_nutrient_rows[i]["unit"] = selected_unit

                    with col4:
                        if st.button("✕", key=f"remove_custom_nutrient_{i}"):
                            remove_custom_nutrient_row(i)
                            st.rerun()

                next_nutrient = get_next_available_nutrient()

                if next_nutrient is not None:
                    if st.button("+ Add another nutrient", key="add_custom_nutrient_row"):
                        add_custom_nutrient_row()
                        st.rerun()
                else:
                    st.info("All supported nutrients have already been added.")

            elif entry_mode == "percent":

                custom_name = st.text_input(
                    "Supplement name",
                    placeholder="Eggshell powder"
                )

                recipe_grams = st.number_input(
                    "Serving weight in grams",
                    min_value=0.0,
                    value=1.0,
                    step=0.1,
                )

                serving_label = st.text_input(
                    "Serving description (optional)",
                    placeholder="1 scoop"
                )

                all_nutrients = get_calculator_nutrient_options()

                nutrient_options = [
                    n for n in all_nutrients
                    if any(u in ["g", "mg", "mcg", "µg"]
                        for u in get_supported_units_for_nutrient(n, ingredients))
                ]

                nutrient_labels = get_nutrient_labels(ingredients)

                st.markdown("**Nutrients listed as percentages**")
                # st.caption("Percent values are converted using: amount = serving weight × (% / 100)")

                header1, header2, header3, header4 = st.columns([3, 2, 2, 1])
                with header1:
                    st.caption("Nutrient (type to search)")
                with header2:
                    st.caption("Percent (%)")
                with header3:
                    st.caption("Converted amount")
                with header4:
                    st.caption("")

                for i, row in enumerate(st.session_state.custom_percent_rows):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                    with col1:
                        selected_nutrients = [
                            r["nutrient"] for r in st.session_state.custom_percent_rows
                        ]

                        available_nutrients = [
                            n for n in nutrient_options
                            if n not in selected_nutrients or n == row["nutrient"]
                        ]

                        selected_nutrient = st.selectbox(
                            "Nutrient",
                            options=available_nutrients,
                            format_func=lambda key: nutrient_labels.get(key, key),
                            index=available_nutrients.index(row["nutrient"]) if row["nutrient"] in available_nutrients else 0,
                            key=f"custom_percent_nutrient_{i}",
                            label_visibility="collapsed"
                        )

                        st.session_state.custom_percent_rows[i]["nutrient"] = selected_nutrient

                    with col2:
                        percent_value = st.number_input(
                            "Percent",
                            min_value=0.0,
                            value=float(row["percent"]),
                            step=0.1,
                            key=f"custom_percent_value_{i}",
                            label_visibility="collapsed"
                        )
                        st.session_state.custom_percent_rows[i]["percent"] = percent_value

                    with col3:
                        if recipe_grams > 0:
                            converted_amount, converted_unit = convert_percent_to_amount_unit(
                                percent_value=percent_value,
                                serving_grams=recipe_grams,
                                nutrient_key=selected_nutrient
                            )
                            st.write(f"{converted_amount:.3f} {converted_unit}")
                        else:
                            st.write("—")

                    with col4:
                        if st.button("✕", key=f"remove_custom_percent_{i}"):
                            remove_custom_percent_row(i)
                            st.rerun()

                next_percent_nutrient = get_next_available_percent_nutrient()

                if next_percent_nutrient is not None:
                    if st.button("+ Add another nutrient", key="add_custom_percent_row"):
                        add_custom_percent_row()
                        st.rerun()
                else:
                    st.info("All supported nutrients have already been added.")

            st.markdown("---")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Cancel", key="cancel_custom_supplement"):
                    reset_custom_nutrient_rows()
                    reset_custom_percent_rows()
                    st.session_state.show_custom_dialog = False
                    st.rerun()

            with col2:
                if st.button("Add Supplement", type="primary", key="submit_custom_supplement"):

                    if not custom_name.strip():
                        st.warning("Please enter a supplement name.")
                        return

                    if entry_mode == "percent" and recipe_grams <= 0:
                        st.warning("Serving weight is required for percent mode.")
                        return

                    if entry_mode == "amount":
                        valid_rows = [
                            row for row in st.session_state.custom_nutrient_rows
                            if float(row["amount"]) > 0
                        ]

                    elif entry_mode == "percent":
                        valid_rows = []

                        for row in st.session_state.custom_percent_rows:
                            percent_value = float(row["percent"])
                            if percent_value <= 0 or recipe_grams <= 0:
                                continue

                            converted_amount, converted_unit = convert_percent_to_amount_unit(
                                percent_value=percent_value,
                                serving_grams=recipe_grams,
                                nutrient_key=row["nutrient"]
                            )

                            valid_rows.append(
                                {
                                    "nutrient": row["nutrient"],
                                    "amount": converted_amount,
                                    "unit": converted_unit,
                                }
                            )

                    if not valid_rows:
                        st.warning("Please enter at least one nutrient amount greater than 0.")
                        return

                    try:
                        custom_key, custom_ingredient = build_custom_ingredient(
                            name=custom_name,
                            serving_label=serving_label,
                            recipe_grams=recipe_grams,
                            nutrient_rows=valid_rows,
                            ingredients=ingredients,
                            custom_index=len(st.session_state.custom_ingredients) + 1,
                        )
                    except ValueError as e:
                        st.warning(str(e))
                        return

                    st.session_state.custom_ingredients[custom_key] = custom_ingredient

                    grams_to_add = recipe_grams if recipe_grams > 0 else 100.0
                    display_grams = recipe_grams if recipe_grams > 0 else None

                    if entry_mode == "amount":
                        st.session_state["pending_custom_ingredient_to_add"] = {
                            "ingredient_key": custom_key,
                            "grams": grams_to_add,
                            "display_grams": display_grams
                        }
                    elif entry_mode == "percent" and recipe_grams > 0:
                        st.session_state["pending_custom_ingredient_to_add"] = {
                            "ingredient_key": custom_key,
                            "grams": recipe_grams,
                            "display_grams": recipe_grams
                        }

                    reset_custom_nutrient_rows()
                    reset_custom_percent_rows()
                    st.session_state.show_custom_dialog = False
                    st.rerun()

        #the supplement button
        st.subheader("Add Custom Supplement")

        st.write("Add vitamins, minerals, or other supplements not listed in the ingredient database.")

        if st.button("Add Supplement"):
            st.session_state.show_custom_dialog = True
            st.rerun()

        if st.session_state.show_custom_dialog:
            show_custom_ingredient_dialog()



    with tab3:
        #recommender tool-----
        st.subheader("Ingredient Suggestions")

        st.write(
            "Generate ingredient recommendations based on the current nutrient gaps in the recipe."
        )

        if len(st.session_state.recipe) == 0:
            st.info("Add at least one ingredient to generate recommendations.")
        else:
            if st.button("Suggest Ingredients"):
                st.session_state.ingredient_suggestions = get_top_ingredient_suggestions(
                    recipe=st.session_state.recipe,
                    ingredients=all_ingredients,
                    guidelines=guidelines,
                    top_n=3,
                    exclude_existing=False
                )
                st.session_state.suggestions_generated = True

            if st.session_state.ingredient_suggestions:
                for i, suggestion in enumerate(st.session_state.ingredient_suggestions):
                    st.markdown(
                        f"""
        **{suggestion["ingredient_name"]} — {suggestion["grams"]} g**  
        {suggestion["justification"]}  
        Overall nutrient target coverage: {suggestion["before_percent"]:.0f}% → {suggestion["after_percent"]:.0f}% (+{suggestion["delta_percent"]:.0f}%)
        """
                    )

                    if st.button(
                        f'Add {suggestion["ingredient_name"]} ({suggestion["grams"]} g)',
                        key=f"add_suggested_{i}"
                    ):
                        add_ingredient_to_recipe(
                            suggestion["ingredient_key"],
                            suggestion["grams"]
                        )
                        st.success(
                            f'Added {suggestion["ingredient_name"]} ({suggestion["grams"]} g) to recipe.'
                        )
                        st.session_state.ingredient_suggestions = []
                        st.session_state.suggestions_generated = False
                        st.rerun()

            elif st.session_state.suggestions_generated:
                st.info(
                    "No additional ingredient recommendations were identified. The recipe may already meet nutrient targets, or further additions could create imbalances."
                )

    total_calories = 0.0
    #current recipe-----
    st.subheader("Current Recipe")

    if not st.session_state.recipe:
        st.info("No ingredients added yet.")
    else:
        recipe_df = pd.DataFrame(st.session_state.recipe)

        recipe_df["display_amount"] = recipe_df["display_grams"].apply(
            lambda x: "N/A" if pd.isna(x) else f"{x:.1f}"
        )

        display_df = recipe_df[["ingredient_name", "display_amount"]].rename(
            columns={
                "ingredient_name": "Ingredient",
                "display_amount": "Amount (g)"
            }
        )

        st.dataframe(display_df, use_container_width=True)

        for item in st.session_state.recipe:
            key = item["ingredient_key"]
            grams = item["grams"]

            kcal_per_100g = all_ingredients[key]["energy_kcal"]["value"]

            if kcal_per_100g is not None:
                total_calories += (grams / 100) * kcal_per_100g

        if total_calories <= 0 and recipe_has_nutrients_but_no_calories():
            st.warning(
                "This recipe contains nutrient data but no calculable energy (kcal), so minimum and maximum targets cannot be scaled and the progress bars cannot be evaluated yet."
            )

        evaluation = evaluate_recipe(
            recipe=st.session_state.recipe,
            ingredients=all_ingredients,
            guidelines=guidelines
        )

        overall_percent = evaluation["percent"]

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Total Recipe Calories", f"{total_calories:.1f} kcal")

        with col2:
            st.metric(
                "Nutrient Target Coverage",
                f"{overall_percent:.0f}%",
                help="Percentage of recommended nutrient targets met by the recipe based on FEDIAF guidelines."
            )

        #remove ingredients section-----
        # st.write("Manage ingredients:")

        # for i, item in enumerate(st.session_state.recipe):
        #     col1, col2, col3 = st.columns([5, 2, 2])

        #     with col1:
        #         st.write(item["ingredient_name"])

        #     with col2:
        #         if item.get("display_grams") is None:
        #             st.write("N/A")
        #         else:
        #             new_amount = st.number_input(
        #                 "Amount (g)",
        #                 min_value=0.0,
        #                 value=float(item["display_grams"]),
        #                 step=1.0,
        #                 key=f"edit_amount_{i}",
        #                 label_visibility="collapsed"
        #             )

        #             if new_amount != item["display_grams"]:
        #                 st.session_state.recipe[i]["display_grams"] = new_amount
        #                 st.session_state.recipe[i]["grams"] = new_amount
        #                 st.rerun()

        #     with col3:
        #         if st.button("Remove", key=f"remove_{i}"):
        #             remove_ingredient_from_recipe(i)
        #             st.rerun()
        st.write("Remove ingredients:")

        for i, item in enumerate(st.session_state.recipe):
            col1, col2, col3 = st.columns([5, 2, 2])

            with col1:
                st.write(item["ingredient_name"])

            with col2:
                if item.get("display_grams") is None:
                    st.write("N/A")
                else:
                    st.write(f"{item['display_grams']:.1f} g")

            with col3:
                if st.button("Remove", key=f"remove_{i}"):
                    remove_ingredient_from_recipe(i)
                    st.rerun()

    #mobile version toggle
    compact_view = st.toggle(
        "Mobile view",
        value=False,
        # help="Use a stacked nutrient layout optimized for smaller screens."
    )

    #PROTEIN
    #nutrient display-----
    if len(st.session_state.recipe) == 0:
        st.info("Add ingredients to calculate nutrients.")

    else:

        with st.expander("Protein", expanded=True):

            protein_group = guidelines["adult_maintenance"]["protein_amino_acids"]

            if not compact_view:
                header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([2.5, 1.5, 4, 1, 1])
                with header_col1:
                    st.markdown("**Nutrient**")
                with header_col2:
                    st.markdown("**Amount**")
                with header_col3:
                    st.markdown("**% of min**")
                with header_col4:
                    st.markdown("**min**")
                with header_col5:
                    st.markdown("**max**")

            for nutrient_key, nutrient_info in protein_group.items():
                label = nutrient_info["label"]
                unit = nutrient_info["unit"]
                min_value = nutrient_info["minimum"]
                max_value = nutrient_info["maximum"]

                total_amount_in_recipe = get_derived_nutrient_total(nutrient_key)
                missing_ingredients = get_missing_derived_nutrient_ingredients(nutrient_key)

                scaled_min = scale_guideline_to_recipe(min_value, total_calories)
                scaled_max = scale_guideline_to_recipe(max_value, total_calories)

                render_nutrient_row(
                    label=label,
                    amount=total_amount_in_recipe,
                    unit=unit,
                    min_value=scaled_min,
                    max_value=scaled_max,
                    missing_ingredients=missing_ingredients
                )

        #FAT
        #nutrient display-----
        with st.expander("Fat", expanded=True):

            fat_keys_to_show = ["fat", "linoleic_acid"]
            fat_group = guidelines["adult_maintenance"]["fat_fatty_acids"]
            if not compact_view:
                header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([2.5, 1.5, 4, 1, 1])
                with header_col1:
                    st.markdown("**Nutrient**")
                with header_col2:
                    st.markdown("**Amount**")
                with header_col3:
                    st.markdown("**% of min**")
                with header_col4:
                    st.markdown("**min**")
                with header_col5:
                    st.markdown("**max**")

            for nutrient_key in fat_keys_to_show:
                nutrient_info = fat_group[nutrient_key]

                label = nutrient_info["label"]
                unit = nutrient_info["unit"]
                min_value = nutrient_info["minimum"]
                max_value = nutrient_info["maximum"]

                total_amount_in_recipe = get_nutrient_total_in_recipe(nutrient_key)
                missing_ingredients = get_missing_nutrient_ingredients(nutrient_key)

                scaled_min = scale_guideline_to_recipe(min_value, total_calories)
                scaled_max = scale_guideline_to_recipe(max_value, total_calories)

                render_nutrient_row(
                    label=label,
                    amount=total_amount_in_recipe,
                    unit=unit,
                    min_value=scaled_min,
                    max_value=scaled_max,
                    missing_ingredients=missing_ingredients
                )

        #MINERALS
        #nutrient display-----
        with st.expander("Minerals", expanded=True):

            mineral_keys_to_show = [
                "calcium",
                "phosphorus",
                "ca_p_ratio",
                "potassium",
                "sodium",
                "chloride",
                "magnesium"
            ]

            mineral_group = guidelines["adult_maintenance"]["minerals"]

            if not compact_view:
                header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([2.5, 1.5, 4, 1, 1])
                with header_col1:
                    st.markdown("**Nutrient**")
                with header_col2:
                    st.markdown("**Amount**")
                with header_col3:
                    st.markdown("**% of min**")
                with header_col4:
                    st.markdown("**min**")
                with header_col5:
                    st.markdown("**max**")

            for nutrient_key in mineral_keys_to_show:

                if nutrient_key == "ca_p_ratio":

                    label = "Calcium : Phosphorus Ratio"
                    min_ratio = 1.0
                    max_ratio = 2.0

                    total_calcium = get_nutrient_total_in_recipe("calcium")
                    total_phosphorus = get_nutrient_total_in_recipe("phosphorus")

                    if total_phosphorus > 0:
                        ratio_value = total_calcium / total_phosphorus
                        ratio_display = f"{ratio_value:.2f} : 1"

                        if ratio_value < min_ratio:
                            status = "Calcium too low relative to phosphorus"
                        elif ratio_value <= max_ratio:
                            status = "Balanced calcium to phosphorus ratio"
                        else:
                            status = "Calcium too high relative to phosphorus"
                    else:
                        ratio_display = "N/A"
                        status = "Phosphorus required to calculate ratio"

                    if compact_view:
                        st.markdown(f"**{label}**")
                        st.caption(f"Amount: {ratio_display} • Min: 1 : 1 • Max: 2 : 1")
                        st.caption(status)
                        st.markdown("---")
                    else:
                        col1, col2, col3, col4, col5 = st.columns([2.5, 1.5, 4, 1, 1])

                        with col1:
                            st.write(label)

                        with col2:
                            st.write(ratio_display)

                        with col3:
                            st.write("")
                            st.caption(status)
                            st.write("")

                        with col4:
                            st.write("1 : 1")

                        with col5:
                            st.write("2 : 1")
                else:
                    nutrient_info = mineral_group[nutrient_key]

                    label = nutrient_info["label"]
                    unit = nutrient_info["unit"]
                    min_value = nutrient_info["minimum"]
                    max_value = nutrient_info["maximum"]

                    total_amount_in_recipe = get_nutrient_total_in_recipe(nutrient_key)
                    missing_ingredients = get_missing_nutrient_ingredients(nutrient_key)

                    scaled_min = scale_guideline_to_recipe(min_value, total_calories)
                    scaled_max = scale_guideline_to_recipe(max_value, total_calories)

                    render_nutrient_row(
                        label=label,
                        amount=total_amount_in_recipe,
                        unit=unit,
                        min_value=scaled_min,
                        max_value=scaled_max,
                        missing_ingredients=missing_ingredients
                    )

        #TRACE ELEMENTS
        #nutrient display-----
        with st.expander("Trace Elements", expanded=True):

            trace_keys_to_show = [
                "copper",
                "iodine",
                "iron",
                "manganese",
                "selenium_wet",
                "zinc"
            ]

            trace_group = guidelines["adult_maintenance"]["trace_elements"]

            if not compact_view:
                header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([2.5, 1.5, 4, 1, 1])
                with header_col1:
                    st.markdown("**Nutrient**")
                with header_col2:
                    st.markdown("**Amount**")
                with header_col3:
                    st.markdown("**% of min**")
                with header_col4:
                    st.markdown("**min**")
                with header_col5:
                    st.markdown("**max**")

            for nutrient_key in trace_keys_to_show:
                nutrient_info = trace_group[nutrient_key]

                label = nutrient_info["label"]
                unit = nutrient_info["unit"]
                min_value = nutrient_info["minimum"]
                max_value = nutrient_info["maximum"]

                total_amount_in_recipe = get_nutrient_total_in_recipe(nutrient_key)
                missing_ingredients = get_missing_nutrient_ingredients(nutrient_key)

                scaled_min = scale_guideline_to_recipe(min_value, total_calories)
                scaled_max = scale_guideline_to_recipe(max_value, total_calories)

                render_nutrient_row(
                    label=label,
                    amount=total_amount_in_recipe,
                    unit=unit,
                    min_value=scaled_min,
                    max_value=scaled_max,
                    missing_ingredients=missing_ingredients
                )

        #VITAMINS
        #nutrient display-----
        with st.expander("Vitamins", expanded=True):

            vitamin_keys_to_show = [
                "vitamin_a",
                "vitamin_d",
                "vitamin_e",
                "vitamin_b1",
                "vitamin_b2",
                "vitamin_b5",
                "vitamin_b6",
                "vitamin_b12",
                "vitamin_b3",
                "vitamin_b9",
                "choline",
            ]

            vitamin_group = guidelines["adult_maintenance"]["vitamins"]

            if not compact_view:

                header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([2.5, 1.5, 4, 1, 1])
                with header_col1:
                    st.markdown("**Nutrient**")
                with header_col2:
                    st.markdown("**Amount**")
                with header_col3:
                    st.markdown("**% of min**")
                with header_col4:
                    st.markdown("**min**")
                with header_col5:
                    st.markdown("**max**")

            for nutrient_key in vitamin_keys_to_show:
                nutrient_info = vitamin_group[nutrient_key]

                label = nutrient_info["label"]
                unit = nutrient_info["unit"]
                min_value = nutrient_info["minimum"]
                max_value = nutrient_info["maximum"]

                total_amount_in_recipe = get_nutrient_total_in_recipe(nutrient_key)
                missing_ingredients = get_missing_nutrient_ingredients(nutrient_key)

                scaled_min = scale_guideline_to_recipe(min_value, total_calories)
                scaled_max = scale_guideline_to_recipe(max_value, total_calories)

                render_nutrient_row(
                    label=label,
                    amount=total_amount_in_recipe,
                    unit=unit,
                    min_value=scaled_min,
                    max_value=scaled_max,
                    missing_ingredients=missing_ingredients
                )
        
        #donut chart macronutrient display-----
        with st.expander("Macronutrient Distribution", expanded=True):

            protein_g = get_nutrient_total_in_recipe("protein")
            fat_g = get_nutrient_total_in_recipe("fat")
            carbs_g = get_nutrient_total_in_recipe("carbohydrate")

            #convert to kcal
            protein_kcal = protein_g * 4
            fat_kcal = fat_g * 9
            carbs_kcal = carbs_g * 4

            values = [protein_kcal, fat_kcal, carbs_kcal]

            total = sum(values)
            if total == 0:
                st.info("No macronutrient data available.")
            else:
                labels = [
                    f"Protein ({(protein_kcal/total)*100:.0f}%)",
                    f"Fat ({(fat_kcal/total)*100:.0f}%)",
                    f"Carbs ({(carbs_kcal/total)*100:.0f}%)"
                ]

                import plotly.graph_objects as go

                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=labels,
                            values=values,
                            hole=0.6
                        )
                    ]
                )

                fig.update_layout(
                    title="Caloric Distribution",
                    showlegend=True,
                    annotations=[
                        dict(
                            text=f"<b>{total_calories:.0f}</b><br>kcal",
                            x=0.5,
                            y=0.5,
                            font=dict(size=22, color="#333"),
                            showarrow=False
                        )
                    ]
                )

                st.plotly_chart(fig, use_container_width=True)

                st.caption(
                "Macronutrient ratios are not defined by FEDIAF guidelines, which instead specify nutrient requirements per 1000 kcal. "
                "This chart is provided for informational purposes to help visualize the caloric contribution of protein, fat, and carbohydrates."
                )

    st.markdown("---")

        #dropdown-----
    with st.expander("Data Sources & Methodology"):
        st.markdown("""

    *For educational use only. This tool does not replace veterinary advice and is not intended for puppies, pregnant dogs, or medically managed diets.*
                        
    **Data sources**
    - The Canadian Nutrient File (CNF) is the primary source of nutrient data for ingredients in this calculator.
                    
    - Iodized salt uses nutrient values from USDA FoodData Central because iodine values are not reported for salt in CNF.
                    
    - Certain ingredients labeled “(supplement, averaged)” were added manually. Additional details about these ingredients are provided in the Supplements section below.
                    
    - The ingredient nutrient dataset used by this calculator is available for download in JSON format below.
    """)
        
        with open("data/ingredients.json", "rb") as file:
            st.download_button(
                label="Download ingredient nutrient dataset (JSON)",
                data=file,
                file_name="ingredients.json",
                mime="application/json"
            )
    
        st.markdown("""
    
    **Predefined supplements (included in dataset)**
    - Four predefined supplements were included in the calculator and are labeled "(supplement, averaged)". These include: eggshell powder, fish oil, bone meal, and calcium carbonate.
    
    - Nutrient values for these were calculated as averages from several commercial supplement products. The products used for these calculations are documented in the downloadable spreadsheet below.
    
    - Only the primary nutrients typically supplied by each supplement were recorded (e.g., calcium for eggshell powder and calcium carbonate; calcium and phosphorus for bone meal; calories, total fat, EPA, and DHA for fish oil). Trace nutrients that may be present in small amounts were not recorded.
    """)
        
        with open("data/supplement_average_sources.xlsx", "rb") as file:
            st.download_button(
                label="Download supplement average source data",
                data=file,
                file_name="supplement_average_sources.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
        st.markdown("""
                    
        **Custom supplements (user-entered)**
        - Users can create custom supplements by entering nutrient amounts directly or by converting label percentages using a specified serving weight.

        - Only the nutrients entered by the user are included in calculations. Nutrients not provided are treated as unknown and are not counted toward totals or recommendations.

        - Percentage values are interpreted as percent by weight of the product using: amount = serving weight × (% / 100)

        - Users are responsible for correctly interpreting supplement labels, including units, serving sizes, and percentage values.
                    

        **Iodine and Chloride**
        - The Canadian Nutrient File (CNF) does not report iodine or chloride values for any of the foods included in this calculator.

        - Iodine levels in foods can vary widely depending on environmental factors such as soil and water iodine content.

        - Chloride is rarely reported in food composition databases because it is typically present as sodium chloride (salt) and is therefore often inferred from sodium rather than measured directly.

        - In this calculator, iodine and chloride are supplied through iodized salt, which provides a consistent and measurable source of these nutrients. Table salt is listed in the Canadian Nutrient File (CNF), but iodine values are not reported for it. Therefore, nutrient values for iodized salt were obtained from USDA FoodData Central.

        - Chloride for iodized salt was calculated from sodium assuming sodium chloride composition (Cl = Na × 1.54).

                     
        **Nutrient Guidelines**
        - Recommended nutrient levels used by this calculator are based on the FEDIAF Nutritional Guidelines for Complete and Complementary Pet Food for Cats and Dogs (2025), Table III-3b.

        - The calculator uses the recommended nutrient allowances for adult dogs expressed per 1000 kcal of metabolizable energy, based on an assumed energy requirement of 95 kcal/kg body weight.
                    
        - These guidelines apply to healthy adult dogs and are not intended for puppies, pregnant or lactating dogs, or dogs with medical conditions.

        - Minimum and maximum nutrient values displayed in the calculator are scaled according to the total caloric content of the recipe.
                    
        - The nutrient guideline dataset used by this calculator is derived from the FEDIAF recommendations and is available for download in JSON format below.
        """)
        
        with open("data/guidelines.json", "rb") as file:
            st.download_button(
                label="Download nutrient guideline dataset (JSON)",
                data=file,
                file_name="guidelines.json",
                mime="application/json"
            )
    
        st.markdown("""                                
        **Overall Nutrient Target Coverage**
                    
        The overall nutrient target coverage represents the percentage of nutrient targets that fall within recommended ranges for the current recipe. Each nutrient is evaluated against minimum and, where applicable, maximum guideline values scaled to the recipe’s total energy. A nutrient is counted as “met” only if it is within this acceptable range. Values below the minimum or above the maximum are considered unmet. The final percentage reflects the proportion of all evaluated nutrients that meet these criteria.   

                    
        **Ingredient Recommendation Method**
                    
        The ingredient recommendation tool simulates adding candidate ingredients in practical amounts and recalculates overall nutrient target coverage for each option. Candidates are scored based on how much they improve coverage. For each ingredient, the best-performing tested amount is kept, and the top suggestions are shown along with the nutrients that improve the most. Recommendations are limited to the tested ingredients and amounts and may not identify all possible improvements.

                    
        **Assumptions and limitations**
        - Nutrient values are derived from food composition databases and do not account for nutrient losses during cooking, processing, or storage.

        - The ingredient list in this calculator is limited and does not represent a complete food composition database.

        - Meeting recommended nutrient targets in this calculator does not guarantee that a recipe is fully balanced or appropriate for all dogs.
                    

        **Progress bar interpretation**
        - Nutrient progress bars represent progress toward the recommended minimum nutrient requirement. The bar reaches 100% when the minimum requirement is met.
                    
        - If a nutrient has a defined maximum value, the percentage may exceed 100% only when the amount surpasses that maximum.
            
        - When no maximum value is defined, the progress bar remains capped at 100% once the minimum requirement is met.
                    

        **Missing nutrient data**
        - A `*` next to a nutrient indicates that one or more ingredients in the recipe have missing source data for that nutrient.
                    
        - Totals may therefore be underestimated.
                    
        - Supplements labeled “(supplement, averaged)” intentionally include only selected primary nutrients, while iodized salt contains only a limited set of reported nutrients from source data. These ingredients do not trigger missing-data warnings for nutrients that were not recorded.
         

        **References**
        - Canadian Nutrient File – Health Canada  
        https://food-nutrition.canada.ca/cnf-fce/

        - FAO/INFOODS. Guidelines for Food Composition Data Management and Use  
        https://www.fao.org/infoods/infoods/standards-guidelines/en/

        - FEDIAF. Nutritional Guidelines for Complete and Complementary Pet Food for Cats and Dogs (2025)  
        https://fediaf.org/self-regulation/nutrition/

        - USDA FoodData Central  
        https://fdc.nal.usda.gov/
        """)

    # st.markdown(
    #     "Built by Jessie Allen • github.com/jallen244"
    # )

    st.markdown(
        "Have feedback or suggestions? [Submit an issue on GitHub](https://github.com/jallen244/dog-food-calculator/issues) or email [jallen.apps@gmail.com](mailto:jallen.apps@gmail.com)."
    )