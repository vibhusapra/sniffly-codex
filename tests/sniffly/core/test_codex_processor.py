import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sniffly.core.processor import ClaudeLogProcessor
from sniffly.utils.log_finder import slugify_log_path


def _write_jsonl(path: Path, records: list[dict]):
    with path.open("w") as f:
        for record in records:
            f.write(json.dumps(record))
            f.write("\n")


def test_codex_processor_handles_rollout():
    with tempfile.TemporaryDirectory() as temp_dir:
        home = Path(temp_dir)
        log_dir = home / ".codex" / "sessions" / "2025" / "10" / "14"
        log_dir.mkdir(parents=True)
        rollout = log_dir / "rollout-2025-10-14.jsonl"
        records = [
            {
                "timestamp": "2025-10-14T19:11:05Z",
                "type": "session_meta",
                "payload": {
                    "id": "session-123",
                    "timestamp": "2025-10-14T19:11:05Z",
                    "cwd": "/Users/example",
                    "originator": "codex_cli_rs",
                    "cli_version": "0.46.0",
                    "source": "cli",
                },
            },
            {
                "timestamp": "2025-10-14T19:11:05Z",
                "type": "turn_context",
                "payload": {"cwd": "/Users/example", "model": "gpt-5-codex"},
            },
            {
                "timestamp": "2025-10-14T19:11:06Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "list files"}],
                },
            },
            {
                "timestamp": "2025-10-14T19:11:07Z",
                "type": "event_msg",
                "payload": {"type": "agent_reasoning", "text": "Preparing shell command."},
            },
            {
                "timestamp": "2025-10-14T19:11:08Z",
                "type": "response_item",
                "payload": {
                    "type": "reasoning",
                    "summary": [{"type": "summary_text", "text": "Preparing shell command."}],
                },
            },
            {
                "timestamp": "2025-10-14T19:11:09Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "shell",
                    "arguments": json.dumps({"command": ["bash", "-lc", "ls"], "workdir": "."}),
                    "call_id": "call-1",
                },
            },
            {
                "timestamp": "2025-10-14T19:11:10Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call-1",
                    "output": json.dumps({"output": "file_a\\nfile_b\\n", "metadata": {"exit_code": 0}}),
                },
            },
            {
                "timestamp": "2025-10-14T19:11:11Z",
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {
                        "last_token_usage": {
                            "input_tokens": 120,
                            "output_tokens": 40,
                            "cached_input_tokens": 16,
                            "reasoning_output_tokens": 8,
                            "total_tokens": 176,
                        }
                    },
                },
            },
            {
                "timestamp": "2025-10-14T19:11:12Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "Here are your files:\\nfile_a\\nfile_b"},
                    ],
                },
            },
        ]
        _write_jsonl(rollout, records)

        with patch("pathlib.Path.home", return_value=home):
            processor = ClaudeLogProcessor(str(log_dir))
            messages, stats = processor.process_logs()

        assert messages, "Expected messages to be extracted from Codex rollout"

        assistant_messages = [msg for msg in messages if msg["type"] == "assistant"]
        assert assistant_messages, "Expected at least one assistant message"

        # Ensure reasoning text is carried over
        assistant_content = "\n".join(msg["content"] for msg in assistant_messages)
        assert "Preparing shell command." in assistant_content

        # Token counts should be applied to the assistant response
        tokens = assistant_messages[0]["tokens"]
        assert tokens["input"] == 120
        assert tokens["output"] == 40
        assert tokens["cache_read"] == 16

        tool_results = [msg for msg in messages if msg.get("has_tool_result")]
        assert tool_results, "Expected tool result messages"
        assert tool_results[0]["type"] == "user"
        assert "file_a" in tool_results[0]["content"]

        overview = stats["overview"]
        assert overview["project_name"].startswith("Codex CLI")
        assert overview["log_dir_name"] == "codex~2025~10~14"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
