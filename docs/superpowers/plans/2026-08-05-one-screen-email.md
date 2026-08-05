# One-Screen AI Email Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the daily email and shared Markdown report to a single compact list of at most 10 clickable Chinese titles, with no headers, metadata, descriptions, or attachments.

**Architecture:** Keep the existing fetch, validation, ranking, editorial, archive, and SMTP pipeline. Narrow the Markdown renderer to numbered links, narrow the HTML renderer to a mobile-friendly ordered link list, and make the email a multipart alternative with plain text and HTML but no mixed attachment layer.

**Tech Stack:** Python 3.12 standard library, `unittest`, SMTP, HTML email.

## Global Constraints

- Non-empty content contains only numbered clickable titles.
- Each title is at most 35 visible characters and links to a validated Chinese article.
- The list contains at most 10 entries.
- No body title, date, summary, category, source, time, explanation, status, or attachment is emitted.
- The email subject remains `每日 AI 速报 · YYYY-MM-DD`.
- A plain-text compatibility part remains but is not an attachment.
- No third-party dependency is added.

---

### Task 1: Render only numbered title links

**Files:**
- Modify: `tests/test_chinese_digest.py`
- Modify: `src/chinese_digest.py`

**Interfaces:**
- Consumes: the existing `render_chinese_report(...)` arguments.
- Produces: Markdown containing only `N. [title](https://...)` lines, or one empty-result sentence.

- [ ] **Step 1: Write the failing report tests**

Replace the expanded report assertion with an exact output assertion:

```python
self.assertEqual(
    report,
    "1. [英伟达推理平台迎来更新](https://example.cn/c1)\n",
)
```

Assert the empty result exactly:

```python
self.assertEqual(report, "本期没有筛出足够可靠的中文 AI 资讯。\n")
```

Keep the existing title truncation, 10-item cap, and unknown-ID assertions.

- [ ] **Step 2: Run report tests and verify RED**

Run: `python3 -m unittest tests.test_chinese_digest.ReportTests -v`

Expected: FAIL because the current report still contains a heading, lead, metadata, and descriptions.

- [ ] **Step 3: Implement the minimal report renderer**

Return the empty sentence when no known item is selected. Otherwise render only:

```python
lines = []
for index, edited in enumerate(selected, 1):
    candidate = by_id[str(edited["id"])]
    title = _compact_title(str(edited.get("title") or candidate.title))
    lines.append(f"{index}. [{title}]({candidate.url})")
return "\n".join(lines) + "\n"
```

Remove summary formatting and renderer-only timezone logic that no longer has a consumer.

- [ ] **Step 4: Run report tests and verify GREEN**

Run: `python3 -m unittest tests.test_chinese_digest.ReportTests -v`

Expected: all report tests pass.

- [ ] **Step 5: Commit the title-only report**

```bash
git add tests/test_chinese_digest.py src/chinese_digest.py
git commit -m "feat: render title-only AI digest"
```

### Task 2: Render a one-screen HTML list without attachments

**Files:**
- Modify: `tests/test_send_email.py`
- Modify: `src/send_email.py`

**Interfaces:**
- Consumes: numbered-link Markdown or the single empty-result sentence.
- Produces: safe HTML containing an ordered title list and an `EmailMessage` with plain and HTML alternatives only.

- [ ] **Step 1: Write failing email structure tests**

Use a two-link report and require the compact list:

```python
self.assertIn("<ol>", html_body)
self.assertIn('<a href="https://example.cn/c1?x=1&amp;y=2">英伟达 &amp; GPU</a>', html_body)
self.assertNotIn("<h1", html_body)
self.assertNotIn("class=\"meta\"", html_body)
```

Require attachment-free multipart alternative output:

```python
self.assertEqual(message.get_content_type(), "multipart/alternative")
self.assertEqual(len(list(message.iter_attachments())), 0)
self.assertIsNotNone(message.get_body(preferencelist=("plain",)))
self.assertIsNotNone(message.get_body(preferencelist=("html",)))
```

- [ ] **Step 2: Run email tests and verify RED**

Run: `python3 -m unittest tests.test_send_email -v`

Expected: FAIL because the current HTML uses article cards and the message includes a Markdown attachment.

- [ ] **Step 3: Implement the compact HTML and remove attachment creation**

Parse only complete numbered HTTPS Markdown links. Render them as one `<ol>` with `<li><a>` entries, escaping title and URL. For an empty report, render one escaped paragraph. Use compact mobile CSS:

```css
main { max-width: 680px; margin: 0 auto; padding: 12px 16px; }
ol { margin: 0; padding-left: 28px; }
li { padding: 10px 0; border-bottom: 1px solid #e8eaed; font-size: 17px; line-height: 1.45; }
```

Keep `message.set_content(report)` and `message.add_alternative(...)`. Delete the `message.add_attachment(...)` call so the top-level MIME type remains `multipart/alternative`.

- [ ] **Step 4: Run email tests and verify GREEN**

Run: `python3 -m unittest tests.test_send_email -v`

Expected: both HTML safety and MIME structure tests pass.

- [ ] **Step 5: Commit the one-screen email**

```bash
git add tests/test_send_email.py src/send_email.py
git commit -m "feat: send one-screen HTML digest"
```

### Task 3: Update documentation, verify, preview, and publish

**Files:**
- Modify: `README.md`
- Verify: `.github/workflows/ai-daily.yml`

**Interfaces:**
- Consumes: the title-only report and attachment-free email from Tasks 1-2.
- Produces: documented and tested `main` behavior ready for `Run workflow`.

- [ ] **Step 1: Update README**

State that the report and email contain only up to 10 clickable titles, that HTML is the primary body, and that no attachment is sent. Remove references to the lead summary, category, time, and short introduction.

- [ ] **Step 2: Run the complete test suite and compile checks**

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests pass.

Run: `PYTHONPYCACHEPREFIX=/tmp/ai-daily-pycache python3 -m py_compile src/ai_digest.py src/chinese_digest.py src/model_editor.py src/send_email.py`

Expected: exit code 0 with no output.

- [ ] **Step 3: Generate a 10-link HTML preview and inspect constraints**

Build a deterministic 10-link Markdown string, call `render_report_html(...)`, and verify that the result contains exactly 10 `<li>` elements, no `<h1>`, no metadata class, and no summary class. Save the temporary preview outside the repository only for local visual inspection.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md
git commit -m "docs: describe one-screen email format"
```

- [ ] **Step 5: Synchronize and publish**

Fetch `origin/main`, rebase the tested commits over any new automated report commit, rerun the full suite, and push `HEAD:main` without force.
