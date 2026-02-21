-- Banking Data Assistant - Database Schema
-- SQLite compatible schema with proper foreign key constraints

-- Enable foreign key support (SQLite specific)
PRAGMA foreign_keys = ON;

-- ============================================================
-- CUSTOMERS TABLE
-- Stores customer information
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- ACCOUNTS TABLE
-- Stores customer bank accounts
-- ============================================================
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    account_number TEXT NOT NULL UNIQUE,
    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- ============================================================
-- TRANSACTIONS TABLE
-- Stores all account transactions
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('credit', 'debit')),
    amount DECIMAL(15, 2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_accounts_customer_id ON accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

-- ============================================================
-- SEED DATA FOR DEVELOPMENT
-- ============================================================

-- Insert sample customers
INSERT INTO customers (name, email) VALUES 
    ('John Doe', 'john.doe@email.com'),
    ('Jane Smith', 'jane.smith@email.com'),
    ('Robert Johnson', 'robert.johnson@email.com'),
    ('Emily Davis', 'emily.davis@email.com'),
    ('Michael Brown', 'michael.brown@email.com');

-- Insert sample accounts
INSERT INTO accounts (customer_id, account_number, balance) VALUES
    (1, 'ACC1001', 5000.00),
    (1, 'ACC1002', 12500.50),
    (2, 'ACC2001', 8750.25),
    (3, 'ACC3001', 15000.00),
    (4, 'ACC4001', 3200.75),
    (5, 'ACC5001', 25000.00),
    (5, 'ACC5002', 50000.00);

-- Insert sample transactions
INSERT INTO transactions (account_id, type, amount) VALUES
    -- Account 1 (ACC1001) transactions
    (1, 'credit', 1000.00),
    (1, 'debit', 250.00),
    (1, 'credit', 500.00),
    (1, 'debit', 100.00),
    
    -- Account 2 (ACC1002) transactions
    (2, 'credit', 5000.00),
    (2, 'credit', 7500.50),
    (2, 'debit', 1500.00),
    
    -- Account 3 (ACC2001) transactions
    (3, 'credit', 10000.00),
    (3, 'debit', 1249.75),
    
    -- Account 4 (ACC3001) transactions
    (4, 'credit', 15000.00),
    (4, 'debit', 500.00),
    (4, 'credit', 2000.00),
    (4, 'debit', 1500.00),
    
    -- Account 5 (ACC4001) transactions
    (5, 'credit', 3200.75),
    (5, 'debit', 100.00),
    (5, 'credit', 500.00),
    
    -- Account 6 (ACC5001) transactions
    (6, 'credit', 25000.00),
    (6, 'debit', 2000.00),
    (6, 'credit', 5000.00),
    
    -- Account 7 (ACC5002) transactions
    (7, 'credit', 50000.00),
    (7, 'debit', 10000.00),
    (7, 'credit', 15000.00),
    (7, 'debit', 5000.00);
