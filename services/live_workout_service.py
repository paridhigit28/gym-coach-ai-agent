from datetime import datetime, date
from database.db import SessionLocal
from database.models import LiveWorkoutSession


def add_exercise(user_id: int, exercise_name: str, reps: int, sets: int, time_seconds: float) -> None:
    """Upsert today's reps/sets/time totals for a user + exercise.

    Mirrors the behavior of Project 1's original raw-sqlite add_exercise():
    if a row already exists for this user/exercise/day, accumulate onto it;
    otherwise create a new row.
    """
    db = SessionLocal()
    try:
        today_start = datetime.combine(date.today(), datetime.min.time())

        existing = (
            db.query(LiveWorkoutSession)
            .filter(
                LiveWorkoutSession.user_id == user_id,
                LiveWorkoutSession.exercise_name == exercise_name,
                LiveWorkoutSession.created_at >= today_start,
            )
            .first()
        )

        if existing:
            existing.reps += reps
            existing.sets += sets
            existing.time_seconds += int(time_seconds)
        else:
            db.add(
                LiveWorkoutSession(
                    user_id=user_id,
                    exercise_name=exercise_name,
                    reps=reps,
                    sets=sets,
                    time_seconds=int(time_seconds),
                )
            )

        db.commit()
    finally:
        db.close()


def get_users_exercises(user_id: int):
    """Return all live-tracked workout rows for a user, most recent first."""
    db = SessionLocal()
    try:
        return (
            db.query(LiveWorkoutSession)
            .filter(LiveWorkoutSession.user_id == user_id)
            .order_by(LiveWorkoutSession.created_at.desc())
            .all()
        )
    finally:
        db.close()
