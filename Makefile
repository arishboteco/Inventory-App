# Makefile for Inventory-App (Python 3.13)

.PHONY: install fmt lint test coverage precommit ci changelog-add changelog-release changelog-show

# Install dev dependencies
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# Format code with Black
fmt:
	black .

# Lint with Ruff (fix issues automatically)
lint:
	ruff check . --fix

# Run tests
test:
	pytest

# Run tests with coverage report
coverage:
	pytest --cov=. --cov-report=term-missing

# Run pre-commit on all files
precommit:
	pre-commit run --all-files

# Run full CI locally: format, lint, and tests
ci: fmt lint test

# Changelog management
changelog-add:
	@echo "Usage: make changelog-add DESC='your change description' TYPE=feat"
	@python tools/changelog.py add "$(DESC)" --type "$(TYPE)"

changelog-release:
	@echo "Usage: make changelog-release VERSION=2.2.0"
	@python tools/changelog.py release "$(VERSION)"

changelog-show:
	@python tools/changelog.py unreleased

.PHONY: up
# Ensure the dev server is running on port 8000
up:
	bash scripts/ensure-port-8000.sh 8000
