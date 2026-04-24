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
from models.llm_provider_config import LLMProviderConfig
from models.llm_task_policy import LLMTaskPolicy
from middleware.auth import get_current_user
from services.runtime_settings import get_runtime_setting
from services.sns_publisher import SNSPublisher
from services.benchmark_collector_service import BenchmarkCollectorService
from services.sns_oauth import decrypt_token
from services.llm.router import DEFAULT_PROVIDER_ROWS, DEFAULT_TASK_POLICIES

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

PUBLISH_FAILURE_CATEGORIES = [
    ("missing_evidence", "증거 누락", ("platform_post_id/published_url",)),
    ("unsupported_platform", "미지원 채널", ("실제 발행 자동화를 지원하지 않습니다",)),
    ("token_expired", "토큰 만료", ("토큰이 만료되어 재인증이 필요합니다",)),
    ("token_missing", "토큰 없음", ("연결 레코드는 있으나 access token 없음",)),
    ("missing_channel", "채널/콘텐츠 누락", ("채널 연결을 찾을 수 없습니다", "채널 연결 ID가 필요합니다", "콘텐츠 또는 채널을 찾을 수 없습니다", "콘텐츠를 찾을 수 없습니다")),
    ("retrying", "재시도 중", ("예약 발행 재시도 중",)),
]


def _channel_has_access_token(channel: ChannelConnection | None) -> bool:
    if not channel or not channel.access_token:
        return False
    return bool(decrypt_token(channel.access_token))


def _classify_publish_error(error_message: str | None) -> tuple[str, str]:
    text = (error_message or "").strip()
    for key, label, needles in PUBLISH_FAILURE_CATEGORIES:
        if any(needle in text for needle in needles):
            return key, label
    return "other", "기타 오류"


def _count_failed_publish_category(contents: list[Content], category_key: str) -> int:
    return sum(1 for content in contents if _classify_publish_error(content.publish_error)[0] == category_key)


def _summarize_publishing_readiness(
    *,
    supported_connected_channels: int,
    supported_healthy_channels: int,
    unsupported_connected_channels: int,
    token_missing_channels: int,
    unknown_token_channels: int,
    suspicious_published_without_evidence: int,
    failed_publish_count: int,
    published_evidence_count: int,
) -> tuple[str, str]:
    if supported_connected_channels == 0:
        return "blocked", "실제 자동발행 가능한 지원 채널 연결이 아직 없습니다"
    if suspicious_published_without_evidence > 0:
        return (
            "warning",
            f"published 상태지만 증거가 없는 콘텐츠 {suspicious_published_without_evidence}건이 있어 성공 판정을 믿기 어렵습니다",
        )
    if failed_publish_count > 0:
        return "warning", f"최근 발행 실패 {failed_publish_count}건이 누적되어 먼저 실패 사유 정리가 필요합니다"
    if token_missing_channels > 0:
        return "warning", f"연결된 채널처럼 보이지만 access token이 없는 채널 {token_missing_channels}개가 있습니다"
    if unsupported_connected_channels > 0:
        return "warning", f"연결은 되어 있지만 자동발행 미지원 채널 {unsupported_connected_channels}개가 섞여 있습니다"
    if unknown_token_channels > 0:
        return "warning", f"토큰 만료시각을 모르는 채널 {unknown_token_channels}개가 있어 발행 준비 판정이 불완전합니다"
    if supported_healthy_channels == 0:
        return "warning", "지원 채널 연결은 있지만 현재 건강한 발행 채널이 없습니다"
    if published_evidence_count == 0:
        return "warning", "발행 가능한 채널은 있지만 아직 확인된 발행 증거가 없습니다"
    return "ready", "실제 발행 가능한 지원 채널과 발행 증거가 함께 확인됩니다"


