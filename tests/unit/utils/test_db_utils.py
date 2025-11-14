from app.utils import db


class FakeDynamoTable:
    """
    Tiny fake Dynamo table that returns a preconfigured response.
    """

    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def get_item(self, **kwargs):
        self.last_kwargs = kwargs
        return self.response


def test_get_user_profile_happy_path(monkeypatch):
    user_sub = "abc-123"

    fake_response = {
        "Item": {
            "PK": f"USER#{user_sub}",
            "SK": "PROFILE",
            "display_name": "Lisa Test",
            "email": "lisa@example.com",
            "timezone": "Europe/London",
        },
        "ResponseMetadata": {"RequestId": "req-123"},
    }

    fake_table = FakeDynamoTable(fake_response)
    monkeypatch.setattr(db, "_table", fake_table)

    result = db.get_user_profile(user_sub)

    # We should have a deserialised dict
    assert result is not None
    assert result["PK"] == f"USER#{user_sub}"
    assert result["SK"] == "PROFILE"
    assert result["display_name"] == "Lisa Test"
    assert result["email"] == "lisa@example.com"

    # And the call to DynamoDB should have used the right key & options
    assert fake_table.last_kwargs is not None
    assert fake_table.last_kwargs["ConsistentRead"] is True

    key = fake_table.last_kwargs["Key"]
    assert key["PK"] == f"USER#{user_sub}"
    assert key["SK"] == "PROFILE"


def test_get_user_profile_not_found_logs_and_returns_none(monkeypatch, caplog):
    user_sub = "nope-user"

    fake_response = {
        # no "Item" key -> simulates not found
        "ResponseMetadata": {"RequestId": "req-404"},
    }

    fake_table = FakeDynamoTable(fake_response)
    monkeypatch.setattr(db, "_table", fake_table)

    # Capture warnings from our "elbiefit" logger
    with caplog.at_level("WARNING", logger="elbiefit"):
        result = db.get_user_profile(user_sub)

    assert result is None

    # Make sure we actually logged something useful
    messages = " ".join(rec.getMessage() for rec in caplog.records)
    assert "User profile not found" in messages
    assert "req-404" in messages
    assert f"USER#{user_sub}" in messages
