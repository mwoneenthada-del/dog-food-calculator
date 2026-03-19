import json
import streamlit as st
import pandas as pd
from recommender import get_top_ingredient_suggestions
from recommender import evaluate_recipe

st.set_page_config(page_title="Dog Food Calculator", layout="wide")

left, center, right = st.columns([1, 2, 1])

with center:

    #load ingredient data-----
    with open("data/ingredients.json", "r", encoding="utf-8") as f:
        ingredient_data = json.load(f)

    ingredients = ingredient_data["ingredients"]


    #load nutrient guidlines-----
    with open("data/guidelines.json", "r", encoding="utf-8") as f:
        guidelines = json.load(f)


    #session state-----
    if "recipe" not in st.session_state:
        st.session_state.recipe = []

    if "ingredient_suggestions" not in st.session_state:
        st.session_state.ingredient_suggestions = []

    if "suggestions_generated" not in st.session_state:
        st.session_state.suggestions_generated = False

    #helper functions-----
    def add_ingredient_to_recipe(ingredient_key, grams):

        ingredient_name = ingredients[ingredient_key]["name"]

        #check if ingredient already exists in recipe
        for item in st.session_state.recipe:
            if item["ingredient_key"] == ingredient_key:
                item["grams"] += grams
                return

        #add new entry if it doesn't exist yet
        st.session_state.recipe.append({
            "ingredient_key": ingredient_key,
            "ingredient_name": ingredient_name,
            "grams": grams
        })


    def remove_ingredient_from_recipe(index: int):
        st.session_state.recipe.pop(index)


    def scale_guideline_to_recipe(guideline_value, total_calories):
        if guideline_value is None:
            return None
        if total_calories is None or total_calories <= 0:
            return 0
        return guideline_value * (total_calories / 1000)
    
    def get_missing_nutrient_ingredients(nutrient_key):
        missing_ingredients = []

        for item in st.session_state.recipe:
            ingredient_key = item["ingredient_key"]
            ingredient_name = item["ingredient_name"]

            ingredient_info = ingredients[ingredient_key]

            #skip salt and supplements 
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

            nutrient_data = ingredients[ingredient_key]["nutrients"].get(nutrient_key)

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


    def render_nutrient_row(label, amount, unit, min_value, max_value, missing_ingredients=None):
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

                #only go above 100 if there is a max and amount exceeds max
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

    #app title-----
    st.title("Homemade Dog Food Nutrition Calculator")

    st.write(
    "**Note: This calculator is for educational purposes only and does not replace professional veterinary advice."
    )

    st.write(
        "Based on FEDIAF adult maintenance guidelines for healthy adult dogs. Not intended for puppies, pregnant, or medically managed diets."
    )
    
    st.write("Build a recipe by selecting ingredients and entering the amount in grams.")

    #dropdown-----
    with st.expander("Data Notes & Assumptions"):
        st.markdown("""
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
    
    **Supplements**
    - Four supplements were included in the calculator and are labeled "(supplement, averaged)". These include: eggshell powder, fish oil, bone meal, and calcium carbonate.
    
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

        **Calculation method**
        - Recipe energy is calculated using metabolizable energy values from the Canadian Nutrient File (kcal per 100 g) and scaled according to the amount of each ingredient used.

        - Nutrient totals are calculated by summing the contribution of each ingredient based on its reported nutrient values per 100 g.

        - Recommended nutrient ranges are based on FEDIAF nutritional guidelines for adult dogs and are scaled according to the total caloric content of the recipe.

        - Some nutrients shown in the calculator (such as methionine + cystine and phenylalanine + tyrosine) are calculated by combining related amino acids.
         
                    
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

        """)                   
        st.warning(
            "This calculator is intended for educational purposes and should not replace veterinary nutritional guidance."
        )
        st.markdown("""          

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

    #add ingredients form-----
    st.subheader("Add Ingredient")

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
                ingredients=ingredients,
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


    #current recipe-----
    st.subheader("Current Recipe")

    if not st.session_state.recipe:
        st.info("No ingredients added yet.")
    else:
        recipe_df = pd.DataFrame(st.session_state.recipe)

        display_df = recipe_df[["ingredient_name", "grams"]].rename(
            columns={
                "ingredient_name": "Ingredient",
                "grams": "Amount (g)"
            }
        )

        st.dataframe(display_df, use_container_width=True)
        
        #calculate recipe calories
        total_calories = 0

        for item in st.session_state.recipe:
            key = item["ingredient_key"]
            grams = item["grams"]

            kcal_per_100g = ingredients[key]["energy_kcal"]["value"]

            if kcal_per_100g is not None:
                total_calories += (grams / 100) * kcal_per_100g

        evaluation = evaluate_recipe(
            recipe=st.session_state.recipe,
            ingredients=ingredients,
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
        st.write("Remove ingredients:")

        for i, item in enumerate(st.session_state.recipe):
            col1, col2, col3 = st.columns([5, 2, 2])

            with col1:
                st.write(item["ingredient_name"])

            with col2:
                st.write(f"{item['grams']:.1f} g")

            with col3:
                if st.button("Remove", key=f"remove_{i}"):
                    remove_ingredient_from_recipe(i)
                    st.rerun()

    #PROTEIN
    #nutrient display-----
    if len(st.session_state.recipe) == 0:
        st.info("Add ingredients to calculate nutrients.")

    else:

        with st.expander("Protein", expanded=True):

            protein_group = guidelines["adult_maintenance"]["protein_amino_acids"]

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