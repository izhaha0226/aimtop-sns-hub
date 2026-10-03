"""
Image Service - Fal.ai API integration for image generation.
"""
import logging

import httpx

from services.runtime_settings import get_runtime_setting

logger = logging.getLogger(__name__)

# Model mapping
# 2026-10-03 대표님 지시: 기본 이미지 모델을 GPT Image 2.5 Flare · medium 품질로 전환
# (1024² 기준 $0.013/장 — Nano Banana 2 $0.08, GPT Image 2 medium $0.053 대비 저렴).
# 기존 별칭(fast/quality/gpt-image-2.0/nano_pro)도 모두 2.5로 보낸다. 롤백용으로 nano2·gpt-image-2만 명시 별칭으로 남긴다.
GPT_IMAGE_25 = "openai/gpt-image-2.5/flare/text-to-image"
GPT_IMAGE_25_DEFAULT_QUALITY = "medium"
_MODEL_MAP = {
    "fast": GPT_IMAGE_25,
    "quality": GPT_IMAGE_25,
    "gpt-image-2.5": GPT_IMAGE_25,
    "gpt-image-2.0": GPT_IMAGE_25,
    "gpt_image_2": GPT_IMAGE_25,
    "nano_pro": GPT_IMAGE_25,
    "nano2": "fal-ai/nano-banana-2",
    "gpt-image-2": "openai/gpt-image-2",
}
_QUALITY_MODELS = {GPT_IMAGE_25, "openai/gpt-image-2"}

FAL_API_BASE = "https://fal.run"


async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    model: str = "gpt-image-2.5",
    quality: str | None = None,
) -> dict:
    """Generate an image via Fal.ai API.

    Args:
        prompt: Text description of the image to generate.
        size: Image dimensions (e.g. "1024x1024", "1024x768").
        model: default gpt-image-2.5 (Flare, medium) via Fal, with legacy aliases supported.
        quality: low/medium/high/xhigh/max — 생략하면 medium.

    Returns:
        {image_url, seed, model_used}
    """
    fal_key = await get_runtime_setting("fal_key")
    if not fal_key:
        raise RuntimeError("Fal.ai API key is not configured")

    model_id = _MODEL_MAP.get(model, GPT_IMAGE_25)

    # Parse size
    try:
        width, height = (int(x) for x in size.split("x"))
    except ValueError:
        width, height = 1024, 1024

    url = f"{FAL_API_BASE}/{model_id}"
    headers = {
        "Authorization": f"Key {fal_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "image_size": {"width": width, "height": height},
        "num_images": 1,
    }
    if model_id in _QUALITY_MODELS:
        payload["quality"] = quality or GPT_IMAGE_25_DEFAULT_QUALITY

    async with httpx.AsyncClient(timeout=170) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Extract result
    images = data.get("images", [])
    if not images:
        raise RuntimeError("No images returned from Fal.ai")

    first = images[0]
    return {
        "image_url": first.get("url", ""),
        "seed": data.get("seed", 0),
        "model_used": model_id,
    }
