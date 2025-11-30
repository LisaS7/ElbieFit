import uuid
from datetime import date as DateType
from typing import List, Protocol

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.models.workout import Workout, WorkoutCreate, WorkoutSet
from app.repositories.errors import WorkoutNotFoundError, WorkoutRepoError
from app.utils import dates, db


class WorkoutRepository(Protocol):
    def get_all_for_user(self, user_sub: str) -> List[Workout]: ...
    def create_workout(self, user_sub, data: WorkoutCreate) -> Workout: ...
    def get_workout_with_sets(
        self, user_sub: str, workout_date: DateType, workout_id: str
    ) -> tuple[Workout, List[WorkoutSet]]: ...
    def update_workout(self, workout: Workout) -> Workout: ...
    def move_workout_date(
        self,
        user_sub: str,
        workout: Workout,
        new_date: DateType,
        sets: list[WorkoutSet],
    ) -> None: ...
    def delete_workout_and_sets(
        self, user_sub: str, workout_date: DateType, workout_id: str
    ) -> None: ...


class DynamoWorkoutRepository:
    """
    Implementation of WorkoutRepository
    """

    def __init__(self, table=None):
        self._table = table or db.get_table()

    def _to_workout(self, item: dict) -> Workout:
        return Workout(**item)

    def _to_workout_set(self, item: dict) -> WorkoutSet:
        return WorkoutSet(**item)

    def _to_model(self, item: dict):
        """
        Map a DynamoDB item (from the resource API) into a Workout model.
        """

        item_type = item.get("type")

        try:
            if item_type == "workout":
                return self._to_workout(item)
            elif item_type == "set":
                return self._to_workout_set(item)
        except Exception as e:
            raise WorkoutRepoError("Failed to create workout model from item") from e

        raise WorkoutRepoError(f"Unknown item type: {item_type}")

    # ----------------------- Get -----------------------------

    def get_all_for_user(self, user_sub: str) -> List[Workout]:
        """
        Return only workout items, sorted by date desc, Sets are filtered out.
        """
        pk = db.build_user_pk(user_sub)

        try:
            response = self._table.query(
                KeyConditionExpression=Key("PK").eq(pk)
                & Key("SK").begins_with("WORKOUT#")
            )
        except ClientError as e:
            raise WorkoutRepoError("Failed to query database for workouts") from e

        try:
            items = response.get("Items", [])
            workouts = [
                self._to_model(item) for item in items if item.get("type") == "workout"
            ]
            # ignore type hint: we're filtering out sets in the previous step
            workouts.sort(key=lambda w: w.date, reverse=True)  # type: ignore[arg-type]
            return workouts  # type: ignore[arg-type]
        except Exception:
            raise WorkoutRepoError("Failed to parse workouts from database response")

    def get_workout_with_sets(
        self, user_sub: str, workout_date: DateType, workout_id: str
    ) -> tuple[Workout, List[WorkoutSet]]:
        """
        Fetch a single workout and its sets for the given user/date/id
        """
        pk = db.build_user_pk(user_sub)
        sk = db.build_workout_sk(workout_date, workout_id)

        try:
            response = self._table.query(
                KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk)
            )
        except ClientError:
            raise WorkoutRepoError("Failed to query workout and sets from database")

        try:
            items = response.get("Items", [])

            models = [self._to_model(item) for item in items]

        except Exception as e:
            raise WorkoutRepoError(
                "Failed to parse workout and sets from response"
            ) from e

        workout = [w for w in models if isinstance(w, Workout)]
        sets = [s for s in models if isinstance(s, WorkoutSet)]

        if not workout:
            raise WorkoutNotFoundError(
                f"Workout {workout_id} on {workout_date} not found for user {user_sub}"
            )

        return workout[0], sets

    # ----------------------- Add -----------------------------

    def create_workout(self, user_sub: str, data: WorkoutCreate) -> Workout:
        """
        Persist a new workout item to DynamoDB.
        """
        new_id = str(uuid.uuid4())
        now = dates.now()

        workout = Workout(
            PK=db.build_user_pk(user_sub),
            SK=db.build_workout_sk(data.date, new_id),
            type="workout",
            date=data.date,
            name=data.name,
            created_at=now,
            updated_at=now,
        )

        item = workout.to_ddb_item()
        try:
            self._table.put_item(Item=item)
        except ClientError as e:
            raise WorkoutRepoError("Failed to create workout in database") from e
        return workout

    # ----------------------- Update -----------------------------

    def update_workout(self, workout: Workout) -> Workout:
        """
        Persist changes to an existing workout.
        """

        item = workout.to_ddb_item()
        try:
            self._table.put_item(Item=item)
        except ClientError as e:
            raise WorkoutRepoError("Failed to update workout in database") from e
        return workout

    def move_workout_date(
        self,
        user_sub: str,
        workout: Workout,
        new_date: DateType,
        sets: list[WorkoutSet],
    ) -> None:

        old_date = workout.date
        old_workout_id = workout.workout_id
        now = dates.now()

        # new keys
        pk = db.build_user_pk(user_sub)
        new_sk = db.build_workout_sk(new_date, old_workout_id)

        # create a new workout
        new_workout = workout.model_copy(
            update={"PK": pk, "SK": new_sk, "date": new_date, "updated_at": now}
        )

        self._table.put_item(Item=new_workout.to_ddb_item())

        # Recreate sets with new SKs
        for s in sets:
            pk = db.build_user_pk(user_sub)
            new_sk = db.build_set_sk(new_workout.date, old_workout_id, s.set_number)
            new_item = {
                **s.to_ddb_item(),
                "PK": pk,
                "SK": new_sk,
            }
            self._table.put_item(Item=new_item)

        # Delete the old workout + sets
        self.delete_workout_and_sets(user_sub, old_date, old_workout_id)

    # ----------------------- Delete -----------------------------

    def delete_workout_and_sets(
        self, user_sub: str, workout_date: DateType, workout_id: str
    ) -> None:
        """
        Delete an existing workout.
        """
        pk = db.build_user_pk(user_sub)
        sk = db.build_workout_sk(workout_date, workout_id)

        try:
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
        except ClientError as e:
            raise WorkoutRepoError(
                "Failed to delete workout and sets from database"
            ) from e
