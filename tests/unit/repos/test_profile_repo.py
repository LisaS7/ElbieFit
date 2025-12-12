from app.repositories.profile import DynamoProfileRepository
from tests.test_data import USER_EMAIL, USER_PK, USER_SUB


def test_get_for_user_success(fake_table):
    expected_item = {
        "PK": USER_PK,
        "SK": "PROFILE",
        "display_name": "Lisa Test",
        "email": USER_EMAIL,
        "timezone": "Europe/London",
    }

    fake_table.response = {
        "Item": expected_item,
        "ResponseMetadata": {"RequestId": "req-123"},
    }

    repo = DynamoProfileRepository(table=fake_table)

    profile = repo.get_for_user(USER_SUB)

    assert profile == expected_item
    assert fake_table.last_get_kwargs == {
        "Key": {"PK": USER_PK, "SK": "PROFILE"},
        "ConsistentRead": True,
    }


def test_get_for_user_not_found_returns_none(fake_table):
    repo = DynamoProfileRepository(table=fake_table)
    result = repo.get_for_user(USER_SUB)
    assert result is None


# def test_get_for_user_wraps_repo_error(failing_get_table):
#     repo = DynamoProfileRepository(table=failing_get_table)
#     with pytest.raises(ProfileRepoError):
#         repo.get_for_user(USER_SUB)
