.PHONY: help dev dev-services dev-stop api web postgres postgres-stop valkey valkey-stop preseed clean

# Configuration
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
	@echo "  postgres       - Start PostgreSQL container (port 5432)"
	@echo "  valkey         - Start Valkey/Redis container (port 6379)"
	@echo ""
	@echo "Database:"
	@echo "  preseed        - Import static EVE data"
	@echo ""
	@echo "Cleanup:"
	@echo "  postgres-stop  - Stop PostgreSQL container"
	@echo "  valkey-stop    - Stop Valkey container"
	@echo "  clean          - Stop all containers"

# Full dev stack - runs all services
dev: dev-services
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 2
	@$(MAKE) preseed
	@echo "Starting API and Web servers..."
	@echo "Press Ctrl+C to stop all services"
	@trap 'kill 0' INT; \
		(cd api && uv run uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000) & \
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
	cd api && uv run uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

# Web dev server
web:
	cd web && npm run dev

# Valkey (Redis-compatible) container
valkey:
	@docker run -d \
		--name linked-valkey \
		-p $(VALKEY_PORT):6379 \
		--rm \
		valkey/valkey:8
	@echo "Valkey started on port $(VALKEY_PORT)"

valkey-stop:
	@docker stop linked-valkey 2>/dev/null || true
	@echo "Valkey stopped"

# Delegate postgres targets to api/Makefile
postgres postgres-stop preseed:
	$(MAKE) -C api $@

clean: postgres-stop valkey-stop
	@echo "Cleanup complete"
