# Changelog

All notable changes to this project will be documented in this file.

## [0.4.3] - 2026-06-02

### 🛡️ Stability Fixes Release

This release addresses critical stability issues in agent execution tracking
and Self-RAG evaluator. **Net change: 7 files, +574 / −28 lines (net +546).**
Focus on thread safety, memory management, and API compatibility.

See [docs/releases/RELEASE_NOTES_v0.4.3.md](./docs/releases/RELEASE_NOTES_v0.4.3.md)
for the full breakdown.

#### Fixed

- **Agent Execution Tracker thread safety**: Replaced coarse-grained locking
  with fine-grained per-trace RLocks, reducing lock contention under
  concurrent load.
- **Memory leak prevention**: Implemented automatic periodic cleanup task
  (5-minute interval, 1-hour TTL) integrated into FastAPI lifespan.
- **Orphaned lock cleanup**: Added cleanup logic to prevent memory growth
  from unused per-trace locks.
- **Self-RAG Evaluator API compatibility**: Fixed `llm.generate()` calls
  to use standard LangChain 0.3+ `ainvoke()` API.

#### Added

- **Comprehensive concurrency tests**: 7 new tests verifying thread safety
  under 100+ concurrent operations, cleanup lifecycle, and singleton pattern.
- **Automatic cleanup scheduling**: `start_periodic_cleanup()` and
  `stop_periodic_cleanup()` methods with graceful shutdown support.

#### Changed

- **`_traces_lock` upgraded** from `Lock` to `RLock` for reentrant locking.
- **`clear_all_traces()` now cleans** both traces and per-trace locks.
- **FastAPI lifespan hook** now manages agent tracker cleanup automatically.

#### Performance Impact

- ⬆️ Improved: Better concurrency under high load
- ✅ Fixed: Unbounded memory growth
- ✅ Fixed: LangChain API compatibility errors

## [0.4.2] - 2026-05-22

### 🛡️ Hardening & Hygiene Release

This release is a focused hardening pass on v0.4.1. No user-facing
features. **Net change: 18 files, +471 / −742 lines (net −271).**
Five focused, independently reviewable commits.

See [docs/releases/RELEASE_NOTES_v0.4.2.md](./docs/releases/RELEASE_NOTES_v0.4.2.md)
for the full breakdown.

#### Removed

- `app/api/routes/admin_users.py.backup` (375 lines of accidentally
  committed scratch text).
- `app/services/auth.py` (135 lines of dead code shadowed by the
  `app/services/auth/` subpackage; verified at runtime never to load).
- `pytest.ini` and `.coveragerc` (settings consolidated into
  `pyproject.toml`).
- The `_xxx_wrapper` indirection pattern in `app/api/dependencies.py`:
  10 helpers collapsed from three declarations each to one.

#### Changed

- **FastAPI lifecycle**: `@app.on_event("startup"/"shutdown")` →
  `lifespan` async context manager.
- **`_ROUTE_MODULES` tuple now includes** five recently added route
  modules (`admin_language_stats`, `agent_tracking`, `evaluation`,
  `advanced_rag`, `analytics`), preventing silent monkeypatch
  failures.
- **9 silent-failure paths now log warnings** (Redis cache get/set,
  inflight lock/clear/check, stream replay, vector store collection
  reset, Neo4j client init, LLM triplet fallback, OCR upscale).
- **`datetime.utcnow()` → `datetime.now(timezone.utc)`** in
  `admin_token_tracker.py` (Python 3.12+ compatibility).
- **Heavy ML/OCR stacks moved to optional extras** (`[ocr]`,
  `[paddle]`, `[docling]`, `[reranker]`, `[full]`). Core install is
  now ~2GB lighter.
- **`pyproject.toml` consolidates** tooling config:
  `[tool.pytest.ini_options]`, `[tool.coverage.*]`, `[tool.ruff]`.

#### Added

- **`_configure_cors(app, settings)`** with production wildcard
  refusal: when `APP_ENV` is `prod` / `production` and
  `CORS_ALLOW_ORIGINS` includes `*`, startup fails with a clear error.
- **`_audit_detail(**fields)`** helper in `admin_users.py`: admin
  audit details for `create_admin`, `reset_password`,
  `reset_approval_token` are now JSON-serialized so user-supplied
  `reason` values cannot break parsing.
- **`tests/test_cors_prod_guard.py`** (5 unit tests) for the CORS
  production guard.
- **README "Optional extras" install block** documenting each extra.

#### Fixed

- **Latent `NameError` on three admin endpoints**: the call to
  `validate_and_check_approval_token()` returns `tuple[bool, str]`
  but the result was being discarded while the next f-string
  referenced `token_mode`. Now captures the tuple. The bug never
  fired in practice because all covering tests mock the validator.

#### Migration

| If you... | Action |
|-----------|--------|
| Run with default config | Nothing required |
| Have `APP_ENV=prod` and `CORS_ALLOW_ORIGINS=*` | Replace `*` with explicit https origins |
| Parse audit `detail` for admin endpoints | Switch to `json.loads(detail)` |
| Need OCR / reranker / Docling | Install with `pip install -e ".[full]"` or pick a subset |

