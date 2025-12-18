# =============================================================================
# 보험 약관 비교 RAG 시스템 - Makefile
# =============================================================================

.PHONY: help up down llm-on cost-guard llm-off smoke-test u48-eval

COMPOSE_BASE = docker compose -f docker-compose.demo.yml
CONTAINER_API = inca_demo_api

help:
	@echo "Usage:"
	@echo "  make up          - Start demo environment (LLM OFF)"
	@echo "  make down        - Stop demo environment"
	@echo "  make llm-on      - Restart API with LLM_ENABLED=1"
	@echo "  make cost-guard  - Restart API with LLM_ENABLED=1 + LLM_COST_GUARD=1"
	@echo "  make llm-off     - Restart API with LLM_ENABLED=0 (default)"
	@echo "  make smoke-test  - Run LLM trace smoke tests"
	@echo "  make u48-eval    - Run U-4.8 evaluation"

# ---------------------------------------------------------------------------
# Demo Environment
# ---------------------------------------------------------------------------

up:
	$(COMPOSE_BASE) up -d
	@echo "Demo started. Web: http://localhost, API: http://localhost:8000"

down:
	$(COMPOSE_BASE) down

# ---------------------------------------------------------------------------
# LLM Mode Switching (U-4.8.1)
# ---------------------------------------------------------------------------

llm-on:
	@echo "Restarting API with LLM_ENABLED=1..."
	$(COMPOSE_BASE) -f ops/compose.override.llm-on.yml up -d api
	@sleep 3
	@echo "Waiting for API health check..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		curl -sf http://localhost:8000/health > /dev/null 2>&1 && break || sleep 1; \
	done
	@docker exec $(CONTAINER_API) printenv | grep -E "LLM_ENABLED|LLM_COST_GUARD" || true
	@echo ""
	@echo "LLM ON mode ready. Run: ./tools/run_llm_trace_smoke.sh --llm-on"

cost-guard:
	@echo "Restarting API with LLM_ENABLED=1 + LLM_COST_GUARD=1..."
	$(COMPOSE_BASE) -f ops/compose.override.cost-guard.yml up -d api
	@sleep 3
	@echo "Waiting for API health check..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		curl -sf http://localhost:8000/health > /dev/null 2>&1 && break || sleep 1; \
	done
	@docker exec $(CONTAINER_API) printenv | grep -E "LLM_ENABLED|LLM_COST_GUARD" || true
	@echo ""
	@echo "COST GUARD mode ready. Run: ./tools/run_llm_trace_smoke.sh --cost-guard"

llm-off:
	@echo "Restarting API with LLM_ENABLED=0 (default)..."
	$(COMPOSE_BASE) up -d api
	@sleep 3
	@echo "Waiting for API health check..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		curl -sf http://localhost:8000/health > /dev/null 2>&1 && break || sleep 1; \
	done
	@docker exec $(CONTAINER_API) printenv | grep -E "LLM_ENABLED|LLM_COST_GUARD" || true
	@echo ""
	@echo "LLM OFF mode ready."

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

smoke-test:
	./tools/run_llm_trace_smoke.sh

u48-eval:
	./tools/run_u48_eval.sh
