---
name: project-workflow-and-standards
description: Complete workflow, documentation organization, code standards, and project structure rules
metadata:
  type: project
  created: 2026-06-03
  priority: high
---

# Project Workflow and Standards

Complete guide for development workflow, documentation organization, code quality standards, and project structure.

**Last Updated**: 2026-06-03

---

## 📋 Development Workflow

### Phase 1: Planning
```
User Request/Idea
    ↓
Understand Requirements
    ↓
Create Planning Document → .claude/plans/[name].md
    ↓
Get User Approval
    ↓
Proceed to Implementation
```

**Planning Document Location**: `.claude/plans/`
- Naming: `v0.x.x-feature-name.md` or `feature-planning.md`
- Contents: Goals, approach, timeline, dependencies
- Status: Keep until implementation complete

### Phase 2: Implementation
```
Approved Plan
    ↓
Write Code → app/, scripts/, tests/
    ↓
Write Tests → tests/
    ↓
Write Documentation → docs/
    ↓
Test & Verify
    ↓
Get User Feedback
    ↓
Iterate if Needed
```

### Phase 3: Completion
```
Implementation Done
    ↓
Run Final Tests
    ↓
Create Summary → .claude/completed/YYYY-MM-DD-[task]-summary.md
    ↓
Update User Documentation → docs/
    ↓
Move Plan to Archive (optional)
    ↓
Task Complete ✅
```

**Completion Summary Location**: `.claude/completed/`
- Naming: `YYYY-MM-DD-[task-name]-summary.md`
- Contents: What was done, files changed, metrics, next steps
- Always include date prefix

---

## 📁 File Organization Rules

### 1. `.claude/` Directory (Internal)

#### `.claude/plans/` - Planning Documents
- **Purpose**: Future plans, design documents, proposals
- **Naming**: `feature-name-plan.md` or `v0.x.x-feature.md`
- **Status**: Active planning, not yet implemented
- **Examples**:
  - `v0.5.0-advanced-search.md`
  - `database-migration-plan.md`
  - `performance-optimization-proposal.md`

#### `.claude/completed/` - Completion Summaries
- **Purpose**: Record of completed work
- **Naming**: `YYYY-MM-DD-task-name-summary.md`
- **Must Include**:
  - Date prefix (YYYY-MM-DD)
  - What was accomplished
  - Files created/modified
  - Metrics/results
  - Next steps
- **Examples**:
  - `2026-06-03-v0.4.4-implementation-summary.md`
  - `2026-06-02-exception-handling-optimization.md`

#### `.claude/memory/` - Persistent Memory
- **Purpose**: Project knowledge, conventions, user preferences
- **Naming**: `topic-name.md`
- **Keep Updated**: Yes, these are living documents
- **Examples**:
  - `project-conventions.md`
  - `user-preferences.md`
  - `architecture-decisions.md`
  - `work-discipline-autonomous-action-control.md`

### 2. `docs/` Directory (User-Facing)

#### Public Documentation
- **Purpose**: User guides, API docs, tutorials
- **Audience**: End users, developers using the project
- **Examples**:
  - `README.md` - Project overview
  - `CHANGELOG.md` - Version history
  - `v0.4.4-implementation-guide.md` - Feature guides
  - `api-reference.md` - API documentation
  - `deployment-guide.md` - Deployment instructions

#### Subdirectories
```
docs/
├── README.md                    # Documentation hub
├── CHANGELOG.md                 # Version history
├── releases/                    # Release notes
│   └── v0.4.4-release-notes.md
├── design/                      # Feature designs
│   └── rag-optimization-design.md
├── archive/                     # Historical docs
│   ├── refactoring/
│   └── investigations/
├── development/                 # Dev guides
│   └── contributing.md
└── operations/                  # Ops guides
    └── deployment.md
```

### 3. Code Structure

#### `app/` - Application Code
```
app/
├── agents/              # Agent implementations
├── api/                 # API routes and handlers
│   ├── routes/         # Route modules
│   └── utils/          # API utilities
├── core/               # Core configuration
│   ├── config.py       # Settings management
│   └── models.py       # Core models
├── graph/              # LangGraph workflows
│   ├── nodes/          # Graph nodes
│   └── routing/        # Routing logic
├── ingestion/          # Document ingestion
│   ├── loaders/        # Document loaders
│   └── utils/          # Ingestion utilities
├── retrievers/         # Retrieval systems
│   └── hybrid/         # Hybrid retrieval modules
├── services/           # Business logic services
│   └── auth/           # Auth services
└── tools/              # Tool integrations
```

#### `scripts/` - Operational Scripts
```
scripts/
├── ingest.py           # Document ingestion
├── benchmark_pipeline.py
├── test_optimized_pipeline.py
└── dev/                # Developer scripts
    └── smoke_tests/
```

