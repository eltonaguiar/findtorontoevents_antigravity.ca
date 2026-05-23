"""Lightweight real-time performance alert system.
Detects: strategy degradation, correlation spikes, data staleness, daily loss.
Uses only existing pick data -- no new API calls.

Rolling degradation uses NON-OVERLAPPING samples: baseline = win rate on trades
*before* the trailing 7d window, so we are not comparing a tiny recent slice
to a baseline that already includes that slice. Requires sufficient N on both
sides to avoid the previous flood of HIGH alerts from 3-trade weeks and 2%
baselines.
"""
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# ── Strategy degradation guardrails (tuned 2026-04-05): kill noise, keep signal ──
_ROLLING_DAYS = 7
_MIN_PRIOR_TRADES = 18  # baseline WR from history *before* the rolling window
_MIN_RECENT_TRADES = 10  # trades inside the rolling window with known close time
_MIN_BASELINE_WR = 12.0  # skip if prior WR already noise-tier (e.g. 2% meme baselines)
_MIN_ABSOLUTE_DROP_PP = 10.0  # require meaningful pp gap, not 30% -> 24%
_RELATIVE_DROP = 0.20  # (prior_wr - recent_wr) / prior_wr > this

# Data staleness: low-frequency sources (e.g. claw) were spamming MONITOR at 24h
_STALE_GAP_HOURS_MEDIUM = 56.0


def _ts(s):
    """Parse ISO timestamp to UTC datetime."""
    if not s:
        return None
    try:
        t = str(s).strip()
        if not t:
            return None
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        if " " in t and "T" not in t:
            t = t.replace(" ", "T", 1)
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _pick_closed_time(pick):
    """Prefer settlement/close time for rolling windows (not entry timestamp)."""
    return _ts(pick.get("closed_at")) or _ts(pick.get("timestamp"))


def _win_fraction(picks):
    """Win % over picks that have a real pnl_pct (loop2 #7 ghost-row filter).

    Picks where ``pnl_pct`` is None are "ghost rows" — settled status but no
    realized outcome. Counting them as losses inflated drop alerts and flagged
    healthy strategies as degrading. We now exclude them from both numerator
    and denominator. Returns None if no resolved picks remain.
    """
    if not picks:
        return None
    resolved = [p for p in picks if p.get("pnl_pct") is not None]
    if not resolved:
        return None
    wins = sum(1 for p in resolved if float(p.get("pnl_pct") or 0) > 0)
    return 100.0 * wins / float(len(resolved))


def _alert(sev, typ, msg, action, **kw):
    return {"severity": sev, "type": typ, "message": msg, "action": action, "details": kw}


def _strategy_baseline_wr_from_stats(stats, strat_name):
    """Use per-system strategy rows when present (fixes fwd_wr vs win_rate field bug)."""
    best_wr = None
    best_n = -1
    for s in stats or []:
        for e in s.get("strategies") or []:
            if not e or e.get("name") != strat_name:
                continue
            wr = e.get("fwd_wr")
            if wr is None:
                wr = e.get("win_rate")
            if wr is None:
                continue
            try:
                wrf = float(wr)
            except (TypeError, ValueError):
                continue
            if wrf <= 0 or wrf <= 1.0:  # fraction stored as 0-1
                wrf = wrf * 100.0
            resolved = int(e.get("resolved") or 0)
            if resolved > best_n:
                best_n = resolved
                best_wr = wrf
    return best_wr, best_n


def _strategy_degradation(active, closed, stats):
    """
    Compare recent 7d WR vs *prior* closed history (disjoint) OR vs audited stats
    baseline when we have enough stats rows.

    Suppresses:
    - Tiny recent samples (< MIN_RECENT_TRADES)
    - Thin prior history (< MIN_PRIOR_TRADES) when using pick-derived baseline
    - Trivial baselines (< MIN_BASELINE_WR)
    - Small absolute drops (< MIN_ABSOLUTE_DROP_PP) even if relative drop is 20%
    """
    alerts = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=_ROLLING_DAYS)
    by_strat = defaultdict(list)
    for p in closed or []:
        key = p.get("strategy") or p.get("signal_type") or "unknown"
        by_strat[key].append(p)

    for strat, picks in by_strat.items():
        recent = []
        prior = []
        for p in picks:
            t = _pick_closed_time(p)
            if not t:
                continue
            if t >= cutoff:
                recent.append(p)
            else:
                prior.append(p)

        if len(recent) < _MIN_RECENT_TRADES:
            continue

        r_wr = _win_fraction(recent)
        if r_wr is None:
            continue

        base = None
        base_source = None
        if len(prior) >= _MIN_PRIOR_TRADES:
            base = _win_fraction(prior)
            base_source = "prior_closed"
        if base is None:
            stat_wr, stat_n = _strategy_baseline_wr_from_stats(stats, strat)
            if stat_wr is not None and stat_n >= _MIN_PRIOR_TRADES:
                base = stat_wr
                base_source = "system_stats"

        if base is None or base < _MIN_BASELINE_WR:
            continue

        abs_drop = base - r_wr
        if abs_drop < _MIN_ABSOLUTE_DROP_PP:
            continue
        rel_drop = abs_drop / max(base, 1e-6)
        if rel_drop <= _RELATIVE_DROP:
            continue

        alerts.append(
            _alert(
                "HIGH",
                "STRATEGY_DEGRADATION",
                f"{strat}: rolling 7d WR {r_wr:.0f}% vs baseline {base:.0f}% (>20% drop)",
                "REDUCE",
                strategy=strat,
                rolling_wr=round(r_wr, 1),
                baseline_wr=round(base, 1),
                prior_source=base_source,
                n_recent=len(recent),
                n_prior=len(prior),
            )
        )
    return alerts


