import time
from typing import Any

from botocore.exceptions import ClientError
from fastapi import HTTPException

from app.settings import settings
from app.utils.db import build_user_pk, get_table
from app.utils.log import logger
from app.utils.seed_data import build_demo_profile, build_exercises, build_workouts

# ─────────────────────────────────────────────────────────
# Cooldown
# ─────────────────────────────────────────────────────────


def enforce_cooldown(user_sub: str, cooldown_seconds: int) -> None:
    table = get_table()
    now = int(time.time())
    cutoff = now - cooldown_seconds

    pk = f"DEMO_RESET#{user_sub}"
    sk = "STATE"

    try:
        table.put_item(
            Item={"PK": pk, "SK": sk, "last_reset_at": now},
            ConditionExpression="attribute_not_exists(last_reset_at) OR last_reset_at <= :cutoff",
            ExpressionAttributeValues={":cutoff": cutoff},
        )

    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")

        if code == "ConditionalCheckFailedException":
            logger.info(f"Demo reset cooldown active for {user_sub}")
            raise HTTPException(
                status_code=429, detail="Demo reset is on cooldown. Try again soon."
            )

        logger.exception(f"Cooldown storage error for {user_sub}\n{code}")
        raise HTTPException(status_code=500, detail="Cooldown check failed.") from e


# ─────────────────────────────────────────────────────────
# Reset user data
# ─────────────────────────────────────────────────────────


def _purge_user_items(*, user_pk: str) -> int:
    """
    Delete ALL items for a given PK, handling pagination.

    Returns number of deleted items.
    """
    table = get_table()
    deleted = 0
    last_evaluated_key: dict[str, Any] | None = None

    while True:
        query_kwargs: dict[str, Any] = {
            "KeyConditionExpression": "PK = :pk",
            "ExpressionAttributeValues": {":pk": user_pk},
        }
        if last_evaluated_key:
            query_kwargs["ExclusiveStartKey"] = last_evaluated_key

        resp = table.query(**query_kwargs)
        items = resp.get("Items", []) or []

        if items:
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                    deleted += 1

        last_evaluated_key = resp.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return deleted


def reset_user(user_sub: str) -> None:
    """
    Reset demo user data:
    - Purge all items under USER#<sub>
    - Seed demo profile, exercises, workouts, sets

    Raises HTTPException(500) on failure.
    """

    if user_sub != settings.DEMO_USER_SUB:
        raise HTTPException(status_code=403, detail="Reset only allowed for demo user.")

    table = get_table()
    pk = build_user_pk(user_sub)

    try:
        deleted = _purge_user_items(user_pk=pk)
        logger.info(f"Purged {deleted} demo user items for user {user_sub}")

        # Seed demo profile
        profile = build_demo_profile(pk)
        table.put_item(Item=profile.to_ddb_item())

        # Seed exercises (deterministic IDs per dataset)
        exercises = build_exercises(pk, dataset="demo")
        for ex in exercises:
            table.put_item(Item=ex.to_ddb_item())

        # Seed workouts + sets
        workouts = build_workouts(pk, dataset="demo")
        for workout, sets in workouts:
            table.put_item(Item=workout.to_ddb_item())
            for s in sets:
                table.put_item(Item=s.to_ddb_item())

        logger.info(
            f"Seeded demo dataset for user {user_sub}\nExercises: {len(exercises)}\nWorkouts: {len(workouts)}\nSets: {sum(len(sets) for _, sets in workouts)}",
        )

    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        logger.exception(
            "Dynamo error during demo reset", extra={"sub": user_sub, "ddb_error": code}
        )
        raise HTTPException(status_code=500, detail="Demo reset failed.") from e

    except Exception as e:
        logger.exception("Unexpected error during demo reset", extra={"sub": user_sub})
        raise HTTPException(status_code=500, detail="Demo reset failed.") from e
