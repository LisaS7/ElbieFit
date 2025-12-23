from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException

from app.utils import demo as demo_utils
from tests.test_data import USER_PK, USER_SUB

# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────


def make_client_error(code: str) -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "nope"}},
        operation_name="PutItem",
    )


@dataclass
class StubModel:
    pk: str
    sk: str
    type: str = "stub"

    def to_ddb_item(self) -> dict[str, Any]:
        return {"PK": self.pk, "SK": self.sk, "type": self.type}


class FakeBatchWriter:
    def __init__(self, table: "FakeDynamoTable"):
        self._table = table

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def delete_item(self, *, Key: dict[str, Any]) -> None:
        self._table.deleted_keys.append(Key)


class FakeDynamoTable:
    """
    Minimal fake Dynamo table that supports:
      - put_item(...)
      - query(...)
      - batch_writer() context manager
    """

    def __init__(self):
        self.put_calls: list[dict[str, Any]] = []
        self.deleted_keys: list[dict[str, Any]] = []
        self.query_calls: list[dict[str, Any]] = []
        self._query_responses: list[dict[str, Any]] = []
        self.put_side_effect: Exception | None = None

        self._items: dict[tuple[str, str], dict[str, Any]] = {}

    def queue_query_responses(self, responses: list[dict[str, Any]]) -> None:
        self._query_responses = list(responses)

    def put_item(self, **kwargs) -> dict[str, Any]:
        if self.put_side_effect:
            raise self.put_side_effect
        self.put_calls.append(kwargs)

        item = kwargs.get("Item")
        if item and "PK" in item and "SK" in item:
            self._items[(item["PK"], item["SK"])] = dict(item)

        return {}

    def get_item(self, **kwargs) -> dict[str, Any]:
        key = kwargs.get("Key") or {}
        pk = key.get("PK")
        sk = key.get("SK")
        if pk is None or sk is None:
            return {}
        item = self._items.get((pk, sk))
        return {"Item": dict(item)} if item else {}

    def query(self, **kwargs) -> dict[str, Any]:
        self.query_calls.append(kwargs)
        if not self._query_responses:
            return {"Items": []}
        return self._query_responses.pop(0)

    def batch_writer(self) -> FakeBatchWriter:
        return FakeBatchWriter(self)


@pytest.fixture
def fake_table(monkeypatch) -> FakeDynamoTable:
    table = FakeDynamoTable()
    monkeypatch.setattr(demo_utils, "get_table", lambda: table)
    return table


# ─────────────────────────────────────────────────────────
# enforce_cooldown
# ─────────────────────────────────────────────────────────


def test_enforce_cooldown_puts_item_with_cutoff(fake_table, monkeypatch):
    # Freeze time in the module under test (it imports time directly)
    monkeypatch.setattr(demo_utils.time, "time", lambda: 1000)

    demo_utils.enforce_cooldown(user_sub=USER_SUB, cooldown_seconds=300)

    assert len(fake_table.put_calls) == 1
    call = fake_table.put_calls[0]

    assert call["Item"]["PK"] == f"DEMO_RESET#{USER_SUB}"
    assert call["Item"]["SK"] == "STATE"
    assert call["Item"]["last_reset_at"] == 1000

    assert (
        call["ConditionExpression"]
        == "attribute_not_exists(last_reset_at) OR last_reset_at <= :cutoff"
    )
    assert call["ExpressionAttributeValues"] == {":cutoff": 700}


def test_enforce_cooldown_raises_429_on_conditional_check_failed(
    fake_table, monkeypatch
):
    monkeypatch.setattr(demo_utils.time, "time", lambda: 1000)
    fake_table.put_side_effect = make_client_error("ConditionalCheckFailedException")

    with pytest.raises(HTTPException) as exc:
        demo_utils.enforce_cooldown(user_sub=USER_SUB, cooldown_seconds=300)

    assert exc.value.status_code == 429
    assert "cooldown" in exc.value.detail.lower()


def test_enforce_cooldown_raises_500_on_other_client_error(fake_table, monkeypatch):
    monkeypatch.setattr(demo_utils.time, "time", lambda: 1000)
    fake_table.put_side_effect = make_client_error(
        "ProvisionedThroughputExceededException"
    )

    with pytest.raises(HTTPException) as exc:
        demo_utils.enforce_cooldown(user_sub=USER_SUB, cooldown_seconds=300)

    assert exc.value.status_code == 500
    assert "cooldown" in exc.value.detail.lower()


# ─────────────────────────────────────────────────────────
# _purge_user_items
# ─────────────────────────────────────────────────────────


def test_purge_user_items_deletes_all_items_across_pages(fake_table):
    fake_table.queue_query_responses(
        [
            {
                "Items": [
                    {"PK": USER_PK, "SK": "A"},
                    {"PK": USER_PK, "SK": "B"},
                ],
                "LastEvaluatedKey": {"PK": USER_PK, "SK": "B"},
            },
            {
                "Items": [
                    {"PK": USER_PK, "SK": "C"},
                ],
                # no LEK => stop
            },
        ]
    )

    deleted = demo_utils._purge_user_items(user_pk=USER_PK)

    assert deleted == 3
    assert fake_table.deleted_keys == [
        {"PK": USER_PK, "SK": "A"},
        {"PK": USER_PK, "SK": "B"},
        {"PK": USER_PK, "SK": "C"},
    ]

    # query called twice, second includes ExclusiveStartKey
    assert len(fake_table.query_calls) == 2
    assert fake_table.query_calls[0]["ExpressionAttributeValues"] == {":pk": USER_PK}
    assert "ExclusiveStartKey" not in fake_table.query_calls[0]
    assert fake_table.query_calls[1]["ExclusiveStartKey"] == {"PK": USER_PK, "SK": "B"}


