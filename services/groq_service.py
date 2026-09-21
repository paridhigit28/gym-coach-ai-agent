# # # import os
# # # import json
# # # import re
# # # from groq import Groq
# # # from utils.prompts import WORKOUT_PROMPT, DIET_PROMPT, CHAT_PROMPT, INSIGHTS_PROMPT

# # # GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# # # def configure_groq() -> Groq:
# # #     api_key = os.getenv("GROQ_API_KEY")
# # #     if not api_key or api_key == "your_groq_api_key_here":
# # #         raise ValueError("GROQ_API_KEY not found or invalid in .env")

# # #     return Groq(api_key=api_key)


# # # def parse_json_response(response_text):
# # #     text = (response_text or "").strip()

# # #     # Strip a leading code fence of any form: ``` , ```json , ```JSON , etc.
# # #     if text.startswith("```"):
# # #         text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
# # #         text = re.sub(r"\s*```\s*$", "", text)
# # #         text = text.strip()

# # #     try:
# # #         return json.loads(text)
# # #     except json.JSONDecodeError:
# # #         pass

# # #     # Fallback: the model may have added stray text around the JSON object
# # #     # (e.g. "Sure, here's your plan:\n{...}"). Grab the outermost {...} block.
# # #     match = re.search(r"\{.*\}", text, re.DOTALL)
# # #     if match:
# # #         try:
# # #             return json.loads(match.group(0))
# # #         except json.JSONDecodeError as e:
# # #             raise ValueError(f"Failed to parse Groq response as JSON: {e}\nRaw Response: {response_text}")

# # #     raise ValueError(f"Failed to parse Groq response as JSON: no JSON object found.\nRaw Response: {response_text}")


# # # def _generate(prompt: str) -> str:
# # #     client = configure_groq()
# # #     response = client.chat.completions.create(
# # #         model=GROQ_MODEL,
# # #         messages=[{"role": "user", "content": prompt}],
# # #     )
# # #     return response.choices[0].message.content


# # # def generate_workout_plan(user_data: dict) -> dict:
# # #     prompt = WORKOUT_PROMPT.format(**user_data)
# # #     text = _generate(prompt)
# # #     return parse_json_response(text)


# # # def generate_meal_plan(user_data: dict) -> dict:
# # #     prompt = DIET_PROMPT.format(**user_data)
# # #     text = _generate(prompt)
# # #     return parse_json_response(text)


# # # def fitness_chat(user_id, message, chat_history):
# # #     client = configure_groq()

# # #     # ChatHistory.role in this project is stored as 'user' or 'model'
# # #     # (see database/models.py) -- 'model' was Gemini's assistant-role name,
# # #     # so it's mapped to Groq/OpenAI-style 'assistant' here. New rows written
# # #     # going forward will still say 'model' unless you also update wherever
# # #     # ChatHistory rows get created; either is handled by this mapping.
# # #     formatted_history = [{"role": "system", "content": CHAT_PROMPT}]
# # #     for msg in chat_history:
# # #         role = "assistant" if msg.role in ("model", "assistant") else "user"
# # #         formatted_history.append({"role": role, "content": msg.message})

# # #     formatted_history.append({"role": "user", "content": message})

# # #     response llama-3.3-70b-versatile= client.chat.completions.create(
# # #         model=GROQ_MODEL,
# # #         messages=formatted_history,
# # #     )
# # #     return response.choices[0].message.content


# # # def generate_weekly_insights(progress_data: str) -> dict:
# # #     prompt = INSIGHTS_PROMPT.format(progress_data=progress_data)
# # #     text = _generate(prompt)
# # #     return parse_json_response(text)

# # import os
# # import json
# # import re
# # from groq import Groq
# # from utils.prompts import WORKOUT_PROMPT, DIET_PROMPT, CHAT_PROMPT, INSIGHTS_PROMPT
# # from nutrition import calculator, food_database, body_build as body_build_module

# # GROQ_MODEL = os.getenv("GROQ_MODEL", "")

# # # --- Portion-sync tuning (see the scaling pass in generate_meal_plan()) ---
# # # After the model picks items, each meal's *real* calorie total (looked up
# # # from food_database.csv) is compared to that meal's calorie budget and the
# # # item portions are scaled to close the gap -- this is what keeps the
# # # top-level Target Calories/Macros in sync with what the meals actually add
# # # up to, instead of just hoping the model's guessed grams land close.
# # _MEAL_SYNC_TOLERANCE = 0.10   # meals within +-10% of budget after scaling are left alone
# # _ITEM_SCALE_MIN = 0.4         # never shrink an item below 40% of what the model picked
# # _ITEM_SCALE_MAX = 2.5         # never grow an item beyond 250% of what the model picked
# # _ITEM_GRAMS_FLOOR = 10.0      # never round an item down to an unrealistically tiny amount
# # _ITEM_GRAMS_CEILING = 800.0   # never scale an item up to an unrealistically huge amount

# # # --- Daily-total validation tolerance (see the retry loop in
# # # generate_meal_plan()) -- separate from _MEAL_SYNC_TOLERANCE above, which
# # # only governs the per-meal portion-scaling pass. These govern whether a
# # # whole attempt (after scaling) is accepted as close enough to the
# # # calculator's targets, or the model gets asked to pick different foods and
# # # try again.
# # _CALORIE_TOLERANCE = 0.05     # daily actual calories must land within +-5% of TargetCalories
# # _MACRO_TOLERANCE = 0.10       # each daily actual macro (protein/carbs/fat) within +-10% of target


# # def configure_groq() -> Groq:
# #     api_key = os.getenv("GROQ_API_KEY")
# #     if not api_key or api_key == "your_groq_api_key_here":
# #         raise ValueError("GROQ_API_KEY not found or invalid in .env")

# #     return Groq(api_key=api_key)


# # def parse_json_response(response_text):
# #     text = (response_text or "").strip()

# #     # Strip a leading code fence of any form: ``` , ```json , ```JSON , etc.
# #     if text.startswith("```"):
# #         text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
# #         text = re.sub(r"\s*```\s*$", "", text)
# #         text = text.strip()

# #     try:
# #         return json.loads(text)
# #     except json.JSONDecodeError:
# #         pass

# #     # Fallback: the model may have added stray text around the JSON object
# #     # (e.g. "Sure, here's your plan:\n{...}"). Grab the outermost {...} block.
# #     match = re.search(r"\{.*\}", text, re.DOTALL)
# #     if match:
# #         try:
# #             return json.loads(match.group(0))
# #         except json.JSONDecodeError as e:
# #             raise ValueError(f"Failed to parse Groq response as JSON: {e}\nRaw Response: {response_text}")

# #     raise ValueError(f"Failed to parse Groq response as JSON: no JSON object found.\nRaw Response: {response_text}")


# # def _generate(prompt: str) -> str:
# #     client = configure_groq()
# #     response = client.chat.completions.create(
# #         model=GROQ_MODEL,
# #         messages=[{"role": "user", "content": prompt}],
# #     )
# #     return response.choices[0].message.content


# # def generate_workout_plan(user_data: dict) -> dict:
# #     prompt = WORKOUT_PROMPT.format(**user_data)
# #     text = _generate(prompt)
# #     return parse_json_response(text)


# # def _meal_macro_budgets(protein_g: float, carb_g: float, fat_g: float) -> dict:
# #     """Per-meal Protein/Carbs/Fat targets (grams), split using the same
# #     percentages calculator.py's MEAL_SPLIT already uses for the per-meal
# #     calorie budgets -- keeps calories and macros proportionally consistent
# #     across meals without adding any new logic to calculator.py itself."""
# #     return {
# #         meal: {
# #             "protein_g": round(protein_g * pct),
# #             "carb_g": round(carb_g * pct),
# #             "fat_g": round(fat_g * pct),
# #         }
# #         for meal, pct in calculator.MEAL_SPLIT.items()
# #     }


# # def _macro_guidance_block(targets: dict, budgets: dict, macro_budgets: dict) -> str:
# #     """Extra prompt text listing daily and per-meal Protein/Carbs/Fat
# #     targets. Appended after DIET_PROMPT.format(...) rather than added as a
# #     new template placeholder, so utils/prompts.py doesn't need to change --
# #     this makes food selection macro-aware, not only calorie-aware."""
# #     lines = [
# #         "",
# #         "Additional macro targets (grams) -- choose foods so each meal's "
# #         "Protein/Carbs/Fat land close to these too, not just its calories:",
# #         f"- Daily: Protein {targets['_protein_g']}g | Carbs {targets['_carb_g']}g | "
# #         f"Fat {targets['_fat_g']}g",
# #     ]
# #     for meal_name, mb in macro_budgets.items():
# #         cal = budgets.get(meal_name, "-")
# #         lines.append(
# #             f"- {meal_name} (~{cal} kcal): Protein {mb['protein_g']}g | "
# #             f"Carbs {mb['carb_g']}g | Fat {mb['fat_g']}g"
# #         )
# #     return "\n".join(lines)


