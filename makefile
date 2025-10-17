.RECIPEPREFIX = >
.PHONY: install-uv venv activate sync install test lint format-check type-check scan-deps build-package publish-package export build-docker-image tag-docker-image push-docker-image clean-docker-image pre-commit clean editable-install ci show-project-structure

# Variables
SRC = src
PROJECT_NAME = ml-orchestrator
REGISTRY = ghcr.io/your-username/ml-orchestrator
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

lint:
>uv run ruff check . --fix
>uv run flake8 src/ scripts/ tests/ examples/
>uv run pylint src/ scripts/ tests/ examples/

format-check:
>uv run pre-commit run ruff-format --all-files
>uv run ruff format --diff .

type-check:
>uv run mypy src/ scripts/ tests/ examples/

mypy-paths:
>uv run mypy --python-path . scripts/

scan-deps:
>trivy fs --format json --output trivy-report.json requirements.txt

pre-commit:
>uv pip install pre-commit ruff
>uv run pre-commit install
>uv run pre-commit autoupdate
>if not exist .gitattributes echo * text=lf > .gitattributes
>if exist src icacls src /grant %USERNAME%:F /T
>if exist tests icacls tests /grant %USERNAME%:F /T
>uv run ruff check . --fix
>uv run pre-commit run end-of-file-fixer --all-files --show-diff-on-failure
>uv run pre-commit run trailing-whitespace --all-files --show-diff-on-failure
>uv run pre-commit run ruff --all-files --hook-stage manual
>uv run pre-commit run ruff-format --all-files --hook-stage manual
>uv run pre-commit run --all-files --hook-stage manual

build-package:
>uv build

publish-package:
>uv publish --registry https://ghcr.io/api/v4/packages/pypi --token $(UV_PUBLISH_TOKEN)

export:
>uv pip compile pyproject.toml -o requirements.txt

build-docker-image:
>docker build -t $(PROJECT_NAME):${DOCKER_TAG:-latest} .

tag-docker-image:
>docker tag $(PROJECT_NAME):${DOCKER_TAG:-latest} $(REGISTRY):${DOCKER_TAG:-latest}

push-docker-image:
>docker push $(REGISTRY):${DOCKER_TAG:-latest}

clean-docker-image:
>docker rmi $(PROJECT_NAME):${DOCKER_TAG:-latest} $(REGISTRY):${DOCKER_TAG:-latest} -f --no-prune

clean:
>Remove-Item -Recurse -Force -Path $(VENV),dist,*.egg-info,.pytest_cache,.mypy_cache,*.xml -ErrorAction SilentlyContinue

ci:
>gh workflow run ci.yml --field branch=$(git rev-parse --abbrev-ref HEAD)

show-project-structure:
>Get-ChildItem -Recurse | Select-Object FullName