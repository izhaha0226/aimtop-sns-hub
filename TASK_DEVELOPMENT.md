# AimTop SNS Hub — 개발 범위 + 실행 계획

> 작성일: 2026-04-03
> 최종 업데이트: 2026-04-09
> 기반: DESIGN_V3.md + 코드베이스 분석 결과
> 기술스택: FastAPI + Next.js 15 + PostgreSQL + Claude CLI
> LLM 호출: `claude --print --max-turns 1` 만 사용. Anthropic API 직접 호출 절대 금지.

---

## 기술스택 확정

| 영역 | 기술 | 버전 |
|---|---|---|
| 프론트엔드 | Next.js + Tailwind CSS + shadcn/ui | 15.x |
| 백엔드 | FastAPI + async SQLAlchemy + Pydantic v2 | Python 3.12 |
| DB | PostgreSQL | 16 |
| 캐시/큐 | Redis + Celery | Redis 7, Celery 5.x |
| AI 텍스트 | Claude CLI (`claude --print --max-turns 1`) | - |
| AI 이미지 | Fal.ai API | - |
| 인증 | JWT (PyJWT) + OAuth2 | - |
| 이메일 | SendGrid 또는 AWS SES | - |
| 알림 | python-telegram-bot | - |
| PDF | WeasyPrint | - |
| 배포 | Vercel + Railway 지향 / 현재 Mac mini + Cloudflare Tunnel 병행 | - |

---

## 2026-04-09 이번 업데이트 완료 항목

- 채널 OAuth 확장: Facebook / Threads / Kakao / TikTok / LinkedIn 추가
- OAuth state 정리 + 백엔드 콜백 후 프론트 리다이렉트 구조 확정
- 토큰 헬스 모니터링 + 30분 주기 알림 자동화 추가
- 대시보드/클라이언트/콘텐츠/캘린더에 채널 헬스 UX 반영
- 승인/반려 API 응답 계약 정렬 (`ApprovalResponse` → `ContentResponse`)
- 외부 승인 이메일 발송 + 공개 검토 페이지 + 콘텐츠 상세 요청 UI 구현
- 프론트 운영 모드 `next dev` → `run-prod.sh` 기반 production build/start 전환

## 전체 Phase 개요

| Phase | 범위 | 예상 기간 | 우선순위 |
|---|---|---|---|
| **Phase 1** | 코어 백엔드 보강 (서비스 레이어 + 누락 모델) | 2~3일 | 🔴 최우선 |
| **Phase 2** | AI 서비스 연동 (Claude CLI + Fal.ai) | 2~3일 | 🔴 최우선 |
| **Phase 3** | SNS OAuth + 실제 발행 | 3~4일 | 🔴 최우선 |
| **Phase 4** | 예약 발행 시스템 (Celery) | 2일 | 🔴 최우선 |
| **Phase 5** | 댓글/인박스 + 자동응답 | 2~3일 | 🟠 높음 |
| **Phase 6** | 성과 분석 + 대시보드 | 3~4일 | 🟠 높음 |
| **Phase 7** | 알림 + 이메일 시스템 | 2일 | 🟠 높음 |
| **Phase 8** | 외부 승인 + 리포트 | 2~3일 | 🟡 중간 |
| **Phase 9** | Growth Hub + 고급 기능 | 3~4일 | 🟡 중간 |
| **Phase 10** | 프론트엔드 보강 + 통합 테스트 | 3~4일 | 🟡 중간 |

**총 예상 기간: 4~5주**

---

## Phase 1: 코어 백엔드 보강

> 목표: 서비스 레이어 분리 + 누락된 DB 모델 + 역할 기반 권한 + Celery 기반 셋업

### 작업 목록

