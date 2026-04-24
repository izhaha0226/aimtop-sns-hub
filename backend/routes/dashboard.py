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
from services.sns_publisher import SNSPublisher
from services.benchmark_collector_service import BenchmarkCollectorService

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

PUBLISH_FAILURE_CATEGORIES = [
    ("missing_evidence", "증거 누락", ("platform_post_id/published_url",)),
    ("unsupported_platform", "미지원 채널", ("실제 발행 자동화를 지원하지 않습니다",)),
    ("token_expired", "토큰 만료", ("토큰이 만료되어 재인증이 필요합니다",)),
    ("missing_channel", "채널/콘텐츠 누락", ("채널 연결을 찾을 수 없습니다", "채널 연결 ID가 필요합니다", "콘텐츠 또는 채널을 찾을 수 없습니다", "콘텐츠를 찾을 수 없습니다")),
    ("retrying", "재시도 중", ("예약 발행 재시도 중",)),
]


def _classify_publish_error(error_message: str | None) -> tuple[str, str]:
    text = (error_message or "").strip()
    for key, label, needles in PUBLISH_FAILURE_CATEGORIES:
        if any(needle in text for needle in needles):
            return key, label
    return "other", "기타 오류"


def _count_failed_publish_category(contents: list[Content], category_key: str) -> int:
    return sum(1 for content in contents if _classify_publish_error(content.publish_error)[0] == category_key)


