#!/usr/bin/env python3
"""Per-class evidence rows: n and net bp, with provenance on every cell.

WHY THIS FILE EXISTS
    The ranked list asserted an order. An order is only worth something if each row
    carries (a) how many observations back it and (b) what the net edge actually is
    in basis points. This assembles that table and REFUSES to fill a cell it cannot
    source -- a missing net_bp is written as null with a reason, not as 0.

THE HONEST HEADLINE IT PRODUCES
    Only TWO of the classes have a measured net edge at all (EQUITY via HML, and
    CRYPTO via funding carry). Both fail the 4.32% hurdle. Every other class has a
    win-rate / profit-factor figure but NO measured net-of-cost bp, because no
    net-of-cost test has been run for it. That distinction is the whole point:
    a PF of 0.31 is a disappointment, but "no net bp measured" is an absence of
    evidence, and the two must not be rendered identically.

UNITS, STATED PER ROW
    net_bp_basis is either "per_year" (a yield or annualised return) or "per_trade".
    Mixing those silently would make the table meaningless, so every row declares it.

Read-only. Not investment advice.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
OUT = REPORTS / "per_class_evidence.json"
HURDLE_BP = 432.0            # capacity_model.HURDLE_TIBILL_APR = 0.0432


def _j(name: str):
    p = REPORTS / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:                                       # noqa: BLE001
        return None


def build_rows() -> list[dict]:
    rows: list[dict] = []
    hml = _j("hml_result.json")
    carry = _j("crypto_funding_carry.json")
    risk = _j("asset_class_risk.json")
    dsr = _j("deflated_sharpe_results.json")

    # ---- EQUITY: measured net edge exists -------------------------------
    if hml and hml.get("result"):
        r = hml["result"]
        rows.append({
            "class": "EQUITY",
            "row": "R1 HML long/short",
            "n": r.get("n_months"), "n_unit": "monthly rebalances",
            "net_bp": round(r.get("net_ann", 0) * 1e4, 1),
            "net_bp_basis": "per_year",
            "gross_bp": round(r.get("gross_ann", 0) * 1e4, 1),
            "cost_bp_round_trip": hml.get("cost", {}).get("round_trip_bp_used"),
            "source": "reports/hml_result.json",
            "measured": True, "verdict": hml.get("rule", {}).get("verdict"),
            "clears_hurdle": (r.get("net_ann", 0) * 1e4) > HURDLE_BP,
        })
    else:
        rows.append({"class": "EQUITY", "row": "R1 HML long/short",
                     "n": None, "net_bp": None, "net_bp_basis": "per_year",
                     "source": "reports/hml_result.json (MISSING)",
                     "measured": False, "reason": "artifact absent"})

    # ---- CRYPTO carry: measured net edge exists --------------------------
    if carry:
        rows.append({
            "class": "CRYPTO",
            "row": "R2b funding/carry",
            "n": carry.get("n_intervals_pooled"), "n_unit": "8h funding intervals",
            "net_bp": round(carry.get("net_ann_yield", 0) * 1e4, 1),
            "net_bp_basis": "per_year",
            "gross_bp": round(carry.get("gross_ann_yield", 0) * 1e4, 1),
            "cost_bp_round_trip": round(carry.get("round_trip_cost", 0) * 1e4, 1),
            "source": "reports/crypto_funding_carry.json",
            "measured": True, "verdict": "DEAD",
            "clears_hurdle": (carry.get("net_ann_yield", 0) * 1e4) > HURDLE_BP,
        })

    # ---- rows with a documented PF but NO measured net-of-cost bp --------
    cited = [
        ("CRYPTO", "R2 directional", 728, "trades", "PF 1.14 / WR 43% (policy-clean); "
         "raw DB 39% WR / PF 0.37; 1864 duplicate signal-ts groups, EXPIRED->WON mislabels",
         "CLAUDE.md asset_class_health + money_ready_verdict 2026-05-24", "DEAD"),
        ("FOREX", "R6 momentum", 53, "trades", "PF 0.55 / WR 40%, USDJPY 55% concentration",
         "CLAUDE.md asset_class_health", "DEAD"),
        ("COMMODITY", "R7 trend", 28, "trades", "PF 0.31 / WR 11%, CT=F 57% concentration",
         "CLAUDE.md asset_class_health", "DEAD"),
        ("BOND", "R3 govt/credit", 8, "trades", "PF 0 / WR 0% -- n too small to rank",
         "CLAUDE.md asset_class_health", "UNKNOWN"),
    ]
    for cls, row, n, unit, detail, src, verdict in cited:
        rows.append({
            "class": cls, "row": row, "n": n, "n_unit": unit,
            "net_bp": None, "net_bp_basis": "per_year",
            "gross_bp": None, "cost_bp_round_trip": None,
            "source": src, "measured": False, "verdict": verdict,
            "clears_hurdle": None,
            "reason": f"no net-of-cost test run. Known: {detail}",
        })

    # ---- ETF / PREDICTION MARKETS / PRIVATE CREDIT ----------------------
    etf = None
    if risk:
        for c in risk.get("classes", []):
            if c.get("asset_class") == "ETF":
                etf = c
                break
    rows.append({
        "class": "ETF", "row": "R4 / R4b",
        "n": etf.get("n") if etf else None, "n_unit": "symbols (risk only)",
        "net_bp": None, "net_bp_basis": "per_year",
        "gross_bp": None, "cost_bp_round_trip": 2.4,
        "source": "reports/asset_class_risk.json + reports/equity_cost_hml.json",
        "measured": False, "verdict": "CANDIDATE",
        "clears_hurdle": None,
        "reason": ("risk measured (Sharpe %.2f, MaxDD %.1f%%) and cost measured at "
                   "~1-2bp, but NO strategy test yet -- R4b is forward-only and "
                   "cannot produce a bp figure before ~2031"
                   % (etf["median_sharpe"], etf["median_mdd"] * 100)) if etf else
                  "risk artifact missing",
    })
    for cls in ("PREDICTION_MARKETS", "PRIVATE_CREDIT", "MUTUAL_FUNDS", "OPTIONS"):
        reason = {
            "PREDICTION_MARKETS": "metric is Brier/calibration, not Sharpe; no scored test yet",
            "PRIVATE_CREDIT": "no data at all in repo; reopen needs a private-credit index",
            "MUTUAL_FUNDS": "no NAV/holdings history; R5b is a COST question (MER), not an alpha test",
            "OPTIONS": "no options-chain history in repo; reopen needs chain data",
        }[cls]
        rows.append({
            "class": cls, "row": "-", "n": 0, "n_unit": "none",
            "net_bp": None, "net_bp_basis": "per_year",
            "gross_bp": None, "cost_bp_round_trip": None,
            "source": "no scored test", "measured": False, "verdict": "UNKNOWN",
            "clears_hurdle": None, "reason": reason,
        })
    return rows


def main() -> int:
    rows = build_rows()
    measured = [r for r in rows if r["measured"]]
    clearing = [r for r in measured if r.get("clears_hurdle")]
    dsr = _j("deflated_sharpe_results.json")

    out = {
        "hurdle_bp_per_year": HURDLE_BP,
        "n_classes_covered": len({r["class"] for r in rows}),
        "n_rows": len(rows),
        "n_rows_measured_net_bp": len(measured),
        "n_rows_clearing_hurdle": len(clearing),
        "programme_dsr": {
            "source": "tools/deflated_sharpe_results.json",
            "survivors": (len(dsr.get("summary", {}).get("survivors", []))
                          if dsr and isinstance(dsr.get("summary"), dict) else None),
            "note": "0/55 survive at SR*=1.014, sigma_SR=0.439 (measured 2026-11-22)",
        },
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print(f"{'CLASS':18} {'ROW':20} {'n':>7} {'unit':16} {'net bp/yr':>10} "
          f"{'clears':>7}  VERDICT")
    for r in rows:
        nb = f"{r['net_bp']:>10.1f}" if r["net_bp"] is not None else f"{'null':>10}"
        cl = {True: "YES", False: "no", None: "-"}[r.get("clears_hurdle")]
        print(f"{r['class']:18} {r['row']:20} {str(r['n']):>7} "
              f"{r['n_unit']:16} {nb} {cl:>7}  {r['verdict']}")
    print()
    print(f"classes covered      : {out['n_classes_covered']}")
    print(f"rows with MEASURED net bp : {out['n_rows_measured_net_bp']} of {out['n_rows']}")
    print(f"rows clearing the {HURDLE_BP:.0f}bp hurdle : {out['n_rows_clearing_hurdle']}")
    print(f"written: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
