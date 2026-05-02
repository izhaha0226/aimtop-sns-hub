import unittest
from types import SimpleNamespace

from services.benchmark_collector_service import BenchmarkCollectorService


class BenchmarkCollectorServiceSourceQualityTest(unittest.IsolatedAsyncioTestCase):
    def make_service(self):
        class NoChannelBenchmarkCollectorService(BenchmarkCollectorService):
            async def _get_source_channels(self, client_id, platform):
                return []

        return NoChannelBenchmarkCollectorService(db=None)

    async def test_unimplemented_platform_refresh_is_not_reported_as_live_supported(self):
        svc = self.make_service()
        account = SimpleNamespace(
            client_id="client-1",
            platform="kakao",
            handle="brand-channel",
            metadata_json={},
        )

        posts, status = await svc._collect_live_posts(account, top_k=10, window_days=30)

        self.assertEqual(posts, [])
        self.assertEqual(status["status"], "manual_ingest_required")
        self.assertEqual(status["support_level"], "unimplemented")
        self.assertEqual(status["support_label"], "미구현")
        self.assertFalse(status["live_supported"])
        self.assertEqual(status["source_channel_missing_reason"], "kakao 실수집기 미구현")

    async def test_manual_platform_refresh_is_not_reported_as_live_supported(self):
        svc = self.make_service()
        account = SimpleNamespace(
            client_id="client-1",
            platform="threads",
            handle="brand-thread",
            metadata_json={},
        )

        posts, status = await svc._collect_live_posts(account, top_k=10, window_days=30)

        self.assertEqual(posts, [])
        self.assertEqual(status["status"], "manual_ingest_required")
        self.assertEqual(status["support_level"], "manual")
        self.assertEqual(status["support_label"], "수동 확인 필요")
        self.assertFalse(status["live_supported"])
        self.assertEqual(status["source_channel_missing_reason"], "Threads 공개 벤치마킹 안정 API 미지원")


if __name__ == "__main__":
    unittest.main()
