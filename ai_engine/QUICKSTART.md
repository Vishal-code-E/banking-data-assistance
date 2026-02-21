"""
Quick Start Guide for AI Banking Data Assistant
"""

# Installation

1. Navigate to the ai_engine directory:
   cd /Users/vishale/banking-data-assistance

2. Install dependencies:
   pip3 install -r ai_engine/requirements.txt

# Usage Examples

## Example 1: Basic Query
```python
from ai_engine.main import run_banking_assistant

result = run_banking_assistant("Show last 5 transactions above 10000")

print(result)
# Output:
# {
#   "validated_sql": "SELECT * FROM transactions WHERE amount > 10000 ORDER BY transaction_date DESC LIMIT 5",
#   "summary": "Retrieved high-value transactions exceeding the threshold amount",
#   "chart_suggestion": "table",
#   "error": None
# }
```

## Example 2: Aggregation Query
```python
result = run_banking_assistant("How many customers have premium accounts?")

print(result['validated_sql'])
# Output: "SELECT COUNT(*) as customer_count FROM customers WHERE account_type = 'premium'"
```

## Example 3: Run Full Demo
```bash
python3 -m ai_engine.demo
```

# Architecture Overview

## Workflow
1. **Intent Agent** - Understands user query
2. **SQL Agent** - Generates SQL from intent
3. **Validation Agent** - Security & correctness checks
4. **Execution Tool** - Runs validated SQL (simulated)
5. **Insight Agent** - Generates summary & chart recommendation

## Key Features
- Defense-in-depth security validation
- Automatic retry logic (max 2 attempts)
- Structured logging
- Type-safe state management
- Modular, testable architecture

# Security

All SQL queries are validated:
- ✅ Only SELECT allowed
- ✅ No DROP, DELETE, UPDATE, INSERT
- ✅ Schema-aware validation
- ✅ Table/column existence checks

# Extensibility

Add new agents easily:
```python
from ai_engine.graph import workflow

workflow.add_node("fraud_agent", fraud_detection_agent)
workflow.add_edge("insight_agent", "fraud_agent")
```

# Production Deployment

To use with real LLM:
1. Install: `pip install langchain-openai`
2. Replace simulation calls in agents with actual LLM calls
3. Configure API keys
4. Replace execution_tool_node with real DB connector

# File Structure

ai_engine/
├── graph.py              # LangGraph workflow
├── state.py              # State schema
├── main.py               # Entry point
├── demo.py               # Demonstrations
├── agents/               # Agent implementations
│   ├── intent_agent.py
│   ├── sql_agent.py
│   ├── validation_agent.py
│   └── insight_agent.py
├── prompts/              # LLM prompts
├── utils/                # Utilities
│   ├── logger.py
│   ├── sql_security.py
│   └── schema_loader.py
└── requirements.txt

# Support

For issues or questions:
1. Check logs in structured JSON format
2. Review agent execution flow
3. Verify SQL validation results
4. Check retry count and error messages
