"""
Growth Service - AI 기반 성장 허브.
트렌딩 해시태그, 콘텐츠 아이디어, 경쟁사 분석, 최적 스케줄.
Claude CLI만 사용 (Anthropic API 직접 호출 금지).
"""
import json
import logging
import uuid
from collections import Counter

from sqlalchemy import desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai_service import call_claude, _parse_json_response

logger = logging.getLogger(__name__)


class GrowthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _safe_int(value) -> int:
        try:
            return max(int(value or 0), 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_float(value) -> float:
        try:
            return max(float(value or 0), 0.0)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def build_viral_signal_summary(cls, posts: list) -> dict:
        """Summarize benchmark/content signals that indicate shareability."""
        platform_counter: Counter[str] = Counter()
        hashtag_counter: Counter[str] = Counter()
        format_counter: Counter[str] = Counter()
        hooks: list[str] = []
        totals = {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "saves": 0,
            "benchmark_score": 0.0,
        }

        for post in posts:
            platform = str(getattr(post, "platform", "") or "unknown")
            platform_counter[platform] += 1
            format_type = str(getattr(post, "format_type", "") or "unknown")
            format_counter[format_type] += 1
            for tag in getattr(post, "hashtags_json", None) or []:
                normalized = str(tag).strip()
                if normalized:
                    hashtag_counter[normalized] += 1
            hook = (getattr(post, "hook_text", None) or getattr(post, "content_text", None) or "").strip()
            if hook:
                hooks.append(hook[:120])

            totals["views"] += cls._safe_int(getattr(post, "view_count", 0))
            totals["likes"] += cls._safe_int(getattr(post, "like_count", 0))
            totals["comments"] += cls._safe_int(getattr(post, "comment_count", 0))
            totals["shares"] += cls._safe_int(getattr(post, "share_count", 0))
            totals["saves"] += cls._safe_int(getattr(post, "save_count", 0))
            totals["benchmark_score"] += cls._safe_float(getattr(post, "benchmark_score", 0.0))

        sample_size = len(posts)
        denominator = max(totals["views"], 1)
        share_rate = round(totals["shares"] / denominator, 4)
        save_rate = round(totals["saves"] / denominator, 4)
        comment_rate = round(totals["comments"] / denominator, 4)
        avg_benchmark = totals["benchmark_score"] / sample_size if sample_size else 0.0
        viral_score = round(
            min(
                100.0,
                (share_rate * 1200) + (save_rate * 900) + (comment_rate * 600) + (avg_benchmark * 0.35),
            ),
            1,
        )

        return {
            "sample_size": sample_size,
            "top_platform": platform_counter.most_common(1)[0][0] if platform_counter else None,
            "viral_score": viral_score,
            "share_rate": share_rate,
            "save_rate": save_rate,
            "comment_rate": comment_rate,
            "top_hashtags": [tag for tag, _ in hashtag_counter.most_common(8)],
            "top_hooks": hooks[:5],
            "top_formats": [
                {"format": format_type, "count": count}
                for format_type, count in format_counter.most_common(5)
            ],
            "totals": totals,
        }

    @staticmethod
    def build_viral_blueprint(client, platform: str, signal_summary: dict) -> dict:
        """Turn Supermarketing viral principles into SNS Hub execution objects."""
        client_name = getattr(client, "name", "선택 클라이언트")
        industry = getattr(client, "industry_category", None) or "일반"
        top_hashtags = signal_summary.get("top_hashtags") or []
        top_hooks = signal_summary.get("top_hooks") or []
        primary_format = "card_news"
        if signal_summary.get("top_formats"):
            primary_format = signal_summary["top_formats"][0].get("format") or primary_format

        return {
            "client": {"name": client_name, "industry_category": industry},
            "platform": platform,
            "strategy_name": "Share-first Viral Loop",
            "strategic_thesis": (
                f"{client_name}의 SNS는 단순 노출보다 '저장·공유·댓글 참여'를 먼저 설계해야 합니다. "
                "콘텐츠 1개가 다음 콘텐츠 소재와 신규 도달을 동시에 만드는 루프로 운영합니다."
            ),
            "signal_summary": signal_summary,
            "viral_loop": {
                "stages": [
                    {"stage": "1. Stop-scroll", "mechanic": "반대 관점/진단형 훅으로 2초 안에 멈추게 함"},
                    {"stage": "2. Save", "mechanic": "체크리스트·템플릿·비교표로 저장 이유를 제공"},
                    {"stage": "3. Share", "mechanic": "친구/팀/가족에게 보내야 하는 상황을 CTA에 직접 명시"},
                    {"stage": "4. Participate", "mechanic": "댓글 키워드, 경험 공유, 투표로 다음 소재를 수집"},
                    {"stage": "5. Repurpose", "mechanic": "댓글/공유 이유를 다음 카드뉴스·릴스·스레드로 재가공"},
                ]
            },
            "content_experiments": [
                {
                    "name": "저장형 체크리스트 카드뉴스",
                    "format": primary_format,
                    "hook": top_hooks[0] if top_hooks else f"{industry}에서 놓치기 쉬운 5가지",
                    "cta": "필요한 친구에게 공유하고 저장해두세요",
                    "measurement": "save_rate, share_rate",
                },
                {
                    "name": "반대 관점/오해 깨기 포스트",
                    "format": "text_or_threads",
                    "hook": f"대부분의 {industry} 콘텐츠가 놓치는 한 가지",
                    "cta": "동의/반박을 댓글로 남겨주세요",
                    "measurement": "comment_rate, profile_clicks",
                },
                {
                    "name": "UGC 질문 루프",
                    "format": "story_or_reels",
                    "hook": "대표님의 경험을 다음 콘텐츠에 반영합니다",
                    "cta": "댓글에 상황을 남기면 다음 편에서 다룹니다",
                    "measurement": "comment_rate, reply_count",
                },
                {
                    "name": "벤치마크 리믹스",
                    "format": "card_news_or_reels",
                    "hook": "요즘 반응 좋은 포맷을 우리 브랜드 언어로 재해석",
                    "cta": "비슷한 고민을 가진 사람에게 보내주세요",
                    "measurement": "share_rate, reach_per_post",
                },
            ],
            "recommended_hashtags": top_hashtags[:5],
            "measurement": {
                "primary_metrics": ["share_rate", "save_rate", "comment_rate", "reach_per_post"],
                "guardrails": ["브랜드 과장 금지", "경쟁사 문구/구조 복제 금지", "샘플 수 부족 시 확정 표현 금지"],
                "next_review_cadence": "주 1회: 실공유율/저장률 기준으로 훅과 CTA 교체",
            },
        }

    async def get_viral_strategy(self, client_id: uuid.UUID, platform: str = "instagram", top_k: int = 20) -> dict:
        """Client-scoped viral strategy based on benchmark signals and Supermarketing patterns."""
        from models.benchmark_post import BenchmarkPost
        from models.client import Client

        client_result = await self.db.execute(
            select(Client).where(Client.id == client_id, Client.is_deleted.is_(False))
        )
        client = client_result.scalar_one_or_none()
        if client is None:
            raise ValueError("Client not found")

        posts_result = await self.db.execute(
            select(BenchmarkPost)
            .where(BenchmarkPost.client_id == client_id, BenchmarkPost.platform == platform)
            .order_by(desc(BenchmarkPost.benchmark_score), desc(BenchmarkPost.share_count), desc(BenchmarkPost.save_count))
            .limit(top_k)
        )
        posts = list(posts_result.scalars().all())
        signal_summary = self.build_viral_signal_summary(posts)
        blueprint = self.build_viral_blueprint(client=client, platform=platform, signal_summary=signal_summary)
        if signal_summary["sample_size"] == 0:
            blueprint["data_warning"] = "벤치마크 게시물 샘플이 없습니다. 경쟁/레퍼런스 계정을 먼저 등록·수집하면 추천 정확도가 올라갑니다."
        return blueprint

    @staticmethod
    def _normalize_hashtag(tag: str) -> str:
        cleaned = str(tag or "").strip().replace(" ", "")
        if not cleaned:
            return ""
        return cleaned if cleaned.startswith("#") else f"#{cleaned}"

    @classmethod
    def build_hashtag_fallback(cls, platform: str, category: str | None = None, tags: list[str] | None = None) -> list[dict]:
        """Deterministic fallback so Growth Hub never depends on local Claude CLI availability."""
        base_tags = tags or []
        if category:
            base_tags.extend([category, f"{category}마케팅", f"{category}콘텐츠"])
        base_tags.extend([platform, "SNS운영", "콘텐츠전략", "브랜드성장", "카드뉴스", "마케팅인사이트"])
        seen: set[str] = set()
        result: list[dict] = []
        for tag in base_tags:
            normalized = cls._normalize_hashtag(tag)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append({
                "hashtag": normalized,
                "popularity": "medium",
                "reason": "벤치마크/클라이언트 카테고리 기반 fallback 추천",
            })
        return result[:20]

    @staticmethod
    def build_content_idea_fallback(recent_titles: list[str], platforms: list[str], count: int = 10) -> list[dict]:
        platform = platforms[0] if platforms else "instagram"
        seeds = [title for title in recent_titles if title and title != "정보 없음"]
        themes = seeds[:3] or ["브랜드 신뢰", "고객 질문", "성과 사례"]
        templates = [
            ("저장형 체크리스트", "고객이 저장해둘 수 있는 실행 체크리스트로 재구성"),
            ("오해 깨기 콘텐츠", "업종에서 흔한 오해를 반대 관점 훅으로 설명"),
            ("비교/선택 가이드", "구매·문의 전 비교 기준을 카드뉴스로 정리"),
            ("고객 질문 답변", "댓글/상담에서 반복되는 질문을 짧은 Q&A로 전환"),
            ("사례 기반 신뢰 포스트", "성과·과정·비하인드를 증거 중심으로 보여줌"),
        ]
        ideas: list[dict] = []
        for index in range(count):
            name, description = templates[index % len(templates)]
            theme = themes[index % len(themes)]
            ideas.append({
                "title": f"{theme} · {name}",
                "platform": platform,
                "post_type": "card_news" if index % 2 == 0 else "text",
                "description": description,
                "expected_engagement": "medium",
                "source": "deterministic_fallback",
            })
        return ideas

    @staticmethod
    def build_competitor_analysis_fallback(competitor_handles: list[str]) -> dict:
        competitors = [
            {
                "handle": handle,
                "estimated_strategy": "등록/수집된 벤치마크 데이터가 부족해 정성 분석 fallback으로 표시합니다.",
                "strengths": ["포지셔닝/콘텐츠 톤 확인 필요", "반응 높은 포맷 수집 필요"],
                "weaknesses": ["실측 게시물 샘플 부족"],
                "content_pattern": "벤치마킹 센터에서 계정 등록 후 Top Posts 수집 필요",
                "posting_frequency": "데이터 부족",
            }
            for handle in competitor_handles
        ]
        return {
            "competitors": competitors,
            "recommendations": [
                "벤치마킹 센터에 경쟁/레퍼런스 계정을 등록하고 수집 후 다시 분석하세요.",
                "현재는 Stop-scroll 훅, 저장형 체크리스트, 공유 CTA 중심으로 실험을 시작하세요.",
            ],
            "market_gaps": ["실측 샘플 부족: 해시태그·포맷·댓글 패턴 수집 필요"],
            "source": "deterministic_fallback",
        }

    async def get_trending_hashtags(
        self, platform: str, category: str | None = None
    ) -> list:
        """트렌딩 해시태그 조회. Claude CLI가 없어도 deterministic fallback으로 응답."""
        category_text = f" ({category} 카테고리)" if category else ""
        prompt = (
            f"{platform} 플랫폼{category_text}에서 현재 트렌딩 중인 해시태그 20개를 추천해줘.\n"
            f"각 해시태그의 인기도(high/medium/low)와 추천 이유도 함께 제공해.\n\n"
            f"JSON 배열로만 응답:\n"
            '[{"hashtag": "#예시", "popularity": "high", "reason": "이유"}]'
        )
        try:
            raw = await call_claude(prompt, timeout=8)
            result = _parse_json_response(raw)
            if isinstance(result, list) and result:
                return result
            if isinstance(result, dict):
                return [result]
        except (FileNotFoundError, TimeoutError, RuntimeError, json.JSONDecodeError, Exception) as e:
            logger.warning("Trending hashtag AI unavailable; using fallback: %s", e)
        return self.build_hashtag_fallback(platform=platform, category=category)

    async def get_content_ideas(
        self, client_id: uuid.UUID, count: int = 10
    ) -> list:
        """콘텐츠 아이디어 생성. 콘텐츠 schema와 LLM 장애에 안전하게 fallback."""
        from models.content import Content
        result = await self.db.execute(
            select(Content.title, Content.target_platform, Content.post_type)
            .where(Content.client_id == client_id)
            .order_by(Content.created_at.desc())
            .limit(20)
        )
        recent = result.all()
        recent_titles = [r[0] for r in recent if r[0]] or ["정보 없음"]
        platforms = list({r[1] for r in recent if r[1]}) or ["instagram"]

        prompt = (
            f"다음 클라이언트의 최근 콘텐츠를 분석하고 새로운 콘텐츠 아이디어를 {count}개 제안해줘.\n\n"
            f"최근 콘텐츠 제목:\n"
            + "\n".join(f"- {t}" for t in recent_titles[:10])
            + f"\n\n활성 플랫폼: {', '.join(platforms)}\n\n"
            f"JSON 배열로만 응답:\n"
            '[{"title": "아이디어 제목", "platform": "플랫폼", "post_type": "유형", '
            '"description": "설명", "expected_engagement": "high/medium/low"}]'
        )
        try:
            raw = await call_claude(prompt, timeout=12)
            result = _parse_json_response(raw)
            ideas = result if isinstance(result, list) else [result]
            if ideas:
                return ideas[:count]
        except (FileNotFoundError, TimeoutError, RuntimeError, json.JSONDecodeError, Exception) as e:
            logger.warning("Content ideas AI unavailable; using fallback: %s", e)
        return self.build_content_idea_fallback(recent_titles=recent_titles, platforms=platforms, count=count)

    async def get_competitor_analysis(
        self, competitor_handles: list[str]
    ) -> dict:
        """경쟁사 분석. Claude CLI가 없어도 화면이 작동하도록 fallback."""
        handles_text = ", ".join(competitor_handles)
        prompt = (
            f"다음 SNS 계정들의 경쟁사 분석을 수행해줘: {handles_text}\n\n"
            f"각 계정에 대해 추정되는 전략, 강점, 약점, 콘텐츠 패턴을 분석해.\n\n"
            f"JSON 형식으로 응답:\n"
            '{"competitors": [{"handle": "@계정", "estimated_strategy": "...", '
            '"strengths": ["..."], "weaknesses": ["..."], "content_pattern": "...", '
            '"posting_frequency": "..."}], '
            '"recommendations": ["우리가 할 수 있는 차별화 전략"], '
            '"market_gaps": ["시장 기회"]}'
        )
        try:
            raw = await call_claude(prompt, timeout=12)
            result = _parse_json_response(raw)
            if isinstance(result, dict):
                return result
            return {"raw": result}
        except (FileNotFoundError, TimeoutError, RuntimeError, json.JSONDecodeError, Exception) as e:
            logger.warning("Competitor analysis AI unavailable; using fallback: %s", e)
        return self.build_competitor_analysis_fallback(competitor_handles)

    async def get_optimal_schedule(self, account_id: uuid.UUID) -> dict:
        """최적 스케줄 AI 추천."""
        # 기존 스케줄/분석 데이터 조회
        from models.analytics import Analytics
        from models.channel import ChannelConnection

        channel_result = await self.db.execute(
            select(ChannelConnection.platform)
            .where(ChannelConnection.id == account_id)
        )
        channel = channel_result.scalar_one_or_none()
        platform = channel or "instagram"

        # 요일별 분석 데이터
        analytics_result = await self.db.execute(
            select(
                func.extract("dow", Analytics.date).label("dow"),
                func.avg(Analytics.likes).label("avg_likes"),
                func.avg(Analytics.reach).label("avg_reach"),
            )
            .where(Analytics.channel_id == account_id)
            .group_by("dow")
            .order_by("dow")
        )
        weekday_stats = [
            {"day_of_week": int(r[0]), "avg_likes": float(r[1] or 0), "avg_reach": float(r[2] or 0)}
            for r in analytics_result.all()
        ]

        stats_text = json.dumps(weekday_stats, ensure_ascii=False) if weekday_stats else "데이터 없음"

        prompt = (
            f"{platform} 플랫폼 계정의 최적 포스팅 스케줄을 추천해줘.\n\n"
            f"요일별 성과 데이터:\n{stats_text}\n\n"
            f"JSON 형식으로 응답:\n"
            f'{{"platform": "{platform}", '
            f'"recommended_times": [{{"day": "월요일", "times": ["09:00", "18:00"], "reason": "..."}}], '
            f'"posting_frequency": "주 N회 추천", '
            f'"best_days": ["화요일", "목요일"], '
            f'"avoid_times": ["..."], '
            f'"tips": ["..."]}}'
        )
        raw = await call_claude(prompt, timeout=8)
        try:
            result = _parse_json_response(raw)
            return result if isinstance(result, dict) else {"raw": result}
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Optimal schedule parse failed: %s", e)
            return {
                "platform": platform,
                "recommended_times": [],
                "posting_frequency": "분석 실패",
                "tips": [raw],
            }
