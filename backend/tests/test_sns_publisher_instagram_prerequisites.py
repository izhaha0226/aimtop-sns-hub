import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services.sns_publisher import SNSPublisher


class SNSPublisherInstagramPrerequisitesTest(unittest.IsolatedAsyncioTestCase):
    async def test_instagram_publish_fails_before_graph_call_when_account_id_missing(self):
        publisher = SNSPublisher()
        account = SimpleNamespace(
            access_token="encrypted-token",
            account_id=None,
            extra_data={},
        )
        content = SimpleNamespace(
            title="테스트",
            text="본문",
            media_urls=["https://example.com/image.jpg"],
            hashtags=[],
        )

        with patch("services.sns_publisher.decrypt_token", return_value="token"), patch(
            "services.sns_publisher.httpx.AsyncClient"
        ) as async_client:
            with self.assertRaisesRegex(ValueError, "Instagram 발행 계정 ID"):
                await publisher._publish_instagram(account, content)

        async_client.assert_not_called()

    async def test_instagram_publish_fails_before_graph_call_when_media_missing(self):
        publisher = SNSPublisher()
        account = SimpleNamespace(
            access_token="encrypted-token",
            account_id="17890000000000000",
            extra_data={},
        )
        content = SimpleNamespace(
            title="테스트",
            text="본문",
            media_urls=[],
            hashtags=[],
        )

        with patch("services.sns_publisher.decrypt_token", return_value="token"), patch(
            "services.sns_publisher.httpx.AsyncClient"
        ) as async_client:
            with self.assertRaisesRegex(ValueError, "이미지 URL"):
                await publisher._publish_instagram(account, content)

        async_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
