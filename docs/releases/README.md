# Release Notes

Official release notes for QueryMind（智询）.

## Latest Release

**[v0.7.1.1](v0.7.1.1-release-notes.md)** - 2026-09-29
- Answers name the specialist that wrote them and the shape they answer in; the tool panel numbers tools the way the answer does
- Chat, architecture, landing and analytics pages describe the pipeline as it runs; the API catalog is rebuilt from the live OpenAPI document
- Fewer model calls per question (clarification only when useful, Self-RAG off by default, no pointless retries)
- Questions about attacks are answered; a refused question answers 422, not 500

## Previous Release

**[v0.7.1](v0.7.1-release-notes.md)** - 2026-09-28
- Five domain specialists (security, AI, data analysis, compliance review, document reading), each with its own read-only tools and answer shape
- Offline threat-intelligence store (NVD, CISA KEV, FIRST EPSS, MITRE ATT&CK) and four bundled regulations
- Tool facts cited as `[T1]` and checked against the tool's output; answers only as long as their evidence
- Models load in the background, so the first question after a restart finds evidence
- Multiple workers on one host: shared state in Redis and SQLite, queued ingestion, quotas counted once
- **Upgrade**: `docker compose down` (never `-v`) first; Redis and the Chroma server become required

## Recent Releases

| Version | Date | Type | Summary |
|---------|------|------|---------|
| [v0.7.1.1](v0.7.1.1-release-notes.md) | 2026-09-29 | Patch / Frontend & Request Flow | Specialist badge and numbered tool sources, pages match the pipeline, fewer model calls per question, defensive questions answered (422 on refusal) |
| [v0.7.1](v0.7.1-release-notes.md) | 2026-09-28 | Feature / Deployment | Five domain specialists with their own tools, offline threat intelligence, tool citations, background model warm-up, multiple workers on one host |
| [v0.7.0.3](v0.7.0.3-release-notes.md) | 2026-09-18 | Feature / Quality & Standards | Dynamic dual-track clarification agent, Codex-style prompt specifications, SonarCloud quality gate mastery |
| [v0.7.0.2](v0.7.0.2-release-notes.md) | 2026-09-16 | Patch / Quality & Security | Full SonarQube quality gate remediation (0 bugs/vulns/smells), 100% duplication elimination (0 lines / 0.0%), topology & admin state decoupling |
| [v0.7.0.1](v0.7.0.1-release-notes.md) | 2026-09-14 | Patch / Feature / Security | Table & Excel pipeline, CSV support, header retention chunking, owner-scoped table SQL, injection screening |
| [v0.7.0](v0.7.0-release-notes.md) | 2026-09-11 | Major | Architecture visualization, execution trace, UI observability |
| [v0.6.2.1](v0.6.2.1-release-notes.md) | 2026-07-18 | Infrastructure | Config governance, deployment standardization, docs restructure |

| [v0.6.2](v0.4.6-release-notes.md) | 2026-07-06 | Feature | Project rebranding, monitoring stack, structured logging |
| [v0.6.1](v0.4.1-release-notes.md) | 2026-07-06 | Feature | Docker support, agent architecture, admin dashboard |
| [v0.6.0](v0.4.1-release-notes.md) | 2026-06-28 | Quality | Agent quality optimization, 99% router accuracy |
| [v0.5.0](v0.4.1-release-notes.md) | 2026-06-26 | Security | Quality assurance system, RBAC, 2026 AI models |
| [v0.4.6](v0.4.6-release-notes.md) | 2026-06-19 | Stability | Backend fixes, 67% memory reduction |
| [v0.4.5](v0.4.6-release-notes.md) | 2026-06-19 | Performance | Graph RAG optimization, 50-93% latency reduction |
| [v0.4.2](v0.4.2-release-notes.md) | 2026-05-22 | Hardening | Code cleanup, FastAPI lifecycle updates |
| [v0.4.1](v0.4.1-release-notes.md) | 2026-05-20 | Refactoring | Code quality, -2,700 lines duplicate code |

## All Releases

See [CHANGELOG.md](../../CHANGELOG.md) for complete version history.

See [Version History](../history/VERSION_HISTORY.md) for public timeline.

## Release Types

- **Major**: Breaking changes, new architecture
- **Feature**: New features, enhancements
- **Quality**: Performance, accuracy improvements
- **Security**: Security fixes, hardening
- **Stability**: Bug fixes, reliability
- **Infrastructure**: Deployment, configuration
- **Refactoring**: Code quality, cleanup

## Support

- **Current**: v0.7.x (full support)
- **Limited**: v0.6.x (security updates only)
- **Unsupported**: < v0.6.0

## Resources

- [Documentation](../README.md)
- [Migration Guides](../../CHANGELOG.md)
- [Security Policy](../../SECURITY.md)
- [Contributing](../../CONTRIBUTING.md)
