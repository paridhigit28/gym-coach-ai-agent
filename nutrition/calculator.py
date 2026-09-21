# """
# Deterministic calorie & macro math.

# This module replaces the "ask the LLM to calculate BMR/TDEE/macros"
# approach. Given the same inputs it always returns the same numbers,
# so nothing here should ever be handed to the model to recompute --
# the model only picks *food items* (see services/groq_service.py),
# this module is the single source of truth for the numbers.
# """

# from __future__ import annotations

# from nutrition import body_build as _body_build

# ACTIVITY_MULTIPLIERS = {
#     "sedentary": 1.2,
#     "lightly active": 1.375,
#     "moderately active": 1.55,
#     "very active": 1.725,
# }

# # Matches the goal_options enum in pages/profile.py -- keep in sync if that changes.
# GOAL_DEFICIT_KCAL = 500      # mid-point of the 400-600 kcal deficit range
# GOAL_SURPLUS_KCAL = 400      # mid-point of the 300-500 kcal surplus range

# PROTEIN_G_PER_KG = {
#     "loss": 2.0,     # 1.6-2.2 g/kg range -> mid/high end to preserve muscle in a deficit
#     "gain": 1.8,      # 1.6-2.0 g/kg range
#     "maintain": 1.6,
# }
# FAT_PCT_OF_CALORIES = 0.25  # remaining calories after protein go ~25% fat, rest carbs


# def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
#     """Mifflin-St Jeor BMR estimate."""
#     gender_norm = (gender or "").strip().lower()
#     base = 10 * weight_kg + 6.25 * height_cm - 5 * age
#     if gender_norm == "male":
#         return base + 5
#     if gender_norm == "female":
#         return base - 161
#     # "Other" / unspecified: split the difference between the male and female offsets
#     return base - 78


# def calculate_maintenance_calories(bmr: float, activity_level: str) -> float:
#     key = (activity_level or "").strip().lower()
#     multiplier = ACTIVITY_MULTIPLIERS.get(key, ACTIVITY_MULTIPLIERS["lightly active"])
#     return bmr * multiplier


# def _goal_direction(goal: str) -> str:
#     g = (goal or "").strip().lower()
#     if g in ("weight loss",):
#         return "loss"
#     if g in ("weight gain", "muscle gain"):
#         return "gain"
#     # "Maintain Weight", "General Fitness", anything unrecognized -> maintain
#     return "maintain"


# def calculate_targets(weight_kg: float, height_cm: float, age: int, gender: str,
#                        activity_level: str, goal: str, body_build: str | None = None) -> dict:
#     """Returns MaintenanceCalories, TargetCalories, and daily macro grams --
#     all computed deterministically, never left for the LLM to state.

#     body_build is OPTIONAL (one of nutrition.body_build.BODY_BUILD_OPTIONS,
#     or None). It is a secondary personalization heuristic layered on top of
#     the primary BMR/TDEE/activity/goal calculation below -- see
#     nutrition/body_build.py and nutrition/data/body_build_nutrition.csv for
#     the (small, conservative) adjustment values and their documentation.
#     The user's actual Fitness Goal always takes precedence: this adjustment
#     nudges the target, it never flips deficit/surplus/maintain direction.
#     """
#     bmr = calculate_bmr(weight_kg, height_cm, age, gender)
#     maintenance = calculate_maintenance_calories(bmr, activity_level)
#     direction = _goal_direction(goal)

#     # Step 1: Fitness Goal adjustment (primary factor).
#     if direction == "loss":
#         target = maintenance - GOAL_DEFICIT_KCAL
#     elif direction == "gain":
#         target = maintenance + GOAL_SURPLUS_KCAL
#     else:
#         target = maintenance

#     # Step 2: Body Build personalization adjustment (secondary factor,
#     # applied exactly once, after the goal adjustment). 0 if body_build
#     # wasn't provided, so this is a no-op for existing/older profiles.
#     target += _body_build.get_calorie_adjustment(body_build)

#     # Keep a sane floor so a small/low-activity user doesn't get an unsafe target.
#     target = max(target, 1200)

