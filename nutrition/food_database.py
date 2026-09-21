# # """
# # Loads nutrition/data/food_database.csv (1,014 Indian dishes with verified
# # per-100g calories/protein/carbs/fat, plus vegetarian/vegan/allergen flags)
# # and exposes lookups used by services/groq_service.py.

# # IMPORTANT CAVEAT: the diet/allergen flags for these dishes were inferred
# # from dish-name keywords, not lab-verified (see classification_method
# # column). They're a reasonable filter, not a guarantee -- for a real
# # allergy, a human should still double check the generated plan. This
# # module surfaces that caveat via `has_verified_metadata()` so callers can
# # show it in the UI if they want.
# # """

# # from __future__ import annotations

# # import difflib
# # import functools
# # import os
# # import re

# # import pandas as pd

# # from nutrition import body_build as _body_build

# # _CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "food_database.csv")

# # FLAG_COLUMNS = [
# #     "vegetarian", "vegan", "gluten_free", "dairy_free", "egg_free",
# #     "peanut_free", "tree_nut_free", "soy_free", "fish_free", "shellfish_free",
# # ]

# # # Maps free-text words a user might type in "Food Restrictions / Allergies"
# # # to the flag column that must be True for a food to be considered safe.
# # RESTRICTION_KEYWORDS = {
# #     "peanut": "peanut_free",
# #     "peanuts": "peanut_free",
# #     "groundnut": "peanut_free",
# #     "dairy": "dairy_free",
# #     "milk": "dairy_free",
# #     "lactose": "dairy_free",
# #     "egg": "egg_free",
# #     "eggs": "egg_free",
# #     "gluten": "gluten_free",
# #     "wheat": "gluten_free",
# #     "soy": "soy_free",
# #     "soya": "soy_free",
# #     "nut": "tree_nut_free",
# #     "nuts": "tree_nut_free",
# #     "tree nut": "tree_nut_free",
# #     "tree nuts": "tree_nut_free",
# #     "almond": "tree_nut_free",
# #     "cashew": "tree_nut_free",
# #     "walnut": "tree_nut_free",
# #     "fish": "fish_free",
# #     "shellfish": "shellfish_free",
# #     "prawn": "shellfish_free",
# #     "shrimp": "shellfish_free",
# #     "crab": "shellfish_free",
# # }


# # @functools.lru_cache(maxsize=1)
# # def load_foods() -> pd.DataFrame:
# #     df = pd.read_csv(_CSV_PATH)
# #     for col in FLAG_COLUMNS:
# #         df[col] = df[col].astype(str).map({"True": True, "False": False}).fillna(True)
# #     df["_name_lower"] = df["food_name"].str.lower().str.strip()
# #     return df


# # def has_verified_metadata(food_name: str) -> bool:
# #     row = load_foods()
# #     match = row[row["_name_lower"] == food_name.lower().strip()]
# #     if match.empty:
# #         return False
# #     return bool((match.iloc[0]["classification_method"] or "") != "inferred_from_dish_name_keywords")


# # def parse_restrictions_text(food_restrictions_text: str) -> set[str]:
# #     """Turns free text like 'peanuts, dairy' into the set of flag columns
# #     that must be True, e.g. {'peanut_free', 'dairy_free'}."""
# #     if not food_restrictions_text or food_restrictions_text.strip().lower() == "none":
# #         return set()
# #     text = food_restrictions_text.lower()
# #     required_flags = set()
# #     for keyword, flag in RESTRICTION_KEYWORDS.items():
# #         if keyword in text:
# #             required_flags.add(flag)
# #     return required_flags


# # def diet_preference_flags(diet_preference: str) -> set[str]:
# #     """'Vegetarian' -> {'vegetarian'}, 'Vegan' -> {'vegetarian','vegan'}."""
# #     pref = (diet_preference or "").strip().lower()
# #     if pref == "vegan":
# #         return {"vegetarian", "vegan"}
# #     if pref == "vegetarian":
# #         return {"vegetarian"}
# #     return set()


# # _PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


# # def candidate_foods(required_flags: set[str], limit: int = 150, body_build: str | None = None) -> list[str]:
# #     """Food names that satisfy every required flag, for injecting into the
# #     LLM prompt as the pool it's allowed to choose meals from.

# #     Allergy/dietary filtering ALWAYS happens first via required_flags, exactly
# #     as before -- body_build only re-orders the already-safe candidates that
# #     remain, it never adds or removes items. This is intentional: Body Build
# #     personalization must never be able to override an allergy or dietary
# #     restriction (see nutrition/body_build.py). food_database.csv itself is
# #     untouched -- ranking uses the nutrition columns that already exist there
# #     (protein_g/carbs_g/fat_g/fiber_g) together with the priority weights in
# #     nutrition/data/body_build_nutrition.csv, so no per-food "body_build"
# #     column is needed.
# #     """
# #     df = load_foods()
# #     mask = pd.Series(True, index=df.index)
# #     for flag in required_flags:
# #         if flag in df.columns:
# #             mask &= df[flag]
# #     safe = df.loc[mask]

