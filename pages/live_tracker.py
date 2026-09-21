import os
import time
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from streamlit_webrtc import webrtc_streamer, WebRtcMode

from services.state.session_defaults import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
from services.ui.style_loader import load_css, inject_local_font, inject_webrtc_styles
from services.ui.components import page_header, section_header, badge
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update, save_unfinished_progress, record_guided_reps
from services.live_workout_service import get_users_exercises
from services.workout_service import get_workout_plan
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import VoicePipeline, autoplay_audio

load_dotenv()

if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.warning("Please log in to view this page.")
    st.stop()

_static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
load_css(os.path.join(_static_dir, "style.css"))
load_css(os.path.join(_static_dir, "live_tracker.css"))
inject_local_font(os.path.join(_static_dir, "AdobeClean.otf"), "AdobeClean")

initial_session_defaults()

if "voice_pipeline" not in st.session_state:
    try:
        api_key = os.environ.get("GROQ_API_KEY", "")

        if not api_key and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            api_key = st.secrets["GROQ_API_KEY"]

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to a .env file "
                "(GROQ_API_KEY=your_key) or to .streamlit/secrets.toml."
            )

        groq_client = Groq(api_key=api_key)
        llm_coach = LLMCoach(groq_client)
        tts = TextToSpeech()
        st.session_state.voice_pipeline = VoicePipeline(llm_coach, tts)
    except Exception as e:
        st.session_state.voice_pipeline = None
        st.error(f"🔇 Voice coach disabled: {e}")

workout_started = st.session_state.get("workout_started", False)

page_header(
    "Live AI Gym Coach",
    subtitle="Real-time pose detection with proactive AI voice coaching.",
    tag_label="Live · Real-Time · Pose Coaching",
)

# ---------------------------------------------------------------------------
# Planned workout integration
# ---------------------------------------------------------------------------
def _normalize_exercise_name(name):
    """Match common AI-plan exercise names to the live pose detectors."""
    value = (name or "").strip().lower()
    aliases = {
        "squat": "Squats", "squats": "Squats",
        "push up": "Push-ups", "push-up": "Push-ups", "push ups": "Push-ups", "push-ups": "Push-ups",
        "biceps curl": "Biceps Curls (Dumbbell)", "biceps curls": "Biceps Curls (Dumbbell)",
        "dumbbell biceps curl": "Biceps Curls (Dumbbell)", "dumbbell curls": "Biceps Curls (Dumbbell)",
        "shoulder press": "Shoulder Press", "dumbbell shoulder press": "Shoulder Press",
        "lunge": "Lunges", "lunges": "Lunges",
    }
    if value in aliases:
        return aliases[value]
    for option in EXERCISE_OPTIONS:
        if value == option.lower():
            return option
    # Keep every AI-generated exercise available to the Live Coach. Exercises
    # without a dedicated pose detector run in Guided mode with the camera,
    # skeleton tracking, AI voice coaching and manual rep controls.
    return (name or "Exercise").strip()

def _parse_int(value, default):
    try:
        import re
        match = re.search(r"\d+", str(value))
        return int(match.group()) if match else default
    except Exception:
        return default

planned_workout = get_workout_plan(st.session_state.user_id) or {}
planned_days = [
    (day, details) for day, details in planned_workout.items()
    if (details.get("WorkoutType") or "").lower() != "rest" and details.get("Exercises")
]

