"""
Tests for sql_validator and database modules.
Run with: pytest tests/ -v
"""
import sys
import os

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from sql_validator import validate_query
from database import get_connection, get_schema_description
from sql_generator import _enforce_limit


# ---------------------------------------------------------------------------
# sql_validator tests
# ---------------------------------------------------------------------------

class TestValidateQuery:
    def test_simple_select_passes(self):
        ok, msg = validate_query("SELECT * FROM customers")
        assert ok is True

    def test_select_with_where_passes(self):
        ok, _ = validate_query("SELECT name, email FROM customers WHERE city = 'New York'")
        assert ok is True

    def test_select_with_join_passes(self):
        sql = (
            "SELECT c.name, a.balance "
            "FROM customers c JOIN accounts a ON c.customer_id = a.customer_id"
        )
        ok, _ = validate_query(sql)
        assert ok is True

    def test_insert_rejected(self):
        ok, reason = validate_query("INSERT INTO customers VALUES (9,'X','x@x.com','','',DATE('now'))")
        assert ok is False
        assert "SELECT" in reason or "forbidden" in reason

    def test_update_rejected(self):
        ok, _ = validate_query("UPDATE accounts SET balance = 0 WHERE account_id = 1")
        assert ok is False

    def test_delete_rejected(self):
        ok, _ = validate_query("DELETE FROM transactions WHERE transaction_id = 1")
        assert ok is False

    def test_drop_rejected(self):
        ok, _ = validate_query("DROP TABLE customers")
        assert ok is False

    def test_multi_statement_rejected(self):
        ok, reason = validate_query("SELECT 1; SELECT 2")
        assert ok is False
        assert "Multiple" in reason

    def test_comment_injection_rejected(self):
        ok, reason = validate_query("SELECT * FROM customers -- injected")
        assert ok is False
        assert "comment" in reason.lower()

    def test_non_select_rejected(self):
        ok, reason = validate_query("PRAGMA table_info(customers)")
        assert ok is False

    def test_select_must_be_first_word(self):
        ok, _ = validate_query("  SELECT 1")
        assert ok is True  # leading whitespace stripped


# ---------------------------------------------------------------------------
# database tests
# ---------------------------------------------------------------------------

class TestDatabase:
    def test_connection_returns_same_instance(self):
        conn1 = get_connection()
        conn2 = get_connection()
        assert conn1 is conn2

    def test_customers_seeded(self):
        conn = get_connection()
        rows = conn.execute("SELECT COUNT(*) FROM customers").fetchone()
        assert rows[0] >= 8

    def test_accounts_seeded(self):
        conn = get_connection()
        rows = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()
        assert rows[0] >= 10

    def test_transactions_seeded(self):
        conn = get_connection()
        rows = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
        assert rows[0] > 0

    def test_schema_description_contains_tables(self):
        desc = get_schema_description()
        assert "customers" in desc
        assert "accounts" in desc
        assert "transactions" in desc

    def test_account_types_valid(self):
        conn = get_connection()
        invalid = conn.execute(
            "SELECT COUNT(*) FROM accounts "
            "WHERE account_type NOT IN ('savings','checking','credit')"
        ).fetchone()[0]
        assert invalid == 0

    def test_transaction_types_valid(self):
        conn = get_connection()
        invalid = conn.execute(
            "SELECT COUNT(*) FROM transactions "
            "WHERE transaction_type NOT IN ('credit','debit','transfer')"
        ).fetchone()[0]
        assert invalid == 0


# ---------------------------------------------------------------------------
# sql_generator tests (limit enforcement only – no OpenAI call)
# ---------------------------------------------------------------------------

class TestEnforceLimit:
    def test_adds_limit_when_absent(self):
        sql = "SELECT * FROM customers"
        result = _enforce_limit(sql, max_rows=50)
        assert result.endswith("LIMIT 50")

    def test_does_not_duplicate_limit(self):
        sql = "SELECT * FROM customers LIMIT 10"
        result = _enforce_limit(sql)
        assert result.count("LIMIT") == 1

    def test_default_limit_is_100(self):
        sql = "SELECT * FROM transactions"
        result = _enforce_limit(sql)
        assert "LIMIT 100" in result