| # | 파일 | 작업 내용 |
|---|---|---|
| 1-1 | `backend/middleware/auth.py` | `require_role(*roles)` 데코레이터 추가. 각 라우트에서 역할 체크 적용 |
| 1-2 | `backend/models/comment.py` | comments 테이블 모델 생성 |
| 1-3 | `backend/models/auto_reply.py` | auto_reply_rules 테이블 모델 생성 |
| 1-4 | `backend/models/analytics.py` | analytics 테이블 모델 생성 |
| 1-5 | `backend/models/notification.py` | notifications 테이블 모델 생성 |
| 1-6 | `backend/models/external_approval.py` | external_approvals 테이블 모델 생성 |
| 1-7 | `backend/models/project.py` | projects 테이블 모델 생성 |
| 1-8 | `backend/models/asset.py` | assets 테이블 모델 생성 |
| 1-9 | `backend/models/__init__.py` | 새 모델 전부 import 등록 |
| 1-10 | `backend/alembic/versions/003_add_comments_autoreplies.py` | comments + auto_reply_rules 마이그레이션 |
| 1-11 | `backend/alembic/versions/004_add_analytics_notifications.py` | analytics + notifications + external_approvals 마이그레이션 |
| 1-12 | `backend/alembic/versions/005_add_projects_assets.py` | projects + assets 마이그레이션 |
| 1-13 | `backend/services/content_service.py` | contents 라우트에서 비즈니스 로직 분리 |
| 1-14 | `backend/repositories/content.py` | contents DB 쿼리 레포지토리 |
| 1-15 | `backend/routes/contents.py` | 서비스 레이어 호출로 리팩토링 |
| 1-16 | `backend/schemas/comment.py` | Comment 스키마 생성 |
| 1-17 | `backend/schemas/analytics.py` | Analytics 스키마 생성 |
| 1-18 | `backend/schemas/notification.py` | Notification 스키마 생성 |
| 1-19 | `backend/requirements.txt` | celery, redis, python-telegram-bot, fal-client, weasyprint 추가 |
| 1-20 | `backend/routes/auth.py` | change-password, invite, accept-invite 엔드포인트 추가 |

### 예상 작업량: 2~3일

---

## Phase 2: AI 서비스 연동

> 목표: Claude CLI 래퍼 + Fal.ai 이미지 생성 + AI 카피/해시태그/컨셉 생성 API

### 작업 목록

| # | 파일 | 작업 내용 |
|---|---|---|
| 2-1 | `backend/services/ai_service.py` | Claude CLI 호출 래퍼 (`subprocess.run(["claude", "--print", "--max-turns", "1", "-p", prompt])`) |
| 2-2 | `backend/services/image_service.py` | Fal.ai API 호출 (nano2 / nano_pro 2-tier) |
| 2-3 | `backend/schemas/ai.py` | AI 관련 request/response 스키마 전체 |
| 2-4 | `backend/routes/ai.py` | `/api/v1/ai/generate-copy` 엔드포인트 |
| 2-5 | `backend/routes/ai.py` | `/api/v1/ai/generate-image` 엔드포인트 |
| 2-6 | `backend/routes/ai.py` | `/api/v1/ai/suggest-hashtags` 엔드포인트 |
| 2-7 | `backend/routes/ai.py` | `/api/v1/ai/concept-sets` 카드뉴스 컨셉 3세트 |
| 2-8 | `backend/routes/ai.py` | `/api/v1/ai/chat` 대화형 콘텐츠 수정 |
| 2-9 | `backend/routes/ai.py` | `/api/v1/ai/generate-strategy` 운영 전략서 생성 |
| 2-10 | `backend/services/prompt_builder.py` | 클라이언트 컨텍스트 기반 프롬프트 자동 구성 (온보딩 설정 + 톤앤매너 + 전략서) |
| 2-11 | `backend/main.py` | ai 라우터 등록 |

### AI 호출 정책 (절대 준수)
```
✅ 허용: subprocess.run(["claude", "--print", "--max-turns", "1", "-p", prompt])
❌ 금지: import anthropic / anthropic.Client() / requests.post("https://api.anthropic.com/...")
❌ 금지: ANTHROPIC_API_KEY 환경변수 사용
```

