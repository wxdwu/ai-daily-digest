from pathlib import Path
import unittest


class WorkflowTests(unittest.TestCase):
    def test_workflow_runs_daily_at_nine_beijing_time(self):
        workflow = Path(".github/workflows/ai-daily.yml").read_text(encoding="utf-8")

        self.assertIn('cron: "0 1 * * *"', workflow)
        self.assertNotIn('cron: "0 23 * * *"', workflow)

    def test_workflow_does_not_depend_on_retired_github_models(self):
        workflow = Path(".github/workflows/ai-daily.yml").read_text(encoding="utf-8")
        self.assertNotIn("models: read", workflow)
        self.assertNotIn("GITHUB_MODELS_MODEL", workflow)
        self.assertIn("LLM_API_KEY: ${{ secrets.LLM_API_KEY }}", workflow)

    def test_workflow_runs_digest_as_module(self):
        workflow = Path(".github/workflows/ai-daily.yml").read_text(encoding="utf-8")
        self.assertIn("python -m src.ai_digest", workflow)

    def test_email_is_the_only_required_notification_channel(self):
        workflow = Path(".github/workflows/ai-daily.yml").read_text(encoding="utf-8")

        self.assertNotIn("issues: write", workflow)
        self.assertNotIn("Create or update daily issue", workflow)
        self.assertNotIn("publish_issue.py", workflow)
        self.assertNotRegex(workflow, r"(?s)- name: Send email\n\s+if:")
        self.assertIn('run: python src/send_email.py --date "$REPORT_DATE"', workflow)


if __name__ == "__main__":
    unittest.main()
