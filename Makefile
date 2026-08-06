.PHONY: help install dev backend worker frontend test test-backend test-frontend lint docker-up docker-down seed demo docs

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install backend deps (editable) and frontend deps
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

dev: ## Run backend + frontend + worker (dev mode)
	@echo "Run in separate terminals:"
	@echo "  1. cd backend && uvicorn app.main:app --reload --port 8000"
	@echo "  2. cd backend && celery -A app.workers.celery_app.celery_app worker -l info"
	@echo "  3. cd frontend && npm run dev"

backend: ## Start backend API only
	cd backend && uvicorn app.main:app --reload --port 8000

worker: ## Start celery worker only
	cd backend && celery -A app.workers.celery_app.celery_app worker -l info

frontend: ## Start frontend dev server
	cd frontend && npm run dev

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend pytest suite
	cd backend && pytest -q

test-frontend: ## Run frontend tests
	cd frontend && npm run test

lint: ## Lint backend and frontend
	cd backend && ruff check app tests
	cd frontend && npx eslint src --ext .ts,.tsx

docker-up: ## Build & start full stack via Docker Compose
	docker compose up -d --build

docker-down: ## Stop full stack
	docker compose down

seed: ## Seed demo project + synthetic multi-omics data
	cd backend && python scripts/seed_demo.py

docs: ## Serve docs locally
	@echo "Open docs/*.md in your editor or use: npx markdown-preview"

demo: seed ## Alias for quick demo setup