---

## [0.4.1] - 2026-05-20

### 🎯 Major Refactoring - Code Quality Improvements

This release focuses on eliminating code duplication and improving maintainability across the entire codebase. **Net reduction: ~2,700 lines of code** while maintaining 100% functionality.

#### Frontend Refactoring (6 commits, ~2,400 lines removed)

**New Reusable Modules Created:**
- `frontend/src/lib/api-helpers.ts` - Unified API request builders
- `frontend/src/lib/validation.ts` - Shared validation utilities
- `frontend/src/lib/file-utils.ts` - File download and timestamp utilities
- `frontend/src/lib/string-utils.ts` - String normalization helpers
- `frontend/src/lib/async-utils.ts` - Async operation wrappers
- `frontend/src/lib/hooks/useCopyToClipboard.ts` - Unified clipboard operations
- `frontend/src/lib/hooks/useAsyncAction.ts` - Standardized async error handling
- `frontend/src/lib/hooks/useAsyncState.ts` - Async state management
- `frontend/src/lib/hooks/useConfirmDialog.ts` - Confirmation dialog logic
- `frontend/src/components/AdminFormField.tsx` - Unified form field component
- `frontend/src/components/ConfirmDialog.tsx` - Reusable confirmation dialog

**Files Refactored:**
- Unified API clients: admin-user-api, admin-ops-api, admin-audit-api, admin-system-log-api, session-api, document-api, prompt-api
- Admin components: AdminCreateForm, AdminSystemLogTable, AdminAuditLogManagement, AdminModelSettings
- Admin actions: auditActions, opsActions, userActions
- Chat components: CodeBlock, MarkdownBlock

**Cleanup:**
- Removed 3,562 lines of backup CSS files
- Deleted obsolete UI components
- Consolidated duplicate form patterns

#### Backend Refactoring (8 commits, ~300 lines removed)

**New Utility Modules Created:**
- `app/api/utils/error_responses.py` - Standardized error responses (9 functions)
- `app/api/utils/request_helpers.py` - Request parameter extraction
- `app/api/utils/string_utils.py` - String normalization utilities
- `app/api/utils/token_utils.py` - Token hashing utilities

**Major Changes:**
- Consolidated duplicate admin_users.py files (eliminated 480 lines)
- Replaced 60+ inline HTTPException instances with standardized error functions
- Replaced 50+ inline string normalization patterns with normalize_string()
- Extracted approval token validation logic to admin_security.py

**Files Refactored:**
- Routes: auth, query, documents, sessions, agent_tracking, evaluation, advanced_rag, admin_settings, admin_ops, prompts, admin_users
- Services: admin_security, adaptive_rag_policy, history, log_buffer, model_config_store, network_security, query_intent, retrieval_profiles, runtime_ops
- Tools: graph_tools
- Core: models, dependencies
- Agents: router_agent, synthesis_agent

### 🐛 Bug Fixes

- Fixed unauthorized() function to return correct 401 status code
- Fixed TypeScript errors in frontend build
- Corrected RetrievalLog field names
- Fixed detected_language metadata in streaming response

### 📊 Features

**Multilingual Support:**
- Language detection module with 20% Chinese threshold
- Integrated language detection into synthesis agent
- Added force_language parameter to query API
- Session language preference tracking
- Language usage analytics and admin endpoint
- Comprehensive multilingual end-to-end tests

**Monitoring & Analytics:**
- RetrievalLogger service with statistics and export
- Analytics API with 4 endpoints
- Retrieval logging in vector and graph handlers
- AnalyticsPage with Recharts visualizations
- Analytics integrated into admin navigation

**Security Documentation:**
- Comprehensive security documentation design
- Application security documentation for RAG systems
- Infrastructure security documentation

### 📈 Statistics

**Code Reduction:**
- Frontend: -2,400 lines (net)
- Backend: -300 lines (net)
- Total: -2,700 lines (net)
- Backup files removed: -3,562 lines

**New Modules:**
- Frontend: 11 reusable modules
- Backend: 8 utility modules
- Total: 19 new reusable modules

**Commits:**
- Total: 14 commits
- Frontend refactoring: 6 commits
- Backend refactoring: 8 commits

**Files Changed:**
- 110 files modified
- 3,960 insertions
- 6,219 deletions

### 🔧 Technical Improvements

**Code Quality:**
- Eliminated duplicate API request patterns
- Standardized error handling across all routes
- Unified string normalization logic
- Consolidated form field components
- Extracted shared hooks and utilities

**Maintainability:**
- Centralized error responses for consistency
- Reduced cognitive load with reusable components
- Improved code discoverability
- Better separation of concerns

**Developer Experience:**
- Clearer code organization
- Easier to add new features
- Reduced boilerplate code
- Better type safety

---

## [0.3.3] - Previous Release

(Previous changelog entries...)
