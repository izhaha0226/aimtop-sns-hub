"""Content operation planner for monthly SNS channel strategy.

The planner returns an honest, approval-first operation plan from a brand brief,
benchmark brands, target, goals, channels, and season context. It never claims
live benchmark collection unless a caller explicitly provides that evidence in a
future integration layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


CHANNEL_DEFAULT_MONTHLY_VOLUME: dict[str, int] = {
    "instagram": 16,
    "threads": 20,
    "x": 20,
    "twitter": 20,
    "blog": 4,
    "naver_blog": 4,
    "youtube": 8,
    "tiktok": 8,
    "facebook": 12,
    "kakao": 6,
    "linkedin": 6,
}

CHANNEL_FORMATS: dict[str, list[str]] = {
    "instagram": ["카드뉴스", "릴스", "스토리", "고객 후기/비포애프터"],
    "threads": ["짧은 관점 스레드", "질문형 포스트", "운영자 코멘트", "체크리스트"],
    "x": ["짧은 관점 포스트", "스레드", "실시간 이슈 코멘트"],
    "twitter": ["짧은 관점 포스트", "스레드", "실시간 이슈 코멘트"],
    "blog": ["문제 해결형 글", "비교/가이드", "사례 소개", "검색형 FAQ"],
    "naver_blog": ["문제 해결형 글", "비교/가이드", "사례 소개", "검색형 FAQ"],
    "youtube": ["쇼츠", "문제 해결 영상", "제품/서비스 데모", "고객 사례"],
    "tiktok": ["숏폼", "트렌드 사운드 활용", "짧은 팁", "현장감 콘텐츠"],
    "facebook": ["카드형 소식", "이벤트 공지", "후기", "커뮤니티 질문"],
    "kakao": ["프로모션 공지", "쿠폰/혜택", "상담 유도", "재방문 리마인드"],
    "linkedin": ["전문성 글", "인사이트 카드", "케이스 스터디", "성과 지표 공유"],
}


@dataclass(frozen=True)
class OperationPlanRequestData:
    brand_name: str
    product_summary: str
    target_audience: str = ""
    goals: list[str] = field(default_factory=list)
    channels: list[str] = field(default_factory=lambda: ["instagram", "threads"])
    benchmark_brands: list[str] = field(default_factory=list)
    month: str | None = None
    season_context: str = ""
    budget_level: str = "standard"
    notes: str = ""
    benchmark_insights: list[dict[str, Any]] = field(default_factory=list)


def _normalize_channels(channels: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for channel in channels or []:
        value = str(channel or "").strip().lower()
        if value and value not in normalized:
            normalized.append(value)
    return normalized or ["instagram", "threads"]


def _resolve_month(month: str | None) -> str:
    if month and month.strip():
        return month.strip()
    return datetime.now().strftime("%Y-%m")


def _seasonal_text(month: str, explicit_context: str) -> str:
    if explicit_context.strip():
        return explicit_context.strip()
    month_num = 0
    try:
        month_num = int(month.split("-")[1])
    except (IndexError, ValueError):
        pass
    defaults = {
        1: "신년 목표/습관 형성/설 연휴 준비 시즌",
        2: "설 이후 재정비/봄 준비/졸업·입학 시즌",
        3: "봄 시작/신학기/새 프로젝트 착수 시즌",
        4: "봄나들이/중간고사/상반기 캠페인 강화 시즌",
        5: "가정의 달/야외 활동/선물 수요 시즌",
        6: "초여름/장마 시작/상반기 마감 시즌",
        7: "여름휴가/방학/시원함과 즉시성 소비 시즌",
        8: "휴가 피크/개학 준비/막바지 여름 프로모션 시즌",
        9: "가을 시작/추석/하반기 루틴 재시작 시즌",
        10: "가을 활동/중간고사/연말 준비 진입 시즌",
        11: "블랙프라이데이/수능/연말 예산 편성 시즌",
        12: "연말 결산/크리스마스/새해 준비 시즌",
    }
    return defaults.get(month_num, "해당 월의 소비 맥락과 브랜드 캠페인 시즌")


def _volume_for_channel(channel: str, goal_count: int) -> int:
    base = CHANNEL_DEFAULT_MONTHLY_VOLUME.get(channel, 8)
    if goal_count >= 3 and channel in {"instagram", "threads", "x", "twitter"}:
        return base + 4
    return base


def _weekly_theme(week: int, brand_name: str, goals: list[str], season_context: str) -> str:
    goal = goals[(week - 1) % len(goals)] if goals else "인지도 확보"
    themes = {
        1: f"{brand_name} 문제 인식과 시즌 공감 형성",
        2: f"상품성/차별점 증명과 {goal} 메시지 강화",
        3: "벤치마킹 패턴을 변주한 참여/저장 유도 콘텐츠",
        4: "전환 CTA와 월말 리마인드/성과 회수",
    }
    if week == 1 and season_context:
        return f"{themes[week]} ({season_context})"
    return themes.get(week, f"{goal} 집중 운영")


def build_supermarketing_strategy(req: OperationPlanRequestData) -> list[str]:
    """Build the Supermarketing strategy layer that must precede weekly planning.

    This deterministic layer mirrors the supermarketing-aimtop workflow so the
    operation planner never jumps straight to a calendar. It first frames the
    audience, offer, angle, benchmark boundaries, and validation loop. The LLM
    path may improve these items, but fallback plans still expose the same
    strategic spine.
    """
    goals = [goal.strip() for goal in req.goals if str(goal).strip()] or ["브랜드 인지도", "문의/전환"]
    channels = _normalize_channels(req.channels)
    if req.benchmark_insights:
        live_count = sum(1 for item in req.benchmark_insights if str(item.get("source_status") or "").startswith("live_collected"))
        evidence_count = sum(int(item.get("evidence_count") or 0) for item in req.benchmark_insights)
        benchmark_scope = (
            f"{len(req.benchmark_insights)}개 벤치마킹 인사이트 / 증거 포스트 {evidence_count}개 "
            f"/ 실수집 가능·성공 {live_count}개. 문구 복제 금지, 구조만 변환."
        )
    else:
        benchmark_scope = (
            ", ".join(req.benchmark_brands)
            if req.benchmark_brands
            else "입력된 벤치마킹 브랜드 없음 — 업종 공통 패턴만 가정"
        )
    return [
        (
            "Brief lock: "
            f"{req.brand_name}의 오퍼는 '{req.product_summary}'이며, 핵심 타겟은 "
            f"'{req.target_audience or '구매/문의 가능성이 높은 잠재 고객'}'로 둔다."
        ),
        (
            "Positioning angle: 문제 공감 → 상품성/차별점 증명 → 행동 유도 순서로 설득하며, "
            f"이번 목표는 {', '.join(goals)}에 맞춰 우선순위를 둔다."
        ),
        (
            "Benchmark rule: "
            f"{benchmark_scope}. 문구/슬로건/캠페인 논리는 복제하지 않고 hook shape, pacing, CTA rhythm만 참고한다."
        ),
        (
            "Channel execution: "
            f"{', '.join(channels)}별로 같은 캠페인 spine을 유지하되 저장형/대화형/검색형/전환형 문법으로 변환한다."
        ),
        (
            "Validation loop: 대표님 승인 전 외부 업로드를 금지하고, 승인 후 draft 성과는 CTR·저장·댓글·문의 전환으로 검증한다."
        ),
    ]


def build_fallback_operation_plan(req: OperationPlanRequestData) -> dict[str, Any]:
    """Build a deterministic monthly operation plan without claiming live AI/data collection."""
    channels = _normalize_channels(req.channels)
    goals = [goal.strip() for goal in req.goals if str(goal).strip()] or ["브랜드 인지도", "문의/전환"]
    month = _resolve_month(req.month)
    season_context = _seasonal_text(month, req.season_context)
    supermarketing_strategy = build_supermarketing_strategy(req)
    monthly_volume = {channel: _volume_for_channel(channel, len(goals)) for channel in channels}
    total_volume = sum(monthly_volume.values())

    channel_plan = []
    for channel in channels:
        formats = CHANNEL_FORMATS.get(channel, ["정보형 포스트", "후기/사례", "CTA 포스트"])
        channel_plan.append(
            {
                "channel": channel,
                "monthly_count": monthly_volume[channel],
                "recommended_formats": formats,
                "role": _channel_role(channel),
                "cadence": _channel_cadence(monthly_volume[channel]),
            }
        )

    weekly_plan = []
    for week in range(1, 5):
        weekly_channels = []
        for channel in channels:
            count = max(1, round(monthly_volume[channel] / 4))
            weekly_channels.append(
                {
                    "channel": channel,
                    "count": count,
                    "formats": CHANNEL_FORMATS.get(channel, ["정보형 포스트"])[0:2],
                }
            )
        weekly_plan.append(
            {
                "week": week,
                "theme": _weekly_theme(week, req.brand_name, goals, season_context),
                "objective": goals[(week - 1) % len(goals)],
                "channels": weekly_channels,
            }
        )

    benchmark_notes = [
        f"{brand}: 문구 복제가 아니라 후킹 구조·포맷·CTA 패턴만 참고" for brand in req.benchmark_brands
    ] or ["벤치마킹 계정 미입력: 업종 공통 패턴 기반 초안으로 시작"]
    if req.benchmark_insights:
        benchmark_notes = []
        for insight in req.benchmark_insights[:8]:
            brand = insight.get("brand") or "벤치마킹 대상"
            channel = insight.get("channel") or "channel"
            evidence_count = int(insight.get("evidence_count") or 0)
            status = insight.get("source_status") or "manual_or_pending"
            benchmark_notes.append(f"{brand}/{channel}: {status}, 증거 {evidence_count}개 — hook/format/CTA 구조만 변환")

    benchmark_source_status = "manual_or_pending"
    if req.benchmark_insights:
        statuses = {str(item.get("source_status") or "manual_or_pending") for item in req.benchmark_insights}
        if any(status.startswith("live_collected") for status in statuses):
            benchmark_source_status = "live_or_cached_evidence"
        elif any(status in {"no_data_collected", "collector_error"} for status in statuses):
            benchmark_source_status = "collector_checked_no_live_data"

    return {
        "brand_name": req.brand_name,
        "month": month,
        "strategy_summary": (
            f"{req.brand_name}의 {month} 운영은 '{season_context}' 맥락에서 "
            f"{', '.join(goals)}를 달성하도록 총 {total_volume}개 콘텐츠를 채널별로 배분합니다."
        ),
        "target_insights": [
            f"핵심 타겟: {req.target_audience or '구매/문의 가능성이 높은 잠재 고객'}",
            "초반에는 문제 공감, 중반에는 상품성 증명, 후반에는 행동 유도를 강화합니다.",
        ],
        "product_angles": [
            f"상품/서비스 핵심: {req.product_summary}",
            "비교 우위, 사용 장면, 고객 변화, 리스크 제거 메시지로 분해합니다.",
        ],
        "supermarketing_strategy": supermarketing_strategy,
        "seasonal_context": season_context,
        "benchmark_source_status": benchmark_source_status,
        "benchmark_notes": benchmark_notes,
        "benchmark_insights": req.benchmark_insights,
        "monthly_volume": monthly_volume,
        "total_monthly_count": total_volume,
        "weekly_plan": weekly_plan,
        "channel_plan": channel_plan,
        "approval_checklist": [
            "브랜드명/상품 설명/타겟 정의가 정확한지 승인",
            "월간 총 제작 수량이 실제 운영 리소스에 맞는지 승인",
            "채널별 콘텐츠 포맷과 업로드 빈도 승인",
            "벤치마킹 브랜드 참고 범위와 금지 표현 확인",
            "승인 전 외부 채널 업로드 없음",
        ],
        "risks": [
            "실수집 벤치마킹 데이터가 없으면 수동/프록시 분석으로 표시해야 합니다.",
            "콘텐츠 수량이 많을수록 이미지 제작/검수 병목이 발생할 수 있습니다.",
            "프로모션/가격/의료·금융·법률 표현은 업로드 전 별도 검수가 필요합니다.",
        ],
        "next_actions": [
            "대표님 승인 후 주차별 콘텐츠 draft bulk 생성",
            "채널 연결 상태 확인 후 예약 가능/수동 필요 항목 분리",
            "카드뉴스·숏폼·블로그별 제작 프롬프트 생성",
        ],
    }


def _channel_role(channel: str) -> str:
    roles = {
        "instagram": "시각적 신뢰와 저장/공유 유도",
        "threads": "관점 확산과 대화 유도",
        "x": "실시간 관점 확산",
        "twitter": "실시간 관점 확산",
        "blog": "검색 유입과 상세 설득",
        "naver_blog": "검색 유입과 상세 설득",
        "youtube": "영상 기반 신뢰/데모",
        "tiktok": "짧은 발견과 바이럴 실험",
        "facebook": "커뮤니티 도달과 이벤트 안내",
        "kakao": "관계 기반 재방문/전환",
        "linkedin": "B2B 전문성/신뢰 구축",
    }
    return roles.get(channel, "브랜드 접점 확장")


def _channel_cadence(monthly_count: int) -> str:
    weekly = max(1, round(monthly_count / 4))
    return f"주 {weekly}회 내외"
