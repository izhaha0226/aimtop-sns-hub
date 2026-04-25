from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from types import SimpleNamespace
import uuid

import httpx
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from models.action_language_profile import ActionLanguageProfile
from models.benchmark_account import BenchmarkAccount
from models.benchmark_post import BenchmarkPost
from models.channel import ChannelConnection
from models.client import Client
from models.industry_action_language_profile import IndustryActionLanguageProfile
from services.action_language_service import build_action_language_profile
from services.benchmark_scoring_service import calculate_benchmark_score
from services.sns_oauth import decrypt_token

HASHTAG_RE = re.compile(r"#\w+")
CTA_RE = re.compile(r"(저장|댓글|문의|신청|클릭|링크|팔로우|구독|DM)")

STATUS_LABELS = {
    "live_collected": "실데이터 수집",
    "live_collected_proxy_views": "실데이터 수집(조회수 프록시)",
    "manual_ingest_required": "수동 확인 필요",
    "collector_error": "수집 오류",
    "placeholder_fallback": "샘플 대체",
}

VIEW_METRIC_LABELS = {
    "actual": "실조회수",
    "proxy_from_public_metrics": "공개지표 기반 프록시 조회수",
    "proxy_from_like_comment": "좋아요/댓글 기반 프록시 조회수",
    "proxy_from_engagement": "참여도 기반 프록시 조회수",
}

DATA_SOURCE_LABELS = {
    "youtube_api_live": "YouTube 실데이터 API",
    "x_api_live": "X 실데이터 API",
    "instagram_business_discovery": "Instagram Business Discovery",
    "facebook_page_posts": "Facebook 페이지 포스트 API",
    "placeholder_benchmark_pipeline": "샘플 placeholder 데이터",
}

SUPPORT_LEVEL_LABELS = {
    "live": "실수집 지원",
    "manual": "수동 확인 필요",
    "unimplemented": "미구현",
}

LIVE_SUPPORTED_PLATFORMS = {"youtube", "x", "instagram", "facebook"}
MANUAL_SUPPORTED_PLATFORMS = {"threads"}


class BenchmarkCollectorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_accounts(self, client_id: uuid.UUID | None = None) -> list[BenchmarkAccount]:
        query = select(BenchmarkAccount).order_by(BenchmarkAccount.created_at.desc())
        if client_id:
            query = query.where(BenchmarkAccount.client_id == client_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_account(self, **kwargs) -> BenchmarkAccount:
        account = BenchmarkAccount(**kwargs)
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def update_account(self, account: BenchmarkAccount, **kwargs) -> BenchmarkAccount:
        for field, value in kwargs.items():
            if value is not None:
                setattr(account, field, value)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def get_account(self, account_id: uuid.UUID) -> BenchmarkAccount | None:
        result = await self.db.execute(select(BenchmarkAccount).where(BenchmarkAccount.id == account_id))
        return result.scalar_one_or_none()

    async def list_account_diagnostics(
        self,
        client_id: uuid.UUID,
        platform: str | None = None,
    ) -> list[dict]:
        platform_normalized = platform.lower() if platform else None
        accounts = await self.list_accounts(client_id)
        diagnostics: list[dict] = []
        for account in accounts:
            if platform_normalized and account.platform.lower() != platform_normalized:
                continue
            diagnostics.append(await self._build_account_diagnostic(account))
        return diagnostics

    async def refresh_account(self, account: BenchmarkAccount, top_k: int = 10, window_days: int = 30) -> dict:
        await self._clear_existing_posts(account.id)
        refresh_context = await self._build_source_channel_context(account.client_id, account.platform)

        try:
            posts, status_payload = await self._collect_live_posts(account, top_k=top_k, window_days=window_days)
        except Exception as e:
            status_payload = {
                "status": "collector_error",
                "message": f"실수집 중 오류가 발생했습니다: {e}",
                "live_supported": False,
                "platform": account.platform,
                **refresh_context,
            }
            if status_payload.get("source_channel_connected") and not status_payload.get("source_channel_has_token"):
                status_payload["source_channel_missing_reason"] = status_payload.get("source_channel_missing_reason") or "연결 레코드는 있으나 access token 없음"
            posts = []

        used_placeholder = False
        if not posts:
            status_payload = {
                **status_payload,
                "used_placeholder": False,
                "message": status_payload.get("message") or "실데이터를 적재하지 못했습니다. 샘플 데이터로 대체하지 않습니다.",
            }

        inserted = await self._insert_posts(account, posts, window_days=window_days) if posts else 0
        profile = await self.rebuild_action_language_profile(account.client_id, account.platform)
        client = await self._get_client(account.client_id)
        if client:
            await self.rebuild_industry_action_language_profile(
                industry_category=client.industry_category,
                platform=account.platform,
            )

        refreshed_at = datetime.now(timezone.utc)
        response_payload = {
            **status_payload,
            "status_label": STATUS_LABELS.get(status_payload.get("status", ""), status_payload.get("status")),
            "inserted": inserted,
            "profile_id": profile.id if profile else None,
            "profile_generated": bool(profile and profile.id),
            "used_placeholder": used_placeholder or bool(status_payload.get("used_placeholder")),
            "refreshed_at": refreshed_at,
        }
        await self._store_refresh_result(account, response_payload)
        return response_payload

    async def get_top_posts(self, client_id: uuid.UUID, platform: str, top_k: int = 10) -> list[BenchmarkPost]:
        platform_normalized = platform.lower()
        direct_posts = await self._query_top_posts_for_client(client_id, platform_normalized, top_k=top_k)
        if direct_posts:
            return direct_posts

        client = await self._get_client(client_id)
        if not client:
            return []
        return await self._query_top_posts_for_industry(
            industry_category=client.industry_category,
            platform=platform_normalized,
            top_k=top_k,
        )

    async def rebuild_action_language_profile(self, client_id: uuid.UUID, platform: str) -> ActionLanguageProfile | None:
        platform_normalized = platform.lower()
        posts = await self._query_top_posts_for_client(client_id, platform_normalized, top_k=20)
        if not posts:
            return None
        profile_data = build_action_language_profile(
            platform_normalized,
            [
                {
                    "content_text": p.content_text,
                    "hook_text": p.hook_text,
                    "cta_text": p.cta_text,
                }
                for p in posts
            ],
        )
        result = await self.db.execute(
            select(ActionLanguageProfile).where(
                ActionLanguageProfile.client_id == client_id,
                ActionLanguageProfile.platform == platform_normalized,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = ActionLanguageProfile(
                client_id=client_id,
                platform=platform_normalized,
                source_scope="manual_benchmark",
            )
            self.db.add(row)
        row.top_hooks_json = profile_data["top_hooks"]
        row.top_ctas_json = profile_data["top_ctas"]
        row.tone_patterns_json = profile_data["tone_patterns"]
        row.format_patterns_json = profile_data["format_patterns"]
        row.recommended_prompt_rules = profile_data["recommended_prompt_rules"]
        row.profile_version = (row.profile_version or 0) + 1
        await self.db.commit()
        await self.db.refresh(row)

        client = await self._get_client(client_id)
        return self._decorate_profile(
            row,
            source_scope="client_direct",
            industry_category=getattr(client, "industry_category", None),
            source_client_id=client_id,
            sample_count=len(posts),
        )

    async def get_action_language_profile(self, client_id: uuid.UUID, platform: str) -> ActionLanguageProfile | SimpleNamespace | None:
        platform_normalized = platform.lower()
        client = await self._get_client(client_id)
        if client is None:
            return None

        result = await self.db.execute(
            select(ActionLanguageProfile).where(
                ActionLanguageProfile.client_id == client_id,
                ActionLanguageProfile.platform == platform_normalized,
            )
        )
        direct_profile = result.scalar_one_or_none()
        direct_posts = await self._query_top_posts_for_client(client_id, platform_normalized, top_k=20)
        if direct_profile is not None and direct_posts:
            return self._decorate_profile(
                direct_profile,
                source_scope="client_direct",
                industry_category=client.industry_category,
                source_client_id=client_id,
                sample_count=len(direct_posts),
            )

        industry_profile = await self.get_industry_action_language_profile(
            industry_category=client.industry_category,
            platform=platform_normalized,
        )
        if industry_profile is None:
            industry_profile = await self.rebuild_industry_action_language_profile(
                industry_category=client.industry_category,
                platform=platform_normalized,
            )
        if industry_profile is None:
            return None

        return SimpleNamespace(
            id=getattr(industry_profile, "id", None),
            client_id=client_id,
            platform=platform_normalized,
            source_scope="industry_fallback",
            top_hooks_json=industry_profile.top_hooks_json or [],
            top_ctas_json=industry_profile.top_ctas_json or [],
            tone_patterns_json=industry_profile.tone_patterns_json or {},
            format_patterns_json=industry_profile.format_patterns_json or {},
            recommended_prompt_rules=industry_profile.recommended_prompt_rules or "",
            profile_version=industry_profile.profile_version or 0,
            updated_at=getattr(industry_profile, "updated_at", datetime.now(timezone.utc)),
            source_client_id=None,
            industry_category=client.industry_category,
            sample_count=getattr(industry_profile, "sample_count", 0),
        )

    async def get_industry_action_language_profile(
        self,
        industry_category: str,
        platform: str,
        format_type: str | None = None,
    ) -> IndustryActionLanguageProfile | None:
        result = await self.db.execute(
            select(IndustryActionLanguageProfile).where(
                IndustryActionLanguageProfile.industry_category == industry_category,
                IndustryActionLanguageProfile.platform == platform.lower(),
                IndustryActionLanguageProfile.format_type == format_type,
            )
        )
        return result.scalar_one_or_none()

    async def rebuild_industry_action_language_profile(
        self,
        industry_category: str,
        platform: str,
        format_type: str | None = None,
    ) -> IndustryActionLanguageProfile | None:
        platform_normalized = platform.lower()
        posts = await self._query_top_posts_for_industry(
            industry_category=industry_category,
            platform=platform_normalized,
            top_k=20,
        )
        if not posts:
            return None

        profile_data = build_action_language_profile(
            platform_normalized,
            [
                {
                    "content_text": p.content_text,
                    "hook_text": p.hook_text,
                    "cta_text": p.cta_text,
                }
                for p in posts
            ],
        )
        recommended_rules = (profile_data.get("recommended_prompt_rules") or "").strip()
        industry_rule = (
            f"이 프로필은 업종 공용 캐시({industry_category}) 기준입니다. 특정 경쟁사 문구를 복제하지 말고 구조만 참고할 것."
        )
        result = await self.db.execute(
            select(IndustryActionLanguageProfile).where(
                IndustryActionLanguageProfile.industry_category == industry_category,
                IndustryActionLanguageProfile.platform == platform_normalized,
                IndustryActionLanguageProfile.format_type == format_type,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = IndustryActionLanguageProfile(
                industry_category=industry_category,
                platform=platform_normalized,
                format_type=format_type,
                source_scope="industry_cache",
            )
            self.db.add(row)

        row.top_hooks_json = profile_data.get("top_hooks") or []
        row.top_ctas_json = profile_data.get("top_ctas") or []
        row.tone_patterns_json = profile_data.get("tone_patterns") or {}
        row.format_patterns_json = profile_data.get("format_patterns") or {}
        row.recommended_prompt_rules = f"{recommended_rules} {industry_rule}".strip()
        row.sample_count = len(posts)
        row.profile_version = (row.profile_version or 0) + 1
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def _get_client(self, client_id: uuid.UUID) -> Client | None:
        result = await self.db.execute(select(Client).where(Client.id == client_id, Client.is_deleted.is_(False)))
        return result.scalar_one_or_none()

    def _is_placeholder_post(self, post: BenchmarkPost) -> bool:
        raw_payload = post.raw_payload if isinstance(post.raw_payload, dict) else {}
        return str(raw_payload.get("source") or "") == "placeholder_benchmark_pipeline"

    def _filter_top_posts_for_reading(self, posts: list[BenchmarkPost], top_k: int) -> list[BenchmarkPost]:
        meaningful_posts = [post for post in posts if not self._is_placeholder_post(post)]
        return meaningful_posts[:top_k]

    async def _query_top_posts_for_client(self, client_id: uuid.UUID, platform: str, top_k: int) -> list[BenchmarkPost]:
        result = await self.db.execute(
            select(BenchmarkPost)
            .where(BenchmarkPost.client_id == client_id, BenchmarkPost.platform == platform)
            .order_by(desc(BenchmarkPost.benchmark_score), desc(BenchmarkPost.view_count))
            .limit(max(top_k * 5, 50))
        )
        return self._filter_top_posts_for_reading(list(result.scalars().all()), top_k)

    async def _query_top_posts_for_industry(self, industry_category: str, platform: str, top_k: int) -> list[BenchmarkPost]:
        result = await self.db.execute(
            select(BenchmarkPost)
            .join(Client, Client.id == BenchmarkPost.client_id)
            .where(
                BenchmarkPost.platform == platform,
                Client.industry_category == industry_category,
                Client.is_deleted.is_(False),
            )
            .order_by(desc(BenchmarkPost.benchmark_score), desc(BenchmarkPost.view_count))
            .limit(max(top_k * 5, 100))
        )
        return self._filter_top_posts_for_reading(list(result.scalars().all()), top_k)

    def _decorate_profile(
        self,
        profile: ActionLanguageProfile,
        *,
        source_scope: str,
        industry_category: str | None,
        source_client_id: uuid.UUID | None,
        sample_count: int,
    ) -> ActionLanguageProfile:
        profile.source_scope = source_scope
        setattr(profile, "industry_category", industry_category)
        setattr(profile, "source_client_id", source_client_id)
        setattr(profile, "sample_count", sample_count)
        return profile

    async def _clear_existing_posts(self, benchmark_account_id: uuid.UUID) -> None:
        existing = await self.db.execute(select(BenchmarkPost).where(BenchmarkPost.benchmark_account_id == benchmark_account_id))
        for row in existing.scalars().all():
            await self.db.delete(row)
        await self.db.flush()

    async def _build_account_diagnostic(self, account: BenchmarkAccount) -> dict:
        platform = account.platform.lower()
        support_level = self._get_support_level(platform)
        support_label = SUPPORT_LEVEL_LABELS[support_level]
        source_channels = await self._get_source_channels(account.client_id, platform)
        source_channel = self._pick_best_source_channel(source_channels)
        source_channel_has_token = self._channel_has_token(source_channel)
        source_channel_connection_count = len(source_channels)
        posts = await self._get_posts_for_account(account.id)
        post_summary = self._summarize_posts(posts)
        last_refresh = self._get_last_refresh_result(account)

        diagnostic = {
            "account_id": account.id,
            "client_id": account.client_id,
            "platform": platform,
            "handle": account.handle,
            "is_active": bool(account.is_active),
            "support_level": support_level,
            "support_label": support_label,
            "status": "manual_ingest_required",
            "status_label": STATUS_LABELS.get("manual_ingest_required"),
            "message": "운영 진단을 계산하지 못했습니다.",
            "live_supported": support_level == "live",
            "source_channel_connected": bool(source_channel),
            "source_channel_platform": platform,
            "source_channel_account_name": getattr(source_channel, "account_name", None) if source_channel else None,
            "source_channel_missing_reason": None,
            "source_channel_has_token": source_channel_has_token,
            "source_channel_connection_count": source_channel_connection_count,
            "source_channel_duplicate_count": max(source_channel_connection_count - 1, 0),
            "source_channel_duplicate_warning": source_channel_connection_count > 1,
            "last_refresh_status": last_refresh.get("status"),
            "last_refresh_status_label": last_refresh.get("status_label"),
            "last_refresh_message": last_refresh.get("message"),
            "last_refresh_inserted": int(last_refresh.get("inserted") or 0),
            "last_refresh_profile_id": last_refresh.get("profile_id"),
            "last_refresh_profile_generated": bool(last_refresh.get("profile_generated") or last_refresh.get("profile_id")),
            "last_refresh_used_placeholder": bool(last_refresh.get("used_placeholder")),
            "last_refresh_data_source": last_refresh.get("data_source"),
            "last_refresh_data_source_label": last_refresh.get("data_source_label"),
            "last_refresh_view_metric_type": last_refresh.get("view_metric_type"),
            "last_refresh_view_metric_label": last_refresh.get("view_metric_label"),
            "last_refresh_at": self._parse_refresh_datetime(last_refresh.get("refreshed_at")),
            **post_summary,
        }

        if not account.is_active:
            diagnostic["status"] = "inactive"
            diagnostic["status_label"] = "비활성"
            diagnostic["message"] = "이 계정은 비활성 상태입니다. 활성화 후에만 실수집/수동 점검 대상에 포함됩니다."
            return diagnostic

        if support_level == "unimplemented":
            diagnostic["message"] = f"{platform} 실수집기는 아직 구현되지 않았습니다."
            diagnostic["source_channel_missing_reason"] = f"{platform} 실수집기 미구현"
            return diagnostic

        if support_level == "manual":
            diagnostic["message"] = "현재 플랫폼은 자동 실수집이 아니라 운영자가 수동으로 확인해야 합니다."
            diagnostic["source_channel_missing_reason"] = "자동 실수집 미지원"
            return diagnostic

        if not source_channel:
            diagnostic["message"] = f"{platform} 실수집에는 연결된 소스 채널이 필요합니다."
            diagnostic["source_channel_missing_reason"] = f"연결된 {platform} 채널 토큰 없음"
            return diagnostic

        if not source_channel_has_token:
            diagnostic["message"] = "채널은 연결된 것처럼 보이지만 복호화 가능한 access token이 없습니다."
            diagnostic["source_channel_missing_reason"] = "연결 레코드는 있으나 access token 없음"
            return diagnostic

        if diagnostic["live_post_count"] == 0 and diagnostic["placeholder_post_count"] == 0 and diagnostic.get("last_refresh_status") == "collector_error":
            diagnostic["status"] = "collector_error"
            diagnostic["status_label"] = STATUS_LABELS.get("collector_error")
            diagnostic["message"] = diagnostic.get("last_refresh_message") or "최근 실수집 중 오류가 발생했습니다."
            diagnostic["source_channel_missing_reason"] = diagnostic.get("source_channel_missing_reason") or "최근 새로고침에서 collector 오류 발생"
            return diagnostic

        if diagnostic["live_post_count"] > 0 and diagnostic["placeholder_post_count"] > 0:
            diagnostic["status"] = "live_collected_mixed"
            diagnostic["status_label"] = "실데이터/샘플 혼재"
            diagnostic["message"] = "실데이터와 샘플 대체가 함께 있습니다. 운영 판단 시 분리해서 봐야 합니다."
            return diagnostic

        if diagnostic["live_post_count"] > 0:
            if diagnostic["actual_metric_count"] > 0 and diagnostic["proxy_metric_count"] == 0:
                diagnostic["status"] = "live_collected"
                diagnostic["status_label"] = STATUS_LABELS.get("live_collected")
                diagnostic["message"] = "실데이터가 적재되어 있습니다."
                diagnostic["view_metric_type"] = diagnostic["view_metric_type"] or "actual"
                diagnostic["view_metric_label"] = diagnostic["view_metric_label"] or VIEW_METRIC_LABELS.get("actual")
            else:
                diagnostic["status"] = "live_collected_proxy_views"
                diagnostic["status_label"] = STATUS_LABELS.get("live_collected_proxy_views")
                diagnostic["message"] = "실데이터는 적재되어 있으나 조회수는 프록시 지표 기준입니다."
            return diagnostic

        if diagnostic["placeholder_post_count"] > 0:
            diagnostic["status"] = "placeholder_fallback"
            diagnostic["status_label"] = STATUS_LABELS.get("placeholder_fallback")
            diagnostic["message"] = "현재 적재된 포스트는 샘플 대체 데이터입니다."
            return diagnostic

        diagnostic["status"] = "no_data_collected"
        diagnostic["status_label"] = "실데이터 없음"
        diagnostic["message"] = "연결은 가능하지만 아직 적재된 실데이터가 없습니다. 새로고침 후 collector 상태를 확인해야 합니다."
        return diagnostic

    async def _get_posts_for_account(self, benchmark_account_id: uuid.UUID) -> list[BenchmarkPost]:
        result = await self.db.execute(
            select(BenchmarkPost)
            .where(BenchmarkPost.benchmark_account_id == benchmark_account_id)
            .order_by(desc(BenchmarkPost.benchmark_score), desc(BenchmarkPost.view_count))
        )
        return list(result.scalars().all())

    def _summarize_posts(self, posts: list[BenchmarkPost]) -> dict:
        live_post_count = 0
        placeholder_post_count = 0
        actual_metric_count = 0
        proxy_metric_count = 0
        data_sources: list[str] = []
        view_metrics: list[str] = []

        for post in posts:
            raw_payload = post.raw_payload or {}
            source = str(raw_payload.get("source") or "")
            metric = str(raw_payload.get("view_metric") or "")
            if source == "placeholder_benchmark_pipeline":
                placeholder_post_count += 1
            elif source:
                live_post_count += 1
                data_sources.append(source)
            if metric == "actual":
                actual_metric_count += 1
                view_metrics.append(metric)
            elif metric.startswith("proxy_"):
                proxy_metric_count += 1
                view_metrics.append(metric)

        data_source = data_sources[0] if len(set(data_sources)) == 1 and data_sources else None
        view_metric_type = view_metrics[0] if len(set(view_metrics)) == 1 and view_metrics else None
        return {
            "live_post_count": live_post_count,
            "placeholder_post_count": placeholder_post_count,
            "actual_metric_count": actual_metric_count,
            "proxy_metric_count": proxy_metric_count,
            "total_post_count": len(posts),
            "data_source": data_source,
            "data_source_label": DATA_SOURCE_LABELS.get(data_source) if data_source else None,
            "view_metric_type": view_metric_type,
            "view_metric_label": VIEW_METRIC_LABELS.get(view_metric_type) if view_metric_type else None,
            "used_placeholder": placeholder_post_count > 0,
        }

    def _get_support_level(self, platform: str) -> str:
        if platform in LIVE_SUPPORTED_PLATFORMS:
            return "live"
        if platform in MANUAL_SUPPORTED_PLATFORMS:
            return "manual"
        return "unimplemented"

    def _get_last_refresh_result(self, account: BenchmarkAccount) -> dict:
        metadata = account.metadata_json or {}
        last_refresh = metadata.get("last_refresh")
        return last_refresh if isinstance(last_refresh, dict) else {}

    async def _build_source_channel_context(self, client_id: uuid.UUID, platform: str) -> dict:
        platform_normalized = platform.lower()
        source_channels = await self._get_source_channels(client_id, platform_normalized)
        source_channel = self._pick_best_source_channel(source_channels)
        source_channel_has_token = self._channel_has_token(source_channel)
        source_channel_connection_count = len(source_channels)
        return {
            "source_channel_connected": bool(source_channel),
            "source_channel_platform": platform_normalized,
            "source_channel_account_name": getattr(source_channel, "account_name", None) if source_channel else None,
            "source_channel_missing_reason": None if not source_channel or source_channel_has_token else "연결 레코드는 있으나 access token 없음",
            "source_channel_has_token": source_channel_has_token,
            "source_channel_connection_count": source_channel_connection_count,
            "source_channel_duplicate_count": max(source_channel_connection_count - 1, 0),
            "source_channel_duplicate_warning": source_channel_connection_count > 1,
        }

    def _parse_refresh_datetime(self, value: object) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    async def _store_refresh_result(self, account: BenchmarkAccount, payload: dict) -> None:
        metadata = dict(account.metadata_json or {})
        metadata["last_refresh"] = {
            "status": payload.get("status"),
            "status_label": payload.get("status_label"),
            "message": payload.get("message"),
            "inserted": int(payload.get("inserted") or 0),
            "profile_id": str(payload.get("profile_id")) if payload.get("profile_id") else None,
            "profile_generated": bool(payload.get("profile_generated") or payload.get("profile_id")),
            "used_placeholder": bool(payload.get("used_placeholder")),
            "data_source": payload.get("data_source"),
            "data_source_label": payload.get("data_source_label"),
            "view_metric_type": payload.get("view_metric_type"),
            "view_metric_label": payload.get("view_metric_label"),
            "source_channel_connected": bool(payload.get("source_channel_connected")),
            "source_channel_platform": payload.get("source_channel_platform"),
            "source_channel_account_name": payload.get("source_channel_account_name"),
            "source_channel_missing_reason": payload.get("source_channel_missing_reason"),
            "source_channel_has_token": bool(payload.get("source_channel_has_token")),
            "source_channel_connection_count": int(payload.get("source_channel_connection_count") or 0),
            "source_channel_duplicate_count": int(payload.get("source_channel_duplicate_count") or 0),
            "source_channel_duplicate_warning": bool(payload.get("source_channel_duplicate_warning")),
            "refreshed_at": payload.get("refreshed_at").isoformat() if isinstance(payload.get("refreshed_at"), datetime) else None,
        }
        account.metadata_json = metadata
        flag_modified(account, "metadata_json")
        await self.db.commit()
        await self.db.refresh(account)

    def _channel_has_token(self, source_channel: ChannelConnection | None) -> bool:
        if not source_channel or not source_channel.access_token:
            return False
        return bool(decrypt_token(source_channel.access_token))

    async def _insert_posts(self, account: BenchmarkAccount, posts: list[dict], window_days: int) -> int:
        inserted = 0
        for item in posts:
            post = BenchmarkPost(
                benchmark_account_id=account.id,
                client_id=account.client_id,
                platform=account.platform,
                external_post_id=item.get("external_post_id"),
                post_url=item.get("post_url"),
                content_text=item.get("content_text"),
                hook_text=item.get("hook_text"),
                cta_text=item.get("cta_text"),
                hashtags_json=item.get("hashtags_json") or [],
                format_type=item.get("format_type"),
                view_count=int(item.get("view_count") or 0),
                like_count=int(item.get("like_count") or 0),
                comment_count=int(item.get("comment_count") or 0),
                share_count=int(item.get("share_count") or 0),
                save_count=int(item.get("save_count") or 0),
                engagement_rate=float(item.get("engagement_rate") or 0),
                raw_payload=item.get("raw_payload") or {},
                published_at=item.get("published_at"),
            )
            post.benchmark_score = calculate_benchmark_score(post, window_days=window_days)
            self.db.add(post)
            inserted += 1
        await self.db.commit()
        return inserted

    async def _collect_live_posts(self, account: BenchmarkAccount, top_k: int, window_days: int) -> tuple[list[dict], dict]:
        platform = account.platform.lower()
        source_channels = await self._get_source_channels(account.client_id, platform)
        source_channel = self._pick_best_source_channel(source_channels)
        source_channel_account_name = getattr(source_channel, "account_name", None) if source_channel else None
        source_channel_has_token = self._channel_has_token(source_channel)
        source_channel_connection_count = len(source_channels)

        def manual_payload(message: str, missing_reason: str, *, connected: bool | None = None) -> dict:
            is_connected = bool(source_channel) if connected is None else connected
            return {
                "status": "manual_ingest_required",
                "message": message,
                "live_supported": False,
                "platform": platform,
                "source_channel_connected": is_connected,
                "source_channel_platform": platform,
                "source_channel_account_name": source_channel_account_name,
                "source_channel_missing_reason": missing_reason,
                "source_channel_has_token": source_channel_has_token,
                "source_channel_connection_count": source_channel_connection_count,
                "source_channel_duplicate_count": max(source_channel_connection_count - 1, 0),
                "source_channel_duplicate_warning": source_channel_connection_count > 1,
            }

        if platform == "youtube":
            if not source_channel:
                return [], manual_payload(
                    "YouTube 실수집에는 이 클라이언트의 연결된 YouTube 채널 토큰이 필요합니다.",
                    "연결된 YouTube 채널 토큰 없음",
                    connected=False,
                )
            if not source_channel_has_token:
                return [], manual_payload(
                    "YouTube 채널은 연결된 것처럼 보이지만 복호화 가능한 access token이 없습니다.",
                    "연결 레코드는 있으나 access token 없음",
                    connected=True,
                )
            posts = await self._collect_youtube_posts(account, source_channel, top_k=top_k, window_days=window_days)
            return posts, {
                "status": "live_collected",
                "message": "YouTube 실데이터 수집 완료",
                "live_supported": True,
                "platform": platform,
                "source_channel_connected": True,
                "source_channel_platform": platform,
                "source_channel_account_name": source_channel_account_name,
                "source_channel_has_token": True,
                "source_channel_connection_count": source_channel_connection_count,
                "source_channel_duplicate_count": max(source_channel_connection_count - 1, 0),
                "source_channel_duplicate_warning": source_channel_connection_count > 1,
                "data_source": "youtube_api_live",
                "data_source_label": DATA_SOURCE_LABELS["youtube_api_live"],
                "view_metric_type": "actual",
                "view_metric_label": VIEW_METRIC_LABELS["actual"],
            }
        if platform == "x":
            if not source_channel:
                return [], manual_payload(
                    "X 실수집에는 이 클라이언트의 연결된 X 채널 토큰이 필요합니다.",
                    "연결된 X 채널 토큰 없음",
                    connected=False,
                )
            if not source_channel_has_token:
                return [], manual_payload(
                    "X 채널은 연결된 것처럼 보이지만 복호화 가능한 access token이 없습니다.",
                    "연결 레코드는 있으나 access token 없음",
                    connected=True,
                )
            posts = await self._collect_x_posts(account, source_channel, top_k=top_k)
            return posts, {
                "status": "live_collected_proxy_views",
                "message": "X 공개 지표 기반 실수집 완료 (조회수는 공개 지표 프록시 추정)",
                "live_supported": True,
                "platform": platform,
                "source_channel_connected": True,
                "source_channel_platform": platform,
                "source_channel_account_name": source_channel_account_name,
                "source_channel_has_token": True,
                "source_channel_connection_count": source_channel_connection_count,
                "source_channel_duplicate_count": max(source_channel_connection_count - 1, 0),
                "source_channel_duplicate_warning": source_channel_connection_count > 1,
                "data_source": "x_api_live",
                "data_source_label": DATA_SOURCE_LABELS["x_api_live"],
                "view_metric_type": "proxy_from_public_metrics",
                "view_metric_label": VIEW_METRIC_LABELS["proxy_from_public_metrics"],
            }
        if platform == "instagram":
            if not source_channel:
                return [], manual_payload(
                    "Instagram 실수집에는 이 클라이언트의 연결된 Instagram 채널 토큰이 필요합니다.",
                    "연결된 Instagram 채널 토큰 없음",
                    connected=False,
                )
            if not source_channel_has_token:
                return [], manual_payload(
                    "Instagram 채널은 연결된 것처럼 보이지만 복호화 가능한 access token이 없습니다.",
                    "연결 레코드는 있으나 access token 없음",
                    connected=True,
                )
            posts = await self._collect_instagram_posts(account, source_channel, top_k=top_k)
            return posts, {
                "status": "live_collected",
                "message": "Instagram Business Discovery 기반 실데이터 수집 완료",
                "live_supported": True,
                "platform": platform,
                "source_channel_connected": True,
                "source_channel_platform": platform,
                "source_channel_account_name": source_channel_account_name,
                "source_channel_has_token": True,
                "source_channel_connection_count": source_channel_connection_count,
                "source_channel_duplicate_count": max(source_channel_connection_count - 1, 0),
                "source_channel_duplicate_warning": source_channel_connection_count > 1,
                "data_source": "instagram_business_discovery",
                "data_source_label": DATA_SOURCE_LABELS["instagram_business_discovery"],
                "view_metric_type": "proxy_from_like_comment",
                "view_metric_label": VIEW_METRIC_LABELS["proxy_from_like_comment"],
            }
        if platform == "facebook":
            if not source_channel:
                return [], manual_payload(
                    "Facebook 실수집에는 이 클라이언트의 연결된 Facebook 페이지 토큰이 필요합니다.",
                    "연결된 Facebook 페이지 토큰 없음",
                    connected=False,
                )
            if not source_channel_has_token:
                return [], manual_payload(
                    "Facebook 페이지는 연결된 것처럼 보이지만 복호화 가능한 access token이 없습니다.",
                    "연결 레코드는 있으나 access token 없음",
                    connected=True,
                )
            posts = await self._collect_facebook_posts(account, source_channel, top_k=top_k)
            return posts, {
                "status": "live_collected_proxy_views",
                "message": "Facebook 페이지 포스트 실데이터 수집 완료 (조회수는 참여도 프록시 추정)",
                "live_supported": True,
                "platform": platform,
                "source_channel_connected": True,
                "source_channel_platform": platform,
                "source_channel_account_name": source_channel_account_name,
                "source_channel_has_token": True,
                "source_channel_connection_count": source_channel_connection_count,
                "source_channel_duplicate_count": max(source_channel_connection_count - 1, 0),
                "source_channel_duplicate_warning": source_channel_connection_count > 1,
                "data_source": "facebook_page_posts",
                "data_source_label": DATA_SOURCE_LABELS["facebook_page_posts"],
                "view_metric_type": "proxy_from_engagement",
                "view_metric_label": VIEW_METRIC_LABELS["proxy_from_engagement"],
            }
        if platform == "threads":
            return [], manual_payload(
                "Threads는 공개 벤치마킹용 안정 API가 아직 부족해 수동 수집 대상으로 유지합니다.",
                "Threads 공개 벤치마킹 안정 API 미지원",
            )
        return [], manual_payload(
            f"{platform} 실수집기는 아직 미구현입니다.",
            f"{platform} 실수집기 미구현",
        )

    async def _get_source_channels(self, client_id: uuid.UUID, platform: str) -> list[ChannelConnection]:
        result = await self.db.execute(
            select(ChannelConnection)
            .where(
                ChannelConnection.client_id == client_id,
                ChannelConnection.channel_type == platform,
                ChannelConnection.is_connected.is_(True),
            )
            .order_by(ChannelConnection.updated_at.desc(), ChannelConnection.created_at.desc())
        )
        return list(result.scalars().all())

    def _pick_best_source_channel(self, channels: list[ChannelConnection]) -> ChannelConnection | None:
        if not channels:
            return None
        for channel in channels:
            if self._channel_has_token(channel):
                return channel
        return channels[0]

    async def _get_source_channel(self, client_id: uuid.UUID, platform: str) -> ChannelConnection | None:
        channels = await self._get_source_channels(client_id, platform)
        return self._pick_best_source_channel(channels)

    async def _collect_youtube_posts(
        self,
        account: BenchmarkAccount,
        source_channel: ChannelConnection,
        top_k: int,
        window_days: int,
    ) -> list[dict]:
        access_token = decrypt_token(source_channel.access_token or "")
        if not access_token:
            raise RuntimeError("YouTube source token is missing")

        channel_id = await self._resolve_youtube_channel_id(account.handle, access_token, account.metadata_json or {})
        if not channel_id:
            raise RuntimeError("YouTube 채널 ID를 찾지 못했습니다")

        published_after = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat().replace("+00:00", "Z")
        max_results = max(5, min(top_k * 2, 25))
        async with httpx.AsyncClient(timeout=30) as client:
            search_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "channelId": channel_id,
                    "order": "viewCount",
                    "type": "video",
                    "publishedAfter": published_after,
                    "maxResults": max_results,
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            search_resp.raise_for_status()
            items = search_resp.json().get("items", [])
            video_ids = [item.get("id", {}).get("videoId") for item in items if item.get("id", {}).get("videoId")]
            if not video_ids:
                return []

            videos_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids),
                    "maxResults": len(video_ids),
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            videos_resp.raise_for_status()
            videos = videos_resp.json().get("items", [])

        rows: list[dict] = []
        for video in videos:
            snippet = video.get("snippet", {})
            stats = video.get("statistics", {})
            title = (snippet.get("title") or "").strip()
            description = (snippet.get("description") or "").strip()
            text = f"{title}\n{description}".strip()
            rows.append(
                {
                    "external_post_id": video.get("id"),
                    "post_url": f"https://www.youtube.com/watch?v={video.get('id')}",
                    "content_text": text,
                    "hook_text": title,
                    "cta_text": self._extract_cta_text(text),
                    "hashtags_json": self._extract_hashtags(text),
                    "format_type": self._detect_youtube_format(snippet),
                    "view_count": int(stats.get("viewCount", 0) or 0),
                    "like_count": int(stats.get("likeCount", 0) or 0),
                    "comment_count": int(stats.get("commentCount", 0) or 0),
                    "share_count": 0,
                    "save_count": 0,
                    "engagement_rate": self._calc_engagement_rate(
                        views=int(stats.get("viewCount", 0) or 0),
                        likes=int(stats.get("likeCount", 0) or 0),
                        comments=int(stats.get("commentCount", 0) or 0),
                    ),
                    "published_at": self._parse_dt(snippet.get("publishedAt")),
                    "raw_payload": {
                        "source": "youtube_api_live",
                        "channel_id": channel_id,
                        "statistics": stats,
                        "view_metric": "actual",
                    },
                }
            )

        rows.sort(key=lambda item: (item.get("view_count", 0), item.get("engagement_rate", 0)), reverse=True)
        return rows[:top_k]

    async def _resolve_youtube_channel_id(self, handle: str, access_token: str, metadata: dict) -> str | None:
        if metadata.get("channel_id"):
            return str(metadata["channel_id"])
        normalized = handle.strip().lstrip("@")
        async with httpx.AsyncClient(timeout=30) as client:
            direct_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "id", "forHandle": normalized, "maxResults": 1},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if direct_resp.status_code == 200:
                items = direct_resp.json().get("items", [])
                if items:
                    return items[0].get("id")

            search_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={"part": "snippet", "q": normalized, "type": "channel", "maxResults": 1},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            search_resp.raise_for_status()
            items = search_resp.json().get("items", [])
            if items:
                return items[0].get("snippet", {}).get("channelId") or items[0].get("id", {}).get("channelId")
        return None

    async def _collect_x_posts(self, account: BenchmarkAccount, source_channel: ChannelConnection, top_k: int) -> list[dict]:
        access_token = decrypt_token(source_channel.access_token or "")
        if not access_token:
            raise RuntimeError("X source token is missing")

        username = account.handle.strip().lstrip("@")
        async with httpx.AsyncClient(timeout=30) as client:
            user_resp = await client.get(
                f"https://api.twitter.com/2/users/by/username/{username}",
                params={"user.fields": "public_metrics,description,created_at,verified"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_resp.raise_for_status()
            user = user_resp.json().get("data", {})
            user_id = user.get("id")
            if not user_id:
                return []

            tweets_resp = await client.get(
                f"https://api.twitter.com/2/users/{user_id}/tweets",
                params={
                    "exclude": "retweets,replies",
                    "max_results": max(5, min(top_k * 2, 20)),
                    "tweet.fields": "created_at,public_metrics,entities",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            tweets_resp.raise_for_status()
            tweets = tweets_resp.json().get("data", [])

        rows: list[dict] = []
        for tweet in tweets:
            text = (tweet.get("text") or "").strip()
            metrics = tweet.get("public_metrics", {})
            like_count = int(metrics.get("like_count", 0) or 0)
            comment_count = int(metrics.get("reply_count", 0) or 0)
            share_count = int(metrics.get("retweet_count", 0) or 0)
            quote_count = int(metrics.get("quote_count", 0) or 0)
            proxy_views = self._estimate_x_views(like_count, comment_count, share_count, quote_count)
            rows.append(
                {
                    "external_post_id": tweet.get("id"),
                    "post_url": f"https://x.com/{username}/status/{tweet.get('id')}",
                    "content_text": text,
                    "hook_text": self._first_line(text),
                    "cta_text": self._extract_cta_text(text),
                    "hashtags_json": [f"#{item.get('tag')}" for item in ((tweet.get("entities") or {}).get("hashtags") or []) if item.get("tag")],
                    "format_type": "text",
                    "view_count": proxy_views,
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "share_count": share_count + quote_count,
                    "save_count": 0,
                    "engagement_rate": self._calc_engagement_rate(
                        views=proxy_views,
                        likes=like_count,
                        comments=comment_count,
                        shares=share_count + quote_count,
                    ),
                    "published_at": self._parse_dt(tweet.get("created_at")),
                    "raw_payload": {
                        "source": "x_api_live",
                        "user_id": user_id,
                        "public_metrics": metrics,
                        "view_metric": "proxy_from_public_metrics",
                    },
                }
            )

        rows.sort(key=lambda item: (item.get("view_count", 0), item.get("engagement_rate", 0)), reverse=True)
        return rows[:top_k]

    async def _collect_instagram_posts(self, account: BenchmarkAccount, source_channel: ChannelConnection, top_k: int) -> list[dict]:
        access_token = decrypt_token(source_channel.access_token or "")
        if not access_token:
            raise RuntimeError("Instagram source token is missing")

        ig_user_id = self._resolve_instagram_user_id(source_channel)
        if not ig_user_id:
            raise RuntimeError("Instagram source account의 ig user id를 찾지 못했습니다")

        username = account.handle.strip().lstrip("@")
        fields = (
            f"business_discovery.username({username})"
            "{username,name,followers_count,media_count,media.limit(20)"
            "{id,caption,media_type,permalink,comments_count,like_count,timestamp}}"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://graph.facebook.com/v19.0/{ig_user_id}",
                params={"fields": fields, "access_token": access_token},
            )
            resp.raise_for_status()
            discovery = (resp.json().get("business_discovery") or {})
            media = (discovery.get("media") or {}).get("data", [])

        rows: list[dict] = []
        for item in media:
            caption = (item.get("caption") or "").strip()
            like_count = int(item.get("like_count", 0) or 0)
            comment_count = int(item.get("comments_count", 0) or 0)
            proxy_views = self._estimate_instagram_views(like_count, comment_count)
            rows.append(
                {
                    "external_post_id": item.get("id"),
                    "post_url": item.get("permalink"),
                    "content_text": caption,
                    "hook_text": self._first_line(caption),
                    "cta_text": self._extract_cta_text(caption),
                    "hashtags_json": self._extract_hashtags(caption),
                    "format_type": str(item.get("media_type") or "post").lower(),
                    "view_count": proxy_views,
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "share_count": 0,
                    "save_count": 0,
                    "engagement_rate": self._calc_engagement_rate(
                        views=proxy_views,
                        likes=like_count,
                        comments=comment_count,
                    ),
                    "published_at": self._parse_dt(item.get("timestamp")),
                    "raw_payload": {
                        "source": "instagram_business_discovery",
                        "target_username": username,
                        "view_metric": "proxy_from_like_comment",
                    },
                }
            )

        rows.sort(key=lambda item: (item.get("view_count", 0), item.get("engagement_rate", 0)), reverse=True)
        return rows[:top_k]

    async def _collect_facebook_posts(self, account: BenchmarkAccount, source_channel: ChannelConnection, top_k: int) -> list[dict]:
        access_token = decrypt_token(source_channel.access_token or "")
        if not access_token:
            raise RuntimeError("Facebook source token is missing")

        page_id = self._resolve_facebook_page_id(account, source_channel)
        if not page_id:
            raise RuntimeError("Facebook 페이지 ID가 필요합니다. benchmark account metadata_json.page_id 또는 숫자 handle을 사용해 주세요")

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://graph.facebook.com/v19.0/{page_id}/posts",
                params={
                    "fields": "id,message,created_time,permalink_url,shares,likes.summary(true),comments.summary(true)",
                    "limit": max(5, min(top_k * 2, 20)),
                    "access_token": access_token,
                },
            )
            resp.raise_for_status()
            items = resp.json().get("data", [])

        rows: list[dict] = []
        for item in items:
            text = (item.get("message") or "").strip()
            like_count = int(((item.get("likes") or {}).get("summary") or {}).get("total_count", 0) or 0)
            comment_count = int(((item.get("comments") or {}).get("summary") or {}).get("total_count", 0) or 0)
            share_count = int((item.get("shares") or {}).get("count", 0) or 0)
            proxy_views = self._estimate_facebook_views(like_count, comment_count, share_count)
            rows.append(
                {
                    "external_post_id": item.get("id"),
                    "post_url": item.get("permalink_url"),
                    "content_text": text,
                    "hook_text": self._first_line(text),
                    "cta_text": self._extract_cta_text(text),
                    "hashtags_json": self._extract_hashtags(text),
                    "format_type": "post",
                    "view_count": proxy_views,
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "share_count": share_count,
                    "save_count": 0,
                    "engagement_rate": self._calc_engagement_rate(
                        views=proxy_views,
                        likes=like_count,
                        comments=comment_count,
                        shares=share_count,
                    ),
                    "published_at": self._parse_dt(item.get("created_time")),
                    "raw_payload": {
                        "source": "facebook_page_posts",
                        "page_id": page_id,
                        "view_metric": "proxy_from_engagement",
                    },
                }
            )

        rows.sort(key=lambda item: (item.get("view_count", 0), item.get("engagement_rate", 0)), reverse=True)
        return rows[:top_k]

    def _build_placeholder_posts(self, account: BenchmarkAccount, top_k: int, window_days: int) -> list[dict]:
        now = datetime.now(timezone.utc)
        posts: list[dict] = []
        for idx in range(max(3, min(top_k, 10))):
            text = (
                f"{account.handle} benchmark sample {idx+1}\n"
                f"지금 확인해야 하는 핵심 포인트 {idx+1}가지\n"
                f"저장하고 댓글로 의견 남겨주세요 #{account.platform} #{idx+1}"
            )
            posts.append(
                {
                    "external_post_id": f"sample-{idx+1}",
                    "post_url": f"https://example.com/{account.platform}/{account.handle.strip('@')}/{idx+1}",
                    "content_text": text,
                    "hook_text": f"지금 확인해야 하는 핵심 포인트 {idx+1}가지",
                    "cta_text": "저장하고 댓글로 의견 남겨주세요",
                    "hashtags_json": [f"#{account.platform}", f"#{idx+1}"],
                    "format_type": "text",
                    "view_count": max(1000, 10000 - (idx * 700)),
                    "like_count": max(100, 1200 - (idx * 80)),
                    "comment_count": max(10, 150 - (idx * 12)),
                    "share_count": max(5, 80 - (idx * 6)),
                    "save_count": max(5, 60 - (idx * 4)),
                    "engagement_rate": max(0.5, 8.0 - (idx * 0.55)),
                    "published_at": now - timedelta(days=idx * 2),
                    "raw_payload": {"source": "placeholder_benchmark_pipeline", "live_supported": False, "window_days": window_days},
                }
            )
        return posts

    def _extract_hashtags(self, text: str) -> list[str]:
        return HASHTAG_RE.findall(text or "")[:20]

    def _first_line(self, text: str) -> str:
        return (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""

    def _extract_cta_text(self, text: str) -> str:
        if not text:
            return ""
        for line in reversed([line.strip() for line in text.splitlines() if line.strip()]):
            if CTA_RE.search(line):
                return line
        match = CTA_RE.search(text)
        return match.group(0) if match else ""

    def _detect_youtube_format(self, snippet: dict) -> str:
        title = (snippet.get("title") or "").lower()
        if "#shorts" in title:
            return "shorts"
        return "video"

    def _resolve_instagram_user_id(self, source_channel: ChannelConnection) -> str | None:
        extra = source_channel.extra_data or {}
        return extra.get("instagram_user_id") or extra.get("id") or source_channel.account_id

    def _resolve_facebook_page_id(self, account: BenchmarkAccount, source_channel: ChannelConnection) -> str | None:
        metadata = account.metadata_json or {}
        if metadata.get("page_id"):
            return str(metadata["page_id"])
        handle = account.handle.strip()
        if handle.isdigit():
            return handle

        pages = (source_channel.extra_data or {}).get("pages") or []
        normalized = handle.lstrip("@").lower()
        for page in pages:
            if str(page.get("id") or "") == normalized:
                return str(page.get("id"))
            if str(page.get("name") or "").strip().lower() == normalized:
                return str(page.get("id"))
        return None

    def _estimate_instagram_views(self, likes: int, comments: int) -> int:
        proxy = (likes * 22) + (comments * 38)
        return max(proxy, likes + comments)

    def _estimate_facebook_views(self, likes: int, comments: int, shares: int) -> int:
        proxy = (likes * 18) + (comments * 32) + (shares * 40)
        return max(proxy, likes + comments + shares)

    def _estimate_x_views(self, likes: int, comments: int, shares: int, quotes: int) -> int:
        proxy = (likes * 28) + (comments * 45) + (shares * 35) + (quotes * 40)
        return max(proxy, likes + comments + shares + quotes)

    def _calc_engagement_rate(self, views: int, likes: int, comments: int, shares: int = 0, saves: int = 0) -> float:
        if views <= 0:
            return 0.0
        return round(((likes + comments + shares + saves) / views) * 100, 4)

    def _parse_dt(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
