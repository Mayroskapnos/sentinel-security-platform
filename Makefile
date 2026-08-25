.PHONY: setup dev up down logs test lint build config migrate rules seed demo reset telemetry telemetry-burst detection-demo clean

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
	cd backend && ruff check . ../tools && ruff format --check . ../tools
	cd frontend && npm run lint && npm run typecheck

build:
	cd frontend && npm run build

config:
	docker compose config --quiet

migrate:
	docker compose exec -T backend alembic upgrade head

rules:
	docker compose exec -T backend python -m app.cli.sync_rules

seed:
	docker compose exec -T backend python -m app.cli.seed

demo: seed

reset:
	docker compose exec -T backend python -m app.cli.seed --reset

telemetry:
	python tools/telemetry_producer.py --mode stream --count 25 --interval 2

telemetry-burst:
	python tools/telemetry_producer.py --mode burst --count 100

detection-demo:
	python tools/telemetry_producer.py --mode detection-demo

clean:
	docker compose down --remove-orphans
