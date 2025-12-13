from decimal import Decimal

import pytest

from app.repositories.errors import WorkoutRepoError
from app.repositories.workout import DynamoWorkoutRepository
from tests.test_data import (
    TEST_DATE_2,
    TEST_SET_SK_2,
    TEST_WORKOUT_ID_2,
    TEST_WORKOUT_SK_2,
    USER_PK,
    USER_SUB,
)

# ──────────────────────────── Test data ────────────────────────────


@pytest.fixture
def fake_table_response_w2_only(workout_factory, set_factory):
    workout = workout_factory(
        SK=TEST_WORKOUT_SK_2,
        date=TEST_DATE_2,
        name="Workout A",
        tags=["upper"],
        notes="Newer",
    )

    set1 = set_factory(
        SK=TEST_SET_SK_2,
        exercise_id="squat",
        set_number=1,
        reps=8,
        weight_kg=Decimal("60"),
        rpe=7,
    )

    return {"Items": [workout.to_ddb_item(), set1.to_ddb_item()]}


# ──────────────────────────── delete_workout_and_sets ────────────────────────────


def test_delete_workout_and_sets_deletes_workout_and_its_sets(
    fake_table, fake_table_response_w2_only
):
    """
    Given a workout with sets, delete_workout_and_sets should:
      - query using the correct PK and SK prefix
      - delete all returned items via batch_writer
    """
    repo = DynamoWorkoutRepository(table=fake_table)

    fake_table.response = fake_table_response_w2_only

    repo.delete_workout_and_sets(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert len(fake_table.deleted_keys) == 2
    assert {"PK": USER_PK, "SK": TEST_WORKOUT_SK_2} in fake_table.deleted_keys
    assert {"PK": USER_PK, "SK": TEST_SET_SK_2} in fake_table.deleted_keys

    # sanity: it did query
    assert fake_table.last_query_kwargs is not None


def test_delete_workout_and_sets_does_nothing_when_no_items(fake_table):
    repo = DynamoWorkoutRepository(table=fake_table)

    fake_table.response = {"Items": []}

    repo.delete_workout_and_sets(USER_SUB, TEST_DATE_2, "NON_EXISTENT")

    assert fake_table.last_query_kwargs is not None
    assert fake_table.deleted_keys == []


def test_delete_workout_and_sets_wraps_client_error(failing_query_table):
    repo = DynamoWorkoutRepository(table=failing_query_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.delete_workout_and_sets(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert "Failed to load workout and sets for deletion" in str(excinfo.value)


def test_delete_workout_and_sets_wraps_unexpected_exception_from_batch_writer(
    fake_table, fake_table_response_w2_only, monkeypatch
):
    """
    If Dynamo's batch_writer.delete_item raises an unexpected exception, the
    repository should wrap it in a WorkoutRepoError with the expected message.
    """
    repo = DynamoWorkoutRepository(table=fake_table)

    fake_table.response = fake_table_response_w2_only

    class BadBatch:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def delete_item(self, Key):
            raise RuntimeError("boom delete")

    monkeypatch.setattr(repo._table, "batch_writer", lambda: BadBatch())

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.delete_workout_and_sets(USER_SUB, TEST_DATE_2, TEST_WORKOUT_ID_2)

    assert "Failed to delete workout and sets from database" in str(excinfo.value)
