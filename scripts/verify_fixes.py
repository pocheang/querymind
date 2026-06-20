import sys
sys.path.insert(0, '.')

# Test imports of all fixed modules
print('Testing imports of fixed modules...')
try:
    from app.services.rate_limiter import SlidingWindowLimiter
    print('[OK] rate_limiter.py')

    from app.services.bulkhead import bulkhead, BulkheadRejectedError
    print('[OK] bulkhead.py')

    from app.services.auth.auth_service import AuthDBService
    print('[OK] auth_service.py')

    from app.services.query_guard import QueryLoadGuard
    print('[OK] query_guard.py')

    from app.services.quota_guard import QuotaGuard
    print('[OK] quota_guard.py')

    from app.services.request_context import request_context, deadline_exceeded
    print('[OK] request_context.py')

    from app.api.middleware import request_timing_middleware
    print('[OK] middleware.py')

    from app.core.config import get_settings
    print('[OK] config.py')

    from app.graph.workflow import run_query, build_workflow
    print('[OK] workflow.py')

    from app.api.utils.query_helpers import handle_pdf_agent_routing
    print('[OK] query_helpers.py')

    print('\n[SUCCESS] All imports successful!')

    # Test new methods exist
    limiter = SlidingWindowLimiter(max_attempts=5, window_seconds=60)
    assert hasattr(limiter, 'try_acquire'), 'try_acquire method missing'
    print('[OK] try_acquire method exists')

    print('\n[COMPLETE] All verifications passed!')

except Exception as e:
    print(f'\n[ERROR] Import failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
