SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help install dev dev-backend dev-runtime dev-frontend test test-backend test-runtime clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-16s %s\n", $$1, $$2}'

install: ## Install frontend and backend dependencies
	python3 -m venv .venv
	./.venv/bin/pip install --upgrade pip
	./.venv/bin/pip install -r apps/api/requirements.txt
	./.venv/bin/pip install -r browser-runtime/requirements.txt
	npm install --prefix apps/web

dev: ## Start frontend and backend placeholder services
	./scripts/dev/start-local.sh

dev-backend: ## Start the backend placeholder service
	./scripts/dev/start-backend.sh

dev-runtime: ## Start the browser-runtime service
	./scripts/dev/start-browser-runtime.sh

dev-frontend: ## Start the frontend placeholder service
	./scripts/dev/start-frontend.sh

test: ## Run the current repo test surface
	$(MAKE) test-backend
	$(MAKE) test-runtime

test-backend: ## Run backend tests
	./scripts/test/run-backend-tests.sh

test-runtime: ## Run browser-runtime tests
	./scripts/test/run-runtime-tests.sh

clean: ## Remove common local build output
	rm -rf apps/web/.next apps/web/node_modules apps/api/.pytest_cache
	find apps/api -type d -name __pycache__ -prune -exec rm -rf {} \;
	find browser-runtime -type d -name __pycache__ -prune -exec rm -rf {} \;
