import unittest

from services.content_operation_planner import OperationPlanRequestData, build_fallback_operation_plan
from services.operation_plan_draft_service import (
    OperationPlanDraftError,
    build_content_draft_specs_from_plan,
)


class OperationPlanDraftBuilderTest(unittest.TestCase):
    def _approved_plan_payload(self):
        req = OperationPlanRequestData(
            brand_name="아임탑",
            product_summary="B2B SNS 자동화 솔루션",
            target_audience="병원/프랜차이즈 마케팅 담당자",
            goals=["문의 확보", "브랜드 신뢰"],
            channels=["instagram", "blog"],
            benchmark_brands=["HubSpot"],
            month="2026-06",
            season_context="상반기 마감 시즌",
        )
        return build_fallback_operation_plan(req)

    def test_builds_weekly_channel_draft_specs_without_uploading(self):
        plan_payload = self._approved_plan_payload()

        drafts = build_content_draft_specs_from_plan(
            operation_plan_id="plan-123",
            status="approved",
            plan_payload=plan_payload,
            client_id="client-123",
            author_id="author-123",
        )

        expected_total = sum(
            channel["count"]
            for week in plan_payload["weekly_plan"]
            for channel in week["channels"]
        )
        self.assertEqual(len(drafts), expected_total)
        first = drafts[0]
        self.assertEqual(first["status"], "draft")
        self.assertEqual(first["client_id"], "client-123")
        self.assertEqual(first["author_id"], "author-123")
        self.assertEqual(first["operation_plan_id"], "plan-123")
        self.assertIsNone(first["scheduled_at"])
        self.assertIsNone(first["channel_connection_id"])
        self.assertIn("외부 업로드 없음", first["source_metadata"]["safety_notes"])
        self.assertEqual(first["source_metadata"]["benchmark_source_status"], "manual_or_pending")
        self.assertIn(first["source_metadata"]["channel_action"], {"manual_required", "token_check_required"})

    def test_rejects_non_approved_operation_plan(self):
        with self.assertRaisesRegex(OperationPlanDraftError, "승인된 운영계획"):
            build_content_draft_specs_from_plan(
                operation_plan_id="plan-123",
                status="pending_approval",
                plan_payload=self._approved_plan_payload(),
                client_id="client-123",
                author_id="author-123",
            )

    def test_requires_client_before_creating_content_records(self):
        with self.assertRaisesRegex(OperationPlanDraftError, "client_id"):
            build_content_draft_specs_from_plan(
                operation_plan_id="plan-123",
                status="approved",
                plan_payload=self._approved_plan_payload(),
                client_id=None,
                author_id="author-123",
            )


if __name__ == "__main__":
    unittest.main()
