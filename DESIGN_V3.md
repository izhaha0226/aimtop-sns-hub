# AimTop SNS Hub — 보완 설계서 V3

> 작성일: 2026-04-03
> 기반: SNS 자동화 플랫폼 SPEC v1.3 + 코드베이스 분석 결과
> 도메인: sns.aimtop.ai
> 회사: 에임탑(AimTop) / admin@aimtop.ai

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 서비스명 | AimTop SNS Hub |
| 목적 | 다수 클라이언트 SNS 계정을 내부 운영팀이 통합 관리하는 자동화 플랫폼 |
| 사용자 | 에임탑 내부 운영팀 (3명+) |
| 운영 방식 | 다중 클라이언트 대행 관리 (멀티 워크스페이스) |
| 도메인 | sns.aimtop.ai |
| 프론트 포트 | 1111 (Next.js) |
| 백엔드 포트 | 5002 (FastAPI) |
| GitHub | izhaha0226/aimtop-sns-hub |

---

## 2. 기술 스택 (확정)

| 영역 | 기술 | 비고 |
|---|---|---|
| 프론트엔드 | Next.js 15 + Tailwind CSS + shadcn/ui | TypeScript |
| 백엔드 | FastAPI (Python 3.12) | async SQLAlchemy |
| DB | PostgreSQL 16 | 메인 데이터 |
| 캐시/큐 | Redis 7 | Celery broker + 세션 캐시 |
| 작업 큐 | Celery + Redis | 예약 발행 / 분석 수집 |
| AI 텍스트 | Claude CLI (`claude --print --max-turns 1`) | Anthropic API 직접 호출 절대 금지 |
| AI 이미지 | Fal.ai (Nano Banana 2 / Pro) | $0.039~$0.15/장 |
| AI 영상 | Fal.ai (Veo 3.1 / Kling v3) | 릴스/숏폼 |
| 인증 | JWT + OAuth2 (Meta / X / 카카오 등) | |
| 알림 | 텔레그램 Bot API | |
| PDF 생성 | WeasyPrint | 리포트 |
| 배포 | Mac mini + Cloudflare Tunnel | |

> **LLM 호출 정책**: 모든 AI 텍스트 생성(카피, 전략서, 인사이트 등)은 반드시 `claude --print --max-turns 1` CLI 호출만 사용. Anthropic API(anthropic Python SDK, REST API) 직접 호출 절대 금지.

---

## 3. 현재 구현 현황 분석

### 3-1. 구현된 DB 모델 (10개)

| 모델 | 테이블명 | 상태 |
|---|---|---|
| User | users | 완료 |
| Client | clients | 완료 |
| ClientUser | client_users | 완료 |
| Content | contents | 완료 |
| ContentVersion | content_versions | 완료 |
| ChannelConnection | channel_connections | 완료 |
| Approval | approvals | 완료 |
| Schedule | schedules | 완료 |
| ClientOnboarding | client_onboardings | 완료 |
| UserActivityLog / UserPermissionLog | user_activity_logs / user_permission_logs | 완료 |

### 3-2. 구현된 API 라우트

| 모듈 | prefix | 엔드포인트 수 | 상태 |
|---|---|---|---|
| auth | /api/v1/auth | 5 (login, refresh, logout, forgot-password, reset-password) | 완료 |
| users | /api/v1/users | 기본 CRUD | 완료 |
| clients | /api/v1/clients | 기본 CRUD | 완료 |
| contents | /api/v1/contents | 10 (CRUD + approve/reject + schedule + publish-now + restore) | 완료 |
| channels | /api/v1/clients/{id}/channels | 4 (list, connect, disconnect, status) | 완료 |
| dashboard | /api/v1/dashboard | 2 (stats, recent-activity) | 기본만 |
| onboarding | /api/v1/onboarding | step1~complete | 완료 |
| health | /api/v1/health | 1 | 완료 |
| media | /api/v1/media | 파일 업로드 | 완료 |

### 3-3. 구현된 프론트엔드 페이지 (18개)

로그인, 회원가입, 비밀번호 찾기/재설정, 초대 수락, 대시보드, 클라이언트 목록/상세, 온보딩, 콘텐츠 목록/유형선택/텍스트에디터/카드뉴스에디터, 휴지통, 캘린더, 인박스, 승인 큐, 분석, 담당자 설정, 외부 승인 페이지, 개인정보/이용약관

### 3-4. 미구현 기능 (GAP 분석)

