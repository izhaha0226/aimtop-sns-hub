from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.llm_provider_config import LLMProviderConfig
from models.llm_task_policy import LLMTaskPolicy
from services.llm.base import LLMGenerationResult
from services.llm.claude_engine import ClaudeEngine
from services.llm.gpt_engine import GPTEngine

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_ROWS = [
    {
        "provider_name": "claude",
        "model_name": "claude-sonnet-4-6",
        "label": "Claude Sonnet 4.6",
        "is_default": True,
        "supports_json": True,
        "supports_reasoning": True,
        "max_tokens": 4096,
        "timeout_seconds": 60,
    },
    {
        "provider_name": "gpt",
        "model_name": "gpt-4.1-mini",
        "label": "GPT-4.1 mini",
        "is_default": False,
        "supports_json": True,
        "supports_reasoning": True,
        "max_tokens": 4096,
        "timeout_seconds": 60,
    },
]

DEFAULT_TASK_POLICIES = {
    "strategy": {
        "routing_mode": "manual",
        "primary_provider": "claude",
        "primary_model": "claude-sonnet-4-6",
        "fallback_provider": "gpt",
        "fallback_model": "gpt-4.1-mini",
    },
    "benchmark_analysis": {
        "routing_mode": "manual",
        "primary_provider": "claude",
        "primary_model": "claude-sonnet-4-6",
        "fallback_provider": "gpt",
        "fallback_model": "gpt-4.1-mini",
    },
    "copy_generation": {
        "routing_mode": "manual",
        "primary_provider": "claude",
        "primary_model": "claude-sonnet-4-6",
        "fallback_provider": "gpt",
        "fallback_model": "gpt-4.1-mini",
    },
    "report_summary": {
        "routing_mode": "manual",
        "primary_provider": "claude",
        "primary_model": "claude-sonnet-4-6",
        "fallback_provider": "gpt",
        "fallback_model": "gpt-4.1-mini",
    },
    "comment_reply_draft": {
        "routing_mode": "manual",
        "primary_provider": "claude",
        "primary_model": "claude-sonnet-4-6",
        "fallback_provider": "gpt",
        "fallback_model": "gpt-4.1-mini",
    },
}


class LLMRouter:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.engines = {
            "claude": ClaudeEngine(),
            "gpt": GPTEngine(),
        }

    async def generate_text(
        self,
        task_type: str,
        prompt: str,
        context: dict | None = None,
        override: dict | None = None,
    ) -> LLMGenerationResult:
        provider_name, model_name, timeout, fallback = await self._resolve_route(task_type, override=override)
        try:
            return await self.engines[provider_name].generate_text(prompt, model=model_name, timeout=timeout, context=context or {})
        except Exception as e:
            if not fallback:
                raise
            logger.warning("Primary LLM failed for %s: %s", task_type, e)
            fallback_provider, fallback_model, fallback_timeout = fallback
            return await self.engines[fallback_provider].generate_text(
                prompt,
                model=fallback_model,
                timeout=fallback_timeout,
                context=context or {},
            )

    async def generate_json(
        self,
        task_type: str,
        prompt: str,
        context: dict | None = None,
        override: dict | None = None,
    ) -> LLMGenerationResult:
        provider_name, model_name, timeout, fallback = await self._resolve_route(task_type, override=override)
        try:
            return await self.engines[provider_name].generate_json(prompt, model=model_name, timeout=timeout, context=context or {})
        except Exception as e:
            if not fallback:
                raise
            logger.warning("Primary JSON LLM failed for %s: %s", task_type, e)
            fallback_provider, fallback_model, fallback_timeout = fallback
            return await self.engines[fallback_provider].generate_json(
                prompt,
                model=fallback_model,
                timeout=fallback_timeout,
                context=context or {},
            )

    async def _resolve_route(self, task_type: str, override: dict | None = None) -> tuple[str, str, int, tuple[str, str, int] | None]:
        override = override or {}
        policy = await self._get_task_policy(task_type)
        provider = override.get("provider") or policy.get("primary_provider") or "claude"
        model = override.get("model") or policy.get("primary_model") or "claude-sonnet-4-6"
        provider_cfg = await self._get_provider_config(provider, model)
        timeout = provider_cfg.timeout_seconds if provider_cfg else 60

        fallback = None
        fallback_enabled = override.get("fallback_enabled")
        if fallback_enabled is None:
            fallback_enabled = policy.get("fallback_enabled", True)
        if fallback_enabled and policy.get("fallback_provider") and policy.get("fallback_model"):
            fallback_cfg = await self._get_provider_config(policy["fallback_provider"], policy["fallback_model"])
            fallback = (
                policy["fallback_provider"],
                policy["fallback_model"],
                fallback_cfg.timeout_seconds if fallback_cfg else 60,
            )

        return provider, model, timeout, fallback

    async def _get_task_policy(self, task_type: str) -> dict[str, Any]:
        if self.db is None:
            return {**DEFAULT_TASK_POLICIES.get(task_type, DEFAULT_TASK_POLICIES["copy_generation"]), "fallback_enabled": True}
        result = await self.db.execute(select(LLMTaskPolicy).where(LLMTaskPolicy.task_type == task_type))
        policy = result.scalar_one_or_none()
        if policy:
            return {
                "routing_mode": policy.routing_mode,
                "primary_provider": policy.primary_provider,
                "primary_model": policy.primary_model,
                "fallback_provider": policy.fallback_provider,
                "fallback_model": policy.fallback_model,
                "fallback_enabled": policy.fallback_enabled,
            }
        return {**DEFAULT_TASK_POLICIES.get(task_type, DEFAULT_TASK_POLICIES["copy_generation"]), "fallback_enabled": True}

    async def _get_provider_config(self, provider_name: str, model_name: str) -> LLMProviderConfig | None:
        if self.db is None:
            for row in DEFAULT_PROVIDER_ROWS:
                if row["provider_name"] == provider_name and row["model_name"] == model_name:
                    return LLMProviderConfig(**row)
            return None
        result = await self.db.execute(
            select(LLMProviderConfig).where(
                LLMProviderConfig.provider_name == provider_name,
                LLMProviderConfig.model_name == model_name,
            )
        )
        return result.scalar_one_or_none()


def parse_json_output(raw: str) -> dict | list:
    text = raw.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)