#### `tests/` - Test Suite
```
tests/
├── unit/               # Unit tests
├── integration/        # Integration tests
├── evaluation/         # RAG evaluation
└── fixtures/           # Test fixtures
```

---

## 💻 Code Quality Standards

### 1. File Length Limits

**IMPORTANT**: Keep files manageable and focused

| File Type | Max Lines | Recommended | Action if Exceeded |
|-----------|-----------|-------------|-------------------|
| Service/Module | 500 | 300-400 | Split into multiple files |
| API Route | 300 | 150-200 | Extract logic to services |
| Utility | 400 | 200-300 | Group related functions |
| Test File | 600 | 300-400 | Split by feature/component |
| Config | 300 | 150-200 | Use multiple config files |

**Signs a File is Too Long**:
- ❌ Scrolling required to see all code
- ❌ Multiple unrelated responsibilities
- ❌ Hard to find specific function
- ❌ Takes > 30 seconds to understand purpose

**How to Split Long Files**:

**Example 1: Large Service File**
```python
# BAD: services/rag_service.py (800 lines)
# Contains: retrieval, reranking, compression, generation

# GOOD: Split into modules
services/
├── retrieval_service.py      # 200 lines - retrieval logic
├── reranking_service.py      # 150 lines - reranking
├── compression_service.py    # 180 lines - compression
└── generation_service.py     # 220 lines - generation
```

**Example 2: Large Retriever**
```python
# BAD: retrievers/hybrid_retriever.py (600 lines)

# GOOD: Split into submodules
retrievers/
├── hybrid_retriever.py       # 150 lines - main interface
└── hybrid/
    ├── __init__.py
    ├── candidate_collection.py  # 200 lines
    ├── fusion.py                # 150 lines
    └── parent_expansion.py      # 120 lines
```

### 2. Function Length Limits

| Function Type | Max Lines | Recommended |
|---------------|-----------|-------------|
| Regular function | 50 | 20-30 |
| Complex algorithm | 80 | 40-50 |
| Simple utility | 20 | 5-15 |

**Rules**:
- If > 50 lines → Extract helper functions
- If > 3 levels of nesting → Refactor
- If hard to name → Probably doing too much

### 3. Code Organization Principles

#### Single Responsibility Principle (SRP)
```python
# BAD: One file does everything
class RAGSystem:
    def retrieve(self): ...       # Retrieval
    def rerank(self): ...         # Reranking
    def compress(self): ...       # Compression
    def generate(self): ...       # Generation
    def cache(self): ...          # Caching
    def monitor(self): ...        # Monitoring

# GOOD: Separate responsibilities
class Retriever:
    def retrieve(self): ...

class Reranker:
    def rerank(self): ...

class Compressor:
    def compress(self): ...

class Generator:
    def generate(self): ...
```

#### DRY (Don't Repeat Yourself)
```python
# BAD: Duplicated logic
def process_query_english(query): ...
def process_query_chinese(query): ...  # 90% same code

# GOOD: Shared logic
def process_query(query, language='auto'):
    language = detect_language(query) if language == 'auto' else language
    # Shared processing logic
    return process_with_language(query, language)
```

#### Clear Module Boundaries
```
✅ Good Structure:
app/retrievers/
├── vector_retriever.py      # Vector-specific logic
├── bm25_retriever.py        # BM25-specific logic
├── hybrid_retriever.py      # Combines both
└── multi_path_retriever.py  # Multi-path strategy

❌ Bad Structure:
app/retrievers/
└── retrievers.py            # Everything in one file (800+ lines)
```

### 4. Naming Conventions

#### Files
- **Modules**: `lowercase_with_underscores.py`
- **Classes**: Match primary class name: `MultiPathRetriever` → `multi_path_retriever.py`
- **Tests**: `test_` prefix: `test_hybrid_retriever.py`
- **Scripts**: Descriptive: `test_optimized_pipeline.py`

#### Code
```python
# Classes: PascalCase
class FastReranker:
    pass

# Functions/Variables: snake_case
def calculate_score():
    user_input = get_input()

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Private: leading underscore
def _internal_helper():
    pass
```

### 5. Documentation Standards

#### Module Docstrings
```python
"""
Module description in one line.

Longer description if needed explaining:
- What this module does
- When to use it
- Key dependencies

Example usage if helpful.
"""
```

#### Function Docstrings
```python
def retrieve(query: str, top_k: int = 10) -> list[dict]:
    """
    Retrieve documents matching the query.

    Args:
        query: Search query string
        top_k: Number of results to return

    Returns:
        List of document dictionaries with metadata

    Raises:
        ValueError: If query is empty
        TimeoutError: If retrieval exceeds timeout
    """
```

