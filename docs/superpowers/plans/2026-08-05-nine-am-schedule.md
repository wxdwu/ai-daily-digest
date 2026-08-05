# Nine AM Schedule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send the daily AI digest at 09:00 Asia/Shanghai instead of 07:00.

**Architecture:** Keep GitHub Actions as the scheduler and convert Beijing 09:00 to UTC 01:00. Protect the cron contract with the existing workflow test and update human-facing documentation in the same change.

**Tech Stack:** GitHub Actions YAML, Python `unittest`, Markdown.

## Global Constraints

- Use exactly one daily cron entry: `0 1 * * *`.
- Keep `workflow_dispatch` unchanged.
- Keep all digest and email steps unchanged.
- Document that GitHub may delay scheduled jobs by several minutes.

---

### Task 1: Change the daily schedule

**Files:**
- Modify: `tests/test_workflow.py`
- Modify: `.github/workflows/ai-daily.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: GitHub Actions UTC cron scheduling.
- Produces: one daily run at 01:00 UTC, equivalent to 09:00 Asia/Shanghai.

- [ ] **Step 1: Add a failing schedule assertion**

```python
def test_workflow_runs_daily_at_nine_beijing_time(self):
    workflow = WORKFLOW.read_text(encoding="utf-8")
    self.assertIn('cron: "0 1 * * *"', workflow)
    self.assertNotIn('cron: "0 23 * * *"', workflow)
```

- [ ] **Step 2: Verify RED**

Run `python3 -m unittest -v tests.test_workflow.WorkflowTests.test_workflow_runs_daily_at_nine_beijing_time`.

Expected: FAIL because the workflow still contains `0 23 * * *`.

- [ ] **Step 3: Implement the schedule**

Change the cron to `0 1 * * *`, update its comment to `01:00 UTC = 09:00 Asia/Shanghai`, and replace both README references to 07:00 with 09:00.

- [ ] **Step 4: Verify GREEN and run the full suite**

Run `python3 -m unittest discover -s tests -v` and `git diff --check`.

Expected: all tests pass and the diff check prints nothing.

- [ ] **Step 5: Commit and publish**

```bash
git add .github/workflows/ai-daily.yml tests/test_workflow.py README.md
git commit -m "chore: send daily digest at nine"
git fetch origin
git rebase origin/main
git push origin HEAD:main
```
