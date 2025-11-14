import boto3

from app.settings import settings

REGION_NAME = settings.REGION
TABLE_NAME = settings.DDB_TABLE_NAME


def get_dynamo_resource():
    return boto3.resource("dynamodb", region_name=REGION_NAME)


def get_table():
    resource = get_dynamo_resource()
    return resource.Table(TABLE_NAME)  # type: ignore
