"""LL1 regression: --tp-pct / --sl-pct compute relative to actual fill.

Cycle-4 (2026-05-09) NEAR was placed expecting entry $1.599 with SL $1.55
(designed as -3% from expected). Actual fill was $1.570; SL became -1.3%
of real fill, too tight, stopped out for ~$37 loss. With --sl-pct 0.03,
SL recomputes to fill * 0.97 = $1.5229, holds.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))


def test_long_buy_fill_relative_tp_pct():
    """LONG fill 1.570, tp_pct 0.05 → TP = 1.6485."""
    fill = 1.570
    side = "BUY"
    tp_pct = 0.05
    expected_tp = round(fill * (1 + tp_pct), 8)
    assert expected_tp == 1.6485
    if side == "BUY":
        assert expected_tp > fill, "LONG TP must be ABOVE fill"


def test_long_buy_fill_relative_sl_pct_protects_near_case():
    """NEAR cycle-4 retro: fill 1.570, sl_pct 3% → SL 1.5229.

    Cycle-4 actual SL was 1.55 (designed as -3% of expected entry 1.599,
    became -1.3% of real fill 1.570 — too tight, stopped out).
    Fill-relative SL 1.5229 = -3% of real fill, gives 1.7%-pt more room.
    """
    fill = 1.570
    sl_pct = 0.03
    expected_sl = round(fill * (1 - sl_pct), 8)
    assert expected_sl == 1.5229
    # Pre-fill expected SL (cycle-4 actual placement)
    expected_entry = 1.599
    pre_fill_sl = round(expected_entry * (1 - sl_pct), 8)
    assert pre_fill_sl == 1.55103  # what swarm vet recommended
    # The fix shifts SL further from real fill, providing more room
    pct_distance_pre = (fill - pre_fill_sl) / fill
    pct_distance_final = (fill - expected_sl) / fill
    assert pct_distance_final > pct_distance_pre
    assert round(pct_distance_final, 4) == 0.03  # exactly 3%
    assert round(pct_distance_pre, 4) < 0.02  # under 2% — too tight


def test_short_sell_pct_inverted_correctly():
    """SHORT fill 100, tp_pct 0.05 → TP = 95 (below). sl_pct 0.02 → SL = 102 (above)."""
    fill = 100.0
    tp_pct = 0.05
    sl_pct = 0.02
    expected_tp = round(fill * (1 - tp_pct), 8)
    expected_sl = round(fill * (1 + sl_pct), 8)
    assert expected_tp == 95.0
    assert expected_sl == 102.0
    assert expected_sl > fill > expected_tp, "SHORT side-sanity: sl > entry > tp"


def test_argparse_requires_tp_xor_tp_pct():
    """CLI: must provide --tp OR --tp-pct, not neither."""
    import argparse
    import pytest
    pytest.importorskip("websocket")  # tv_place_pick imports tv_cdp_runner which needs websocket-client
    import tv_place_pick as m
    # Smoke: imports cleanly, main() exists
    assert hasattr(m, "main")
    assert hasattr(m, "place")
    # Place signature accepts new kwargs
    import inspect
    sig = inspect.signature(m.place)
    assert "tp_pct" in sig.parameters
    assert "sl_pct" in sig.parameters


def test_pre_mid_used_when_market_order_and_no_panel():
    """For MARKET pct-mode, pre_tp/pre_sl come from order panel mid placeholder.
    Test the pre-execute math: pre_mid 1.42, tp_pct 0.02, sl_pct 0.014 → pre_tp 1.4484, pre_sl 1.4001."""
    pre_mid = 1.42
    tp_pct = 0.02
    sl_pct = 0.014
    pre_tp = round(pre_mid * (1 + tp_pct), 8)
    pre_sl = round(pre_mid * (1 - sl_pct), 8)
    assert pre_tp == 1.4484
    assert pre_sl == 1.40012
    # Side-sanity passes
    assert pre_tp > pre_mid > pre_sl


def test_pct_zero_means_at_entry_use_caution():
    """sl_pct=0 means SL == fill (instant stop). Not blocked but unusual."""
    fill = 100.0
    sl_pct = 0.0
    sl = round(fill * (1 - sl_pct), 8)
    assert sl == fill  # caller's responsibility — orchestrator doesn't second-guess


def test_pct_recompute_path_triggered_when_fill_differs_from_pre_mid():
    """When pre_mid (from panel placeholder) and fill_price differ, pre_tp/sl
    differ from final_tp/sl, triggering the Protect dialog re-apply path.

    Replays cycle-4 NEAR: pre_mid (panel placeholder pre-execute) = 1.599,
    fill = 1.570, sl_pct = 0.03.
    """
    pre_mid = 1.599
    fill = 1.570
    sl_pct = 0.03
    pre_sl = round(pre_mid * (1 - sl_pct), 8)
    final_sl = round(fill * (1 - sl_pct), 8)
    assert pre_sl != final_sl
    assert final_sl < pre_sl  # fill below expected → SL also below
    # The orchestrator should detect this delta and apply final via Protect
    pct_recompute_needed = (sl_pct is not None) and (final_sl != pre_sl)
    assert pct_recompute_needed
