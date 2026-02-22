# Banking Data Assistant

A natural-language interface for querying banking data, powered by a multi-agent AI pipeline built with LangGraph.

Users ask questions in plain English. The system interprets the intent, generates SQL, validates it for safety, executes it against the database, and returns results with summaries and visualizations.

---

## How It Works

```
User: "What is the average account balance?"
  │
  ▼
┌─────────────┐   ┌───────────┐   ┌────────────────┐   ┌───────────┐   ┌──────────────┐
│ Intent Agent│──►│ SQL Agent │──►│ Validation     │──►│ Execution │──►│ Insight Agent│
│ (GPT-4o-mini)│  │(GPT-4o-mini)│ │ (rule-based)   │   │ (database)│   │ (GPT-4o-mini)│
└─────────────┘   └───────────┘   └────────────────┘   └───────────┘   └──────────────┘
  │                                                                         │
  ▼                                                                         ▼
"Calculate average                "SELECT AVG(balance)                "The average account
 balance from                      FROM accounts                      balance is $9,150.10
 accounts table"                   LIMIT 100"                         across 5 accounts."
                                                                      Chart: metric
```

---

## Capabilities

- **Natural language queries** — Ask questions about customers, accounts, and transactions without writing SQL.
- **Direct SQL execution** — Power users can write raw `SELECT` queries via the SQL Editor or chat input.
- **Automatic visualization** — Results are rendered as bar charts, line charts, pie charts, metric cards, or data tables based on data shape.
- **Security-first SQL validation** — Multi-layer defense: LLM prompt constraints, rule-based validation (forbidden keywords, injection pattern detection, table whitelisting), LIMIT enforcement, and backend-level re-validation.
- **Retry logic** — Failed SQL generation is automatically retried up to 2 times with error context fed back to the LLM.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Orchestration | LangGraph, LangChain |
| LLM | OpenAI GPT-4o-mini |
| Backend | FastAPI, Uvicorn |
| Database | SQLAlchemy (SQLite for development, PostgreSQL for production) |
| Frontend | Vanilla JavaScript (ES modules, no build step) |
| Charts | Chart.js 4.4.7 |
| Deployment | Render (Web Service + Static Site) |

---

## Project Structure

```
banking-data-assistance/
├── ai_engine/
│   ├── agents/
│   │   ├── intent_agent.py       # Intent extraction (LLM)
│   │   ├── sql_agent.py          # SQL generation (LLM)
│   │   ├── validation_agent.py   # SQL safety validation (rule-based)
│   │   └── insight_agent.py      # Summary + chart recommendation (LLM)
│   ├── prompts/
│   │   ├── intent_prompt.txt     # Intent extraction prompt
│   │   ├── sql_prompt.txt        # SQL generation prompt
│   │   ├── validation_prompt.txt # Validation prompt (reserved)
│   │   └── insight_prompt.txt    # Insight generation prompt
│   ├── utils/
│   │   ├── schema_loader.py      # Database schema definition
│   │   ├── sql_security.py       # Rule-based SQL security checks
│   │   └── logger.py             # Structured JSON logging
│   ├── graph.py                  # LangGraph workflow definition
│   ├── state.py                  # Shared state schema (TypedDict)
│   └── main.py                   # AI engine entry point
├── backend/
│   ├── main.py                   # FastAPI app, routes, lifespan
│   ├── config.py                 # Environment-based configuration
│   ├── db.py                     # SQLAlchemy engine + initialization
│   ├── execution.py              # Query execution + serialization
│   ├── validation.py             # Backend SQL validation pipeline
│   └── schemas.py                # Pydantic request/response models
├── frontend/
│   ├── index.html                # SPA shell
│   ├── styles.css                # Application styles
│   └── js/
│       ├── app.js                # Router + bootstrap
│       ├── api.js                # HTTP client
│       ├── state.js              # Client-side state
│       └── pages/
│           ├── conversations.js  # Chat UI + chart engine
│           ├── dashboard.js      # Dashboard page
│           ├── sql-editor.js     # SQL editor page
│           ├── history.js        # Query history page
│           └── datasources.js    # Schema explorer page
├── models/
│   ├── schema.sql                # SQLite schema
│   └── schema_postgres.sql       # PostgreSQL schema
├── docs/
│   ├── ai_agents.md              # AI agent architecture docs
│   ├── backend.md                # Backend API docs
│   ├── frontend.md               # Frontend SPA docs
│   └── orchestration.md          # LangGraph workflow docs
├── requirements.txt              # Python dependencies
├── .python-version               # Python 3.12.0
├── .env.example                  # Environment variable template
├── render.yaml                   # Render deployment blueprint
└── DEPLOYMENT.md                 # Deployment guide
```

---

## Database Schema

Three tables representing a simplified banking domain:

| Table | Columns | Description |
|---|---|---|
| `customers` | `id`, `name`, `email`, `created_at` | Customer records |
| `accounts` | `id`, `customer_id`, `account_number`, `balance`, `created_at` | Bank accounts linked to customers |
| `transactions` | `id`, `account_id`, `type` (credit/debit), `amount`, `created_at` | Transaction history |

Foreign keys: `accounts.customer_id` → `customers.id`, `transactions.account_id` → `accounts.id`.

---

## Local Setup

### Prerequisites

- Python 3.12
- An OpenAI API key

### Steps

```bash
# 1. Clone
git clone https://github.com/Vishal-code-E/banking-data-assistance.git
cd banking-data-assistance

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

# 5. Start the backend
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload

# 6. Open the frontend
# Open frontend/index.html in a browser, or use VS Code Live Server on port 5500
```

The backend starts on `http://localhost:8001`. The frontend auto-detects the local backend URL.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API info |
| `GET` | `/health` | Database + AI readiness check |
| `GET` | `/info` | App metadata and feature list |
| `GET` | `/tables` | Available tables with column details |
| `POST` | `/query` | Execute raw SQL (body: `{ "sql": "..." }`) |
| `POST` | `/ask` | Natural-language question → AI pipeline (body: `{ "query": "..." }`) |

Both `/query` and `/ask` return the same response contract:

```json
{
  "validated_sql": "SELECT ...",
  "execution_result": {
    "data": [{ "column": "value" }],
    "row_count": 10,
    "execution_time_ms": 15.32
  },
  "summary": "Human-readable description...",
  "chart_suggestion": "bar",
  "error": null
}
```

---

## Example Query Flow

**Input:** "Show me the top 3 customers by total balance"

1. **Intent Agent** → "Retrieve top 3 customers ranked by total account balance, using SUM aggregate with GROUP BY customer, ordered DESC, limited to 3"
2. **SQL Agent** → `SELECT c.name, SUM(a.balance) AS total_balance FROM accounts a JOIN customers c ON a.customer_id = c.id GROUP BY c.name ORDER BY total_balance DESC LIMIT 3`
3. **Validation Agent** → SELECT-only ✓, no forbidden keywords ✓, tables exist ✓, LIMIT present ✓ → VALID
4. **Execution** → `[{ "name": "Alice", "total_balance": 25000 }, { "name": "Bob", "total_balance": 18500 }, { "name": "Carol", "total_balance": 12000 }]`
5. **Insight Agent** → Summary: "Alice leads with $25,000 in total balance..." Chart: bar
6. **Frontend** → Renders summary text, SQL block, data table, and a bar chart

---

## Security

### SQL safety checks (two independent layers)

**AI Engine layer** (`ai_engine/utils/sql_security.py`):
- SELECT-only enforcement
- Forbidden keyword blocking (16 keywords)
- Multi-statement detection
- UNION blocking
- Schema table validation
- Automatic LIMIT enforcement (default 100, max 1000)

**Backend layer** (`backend/validation.py`):
- All of the above, plus:
- SQL comment blocking (`--`, `/* */`)
- Injection pattern detection (10 regex patterns)
- Table authorization against whitelist
- Query length limit (5000 chars)

### Runtime safeguards

- All queries execute via `sqlalchemy.text()` — no string interpolation
- Query timeout: 30 seconds (thread-based)
- Row limit: 1000 rows maximum
- Database credentials are never logged
- Swagger docs disabled in production

---

## Deployment

The application is deployed on Render:

| Service | Type | URL |
|---|---|---|
| Backend | Web Service | `https://banking-data-assistance.onrender.com` |
| Frontend | Static Site | `https://banking-data-frontend-assistance-1.onrender.com` |

### Required environment variables on Render

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `DATABASE_URL` | PostgreSQL connection string (provided by Render) |

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

---

## Documentation

Detailed technical documentation is available in the `docs/` directory:

| Document | Content |
|---|---|
| [docs/ai_agents.md](docs/ai_agents.md) | Multi-agent architecture, state management, prompt engineering, security layers |
| [docs/backend.md](docs/backend.md) | FastAPI endpoints, validation pipeline, execution layer, configuration |
| [docs/frontend.md](docs/frontend.md) | SPA structure, chat interface, chart intelligence engine, state management |
| [docs/orchestration.md](docs/orchestration.md) | LangGraph workflow, conditional routing, retry logic, data flow |

---

## Limitations

- **Schema is static.** The agent pipeline uses a hardcoded schema definition. Adding tables or columns requires updating `schema_loader.py`, the prompt files, and `config.py`'s `ALLOWED_TABLES`.
- **No authentication.** The API is open. In a production banking context, authentication and authorization would be required.
- **No persistent chat history.** Messages are stored in browser memory and lost on page refresh.
- **Single LLM provider.** The system is coupled to OpenAI's API. Switching providers requires modifying the agent files.
- **Render free tier.** Cold starts can take 30–60 seconds. The frontend has a 120-second timeout to accommodate this.
