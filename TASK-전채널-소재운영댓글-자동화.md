# TASK — SNS Hub 전 채널 소재·운영·댓글 자동화

> 작성: 2026-07-12  
> 상태: **MVP 구현 진행/로컬 배포됨** (2026-07-12 오토파일럿)  
> 브랜치: `feature/channel-automation-engine`  
> 기준 repo: `~/projects/aimtop-sns-hub`  
> 상위 목표: 클라이언트가 채널을 연결하고 정책을 켜면, **소재 생성 → 승인/예약 → 실발행 → 댓글 수집/자동응답 → 성과 학습**이 전 채널에서 돌아가는 SNS 운영 OS

---

## 0. 한 줄 정의

**전 채널 공통 자동화 엔진**을 만든다.  
Agent Monitor / Control Tower는 이번 범위에서 **제외**한다.  
Threads 자동화 MVP는 **레퍼런스 패턴**으로만 사용하고, 전 채널 엔진으로 일반화한다.

---

## 1. 대표님 의도 (확정)

| 축 | 원하는 결과 |
|---|---|
| **소재** | 주제 1개 → 채널별 카피/이미지/카드뉴스/숏폼 초안 자동 생성 |
| **운영** | 승인·예약·실발행·재시도·토큰헬스·실패 알림 자동 |
| **댓글** | 수집 → 규칙/AI 매칭 → 자동응답 또는 인박스 에스컬레이션 |
| **전 채널** | Instagram, Facebook, Threads, X, YouTube, Blog, Kakao, TikTok, LinkedIn |

성공 기준(대표님 관점):

1. 클라이언트 선택 후 **자동화 ON**
2. 채널별 정책(하루 발행 수, 승인 필요 여부, 자동댓글 범위) 설정
3. 사람이 매일 채널마다 수동 업로드/답글을 반복하지 않음
4. 실패/권한 부족/토큰 만료는 **조용히 실패하지 않고** 인박스·배지로 드러남
5. 실발행 성공은 UI 배지가 아니라 **`platform_post_id` 또는 `published_url` 증거**로만 보고

---

## 2. 비목표 (이번 범위 밖)

- Agent Monitor / Control Tower UI 고도화
- 새 도메인 추가 (sns.aimtop.ai 유지, 추가 서브도메인 금지)
- Railway/Vercel 풀 이전 (별도 TASK)
- 더미/가짜 성과 데이터 DB 삽입
- Anthropic API 직접 호출 (Claude CLI / 기존 LLM router만)
- “예쁘기만 한 대시보드” 우선 작업

---

## 3. 현재 실측 갭 (코드 기준 2026-07-12)

### 3-1. 채널 능력 매트릭스

| 채널 | OAuth 코드 | 실발행 | 댓글 수집 | 댓글 답글 | 소재 변형 | 자동화 루프 |
|---|---|---|---|---|---|---|
| Instagram | ✅ | ✅ 코드 | ✅ | ✅ 코드 | ✅ topic | ❌ 공통 엔진 없음 |
| Facebook | ✅ | ✅ 코드 | ❌ | ❌ | ✅ topic | ❌ |
| Threads | ✅ | ✅ 코드 | ❌ | ❌ | ✅ topic | 🔶 Threads 전용 MVP |
| X | ✅ | ✅ 코드 | ❌ | ❌ | ✅ topic | ❌ |
| YouTube | ✅ | ✅ 코드 | ✅ | ✅ 코드 | △ 약함 | ❌ |
| Blog(Naver) | ✅ | ✅ 코드 | ❌ | ❌ | ✅ topic | ❌ |
| LinkedIn | ✅ | ✅ 코드 | ❌ | ❌ | ✅ topic | ❌ |
| Kakao | ✅ | ❌ 미구현 | ❌ | ❌ | 목록만 | ❌ |
| TikTok | ✅ | ❌ 미구현 | ❌ | ❌ | 목록 외 | ❌ |

참고 코드:

- 발행: `backend/services/sns_publisher.py`  
  `SUPPORTED_PLATFORMS = {instagram, threads, youtube, blog, x, facebook, linkedin}`