### 예상 작업량: 2~3일

---

## Phase 3: SNS OAuth + 실제 발행

> 목표: 각 플랫폼 OAuth 연동 + 실제 게시물 발행 API 구현

### 작업 목록

| # | 파일 | 작업 내용 |
|---|---|---|
| 3-1 | `backend/services/sns/base.py` | SNS 플랫폼 기본 인터페이스 (추상 클래스) |
| 3-2 | `backend/services/sns/instagram.py` | Meta Graph API v21 — 피드/릴스 발행, 댓글 수집, 인사이트 조회 |
| 3-3 | `backend/services/sns/facebook.py` | Meta Graph API v21 — 페이지 포스팅, 댓글, 인사이트 |
| 3-4 | `backend/services/sns/x_twitter.py` | X API v2 — 트윗/스레드 발행, 댓글, DM |
| 3-5 | `backend/services/sns/threads.py` | Threads API (Meta) — 게시물 발행, 인사이트 |
| 3-6 | `backend/services/sns/kakao.py` | 카카오 비즈메시지 API — 포스팅, 알림톡 |
| 3-7 | `backend/routes/oauth.py` | 플랫폼별 OAuth init/callback 엔드포인트 (6개 플랫폼) |
| 3-8 | `backend/services/publish_service.py` | 통합 발행 서비스 (플랫폼 라우팅 + 재시도 로직) |
| 3-9 | `backend/routes/publish.py` | `/api/v1/publish/{platform}` 발행 엔드포인트 |
| 3-10 | `backend/services/token_service.py` | 토큰 AES-256 암호화/복호화 + 자동 갱신 로직 |
| 3-11 | `backend/core/encryption.py` | AES-256 암호화 유틸리티 |

### 선결 조건 (외부)
- Meta 개발자 앱 등록 + 권한 심사 신청
- X API Basic 플랜 결제 ($100/월)
- 카카오 비즈 API 키 확인
- (개발 중에는 테스트 계정/Sandbox 모드 사용)

### 예상 작업량: 3~4일

---

## Phase 4: 예약 발행 시스템 (Celery)

> 목표: Celery + Redis 기반 예약 발행 + 토큰 갱신 + 휴지통 정리 워커

### 작업 목록

| # | 파일 | 작업 내용 |
|---|---|---|
| 4-1 | `backend/workers/__init__.py` | workers 패키지 초기화 |
| 4-2 | `backend/workers/celery_app.py` | Celery 앱 설정 + Beat 스케줄 정의 |
| 4-3 | `backend/workers/publish.py` | `check_and_publish` 태스크: 매 1분, 예약 시간 도래한 콘텐츠 발행 |
| 4-4 | `backend/workers/tokens.py` | `check_and_refresh` 태스크: 매일 03:00, 만료 임박 토큰 갱신 |
| 4-5 | `backend/workers/cleanup.py` | `delete_expired_trash` 태스크: 매일 04:00, 30일 경과 휴지통 영구 삭제 |
| 4-6 | `backend/workers/analytics_collector.py` | `collect_metrics` 태스크: 발행 후 1h/6h/24h/3d/7d/30d 성과 수집 |
| 4-7 | `backend/start_worker.sh` | Celery 워커 + Beat 실행 스크립트 |
| 4-8 | `backend/start.sh` | 기존 start.sh에 Celery 워커 자동 실행 추가 |

### 예상 작업량: 2일

---

## Phase 5: 댓글/인박스 + 자동응답

> 목표: 전체 채널 댓글 통합 수집 + 인박스 UI 백엔드 + 자동응답 룰

### 작업 목록

