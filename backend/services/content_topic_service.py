import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.content import Content
from models.content_topic import ContentTopic
from services.ai_service import call_llm_json
from services.image_service import generate_image

logger = logging.getLogger(__name__)

CARD_ARC = [
    (1, "강한 후킹", "첫 장에서 스크롤을 멈추게 하는 한 문장과 핵심 장면"),
    (2, "문제/맥락", "타깃이 공감하는 문제 또는 상황 제시"),
    (3, "메커니즘/차별점", "왜 이 제안이 다른지 증거와 구조 설명"),
    (4, "효과/결과", "사용자가 얻는 변화, 혜택, 사회적 증거"),
    (5, "CTA", "저장/문의/구매/상담 등 다음 행동 유도"),
]


def _asset_context(topic: ContentTopic) -> str:
    assets = topic.reference_assets or []
    if not assets:
        return "첨부/참고 이미지 없음"
    lines = []
    for idx, asset in enumerate(assets, 1):
        lines.append(
            f"{idx}. type={asset.get('asset_type')} usage={asset.get('usage_mode')} "
            f"cards={asset.get('target_cards')} memo={asset.get('memo') or ''} url={asset.get('url')}"
        )
    return "\n".join(lines)


def build_fallback_storyline(topic: ContentTopic) -> list[dict[str, Any]]:
    base = topic.core_message or topic.brief or topic.title
    return [
        {
            "card_no": no,
            "headline": f"{topic.title}: {role}",
            "body": f"{base}\n{desc}",
            "visual_brief": f"{role}를 직관적으로 보여주는 프리미엄 SNS 카드뉴스 장면. {_asset_context(topic)}",
            "cta_or_transition": "다음 장에서 확인" if no < 5 else "지금 문의/저장하기",
        }
        for no, role, desc in CARD_ARC
    ]


async def generate_topic_storyline(topic: ContentTopic, db: AsyncSession, engine: dict | None = None) -> list[dict[str, Any]]:
    prompt = f"""
너는 AimTop SNS Hub의 Supermarketing 카드뉴스 전략가다.
아래 주제로 먼저 5장 카드뉴스 내용/스토리라인을 만든다. 이미지는 아직 만들지 않는다.

[주제]
{topic.title}

[브리프]
{topic.brief or ''}

[목표]
{topic.objective or ''}

[타깃]
{topic.target_audience or ''}

[핵심 메시지]
{topic.core_message or ''}

[첨부/참고/합성 자산]
{_asset_context(topic)}

[규칙]
- 정확히 5장.
- Card 1: 후킹, Card 2: 문제/맥락, Card 3: 메커니즘/차별점, Card 4: 효과/증거, Card 5: CTA.
- 각 장은 headline, body, visual_brief, cta_or_transition을 포함.
- 첨부 자산이 있으면 usage_mode와 target_cards를 visual_brief에 반영.
- JSON 배열로만 반환.
예: [{{"card_no":1,"headline":"...","body":"...","visual_brief":"...","cta_or_transition":"..."}}]
""".strip()
    try:
        result = await call_llm_json("copy_generation", prompt, engine=engine, timeout=180, db=db)
        items = result if isinstance(result, list) else result.get("cards", [])
        if len(items) >= 5:
            return items[:5]
    except Exception as exc:  # fallback keeps autonomous UX alive when LLM route is unavailable
        logger.warning("topic storyline LLM fallback: %s", exc)
    return build_fallback_storyline(topic)


def build_visual_option_prompts(topic: ContentTopic) -> list[dict[str, Any]]:
    storyline = topic.card_storyline or build_fallback_storyline(topic)
    first = storyline[0]
    base = f"""
SNS 카드뉴스 1장차 표지 이미지. 주제: {topic.title}
헤드라인: {first.get('headline')}
본문 요지: {first.get('body')}
장면 지시: {first.get('visual_brief')}
첨부/참고/합성 자산: {_asset_context(topic)}
한국어 텍스트는 짧고 선명하게, 모바일 정사각형 1024x1024, 프리미엄 브랜드 광고 품질.
""".strip()
    return [
        {"option_id": "photorealistic_1", "label": "실사형 1안", "style_type": "photorealistic", "prompt": base + "\n스타일: 고급 실사 광고 사진, 자연광, 제품/인물 합성 가능, 현실적인 질감."},
        {"option_id": "photorealistic_2", "label": "실사형 2안", "style_type": "photorealistic", "prompt": base + "\n스타일: 대담한 실사 캠페인 비주얼, 극적인 조명, 강한 후킹 구도, 현실적인 합성."},
        {"option_id": "illustration_3", "label": "일러스트형 3안", "style_type": "illustration", "prompt": base + "\n스타일: 세련된 브랜드 일러스트, 명확한 아이콘/캐릭터/그래픽 메타포, 깔끔한 타이포그래피."},
    ]


