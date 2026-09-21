import streamlit as st
import time
from services.config.workout_config import METRICS_FIELDS
from services.live_workout_service import add_exercise


def save_unfinished_progress():
    """Persist reps done so far that haven't been saved yet.

    The normal save path (below) only writes to history when a full set is
    completed. If the user ends the workout early — mid-set, or with no
    reps_per_set target set at all — those reps would otherwise be lost.
    This saves them as a partial entry (reps counted, no extra full set).
    """
    exercise = st.session_state.get("exercise_type")
    user_id = st.session_state.get("user_id", 0)

    if not exercise:
        return

    reps = st.session_state.get("reps", 0) or 0
    reps_per_set = st.session_state.get("reps_per_set", 0) or 0
    last_saved_sets = st.session_state.get("last_saved_sets_completed", 0) or 0

    already_saved_reps = last_saved_sets * reps_per_set
    leftover_reps = reps - already_saved_reps

    if leftover_reps <= 0:
        return

    now_ts = time.time()
    started_at = st.session_state.get("set_cycle_started_at", now_ts)
    time_taken = now_ts - started_at

    # sets=0 because this is a partial/incomplete set, not a finished one
    add_exercise(user_id, exercise, leftover_reps, 0, time_taken)

    st.session_state.last_saved_sets_completed = last_saved_sets
    st.session_state.set_cycle_started_at = now_ts


def sync_metrics_update(context):
    if not context or not hasattr(context, "state") or not context.state.playing:
        return
    
    processor = getattr(context, "video_processor", None)

    if not processor:
        return 
    
    exercise = st.session_state.get("exercise_type")

    if not exercise:
        return
    
    processor.set_exercise(exercise)

    # Guided exercises intentionally do not have an automatic rep detector.
    # Keep the live camera running, but never overwrite user-confirmed reps.
    if exercise not in METRICS_FIELDS:
        return

    latest_metrics = processor.get_latest_metrics()

    if not latest_metrics:
        return
    
    reps = latest_metrics.get("reps", 0)

    if reps is None:
        reps = 0
        
    st.session_state.reps = reps

    fields = METRICS_FIELDS.get(exercise)

    if not fields:
        return 

    for key, default in fields.items():
        st.session_state[key] = latest_metrics.get(key, default)

    reps_per_set = st.session_state.get("reps_per_set", 0)
    target_sets = st.session_state.get("target_sets", 0)

    if reps is not None and reps_per_set > 0 and target_sets > 0:
        sets_completed = reps // reps_per_set
        current_set_reps = reps % reps_per_set
        workout_completed = sets_completed >= target_sets 
    else:
        sets_completed = 0
        current_set_reps = 0
        workout_completed = False

    st.session_state.sets_completed = sets_completed
    st.session_state.current_set_reps = current_set_reps
    st.session_state.workout_completed = workout_completed

    last_saved_sets = st.session_state.get("last_saved_sets_completed", 0)

    if target_sets > 0 and reps_per_set > 0 and sets_completed > last_saved_sets:
        newly_completed = sets_completed - last_saved_sets
        now_ts = time.time()
        started_at = st.session_state.get("set_cycle_started_at", now_ts)
        time_taken = now_ts - started_at
        user_id = st.session_state.get("user_id", 0)

        add_exercise(user_id, exercise, newly_completed * reps_per_set, newly_completed, time_taken)

        if st.session_state.get("voice_pipeline"):
            result = st.session_state.voice_pipeline.process_event(
                event="set_completed",
                exercise=exercise,
                metrics=latest_metrics,
            )

            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result

        st.session_state.set_cycle_started_at = now_ts
        st.session_state.last_saved_sets_completed = sets_completed

    if workout_completed and not st.session_state.get("last_notified_workout_complete", False):
        st.session_state.last_notified_workout_complete = True

        if st.session_state.get("voice_pipeline"):
            result = st.session_state.voice_pipeline.process_event(
                event="workout_completed",
                exercise=exercise,
                metrics=latest_metrics,
            )

            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result
                
    pose_detected = latest_metrics.get("pose_detected", True)
    
    if not pose_detected and st.session_state.get("voice_pipeline"):
        result = st.session_state.voice_pipeline.process_event(
            event="no_pose_detected",
            exercise=exercise,
            metrics={"issue": "No pose detected! Please step into the camera frame."},
        )
    
        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result

    if st.session_state.get("voice_pipeline"):
        result = st.session_state.voice_pipeline.process_event(
            event="ongoing_form_check",
            exercise=exercise,
            metrics=latest_metrics,
        )
        
        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result


def record_guided_reps(increment: int = 1):
    """Record reps for an AI-planned exercise without a dedicated pose counter.

    The camera and voice coach remain active; the user confirms completed reps
    so every exercise generated by the planner can be completed in Live Coach.
    """
    increment = max(int(increment or 0), 0)
    if increment <= 0:
        return

    exercise = st.session_state.get("exercise_type")
    user_id = st.session_state.get("user_id", 0)
    if not exercise:
        return

    previous_reps = int(st.session_state.get("reps", 0) or 0)
    new_reps = previous_reps + increment
    st.session_state.reps = new_reps

    reps_per_set = int(st.session_state.get("reps_per_set", 0) or 0)
    target_sets = int(st.session_state.get("target_sets", 0) or 0)
    sets_completed = new_reps // reps_per_set if reps_per_set > 0 else 0
    current_set_reps = new_reps % reps_per_set if reps_per_set > 0 else new_reps
    st.session_state.sets_completed = sets_completed
    st.session_state.current_set_reps = current_set_reps
    st.session_state.workout_completed = bool(target_sets > 0 and sets_completed >= target_sets)

    last_saved_sets = int(st.session_state.get("last_saved_sets_completed", 0) or 0)
    if reps_per_set > 0 and sets_completed > last_saved_sets:
        newly_completed = sets_completed - last_saved_sets
        now_ts = time.time()
        started_at = st.session_state.get("set_cycle_started_at", now_ts)
        add_exercise(
            user_id,
            exercise,
            newly_completed * reps_per_set,
            newly_completed,
            now_ts - started_at,
        )
        st.session_state.last_saved_sets_completed = sets_completed
        st.session_state.set_cycle_started_at = now_ts

        if st.session_state.get("voice_pipeline"):
            result = st.session_state.voice_pipeline.process_event(
                event="set_completed",
                exercise=exercise,
                metrics={"tracking_mode": "guided"},
            )
            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result

    if st.session_state.workout_completed and not st.session_state.get("last_notified_workout_complete", False):
        st.session_state.last_notified_workout_complete = True
        if st.session_state.get("voice_pipeline"):
            result = st.session_state.voice_pipeline.process_event(
                event="workout_completed",
                exercise=exercise,
                metrics={"tracking_mode": "guided"},
            )
            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result
