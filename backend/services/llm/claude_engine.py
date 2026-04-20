from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from services.llm.base import LLMGenerationResult

logger = logging.getLogger(__name__)


class ClaudeEngine:
    provider_name = "claude"

    async def generate_text(self, prompt: str, model: str | None = None, timeout: int = 60, **_: Any) -> LLMGenerationResult:
        started = time.perf_counter()
        command = ["claude", "--print", "--max-turns", "1"]
        if model:
            command.extend(["--model", model])
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(input=prompt.encode("utf-8")), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise TimeoutError(f"Claude CLI timed out after {timeout}s")

        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8").strip() if stderr else "unknown error"
            logger.error("Claude CLI error (rc=%d): %s", proc.returncode, err_msg)
            raise RuntimeError(f"Claude CLI failed: {err_msg}")

        return LLMGenerationResult(
            provider=self.provider_name,
            model=model or "default",
            output_text=stdout.decode("utf-8").strip(),
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
