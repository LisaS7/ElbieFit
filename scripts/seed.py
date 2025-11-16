# Run using uv run python -m scripts.seed

import boto3

from app.settings import settings
from scripts.seed_data import build_exercises, build_profile, build_workouts

TEST_USER_SUB = "e6b2d244-8091-70df-730d-3a2a1b855f0f"


def get_table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.REGION)
    return dynamodb.Table(settings.DDB_TABLE_NAME)  # type: ignore


def seed_profile(table):
    pk = f"USER#{TEST_USER_SUB}"

    profile = build_profile(pk)
    table.put_item(Item=profile.to_ddb_item())
    print("Seeded profile for", profile.display_name)


def seed_exercises(table, pk: str):

    exercises = build_exercises(pk)
    for ex in exercises:
        table.put_item(Item=ex.to_ddb_item())
    print(f"Seeded {len(exercises)} exercises")


def seed_workouts(table, pk: str):
    workouts = build_workouts(pk)
    for workout, sets in workouts:
        table.put_item(Item=workout.to_ddb_item())

        for s in sets:
            table.put_item(Item=s.to_ddb_item())
        print(f"Seeded workout {workout.SK} with {len(sets)} sets")


def main():
    table = get_table()

    pk = f"USER#{TEST_USER_SUB}"

    seed_profile(table)
    seed_exercises(table, pk)
    seed_workouts(table, pk)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Seeding failed:", e)
        raise
