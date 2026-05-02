"""
AI Routes - API endpoints for AI-powered content generation.
"""
from fastapi import APIRouter, Depends, HTTPException
import logging

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
        result = await generate_operation_plan(
            brand_name=req.brand_name,
            product_summary=req.product_summary,
            target_audience=req.target_audience,
            goals=req.goals,
            channels=req.channels,
            benchmark_brands=req.benchmark_brands,
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
