.PHONY: setup dev up down logs test lint build config clean

setup:
	@test -f .env || cp .env.example .env
	python -m venv backend/.venv
	backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
	cd frontend && npm ci

dev:
	docker compose up --build

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd backend && python -m pytest

lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint && npm run typecheck

build:
	cd frontend && npm run build

config:
	docker compose config --quiet

clean:
	docker compose down --remove-orphans
