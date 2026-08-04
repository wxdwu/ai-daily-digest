# Compact AI Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the expanded daily digest with one short headline and at most ten directly clickable, concise Chinese titles.

**Architecture:** Keep the existing fetch, validation, ranking, JSON, Issue, and email pipeline unchanged. Limit the behavioral change to Markdown rendering in `src/chinese_digest.py`, rule-mode headline generation in `src/model_editor.py`, and diagnostic logging in `src/ai_digest.py`; all consumers continue sharing `reports/latest.md`.

**Tech Stack:** Python 3.12 standard library, `unittest`, Markdown, GitHub Actions.

## Global Constraints

- Report body contains only the date, one `📮 今日 AI 猛料` sentence, and at most ten numbered clickable titles.
- Each displayed title is at most 35 visible characters, including a final ellipsis when truncated.
- The renderer never accepts or displays a model-provided URL; URLs come only from validated Chinese candidates.
- Item summaries, sources, timestamps, categories, reasons, trend lists, run status, warnings, and source errors do not appear in Markdown.
- JSON output and the existing Issue, email, archive, and artifact flows remain compatible.
- No new third-party dependency.

---

### Task 1: Compact Markdown renderer

**Files:**
- Modify: `tests/test_chinese_digest.py`
- Modify: `src/chinese_digest.py`

**Interfaces:**
- Consumes: `render_chinese_report(candidates, editorial, now, *, radar_count, chinese_source_count, valid_count, source_errors=None, warnings=None) -> str`
- Produces: `_compact_title(value: str, limit: int = 35) -> str` and compact Markdown from the existing renderer signature.

- [ ] **Step 1: Replace the report test with failing compact-format assertions**

```python
def test_report_is_a_compact_clickable_title_list(self):
    candidate = make_candidate("c1", "英伟达发布中文推理平台", "infra")
    editorial = EditorialResult(
        storm_summary="从大模型到智能体落地，今日重点一页看完。",
        selected_items=[{
            "id": "c1",
            "title": "英伟达推理平台迎来更新",
            "summary": "不应显示的摘要",
            "why": "不应显示的理由",
        }],
        trends=["不应显示的趋势"],
        mode="规则降级",
        warning="不应显示的警告",
    )
    report = render_chinese_report(
        [candidate], editorial, FIXED_NOW,
        radar_count=12, chinese_source_count=5, valid_count=1,
        source_errors=["不应显示的来源错误"],
    )
    self.assertIn("📮 今日 AI 猛料：从大模型到智能体落地，今日重点一页看完。", report)
    self.assertIn("1. [英伟达推理平台迎来更新](https://example.cn/c1)", report)
    for hidden in ("不应显示的摘要", "不应显示的理由", "不应显示的趋势", "运行状态", "示例中文媒体"):
        self.assertNotIn(hidden, report)
```

Add a separate failing test for title length:

```python
def test_report_truncates_titles_to_35_visible_characters(self):
    long_title = "这是一个明显超过三十五个可见字符并且需要在手机速报中被稳定截断的中文资讯标题"
    # Render one known candidate/editorial item.
    displayed = re.search(r"1\. \[(.*?)\]\(", report).group(1)
    self.assertEqual(len(displayed), 35)
    self.assertTrue(displayed.endswith("…"))
```

Add focused assertions that a short title such as `"模型发布！！！"` renders as `模型发布`, and that passing 11 known candidates/editorial items renders entries 1 through 10 but no entry 11.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `PYTHONPYCACHEPREFIX=/tmp/compact-report-pycache python3 -m unittest tests.test_chinese_digest.ReportTests -v`

Expected: failures because the current renderer includes expanded metadata, summaries, trends, and status, and does not cap title length.

- [ ] **Step 3: Implement the minimal compact renderer**

Implement `_compact_title` as whitespace normalization, trailing punctuation cleanup, and deterministic truncation to 34 characters plus `…`. Keep the existing renderer arguments for caller compatibility, ignore display-only diagnostics, filter editorial IDs through `by_id`, cap the list at ten, and emit:

