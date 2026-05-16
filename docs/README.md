# Documentation Hub

**Status**: Public  
**Last Updated**: 2026-05-16  
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
| [PUBLICATION_MATRIX.md](PUBLICATION_MATRIX.md) | What can and cannot be published to GitHub | Maintainers, contributors |
| [SECURITY.md](SECURITY.md) | Responsible disclosure policy | Security reporters, maintainers |
| [API_SETTINGS_GUIDE.md](API_SETTINGS_GUIDE.md) | API/model configuration guidance | Admins, operators |
| [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md) | General performance tuning | Operators, engineers |
| [VERSION_HISTORY.md](VERSION_HISTORY.md) | Public version timeline | Delivery, maintainers |
| [project/production_readiness_checklist.md](project/production_readiness_checklist.md) | Sanitized production readiness checklist | Operators, SRE, engineering |
| [project/INDEX.md](project/INDEX.md) | Project documentation index | Operators, maintainers |
| [operations/INDEX.md](operations/INDEX.md) | Operations documentation index | Operators |
| [development/INDEX.md](development/INDEX.md) | Development documentation index | Contributors |
| [design/INDEX.md](design/INDEX.md) | Public design documentation index | Product, engineering |
| [templates/README.md](templates/README.md) | Documentation templates | Maintainers |

## Public Directory Structure

```text
docs/
├── README.md                    # This file - documentation hub
├── INDEX.md                     # Complete documentation index
├── PUBLICATION_MATRIX.md
├── SECURITY.md
├── API_SETTINGS_GUIDE.md
├── PERFORMANCE_OPTIMIZATION.md
├── VERSION_HISTORY.md
├── releases/                    # Release notes and announcements
│   ├── RELEASE_NOTES_v0.4.0.md
│   └── RELEASE_v0.3.1.md
├── archive/                     # Historical reports and investigations
│   ├── refactoring/            # Refactoring reports
│   ├── ui/                     # UI modernization reports
│   └── investigations/         # Technical investigation reports
├── project/                     # Project planning and architecture
├── operations/                  # Deployment and operational guides
├── development/                 # Development guides and workflows
├── design/                      # Design documentation
├── plans/                       # Implementation plans
├── security/                    # Security documentation
└── templates/                   # Documentation templates
```

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
