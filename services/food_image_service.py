"""Database-backed food image registry, independent from the Diet Planner UI."""
from __future__ import annotations
import json, re
from functools import lru_cache
from pathlib import Path
from database.db import SessionLocal
from database.models import FoodImage

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_IMAGE_DIR = _PROJECT_ROOT / "static" / "food_images"
_MANIFEST_PATH = _IMAGE_DIR / "food_image_map.json"

def _canonical_name(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())

@lru_cache(maxsize=1)
def load_manifest() -> dict[str, str]:
    try:
        with _MANIFEST_PATH.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {_canonical_name(k): str(v).strip() for k,v in raw.items() if str(k).strip() and str(v).strip()}

def sync_food_image_manifest() -> int:
    """Upsert valid manifest mappings into the database."""
    manifest=load_manifest()
    if not manifest: return 0
    db=SessionLocal()
    try:
        active=0
        for food_name, filename in manifest.items():
            if not (_IMAGE_DIR/filename).is_file(): continue
            rel=f"static/food_images/{filename}"
            row=db.query(FoodImage).filter(FoodImage.food_name==food_name).first()
            if row is None:
                row=FoodImage(food_name=food_name,image_path=rel,image_filename=filename,source="manifest",is_active=True)
                db.add(row)
            else:
                row.image_path=rel; row.image_filename=filename; row.source="manifest"; row.is_active=True
            active+=1
        db.query(FoodImage).filter(~FoodImage.food_name.in_(list(manifest.keys()))).update({"is_active":False},synchronize_session=False)
        db.commit()
        return active
    finally: db.close()

def image_path_for_food(food_name: str) -> str | None:
    """Return an absolute path only when the DB mapping and file both exist."""
    canonical=_canonical_name(food_name)
    if not canonical: return None
    db=SessionLocal()
    try:
        row=db.query(FoodImage).filter(FoodImage.food_name==canonical,FoodImage.is_active.is_(True)).first()
        if row is None: return None
        path=_PROJECT_ROOT/row.image_path
        return str(path) if path.is_file() else None
    finally: db.close()

def image_registry_stats() -> dict[str,int]:
    db=SessionLocal()
    try:
        return {"total":db.query(FoodImage).count(),"active":db.query(FoodImage).filter(FoodImage.is_active.is_(True)).count()}
    finally: db.close()