# #     rules = _body_build.get_rules(body_build)
# #     if rules:
# #         # Simple weighted-priority score: foods richer (per 100g) in the
# #         # macros this build prioritizes sort first, so the LLM's candidate
# #         # list leads with more relevant options. This is a display-order
# #         # nudge, not a filter -- every safe food is still in the list.
# #         w_protein = _PRIORITY_WEIGHT.get(rules.get("protein_priority"), 1)
# #         w_carb = _PRIORITY_WEIGHT.get(rules.get("carb_priority"), 1)
# #         w_fat = _PRIORITY_WEIGHT.get(rules.get("fat_priority"), 1)
# #         w_fiber = _PRIORITY_WEIGHT.get(rules.get("fiber_priority"), 1)
# #         score = (
# #             safe["protein_g"] * w_protein
# #             + safe["fiber_g"] * w_fiber
# #             + safe["carbs_g"] * w_carb * 0.3
# #             + safe["fat_g"] * w_fat * 0.3
# #         ) / safe["calories"].clip(lower=1)
# #         safe = safe.assign(_body_build_score=score).sort_values("_body_build_score", ascending=False)

# #     names = safe["food_name"].tolist()
# #     return names[:limit]


# # _GRAMS_RE = re.compile(r"([-+]?\d*\.?\d+)\s*g\b", re.IGNORECASE)


# # def parse_item(item_str: str) -> tuple[str, float]:
# #     """'Paneer parantha/paratha(120g)' -> ('Paneer parantha/paratha', 120.0).
# #     Defaults to 100g if no gram amount is present in the item string."""
# #     match = _GRAMS_RE.search(item_str)
# #     grams = float(match.group(1)) if match else 100.0
# #     name = _GRAMS_RE.sub("", item_str)
# #     name = re.sub(r"[()]", "", name).strip()
# #     return name, grams


# # def lookup(food_name: str, cutoff: float = 0.6):
# #     """Best-effort fuzzy match against the database. Returns the matching
# #     row (as a dict) or None if nothing close enough was found."""
# #     df = load_foods()
# #     name_lower = food_name.lower().strip()

# #     exact = df[df["_name_lower"] == name_lower]
# #     if not exact.empty:
# #         return exact.iloc[0].to_dict()

# #     # substring match (handles "Paneer Parantha" vs "Paneer parantha/paratha")
# #     contains = df[df["_name_lower"].str.contains(re.escape(name_lower), na=False)]
# #     if not contains.empty:
# #         return contains.iloc[0].to_dict()

# #     close = difflib.get_close_matches(name_lower, df["_name_lower"].tolist(), n=1, cutoff=cutoff)
# #     if close:
# #         return df[df["_name_lower"] == close[0]].iloc[0].to_dict()

# #     return None


# # def nutrition_for_item(item_str: str) -> dict | None:
# #     """Looks up an LLM-produced item string against the database and scales
# #     its per-100g nutrition to the stated gram amount. Returns None if the
# #     food couldn't be matched -- callers should treat that as "unverified"
# #     rather than silently guessing."""
# #     name, grams = parse_item(item_str)
# #     row = lookup(name)
# #     if row is None:
# #         return None
# #     scale = grams / 100.0
# #     return {
# #         "matched_name": row["food_name"],
# #         "grams": grams,
# #         "calories": round(row["calories"] * scale, 1),
# #         "protein_g": round(row["protein_g"] * scale, 1),
# #         "carbs_g": round(row["carbs_g"] * scale, 1),
# #         "fat_g": round(row["fat_g"] * scale, 1),
# #         "verified": row.get("classification_method") != "inferred_from_dish_name_keywords",
# #     }


# # def violates_restrictions(food_name: str, required_flags: set[str]) -> bool:
# #     """True if the matched food is known to fail one of the required
# #     flags. Foods that can't be matched at all are NOT flagged here --
# #     that's a separate 'unverified' case handled by the caller."""
# #     name, _ = parse_item(food_name)
# #     row = lookup(name)
# #     if row is None:
# #         return False
# #     return any(not row.get(flag, True) for flag in required_flags)


# """
# Loads nutrition/data/food_database.csv (Indian dishes with verified
# per-1g calories/protein/carbs/fat, plus vegetarian/vegan/allergen flags)
# and exposes lookups used by services/groq_service.py.

