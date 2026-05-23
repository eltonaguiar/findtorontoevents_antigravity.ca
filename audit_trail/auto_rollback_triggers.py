"""Auto-rollback trigger detector (opt-in sidecar; default-OFF behavior).

Defense-in-depth module per panel review item #8
(reports/PANEL_REVIEW_2026_04_29_OPERATION_PHENOMENAL_FOLLOWUPS.md, 3/4 quick-win).

Threshold correction
--------------------
The 2026-04-29 "Operation Phenomenal Performance" entry in `updates/index.html`
listed `CRYPTO MDD >195%` as an auto-rollback trigger. That threshold is
mathematically impossible: MDD on a non-leveraged equity curve is bounded by
~100%, and even our pnl_pct-sum aggregation tops out near that ceiling.
Panel AI #2 flagged this explicitly and 3/4 panelists concurred. This module
uses 30% as the canonical MDD trigger (Tier 2 hedge-fund cap, per
`docs/PERFORMANCE_CHARTER.md`).

Public API
----------
- check_rollback_conditions(asset_class, window_days) -> list[dict]
    Pure function. Reads JSON files, returns triggered conditions. Takes NO
    rollback action whatsoever; integration with an actual rollback path is
    out of scope and will land in a follow-up PR.

Triggers
--------
1. banned_id_emit  — any pick in `picks.active` or `picks.active_raw` whose
   strategy / source matches a kill_list entry, AND the kill_list is not
   auto-expired.
2. wr_3d_below_28  — for any asset class with n>=20 trades in the rolling
   `window_days`-day window, fires if WR < 28%.
3. mdd_breach      — MDD over recent_closed (sorted by closed_at) for the
   given asset_class exceeds 30% (peak-to-trough on cumulative sum_pnl_pct).

CLI
---
    python -m audit_trail.auto_rollback_triggers

Wire-Up Plan (out of scope for this PR)
---------------------------------------
Future call site: `alpha_engine/smart_picks_engine.py`, pre-emission. Triggers
will be logged to `audit_dashboard/data/auto_rollback_log.json` and surfaced
on the dashboard. Expected wire-up PR: 2026-05-05.

Stdlib-only.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DASHBOARD_DATA = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
DEFAULT_ACTIVE_PICKS = REPO_ROOT / "alpha_engine" / "data" / "active_picks.json"
DEFAULT_WHITELIST = REPO_ROOT / "alpha_engine" / "data" / "core_whitelist.json"

# Panel-approved thresholds.
WR_3D_THRESHOLD_PCT = 28.0
WR_3D_MIN_TRADES = 20
MDD_THRESHOLD_PCT = 30.0  # was 195% (mathematically impossible); panel-corrected.


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _safe_load(path: Path) -> Any:
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _normalize_kill_entries(entries: Iterable[Any]) -> set[str]:
    out: set[str] = set()
    for raw in entries or []:
        if raw is None:
            continue
        s = str(raw).strip().lower()
        if not s:
            continue
        out.add(s)
        # Also index the bare suffix after `::` for source-prefixed entries
        # like `alpha_engine::ml_enhanced_FETUSDT_1d_B_lightgbm`.
        if "::" in s:
            out.add(s.split("::", 1)[1])
    return out


def _load_kill_state(whitelist_path: Path) -> tuple[set[str], bool]:
    data = _safe_load(whitelist_path) or {}
    kill_list = data.get("kill_list") or []
    metadata = data.get("kill_list_metadata") or {}
    auto_expired = bool(
        metadata.get("auto_expired")
        or data.get("kill_list_auto_expired")
        or False
    )
    return _normalize_kill_entries(kill_list), auto_expired


# ---------------------------------------------------------------------------
# Trigger 1: banned-ID emit detection
# ---------------------------------------------------------------------------


def _pick_identifiers(pick: dict) -> set[str]:
    """Return the set of identifier strings to test against the kill_list."""
    keys = ("strategy", "source", "source_system", "system")
    out: set[str] = set()
    for k in keys:
        v = pick.get(k)
        if v is None:
            continue
        s = str(v).strip().lower()
        if s:
            out.add(s)
    # Also add common compound keys e.g. `<source_system>::<strategy>`.
    src = pick.get("source_system") or pick.get("source") or pick.get("system")
    strat = pick.get("strategy")
    if src and strat:
        out.add(f"{str(src).strip().lower()}::{str(strat).strip().lower()}")
    return out


def detect_banned_id_emits(
    active_picks: list[dict],
    kill_set: set[str],
    *,
    auto_expired: bool,
    bucket: str = "active",
) -> list[dict]:
    """Return one trigger dict per pick that matches a kill_list entry."""
    if auto_expired:
        return []
    if not kill_set or not active_picks:
        return []
    out: list[dict] = []
    for pick in active_picks:
        if not isinstance(pick, dict):
            continue
        ids = _pick_identifiers(pick)
        matches = ids & kill_set
        if matches:
            out.append(
                {
                    "trigger": "banned_id_emit",
                    "severity": "critical",
                    "details": {
                        "bucket": bucket,
                        "pick_id": pick.get("id"),
                        "symbol": pick.get("symbol"),
                        "strategy": pick.get("strategy"),
                        "source": pick.get("source") or pick.get("source_system"),
                        "matched_kill_entries": sorted(matches),
                    },
                }
            )
    return out


# ---------------------------------------------------------------------------
# Trigger 2: rolling 3d WR < 28%
# ---------------------------------------------------------------------------


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _is_win(pick: dict) -> bool:
    """Pick is a winner if pnl_pct > 0 (canonical rule from kill_run_stats)."""
    pnl = pick.get("pnl_pct")
    if pnl is None:
        # Fall back to status string if pnl_pct missing.
        return str(pick.get("status", "")).upper() == "WON"
    try:
        return float(pnl) > 0
    except (TypeError, ValueError):
        return False


def _filter_recent_by_class(
    picks: list[dict],
    asset_class: str,
    window: timedelta,
    *,
    now: datetime,
) -> list[dict]:
    cutoff = now - window
    target = asset_class.upper()
    out = []
    for p in picks:
        if not isinstance(p, dict):
            continue
        if str(p.get("asset_class") or "").upper() != target:
            continue
        ts = _parse_ts(p.get("closed_at") or p.get("timestamp"))
        if ts is None or ts < cutoff:
            continue
        out.append(p)
    return out


def detect_wr_breaches(
    recent_closed: list[dict],
    *,
    window_days: int,
    now: datetime,
) -> list[dict]:
    """Return one trigger per asset class with WR<28% over n>=20 in window."""
    by_class: dict[str, list[dict]] = {}
    cutoff = now - timedelta(days=window_days)
    for p in recent_closed or []:
        if not isinstance(p, dict):
            continue
        ts = _parse_ts(p.get("closed_at") or p.get("timestamp"))
        if ts is None or ts < cutoff:
            continue
        cls = str(p.get("asset_class") or "UNKNOWN").upper()
        by_class.setdefault(cls, []).append(p)

    out = []
    for cls, picks in by_class.items():
        n = len(picks)
        if n < WR_3D_MIN_TRADES:
            continue
        wins = sum(1 for p in picks if _is_win(p))
        wr_pct = (wins / n) * 100.0
        if wr_pct < WR_3D_THRESHOLD_PCT:
            out.append(
                {
                    "trigger": "wr_3d_below_28",
                    "severity": "high",
                    "asset_class": cls,
                    "wr_pct": round(wr_pct, 2),
                    "n": n,
                    "threshold_pct": WR_3D_THRESHOLD_PCT,
                    "window_days": window_days,
                }
            )
    return out


# ---------------------------------------------------------------------------
# Trigger 3: MDD breach
# ---------------------------------------------------------------------------


def compute_mdd_pct(picks: list[dict]) -> float:
    """Compute peak-to-trough drawdown on cumulative sum_pnl_pct.

    Returns the MDD as a positive percentage (e.g. 12.5 == 12.5pp drawdown).
    Picks should already be filtered by asset_class. Sorted internally by
    closed_at.
    """
    if not picks:
        return 0.0
    sortable = []
    for p in picks:
        ts = _parse_ts(p.get("closed_at") or p.get("timestamp"))
        if ts is None:
            continue
        try:
            pnl = float(p.get("pnl_pct") or 0.0)
        except (TypeError, ValueError):
            pnl = 0.0
        sortable.append((ts, pnl))
    if not sortable:
        return 0.0
    sortable.sort(key=lambda t: t[0])

    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for _, pnl in sortable:
        cum += pnl
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    return max_dd


def detect_mdd_breach(
    recent_closed: list[dict],
    *,
    asset_class: str,
    window_days: int,
    now: datetime,
) -> list[dict]:
    target = asset_class.upper()
    in_window = _filter_recent_by_class(
        recent_closed, target, timedelta(days=window_days), now=now
    )
    if not in_window:
        return []
    mdd = compute_mdd_pct(in_window)
    if mdd > MDD_THRESHOLD_PCT:
        return [
            {
                "trigger": "mdd_breach",
                "severity": "critical",
                "asset_class": target,
                "mdd_pct": round(mdd, 2),
                "threshold_pct": MDD_THRESHOLD_PCT,
                "window_days": window_days,
                "n": len(in_window),
            }
        ]
    return []


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check_rollback_conditions(
    asset_class: str = "CRYPTO",
    window_days: int = 3,
    *,
    dashboard_data_path: Path | None = None,
    active_picks_path: Path | None = None,
    whitelist_path: Path | None = None,
    now: datetime | None = None,
) -> list[dict]:
    """Return the list of triggered rollback conditions (no side effects)."""
    dashboard_data_path = dashboard_data_path or DEFAULT_DASHBOARD_DATA
    active_picks_path = active_picks_path or DEFAULT_ACTIVE_PICKS
    whitelist_path = whitelist_path or DEFAULT_WHITELIST
    now = now or datetime.now(timezone.utc)

    dashboard = _safe_load(Path(dashboard_data_path)) or {}
    picks_blob = dashboard.get("picks") or {}
    active = picks_blob.get("active") or []
    active_raw = picks_blob.get("active_raw") or []
    recent_closed = picks_blob.get("recent_closed") or []

    # active_picks.json is an optional supplemental source.
    extra_active = _safe_load(Path(active_picks_path))
    if isinstance(extra_active, list):
        active_raw = list(active_raw) + extra_active

    kill_set, auto_expired = _load_kill_state(Path(whitelist_path))

    triggers: list[dict] = []
    triggers.extend(
        detect_banned_id_emits(
            active, kill_set, auto_expired=auto_expired, bucket="active"
        )
    )
    triggers.extend(
        detect_banned_id_emits(
            active_raw, kill_set, auto_expired=auto_expired, bucket="active_raw"
        )
    )
    triggers.extend(
        detect_wr_breaches(recent_closed, window_days=window_days, now=now)
    )
    triggers.extend(
        detect_mdd_breach(
            recent_closed,
            asset_class=asset_class,
            window_days=window_days,
            now=now,
        )
    )
    return triggers


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli() -> int:
    triggers = check_rollback_conditions()
    if not triggers:
        print("no triggers")
        return 0
    print(json.dumps(triggers, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())
