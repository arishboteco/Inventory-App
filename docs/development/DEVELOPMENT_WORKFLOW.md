# Development Workflow Guide

## Changelog Best Practices

We maintain a comprehensive changelog to track all development progress and ensure continuity between sessions.

### Daily Workflow

1. **Before Starting Work**
   ```bash
   # Check current unreleased changes
   make changelog-show
   # or
   python tools/changelog.py unreleased
   ```

2. **During Development**
   ```bash
   # Add entries as you work
   make changelog-add DESC="Add new feature X" TYPE=feat
   make changelog-add DESC="Fix bug in component Y" TYPE=fix
   make changelog-add DESC="Update documentation" TYPE=docs
   ```

3. **Before Committing**
   ```bash
   # Run quality checks
   make fmt && make lint && make test
   
   # Review changelog
   make changelog-show
   ```

4. **Creating Releases**
   ```bash
   # Move unreleased items to versioned release
   make changelog-release VERSION=2.2.0
   ```

### Changelog Entry Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New features | "Add user authentication system" |
| `fix` | Bug fixes | "Fix pagination in items list" |
| `docs` | Documentation | "Update API documentation" |
| `perf` | Performance improvements | "Optimize database queries" |
| `test` | Test additions/changes | "Add integration tests for orders" |
| `refactor` | Code refactoring | "Restructure service layer" |
| `style` | Code style changes | "Apply Black formatting" |
| `chore` | Maintenance tasks | "Update dependencies" |

### Session Handoff Protocol

**At End of Session:**
1. Update CHANGELOG.md with all completed work
2. Ensure all changes are committed
3. Update any status documentation
4. Leave clear notes in unreleased section

**At Start of Session:**
1. Review CHANGELOG.md unreleased section
2. Check recent commits with `git log --oneline -10`
3. Review any status files (PROGRESS_SUMMARY.md, etc.)
4. Run tests to ensure starting from clean state

### Integration with Git

The changelog complements your Git commit history:
- **Commits**: Technical implementation details
- **Changelog**: User-facing feature and business impact summary
- **Status Files**: Project milestone documentation

### Makefile Commands

```bash
# Development workflow
make install          # Install dependencies
make fmt             # Format code with Black
make lint            # Lint and auto-fix with Ruff
make test            # Run pytest suite
make coverage        # Run tests with coverage report

# Changelog management
make changelog-show                                    # Show unreleased changes
make changelog-add DESC="description" TYPE=feat       # Add new entry
make changelog-release VERSION=2.2.0                  # Create release
```

This workflow ensures we maintain clear development history and can easily resume work across sessions.
