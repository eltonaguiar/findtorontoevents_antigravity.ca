"""End-to-end canary: run the ledger exactly as the scheduled workflow does.

The unit suites exercise helpers; this runs the real CLI with the real flags
(``--history``/``--history-write``/``--persistence-runs``/``--prev-ledger``/
``--max-churn``) against a tiny synthetic payload. It is the test that would have
caught the 2026-11-19 outage in one shot:

* duplicate ``--history`` -> argparse conflict before any scoring;
* missing ``require_alpha`` kwarg -> TypeError inside main();
* a dropped ``denylist_hits`` key -> absent from the output.

It also checks the report shape the dashboards depend on.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _row(i: int) -> dict:
    win = i % 3 != 0
    return {
        "symbol": f"SYM{i % 4}USDT",
        "asset_class": "CRYPTO",
        "strategy": "canary_strategy",
        "direction": "LONG",
        "source_system": "src_a" if i % 2 else "src_b",
        "entry_price": 100.0,
        "exit_price": 104.0 if win else 98.0,
        "pnl_pct": 4.0 if win else -2.0,
        "status": "WON" if win else "LOST",
        "exit_reason": "TP" if win else "STOP",
        "closed_at": f"2026-11-19T{(i // 60) % 24:02d}:{i % 60:02d}:00Z",
    }


def test_cli_runs_end_to_end_and_emits_the_report_contract(tmp_path):
    rows = [_row(i) for i in range(150)]
    picks = tmp_path / "pipeline_data.json"
    picks.write_text(json.dumps({
        "generated_at": "2026-11-19T23:00:00Z",
        "picks": {"recent_closed": rows},
        "summary": {"total_closed_picks": len(rows),
                    "valid_closed_picks": len(rows),
                    "integrity_excluded": 0, "auto_expired_excluded": 0},
    }))
    out = tmp_path / "ledger.json"
    hist = tmp_path / "history.json"
    prev = tmp_path / "prev.json"
    prev.write_text(json.dumps({"cells": []}))

    env = dict(os.environ)
    env["AUDIT3_DENYLIST_HIT_LOG"] = str(tmp_path / "hits.jsonl")
    env.pop("AUDIT3_DENYLIST_DISABLED", None)

    r = subprocess.run(
        [sys.executable, "-m", "alpha_engine.audit3_tribunal",
         "--picks", str(picks), "--out", str(out),
         "--history", str(hist), "--history-write",
         "--persistence-runs", "2",
         "--prev-ledger", str(prev), "--max-churn", "0.30"],
        cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 0, (r.stdout[-2000:], r.stderr[-3000:])

    d = json.loads(out.read_text())
    assert d["schema"] == "audit3.v1"
    for key in ("coverage", "classes", "cells", "verdict_churn",
                "persistence", "denylist_hits", "selection_alpha", "summary"):
        assert key in d, f"report lost key: {key}"
    assert d["coverage"]["denominator"]["mode"] in ("canonical", "payload_slice")
    assert d["persistence"]["available"] is True
    # The ledger dedupes mirror/duplicate rows, so assert the contract rather
    # than an exact count: rows scored must match the coverage numerator.
    assert d["summary"]["n_rows"] > 0
    assert d["coverage"]["scored_rows"] == d["summary"]["n_rows"]
    # The sidecar must be written so the next run can apply persistence.
    assert hist.exists()
    assert json.loads(hist.read_text())["schema"] == "audit3.verdict_history.v1"
