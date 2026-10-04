.PHONY: up down api worker collector watchdog retention web test lint lint-imports typecheck build backup restore
up:
	docker compose up -d neo4j
down:
	docker compose down
api:
	cd backend && .venv/bin/uvicorn jevtriage.main:app --reload --host 0.0.0.0
worker:
	cd backend && .venv/bin/python -m jevtriage.jobs.worker
collector:
	cd backend && .venv/bin/python -m jevtriage.journal.collector
watchdog:
	cd backend && .venv/bin/python -m jevtriage.journal.watchdog
retention:
	cd backend && .venv/bin/python -m jevtriage.ops.retention $(RETENTION_ARGS)
web:
	cd frontend && npm run dev
test:
	cd backend && .venv/bin/pytest
	cd frontend && npm run test
lint: lint-imports
	cd backend && .venv/bin/ruff check jevtriage tests
	cd backend && .venv/bin/ruff check --isolated --preview --select PLC2701 jevtriage
lint-imports:
	cd backend && .venv/bin/lint-imports
typecheck:
	cd frontend && npm run typecheck
build:
	cd frontend && npm run build

.PHONY: test-fault
test-fault:
	bash scripts/fault/run.sh
BACKUP_DIR ?= artifacts/backups/$(shell date -u +%Y%m%dT%H%M%SZ)
RESTORE_DATA_DIR ?=
RESTORE_NEO4J_DIR ?=
DATA_DIR ?= $(CURDIR)/.data
NEO4J_DATA_DIR ?= $(CURDIR)/.data/neo4j
COMPOSE_PROJECT ?= jevtriage-backup
NEO4J_CONTAINER ?= jevtriage-backup-neo4j-1
NEO4J_BOLT_PORT ?= 7689
backup:
	bash scripts/ops/backup.sh --backup-dir "$(BACKUP_DIR)" --container "$(NEO4J_CONTAINER)" --project "$(COMPOSE_PROJECT)" --port "$(NEO4J_BOLT_PORT)" --neo4j-volume "$(NEO4J_DATA_DIR)" --data-dir "$(DATA_DIR)"
restore:
	test -n "$(RESTORE_DATA_DIR)"
	bash scripts/ops/restore.sh --backup-dir "$(BACKUP_DIR)" --new-data-dir "$(RESTORE_DATA_DIR)" $(if $(RESTORE_NEO4J_DIR),--new-neo4j-dir "$(RESTORE_NEO4J_DIR)",) --container "$(NEO4J_CONTAINER)" --project "$(COMPOSE_PROJECT)" --port "$(NEO4J_BOLT_PORT)"

.PHONY: load
load:
	bash loadtest/run.sh

.PHONY: test-acceptance
# T21 acceptance (functional/safety/permission gates): live Jev + shared Neo4j, dedicated tenants.
# Writes artifacts/validation/t21/<run-id>/. ACC_SKIP_UI=1 skips the Playwright part.
test-acceptance:
	bash backend/tests/acceptance/run.sh
