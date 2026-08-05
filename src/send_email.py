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
        link_style = (
            "display: block; max-width: 100%; color: #24446b !important; "
            "text-decoration: none !important; overflow-wrap: anywhere; "
            "word-break: normal; font-size: 14px; line-height: 1.35; font-weight: 600;"
        )
        items = "\n".join(
            '<li style="padding: 5px 0; border-bottom: 1px solid #edf1f5;">'
            f'<a href="{html.escape(url, quote=True)}" style="{link_style}">'
            f"{html.escape(title)}</a></li>"
            for title, url in links
        )
        headline = fallback_lines[0] if fallback_lines else "今日 AI 焦点"
        focus = (
            '<div class="digest-focus" style="margin: 0 0 4px; padding: 8px 10px; '
            'background: #f3f7fd; border-left: 3px solid #3b82f6; border-radius: 6px;">'
            '<div style="margin: 0; color: #527097; font-size: 10px; line-height: 1.2; '
            f'font-weight: 700; letter-spacing: .08em;">AI DAILY · {len(links)} 条精选</div>'
            '<h1 class="digest-headline" style="margin: 2px 0 0; color: #172b4d; '
            f'font-size: 15px; line-height: 1.3; font-weight: 700;">{html.escape(headline)}</h1>'
            "</div>"
        )
        content = (
            f'{focus}<ol style="margin: 0; padding-left: 26px; color: #667085;">\n'
            f"{items}\n</ol>"
        )
    else:
        content = f"<p>{html.escape(' '.join(fallback_lines))}</p>"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ margin: 0; background: #ffffff; color: #202124; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ max-width: 680px; margin: 0 auto; padding: 10px 14px; }}
    .digest-focus {{ background: #f3f7fd; border-left: 3px solid #3b82f6; }}
    .digest-headline {{ color: #172b4d; font-size: 15px; line-height: 1.3; }}
    ol {{ margin: 0; padding-left: 26px; color: #667085; }}
    li {{ padding: 5px 0; border-bottom: 1px solid #edf1f5; font-size: 14px; line-height: 1.35; }}
    li:last-child {{ border-bottom: 0; }}
    a {{ display: block; max-width: 100%; color: #24446b !important; text-decoration: none !important; overflow-wrap: anywhere; word-break: normal; font-weight: 600; }}
    p {{ margin: 0; font-size: 14px; line-height: 1.4; }}
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
