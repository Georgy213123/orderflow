# OrderFlow — единый интерфейс кейса. Цели одинаковы во всех кейсах витрины.
SHELL := /bin/bash
.DEFAULT_GOAL := help

PG_PORT ?= 55301
API_PORT ?= 8301
WEB_PORT ?= 5301
DATABASE_URL ?= postgresql+psycopg://postgres@localhost:$(PG_PORT)/orderflow
TEST_DATABASE_URL ?= postgresql+psycopg://postgres@localhost:$(PG_PORT)/orderflow_test

BACKEND := cd backend &&
FRONTEND := cd frontend &&
E2E := cd e2e &&

.PHONY: help install up down dev migrate seed lint format test test-backend test-frontend e2e audit openapi

help: ## список целей
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

install: ## зависимости бэкенда, фронта и e2e
	$(BACKEND) uv sync --frozen
	$(FRONTEND) npm ci
	$(E2E) npm ci && npx playwright install chromium

up: ## весь стенд в Docker: postgres, backend, frontend
	docker compose up --build

down: ## остановить стенд Docker
	docker compose down

migrate: ## миграции на DATABASE_URL
	$(BACKEND) DATABASE_URL=$(DATABASE_URL) uv run alembic upgrade head

seed: ## справочник материалов
	$(BACKEND) DATABASE_URL=$(DATABASE_URL) uv run python -m app.seed

dev: migrate seed ## локально без Docker (нужен PostgreSQL на DATABASE_URL)
	@echo "API: http://localhost:$(API_PORT)/docs   UI: http://localhost:$(WEB_PORT)"
	@trap 'kill 0' EXIT; \
	(cd backend && DATABASE_URL=$(DATABASE_URL) uv run uvicorn app.main:app --reload --port $(API_PORT)) & \
	(cd frontend && npm run dev) & \
	wait

lint: ## ruff, mypy, eslint, tsc, prettier
	$(BACKEND) uv run ruff check . && uv run ruff format --check . && uv run mypy .
	$(FRONTEND) npx eslint . && npx tsc --noEmit && npx prettier --check .
	$(E2E) npx tsc --noEmit
	$(FRONTEND) npx prettier --check ../e2e/tests ../e2e/playwright.config.ts

format: ## автоформат
	$(BACKEND) uv run ruff format . && uv run ruff check --fix .
	$(FRONTEND) npx prettier --write . ../e2e/tests ../e2e/playwright.config.ts

test: test-backend test-frontend ## unit + integration бэкенда, unit фронта

test-backend:
	$(BACKEND) DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest --cov --cov-report=term-missing:skip-covered

test-frontend:
	$(FRONTEND) npx vitest run

e2e: ## Playwright: поднимает backend и frontend сам, если они не запущены
	$(E2E) DATABASE_URL=$(DATABASE_URL) npx playwright test

audit: ## уязвимости зависимостей
	$(BACKEND) uv run pip-audit
	$(FRONTEND) npm audit --audit-level=high
	$(E2E) npm audit --audit-level=high

openapi: ## выгрузить контракт в docs/03-design/openapi.yaml
	$(BACKEND) uv run python -m scripts.export_openapi