| # | 미구현 항목 | SPEC 참조 | 심각도 |
|---|---|---|---|
| 1 | AI 카피 생성 API (/ai/generate-copy) | FR-12 | CRITICAL |
| 2 | AI 이미지 생성 API (/ai/generate-image) | FR-13 | CRITICAL |
| 3 | AI 채팅 수정 API (/ai/chat) | FR-13-B | HIGH |
| 4 | AI 컨셉 세트 생성 (/ai/concept-sets) | FR-09 | HIGH |
| 5 | SNS OAuth 실제 연동 (Meta/X/카카오 등) | 3-3-B | CRITICAL |
| 6 | 실제 SNS 발행 기능 (API 호출) | FR-24 | CRITICAL |
| 7 | Celery 예약 발행 스케줄러 | FR-30~32 | CRITICAL |
| 8 | 댓글/DM 수집 및 통합 인박스 백엔드 | FR-40~44 | HIGH |
| 9 | 자동응답 룰셋 관리 | FR-42 | HIGH |
| 10 | 성과 분석 데이터 수집 (트래킹 워커) | FR-50~57 | HIGH |
| 11 | Analytics 실제 백엔드 (현재 기본 stats만) | FR-52 | HIGH |
| 12 | 외부(클라이언트) 승인 이메일 발송 | FR-22 | HIGH |
| 13 | 이메일 발송 시스템 (SendGrid/SES) | 전반 | HIGH |
| 14 | 텔레그램 알림 시스템 | FR-60~61 | MEDIUM |
| 15 | PDF 리포트 자동 생성 | FR-58~59 | MEDIUM |
| 16 | Growth Hub 백엔드 전체 | FR-60-A~D | MEDIUM |
| 17 | 콘텐츠 라이브러리/소재 관리 | FR-60~72 | MEDIUM |
| 18 | 월간 콘텐츠 플랜 | FR-80~82 | MEDIUM |
| 19 | 통합 검색 | FR-110~112 | LOW |
| 20 | 2FA 인증 | FR-102 | LOW |
| 21 | 토큰 자동 갱신 시스템 (Celery Beat) | 3-3-B | HIGH |
| 22 | 카카오 챗봇 시나리오 빌더 백엔드 | FR-45 | MEDIUM |
| 23 | 해시태그 자동 추천 (/ai/suggest-hashtags) | FR-12 | MEDIUM |
| 24 | 콘텐츠 버전 관리 API (versions/rollback) | FR-08-B | MEDIUM |
| 25 | 프로젝트 관리 (projects CRUD) | FR-08-C | MEDIUM |

---

## 4. 아키텍처 개선사항

### 4-1. 현재 아키텍처 문제점

1. **서비스 레이어 부재**: routes에 비즈니스 로직 직접 작성. services/ 디렉토리에 auth, client, user만 존재하고 content, channel, dashboard 등은 route에서 직접 처리
2. **Repository 패턴 미활용**: repositories/ 에 base, client, user만 있고 실제로 route에서 직접 DB 쿼리
3. **Celery/Redis 미설정**: requirements.txt에 celery 없음. 예약 발행 불가
4. **AI 연동 모듈 없음**: services/ai.py, routes/ai.py 없음
5. **SNS API 연동 모듈 없음**: 채널 연동은 DB 저장만, 실제 API 호출 없음
6. **알림 시스템 없음**: 텔레그램/이메일 발송 코드 없음
7. **Alembic 마이그레이션**: 2개만 존재 (initial + content_channel)
8. **테스트 없음**: tests/ 디렉토리 없음

### 4-2. 개선된 아키텍처

```
┌──────────────────────────────────────────────────┐
│         SNS Hub 프론트엔드 (Web UI)               │
│         Next.js 15 + Tailwind + shadcn/ui         │
│         포트: 1111  /  도메인: sns.aimtop.ai       │
└────────────────────┬─────────────────────────────┘
                     │ REST API
┌────────────────────▼─────────────────────────────┐
│              백엔드 API (FastAPI)                  │
│              포트: 5002                            │
│                                                    │
│  routes/ → schemas/ → services/ → repositories/   │
│                                                    │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐ │
│  │ AI 서비스│  │ SNS API  │  │   알림 서비스    │ │
│  │(Claude   │  │ 연동     │  │(텔레그램/이메일) │ │
│  │ CLI)     │  │ 서비스   │  │                 │ │
│  └──────────┘  └──────────┘  └─────────────────┘ │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │  Celery Workers (Redis Broker)                │ │
│  │  - 예약 발행 Worker                           │ │
│  │  - 성과 수집 Worker                           │ │
│  │  - 토큰 갱신 Worker (Beat: 매일 03:00)       │ │
│  │  - 알림 발송 Worker                           │ │
│  └──────────────────────────────────────────────┘ │
└────┬──────┬──────┬──────┬──────┬─────────────────┘
     │      │      │      │      │
  인스타  페북    X    Threads 카카오 ...
  Graph  Graph  v2    Meta   비즈API
  API    API    API   API
```