# # def _tolerance_gap(actual_calories: float, actual_protein: float, actual_carbs: float,
# #                     actual_fats: float, targets: dict) -> float:
# #     """0.0 if the daily actual totals are within tolerance of the
# #     calculator's targets on every axis (calories +-5%, each macro +-10%);
# #     otherwise a positive score (larger = further off), used only to pick the
# #     closest-of-several attempts when none lands fully inside tolerance."""

# #     def _excess(actual: float, target: float, tolerance: float) -> float:
# #         if not target:
# #             return 0.0
# #         return max(abs(actual - target) / target - tolerance, 0.0)

# #     return (
# #         _excess(actual_calories, targets["TargetCalories"], _CALORIE_TOLERANCE)
# #         + _excess(actual_protein, targets["_protein_g"], _MACRO_TOLERANCE)
# #         + _excess(actual_carbs, targets["_carb_g"], _MACRO_TOLERANCE)
# #         + _excess(actual_fats, targets["_fat_g"], _MACRO_TOLERANCE)
# #     )


# # def _process_meals(meals_raw: dict, budgets: dict, required_flags) -> tuple:
# #     """Replace whatever the model said about calories/macros with real
# #     numbers looked up per item, drop anything that turns out to violate a
# #     restriction despite the pre-filtered candidate list, THEN scale each
# #     meal's item portions so the real (looked-up) calorie total actually
# #     lands close to that meal's budget -- this is the step that keeps the
# #     Target Calories/Macros shown at the top of the page in sync with what
# #     the Meals section actually adds up to. Without it, the model's guessed
# #     gram amounts (e.g. a 200g soup + a 50g roti) can easily undershoot or
# #     overshoot the target by a large margin even though every individual
# #     number is independently "correct".

# #     Returns (meals_final, warnings, daily_actual_calories,
# #     daily_actual_protein, daily_actual_carbs, daily_actual_fats) for this
# #     one attempt's food selection -- unchanged calorie-scaling logic, just
# #     extracted so generate_meal_plan() can run it once per retry attempt.
# #     """
# #     warnings: list[str] = []
# #     mismatched_foods_warned: set[str] = set()  # dedupe across meals -- it's a per-food data issue, not per-meal
# #     meals_final = {}
# #     for meal_name, meal in meals_raw.items():
# #         items = meal.get("Items", []) if isinstance(meal, dict) else []
# #         parsed_items: list[dict] = []   # matched foods -- rescalable
# #         unverified_items: list[str] = []  # couldn't be matched -- left as-is, not scaled
# #         for item in items:
# #             if food_database.violates_restrictions(item, required_flags):
# #                 warnings.append(f"{meal_name}: removed '{item}' -- conflicts with a stated restriction")
# #                 continue
# #             nutrition = food_database.nutrition_for_item(item)
# #             if nutrition is None:
# #                 warnings.append(f"{meal_name}: '{item}' isn't in the food database -- kept but unverified")
# #                 unverified_items.append(item)
# #                 continue
# #             if nutrition["macro_mismatch"] and nutrition["matched_name"] not in mismatched_foods_warned:
# #                 mismatched_foods_warned.add(nutrition["matched_name"])
# #                 warnings.append(
# #                     f"'{nutrition['matched_name']}' -- this food's own calories_per_g in "
# #                     f"food_database.csv doesn't add up (via 4/4/9 Atwater) to its "
# #                     f"protein/carbs/fat_per_g -- fix the row in the CSV, this isn't a "
# #                     f"portion-scaling issue"
# #                 )
# #             parsed_items.append(nutrition)

# #         meal_budget = budgets.get(meal_name)
# #         cal_total = sum(n["calories"] for n in parsed_items)

# #         # Scale portions (up or down) so this meal's real total lands close
# #         # to its budget. Skipped if there's nothing to scale, no budget to
# #         # target, or the picked items happen to be ~0 kcal (can't scale a
# #         # ratio off of zero).
# #         if parsed_items and meal_budget and cal_total > 0:
# #             raw_scale = meal_budget / cal_total
# #             scale = min(max(raw_scale, _ITEM_SCALE_MIN), _ITEM_SCALE_MAX)
# #             if abs(scale - 1.0) > 1e-6:
# #                 for n in parsed_items:
# #                     target_grams = n["grams"] * scale
# #                     new_grams = min(max(target_grams, _ITEM_GRAMS_FLOOR), _ITEM_GRAMS_CEILING)
# #                     ratio = (new_grams / n["grams"]) if n["grams"] else 1.0
# #                     n["grams"] = round(new_grams, 1)
# #                     n["calories"] = round(n["calories"] * ratio, 1)
# #                     n["protein_g"] = round(n["protein_g"] * ratio, 1)
# #                     n["carbs_g"] = round(n["carbs_g"] * ratio, 1)
# #                     n["fat_g"] = round(n["fat_g"] * ratio, 1)
# #             cal_total = sum(n["calories"] for n in parsed_items)

# #         if meal_budget and cal_total and abs(cal_total - meal_budget) / meal_budget > _MEAL_SYNC_TOLERANCE:
# #             direction = "above" if cal_total > meal_budget else "below"
# #             warnings.append(
# #                 f"{meal_name}: portions were adjusted but the meal is still {direction} its "
# #                 f"~{meal_budget} kcal budget ({round(cal_total)} kcal) -- the chosen foods "
# #                 f"couldn't be scaled into range without an unrealistic portion size."
# #             )

# #         kept_items = [f"{n['matched_name']}({n['grams']:g}g)" for n in parsed_items] + unverified_items
# #         p_total = sum(n["protein_g"] for n in parsed_items)
# #         c_total = sum(n["carbs_g"] for n in parsed_items)
# #         f_total = sum(n["fat_g"] for n in parsed_items)

# #         meals_final[meal_name] = {
# #             "Items": kept_items,
# #             "Calories": round(cal_total),
# #             "Protein": f"{round(p_total)}g",
# #             "Carbs": f"{round(c_total)}g",
# #             "Fats": f"{round(f_total)}g",
# #         }

# #     daily_actual_calories = sum(m["Calories"] for m in meals_final.values())
# #     daily_actual_protein = sum(float(m["Protein"].rstrip("g") or 0) for m in meals_final.values())
# #     daily_actual_carbs = sum(float(m["Carbs"].rstrip("g") or 0) for m in meals_final.values())
# #     daily_actual_fats = sum(float(m["Fats"].rstrip("g") or 0) for m in meals_final.values())

# #     return (meals_final, warnings, daily_actual_calories, daily_actual_protein,
# #             daily_actual_carbs, daily_actual_fats)


# # def generate_meal_plan(user_data: dict, max_attempts: int = 3) -> dict:
# #     """Generates a meal plan where the LLM only chooses which foods go in
# #     each meal -- every Calories/Protein/Carbs/Fats number in the returned
# #     plan (daily and per-meal) comes from nutrition/calculator.py and
# #     nutrition/food_database.py, not from the model. After the model picks
# #     items, their portions are scaled (see the sync pass below) so the real,
# #     looked-up meal totals actually land close to the deterministic
# #     Target Calories/Macros -- not just each individually "correct" but
# #     collectively mismatched with the target. This means the numbers are
# #     internally consistent AND synchronized with the target for every
# #     request, not just when the model's own guessed portions happen to add
# #     up right.

# #     The prompt also states daily and per-meal Protein/Carbs/Fat targets (not
# #     just calories), so the model's food selection is macro-aware. After
# #     scaling, the resulting daily actual totals are checked against the
# #     calculator's targets (calories +-5%, each macro +-10%); if they're
# #     outside tolerance, the model is asked to pick different foods and the
# #     whole selection+scaling pass runs again, up to max_attempts times. The
# #     closest attempt seen is kept even if none lands fully inside tolerance.

# #     Required user_data keys: age, gender, weight, height, goal,
# #     activity_level, diet, food_restrictions.
# #     Optional key: body_build -- one of nutrition.body_build.BODY_BUILD_OPTIONS
# #     (the user-friendly name, e.g. "Lean / Slim Build"), or None/absent for
# #     users who skipped this optional assessment field.
# #     """
# #     body_build = user_data.get("body_build") or None
# #     if not body_build_module.is_valid_body_build(body_build):
# #         # Unrecognized value (e.g. stale/corrupt data) -- fail safe by
# #         # treating it as "not provided" rather than erroring the whole plan.
# #         body_build = None

# #     # 1. Deterministic daily targets -- never asked of the LLM. Body Build
# #     #    (if any) is applied here exactly once, as a secondary adjustment
# #     #    on top of the primary BMR/TDEE/Goal calculation.
# #     targets = calculator.calculate_targets(
# #         weight_kg=float(user_data["weight"]),
# #         height_cm=float(user_data["height"]),
# #         age=int(user_data["age"]),
# #         gender=user_data.get("gender", ""),
# #         activity_level=user_data.get("activity_level", ""),
# #         goal=user_data.get("goal", ""),
# #         body_build=body_build,
# #     )
# #     budgets = calculator.meal_calorie_budgets(targets["TargetCalories"])
# #     macro_budgets = _meal_macro_budgets(targets["_protein_g"], targets["_carb_g"], targets["_fat_g"])

