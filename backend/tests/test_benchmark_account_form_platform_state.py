from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_PAGE = PROJECT_ROOT / "frontend/src/app/(main)/clients/[id]/benchmark/page.tsx"


class BenchmarkAccountFormPlatformStateTest(unittest.TestCase):
    def test_registration_form_drafts_are_scoped_per_platform(self):
        source = BENCHMARK_PAGE.read_text()

        self.assertIn("formsByPlatform", source)
        self.assertIn("setFormsByPlatform", source)
        self.assertRegex(
            source,
            re.compile(r"const\s+form\s*=\s*formsByPlatform\[platform\]", re.DOTALL),
        )
        self.assertRegex(
            source,
            re.compile(r"\[platform\]:\s*\{\s*\.\.\.\(prev\[platform\]", re.DOTALL),
        )
        self.assertRegex(
            source,
            re.compile(r"resetCurrentForm[\s\S]*\[platform\]:\s*emptyAccountForm\(\)", re.DOTALL),
        )

    def test_registration_text_inputs_have_platform_scoped_identity(self):
        source = BENCHMARK_PAGE.read_text()

        for field in ("handle", "metadata", "memo"):
            self.assertIn('key={`${platform}-' + field + '`}', source)
            self.assertIn('id={`benchmark-${platform}-' + field + '`}', source)
            self.assertIn('name={`benchmark-${platform}-' + field + '`}', source)
            self.assertIn('data-testid={`benchmark-${platform}-' + field + '`}', source)

    def test_benchmark_center_has_operational_actions(self):
        source = BENCHMARK_PAGE.read_text()

        self.assertIn("handleRefreshAllAccounts", source)
        self.assertIn("handleDeleteAccount", source)
        self.assertIn("handleCreateManualPost", source)
        self.assertIn("manualPostByAccount", source)
        self.assertIn("benchmarkingService.deleteAccount", source)
        self.assertIn("benchmarkingService.createManualPost", source)
        self.assertIn("전체 새로고침", source)
        self.assertIn("수동 포스트 추가", source)


if __name__ == "__main__":
    unittest.main()
