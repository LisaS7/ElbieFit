# Run using
# uv run python -m scripts.seed \
#  --sub "<cognito sub>" \
#  --display-name "Lisa" \
#  --email "your@email"

import argparse

from boto3.dynamodb.conditions import Key

from app.utils.db import get_table
from app.utils.seed_data import (
    build_exercises,
    build_profile,
    build_workouts,
)

TEST_USER_SUB = "e6b2d244-8091-70df-730d-3a2a1b855f0f"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed DynamoDB user data")

    parser.add_argument(
        "--sub",
        default=None,
        help="Cognito user sub to seed data for",
    )

    parser.add_argument(
        "--display-name",
        default=None,
        help="Display name for profile (prod recommended)",
    )

    parser.add_argument(
        "--email",
        default=None,
        help="Email for profile (prod recommended)",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing items for this user before seeding",
    )

    return parser.parse_args()


def purge_user_items(table, pk: str):
    resp = table.query(KeyConditionExpression=Key("PK").eq(pk))
    items = resp.get("Items", [])

    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

    print(f"Deleted {len(items)} items for {pk}")


def seed_profile(table, pk: str, *, display_name: str | None, email: str | None):
    if not display_name or not email:
        raise ValueError("prod seeding requires --display-name and --email")
    profile = build_profile(pk, display_name=display_name, email=email)

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
    args = parse_args()
    table = get_table()

    if args.sub:
        user_sub = args.sub
    else:
        user_sub = TEST_USER_SUB

    pk = f"USER#{user_sub}"

    if args.reset:
        purge_user_items(table, pk)

    seed_profile(table, pk, display_name=args.display_name, email=args.email)
    seed_exercises(table, pk)
    seed_workouts(table, pk)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Seeding failed:", e)
        raise
