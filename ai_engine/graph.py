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
    Simulated database execution node.
    In production the backend executes the validated SQL against the real database.

    Args:
        state: Current state containing validated_sql

    Returns:
        State updates with execution_result
    """
    validated_sql = state["validated_sql"]

    # SIMULATION MODE - the real backend handles SQL execution
    if "COUNT(*)" in validated_sql:
        mock_result = {"rows": [{"customer_count": 342}], "row_count": 1}
    elif "AVG(balance)" in validated_sql:
        mock_result = {"rows": [{"avg_balance": 8450.75}], "row_count": 1}
    elif "SELECT * FROM transactions" in validated_sql:
        mock_result = {
            "rows": [
                {"transaction_id": 1001, "amount": 15000.00, "transaction_date": "2026-02-20"},
                {"transaction_id": 1002, "amount": 12500.00, "transaction_date": "2026-02-19"},
            ],
            "row_count": 2
        }
    else:
        mock_result = {"rows": [], "row_count": 0}

    logger.log_agent_execution(
        agent_name="ExecutionTool",
        input_data={"validated_sql": validated_sql},
        output_data={"execution_result": mock_result}
    )

    return {"execution_result": mock_result}


def should_retry(state: BankingAssistantState) -> Literal["sql_agent", "execution_tool", "end_failure"]:
    """
    Conditional routing logic after validation.

    Determines whether to:
    - Retry SQL generation (validation failed, retries remain)
    - Proceed to execution (validation passed)
    - End with failure (max retries exceeded)
    """
    error_message = state.get("error_message")
    retry_count = state.get("retry_count", 0)
    validated_sql = state.get("validated_sql")

    if validated_sql and not error_message:
        return "execution_tool"

    if error_message and retry_count < MAX_RETRY_COUNT:
        logger.log_retry(retry_count, error_message)
        return "sql_agent"

    if retry_count >= MAX_RETRY_COUNT:
        logger.log_final_status(
            success=False,
            error=f"Max retries ({MAX_RETRY_COUNT}) exceeded. Last error: {error_message}"
        )
        return "end_failure"

    return "execution_tool"


def build_graph() -> StateGraph:
    """
    Build the LangGraph workflow.

    Flow:
    START → IntentAgent → SQLAgent → ValidationAgent → [Conditional]
                                                           ↓
                                            [retry] → SQLAgent (retry_count < MAX)
                                            [success] → ExecutionTool → InsightAgent → END
                                            [failure] → END
    """
    workflow = StateGraph(BankingAssistantState)

    workflow.add_node("intent_agent", intent_agent)
    workflow.add_node("sql_agent", sql_agent)
    workflow.add_node("validation_agent", validation_agent)
    workflow.add_node("execution_tool", execution_tool_node)
    workflow.add_node("insight_agent", insight_agent)

    workflow.set_entry_point("intent_agent")

    workflow.add_edge("intent_agent", "sql_agent")
    workflow.add_edge("sql_agent", "validation_agent")

    workflow.add_conditional_edges(
        "validation_agent",
        should_retry,
        {
            "sql_agent": "sql_agent",
            "execution_tool": "execution_tool",
            "end_failure": END
        }
    )

    workflow.add_edge("execution_tool", "insight_agent")
    workflow.add_edge("insight_agent", END)

    return workflow.compile()


# Create the compiled graph (singleton)
banking_assistant_graph = build_graph()
