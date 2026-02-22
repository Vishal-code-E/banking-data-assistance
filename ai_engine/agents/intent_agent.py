"""
Intent Agent - Extracts structured intent from user's natural language query.
First agent in the LangGraph pipeline.
"""

from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from ai_engine.state import BankingAssistantState
from ai_engine.utils.logger import logger

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_intent_prompt() -> str:
    """Load the intent extraction prompt template."""
    with open(_PROMPT_DIR / "intent_prompt.txt", "r") as f:
        return f.read()


def call_llm_for_intent(prompt: str) -> str:
    """
    Call OpenAI LLM for intent extraction.
    """
    import os
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.log_error("OPENAI_API_KEY not set", {})
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. "
            "Please set it in the Render dashboard under Environment Variables."
        )

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        response = llm.invoke(prompt)
        return response.content.strip()
    except RuntimeError:
        raise
    except Exception as e:
        logger.log_error(f"LLM call failed: {e}", {})
        raise RuntimeError(f"Intent extraction failed: {e}")


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
    
    # Return state update
    return {
        "interpreted_intent": interpreted_intent
    }
