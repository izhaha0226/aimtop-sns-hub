import unittest

from services.content_operation_planner import (
    OperationPlanRequestData,
    build_brand_study,
    build_fallback_operation_plan,
    build_supermarketing_strategy,
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

    def test_fallback_plan_passes_through_supermarketing_strategy_first(self):
        req = OperationPlanRequestData(
            brand_name="탑클래스",
            product_summary="인플루언서 재능 마켓과 가정의달 선물 오퍼",
            target_audience="30~40대 부모와 선물 구매자",
            goals=["선물 수요 전환", "브랜드 신뢰"],
            channels=["instagram", "facebook", "threads"],
            benchmark_brands=["클래스101", "크몽"],
            month="2026-05",
        )

        strategy = build_supermarketing_strategy(req)
        plan = build_fallback_operation_plan(req)

        self.assertGreaterEqual(len(strategy), 4)
        self.assertEqual(plan["supermarketing_strategy"], strategy)
        self.assertTrue(any("Brief lock" in item for item in plan["supermarketing_strategy"]))
        self.assertTrue(any("Benchmark rule" in item for item in plan["supermarketing_strategy"]))
        self.assertTrue(any("승인 전 외부 업로드" in item for item in plan["supermarketing_strategy"]))

    def test_benchmark_insights_are_reflected_honestly(self):
        req = OperationPlanRequestData(
            brand_name="탑클래스",
            product_summary="인플루언서 재능 마켓과 가정의달 선물 오퍼",
            channels=["instagram"],
            benchmark_brands=["클래스101"],
            benchmark_insights=[
                {
                    "brand": "클래스101",
                    "channel": "instagram",
                    "source_status": "live_collected_proxy_views",
                    "support_level": "live",
                    "evidence_count": 6,
                    "hook_patterns": ["질문형 훅"],
                    "format_patterns": ["카드뉴스"],
                    "cta_patterns": ["저장 유도"],
                    "apply_points": ["구조만 변환"],
                    "warnings": ["복제 금지"],
                }
            ],
        )

        plan = build_fallback_operation_plan(req)

        self.assertEqual(plan["benchmark_source_status"], "live_or_cached_evidence")
        self.assertEqual(plan["benchmark_insights"][0]["evidence_count"], 6)
        self.assertIn("증거 6개", plan["benchmark_notes"][0])

    def test_brand_study_locks_primary_offer_before_weekly_plan(self):
        req = OperationPlanRequestData(
            brand_name="탑클래스",
            product_summary="김기원VIP멤버십, 프리미엄 입시/학습 관리 프로그램",
            target_audience="상위권 도약을 원하는 학생과 학부모",
            goals=["VIP 멤버십 상담 신청", "신뢰 형성"],
            channels=["instagram", "kakao", "blog"],
            benchmark_brands=["클래스101"],
            month="2026-05",
        )

        study = build_brand_study(req)
        strategy = build_supermarketing_strategy(req)
        plan = build_fallback_operation_plan(req)

        self.assertEqual(plan["primary_offer"], "김기원VIP멤버십")
        self.assertTrue(any("김기원VIP멤버십" in item for item in study))
        self.assertTrue(any("김기원VIP멤버십" in item for item in strategy))
        self.assertTrue(any("김기원VIP멤버십" in item for item in plan["product_angles"]))
        self.assertTrue(any("김기원VIP멤버십" in week["theme"] for week in plan["weekly_plan"]))
        self.assertTrue(any("대표 홍보 오퍼" in item for item in plan["approval_checklist"]))


if __name__ == "__main__":
    unittest.main()