---

## 5. DB 스키마 상세 (보완)

### 5-1. 기존 테이블 (구현 완료)

```sql
-- 이미 구현된 테이블은 그대로 유지
users, clients, client_users, contents, content_versions,
channel_connections, approvals, schedules, client_onboardings,
user_activity_logs, user_permission_logs
```

### 5-2. 추가 필요 테이블

```sql
-- ========== 댓글/DM 관리 ==========
comments
  id UUID PK
  channel_connection_id UUID FK → channel_connections.id
  content_id UUID FK → contents.id (nullable, 연결된 게시물)
  platform_comment_id VARCHAR(200) -- 플랫폼 원본 ID
  parent_id UUID FK → comments.id (nullable, 대댓글)
  text TEXT NOT NULL
  author_name VARCHAR(200)
  author_platform_id VARCHAR(200)
  comment_type VARCHAR(20) DEFAULT 'comment' -- comment / dm
  sentiment VARCHAR(20) -- positive / neutral / negative
  is_replied BOOLEAN DEFAULT FALSE
  replied_at TIMESTAMPTZ
  reply_text TEXT
  is_read BOOLEAN DEFAULT FALSE
  is_hidden BOOLEAN DEFAULT FALSE
  platform_created_at TIMESTAMPTZ
  created_at TIMESTAMPTZ DEFAULT NOW()

-- ========== 자동응답 룰 ==========
auto_reply_rules
  id UUID PK
  client_id UUID FK → clients.id
  channel_connection_id UUID FK → channel_connections.id (nullable, 전체 채널이면 null)
  keyword VARCHAR(500) NOT NULL
  match_type VARCHAR(20) DEFAULT 'contains' -- exact / contains / regex
  response_text TEXT NOT NULL
  priority INTEGER DEFAULT 0
  is_active BOOLEAN DEFAULT TRUE
  created_at TIMESTAMPTZ DEFAULT NOW()
  updated_at TIMESTAMPTZ DEFAULT NOW()

-- ========== 성과 분석 ==========
analytics
  id UUID PK
  channel_connection_id UUID FK → channel_connections.id
  content_id UUID FK → contents.id (nullable)
  platform_post_id VARCHAR(200)
  metric_type VARCHAR(50) NOT NULL -- reach / impressions / likes / comments / shares / saves / clicks / video_views / followers
  value BIGINT DEFAULT 0
  recorded_at TIMESTAMPTZ NOT NULL
  period VARCHAR(20) DEFAULT 'snapshot' -- 1h / 6h / 24h / 3d / 7d / 30d / snapshot
  created_at TIMESTAMPTZ DEFAULT NOW()

  INDEX idx_analytics_content_period ON (content_id, period)
  INDEX idx_analytics_channel_date ON (channel_connection_id, recorded_at)

-- ========== 외부 승인 ==========
external_approvals
  id UUID PK
  content_id UUID FK → contents.id
  approver_name VARCHAR(200)
  approver_email VARCHAR(255) NOT NULL
  token VARCHAR(500) UNIQUE NOT NULL -- 1회용 보안 토큰
  token_expires_at TIMESTAMPTZ NOT NULL
  action VARCHAR(30) DEFAULT 'pending' -- pending / approved / revision_requested
  comment TEXT
  sent_at TIMESTAMPTZ DEFAULT NOW()
  responded_at TIMESTAMPTZ

-- ========== 알림 ==========
notifications
  id UUID PK
  user_id UUID FK → users.id
  type VARCHAR(50) NOT NULL -- approval_request / approval_done / publish_success / publish_fail / token_expiry / negative_comment
  title VARCHAR(500) NOT NULL
  message TEXT
  link VARCHAR(500)
  is_read BOOLEAN DEFAULT FALSE
  channel VARCHAR(20) DEFAULT 'in_app' -- in_app / telegram / email
  sent_at TIMESTAMPTZ DEFAULT NOW()

-- ========== 프로젝트 ==========
projects
  id UUID PK
  client_id UUID FK → clients.id
  name VARCHAR(300) NOT NULL
  description TEXT
  approval_type VARCHAR(20) DEFAULT 'internal' -- internal / external / both
  external_approver_name VARCHAR(200)
  external_approver_email VARCHAR(255)
  status VARCHAR(20) DEFAULT 'active' -- active / trashed
  deleted_at TIMESTAMPTZ
  created_at TIMESTAMPTZ DEFAULT NOW()
  updated_at TIMESTAMPTZ DEFAULT NOW()

-- ========== 카카오 챗봇 ==========
kakao_chatbot_scenarios
  id UUID PK
  client_id UUID FK → clients.id
  name VARCHAR(200) NOT NULL
  trigger_type VARCHAR(20) NOT NULL -- keyword / button / fallback
  trigger_value VARCHAR(500)
  response_type VARCHAR(20) DEFAULT 'text' -- text / button
  response_content JSON
  priority INTEGER DEFAULT 0
  is_active BOOLEAN DEFAULT TRUE
  is_fallback BOOLEAN DEFAULT FALSE
  created_at TIMESTAMPTZ DEFAULT NOW()
  updated_at TIMESTAMPTZ DEFAULT NOW()

-- ========== 콘텐츠 소재 ==========
assets
  id UUID PK
  client_id UUID FK → clients.id
  file_name VARCHAR(500) NOT NULL
  file_url VARCHAR(1000) NOT NULL
  file_type VARCHAR(50) -- image / video / font / document
  file_size BIGINT
  folder VARCHAR(200) DEFAULT '/'
  tags JSON -- ["logo", "product"]
  uploaded_by UUID FK → users.id
  created_at TIMESTAMPTZ DEFAULT NOW()

-- ========== 콘텐츠 태그 ==========
content_tags
  id UUID PK
  content_id UUID FK → contents.id
  tag VARCHAR(100) NOT NULL
  INDEX idx_content_tags_tag ON (tag)

-- ========== 월간 플랜 ==========
monthly_plans
  id UUID PK
  client_id UUID FK → clients.id
  year_month VARCHAR(7) NOT NULL -- '2026-04'
  plan_data JSON -- [{date, post_type, topic, channel, status}]
  status VARCHAR(20) DEFAULT 'draft' -- draft / approved / active
  created_by UUID FK → users.id
  created_at TIMESTAMPTZ DEFAULT NOW()
  updated_at TIMESTAMPTZ DEFAULT NOW()

-- ========== Growth Hub: 캠페인 ==========
campaigns
  id UUID PK
  client_id UUID FK → clients.id
  name VARCHAR(300) NOT NULL
  hashtag VARCHAR(200)
  start_date DATE
  end_date DATE
  goal_type VARCHAR(50) -- hashtag_count / followers / engagement
  goal_value INTEGER
  channels JSON -- ["instagram", "x"]
  status VARCHAR(20) DEFAULT 'draft' -- draft / active / ended
  result_metrics JSON
  created_at TIMESTAMPTZ DEFAULT NOW()

-- ========== Growth Hub: 경쟁사 계정 ==========
competitor_accounts
  id UUID PK
  client_id UUID FK → clients.id
  platform VARCHAR(50) NOT NULL
  handle VARCHAR(200) NOT NULL
  last_analyzed_at TIMESTAMPTZ
  analysis_result JSON
  created_at TIMESTAMPTZ DEFAULT NOW()
```

