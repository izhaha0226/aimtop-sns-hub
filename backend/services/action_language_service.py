from __future__ import annotations

import re
from collections import Counter

CTA_PATTERNS = {
    "save": ["저장", "save"],
    "comment": ["댓글", "comment"],
    "dm": ["dm", "문의", "메시지"],
    "click": ["클릭", "link", "링크"],
    "profile": ["프로필"],
    "consult": ["상담", "문의하기"],
}

HOOK_PATTERNS = {
    "question": r"\?$",
    "number": r"\d+",
    "warning": r"주의|놓치면|손해",
    "list": r"체크|가지|포인트|방법",
    "before_after": r"전|후|before|after",
}

EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
HASHTAG_RE = re.compile(r"#\w+")


def _first_line(text: str) -> str:
    return (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""


def _extract_ctas(text: str) -> list[str]:
    lowered = (text or "").lower()
    found = []
    for name, patterns in CTA_PATTERNS.items():
        if any(p.lower() in lowered for p in patterns):
            found.append(name)
    return found


def _extract_hook_tags(hook: str) -> list[str]:
    found = []
    for name, pattern in HOOK_PATTERNS.items():
        if re.search(pattern, hook, re.IGNORECASE):
            found.append(name)
    return found


def build_action_language_profile(platform: str, posts: list[dict]) -> dict:
    hook_counter: Counter[str] = Counter()
    cta_counter: Counter[str] = Counter()
    hook_examples: list[str] = []
    hashtag_counts = []
    emoji_counts = []
    linebreak_counts = []
    sentence_lengths = []

    for post in posts:
        text = str(post.get("content_text") or "")
        hook = str(post.get("hook_text") or _first_line(text))
        if hook:
            hook_examples.append(hook)
            hook_counter.update(_extract_hook_tags(hook))
        cta_text = str(post.get("cta_text") or text)
        cta_counter.update(_extract_ctas(cta_text))
        hashtag_counts.append(len(HASHTAG_RE.findall(text)))
        emoji_counts.append(len(EMOJI_RE.findall(text)))
        linebreak_counts.append(text.count("\n"))
        if text:
            sentence_lengths.append(round(len(text) / max(1, len(text.split())), 2))

    top_hooks = [{"pattern": name, "count": count} for name, count in hook_counter.most_common(5)]
    top_ctas = [{"pattern": name, "count": count} for name, count in cta_counter.most_common(5)]

    return {
        "platform": platform,
        "top_hooks": top_hooks,
        "top_ctas": top_ctas,
        "tone_patterns": {
            "sample_hooks": hook_examples[:5],
            "avg_emoji_count": round(sum(emoji_counts) / len(emoji_counts), 2) if emoji_counts else 0,
            "avg_linebreak_count": round(sum(linebreak_counts) / len(linebreak_counts), 2) if linebreak_counts else 0,
        },
        "format_patterns": {
            "avg_hashtag_count": round(sum(hashtag_counts) / len(hashtag_counts), 2) if hashtag_counts else 0,
            "avg_sentence_length": round(sum(sentence_lengths) / len(sentence_lengths), 2) if sentence_lengths else 0,
        },
        "recommended_prompt_rules": (
            f"{platform} 상위 콘텐츠의 훅 패턴 {', '.join(item['pattern'] for item in top_hooks[:3]) or 'none'}와 "
            f"CTA 패턴 {', '.join(item['pattern'] for item in top_ctas[:3]) or 'none'}를 반영하되 문구는 직접 복제하지 말 것."
        ),
    }
