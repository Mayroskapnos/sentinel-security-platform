.PHONY: setup dev up down logs test lint build config migrate rules seed demo reset telemetry telemetry-burst detection-demo lab-up lab-down lab-logs lab-status lab-reset lab-activity-web lab-activity-db lab-activity-auth lab-activity-privilege simulator-status scenario-list scenario-run scenario-history validate-scenarios validate-correlation network-rebuild incident-rebuild network-integration test-lab clean

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
	cd backend && ruff check . ../tools ../lab && ruff format --check . ../tools ../lab
	cd frontend && npm run lint && npm run typecheck

build:
	cd frontend && npm run build

config:
	docker compose config --quiet
	python tools/validate_lab_compose.py

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

lab-up:
	docker compose up --build -d

lab-down:
	docker compose stop sentinel-collector sentinel-lab-gateway sentinel-employee-01 sentinel-employee-02 sentinel-admin sentinel-web sentinel-db

lab-logs:
	docker compose logs -f sentinel-collector sentinel-lab-gateway sentinel-employee-01 sentinel-employee-02 sentinel-admin sentinel-web sentinel-db

lab-status:
	docker compose ps sentinel-collector sentinel-lab-gateway sentinel-employee-01 sentinel-employee-02 sentinel-admin sentinel-web sentinel-db

lab-reset:
	python tools/lab_reset.py

lab-activity-web:
	docker compose exec -T sentinel-employee-01 python /app/agent.py activity web

lab-activity-db:
	docker compose exec -T sentinel-employee-01 python /app/agent.py activity database

lab-activity-auth:
	docker compose exec -T sentinel-employee-01 python /app/agent.py activity auth-success

lab-activity-privilege:
	docker compose exec -T sentinel-admin python /app/agent.py activity privilege

simulator-status:
	curl --fail --silent http://127.0.0.1:8000/api/v1/simulator/status

scenario-list:
	curl --fail --silent http://127.0.0.1:8000/api/v1/simulator/scenarios

scenario-run:
	@test -n "$(SCENARIO)" || (echo "SCENARIO is required, for example SCENARIO=SCN-001" && exit 2)
	curl --fail --silent --request POST http://127.0.0.1:8000/api/v1/simulator/run/$(SCENARIO)

scenario-history:
	curl --fail --silent http://127.0.0.1:8000/api/v1/simulator/runs

validate-scenarios:
	cd backend && python -m app.cli.validate_scenarios

validate-correlation:
	cd backend && python -m app.cli.validate_correlation

network-rebuild:
	docker compose exec -T backend python -m app.cli.rebuild_network_connections

incident-rebuild:
	docker compose exec -T backend python -m app.cli.rebuild_incidents

network-integration:
	backend/.venv/bin/python tools/network_integration_test.py

test-lab:
	python tools/lab_integration_test.py

clean:
	docker compose down --remove-orphans
