"""
Cross-checks AI-generated meal items against real nutrition data.

Lookup order for every food item:
1. INDIAN_FOOD_DB (local, hand-verified, instant, free) — checked first
   because it covers common Indian dishes far more accurately than USDA.
2. USDA FoodData Central API (fallback) — used only when the item isn't
   found locally, e.g. less common or Continental-style items.

If neither source has the item, it is silently skipped (not flagged) —
we only warn when we have real data to compare against.
"""

import os
import re
import requests

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# Hand-verified reference values for common Indian foods.
# Values are per the stated typical serving ("per"), sourced from IFCT-style
# references. Extend this dictionary over time — it is the most reliable
# and lowest-latency source available.
INDIAN_FOOD_DB = {
    "roti":        {"calories": 80,  "protein": 3,  "carbs": 15, "fats": 0.7, "grams": 40},
    "chapati":     {"calories": 80,  "protein": 3,  "carbs": 15, "fats": 0.7, "grams": 40},
    "dal":         {"calories": 116, "protein": 9,  "carbs": 20, "fats": 0.4, "grams": 200},
    "paneer":      {"calories": 265, "protein": 18, "carbs": 6,  "fats": 20,  "grams": 100},
    "brown rice":  {"calories": 216, "protein": 5,  "carbs": 45, "fats": 1.8, "grams": 195},
    "white rice":  {"calories": 205, "protein": 4,  "carbs": 45, "fats": 0.4, "grams": 158},
    "boiled egg":  {"calories": 78,  "protein": 6,  "carbs": 0.6,"fats": 5,   "grams": 50},
    "poha":        {"calories": 250, "protein": 6,  "carbs": 35, "fats": 10,  "grams": 200},
    "idli":        {"calories": 39,  "protein": 2,  "carbs": 8,  "fats": 0.2, "grams": 40},
    "dosa":        {"calories": 133, "protein": 3,  "carbs": 19, "fats": 5,   "grams": 80},
    "curd":        {"calories": 60,  "protein": 3.5,"carbs": 4.7,"fats": 3.3, "grams": 100},
    "khichdi":     {"calories": 180, "protein": 6,  "carbs": 30, "fats": 4,   "grams": 200},
    "rajma":       {"calories": 140, "protein": 9,  "carbs": 23, "fats": 0.5, "grams": 200},
    "chole":       {"calories": 160, "protein": 8,  "carbs": 27, "fats": 3,   "grams": 200},
    "banana":      {"calories": 105, "protein": 1.3,"carbs": 27, "fats": 0.4, "grams": 120},
    "almonds":     {"calories": 7,   "protein": 0.25,"carbs": 0.2,"fats": 0.6,"grams": 1},
    "chicken breast": {"calories": 165, "protein": 31,"carbs": 0,  "fats": 3.6, "grams": 100},
}


def get_usda_api_key():
    return os.getenv("USDA_API_KEY")


def extract_grams_from_item(item_text: str):
    """'2 Roti (medium, ~40g each)' -> ('roti', 80.0)
    '100g Paneer' -> ('paneer', 100.0)
    Returns (food_name_lower, total_grams) or (food_name_lower, None) if no
    quantity could be parsed."""
    gram_match = re.search(r'~?(\d+)\s*g', item_text)
    count_match = re.match(r'^(\d+)\s+', item_text.strip())

    food_name = re.sub(r'\(.*?\)', '', item_text)
    food_name = re.sub(r'^\d+\s*g?\s*', '', food_name, flags=re.IGNORECASE).strip().lower()

    if gram_match:
        per_unit_grams = float(gram_match.group(1))
        count = int(count_match.group(1)) if (count_match and "each" in item_text.lower()) else 1
        return food_name, per_unit_grams * count

    return food_name, None


def lookup_local(food_name: str):
    """Checks INDIAN_FOOD_DB for a substring match. Returns per-gram
    nutrition data or None."""
    for key, data in INDIAN_FOOD_DB.items():
        if key in food_name:
            grams = data["grams"]
            return {
                "source": "local",
                "matched_name": key,
                "calories_per_g": data["calories"] / grams,
                "protein_per_g": data["protein"] / grams,
                "carbs_per_g": data["carbs"] / grams,
                "fats_per_g": data["fats"] / grams,
            }
    return None


def lookup_usda(food_name: str):
    """Falls back to the USDA API when the item isn't in the local dataset.
    Returns per-gram nutrition data or None if unavailable/not found."""
    api_key = get_usda_api_key()
    if not api_key:
        return None
    try:
        response = requests.get(
            f"{USDA_BASE_URL}/foods/search",
            params={
                "api_key": api_key,
                "query": food_name,
                "pageSize": 1,
                "dataType": ["Foundation", "SR Legacy"],
            },
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("foods"):
            return None

        food = data["foods"][0]
        nutrients = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", [])}
        # USDA values are per 100g
        return {
            "source": "usda",
            "matched_name": food.get("description", food_name),
            "calories_per_g": nutrients.get("Energy", 0) / 100,
            "protein_per_g": nutrients.get("Protein", 0) / 100,
            "carbs_per_g": nutrients.get("Carbohydrate, by difference", 0) / 100,
            "fats_per_g": nutrients.get("Total lipid (fat)", 0) / 100,
        }
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None


def verify_plan_nutrition(plan: dict, tolerance: float = 0.35) -> list:
    """Scans every meal item in the plan, looks it up (local DB first, USDA
    fallback), and flags items whose claimed per-meal calorie contribution
    looks very inconsistent with real data. This is a coarse sanity check,
    not an exact audit — quantities and mixed dishes make exact matching
    hard, so we only flag large (>tolerance) discrepancies.

    Returns a list of human-readable warning strings (empty = nothing
    flagged, either because everything matched or because items couldn't
    be looked up)."""
    warnings = []
    meals = plan.get("Meals", {})

    for meal_name, meal_details in meals.items():
        items = meal_details.get("Items", [])
        if not items:
            continue

        # We don't have a claimed calorie value per item (only per meal),
        # so we sanity-check the total: sum of looked-up items vs meal total.
        looked_up_calories = 0
        matched_any = False

        for item in items:
            food_name, grams = extract_grams_from_item(item)
            if grams is None:
                continue

            match = lookup_local(food_name) or lookup_usda(food_name)
            if match is None:
                continue

            matched_any = True
            looked_up_calories += match["calories_per_g"] * grams

        if not matched_any:
            continue  # nothing in this meal could be verified — skip silently

        claimed_calories = meal_details.get("Calories", 0) or 0
        if claimed_calories == 0:
            continue

        diff = abs(looked_up_calories - claimed_calories) / claimed_calories
        if diff > tolerance:
            warnings.append(
                f"{meal_name}: claimed {claimed_calories} kcal, but looked-up "
                f"ingredients suggest ~{round(looked_up_calories)} kcal — "
                "worth double-checking."
            )

    return warnings
