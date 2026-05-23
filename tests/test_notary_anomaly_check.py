"""Tests for tools/notary_anomaly_check.py."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "notary_anomaly_check", REPO / "tools" / "notary_anomaly_check.py"
)
nac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nac)


def _entry(n_active=40, n_closed=3500, ts="2026-05-02T04:00:00Z",
           active_hash="sha256:" + "a" * 64,
           summary_hash="sha256:" + "b" * 64, **extra):
    e = {"kind": "notarize",
         "ts_utc": ts,
         "n_active": n_active,
         "n_recent_closed": n_closed,
         "active_picks_hash": active_hash,
         "summary_hash": summary_hash,
         "schema_version": 1}
    e.update(extra)
    return e


class CleanLogTests(unittest.TestCase):
    def test_clean_log_no_alerts(self) -> None:
        entries = [_entry(n_active=40 + i % 3,
                          ts=f"2026-05-02T{4 + i:02d}:00:00Z",
                          active_hash=f"sha256:{i:064x}") for i in range(10)]
        self.assertEqual(nac.detect_anomalies(entries), [])

    def test_empty_log_no_alerts(self) -> None:
        self.assertEqual(nac.detect_anomalies([]), [])


class DetectorTests(unittest.TestCase):
    def test_n_recent_closed_regression(self) -> None:
        entries = [
            _entry(n_closed=3500, ts="2026-05-02T04:00:00Z",
                   active_hash="sha256:" + "a" * 64),
            _entry(n_closed=3450, ts="2026-05-02T05:00:00Z",
                   active_hash="sha256:" + "b" * 64),  # regression!
        ]
        alerts = nac.detect_anomalies(entries)
        kinds = [a["kind"] for a in alerts]
        self.assertIn("n_recent_closed_regression", kinds)

    def test_schema_version_regression(self) -> None:
        e1 = _entry(ts="2026-05-02T04:00:00Z",
                    active_hash="sha256:" + "a" * 64, schema_version=2)
        e2 = _entry(ts="2026-05-02T05:00:00Z",
                    active_hash="sha256:" + "b" * 64, schema_version=1)
        alerts = nac.detect_anomalies([e1, e2])
        kinds = [a["kind"] for a in alerts]
        self.assertIn("schema_version_regression", kinds)

    def test_active_picks_hash_stuck(self) -> None:
        # 8 consecutive entries with the same hash; default max_stuck=6
        entries = [_entry(ts=f"2026-05-02T{4 + i:02d}:00:00Z",
                          n_active=40 + i,
                          active_hash="sha256:" + "f" * 64) for i in range(8)]
        alerts = nac.detect_anomalies(entries)
        kinds = [a["kind"] for a in alerts]
        self.assertIn("active_picks_hash_stuck", kinds)

    def test_n_active_sudden_swing(self) -> None:
        entries = [_entry(n_active=40, ts=f"2026-05-02T{4 + i:02d}:00:00Z",
                          active_hash=f"sha256:{i:064x}") for i in range(8)]
        # Now an outlier:
        entries.append(_entry(n_active=400, ts="2026-05-02T12:00:00Z",
                              active_hash="sha256:" + "f" * 64))
        alerts = nac.detect_anomalies(entries)
        kinds = [a["kind"] for a in alerts]
        self.assertIn("n_active_sudden_swing", kinds)

    def test_malformed_line_flagged(self) -> None:
        entries = [_entry(active_hash="sha256:" + "a" * 64),
                   {"_malformed_line": "{ this is not json"}]
        alerts = nac.detect_anomalies(entries)
        kinds = [a["kind"] for a in alerts]
        self.assertIn("malformed_log_line", kinds)

    def test_identical_triple_repeated(self) -> None:
        # Same (n_active, n_closed, summary_hash) appearing 5 times — the
        # clone_hl_copy placeholder pattern from memory file.
        entries = [_entry(n_active=42, n_closed=3500,
                          ts=f"2026-05-02T{4 + i:02d}:00:00Z",
                          active_hash=f"sha256:{i:064x}",
                          summary_hash="sha256:" + "c" * 64) for i in range(5)]
        alerts = nac.detect_anomalies(entries)
        kinds = [a["kind"] for a in alerts]
        self.assertIn("identical_triple_repeated", kinds)


class ExitCodeTests(unittest.TestCase):
    def test_high_severity_returns_one(self) -> None:
        # Provide a log with malformed line (high severity)
        import tempfile
        import json
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8") as f:
            f.write(json.dumps({"kind": "notarize", "n_active": 40,
                                "n_recent_closed": 100,
                                "active_picks_hash": "x", "summary_hash": "y",
                                "schema_version": 1}) + "\n")
            f.write("{ broken json\n")
            tmp = f.name
        rc = nac.main(["--log-path", tmp, "--quiet"])
        self.assertEqual(rc, 1)

    def test_clean_log_returns_zero(self) -> None:
        import tempfile
        import json
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8") as f:
            for i in range(3):
                f.write(json.dumps({"kind": "notarize",
                                    "ts_utc": f"2026-05-02T0{4+i}:00:00Z",
                                    "n_active": 40 + i,
                                    "n_recent_closed": 3500 + i,
                                    "active_picks_hash": f"sha256:{i:064x}",
                                    "summary_hash": f"sha256:{i+10:064x}",
                                    "schema_version": 1}) + "\n")
            tmp = f.name
        rc = nac.main(["--log-path", tmp, "--quiet"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
