"""
SQL Generator Agent - Converts interpreted intent into SQL query.
Second agent in the LangGraph pipeline.
"""

from typing import Dict, Any
from pathlib import Path
from ai_engine.state import BankingAssistantState
from ai_engine.utils.logger import logger
from ai_engine.utils.schema_loader import get_schema_as_text

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_sql_prompt() -> str:
    """Load the SQL generation prompt template."""
    with open(_PROMPT_DIR / "sql_prompt.txt", "r") as f:
        return f.read()


def call_llm_for_sql(prompt: str) -> str:
    """
    Call OpenAI LLM for SQL generation.
    """
    import os
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.log_error("OPENAI_API_KEY not set", {})
        return "SELECT * FROM transactions LIMIT 10"

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        response = llm.invoke(prompt)

        # Extract SQL from response (handle code blocks)
        sql = response.content.strip()

        # Remove markdown code blocks if present
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()

        return sql
    except Exception as e:
        logger.log_error(f"LLM call failed: {e}", {})
        # Fallback to safe default
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
    
    # Return state update
    return {
        "generated_sql": generated_sql
    }
