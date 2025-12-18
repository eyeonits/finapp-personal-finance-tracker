import pandas as pd
from datetime import datetime, timedelta
import random

def query_transactions_from_dynamo(
    start_date: str,
    end_date: str,
    desc_filter: str | None = None,
    category_filter: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    limit: int = 500,
) -> pd.DataFrame:
    """
    Stub function that returns mock DynamoDB transaction data.
    Replace with real DynamoDB query once backend is ready.
    """
    
    # Sample transactions
    merchants = [
        "STARBUCKS COFFEE", "WALMART SUPERCENTER", "NETFLIX.COM",
        "AMAZON.COM", "SHELL GAS STATION", "WHOLE FOODS MARKET",
        "CVS PHARMACY", "TARGET STORE", "CHIPOTLE MEXICAN GRILL",
        "UBER EATS", "DOORDASH INC", "SPOTIFY AB"
    ]
    
    categories = [
        "Food & Dining", "Shopping", "Entertainment", "Gas & Fuel",
        "Groceries", "Health & Fitness", "Transportation", "Utilities"
    ]
    
    # Generate mock data
    rows = []
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    current = start
    
    while current <= end and len(rows) < limit:
        num_tx_today = random.randint(1, 4)
        for _ in range(num_tx_today):
            amount = round(random.uniform(-150, 50), 2)
            merchant = random.choice(merchants)
            category = random.choice(categories)
            
            # Apply filters
            if desc_filter and desc_filter.lower() not in merchant.lower():
                continue
            if category_filter and category_filter.lower() not in category.lower():
                continue
            if amount_min is not None and amount < amount_min:
                continue
            if amount_max is not None and amount > amount_max:
                continue
            
            rows.append({
                "TRANSACTION_DATE": current.date(),
                "POST_DATE": current.date(),
                "DESCRIPTION": merchant,
                "CATEGORY": category,
                "TYPE": "debit" if amount < 0 else "credit",
                "AMOUNT": amount,
                "MEMO": f"Mock transaction {len(rows)}"
            })
        
        current += timedelta(days=1)
    
    df = pd.DataFrame(rows[:limit])
    return df