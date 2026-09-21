"""
Resolves a demo image for an exercise name coming out of the AI workout
agent (services/groq_service.generate_workout_plan).

The agent invents exercise names freely (it isn't limited to a fixed
list), so there's no static "name -> image" table we can rely on being
complete. Four layers, best/most-reliable real-photo source first:

0. A bundled copy of the free-exercise-db dataset (MIT licensed, no key,
   no network call needed to *match* -- the ~900-name index ships in
   data/free_exercise_db.json). Only the matched exercise's actual photo
   is fetched, and it's fetched by the *browser* (via a plain
   raw.githubusercontent.com <img src> URL), not by this server, so it
   isn't affected by outbound-network restrictions on wherever this app
   is deployed. This is the primary source -- it needs no API key and
   doesn't depend on a 3rd-party subscription staying alive.
1. ExerciseDB (via RapidAPI) -- real human demo photos/GIFs, if you have
   a *working, subscribed* RapidAPI key in RAPIDAPI_KEY (see .env). Note
   this API has increasingly moved behind paid plans, so a key alone
   doesn't guarantee results -- see the troubleshooting note below
   get_exercise_image(). Tries the exercise name as-is, then a
   "simplified" version (equipment/stance qualifiers like "Barbell",
   "Unilateral", "Behind-the-Neck" stripped off).
2. wger.de's free, open exercise database -- no key needed, used when
   ExerciseDB has no key configured or no match.
3. A small set of hand-drawn category icons (chest/back/legs/shoulders/
   arms/core/cardio/default), picked by keyword-matching the exercise
   name. Always works offline, carries no licensing risk -- the final
   fallback so the UI never shows a broken image.

Every network call is short-timeout + cached per process, so a given
exercise name only ever triggers one lookup regardless of how many
times/pages it's rendered on.

Set EXERCISE_IMAGE_DEBUG=1 in the environment to print (to stdout/logs)
which layer resolved each exercise name -- handy for seeing exactly why
something fell all the way through to the icon fallback.

Callers just need get_exercise_image(name) -> str (a src usable directly
in an <img> tag: either a remote https URL or a data: URI).
"""

from __future__ import annotations

import base64
import functools
import json
import os
import re
from urllib.parse import quote

import requests

_DEBUG = (os.getenv("EXERCISE_IMAGE_DEBUG") or "").strip() == "1"


def _debug(name: str, layer: str) -> None:
    if _DEBUG:
        print(f"[exercise_images] '{name}' -> {layer}")


_WGER_SEARCH_URL = "https://wger.de/api/v2/exercise/search/"
_WGER_TIMEOUT = 3.5  # seconds -- page must never hang waiting on a 3rd party

_EXERCISEDB_HOST = "exercisedb.p.rapidapi.com"
_EXERCISEDB_BASE = f"https://{_EXERCISEDB_HOST}"
_EXERCISEDB_TIMEOUT = 4.0

_FREE_DB_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "free_exercise_db.json")
_FREE_DB_IMAGE_BASE = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises"
_FREE_DB_MATCH_CUTOFF = 0.3  # min token-overlap score (0-1) to accept a match

# Qualifiers the AI agent likes to prepend/append that ExerciseDB's names
# usually don't include -- stripped off for a second, looser search attempt
# when the exact name has no match (e.g. "Barbell Unilateral Lunges" ->
# "lunges").
_QUALIFIER_WORDS = (
    "barbell", "dumbbell", "cable", "machine", "smith", "unilateral",
    "bilateral", "alternating", "elevated", "seated", "standing",
    "bent-over", "bent over", "behind-the-neck", "behind the neck",
    "incline", "decline", "close-grip", "close grip", "wide-grip",
    "wide grip", "assisted", "resistance band", "band", "kettlebell",
    "single-arm", "single arm", "single-leg", "single leg",
)

# ---------------------------------------------------------------------------
# Category fallback icons
# ---------------------------------------------------------------------------
# Small hand-drawn line icons in the app's dark/lime palette. Kept as plain
# SVG markup (not base64) so they stay easy to read/tweak in a diff.

