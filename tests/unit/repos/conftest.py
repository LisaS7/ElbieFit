import pytest
from botocore.exceptions import ClientError


class FakeBatchWriter:
    """
    Minimal stand-in for DynamoDB's batch_writer.
    It forwards delete_item calls to the parent FakeTable,
    which records the keys that were 'deleted'.
    """

    def __init__(self, table):
        self._table = table

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def delete_item(self, Key: dict):
        # Record the delete call on the table
        self._table.deleted_keys.append(Key)


class FakeTable:
    """
    A lightweight fake for boto3 DynamoDB Table.
    It captures the arguments used in `query`, `get_item`, and `put_item`,
    and returns a preconfigured response.

    Useful for repository unit tests where we want to
    control DynamoDB responses without hitting AWS.
    """

    def __init__(self, response=None):
        self.response = response or {}
        self.last_query_kwargs = None
        self.last_get_kwargs = None
        self.last_put_kwargs = None
        self.deleted_keys = []

    def query(self, **kwargs):
        self.last_query_kwargs = kwargs
        return self.response

    def get_item(self, **kwargs):
        self.last_get_kwargs = kwargs
        return self.response

    def put_item(self, **kwargs):
        self.last_put_kwargs = kwargs
        return self.response

    def batch_writer(self):
        return FakeBatchWriter(self)


@pytest.fixture
def fake_table():
    """
    Fixture returning a FakeTable instance.
    Tests can override the FakeTable.response to simulate different cases.
    """
    return FakeTable()


def _client_error(op_name: str) -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": "500", "Message": "Boom in {op_name}"}},
        operation_name=op_name,
    )


class FailingQueryTable:
    """Fake table whose query() always raises ClientError."""

    def query(self, *args, **kwargs):
        raise _client_error("Query")


@pytest.fixture
def failing_query_table():
    return FailingQueryTable()


class BadItemsTable:
    def __init__(self):
        self.response = {"Items": [{"type": "workout"}]}  # missing fields

    def query(self, *args, **kwargs):
        return self.response


@pytest.fixture
def bad_items_table():
    return BadItemsTable()


class FailingPutTable:
    def put_item(self, **kwargs):
        raise _client_error("PutItem")


@pytest.fixture
def failing_put_table():
    return FailingPutTable()


class FailingDeleteTable:
    def query(self, *args, **kwargs):
        raise _client_error("Query")


@pytest.fixture
def failing_delete_table():
    return FailingDeleteTable()
