import unittest

from services.content_operation_planner import (
    OperationPlanRequestData,
    build_fallback_operation_plan,
)


class ContentOperationPlannerTest(unittest.TestCase):
    def test_fallback_plan_calculates_channel_specific_monthly_volume(self):
        req = OperationPlanRequestData(
            brand_name="메가커피",
            product_summary="여름 시즌 신메뉴와 매장 방문 프로모션",
            target_audience="20대 대학생과 직장인",
            goals=["매장 방문", "신메뉴 인지도"],
            channels=["instagram", "threads", "blog"],
            benchmark_brands=["스타벅스", "컴포즈커피"],
            month="2026-06",
            season_context="초여름, 기말고사, 장마 시작",
        )

        plan = build_fallback_operation_plan(req)

        self.assertEqual(plan["brand_name"], "메가커피")
        self.assertEqual(plan["month"], "2026-06")
        self.assertEqual(plan["benchmark_source_status"], "manual_or_pending")
        self.assertIn("초여름", plan["seasonal_context"])
        self.assertEqual(plan["monthly_volume"]["instagram"], 16)
        self.assertEqual(plan["monthly_volume"]["threads"], 20)
        self.assertEqual(plan["monthly_volume"]["blog"], 4)
        self.assertGreaterEqual(len(plan["weekly_plan"]), 4)
        self.assertTrue(any("스타벅스" in item for item in plan["benchmark_notes"]))

    def test_fallback_plan_includes_approval_checklist_and_next_actions(self):
        req = OperationPlanRequestData(
            brand_name="아임탑",
            product_summary="B2B 마케팅 자동화 솔루션",
            target_audience="병원/프랜차이즈 마케팅 담당자",
            goals=["문의 확보"],
            channels=["linkedin", "youtube", "kakao"],
            benchmark_brands=["HubSpot"],
            month="2026-11",
            season_context="블랙프라이데이와 연말 예산 편성 시즌",
        )

        plan = build_fallback_operation_plan(req)

        self.assertIn("approval_checklist", plan)
        self.assertIn("next_actions", plan)
        self.assertTrue(any("승인" in item for item in plan["approval_checklist"]))
        self.assertTrue(any("draft" in item.lower() or "초안" in item for item in plan["next_actions"]))
        self.assertEqual(plan["monthly_volume"]["linkedin"], 6)
        self.assertEqual(plan["monthly_volume"]["youtube"], 8)
        self.assertEqual(plan["monthly_volume"]["kakao"], 6)


if __name__ == "__main__":
    unittest.main()
