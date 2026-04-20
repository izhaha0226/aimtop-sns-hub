"""
Prompt Builder - Constructs context-aware prompts for AI services.
Incorporates onboarding settings, platform optimization, and strategy context.
"""

# Platform-specific format instructions
PLATFORM_FORMATS: dict[str, str] = {
    "instagram": (
        "인스타그램 피드용 캡션을 작성해. "
        "이모지를 적절히 사용하고, 짧은 문단으로 나누고, "
        "해시태그는 본문 아래 별도로 배치해. "
        "글자 수 2200자 이내."
    ),
    "blog": (
        "네이버 블로그 본문을 작성해. "
        "SEO 최적화된 제목, 소제목 구조, "
        "1500~3000자 분량으로 작성해. "
        "핵심 키워드를 자연스럽게 반복해."
    ),
    "youtube": (
        "유튜브 영상 설명란을 작성해. "
        "핵심 내용 요약 + 타임스탬프 예시 + CTA를 포함해. "
        "SEO 키워드를 자연스럽게 포함해."
    ),
    "x": (
        "X(트위터) 게시물을 작성해. "
        "280자 이내로 임팩트 있게 작성하고, "
        "관련 해시태그 2~3개만 포함해."
    ),
    "threads": (
        "Threads 게시물을 작성해. "
        "캐주얼하고 대화체로, 500자 이내로 작성해."
    ),
}

DEFAULT_PLATFORM_FORMAT = (
    "SNS 게시물 카피를 작성해. "
    "플랫폼에 맞는 적절한 길이와 톤으로 작성해."
)


def _get_platform_instruction(platform: str) -> str:
    """Get platform-specific writing instructions."""
    return PLATFORM_FORMATS.get(platform.lower(), DEFAULT_PLATFORM_FORMAT)


def build_copy_prompt(
    platform: str,
    tone: str,
    topic: str,
    context: str = "",
    language: str = "ko",
    brand_name: str = "",
    target_audience: str = "",
    strategy_keywords: list[str] | None = None,
    benchmark_profile: dict | None = None,
) -> str:
    """Build a complete prompt for copy generation.

    Returns a prompt string that instructs Claude to respond
    with JSON: {title, body, hashtags[], cta}
    """
    parts: list[str] = []

    # Language setting
    lang_label = {"ko": "한국어", "en": "English", "ja": "日本語"}.get(language, language)
    parts.append(f"응답 언어: {lang_label}")

    # Brand context
    if brand_name:
        parts.append(f"브랜드: {brand_name}")
    if target_audience:
        parts.append(f"타겟 오디언스: {target_audience}")

    # Platform instruction
    parts.append(f"\n[플랫폼 가이드]\n{_get_platform_instruction(platform)}")

    # Tone
    parts.append(f"\n[톤앤매너]\n{tone}")

    # Strategy keywords
    if strategy_keywords:
        parts.append(f"\n[전략 키워드]\n{', '.join(strategy_keywords)}")

    # Additional context
    if context:
        parts.append(f"\n[추가 컨텍스트]\n{context}")

    if benchmark_profile:
        top_hooks = ", ".join(item.get("pattern", "") for item in benchmark_profile.get("top_hooks", [])[:3] if item.get("pattern"))
        top_ctas = ", ".join(item.get("pattern", "") for item in benchmark_profile.get("top_ctas", [])[:3] if item.get("pattern"))
        rules = benchmark_profile.get("recommended_prompt_rules", "")
        parts.append(
            "\n[벤치마킹 인텔리전스]\n"
            f"상위 훅 패턴: {top_hooks or '없음'}\n"
            f"상위 CTA 패턴: {top_ctas or '없음'}\n"
            f"적용 규칙: {rules or '문구를 직접 복제하지 말고 구조만 참고할 것'}"
        )

    # Main topic
    parts.append(f"\n[주제]\n{topic}")

    # Output format
    parts.append(
        "\n[출력 형식]\n"
        "반드시 아래 JSON 형식으로만 응답해:\n"
        '{"title": "제목", "body": "본문 내용", '
        '"hashtags": ["#해시태그1", "#해시태그2"], "cta": "행동 유도 문구"}'
    )

    return "\n".join(parts)


def build_strategy_prompt(
    brand_name: str,
    tone: str,
    target_audience: str,
    period: str = "monthly",
    current_themes: list[str] | None = None,
    goals: list[str] | None = None,
) -> str:
    """Build a prompt for strategy document generation."""
    parts: list[str] = [
        f"브랜드: {brand_name}",
        f"톤앤매너: {tone}",
        f"타겟 오디언스: {target_audience}",
        f"기간: {period}",
    ]

    if current_themes:
        parts.append(f"현재 테마: {', '.join(current_themes)}")
    if goals:
        parts.append(f"목표: {', '.join(goals)}")

    return "\n".join(parts)
