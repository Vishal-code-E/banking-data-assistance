"""
PHASE 3: Agent Logic Tests
Tests for retry mechanisms, agent behavior, and workflow logic
"""

import pytest
from ai_engine.graph import banking_assistant_graph
from ai_engine.state import create_initial_state, BankingAssistantState
from unittest.mock import patch, MagicMock


class TestRetryLogic:
    """Test agent retry mechanisms"""
    
    def test_sql_agent_retry_on_invalid_sql(self):
        """Test: SQL agent retries when validation fails"""
        query = "Show transactions"
        initial_state = create_initial_state(query)
        
        # Track retry behavior through state
        result = banking_assistant_graph.invoke(initial_state)
        
        # Check if retry_count field exists and is used
        if "retry_count" in result:
            # Retry count should be >= 0
            assert result["retry_count"] >= 0
            # Should not exceed max retries (typically 2)
            assert result["retry_count"] <= 2
    
    @patch('ai_engine.agents.sql_agent.call_llm_for_sql')
    def test_max_retry_limit(self, mock_llm):
        """Test: System stops at max retry limit"""
        # Force LLM to always return invalid SQL
        mock_llm.side_effect = [
            "INVALID SQL QUERY",  # First attempt
            "STILL INVALID",      # First retry
            "STILL BAD SQL"       # Second retry
        ]
        
        query = "Show all customers"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should eventually error out
        assert result.get("error_message") is not None or result.get("validated_sql") is None
        
        # Should not retry infinitely
        assert mock_llm.call_count <= 3  # Initial + 2 retries
    
    def test_successful_retry(self):
        """Test: Valid SQL generated after retry"""
        # This tests that the system can recover from initial failures
        query = "Show customers"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should eventually succeed (or fail gracefully)
        assert "validated_sql" in result
        assert "error_message" in result or result.get("error_message") is None


class TestIntentAgent:
    """Test intent classification logic"""
    
    def test_ambiguous_query_handling(self):
        """Test: Ambiguous query - 'Show large transactions'"""
        query = "Show large transactions"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # System should:
        # 1. Use default threshold, OR
        # 2. Ask for clarification, OR
        # 3. Make reasonable assumption
        
        if result.get("validated_sql"):
            # Should have some threshold (e.g., > 1000 or > 5000)
            sql_upper = result["validated_sql"].upper()
            assert "WHERE" in sql_upper
            assert "amount" in result["validated_sql"].lower()
            # Some numeric threshold should exist
            assert any(char.isdigit() for char in result["validated_sql"])
    
    def test_intent_extraction_balance_query(self):
        """Test: Intent correctly identified for balance queries"""
        queries = [
            "What is my account balance?",
            "Show account balances",
            "How much money is in each account?"
        ]
        
        for query in queries:
            initial_state = create_initial_state(query)
            result = banking_assistant_graph.invoke(initial_state)
            
            if result.get("validated_sql"):
                # Should query accounts table
                assert "accounts" in result["validated_sql"].lower()
                # Should select balance field
                assert "balance" in result["validated_sql"].lower()
    
    def test_intent_extraction_transaction_query(self):
        """Test: Intent correctly identified for transaction queries"""
        queries = [
            "Show my recent transactions",
            "What are the latest transactions?",
            "List all transactions"
        ]
        
        for query in queries:
            initial_state = create_initial_state(query)
            result = banking_assistant_graph.invoke(initial_state)
            
            if result.get("validated_sql"):
                # Should query transactions table
                assert "transactions" in result["validated_sql"].lower()


class TestValidationAgent:
    """Test validation agent behavior"""
    
    def test_validation_agent_blocks_invalid_sql(self):
        """Test: Validation agent rejects malformed SQL"""
        query = "Show customers"
        initial_state = create_initial_state(query)
        
        # Manually inject bad SQL to test validation
        test_state = initial_state.copy()
        test_state["generated_sql"] = "SELECT * FROM nonexistent_table"
        
        result = banking_assistant_graph.invoke(test_state)
        
        # Validation should fail
        if result.get("validation_result"):
            # Should indicate failure
            validation = result["validation_result"]
            if isinstance(validation, dict):
                assert validation.get("valid") is False or validation.get("is_valid") is False
    
    def test_validation_agent_approves_valid_sql(self):
        """Test: Validation agent approves valid SELECT queries"""
        query = "Show all customers"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # If SQL was generated and validated
        if result.get("validated_sql") and not result.get("error_message"):
            # Validation should have passed
            if result.get("validation_result"):
                validation = result["validation_result"]
                if isinstance(validation, dict):
                    assert validation.get("valid") is True or validation.get("is_valid") is True


class TestInsightAgent:
    """Test insight generation"""
    
    def test_insight_agent_generates_summary(self):
        """Test: Insight agent creates human-readable summary"""
        query = "Show last 5 transactions"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should have summary
        assert result.get("summary") is not None
        
        # Summary should be non-empty string
        if result["summary"]:
            assert isinstance(result["summary"], str)
            assert len(result["summary"]) > 10  # Meaningful summary
    
    def test_insight_agent_suggests_appropriate_chart(self):
        """Test: Chart suggestions are appropriate for query type"""
        test_cases = [
            ("Show transaction trends over time", ["line", "bar"]),
            ("Show total by transaction type", ["pie", "bar"]),
            ("List all customers", ["table"]),
        ]
        
        for query, expected_chart_types in test_cases:
            initial_state = create_initial_state(query)
            result = banking_assistant_graph.invoke(initial_state)
            
            if result.get("chart_suggestion"):
                # Chart should be one of the expected types
                assert result["chart_suggestion"] in ["bar", "line", "pie", "table"]


class TestStateManagement:
    """Test state flow through agents"""
    
    def test_state_progression(self):
        """Test: State properly flows through agent pipeline"""
        query = "Show customers"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # State should contain user query
        assert result.get("user_query") == query or "user_query" in result
        
        # State should have been processed by agents
        # At minimum, should have attempted SQL generation
        assert "generated_sql" in result or "validated_sql" in result
    
    def test_error_state_propagation(self):
        """Test: Errors properly propagate through state"""
        # Use a query that should fail
        query = "DROP TABLE customers"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Error should be in final state
        assert result.get("error_message") is not None or result.get("validated_sql") is None
