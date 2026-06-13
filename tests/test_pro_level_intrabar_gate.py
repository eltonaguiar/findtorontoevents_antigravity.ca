"""Tests for picks-now intrabar gate and strategy tribunal classification."""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.picks_now_intrabar_gate import (  # noqa: E402
    apply_class_fail_gate,
    classify_intrabar_pick,
    load_sym_dir_map,
    normalize_direction,
    normalize_symbol,
    stamp_intrabar_fields,
)
from tools.strategy_kill_tribunal import (  # noqa: E402
    _should_kill,
    classify_verdict,
)


class TestIntrabarGate(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_symbol("BTC-USD"), "BTCUSD")
        self.assertEqual(normalize_direction("STRONG_BUY"), "LONG")

    def test_classify_blocks_bad_wr(self):
        d, status, _ = classify_intrabar_pick("STRONG_BUY", 30.0, 10)
        self.assertEqual(d, "AVOID")
        self.assertEqual(status, "BLOCKED")

    def test_classify_demotes_marginal(self):
        d, status, _ = classify_intrabar_pick("STRONG_BUY", 45.0, 8)
        self.assertEqual(d, "WATCH")
        self.assertEqual(status, "DEMOTED")

    def test_classify_proven_lane(self):
        d, status, _ = classify_intrabar_pick("STRONG_BUY", 55.0, 12)
        self.assertEqual(d, "STRONG_BUY")
        self.assertEqual(status, "PROVEN_LANE")

    def test_class_fail_demotes_equity(self):
        truth = {"EQUITY": {"n": 113, "verdict": "FAIL"}}
        d, note = apply_class_fail_gate("STRONG_BUY", "EQUITY", truth)
        self.assertEqual(d, "WATCH")
        self.assertIn("FAIL", note)

    def test_stamp_intrabar_demotes_amd_like(self):
        sym_map = {"AMD|LONG": {"n": 20, "wr_pct": 25.0, "pf": 0.4}}
        result = {"symbol": "AMD", "class": "EQUITY", "direction": "STRONG_BUY", "signals": "x"}
        out = stamp_intrabar_fields(result, sym_map, {})
        self.assertEqual(out["direction"], "AVOID")
        self.assertEqual(out["intrabar_gate"], "BLOCKED")

    def test_load_sym_dir_empty_missing_file(self):
        self.assertEqual(load_sym_dir_map("/nonexistent/path.json"), {})


class TestTribunal(unittest.TestCase):
    def test_kill_verdict(self):
        self.assertEqual(classify_verdict(40, 0.20, 0.5), "KILL")

    def test_probation_verdict(self):
        self.assertEqual(classify_verdict(20, 0.38, 1.2), "PROBATION")

    def test_keep_verdict(self):
        self.assertEqual(classify_verdict(50, 0.55, 1.6), "KEEP")

    def test_luxalgo_exception(self):
        self.assertFalse(_should_kill("luxalgo_confluence", 38, 0.71))
        self.assertTrue(_should_kill("luxalgo_confluence", 100, 0.35))

    def test_apply_kills_requires_env(self):
        from tools.strategy_kill_tribunal import apply_kills
        with self.assertRaises(RuntimeError):
            apply_kills({"kills": [{"strategy": "rsi_bounce"}]})

    def test_apply_kills_writes_audit(self):
        from tools.strategy_kill_tribunal import apply_kills
        with tempfile.TemporaryDirectory() as td:
            audit_path = os.path.join(td, "emitter_audit.json")
            with patch("tools.strategy_kill_tribunal.AUDIT_FILE", audit_path):
                with patch.dict(os.environ, {"TRIBUNAL_APPLY": "1"}):
                    added = apply_kills({"kills": [{"strategy": "rsi_bounce"}], "generated_at": "t"})
            self.assertIn("rsi_bounce", added)
            with open(audit_path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("rsi_bounce", data["recommended_actions"]["force_kill"])


if __name__ == "__main__":
    unittest.main()
