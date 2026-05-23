from alpha_engine.adaptive_tp_sl import get_optimal_tp_sl
from alpha_engine.tpsl_policy import get_tpsl_policy


def test_tpsl_policy_commodity_defaults_are_wider():
    policy = get_tpsl_policy("commodity")
    assert round(policy["tp_pct"], 4) == 0.0625
    assert round(policy["sl_pct"], 4) == 0.0375


def test_tpsl_policy_uses_explicit_atr_pct():
    policy = get_tpsl_policy("futures", atr_pct=3.0)
    assert round(policy["tp_pct"], 4) == 0.075
    assert round(policy["sl_pct"], 4) == 0.045


def test_get_optimal_tp_sl_uses_policy_defaults_for_commodity():
    tp, sl = get_optimal_tp_sl(
        strategy="unit_test_no_history_strategy",
        symbol="GC=F",
        entry_price=100.0,
        category="commodity",
        direction="LONG",
    )
    assert tp == 106.25
    assert sl == 96.25
