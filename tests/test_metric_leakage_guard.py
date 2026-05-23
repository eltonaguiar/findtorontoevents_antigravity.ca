"""Regression guard — detects TARGET LEAKAGE in trading-pick track-record metrics.

Source: reports/AUDIT_STAT_VALIDATION_2026-05-22.md, Part 4.

The audit found that `sym_track_wr` (symbol track-record win rate) stamped on
each pick in `picks.recent_closed` is a target-leakage artifact. It is built by
`_build_strategy_symbol_track_stats` (audit_trail/dashboard_generator.py ~5425)
by aggregating ALL closed picks for each (strategy, symbol) bucket with NO time
filter, then stamped onto every pick (~line 15563). So every pick is tagged with
the all-time WR of a window that includes that very pick and every later pick —
not point-in-time.

Smoking gun (audit): for 81 of 139 (strategy,symbol) groups with n>=5, the
stamped `sym_track_wr` was numerically identical (<=0.6pp) to that group's OWN
realized win rate. "High sym_track_wr predicts wins" reduces to "buckets that
won a lot, won a lot" — tautological.

This module:
  1. test_sym_track_wr_leakage_rate_below_threshold — the leakage detector.
     Currently xfails (metric is still leaky). It auto-flips to xpass once a
     point-in-time recompute lands, so CI surfaces the fix.
  2. test_point_in_time_sym_wr_never_uses_future — exercises the reference
     `point_in_time_sym_wr` helper a future fix should adopt. PASSES now.
  3. test_sym_track_wr_schema_guard — basic always-passing schema guard:
     `sym_track_wr` is numeric and in [0, 100] where present.

Read-only on audit_dashboard/data/dashboard_data.json. Skips gracefully when
the payload or the relevant fields are absent (lean CI checkouts).

Run from repo root:
    python3 -m pytest tests/test_metric_leakage_guard.py -v
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "audit_dashboard" / "data" / "dashboard_data.json"

# A group is considered "leaky" when the stamped value is within this many
# percentage points of the group's OWN realized WR — i.e. the metric was
# computed in-sample over a window that includes the group's own picks.
LEAKAGE_TOL_PP = 0.6

# Minimum picks per (strategy, symbol) group to be statistically meaningful.
MIN_GROUP_N = 5

# Test fails (i.e. the metric is healthy) only when leakage rate is below this.
# The audit measured ~0.58 (81/139); a leakage-free point-in-time metric should
# land well under 0.20 by chance alone.
MAX_ACCEPTABLE_LEAKAGE_RATE = 0.20


# --------------------------------------------------------------------------
# fixtures / helpers
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def closed_picks():
    if not DATA.exists():
        pytest.skip(f"dashboard_data.json absent at {DATA} — run pipeline to generate")
    with DATA.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    picks = payload.get("picks", {}).get("recent_closed")
    if not isinstance(picks, list) or not picks:
        pytest.skip("picks.recent_closed missing or empty")
    return picks


def _parse_dt(s):
    """Parse an ISO-ish timestamp to a tz-aware UTC datetime, or None."""
    if not s or not isinstance(s, str):
        return None
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _realized_wr(picks):
    """Realized win rate (%) from pnl_pct sign — wins / (wins + losses).

    Returns None when there are no resolved (non-zero pnl) picks.
    """
    wins = sum(1 for p in picks if isinstance(p.get("pnl_pct"), (int, float)) and p["pnl_pct"] > 0)
    losses = sum(1 for p in picks if isinstance(p.get("pnl_pct"), (int, float)) and p["pnl_pct"] < 0)
    denom = wins + losses
    if denom == 0:
        return None
    return wins / denom * 100.0


# --------------------------------------------------------------------------
# Reference implementation a future fix should adopt
# --------------------------------------------------------------------------
def point_in_time_sym_wr(picks, ts_field="timestamp"):
    """Compute a leakage-FREE point-in-time (strategy, symbol) win rate.

    For each pick, the (strategy, symbol) win rate is computed using ONLY
    picks in the same bucket whose timestamp is STRICTLY EARLIER. The pick
    itself, and every same-or-later pick, are excluded — eliminating the
    target leakage in the current all-time `sym_track_wr`.

    Args:
        picks: iterable of dicts, each with at least `strategy`, `symbol`,
            `pnl_pct`, and a timestamp under ``ts_field``.
        ts_field: name of the timestamp field (default "timestamp").

    Returns:
        list of float|None, parallel to the INPUT order of ``picks``. Each
        entry is the point-in-time WR (%) for that pick, or None when there
        are no strictly-earlier resolved picks in its bucket (e.g. the first
        pick of a group always gets None).

    Ties: picks with an identical timestamp are NOT counted as "earlier" —
    only strictly-earlier picks contribute, so a pick is never informed by a
    same-timestamp sibling.
    """
    enumerated = list(enumerate(picks))

    # Bucket picks by (strategy, symbol), each entry carries its parsed time.
    buckets = defaultdict(list)
    for orig_idx, p in enumerated:
        key = (p.get("strategy"), p.get("symbol"))
        buckets[key].append((orig_idx, _parse_dt(p.get(ts_field)), p))

    result = [None] * len(enumerated)
    for key, members in buckets.items():
        # Stable sort by time; picks with an unparseable timestamp sort first
        # (datetime.min) so they never see "future" siblings as earlier.
        members_sorted = sorted(
            members,
            key=lambda m: m[1] or datetime.min.replace(tzinfo=timezone.utc),
        )
        for i, (orig_idx, this_ts, _p) in enumerate(members_sorted):
            earlier = []
            for j in range(i):
                _oj, other_ts, other_p = members_sorted[j]
                # STRICTLY earlier only — equal timestamps are excluded.
                if this_ts is not None and other_ts is not None and other_ts >= this_ts:
                    continue
                earlier.append(other_p)
            result[orig_idx] = _realized_wr(earlier)
    return result


# --------------------------------------------------------------------------
# 1. THE LEAKAGE DETECTOR (xfail until point-in-time recompute lands)
# --------------------------------------------------------------------------
@pytest.mark.xfail(
    reason=(
        "sym_track_wr is in-sample / target-leaked — see "
        "reports/AUDIT_STAT_VALIDATION_2026-05-22.md; flips to PASS (xpass) "
        "once point-in-time recompute lands"
    ),
    strict=False,
)
def test_sym_track_wr_leakage_rate_below_threshold(closed_picks):
    """LEAKAGE RATE of sym_track_wr must be below threshold.

    For each (strategy, symbol) group with n>=MIN_GROUP_N, compare the stamped
    `sym_track_wr` to the group's OWN realized WR. If they coincide within
    LEAKAGE_TOL_PP for a large fraction of groups, the metric is computed
    in-sample (it sees its own picks) — that is target leakage.

    Currently EXPECTED TO FAIL (xfail): the audit measured ~58% leakage.
    Auto-flips to xpass when someone re-derives sym_track_wr point-in-time.
    """
    groups = defaultdict(list)
    for p in closed_picks:
        strat, sym = p.get("strategy"), p.get("symbol")
        if strat and sym and isinstance(p.get("pnl_pct"), (int, float)):
            groups[(strat, sym)].append(p)

    big = {k: v for k, v in groups.items() if len(v) >= MIN_GROUP_N}
    if not big:
        pytest.skip(f"no (strategy,symbol) groups with n>={MIN_GROUP_N}")

    checked = 0
    leaky = 0
    leaky_examples = []
    for (strat, sym), members in big.items():
        own_wr = _realized_wr(members)
        if own_wr is None:
            continue
        stamped_vals = [
            p["sym_track_wr"]
            for p in members
            if isinstance(p.get("sym_track_wr"), (int, float))
        ]
        if not stamped_vals:
            continue
        # Average the stamped value across the group; in the leaky regime all
        # picks in a bucket carry the SAME all-time WR so the mean == that WR.
        stamped = sum(stamped_vals) / len(stamped_vals)
        checked += 1
        if abs(stamped - own_wr) <= LEAKAGE_TOL_PP:
            leaky += 1
            if len(leaky_examples) < 5:
                leaky_examples.append(
                    (strat, sym, len(members), round(stamped, 2), round(own_wr, 2))
                )

    if checked == 0:
        pytest.skip("no groups had both a realized WR and a stamped sym_track_wr")

    leakage_rate = leaky / checked
    assert leakage_rate < MAX_ACCEPTABLE_LEAKAGE_RATE, (
        f"sym_track_wr LEAKAGE RATE = {leakage_rate:.3f} "
        f"({leaky}/{checked} groups) — stamped value coincides with each "
        f"group's OWN realized WR (within {LEAKAGE_TOL_PP}pp). The metric is "
        f"computed in-sample (all-time, no time cutoff). Examples "
        f"(strategy, symbol, n, stamped_wr, own_wr): {leaky_examples}. "
        f"Fix: point-in-time recompute — see point_in_time_sym_wr() and "
        f"reports/AUDIT_STAT_VALIDATION_2026-05-22.md Part 4."
    )


# --------------------------------------------------------------------------
# 2. REFERENCE FIX — point-in-time helper never uses same-or-later data
# --------------------------------------------------------------------------
def test_point_in_time_sym_wr_never_uses_future():
    """point_in_time_sym_wr() must compute each pick's WR from STRICTLY
    earlier picks only — the first pick of a group gets None, and no pick is
    informed by a same- or later-timestamped sibling.

    This is the reference implementation a future fix should adopt; it PASSES.
    """
    # Synthetic (strategy, symbol) = (alpha, AAA) bucket, deliberately
    # interleaved out of chronological order in the input list to prove the
    # helper sorts by time, not by position.
    picks = [
        # idx 0 — chronologically the 3rd pick
        {"strategy": "alpha", "symbol": "AAA", "timestamp": "2026-05-03T00:00:00Z", "pnl_pct": -1.0},
        # idx 1 — chronologically the 1st pick (a WIN)
        {"strategy": "alpha", "symbol": "AAA", "timestamp": "2026-05-01T00:00:00Z", "pnl_pct": 2.0},
        # idx 2 — chronologically the 2nd pick (a WIN)
        {"strategy": "alpha", "symbol": "AAA", "timestamp": "2026-05-02T00:00:00Z", "pnl_pct": 1.5},
        # idx 3 — chronologically the 4th pick (a LOSS)
        {"strategy": "alpha", "symbol": "AAA", "timestamp": "2026-05-04T00:00:00Z", "pnl_pct": -0.5},
        # idx 4 — different bucket entirely, single pick
        {"strategy": "beta", "symbol": "BBB", "timestamp": "2026-05-01T00:00:00Z", "pnl_pct": 3.0},
    ]

    wr = point_in_time_sym_wr(picks)
    assert len(wr) == len(picks)

    # idx 1 is the FIRST pick of (alpha, AAA) chronologically -> no earlier data -> None
    assert wr[1] is None, f"first pick of a group must get None, got {wr[1]}"

    # idx 2 is the 2nd chronologically; only earlier pick is idx1 (a win) -> 100%
    assert wr[2] == pytest.approx(100.0), f"expected 100.0, got {wr[2]}"

    # idx 0 is the 3rd chronologically; earlier = idx1 (win) + idx2 (win) -> 100%
    assert wr[0] == pytest.approx(100.0), f"expected 100.0, got {wr[0]}"

    # idx 3 is the 4th (last) chronologically; earlier = idx1,idx2 (wins) +
    # idx0 (loss) -> 2 wins / 3 -> 66.67%. CRUCIALLY this MUST NOT include
    # idx3 itself (the loss). A leaky all-time impl would give 2/4 = 50%.
    assert wr[3] == pytest.approx(2.0 / 3.0 * 100.0), (
        f"last pick WR must use only the 3 strictly-earlier picks "
        f"(2W/1L -> 66.67%), got {wr[3]} — if it is 50.0 the helper is "
        f"counting the pick's own outcome (leakage)"
    )

    # idx 4 is the ONLY pick in the (beta, BBB) bucket -> None
    assert wr[4] is None, f"lone pick of a group must get None, got {wr[4]}"

    # Tie-breaking: two picks with the SAME timestamp must not see each other.
    tie_picks = [
        {"strategy": "g", "symbol": "S", "timestamp": "2026-05-01T00:00:00Z", "pnl_pct": 5.0},
        {"strategy": "g", "symbol": "S", "timestamp": "2026-05-01T00:00:00Z", "pnl_pct": -5.0},
    ]
    tie_wr = point_in_time_sym_wr(tie_picks)
    assert tie_wr[0] is None and tie_wr[1] is None, (
        f"same-timestamp picks must not inform each other (strictly-earlier "
        f"only), got {tie_wr}"
    )

    # Sanity: a fully self-consistent leakage check — for the (alpha,AAA)
    # bucket the point-in-time series must NEVER equal the bucket's all-time
    # WR (2W/2L = 50%) on the early picks, proving it is not in-sample.
    all_time_wr = _realized_wr([p for p in picks if p["symbol"] == "AAA"])
    assert all_time_wr == pytest.approx(50.0)
    early_pit = [wr[1], wr[2]]  # first two chronological picks
    assert all(
        v is None or not math.isclose(v, all_time_wr, abs_tol=1e-9) for v in early_pit
    ), "early point-in-time WRs must differ from the bucket's all-time WR"


# --------------------------------------------------------------------------
# 3. ALWAYS-PASSING SCHEMA GUARD
# --------------------------------------------------------------------------
def test_sym_track_wr_schema_guard(closed_picks):
    """Basic schema guard: where `sym_track_wr` is present it must be a
    number in [0, 100]. Always passes — guards against the field going
    missing or turning non-numeric. Does NOT assert anything about leakage.
    """
    present = [
        p for p in closed_picks if p.get("sym_track_wr") is not None
    ]
    if not present:
        pytest.skip("no picks carry sym_track_wr")

    bad = []
    for p in present:
        v = p["sym_track_wr"]
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            bad.append((p.get("strategy"), p.get("symbol"), repr(v), "non-numeric"))
        elif not (0.0 <= float(v) <= 100.0):
            bad.append((p.get("strategy"), p.get("symbol"), v, "out-of-range"))
    assert not bad, f"sym_track_wr schema violations: {bad[:5]}"


# --------------------------------------------------------------------------
# 4. GENERATOR FUNCTION GUARD — _stamp_pit_sym_track must be leakage-free
# --------------------------------------------------------------------------
def _load_generator():
    """Import audit_trail/dashboard_generator.py in isolation. Skips the test
    if the module cannot be imported in this environment (heavy module)."""
    import importlib.util

    path = REPO / "audit_trail" / "dashboard_generator.py"
    if not path.exists():
        pytest.skip("dashboard_generator.py not present")
    spec = importlib.util.spec_from_file_location("_dg_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"dashboard_generator import failed: {type(exc).__name__}")
    return mod


def test_stamp_pit_sym_track_is_leakage_free():
    """The production `_stamp_pit_sym_track` must compute each pick's
    `sym_track_wr_pit` from STRICTLY-earlier closed history only — never from
    the pick's own outcome or any same/later sibling.
    """
    dg = _load_generator()
    stamp = getattr(dg, "_stamp_pit_sym_track", None)
    assert callable(stamp), "_stamp_pit_sym_track missing from dashboard_generator"

    hist = [
        {"strategy": "s", "symbol": "BTCUSDT", "status": "WON", "pnl_pct": 2,
         "timestamp": "2026-01-01T00:00:00Z"},
        {"strategy": "s", "symbol": "BTCUSDT", "status": "LOST", "pnl_pct": -1,
         "timestamp": "2026-01-02T00:00:00Z"},
        {"strategy": "s", "symbol": "BTCUSDT", "status": "LOST", "pnl_pct": -1,
         "timestamp": "2026-01-03T00:00:00Z"},
    ]
    # Each scored pick has a huge WON outcome — it must NOT inflate its own pit.
    first = {"strategy": "s", "symbol": "BTCUSDT", "status": "WON", "pnl_pct": 99,
             "timestamp": "2026-01-01T00:00:00Z"}      # tie with hist -> strict< -> None
    later = {"strategy": "s", "symbol": "BTCUSDT", "status": "WON", "pnl_pct": 99,
             "timestamp": "2026-01-04T00:00:00Z"}      # 3 prior: 1W/2L -> 33.3
    mid = {"strategy": "s", "symbol": "BTCUSDT", "status": "WON", "pnl_pct": 99,
           "timestamp": "2026-01-02T12:00:00Z"}        # 2 prior: 1W/1L -> 50.0

    stamp([first, later, mid], hist)

    assert first["sym_track_wr_pit"] is None and first["sym_track_total_pit"] == 0
    assert later["sym_track_wr_pit"] == pytest.approx(33.3, abs=0.1)
    assert later["sym_track_total_pit"] == 3
    assert mid["sym_track_wr_pit"] == pytest.approx(50.0, abs=0.1)
    assert mid["sym_track_total_pit"] == 2
    # The leaky all-time field is left untouched (shadow column, not a replacement).
    assert "sym_track_wr" not in first or first.get("sym_track_wr") != 100.0