---

## 6. API 스펙 상세

### 6-1. 인증 (Auth) — 구현 완료 + 보완 필요

```
POST   /api/v1/auth/login
  Request:  { email: string, password: string }
  Response: { access_token: string, refresh_token: string }

POST   /api/v1/auth/refresh
  Request:  { refresh_token: string }
  Response: { access_token: string, refresh_token: string }

POST   /api/v1/auth/logout
  Response: { message: string }

POST   /api/v1/auth/forgot-password
  Request:  { email: string }
  Response: { message: string }
  TODO: 실제 이메일 발송 연동

POST   /api/v1/auth/reset-password
  Request:  { token: string, new_password: string }
  Response: { message: string }

POST   /api/v1/auth/change-password              ← 추가 필요
  Request:  { current_password: string, new_password: string }
  Response: { message: string }

POST   /api/v1/auth/invite                       ← 추가 필요
  Request:  { email: string, name: string, role: string }
  Response: { message: string, invite_token: string }

POST   /api/v1/auth/accept-invite                ← 추가 필요
  Request:  { token: string, password: string }
  Response: { message: string }
```

### 6-2. AI 서비스 — 전체 신규

> 모든 AI 텍스트 생성은 내부적으로 `subprocess.run(["claude", "--print", "--max-turns", "1", "-p", prompt])` 호출

