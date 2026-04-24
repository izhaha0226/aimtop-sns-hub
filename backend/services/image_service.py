"""
Image Service - Fal.ai API integration for image generation.
"""
import logging

import httpx

from services.runtime_settings import get_runtime_setting

logger = logging.getLogger(__name__)

# Model mapping
_MODEL_MAP = {
    "fast": "fal-ai/nano-banana-2",
    "nano2": "fal-ai/nano-banana-2",
    "quality": "openai/gpt-image-2",
    "gpt-image-2.0": "openai/gpt-image-2",
    "gpt_image_2": "openai/gpt-image-2",
    "nano_pro": "openai/gpt-image-2",
}

FAL_API_BASE = "https://fal.run"


async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    model: str = "gpt-image-2.0",
    quality: str | None = None,
) -> dict:
    """Generate an image via Fal.ai API.

    Args:
        prompt: Text description of the image to generate.
        size: Image dimensions (e.g. "1024x1024", "1024x768").
        model: default gpt-image-2.0 via Fal, with legacy aliases supported.

    Returns:
        {image_url, seed, model_used}
    """
    fal_key = await get_runtime_setting("fal_key")
    if not fal_key:
        raise RuntimeError("FAL_KEY environment variable is not set")

    model_id = _MODEL_MAP.get(model, _MODEL_MAP["fast"])

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
    if model_id == "openai/gpt-image-2" and quality:
        payload["quality"] = quality

    async with httpx.AsyncClient(timeout=300) as client:
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
