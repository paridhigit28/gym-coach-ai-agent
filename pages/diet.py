import base64
import html
import mimetypes
import os as _os

import streamlit as st

from services.ui.style_loader import load_css, inject_local_font

_static_dir = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "static"
)
load_css(_os.path.join(_static_dir, "style.css"))
inject_local_font(_os.path.join(_static_dir, "AdobeClean.otf"), "AdobeClean")

from database.db import SessionLocal
from database.models import User, FitnessAssessment
from services.groq_service import generate_meal_plan
from services.diet_service import save_diet_plan, get_diet_plan
from nutrition import calculator, food_database


# -----------------------------------------------------------------------------
# Diet-page-only visual layer.
# The selectors are intentionally scoped to the diet page classes/components so
# this redesign does not change the Workout Planner or Live Gym Coach UI.
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --diet-bg: #0b100c;
        --diet-panel: #111811;
        --diet-panel-2: #151d14;
        --diet-line: rgba(220, 255, 52, .16);
        --diet-line-soft: rgba(255,255,255,.08);
        --diet-lime: #d9ff35;
        --diet-lime-soft: rgba(217,255,53,.10);
        --diet-text: #f3f6ee;
        --diet-muted: #899287;
    }

    /* Make the Diet Planner feel like a full landing-page experience. */
    .stApp { background: var(--diet-bg) !important; }
    [data-testid="stMainBlockContainer"] {
        max-width: 1500px !important;
        padding-left: clamp(1rem, 3vw, 3.5rem) !important;
        padding-right: clamp(1rem, 3vw, 3.5rem) !important;
        padding-bottom: 5rem !important;
    }

    /* Top navigation: same Trainora language, but more expressive on Diet. */
    .trainora-top-nav-shell {
        background: rgba(11,16,12,.90) !important;
        border-color: rgba(217,255,53,.18) !important;
        box-shadow: 0 12px 45px rgba(0,0,0,.32), inset 0 -1px 0 rgba(217,255,53,.06) !important;
        backdrop-filter: blur(18px) !important;
    }
    button[key^="topnav_"] {
        position: relative !important;
        overflow: hidden !important;
        border-radius: 999px !important;
        transition: transform .22s ease, color .22s ease, background .22s ease,
                    box-shadow .22s ease !important;
    }
    button[key^="topnav_"]::after {
        content: "";
        position: absolute;
        left: 18%; right: 18%; bottom: 3px;
        height: 2px;
        background: var(--diet-lime);
        transform: scaleX(0);
        transform-origin: center;
        transition: transform .22s ease;
    }
    button[key^="topnav_"]:hover {
        transform: translateY(-2px) !important;
        color: var(--diet-lime) !important;
        background: rgba(217,255,53,.075) !important;
        box-shadow: 0 8px 22px rgba(217,255,53,.07) !important;
    }
    button[key^="topnav_"]:hover::after { transform: scaleX(1); }

    /* Hero */
    .diet-hero {
        position: relative;
        min-height: 170px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        overflow: hidden;
        padding: clamp(1.2rem, 2.4vw, 2rem) clamp(1.5rem, 4vw, 3rem);
        margin: 1rem 0 1.2rem;
        border: 1px solid var(--diet-line);
        background:
            radial-gradient(circle at 84% 22%, rgba(217,255,53,.12), transparent 25%),
            radial-gradient(circle at 75% 100%, rgba(217,255,53,.05), transparent 30%),
            linear-gradient(135deg, #101710 0%, #0c110d 62%, #111911 100%);
        box-shadow: 0 30px 70px rgba(0,0,0,.30);
    }
    .diet-hero::before {
        content: "";
        position: absolute;
        width: 220px; height: 220px;
        right: -80px; top: -100px;
        border: 1px solid rgba(217,255,53,.12);
        border-radius: 50%;
        box-shadow: 0 0 0 45px rgba(217,255,53,.025), 0 0 0 90px rgba(217,255,53,.012);
    }
    .diet-eyebrow {
        position: relative;
        z-index: 1;
        display: inline-flex;
        width: fit-content;
        align-items: center;
        gap: 8px;
        margin-bottom: 18px;
        color: var(--diet-lime);
        font-size: .68rem;
        font-weight: 600;
        letter-spacing: .18em;
        text-transform: uppercase;
    }
    .diet-eyebrow::before {
        content: "";
        width: 7px; height: 7px;
        border-radius: 50%;
        background: var(--diet-lime);
        box-shadow: 0 0 14px rgba(217,255,53,.75);
    }
    .diet-hero h1 {
        position: relative;
        z-index: 1;
        max-width: 760px;
        margin: 0;
        color: var(--diet-text);
        font-size: clamp(1.8rem, 3.4vw, 2.8rem) !important;
        line-height: 1.05 !important;
        letter-spacing: -.03em !important;
        font-weight: 500 !important;
    }
    .diet-hero h1 span { color: var(--diet-lime); }
    .diet-hero p {
        position: relative;
        z-index: 1;
        max-width: 620px;
        margin: 12px 0 0;
        color: #a6afa2;
        font-size: .88rem;
        line-height: 1.5;
    }

    /* CTA row */
    .diet-cta-note {
        padding: 14px 18px;
        border-left: 2px solid var(--diet-lime);
        background: linear-gradient(90deg, rgba(217,255,53,.07), transparent);
        color: var(--diet-muted);
        font-size: .84rem;
        line-height: 1.5;
    }
    .diet-cta-note strong { color: var(--diet-text); }
    div[data-testid="stButton"] button[kind="primary"] {
        min-height: 52px !important;
        border-radius: 999px !important;
        border: 1px solid var(--diet-lime) !important;
        background: var(--diet-lime) !important;
        color: #10140c !important;
        font-weight: 700 !important;
        box-shadow: 0 0 0 0 rgba(217,255,53,.25) !important;
        transition: transform .22s ease, box-shadow .22s ease, filter .22s ease !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        transform: translateY(-3px) scale(1.015) !important;
        filter: brightness(1.04) !important;
        box-shadow: 0 12px 35px rgba(217,255,53,.20) !important;
    }

    /* Nutrition overview */
    .diet-section-label {
        margin: 2.5rem 0 .8rem;
        color: var(--diet-lime);
        font-size: .68rem;
        font-weight: 600;
        letter-spacing: .18em;
        text-transform: uppercase;
    }
    .diet-section-title {
        margin: 0 0 1.2rem;
        color: var(--diet-text);
        font-size: clamp(2rem, 4vw, 3.8rem);
        line-height: .98;
        letter-spacing: -.045em;
    }
    [data-testid="stMetric"] {
        position: relative;
        overflow: hidden;
        min-height: 120px;
        padding: 1.25rem 1.35rem !important;
        border: 1px solid var(--diet-line-soft) !important;
        border-left: 1px solid var(--diet-line) !important;
        background: linear-gradient(145deg, rgba(21,29,20,.95), rgba(12,17,13,.95)) !important;
        box-shadow: none !important;
        transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease !important;
    }
    [data-testid="stMetric"]::after {
        content: "";
        position: absolute;
        width: 110px; height: 110px;
        right: -45px; top: -45px;
        border: 1px solid rgba(217,255,53,.12);
        border-radius: 50%;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: rgba(217,255,53,.30) !important;
        box-shadow: 0 18px 45px rgba(0,0,0,.22) !important;
    }
    [data-testid="stMetricValue"] { color: var(--diet-lime) !important; font-size: 1.9rem !important; }
    [data-testid="stMetricLabel"] { color: var(--diet-muted) !important; }

    /* Meal cards */
    .diet-meal-heading {
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: 18px;
        margin: 3rem 0 1rem;
    }
    .diet-meal-heading h2 {
        margin: 0;
        color: var(--diet-text);
        font-size: clamp(2rem, 4vw, 3.5rem);
        line-height: .95;
        letter-spacing: -.045em;
    }
    .diet-meal-heading span { color: var(--diet-muted); font-size: .82rem; }
    .diet-meal-card {
        position: relative;
        overflow: hidden;
        height: 100%;
        min-height: 430px;
        padding: 18px;
        border: 1px solid var(--diet-line-soft);
        background: linear-gradient(145deg, #131b13, #0e130f);
        transition: transform .3s cubic-bezier(.2,.8,.2,1), border-color .3s ease,
                    box-shadow .3s ease;
    }
    .diet-meal-card:hover {
        transform: translateY(-8px);
        border-color: rgba(217,255,53,.28);
        box-shadow: 0 28px 65px rgba(0,0,0,.34);
    }
    .diet-meal-top {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: flex-start;
        padding-bottom: 14px;
        border-bottom: 1px solid var(--diet-line-soft);
    }
    .diet-meal-kicker { color: var(--diet-lime); font-size: .62rem; letter-spacing: .15em; text-transform: uppercase; }
    .diet-meal-name { margin-top: 4px; color: var(--diet-text); font-size: 1.35rem; font-weight: 500; }
    .diet-meal-cal { color: var(--diet-text); font-size: .8rem; white-space: nowrap; }
    .diet-food-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
        gap: 12px;
        padding-top: 15px;
    }
    .diet-food {
        position: relative;
        overflow: hidden;
        min-width: 0;
        border: 1px solid rgba(255,255,255,.065);
        background: #0b100c;
        cursor: zoom-in;
        transition: transform .28s ease, border-color .28s ease, box-shadow .28s ease;
    }
    .diet-food:hover {
        transform: translateY(-5px) scale(1.025);
        z-index: 3;
        border-color: rgba(217,255,53,.38);
        box-shadow: 0 18px 40px rgba(0,0,0,.40), 0 0 30px rgba(217,255,53,.07);
    }
    .diet-food-image-wrap { height: 155px; overflow: hidden; background: #121812; }
    .diet-food img {
        width: 100%; height: 100%; object-fit: cover; display: block;
        transition: transform .5s cubic-bezier(.2,.8,.2,1), filter .35s ease;
    }
    .diet-food:hover img { transform: scale(1.12); filter: saturate(1.08) brightness(1.05); }
    .diet-food::after {
        content: "VIEW";
        position: absolute;
        top: 10px; right: 10px;
        padding: 5px 8px;
        color: #10140c;
        background: var(--diet-lime);
        font-size: .55rem;
        font-weight: 700;
        letter-spacing: .12em;
        opacity: 0;
        transform: translateY(-5px);
        transition: opacity .25s ease, transform .25s ease;
    }
    .diet-food:hover::after { opacity: 1; transform: translateY(0); }
    .diet-food-meta { padding: 11px 12px 13px; }
    .diet-food-name { color: var(--diet-text); font-size: .88rem; line-height: 1.25; }
    .diet-food-grams { margin-top: 5px; color: var(--diet-muted); font-size: .72rem; }

    .diet-meal-macros {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 14px;
        padding-top: 13px;
        border-top: 1px solid var(--diet-line-soft);
    }
    .diet-macro-chip {
        padding: 6px 9px;
        border: 1px solid rgba(217,255,53,.13);
        color: #aeb8aa;
        background: rgba(217,255,53,.025);
        font-size: .68rem;
    }
    .diet-macro-chip strong { color: var(--diet-lime); font-weight: 500; }

    .diet-footnote {
        margin-top: 2rem;
        padding: 15px 18px;
        border-top: 1px solid var(--diet-line-soft);
        border-bottom: 1px solid var(--diet-line-soft);
        color: #778176;
        font-size: .72rem;
        line-height: 1.65;
    }

    /* Keep Streamlit's default separators from fighting the custom design. */
    hr { border-color: var(--diet-line-soft) !important; }
    .stAlert { border-radius: 0 !important; }

    @media (max-width: 800px) {
        .diet-hero { min-height: 140px; padding: 1.4rem 1.2rem; }
        .diet-hero h1 { font-size: 1.7rem !important; }
        .diet-meal-card { min-height: auto; }
        .diet-food-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .diet-food-image-wrap { height: 135px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.warning("Please log in to view this page.")
    st.stop()


# -----------------------------------------------------------------------------
# Small helpers for the visual-only layer.
# -----------------------------------------------------------------------------
def _image_data_uri(path: str | None) -> str | None:
    if not path or not _os.path.isfile(path):
        return None
    try:
        mime = mimetypes.guess_type(path)[0] or "image/jpeg"
        with open(path, "rb") as fh:
            encoded = base64.b64encode(fh.read()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except OSError:
        return None


def _esc(value) -> str:
    return html.escape(str(value))


def _meal_card(meal_name: str, meal_details: dict) -> str:
    items = meal_details.get("Items", []) or []
    food_html = []

    for item in items:
        image_path = food_database.image_for_item(item)
        image_uri = _image_data_uri(image_path)
        item_name, grams = food_database.parse_item(item)

        if image_uri:
            image_block = (
                f'<div class="diet-food-image-wrap">'
                f'<img src="{image_uri}" alt="{_esc(item_name)}" loading="lazy">'
                f'</div>'
            )
        else:
            image_block = (
                '<div class="diet-food-image-wrap" style="display:flex;align-items:center;'
                'justify-content:center;color:#667064;font-size:.7rem;">'
                'IMAGE NOT AVAILABLE</div>'
            )

        food_html.append(
            '<div class="diet-food">'
            f'{image_block}'
            '<div class="diet-food-meta">'
            f'<div class="diet-food-name">{_esc(item_name)}</div>'
            f'<div class="diet-food-grams">{grams:g} g serving</div>'
            '</div>'
            '</div>'
        )

    if not food_html:
        food_html.append(
            '<div style="grid-column:1/-1;padding:35px;text-align:center;'
            'border:1px dashed rgba(255,255,255,.1);color:#778176;">'
            'No food items were returned for this meal.'
            '</div>'
        )

    calories = meal_details.get("Calories", "-")
    protein = meal_details.get("Protein", "-")
    carbs = meal_details.get("Carbs", "-")
    fats = meal_details.get("Fats", "-")

    return (
        '<div class="diet-meal-card">'
        '<div class="diet-meal-top">'
        '<div><div class="diet-meal-kicker">MEAL PLAN</div>'
        f'<div class="diet-meal-name">{_esc(meal_name)}</div></div>'
        f'<div class="diet-meal-cal">{_esc(calories)} kcal</div>'
        '</div>'
        f'<div class="diet-food-grid">{"".join(food_html)}</div>'
        '<div class="diet-meal-macros">'
        f'<div class="diet-macro-chip"><strong>P</strong> {_esc(protein)}</div>'
        f'<div class="diet-macro-chip"><strong>C</strong> {_esc(carbs)}</div>'
        f'<div class="diet-macro-chip"><strong>F</strong> {_esc(fats)}</div>'
        '</div>'
        '</div>'
    )


# -----------------------------------------------------------------------------
# Data / generation logic — unchanged.
# -----------------------------------------------------------------------------
db = SessionLocal()
try:
    user = db.query(User).filter(User.id == st.session_state.user_id).first()
    assessment = db.query(FitnessAssessment).filter(
        FitnessAssessment.user_id == st.session_state.user_id
    ).first()
finally:
    db.close()

if not user or not user.height or not user.weight:
    st.warning("Please update your Profile with your height and weight first.")
    st.stop()

if not assessment:
    st.warning("Please complete your Fitness Assessment first to get a personalized plan.")
    st.stop()

existing_plan = get_diet_plan(st.session_state.user_id)

# -----------------------------------------------------------------------------
# Hero / CTA
# -----------------------------------------------------------------------------
st.markdown(
    """
    <section class="diet-hero">
        <div class="diet-eyebrow">YOUR GOALS · YOUR FOOD · YOUR PLAN</div>
        <h1>Eat well.<br><span>Train better.</span></h1>
        <p>
            A personalized daily meal plan built around your fitness goal,
            food preferences and lifestyle — with real Indian food images so
            you know exactly what is on your plate.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

cta_col, button_col = st.columns([3.4, 1.2], vertical_alignment="center")
with cta_col:
    st.markdown(
        '<div class="diet-cta-note"><strong>Ready for today?</strong> '
        'Build a fresh four-meal plan from your personalized nutrition profile.</div>',
        unsafe_allow_html=True,
    )
with button_col:
    if st.button("Build My Meal Plan  →", type="primary", width="stretch"):
        with st.spinner("Our AI is creating your personalized meal plan..."):
            user_data = {
                "age": user.age,
                "gender": user.gender,
                "height": user.height,
                "weight": user.weight,
                "goal": calculator.derive_goal(
                    user.weight, assessment.target_weight, user.fitness_goal
                ),
                "activity_level": assessment.workout_frequency,
                "diet": assessment.preferred_meals,
                "body_build": getattr(assessment, "body_build", None),
                "food_restrictions": assessment.food_restrictions or "None",
            }
            try:
                new_plan = generate_meal_plan(user_data)
                save_diet_plan(st.session_state.user_id, new_plan)
                existing_plan = new_plan
                st.success("Diet plan generated successfully!")
            except Exception as e:
                st.error(f"Error generating plan: {e}")


if existing_plan:
    macros = existing_plan.get("DailyMacros", {})

    st.markdown(
        '<div class="diet-section-label">ONE DAY · BUILT AROUND YOU</div>'
        '<div class="diet-section-title">Nutrition that fits you.</div>',
        unsafe_allow_html=True,
    )

    col_mac1, col_mac2, col_mac3 = st.columns(3)
    with col_mac1:
        st.metric("Target Calories", f"{existing_plan.get('TargetCalories', '-')} kcal")
    with col_mac2:
        st.metric(
            "Maintenance Calories",
            f"{existing_plan.get('MaintenanceCalories', '-')} kcal",
        )
    # with col_mac3:
    #     st.metric(
    #         "Daily Protein",
    #         f"{macros.get('Protein', '-')} g",
    #     )

    if "DailyActualCalories" in existing_plan:
        actual = existing_plan.get("DailyActualMacros", {})
        st.markdown(
            f'<div class="diet-cta-note" style="margin-top:18px;">'
            f'<strong>Plan total:</strong> {_esc(existing_plan["DailyActualCalories"])} kcal '
            f'· Protein {_esc(actual.get("Protein", "-"))} '
            f'· Carbs {_esc(actual.get("Carbs", "-"))} '
            f'· Fats {_esc(actual.get("Fats", "-"))}</div>',
            unsafe_allow_html=True,
        )

    if existing_plan.get("BodyBuild"):
        st.markdown(
            f'<div style="margin-top:12px;color:#899287;font-size:.75rem;">'
            f'PERSONALIZED FOR <strong style="color:#f3f6ee;">{_esc(existing_plan["BodyBuild"])}</strong>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="diet-meal-heading">'
        '<div><div class="diet-eyebrow" style="margin-bottom:8px;">FOUR MEALS · ONE PLAN</div>'
        # '<h2>Your day, plated.</h2></div>'
        # '<span>Hover over a dish to bring it forward.</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    meals = existing_plan.get("Meals", {})
    meal_items = list(meals.items())

    # Two large editorial cards per row make use of the entire page width.
    for row_start in range(0, len(meal_items), 2):
        row = meal_items[row_start:row_start + 2]
        cols = st.columns(len(row), gap="large")
        for col, (meal_name, meal_details) in zip(cols, row):
            with col:
                st.markdown(_meal_card(meal_name, meal_details), unsafe_allow_html=True)

    st.markdown(
        '<div class="diet-footnote">'
        'Calories and macros are calculated from the selected food items and the '
        'nutrition database rather than relying on the AI\'s estimates. This is '
        'general guidance; consult a qualified professional for medical, allergy, '
        'or other individualized nutrition needs.'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div style="margin:4rem 0;padding:4rem 2rem;text-align:center;'
        'border:1px solid rgba(255,255,255,.08);background:#101610;">'
        '<div class="diet-eyebrow" style="margin-bottom:12px;">YOUR PLAN IS WAITING</div>'
        '<div style="font-size:2.5rem;letter-spacing:-.04em;color:#f3f6ee;">'
        'Build your first meal plan.'
        '</div></div>',
        unsafe_allow_html=True,
    )