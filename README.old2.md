# Banking Data Assistant

AI-powered banking data assistant with secure SQL execution. Built with FastAPI, SQLAlchemy, and LangGraph.

## Overview

- AI-powered query processing (natural language to SQL)
- Secure SQL validation and execution
- Multi-agent architecture with LangGraph
- Production-ready backend with FastAPI

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Query (NL/SQL)                  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│            FastAPI Layer (backend/main.py)              │
│     - HTTP endpoints (/query, /health, /info)          │
│     - Request/Response handling                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│         AI Engine (ai_engine/) - LangGraph              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Intent Agent → SQL Agent → Validation Agent    │   │
│  │        ↓            ↓              ↓            │   │
│  │   Understand → Generate SQL → Verify Safety    │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│      Validation Layer (backend/validation.py)           │
│     - SQL syntax validation                             │
│     - Injection pattern detection                       │
│     - Table authorization                               │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│      Execution Layer (backend/execution.py)             │
│     - Safe query execution                              │
│     - Result serialization                              │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│       Database Layer (backend/db.py)                    │
│     - SQLAlchemy engine                                 │
│     - Connection management                             │
└─────────────────────────────────────────────────────────┘
```

**Components:**
- **Backend**: FastAPI REST API with SQL validation
- **AI Engine**: LangGraph multi-agent system (Intent, SQL, Validation, Insight agents)
- **Database**: SQLite/PostgreSQL with banking schema

## Project Structure

```
banking-data-assistance/
├── backend/          # FastAPI REST API
├── ai_engine/        # LangGraph AI agents
├── models/           # Database schema
├── tests/            # Test suite
└── requirements.txt  # Dependencies
```

## Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   ```

3. **Run server**
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

4. **Access API**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/query` | POST | Execute SQL query |
| `/tables` | GET | List tables |

## Security

- SELECT-only queries
- SQL injection protection
- Table whitelist enforcement
- Query validation and sanitization
- No dangerous keywords (INSERT, UPDATE, DELETE, DROP, etc.)
