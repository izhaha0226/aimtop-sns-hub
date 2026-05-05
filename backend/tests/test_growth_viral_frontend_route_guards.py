from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GROWTH_ROUTE = PROJECT_ROOT / "backend/routes/growth.py"
GROWTH_PAGE = PROJECT_ROOT / "frontend/src/app/(main)/growth/page.tsx"


class GrowthViralFrontendRouteGuardsTest(unittest.TestCase):
    def test_backend_exposes_client_scoped_viral_strategy_endpoint(self):
        source = GROWTH_ROUTE.read_text()

        self.assertIn('@router.get("/viral-strategy")', source)
        self.assertIn('client_id: uuid.UUID = Query(...)', source)
        self.assertIn('get_viral_strategy(client_id=client_id', source)

    def test_growth_page_uses_selected_client_and_renders_viral_section(self):
        source = GROWTH_PAGE.read_text()

        self.assertIn('useSelectedClient', source)
        self.assertIn('selectedClientId', source)
        self.assertIn('/api/v1/growth/viral-strategy', source)
        self.assertIn('바이럴 루프', source)
        self.assertIn('공유율', source)


if __name__ == "__main__":
    unittest.main()
