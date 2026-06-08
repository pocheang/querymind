# Documentation Policy

**Status**: Public  
**Last Updated**: 2026-04-29  
**Audience**: Maintainers, contributors, operators, release managers  

This repository separates public GitHub documentation from internal delivery,
security, audit, and planning records. The goal is to make the public repository
useful and professional without exposing implementation risk, credentials,
security findings, internal operating notes, or unfinished plans.

## Public Documentation

The following documents are allowed to be visible on GitHub when they do not
contain secrets, customer data, exploit details, or internal-only procedures:

| Location | Public Use |
| --- | --- |
| `README.md` | Product overview, setup, usage, architecture summary |
| `CHANGELOG.md` | Public change history |
| `RELEASE_*.md` | Sanitized release notes |
| `LICENSE` | License |
| `DOCUMENTATION_POLICY.md` | This public documentation policy |
| `docs/README.md` | Public documentation hub |
| `docs/PUBLICATION_MATRIX.md` | Public/private documentation classification |
| `docs/SECURITY.md` | Responsible disclosure policy without vulnerability details |
| `docs/API_SETTINGS_GUIDE.md` | User-facing configuration guidance |
| `docs/PERFORMANCE_OPTIMIZATION.md` | General performance tuning guidance |
| `docs/VERSION_HISTORY.md` | Public version timeline |
| `docs/project/production_readiness_checklist.md` | Sanitized deployment readiness checklist |
| `docs/project/INDEX.md` | Public project documentation index |
| `docs/operations/INDEX.md` | Public operations documentation index |
| `docs/development/INDEX.md` | Public contributor/developer documentation index |
| `docs/design/INDEX.md` | Public design documentation index |
| `docs/templates/*.md` | Public documentation templates |

## Internal Documentation

Internal documents must stay under `internal_docs/` or another ignored internal
path and must not be committed to the public GitHub repository.

| Internal Content | Required Location |
| --- | --- |
| Security audits, vulnerability details, exploit scenarios, patch guides | `internal_docs/security/` |
| Project audits, quality findings, risk registers, P0/P1 issue lists | `internal_docs/project_audit/` |
| Internal plans, implementation roadmaps, delivery schedules | `internal_docs/plans/` |
| AI assistant instructions, local prompts, agent settings | `internal_docs/` or ignored local config |
| Generated validation reports and local audit artifacts | `internal_docs/docs_archive/` or `artifacts/` |
| Drafts, incomplete notes, private design decisions | `internal_docs/` |
| Customer data, logs, screenshots with sensitive content | ignored local runtime folders |

## Never Publish

Never publish these items to GitHub:

- `.env`, `.env.*` except `.env.example`
- API keys, tokens, passwords, private keys, certificates, cookies, sessions
- Local databases, vector stores, uploaded documents, user files
- Vulnerability reproduction steps, exploit payloads, CVSS detail reports
- Internal security patch procedures before public disclosure approval
- Internal project audit reports and remediation backlogs
- AI assistant local instructions such as `CLAUDE.md`
- Generated reports such as `docs/VALIDATION_REPORT.json`
- Local logs, screenshots, temporary files, and test scratch directories

## Publication Review Checklist

Before committing or publishing documentation:

1. Confirm the document is listed as public in `docs/PUBLICATION_MATRIX.md`.
2. Check that it contains no secrets, customer data, internal hostnames, or
   vulnerability details.
3. Make sure links point only to public documents or public source files.
4. Move internal records to `internal_docs/`.
5. Run `git status --short` and verify ignored/internal documents are not staged.
6. Run documentation validation when practical.

## Maintenance Rules

- Public docs should be stable, user-facing, and safe to share.
- Internal docs can be detailed, operational, and security-sensitive.
- If a document mixes public and internal content, split it into a sanitized
  public summary and an internal detailed record.
- Historical documents may remain public only when they are sanitized release
  notes or non-sensitive summaries.
- Any document describing unresolved security weaknesses is internal by default.

## Verification Commands

```bash
git status --short
git check-ignore internal_docs/
git check-ignore docs/security/
git check-ignore docs/plans/
git check-ignore docs/VALIDATION_REPORT.json
```