#### Class Docstrings
```python
class FastReranker:
    """
    Fast single-model reranker optimized for speed.

    Uses GPU acceleration and batching to rerank documents
    in under 200ms. Suitable for production RAG systems.

    Attributes:
        model_name: Name of the reranking model
        device: Device to use ('cuda' or 'cpu')
        batch_size: Batch size for inference

    Example:
        reranker = FastReranker()
        results, diag = reranker.rerank(query, docs, top_k=10)
    """
```

### 6. Import Organization

```python
"""Module docstring."""

# Standard library (alphabetical)
import asyncio
import logging
import time
from typing import Optional

# Third-party packages (alphabetical)
import numpy as np
from sentence_transformers import CrossEncoder

# Local imports (alphabetical)
from app.core.config import get_settings
from app.services.tracing import traced_span

# Module-level constants
logger = logging.getLogger(__name__)
MAX_RETRIES = 3
```

---

## 🏗️ Project Structure Principles

### 1. Modular Architecture

**Each module should**:
- ✅ Have a single, clear purpose
- ✅ Be independently testable
- ✅ Have minimal dependencies
- ✅ Export a clean API
- ✅ Be < 500 lines

### 2. Layered Architecture

```
┌─────────────────────────────────────┐
│     API Layer (FastAPI Routes)     │  ← User-facing
├─────────────────────────────────────┤
│     Service Layer (Business Logic) │  ← Orchestration
├─────────────────────────────────────┤
│     Domain Layer (Core Logic)      │  ← Domain models
├─────────────────────────────────────┤
│     Data Layer (Retrievers, DB)    │  ← Data access
└─────────────────────────────────────┘
```

**Rules**:
- API layer calls Service layer (not Data layer directly)
- Service layer orchestrates Domain and Data layers
- No circular dependencies

### 3. Configuration Management

```python
# app/core/config.py - Base settings
class Settings(BaseSettings):
    # Core settings
    pass

# app/core/optimized_config.py - Feature-specific settings
class OptimizedRAGSettings(BaseSettings):
    # Feature-specific settings
    pass

# Usage
from app.core.config import get_settings
from app.core.optimized_config import get_optimized_settings

settings = get_settings()
opt_settings = get_optimized_settings()
```

### 4. Feature Organization

**Option A: By Component Type** (Current)
```
app/
├── retrievers/        # All retrievers
├── services/          # All services
└── agents/            # All agents
```

**Option B: By Feature** (For large features)
```
app/
├── features/
│   ├── optimized_rag/
│   │   ├── __init__.py
│   │   ├── retriever.py
│   │   ├── reranker.py
│   │   ├── compressor.py
│   │   └── pipeline.py
│   └── graph_search/
│       └── ...
```

**When to use Feature-based**:
- Feature has 5+ related files
- Feature is relatively independent
- Team works on feature as a unit

---

## ✅ Quality Checklist

### Before Committing Code

- [ ] No file > 500 lines (split if needed)
- [ ] No function > 50 lines (extract if needed)
- [ ] All functions have docstrings
- [ ] Imports are organized
- [ ] No dead/commented code
- [ ] Error handling in place
- [ ] Logging added for key operations
- [ ] Type hints on function signatures
- [ ] Tests written and passing
- [ ] Documentation updated

### Before Completing Task

- [ ] All tests pass
- [ ] Documentation complete in `docs/`
- [ ] Summary created in `.claude/completed/`
- [ ] User can use the feature
- [ ] Performance meets targets
- [ ] Error cases handled
- [ ] Logging/monitoring in place

---

## 🔄 Refactoring Triggers

**Refactor When**:
1. File > 500 lines
2. Function > 50 lines
3. Duplicated code (3+ instances)
4. Hard to test
5. Hard to understand
6. Multiple responsibilities
7. Deep nesting (> 3 levels)

**Refactoring Patterns**:
- Extract Function
- Extract Class
- Extract Module
- Move to Subdirectory
- Split by Responsibility

---

## 📊 File Size Reference

**Current Good Examples**:
- `app/retrievers/fast_reranker.py` - 280 lines ✅
- `app/services/rule_compressor.py` - 350 lines ✅
- `app/services/adaptive_strategy.py` - 400 lines ✅

**Files That Should Be Split If They Grow**:
- Any service > 400 lines → Split into submodules
- Any retriever > 300 lines → Extract helpers
- Any API route > 200 lines → Extract to service

---

## 🎯 Summary

**Key Principles**:
1. 📋 Plans → `.claude/plans/`
2. ✅ Completed → `.claude/completed/` + date
3. 📚 User docs → `docs/`
4. 💻 Keep files < 500 lines
5. 🎯 Single responsibility per module
6. 📝 Document everything
7. 🧪 Test everything
8. 🔄 Refactor when needed

**Why This Matters**:
- ✅ Easy to find code
- ✅ Easy to understand
- ✅ Easy to maintain
- ✅ Easy to test
- ✅ Easy to extend
- ✅ Team can collaborate

---

**This is a living document. Update as standards evolve.**

Related: [[work-discipline-autonomous-action-control]]
