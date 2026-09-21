"""
Authoritative nutrition calculation engine for the Diet Planner.

Design principle: the AI (LLM) is ONLY trusted to pick food items and
realistic quantities. It is never trusted to compute calories, protein,
carbs, or fats — those are always calculated here, deterministically, from
a verified nutrition database. This guarantees that displayed numbers
always match the actual food items, and that
Calories == Protein*4 + Carbs*4 + Fats*9 by construction (never a separate,
possibly-inconsistent number).

Lookup order for every food item:
1. FOOD_DB (local, hand-curated, instant, free) — covers common Indian and
   generic foods. Checked first because it's far more reliable for Indian
   dishes than any generic API.
2. USDA FoodData Central API (fallback) — used only when the item isn't in
   FOOD_DB.
3. If neither source has the item, it is marked "unmatched" and EXCLUDED
   from the totals — we never guess a number for something we can't verify.

NOTE FOR MAINTAINERS: FOOD_DB values are reasonable per-100g approximations
suitable for a general fitness app. For clinical/medical-grade accuracy,
replace/extend these with values from the official IFCT (Indian Food
Composition Tables) or a licensed nutrition database.
"""

import os
import re
import requests

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# ---------------------------------------------------------------------------
# Local nutrition database — values are per 100g (protein/carbs/fats in
# grams). "default_grams" is the typical weight of ONE serving/piece, used
# when the AI gives a count without an explicit gram quantity
# (e.g. "Chicken Breast" -> assumed 100g; "2 Roti" -> 2 x 40g).
# ---------------------------------------------------------------------------
FOOD_DB = {
    # Grains / breads
    "roti":            {"protein": 7,   "carbs": 45, "fats": 4,    "default_grams": 40},
    "naan":            {"protein": 9,   "carbs": 50, "fats": 8,    "default_grams": 90},
    "paratha":         {"protein": 6,   "carbs": 40, "fats": 13,   "default_grams": 60},
    "bread":           {"protein": 9,   "carbs": 49, "fats": 3,    "default_grams": 30},
    "brown rice":      {"protein": 2.6, "carbs": 23, "fats": 0.9,  "default_grams": 195},
    "white rice":      {"protein": 2.7, "carbs": 28, "fats": 0.3,  "default_grams": 158},
    "poha":            {"protein": 3,   "carbs": 27, "fats": 4,    "default_grams": 200},
    "idli":            {"protein": 3,   "carbs": 20, "fats": 0.5,  "default_grams": 40},
    "dosa":            {"protein": 4,   "carbs": 26, "fats": 4,    "default_grams": 80},
    "upma":            {"protein": 4,   "carbs": 26, "fats": 4.5,  "default_grams": 180},
    "khichdi":         {"protein": 3.5, "carbs": 17, "fats": 2.2,  "default_grams": 200},
    "oats":            {"protein": 13.5,"carbs": 68, "fats": 6.5,  "default_grams": 40},
    "quinoa":          {"protein": 4.4, "carbs": 21, "fats": 1.9,  "default_grams": 185},
    "pasta":           {"protein": 5,   "carbs": 25, "fats": 1.1,  "default_grams": 140},
    "noodles":         {"protein": 4.5, "carbs": 25, "fats": 2,    "default_grams": 140},

    # Legumes / pulses
    "dal":             {"protein": 5,   "carbs": 12, "fats": 0.5,  "default_grams": 200},
    "rajma":           {"protein": 5,   "carbs": 14, "fats": 0.5,  "default_grams": 200},
    "chole":           {"protein": 5,   "carbs": 15, "fats": 1.8,  "default_grams": 200},
    "sprouts":         {"protein": 7,   "carbs": 12, "fats": 0.5,  "default_grams": 100},

    # Dairy & dairy-free alternatives (checked with longest-key-first so
    # "soy milk" matches before generic "milk")
    "paneer":          {"protein": 18,  "carbs": 4,  "fats": 20,   "default_grams": 100},
    "curd":            {"protein": 3.5, "carbs": 4.7,"fats": 3.3,  "default_grams": 100},
    "greek yogurt":    {"protein": 10,  "carbs": 4,  "fats": 0.4,  "default_grams": 150},
    "soy milk":        {"protein": 3.3, "carbs": 1.8,"fats": 1.6,  "default_grams": 240},
    "almond milk":     {"protein": 0.5, "carbs": 0.6,"fats": 1.1,  "default_grams": 240},
    "oat milk":        {"protein": 1,   "carbs": 7,  "fats": 1.5,  "default_grams": 240},
    "coconut milk":    {"protein": 2.3, "carbs": 3.3,"fats": 24,   "default_grams": 240},
    "milk":            {"protein": 3.2, "carbs": 4.8,"fats": 3.3,  "default_grams": 240},
    "cheese":          {"protein": 25,  "carbs": 1.3,"fats": 33,   "default_grams": 30},
    "ghee":            {"protein": 0,   "carbs": 0,  "fats": 100,  "default_grams": 5},
    "butter":          {"protein": 0.9, "carbs": 0.1,"fats": 81,   "default_grams": 10},

    # Proteins
    "egg white":       {"protein": 11,  "carbs": 0.7,"fats": 0.2,  "default_grams": 33},
    "boiled egg":      {"protein": 13,  "carbs": 1.1,"fats": 11,   "default_grams": 50},
    "chicken breast":  {"protein": 31,  "carbs": 0,  "fats": 3.6,  "default_grams": 100},
    "salmon":          {"protein": 20,  "carbs": 0,  "fats": 13,   "default_grams": 100},
    "tuna":            {"protein": 28,  "carbs": 0,  "fats": 1.3,  "default_grams": 100},
    "prawns":          {"protein": 24,  "carbs": 0.2,"fats": 0.3,  "default_grams": 100},
    "fish":            {"protein": 22,  "carbs": 0,  "fats": 5,    "default_grams": 100},
    "tofu":            {"protein": 8,   "carbs": 1.9,"fats": 4.8,  "default_grams": 100},
    "whey protein":    {"protein": 80,  "carbs": 8,  "fats": 6,    "default_grams": 30},
    "protein shake":   {"protein": 80,  "carbs": 8,  "fats": 6,    "default_grams": 30},
    "soya chunks":     {"protein": 52,  "carbs": 33, "fats": 0.5,  "default_grams": 50},

    # Fruits & vegetables
    "banana":          {"protein": 1.1, "carbs": 23, "fats": 0.3,  "default_grams": 120},
    "apple":           {"protein": 0.3, "carbs": 14, "fats": 0.2,  "default_grams": 150},
    "orange":          {"protein": 0.9, "carbs": 12, "fats": 0.1,  "default_grams": 130},
    "mango":           {"protein": 0.8, "carbs": 15, "fats": 0.4,  "default_grams": 150},
    "papaya":          {"protein": 0.5, "carbs": 11, "fats": 0.3,  "default_grams": 150},
    "avocado":         {"protein": 2,   "carbs": 8.5,"fats": 15,   "default_grams": 100},
    "broccoli":        {"protein": 2.8, "carbs": 7,  "fats": 0.4,  "default_grams": 90},
    "spinach":         {"protein": 2.9, "carbs": 3.6,"fats": 0.4,  "default_grams": 90},
    "sweet potato":    {"protein": 1.6, "carbs": 20, "fats": 0.1,  "default_grams": 130},
    "potato":          {"protein": 2,   "carbs": 17, "fats": 0.1,  "default_grams": 150},
    "sabzi":           {"protein": 2.5, "carbs": 10, "fats": 3,    "default_grams": 150},
    "saag":            {"protein": 3.5, "carbs": 6,  "fats": 6,    "default_grams": 150},
    "saag aloo":       {"protein": 3,   "carbs": 12, "fats": 5.5,  "default_grams": 200},
    "aloo gobi":       {"protein": 2.5, "carbs": 12, "fats": 4,    "default_grams": 150},
    "aloo":            {"protein": 2,   "carbs": 17, "fats": 0.1,  "default_grams": 150},
    "baingan bharta":  {"protein": 2,   "carbs": 8,  "fats": 5,    "default_grams": 150},
    "mixed vegetable curry": {"protein": 2.5, "carbs": 10, "fats": 3.5, "default_grams": 150},
    "palak paneer":    {"protein": 8,   "carbs": 5,  "fats": 13,   "default_grams": 150},
    "paneer bhurji":   {"protein": 14,  "carbs": 4,  "fats": 16,   "default_grams": 100},
    "paneer tikka":    {"protein": 16,  "carbs": 5,  "fats": 15,   "default_grams": 100},
    "matar paneer":    {"protein": 9,   "carbs": 8,  "fats": 12,   "default_grams": 150},
    "dal makhani":     {"protein": 6,   "carbs": 14, "fats": 6,    "default_grams": 200},
    "dal tadka":       {"protein": 5,   "carbs": 12, "fats": 3,    "default_grams": 200},
    "chana masala":    {"protein": 6,   "carbs": 16, "fats": 3,    "default_grams": 200},
    "vegetable pulao": {"protein": 3,   "carbs": 24, "fats": 4,    "default_grams": 200},
    "jeera rice":      {"protein": 2.5, "carbs": 27, "fats": 3,    "default_grams": 195},
    "curd rice":       {"protein": 3,   "carbs": 18, "fats": 2,    "default_grams": 200},
    "raita":           {"protein": 2.5, "carbs": 4,  "fats": 2,    "default_grams": 100},
    "salad":           {"protein": 1.5, "carbs": 5,  "fats": 0.2,  "default_grams": 150},

    # Nuts, seeds, oils
    "almonds":         {"protein": 21,  "carbs": 22, "fats": 50,   "default_grams": 10},
    "walnuts":         {"protein": 15,  "carbs": 14, "fats": 65,   "default_grams": 10},
    "cashews":         {"protein": 18,  "carbs": 30, "fats": 44,   "default_grams": 10},
    "peanuts":         {"protein": 26,  "carbs": 16, "fats": 49,   "default_grams": 15},
    "sunflower seed butter": {"protein": 17, "carbs": 21, "fats": 55, "default_grams": 15},
    "peanut butter":   {"protein": 25,  "carbs": 20, "fats": 50,   "default_grams": 15},
    "chia seeds":      {"protein": 17,  "carbs": 42, "fats": 31,   "default_grams": 10},
    "flax seeds":      {"protein": 18,  "carbs": 29, "fats": 42,   "default_grams": 10},
    "olive oil":       {"protein": 0,   "carbs": 0,  "fats": 100,  "default_grams": 5},

    # Misc
    "lassi":           {"protein": 3,   "carbs": 10, "fats": 3,    "default_grams": 200},
    "buttermilk":      {"protein": 3,   "carbs": 4.8,"fats": 0.9,  "default_grams": 200},
    "biscuit":         {"protein": 6,   "carbs": 68, "fats": 18,   "default_grams": 15},
    "khakhra":         {"protein": 10,  "carbs": 63, "fats": 10,   "default_grams": 15},
}

