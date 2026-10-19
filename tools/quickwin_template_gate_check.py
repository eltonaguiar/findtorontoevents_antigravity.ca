#!/usr/bin/env python3
"""quickwin_template_gate_check.py — gate every quick-win strategy template against
the current honest ledgers.

Registry: reports/quickwin_strategy_templates.json (the verified/corrected form of the
"Quick-Win Symbols & Strategy Templates by Asset Class" task; see
reports/QUICKWIN_STRATEGY_TEMPLATES_2026-10-19.md).

Sources (both local, read-only, no network, no DB):
  1. LIVE  — audit_dashboard/data/dashboard_data.json :: money_ready_verdicts
             (regenerate locally via tools/refresh_local_audit_mirror.py)
  2. FROZEN — audit_dashboard/data/intrabar_truth_by_class.json
             (the canonical honest ledger, generated 2026-06-21, frozen)

Gates = Tier 2 of alpha_engine.value_backtest.classify_tier:
  n >= 100, PF >= 1.5, WR >= 50%, MaxDD <= 20%.

Usage:
    python3 tools/quickwin_template_gate_check.py             # table + write status JSON
    python3 tools/quickwin_template_gate_check.py --stdout     # table only, no write
    python3 tools/quickwin_template_gate_check.py --json        # machine JSON to stdout

Exit codes: 0 = ran (any pass/fail mix), 1 = missing/unreadable input.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, str(REPO))

from alpha_engine.value_backtest import classify_tier  # noqa: E402  (REPO on sys.path first)

REGISTRY_PATH = os.path.join(REPO, "reports", "quickwin_strategy_templates.json")
LIVE_PAYLOAD = os.path.join(REPO, "audit_dashboard", "data", "dashboard_data.json")
FROZEN_LEDGER = os.path.join(REPO, "audit_dashboard", "data", "intrabar_truth_by_class.json")
OUT_PATH = os.path.join(REPO, "reports", "quickwin_template_gate_status.json")


def _load(path: str, what: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"missing {what}: {path} "
                                f"(mirror refresh: python3 tools/refresh_local_audit_mirror.py)")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _gates(metrics: dict, gates: dict) -> dict:
    """Evaluate n / PF / WR / MDD gates on one metrics dict (missing metrics => None)."""
    n = metrics.get("n")
    pf = metrics.get("pf")
    wr_pct = metrics.get("wr_pct")
    mdd = metrics.get("mdd")

    return {
        "n": {"ok": (n is not None and n >= gates["n_min"]), "value": n},
        "pf": {"ok": (pf is not None and pf >= gates["pf_min"]), "value": pf},
        "wr": {"ok": (wr_pct is not None and wr_pct >= gates["wr_min_pct"]), "value": wr_pct},
        "mdd": {"ok": (None if mdd is None else mdd <= gates["max_dd_max"]), "value": mdd},
    }


def _tier(metrics: dict, gates: dict) -> str:
    """classify_tier needs all four; MDD missing (no drawdown marked yet) can never
    satisfy the DD gate, so feed 1.0 — n<100 already forces 'below' anyway."""
    n = metrics.get("n") or 0
    pf = metrics.get("pf")
    wr_pct = metrics.get("wr_pct")
    mdd = metrics.get("mdd")
    if pf is None or wr_pct is None:
        return "below (incomplete metrics)"
    return classify_tier(wr_pct / 100.0, pf, mdd if mdd is not None else 1.0, n)


def run() -> tuple[dict, int]:
    registry = _load(REGISTRY_PATH, "template registry")
    live_payload = _load(LIVE_PAYLOAD, "live dashboard payload")
    frozen = _load(FROZEN_LEDGER, "frozen honest ledger")

    gates = registry["gates"]
    live_verdicts = live_payload.get("money_ready_verdicts") or {}
    frozen_classes = frozen.get("by_class") or {}

    results = []
    for tpl in registry["templates"]:
        cls = tpl["asset_class"]
        live = live_verdicts.get(cls) or {}
        frz = frozen_classes.get(cls) or {}

        live_metrics = {k: live.get(k) for k in ("n_resolved", "wr_pct", "pf", "mdd")}
        live_metrics = {"n": live_metrics["n_resolved"], "wr_pct": live_metrics["wr_pct"],
                        "pf": live_metrics["pf"], "mdd": live_metrics["mdd"]}
        frozen_metrics = {"n": frz.get("n"), "wr_pct": frz.get("wr_pct"),
                          "pf": frz.get("pf"), "mdd": None}

        entry = {
            "id": tpl["id"],
            "asset_class": cls,
            "track": tpl.get("track"),
            "ledger_gate_applies": tpl.get("ledger_gate_applies", True),
            "paper_only": tpl.get("paper_only"),
            "live": {**live_metrics, "gates": _gates(live_metrics, gates),
                     "tier": _tier(live_metrics, gates),
                     "payload_generated_at": live_payload.get("generated_at")},
            "frozen": {**frozen_metrics, "gates": _gates(frozen_metrics, gates),
                       "tier": _tier(frozen_metrics, gates),
                       "ledger_generated_at": frozen.get("generated_at")},
        }
        if entry["ledger_gate_applies"]:
            ok = entry["live"]["gates"]
            entry["live_pass"] = all(ok[k]["ok"] for k in ("n", "pf", "wr", "mdd"))
        else:
            entry["live_pass"] = None  # backtest track (ETF TAA) — ledger gates don't apply
        results.append(entry)

    status = {
        "schema": "quickwin_template_gate_status/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "registry": os.path.relpath(REGISTRY_PATH, REPO),
        "sources": {
            "live_payload_generated_at": live_payload.get("generated_at"),
            "frozen_ledger_generated_at": frozen.get("generated_at"),
        },
        "gates": gates,
        "results": results,
        "summary": {
            "templates": len(results),
            "ledger_gated": sum(1 for r in results if r["ledger_gate_applies"]),
            "live_pass": sum(1 for r in results if r["live_pass"] is True),
            "paper_only": sum(1 for r in results if r.get("paper_only")),
        },
    }
    return status, 0


def _print_table(status: dict) -> None:
    s = status["summary"]
    print(f"Quick-Win template gate check — {status['generated_at']}  "
          f"(live payload {status['sources']['live_payload_generated_at']}, "
          f"frozen ledger {status['sources']['frozen_ledger_generated_at']})")
    print(f"Tier-2 gates: n>={status['gates']['n_min']}  PF>={status['gates']['pf_min']}  "
          f"WR>={status['gates']['wr_min_pct']}%  MDD<={status['gates']['max_dd_max']}")
    print(f"{'TEMPLATE':<32}{'CLASS':<11}{'live n':>8}{'WR%':>7}{'PF':>9}{'MDD':>8}  "
          f"{'tier(live)':<22}{'PASS':>6}")
    for r in status["results"]:
        lv = r["live"]
        g = lv["gates"]
        fmt = lambda v: "n/a" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v))
        passed = "—" if r["live_pass"] is None else ("YES" if r["live_pass"] else "no")
        print(f"{r['id']:<32}{r['asset_class']:<11}{fmt(g['n']['value']):>8}"
              f"{fmt(g['wr']['value']):>7}{fmt(g['pf']['value']):>9}{fmt(g['mdd']['value']):>8}  "
              f"{lv['tier']:<22}{passed:>6}")
    print(f"\n{s['live_pass']}/{s['ledger_gated']} ledger-gated templates pass Tier-2 "
          f"live; {s['paper_only']} paper-only; "
          f"{s['templates'] - s['ledger_gated']} backtest-track (ETF TAA — forward-track, "
          f"ledger gates not applicable).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stdout", action="store_true", help="print only, do not write status JSON")
    ap.add_argument("--json", action="store_true", help="print machine JSON to stdout")
    args = ap.parse_args()

    try:
        status, code = run()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(status, indent=2))
    else:
        _print_table(status)

    if not args.stdout and not args.json:
        tmp = OUT_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(status, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, OUT_PATH)
        print(f"wrote {os.path.relpath(OUT_PATH, REPO)}")
    return code


if __name__ == "__main__":
    sys.exit(main())
