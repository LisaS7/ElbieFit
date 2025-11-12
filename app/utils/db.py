import os

import boto3
from boto3.dynamodb.types import TypeDeserializer

from app.utils.log import logger

PROJECT_NAME = os.getenv("PROJECT_NAME", "elbiefit")
REGION_NAME = os.getenv("REGION_NAME", "eu-west-2")
ENV = os.getenv("ENV", "dev")
TABLE_NAME = os.getenv("DDB_TABLE_NAME", f"{PROJECT_NAME}-{ENV}-table")

_dynamo = boto3.client("dynamodb", region_name=REGION_NAME)
_deser = TypeDeserializer()


def _unmarshal(item: dict) -> dict:
    return {k: _deser.deserialize(v) for k, v in item.items()}


def get_user_profile(user_sub: str) -> dict | None:
    """
    Fetch user profile from the database based on user_sub.
    """
    key = {
        "PK": {"S": f"USER#{user_sub}"},
        "SK": {"S": "PROFILE"},
    }

    # Use consistent read to ensure the data is up-to-date. This forces the db to use
    # the latest copy of the data rather than potentially stale replicas.
    response = _dynamo.get_item(
        TableName=TABLE_NAME,
        Key=key,
        ConsistentRead=True,
    )

    request_id = response.get("ResponseMetadata", {}).get("RequestId")
    profile = response.get("Item")

    if not profile:
        logger.warning(
            f"User profile not found. \nRequest id: {request_id} \nKey: {key}"
        )
        return None

    return _unmarshal(profile)
