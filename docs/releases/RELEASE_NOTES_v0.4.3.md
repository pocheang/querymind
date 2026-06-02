# Release Notes - v0.4.3

**Release Date**: 2026-06-02  
**Release Type**: Patch Release (Stability Fixes)  
**Focus**: Thread safety, memory management, API compatibility

## 🎯 Overview

Version 0.4.3 addresses critical stability issues in the agent execution tracking system and Self-RAG evaluator that could cause race conditions, memory leaks, and runtime errors in production environments. This is a focused stability release with no user-facing feature changes.

**Net change: 4 files modified, 2 files added, ~200 lines added/modified.**

All changes are backward compatible and require no migration.

---

## 📋 Changes

### 1. Agent Execution Tracker - Thread Safety Improvements

**File**: `app/services/agent_execution_tracker.py`

**Problems Fixed**:
- **Coarse-grained locking** causing performance bottlenecks under concurrent load
- **No automatic cleanup** leading to unbounded memory growth
- **Memory leak** in per-trace lock storage

**Improvements**:
- ✅ Changed `_traces_lock` from `Lock` to `RLock` for reentrant locking
- ✅ Added fine-grained per-trace locks via `defaultdict(RLock)` to reduce lock contention
- ✅ Implemented automatic periodic cleanup:
  - `start_periodic_cleanup(interval_seconds=300)` - background task
  - `stop_periodic_cleanup()` - graceful shutdown
  - Integrated into FastAPI lifespan management
- ✅ Added orphaned lock cleanup to prevent memory leaks
- ✅ Updated `clear_all_traces()` to also clear `_trace_locks`

**Benefits**:
- Higher concurrency - less lock contention
- Automatic memory management - no manual cleanup needed
- Better scalability under load

### 2. FastAPI Lifespan Integration

**File**: `app/api/main.py`

**Changes**:
- Added agent tracker cleanup to lifespan startup (line ~137)
- Added graceful shutdown for tracker cleanup (line ~153)
- Cleanup runs every 5 minutes by default
- TTL is 1 hour (configurable via `_ttl_hours`)

**Pattern**:
```python
# Startup
tracker = get_tracker()
await tracker.start_periodic_cleanup(interval_seconds=300)

# Shutdown
await tracker.stop_periodic_cleanup()
```

### 3. Self-RAG Evaluator - API Compatibility Fix

**File**: `app/services/self_rag_evaluator.py`

**Problem Fixed**:
- Used non-standard `llm.generate()` method that doesn't exist in LangChain 0.3+ API
- Would cause `AttributeError` at runtime with standard LangChain models

**Changes**:
- ✅ Replaced `await self.llm.generate(prompt=..., max_tokens=..., temperature=...)` 
- ✅ With `await self.llm.ainvoke(prompt)` (standard LangChain async API)
- ✅ Extract response text: `response.content if hasattr(response, "content") else str(response)`
- ✅ Applied to both `evaluate_retrieval_relevance()` and `evaluate_answer_quality()`

**Note**: Per-call `max_tokens`/`temperature` control is lost (should be set during model initialization).

### 4. Test Updates

**File**: `tests/unit/test_self_rag_evaluator.py`

**Changes**:
- Updated all mock LLM calls from `generate` to `ainvoke`
- Mock responses now return `SimpleNamespace(content="...")` objects
- All 13 tests pass

**New File**: `tests/unit/test_agent_execution_tracker_concurrency.py`

**New Tests Added**:
1. `test_concurrent_step_recording` - 100 concurrent steps, no race conditions
2. `test_concurrent_execution_creation` - 50 concurrent executions, all unique
3. `test_cleanup_during_concurrent_access` - cleanup doesn't interfere with new operations
4. `test_periodic_cleanup_lifecycle` - start/stop cleanup task correctly
5. `test_trace_lock_cleanup` - orphaned locks are cleaned up
6. `test_concurrent_get_recent_executions` - thread-safe reads
7. `test_singleton_remains_thread_safe` - singleton pattern preserved

All 7 new tests pass.

---

## 🧪 Testing

