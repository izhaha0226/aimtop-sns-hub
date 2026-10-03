import unittest
from unittest.mock import AsyncMock, patch

from services import image_service


class FalImageModelDefaultTest(unittest.IsolatedAsyncioTestCase):
    """2026-10-03: 기본 모델 GPT Image 2.5 Flare · medium."""

    async def _capture(self, **kwargs):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"images": [{"url": "https://fal.example/x.png"}], "seed": 1}

        class FakeAsyncClient:
            def __init__(self, *args, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, url, json=None, headers=None):
                captured["url"] = url
                captured["payload"] = json
                return FakeResponse()

        with patch("services.image_service.get_runtime_setting", new=AsyncMock(return_value="fal-test-key")):
            with patch("services.image_service.httpx.AsyncClient", FakeAsyncClient):
                result = await image_service.generate_image("premium sns visual", **kwargs)
        return captured, result

    async def test_default_is_gpt_image_25_medium(self):
        captured, result = await self._capture()
        self.assertTrue(captured["url"].endswith("openai/gpt-image-2.5/flare/text-to-image"))
        self.assertEqual(captured["payload"]["quality"], "medium")
        self.assertEqual(result["model_used"], "openai/gpt-image-2.5/flare/text-to-image")

    async def test_legacy_aliases_route_to_25(self):
        for alias in ("fast", "quality", "gpt-image-2.0", "nano_pro"):
            captured, _ = await self._capture(model=alias)
            self.assertTrue(captured["url"].endswith("openai/gpt-image-2.5/flare/text-to-image"), alias)

    async def test_explicit_quality_is_kept(self):
        captured, _ = await self._capture(quality="high")
        self.assertEqual(captured["payload"]["quality"], "high")



if __name__ == "__main__":
    unittest.main()
