from typing import Generic, List, TypeVar

from botocore.exceptions import ClientError

from app.repositories.errors import RepoError

T = TypeVar("T")


class DynamoRepository(Generic[T]):
    """
    Base class for DynamoDB repositories with common query/error handling.
    """

    def __init__(self, table=None):
        from app.utils import db

        self._table = table or db.get_table()

    def _to_model(self, item: dict) -> T:
        """This should be overridden in subclasses"""
        raise NotImplementedError

    def _safe_query(self, **kwargs) -> List[dict]:
        """Execute query and handle ClientError"""
        try:
            response = self._table.query(**kwargs)
            return response.get("Items", [])
        except ClientError as e:
            raise RepoError("Failed to query database") from e

    def _safe_put(self, item: dict) -> None:
        """Safely put item"""
        try:
            self._table.put_item(Item=item)
        except ClientError as e:
            raise RepoError("Failed to write to database") from e
