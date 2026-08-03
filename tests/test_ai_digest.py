from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest

from unittest.mock import patch

from src.ai_digest import (
    Item,
    candidate_excerpt,
    categorize_and_score,
    deduplicate,
    extract_article_text,
    parse_datetime,
    parse_feed,
    resolve_editor_config,
    split_source_pools,
    validate_chinese_items,
)


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

    def test_ai_industry_news_has_a_latest_dynamics_category(self):
        config = json.loads(Path("config/sources.json").read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc)
        item = Item(
            title="人工智能公司完成新一轮融资并宣布战略收购",
            url="https://example.cn/news",
            source="中文来源",
            published=now,
        )
        categorize_and_score(item, config["categories"], now)
        self.assertEqual(item.category_id, "dynamics")

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

    def test_distinct_chinese_titles_are_not_collapsed(self):
        now = datetime.now(timezone.utc)
        items = [
            Item("英伟达发布推理平台", "https://example.cn/infra", "A", now),
            Item("智谱发布新一代大模型", "https://example.cn/model", "B", now),
        ]
        self.assertEqual(len(deduplicate(items)), 2)

    @patch("src.ai_digest.fetch")
    def test_feed_items_keep_source_pool_and_credibility(self, mocked_fetch):
        mocked_fetch.return_value = b"""<?xml version='1.0' encoding='UTF-8'?>
        <rss><channel><item>
          <title>\xe8\x8b\xb1\xe4\xbc\x9f\xe8\xbe\xbe\xe5\x8f\x91\xe5\xb8\x83\xe4\xb8\xad\xe6\x96\x87\xe6\x8e\xa8\xe7\x90\x86\xe6\x8a\xa5\xe5\x91\x8a</title>
          <link>https://example.cn/infra</link>
          <pubDate>Mon, 03 Aug 2026 01:00:00 GMT</pubDate>
          <description>\xe4\xb8\xad\xe6\x96\x87\xe6\x91\x98\xe8\xa6\x81</description>
        </item></channel></rss>"""
        source = {
            "type": "feed",
            "name": "\xe4\xb8\xad\xe6\x96\x87\xe6\x9d\xa5\xe6\xba\x90",
            "url": "https://example.cn/feed",
            "pool": "chinese",
            "credibility": 5,
        }
        item = parse_feed(source, 10)[0]
        self.assertEqual(item.pool, "chinese")
        self.assertEqual(item.credibility, 5)

    def test_extract_article_text_ignores_scripts_and_keeps_chinese_body(self):
        raw = """
        <html><head><script>忽略这段脚本</script></head><body>
          <nav>网站导航</nav><article><h1>推理平台更新</h1>
          <p>这是正文内容，介绍大模型推理基础设施的重要更新。</p></article>
        </body></html>
        """.encode()
        text = extract_article_text(raw)
        self.assertIn("这是正文内容", text)
        self.assertNotIn("忽略这段脚本", text)

    def test_source_pools_keep_international_items_out_of_chinese_candidates(self):
        now = datetime.now(timezone.utc)
        international = Item("English radar", "https://global.test/a", "Global", now)
        chinese = Item(
            "中文人工智能资讯",
            "https://china.test/a",
            "中文来源",
            now,
            pool="chinese",
        )
        radar, chinese_items = split_source_pools([international, chinese])
        self.assertEqual([item.title for item in radar], ["English radar"])
        self.assertEqual([item.title for item in chinese_items], ["中文人工智能资讯"])

    @patch("src.ai_digest.fetch")
    def test_chinese_item_requires_valid_fetched_article_body(self, mocked_fetch):
        mocked_fetch.return_value = (
            "<html><article><h1>英伟达发布推理平台</h1><p>"
            + "这是一篇介绍大模型推理基础设施、部署效率和算力成本变化的完整中文报道。" * 20
            + "</p></article></html>"
        ).encode()
        now = datetime.now(timezone.utc)
        item = Item(
            "英伟达发布推理平台",
            "https://example.cn/infra",
            "中文来源",
            now,
            summary="这项更新关注推理基础设施。",
            pool="chinese",
            credibility=5,
            category_id="infra",
            category_label="AI Infra",
            relevance=6,
        )
        candidates, rejection_counts = validate_chinese_items([item], timeout=10)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].url, "https://example.cn/infra")
        self.assertGreater(len(candidates[0].body), 120)
        self.assertEqual(rejection_counts, {})

    def test_placeholder_feed_summary_uses_article_excerpt(self):
        candidate = type(
            "Candidate",
            (),
            {
                "summary": "点击查看原文>",
                "body": (
                    "网站导航 登录 / 注册 AI摘要 核心内容："
                    "文章揭示 AI 竞争焦点正从模型能力转向智能体系统的工程化落地能力。"
                    "关键观点：系统需要可编排和可追溯。"
                ),
            },
        )()
        excerpt = candidate_excerpt(candidate)
        self.assertIn("智能体系统的工程化落地能力", excerpt)
        self.assertNotIn("点击查看原文", excerpt)

    def test_github_token_is_not_misused_as_a_retired_model_token(self):
        with patch.dict(
            "os.environ",
            {"GITHUB_TOKEN": "workflow-token", "GITHUB_MODELS_MODEL": "openai/gpt-4.1-mini"},
            clear=True,
        ):
            config = resolve_editor_config()
        self.assertEqual(config["provider_name"], "未配置外部模型")
        self.assertEqual(config["token"], "")
        self.assertEqual(config["endpoint"], "")

    def test_complete_external_editor_config_enables_model_editing(self):
        with patch.dict(
            "os.environ",
            {
                "GITHUB_TOKEN": "workflow-token",
                "LLM_API_KEY": "external-token",
                "LLM_ENDPOINT": "https://llm.example/v1/chat/completions",
                "LLM_MODEL": "example-model",
            },
            clear=True,
        ):
            config = resolve_editor_config()
        self.assertEqual(config["provider_name"], "外部模型")
        self.assertEqual(config["token"], "external-token")


if __name__ == "__main__":
    unittest.main()
