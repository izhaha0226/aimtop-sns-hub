#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
echo "=== AimTop SNS Hub Backend 시작 ==="
[ ! -d ".venv" ] && python3 -m venv .venv
source .venv/bin/activate
pip install -q -e .
echo "백엔드 시작 (포트 5001)..."
uvicorn main:app --host 0.0.0.0 --port 5001 --reload
