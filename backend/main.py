"""
FastAPI application – Banking Data Assistant backend.
Integrates with the AI Engine (ai_engine.main.process_query) for
natural-language-to-SQL conversion, then executes validated SQL against
the local SQLite database.
"""
import logging
import os
import sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from database import get_connection
from sql_validator import validate_query

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Banking Data Assistant API",
    description="Natural-language interface to banking data via AI Engine + SQLite.",
    version="1.0.0",
)

_ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:8081,http://127.0.0.1:8081"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)


class QueryResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list[list]
    row_count: int
    summary: Optional[str] = None
    chart_suggestion: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def run_query(body: QueryRequest):
    """
    Accept a natural-language query, process it through the AI Engine to
    generate and validate SQL, execute it against the banking database,
    and return structured results with an optional summary and chart hint.
    """
    # 1. Call AI Engine – graceful degradation on failure
    try:
        from ai_engine.main import process_query
        result = process_query(body.query)
    except Exception as exc:
        logger.error("AI engine unavailable: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=502, detail=f"AI engine error: {exc}"
        ) from exc

    # 2. Check for AI engine error
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    # 3. Ensure validated SQL is present
    sql = result.get("validated_sql")
    if not sql:
        raise HTTPException(
            status_code=400, detail="AI engine did not produce a valid SQL query."
        )

    # 4. Validate – read-only guard (defence in depth)
    is_safe, reason = validate_query(sql)
    if not is_safe:
        raise HTTPException(
            status_code=400, detail=f"Unsafe query rejected: {reason}"
        )

    # 5. Execute
    conn = get_connection()
    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=400, detail=f"SQL execution error: {exc}"
        ) from exc

    return QueryResponse(
        sql=sql,
        columns=columns,
        rows=[list(row) for row in rows],
        row_count=len(rows),
        summary=result.get("summary"),
        chart_suggestion=result.get("chart_suggestion"),
    )


@app.get("/schema")
def schema():
    """Return the live database schema (table names and columns)."""
    conn = get_connection()
    tables: dict[str, list[str]] = {}
    for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ):
        table_name = row[0]
        cols = [
            col[1]
            for col in conn.execute(f"PRAGMA table_info({table_name})")
        ]
        tables[table_name] = cols
    return {"tables": tables}
