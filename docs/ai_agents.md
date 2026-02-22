# AI Agents — Multi-Agent Architecture

This document covers the design, implementation, and behavior of the four AI agents that form the core reasoning pipeline of the Banking Data Assistant. Each agent occupies a specific role in the LangGraph workflow and communicates through a shared typed state.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Shared State](#shared-state)
3. [Intent Agent](#intent-agent)
4. [SQL Agent](#sql-agent)
5. [Validation Agent](#validation-agent)
6. [Insight Agent](#insight-agent)
7. [Prompt Engineering](#prompt-engineering)
8. [Security Layers](#security-layers)
9. [Error Handling and Retry Logic](#error-handling-and-retry-logic)
10. [Extending the Agent Pipeline](#extending-the-agent-pipeline)

---

## Architecture Overview

The system uses a **linear multi-agent pipeline** orchestrated by LangGraph. Each agent is a pure function that receives the current state, performs its task, and returns a partial state update. Agents do not call each other directly — all routing is handled by the graph layer (see [orchestration.md](orchestration.md)).

```
User Query
    │
    ▼
┌──────────────┐
│ Intent Agent │  ← Extracts structured intent from natural language
└──────┬───────┘
       │ interpreted_intent
       ▼
┌──────────────┐
│  SQL Agent   │  ← Generates SQL from intent + schema
└──────┬───────┘
       │ generated_sql
       ▼
┌──────────────────┐
│ Validation Agent │  ← Rule-based + schema checks
└──────┬───────────┘
       │ validated_sql
       ▼
┌──────────────────┐
│ Execution Tool   │  ← Runs SQL against the database (not an LLM agent)
└──────┬───────────┘
       │ execution_result
       ▼
┌──────────────┐
│ Insight Agent│  ← Generates summary + chart recommendation
└──────────────┘
```

Three of the four agents (Intent, SQL, Insight) call an LLM. The Validation Agent is entirely rule-based.

---

## Shared State

All agents read from and write to a single `BankingAssistantState` defined in `ai_engine/state.py`:

```python
class BankingAssistantState(TypedDict):
    # User inputs
    user_query: str

    # Agent outputs
    interpreted_intent: Optional[str]
    generated_sql: Optional[str]
    validated_sql: Optional[str]
    execution_result: Optional[dict]

    # Control flow
    retry_count: int
    error_message: Optional[str]

    # Final outputs
    summary: Optional[str]
    chart_suggestion: Optional[str]
```

**Key design decisions:**

| Field | Written by | Read by |
|---|---|---|
| `user_query` | Caller | Intent Agent |
| `interpreted_intent` | Intent Agent | SQL Agent |
| `generated_sql` | SQL Agent | Validation Agent |
| `validated_sql` | Validation Agent | Execution Tool, Insight Agent |
| `execution_result` | Execution Tool | Insight Agent |
| `retry_count` | Validation Agent, Execution Tool | Routing functions |
| `error_message` | Validation Agent, Execution Tool | SQL Agent (for retry context) |
| `summary` | Insight Agent | Caller |
| `chart_suggestion` | Insight Agent | Caller |

The `create_initial_state(user_query)` factory function initializes all optional fields to `None` and `retry_count` to `0`. It raises `ValueError` if `user_query` is empty or whitespace-only.

`MAX_RETRY_COUNT` is set to **2**, meaning the pipeline allows up to 2 retry loops before failing.

---

## Intent Agent

**File:** `ai_engine/agents/intent_agent.py`  
**Role:** First agent in the pipeline. Converts a natural-language question into a structured intent description.  
**LLM:** GPT-4o-mini via `langchain-openai` (`temperature=0`)

### Behavior

1. Loads the prompt template from `ai_engine/prompts/intent_prompt.txt`.
2. Formats the prompt with `{user_query}`.
3. Calls the LLM via `ChatOpenAI.invoke()`.
4. Returns `{ "interpreted_intent": <LLM response> }`.

### Input → Output

| Input field | Output field |
|---|---|
| `user_query` | `interpreted_intent` |

### Example

```
Input:  "Show last 5 transactions above 10000"
Output: "Retrieve the 5 most recent transactions where amount > 10000,
         ordered by created_at DESC"
```

### Error behavior

If `OPENAI_API_KEY` is not set, the agent raises `RuntimeError` with a message directing the operator to configure the key. This is a hard failure — no fallback data is generated.

---

## SQL Agent

**File:** `ai_engine/agents/sql_agent.py`  
**Role:** Second agent. Converts the structured intent into a valid SQL SELECT query.  
**LLM:** GPT-4o-mini via `langchain-openai` (`temperature=0`)

### Behavior

1. Loads the database schema via `get_schema_as_text()` from `ai_engine/utils/schema_loader.py`.
2. Loads the prompt template from `ai_engine/prompts/sql_prompt.txt`.
3. Formats the prompt with `{schema}`, `{intent}`, and `{error_message}` (populated on retries).
4. Calls the LLM.
5. Strips markdown code fences (` ```sql ``` `) if the LLM wraps the response.
6. Strips trailing semicolons.
7. Returns `{ "generated_sql": <cleaned SQL> }`.

### Retry awareness

On a retry, the `error_message` from the previous validation failure is injected into the prompt. This gives the LLM context about what went wrong and allows it to self-correct (e.g., referencing a non-existent column).

### Schema grounding

The schema is not inferred from the live database at generation time. It is a hardcoded dictionary in `schema_loader.py` that mirrors the actual `schema.sql`:

| Table | Columns |
|---|---|
| `customers` | `id`, `name`, `email`, `created_at` |
| `accounts` | `id`, `customer_id`, `account_number`, `balance`, `created_at` |
| `transactions` | `id`, `account_id`, `type` (credit/debit), `amount`, `created_at` |

The schema text is formatted as markdown headers and bullet lists before being passed into the prompt.

### Error behavior

Same as Intent Agent — raises `RuntimeError` if `OPENAI_API_KEY` is absent.

---

## Validation Agent

**File:** `ai_engine/agents/validation_agent.py`  
**Role:** Third agent. Validates the generated SQL for safety and correctness before execution.  
**LLM:** None (rule-based). A placeholder `call_llm_for_validation()` exists but currently returns `"VALID"` unconditionally. The real validation is performed by rule-based functions.

### Validation pipeline

The agent applies checks in this order via `validate_sql_safety()` from `ai_engine/utils/sql_security.py`:

| # | Check | Function | Blocks |
|---|---|---|---|
| 1 | SELECT-only | `is_select_only()` | Any query not starting with `SELECT` |
| 2 | Single statement | `contains_multiple_statements()` | Stacked queries (`;` separators) |
| 3 | No UNION | `contains_union()` | UNION-based injection |
| 4 | No forbidden keywords | `contains_forbidden_keywords()` | `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `TRUNCATE`, `REPLACE`, `MERGE`, `GRANT`, `REVOKE`, `EXEC`, `EXECUTE`, `CALL`, `PROCEDURE`, `FUNCTION` |
| 5 | Schema table check | `validate_schema_tables()` | References to non-existent tables |

If all checks pass:
- `enforce_limit()` appends `LIMIT 100` if no LIMIT clause exists, or caps existing LIMIT at 1000.
- Returns `{ "validated_sql": <sql>, "error_message": None }`.

If any check fails:
- Increments `retry_count`.
- Sets `error_message` with the specific failure reason.
- Sets `validated_sql` to `None`.
- The graph router then decides whether to retry or terminate.

### SQL comment stripping

`remove_sql_comments()` strips both single-line (`--`) and multi-line (`/* */`) comments before any validation check, preventing comment-based obfuscation attacks.

---

## Insight Agent

**File:** `ai_engine/agents/insight_agent.py`  
**Role:** Final agent. Generates a human-readable summary and a chart type recommendation based on the executed query results.  
**LLM:** GPT-4o-mini via `langchain-openai` (`temperature=0`)

### Behavior

1. Loads the prompt template from `ai_engine/prompts/insight_prompt.txt`.
2. Formats the prompt with `{sql}` (validated SQL) and `{result}` (stringified execution result).
3. Calls the LLM.
4. Parses the response using regex to extract `SUMMARY:` and `CHART:` lines.
5. Returns `{ "summary": <text>, "chart_suggestion": <chart type> }`.

### Response parsing

The parser uses `re.search` with `re.IGNORECASE | re.DOTALL`:

```python
# Match SUMMARY: ... (greedy, can span lines until CHART: or end)
summary_match = re.search(
    r'(?:^|\n)\s*summary\s*:\s*(.+?)(?=\n\s*chart\s*:|$)',
    content, re.IGNORECASE | re.DOTALL
)

# Match CHART: ... (single word)
chart_match = re.search(
    r'(?:^|\n)\s*chart\s*:\s*(\w+)',
    content, re.IGNORECASE
)
```

If the LLM returns an unstructured response (no `SUMMARY:` or `CHART:` prefix), the full content is used as the summary and the chart defaults to `"table"`.

### Valid chart types

`bar`, `line`, `pie`, `table`, `metric`, `doughnut`

Any chart value not in this set is discarded and falls back to `"table"`.

---

## Prompt Engineering

Each agent's prompt is stored as a plain text file in `ai_engine/prompts/`:

| File | Used by | Key directives |
|---|---|---|
| `intent_prompt.txt` | Intent Agent | Entity type, action, filters, aggregation, limit extraction |
| `sql_prompt.txt` | SQL Agent | SELECT-only, no UNION, proper JOINs, default LIMIT 100, schema grounding |
| `validation_prompt.txt` | Validation Agent | VALID/INVALID binary response format |
| `insight_prompt.txt` | Insight Agent | Chart selection rules table, 5 examples, strict 2-line output format |

Prompts are loaded at call time (not cached), which means they can be edited without restarting the server. This design supports iterative prompt tuning during development.

### Prompt injection defense

The prompts themselves do not contain explicit injection defenses. The system relies on the Validation Agent's rule-based checks to catch any harmful SQL that might be generated from adversarial user input.

---

## Security Layers

The system implements defense-in-depth across multiple layers:

### Layer 1 — LLM prompt constraints (SQL Agent)
The SQL generation prompt explicitly instructs the LLM to generate only SELECT queries, avoid UNION, avoid subqueries, and reference only known tables/columns.

### Layer 2 — Rule-based validation (Validation Agent)
Five independent checks in `sql_security.py` catch violations that the LLM might produce despite prompt instructions.

### Layer 3 — LIMIT enforcement
`enforce_limit()` guarantees every query has a LIMIT clause. Default: 100 rows. Maximum: 1000 rows.

### Layer 4 — Backend validation (redundant)
The backend's `validation.py` applies its own 9-step validation pipeline (comments, multiple statements, statement type, dangerous keywords, injection patterns, table authorization, query length) before execution. This is an independent layer that does not trust the AI engine's validation.

### Layer 5 — SQLAlchemy text()
All queries are executed via `sqlalchemy.text()`, which prevents direct string interpolation attacks at the driver level.

---

## Error Handling and Retry Logic

### API key missing
All three LLM-calling agents (Intent, SQL, Insight) raise `RuntimeError` if `OPENAI_API_KEY` is not set. This surfaces immediately to the user as an error message rather than producing misleading fallback data.

### LLM call failures
If the LLM call itself fails (network error, rate limit, etc.), the agent catches the exception and re-raises it as `RuntimeError` with context, which the graph propagates to `ai_engine/main.py`'s exception handler.

### Validation failures and retries
When the Validation Agent rejects a query, it increments `retry_count` and sets `error_message`. The graph's conditional routing function (`should_retry`) then:
- Routes back to SQL Agent if `retry_count < MAX_RETRY_COUNT` (2).
- Routes to `END` if retries are exhausted.

The same retry mechanism applies after execution failures via `should_retry_after_execution`.

### Output contract on failure
`format_output()` in `ai_engine/main.py` always returns a dict with five keys:
```python
{
    "validated_sql": None,
    "execution_result": None,
    "summary": None,
    "chart_suggestion": None,
    "error": "<error message>"
}
```
The caller never receives an exception — only structured error data.

---

## Extending the Agent Pipeline

To add a new agent:

1. Create a new file in `ai_engine/agents/` following the existing pattern.
2. Define a function with signature `(state: BankingAssistantState) -> Dict[str, Any]`.
3. Add any new state fields to `BankingAssistantState` in `state.py`.
4. Register the node in `graph.py` via `workflow.add_node()`.
5. Add edges connecting the new node to the appropriate predecessors/successors.
6. If the agent uses an LLM, add a prompt file in `ai_engine/prompts/`.

The agent must return a dictionary containing only the state fields it wants to update. LangGraph merges this partial update into the shared state automatically.
