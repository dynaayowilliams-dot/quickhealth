import unittest
from types import SimpleNamespace
from unittest.mock import patch

from quickhealth.workflow import _UsageRecordingClient


class UsageMetricsTests(unittest.TestCase):
    def test_client_proxy_records_only_token_counts_and_elapsed_time(self):
        response = SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=123, completion_tokens=45),
            choices=[],
        )
        original = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_kwargs: response)
            )
        )
        with patch("quickhealth.workflow.record_model_usage") as record:
            wrapped = _UsageRecordingClient(original, "fictional-id")
            self.assertIs(wrapped.chat.completions.create(model="fictional-model"), response)
        record.assert_called_once()
        session_id, input_tokens, output_tokens, elapsed_ms = record.call_args.args
        self.assertEqual((session_id, input_tokens, output_tokens), ("fictional-id", 123, 45))
        self.assertGreaterEqual(elapsed_ms, 0)

    def test_missing_provider_usage_is_not_recorded(self):
        response = SimpleNamespace(choices=[])
        original = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_kwargs: response)
            )
        )
        with patch("quickhealth.workflow.record_model_usage") as record:
            _UsageRecordingClient(original, "fictional-id").chat.completions.create()
        record.assert_not_called()


if __name__ == "__main__":
    unittest.main()
