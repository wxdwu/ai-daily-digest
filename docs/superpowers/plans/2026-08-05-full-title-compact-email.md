# Full-title compact email implementation plan

**Goal:** Keep every digest title complete while making the HTML email dense enough to scan on one phone screen.

**Architecture:** Preserve the current title-only report and multipart email pipeline. Remove the renderer's presentation-layer length cap, ask the optional model editor for concise but complete titles, and tighten only the inline email CSS so compatibility with mobile mail clients is unchanged.

**Tech stack:** Python standard library, `unittest`, GitHub Actions.

---

### Task 1: Stop truncating report titles

**Files:**
- Modify: `tests/test_chinese_digest.py`
- Modify: `src/chinese_digest.py`
- Modify: `tests/test_model_editor.py`
- Modify: `src/model_editor.py`

1. Change the report test to require the complete normalized title and forbid a trailing ellipsis.
2. Run the focused report test and confirm it fails because the current 35-character limit remains.
3. Remove the fixed title length from `_compact_title`, retaining whitespace and trailing-punctuation cleanup.
4. Add a model-editor prompt assertion requiring semantically complete titles without ellipsis truncation.
5. Update the prompt from “不超过35字” to “准确、简洁、语义完整，不得使用省略号截断”.
6. Run the focused report and model-editor tests until green.

### Task 2: Tighten the HTML email layout

**Files:**
- Modify: `tests/test_send_email.py`
- Modify: `src/send_email.py`

1. Add assertions for 14px title text, 1.35 line height, and 5px vertical item padding.
2. Run the focused email test and confirm it fails against the existing 17px/10px layout.
3. Update the inline HTML CSS while preserving full-width wrapping and safe escaped links.
4. Run the focused email tests until green.

### Task 3: Verify and publish

**Files:**
- Modify: `README.md` if the documented output contract needs clarification.

1. Run the complete unit-test suite.
2. Compile the Python source and run `git diff --check`.
3. Fetch and rebase onto the latest `origin/main` if necessary.
4. Push the verified commit to `origin/main`.
5. Confirm the remote workflow contains the full-title renderer and compact email CSS.
