#!/usr/bin/env bash
# INCA-RAG Demo Evaluation Script
# This script serves as the "demo reliability baseline"
#
# Usage:
#   ./tools/run_demo_eval.sh

set -e

echo "========================================"
echo "INCA-RAG Demo Evaluation"
echo "========================================"

# Start containers if not running
echo ""
echo "[1/3] Checking Docker containers..."
docker compose -f docker-compose.demo.yml up -d

# Wait for API to be healthy
echo ""
echo "[2/3] Waiting for API to be ready..."
sleep 5

# Check API health
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "Warning: API health check failed, waiting 5 more seconds..."
    sleep 5
fi

# Run audit
echo ""
echo "[3/3] Running evaluations..."
echo ""

echo "--- Slot Audit ---"
python tools/audit_slots.py

echo ""
echo "--- Goldset Eval ---"
python eval/eval_runner.py

echo ""
echo "========================================"
echo "Demo Evaluation Complete"
echo "========================================"