# #     # 2. Filter the food database down to what's safe for this user (allergy/
# #     #    diet restrictions -- unaffected by Body Build), then re-order the
# #     #    remaining safe candidates so foods relevant to this Body Build lead
# #     #    the list the model sees.
# #     required_flags = food_database.diet_preference_flags(user_data.get("diet", ""))
# #     required_flags |= food_database.parse_restrictions_text(user_data.get("food_restrictions", ""))
# #     candidates = food_database.candidate_foods(required_flags, body_build=body_build)

# #     rules = body_build_module.get_rules(body_build)
# #     if rules:
# #         body_build_guidance = (
# #             f"Body Build personalization ({body_build} -> internally "
# #             f"'{body_build_module.get_internal_type(body_build)}', a heuristic "
# #             f"classification, not a diagnosis): {rules['food_selection_strategy']}\n"
# #         )
# #     else:
# #         body_build_guidance = ""

# #     prompt = DIET_PROMPT.format(
# #         age=user_data["age"],
# #         gender=user_data.get("gender", ""),
# #         weight=user_data["weight"],
# #         height=user_data["height"],
# #         goal=user_data.get("goal", ""),
# #         activity_level=user_data.get("activity_level", ""),
# #         diet=user_data.get("diet", ""),
# #         body_build=body_build or "Not specified",
# #         food_restrictions=user_data.get("food_restrictions", "None"),
# #         target_calories=targets["TargetCalories"],
# #         protein_g=targets["_protein_g"],
# #         carb_g=targets["_carb_g"],
# #         fat_g=targets["_fat_g"],
# #         breakfast_kcal=budgets["Breakfast"],
# #         lunch_kcal=budgets["Lunch"],
# #         snack_kcal=budgets["EveningSnack"],
# #         dinner_kcal=budgets["Dinner"],
# #         body_build_guidance=body_build_guidance,
# #         candidate_foods=", ".join(candidates) if candidates else "(none available -- see warning)",
# #     )
# #     # Daily and per-meal Protein/Carbs/Fat targets -- appended rather than
# #     # added as a new DIET_PROMPT placeholder, so utils/prompts.py doesn't
# #     # need to change. This is what makes food selection macro-aware instead
# #     # of only calorie-aware.
# #     prompt += "\n" + _macro_guidance_block(targets, budgets, macro_budgets)

# #     base_warnings: list[str] = []
# #     if not candidates:
# #         base_warnings.append(
# #             "No foods in the database matched this user's Diet Preference / Food "
# #             "Restrictions combination, so the model had no safe candidate list to "
# #             "choose from -- treat any items below as unverified."
# #         )

# #     # 3. Generate -> process/scale -> validate against the calculator's
# #     #    daily targets, retrying with a fresh food selection (same prompt,
# #     #    the model can pick differently each call) if the result lands
# #     #    outside tolerance. Keeps whichever attempt gets closest even if
# #     #    none lands fully inside tolerance, rather than discarding work.
# #     best = None  # (gap, meals_final, meal_warnings, cal, protein, carbs, fats)
# #     attempts = max(1, max_attempts)
# #     for _ in range(attempts):
# #         text = _generate(prompt)
# #         response = parse_json_response(text)
# #         meals_raw = response.get("Meals", {})
# #         # Skip (and retry, if attempts remain) if the model ignored the
# #         # instruction and returned nothing usable.
# #         if not any(isinstance(m, dict) and m.get("Items") for m in meals_raw.values()):
# #             continue

# #         (meals_final, meal_warnings, daily_actual_calories, daily_actual_protein,
# #          daily_actual_carbs, daily_actual_fats) = _process_meals(meals_raw, budgets, required_flags)

# #         gap = _tolerance_gap(daily_actual_calories, daily_actual_protein,
# #                               daily_actual_carbs, daily_actual_fats, targets)

# #         if best is None or gap < best[0]:
# #             best = (gap, meals_final, meal_warnings, daily_actual_calories,
# #                      daily_actual_protein, daily_actual_carbs, daily_actual_fats)

# #         if gap <= 0:
# #             break  # within tolerance on calories and every macro -- no need to retry

# #     if best is None:
# #         # Every attempt returned nothing usable.
# #         meals_final, meal_warnings = {}, []
# #         daily_actual_calories = daily_actual_protein = daily_actual_carbs = daily_actual_fats = 0.0
# #     else:
# #         (_, meals_final, meal_warnings, daily_actual_calories, daily_actual_protein,
# #          daily_actual_carbs, daily_actual_fats) = best

# #     warnings = base_warnings + meal_warnings

# #     # 4. Daily actual totals -- the real sum of what's in the Meals section
# #     #    above, computed the same way (from food_database.csv), so the UI
# #     #    can show it next to Target Calories/Macros and the two numbers are
# #     #    always describing the same thing. If they still don't match closely
# #     #    after every retry attempt, that's surfaced as a warning rather than
# #     #    silently left inconsistent.
# #     target_calories = targets["TargetCalories"]
# #     if target_calories and abs(daily_actual_calories - target_calories) / target_calories > _CALORIE_TOLERANCE:
# #         direction = "above" if daily_actual_calories > target_calories else "below"
# #         warnings.append(
# #             f"Daily total ({round(daily_actual_calories)} kcal) is still {direction} the "
# #             f"{target_calories} kcal Target Calories after {attempts} generation attempt(s) -- "
# #             f"see the per-meal notes above for which meal(s) couldn't be scaled into range."
# #         )

# #     for label, actual, target_key in (
# #         ("Protein", daily_actual_protein, "_protein_g"),
# #         ("Carbs", daily_actual_carbs, "_carb_g"),
# #         ("Fats", daily_actual_fats, "_fat_g"),
# #     ):
# #         target_val = targets[target_key]
# #         if target_val and abs(actual - target_val) / target_val > _MACRO_TOLERANCE:
# #             direction = "above" if actual > target_val else "below"
# #             warnings.append(
# #                 f"Daily {label} ({round(actual)}g) is still {direction} the {target_val}g target "
# #                 f"by more than {int(_MACRO_TOLERANCE * 100)}% after {attempts} generation attempt(s)."
# #             )

# #     plan = {
# #         "MaintenanceCalories": targets["MaintenanceCalories"],
# #         "TargetCalories": targets["TargetCalories"],
# #         "DailyMacros": targets["DailyMacros"],
# #         "BodyBuild": body_build,
# #         "Meals": meals_final,
# #         "DailyActualCalories": round(daily_actual_calories),
# #         "DailyActualMacros": {
# #             "Protein": f"{round(daily_actual_protein)}g",
# #             "Carbs": f"{round(daily_actual_carbs)}g",
# #             "Fats": f"{round(daily_actual_fats)}g",
# #         },
# #     }
# #     if warnings:
# #         plan["_nutrition_warnings"] = warnings
# #     return plan


# # def fitness_chat(user_id, message, chat_history):
# #     client = configure_groq()

# #     # ChatHistory.role in this project is stored as 'user' or 'model'
# #     # (see database/models.py) -- 'model' was Gemini's assistant-role name,
# #     # so it's mapped to Groq/OpenAI-style 'assistant' here. New rows written
# #     # going forward will still say 'model' unless you also update wherever
# #     # ChatHistory rows get created; either is handled by this mapping.
# #     formatted_history = [{"role": "system", "content": CHAT_PROMPT}]
# #     for msg in chat_history:
# #         role = "assistant" if msg.role in ("model", "assistant") else "user"
# #         formatted_history.append({"role": role, "content": msg.message})

# #     formatted_history.append({"role": "user", "content": message})

# #     response = client.chat.completions.create(
# #         model=GROQ_MODEL,
# #         messages=formatted_history,
# #     )
# #     return response.choices[0].message.content


# # def generate_weekly_insights(progress_data: str) -> dict:
# #     prompt = INSIGHTS_PROMPT.format(progress_data=progress_data)
# #     text = _generate(prompt)
# #     return parse_json_response(text)

# # import os
# # import json
# # import re
# # from groq import Groq
# # from utils.prompts import WORKOUT_PROMPT, DIET_PROMPT, CHAT_PROMPT, INSIGHTS_PROMPT

# # GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# # def configure_groq() -> Groq:
# #     api_key = os.getenv("GROQ_API_KEY")
# #     if not api_key or api_key == "your_groq_api_key_here":
# #         raise ValueError("GROQ_API_KEY not found or invalid in .env")

# #     return Groq(api_key=api_key)


# # def parse_json_response(response_text):
# #     text = (response_text or "").strip()

# #     # Strip a leading code fence of any form: ``` , ```json , ```JSON , etc.
# #     if text.startswith("```"):
# #         text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
# #         text = re.sub(r"\s*```\s*$", "", text)
# #         text = text.strip()