_ICON_SURFACE = "#2a312a"
_ICON_LINE = "#d7ff32"
_ICON_MUTED = "#929a8e"

_ICON_TEMPLATES = {
    # Barbell over a flat bench
    "chest": f'''
        <rect x="4" y="4" width="56" height="56" rx="12" fill="{_ICON_SURFACE}"/>
        <rect x="14" y="36" width="36" height="8" rx="3" fill="{_ICON_MUTED}"/>
        <rect x="10" y="26" width="44" height="6" rx="3" fill="{_ICON_LINE}"/>
        <circle cx="12" cy="29" r="7" fill="{_ICON_LINE}"/>
        <circle cx="52" cy="29" r="7" fill="{_ICON_LINE}"/>
    ''',
    # Person + pull-up bar
    "back": f'''
        <rect x="4" y="4" width="56" height="56" rx="12" fill="{_ICON_SURFACE}"/>
        <rect x="14" y="16" width="36" height="5" rx="2.5" fill="{_ICON_LINE}"/>
        <circle cx="32" cy="30" r="5" fill="{_ICON_MUTED}"/>
        <path d="M32 35 L32 46 M32 38 L20 21 M32 38 L44 21 M32 46 L24 54 M32 46 L40 54"
              stroke="{_ICON_LINE}" stroke-width="3.4" stroke-linecap="round" fill="none"/>
    ''',
    # Squatting figure
    "legs": f'''
        <rect x="4" y="4" width="56" height="56" rx="12" fill="{_ICON_SURFACE}"/>
        <circle cx="32" cy="16" r="5" fill="{_ICON_MUTED}"/>
        <path d="M32 21 L32 32 M32 26 L22 30 M32 26 L42 30 M32 32 L22 40 L22 54 M32 32 L42 40 L42 54"
              stroke="{_ICON_LINE}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    ''',
    # Overhead press
    "shoulders": f'''
        <rect x="4" y="4" width="56" height="56" rx="12" fill="{_ICON_SURFACE}"/>
        <circle cx="32" cy="18" r="5" fill="{_ICON_MUTED}"/>
        <path d="M32 23 L32 44 M32 46 L24 54 M32 46 L40 54 M32 28 L18 14 M32 28 L46 14"
              stroke="{_ICON_LINE}" stroke-width="3.4" stroke-linecap="round" fill="none"/>
        <circle cx="16" cy="12" r="5" fill="{_ICON_LINE}"/>
        <circle cx="48" cy="12" r="5" fill="{_ICON_LINE}"/>
    ''',
    # Bicep curl
    "arms": f'''
        <rect x="4" y="4" width="56" height="56" rx="12" fill="{_ICON_SURFACE}"/>
        <circle cx="24" cy="16" r="5" fill="{_ICON_MUTED}"/>
        <path d="M24 21 L24 46 M24 46 L18 54 M24 46 L30 54 M24 27 L40 27 L40 40"
              stroke="{_ICON_LINE}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <circle cx="40" cy="40" r="6" fill="{_ICON_LINE}"/>
    ''',
    # Plank / core
    "core": f'''
        <rect x="4" y="4" width="56" height="56" rx="12" fill="{_ICON_SURFACE}"/>
        <circle cx="14" cy="24" r="5" fill="{_ICON_MUTED}"/>
        <path d="M14 29 L48 40 M14 29 L14 46 M48 40 L48 50"
              stroke="{_ICON_LINE}" stroke-width="3.4" stroke-linecap="round" fill="none"/>
        <line x1="8" y1="52" x2="56" y2="52" stroke="{_ICON_MUTED}" stroke-width="3" stroke-linecap="round"/>
    ''',
    # Running figure
    "cardio": f'''
        <rect x="4" y="4" width="56" height="56" rx="12" fill="{_ICON_SURFACE}"/>
        <circle cx="30" cy="14" r="5" fill="{_ICON_MUTED}"/>
        <path d="M30 19 L26 34 L36 40 L40 54 M26 34 L16 30 M26 34 L18 46 M30 19 L42 24"
              stroke="{_ICON_LINE}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    ''',
    # Seated forward-fold stretch -- used for yoga/mobility/foam-rolling/
    # breathing-type entries so they read as "recovery", not as a random
    # strength-training icon.
    "mobility": f'''
        <rect x="4" y="4" width="56" height="56" rx="12" fill="{_ICON_SURFACE}"/>
        <circle cx="20" cy="16" r="5" fill="{_ICON_MUTED}"/>
        <path d="M20 21 L20 34 L36 44 M20 34 L14 50 M36 44 L44 40 M36 44 L38 54"
              stroke="{_ICON_LINE}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <ellipse cx="30" cy="53" rx="20" ry="3" fill="{_ICON_MUTED}" opacity="0.5"/>
    ''',
    # Generic dumbbell
    "default": f'''
        <rect x="4" y="4" width="56" height="56" rx="12" fill="{_ICON_SURFACE}"/>
        <rect x="18" y="29" width="28" height="6" rx="3" fill="{_ICON_LINE}"/>
        <rect x="10" y="22" width="10" height="20" rx="4" fill="{_ICON_LINE}"/>
        <rect x="44" y="22" width="10" height="20" rx="4" fill="{_ICON_LINE}"/>
    ''',
}

