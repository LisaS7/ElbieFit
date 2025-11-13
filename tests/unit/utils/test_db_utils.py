from app.utils import db


class FakeDynamoClient:
    """
    Tiny fake Dynamo client that just records the last call
    and returns a preconfigured response.
    """

    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def get_item(self, **kwargs):
        self.last_kwargs = kwargs
        return self.response


def test_unmarshal_converts_dynamodb_types():
    # Given a Dynamo-style item
    item = {
        "PK": {"S": "USER#123"},
        "age": {"N": "42"},
        "tags": {"L": [{"S": "strength"}, {"S": "cardio"}]},
    }

    result = db._unmarshal(item)  # type: ignore[attr-defined]

    # Then we get normal Python types
    assert result["PK"] == "USER#123"
    assert result["age"] == 42
    assert result["tags"] == ["strength", "cardio"]


def test_get_user_profile_happy_path(monkeypatch):
    user_sub = "abc-123"

    fake_response = {
        "Item": {
            "PK": {"S": f"USER#{user_sub}"},
            "SK": {"S": "PROFILE"},
            "display_name": {"S": "Lisa Test"},
            "email": {"S": "lisa@example.com"},
            "timezone": {"S": "Europe/London"},
        },
        "ResponseMetadata": {"RequestId": "req-123"},
    }

    fake_client = FakeDynamoClient(fake_response)
    monkeypatch.setattr(db, "_dynamo", fake_client)

    result = db.get_user_profile(user_sub)

    # We should have a deserialised dict
    assert result is not None
    assert result["PK"] == f"USER#{user_sub}"
    assert result["SK"] == "PROFILE"
    assert result["display_name"] == "Lisa Test"
    assert result["email"] == "lisa@example.com"

    # And the call to DynamoDB should have used the right table & key
    assert fake_client.last_kwargs is not None
    assert fake_client.last_kwargs["TableName"] == db.TABLE_NAME
    assert fake_client.last_kwargs["ConsistentRead"] is True

    key = fake_client.last_kwargs["Key"]
    assert key["PK"]["S"] == f"USER#{user_sub}"
    assert key["SK"]["S"] == "PROFILE"


def test_get_user_profile_not_found_logs_and_returns_none(monkeypatch, caplog):
    user_sub = "nope-user"

    fake_response = {
        # no "Item" key -> simulates not found
        "ResponseMetadata": {"RequestId": "req-404"},
    }

    fake_client = FakeDynamoClient(fake_response)
    monkeypatch.setattr(db, "_dynamo", fake_client)

    # Capture warnings from our "elbiefit" logger
    with caplog.at_level("WARNING", logger="elbiefit"):
        result = db.get_user_profile(user_sub)

    assert result is None

    # Make sure we actually logged something useful
    messages = " ".join(rec.getMessage() for rec in caplog.records)
    assert "User profile not found" in messages
    assert "req-404" in messages
    assert f"USER#{user_sub}" in messages
