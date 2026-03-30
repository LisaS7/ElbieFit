# Creates the DynamoDB table in DynamoDB Local.
# Run after `docker compose up -d`:
#
#   uv run python -m scripts.create_local_table

import boto3

from app.settings import settings


def main():
    if not settings.DDB_ENDPOINT_URL:
        print("DDB_ENDPOINT_URL is not set — refusing to run against real AWS.")
        raise SystemExit(1)

    client = boto3.client(
        "dynamodb",
        region_name=settings.REGION,
        endpoint_url=settings.DDB_ENDPOINT_URL,
    )

    table_name = settings.DDB_TABLE_NAME

    existing = client.list_tables().get("TableNames", [])
    if table_name in existing:
        print(f"Table '{table_name}' already exists — nothing to do.")
        return

    client.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "ExercisePK", "AttributeType": "S"},
            {"AttributeName": "ExerciseSK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "ExerciseIndex",
                "KeySchema": [
                    {"AttributeName": "ExercisePK", "KeyType": "HASH"},
                    {"AttributeName": "ExerciseSK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )

    print(f"Table '{table_name}' created.")


if __name__ == "__main__":
    main()
