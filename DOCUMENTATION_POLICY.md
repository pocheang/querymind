# Documentation Policy

## Public vs Internal Documentation

This project maintains a clear separation between public and internal documentation to ensure clean GitHub presentation while preserving internal development resources.

## Public Documentation (Visible on GitHub)

### Root Level
- `README.md` - Main project documentation, installation, and usage
- `CHANGELOG.md` - Version history and release notes
- `RELEASE_*.md` - Specific release announcements
- `LICENSE` - Project license

### docs/ Directory
- `docs/README.md` - Documentation index
- `docs/API_SETTINGS_GUIDE.md` - API configuration and usage
- `docs/PERFORMANCE_OPTIMIZATION.md` - Performance tuning guide
- `docs/VERSION_HISTORY.md` - Detailed version tracking

## Internal Documentation (Hidden from GitHub)

All internal documentation is stored in `internal_docs/` and excluded via `.gitignore`:

### Categories
1. **Project Audits** (`internal_docs/project_audit/`)
   - System audits, security reviews, issue tracking
   
2. **Development Guides** (`internal_docs/`)
   - Git workflows, release processes, security procedures
   - CLAUDE.md (AI assistant instructions)
   
3. **Documentation Standards** (`internal_docs/docs_archive/`)
   - Internal documentation maintenance guidelines
   - Version documentation standards
   
4. **Completion Reports** (`internal_docs/`)
   - Version milestone reports
   - Refactoring completion summaries

## Guidelines

### When to Make Documentation Public
- User-facing features and APIs
- Installation and setup instructions
- Configuration guides
- Performance optimization tips
- Version history and changelogs

### When to Keep Documentation Internal
- Security audits and vulnerability reports
- Internal development processes
- Strategic planning documents
- AI assistant configurations
- Incomplete or draft documentation
- Team-specific workflows

## Maintenance

### Adding New Documentation
1. Determine if documentation is public or internal
2. Place in appropriate directory
3. For internal docs, verify `.gitignore` exclusion
4. Update relevant README.md files

### Before Committing
1. Review `git status` for unintended public documentation
2. Ensure no sensitive information in public docs
3. Verify `.gitignore` patterns are working
4. Check that internal_docs/ is not staged

## Verification

To verify documentation separation:
```bash
# Check what will be committed
git status

# Verify internal_docs is ignored
git check-ignore internal_docs/

# List public documentation
ls -1 *.md docs/*.md
```

Expected public files:
- Root: `README.md`, `CHANGELOG.md`, `RELEASE_*.md`, `DOCUMENTATION_POLICY.md`
- docs/: `README.md`, `API_SETTINGS_GUIDE.md`, `PERFORMANCE_OPTIMIZATION.md`, `VERSION_HISTORY.md`