- OAuth: `backend/routes/oauth.py` 9채널
- 댓글: `backend/services/comment_service.py` — fetch/reply가 **instagram/youtube 중심**
- 소재: `content_topic_service.py` + `/contents/new/topic`  
  채널 목록: `instagram, facebook, threads, x, linkedin, kakao, blog` (TikTok 미포함)
- Threads 전용: `threads_automation_service.py` + `/growth/threads-automation`

### 3-2. 핵심 구조 문제

1. **채널별 if-else 파편** — 발행/댓글/OAuth/소재가 서로 다른 파일에 따로 존재
2. **Threads만 자동화 도메인 모델** — persona/target/draft/approval/action/learning이 Threads 전용 테이블
3. **소재→발행→댓글이 한 파이프라인으로 묶이지 않음** — 사람이 화면을 이동하며 수동 연결
4. **실발행 증거 계약 약함** — status=published만으로 성공 착각 가능
5. **권한/App Review 현실** — Meta/TikTok 등은 코드 있어도 실계정 권한 없으면 불가. 코드 완료 ≠ 실연동 가능을 분리 보고해야 함

---

## 4. 목표 아키텍처

```text
[Client Automation Policy]
   client_id + channel + enabled
   daily_quota / require_approval / auto_reply_mode / quiet_hours

        │
        ▼
[Material Pipeline]          소재
   topic / brief / benchmark
   → storyline / images / channel variants
   → contents(draft)

        │
        ▼
[Ops Pipeline]               운영
   approve (internal/external)
   → schedule
   → publish worker
   → evidence (platform_post_id, published_url, error)
   → retry / reauth gate

        │
        ▼
[Comment Pipeline]           댓글
   sync comments per channel
   → classify (rule / sentiment / spam)
   → auto-reply OR inbox escalate
   → action log

        │
        ▼
[Learning Loop]
   publish + engagement + reply outcome
   → next material hints / schedule suggestions
```

### 4-1. 공통 엔진 개념

| 개념 | 설명 |
|---|---|
| `ChannelCapability` | 채널별 지원 기능 선언(publish/media/comment_fetch/comment_reply/oauth_ready) |
| `AutomationPolicy` | 클라이언트×채널 정책 |
| `AutomationRun` | 1회 자동화 실행 단위(소재 배치 또는 스케줄 틱) |
| `ActionLog` | 모든 외부 API 호출의 읽기 가능 로그(성공/실패/증거) |
| `ChannelAdapter` | 플랫폼별 adapter 인터페이스 (publish / fetch_comments / reply) |

Threads 전용 모델(`ThreadsPersona` 등)은 1차로 유지하되,  
공통 엔진 인터페이스를 먼저 만들고 Threads를 첫 adapter 구현체로 편입한다.  
전 채널 완전 통합 스키마 마이그레이션은 Phase 2 이후.

---

## 5. 단계별 실행 계획

### Phase A — 계약 고정 + Capability Registry (0.5~1일)

**목표:** “이 채널에서 뭐가 되고 안 되는지”를 코드/UI/보고가 같은 표로 말하게 한다.

작업:

1. `backend/services/channel_capability.py` 신설  
   - 채널별: oauth, publish, media_types, comment_fetch, comment_reply, notes, blockers
2. `GET /api/v1/channels/capabilities`  
   - 프론트 자동화 설정 화면·클라이언트 상세에서 사용
3. 발행/댓글 서비스가 capability 밖 호출 시 명확한 400 메시지
4. 문서 표(본 TASK 3-1)와 코드 registry 동기화 테스트

완료 기준:

- [ ] capabilities API 200 + 9채널 전부 응답
- [ ] Kakao/TikTok publish 호출 시 “미지원” 400 (silent fail 금지)
- [ ] 단위 테스트: registry 키 누락 시 fail

---

### Phase B — 소재 자동화 강화 (1~2일)

**목표:** 주제 1개 → 선택 채널 N개 draft 콘텐츠 자동 생성까지 안정화.

기존 자산:

- `/contents/new/topic`
- `generate_topic_storyline` / `generate_card_images` / `create_channel_contents`

작업:

1. 채널 목록에 **YouTube / TikTok** 정책 반영  
   - 지원 불가면 UI 비활성 + 이유 표시
