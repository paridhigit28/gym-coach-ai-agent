from database.db import SessionLocal
from database.models import DietPlan
import json

def save_diet_plan(user_id: int, plan_dict: dict):
    db = SessionLocal()
    try:
        existing_plan = db.query(DietPlan).filter(DietPlan.user_id == user_id).first()
        if existing_plan:
            existing_plan.plan_data = json.dumps(plan_dict)
        else:
            new_plan = DietPlan(user_id=user_id, plan_data=json.dumps(plan_dict))
            db.add(new_plan)
        db.commit()
    finally:
        db.close()

def get_diet_plan(user_id: int):
    db = SessionLocal()
    try:
        plan = db.query(DietPlan).filter(DietPlan.user_id == user_id).first()
        if plan:
            return json.loads(plan.plan_data)
        return None
    finally:
        db.close()