# Keyword -> category, checked in this order (most specific / least
# ambiguous first -- e.g. "leg curl" must resolve to legs, not arms, and
# "mobility" must be checked *before* "arms" so "Thoracic Extension" isn't
# stolen by the "extension" keyword meant for triceps extensions).
_KEYWORD_CATEGORIES = [
    ("mobility", ("yoga", "flow", "sun salutation", "foam roll", "foam-roll",
                  "myofascial", "mobility", "thoracic", "spine", "spinal",
                  "breathing", "meditation", "recovery", "dynamic stretch",
                  "static stretch", " stretch", "cool-down", "cooldown",
                  "warm-up", "warmup", "flexibility")),
    ("cardio", ("run", "sprint", "jump", "burpee", "jack", "mountain climber",
                "cardio", "cycling", "bike", "rowing machine", "skater")),
    ("legs", ("squat", "lunge", "leg ", "calf", "glute", "hamstring", "quad",
              "hip thrust", "step-up", "step up", "ankle")),
    ("back", ("row", "pulldown", "pull-up", "pullup", "pull up", "deadlift",
              "lat ", "back")),
    ("chest", ("bench", "chest", "fly", "flye", "push-up", "pushup", "push up",
               "dip", "incline", "decline")),
    ("shoulders", ("shoulder", "overhead press", "military press", "lateral raise",
                   "front raise", "shrug", "arnold")),
    ("arms", ("curl", "tricep", "bicep", "extension", "skull crusher",
              "hammer", "kickback")),
    ("core", ("plank", "crunch", "sit-up", "situp", "sit up", "ab ", "abs",
              "core", "twist", "leg raise")),
]


def _category_for(name: str) -> str:
    lname = f" {name.lower()} "
    for category, keywords in _KEYWORD_CATEGORIES:
        if any(kw in lname for kw in keywords):
            return category
    return "default"


@functools.lru_cache(maxsize=256)
def _icon_data_uri(category: str) -> str:
    body = _ICON_TEMPLATES.get(category, _ICON_TEMPLATES["default"])
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{body}</svg>'
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _fallback_icon(name: str) -> str:
    return _icon_data_uri(_category_for(name))


# ---------------------------------------------------------------------------
# Bundled free-exercise-db lookup -- real human demo photos, no key,
# no network call needed to match (matching happens against the local
# JSON index; only the winning photo URL is handed to the browser).
# ---------------------------------------------------------------------------

# Purely descriptive words that don't change *which movement* this is --
# safe to drop before comparing two exercise names. Deliberately narrower
# than _QUALIFIER_WORDS below: this list keeps stance/angle words like
# "incline", "seated", "behind-the-neck" (free-exercise-db's own names
# use those too).
_FREE_DB_FILLER_WORDS = {
    "moderate", "weight", "neutral", "grip", "light", "heavy", "with",
    "and", "the", "a", "of", "to", "warm", "warmup", "up",
}


