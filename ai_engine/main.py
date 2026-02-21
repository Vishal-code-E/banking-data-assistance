"""
Main entry point for the AI Banking Data Assistant.
Demonstrates the multi-agent system in action.
"""

import json
from pathlib import Path
from ai_engine.graph import banking_assistant_graph
from ai_engine.state import create_initial_state
from ai_engine.utils.logger import logger


def format_output(final_state: dict) -> dict:
    """
    Format the final state into a clean output contract.
    
    Args:
        final_state: Final state from graph execution
        
    Returns:
        Formatted output dictionary
    """
    # Check for error conditions
    error = None
    if final_state.get("error_message"):
        error = final_state["error_message"]
    elif not final_state.get("validated_sql"):
        error = "Failed to generate valid SQL"
    
    return {
        "validated_sql": final_state.get("validated_sql"),
        "summary": final_state.get("summary"),
        "chart_suggestion": final_state.get("chart_suggestion"),
        "error": error
    }


def run_banking_assistant(user_query: str, verbose: bool = True) -> dict:
    """
    Execute the banking assistant workflow for a user query.
    
    Args:
        user_query: Natural language query from user
        verbose: Whether to print detailed execution info
        
    Returns:
        Formatted output with validated_sql, summary, chart_suggestion, and error
    """
    print(f"\n{'='*70}")
    print(f"AI BANKING DATA ASSISTANT")
    print(f"{'='*70}")
    print(f"\nUser Query: {user_query}\n")
    
    # Validate input
    if not user_query or not user_query.strip():
        return {
            "validated_sql": None,
            "summary": None,
            "chart_suggestion": None,
            "error": "Query cannot be empty or whitespace-only"
        }

    # Create initial state
    initial_state = create_initial_state(user_query)

    try:
        # Execute the graph
        if verbose:
            print("Executing multi-agent workflow...\n")
        
        final_state = banking_assistant_graph.invoke(initial_state)
        
        # Format output
        output = format_output(final_state)
        
        # Log final status
        logger.log_final_status(
            success=(output["error"] is None),
            validated_sql=output["validated_sql"],
            error=output["error"]
        )
        
        # Print results
        if verbose:
            print(f"{'='*70}")
            print("EXECUTION COMPLETE")
            print(f"{'='*70}\n")
            
            if output["error"]:
                print(f"❌ ERROR: {output['error']}\n")
            else:
                print(f"✅ SQL Query Generated:\n{output['validated_sql']}\n")
                print(f"📊 Summary: {output['summary']}\n")
                print(f"📈 Recommended Chart: {output['chart_suggestion']}\n")
        
        return output
        
    except Exception as e:
        error_msg = f"System error: {str(e)}"
        logger.log_error(error_msg, {"user_query": user_query})
        
        return {
            "validated_sql": None,
            "summary": None,
            "chart_suggestion": None,
            "error": error_msg
        }


def main():
    """
    Main function with example invocations.
    """
    print("\n" + "="*70)
    print("AI BANKING DATA ASSISTANT - MULTI-AGENT SYSTEM")
    print("Powered by LangGraph")
    print("="*70)
    
    # Example queries
    test_queries = [
        "Show last 5 transactions above 10000",
        "How many customers have premium accounts?",
        "What's the average balance for savings accounts?",
    ]
    
    results = []
    
    for query in test_queries:
        result = run_banking_assistant(query, verbose=True)
        results.append({
            "query": query,
            "result": result
        })
        print("\n" + "-"*70 + "\n")
    
    # Summary output
    print("\n" + "="*70)
    print("EXECUTION SUMMARY")
    print("="*70 + "\n")
    
    for idx, item in enumerate(results, 1):
        print(f"{idx}. Query: {item['query']}")
        if item['result']['error']:
            print(f"   Status: ❌ FAILED - {item['result']['error']}")
        else:
            print(f"   Status: ✅ SUCCESS")
            print(f"   SQL: {item['result']['validated_sql']}")
        print()
    
    # Export results as JSON
    output_path = Path(__file__).resolve().parent / "example_output.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Full results exported to: ai_engine/example_output.json\n")


if __name__ == "__main__":
    main()