async def generate_first_slide_options(topic: ContentTopic, *, size: str = "1024x1024", model: str = "fast") -> list[dict[str, Any]]:
    options = build_visual_option_prompts(topic)
    generated = []
    for option in options:
        try:
            result = await generate_image(option["prompt"], size=size, model=model, quality="medium")
            option["image_url"] = result.get("image_url")
            option["model_used"] = result.get("model_used")
        except Exception as exc:
            logger.warning("visual option generation failed (%s): %s", option["option_id"], exc)
            option["image_url"] = None
            option["error"] = str(exc)
        generated.append(option)
    return generated


def _selected_option(topic: ContentTopic) -> dict[str, Any] | None:
    selected = topic.selected_visual_option
    for option in topic.visual_options or []:
        if option.get("option_id") == selected:
            return option
    return None


async def generate_card_images(topic: ContentTopic, *, size: str = "1024x1024", model: str = "fast", quality: str | None = "medium") -> list[str]:
    storyline = topic.card_storyline or build_fallback_storyline(topic)
    selected = _selected_option(topic) or (topic.visual_options or build_visual_option_prompts(topic))[0]
    style = selected.get("style_type", "photorealistic")
    urls: list[str] = []
    for card in storyline[:5]:
        prompt = f"""
5장 카드뉴스 중 {card.get('card_no')}장차 이미지.
선택된 스타일: {selected.get('label')} / {style}
전체 주제: {topic.title}
카드 헤드라인: {card.get('headline')}
카드 본문: {card.get('body')}
시각 브리프: {card.get('visual_brief')}
첨부/참고/합성 자산: {_asset_context(topic)}
첫 장 시안의 룩앤필을 유지하되 이 카드 메시지에 맞는 새 장면으로 구성.
모바일 정사각형 1024x1024, 한국어 타이포그래피는 짧고 명확하게, 브랜드 광고 품질.
""".strip()
        result = await generate_image(prompt, size=size, model=model, quality=quality)
        urls.append(result.get("image_url", ""))
    return urls


def build_channel_variant(topic: ContentTopic, platform: str) -> dict[str, Any]:
    storyline = topic.card_storyline or []
    hooks = [card.get("headline", "") for card in storyline]
    hashtags = ["#SNS운영", "#카드뉴스", f"#{platform}"]
    if platform in ("instagram", "facebook"):
        body = "\n\n".join([f"{card.get('card_no')}. {card.get('headline')}\n{card.get('body')}" for card in storyline])
    elif platform == "threads":
        body = " → ".join([card.get("headline", "") for card in storyline]) + "\n\n자세한 내용은 카드뉴스에서 확인하세요."
    elif platform == "x":
        body = (hooks[0] if hooks else topic.title)[:220]
    else:
        body = "\n".join(hooks) + f"\n\n{topic.core_message or topic.brief or ''}"
    return {
        "platform": platform,
        "title": f"[{platform}] {topic.title}",
        "text": body,
        "hashtags": hashtags,
    }


async def create_channel_contents(topic: ContentTopic, db: AsyncSession, channels: list[str]) -> list[dict[str, Any]]:
    variants = []
    for platform in channels:
        variant = build_channel_variant(topic, platform)
        content = Content(
            client_id=topic.client_id,
            author_id=topic.author_id,
            topic_id=topic.id,
            target_platform=platform,
            variant_role="channel_variant",
            post_type="card_news" if platform in ("instagram", "facebook", "linkedin", "kakao", "blog") else "text",
            title=variant["title"],
            text=variant["text"],
            hashtags=variant["hashtags"],
            media_urls=topic.shared_media_urls or [],
            source_metadata={
                "source": "content_topic",
                "topic_id": str(topic.id),
                "card_storyline": topic.card_storyline,
                "selected_visual_option": topic.selected_visual_option,
            },
        )
        db.add(content)
        await db.flush()
        variant["content_id"] = content.id
        variants.append(variant)
    await db.commit()
    return variants
