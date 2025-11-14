import boto3

from app.settings import settings
from app.utils.log import logger

REGION_NAME = settings.REGION
TABLE_NAME = settings.DDB_TABLE_NAME

_dynamo = boto3.resource("dynamodb", region_name=REGION_NAME)
_table = _dynamo.Table(TABLE_NAME)  # type: ignore


def get_dynamo_resource():
    return boto3.resource("dynamodb", region_name=REGION_NAME)


def get_table():
    resource = get_dynamo_resource
    return resource.Table(TABLE_NAME)


def get_user_profile(user_sub: str) -> dict | None:
    """
    Fetch user profile from the database based on user_sub.
    """
    key = {
        "PK": f"USER#{user_sub}",
        "SK": "PROFILE",
    }

    # Use consistent read to ensure the data is up-to-date. This forces the db to use
    # the latest copy of the data rather than potentially stale replicas.
    response = _table.get_item(
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

    return profile
