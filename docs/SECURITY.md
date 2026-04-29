# Security Policy

**Status**: Public  
**Last Updated**: 2026-04-29  
**Audience**: Security reporters, maintainers, operators  

This public document explains how to report security issues. It intentionally
does not include vulnerability details, exploit steps, internal audit reports, or
patch procedures.

## Reporting A Security Issue

Please report suspected vulnerabilities privately to the project maintainer or
repository owner. Do not open a public GitHub issue containing exploit details,
tokens, logs, customer data, screenshots with sensitive content, or private
deployment information.

Include only the minimum detail needed to reproduce and triage the issue:

- A short summary of the suspected issue
- Affected feature or endpoint
- Impact assessment
- Safe reproduction notes without secrets
- Suggested remediation if available

## Public Disclosure

Security findings remain internal until the maintainers confirm the issue,
prepare a fix, and approve public disclosure. Public release notes should describe
the impact and fixed version without publishing operational exploit detail.

## Internal Security Records

Security audits, vulnerability reports, patch guides, and remediation plans are
stored under `internal_docs/security/` and are not published to GitHub.

For document classification rules, see [PUBLICATION_MATRIX.md](PUBLICATION_MATRIX.md).
