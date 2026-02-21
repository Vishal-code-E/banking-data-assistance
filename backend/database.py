"""
Database setup and seed data for the Banking Data Assistant.
Creates an in-memory SQLite database with Customers, Accounts, and Transactions.
"""
import sqlite3
from datetime import date, timedelta
import random

DB_PATH = ":memory:"

_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """Return (and lazily create) the shared in-memory SQLite connection."""
    global _connection
    if _connection is None:
        _connection = _create_and_seed()
    return _connection


def _create_and_seed() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _create_schema(conn)
    _seed(conn)
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id   INTEGER PRIMARY KEY,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            phone         TEXT,
            city          TEXT,
            created_at    DATE    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS accounts (
            account_id    INTEGER PRIMARY KEY,
            customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
            account_type  TEXT    NOT NULL CHECK(account_type IN ('savings','checking','credit')),
            balance       REAL    NOT NULL DEFAULT 0,
            currency      TEXT    NOT NULL DEFAULT 'USD',
            opened_at     DATE    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id   INTEGER PRIMARY KEY,
            account_id       INTEGER NOT NULL REFERENCES accounts(account_id),
            transaction_type TEXT    NOT NULL CHECK(transaction_type IN ('credit','debit','transfer')),
            amount           REAL    NOT NULL,
            description      TEXT,
            transaction_date DATE    NOT NULL
        );
        """
    )
    conn.commit()


def _seed(conn: sqlite3.Connection) -> None:
    random.seed(42)
    today = date.today()

    def d(offset: int) -> str:
        return (today - timedelta(days=offset)).isoformat()

    customers = [
        (1, "Alice Johnson",   "alice@example.com",   "555-0101", "New York",    d(730)),
        (2, "Bob Smith",       "bob@example.com",     "555-0102", "Los Angeles", d(600)),
        (3, "Carol Williams",  "carol@example.com",   "555-0103", "Chicago",     d(500)),
        (4, "David Brown",     "david@example.com",   "555-0104", "Houston",     d(400)),
        (5, "Eva Martinez",    "eva@example.com",     "555-0105", "Phoenix",     d(300)),
        (6, "Frank Lee",       "frank@example.com",   "555-0106", "Philadelphia",d(200)),
        (7, "Grace Kim",       "grace@example.com",   "555-0107", "San Antonio", d(150)),
        (8, "Henry Davis",     "henry@example.com",   "555-0108", "San Diego",   d(100)),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?)", customers
    )

    accounts = [
        (1,  1, "savings",  15000.00, "USD", d(700)),
        (2,  1, "checking",  3200.00, "USD", d(690)),
        (3,  2, "savings",  22000.00, "USD", d(580)),
        (4,  2, "credit",   -1500.00, "USD", d(570)),
        (5,  3, "checking",  8750.00, "USD", d(480)),
        (6,  4, "savings",  31000.00, "USD", d(380)),
        (7,  5, "checking",  4500.00, "USD", d(280)),
        (8,  6, "savings",   9200.00, "USD", d(180)),
        (9,  7, "checking",  6100.00, "USD", d(130)),
        (10, 8, "credit",   -800.00,  "USD", d(90)),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO accounts VALUES (?,?,?,?,?,?)", accounts
    )

    descriptions = [
        "Grocery Store", "Online Transfer", "Salary Credit", "ATM Withdrawal",
        "Utility Bill", "Restaurant", "Refund", "Insurance Premium",
        "Subscription Fee", "Interest Credit",
    ]
    tx_types = ["credit", "debit", "transfer"]
    transactions = []
    tx_id = 1
    for offset in range(60):
        tx_date = (today - timedelta(days=offset)).isoformat()
        num_tx = random.randint(3, 8)
        for _ in range(num_tx):
            account_id = random.randint(1, 10)
            tx_type = random.choice(tx_types)
            amount = round(random.uniform(10, 2000), 2)
            desc = random.choice(descriptions)
            transactions.append((tx_id, account_id, tx_type, amount, desc, tx_date))
            tx_id += 1

    conn.executemany(
        "INSERT OR IGNORE INTO transactions VALUES (?,?,?,?,?,?)", transactions
    )
    conn.commit()


def get_schema_description() -> str:
    """Return a compact schema string to include in prompts."""
    return """
Tables:
  customers(customer_id PK, name, email, phone, city, created_at DATE)
  accounts(account_id PK, customer_id FK, account_type TEXT ['savings','checking','credit'],
           balance REAL, currency TEXT, opened_at DATE)
  transactions(transaction_id PK, account_id FK,
               transaction_type TEXT ['credit','debit','transfer'],
               amount REAL, description TEXT, transaction_date DATE)
""".strip()