2. `build_channel_variant` 고도화  
   - 채널별 글자수/해시태그/미디어 규격
   - X 280, Threads 텍스트 중심, IG/FB 카드뉴스, Blog 장문, LinkedIn 전문 톤
3. 생성 결과 `contents`에  
   - `client_id` 강제  
   - `target_platform`  
   - `source_metadata.automation = true`  
   - 연결 가능한 `channel_connection_id` 후보 매핑
4. 소재 배치 API  
   - `POST /api/v1/automation/materials/generate`  
   - input: `client_id`, `topic/brief`, `channels[]`, `require_approval`
5. 실패 시 partial success 허용 + 채널별 error 배열 반환

완료 기준:

- [ ] 선택 클라이언트 + 3채널 이상 draft 생성 smoke
- [ ] 다른 client_id로 오염 저장 0건
- [ ] 채널 규격 위반 시 생성 단계에서 경고 또는 자동 트림

금지:

- client_id 없는 전역 생성
- 타 클라이언트 운영계획/콘텐츠 fallback

---

### Phase C — 운영 자동화 루프 (2~3일)

**목표:** draft → 승인 정책 → 예약/즉시 발행 → 증거 저장 → 실패 재시도.

기존 자산:

- `SNSPublisher`, `scheduler_service`, contents approve/schedule/publish

작업:

1. `AutomationPolicy` 모델/테이블  
   - `client_id`, `platform`, `enabled`, `require_approval`, `daily_limit`, `auto_publish_hours`, `auto_reply_enabled`
2. 스케줄러 틱에 automation worker 연결  
   - due schedule 발행  
   - reauth_required 채널 차단  
   - 실패 시 `publish_error` + Notification
3. 실발행 성공 계약 강화  
   - 성공: `platform_post_id` 또는 `published_url` 필수  
   - 없으면 status를 published로 올리지 않거나 `publish_unverified`로 분리
4. 일일 쿼터/중복 발행 가드
5. 프론트: 클라이언트 상세 또는 `/growth/automation`  
   - 채널별 ON/OFF, 승인 필요, 하루 한도, 최근 run 로그

완료 기준:

- [ ] 테스트 채널(가능 시) 1건 즉시 발행 시 외부 증거 필드 존재
- [ ] 토큰 만료 채널 예약 발행 차단 + 알림
- [ ] 실패 재시도 N회 후 BLOCKED/알림
- [ ] 회귀: `status=published` + 증거 없음 케이스를 테스트로 고정

---

### Phase D — 댓글 자동화 루프 (2~3일)

**목표:** 발행된 포스트 기준으로 댓글 수집·자동응답·인박스 에스컬레이션.

기존 자산:

- `CommentService`, `AutoReplyService`, `/inbox`

작업:

1. 댓글 adapter 확장 우선순위  
   1) Instagram (이미 있음)  
   2) YouTube (이미 있음)  
   3) Facebook Page  
   4) Threads  
   5) X  
   6) LinkedIn / Blog / Kakao / TikTok (가능 범위만, 불가 시 capability 명시)
2. 스케줄러: 활성 채널 댓글 sync 주기(예: 10~15분)
3. AutoReply  
   - 키워드/감성 규칙  
   - 위험 키워드(환불/욕설/법적) → 자동응답 금지, 인박스 에스컬레이션
4. 답글 전송 후 `replied_at` + action log
5. 인박스 UX  
   - 채널/상태 필터  
   - 자동응답됨 / 대기 / 실패 배지  
   - 선택 클라이언트 scope 강제

완료 기준:

- [ ] IG(+가능 채널) 댓글 sync smoke
- [ ] 규칙 매칭 자동응답 1건 evidence
- [ ] 위험 키워드 에스컬레이션 1건
- [ ] client scope 깨짐 0

---

### Phase E — Threads 패턴 전 채널 일반화 (2일, Phase C/D와 병행 가능)

**목표:** Threads 자동화 화면/모델을 “채널 자동화” 공통 UX의 첫 구현으로 승격.

작업:

1. `/growth/threads-automation` 기능을  
   `/growth/automation?platform=threads` 또는 공통 페이지 탭으로 확장 설계