# IMPORTANT CAVEAT: the diet/allergen flags for these dishes were inferred
# from dish-name keywords, not lab-verified (see classification_method
# column). They're a reasonable filter, not a guarantee -- for a real
# allergy, a human should still double check the generated plan. This
# module surfaces that caveat via `has_verified_metadata()` so callers can
# show it in the UI if they want.
# """

# from __future__ import annotations

# import difflib
# import functools
# import os
# import re

# import pandas as pd

# from nutrition import body_build as _body_build

# _CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "food_database.csv")

# FLAG_COLUMNS = [
#     "vegetarian", "vegan", "gluten_free", "dairy_free", "egg_free",
#     "peanut_free", "tree_nut_free", "soy_free", "fish_free", "shellfish_free",
# ]

# # Maps free-text words a user might type in "Food Restrictions / Allergies"
# # to the flag column that must be True for a food to be considered safe.
# RESTRICTION_KEYWORDS = {
#     "peanut": "peanut_free",
#     "peanuts": "peanut_free",
#     "groundnut": "peanut_free",
#     "dairy": "dairy_free",
#     "milk": "dairy_free",
#     "lactose": "dairy_free",
#     "egg": "egg_free",
#     "eggs": "egg_free",
#     "gluten": "gluten_free",
#     "wheat": "gluten_free",
#     "soy": "soy_free",
#     "soya": "soy_free",
#     "nut": "tree_nut_free",
#     "nuts": "tree_nut_free",
#     "tree nut": "tree_nut_free",
#     "tree nuts": "tree_nut_free",
#     "almond": "tree_nut_free",
#     "cashew": "tree_nut_free",
#     "walnut": "tree_nut_free",
#     "fish": "fish_free",
#     "shellfish": "shellfish_free",
#     "prawn": "shellfish_free",
#     "shrimp": "shellfish_free",
#     "crab": "shellfish_free",
# }


# @functools.lru_cache(maxsize=1)
# def load_foods() -> pd.DataFrame:
#     df = pd.read_csv(_CSV_PATH)
#     for col in FLAG_COLUMNS:
#         df[col] = df[col].astype(str).map({"True": True, "False": False}).fillna(True)
#     df["_name_lower"] = df["food_name"].str.lower().str.strip()
#     return df


# def has_verified_metadata(food_name: str) -> bool:
#     row = load_foods()
#     match = row[row["_name_lower"] == food_name.lower().strip()]
#     if match.empty:
#         return False
#     return bool((match.iloc[0]["classification_method"] or "") != "inferred_from_dish_name_keywords")


# def parse_restrictions_text(food_restrictions_text: str) -> set[str]:
#     """Turns free text like 'peanuts, dairy' into the set of flag columns
#     that must be True, e.g. {'peanut_free', 'dairy_free'}."""
#     if not food_restrictions_text or food_restrictions_text.strip().lower() == "none":
#         return set()
#     text = food_restrictions_text.lower()
#     required_flags = set()
#     for keyword, flag in RESTRICTION_KEYWORDS.items():
#         if keyword in text:
#             required_flags.add(flag)
#     return required_flags


# def diet_preference_flags(diet_preference: str) -> set[str]:
#     """'Vegetarian' -> {'vegetarian'}, 'Vegan' -> {'vegetarian','vegan'}."""
#     pref = (diet_preference or "").strip().lower()
#     if pref == "vegan":
#         return {"vegetarian", "vegan"}
#     if pref == "vegetarian":
#         return {"vegetarian"}
#     return set()


# _PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


# def candidate_foods(required_flags: set[str], limit: int = 150, body_build: str | None = None) -> list[str]:
#     """Food names that satisfy every required flag, for injecting into the
#     LLM prompt as the pool it's allowed to choose meals from.

#     Allergy/dietary filtering ALWAYS happens first via required_flags, exactly
#     as before -- body_build only re-orders the already-safe candidates that
#     remain, it never adds or removes items. This is intentional: Body Build
#     personalization must never be able to override an allergy or dietary
#     restriction (see nutrition/body_build.py). food_database.csv itself is
#     untouched -- ranking uses the nutrition columns that already exist there
#     (protein_g/carbs_g/fat_g/fiber_g) together with the priority weights in
#     nutrition/data/body_build_nutrition.csv, so no per-food "body_build"
#     column is needed.
#     """
#     df = load_foods()
#     mask = pd.Series(True, index=df.index)
#     for flag in required_flags:
#         if flag in df.columns:
#             mask &= df[flag]
#     safe = df.loc[mask]

