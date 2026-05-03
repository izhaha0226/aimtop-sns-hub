import unittest
from datetime import datetime, timezone
from uuid import uuid4

from schemas.channel import ChannelConnectionResponse
from services.sns_oauth import SNSOAuth


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeAsyncClient:
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("/me"):
            return FakeResponse(200, {"id": "user-123", "name": "Facebook User"})
        if url.endswith("/me/accounts"):
            return FakeResponse(200, {"data": []})
        return FakeResponse(404, {})


class FacebookChannelAccountIdentityTest(unittest.IsolatedAsyncioTestCase):
    async def test_facebook_profile_id_is_preserved_when_no_pages_exist(self):
        import services.sns_oauth as oauth_module

        original_client = oauth_module.httpx.AsyncClient
        FakeAsyncClient.calls = []
        oauth_module.httpx.AsyncClient = FakeAsyncClient
        try:
            profile = await SNSOAuth().fetch_account_profile("facebook", "token-redacted")
        finally:
            oauth_module.httpx.AsyncClient = original_client

        self.assertIsNone(profile["account_id"])
        self.assertEqual(profile["account_name"], "Facebook User")
        self.assertEqual(profile["extra_data"]["facebook_profile"]["id"], "user-123")
        self.assertEqual(profile["extra_data"]["pages"], [])

    async def test_facebook_page_id_remains_publish_account_when_pages_exist(self):
        import services.sns_oauth as oauth_module

        class PageAsyncClient(FakeAsyncClient):
            async def get(self, url, **kwargs):
                if url.endswith("/me"):
                    return FakeResponse(200, {"id": "user-123", "name": "Facebook User"})
                if url.endswith("/me/accounts"):
                    return FakeResponse(200, {"data": [{"id": "page-456", "name": "AimTop Page"}]})
                return FakeResponse(404, {})

        original_client = oauth_module.httpx.AsyncClient
        oauth_module.httpx.AsyncClient = PageAsyncClient
        try:
            profile = await SNSOAuth().fetch_account_profile("facebook", "token-redacted")
        finally:
            oauth_module.httpx.AsyncClient = original_client

        self.assertEqual(profile["account_id"], "page-456")
        self.assertEqual(profile["account_name"], "AimTop Page")
        self.assertEqual(profile["extra_data"]["facebook_profile"]["id"], "user-123")
        self.assertEqual(profile["extra_data"]["pages"][0]["id"], "page-456")

    def test_channel_response_exposes_token_free_facebook_identity(self):
        response = ChannelConnectionResponse.model_validate({
            "id": uuid4(),
            "client_id": uuid4(),
            "channel_type": "facebook",
            "account_name": "Facebook User",
            "account_id": None,
            "is_connected": True,
            "connected_at": datetime.now(timezone.utc),
            "token_expires_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "extra_data": {
                "facebook_profile": {"id": "user-123", "name": "Facebook User"},
                "pages": [],
            },
        })
        dumped = response.model_dump()

        self.assertEqual(dumped["display_account_id"], "user-123")
        self.assertEqual(dumped["display_account_name"], "Facebook User")
        self.assertIsNone(dumped["facebook_page_id"])
        self.assertEqual(dumped["facebook_page_count"], 0)
        self.assertNotIn("extra_data", dumped)


if __name__ == "__main__":
    unittest.main()
