from typing import List, Protocol

from boto3.dynamodb.conditions import Key

from app.models.workout import Workout, WorkoutSet
from app.utils import db


class WorkoutRepository(Protocol):
    def get_all_for_user(self, user_sub: str) -> List[Workout]: ...


class DynamoWorkoutRepository:
    """
    Implementation of WorkoutRepository
    """

    def __init__(self, table=None):
        self._table = table or db.get_table()

    def _to_model(self, item: dict):
        """
        Map a DynamoDB item (from the resource API) into a Workout model.
        """

        item_type = item.get("type")

        if item_type == "workout":
            return Workout(**item)

        if item_type == "set":
            return WorkoutSet(**item)

        raise ValueError(f"Unknown item type: {item_type}")

    def get_all_for_user(self, user_sub: str) -> List[Workout]:
        """
        Return only workout items, sorted by date desc, Sets are filtered out.
        """
        pk = f"USER#{user_sub}"

        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with("WORKOUT#")
        )

        items = response.get("Items", [])
        workouts = [
            self._to_model(item) for item in items if item.get("type") == "workout"
        ]
        # ignore type hint: we're filtering out sets in the previous step
        # so all items will have a date attribute
        workouts.sort(key=lambda w: w.date, reverse=True)  # type: ignore[arg-type]
        return workouts  # type: ignore[arg-type]