#     rules = _body_build.get_rules(body_build)
#     if rules:
#         # Simple weighted-priority score: foods richer (per 100g) in the
#         # macros this build prioritizes sort first, so the LLM's candidate
#         # list leads with more relevant options. This is a display-order
#         # nudge, not a filter -- every safe food is still in the list.
#         w_protein = _PRIORITY_WEIGHT.get(rules.get("protein_priority"), 1)
#         w_carb = _PRIORITY_WEIGHT.get(rules.get("carb_priority"), 1)
#         w_fat = _PRIORITY_WEIGHT.get(rules.get("fat_priority"), 1)
#         w_fiber = _PRIORITY_WEIGHT.get(rules.get("fiber_priority"), 1)
#         score = (
#             safe["protein_g_per_g"] * w_protein
#             + safe["fiber_g_per_g"] * w_fiber
#             + safe["carbs_g_per_g"] * w_carb * 0.3
#             + safe["fat_g_per_g"] * w_fat * 0.3
#         ) / safe["calories_per_g"].clip(lower=0.01)
#         safe = safe.assign(_body_build_score=score).sort_values("_body_build_score", ascending=False)

#     names = safe["food_name"].tolist()
#     return names[:limit]


# _GRAMS_RE = re.compile(r"([-+]?\d*\.?\d+)\s*g\b", re.IGNORECASE)


# def parse_item(item_str: str) -> tuple[str, float]:
#     """'Paneer parantha/paratha(120g)' -> ('Paneer parantha/paratha', 120.0).
#     Defaults to 100g if no gram amount is present in the item string."""
#     match = _GRAMS_RE.search(item_str)
#     grams = float(match.group(1)) if match else 100.0
#     name = _GRAMS_RE.sub("", item_str)
#     name = re.sub(r"[()]", "", name).strip()
#     return name, grams


# def lookup(food_name: str, cutoff: float = 0.6):
#     """Best-effort fuzzy match against the database. Returns the matching
#     row (as a dict) or None if nothing close enough was found."""
#     df = load_foods()
#     name_lower = food_name.lower().strip()

#     exact = df[df["_name_lower"] == name_lower]
#     if not exact.empty:
#         return exact.iloc[0].to_dict()

#     # substring match (handles "Paneer Parantha" vs "Paneer parantha/paratha")
#     contains = df[df["_name_lower"].str.contains(re.escape(name_lower), na=False)]
#     if not contains.empty:
#         return contains.iloc[0].to_dict()

#     close = difflib.get_close_matches(name_lower, df["_name_lower"].tolist(), n=1, cutoff=cutoff)
#     if close:
#         return df[df["_name_lower"] == close[0]].iloc[0].to_dict()

#     return None


# _ATWATER_TOLERANCE = 0.15  # relative slack allowed before a row is flagged


# def calorie_macro_mismatch(row: dict, tolerance: float = _ATWATER_TOLERANCE) -> bool:
#     """True if a food_database.csv row's own stated calories_per_g is
#     inconsistent with what its protein/carbs/fat_per_g would imply via the
#     standard Atwater factors (4 kcal/g protein, 4 kcal/g carbs, 9 kcal/g
#     fat), by more than `tolerance` (relative).

#     This is a data-quality check on the CSV row itself -- independent of
#     (and a different failure mode from) the per-meal budget scaling done in
#     services/groq_service.py. A row can pass through parse/lookup/scaling
#     just fine and still have macros that don't add up to its own calorie
#     figure (e.g. a dish whose calories weren't updated to match its
#     protein/carbs/fat when the dataset was edited). Flagging it here lets
#     callers surface a warning that actually names the real cause, instead
#     of the scaling pass silently producing a meal total that looks "wrong"
#     for no explained reason.
#     """
#     implied = (
#         row.get("protein_g_per_g", 0) * 4
#         + row.get("carbs_g_per_g", 0) * 4
#         + row.get("fat_g_per_g", 0) * 9
#     )
#     stated = row.get("calories_per_g", 0) or 0
#     if stated <= 0:
#         return implied > 0
#     return abs(implied - stated) / stated > tolerance


# def nutrition_for_item(item_str: str) -> dict | None:
#     """Looks up an LLM-produced item string against the database and scales
#     its per-1g nutrition to the stated gram amount. Returns None if the
#     food couldn't be matched -- callers should treat that as "unverified"
#     rather than silently guessing."""
#     name, grams = parse_item(item_str)
#     row = lookup(name)
#     if row is None:
#         return None
#     scale = grams
#     return {
#         "matched_name": row["food_name"],
#         "grams": grams,
#         "calories": round(row["calories_per_g"] * scale, 1),
#         "protein_g": round(row["protein_g_per_g"] * scale, 1),
#         "carbs_g": round(row["carbs_g_per_g"] * scale, 1),
#         "fat_g": round(row["fat_g_per_g"] * scale, 1),
#         "verified": row.get("classification_method") != "inferred_from_dish_name_keywords",
#         "macro_mismatch": calorie_macro_mismatch(row),
#     }


