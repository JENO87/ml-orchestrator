.RECIPEPREFIX = >
.PHONY: install-uv venv activate sync install test lint format-check type-check scan-deps build-package publish-package export build-docker-image tag-docker-image push-docker-image clean-docker-image pre-commit clean editable-install ci show-project-structure

# Variables
SRC = src
PROJECT_NAME = ml-orchestrator
PYTHON = C:\Users\J_Nor\AppData\Local\Programs\Python\Python313\python.exe
VENV = .venv

help:
>powershell -Command "Get-Content Makefile | Select-String '^[a-zA-Z0-9_-]+:' | ForEach-Object { $$_.Line.Split(':')[0] } | Sort-Object | ForEach-Object { Write-Output $$_ }"

install-uv:
>where uv >nul 2>&1 || pip install uv

venv:
>if not exist $(VENV) uv venv --python $(PYTHON) $(VENV)

activate:
>powershell -Command "& '$(VENV)\Scripts\Activate.ps1'"

check-env:
>powershell -Command "Write-Output 'PYTHONPATH: $$env:PYTHONPATH'; Write-Output 'Current Dir: $$(Get-Location)'"

run-debug:
>powershell -Command "$$env:PYTHONPATH='$(SRC)'; uv run python -m pdb '$(RUN)'"

sync:
>uv sync --all-extras --no-reinstall --frozen

install:
>powershell -Command "$$env:VIRTUAL_ENV='C:\Users\J_Nor\DataspellProjects\ml-orchestrator\.venv'; Invoke-Expression 'make install-uv'; Invoke-Expression 'make venv'; Invoke-Expression 'make sync'; Invoke-Expression 'make editable-install'; uv run pre-commit install; uv run pre-commit autoupdate"

editable-install:
>uv pip install -e .[dev,test] --python $(PYTHON)

test:
>uv run pytest tests/ --cov=$(PROJECT_NAME) --junitxml=report.xml

lint-fix:
>uv run ruff check . --fix
>uv run flake8 src/ scripts/ tests/ examples/
>uv run pylint src/ scripts/ tests/ examples/

lint-check:
>uv run ruff check .
>uv run flake8 src/ scripts/ tests/ examples/
>uv run pylint src/ scripts/ tests/ examples/

format-check:
>uv run pre-commit run ruff-format --all-files
>uv run ruff format --diff .

type-check:
>uv run mypy src/ml_orchestrator \
		--untyped-calls-exclude=google.oauth2.service_account \
		--untyped-calls-exclude=google.auth \
		--untyped-calls-exclude=google.cloud.aiplatform

mypy-paths:
>uv run mypy --python-path . scripts/

scan-deps:
>trivy fs --format json --output trivy-report.json requirements.txt

pre-commit:
>uv pip install pre-commit
>uv run pre-commit install
>uv run pre-commit autoupdate
>uv run pre-commit run --all-files

build-package:
>uv build

publish-package:
>uv publish --registry https://ghcr.io/api/v4/packages/pypi --token $(UV_PUBLISH_TOKEN)

export:
>uv pip compile pyproject.toml -o requirements.txt

clean:
>git clean -fdX

ci:
>gh workflow run ci.yml --field branch=$(git rev-parse --abbrev-ref HEAD)

show-project-structure:
>Get-ChildItem -Recurse | Select-Object FullName
