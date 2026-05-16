"""
Agent Execution Tracking Demo

This example demonstrates how to use the agent execution tracking system
to monitor and visualize multi-agent workflow execution in real-time.
"""

import time
from app.services.agent_execution_tracker import get_tracker
from app.graph.workflow import run_query


def demo_basic_tracking():
    """Demonstrate basic execution tracking."""
    print("=== Basic Execution Tracking Demo ===\n")

    tracker = get_tracker()

    # Run a query with tracking enabled (default)
    print("Running query: 'What are the main features of this RAG system?'")
    result = run_query(
        question="What are the main features of this RAG system?",
        enable_tracking=True
    )

    # Get the execution ID from the result
    execution_id = result.get("execution_id")

    if execution_id:
        print(f"\nExecution ID: {execution_id}")

        # Retrieve the execution trace
        trace = tracker.get_execution(execution_id)

        if trace:
            print(f"\nExecution Status: {trace.status}")
            print(f"Total Steps: {len(trace.steps)}")
            print(f"Start Time: {trace.start_time}")
            print(f"End Time: {trace.end_time}")

            if trace.end_time and trace.start_time:
                duration = (trace.end_time - trace.start_time).total_seconds()
                print(f"Total Duration: {duration:.2f}s")

            print("\nAgent Steps:")
            for i, step in enumerate(trace.steps, 1):
                status_symbol = "✓" if step.status == "completed" else "✗" if step.status == "failed" else "..."
                print(f"  {i}. [{status_symbol}] {step.agent_name}")
                if step.duration_seconds:
                    print(f"     Duration: {step.duration_seconds:.2f}s")
                if step.error:
                    print(f"     Error: {step.error}")
    else:
        print("\nNo execution ID found in result")


def demo_multiple_executions():
    """Demonstrate tracking multiple executions."""
    print("\n\n=== Multiple Executions Demo ===\n")

    tracker = get_tracker()

    queries = [
        "What is RAG?",
        "How does vector search work?",
        "Explain hybrid retrieval"
    ]

    execution_ids = []

    for query in queries:
        print(f"Running: {query}")
        result = run_query(question=query, enable_tracking=True)
        execution_id = result.get("execution_id")
        if execution_id:
            execution_ids.append(execution_id)

    print(f"\nCompleted {len(execution_ids)} executions")

    # List all recent executions
    recent = tracker.list_recent_executions(limit=5)
    print(f"\nRecent executions: {len(recent)}")

    for trace in recent:
        print(f"\n  ID: {trace.execution_id[:8]}...")
        print(f"  Query: {trace.query}")
        print(f"  Status: {trace.status}")
        print(f"  Steps: {len(trace.steps)}")


def demo_execution_comparison():
    """Compare execution traces across different queries."""
    print("\n\n=== Execution Comparison Demo ===\n")

    tracker = get_tracker()

    # Run two different types of queries
    print("Running simple query...")
    result1 = run_query(
        question="What is the capital of France?",
        enable_tracking=True
    )

    print("Running complex query...")
    result2 = run_query(
        question="Compare the performance characteristics of vector search vs hybrid search",
        use_web_fallback=True,
        enable_tracking=True
    )

    exec_id1 = result1.get("execution_id")
    exec_id2 = result2.get("execution_id")

    if exec_id1 and exec_id2:
        trace1 = tracker.get_execution(exec_id1)
        trace2 = tracker.get_execution(exec_id2)

        print("\nComparison:")
        print(f"\nSimple Query:")
        print(f"  Steps: {len(trace1.steps)}")
        if trace1.end_time and trace1.start_time:
            duration1 = (trace1.end_time - trace1.start_time).total_seconds()
            print(f"  Duration: {duration1:.2f}s")

        print(f"\nComplex Query:")
        print(f"  Steps: {len(trace2.steps)}")
        if trace2.end_time and trace2.start_time:
            duration2 = (trace2.end_time - trace2.start_time).total_seconds()
            print(f"  Duration: {duration2:.2f}s")

        print("\nAgent execution paths:")
        print(f"  Simple: {' -> '.join(s.agent_name for s in trace1.steps)}")
        print(f"  Complex: {' -> '.join(s.agent_name for s in trace2.steps)}")


def demo_api_usage():
    """Demonstrate how to use the tracking API endpoints."""
    print("\n\n=== API Usage Demo ===\n")

    print("The agent tracking system provides the following API endpoints:")
    print("\n1. GET /api/agent-tracking/executions/{execution_id}")
    print("   - Retrieve a specific execution trace")

    print("\n2. GET /api/agent-tracking/executions/{execution_id}/stream")
    print("   - Stream real-time updates via Server-Sent Events (SSE)")
    print("   - Example client code:")
    print("""
    const eventSource = new EventSource(
        `/api/agent-tracking/executions/${executionId}/stream`
    );

    eventSource.onmessage = (event) => {
        const trace = JSON.parse(event.data);
        console.log('Execution update:', trace);
        // Update UI with new steps
    };
    """)

    print("\n3. GET /api/agent-tracking/executions")
    print("   - List recent executions")
    print("   - Query params: limit (default: 10)")

    print("\n4. DELETE /api/agent-tracking/executions/{execution_id}")
    print("   - Delete a specific execution trace")

    print("\n5. POST /api/agent-tracking/cleanup")
    print("   - Clean up old execution traces")
    print("   - Query params: hours_old (default: 24)")


if __name__ == "__main__":
    try:
        # Run all demos
        demo_basic_tracking()
        demo_multiple_executions()
        demo_execution_comparison()
        demo_api_usage()

        print("\n\n=== Demo Complete ===")
        print("\nNote: This demo uses mock data. In production, integrate with")
        print("your actual RAG workflow to see real execution traces.")

    except Exception as e:
        print(f"\nError running demo: {e}")
        print("\nMake sure you have:")
        print("1. Installed all dependencies")
        print("2. Set up your environment variables")
        print("3. Initialized the vector store")
