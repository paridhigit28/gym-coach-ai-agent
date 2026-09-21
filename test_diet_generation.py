"""
Standalone test -- calls generate_meal_plan() directly, completely outside
Streamlit, to prove whether the patched services/groq_service.py is
actually the file being used.

Why this matters: Streamlit caches imported modules in the running
process, so editing groq_service.py on disk does NOT change what a
still-running `streamlit run` process uses -- you must fully stop and
restart it. This script sidesteps that entirely by importing fresh in a
brand new Python process.

Usage (from the project root, with your venv active):
    python test_diet_generation.py

If this script raises the raw
    "Error code: 400 - {'error': {'message': 'Failed to validate JSON...'"
then the fix genuinely isn't working yet and we need to dig further.

If instead you see either a successful plan printed, OR a message that
starts with "Groq failed to return a valid response on all" / "Couldn't
reach Groq's API on all", then the patched file IS active and working as
designed (it's turning the raw crash into a handled, retried outcome) --
and any leftover raw-error report from the Streamlit app itself means the
Streamlit process still needs a full restart (see step 4).
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

print("0. Sanity check: which groq_service.py is actually being imported?")
import services.groq_service as groq_service
print("   ->", groq_service.__file__)
print("   Open that exact file and confirm it contains 'include_reasoning'")
print("   and 'max_completion_tokens' (search for those two strings).")
print("   If it does NOT, this is the wrong/old file and needs replacing.\n")

print("1. Calling generate_meal_plan() with a sample user profile...")
sample_user_data = {
    "age": 28,
    "gender": "Male",
    "weight": 75,
    "height": 175,
    "goal": "Muscle Gain",
    "activity_level": "Moderately Active",
    "diet": "Vegetarian",
    "body_build": None,
    "food_restrictions": "None",
}

try:
    plan = groq_service.generate_meal_plan(sample_user_data)
    print("\n   SUCCESS -- plan generated:")
    print("   TargetCalories:", plan.get("TargetCalories"))
    print("   DailyActualCalories:", plan.get("DailyActualCalories"))
    print("   Meals:", list(plan.get("Meals", {}).keys()))
    warnings = plan.get("_nutrition_warnings", [])
    if warnings:
        print("\n   Warnings surfaced (this is normal/handled, not a crash):")
        for w in warnings:
            print("    -", w)
except Exception as e:
    print(f"\n   RAISED (unhandled): {type(e).__name__}: {e}")
    print("   -> If this is the raw 'Error code: 400 - {...json_validate_failed...}'")
    print("      text, the fix isn't active in this file -- re-check step 0 above.")
    sys.exit(1)
