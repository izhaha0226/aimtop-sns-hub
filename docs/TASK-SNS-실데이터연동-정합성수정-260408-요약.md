# TASK-SNS-실데이터연동-정합성수정-260408 요약

- **작성일시:** 2026-04-08 23:24 KST
- **대상:** AimTop SNS Hub (`sns.aimtop.ai`)
- **주도:** 헤리 (P1+P3 작업), Master Chief 검증 정리

## 1. 작업 범위 정리

요청된 범위는 아래 2개로 제한하여 반영했습니다.

- **P1:** analytics / inbox / calendar API 계약 정합성 복구
- **P3:** 헤더 클라이언트 셀렉터 및 알림벨 최소 동작 연결

## 2. 실행 결과 (커밋)

- **브랜치:** `fix/sns-p1-p3-contract-alignment`
- **커밋:** `ee01861`
- **메시지:** `feat: align analytics/inbox/calendar APIs with client+channel contracts`

## 3. 변경 파일

- `backend/routes/comments.py`
- `backend/routes/schedule.py`
- `backend/services/comment_service.py`
- `frontend/src/app/(main)/analytics/page.tsx`
- `frontend/src/app/(main)/calendar/page.tsx`
- `frontend/src/app/(main)/inbox/page.tsx`
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/hooks/useSelectedClient.ts`
- `frontend/src/lib/selected-client.ts`
- `frontend/src/services/channels.ts`
- `frontend/src/services/notifications.ts`

## 4. 핵심 반영 포인트

### P1
- analytics: `summary`/`insights` 엔드포인트를 `/{account_id}` 기반 경로에 맞추고, `content-performance` 호출을 `client_id` 전달 형태로 조정
- inbox: `/all` 형태 호출 제거, `/{account_id}` 기반 조회/동기화 호출로 전환
- calendar: 백엔드 객체 응답(`dates`)에서 화면용 배열로 변환해 표시하도록 보호

### P3
- 헤더 클라이언트 선택 상태를 실제 앱 상태로 연결
- 알림 API(`GET /api/v1/notifications`, `GET /api/v1/notifications/unread-count`) 연결 및 읽음 처리 경로 연결

## 5. 검증

- `npm run -s lint` ✅
- `npm run -s build` ✅
- `python3 -m compileall -q backend` ✅
- `pytest -q` ❌ (`pytest` command not found)

## 6. 남은 P2 후보

- 다중 채널 집계/선택 UX 정교화
- `/comments/all`, `/comments/sync/all` 정책 정리(현재 호환 경로 유지)
- 알림 갱신 주기/오류표시 UX 보완
