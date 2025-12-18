import argparse
import csv
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

# ---------------------------------------------------
# Load .env from the directory of this script
# ---------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / "dev.env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
    print(f"Loaded .env from {ENV_PATH}")
else:
    print(f"WARNING: .env file not found at {ENV_PATH}")


def get_snowflake_connection():
    """Create and return a Snowflake connection using env vars."""
    conn_params = {
        "user": os.getenv("SF_USER"),
        "password": os.getenv("SF_PASSWORD"),
        "account": os.getenv("SF_ACCOUNT"),
        "warehouse": os.getenv("SF_WAREHOUSE"),
        "database": os.getenv("SF_DATABASE"),
        "schema": os.getenv("SF_SCHEMA"),
    }
    role = os.getenv("SF_ROLE")
    if role:
        conn_params["role"] = role

    missing = [k for k, v in conn_params.items() if v is None]
    if missing:
        raise RuntimeError(f"Missing Snowflake env vars: {', '.join(missing)}")

    return snowflake.connector.connect(**conn_params)


def parse_date(value: str) -> Optional[str]:
    """Parse a date string and return it as ISO (YYYY-MM-DD) or None."""
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    # Adjust formats here if your bank uses something else.
    # Common formats: "%m/%d/%Y", "%Y-%m-%d"
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            d = datetime.strptime(value, fmt).date()
            return d.isoformat()
        except ValueError:
            continue

    # If it doesn't match any known format, raise or log
    raise ValueError(f"Unrecognized date format: {value!r}")


def generate_transaction_id(row: Dict[str, Any], account_id: str) -> str:
    """
    Generate a deterministic UUID based on key fields.
    This helps avoid duplicate inserts if we re-ingest the same CSV.
    """
    key_parts = [
        row.get("transaction date", "") or "",
        row.get("post date", "") or "",
        (row.get("description", "") or "").upper(),
        str(row.get("amount", "") or "").strip(),
        account_id.strip(),
    ]
    key = "|".join(key_parts)
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))


