import unittest

from services.sns_oauth import PLATFORM_CONFIGS


class SNSOAuthScopeTest(unittest.TestCase):
    def test_facebook_connect_scope_omits_unapproved_write_permissions(self):
        scopes = set(PLATFORM_CONFIGS["facebook"]["scopes"].split(","))

        self.assertIn("pages_show_list", scopes)
        self.assertIn("pages_read_engagement", scopes)
        self.assertNotIn("pages_manage_posts", scopes)
        self.assertNotIn("pages_manage_metadata", scopes)

    def test_instagram_connect_scope_omits_unapproved_instagram_permissions(self):
        scopes = set(PLATFORM_CONFIGS["instagram"]["scopes"].split(","))

        self.assertIn("pages_show_list", scopes)
        self.assertIn("pages_read_engagement", scopes)
        self.assertNotIn("instagram_basic", scopes)
        self.assertNotIn("instagram_content_publish", scopes)

    def test_threads_connect_scope_omits_unapproved_threads_permissions(self):
        scopes = set(PLATFORM_CONFIGS["threads"]["scopes"].split(","))

        self.assertIn("pages_show_list", scopes)
        self.assertIn("pages_read_engagement", scopes)
        self.assertNotIn("instagram_basic", scopes)
        self.assertNotIn("threads_basic", scopes)
        self.assertNotIn("threads_content_publish", scopes)


if __name__ == "__main__":
    unittest.main()