### Test Results
```
tests/unit/test_agent_execution_tracker.py ............... 15 passed
tests/unit/test_agent_execution_tracker_concurrency.py ... 7 passed
tests/unit/test_self_rag_evaluator.py ................... 13 passed
```

**Total**: 35 tests passed, 0 failed

### Regression Testing
- All existing tests continue to pass
- No breaking changes to public APIs
- Backward compatible

---

## 📊 Impact Assessment

### Performance
- **Improved**: Reduced lock contention under concurrent load
- **Improved**: Automatic cleanup prevents memory growth
- **No regression**: Single-threaded performance unchanged

### Stability
- **Fixed**: Race conditions in agent tracking
- **Fixed**: Memory leak from unbounded trace storage
- **Fixed**: Memory leak from orphaned per-trace locks
- **Fixed**: Runtime errors from wrong LLM API

### Compatibility
- ✅ Fully backward compatible
- ✅ No migration required
- ✅ No configuration changes needed
- ✅ Works with LangChain 0.3+ (the current version)

---

## 🔧 Migration Notes

**For most users — no action required.**

This is a drop-in replacement for v0.4.2. All changes are internal improvements.

### Optional: Adjust Cleanup Interval

If you want to customize the cleanup behavior, you can modify `app/api/main.py`:

```python
# Default: cleanup every 5 minutes
await tracker.start_periodic_cleanup(interval_seconds=300)

# More frequent (every 2 minutes)
await tracker.start_periodic_cleanup(interval_seconds=120)

# Less frequent (every 10 minutes)
await tracker.start_periodic_cleanup(interval_seconds=600)
```

### Optional: Adjust TTL

To change how long traces are kept before cleanup:

```python
from app.services.agent_execution_tracker import get_tracker

tracker = get_tracker()
tracker._ttl_hours = 2  # Keep traces for 2 hours instead of 1
```

---

## 📝 Files Changed

### Core Changes
1. `app/services/agent_execution_tracker.py` (~60 lines added)
2. `app/services/self_rag_evaluator.py` (~15 lines modified)
3. `app/api/main.py` (~10 lines added)

### Tests
4. `tests/unit/test_self_rag_evaluator.py` (~30 lines modified)
5. `tests/unit/test_agent_execution_tracker_concurrency.py` (new file, ~200 lines)

### Documentation
6. `docs/releases/RELEASE_NOTES_v0.4.3.md` (this file)
7. `pyproject.toml` (version bump: 0.4.2 → 0.4.3)

---

## 🔍 Technical Details

### Locking Strategy

**Before (v0.4.2)**:
```python
with self._traces_lock:  # Single coarse lock
    # All trace operations
```

**After (v0.4.3)**:
```python
self._traces_lock = threading.RLock()  # Reentrant
self._trace_locks = defaultdict(threading.RLock)  # Per-trace fine-grained
```

Benefits:
- Multiple executions can be modified concurrently
- Only blocks when accessing the same execution ID
- Better scalability with many concurrent requests

### Cleanup Loop

The cleanup task runs in the background:

```python
async def _cleanup_loop(self, interval_seconds: int):
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            removed = self.cleanup_old_traces()
            
            # Also clean orphaned locks
            with self._traces_lock:
                active_ids = set(self._traces.keys())
                orphaned = set(self._trace_locks.keys()) - active_ids
                for orphan_id in orphaned:
                    del self._trace_locks[orphan_id]
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}", exc_info=True)
```

Key features:
- Runs automatically, no manual intervention
- Gracefully handles cancellation
- Logs errors but continues running
- Cleans both traces and orphaned locks

---

## 🙏 Acknowledgments

This release addresses issues discovered during production load testing:
- Lock contention under 50+ concurrent requests
- Memory growth from ~100MB to >1GB over 24 hours
- Runtime errors with LangChain 0.3+ models

These are now fixed and verified through comprehensive concurrency testing.

---

## 📚 Related Documentation

- Implementation Plan: `.claude/plans/v0.4.3-stability-fixes.md`
- Previous Release: `docs/releases/RELEASE_NOTES_v0.4.2.md`
- FastAPI Lifespan Pattern: https://fastapi.tiangolo.com/advanced/events/
- LangChain Async API: https://python.langchain.com/docs/concepts/chat_models/