```
POST   /api/v1/ai/generate-copy
  Request:  {
    client_id: UUID,
    topic: string,
    post_type: string,
    platforms: string[],      // ["instagram", "x", "facebook"]
    additional_context?: string
  }
  Response: {
    copies: [
      { variant: "A", text: string, hashtags: string[], platform_texts: { instagram: string, x: string, ... } },
      { variant: "B", ... },
      { variant: "C", ... }
    ]
  }

POST   /api/v1/ai/generate-image
  Request:  {
    prompt: string,
    tier: "nano2" | "nano_pro",     // Fal.ai 모델 선택
    aspect_ratio?: string,          // "1:1", "4:5", "9:16", "16:9"
    reference_urls?: string[],
    reference_strength?: float      // 0.0~1.0
  }
  Response: {
    image_url: string,
    generation_time_ms: int,
    cost_usd: float
  }

POST   /api/v1/ai/suggest-hashtags
  Request:  { text: string, platform: string, count?: int }
  Response: { hashtags: string[] }

POST   /api/v1/ai/concept-sets
  Request:  {
    client_id: UUID,
    topic: string,
    slide_count: int
  }
  Response: {
    sets: [
      { set_id: "A", title: string, tone: string, color_direction: string, preview_text: string },
      { set_id: "B", ... },
      { set_id: "C", ... }
    ]
  }

POST   /api/v1/ai/chat
  Request:  {
    content_id: UUID,
    message: string,
    context?: { slide_number?: int }
  }
  Response: {
    response: string,
    updated_fields?: { text?: string, hashtags?: string[], slides?: object[] }
  }

POST   /api/v1/ai/generate-strategy
  Request:  { client_id: UUID }
  Response: { strategy_markdown: string }
```

### 6-3. SNS 발행 — 전체 신규

```
POST   /api/v1/publish/instagram
  Request:  { content_id: UUID, channel_connection_id: UUID, caption: string, media_urls: string[] }
  Response: { platform_post_id: string, published_at: string }

POST   /api/v1/publish/facebook
  (동일 구조)

POST   /api/v1/publish/x
  Request:  { content_id: UUID, channel_connection_id: UUID, text: string, media_urls?: string[] }
  Response: { platform_post_id: string }

POST   /api/v1/publish/threads
POST   /api/v1/publish/kakao
POST   /api/v1/publish/tiktok
POST   /api/v1/publish/linkedin
POST   /api/v1/publish/youtube
```

### 6-4. 댓글/인박스 — 전체 신규

```
GET    /api/v1/inbox
  Query: client_id, channel_type, is_read, comment_type, page, limit
  Response: { items: Comment[], total: int }

POST   /api/v1/inbox/{comment_id}/reply
  Request:  { text: string }
  Response: { success: bool, platform_reply_id: string }

PATCH  /api/v1/inbox/{comment_id}/read
  Response: { success: bool }

PATCH  /api/v1/inbox/{comment_id}/hide
  Response: { success: bool }
```

### 6-5. 자동응답 룰

```
GET    /api/v1/auto-reply-rules?client_id=UUID
POST   /api/v1/auto-reply-rules
PUT    /api/v1/auto-reply-rules/{id}
DELETE /api/v1/auto-reply-rules/{id}
```

### 6-6. 성과 분석 — 전체 신규

```
GET    /api/v1/analytics/dashboard?client_id=UUID&period=7d
  Response: {
    channels: [{ platform, reach, impressions, likes, comments, followers_change, engagement_rate }],
    total_reach: int,
    total_engagement: int,
    period_comparison: { reach_change_pct: float, ... }
  }

GET    /api/v1/analytics/contents?client_id=UUID&period=30d&sort_by=reach
  Response: { items: [{ content_id, title, reach, likes, comments, saves, engagement_rate }] }

GET    /api/v1/analytics/content/{content_id}/timeline
  Response: { timeline: [{ period: "1h", metrics: {...} }, { period: "6h", ... }] }

GET    /api/v1/analytics/heatmap?client_id=UUID&channel=instagram
  Response: { heatmap: { "mon": { "09": 2.4, "10": 3.1, ... }, ... } }

POST   /api/v1/reports/generate
  Request:  { client_id: UUID, report_type: "weekly"|"monthly", period: string }
  Response: { pdf_url: string }
```

