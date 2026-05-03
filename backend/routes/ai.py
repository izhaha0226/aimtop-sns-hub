"""
AI Routes - API endpoints for AI-powered content generation.
"""
from fastapi import APIRouter, Depends, HTTPException
import logging
import re
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.ai import (
    GenerateCopyRequest, GenerateCopyResponse,
    GenerateImageRequest, GenerateImageResponse,
    SuggestHashtagsRequest, SuggestHashtagsResponse,
    GenerateConceptSetsRequest, GenerateConceptSetsResponse,
    ChatEditRequest, ChatEditResponse,
    GenerateStrategyRequest, GenerateStrategyResponse,
    GenerateOperationPlanRequest, GenerateOperationPlanResponse,
)
from services.ai_service import (
    generate_copy,
    suggest_hashtags,
    generate_concept_sets,
    chat_edit,
    generate_strategy,
    generate_operation_plan,
)
from services.benchmark_collector_service import BenchmarkCollectorService
from services.image_service import generate_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


def _benchmark_key(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(value or "").lower())


def _detect_hook_patterns(text: str) -> list[str]:
    value = str(text or "").strip()
    patterns: list[str] = []
    if not value:
        return patterns
    if "?" in value or any(token in value for token in ["왜", "어떻게", "무엇", "가능할까"]):
        patterns.append("질문형 훅")
    if re.search(r"\d|[0-9]+가지|TOP|top", value, re.I):
        patterns.append("숫자/리스트형 훅")
    if any(token in value for token in ["실패", "문제", "고민", "불편", "걱정"]):
        patterns.append("문제 제기형 훅")
    if any(token in value for token in ["혜택", "할인", "무료", "이벤트", "선착순"]):
        patterns.append("혜택/프로모션형 훅")
    if any(token in value for token in ["후기", "사례", "전후", "비포", "결과"]):
        patterns.append("사례/증거형 훅")
    return patterns or ["공감/정보형 훅"]


def _detect_cta_patterns(text: str) -> list[str]:
    value = str(text or "")
    patterns = []
    if any(token in value for token in ["저장", "save"]):
        patterns.append("저장 유도")
    if any(token in value for token in ["댓글", "comment"]):
        patterns.append("댓글/대화 유도")
    if any(token in value for token in ["문의", "상담", "DM", "디엠"]):
        patterns.append("상담/문의 유도")
    if any(token in value for token in ["링크", "클릭", "프로필"]):
        patterns.append("링크 클릭 유도")
    if any(token in value for token in ["구매", "예약", "신청"]):
        patterns.append("전환 행동 유도")
    return patterns


def _summarize_benchmark_posts(posts) -> dict:
    hook_counter: Counter[str] = Counter()
    cta_counter: Counter[str] = Counter()
    format_counter: Counter[str] = Counter()
    for post in posts:
        text = getattr(post, "hook_text", None) or getattr(post, "content_text", None) or ""
        for pattern in _detect_hook_patterns(text):
            hook_counter[pattern] += 1
        cta_text = getattr(post, "cta_text", None) or getattr(post, "content_text", None) or ""
        for pattern in _detect_cta_patterns(cta_text):
            cta_counter[pattern] += 1
        fmt = getattr(post, "format_type", None) or "일반 포스트"
        format_counter[str(fmt)] += 1
    hook_patterns = [name for name, _ in hook_counter.most_common(5)]
    cta_patterns = [name for name, _ in cta_counter.most_common(5)] or ["명시 CTA 약함 — 운영계획에서 CTA를 보강"]
    format_patterns = [name for name, _ in format_counter.most_common(5)] or ["수집 포맷 없음"]
    return {
        "hook_patterns": hook_patterns,
        "cta_patterns": cta_patterns,
        "format_patterns": format_patterns,
    }


