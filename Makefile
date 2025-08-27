# Makefile for Inventory-App (Python 3.13)

.PHONY: install fmt lint test coverage precommit

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