# def violates_restrictions(food_name: str, required_flags: set[str]) -> bool:
#     """True if the matched food is known to fail one of the required
#     flags. Foods that can't be matched at all are NOT flagged here --
#     that's a separate 'unverified' case handled by the caller."""
#     name, _ = parse_item(food_name)
#     row = lookup(name)
#     if row is None:
#         return False
#     return any(not row.get(flag, True) for flag in required_flags)


# """
# Loads nutrition/data/food_database.csv (1,014 Indian dishes with verified
# per-100g calories/protein/carbs/fat, plus vegetarian/vegan/allergen flags)
# and exposes lookups used by services/groq_service.py.

# IMPORTANT CAVEAT: the diet/allergen flags for these dishes were inferred
# from dish-name keywords, not lab-verified (see classification_method
# column). They're a reasonable filter, not a guarantee -- for a real
# allergy, a human should still double check the generated plan. This
# module surfaces that caveat via `has_verified_metadata()` so callers can
# show it in the UI if they want.
# """

# from __future__ import annotations

# import difflib
# import functools
# import os
# import re

# import pandas as pd

# from nutrition import body_build as _body_build

# _CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "food_database.csv")

# FLAG_COLUMNS = [
#     "vegetarian", "vegan", "gluten_free", "dairy_free", "egg_free",
#     "peanut_free", "tree_nut_free", "soy_free", "fish_free", "shellfish_free",
# ]

# # Maps free-text words a user might type in "Food Restrictions / Allergies"
# # to the flag column that must be True for a food to be considered safe.
# RESTRICTION_KEYWORDS = {
#     "peanut": "peanut_free",
#     "peanuts": "peanut_free",
#     "groundnut": "peanut_free",
#     "dairy": "dairy_free",
#     "milk": "dairy_free",
#     "lactose": "dairy_free",
#     "egg": "egg_free",
#     "eggs": "egg_free",
#     "gluten": "gluten_free",
#     "wheat": "gluten_free",
#     "soy": "soy_free",
#     "soya": "soy_free",
#     "nut": "tree_nut_free",
#     "nuts": "tree_nut_free",
#     "tree nut": "tree_nut_free",
#     "tree nuts": "tree_nut_free",
#     "almond": "tree_nut_free",
#     "cashew": "tree_nut_free",
#     "walnut": "tree_nut_free",
#     "fish": "fish_free",
#     "shellfish": "shellfish_free",
#     "prawn": "shellfish_free",
#     "shrimp": "shellfish_free",
#     "crab": "shellfish_free",
# }


# @functools.lru_cache(maxsize=1)
# def load_foods() -> pd.DataFrame:
#     df = pd.read_csv(_CSV_PATH)
#     for col in FLAG_COLUMNS:
#         df[col] = df[col].astype(str).map({"True": True, "False": False}).fillna(True)
#     df["_name_lower"] = df["food_name"].str.lower().str.strip()
#     return df


# def has_verified_metadata(food_name: str) -> bool:
#     row = load_foods()
#     match = row[row["_name_lower"] == food_name.lower().strip()]
#     if match.empty:
#         return False
#     return bool((match.iloc[0]["classification_method"] or "") != "inferred_from_dish_name_keywords")


# def parse_restrictions_text(food_restrictions_text: str) -> set[str]:
#     """Turns free text like 'peanuts, dairy' into the set of flag columns
#     that must be True, e.g. {'peanut_free', 'dairy_free'}."""
#     if not food_restrictions_text or food_restrictions_text.strip().lower() == "none":
#         return set()
#     text = food_restrictions_text.lower()
#     required_flags = set()
#     for keyword, flag in RESTRICTION_KEYWORDS.items():
#         if keyword in text:
#             required_flags.add(flag)
#     return required_flags


# def diet_preference_flags(diet_preference: str) -> set[str]:
#     """'Vegetarian' -> {'vegetarian'}, 'Vegan' -> {'vegetarian','vegan'}."""
#     pref = (diet_preference or "").strip().lower()
#     if pref == "vegan":
#         return {"vegetarian", "vegan"}
#     if pref == "vegetarian":
#         return {"vegetarian"}
#     return set()


# _PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


# def candidate_foods(required_flags: set[str], limit: int = 100, body_build: str | None = None) -> list[str]:
#     """Food names that satisfy every required flag, for injecting into the
#     LLM prompt as the pool it's allowed to choose meals from.

#     Allergy/dietary filtering ALWAYS happens first via required_flags, exactly
#     as before -- body_build only re-orders the already-safe candidates that
#     remain, it never adds or removes items. This is intentional: Body Build
#     personalization must never be able to override an allergy or dietary
#     restriction (see nutrition/body_build.py). food_database.csv itself is
#     untouched -- ranking uses the nutrition columns that already exist there
#     (protein_g/carbs_g/fat_g/fiber_g) together with the priority weights in
#     nutrition/data/body_build_nutrition.csv, so no per-food "body_build"
#     column is needed.
#     """
#     df = load_foods()
#     mask = pd.Series(True, index=df.index)
#     for flag in required_flags:
#         if flag in df.columns:
#             mask &= df[flag]
#     safe = df.loc[mask]

