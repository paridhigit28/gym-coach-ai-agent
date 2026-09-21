import streamlit as st
import os as _os
from services.ui.style_loader import load_css, inject_local_font

_static_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "static")
load_css(_os.path.join(_static_dir, "style.css"))
inject_local_font(_os.path.join(_static_dir, "AdobeClean.otf"), "AdobeClean")

from database.db import SessionLocal
from database.models import User, FitnessAssessment
from services.ui.components import tag

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.warning("Please log in to view this page.")
    st.stop()

tag("My Profile · Onboarding")

# ---------------------------------------------------------------------------
# Page-scoped CSS: turns st.button into big "choice card" buttons like a
# Typeform-style, one-question-at-a-time wizard.
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .wizard-progress-track {
        width: 100%; height: 6px; border-radius: 999px;
        background: var(--surface-3, var(--border-soft));
        margin-bottom: 28px; overflow: hidden;
    }
    .wizard-progress-fill {
        height: 100%; background: linear-gradient(90deg, var(--teal-dim), var(--teal));
        box-shadow: 0 0 10px var(--teal-glow);
        transition: width 0.25s ease;
    }
    .wizard-step-label {
        color: var(--muted); font-size: 0.8rem; letter-spacing: 0.08em;
        text-transform: uppercase; margin-bottom: 6px;
    }
    .wizard-question {
        font-size: 1.7rem; font-weight: 700; color: var(--text);
        line-height: 1.25; margin-bottom: 26px;
    }
    /* Choice-card buttons (secondary = unselected, primary = selected).
       Scoped to :not([data-baseweb="popover"] ...) so this never leaks
       into the account-menu dropdown (Home / My Profile / Logout),
       which must look identical on every page. */
    div[data-testid="stButton"]:not([data-baseweb="popover"] div[data-testid="stButton"]) button {
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 16px 20px !important;
        font-size: 1rem !important;
        margin-bottom: 10px !important;
        border-radius: var(--radius-sm, 10px) !important;
    }
    div[data-testid="stButton"]:not([data-baseweb="popover"] div[data-testid="stButton"]) button[kind="secondary"] {
        background-color: var(--surface-2) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
    }
    div[data-testid="stButton"]:not([data-baseweb="popover"] div[data-testid="stButton"]) button[kind="secondary"]:hover {
        border-color: var(--teal) !important;
        background-color: var(--teal-glow) !important;
        color: var(--teal) !important;
    }
    div[data-testid="stButton"]:not([data-baseweb="popover"] div[data-testid="stButton"]) button[kind="primary"] {
        background-color: var(--teal) !important;
        color: var(--on-lime, #10140c) !important;
        border: 1px solid var(--teal) !important;
        font-weight: 700 !important;
    }
    .wizard-nav-back button {
        background: transparent !important;
        border: none !important;
        color: var(--muted) !important;
        padding-left: 0 !important;
    }
    .wizard-nav-back button:hover {
        color: var(--teal) !important;
        background: transparent !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Step definitions — one question per step. "choice" steps auto-advance on
# click; "text" / "number" / "text_area" steps show a Continue button.
# ---------------------------------------------------------------------------
STEPS = [
    {"key": "full_name", "type": "text", "label": "What should we call you?",
     "placeholder": "Your full name"},
    {"key": "gender", "type": "choice", "label": "What's your gender?",
     "options": ["Male", "Female", "Other"]},
    {"key": "age", "type": "number", "label": "How old are you?",
     "min": 10, "max": 120, "step": 1, "default": 25, "fmt": "%d"},
    {"key": "weight", "type": "number", "label": "What's your current weight?",
     "min": 20.0, "max": 300.0, "step": 0.5, "default": 70.0, "suffix": "kg"},
    {"key": "height", "type": "number", "label": "What's your height?",
     "min": 50.0, "max": 250.0, "step": 0.5, "default": 170.0, "suffix": "cm"},
    {"key": "current_fitness_level", "type": "choice", "label": "What's your current fitness level?",
     "options": ["Beginner", "Intermediate", "Advanced"]},
    {"key": "workout_experience", "type": "choice", "label": "How much workout experience do you have?",
     "options": ["Less than 6 months", "6 months - 1 year", "1 - 3 years", "3+ years"]},
    {"key": "target_weight", "type": "number", "label": "What's your target weight?",
     "min": 20.0, "max": 300.0, "step": 0.5, "default": 70.0, "suffix": "kg"},
    {"key": "goal_timeline", "type": "choice", "label": "What's your goal timeline?",
     "options": ["1 month", "3 months", "6 months", "1 year"]},
    {"key": "workout_days_per_week", "type": "choice", "label": "How many days a week can you work out?",
     "options": ["1", "2", "3", "4", "5", "6", "7"]},
    {"key": "workout_duration", "type": "choice", "label": "How long can each workout session be?",
     "options": ["15", "30", "45", "60", "75", "90", "105", "120"], "suffix": "minutes"},
    {"key": "equipment_access", "type": "choice", "label": "What equipment do you have access to?",
     "options": ["None (Bodyweight)", "Dumbbells/Kettlebells", "Resistance Bands", "Full Gym"]},
    {"key": "workout_frequency", "type": "choice", "label": "How active is your daily lifestyle currently?",
     "options": ["Sedentary", "Lightly Active", "Moderately Active", "Very Active"]},
    {"key": "medical_conditions", "type": "text_area", "label": "Any medical conditions we should know about?",
     "placeholder": "e.g., Asthma, Knee Pain — or type None"},
    {"key": "preferred_meals", "type": "choice", "label": "What's your diet preference?",
     "options": ["Non-Vegetarian", "Vegetarian", "Vegan"]},
    {"key": "cuisine_preference", "type": "choice", "label": "What cuisine do you prefer?",
     "options": ["Indian", "Continental", "Mixed"]},
    {"key": "food_restrictions", "type": "text_area", "label": "Any food restrictions or allergies?",
     "placeholder": "e.g., Lactose intolerant, Nut allergy — or type None"},
    {"key": "body_build", "type": "choice", "label": "What's your body build? (optional)",
     "options": ["Not specified", "Lean / Slim Build", "Athletic / Muscular Build", "Broad / Higher Body-Fat Build"]},
    {"key": "stress_level", "type": "choice", "label": "What's your current stress level?",
     "options": ["Low", "Moderate", "High"]},
]
TOTAL_STEPS = len(STEPS) + 1  # +1 for the final review/save screen

db = SessionLocal()
try:
    user = db.query(User).filter(User.id == st.session_state.user_id).first()
    existing_assessment = db.query(FitnessAssessment).filter(
        FitnessAssessment.user_id == st.session_state.user_id
    ).first()

    # -----------------------------------------------------------------
    # Initialize wizard state once, pre-filled from anything already saved
    # -----------------------------------------------------------------
    if "wiz_step" not in st.session_state:
        st.session_state.wiz_step = 0

    if "wiz_answers" not in st.session_state:
        defaults = {
            "full_name": user.full_name or "",
            "gender": user.gender or "Male",
            "age": user.age or 25,
            "weight": user.weight or 70.0,
            "height": user.height or 170.0,
        }
        if existing_assessment:
            defaults.update({
                "current_fitness_level": existing_assessment.current_fitness_level or "Beginner",
                "workout_experience": existing_assessment.workout_experience or "Less than 6 months",
                "target_weight": existing_assessment.target_weight or 70.0,
                "goal_timeline": existing_assessment.goal_timeline or "3 months",
                "workout_days_per_week": str(existing_assessment.workout_days_per_week or 3),
                "workout_duration": str(existing_assessment.workout_duration or 45),
                "equipment_access": existing_assessment.equipment_access or "Full Gym",
                "workout_frequency": existing_assessment.workout_frequency or "Lightly Active",
                "medical_conditions": existing_assessment.medical_conditions or "",
                "preferred_meals": existing_assessment.preferred_meals or "Non-Vegetarian",
                "cuisine_preference": existing_assessment.cuisine_preference or "Indian",
                "food_restrictions": existing_assessment.food_restrictions or "",
                "body_build": existing_assessment.body_build or "Not specified",
                "stress_level": existing_assessment.stress_level or "Moderate",
            })
        st.session_state.wiz_answers = defaults

    answers = st.session_state.wiz_answers
    step_idx = st.session_state.wiz_step

    def go_next():
        st.session_state.wiz_step += 1
        st.rerun()

    def go_back():
        if st.session_state.wiz_step > 0:
            st.session_state.wiz_step -= 1
            st.rerun()

    def save_all():
        user.full_name = answers["full_name"].strip() or user.full_name
        user.gender = answers["gender"]
        user.age = int(answers["age"])
        user.weight = float(answers["weight"])
        user.height = float(answers["height"])
        st.session_state.username = user.full_name

        assessment = existing_assessment
        if not assessment:
            assessment = FitnessAssessment(user_id=st.session_state.user_id)
            db.add(assessment)

        assessment.current_fitness_level = answers["current_fitness_level"]
        assessment.workout_experience = answers["workout_experience"]
        assessment.target_weight = float(answers["target_weight"])
        assessment.goal_timeline = answers["goal_timeline"]
        assessment.workout_days_per_week = int(answers["workout_days_per_week"])
        assessment.workout_duration = int(answers["workout_duration"])
        assessment.equipment_access = answers["equipment_access"]
        assessment.workout_frequency = answers["workout_frequency"]
        assessment.medical_conditions = answers["medical_conditions"].strip() or "None"
        assessment.food_restrictions = answers["food_restrictions"].strip() or "None"
        assessment.preferred_meals = answers["preferred_meals"]
        assessment.cuisine_preference = answers["cuisine_preference"]
        assessment.body_build = None if answers["body_build"] == "Not specified" else answers["body_build"]
        assessment.stress_level = answers["stress_level"]
        db.commit()

    # -----------------------------------------------------------------
    # Progress bar + back button
    # -----------------------------------------------------------------
    progress_pct = int((step_idx / TOTAL_STEPS) * 100)
    st.markdown(
        f"""
        <div class="wizard-progress-track">
            <div class="wizard-progress-fill" style="width:{progress_pct}%;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if step_idx > 0:
        with st.container():
            st.markdown('<div class="wizard-nav-back">', unsafe_allow_html=True)
            if st.button("← Back", key="wiz_back"):
                go_back()
            st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # Render current step
    # -----------------------------------------------------------------
    if step_idx < len(STEPS):
        step = STEPS[step_idx]

        if step_idx < 5:
            section_label = "PERSONAL INFORMATION"
        elif step_idx < 8:
            section_label = "FITNESS INFORMATION"
        elif step_idx < 14:
            section_label = "YOUR GOALS & TRAINING PLAN"
        elif step_idx < 17:
            section_label = "DIETARY INFORMATION"
        else:
            section_label = "PREFERENCES"

        st.markdown(
            f'<div class="wizard-step-label">STEP {step_idx + 1} OF {TOTAL_STEPS} · {section_label}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="wizard-question">{step["label"]}</div>', unsafe_allow_html=True)

        if step["type"] == "choice":
            current_value = str(answers.get(step["key"], ""))
            for option in step["options"]:
                label = f"{option} {step['suffix']}" if step.get("suffix") else option
                is_selected = (option == current_value)
                if st.button(
                    label,
                    key=f"choice_{step['key']}_{option}",
                    type="primary" if is_selected else "secondary",
                    width="stretch",
                ):
                    answers[step["key"]] = option
                    go_next()

        elif step["type"] == "text":
            value = st.text_input(
                step["label"], value=answers.get(step["key"], ""),
                placeholder=step.get("placeholder", ""), label_visibility="collapsed",
            )
            if st.button("Continue →", type="primary", width="stretch"):
                if not value.strip():
                    st.error("Please enter a value to continue.")
                else:
                    answers[step["key"]] = value
                    go_next()

        elif step["type"] == "number":
            value = st.number_input(
                step["label"], min_value=step["min"], max_value=step["max"],
                value=answers.get(step["key"], step["default"]),
                step=step["step"], label_visibility="collapsed",
            )
            if step.get("suffix"):
                st.caption(step["suffix"])
            if st.button("Continue →", type="primary", width="stretch"):
                answers[step["key"]] = value
                go_next()

        elif step["type"] == "text_area":
            value = st.text_area(
                step["label"], value=answers.get(step["key"], ""),
                placeholder=step.get("placeholder", ""), label_visibility="collapsed",
            )
            if st.button("Continue →", type="primary", width="stretch"):
                answers[step["key"]] = value
                go_next()

    else:
        # ---------------------------------------------------------
        # Final review + save
        # ---------------------------------------------------------
        st.markdown(
            f'<div class="wizard-step-label">STEP {TOTAL_STEPS} OF {TOTAL_STEPS} · REVIEW</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="wizard-question"></div>', unsafe_allow_html=True)
        st.write("Review your answers below, then save to generate your AI plans.")

        review_groups = [
            ("Personal Information", STEPS[0:5]),
            ("Fitness Information", STEPS[5:8]),
            ("Your Goals & Training Plan", STEPS[8:14]),
            ("Dietary Information", STEPS[14:17]),
            ("Preferences", STEPS[17:]),
        ]
        for group_title, group_steps in review_groups:
            if not group_steps:
                continue
            with st.expander(group_title, expanded=True):
                for s in group_steps:
                    val = answers.get(s["key"], "—")
                    suffix = f" {s['suffix']}" if s.get("suffix") and val not in ("", "—") else ""
                    st.markdown(f"**{s['label']}**  \n{val}{suffix}")

        if not st.session_state.get("wiz_saved", False):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✓ Save Assessment", type="primary", width="stretch"):
                    save_all()
                    st.session_state.wiz_saved = True
                    st.rerun()
            with col2:
                if st.button("Start Over", width="stretch"):
                    st.session_state.wiz_step = 0
                    del st.session_state.wiz_answers
                    st.rerun()
        else:
            st.success("Assessment saved successfully! You can now generate AI plans.")
            if st.button("Go to Home →", type="primary", width="stretch"):
                del st.session_state.wiz_saved
                st.switch_page("pages/home.py")
finally:
    db.close()