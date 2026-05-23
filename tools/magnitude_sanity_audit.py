#!/usr/bin/env python3
"""magnitude_sanity_audit.py — audit closed + active picks for implausible
TP/SL magnitudes (M-108). The caller for alpha_engine.magnitude_sanity_gate.

Runs the magnitude-sanity gate over the ledgers and reports, per asset class
and per strategy, how many picks carry a fantasy take-profit / stop-loss.
Read-only; writes reports/magnitude_sanity_audit_<UTC>.md.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from alpha_engine.magnitude_sanity_gate import (  # noqa: E402
    implied_move_pct, is_magnitude_plausible,
)

LEDGERS = [
    "alpha_engine/data/closed_picks.json",
    "alpha_engine/data/active_picks.json",
]
OUT_DIR = os.path.join(REPO, "reports")


def _load(rel):
    path = os.path.join(REPO, rel)
    if not os.path.isfile(path):
        return []
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(d, dict):
        d = list(d.values())
    return [r for r in d if isinstance(r, dict)]


def main() -> int:
    total = 0
    failed = 0
    by_class = defaultdict(lambda: [0, 0])      # class -> [n, n_fail]
    by_strategy = defaultdict(lambda: [0, 0])   # strat -> [n, n_fail]
    worst = []  # (move_pct, symbol, strategy, reason)

    for rel in LEDGERS:
        for p in _load(rel):
            total += 1
            ac = str(p.get("asset_class") or "?").upper()
            strat = str(p.get("strategy") or p.get("source_system") or "?")
            by_class[ac][0] += 1
            by_strategy[strat][0] += 1
            ok, reason = is_magnitude_plausible(p)
            if not ok:
                failed += 1
                by_class[ac][1] += 1
                by_strategy[strat][1] += 1
                tp_m = implied_move_pct(p.get("entry_price"),
                                        p.get("take_profit")) or 0.0
                worst.append((tp_m, str(p.get("symbol") or "?"), strat, reason))

    worst.sort(key=lambda x: -x[0])
    lines = [
        "# Magnitude-Sanity Audit (M-108)",
        "",
        "- generated: %s" % datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "- picks scanned: %d" % total,
        "- **implausible-magnitude picks: %d (%.1f%%)**" % (
            failed, 100.0 * failed / max(total, 1)),
        "",
        "## By asset class",
        "",
        "| class | picks | implausible | % |",
        "|---|---|---|---|",
    ]
    for ac, (n, nf) in sorted(by_class.items(), key=lambda kv: -kv[1][1]):
        lines.append("| %s | %d | %d | %.1f%% |" % (
            ac, n, nf, 100.0 * nf / max(n, 1)))
    lines += ["", "## Strategies with the most implausible picks", ""]
    bad = sorted(((s, v) for s, v in by_strategy.items() if v[1] > 0),
                 key=lambda kv: -kv[1][1])[:15]
    for s, (n, nf) in bad:
        lines.append("- `%s` — %d/%d implausible" % (s, nf, n))
    if worst:
        lines += ["", "## Worst 15 (largest implied TP)", ""]
        for mv, sym, strat, reason in worst[:15]:
            lines.append("- %s `%s` — implied TP %.1f%% — %s" % (
                sym, strat, mv * 100, reason))
    report = "\n".join(lines) + "\n"

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = os.path.join(OUT_DIR, "magnitude_sanity_audit_%s.md" % stamp)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(report)
    print("written -> reports/magnitude_sanity_audit_%s.md" % stamp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
