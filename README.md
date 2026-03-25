# AimTop SNS Hub

> 멀티 클라이언트 SNS 자동화 플랫폼

에임탑 내부 운영팀을 위한 통합 SNS 관리 시스템입니다.

## 지원 채널 (8개)

| 채널 | 기능 |
|---|---|
| 인스타그램 | 피드/릴스/스토리 발행, 댓글, 인사이트 |
| 페이스북 | 페이지 포스팅, 댓글, 광고 연동 |
| X (트위터) | 트윗/스레드, 답글, DM |
| Threads | 게시물 발행, 댓글 |
| 카카오채널 | 포스팅, 알림톡, 친구톡, 챗봇 |
| 틱톡 | 숏폼 영상 발행, 댓글 |
| 링크드인 | 페이지 포스팅, 댓글 |
| 유튜브 | 쇼츠/영상 발행, 댓글, 썸네일 |

## 기술 스택

### 프론트엔드
- Next.js 15 + Tailwind CSS + shadcn/ui
- 포트: 5000 / 도메인: sns.aimtop.ai

### 백엔드
- FastAPI (Python 3.12)
- 포트: 5001

### 인프라
- PostgreSQL 16 + Redis 7
- Celery (예약 발행 스케줄러)
- Mac mini + Cloudflare Tunnel

### AI
- Claude API (카피 생성)
- Fal.ai Nano Banana 2 / Pro (이미지 생성)
- Fal.ai Veo 3.1 / Kling (영상 생성)
- Canva Connect API (카드뉴스 조립)

## 프로젝트 구조

```
aimtop-sns-hub/
├── frontend/          # Next.js 프론트엔드
├── backend/           # FastAPI 백엔드
├── data/              # JSON/MD 파일 데이터
│   └── clients/       # 클라이언트별 워크스페이스
├── docs/              # 문서
│   └── SPEC.md        # 기획 SPEC
└── scripts/           # 유틸리티 스크립트
```

## 개발 현황

- [x] SPEC 작성 완료
- [ ] Sprint 1: 기반 구축 + 인증/권한
- [ ] Sprint 2: 클라이언트 온보딩
- [ ] Sprint 3: 콘텐츠 에디터 + AI 생성
- [ ] Sprint 4: 발행 자동화
- [ ] Sprint 5: 승인 프로세스
- [ ] Sprint 6: 댓글/DM 관리
- [ ] Sprint 7: 성과 분석
- [ ] Sprint 8: Growth Hub
- [ ] Sprint 9: 리포트 + 마무리

## 라이선스

Private — AimTop 내부용
