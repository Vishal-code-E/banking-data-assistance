# AI Banking Data Assistant - Intelligence Layer

A production-ready multi-agent orchestration system built with LangGraph for converting natural language queries into secure, validated SQL queries.

## Architecture

This is the **Intelligence Layer** - a modular AI agent system that orchestrates query understanding, SQL generation, validation, and insight generation.

### System Components

```
ai_engine/
├── graph.py                 # LangGraph orchestration & workflow
├── state.py                 # Shared state schema (TypedDict)
├── main.py                  # Entry point & examples
│
├── agents/                  # Independent, testable agents
│   ├── intent_agent.py      # Natural language → Structured intent
│   ├── sql_agent.py         # Intent → SQL generation
│   ├── validation_agent.py  # SQL security & correctness
│   └── insight_agent.py     # Results → Human summary + viz
│
├── prompts/                 # Structured LLM prompts
│   ├── intent_prompt.txt
│   ├── sql_prompt.txt
│   ├── validation_prompt.txt
│   └── insight_prompt.txt
│
└── utils/                   # Shared utilities
    ├── schema_loader.py     # Database schema provider
    ├── sql_security.py      # Rule-based SQL validation
    └── logger.py            # Structured logging
```

## Multi-Agent Workflow

```
START
  ↓
[Intent Agent] - Extracts structured intent from user query
  ↓
[SQL Generator Agent] - Converts intent + schema → SQL
  ↓
[Validation Agent] - Security & correctness checks
  ↓
[Conditional Router]
  ├─→ Retry (if error & retry_count < 2) → SQL Generator
  ├─→ Execute (if valid) → Database Execution Tool
  └─→ Fail (if max retries) → END
  ↓
[Insight Agent] - Generate summary + chart suggestion
  ↓
END
```

## Key Features

### 🔒 Defense-in-Depth Security
- Rule-based SQL validation (primary)
- LLM-based semantic validation (secondary)
- Only SELECT queries allowed
- Schema-aware table/column validation

### 🔄 Intelligent Retry Logic
- Automatic retry on validation failure
- Max 2 retries with error feedback
- State-preserved retry context

### 📊 Business Intelligence
- Automatic insight generation
- Visualization recommendations (bar/line/pie/table/metric)
- Human-readable summaries

### 🏗️ Production-Ready Design
- Modular, testable agents
- Structured logging
- Type-safe state management
- Extensible architecture

## Usage

### Basic Invocation

```python
from ai_engine.main import run_banking_assistant

# Execute a natural language query
result = run_banking_assistant("Show last 5 transactions above 10000")

print(result)
# {
#   "validated_sql": "SELECT * FROM transactions WHERE amount > 10000 ORDER BY transaction_date DESC LIMIT 5",
#   "summary": "Retrieved high-value transactions exceeding the threshold amount",
#   "chart_suggestion": "table",
#   "error": None
# }
```

### Run Examples

```bash
cd /Users/vishale/banking-data-assistance
python -m ai_engine.main
```

## State Schema

```python
BankingAssistantState = {
    "user_query": str,              # Input: User's natural language query
    "interpreted_intent": str,       # Intent Agent output
    "generated_sql": str,            # SQL Agent output
    "validated_sql": str,            # Validation Agent output
    "execution_result": dict,        # Execution Tool output
    "retry_count": int,              # Control: Retry attempts (max 2)
    "error_message": str,            # Control: Validation errors
    "summary": str,                  # Insight Agent output
    "chart_suggestion": str          # Insight Agent output
}
```

## Output Contract

Every execution returns:

```json
{
  "validated_sql": "SELECT ...",
  "summary": "Human-readable description",
  "chart_suggestion": "bar|line|pie|table|metric",
  "error": null | "error message"
}
```

## Security Model

### Validation Layers

1. **Rule-Based Security** (`sql_security.py`)
   - SELECT-only enforcement
   - Forbidden keyword detection (DROP, DELETE, UPDATE, etc.)
   - SQL injection pattern blocking

2. **Schema Validation**
   - Table existence verification
   - Column existence verification
   - Foreign key awareness

3. **LLM Semantic Validation** (optional)
   - Contextual query validation
   - Intent-SQL alignment check

## Extensibility

Designed for easy agent addition:

```python
# Future agents can be added to the graph:
# - FraudDetectionAgent
# - ForecastAgent
# - MemoryAgent (for conversation context)
# - ComplianceAgent

workflow.add_node("fraud_agent", fraud_detection_agent)
workflow.add_edge("insight_agent", "fraud_agent")
```

## Database Schema

Current schema includes:
- **customers** - Customer information
- **accounts** - Bank account details
- **transactions** - Transaction history

Schema is loaded from `utils/schema_loader.py` and can be easily extended.

## Logging

All operations are logged with structured JSON:

```json
{
  "event": "agent_execution",
  "timestamp": "2026-02-21T...",
  "agent": "ValidationAgent",
  "input": {...},
  "output": {...}
}
```

## Testing

Each agent is independently testable:

```python
from ai_engine.agents.intent_agent import intent_agent
from ai_engine.state import create_initial_state

state = create_initial_state("Show recent transactions")
result = intent_agent(state)
assert result["interpreted_intent"] is not None
```

## Tech Stack

- **Python 3.11+**
- **LangGraph** - Multi-agent orchestration
- **LangChain** - LLM abstractions
- **TypedDict** - Type-safe state management

## LLM Integration

Current implementation uses **abstracted LLM calls** with simulation mode for demonstration.

To integrate with OpenAI:

```python
from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
response = llm.invoke(formatted_prompt)
```

## Production Deployment

For production use:

1. Replace simulated LLM calls with actual API calls
2. Replace `execution_tool_node` with real database connector
3. Add authentication & authorization layers
4. Implement rate limiting
5. Add comprehensive error handling
6. Deploy logging to centralized system (e.g., CloudWatch, Datadog)

## License

Proprietary - Banking Data Assistance System

---

**Built with modular architecture principles**
**No UI code - Pure intelligence layer**
**Production-structured, not hacked together**
