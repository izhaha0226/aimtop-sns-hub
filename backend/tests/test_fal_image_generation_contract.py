import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException

from routes import ai as ai_routes
from schemas.ai import GenerateImageRequest
from services import image_service
from services.image_service import FalConfigurationError, FalEmptyResponseError


class FalImageGenerationServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_missing_fal_key_raises_configuration_error_before_network(self):
        with patch("services.image_service.get_runtime_setting", new=AsyncMock(return_value="")):
            with self.assertRaises(FalConfigurationError):
                await image_service.generate_image("premium sns visual")

    async def test_empty_fal_response_is_not_reported_as_key_configuration_error(self):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"images": [], "seed": 123}

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                self.timeout = kwargs.get("timeout")

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with patch("services.image_service.get_runtime_setting", new=AsyncMock(return_value="fal-test-key")):
            with patch("services.image_service.httpx.AsyncClient", FakeAsyncClient):
                with self.assertRaises(FalEmptyResponseError):
                    await image_service.generate_image("premium sns visual")


class FalImageGenerationRouteTest(unittest.IsolatedAsyncioTestCase):
    def _request(self):
        return GenerateImageRequest(prompt="premium Korean SNS visual", size="1024x1024", quality="medium")

    async def test_missing_key_maps_to_operator_configuration_400(self):
        with patch.object(ai_routes, "generate_image", new=AsyncMock(side_effect=FalConfigurationError("missing"))):
            with self.assertRaises(HTTPException) as ctx:
                await ai_routes.api_generate_image(self._request())
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("FAL_KEY/FAL_API_KEY", ctx.exception.detail)

    async def test_timeout_maps_to_504_before_browser_timeout(self):
        with patch.object(ai_routes, "generate_image", new=AsyncMock(side_effect=httpx.TimeoutException("slow"))):
            with self.assertRaises(HTTPException) as ctx:
                await ai_routes.api_generate_image(self._request())
        self.assertEqual(ctx.exception.status_code, 504)
        self.assertIn("시간 초과", ctx.exception.detail)

    async def test_empty_fal_response_maps_to_bad_gateway_not_key_error(self):
        with patch.object(ai_routes, "generate_image", new=AsyncMock(side_effect=FalEmptyResponseError("no url"))):
            with self.assertRaises(HTTPException) as ctx:
                await ai_routes.api_generate_image(self._request())
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("이미지 URL", ctx.exception.detail)

    async def test_success_response_preserves_media_url_contract_fields(self):
        payload = {"image_url": "https://fal.example/image.png", "seed": 7, "model_used": "openai/gpt-image-2"}
        with patch.object(ai_routes, "generate_image", new=AsyncMock(return_value=payload)):
            response = await ai_routes.api_generate_image(self._request())
        self.assertEqual(response.image_url, payload["image_url"])
        self.assertEqual(response.seed, payload["seed"])
        self.assertEqual(response.model_used, payload["model_used"])


if __name__ == "__main__":
    unittest.main()
