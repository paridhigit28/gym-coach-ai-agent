import streamlit as st
import os as _os
from services.ui.style_loader import load_css, inject_local_font
from services.ui.components import (
    hero, tag, section_header, stat_card, badge,
    plan_total_bar, dish_item_markup, plan_grid_card_markup, rest_card_markup,
    day_notes_markup, day_icon,
)

_static_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "static")
load_css(_os.path.join(_static_dir, "style.css"))
inject_local_font(_os.path.join(_static_dir, "AdobeClean.otf"), "AdobeClean")

from database.db import SessionLocal
from database.models import User, FitnessAssessment
from services.groq_service import generate_workout_plan
from services.workout_service import save_workout_plan, get_workout_plan
from services.vision.exercise_images import get_exercise_image

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.warning("Please log in to view this page.")
    st.stop()

db = SessionLocal()
try:
    user = db.query(User).filter(User.id == st.session_state.user_id).first()
    assessment = db.query(FitnessAssessment).filter(FitnessAssessment.user_id == st.session_state.user_id).first()
finally:
    db.close()

if not user or not user.height or not user.weight:
    st.warning("Please update your Profile with your height and weight first.")
    st.stop()

if not assessment:
    st.warning("Please complete your Fitness Assessment first to get a personalized plan.")
    st.stop()

existing_plan = get_workout_plan(st.session_state.user_id)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
hero(
    tag_label="Your Goals · Your Body · Your Plan",
    greeting=(
        '<span style="color:var(--lime);">Train hard.</span><br/>'
        '<span style="color:var(--lime);">Move better.</span>'
    ),
    sub=(
        "A personalized weekly training split built around your fitness goal, "
        "equipment, and experience — with a real demo photo for every exercise "
        "so you know exactly how to perform it."
    ),
)

# ---------------------------------------------------------------------------
# Generate action
# ---------------------------------------------------------------------------
with st.container(border=True):
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**Ready to train?**")
        st.write("Build a fresh weekly split from your personalized fitness profile.")
    with col2:
        generate_clicked = st.button("Build My Workout Plan →", type="primary", width="stretch")

if generate_clicked:
    with st.spinner("Building your personalized weekly split..."):
        user_data = {
            "age": user.age,
            "gender": user.gender,
            "height": user.height,
            "weight": user.weight,
            "goal": user.fitness_goal or f"Target weight: {assessment.target_weight}kg",
            "experience": assessment.workout_experience,
            "equipment": assessment.equipment_access,
            "days": assessment.workout_days_per_week,
            "medical_conditions": assessment.medical_conditions or "None"
        }
        try:
            new_plan = generate_workout_plan(user_data)
            save_workout_plan(st.session_state.user_id, new_plan)
            existing_plan = new_plan
            st.success("Workout plan generated successfully!")
        except Exception as e:
            st.error(f"Error generating plan: {e}")

# ---------------------------------------------------------------------------
# Training profile + weekly schedule
# ---------------------------------------------------------------------------
if existing_plan:
    tag("One Week · Built Around You")
    st.markdown('<h2 class="tr-page-title" style="font-size:1.7rem;">Training that fits you.</h2>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Fitness Level", assessment.current_fitness_level or "—")
    with c2:
        stat_card("Experience", assessment.workout_experience or "—")
    with c3:
        stat_card("Days / Week", str(assessment.workout_days_per_week or "—"))
    with c4:
        stat_card("Equipment", assessment.equipment_access or "—")

    # --- Plan total bar -----------------------------------------------
    training_days = [d for d in existing_plan.values() if (d.get("WorkoutType") or "").lower() != "rest"]
    rest_days = len(existing_plan) - len(training_days)
    total_exercises = sum(len(d.get("Exercises") or []) for d in training_days)
    kcal_values = [d.get("EstimatedCaloriesBurned") for d in training_days if d.get("EstimatedCaloriesBurned")]
    avg_kcal = round(sum(kcal_values) / len(kcal_values)) if kcal_values else None

    summary_bits = [f"<b>{len(training_days)} training day{'s' if len(training_days) != 1 else ''}</b>"]
    if rest_days:
        summary_bits.append(f"{rest_days} rest day{'s' if rest_days != 1 else ''}")
    summary_bits.append(f"{total_exercises} exercises total")
    if avg_kcal:
        summary_bits.append(f"~{avg_kcal} kcal burned / session")
    plan_total_bar("Plan total: " + " · ".join(summary_bits))

    if user.fitness_goal:
        st.caption(f"Personalized for goal: {user.fitness_goal}")

    section_header("Seven Days · One Plan", hint="Pick a day below — every exercise gets a big demo photo.")

    # --- Day tabs: one day fully in view at a time, so photos get to be
    # large instead of squeezed 4-to-a-row in a shared grid. --------------
    day_items = list(existing_plan.items())
    tab_labels = [
        f"{day_icon(day_plan.get('WorkoutType', 'Rest Day'))} {day}"
        for day, day_plan in day_items
    ]
    day_tabs = st.tabs(tab_labels)

    for tab, (day, day_plan) in zip(day_tabs, day_items):
        workout_type = day_plan.get("WorkoutType", "Rest Day")
        is_rest = workout_type.lower() == "rest"

        with tab:
            if is_rest:
                st.markdown(
                    rest_card_markup(
                        day, workout_type,
                        "Enjoy your rest day! Proper recovery is crucial for progress.",
                    ),
                    unsafe_allow_html=True,
                )
                continue

            exercises = day_plan.get("Exercises") or []
            items_html = "".join(
                dish_item_markup(
                    get_exercise_image(ex.get("Exercise", "Exercise")),
                    ex.get("Exercise", "Exercise"),
                    f"{ex.get('Sets', '-')} × {ex.get('Reps', '-')} · {ex.get('Rest', '-')} rest",
                    index=i,
                )
                for i, ex in enumerate(exercises, start=1)
            )

            kcal = day_plan.get("EstimatedCaloriesBurned")
            meta_right = f"{kcal} kcal" if kcal else badge("Training Day", "good")

            card_html = plan_grid_card_markup(
                day, workout_type, meta_right, items_html,
                footnote_html="", icon=day_icon(workout_type),
            )
            # Splice the warmup/cooldown note strip in as a real part of
            # the card (bigger and easier to read than a footnote line).
            notes_html = day_notes_markup(day_plan.get("Warmup"), day_plan.get("Cooldown"))
            if notes_html:
                card_html = card_html[:-len("</div>")] + notes_html + "</div>"
            st.markdown(card_html, unsafe_allow_html=True)

else:
    st.markdown(
        """
        <div class="trainora-empty-state">
            <h2>No workout plan yet</h2>
            <p>Click <strong>Build My Workout Plan</strong> above to build your first personalized weekly split.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
