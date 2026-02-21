"""
Pydantic schemas for Banking Data Assistant API
Defines request and response models for type safety and validation
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator


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
        example="SELECT * FROM customers LIMIT 10"
    )
    
    @validator('sql')
    def validate_sql_not_empty(cls, v):
        """Ensure SQL is not just whitespace"""
        if not v or not v.strip():
            raise ValueError("SQL query cannot be empty or whitespace only")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "sql": "SELECT * FROM customers WHERE id = 1"
            }
        }


# ============================================================
# RESPONSE SCHEMAS
# ============================================================

class QueryResponse(BaseModel):
    """
    Response model for successful query execution
    """
    success: bool = Field(
        default=True,
        description="Indicates if query executed successfully"
    )
    data: List[Dict[str, Any]] = Field(
        default=[],
        description="Query result rows as array of objects"
    )
    row_count: int = Field(
        default=0,
        description="Number of rows returned"
    )
    execution_time_ms: Optional[float] = Field(
        default=None,
        description="Query execution time in milliseconds"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "id": 1,
                        "name": "John Doe",
                        "email": "john.doe@email.com",
                        "created_at": "2024-01-01T00:00:00"
                    }
                ],
                "row_count": 1,
                "execution_time_ms": 15.32
            }
        }


class ErrorResponse(BaseModel):
    """
    Response model for errors
    """
    success: bool = Field(
        default=False,
        description="Indicates if query failed"
    )
    error: str = Field(
        ...,
        description="Error message describing what went wrong"
    )
    row_count: int = Field(
        default=0,
        description="Number of rows returned (always 0 for errors)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Validation error: Only SELECT statements are allowed",
                "row_count": 0
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
    database: str = Field(
        ...,
        description="Database type"
    )
    tables: List[str] = Field(
        default=[],
        description="List of available tables"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "database": "sqlite",
                "tables": ["customers", "accounts", "transactions"]
            }
        }


# ============================================================
# INFO SCHEMAS
# ============================================================

class TableInfo(BaseModel):
    """
    Information about a database table
    """
    name: str = Field(..., description="Table name")
    description: str = Field(..., description="Table description")


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
    
    class Config:
        json_schema_extra = {
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