#     protein_g_per_kg = PROTEIN_G_PER_KG[direction]
#     protein_g = weight_kg * protein_g_per_kg
#     protein_kcal = protein_g * 4

#     fat_kcal = target * FAT_PCT_OF_CALORIES
#     fat_g = fat_kcal / 9

#     carb_kcal = max(target - protein_kcal - fat_kcal, 0)
#     carb_g = carb_kcal / 4

#     return {
#         "MaintenanceCalories": round(maintenance),
#         "TargetCalories": round(target),
#         "_body_build_adjustment": _body_build.get_calorie_adjustment(body_build),
#         "DailyMacros": {
#             "Protein": f"{round(protein_g)}g",
#             "Carbs": f"{round(carb_g)}g",
#             "Fats": f"{round(fat_g)}g",
#         },
#         # kept as plain numbers too, for callers that need to do more math
#         "_protein_g": round(protein_g),
#         "_carb_g": round(carb_g),
#         "_fat_g": round(fat_g),
#     }


# # Standard meal-split used to divide the daily target across meals when
# # building the prompt's per-meal calorie budget.
# MEAL_SPLIT = {
#     "Breakfast": 0.25,
#     "Lunch": 0.35,
#     "EveningSnack": 0.10,
#     "Dinner": 0.30,
# }


# def meal_calorie_budgets(target_calories: float) -> dict:
#     return {meal: round(target_calories * pct) for meal, pct in MEAL_SPLIT.items()}


"""
Deterministic calorie & macro math.

This module replaces the "ask the LLM to calculate BMR/TDEE/macros"
approach. Given the same inputs it always returns the same numbers,
so nothing here should ever be handed to the model to recompute --
the model only picks *food items* (see services/groq_service.py),
this module is the single source of truth for the numbers.
"""

from __future__ import annotations

from nutrition import body_build as _body_build

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly active": 1.375,
    "moderately active": 1.55,
    "very active": 1.725,
}

# Matches the goal_options enum in pages/profile.py -- keep in sync if that changes.
GOAL_DEFICIT_KCAL = 500      # mid-point of the 400-600 kcal deficit range
GOAL_SURPLUS_KCAL = 400      # mid-point of the 300-500 kcal surplus range