# #     try:
# #         return json.loads(text)
# #     except json.JSONDecodeError:
# #         pass

# #     # Fallback: the model may have added stray text around the JSON object
# #     # (e.g. "Sure, here's your plan:\n{...}"). Grab the outermost {...} block.
# #     match = re.search(r"\{.*\}", text, re.DOTALL)
# #     if match:
# #         try:
# #             return json.loads(match.group(0))
# #         except json.JSONDecodeError as e:
# #             raise ValueError(f"Failed to parse Groq response as JSON: {e}\nRaw Response: {response_text}")

# #     raise ValueError(f"Failed to parse Groq response as JSON: no JSON object found.\nRaw Response: {response_text}")


# # def _generate(prompt: str) -> str:
# #     client = configure_groq()
# #     response = client.chat.completions.create(
# #         model=GROQ_MODEL,
# #         messages=[{"role": "user", "content": prompt}],
# #     )
# #     return response.choices[0].message.content


# # def generate_workout_plan(user_data: dict) -> dict:
# #     prompt = WORKOUT_PROMPT.format(**user_data)
# #     text = _generate(prompt)
# #     return parse_json_response(text)


# # def generate_meal_plan(user_data: dict) -> dict:
# #     prompt = DIET_PROMPT.format(**user_data)
# #     text = _generate(prompt)
# #     return parse_json_response(text)


# # def fitness_chat(user_id, message, chat_history):
# #     client = configure_groq()

# #     # ChatHistory.role in this project is stored as 'user' or 'model'
# #     # (see database/models.py) -- 'model' was Gemini's assistant-role name,
# #     # so it's mapped to Groq/OpenAI-style 'assistant' here. New rows written
# #     # going forward will still say 'model' unless you also update wherever
# #     # ChatHistory rows get created; either is handled by this mapping.
# #     formatted_history = [{"role": "system", "content": CHAT_PROMPT}]
# #     for msg in chat_history:
# #         role = "assistant" if msg.role in ("model", "assistant") else "user"
# #         formatted_history.append({"role": role, "content": msg.message})

# #     formatted_history.append({"role": "user", "content": message})

# #     response llama-3.3-70b-versatile= client.chat.completions.create(
# #         model=GROQ_MODEL,
# #         messages=formatted_history,
# #     )
# #     return response.choices[0].message.content


# # def generate_weekly_insights(progress_data: str) -> dict:
# #     prompt = INSIGHTS_PROMPT.format(progress_data=progress_data)
# #     text = _generate(prompt)
# #     return parse_json_response(text)

# import os
# import json
# import re
# from groq import Groq
# from utils.prompts import WORKOUT_PROMPT, DIET_PROMPT, CHAT_PROMPT, INSIGHTS_PROMPT
# from nutrition import calculator, food_database, body_build as body_build_module

# GROQ_MODEL = os.getenv("GROQ_MODEL", "")

# # --- Portion-sync tuning (see the scaling pass in generate_meal_plan()) ---
# # After the model picks items, each meal's *real* calorie total (looked up
# # from food_database.csv) is compared to that meal's calorie budget and the
# # item portions are scaled to close the gap -- this is what keeps the
# # top-level Target Calories/Macros in sync with what the meals actually add
# # up to, instead of just hoping the model's guessed grams land close.
# _MEAL_SYNC_TOLERANCE = 0.10   # meals within +-10% of budget after scaling are left alone
# _ITEM_SCALE_MIN = 0.4         # never shrink an item below 40% of what the model picked
# _ITEM_SCALE_MAX = 2.5         # never grow an item beyond 250% of what the model picked
# _ITEM_GRAMS_FLOOR = 10.0      # never round an item down to an unrealistically tiny amount
# _ITEM_GRAMS_CEILING = 800.0   # never scale an item up to an unrealistically huge amount

# # --- Daily-total validation tolerance (see the retry loop in
# # generate_meal_plan()) -- separate from _MEAL_SYNC_TOLERANCE above, which
# # only governs the per-meal portion-scaling pass. These govern whether a
# # whole attempt (after scaling) is accepted as close enough to the
# # calculator's targets, or the model gets asked to pick different foods and
# # try again.
# _CALORIE_TOLERANCE = 0.05     # daily actual calories must land within +-5% of TargetCalories
# _MACRO_TOLERANCE = 0.10       # each daily actual macro (protein/carbs/fat) within +-10% of target


# def configure_groq() -> Groq:
#     api_key = os.getenv("GROQ_API_KEY")
#     if not api_key or api_key == "your_groq_api_key_here":
#         raise ValueError("GROQ_API_KEY not found or invalid in .env")

#     return Groq(api_key=api_key)


# def parse_json_response(response_text):
#     text = (response_text or "").strip()

#     # Strip a leading code fence of any form: ``` , ```json , ```JSON , etc.
#     if text.startswith("```"):
#         text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
#         text = re.sub(r"\s*```\s*$", "", text)
#         text = text.strip()

#     try:
#         return json.loads(text)
#     except json.JSONDecodeError:
#         pass

#     # Fallback: the model may have added stray text around the JSON object
#     # (e.g. "Sure, here's your plan:\n{...}"). Grab the outermost {...} block.
#     match = re.search(r"\{.*\}", text, re.DOTALL)
#     if match:
#         try:
#             return json.loads(match.group(0))
#         except json.JSONDecodeError as e:
#             raise ValueError(f"Failed to parse Groq response as JSON: {e}\nRaw Response: {response_text}")

#     raise ValueError(f"Failed to parse Groq response as JSON: no JSON object found.\nRaw Response: {response_text}")


# def _generate(prompt: str) -> str:
#     client = configure_groq()
#     response = client.chat.completions.create(
#         model=GROQ_MODEL,
#         messages=[{"role": "user", "content": prompt}],
#         reasoning_effort="low",
#         max_completion_tokens=8192,
#     )
#     content = response.choices[0].message.content
#     if not content:
#         # Reasoning models (e.g. openai/gpt-oss-120b) can occasionally put
#         # the final answer in the "reasoning" field instead of "content" --
#         # fall back to that rather than returning an empty string.
#         content = getattr(response.choices[0].message, "reasoning", "") or ""
#     return content


# def generate_workout_plan(user_data: dict) -> dict:
#     prompt = WORKOUT_PROMPT.format(**user_data)
#     text = _generate(prompt)
#     return parse_json_response(text)


# def _meal_macro_budgets(protein_g: float, carb_g: float, fat_g: float) -> dict:
#     """Per-meal Protein/Carbs/Fat targets (grams), split using the same
#     percentages calculator.py's MEAL_SPLIT already uses for the per-meal
#     calorie budgets -- keeps calories and macros proportionally consistent
#     across meals without adding any new logic to calculator.py itself."""
#     return {
#         meal: {
#             "protein_g": round(protein_g * pct),
#             "carb_g": round(carb_g * pct),
#             "fat_g": round(fat_g * pct),
#         }
#         for meal, pct in calculator.MEAL_SPLIT.items()
#     }


# def _macro_guidance_block(targets: dict, budgets: dict, macro_budgets: dict) -> str:
#     """Extra prompt text listing daily and per-meal Protein/Carbs/Fat
#     targets. Appended after DIET_PROMPT.format(...) rather than added as a
#     new template placeholder, so utils/prompts.py doesn't need to change --
#     this makes food selection macro-aware, not only calorie-aware."""
#     lines = [
#         "",
#         "Additional macro targets (grams) -- choose foods so each meal's "
#         "Protein/Carbs/Fat land close to these too, not just its calories:",
#         f"- Daily: Protein {targets['_protein_g']}g | Carbs {targets['_carb_g']}g | "
#         f"Fat {targets['_fat_g']}g",
#     ]
#     for meal_name, mb in macro_budgets.items():
#         cal = budgets.get(meal_name, "-")
#         lines.append(
#             f"- {meal_name} (~{cal} kcal): Protein {mb['protein_g']}g | "
#             f"Carbs {mb['carb_g']}g | Fat {mb['fat_g']}g"
#         )
#     return "\n".join(lines)


# def _tolerance_gap(actual_calories: float, actual_protein: float, actual_carbs: float,
#                     actual_fats: float, targets: dict) -> float:
#     """0.0 if the daily actual totals are within tolerance of the
#     calculator's targets on every axis (calories +-5%, each macro +-10%);
#     otherwise a positive score (larger = further off), used only to pick the
#     closest-of-several attempts when none lands fully inside tolerance."""

#     def _excess(actual: float, target: float, tolerance: float) -> float:
#         if not target:
#             return 0.0
#         return max(abs(actual - target) / target - tolerance, 0.0)

#     return (
#         _excess(actual_calories, targets["TargetCalories"], _CALORIE_TOLERANCE)
#         + _excess(actual_protein, targets["_protein_g"], _MACRO_TOLERANCE)
#         + _excess(actual_carbs, targets["_carb_g"], _MACRO_TOLERANCE)
#         + _excess(actual_fats, targets["_fat_g"], _MACRO_TOLERANCE)
#     )


