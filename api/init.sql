-- Initial database schema for FinApp

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(36) PRIMARY KEY,
    cognito_sub VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_users_cognito_sub ON users(cognito_sub);
CREATE INDEX idx_users_email ON users(email);

-- Create transactions table
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(user_id),
    transaction_date DATE NOT NULL,
    post_date DATE NOT NULL,
    description VARCHAR(500) NOT NULL,
    category VARCHAR(100),
    type VARCHAR(50),
    amount NUMERIC(10, 2) NOT NULL,
    memo VARCHAR(500),
    account_id VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_account_id ON transactions(account_id);

-- Create import_history table
CREATE TABLE IF NOT EXISTS import_history (
    import_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(user_id),
    import_type VARCHAR(50) NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    filename VARCHAR(255),
    rows_total INTEGER NOT NULL,
    rows_inserted INTEGER NOT NULL,
    rows_skipped INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_import_history_user_id ON import_history(user_id);
CREATE INDEX idx_import_history_created_at ON import_history(created_at);

-- Create a system user for existing data migration
INSERT INTO users (user_id, cognito_sub, email, is_active)
VALUES (
    'system-user-id',
    'system',
    'system@finapp.local',
    true
)
ON CONFLICT (cognito_sub) DO NOTHING;
