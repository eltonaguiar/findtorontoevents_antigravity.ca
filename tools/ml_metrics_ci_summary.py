#!/usr/bin/env python3
"""
Emit a short ML metrics summary for GitHub Actions step summary (and stdout).

Reads JSON artifacts written by ML Gatekeeper and Audit ML Consensus when present.
Safe to run locally; only appends to GITHUB_STEP_SUMMARY if that env var is set.

Usage:
  python tools/ml_metrics_ci_summary.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GK_REPORT = ROOT / "ml_gatekeeper" / "models" / "training_report.json"
CS_REPORT = ROOT / "ml_consensus" / "models" / "consensus_report.json"


def _md_block() -> str:
    lines: list[str] = ["## ML metrics (CI artifacts)", ""]

    if GK_REPORT.exists():
        try:
            data = json.loads(GK_REPORT.read_text(encoding="utf-8"))
            lines.append("### ML Gatekeeper")
            tr = data.get("training_data", {})
            lines.append(f"- Samples: {tr.get('n_samples', '?')}  features: {tr.get('n_features', '?')}")
            bt = data.get("backtest", {})
            th = bt.get("true_holdout", {})
            if th:
                lines.append(
                    f"- Holdout AUC: {th.get('auc', '?')}  WR lift %: {th.get('wr_lift_pct', '?')}  "
                    f"passed_n: {th.get('passed_n', '?')}"
                )
            lines.append("")
        except (json.JSONDecodeError, OSError) as e:
            lines.append(f"### ML Gatekeeper\n- (read error: {e})\n")

    if CS_REPORT.exists():
        try:
            data = json.loads(CS_REPORT.read_text(encoding="utf-8"))
            lines.append("### Audit ML consensus")
            if isinstance(data, dict):
                lines.append(f"- generated_at: {data.get('generated_at', '?')}")
                bt = data.get("backtest") or {}
                if bt:
                    lines.append(
                        f"- backtest: consensus_WR={bt.get('consensus_wr', '?')}  "
                        f"single_WR={bt.get('single_wr', '?')}  wr_lift={bt.get('wr_lift', '?')}"
                    )
                ac = data.get("active_consensus") or {}
                if ac:
                    lines.append(
                        f"- active: groups={ac.get('total_groups', '?')}  "
                        f"multi_system={ac.get('multi_system_picks', '?')}"
                    )
            lines.append("")
        except (json.JSONDecodeError, OSError) as e:
            lines.append(f"### Audit ML consensus\n- (read error: {e})\n")

    if len(lines) <= 2:
        lines.append("_No ml_gatekeeper/models/training_report.json or ml_consensus/models/consensus_report.json yet._")
        lines.append("")

    lines.append(f"Artifacts: `{GK_REPORT.relative_to(ROOT)}`, `{CS_REPORT.relative_to(ROOT)}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    text = _md_block()
    print(text)
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    if out:
        try:
            with open(out, "a", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
