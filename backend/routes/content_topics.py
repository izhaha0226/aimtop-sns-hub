import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from middleware.auth import get_current_user
from models.content_topic import ContentTopic
from models.user import User
from schemas.content_topic import (
    ChannelVariantResponse,
    ContentTopicCreate,
    ContentTopicListResponse,
    ContentTopicResponse,
    ContentTopicUpdate,
    GenerateCardImagesRequest,
    GenerateChannelVariantsRequest,
    GenerateStorylineRequest,
    GenerateVisualOptionsRequest,
    ReferenceAssetsRequest,
    SelectVisualOptionRequest,
)
from services.content_topic_service import (
    create_channel_contents,
    generate_card_images,
    generate_first_slide_options,
    generate_topic_storyline,
)

router = APIRouter(prefix="/api/v1/content-topics", tags=["content-topics"])


async def _get_topic_or_404(topic_id: uuid.UUID, db: AsyncSession) -> ContentTopic:
    result = await db.execute(select(ContentTopic).where(ContentTopic.id == topic_id, ContentTopic.status != "trashed"))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="콘텐츠 주제를 찾을 수 없습니다")
    return topic


@router.get("", response_model=ContentTopicListResponse)
async def list_content_topics(
    client_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = select(ContentTopic).where(ContentTopic.status != "trashed")
    if client_id:
        query = query.where(ContentTopic.client_id == client_id)
    if status:
        query = query.where(ContentTopic.status == status)
    query = query.order_by(ContentTopic.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": items, "total": len(items)}


@router.post("", response_model=ContentTopicResponse, status_code=201)
async def create_content_topic(
    body: ContentTopicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = body.model_dump()
    channels = data.pop("channels", None)
    metadata = data.get("source_metadata") or {}
    if channels:
        metadata["channels"] = channels
    topic = ContentTopic(**data, source_metadata=metadata, author_id=current_user.id)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


@router.get("/{topic_id}", response_model=ContentTopicResponse)
async def get_content_topic(
    topic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await _get_topic_or_404(topic_id, db)


@router.put("/{topic_id}", response_model=ContentTopicResponse)
async def update_content_topic(
    topic_id: uuid.UUID,
    body: ContentTopicUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    topic = await _get_topic_or_404(topic_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(topic, field, value)
    await db.commit()
    await db.refresh(topic)
    return topic


@router.delete("/{topic_id}", status_code=204)
async def delete_content_topic(
    topic_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    topic = await _get_topic_or_404(topic_id, db)
    topic.status = "trashed"
    await db.commit()


@router.post("/{topic_id}/reference-assets", response_model=ContentTopicResponse)
async def attach_reference_assets(
    topic_id: uuid.UUID,
    body: ReferenceAssetsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    topic = await _get_topic_or_404(topic_id, db)
    topic.reference_assets = [asset.model_dump() for asset in body.assets]
    await db.commit()
    await db.refresh(topic)
    return topic


@router.post("/{topic_id}/generate-storyline", response_model=ContentTopicResponse)
async def api_generate_storyline(
    topic_id: uuid.UUID,
    body: GenerateStorylineRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    topic = await _get_topic_or_404(topic_id, db)
    if topic.card_storyline and not body.force_regenerate:
        return topic
    topic.card_storyline = await generate_topic_storyline(topic, db, engine=body.engine)
    topic.status = "storyline_ready"
    await db.commit()
    await db.refresh(topic)
    return topic


@router.post("/{topic_id}/generate-visual-options", response_model=ContentTopicResponse)
async def api_generate_visual_options(
    topic_id: uuid.UUID,
    body: GenerateVisualOptionsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    topic = await _get_topic_or_404(topic_id, db)
    if not topic.card_storyline:
        topic.card_storyline = await generate_topic_storyline(topic, db, engine=body.engine)
    if topic.visual_options and not body.force_regenerate:
        return topic
    topic.visual_options = await generate_first_slide_options(topic)
    topic.status = "visual_options_ready"
    await db.commit()
    await db.refresh(topic)
    return topic


@router.post("/{topic_id}/select-visual-option", response_model=ContentTopicResponse)
async def api_select_visual_option(
    topic_id: uuid.UUID,
    body: SelectVisualOptionRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    topic = await _get_topic_or_404(topic_id, db)
    option_ids = {item.get("option_id") for item in topic.visual_options or []}
    if body.option_id not in option_ids:
        raise HTTPException(status_code=400, detail="선택 가능한 시안이 아닙니다")
    topic.selected_visual_option = body.option_id
    topic.status = "visual_option_selected"
    await db.commit()
    await db.refresh(topic)
    return topic


@router.post("/{topic_id}/generate-card-images", response_model=ContentTopicResponse)
async def api_generate_card_images(
    topic_id: uuid.UUID,
    body: GenerateCardImagesRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    topic = await _get_topic_or_404(topic_id, db)
    if topic.shared_media_urls and not body.force_regenerate:
        return topic
    if not topic.selected_visual_option:
        raise HTTPException(status_code=400, detail="먼저 첫 장 시안을 선택해야 합니다")
    topic.shared_media_urls = await generate_card_images(topic, size=body.size, model=body.model, quality=body.quality)
    topic.status = "card_images_ready"
    await db.commit()
    await db.refresh(topic)
    return topic


@router.post("/{topic_id}/generate-channel-variants", response_model=list[ChannelVariantResponse])
async def api_generate_channel_variants(
    topic_id: uuid.UUID,
    body: GenerateChannelVariantsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    topic = await _get_topic_or_404(topic_id, db)
    if not topic.card_storyline:
        raise HTTPException(status_code=400, detail="먼저 5장 카드뉴스 스토리라인을 생성해야 합니다")
    variants = await create_channel_contents(topic, db, body.channels) if body.create_contents else []
    return variants