def _summarize_benchmark_diagnostics(diagnostics: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=24)

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
    duplicate_source_rows = [row for row in active_rows if row.get("source_channel_duplicate_warning")]
    never_refreshed_rows = [row for row in active_rows if not row.get("last_refresh_at")]
    stale_refresh_rows = [
        row
        for row in active_rows
        if row.get("last_refresh_at")
        and isinstance(row.get("last_refresh_at"), datetime)
        and row["last_refresh_at"] < stale_cutoff
    ]

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
        or len(duplicate_source_rows) > 0
        or len(never_refreshed_rows) > 0
        or len(stale_refresh_rows) > 0
    )

    if blocked:
        status = "blocked"
        summary = "활성 벤치마킹 계정 또는 직접 실수집 가능한 계정이 아직 부족합니다"
    elif warning:
        status = "warning"
        if len(never_refreshed_rows) > 0 or len(stale_refresh_rows) > 0:
            summary = "실데이터 상태 외에도 새로고침 이력 부족/노후 계정이 있어 현재 운영 상태를 최신 정보로 보기 어렵습니다"
        else:
            summary = "실데이터와 fallback/누락/수동 확인 상태가 섞여 있어 운영자가 상태를 분리해서 봐야 합니다"
    else:
        status = "ready"
        summary = "직접 실데이터 기준으로 벤치마킹 계정 상태가 정돈되어 있습니다"

    return {
        "status": status,
        "summary": summary,
        "details": {
            "active_accounts": len(active_rows),
            "live_supported_accounts": len(live_supported_rows),
            "live_accounts": len(live_rows),
            "mixed_accounts": len(mixed_rows),
            "placeholder_only_accounts": len(placeholder_rows),
            "no_data_accounts": len(no_data_rows),
            "token_missing_accounts": len(token_missing_rows),
            "collector_error_accounts": len(collector_error_rows),
            "manual_required_accounts": len(manual_required_rows),
            "manual_supported_accounts": len(manual_supported_rows),
            "unimplemented_accounts": len(unimplemented_rows),
            "duplicate_source_accounts": len(duplicate_source_rows),
            "duplicate_source_connections": sum(int(row.get("source_channel_duplicate_count") or 0) for row in duplicate_source_rows),
            "never_refreshed_accounts": len(never_refreshed_rows),
            "stale_refresh_accounts": len(stale_refresh_rows),
            "inactive_accounts": max(len(diagnostics) - len(active_rows), 0),
            "live_post_count": sum(int(row.get("live_post_count") or 0) for row in active_rows),
            "placeholder_post_count": sum(int(row.get("placeholder_post_count") or 0) for row in active_rows),
            "actual_metric_posts": sum(int(row.get("actual_metric_count") or 0) for row in active_rows),
            "proxy_metric_posts": sum(int(row.get("proxy_metric_count") or 0) for row in active_rows),
        },
    }


def _runtime_provider_available(provider_name: str | None, *, openai_key_present: bool, claude_cli_available: bool) -> bool:
    if provider_name == "gpt":
        return openai_key_present
    if provider_name == "claude":
        return claude_cli_available
    return False


