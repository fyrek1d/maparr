.PHONY: help install dev build test lint type-check clean docker-build docker-run

# ===== Help =====
help:
	@echo "Makefile for Maparr development"
	@echo ""
	@echo "Usage:"
	@echo "  make install       Install backend and frontend dependencies"
	@echo "  make dev           Run both backend and frontend in development mode"
	@echo "  make build         Build production assets (frontend) and backend wheel"
	@echo "  make test          Run backend tests"
	@echo "  make lint          Run linters (backend + frontend)"
	@echo "  make type-check    Run TypeScript type checking"
	@echo "  make docker-build  Build the Docker image"
	@echo "  make docker-run    Run the Docker container (requires .env)"
	@echo ""
	@echo "Development:"
	@echo "  make backend-dev   Run backend dev server (uvicorn)"
	@echo "  make frontend-dev  Run frontend dev server (vite)"
	@echo ""
	@echo "Quality:"
	@echo "  make format        Format code (backend: ruff, frontend: prettier)"

# ===== Installation =====
install:
	pip install -e "./backend[dev]"
	npm ci --prefix frontend

# ===== Development =====
dev:
	@echo "Starting development servers..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173 (proxied to backend)"
	(@cd backend && uvicorn maparr.main:create_app --factory --reload --host 0.0.0.0 --port 8000) & \
	cd frontend && npm run dev

backend-dev:
	cd backend && uvicorn maparr.main:create_app --factory --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && npm run dev

# ===== Build =====
build:
	npm run build --prefix frontend
	pip wheel --wheel-dir=dist ./backend

# ===== Testing =====
test:
	cd backend && pytest

# ===== Linting & Type Checking =====
lint:
	ruff check ./backend
	npm run lint --prefix frontend

type-check:
	npm run type-check --prefix frontend

format:
	ruff check --fix ./backend
	npm run format --prefix frontend

# ===== Cleaning =====
clean:
	rm -rf ./backend/dist ./frontend/dist ./frontend/node_modules
	pip cache purge
	npm cache clean --force

# ===== Docker =====
docker-build:
	docker build -t maparr:latest .

docker-run:
	docker run -d \
	  --name maparr \
	  -p 8000:8000 \
	  -v $(PWD)/data:/app/data \
	  --env-file .env \
	  maparr:latest

# ===== Utilities =====
shell:
	docker run -it --rm \
	  -v $(PWD):/app \
	  -w /app \
	  python:3.11-slim bash