import os
from datetime import date, timedelta
import json
import tempfile

from flask import Flask, render_template, request

from queries import (
    query_cc_transactions_snowflake,
    query_bank_transactions_snowflake,
    cc_category_labels,
    cc_category_values,
    bank_income_expense_labels,
    bank_income_expense_values,
)
from metrics import compute_dashboard_metrics, build_correlated_payments
from ingest_cc_transactions import ingest_csv_file
from ingest_bank_transactions import ingest_bank_csv_file


# ---------------------------------------------------
# Flask app & routes
# ---------------------------------------------------

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    today = date.today()
    default_start = today - timedelta(days=90)

    if request.method == "POST":
        dataset = request.form.get("dataset") or "cc"
        start_str = request.form.get("start_date") or default_start.isoformat()
        end_str = request.form.get("end_date") or today.isoformat()
        desc_filter = request.form.get("description") or None
        category_filter = request.form.get("category") or None
        amount_min_str = request.form.get("amount_min") or None
        amount_max_str = request.form.get("amount_max") or None
    else:
        dataset = request.args.get("dataset") or "cc"
        start_str = default_start.isoformat()
        end_str = today.isoformat()
        desc_filter = None
        category_filter = None
        amount_min_str = None
        amount_max_str = None

    amount_min = float(amount_min_str) if amount_min_str else None
    amount_max = float(amount_max_str) if amount_max_str else None

    # Choose dataset
    if dataset == "bank":
        df = query_bank_transactions_snowflake(
            start_str,
            end_str,
            desc_filter=desc_filter,
            _category_filter=category_filter,
            amount_min=amount_min,
            amount_max=amount_max,
            limit=2000,
        )
        source_label = "Snowflake · Bank"
    elif dataset == "correlated":
        # For charts & cards, we'll still show CC-only for now
        df = query_cc_transactions_snowflake(
            start_str,
            end_str,
            desc_filter=desc_filter,
            category_filter=category_filter,
            amount_min=amount_min,
            amount_max=amount_max,
            limit=2000,
        )
        source_label = "Snowflake · Credit Card"
    else:
        # Default: CC
        df = query_cc_transactions_snowflake(
            start_str,
            end_str,
            desc_filter=desc_filter,
            category_filter=category_filter,
            amount_min=amount_min,
            amount_max=amount_max,
            limit=2000,
        )
        source_label = "Snowflake · Credit Card"

    metrics = compute_dashboard_metrics(df, start_str, end_str)

    rows = df.to_dict(orient="records")

    correlations = []
    if dataset == "correlated":
        correlations = build_correlated_payments(start_str, end_str)

    return render_template(
        "index.html",
        # filters
        start_date=start_str,
        end_date=end_str,
        desc_filter=desc_filter or "",
        category_filter=category_filter or "",
        amount_min=amount_min_str or "",
        amount_max=amount_max_str or "",
        # dataset/source
        dataset=dataset,
        source_label=source_label,
        # summary
        num_tx=metrics["num_tx"],
        total_spent=metrics["total_spent"],
        total_received=metrics["total_received"],
        net=metrics["net"],
        avg_daily_spend=metrics["avg_daily_spend"],
        # charts
        daily_labels=metrics["daily_labels"],
        daily_spend=metrics["daily_spend"],
        #cat_labels=metrics["cat_labels"],
        #cat_values=metrics["cat_values"],
        spend_cat_labels=metrics["spend_cat_labels"],
        spend_cat_values=metrics["spend_cat_values"],
        income_cat_labels=metrics["income_cat_labels"],
        income_cat_values=metrics["income_cat_values"],
        cc_category_labels=json.dumps(cc_category_labels),
        cc_category_values=json.dumps(cc_category_values),
        bank_income_expense_labels=json.dumps(bank_income_expense_labels),
        bank_income_expense_values=json.dumps(bank_income_expense_values),
        # rows + correlations
        rows=rows,
        correlations=correlations,
    )


@app.route("/import", methods=["GET", "POST"])
def import_dashboard():
    cc_summary = None
    bank_summary = None
    cc_error = None
    bank_error = None

    # default tab is credit
    active_tab = request.args.get("tab", "cc")

    if request.method == "POST":
        import_type = request.form.get("import_type", "cc")
        active_tab = import_type  # keep the tab you submitted from active

        file = request.files.get("file")
        account_id = (request.form.get("account_id") or "").strip()

        if not file or file.filename == "":
            if import_type == "cc":
                cc_error = "Please choose a CSV file."
            else:
                bank_error = "Please choose a CSV file."
        elif not account_id:
            if import_type == "cc":
                cc_error = "Please enter an account id (e.g. cc_apple)."
            else:
                bank_error = "Please enter an account id (e.g. bank_main)."
        else:
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    temp_path = tmp.name
                    file.save(temp_path)

                if import_type == "cc":
                    cc_summary = ingest_csv_file(temp_path, account_id)
                else:
                    bank_summary = ingest_bank_csv_file(temp_path, account_id)

            except Exception as exc:
                if import_type == "cc":
                    cc_error = f"Import failed: {exc}"
                else:
                    bank_error = f"Import failed: {exc}"
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

    return render_template(
        "import.html",
        active_tab=active_tab,
        cc_summary=cc_summary,
        bank_summary=bank_summary,
        cc_error=cc_error,
        bank_error=bank_error,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
