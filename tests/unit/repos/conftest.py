from decimal import Decimal
from typing import Any, Callable

import pytest
from botocore.exceptions import ClientError

from app.models.workout import Workout, WorkoutSet
from app.utils import db
from tests.test_data import TEST_DATE_2, TEST_WORKOUT_ID_2, USER_SUB

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


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


@pytest.fixture
def client_error():
    """
    Fixture returning a helper function to build ClientError instances.
    Usage:
        err = client_error("Query")
    """
    return _client_error


# ─────────────────────────────────────────────────────────────
# Fake DynamoDB Table + batch_writer
# ─────────────────────────────────────────────────────────────


OP_NAMES = {
    "query": "Query",
    "get_item": "GetItem",
    "put_item": "PutItem",
    "delete_item": "DeleteItem",
}


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
    """

    def __init__(
        self, response: dict | None = None, *, fail_on: set[str] | None = None
    ):
        self.response: dict = response or {}
        self.fail_on: set[str] = set(fail_on or [])

        self.last_query_kwargs: dict | None = None
        self.last_get_kwargs: dict | None = None
        self.last_put_kwargs: dict | None = None
        self.last_delete_kwargs: dict | None = None

        self.deleted_keys: list[dict] = []

    def _maybe_fail(self, op: str):
        name = OP_NAMES[op]
        if op in self.fail_on or name in self.fail_on:
            raise _client_error(op)

    def query(self, **kwargs):
        self._maybe_fail("query")
        self.last_query_kwargs = kwargs
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

    def batch_writer(self):
        return FakeBatchWriter(self)


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def fake_table() -> FakeTable:
    """
    Fixture returning a FakeTable instance.
    Tests can override the FakeTable.response to simulate DynamoDB responses.
    """
    return FakeTable()


@pytest.fixture
def failing_query_table() -> FakeTable:
    return FakeTable(fail_on={"query"})


@pytest.fixture
def failing_get_table() -> FakeTable:
    return FakeTable(fail_on={"get_item"})


@pytest.fixture
def failing_put_table() -> FakeTable:
    return FakeTable(fail_on={"put_item"})


@pytest.fixture
def failing_delete_table() -> FakeTable:
    return FakeTable(fail_on={"delete_item"})


@pytest.fixture
def bad_items_table() -> FakeTable:
    """
    Returns malformed Items for parse-error tests.
    """
    return FakeTable(response={"Items": [{"type": "workout"}]})


@pytest.fixture
def workout_factory(fixed_now) -> Callable[..., Workout]:
    def _make(**overrides: Any) -> Workout:
        base = Workout(
            PK=db.build_user_pk(USER_SUB),
            SK=db.build_workout_sk(TEST_DATE_2, TEST_WORKOUT_ID_2),
            type="workout",
            date=TEST_DATE_2,
            name="Move Me Dino Day",
            tags=["upper"],
            notes="Roar",
            created_at=fixed_now,
            updated_at=fixed_now,
        )
        return base.model_copy(update=overrides)

    return _make


@pytest.fixture
def set_factory(fixed_now) -> Callable[..., WorkoutSet]:
    def _make(**overrides: Any) -> WorkoutSet:
        base = WorkoutSet(
            PK=db.build_user_pk(USER_SUB),
            SK=db.build_set_sk(TEST_DATE_2, TEST_WORKOUT_ID_2, 1),
            type="set",
            exercise_id="squat",
            set_number=1,
            reps=8,
            weight_kg=Decimal("60"),
            rpe=7,
            created_at=fixed_now,
            updated_at=fixed_now,
        )
        return base.model_copy(update=overrides)

    return _make
