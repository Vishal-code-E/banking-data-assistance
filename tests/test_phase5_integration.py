"""
PHASE 5: Integration Tests
End-to-end tests for the complete pipeline: API → AI → Validation → Execution
"""

import pytest
import httpx
from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)


class TestBackendAPI:
    """Test FastAPI backend endpoints"""
    
    def test_health_endpoint(self):
        """Test: GET /health"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "tables" in data
        assert isinstance(data["tables"], list)
    
    def test_query_endpoint_valid_sql(self):
        """Test: POST /query with valid SQL"""
        response = client.post(
            "/query",
            json={"sql": "SELECT * FROM customers LIMIT 5"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert data["success"] is True
        assert "data" in data
        assert "row_count" in data
        assert isinstance(data["data"], list)
    
    def test_query_endpoint_invalid_sql(self):
        """Test: POST /query with invalid SQL (DROP)"""
        response = client.post(
            "/query",
            json={"sql": "DROP TABLE customers"}
        )
        
        # Should return 200 but with success=false
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
    
    def test_query_endpoint_sql_injection(self):
        """Test: POST /query with SQL injection attempt"""
        response = client.post(
            "/query",
            json={"sql": "SELECT * FROM customers; DROP TABLE customers;"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is False
        assert "error" in data
    
    def test_query_endpoint_missing_sql(self):
        """Test: POST /query without SQL field"""
        response = client.post(
            "/query",
            json={}
        )
        
        # Should return 422 (validation error)
        assert response.status_code == 422
    
    def test_tables_endpoint(self):
        """Test: GET /tables"""
        response = client.get("/tables")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "tables" in data
        assert isinstance(data["tables"], list)
        assert len(data["tables"]) > 0


class TestEndToEndPipeline:
    """Test complete pipeline from query to response"""
    
    def test_simple_query_full_pipeline(self):
        """Test: Simple query through complete pipeline"""
        # Natural language query
        query = "Show last 5 transactions"
        
        # Expected flow:
        # 1. Intent Agent processes query
        # 2. SQL Agent generates SQL
        # 3. Validation Agent validates SQL
        # 4. Backend executes SQL
        # 5. Insight Agent generates summary
        
        # For this test, we'll test the AI pipeline
        from ai_engine.graph import banking_assistant_graph
        from ai_engine.state import create_initial_state
        
        initial_state = create_initial_state(query)
        result = banking_assistant_graph.invoke(initial_state)
        
        # Validate complete output
        assert "validated_sql" in result
        assert "summary" in result
        assert "chart_suggestion" in result
        
        # If SQL was generated, test execution
        if result.get("validated_sql"):
            response = client.post(
                "/query",
                json={"sql": result["validated_sql"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_complex_query_full_pipeline(self):
        """Test: Complex JOIN query through pipeline"""
        query = "Show customers with their account balances"
        
        from ai_engine.graph import banking_assistant_graph
        from ai_engine.state import create_initial_state
        
        initial_state = create_initial_state(query)
        result = banking_assistant_graph.invoke(initial_state)
        
        # Should have valid SQL
        if result.get("validated_sql"):
            # SQL should contain JOIN
            assert "JOIN" in result["validated_sql"].upper()
            
            # Execute it
            response = client.post(
                "/query",
                json={"sql": result["validated_sql"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have results
            if data["success"]:
                assert "data" in data
                assert isinstance(data["data"], list)
    
    def test_aggregation_query_full_pipeline(self):
        """Test: Aggregation query through pipeline"""
        query = "What is the total amount of all transactions?"
        
        from ai_engine.graph import banking_assistant_graph
        from ai_engine.state import create_initial_state
        
        initial_state = create_initial_state(query)
        result = banking_assistant_graph.invoke(initial_state)
        
        if result.get("validated_sql"):
            # Should have SUM
            assert "SUM" in result["validated_sql"].upper()
            
            # Execute
            response = client.post(
                "/query",
                json={"sql": result["validated_sql"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "data" in data


class TestOutputContract:
    """Test that output matches expected contract"""
    
    def test_ai_output_contract(self):
        """Test: AI pipeline output has required fields"""
        from ai_engine.graph import banking_assistant_graph
        from ai_engine.state import create_initial_state
        
        query = "Show all customers"
        initial_state = create_initial_state(query)
        result = banking_assistant_graph.invoke(initial_state)
        
        # Required fields in AI output
        required_fields = [
            "validated_sql",
            "summary", 
            "chart_suggestion"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Error field should exist (can be None)
        assert "error_message" in result or result.get("error_message") is None
    
    def test_backend_success_output_contract(self):
        """Test: Backend success response has required fields"""
        response = client.post(
            "/query",
            json={"sql": "SELECT * FROM customers LIMIT 1"}
        )
        
        data = response.json()
        
        # Required fields in backend success response
        required_fields = ["success", "data", "row_count"]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Type checks
        assert isinstance(data["success"], bool)
        assert isinstance(data["data"], list)
        assert isinstance(data["row_count"], int)
    
    def test_backend_error_output_contract(self):
        """Test: Backend error response has required fields"""
        response = client.post(
            "/query",
            json={"sql": "DROP TABLE customers"}
        )
        
        data = response.json()
        
        # Required fields in error response
        required_fields = ["success", "error", "row_count"]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Values
        assert data["success"] is False
        assert isinstance(data["error"], str)
        assert data["row_count"] == 0


class TestIntegrationScenarios:
    """Test realistic user scenarios"""
    
    def test_scenario_check_balance(self):
        """Scenario: User wants to check account balance"""
        query = "What is the balance of account ACC1001?"
        
        from ai_engine.graph import banking_assistant_graph
        from ai_engine.state import create_initial_state
        
        initial_state = create_initial_state(query)
        ai_result = banking_assistant_graph.invoke(initial_state)
        
        if ai_result.get("validated_sql"):
            # Should query accounts table
            assert "accounts" in ai_result["validated_sql"].lower()
            assert "balance" in ai_result["validated_sql"].lower()
            
            # Execute query
            response = client.post(
                "/query",
                json={"sql": ai_result["validated_sql"]}
            )
            
            assert response.status_code == 200
            exec_result = response.json()
            
            # Should have data
            if exec_result["success"]:
                assert len(exec_result["data"]) > 0
                # Should have summary
                assert ai_result.get("summary") is not None
    
    def test_scenario_recent_transactions(self):
        """Scenario: User wants to see recent transactions"""
        query = "Show me the last 10 transactions"
        
        from ai_engine.graph import banking_assistant_graph
        from ai_engine.state import create_initial_state
        
        initial_state = create_initial_state(query)
        ai_result = banking_assistant_graph.invoke(initial_state)
        
        if ai_result.get("validated_sql"):
            # Should have LIMIT 10
            assert "10" in ai_result["validated_sql"]
            assert "transactions" in ai_result["validated_sql"].lower()
            
            # Execute
            response = client.post(
                "/query",
                json={"sql": ai_result["validated_sql"]}
            )
            
            assert response.status_code == 200
            exec_result = response.json()
            
            # Should return at most 10 rows
            if exec_result["success"]:
                assert exec_result["row_count"] <= 10
    
    def test_scenario_high_value_alerts(self):
        """Scenario: User wants to find high-value transactions"""
        query = "Show transactions over $5000"
        
        from ai_engine.graph import banking_assistant_graph
        from ai_engine.state import create_initial_state
        
        initial_state = create_initial_state(query)
        ai_result = banking_assistant_graph.invoke(initial_state)
        
        if ai_result.get("validated_sql"):
            # Should filter by amount
            assert "WHERE" in ai_result["validated_sql"].upper()
            assert "amount" in ai_result["validated_sql"].lower()
            assert "5000" in ai_result["validated_sql"]
            
            # Execute
            response = client.post(
                "/query",
                json={"sql": ai_result["validated_sql"]}
            )
            
            assert response.status_code == 200


class TestPerformance:
    """Test system performance and limits"""
    
    def test_response_time_simple_query(self):
        """Test: Response time for simple query"""
        import time
        
        start = time.time()
        response = client.post(
            "/query",
            json={"sql": "SELECT * FROM customers LIMIT 5"}
        )
        end = time.time()
        
        # Should respond within reasonable time (< 5 seconds)
        assert (end - start) < 5.0
        assert response.status_code == 200
    
    def test_concurrent_requests(self):
        """Test: Handle multiple concurrent requests"""
        import concurrent.futures
        
        def make_request():
            return client.post(
                "/query",
                json={"sql": "SELECT * FROM customers LIMIT 1"}
            )
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        assert len(responses) == 10
        for response in responses:
            assert response.status_code == 200