| # | 파일 | 작업 내용 |
|---|---|---|
| 5-1 | `backend/routes/inbox.py` | GET /inbox (통합 댓글 목록), POST /inbox/{id}/reply, PATCH /inbox/{id}/read, PATCH /inbox/{id}/hide |
| 5-2 | `backend/services/comment_service.py` | 댓글 수집 서비스 (각 플랫폼 API 폴링 → comments 테이블 저장) |
| 5-3 | `backend/services/auto_reply_service.py` | 키워드 매칭 → 자동 응답 or AI 응답 초안 생성 |
| 5-4 | `backend/routes/auto_reply_rules.py` | CRUD: GET/POST/PUT/DELETE /api/v1/auto-reply-rules |
| 5-5 | `backend/workers/comment_collector.py` | Celery 태스크: 5분마다 각 채널 댓글/DM 폴링 수집 |
| 5-6 | `backend/services/sentiment_service.py` | Claude CLI로 댓글 감성 분석 (positive/neutral/negative) |
| 5-7 | `backend/main.py` | inbox, auto_reply_rules 라우터 등록 |

### 예상 작업량: 2~3일

---

## Phase 6: 성과 분석 + 대시보드

> 목표: 플랫폼별 성과 수집 + KPI 대시보드 + 콘텐츠별 성과 + 히트맵

### 작업 목록

| # | 파일 | 작업 내용 |
|---|---|---|
| 6-1 | `backend/services/analytics_service.py` | 각 플랫폼 인사이트 API 호출 → analytics 테이블 저장 |
| 6-2 | `backend/routes/analytics.py` | GET /analytics/dashboard — 채널별 KPI 집계 |
| 6-3 | `backend/routes/analytics.py` | GET /analytics/contents — 콘텐츠별 성과 순위 |
| 6-4 | `backend/routes/analytics.py` | GET /analytics/content/{id}/timeline — 시간별 추이 |
| 6-5 | `backend/routes/analytics.py` | GET /analytics/heatmap — 요일×시간대 참여율 |
| 6-6 | `backend/services/insight_service.py` | Claude CLI로 7일 성과 AI 인사이트 자동 생성 |
| 6-7 | `backend/routes/dashboard.py` | 기존 stats/recent-activity 보강 + 채널 상태 + 알림 요약 |
| 6-8 | `backend/main.py` | analytics 라우터 등록 |

### 예상 작업량: 3~4일

---

## Phase 7: 알림 + 이메일 시스템

> 목표: 텔레그램 알림 + 인앱 알림 + 이메일 발송 (승인 요청/리포트)

### 작업 목록

| # | 파일 | 작업 내용 |
|---|---|---|
| 7-1 | `backend/services/notification_service.py` | 알림 생성 + 채널별 발송 라우팅 (in_app / telegram / email) |
| 7-2 | `backend/services/telegram_service.py` | python-telegram-bot으로 텔레그램 알림 발송 |
| 7-3 | `backend/services/email_service.py` | SendGrid/SES 이메일 발송 (승인 요청, 토큰 만료, 리포트) |
| 7-4 | `backend/routes/notifications.py` | GET /notifications, PATCH /notifications/{id}/read, PATCH /notifications/read-all |
| 7-5 | `backend/main.py` | notifications 라우터 등록 |
| 7-6 | 각 서비스 전반 | 발행 완료/실패, 승인 요청/완료, 토큰 만료 등 이벤트에 알림 호출 삽입 |

### 예상 작업량: 2일

---

## Phase 8: 외부 승인 + PDF 리포트

> 목표: 클라이언트 이메일 승인 + PDF 리포트 자동 생성

### 작업 목록

