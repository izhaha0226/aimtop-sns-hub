from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTENTS_PAGE = PROJECT_ROOT / "frontend/src/app/(main)/contents/page.tsx"
CONTENT_DETAIL_PAGE = PROJECT_ROOT / "frontend/src/app/(main)/contents/[id]/page.tsx"
HEADER = PROJECT_ROOT / "frontend/src/components/layout/Header.tsx"
PLANNER_PAGE = PROJECT_ROOT / "frontend/src/app/(main)/growth/planner/page.tsx"
CONTENTS_ROUTE = PROJECT_ROOT / "backend/routes/contents.py"


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

    def test_header_does_not_treat_content_detail_id_as_client_id(self):
        source = HEADER.read_text()

        self.assertIn('usePathname', source)
        self.assertIn('pathname.startsWith("/clients/")', source)
        self.assertIn('routeClientId = useMemo', source)
        self.assertRegex(
            source,
            re.compile(r"if \(!pathname\.startsWith\(\"/clients/\"\)\) return \"\"", re.DOTALL),
        )

    def test_content_detail_shows_client_and_channel_account_context(self):
        source = CONTENT_DETAIL_PAGE.read_text()

        self.assertIn('콘텐츠 소속', source)
        self.assertIn('client_id', source)
        self.assertIn('발행 계정', source)
        self.assertIn('account_id', source)

    def test_backend_contents_list_requires_client_id_scope(self):
        source = CONTENTS_ROUTE.read_text()

        self.assertIn('client_id: uuid.UUID = Query(...)', source)
        self.assertNotIn('client_id: uuid.UUID | None = Query(None)', source)

    def test_planner_does_not_restore_other_clients_latest_plan(self):
        source = PLANNER_PAGE.read_text()

        self.assertNotIn('const fallback = await operationPlansService.list()', source)
        self.assertNotIn('fallback.items', source)
        self.assertIn('setPlan(null)', source)
        self.assertIn('setSavedPlan(null)', source)
        self.assertIn('setLastRequest(null)', source)


if __name__ == "__main__":
    unittest.main()
