import argparse
import csv
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

# ---------------------------------------------------
# Load dev.env from the directory of this script
# ---------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / "dev.env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
    print(f"Loaded env from {ENV_PATH}")
else:
    load_dotenv()
    print("WARNING: dev.env not found in script directory; using default environment.")


# ---------------------------------------------------
# Snowflake helpers
# ---------------------------------------------------

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
    missing = [k for k, v in conn_params.items() if not v]
    if missing:
        raise RuntimeError(f"Missing Snowflake env vars: {', '.join(missing)}")

    role = os.getenv("SF_ROLE")
    if role:
        conn_params["role"] = role

    return snowflake.connector.connect(**conn_params)


def parse_date(value: str) -> str | None:
    """Parse a date string and return it as ISO (YYYY-MM-DD) or None."""
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    # Adjust formats here if your bank uses something else.
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            d = datetime.strptime(value, fmt).date()
            return d.isoformat()
        except ValueError:
            continue

    raise ValueError(f"Unrecognized date format: {value!r}")


def clean_amount(value: str) -> float:
    """Convert a bank amount string like '-$1,234.56' into a proper float."""
    if value is None:
        return 0.0

    cleaned = str(value).strip().replace("$", "").replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        raise ValueError(f"Invalid amount format: {value!r}")


def generate_transaction_id(row: Dict[str, Any], account_id: str) -> str:
    """Generate a deterministic UUID based on key fields."""
    key_parts = [
        row.get("posted_date", "") or "",
        row.get("effective_date", "") or "",
        (row.get("description", "") or "").upper(),
        str(row.get("amount", "") or "").strip(),
        account_id.strip(),
    ]
    key = "|".join(key_parts)
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))


# ---------------------------------------------------
# CSV handling for BANK file
# ---------------------------------------------------

def read_csv_rows(csv_path: str) -> List[Dict[str, Any]]:
    """
    Read the BANK CSV file and return a list of normalized rows.

    Bank CSV Columns (case-insensitive):
      - Posted Date
      - Effective Date
      - Transaction
      - Amount
      - Balance
      - Description
      - Check#
      - Memo
    """
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise RuntimeError("Bank CSV has no header row.")

        field_map = {name.lower().strip(): name for name in reader.fieldnames}

        required_bank_fields = [
            "posted date",
            "effective date",
            "transaction",
            "amount",
            "balance",
            "description",
            "check#",
            "memo",
        ]

        for col in required_bank_fields:
            if col not in field_map:
                raise RuntimeError(
                    f"Bank CSV is missing required column: {col} "
                    f"(present columns: {reader.fieldnames})"
                )

        rows: List[Dict[str, Any]] = []
        for raw in reader:
            rows.append({
                "posted_date": raw[field_map["posted date"]],
                "effective_date": raw[field_map["effective date"]],
                "description": raw[field_map["description"]],
                "transaction_type": raw[field_map["transaction"]],
                "amount": raw[field_map["amount"]],
                "running_balance": raw[field_map["balance"]],
                "check_number": raw[field_map["check#"]],
                "memo": raw[field_map["memo"]],
            })

    return rows


def prepare_rows_for_insert(csv_rows: List[Dict[str, Any]], account_id: str) -> List[Dict[str, Any]]:
    """Convert raw BANK CSV rows into a structure ready for Snowflake insert."""
    prepared: List[Dict[str, Any]] = []

    for r in csv_rows:
        posted_date_iso = parse_date(r["posted_date"])
        effective_date_iso = parse_date(r["effective_date"])
        description = (r["description"] or "").strip()
        transaction_type = (r["transaction_type"] or "").strip() or None
        amount = clean_amount(r["amount"])
        running_balance = clean_amount(r["running_balance"])
        check_number = (r["check_number"] or "").strip() or None
        memo = (r["memo"] or "").strip() or None

        tx_id = generate_transaction_id(
            {
                "posted_date": posted_date_iso or "",
                "effective_date": effective_date_iso or "",
                "description": description,
                "amount": amount,
            },
            account_id=account_id,
        )

        prepared.append({
            "TRANSACTION_ID": tx_id,
            "POSTED_DATE": posted_date_iso,
            "EFFECTIVE_DATE": effective_date_iso,
            "DESCRIPTION": description,
            "TRANSACTION_TYPE": transaction_type,
            "AMOUNT": amount,
            "RUNNING_BALANCE": running_balance,
            "CHECK_NUMBER": check_number,
            "MEMO": memo,
            "ACCOUNT_ID": account_id,
        })

    return prepared


# ---------------------------------------------------
# Snowflake insert / merge logic
# ---------------------------------------------------

