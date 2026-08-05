# Email-Only Concise AI Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send the daily AI digest only by email, with clickable titles, category/time metadata, one short introduction, no source label, and no “为什么值得看” section.

**Architecture:** Keep the existing fetch, validation, ranking, model, archive, and artifact pipeline. Extend the shared Markdown renderer to include the approved compact context, render that Markdown into a safe mobile-friendly HTML email alternative, and remove the GitHub Issue action from the workflow.

**Tech Stack:** Python 3.12 standard library, `unittest`, GitHub Actions YAML, SMTP SSL/STARTTLS.

## Global Constraints

- Every title links directly to a validated Chinese article and is at most 35 visible characters.
- Each item shows category and local publication time, but never the source name.
- Each item shows exactly one short introduction and never “为什么值得看”.
- The report contains at most 10 items.
- SMTP is the only notification channel; missing configuration or delivery failure fails the workflow without exposing Secret values.
- The Markdown archive, plain-text email, and HTML email use the same report content.
- No third-party Python dependency is added.

---

### Task 1: Render the approved report body

**Files:**
- Modify: `tests/test_chinese_digest.py`
- Modify: `src/chinese_digest.py`

**Interfaces:**
- Consumes: `ChineseCandidate`, `EditorialResult`, and `render_chinese_report(...)`.
- Produces: Markdown items containing clickable title, ``category · MM-DD HH:MM``, and one editorial/candidate summary.

- [ ] **Step 1: Write the failing report test**

Change the report assertion to require the approved content and reject the hidden fields:

```python
candidate.published = datetime(2026, 8, 4, 1, 27, tzinfo=timezone.utc)
editorial.selected_items[0]["summary"] = "推理成本倒挂，团队正跨云重构 GPU 集群。"
self.assertIn("1. [英伟达推理平台迎来更新](https://example.cn/c1)", report)
self.assertIn("`AI Infra` · `08-04 09:27`", report)
self.assertIn("推理成本倒挂，团队正跨云重构 GPU 集群。", report)
self.assertNotIn("示例中文媒体", report)
self.assertNotIn("为什么值得看", report)
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m unittest tests.test_chinese_digest.ReportTests.test_report_has_clickable_title_metadata_and_short_intro -v`

Expected: FAIL because the current compact renderer omits metadata and the introduction.

- [ ] **Step 3: Implement the minimal renderer change**

For each selected candidate, resolve the title and one short summary, convert `candidate.published` to the configured local timezone, and append:

```python
lines.extend(
    [
        f"{index}. [{title}]({candidate.url})",
        "",
        f"   `{candidate.category_label}` · `{published:%m-%d %H:%M}`",
        "",
        f"   {_compact_summary(str(edited.get('summary') or candidate.summary))}",
        "",
    ]
)
```

Implement `_compact_summary(value: str, limit: int = 120) -> str` by collapsing whitespace and truncating overlong text with `…`. Do not read or render `candidate.source` or `edited["why"]`.

- [ ] **Step 4: Run report tests and verify GREEN**

Run: `python -m unittest tests.test_chinese_digest.ReportTests -v`

Expected: all report tests pass; the empty report remains short.

- [ ] **Step 5: Commit the report behavior**

```bash
git add tests/test_chinese_digest.py src/chinese_digest.py
git commit -m "feat: add concise context to AI digest"
```

### Task 2: Send a clickable HTML email alternative

**Files:**
- Create: `tests/test_send_email.py`
- Modify: `src/send_email.py`

**Interfaces:**
- Produces: `render_report_html(report: str) -> str` and `build_message(report: str, date: str, sender: str, to: list[str], cc: list[str]) -> EmailMessage`.
- Consumes: the exact Markdown emitted by `render_chinese_report(...)`.

- [ ] **Step 1: Write failing email rendering tests**

Add tests that call the two public helpers and assert real message behavior:

```python
html_body = render_report_html(report)
self.assertIn('<a href="https://example.cn/c1">英伟达 &amp; GPU</a>', html_body)
self.assertIn("AI Infra", html_body)
self.assertNotIn("<script>", html_body)

message = build_message(report, "2026-08-05", "from@example.com", ["to@example.com"], [])
self.assertEqual(message.get_content_type(), "multipart/mixed")
self.assertIsNotNone(message.get_body(preferencelist=("html",)))
self.assertEqual(message.get_body(preferencelist=("plain",)).get_content().strip(), report.strip())
self.assertEqual(len(list(message.iter_attachments())), 1)
```

- [ ] **Step 2: Run the email tests and verify RED**

Run: `python -m unittest tests.test_send_email -v`