# ---------------------------------------------------------------------------
# Session setup / control panel.
# ---------------------------------------------------------------------------
if not workout_started:
    if planned_days:
        section_header("Your Exercise Planner", hint="Choose an exercise from your AI-generated plan and perform it with the Live Coach.")
        day_names = [day for day, _ in planned_days]
        selected_day = st.selectbox("Workout Day", day_names, key="live_plan_day")
        selected_details = dict(planned_days)[selected_day]
        planned_exercises = selected_details.get("Exercises") or []

        st.markdown('<div class="tr-live-panel">', unsafe_allow_html=True)
        st.markdown('<div class="tr-live-panel-title">Exercises from Your Plan</div>', unsafe_allow_html=True)
        for index, item in enumerate(planned_exercises, start=1):
            raw_name = item.get("Exercise", "Exercise")
            live_name = _normalize_exercise_name(raw_name)
            sets = _parse_int(item.get("Sets"), 3)
            reps = _parse_int(item.get("Reps"), 10)
            c1, c2 = st.columns([4, 1])
            supported_pose_tracking = live_name in EXERCISE_OPTIONS
            with c1:
                tracking_label = "Live AI pose tracking" if supported_pose_tracking else "Guided mode · camera + AI coaching + manual rep tracking"
                st.markdown(f"**{index}. {raw_name}**  \n{sets} sets × {reps} reps · {tracking_label}")
            with c2:
                if st.button("Start", key=f"start_planned_{selected_day}_{index}", width="stretch", type="primary"):
                    st.session_state.exercise_type = live_name
                    st.session_state.target_sets = sets
                    st.session_state.reps_per_set = reps
                    st.session_state.plan_exercise = live_name
                    st.session_state.plan_sets = sets
                    st.session_state.plan_reps = reps
                    st.session_state.reps = 0
                    st.session_state.current_set_reps = 0
                    st.session_state.sets_completed = 0
                    st.session_state.workout_completed = False
                    st.session_state.workout_started = True
                    st.session_state.tracking_mode = "pose" if supported_pose_tracking else "guided"
                    st.session_state.set_cycle_started_at = time.time()
                    st.session_state.last_saved_sets_completed = 0
                    st.session_state.last_notified_sets_completed = 0
                    st.session_state.last_notified_workout_complete = False
                    st.session_state.active_planned_day = selected_day
                    st.session_state.active_planned_exercise = index - 1
                    if st.session_state.voice_pipeline:
                        result = st.session_state.voice_pipeline.process_event(
                            event="workout_started", exercise=live_name, metrics={"tracking_mode": st.session_state.tracking_mode}
                        )
                        if result:
                            st.session_state.audio_to_play, st.session_state.coach_feedback = result
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

# ---------------------------------------------------------------------------
# Session setup / control panel.
# (This used to live in st.sidebar, but the sidebar is hidden app-wide in
# favor of top-right menu navigation, so the controls are now a proper part
# of the page layout instead of being invisible.)
# ---------------------------------------------------------------------------
if not workout_started:
    st.markdown('<div class="tr-live-panel">', unsafe_allow_html=True)
    st.markdown('<div class="tr-live-panel-title">Set Your Workout Plan</div>', unsafe_allow_html=True)

    p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
    with p1:
        plan_exercise = st.selectbox("Exercise", options=EXERCISE_OPTIONS, key="plan_exercise")
    with p2:
        plan_sets = st.number_input("Sets", min_value=0, max_value=50, key="plan_sets", step=1)
    with p3:
        plan_reps = st.number_input("Reps per Set", min_value=0, max_value=50, key="plan_reps", step=1)
    with p4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        start_session_button = st.button("Start Workout", width="stretch", key="start_session_button", type="primary")
    st.markdown('</div>', unsafe_allow_html=True)

    if start_session_button:
        st.session_state.exercise_type = plan_exercise
        st.session_state.target_sets = int(plan_sets)
        st.session_state.reps_per_set = int(plan_reps)
        st.session_state.reps = 0
        st.session_state.current_set_reps = 0
        st.session_state.sets_completed = 0
        st.session_state.workout_completed = False
        st.session_state.tracking_mode = "pose"
        st.session_state.workout_started = True
        st.session_state.set_cycle_started_at = time.time()
        st.session_state.last_saved_sets_completed = 0

        if st.session_state.voice_pipeline:
            result = st.session_state.voice_pipeline.process_event(
                event="workout_started", exercise=plan_exercise, metrics={}
            )
            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result

        st.session_state.last_notified_sets_completed = 0
        st.session_state.last_notified_workout_complete = False
        st.rerun()
