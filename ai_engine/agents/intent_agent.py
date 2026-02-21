"""
Intent Agent - Extracts structured intent from user's natural language query.
First agent in the LangGraph pipeline.
"""

from pathlib import Path
from typing import Dict, Any
from ai_engine.state import BankingAssistantState
from ai_engine.utils.logger import logger

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_intent_prompt() -> str:
    """Load the intent extraction prompt template."""
    prompt_file = _PROMPTS_DIR / "intent_prompt.txt"
    with open(prompt_file, "r") as f:
        return f.read()


def call_llm_for_intent(prompt: str) -> str:
    """
    Abstract LLM call for intent extraction.
    In production, this would call OpenAI/Anthropic API.

    For now, we'll simulate with rule-based logic.
    """
    # SIMULATION MODE - replace with actual LLM in production
    user_query = prompt.split("User Query: ")[-1].strip()

    query_lower = user_query.lower()

    if "last" in query_lower and "transactions" in query_lower:
        if "above" in query_lower or ">" in query_lower:
            return "Retrieve the most recent transactions where amount exceeds a threshold, ordered by transaction_date DESC with limited results"
        return "Retrieve the most recent transactions, ordered by transaction_date DESC with limited results"

    elif "how many" in query_lower and "customers" in query_lower:
        return "Count total number of customers, optionally filtered by account type or status"

    elif "average" in query_lower and "balance" in query_lower:
        return "Calculate average account balance, optionally filtered by account type"

    elif "failed" in query_lower and "transactions" in query_lower:
        return "Retrieve transactions where status = 'failed', with date range filter"

    else:
        return f"Extract and analyze data based on: {user_query}"


def intent_agent(state: BankingAssistantState) -> Dict[str, Any]:
    """
    Intent Agent Node - Extracts structured intent from user query.

    Args:
        state: Current state containing user_query

    Returns:
        State updates with interpreted_intent
    """
    user_query = state["user_query"]

    logger.log_user_query(user_query)

    # Load prompt template
    prompt_template = load_intent_prompt()

    # Format prompt with user query
    formatted_prompt = prompt_template.format(user_query=user_query)

    # Call LLM (abstracted)
    interpreted_intent = call_llm_for_intent(formatted_prompt)

    logger.log_agent_execution(
        agent_name="IntentAgent",
        input_data={"user_query": user_query},
        output_data={"interpreted_intent": interpreted_intent}
    )

    return {
        "interpreted_intent": interpreted_intent
    }