async def _build_operation_benchmark_insights(
    db: AsyncSession,
    *,
    client_id,
    benchmark_brands: list[str],
    channels: list[str],
) -> list[dict]:
    if not client_id or not benchmark_brands:
        return []
    svc = BenchmarkCollectorService(db)
    accounts = await svc.list_accounts(client_id)
    channel_set = {str(channel or "").lower() for channel in channels if str(channel or "").strip()}
    brand_keys = {_benchmark_key(name): name for name in benchmark_brands if _benchmark_key(name)}
    diagnostics = await svc.list_account_diagnostics(client_id=client_id)
    diagnostics_by_account = {str(item.get("account_id")): item for item in diagnostics}
    insights: list[dict] = []
    matched_pairs: set[tuple[str, str]] = set()

    for account in accounts:
        platform = str(account.platform or "").lower()
        if channel_set and platform not in channel_set:
            continue
        handle_key = _benchmark_key(account.handle)
        matched_brand = None
        for key, original in brand_keys.items():
            if key and (key in handle_key or handle_key in key):
                matched_brand = original
                break
        if not matched_brand:
            continue

        diagnostic = diagnostics_by_account.get(str(account.id), {})
        refresh_status = None
        if diagnostic.get("live_supported") and diagnostic.get("source_channel_has_token") and getattr(account, "is_active", True):
            try:
                refresh_status = await svc.refresh_account(account, top_k=8, window_days=30)
            except Exception as exc:  # keep planner usable and honest
                refresh_status = {"status": "collector_error", "message": str(exc)}
        posts = await svc.get_top_posts(client_id, platform, top_k=8)
        summary = _summarize_benchmark_posts(posts)
        status = str((refresh_status or {}).get("status") or diagnostic.get("status") or "manual_or_pending")
        support_level = str(diagnostic.get("support_level") or "manual")
        evidence_count = len(posts)
        warnings = [
            "경쟁사 문구/슬로건/캠페인 논리는 복제 금지",
        ]
        if evidence_count == 0:
            warnings.append(diagnostic.get("source_channel_missing_reason") or "수집된 포스트 없음 — 수동 확인 필요")
        insights.append(
            {
                "brand": matched_brand,
                "channel": platform,
                "source_status": status,
                "support_level": support_level,
                "evidence_count": evidence_count,
                "hook_patterns": summary["hook_patterns"],
                "format_patterns": summary["format_patterns"],
                "cta_patterns": summary["cta_patterns"],
                "apply_points": [
                    "반응 포스트의 첫 문장 구조를 우리 브랜드 문제/혜택 언어로 재작성",
                    "반복 포맷은 주차별 카드뉴스·숏폼·검색형 콘텐츠로 변환",
                    "CTA 리듬은 저장/댓글/문의/링크 클릭 중 채널 목적에 맞춰 분산",
                ],
                "warnings": warnings,
            }
        )
        matched_pairs.add((matched_brand, platform))

    for brand in benchmark_brands:
        for channel in channel_set or {"manual"}:
            if (brand, channel) in matched_pairs:
                continue
            insights.append(
                {
                    "brand": brand,
                    "channel": channel,
                    "source_status": "manual_or_pending",
                    "support_level": "manual",
                    "evidence_count": 0,
                    "hook_patterns": [],
                    "format_patterns": [],
                    "cta_patterns": [],
                    "apply_points": ["등록된 벤치마킹 계정/수집 데이터가 없어 브랜드명은 전략 참고값으로만 사용"],
                    "warnings": ["자동 서칭 근거 없음 — 벤치마킹 계정 등록 또는 수동 자료 첨부 필요"],
                }
            )
    return insights[:20]


