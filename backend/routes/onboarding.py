import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.onboarding import ClientOnboarding
from models.client import Client
from models.user import User
from schemas.onboarding import (
    OnboardingStep1, OnboardingStep2, OnboardingStep3,
    OnboardingStep4, OnboardingResponse
)
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/clients/{client_id}/onboarding", tags=["onboarding"])


async def get_or_create_onboarding(
    client_id: uuid.UUID,
    db: AsyncSession
) -> ClientOnboarding:
    result = await db.execute(
        select(ClientOnboarding).where(ClientOnboarding.client_id == client_id)
    )
    onboarding = result.scalar_one_or_none()
    if not onboarding:
        onboarding = ClientOnboarding(client_id=client_id)
        db.add(onboarding)
        await db.commit()
        await db.refresh(onboarding)
    return onboarding


@router.get("", response_model=OnboardingResponse)
async def get_onboarding(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    onboarding = await get_or_create_onboarding(client_id, db)
    return onboarding


@router.post("/step1", response_model=OnboardingResponse)
async def step1_account_type(
    client_id: uuid.UUID,
    body: OnboardingStep1,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    onboarding = await get_or_create_onboarding(client_id, db)
    onboarding.account_type = body.account_type
    await db.commit()
    await db.refresh(onboarding)
    return onboarding


@router.post("/step2", response_model=OnboardingResponse)
async def step2_tone(
    client_id: uuid.UUID,
    body: OnboardingStep2,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    onboarding = await get_or_create_onboarding(client_id, db)
    onboarding.tones = body.tones
    onboarding.forbidden_words = body.forbidden_words
    onboarding.emoji_policy = body.emoji_policy
    onboarding.hashtag_policy = body.hashtag_policy
    onboarding.extra_notes = body.extra_notes
    await db.commit()
    await db.refresh(onboarding)
    return onboarding


@router.post("/step3", response_model=OnboardingResponse)
async def step3_channels(
    client_id: uuid.UUID,
    body: OnboardingStep3,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    onboarding = await get_or_create_onboarding(client_id, db)
    onboarding.selected_channels = body.selected_channels
    await db.commit()
    await db.refresh(onboarding)
    return onboarding


@router.post("/step4", response_model=OnboardingResponse)
async def step4_benchmark(
    client_id: uuid.UUID,
    body: OnboardingStep4,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    onboarding = await get_or_create_onboarding(client_id, db)
    onboarding.benchmark_channels = [b.model_dump() for b in body.benchmark_channels]
    await db.commit()
    await db.refresh(onboarding)
    return onboarding


@router.post("/complete", response_model=OnboardingResponse)
async def complete_onboarding(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user)
):
    onboarding = await get_or_create_onboarding(client_id, db)
    strategy = _generate_strategy(onboarding)
    onboarding.strategy_content = strategy
    onboarding.is_completed = True
    onboarding.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(onboarding)
    return onboarding


def _generate_strategy(onboarding: ClientOnboarding) -> str:
    account_type = onboarding.account_type or "브랜드"
    tones = ", ".join(onboarding.tones or ["친근/캐주얼"])
    channels = ", ".join(onboarding.selected_channels or [])
    return f"""# 채널 운영 전략서

## 계정 유형
{account_type}

## 톤앤매너
{tones}

## 운영 채널
{channels}

## 권장 콘텐츠 믹스
- 제품/서비스 소개: 30%
- 스토리텔링/공감: 40%
- 이벤트/참여 유도: 20%
- 정보형 콘텐츠: 10%

## 권장 발행 주기
주 4~5회 (화/목/토 집중)

## 해시태그 전략
정책: {onboarding.hashtag_policy}
이모지: {onboarding.emoji_policy}

## 금지 표현
{', '.join(onboarding.forbidden_words or []) or '없음'}

---
*AI 자동 생성 전략서 · 언제든 수정 가능*
"""
