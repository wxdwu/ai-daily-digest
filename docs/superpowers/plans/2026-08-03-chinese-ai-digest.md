# Chinese AI Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **2026-08-03 correction:** GitHub's current documentation says GitHub Models was fully retired on 2026-07-30. All GitHub Models-specific steps below are superseded: the implemented workflow uses deterministic Chinese fallback by default and an optional external OpenAI-compatible API only when all three `LLM_*` secrets are configured.

**Goal:** Generate a concise Chinese-only daily AI report whose links open Chinese articles, using international sources as a radar, Chinese sources as publishable candidates, and at most one optional external-model editorial request per run.

**Architecture:** Keep `src/ai_digest.py` as the fetch/orchestration entrypoint. Add a focused `src/chinese_digest.py` module for Chinese validation, event matching, scoring, selection, and Markdown rendering, plus `src/model_editor.py` for one-shot external Chat Completions editing with deterministic fallback. Source configuration marks each feed as `international` or `chinese`; only validated Chinese candidates can reach the renderer.

**Tech Stack:** Python 3.12 standard library, `unittest`, GitHub Actions, optional OpenAI-compatible Chat Completions API, JSON source configuration.

---

### Task 1: Chinese page validation and candidate model

**Files:**
- Create: `src/chinese_digest.py`
- Create: `tests/test_chinese_digest.py`

- [ ] **Step 1: Write failing tests for Chinese text and page validation**

```python
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

    def test_chinese_ratio_counts_only_language_characters(self):
        self.assertGreater(chinese_ratio("AI 推理平台支持 GPU 集群"), 0.4)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_chinese_digest.ChineseValidationTests -v`

Expected: `ModuleNotFoundError: No module named 'src.chinese_digest'`.

- [ ] **Step 3: Implement the candidate and validation API**

Create `ChineseCandidate` with `id`, `title`, `url`, `source`, `published`, `summary`, `body`, `credibility`, `category_id`, `category_label`, `relevance`, `score`, `matched_topic_ids`, and editorial fields. Implement:

```python
@dataclass
class PageValidation:
    valid: bool
    reason: str = ""


def chinese_ratio(text: str) -> float:
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return chinese / max(1, chinese + latin)


def validate_chinese_page(title: str, body: str, url: str) -> PageValidation:
    combined = f"{title} {body}"
    if any(marker in combined[:500] for marker in ("验证码", "登录后", "安全验证", "访问异常")):
        return PageValidation(False, "blocked_page")
    if not url.startswith("https://"):
        return PageValidation(False, "insecure_url")
    if len(re.findall(r"[\u4e00-\u9fff]", title)) < 4:
        return PageValidation(False, "non_chinese")
    if len(re.findall(r"[\u4e00-\u9fff]", body)) < 120 or chinese_ratio(body) < 0.25:
        return PageValidation(False, "non_chinese")
    return PageValidation(True)
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `python -m unittest tests.test_chinese_digest.ChineseValidationTests -v`

Expected: all four tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/chinese_digest.py tests/test_chinese_digest.py
git commit -m "feat: validate Chinese news pages"
```

### Task 2: Event matching, deduplication, and AI Infra weighting

**Files:**
- Modify: `src/chinese_digest.py`
- Modify: `tests/test_chinese_digest.py`

- [ ] **Step 1: Write failing tests for matching and selection**

