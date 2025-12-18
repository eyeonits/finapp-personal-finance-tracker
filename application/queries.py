import pandas as pd
from db import run_query_df

# Helper to normalize sign quirks for certain accounts (kept here so queries can call it)
def normalize_transaction_signs(df: pd.DataFrame, account_id: str) -> pd.DataFrame:
    df = df.copy()
    apple_card_ids = ["cc_apple", "apple_card"]
    if account_id and account_id.lower() in apple_card_ids:
        df["AMOUNT"] = -df["AMOUNT"]
    return df

# Preload small summary datasets used by the UI charts (keeps behavior similar to original app)
try:
    cc_df = run_query_df(
        "SELECT TRANSACTION_DATE, POST_DATE, DESCRIPTION, CATEGORY, TYPE, AMOUNT, MEMO, ACCOUNT_ID FROM FIN.CC_TRANSACTIONS"
    )
except Exception:
    cc_df = pd.DataFrame(columns=["TRANSACTION_DATE", "POST_DATE", "DESCRIPTION", "CATEGORY", "TYPE", "AMOUNT", "MEMO", "ACCOUNT_ID"])

try:
    bank_df = run_query_df(
        "SELECT POSTED_DATE, EFFECTIVE_DATE, DESCRIPTION, TRANSACTION_TYPE, AMOUNT, RUNNING_BALANCE FROM FIN.BANK_TRANSACTIONS"
    )
except Exception:
    bank_df = pd.DataFrame(columns=["POSTED_DATE", "EFFECTIVE_DATE", "DESCRIPTION", "TRANSACTION_TYPE", "AMOUNT", "RUNNING_BALANCE"])

# Build cc category aggregates (top 10) used by charts as in original
if not cc_df.empty:
    cc_df["TRANSACTION_DATE"] = pd.to_datetime(cc_df["TRANSACTION_DATE"])
    cc_spend = cc_df[cc_df["AMOUNT"] < 0].copy()
    cc_spend["AMOUNT_ABS"] = cc_spend["AMOUNT"].abs()
    cc_cat = (
        cc_spend.groupby("CATEGORY", dropna=False)["AMOUNT_ABS"].sum().sort_values(ascending=False).reset_index()
    )
    cc_cat_top = cc_cat.head(10)
    cc_category_labels = cc_cat_top["CATEGORY"].fillna("Uncategorized").tolist()
    cc_category_values = cc_cat_top["AMOUNT_ABS"].tolist()
else:
    cc_category_labels = []
    cc_category_values = []

# Bank income/expense summary
if not bank_df.empty:
    bank_income = bank_df[bank_df["AMOUNT"] > 0]["AMOUNT"].sum()
    bank_expense = bank_df[bank_df["AMOUNT"] < 0]["AMOUNT"].abs().sum()
else:
    bank_income = 0.0
    bank_expense = 0.0

bank_income_expense_labels = ["Income", "Expenses"]
bank_income_expense_values = [float(bank_income), float(bank_expense)]


def query_cc_transactions_snowflake(
    start_date: str,
    end_date: str,
    desc_filter: str | None,
    category_filter: str | None,
    amount_min: float | None,
    amount_max: float | None,
    limit: int = 2000,
) -> pd.DataFrame:
    where_clauses = ["TRANSACTION_DATE BETWEEN %(start)s AND %(end)s"]
    params: dict[str, object] = {"start": start_date, "end": end_date}

    if desc_filter:
        where_clauses.append("UPPER(DESCRIPTION) LIKE %(desc)s")
        params["desc"] = f"%{desc_filter.upper()}%"

    if category_filter:
        where_clauses.append("UPPER(CATEGORY) LIKE %(cat)s")
        params["cat"] = f"%{category_filter.upper()}%"

    if amount_min is not None:
        where_clauses.append("AMOUNT >= %(amin)s")
        params["amin"] = amount_min

    if amount_max is not None:
        where_clauses.append("AMOUNT <= %(amax)s")
        params["amax"] = amount_max

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT
          TRANSACTION_DATE,
          POST_DATE,
          DESCRIPTION,
          CATEGORY,
          TYPE,
          AMOUNT,
          MEMO,
          ACCOUNT_ID
        FROM FIN.CC_TRANSACTIONS
        WHERE {where_sql}
        ORDER BY TRANSACTION_DATE DESC, POST_DATE DESC
        LIMIT {limit}
    """

    df = run_query_df(sql, params)
    if df.empty:
        return df

    df.columns = [c.upper() for c in df.columns]

    if "ACCOUNT_ID" in df.columns and len(df) > 0:
        account_id = df["ACCOUNT_ID"].iloc[0]
        df = normalize_transaction_signs(df, account_id)

    return df


def query_bank_transactions_snowflake(
    start_date: str,
    end_date: str,
    desc_filter: str | None,
    _category_filter: str | None,
    amount_min: float | None,
    amount_max: float | None,
    limit: int = 2000,
) -> pd.DataFrame:
    where_clauses = ["POSTED_DATE BETWEEN %(start)s AND %(end)s"]
    params: dict[str, object] = {"start": start_date, "end": end_date}

    if desc_filter:
        where_clauses.append("UPPER(DESCRIPTION) LIKE %(desc)s")
        params["desc"] = f"%{desc_filter.upper()}%"

    if amount_min is not None:
        where_clauses.append("AMOUNT >= %(amin)s")
        params["amin"] = amount_min

    if amount_max is not None:
        where_clauses.append("AMOUNT <= %(amax)s")
        params["amax"] = amount_max

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT
          COALESCE(EFFECTIVE_DATE, POSTED_DATE) AS TRANSACTION_DATE,
          POSTED_DATE,
          DESCRIPTION,
          TRANSACTION_TYPE,
          AMOUNT,
          RUNNING_BALANCE,
          CHECK_NUMBER,
          MEMO,
          ACCOUNT_ID
        FROM FIN.BANK_TRANSACTIONS
        WHERE {where_sql}
        ORDER BY POSTED_DATE DESC
        LIMIT {limit}
    """

    df = run_query_df(sql, params)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "TRANSACTION_DATE",
                "POST_DATE",
                "DESCRIPTION",
                "CATEGORY",
                "TYPE",
                "AMOUNT",
                "MEMO",
                "ACCOUNT_ID",
                "RUNNING_BALANCE",
                "CHECK_NUMBER",
            ]
        )

    df = df.rename(
        columns={
            "TRANSACTION_DATE": "TRANSACTION_DATE",
            "POSTED_DATE": "POST_DATE",
            "DESCRIPTION": "DESCRIPTION",
            "TRANSACTION_TYPE": "TYPE",
            "AMOUNT": "AMOUNT",
            "RUNNING_BALANCE": "RUNNING_BALANCE",
            "CHECK_NUMBER": "CHECK_NUMBER",
            "MEMO": "MEMO",
            "ACCOUNT_ID": "ACCOUNT_ID",
        }
    )

    df["CATEGORY"] = df["TYPE"]
    cols = [
        "TRANSACTION_DATE",
        "POST_DATE",
        "DESCRIPTION",
        "CATEGORY",
        "TYPE",
        "AMOUNT",
        "MEMO",
        "ACCOUNT_ID",
        "RUNNING_BALANCE",
        "CHECK_NUMBER",
    ]
    df = df[cols]
    return df