Expected: import failure because `render_report_html` and `build_message` do not exist.

- [ ] **Step 3: Implement safe HTML and message builders**

Use `html.escape(..., quote=True)` for every title, URL, metadata value, summary, and fallback line. Recognize only the report's heading, lead paragraph, numbered Markdown links, backtick metadata line, and summary text. Wrap them in a responsive HTML document with inline CSS. Build the message as:

```python
message.set_content(report)
message.add_alternative(render_report_html(report), subtype="html")
message.add_attachment(
    report.encode("utf-8"),
    maintype="text",
    subtype="markdown",
    filename=f"ai-daily-{date}.md",
)
```

Refactor `main()` to call `build_message(...)`; preserve SSL and STARTTLS delivery behavior and address parsing.

- [ ] **Step 4: Run email tests and verify GREEN**

Run: `python -m unittest tests.test_send_email -v`

Expected: all email structure and escaping tests pass.

- [ ] **Step 5: Commit HTML email support**

```bash
git add tests/test_send_email.py src/send_email.py
git commit -m "feat: send clickable HTML digest emails"
```

### Task 3: Make email the only notification channel

**Files:**
- Create: `tests/test_workflow.py`
- Modify: `.github/workflows/ai-daily.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: SMTP Secrets already exposed in the workflow environment.
- Produces: one unconditional `Send email` action after report archiving; no Issue permission or publishing step.

- [ ] **Step 1: Write a failing workflow policy test**

Add a standard-library test that reads the YAML as text:

```python
workflow = Path(".github/workflows/ai-daily.yml").read_text(encoding="utf-8")
self.assertNotIn("issues: write", workflow)
self.assertNotIn("Create or update daily issue", workflow)
self.assertNotIn("publish_issue.py", workflow)
self.assertNotRegex(workflow, r"(?s)- name: Send email\n\s+if:")
self.assertIn('run: python src/send_email.py --date "$REPORT_DATE"', workflow)
```

- [ ] **Step 2: Run the workflow test and verify RED**

Run: `python -m unittest tests.test_workflow -v`

Expected: FAIL because the workflow still grants Issue permission, invokes `publish_issue.py`, and conditionally skips email.

- [ ] **Step 3: Update workflow and operator documentation**

Remove `issues: write`, the complete Issue step, and the email step's `if:` expression. Update README to state that reports are available in the repository/artifact and are delivered only by email. Remove `CREATE_DAILY_ISSUE` instructions. Document the approved item format and state explicitly:

```text
RSS 抓取、报告生成、归档和 SMTP 邮件不消耗大模型 Token。只有同时配置
LLM_API_KEY、LLM_ENDPOINT、LLM_MODEL 时，每份报告才调用一次外部模型并按服务商计费。
```

- [ ] **Step 4: Run workflow and full tests**

Run: `python -m unittest tests.test_workflow -v`

Expected: workflow policy test passes.

Run: `python -m unittest discover -s tests -v`

Expected: the entire suite passes without warnings or errors.

- [ ] **Step 5: Commit email-only delivery**

```bash
git add tests/test_workflow.py .github/workflows/ai-daily.yml README.md
git commit -m "ci: deliver AI digest by email only"
```

### Task 4: Verify the real output and publish

**Files:**
- Verify: `reports/latest.md`
- Verify: `.github/workflows/ai-daily.yml`

**Interfaces:**
- Consumes: all changes from Tasks 1-3.
- Produces: a tested `main` branch that the user can run with the GitHub Actions `Run workflow` button.

- [ ] **Step 1: Compile production modules**

Run: `PYTHONPYCACHEPREFIX=/tmp/ai-daily-pycache python -m py_compile src/ai_digest.py src/chinese_digest.py src/model_editor.py src/send_email.py`

Expected: exit code 0 with no output.

- [ ] **Step 2: Generate and inspect a real report**

Run: `python -m src.ai_digest --ignore-seen`

Expected: `reports/latest.md` contains no source label and no “为什么值得看”; each non-empty item has title, category/time, and one introduction.

- [ ] **Step 3: Re-run the complete suite and inspect repository state**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass.

Run: `git diff --check && git status --short --branch`

Expected: no whitespace errors; only the intentionally regenerated report files may be modified.

- [ ] **Step 4: Synchronize and publish**

Fetch `origin/main`, integrate any newer automated report commit without discarding feature commits, then push the tested feature history to `main`.

- [ ] **Step 5: Confirm the handoff**

Give the user the exact SMTP Secrets required and the GitHub path `Actions → 每日 AI 速报 → Run workflow`, including the fact that a missing email Secret now produces an explicit failure.
