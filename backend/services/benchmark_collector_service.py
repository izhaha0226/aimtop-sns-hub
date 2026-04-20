from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.action_language_profile import ActionLanguageProfile
from models.benchmark_account import BenchmarkAccount
from models.benchmark_post import BenchmarkPost
from services.action_language_service import build_action_language_profile
from services.benchmark_scoring_service import calculate_benchmark_score


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

    async def refresh_account(self, account: BenchmarkAccount, top_k: int = 10, window_days: int = 30) -> dict:
        # Initial placeholder: create deterministic sample posts so the pipeline, UI, and scoring work end-to-end.
        # Unsupported real collectors must not claim live ingestion; status makes that explicit.
        existing = await self.db.execute(select(BenchmarkPost).where(BenchmarkPost.benchmark_account_id == account.id))
        for row in existing.scalars().all():
            await self.db.delete(row)
        await self.db.flush()

        now = datetime.now(timezone.utc)
        posts: list[BenchmarkPost] = []
        for idx in range(max(3, min(top_k, 10))):
            text = (
                f"{account.handle} benchmark sample {idx+1}\n"
                f"지금 확인해야 하는 핵심 포인트 {idx+1}가지\n"
                f"저장하고 댓글로 의견 남겨주세요 #{account.platform} #{idx+1}"
            )
            post = BenchmarkPost(
                benchmark_account_id=account.id,
                client_id=account.client_id,
                platform=account.platform,
                external_post_id=f"sample-{idx+1}",
                post_url=f"https://example.com/{account.platform}/{account.handle.strip('@')}/{idx+1}",
                content_text=text,
                hook_text=f"지금 확인해야 하는 핵심 포인트 {idx+1}가지",
                cta_text="저장하고 댓글로 의견 남겨주세요",
                hashtags_json=[f"#{account.platform}", f"#{idx+1}"],
                format_type="text",
                view_count=max(1000, 10000 - (idx * 700)),
                like_count=max(100, 1200 - (idx * 80)),
                comment_count=max(10, 150 - (idx * 12)),
                share_count=max(5, 80 - (idx * 6)),
                save_count=max(5, 60 - (idx * 4)),
                engagement_rate=max(0.5, 8.0 - (idx * 0.55)),
                raw_payload={"source": "placeholder_benchmark_pipeline", "live_supported": False},
                published_at=now - timedelta(days=idx * 2),
            )
            post.benchmark_score = calculate_benchmark_score(post, window_days=window_days)
            self.db.add(post)
            posts.append(post)

        await self.db.commit()
        profile = await self.rebuild_action_language_profile(account.client_id, account.platform)
        return {
            "status": "manual_ingest_required",
            "message": "실채널 수집기는 아직 미구현이며 현재는 파이프라인 검증용 샘플 데이터만 적재했습니다.",
            "inserted": len(posts),
            "profile_id": str(profile.id) if profile else None,
        }

    async def get_top_posts(self, client_id: uuid.UUID, platform: str, top_k: int = 10) -> list[BenchmarkPost]:
        result = await self.db.execute(
            select(BenchmarkPost)
            .where(BenchmarkPost.client_id == client_id, BenchmarkPost.platform == platform)
            .order_by(desc(BenchmarkPost.benchmark_score), desc(BenchmarkPost.view_count))
            .limit(top_k)
        )
        return list(result.scalars().all())

    async def rebuild_action_language_profile(self, client_id: uuid.UUID, platform: str) -> ActionLanguageProfile | None:
        posts = await self.get_top_posts(client_id, platform, top_k=20)
        if not posts:
            return None
        profile_data = build_action_language_profile(
            platform,
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
                ActionLanguageProfile.platform == platform,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = ActionLanguageProfile(
                client_id=client_id,
                platform=platform,
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
        return row

    async def get_action_language_profile(self, client_id: uuid.UUID, platform: str) -> ActionLanguageProfile | None:
        result = await self.db.execute(
            select(ActionLanguageProfile).where(
                ActionLanguageProfile.client_id == client_id,
                ActionLanguageProfile.platform == platform,
            )
        )
        return result.scalar_one_or_none()
