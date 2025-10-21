.RECIPEPREFIX = >
.PHONY: type-check

# Variables
SRC = src
PROJECT_NAME = ml-orchestrator
PYTHON = C:\Users\J_Nor\AppData\Local\Programs\Python\Python313\python.exe
VENV = .venv

type-check:
>uv run mypy . \
		--untyped-calls-exclude=google.oauth2.service_account \
		--untyped-calls-exclude=google.auth \
		--untyped-calls-exclude=google.cloud.aiplatform