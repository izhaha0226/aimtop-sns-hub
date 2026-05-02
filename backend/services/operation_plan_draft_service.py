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
    title = f"{month} · {week_number}주차 · {channel} · {content_format} · {index:02d}"
    product_angle = _pick(product_angles, index - 1, "상품성/차별점 메시지")
    target_insight = _pick(target_insights, index - 1, "핵심 타겟 공감")
    product_message = _clean_insight(product_angle)
    target_message = _clean_insight(target_insight)
    hook = _hook_for(theme=theme, objective=objective, product_message=product_message, target_message=target_message)
    body = _body_for(
        brand_name=brand_name,
        theme=theme,
        objective=objective,
        channel=channel,
        content_format=content_format,
        product_message=product_message,
        target_message=target_message,
    )
    visual_direction = _visual_direction_for(theme=theme, channel=channel, content_format=content_format, objective=objective)
    image_prompt = _image_prompt_for(
        brand_name=brand_name,
        theme=theme,
        objective=objective,
        channel=channel,
        content_format=content_format,
        visual_direction=visual_direction,
    )
    hashtags = _hashtags_for(brand_name=brand_name, channel=channel, objective=objective, theme=theme, product_message=product_message)
    text = "\n".join(
        [
            f"주제: {theme}",
            f"설명: {objective}를 위해 {target_message}에게 {product_message}를 연결하는 콘텐츠입니다.",
            f"훅: {hook}",
            f"본문: {body}",
            f"CTA: {brand_name}에 맞는 실행/상담/저장 행동으로 연결합니다.",
            f"이미지 방향: {visual_direction}",
            "주의: 벤치마킹은 구조만 참고하고 문구/캠페인 논리는 복제하지 않습니다.",
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
        "hashtags": hashtags,
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
            "sequence": index,
            "display_title": title,
            "visual_direction": visual_direction,
            "image_prompt": image_prompt,
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


def _clean_insight(value: Any) -> str:
    text = str(value or "").strip()
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    return text or "핵심 메시지"


def _hook_for(*, theme: str, objective: str, product_message: str, target_message: str) -> str:
    if "문제" in theme or "공감" in theme:
        return f"{target_message}가 반복해서 놓치는 문제를 {product_message} 관점으로 보여줍니다."
    if "증명" in theme or "차별" in theme:
        return f"비슷해 보이는 선택지 사이에서 {product_message}가 왜 다른지 증명합니다."
    if "문의" in objective:
        return f"지금 문의해야 하는 이유를 {target_message}의 손실 회피 관점으로 압축합니다."
    return f"{theme}를 {target_message}의 언어로 다시 정의합니다."


def _body_for(
    *,
    brand_name: str,
    theme: str,
    objective: str,
    channel: str,
    content_format: str,
    product_message: str,
    target_message: str,
) -> str:
    if channel in LONGFORM_CHANNELS:
        return (
            f"문제 제기 → {target_message}의 현재 운영 누수 → {brand_name}가 제안하는 {product_message} → "
            f"비교 기준 3가지 → {objective}로 이어지는 체크리스트 순서로 구성합니다."
        )
    if "카드" in content_format:
        return (
            f"1장: {theme}의 긴장감, 2장: {target_message}가 겪는 상황, 3장: 기존 방식의 한계, "
            f"4장: {product_message}, 5장: 행동 기준과 {objective} CTA로 마무리합니다."
        )
    if "릴스" in content_format or "영상" in content_format:
        return (
            f"첫 3초에 {theme}를 질문으로 던지고, 중간에는 {target_message}의 실제 장면을 보여준 뒤, "
            f"마지막에 {product_message}와 {objective} CTA를 짧게 연결합니다."
        )
    return (
        f"{target_message}의 공감 문장으로 시작해 {theme}의 문제를 드러내고, "
        f"{product_message}를 해결 프레임으로 제시한 뒤 {objective} 행동으로 닫습니다."
    )


def _visual_direction_for(*, theme: str, channel: str, content_format: str, objective: str) -> str:
    if "카드" in content_format:
        return f"카드뉴스형 정보 구조, 큰 문제 문장과 대비 컬러, {objective} CTA가 보이는 깔끔한 B2B 마케팅 비주얼"
    if "릴스" in content_format or "영상" in content_format:
        return f"짧은 영상 썸네일, 질문형 헤드라인, 실제 업무 장면과 {theme}를 상징하는 그래픽 오버레이"
    if channel in LONGFORM_CHANNELS:
        return f"블로그 커버 이미지, 체크리스트/비교표 느낌, {theme}를 설명하는 전문적이고 신뢰감 있는 비주얼"
    return f"SNS 피드용 정사각 비주얼, {theme} 핵심 키워드와 행동 유도 문구를 중심에 배치"


def _image_prompt_for(*, brand_name: str, theme: str, objective: str, channel: str, content_format: str, visual_direction: str) -> str:
    return (
        f"{brand_name} SNS 콘텐츠 이미지. 주제: {theme}. 목표: {objective}. "
        f"채널: {channel}, 형식: {content_format}. 비주얼 방향: {visual_direction}. "
        "한국어 텍스트가 들어갈 여백, 프리미엄 B2B 브랜드 톤, 과장된 스톡사진 금지, 경쟁사 문구 복제 금지."
    )


def _hashtags_for(*, brand_name: str, channel: str, objective: str, theme: str, product_message: str) -> list[str]:
    candidates = [
        brand_name,
        channel,
        objective,
        "SNS운영",
        "콘텐츠마케팅",
        _keyword_from(theme),
        _keyword_from(product_message),
    ]
    seen: set[str] = set()
    tags: list[str] = []
    for candidate in candidates:
        token = "".join(ch for ch in str(candidate) if ch.isalnum() or ch in ("_",))
        if not token or token in seen:
            continue
        seen.add(token)
        tags.append(f"#{token}")
    return tags[:8]


def _keyword_from(text: str) -> str:
    parts = [part.strip("/·,() ") for part in str(text).replace("/", " ").split()]
    return next((part for part in parts if len(part) >= 2), "마케팅")


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
