import pytest

from app.repositories.errors import WorkoutRepoError
from app.repositories.workout import DynamoWorkoutRepository
from tests.test_data import TEST_WORKOUT_SK_1, TEST_WORKOUT_SK_2, USER_PK


def test_to_model_wraps_validation_error_in_workoutrepoerror(fake_table):
    # Missing required fields -> Pydantic should blow up
    bad_item = {
        "PK": USER_PK,
        "SK": TEST_WORKOUT_SK_1,
        "type": "workout",
        # missing date, name, etc.
    }

    repo = DynamoWorkoutRepository(table=fake_table)

    with pytest.raises(WorkoutRepoError) as excinfo:
        repo._to_model(bad_item)

    assert "Failed to create workout model" in str(excinfo.value)


def test_to_model_raises_for_unknown_type(fake_table):
    repo = DynamoWorkoutRepository(table=fake_table)

    wrong_type_item = {
        "PK": USER_PK,
        "SK": TEST_WORKOUT_SK_2,
        "type": "lunch",
    }

    with pytest.raises(WorkoutRepoError) as err:
        repo._to_model(wrong_type_item)

    assert "Unknown item type" in str(err.value)