| # | 파일 | 작업 내용 |
|---|---|---|
| 8-1 | `backend/routes/external_approval.py` | POST /contents/{id}/request-external-approval (이메일 발송) |
| 8-2 | `backend/routes/external_approval.py` | GET /approve/{token} (클라이언트 승인 페이지 데이터) |
| 8-3 | `backend/routes/external_approval.py` | POST /approve/{token}/approve, POST /approve/{token}/revise |
| 8-4 | `backend/services/report_service.py` | Claude CLI로 리포트 텍스트 생성 + WeasyPrint로 PDF 렌더링 |
| 8-5 | `backend/routes/reports.py` | POST /reports/generate |
| 8-6 | `backend/workers/report_generator.py` | Celery Beat: 주간(매주 월 09:00) / 월간(매월 1일 09:00) 자동 생성 |
| 8-7 | `backend/templates/report_weekly.html` | WeasyPrint용 주간 리포트 HTML 템플릿 |
| 8-8 | `backend/templates/report_monthly.html` | WeasyPrint용 월간 리포트 HTML 템플릿 |
| 8-9 | `frontend/src/app/external-approval/[token]/page.tsx` | 클라이언트 전용 승인 페이지 (로그인 불필요) |
| 8-10 | `backend/main.py` | external_approval, reports 라우터 등록 |

### 예상 작업량: 2~3일

---

## Phase 9: Growth Hub + 고급 기능

> 목표: 캠페인 관리, 경쟁사 모니터링, 월간 플랜, 소재 관리, 검색

### 작업 목록

| # | 파일 | 작업 내용 |
|---|---|---|
| 9-1 | `backend/models/campaign.py` | campaigns 테이블 모델 |
| 9-2 | `backend/models/competitor.py` | competitor_accounts 테이블 모델 |
| 9-3 | `backend/models/monthly_plan.py` | monthly_plans 테이블 모델 |
| 9-4 | `backend/routes/campaigns.py` | 캠페인 CRUD + 해시태그 트래킹 |
| 9-5 | `backend/routes/competitors.py` | 경쟁사 등록/분석 결과 조회 |
| 9-6 | `backend/routes/monthly_plans.py` | 월간 플랜 생성 (AI 자동 제안 포함) |
| 9-7 | `backend/routes/assets.py` | 소재 업로드/목록/삭제 |
| 9-8 | `backend/routes/search.py` | GET /search (콘텐츠+소재+담당자 통합 검색) |
| 9-9 | `backend/services/competitor_service.py` | 경쟁사 계정 공개 데이터 수집 + Claude CLI 분석 |
| 9-10 | `backend/services/plan_service.py` | Claude CLI로 월간 플랜 AI 초안 생성 |
| 9-11 | `backend/alembic/versions/006_growth_hub.py` | campaigns + competitor_accounts + monthly_plans + assets 마이그레이션 |

### 예상 작업량: 3~4일

---

## Phase 10: 프론트엔드 보강 + 통합 테스트

> 목표: 백엔드 실데이터 연동 + 미구현 프론트 페이지 + E2E 테스트

### 작업 목록

| # | 파일 | 작업 내용 |
|---|---|---|
| 10-1 | `frontend/src/services/ai.ts` | AI API 클라이언트 (generate-copy, generate-image, suggest-hashtags, concept-sets, chat) |
| 10-2 | `frontend/src/services/analytics.ts` | 분석 API 클라이언트 |
| 10-3 | `frontend/src/services/inbox.ts` | 인박스 API 클라이언트 |
| 10-4 | `frontend/src/services/notifications.ts` | 알림 API 클라이언트 |
| 10-5 | `frontend/src/app/(main)/analytics/page.tsx` | 분석 페이지 실데이터 연동 (KPI 카드 + 차트) |
| 10-6 | `frontend/src/app/(main)/inbox/page.tsx` | 인박스 페이지 실데이터 연동 |
| 10-7 | `frontend/src/app/(main)/calendar/page.tsx` | 캘린더 페이지 예약 데이터 연동 |
| 10-8 | `frontend/src/app/(main)/contents/new/text/page.tsx` | 텍스트 에디터 AI 연동 (카피 생성 버튼) |
| 10-9 | `frontend/src/app/(main)/contents/new/card-news/page.tsx` | 카드뉴스 에디터 AI 연동 (컨셉 3세트 + 이미지 생성) |
| 10-10 | `frontend/src/components/features/AIChat.tsx` | AI 대화형 수정 패널 컴포넌트 |
| 10-11 | `frontend/src/components/features/NotificationBell.tsx` | 알림 벨 + 드롭다운 |
| 10-12 | `frontend/src/app/(main)/growth-hub/page.tsx` | Growth Hub 메인 (성장 목표 + 인사이트) |
| 10-13 | `backend/tests/test_auth.py` | 인증 API 테스트 |
| 10-14 | `backend/tests/test_contents.py` | 콘텐츠 CRUD 테스트 |
| 10-15 | `backend/tests/test_ai_service.py` | AI 서비스 테스트 (Claude CLI mock) |
| 10-16 | `backend/tests/test_publish.py` | 발행 서비스 테스트 (SNS API mock) |

