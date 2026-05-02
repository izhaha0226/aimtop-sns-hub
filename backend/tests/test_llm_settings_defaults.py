import unittest

from services.llm.router import DEFAULT_PROVIDER_ROWS, DEFAULT_TASK_POLICIES


class LLMSettingsDefaultsTest(unittest.TestCase):
    def test_default_provider_rows_include_latest_gpt_models(self):
        models = {row["model_name"]: row for row in DEFAULT_PROVIDER_ROWS}

        self.assertIn("gpt-5.5", models)
        self.assertIn("gpt-5.4", models)
        self.assertIn("gpt-5.4-mini", models)
        self.assertEqual(models["gpt-5.5"]["provider_name"], "gpt")
        self.assertTrue(models["gpt-5.5"]["supports_reasoning"])

    def test_default_task_policies_use_latest_gpt_primary_and_claude_fallback(self):
        self.assertGreaterEqual(len(DEFAULT_TASK_POLICIES), 5)
        for task_type, policy in DEFAULT_TASK_POLICIES.items():
            with self.subTest(task_type=task_type):
                self.assertEqual(policy["primary_provider"], "gpt")
                self.assertEqual(policy["primary_model"], "gpt-5.5")
                self.assertEqual(policy["fallback_provider"], "claude")
                self.assertTrue(policy["fallback_model"].startswith("claude-"))


if __name__ == "__main__":
    unittest.main()