# def _process_meals(meals_raw: dict, budgets: dict, required_flags) -> tuple:
#     """Replace whatever the model said about calories/macros with real
#     numbers looked up per item, drop anything that turns out to violate a
#     restriction despite the pre-filtered candidate list, THEN scale each
#     meal's item portions so the real (looked-up) calorie total actually
#     lands close to that meal's budget -- this is the step that keeps the
#     Target Calories/Macros shown at the top of the page in sync with what
#     the Meals section actually adds up to. Without it, the model's guessed
#     gram amounts (e.g. a 200g soup + a 50g roti) can easily undershoot or
#     overshoot the target by a large margin even though every individual
#     number is independently "correct".

#     Returns (meals_final, warnings, daily_actual_calories,
#     daily_actual_protein, daily_actual_carbs, daily_actual_fats) for this
#     one attempt's food selection -- unchanged calorie-scaling logic, just
#     extracted so generate_meal_plan() can run it once per retry attempt.
#     """
#     warnings: list[str] = []
#     mismatched_foods_warned: set[str] = set()  # dedupe across meals -- it's a per-food data issue, not per-meal
#     meals_final = {}
#     for meal_name, meal in meals_raw.items():
#         items = meal.get("Items", []) if isinstance(meal, dict) else []
#         parsed_items: list[dict] = []   # matched foods -- rescalable
#         unverified_items: list[str] = []  # couldn't be matched -- left as-is, not scaled
#         for item in items:
#             if food_database.violates_restrictions(item, required_flags):
#                 warnings.append(f"{meal_name}: removed '{item}' -- conflicts with a stated restriction")
#                 continue
#             nutrition = food_database.nutrition_for_item(item)
#             if nutrition is None:
#                 warnings.append(f"{meal_name}: '{item}' isn't in the food database -- kept but unverified")
#                 unverified_items.append(item)
#                 continue
#             if nutrition["macro_mismatch"] and nutrition["matched_name"] not in mismatched_foods_warned:
#                 mismatched_foods_warned.add(nutrition["matched_name"])
#                 warnings.append(
#                     f"'{nutrition['matched_name']}' -- this food's own calories_per_g in "
#                     f"food_database.csv doesn't add up (via 4/4/9 Atwater) to its "
#                     f"protein/carbs/fat_per_g -- fix the row in the CSV, this isn't a "
#                     f"portion-scaling issue"
#                 )
#             parsed_items.append(nutrition)

#         meal_budget = budgets.get(meal_name)
#         cal_total = sum(n["calories"] for n in parsed_items)

#         # Scale portions (up or down) so this meal's real total lands close
#         # to its budget. Skipped if there's nothing to scale, no budget to
#         # target, or the picked items happen to be ~0 kcal (can't scale a
#         # ratio off of zero).
#         if parsed_items and meal_budget and cal_total > 0:
#             raw_scale = meal_budget / cal_total
#             scale = min(max(raw_scale, _ITEM_SCALE_MIN), _ITEM_SCALE_MAX)
#             if abs(scale - 1.0) > 1e-6:
#                 for n in parsed_items:
#                     target_grams = n["grams"] * scale
#                     new_grams = min(max(target_grams, _ITEM_GRAMS_FLOOR), _ITEM_GRAMS_CEILING)
#                     ratio = (new_grams / n["grams"]) if n["grams"] else 1.0
#                     n["grams"] = round(new_grams, 1)
#                     n["calories"] = round(n["calories"] * ratio, 1)
#                     n["protein_g"] = round(n["protein_g"] * ratio, 1)
#                     n["carbs_g"] = round(n["carbs_g"] * ratio, 1)
#                     n["fat_g"] = round(n["fat_g"] * ratio, 1)
#             cal_total = sum(n["calories"] for n in parsed_items)

#         if meal_budget and cal_total and abs(cal_total - meal_budget) / meal_budget > _MEAL_SYNC_TOLERANCE:
#             direction = "above" if cal_total > meal_budget else "below"
#             warnings.append(
#                 f"{meal_name}: portions were adjusted but the meal is still {direction} its "
#                 f"~{meal_budget} kcal budget ({round(cal_total)} kcal) -- the chosen foods "
#                 f"couldn't be scaled into range without an unrealistic portion size."
#             )

#         kept_items = [f"{n['matched_name']}({n['grams']:g}g)" for n in parsed_items] + unverified_items
#         p_total = sum(n["protein_g"] for n in parsed_items)
#         c_total = sum(n["carbs_g"] for n in parsed_items)
#         f_total = sum(n["fat_g"] for n in parsed_items)

#         meals_final[meal_name] = {
#             "Items": kept_items,
#             "Calories": round(cal_total),
#             "Protein": f"{round(p_total)}g",
#             "Carbs": f"{round(c_total)}g",
#             "Fats": f"{round(f_total)}g",
#         }

#     daily_actual_calories = sum(m["Calories"] for m in meals_final.values())
#     daily_actual_protein = sum(float(m["Protein"].rstrip("g") or 0) for m in meals_final.values())
#     daily_actual_carbs = sum(float(m["Carbs"].rstrip("g") or 0) for m in meals_final.values())
#     daily_actual_fats = sum(float(m["Fats"].rstrip("g") or 0) for m in meals_final.values())

#     return (meals_final, warnings, daily_actual_calories, daily_actual_protein,
#             daily_actual_carbs, daily_actual_fats)


# def generate_meal_plan(user_data: dict, max_attempts: int = 3) -> dict:
#     """Generates a meal plan where the LLM only chooses which foods go in
#     each meal -- every Calories/Protein/Carbs/Fats number in the returned
#     plan (daily and per-meal) comes from nutrition/calculator.py and
#     nutrition/food_database.py, not from the model. After the model picks
#     items, their portions are scaled (see the sync pass below) so the real,
#     looked-up meal totals actually land close to the deterministic
#     Target Calories/Macros -- not just each individually "correct" but
#     collectively mismatched with the target. This means the numbers are
#     internally consistent AND synchronized with the target for every
#     request, not just when the model's own guessed portions happen to add
#     up right.

#     The prompt also states daily and per-meal Protein/Carbs/Fat targets (not
#     just calories), so the model's food selection is macro-aware. After
#     scaling, the resulting daily actual totals are checked against the
#     calculator's targets (calories +-5%, each macro +-10%); if they're
#     outside tolerance, the model is asked to pick different foods and the
#     whole selection+scaling pass runs again, up to max_attempts times. The
#     closest attempt seen is kept even if none lands fully inside tolerance.

#     Required user_data keys: age, gender, weight, height, goal,
#     activity_level, diet, food_restrictions.
#     Optional key: body_build -- one of nutrition.body_build.BODY_BUILD_OPTIONS
#     (the user-friendly name, e.g. "Lean / Slim Build"), or None/absent for
#     users who skipped this optional assessment field.
#     """
#     body_build = user_data.get("body_build") or None
#     if not body_build_module.is_valid_body_build(body_build):
#         # Unrecognized value (e.g. stale/corrupt data) -- fail safe by
#         # treating it as "not provided" rather than erroring the whole plan.
#         body_build = None

#     # 1. Deterministic daily targets -- never asked of the LLM. Body Build
#     #    (if any) is applied here exactly once, as a secondary adjustment
#     #    on top of the primary BMR/TDEE/Goal calculation.
#     targets = calculator.calculate_targets(
#         weight_kg=float(user_data["weight"]),
#         height_cm=float(user_data["height"]),
#         age=int(user_data["age"]),
#         gender=user_data.get("gender", ""),
#         activity_level=user_data.get("activity_level", ""),
#         goal=user_data.get("goal", ""),
#         body_build=body_build,
#     )
#     budgets = calculator.meal_calorie_budgets(targets["TargetCalories"])
#     macro_budgets = _meal_macro_budgets(targets["_protein_g"], targets["_carb_g"], targets["_fat_g"])

#     # 2. Filter the food database down to what's safe for this user (allergy/
#     #    diet restrictions -- unaffected by Body Build), then re-order the
#     #    remaining safe candidates so foods relevant to this Body Build lead
#     #    the list the model sees.
#     required_flags = food_database.diet_preference_flags(user_data.get("diet", ""))
#     required_flags |= food_database.parse_restrictions_text(user_data.get("food_restrictions", ""))
#     candidates = food_database.candidate_foods(required_flags, body_build=body_build)

#     rules = body_build_module.get_rules(body_build)
#     if rules:
#         body_build_guidance = (
#             f"Body Build personalization ({body_build} -> internally "
#             f"'{body_build_module.get_internal_type(body_build)}', a heuristic "
#             f"classification, not a diagnosis): {rules['food_selection_strategy']}\n"
#         )
#     else:
#         body_build_guidance = ""

