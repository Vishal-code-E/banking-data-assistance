"""
Tests for sql_validator, database, sql_generator, and AI engine integration.
Run with: pytest tests/ -v
"""
import sys
import os

# Ensure backend is importable (also covers ai_engine package at repo root)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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


# ---------------------------------------------------------------------------
# AI engine integration tests
# ---------------------------------------------------------------------------

class TestProcessQuery:
    def test_returns_required_keys(self):
        from ai_engine.main import process_query
        result = process_query("Show last 5 transactions above 10000")
        assert set(result.keys()) >= {"validated_sql", "summary", "chart_suggestion", "error"}

    def test_successful_query_has_no_error(self):
        from ai_engine.main import process_query
        result = process_query("Show last 5 transactions above 10000")
        assert result["error"] is None

    def test_successful_query_has_validated_sql(self):
        from ai_engine.main import process_query
        result = process_query("Show last 5 transactions above 10000")
        assert result["validated_sql"] is not None
        assert result["validated_sql"].strip().upper().startswith("SELECT")

    def test_successful_query_has_summary(self):
        from ai_engine.main import process_query
        result = process_query("Show last 5 transactions above 10000")
        assert result["summary"] is not None

    def test_successful_query_has_chart_suggestion(self):
        from ai_engine.main import process_query
        result = process_query("Show last 5 transactions above 10000")
        assert result["chart_suggestion"] is not None


class TestBackendQueryEndpoint:
    def get_client(self):
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)

    def test_query_returns_200(self):
        client = self.get_client()
        resp = client.post("/query", json={"query": "Show last 5 transactions above 10000"})
        assert resp.status_code == 200

    def test_query_response_has_sql(self):
        client = self.get_client()
        resp = client.post("/query", json={"query": "Show last 5 transactions above 10000"})
        data = resp.json()
        assert "sql" in data
        assert data["sql"].strip().upper().startswith("SELECT")

    def test_query_response_has_columns(self):
        client = self.get_client()
        resp = client.post("/query", json={"query": "Show last 5 transactions above 10000"})
        data = resp.json()
        assert "columns" in data
        assert isinstance(data["columns"], list)

    def test_query_response_has_row_count(self):
        client = self.get_client()
        resp = client.post("/query", json={"query": "Show last 5 transactions above 10000"})
        data = resp.json()
        assert "row_count" in data
        assert isinstance(data["row_count"], int)

    def test_query_response_has_summary(self):
        client = self.get_client()
        resp = client.post("/query", json={"query": "Show last 5 transactions above 10000"})
        data = resp.json()
        assert "summary" in data

    def test_query_response_has_chart_suggestion(self):
        client = self.get_client()
        resp = client.post("/query", json={"query": "Show last 5 transactions above 10000"})
        data = resp.json()
        assert "chart_suggestion" in data

    def test_query_too_short_returns_422(self):
        client = self.get_client()
        resp = client.post("/query", json={"query": "hi"})
        assert resp.status_code == 422

    def test_average_balance_query(self):
        client = self.get_client()
        resp = client.post("/query", json={"query": "What is the average balance for savings accounts?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["row_count"] >= 0