### 예상 작업량: 3~4일

---

## 개발 정책 (절대 준수)

### LLM 호출 정책
```
✅ 허용 (유일한 방법):
   subprocess.run(["claude", "--print", "--max-turns", "1", "-p", prompt])

❌ 절대 금지:
   - import anthropic
   - anthropic.Anthropic() 또는 anthropic.Client()
   - requests.post("https://api.anthropic.com/...")
   - ANTHROPIC_API_KEY 환경변수 사용
   - 기타 Anthropic SDK/API 직접 호출
```

### 코드 구조 정책
- routes/ → schemas 검증만 → services/ 비즈니스 로직 → repositories/ DB 접근
- 함수 30줄 이하 원칙
- 모든 외부 API 호출에 try/except 필수
- 환경변수 하드코딩 금지
- 로그에 토큰/비밀번호 출력 금지

### Git 정책
- feature 브랜치 → PR → 리뷰 → main 머지
- 커밋 메시지: feat/fix/refactor/docs/test/chore 접두사
- .env 파일 절대 커밋 금지

---

## 환경변수 목록 (.env.example)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/sns_hub
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# SNS OAuth (Meta)
META_APP_ID=
META_APP_SECRET=
META_REDIRECT_URI=https://sns.aimtop.ai/api/v1/oauth/instagram/callback

# SNS OAuth (X/Twitter)
X_API_KEY=
X_API_SECRET=
X_BEARER_TOKEN=

# SNS OAuth (카카오)
KAKAO_REST_API_KEY=
KAKAO_CLIENT_SECRET=

# SNS OAuth (YouTube/Google)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Fal.ai
FAL_API_KEY=

# 이메일 (SendGrid)
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=noreply@aimtop.ai

# 텔레그램
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_CHAT_ID=

# 암호화 (토큰 저장용)
TOKEN_ENCRYPTION_KEY=  # AES-256 key (32 bytes base64)

# 서버
CORS_ORIGINS=["https://sns.aimtop.ai","http://localhost:1111"]
```

---

## 실행 순서 요약

```
Phase 1 (2~3일) : DB 모델 + 서비스 레이어 + Celery 기반 설치
    ↓
Phase 2 (2~3일) : AI 연동 (Claude CLI + Fal.ai)
    ↓
Phase 3 (3~4일) : SNS OAuth + 실제 발행 (테스트 계정)
    ↓
Phase 4 (2일)   : 예약 발행 Celery 워커
    ↓
Phase 5 (2~3일) : 댓글 인박스 + 자동응답
    ↓
Phase 6 (3~4일) : 성과 분석 + 대시보드
    ↓
Phase 7 (2일)   : 알림 + 이메일
    ↓
Phase 8 (2~3일) : 외부 승인 + PDF 리포트
    ↓
Phase 9 (3~4일) : Growth Hub + 고급 기능
    ↓
Phase 10 (3~4일): 프론트엔드 보강 + 테스트
```

---

*Master Chief 작성 · 에임탑 내부 문서 · 2026-04-03*
