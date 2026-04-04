import uuid
from datetime import date as DateType
from datetime import datetime, timezone
from typing import Any

from botocore.exceptions import ClientError

from app.models.exercise import Exercise
from app.models.profile import Preferences, UserProfile
from app.models.workout import Workout
from app.repositories.errors import ProfileRepoError
from app.utils import db


def make_test_profile(*, units: str = "metric", user_sub: str = "test-user") -> UserProfile:
    return UserProfile(
        PK=f"USER#{user_sub}",
        SK="PROFILE",
        display_name="Test User",
        email="test@example.com",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        timezone="Europe/London",
        preferences=Preferences(units=units),
    )


class FakeProfileRepo:
    def __init__(
        self,
        profile: UserProfile | None = None,
        *,
        raise_on_get: bool = False,
        raise_on_update: bool = False,
        updated_profile: UserProfile | None = None,
    ):
        self._profile = profile
        self._raise_on_get = raise_on_get
        self._raise_on_update = raise_on_update
        self._updated_profile = updated_profile or profile

        # optional: capture calls
        self.last_update_account = None
        self.last_update_prefs = None

    def get_for_user(self, user_sub: str) -> UserProfile | None:
        if self._raise_on_get:
            raise ProfileRepoError("boom")
        return self._profile

    def update_account(
        self, user_sub: str, *, display_name: str, timezone: str
    ) -> UserProfile:
        if self._raise_on_update:
            raise ProfileRepoError("boom update")
        self.last_update_account = {
            "user_sub": user_sub,
            "display_name": display_name,
            "timezone": timezone,
        }
        return self._updated_profile  # type: ignore[return-value]

    def update_preferences(
        self, user_sub: str, *, theme: str, units: str
    ) -> UserProfile:
        if self._raise_on_update:
            raise ProfileRepoError("boom update")
        self.last_update_prefs = {
            "user_sub": user_sub,
            "theme": theme,
            "units": units,
        }
        return self._updated_profile  # type: ignore[return-value]


# --------------- FakeResponse ---------------


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


# --------------- Workout / Exercise repos (route fakes) ---------------


class FakeWorkoutRepo:
    """
    Tiny fake to stand in for DynamoWorkoutRepository in route tests.
    """

    def __init__(self):
        self.user_subs = []
        self.workouts_to_return = []
        self.created_workouts = []

        self.workout_to_return = None
        self.sets_to_return = []

        self.updated_workouts = []

        self.deleted_calls = []

        self.added_sets: list[tuple[str, DateType, str, str, Any]] = []

        self.set_to_return = None
        self.edited_sets: list[tuple[str, DateType, str, int, object]] = []

    def get_all_for_user(self, user_sub: str):
        self.user_subs.append(user_sub)
        return self.workouts_to_return

    def create_workout(self, user_sub: str, data):
        self.user_subs.append(user_sub)

        new_id = str(uuid.uuid4())
        now = datetime(2025, 1, 1, tzinfo=timezone.utc)

        workout = Workout(
            PK=db.build_user_pk(user_sub),
            SK=db.build_workout_sk(data.date, new_id),
            type="workout",
            date=data.date,
            name=data.name,
            created_at=now,
            updated_at=now,
        )

        self.created_workouts.append(workout)
        return workout

    def get_workout_with_sets(self, user_sub, workout_date, workout_id):
        return self.workout_to_return, self.sets_to_return

    def edit_workout(self, workout):
        self.updated_workouts.append(workout)
        return workout

    def delete_workout_and_sets(self, user_sub, workout_date, workout_id):
        self.deleted_calls.append((user_sub, workout_date, workout_id))

    def add_set(self, user_sub, workout_date, workout_id, exercise_id, form):
        self.added_sets.append((user_sub, workout_date, workout_id, exercise_id, form))
        self.user_subs.append(user_sub)

    def delete_set(self, user_sub, workout_date, workout_id, set_number):
        self.deleted_calls.append((user_sub, workout_date, workout_id, set_number))

    def get_set(self, user_sub, workout_date, workout_id, set_number):
        return self.set_to_return

    def edit_set(self, user_sub, workout_date, workout_id, set_number, form):
        self.edited_sets.append((user_sub, workout_date, workout_id, set_number, form))


