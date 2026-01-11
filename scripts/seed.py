# Run using
# uv run python -m scripts.seed --dataset demo
# or
# uv run python -m scripts.seed --sub <demo sub> --dataset demo

import argparse

import boto3

from app.settings import settings
from app.utils.seed_data import (
    build_demo_profile,
    build_exercises,
    build_profile,
    build_workouts,
)

TEST_USER_SUB = "e6b2d244-8091-70df-730d-3a2a1b855f0f"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed DynamoDB user data")

    parser.add_argument(
        "--dataset",
        choices=["dev", "demo", "prod"],
        default="dev",
        help="Which dataset to seed",
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


def get_table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.REGION)
    return dynamodb.Table(settings.DDB_TABLE_NAME)  # type: ignore


def purge_user_items(table, pk: str):
    resp = table.query(
        KeyConditionExpression="PK = :pk", ExpressionAttributeValues={":pk": pk}
    )
    items = resp.get("Items", [])

    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

    print(f"Deleted {len(items)} items for {pk}")


def seed_profile(
    table, pk: str, dataset: str, *, display_name: str | None, email: str | None
):
    if dataset == "demo":
        profile = build_demo_profile(pk)
    elif dataset == "prod":
        if not display_name or not email:
            raise ValueError("prod seeding requires --display-name and --email")
        profile = build_profile(pk, display_name=display_name, email=email)
    else:
        profile = build_profile(pk)

    table.put_item(Item=profile.to_ddb_item())
    print("Seeded profile for", profile.display_name)


def seed_exercises(table, pk: str, dataset: str):
    exercises = build_exercises(pk, dataset)
    for ex in exercises:
        table.put_item(Item=ex.to_ddb_item())
    print(f"Seeded {len(exercises)} exercises")


def seed_workouts(table, pk: str, dataset: str):
    workouts = build_workouts(pk, dataset)
    for workout, sets in workouts:
        table.put_item(Item=workout.to_ddb_item())

        for s in sets:
            table.put_item(Item=s.to_ddb_item())
        print(f"Seeded workout {workout.SK} with {len(sets)} sets")


def main():
    args = parse_args()
    table = get_table()

    pk = f"USER#{args.sub}"

    if args.reset:
        if args.dataset == "demo":
            purge_user_items(table, pk)
        else:
            raise ValueError("Reset only allowed for demo profile")

    seed_profile(
        table, pk, args.dataset, display_name=args.display_name, email=args.email
    )
    seed_exercises(table, pk, args.dataset)

    if args.dataset in {"test", "demo"}:
        seed_workouts(table, pk, args.dataset)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Seeding failed:", e)
        raise
