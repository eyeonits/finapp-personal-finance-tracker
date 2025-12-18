import boto3
from boto3.dynamodb.conditions import Key, Attr
import os
import pandas as pd

DDB_REGION = os.getenv("AWS_REGION", "us-east-1")
DDB_TABLE = os.getenv("DDB_TABLE", "bank_transactions")

dynamodb = boto3.resource("dynamodb", region_name=DDB_REGION)
txn_table = dynamodb.Table(DDB_TABLE)

def query_transactions_from_dynamo(
    start_date: str,
    end_date: str,
    desc_filter: str | None = None,
    category_filter: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    limit: int = 2000,
) -> pd.DataFrame:
    # Query by date range on GSI
    resp = txn_table.query(
        IndexName="gsi_user_date",
        KeyConditionExpression=Key("user_id").eq("household") &
                               Key("transaction_date").between(start_date, end_date)
    )

    items = resp.get("Items", [])

    # Handle pagination if needed (lots of data)
    while "LastEvaluatedKey" in resp and len(items) < limit:
        resp = txn_table.query(
            IndexName="gsi_user_date",
            KeyConditionExpression=Key("user_id").eq("household") &
                                   Key("transaction_date").between(start_date, end_date),
            ExclusiveStartKey=resp["LastEvaluatedKey"]
        )
        items.extend(resp.get("Items", []))

    # Convert to DataFrame
    if not items:
        return pd.DataFrame(columns=[
            "TRANSACTION_DATE", "POST_DATE", "DESCRIPTION",
            "CATEGORY", "TYPE", "AMOUNT", "MEMO", "ACCOUNT_ID"
        ])

    df = pd.DataFrame(items)

    # Normalize column names to match your existing dashboard code
    df = df.rename(columns={
        "transaction_date": "TRANSACTION_DATE",
        "post_date": "POST_DATE",
        "description": "DESCRIPTION",
        "category": "CATEGORY",
        "type": "TYPE",
        "amount": "AMOUNT",
        "memo": "MEMO",
        "account_id": "ACCOUNT_ID",
    })

    # Convert types
    df["AMOUNT"] = df["AMOUNT"].astype(float)

    # Apply filters in Python
    if desc_filter:
        mask = df["DESCRIPTION"].str.contains(desc_filter, case=False, na=False)
        df = df[mask]

    if category_filter:
        mask = df["CATEGORY"].str.contains(category_filter, case=False, na=False)
        df = df[mask]

    if amount_min is not None:
        df = df[df["AMOUNT"] >= amount_min]

    if amount_max is not None:
        df = df[df["AMOUNT"] <= amount_max]

    # Limit rows
    if len(df) > limit:
        df = df.head(limit)

    return df
