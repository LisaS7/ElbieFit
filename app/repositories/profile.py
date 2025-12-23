from typing import Protocol

from app.models.profile import UserProfile
from app.repositories.base import DynamoRepository
from app.repositories.errors import ProfileRepoError, RepoError
from app.utils import db
from app.utils.log import logger


class ProfileRepository(Protocol):
    def get_for_user(self, user_sub: str) -> UserProfile | None: ...


class DynamoProfileRepository(DynamoRepository[UserProfile]):
    """
    Repository for the user profile
    """

    def __init__(self, table=None):
        self._table = table or db.get_table()

    def _to_model(self, item: dict) -> UserProfile:
        try:
            return UserProfile.model_validate(item)
        except Exception as e:
            logger.error(f"_to_model failed for profile: {e}")
            raise ProfileRepoError("Failed to create profile model from item") from e

    def get_for_user(self, user_sub: str) -> UserProfile | None:
        pk = db.build_user_pk(user_sub)
        key = {"PK": pk, "SK": "PROFILE"}

        try:
            item = self._safe_get(Key=key, ConsistentRead=True)
        except RepoError as e:
            logger.error(f"Repo error fetching profile for {user_sub}: {e}")
            raise ProfileRepoError("Failed to fetch profile from database") from e

        if not item:
            logger.warning(f"User profile not found for user_sub={user_sub}")
            return None

        return self._to_model(item)
