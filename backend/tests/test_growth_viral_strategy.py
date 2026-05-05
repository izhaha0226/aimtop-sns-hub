import unittest
from types import SimpleNamespace

from services.growth_service import GrowthService


class GrowthViralStrategyTest(unittest.TestCase):
    def test_viral_signal_summary_weights_shares_saves_and_benchmark_score(self):
        posts = [
            SimpleNamespace(
                platform="instagram",
                hook_text="고객이 친구에게 공유하는 체크리스트",
                content_text="저장하고 팀에 공유하세요",
                hashtags_json=["#수국차", "#타임세일"],
                view_count=1000,
                like_count=80,
                comment_count=10,
                share_count=30,
                save_count=40,
                benchmark_score=82.0,
                format_type="card_news",
            ),
            SimpleNamespace(
                platform="instagram",
                hook_text="왜 아무도 이걸 말 안 했을까",
                content_text="댓글로 경험을 남겨주세요",
                hashtags_json=["#수국차", "#건강습관"],
                view_count=500,
                like_count=25,
                comment_count=20,
                share_count=5,
                save_count=10,
                benchmark_score=54.0,
                format_type="reels",
            ),
        ]

        summary = GrowthService.build_viral_signal_summary(posts)

        self.assertEqual(summary["sample_size"], 2)
        self.assertEqual(summary["top_platform"], "instagram")
        self.assertGreater(summary["viral_score"], 0)
        self.assertIn("#수국차", summary["top_hashtags"])
        self.assertEqual(summary["top_formats"][0]["format"], "card_news")
        self.assertGreater(summary["share_rate"], 0)
        self.assertGreater(summary["save_rate"], 0)

    def test_viral_blueprint_turns_signals_into_sns_execution_plan(self):
        client = SimpleNamespace(name="용평밸리", industry_category="식품/건강")
        signal_summary = {
            "sample_size": 3,
            "viral_score": 71.5,
            "top_platform": "instagram",
            "top_hashtags": ["#수국차", "#건강습관"],
            "top_hooks": ["고객이 친구에게 공유하는 체크리스트"],
            "top_formats": [{"format": "card_news", "count": 2}],
            "share_rate": 0.035,
            "save_rate": 0.041,
            "comment_rate": 0.02,
        }

        blueprint = GrowthService.build_viral_blueprint(
            client=client,
            platform="instagram",
            signal_summary=signal_summary,
        )

        self.assertEqual(blueprint["client"]["name"], "용평밸리")
        self.assertEqual(blueprint["platform"], "instagram")
        self.assertIn("viral_loop", blueprint)
        self.assertGreaterEqual(len(blueprint["viral_loop"]["stages"]), 4)
        self.assertGreaterEqual(len(blueprint["content_experiments"]), 4)
        self.assertIn("share_rate", blueprint["measurement"]["primary_metrics"])
        self.assertTrue(any("친구" in item["cta"] or "공유" in item["cta"] for item in blueprint["content_experiments"]))


if __name__ == "__main__":
    unittest.main()
