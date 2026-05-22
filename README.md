# Multi-Agent Local RAG

[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB.svg)](https://react.dev/)
[![Version](https://img.shields.io/badge/version-v0.4.1-blue.svg)](./docs/VERSION_HISTORY.md)

Enterprise-oriented, local-first RAG platform with multi-agent orchestration, hybrid retrieval, graph enhancement, admin governance, and streaming chat.

**Latest Release**: v0.4.1 (2026-05-20) - Code Quality Improvements: Eliminated ~2,700 lines of duplicate code, created 19 reusable modules, standardized error handling and API patterns across frontend and backend

This repository packages a FastAPI backend, a React frontend, and a modular retrieval pipeline designed for private knowledge bases, internal copilots, and controlled enterprise AI workflows.

## Executive Summary

- Multi-agent query orchestration built on LangGraph with intelligent routing
- Hybrid retrieval with vector search, BM25, reciprocal rank fusion, and reranking
- **Performance comparison framework** with baseline systems and comprehensive evaluation metrics
- **Agent execution visualization** with real-time tracking and SSE streaming
- **Chinese NLP optimization** with tokenization, synonym expansion, and query preprocessing
- **Advanced RAG techniques** including query decomposition and Self-RAG evaluation
- **Streaming PDF processing** with true streaming and 70% memory reduction for large documents
- **Batch chart extraction** with parallel processing for improved throughput
- **Modern UI design** with welcome screen, interactive architecture visualization, and optimized settings modal
- **Multilingual response support** with automatic language detection and session preferences
- **Retrieval analytics and monitoring** with visualization dashboard and statistics export
- Optional Neo4j knowledge graph enrichment for entity relationships
- Local-first document ingestion with OCR support (Tesseract) and image captioning
- Role-based access control (RBAC), session isolation, and comprehensive admin operations
- Runtime controls for retrieval profiles, canary routing, rollback, benchmarking, and replay
- Streaming chat UX with session history, prompt versioning, and memory management
- CI/CD quality gates with automated RAG evaluation and performance benchmarking
- Frontend performance optimization with critical CSS extraction and code splitting

## Target Use Cases

- Internal knowledge assistant for enterprise teams with secure document access
- Private document Q&A over PDF, image, and text corpora with OCR support
- RAG evaluation and retrieval strategy experimentation with benchmarking tools
- Controlled AI operations with auditability, rollback, and canary deployment
- Hybrid local and hosted model deployments (Ollama, OpenAI, Anthropic)
- Multi-hop reasoning with knowledge graph integration for complex queries
- Session-based conversational AI with memory and context management

## System Overview

### Core Components

- `app/api/`: FastAPI application with 10+ route modules, middleware, and dependencies
- `app/graph/`: LangGraph workflow orchestration, routing logic, and streaming helpers
- `app/agents/`: Router, retrieval, graph, web research, and synthesis agents
- `app/retrievers/`: Hybrid retrieval pipeline with vector, BM25, fusion, and reranking
- `app/services/`: Auth, runtime governance, caching, resilience, memory, and prompt management
- `app/ingestion/`: Document loaders, chunking strategies, OCR processing, and indexing
- `frontend/`: React + Vite user interface with TypeScript and modern CSS architecture
- `tests/`: Backend and workflow regression coverage (50+ test modules)
- `scripts/`: Operational tooling for ingestion, benchmarking, evaluation, and CI/CD
- `scripts/dev/`: Manual smoke and developer-driven verification scripts

### Request Flow

1. User authenticates via JWT-based auth system and starts or resumes a session.
2. Query enters the FastAPI layer where shared dependencies initialize request context.
3. LangGraph orchestrates the multi-agent workflow through specialized nodes:
   - **Router Agent**: Analyzes query intent and determines execution strategy
   - **Vector RAG Agent**: Performs hybrid retrieval (vector + BM25 + reranking)
   - **Graph RAG Agent**: Queries Neo4j for entity relationships and knowledge enrichment
   - **Web Research Agent**: Conducts web search when local knowledge is insufficient
   - **Synthesis Agent**: Generates final answer with grounding and safety checks
4. Hybrid retrieval gathers evidence from ChromaDB, BM25 index, and optional graph context.
5. Tiered execution system automatically adjusts retrieval depth based on query complexity.
6. Safety guards, grounding logic, and citation extraction shape the final answer.
7. Frontend receives streamed or non-streamed output with citations, metadata, and tier information.

## API Surface

The main backend entry point is `app.api.main:app`.

### Major Route Groups

- `/auth`: User registration, login, logout, token refresh, and current user info
- `/query`: Synchronous and streaming query endpoints with tier-based execution
- `/sessions`: Session CRUD, strategy lock, memory operations, and history management
- `/documents`: Document inventory, deletion, reindex, upload, and metadata retrieval
- `/prompts`: Prompt templates, validation, versioning, approval workflow, and rollback
- `/admin/users`: User lifecycle management, role/status updates, and audit operations
- `/admin/ops`: Retrieval profile management, canary routing, rollback, benchmark, replay, and operational reports
- `/admin/model-settings` and `/user/api-settings`: Runtime model configuration and API key management
- `/api/evaluation`: Performance comparison, baseline systems, and evaluation metrics
- `/api/agent-tracking`: Real-time agent execution tracking with SSE streaming
- `/api/advanced-rag`: Query decomposition and Self-RAG evaluation endpoints
- `/api/analytics`: Retrieval analytics, monitoring statistics, and visualization data
- `/health`, `/ready`, `/metrics`: Health checks, readiness probes, and system metrics

## Architecture Characteristics

### Retrieval

- **Dense retrieval** through ChromaDB with configurable embedding models
- **Sparse retrieval** through BM25 with document filtering and source allowlists
- **Reciprocal Rank Fusion** for intelligent candidate blending from multiple sources
- **Optional reranking** with `BAAI/bge-reranker-v2-m3` for precision improvement
- **Parent-child chunk strategy** for balancing precision and answer context
- **Query rewriting** with deduplication to reduce redundant LLM calls (10-30% savings)
- **Tier-based retrieval** with adaptive top_k and rerank parameters (fast/balanced/deep)

### Orchestration

- **LangGraph-based** multi-agent workflow with conditional routing
- **Five specialized agents**: Router, Vector RAG, Graph RAG, Web Research, and Synthesis
- **Streaming support** for progressive answer delivery with real-time updates
- **Runtime-safe wrappers** with timeout controls and fallback handling
- **Concurrent execution** for vector and graph retrieval in hybrid mode
- **Tier-based execution** with automatic complexity classification and load-based degradation
- **State management** with comprehensive parameter validation and error recovery

### Governance and Safety

- **RBAC** with user-scoped data access and role-based permissions (admin/user)
- **Approval-token flow** for privileged admin creation with single-use enforcement
- **Comprehensive audit logging** for sensitive operations with failure tracking
- **Retrieval profiles** (baseline/advanced/safe) with canary routing and rollback support
- **Query guards** with quota controls, rate limiting, and input validation
- **Resilience utilities** including circuit breakers, bulkhead isolation, and retry logic
- **Security hardening** with constant-time token comparison, HTTPS-only cookies, and CSRF protection
- **Password policy** enforcement (12-128 chars, special characters required)
- **Session isolation** with user-scoped document access and memory management

## Repository Layout

```text
.
├── app/                  # Backend code
│   ├── agents/           # Specialized agent implementations
│   ├── api/              # FastAPI app, routes, middleware
│   ├── core/             # Settings, logging, shared utilities
│   ├── graph/            # LangGraph orchestration and streaming
│   ├── ingestion/        # Loaders, chunking, OCR, indexing
│   ├── retrievers/       # Vector, BM25, fusion, reranking
│   ├── services/         # Auth, governance, memory, prompts
│   └── tools/            # Tool integrations
├── configs/              # Runtime profile and config files
├── data/                 # Local runtime data (mostly gitignored)
├── docs/                 # Public documentation (see docs/README.md)
├── frontend/             # React + Vite UI
├── scripts/              # Operational tooling
│   └── dev/              # Manual smoke / developer scripts
├── tests/                # Backend and workflow regression tests
└── examples/             # Usage examples
```

Internal records (audits, plans, fix logs, AI assistant configs) live under
`internal_docs/` and are excluded from the public repository per
[DOCUMENTATION_POLICY.md](./DOCUMENTATION_POLICY.md).

## Multi-Agent Workflow

The system uses **LangGraph** to orchestrate a sophisticated multi-agent workflow:

1. **Router Agent** - Analyzes query intent and determines routing strategy
2. **Vector RAG Agent** - Performs hybrid retrieval (vector + BM25 + reranking)
3. **Graph RAG Agent** - Queries Neo4j knowledge graph for entity relationships
4. **Web Research Agent** - Conducts web search when local knowledge is insufficient
5. **Synthesis Agent** - Synthesizes final answer with grounding and safety checks

### Tiered Execution System

Queries are automatically classified into three tiers based on complexity:

| Tier | Use Case | Retrieval | Max Time | Tokens | Web Fallback |
|------|----------|-----------|----------|--------|--------------|
| **Fast** | Simple factual queries, single-entity lookup | top_k=5, rerank=3 | 800ms | 300 | Disabled |
| **Balanced** | Default for most queries, moderate complexity | top_k=10, rerank=5 | 2000ms | 800 | Conditional |
| **Deep** | Multi-hop reasoning, comprehensive answers | top_k=20, rerank=10 | 5000ms | 1500 | Enabled |

**Load-Based Degradation**: System automatically downgrades tiers when load >80% for stability.

## Recent Improvements

For the full version history with all releases, see
[CHANGELOG.md](./CHANGELOG.md) and [docs/VERSION_HISTORY.md](./docs/VERSION_HISTORY.md).

### v0.4.1 (2026-05-20)
- **Code Quality Refactoring**: Eliminated ~2,700 lines of duplicate code across frontend and backend
- **Reusable Modules**: Created 19 new utility modules and components for better maintainability
- **Error Handling**: Standardized error responses across all API routes with dedicated utilities
- **Multilingual Support**: Automatic language detection with 20% Chinese threshold and session preferences
- **Analytics Dashboard**: Retrieval monitoring with statistics, visualization, and export capabilities

### v0.4.0 (2026-05-16)
- **Performance Comparison Framework**: Baseline systems with comprehensive evaluation metrics
- **Agent Execution Visualization**: Real-time tracking with SSE streaming and interactive display
- **Chinese NLP Optimization**: Tokenization, synonym expansion, and query preprocessing
- **Advanced RAG Techniques**: Query decomposition and Self-RAG evaluation endpoints

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose for Neo4j
- One model backend:
  - Ollama
  - OpenAI
  - Anthropic

## Quick Start

### 1. Backend Setup

**Conda (recommended)**:
```bash
conda create -n rag-local python=3.11
conda activate rag-local
pip install -U pip
pip install -e .
cp .env.example .env   # Windows: copy .env.example .env
```

**venv**:
```bash
# macOS/Linux
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
cp .env.example .env

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e .
copy .env.example .env
```

**Optional extras** (install only what you need):

```bash
# Tesseract-based OCR for scanned PDFs / images
pip install -e ".[ocr]"

# Cross-encoder reranker (BAAI/bge-reranker-v2-m3 by default)
pip install -e ".[reranker]"

# Docling for advanced PDF / DOCX / PPTX structured extraction
pip install -e ".[docling]"

# PaddleOCR for layout-aware Chinese OCR (~500MB native libs)
pip install -e ".[paddle]"

# All optional features at once (matches the historical "full" install)
pip install -e ".[full]"

# Development tooling (pytest, ruff, etc.)
pip install -e ".[dev]"
```

The minimal `pip install -e .` boots the FastAPI backend, hybrid retriever
(vector + BM25), graph integration, and basic PDF/text ingestion. OCR, the
reranker, Docling, and PaddleOCR are loaded on-demand and degrade gracefully
when their packages are absent.

### 2. Configure Environment

Edit `.env` and set the backend you want to use.

**Example for OpenAI**:

```bash
MODEL_BACKEND=openai
OPENAI_API_KEY=your_api_key
OPENAI_CHAT_MODEL=gpt-4-turbo
OPENAI_EMBED_MODEL=text-embedding-3-small
```

**Example for Ollama (Local)**:

```bash
MODEL_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b-instruct
OLLAMA_EMBED_MODEL=nomic-embed-text
```

**Example for Anthropic**:

```bash
MODEL_BACKEND=anthropic
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_CHAT_MODEL=claude-3-5-sonnet-20241022
# Note: Anthropic uses OpenAI embeddings
OPENAI_API_KEY=your_openai_key
OPENAI_EMBED_MODEL=text-embedding-3-small
```

### 3. Start Neo4j

```bash
docker compose up -d neo4j
```

### 4. Run the Backend

```bash
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app --reload-include "*.py" --reload-exclude "data/*" --reload-exclude "artifacts/*" --reload-exclude "frontend/*"
```

### 5. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173/app`.

## Document Ingestion

- Put source files under `data/docs`
- Or upload through the web UI / API
- Run manual ingestion when needed:

```bash
python scripts/ingest.py
```

Useful related settings:

- `AUTO_INGEST_ENABLED`
- `DATA_DIR`
- `CHROMA_PERSIST_DIR`
- `CORPUS_STORE_PATH`
- `PARENT_STORE_PATH`

## Key Configuration Domains

### Model and Runtime

- `MODEL_BACKEND`
- `OPENAI_*`
- `ANTHROPIC_*`
- `OLLAMA_*`
- `QUERY_REQUEST_TIMEOUT_MS`

### Retrieval

- `TOP_K`
- `VECTOR_TOP_K`
- `BM25_TOP_K`
- `ENABLE_RERANKER`
- `RERANKER_MODEL_NAME`
- `RETRIEVAL_PROFILE`

### Storage

- `CHROMA_PERSIST_DIR`
- `DATA_DIR`
- `APP_DB_PATH`
- `SESSIONS_DIR`
- `UPLOADS_DIR`

### Security

- `AUTH_TOKEN_TTL_HOURS` - JWT token expiration time
- `ADMIN_CREATE_APPROVAL_TOKEN_HASH` - Hashed approval token for admin creation
- `API_SETTINGS_ENCRYPTION_KEY` - Encryption key for API credentials storage
- `API_BASE_URL_ALLOWLIST` - Comma-separated list of allowed API base URLs
- `AUTH_COOKIE_SECURE` - Enable HTTPS-only cookies (default: true)
- `AUTH_COOKIE_SAMESITE` - CSRF protection mode (default: strict)
- `AUTH_COOKIE_HTTPONLY` - Prevent JavaScript access to cookies (default: true)

### OCR and Media

- `TESSERACT_CMD` - Path to Tesseract OCR executable
- `TESSERACT_LANG` - OCR language (default: eng+chi_sim for English and Chinese)
- `OCR_PREPROCESS_ENABLED` - Enable image preprocessing for better OCR accuracy
- `IMAGE_CAPTION_ENABLED` - Enable AI-powered image captioning for visual content
- `OCR_DPI` - DPI setting for OCR processing (default: 300)
- `IMAGE_MAX_SIZE` - Maximum image dimension for processing

## Operations

### Backend Tests

```bash
# Run all tests
pytest -q

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test modules
pytest tests/test_routing_logic.py -v

# Run tests allowing runtime unavailable (for CI environments)
pytest --allow-runtime-unavailable
```

### Manual Smoke Scripts

Developer-driven verification scripts live under `scripts/dev/`. These are CLI
tools meant to be run interactively against a real environment, not automated
tests. See [scripts/dev/README.md](./scripts/dev/README.md) for the catalog.

### CI/CD Quality Gate

```bash
# Run comprehensive quality checks (includes backend tests, RAG evaluation, benchmarks)
python scripts/ci_quality_gate.py

# Components:
# - Backend tests (29+ tests with workflow regression coverage)
# - RAG evaluation (precision/recall/F1 metrics)
# - Performance benchmarks (latency and throughput)
# - Code quality checks

# Exit codes:
# 0 = All checks passed
# 1 = Backend tests failed
# 2 = Precision below threshold
# 3 = F1 score below threshold
# 4 = Recall below threshold (non-blocking in CI)
```

### Frontend Build

```bash
cd frontend
npm run build

# Development mode with hot reload
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint
```

### Example Operational Scripts

- `scripts/benchmark_pipeline.py` - Retrieval pipeline performance benchmarking with latency analysis
- `scripts/load_test_query.py` - Concurrent query load testing with throughput metrics
- `scripts/eval_retrieval.py` - RAG evaluation with precision/recall/F1 metrics
- `scripts/chaos_probe.py` - Chaos engineering and resilience testing for failure scenarios
- `scripts/ingest.py` - Manual document ingestion and indexing with OCR support
- `scripts/ci_quality_gate.py` - Comprehensive CI/CD quality gate with automated checks

## Security Notes

- **Never commit `.env` files** - Use `.env.example` as a template
- **Use hashed approval tokens** - Prefer `ADMIN_CREATE_APPROVAL_TOKEN_HASH` over plaintext
- **Review upload limits** - Configure `MAX_UPLOAD_SIZE_MB` and file type restrictions
- **Validate API allowlists** - Set `API_BASE_URL_ALLOWLIST` before production deployment
- **Enable HTTPS in production** - Set `AUTH_COOKIE_SECURE=true` for secure cookie transmission
- **Enforce strong passwords** - System requires 12+ characters with special characters
- **Monitor audit logs** - Review admin operations and authentication events regularly
- **Validate cross-user isolation** - Test user-scoped data access in every release
- **Protect model credentials** - Treat API keys as environment-scoped secrets
- **Rate limit admin endpoints** - Built-in rate limiting prevents abuse (configurable)
- **Single-use approval tokens** - Tokens are tracked and can only be used once
- **Constant-time comparisons** - Prevents timing attacks on sensitive operations

## Documentation

Start with the documentation hub: [docs/README.md](./docs/README.md)

### Recommended Reading Order

1. **[docs/README.md](./docs/README.md)** - Documentation hub and navigation guide
2. **[CHANGELOG.md](./CHANGELOG.md)** - Detailed version history and changes
3. **[docs/VERSION_HISTORY.md](./docs/VERSION_HISTORY.md)** - Complete version timeline
4. **[DOCUMENTATION_POLICY.md](./DOCUMENTATION_POLICY.md)** - Public/internal classification policy

### Documentation Structure

- **[docs/](./docs/)** - Public documentation directory
  - **[releases/](./docs/releases/)** - Release notes and version announcements
  - **[design/](./docs/design/)** - Feature design specifications and technical proposals
  - **[archive/](./docs/archive/)** - Historical reports and investigations
    - `refactoring/` - Refactoring reports and technical debt cleanup
    - `ui/` - UI modernization and CSS cleanup reports
    - `investigations/` - Technical investigation reports
  - **[development/](./docs/development/)** - Development guides and workflows
  - **[operations/](./docs/operations/)** - Deployment and operational guides
  - **[project/](./docs/project/)** - Project planning and readiness checklists
  - **[templates/](./docs/templates/)** - Documentation templates
  - **[images/](./docs/images/)** - Architecture diagrams and screenshots

### Additional Resources

- **API Documentation** - Available at `/docs` when backend is running

## Contributing

Contributions are welcome! Please ensure:

- All tests pass before submitting PRs
- Follow the existing code style and architecture patterns
- Update documentation for new features
- Add tests for new functionality
- Run the CI quality gate locally before pushing

## License

MIT. See [LICENSE](./LICENSE).

---

**Made with ❤️ by the Bronit Team**
