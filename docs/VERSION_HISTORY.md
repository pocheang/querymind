# Version History

**Status**: Public  
**Last Updated**: 2026-05-16  
**Audience**: Users, operators, contributors, maintainers  

This file is the public version timeline for Multi-Agent Local RAG. It keeps a
sanitized record of releases and intentionally excludes internal audit reports,
security exploit details, private remediation plans, and generated validation
artifacts.

For current release notes, also see [../CHANGELOG.md](../CHANGELOG.md).

## Release Timeline

| Version | Date | Type | Public Summary |
| --- | --- | --- | --- |
| v0.4.0 | 2026-05-16 | Major Feature | Interview demo features: Performance comparison, Agent visualization, Chinese NLP, Advanced RAG, Streaming PDF, Demo dataset, Modern UI redesign |
| v0.3.3 | 2026-05-07 | Feature | Performance optimization and enhanced testing |
| v0.3.1.2 | 2026-04-28 | Security hardening | Admin user management hardening, RBAC checks, input validation, safer auth behavior |
| v0.3.1.1 | 2026-04-28 | Patch | PDF upload statistics fixes and user feedback improvements |
| v0.3.1 | 2026-04-27 | Documentation | Documentation organization, public/internal separation, version history cleanup |
| v0.3.0 | 2026-04-27 | Architecture | Modular architecture refactor and dependency boundary cleanup |
| v0.2.5 | 2026-04-27 | Patch | Stability fixes, retrieval improvements, performance tuning |
| v0.2.4 | 2026-04-26 | Feature | Runtime profile work and query-to-answer speed improvements |
| v0.2.2.1 | 2026-04-10 | Patch | Streaming response reliability improvements |
| v0.2.2 | 2026-04-09 | Architecture | Runtime resilience and operational controls |
| v0.2.1 | 2026-04-09 | Feature | RAG and agent operations controls |
| v0.2.0 | 2026-04-08 | Feature | Admin operations and user management |
| v0.1.0 | 2026-04-08 | Initial release | Initial public baseline |

## v0.4.0

Public highlights:

- **Performance Comparison Framework**: Baseline systems (vector-only, hybrid, rerank) with comprehensive evaluation metrics (Precision, Recall, F1, MRR, NDCG)
- **Agent Execution Visualization**: Real-time tracking service with SSE streaming, frontend hooks, and execution history
- **Chinese NLP Optimization**: Jieba-based tokenization, synonym expansion, query preprocessing, and Chinese-specific evaluation metrics
- **Advanced RAG Techniques**: Query decomposition for complex queries and Self-RAG with relevance/quality evaluation
- **Streaming PDF Processing**: True streaming with 70% memory reduction for large PDFs (1000+ pages)
- **Batch Chart Extraction**: Parallel processing for improved throughput
- **Demo Dataset**: 6 documents (2,763 lines, ~19,000 words) for interview demonstrations
- **Modern UI Redesign**:
  - Welcome Screen component with system statistics, quick actions, and feature highlights
  - API Settings modal redesign with unified card-based design and modern form inputs
  - Interactive Architecture visualization with React Flow (28 functional nodes)
  - Sidebar optimization with enhanced visual hierarchy and status badges
  - CSS architecture improvements with lazy-loaded styles

Key metrics:
- 84+ files modified/added with 15,086+ lines of new code
- 13 new backend services, 3 API route modules
- 9 comprehensive unit test files, 6 demo documents
- 4 new UI components (WelcomeScreen, DataFlowVisualization)
- 15-25% accuracy improvement over baseline systems
- 70% memory reduction for large PDF processing
- Real-time agent execution tracking with SSE support

Related public documents:
- [Interview Demo Implementation Summary](INTERVIEW_DEMO_IMPLEMENTATION_SUMMARY.md)
- [Performance Comparison Framework](performance_comparison_framework.md)
- [Agent Execution Tracking](agent_execution_tracking.md)
- [Chinese NLP Optimization](chinese_nlp_optimization.md)
- [Advanced RAG Techniques](advanced_rag_techniques.md)

## v0.3.3

Public highlights:

- Performance optimization and enhanced testing
- PDF processing improvements with streaming support
- Comprehensive test coverage expansion
- Performance benchmarking system

## v0.3.1.2

Public highlights:

- Hardened admin user management flows.
- Improved role and status validation.
- Strengthened password and authentication behavior.
- Added security-focused regression coverage.

Internal security audit details, vulnerability analysis, exploit scenarios, and
patch guides are stored under `internal_docs/security/` and are not published to
GitHub.

## v0.3.1.1

Public highlights:

- Fixed PDF upload statistics behavior.
- Improved user feedback around upload and indexing flows.
- Preserved backward-compatible API behavior where practical.

Detailed implementation notes and internal fix plans are kept in internal
documentation.

## v0.3.1

Public highlights:

- Clarified public versus internal documentation boundaries.
- Added public documentation governance.
- Consolidated public documentation entry points.
- Moved internal plans, audits, security reports, and generated validation
  artifacts out of the public `docs/` tree.

Relevant public documents:

- [Documentation Policy](../DOCUMENTATION_POLICY.md)
- [Publication Matrix](PUBLICATION_MATRIX.md)
- [Documentation Hub](README.md)

## v0.3.0

Public highlights:

- Refactored architecture into clearer modules.
- Improved separation of graph, retrieval, service, and API responsibilities.
- Reduced coupling in runtime workflows.

Detailed refactoring reports are kept in internal archives unless explicitly
sanitized for public release.

## v0.2.5

Public highlights:

- Fixed multiple stability and workflow issues.
- Improved retrieval behavior.
- Added or refreshed regression tests.
- Tuned performance-sensitive paths.

## v0.2.4

Public highlights:

- Introduced query-to-answer UX speed work.
- Clarified runtime profile behavior.
- Improved perceived latency and streaming flow.

Related public design reference:

- [Query-to-Answer UX Speed Design](superpowers/specs/2026-04-19-query-to-answer-ux-speed-design.md)

## v0.2.2.1

Public highlights:

- Improved streaming response reliability.
- Added fallback behavior for partial failures.

## v0.2.2

Public highlights:

- Added runtime resilience controls.
- Improved operational guardrails.
- Expanded service-level tests.

## v0.2.1

Public highlights:

- Added RAG and agent operations controls.
- Improved retrieval strategy management.

## v0.2.0

Public highlights:

- Added admin operations and user management foundations.
- Added initial RBAC-related service structure.

## v0.1.0

Public highlights:

- Initial local multi-agent RAG baseline.
- FastAPI backend, React frontend, retrieval and graph orchestration foundations.

## Publication Notes

- Public version history should summarize user-visible behavior, compatibility,
  and safe release information.
- Security-sensitive findings belong in `internal_docs/security/`.
- Deep code reviews, fix logs, and generated validation reports belong in
  `internal_docs/docs_archive/`.
- Public release notes must not link to ignored internal files.
