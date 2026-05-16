import unittest
import uuid

from pydantic import ValidationError

from models.threads_automation import ThreadsActionLog
from schemas.auth_identity import AuthIdentityCreateRequest, AuthIdentityResponse
from schemas.threads_automation import DraftCreateRequest
from services.threads_automation_service import ThreadsAutomationService


class _Rule:
    keywords_json = ["AI", "marketing"]
    hashtags_json = ["#automation"]
    competitor_handles_json = ["@reference"]


class ThreadsAutomationContractTest(unittest.TestCase):
    def test_auth_identity_schema_has_no_token_fields(self):
        request_fields = set(AuthIdentityCreateRequest.model_fields)
        response_fields = set(AuthIdentityResponse.model_fields)

        self.assertNotIn("access_token", request_fields)
        self.assertNotIn("refresh_token", request_fields)
        self.assertNotIn("token", request_fields)
        self.assertNotIn("access_token", response_fields)
        self.assertNotIn("refresh_token", response_fields)
        self.assertNotIn("token", response_fields)

    def test_draft_action_type_is_limited_to_safe_mvp_actions(self):
        client_id = uuid.uuid4()
        self.assertEqual(DraftCreateRequest(client_id=client_id, action_type="comment").action_type, "comment")
        with self.assertRaises(ValidationError):
            DraftCreateRequest(client_id=client_id, action_type="publish")

    def test_fit_score_is_deterministic_without_external_api(self):
        svc = ThreadsAutomationService(db=None)
        score = svc._score_fit("AI automation workflow", "@someone", _Rule())

        self.assertGreater(score, 0.55)
        self.assertLessEqual(score, 1.0)

    def test_action_log_defaults_keep_external_write_disabled(self):
        action = ThreadsActionLog(client_id=uuid.uuid4(), action_type="like")

        self.assertFalse(action.external_write_enabled)


if __name__ == "__main__":
    unittest.main()
