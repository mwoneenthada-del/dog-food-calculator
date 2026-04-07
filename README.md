# Dog Food Nutrition Calculator

A Streamlit application for building and evaluating homemade dog food recipes using FEDIAF nutritional guidelines.

Created by Jessie Allen.

---

## Overview

This tool allows users to construct dog food recipes from individual ingredients and evaluate their nutritional profile against established guidelines for adult dogs.

It is designed for educational use and general formulation guidance, not as a substitute for veterinary advice.

---

## Features

- Build recipes using ingredient data from the Canadian Nutrient File (CNF)
- Calculate total calories and nutrient contributions
- Compare nutrients against FEDIAF adult maintenance recommendations
- View progress toward minimum and maximum nutrient targets
- Identify missing nutrient data across ingredients
- Add custom supplements with:
  - Exact nutrient amounts (g, mg, IU, etc.)
  - Percentage-based label conversion using serving weight
- Generate ingredient suggestions to improve nutrient coverage
- Visualize macronutrient distribution

---

## Data Sources

- Canadian Nutrient File (CNF) – primary ingredient nutrient data
- USDA FoodData Central – iodized salt nutrient values
- FEDIAF Nutritional Guidelines (2025) – recommended nutrient targets

Certain supplements included in the dataset are averaged from multiple commercial products and include only their primary nutrients.

---

## Calculation Method

- Nutrient values are based on reported values per 100 g of each ingredient
- Total nutrient amounts are calculated by summing contributions across the recipe
- Energy is calculated using metabolizable energy values (kcal per 100 g)
- Nutrient targets are scaled relative to total recipe energy (per 1000 kcal)
- Some nutrients are derived by combining related values (e.g., methionine + cystine)

---

## Limitations

- Intended for healthy adult dogs only
- Not suitable for puppies, pregnant, or medically managed diets
- Does not account for nutrient loss during cooking or processing
- Ingredient dataset is limited and not exhaustive
- Missing nutrient data may result in underestimation of totals

---

## Running Locally

Clone the repository:

```bash
git clone https://github.com/jallen244/dog-food-calculator.git
cd dog-food-calculator
```
