# CLAUDE.md — SNS Hub (3계층: 프로젝트)

> 상위: ~/.claude/CLAUDE.md (전역) → AIMTOP-DEV-HARNESS.md (시스템)

---

## 프로젝트 개요

SNS 자동화 플랫폼
- URL: sns.aimtop.ai
- Admin: admin@aimtop.ai / aimtop2026!
- 배포: 맥미니 + CF Tunnel
- 포트: 프론트 1111, 백엔드 1112

## 핵심 규칙

- launchd 자동재시작 설정됨 — plist 수정 시 주의
- CF Tunnel 설정 함부로 변경 금지
- 새 도메인 만들지 말 것

## 서브에이전트 지시사항

- 맥미니 로컬 환경이라 Railway/Vercel과 다름
- 서버 재시작: launchctl 사용

---

_최종 갱신: 2026-04-03_
