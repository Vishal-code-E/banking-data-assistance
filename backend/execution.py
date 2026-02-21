"""
Query Execution Layer for Banking Data Assistant
Safely executes validated SQL queries and returns structured results
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DatabaseError

from backend.db import engine
from backend.validation import validate_sql, ValidationResult
from backend.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# RESULT SERIALIZATION
# ============================================================

def serialize_value(value: Any) -> Any:
    """
    Serialize a single database value to JSON-compatible format
    Handles datetime, date, Decimal, and other special types
    """
    if value is None:
        return None
    
    # Convert datetime to ISO format string
    if isinstance(value, datetime):
        return value.isoformat()
    
    # Convert date to ISO format string
    if isinstance(value, date):
        return value.isoformat()
    
    # Convert Decimal to float
    if isinstance(value, Decimal):
        return float(value)
    
    # Convert bytes to string
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore')
    
    # Return as-is for primitive types
    return value


def serialize_row(row: Any, columns: List[str]) -> Dict[str, Any]:
    """
    Convert a database row to a dictionary with serialized values
    """
    return {
        column: serialize_value(value) 
        for column, value in zip(columns, row)
    }


def serialize_results(rows: List[Any], columns: List[str]) -> List[Dict[str, Any]]:
    """
    Convert all rows to JSON-serializable dictionaries
    """
    return [serialize_row(row, columns) for row in rows]


# ============================================================
# QUERY EXECUTION
# ============================================================

class QueryExecutionError(Exception):
    """Custom exception for query execution errors"""
    pass


class QueryResult:
    """Container for query execution results"""
    
    def __init__(
        self,
        success: bool,
        data: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
        row_count: int = 0,
        execution_time_ms: Optional[float] = None,
        cleaned_sql: Optional[str] = None
    ):
        self.success = success
        self.data = data or []
        self.error = error
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.cleaned_sql = cleaned_sql
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API response"""
        result = {
            "success": self.success,
            "row_count": self.row_count
        }
        
        if self.success:
            result["data"] = self.data
            if self.execution_time_ms is not None:
                result["execution_time_ms"] = round(self.execution_time_ms, 2)
        else:
            result["error"] = self.error
        
        return result


def execute_query(sql: str) -> QueryResult:
    """
    Execute a SQL query safely with validation
    
    Process:
    1. Validate SQL query
    2. Execute using SQLAlchemy text() for safety
    3. Serialize results to JSON-compatible format
    4. Handle errors gracefully
    
    Args:
        sql: SQL query string to execute
    
    Returns:
        QueryResult object containing data or error
    """
    import time
    start_time = time.time()
    
    try:
        # Step 1: Validate SQL
        validation_result: ValidationResult = validate_sql(sql)
        
        if not validation_result.is_valid:
            logger.warning(f"Query validation failed: {validation_result.error}")
            return QueryResult(
                success=False,
                error=f"Validation error: {validation_result.error}"
            )
        
        cleaned_sql = validation_result.cleaned_sql
        logger.info(f"Executing query: {cleaned_sql[:100]}...")
        
        # Step 2: Execute query
        with engine.connect() as conn:
            # Use text() for safe execution with SQLAlchemy
            result = conn.execute(text(cleaned_sql))
            
            # Fetch all rows
            rows = result.fetchall()
            
            # Get column names
            columns = list(result.keys())
            
            # Check row limit
            if len(rows) > settings.MAX_RESULT_ROWS:
                logger.warning(
                    f"Query returned {len(rows)} rows, truncating to {settings.MAX_RESULT_ROWS}"
                )
                rows = rows[:settings.MAX_RESULT_ROWS]
            
            # Step 3: Serialize results
            serialized_data = serialize_results(rows, columns)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(f"Query executed successfully: {len(rows)} rows in {execution_time_ms:.2f}ms")
            
            return QueryResult(
                success=True,
                data=serialized_data,
                row_count=len(rows),
                execution_time_ms=execution_time_ms,
                cleaned_sql=cleaned_sql
            )
    
    except OperationalError as e:
        # Database operational errors (connection issues, timeout, etc.)
        logger.error(f"Database operational error: {e}")
        return QueryResult(
            success=False,
            error=f"Database error: {str(e)}"
        )
    
    except DatabaseError as e:
        # Database errors (syntax errors, constraint violations, etc.)
        logger.error(f"Database error: {e}")
        return QueryResult(
            success=False,
            error=f"Query execution error: {str(e)}"
        )
    
    except SQLAlchemyError as e:
        # Generic SQLAlchemy errors
        logger.error(f"SQLAlchemy error: {e}")
        return QueryResult(
            success=False,
            error=f"Database error: {str(e)}"
        )
    
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error during query execution: {e}", exc_info=True)
        return QueryResult(
            success=False,
            error="An unexpected error occurred during query execution"
        )


# ============================================================
# QUERY EXECUTION WITH TIMEOUT
# ============================================================

def execute_query_with_timeout(sql: str, timeout: Optional[int] = None) -> QueryResult:
    """
    Execute query with timeout protection
    
    Args:
        sql: SQL query to execute
        timeout: Timeout in seconds (uses settings.QUERY_TIMEOUT if not provided)
    
    Returns:
        QueryResult object
    """
    # Note: SQLite doesn't support query timeout natively
    # For production with PostgreSQL, we can use statement_timeout
    # For now, we'll use the basic execute_query
    
    timeout = timeout or settings.QUERY_TIMEOUT
    
    # For SQLite, we rely on the synchronous execution
    # For PostgreSQL, we would set statement_timeout before execution
    
    if not settings.DATABASE_URL.startswith("sqlite"):
        # Set statement timeout for PostgreSQL
        timeout_sql = f"SET statement_timeout = {timeout * 1000};"  # milliseconds
        try:
            with engine.connect() as conn:
                conn.execute(text(timeout_sql))
        except Exception as e:
            logger.warning(f"Failed to set query timeout: {e}")
    
    return execute_query(sql)


# ============================================================
# BATCH QUERY EXECUTION (Future feature)
# ============================================================

def execute_batch_queries(queries: List[str]) -> List[QueryResult]:
    """
    Execute multiple queries in sequence
    Each query is validated and executed independently
    
    Note: This is for future multi-query support
    Currently not exposed via API
    """
    results = []
    
    for idx, query in enumerate(queries):
        logger.info(f"Executing batch query {idx + 1}/{len(queries)}")
        result = execute_query(query)
        results.append(result)
        
        # Stop on first error (optional behavior)
        if not result.success:
            logger.warning(f"Batch execution stopped at query {idx + 1} due to error")
            break
    
    return results


# ============================================================
# QUERY ANALYSIS (Future feature)
# ============================================================

def analyze_query(sql: str) -> Dict[str, Any]:
    """
    Analyze query without executing it
    Returns metadata about the query
    
    Future feature for query optimization and cost estimation
    """
    validation_result = validate_sql(sql)
    
    if not validation_result.is_valid:
        return {
            "valid": False,
            "error": validation_result.error
        }
    
    # For SQLite, we can use EXPLAIN QUERY PLAN
    try:
        with engine.connect() as conn:
            explain_result = conn.execute(
                text(f"EXPLAIN QUERY PLAN {validation_result.cleaned_sql}")
            )
            plan = [dict(row._mapping) for row in explain_result]
            
            return {
                "valid": True,
                "query": validation_result.cleaned_sql,
                "execution_plan": plan
            }
    except Exception as e:
        logger.error(f"Query analysis failed: {e}")
        return {
            "valid": True,
            "query": validation_result.cleaned_sql,
            "error": f"Analysis failed: {str(e)}"
        }
