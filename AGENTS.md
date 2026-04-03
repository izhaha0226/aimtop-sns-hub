# AGENTS.md — SNS Hub v2

> 상위 규칙: `/Users/yosiki/projects/AIMTOP-DEV-HARNESS.md` 반드시 준수

> **4계층 규칙 체계:** 이 파일은 **3계층 (프로젝트별 규칙)**입니다.
> - 1계층: `AIMTOP-DEV-HARNESS.md` (전사 규칙, 최우선)
> - 2계층: `~/.openclaw/workspace/AGENTS.md` (에이전트 전역)
> - 3계층: 이 파일 (프로젝트별)
> - 4계층: `.claude-local` (개발자/에이전트 로컬 오버라이드, 커밋 금지)
>
> 하위 계층이 상위와 충돌 시 **상위 우선**.

---

## 기술 스택

| 구분 | 기술 |
|---|---|
| **프론트엔드** | Next.js 15 + React + TypeScript |
| **백엔드** | FastAPI (Python) |
| **DB** | SQLite |
| **ORM** | SQLAlchemy + Alembic (마이그레이션) |
| **프론트 배포** | Vercel |
| **백엔드 배포** | Railway |
| **도메인** | sns.aimtop.ai |

## 포트 정보 (고정)

| 서비스 | 포트 |
|---|---|
| Next.js 프론트엔드 | 1111 |
| FastAPI 백엔드 | 1112 |
| CF 터널 | 1111 |

## 환경변수 (.env — 커밋 금지!)

프론트: `frontend/.env.local`, 백엔드: `backend/.env`

## 디렉터리 구조

```
aimtop-sns-hub/
├── frontend/
│   ├── src/
│   │   ├── app/              ← Next.js App Router 페이지
│   │   ├── components/       ← UI 컴포넌트
│   │   ├── hooks/            ← 커스텀 훅
│   │   ├── services/         ← API 클라이언트
│   │   ├── types/            ← TypeScript 타입 정의
│   │   ├── constants/        ← 상수
│   │   └── utils/            ← 유틸리티
│   ├── public/               ← 정적 파일
│   ├── package.json
│   └── next.config.ts
├── backend/
│   ├── main.py               ← FastAPI 진입점
│   ├── routes/               ← API 라우트 (20+ 라우트)
│   │   ├── auth.py, users.py, clients.py
│   │   ├── contents.py, comments.py, channels.py
│   │   ├── analytics.py, dashboard.py, reports.py
│   │   ├── ai.py, growth.py, schedule.py
│   │   ├── approvals.py, notifications.py
│   │   ├── media.py, publish.py, oauth.py
│   │   ├── auto_reply.py, onboarding.py
│   │   └── health.py
│   ├── models/               ← SQLAlchemy 모델
│   ├── schemas/              ← Pydantic 스키마
│   ├── services/             ← 비즈니스 로직
│   ├── repositories/         ← 데이터 접근 계층
│   ├── middleware/            ← 인증, 로깅 미들웨어
│   ├── core/                 ← 설정, DB 연결, 보안
│   ├── alembic/              ← DB 마이그레이션
│   ├── scripts/              ← 유틸리티 스크립트
│   ├── uploads/              ← 업로드 파일 저장
│   └── requirements.txt
├── docs/                     ← 문서
├── logs/                     ← 로그 파일
├── start.sh                  ← 서버 시작 스크립트
├── deploy-check.sh           ← 배포 전 자동 체크
└── AGENTS.md                 ← 이 파일
```

## 절대 금지 사항 🚫

1. **`.env` / `.env.local` 커밋 금지** — git에 절대 포함되면 안 됨
2. **API 키 하드코딩 금지** — 반드시 환경변수 사용
3. **프로덕션 DB 직접 수정 금지** — ORM/마이그레이션만
4. **`seed_admin.py` 무단 실행 금지** — 대표님 확인 후만
5. **포트 변경 금지** — 프론트 1111, 백엔드 1112 고정
6. **임시 파일 커밋 금지** — `temp_*`, `migrate_*`, `debug_*`, `fix_*` 파일은 작업 후 즉시 삭제
7. **더미/가짜 데이터 DB 삽입 금지** — 대표님 명시 지시 없으면 절대 금지
8. **직접 SQL 실행 금지** — SQLAlchemy ORM만 사용

## 배포

### 프론트엔드 (Vercel)
```bash
# 배포 전 필수
cd frontend && npm run build

# Vercel 자동 배포 (git push)
git push origin main
```

### 백엔드 (Railway)
```bash
# 배포 전 필수
cd backend && python3 -c "import main"

# Railway 자동 배포 (git push)
git push origin main
```

## 배포 전 체크

```bash
# 전체 검증
./deploy-check.sh

# 최소 검증
cd frontend && npm run build
cd backend && python3 -c "import main"
```

## DB 접근 규칙

- SQLAlchemy ORM **만** 사용
- 직접 SQL (`text()`, `execute()`) 금지
- 마이그레이션: `alembic upgrade head`
- 스키마 변경 시 반드시 alembic revision 생성

## Next.js 15 주의사항

- App Router 사용 (`src/app/` 디렉터리)
- Server Components / Client Components 구분 주의
- `'use client'` 디렉티브 빠뜨리지 않기

## 서버 시작

```bash
# 반드시 start.sh 사용 (포트가 고정됨)
./start.sh

# 또는 수동 시작
cd backend && uvicorn main:app --host 0.0.0.0 --port 1112
cd frontend && npm run dev -- -p 1111
```

---

_최종 갱신: 2026-04-03 | Master Chief_
