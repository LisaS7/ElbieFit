import pytest
from botocore.exceptions import ClientError

from app.repositories.base import DynamoRepository
from app.repositories.errors import RepoError


class FakeRepo(DynamoRepository[dict]):
    """
    Minimal concrete subclass so we can instantiate DynamoRepository.
    We don't call _to_model in these tests, so returning the item is fine.
    """

    def _to_model(self, item: dict) -> dict:
        return item


def test_base_repo_to_model_raises_not_implemented(fake_table):
    # Use the base class directly so we hit the NotImplementedError path
    repo = DynamoRepository(table=fake_table)

    with pytest.raises(NotImplementedError):
        repo._to_model({"PK": "USER#1"})


# ──────────────────────────── __init__ behaviour ────────────────────────────


def test_init_uses_explicit_table(fake_table):
    repo = FakeRepo(table=fake_table)
    assert repo._table is fake_table


def test_init_uses_db_get_table_when_table_not_provided(monkeypatch):
    # We'll patch app.utils.db.get_table to return a sentinel object
    from app.utils import db as db_module

    sentinel_table = object()

    def fake_get_table():
        return sentinel_table

    monkeypatch.setattr(db_module, "get_table", fake_get_table)

    repo = FakeRepo()
    assert repo._table is sentinel_table


# ──────────────────────────── _safe_query ────────────────────────────


def test_safe_query_returns_items(fake_table):
    fake_table.response = {"Items": [{"PK": "USER#1"}, {"PK": "USER#2"}]}
    repo = FakeRepo(table=fake_table)

    result = repo._safe_query(KeyConditionExpression="whatever")

    assert result == fake_table.response["Items"]
    assert fake_table.last_query_kwargs == {"KeyConditionExpression": "whatever"}


def test_safe_query_missing_items_returns_empty_list(fake_table):
    # No "Items" key in response → should safely return []
    fake_table.response = {}
    repo = FakeRepo(table=fake_table)

    result = repo._safe_query()

    assert result == []


def test_safe_query_wraps_client_error(failing_query_table):
    repo = FakeRepo(table=failing_query_table)

    with pytest.raises(RepoError) as excinfo:
        repo._safe_query()

    assert "Failed to query database" in str(excinfo.value)


# ──────────────────────────── _safe_put ────────────────────────────


def test_safe_put_calls_table_put_item(fake_table):
    repo = FakeRepo(table=fake_table)
    item = {"PK": "USER#1", "SK": "WORKOUT#2025-11-03#W1"}

    repo._safe_put(item)

    assert fake_table.last_put_kwargs == {"Item": item}


def test_safe_put_wraps_client_error(failing_put_table):
    repo = FakeRepo(table=failing_put_table)

    with pytest.raises(RepoError) as excinfo:
        repo._safe_put({"PK": "USER#1"})

    assert "Failed to write to database" in str(excinfo.value)


# ──────────────────────────── _safe_get ────────────────────────────


def test_safe_get_returns_item(fake_table):
    fake_table.response = {"Item": {"PK": "USER#1", "SK": "WORKOUT#2025-11-03#W1"}}
    repo = FakeRepo(table=fake_table)

    result = repo._safe_get(Key={"PK": "USER#1", "SK": "WORKOUT#2025-11-03#W1"})

    assert result == {"PK": "USER#1", "SK": "WORKOUT#2025-11-03#W1"}
    assert fake_table.last_get_kwargs == {
        "Key": {"PK": "USER#1", "SK": "WORKOUT#2025-11-03#W1"}
    }


def test_safe_get_returns_none_when_item_missing(fake_table):
    # No "Item" key → should return None
    fake_table.response = {}
    repo = FakeRepo(table=fake_table)

    result = repo._safe_get(Key={"PK": "USER#1"})

    assert result is None


def _client_error(op_name: str) -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": "500", "Message": f"Boom in {op_name}"}},
        operation_name=op_name,
    )


class FailingGetTable:
    def get_item(self, **kwargs):
        raise _client_error("GetItem")


def test_safe_get_wraps_client_error():
    repo = FakeRepo(table=FailingGetTable())

    with pytest.raises(RepoError) as excinfo:
        repo._safe_get(Key={"PK": "USER#1"})

    assert "Failed to read from database" in str(excinfo.value)


# ──────────────────────────── _safe_delete ────────────────────────────


class DeleteTable:
    def __init__(self):
        self.last_delete_kwargs = None

    def delete_item(self, **kwargs):
        self.last_delete_kwargs = kwargs


def test_safe_delete_calls_table_delete_item():
    table = DeleteTable()
    repo = FakeRepo(table=table)

    repo._safe_delete(Key={"PK": "USER#1", "SK": "WORKOUT#2025-11-03#W1"})

    assert table.last_delete_kwargs == {
        "Key": {"PK": "USER#1", "SK": "WORKOUT#2025-11-03#W1"}
    }


class FailingDeleteTable:
    def delete_item(self, **kwargs):
        raise _client_error("DeleteItem")


def test_safe_delete_wraps_client_error():
    repo = FakeRepo(table=FailingDeleteTable())

    with pytest.raises(RepoError) as excinfo:
        repo._safe_delete(Key={"PK": "USER#1"})

    assert "Failed to delete from database" in str(excinfo.value)