PROTEIN_G_PER_KG = {
    "loss": 2.0,     # 1.6-2.2 g/kg range -> mid/high end to preserve muscle in a deficit
    "gain": 1.8,      # 1.6-2.0 g/kg range
    "maintain": 1.6,
}
FAT_PCT_OF_CALORIES = 0.25  # remaining calories after protein go ~25% fat, rest carbs


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor BMR estimate."""
    gender_norm = (gender or "").strip().lower()
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if gender_norm == "male":
        return base + 5
    if gender_norm == "female":
        return base - 161
    # "Other" / unspecified: split the difference between the male and female offsets
    return base - 78


def calculate_maintenance_calories(bmr: float, activity_level: str) -> float:
    key = (activity_level or "").strip().lower()
    multiplier = ACTIVITY_MULTIPLIERS.get(key, ACTIVITY_MULTIPLIERS["lightly active"])
    return bmr * multiplier


def _goal_direction(goal: str) -> str:
    """Maps a goal string to loss/gain/maintain.

    Uses substring matching (not an exact-match set) so canonical values
    like "Weight Loss" / "Weight Gain" / "Muscle Gain" / "Maintain Weight"
    all resolve correctly, and this stays robust to minor wording
    variations. Anything without a recognizable loss/gain keyword
    (including "Maintain Weight", "General Fitness", or an empty/unknown
    value) safely falls back to "maintain" rather than guessing.
    """
    g = (goal or "").strip().lower()
    if "loss" in g or "lose" in g or "cut" in g or "deficit" in g:
        return "loss"
    if "gain" in g or "bulk" in g or "muscle" in g or "surplus" in g:
        return "gain"
    return "maintain"


def derive_goal(current_weight_kg: float | None, target_weight_kg: float | None,
                 fitness_goal: str | None = None) -> str:
    """Single source of truth for turning what we know about the user into
    one of the three canonical goal labels: "Weight Loss", "Weight Gain",
    or "Maintain Weight". Never returns anything else, and never leaves
    this decision to the LLM.

    Priority:
    1. An explicit fitness_goal string, if the user has set one (e.g. via
       the Fitness Assessment "Fitness Goal" field) -- this is the
       authoritative signal once present.
    2. Otherwise, fall back to comparing current weight against the
       Target Weight captured in the Fitness Assessment (a >=1kg
       difference either way counts as Loss/Gain; anything closer than
       that counts as Maintain, since it's within normal day-to-day
       weight fluctuation and not a real body-recomposition goal).
    3. If neither signal is available, default to "Maintain Weight" --
       never guess a deficit/surplus without real user input.
    """
    explicit = (fitness_goal or "").strip()
    if explicit:
        direction = _goal_direction(explicit)
        if direction == "loss":
            return "Weight Loss"
        if direction == "gain":
            return "Weight Gain"
        return "Maintain Weight"

    if current_weight_kg is None or target_weight_kg is None:
        return "Maintain Weight"

    diff = float(target_weight_kg) - float(current_weight_kg)
    tolerance_kg = 1.0
    if diff <= -tolerance_kg:
        return "Weight Loss"
    if diff >= tolerance_kg:
        return "Weight Gain"
    return "Maintain Weight"


def calculate_targets(weight_kg: float, height_cm: float, age: int, gender: str,
                       activity_level: str, goal: str, body_build: str | None = None) -> dict:
    """Returns MaintenanceCalories, TargetCalories, and daily macro grams --
    all computed deterministically, never left for the LLM to state.

    body_build is OPTIONAL (one of nutrition.body_build.BODY_BUILD_OPTIONS,
    or None). It is a secondary personalization heuristic layered on top of
    the primary BMR/TDEE/activity/goal calculation below -- see
    nutrition/body_build.py and nutrition/data/body_build_nutrition.csv for
    the (small, conservative) adjustment values and their documentation.
    The user's actual Fitness Goal always takes precedence: this adjustment
    nudges the target, it never flips deficit/surplus/maintain direction.
    """
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    maintenance = calculate_maintenance_calories(bmr, activity_level)
    direction = _goal_direction(goal)

    # Step 1: Fitness Goal adjustment (primary factor).
    if direction == "loss":
        target = maintenance - GOAL_DEFICIT_KCAL
    elif direction == "gain":
        target = maintenance + GOAL_SURPLUS_KCAL
    else:
        target = maintenance

    # Step 2: Body Build personalization adjustment (secondary factor,
    # applied exactly once, after the goal adjustment). 0 if body_build
    # wasn't provided, so this is a no-op for existing/older profiles.
    target += _body_build.get_calorie_adjustment(body_build)

    # Keep a sane floor so a small/low-activity user doesn't get an unsafe target.
    target = max(target, 1200)

    protein_g_per_kg = PROTEIN_G_PER_KG[direction]
    protein_g = weight_kg * protein_g_per_kg
    protein_kcal = protein_g * 4

    fat_kcal = target * FAT_PCT_OF_CALORIES
    fat_g = fat_kcal / 9

    carb_kcal = max(target - protein_kcal - fat_kcal, 0)
    carb_g = carb_kcal / 4

    return {
        "MaintenanceCalories": round(maintenance),
        "TargetCalories": round(target),
        "_body_build_adjustment": _body_build.get_calorie_adjustment(body_build),
        "DailyMacros": {
            "Protein": f"{round(protein_g)}g",
            "Carbs": f"{round(carb_g)}g",
            "Fats": f"{round(fat_g)}g",
        },
        # kept as plain numbers too, for callers that need to do more math
        "_protein_g": round(protein_g),
        "_carb_g": round(carb_g),
        "_fat_g": round(fat_g),
    }


# Standard meal-split used to divide the daily target across meals when
# building the prompt's per-meal calorie budget.
MEAL_SPLIT = {
    "Breakfast": 0.25,
    "Lunch": 0.35,
    "EveningSnack": 0.10,
    "Dinner": 0.30,
}


def meal_calorie_budgets(target_calories: float) -> dict:
    return {meal: round(target_calories * pct) for meal, pct in MEAL_SPLIT.items()}