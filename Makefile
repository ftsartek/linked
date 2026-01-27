.PHONY: help dev dev-services dev-stop api web web-build postgres postgres-stop valkey valkey-stop migrations preseed schema clean cli test

# Configuration
POSTGRES_USER ?= linked
POSTGRES_PASSWORD ?= linked
POSTGRES_DB ?= linked
POSTGRES_PORT ?= 5432
VALKEY_PORT ?= 6379

help:
	@echo "Development Stack:"
	@echo "  dev            - Start all services (postgres, valkey, api, web)"
	@echo "  dev-services   - Start infrastructure only (postgres, valkey)"
	@echo "  dev-stop       - Stop all services"
	@echo ""
	@echo "Individual Services:"
	@echo "  api            - Start API server (port 8000)"
	@echo "  web            - Start web dev server (port 5173)"
	@echo "  web-build      - Build web for production (Node adapter)"
	@echo "  postgres       - Start PostgreSQL container (port 5432)"
	@echo "  valkey         - Start Valkey/Redis container (port 6379)"
	@echo ""
	@echo "Database:"
	@echo "  migrations     - Run database migrations"
	@echo "  preseed        - Import static EVE data"
	@echo ""
	@echo "Code Generation:"
	@echo "  schema         - Generate OpenAPI schema and TypeScript types"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run API integration tests (requires Docker)"
	@echo ""
	@echo "CLI:"
	@echo "  cli            - Run CLI command (make cli CMD=\"...\")"
	@echo ""
	@echo "Cleanup:"
	@echo "  postgres-stop  - Stop PostgreSQL container"
	@echo "  valkey-stop    - Stop Valkey container"
	@echo "  clean          - Stop all containers"

# Full dev stack - runs all services
dev: dev-services
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 2
	@$(MAKE) migrations
	@$(MAKE) preseed
	@echo "Starting API and Web servers..."
	@echo "Press Ctrl+C to stop all services"
	@trap '$(MAKE) dev-stop; exit 0' INT TERM; \
		(cd api && uv run uvicorn src.api.main:app --reload --timeout-graceful-shutdown=5 --host 0.0.0.0 --port 8000) & \
		(cd web && npm run dev) & \
		wait

# Start just infrastructure (for running api/web separately)
dev-services: postgres valkey
	@echo ""
	@echo "Infrastructure ready:"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Valkey:     localhost:$(VALKEY_PORT)"
	@echo ""
	@echo "Run 'make api' and 'make web' in separate terminals"

dev-stop: postgres-stop valkey-stop
	@echo "All services stopped"

# API server
api:
	cd api && uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Web dev server
web:
	cd web && npm run dev

# Web production build
web-build:
	cd web && npm run build

# Valkey (Redis-compatible) container
valkey:
	@docker run -d \
		--name linked-valkey \
		-p $(VALKEY_PORT):6379 \
		--rm \
		valkey/valkey:9
	@echo "Valkey started on port $(VALKEY_PORT)"

valkey-stop:
	@docker stop linked-valkey 2>/dev/null || true
	@echo "Valkey stopped"

# Generate OpenAPI schema and TypeScript types
schema:
	cd api && uv run linked schema -o ../openapi.json
	cd web && npx openapi-typescript ../openapi.json -o src/lib/client/schema.d.ts
	@rm -f openapi.json
	cd web && npx prettier --write src/lib/client/schema.d.ts

# PostgreSQL container
postgres:
	@docker run -d \
		--name linked-postgres \
		-e POSTGRES_USER=$(POSTGRES_USER) \
		-e POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
		-e POSTGRES_DB=$(POSTGRES_DB) \
		-p $(POSTGRES_PORT):5432 \
		--rm \
		pgvector/pgvector:pg18-trixie
	@echo "PostgreSQL started on port $(POSTGRES_PORT)"
	@echo "Connection: postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost:$(POSTGRES_PORT)/$(POSTGRES_DB)"

postgres-stop:
	@docker stop linked-postgres 2>/dev/null || true
	@echo "PostgreSQL stopped"

# Import static EVE data
preseed:
	cd api && uv run linked preseed

# Run migrations
migrations:
	cd api && uv run linked migrate

# Run CLI commands
cli:
	cd api && uv run linked $(CMD)

# Run API integration tests
test:
	cd api && CONFIG_FILE=tests/config.test.yaml uv run pytest tests/ -v

clean: postgres-stop valkey-stop
	@echo "Cleanup complete"
