"""
State management for the AI Banking Data Assistant.
Uses Pydantic for strict type validation and LangGraph TypedDict pattern.
"""

from typing import TypedDict, Optional


class BankingAssistantState(TypedDict):
    """
    Shared state schema for the multi-agent banking assistant workflow.

    This state is passed through all agents in the LangGraph pipeline.
    Each agent reads from and writes to this state.
    """

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


def create_initial_state(user_query: str) -> BankingAssistantState:
    """
    Factory function to create initial state with defaults.

    Args:
        user_query: The user's natural language query

    Returns:
        BankingAssistantState with all fields initialized
    """
    return BankingAssistantState(
        user_query=user_query,
        interpreted_intent=None,
        generated_sql=None,
        validated_sql=None,
        execution_result=None,
        retry_count=0,
        error_message=None,
        summary=None,
        chart_suggestion=None,
    )


# Constants
MAX_RETRY_COUNT = 2
