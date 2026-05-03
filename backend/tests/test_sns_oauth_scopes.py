import unittest

from services.sns_oauth import PLATFORM_CONFIGS


class SNSOAuthScopeTest(unittest.TestCase):
    def test_facebook_connect_scope_omits_unapproved_write_permissions(self):
        scopes = set(PLATFORM_CONFIGS["facebook"]["scopes"].split(","))

        self.assertIn("pages_show_list", scopes)
        self.assertIn("pages_read_engagement", scopes)
        self.assertNotIn("pages_manage_posts", scopes)
        self.assertNotIn("pages_manage_metadata", scopes)


if __name__ == "__main__":
    unittest.main()