@router.post("/generate-copy", response_model=GenerateCopyResponse)
async def api_generate_copy(
    req: GenerateCopyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate platform-specific marketing copy."""
    try:
        benchmark_profile = None
        if req.benchmark and req.benchmark.client_id:
            svc = BenchmarkCollectorService(db)
            benchmark_profile_row = await svc.get_action_language_profile(
                req.benchmark.client_id,
                req.benchmark.platform or req.platform,
            )
            if benchmark_profile_row:
                benchmark_profile = {
                    "top_hooks": benchmark_profile_row.top_hooks_json or [],
                    "top_ctas": benchmark_profile_row.top_ctas_json or [],
                    "recommended_prompt_rules": benchmark_profile_row.recommended_prompt_rules or "",
                    "source_scope": getattr(benchmark_profile_row, "source_scope", "unknown"),
                    "industry_category": getattr(benchmark_profile_row, "industry_category", None),
                    "sample_count": getattr(benchmark_profile_row, "sample_count", 0),
                }
        result = await generate_copy(
            platform=req.platform,
            tone=req.tone,
            topic=req.topic,
            context=req.context,
            language=req.language,
            brand_name=req.brand_name,
            target_audience=req.target_audience,
            strategy_keywords=req.strategy_keywords,
            engine=req.engine.model_dump(exclude_none=True) if req.engine else None,
            benchmark_profile=benchmark_profile,
            db=db,
        )
        return GenerateCopyResponse(**result)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except Exception as e:
        logger.error("generate_copy failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"카피 생성 실패: {str(e)}")


@router.post("/generate-image", response_model=GenerateImageResponse)
async def api_generate_image(req: GenerateImageRequest):
    """Generate an image using Fal.ai."""
    try:
        result = await generate_image(
            prompt=req.prompt,
            size=req.size,
            model=req.model,
            quality=req.quality,
        )
        return GenerateImageResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("generate_image failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"이미지 생성 실패: {str(e)}")


@router.post("/suggest-hashtags", response_model=SuggestHashtagsResponse)
async def api_suggest_hashtags(
    req: SuggestHashtagsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Suggest hashtags for a topic."""
    try:
        tags = await suggest_hashtags(
            topic=req.topic,
            platform=req.platform,
            count=req.count,
            engine=req.engine.model_dump(exclude_none=True) if req.engine else None,
            db=db,
        )
        return SuggestHashtagsResponse(hashtags=tags)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except Exception as e:
        logger.error("suggest_hashtags failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"해시태그 추천 실패: {str(e)}")


@router.post("/concept-sets", response_model=GenerateConceptSetsResponse)
async def api_concept_sets(
    req: GenerateConceptSetsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate card-news concept sets."""
    try:
        sets = await generate_concept_sets(
            topic=req.topic,
            brand_info=req.brand_info,
            count=req.count,
            engine=req.engine.model_dump(exclude_none=True) if req.engine else None,
            db=db,
        )
        return GenerateConceptSetsResponse(concept_sets=sets)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except Exception as e:
        logger.error("concept_sets failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"컨셉 세트 생성 실패: {str(e)}")


@router.post("/chat", response_model=ChatEditResponse)
async def api_chat_edit(
    req: ChatEditRequest,
    db: AsyncSession = Depends(get_db),
):
    """Edit content via conversational instruction."""
    try:
        edited = await chat_edit(
            original_text=req.original_text,
            instruction=req.instruction,
            engine=req.engine.model_dump(exclude_none=True) if req.engine else None,
            db=db,
        )
        return ChatEditResponse(edited_text=edited)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except Exception as e:
        logger.error("chat_edit failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"콘텐츠 수정 실패: {str(e)}")


@router.post("/generate-strategy", response_model=GenerateStrategyResponse)
async def api_generate_strategy(
    req: GenerateStrategyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate SNS operation strategy document."""
    try:
        result = await generate_strategy(
            client_info=req.client_info,
            period=req.period,
            engine=req.engine.model_dump(exclude_none=True) if req.engine else None,
            db=db,
        )
        return GenerateStrategyResponse(**result)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except Exception as e:
        logger.error("generate_strategy failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"전략서 생성 실패: {str(e)}")


@router.post("/generate-operation-plan", response_model=GenerateOperationPlanResponse)
async def api_generate_operation_plan(
    req: GenerateOperationPlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate an approval-first monthly SNS operation plan."""
    try:
        benchmark_insights = await _build_operation_benchmark_insights(
            db,
            client_id=req.client_id,
            benchmark_brands=req.benchmark_brands,
            channels=req.channels,
        )
        result = await generate_operation_plan(
            brand_name=req.brand_name,
            product_summary=req.product_summary,
            target_audience=req.target_audience,
            goals=req.goals,
            channels=req.channels,
            benchmark_brands=req.benchmark_brands,
            benchmark_insights=benchmark_insights,
            month=req.month,
            season_context=req.season_context,
            budget_level=req.budget_level,
            notes=req.notes,
            engine=req.engine.model_dump(exclude_none=True) if req.engine else None,
            db=db,
        )
        return GenerateOperationPlanResponse(**result)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except Exception as e:
        logger.error("generate_operation_plan failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"운영계획 생성 실패: {str(e)}")
