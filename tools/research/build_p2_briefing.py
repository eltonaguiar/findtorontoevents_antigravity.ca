"""Generate a P2 briefing for an asset class by:
  1. Loading the latest P1 swarm output for that class
  2. HEAD-checking citation URLs
  3. Inlining the verified subset into the P2 prompt template

Run:
  python -m tools.research.build_p2_briefing --class forex

Produces `swarm_runs/briefing_research_<class>_p2.md` ready for
`python tools/swarm/swarm_run.py --config tools/swarm/examples/research_<class>_p2.yaml`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .p1_loader import load_p1_citations
from .verify_citations import verify_citations

REPO_ROOT = Path(__file__).resolve().parents[2]
SWARM_RUNS = REPO_ROOT / "swarm_runs"

ASSET_UNIVERSE = {
    "bond": ["IEF", "TLT", "SHY", "IEI", "TIP", "LQD", "VCIT", "VCSH", "HYG", "BND", "TIPS", "MBB", "AGG"],
    "forex": ["UUP", "FXE", "FXY", "FXB", "FXA", "FXC", "FXF", "UDN", "CYB", "INR", "BZF"],
    "equity": ["SPY", "QQQ", "IWM", "VTI", "VOO", "DIA", "MDY"],
    "crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"],
    "etf": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"],
    "futures": ["DBC", "GSG", "DBA", "USO", "UNG", "PDBC"],
    "commodity": ["GLD", "SLV", "PPLT", "PALL", "CPER", "DBA"],
}


TEMPLATE = """# {CLASS_UPPER} research P2 — CANDIDATES swarm briefing

You are one of 3 AI engines running P2 of the {CLASS_UPPER} research pipeline. P1 produced {N_TOTAL_CITATIONS} raw citations; {N_VERIFIED} passed HEAD-check verification and are included verbatim below.

Engine vote weights from P1: {WEIGHTS_STR}.

## P1 verified citations ({N_VERIFIED})

```json
{VERIFIED_JSON}
```

## Your mandate

Propose at least 5 backtestable {CLASS_UPPER} strategy specs. Each spec must:

1. Reference ≥1 verified citation (by URL) above. No citing P1 hallucinated URLs.
2. Trade ETF instruments only (we backtest on yfinance daily bars):
   allowed universe = `{UNIVERSE}`. Single-symbol picks OK, multi-leg pairs
   OK. Do not propose strategies needing futures contracts, swaps, options,
   or OTC instruments — exits scope.
3. Have a concrete entry rule, exit rule, and sizing rule expressible in pseudo-code.
4. Have a regime filter or "skip-when" condition (when NOT to fire).
5. Beat the cross-test (we compute ρ + symbol overlap vs every shipped strategy in `dashboard_data.json::systems`).

## Target outcome

Strategies that, when backtested over 2020-2025, can clear Tier-2 floors per CLAUDE.md:
  - PF ≥ 1.5
  - WR ≥ 50%
  - MDD < 20%
  - n ≥ 100 trades

If you BELIEVE the asset class has no scalable retail edge, say so — propose 1-2 "diagnostic" strategies that would CONFIRM no-edge if backtested, and explain in rationale why edge has likely decayed. NO_EDGE verdicts are first-class deliverables; don't fabricate fake edge.

## Output schema (JSON-strict, identical to BOND P2)

```json
{{
  "schema_version": "v1",
  "engine": "<your name>",
  "asset_class": "{CLASS_UPPER}",
  "candidates": [
    {{
      "spec_id": "{class_lower}_<slug>_v1",
      "asset_class": "{CLASS_UPPER}",
      "entry": "exact rule, e.g. 'long UUP when 60d momentum > 0 AND DXY 90d realized vol < 8%'",
      "exit": "e.g. 'exit on momentum sign flip or 30d hold'",
      "sizing": "e.g. 'risk-parity to 8% annualized vol'",
      "universe": ["UUP", "FXE", ...],
      "regime_filter": "e.g. 'skip when VIX > 30 or DXY rolling vol > 12%'",
      "source_refs": ["https://verified-url-1"],
      "proposed_by_engine": "<your name>",
      "expected_pf": 1.5,
      "expected_wr": 51.0,
      "expected_mdd_pct": 15.0,
      "expected_n_per_year": 10,
      "rationale": "1-2 sentences why this should clear T2 floors OR why it might NOT (diagnostic)"
    }}
  ],
  "notes_to_p3": "1-paragraph hint for the backtest pass"
}}
```

Return ONLY the JSON object. No prose preamble, no markdown fence.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="asset_class", required=True,
                    choices=sorted(ASSET_UNIVERSE.keys()))
    args = ap.parse_args()
    cls = args.asset_class

    r1 = load_p1_citations(cls)
    if not r1["citations"]:
        print(f"ERROR: no P1 output found for class={cls}. Run P1 swarm first.")
        return 1

    v = verify_citations(r1["citations"], engine_attribution=r1["engine_attribution"])
    verified = [c for c in v["citations"] if c.verified]
    weights = v["engine_weights"]

    verified_payload = {
        "citations": [
            {
                "url": c.url,
                "title": c.title,
                "author": c.author,
                "year": c.year,
                "claim": c.claim,
                "evidence_strength": c.evidence_strength,
            }
            for c in verified
        ]
    }

    out = TEMPLATE.format(
        CLASS_UPPER=cls.upper(),
        class_lower=cls.lower(),
        N_TOTAL_CITATIONS=len(r1["citations"]),
        N_VERIFIED=len(verified),
        WEIGHTS_STR=", ".join(f"{e} {w}x" for e, w in sorted(weights.items())) or "all 1.0x clean",
        UNIVERSE=ASSET_UNIVERSE[cls],
        VERIFIED_JSON=json.dumps(verified_payload, indent=2, ensure_ascii=False),
    )

    out_path = SWARM_RUNS / f"briefing_research_{cls}_p2.md"
    out_path.write_text(out, encoding="utf-8")
    print(f"wrote {out_path} ({len(out)} bytes)")
    print(f"  verified: {len(verified)}/{len(r1['citations'])}")
    print(f"  weights:  {weights}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
