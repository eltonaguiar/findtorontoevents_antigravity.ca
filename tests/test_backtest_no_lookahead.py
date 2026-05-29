"""
No-lookahead audit for tools/backtest_swarm_strategies.py engines.

A backtest "peeks at the future" if a signal at bar t depends on data after t —
the #1 way AI-generated strategies fake edge. We prove the absence of lookahead by
PREFIX STABILITY: run each engine on the full series and on truncated prefixes, and
assert that every trade entered well before the truncation boundary is IDENTICAL in
both runs. If any future bar influenced an earlier decision, truncating would change
those earlier entries and the assertion fails.

Deterministic synthetic OHLCV (no network) so the test is hermetic + reproducible.
Run: python3 tests/test_backtest_no_lookahead.py   (or: pytest tests/test_backtest_no_lookahead.py)
"""
import importlib.util
import math
import pathlib

_MOD_PATH = pathlib.Path(__file__).resolve().parents[1] / "tools" / "backtest_swarm_strategies.py"
_spec = importlib.util.spec_from_file_location("bss", _MOD_PATH)
bss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bss)

BUFFER = 80  # bars; any trade entered > BUFFER before truncation has fully closed


def _gen(n):
    """Deterministic OHLCV with cycles + drift so both engines actually fire trades."""
    bars = []
    for i in range(n):
        c = 100 + math.sin(i / 15.0) * 3 + math.sin(i / 47.0) * 8 + i * 0.02
        o = c - math.sin(i / 9.0) * 0.5
        h = max(o, c) + abs(math.sin(i / 5.0)) * 1.2 + 0.5
        l = min(o, c) - abs(math.cos(i / 6.0)) * 1.2 - 0.5
        v = 1000 + abs(math.sin(i / 3.0)) * 800 + (i % 7) * 120
        bars.append((o, h, l, c, v))
    return bars


def _entries(trades):
    return [i for i, _ in trades]


def _run(engine, bars, kind):
    if kind == "momentum":
        return engine(bars)
    if kind == "mr_rsi":
        return engine(bars, use_rsi=True)
    return engine(bars, allow_short=True)


def test_no_lookahead():
    bars = _gen(340)
    cases = [
        (bss.engine_momentum_breakout, "momentum"),
        (bss.engine_bb_mean_reversion, "mr_rsi"),
        (bss.engine_bb_mean_reversion, "mr_short"),
    ]
    total_compared = 0
    for engine, kind in cases:
        full_entries = _entries(_run(engine, bars, kind))
        for k in (180, 230, 280):
            trunc_entries = _entries(_run(engine, bars[:k], kind))
            cutoff = k - BUFFER
            a = [i for i in full_entries if i < cutoff]
            b = [i for i in trunc_entries if i < cutoff]
            assert a == b, (
                f"LOOKAHEAD detected in {kind}: truncating at k={k} changed earlier "
                f"entries (<{cutoff}): full={a} vs trunc={b}"
            )
            total_compared += len(a)
    assert total_compared > 0, "test ineffective — engines produced no early trades to compare"


if __name__ == "__main__":
    test_no_lookahead()
    print("no-lookahead audit PASSED — engines are prefix-stable (no future-bar leakage)")
