from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GROWTH_SERVICE = PROJECT_ROOT / "backend/services/growth_service.py"
GROWTH_PAGE = PROJECT_ROOT / "frontend/src/app/(main)/growth/page.tsx"


class GrowthHubRuntimeGuardsTest(unittest.TestCase):
    def test_content_ideas_does_not_query_removed_content_platform_column(self):
        source = GROWTH_SERVICE.read_text()

        self.assertNotIn("Content.platform", source)
        self.assertIn("Content.target_platform", source)

    def test_ai_backed_growth_buttons_have_deterministic_fallbacks(self):
        source = GROWTH_SERVICE.read_text()

        self.assertIn("build_hashtag_fallback", source)
        self.assertIn("build_content_idea_fallback", source)
        self.assertIn("build_competitor_analysis_fallback", source)
        self.assertIn("FileNotFoundError", source)

    def test_growth_page_surfaces_action_errors_instead_of_silent_button_failure(self):
        source = GROWTH_PAGE.read_text()

        self.assertIn("errorMessage", source)
        self.assertIn("setErrorMessage", source)
        self.assertIn("기능 실행 중 오류", source)


if __name__ == "__main__":
    unittest.main()
