from datetime import date

import boto3
import pytest
from botocore.exceptions import ClientError

from app.settings import settings
from app.utils import db
from tests.test_data import USER_SUB


def test_get_dynamo_resource(monkeypatch):
    store = {}

    def fake_resource(service, region_name=None):
        store["service"] = service
        store["region_name"] = region_name
        return "FAKE-RES"

    monkeypatch.setattr(boto3, "resource", fake_resource)

    res = db.get_dynamo_resource()
    assert res == "FAKE-RES"
    assert store["service"] == "dynamodb"
    assert store["region_name"] == settings.REGION


class FakeResource:
    def Table(self, name):
        self.last_name = name
        return f"FAKE-TABLE:{name}"


def test_get_table(monkeypatch):
    fake_res = FakeResource()

    monkeypatch.setattr(db, "get_dynamo_resource", lambda: fake_res)

    table = db.get_table()

    assert table == "FAKE-TABLE:" + settings.DDB_TABLE_NAME
    assert fake_res.last_name == settings.DDB_TABLE_NAME


def test_build_user_pk_formats_correctly():
    assert db.build_user_pk(USER_SUB) == "USER#abc-123"


def test_build_workout_sk_formats_correctly():
    d = date(2025, 11, 4)
    result = db.build_workout_sk(d, "W1")
    assert result == "WORKOUT#2025-11-04#W1"


def test_build_set_sk_formats_correctly_and_zero_pads():
    d = date(2025, 11, 4)

    # 1 → 001
    assert db.build_set_sk(d, "W1", 1) == "WORKOUT#2025-11-04#W1#SET#001"

    # 10 → 010
    assert db.build_set_sk(d, "W1", 10) == "WORKOUT#2025-11-04#W1#SET#010"

    # 123 → 123 (no truncation, still 3 digits)
    assert db.build_set_sk(d, "W1", 123) == "WORKOUT#2025-11-04#W1#SET#123"


# ─────────────────────────────────────────────────────────────
# Rate limiting
# ─────────────────────────────────────────────────────────────


def test_build_rate_limit_pk_formats_correctly():
    assert db.build_rate_limit_pk("client-123") == "RATE#client-123"


def test_build_rate_limit_sk_formats_correctly():
    assert db.build_rate_limit_sk(42) == "WIN#42"


# ──────────────────────────── rate_limit_hit ────────────────────────────


def test_rate_limit_hit_allows_within_limit(frozen_time, fake_table_factory, use_table):
    now = frozen_time
    table = use_table(fake_table_factory(count=3))

    allowed, retry_after = db.rate_limit_hit(
        client_id="client-123", limit=3, ttl_seconds=600
    )

    assert allowed is True
    assert retry_after == 55

    assert table.last_kwargs["Key"] == {"PK": "RATE#client-123", "SK": "WIN#2"}
    assert (
        table.last_kwargs["UpdateExpression"]
        == "ADD #count :inc SET #expires_at = :expires_at"
    )
    assert table.last_kwargs["ExpressionAttributeNames"] == {
        "#count": "count",
        "#expires_at": "expires_at",
    }
    assert table.last_kwargs["ExpressionAttributeValues"] == {
        ":inc": 1,
        ":expires_at": now + 600,
    }
    assert table.last_kwargs["ReturnValues"] == "UPDATED_NEW"


def test_rate_limit_hit_blocks_when_exceeded(
    frozen_time, fake_table_factory, use_table
):
    use_table(fake_table_factory(count=4))  # limit=3, so exceeded

    allowed, retry_after = db.rate_limit_hit(
        client_id="client-123", limit=3, ttl_seconds=600
    )

    assert allowed is False
    assert retry_after == 55


def test_rate_limit_hit_raises_rate_limit_ddb_error_on_clienterror(
    frozen_time, monkeypatch
):
    class ErrorTable:
        def update_item(self, **kwargs):
            raise ClientError(
                error_response={
                    "Error": {"Code": "ProvisionedThroughputExceededException"}
                },
                operation_name="UpdateItem",
            )

    monkeypatch.setattr(db, "get_table", lambda: ErrorTable())

    with pytest.raises(db.RateLimitDdbError):
        db.rate_limit_hit(client_id="client-123", limit=3, ttl_seconds=600)
