import uuid
from datetime import date as DateType
from typing import List, Protocol

from boto3.dynamodb.conditions import Key

from app.models.workout import Workout, WorkoutCreate, WorkoutSet
from app.repositories.base import DynamoRepository
from app.repositories.errors import RepoError, WorkoutNotFoundError, WorkoutRepoError
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


class DynamoWorkoutRepository(DynamoRepository[Workout]):
    """
    Implementation of WorkoutRepository
    """

    def _to_model(self, item: dict):
        item_type = item.get("type")

        try:
            if item_type == "workout":
                return Workout(**item)
            elif item_type == "set":
                return WorkoutSet(**item)
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
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk)
                & Key("SK").begins_with("WORKOUT#")
            )

            models = [self._to_model(item) for item in items]
            workouts = [m for m in models if isinstance(m, Workout)]
            workouts.sort(key=lambda w: w.date, reverse=True)
            return workouts
        except WorkoutRepoError:
            raise
        except RepoError as e:
            raise WorkoutRepoError("Failed to fetch workouts from database") from e
        except Exception as e:
            raise WorkoutRepoError(
                "Failed to parse workouts from database response"
            ) from e

    def get_workout_with_sets(
        self, user_sub: str, workout_date: DateType, workout_id: str
    ) -> tuple[Workout, List[WorkoutSet]]:
        """
        Fetch a single workout and its sets for the given user/date/id
        """
        pk = db.build_user_pk(user_sub)
        sk = db.build_workout_sk(workout_date, workout_id)

        try:
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk)
            )
            models = [self._to_model(item) for item in items]
        except WorkoutRepoError:
            raise
        except RepoError as e:
            raise WorkoutRepoError(
                "Failed to query workout and sets from database"
            ) from e
        except Exception as e:
            raise WorkoutRepoError(
                "Failed to parse workout and sets from response"
            ) from e

        workout = [m for m in models if isinstance(m, Workout)]
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

        try:
            self._safe_put(workout.to_ddb_item())
        except RepoError as e:
            raise WorkoutRepoError("Failed to create workout in database") from e
        return workout

    # ----------------------- Update -----------------------------

    def update_workout(self, workout: Workout) -> Workout:
        """
        Persist changes to an existing workout.
        """

        try:
            self._safe_put(workout.to_ddb_item())
        except RepoError as e:
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

        try:
            self._safe_put(new_workout.to_ddb_item())

            # Recreate sets with new SKs
            for s in sets:
                pk = db.build_user_pk(user_sub)
                new_sk = db.build_set_sk(new_workout.date, old_workout_id, s.set_number)
                new_item = {
                    **s.to_ddb_item(),
                    "PK": pk,
                    "SK": new_sk,
                }
                self._safe_put(new_item)
        except RepoError as e:
            raise WorkoutRepoError("Failed to write new workout or sets") from e

        try:
            self.delete_workout_and_sets(user_sub, old_date, old_workout_id)
        except WorkoutRepoError as e:
            raise WorkoutRepoError(
                "New workout created but failed to delete old one"
            ) from e

    # ----------------------- Delete -----------------------------

    def delete_workout_and_sets(
        self, user_sub: str, workout_date: DateType, workout_id: str
    ) -> None:
        """
        Delete an existing workout and all its sets.
        """
        pk = db.build_user_pk(user_sub)
        sk = db.build_workout_sk(workout_date, workout_id)

        try:
            # Get everything beginning with this pk/sk combo
            # (so this includes sets belonging to the workout)
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk)
            )
        except RepoError as e:
            raise WorkoutRepoError(
                "Failed to load workout and sets for deletion"
            ) from e

        if not items:
            return

        # use batch_writer here to make bulk delete easier
        # batch_writer bundles into batches and auto retries unprocessed items
        try:
            with self._table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
        except Exception as e:
            raise WorkoutRepoError(
                "Failed to delete workout and sets from database"
            ) from e