def read_csv_rows(csv_path: str) -> List[Dict[str, Any]]:
    """
    Read the CSV file and return a list of dict rows.

    Supports:
      1) Original "standard" CC CSV format:
         transaction date, post date, description, category, type, amount, memo

      2) Apple Card CSV format:
         Transaction Date, Clearing Date, Description, Merchant,
         Category, Type, Amount (USD), Purchased By

      3) Simple Date/Amount CC format (e.g. Amex):
         Date, Description, Amount, Category, (plus other unused cols)

    Internally we normalize to keys:
      "transaction date", "post date", "description",
      "category", "type", "amount", "memo"
    """
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise RuntimeError("CSV has no header row.")

        # Map lower-cased header -> original header name
        field_map = {name.lower().strip(): name for name in reader.fieldnames}

        # --- Format detection ---

        # Apple: has Transaction Date + Clearing Date + Amount (USD)
        is_apple = (
            "transaction date" in field_map
            and "clearing date" in field_map
            and "amount (usd)" in field_map
        )

        # Simple / Amex style: Date + Amount, but NO "transaction date" header
        is_simple_date_amount = (
            "date" in field_map
            and "amount" in field_map
            and "transaction date" not in field_map
        )

        # Standard format: our original header layout
        has_standard_columns = all(
            col in field_map
            for col in [
                "transaction date",
                "post date",
                "description",
                "category",
                "type",
                "amount",
                "memo",
            ]
        )

        rows: List[Dict[str, Any]] = []

        # ---------- APPLE CARD ----------
        if is_apple:
            for col in [
                "transaction date",
                "clearing date",
                "description",
                "category",
                "type",
                "amount (usd)",
            ]:
                if col not in field_map:
                    raise RuntimeError(
                        f"CSV (Apple format) is missing required column: {col}"
                    )

            for raw_row in reader:
                merchant = (
                    raw_row[field_map["merchant"]].strip()
                    if "merchant" in field_map and raw_row.get(field_map["merchant"])
                    else ""
                )
                purchased_by = (
                    raw_row[field_map["purchased by"]].strip()
                    if "purchased by" in field_map and raw_row.get(field_map["purchased by"])
                    else ""
                )

                memo_parts = [p for p in [merchant, purchased_by] if p]
                memo = " | ".join(memo_parts) if memo_parts else ""

                # Flip sign so charges NEGATIVE, payments POSITIVE
                amount_raw = raw_row[field_map["amount (usd)"]].replace(",", "").strip()
                type_value = raw_row[field_map["type"]].strip() if "type" in field_map else ""
                normalized_amount = amount_raw
                try:
                    amt = float(amount_raw)
                    normalized_amount = str(-amt)
                except ValueError:
                    pass

                row = {
                    "transaction date": raw_row[field_map["transaction date"]],
                    "post date": raw_row[field_map["clearing date"]],
                    "description": raw_row[field_map["description"]],
                    "category": raw_row[field_map["category"]],
                    "type": type_value,
                    "amount": normalized_amount,
                    "memo": memo,
                }
                rows.append(row)

        # ---------- AMEX / SIMPLE DATE+AMOUNT FORMAT ----------
        elif is_simple_date_amount:
            for col in ["date", "description", "amount"]:
                if col not in field_map:
                    raise RuntimeError(
                        f"CSV (Date/Amount format) is missing required column: {col}"
                    )

            for raw_row in reader:
                raw_amt = raw_row[field_map["amount"]].replace(",", "").strip()
                txn_type = ""
                normalized_amount = raw_amt

                try:
                    amt = float(raw_amt)
                    # Amex export: charges POSITIVE, payments NEGATIVE
                    if amt > 0:
                        txn_type = "CHARGE"
                    elif amt < 0:
                        txn_type = "PAYMENT"

                    # Normalize: charges NEGATIVE, payments POSITIVE
                    normalized_amount = str(-amt)
                except ValueError:
                    pass

                row = {
                    "transaction date": raw_row[field_map["date"]],
                    "post date": raw_row[field_map["date"]],
                    "description": raw_row[field_map["description"]],
                    "category": raw_row[field_map["category"]] if "category" in field_map else "",
                    "type": txn_type,
                    "amount": normalized_amount,
                    "memo": "",  # no extra columns in memo for Amex
                }
                rows.append(row)

        # ---------- ORIGINAL STANDARD FORMAT ----------
        elif has_standard_columns:
            for raw_row in reader:
                row = {
                    "transaction date": raw_row[field_map["transaction date"]],
                    "post date": raw_row[field_map["post date"]],
                    "description": raw_row[field_map["description"]],
                    "category": raw_row[field_map["category"]],
                    "type": raw_row[field_map["type"]],
                    "amount": raw_row[field_map["amount"]],
                    "memo": raw_row[field_map["memo"]],
                }
                rows.append(row)

        else:
            raise RuntimeError(
                f"Unrecognized CSV layout. Headers: {reader.fieldnames}"
            )

    return rows


def prepare_rows_for_insert(csv_rows: List[Dict[str, Any]], account_id: str) -> List[Dict[str, Any]]:
    """
    Convert raw CSV rows into a structure ready for Snowflake insert.
    """
    prepared = []
    for r in csv_rows:
        tx_date_iso = parse_date(r["transaction date"])
        post_date_iso = parse_date(r["post date"])
        description = r["description"].strip()
        category = r["category"].strip() if r["category"] else None
        tx_type = r["type"].strip() if r["type"] else None

        try:
            amount = float(r["amount"])
        except ValueError:
            raise ValueError(f"Invalid amount value: {r['amount']!r}")

        memo = r["memo"].strip() if r["memo"] else None

        tx_id = generate_transaction_id(
            {
                "transaction date": tx_date_iso or "",
                "post date": post_date_iso or "",
                "description": description,
                "amount": amount,
            },
            account_id=account_id,
        )

        prepared.append(
            {
                "TRANSACTION_ID": tx_id,
                "TRANSACTION_DATE": tx_date_iso,
                "POST_DATE": post_date_iso,
                "DESCRIPTION": description,
                "CATEGORY": category,
                "TYPE": tx_type,
                "AMOUNT": amount,
                "MEMO": memo,
                "ACCOUNT_ID": account_id,
            }
        )

    return prepared


