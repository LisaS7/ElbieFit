# Run using uv run python -m scripts.seed
from datetime import date
from decimal import Decimal

import boto3

from app.models import Exercise, UserProfile, Workout, WorkoutSet
from app.settings import settings
from app.utils.dates import now

TEST_USER_SUB = "e6b2d244-8091-70df-730d-3a2a1b855f0f"


def get_table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.REGION)
    return dynamodb.Table(settings.DDB_TABLE_NAME)  # type: ignore


def seed_profile(table):
    pk = f"USER#{TEST_USER_SUB}"
    ts = now()

    profile = UserProfile(
        PK=pk,
        SK="PROFILE",
        display_name="Lisa Test",
        email="lisa@example.com",
        created_at=ts,
        updated_at=ts,
        timezone="Europe/London",
    )

    table.put_item(Item=profile.to_ddb_item())
    print("Seeded profile for", profile.display_name)


def seed_exercises(table, pk: str):
    ts = now()
    exercises = [
        Exercise(
            PK=pk,
            SK="EXERCISE#PUSHUP",
            type="exercise",
            name="Push-up",
            muscles=["chest", "triceps", "shoulders"],
            equipment="bodyweight",
            category="push",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#ROW",
            type="exercise",
            name="Dumbbell Row",
            muscles=["lats", "upper_back", "biceps"],
            equipment="dumbbells",
            category="pull",
            created_at=ts,
            updated_at=ts,
        ),
        Exercise(
            PK=pk,
            SK="EXERCISE#SQUAT",
            type="exercise",
            name="Back Squat",
            muscles=["quads", "glutes", "hamstrings"],
            equipment="barbell",
            category="legs",
            created_at=ts,
            updated_at=ts,
        ),
    ]

    for ex in exercises:
        table.put_item(Item=ex.to_ddb_item())
    print(f"Seeded {len(exercises)} exercises")


def seed_workout_with_sets(table, pk: str):
    ts = now()

    workout = Workout(
        PK=pk,
        SK="WORKOUT#2025-11-04#W1",
        type="workout",
        date=date(2025, 11, 4),
        name="Workout A",
        tags=["push", "pull", "upper_body"],
        notes="Push/pull day",
        created_at=ts,
        updated_at=ts,
    )

    sets = [
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-04#W1#SET#001",
            type="set",
            exercise_id="PUSHUP",
            set_number=1,
            reps=12,
            weight_kg=Decimal(0.0),
            rpe=7,
            created_at=ts,
            updated_at=ts,
        ),
        WorkoutSet(
            PK=pk,
            SK="WORKOUT#2025-11-04#W1#SET#002",
            type="set",
            exercise_id="ROW",
            set_number=2,
            reps=10,
            weight_kg=Decimal(20.0),
            rpe=8,
            created_at=ts,
            updated_at=ts,
        ),
    ]

    table.put_item(Item=workout.to_ddb_item())
    for s in sets:
        table.put_item(Item=s.to_ddb_item())

    print(f"Seeded workout {workout.SK} with {len(sets)} sets")


def main():
    table = get_table()

    pk = f"USER#{TEST_USER_SUB}"

    # seed_profile(table)
    seed_exercises(table, pk)
    seed_workout_with_sets(table, pk)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Seeding failed:", e)
        raise
