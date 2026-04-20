from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from services.llm.base import LLMGenerationResult
from services.runtime_settings import get_runtime_setting

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


class GPTEngine:
    provider_name = "gpt"

    async def _resolve_client_config(self) -> tuple[str, str]:
        api_key = await get_runtime_setting("openai_api_key")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        base_url = await get_runtime_setting("openai_base_url") or DEFAULT_OPENAI_BASE_URL
        return api_key, base_url.rstrip("/")

    async def generate_text(
        self,
        prompt: str,
        model: str | None = None,
        timeout: int = 60,
        max_tokens: int = 1200,
        **_: Any,
    ) -> LLMGenerationResult:
        started = time.perf_counter()
        api_key, base_url = await self._resolve_client_config()
        payload = {
            "model": model or "gpt-4.1-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            output_text = data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error("GPT response parse failed: %s", e)
            raise RuntimeError("GPT response parse failed") from e

        return LLMGenerationResult(
            provider=self.provider_name,
            model=payload["model"],
            output_text=output_text,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def generate_json(self, prompt: str, model: str | None = None, timeout: int = 60, **kwargs: Any) -> LLMGenerationResult:
        result = await self.generate_text(prompt, model=model, timeout=timeout, **kwargs)
        text = result.output_text.strip()
        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()
        result.parsed_json = json.loads(text)
        return result
