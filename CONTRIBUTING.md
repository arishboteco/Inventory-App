# Contributing to Inventory-App

Thank you for taking the time to contribute! This guide summarizes our branching model, commit style, and review steps. For a complete view of the day-to-day workflow—including changelog management—see [docs/development/DEVELOPMENT_WORKFLOW.md](docs/development/DEVELOPMENT_WORKFLOW.md).

## Branching

- Work off the `main` branch.
- Name branches using the pattern:
  - `feature/<short-description>` for new features
  - `fix/<short-description>` for bug fixes
  - `docs/<short-description>` for documentation changes
- Keep branches up to date with `main` and remove them after merge.

## Commit Messages

- Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
  - `feat: add inventory import command`
  - `fix: correct stock calculation`
  - `docs: update API examples`
- Use the imperative mood and keep subject lines under 50 characters.
- Reference related issues when applicable.

## Review Process

1. Follow the [Development Workflow](docs/development/DEVELOPMENT_WORKFLOW.md) for changelog updates and daily routines.
2. Before pushing, ensure checks pass locally:
   ```bash
   make fmt && make lint && make test
   ```
3. Update relevant documentation and changelog entries.
4. Open a pull request:
   - Fill out the PR template and link related issues.
   - Request review from maintainers.
5. Address review feedback and keep commits focused.
6. A maintainer merges after approvals and passing CI.

See the [README](README.md) for project overview and setup instructions.