### 6-7. 알림

```
GET    /api/v1/notifications?is_read=false&limit=20
PATCH  /api/v1/notifications/{id}/read
PATCH  /api/v1/notifications/read-all
```

### 6-8. 검색

```
GET    /api/v1/search?q=keyword&type=content|asset|user&client_id=UUID
  Response: { contents: [...], assets: [...], users: [...] }
```

---

## 7. 인증/권한 설계 (보완)

### 7-1. JWT 토큰 구조

```json
{
  "sub": "user_uuid",
  "role": "admin|approver|editor|viewer",
  "type": "access|refresh",
  "exp": 1234567890,
  "iat": 1234567890
}
```

- Access Token: 2시간
- Refresh Token: 30일
- 비활성 2시간 후 자동 로그아웃 (프론트에서 체크)

### 7-2. 권한 체크 미들웨어 (보완 필요)

현재 `middleware/auth.py`에 `get_current_user`만 있고, 역할 기반 권한 체크 없음.

추가 필요:
```python
# middleware/auth.py에 추가
def require_role(*roles: str):
    """역할 기반 접근 제어 데코레이터"""
    async def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="권한이 없습니다")
        return current_user
    return dependency

# 사용 예시
@router.delete("/{user_id}")
async def delete_user(user_id: UUID, admin: User = Depends(require_role("admin"))):
    ...
```

### 7-3. SNS OAuth 연동 설계

```
[SNS Hub 프론트] → [백엔드 /api/v1/oauth/{platform}/init]
    → 302 Redirect to Platform OAuth URL
    → 사용자가 플랫폼에서 로그인/권한허용
    → Platform → [백엔드 /api/v1/oauth/{platform}/callback?code=xxx]
    → 백엔드가 code → access_token + refresh_token 교환
    → AES-256 암호화 후 channel_connections 테이블 저장
    → 프론트로 redirect (성공/실패)
```

각 플랫폼별 OAuth 엔드포인트:
```
GET    /api/v1/oauth/instagram/init?client_id=UUID
GET    /api/v1/oauth/instagram/callback?code=xxx&state=xxx
GET    /api/v1/oauth/facebook/init?client_id=UUID
GET    /api/v1/oauth/facebook/callback
GET    /api/v1/oauth/x/init?client_id=UUID
GET    /api/v1/oauth/x/callback
GET    /api/v1/oauth/kakao/init?client_id=UUID
GET    /api/v1/oauth/kakao/callback
GET    /api/v1/oauth/youtube/init?client_id=UUID
GET    /api/v1/oauth/youtube/callback
```

---

## 8. 콘텐츠 생성 파이프라인 (AI 연동)

### 8-1. Claude CLI 호출 래퍼

```python
# services/ai_service.py

import subprocess
import json

async def call_claude(prompt: str) -> str:
    """Claude CLI를 통한 텍스트 생성. Anthropic API 직접 호출 절대 금지."""
    result = subprocess.run(
        ["claude", "--print", "--max-turns", "1", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=120
    )
    if result.returncode != 0:
        raise Exception(f"Claude CLI 오류: {result.stderr}")
    return result.stdout.strip()
```

### 8-2. 카피 생성 파이프라인

```
1. 클라이언트 컨텍스트 로드
   - client_onboardings → 계정유형, 톤앤매너, 금지어
   - channel_strategy → 운영 전략서
   - benchmark_channels → 벤치마킹 결과

2. 프롬프트 구성
   - 시스템 프롬프트: 역할 + 규칙 + 출력 형식
   - 컨텍스트: 클라이언트 설정 + 채널 규격
   - 사용자 입력: 주제 + 키워드 + 발행 채널

3. Claude CLI 호출 → JSON 파싱
4. 채널별 글자수 검증 (인스타 2200자, X 280자 등)
5. 해시태그 자동 추천 (별도 Claude CLI 호출)
6. 3가지 변형(A/B/C) 반환
```

### 8-3. 이미지 생성 파이프라인

```
1. Claude CLI로 이미지 프롬프트 생성
2. Fal.ai API 호출 (tier 선택: nano2 / nano_pro)
3. 레퍼런스 이미지가 있으면 image-to-image 모드
4. 결과 이미지 S3/로컬 저장
5. 소재 라이브러리에 자동 등록
```

