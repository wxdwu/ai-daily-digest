import unittest

from src.send_email import build_message, render_report_html


REPORT = """1. [英伟达 & GPU](https://example.cn/c1?x=1&y=2)
2. [智能体安全更新](https://example.cn/c2)
"""


class EmailRenderingTests(unittest.TestCase):
    def test_html_is_only_a_compact_safe_link_list(self):
        html_body = render_report_html(REPORT)

        self.assertIn("<ol>", html_body)
        self.assertIn(
            '<a href="https://example.cn/c1?x=1&amp;y=2">英伟达 &amp; GPU</a>',
            html_body,
        )
        self.assertEqual(html_body.count("<li>"), 2)
        self.assertNotIn("<h1", html_body)
        self.assertNotIn('class="lead"', html_body)
        self.assertNotIn('class="meta"', html_body)
        self.assertNotIn('class="summary"', html_body)
        self.assertIn("overflow-wrap: anywhere", html_body)
        self.assertIn("display: block", html_body)
        self.assertIn("word-break: break-all", html_body)

    def test_message_contains_plain_and_html_without_attachment(self):
        message = build_message(
            REPORT,
            "2026-08-05",
            "from@example.com",
            ["to@example.com"],
            [],
        )

        self.assertEqual(message.get_content_type(), "multipart/alternative")
        self.assertEqual(
            message.get_body(preferencelist=("plain",)).get_content().strip(),
            REPORT.strip(),
        )
        self.assertIn(
            '<a href="https://example.cn/c1?x=1&amp;y=2">英伟达 &amp; GPU</a>',
            message.get_body(preferencelist=("html",)).get_content(),
        )
        self.assertEqual(len(list(message.iter_attachments())), 0)

    def test_empty_result_is_one_plain_html_paragraph(self):
        html_body = render_report_html("本期没有筛出足够可靠的中文 AI 资讯。\n")

        self.assertIn("<p>本期没有筛出足够可靠的中文 AI 资讯。</p>", html_body)
        self.assertNotIn("<ol>", html_body)


if __name__ == "__main__":
    unittest.main()
