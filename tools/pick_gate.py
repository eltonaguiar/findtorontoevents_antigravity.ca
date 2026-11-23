#!/usr/bin/env python3
"""pick_gate.py — G1–G5 gate engine for ranked picks.

Every pick MUST carry: n, net_bp, kill_rule. Every bp figure MUST state the ticket
size it was measured at, because IBKR commission is not scale-invariant:
    $1k ticket  -> ~11 bp/side
    $25k ticket -> ~0.4 bp/side

Gates (a pick either PASSES or is LABELLED with the gate it fails):
    G1  gross edge > 2 x MEASURED round-trip cost (spread 6.04 bp/side = 12.07 bp RT,
        13 names; commission added by ticket size).
    G2  survives at a holding period of 1 day or longer (kills sub-day noise edges).
    G3  deflated Sharpe reported WITH the trial count stated (DSR needs n_trials).
    G4  return on COMMITTED CAPITAL including cash collateral, vs a 4.3% T-bill —
        NOT return on notional. A long-only cash-secured position ties up the cash.
    G5  the pick was recorded before its outcome (pre-registration / forward rows).

This module is pure: it takes measured inputs and returns a gate report. It does not
read the DB. Callers supply cost + holding + DSR + timing.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

# Measured market-structure inputs (2026-11-23 measurement, 13 names).
SPREAD_BP_PER_SIDE = 6.04
SPREAD_BP_ROUND_TRIP = 12.07  # measured round-trip, 13 names (≈ 2 x 6.04, rounded)
TBIL_YIELD_PCT = 4.3          # risk-free hurdle for G4

# IBKR commission per side, measured, not scale-invariant.
IBKR_BP_PER_SIDE = {
    1_000: 11.0,
    25_000: 0.4,
}


def ibkr_commission_bp(ticket_usd: float) -> float:
    """Per-side commission in bp, interpolated log-linearly between measured points.

    Below $1k we hold 11 bp (worst measured). Above $25k we hold 0.4 bp (best
    measured) — we never assume better than the largest measured ticket.
    """
    pts = sorted(IBKR_BP_PER_SIDE.items())
    if ticket_usd <= pts[0][0]:
        return pts[0][1]
    if ticket_usd >= pts[-1][0]:
        return pts[-1][1]
    import math
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    t = (math.log(ticket_usd) - math.log(x0)) / (math.log(x1) - math.log(x0))
    return y0 + t * (y1 - y0)


@dataclass
class Pick:
    symbol: str
    asset_class: str
    side: str                      # LONG / SHORT
    n: int
    gross_edge_bp: float           # per-trade gross edge in bp
    holding_days: float
    ticket_usd: float              # capital committed per ticket
    dsr: float | None = None
    dsr_n_trials: int | None = None
    pre_recorded: bool = False     # G5
    kill_rule: str = ""
    net_bp: float | None = None    # computed if not supplied
    gates: dict = field(default_factory=dict)
    verdict: str = ""


GLOSSARY = {
    "G1": "gross edge > 2x measured round-trip cost",
    "G2": "survives holding >= 1 day",
    "G3": "deflated Sharpe with trial count stated",
    "G4": "return on committed capital (incl. cash collateral) > 4.3% T-bill",
    "G5": "pick recorded before outcome",
}


def round_trip_cost_bp(ticket_usd: float, side: str) -> dict:
    """Measured round-trip cost in bp at a given ticket, broken out.

    Long-only cash-secured: spread paid both ways + commission both ways.
    """
    comm_side = ibkr_commission_bp(ticket_usd)
    spread = SPREAD_BP_ROUND_TRIP
    commission = 2.0 * comm_side
    total = spread + commission
    return {"spread_bp": spread, "commission_bp": round(commission, 4),
            "commission_bp_per_side": round(comm_side, 4),
            "total_rt_bp": round(total, 4), "ticket_usd": ticket_usd}


def gate_pick(p: Pick) -> Pick:
    cost = round_trip_cost_bp(p.ticket_usd, p.side)
    g = {}

    # G1: gross > 2x measured RT cost
    g["G1"] = p.gross_edge_bp > 2.0 * cost["total_rt_bp"]

    # G2: holding >= 1 day
    g["G2"] = p.holding_days >= 1.0

    # G3: DSR present AND trial count stated
    g["G3"] = (p.dsr is not None and p.dsr_n_trials is not None and p.dsr_n_trials >= 1)

    # G4: return on committed capital vs T-bill.
    # net edge % on the committed ticket, annualised by turnover, must exceed T-bill.
    net_bp = p.gross_edge_bp - cost["total_rt_bp"]
    p.net_bp = round(net_bp, 4)
    if p.holding_days > 0:
        trades_per_year = 365.0 / p.holding_days
        net_annual_pct = (net_bp / 10000.0) * trades_per_year * 100.0
    else:
        net_annual_pct = 0.0
    g["G4"] = net_annual_pct > TBIL_YIELD_PCT
    p.gates = g
    p.roc_annual_pct = round(net_annual_pct, 4)

    # G5
    g["G5"] = bool(p.pre_recorded)

    # G3 label also needs the trial count echoed
    p.dsr_trials_stated = p.dsr_n_trials

    p.verdict = "PASS" if all(g.values()) else "FAIL:" + ",".join(k for k, v in g.items() if not v)
    p.cost = cost
    return p


def report(picks: list[Pick]) -> dict:
    gated = [gate_pick(p) for p in picks]
    return {
        "inputs": {
            "spread_bp_per_side": SPREAD_BP_PER_SIDE,
            "spread_bp_round_trip": SPREAD_BP_ROUND_TRIP,
            "tbill_yield_pct": TBIL_YIELD_PCT,
            "ibkr_bp_per_side": IBKR_BP_PER_SIDE,
        },
        "glossary": GLOSSARY,
        "picks": [asdict(p) for p in gated],
        "n_pass": sum(1 for p in gated if p.verdict == "PASS"),
        "n_fail": sum(1 for p in gated if p.verdict != "PASS"),
    }


if __name__ == "__main__":
    import json
    demo = [
        Pick("AAPL", "EQUITY", "LONG", n=81, gross_edge_bp=20.9, holding_days=20,
             ticket_usd=1000, dsr=0.011, dsr_n_trials=277, pre_recorded=False,
             kill_rule="exit if CI-LB<=0 at day 30/60"),
    ]
    print(json.dumps(report(demo), indent=2))