2. persona / target rule / safety filter 개념을 platform-aware로 확장  
   - 1차는 Threads 데이터 유지 + platform 컬럼 추가 또는 공통 테이블 병행
3. draft 승인 큐를 contents 승인 흐름과 중복되지 않게 정렬  
   - 원칙: **최종 발행 단위는 contents**  
   - Threads draft는 contents로 promote 후 발행
4. learning event를 발행/댓글 성과와 연결

완료 기준:

- [ ] Threads 기존 MVP 회귀 없음
- [ ] Threads draft → content → publish 경로 문서화 + smoke
- [ ] 다른 채널 탭 추가 시 adapter만 붙이면 되는 구조

---

### Phase F — Kakao / TikTok 발행·댓글 (여력 시, 권한 의존)

**목표:** 미구현 2채널 메우기.  
단, **앱 검수/권한 없으면 코드만 준비하고 capability=blocked 유지**.

작업:

1. `SNSPublisher._publish_kakao` / `_publish_tiktok`
2. 필요 scope·redirect·미디어 규격 문서화
3. 댓글 API 가능 여부 조사 후 지원/미지원 명시
4. 실계정 검증 전 UI에 “준비됨/검수대기/실연동불가” 배지

완료 기준:

- [ ] publisher 코드 + 단위 테스트(mock)
- [ ] 실계정 없으면 “실연동 미검증”으로 보고 (과장 금지)

---

## 6. 프론트 정보구조 (제안)

| 경로 | 역할 |
|---|---|
| `/contents/new/topic` | 소재 생성(기존 강화) |
| `/growth/automation` | **신규** 전 채널 자동화 콘솔 (ON/OFF, 정책, run 로그) |
| `/growth/threads-automation` | 당분간 유지 → 이후 automation 탭으로 흡수 |
| `/contents`, `/contents/[id]` | draft/승인/발행 증거 표시 강화 |
| `/inbox` | 댓글 운영 콘솔 |
| `/clients/[id]` | 채널 연결 + capability + reauth |
| `/calendar` | 예약/자동화 발행 타임라인 |

Agent Monitor(`/agent-monitor`)는 운영 인프라 관측용으로 남기되,  
**본 자동화 제품 플로우의 진입점이 아니다.**

---

## 7. 데이터 / API 초안

### 7-1. 신규(또는 확장) 테이블

1. `channel_automation_policies`
   - id, client_id, platform, enabled, require_approval, daily_limit, auto_reply_enabled, quiet_hours_json, config_json, updated_at
2. `automation_runs`
   - id, client_id, kind(material|publish|comment_sync), status, started_at, finished_at, summary_json
3. `automation_action_logs`
   - id, run_id, client_id, platform, action, target_id, ok, evidence_json, error, created_at

기존 재사용:

- `contents`, `schedules`, `comments`, `auto_replies`, `channel_connections`, `notifications`
- Threads 전용 테이블 (Phase E에서 점진 편입)

### 7-2. API

```text
GET  /api/v1/channels/capabilities
GET  /api/v1/automation/policies?client_id=
PUT  /api/v1/automation/policies/{platform}
POST /api/v1/automation/materials/generate
POST /api/v1/automation/runs/{id}/retry
GET  /api/v1/automation/runs?client_id=
GET  /api/v1/automation/actions?client_id=
POST /api/v1/comments/sync          # 채널/클라이언트 단위
POST /api/v1/comments/{id}/reply
POST /api/v1/auto-replies/...       # 기존 유지/보강
```

모든 목록/생성 API는 **client_id scope 필수**.

---

## 8. 금지사항

1. `.env` 커밋, 시크릿 로그 출력
2. 더미 성과/가짜 댓글 DB 삽입 (명시 지시 없으면)
3. 포트 변경 (FE 1111 / BE 1112)
4. 새 도메인 제안
5. Anthropic API 직접 import
6. `status=published`만으로 실발행 성공 보고
7. 선택 클라이언트 없이 전체 클라이언트 콘텐츠/댓글 혼합 표시
8. 대규모 무관 리팩터링 (자동화 엔진에 필요 없는 파일 손대지 말 것)
9. Agent Monitor 작업을 본 TASK 완료로 치환 금지

---

