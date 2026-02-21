# Banking Data Assistant - Full Stack AI System

A production-grade, AI-powered banking data assistant that combines natural language processing with secure SQL execution. Built with FastAPI, SQLAlchemy, and LangGraph for enterprise-level security and intelligent query processing.

---

## 🎯 **Overview**

This system provides:
- **🤖 AI-Powered Query Processing** - Natural language to SQL using LangGraph multi-agent architecture
- **🔒 Strict Security** - SELECT-only queries with SQL injection protection
- **🏗️ Modular Architecture** - Separate backend and AI engine layers
- **✅ Intelligent Validation** - Multi-layer validation with intent detection
- **📊 Production Ready** - Complete error handling, logging, and monitoring

**Complete Integration**: Backend core (FastAPI + SQLAlchemy) + AI Engine (LangGraph + LangChain)

---

## 🏗️ **Architecture**

### **High-Level System Architecture**

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

---

## 📁 **Project Structure**

```
banking-data-assistance/
│
├── backend/                  # FastAPI Backend Core
│   ├── main.py              # FastAPI application & endpoints
│   ├── config.py            # Configuration & settings
│   ├── db.py                # Database layer (SQLAlchemy)
│   ├── validation.py        # SQL validation logic
│   ├── execution.py         # Query execution engine
│   └── schemas.py           # Pydantic models
│
├── ai_engine/               # LangGraph AI Engine
│   ├── main.py             # AI engine entry point
│   ├── graph.py            # LangGraph workflow definition
│   ├── state.py            # State management
│   ├── agents/             # Multi-agent system
│   │   ├── intent_agent.py      # Intent classification
│   │   ├── sql_agent.py         # SQL generation
│   │   ├── validation_agent.py  # Safety validation
│   │   └── insight_agent.py     # Result interpretation
│   ├── prompts/            # Agent prompts
│   ├── utils/              # Utilities
│   │   ├── logger.py           # Logging
│   │   ├── schema_loader.py    # Schema management
│   │   └── sql_security.py     # Security checks
│   └── test_security.py    # Security tests
│
├── models/
│   └── schema.sql          # Database schema + seed data
│
├── frontend/               # Frontend (future)
├── tests/                  # Tests
├── requirements.txt        # Unified dependencies
├── .env.example           # Environment template
└── README.md              # This file
```

---

## 🔧 **Technology Stack**

| Component | Technology |
|-----------|-----------|
| **Web Framework** | FastAPI 0.109+ |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **ORM** | SQLAlchemy 2.0+ |
| **Validation** | Custom validation layer |
| **Configuration** | python-dotenv, pydantic-settings |
| **Server** | Uvicorn |

---

## 🚀 **Setup Instructions**

### **1. Prerequisites**

- Python 3.10 or higher
- pip (Python package manager)

### **2. Clone and Navigate**

```bash
cd banking-data-assistance
```

### **3. Create Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### **4. Install Dependencies**

```bash
pip install -r requirements.txt
```

### **5. Configure Environment**

```bash
cp .env.example .env
```

Edit `.env` if needed (defaults work for development).

### **6. Initialize Database**

The database is automatically initialized on first startup. To manually initialize:

```bash
python -c "from backend.db import init_database; init_database()"
```

### **7. Run the Application**

