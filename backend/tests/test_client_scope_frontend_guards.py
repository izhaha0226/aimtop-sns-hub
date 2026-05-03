from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTENTS_PAGE = PROJECT_ROOT / "frontend/src/app/(main)/contents/page.tsx"
PLANNER_PAGE = PROJECT_ROOT / "frontend/src/app/(main)/growth/planner/page.tsx"


class ClientScopedFrontendGuardsTest(unittest.TestCase):
    def test_contents_page_loads_only_selected_client_contents(self):
        source = CONTENTS_PAGE.read_text()

        self.assertIn('useSelectedClient', source)
        self.assertIn('selectedClientId', source)
        self.assertRegex(
            source,
            re.compile(r"contentsService\.list\([^\)]*client_id:\s*selectedClientId", re.DOTALL),
        )
        self.assertIn('clientLoading', source)

    def test_planner_does_not_restore_other_clients_latest_plan(self):
        source = PLANNER_PAGE.read_text()

        self.assertNotIn('const fallback = await operationPlansService.list()', source)
        self.assertNotIn('fallback.items', source)
        self.assertIn('setPlan(null)', source)
        self.assertIn('setSavedPlan(null)', source)
        self.assertIn('setLastRequest(null)', source)


if __name__ == "__main__":
    unittest.main()