def insert_rows(conn, rows: List[Dict[str, Any]], dry_run: bool = False):
    """Insert rows into BANK_TRANSACTIONS using MERGE on TRANSACTION_ID."""
    if not rows:
        print("No bank rows to insert.")
        return

    if dry_run:
        print(f"[DRY RUN] Would insert/merge up to {len(rows)} bank rows.")
        return

    cursor = conn.cursor()
    try:
        chunk_size = 200
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]

            values_clause_parts = []
            params: Dict[str, Any] = {}

            for idx, r in enumerate(chunk):
                suffix = f"_{i}_{idx}"
                values_clause_parts.append(
                    f"(%(TRANSACTION_ID{suffix})s, %(POSTED_DATE{suffix})s, "
                    f"%(EFFECTIVE_DATE{suffix})s, %(DESCRIPTION{suffix})s, "
                    f"%(TRANSACTION_TYPE{suffix})s, %(AMOUNT{suffix})s, "
                    f"%(RUNNING_BALANCE{suffix})s, %(CHECK_NUMBER{suffix})s, "
                    f"%(MEMO{suffix})s, %(ACCOUNT_ID{suffix})s)"
                )

                for col in [
                    "TRANSACTION_ID",
                    "POSTED_DATE",
                    "EFFECTIVE_DATE",
                    "DESCRIPTION",
                    "TRANSACTION_TYPE",
                    "AMOUNT",
                    "RUNNING_BALANCE",
                    "CHECK_NUMBER",
                    "MEMO",
                    "ACCOUNT_ID",
                ]:
                    params[f"{col}{suffix}"] = r[col]

            values_clause = ",\n".join(values_clause_parts)

            merge_sql = f"""
                MERGE INTO BANK_TRANSACTIONS AS tgt
                USING (
                  SELECT
                    column1 AS TRANSACTION_ID,
                    column2 AS POSTED_DATE,
                    column3 AS EFFECTIVE_DATE,
                    column4 AS DESCRIPTION,
                    column5 AS TRANSACTION_TYPE,
                    column6 AS AMOUNT,
                    column7 AS RUNNING_BALANCE,
                    column8 AS CHECK_NUMBER,
                    column9 AS MEMO,
                    column10 AS ACCOUNT_ID
                  FROM VALUES
                  {values_clause}
                ) AS src
                ON tgt.TRANSACTION_ID = src.TRANSACTION_ID
                WHEN NOT MATCHED THEN
                  INSERT (
                    TRANSACTION_ID,
                    POSTED_DATE,
                    EFFECTIVE_DATE,
                    DESCRIPTION,
                    TRANSACTION_TYPE,
                    AMOUNT,
                    RUNNING_BALANCE,
                    CHECK_NUMBER,
                    MEMO,
                    ACCOUNT_ID
                  )
                  VALUES (
                    src.TRANSACTION_ID,
                    src.POSTED_DATE,
                    src.EFFECTIVE_DATE,
                    src.DESCRIPTION,
                    src.TRANSACTION_TYPE,
                    src.AMOUNT,
                    src.RUNNING_BALANCE,
                    src.CHECK_NUMBER,
                    src.MEMO,
                    src.ACCOUNT_ID
                  )
            """

            cursor.execute(merge_sql, params)

        conn.commit()
        print(f"Inserted/merged up to {len(rows)} bank rows.")
    finally:
        cursor.close()


# ---------------------------------------------------
# CLI
# ---------------------------------------------------

def ingest_bank_csv_file(csv_path: str, account_id: str, dry_run: bool = False) -> dict:
    """
    Run the full ingest for a bank CSV file and return a summary dict
    that the UI can display.
    """
    raw_rows = read_csv_rows(csv_path)
    prepared_rows = prepare_rows_for_insert(raw_rows, account_id=account_id)

    conn = get_snowflake_connection()
    try:
        # Call your existing insert/upsert function – it probably returns None
        #upsert_rows_to_snowflake(conn, prepared_rows, dry_run=dry_run)
        insert_rows(conn, prepared_rows, dry_run=dry_run)
    finally:
        conn.close()

    # Since the insert function doesn’t tell us counts, just infer them
    rows_prepared = len(prepared_rows)
    return {
        "rows_in_file": len(raw_rows),
        "rows_prepared": rows_prepared,
        "rows_inserted": 0 if dry_run else rows_prepared,
        "rows_updated": 0,          # adjust if you later track updates separately
        "account_id": account_id,
        "dry_run": dry_run,
    }

def main():
    parser = argparse.ArgumentParser(description="Ingest BANK CSV into Snowflake BANK_TRANSACTIONS.")
    parser.add_argument("csv_path", help="Path to the BANK CSV file.")
    parser.add_argument(
        "--account-id",
        required=True,
        help="Logical account id for these bank transactions (e.g. 'chk_main').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and prepare bank rows but do not insert into Snowflake.",
    )

    args = parser.parse_args()
    csv_path = args.csv_path
    account_id = args.account_id

    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Bank CSV file not found: {csv_path}")

    print(f"Reading BANK CSV from {csv_path} ...")
    raw_rows = read_csv_rows(csv_path)
    print(f"Read {len(raw_rows)} bank rows from CSV.")

    prepared_rows = prepare_rows_for_insert(raw_rows, account_id=account_id)
    print(f"Prepared {len(prepared_rows)} bank rows for insert.")

    conn = get_snowflake_connection()
    try:
        insert_rows(conn, prepared_rows, dry_run=args.dry_run)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