---

## 9. 예약 발행 시스템

### 9-1. Celery 구성

```python
# workers/celery_app.py
from celery import Celery
from celery.schedules import crontab

celery_app = Celery("sns_hub", broker="redis://localhost:6379/0")

celery_app.conf.beat_schedule = {
    "check-scheduled-posts": {
        "task": "workers.publish.check_and_publish",
        "schedule": 60.0,  # 매 1분마다
    },
    "collect-analytics": {
        "task": "workers.analytics.collect_metrics",
        "schedule": crontab(minute="0", hour="*/6"),  # 6시간마다
    },
    "refresh-tokens": {
        "task": "workers.tokens.check_and_refresh",
        "schedule": crontab(minute="0", hour="3"),  # 매일 03:00
    },
    "cleanup-trash": {
        "task": "workers.cleanup.delete_expired_trash",
        "schedule": crontab(minute="0", hour="4"),  # 매일 04:00
    },
}
```

### 9-2. 발행 워커 플로우

```
1. Celery Beat → 매 1분 check_and_publish 호출
2. schedules 테이블에서 status=pending, scheduled_at <= now() 조회
3. 각 schedule에 대해:
   a. channel_connections에서 토큰 확인
   b. 플랫폼별 발행 API 호출
   c. 성공: status=published, platform_post_id 저장
   d. 실패: retry_count++ (최대 3회, 5분 간격)
   e. 3회 실패: status=failed, 담당자 알림 발송
```

### 9-3. 발행 실패 재시도

```
retry_count=0 → 즉시 재시도
retry_count=1 → 5분 후
retry_count=2 → 10분 후
retry_count=3 → 실패 확정, 알림 발송
```

---

## 10. 분석/대시보드 설계

### 10-1. 성과 데이터 수집 타임라인

발행 후 자동 트래킹:
- 1시간 후: 초기 반응
- 6시간 후: 중간 성과
- 24시간 후: 1일 성과
- 3일 후: 3일 성과
- 7일 후: 주간 성과 (AI 인사이트 생성)
- 30일 후: 최종 기록 후 트래킹 종료

### 10-2. 대시보드 위젯 데이터 소스

| 위젯 | 데이터 소스 | API |
|---|---|---|
| 채널별 KPI | analytics 테이블 집계 | GET /analytics/dashboard |
| 오늘 발행 현황 | contents WHERE published_at = today | GET /dashboard/stats |
| 승인 대기 | contents WHERE status = pending_approval | GET /dashboard/stats |
| 최근 알림 | notifications 테이블 | GET /notifications |
| 채널 상태 | channel_connections.is_connected + token_expires_at | GET /dashboard/channel-status |

---

## 11. 파일 구조 (보완된 백엔드)

