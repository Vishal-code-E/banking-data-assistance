"""
Validation Agent - Validates SQL queries for safety and correctness.
Third agent in the LangGraph pipeline.
"""

from typing import Dict, Any
from ai_engine.state import BankingAssistantState, MAX_RETRY_COUNT
from ai_engine.utils.logger import logger
from ai_engine.utils.schema_loader import get_schema, get_schema_as_text
from ai_engine.utils.sql_security import validate_sql_safety


def load_validation_prompt() -> str:
    """Load the validation prompt template."""
    with open("/Users/vishale/banking-data-assistance/ai_engine/prompts/validation_prompt.txt", "r") as f:
        return f.read()


def call_llm_for_validation(prompt: str) -> str:
    """
    Abstract LLM call for SQL validation.
    In production, this would call OpenAI/Anthropic API.
    
    For now, we'll rely primarily on rule-based validation.
    """
    # SIMULATION MODE
    # In production, LLM would provide additional semantic validation
    # For now, we'll return a placeholder that rule-based checks override
    return "VALID"


def validation_agent(state: BankingAssistantState) -> Dict[str, Any]:
    """
    Validation Agent Node - Validates SQL for safety and correctness.
    
    Implements defense-in-depth:
    1. Rule-based security checks (primary)
    2. Schema validation
    3. LLM semantic validation (secondary)
    
    Args:
        state: Current state containing generated_sql
        
    Returns:
        State updates with validated_sql OR error_message and incremented retry_count
    """
    generated_sql = state["generated_sql"]
    retry_count = state.get("retry_count", 0)
    
    # Get schema for validation
    schema = get_schema()
    
    # STEP 1: Rule-based security validation (primary defense)
    is_valid, validation_message = validate_sql_safety(generated_sql, schema)
    
    if not is_valid:
        # Validation failed - increment retry and set error
        new_retry_count = retry_count + 1
        
        logger.log_validation_result(False, validation_message)
        logger.log_retry(new_retry_count, validation_message)
        
        logger.log_agent_execution(
            agent_name="ValidationAgent",
            input_data={"generated_sql": generated_sql},
            output_data={
                "is_valid": False,
                "error": validation_message,
                "retry_count": new_retry_count
            }
        )
        
        return {
            "error_message": validation_message,
            "retry_count": new_retry_count,
            "validated_sql": None
        }
    
    # STEP 2: LLM semantic validation (optional additional layer)
    # In production, you could add LLM-based validation here
    schema_text = get_schema_as_text()
    prompt_template = load_validation_prompt()
    formatted_prompt = prompt_template.format(
        schema=schema_text,
        sql=generated_sql
    )
    
    llm_validation = call_llm_for_validation(formatted_prompt)
    
    # If LLM says invalid, handle it
    if llm_validation.startswith("INVALID"):
        new_retry_count = retry_count + 1
        error_msg = llm_validation.replace("INVALID: ", "")
        
        logger.log_validation_result(False, error_msg)
        logger.log_retry(new_retry_count, error_msg)
        
        return {
            "error_message": error_msg,
            "retry_count": new_retry_count,
            "validated_sql": None
        }
    
    # Validation passed
    logger.log_validation_result(True, "SQL validated successfully")
    
    logger.log_agent_execution(
        agent_name="ValidationAgent",
        input_data={"generated_sql": generated_sql},
        output_data={
            "is_valid": True,
            "validated_sql": generated_sql
        }
    )
    
    return {
        "validated_sql": generated_sql,
        "error_message": None
    }
