"""Tests for alpha_engine/benchmark_closed_ledger.py (Task 10).

Deterministic: every stochastic function takes an explicit seed; assertions
use seeded outcomes only. Run:
    python3 -m pytest tests/test_benchmark_closed_ledger.py -q
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

import pytest

from alpha_engine.benchmark_closed_ledger import (
    BENCHMARK_BY_CLASS,
    WR_HIDE_BELOW_N,
    _asof_close,
    _group_ledgers,
    _to_dt,
    benchmark_ledger,
    build_report,
    compound_return,
    load_closed_picks,
    load_prices,
    main,
    paired_bootstrap,
    profit_factor,
    random_entry_mc,
    wilson_interval,
)


# ─────────────────────────────────────────────────────────────── statistics ──
def test_wilson_two_of_two_is_never_100_pct():
    """The '2/2 = 100%' killer: CI must be wide, never [1.0, 1.0]."""
    lo, hi = wilson_interval(2, 2)
    assert lo < 0.5 < hi == 1.0
    assert lo > 0.1   # informative but nowhere near certain


def test_wilson_large_n_is_tight():
    lo, hi = wilson_interval(60, 100)
    assert 0.50 < lo < 0.55 and 0.64 < hi < 0.70


def test_wilson_zero_n_is_full_range():
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_profit_factor_basic_and_undefined():
    assert profit_factor([1.0, -0.5, 0.5, -0.5]) == pytest.approx(1.5 / 1.0)
    # all wins -> undefined (None), NOT Infinity (Infinity breaks JSON)
    assert profit_factor([0.1, 0.2, 0.3]) is None
    # no trades -> None
    assert profit_factor([]) is None


def test_compound_return():
    assert compound_return([0.10, -0.10]) == pytest.approx(-0.01)
    assert compound_return([]) == 0.0


# ─────────────────────────────────────────────────────────────── paired boot ──
def test_paired_bootstrap_detects_true_edge():
    rng = random.Random(0)
    trades = [rng.gauss(0.010, 0.02) for _ in range(60)]
    bench = [rng.gauss(0.002, 0.02) for _ in range(60)]
    res = paired_bootstrap(trades, bench, n_boot=2000, seed=1)
    assert res["frac_positive"] >= 0.95
    assert res["pass_95"] is True
    assert res["ci_lo"] > 0


def test_paired_bootstrap_flags_no_edge():
    # Deterministic zero-edge population: symmetric +/- diffs centred on 0.
    # (Random zero-mean draws can get lucky with one seed; this cannot.)
    trades = [0.01 if i % 2 == 0 else -0.01 for i in range(60)]
    bench = [0.0] * 60
    res = paired_bootstrap(trades, bench, n_boot=2000, seed=1)
    assert res["frac_positive"] < 0.95
    assert res["pass_95"] is False
    assert abs(res["mean_excess"]) < 1e-12


def test_paired_bootstrap_is_deterministic_given_seed():
    t = [0.01] * 30
    b = [0.0] * 30
    a = paired_bootstrap(t, b, n_boot=500, seed=7)
    c = paired_bootstrap(t, b, n_boot=500, seed=7)
    assert a == c


# ────────────────────────────────────────────────────────────── random MC ────
def _drift_series(n=400, seed=5):
    rng = random.Random(seed)
    px, out = 100.0, []
    for _ in range(n):
        px *= 1.0 + rng.gauss(0.0005, 0.01)
        out.append(px)
    return out


def test_random_entry_mc_ranks_skilled_timing_high():
    """Trades opened just before big up-moves must land in the top decile."""
    prices = _drift_series()
    n = len(prices)
    # find the 30 largest 3-day up-moves and enter before each
    moves = sorted(
        ((prices[i + 3] / prices[i] - 1.0, i) for i in range(n - 4)),
        reverse=True)[:30]
    trades = [("X", i, i + 3, prices[i + 3] / prices[i] - 1.0, 1)
              for _, i in moves]
    res = random_entry_mc({"X": prices}, trades, n_perm=2000, seed=3)
    assert res is not None and res["percentile"] >= 0.90


def test_random_entry_mc_coin_flip_lands_mid():
    prices = _drift_series()
    rng = random.Random(9)
    trades = []
    for _ in range(30):
        ei = rng.randrange(0, len(prices) - 6)
        xi = ei + 3
        trades.append(("X", ei, xi, prices[xi] / prices[ei] - 1.0, 1))
    res = random_entry_mc({"X": prices}, trades, n_perm=2000, seed=3)
    assert res is not None and 0.05 <= res["percentile"] <= 0.95


def test_random_entry_mc_skips_out_of_range():
    res = random_entry_mc({"X": [1.0, 2.0]}, [("X", 0, 5, 0.1, 1)],
                          n_perm=10, seed=1)
    assert res is None


# ───────────────────────────────────────────────────────────────── loading ───
def test_to_dt_dialects():
    a = _to_dt("2026-10-02T17:11:43+00:00")
    b = _to_dt("2026-10-02T17:11:43Z")
    c = _to_dt("2026-10-02T17:11:43")          # naive -> UTC
    assert a == b == c
    assert _to_dt("2026-10-02T17:11:43.681639+00:00").microsecond == 681639
    assert _to_dt(None) is None and _to_dt("garbage") is None


def test_asof_close_looks_back_over_weekend():
    dates = ["2026-10-01", "2026-10-02", "2026-10-05"]
    closes = [100.0, 101.0, 102.0]
    assert _asof_close(dates, closes, "2026-10-03") == 101.0  # Saturday
    assert _asof_close(dates, closes, "2026-10-05") == 102.0
    assert _asof_close(dates, closes, "2026-09-30") is None


def test_load_closed_picks_dashboard_shape(tmp_path):
    feed = {"picks": {"recent_closed": [
        {"symbol": "X", "pnl_pct": 1.5},
        {"symbol": "Y", "pnl_pct": None},   # dropped
        {"symbol": "Z", "pnl_pct": -2.0},
    ]}}
    p = tmp_path / "d.json"
    p.write_text(json.dumps(feed))
    rows = load_closed_picks(str(p))
    assert len(rows) == 2


def test_load_closed_picks_flat_list(tmp_path):
    p = tmp_path / "f.json"
    p.write_text(json.dumps([{"pnl_pct": 1.0}]))
    assert len(load_closed_picks(str(p))) == 1


def test_load_closed_picks_raises_on_unusable(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"picks": [{"pnl_pct": None}]}))
    with pytest.raises(ValueError):
        load_closed_picks(str(p))


def test_load_prices(tmp_path):
    p = tmp_path / "px.json"
    p.write_text(json.dumps({"SPY": {"2026-10-01": 100, "2026-10-02": 101.5}}))
    px = load_prices(str(p))
    assert px["SPY"]["2026-10-02"] == 101.5


def test_group_ledgers():
    rows = [{"strategy": "s1", "asset_class": "EQUITY"},
            {"strategy": "s1", "asset_class": "EQUITY"},
            {"strategy": "s2", "asset_class": "CRYPTO"}]
    g = _group_ledgers(rows)
    assert g[("s1", "EQUITY")] and len(g[("s1", "EQUITY")]) == 2


# ──────────────────────────────────────────────────────────────── ledger ─────
def _spy_series(days=120, start=100.0, seed=11):
    rng = random.Random(seed)
    px, out = start, {}
    d0 = datetime(2026, 5, 1)
    from datetime import timedelta
    for i in range(days):
        day = d0 + timedelta(days=i)
        px *= 1.0 + rng.gauss(0.0004, 0.008)
        out[day.strftime("%Y-%m-%d")] = round(px, 2)
    return out


def _make_rows(n, wr_side, entry_day="2026-06-01", exit_day="2026-06-15"):
    rows = []
    for i in range(n):
        pnl = 2.0 if i % 2 == 0 else -1.0
        if wr_side == "flip":
            pnl = -pnl
        rows.append({
            "symbol": f"S{i}", "strategy": "t", "asset_class": "EQUITY",
            "pnl_pct": pnl,
            "entry_time": f"{entry_day}T14:00:00Z",
            "closed_at": f"{exit_day}T15:00:00Z",
        })
    return rows


def test_benchmark_ledger_wr_hidden_below_n20():
    out = benchmark_ledger(_make_rows(10, "up"), {"SPY": _spy_series()}, "SPY",
                           n_boot=200, n_perm=200)
    assert out["wr"] is None and out["wr_published"] is False
    assert out["wilson_ci"] is None
    assert any("hidden" in n for n in out["notes"])


def test_benchmark_ledger_full_path():
    out = benchmark_ledger(_make_rows(40, "up"), {"SPY": _spy_series()}, "SPY",
                           n_boot=500, n_perm=500, seed=4)
    assert out["n"] == 40 and out["wr"] is not None
    assert out["wilson_ci"] is not None
    assert out["paired_bootstrap"] is not None
    assert out["random_entry_mc"] is not None
    assert out["n_paired"] == 40


def test_benchmark_ledger_no_prices_degrades_softly():
    out = benchmark_ledger(_make_rows(40, "up"), {}, "SPY")
    assert out["paired_bootstrap"] is None and out["random_entry_mc"] is None
    assert any("no price series" in n for n in out["notes"])


def test_benchmark_ledger_no_timestamps_degrades_softly():
    rows = [{"symbol": "A", "strategy": "t", "asset_class": "EQUITY",
             "pnl_pct": 1.0}] * 40
    out = benchmark_ledger(rows, {"SPY": _spy_series()}, "SPY")
    assert out["paired_bootstrap"] is None
    assert any("usable timestamps" in n for n in out["notes"])


# ────────────────────────────────────────────────────────────── build_report ─
def test_build_report_summary_counts():
    rows = (_make_rows(40, "up") +
            [{"symbol": "C", "strategy": "cs", "asset_class": "CRYPTO",
              "pnl_pct": -1.0, "entry_time": "2026-06-01T00:00:00Z",
              "closed_at": "2026-06-02T00:00:00Z"}])
    px = {"SPY": _spy_series(), "BTC-USD": _spy_series(seed=12)}
    rep = build_report(rows, px, n_boot=300, n_perm=300, seed=4)
    assert rep["summary"]["n_ledgers"] == 2
    assert rep["source"].endswith("(Task 10)")
    # JSON-serializable with strict allow_nan (no Infinity leakage)
    json.dumps(rep, allow_nan=False)


def test_build_report_crypto_maps_to_btc():
    rows = [{"symbol": "C", "strategy": "cs", "asset_class": "CRYPTO",
             "pnl_pct": 1.0}]
    rep = build_report(rows, {}, n_boot=10, n_perm=10)
    assert rep["ledgers"][0]["benchmark"] == "BTC-USD"
    assert BENCHMARK_BY_CLASS["EQUITY"] == "SPY"


def test_build_report_unmapped_class_notes_fallback():
    rows = [{"symbol": "Q", "strategy": "s", "asset_class": "WEIRD_CLASS",
             "pnl_pct": 1.0}]
    rep = build_report(rows, {}, n_boot=10, n_perm=10)
    assert any("unmapped asset class" in n for n in rep["ledgers"][0]["notes"])


def test_wr_hide_threshold_constant():
    assert WR_HIDE_BELOW_N == 20


# ────────────────────────────────────────────────────────────────────── CLI ──
def test_cli_end_to_end(tmp_path, capsys):
    feed = {"picks": {"recent_closed": _make_rows(30, "up")}}
    fp = tmp_path / "feed.json"
    fp.write_text(json.dumps(feed))
    pxp = tmp_path / "px.json"
    pxp.write_text(json.dumps({"SPY": _spy_series()}))
    out = tmp_path / "report.json"
    rc = main(["--picks", str(fp), "--prices", str(pxp),
               "--out", str(out), "--n-boot", "200", "--n-perm", "200"])
    assert rc == 0
    rep = json.loads(out.read_text())
    assert rep["ledgers"][0]["n"] == 30
    assert "wrote" in capsys.readouterr().out


def test_cli_bad_picks_returns_2(tmp_path):
    rc = main(["--picks", str(tmp_path / "missing.json")])
    assert rc == 2


# ─────────────────────────── random-entry MC: window-match fixes (2026-10-19) ──
# External review found the MC null broken: nulls were sampled across the FULL
# benchmark history, so a no-skill ledger trading one strong regime scored
# percentile 1.0 (e.g. luxalgo_confluence/CRYPTO: PF 1.03, WR 42% -> 1.0).
# These two tests are the pass gate: a coin-flip strategy must land near the
# 50th percentile, and a ledger trading only the calm tail of a crashing
# series must NOT pin at 1.0.


def _walk(n, mu, sigma, seed, start=100.0):
    rng = random.Random(seed)
    p = start
    out = []
    for _ in range(n):
        p *= 1.0 + rng.gauss(mu, sigma)
        out.append(p)
    return out


def test_mc_coin_flip_lands_near_median():
    """No-skill (random-entry) ledger ~ 50th percentile vs window-matched nulls."""
    prices = _walk(1500, 0.0003, 0.02, seed=7)
    n = len(prices)
    rng = random.Random(13)
    trades = []
    for _ in range(120):
        hold = rng.randint(2, 20)
        ei = rng.randrange(200, n - hold - 1)
        trades.append(("X", ei, ei + hold, prices[ei + hold] / prices[ei] - 1.0, 1))
    pcts = [random_entry_mc({"X": prices}, trades, n_perm=400, seed=s)["percentile"]
            for s in range(8)]
    mean = sum(pcts) / len(pcts)
    assert 0.30 <= mean <= 0.70, f"coin-flip mean percentile {mean:.3f} {pcts}"
    assert all(0.15 <= p <= 0.85 for p in pcts), pcts


def test_mc_window_matched_not_full_history():
    """A ledger trading only the calm tail must not pin at 1.0 vs full history."""
    prices = _walk(1000, -0.004, 0.01, seed=3, start=1000.0) + \
             _walk(300, 0.0005, 0.004, seed=4, start=500.0)
    n = len(prices)
    rng = random.Random(11)
    trades = []
    for _ in range(80):
        hold = rng.randint(2, 12)
        ei = rng.randrange(1000, n - hold - 1)   # trade only the calm tail
        trades.append(("X", ei, ei + hold, prices[ei + hold] / prices[ei] - 1.0, 1))
    mc = random_entry_mc({"X": prices}, trades, n_perm=500, seed=11)
    assert mc["n_symbols"] == 1 and mc["n_simulated"] == 80
    assert mc["percentile"] < 0.9, mc              # full-history null => ~1.0


def test_mc_same_asset_null_not_calm_benchmark():
    """Grok's cross-asset bug: coin flips on a volatile asset must not pin at
    1.0 — the null must be sampled on the asset's own path, not a calm
    benchmark (altcoin trades vs BTC path, penny stocks vs SPY path)."""
    calm = _walk(800, 0.0003, 0.004, seed=21)      # SPY-like, low vol
    vol = _walk(800, 0.0003, 0.04, seed=22)        # altcoin-like, 10x vol
    rng = random.Random(23)
    trades = []
    for _ in range(60):
        hold = rng.randint(2, 15)
        ei = rng.randrange(50, 800 - hold - 1)
        trades.append(("V", ei, ei + hold, vol[ei + hold] / vol[ei] - 1.0, 1))
    pcts = [random_entry_mc({"V": vol, "C": calm}, trades,
                            n_perm=300, seed=s)["percentile"] for s in (1, 2, 3)]
    assert all(0.10 <= p <= 0.95 for p in pcts), pcts
    # a calm-benchmark null would pin these volatile totals at ~1.0


def test_mc_short_sign_negates_null_path():
    """Short trades must be ranked against the negated price path."""
    # flat noise with one 3x level shift at bar 260 — the shock trade captures
    # it; nulls (window-matched, same hold) almost never do.
    rng = random.Random(31)
    px = [100.0 * (1 + rng.gauss(0, 0.002)) for _ in range(400)]
    for i in range(260, 400):
        px[i] *= 3.0
    trades_long, trades_short = [], []
    for k in range(20):                      # small trades far from the shock
        ei = 20 + k * 10
        xi = ei + 5
        r = px[xi] / px[ei] - 1.0
        trades_long.append(("X", ei, xi, r, 1))
        trades_short.append(("X", ei, xi, -r, -1))
    r_shock = px[260] / px[250] - 1.0
    trades_long.append(("X", 250, 260, r_shock, 1))
    trades_short.append(("X", 250, 260, -r_shock, -1))
    rl = random_entry_mc({"X": px}, trades_long, n_perm=300, seed=2)
    rs = random_entry_mc({"X": px}, trades_short, n_perm=300, seed=2)
    # Nulls can also catch the shock boundary (a null start crossing bar 260),
    # so ~0.90 not 1.0 — but sign symmetry must hold decisively.
    assert rl["percentile"] >= 0.80, rl   # long caught the shock -> top
    assert rs["percentile"] <= 0.20, rs   # same trade as short -> bottom
    assert abs(rl["percentile"] + rs["percentile"] - 1.0) < 0.02, (rl, rs)


def test_mc_reports_skips_and_keeps_obs_like_for_like():
    """Same-day round trips (hold=0 on daily closes) + missing symbols are
    skipped and counted; obs_total uses only simulatable trades."""
    prices = _walk(600, 0.001, 0.01, seed=5)
    trades = [("X", 10, 10, 0.05, 1), ("X", 20, 25, 0.02, 1),
              ("X", 30, 33, -0.01, 1), ("GHOST", 0, 5, 0.5, 1)]
    mc = random_entry_mc({"X": prices}, trades, n_perm=100, seed=1)
    assert mc["n_skipped"] == 2 and mc["n_simulated"] == 2
    assert abs(mc["obs_total"] - 0.01) < 1e-9      # only simulatable trades
