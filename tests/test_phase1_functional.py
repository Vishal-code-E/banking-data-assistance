"""
PHASE 1: Functional Tests - Valid Queries
Tests for legitimate banking queries through the AI engine
"""

import pytest
from ai_engine.graph import banking_assistant_graph
from ai_engine.state import create_initial_state


class TestValidQueries:
    """Test valid banking queries through the AI pipeline"""
    
    def test_simple_transaction_query(self):
        """Test: Show last 5 transactions"""
        query = "Show last 5 transactions"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Validate SQL generation
        assert result["validated_sql"] is not None
        assert "SELECT" in result["validated_sql"].upper()
        assert "transactions" in result["validated_sql"].lower()
        assert "LIMIT 5" in result["validated_sql"] or "LIMIT  5" in result["validated_sql"]
        assert "ORDER BY" in result["validated_sql"].upper()  # Should order by created_at
        
        # Validate no errors
        assert result.get("error_message") is None
        
        # Validate summary exists
        assert result.get("summary") is not None
        assert len(result["summary"]) > 0
        
        # Validate chart suggestion
        assert result.get("chart_suggestion") is not None
        assert result["chart_suggestion"] in ["bar", "line", "pie", "table"]
    
    def test_high_value_transactions(self):
        """Test: Show transactions above 10000"""
        query = "Show transactions above 10000"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Validate SQL contains WHERE clause with amount filter
        assert result["validated_sql"] is not None
        assert "WHERE" in result["validated_sql"].upper()
        assert "amount" in result["validated_sql"].lower()
        assert "10000" in result["validated_sql"]
        
        # Check for proper comparison operator
        sql_upper = result["validated_sql"].upper()
        assert ">" in result["validated_sql"] or "GREATER" in sql_upper
        
        assert result.get("error_message") is None
    
    def test_customer_accounts_join(self):
        """Test: Show accounts for customer 1"""
        query = "Show accounts for customer 1"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Validate SQL contains JOIN
        sql_upper = result["validated_sql"].upper()
        assert "JOIN" in sql_upper
        assert "customers" in result["validated_sql"].lower()
        assert "accounts" in result["validated_sql"].lower()
        
        # Should filter by customer ID
        assert "customer_id" in result["validated_sql"].lower() or "c.id" in result["validated_sql"].lower()
        assert "1" in result["validated_sql"]
        
        assert result.get("error_message") is None
    
    def test_daily_credit_summary(self):
        """Test: Show total credit transactions today"""
        query = "Show total credit transactions today"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Validate SQL contains aggregation
        sql_upper = result["validated_sql"].upper()
        assert "SUM" in sql_upper
        assert "amount" in result["validated_sql"].lower()
        
        # Should filter by type = 'credit'
        assert "credit" in result["validated_sql"].lower()
        assert "type" in result["validated_sql"].lower()
        
        # Should have date filter
        assert "DATE" in sql_upper or "created_at" in result["validated_sql"].lower()
        
        assert result.get("error_message") is None
        
        # Chart suggestion should be appropriate for aggregation
        assert result.get("chart_suggestion") in ["bar", "pie", "table"]
    
    def test_account_balance_query(self):
        """Test: Show account balances"""
        query = "Show account balances for all customers"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should select balance field
        assert "balance" in result["validated_sql"].lower()
        assert "accounts" in result["validated_sql"].lower()
        
        # Should join with customers
        sql_upper = result["validated_sql"].upper()
        assert "JOIN" in sql_upper or "customers" in result["validated_sql"].lower()
        
        assert result.get("error_message") is None


class TestOutputStructure:
    """Test that output structure matches expected contract"""
    
    def test_output_contract(self):
        """Validate output JSON structure"""
        query = "Show last 10 transactions"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Required fields
        assert "validated_sql" in result
        assert "summary" in result
        assert "chart_suggestion" in result
        
        # Optional fields
        assert "error_message" in result or result.get("error_message") is None
        
        # Type validation
        assert isinstance(result["validated_sql"], str) or result["validated_sql"] is None
        assert isinstance(result["summary"], str) or result["summary"] is None
        assert isinstance(result["chart_suggestion"], str) or result["chart_suggestion"] is None


class TestComplexQueries:
    """Test complex multi-table queries"""
    
    def test_transaction_summary_by_customer(self):
        """Test: Summary of transactions grouped by customer"""
        query = "Show total transaction amounts by customer"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        sql_upper = result["validated_sql"].upper()
        
        # Should have aggregation
        assert "SUM" in sql_upper or "COUNT" in sql_upper
        
        # Should have GROUP BY
        assert "GROUP BY" in sql_upper
        
        # Should join customers, accounts, and transactions
        assert "customers" in result["validated_sql"].lower()
        assert "transactions" in result["validated_sql"].lower()
        
        assert result.get("error_message") is None
    
    def test_average_balance_query(self):
        """Test: Calculate average account balance"""
        query = "What is the average account balance?"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        sql_upper = result["validated_sql"].upper()
        
        # Should use AVG aggregation
        assert "AVG" in sql_upper
        assert "balance" in result["validated_sql"].lower()
        assert "accounts" in result["validated_sql"].lower()
        
        assert result.get("error_message") is None
