from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class LLMGenerationResult(BaseModel):
    provider: str
    model: str
    output_text: str
    parsed_json: dict | list | None = None
    latency_ms: int | None = None


class BaseLLMEngine(Protocol):
    provider_name: str

    async def generate_text(self, prompt: str, model: str | None = None, **kwargs: Any) -> LLMGenerationResult:
        ...

    async def generate_json(self, prompt: str, model: str | None = None, **kwargs: Any) -> LLMGenerationResult:
        ...
