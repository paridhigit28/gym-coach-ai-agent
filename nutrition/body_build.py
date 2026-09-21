"""
Body Build personalization -- single source of truth.

The user only ever sees the plain-language names on the left. The
traditional somatotype terms on the right are an internal/developer
classification and are never required from, or necessarily shown to,
the user.

    Lean / Slim Build           -> Ectomorph
    Athletic / Muscular Build   -> Mesomorph
    Broad / Higher Body-Fat Build -> Endomorph

IMPORTANT: Ectomorph/Mesomorph/Endomorph are NOT a scientifically
validated way to predict metabolism -- see the module docstring in
nutrition/calculator.py. Body Build is treated everywhere in this app
as an OPTIONAL, secondary personalization heuristic layered on top of
the real BMR/TDEE/activity/goal calculation, never a replacement for it.

Every other file that needs the mapping or the per-build nutrition
rules should import from here rather than redefining them.
"""

from __future__ import annotations

import functools
import os

import pandas as pd

# The only three user-facing options. UI code should build its
# selectbox/radio from this list rather than hard-coding the strings.
BODY_BUILD_OPTIONS = [
    "Lean / Slim Build",
    "Athletic / Muscular Build",
    "Broad / Higher Body-Fat Build",
]

# Centralized mapping -- do not duplicate this dict anywhere else.
BODY_BUILD_MAPPING = {
    "Lean / Slim Build": "Ectomorph",
    "Athletic / Muscular Build": "Mesomorph",
    "Broad / Higher Body-Fat Build": "Endomorph",
}

_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "body_build_nutrition.csv")


def is_valid_body_build(value: str | None) -> bool:
    """True for one of the 3 user-facing options, OR None/'' (Body Build
    is optional, so "not provided" is also valid)."""
    if value is None or str(value).strip() == "":
        return True
    return value in BODY_BUILD_MAPPING


def get_internal_type(display_name: str | None) -> str | None:
    """'Lean / Slim Build' -> 'Ectomorph'. Returns None for missing/unknown
    input instead of raising, so callers never need a try/except just to
    handle a user who skipped this optional field."""
    if not display_name:
        return None
    return BODY_BUILD_MAPPING.get(display_name)


@functools.lru_cache(maxsize=1)
def _load_rules() -> pd.DataFrame:
    df = pd.read_csv(_CSV_PATH)
    df["calorie_adjustment"] = df["calorie_adjustment"].astype(int)
    return df.set_index("body_build")


def get_rules(display_name: str | None) -> dict | None:
    """Returns the full row of personalization rules for a Body Build
    (calorie_adjustment, protein/carb/fat/fiber priority, food_selection_strategy)
    or None if display_name is missing/unrecognized."""
    if not display_name:
        return None
    df = _load_rules()
    if display_name not in df.index:
        return None
    return df.loc[display_name].to_dict()


def get_calorie_adjustment(display_name: str | None) -> int:
    """Small, conservative kcal nudge for this build. 0 if Body Build
    wasn't provided -- an unset optional field must never change the
    calorie target."""
    rules = get_rules(display_name)
    return int(rules["calorie_adjustment"]) if rules else 0
