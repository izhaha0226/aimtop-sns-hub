"""전 채널 자동화 엔진 계약 테스트 (DB 없이 단위 검증)."""

from services.auto_reply_service import AutoReplyService, DANGER_KEYWORD_RE
from services.channel_capability import (
    ALL_PLATFORMS,
    assert_capability,
    get_capability,
    list_capabilities,
    publishable_platforms,
)
from services.content_topic_service import build_channel_variant, build_fallback_storyline
from services.sns_publisher import SNSPublisher


class _Topic:
    def __init__(self):
        self.title = "자동화 테스트"
        self.brief = "소재 운영 댓글"
        self.core_message = "한 번의 주제로 전 채널 draft"
        self.card_storyline = None
        self.reference_assets = []


def test_capabilities_cover_nine_platforms():
    items = list_capabilities()
    platforms = {item["platform"] for item in items}
    assert platforms == set(ALL_PLATFORMS)
    assert len(items) == 9


def test_publishable_platforms_exclude_kakao_tiktok():
    pubs = publishable_platforms()
    assert "instagram" in pubs
    assert "facebook" in pubs
    assert "kakao" not in pubs
    assert "tiktok" not in pubs


def test_assert_capability_blocks_kakao_publish():
    try:
        assert_capability("kakao", "publish")
        assert False, "should raise"
    except ValueError as exc:
        assert "publish" in str(exc)


def test_sns_publisher_uses_capability_for_supported_check():
    assert SNSPublisher.is_supported_platform("instagram") is True
    assert SNSPublisher.is_supported_platform("kakao") is False


def test_channel_variant_respects_x_limit():
    topic = _Topic()
    topic.card_storyline = build_fallback_storyline(topic)
    variant = build_channel_variant(topic, "x")
    assert len(variant["text"]) <= 240
    assert variant["platform"] == "x"


def test_channel_variant_instagram_is_card_news():
    topic = _Topic()
    topic.card_storyline = build_fallback_storyline(topic)
    variant = build_channel_variant(topic, "instagram")
    assert variant["post_type"] == "card_news"
    assert "1." in variant["text"] or "강한 후킹" in variant["text"]


def test_danger_keywords_block_auto_reply():
    assert AutoReplyService.is_danger_comment("환불 요청합니다") is True
    assert AutoReplyService.is_danger_comment("좋은 정보 감사합니다") is False
    assert DANGER_KEYWORD_RE.search("변호사 선임합니다")


def test_comment_fetch_capability_matrix():
    assert get_capability("instagram")["comment_fetch"] is True
    assert get_capability("facebook")["comment_fetch"] is True
    assert get_capability("threads")["comment_fetch"] is True
    assert get_capability("youtube")["comment_fetch"] is True
    assert get_capability("x")["comment_fetch"] is False