```python
lines = [
    f"# 每日 AI 速报 · {local_now:%Y-%m-%d}",
    "",
    f"📮 今日 AI 猛料：{storm_summary}",
    "",
]
for index, edited in enumerate(selected[:10], 1):
    candidate = by_id[str(edited["id"])]
    title = _compact_title(str(edited.get("title") or candidate.title))
    lines.append(f"{index}. [{title}]({candidate.url})")
```

For zero selected items, use `本期没有筛出足够可靠的中文 AI 资讯。` as the single headline sentence and emit no numbered list.

- [ ] **Step 4: Run the focused and full suites and verify GREEN**

Run: `PYTHONPYCACHEPREFIX=/tmp/compact-report-pycache python3 -m unittest tests.test_chinese_digest.ReportTests -v`

Expected: all `ReportTests` pass.

Run: `PYTHONPYCACHEPREFIX=/tmp/compact-report-pycache python3 -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 5: Commit the renderer**

```bash
git add src/chinese_digest.py tests/test_chinese_digest.py
git commit -m "feat: render compact AI report"
```

### Task 2: Concise fallback headline and Actions diagnostics

**Files:**
- Modify: `tests/test_model_editor.py`
- Modify: `tests/test_ai_digest.py`
- Modify: `src/model_editor.py`
- Modify: `src/ai_digest.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `fallback_editorial(candidates, warning="") -> EditorialResult`
- Produces: `run_diagnostic_lines(source_errors: list[str], warnings: list[str]) -> list[str]` for Actions standard output.

- [ ] **Step 1: Write failing tests for the concise fallback headline and diagnostic lines**

```python
def test_fallback_headline_uses_category_range_instead_of_item_counts(self):
    candidates = [candidate_dict("c1"), candidate_dict("c2")]
    candidates[0]["category"] = "大模型"
    candidates[1]["category"] = "AI Agent"
    result = fallback_editorial(candidates)
    self.assertEqual(result.storm_summary, "从大模型到 AI Agent，今日 AI 重点一页看完。")
    self.assertNotIn("筛选出", result.storm_summary)
```

```python
def test_diagnostic_lines_keep_errors_outside_the_report(self):
    self.assertEqual(
        run_diagnostic_lines(["量子位: timeout"], ["中文页面校验未通过：1 条"]),
        ["来源失败：量子位: timeout", "提示：中文页面校验未通过：1 条"],
    )
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `PYTHONPYCACHEPREFIX=/tmp/compact-report-pycache python3 -m unittest tests.test_model_editor tests.test_ai_digest -v`

Expected: fallback headline assertion fails with the current count-based text and `run_diagnostic_lines` import fails because the helper does not exist.

- [ ] **Step 3: Implement the fallback headline and logging helper**

Build the fallback headline from the first and last unique non-empty categories in the selected order. One category uses `今日聚焦{category}，AI 重点一页看完。`; two or more use `从{first}到 {last}，今日 AI 重点一页看完。`. Implement `run_diagnostic_lines` exactly as asserted and print each returned line after the existing fetch summary in `build_digest`. Pass both rule-validation warnings and `editorial.warning` to this helper so model fallback details remain visible in Actions logs.

Update README's result description to say the Markdown, Issue, and email contain the same compact clickable-title list; diagnostics remain in Actions logs.

- [ ] **Step 4: Run all verification commands**

Run: `PYTHONPYCACHEPREFIX=/tmp/compact-report-pycache python3 -m unittest discover -s tests -v`

Expected: all tests pass.

Run: `PYTHONPYCACHEPREFIX=/tmp/compact-report-pycache python3 -m py_compile src/*.py`

Expected: exit code 0.

Run: `git diff --check`

Expected: no output.

- [ ] **Step 5: Generate a preview from the latest selected JSON records**

Use the committed 2026-08-04 report data or a live fetch in a temporary output directory, then inspect the Markdown. Confirm it contains one headline, no more than ten numbered links, and none of `运行状态`, `为什么值得看`, source names, timestamps, or summaries.

- [ ] **Step 6: Commit documentation and diagnostics**

```bash
git add README.md src/ai_digest.py src/model_editor.py tests/test_ai_digest.py tests/test_model_editor.py
git commit -m "feat: keep digest diagnostics in Actions logs"
```
