from typing import Any, Dict, Generic, List, TypeVar

from botocore.exceptions import ClientError

from app.repositories.errors import RepoError
from app.utils.log import logger

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
            logger.exception("DynamoDB query failed")
            raise RepoError("Failed to query database") from e

    def _safe_put(self, item: dict) -> None:
        """Safely put item"""
        try:
            self._table.put_item(Item=item)
        except ClientError as e:
            logger.exception("DynamoDB put_item failed")
            raise RepoError("Failed to write to database") from e

    def _safe_update(self, **kwargs) -> Dict[str, Any]:
        try:
            resp = self._table.update_item(**kwargs)
            return resp
        except ClientError as e:
            logger.exception("DynamoDB update_item failed")
            raise RepoError("Failed to update database") from e

    def _safe_get(self, **kwargs) -> dict | None:
        try:
            resp = self._table.get_item(**kwargs)
            return resp.get("Item")
        except ClientError as e:
            logger.exception("DynamoDB get_item failed")
            raise RepoError("Failed to read from database") from e

    def _safe_delete(self, **kwargs) -> None:
        try:
            self._table.delete_item(**kwargs)
        except ClientError as e:
            logger.exception("DynamoDB delete_item failed")
            raise RepoError("Failed to delete from database") from e