def _free_db_tokens(name: str) -> frozenset[str]:
    """Tokenizes an exercise name for matching. Parenthetical content is
    KEPT as ordinary words rather than discarded -- for a plain equipment
    note like "(machine)" that costs almost nothing, but for something
    like "Cardio Finisher: ... (30 sec jump rope or fast marching)" the
    parenthetical is where the actual exercise identity lives, so
    dropping it would leave nothing meaningful to match against."""
    lname = name.lower()
    lname = re.sub(r"[():,]", " ", lname)  # strip punctuation, keep the words
    lname = re.sub(r"[^a-z0-9\s-]", " ", lname)
    lname = lname.replace("-", " ")
    return frozenset(
        t.rstrip("s") for t in lname.split()
        if t and t not in _FREE_DB_FILLER_WORDS and len(t) > 1
    )


@functools.lru_cache(maxsize=1)
def _free_db_index() -> tuple[tuple[str, str, frozenset[str]], ...]:
    """Loads the bundled (name, id, tokens) index once per process. Returns
    an empty tuple if the data file is missing so callers degrade
    gracefully instead of crashing."""
    try:
        with open(_FREE_DB_JSON_PATH, "r", encoding="utf-8") as f:
            entries = json.load(f)
        return tuple(
            (e["name"], e["id"], _free_db_tokens(e["name"]))
            for e in entries
            if e.get("name") and e.get("id")
        )
    except (OSError, ValueError, KeyError):
        return ()


@functools.lru_cache(maxsize=512)
def _free_db_photo_url(name: str) -> str:
    """Best token-overlap match against the bundled free-exercise-db
    index. Returns "" if the index is unavailable or nothing clears the
    similarity cutoff."""
    query_tokens = _free_db_tokens(name)
    if not query_tokens:
        return ""

    best_id, best_score = "", 0.0
    for _, ex_id, ex_tokens in _free_db_index():
        if not ex_tokens:
            continue
        overlap = query_tokens & ex_tokens
        if not overlap:
            continue
        union = query_tokens | ex_tokens
        score = len(overlap) / len(union)
        if score > best_score:
            best_score, best_id = score, ex_id

    if best_score >= _FREE_DB_MATCH_CUTOFF:
        # Every entry in this dataset ships 2 photos: 0.jpg is usually just
        # the starting stance (for a plank/stretch/hold this can look like
        # almost nothing is happening), 1.jpg is consistently the actual
        # "in the movement" frame -- noticeably more recognizable, so it's
        # the better default demo image.
        return f"{_FREE_DB_IMAGE_BASE}/{quote(best_id)}/1.jpg"
    return ""


# The bundled free-exercise-db dataset is a strength-training library --
# it has essentially no entries for yoga flows, foam rolling, or generic
# "mobility drill" names, so those never clear the token-overlap cutoff
# above even though the dataset *does* contain real floor-stretch photos
# that are a reasonable visual stand-in (better than a generic icon). Each
# trigger is tried as a bonus search *in addition to* the real name, and
# only used if it beats what the name alone found -- so this never makes
# a genuinely good direct match worse, it only helps the "nothing at all"
# case land on a real photo instead of an icon.
_RECOVERY_ALIAS_HINTS = (
    (("yoga", "sun salutation", "flow", "vinyasa"), "cat stretch"),
    (("foam roll", "foam-roll", "myofascial", "roller"), "cat stretch"),
    (("thoracic", "spine", "spinal"), "cat stretch"),
    (("ankle mobility", "ankle drill", "ankle circle"), "ankle circles"),
    (("breathing", "meditation"), "child's pose"),
)


def _recovery_alias_photo(name: str) -> str:
    lname = name.lower()
    for triggers, hint in _RECOVERY_ALIAS_HINTS:
        if any(t in lname for t in triggers):
            photo = _free_db_photo_url(hint)
            if photo:
                return photo
    return ""


# ---------------------------------------------------------------------------
# ExerciseDB (RapidAPI) lookup -- real human demo photos/GIFs
# ---------------------------------------------------------------------------

def _rapidapi_key() -> str:
    return (os.getenv("RAPIDAPI_KEY") or "").strip()