def insert_rows(conn, rows: List[Dict[str, Any]], dry_run: bool = False):
    """
    Insert rows into CC_TRANSACTIONS using MERGE on TRANSACTION_ID.
    Re-ingesting the same file for the same account will not create dups.
    """
    if not rows:
        print("No credit card rows to insert.")
        return

    if dry_run:
        print(f"[DRY RUN] Would insert/merge up to {len(rows)} credit card rows.")
        return

    cursor = conn.cursor()
    try:
        chunk_size = 200
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]

            values_clause_parts: List[str] = []
            params: Dict[str, Any] = {}

            for idx, r in enumerate(chunk):
                suffix = f"_{idx}"
                values_clause_parts.append(
                    "("
                    + ", ".join(
                        [
                            f"%({col}{suffix})s"
                            for col in [
                                "TRANSACTION_ID",
                                "TRANSACTION_DATE",
                                "POST_DATE",
                                "DESCRIPTION",
                                "CATEGORY",
                                "TYPE",
                                "AMOUNT",
                                "MEMO",
                                "ACCOUNT_ID",
                            ]
                        ]
                    )
                    + ")"
                )

                for col in [
                    "TRANSACTION_ID",
                    "TRANSACTION_DATE",
                    "POST_DATE",
                    "DESCRIPTION",
                    "CATEGORY",
                    "TYPE",
                    "AMOUNT",
                    "MEMO",
                    "ACCOUNT_ID",
                ]:
                    params[f"{col}{suffix}"] = r[col]

            values_clause = ",\n".join(values_clause_parts)

            merge_sql = f"""
                MERGE INTO CC_TRANSACTIONS AS tgt
                USING (
                  SELECT
                    column1 AS TRANSACTION_ID,
                    column2 AS TRANSACTION_DATE,
                    column3 AS POST_DATE,
                    column4 AS DESCRIPTION,
                    column5 AS CATEGORY,
                    column6 AS TYPE,
                    column7 AS AMOUNT,
                    column8 AS MEMO,
                    column9 AS ACCOUNT_ID
                  FROM VALUES
                  {values_clause}
                ) AS src
                ON tgt.TRANSACTION_ID = src.TRANSACTION_ID
                WHEN NOT MATCHED THEN
                  INSERT (
                    TRANSACTION_ID,
                    TRANSACTION_DATE,
                    POST_DATE,
                    DESCRIPTION,
                    CATEGORY,
                    TYPE,
                    AMOUNT,
                    MEMO,
                    ACCOUNT_ID
                  )
                  VALUES (
                    src.TRANSACTION_ID,
                    src.TRANSACTION_DATE,
                    src.POST_DATE,
                    src.DESCRIPTION,
                    src.CATEGORY,
                    src.TYPE,
                    src.AMOUNT,
                    src.MEMO,
                    src.ACCOUNT_ID
                  )
            """

            cursor.execute(merge_sql, params)

        conn.commit()
        print(f"Inserted/merged up to {len(rows)} credit card rows.")
    finally:
        cursor.close()

def ingest_csv_file(csv_path: str, account_id: str, dry_run: bool = False) -> dict:
    """
    Convenience helper so the Flask app can call this directly.

    Returns a small summary dict that the UI can display.
    """
    raw_rows = read_csv_rows(csv_path)
    prepared_rows = prepare_rows_for_insert(raw_rows, account_id=account_id)

    conn = get_snowflake_connection()
    try:
        insert_rows(conn, prepared_rows, dry_run=dry_run)
    finally:
        conn.close()

    return {
        "rows_in_file": len(raw_rows),
        "rows_prepared": len(prepared_rows),
        # we can't easily distinguish skips vs inserts without changing insert_rows,
        # so treat everything as "attempted".
        "rows_attempted_insert": 0 if dry_run else len(prepared_rows),
        "account_id": account_id,
        "dry_run": dry_run,
    }



def main():
    parser = argparse.ArgumentParser(description="Ingest bank CSV into Snowflake BANK_TRANSACTIONS.")
    parser.add_argument("csv_path", help="Path to the CSV file to ingest.")
    parser.add_argument(
        "--account-id",
        required=True,
        help="Logical account id (e.g. 'chk_main', 'cc_chase') to tag each row.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and prepare rows but do not insert into Snowflake.",
    )
    args = parser.parse_args()

    csv_path = args.csv_path
    account_id = args.account_id

    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    print(f"Reading CSV from {csv_path} ...")
    raw_rows = read_csv_rows(csv_path)
    print(f"Read {len(raw_rows)} rows from CSV.")

    prepared_rows = prepare_rows_for_insert(raw_rows, account_id=account_id)
    print(f"Prepared {len(prepared_rows)} rows for insert.")

    conn = get_snowflake_connection()
    try:
        insert_rows(conn, prepared_rows, dry_run=args.dry_run)
    finally:
        conn.close()


if __name__ == "__main__":
    main()