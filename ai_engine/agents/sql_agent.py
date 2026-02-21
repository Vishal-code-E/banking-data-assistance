"""
SQL Generator Agent - Converts interpreted intent into SQL query.
Second agent in the LangGraph pipeline.
"""

from pathlib import Path
from typing import Dict, Any
from ai_engine.state import BankingAssistantState
from ai_engine.utils.logger import logger
from ai_engine.utils.schema_loader import get_schema_as_text

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_sql_prompt() -> str:
    """Load the SQL generation prompt template."""
    prompt_file = _PROMPTS_DIR / "sql_prompt.txt"
    with open(prompt_file, "r") as f:
        return f.read()


def call_llm_for_sql(prompt: str) -> str:
    """
    Abstract LLM call for SQL generation.
    In production, this would call OpenAI/Anthropic API.

    For now, we'll simulate with rule-based logic.
    """
    # SIMULATION MODE - replace with actual LLM in production
    prompt_lower = prompt.lower()

    if "most recent transactions where amount exceeds" in prompt_lower:
        return "SELECT * FROM transactions WHERE amount > 10000 ORDER BY transaction_date DESC LIMIT 5"

    elif "count total number of customers" in prompt_lower:
        if "premium" in prompt_lower:
            return "SELECT COUNT(*) as customer_count FROM customers WHERE account_type = 'premium'"
        return "SELECT COUNT(*) as customer_count FROM customers"

    elif "calculate average account balance" in prompt_lower:
        if "savings" in prompt_lower:
            return "SELECT AVG(balance) as avg_balance FROM accounts WHERE account_type = 'savings'"
        return "SELECT AVG(balance) as avg_balance FROM accounts"

    elif "status = 'failed'" in prompt_lower:
        return "SELECT * FROM transactions WHERE status = 'failed' AND transaction_date >= DATE('now', '-7 days')"

    else:
        return "SELECT * FROM transactions LIMIT 10"


def sql_agent(state: BankingAssistantState) -> Dict[str, Any]:
    """
    SQL Generator Agent Node - Converts intent to SQL.

    Args:
        state: Current state containing interpreted_intent

    Returns:
        State updates with generated_sql
    """
    interpreted_intent = state["interpreted_intent"]
    error_message = state.get("error_message", "")
    retry_count = state.get("retry_count", 0)

    # Load schema
    schema = get_schema_as_text()

    # Load prompt template
    prompt_template = load_sql_prompt()

    # Format prompt
    formatted_prompt = prompt_template.format(
        schema=schema,
        intent=interpreted_intent,
        error_message=error_message if error_message else "None"
    )

    # Call LLM (abstracted)
    generated_sql = call_llm_for_sql(formatted_prompt)

    # Clean up SQL
    generated_sql = generated_sql.strip().rstrip(';')

    logger.log_sql_generation(generated_sql, retry_count)

    logger.log_agent_execution(
        agent_name="SQLAgent",
        input_data={
            "interpreted_intent": interpreted_intent,
            "retry_count": retry_count
        },
        output_data={"generated_sql": generated_sql}
    )

    return {
        "generated_sql": generated_sql
    }
