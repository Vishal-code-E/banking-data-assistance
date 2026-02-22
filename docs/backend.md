# Backend — FastAPI Application

This document covers the backend API layer built with FastAPI, including all endpoints, request/response contracts, database integration, validation pipeline, execution layer, and configuration.

---

## Table of Contents

1. [Application Structure](#application-structure)
2. [Configuration](#configuration)
3. [Database Layer](#database-layer)
4. [API Endpoints](#api-endpoints)
5. [Request and Response Schemas](#request-and-response-schemas)
6. [SQL Validation Pipeline](#sql-validation-pipeline)
7. [Query Execution Layer](#query-execution-layer)
8. [AI Engine Integration](#ai-engine-integration)
9. [CORS and Middleware](#cors-and-middleware)
10. [Error Handling](#error-handling)
11. [Logging](#logging)
12. [Environment Variables](#environment-variables)

---

## Application Structure

```
backend/
├── main.py           # FastAPI app, lifespan, all route handlers
├── config.py         # pydantic-settings configuration
├── db.py             # SQLAlchemy engine, table definitions, init
├── execution.py      # Query execution with serialization
├── validation.py     # 9-step SQL validation pipeline
├── schemas.py        # Pydantic request/response models
└── __init__.py
```

The application is started with:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

---

## Configuration

**File:** `backend/config.py`

Configuration is managed through `pydantic-settings` and loaded from environment variables (with `.env` file fallback). The `Settings` class follows the 12-factor app pattern.

| Setting | Default | Description |
|---|---|---|
| `APP_NAME` | `"Banking Data Assistant"` | Application display name |
| `APP_VERSION` | `"1.0.0"` | Semantic version |
| `DEBUG` | `False` | Enables verbose logging, Swagger docs, SQLAlchemy echo |
| `DATABASE_URL` | `sqlite:///banking_10k.db` | SQLAlchemy connection string |
| `DB_POOL_SIZE` | `5` | Connection pool size (PostgreSQL only) |
| `DB_MAX_OVERFLOW` | `10` | Max connections beyond pool size |
| `DB_POOL_TIMEOUT` | `30` | Seconds to wait for pool connection |
| `QUERY_TIMEOUT` | `30` | Max query execution time in seconds |
| `MAX_RESULT_ROWS` | `1000` | Hard ceiling on returned rows |
| `ALLOWED_TABLES` | `["customers", "accounts", "transactions"]` | Table access whitelist |
| `CORS_ORIGINS` | Production + localhost origins | Comma-separated allowed origins |
| `PORT` | `8000` | HTTP listen port (Render injects this) |

`cors_origins_list` is a computed property that splits `CORS_ORIGINS` into a list.

When `DEBUG` is `False`:
- Swagger (`/docs`) and ReDoc (`/redoc`) are disabled.
- SQLAlchemy echo is off.
- Log level is `INFO`.

---

## Database Layer

**File:** `backend/db.py`

### Engine creation

`create_db_engine()` supports two database backends:

| Backend | Used when | Configuration |
|---|---|---|
| **SQLite** | `DATABASE_URL` starts with `sqlite` | `StaticPool`, `check_same_thread=False`, `PRAGMA foreign_keys=ON` |
| **PostgreSQL** | `DATABASE_URL` starts with `postgres` or `postgresql` | Connection pooling, `pool_pre_ping=True`, `pool_recycle=300` |

Render provides `DATABASE_URL` with the `postgres://` scheme. SQLAlchemy 2.x requires `postgresql://`. The `_fix_render_postgres_url()` function handles this transparently.

### Table definitions

Three tables are defined using SQLAlchemy `Table` objects for metadata reflection:

- **customers** — `id`, `name`, `email`, `created_at`
- **accounts** — `id`, `customer_id` (FK → customers), `account_number`, `balance`, `created_at`
- **transactions** — `id`, `account_id` (FK → accounts), `type`, `amount`, `created_at`

### Database initialization

`init_database()` reads the appropriate schema file based on the database backend:
- `models/schema.sql` for SQLite
- `models/schema_postgres.sql` for PostgreSQL

Statements are split on `;` and executed individually. SQLite `PRAGMA` statements are skipped when running against PostgreSQL.

### Health check

`check_database_health()` executes `SELECT 1`, reflects table names, and returns a status dictionary used by the `/health` endpoint.

### Session management

- `SessionLocal` — SQLAlchemy `sessionmaker` bound to the global engine.
- `get_db_session()` — Context manager for safe session lifecycle.
- `get_db()` — FastAPI dependency (generator pattern).

---

## API Endpoints

### `GET /`

Returns basic API information (name, version, links to docs and health).

### `GET /health`

Returns database connection status, list of available tables, and `ai_ready` flag (whether `OPENAI_API_KEY` is set).

```json
{
  "status": "healthy",
  "database": "sqlite",
  "tables": ["customers", "accounts", "transactions"],
  "ai_ready": true
}
```

### `GET /info`

Returns application metadata and feature list. Response model: `InfoResponse`.

### `GET /tables`

Returns all available tables with descriptions and column lists. Hardcoded to match the schema.

### `POST /query`

Executes a raw SQL query submitted by the user.

**Request body:**
```json
{ "sql": "SELECT * FROM customers LIMIT 10" }
```

**Pipeline:**
1. Validates SQL through the 9-step validation pipeline (`backend/validation.py`).
2. Executes the query against the database via `execute_query()`.
3. Serializes results (handles `datetime`, `Decimal`, `bytes`).
4. Generates a basic summary and chart suggestion via `_suggest_chart()`.
5. Returns `QueryResponse`.

### `POST /ask`

Accepts a natural-language question and routes it through the LangGraph AI engine.

**Request body:**
```json
{ "query": "What is the total balance across all accounts?" }
```

**Pipeline:**
1. Calls `run_banking_assistant(query, verbose=False)` in a thread pool via `asyncio.to_thread()` to avoid blocking the event loop.
2. Normalizes the execution result: renames `rows` → `data`, converts `execution_time_seconds` → `execution_time_ms`.
3. Returns `QueryResponse`.

### `GET /debug/config` (DEBUG mode only)

Returns current configuration with database credentials masked.

---

## Request and Response Schemas

**File:** `backend/schemas.py`

All schemas use Pydantic v2 with `Field` descriptors and `field_validator` decorators.

### `QueryRequest`

| Field | Type | Constraints |
|---|---|---|
| `sql` | `str` | 1–5000 chars, stripped of whitespace |

### `AskRequest`

| Field | Type | Constraints |
|---|---|---|
| `query` | `str` | 1–2000 chars, stripped of whitespace |

### `QueryResponse` (unified contract)

Both `/query` and `/ask` return this same structure:

| Field | Type | Description |
|---|---|---|
| `validated_sql` | `Optional[str]` | The SQL that was executed, `null` on error |
| `execution_result` | `Optional[dict]` | Contains `data` (list of row dicts), `row_count`, `execution_time_ms` |
| `summary` | `Optional[str]` | Human-readable description of results |
| `chart_suggestion` | `Optional[str]` | Recommended visualization type |
| `error` | `Optional[str]` | Error message, `null` on success |

On success, `error` is `null`. On failure, all other fields are `null` and `error` contains the reason.

### `HealthResponse`

| Field | Type |
|---|---|
| `status` | `str` |
| `database` | `Optional[str]` |
| `tables` | `List[str]` |
| `error` | `Optional[str]` |

### `InfoResponse`

| Field | Type |
|---|---|
| `app_name` | `str` |
| `version` | `str` |
| `allowed_tables` | `List[str]` |
| `features` | `List[str]` |

---

## SQL Validation Pipeline

**File:** `backend/validation.py`

The backend implements its own validation layer independent of the AI engine's `sql_security.py`. This provides defense-in-depth: even if the AI engine is bypassed (e.g., via direct `/query` calls), all SQL is validated.

### Validation order

| Step | Check | Blocks |
|---|---|---|
| 1 | `clean_sql()` | Normalizes whitespace |
| 2 | `check_query_length()` | Queries > 5000 chars |
| 3 | `check_for_comments()` | `--` and `/* */` |
| 4 | `check_for_multiple_statements()` | Semicolon-separated stacked queries |
| 5 | `check_statement_type()` | Anything not starting with `SELECT` |
| 6 | `check_for_dangerous_keywords()` | 14 keywords: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `TRUNCATE`, `REPLACE`, `MERGE`, `GRANT`, `REVOKE`, `EXEC`, `EXECUTE`, `CALL`, `PRAGMA` |
| 7 | `check_for_injection_patterns()` | 10 regex patterns including `UNION SELECT`, hex injection, `xp_`/`sp_` procedures |
| 8 | `check_table_authorization()` | Tables not in `ALLOWED_TABLES` |

Each check returns a `ValidationResult(is_valid, error, cleaned_sql)`. The pipeline short-circuits on the first failure.

---

## Query Execution Layer

**File:** `backend/execution.py`

### `QueryResult` class

Container for execution output:

| Attribute | Type | Description |
|---|---|---|
| `success` | `bool` | Whether execution succeeded |
| `data` | `List[Dict]` | Serialized row dictionaries |
| `error` | `Optional[str]` | Error message on failure |
| `row_count` | `int` | Number of rows returned |
| `execution_time_ms` | `Optional[float]` | Wall-clock execution time |
| `cleaned_sql` | `Optional[str]` | Validated SQL that was executed |

### Serialization

`serialize_value()` converts database types to JSON-safe Python types:

| Database type | Python output |
|---|---|
| `datetime` | ISO 8601 string |
| `date` | ISO 8601 string |
| `Decimal` | `float` |
| `bytes` | UTF-8 decoded string |
| `None` | `None` |

### Execution flow

1. Runs `validate_sql()` — returns error if invalid.
2. Opens a connection via `engine.connect()`.
3. Executes via `sqlalchemy.text()`.
4. Fetches all rows and extracts column names via `result.keys()`.
5. Truncates to `MAX_RESULT_ROWS` (1000) if exceeded.
6. Serializes each row into a `{column: value}` dictionary.
7. Returns `QueryResult`.

### Error hierarchy

| Exception | Handling |
|---|---|
| `OperationalError` | Connection/timeout issues |
| `DatabaseError` | Syntax errors, constraint violations |
| `SQLAlchemyError` | Generic ORM errors |
| `Exception` | Catch-all, logs stack trace |

All exceptions are caught and returned as `QueryResult(success=False, error=...)`. The API layer never exposes raw tracebacks.

### Additional capabilities (not exposed via API)

- `execute_query_with_timeout()` — Sets PostgreSQL `statement_timeout` before execution.
- `execute_batch_queries()` — Sequential multi-query execution with stop-on-error.
- `analyze_query()` — Returns `EXPLAIN QUERY PLAN` output for SQLite.

---

## AI Engine Integration

The `/ask` endpoint bridges the backend to the AI engine:

```python
from ai_engine.main import run_banking_assistant
result = await asyncio.to_thread(run_banking_assistant, request.query, False)
```

The AI engine is synchronous (LangGraph's `.invoke()` blocks). `asyncio.to_thread()` offloads it to a thread pool so the FastAPI event loop remains responsive.

**Key normalization step:** The AI engine returns `execution_result.rows` while the frontend expects `execution_result.data`. The `/ask` handler renames this key. It also converts `execution_time_seconds` to `execution_time_ms`.

---

## CORS and Middleware

CORS is configured in `main.py` using FastAPI's `CORSMiddleware`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

Default allowed origins include:
- `https://banking-data-frontend-assistance-1.onrender.com` (production frontend)
- `http://localhost:3000`, `http://localhost:8080`, `http://localhost:8001` (development)
- `http://localhost:5500`, `http://127.0.0.1:5500` (VS Code Live Server)

Only `GET` and `POST` methods are permitted. `PUT`, `DELETE`, and `PATCH` are blocked.

---

## Error Handling

### Global exception handlers

Two exception handlers are registered on the FastAPI app:

1. **`RequestValidationError`** — Catches Pydantic validation failures. Returns HTTP 422 with the unified `QueryResponse` contract (all fields `null` except `error`).

2. **`Exception`** (catch-all) — Catches any unhandled exception. Logs the full traceback. Returns HTTP 500 with `"An internal server error occurred"`. No internal details are leaked.

Both handlers return contract-compliant JSON, so the frontend always receives a parseable response.

### Per-endpoint error handling

Each endpoint wraps its logic in `try/except` and returns a `QueryResponse` with the error field populated. This means even endpoint-level failures produce the expected JSON shape rather than FastAPI's default error format.

---

## Logging

The application uses Python's `logging` module configured at startup:

```python
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Log events include:
- Query received (first 100 chars)
- Validation pass/fail
- Execution time and row count
- Database health check results
- Startup configuration (database URL with credentials masked)

Database credentials are never logged. The connection string is split at `@` and only the host/database portion is emitted.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | No (defaults to SQLite) | SQLAlchemy connection string |
| `OPENAI_API_KEY` | Yes (for AI features) | OpenAI API key |
| `DEBUG` | No | Set to `"true"` for development mode |
| `PORT` | No (default 8000) | Render injects this |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `DB_POOL_SIZE` | No | PostgreSQL connection pool size |
| `DB_MAX_OVERFLOW` | No | PostgreSQL pool overflow |
| `DB_POOL_TIMEOUT` | No | PostgreSQL pool wait timeout |
| `QUERY_TIMEOUT` | No | Max query execution seconds |
| `MAX_RESULT_ROWS` | No | Hard row limit |

The startup lifespan checks for `OPENAI_API_KEY` and logs a warning if it is missing. The `/health` endpoint reports `ai_ready: false` in this case.
