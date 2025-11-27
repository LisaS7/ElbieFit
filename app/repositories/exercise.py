from typing import List, Protocol

from boto3.dynamodb.conditions import Key

from app.models.exercise import Exercise
from app.utils import db


class ExerciseRepository(Protocol):
    def get_all_for_user(self, user_sub: str) -> List[Exercise]: ...

    # TODO:
    # create exercise
    # update exercise
    # delete exercise
    # get exercise by id


class DynamoExerciseRepository:
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

        pk = f"USER#{user_sub}"

        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with("EXERCISE#")
        )

        items = response.get("Items", [])
        exercises = [self._to_model(item) for item in items]

        return exercises
