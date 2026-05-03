"""
AI Service - LLM router wrapper for SNS content generation.
Default path keeps Claude CLI, but Claude/GPT can now be selected via router.
"""
import asyncio
import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.llm.router import LLMRouter

logger = logging.getLogger(__name__)


async def call_claude(prompt: str, timeout: int = 60) -> str:
    """Call Claude CLI and return raw text output."""
    proc = await asyncio.create_subprocess_exec(
        "claude", "--print", "--max-turns", "1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=prompt.encode("utf-8")),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"Claude CLI timed out after {timeout}s")

    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8").strip() if stderr else "unknown error"
        logger.error("Claude CLI error (rc=%d): %s", proc.returncode, err_msg)
        raise RuntimeError(f"Claude CLI failed: {err_msg}")

    return stdout.decode("utf-8").strip()


def _parse_json_response(raw: str) -> dict | list:
    """Extract JSON from model response (handles markdown fences)."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


async def call_llm_text(
    task_type: str,
    prompt: str,
    engine: dict | None = None,
    timeout: int = 60,
    context: dict[str, Any] | None = None,
    db: AsyncSession | None = None,
) -> str:
    router = LLMRouter(db)
    result = await router.generate_text(
        task_type=task_type,
        prompt=prompt,
        context=context,
        override={**(engine or {}), "timeout": timeout},
    )
    return result.output_text


async def call_llm_json(
    task_type: str,
    prompt: str,
    engine: dict | None = None,
    timeout: int = 60,
    context: dict[str, Any] | None = None,
    db: AsyncSession | None = None,
) -> dict | list:
    router = LLMRouter(db)
    result = await router.generate_json(
        task_type=task_type,
        prompt=prompt,
        context=context,
        override={**(engine or {}), "timeout": timeout},
    )
    return result.parsed_json if result.parsed_json is not None else _parse_json_response(result.output_text)


async def generate_copy(
    platform: str,
    tone: str,
    topic: str,
    context: str = "",
    language: str = "ko",
    brand_name: str = "",
    target_audience: str = "",
    strategy_keywords: list[str] | None = None,
    engine: dict | None = None,
    benchmark_profile: dict | None = None,
    db: AsyncSession | None = None,
) -> dict:
    """Generate platform-specific copy. Returns {title, body, hashtags[], cta}."""
    from services.prompt_builder import build_copy_prompt

    prompt = build_copy_prompt(
        platform=platform,
        tone=tone,
        topic=topic,
        context=context,
        language=language,
        brand_name=brand_name,
        target_audience=target_audience,
        strategy_keywords=strategy_keywords,
        benchmark_profile=benchmark_profile,
    )
    try:
        return await call_llm_json("copy_generation", prompt, engine=engine, timeout=60, db=db)
    except json.JSONDecodeError:
        raw = await call_llm_text("copy_generation", prompt, engine=engine, timeout=60, db=db)
        logger.warning("Failed to parse JSON, returning raw text")
        return {"title": "", "body": raw, "hashtags": [], "cta": ""}


async def suggest_hashtags(
    topic: str,
    platform: str,
    count: int = 15,
    engine: dict | None = None,
    db: AsyncSession | None = None,
) -> list[str]:
    """Suggest hashtags for the given topic and platform."""
    prompt = (
        f"다음 주제에 대해 {platform} 플랫폼에 적합한 해시태그를 "
        f"정확히 {count}개 추천해줘.\n"
        f"주제: {topic}\n\n"
        f"JSON 배열로만 응답해. 예: [\"#해시태그1\", \"#해시태그2\"]"
    )
    try:
        result = await call_llm_json("copy_generation", prompt, engine=engine, timeout=60, db=db)
        if isinstance(result, list):
            return result[:count]
        return result.get("hashtags", [])[:count]
    except (json.JSONDecodeError, AttributeError):
        raw = await call_llm_text("copy_generation", prompt, engine=engine, timeout=60, db=db)
        tags = [w for w in raw.split() if w.startswith("#")]
        return tags[:count]


async def generate_concept_sets(
    topic: str,
    brand_info: str,
    count: int = 3,
    engine: dict | None = None,
    db: AsyncSession | None = None,
) -> list[dict]:
    """Generate card-news concept sets.
    Each set: {concept_name, slides: [{title, body, visual_direction}]}
    """
    prompt = (
        f"카드뉴스 컨셉을 {count}세트 만들어줘.\n"
        f"주제: {topic}\n"
        f"브랜드 정보: {brand_info}\n\n"
        "[HAICo 컨셉 생성 규칙]\n"
        "- 최종 카드뉴스 한 세트로 바로 수렴하지 말고, 내부적으로 먼저 서로 다른 방향을 충분히 발산할 것.\n"
        "- 각 컨셉은 worldview, 정보 구조, 설득 메커니즘이 달라야 한다.\n"
        "- 흔한 제목 바꾸기 수준이 아니라 narrative arc가 달라야 한다.\n"
        "- 가장 강한 방향만 선택해 세트로 완성하듯 생각하되, 출력은 요청된 세트 수만큼 서로 다른 컨셉 세트로 줄 것.\n"
        "- 각 슬라이드는 모바일에서 바로 읽히는 짧은 문장과 장면감 있는 visual_direction을 우선할 것.\n\n"
        "각 세트는 다음 JSON 형식이야:\n"
        '{"concept_name": "...", "slides": ['
        '{"title": "...", "body": "...", "visual_direction": "..."}}]}\n\n'
        f"JSON 배열로만 응답해. 총 {count}개의 세트를 배열로 반환."
    )
    try:
        result = await call_llm_json("copy_generation", prompt, engine=engine, timeout=180, db=db)
        if isinstance(result, list):
            return result[:count]
        return [result]
    except json.JSONDecodeError:
        raw = await call_llm_text("copy_generation", prompt, engine=engine, timeout=180, db=db)
        return [{"concept_name": "생성 실패", "slides": [], "raw": raw}]


async def chat_edit(
    original_text: str,
    instruction: str,
    engine: dict | None = None,
    db: AsyncSession | None = None,
) -> str:
    """Edit content based on conversational instruction."""
    prompt = (
        f"아래 원문을 수정 지시에 따라 수정해줘. 수정된 텍스트만 출력해.\n\n"
        f"[원문]\n{original_text}\n\n"
        f"[수정 지시]\n{instruction}"
    )
    return await call_llm_text("copy_generation", prompt, engine=engine, timeout=60, db=db)


async def generate_strategy(
    client_info: str,
    period: str = "monthly",
    engine: dict | None = None,
    db: AsyncSession | None = None,
) -> dict:
    """Generate SNS operation strategy document."""
    period_label = {"monthly": "월간", "weekly": "주간", "quarterly": "분기"}.get(
        period, period
    )
    prompt = (
        f"다음 클라이언트 정보를 바탕으로 {period_label} SNS 운영 전략서를 작성해줘.\n\n"
        f"클라이언트 정보:\n{client_info}\n\n"
        f"JSON 형식으로 응답해:\n"
        f'{{"period": "{period_label}", "summary": "...", '
        f'"goals": ["..."], "themes": [{{"week": 1, "theme": "...", '
        f'"keywords": ["..."], "content_ideas": ["..."]}}], '
        f'"kpi": {{"followers_target": 0, "engagement_rate": 0}}, '
        f'"notes": "..."}}'
    )
    try:
        return await call_llm_json("strategy", prompt, engine=engine, timeout=180, db=db)
    except json.JSONDecodeError:
        raw = await call_llm_text("strategy", prompt, engine=engine, timeout=180, db=db)
        return {"period": period_label, "summary": raw, "goals": [], "themes": [], "kpi": {}, "notes": ""}


async def generate_operation_plan(
    brand_name: str,
    product_summary: str,
    target_audience: str = "",
    goals: list[str] | None = None,
    channels: list[str] | None = None,
    benchmark_brands: list[str] | None = None,
    benchmark_insights: list[dict] | None = None,
    month: str | None = None,
    season_context: str = "",
    budget_level: str = "standard",
    notes: str = "",
    engine: dict | None = None,
    db: AsyncSession | None = None,
) -> dict:
    """Generate a monthly brand/channel operation plan with deterministic fallback."""
    from services.content_operation_planner import OperationPlanRequestData, build_fallback_operation_plan

    req = OperationPlanRequestData(
        brand_name=brand_name,
        product_summary=product_summary,
        target_audience=target_audience,
        goals=goals or [],
        channels=channels or [],
        benchmark_brands=benchmark_brands or [],
        benchmark_insights=benchmark_insights or [],
        month=month,
        season_context=season_context,
        budget_level=budget_level,
        notes=notes,
    )
    fallback = build_fallback_operation_plan(req)

    prompt = (
        "너는 SNS 운영 총괄 에이전트다. 운영계획을 바로 달력으로 만들지 말고 반드시 먼저 "
        "Supermarketing/AimTop 전략 레이어를 통과시킨 뒤 월간·주차별 계획을 만들어라.\n\n"
        "[Supermarketing 필수 사고 순서]\n"
        "1) Brief lock: product/offer, audience, channel, conversion goal, constraints를 고정한다.\n"
        "2) Direction divergence: 최소 3개 다른 마케팅 앵글을 내부적으로 발산한다.\n"
        "3) Bench-aware judgment: 벤치마킹은 hook shape, pacing, CTA rhythm만 참고하고 문구·슬로건·캠페인 논리 복제는 금지한다.\n"
        "4) Execution translation: 승리 앵글을 채널별 콘텐츠 역할, 월간 수량, 주차별 테마로 변환한다.\n"
        "5) Validation: 승인 전 외부 업로드 금지, 승인 후 CTR/저장/댓글/문의 전환으로 검증한다.\n\n"
        "반드시 supermarketing_strategy 배열에 위 전략 판단을 4~6개 bullet로 요약하고, "
        "weekly_plan은 이 전략 spine에서 파생되게 만들어라. benchmark_insights가 있으면 그 안의 "
        "hook_patterns/format_patterns/cta_patterns/apply_points를 우선 반영하되, 원문 문구를 복제하지 말고 구조만 변환한다. "
        "외부 실수집 근거가 없으면 benchmark_source_status는 manual_or_pending으로 둔다. "
        "응답은 JSON만 반환해라.\n\n"
        f"[브랜드]\n{brand_name}\n"
        f"[상품/서비스]\n{product_summary}\n"
        f"[타겟]\n{target_audience}\n"
        f"[목표]\n{goals or []}\n"
        f"[채널]\n{channels or []}\n"
        f"[벤치마킹]\n{benchmark_brands or []}\n"
        f"[벤치마킹 수집/분석 근거]\n{json.dumps(benchmark_insights or [], ensure_ascii=False)}\n"
        f"[월/시즌]\n{month or ''} / {season_context}\n"
        f"[추가 메모]\n{notes}\n\n"
        "반환 스키마 키는 baseline과 동일해야 하며 supermarketing_strategy를 유지/개선해야 한다.\n"
        f"[baseline]\n{json.dumps(fallback, ensure_ascii=False)}"
    )
    try:
        result = await call_llm_json("strategy", prompt, engine=engine, timeout=180, db=db)
        if isinstance(result, dict):
            merged = {**fallback, **result}
            merged["benchmark_source_status"] = str(merged.get("benchmark_source_status") or "manual_or_pending")
            return merged
    except Exception as exc:
        logger.warning("generate_operation_plan falling back to deterministic plan: %s", exc)
    return fallback