# Alternate names that map to an existing FOOD_DB entry.
ALIASES = {
    "chapati": "roti",
    "phulka": "roti",
    "rice": "white rice",
    "lentils": "dal",
    "chickpeas": "chole",
    "yogurt": "curd",
    "yoghurt": "curd",
    "oatmeal": "oats",
    "chicken": "chicken breast",
}

# Sorted once, longest first, so specific matches (e.g. "soy milk") are
# checked before generic ones (e.g. "milk").
_ALL_KEYS_SORTED = sorted(list(FOOD_DB.keys()) + list(ALIASES.keys()), key=len, reverse=True)


def _clean_name(item_text: str) -> str:
    """Strips bracketed detail and a leading count/quantity, returns a
    lowercase food name suitable for matching. '2 Roti (~40g each)' -> 'roti'"""
    text = re.sub(r'\(.*?\)', '', item_text)
    text = re.sub(r'^\d+(?:\.\d+)?\s*(?:g|ml|cup[s]?|tbsp|tsp)?\s*', '', text, flags=re.IGNORECASE)
    return text.strip().lower()


def match_food(item_text: str):
    """Returns (canonical_key, per_100g_dict) or (None, None)."""
    name = _clean_name(item_text)
    for key in _ALL_KEYS_SORTED:
        if key in name:
            canonical = ALIASES.get(key, key)
            return canonical, FOOD_DB[canonical]
    return None, None


