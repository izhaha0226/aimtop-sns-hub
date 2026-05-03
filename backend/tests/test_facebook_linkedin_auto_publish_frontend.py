import unittest
from pathlib import Path

from services.sns_oauth import PLATFORM_CONFIGS

ROOT = Path(__file__).resolve().parents[2]
CHANNELS_TS = ROOT / "frontend" / "src" / "services" / "channels.ts"


class FacebookLinkedInAutoPublishFrontendTest(unittest.TestCase):
    def test_frontend_declares_facebook_and_linkedin_auto_publish_ready_channels(self):
        source = CHANNELS_TS.read_text()
        self.assertRegex(source, r'AUTO_PUBLISH_SUPPORTED_CHANNELS\s*=\s*\[[^\]]*"facebook"')
        self.assertRegex(source, r'AUTO_PUBLISH_SUPPORTED_CHANNELS\s*=\s*\[[^\]]*"linkedin"')
        self.assertIn("Facebook 페이지 ID 없음", source)
        self.assertIn("LinkedIn 작성자 ID 없음", source)


class FacebookPublishScopeTest(unittest.TestCase):
    def test_facebook_publish_scope_includes_pages_manage_posts(self):
        scopes = set(PLATFORM_CONFIGS["facebook"]["scopes"].split(","))

        self.assertIn("pages_show_list", scopes)
        self.assertIn("pages_read_engagement", scopes)
        self.assertIn("pages_manage_posts", scopes)
        self.assertNotIn("pages_manage_metadata", scopes)


if __name__ == "__main__":
    unittest.main()