class FakeExerciseRepo:
    """
    Fake DynamoExerciseRepository for route tests.
    """

    def __init__(self):
        self.exercises: dict[str, Exercise] = {}
        self.created: list[Exercise] = []
        self.updated: list[Exercise] = []
        self.deleted: list[tuple[str, str]] = []

        # Override to make get_exercise_by_id raise
        self.raise_on_get: bool = False
        self.raise_on_create: bool = False
        self.raise_on_update: bool = False
        self.raise_on_delete: bool = False

    def _make_exercise(self, exercise_id: str) -> Exercise:
        now = datetime(2025, 1, 1, tzinfo=timezone.utc)
        return Exercise(
            PK=db.build_user_pk("test-user-sub"),
            SK=db.build_exercise_sk(exercise_id),
            type="exercise",
            name=f"Exercise {exercise_id}",
            equipment="barbell",
            category="legs",
            muscles=["quads"],
            created_at=now,
            updated_at=now,
        )

    def seed(self, exercise: Exercise) -> None:
        self.exercises[exercise.exercise_id] = exercise

    def get_all_for_user(self, user_sub: str) -> list[Exercise]:
        return list(self.exercises.values())

    def get_exercise_by_id(self, user_sub: str, exercise_id: str) -> Exercise | None:
        from app.repositories.errors import ExerciseRepoError

        if self.raise_on_get:
            raise ExerciseRepoError("boom")
        return self.exercises.get(exercise_id)

    def create_exercise(self, user_sub: str, data) -> Exercise:
        from app.repositories.errors import ExerciseRepoError

        if self.raise_on_create:
            raise ExerciseRepoError("boom")
        now = datetime(2025, 1, 1, tzinfo=timezone.utc)
        new_id = str(uuid.uuid4())
        exercise = Exercise(
            PK=db.build_user_pk(user_sub),
            SK=db.build_exercise_sk(new_id),
            type="exercise",
            name=data.name,
            equipment=data.equipment,
            category=data.category,
            muscles=data.muscles,
            created_at=now,
            updated_at=now,
        )
        self.created.append(exercise)
        self.exercises[exercise.exercise_id] = exercise
        return exercise

    def update_exercise(self, exercise: Exercise) -> None:
        from app.repositories.errors import ExerciseRepoError

        if self.raise_on_update:
            raise ExerciseRepoError("boom")
        self.updated.append(exercise)
        self.exercises[exercise.exercise_id] = exercise

    def delete_exercise(self, user_sub: str, exercise_id: str) -> None:
        from app.repositories.errors import ExerciseRepoError

        if self.raise_on_delete:
            raise ExerciseRepoError("boom")
        self.deleted.append((user_sub, exercise_id))
        self.exercises.pop(exercise_id, None)


# --------------- DynamoDB table fakes (repo tests) ---------------


OP_NAMES = {
    "query": "Query",
    "get_item": "GetItem",
    "put_item": "PutItem",
    "delete_item": "DeleteItem",
    "update_item": "UpdateItem",
}


def _client_error(
    op_name: str, *, code: str = "500", message: str | None = None
) -> ClientError:
    """
    Build a botocore ClientError for unit tests.
    """
    msg = message or f"Boom in {op_name}"
    return ClientError(
        error_response={"Error": {"Code": code, "Message": msg}},
        operation_name=op_name,
    )


class FakeBatchWriter:
    """
    Minimal stand-in for DynamoDB's batch_writer.
    Forwards delete_item calls to the parent FakeTable.
    """

    def __init__(self, table: "FakeTable"):
        self._table = table

    def __enter__(self) -> "FakeBatchWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        # Don't suppress exceptions
        return False

    def delete_item(self, Key: dict) -> None:
        self._table.deleted_keys.append(Key)


class FakeTable:
    """
    A lightweight fake for boto3 DynamoDB Table.

    - `response`: dict returned by query/get/put/delete
    - `fail_on`: set of operation names that should raise ClientError
      (e.g. {"query", "put_item"})
    - `paginated_responses`: list of dicts consumed one per query() call,
      used to simulate multi-page DynamoDB results. When set, each call to
      query() pops the next response off the front of the list (ignoring
      `response`).
    """

    def __init__(
        self,
        response: dict | None = None,
        *,
        fail_on: set[str] | None = None,
        paginated_responses: list[dict] | None = None,
    ):
        self.response: dict = response or {}
        self.fail_on: set[str] = set(fail_on or [])
        self.paginated_responses: list[dict] = list(paginated_responses or [])

        self.last_query_kwargs: dict | None = None
        self.last_get_kwargs: dict | None = None
        self.last_put_kwargs: dict | None = None
        self.last_delete_kwargs: dict | None = None

        self.deleted_keys: list[dict] = []

        self.last_update_kwargs: dict | None = None

    def _maybe_fail(self, op: str):
        name = OP_NAMES[op]
        if op in self.fail_on or name in self.fail_on:
            raise _client_error(op)

    def query(self, **kwargs):
        self._maybe_fail("query")
        self.last_query_kwargs = kwargs
        if self.paginated_responses:
            return self.paginated_responses.pop(0)
        return self.response

    def get_item(self, **kwargs):
        self._maybe_fail("get_item")
        self.last_get_kwargs = kwargs
        return self.response

    def put_item(self, **kwargs):
        self._maybe_fail("put_item")
        self.last_put_kwargs = kwargs
        return self.response

    def delete_item(self, **kwargs):
        self._maybe_fail("delete_item")
        self.last_delete_kwargs = kwargs
        key = kwargs.get("Key")
        if key is not None:
            self.deleted_keys.append(key)
        return self.response

    def update_item(self, **kwargs):
        self._maybe_fail("update_item")
        self.last_update_kwargs = kwargs
        return self.response

    def batch_writer(self):
        return FakeBatchWriter(self)


# --------------- Rate-limiting table fake (utils tests) ---------------


class FakeRateLimitTable:
    def __init__(self, count: int):
        self.count = count
        self.last_kwargs = None

    def update_item(self, **kwargs):
        self.last_kwargs = kwargs
        return {"Attributes": {"count": self.count}}
