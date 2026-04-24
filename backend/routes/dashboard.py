import shutil
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from models.content import Content
from models.approval import Approval
from models.channel import ChannelConnection
from models.user import User
from models.benchmark_account import BenchmarkAccount
from models.benchmark_post import BenchmarkPost
from middleware.auth import get_current_user
from services.runtime_settings import get_runtime_setting

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_result = await db.execute(
        select(func.count()).select_from(Content).where(Content.status != "trashed")
    )
    total_contents = total_result.scalar()

    pending_result = await db.execute(
        select(func.count()).select_from(Content).where(Content.status == "pending_approval")
    )
    pending_approvals = pending_result.scalar()

    published_result = await db.execute(
        select(func.count()).select_from(Content).where(
            Content.status == "published",
            Content.published_at >= today_start,
        )
    )
    published_today = published_result.scalar()

    scheduled_result = await db.execute(
        select(func.count()).select_from(Content).where(Content.status == "scheduled")
    )
    scheduled_count = scheduled_result.scalar()

    draft_result = await db.execute(
        select(func.count()).select_from(Content).where(Content.status == "draft")
    )
    draft_count = draft_result.scalar()

    return {
        "total_contents": total_contents,
        "pending_approvals": pending_approvals,
        "published_today": published_today,
        "scheduled": scheduled_count,
        "drafts": draft_count,
    }


@router.get("/channels-health")
async def get_channels_health(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=7)

    result = await db.execute(select(ChannelConnection).where(ChannelConnection.is_connected == True))
    channels = result.scalars().all()

    summary = {"healthy": 0, "expiring": 0, "reauth_required": 0, "unknown": 0}
    items = []
    for channel in channels:
        if not channel.token_expires_at:
            health = "unknown"
        elif channel.token_expires_at <= now:
            health = "reauth_required"
        elif channel.token_expires_at <= soon:
            health = "expiring"
        else:
            health = "healthy"
        summary[health] += 1
        items.append({
            "id": str(channel.id),
            "platform": channel.channel_type,
            "account_name": channel.account_name,
            "health": health,
            "token_expires_at": channel.token_expires_at.isoformat() if channel.token_expires_at else None,
        })

    return {"summary": summary, "items": items}


@router.get("/pipeline-readiness")
async def get_pipeline_readiness(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=7)

    connected_result = await db.execute(select(ChannelConnection).where(ChannelConnection.is_connected == True))
    connected_channels = connected_result.scalars().all()
    connected_count = len(connected_channels)
    healthy_channels = 0
    reauth_required = 0
    for channel in connected_channels:
        if channel.token_expires_at and channel.token_expires_at > soon:
            healthy_channels += 1
        elif channel.token_expires_at and channel.token_expires_at <= now:
            reauth_required += 1

    benchmark_account_count = (await db.execute(select(func.count()).select_from(BenchmarkAccount))).scalar() or 0
    benchmark_post_count = (await db.execute(select(func.count()).select_from(BenchmarkPost))).scalar() or 0
    published_evidence_count = (
        await db.execute(
            select(func.count()).select_from(Content).where(
                Content.status == "published",
                (Content.platform_post_id.isnot(None) | Content.published_url.isnot(None)),
            )
        )
    ).scalar() or 0
    suspicious_published_without_evidence = (
        await db.execute(
            select(func.count()).select_from(Content).where(
                Content.status == "published",
                Content.platform_post_id.is_(None),
                Content.published_url.is_(None),
            )
        )
    ).scalar() or 0
    failed_publish_count = (
        await db.execute(
            select(func.count()).select_from(Content).where(
                Content.status == "failed",
                Content.publish_error.isnot(None),
            )
        )
    ).scalar() or 0

    openai_key_present = bool(await get_runtime_setting("openai_api_key"))
    meta_app_id_present = bool(await get_runtime_setting("meta_app_id"))
    meta_app_secret_present = bool(await get_runtime_setting("meta_app_secret"))
    claude_cli_available = shutil.which("claude") is not None

    items = [
        {
            "key": "ai_generation",
            "label": "AI 생성",
            "status": "ready" if openai_key_present else "blocked",
            "summary": "GPT 기본 생성 엔진 준비 상태",
            "details": {
                "primary_provider": "gpt",
                "primary_model": "gpt-5.4",
                "fallback_provider": "claude",
                "fallback_model": "claude-opus-5.7",
                "openai_key_present": openai_key_present,
                "claude_cli_available": claude_cli_available,
            },
        },
        {
            "key": "oauth_connections",
            "label": "OAuth 연동",
            "status": "ready" if meta_app_id_present and meta_app_secret_present else "blocked",
            "summary": "Meta/외부 채널 연동 준비 상태",
            "details": {
                "meta_app_id_present": meta_app_id_present,
                "meta_app_secret_present": meta_app_secret_present,
                "connected_channels": connected_count,
                "reauth_required": reauth_required,
            },
        },
        {
            "key": "publishing",
            "label": "발행",
            "status": (
                "blocked"
                if connected_count == 0
                else "warning"
                if suspicious_published_without_evidence > 0 or failed_publish_count > 0 or healthy_channels == 0
                else "ready"
            ),
            "summary": "실발행 가능한 채널 상태와 증거 정합성",
            "details": {
                "connected_channels": connected_count,
                "healthy_channels": healthy_channels,
                "published_evidence_count": published_evidence_count,
                "suspicious_published_without_evidence": suspicious_published_without_evidence,
                "failed_publish_count": failed_publish_count,
            },
        },
        {
            "key": "benchmarking",
            "label": "벤치마킹",
            "status": "ready" if benchmark_post_count > 0 else ("warning" if benchmark_account_count > 0 else "blocked"),
            "summary": "벤치마킹 학습 데이터 적재 상태",
            "details": {
                "benchmark_accounts": benchmark_account_count,
                "benchmark_posts": benchmark_post_count,
            },
        },
    ]

    summary = {
        "ready": sum(1 for item in items if item["status"] == "ready"),
        "warning": sum(1 for item in items if item["status"] == "warning"),
        "blocked": sum(1 for item in items if item["status"] == "blocked"),
    }

    return {"summary": summary, "items": items}


