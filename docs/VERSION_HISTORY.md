# Version History

**Status**: Public  
**Last Updated**: 2026-04-29  
**Audience**: Users, operators, contributors, maintainers  

This file is the public version timeline for Multi-Agent Local RAG. It keeps a
sanitized record of releases and intentionally excludes internal audit reports,
security exploit details, private remediation plans, and generated validation
artifacts.

For current release notes, also see [../CHANGELOG.md](../CHANGELOG.md).

## Release Timeline

| Version | Date | Type | Public Summary |
| --- | --- | --- | --- |
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
