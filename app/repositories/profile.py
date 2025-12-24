from typing import Protocol

from app.models.profile import UserProfile
from app.repositories.base import DynamoRepository
from app.repositories.errors import ProfileRepoError, RepoError
from app.utils import db
from app.utils.dates import dt_to_iso, now
from app.utils.log import logger


class ProfileRepository(Protocol):
    def get_for_user(self, user_sub: str) -> UserProfile | None: ...
    def update_account(
        self, user_sub: str, *, display_name: str, timezone: str
    ) -> UserProfile: ...
    def update_preferences(
        self,
        user_sub: str,
        *,
        show_tips: bool,
        theme: str,
        units: str,
    ) -> UserProfile: ...


class DynamoProfileRepository(DynamoRepository[UserProfile]):
    """
    Repository for the user profile
    """

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

    def update_account(
        self, user_sub: str, *, display_name: str, timezone: str
    ) -> UserProfile:
        pk = db.build_user_pk(user_sub)
        key = {"PK": pk, "SK": "PROFILE"}

        try:
            resp = self._safe_update(
                Key=key,
                UpdateExpression="SET display_name = :dn, timezone = :tz, updated_at = :ua",
                ExpressionAttributeValues={
                    ":dn": display_name,
                    ":tz": timezone,
                    ":ua": dt_to_iso(now()),
                },
                ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
                ReturnValues="ALL_NEW",
            )
        except RepoError as e:
            logger.error(f"Repo error updating account user_sub={user_sub}: {e}")
            raise ProfileRepoError("Failed to update account fields") from e

        attrs = resp.get("Attributes")
        if not attrs:
            raise ProfileRepoError("Account update returned no attributes")

        return self._to_model(attrs)

    def update_preferences(
        self,
        user_sub: str,
        *,
        show_tips: bool,
        theme: str,
        units: str,
    ) -> UserProfile:
        pk = db.build_user_pk(user_sub)
        key = {"PK": pk, "SK": "PROFILE"}

        try:
            resp = self._safe_update(
                Key=key,
                UpdateExpression=(
                    "SET preferences.show_tips = :st, "
                    "preferences.theme = :th, "
                    "preferences.units = :un, "
                    "updated_at = :ua"
                ),
                ExpressionAttributeValues={
                    ":st": show_tips,
                    ":th": theme,
                    ":un": units,
                    ":ua": dt_to_iso(now()),
                },
                ConditionExpression="attribute_exists(PK) AND attribute_exists(SK)",
                ReturnValues="ALL_NEW",
            )
        except RepoError as e:
            logger.error(f"Repo error updating preferences user_sub={user_sub}: {e}")
            raise ProfileRepoError("Failed to update preferences") from e

        attrs = resp.get("Attributes")
        if not attrs:
            raise ProfileRepoError("Preferences update returned no attributes")

        return self._to_model(attrs)
