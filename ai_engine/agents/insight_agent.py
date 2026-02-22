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
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. "
            "Please set it in the Render dashboard under Environment Variables."
        )

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Parse summary and chart from LLM response
        summary = content
        chart = "table"

        # Try to extract structured response (case-insensitive, flexible)
        import re

        # Match SUMMARY: ... (greedy, can span line)
        summary_match = re.search(
            r'(?:^|\n)\s*summary\s*:\s*(.+?)(?=\n\s*chart\s*:|$)',
            content, re.IGNORECASE | re.DOTALL
        )
        if summary_match:
            summary = summary_match.group(1).strip().strip('"').strip("'")

        # Match CHART: ... (single word)
        chart_match = re.search(
            r'(?:^|\n)\s*chart\s*:\s*(\w+)',
            content, re.IGNORECASE
        )
        if chart_match:
            chart_val = chart_match.group(1).strip().lower()
            valid_charts = ("bar", "line", "pie", "table", "metric", "doughnut")
            if chart_val in valid_charts:
                chart = chart_val

        # Fallback: if no structured format found, use full content as summary
        if not summary_match:
            summary = content

        return summary, chart

    except RuntimeError:
        raise
    except Exception as e:
        logger.log_error(f"Insight LLM call failed: {e}", {})
        raise RuntimeError(f"Insight generation failed: {e}")


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
    
    # Return state update
    return {
        "summary": summary,
        "chart_suggestion": chart_suggestion
    }
