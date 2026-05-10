from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid

from routes.content_topics import create_content_topic
from schemas.content_topic import ContentTopicCreate


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTENT_TOPICS_ROUTE = PROJECT_ROOT / "backend/routes/content_topics.py"
CONTENT_TOPIC_PAGE = PROJECT_ROOT / "frontend/src/app/(main)/contents/new/topic/page.tsx"


class FakeDB:
    def __init__(self):
        self.added = None
        self.committed = False
        self.refreshed = False

    def add(self, item):
        self.added = item

    async def commit(self):
        self.committed = True

    async def refresh(self, item):
        self.refreshed = True


class ContentTopicRuntimeGuardsTest(unittest.IsolatedAsyncioTestCase):
    def test_create_topic_pops_source_metadata_before_constructor(self):
        source = CONTENT_TOPICS_ROUTE.read_text()

        self.assertIn('metadata = data.pop("source_metadata", None) or {}', source)
        self.assertNotIn('metadata = data.get("source_metadata") or {}', source)
        self.assertIn("ContentTopic(**data, source_metadata=metadata", source)

    def test_topic_page_has_visible_error_surface_for_storyline_generation(self):
        source = CONTENT_TOPIC_PAGE.read_text()

        self.assertIn("5장 내용 먼저 생성", source)
        self.assertIn("setError(message)", source)
        self.assertIn("처리 중 오류가 발생했습니다", source)

    async def test_create_topic_with_channels_does_not_duplicate_source_metadata_kwarg(self):
        db = FakeDB()
        user_id = uuid.uuid4()
        body = ContentTopicCreate(
            client_id=uuid.uuid4(),
            title="5장 내용 생성 회귀 테스트",
            brief="source_metadata와 channels가 함께 있어도 생성되어야 한다",
            channels=["instagram", "facebook"],
            source_metadata={"origin": "test"},
        )

        topic = await create_content_topic(body=body, db=db, current_user=SimpleNamespace(id=user_id))

        self.assertIs(topic, db.added)
        self.assertTrue(db.committed)
        self.assertTrue(db.refreshed)
        self.assertEqual(topic.author_id, user_id)
        self.assertEqual(topic.source_metadata["origin"], "test")
        self.assertEqual(topic.source_metadata["channels"], ["instagram", "facebook"])


if __name__ == "__main__":
    unittest.main()
