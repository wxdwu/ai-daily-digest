import json
import unittest

from src.model_editor import edit_candidates


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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


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
        calls = []

        def opener(request, timeout):
            calls.append(json.loads(request.data))
            return FakeResponse(completion)

        result = edit_candidates([candidate_dict("c1")], token="token", opener=opener)
        self.assertEqual([item["id"] for item in result.selected_items], ["c1"])
        self.assertEqual(result.mode, "GitHub Models: openai/gpt-4.1-mini")
        self.assertEqual(len(calls), 1)
        self.assertNotIn("url", calls[0]["messages"][1]["content"])

    def test_invalid_response_returns_deterministic_fallback(self):
        result = edit_candidates(
            [candidate_dict("c1")],
            token="token",
            opener=lambda *a, **k: FakeResponse({"choices": [{"message": {"content": "not json"}}]}),
        )
        self.assertEqual(result.mode, "规则降级")
        self.assertEqual(result.selected_items[0]["id"], "c1")

    def test_missing_token_skips_network_and_falls_back(self):
        called = False

        def opener(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("network must not be called")

        result = edit_candidates([candidate_dict("c1")], token="", opener=opener)
        self.assertFalse(called)
        self.assertEqual(result.mode, "规则降级")

    def test_external_provider_is_named_in_mode(self):
        completion = {
            "choices": [{"message": {"content": json.dumps({
                "storm_summary": "今日 AI 动态集中在推理效率。",
                "selected_items": [{"id": "c1", "title": "中文标题", "summary": "中文摘要", "why": "降低成本"}],
                "trends": [],
            }, ensure_ascii=False)}}]
        }
        result = edit_candidates(
            [candidate_dict("c1")],
            token="external-token",
            endpoint="https://provider.example/v1/chat/completions",
            model="example-model",
            provider_name="外部模型",
            opener=lambda *a, **k: FakeResponse(completion),
        )
        self.assertEqual(result.mode, "外部模型: example-model")


if __name__ == "__main__":
    unittest.main()
