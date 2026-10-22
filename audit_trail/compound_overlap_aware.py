"""Overlap-aware equal-weight compounding of closed trades.

The legacy dashboard metric (``_compound_equal_weight_capped_sequence`` in
``dashboard_generator.py``) compounds sequentially as if every trade used 100%
of capital, one after another. That math is impossible whenever positions
overlap in time -- and it is catastrophically wrong for resolver batch-closes,
where dozens of trades share one ``closed_at`` instant.

This module provides ``compound_overlap_aware``: a corrected model that detects
concurrency by interval overlap, allocates capital equally among concurrently
active positions (1/N_active each), and applies each trade's return only to its
allocated capital share. It also returns diagnostics so the dashboard can show
*how much* the old sequential model distorted the number.

Sub-project 1, Task 3. See ``updates/2026-10-22-overlap-aware-compounding.md``.
"""
from __future__ import annotations

from datetime import datetime, timezone

__all__ = ["compound_overlap_aware"]


def _parse_ts_utc(value):
    """Parse a timestamp into an aware UTC datetime, or None on failure.

    Tolerates ISO-8601 strings (with/without 'Z'), space-separated forms, and
    date-only forms. Returns ``None`` for anything unparseable so callers can
    fail-soft.
    """
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    if " " in s and "T" not in s:
        s = s.replace(" ", "T")
    for candidate in (s, s[:10]):
        if not candidate:
            continue
        try:
            dt = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def _entry_ts(pick):
    """Entry timestamp via the canonical fallback chain (see dashboard_generator)."""
    raw = (
        pick.get("entry_time")
        or pick.get("timestamp")
        or pick.get("opened_at")
        or pick.get("created_at")
    )
    return _parse_ts_utc(raw)


def _exit_ts(pick):
    """Exit timestamp via the canonical fallback chain (see dashboard_generator)."""
    raw = (
        pick.get("closed_at")
        or pick.get("resolved_at")
        or pick.get("exit_time")
        or pick.get("exit_timestamp")
        or pick.get("exit_date")
        or pick.get("exit_time_est")
    )
    return _parse_ts_utc(raw)


def _pnl_pct_value(pick):
    """Resolve per-trade PnL percent: net-of-cost preferred, else gross."""
    net = pick.get("net_of_cost_pnl_pct")
    if net is not None:
        try:
            return float(net)
        except (TypeError, ValueError):
            pass
    raw = pick.get("pnl_pct")
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


def _cap(value, max_pnl_pct):
    return max(-max_pnl_pct, min(max_pnl_pct, value))


def _zero_diagnostics():
    return {
        "n_trades": 0,
        "n_timed": 0,
        "n_untimed": 0,
        "max_concurrency": 0,
        "mean_concurrency": 0.0,
        "sequential_pct": 0.0,
        "distortion_pp": 0.0,
    }


