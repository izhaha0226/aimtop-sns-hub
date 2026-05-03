from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHANNELS_SERVICE = PROJECT_ROOT / "frontend/src/services/channels.ts"
CONTENT_DETAIL_PAGE = PROJECT_ROOT / "frontend/src/app/(main)/contents/[id]/page.tsx"


class InstagramPublishReadinessFrontendGuardTest(unittest.TestCase):
    def test_instagram_without_account_id_is_not_auto_publish_ready(self):
        source = CHANNELS_SERVICE.read_text()

        self.assertIn('channel.channel_type === "instagram" && !channel.account_id', source)
        self.assertIn('Instagram 발행 계정 ID 없음', source)
        self.assertIn('isChannelAutoPublishReady', source)

    def test_content_detail_uses_channel_readiness_not_type_only_support(self):
        source = CONTENT_DETAIL_PAGE.read_text()

        self.assertIn('isChannelAutoPublishReady(channel)', source)
        self.assertIn('getAutoPublishBlockReason(channel)', source)
        self.assertIn('selectedChannelAutoPublishBlockReason', source)
        self.assertNotIn('unsupported = !isAutoPublishSupported(channel.channel_type)', source)


if __name__ == "__main__":
    unittest.main()
