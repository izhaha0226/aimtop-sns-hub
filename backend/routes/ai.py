"""
AI Routes - API endpoints for AI-powered content generation.
"""
from fastapi import APIRouter, HTTPException
import logging

from schemas.ai import (
    GenerateCopyRequest, GenerateCopyResponse,
    GenerateImageRequest, GenerateImageResponse,
    SuggestHashtagsRequest, SuggestHashtagsResponse,
    GenerateConceptSetsRequest, GenerateConceptSetsResponse,
    ChatEditRequest, ChatEditResponse,
    GenerateStrategyRequest, GenerateStrategyResponse,
)
from services.ai_service import (
    generate_copy,
    suggest_hashtags,
    generate_concept_sets,
    chat_edit,
    generate_strategy,
)
from services.image_service import generate_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


@router.post("/generate-copy", response_model=GenerateCopyResponse)
async def api_generate_copy(req: GenerateCopyRequest):
    """Generate platform-specific marketing copy."""
    try:
        result = await generate_copy(
            platform=req.platform,
            tone=req.tone,
            topic=req.topic,
            context=req.context,
            language=req.language,
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
        )
        return GenerateImageResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("generate_image failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"이미지 생성 실패: {str(e)}")


@router.post("/suggest-hashtags", response_model=SuggestHashtagsResponse)
async def api_suggest_hashtags(req: SuggestHashtagsRequest):
    """Suggest hashtags for a topic."""
    try:
        tags = await suggest_hashtags(
            topic=req.topic,
            platform=req.platform,
            count=req.count,
        )
        return SuggestHashtagsResponse(hashtags=tags)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except Exception as e:
        logger.error("suggest_hashtags failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"해시태그 추천 실패: {str(e)}")


@router.post("/concept-sets", response_model=GenerateConceptSetsResponse)
async def api_concept_sets(req: GenerateConceptSetsRequest):
    """Generate card-news concept sets."""
    try:
        sets = await generate_concept_sets(
            topic=req.topic,
            brand_info=req.brand_info,
            count=req.count,
        )
        return GenerateConceptSetsResponse(concept_sets=sets)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except Exception as e:
        logger.error("concept_sets failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"컨셉 세트 생성 실패: {str(e)}")


@router.post("/chat", response_model=ChatEditResponse)
async def api_chat_edit(req: ChatEditRequest):
    """Edit content via conversational instruction."""
    try:
        edited = await chat_edit(
            original_text=req.original_text,
            instruction=req.instruction,
        )
        return ChatEditResponse(edited_text=edited)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except Exception as e:
        logger.error("chat_edit failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"콘텐츠 수정 실패: {str(e)}")


@router.post("/generate-strategy", response_model=GenerateStrategyResponse)
async def api_generate_strategy(req: GenerateStrategyRequest):
    """Generate SNS operation strategy document."""
    try:
        result = await generate_strategy(
            client_info=req.client_info,
            period=req.period,
        )
        return GenerateStrategyResponse(**result)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except Exception as e:
        logger.error("generate_strategy failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"전략서 생성 실패: {str(e)}")