def _compound_overlap_aware_impl(picks, max_pnl_pct):
    n_trades = len(picks)
    timed = []      # dicts: {idx, entry, exit, pnl (capped)}
    untimed = []    # dicts: {idx, pnl (capped)}

    for idx, pick in enumerate(picks):
        if not isinstance(pick, dict):
            continue
        en = _entry_ts(pick)
        ex = _exit_ts(pick)
        capped = _cap(_pnl_pct_value(pick), max_pnl_pct)
        if en is not None and ex is not None:
            timed.append({"idx": idx, "entry": en, "exit": ex, "pnl": capped})
        else:
            untimed.append({"idx": idx, "pnl": capped})

    n_timed = len(timed)
    n_untimed = len(untimed)

    compounded = 1.0
    max_concurrency = 0
    mean_concurrency = 0.0

    if timed:
        events = []
        for t in timed:
            events.append((t["entry"], +1, t["idx"]))
            events.append((t["exit"], -1, t["idx"]))
        # Entries precede exits at the same instant -> sort by (ts, -delta).
        events.sort(key=lambda e: (e[0], -e[1]))

        acc = {t["idx"]: 0.0 for t in timed}
        total_dur = {t["idx"]: 0.0 for t in timed}
        open_set = set()
        prev_ts = None
        weighted_open = 0.0   # sum over open segments of dur * N
        total_span = 0.0      # total duration with at least one open position

        i = 0
        m = len(events)
        while i < m:
            ts = events[i][0]
            j = i
            while j < m and events[j][0] == ts:
                j += 1

            # Interval [prev_ts, ts): open_set fixed as of before this group.
            if prev_ts is not None and ts != prev_ts:
                dur = (ts - prev_ts).total_seconds()
                if dur > 0:
                    n_open = len(open_set)
                    if n_open > 0:
                        weighted_open += dur * n_open
                        total_span += dur
                        share_contrib = dur / n_open
                        for idx in open_set:
                            acc[idx] += share_contrib
                            total_dur[idx] += dur

            # Process all events at this ts; entries (+1) first within the group.
            group = events[i:j]
            group.sort(key=lambda e: -e[1])
            for _ts, delta, idx in group:
                if delta == +1:
                    open_set.add(idx)
                else:
                    open_set.discard(idx)

            max_concurrency = max(max_concurrency, len(open_set))
            prev_ts = ts
            i = j

        shares = {}
        for t in timed:
            idx = t["idx"]
            dur = total_dur[idx]
            shares[idx] = (acc[idx] / dur) if dur > 0 else 1.0

        # Apply each trade's return to its allocated share. The product of
        # multiplicative factors is commutative, but keep a deterministic order.
        ordered = sorted(timed, key=lambda t: (t["exit"], t["idx"]))
        for t in ordered:
            sh = shares[t["idx"]]
            compounded *= 1.0 + sh * t["pnl"] / 100.0

        mean_concurrency = (weighted_open / total_span) if total_span > 0 else 0.0

    # Untimed tail: applied sequentially at full weight (documented fallback).
    for u in untimed:
        compounded *= 1.0 + u["pnl"] / 100.0

    compounded_pct = (compounded - 1.0) * 100.0

    # Reproduce the OLD sequential model exactly on the same input: sort by
    # timestamp then symbol, cap each, multiply. Used for old-vs-new comparison.
    seq_prod = 1.0

    def _sort_key(p):
        return (str(p.get("timestamp") or ""), str(p.get("symbol") or ""))

    for p in sorted(picks, key=_sort_key):
        if not isinstance(p, dict):
            continue
        raw = float(p.get("pnl_pct", 0) or 0)
        capped = max(-max_pnl_pct, min(max_pnl_pct, raw))
        seq_prod *= 1.0 + capped / 100.0

    sequential_pct = (seq_prod - 1.0) * 100.0

    compounded_rounded = round(compounded_pct, 2)
    sequential_rounded = round(sequential_pct, 2)
    distortion_pp = round(sequential_rounded - compounded_rounded, 2)

    diag = {
        "n_trades": n_trades,
        "n_timed": n_timed,
        "n_untimed": n_untimed,
        "max_concurrency": max_concurrency,
        "mean_concurrency": round(mean_concurrency, 4),
        "sequential_pct": sequential_rounded,
        "distortion_pp": distortion_pp,
    }
    return (compounded_rounded, diag)


def compound_overlap_aware(picks, max_pnl_pct: float = 10.0):
    """Overlap-aware equal-weight compounding of closed trades.

    Returns ``(compounded_pct, diagnostics)`` where diagnostics contains:

      n_trades          - total rows considered
      n_timed           - rows with both entry and exit timestamps parsed
      n_untimed         - rows missing usable timestamps (applied sequentially at the end)
      max_concurrency   - peak number of simultaneously open positions
      mean_concurrency  - time-weighted mean number of open positions
      sequential_pct    - the OLD sequential result on the same input, for comparison
      distortion_pp     - sequential_pct - compounded_pct (percentage points)

    Fail-soft: a degenerate input never raises; it returns ``(0.0, {...zeros...})``.
    """
    if not isinstance(picks, list):
        return (0.0, _zero_diagnostics())
    try:
        return _compound_overlap_aware_impl(picks, max_pnl_pct)
    except Exception:
        return (0.0, _zero_diagnostics())
