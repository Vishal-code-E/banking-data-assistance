"""
Main entry point for the AI Banking Data Assistant.
Exposes process_query() as the integration contract for the backend.
"""

from typing import Optional
from ai_engine.graph import banking_assistant_graph
from ai_engine.state import create_initial_state
from ai_engine.utils.logger import logger


def _format_output(final_state: dict) -> dict:
    """
    Format the final graph state into the integration contract dict.

    Returns:
        {
            "validated_sql": str | None,
            "summary": str | None,
            "chart_suggestion": str | None,
            "error": str | None,
        }
    """
    error: Optional[str] = None
    if final_state.get("error_message"):
        error = final_state["error_message"]
    elif not final_state.get("validated_sql"):
        error = "Failed to generate valid SQL"

    return {
        "validated_sql": final_state.get("validated_sql"),
        "summary": final_state.get("summary"),
        "chart_suggestion": final_state.get("chart_suggestion"),
        "error": error,
    }


def process_query(user_query: str) -> dict:
    """
    Execute the multi-agent AI workflow for a natural-language banking query.

    This is the primary integration contract used by the backend.

    Args:
        user_query: Natural language query from the user.

    Returns:
        dict with keys:
            validated_sql (str | None)  – the generated and validated SQL
            summary       (str | None)  – human-readable summary of the query
            chart_suggestion (str | None) – recommended chart type
            error         (str | None)  – set when processing failed
    """
    initial_state = create_initial_state(user_query)

    try:
        final_state = banking_assistant_graph.invoke(initial_state)
        result = _format_output(final_state)

        logger.log_final_status(
            success=(result["error"] is None),
            validated_sql=result["validated_sql"],
            error=result["error"],
        )

        return result

    except Exception as exc:
        error_msg = f"System error: {exc}"
        logger.log_error(error_msg, {"user_query": user_query})

        return {
            "validated_sql": None,
            "summary": None,
            "chart_suggestion": None,
            "error": error_msg,
        }


def run_banking_assistant(user_query: str, verbose: bool = True) -> dict:
    """
    Execute the banking assistant workflow with optional console output.

    Args:
        user_query: Natural language query from user.
        verbose: Whether to print detailed execution info.

    Returns:
        Formatted output with validated_sql, summary, chart_suggestion, and error.
    """
    if verbose:
        print(f"\n{'='*70}")
        print("AI BANKING DATA ASSISTANT")
        print(f"{'='*70}")
        print(f"\nUser Query: {user_query}\n")
        print("Executing multi-agent workflow...\n")

    result = process_query(user_query)

    if verbose:
        print(f"{'='*70}")
        print("EXECUTION COMPLETE")
        print(f"{'='*70}\n")

        if result["error"]:
            print(f"ERROR: {result['error']}\n")
        else:
            print(f"SQL Query Generated:\n{result['validated_sql']}\n")
            print(f"Summary: {result['summary']}\n")
            print(f"Recommended Chart: {result['chart_suggestion']}\n")

    return result
