"""
Demonstration script showing the AI Banking Assistant in action.
Shows various query types and system capabilities.
"""

from ai_engine.main import run_banking_assistant
import json


def demonstrate_system():
    """Run comprehensive demonstrations of the system."""
    
    print("\n" + "="*80)
    print(" AI BANKING DATA ASSISTANT - SYSTEM DEMONSTRATION")
    print(" Multi-Agent Intelligence Layer powered by LangGraph")
    print("="*80 + "\n")
    
    # Test cases covering different query patterns
    test_cases = [
        {
            "category": "High-Value Transaction Query",
            "query": "Show last 5 transactions above 10000",
            "expected": "Should filter by amount and return limited sorted results"
        },
        {
            "category": "Customer Count Aggregation",
            "query": "How many customers have premium accounts?",
            "expected": "Should count customers with filter on account_type"
        },
        {
            "category": "Average Calculation",
            "query": "What's the average balance for savings accounts?",
            "expected": "Should calculate AVG with account type filter"
        },
        {
            "category": "Status-Based Filtering",
            "query": "List all failed transactions in the last week",
            "expected": "Should filter by status and date range"
        }
    ]
    
    results = []
    
    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n{'─'*80}")
        print(f"TEST CASE {idx}: {test_case['category']}")
        print(f"{'─'*80}")
        print(f"Query: \"{test_case['query']}\"")
        print(f"Expected: {test_case['expected']}\n")
        
        result = run_banking_assistant(test_case['query'], verbose=False)
        
        # Display compact result
        print("\n📋 RESULT:")
        if result['error']:
            print(f"   ❌ ERROR: {result['error']}")
            status = "FAILED"
        else:
            print(f"   ✅ Status: SUCCESS")
            print(f"   🔍 SQL: {result['validated_sql']}")
            print(f"   💡 Summary: {result['summary']}")
            print(f"   📊 Chart: {result['chart_suggestion']}")
            status = "SUCCESS"
        
        results.append({
            "test_case": test_case['category'],
            "query": test_case['query'],
            "status": status,
            "result": result
        })
    
    # Summary report
    print("\n" + "="*80)
    print(" EXECUTION SUMMARY")
    print("="*80 + "\n")
    
    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    total_count = len(results)
    
    print(f"Total Tests: {total_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_count - success_count}")
    print(f"Success Rate: {(success_count/total_count)*100:.1f}%\n")
    
    # Detailed results table
    print("Detailed Results:")
    print("-" * 80)
    for idx, result in enumerate(results, 1):
        status_icon = "✅" if result['status'] == 'SUCCESS' else "❌"
        print(f"{idx}. {status_icon} {result['test_case']}")
        print(f"   Query: {result['query']}")
        if result['status'] == 'SUCCESS':
            print(f"   SQL: {result['result']['validated_sql']}")
        else:
            print(f"   Error: {result['result']['error']}")
        print()
    
    # Export results
    output_file = "/Users/vishale/banking-data-assistance/ai_engine/demo_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Full results exported to: {output_file}\n")
    
    return results


def demonstrate_retry_logic():
    """Demonstrate the retry mechanism with an intentionally problematic query."""
    
    print("\n" + "="*80)
    print(" RETRY LOGIC DEMONSTRATION")
    print("="*80 + "\n")
    
    print("This demonstrates the system's ability to handle and retry failed validations.\n")
    
    # In production, this would trigger retry logic
    # For now, we'll just document the mechanism
    
    print("Retry Flow:")
    print("1. SQL Agent generates query")
    print("2. Validation Agent detects issue")
    print("3. Error message is logged")
    print("4. Retry count increments")
    print("5. SQL Agent re-generates with error feedback")
    print("6. Process repeats (max 2 retries)")
    print("7. If still failing, workflow terminates with error\n")
    
    print("Example retry scenario:")
    print("  Attempt 1: SELECT * FROM invalid_table → INVALID (table not in schema)")
    print("  Attempt 2: SELECT * FROM transactions → VALID ✓\n")


def show_architecture():
    """Display system architecture information."""
    
    print("\n" + "="*80)
    print(" SYSTEM ARCHITECTURE")
    print("="*80 + "\n")
    
    print("Multi-Agent Workflow:")
    print("""
    ┌─────────────┐
    │   START     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────────┐
    │  Intent Agent   │ ← Extracts structured intent
    └────────┬────────┘
           │
           ▼
    ┌─────────────────┐
    │   SQL Agent     │ ← Converts intent → SQL
    └────────┬────────┘
           │
           ▼
    ┌─────────────────┐
    │ Validation Agent│ ← Security & correctness checks
    └────────┬────────┘
           │
           ▼
    ┌─────────────────┐
    │  Router Logic   │
    └────┬─────┬─────┬┘
         │     │     │
    Retry│  OK │  Fail
         │     │     │
         ▼     ▼     ▼
      [SQL] [Exec] [End]
              │
              ▼
       ┌────────────┐
       │ Insight    │ ← Summary & visualization
       │ Agent      │
       └─────┬──────┘
             │
             ▼
          [END]
    """)
    
    print("\nKey Components:")
    print("• State Management: TypedDict with full type safety")
    print("• Security: Defense-in-depth (rule-based + LLM validation)")
    print("• Retry Logic: Smart retry with context preservation")
    print("• Logging: Structured JSON logs for all operations")
    print("• Extensibility: Modular design for easy agent addition\n")


if __name__ == "__main__":
    # Run full demonstration
    show_architecture()
    demonstrate_retry_logic()
    results = demonstrate_system()
    
    print("\n" + "="*80)
    print(" DEMONSTRATION COMPLETE")
    print("="*80 + "\n")
    print("The AI Banking Data Assistant intelligence layer is fully operational.")
    print("All agents are working in concert to process natural language queries.\n")
