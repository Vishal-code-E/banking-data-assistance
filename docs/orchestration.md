# Orchestration — LangGraph Workflow

This document provides a deep technical walkthrough of the LangGraph state-machine workflow that powers the AI engine. It covers the graph construction, node definitions, conditional routing, retry logic, execution model, and data flow.

---

## Table of Contents

1. [Overview](#overview)
2. [Graph Definition](#graph-definition)
3. [Node Inventory](#node-inventory)
4. [Edge Definitions](#edge-definitions)
5. [Conditional Routing Functions](#conditional-routing-functions)
6. [Execution Flow — Full Walkthrough](#execution-flow--full-walkthrough)
7. [Retry Mechanism](#retry-mechanism)
8. [Execution Tool Node](#execution-tool-node)
9. [State Mutation Rules](#state-mutation-rules)
10. [Graph Compilation and Invocation](#graph-compilation-and-invocation)
11. [Entry Points: main.py and /ask](#entry-points-mainpy-and-ask)
12. [Failure Modes](#failure-modes)

---

## Overview

The AI engine uses [LangGraph](https://github.com/langchain-ai/langgraph) to define a directed graph where:

- **Nodes** are agent functions that transform shared state.
- **Edges** define the execution order.
- **Conditional edges** implement branching logic (retry vs. proceed vs. fail).

The graph is compiled once at import time and reused as a singleton for all requests.

---

## Graph Definition

**File:** `ai_engine/graph.py`

```
START
  │
  ▼
intent_agent
  │
  ▼
sql_agent  ◄─────────────────────┐
  │                               │
  ▼                               │
validation_agent                  │
  │                               │
  ├── [VALID] ──► execution_tool  │
  │                  │            │
  │                  ├── [OK] ──► insight_agent ──► END
  │                  │            │
  │                  └── [ERROR, retries left] ──┘
  │                  │
  │                  └── [ERROR, no retries] ──► END
  │
  ├── [INVALID, retries left] ───┘
  │
  └── [INVALID, no retries] ──► END
```

---

## Node Inventory

| Node name | Function | Source file | Uses LLM | Purpose |
|---|---|---|---|---|
| `intent_agent` | `intent_agent()` | `agents/intent_agent.py` | Yes | Extract structured intent from natural language |
| `sql_agent` | `sql_agent()` | `agents/sql_agent.py` | Yes | Generate SQL from intent + schema |
| `validation_agent` | `validation_agent()` | `agents/validation_agent.py` | No | Validate SQL safety and correctness |
| `execution_tool` | `execution_tool_node()` | `graph.py` | No | Execute SQL against the database |
| `insight_agent` | `insight_agent()` | `agents/insight_agent.py` | Yes | Generate summary and chart recommendation |

All nodes accept `BankingAssistantState` and return a `Dict[str, Any]` containing only the fields they modify. LangGraph merges these partial updates into the shared state.

---

## Edge Definitions

### Linear edges

```python
workflow.set_entry_point("intent_agent")
workflow.add_edge("intent_agent", "sql_agent")
workflow.add_edge("sql_agent", "validation_agent")
workflow.add_edge("insight_agent", END)
```

These are unconditional: Intent always flows to SQL, SQL always flows to Validation, and Insight always terminates the graph.

### Conditional edges

Two conditional routing points handle the retry logic:

```python
workflow.add_conditional_edges(
    "validation_agent",
    should_retry,
    {
        "sql_agent": "sql_agent",
        "execution_tool": "execution_tool",
        "end_failure": END
    }
)

workflow.add_conditional_edges(
    "execution_tool",
    should_retry_after_execution,
    {
        "sql_agent": "sql_agent",
        "insight_agent": "insight_agent",
        "end_failure": END
    }
)
```

---

## Conditional Routing Functions

### `should_retry(state)` — After validation

| Condition | Return value | Next node |
|---|---|---|
| `validated_sql` exists and no `error_message` | `"execution_tool"` | Proceed to execution |
| `error_message` set and `retry_count < MAX_RETRY_COUNT` | `"sql_agent"` | Retry SQL generation |
| `retry_count >= MAX_RETRY_COUNT` | `"end_failure"` | Terminate with error |
| Unclear state | `"execution_tool"` | Default to execution |

### `should_retry_after_execution(state)` — After execution

| Condition | Return value | Next node |
|---|---|---|
| No `error_message` and no execution error | `"insight_agent"` | Proceed to insights |
| Execution error and `retry_count < MAX_RETRY_COUNT` | `"sql_agent"` | Retry SQL generation |
| `retry_count >= MAX_RETRY_COUNT` | `"end_failure"` | Terminate with error |

Both functions use `Literal` type hints to declare their possible return values, which LangGraph uses for graph validation at compile time.

---

## Execution Flow — Full Walkthrough

### Successful query (no retries)

```
1. START
   State: { user_query: "How many customers?", retry_count: 0, everything else: None }

2. intent_agent
   ├─ Reads: user_query
   ├─ Calls: GPT-4o-mini with intent_prompt.txt
   └─ Writes: { interpreted_intent: "Count all rows in customers table" }

3. sql_agent
   ├─ Reads: interpreted_intent, error_message (None)
   ├─ Calls: GPT-4o-mini with sql_prompt.txt + schema
   └─ Writes: { generated_sql: "SELECT COUNT(*) FROM customers" }

4. validation_agent
   ├─ Reads: generated_sql
   ├─ Runs: is_select_only ✓, no_multiple_statements ✓, no_union ✓,
   │         no_forbidden_keywords ✓, validate_schema_tables ✓
   ├─ Runs: enforce_limit → "SELECT COUNT(*) FROM customers LIMIT 100"
   └─ Writes: { validated_sql: "SELECT COUNT(*) FROM customers LIMIT 100",
   │            error_message: None }

5. should_retry → "execution_tool" (validated_sql is set, no error)

6. execution_tool
   ├─ Reads: validated_sql
   ├─ Executes: SQL against database via SQLAlchemy
   ├─ Times out after: 30 seconds (thread-based timeout)
   └─ Writes: { execution_result: { rows: [{"COUNT(*)": 42}],
   │            row_count: 1, execution_time_seconds: 0.003 } }

7. should_retry_after_execution → "insight_agent" (no error)

8. insight_agent
   ├─ Reads: validated_sql, execution_result
   ├─ Calls: GPT-4o-mini with insight_prompt.txt
   ├─ Parses: "SUMMARY: There are 42 customers...\nCHART: metric"
   └─ Writes: { summary: "There are 42 customers...",
   │            chart_suggestion: "metric" }

9. END
```

### Failed validation with retry

```
1-3. (same as above, but SQL Agent generates invalid SQL)

4. validation_agent
   └─ Writes: { validated_sql: None,
   │            error_message: "Table 'users' not found in schema",
   │            retry_count: 1 }

5. should_retry → "sql_agent" (error exists, retry_count=1 < MAX=2)

6. sql_agent (retry)
   ├─ Reads: interpreted_intent, error_message="Table 'users' not found..."
   ├─ Calls: GPT-4o-mini with error context injected into prompt
   └─ Writes: { generated_sql: "SELECT COUNT(*) FROM customers" }

7. validation_agent (second attempt)
   └─ Writes: { validated_sql: "SELECT COUNT(*) FROM customers LIMIT 100",
   │            error_message: None }

8. should_retry → "execution_tool" (success)
   ... continues to execution and insight ...
```

### Exhausted retries

```
4. validation_agent
   └─ Writes: { retry_count: 2, error_message: "..." }

5. should_retry → "sql_agent" (retry_count=2 < MAX=2? No, 2 ≥ 2)
   Correction: MAX_RETRY_COUNT = 2, condition is retry_count < MAX_RETRY_COUNT
   So retry_count=2 is NOT less than 2 → "end_failure"

6. END (graph terminates, final state has error_message set)
```

---

## Retry Mechanism

### Constants

```python
MAX_RETRY_COUNT = 2  # Defined in ai_engine/state.py
```

### Retry budget

The system allows up to 2 retries after the initial attempt, meaning a query can go through the SQL → Validation → SQL loop at most 2 additional times. Including the first attempt, the SQL Agent runs at most **3 times** for a single user query.

### Retry sources

| Source | When | State changes |
|---|---|---|
| Validation failure | SQL fails safety checks | `retry_count += 1`, `error_message` set, `validated_sql = None` |
| Execution failure | Database returns error | `retry_count += 1`, `error_message` set, `validated_sql = None` |

Both sources feed back into `sql_agent`, which receives the `error_message` as context to improve the next SQL generation attempt.

### Logging

Each retry is logged via `logger.log_retry(retry_count, error_message)` with `WARNING` severity.

---

## Execution Tool Node

**File:** `ai_engine/graph.py` — `execution_tool_node()`

This node is not an LLM agent. It executes validated SQL against the real database.

### Implementation details

```python
QUERY_TIMEOUT_SECONDS = 30
MAX_ROWS = 1000
```

The function uses a **threaded timeout** instead of `signal.alarm()` because LangGraph may run nodes in non-main threads where signal-based timeouts are not allowed.

```python
t = threading.Thread(target=_target, daemon=True)
t.start()
t.join(timeout=QUERY_TIMEOUT_SECONDS)
if t.is_alive():
    raise TimeoutError(...)
```

### Execution steps

1. Import `engine` from `backend.db` and `text` from `sqlalchemy`.
2. Open a connection, execute the validated SQL via `text()`.
3. Iterate rows up to `MAX_ROWS`, converting each to a dictionary.
4. Return `execution_result` with `rows`, `row_count`, and `execution_time_seconds`.

### On failure

If execution raises an exception or times out:
- `execution_result.error` is set.
- `retry_count` is incremented.
- `validated_sql` is cleared to `None`.
- `error_message` is set.

The routing function `should_retry_after_execution` then decides whether to retry.

---

## State Mutation Rules

Each node returns a partial dictionary. LangGraph merges it into the shared state using shallow key-level updates.

### Write patterns by node

| Node | Fields written |
|---|---|
| `intent_agent` | `interpreted_intent` |
| `sql_agent` | `generated_sql` |
| `validation_agent` | `validated_sql`, `error_message`, `retry_count` (on failure) |
| `execution_tool` | `execution_result`, `error_message`, `retry_count` (on failure), `validated_sql` (cleared on failure) |
| `insight_agent` | `summary`, `chart_suggestion` |

### Important invariants

- `validated_sql` is **only set by the Validation Agent** on success. It is cleared to `None` on validation or execution failure.
- `error_message` is set on failure and cleared to `None` on success (by the Validation Agent).
- `retry_count` only increases, never decreases.
- `generated_sql` is overwritten each time the SQL Agent runs (including retries).

---

## Graph Compilation and Invocation

### Compilation

```python
banking_assistant_graph = build_graph()  # Called once at import time
```

`build_graph()` creates a `StateGraph(BankingAssistantState)`, adds all nodes and edges, and calls `.compile()`. The compiled graph is a singleton stored at module level.

### Invocation

```python
final_state = banking_assistant_graph.invoke(initial_state)
```

`.invoke()` is synchronous. It runs all nodes in sequence (respecting routing decisions) and returns the final state dictionary.

### Thread safety

The compiled graph object is stateless — all state is carried in the `initial_state` dict passed to `.invoke()`. Multiple concurrent invocations are safe because each gets its own state copy.

---

## Entry Points: main.py and /ask

### `ai_engine/main.py` — `run_banking_assistant(user_query, verbose=True)`

1. Creates initial state via `create_initial_state(user_query)`.
2. Calls `banking_assistant_graph.invoke(initial_state)`.
3. Passes the final state through `format_output()`, which produces:
   ```python
   {
       "validated_sql": ...,
       "execution_result": ...,
       "summary": ...,
       "chart_suggestion": ...,
       "error": ...
   }
   ```
4. If `verbose=True`, prints execution details to stdout.
5. On any exception, catches it and returns a structured error dict (same shape).

### `backend/main.py` — `POST /ask`

1. Receives `AskRequest` with `query` field.
2. Calls `run_banking_assistant(query, verbose=False)` via `asyncio.to_thread()`.
3. Normalizes `execution_result.rows` → `execution_result.data`.
4. Returns `QueryResponse`.

The `asyncio.to_thread()` wrapper prevents the synchronous LangGraph execution from blocking FastAPI's async event loop.

---

## Failure Modes

| Failure | How it surfaces | Recovery |
|---|---|---|
| Missing API key | `RuntimeError` from any LLM agent | Immediate termination, error in response |
| LLM rate limit / network error | `RuntimeError` re-raised by agent | Caught by `main.py`, returned as error |
| Invalid SQL (validation failure) | `should_retry` routes to `sql_agent` | Up to 2 retries with error context |
| Database execution error | `should_retry_after_execution` routes to `sql_agent` | Up to 2 retries |
| Query timeout (>30s) | `TimeoutError` in execution tool | Treated as execution error, may retry |
| Max retries exhausted | `should_retry` returns `"end_failure"` | Graph terminates, error in final state |
| Empty query | `ValueError` from `create_initial_state` | Caught by `run_banking_assistant`, returned as error |

In all cases, the caller receives a structured dictionary with an `error` field. No unhandled exceptions propagate to the API layer.
