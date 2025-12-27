.PHONY: help postgres postgres-stop preseed clean

POSTGRES_USER ?= linked
POSTGRES_PASSWORD ?= linked
POSTGRES_DB ?= linked
POSTGRES_PORT ?= 5432

help:
	@echo "Available targets:"
	@echo "  postgres       - Start PostgreSQL container"
	@echo "  postgres-stop  - Stop PostgreSQL container"
	@echo "  preseed        - Run database preseed (imports static data)"
	@echo "  clean          - Stop containers and clean up"

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

preseed:
	cd $(dir $(abspath $(lastword $(MAKEFILE_LIST)))) && uv run linked preseed

clean: postgres-stop
	@echo "Cleanup complete"
