from typing import Protocol

from app.utils import db
from app.utils.log import logger


class ProfileRepository(Protocol):
    def get_for_user(self, user_sub: str) -> dict | None: ...


class DynamoProfileRepository:
    """
    Repository for the user profile
    """

    def __init__(self, table=None):
        self._table = table or db.get_table()

    def get_for_user(self, user_sub: str) -> dict | None:
        pk = db.build_user_pk(user_sub)

        key = {"PK": pk, "SK": "PROFILE"}
        response = self._table.get_item(Key=key, ConsistentRead=True)

        request_id = response.get("ResponseMetadata", {}).get("RequestId")
        profile = response.get("Item")

        if not profile:
            logger.warning(
                f"User profile not found. \nRequest id: {request_id} \nKey: {key}"
            )
            return None

        return profile
