"""Chinese-only candidate validation and report selection helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
import os
import re
from typing import Any
from zoneinfo import ZoneInfo

from src.model_editor import EditorialResult


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


_ALIASES = {
    "nvidia": ("nvidia", "英伟达"),
    "openai": ("openai",),
    "anthropic": ("anthropic",),
    "google": ("google", "谷歌"),
    "microsoft": ("microsoft", "微软"),
    "amazon": ("amazon", "亚马逊"),
    "inference": ("inference", "推理"),
    "training": ("training", "训练"),
    "agent": ("agent", "agentic", "智能体"),
    "llm": ("llm", "large language model", "大模型"),
    "gpu": ("gpu", "显卡", "算力卡"),
    "platform": ("platform", "平台"),
}
_STOP_WORDS = {
    "a", "an", "and", "for", "from", "in", "of", "on", "the", "to", "with",
    "new", "launch", "launches", "launched", "release", "released", "发布", "推出",
}
_GENERIC_SIGNATURES = {"ai", "agent", "gpu", "inference", "llm", "platform", "training"}


def event_signature(text: str) -> set[str]:
    lowered = text.lower()
    signature = {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9.+-]*", lowered)
        if len(token) >= 2 and token not in _STOP_WORDS
    }
    for canonical, aliases in _ALIASES.items():
        if any(alias in lowered for alias in aliases):
            signature.add(canonical)
    return signature


def _signatures_match(left: set[str], right: set[str]) -> bool:
    if not left or not right:
        return False
    common = left & right
    specific = common - _GENERIC_SIGNATURES
    coverage = len(common) / max(1, min(len(left), len(right)))
    return (len(specific) >= 1 and coverage >= 0.5) or len(common) >= 3


def match_topics(candidates: list[ChineseCandidate], radar_topics: list[dict[str, Any]]) -> None:
    topic_signatures = {
        str(topic["id"]): event_signature(str(topic.get("title", ""))) for topic in radar_topics
    }
    for candidate in candidates:
        candidate_signature = event_signature(f"{candidate.title} {candidate.summary}")
        candidate.matched_topic_ids = [
            topic_id
            for topic_id, signature in topic_signatures.items()
            if _signatures_match(candidate_signature, signature)
        ]


def rank_candidates(candidates: list[ChineseCandidate], now: datetime) -> list[ChineseCandidate]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    for candidate in candidates:
        age_hours = max(0.0, (now - candidate.published).total_seconds() / 3600)
        freshness = max(0.0, 3.0 - age_hours / 16.0)
        infra_bonus = 2.0 if candidate.category_id == "infra" else 0.0
        match_bonus = min(4.0, len(candidate.matched_topic_ids) * 2.0)
        candidate.score = round(
            candidate.relevance + candidate.credibility + freshness + infra_bonus + match_bonus,
            2,
        )
    return sorted(candidates, key=lambda item: (item.score, item.published), reverse=True)


def _duplicate(left: ChineseCandidate, right: ChineseCandidate) -> bool:
    left_signature = event_signature(left.title)
    right_signature = event_signature(right.title)
    if _signatures_match(left_signature, right_signature):
        return True
    return SequenceMatcher(None, left.title.lower(), right.title.lower()).ratio() >= 0.82


def select_candidates(ranked: list[ChineseCandidate], max_items: int = 10) -> list[ChineseCandidate]:
    selected: list[ChineseCandidate] = []
    for candidate in ranked:
        if candidate.relevance < 2:
            continue
        if any(_duplicate(candidate, existing) for existing in selected):
            continue
        selected.append(candidate)
        if len(selected) >= max_items:
            break
    return selected


def _compact_title(value: str, limit: int = 35) -> str:
    title = re.sub(r"\s+", " ", value).strip()
    title = re.sub(r"[。！!？?，,、；;：:….\s]+$", "", title)
    if len(title) <= limit:
        return title
    return title[: limit - 1].rstrip() + "…"


def render_chinese_report(
    candidates: list[ChineseCandidate],
    editorial: EditorialResult,
    now: datetime,
    *,
    radar_count: int,
    chinese_source_count: int,
    valid_count: int,
    source_errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> str:
    local_tz = ZoneInfo(os.getenv("TZ", "Asia/Shanghai"))
    local_now = now.astimezone(local_tz)
    by_id = {candidate.id: candidate for candidate in candidates}
    selected = [
        item for item in editorial.selected_items if str(item.get("id", "")) in by_id
    ][:10]
    storm_summary = re.sub(r"\s+", " ", editorial.storm_summary).strip()
    if not selected:
        storm_summary = "本期没有筛出足够可靠的中文 AI 资讯。"
    lines = [
        f"# 每日 AI 速报 · {local_now:%Y-%m-%d}",
        "",
        f"📮 今日 AI 猛料：{storm_summary}",
        "",
    ]
    for index, edited in enumerate(selected, 1):
        candidate = by_id[str(edited["id"])]
        title = _compact_title(str(edited.get("title") or candidate.title))
        lines.append(f"{index}. [{title}]({candidate.url})")
    return "\n".join(lines).rstrip() + "\n"