def _correlation_spike(active):
    alerts = []
    if not active:
        return alerts
    by_sys = defaultdict(int)
    for p in active:
        by_sys[p.get("source_system", "unknown")] += 1
    total = len(active)
    for sys, cnt in by_sys.items():
        pct = cnt / total * 100
        if cnt > 5 and pct > 60:
            alerts.append(
                _alert(
                    "HIGH",
                    "CORRELATION_SPIKE",
                    f"{sys} has {cnt}/{total} active picks ({pct:.0f}%) -- concentration risk",
                    "REDUCE",
                    system=sys,
                    count=cnt,
                    total=total,
                    pct=round(pct, 1),
                )
            )
        elif cnt > 5 and pct > 40:
            alerts.append(
                _alert(
                    "MEDIUM",
                    "CORRELATION_SPIKE",
                    f"{sys} has {cnt}/{total} active picks ({pct:.0f}%) -- herding watch",
                    "MONITOR",
                    system=sys,
                    count=cnt,
                    total=total,
                    pct=round(pct, 1),
                )
            )
    return alerts


def _data_staleness(active):
    alerts, now = [], datetime.now(timezone.utc)
    if not active:
        return [_alert("CRITICAL", "DATA_STALE", "No active picks -- all scanners may be down", "HALT")]
    by_sys = defaultdict(lambda: datetime.min.replace(tzinfo=timezone.utc))
    stamps = []
    for p in active:
        ts = _ts(p.get("timestamp"))
        if ts:
            stamps.append(ts)
            s = p.get("source_system", "unknown")
            if ts > by_sys[s]:
                by_sys[s] = ts
    if not stamps:
        return alerts
    h_new = (now - max(stamps)).total_seconds() / 3600
    h_old = (now - min(stamps)).total_seconds() / 3600
    if h_old > 48 and h_new > 6:
        alerts.append(
            _alert(
                "CRITICAL",
                "DATA_STALE",
                f"Oldest pick {h_old:.0f}h old, no new picks in {h_new:.1f}h",
                "HALT",
                oldest_hours=round(h_old, 1),
                newest_hours=round(h_new, 1),
            )
        )
    for sys, latest in by_sys.items():
        gap = (now - latest).total_seconds() / 3600
        if gap > _STALE_GAP_HOURS_MEDIUM:
            alerts.append(
                _alert(
                    "MEDIUM",
                    "DATA_STALE",
                    f"{sys} hasn't produced a pick in {gap:.0f}h",
                    "MONITOR",
                    system=sys,
                    hours_since_last=round(gap, 1),
                )
            )
    return alerts


_OPEN_STATUSES = {"OPEN", "PENDING", ""}


def _daily_loss(active):
    """Sum *unrealized* PnL across truly-open picks only.

    2026-04-27 fix: previously the function used
        ``p.get("unrealized_pnl_pct") or p.get("pnl_pct") or 0``
    and counted every row passed in. When the caller's `active` list contained
    rows whose status was already a terminal one (e.g. WON / LOST / TP_HIT) but
    that hadn't yet been moved out of the active pool, the fallback picked up
    each row's *realized* ``pnl_pct``, inflating the negative sum. A single bad
    snapshot tripped a phantom CRITICAL HALT (-60.27% on n=271 vs reality
    -7.66% on n=151). See data-dive in `docs/AUDIT_DASHBOARD_ASSET_CLASS_TWEAKS_2026_04_27.md`.

    Now: filter to OPEN/PENDING/unset status, and only sum the explicit
    ``unrealized_pnl_pct`` field (no realized fallback). Picks without an
    unrealized field contribute 0.
    """
    alerts = []
    open_picks = [
        p for p in active
        if str(p.get("status", "") or "").upper() in _OPEN_STATUSES
    ]
    # TODO(round3-panel-2026-04-29): pnl_pct units mixed across sources
    # (decimal vs percent); this naive sum can under- or over-trigger HALT
    # when a window mixes both conventions. See
    # tests/test_phantom_halt_mixed_units_regression.py and
    # reports/round3_bugs_qa_synthesis_2026_04_29.md (P0 items #3, #5).
    # Bundle fix with P0-DATA pnl_pct_unit ingest normalization in
    # audit_trail/recorder.py before patching this line in isolation.
    total = sum(float(p.get("unrealized_pnl_pct") or 0) for p in open_picks)
    if total < -5:
        alerts.append(
            _alert(
                "CRITICAL",
                "DAILY_LOSS",
                f"Unrealized portfolio PnL {total:+.1f}% -- daily loss limit approaching",
                "HALT",
                total_unrealized_pnl_pct=round(total, 2),
                pick_count=len(open_picks),
            )
        )
    elif total < -3:
        alerts.append(
            _alert(
                "HIGH",
                "DAILY_LOSS",
                f"Unrealized portfolio PnL {total:+.1f}% -- caution",
                "REDUCE",
                total_unrealized_pnl_pct=round(total, 2),
                pick_count=len(open_picks),
            )
        )
    return alerts


def check_all_alerts(active_picks=None, closed_picks=None, system_stats=None):
    """Run all alert checks. Returns list of alert dicts sorted by severity."""
    active_picks, closed_picks = active_picks or [], closed_picks or []
    sev = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts = (
        _strategy_degradation(active_picks, closed_picks, system_stats)
        + _correlation_spike(active_picks)
        + _data_staleness(active_picks)
        + _daily_loss(active_picks)
    )
    alerts.sort(key=lambda a: sev.get(a["severity"], 9))
    return alerts
