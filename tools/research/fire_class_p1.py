"""Fire a P1 swarm for any asset class.

Generates the briefing on-the-fly from a template (no per-class .md files
needed), writes a temp YAML config, and runs swarm_run.py. Reduces
maintenance cost when expanding to more classes.

Usage:
  python -m tools.research.fire_class_p1 --class equity
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SWARM_RUNS = REPO_ROOT / "swarm_runs"
SWARM_EXAMPLES = REPO_ROOT / "tools" / "swarm" / "examples"

UNIVERSE = {
    "equity": ["SPY", "QQQ", "IWM", "VTI", "VOO", "DIA", "MDY"],
    "crypto": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"],
    "etf": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"],
    "futures": ["DBC", "GSG", "DBA", "USO", "UNG", "PDBC"],
    "commodity": ["GLD", "SLV", "PPLT", "PALL", "CPER", "DBA"],
}

CONTEXT = {
    "equity": "EQUITY currently PF 1.41 / WR 52.7% / n=421 (Tier-2 candidate). Lift PF + n.",
    "crypto": "CRYPTO currently PF 1.25 / WR 44.6% / n=8067 (sub-T2). Quan_engine drag (PF 0.66, 21% vol).",
    "etf": "ETF currently PF 1.24 / WR 55.2% / n=87 (borderline; n→100).",
    "futures": "FUTURES has effectively no production picks. Greenfield exploration.",
    "commodity": "COMMODITY PF 1.78 / WR 46.9% / n=750 (meets T2 PF; lift WR).",
}


def _briefing(asset_class: str) -> str:
    universe = UNIVERSE[asset_class]
    context = CONTEXT[asset_class]
    return f"""# {asset_class.upper()} research P1 — LITERATURE swarm briefing

You are one of 3 AI engines running P1 of the {asset_class.upper()} research pipeline.

## Current state
{context}

## Universe constraint
We trade ETF-style instruments via yfinance: `{universe}`. No single-ticker exotic strategies needing futures contracts, swaps, or OTC instruments.

## Your mandate
Return ≥10 citations on {asset_class.upper()} trading strategies that:
1. Have empirical backtest results in 2010+.
2. Cover diverse styles: momentum, mean reversion, carry, value, vol-targeting, regime-conditional.
3. URLs must resolve. We HEAD-check every URL. >25% hallucination = 0.5x weight; >50% = excluded from P2.

## Trusted domains
ssrn.com, arxiv.org, papers.nber.org, sciencedirect.com, journals.aeaweb.org, federalreserve.gov, bis.org, doi.org, aqr.com, qmom.com.

## Output schema (JSON-strict)
```json
{{
  "schema_version": "v1",
  "engine": "<your name>",
  "asset_class": "{asset_class.upper()}",
  "citations": [
    {{
      "url": "https://...",
      "access_date": "2026-05-11",
      "title": "...",
      "author": "...",
      "year": "2018",
      "claim": "1-paragraph extracted claim",
      "evidence_strength": "peer-reviewed|empirical|anec",
      "instruments_studied": [...],
      "key_metric": "..."
    }}
  ],
  "themes_observed": ["..."],
  "notes_to_p2": "1-paragraph hint"
}}
```

Do NOT invent URLs. Drop unverified citations. Return ONLY the JSON object.
"""


def _yaml(asset_class: str) -> str:
    return f"""name: research_{asset_class}_p1_${{TS}}
prompt_file: swarm_runs/briefing_research_{asset_class}_p1.md
out_dir: swarm_runs/research_{asset_class}_p1_${{TS}}
max_parallel: 3
json_strict: true
strictness: strict

engines:
  - name: cerebras
    sampling:
      temperature: 0.2
      max_tokens: 8000
  - name: deepseek
    model: deepseek-chat
    sampling:
      temperature: 0.2
      max_tokens: 8000
  - name: xai
    sampling:
      temperature: 0.2
      max_tokens: 8000
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="asset_class", required=True,
                    choices=sorted(UNIVERSE.keys()))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cls = args.asset_class

    briefing_path = SWARM_RUNS / f"briefing_research_{cls}_p1.md"
    yaml_path = SWARM_EXAMPLES / f"research_{cls}_p1.yaml"

    briefing_path.write_text(_briefing(cls), encoding="utf-8")
    yaml_path.write_text(_yaml(cls), encoding="utf-8")
    print(f"wrote {briefing_path}")
    print(f"wrote {yaml_path}")

    if args.dry_run:
        print("(dry-run; not firing swarm)")
        return 0

    cmd = ["python", "tools/swarm/swarm_run.py", "--config", str(yaml_path)]
    print(f"firing: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
