"""Sync the independently maintained food-image manifest into the DB.

Run after an image-generation/matching job updates
static/food_images/food_image_map.json.
"""
from services.food_image_service import sync_food_image_manifest, image_registry_stats

if __name__ == "__main__":
    count = sync_food_image_manifest()
    print(f"Synced {count} active food-image mappings.")
    print(image_registry_stats())
