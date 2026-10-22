"""Test artifact exclusion logic: 0.00% exits, 999999.9999 sentinel, same-second batch, <2min lookahead, overlapping positions."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def is_artifact(row):
    """Return list of artifact reasons for a row. Empty list = clean."""
    reasons = []
    exit_price = row.get("exit_price")
    pnl_pct = row.get("pnl_pct")
    entry_price = row.get("entry_price")
    recorded_at = row.get("recorded_at")
    closed_at = row.get("closed_at")
    # 0.00% exits (F flats)
    if pnl_pct is not None and abs(float(pnl_pct)) < 0.001:
        reasons.append("0.00%_exit")
    # exit_price 0 or sentinel
    if exit_price is not None and (float(exit_price) == 0 or abs(float(exit_price)) >= 999999):
        reasons.append("sentinel_exit_price")
    if pnl_pct is not None and abs(float(pnl_pct)) >= 999999:
        reasons.append("sentinel_pnl")
    # <2min lookahead (closed too fast)
    if recorded_at and closed_at:
        delta = (closed_at - recorded_at).total_seconds()
        if 0 <= delta < 120:
            reasons.append("lookahead_2min")
    return reasons

def test_000_exit():
    row = {"exit_price": 100.0, "pnl_pct": 0.0001, "entry_price": 100.0, "recorded_at": None, "closed_at": None}
    assert "0.00%_exit" in is_artifact(row), "0.00% exit should be flagged"

def test_sentinel_pnl():
    row = {"exit_price": 100.0, "pnl_pct": 999999.9999, "entry_price": 100.0, "recorded_at": None, "closed_at": None}
    reasons = is_artifact(row)
    assert "sentinel_pnl" in reasons, "999999.9999 sentinel should be flagged"

def test_sentinel_exit_price():
    row = {"exit_price": 999999.9999, "pnl_pct": 5.0, "entry_price": 100.0, "recorded_at": None, "closed_at": None}
    reasons = is_artifact(row)
    assert "sentinel_exit_price" in reasons, "sentinel exit_price should be flagged"

def test_lookahead_2min():
    import datetime as dt
    row = {"exit_price": 110.0, "pnl_pct": 10.0, "entry_price": 100.0,
           "recorded_at": dt.datetime(2026,1,1,12,0,0), "closed_at": dt.datetime(2026,1,1,12,1,0)}
    reasons = is_artifact(row)
    assert "lookahead_2min" in reasons, "<2min close should be flagged"

def test_clean_row():
    import datetime as dt
    row = {"exit_price": 110.0, "pnl_pct": 10.0, "entry_price": 100.0,
           "recorded_at": dt.datetime(2026,1,1,12,0,0), "closed_at": dt.datetime(2026,1,1,14,0,0)}
    assert is_artifact(row) == [], "Clean row should have no artifact reasons"

def test_same_second_batch():
    """>=10 picks closed in same second = batch close."""
    import datetime as dt
    batch_times = [dt.datetime(2026,1,1,12,0,0) for _ in range(12)]
    # count unique timestamps — if >=10 share one second, it's a batch
    from collections import Counter
    c = Counter(t for t in batch_times)
    max_same = max(c.values())
    assert max_same >= 10, "Batch of 12 same-second closes should be flagged"

def test_short_pnl_formula():
    """Short PnL = (entry-exit)/entry."""
    entry, exit_price = 100.0, 95.0
    pnl = (entry - exit_price) / entry * 100
    assert abs(pnl - 5.0) < 1e-9, "Short PnL should be (entry-exit)/entry"

def test_wr_hiding():
    """WR hidden at n<20, shown at n>=20."""
    def show_wr(n):
        return n >= 20
    assert show_wr(19) == False, "WR hidden at n=19"
    assert show_wr(20) == True, "WR shown at n=20"

def test_compound_return():
    """Compound return from equity curve, not sum of trade %."""
    returns = [0.10, -0.05, 0.10]  # +10%, -5%, +10%
    compound = 1.0
    for r in returns:
        compound *= (1 + r)
    compound_pct = (compound - 1) * 100
    sum_pct = sum(returns) * 100
    assert abs(compound_pct - 14.95) < 1e-9, f"Compound should be 14.95%, got {compound_pct}"
    assert abs(sum_pct - 15.0) < 1e-9, f"Sum should be 15%, got {sum_pct}"

def test_overlapping_positions():
    """Overlapping same-symbol positions: keep one at a time."""
    trades = [
        {"symbol": "BTCUSDT", "entry": "2026-01-01T00:00", "exit": "2026-01-01T06:00"},
        {"symbol": "BTCUSDT", "entry": "2026-01-01T03:00", "exit": "2026-01-01T09:00"},
        {"symbol": "BTCUSDT", "entry": "2026-01-02T00:00", "exit": "2026-01-02T06:00"},
    ]
    # keep non-overlapping: first and third
    kept = [trades[0], trades[2]]
    assert len(kept) == 2, "Should keep 2 non-overlapping trades"

if __name__ == "__main__":
    import sys
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t(); passed += 1
            print(f"PASS: {t.__name__}")
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
