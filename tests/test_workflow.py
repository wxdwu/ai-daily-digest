from pathlib import Path
import unittest


class WorkflowTests(unittest.TestCase):
    def test_workflow_does_not_depend_on_retired_github_models(self):
        workflow = Path(".github/workflows/ai-daily.yml").read_text(encoding="utf-8")
        self.assertNotIn("models: read", workflow)
        self.assertNotIn("GITHUB_MODELS_MODEL", workflow)
        self.assertIn("LLM_API_KEY: ${{ secrets.LLM_API_KEY }}", workflow)

    def test_workflow_runs_digest_as_module(self):
        workflow = Path(".github/workflows/ai-daily.yml").read_text(encoding="utf-8")
        self.assertIn("python -m src.ai_digest", workflow)


if __name__ == "__main__":
    unittest.main()
