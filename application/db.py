import os
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

SF_USER = os.getenv("SF_USER")
SF_PASSWORD = os.getenv("SF_PASSWORD")
SF_ACCOUNT = os.getenv("SF_ACCOUNT")
SF_WAREHOUSE = os.getenv("SF_WAREHOUSE")
SF_DATABASE = os.getenv("SF_DATABASE")
SF_SCHEMA = os.getenv("SF_SCHEMA")

def get_snowflake_connection():
    params = {
        "user": SF_USER,
        "password": SF_PASSWORD,
        "account": SF_ACCOUNT,
        "warehouse": SF_WAREHOUSE,
        "database": SF_DATABASE,
        "schema": SF_SCHEMA,
    }
    missing = [k for k, v in params.items() if not v]
    if missing:
        raise RuntimeError(f"Missing Snowflake env vars: {', '.join(missing)}")
    role = os.getenv("SF_ROLE")
    if role:
        params["role"] = role
    return snowflake.connector.connect(**params)

def run_query_df(sql: str, params: dict | None = None):
    conn = get_snowflake_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or {})
        df = cur.fetch_pandas_all()
    finally:
        cur.close()
        conn.close()
    return df