#     rules = _body_build.get_rules(body_build)
#     if rules:
#         # Simple weighted-priority score: foods richer (per 100g) in the
#         # macros this build prioritizes sort first, so the LLM's candidate
#         # list leads with more relevant options. This is a display-order
#         # nudge, not a filter -- every safe food is still in the list.
#         w_protein = _PRIORITY_WEIGHT.get(rules.get("protein_priority"), 1)
#         w_carb = _PRIORITY_WEIGHT.get(rules.get("carb_priority"), 1)
#         w_fat = _PRIORITY_WEIGHT.get(rules.get("fat_priority"), 1)
#         w_fiber = _PRIORITY_WEIGHT.get(rules.get("fiber_priority"), 1)
#         score = (
#             safe["protein_g"] * w_protein
#             + safe["fiber_g"] * w_fiber
#             + safe["carbs_g"] * w_carb * 0.3
#             + safe["fat_g"] * w_fat * 0.3
#         ) / safe["calories"].clip(lower=1)
#         safe = safe.assign(_body_build_score=score).sort_values("_body_build_score", ascending=False)

#     names = safe["food_name"].tolist()
#     return names[:limit]


# _GRAMS_RE = re.compile(r"([-+]?\d*\.?\d+)\s*g\b", re.IGNORECASE)


# def parse_item(item_str: str) -> tuple[str, float]:
#     """'Paneer parantha/paratha(120g)' -> ('Paneer parantha/paratha', 120.0).
#     Defaults to 100g if no gram amount is present in the item string."""
#     match = _GRAMS_RE.search(item_str)
#     grams = float(match.group(1)) if match else 100.0
#     name = _GRAMS_RE.sub("", item_str)
#     name = re.sub(r"[()]", "", name).strip()
#     return name, grams


# def lookup(food_name: str, cutoff: float = 0.6):
#     """Best-effort fuzzy match against the database. Returns the matching
#     row (as a dict) or None if nothing close enough was found."""
#     df = load_foods()
#     name_lower = food_name.lower().strip()

#     exact = df[df["_name_lower"] == name_lower]
#     if not exact.empty:
#         return exact.iloc[0].to_dict()

#     # substring match (handles "Paneer Parantha" vs "Paneer parantha/paratha")
#     contains = df[df["_name_lower"].str.contains(re.escape(name_lower), na=False)]
#     if not contains.empty:
#         return contains.iloc[0].to_dict()

#     close = difflib.get_close_matches(name_lower, df["_name_lower"].tolist(), n=1, cutoff=cutoff)
#     if close:
#         return df[df["_name_lower"] == close[0]].iloc[0].to_dict()

#     return None


# def nutrition_for_item(item_str: str) -> dict | None:
#     """Looks up an LLM-produced item string against the database and scales
#     its per-100g nutrition to the stated gram amount. Returns None if the
#     food couldn't be matched -- callers should treat that as "unverified"
#     rather than silently guessing."""
#     name, grams = parse_item(item_str)
#     row = lookup(name)
#     if row is None:
#         return None
#     scale = grams / 100.0
#     return {
#         "matched_name": row["food_name"],
#         "grams": grams,
#         "calories": round(row["calories"] * scale, 1),
#         "protein_g": round(row["protein_g"] * scale, 1),
#         "carbs_g": round(row["carbs_g"] * scale, 1),
#         "fat_g": round(row["fat_g"] * scale, 1),
#         "verified": row.get("classification_method") != "inferred_from_dish_name_keywords",
#     }


# def violates_restrictions(food_name: str, required_flags: set[str]) -> bool:
#     """True if the matched food is known to fail one of the required
#     flags. Foods that can't be matched at all are NOT flagged here --
#     that's a separate 'unverified' case handled by the caller."""
#     name, _ = parse_item(food_name)
#     row = lookup(name)
#     if row is None:
#         return False
#     return any(not row.get(flag, True) for flag in required_flags)


"""
Loads nutrition/data/food_database.csv (Indian dishes with verified
per-1g calories/protein/carbs/fat, plus vegetarian/vegan/allergen flags)
and exposes lookups used by services/groq_service.py.

IMPORTANT CAVEAT: the diet/allergen flags for these dishes were inferred
from dish-name keywords, not lab-verified (see classification_method
column). They're a reasonable filter, not a guarantee -- for a real
allergy, a human should still double check the generated plan. This
module surfaces that caveat via `has_verified_metadata()` so callers can
show it in the UI if they want.
"""

