"""CUSUM event-driven filter (Lopez de Prado, AFML Ch. 2.5.2.1).

Instead of sampling/acting at fixed intervals (every minute, every bar), sample
only when the CUMULATIVE price movement since the last event exceeds a
threshold. This produces an "event-driven" time series that focuses computation
on moments when something actually changed.

Algorithm (symmetric CUSUM):
  1. Initialize S_plus = 0, S_minus = 0
  2. For each new log-return r_t:
     - S_plus = max(0, S_plus + r_t)
     - S_minus = min(0, S_minus + r_t)
  3. If S_plus >= threshold: emit UP event, reset S_plus = 0
     If S_minus <= -threshold: emit DOWN event, reset S_minus = 0

Result: a set of timestamps when the price has moved enough to matter.

Why we need this
----------------
Currently our scanners run on fixed cron intervals. Most bars don't contain
a meaningful move. CUSUM-filtered sampling would:
  - Only trigger strategy re-scoring when the market actually moves
  - Reduce false-positive signal churn (fewer "noise" picks)
  - Give cleaner event-driven ML training labels

Integration hook: wrap around `alpha_engine/production_scanner.py`'s price-
update loop so downstream strategy evaluation only runs on CUSUM events for
a given symbol. Or use to prune the historical pick set for ML training.
"""
from __future__ import annotations

import math
from typing import Iterable


def log_returns(prices: list[float]) -> list[float]:
    """Convert a price series to log-returns (len-1 output)."""
    out = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0 and prices[i] > 0:
            out.append(math.log(prices[i] / prices[i - 1]))
        else:
            out.append(0.0)
    return out


def cusum_events(returns: list[float], threshold: float) -> list[dict]:
    """Return list of {idx, direction, cumsum} for each CUSUM event.

    threshold is in the same units as `returns` (typically log-return sigma×k).
    A common heuristic: threshold = 2 * stdev(returns).
    """
    s_plus = 0.0
    s_minus = 0.0
    events = []
    for i, r in enumerate(returns):
        s_plus = max(0.0, s_plus + r)
        s_minus = min(0.0, s_minus + r)
        if s_plus >= threshold:
            events.append({"idx": i, "direction": "UP", "cumsum": round(s_plus, 6)})
            s_plus = 0.0
            s_minus = 0.0  # dual reset (Lopez de Prado)
        elif s_minus <= -threshold:
            events.append({"idx": i, "direction": "DOWN", "cumsum": round(s_minus, 6)})
            s_plus = 0.0
            s_minus = 0.0
    return events


def suggest_threshold(returns: list[float], k: float = 2.0) -> float:
    """Convenience: k * stdev(returns) — common default."""
    if len(returns) < 2:
        return 0.0
    import statistics
    sd = statistics.stdev(returns) if len(returns) >= 2 else 0.0
    return k * sd


def sampling_reduction_rate(n_bars: int, n_events: int) -> float:
    """Fraction of bars that CAN be skipped vs event-driven sampling."""
    if n_bars == 0:
        return 0.0
    return 1.0 - (n_events / n_bars)


if __name__ == "__main__":
    import argparse
    import json
    import random

    ap = argparse.ArgumentParser(description="CUSUM filter demo on synthetic data.")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--drift", type=float, default=0.0)
    ap.add_argument("--sigma", type=float, default=0.01)
    ap.add_argument("--k", type=float, default=2.0)
    args = ap.parse_args()

    rng = random.Random(7)
    prices = [100.0]
    for _ in range(args.n):
        prices.append(prices[-1] * math.exp(args.drift + args.sigma * rng.gauss(0, 1)))
    rets = log_returns(prices)
    thresh = suggest_threshold(rets, k=args.k)
    evts = cusum_events(rets, thresh)
    print(json.dumps({
        "n_bars": len(rets),
        "threshold": round(thresh, 6),
        "n_events": len(evts),
        "reduction_pct": round(sampling_reduction_rate(len(rets), len(evts)) * 100, 2),
        "first_5_events": evts[:5],
    }, indent=2))
