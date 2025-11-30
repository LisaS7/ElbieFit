from datetime import date as DateType

import boto3

from app.settings import settings

REGION_NAME = settings.REGION
TABLE_NAME = settings.DDB_TABLE_NAME


def get_dynamo_resource():
    return boto3.resource("dynamodb", region_name=REGION_NAME)


def get_table():
    resource = get_dynamo_resource()
    return resource.Table(TABLE_NAME)  # type: ignore


def build_user_pk(user_sub: str) -> str:
    """
    Partition key for all user-owned items.
    Example: USER#abc-123
    """
    return f"USER#{user_sub}"


def build_workout_sk(workout_date: DateType, workout_id: str) -> str:
    """
    Build the SK for a workout item, e.g.:
    WORKOUT#2025-11-04#W1
    """
    return f"WORKOUT#{workout_date.isoformat()}#{workout_id}"


def build_set_sk(workout_date: DateType, workout_id: str, set_number: int) -> str:
    """
    Build the SK for a set item, e.g.:
    WORKOUT#2025-11-04#W1#SET#001
    """
    return f"{build_workout_sk(workout_date, workout_id)}#SET#{set_number:03d}"