```bash
# Option 1: Using uvicorn directly
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Using Python
cd backend
python main.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📊 **Database Schema**

### **Tables**

#### **customers**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Customer name |
| email | TEXT | Customer email (unique) |
| created_at | DATETIME | Record creation timestamp |

#### **accounts**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| customer_id | INTEGER | Foreign key → customers.id |
| account_number | TEXT | Account number (unique) |
| balance | DECIMAL(15,2) | Account balance |
| created_at | DATETIME | Record creation timestamp |

#### **transactions**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| account_id | INTEGER | Foreign key → accounts.id |
| type | TEXT | 'credit' or 'debit' |
| amount | DECIMAL(15,2) | Transaction amount |
| created_at | DATETIME | Record creation timestamp |

---

## 🔌 **API Endpoints**

### **Health & Info**

#### `GET /`
Root endpoint with API information.

#### `GET /health`
Database health check.

**Response:**
```json
{
  "status": "healthy",
  "database": "sqlite",
  "tables": ["customers", "accounts", "transactions"]
}
```

#### `GET /info`
API capabilities and configuration.

#### `GET /tables`
List all available tables with descriptions.

---

### **Query Execution**

#### `POST /query`
Execute a SQL query.

**Request:**
```json
{
  "sql": "SELECT * FROM customers LIMIT 5"
}
```

**Success Response:**
```json
{
  "success": true,
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
```

**Error Response:**
```json
{
  "success": false,
  "error": "Validation error: Only SELECT statements are allowed",
  "row_count": 0
}
```

---

## 🛡️ **Security Features**

### **Multi-Layer Validation**

1. **Statement Type Check**: Only SELECT queries allowed
2. **Keyword Blocking**: Blocks INSERT, UPDATE, DELETE, DROP, ALTER, etc.
3. **Comment Blocking**: SQL comments (-- and /* */) are forbidden
4. **Multi-Statement Prevention**: Only single queries allowed
5. **Table Whitelist**: Only authorized tables can be accessed
6. **Injection Pattern Detection**: Blocks common SQL injection patterns
7. **Query Length Limits**: Maximum 5000 characters

### **Safe Execution**

- Uses SQLAlchemy `text()` for safe parameter handling
- Read-only database mode
- No raw string interpolation
- Result row limits (configurable, default: 1000 rows)

### **Error Handling**

- Never exposes internal errors to clients
- Proper logging for debugging
- Graceful degradation
- No server crashes on bad queries

---

## 📝 **Example Queries**

### **Get all customers**
```sql
SELECT * FROM customers
```

### **Get customer with accounts**
```sql
SELECT c.name, c.email, a.account_number, a.balance 
FROM customers c 
JOIN accounts a ON c.id = a.customer_id 
WHERE c.id = 1
```

### **Get transaction summary by account**
```sql
SELECT 
  a.account_number,
  COUNT(t.id) as transaction_count,
  SUM(CASE WHEN t.type = 'credit' THEN t.amount ELSE 0 END) as total_credits,
  SUM(CASE WHEN t.type = 'debit' THEN t.amount ELSE 0 END) as total_debits
FROM accounts a
LEFT JOIN transactions t ON a.id = t.account_id
GROUP BY a.account_number
```

### **Get recent transactions**
```sql
SELECT 
  t.id,
  a.account_number,
  t.type,
  t.amount,
  t.created_at
FROM transactions t
JOIN accounts a ON t.account_id = a.id
ORDER BY t.created_at DESC
LIMIT 10
```

---

## ⚙️ **Configuration**

Configuration is managed through environment variables (`.env` file):

```bash
# Application
DEBUG=False
APP_NAME=Banking Data Assistant
APP_VERSION=1.0.0

# Database
DATABASE_URL=sqlite:///banking.db

# Query Settings
QUERY_TIMEOUT=30
MAX_RESULT_ROWS=1000

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## 🧪 **Testing**

Run the test suite:

```bash
pytest tests/ -v
```

Test coverage:

```bash
pytest tests/ --cov=backend --cov-report=html
```

---

## 📦 **Production Deployment**

### **PostgreSQL Migration**

Update `.env`:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/banking_db
```

### **Docker Deployment** (Future)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Environment Variables for Production**

```bash
DEBUG=False
DATABASE_URL=postgresql://user:password@production-db:5432/banking_db
QUERY_TIMEOUT=30
MAX_RESULT_ROWS=1000
```

---

## 🔮 **Future Enhancements**

### **Phase 2: AI Integration (LangGraph)**
- Natural language to SQL conversion
- Multi-agent query planning
- Query optimization suggestions

### **Phase 3: Advanced Features**
- Query caching (Redis)
- Rate limiting
- Query history and analytics
- User authentication & authorization
- Query templates
- Batch query execution

---

## 🐛 **Troubleshooting**

### **Database not initializing**
```bash
# Manually initialize
python -c "from backend.db import init_database; init_database()"
```

### **Import errors**
Make sure you're in the project root and virtual environment is activated:
```bash
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### **Port already in use**
Change the port in the run command:
```bash
uvicorn backend.main:app --port 8001
```

---

## 📚 **API Documentation**

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 👥 **Contributing**

This is a production-grade project. Follow these guidelines:

1. **Code Style**: Follow PEP 8
2. **Type Hints**: Use type hints for all functions
3. **Documentation**: Document all public functions
4. **Testing**: Write tests for new features
5. **Security**: Never bypass validation layers

---

## 📄 **License**

MIT License

---

## 📞 **Support**

For issues or questions:
- Check the API documentation at `/docs`
- Review logs for error details
- Check database health at `/health`

---

**Built with enterprise-grade engineering practices. Ready for AI agent integration.** 🚀
