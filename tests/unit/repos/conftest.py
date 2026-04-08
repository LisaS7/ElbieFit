import pytest

from tests.fakes import FakeBatchWriter, FakeTable, _client_error

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def client_error():
    """
    Fixture returning a helper function to build ClientError instances.
    Usage:
        err = client_error("Query")
    """
    return _client_error


@pytest.fixture
def fake_table() -> FakeTable:
    """
    Fixture returning a FakeTable instance.
    Tests can override the FakeTable.response to simulate DynamoDB responses.
    """
    return FakeTable()


@pytest.fixture
def failing_query_table() -> FakeTable:
    return FakeTable(fail_on={"query"})


@pytest.fixture
def failing_get_table() -> FakeTable:
    return FakeTable(fail_on={"get_item"})


@pytest.fixture
def failing_put_table() -> FakeTable:
    return FakeTable(fail_on={"put_item"})


@pytest.fixture
def failing_delete_table() -> FakeTable:
    return FakeTable(fail_on={"delete_item"})


@pytest.fixture
def failing_update_table() -> FakeTable:
    return FakeTable(fail_on={"update_item"})


@pytest.fixture
def bad_items_table() -> FakeTable:
    """
    Returns malformed Items for parse-error tests.
    """
    return FakeTable(response={"Items": [{"type": "workout"}]})
