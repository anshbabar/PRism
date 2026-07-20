.DEFAULT_GOAL := help

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest

.PHONY: help venv install web-install dev web test lint fmt typecheck eval db-up db-down clean

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

eval: ## Run the evaluation harness (stub until Milestone 6)
	@echo "eval: benchmark harness lands in Milestone 6 (see docs/technical-design.md §11). No-op for now."

db-up: ## Start Postgres (pgvector) via docker compose
	docker compose up -d db

db-down: ## Stop Postgres
	docker compose down

clean: ## Remove caches and the virtualenv
	rm -rf $(VENV) .pytest_cache .ruff_cache .mypy_cache **/__pycache__