def lookup_usda(food_name: str):
    """Fallback lookup for items not in FOOD_DB. Returns a dict shaped like
    a FOOD_DB entry (protein/carbs/fats per 100g, no default_grams) or None."""
    api_key = os.getenv("USDA_API_KEY")
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
        return {
            "protein": nutrients.get("Protein", 0),
            "carbs": nutrients.get("Carbohydrate, by difference", 0),
            "fats": nutrients.get("Total lipid (fat)", 0),
            "default_grams": None,
            "matched_name": food.get("description", food_name),
        }
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None


def parse_grams(item_text: str, default_grams=None):
    """Extracts a total gram quantity from an item description.
    Handles explicit grams/ml, cup/tbsp/tsp, per-unit-with-count ("each"),
    and falls back to default_grams (one serving) if nothing is specified."""
    text_lower = item_text.lower()

    gram_matches = re.findall(r'~?(\d+(?:\.\d+)?)\s*g\b', text_lower)
    ml_matches = re.findall(r'~?(\d+(?:\.\d+)?)\s*ml\b', text_lower)
    cup_matches = re.findall(r'(\d+(?:\.\d+)?)\s*cups?\b', text_lower)
    tbsp_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:tbsp|tablespoons?)\b', text_lower)
    tsp_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:tsp|teaspoons?)\b', text_lower)

    leading_count_match = re.match(r'^(\d+(?:\.\d+)?)\s+', item_text.strip())
    count = float(leading_count_match.group(1)) if leading_count_match else 1
    is_each = "each" in text_lower

    if gram_matches:
        val = float(gram_matches[-1])
        return val * count if is_each else val
    if ml_matches:
        val = float(ml_matches[-1])  # approximated 1ml ~= 1g for common drinks
        return val * count if is_each else val
    if cup_matches:
        return float(cup_matches[-1]) * 240
    if tbsp_matches:
        return float(tbsp_matches[-1]) * 15
    if tsp_matches:
        return float(tsp_matches[-1]) * 5
    if default_grams:
        return count * default_grams
    return None