@router.get("/publish-observability")
async def get_publish_observability(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    published_result = await db.execute(
        select(Content)
        .where(
            Content.status == "published",
            (Content.platform_post_id.isnot(None) | Content.published_url.isnot(None)),
        )
        .order_by(Content.published_at.desc().nullslast(), Content.updated_at.desc())
        .limit(10)
    )
    published_items = published_result.scalars().all()

    suspicious_result = await db.execute(
        select(Content)
        .where(
            Content.status == "published",
            Content.platform_post_id.is_(None),
            Content.published_url.is_(None),
        )
        .order_by(Content.published_at.desc().nullslast(), Content.updated_at.desc())
        .limit(10)
    )
    suspicious_items = suspicious_result.scalars().all()

    failed_result = await db.execute(
        select(Content)
        .where(
            Content.status == "failed",
            Content.publish_error.isnot(None),
        )
        .order_by(Content.updated_at.desc())
        .limit(10)
    )
    failed_items = failed_result.scalars().all()

    failed_missing_evidence = sum(
        1 for item in failed_items
        if item.publish_error and "platform_post_id/published_url" in item.publish_error
    )
    failed_unsupported_platform = sum(
        1 for item in failed_items
        if item.publish_error and "실제 발행 자동화를 지원하지 않습니다" in item.publish_error
    )

    return {
        "summary": {
            "published_with_evidence": len(published_items),
            "published_without_evidence": len(suspicious_items),
            "failed_with_error": len(failed_items),
            "failed_missing_evidence": failed_missing_evidence,
            "failed_unsupported_platform": failed_unsupported_platform,
        },
        "published_items": [
            {
                "id": str(item.id),
                "title": item.title,
                "platform_post_id": item.platform_post_id,
                "published_url": item.published_url,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "channel_connection_id": str(item.channel_connection_id) if item.channel_connection_id else None,
            }
            for item in published_items
        ],
        "suspicious_items": [
            {
                "id": str(item.id),
                "title": item.title,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "channel_connection_id": str(item.channel_connection_id) if item.channel_connection_id else None,
            }
            for item in suspicious_items
        ],
        "failed_items": [
            {
                "id": str(item.id),
                "title": item.title,
                "publish_error": item.publish_error,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "channel_connection_id": str(item.channel_connection_id) if item.channel_connection_id else None,
            }
            for item in failed_items
        ],
    }


@router.get("/recent-activity")
async def recent_activity(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    contents_result = await db.execute(
        select(Content)
        .where(Content.status != "trashed")
        .order_by(Content.updated_at.desc())
        .limit(10)
    )
    recent_contents = contents_result.scalars().all()

    approvals_result = await db.execute(
        select(Approval).order_by(Approval.created_at.desc()).limit(10)
    )
    recent_approvals = approvals_result.scalars().all()

    return {
        "recent_contents": [
            {
                "id": str(c.id),
                "title": c.title,
                "status": c.status,
                "post_type": c.post_type,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in recent_contents
        ],
        "recent_approvals": [
            {
                "id": str(a.id),
                "content_id": str(a.content_id),
                "action": a.action,
                "created_at": a.created_at.isoformat(),
            }
            for a in recent_approvals
        ],
    }


@router.get("/overview")
async def get_overview(
    client_id: uuid.UUID = Query(..., description="클라이언트 ID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """전체 계정 통합 대시보드."""
    from services.dashboard_service import DashboardService
    service = DashboardService(db)
    return await service.get_overview(client_id)


@router.get("/best-times/{account_id}")
async def get_best_times(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """AI 기반 최적 발행 시간 추천."""
    from services.dashboard_service import DashboardService
    from fastapi import HTTPException
    service = DashboardService(db)
    try:
        return await service.get_best_times(account_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