#     prompt = DIET_PROMPT.format(
#         age=user_data["age"],
#         gender=user_data.get("gender", ""),
#         weight=user_data["weight"],
#         height=user_data["height"],
#         goal=user_data.get("goal", ""),
#         activity_level=user_data.get("activity_level", ""),
#         diet=user_data.get("diet", ""),
#         body_build=body_build or "Not specified",
#         food_restrictions=user_data.get("food_restrictions", "None"),
#         target_calories=targets["TargetCalories"],
#         protein_g=targets["_protein_g"],
#         carb_g=targets["_carb_g"],
#         fat_g=targets["_fat_g"],
#         breakfast_kcal=budgets["Breakfast"],
#         lunch_kcal=budgets["Lunch"],
#         snack_kcal=budgets["EveningSnack"],
#         dinner_kcal=budgets["Dinner"],
#         body_build_guidance=body_build_guidance,
#         candidate_foods=", ".join(candidates) if candidates else "(none available -- see warning)",
#     )
#     # Daily and per-meal Protein/Carbs/Fat targets -- appended rather than
#     # added as a new DIET_PROMPT placeholder, so utils/prompts.py doesn't
#     # need to change. This is what makes food selection macro-aware instead
#     # of only calorie-aware.
#     prompt += "\n" + _macro_guidance_block(targets, budgets, macro_budgets)

#     base_warnings: list[str] = []
#     if not candidates:
#         base_warnings.append(
#             "No foods in the database matched this user's Diet Preference / Food "
#             "Restrictions combination, so the model had no safe candidate list to "
#             "choose from -- treat any items below as unverified."
#         )

#     # 3. Generate -> process/scale -> validate against the calculator's
#     #    daily targets, retrying with a fresh food selection (same prompt,
#     #    the model can pick differently each call) if the result lands
#     #    outside tolerance. Keeps whichever attempt gets closest even if
#     #    none lands fully inside tolerance, rather than discarding work.
#     best = None  # (gap, meals_final, meal_warnings, cal, protein, carbs, fats)
#     attempts = max(1, max_attempts)
#     for _ in range(attempts):
#         text = _generate(prompt)
#         response = parse_json_response(text)
#         meals_raw = response.get("Meals", {})
#         # Skip (and retry, if attempts remain) if the model ignored the
#         # instruction and returned nothing usable.
#         if not any(isinstance(m, dict) and m.get("Items") for m in meals_raw.values()):
#             continue

#         (meals_final, meal_warnings, daily_actual_calories, daily_actual_protein,
#          daily_actual_carbs, daily_actual_fats) = _process_meals(meals_raw, budgets, required_flags)

#         gap = _tolerance_gap(daily_actual_calories, daily_actual_protein,
#                               daily_actual_carbs, daily_actual_fats, targets)

#         if best is None or gap < best[0]:
#             best = (gap, meals_final, meal_warnings, daily_actual_calories,
#                      daily_actual_protein, daily_actual_carbs, daily_actual_fats)

#         if gap <= 0:
#             break  # within tolerance on calories and every macro -- no need to retry

#     if best is None:
#         # Every attempt returned nothing usable.
#         meals_final, meal_warnings = {}, []
#         daily_actual_calories = daily_actual_protein = daily_actual_carbs = daily_actual_fats = 0.0
#     else:
#         (_, meals_final, meal_warnings, daily_actual_calories, daily_actual_protein,
#          daily_actual_carbs, daily_actual_fats) = best

#     warnings = base_warnings + meal_warnings

#     # 4. Daily actual totals -- the real sum of what's in the Meals section
#     #    above, computed the same way (from food_database.csv), so the UI
#     #    can show it next to Target Calories/Macros and the two numbers are
#     #    always describing the same thing. If they still don't match closely
#     #    after every retry attempt, that's surfaced as a warning rather than
#     #    silently left inconsistent.
#     target_calories = targets["TargetCalories"]
#     if target_calories and abs(daily_actual_calories - target_calories) / target_calories > _CALORIE_TOLERANCE:
#         direction = "above" if daily_actual_calories > target_calories else "below"
#         warnings.append(
#             f"Daily total ({round(daily_actual_calories)} kcal) is still {direction} the "
#             f"{target_calories} kcal Target Calories after {attempts} generation attempt(s) -- "
#             f"see the per-meal notes above for which meal(s) couldn't be scaled into range."
#         )

#     for label, actual, target_key in (
#         ("Protein", daily_actual_protein, "_protein_g"),
#         ("Carbs", daily_actual_carbs, "_carb_g"),
#         ("Fats", daily_actual_fats, "_fat_g"),
#     ):
#         target_val = targets[target_key]
#         if target_val and abs(actual - target_val) / target_val > _MACRO_TOLERANCE:
#             direction = "above" if actual > target_val else "below"
#             warnings.append(
#                 f"Daily {label} ({round(actual)}g) is still {direction} the {target_val}g target "
#                 f"by more than {int(_MACRO_TOLERANCE * 100)}% after {attempts} generation attempt(s)."
#             )

#     plan = {
#         "MaintenanceCalories": targets["MaintenanceCalories"],
#         "TargetCalories": targets["TargetCalories"],
#         "DailyMacros": targets["DailyMacros"],
#         "BodyBuild": body_build,
#         "Meals": meals_final,
#         "DailyActualCalories": round(daily_actual_calories),
#         "DailyActualMacros": {
#             "Protein": f"{round(daily_actual_protein)}g",
#             "Carbs": f"{round(daily_actual_carbs)}g",
#             "Fats": f"{round(daily_actual_fats)}g",
#         },
#     }
#     if warnings:
#         plan["_nutrition_warnings"] = warnings
#     return plan


# def fitness_chat(user_id, message, chat_history):
#     client = configure_groq()

#     # ChatHistory.role in this project is stored as 'user' or 'model'
#     # (see database/models.py) -- 'model' was Gemini's assistant-role name,
#     # so it's mapped to Groq/OpenAI-style 'assistant' here. New rows written
#     # going forward will still say 'model' unless you also update wherever
#     # ChatHistory rows get created; either is handled by this mapping.
#     formatted_history = [{"role": "system", "content": CHAT_PROMPT}]
#     for msg in chat_history:
#         role = "assistant" if msg.role in ("model", "assistant") else "user"
#         formatted_history.append({"role": role, "content": msg.message})

#     formatted_history.append({"role": "user", "content": message})

#     response = client.chat.completions.create(
#         model=GROQ_MODEL,
#         messages=formatted_history,
#         reasoning_effort="low",
#         max_completion_tokens=4096,
#     )
#     content = response.choices[0].message.content
#     if not content:
#         content = getattr(response.choices[0].message, "reasoning", "") or ""
#     return content


# def generate_weekly_insights(progress_data: str) -> dict:
#     prompt = INSIGHTS_PROMPT.format(progress_data=progress_data)
#     text = _generate(prompt)
#     return parse_json_response(text)


import os
import json
import re
from groq import Groq
from utils.prompts import WORKOUT_PROMPT, DIET_PROMPT, CHAT_PROMPT, INSIGHTS_PROMPT
from nutrition import calculator, food_database, body_build as body_build_module

GROQ_MODEL = os.getenv("GROQ_MODEL", "")

# --- Portion-sync tuning (see the scaling pass in generate_meal_plan()) ---
# After the model picks items, each meal's *real* calorie total (looked up
# from food_database.csv) is compared to that meal's calorie budget and the
# item portions are scaled to close the gap -- this is what keeps the
# top-level Target Calories/Macros in sync with what the meals actually add
# up to, instead of just hoping the model's guessed grams land close.
_MEAL_SYNC_TOLERANCE = 0.10   # meals within +-10% of budget after scaling are left alone
_ITEM_SCALE_MIN = 0.4         # never shrink an item below 40% of what the model picked
_ITEM_SCALE_MAX = 2.5         # never grow an item beyond 250% of what the model picked
_ITEM_GRAMS_FLOOR = 10.0      # never round an item down to an unrealistically tiny amount
_ITEM_GRAMS_CEILING = 800.0   # never scale an item up to an unrealistically huge amount

# --- Daily-total validation tolerance (see the retry loop in
# generate_meal_plan()) -- separate from _MEAL_SYNC_TOLERANCE above, which
# only governs the per-meal portion-scaling pass. These govern whether a
# whole attempt (after scaling) is accepted as close enough to the
# calculator's targets, or the model gets asked to pick different foods and
# try again.
_CALORIE_TOLERANCE = 0.05     # daily actual calories must land within +-5% of TargetCalories
_MACRO_TOLERANCE = 0.10       # each daily actual macro (protein/carbs/fat) within +-10% of target


def configure_groq() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError("GROQ_API_KEY not found or invalid in .env")

    return Groq(api_key=api_key)


def parse_json_response(response_text):
    text = (response_text or "").strip()

    # Strip a leading code fence of any form: ``` , ```json , ```JSON , etc.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: the model may have added stray text around the JSON object
    # (e.g. "Sure, here's your plan:\n{...}"). Grab the outermost {...} block.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Groq response as JSON: {e}\nRaw Response: {response_text}")

    raise ValueError(f"Failed to parse Groq response as JSON: no JSON object found.\nRaw Response: {response_text}")


