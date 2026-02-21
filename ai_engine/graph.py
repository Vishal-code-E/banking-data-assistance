"""
LangGraph orchestration for the AI Banking Data Assistant.
Defines the multi-agent workflow with conditional routing and retry logic.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from ai_engine.state import BankingAssistantState, MAX_RETRY_COUNT
from ai_engine.agents.intent_agent import intent_agent
from ai_engine.agents.sql_agent import sql_agent
from ai_engine.agents.validation_agent import validation_agent
from ai_engine.agents.insight_agent import insight_agent
from ai_engine.utils.logger import logger


def execution_tool_node(state: BankingAssistantState) -> dict:
    """
    Database execution node - executes validated SQL against the real database.

    Args:
        state: Current state containing validated_sql

    Returns:
        State updates with execution_result
    """
    import time
    import threading

    QUERY_TIMEOUT_SECONDS = 30
    MAX_ROWS = 1000

    validated_sql = state["validated_sql"]
    start_time = time.time()

    try:
        # Execute against real database
        from backend.db import engine
        from sqlalchemy import text

        def _run_query():
            with engine.connect() as conn:
                result = conn.execute(text(validated_sql))

                rows = []
                columns = list(result.keys()) if result.keys() else []

                for row in result:
                    if len(rows) >= MAX_ROWS:
                        break
                    row_dict = {}
                    for i, col in enumerate(columns):
                        row_dict[col] = row[i]
                    rows.append(row_dict)

                return rows

        # Use a thread with join timeout (works in non-main threads)
        query_result = [None]
        query_error = [None]

        def _target():
            try:
                query_result[0] = _run_query()
            except Exception as e:
                query_error[0] = e

        t = threading.Thread(target=_target, daemon=True)
        t.start()
        t.join(timeout=QUERY_TIMEOUT_SECONDS)

        if t.is_alive():
            raise TimeoutError(f"Query exceeded {QUERY_TIMEOUT_SECONDS}s timeout")
        if query_error[0]:
            raise query_error[0]

        rows = query_result[0]
        execution_time = round(time.time() - start_time, 3)
        execution_result = {
            "rows": rows,
            "row_count": len(rows),
            "execution_time_seconds": execution_time
        }

    except TimeoutError as e:
        execution_time = round(time.time() - start_time, 3)
        logger.log_error(f"Query timeout: {e}", {"sql": validated_sql})
        execution_result = {
            "rows": [],
            "row_count": 0,
            "error": str(e),
            "execution_time_seconds": execution_time
        }

    except Exception as e:
        execution_time = round(time.time() - start_time, 3)
        logger.log_error(f"Database execution failed: {e}", {"sql": validated_sql})
        execution_result = {
            "rows": [],
            "row_count": 0,
            "error": str(e),
            "execution_time_seconds": execution_time
        }
    
    logger.log_agent_execution(
        agent_name="ExecutionTool",
        input_data={"validated_sql": validated_sql},
        output_data={"execution_result": execution_result}
    )

    # If execution failed, set error for potential retry
    if execution_result.get("error"):
        retry_count = state.get("retry_count", 0)
        new_retry_count = retry_count + 1
        return {
            "execution_result": execution_result,
            "error_message": f"Execution error: {execution_result['error']}",
            "retry_count": new_retry_count,
            "validated_sql": None
        }

    return {
        "execution_result": execution_result,
        "error_message": None
    }


def should_retry(state: BankingAssistantState) -> Literal["sql_agent", "execution_tool", "end_failure"]:
    """
    Conditional routing logic after validation.
    
    Determines whether to:
    - Retry SQL generation (if validation failed and retries remain)
    - Proceed to execution (if validation passed)
    - End with failure (if max retries exceeded)
    
    Args:
        state: Current state
        
    Returns:
        Next node to route to
    """
    error_message = state.get("error_message")
    retry_count = state.get("retry_count", 0)
    validated_sql = state.get("validated_sql")
    
    # If validation passed, proceed to execution
    if validated_sql and not error_message:
        return "execution_tool"
    
    # If validation failed but we can retry
    if error_message and retry_count < MAX_RETRY_COUNT:
        logger.log_retry(retry_count, error_message)
        return "sql_agent"
    
    # Max retries exceeded - fail
    if retry_count >= MAX_RETRY_COUNT:
        logger.log_final_status(
            success=False,
            error=f"Max retries ({MAX_RETRY_COUNT}) exceeded. Last error: {error_message}"
        )
        return "end_failure"
    
    # Default to execution if state is unclear
    return "execution_tool"


def should_retry_after_execution(state: BankingAssistantState) -> Literal["sql_agent", "insight_agent", "end_failure"]:
    """
    Conditional routing after execution.
    Routes back to sql_agent on execution errors if retries remain.
    """
    error_message = state.get("error_message")
    retry_count = state.get("retry_count", 0)
    execution_result = state.get("execution_result", {})

    # Execution succeeded
    if not error_message and not execution_result.get("error"):
        return "insight_agent"

    # Execution failed but retries remain
    if retry_count < MAX_RETRY_COUNT:
        logger.log_retry(retry_count, error_message or "Execution error")
        return "sql_agent"

    # Max retries exceeded
    logger.log_final_status(
        success=False,
        error=f"Max retries ({MAX_RETRY_COUNT}) exceeded after execution error: {error_message}"
    )
    return "end_failure"


def build_graph() -> StateGraph:
    """
    Build the LangGraph workflow.
    
    Flow:
    START → IntentAgent → SQLAgent → ValidationAgent → [Conditional]
                                                           ↓
                                            [retry] → SQLAgent (if retry_count < MAX)
                                            [success] → ExecutionTool → InsightAgent → END
                                            [failure] → END
    
    Returns:
        Compiled StateGraph
    """
    # Initialize graph with state schema
    workflow = StateGraph(BankingAssistantState)
    
    # Add agent nodes
    workflow.add_node("intent_agent", intent_agent)
    workflow.add_node("sql_agent", sql_agent)
    workflow.add_node("validation_agent", validation_agent)
    workflow.add_node("execution_tool", execution_tool_node)
    workflow.add_node("insight_agent", insight_agent)
    
    # Define edges
    workflow.set_entry_point("intent_agent")
    
    # Linear flow: Intent → SQL → Validation
    workflow.add_edge("intent_agent", "sql_agent")
    workflow.add_edge("sql_agent", "validation_agent")
    
    # Conditional edge after validation
    workflow.add_conditional_edges(
        "validation_agent",
        should_retry,
        {
            "sql_agent": "sql_agent",           # Retry SQL generation
            "execution_tool": "execution_tool",  # Proceed to execution
            "end_failure": END                   # Max retries - terminate
        }
    )
    
    # Conditional edge after execution (retry on execution errors)
    workflow.add_conditional_edges(
        "execution_tool",
        should_retry_after_execution,
        {
            "sql_agent": "sql_agent",           # Retry SQL on execution error
            "insight_agent": "insight_agent",    # Success → insights
            "end_failure": END                   # Max retries - terminate
        }
    )
    workflow.add_edge("insight_agent", END)
    
    # Compile the graph
    return workflow.compile()


# Create the compiled graph (singleton)
banking_assistant_graph = build_graph()
