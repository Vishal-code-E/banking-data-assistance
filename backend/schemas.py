"""
Pydantic schemas for Banking Data Assistant API
Defines request and response models for type safety and validation
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class QueryRequest(BaseModel):
    """
    Request model for SQL query execution
    """
    sql: str = Field(
        ...,
        description="SQL query to execute (SELECT only)",
        min_length=1,
        max_length=5000,
        examples=["SELECT * FROM customers LIMIT 10"]
    )

    @field_validator('sql')
    @classmethod
    def validate_sql_not_empty(cls, v: str) -> str:
        """Ensure SQL is not just whitespace"""
        if not v or not v.strip():
            raise ValueError("SQL query cannot be empty or whitespace only")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "sql": "SELECT * FROM customers WHERE id = 1"
            }
        }
    }


# ============================================================
# RESPONSE SCHEMAS — Standardized Contract
# ============================================================

class QueryResponse(BaseModel):
    """
    Unified response model for /query endpoint.
    Both success and error responses follow this contract.
    """
    validated_sql: Optional[str] = Field(
        default=None,
        description="The validated SQL that was executed"
    )
    execution_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Query execution result with data and row_count"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Human-readable summary of results"
    )
    chart_suggestion: Optional[str] = Field(
        default=None,
        description="Suggested chart type for visualization"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message, null on success"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "validated_sql": "SELECT * FROM customers LIMIT 10",
                    "execution_result": {
                        "data": [{"id": 1, "name": "John Doe"}],
                        "row_count": 1,
                        "execution_time_ms": 15.32
                    },
                    "summary": "Returned 1 customer record",
                    "chart_suggestion": "table",
                    "error": None
                },
                {
                    "validated_sql": None,
                    "execution_result": None,
                    "summary": None,
                    "chart_suggestion": None,
                    "error": "Validation error: Only SELECT statements are allowed"
                }
            ]
        }
    }


# ============================================================
# HEALTH CHECK SCHEMAS
# ============================================================

class HealthResponse(BaseModel):
    """
    Response model for health check endpoint
    """
    status: str = Field(
        ...,
        description="Overall health status"
    )
    database: Optional[str] = Field(
        default=None,
        description="Database type"
    )
    tables: List[str] = Field(
        default=[],
        description="List of available tables"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error details when unhealthy"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "database": "sqlite",
                "tables": ["customers", "accounts", "transactions"]
            }
        }
    }


# ============================================================
# INFO SCHEMAS
# ============================================================

class InfoResponse(BaseModel):
    """
    Response model for API information endpoint
    """
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="API version")
    allowed_tables: List[str] = Field(
        ...,
        description="List of tables that can be queried"
    )
    features: List[str] = Field(
        default=[],
        description="List of supported features"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "app_name": "Banking Data Assistant",
                "version": "1.0.0",
                "allowed_tables": ["customers", "accounts", "transactions"],
                "features": [
                    "Read-only SQL queries",
                    "Strict validation",
                    "SQL injection protection"
                ]
            }
        }
    }
