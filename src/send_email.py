#!/usr/bin/env python3
"""Send the generated Markdown report over authenticated SMTP."""

from __future__ import annotations

import argparse
from email.message import EmailMessage
import os
from pathlib import Path
import smtplib
import ssl


def split_addresses(value: str) -> list[str]:
    return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]


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
    message = EmailMessage()
    message["Subject"] = f"每日 AI 速报 · {args.date}"
    message["From"] = os.environ["EMAIL_FROM"]
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    report = Path(args.report).read_text(encoding="utf-8")
    message.set_content(report)
    message.add_attachment(report.encode("utf-8"), maintype="text", subtype="markdown", filename=f"ai-daily-{args.date}.md")

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
