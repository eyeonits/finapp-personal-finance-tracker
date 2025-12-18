# FinApp - Personal Finance Tracker

## Overview

FinApp is a personal finance tracking application that helps users visualize and analyze their financial transactions from credit cards and bank accounts. The application provides a web-based dashboard with filtering capabilities, charts, and transaction correlation features.

## Architecture

### Technology Stack

- **Backend**: Python 3.x with Flask web framework
- **Database**: Snowflake data warehouse
- **Frontend**: Bootstrap 5.3 with Chart.js for visualizations
- **Data Processing**: Pandas for data manipulation
- **Database Migrations**: Flyway for schema management

### Application Structure

```
finapp/
├── application/           # Main Flask application
│   ├── app.py            # Flask routes and application entry point
│   ├── db.py             # Snowflake connection utilities
│   ├── queries.py        # Database query functions
│   ├── metrics.py        # Dashboard metrics computation
│   ├── ingest_cc_transactions.py    # Credit card CSV import
│   ├── ingest_bank_transactions.py  # Bank account CSV import
│   └── templates/        # HTML templates
│       ├── index.html    # Main dashboard
│       └── import.html   # Transaction import interface
├── databases/            # Database schema definitions
│   └── finapp/
│       ├── schemas/      # Schema definitions
│       ├── tables/       # Table DDL scripts
│       └── permissions/  # Permission grants
└── docs/                 # Documentation
```

## Core Features

### 1. Transaction Management

**Credit Card Transactions**
- Supports multiple CSV formats:
  - Standard format (transaction date, post date, description, category, type, amount, memo)
  - Apple Card format (with merchant and purchased by fields)
  - Amex/Simple format (date, description, amount, category)
- Automatic sign normalization (charges negative, payments positive)
- Deterministic transaction IDs to prevent duplicates
- Account-specific handling (e.g., Apple Card sign flipping)

**Bank Transactions**
- CSV import with fields: posted date, effective date, description, transaction type, amount, balance, check number, memo
- Running balance tracking
- Check number support
- Account identification

### 2. Dashboard Features

**Summary Metrics**
- Total number of transactions
- Total spent (negative amounts)
- Total received (positive amounts)
- Net cash flow
- Average daily spend

**Visualizations**
- Daily spend line chart
- Cash flow doughnut chart (spent vs received)
- Credit card spending by category (top 10 categories)
- Bank income vs expenses comparison

**Filtering Capabilities**
- Date range selection (start/end dates)
- Description text search
- Category filtering
- Amount range filtering (min/max)
- Dataset selection (credit card, bank, or correlated view)

### 3. Correlated Payments View

A unique feature that matches credit card payments with corresponding bank account debits:
- Matches transactions with identical amounts
- Allows configurable date tolerance (default: 3 days)
- Helps identify payment flows between accounts
- Shows date differences between correlated transactions

### 4. Theme Support

- Light and dark mode toggle
- Persists user preference in localStorage
- Respects system color scheme preferences
- Smooth theme transitions

## Data Model

### CC_TRANSACTIONS Table

```sql
- TRANSACTION_ID (STRING, PRIMARY KEY) - Unique identifier
- TRANSACTION_DATE (DATE) - When transaction occurred
- POST_DATE (DATE) - When transaction posted
- DESCRIPTION (VARCHAR) - Merchant/transaction description
- CATEGORY (VARCHAR) - Transaction category
- TYPE (VARCHAR) - Transaction type (charge, payment, etc.)
- AMOUNT (NUMBER) - Transaction amount (negative = out, positive = in)
- MEMO (VARCHAR) - Additional notes
- ACCOUNT_ID (VARCHAR) - Account identifier
- LOAD_TS (TIMESTAMP) - When record was loaded
```

### BANK_TRANSACTIONS Table

```sql
- TRANSACTION_ID (STRING, PRIMARY KEY) - Unique identifier
- POSTED_DATE (DATE) - When transaction posted
- EFFECTIVE_DATE (DATE) - Effective transaction date
- DESCRIPTION (VARCHAR) - Transaction description
- TRANSACTION_TYPE (VARCHAR) - Type (debit, credit, fee, etc.)
- AMOUNT (NUMBER) - Transaction amount (negative = out, positive = in)
- RUNNING_BALANCE (NUMBER) - Account balance after transaction
- CHECK_NUMBER (VARCHAR) - Check number if applicable
- MEMO (VARCHAR) - Additional notes
- ACCOUNT_ID (VARCHAR) - Account identifier
- LOAD_TS (TIMESTAMP) - When record was loaded
```

