# AimTop SNS Hub

멀티 클라이언트 SNS 운영 자동화 플랫폼입니다.

콘텐츠 기획부터 승인, 예약 발행, 채널 연동, 리포트, 운영 모니터링까지 한 곳에서 관리할 수 있습니다.

## 주요 기능

- 멀티 클라이언트 워크스페이스 관리
- 콘텐츠 작성 / 승인 / 예약 발행
- SNS 채널 OAuth 연동
- AI 카피 / 이미지 생성 보조
- 캘린더 기반 발행 관리
- 성과 분석 및 운영 리포트
- Agent Monitor 운영 대시보드

## 지원 채널

- 인스타그램
- 페이스북
- X
- Threads
- 카카오채널
- 틱톡
- 링크드인
- 유튜브
- 네이버 블로그

## 기술 스택

### Frontend
- Next.js 15
- TypeScript
- Tailwind CSS
- shadcn/ui

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Celery

### AI / Media
- LLM 기반 카피 생성
- Fal.ai 기반 이미지 / 영상 생성
- Canva Connect API

## 실행 포트

- Frontend: 1111
- Backend: 1112

## 프로젝트 구조

```text
aimtop-sns-hub/
├── frontend/                # Next.js 프론트엔드
├── backend/                 # FastAPI 백엔드
├── docs/                    # 설계 / 운영 문서
├── logs/                    # 런타임 로그
├── start.sh                 # 통합 시작 스크립트
└── README.md
```

## 로컬 실행

```bash
bash start.sh
```

또는 개별 실행:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 1112

cd ../frontend
npm install
npm run dev -- -p 1111
```

## 배포 전 기본 검증

```bash
cd frontend && npm run build
cd ../backend && source .venv/bin/activate && python -c "import main"
```

## 배포 도메인

- https://sns.aimtop.ai
- https://monitor.aimtop.ai

## 라이선스

Copyright © AimTop. All rights reserved.