def test_purge_user_items_handles_empty_pages(fake_table):
    fake_table.queue_query_responses(
        [
            {"Items": [], "LastEvaluatedKey": {"PK": USER_PK, "SK": "Z"}},
            {"Items": [{"PK": USER_PK, "SK": "A"}]},
        ]
    )

    deleted = demo_utils._purge_user_items(user_pk=USER_PK)

    assert deleted == 1
    assert fake_table.deleted_keys == [{"PK": USER_PK, "SK": "A"}]


# ─────────────────────────────────────────────────────────
# reset_user
# ─────────────────────────────────────────────────────────


def test_reset_user_forbidden_when_not_demo_user(monkeypatch):
    monkeypatch.setattr(demo_utils.settings, "DEMO_USER_SUB", "demo-sub")

    with pytest.raises(HTTPException) as exc:
        demo_utils.reset_user(user_sub="not-demo")

    assert exc.value.status_code == 403
    assert "demo" in exc.value.detail.lower()


def test_reset_user_happy_path_seeds_expected_items(fake_table, monkeypatch):
    monkeypatch.setattr(demo_utils.settings, "DEMO_USER_SUB", USER_SUB)

    purge_calls: dict[str, Any] = {}

    def fake_purge_user_items(*, user_pk: str) -> int:
        purge_calls["user_pk"] = user_pk
        return 12

    monkeypatch.setattr(demo_utils, "_purge_user_items", fake_purge_user_items)

    profile = StubModel(pk=USER_PK, sk="PROFILE", type="profile")
    exercises = [
        StubModel(pk=USER_PK, sk="EX#1", type="exercise"),
        StubModel(pk=USER_PK, sk="EX#2", type="exercise"),
    ]
    workout_1 = StubModel(pk=USER_PK, sk="WO#1", type="workout")
    set_1a = StubModel(pk=USER_PK, sk="SET#1A", type="set")
    set_1b = StubModel(pk=USER_PK, sk="SET#1B", type="set")
    workouts = [(workout_1, [set_1a, set_1b])]

    monkeypatch.setattr(demo_utils, "build_demo_profile", lambda pk: profile)

    build_exercises_calls: dict[str, Any] = {}

    def fake_build_exercises(pk: str, dataset: str):
        build_exercises_calls["args"] = (pk, dataset)
        return exercises

    monkeypatch.setattr(demo_utils, "build_exercises", fake_build_exercises)

    build_workouts_calls: dict[str, Any] = {}

    def fake_build_workouts(pk: str, dataset: str):
        build_workouts_calls["args"] = (pk, dataset)
        return workouts

    monkeypatch.setattr(demo_utils, "build_workouts", fake_build_workouts)

    demo_utils.reset_user(user_sub=USER_SUB)

    assert purge_calls["user_pk"] == USER_PK
    assert build_exercises_calls["args"] == (USER_PK, "demo")
    assert build_workouts_calls["args"] == (USER_PK, "demo")

    # 1 profile + 2 exercises + 1 workout + 2 sets = 6
    assert len(fake_table.put_calls) == 6

    put_items = [c["Item"] for c in fake_table.put_calls]
    assert put_items == [
        profile.to_ddb_item(),
        exercises[0].to_ddb_item(),
        exercises[1].to_ddb_item(),
        workout_1.to_ddb_item(),
        set_1a.to_ddb_item(),
        set_1b.to_ddb_item(),
    ]


def test_reset_user_raises_500_on_client_error(fake_table, monkeypatch):
    monkeypatch.setattr(demo_utils.settings, "DEMO_USER_SUB", USER_SUB)

    # Ensure purge happens then a put fails
    monkeypatch.setattr(demo_utils, "_purge_user_items", lambda *, user_pk: 0)
    monkeypatch.setattr(
        demo_utils, "build_demo_profile", lambda pk: StubModel(pk=pk, sk="PROFILE")
    )
    monkeypatch.setattr(demo_utils, "build_exercises", lambda pk, dataset: [])
    monkeypatch.setattr(demo_utils, "build_workouts", lambda pk, dataset: [])

    fake_table.put_side_effect = make_client_error("InternalServerError")

    with pytest.raises(HTTPException) as exc:
        demo_utils.reset_user(user_sub=USER_SUB)

    assert exc.value.status_code == 500
    assert "reset" in exc.value.detail.lower()


def test_reset_user_raises_500_on_unexpected_exception(fake_table, monkeypatch):
    """
    This test assumes you add the catch-all:

        except Exception as e:
            logger.exception("Unexpected error during demo reset", ...)
            raise HTTPException(500, "Demo reset failed.") from e
    """
    monkeypatch.setattr(demo_utils.settings, "DEMO_USER_SUB", USER_SUB)

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(demo_utils, "_purge_user_items", boom)

    with pytest.raises(HTTPException) as exc:
        demo_utils.reset_user(user_sub=USER_SUB)

    assert exc.value.status_code == 500
    assert "reset" in exc.value.detail.lower()
