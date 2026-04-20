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
        f"각 세트는 다음 JSON 형식이야:\n"
        f'{{"concept_name": "...", "slides": ['
        f'{{"title": "...", "body": "...", "visual_direction": "..."}}]}}\n\n'
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
