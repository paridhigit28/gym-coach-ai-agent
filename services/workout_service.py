from database.db import SessionLocal
from database.models import WorkoutPlan
import json

def save_workout_plan(user_id: int, plan_dict: dict):
    db = SessionLocal()
    try:
        # Check if plan already exists and update, or create new
        existing_plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).first()
        if existing_plan:
            existing_plan.plan_data = json.dumps(plan_dict)
        else:
            new_plan = WorkoutPlan(user_id=user_id, plan_data=json.dumps(plan_dict))
            db.add(new_plan)
        db.commit()
    finally:
        db.close()

def get_workout_plan(user_id: int):
    db = SessionLocal()
    try:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).first()
        if plan:
            return json.loads(plan.plan_data)
        return None
    finally:
        db.close()