## Key Components

### app.py - Flask Application

**Routes:**
- `GET/POST /` - Main dashboard with filtering and visualization
- `GET/POST /import` - Transaction import interface

**Responsibilities:**
- Request handling and parameter parsing
- Dataset selection (credit card, bank, correlated)
- Filter application
- Template rendering with computed metrics

### queries.py - Data Access Layer

**Functions:**
- `query_cc_transactions_snowflake()` - Fetch credit card transactions with filters
- `query_bank_transactions_snowflake()` - Fetch bank transactions with filters
- `normalize_transaction_signs()` - Handle account-specific sign conventions

**Features:**
- Parameterized queries to prevent SQL injection
- Pre-loaded summary data for charts
- Column normalization for consistent data structure

### metrics.py - Analytics Engine

**Functions:**
- `compute_dashboard_metrics()` - Calculate summary statistics and chart data
- `build_correlated_payments()` - Match credit card payments with bank debits

**Capabilities:**
- Daily spending aggregation
- Category-based spending analysis
- Income vs expense categorization
- Cross-dataset correlation with date tolerance

### ingest_cc_transactions.py - Credit Card Import

**Features:**
- Multi-format CSV parsing (standard, Apple Card, Amex)
- Date format detection and normalization
- Amount sign normalization per account type
- Deterministic UUID generation for deduplication
- MERGE-based upsert to prevent duplicates
- Batch processing (200 rows per chunk)

### ingest_bank_transactions.py - Bank Import

**Features:**
- Bank CSV format parsing
- Amount cleaning (handles $, commas)
- Running balance tracking
- Check number support
- MERGE-based upsert
- Batch processing

## Configuration

### Environment Variables

Required Snowflake connection parameters:
```
SF_USER - Snowflake username
SF_PASSWORD - Snowflake password
SF_ACCOUNT - Snowflake account identifier
SF_WAREHOUSE - Snowflake warehouse name
SF_DATABASE - Database name
SF_SCHEMA - Schema name (typically "FIN")
SF_ROLE - Snowflake role (optional)
```

Configuration files:
- `application/dev.env` - Application-level environment variables
- `dev.env` - Root-level environment variables

## Deployment

### Docker Compose

The application includes Flyway for database migrations:

```yaml
services:
  flyway:
    - Manages database schema migrations
    - Connects to Snowflake using environment variables
    - Runs SQL scripts from databases/ directory
```

### Running the Application

1. Set up environment variables in `application/dev.env`
2. Install Python dependencies: `pip install -r application/requirements.txt`
3. Run Flask app: `python application/app.py`
4. Access dashboard at `http://localhost:5000`

## Import Workflows

### Credit Card Import

1. Export CSV from credit card provider
2. Navigate to Import page
3. Select Credit Card tab
4. Choose CSV file
5. Enter account ID (e.g., "cc_apple", "cc_chase")
6. Submit for processing

### Bank Import

1. Export CSV from bank
2. Navigate to Import page
3. Select Bank tab
4. Choose CSV file
5. Enter account ID (e.g., "bank_main", "chk_main")
6. Submit for processing

### CLI Import (Alternative)

Both import scripts support command-line usage:

```bash
# Credit card import
python application/ingest_cc_transactions.py path/to/file.csv --account-id cc_apple

# Bank import
python application/ingest_bank_transactions.py path/to/file.csv --account-id bank_main

# Dry run (parse only, don't insert)
python application/ingest_cc_transactions.py file.csv --account-id cc_apple --dry-run
```

## Data Flow

1. **Import**: CSV files → Python parsers → Snowflake tables
2. **Query**: User filters → SQL queries → Pandas DataFrames
3. **Processing**: DataFrames → Metrics computation → Chart data
4. **Display**: Chart data → Flask templates → Browser visualization

## Security Considerations

- Parameterized SQL queries prevent injection attacks
- Environment variables for sensitive credentials
- No hardcoded passwords or API keys
- MERGE operations prevent duplicate data insertion

## Known Limitations

- Single-user application (no authentication)
- Manual CSV imports (no automatic bank connections)
- Limited to Snowflake as data warehouse
- No transaction editing or deletion through UI
- Category assignment depends on bank/card provider
- No budgeting or forecasting features
- No mobile-responsive design optimization