```python
from src.chinese_digest import event_signature, match_topics, rank_candidates, select_candidates


def make_candidate(candidate_id, title, category_id, relevance=4, credibility=3):
    return ChineseCandidate(
        id=candidate_id,
        title=title,
        url=f"https://example.cn/{candidate_id}",
        source="示例中文媒体",
        published=datetime.now(timezone.utc),
        credibility=credibility,
        category_id=category_id,
        category_label={"infra": "AI Infra", "agents": "AI Agent", "models": "大模型"}[category_id],
        relevance=relevance,
        body="这是一篇完整的中文人工智能技术报道。" * 20,
    )


class MatchingTests(unittest.TestCase):
    def test_matches_cross_language_entities(self):
        radar = [{"id": "r1", "title": "NVIDIA launches Dynamo inference platform"}]
        candidate = ChineseCandidate(
            id="c1",
            title="英伟达发布 Dynamo 分布式推理平台",
            url="https://example.cn/dynamo",
            source="示例中文媒体",
            published=datetime.now(timezone.utc),
            credibility=4,
        )
        match_topics([candidate], radar)
        self.assertEqual(candidate.matched_topic_ids, ["r1"])

    def test_infra_candidate_receives_priority_without_forcing_low_quality(self):
        infra = make_candidate("c1", "vLLM 推理吞吐量提升", "infra", relevance=6, credibility=4)
        agent = make_candidate("c2", "AI Agent 新产品", "agents", relevance=6, credibility=4)
        low = make_candidate("c3", "GPU 广告合集", "infra", relevance=0.5, credibility=1)
        ranked = rank_candidates([agent, infra, low], datetime.now(timezone.utc))
        self.assertEqual(ranked[0].id, "c1")
        self.assertNotIn("c3", [item.id for item in select_candidates(ranked, max_items=10)])

    def test_duplicate_event_prefers_credible_source(self):
        official = make_candidate("c1", "英伟达发布 Dynamo 推理平台", "infra", credibility=5)
        repost = make_candidate("c2", "NVIDIA Dynamo 推理平台正式发布", "infra", credibility=2)
        selected = select_candidates(rank_candidates([repost, official], datetime.now(timezone.utc)), max_items=10)
        self.assertEqual([item.id for item in selected], ["c1"])
```

- [ ] **Step 2: Run the matching tests and verify RED**

Run: `python -m unittest tests.test_chinese_digest.MatchingTests -v`

Expected: import failures for the new matching functions.

- [ ] **Step 3: Implement deterministic event signatures and ranking**

Implement `event_signature(text)`, `match_topics(candidates, radar_topics)`, `rank_candidates(candidates, now)`, and `select_candidates(ranked, max_items)`. Normalize known bilingual aliases such as `NVIDIA/英伟达`, preserve model and project tokens (`vllm`, `sglang`, `dynamo`, `mcp`, `claude`, `gpt`, `qwen`, `deepseek`), add a 2-point AI Infra boost, require relevance at least 2, and deduplicate with normalized entity overlap plus title similarity.

- [ ] **Step 4: Run all Chinese digest tests and verify GREEN**

Run: `python -m unittest tests.test_chinese_digest -v`

Expected: validation and matching tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/chinese_digest.py tests/test_chinese_digest.py
git commit -m "feat: match and rank Chinese AI news"
```

### Task 3: One-shot GitHub Models editor with safe fallback

**Files:**
- Create: `src/model_editor.py`
- Create: `tests/test_model_editor.py`

- [ ] **Step 1: Write failing tests for editorial output validation**

```python
import io
import json
import unittest

from src.model_editor import edit_candidates, EditorialResult


def candidate_dict(candidate_id):
    return {
        "id": candidate_id,
        "title": "中文人工智能推理平台发布",
        "summary": "该平台提升了大模型推理效率。",
        "source": "示例中文媒体",
        "category": "AI Infra",
        "published": "2026-08-03T00:00:00+00:00",
    }


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload


class ModelEditorTests(unittest.TestCase):
    def test_accepts_only_known_candidate_ids(self):
        completion = {
            "choices": [{"message": {"content": json.dumps({
                "storm_summary": "今日推理基础设施升级明显。",
                "selected_items": [
                    {"id": "c1", "title": "中文标题", "summary": "中文摘要", "why": "值得关注"},
                    {"id": "invented", "title": "编造项", "summary": "无效", "why": "无效"},
                ],
                "trends": ["推理成本继续下降"],
            }, ensure_ascii=False)}}]
        }
        result = edit_candidates([candidate_dict("c1")], token="token", opener=lambda *a, **k: FakeResponse(completion))
        self.assertEqual([item["id"] for item in result.selected_items], ["c1"])

    def test_invalid_response_returns_deterministic_fallback(self):
        result = edit_candidates(
            [candidate_dict("c1")],
            token="token",
            opener=lambda *a, **k: FakeResponse({"choices": [{"message": {"content": "not json"}}]}),
        )
        self.assertEqual(result.mode, "规则降级")
        self.assertEqual(result.selected_items[0]["id"], "c1")
