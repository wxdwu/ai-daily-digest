#!/usr/bin/env python3
"""Create or update today's GitHub issue without third-party actions."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def api_request(url: str, token: str, method: str = "GET", payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ai-daily-digest/1.0",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read() or b"{}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="reports/latest.md")
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    token = os.environ["GITHUB_TOKEN"]
    repository = os.environ["GITHUB_REPOSITORY"]
    api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
    title = f"AI Daily · {args.date}"
    body = Path(args.report).read_text(encoding="utf-8")[:65_000]

    query = urlencode({"state": "all", "per_page": 100})
    issues = api_request(f"{api_url}/repos/{repository}/issues?{query}", token)
    existing = next((issue for issue in issues if issue.get("title") == title and "pull_request" not in issue), None)
    if existing:
        api_request(existing["url"], token, "PATCH", {"body": body})
        print(f"Updated issue #{existing['number']}")
    else:
        created = api_request(f"{api_url}/repos/{repository}/issues", token, "POST", {"title": title, "body": body})
        print(f"Created issue #{created['number']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
