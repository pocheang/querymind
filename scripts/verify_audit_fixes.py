"""Quick verification script - verify audit fix core functionality"""

import sys
import traceback

def test_imports():
    """Test all critical imports work"""
    print("Test 1: Verify imports...")
    try:
        from app.api.routes.agent_tracking import _verify_trace_ownership
        from app.core.schemas import QueryResponse
        from app.graph.streaming.stream_processor import run_query_stream
        from app.services.agent_execution_tracker import AgentExecutionTracker
        print("  PASS: All imports successful")
        return True
    except Exception as e:
        print(f"  FAIL: Import failed: {e}")
        traceback.print_exc()
        return False


def test_query_response_schema():
    """Test QueryResponse includes execution_id"""
    print("\nTest 2: Verify QueryResponse schema...")
    try:
        from app.core.schemas import QueryResponse

        # Test creating response with execution_id
        response = QueryResponse(
            answer="test",
            route="vector",
            execution_id="test-exec-123"
        )
        assert response.execution_id == "test-exec-123"

        # Test without execution_id (backward compatibility)
        response2 = QueryResponse(
            answer="test",
            route="vector"
        )
        assert response2.execution_id is None

        print("  PASS: QueryResponse schema correctly includes execution_id")
        return True
    except Exception as e:
        print(f"  FAIL: Schema test failed: {e}")
        traceback.print_exc()
        return False


def test_tracker_user_id():
    """Test tracker supports user_id"""
    print("\nTest 3: Verify ExecutionTracker user_id support...")
    try:
        from app.services.agent_execution_tracker import AgentExecutionTracker

        tracker = AgentExecutionTracker.get_instance()
        tracker.clear_all_traces()

        # Create trace with user_id
        exec_id = tracker.start_execution("test query", user_id="user-123")
        trace = tracker.get_execution_trace(exec_id)

        assert trace is not None
        assert trace.user_id == "user-123"
        assert trace.query == "test query"

        tracker.clear_all_traces()
        print("  PASS: ExecutionTracker correctly supports user_id")
        return True
    except Exception as e:
        print(f"  FAIL: Tracker test failed: {e}")
        traceback.print_exc()
        return False


def test_verify_ownership_function():
    """Test ownership verification function exists and works"""
    print("\nTest 4: Verify ownership verification function...")
    try:
        from app.api.routes.agent_tracking import _verify_trace_ownership
        from app.services.agent_execution_tracker import ExecutionTrace, AgentExecutionTracker
        from app.api.utils.error_responses import forbidden

        tracker = AgentExecutionTracker.get_instance()
        tracker.clear_all_traces()

        # Create a trace
        exec_id = tracker.start_execution("test", user_id="user-456")
        trace = tracker.get_execution_trace(exec_id)

        # Test admin can access
        admin_user = {"user_id": "admin-123", "role": "admin"}
        try:
            _verify_trace_ownership(trace, admin_user)
            print("  PASS: Admin can access any trace")
        except:
            print("  FAIL: Admin access failed")
            tracker.clear_all_traces()
            return False

        # Test user can access their own
        owner_user = {"user_id": "user-456", "role": "viewer"}
        try:
            _verify_trace_ownership(trace, owner_user)
            print("  PASS: User can access their own trace")
        except:
            print("  FAIL: User access to own trace failed")
            tracker.clear_all_traces()
            return False

        # Test user cannot access others'
        other_user = {"user_id": "user-789", "role": "viewer"}
        try:
            _verify_trace_ownership(trace, other_user)
            print("  FAIL: User can access others' trace (security vulnerability!)")
            tracker.clear_all_traces()
            return False
        except Exception:
            print("  PASS: User cannot access others' trace")

        tracker.clear_all_traces()
        print("  PASS: Ownership verification function works correctly")
        return True
    except Exception as e:
        print(f"  FAIL: Ownership verification test failed: {e}")
        traceback.print_exc()
        return False


def test_stream_processor_signature():
    """Test run_query_stream signature includes new parameters"""
    print("\nTest 5: Verify run_query_stream signature...")
    try:
        from app.graph.streaming.stream_processor import run_query_stream
        import inspect

        sig = inspect.signature(run_query_stream)
        params = list(sig.parameters.keys())

        assert "execution_id" in params, "Missing execution_id parameter"
        assert "enable_tracking" in params, "Missing enable_tracking parameter"
        assert "user_id" in params, "Missing user_id parameter"

        print(f"  PASS: run_query_stream signature correct")
        print(f"    Parameters: {', '.join(params)}")
        return True
    except Exception as e:
        print(f"  FAIL: Signature test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all verification tests"""
    print("=" * 60)
    print("Audit Fix Verification Script")
    print("=" * 60)

    results = []
    results.append(("Import tests", test_imports()))
    results.append(("QueryResponse Schema", test_query_response_schema()))
    results.append(("ExecutionTracker user_id", test_tracker_user_id()))
    results.append(("Ownership verification", test_verify_ownership_function()))
    results.append(("run_query_stream signature", test_stream_processor_signature()))

    print("\n" + "=" * 60)
    print("Verification Results Summary")
    print("=" * 60)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{name:30s} {status}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print("\n" + "=" * 60)
    if passed == total:
        print(f"SUCCESS: All {total} verifications passed!")
        print("=" * 60)
        return 0
    else:
        print(f"FAILURE: {total - passed}/{total} verifications failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
