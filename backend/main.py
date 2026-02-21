"""
FastAPI Application for Banking Data Assistant
Main entry point for the backend API
"""

import logging
from contextlib import asynccontextmanager
from typing import Union

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.db import init_database, verify_tables_exist, check_database_health
from backend.execution import execute_query, QueryResult
from backend.schemas import (
    QueryRequest,
    QueryResponse,
    ErrorResponse,
    HealthResponse,
    InfoResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# APPLICATION LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting Banking Data Assistant API...")
    logger.info(f"Environment: {'Development' if settings.DEBUG else 'Production'}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    
    try:
        # Initialize database
        init_database()
        
        # Verify tables exist
        if not verify_tables_exist():
            logger.warning("Some required tables are missing!")
        else:
            logger.info("All required tables verified successfully")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Banking Data Assistant API...")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Banking Data Assistant API - A secure, read-only SQL query interface
    
    ## Features
    * Execute SELECT queries safely
    * Strict SQL validation
    * SQL injection protection
    * Read-only access to banking data
    
    ## Security
    * Only SELECT statements allowed
    * Table access whitelist
    * No dangerous SQL operations
    * Query sanitization and validation
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============================================================
# MIDDLEWARE
# ============================================================

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ============================================================
# EXCEPTION HANDLERS
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unexpected errors
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "An internal server error occurred",
            "row_count": 0
        }
    )


# ============================================================
# API ENDPOINTS
# ============================================================

@app.get("/", tags=["Info"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "message": "Banking Data Assistant API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint
    Returns database connection status and available tables
    """
    try:
        health_status = check_database_health()
        return HealthResponse(**health_status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable"
        )


@app.get("/info", response_model=InfoResponse, tags=["Info"])
async def get_info():
    """
    Get API information and capabilities
    """
    return InfoResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        allowed_tables=settings.ALLOWED_TABLES,
        features=[
            "Read-only SQL queries (SELECT only)",
            "Strict SQL validation",
            "SQL injection protection",
            "Table access whitelist",
            "Query result serialization",
            "Automatic type conversion"
        ]
    )


@app.post(
    "/query",
    response_model=Union[QueryResponse, ErrorResponse],
    tags=["Query"],
    responses={
        200: {
            "description": "Query executed successfully",
            "model": QueryResponse
        },
        400: {
            "description": "Invalid query or validation error",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    }
)
async def execute_sql_query(request: QueryRequest):
    """
    Execute a SQL query
    
    ## Request Body
    - **sql**: SQL SELECT query to execute
    
    ## Security
    - Only SELECT statements are allowed
    - All queries are validated before execution
    - Only whitelisted tables can be accessed
    - SQL injection patterns are blocked
    
    ## Example Queries
    
    Get all customers:
    ```sql
    SELECT * FROM customers
    ```
    
    Get customer with accounts:
    ```sql
    SELECT c.name, a.account_number, a.balance 
    FROM customers c 
    JOIN accounts a ON c.id = a.customer_id 
    WHERE c.id = 1
    ```
    
    Get transaction summary:
    ```sql
    SELECT account_id, type, SUM(amount) as total 
    FROM transactions 
    GROUP BY account_id, type
    ```
    """
    try:
        logger.info(f"Received query request: {request.sql[:100]}...")
        
        # Execute query through execution layer
        result: QueryResult = execute_query(request.sql)
        
        # Return appropriate response
        if result.success:
            return QueryResponse(**result.to_dict())
        else:
            # Return error response with 200 status (business logic error, not HTTP error)
            return ErrorResponse(**result.to_dict())
            
    except Exception as e:
        logger.error(f"Query execution failed: {e}", exc_info=True)
        return ErrorResponse(
            success=False,
            error="An unexpected error occurred during query execution",
            row_count=0
        )


# ============================================================
# ADDITIONAL ENDPOINTS (Future)
# ============================================================

@app.get("/tables", tags=["Info"])
async def list_tables():
    """
    List all available tables with descriptions
    """
    tables = [
        {
            "name": "customers",
            "description": "Customer information including name and email",
            "columns": ["id", "name", "email", "created_at"]
        },
        {
            "name": "accounts",
            "description": "Bank accounts associated with customers",
            "columns": ["id", "customer_id", "account_number", "balance", "created_at"]
        },
        {
            "name": "transactions",
            "description": "All banking transactions (credits and debits)",
            "columns": ["id", "account_id", "type", "amount", "created_at"]
        }
    ]
    
    return {
        "tables": tables,
        "count": len(tables)
    }


# ============================================================
# DEVELOPMENT ENDPOINTS (Debug mode only)
# ============================================================

if settings.DEBUG:
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """
        Debug endpoint to view configuration (DEBUG mode only)
        """
        return {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
            "database_url": settings.DATABASE_URL.split("@")[-1],  # Hide credentials
            "allowed_tables": settings.ALLOWED_TABLES,
            "query_timeout": settings.QUERY_TIMEOUT,
            "max_result_rows": settings.MAX_RESULT_ROWS
        }


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )

