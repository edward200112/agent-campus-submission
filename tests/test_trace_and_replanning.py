from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from asset_agent.agent import run_request
from asset_agent.cli import main
from asset_agent.demo import request_for, run_case
from asset_agent.domain import DomainError, canonical
from asset_agent.model import MockModel
from asset_agent.storage import Store
from asset_agent.trace_view import build_view, format_event, read_view, render_markdown


class TraceAndReplanningTests(unittest.TestCase):
    def test_existing_live_trace_maps_actual_next_action(self):
        path = ROOT / "examples/live/conflict/trace-1.jsonl"
        original = path.read_bytes()
        view = read_view(path)
        self.assertEqual(view["modes"], ["live"])
        query = view["steps"][2]
        self.assertEqual(query["action"], "query_slots")
        self.assertEqual(query["next_action"]["arguments"]["scope"], "day")
        self.assertIn("占用", query["observation_summary"])
        self.assertEqual(view["steps"][-1]["termination"], "finish:needs_confirmation")
        self.assertEqual(path.read_bytes(), original)

    def test_report_preserves_known_reason_mismatch(self):
        view = read_view(ROOT / "examples/live/confirmation/trace-2.jsonl")
        self.assertTrue(view["warnings"])
        self.assertEqual(view["steps"][-1]["action"], "finish")
        self.assertIn("待确认", view["steps"][-1]["decision_summary"])
        self.assertIn("模型依据出现", render_markdown(view))

    def test_next_action_does_not_cross_material_boundary(self):
        base = {"event": "action", "action": "finish", "arguments": {"reason": "结束"},
                "decision_summary": "结束", "observation": {"ok": True, "outcome": "blocked"}}
        view = build_view([{**base, "step": 1, "material_id": "M01"},
                           {**base, "step": 2, "material_id": "M02"}])
        self.assertIsNone(view["steps"][0]["next_action"])

    def test_limit_is_visible_as_termination(self):
        view = read_view(ROOT / "examples/live/step_limit/trace-1.jsonl")
        self.assertEqual(view["steps"][-1]["termination"], "step_limit")
        self.assertIn("step_limit", render_markdown(view))

    def test_malformed_trace_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.jsonl"
            for content in ["not json", canonical({"event": "action"}), ""]:
                with self.subTest(content=content):
                    path.write_text(content)
                    with self.assertRaises(DomainError):
                        read_view(path)

    def test_markdown_escapes_untrusted_html_and_table_separator(self):
        event = {"event": "action", "step": 1, "material_id": "M01", "action": "read_material",
                 "arguments": {"section": "base"}, "decision_summary": "<script>bad</script>|value",
                 "observation": {"ok": True, "section": "base", "material": {"title": "<img src=x>|text"}}}
        markdown = render_markdown(build_view([event]))
        self.assertNotIn("<script>", markdown)
        self.assertNotIn("<img", markdown)
        self.assertIn("\\|", markdown)

    def test_trace_cli_does_not_call_model_and_cannot_overwrite_raw(self):
        source = ROOT / "examples/live/conflict/trace-1.jsonl"
        with patch("asset_agent.cli.make_model", side_effect=AssertionError("must not call model")):
            with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(main(["trace", "--input", str(source), "--format", "json"]), 0)
                self.assertEqual(json.loads(stdout.getvalue())["action_count"], 6)
            with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(main(["trace", "--input", str(source), "--output", str(source)]), 2)
                self.assertEqual(json.loads(stdout.getvalue())["error"], "TRACE_OVERWRITE")

    def test_verbose_output_uses_stderr_and_keeps_stdout_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "input.json"
            path.write_text(canonical(request_for("verbose")))
            with patch("sys.stdout", new_callable=io.StringIO) as stdout, patch("sys.stderr", new_callable=io.StringIO) as stderr:
                code = main(["run", "--mode", "mock", "--input", str(path), "--db", str(root / "db.sqlite"),
                             "--data-dir", str(ROOT / "data"), "--trace", str(root / "trace.jsonl"), "--verbose"])
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(stdout.getvalue())["mode"], "mock")
                self.assertIn("观察：", stderr.getvalue())
                self.assertIn("save_draft", stderr.getvalue())

    def test_each_observation_has_actual_state_and_remaining_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp) / "db.sqlite", [])
            received = []
            try:
                output, events = run_request(request_for("feedback"), MockModel(), store, ROOT / "data", on_event=received.append)
                self.assertEqual(len(received), len(events))
                action = events[0]
                runtime = action["observation"]["runtime"]
                self.assertEqual(runtime["budget"]["remaining_steps"], 59)
                self.assertEqual(runtime["budget"]["remaining_tool_calls"], 49)
                self.assertEqual(runtime["state"]["review_status"], "not_checked")
                self.assertTrue(action["tool_call_id"])
                saved = next(e for e in events if e.get("action") == "save_draft")
                self.assertEqual(saved["observation"]["runtime"]["state"]["draft_state"], "ready")
            finally:
                store.close()

    def test_new_replanning_cases_and_source_catalog_unchanged(self):
        original = (ROOT / "data/materials.json").read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            for case in ["race_conflict", "stale_material", "transient_save_failure"]:
                with self.subTest(case=case):
                    out = Path(temp) / case
                    result = run_case(case, "mock", out, ROOT / "data")
                    self.assertTrue(result["passed"], result)
                    view = read_view(out / "trace-1.jsonl")
                    self.assertTrue((out / "react-1.md").exists())
                    self.assertTrue(any(not row["observation"]["ok"] for row in view["steps"]))
        self.assertEqual((ROOT / "data/materials.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
