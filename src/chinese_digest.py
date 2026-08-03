"""Chinese-only candidate validation and report selection helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import re
from typing import Any


@dataclass
class ChineseCandidate:
    id: str
    title: str
    url: str
    source: str
    published: datetime
    summary: str = ""
    body: str = ""
    credibility: int = 0
    category_id: str = ""
    category_label: str = ""
    relevance: float = 0.0
    score: float = 0.0
    matched_topic_ids: list[str] = field(default_factory=list)
    editorial_title: str = ""
    editorial_summary: str = ""
    why_it_matters: str = ""

    def serializable(self) -> dict[str, Any]:
        data = asdict(self)
        data["published"] = self.published.isoformat()
        return data


@dataclass(frozen=True)
class PageValidation:
    valid: bool
    reason: str = ""


def chinese_ratio(text: str) -> float:
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return chinese / max(1, chinese + latin)


def validate_chinese_page(title: str, body: str, url: str) -> PageValidation:
    combined = f"{title} {body}"
    blocked_markers = ("验证码", "登录后", "安全验证", "访问异常")
    if any(marker in combined[:500] for marker in blocked_markers):
        return PageValidation(False, "blocked_page")
    if not url.startswith("https://"):
        return PageValidation(False, "insecure_url")
    if len(re.findall(r"[\u4e00-\u9fff]", title)) < 4:
        return PageValidation(False, "non_chinese")
    if len(re.findall(r"[\u4e00-\u9fff]", body)) < 120 or chinese_ratio(body) < 0.25:
        return PageValidation(False, "non_chinese")
    return PageValidation(True)