from __future__ import annotations

import difflib
import functools
import os
import re

import pandas as pd

from nutrition import body_build as _body_build

_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "food_database.csv")

from services.food_image_service import image_path_for_food as _image_path_for_food

def image_for_item(item_str: str) -> str | None:
    """Resolve a canonical food item to its DB-backed local image path."""
    name, _ = parse_item(item_str)
    row = lookup(name)
    if row is None:
        return None
    return _image_path_for_food(str(row["food_name"]))


FLAG_COLUMNS = [
    "vegetarian", "vegan", "gluten_free", "dairy_free", "egg_free",
    "peanut_free", "tree_nut_free", "soy_free", "fish_free", "shellfish_free",
]

# Maps free-text words a user might type in "Food Restrictions / Allergies"
# to the flag column that must be True for a food to be considered safe.
RESTRICTION_KEYWORDS = {
    "peanut": "peanut_free",
    "peanuts": "peanut_free",
    "groundnut": "peanut_free",
    "dairy": "dairy_free",
    "milk": "dairy_free",
    "lactose": "dairy_free",
    "egg": "egg_free",
    "eggs": "egg_free",
    "gluten": "gluten_free",
    "wheat": "gluten_free",
    "soy": "soy_free",
    "soya": "soy_free",
    "nut": "tree_nut_free",
    "nuts": "tree_nut_free",
    "tree nut": "tree_nut_free",
    "tree nuts": "tree_nut_free",
    "almond": "tree_nut_free",
    "cashew": "tree_nut_free",
    "walnut": "tree_nut_free",
    "fish": "fish_free",
    "shellfish": "shellfish_free",
    "prawn": "shellfish_free",
    "shrimp": "shellfish_free",
    "crab": "shellfish_free",
}


@functools.lru_cache(maxsize=1)
def load_foods() -> pd.DataFrame:
    df = pd.read_csv(_CSV_PATH)
    for col in FLAG_COLUMNS:
        df[col] = df[col].astype(str).map({"True": True, "False": False}).fillna(True)
    df["_name_lower"] = df["food_name"].str.lower().str.strip()
    return df


def has_verified_metadata(food_name: str) -> bool:
    row = load_foods()
    match = row[row["_name_lower"] == food_name.lower().strip()]
    if match.empty:
        return False
    return bool((match.iloc[0]["classification_method"] or "") != "inferred_from_dish_name_keywords")


def parse_restrictions_text(food_restrictions_text: str) -> set[str]:
    """Turns free text like 'peanuts, dairy' into the set of flag columns
    that must be True, e.g. {'peanut_free', 'dairy_free'}."""
    if not food_restrictions_text or food_restrictions_text.strip().lower() == "none":
        return set()
    text = food_restrictions_text.lower()
    required_flags = set()
    for keyword, flag in RESTRICTION_KEYWORDS.items():
        if keyword in text:
            required_flags.add(flag)
    return required_flags


def diet_preference_flags(diet_preference: str) -> set[str]:
    """'Vegetarian' -> {'vegetarian'}, 'Vegan' -> {'vegetarian','vegan'}."""
    pref = (diet_preference or "").strip().lower()
    if pref == "vegan":
        return {"vegetarian", "vegan"}
    if pref == "vegetarian":
        return {"vegetarian"}
    return set()


_PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


def candidate_foods(required_flags: set[str], limit: int = 100, body_build: str | None = None) -> list[str]:
    """Food names that satisfy every required flag, for injecting into the
    LLM prompt as the pool it's allowed to choose meals from.

    Allergy/dietary filtering ALWAYS happens first via required_flags, exactly
    as before -- body_build only re-orders the already-safe candidates that
    remain, it never adds or removes items. This is intentional: Body Build
    personalization must never be able to override an allergy or dietary
    restriction (see nutrition/body_build.py). food_database.csv itself is
    untouched -- ranking uses the nutrition columns that already exist there
    (protein_g/carbs_g/fat_g/fiber_g) together with the priority weights in
    nutrition/data/body_build_nutrition.csv, so no per-food "body_build"
    column is needed.
    """
    df = load_foods()
    mask = pd.Series(True, index=df.index)
    for flag in required_flags:
        if flag in df.columns:
            mask &= df[flag]
    safe = df.loc[mask]

    rules = _body_build.get_rules(body_build)
    if rules:
        # Simple weighted-priority score: foods richer (per 100g) in the
        # macros this build prioritizes sort first, so the LLM's candidate
        # list leads with more relevant options. This is a display-order
        # nudge, not a filter -- every safe food is still in the list.
        w_protein = _PRIORITY_WEIGHT.get(rules.get("protein_priority"), 1)
        w_carb = _PRIORITY_WEIGHT.get(rules.get("carb_priority"), 1)
        w_fat = _PRIORITY_WEIGHT.get(rules.get("fat_priority"), 1)
        w_fiber = _PRIORITY_WEIGHT.get(rules.get("fiber_priority"), 1)
        score = (
            safe["protein_g_per_g"] * w_protein
            + safe["fiber_g_per_g"] * w_fiber
            + safe["carbs_g_per_g"] * w_carb * 0.3
            + safe["fat_g_per_g"] * w_fat * 0.3
        ) / safe["calories_per_g"].clip(lower=0.01)
        safe = safe.assign(_body_build_score=score).sort_values("_body_build_score", ascending=False)

    names = safe["food_name"].tolist()
    return names[:limit]


