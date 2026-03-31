#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== AimTop SNS Hub 시작 ==="

# Kill existing processes
echo "기존 프로세스 정리..."
lsof -ti :1111 2>/dev/null | xargs kill 2>/dev/null || true
lsof -ti :1112 2>/dev/null | xargs kill 2>/dev/null || true
sleep 2

# Start Backend
echo "백엔드 시작 (포트 1112)..."
cd "$ROOT/backend"
source .venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 1112 > /tmp/sns-backend.log 2>&1 &
BACKEND_PID=$!
echo "  PID: $BACKEND_PID"

# Start Frontend
echo "프론트엔드 시작 (포트 1111)..."
cd "$ROOT/frontend"
nohup npx next dev -p 1111 > /tmp/sns-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  PID: $FRONTEND_PID"

# Wait for health
sleep 3
echo ""
echo "=== 상태 확인 ==="
curl -s http://localhost:1112/health && echo " ← 백엔드 OK" || echo " ← 백엔드 FAIL"
curl -s -o /dev/null -w "%{http_code}" http://localhost:1111 && echo " ← 프론트엔드 OK" || echo " ← 프론트엔드 FAIL"

echo ""
echo "✅ SNS Hub 시작 완료"
echo "   프론트엔드: http://localhost:1111"
echo "   백엔드 API: http://localhost:1112"
echo "   도메인: https://sns.aimtop.ai"
echo "   로그: /tmp/sns-backend.log, /tmp/sns-frontend.log"
