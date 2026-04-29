# GitHub Publication Matrix

**Status**: Public  
**Last Updated**: 2026-04-29  
**Audience**: Maintainers, contributors, release managers  

This matrix defines which documents can be public on GitHub and which must stay
internal. When in doubt, keep the document internal until it is reviewed.

## Allowed On GitHub

| Category | Examples | Conditions |
| --- | --- | --- |
| Product overview | `README.md` | No secrets, no private endpoints, no customer data |
| Public release notes | `CHANGELOG.md`, `RELEASE_*.md` | Sanitized and user-facing |
| Public setup/configuration | `docs/API_SETTINGS_GUIDE.md`, `.env.example` | Placeholder values only |
| Public performance guidance | `docs/PERFORMANCE_OPTIMIZATION.md` | General tuning, no private capacity data |
| Public version history | `docs/VERSION_HISTORY.md` | No internal incident detail |
| Public readiness checklist | `docs/project/production_readiness_checklist.md` | Sanitized checklist only |
| Public documentation indexes | `docs/README.md`, `docs/*/INDEX.md` | Links must target public docs only |
| Public templates | `docs/templates/*.md` | Generic templates only |
| Public security policy | `docs/SECURITY.md` | Disclosure process only, no vulnerability detail |

## Not Allowed On GitHub

| Category | Examples | Required Location |
| --- | --- | --- |
| Secrets and credentials | `.env`, tokens, keys, certificates | Never commit |
| Security audits | `ADMIN_USERS_SECURITY_AUDIT.md` | `internal_docs/security/` |
| Vulnerability patch guides | `ADMIN_USERS_PATCH_GUIDE.md`, `SECURITY_FIXES_INSTALLATION.md` | `internal_docs/security/` |
| Internal fix plans | `ADMIN_USERS_FIX_PLAN.md` | `internal_docs/security/` or `internal_docs/plans/` |
| Project audits | `internal_docs/project_audit/*.md` | `internal_docs/project_audit/` |
| Internal roadmaps | `docs/plans/*.md` moved to internal storage | `internal_docs/plans/` |
| Deep code reviews | `DEEP_CODE_REVIEW_*.md` | `internal_docs/docs_archive/` |
| Fix summaries with sensitive implementation detail | `FIXES_*.md` | `internal_docs/docs_archive/` |
| Generated validation reports | `docs/VALIDATION_REPORT.json` | `internal_docs/docs_archive/` or `artifacts/` |
| AI assistant instructions | `CLAUDE.md`, `.agents/`, `.claude/` | ignored local/internal paths |
| Runtime data | logs, local DBs, uploaded docs, vector stores | ignored local data paths |

## Current Normalization Record

On 2026-04-29, the following public-to-internal moves were made:

| Previous Public Path | Internal Location |
| --- | --- |
| `docs/security/ADMIN_USERS_SECURITY_AUDIT.md` | `internal_docs/security/ADMIN_USERS_SECURITY_AUDIT.md` |
| `docs/security/ADMIN_USERS_FIX_PLAN.md` | `internal_docs/security/ADMIN_USERS_FIX_PLAN.md` |
| `docs/security/ADMIN_USERS_PATCH_GUIDE.md` | `internal_docs/security/ADMIN_USERS_PATCH_GUIDE.md` |
| `docs/security/SECURITY_FIXES_INSTALLATION.md` | `internal_docs/security/SECURITY_FIXES_INSTALLATION.md` |
| `docs/plans/*.md` | `internal_docs/plans/` |
| `docs/archive/DEEP_CODE_REVIEW_2026-04-27.md` | `internal_docs/docs_archive/DEEP_CODE_REVIEW_2026-04-27.md` |
| `docs/archive/DOCUMENTATION_COMPLETENESS_REPORT.md` | `internal_docs/docs_archive/DOCUMENTATION_COMPLETENESS_REPORT.md` |
| `docs/archive/FIXES_INDEX.md` | `internal_docs/docs_archive/FIXES_INDEX.md` |
| `docs/archive/FIXES_SUMMARY.md` | `internal_docs/docs_archive/FIXES_SUMMARY.md` |
| `docs/VALIDATION_REPORT.json` | `internal_docs/docs_archive/VALIDATION_REPORT_2026-04-29.json` |

## Decision Rule

Publish a document only when all answers are "yes":

1. Is it useful to external users, operators, or contributors?
2. Is it free of credentials, customer data, internal hostnames, and local paths?
3. Is it free of unresolved security findings and exploit detail?
4. Are all links public and valid?
5. Would it still be safe if copied outside the repository?

If any answer is "no", keep it internal.