```
backend/
├── main.py
├── core/
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── redis.py
│   ├── exceptions.py
│   └── logging.py
├── models/
│   ├── user.py           ✅ 구현
│   ├── client.py         ✅ 구현
│   ├── content.py        ✅ 구현
│   ├── channel.py        ✅ 구현
│   ├── approval.py       ✅ 구현
│   ├── schedule.py       ✅ 구현
│   ├── onboarding.py     ✅ 구현
│   ├── log.py            ✅ 구현
│   ├── comment.py        🔴 추가 필요
│   ├── auto_reply.py     🔴 추가 필요
│   ├── analytics.py      🔴 추가 필요
│   ├── notification.py   🔴 추가 필요
│   ├── project.py        🔴 추가 필요
│   ├── external_approval.py  🔴 추가 필요
│   ├── asset.py          🟡 추가 필요
│   ├── campaign.py       🟡 추가 필요
│   └── monthly_plan.py   🟡 추가 필요
├── schemas/
│   ├── auth.py           ✅
│   ├── user.py           ✅
│   ├── client.py         ✅
│   ├── content.py        ✅
│   ├── channel.py        ✅
│   ├── approval.py       ✅
│   ├── schedule.py       ✅
│   ├── onboarding.py     ✅
│   ├── ai.py             🔴 추가
│   ├── comment.py        🔴 추가
│   ├── analytics.py      🔴 추가
│   └── notification.py   🔴 추가
├── routes/
│   ├── auth.py           ✅
│   ├── users.py          ✅
│   ├── clients.py        ✅
│   ├── contents.py       ✅
│   ├── channels.py       ✅
│   ├── onboarding.py     ✅
│   ├── dashboard.py      ✅ (보강 필요)
│   ├── health.py         ✅
│   ├── media.py          ✅
│   ├── ai.py             🔴 추가
│   ├── publish.py        🔴 추가
│   ├── inbox.py          🔴 추가
│   ├── analytics.py      🔴 추가
│   ├── notifications.py  🔴 추가
│   ├── oauth.py          🔴 추가
│   ├── search.py         🟡 추가
│   └── reports.py        🟡 추가
├── services/
│   ├── auth.py           ✅
│   ├── client.py         ✅
│   ├── user.py           ✅
│   ├── ai_service.py     🔴 추가 (Claude CLI 래퍼)
│   ├── image_service.py  🔴 추가 (Fal.ai 연동)
│   ├── publish_service.py 🔴 추가 (SNS 발행)
│   ├── sns/
│   │   ├── instagram.py  🔴 추가
│   │   ├── facebook.py   🔴 추가
│   │   ├── x_twitter.py  🔴 추가
│   │   ├── threads.py    🔴 추가
│   │   ├── kakao.py      🔴 추가
│   │   ├── youtube.py    🟡 추가
│   │   ├── tiktok.py     🟡 추가
│   │   └── linkedin.py   🟡 추가
│   ├── notification_service.py  🔴 추가
│   ├── email_service.py  🔴 추가
│   └── report_service.py 🟡 추가
├── workers/
│   ├── celery_app.py     🔴 추가
│   ├── publish.py        🔴 추가 (예약 발행 워커)
│   ├── analytics.py      🔴 추가 (성과 수집 워커)
│   ├── tokens.py         🔴 추가 (토큰 갱신 워커)
│   └── cleanup.py        🔴 추가 (휴지통 정리 워커)
├── repositories/
│   ├── base.py           ✅
│   ├── client.py         ✅
│   ├── user.py           ✅
│   ├── content.py        🔴 추가
│   ├── analytics.py      🔴 추가
│   └── comment.py        🔴 추가
├── middleware/
│   ├── auth.py           ✅ (역할 체크 보강 필요)
│   └── logging.py        ✅
├── alembic/
│   └── versions/
│       ├── 001_initial_tables.py     ✅
│       ├── 002_content_channel.py    ✅
│       ├── 003_comments_autoreplies.py    🔴 추가
│       ├── 004_analytics.py               🔴 추가
│       ├── 005_notifications.py           🔴 추가
│       ├── 006_external_approvals.py      🔴 추가
│       └── 007_projects_assets_plans.py   🟡 추가
└── tests/                🔴 전체 추가 필요
    ├── test_auth.py
    ├── test_contents.py
    ├── test_ai_service.py
    └── ...
```

---

## 12. 프론트엔드 구조 (현재)

```
frontend/src/
├── app/
│   ├── (auth)/login/page.tsx         ✅
│   ├── (main)/
│   │   ├── dashboard/page.tsx        ✅
│   │   ├── clients/page.tsx          ✅
│   │   ├── clients/[id]/page.tsx     ✅
│   │   ├── contents/page.tsx         ✅
│   │   ├── contents/new/page.tsx     ✅
│   │   ├── contents/[id]/page.tsx    ✅
│   │   ├── onboarding/page.tsx       ✅
│   │   ├── settings/users/page.tsx   ✅
│   │   └── layout.tsx                ✅
│   ├── privacy/page.tsx              ✅
│   └── terms/page.tsx                ✅
├── components/
│   ├── common/ (Button, Input, Modal, Toast, EmptyState, LoadingSpinner)  ✅
│   ├── layout/ (Sidebar, Header, AuthGuard)  ✅
│   └── onboarding/ (Step1~5)         ✅
├── hooks/ (useAuth, useClients)       ✅
├── services/ (api, auth, channels, clients, contents, onboarding, users)  ✅
├── types/ (auth, client, content, user)  ✅
├── constants/ (roles, routes)         ✅
└── utils/ (cn)                        ✅
```

프론트엔드 추가 필요 페이지:
- /calendar (캘린더 뷰 보강)
- /inbox (인박스 백엔드 연동)
- /approvals (승인 큐 백엔드 연동)
- /analytics (실데이터 연동)
- /growth-hub/* (Growth Hub 전체)
- /contents/new/card-news (에디터 보강)

---

*Master Chief 작성 · 에임탑 내부 문서 · 2026-04-03*
