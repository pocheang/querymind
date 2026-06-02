# Documentation Hub

**Status**: Public  
**Last Updated**: 2026-06-02  
**Audience**: Users, operators, contributors, maintainers  

This directory is the public GitHub documentation hub for Multi-Agent Local RAG.
It contains only sanitized documentation that is safe to publish. Internal
audits, security findings, private plans, and generated reports are kept under
`internal_docs/` and are excluded from GitHub by `.gitignore`.

**Quick Navigation**: See [INDEX.md](./INDEX.md) for a complete documentation index.

## Public Documentation Map

| Document | Purpose | Audience |
| --- | --- | --- |
| [../README.md](../README.md) | Project overview, setup, usage | All users |
| [../CHANGELOG.md](../CHANGELOG.md) | Public change history | Users, maintainers |
| [../DOCUMENTATION_POLICY.md](../DOCUMENTATION_POLICY.md) | Documentation governance policy | Maintainers |
| [INDEX.md](INDEX.md) | Complete documentation index | All users |
| [project/PUBLICATION_MATRIX.md](project/PUBLICATION_MATRIX.md) | What can and cannot be published to GitHub | Maintainers, contributors |
| [project/SECURITY.md](project/SECURITY.md) | Responsible disclosure policy | Security reporters, maintainers |
| [project/CODE_CHANGE_POLICY.md](project/CODE_CHANGE_POLICY.md) | Code change policy | Maintainers, contributors |
| [guides/API_SETTINGS_GUIDE.md](guides/API_SETTINGS_GUIDE.md) | API/model configuration guidance | Admins, operators |
| [guides/PERFORMANCE_OPTIMIZATION.md](guides/PERFORMANCE_OPTIMIZATION.md) | General performance tuning | Operators, engineers |
| [history/VERSION_HISTORY.md](history/VERSION_HISTORY.md) | Public version timeline | Delivery, maintainers |
| [project/production_readiness_checklist.md](project/production_readiness_checklist.md) | Sanitized production readiness checklist | Operators, SRE, engineering |
| [project/INDEX.md](project/INDEX.md) | Project documentation index | Operators, maintainers |
| [design/INDEX.md](design/INDEX.md) | Public design documentation index | Product, engineering |
| [templates/README.md](templates/README.md) | Documentation templates | Maintainers |

## Public Directory Structure

```text
docs/
├── README.md                    # This file - documentation hub
├── INDEX.md                     # Complete documentation index
├── guides/                      # Configuration and operation guides
│   ├── API_SETTINGS_GUIDE.md
│   ├── PDF_PERFORMANCE_TUNING.md
│   ├── PDF_TESTING_GUIDE.md
│   └── PERFORMANCE_OPTIMIZATION.md
├── features/                    # Feature documentation
│   ├── rag/                    # RAG and retrieval features
│   ├── agents/                 # Agent system features
│   ├── pdf/                    # PDF processing features
│   └── ocr/                    # OCR and image processing
├── history/                     # Version history and optimization records
│   ├── VERSION_HISTORY.md
│   ├── OPTIMIZATION_HISTORY.md
│   └── demo_dataset_setup.md
├── project/                     # Project planning and policies
│   ├── CODE_CHANGE_POLICY.md
│   ├── PUBLICATION_MATRIX.md
│   ├── SECURITY.md
│   └── production_readiness_checklist.md
├── design/                      # Design documents and feature specs
├── releases/                    # Release notes and announcements
├── archive/                     # Historical reports and investigations
│   ├── refactoring/            # Refactoring reports
│   ├── ui/                     # UI modernization reports
│   └── investigations/         # Technical investigation reports
├── images/                      # Architecture diagrams and screenshots
└── templates/                   # Documentation templates
```

Internal-only locations excluded from this hub (kept under `internal_docs/`):

- `internal_docs/plans/` - Execution plans with step-by-step instructions
- `internal_docs/docs_archive/` - Test reports, fix logs, deep code reviews
- `internal_docs/security/` - Security audits, patch guides, vulnerability details
- `internal_docs/project_audit/` - Project audit reports and remediation backlogs

## Internal Documentation

The following content must not be linked from public docs and must stay in
`internal_docs/`:

- Security audits, vulnerability details, exploit scenarios, patch guides
- Project audit reports, P0/P1 remediation lists, quality findings
- Internal implementation plans and delivery roadmaps
- AI assistant instructions and local operating notes
- Generated validation reports, local logs, screenshots, temporary files

For the full classification rules, see [PUBLICATION_MATRIX.md](PUBLICATION_MATRIX.md).

## Review Rules

- Public docs should be safe for GitHub, customers, and external contributors.
- Internal docs can contain sensitive detail but must remain ignored by Git.
- If a document has both public and sensitive content, split it into a public
  summary and an internal detailed record.
- Do not link public docs to ignored internal files.
