# Render Deployment Guide — Banking Data Assistant

## Architecture

```
┌─────────────────────┐     HTTPS     ┌─────────────────────┐
│  bdata-frontend     │ ────────────► │  bdata-backend      │
│  (Render Static)    │    /ask       │  (Render Web Svc)   │
│  vanilla JS + CSS   │    /query     │  FastAPI + AI Engine │
└─────────────────────┘               └────────┬────────────┘
                                               │
                                               │  postgresql://
                                               ▼
                                      ┌─────────────────────┐
                                      │  bdata-db            │
                                      │  (Render PostgreSQL) │
                                      └─────────────────────┘
```

## One-Click Deploy (Blueprint)

1. Push this repo to GitHub.
2. Go to **https://render.com/deploy**.
3. Point it at your repo — Render reads `render.yaml` and provisions:
   - PostgreSQL database (`bdata-db`)
   - Web Service (`bdata-backend`)
   - Static Site (`bdata-frontend`)
4. Set **`OPENAI_API_KEY`** manually in the backend service's Environment tab.
5. Done.

## Manual Deploy Steps

### 1. Create PostgreSQL Database
- Render Dashboard → **New** → **PostgreSQL**
- Name: `bdata-db`
- Copy the **Internal Connection String**.

### 2. Create Backend Web Service
- Render Dashboard → **New** → **Web Service**
- Connect your GitHub repo.
- Settings:
  | Field | Value |
  |---|---|
  | Name | `bdata-backend` |
  | Runtime | Python |
  | Build Command | `pip install -r requirements.txt` |
  | Start Command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
  | Health Check Path | `/health` |
- **Environment Variables**:
  | Variable | Value |
  |---|---|
  | `DATABASE_URL` | Paste the PostgreSQL connection string |
  | `OPENAI_API_KEY` | Your OpenAI key |
  | `CORS_ORIGINS` | `https://bdata-frontend.onrender.com` |
  | `DEBUG` | `False` |

### 3. Create Frontend Static Site
- Render Dashboard → **New** → **Static Site**
- Connect same repo.
- Settings:
  | Field | Value |
  |---|---|
  | Name | `bdata-frontend` |
  | Publish Directory | `./frontend` |
  | Build Command | _(leave empty or `echo done`)_ |

## Files Modified for Production

| File | Change |
|---|---|
| `backend/config.py` | CORS from env var; `PORT` from env var |
| `backend/db.py` | `postgres://` → `postgresql://` auto-fix; `pool_pre_ping`, `pool_recycle`; picks schema file by DB type |
| `backend/main.py` | Port from `settings.PORT`; mask DB credentials in logs; disable docs in production |
| `frontend/js/api.js` | `API_BASE` auto-resolves from hostname (Render convention or localhost fallback) |
| `requirements.txt` | Added `psycopg2-binary`, `langchain-openai`; removed test deps |
| `models/schema_postgres.sql` | New — PostgreSQL-compatible schema + seed data |
| `.env.example` | Updated with all production env vars |
| `render.yaml` | New — Render Blueprint for one-click deploy |
| `ai_engine/agents/*.py` | Removed diagnostic `print()` statements |
| `ai_engine/graph.py` | Removed diagnostic `print()` statements |

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | `sqlite:///banking_10k.db` | PostgreSQL connection string on Render |
| `OPENAI_API_KEY` | Yes | _(none)_ | OpenAI API key for LLM agents |
| `CORS_ORIGINS` | Yes | localhost variants | Frontend URL (comma-separated) |
| `PORT` | Auto | `10000` | Render injects this automatically |
| `DEBUG` | No | `False` | Enables /docs, verbose logging |
| `DB_POOL_SIZE` | No | `5` | SQLAlchemy pool size |
| `DB_MAX_OVERFLOW` | No | `10` | Max overflow connections |
| `QUERY_TIMEOUT` | No | `30` | Max query execution time (seconds) |
| `MAX_RESULT_ROWS` | No | `1000` | Row limit per query |

## Deployment Risks & Notes

1. **Free tier cold starts**: Render free Web Services spin down after 15 min idle. First request takes ~30s.
2. **Free PostgreSQL expiry**: Render free PostgreSQL databases expire after 90 days. Upgrade to a paid plan for persistence.
3. **OpenAI costs**: Each `/ask` call makes 3 LLM requests (intent + SQL + insight). Monitor usage.
4. **No auth**: All endpoints are public. Add API key middleware if needed.
5. **Schema seeding**: The app auto-seeds on first boot via `init_database()`. For fresh PostgreSQL, seed data is included in `models/schema_postgres.sql`.

## Post-Deploy Verification

```bash
# Health check
curl https://bdata-backend.onrender.com/health

# AI query test
curl -X POST https://bdata-backend.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "how many customers are there?"}'
```