```

- [ ] **Step 2: Run the editor tests and verify RED**

Run: `python -m unittest tests.test_model_editor -v`

Expected: `ModuleNotFoundError: No module named 'src.model_editor'`.

- [ ] **Step 3: Implement one request and candidate-ID constrained parsing**

Implement `EditorialResult`, `fallback_editorial(candidates)`, and `edit_candidates(...)`. Default to `https://models.github.ai/inference/chat/completions` and `openai/gpt-4.1-mini`; use `GITHUB_TOKEN` when external LLM settings are absent. Send at most 25 candidate records, request JSON output, parse fenced or plain JSON, drop unknown IDs, and fill missing slots from ranked candidates. Never use a model-returned URL.

- [ ] **Step 4: Run editor tests and verify GREEN**

Run: `python -m unittest tests.test_model_editor -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/model_editor.py tests/test_model_editor.py
git commit -m "feat: edit digest with GitHub Models"
```

### Task 4: Integrate Chinese sources and render the unified report

**Files:**
- Modify: `config/sources.json`
- Modify: `src/ai_digest.py`
- Modify: `src/chinese_digest.py`
- Modify: `tests/test_ai_digest.py`
- Modify: `tests/test_chinese_digest.py`

- [ ] **Step 1: Write failing integration tests**

Add tests proving that source records with `pool: "chinese"` become `ChineseCandidate` objects, international records never appear in the report, report links resolve from candidate IDs, the report contains `今日 AI 风暴` and `今日三个趋势判断`, and the status block names the actual model or `规则降级`.

```python
from datetime import datetime, timezone

from src.chinese_digest import render_chinese_report
from src.model_editor import EditorialResult


FIXED_NOW = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)


def test_rendered_report_contains_only_validated_chinese_candidates(self):
    chinese = make_candidate("c1", "中文推理平台发布", "infra", credibility=5)
    editorial = EditorialResult(
        storm_summary="今日 AI 基础设施出现重要升级。",
        selected_items=[{"id": "c1", "title": "中文推理平台发布", "summary": "推理效率进一步提升。", "why": "降低部署成本"}],
        trends=["推理服务继续向高吞吐演进"],
        mode="GitHub Models: openai/gpt-4.1-mini",
    )
    report = render_chinese_report([chinese], editorial, FIXED_NOW, stats={})
    self.assertIn("https://example.cn/c1", report)
    self.assertNotIn("https://openai.com/", report)
    self.assertIn("今日 AI 风暴", report)
```

- [ ] **Step 2: Run integration tests and verify RED**

Run: `python -m unittest tests.test_chinese_digest tests.test_ai_digest -v`

Expected: failures for missing report rendering and source-pool integration.

- [ ] **Step 3: Add initial verified Chinese feeds**

Add Chinese pool entries for:

- `https://www.qbitai.com/feed`
- `https://www.infoq.cn/feed`
- `https://blogs.nvidia.cn/feed/`
- `https://developer.nvidia.cn/blog/feed/`
- `https://aws.amazon.com/cn/blogs/china/feed/`

Each entry declares `pool: "chinese"`, a credibility score, and relevant categories. Existing sources explicitly use `pool: "international"`.

- [ ] **Step 4: Integrate the two pools and unified renderer**

Update orchestration to fetch both pools concurrently, use a 48-hour Chinese cutoff, validate candidate pages before model input, build radar topic dictionaries from international items, rank at most 25 Chinese candidates, call `edit_candidates` once, and write the same Markdown report to `latest.md` and the dated archive. Keep JSON output with stats and selected candidate records.

