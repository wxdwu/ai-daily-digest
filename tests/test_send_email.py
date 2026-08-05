import unittest

from src.send_email import build_message, render_report_html


REPORT = """# 每日 AI 速报 · 2026-08-05

📮 今日 AI 猛料：今日聚焦 AI Infra。

1. [英伟达 & GPU](https://example.cn/c1?x=1&y=2)

   `AI Infra` · `08-05 09:27`

   <script>alert("x")</script> 推理成本下降。
"""


class EmailRenderingTests(unittest.TestCase):
    def test_html_has_clickable_escaped_title_and_safe_summary(self):
        html_body = render_report_html(REPORT)

        self.assertIn(
            '<a href="https://example.cn/c1?x=1&amp;y=2">英伟达 &amp; GPU</a>',
            html_body,
        )
        self.assertIn("AI Infra", html_body)
        self.assertNotIn("<script>", html_body)
        self.assertIn("&lt;script&gt;", html_body)

    def test_message_contains_plain_html_and_markdown_attachment(self):
        message = build_message(
            REPORT,
            "2026-08-05",
            "from@example.com",
            ["to@example.com"],
            [],
        )

        self.assertEqual(message.get_content_type(), "multipart/mixed")
        self.assertEqual(
            message.get_body(preferencelist=("plain",)).get_content().strip(),
            REPORT.strip(),
        )
        self.assertIn(
            '<a href="https://example.cn/c1?x=1&amp;y=2">英伟达 &amp; GPU</a>',
            message.get_body(preferencelist=("html",)).get_content(),
        )
        attachments = list(message.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_filename(), "ai-daily-2026-08-05.md")


if __name__ == "__main__":
    unittest.main()
