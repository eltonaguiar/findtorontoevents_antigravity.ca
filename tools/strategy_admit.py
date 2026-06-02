#!/usr/bin/env python3
"""
Unified strategy admissibility CLI (EAGLE2 workstream B1).

Runs walk-forward verdict lookup + optional rigorous harness sample,
writes a single JSON artifact for promotion gates.

Usage:
  python3 tools/strategy_admit.py --strategy etf_dual_momentum
  python3 tools/strategy_admit.py --strategy vwap_reversion --asset-class CRYPTO
  python3 tools/strategy_admit.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports" / "strategy_admit"
WF_REPORT = ROOT / "verified_strategies" / "WALKFORWARD_REPORT.json"
HYPOTHESIS = ROOT / "reports" / "hypothesis_registry.json"

# Map CLI names → walkforward report keys
SLEEVE_ALIASES: Dict[str, str] = {
    "etf_dual_momentum": "dual_momentum_etf",
    "dual_momentum_etf": "dual_momentum_etf",
    "faber_taa": "faber_taa",
    "vwap_reversion": "vwap_reversion",
    "bollinger_mr": "bollinger_mr",
    "crypto_donchian": "crypto_donchian",
    "donchian": "crypto_donchian",
    "equity_momentum_12_1": "equity_momentum_12_1",
    "equity_verified_momentum_12_1": "equity_momentum_12_1",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _wf_verdict(sleeve_key: str) -> Dict[str, Any]:
    wf = _load_json(WF_REPORT) or {}
    row = wf.get(sleeve_key)
    if not isinstance(row, dict):
        return {"verdict": "UNTESTED", "note": f"no row in WALKFORWARD_REPORT.json for {sleeve_key}"}
    return {
        "verdict": row.get("verdict", "UNKNOWN"),
        "pf": row.get("pf") or row.get("costed_pf"),
        "wr": row.get("wr") or row.get("costed_wr"),
        "n": row.get("n") or row.get("n_trades"),
        "artifact": str(WF_REPORT),
    }


def _hypothesis_registered(strategy: str) -> Optional[str]:
    reg = _load_json(HYPOTHESIS)
    if not reg:
        return None
    entries = reg if isinstance(reg, list) else reg.get("hypotheses") or reg.get("entries") or []
    for e in entries:
        if not isinstance(e, dict):
            continue
        sid = str(e.get("strategy_id") or e.get("strategy") or e.get("id") or "")
        if sid.lower() == strategy.lower() or strategy.lower() in sid.lower():
            return str(e.get("hypothesis_id") or e.get("id") or sid)
    return None


def _money_ready_class(asset_class: str) -> Dict[str, Any]:
    ac = asset_class.upper()
    try:
        from alpha_engine.money_ready_verdict import class_verdict, sizing_multiplier_for_class

        return {
            "verdict": class_verdict(ac),
            "sizing_multiplier": sizing_multiplier_for_class(ac),
        }
    except Exception:
        mr = _load_json(ROOT / "audit_dashboard" / "data" / "money_ready_verdict.json")
        row = (mr or {}).get("classes", mr or {}).get(ac) if isinstance(mr, dict) else None
        if isinstance(row, dict):
            v = str(row.get("verdict") or "NOT_READY")
            return {"verdict": v, "sizing_multiplier": 1.0 if v == "MONEY_READY" else 0.0}
        return {"verdict": "UNKNOWN", "sizing_multiplier": None}


def admit(strategy: str, asset_class: str) -> Dict[str, Any]:
    sleeve = SLEEVE_ALIASES.get(strategy.lower(), strategy.lower())
    wf = _wf_verdict(sleeve)
    hyp = _hypothesis_registered(strategy)
    mr = _money_ready_class(asset_class.upper())

    wf_ok = str(wf.get("verdict")).upper() == "PASS"
    mr_ok = str(mr.get("verdict")).upper() == "MONEY_READY"
    hyp_ok = hyp is not None

    if wf_ok and mr_ok:
        status = "PROMOTE_LIVE"
    elif wf_ok:
        status = "FORWARD_PILOT_ONLY"
    elif str(wf.get("verdict")).upper() == "FAIL":
        status = "REJECT"
    else:
        status = "SHADOW_OR_UNTESTED"

    return {
        "schema_version": "1.0",
        "generated_at": _now(),
        "strategy": strategy,
        "sleeve_key": sleeve,
        "asset_class": asset_class.upper(),
        "hypothesis_id": hyp,
        "hypothesis_preregistered": hyp_ok,
        "walkforward": wf,
        "money_ready_class": mr,
        "admit_status": status,
        "checks": {
            "m107_preregister": hyp_ok,
            "walkforward_pass": wf_ok,
            "class_money_ready": mr_ok,
        },
        "recommendation": (
            "Live merge allowed only when walkforward PASS + class MONEY_READY + forward pilot ready."
            if status != "PROMOTE_LIVE"
            else "All gates green — still require forward n>=100 before sizing."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="EAGLE2 unified strategy admissibility")
    ap.add_argument("--strategy", help="Strategy or sleeve name")
    ap.add_argument("--asset-class", default="CRYPTO", help="Asset class for MR gate")
    ap.add_argument("--list", action="store_true", help="List known sleeve aliases")
    ap.add_argument("--write", action="store_true", help="Write reports/strategy_admit/<strategy>.json")
    args = ap.parse_args(argv)

    if args.list:
        for k, v in sorted(SLEEVE_ALIASES.items()):
            print(f"  {k} -> {v}")
        return 0

    if not args.strategy:
        ap.error("--strategy required (or use --list)")

    result = admit(args.strategy, args.asset_class)
    text = json.dumps(result, indent=2)
    print(text)

    if args.write:
        REPORTS.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.strategy)
        out = REPORTS / f"{safe}.json"
        out.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {out}", file=sys.stderr)

    return 0 if result["admit_status"] != "REJECT" else 1


if __name__ == "__main__":
    raise SystemExit(main())