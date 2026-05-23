"""Tests for tools/pick_provenance_tracker.py."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "pick_provenance_tracker", REPO / "tools" / "pick_provenance_tracker.py"
)
ppt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppt)


def _pick(**fields) -> dict:
    base = {
        "strategy": "demo_alpha",
        "asset_class": "CRYPTO",
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "confidence": 0.7,
        "ml_score": 0.4,
        "entry_price": 65000.0,
        "regime": "BULL",
    }
    base.update(fields)
    return base


class FingerprintTests(unittest.TestCase):
    def test_deterministic_for_identical_input(self) -> None:
        a = _pick()
        b = _pick()
        self.assertEqual(ppt.fingerprint_pick(a), ppt.fingerprint_pick(b))

    def test_changes_on_relevant_field_mutation(self) -> None:
        a = _pick(confidence=0.7)
        b = _pick(confidence=0.71)
        self.assertNotEqual(
            ppt.fingerprint_pick(a), ppt.fingerprint_pick(b)
        )

    def test_unaffected_by_non_provenance_fields(self) -> None:
        # pnl_pct, closed_at, opened_at etc. should NOT affect fingerprint
        a = _pick()
        b = dict(_pick())
        b["pnl_pct"] = 5.0
        b["closed_at"] = "2026-05-02T13:00:00Z"
        b["opened_at"] = "2026-05-02T12:00:00Z"
        self.assertEqual(ppt.fingerprint_pick(a), ppt.fingerprint_pick(b))

    def test_missing_field_fingerprint_stable(self) -> None:
        # Older-schema picks lacking 'regime' should still fingerprint
        # consistently — projection sets None for missing fields.
        a = _pick()
        del a["regime"]
        b = _pick()
        del b["regime"]
        self.assertEqual(ppt.fingerprint_pick(a), ppt.fingerprint_pick(b))

    def test_field_order_independence(self) -> None:
        # JSON canonicalisation should make insertion order irrelevant.
        a = {"strategy": "x", "symbol": "Y", "confidence": 0.5}
        b = {"confidence": 0.5, "symbol": "Y", "strategy": "x"}
        self.assertEqual(ppt.fingerprint_pick(a), ppt.fingerprint_pick(b))

    def test_sha256_format(self) -> None:
        fp = ppt.fingerprint_pick(_pick())
        self.assertTrue(fp.startswith("sha256:"))
        self.assertEqual(len(fp), 7 + 64)


class FingerprintAllTests(unittest.TestCase):
    def test_one_row_per_pick(self) -> None:
        picks = [_pick(symbol=s) for s in ("BTCUSDT", "ETHUSDT", "ADAUSDT")]
        out = ppt.fingerprint_all(picks)
        self.assertEqual(len(out), 3)
        for row in out:
            self.assertIn("fingerprint", row)
            self.assertIn("strategy", row)
            self.assertIn("symbol", row)
            self.assertEqual(row["schema_version"], 1)


class LogRoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.log = Path(self._tmp.name) / "log.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_append_and_query_roundtrip(self) -> None:
        picks = [_pick(symbol="BTCUSDT", confidence=0.7),
                 _pick(symbol="ETHUSDT", confidence=0.6)]
        entries = ppt.fingerprint_all(picks)
        n = ppt.append_log(entries, log_path=self.log,
                            ts_utc="2026-05-02T13:00:00Z",
                            git_sha="abc123def456")
        self.assertEqual(n, 2)

        target = entries[0]["fingerprint"]
        rows = ppt.query_by_fingerprint(target, log_path=self.log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fingerprint"], target)
        self.assertEqual(rows[0]["ts_utc"], "2026-05-02T13:00:00Z")
        self.assertEqual(rows[0]["git_sha"], "abc123def456")

    def test_query_chronological_order(self) -> None:
        picks = [_pick()]  # same fingerprint every run
        entries = ppt.fingerprint_all(picks)
        ppt.append_log(entries, log_path=self.log,
                        ts_utc="2026-05-02T10:00:00Z", git_sha="aaa")
        ppt.append_log(entries, log_path=self.log,
                        ts_utc="2026-05-02T13:00:00Z", git_sha="bbb")
        ppt.append_log(entries, log_path=self.log,
                        ts_utc="2026-05-02T11:00:00Z", git_sha="ccc")
        target = entries[0]["fingerprint"]
        rows = ppt.query_by_fingerprint(target, log_path=self.log)
        self.assertEqual([r["ts_utc"] for r in rows], [
            "2026-05-02T10:00:00Z",
            "2026-05-02T11:00:00Z",
            "2026-05-02T13:00:00Z",
        ])

    def test_query_missing_fingerprint(self) -> None:
        rows = ppt.query_by_fingerprint(
            "sha256:" + "0" * 64, log_path=self.log)
        self.assertEqual(rows, [])

    def test_query_missing_log_file(self) -> None:
        rows = ppt.query_by_fingerprint(
            "sha256:" + "0" * 64,
            log_path=Path("/nonexistent/path/missing.jsonl"))
        self.assertEqual(rows, [])

    def test_skips_malformed_jsonl_lines(self) -> None:
        with self.log.open("w", encoding="utf-8") as f:
            f.write('{"valid": true, "fingerprint": "sha256:aaa"}\n')
            f.write('{ broken json\n')
            f.write('{"valid": true, "fingerprint": "sha256:aaa"}\n')
        rows = ppt.query_by_fingerprint("sha256:aaa", log_path=self.log)
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
