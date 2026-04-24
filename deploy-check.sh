#!/bin/bash
# ============================================================
# SNS Hub v2 — 배포 전 자동 체크 스크립트
# 모든 체크 통과 시에만 "✅ 배포 가능" 출력
# ============================================================

set -e
cd "$(dirname "$0")"

FAIL=0
WARN=0

echo "🔍 SNS Hub v2 배포 전 체크 시작..."
echo "================================================"

# ── 1. Frontend 빌드 체크 ──
echo ""
echo "📦 [1/6] Frontend 빌드 체크..."
cd frontend
python3 - <<'PY' >/dev/null 2>&1
import shutil
shutil.rmtree('.next', ignore_errors=True)
PY
if npm run build > /dev/null 2>&1; then
    echo "  ✅ Next.js 빌드 성공"
else
    echo "  ❌ Next.js 빌드 실패!"
    FAIL=$((FAIL + 1))
fi
cd ..

# ── 2. Backend import 체크 ──
echo ""
echo "📦 [2/6] Backend main import 체크..."
cd backend
PYTHON_BIN="./.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi
if "$PYTHON_BIN" -c "from main import app; print('ok')" >/dev/null 2>&1; then
    echo "  ✅ main.py import 성공"
else
    echo "  ❌ main.py import 실패!"
    FAIL=$((FAIL + 1))
fi
cd ..

# ── 3. 임시 파일 체크 ──
echo ""
echo "🗑️  [3/6] 임시 파일 체크..."
TEMP_FILES=$(find . -maxdepth 3 -name "temp_*" -o -name "migrate_*" -o -name "debug_*" -o -name "fix_*" 2>/dev/null | grep -v node_modules | grep -v __pycache__ | grep -v .git | grep -v .venv || true)
if [ -n "$TEMP_FILES" ]; then
    echo "  ❌ 임시 파일 발견!"
    echo "$TEMP_FILES" | while read f; do echo "    - $f"; done
    FAIL=$((FAIL + 1))
else
    echo "  ✅ 임시 파일 없음"
fi

# ── 4. .env 파일 git 체크 ──
echo ""
echo "🔒 [4/6] .env 파일 git 체크..."
ENV_IN_GIT=$(git ls-files 2>/dev/null | grep -E "\.env" | grep -v "\.env\.example" || true)
if [ -n "$ENV_IN_GIT" ]; then
    echo "  ❌ .env 파일이 git에 포함됨!"
    echo "    $ENV_IN_GIT"
    FAIL=$((FAIL + 1))
else
    echo "  ✅ .env 파일 안전"
fi

# ── 5. 하드코딩 credentials 체크 ──
echo ""
echo "🔐 [5/6] 하드코딩 credentials 체크..."
CRED_HITS=$(grep -rn 'sk-\|api_key\s*=\s*["\\x27][A-Za-z0-9]' --include="*.py" --include="*.ts" --include="*.tsx" backend/ frontend/src/ 2>/dev/null | grep -v "os.getenv\|os.environ\|process.env\|settings\.\|config\.\|startswith\|\.venv/\|venv/" || true)
if [ -n "$CRED_HITS" ]; then
    echo "  ❌ 하드코딩된 credentials 발견!"
    echo "$CRED_HITS" | head -5 | while read line; do echo "    $line"; done
    FAIL=$((FAIL + 1))
else
    echo "  ✅ 하드코딩 credentials 없음"
fi

# ── 6. TODO/console.log 체크 ──
echo ""
echo "📝 [6/6] TODO/console.log 체크..."
TODO_COUNT=$(grep -rn "TODO\|FIXME\|HACK" --include="*.py" --include="*.ts" --include="*.tsx" backend/ frontend/src/ 2>/dev/null | wc -l | tr -d ' ')
CONSOLE_COUNT=$(grep -rn "console\.log" --include="*.ts" --include="*.tsx" frontend/src/ 2>/dev/null | wc -l | tr -d ' ')
if [ "$TODO_COUNT" -gt 0 ] || [ "$CONSOLE_COUNT" -gt 0 ]; then
    echo "  ⚠️  TODO/FIXME ${TODO_COUNT}개, console.log ${CONSOLE_COUNT}개 (경고)"
    WARN=$((WARN + 1))
else
    echo "  ✅ 깔끔함"
fi

# ── 결과 ──
echo ""
echo "================================================"
if [ $FAIL -gt 0 ]; then
    echo "❌ 배포 불가! 실패 ${FAIL}건, 경고 ${WARN}건"
    exit 1
else
    if [ $WARN -gt 0 ]; then
        echo "✅ 배포 가능 (경고 ${WARN}건 — 확인 권장)"
    else
        echo "✅ 배포 가능! 모든 체크 통과."
    fi
    exit 0
fi