- [ ] **Step 5: Run integration and regression tests**

Run: `python -m unittest discover -s tests -v`

Expected: all existing and new tests pass.

- [ ] **Step 6: Commit**

```bash
git add config/sources.json src/ai_digest.py src/chinese_digest.py tests/test_ai_digest.py tests/test_chinese_digest.py
git commit -m "feat: generate Chinese-only AI digest"
```

### Task 5: Enable GitHub Models and document one-click operation

**Files:**
- Modify: `.github/workflows/ai-daily.yml`
- Modify: `README.md`
- Test: `tests/test_workflow_config.py`

- [ ] **Step 1: Write a failing workflow configuration test**

```python
from pathlib import Path
import unittest


class WorkflowConfigTests(unittest.TestCase):
    def test_workflow_grants_models_read_and_passes_github_token(self):
        workflow = Path(".github/workflows/ai-daily.yml").read_text()
        self.assertIn("models: read", workflow)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", workflow)
        self.assertIn("GITHUB_MODELS_MODEL", workflow)

    def test_workflow_keeps_manual_run(self):
        workflow = Path(".github/workflows/ai-daily.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
```

- [ ] **Step 2: Run the workflow test and verify RED**

Run: `python -m unittest tests.test_workflow_config -v`

Expected: failure because `models: read` and GitHub Models environment variables are absent.

- [ ] **Step 3: Update workflow and README**

Add `models: read`, pass `GITHUB_TOKEN: ${{ github.token }}`, and use repository variable `GITHUB_MODELS_MODEL` with code-level default `openai/gpt-4.1-mini`. Keep existing SMTP Secrets and external LLM override. Document that the user only needs to click `Run workflow`; GitHub Models requires no new Secret. Document Chinese source behavior, report locations, email Secrets, and model fallback.

- [ ] **Step 4: Run workflow and full tests**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass.

Run: `ruby -e 'require "yaml"; YAML.parse_file(".github/workflows/ai-daily.yml"); puts "workflow YAML syntax: OK"'`

Expected: `workflow YAML syntax: OK`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ai-daily.yml README.md tests/test_workflow_config.py
git commit -m "feat: enable zero-config GitHub Models"
```

### Task 6: End-to-end verification and publish for manual Run workflow

**Files:**
- Modify only if verification exposes a failing requirement.

- [ ] **Step 1: Run fresh offline verification**

Run: `python -m unittest discover -s tests -v`

Expected: zero failures and zero errors.

Run: `PYTHONPYCACHEPREFIX=/tmp/ai-daily-pycache python -m py_compile src/ai_digest.py src/chinese_digest.py src/model_editor.py src/publish_issue.py src/send_email.py`

Expected: exit code 0.

Run: `git diff --check`

Expected: no output.

- [ ] **Step 2: Run a live fetch without a model token**

Run: `python src/ai_digest.py --ignore-seen`

Expected: Chinese sources are fetched, only validated Chinese links are selected, and `reports/latest.md` identifies `规则降级`.

- [ ] **Step 3: Validate every final link and the report language**

Read `reports/latest.json`, fetch every selected URL, and assert each page passes `validate_chinese_page`. Confirm the report contains no selected international URL and all item titles contain Chinese characters.

- [ ] **Step 4: Push the feature branch and open a draft PR**

```bash
git push -u origin agent/chinese-ai-digest
gh pr create --draft --base main --head agent/chinese-ai-digest --title "Generate a Chinese-only AI daily digest" --body-file /tmp/ai-daily-pr.md
```

The PR body must summarize the Chinese source pool, optional external-model integration, AI Infra weighting, fallback behavior, and verification commands.

- [ ] **Step 5: Merge after checks and confirm workflow discovery**

Merge the PR only after its checks pass, then run:

```bash
gh workflow list --repo wxdwu/ai-daily-digest --all
```

Expected: `AI Daily Digest` is `active` on `main`. Stop before triggering it so the user can perform the requested final `Run workflow` test.
