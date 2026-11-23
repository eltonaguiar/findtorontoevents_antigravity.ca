#!/usr/bin/env python3
"""build_asset_class_rankings.py — END-GOAL A/B: per-symbol ranked picks with G1–G5 gates.

Source of truth:
  * per-symbol picks  -> ledger["symbols"]  (cells are strategy aggregates with symbol=None)
  * strategy context  -> ledger["cells"]    (for DSR trial counts)

IMPORTANT measured-vs-ledger disagreements (reported, not hidden):
  * Ledger mean_cost_pct for EQUITY is 0.05% (5 bp). Our MEASURED market cost is
    12.07 bp round trip (spread, 13 names) + IBKR commission by ticket. G1 uses the
    MEASURED cost, which is ~2.4x larger than the ledger's assumed cost.
  * The ledger does NOT publish hold_days_mean/median. G2 therefore cannot be proven
    from the ledger and every pick is labelled FAIL:G2 (unmeasurable) until a
    hold-time feed exists. This is reported, not papered over.

Ticket assumption: $25k default (IBKR 0.4 bp/side). Every bp figure states the ticket.
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.pick_gate import Pick, gate_pick, round_trip_cost_bp, ibkr_commission_bp  # noqa: E402

TBIL = 4.3


def _symbols_as_list(d: dict) -> list[dict]:
    syms = d.get("symbols", [])
    if isinstance(syms, dict):
        return list(syms.values())
    return [s for s in syms if isinstance(s, dict)]


def build(ledger_path: str, ticket_usd: float) -> dict:
    d = json.loads(Path(ledger_path).read_text())
    syms = _symbols_as_list(d)
    cells = d.get("cells", [])

    # DSR trial count: take the max published (global multiplicity) once.
    trial_counts = [c.get("dsr_n_trials") for c in cells if c.get("dsr_n_trials")]
    global_trials = max(trial_counts) if trial_counts else None

    # Optional hold_days feed (partial, from forward ledger only)
    hold_feed = {}
    hf = Path("reports/hold_days_by_symbol.json")
    if hf.exists():
        try:
            hd = json.loads(hf.read_text())
            for k, v in hd.get("by_symbol", {}).items():
                # k = "CRYPTO:BTC"
                hold_feed[k.split(":", 1)[1]] = v
        except Exception:
            pass

    picks = []
    for s in syms:
        if not s.get("n"):
            continue
        # Use GROSS expectancy (the ledger's net is already net of its own 5 bp cost;
        # re-costing from net would double-subtract). Fall back to net+5bp if gross absent.
        ge = s.get("gross_expectancy_pct")
        if ge is not None:
            gross_bp = float(ge) * 100.0
        else:
            ne = s.get("net_expectancy_pct")
            gross_bp = (float(ne) * 100.0 + 5.0) if ne is not None else 0.0
        sym = s.get("symbol", "UNK")
        hold = hold_feed.get(sym, {}).get("hold_days_mean", 0.0) if hold_feed else 0.0
        p = Pick(
            symbol=sym,
            asset_class=s.get("asset_class", "UNK"),
            side=s.get("direction", "LONG"),
            n=int(s.get("n", 0)),
            gross_edge_bp=round(gross_bp, 4),
            holding_days=float(hold),  # partial feed from forward ledger
            ticket_usd=ticket_usd,
            dsr=s.get("dsr"),
            dsr_n_trials=s.get("dsr_n_trials") or global_trials,
            pre_recorded=False,
            kill_rule="exit if CI-LB<=0 at day 30/60, or forward n<100, or net_bp<=0",
        )
        picks.append(gate_pick(p))

    # per-class ranking: PASS first, then net_bp desc
    by_class: dict[str, list] = {}
    for p in picks:
        by_class.setdefault(p.asset_class, []).append(p)
    for ac, lst in by_class.items():
        lst.sort(key=lambda x: (x.verdict != "PASS", -(x.net_bp if x.net_bp is not None else -1e9)))

    top3 = {}
    for ac, lst in by_class.items():
        top3[ac] = [
            {"symbol": p.symbol, "n": p.n, "net_bp": p.net_bp, "verdict": p.verdict,
             "kill_rule": p.kill_rule, "ticket_usd": p.ticket_usd,
             "dsr": p.dsr, "dsr_n_trials": p.dsr_n_trials,
             "roc_annual_pct": getattr(p, "roc_annual_pct", None)}
            for p in lst[:3]
        ]

    cost = round_trip_cost_bp(ticket_usd, "LONG")
    return {
        "generated_at": d.get("generated_at"),
        "ticket_usd": ticket_usd,
        "ibkr_bp_per_side": round(ibkr_commission_bp(ticket_usd), 4),
        "measured_cost_rt_bp": cost,
        "tbill_yield_pct": TBIL,
        "disagreements": {
            "ledger_assumed_equity_cost_bp": 5.0,
            "measured_rt_cost_bp": cost["total_rt_bp"],
            "ratio": round(cost["total_rt_bp"] / 5.0, 2),
            "hold_days_present_in_ledger": False,
            "hold_days_feed": "reports/hold_days_by_symbol.json (partial: 430 forward rows, 31 symbols)",
            "hold_feed_symbols": len(hold_feed),
            "g2_note": "G2 computed where forward-ledger hold_days exists; picks without a feed row still FAIL:G2",
        },
        "top3_summary": top3,
        "n_pass": sum(1 for p in picks if p.verdict == "PASS"),
        "n_fail": sum(1 for p in picks if p.verdict != "PASS"),
        "picks": [
            {"symbol": p.symbol, "asset_class": p.asset_class, "side": p.side, "n": p.n,
             "net_bp": p.net_bp, "gates": p.gates, "verdict": p.verdict,
             "dsr": p.dsr, "dsr_n_trials": p.dsr_n_trials, "ticket_usd": p.ticket_usd,
             "kill_rule": p.kill_rule, "roc_annual_pct": getattr(p, "roc_annual_pct", None)}
            for p in picks
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default="audit_dashboard/data/audit3_ledger.json")
    ap.add_argument("--ticket-usd", type=float, default=25_000)
    ap.add_argument("--out", default="reports/asset_class_rankings.json")
    args = ap.parse_args()

    out = build(args.ledger, args.ticket_usd)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(f"rankings written: {args.out} ({len(out['picks'])} picks, {out['n_pass']} PASS, {out['n_fail']} FAIL)")


if __name__ == "__main__":
    main()
