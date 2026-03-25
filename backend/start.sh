#!/bin/bash
cd "$(dirname "$0")"
[ ! -d ".venv" ] && python3 -m venv .venv
source .venv/bin/activate
pip install -q -e .
alembic upgrade head 2>/dev/null || echo "DB 마이그레이션 스킵 (DB 미연결)"
uvicorn main:app --host 0.0.0.0 --port 5001 --reload
