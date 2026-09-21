from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from database.db import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    height = Column(Float, nullable=True)  # in cm or m, keep consistent
    weight = Column(Float, nullable=True)  # in kg
    activity_level = Column(String(50), nullable=True)
    fitness_goal = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessments = relationship("FitnessAssessment", back_populates="user", cascade="all, delete-orphan")
    workout_plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan")
    diet_plans = relationship("DietPlan", back_populates="user", cascade="all, delete-orphan")
    progress_logs = relationship("ProgressLog", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    ai_insights = relationship("AiInsight", back_populates="user", cascade="all, delete-orphan")
    water_logs = relationship("WaterTracking", back_populates="user", cascade="all, delete-orphan")
    step_logs = relationship("StepTracking", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    live_workout_sessions = relationship("LiveWorkoutSession", back_populates="user", cascade="all, delete-orphan")

class FitnessAssessment(Base):
    __tablename__ = "fitness_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    current_fitness_level = Column(String(50))
    workout_frequency = Column(String(50))
    workout_experience = Column(String(50))
    target_weight = Column(Float)
    goal_timeline = Column(String(50))
    workout_days_per_week = Column(Integer)
    workout_duration = Column(Integer)  # in minutes
    equipment_access = Column(String(100))
    medical_conditions = Column(Text)
    food_restrictions = Column(Text)
    preferred_meals = Column(Text)
    cuisine_preference = Column(String(50))
    # Optional body-build personalization used by the diet planner.
    body_build = Column(String(50), nullable=True)
    water_intake = Column(Float) # target in liters
    sleep_duration = Column(Float) # target in hours
    stress_level = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="assessments")

class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_data = Column(Text)  # JSON stored as string
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="workout_plans")

class DietPlan(Base):
    __tablename__ = "diet_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_data = Column(Text)  # JSON stored as string
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="diet_plans")

class ProgressLog(Base):
    __tablename__ = "progress_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=datetime.utcnow)
    weight = Column(Float)
    chest = Column(Float, nullable=True)
    waist = Column(Float, nullable=True)
    hip = Column(Float, nullable=True)
    arms = Column(Float, nullable=True)
    thighs = Column(Float, nullable=True)
    workout_completed = Column(Boolean, default=False)
    calories_consumed = Column(Integer, nullable=True)
    water_intake = Column(Float, nullable=True)  # in liters
    steps = Column(Integer, nullable=True)
    sleep_hours = Column(Float, nullable=True)

    user = relationship("User", back_populates="progress_logs")

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(20))  # 'user' or 'model'
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_history")

class AiInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    report_type = Column(String(50)) # 'weekly', 'monthly'
    insight_data = Column(Text) # JSON stored as string
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ai_insights")

class WaterTracking(Base):
    __tablename__ = "water_tracking"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=datetime.utcnow)
    amount_liters = Column(Float)

    user = relationship("User", back_populates="water_logs")

class StepTracking(Base):
    __tablename__ = "step_tracking"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=datetime.utcnow)
    step_count = Column(Integer)

    user = relationship("User", back_populates="step_logs")

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    report_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reports")

class LiveWorkoutSession(Base):
    """Rep/set/time totals logged by the real-time AI pose-tracking coach.

    One row per (user, exercise, day) — reps/sets/time accumulate onto the
    same row across a day via upsert, mirroring the original raw-sqlite
    'exercises' table from the live-tracking module, now backed by the
    shared SQLAlchemy schema instead of a separate database file.
    """
    __tablename__ = "live_workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exercise_name = Column(String(100), nullable=False)
    reps = Column(Integer, nullable=False, default=0)
    sets = Column(Integer, nullable=False, default=0)
    time_seconds = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="live_workout_sessions")


class FoodImage(Base):
    """Canonical food-image registry.

    Nutrition/food data and image files stay separate: this table stores the
    stable mapping from a canonical food name to the relative path of its
    image file. The UI reads this registry; image generation/matching can be
    updated independently by syncing the manifest.
    """
    __tablename__ = "food_images"

    id = Column(Integer, primary_key=True, index=True)
    food_name = Column(String(255), unique=True, nullable=False, index=True)
    image_path = Column(String(500), nullable=False)
    image_filename = Column(String(255), nullable=True)
    source = Column(String(100), nullable=True, default="local")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)