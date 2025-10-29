# Enforce bash shell for cross-platform compatibility
SHELL := /bin/bash
.RECIPEPREFIX = >
.PHONY: help install-uv venv activate sync install test lint format-check type-check scan-deps build-package export pre-commit clean editable-install ci show-project-structure install-trivy

# Variables
SRC = src
PROJECT_NAME = ml-orchestrator
VENV = .venv
PYTHON = $(VENV)/bin/python

# ==============================================================================
# HELP
# ==============================================================================

help: ## Shows this help message
> @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# ==============================================================================
# DEVELOPMENT LIFECYCLE
# ==============================================================================

install: editable-install ## Install project and all development dependencies
> uv run pre-commit install
> uv run pre-commit autoupdate

editable-install: venv ## Install project in editable mode with dev/test extras
> uv pip install -e .[dev,test]

test: ## Run all tests with pytest
> uv run pytest tests/ --cov=$(PROJECT_NAME) --junitxml=report.xml

lint-check: ## Check for linting errors with ruff and pylint
> uv run ruff check .
> uv run pylint src/ tests/

type-check: ## Check type hints with mypy
> uv run mypy src/

pre-commit: ## Run all pre-commit hooks on all files
> uv run pre-commit run --all-files

# ==============================================================================
# BUILD & UTILITIES
# ==============================================================================

build-package: ## Build the python wheel and source distribution
> uv run hatch build

version: ## Show the current project version
> uv run hatch version

export: ## Export dependencies to requirements.txt
> uv pip compile pyproject.toml -o requirements.txt

scan-deps: export install-trivy ## Scan exported dependencies for vulnerabilities
> trivy fs --format json --output trivy-report.json requirements.txt

clean: ## Remove all build artifacts and temporary files
> rm -rf build dist .mypy_cache .pytest_cache .ruff_cache *.egg-info

show-project-structure: ## Show the project's file structure
> find . -not -path '*/\.*' -not -path '*__pycache__*' | sort

# ==============================================================================
# INTERNAL TARGETS
# ==============================================================================

install-trivy: ## Install trivy if it's not already present
> command -v trivy >/dev/null 2>&1 || choco install trivy -y

install-uv: ## Install uv if it's not already present
> command -v uv >/dev/null 2>&1 || pip install uv

venv: install-uv ## Create a virtual environment if it doesn't exist
> test -d $(VENV) || uv venv $(VENV)

tag: ## Create a git tag with the project version
> @VERSION=$$(grep "version =" pyproject.toml | head -n 1 | cut -d '"' -f 2); \
> echo "Creating tag v$${VERSION}"; \
> git tag -a "v$${VERSION}" -m "Release v$${VERSION}"
