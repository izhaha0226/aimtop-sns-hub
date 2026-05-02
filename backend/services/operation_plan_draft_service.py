"""Build content draft specs from an approved operation plan.

This service is intentionally side-effect free. Routes may persist the returned
specs as Content records, but the builder itself never schedules or uploads.
"""
from __future__ import annotations

from typing import Any

SCHEDULE_CAPABLE_CHANNELS = {"instagram", "facebook", "threads", "x", "twitter", "linkedin"}
LONGFORM_CHANNELS = {"blog", "naver_blog"}
VIDEO_CHANNELS = {"youtube", "tiktok"}


class OperationPlanDraftError(ValueError):
    pass


def build_content_draft_specs_from_plan(
    *,
    operation_plan_id: Any,
    status: str,
    plan_payload: dict[str, Any] | None,
    client_id: Any | None,
    author_id: Any | None,
) -> list[dict[str, Any]]:
    """Convert an approved operation-plan payload into draft content specs."""
    if status != "approved":
        raise OperationPlanDraftError("승인된 운영계획만 콘텐츠 draft를 생성할 수 있습니다")
    if not client_id:
        raise OperationPlanDraftError("content draft 생성을 위해 client_id가 필요합니다")
    if not plan_payload:
        raise OperationPlanDraftError("운영계획 payload가 없습니다")

    brand_name = str(plan_payload.get("brand_name") or "브랜드")
    month = str(plan_payload.get("month") or "운영월")
    benchmark_source_status = str(plan_payload.get("benchmark_source_status") or "manual_or_pending")
    benchmark_notes = list(plan_payload.get("benchmark_notes") or [])
    product_angles = list(plan_payload.get("product_angles") or [])
    target_insights = list(plan_payload.get("target_insights") or [])
    channel_plan = _channel_plan_by_name(plan_payload.get("channel_plan") or [])

    drafts: list[dict[str, Any]] = []
    for week in plan_payload.get("weekly_plan") or []:
        week_number = int(week.get("week") or len(drafts) + 1)
        theme = str(week.get("theme") or f"{month} {week_number}주차 콘텐츠")
        objective = str(week.get("objective") or "브랜드 인지도")
        for weekly_channel in week.get("channels") or []:
            channel = str(weekly_channel.get("channel") or "sns").lower()
            count = max(1, int(weekly_channel.get("count") or 1))
            formats = list(weekly_channel.get("formats") or channel_plan.get(channel, {}).get("recommended_formats") or ["정보형 포스트"])
            for index in range(1, count + 1):
                content_format = str(formats[(index - 1) % len(formats)]) if formats else "정보형 포스트"
                drafts.append(
                    _build_single_draft(
                        operation_plan_id=operation_plan_id,
                        client_id=client_id,
                        author_id=author_id,
                        brand_name=brand_name,
                        month=month,
                        week_number=week_number,
                        channel=channel,
                        index=index,
                        content_format=content_format,
                        theme=theme,
                        objective=objective,
                        benchmark_source_status=benchmark_source_status,
                        benchmark_notes=benchmark_notes,
                        product_angles=product_angles,
                        target_insights=target_insights,
                    )
                )
    if not drafts:
        raise OperationPlanDraftError("생성할 주차/채널 draft 항목이 없습니다")
    return drafts


def _channel_plan_by_name(channel_plan: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("channel") or "").lower(): item for item in channel_plan if item.get("channel")}


def _build_single_draft(
    *,
    operation_plan_id: Any,
    client_id: Any,
    author_id: Any,
    brand_name: str,
    month: str,
    week_number: int,
    channel: str,
    index: int,
    content_format: str,
    theme: str,
    objective: str,
    benchmark_source_status: str,
    benchmark_notes: list[Any],
    product_angles: list[Any],
    target_insights: list[Any],
) -> dict[str, Any]:
    title = f"[{brand_name}] {month} {week_number}주차 {channel} {content_format} #{index}"
    text = "\n".join(
        [
            f"목표: {objective}",
            f"테마: {theme}",
            f"포맷: {content_format}",
            f"핵심 메시지: {_pick(product_angles, index - 1, '상품성/차별점 메시지')}",
            f"타겟 인사이트: {_pick(target_insights, index - 1, '핵심 타겟 공감')}",
            "CTA: 저장/문의/상담 중 대표님 승인 후 확정",
            "주의: 벤치마킹 문구 복제 금지, 구조만 참고",
        ]
    )
    return {
        "client_id": client_id,
        "author_id": author_id,
        "operation_plan_id": operation_plan_id,
        "post_type": _post_type_for(channel, content_format),
        "title": title,
        "text": text,
        "media_urls": [],
        "hashtags": [f"#{brand_name}", f"#{channel}", "#SNS운영"],
        "status": "draft",
        "channel_connection_id": None,
        "scheduled_at": None,
        "source_metadata": {
            "source": "operation_plan",
            "operation_plan_id": str(operation_plan_id),
            "channel": channel,
            "week": week_number,
            "objective": objective,
            "format": content_format,
            "benchmark_source_status": benchmark_source_status,
            "benchmark_notes": [str(note) for note in benchmark_notes],
            "channel_action": _channel_action(channel),
            "safety_notes": [
                "외부 업로드 없음",
                "대표님 콘텐츠별 승인 전 예약/발행 금지",
                "벤치마킹 문구 복제 금지",
            ],
        },
    }


def _pick(items: list[Any], index: int, fallback: str) -> str:
    if not items:
        return fallback
    return str(items[index % len(items)])


def _post_type_for(channel: str, content_format: str) -> str:
    format_text = content_format.lower()
    if channel in VIDEO_CHANNELS or "릴스" in content_format or "쇼츠" in content_format or "영상" in content_format:
        return "reels"
    if channel in LONGFORM_CHANNELS:
        return "text"
    if "카드" in content_format or "인포" in content_format:
        return "card_news"
    return "text"


def _channel_action(channel: str) -> str:
    if channel in SCHEDULE_CAPABLE_CHANNELS:
        return "token_check_required"
    return "manual_required"