def _generate(prompt: str) -> str:
    client = configure_groq()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        reasoning_effort="low",
        max_completion_tokens=2048,
    )
    content = response.choices[0].message.content
    if not content:
        # Reasoning models (e.g. openai/gpt-oss-120b) can occasionally put
        # the final answer in the "reasoning" field instead of "content" --
        # fall back to that rather than returning an empty string.
        content = getattr(response.choices[0].message, "reasoning", "") or ""
    return content


def generate_workout_plan(user_data: dict) -> dict:
    prompt = WORKOUT_PROMPT.format(**user_data)
    text = _generate(prompt)
    return parse_json_response(text)


def _meal_macro_budgets(protein_g: float, carb_g: float, fat_g: float) -> dict:
    """Per-meal Protein/Carbs/Fat targets (grams), split using the same
    percentages calculator.py's MEAL_SPLIT already uses for the per-meal
    calorie budgets -- keeps calories and macros proportionally consistent
    across meals without adding any new logic to calculator.py itself."""
    return {
        meal: {
            "protein_g": round(protein_g * pct),
            "carb_g": round(carb_g * pct),
            "fat_g": round(fat_g * pct),
        }
        for meal, pct in calculator.MEAL_SPLIT.items()
    }


def _macro_guidance_block(targets: dict, budgets: dict, macro_budgets: dict) -> str:
    """Extra prompt text listing daily and per-meal Protein/Carbs/Fat
    targets. Appended after DIET_PROMPT.format(...) rather than added as a
    new template placeholder, so utils/prompts.py doesn't need to change --
    this makes food selection macro-aware, not only calorie-aware."""
    lines = [
        "",
        "Additional macro targets (grams) -- choose foods so each meal's "
        "Protein/Carbs/Fat land close to these too, not just its calories:",
        f"- Daily: Protein {targets['_protein_g']}g | Carbs {targets['_carb_g']}g | "
        f"Fat {targets['_fat_g']}g",
    ]
    for meal_name, mb in macro_budgets.items():
        cal = budgets.get(meal_name, "-")
        lines.append(
            f"- {meal_name} (~{cal} kcal): Protein {mb['protein_g']}g | "
            f"Carbs {mb['carb_g']}g | Fat {mb['fat_g']}g"
        )
    return "\n".join(lines)


def _tolerance_gap(actual_calories: float, actual_protein: float, actual_carbs: float,
                    actual_fats: float, targets: dict) -> float:
    """0.0 if the daily actual totals are within tolerance of the
    calculator's targets on every axis (calories +-5%, each macro +-10%);
    otherwise a positive score (larger = further off), used only to pick the
    closest-of-several attempts when none lands fully inside tolerance."""

    def _excess(actual: float, target: float, tolerance: float) -> float:
        if not target:
            return 0.0
        return max(abs(actual - target) / target - tolerance, 0.0)

    return (
        _excess(actual_calories, targets["TargetCalories"], _CALORIE_TOLERANCE)
        + _excess(actual_protein, targets["_protein_g"], _MACRO_TOLERANCE)
        + _excess(actual_carbs, targets["_carb_g"], _MACRO_TOLERANCE)
        + _excess(actual_fats, targets["_fat_g"], _MACRO_TOLERANCE)
    )


def _process_meals(meals_raw: dict, budgets: dict, required_flags) -> tuple:
    """Replace whatever the model said about calories/macros with real
    numbers looked up per item, drop anything that turns out to violate a
    restriction despite the pre-filtered candidate list, THEN scale each
    meal's item portions so the real (looked-up) calorie total actually
    lands close to that meal's budget -- this is the step that keeps the
    Target Calories/Macros shown at the top of the page in sync with what
    the Meals section actually adds up to. Without it, the model's guessed
    gram amounts (e.g. a 200g soup + a 50g roti) can easily undershoot or
    overshoot the target by a large margin even though every individual
    number is independently "correct".

    Returns (meals_final, warnings, daily_actual_calories,
    daily_actual_protein, daily_actual_carbs, daily_actual_fats) for this
    one attempt's food selection -- unchanged calorie-scaling logic, just
    extracted so generate_meal_plan() can run it once per retry attempt.
    """
    warnings: list[str] = []
    mismatched_foods_warned: set[str] = set()  # dedupe across meals -- it's a per-food data issue, not per-meal
    meals_final = {}
    for meal_name, meal in meals_raw.items():
        items = meal.get("Items", []) if isinstance(meal, dict) else []
        parsed_items: list[dict] = []   # matched foods -- rescalable
        unverified_items: list[str] = []  # couldn't be matched -- left as-is, not scaled
        for item in items:
            if food_database.violates_restrictions(item, required_flags):
                warnings.append(f"{meal_name}: removed '{item}' -- conflicts with a stated restriction")
                continue
            nutrition = food_database.nutrition_for_item(item)
            if nutrition is None:
                warnings.append(f"{meal_name}: '{item}' isn't in the food database -- kept but unverified")
                unverified_items.append(item)
                continue
            if nutrition["macro_mismatch"] and nutrition["matched_name"] not in mismatched_foods_warned:
                mismatched_foods_warned.add(nutrition["matched_name"])
                warnings.append(
                    f"'{nutrition['matched_name']}' -- this food's own calories_per_g in "
                    f"food_database.csv doesn't add up (via 4/4/9 Atwater) to its "
                    f"protein/carbs/fat_per_g -- fix the row in the CSV, this isn't a "
                    f"portion-scaling issue"
                )
            parsed_items.append(nutrition)

        meal_budget = budgets.get(meal_name)
        cal_total = sum(n["calories"] for n in parsed_items)

        # Scale portions (up or down) so this meal's real total lands close
        # to its budget. Skipped if there's nothing to scale, no budget to
        # target, or the picked items happen to be ~0 kcal (can't scale a
        # ratio off of zero).
        if parsed_items and meal_budget and cal_total > 0:
            raw_scale = meal_budget / cal_total
            scale = min(max(raw_scale, _ITEM_SCALE_MIN), _ITEM_SCALE_MAX)
            if abs(scale - 1.0) > 1e-6:
                for n in parsed_items:
                    target_grams = n["grams"] * scale
                    new_grams = min(max(target_grams, _ITEM_GRAMS_FLOOR), _ITEM_GRAMS_CEILING)
                    ratio = (new_grams / n["grams"]) if n["grams"] else 1.0
                    n["grams"] = round(new_grams, 1)
                    n["calories"] = round(n["calories"] * ratio, 1)
                    n["protein_g"] = round(n["protein_g"] * ratio, 1)
                    n["carbs_g"] = round(n["carbs_g"] * ratio, 1)
                    n["fat_g"] = round(n["fat_g"] * ratio, 1)
            cal_total = sum(n["calories"] for n in parsed_items)

        if meal_budget and cal_total and abs(cal_total - meal_budget) / meal_budget > _MEAL_SYNC_TOLERANCE:
            direction = "above" if cal_total > meal_budget else "below"
            warnings.append(
                f"{meal_name}: portions were adjusted but the meal is still {direction} its "
                f"~{meal_budget} kcal budget ({round(cal_total)} kcal) -- the chosen foods "
                f"couldn't be scaled into range without an unrealistic portion size."
            )

        kept_items = [f"{n['matched_name']}({n['grams']:g}g)" for n in parsed_items] + unverified_items
        p_total = sum(n["protein_g"] for n in parsed_items)
        c_total = sum(n["carbs_g"] for n in parsed_items)
        f_total = sum(n["fat_g"] for n in parsed_items)

        meals_final[meal_name] = {
            "Items": kept_items,
            "Calories": round(cal_total),
            "Protein": f"{round(p_total)}g",
            "Carbs": f"{round(c_total)}g",
            "Fats": f"{round(f_total)}g",
        }

    daily_actual_calories = sum(m["Calories"] for m in meals_final.values())
    daily_actual_protein = sum(float(m["Protein"].rstrip("g") or 0) for m in meals_final.values())
    daily_actual_carbs = sum(float(m["Carbs"].rstrip("g") or 0) for m in meals_final.values())
    daily_actual_fats = sum(float(m["Fats"].rstrip("g") or 0) for m in meals_final.values())

    return (meals_final, warnings, daily_actual_calories, daily_actual_protein,
            daily_actual_carbs, daily_actual_fats)