else:
    exercise = st.session_state.get("exercise_type")
    sets = st.session_state.get("target_sets")
    reps = st.session_state.get("reps_per_set")

    header_l, header_r = st.columns([3, 1])
    with header_l:
        st.markdown(
            f'<div class="tr-live-header">'
            f'{badge("Live", "live")}'
            f'<span style="color:var(--text);font-weight:700;font-size:1.05rem;">{exercise}</span>'
            f'<span style="color:var(--muted);font-size:0.9rem;">{sets} Sets · {reps} Reps</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with header_r:
        end_session_button = st.button("End Workout", key="end_session_button", width="stretch")

    if end_session_button:
        st.session_state.workout_started = False
        save_unfinished_progress()

        if st.session_state.voice_pipeline:
            result = st.session_state.voice_pipeline.process_event(
                event="workout_completed", exercise=exercise, metrics={}
            )
            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result

        st.rerun()

    # --- Rep / set readout ---
    total_reps = st.session_state.get("reps")
    current_set_reps = st.session_state.get("current_set_reps")
    reps_per_set = st.session_state.get("reps_per_set")
    sets_completed = st.session_state.get("sets_completed")
    target_sets = st.session_state.get("target_sets")

    # Every exercise in the AI plan can be performed with the Live Coach.
    # Exercises that do not yet have a dedicated rep detector use guided mode.
    if exercise not in EXERCISE_OPTIONS:
        st.info("Guided Live Coach mode: keep the camera on for live coaching and use the controls below to record each rep/set.")
        g1, g2 = st.columns(2)
        with g1:
            if st.button("+ 1 Rep", key="guided_add_rep", width="stretch", type="primary"):
                record_guided_reps(1)
                st.rerun()
        with g2:
            remaining = max((reps_per_set or 0) - (current_set_reps or 0), 1)
            if st.button("Complete Current Set", key="guided_complete_set", width="stretch"):
                record_guided_reps(remaining)
                st.rerun()

    st.markdown(
        f'''
        <div class="tr-readout-row">
            <div class="tr-readout">
                <div class="tr-readout-value">{total_reps}</div>
                <div class="tr-readout-label">Total Reps</div>
            </div>
            <div class="tr-readout">
                <div class="tr-readout-value">{current_set_reps} / {reps_per_set}</div>
                <div class="tr-readout-label">Current Set</div>
            </div>
            <div class="tr-readout">
                <div class="tr-readout-value">{sets_completed} / {target_sets}</div>
                <div class="tr-readout-label">Sets Completed</div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # --- Form-quality metrics (per exercise, same fields as before) ---
    FORM_METRICS = {
        "Squats": [
            ("knee_angle", "Knee Angle", "°"),
            ("back_angle", "Back Angle", "°"),
            ("depth_status", "Depth", ""),
        ],
        "Push-ups": [
            ("elbow_angle", "Elbow Angle", "°"),
            ("body_alignment", "Body Alignment", ""),
            ("hip_status", "Hip Position", ""),
        ],
        "Biceps Curls (Dumbbell)": [
            ("elbow_angle", "Elbow Angle", "°"),
            ("shoulder_status", "Shoulder Stability", ""),
            ("swing_status", "Swing Detection", ""),
        ],
        "Shoulder Press": [
            ("elbow_angle", "Elbow Angle", "°"),
            ("extension_status", "Arm Extension", ""),
            ("back_arch_status", "Back Arch", ""),
        ],
        "Lunges": [
            ("front_knee_angle", "Front Knee Angle", "°"),
            ("torso_angle", "Torso Angle", "°"),
            ("balance_status", "Balance", ""),
        ],
    }

    if exercise in FORM_METRICS:
        section_header("Form")
        metric_cells = []
        for key, label, suffix in FORM_METRICS[exercise]:
            value = st.session_state.get(key, "N/A")
            display = f"{value}{suffix}" if suffix else value
            metric_cells.append(
                f'<div class="tr-form-metric">'
                f'<span class="tr-form-metric-label">{label}</span>'
                f'<span class="tr-form-metric-value">{display}</span>'
                f'</div>'
            )
        st.markdown(f'<div class="tr-form-grid">{"".join(metric_cells)}</div>', unsafe_allow_html=True)

if st.session_state.get("audio_to_play"):
    autoplay_audio(st.session_state.audio_to_play)

if st.session_state.get("coach_feedback"):
    st.markdown("")
    st.success(f"🤖 **Coach:** {st.session_state.coach_feedback}")

if not workout_started:
    st.markdown(
        """
        <div class="trainora-empty-state">
            <h2>👆 Set your workout plan</h2>
            <p>
                Choose your exercise, sets and reps above,<br>
                then click <strong>Start Workout</strong> to activate the camera and AI coach.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown('<div class="tr-camera-frame">', unsafe_allow_html=True)
    context = webrtc_streamer(
        key="exercise-analysis",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=VideoProcessorClass,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    sync_metrics_update(context)

    if context.state.playing:
        time.sleep(0.25)
        st.rerun()
    else:
        save_unfinished_progress()

    inject_webrtc_styles()

section_header("Live Session History")

history_rows = get_users_exercises(st.session_state.user_id)

arr = [
    {
        "Exercise": row.exercise_name,
        "Reps": row.reps,
        "Sets": row.sets,
        "Time (sec)": row.time_seconds,
        "Date": row.created_at,
    }
    for row in history_rows
]

df = pd.DataFrame(arr)

st.markdown('<div class="tr-history-wrap">', unsafe_allow_html=True)
if not df.empty:
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    agg_df = df.groupby(["Exercise", "Date"]).agg({
        "Reps": "sum",
        "Sets": "sum",
        "Time (sec)": "sum",
    }).reset_index()
    agg_df.index += 1
    st.table(agg_df)
else:
    st.info("No live-tracked workout history found yet.")
st.markdown('</div>', unsafe_allow_html=True)
