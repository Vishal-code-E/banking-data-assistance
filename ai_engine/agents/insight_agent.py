"""
Insight Agent - Generates human-readable summaries and visualization recommendations.
Final agent in the LangGraph pipeline.
"""

from pathlib import Path
from typing import Dict, Any
from ai_engine.state import BankingAssistantState
from ai_engine.utils.logger import logger

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_insight_prompt() -> str:
    """Load the insight generation prompt template."""
    prompt_file = _PROMPTS_DIR / "insight_prompt.txt"
    with open(prompt_file, "r") as f:
        return f.read()


def call_llm_for_insight(prompt: str) -> tuple:
    """
    Abstract LLM call for insight generation.
    In production, this would call OpenAI/Anthropic API.

    Returns:
        Tuple of (summary, chart_suggestion)
    """
    # SIMULATION MODE - replace with actual LLM in production
    if "SELECT * FROM transactions WHERE amount >" in prompt:
        summary = "Retrieved high-value transactions exceeding the threshold amount, sorted by most recent first."
        chart = "table"

    elif "COUNT(*)" in prompt and "customers" in prompt:
        summary = "Counted the total number of customers matching the specified criteria."
        chart = "metric"

    elif "AVG(balance)" in prompt:
        summary = "Calculated the average account balance across matching accounts."
        chart = "metric"

    elif "status = 'failed'" in prompt:
        summary = "Retrieved all failed transactions within the specified time period."
        chart = "table"

    else:
        summary = "Query executed successfully and returned the requested data."
        chart = "table"

    return summary, chart


def insight_agent(state: BankingAssistantState) -> Dict[str, Any]:
    """
    Insight Agent Node - Generates summary and visualization recommendations.

    Args:
        state: Current state containing validated_sql and execution_result

    Returns:
        State updates with summary and chart_suggestion
    """
    validated_sql = state["validated_sql"]
    execution_result = state.get("execution_result", {})

    # Load prompt template
    prompt_template = load_insight_prompt()

    # Format prompt
    formatted_prompt = prompt_template.format(
        sql=validated_sql,
        result=str(execution_result)
    )

    # Call LLM (abstracted)
    summary, chart_suggestion = call_llm_for_insight(formatted_prompt)

    logger.log_agent_execution(
        agent_name="InsightAgent",
        input_data={
            "validated_sql": validated_sql,
            "execution_result": execution_result
        },
        output_data={
            "summary": summary,
            "chart_suggestion": chart_suggestion
        }
    )

    return {
        "summary": summary,
        "chart_suggestion": chart_suggestion
    }
