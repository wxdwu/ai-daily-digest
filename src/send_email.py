#!/usr/bin/env python3
"""Send the generated Markdown report over authenticated SMTP."""

from __future__ import annotations

import argparse
from email.message import EmailMessage
import html
import os
from pathlib import Path
import re
import smtplib
import ssl


def split_addresses(value: str) -> list[str]:
    return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]


def render_report_html(report: str) -> str:
    body: list[str] = []
    article_open = False
    link_pattern = re.compile(r"^(\d+)\. \[(.*?)\]\((https://.*)\)$")
    metadata_pattern = re.compile(r"^`([^`]+)` · `([^`]+)`$")

    for raw_line in report.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
            continue
        if line.startswith("📮"):
            body.append(f'<p class="lead">{html.escape(line)}</p>')
            continue

        link_match = link_pattern.match(line)
        if link_match:
            if article_open:
                body.append("</article>")
            article_open = True
            number, title, url = link_match.groups()
            body.append(
                '<article><h2><span class="number">'
                f"{html.escape(number)}.</span> "
                f'<a href="{html.escape(url, quote=True)}">{html.escape(title)}</a>'
                "</h2>"
            )
            continue

        metadata_match = metadata_pattern.match(line)
        if metadata_match:
            category, published = metadata_match.groups()
            body.append(
                '<p class="meta"><span>'
                f"{html.escape(category)}</span><span>{html.escape(published)}</span></p>"
            )
            continue

        css_class = "summary" if article_open else "text"
        body.append(f'<p class="{css_class}">{html.escape(line)}</p>')

    if article_open:
        body.append("</article>")

    content = "\n".join(body)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ margin: 0; background: #f6f7f9; color: #202124; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ max-width: 680px; margin: 0 auto; padding: 24px 18px 36px; background: #ffffff; }}
    h1 {{ margin: 0 0 18px; font-size: 25px; line-height: 1.35; }}
    .lead {{ margin: 0 0 22px; padding: 13px 14px; background: #f2f6ff; border-left: 4px solid #2f6feb; line-height: 1.65; }}
    article {{ padding: 18px 0; border-top: 1px solid #e8eaed; }}
    h2 {{ margin: 0; font-size: 18px; line-height: 1.55; }}
    h2 a {{ color: #1769d2; text-decoration: none; }}
    .number {{ color: #202124; }}
    .meta {{ display: flex; gap: 8px; margin: 10px 0 8px; color: #5f6368; font-size: 13px; }}
    .meta span {{ padding: 2px 7px; border-radius: 5px; background: #f1f3f4; }}
    .summary, .text {{ margin: 0; color: #3c4043; font-size: 15px; line-height: 1.7; }}
  </style>
</head>
<body><main>
{content}
</main></body>
</html>"""


def build_message(
    report: str,
    date: str,
    sender: str,
    to: list[str],
    cc: list[str],
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"每日 AI 速报 · {date}"
    message["From"] = sender
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    message.set_content(report)
    message.add_alternative(render_report_html(report), subtype="html")
    message.add_attachment(
        report.encode("utf-8"),
        maintype="text",
        subtype="markdown",
        filename=f"ai-daily-{date}.md",
    )
    return message


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="reports/latest.md")
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    required = ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"SMTP is enabled but these variables are missing: {', '.join(missing)}")

    to = split_addresses(os.environ["EMAIL_TO"])
    cc = split_addresses(os.getenv("EMAIL_CC", ""))
    report = Path(args.report).read_text(encoding="utf-8")
    message = build_message(report, args.date, os.environ["EMAIL_FROM"], to, cc)

    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "465"))
    use_starttls = os.getenv("SMTP_STARTTLS", "false").lower() == "true"
    context = ssl.create_default_context()
    if use_starttls:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=context)
            server.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            server.send_message(message, to_addrs=to + cc)
    else:
        with smtplib.SMTP_SSL(host, port, timeout=30, context=context) as server:
            server.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            server.send_message(message, to_addrs=to + cc)
    print(f"Sent digest to {len(to)} recipient(s), cc {len(cc)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
