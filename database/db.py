import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///fitness_app.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    from database import models
    Base.metadata.create_all(bind=engine)

    # Lightweight migration for existing SQLite databases. SQLAlchemy
    # create_all() does not add newly introduced columns to an existing table.
    if DATABASE_URL.startswith("sqlite"):
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        if "fitness_assessments" in inspector.get_table_names():
            columns = {c["name"] for c in inspector.get_columns("fitness_assessments")}
            if "body_build" not in columns:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            "ALTER TABLE fitness_assessments "
                            "ADD COLUMN body_build VARCHAR(50)"
                        )
                    )

    # Food images are stored as files, while this table keeps the canonical
    # food_name -> relative image path mapping. The manifest can be regenerated
    # independently of the UI and synced on startup.
    try:
        from services.food_image_service import sync_food_image_manifest
        sync_food_image_manifest()
    except Exception as exc:
        # Image registry must never prevent the rest of the application from
        # starting (for example when a deployment has no image assets yet).
        import logging
        logging.getLogger(__name__).warning(
            "Food-image registry sync skipped: %s", exc
        )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
