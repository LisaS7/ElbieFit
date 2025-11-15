import boto3

from app.settings import settings
from app.utils import db


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
