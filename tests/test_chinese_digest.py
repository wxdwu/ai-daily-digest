from datetime import datetime, timezone
import unittest

from src.chinese_digest import ChineseCandidate, chinese_ratio, validate_chinese_page


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


if __name__ == "__main__":
    unittest.main()