def _simplified_name(name: str) -> str:
    """Strips equipment/stance qualifiers so a specific agent-generated name
    like "Barbell Unilateral Lunges" has a shot at matching ExerciseDB's
    plainer naming ("lunges")."""
    lname = name.lower()
    for word in _QUALIFIER_WORDS:
        lname = lname.replace(word, " ")
    lname = re.sub(r"[^a-z0-9\s]", " ", lname)
    lname = re.sub(r"\s+", " ", lname).strip()
    return lname


@functools.lru_cache(maxsize=512)
def _exercisedb_search(term: str) -> str:
    """Single ExerciseDB /exercises/name/{term} lookup. Returns a gifUrl or
    "" (no match / no key configured / request failed)."""
    key = _rapidapi_key()
    if not key or not term:
        return ""
    try:
        resp = requests.get(
            f"{_EXERCISEDB_BASE}/exercises/name/{quote(term)}",
            headers={
                "X-RapidAPI-Key": key,
                "X-RapidAPI-Host": _EXERCISEDB_HOST,
            },
            params={"limit": "1"},
            timeout=_EXERCISEDB_TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json() or []
        if results:
            return (results[0] or {}).get("gifUrl", "") or ""
    except (requests.RequestException, ValueError, IndexError):
        pass
    return ""


def _exercisedb_photo_url(name: str) -> str:
    """Tries the exercise name as given, then a qualifier-stripped version,
    against ExerciseDB. No-op (returns "") if RAPIDAPI_KEY isn't set."""
    if not _rapidapi_key():
        return ""

    photo = _exercisedb_search(name.lower())
    if photo:
        return photo

    simplified = _simplified_name(name)
    if simplified and simplified != name.lower():
        photo = _exercisedb_search(simplified)
        if photo:
            return photo
    return ""


# ---------------------------------------------------------------------------
# wger.de lookup (free fallback real photo, no key required)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=512)
def _wger_photo_url(name: str) -> str:
    """Returns an https image URL from wger.de's open exercise database, or
    "" if nothing was found / the request failed for any reason. Cached
    per process so a given exercise name only ever triggers one network
    call, regardless of how many times/pages it's rendered on. Tries the
    name as given, then (like the ExerciseDB layer) a qualifier-stripped
    version, since wger's own naming tends to be plainer than what the AI
    agent generates."""
    for term in dict.fromkeys([name, _simplified_name(name)]):
        if not term:
            continue
        try:
            resp = requests.get(
                _WGER_SEARCH_URL,
                params={"term": term, "language": "en", "format": "json"},
                timeout=_WGER_TIMEOUT,
            )
            resp.raise_for_status()
            results = (resp.json() or {}).get("suggestions", [])
            for item in results:
                image = ((item or {}).get("data") or {}).get("image")
                if image:
                    return image
        except (requests.RequestException, ValueError):
            continue
    return ""


def get_exercise_image(exercise_name: str) -> str:
    """Best-effort demo image for an exercise name. Always returns a usable
    <img src> value -- a real human demo photo when the bundled
    free-exercise-db index (or, failing that, ExerciseDB / wger) has a
    match, otherwise a category icon generated locally so the UI never
    shows a broken image.

    Troubleshooting a broken RAPIDAPI_KEY: ExerciseDB's free RapidAPI tier
    has gotten unreliable (many free-tier keys now get a 403 "not
    subscribed" or empty results even with a key set). That's fine here --
    the bundled free-exercise-db layer runs first and needs no key at all,
    so exercise photos work even if RAPIDAPI_KEY stops working. Set
    EXERCISE_IMAGE_DEBUG=1 to see which layer resolved each name.
    """
    name = (exercise_name or "").strip()
    if not name:
        return _icon_data_uri("default")

    photo = _free_db_photo_url(name)
    if photo:
        _debug(name, f"free-exercise-db ({photo})")
        return photo

    photo = _recovery_alias_photo(name)
    if photo:
        _debug(name, f"free-exercise-db, recovery alias ({photo})")
        return photo

    photo = _exercisedb_photo_url(name)
    if photo:
        _debug(name, "ExerciseDB")
        return photo

    photo = _wger_photo_url(name)
    if photo:
        _debug(name, "wger.de")
        return photo

    _debug(name, "icon fallback")
    return _fallback_icon(name)
