# Polished One-screen Email Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact daily-focus headline and email-safe visual hierarchy while keeping ten complete clickable titles within roughly one mobile screen.

**Architecture:** Reuse `EditorialResult.storm_summary` as the single display headline, then serialize it as the first plain-text line before the Markdown link list. Enhance `render_report_html` to parse that headline and render a compact, escaped header plus inline-styled links that survive mobile email-client CSS rewriting.

**Tech Stack:** Python standard library, `unittest`, Markdown-compatible plain text, inline HTML email CSS, GitHub Actions.

## Global Constraints

- Keep at most 10 complete Chinese titles; never truncate them with ellipsis.
- Display no item summaries, tags, sources, timestamps, “为什么值得看”, or attachments.
- The focus headline is 14–24 visible characters and avoids “猛料” and “一页看完”.
- Use 14px list text, 1.35 line height, 5px vertical item padding, and email-safe inline styles.
- Escape every displayed headline, title, and URL.
- Preserve `multipart/alternative`, the existing SMTP settings, and the existing email subject.

---

### Task 1: Put the editorial focus headline in the report

**Files:**
- Modify: `tests/test_chinese_digest.py`
- Modify: `src/chinese_digest.py`
- Modify: `tests/test_model_editor.py`
- Modify: `src/model_editor.py`

**Interfaces:**
- Consumes: `EditorialResult.storm_summary: str` and the existing selected candidate list.
- Produces: `render_chinese_report(...) -> str` with `{headline}\n\n{numbered links}\n` when items exist.

- [ ] **Step 1: Write failing report and fallback-headline tests**

Change the report expectation to the literal shape:

```python
self.assertEqual(
    report,
    "算力基础设施与智能体落地提速\n\n"
    "1. [英伟达推理平台迎来更新](https://example.cn/c1)\n",
)
```

Change fallback expectations to `大模型与 AI Agent 成为今日焦点` and `今日聚焦 AI Infra`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
python3 -m unittest -v tests.test_chinese_digest.ReportTests tests.test_model_editor.ModelEditorTests
```

Expected: report tests fail because the headline is absent; fallback tests fail with the old “一页看完” copy.

- [ ] **Step 3: Implement the compact focus headline**

In `fallback_editorial`, emit `今日聚焦 {category}` for one category and `{first}与 {last} 成为今日焦点` for multiple categories, preserving correct English spacing. Update the model prompt to request `storm_summary（14到24字的当日内容焦点，不使用“猛料”或“一页看完”）`. In `render_chinese_report`, normalize the non-empty summary and prepend it before the link list.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the command from Step 2. Expected: all report and editor tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/chinese_digest.py src/model_editor.py tests/test_chinese_digest.py tests/test_model_editor.py
git commit -m "feat: add compact daily focus headline"
```

### Task 2: Render a polished mobile email hierarchy

**Files:**
- Modify: `tests/test_send_email.py`
- Modify: `src/send_email.py`

**Interfaces:**
- Consumes: the first non-link report line as the focus headline and numbered Markdown links.
- Produces: escaped HTML with one `.digest-headline` block and the same number of clickable titles.

- [ ] **Step 1: Write a failing HTML rendering test**

Use a report beginning with `算力基础设施与智能体落地提速`, then assert:

```python
self.assertIn('<h1 class="digest-headline"', html_body)
self.assertIn("算力基础设施与智能体落地提速", html_body)
self.assertIn("AI DAILY · 2 条精选", html_body)
self.assertIn("text-decoration: none !important", html_body)
self.assertIn("word-break: normal", html_body)
self.assertNotIn("word-break: break-all", html_body)
```

Keep the existing special-character escaping and no-attachment assertions.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest -v tests.test_send_email
```

Expected: failure because no focus block exists and links still use `break-all`.

- [ ] **Step 3: Implement email-safe inline styling**

Render the headline in a shallow pale-blue block with escaped content and the item count. Add inline styles to each anchor: deep blue-gray, 14px, 600 weight, 1.35 line height, no underline, `overflow-wrap:anywhere`, and `word-break:normal`. Retain a matching `<style>` fallback and semantic `<ol>/<li>` structure.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the command from Step 2. Expected: all email tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/send_email.py tests/test_send_email.py
git commit -m "style: polish compact AI email"
```

### Task 3: Preview, verify, publish, and run

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the latest generated report and the GitHub Actions manual-dispatch workflow.
- Produces: a verified `main` commit and a completed manual workflow run.

- [ ] **Step 1: Update the output contract**

Document the single dynamic focus headline, full clickable titles, no per-item metadata, and no attachment.

- [ ] **Step 2: Generate and visually inspect a representative HTML preview**

Render 10 realistic long titles at a mobile viewport. Confirm the headline is compact, titles remain complete, English words do not break unnecessarily, and the content remains roughly one screen tall.

- [ ] **Step 3: Run full verification**

```bash
python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/ai-daily-pycache python3 -m py_compile src/*.py
git diff --check
```

Expected: all tests pass, compilation exits 0, and `git diff --check` prints nothing.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md
git commit -m "docs: describe polished focus email"
```

- [ ] **Step 5: Rebase and publish**

Fetch `origin`, rebase on the latest `origin/main`, rerun Step 3, and push `HEAD:main` without force.

- [ ] **Step 6: Trigger and monitor GitHub Actions**

Run the `ai-daily.yml` workflow on `main` with `lookback_hours=36` and `include_seen=true`. Wait for completion and inspect the build and email-send steps. Report only after the workflow finishes successfully or provide the exact failing step if it does not.