## 9. 완료 기준 (Definition of Done)

### MVP DoD (Phase A~D)

1. capabilities registry + API
2. 소재 생성: 1 topic → ≥3 채널 draft
3. 운영: 승인 정책 반영 + 예약/즉시 발행 + 실패 알림
4. 댓글: 최소 IG(+가능 시 YT) sync + 규칙 자동응답 + 인박스
5. 자동화 콘솔에서 채널 ON/OFF와 최근 액션 로그 확인 가능
6. 회귀 테스트:
   - client scope
   - unsupported platform 400
   - publish evidence guard
   - auto-reply danger keyword escalate

### 보고 형식 (완료 보고 시 필수)

```text
- 채널별 capability 표 (코드/실계정 구분)
- smoke: material generate evidence
- smoke: publish evidence (post id/url or blocked reason)
- smoke: comment sync/reply evidence
- 미완/권한 blocker 목록
- 커밋 해시 / 브랜치
```

Truth Score 규칙:

- 코드 존재와 실계정 연동 가능을 분리
- env 누락 / App Review 대기는 “준비됨”이 아니라 “실연동 불가/대기”

---

## 10. 검증 체크리스트

### 로컬

```bash
# backend
cd ~/projects/aimtop-sns-hub/backend
source .venv/bin/activate
pytest -q tests/test_channel_capabilities.py tests/test_automation_*  # 추가 예정

# health
curl -s http://127.0.0.1:1112/health
curl -s http://127.0.0.1:1112/api/v1/channels/capabilities -H "Authorization: Bearer ..."

# frontend
cd ../frontend && npm run build
```

### 브라우저 smoke

1. 로그인 → 클라이언트 선택
2. `/contents/new/topic` 소재 생성
3. draft 목록에서 채널별 콘텐츠 확인
4. 승인/예약 또는 즉시 발행 (가능 채널)
5. `/inbox` 댓글 sync/자동응답
6. `/growth/automation` 정책 ON/OFF 및 로그

### 배포(요청 시)

- main push 후 로컬 launchd prod 경로 재기동
- `deploy-check.sh` 통과
- `sns.aimtop.ai` smoke
- 배포/prod DB/seed는 대표님 승인 후만

---

## 11. 리스크 / 의사결정 필요

| 항목 | 내용 | 기본안 |
|---|---|---|
| Meta 권한 | pages_manage_posts / IG publish 등 App Review 필요 가능 | 연결 최소 scope + 발행 권한 분리 유지 |
| 자동댓글 법적/브랜드 리스크 | 무조건 자동응답 위험 | 기본은 안전한 FAQ만, 민감 키워드는 인박스 |
| Threads 전용 테이블 | 즉시 공통화 vs 병행 | **병행 후 점진 편입** |
| Kakao/TikTok | 일정 내 실발행 미검증 가능 | capability blocked로 정직 표시 |
| LLM 런타임 | Claude CLI 맥미니 의존 | 기존 router 유지, 클라우드 이전은 별도 TASK |

---

## 12. 추천 착수 순서 (승인 후)

1. Phase A (capability)  
2. Phase B (소재)  
3. Phase C (운영 증거/스케줄)  
4. Phase D (댓글 IG 중심)  
5. Phase E (Threads 편입)  
6. Phase F (Kakao/TikTok — 여력)

예상 MVP 기간: **약 5~8 작업일** (실계정 권한 대기는 제외)

---

## 13. 승인 요청

대표님 확인 필요:

1. 이 TASK 범위(전 채널 소재·운영·댓글 자동화)로 진행할지
2. MVP에서 **실동작 우선 채널**  
   - 추천: `Instagram + Threads + Facebook + X`  
   - YouTube/Blog/LinkedIn은 발행 유지, 댓글은 가능한 것만  
   - Kakao/TikTok은 2차
3. 자동댓글 기본 정책  
   - 추천: **안전 FAQ 자동 + 민감 이슈 수동 에스컬레이션**
4. 승인 후 브랜치 `feature/channel-automation-engine` 생성하고 Phase A부터 구현

---

## 14. 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-07-12 | 초안 작성. Agent Monitor 요청을 전 채널 자동화 의도로 재정의 후 TASK 고정 |
