# ──────────────────────────── _build_moved_workout ────────────────────────────


import pytest

from app.repositories.errors import WorkoutRepoError
from app.repositories.workout import DynamoWorkoutRepository
from app.utils import db
from tests.test_data import TEST_DATE_2, TEST_DATE_3, TEST_WORKOUT_ID_2, USER_SUB


def test_build_moved_workout_updates_keys_and_date(
    fake_table, workout_factory, fixed_now
):
    repo = DynamoWorkoutRepository(table=fake_table)

    original = workout_factory()
    new_workout = repo._build_moved_workout(USER_SUB, original, TEST_DATE_3)

    assert new_workout.PK == db.build_user_pk(USER_SUB)
    assert new_workout.SK == db.build_workout_sk(TEST_DATE_3, TEST_WORKOUT_ID_2)
    assert new_workout.date == TEST_DATE_3
    assert new_workout.updated_at == fixed_now
    assert new_workout.name == original.name
    assert new_workout.created_at == original.created_at


# ──────────────────────────── _build_moved_sets ────────────────────────────


def test_build_moved_sets_updates_pk_sk_and_timestamp(
    fake_table, workout_factory, set_factory, fixed_now
):
    repo = DynamoWorkoutRepository(table=fake_table)

    new_workout = workout_factory(
        SK=db.build_workout_sk(TEST_DATE_3, TEST_WORKOUT_ID_2),
        date=TEST_DATE_3,
        name="Moved",
    )
    original_set = set_factory()

    new_sets = repo._build_moved_sets(
        USER_SUB, new_workout, TEST_WORKOUT_ID_2, [original_set]
    )

    assert len(new_sets) == 1
    moved = new_sets[0]

    assert moved.PK == db.build_user_pk(USER_SUB)
    assert moved.SK == db.build_set_sk(TEST_DATE_3, TEST_WORKOUT_ID_2, 1)
    assert moved.updated_at == fixed_now

    assert moved.exercise_id == original_set.exercise_id
    assert moved.reps == original_set.reps
    assert moved.weight_kg == original_set.weight_kg
    assert moved.rpe == original_set.rpe
    assert moved.created_at == original_set.created_at


# ──────────────────────────── move_workout_date ────────────────────────────


def test_move_workout_date_moves_workout_without_sets(
    fake_table, workout_factory, monkeypatch
):
    repo = DynamoWorkoutRepository(table=fake_table)
    workout = workout_factory()

    delete_calls: dict = {}

    def fake_delete(user_sub, workout_date, workout_id):
        delete_calls["user_sub"] = user_sub
        delete_calls["date"] = workout_date
        delete_calls["workout_id"] = workout_id

    monkeypatch.setattr(repo, "delete_workout_and_sets", fake_delete)

    repo.move_workout_date(USER_SUB, workout, TEST_DATE_3, sets=[])

    assert delete_calls == {
        "user_sub": USER_SUB,
        "date": TEST_DATE_2,
        "workout_id": TEST_WORKOUT_ID_2,
    }

    item = fake_table.last_put_kwargs["Item"]
    assert item["PK"] == db.build_user_pk(USER_SUB)
    assert item["SK"] == db.build_workout_sk(TEST_DATE_3, TEST_WORKOUT_ID_2)


def test_move_workout_date_raises_workoutrepoerror_when_write_fails(
    failing_put_table, workout_factory
):
    repo = DynamoWorkoutRepository(table=failing_put_table)
    workout = workout_factory()

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.move_workout_date(USER_SUB, workout, TEST_DATE_3, sets=[])

    assert "Failed to write new workout or sets" in str(excinfo.value)


def test_move_workout_date_raises_workoutrepoerror_when_delete_fails(
    fake_table, workout_factory, monkeypatch
):
    repo = DynamoWorkoutRepository(table=fake_table)
    workout = workout_factory()

    def fake_delete(user_sub, workout_date, workout_id):
        raise WorkoutRepoError("failed to delete old workout")

    monkeypatch.setattr(repo, "delete_workout_and_sets", fake_delete)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo.move_workout_date(USER_SUB, workout, TEST_DATE_3, sets=[])

    assert "New workout created but failed to delete old one" in str(excinfo.value)


def test_move_workout_date_calls_safe_put_for_sets(
    fake_table, workout_factory, set_factory, monkeypatch
):
    repo = DynamoWorkoutRepository(table=fake_table)

    workout = workout_factory()
    set1 = set_factory()

    calls: list[dict] = []

    monkeypatch.setattr(repo, "_safe_put", lambda item: calls.append(item))

    repo.move_workout_date(USER_SUB, workout, TEST_DATE_3, sets=[set1])

    assert len(calls) == 2
