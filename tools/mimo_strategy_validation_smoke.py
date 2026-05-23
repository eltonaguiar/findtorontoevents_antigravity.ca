#!/usr/bin/env python3
"""
MIMO strategy smoke test — TESTING_PROTOCOL.MD Layer 5 (bootstrap sanity).

- Imports rehabilitation baby strategies and runs generate_signals on synthetic OHLC.
- Runs MonteCarloSimulator.bootstrap_returns on synthetic daily returns (requires n>=30).

Usage (repo root):
  python tools/mimo_strategy_validation_smoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _synth_ohlc(n: int = 400, seed: int = 7):
    import numpy as np
    import pandas as pd

    rng = np.random.RandomState(seed)
    r = rng.randn(n).cumsum() * 0.002 + 1.0
    close = pd.Series(r, dtype=float) * 1.08
    high = close * (1 + rng.rand(n) * 0.01)
    low = close * (1 - rng.rand(n) * 0.01)
    open_ = close.shift(1).fillna(close.iloc[0])
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})


def main() -> int:
    import numpy as np
    import pandas as pd

    from baby_strategies.forex_bb_mr_rehab_v1 import ForexBbMrRehabV1Strategy
    from baby_strategies.paxg_bollinger_mr_rehab import PaxgBollingerMrRehabStrategy
    from baby_strategies.vol_spike_capitulation_long_rehab import VolSpikeCapitulationLongRehabStrategy
    from baby_strategies.stoch_pullback_trend_long_rehab import StochPullbackTrendLongRehabStrategy
    from alpha_engine.validation.monte_carlo import MonteCarloSimulator

    df = _synth_ohlc()
    fx = ForexBbMrRehabV1Strategy()
    gx = PaxgBollingerMrRehabStrategy()
    vx = VolSpikeCapitulationLongRehabStrategy()
    sx = StochPullbackTrendLongRehabStrategy()
    fx.generate_signals(df, "EURUSDT")
    gx.generate_signals(df, "PAXGUSDT")
    vx.generate_signals(df, "BTCUSDT")
    sx.generate_signals(df, "BTCUSDT")

    rets = pd.Series(np.random.RandomState(42).randn(120) * 0.01)
    mc = MonteCarloSimulator(n_simulations=200, random_seed=99)
    out = mc.bootstrap_returns(rets, n_sims=200, use_block_bootstrap=False, strategy_type="mean_reversion")
    if out.get("error"):
        print("FAIL monte_carlo:", out)
        return 1
    sharpe_mean = out["sharpe"]["mean"]
    print("OK baby_strategies generate_signals (no crash)")
    print("OK monte_carlo bootstrap sharpe mean:", round(float(sharpe_mean), 4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
