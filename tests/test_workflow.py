from pathlib import Path
import unittest


class WorkflowTests(unittest.TestCase):
    def test_workflow_can_call_github_models_without_user_secret(self):
        workflow = Path(".github/workflows/ai-daily.yml").read_text(encoding="utf-8")
        self.assertIn("models: read", workflow)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", workflow)
        self.assertIn("GITHUB_MODELS_MODEL: ${{ vars.GITHUB_MODELS_MODEL }}", workflow)

    def test_workflow_runs_digest_as_module(self):
        workflow = Path(".github/workflows/ai-daily.yml").read_text(encoding="utf-8")
        self.assertIn("python -m src.ai_digest", workflow)


if __name__ == "__main__":
    unittest.main()