def compute_item(item_text: str) -> dict:
    """Looks up and calculates the real nutrition for a single food item
    string. Returns matched=False if it couldn't be verified against any
    data source — such items are excluded from totals, never guessed."""
    canonical, data = match_food(item_text)
    source = "local"
    if data is None:
        usda_data = lookup_usda(_clean_name(item_text))
        if usda_data is None:
            return {"item": item_text, "matched": False}
        data = usda_data
        source = "usda"

    grams = parse_grams(item_text, data.get("default_grams"))
    if grams is None:
        return {"item": item_text, "matched": False}

    scale = grams / 100
    protein = round(data["protein"] * scale, 1)
    carbs = round(data["carbs"] * scale, 1)
    fats = round(data["fats"] * scale, 1)
    calories = round(protein * 4 + carbs * 4 + fats * 9)  # always derived, never stored separately

    return {
        "item": item_text,
        "matched": True,
        "grams": round(grams, 1),
        "protein": protein,
        "carbs": carbs,
        "fats": fats,
        "calories": calories,
        "source": source,
    }


def compute_meal(items: list) -> dict:
    """Computes real Calories/Protein/Carbs/Fats for one meal by summing
    every matched item. Unmatched items are listed but excluded from the
    totals so numbers are never based on a guess."""
    computed_items = [compute_item(str(i)) for i in items]
    matched = [c for c in computed_items if c["matched"]]
    unmatched = [c["item"] for c in computed_items if not c["matched"]]

    protein = round(sum(c["protein"] for c in matched), 1)
    carbs = round(sum(c["carbs"] for c in matched), 1)
    fats = round(sum(c["fats"] for c in matched), 1)
    calories = round(protein * 4 + carbs * 4 + fats * 9)

    return {
        "Items": list(items),
        "Calories": calories,
        "Protein": f"{protein}g",
        "Carbs": f"{carbs}g",
        "Fats": f"{fats}g",
        "_unmatched_items": unmatched,
    }


def compute_daily_nutrition(meals_raw: dict) -> dict:
    """Computes the full day's nutrition from an AI-provided
    {mealName: {"Items": [...]}} structure. This is the single source of
    truth: daily totals are always the sum of backend-computed meal
    totals, never a separately AI-provided number."""
    computed_meals = {}
    total_protein = total_carbs = total_fats = 0.0
    all_unmatched = []

    for meal_name, meal_data in meals_raw.items():
        items = meal_data.get("Items", []) if isinstance(meal_data, dict) else (meal_data or [])
        computed = compute_meal(items)
        computed_meals[meal_name] = computed

        total_protein += float(computed["Protein"].rstrip("g"))
        total_carbs += float(computed["Carbs"].rstrip("g"))
        total_fats += float(computed["Fats"].rstrip("g"))
        all_unmatched.extend(f"{meal_name}: {i}" for i in computed["_unmatched_items"])

    total_protein = round(total_protein, 1)
    total_carbs = round(total_carbs, 1)
    total_fats = round(total_fats, 1)
    total_calories = round(total_protein * 4 + total_carbs * 4 + total_fats * 9)

    return {
        "Meals": computed_meals,
        "DailyMacros": {
            "Protein": f"{total_protein}g",
            "Carbs": f"{total_carbs}g",
            "Fats": f"{total_fats}g",
        },
        "ComputedCalories": total_calories,
        "_unmatched_items": all_unmatched,
    }