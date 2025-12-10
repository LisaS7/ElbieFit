import uuid
from datetime import date as DateType
from typing import List, Protocol

from boto3.dynamodb.conditions import Key

from app.models.workout import Workout, WorkoutCreate, WorkoutSet, WorkoutSetCreate
from app.repositories.base import DynamoRepository
from app.repositories.errors import RepoError, WorkoutNotFoundError, WorkoutRepoError
from app.utils import dates, db
from app.utils.log import logger


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
    ) -> Workout: ...
    def delete_workout_and_sets(
        self, user_sub: str, workout_date: DateType, workout_id: str
    ) -> None: ...
    def add_set(
        self,
        user_sub: str,
        workout_date: DateType,
        workout_id: str,
        exercise_id: str,
        data: WorkoutSetCreate,
    ) -> WorkoutSet: ...
    def delete_set(
        self, user_sub: str, workout_date: DateType, workout_id: str, set_number: int
    ) -> None: ...


class DynamoWorkoutRepository(DynamoRepository[Workout]):
    """
    Implementation of WorkoutRepository
    """

    def _to_model(self, item: dict):
        item_type = item.get("type")
        logger.debug(f"_to_model: converting item with type={item_type}")

        try:
            if item_type == "workout":
                return Workout(**item)
            elif item_type == "set":
                return WorkoutSet(**item)
        except Exception as e:
            logger.error(f"_to_model failed: {e}")
            raise WorkoutRepoError("Failed to create workout model from item") from e

        raise WorkoutRepoError(f"Unknown item type: {item_type}")

    def _build_moved_workout(
        self, user_sub: str, workout: Workout, new_date: DateType
    ) -> Workout:
        """
        Create a new Workout model instance with updated date and keys.
        """

        logger.debug(
            f"_build_moved_workout: moving workout {workout.workout_id} "
            f"from {workout.date} → {new_date}"
        )

        pk = db.build_user_pk(user_sub)
        sk = db.build_workout_sk(new_date, workout.workout_id)
        now = dates.now()

        return workout.model_copy(
            update={"PK": pk, "SK": sk, "date": new_date, "updated_at": now}
        )

    def _build_moved_sets(
        self,
        user_sub: str,
        new_workout: Workout,
        old_workout_id: str,
        sets: List[WorkoutSet],
    ) -> List[WorkoutSet]:
        """
        Create new WorkoutSet model instances with updated keys for the moved workout.
        """
        logger.debug(
            f"_build_moved_sets: moving {len(sets)} sets to new workout {new_workout.workout_id}"
        )

        pk = db.build_user_pk(user_sub)
        new_sets = []
        for s in sets:
            new_sk = db.build_set_sk(new_workout.date, old_workout_id, s.set_number)
            now = dates.now()
            logger.debug(f"Moving set {s.set_number} → SK={new_sk}")
            new_set = s.model_copy(update={"PK": pk, "SK": new_sk, "updated_at": now})
            new_sets.append(new_set)
        return new_sets

    def _get_next_set_number(
        self, user_sub: str, workout_date: DateType, workout_id: str
    ) -> int:
        """
        Determine the next set number for a given workout by fetching existing sets.
        """
        logger.debug(f"Calculating next set number for workout {workout_id}")

        pk = db.build_user_pk(user_sub)
        sk_prefix = db.build_set_prefix(workout_date, workout_id)

        try:
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk)
                & Key("SK").begins_with(sk_prefix)
            )
            logger.debug(f"Found {len(items)} existing sets")

            if not items:
                return 1

            set_numbers = []
            for item in items:
                parts = item["SK"].split("#")
                if len(parts) >= 5:
                    try:
                        set_number = int(parts[-1])
                        set_numbers.append(set_number)
                    except ValueError:
                        logger.warning(f"Invalid set number in SK: {item['SK']}")

            if not set_numbers:
                logger.warning("No valid set numbers found, defaulting to 1")
                return 1

            next_number = max(set_numbers) + 1
            logger.debug(f"Next set number is {next_number}")

            return next_number
        except RepoError as e:
            logger.error(f"Error determining next set number: {e}")
            raise WorkoutRepoError("Failed to determine next set number") from e

    # ----------------------- Get -----------------------------

    def get_all_for_user(self, user_sub: str) -> List[Workout]:
        """
        Return only workout items, sorted by date desc, Sets are filtered out.
        """
        logger.debug(f"Fetching all workouts for user {user_sub}")

        pk = db.build_user_pk(user_sub)

        try:
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk)
                & Key("SK").begins_with("WORKOUT#")
            )
            logger.debug(f"{len(items)} items returned from DynamoDB")

            models = [self._to_model(item) for item in items]
            workouts = [m for m in models if isinstance(m, Workout)]
            logger.debug(f"{len(workouts)} workouts parsed")

            workouts.sort(key=lambda w: w.date, reverse=True)
            return workouts

        except RepoError as e:
            logger.error(f"Repo error fetching workouts: {e}")
            raise WorkoutRepoError("Failed to fetch workouts from database") from e
        except Exception as e:
            logger.error(f"Unexpected error parsing workouts: {e}")
            raise WorkoutRepoError(
                "Failed to parse workouts from database response"
            ) from e

    def get_workout_with_sets(
        self, user_sub: str, workout_date: DateType, workout_id: str
    ) -> tuple[Workout, List[WorkoutSet]]:
        """
        Fetch a single workout and its sets for the given user/date/id
        """
        logger.debug(f"Fetching workout {workout_id} with sets for {workout_date}")

        pk = db.build_user_pk(user_sub)
        sk = db.build_workout_sk(workout_date, workout_id)

        try:
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk)
            )
            logger.debug(f"Query returned {len(items)} items")
            models = [self._to_model(item) for item in items]

        except RepoError as e:
            logger.error(f"Repo error querying workout+sets: {e}")
            raise WorkoutRepoError(
                "Failed to query workout and sets from database"
            ) from e

        workout = [m for m in models if isinstance(m, Workout)]
        sets = [s for s in models if isinstance(s, WorkoutSet)]

        logger.debug(f"Parsed workout={len(workout)}, sets={len(sets)}")

        if not workout:
            logger.warning(f"Workout not found: {workout_id} on {workout_date}")
            raise WorkoutNotFoundError(
                f"Workout {workout_id} on {workout_date} not found for user {user_sub}"
            )

        return workout[0], sets

    # ----------------------- Add -----------------------------

    def create_workout(self, user_sub: str, data: WorkoutCreate) -> Workout:
        """
        Persist a new workout item to DynamoDB.
        """
        logger.debug(f"Creating workout for {user_sub} with name '{data.name}'")

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

        logger.debug(f"New workout ID={new_id}, SK={workout.SK}")

        try:
            self._safe_put(workout.to_ddb_item())
        except RepoError as e:
            logger.error(f"Failed to put workout: {e}")
            raise WorkoutRepoError("Failed to create workout in database") from e
        return workout

    def add_set(
        self,
        user_sub: str,
        workout_date: DateType,
        workout_id: str,
        exercise_id: str,
        data: WorkoutSetCreate,
    ) -> WorkoutSet:
        """
        Add a new set to the existing workout.
        """
        logger.debug(f"Adding set to workout {workout_id} on {workout_date}")

        new_set_number = self._get_next_set_number(user_sub, workout_date, workout_id)

        now = dates.now()

        new_set = WorkoutSet(
            PK=db.build_user_pk(user_sub),
            SK=db.build_set_sk(workout_date, workout_id, new_set_number),
            type="set",
            set_number=new_set_number,
            exercise_id=exercise_id,
            reps=data.reps,
            weight_kg=data.weight_kg,
            rpe=data.rpe,
            created_at=now,
            updated_at=now,
        )

        logger.debug(f"New set SK={new_set.SK}")

        try:
            self._safe_put(new_set.to_ddb_item())
        except RepoError as e:
            logger.error(f"Failed to add set: {e}")
            raise WorkoutRepoError("Failed to add workout set to database") from e

        return new_set

    # ----------------------- Update -----------------------------

    def update_workout(self, workout: Workout) -> Workout:
        """
        Persist changes to an existing workout.
        """

        logger.debug(f"Updating workout {workout.workout_id}")

        try:
            self._safe_put(workout.to_ddb_item())
        except RepoError as e:
            logger.error(f"Failed to update workout: {e}")
            raise WorkoutRepoError("Failed to update workout in database") from e
        return workout

    def move_workout_date(
        self,
        user_sub: str,
        workout: Workout,
        new_date: DateType,
        sets: list[WorkoutSet],
    ) -> Workout:

        logger.debug(
            f"Moving workout {workout.workout_id} from {workout.date} → {new_date} "
            f"with {len(sets)} sets"
        )

        old_date = workout.date
        old_workout_id = workout.workout_id

        # create a new workout
        new_workout = self._build_moved_workout(user_sub, workout, new_date)
        new_sets = self._build_moved_sets(user_sub, new_workout, old_workout_id, sets)

        try:
            self._safe_put(new_workout.to_ddb_item())

            for item in new_sets:
                logger.debug(f"Writing moved set: {item.SK}")
                self._safe_put(item.to_ddb_item())
        except RepoError as e:
            logger.error(f"Failed writing moved workout or sets: {e}")
            raise WorkoutRepoError("Failed to write new workout or sets") from e

        try:
            logger.debug("Deleting old workout and sets")
            self.delete_workout_and_sets(user_sub, old_date, old_workout_id)
        except WorkoutRepoError as e:
            logger.error(f"Move succeeded but cleanup failed: {e}")
            raise WorkoutRepoError(
                "New workout created but failed to delete old one"
            ) from e

        return new_workout

    # ----------------------- Delete -----------------------------

    def delete_workout_and_sets(
        self, user_sub: str, workout_date: DateType, workout_id: str
    ) -> None:
        """
        Delete an existing workout and all its sets.
        """
        logger.debug(f"Deleting workout {workout_id} and its sets")

        pk = db.build_user_pk(user_sub)
        sk = db.build_workout_sk(workout_date, workout_id)

        try:
            # Get everything beginning with this pk/sk combo
            # (so this includes sets belonging to the workout)
            items = self._safe_query(
                KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk)
            )
            logger.debug(f"Found {len(items)} items to delete")
        except RepoError as e:
            logger.error(f"Failed loading items for deletion: {e}")
            raise WorkoutRepoError(
                "Failed to load workout and sets for deletion"
            ) from e

        if not items:
            logger.debug("No items found — nothing to delete")
            return

        # use batch_writer here to make bulk delete easier
        # batch_writer bundles into batches and auto retries unprocessed items
        try:
            with self._table.batch_writer() as batch:
                for item in items:
                    logger.debug(f"Deleting PK={item['PK']} SK={item['SK']}")
                    batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
        except Exception as e:
            logger.error(f"Batch delete failed: {e}")
            raise WorkoutRepoError(
                "Failed to delete workout and sets from database"
            ) from e

    def delete_set(
        self, user_sub: str, workout_date: DateType, workout_id: str, set_number: int
    ) -> None:
        """
        Delete a specific workout set.
        """

        logger.debug(
            f"Deleting set #{set_number} from workout {workout_id} on {workout_date}"
        )

        pk = db.build_user_pk(user_sub)
        sk = db.build_set_sk(workout_date, workout_id, set_number)

        try:
            self._safe_delete(Key={"PK": pk, "SK": sk})
        except RepoError as e:
            logger.error(f"Failed to delete set: {e}")
            raise WorkoutRepoError("Failed to delete workout set from database") from e
