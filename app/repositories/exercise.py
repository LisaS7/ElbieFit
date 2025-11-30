from typing import List, Protocol

from boto3.dynamodb.conditions import Key

from app.models.exercise import Exercise
from app.repositories.base import DynamoRepository
from app.repositories.errors import ExerciseRepoError
from app.utils import db


class ExerciseRepository(Protocol):
    def get_all_for_user(self, user_sub: str) -> List[Exercise]: ...

    # TODO:
    # create exercise
    # update exercise
    # delete exercise
    # get exercise by id


class DynamoExerciseRepository(DynamoRepository[Exercise]):
    """
    Implementation for DynamoExerciseRepository
    """

    def __init__(self, table=None):
        self._table = table or db.get_table()

    def _to_model(self, item: dict):
        """
        Map a DynamoDB item (from the resource API) into an Exercise model.
        """
        return Exercise(**item)

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
        except ExerciseRepoError:
            raise

        return [self._to_model(item) for item in items]
