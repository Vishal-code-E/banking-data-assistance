"""
Insight Agent - Generates human-readable summaries and visualization recommendations.
Final agent in the LangGraph pipeline.
"""

from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from ai_engine.state import BankingAssistantState
from ai_engine.utils.logger import logger

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_insight_prompt() -> str:
    """Load the insight generation prompt template."""
    with open(_PROMPT_DIR / "insight_prompt.txt", "r") as f:
        return f.read()


def call_llm_for_insight(prompt: str) -> tuple:
    """
    Call OpenAI LLM for insight generation.

    Returns:
        Tuple of (summary, chart_suggestion)
    """
    import os
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.log_error("OPENAI_API_KEY not set for insight generation", {})
        return "Query executed successfully and returned the requested data.", "table"

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Parse summary and chart from LLM response
        summary = content
        chart = "table"

        # Try to extract structured response
        lines = content.split("\n")
        for line in lines:
            line_lower = line.strip().lower()
            if line_lower.startswith("summary:"):
                summary = line.split(":", 1)[1].strip().strip('"')
            elif line_lower.startswith("chart:"):
                chart_val = line.split(":", 1)[1].strip().strip('"').lower()
                if chart_val in ("bar", "line", "pie", "table", "metric"):
                    chart = chart_val

        # If no structured format, use full response as summary
        if summary == content and "Summary" not in content:
            summary = content

        return summary, chart

    except Exception as e:
        logger.log_error(f"Insight LLM call failed: {e}", {})
        return "Query executed successfully and returned the requested data.", "table"


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
    
    row_count = execution_result.get('row_count', 0)
    print(f"[INSIGHT AGENT] EXECUTION RESULT COUNT: {row_count}")
    print(f"[INSIGHT AGENT] SUMMARY: {summary[:100]}")
    print(f"[INSIGHT AGENT] CHART: {chart_suggestion}")
    
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
    
    # Return state update
    return {
        "summary": summary,
        "chart_suggestion": chart_suggestion
    }