def generate_meal_plan(user_data: dict, max_attempts: int = 2) -> dict:
    """Generates a meal plan where the LLM only chooses which foods go in
    each meal -- every Calories/Protein/Carbs/Fats number in the returned
    plan (daily and per-meal) comes from nutrition/calculator.py and
    nutrition/food_database.py, not from the model. After the model picks
    items, their portions are scaled (see the sync pass below) so the real,
    looked-up meal totals actually land close to the deterministic
    Target Calories/Macros -- not just each individually "correct" but
    collectively mismatched with the target. This means the numbers are
    internally consistent AND synchronized with the target for every
    request, not just when the model's own guessed portions happen to add
    up right.

    The prompt also states daily and per-meal Protein/Carbs/Fat targets (not
    just calories), so the model's food selection is macro-aware. After
    scaling, the resulting daily actual totals are checked against the
    calculator's targets (calories +-5%, each macro +-10%); if they're
    outside tolerance, the model is asked to pick different foods and the
    whole selection+scaling pass runs again, up to max_attempts times. The
    closest attempt seen is kept even if none lands fully inside tolerance.

    Required user_data keys: age, gender, weight, height, goal,
    activity_level, diet, food_restrictions.
    Optional key: body_build -- one of nutrition.body_build.BODY_BUILD_OPTIONS
    (the user-friendly name, e.g. "Lean / Slim Build"), or None/absent for
    users who skipped this optional assessment field.
    """
    body_build = user_data.get("body_build") or None
    if not body_build_module.is_valid_body_build(body_build):
        # Unrecognized value (e.g. stale/corrupt data) -- fail safe by
        # treating it as "not provided" rather than erroring the whole plan.
        body_build = None

    # 1. Deterministic daily targets -- never asked of the LLM. Body Build
    #    (if any) is applied here exactly once, as a secondary adjustment
    #    on top of the primary BMR/TDEE/Goal calculation.
    targets = calculator.calculate_targets(
        weight_kg=float(user_data["weight"]),
        height_cm=float(user_data["height"]),
        age=int(user_data["age"]),
        gender=user_data.get("gender", ""),
        activity_level=user_data.get("activity_level", ""),
        goal=user_data.get("goal", ""),
        body_build=body_build,
    )
    budgets = calculator.meal_calorie_budgets(targets["TargetCalories"])
    macro_budgets = _meal_macro_budgets(targets["_protein_g"], targets["_carb_g"], targets["_fat_g"])

    # 2. Filter the food database down to what's safe for this user (allergy/
    #    diet restrictions -- unaffected by Body Build), then re-order the
    #    remaining safe candidates so foods relevant to this Body Build lead
    #    the list the model sees.
    required_flags = food_database.diet_preference_flags(user_data.get("diet", ""))
    required_flags |= food_database.parse_restrictions_text(user_data.get("food_restrictions", ""))
    candidates = food_database.candidate_foods(required_flags, body_build=body_build)

    rules = body_build_module.get_rules(body_build)
    if rules:
        body_build_guidance = (
            f"Body Build personalization ({body_build} -> internally "
            f"'{body_build_module.get_internal_type(body_build)}', a heuristic "
            f"classification, not a diagnosis): {rules['food_selection_strategy']}\n"
        )
    else:
        body_build_guidance = ""

    prompt = DIET_PROMPT.format(
        age=user_data["age"],
        gender=user_data.get("gender", ""),
        weight=user_data["weight"],
        height=user_data["height"],
        goal=user_data.get("goal", ""),
        activity_level=user_data.get("activity_level", ""),
        diet=user_data.get("diet", ""),
        body_build=body_build or "Not specified",
        food_restrictions=user_data.get("food_restrictions", "None"),
        target_calories=targets["TargetCalories"],
        protein_g=targets["_protein_g"],
        carb_g=targets["_carb_g"],
        fat_g=targets["_fat_g"],
        breakfast_kcal=budgets["Breakfast"],
        lunch_kcal=budgets["Lunch"],
        snack_kcal=budgets["EveningSnack"],
        dinner_kcal=budgets["Dinner"],
        body_build_guidance=body_build_guidance,
        candidate_foods=", ".join(candidates) if candidates else "(none available -- see warning)",
    )
    # Daily and per-meal Protein/Carbs/Fat targets -- appended rather than
    # added as a new DIET_PROMPT placeholder, so utils/prompts.py doesn't
    # need to change. This is what makes food selection macro-aware instead
    # of only calorie-aware.
    prompt += "\n" + _macro_guidance_block(targets, budgets, macro_budgets)

    base_warnings: list[str] = []
    if not candidates:
        base_warnings.append(
            "No foods in the database matched this user's Diet Preference / Food "
            "Restrictions combination, so the model had no safe candidate list to "
            "choose from -- treat any items below as unverified."
        )

    # 3. Generate -> process/scale -> validate against the calculator's
    #    daily targets, retrying with a fresh food selection (same prompt,
    #    the model can pick differently each call) if the result lands
    #    outside tolerance. Keeps whichever attempt gets closest even if
    #    none lands fully inside tolerance, rather than discarding work.
    best = None  # (gap, meals_final, meal_warnings, cal, protein, carbs, fats)
    attempts = max(1, max_attempts)
    for _ in range(attempts):
        text = _generate(prompt)
        response = parse_json_response(text)
        meals_raw = response.get("Meals", {})
        # Skip (and retry, if attempts remain) if the model ignored the
        # instruction and returned nothing usable.
        if not any(isinstance(m, dict) and m.get("Items") for m in meals_raw.values()):
            continue

        (meals_final, meal_warnings, daily_actual_calories, daily_actual_protein,
         daily_actual_carbs, daily_actual_fats) = _process_meals(meals_raw, budgets, required_flags)

        gap = _tolerance_gap(daily_actual_calories, daily_actual_protein,
                              daily_actual_carbs, daily_actual_fats, targets)

        if best is None or gap < best[0]:
            best = (gap, meals_final, meal_warnings, daily_actual_calories,
                     daily_actual_protein, daily_actual_carbs, daily_actual_fats)

        if gap <= 0:
            break  # within tolerance on calories and every macro -- no need to retry

    if best is None:
        # Every attempt returned nothing usable.
        meals_final, meal_warnings = {}, []
        daily_actual_calories = daily_actual_protein = daily_actual_carbs = daily_actual_fats = 0.0
    else:
        (_, meals_final, meal_warnings, daily_actual_calories, daily_actual_protein,
         daily_actual_carbs, daily_actual_fats) = best

    warnings = base_warnings + meal_warnings

    # 4. Daily actual totals -- the real sum of what's in the Meals section
    #    above, computed the same way (from food_database.csv), so the UI
    #    can show it next to Target Calories/Macros and the two numbers are
    #    always describing the same thing. If they still don't match closely
    #    after every retry attempt, that's surfaced as a warning rather than
    #    silently left inconsistent.
    target_calories = targets["TargetCalories"]
    if target_calories and abs(daily_actual_calories - target_calories) / target_calories > _CALORIE_TOLERANCE:
        direction = "above" if daily_actual_calories > target_calories else "below"
        warnings.append(
            f"Daily total ({round(daily_actual_calories)} kcal) is still {direction} the "
            f"{target_calories} kcal Target Calories after {attempts} generation attempt(s) -- "
            f"see the per-meal notes above for which meal(s) couldn't be scaled into range."
        )

    for label, actual, target_key in (
        ("Protein", daily_actual_protein, "_protein_g"),
        ("Carbs", daily_actual_carbs, "_carb_g"),
        ("Fats", daily_actual_fats, "_fat_g"),
    ):
        target_val = targets[target_key]
        if target_val and abs(actual - target_val) / target_val > _MACRO_TOLERANCE:
            direction = "above" if actual > target_val else "below"
            warnings.append(
                f"Daily {label} ({round(actual)}g) is still {direction} the {target_val}g target "
                f"by more than {int(_MACRO_TOLERANCE * 100)}% after {attempts} generation attempt(s)."
            )

    plan = {
        "MaintenanceCalories": targets["MaintenanceCalories"],
        "TargetCalories": targets["TargetCalories"],
        "DailyMacros": targets["DailyMacros"],
        "BodyBuild": body_build,
        "Meals": meals_final,
        "DailyActualCalories": round(daily_actual_calories),
        "DailyActualMacros": {
            "Protein": f"{round(daily_actual_protein)}g",
            "Carbs": f"{round(daily_actual_carbs)}g",
            "Fats": f"{round(daily_actual_fats)}g",
        },
    }
    if warnings:
        plan["_nutrition_warnings"] = warnings
    return plan


def fitness_chat(user_id, message, chat_history):
    client = configure_groq()

    # ChatHistory.role in this project is stored as 'user' or 'model'
    # (see database/models.py) -- 'model' was Gemini's assistant-role name,
    # so it's mapped to Groq/OpenAI-style 'assistant' here. New rows written
    # going forward will still say 'model' unless you also update wherever
    # ChatHistory rows get created; either is handled by this mapping.
    formatted_history = [{"role": "system", "content": CHAT_PROMPT}]
    for msg in chat_history:
        role = "assistant" if msg.role in ("model", "assistant") else "user"
        formatted_history.append({"role": role, "content": msg.message})

    formatted_history.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=formatted_history,
        reasoning_effort="low",
        max_completion_tokens=4096,
    )
    content = response.choices[0].message.content
    if not content:
        content = getattr(response.choices[0].message, "reasoning", "") or ""
    return content


def generate_weekly_insights(progress_data: str) -> dict:
    prompt = INSIGHTS_PROMPT.format(progress_data=progress_data)
    text = _generate(prompt)
    return parse_json_response(text)