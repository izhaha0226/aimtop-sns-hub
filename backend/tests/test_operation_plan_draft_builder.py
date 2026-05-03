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

    def test_draft_title_omits_redundant_brand_prefix_and_uses_readable_sequence(self):
        plan_payload = self._approved_plan_payload()

        drafts = build_content_draft_specs_from_plan(
            operation_plan_id="plan-123",
            status="approved",
            plan_payload=plan_payload,
            client_id="client-123",
            author_id="author-123",
        )

        first = drafts[0]
        self.assertNotIn("[아임탑]", first["title"])
        self.assertRegex(first["title"], r"^2026-06 · 1주차 · [a-z_]+ · .+ · 01$")
        self.assertEqual(first["source_metadata"]["sequence"], 1)
        self.assertEqual(first["source_metadata"]["display_title"], first["title"])

    def test_draft_body_has_topic_specific_marketing_copy_hashtags_and_image_prompt(self):
        plan_payload = self._approved_plan_payload()

        drafts = build_content_draft_specs_from_plan(
            operation_plan_id="plan-123",
            status="approved",
            plan_payload=plan_payload,
            client_id="client-123",
            author_id="author-123",
        )

        first = drafts[0]
        text = first["text"]
        metadata = first["source_metadata"]
        self.assertIn("주제:", text)
        self.assertIn(plan_payload["weekly_plan"][0]["theme"], text)
        self.assertIn("설명:", text)
        self.assertIn("훅:", text)
        self.assertIn("본문:", text)
        self.assertIn("CTA:", text)
        self.assertIn("병원/프랜차이즈", text)
        self.assertIn("B2B SNS 자동화", text)
        self.assertGreaterEqual(len(first["hashtags"]), 5)
        self.assertTrue(any("문의" in tag or "브랜드" in tag for tag in first["hashtags"]))
        self.assertIn("image_prompt", metadata)
        self.assertIn(plan_payload["weekly_plan"][0]["theme"], metadata["image_prompt"])
        self.assertIn("visual_direction", metadata)

    def test_builds_draft_specs_from_saved_draft_plan_without_approval_gate(self):
        plan_payload = self._approved_plan_payload()

        drafts = build_content_draft_specs_from_plan(
            operation_plan_id="plan-123",
            status="draft",
            plan_payload=plan_payload,
            client_id="client-123",
            author_id="author-123",
        )

        self.assertGreater(len(drafts), 0)
        self.assertTrue(all(item["status"] == "draft" for item in drafts))

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
