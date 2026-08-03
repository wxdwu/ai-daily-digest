from datetime import datetime, timedelta, timezone
import unittest

from src.ai_digest import Item, categorize_and_score, deduplicate, parse_datetime


CATEGORIES = [
    {"id": "models", "label": "大模型", "keywords": {"language model": 3, "gpt": 4}},
    {"id": "infra", "label": "AI Infra", "keywords": {"inference": 4, "gpu": 3}},
    {"id": "agents", "label": "AI Agent", "keywords": {"ai agent": 5, "tool use": 4}},
]


class DigestTests(unittest.TestCase):
    def test_parse_rfc_and_iso_dates(self):
        self.assertEqual(parse_datetime("Mon, 20 Jul 2026 08:00:00 GMT").hour, 8)
        self.assertEqual(parse_datetime("2026-07-20T08:00:00Z").tzinfo, timezone.utc)

    def test_category_and_score(self):
        now = datetime.now(timezone.utc)
        item = Item(
            title="Faster GPU inference for language model serving",
            url="https://example.com/a",
            source="Example",
            published=now - timedelta(hours=2),
            source_weight=3,
        )
        categorize_and_score(item, CATEGORIES, now)
        self.assertEqual(item.category_id, "infra")
        self.assertGreater(item.score, item.relevance)

    def test_title_signal_outweighs_incidental_summary_keyword(self):
        now = datetime.now(timezone.utc)
        item = Item(
            title="A practical GPU inference guide",
            url="https://example.com/infra",
            source="Example",
            published=now,
            summary="A language model is mentioned once in a long aside.",
        )
        categorize_and_score(item, CATEGORIES, now)
        self.assertEqual(item.category_id, "infra")
        self.assertGreater(item.relevance, 5)

    def test_deduplicate_urls_and_similar_titles(self):
        now = datetime.now(timezone.utc)
        items = [
            Item("Introducing a new AI agent", "https://a.test/post?utm=1", "A", now, source_weight=2),
            Item("Introducing the new AI agent", "https://b.test/post", "B", now, source_weight=1),
            Item("GPU kernels get faster", "https://a.test/gpu?utm=1", "A", now, source_weight=3),
            Item("Same URL should vanish", "https://a.test/gpu?other=2", "C", now, source_weight=1),
        ]
        result = deduplicate(items)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].title, "GPU kernels get faster")


if __name__ == "__main__":
    unittest.main()
