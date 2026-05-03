import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.sns_publisher import SNSPublisher


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="OK"):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        if not self.responses:
            raise AssertionError("No fake response configured")
        return self.responses.pop(0)


class SNSPublisherFacebookLinkedInTest(unittest.IsolatedAsyncioTestCase):
    async def test_supported_platforms_include_facebook_and_linkedin(self):
        self.assertTrue(SNSPublisher.is_supported_platform("facebook"))
        self.assertTrue(SNSPublisher.is_supported_platform("linkedin"))

    async def test_facebook_text_publish_uses_page_feed_and_page_token(self):
        publisher = SNSPublisher()
        account = SimpleNamespace(
            channel_type="facebook",
            access_token="encrypted-user-token",
            account_id="page-123",
            account_name="AIMTOP Page",
            extra_data={"pages": [{"id": "page-123", "access_token": "page-token"}]},
        )
        content = SimpleNamespace(title="제목", text="본문", media_urls=[], hashtags=["aimtop"])
        fake_client = FakeAsyncClient([FakeResponse(200, {"id": "page-123_post-456"})])

        with patch("services.sns_publisher.decrypt_token", return_value="user-token"), patch(
            "services.sns_publisher.httpx.AsyncClient", return_value=fake_client
        ):
            result = await publisher.publish(account, content)

        self.assertEqual(result["platform_post_id"], "page-123_post-456")
        self.assertEqual(result["url"], "https://www.facebook.com/page-123_post-456")
        method, url, kwargs = fake_client.calls[0]
        self.assertEqual(method, "post")
        self.assertEqual(url, "https://graph.facebook.com/v19.0/page-123/feed")
        self.assertEqual(kwargs["data"]["access_token"], "page-token")
        self.assertIn("제목", kwargs["data"]["message"])
        self.assertIn("#aimtop", kwargs["data"]["message"])

    async def test_facebook_image_publish_uses_page_photos_endpoint(self):
        publisher = SNSPublisher()
        account = SimpleNamespace(
            channel_type="facebook",
            access_token="encrypted-user-token",
            account_id="page-123",
            account_name="AIMTOP Page",
            extra_data={"page_access_token": "page-token"},
        )
        content = SimpleNamespace(
            title="제목",
            text="본문",
            media_urls=["https://example.com/card.jpg"],
            hashtags=[],
        )
        fake_client = FakeAsyncClient([FakeResponse(200, {"post_id": "page-123_post-789", "id": "photo-1"})])

        with patch("services.sns_publisher.decrypt_token", return_value="user-token"), patch(
            "services.sns_publisher.httpx.AsyncClient", return_value=fake_client
        ):
            result = await publisher._publish_facebook(account, content)

        self.assertEqual(result["platform_post_id"], "page-123_post-789")
        method, url, kwargs = fake_client.calls[0]
        self.assertEqual(url, "https://graph.facebook.com/v19.0/page-123/photos")
        self.assertEqual(kwargs["data"]["url"], "https://example.com/card.jpg")
        self.assertEqual(kwargs["data"]["published"], "true")

    async def test_facebook_publish_fails_before_graph_call_without_page_id(self):
        publisher = SNSPublisher()
        account = SimpleNamespace(
            channel_type="facebook",
            access_token="encrypted-user-token",
            account_id=None,
            account_name=None,
            extra_data={"page_access_token": "page-token"},
        )
        content = SimpleNamespace(title="제목", text="본문", media_urls=[], hashtags=[])

        with patch("services.sns_publisher.decrypt_token", return_value="user-token"), patch(
            "services.sns_publisher.httpx.AsyncClient"
        ) as async_client:
            with self.assertRaisesRegex(ValueError, "Facebook 페이지 ID"):
                await publisher._publish_facebook(account, content)

        async_client.assert_not_called()

    async def test_linkedin_publish_uses_rest_posts_author_urn(self):
        publisher = SNSPublisher()
        account = SimpleNamespace(
            channel_type="linkedin",
            access_token="encrypted-linkedin-token",
            account_id="person-123",
            account_name="AIMTOP",
            extra_data={},
        )
        content = SimpleNamespace(title="제목", text="본문", media_urls=[], hashtags=["B2B"])
        fake_client = FakeAsyncClient([FakeResponse(201, {"id": "urn:li:share:999"})])

        with patch("services.sns_publisher.decrypt_token", return_value="linkedin-token"), patch(
            "services.sns_publisher.httpx.AsyncClient", return_value=fake_client
        ):
            result = await publisher.publish(account, content)

        self.assertEqual(result["platform_post_id"], "urn:li:share:999")
        self.assertEqual(result["url"], "https://www.linkedin.com/feed/update/urn:li:share:999")
        method, url, kwargs = fake_client.calls[0]
        self.assertEqual(method, "post")
        self.assertEqual(url, "https://api.linkedin.com/rest/posts")
        self.assertEqual(kwargs["json"]["author"], "urn:li:person:person-123")
        self.assertEqual(kwargs["json"]["visibility"], "PUBLIC")
        self.assertIn("Linkedin-Version", kwargs["headers"])
        self.assertIn("제목", kwargs["json"]["commentary"])

    async def test_linkedin_publish_fails_before_api_call_without_author_id(self):
        publisher = SNSPublisher()
        account = SimpleNamespace(
            channel_type="linkedin",
            access_token="encrypted-linkedin-token",
            account_id=None,
            account_name=None,
            extra_data={},
        )
        content = SimpleNamespace(title="제목", text="본문", media_urls=[], hashtags=[])

        with patch("services.sns_publisher.decrypt_token", return_value="linkedin-token"), patch(
            "services.sns_publisher.httpx.AsyncClient"
        ) as async_client:
            with self.assertRaisesRegex(ValueError, "LinkedIn 작성자 ID"):
                await publisher._publish_linkedin(account, content)

        async_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
