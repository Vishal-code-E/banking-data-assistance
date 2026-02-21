"""
FastAPI application – Banking Data Assistant backend.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import sqlite3

from database import get_connection
from sql_generator import natural_language_to_sql
from sql_validator import validate_query

app = FastAPI(
    title="Banking Data Assistant API",
    description="Natural-language interface to banking data via OpenAI + SQLite.",
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
    Accept a natural-language query, generate SQL via OpenAI, validate it,
    execute it against the banking database, and return structured results.
    """
    # 1. Translate to SQL
    try:
        sql = natural_language_to_sql(body.query)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"SQL generation failed: {exc}"
        ) from exc

    # 2. Validate – read-only guard
    is_safe, reason = validate_query(sql)
    if not is_safe:
        raise HTTPException(
            status_code=400, detail=f"Unsafe query rejected: {reason}"
        )

    # 3. Execute
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
