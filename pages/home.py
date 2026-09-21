import streamlit as st
import os as _os
from services.ui.style_loader import load_css, inject_local_font
from services.ui.components import (
    hero, section_header, stat_card, agent_card, image_to_base64,
)

_static_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "static")
load_css(_os.path.join(_static_dir, "style.css"))
inject_local_font(_os.path.join(_static_dir, "AdobeClean.otf"), "AdobeClean")

from database.db import SessionLocal
from database.models import User, FitnessAssessment

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.warning("Please log in to view this page.")
    st.stop()

db = SessionLocal()
try:
    user = db.query(User).filter(User.id == st.session_state.user_id).first()
    assessment = db.query(FitnessAssessment).filter(
        FitnessAssessment.user_id == st.session_state.user_id
    ).first()
finally:
    db.close()

profile_complete = bool(assessment and user.height and user.weight)
first_name = user.full_name.split()[0] if user.full_name else "there"

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
if profile_complete:
    sub = (
        f"Goal: {user.fitness_goal} · Target {assessment.target_weight} kg "
        f"in {assessment.goal_timeline}." if user.fitness_goal
        else f"Target {assessment.target_weight} kg in {assessment.goal_timeline}."
    )
else:
    sub = "Complete your profile to unlock personalized plans from all three AI agents."

hero(
    tag_label="Your Dashboard",
    greeting=f"Welcome back, {first_name}",
    sub=sub,
)

if not profile_complete:
    st.warning(
        "Your profile / fitness assessment isn't complete yet — some agents need it "
        "to build a personalized plan."
    )
    if st.button("Complete My Profile →", type="primary"):
        st.switch_page("pages/assessment.py")

# ---------------------------------------------------------------------------
# Status summary (quick stats)
# ---------------------------------------------------------------------------
if profile_complete:
    section_header("Your Current Status")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Current Weight", f"{user.weight:g}", "kg")
    with c2:
        stat_card("Target Weight", f"{assessment.target_weight:g}", "kg")
    with c3:
        stat_card("Fitness Level", assessment.current_fitness_level or "—")
    with c4:
        stat_card("Days / Week", str(assessment.workout_days_per_week or "—"))

# ---------------------------------------------------------------------------
# Three AI agent cards — logic unchanged, only the presentation is new.
# ---------------------------------------------------------------------------
section_header(" ")

AGENTS = [
    {
            "image": "diet-rabbit.png",
            "title": "AI Diet Planner",
            "desc": "Builds a daily meal plan with recipes and pictures matched to your diet preference and restrictions.",
            "page": "pages/diet.py",
            "cta": "Open Diet Planner",
            "featured": False,
        },
    {
        "image": "workout-mascot.png",
        "title": "AI Workout Planner",
        "desc": "Generates a personalized weekly workout plan based on your profile, goals and equipment access.",
        "page": "pages/workout.py",
        "cta": "Open Workout Planner",
        "featured": False,
    },
    
    {
        "image": "coach-mascot.png",
        "title": "Live AI Gym Coach",
        "desc": "Tracks your reps and form in real time through your camera, using your workout data as you train.",
        "page": "pages/live_tracker.py",
        "cta": "Open Live Coach",
        "featured": True,
    },
]

cols = st.columns(3, gap="medium")
for col, agent in zip(cols, AGENTS):
    with col:
        img_b64 = image_to_base64(_os.path.join(_static_dir, "images", agent["image"]))
        agent_card(img_b64, agent["title"], agent["desc"], featured=agent["featured"])
        btn_type = "primary" if agent["featured"] else "secondary"
        if st.button(agent["cta"], key=f"open_{agent['page']}", width="stretch", type=btn_type):
            st.switch_page(agent["page"])

# ---------------------------------------------------------------------------
# Quick actions
# ---------------------------------------------------------------------------
section_header("Quick Actions")
if st.button("Update My Profile", width="stretch"):
    st.switch_page("pages/assessment.py")

st.caption("Want to update your details? Use **My Profile** from the menu in the top-right corner any time.")
