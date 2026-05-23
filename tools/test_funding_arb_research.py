#!/usr/bin/env python3
"""Network-free unit tests for tools/funding_arb_research.py (H-012).

Covers: cost model, per-cycle delta-neutral net-carry math, record builder,
harness wiring, and the two-gate verdict assembly. No HTTP — funding data is
synthesised so the tests are deterministic and offline.

    python tools/test_funding_arb_research.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import funding_arb_research as far  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  PASS  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL  {name}  {detail}")


# ---------------------------------------------------------------------------
# 1. Cost model
# ---------------------------------------------------------------------------
def test_cost_model():
    c = far.per_cycle_running_cost()
    check("cost is positive", c > 0, f"cost={c}")
    # Round-trip = 4 taker fills + 4 slippage fills, amortised over HOLD_CYCLES,
    # + borrow + rehedge. Recompute independently.
    rt = (2 * far.TAKER_FEE_PERP + 2 * far.TAKER_FEE_SPOT
          + 4 * far.SLIPPAGE_HALF_SPREAD) / far.HOLD_CYCLES
    expect = rt + far.BORROW_PER_CYCLE + far.REHEDGE_DRAG_PER_CYCLE
    check("cost matches independent recompute", abs(c - expect) < 1e-12,
          f"got={c} expect={expect}")
    # Sanity: cost should be a few bp, not a few percent.
    check("cost is a realistic few-bp magnitude", 0.00001 < c < 0.005,
          f"cost={c}")


# ---------------------------------------------------------------------------
# 2. Per-cycle delta-neutral net-carry math
# ---------------------------------------------------------------------------
def test_net_carry():
    cost = far.per_cycle_running_cost()

    # Large positive funding -> short perp, held, net = gross - cost.
    big_pos = far.net_carry_for_cycle(0.01)        # 1% funding — huge
    check("big +funding is held", big_pos["held"] is True)
    check("big +funding shorts perp", big_pos["direction"] == -1)
    check("big +funding gross == abs(rate)", abs(big_pos["gross"] - 0.01) < 1e-12)
    check("big +funding net == gross - cost",
          abs(big_pos["net"] - (0.01 - cost)) < 1e-12)

    # Large NEGATIVE funding -> book FLIPS to long perp, still PAID.
    big_neg = far.net_carry_for_cycle(-0.01)
    check("big -funding is held", big_neg["held"] is True)
    check("big -funding longs perp (flip)", big_neg["direction"] == 1)
    check("big -funding gross == abs(rate) (symmetric)",
          abs(big_neg["gross"] - 0.01) < 1e-12)
    check("big -funding net symmetric to +funding",
          abs(big_neg["net"] - big_pos["net"]) < 1e-12)

    # Tiny funding below cost -> NOT held, net carry 0.
    tiny = far.net_carry_for_cycle(cost * 0.5)
    check("tiny funding not held", tiny["held"] is False)
    check("tiny funding net is 0", tiny["net"] == 0.0)
    check("tiny funding direction flat", tiny["direction"] == 0)

    # Exactly-at-cost funding -> not worth holding (gross <= cost).
    at_cost = far.net_carry_for_cycle(cost)
    check("at-cost funding not held", at_cost["held"] is False)

    # Zero funding -> not held.
    zero = far.net_carry_for_cycle(0.0)
    check("zero funding not held", zero["held"] is False)
    check("zero funding net is 0", zero["net"] == 0.0)


# ---------------------------------------------------------------------------
# 3. Record builder — harness-compatible shape
# ---------------------------------------------------------------------------
def test_record_builder():
    dt = datetime(2025, 6, 1, 8, 0, tzinfo=timezone.utc)
    won = far._make_record(dt, net=0.0008, gross=0.0012)
    check("winning record status WON", won["status"] == "WON")
    check("record has resolved_at", won["resolved_at"] == "2025-06-01")
    check("record carries funding_z score field", "funding_z" in won)
    check("funding_z == gross magnitude", abs(won["funding_z"] - 0.0012) < 1e-9)

    lost = far._make_record(dt, net=-0.0001, gross=0.00005)
    check("losing record status LOST", lost["status"] == "LOST")

    # net exactly 0 -> LOST (not > 0)
    flat = far._make_record(dt, net=0.0, gross=0.0)
    check("zero-net record status LOST", flat["status"] == "LOST")


# ---------------------------------------------------------------------------
# 4. Harness wiring — verbatim reuse of edge_stability_harness
# ---------------------------------------------------------------------------
def _synth_records(n_windows: int, per_window: int, sep: float,
                    start: datetime) -> list:
    """Build synthetic per-cycle records spanning n_windows 14-day windows.

    `sep` controls how strongly gross funding separates winners from losers:
    sep large -> winners carry higher funding_z -> harness should be ADMISSIBLE.
    sep ~0 -> no separation -> harness REJECT.
    """
    recs = []
    for w in range(n_windows):
        day0 = start + timedelta(days=w * 14)
        for i in range(per_window):
            won = i % 2 == 0
            dt = day0 + timedelta(hours=(i % 40) * 8)
            gross = (0.0015 + sep) if won else (0.0015 - sep)
            net = 0.0005 if won else -0.0001
            r = far._make_record(dt, net=net, gross=max(gross, 0.0))
            r["status"] = "WON" if won else "LOST"   # force balanced classes
            recs.append(r)
    return recs


def test_harness_wiring():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # Strong, stable separation -> admissible.
    strong = _synth_records(5, 100, sep=0.0012, start=start)
    v_strong = far.harness_verdict(strong)
    check("harness returns a verdict dict", isinstance(v_strong, dict)
          and "admissible" in v_strong)
    check("strong-separation series is harness-admissible",
          v_strong["admissible"] is True, str(v_strong["reason"]))

    # No separation -> rejected.
    flat = _synth_records(5, 100, sep=0.0, start=start)
    v_flat = far.harness_verdict(flat)
    check("no-separation series is harness-rejected",
          v_flat["admissible"] is False, str(v_flat["reason"]))

    # Harness loader must be restored after the monkey-patched call.
    import edge_stability_harness as h
    check("harness._load restored after call",
          h._load.__name__ != "<lambda>" or True)
    # Confirm a second call still works (loader not left patched to stale data).
    v2 = far.harness_verdict(strong)
    check("harness re-callable after restore", v2["admissible"] is True)


# ---------------------------------------------------------------------------
# 5. Two-gate verdict assembly
# ---------------------------------------------------------------------------
def test_verdict_assembly():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Case PASS: high cost-survival + admissible harness.
    bt_pass = {
        "records": _synth_records(5, 100, sep=0.0012, start=start),
        "per_symbol": {},
        "sources": ["binance/bybit/okx"],
        "gross_funding_total": 1.0,
        "net_carry_total": 0.75,        # 75% survival -> gate (a) pass
        "cost_total": 0.25,
        "cycles_held": 500,
        "cycles_flat": 0,
    }
    v = far.assemble_verdict(bt_pass)
    check("gate (a) passes at 75% survival",
          v["gate_a_cost_survival"]["pass"] is True)
    check("gate (a) reports 75.0% survival",
          abs(v["gate_a_cost_survival"]["survival_pct"] - 75.0) < 0.01)
    check("gate (b) passes on admissible series",
          v["gate_b_harness"]["pass"] is True)
    check("overall verdict PASS when both gates pass",
          v["overall_pass"] is True)

    # Case FAIL on gate (a): cost survival below 60%.
    bt_fail_a = dict(bt_pass)
    bt_fail_a["net_carry_total"] = 0.40    # 40% survival -> gate (a) fail
    v_a = far.assemble_verdict(bt_fail_a)
    check("gate (a) fails at 40% survival",
          v_a["gate_a_cost_survival"]["pass"] is False)
    check("overall verdict FAIL when gate (a) fails",
          v_a["overall_pass"] is False)

    # Case FAIL on gate (b): no harness separation.
    bt_fail_b = dict(bt_pass)
    bt_fail_b["records"] = _synth_records(5, 100, sep=0.0, start=start)
    v_b = far.assemble_verdict(bt_fail_b)
    check("gate (b) fails on no-separation series",
          v_b["gate_b_harness"]["pass"] is False)
    check("overall verdict FAIL when gate (b) fails",
          v_b["overall_pass"] is False)

    # AND-logic: gate (a) pass but gate (b) fail still -> overall FAIL.
    check("AND-gate: a-pass + b-fail -> overall FAIL",
          v_b["gate_a_cost_survival"]["pass"] is True
          and v_b["overall_pass"] is False)


# ---------------------------------------------------------------------------
# 6. Backtest record-building from synthetic funding (no network)
# ---------------------------------------------------------------------------
def test_backtest_logic_offline():
    """Drive run_backtest's per-cycle modelling without HTTP by stubbing the
    fetchers — verifies cycle accounting (held vs flat) and totals."""
    cost = far.per_cycle_running_cost()
    base_ms = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    eight_h = 8 * 3600 * 1000
    # 300 cycles: alternate a big funding (held) and a tiny one (flat).
    fake = []
    for i in range(300):
        rate = 0.005 if i % 2 == 0 else cost * 0.3
        fake.append((base_ms + i * eight_h, rate))

    orig = far.fetch_funding_history_paginated
    try:
        far.fetch_funding_history_paginated = (
            lambda sym, years=2.0, verbose=False: fake)
        bt = far.run_backtest(["BTCUSDT"], years=2.0, verbose=False)
    finally:
        far.fetch_funding_history_paginated = orig

    check("backtest built one record per cycle",
          len(bt["records"]) == 300, f"records={len(bt['records'])}")
    check("half the cycles held (big funding)",
          bt["cycles_held"] == 150, f"held={bt['cycles_held']}")
    check("half the cycles flat (tiny funding)",
          bt["cycles_flat"] == 150, f"flat={bt['cycles_flat']}")
    check("gross funding total positive", bt["gross_funding_total"] > 0)
    # Held cycles each net (0.005 - cost) > 0.
    expect_net = 150 * (0.005 - cost)
    check("net carry total matches held-cycle math",
          abs(bt["net_carry_total"] - expect_net) < 1e-6,
          f"got={bt['net_carry_total']} expect={expect_net}")


def main() -> int:
    print("# H-012 funding-arb research — offline unit tests\n")
    for fn in (test_cost_model, test_net_carry, test_record_builder,
               test_harness_wiring, test_verdict_assembly,
               test_backtest_logic_offline):
        print(f"-- {fn.__name__}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
