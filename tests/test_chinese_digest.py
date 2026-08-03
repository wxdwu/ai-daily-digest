from datetime import datetime, timezone
import unittest

from src.chinese_digest import (
    ChineseCandidate,
    chinese_ratio,
    event_signature,
    match_topics,
    rank_candidates,
    select_candidates,
    validate_chinese_page,
)


def make_candidate(candidate_id, title, category_id, relevance=4, credibility=3):
    return ChineseCandidate(
        id=candidate_id,
        title=title,
        url=f"https://example.cn/{candidate_id}",
        source="示例中文媒体",
        published=datetime.now(timezone.utc),
        credibility=credibility,
        category_id=category_id,
        category_label={"infra": "AI Infra", "agents": "AI Agent", "models": "大模型"}[category_id],
        relevance=relevance,
        body="这是一篇完整的中文人工智能技术报道。" * 20,
    )


class ChineseValidationTests(unittest.TestCase):
    def test_accepts_substantial_chinese_article(self):
        body = "这是中文人工智能基础设施报道。" * 20
        result = validate_chinese_page("英伟达发布全新推理平台", body, "https://example.cn/post")
        self.assertTrue(result.valid)

    def test_rejects_english_article(self):
        result = validate_chinese_page(
            "New inference platform",
            "This article contains only English words about AI infrastructure. " * 20,
            "https://example.com/post",
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "non_chinese")

    def test_rejects_login_and_captcha_pages(self):
        body = "登录后继续阅读，验证码。" * 30
        result = validate_chinese_page("请登录", body, "https://example.cn/login")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "blocked_page")

    def test_rejects_insecure_url(self):
        body = "这是中文人工智能基础设施报道。" * 20
        result = validate_chinese_page("英伟达发布全新推理平台", body, "http://example.cn/post")
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "insecure_url")

    def test_chinese_ratio_counts_only_language_characters(self):
        self.assertGreater(chinese_ratio("AI 推理平台支持 GPU 集群"), 0.4)

    def test_candidate_serializes_datetime(self):
        candidate = ChineseCandidate(
            id="c1",
            title="中文人工智能资讯",
            url="https://example.cn/c1",
            source="示例来源",
            published=datetime(2026, 8, 3, tzinfo=timezone.utc),
        )
        self.assertEqual(candidate.serializable()["published"], "2026-08-03T00:00:00+00:00")


class MatchingTests(unittest.TestCase):
    def test_event_signature_normalizes_bilingual_entities(self):
        english = event_signature("NVIDIA launches Dynamo inference platform")
        chinese = event_signature("英伟达发布 Dynamo 分布式推理平台")
        self.assertIn("nvidia", english & chinese)
        self.assertIn("dynamo", english & chinese)
        self.assertIn("inference", english & chinese)

    def test_matches_cross_language_entities(self):
        radar = [{"id": "r1", "title": "NVIDIA launches Dynamo inference platform"}]
        candidate = make_candidate("c1", "英伟达发布 Dynamo 分布式推理平台", "infra")
        match_topics([candidate], radar)
        self.assertEqual(candidate.matched_topic_ids, ["r1"])

    def test_infra_candidate_receives_priority_without_forcing_low_quality(self):
        infra = make_candidate("c1", "vLLM 推理吞吐量提升", "infra", relevance=6, credibility=4)
        agent = make_candidate("c2", "AI Agent 新产品", "agents", relevance=6, credibility=4)
        low = make_candidate("c3", "GPU 广告合集", "infra", relevance=0.5, credibility=1)
        ranked = rank_candidates([agent, infra, low], datetime.now(timezone.utc))
        self.assertEqual(ranked[0].id, "c1")
        self.assertNotIn("c3", [item.id for item in select_candidates(ranked, max_items=10)])

    def test_duplicate_event_prefers_credible_source(self):
        official = make_candidate("c1", "英伟达发布 Dynamo 推理平台", "infra", credibility=5)
        repost = make_candidate("c2", "NVIDIA Dynamo 推理平台正式发布", "infra", credibility=2)
        selected = select_candidates(
            rank_candidates([repost, official], datetime.now(timezone.utc)),
            max_items=10,
        )
        self.assertEqual([item.id for item in selected], ["c1"])


if __name__ == "__main__":
    unittest.main()
