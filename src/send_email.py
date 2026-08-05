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
    link_pattern = re.compile(r"^(\d+)\. \[(.*?)\]\((https://.*)\)$")
    links: list[tuple[str, str]] = []
    fallback_lines: list[str] = []
    for raw_line in report.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = link_pattern.match(line)
        if match:
            _, title, url = match.groups()
            links.append((title, url))
        else:
            fallback_lines.append(line)

    if links:
        items = "\n".join(
            f'<li><a href="{html.escape(url, quote=True)}">{html.escape(title)}</a></li>'
            for title, url in links
        )
        content = f"<ol>\n{items}\n</ol>"
    else:
        content = f"<p>{html.escape(' '.join(fallback_lines))}</p>"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ margin: 0; background: #ffffff; color: #202124; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ max-width: 680px; margin: 0 auto; padding: 12px 16px; }}
    ol {{ margin: 0; padding-left: 28px; }}
    li {{ padding: 10px 0; border-bottom: 1px solid #e8eaed; font-size: 17px; line-height: 1.45; }}
    li:last-child {{ border-bottom: 0; }}
    a {{ display: block; max-width: 100%; color: #1769d2; text-decoration: none; overflow-wrap: anywhere; word-break: break-all; }}
    p {{ margin: 0; font-size: 16px; line-height: 1.5; }}
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
