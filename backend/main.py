"""
FastAPI Application for Banking Data Assistant
Main entry point for the backend API
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.db import init_database, verify_tables_exist, check_database_health
from backend.execution import execute_query, QueryResult
from backend.schemas import (
    QueryRequest,
    QueryResponse,
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
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ============================================================
# EXCEPTION HANDLERS
# ============================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic / request validation errors.
    Returns contract-compliant JSON instead of FastAPI default 422.
    """
    errors = exc.errors()
    msg = "; ".join(e.get("msg", "Validation error") for e in errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "validated_sql": None,
            "execution_result": None,
            "summary": None,
            "chart_suggestion": None,
            "error": f"Request validation error: {msg}"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unexpected errors.
    Ensures server NEVER crashes — always returns safe JSON.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "validated_sql": None,
            "execution_result": None,
            "summary": None,
            "chart_suggestion": None,
            "error": "An internal server error occurred"
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
        return HealthResponse(status="unhealthy", error=str(e))


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
    response_model=QueryResponse,
    tags=["Query"],
    responses={
        200: {
            "description": "Query executed (success or validation error)",
            "model": QueryResponse
        },
        500: {
            "description": "Internal server error",
            "model": QueryResponse
        }
    }
)
async def execute_sql_query(request: QueryRequest):
    """
    Execute a SQL query

    ## Request Body
    - **sql**: SQL SELECT query to execute

    ## Response Contract
    Always returns the standardized JSON:
    ```json
    {
      "validated_sql": "...",
      "execution_result": {...},
      "summary": "...",
      "chart_suggestion": "...",
      "error": null
    }
    ```

    ## Security
    - Only SELECT statements are allowed
    - All queries are validated before execution
    - Only whitelisted tables can be accessed
    - SQL injection patterns are blocked
    """
    try:
        logger.info(f"Received query request: {request.sql[:100]}...")

        # Execute query through execution layer
        result: QueryResult = execute_query(request.sql)

        if result.success:
            # Build execution_result payload
            execution_result = {
                "data": result.data,
                "row_count": result.row_count,
            }
            if result.execution_time_ms is not None:
                execution_result["execution_time_ms"] = round(result.execution_time_ms, 2)

            # Generate a human-readable summary
            summary = f"Query returned {result.row_count} row(s)"

            # Suggest a chart type based on result shape
            chart_suggestion = _suggest_chart(result.data, result.row_count)

            return QueryResponse(
                validated_sql=result.cleaned_sql,
                execution_result=execution_result,
                summary=summary,
                chart_suggestion=chart_suggestion,
                error=None
            )
        else:
            # Validation or execution error — return contract-compliant error
            return QueryResponse(
                validated_sql=None,
                execution_result=None,
                summary=None,
                chart_suggestion=None,
                error=result.error
            )

    except Exception as e:
        logger.error(f"Query execution failed: {e}", exc_info=True)
        return QueryResponse(
            validated_sql=None,
            execution_result=None,
            summary=None,
            chart_suggestion=None,
            error="An unexpected error occurred during query execution"
        )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _suggest_chart(data: list, row_count: int) -> str:
    """Simple heuristic for chart suggestion based on result shape."""
    if row_count == 0:
        return "none"
    if row_count == 1:
        return "card"
    # If only 2 columns (label + value), a bar/pie chart works
    if data and len(data[0]) == 2:
        return "bar" if row_count > 5 else "pie"
    return "table"


# ============================================================
# ADDITIONAL ENDPOINTS
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
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
