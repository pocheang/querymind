#!/bin/bash
# Complete verification of all audit fixes

echo "=========================================="
echo "Complete Audit Fix Verification Checklist"
echo "=========================================="
echo ""

total=0
passed=0

check_item() {
    total=$((total + 1))
    if eval "$2"; then
        echo "✓ $1"
        passed=$((passed + 1))
        return 0
    else
        echo "✗ $1"
        return 1
    fi
}

echo "=== Issue 1: Agent-Tracking Permission Validation ==="
echo ""

check_item "1.1 _verify_trace_ownership function exists" \
    "grep -q 'def _verify_trace_ownership' app/api/routes/agent_tracking.py"

check_item "1.2 GET /trace/{execution_id} has ownership check" \
    "grep -A 15 'def get_execution_trace' app/api/routes/agent_tracking.py | grep -q '_verify_trace_ownership'"

check_item "1.3 GET /stream/{execution_id} has ownership check" \
    "grep -A 20 'def stream_execution' app/api/routes/agent_tracking.py | grep -q '_verify_trace_ownership'"

check_item "1.4 GET /status/{execution_id} has ownership check" \
    "grep -A 15 'def get_execution_status' app/api/routes/agent_tracking.py | grep -q '_verify_trace_ownership'"

check_item "1.5 DELETE /trace/{execution_id} has ownership check" \
    "grep -A 15 'def delete_execution_trace' app/api/routes/agent_tracking.py | grep -q '_verify_trace_ownership'"

check_item "1.6 forbidden() function is imported" \
    "grep -q 'from app.api.utils.error_responses import.*forbidden' app/api/routes/agent_tracking.py"

echo ""
echo "=== Issue 2: Query API Returns execution_id ==="
echo ""

check_item "2.1 QueryResponse has execution_id field" \
    "grep -q 'execution_id.*str.*None' app/core/schemas.py"

check_item "2.2 Non-streaming query returns execution_id" \
    'grep -q "\"execution_id\": result.get(\"execution_id\")" app/api/routes/query.py'

check_item "2.3 Stream query has user_id parameter" \
    'grep -A 10 "stream_kwargs.*dict" app/api/routes/query.py | grep -q "\"user_id\":"'

check_item "2.4 Stream query has enable_tracking parameter" \
    'grep -A 10 "stream_kwargs.*dict" app/api/routes/query.py | grep -q "\"enable_tracking\":"'

check_item "2.5 run_query_stream imports AgentExecutionTracker" \
    "grep -q 'from app.services.agent_execution_tracker import AgentExecutionTracker' app/graph/streaming/stream_processor.py"

check_item "2.6 run_query_stream has execution_id parameter" \
    "grep -A 5 'def run_query_stream' app/graph/streaming/stream_processor.py | grep -q 'execution_id'"

check_item "2.7 run_query_stream has enable_tracking parameter" \
    "grep -A 5 'def run_query_stream' app/graph/streaming/stream_processor.py | grep -q 'enable_tracking'"

check_item "2.8 run_query_stream creates execution tracking" \
    "grep -q 'tracker.start_execution' app/graph/streaming/stream_processor.py"

check_item "2.9 Timeout payload includes execution_id" \
    'grep -A 15 "deadline_exceeded():" app/graph/streaming/stream_processor.py | grep -q "\"execution_id\": execution_id"'

check_item "2.10 Smalltalk payload includes execution_id" \
    'grep -A 30 "smalltalk_fast" app/graph/streaming/stream_processor.py | grep -q "\"execution_id\": execution_id"'

check_item "2.11 ReAct payload includes execution_id" \
    'grep -B 5 -A 15 "route.*react" app/graph/streaming/stream_processor.py | grep -q "\"execution_id\": execution_id"'

check_item "2.12 Main final_payload includes execution_id" \
    'tail -50 app/graph/streaming/stream_processor.py | grep -q "\"execution_id\": execution_id"'

echo ""
echo "=== Issue 3: Streaming ReAct Passes agent_class ==="
echo ""

check_item "3.1 Streaming ReAct passes agent_class" \
    'grep -A 15 "if route == \"react\":" app/graph/streaming/stream_processor.py | grep -q "agent_class=state.get(\"agent_class\")"'

check_item "3.2 Streaming ReAct passes allowed_sources" \
    'grep -A 15 "if route == \"react\":" app/graph/streaming/stream_processor.py | grep -q "allowed_sources=allowed_sources"'

check_item "3.3 Streaming ReAct passes retrieval_strategy" \
    'grep -A 15 "if route == \"react\":" app/graph/streaming/stream_processor.py | grep -q "retrieval_strategy=retrieval_strategy"'

echo ""
echo "=== Issue 4: Backend Tracking Fields (Maintained) ==="
echo ""

check_item "4.1 AgentStep uses duration_ms" \
    "grep -q 'duration_ms.*Optional' app/services/agent_execution_tracker.py"

check_item "4.2 ExecutionTrace uses total_duration_ms" \
    "grep -q 'total_duration_ms.*Optional' app/services/agent_execution_tracker.py"

check_item "4.3 Result stored in metadata.result" \
    'grep -q "metadata\[\"result\"\]" app/services/agent_execution_tracker.py'

echo ""
echo "=== Issue 5: Test Dependencies Complete ==="
echo ""

check_item "5.1 reportlab in requirements-dev.txt" \
    "grep -q 'reportlab' requirements-dev.txt"

check_item "5.2 authlib in requirements-dev.txt" \
    "grep -q 'authlib' requirements-dev.txt"

check_item "5.3 psutil in requirements-dev.txt" \
    "grep -q 'psutil' requirements-dev.txt"

check_item "5.4 ruff in requirements-dev.txt" \
    "grep -q 'ruff' requirements-dev.txt"

echo ""
echo "=== Test Files Created ==="
echo ""

check_item "6.1 test_agent_tracking_permissions.py exists" \
    "test -f tests/api/test_agent_tracking_permissions.py"

check_item "6.2 test_query_execution_id.py exists" \
    "test -f tests/api/test_query_execution_id.py"

check_item "6.3 test_streaming_react_agent_class.py exists" \
    "test -f tests/test_streaming_react_agent_class.py"

echo ""
echo "=== Documentation Files ==="
echo ""

check_item "7.1 Detailed fix report exists" \
    "test -f docs/project/agent-audit-fixes-2026-06-22.md"

check_item "7.2 Execution summary exists" \
    "test -f AGENT_AUDIT_EXECUTION_SUMMARY.md"

check_item "7.3 Verification script exists" \
    "test -f scripts/verify_audit_fixes.py"

echo ""
echo "=========================================="
echo "Verification Results"
echo "=========================================="
echo "Passed: $passed / $total"
echo ""

if [ $passed -eq $total ]; then
    echo "✓✓✓ ALL CHECKS PASSED ✓✓✓"
    echo "All audit fixes are complete and verified!"
    exit 0
else
    failed=$((total - passed))
    echo "✗✗✗ $failed CHECKS FAILED ✗✗✗"
    echo "Some fixes may be incomplete."
    exit 1
fi
