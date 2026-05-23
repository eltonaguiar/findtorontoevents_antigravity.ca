#!/usr/bin/env python3
"""
Merge **existing repo JSON** (no external APIs) into one dashboard-friendly list:

  - Hyperliquid-qualified traders (`qualified_traders.json`)
  - Polymarket leaderboard profiles (`polymarket_trader_profiles.json` → qualified_traders)
  - Trusted registry from `trusted_trader_tracker.py` (`trusted_traders.json`)

Output: `copy_trader_intel/data/unified_copytrade_candidates.json`

Run from repo root:
  python tools/build_unified_copytrade_candidates.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "copy_trader_intel" / "data"
OUT = DATA / "unified_copytrade_candidates.json"


def _read_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    candidates = []
    now = datetime.now(timezone.utc).isoformat()

    hl = _read_json(DATA / "qualified_traders.json") or {}
    for t in hl.get("traders") or []:
        if not isinstance(t, dict):
            continue
        addr = t.get("address") or t.get("wallet") or ""
        candidates.append(
            {
                "source": "hyperliquid_qualified",
                "id": str(addr)[:20] + ("…" if len(str(addr)) > 20 else ""),
                "address": addr,
                "label": t.get("label") or "",
                "win_rate": t.get("win_rate"),
                "total_trades": t.get("total_trades"),
                "profit_factor": t.get("profit_factor"),
                "edge_score": t.get("edge_score"),
                "qualified": t.get("qualified", True),
            }
        )

    pm = _read_json(DATA / "polymarket_trader_profiles.json") or {}
    for t in pm.get("qualified_traders") or []:
        if not isinstance(t, dict):
            continue
        w = t.get("wallet") or ""
        candidates.append(
            {
                "source": "polymarket_qualified",
                "id": t.get("alias") or w[:16],
                "wallet": w,
                "user_name": t.get("user_name"),
                "crypto_win_rate_bayes": t.get("crypto_win_rate_bayes"),
                "crypto_total_pnl": t.get("crypto_total_pnl"),
                "crypto_decisions": t.get("crypto_decisions"),
                "crypto_sample_tier": t.get("crypto_sample_tier"),
                "copyable_archetype": t.get("copyable_archetype"),
                "wallet_archetype": t.get("wallet_archetype"),
            }
        )

    tt = _read_json(DATA / "trusted_traders.json") or {}
    for key, t in (tt.get("traders") or {}).items():
        if not isinstance(t, dict):
            continue
        perf = t.get("performance") or {}
        candidates.append(
            {
                "source": "trusted_registry",
                "id": key,
                "label": t.get("label"),
                "strategy_prefix": t.get("strategy_prefix"),
                "trust_status": t.get("trust_status"),
                "trust_score": t.get("trust_score"),
                "win_rate": perf.get("win_rate"),
                "closed_picks": perf.get("closed_picks"),
                "total_pnl_pct": perf.get("total_pnl_pct"),
            }
        )

    gate = _read_json(DATA / "gate_trader_profiles.json") or {}
    for p in gate.get("profiles") or []:
        if not isinstance(p, dict):
            continue
        lid = p.get("leaderId") or ""
        candidates.append(
            {
                "source": "gate_copy_trading",
                "id": lid,
                "nickName": p.get("nickName"),
                "win_rate": p.get("win_rate"),
                "total_trades": p.get("total_trades"),
                "profit_factor": p.get("profit_factor"),
                "sharpe": p.get("sharpe"),
                "max_drawdown": p.get("max_drawdown"),
            }
        )

    payload = {
        "generated_at": now,
        "candidate_count": len(candidates),
        "sources": [
            "copy_trader_intel/data/qualified_traders.json",
            "copy_trader_intel/data/polymarket_trader_profiles.json",
            "copy_trader_intel/data/trusted_traders.json",
            "copy_trader_intel/data/gate_trader_profiles.json",
        ],
        "candidates": candidates,
        "_doc": "Merged view for audit UI / ops — not investment advice. Re-run after scrapers update feeds.",
    }

    DATA.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote {len(candidates)} rows to {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
