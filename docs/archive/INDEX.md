# Archive Documentation Index

**Last Updated**: 2026-04-27  
**Version**: v0.3.1  
**Purpose**: Index of historical and archived documentation

## Archive Contents

This public archive contains sanitized historical documents that are safe to keep
on GitHub. Internal audits, deep code reviews, fix logs, and generated validation
reports have been moved to `internal_docs/docs_archive/`.

### Summary Documents (Consolidated)

**Refactoring Summary** (1 file)
- `REFACTORING_SUMMARY.md` - Consolidated refactoring reports

**Release Summary** (1 file)
- `RELEASE_v0.2.5_SUMMARY.md` - Consolidated v0.2.5 release documents

**Version Summary** (2 files)
- `V0.3.0_SUMMARY.md` - Consolidated v0.3.0 status reports
- `V0.3.0_RELEASE_NOTES.md` - Complete v0.3.0 release notes

### Other Historical Documents

**Documentation & Changelog**
- Public changelog and release history should remain in root `CHANGELOG.md`,
  `RELEASE_*.md`, or sanitized archive files.

**Chinese Documentation** (1 file)
- `README_CN.md` - Chinese version of README (archived)

## How to Use This Archive

1. **For current operational guidance**: Use active core documents in `docs/` root
2. **For historical context**: Reference archived documents with understanding they are point-in-time snapshots
3. **For audit/traceability**: use public archive files only for sanitized history; use internal archives for sensitive audit evidence
4. **When conflicts arise**: Active documents take precedence over archived ones

## Maintenance Policy

- Historical documents are preserved as-is for audit purposes
- No updates are made to archived documents unless correcting factual errors
- Documents are moved to archive when they become historical
- Quarterly review recommended to identify documents that should be consolidated

---

**Maintained by**: Bronit Team  
**Total Archived Documents**: review with `git ls-files docs/archive`