_GRAMS_RE = re.compile(r"([-+]?\d*\.?\d+)\s*g\b", re.IGNORECASE)


def parse_item(item_str: str) -> tuple[str, float]:
    """'Paneer parantha/paratha(120g)' -> ('Paneer parantha/paratha', 120.0).
    Defaults to 100g if no gram amount is present in the item string."""
    match = _GRAMS_RE.search(item_str)
    grams = float(match.group(1)) if match else 100.0
    name = _GRAMS_RE.sub("", item_str)
    name = re.sub(r"[()]", "", name).strip()
    return name, grams


def lookup(food_name: str, cutoff: float = 0.6):
    """Best-effort fuzzy match against the database. Returns the matching
    row (as a dict) or None if nothing close enough was found."""
    df = load_foods()
    name_lower = food_name.lower().strip()

    exact = df[df["_name_lower"] == name_lower]
    if not exact.empty:
        return exact.iloc[0].to_dict()

    # substring match (handles "Paneer Parantha" vs "Paneer parantha/paratha")
    contains = df[df["_name_lower"].str.contains(re.escape(name_lower), na=False)]
    if not contains.empty:
        return contains.iloc[0].to_dict()

    close = difflib.get_close_matches(name_lower, df["_name_lower"].tolist(), n=1, cutoff=cutoff)
    if close:
        return df[df["_name_lower"] == close[0]].iloc[0].to_dict()

    return None


_ATWATER_TOLERANCE = 0.15  # relative slack allowed before a row is flagged


def calorie_macro_mismatch(row: dict, tolerance: float = _ATWATER_TOLERANCE) -> bool:
    """True if a food_database.csv row's own stated calories_per_g is
    inconsistent with what its protein/carbs/fat_per_g would imply via the
    standard Atwater factors (4 kcal/g protein, 4 kcal/g carbs, 9 kcal/g
    fat), by more than `tolerance` (relative).

    This is a data-quality check on the CSV row itself -- independent of
    (and a different failure mode from) the per-meal budget scaling done in
    services/groq_service.py. A row can pass through parse/lookup/scaling
    just fine and still have macros that don't add up to its own calorie
    figure (e.g. a dish whose calories weren't updated to match its
    protein/carbs/fat when the dataset was edited). Flagging it here lets
    callers surface a warning that actually names the real cause, instead
    of the scaling pass silently producing a meal total that looks "wrong"
    for no explained reason.
    """
    implied = (
        row.get("protein_g_per_g", 0) * 4
        + row.get("carbs_g_per_g", 0) * 4
        + row.get("fat_g_per_g", 0) * 9
    )
    stated = row.get("calories_per_g", 0) or 0
    if stated <= 0:
        return implied > 0
    return abs(implied - stated) / stated > tolerance


def nutrition_for_item(item_str: str) -> dict | None:
    """Looks up an LLM-produced item string against the database and scales
    its per-1g nutrition to the stated gram amount. Returns None if the
    food couldn't be matched -- callers should treat that as "unverified"
    rather than silently guessing."""
    name, grams = parse_item(item_str)
    row = lookup(name)
    if row is None:
        return None
    scale = grams
    return {
        "matched_name": row["food_name"],
        "grams": grams,
        "calories": round(row["calories_per_g"] * scale, 1),
        "protein_g": round(row["protein_g_per_g"] * scale, 1),
        "carbs_g": round(row["carbs_g_per_g"] * scale, 1),
        "fat_g": round(row["fat_g_per_g"] * scale, 1),
        "verified": row.get("classification_method") != "inferred_from_dish_name_keywords",
        "macro_mismatch": calorie_macro_mismatch(row),
    }


def violates_restrictions(food_name: str, required_flags: set[str]) -> bool:
    """True if the matched food is known to fail one of the required
    flags. Foods that can't be matched at all are NOT flagged here --
    that's a separate 'unverified' case handled by the caller."""
    name, _ = parse_item(food_name)
    row = lookup(name)
    if row is None:
        return False
    return any(not row.get(flag, True) for flag in required_flags)
