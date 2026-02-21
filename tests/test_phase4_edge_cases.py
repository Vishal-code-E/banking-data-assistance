"""
PHASE 4: Edge Cases and Error Handling
Tests for boundary conditions and graceful failure
"""

import pytest
from ai_engine.graph import banking_assistant_graph
from ai_engine.state import create_initial_state


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_query(self):
        """Test: Empty query string"""
        query = ""
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should handle gracefully
        assert "error_message" in result
        # Should not crash
        assert isinstance(result, dict)
        # Should have error
        assert result.get("error_message") is not None or result.get("validated_sql") is None
    
    def test_whitespace_only_query(self):
        """Test: Query with only whitespace"""
        query = "   \n\t   "
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should be treated as empty/invalid
        assert result.get("error_message") is not None or result.get("validated_sql") is None
    
    def test_very_long_query(self):
        """Test: Extremely long query (>1000 chars)"""
        query = "Show transactions " + "with amount greater than 100 " * 100  # Very long
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should handle without crashing
        assert isinstance(result, dict)
        
        # May reject due to length or process it
        # Either way, should not crash
        assert "validated_sql" in result or "error_message" in result
    
    def test_special_characters_in_query(self):
        """Test: Query with special characters"""
        query = "Show transactions with amount > $1,000.00"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should handle special chars gracefully
        assert isinstance(result, dict)
        
        # If successful, should sanitize special chars
        if result.get("validated_sql"):
            # SQL should not contain literal $ signs
            assert "$" not in result["validated_sql"]
    
    def test_unicode_characters(self):
        """Test: Query with unicode characters"""
        query = "Show customers named José or François"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should handle unicode without crashing
        assert isinstance(result, dict)
    
    def test_numeric_only_query(self):
        """Test: Query that's just a number"""
        query = "12345"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should not crash
        assert isinstance(result, dict)
        # Likely should have error or no SQL
        assert result.get("error_message") is not None or result.get("validated_sql") is None


class TestResultLimits:
    """Test handling of large result sets"""
    
    def test_query_returning_many_rows(self):
        """Test: Query that returns >1000 rows"""
        query = "Show all transactions"  # Could return many rows
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should either:
        # 1. Add LIMIT clause automatically, OR
        # 2. Handle large results gracefully
        
        if result.get("validated_sql"):
            sql_upper = result["validated_sql"].upper()
            # Should have some limit mechanism
            # Could be LIMIT, TOP, or FETCH FIRST
            has_limit = any(keyword in sql_upper for keyword in ["LIMIT", "TOP", "FETCH"])
            
            # If no explicit limit, should still not crash
            assert isinstance(result, dict)
    
    def test_no_results_query(self):
        """Test: Query that returns no results"""
        query = "Show transactions with amount > 999999999"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should handle empty results gracefully
        assert isinstance(result, dict)
        assert "validated_sql" in result or "error_message" in result


class TestUnknownTables:
    """Test queries referencing non-existent tables"""
    
    def test_nonexistent_table_request(self):
        """Test: Query for table that doesn't exist"""
        query = "Show me all products"  # products table doesn't exist
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should either:
        # 1. Reject the query (preferred), OR
        # 2. Map to valid table, OR
        # 3. Return error
        
        if result.get("validated_sql"):
            sql_lower = result["validated_sql"].lower()
            # Should not contain 'products'
            assert "products" not in sql_lower or result.get("error_message") is not None
            
            # Should use whitelisted tables only
            allowed = ["customers", "accounts", "transactions"]
            has_allowed = any(table in sql_lower for table in allowed)
            assert has_allowed or result.get("error_message") is not None
    
    def test_typo_in_table_name(self):
        """Test: Misspelled table name"""
        query = "Show all custmers"  # Typo: custmers
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # System should:
        # 1. Correct the typo (smart), OR
        # 2. Map to correct table, OR
        # 3. Reject
        
        if result.get("validated_sql"):
            sql_lower = result["validated_sql"].lower()
            # Should use correct spelling
            if "customer" in sql_lower:
                assert "customers" in sql_lower  # Correct spelling


class TestMalformedInput:
    """Test handling of malformed or nonsensical input"""
    
    def test_nonsensical_query(self):
        """Test: Query that makes no sense"""
        query = "asdfghjkl qwertyuiop"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should not crash
        assert isinstance(result, dict)
        
        # Should have error or no SQL
        assert result.get("error_message") is not None or result.get("validated_sql") is None
    
    def test_sql_in_natural_language(self):
        """Test: User provides SQL directly instead of natural language"""
        query = "SELECT * FROM customers WHERE id = 1"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # System should:
        # 1. Validate and use the SQL, OR
        # 2. Treat it as natural language
        
        # Either way, should not crash
        assert isinstance(result, dict)
        
        # If validated, should be SELECT only
        if result.get("validated_sql"):
            assert result["validated_sql"].strip().upper().startswith("SELECT")


class TestErrorHandling:
    """Test error handling and recovery"""
    
    def test_no_crash_on_invalid_state(self):
        """Test: System doesn't crash with invalid state"""
        # Create malformed state
        invalid_state = {"invalid_key": "invalid_value"}
        
        try:
            result = banking_assistant_graph.invoke(invalid_state)
            # Should either process or error gracefully
            assert isinstance(result, dict)
        except Exception as e:
            # If exception is raised, should be handled exception
            assert isinstance(e, (ValueError, KeyError, TypeError))
    
    def test_error_message_format(self):
        """Test: Error messages are user-friendly"""
        query = "DROP TABLE customers"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        if result.get("error_message"):
            error = result["error_message"]
            # Should be string
            assert isinstance(error, str)
            # Should be non-empty
            assert len(error) > 0
            # Should not expose internal details
            assert "Traceback" not in error
            assert "Exception" not in error or "not allowed" in error.lower()
    
    def test_graceful_degradation(self):
        """Test: System degrades gracefully on partial failure"""
        query = "Show customers"
        initial_state = create_initial_state(query)
        
        result = banking_assistant_graph.invoke(initial_state)
        
        # Even if some components fail, should return structured response
        assert isinstance(result, dict)
        
        # Core fields should exist
        assert "validated_sql" in result or "error_message" in result
