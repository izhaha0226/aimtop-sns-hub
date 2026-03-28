#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "=== AimTop SNS Hub Frontend 시작 ==="
npm install --silent
echo "프론트엔드 시작 (포트 1111)..."
PORT=1111 npm run dev
