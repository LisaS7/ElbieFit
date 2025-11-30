from datetime import date
from typing import List, Protocol

from boto3.dynamodb.conditions import Key

from app.models.workout import Workout, WorkoutSet
from app.utils import db


class WorkoutRepository(Protocol):
    def get_all_for_user(self, user_sub: str) -> List[Workout]: ...
    def create_workout(self, workout: Workout) -> Workout: ...
    def get_workout_with_sets(
        self, user_sub: str, workout_date: date, workout_id: str
    ) -> tuple[Workout, List[WorkoutSet]]: ...
    def update_workout(self, workout: Workout) -> Workout: ...
    def delete_workout(
        self, user_sub: str, workout_date: date, workout_id: str
    ) -> None: ...


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

    # ----------------------- Get -----------------------------

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

    def get_workout_with_sets(
        self, user_sub: str, workout_date: date, workout_id: str
    ) -> tuple[Workout, List[WorkoutSet]]:
        """
        Fetch a single workout and its sets for the given user/date/id
        """
        pk = f"USER#{user_sub}"
        sk = f"WORKOUT#{workout_date.isoformat()}#{workout_id}"

        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk)
        )
        items = response.get("Items", [])

        models = [self._to_model(item) for item in items]

        workout = [w for w in models if isinstance(w, Workout)]
        sets = [s for s in models if isinstance(s, WorkoutSet)]

        if not workout:
            raise KeyError("Workout not found")

        return workout[0], sets

    # ----------------------- Add -----------------------------

    def create_workout(self, workout: Workout) -> Workout:
        """
        Persist a new workout item to DynamoDB.
        Expects PK/SK/created_at/updated_at to be set on the model.
        """
        item = workout.to_ddb_item()
        self._table.put_item(Item=item)
        return workout

    # ----------------------- Update -----------------------------

    def update_workout(self, workout: Workout) -> Workout:
        """
        Persist changes to an existing workout.
        """

        item = workout.to_ddb_item()
        self._table.put_item(Item=item)
        return workout

    # ----------------------- Delete -----------------------------

    def delete_workout_and_sets(
        self, user_sub: str, workout_date: date, workout_id: str
    ) -> None:
        """
        Delete an existing workout.
        """
        pk = f"USER#{user_sub}"
        sk = f"WORKOUT#{workout_date}#{workout_id}"

        # Get everything beginning with this pk/sk combo
        # (so this includes sets belonging to the workout)
        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk)
        )
        items = response.get("Items", [])

        if not items:
            return

        # use batch_writer here to make bulk delete easier
        # batch_writer bundles into batches and auto retries unprocessed items
        with self._table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
