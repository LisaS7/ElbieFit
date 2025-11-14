from app.repositories.profile import DynamoProfileRepository


def test_get_for_user_success(fake_table):
    user_sub = "test-123"

    expected_item = {
        "PK": f"USER#{user_sub}",
        "SK": "PROFILE",
        "display_name": "Lisa Test",
        "email": "lisa@example.com",
        "timezone": "Europe/London",
    }

    fake_table.response = {
        "Item": expected_item,
        "ResponseMetadata": {"RequestId": "req-123"},
    }

    repo = DynamoProfileRepository(fake_table)

    profile = repo.get_for_user(user_sub)

    assert profile == expected_item

    # called Dynamo with right key + ConsistentRead
    assert fake_table.last_get_kwargs == {
        "Key": {"PK": f"USER#{user_sub}", "SK": "PROFILE"},
        "ConsistentRead": True,
    }


def test_get_for_user_not_found_returns_none(fake_table):
    user_sub = "test-123"
    repo = DynamoProfileRepository(fake_table)
    result = repo.get_for_user(user_sub)
    assert result is None
