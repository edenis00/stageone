"""
Seed the database with profiles from seed_profiles.json.
"""

import json
import sys
from pathlib import Path

# Ensure the project root is on sys.path so 'app' can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.session import SessionLocal, engine, Base
from app.models.profiles import Profile


def seed():
    # Ensure the table exists
    Base.metadata.create_all(bind=engine)

    seed_file = Path(__file__).resolve().parent / "seed_profiles.json"
    if not seed_file.exists():
        print(f"ERROR: {seed_file} not found.")
        sys.exit(1)

    with open(seed_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = data.get("profiles", [])
    if not profiles:
        print("No profiles found in seed file.")
        return

    db = SessionLocal()
    inserted = 0
    skipped = 0

    try:
        # Fetch all existing names in one query for efficiency
        existing_names = set(row[0] for row in db.query(Profile.name).all())

        for entry in profiles:
            name = entry["name"].strip().lower()

            if name in existing_names:
                skipped += 1
                continue

            profile = Profile(
                name=name,
                gender=entry.get("gender"),
                gender_probability=entry.get("gender_probability"),
                sample_size=entry.get("sample_size", 0),
                age=entry.get("age"),
                age_group=entry.get("age_group"),
                country_id=entry.get("country_id"),
                country_probability=entry.get("country_probability"),
            )
            db.add(profile)
            existing_names.add(name)  # track to avoid intra-batch dupes
            inserted += 1

        db.commit()
        print(f"Seed complete: {inserted} inserted, {skipped} skipped.")
    except Exception as e:
        db.rollback()
        print(f"ERROR during seeding: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
