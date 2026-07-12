"""
전 채널 자동화 capability registry.

코드 지원 여부와 실계정/App Review 가능 여부는 분리해서 보고한다.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# 9 channels in product scope
ALL_PLATFORMS = (
    "instagram",
    "facebook",
    "threads",
    "x",
    "youtube",
    "blog",
    "linkedin",
    "kakao",
    "tiktok",
)

# Canonical capability table — keep in sync with SNSPublisher / CommentService / OAuth.
_CAPABILITIES: dict[str, dict[str, Any]] = {
    "instagram": {
        "label": "Instagram",
        "oauth": True,
        "publish": True,
        "publish_media": ["image", "carousel"],
        "comment_fetch": True,
        "comment_reply": True,
        "material_variant": True,
        "automation_ready": True,
        "notes": "Graph API. IG business/creator + content publish 권한 필요.",
        "blockers": ["instagram_user_id 없으면 발행 불가", "App Review(content_publish) 필요할 수 있음"],
    },
    "facebook": {
        "label": "Facebook",
        "oauth": True,
        "publish": True,
        "publish_media": ["image", "text"],
        "comment_fetch": True,
        "comment_reply": True,
        "material_variant": True,
        "automation_ready": True,
        "notes": "Page feed/photos. pages_manage_posts는 발행 단계에서 필요할 수 있음.",
        "blockers": ["Page 선택 필수", "pages_manage_posts App Review 가능"],
    },
    "threads": {
        "label": "Threads",
        "oauth": True,
        "publish": True,
        "publish_media": ["text", "image"],
        "comment_fetch": True,
        "comment_reply": False,
        "material_variant": True,
        "automation_ready": True,
        "notes": "텍스트/이미지 발행 + 전용 자동화 MVP 보유. 답글 API는 제한적.",
        "blockers": ["Threads 전용 권한/App Review 가능"],
    },
    "x": {
        "label": "X",
        "oauth": True,
        "publish": True,
        "publish_media": ["text", "image"],
        "comment_fetch": False,
        "comment_reply": False,
        "material_variant": True,
        "automation_ready": True,
        "notes": "Tweet 발행 지원. 댓글(멘션) 수집은 API tier 의존으로 기본 비활성.",
        "blockers": ["X API tier/결제 플랜"],
    },
    "youtube": {
        "label": "YouTube",
        "oauth": True,
        "publish": True,
        "publish_media": ["video"],
        "comment_fetch": True,
        "comment_reply": True,
        "material_variant": True,
        "automation_ready": True,
        "notes": "영상 업로드 중심. 카드뉴스 변형은 설명/제목 텍스트 위주.",
        "blockers": ["영상 미디어 필요"],
    },
    "blog": {
        "label": "Naver Blog",
        "oauth": True,
        "publish": True,
        "publish_media": ["text", "image"],
        "comment_fetch": False,
        "comment_reply": False,
        "material_variant": True,
        "automation_ready": True,
        "notes": "장문 발행 중심. 댓글 API 미연동.",
        "blockers": ["네이버 앱 권한"],
    },
    "linkedin": {
        "label": "LinkedIn",
        "oauth": True,
        "publish": True,
        "publish_media": ["text", "link"],
        "comment_fetch": False,
        "comment_reply": False,
        "material_variant": True,
        "automation_ready": True,
        "notes": "텍스트 중심 발행. 이미지는 commentary 링크 방식.",
        "blockers": ["w_member_social 권한", "refresh 미지원 → 재인증 주기 짧음"],
    },
    "kakao": {
        "label": "Kakao Channel",
        "oauth": True,
        "publish": False,
        "publish_media": [],
        "comment_fetch": False,
        "comment_reply": False,
        "material_variant": True,
        "automation_ready": False,
        "notes": "OAuth/소재 변형만. 실발행 adapter 미구현.",
        "blockers": ["publish adapter 미구현", "카카오 비즈 API 권한"],
    },
    "tiktok": {
        "label": "TikTok",
        "oauth": True,
        "publish": False,
        "publish_media": [],
        "comment_fetch": False,
        "comment_reply": False,
        "material_variant": True,
        "automation_ready": False,
        "notes": "OAuth만. Content Posting API 연동 대기.",
        "blockers": ["publish adapter 미구현", "TikTok 앱 검수"],
    },
}


def list_capabilities() -> list[dict[str, Any]]:
    items = []
    for platform in ALL_PLATFORMS:
        item = deepcopy(_CAPABILITIES[platform])
        item["platform"] = platform
        items.append(item)
    return items


def get_capability(platform: str) -> dict[str, Any] | None:
    key = (platform or "").strip().lower()
    if key not in _CAPABILITIES:
        return None
    item = deepcopy(_CAPABILITIES[key])
    item["platform"] = key
    return item


def assert_capability(platform: str, feature: str) -> dict[str, Any]:
    """feature: publish | comment_fetch | comment_reply | material_variant | oauth"""
    cap = get_capability(platform)
    if not cap:
        raise ValueError(f"지원하지 않는 채널입니다: {platform}")
    if feature not in cap:
        raise ValueError(f"알 수 없는 capability feature: {feature}")
    if not cap.get(feature):
        blockers = ", ".join(cap.get("blockers") or []) or "미지원"
        raise ValueError(
            f"{cap['label']} 채널은 {feature} 자동화를 지원하지 않습니다 ({blockers})"
        )
    return cap


def publishable_platforms() -> set[str]:
    return {p for p, c in _CAPABILITIES.items() if c.get("publish")}


def comment_sync_platforms() -> set[str]:
    return {p for p, c in _CAPABILITIES.items() if c.get("comment_fetch")}


def material_platforms() -> list[str]:
    return [p for p in ALL_PLATFORMS if _CAPABILITIES[p].get("material_variant")]
