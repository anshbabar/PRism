.DEFAULT_GOAL := help

VENV := .venv
# Prefer the local virtualenv; fall back to PATH python (e.g. CI installs deps
# into the runner's Python without creating a .venv).
PY := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python)
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest

.PHONY: help venv install web-install dev web test lint fmt typecheck eval db-up db-down migrate clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

$(VENV): ## Create the Python virtualenv
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

venv: $(VENV) ## Alias for creating the virtualenv

install: $(VENV) ## Install backend deps (editable, with dev extras)
	$(PIP) install -e ".[dev]"

web-install: ## Install frontend deps
	cd web && npm install

dev: ## Run the backend API with autoreload (http://localhost:8000)
	$(VENV)/bin/uvicorn app.main:app --reload --port 8000

web: ## Run the frontend dev server (http://localhost:3000)
	cd web && npm run dev

test: ## Run backend tests
	$(PYTEST)

lint: ## Lint backend (ruff) and frontend (eslint)
	$(RUFF) check app tests
	$(RUFF) format --check app tests
	cd web && npm run lint

fmt: ## Auto-format backend code
	$(RUFF) check --fix app tests
	$(RUFF) format app tests

typecheck: ## Type-check backend (mypy) and frontend (tsc)
	$(MYPY)
	cd web && npm run typecheck

eval: ## Run the evaluation harness (mock provider) and enforce smoke invariants
	$(PY) eval/run_eval.py --check

db-up: ## Start Postgres (pgvector) via docker compose
	docker compose up -d db

db-down: ## Stop Postgres
	docker compose down

migrate: ## Apply database migrations (alembic upgrade head)
	$(PY) -m alembic upgrade head

clean: ## Remove caches and the virtualenv
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache **/__pycache__
