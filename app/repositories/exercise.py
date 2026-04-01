from typing import List

from boto3.dynamodb.conditions import Key

from app.models.exercise import Exercise
from app.repositories.base import DynamoRepository
from app.repositories.errors import ExerciseRepoError, RepoError
from app.utils import db
from app.utils.log import logger


class DynamoExerciseRepository(DynamoRepository[Exercise]):
    """
    Implementation for DynamoExerciseRepository
    """

    def _to_model(self, item: dict):
        """
        Map a DynamoDB item (from the resource API) into an Exercise model.
        """
        try:
            return Exercise(**item)
        except Exception as e:
            logger.error(f"_to_model failed for exercise: {e}")
            raise ExerciseRepoError("Failed to create exercise model from item") from e

    def get_all_for_user(self, user_sub: str) -> List[Exercise]:
        """
        Return a list of exercises for this user
        """

        pk = db.build_user_pk(user_sub)

        try:
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk)
                & Key("SK").begins_with("EXERCISE#")
            )
        except RepoError as e:
            raise ExerciseRepoError("Failed to get all exercises for user") from e

        return [self._to_model(item) for item in items]

    def get_exercise_by_id(self, user_sub: str, exercise_id: str) -> Exercise | None:
        """
        Return a single exercise by its id for this user
        """

        pk = db.build_user_pk(user_sub)
        sk = db.build_exercise_sk(exercise_id)

        try:
            item = self._safe_get(Key={"PK": pk, "SK": sk})
        except RepoError as e:
            raise ExerciseRepoError("Failed to get exercise by id for user") from e

        if not item:
            return None

        return self._to_model(item)
