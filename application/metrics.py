from datetime import timedelta
import pandas as pd
from typing import List
from queries import query_cc_transactions_snowflake, query_bank_transactions_snowflake

def build_correlated_payments(
    start_date: str,
    end_date: str,
    date_tolerance_days: int = 3,
) -> List[dict]:
    start_buf = (pd.to_datetime(start_date) - timedelta(days=date_tolerance_days)).date().isoformat()
    end_buf = (pd.to_datetime(end_date) + timedelta(days=date_tolerance_days)).date().isoformat()

    cc_df = query_cc_transactions_snowflake(
        start_date=start_buf,
        end_date=end_buf,
        desc_filter=None,
        category_filter=None,
        amount_min=None,
        amount_max=None,
        limit=5000,
    )
    bank_df = query_bank_transactions_snowflake(
        start_date=start_buf,
        end_date=end_buf,
        desc_filter=None,
        _category_filter=None,
        amount_min=None,
        amount_max=None,
        limit=5000,
    )

    if cc_df.empty or bank_df.empty:
        return []

    cc_df["TRANSACTION_DATE"] = pd.to_datetime(cc_df["TRANSACTION_DATE"])
    bank_df["TRANSACTION_DATE"] = pd.to_datetime(bank_df["TRANSACTION_DATE"])

    cc_payments = cc_df[cc_df["AMOUNT"] > 0].copy()
    if cc_payments.empty:
        return []

    bank_out = bank_df[bank_df["AMOUNT"] < 0].copy()
    bank_out["AMOUNT_ABS"] = bank_out["AMOUNT"].abs()
    cc_payments["AMOUNT_ABS"] = cc_payments["AMOUNT"].abs()

    merged = cc_payments.merge(
        bank_out,
        how="inner",
        left_on="AMOUNT_ABS",
        right_on="AMOUNT_ABS",
        suffixes=("_CC", "_BANK"),
    )

    if merged.empty:
        return []

    merged["DATE_DIFF"] = (merged["TRANSACTION_DATE_BANK"] - merged["TRANSACTION_DATE_CC"]).dt.days.abs()
    merged = merged[merged["DATE_DIFF"] <= date_tolerance_days]

    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)
    merged = merged[
        (merged["TRANSACTION_DATE_CC"].between(start_ts, end_ts)) |
        (merged["TRANSACTION_DATE_BANK"].between(start_ts, end_ts))
    ]

    results = []
    for _, row in merged.iterrows():
        results.append(
            {
                "amount": float(row["AMOUNT_CC"]),
                "cc_date": row["TRANSACTION_DATE_CC"].date().isoformat(),
                "cc_desc": row["DESCRIPTION_CC"],
                "bank_date": row["TRANSACTION_DATE_BANK"].date().isoformat(),
                "bank_desc": row["DESCRIPTION_BANK"],
                "bank_type": row["TYPE_BANK"],
                "date_diff": int(row["DATE_DIFF"]),
            }
        )

    results.sort(key=lambda r: r["cc_date"], reverse=True)
    return results


def compute_dashboard_metrics(df: pd.DataFrame, start_str: str, end_str: str):
    if df.empty:
        return {
            "num_tx": 0,
            "total_spent": 0.0,
            "total_received": 0.0,
            "net": 0.0,
            "avg_daily_spend": 0.0,
            "daily_labels": [],
            "daily_spend": [],
            "cat_labels": [],
            "cat_values": [],
        }

    num_tx = len(df)
    total_spent = float(df.loc[df["AMOUNT"] < 0, "AMOUNT"].sum())
    total_received = float(df.loc[df["AMOUNT"] > 0, "AMOUNT"].sum())
    net = total_received + total_spent

    daily = df.copy()
    daily["TRANSACTION_DATE"] = pd.to_datetime(daily["TRANSACTION_DATE"])
    daily_out = (
        daily[daily["AMOUNT"] < 0]
        .groupby("TRANSACTION_DATE")["AMOUNT"]
        .sum()
        .abs()
        .reset_index()
        .sort_values("TRANSACTION_DATE")
    )

    if not daily_out.empty:
        daily_labels = daily_out["TRANSACTION_DATE"].dt.strftime("%Y-%m-%d").tolist()
        daily_spend = daily_out["AMOUNT"].round(2).tolist()
        days_in_range = (pd.to_datetime(end_str) - pd.to_datetime(start_str)).days or 1
        avg_daily_spend = abs(total_spent) / days_in_range
    else:
        daily_labels = []
        daily_spend = []
        avg_daily_spend = 0.0

    spend = (
        df[df["AMOUNT"] < 0]
        .groupby("CATEGORY", dropna=False)["AMOUNT"]
        .sum()
        .abs()
        .sort_values(ascending=False)
        .head(7)
        .reset_index()
    )

    if not spend.empty:
        spend_cat_labels = spend["CATEGORY"].fillna("Uncategorized").tolist()
        spend_cat_values = spend["AMOUNT"].round(2).tolist()
    else:
        spend_cat_labels = []
        spend_cat_values = []

    income = (
        df[df["AMOUNT"] > 0]
        .groupby("CATEGORY", dropna=False)["AMOUNT"]
        .sum()
        .sort_values(ascending=False)
        .abs()
        .head(7)
        .reset_index()
    )

    cat_labels = spend_cat_labels
    cat_values = spend_cat_values

    if not income.empty:
        income_cat_labels = income["CATEGORY"].fillna("Uncategorized").tolist()
        income_cat_values = income["AMOUNT"].round(2).tolist()
    else:
        income_cat_labels = []
        income_cat_values = []

    return {
        "num_tx": num_tx,
        "total_spent": total_spent,
        "total_received": total_received,
        "net": net,
        "avg_daily_spend": avg_daily_spend,
        "daily_labels": daily_labels,
        "daily_spend": daily_spend,
        "cat_labels": cat_labels,
        "cat_values": cat_values,
        "spend_cat_labels": spend_cat_labels,
        "spend_cat_values": spend_cat_values,
        "income_cat_labels": income_cat_labels,
        "income_cat_values": income_cat_values,
    }