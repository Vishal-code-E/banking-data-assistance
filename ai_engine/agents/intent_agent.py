"""
Intent Agent - Extracts structured intent from user's natural language query.
First agent in the LangGraph pipeline.
"""

from typing import Dict, Any
from ai_engine.state import BankingAssistantState
from ai_engine.utils.logger import logger


def load_intent_prompt() -> str:
    """Load the intent extraction prompt template."""
    with open("/Users/vishale/banking-data-assistance/ai_engine/prompts/intent_prompt.txt", "r") as f:
        return f.read()


def call_llm_for_intent(prompt: str) -> str:
    """
    Call OpenAI LLM for intent extraction.
    """
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        logger.log_error(f"LLM call failed: {e}", {})
        # Fallback to basic extraction
        user_query = prompt.split("User Query: ")[-1].strip()
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
    
    # Return state update
    return {
        "interpreted_intent": interpreted_intent
    }
