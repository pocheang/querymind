# Design Documentation Index

**Status**: Public
**Last Updated**: 2026-05-22
**Purpose**: Index of feature design specifications and technical design artifacts

## About This Directory

`docs/design/` contains finalized public design documents for features that
have shipped or are scheduled. Internal-only design notes, results reports, and
analysis records are stored in `internal_docs/docs_archive/` and not published.

Active in-progress execution plans are kept in `internal_docs/plans/` and
moved here when the design they describe is ready for public reference.

## UI and UX Designs

- [2026-04-19-query-to-answer-ux-speed-design.md](./2026-04-19-query-to-answer-ux-speed-design.md) - Query-to-answer UX speed design
- [2026-04-30-auth-ui-refresh-design.md](./2026-04-30-auth-ui-refresh-design.md) - Auth UI refresh
- [2026-04-30-chat-workbench-console-refresh-design.md](./2026-04-30-chat-workbench-console-refresh-design.md) - Chat workbench console refresh
- [2026-05-03-sidebar-operations-deck-design.md](./2026-05-03-sidebar-operations-deck-design.md) - Sidebar operations deck
- [2026-05-15-interview-demo-improvements-design.md](./2026-05-15-interview-demo-improvements-design.md) - Interview demo improvements

## CSS and Frontend Performance

- [2026-05-01-css-optimization-design.md](./2026-05-01-css-optimization-design.md) - CSS performance optimization and code splitting
- [2026-05-02-css-phase2-critical-extraction-design.md](./2026-05-02-css-phase2-critical-extraction-design.md) - Critical CSS extraction (Phase 2)

## Feature and System Designs

- [2026-05-02-admin-script-secret-handling-design.md](./2026-05-02-admin-script-secret-handling-design.md) - Admin script secret handling
- [2026-05-15-pdf-p3-improvements-design.md](./2026-05-15-pdf-p3-improvements-design.md) - PDF P3 improvements
- [2026-05-17-monitoring-analytics-design.md](./2026-05-17-monitoring-analytics-design.md) - Monitoring and analytics system
- [2026-05-17-security-documentation-design.md](./2026-05-17-security-documentation-design.md) - Security documentation knowledge base
- [2026-05-18-multilingual-response-design.md](./2026-05-18-multilingual-response-design.md) - Multilingual response

## Guidelines

Use `docs/design/` for:
- Feature design specifications
- Technical architecture proposals
- API design documents
- UX and interaction design artifacts
- Decision records tied to feature design

Keep out of `docs/design/`:
- Execution plans with step-by-step instructions and commit commands - use `internal_docs/plans/`
- Test reports, results documents, and analysis logs - use `internal_docs/docs_archive/`
- Anything containing internal hostnames, secrets, or unfixed security findings
