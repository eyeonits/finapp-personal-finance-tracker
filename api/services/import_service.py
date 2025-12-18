"""
Import service for CSV processing.
"""
import csv
import uuid
import io
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from decimal import Decimal

from api.repositories.transaction_repository import TransactionRepository
from api.repositories.import_repository import ImportRepository
from api.models.domain import Transaction


class ImportService:
    """Service for handling CSV imports."""
    
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        import_repository: ImportRepository
    ):
        """Initialize import service."""
        self.transaction_repository = transaction_repository
        self.import_repository = import_repository
    
    def _generate_transaction_id(
        self,
        transaction_date: str,
        post_date: str,
        description: str,
        amount: str,
        account_id: str
    ) -> str:
        """
        Generate a deterministic UUID based on key fields.
        This helps avoid duplicate inserts if we re-ingest the same CSV.
        """
        key_parts = [
            transaction_date or "",
            post_date or "",
            (description or "").upper(),
            str(amount or "").strip(),
            account_id.strip(),
        ]
        key = "|".join(key_parts)
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, key))
    
    def _parse_date(self, value: str) -> Optional[date]:
        """Parse a date string and return it as a date object or None."""
        if not value:
            return None
        
        value = value.strip()
        if not value:
            return None
        
        # Common date formats
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        
        raise ValueError(f"Unrecognized date format: {value!r}")
    
    def _clean_amount(self, value: str) -> Decimal:
        """Convert an amount string like '-$1,234.56' into a Decimal."""
        if value is None:
            return Decimal('0.00')
        
        cleaned = str(value).strip().replace("$", "").replace(",", "")
        
        try:
            return Decimal(cleaned)
        except ValueError:
            raise ValueError(f"Invalid amount format: {value!r}")
    
    def _read_credit_card_csv(self, file_content: bytes) -> List[Dict[str, Any]]:
        """
        Read credit card CSV file and return a list of normalized rows.
        
        Supports:
          1) Original "standard" CC CSV format:
             transaction date, post date, description, category, type, amount, memo

          2) Apple Card CSV format:
             Transaction Date, Clearing Date, Description, Merchant,
             Category, Type, Amount (USD), Purchased By

          3) Simple Date/Amount CC format (e.g. Amex):
             Date, Description, Amount, Category, (plus other unused cols)
          
          4) Debit/Credit format (e.g. Capital One):
             Transaction Date, Posted Date, Card No., Description, Category, Debit, Credit
        """
        # Decode file content
        try:
            text = file_content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = file_content.decode('latin-1')
        
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV has no header row.")
        
        # Map lower-cased header -> original header name
        field_map = {name.lower().strip(): name for name in reader.fieldnames}
        
        # Format detection
        is_apple = (
            "transaction date" in field_map
            and "clearing date" in field_map
            and "amount (usd)" in field_map
        )
        
        is_simple_date_amount = (
            "date" in field_map
            and "amount" in field_map
            and "transaction date" not in field_map
        )
        
        # Capital One / Debit-Credit format:
        # Transaction Date, Posted Date, Card No., Description, Category, Debit, Credit
        is_debit_credit = (
            "transaction date" in field_map
            and "posted date" in field_map
            and "debit" in field_map
            and "credit" in field_map
            and "description" in field_map
        )
        
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
        
        # Apple Card format
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
                    raise ValueError(f"CSV (Apple format) is missing required column: {col}")
            
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
        
        # Amex / Simple Date+Amount format
        elif is_simple_date_amount:
            for col in ["date", "description", "amount"]:
                if col not in field_map:
                    raise ValueError(f"CSV (Date/Amount format) is missing required column: {col}")
            
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
                    "memo": "",
                }
                rows.append(row)
        
        # Capital One / Debit-Credit format
        elif is_debit_credit:
            for col in ["transaction date", "posted date", "description", "debit", "credit"]:
                if col not in field_map:
                    raise ValueError(f"CSV (Debit/Credit format) is missing required column: {col}")
            
            for raw_row in reader:
                # Get debit and credit values
                debit_raw = raw_row[field_map["debit"]].replace(",", "").replace("$", "").strip()
                credit_raw = raw_row[field_map["credit"]].replace(",", "").replace("$", "").strip()
                
                # Calculate amount: Debit is spending (negative), Credit is payment/refund (positive)
                amount = 0.0
                txn_type = ""
                
                if debit_raw and debit_raw != "":
                    try:
                        amount = -abs(float(debit_raw))  # Debit = spending = negative
                        txn_type = "DEBIT"
                    except ValueError:
                        pass
                elif credit_raw and credit_raw != "":
                    try:
                        amount = abs(float(credit_raw))  # Credit = payment/refund = positive
                        txn_type = "CREDIT"
                    except ValueError:
                        pass
                
                # Get card number for memo if available
                card_no = ""
                if "card no." in field_map and raw_row.get(field_map["card no."]):
                    card_no = raw_row[field_map["card no."]].strip()
                
                memo = f"Card: {card_no}" if card_no else ""
                
                row = {
                    "transaction date": raw_row[field_map["transaction date"]],
                    "post date": raw_row[field_map["posted date"]],
                    "description": raw_row[field_map["description"]],
                    "category": raw_row[field_map["category"]] if "category" in field_map else "",
                    "type": txn_type,
                    "amount": str(amount),
                    "memo": memo,
                }
                rows.append(row)
        
        # Original standard format
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
            raise ValueError(f"Unrecognized CSV layout. Headers: {reader.fieldnames}")
        
        return rows
    
    def _read_bank_csv(self, file_content: bytes) -> List[Dict[str, Any]]:
        """
        Read bank CSV file and return a list of normalized rows.
        
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
        # Decode file content
        try:
            text = file_content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = file_content.decode('latin-1')
        
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("Bank CSV has no header row.")
        
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
                raise ValueError(
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
    
    async def import_credit_card_csv(
        self,
        user_id: str,
        file_content: bytes,
        account_id: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import credit card CSV file.
        
        Args:
            user_id: User ID performing the import
            file_content: CSV file content as bytes
            account_id: Account identifier (e.g., 'cc_apple', 'cc_chase')
            filename: Original filename (optional)
            
        Returns:
            Dictionary with import results
        """
        import_id = str(uuid.uuid4())
        rows_total = 0
        rows_inserted = 0
        rows_skipped = 0
        status = "success"
        error_message = None
        
        try:
            # Read and parse CSV
            csv_rows = self._read_credit_card_csv(file_content)
            rows_total = len(csv_rows)
            
            # First pass: parse all rows and generate transaction IDs
            parsed_transactions: List[Dict[str, Any]] = []
            transaction_ids_to_check: List[str] = []
            existing_ids_in_batch = set()
            
            for row in csv_rows:
                try:
                    tx_date = self._parse_date(row["transaction date"])
                    post_date = self._parse_date(row["post date"])
                    description = (row["description"] or "").strip()
                    category = (row["category"] or "").strip() or None
                    tx_type = (row["type"] or "").strip() or None
                    amount = self._clean_amount(row["amount"])
                    memo = (row["memo"] or "").strip() or None
                    
                    if not tx_date or not post_date:
                        rows_skipped += 1
                        continue
                    
                    # Generate transaction ID
                    tx_id = self._generate_transaction_id(
                        tx_date.isoformat(),
                        post_date.isoformat(),
                        description,
                        str(amount),
                        account_id
                    )
                    
                    # Check for duplicates in this batch
                    if tx_id in existing_ids_in_batch:
                        rows_skipped += 1
                        continue
                    
                    existing_ids_in_batch.add(tx_id)
                    transaction_ids_to_check.append(tx_id)
                    
                    parsed_transactions.append({
                        'transaction_id': tx_id,
                        'transaction_date': tx_date,
                        'post_date': post_date,
                        'description': description,
                        'category': category,
                        'type': tx_type,
                        'amount': amount,
                        'memo': memo,
                    })
                    
                except Exception as e:
                    # Skip invalid rows
                    rows_skipped += 1
                    continue
            
            # Bulk check for existing transactions in database
            existing_db_ids = set()
            if transaction_ids_to_check:
                existing_db_ids = await self.transaction_repository.get_existing_transaction_ids(
                    transaction_ids_to_check,
                    user_id
                )
            
            # Second pass: create Transaction objects only for new transactions
            transactions_to_create: List[Transaction] = []
            for parsed in parsed_transactions:
                tx_id = parsed['transaction_id']
                
                # Skip if already exists in database
                if tx_id in existing_db_ids:
                    rows_skipped += 1
                    continue
                
                # Create transaction object
                transaction = Transaction(
                    transaction_id=tx_id,
                    user_id=user_id,
                    transaction_date=parsed['transaction_date'],
                    post_date=parsed['post_date'],
                    description=parsed['description'],
                    category=parsed['category'],
                    type=parsed['type'],
                    amount=parsed['amount'],
                    memo=parsed['memo'],
                    account_id=account_id,
                    source="credit_card"
                )
                
                transactions_to_create.append(transaction)
            
            # Bulk insert transactions
            if transactions_to_create:
                await self.transaction_repository.create_transactions_bulk(transactions_to_create)
                rows_inserted = len(transactions_to_create)
            
            # Determine status
            if rows_inserted == 0 and rows_total > 0:
                status = "partial" if rows_skipped > 0 else "failed"
            elif rows_skipped > 0:
                status = "partial"
            
        except Exception as e:
            status = "failed"
            error_message = str(e)
            rows_inserted = 0
            rows_skipped = rows_total
        
        # Create import history record
        import_history = await self.import_repository.create_import_history(
            user_id=user_id,
            import_type="credit_card",
            account_id=account_id,
            filename=filename,
            rows_total=rows_total,
            rows_inserted=rows_inserted,
            rows_skipped=rows_skipped,
            status=status,
            error_message=error_message
        )
        
        return {
            "import_id": import_history.import_id,
            "rows_total": rows_total,
            "rows_inserted": rows_inserted,
            "rows_skipped": rows_skipped,
            "status": status
        }
    
    async def import_bank_csv(
        self,
        user_id: str,
        file_content: bytes,
        account_id: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import bank CSV file.
        
        Args:
            user_id: User ID performing the import
            file_content: CSV file content as bytes
            account_id: Account identifier (e.g., 'chk_main', 'sav_main')
            filename: Original filename (optional)
            
        Returns:
            Dictionary with import results
        """
        import_id = str(uuid.uuid4())
        rows_total = 0
        rows_inserted = 0
        rows_skipped = 0
        status = "success"
        error_message = None
        
        try:
            # Read and parse CSV
            csv_rows = self._read_bank_csv(file_content)
            rows_total = len(csv_rows)
            
            # First pass: parse all rows and generate transaction IDs
            parsed_transactions: List[Dict[str, Any]] = []
            transaction_ids_to_check: List[str] = []
            existing_ids_in_batch = set()
            
            for row in csv_rows:
                try:
                    posted_date = self._parse_date(row["posted_date"])
                    effective_date = self._parse_date(row["effective_date"])
                    description = (row["description"] or "").strip()
                    transaction_type = (row["transaction_type"] or "").strip() or None
                    amount = self._clean_amount(row["amount"])
                    check_number = (row["check_number"] or "").strip() or None
                    memo = (row["memo"] or "").strip() or None
                    
                    # Use posted_date as transaction_date, effective_date as post_date
                    # If effective_date is missing, use posted_date for both
                    tx_date = posted_date or effective_date
                    post_date = effective_date or posted_date
                    
                    if not tx_date or not post_date:
                        rows_skipped += 1
                        continue
                    
                    # Add check number to memo if present
                    if check_number and memo:
                        memo = f"{memo} (Check #{check_number})"
                    elif check_number:
                        memo = f"Check #{check_number}"
                    
                    # Generate transaction ID
                    tx_id = self._generate_transaction_id(
                        tx_date.isoformat(),
                        post_date.isoformat(),
                        description,
                        str(amount),
                        account_id
                    )
                    
                    # Check for duplicates in this batch
                    if tx_id in existing_ids_in_batch:
                        rows_skipped += 1
                        continue
                    
                    existing_ids_in_batch.add(tx_id)
                    transaction_ids_to_check.append(tx_id)
                    
                    parsed_transactions.append({
                        'transaction_id': tx_id,
                        'transaction_date': tx_date,
                        'post_date': post_date,
                        'description': description,
                        'transaction_type': transaction_type,
                        'amount': amount,
                        'memo': memo,
                    })
                    
                except Exception as e:
                    # Skip invalid rows
                    rows_skipped += 1
                    continue
            
            # Bulk check for existing transactions in database
            existing_db_ids = set()
            if transaction_ids_to_check:
                existing_db_ids = await self.transaction_repository.get_existing_transaction_ids(
                    transaction_ids_to_check,
                    user_id
                )
            
            # Second pass: create Transaction objects only for new transactions
            transactions_to_create: List[Transaction] = []
            for parsed in parsed_transactions:
                tx_id = parsed['transaction_id']
                
                # Skip if already exists in database
                if tx_id in existing_db_ids:
                    rows_skipped += 1
                    continue
                
                # Create transaction object
                transaction = Transaction(
                    transaction_id=tx_id,
                    user_id=user_id,
                    transaction_date=parsed['transaction_date'],
                    post_date=parsed['post_date'],
                    description=parsed['description'],
                    category=None,  # Bank transactions typically don't have categories
                    type=parsed['transaction_type'],
                    amount=parsed['amount'],
                    memo=parsed['memo'],
                    account_id=account_id,
                    source="bank"
                )
                
                transactions_to_create.append(transaction)
            
            # Bulk insert transactions
            if transactions_to_create:
                await self.transaction_repository.create_transactions_bulk(transactions_to_create)
                rows_inserted = len(transactions_to_create)
            
            # Determine status
            if rows_inserted == 0 and rows_total > 0:
                status = "partial" if rows_skipped > 0 else "failed"
            elif rows_skipped > 0:
                status = "partial"
            
        except Exception as e:
            status = "failed"
            error_message = str(e)
            rows_inserted = 0
            rows_skipped = rows_total
        
        # Create import history record
        import_history = await self.import_repository.create_import_history(
            user_id=user_id,
            import_type="bank",
            account_id=account_id,
            filename=filename,
            rows_total=rows_total,
            rows_inserted=rows_inserted,
            rows_skipped=rows_skipped,
            status=status,
            error_message=error_message
        )
        
        return {
            "import_id": import_history.import_id,
            "rows_total": rows_total,
            "rows_inserted": rows_inserted,
            "rows_skipped": rows_skipped,
            "status": status
        }