async def _summarize_ai_generation_readiness(
    db: AsyncSession,
    *,
    openai_key_present: bool,
    claude_cli_available: bool,
) -> dict:
    provider_result = await db.execute(select(LLMProviderConfig))
    provider_rows = list(provider_result.scalars().all())
    provider_index = {(row.provider_name, row.model_name): row for row in provider_rows}
    default_provider_index = {
        (row["provider_name"], row["model_name"]): row
        for row in DEFAULT_PROVIDER_ROWS
    }

    policy_result = await db.execute(
        select(LLMTaskPolicy)
        .where(LLMTaskPolicy.is_active == True)
        .order_by(LLMTaskPolicy.task_type)
    )
    policy_rows = list(policy_result.scalars().all())
    policies = [
        {
            "task_type": row.task_type,
            "primary_provider": row.primary_provider,
            "primary_model": row.primary_model,
            "fallback_provider": row.fallback_provider,
            "fallback_model": row.fallback_model,
            "fallback_enabled": row.fallback_enabled,
        }
        for row in policy_rows
    ] or [
        {
            "task_type": task_type,
            "primary_provider": config.get("primary_provider"),
            "primary_model": config.get("primary_model"),
            "fallback_provider": config.get("fallback_provider"),
            "fallback_model": config.get("fallback_model"),
            "fallback_enabled": True,
        }
        for task_type, config in DEFAULT_TASK_POLICIES.items()
    ]

    blocked_tasks: list[str] = []
    fallback_only_tasks: list[str] = []
    fallback_missing_tasks: list[str] = []
    missing_provider_config_tasks: list[str] = []
    inactive_provider_tasks: list[str] = []
    primary_routes: set[str] = set()
    fallback_routes: set[str] = set()
    primary_ready_tasks = 0
    fallback_ready_tasks = 0

    for policy in policies:
        primary_provider = policy.get("primary_provider")
        primary_model = policy.get("primary_model")
        fallback_provider = policy.get("fallback_provider")
        fallback_model = policy.get("fallback_model")
        fallback_enabled = bool(policy.get("fallback_enabled"))
        task_type = str(policy.get("task_type") or "unknown")

        primary_key = (primary_provider, primary_model)
        primary_cfg = provider_index.get(primary_key)
        primary_default_cfg = default_provider_index.get(primary_key)
        primary_config_present = primary_cfg is not None or primary_default_cfg is not None
        primary_config_active = bool(getattr(primary_cfg, "is_active", True)) if primary_cfg is not None else primary_default_cfg is not None
        primary_runtime_ready = _runtime_provider_available(
            primary_provider,
            openai_key_present=openai_key_present,
            claude_cli_available=claude_cli_available,
        )
        primary_ready = bool(primary_provider and primary_model and primary_config_present and primary_config_active and primary_runtime_ready)
        if primary_provider and primary_model:
            primary_routes.add(f"{primary_provider}:{primary_model}")
        if primary_ready:
            primary_ready_tasks += 1
        elif not primary_config_present:
            missing_provider_config_tasks.append(task_type)
        elif not primary_config_active:
            inactive_provider_tasks.append(task_type)

        fallback_ready = False
        fallback_config_problem = False
        if fallback_enabled and fallback_provider and fallback_model:
            fallback_key = (fallback_provider, fallback_model)
            fallback_cfg = provider_index.get(fallback_key)
            fallback_default_cfg = default_provider_index.get(fallback_key)
            fallback_config_present = fallback_cfg is not None or fallback_default_cfg is not None
            fallback_config_active = bool(getattr(fallback_cfg, "is_active", True)) if fallback_cfg is not None else fallback_default_cfg is not None
            fallback_runtime_ready = _runtime_provider_available(
                fallback_provider,
                openai_key_present=openai_key_present,
                claude_cli_available=claude_cli_available,
            )
            fallback_ready = bool(fallback_config_present and fallback_config_active and fallback_runtime_ready)
            fallback_routes.add(f"{fallback_provider}:{fallback_model}")
            if fallback_ready:
                fallback_ready_tasks += 1
            elif not fallback_config_present:
                missing_provider_config_tasks.append(task_type)
                fallback_config_problem = True
            elif not fallback_config_active:
                inactive_provider_tasks.append(task_type)
                fallback_config_problem = True
        elif fallback_enabled:
            fallback_config_problem = True

        if not primary_ready and fallback_ready:
            fallback_only_tasks.append(task_type)
        elif primary_ready and fallback_enabled and not fallback_ready:
            fallback_missing_tasks.append(task_type)

        if not primary_ready and not fallback_ready:
            blocked_tasks.append(task_type)
        elif fallback_config_problem and not primary_ready:
            blocked_tasks.append(task_type)

    active_task_count = len(policies)
    blocked_count = len(set(blocked_tasks))
    fallback_only_count = len(set(fallback_only_tasks))
    fallback_missing_count = len(set(fallback_missing_tasks))
    missing_provider_config_count = len(set(missing_provider_config_tasks))
    inactive_provider_count = len(set(inactive_provider_tasks))

    if active_task_count == 0:
        status = "blocked"
        summary = "활성 AI 작업 정책이 없어 생성 경로를 판단할 수 없습니다"
    elif blocked_count == active_task_count:
        status = "blocked"
        summary = "AI 생성 정책 전부가 현재 런타임 또는 설정 기준에서 막혀 있습니다"
    elif blocked_count > 0:
        status = "warning"
        summary = f"AI 생성 정책 {blocked_count}개가 현재 막혀 있어 일부 작업은 생성이 실패할 수 있습니다"
    elif fallback_only_count > 0:
        status = "warning"
        summary = f"AI 생성 정책 {fallback_only_count}개가 기본 경로 없이 fallback 경로에 의존합니다"
    elif fallback_missing_count > 0 or missing_provider_config_count > 0 or inactive_provider_count > 0:
        status = "warning"
        summary = "AI 생성은 가능하지만 fallback/설정 활성 상태가 불완전해 장애 시 취약합니다"
    else:
        status = "ready"
        summary = "활성 AI 생성 정책이 현재 설정과 런타임 기준에서 실행 가능합니다"

    return {
        "status": status,
        "summary": summary,
        "details": {
            "active_task_policies": active_task_count,
            "blocked_tasks": blocked_count,
            "fallback_only_tasks": fallback_only_count,
            "fallback_missing_tasks": fallback_missing_count,
            "missing_provider_config_tasks": missing_provider_config_count,
            "inactive_provider_tasks": inactive_provider_count,
            "primary_ready_tasks": primary_ready_tasks,
            "fallback_ready_tasks": fallback_ready_tasks,
            "openai_key_present": openai_key_present,
            "claude_cli_available": claude_cli_available,
            "primary_routes": ", ".join(sorted(primary_routes)) or "-",
            "fallback_routes": ", ".join(sorted(fallback_routes)) or "-",
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
    token_missing_channels = 0
    for channel in connected_channels:
        has_access_token = _channel_has_access_token(channel)
        if not has_access_token:
            token_missing_channels += 1
        if channel.token_expires_at and channel.token_expires_at > soon and has_access_token:
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
    ai_generation_summary = await _summarize_ai_generation_readiness(
        db,
        openai_key_present=openai_key_present,
        claude_cli_available=claude_cli_available,
    )

    oauth_status = "ready"
    oauth_summary = "Meta/외부 채널 연동 준비 상태"
    if not meta_app_id_present or not meta_app_secret_present:
        oauth_status = "blocked"
        oauth_summary = "Meta OAuth 환경변수가 비어 있어 시작 자체가 불가합니다"
    elif connected_count == 0:
        oauth_status = "warning"
        oauth_summary = "연동 키는 있지만 실제 연결된 채널이 아직 없습니다"
    elif reauth_required > 0:
        oauth_status = "warning"
        oauth_summary = f"재인증이 필요한 채널 {reauth_required}개가 있어 OAuth 운영 상태가 불안정합니다"
    elif token_missing_channels > 0:
        oauth_status = "warning"
        oauth_summary = f"연결은 되어 있지만 access token이 비어 있는 채널 {token_missing_channels}개가 있습니다"
    elif unknown_token_channels > 0:
        oauth_status = "warning"
        oauth_summary = f"토큰 만료시각을 모르는 채널 {unknown_token_channels}개가 있어 운영 판정이 불완전합니다"

    publishing_status, publishing_summary = _summarize_publishing_readiness(
        supported_connected_channels=supported_connected_count,
        supported_healthy_channels=supported_healthy_channels,
        unsupported_connected_channels=unsupported_connected_count,
        token_missing_channels=token_missing_channels,
        unknown_token_channels=unknown_token_channels,
        suspicious_published_without_evidence=suspicious_published_without_evidence,
        failed_publish_count=failed_publish_count,
        published_evidence_count=published_evidence_count,
    )

    items = [
        {
            "key": "ai_generation",
            "label": "AI 생성",
            "status": ai_generation_summary["status"],
            "summary": ai_generation_summary["summary"],
            "details": ai_generation_summary["details"],
        },
        {
            "key": "oauth_connections",
            "label": "OAuth 연동",
            "status": oauth_status,
            "summary": oauth_summary,
            "details": {
                "meta_app_id_present": meta_app_id_present,
                "meta_app_secret_present": meta_app_secret_present,
                "connected_channels": connected_count,
                "reauth_required": reauth_required,
                "token_missing_channels": token_missing_channels,
                "unknown_token_channels": unknown_token_channels,
                "supported_healthy_channels": supported_healthy_channels,
            },
        },
        {
            "key": "publishing",
            "label": "발행",
            "status": publishing_status,
            "summary": publishing_summary,
            "details": {
                "supported_connected_channels": supported_connected_count,
                "supported_healthy_channels": supported_healthy_channels,
                "unsupported_connected_channels": unsupported_connected_count,
                "token_missing_channels": token_missing_channels,
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
    failed_token_missing = _count_failed_publish_category(failed_contents, "token_missing")
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
            "failed_token_missing": failed_token_missing,
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