def _summarize_benchmark_diagnostics(diagnostics: list[dict]) -> dict:
    active_rows = [row for row in diagnostics if row.get("is_active")]
    live_rows = [row for row in active_rows if row.get("status") in {"live_collected", "live_collected_proxy_views"}]
    mixed_rows = [row for row in active_rows if row.get("status") == "live_collected_mixed"]
    placeholder_rows = [row for row in active_rows if row.get("status") == "placeholder_fallback"]
    no_data_rows = [row for row in active_rows if row.get("status") == "no_data_collected"]
    collector_error_rows = [row for row in active_rows if row.get("status") == "collector_error"]
    manual_required_rows = [row for row in active_rows if row.get("status") == "manual_ingest_required"]
    token_missing_rows = [
        row
        for row in active_rows
        if row.get("source_channel_connected") and not row.get("source_channel_has_token")
    ]
    manual_supported_rows = [row for row in active_rows if row.get("support_level") == "manual"]
    unimplemented_rows = [row for row in active_rows if row.get("support_level") == "unimplemented"]
    live_supported_rows = [row for row in active_rows if row.get("support_level") == "live"]

    blocked = len(active_rows) == 0 or (len(live_supported_rows) == 0 and len(live_rows) == 0 and len(mixed_rows) == 0)
    warning = (
        len(mixed_rows) > 0
        or len(placeholder_rows) > 0
        or len(no_data_rows) > 0
        or len(collector_error_rows) > 0
        or len(manual_required_rows) > 0
        or len(token_missing_rows) > 0
        or len(manual_supported_rows) > 0
        or len(unimplemented_rows) > 0
    )

    if blocked:
        status = "blocked"
        summary = "활성 벤치마킹 계정 또는 직접 실수집 가능한 계정이 아직 부족합니다"
    elif warning:
        status = "warning"
        summary = "실데이터와 fallback/누락/수동 확인 상태가 섞여 있어 운영자가 상태를 분리해서 봐야 합니다"
    else:
        status = "ready"
        summary = "직접 실데이터 기준으로 벤치마킹 계정 상태가 정돈되어 있습니다"

    return {
        "status": status,
        "summary": summary,
        "details": {
            "active_accounts": len(active_rows),
            "live_accounts": len(live_rows),
            "mixed_accounts": len(mixed_rows),
            "placeholder_only_accounts": len(placeholder_rows),
            "no_data_accounts": len(no_data_rows),
            "token_missing_accounts": len(token_missing_rows),
            "collector_error_accounts": len(collector_error_rows),
            "manual_required_accounts": len(manual_required_rows),
            "manual_supported_accounts": len(manual_supported_rows),
            "unimplemented_accounts": len(unimplemented_rows),
            "inactive_accounts": max(len(diagnostics) - len(active_rows), 0),
            "live_post_count": sum(int(row.get("live_post_count") or 0) for row in active_rows),
            "placeholder_post_count": sum(int(row.get("placeholder_post_count") or 0) for row in active_rows),
        },
    }


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
    supported_channels = [channel for channel in connected_channels if SNSPublisher.is_supported_platform(channel.channel_type)]
    supported_connected_count = len(supported_channels)
    unsupported_connected_count = connected_count - supported_connected_count
    healthy_channels = 0
    supported_healthy_channels = 0
    reauth_required = 0
    unknown_token_channels = 0
    for channel in connected_channels:
        if channel.token_expires_at and channel.token_expires_at > soon:
            healthy_channels += 1
            if SNSPublisher.is_supported_platform(channel.channel_type):
                supported_healthy_channels += 1
        elif channel.token_expires_at and channel.token_expires_at <= now:
            reauth_required += 1
        elif not channel.token_expires_at:
            unknown_token_channels += 1

    benchmark_account_count = (await db.execute(select(func.count()).select_from(BenchmarkAccount))).scalar() or 0
    benchmark_post_count = (await db.execute(select(func.count()).select_from(BenchmarkPost))).scalar() or 0
    benchmark_accounts_result = await db.execute(select(BenchmarkAccount))
    benchmark_accounts = list(benchmark_accounts_result.scalars().all())
    benchmark_service = BenchmarkCollectorService(db)
    benchmark_diagnostics = [
        await benchmark_service._build_account_diagnostic(account)
        for account in benchmark_accounts
    ]
    benchmark_summary = _summarize_benchmark_diagnostics(benchmark_diagnostics)
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
                if supported_connected_count == 0
                else "warning"
                if (
                    unsupported_connected_count > 0
                    or unknown_token_channels > 0
                    or suspicious_published_without_evidence > 0
                    or failed_publish_count > 0
                    or supported_healthy_channels == 0
                )
                else "ready"
            ),
            "summary": "실발행 가능한 채널 상태와 증거 정합성",
            "details": {
                "supported_connected_channels": supported_connected_count,
                "supported_healthy_channels": supported_healthy_channels,
                "unsupported_connected_channels": unsupported_connected_count,
                "unknown_token_channels": unknown_token_channels,
                "published_evidence_count": published_evidence_count,
                "suspicious_published_without_evidence": suspicious_published_without_evidence,
                "failed_publish_count": failed_publish_count,
            },
        },
        {
            "key": "benchmarking",
            "label": "벤치마킹",
            "status": benchmark_summary["status"],
            "summary": benchmark_summary["summary"],
            "details": {
                **benchmark_summary["details"],
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
    published_with_evidence = (
        await db.execute(
            select(func.count()).select_from(Content).where(
                Content.status == "published",
                (Content.platform_post_id.isnot(None) | Content.published_url.isnot(None)),
            )
        )
    ).scalar() or 0
    published_without_evidence = (
        await db.execute(
            select(func.count()).select_from(Content).where(
                Content.status == "published",
                Content.platform_post_id.is_(None),
                Content.published_url.is_(None),
            )
        )
    ).scalar() or 0
    failed_with_error = (
        await db.execute(
            select(func.count()).select_from(Content).where(
                Content.status == "failed",
                Content.publish_error.isnot(None),
            )
        )
    ).scalar() or 0

    failed_contents_result = await db.execute(
        select(Content)
        .where(
            Content.status == "failed",
            Content.publish_error.isnot(None),
        )
    )
    failed_contents = list(failed_contents_result.scalars().all())
    failed_missing_evidence = _count_failed_publish_category(failed_contents, "missing_evidence")
    failed_unsupported_platform = _count_failed_publish_category(failed_contents, "unsupported_platform")
    failed_token_expired = _count_failed_publish_category(failed_contents, "token_expired")
    failed_missing_channel = _count_failed_publish_category(failed_contents, "missing_channel")
    failed_retrying = _count_failed_publish_category(failed_contents, "retrying")
    failed_other = _count_failed_publish_category(failed_contents, "other")

    published_result = await db.execute(
        select(Content, ChannelConnection)
        .outerjoin(ChannelConnection, Content.channel_connection_id == ChannelConnection.id)
        .where(
            Content.status == "published",
            (Content.platform_post_id.isnot(None) | Content.published_url.isnot(None)),
        )
        .order_by(Content.published_at.desc().nullslast(), Content.updated_at.desc())
        .limit(10)
    )
    published_items = published_result.all()

    suspicious_result = await db.execute(
        select(Content, ChannelConnection)
        .outerjoin(ChannelConnection, Content.channel_connection_id == ChannelConnection.id)
        .where(
            Content.status == "published",
            Content.platform_post_id.is_(None),
            Content.published_url.is_(None),
        )
        .order_by(Content.published_at.desc().nullslast(), Content.updated_at.desc())
        .limit(10)
    )
    suspicious_items = suspicious_result.all()

    failed_result = await db.execute(
        select(Content, ChannelConnection)
        .outerjoin(ChannelConnection, Content.channel_connection_id == ChannelConnection.id)
        .where(
            Content.status == "failed",
            Content.publish_error.isnot(None),
        )
        .order_by(Content.updated_at.desc())
        .limit(10)
    )
    failed_items = failed_result.all()

    return {
        "summary": {
            "published_with_evidence": published_with_evidence,
            "published_without_evidence": published_without_evidence,
            "failed_with_error": failed_with_error,
            "failed_missing_evidence": failed_missing_evidence,
            "failed_unsupported_platform": failed_unsupported_platform,
            "failed_token_expired": failed_token_expired,
            "failed_missing_channel": failed_missing_channel,
            "failed_retrying": failed_retrying,
            "failed_other": failed_other,
        },
        "published_items": [
            {
                "id": str(item.id),
                "title": item.title,
                "platform_post_id": item.platform_post_id,
                "published_url": item.published_url,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "channel_connection_id": str(item.channel_connection_id) if item.channel_connection_id else None,
                "channel_type": channel.channel_type if channel else None,
                "account_name": channel.account_name if channel else None,
            }
            for item, channel in published_items
        ],
        "suspicious_items": [
            {
                "id": str(item.id),
                "title": item.title,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "channel_connection_id": str(item.channel_connection_id) if item.channel_connection_id else None,
                "channel_type": channel.channel_type if channel else None,
                "account_name": channel.account_name if channel else None,
            }
            for item, channel in suspicious_items
        ],
        "failed_items": [
            {
                "id": str(item.id),
                "title": item.title,
                "publish_error": item.publish_error,
                "failure_category": _classify_publish_error(item.publish_error)[0],
                "failure_label": _classify_publish_error(item.publish_error)[1],
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "channel_connection_id": str(item.channel_connection_id) if item.channel_connection_id else None,
                "channel_type": channel.channel_type if channel else None,
                "account_name": channel.account_name if channel else None,
            }
            for item, channel in failed_items
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
