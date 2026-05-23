"""Generate a P5 SYNTHESIS briefing for one asset class run.

Inlines the run's P3 backtest results + P4 cross-test verdicts + the
verified P1 citations. Asks the swarm to vote GO/MIXED/NO_EDGE per
candidate + draft a Wiring Plan when GO.

Usage:
  python -m tools.research.build_p5_briefing --class bond \\
    --run research/asset_class/bond/run_2026-05-11T19-01-40Z
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SWARM_RUNS = REPO_ROOT / "swarm_runs"


TEMPLATE = """# {CLASS_UPPER} research P5 — SYNTHESIS swarm briefing

You are one of 3 AI engines voting on the {CLASS_UPPER} research run at {RUN_ID}.

P3 backtest + P4 cross-test are complete. Numbers are real (yfinance prices, SMA-crossover proxy of spec.entry, 5y window, 5bp round-trip costs) but the signal is SIMPLIFIED — spec.entry text is not yet parsed faithfully. A faithful-signal translator is queued for v3.

## Per-candidate evidence

{PER_CANDIDATE_BLOCK}

## Tier-2 floor (CLAUDE.md MAJOR GOAL)

PF ≥ 1.5, WR ≥ 50%, MDD < 20%, n ≥ 100 trades.

## Your mandate

Vote GO / MIXED / NO_EDGE per candidate. For GO verdicts, draft a Wiring Plan (per CLAUDE.md Wire-Up Rule) — what file gets the caller, what trust_score to seed, what feature flag gates it.

If most candidates fail T2 floor (esp. n<100), the run-level verdict should be MIXED or NO_EDGE — DO NOT fabricate GO just because backtest PF is high. n<30 is too small for any reliable verdict; flag as "needs longer history" rather than GO.

## Output schema (JSON-strict)

```json
{{
  "schema_version": "v1",
  "engine": "<your name>",
  "asset_class": "{CLASS_UPPER}",
  "run_id": "{RUN_ID}",
  "synthesis": [
    {{
      "spec_id": "<from list above>",
      "verdict": "GO|MIXED|NO_EDGE",
      "rationale": "1-3 sentences citing PF/WR/MDD/n + cross-test + simplified-signal caveat",
      "wiring_plan": "if GO: paste-ready 1-paragraph wiring plan. else empty string."
    }}
  ],
  "run_verdict": "GO|MIXED|NO_EDGE",
  "run_rationale": "1-paragraph overall — what edge surfaced (if any), what's blocked on n / faithful-signal, retry conditions"
}}
```

Return ONLY the JSON object. No prose preamble, no markdown fence.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="asset_class", required=True)
    ap.add_argument("--run", type=Path, required=True,
                    help="research/asset_class/<class>/run_<ts>/ directory")
    args = ap.parse_args()
    cls = args.asset_class
    run_dir = args.run.resolve()

    if not run_dir.exists():
        print(f"ERROR: run dir not found: {run_dir}")
        return 1

    p2 = json.loads((run_dir / "p2_candidates.json").read_text(encoding="utf-8"))
    p3 = json.loads((run_dir / "p3_backtest.json").read_text(encoding="utf-8"))
    p4 = json.loads((run_dir / "p4_cross_test.json").read_text(encoding="utf-8"))

    p2_by = {s["spec_id"]: s for s in p2}
    p3_by = {r["spec_id"]: r for r in p3}
    p4_by = {r["spec_id"]: r for r in p4}

    blocks = []
    for spec_id in p2_by:
        s = p2_by[spec_id]
        b = p3_by.get(spec_id, {})
        c = p4_by.get(spec_id, {})
        blocks.append(
            f"### `{spec_id}` ({s.get('proposed_by_engine','?')})\n"
            f"  - entry: {s.get('entry','')}\n"
            f"  - exit: {s.get('exit','')}\n"
            f"  - sizing: {s.get('sizing','')}\n"
            f"  - universe: {s.get('universe',[])}\n"
            f"  - regime: {s.get('regime_filter','')}\n"
            f"  - P3: PF={b.get('pf','?')} WR={b.get('wr','?')}% MDD={b.get('mdd','?')}% Sharpe={b.get('sharpe','?')} n={b.get('n_trades','?')}\n"
            f"  - P4: {c.get('verdict','?')} (max|ρ|={c.get('max_rho','?')} vs {c.get('max_rho_strategy','?')})\n"
            f"  - notes: {b.get('notes','')[:150]}\n"
        )

    out = TEMPLATE.format(
        CLASS_UPPER=cls.upper(),
        RUN_ID=run_dir.name,
        PER_CANDIDATE_BLOCK="\n".join(blocks),
    )

    out_path = SWARM_RUNS / f"briefing_research_{cls}_p5_{run_dir.name}.md"
    out_path.write_text(out, encoding="utf-8")
    print(f"wrote {out_path} ({len(out)} bytes)")
    print(f"  candidates evidenced: {len(p2_by)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
