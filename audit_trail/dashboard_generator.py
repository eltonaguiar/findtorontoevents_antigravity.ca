#!/usr/bin/env python3
"""
Unified Audit Dashboard Generator.
Reads ALL pick/trade/portfolio data sources and outputs a single JSON payload.

Usage:  python -m audit_trail.dashboard_generator

Sources:
  - 30+ JSON pick files (active + closed from all systems)
  - 16 SQLite databases (audit trail, paper trading, KIMI, etc.)
  - Portfolio JSONs and DB tables
  - Baby strategy bundles
  - Audit events and filter logs
"""

import glob
import json
import logging
import math
import os
import re
import sqlite3
import subprocess
import sys
import traceback
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

# Trade timeframe classification
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cross_aggregation.timeframe_classifier import classify_timeframe
from cross_aggregation.performance_alerts import check_all_alerts
try:
    from alpha_engine.risk_policy_loader import load_risk_policy
except Exception:  # pragma: no cover - optional import
    def load_risk_policy(*args, **kwargs):
        return {}

try:
    from alpha_engine.money_ready_verdict import money_ready_verdict as _money_ready_verdict
    _HAS_MONEY_READY = True
except Exception:  # pragma: no cover - optional import
    _HAS_MONEY_READY = False

try:
    from tools.pending_spa_scan import get_pending_spa_alerts as _get_pending_spa_alerts
    _HAS_PENDING_SPA = True
except Exception:  # pragma: no cover - optional import
    _HAS_PENDING_SPA = False

from audit_trail.pnl_ingest_sanity import clamp_pnl_pct_for_pick

# Cross-AI PR review (2026-04-28) HIGH cleanup item: the canonical
# BOND_SYMBOLS / ETF_SYMBOLS frozensets were being re-imported on every
# call to _derive_asset_class (via inline `from ... import` inside the
# function body — once for the bond-hard guard, once for the late
# ETF/BOND ranking block). Hoisting these to module top: the names are
# frozensets defined at alpha_engine/asset_class.py:27/31, safe to
# import once. Falls back to empty frozensets if alpha_engine is not
# installed (minimal install path) so the dashboard still builds.
try:
    from alpha_engine.asset_class import (
        BOND_SYMBOLS as _AC_BOND_SYMBOLS,
        ETF_SYMBOLS as _AC_ETF_SYMBOLS,
    )
except Exception as _ac_import_err:  # pragma: no cover - optional import
    # Per cross-AI review 2026-04-29: silent fall-through to empty
    # frozensets undoes #492's BOND/ETF precedence fix without warning.
    # Log loudly so a misconfigured install surfaces in CI logs.
    import logging as _logging
    _logging.getLogger(__name__).error(
        "alpha_engine.asset_class import failed (BOND/ETF precedence "
        "DISABLED — bond symbols will not route to BOND, ETFs to ETF): %r",
        _ac_import_err,
    )
    _AC_BOND_SYMBOLS = frozenset()
    _AC_ETF_SYMBOLS = frozenset()

# UEPS section renderer (server-side) — populates the #ueps-section-mount div
# in audit_dashboard/template.html with long_term_value + swing picks loaded
# from alpha_engine/data/active_picks.json. Optional: if the module is missing
# (e.g. minimal install) the dashboard still builds — the template's fallback
# "Building (n=0/100)" placeholder remains visible.
# See updates/long_term_value_project_2026-04-27/PROJECT.md
try:
    from audit_dashboard.ueps_section_renderer import render_ueps_section as _render_ueps_section
    _UEPS_RENDERER_AVAILABLE = True
except Exception:  # pragma: no cover - optional import
    _render_ueps_section = None
    _UEPS_RENDERER_AVAILABLE = False

# HF-grade statistical toolbox
try:
    from tools.hf_stats import compute_metrics as _hf_compute_metrics
    _HF_STATS_AVAILABLE = True
except ImportError:
    _HF_STATS_AVAILABLE = False
    def _hf_compute_metrics(*args, **kwargs):
        return {}

# Phase 2 of the Hedge-Fund-Uplift Roadmap (PR-B): per-strategy
# audit_metrics_block stamping. Default-OFF behind STAT_RIGOR_ENABLED env
# flag (14-day shadow per CLAUDE.md gate-change rule). Cherry-picked from
# alpha_engine.statistical_rigor (PR #626 foundation + PR #633 DSR add-on).
try:
    from alpha_engine.statistical_rigor import audit_metrics_block as _audit_metrics_block
    _STAT_RIGOR_AVAILABLE = True
except ImportError:
    _STAT_RIGOR_AVAILABLE = False
    def _audit_metrics_block(*args, **kwargs):
        return {}

# Direction conflict resolver — filters self-hedging LONG+SHORT pairs
try:
    from audit_trail.direction_conflict_resolver import filter_direction_conflicts
    _CONFLICT_RESOLVER_AVAILABLE = True
except ImportError:
    _CONFLICT_RESOLVER_AVAILABLE = False
    def filter_direction_conflicts(picks, strategy="trust_weighted"):
        return picks

# Charter §7 execution-cost model — converts gross pnl_pct to net (after
# round-trip slippage) for the asset-class verdict aggregate. See
# reports/crypto_edge_artifact_audit_2026_05_17.md (C2 / claim A4).
try:
    from alpha_engine.charter_slippage import deduct_slippage
except ImportError:
    def deduct_slippage(pnl_pct_gross, asset_class=None):  # type: ignore[misc]
        """Fallback: no-op if charter_slippage unavailable (PF stays gross)."""
        return pnl_pct_gross

# Quality gates for high-quality picks filtering
try:
    from audit_trail.quality_gates import (
        passes_active_gate,
        passes_smart_gate,
        calculate_smart_score,
        classify_pick_quality,
        get_pick_rationale,
        _compute_cross_asset_confluence,
        normalize_exit_reason,
        is_corrupted_outcome_row,
        ASSET_CLASS_SMART_THRESHOLDS,
        CRYPTO_MAX_AGE_HOURS,
        NON_CRYPTO_MAX_AGE_HOURS,
        COMMODITY_BLACKLIST,
        ETF_BLACKLIST,
        BLOCKED_SOURCE_SYSTEMS,
        COT_DEDUP_SYSTEMS,
    )

    _QUALITY_GATES_AVAILABLE = True
except ImportError as _qge:
    # CRITICAL: If quality_gates fails to import, we MUST NOT silently let
    # all picks through. The fallback implements the absolute minimum safety
    # checks so that corrupt / zero-score picks never reach the dashboard.
    logging.warning("quality_gates import failed: %s — using SAFE fallback", _qge)
    _QUALITY_GATES_AVAILABLE = False
    CRYPTO_MAX_AGE_HOURS = 168
    NON_CRYPTO_MAX_AGE_HOURS = 240
    ASSET_CLASS_SMART_THRESHOLDS = {}
    COMMODITY_BLACKLIST: frozenset = frozenset()  # type: ignore[assignment]
    ETF_BLACKLIST: frozenset = frozenset()  # type: ignore[assignment]
    BLOCKED_SOURCE_SYSTEMS: frozenset = frozenset()  # type: ignore[assignment]
    COT_DEDUP_SYSTEMS: frozenset = frozenset()  # type: ignore[assignment]
    is_corrupted_outcome_row = lambda p: False  # type: ignore[assignment]

    def passes_active_gate(p):
        """Safe fallback: reject null symbol, missing entry, score <= 0, closed status."""
        if not isinstance(p, dict):
            return False
        symbol = str(p.get("symbol", "") or "").strip()
        if not symbol:
            return False
        status = str(p.get("status", "") or "").upper().strip()
        if status and status not in {"OPEN", "ACTIVE", "PENDING", "LIVE", ""}:
            return False
        entry = float(p.get("entry_price", 0) or 0)
        if entry <= 0:
            return False
        score = float(p.get("score", 0) or 0)
        if score <= 0:
            return False
        return True

    def passes_smart_gate(p):
        return False

    def calculate_smart_score(p):
        return 0

    def classify_pick_quality(p):
        return "ACTIVE"

    def _compute_cross_asset_confluence(all_picks):  # type: ignore
        return {}

    def get_pick_rationale(p):
        return {}

    def normalize_exit_reason(p):  # type: ignore
        return str(p.get("exit_reason") or "UNKNOWN")


# Optional ML feature persistence and edge analytics.
# Keep this soft-fail so dashboard generation never hard-breaks on analytics code.
try:
    from audit_trail.pick_feature_store import run_sqlite_migration, store_pick_features
    from audit_trail.feature_edge_analyzer import (
        run_full_analysis,
        get_feature_edge_summary,
        get_top_feature_edges,
    )
    from audit_trail.symbol_strategy_tracker import (
        rebuild_from_closed_picks,
        get_symbol_strategy_summary,
        get_edge_picks,
    )

    _EDGE_TRACKING_AVAILABLE = True
except Exception:
    _EDGE_TRACKING_AVAILABLE = False


ROOT = Path(__file__).resolve().parent.parent
_GHOST_SYSTEMS: set[str] = set()
LOCK_FILE = ROOT / "audit_trail" / "data" / ".generator.lock"
MAX_CLOSED_PICKS = 3500  # v105: bumped to accommodate 365-day audit
RESERVED_TRACK_RECORD_CLOSED_PICKS = 500
RESERVED_NON_CRYPTO_CLOSED_PICKS = 2000  # Guarantee non-crypto picks survive the cap
PAYLOAD_SIZE_WARN_KB = 4096  # Warn if payload exceeds 4MB

# v101: Strip heavy fields from closed picks to reduce payload size
_CLOSED_PICK_KEEP_FIELDS = {
    "symbol", "direction", "strategy", "entry_price", "exit_price", "close_price", "take_profit",
    "stop_loss", "pnl_pct", "net_pnl_pct", "score", "timestamp", "closed_at",
    "exit_reason", "status", "source_system", "asset_class", "category", "confidence",
    "trust_score", "trust_tier", "trade_timeframe", "timeframe", "id",
    "elite_score", "elite_grade", "grade", "forward_wr", "forward_trades",
    "strat_fwd_wr", "strat_fwd_pf", "strat_fwd_trades", "track_record",
    "strong", "wf_verdict", "wf_p_value", "age_hours", "rr_ratio",
    "_direction_conflict", "has_conflict",
    "tv_edge_score", "tv_edge_bonus", "tv_edge_meta",
    "exit_reason_raw",
    # ── At-issue snapshot fields: values at time pick was issued ──
    "at_issue_strat_fwd_wr", "at_issue_strat_fwd_trades",
    "at_issue_trust_score", "at_issue_trust_tier",
    # ── At-issue feed-membership fields (2026-04-20 effectiveness audit
    #    recommendation #2). Retained on closed picks so Smart Picks / HC /
    #    Verified Alpha / Track% cohorts can be audited retroactively. Also
    #    pulls in ml_score (predictive feature) and entry_time (staleness
    #    detection), both flagged as 0% populated by the additional-fixes
    #    survey. ──
    "ml_score", "hf_conviction_tier", "va_cohort_id",
    "sym_track_wr", "sym_track_wr_pit", "sym_track_total_pit", "paper_trade", "entry_time",
    "is_smart_pick", "is_verified_alpha", "hc_tier",
    "smart_score_v2_shadow",
    # B17 (2026-05-02): after-cost reality fields from forward-edge-audit
    "after_cost_net_per_trade", "wilson_lb_wr", "is_ac_survivor",
    # 2026-05-08: preserve pick_type + holding_horizon so concept_registry
    # can tag UEPS picks as long_term_value (was dropped → 38 picks tagged
    # "standard" instead of "long_term_value", breaking LONG_TERM filter).
    "pick_type", "holding_horizon",
}


def _slim_closed_pick(pick: dict) -> dict:
    """Strip heavy fields from closed picks to reduce payload size."""
    slim = {k: v for k, v in pick.items() if k in _CLOSED_PICK_KEEP_FIELDS}
    # Truncate reason if present
    reason = pick.get("reason", "")
    if reason and len(str(reason)) > 120:
        slim["reason"] = str(reason)[:120]
    elif reason:
        slim["reason"] = reason
    return slim


def _snapshot_at_issue_for_recent_closed(
    recent_closed: list[dict], *, pre_leaderboard: bool
) -> None:
    """Populate at_issue_* on published closed rows for dashboard delta columns.

    * ``pre_leaderboard=True``: run immediately before the leaderboard merge loop
      copies ``strat_fwd_*`` / ``forward_*`` and any existing trust fields from the
      raw row so post-merge values can be compared to pre-merge.
    * ``pre_leaderboard=False``: run after that loop, immediately before
      ``enrich_picks_with_trust_score(recent_closed)``, to capture ``trust_tier`` /
      ``trust_score`` when they were still missing from the first snapshot.

    See ``updates/2026-04-15-audit-trust-edge-lev-tooltips-closed-snapshot.md``.
    """
    for pick in recent_closed or []:
        if not isinstance(pick, dict):
            continue
        if pre_leaderboard:
            if pick.get("at_issue_strat_fwd_wr") is None:
                v = pick.get("strat_fwd_wr")
                if v is None:
                    v = pick.get("forward_wr")
                if v is not None:
                    pick["at_issue_strat_fwd_wr"] = v
            if pick.get("at_issue_strat_fwd_trades") is None:
                v = pick.get("strat_fwd_trades")
                if v is None:
                    v = pick.get("forward_trades")
                if v is not None:
                    pick["at_issue_strat_fwd_trades"] = int(v)
            if pick.get("at_issue_trust_score") is None and pick.get(
                "trust_score"
            ) is not None:
                pick["at_issue_trust_score"] = pick["trust_score"]
            tt = pick.get("trust_tier")
            if pick.get("at_issue_trust_tier") is None and tt:
                pick["at_issue_trust_tier"] = str(tt).strip()
        else:
            tt = pick.get("trust_tier")
            if pick.get("at_issue_trust_tier") is None and tt:
                pick["at_issue_trust_tier"] = str(tt).strip()
            if pick.get("at_issue_trust_score") is None and pick.get(
                "trust_score"
            ) is not None:
                pick["at_issue_trust_score"] = pick["trust_score"]


UNIVERSAL_RESOLVER_MAX_AGE_MINUTES = 30
UNIVERSAL_RESOLVER_WATCH_FILES = (
    "predictions/data/active_predictions.json",
    "rapid_fire_data/active_picks.json",
    "quan_engine/data/active_signals.json",
)


def _sanitize_for_json(obj):
    """Recursively replace `inf`/`-inf`/`nan` with `None` for strict-JSON output.

    JSON spec does NOT allow ``Infinity`` / ``-Infinity`` / ``NaN`` literals, but
    Python's default ``json.dumps`` emits them anyway (``allow_nan=True`` default).
    Browsers' ``JSON.parse()`` rejects the entire payload on the first such literal,
    which is exactly what broke ``findtorontoevents.ca/audit`` on 2026-04-27 — the
    external data fetch failed with ``Unexpected token 'I', "..._factor": Infinity}"``
    and the dashboard rendered "No data loaded".

    Source: ``profit_factor = gross_wins / gross_losses`` produces ``inf`` when a
    cohort has zero losses (e.g. a strategy with all wins). This helper walks the
    payload before ``json.dumps`` and replaces those values with ``None`` so the
    JSON validates and the dashboard renders.

    Apply to ``payload`` immediately before any ``json.dumps`` call that writes a
    user-visible artifact (external dashboard_data.json, embedded HTML payload).
    """
    import math as _math
    if isinstance(obj, float):
        if _math.isnan(obj) or _math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, tuple):
        return [_sanitize_for_json(v) for v in obj]
    return obj


def _write_text_file(path: Path, text: str) -> None:
    """Atomic text write — writes to temp file in same directory, then os.replace.

    2026-04-17 (per dashboard_payload_health + low_score_tracker failure reports):
    concurrent readers were hitting JSONDecodeError mid-write on the 25MB payload
    file. Switch to temp-file + os.replace for cross-process safety. Same pattern
    as alpha_engine/atomic_json.atomic_write_json (which we don't import directly
    here to avoid a circular: dashboard_generator is imported by many paths).
    """
    import os as _os
    import tempfile as _tempfile
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tempfile.NamedTemporaryFile(
        mode="w", dir=str(path.parent), prefix=path.name + ".",
        suffix=".tmp", delete=False, encoding="utf-8", newline="\n",
    )
    try:
        tmp.write(text)
        tmp.flush()
        try:
            _os.fsync(tmp.fileno())
        except OSError:
            pass  # not fatal on some filesystems
        tmp.close()
        _os.replace(tmp.name, path)
    except Exception:
        try:
            tmp.close()
        except Exception:
            pass
        try:
            _os.unlink(tmp.name)
        except OSError:
            pass
        raise


def _git_head_meta(repo_root: Path) -> tuple[str | None, str | None, str | None]:
    """Return (sha, commit_iso_utc, error). Never raises."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True
        ).strip()
        ts = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI"], cwd=str(repo_root), text=True
        ).strip()
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return sha, dt.astimezone(timezone.utc).isoformat(), None
    except Exception as e:  # pragma: no cover - non-fatal metadata path
        return None, None, str(e)


def _compute_payload_lag_seconds(generated_at_iso: str, commit_iso: str | None) -> float | None:
    if not generated_at_iso or not commit_iso:
        return None
    try:
        g = datetime.fromisoformat(str(generated_at_iso).replace("Z", "+00:00"))
        c = datetime.fromisoformat(str(commit_iso).replace("Z", "+00:00"))
        if g.tzinfo is None:
            g = g.replace(tzinfo=timezone.utc)
        if c.tzinfo is None:
            c = c.replace(tzinfo=timezone.utc)
        return (g.astimezone(timezone.utc) - c.astimezone(timezone.utc)).total_seconds()
    except Exception:
        return None


def _pick_pnl_pct(pick: dict) -> float | None:
    """Best-effort extraction of pnl% for active/closed picks."""
    for k in ("pnl_pct", "unrealized_pnl_pct", "realized_pnl_pct"):
        v = pick.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    entry = pick.get("entry_price") or pick.get("entry")
    live = pick.get("current_price") or pick.get("last_price") or pick.get("live")
    try:
        e = float(entry)
        l = float(live)
    except (TypeError, ValueError):
        return None
    if e <= 0:
        return None
    return ((l - e) / e) * 100.0


def _summarize_big_movers(active: list[dict], closed: list[dict], threshold_pct: float = 3.0) -> dict:
    def _collect(rows: list[dict], cohort: str) -> list[dict]:
        out = []
        for p in rows:
            if not isinstance(p, dict):
                continue
            pnl = _pick_pnl_pct(p)
            if pnl is None or abs(pnl) < threshold_pct:
                continue
            out.append(
                {
                    "symbol": str(p.get("symbol") or ""),
                    "asset_class": _coerce_asset_class(p),
                    "strategy": str(p.get("strategy") or p.get("source_system") or "unknown").lower(),
                    "system": str(p.get("source_system") or p.get("system") or "unknown").lower(),
                    "pnl_pct": round(float(pnl), 4),
                    "cohort": cohort,
                }
            )
        return out

    records = _collect(active, "active") + _collect(closed, "closed")
    winners = [r for r in records if r["pnl_pct"] > 0]
    losers = [r for r in records if r["pnl_pct"] < 0]

    def _rollup(rows: list[dict], key: str) -> dict:
        bucket = defaultdict(lambda: {"count": 0, "avg_pnl_pct": 0.0})
        for r in rows:
            b = bucket[str(r.get(key) or "unknown")]
            b["count"] += 1
            b["avg_pnl_pct"] += float(r["pnl_pct"])
        out = {}
        for name, agg in bucket.items():
            count = int(agg["count"])
            out[name] = {
                "count": count,
                "avg_pnl_pct": round(float(agg["avg_pnl_pct"]) / max(1, count), 4),
            }
        return out

    winners.sort(key=lambda x: x["pnl_pct"], reverse=True)
    losers.sort(key=lambda x: x["pnl_pct"])
    return {
        "threshold_pct": threshold_pct,
        "total_movers": len(records),
        "winners": len(winners),
        "losers": len(losers),
        "top_winners": winners[:25],
        "top_losers": losers[:25],
        "winners_by_strategy": _rollup(winners, "strategy"),
        "losers_by_strategy": _rollup(losers, "strategy"),
        "winners_by_system": _rollup(winners, "system"),
        "losers_by_system": _rollup(losers, "system"),
        "winners_by_asset_class": _rollup(winners, "asset_class"),
        "losers_by_asset_class": _rollup(losers, "asset_class"),
    }


def _concentration_summary_from_active(active: list[dict]) -> dict:
    total = len(active)
    if total <= 0:
        return {
            "total_active": 0,
            "top_symbol_share_pct": 0.0,
            "top_strategy_share_pct": 0.0,
            "top_system_share_pct": 0.0,
        }

    by_symbol = defaultdict(int)
    by_strategy = defaultdict(int)
    by_system = defaultdict(int)
    for p in active:
        if not isinstance(p, dict):
            continue
        by_symbol[str(p.get("symbol") or "").upper()] += 1
        by_strategy[str(p.get("strategy") or p.get("source_system") or "unknown").lower()] += 1
        by_system[str(p.get("source_system") or p.get("system") or "unknown").lower()] += 1

    def _top_share(bucket: dict) -> tuple[str, int, float]:
        if not bucket:
            return "", 0, 0.0
        name, count = max(bucket.items(), key=lambda x: x[1])
        return str(name), int(count), round((float(count) / max(1, total)) * 100.0, 2)

    sym_name, sym_count, sym_share = _top_share(by_symbol)
    strat_name, strat_count, strat_share = _top_share(by_strategy)
    sys_name, sys_count, sys_share = _top_share(by_system)
    return {
        "total_active": total,
        "top_symbol": {"name": sym_name, "count": sym_count, "share_pct": sym_share},
        "top_strategy": {"name": strat_name, "count": strat_count, "share_pct": strat_share},
        "top_system": {"name": sys_name, "count": sys_count, "share_pct": sys_share},
    }


def _probation_quarantine_summary(smart_picks_feed: dict) -> dict:
    picks = smart_picks_feed.get("picks") if isinstance(smart_picks_feed, dict) else []
    picks = picks if isinstance(picks, list) else []
    excluded = smart_picks_feed.get("excluded_reasons") if isinstance(smart_picks_feed, dict) else {}
    excluded = excluded if isinstance(excluded, dict) else {}
    control = smart_picks_feed.get("concentration_probation_stats") if isinstance(smart_picks_feed, dict) else {}
    control = control if isinstance(control, dict) else {}

    quarantine_counts = defaultdict(int)
    probation_count = 0
    for p in picks:
        if not isinstance(p, dict):
            continue
        q = str(p.get("quarantine") or "").strip().lower()
        if q:
            quarantine_counts[q] += 1
        if p.get("probation_flag"):
            probation_count += 1

    total_picks = len([p for p in picks if isinstance(p, dict)])
    return {
        "total_smart_picks": total_picks,
        "quarantine_counts": dict(quarantine_counts),
        "probation_tagged_in_output": probation_count,
        "probation_filtered_count": int(excluded.get("probation_concentration", 0) or 0),
        "non_crypto_probation_filtered": int(excluded.get("non_crypto_probation", 0) or 0),
        "concentration_controls": control,
    }

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("audit_dashboard")

# ── Trust registry for conflict resolution ──
try:
    from cross_aggregation.system_trust_registry import (
        get_tier,
        get_vote_weight,
        resolve_conflict,
        normalize_system_name,
    )

    _TRUST_AVAILABLE = True
except ImportError:
    _TRUST_AVAILABLE = False

    def get_tier(s):
        return "WATCH"

    def get_vote_weight(s):
        return 1.0

    def resolve_conflict(l, s):
        return ("CONTESTED", "Trust registry unavailable", 0.0)

    def normalize_system_name(s):
        return s


_EQUITY_SYMBOLS = {
    "SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "AMD", "NFLX",
    "DIS", "BA", "JPM", "GS", "V", "MA", "PYPL", "SQ", "COIN", "MSTR", "RIOT", "MARA", "HUT", "BITF",
    "IWM", "DIA", "VTI", "VOO", "ARKK", "XLF", "XLE", "XLK", "GLD", "SLV", "USO", "TLT", "VIX",
    "UVXY", "SQQQ", "TQQQ", "INTC", "CSCO", "ORCL", "ADBE", "CRM", "SAP", "ASML", "AVGO", "TXN",
    "QCOM", "MU", "AMAT", "LRCX", "ADI", "KLAC", "SNPS", "CDNS", "MRVL", "NXPI", "MCHP", "ON",
    "TER", "ENTP", "SMH", "SOXX", "XBI", "KRE", "GDX", "GDXJ", "TLT", "SHV", "IEI", "IEF", "TLH",
    "BIL", "VGK", "EWJ", "EEM", "EFA", "VWO", "IYW", "IYT", "IBB", "XOP", "XRT", "XME", "XHB",
    "XLP", "XLV", "XLY", "XLU", "XLB", "XLI", "VGT", "VFH", "VNQ", "VNQI", "SCHD", "VYM", "DGRO",
    "IBM", "ORCL", "CSCO", "INTC", "QCOM", "TXN", "MU", "AMD", "ADI", "LRCX", "AMAT", "KLAC",
    "SNPS", "CDNS", "PANW", "FTNT", "CRWD", "DDOG", "NET", "SNOW", "PLTR", "ZS", "OKTA", "NET",
    "SHOP", "SQ", "U", "TWLO", "DOCU", "ZM", "PYPL", "V", "MA", "AXP", "DFS", "COF", "JPM",
    "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "TROW", "KRE", "KBE", "XLF", "XLI", "XLY",
    "CAT", "DE", "HON", "GE", "UPS", "FDX", "MMM", "LMT", "RTX", "NOC", "GD", "BA", "JNJ",
    "UNH", "PFE", "ABBV", "BMY", "MRK", "MRNA", "AMGEN", "GILD", "VRTX", "ISRG", "TMO", "DHR",
    "ABT", "MDT", "SYK", "STR", "ZTS", "PG", "KO", "PEP", "COST", "WMT", "TGT", "PM", "MO",
    "MDLZ", "CL", "KMB", "HSY", "STZ", "XLP", "XLU", "XLE", "XOP", "XME", "FCX", "NEM", "GOLD",
    "EUG", "OXY", "CVX", "XOM", "COP", "SLB", "HAL", "MPC", "PSX", "VLO",
    "SOFI", "NIO", "AMC", "GME", "RIVN", "LCID", "GRAB", "SE", "BABA", "JD", "PDD", "LI", "XPEV",
}


def _normalize_symbol(sym: str) -> str:
    """Normalize symbol strings so BTC-USD, BTCUSD, BTCUSDT all become BTCUSDT.

    Handles:
      - Crypto: BTC-USD → BTCUSDT, BTC/USD → BTCUSDT, BTC-USDT → BTCUSDT
      - Equity: SPY, QQQ, AAPL stay as-is (no suffix mangling)
      - Forex: EURUSD=X → EURUSD, GBPJPY=X → GBPJPY
      - Stablecoins: BTCBUSD stays BTCBUSD, ETHUSDC stays ETHUSDC
    """
    if not sym:
        return sym
    s = sym.strip().upper()
    if not s:
        return s

    # Strip Yahoo Finance suffix (=X for forex)
    if s.endswith("=X"):
        s = s[:-2]

    # Remove separators
    s = s.replace("-", "").replace("_", "").replace("/", "")

    # Known equity/index symbols — don't append crypto suffixes
    if s in _EQUITY_SYMBOLS:
        return s

    # Known forex pairs (6 chars, no crypto suffix) — don't append USDT
    _FOREX_BASES = {
        "EUR",
        "GBP",
        "JPY",
        "AUD",
        "NZD",
        "CAD",
        "CHF",
        "SGD",
        "HKD",
        "NOK",
        "SEK",
        "DKK",
        "ZAR",
        "MXN",
        "TRY",
        "CNY",
        "CNH",
        "INR",
    }
    if len(s) == 6:
        base, quote = s[:3], s[3:]
        if base in _FOREX_BASES or quote in _FOREX_BASES:
            # It's a forex pair like EURUSD, GBPJPY — keep as-is
            if (
                base == "USD"
                or quote == "USD"
                or (base in _FOREX_BASES and quote in _FOREX_BASES)
            ):
                return s

    # Crypto normalization: ensure consistent suffix
    # If ends with USD but not USDT, append T (BTC-USD → BTCUSD → BTCUSDT)
    if s.endswith("USD") and not s.endswith("USDT") and not s.endswith("BUSD"):
        s += "T"

    return s


# Multi-asset / UI labels that map to canonical survivor leaderboard keys
_STRATEGY_BT_ALIAS_TO_CANONICAL: dict[str, str] = {
    "multi_asset_futures_connors_rsi2": "connors_rsi2",
}



# ── ML strategy grouping ──
# ML sub-strategies like "ml_enhanced_BTCUSDT_1h_B_lightgbm" have only 1-2 trades
# each, making individual forward stats meaningless. We group them into
# "ml_enhanced_group" (and similar) so picks inherit meaningful aggregate stats.
_ML_GROUP_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^ml_enhanced_", re.IGNORECASE), "ml_enhanced_group"),
    (re.compile(r"^ml_crypto_predictor", re.IGNORECASE), "ml_crypto_predictor_group"),
]


def _ml_group_name(strategy: str) -> str | None:
    """Return the ML group name for an ML sub-strategy, or None if not an ML strat.

    E.g. "ml_enhanced_BTCUSDT_1h_B_lightgbm" -> "ml_enhanced_group".
    """
    if not strategy:
        return None
    for pat, group in _ML_GROUP_PATTERNS:
        if pat.match(strategy):
            return group
    return None


def _normalize_strategy_tooltip_key(name: str) -> str:
    """Match audit_dashboard/template.html normalizeStrategyName (collapse _- and space)."""
    if not name:
        return ""
    return re.sub(r"[_\-\s]+", "", name.lower()).strip()


def _leaderboard_name_candidates_for_pick(pick: dict, strat_name: str) -> list[str]:
    """Ordered keys to resolve collect_strategy_leaderboard rows (display label vs id prefix)."""
    out: list[str] = []
    seen: set[str] = set()

    def add(x: str) -> None:
        x = (x or "").strip()
        if not x or x in seen:
            return
        seen.add(x)
        out.append(x)

    add(strat_name)
    pid = str(pick.get("id") or "")
    if "::" in pid:
        prefix = pid.split("::", 1)[0].strip()
        if prefix and re.match(r"^[A-Za-z][A-Za-z0-9_]*$", prefix):
            add(prefix)
    for key in list(out):
        alias = _STRATEGY_BT_ALIAS_TO_CANONICAL.get(key)
        if alias:
            add(alias)
    # ML group fallback: if strategy is an ML sub-strategy,
    # also try the ML group name (e.g. "ml_enhanced_group")
    ml_group = _ml_group_name(strat_name)
    if ml_group:
        add(ml_group)

    return out


def _resolve_leaderboard_row(strat_lookup: dict, pick: dict, strat_name: str) -> dict:
    for cand in _leaderboard_name_candidates_for_pick(pick, strat_name):
        row = strat_lookup.get(cand)
        if row:
            return row
        nk = _normalize_strategy_tooltip_key(cand)
        if nk:
            row = strat_lookup.get(nk)
            if row:
                return row
    return {}


_OPEN_ACTIVE_STATUSES = {"", "OPEN", "ACTIVE", "PENDING", "LIVE"}


def _is_active_pick(pick: dict) -> bool:
    status = str(pick.get("status", "") or "").upper().strip()
    return status in _OPEN_ACTIVE_STATUSES


def _has_tradeable_entry(pick: dict) -> bool:
    entry = _float(pick.get("entry_price", 0))
    return entry > 0


def _extract_freshness_timestamp_str(pick: dict) -> str:
    """Best-effort timestamp for staleness; aligns with quality_gates age fields."""
    if not isinstance(pick, dict):
        return ""
    for key in (
        "timestamp",
        "entry_time",
        "created_at",
        "generated_at",
        "entry_time_est",
        "signal_time",
        "opened_at",
        "entryDate",
    ):
        v = pick.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _parse_pick_timestamp_utc(ts_raw: str):
    """Return aware UTC datetime or None."""
    if not ts_raw or not str(ts_raw).strip():
        return None
    _tz_map = {
        "EST": "-05:00",
        "EDT": "-04:00",
        "CST": "-06:00",
        "CDT": "-05:00",
        "PST": "-08:00",
        "PDT": "-07:00",
        "UTC": "+00:00",
    }
    try:
        ts_clean = ts_raw.strip()
        for abbr, offset in _tz_map.items():
            if ts_clean.endswith(" " + abbr):
                ts_clean = ts_clean[: -len(abbr) - 1].strip() + offset
                break
        ts_clean = ts_clean.replace("Z", "+00:00")
        if "+" not in ts_clean and "-" not in ts_clean[10:] and len(ts_clean) >= 19:
            ts_clean += "+00:00"
        if " " in ts_clean and "T" not in ts_clean:
            ts_clean = ts_clean.replace(" ", "T")
            if "+" not in ts_clean and "-" not in ts_clean[10:]:
                ts_clean += "+00:00"
        pick_time = datetime.fromisoformat(ts_clean)
        if pick_time.tzinfo is None:
            pick_time = pick_time.replace(tzinfo=timezone.utc)
        return pick_time
    except (ValueError, TypeError, IndexError):
        return None


_HARD_BLOCKED_TRUST_TIERS = {"BANNED", "AVOID"}
_HARD_BLOCKED_TRUST_LABELS = {"BANNED", "AVOID"}


def _is_pre_score_active_candidate(pick: dict) -> bool:
    """Keep scorable active candidates alive until score-based gates can run.

    passes_active_gate() enforces final score floors, so calling it before
    elite scoring/score_booster collapses the active book prematurely.
    Trust-tier/label BANNED/AVOID picks are hard-blocked here regardless of
    score stage — trust is system-level metadata, not pick-derived.
    """
    trust_tier = str(pick.get("trust_tier", "") or "").strip().upper()
    trust_label = str(pick.get("trust_label", "") or "").strip().upper()
    if trust_tier in _HARD_BLOCKED_TRUST_TIERS or trust_label in _HARD_BLOCKED_TRUST_LABELS:
        return False
    strategy = str(pick.get("strategy", "") or "").strip().lower()
    return bool(strategy) and strategy not in {"", "none", "null", "unknown"}


def _extract_normalized_source_scores(raw: dict, source_system: str) -> dict:
    """Preserve upstream scoring metadata without mistaking probabilities for scores."""
    source_key = str(source_system or "").lower()

    def _rounded_positive(value, digits: int = 2):
        parsed = _float(value)
        return round(parsed, digits) if parsed > 0 else None

    ml_composite_score = _rounded_positive(raw.get("ml_composite_score"), 1)
    elite_score = _rounded_positive(raw.get("elite_score"), 1)
    method_a_score = _rounded_positive(raw.get("method_a_score"), 1)

    # Some feeds use `score` for a 0-100 display score, others use it as a 0-1
    # probability. Only preserve obviously score-scaled values here.
    raw_score_val = _float(raw.get("score"))
    score = None
    for candidate in (ml_composite_score, elite_score, method_a_score):
        if candidate is not None:
            score = candidate
            break
    if score is None and raw_score_val >= 10:
        score = round(raw_score_val, 1)

    # KIMI emits integer confluence scores (50/65/etc.), while other systems use
    # low decimal multipliers. Only lift the KIMI-style integer scores.
    confluence_score = _rounded_positive(raw.get("confluence_score"), 1)
    if (
        score is None
        and source_key in {"kimi_riseoftheclaw", "riseoftheclaw", "kimi_live_signals"}
        and confluence_score is not None
        and confluence_score >= 10
    ):
        score = confluence_score

    source_grade = (
        raw.get("grade")
        or raw.get("ml_composite_grade")
        or raw.get("elite_grade")
        or raw.get("method_a_grade")
    )

    return {
        "score": score,
        "elite_score": elite_score,
        "ml_score": _rounded_positive(raw.get("ml_score"), 4),
        "ml_composite_score": ml_composite_score,
        "method_a_score": method_a_score,
        "precursor_score": _rounded_positive(raw.get("precursor_score"), 1),
        "confluence_score": confluence_score,
        "safety_score": _rounded_positive(raw.get("safety_score"), 1),
        "elite_grade": str(source_grade) if source_grade else None,
        "grade": str(source_grade) if source_grade else None,
        "trust_label": raw.get("trust_label") or raw.get("trust_level"),
        "trust_tier": raw.get("trust_tier"),
        "_source_score_breakdown": raw.get("ml_composite_breakdown")
        or raw.get("elite_breakdown"),
    }


# ── External Source Quality Gates ──
# These gates apply to picks from external sources (contrarian_consensus, tsmom, genome, etc.)
# that bypass the production_scanner pipeline. They ensure basic quality standards.

# External sources that bypass production_scanner (from HANDOFF_OPUS_SESSION.MD)
_EXTERNAL_SOURCES = {
    "contrarian_consensus",
    "contrarian",
    "tsmom",
    "genome",
    "genetic_programmer",
    "audit_ensemble",
    "mape_evolver",
    "ensemble_evolver",
    "neat_neural",
    "hyperparam_dna",
    "failure_evolver",
    "momentum_evolver",
    "multitf_evolver",
    "contrarian_evolver",
    "macd_dna_mutations",
    "mutation_lab",
    "short_engine",
}

# R:R floor — below this we tag _low_rr but don't hard-block
_EXTERNAL_RR_FLOOR = 0.8
# Stale threshold — picks older than this get _stale tag + score penalty
_EXTERNAL_STALE_DAYS = 7
_EXTERNAL_STALE_SCORE_PENALTY = 30

# Lazy-loaded kill list from core_whitelist.json (populated on first call)
_ext_kill_set_cache = None


def _load_external_kill_set():
    """Load kill list from core_whitelist.json, cache for reuse.

    Auto-expiry safety valve (added 2026-04-29 per
    reports/EDGE_DELIVERY_INVESTIGATION_2026_04_29.md): if
    metadata.last_kill_run is older than metadata.kill_list_max_age_days
    (default 21d), the entire kill_list is treated as expired and ignored,
    with a single warning log. This prevents a stale kill_list from
    silently blocking strategies that have re-developed edge after the last
    kill run. Re-running tools/strategy_killer.py refreshes last_kill_run.
    """
    global _ext_kill_set_cache
    if _ext_kill_set_cache is not None:
        return _ext_kill_set_cache
    _ext_kill_set_cache = set()
    try:
        kl_path = (
            Path(__file__).resolve().parent.parent
            / "alpha_engine"
            / "data"
            / "core_whitelist.json"
        )
        if kl_path.exists():
            kl_data = json.loads(kl_path.read_text(encoding="utf-8", errors="replace"))
            metadata = kl_data.get("metadata", {}) or {}
            max_age_days = metadata.get("kill_list_max_age_days", 21)
            last_kill_run = metadata.get("last_kill_run")
            kill_list_expired = False
            if last_kill_run:
                try:
                    from datetime import datetime, timezone
                    # Parse ISO-format timestamp; tolerate timezone variants
                    ts = last_kill_run.replace("Z", "+00:00")
                    last_run_dt = datetime.fromisoformat(ts)
                    if last_run_dt.tzinfo is None:
                        last_run_dt = last_run_dt.replace(tzinfo=timezone.utc)
                    age_days = (datetime.now(timezone.utc) - last_run_dt).total_seconds() / 86400.0
                    if age_days > max_age_days:
                        kill_list_expired = True
                        log.warning(
                            "[DASHBOARD GATE] kill_list is %.1fd stale (>%dd max_age); "
                            "treating as EXPIRED and unblocking all strategies. "
                            "Re-run tools/strategy_killer.py to refresh.",
                            age_days, max_age_days,
                        )
                except (ValueError, TypeError, ImportError) as e:
                    log.warning("[DASHBOARD GATE] could not parse last_kill_run=%r: %s", last_kill_run, e)
            if not kill_list_expired:
                core_strats = {s.lower() for s in kl_data.get("core_strategies", [])}
                for s in kl_data.get("kill_list", []):
                    _ext_kill_set_cache.add(s.lower())
                    # Also add the bare name after :: prefix, unless it's a core strategy
                    if "::" in s:
                        bare = s.split("::", 1)[1].lower()
                        if bare not in core_strats:
                            _ext_kill_set_cache.add(bare)
    except Exception as e:
        log.warning("[DASHBOARD GATE] Failed to load kill list: %s", e)
    return _ext_kill_set_cache


def _apply_external_source_gate(pick: dict, source_system: str):
    """
    Lightweight quality gate for external source picks that bypass production_scanner.

    Instead of hard-blocking on R:R / staleness, this gate:
      - Removes picks from killed strategies (returns "killed")
      - Tags _low_rr if R:R > 0 but < 0.8
      - Normalizes confidence (>1.0 divide by 100, cap at 0.95)
      - Tags _stale and reduces score by 30 if age > 7 days

    Returns: (action, reason)
      action = "pass" | "killed" | "tagged"
      reason = human-readable explanation
    """
    # Only apply to known external sources
    if source_system not in _EXTERNAL_SOURCES:
        return "pass", "not external source"

    tags = []

    # 1. Kill list filter — load from core_whitelist.json
    kill_set = _load_external_kill_set()
    strategy = str(pick.get("strategy", "") or "").lower()
    # Strip :: prefix for matching (e.g. "aggregated_picks::foo" -> "foo")
    bare_strategy = strategy.split("::")[-1] if "::" in strategy else strategy
    if strategy in kill_set or bare_strategy in kill_set:
        return "killed", f"strategy '{pick.get('strategy')}' in kill list"

    # 2. Confidence normalization — before any confidence-based checks
    conf = _float(pick.get("confidence", 0))
    if conf > 1.0:
        conf = conf / 100.0
    conf = min(conf, 0.95)
    pick["confidence"] = round(conf, 4)

    # 3. R:R floor — tag but don't hard-block
    rr = _float(pick.get("rr_ratio", 0))
    if rr <= 0:
        # Compute from entry/tp/sl if rr_ratio not set
        entry = _float(pick.get("entry_price", 0))
        tp = _float(pick.get("take_profit", 0))
        sl = _float(pick.get("stop_loss", 0))
        if entry > 0 and tp > 0 and sl > 0 and abs(entry - sl) > 0:
            rr = abs(tp - entry) / abs(entry - sl)
    # Cap R:R at 10 — values above indicate SL too close to entry (data quality issue)
    if rr > 10.0:
        rr = 10.0
        pick["rr_ratio"] = 10.0
    if 0 < rr < _EXTERNAL_RR_FLOOR:
        pick["_low_rr"] = True
        tags.append(f"low_rr={rr:.2f}")

    # 4. Stale pick filter — age > 7 days
    age_hours = pick.get("age_hours")
    if age_hours is not None and age_hours > _EXTERNAL_STALE_DAYS * 24:
        pick["_stale"] = True
        # Reduce score by penalty (score may be set later; store penalty for downstream)
        existing_score = _float(pick.get("score", 0))
        if existing_score > 0:
            pick["score"] = max(0, existing_score - _EXTERNAL_STALE_SCORE_PENALTY)
        pick["_stale_penalty"] = _EXTERNAL_STALE_SCORE_PENALTY
        tags.append(f"stale={age_hours:.0f}h")

    if tags:
        return "tagged", ", ".join(tags)
    return "pass", "all checks passed"


# ── Live price enrichment for active picks ──
def _fetch_prices_with_failover(crypto_symbols: set) -> dict:
    """Fetch prices from multiple APIs with failover. Returns {SYMBOL: price}.

    Strategy: try Binance first (all endpoints), then fill remaining gaps with
    CoinGecko.  Never return early after partial results — always attempt to
    fill every requested symbol.
    """
    prices = {}

    # ── k-prefix / 1000-prefix mapping ──
    # Some systems emit kPEPEUSDT (= PEPEUSDT * 1000) or 1000SHIBUSDT.
    # Binance lists 1000PEPEUSDT, 1000SHIBUSDT, 1000FLOKIUSDT natively.
    _K_PREFIX_MAP = {}  # kPEPEUSDT -> PEPEUSDT  (multiply by 1000 later)
    _1000_PREFIX_MAP = {}  # 1000SHIBUSDT -> SHIBUSDT (divide by 1000 later)
    _binance_syms = set()  # what we actually request from Binance

    for sym in crypto_symbols:
        if (
            sym.startswith("K")
            and len(sym) > 5
            and sym[1:].replace("USDT", "").isalpha()
        ):
            # kPEPEUSDT → Binance has 1000PEPEUSDT; we also try the base
            base = sym[1:]  # PEPEUSDT
            binance_1000 = "1000" + base  # 1000PEPEUSDT
            _K_PREFIX_MAP[sym] = (base, binance_1000)
            _binance_syms.add(base)
            _binance_syms.add(binance_1000)
        elif sym.startswith("1000") and len(sym) > 8:
            base = sym[4:]  # SHIBUSDT
            _1000_PREFIX_MAP[sym] = base
            _binance_syms.add(sym)  # Binance lists 1000SHIBUSDT natively
            _binance_syms.add(base)  # also try the base
        else:
            _binance_syms.add(sym)

    # 1. Try Binance endpoints (primary + vision)
    _binance_all = {}  # cache ALL Binance prices for prefix lookups
    for base_url in (
        "https://api.binance.com",
        "https://data-api.binance.vision",
        "https://api.binance.us",
    ):
        if len(prices) >= len(crypto_symbols):
            break
        try:
            url = f"{base_url}/api/v3/ticker/price"
            req = urllib.request.Request(
                url, headers={"User-Agent": "AuditDashboard/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            for item in data:
                s = item.get("symbol", "")
                p = float(item.get("price", 0))
                if p > 0:
                    _binance_all[s] = p
                    if s in _binance_syms and s not in prices:
                        prices[s] = p
            log.info(
                "Fetched from %s: %d prices cached, %d matched so far",
                base_url,
                len(_binance_all),
                len(prices),
            )
            break  # one successful Binance endpoint is enough
        except Exception as e:
            log.warning("Binance %s failed: %s", base_url, e)

    # Resolve k-prefix and 1000-prefix symbols from Binance cache
    for orig_sym, (base_sym, binance_1000) in _K_PREFIX_MAP.items():
        if orig_sym in prices:
            continue
        # kPEPEUSDT: try 1000PEPEUSDT (price / 1000) or PEPEUSDT directly
        if binance_1000 in _binance_all:
            prices[orig_sym] = _binance_all[binance_1000] / 1000.0
        elif base_sym in _binance_all:
            prices[orig_sym] = _binance_all[base_sym]

    for orig_sym, base_sym in _1000_PREFIX_MAP.items():
        if orig_sym in prices:
            continue
        # 1000SHIBUSDT: Binance has it natively
        if orig_sym in _binance_all:
            prices[orig_sym] = _binance_all[orig_sym]
        elif base_sym in _binance_all:
            prices[orig_sym] = _binance_all[base_sym] * 1000.0

    # Also map any direct Binance hits back to the original requested symbols
    for sym in crypto_symbols:
        if sym not in prices and sym in _binance_all:
            prices[sym] = _binance_all[sym]

    # 2. CoinGecko for remaining symbols (always attempted for gaps)
    missing = crypto_symbols - set(prices.keys())
    if missing:
        try:
            _CG_MAP = {
                "BTCUSDT": "bitcoin",
                "ETHUSDT": "ethereum",
                "SOLUSDT": "solana",
                "BNBUSDT": "binancecoin",
                "XRPUSDT": "ripple",
                "DOGEUSDT": "dogecoin",
                "ADAUSDT": "cardano",
                "AVAXUSDT": "avalanche-2",
                "DOTUSDT": "polkadot",
                "LINKUSDT": "chainlink",
                "MATICUSDT": "matic-network",
                "LTCUSDT": "litecoin",
                "NEARUSDT": "near",
                "ATOMUSDT": "cosmos",
                "APTUSDT": "aptos",
                "ARBUSDT": "arbitrum",
                "OPUSDT": "optimism",
                "SUIUSDT": "sui",
                "TRXUSDT": "tron",
                "SHIBUSDT": "shiba-inu",
                "PEPEUSDT": "pepe",
                "RENDERUSDT": "render-token",
                "FETUSDT": "fetch-ai",
                "INJUSDT": "injective-protocol",
                "FILUSDT": "filecoin",
                "GALAUSDT": "gala",
                "WLDUSDT": "worldcoin-wld",
                "HYPEUSDT": "hyperliquid",
                "TAOUSDT": "bittensor",
                "KASUSDT": "kaspa",
                "ONDOUSDT": "ondo-finance",
                "ICPUSDT": "internet-computer",
                "XLMUSDT": "stellar",
                "ETCUSDT": "ethereum-classic",
                # Extended map for commonly missing symbols
                "IPUSDT": "story-protocol",
                "TONUSDT": "the-open-network",
                "RUNEUSDT": "thorchain",
                "PENDLEUSDT": "pendle",
                "BERAUSDT": "berachain-bera",
                "MNTUSDT": "mantle",
                "XMRUSDT": "monero",
                "DYDXUSDT": "dydx-chain",
                "GMXUSDT": "gmx",
                "JUPUSDT": "jupiter-exchange-solana",
                "WUSDT": "wormhole",
                "STXUSDT": "blockstack",
                "TIAUSDT": "celestia",
                "SEIUSDT": "sei-network",
                "MANTAUSDT": "manta-network",
                "ZETAUSDT": "zetachain",
                "PYTHUSDT": "pyth-network",
                "JTOUSDT": "jito-governance-token",
                "BLURUSDT": "blur",
                "STRKUSDT": "starknet",
                "ZKUSDT": "zksync",
                "EIGENUSDT": "eigenlayer",
                "ENAUSDT": "ethena",
                "AEVOUSDT": "aevo-exchange",
                "WIFUSDT": "dogwifcoin",
                "BOMEUSDT": "book-of-meme",
                "PEOPLEUSDT": "constitutiondao",
                "MOVRUSDT": "moonriver",
                "MOVEUSDT": "movement",
                "LAYERUSDT": "solayer",
                "ORCAUSDT": "orca",
                "POLUSDT": "matic-network",
                "FLOKIUSDT": "floki",
                "BONKUSDT": "bonk",
                "ORDIUSDT": "ordinals",
                "AKTUSDT": "akash-network",
                "ARUSDT": "arweave",
                "RNDRUSDT": "render-token",
                "AGIXUSDT": "singularitynet",
                "OCEANUSDT": "ocean-protocol",
                "CFXUSDT": "conflux-token",
                "EGLDUSDT": "elrond-erd-2",
                "FLOWUSDT": "flow",
                "SANDUSDT": "the-sandbox",
                "MANAUSDT": "decentraland",
                "AXSUSDT": "axie-infinity",
                "CRVUSDT": "curve-dao-token",
                "MKRUSDT": "maker",
                "COMPUSDT": "compound-governance-token",
                "SNXUSDT": "havven",
                "LDOUSDT": "lido-dao",
                "RPLETH": "rocket-pool",
                "FTMUSDT": "fantom",
                "ALGOUSDT": "algorand",
                "VETUSDT": "vechain",
                "THETAUSDT": "theta-token",
                "QNTUSDT": "quant-network",
                "HBARUSDT": "hedera-hashgraph",
                "XTZUSDT": "tezos",
                "EOSUSDT": "eos",
                "IOTAUSDT": "iota",
                "KLAYUSDT": "klay-token",
                "LRCUSDT": "loopring",
                "APEUSDT": "apecoin",
                "CHZUSDT": "chiliz",
                "IMXUSDT": "immutable-x",
                "RONINUSDT": "ronin",
                "SUPERUSDT": "superfarm",
            }
            needed_ids = []
            id_to_sym = {}
            for sym in missing:
                cg_id = _CG_MAP.get(sym)
                if cg_id and cg_id not in id_to_sym:
                    needed_ids.append(cg_id)
                    id_to_sym[cg_id] = sym
            if needed_ids:
                # CoinGecko allows ~250 IDs per request; batch in chunks of 50
                for i in range(0, len(needed_ids), 50):
                    chunk = needed_ids[i : i + 50]
                    ids_str = ",".join(chunk)
                    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "AuditDashboard/1.0"}
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        data = json.loads(resp.read())
                    for cg_id, price_data in data.items():
                        sym = id_to_sym.get(cg_id)
                        if sym and "usd" in price_data:
                            prices[sym] = float(price_data["usd"])
                cg_filled = len(prices) - len(prices.keys() - crypto_symbols)
                log.info(
                    "CoinGecko filled %d additional prices for missing symbols",
                    len(needed_ids),
                )
        except Exception as e:
            log.warning("CoinGecko fallback failed: %s", e)

    # 3. XAGUSDT (silver) — not on crypto exchanges; use a metals API or hardcode
    if "XAGUSDT" in crypto_symbols and "XAGUSDT" not in prices:
        try:
            # Try metals.live free API
            url = "https://api.metals.live/v1/spot"
            req = urllib.request.Request(
                url, headers={"User-Agent": "AuditDashboard/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            for metal in data:
                if metal.get("gold") is not None:
                    continue
                if metal.get("silver") is not None:
                    prices["XAGUSDT"] = float(metal["silver"])
                    log.info(
                        "Fetched silver price from metals.live: $%.2f",
                        prices["XAGUSDT"],
                    )
                    break
        except Exception:
            pass
        if "XAGUSDT" not in prices:
            try:
                # Fallback: goldapi.io free endpoint
                url = "https://www.goldapi.io/api/XAG/USD"
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "AuditDashboard/1.0",
                        "x-access-token": "goldapi-demo",
                    },
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                if data.get("price"):
                    prices["XAGUSDT"] = float(data["price"])
                    log.info(
                        "Fetched silver price from goldapi: $%.2f", prices["XAGUSDT"]
                    )
            except Exception:
                pass
        if "XAGUSDT" not in prices:
            # Last resort hardcoded recent silver price (updated periodically)
            prices["XAGUSDT"] = 33.50
            log.info("Using hardcoded silver price: $33.50")

    # Similarly handle XAUUSDT (gold) if requested
    if "XAUUSDT" in crypto_symbols and "XAUUSDT" not in prices:
        if "XAUUSDT" in _binance_all:
            prices["XAUUSDT"] = _binance_all["XAUUSDT"]
        else:
            prices["XAUUSDT"] = 3050.0  # hardcoded fallback
            log.info("Using hardcoded gold price: $3050.00")

    filled = len(set(prices.keys()) & crypto_symbols)
    still_missing = crypto_symbols - set(prices.keys())
    log.info(
        "Price enrichment complete: %d/%d symbols resolved, %d still missing",
        filled,
        len(crypto_symbols),
        len(still_missing),
    )
    if still_missing:
        log.warning("Missing prices for: %s", ", ".join(sorted(still_missing)[:20]))

    return prices


def _fetch_equity_prices(equity_symbols: set) -> dict:
    """Fetch prices for yfinance/FMP-addressable non-crypto symbols.

    Priority:
      0. Read audit_trail/data/stock_prices.json (written by fetch_stock_prices.py in CI)
      1. yfinance batch download for any symbols not found in cache
      2. FMP free API for remaining misses
    Returns {SYMBOL: price}.
    """
    prices = {}
    if not equity_symbols:
        return prices

    invalid_symbols = {
        sym for sym in equity_symbols if not _looks_like_quote_symbol(sym)
    }
    if invalid_symbols:
        equity_symbols = equity_symbols - invalid_symbols
        log.info(
            "Skipping %d non-quote symbols from equity price lookup",
            len(invalid_symbols),
        )
    if not equity_symbols:
        return prices

    # 0. Read pre-cached stock prices (fetch_stock_prices.py writes this before us in CI)
    stock_prices_path = ROOT / "audit_trail" / "data" / "stock_prices.json"
    try:
        if stock_prices_path.exists():
            cached_text = stock_prices_path.read_text(encoding="utf-8", errors="replace")
            try:
                cached = json.loads(cached_text)
            except json.JSONDecodeError:
                # Runtime data files occasionally pick up git conflict markers.
                # Strip marker lines so we can still salvage the last valid JSON body.
                cleaned = "\n".join(
                    line
                    for line in cached_text.splitlines()
                    if not line.lstrip().startswith(("<<<<<<<", "=======", ">>>>>>>"))
                )
                cached = json.loads(cleaned)
                log.warning(
                    "Recovered stock_prices.json after stripping conflict markers"
                )
            cached_prices = cached.get("prices", {})
            for sym in equity_symbols:
                if (
                    sym in cached_prices
                    and cached_prices[sym]
                    and cached_prices[sym] > 0
                ):
                    prices[sym] = float(cached_prices[sym])
            if prices:
                log.info(
                    "Loaded %d/%d equity prices from stock_prices.json cache",
                    len(prices),
                    len(equity_symbols),
                )
    except Exception as e:
        log.warning("Failed to read stock_prices.json cache: %s", e)

    # If all symbols resolved from cache, skip network calls entirely
    remaining = equity_symbols - set(prices.keys())
    if not remaining:
        return prices

    # 1. Try yfinance batch download for remaining symbols (threads=True for parallel fetching)
    try:
        import yfinance as yf

        syms_list = list(remaining)
        try:
            # Batch download: one HTTP call for all symbols — much faster than per-symbol
            data = yf.download(syms_list, period="1d", progress=False, threads=True)
            if data is not None and not data.empty:
                close = data.get("Close", data)
                if hasattr(close, "columns"):
                    # Multi-ticker: columns are symbol names
                    for sym in syms_list:
                        try:
                            col = close[sym] if sym in close.columns else None
                            if col is not None and not col.dropna().empty:
                                prices[sym] = float(col.dropna().iloc[-1])
                        except Exception:
                            continue
                else:
                    # Single-ticker: flat Series
                    sym = syms_list[0]
                    if not close.dropna().empty:
                        prices[sym] = float(close.dropna().iloc[-1])
        except Exception:
            pass
        # Fall back to per-symbol for any missed from the batch
        still_missing = remaining - set(prices.keys())
        for sym in still_missing:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="1d")
                if not hist.empty:
                    prices[sym] = float(hist["Close"].iloc[-1])
            except Exception:
                continue
        yf_count = len(remaining & set(prices.keys()))
        if yf_count:
            log.info(
                "Fetched %d/%d equity prices from yfinance (batch+fallback)",
                yf_count,
                len(remaining),
            )
    except ImportError:
        log.warning("yfinance not installed — trying FMP fallback")
    except Exception as e:
        log.warning("yfinance failed: %s", e)

    # 2. Fallback: FMP free API for any symbols still missing
    missing = equity_symbols - set(prices.keys())
    if missing:
        for sym in missing:
            try:
                url = f"https://financialmodelingprep.com/api/v3/quote-short/{sym}?apikey=demo"
                req = urllib.request.Request(
                    url, headers={"User-Agent": "AuditDashboard/1.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                if data and isinstance(data, list) and data[0].get("price"):
                    prices[sym] = float(data[0]["price"])
            except Exception:
                continue
        if missing & set(prices.keys()):
            log.info(
                "Fetched %d equity prices from FMP fallback",
                len(missing & set(prices.keys())),
            )

    return prices


def _enrich_live_pnl(picks: list) -> list:
    """Fetch current prices from multiple APIs and compute unrealized PnL for active picks."""
    if not picks:
        return picks

    # Collect unique symbols — crypto (USDT/BUSD/USD suffix, k-prefix, 1000-prefix,
    # commodities like XAGUSDT) and equity tickers
    crypto_symbols = set()
    equity_symbols = set()
    source_prices = {}
    market_asset_classes = {"EQUITY", "ETF", "FOREX", "FUTURES", "COMMODITY", "BOND"}
    _EQUITY_TICKERS = {
        "SPY",
        "QQQ",
        "AAPL",
        "MSFT",
        "GOOGL",
        "GOOG",
        "AMZN",
        "TSLA",
        "META",
        "NVDA",
        "AMD",
        "NFLX",
        "DIS",
        "BA",
        "JPM",
        "GS",
        "V",
        "MA",
        "PYPL",
        "SQ",
        "COIN",
        "MSTR",
        "RIOT",
        "MARA",
        "HUT",
        "BITF",
        "IWM",
        "DIA",
        "VTI",
        "VOO",
        "ARKK",
        "XLF",
        "XLE",
        "XLK",
        "GLD",
        "SLV",
        "USO",
        "TLT",
        "VIX",
        "UVXY",
        "SQQQ",
        "TQQQ",
        "BAC",
    }
    for p in picks:
        raw_sym = str(p.get("symbol") or "").upper().strip()
        sym = raw_sym.replace("-", "").replace("_", "").replace("/", "")
        if not raw_sym:
            continue
        if not _looks_like_quote_symbol(raw_sym):
            continue
        current_price = _float(p.get("current_price", 0))
        if current_price and current_price > 0:
            source_prices[raw_sym] = current_price
            source_prices[sym] = current_price
            continue
        if raw_sym in source_prices or sym in source_prices:
            continue
        asset_class = (
            str(p.get("asset_class") or p.get("category") or "").upper().strip()
        )
        # Explicit equity tickers
        if raw_sym in _EQUITY_TICKERS or sym in _EQUITY_TICKERS:
            equity_symbols.add(raw_sym)
        elif asset_class in {"FOREX", "COMMODITY"} and len(sym) == 6 and sym.isalpha():
            fx_lookup = f"{sym}=X"
            equity_symbols.add(fx_lookup)
            p["_price_lookup_sym"] = fx_lookup
        # Crypto: USDT, BUSD, or USD-suffix (will be normalized to USDT)
        elif sym.endswith(("USDT", "BUSD")) and len(sym) > 4:
            crypto_symbols.add(sym)
        elif sym.endswith("USD") and not sym.endswith("USDT") and len(sym) > 3:
            # e.g., BTCUSD -> BTCUSDT for Binance lookup
            crypto_symbols.add(sym + "T")
            # Also store original -> normalized mapping for later
            p["_price_lookup_sym"] = sym + "T"
        elif sym.startswith(("K", "1000")) and sym.endswith(("USDT", "BUSD")):
            # k-prefix (kPEPEUSDT) or 1000-prefix (1000SHIBUSDT)
            crypto_symbols.add(sym)
        elif sym in ("XAGUSDT", "XAUUSDT"):
            crypto_symbols.add(sym)
        elif raw_sym.endswith(("=X", "=F")) or raw_sym.startswith("^"):
            equity_symbols.add(raw_sym)
        elif asset_class in market_asset_classes:
            equity_symbols.add(raw_sym)
        elif sym and len(sym) <= 5 and sym.isalpha():
            # Likely an equity ticker (e.g., AAPL, NVDA, MSFT)
            equity_symbols.add(raw_sym)

    if not crypto_symbols and not equity_symbols and not source_prices:
        return picks

    prices = dict(source_prices)
    if crypto_symbols:
        for sym, price in _fetch_prices_with_failover(crypto_symbols).items():
            prices.setdefault(sym, price)
    if equity_symbols:
        for sym, price in _fetch_equity_prices(equity_symbols).items():
            prices.setdefault(sym, price)
    if not prices:
        return picks

    # Enrich each pick with live PnL
    updated = 0
    for p in picks:
        raw_symbol = str(p.get("symbol") or "").upper().strip()
        raw_sym = raw_symbol.replace("-", "").replace("_", "").replace("/", "")
        # Try direct lookup, then normalized USDT form, then _price_lookup_sym
        price = prices.get(raw_symbol)
        if price is None:
            price = prices.get(raw_sym)
        if price is None and raw_sym.endswith("USD") and not raw_sym.endswith("USDT"):
            price = prices.get(raw_sym + "T")
        if (
            price is None
            and raw_symbol.endswith("USD")
            and not raw_symbol.endswith("USDT")
        ):
            price = prices.get(raw_symbol + "T")
        if price is None and "_price_lookup_sym" in p:
            price = prices.get(p["_price_lookup_sym"])
        if price is None:
            continue
        entry = _float(p.get("entry_price", 0))
        if not entry or entry == 0:
            if _is_prediction_market_pick(
                str(p.get("source_system", "") or ""),
                str(p.get("source_system", "") or ""),
                p,
                str(p.get("strategy", "") or ""),
            ):
                _snapshot_prediction_market_entry(p, price)
                entry = _float(p.get("entry_price", 0))
        if not entry or entry == 0:
            continue
        direction = (p.get("direction") or "").upper()
        if direction == "SHORT":
            pnl = ((entry - price) / entry) * 100
        else:
            pnl = ((price - entry) / entry) * 100

        # Check if TP/SL breached by live price
        tp = _float(p.get("take_profit", 0))
        sl = _float(p.get("stop_loss", 0))
        if direction == "SHORT":
            if tp and price <= tp * 1.001:
                p["_tp_breached"] = True
                p["status"] = "TP_HIT"
            elif sl and price >= sl * 0.999:
                p["_sl_breached"] = True
                p["status"] = "SL_HIT"
        else:  # LONG
            if tp and price >= tp * 0.999:
                p["_tp_breached"] = True
                p["status"] = "TP_HIT"
            elif sl and price <= sl * 1.001:
                p["_sl_breached"] = True
                p["status"] = "SL_HIT"

        # Sanity check: if |P/L| > 500%, entry price is likely corrupt
        # (e.g., stored at wrong decimal scale). Flag but don't display garbage.
        if abs(pnl) > 500:
            p["pnl_pct"] = None
            p["pnl_flagged"] = True
            p["pnl_raw"] = round(pnl, 2)
            p["current_price"] = price
            log.warning(
                "PnL sanity fail: %s entry=%.6f current=%.2f pnl=%.1f%% — flagged as corrupt",
                p.get("symbol"),
                entry,
                price,
                pnl,
            )
            continue

        # Entry price validation gate: flag picks with |PnL| > 200% as suspicious
        # These are not corrupt (that's the >500% check above) but warrant verification.
        if abs(pnl) > 200:
            p["_suspicious_entry"] = True
            p["_entry_validation"] = f"unrealized PnL {pnl:.1f}% exceeds 200% — verify entry price"
            log.warning(
                "Suspicious entry: %s entry=%.6f current=%.2f pnl=%.1f%% — flagged for review",
                p.get("symbol"),
                entry,
                price,
                pnl,
            )

        p["pnl_pct"] = round(pnl, 2)
        p["current_price"] = price
        updated += 1

    # Clean up temporary lookup keys so they don't leak into the payload
    for p in picks:
        p.pop("_price_lookup_sym", None)

    # Inject Symbol-Aware Track Stats using the user's new tool
    track_stats = _build_strategy_symbol_track_stats(
        [p for p in picks if str(p.get("status")).upper() in ("CLOSED", "RESOLVED", "WON", "LOST", "SL_HIT", "TP_HIT")]
    )
    for p in picks:
        if str(p.get("status")).upper() in ("OPEN", "ACTIVE", "LIVE", "PENDING"):
            key = _track_stats_key(str(p.get("strategy", "")), _normalize_symbol(str(p.get("symbol", ""))))
            stats = track_stats.get(key)
            if stats:
                p.update(stats)
                # Calculate a symbol-specific track score boost
                wr = stats.get("sym_track_wr")
                total = stats.get("sym_track_total", 0)
                if wr is not None and total >= 5:
                    p["sym_track_score"] = round((wr - 50) * min(total/10, 2.0), 2)

    log.info("Updated PnL and Track Stats for %d active picks with live prices", updated)
    return picks


# ── Lock file to prevent concurrent runs ──


def _acquire_lock():
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            age = datetime.now().timestamp() - LOCK_FILE.stat().st_mtime
            if age < 300:  # 5 min
                log.warning(
                    "Lock file exists and is %.0fs old — another run in progress?", age
                )
                return False
            log.warning("Stale lock file (%.0fs old) — removing", age)
            LOCK_FILE.unlink()
        except Exception:
            pass
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True


def _release_lock():
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ── Safe readers ──


def _load_json_resilient(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = "\n".join(
            line
            for line in text.splitlines()
            if not line.lstrip().startswith(("<<<<<<<", "=======", ">>>>>>>"))
        )
        data = json.loads(cleaned)
        log.warning("Recovered JSON after stripping conflict markers: %s", path)
        return data


def _safe_json(path: Path):
    """Load JSON file safely, return None on error."""
    if not path.exists():
        log.debug("JSON not found: %s", path)
        return None
    try:
        return _load_json_resilient(path)
    except Exception as e:
        log.warning("Failed to load JSON %s: %s", path, e)
        return None


def _hf_stats_summary() -> dict:
    """Compute HF-grade stats from the recent_closed pick set.

    Either loads from cached JSON or computes fresh from dashboard_data.json.
    Returns {} if hf_stats module unavailable or fewer than 20 closed picks.
    """
    if not _HF_STATS_AVAILABLE:
        return {}
    hf_cache = ROOT / "tools" / "data" / "hf_stats_summary.json"
    # 2026-05-12 V2 fix: prior code returned cached data WITHOUT checking
    # mtime — the snapshot from 2026-04-22 was being served for 20 days
    # because hf_cache.exists() always returned True. Add 24h staleness gate.
    HF_CACHE_MAX_AGE_HOURS = 24
    cache_fresh = False
    if hf_cache.exists():
        try:
            from datetime import datetime as _dt, timezone as _tz
            mtime = _dt.fromtimestamp(hf_cache.stat().st_mtime, tz=_tz.utc)
            age_hours = (_dt.now(_tz.utc) - mtime).total_seconds() / 3600
            cache_fresh = age_hours <= HF_CACHE_MAX_AGE_HOURS
            if not cache_fresh:
                log.info(
                    "HF stats cache %.1fh stale (>%dh); recomputing",
                    age_hours, HF_CACHE_MAX_AGE_HOURS,
                )
        except (OSError, ValueError) as exc:
            log.warning("HF stats cache mtime check failed: %s", exc)
            cache_fresh = False
    if cache_fresh:
        data = _safe_json(hf_cache)
        if data:
            return data
    dash_path = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
    if not dash_path.exists():
        return {}
    try:
        data = json.loads(dash_path.read_text(encoding="utf-8"))
        picks = data.get("picks", {}).get("recent_closed") or []
        if len(picks) < 20:
            return {}
        from tools.hf_stats import compute_metrics
        result = compute_metrics(picks, window_days=30, fee_bps=20.0)
        hf_cache.parent.mkdir(parents=True, exist_ok=True)
        hf_cache.write_text(json.dumps(result, indent=2), encoding="utf-8")
        log.info("Computed fresh HF stats from %d picks", len(picks))
        return result
    except Exception as e:
        log.warning("HF stats compute failed: %s", e)
        return {}


def _safe_text(path: Path) -> str:
    """Load text file safely, return empty string on error."""
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        log.warning("Failed to load text %s: %s", path, e)
        return ""


def _dashboard_href(path: Path) -> str:
    """Build a repo-relative href that works from the audit dashboard."""
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        rel = path.as_posix()
    return "../" + quote(rel, safe="/")


def _artifact_category(path: Path) -> str:
    ext = path.suffix.lower()
    name = path.name.lower()
    if ext == ".png":
        return "chart"
    if ext == ".csv":
        return "dataset"
    if ext == ".py":
        return "code"
    if "strategy" in name:
        return "strategy"
    if "report" in name or "analysis" in name or "summary" in name:
        return "report"
    return "note"


def _extract_match(pattern: str, text: str, flags: int = 0):
    return re.search(pattern, text or "", flags)


def _extract_float(pattern: str, text: str, flags: int = 0) -> float | None:
    match = _extract_match(pattern, text, flags)
    if not match:
        return None
    try:
        return float(match.group(1))
    except Exception:
        return None


def _build_btc_strategy_replication_report(folder: Path) -> dict | None:
    """Summarize the BTC scalping replication dossier for the audit dashboard."""
    if not folder.exists() or not folder.is_dir():
        return None

    final_report_path = folder / "FINAL_INVESTIGATION_REPORT.txt"
    final_strategy_path = folder / "FINAL_STRATEGY.txt"
    backtest_path = folder / "backtest_results.txt"
    timing_path = folder / "timing_analysis_report.txt"
    discrepancy_path = folder / "bybit_price_discrepancy_investigation_report.md"
    deliverables_path = folder / "FINAL_DELIVERABLES.txt"
    synthesis_path = folder / "strategy_synthesis_summary.txt"
    microstructure_path = folder / "bybit_microstructure_scalper.py"
    production_code_path = folder / "final_strategy.py"

    final_report = _safe_text(final_report_path)
    final_strategy = _safe_text(final_strategy_path)
    backtest = _safe_text(backtest_path)
    timing = _safe_text(timing_path)
    discrepancy = _safe_text(discrepancy_path)
    deliverables = _safe_text(deliverables_path)
    synthesis = _safe_text(synthesis_path)
    microstructure_code = _safe_text(microstructure_path)

    if not any(
        [
            final_report,
            final_strategy,
            backtest,
            timing,
            discrepancy,
            deliverables,
            synthesis,
        ]
    ):
        return None

    claim_win_rate = _extract_float(r"Win Rate:\s+([0-9.]+)%", final_report)
    best_dataset_wr = None
    for dataset in ("DATASET 1", "DATASET 2"):
        match = _extract_match(
            rf"{dataset}.*?Win Rate:\s+([0-9.]+)%",
            backtest,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            wr = float(match.group(1))
            best_dataset_wr = wr if best_dataset_wr is None else max(best_dataset_wr, wr)

    realistic_wr_match = _extract_match(
        r"Win Rate:\s+([0-9]+)-([0-9]+)%",
        final_strategy,
        flags=re.IGNORECASE,
    )
    realistic_wr_range = None
    if realistic_wr_match:
        realistic_wr_range = (
            f"{realistic_wr_match.group(1)}-{realistic_wr_match.group(2)}%"
        )

    matched_real = None
    matched_total = None
    match_real = _extract_match(
        r"Only\s+([0-9]+)\s+of\s+([0-9]+)\s+trades matched real BTC market (?:data|prices)",
        final_report,
        flags=re.IGNORECASE,
    )
    if match_real:
        matched_real = int(match_real.group(1))
        matched_total = int(match_real.group(2))

    automation_confidence = _extract_float(
        r"CONFIDENCE LEVEL:\s*([0-9.]+)%",
        timing,
        flags=re.IGNORECASE,
    )
    if automation_confidence is None:
        automation_confidence = _extract_float(
            r"CONFIDENCE LEVEL:\s*([0-9.]+)%",
            final_report,
            flags=re.IGNORECASE,
        )

    fee_range_match = _extract_match(
        r"Estimated \$([0-9]+)-([0-9]+) in unreported costs",
        final_report,
        flags=re.IGNORECASE,
    )
    fee_range = (
        f"${fee_range_match.group(1)}-${fee_range_match.group(2)}"
        if fee_range_match
        else None
    )

    contradiction_files = []
    for path, text in (
        (deliverables_path, deliverables),
        (synthesis_path, synthesis),
        (microstructure_path, microstructure_code),
    ):
        lowered = (text or "").lower()
        if (
            "91.67% win rate is achievable" in lowered
            or "expected win rate:         91.67%" in lowered
            or "target: 91.67% win rate replication" in lowered
        ):
            contradiction_files.append(path.name)

    artifacts = []
    for path in sorted(folder.iterdir(), key=lambda p: (p.suffix.lower(), p.name.lower())):
        if not path.is_file():
            continue
        artifacts.append(
            {
                "name": path.name,
                "category": _artifact_category(path),
                "size_kb": round(path.stat().st_size / 1024, 1),
                "href": _dashboard_href(path),
            }
        )

    recommended_names = {
        final_report_path.name,
        final_strategy_path.name,
        backtest_path.name,
        production_code_path.name,
        discrepancy_path.name,
        timing_path.name,
    }
    superseded_names = set(contradiction_files)
    final_artifacts = [a for a in artifacts if a["name"] in recommended_names]
    superseded_artifacts = [a for a in artifacts if a["name"] in superseded_names]
    chart_artifacts = [a for a in artifacts if a["category"] == "chart"]

    review_findings = []
    if contradiction_files:
        review_findings.append(
            {
                "severity": "high",
                "title": "Intermediate deliverables contradict the final verdict",
                "detail": (
                    "Several exploratory files still claim the 91.67% result is "
                    "achievable, but the final investigation, backtest, and practical "
                    "strategy all conclude the screenshot is not reproducible on real data."
                ),
                "files": contradiction_files,
            }
        )
    if best_dataset_wr is not None and claim_win_rate is not None and best_dataset_wr < claim_win_rate:
        review_findings.append(
            {
                "severity": "medium",
                "title": "Best observed backtest still missed the headline claim",
                "detail": (
                    f"The strongest backtest run reached {best_dataset_wr:.2f}% win rate, "
                    f"still below the claimed {claim_win_rate:.2f}%."
                ),
                "files": [backtest_path.name],
            }
        )

    folder_ts = datetime.fromtimestamp(folder.stat().st_mtime, tz=timezone.utc)

    return {
        "id": "btc_scalping_strategy_replication",
        "title": "BTC Scalping Strategy Replication",
        "subtitle": "Review of the claimed 91.67% BTCUSD.V win-rate screenshot",
        "folder_name": folder.name,
        "folder_href": _dashboard_href(final_report_path),
        "updated_at": folder_ts.isoformat(),
        "verdict": {
            "status": "not_replicable",
            "label": "Not Replicable",
            "summary": (
                "The claimed 91.67% win rate does not hold up under realistic market "
                "data, cost accounting, and repeatable backtesting."
            ),
        },
        "claim": {
            "win_rate_pct": claim_win_rate,
            "trade_count": matched_total or 12,
        },
        "metrics": {
            "matched_real_trades": matched_real,
            "trade_count": matched_total,
            "best_backtest_win_rate_pct": best_dataset_wr,
            "automation_confidence_pct": automation_confidence,
            "realistic_win_rate_range": realistic_wr_range,
            "unreported_cost_range": fee_range,
            "contradiction_count": len(contradiction_files),
        },
        "key_findings": [
            "Only 2 of 12 trades matched real BTC market data.",
            "The outlier 1,737-point move did not occur in real BTC price history.",
            "Reported P/L excluded exchange costs, adding roughly $216-$324 in hidden fees.",
            "The 4-second pyramid strongly implies automation rather than manual execution.",
            "The practical replacement is VWAP Scalper Pro with a 60-75% target win-rate range.",
        ],
        "review_findings": review_findings,
        "final_artifacts": final_artifacts,
        "superseded_artifacts": superseded_artifacts,
        "chart_artifacts": chart_artifacts,
        "artifacts": artifacts,
        "recommended_next_step": (
            "Use FINAL_INVESTIGATION_REPORT.txt and FINAL_STRATEGY.txt as the source of truth; "
            "treat the microstructure replication files as exploratory dead ends."
        ),
    }


def collect_research_reports() -> list[dict]:
    """Collect curated research dossiers that should surface in the audit dashboard."""
    reports = []
    btc_report = _build_btc_strategy_replication_report(
        ROOT / "Kimi_Agent_BTC Scalping Strategy Replication"
    )
    if btc_report:
        reports.append(btc_report)
    return reports


def _claude_perf_sort_ts(raw: dict) -> float:
    """Best-effort timestamp sort key for Claude tracker rows."""
    for key in (
        "exit_time",
        "resolved_at",
        "closed_at",
        "entry_time",
        "timestamp",
        "created_at",
    ):
        value = raw.get(key)
        if not value:
            continue
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            continue
    return 0.0


def _build_claude_perf_index(*datasets) -> dict[tuple[str, str], list[dict]]:
    """Index rich Claude tracker rows so recent_10 can inherit real entry/exit data."""
    index: dict[tuple[str, str], list[dict]] = {}
    seen_keys = set()
    for dataset in datasets:
        if not isinstance(dataset, list):
            continue
        for raw in dataset:
            if not isinstance(raw, dict):
                continue
            symbol = str(raw.get("symbol", "")).upper().strip()
            exit_reason = (
                str(raw.get("exit_reason", raw.get("resolved_reason", "")))
                .upper()
                .strip()
            )
            if not symbol or not exit_reason:
                continue
            dedupe_key = (
                raw.get("pick_id") or raw.get("id") or "",
                symbol,
                exit_reason,
                round(_float(raw.get("pnl_pct", 0)), 4),
                round(_claude_perf_sort_ts(raw), 0),
            )
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            index.setdefault((symbol, exit_reason), []).append(raw)

    for candidates in index.values():
        candidates.sort(key=_claude_perf_sort_ts, reverse=True)
    return index


def _match_claude_perf_row(
    summary_trade: dict, perf_index: dict[tuple[str, str], list[dict]]
) -> dict | None:
    """Find the rich history row backing a recent_10 Claude performance summary item."""
    symbol = str(summary_trade.get("symbol", "")).upper().strip()
    exit_reason = str(summary_trade.get("exit_reason", "")).upper().strip()
    target_pnl = round(_float(summary_trade.get("pnl_pct", 0)), 4)
    if not symbol:
        return None

    candidates = list(perf_index.get((symbol, exit_reason), []))
    if not candidates:
        for (candidate_symbol, _candidate_reason), rows in perf_index.items():
            if candidate_symbol == symbol:
                candidates.extend(rows)

    best = None
    best_delta = None
    for row in candidates:
        delta = abs(round(_float(row.get("pnl_pct", 0)), 4) - target_pnl)
        if best is None or delta < best_delta:
            best = row
            best_delta = delta
            if delta < 0.02:
                break

    if best is None or best_delta is None or best_delta > 0.5:
        return None
    return dict(best)


def _build_claude_perf_pick(
    summary_trade: dict, matched_row: dict | None, fallback_timestamp: str
) -> dict:
    """Merge recent_10 summary fields with the richer tracker/history row when available."""
    pick = dict(matched_row or {})
    pick.setdefault("symbol", summary_trade.get("symbol", ""))
    pick.setdefault("direction", "BUY")
    pick.setdefault("strategy", "claude_gainer_ml")
    pick.setdefault("entry_price", summary_trade.get("entry_price", 0))
    pick.setdefault("exit_price", summary_trade.get("exit_price", 0))
    pick.setdefault("pnl_pct", summary_trade.get("pnl_pct", 0))
    pick.setdefault("exit_reason", summary_trade.get("exit_reason", ""))
    if not pick.get("confidence"):
        pick["confidence"] = summary_trade.get("confidence", "")
    if (
        not any(pick.get(k) for k in ("entry_time", "timestamp", "created_at"))
        and fallback_timestamp
    ):
        pick["timestamp"] = fallback_timestamp
    if (
        not any(pick.get(k) for k in ("exit_time", "resolved_at", "closed_at"))
        and fallback_timestamp
    ):
        pick["resolved_at"] = fallback_timestamp
    return pick


def _maybe_refresh_universal_resolved():
    """Refresh universal_resolved_picks.json when it is stale versus key source ledgers."""
    resolved_path = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
    refresh_reasons = []
    resolved_mtime = resolved_path.stat().st_mtime if resolved_path.exists() else 0.0
    now_ts = datetime.now(timezone.utc).timestamp()

    if not resolved_path.exists():
        refresh_reasons.append("resolved file missing")
    else:
        age_minutes = (now_ts - resolved_mtime) / 60.0
        if age_minutes > UNIVERSAL_RESOLVER_MAX_AGE_MINUTES:
            refresh_reasons.append(f"resolved file is {age_minutes:.0f}m old")

    newer_sources = []
    for rel_path in UNIVERSAL_RESOLVER_WATCH_FILES:
        src_path = ROOT / rel_path
        if src_path.exists() and src_path.stat().st_mtime > resolved_mtime + 1:
            newer_sources.append(src_path.name)
    if newer_sources:
        refresh_reasons.append(
            "newer source ledgers: " + ", ".join(sorted(newer_sources))
        )

    if not refresh_reasons:
        return

    log.info("Refreshing universal pick resolver (%s)", "; ".join(refresh_reasons))
    try:
        subprocess.run(
            [sys.executable, "-m", "audit_trail.universal_pick_resolver"],
            cwd=str(ROOT),
            check=True,
            timeout=600,
        )
        if resolved_path.exists():
            age_seconds = (
                datetime.now(timezone.utc).timestamp() - resolved_path.stat().st_mtime
            )
            log.info(
                "  Universal resolver refreshed successfully (age %.0fs)", age_seconds
            )
    except subprocess.TimeoutExpired:
        log.warning(
            "  Universal resolver timed out after 600s; using existing resolved file"
        )
    except subprocess.CalledProcessError as e:
        log.warning(
            "  Universal resolver failed with exit code %s; using existing resolved file",
            e.returncode,
        )
    except Exception as e:
        log.warning("  Universal resolver refresh failed: %s", e)


def _load_smart_picks_feed():
    """Load the current Smart Picks feed for embedding into the dashboard payload."""
    path = ROOT / "alpha_engine" / "data" / "smart_picks.json"
    data = _safe_json(path)
    return data if isinstance(data, dict) else {"picks": []}


def _summarize_smart_picks_history():
    """Build a compact Smart Picks snapshot summary for the dashboard card."""
    path = ROOT / "alpha_engine" / "data" / "smart_picks_history.json"
    data = _safe_json(path)
    if not isinstance(data, dict):
        return None

    batches = data.get("batches", [])
    resolved = [b for b in batches if isinstance(b, dict) and b.get("resolved")]
    tier_stats = {
        "SCALP": {"wins": 0, "total": 0},
        "SWING": {"wins": 0, "total": 0},
        "POSITION": {"wins": 0, "total": 0},
    }
    total_wins = 0
    total_picks = 0
    flat_count = 0
    recent_batches = []

    def _pick_pnl(pick, idx, last_snapshot):
        raw = pick.get("final_pnl")
        if raw is None:
            raw = pick.get("pnl_pct")
        if raw is None and isinstance(last_snapshot, dict):
            snap_pnls = last_snapshot.get("picks_pnl", [])
            if idx < len(snap_pnls):
                raw = snap_pnls[idx]
        return _float(raw)

    for batch in resolved:
        last_snapshot = (
            batch.get("snapshots", [])[-1] if batch.get("snapshots") else None
        )
        batch_wins = 0
        batch_total = 0
        for idx, pick in enumerate(batch.get("picks", [])):
            if not isinstance(pick, dict):
                continue
            pnl = _pick_pnl(pick, idx, last_snapshot)
            tier = str(pick.get("tier", "SWING") or "SWING").upper()
            if tier not in tier_stats:
                tier = "SWING"
            tier_stats[tier]["total"] += 1
            total_picks += 1
            batch_total += 1
            if pnl > 0:
                tier_stats[tier]["wins"] += 1
                total_wins += 1
                batch_wins += 1
            elif abs(pnl) <= 1e-9:
                flat_count += 1

        recent_batches.append(
            {
                "batch_id": batch.get("batch_id") or batch.get("batch_number"),
                "generated_at": batch.get("generated_at"),
                "wins": batch_wins,
                "total": batch_total,
                "win_rate": round(batch_wins / batch_total * 100, 1)
                if batch_total
                else 0.0,
            }
        )

    updated_at = (
        datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        if path.exists()
        else None
    )
    return {
        "metric_type": "snapshot",
        "updated_at": updated_at,
        "resolved_batches": len(resolved),
        "total_picks": total_picks,
        "wins": total_wins,
        "flat": flat_count,
        "win_rate": round(total_wins / total_picks * 100, 1) if total_picks else 0.0,
        "tiers": {
            tier: {
                "wins": stats["wins"],
                "total": stats["total"],
                "win_rate": round(stats["wins"] / stats["total"] * 100, 1)
                if stats["total"]
                else 0.0,
            }
            for tier, stats in tier_stats.items()
        },
        "last_batches": list(reversed(recent_batches[-3:])),
    }


def _safe_sqlite(db_path: Path, query: str, params: tuple = ()):
    """Run a SELECT query safely, return list of dicts.

    Always pass user-influenced values via *params* (parameterised query) —
    never interpolate them directly into the query string.
    """
    if not db_path.exists():
        log.debug("SQLite DB not found: %s", db_path)
        return []
    try:
        with sqlite3.connect(str(db_path), timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        log.warning("SQLite query failed on %s: %s", db_path, e)
        return []


def _float(v):
    try:
        return float(v) if v else 0.0
    except (ValueError, TypeError):
        return 0.0


def _cap_sharpe(v, cap=99.99):
    """Cap Sharpe ratio to a reasonable range to prevent near-zero std overflow."""
    try:
        f = float(v) if v else 0.0
    except (ValueError, TypeError):
        return 0.0
    if abs(f) > cap:
        return 0.0  # Treat absurd Sharpe as invalid (division by near-zero std)
    return f


def _rolling_wr(trades: list, n: int = 10) -> float:
    """Win rate over the last N trades. Returns 0.0 if insufficient data."""
    if not trades:
        return 0.0
    recent = trades[-n:]
    wins = sum(1 for t in recent if _float(t.get("pnl_pct", t.get("pnl", 0))) > 0)
    return round(wins / len(recent), 4) if recent else 0.0


def _health_score(entry: dict) -> str:
    """Compute strategy health: HEALTHY / WATCH / DEGRADED.

    Score inputs (0-100):
    - Forward decay vs backtest: 30%
    - Last 10 WR vs lifetime WR: 30%
    - Days since last trade: 20%
    - Trade volume (sample quality): 20%
    """
    score = 50  # baseline

    # Decay component (30%)
    decay = _float(entry.get("fwd_decay", entry.get("decay", 0)))
    if decay > -10:
        score += 15
    elif decay > -30:
        score += 5
    else:
        score -= 15

    # Rolling WR vs lifetime (30%)
    last10 = _float(entry.get("fwd_last10_wr", 0))
    lifetime = _float(entry.get("fwd_wr", 0))
    if last10 > 0 and lifetime > 0:
        wr_ratio = last10 / lifetime if lifetime > 0 else 1.0
        if wr_ratio >= 0.9:
            score += 15
        elif wr_ratio >= 0.7:
            score += 5
        else:
            score -= 15

    # Recency component (20%) - based on sample quality
    sq = entry.get("sample_quality", "insufficient")
    if sq == "strong":
        score += 10
    elif sq == "moderate":
        score += 5
    elif sq == "weak":
        score -= 5
    else:
        score -= 10

    # Volume component (20%)
    trades = entry.get("fwd_trades", 0)
    if isinstance(trades, (int, float)) and trades >= 20:
        score += 10
    elif isinstance(trades, (int, float)) and trades >= 10:
        score += 5

    if score >= 65:
        return "healthy"
    elif score >= 40:
        return "watch"
    else:
        return "degraded"


def _detect_conflicts(active_picks: list) -> list:
    """Detect symbols with conflicting LONG+SHORT active picks.

    Enhanced with trust-weighted resolution and timeframe-aware filtering:
    picks on different trade horizons (e.g., SCALP SHORT + SWING LONG) are
    tagged as cross-timeframe non-conflicts rather than true conflicts.
    """
    from collections import defaultdict
    from cross_aggregation.timeframe_classifier import (
        is_real_conflict as _is_tf_conflict,
    )

    by_symbol = defaultdict(
        lambda: {
            "LONG": [],
            "SHORT": [],
            "strategies": [],
            "long_timeframes": [],
            "short_timeframes": [],
        }
    )
    for p in active_picks:
        sym = _normalize_symbol(p.get("symbol", ""))
        d = p.get("direction", "")
        sys_name = p.get("source_system", "unknown")
        tf = p.get("trade_timeframe", "SWING")
        if sym and d in ("LONG", "SHORT"):
            by_symbol[sym][d].append(sys_name)
            by_symbol[sym]["strategies"].append(p.get("strategy", "unknown"))
            by_symbol[sym][f"{d.lower()}_timeframes"].append(tf)

    conflicts = []
    for sym, info in by_symbol.items():
        if info["LONG"] and info["SHORT"]:
            # Trust-weighted conflict resolution
            direction, reason, confidence = resolve_conflict(
                info["LONG"], info["SHORT"]
            )
            long_tiers = [get_tier(s) for s in info["LONG"]]
            short_tiers = [get_tier(s) for s in info["SHORT"]]
            long_weight = sum(get_vote_weight(s) for s in info["LONG"])
            short_weight = sum(get_vote_weight(s) for s in info["SHORT"])

            # Timeframe-aware conflict classification
            # Check if ANY long vs short pair is on a similar timeframe
            long_tfs = set(info["long_timeframes"])
            short_tfs = set(info["short_timeframes"])
            has_real_tf_conflict = any(
                _is_tf_conflict(ltf, stf) for ltf in long_tfs for stf in short_tfs
            )

            conflicts.append(
                {
                    "symbol": sym,
                    "long_count": len(info["LONG"]),
                    "short_count": len(info["SHORT"]),
                    "total": len(info["LONG"]) + len(info["SHORT"]),
                    "strategies": info["strategies"][:10],
                    # Trust-enriched fields
                    "recommended_direction": direction,
                    "resolution_reason": reason,
                    "confidence_delta": round(confidence, 3),
                    "long_systems": info["LONG"][:5],
                    "short_systems": info["SHORT"][:5],
                    "long_tiers": long_tiers[:5],
                    "short_tiers": short_tiers[:5],
                    "long_weight": round(long_weight, 1),
                    "short_weight": round(short_weight, 1),
                    # Timeframe conflict classification
                    "is_real_conflict": has_real_tf_conflict,
                    "long_timeframes": sorted(long_tfs),
                    "short_timeframes": sorted(short_tfs),
                    "conflict_note": (
                        "Same/adjacent timeframe — genuine direction conflict"
                        if has_real_tf_conflict
                        else f"Cross-timeframe: LONG={'/'.join(sorted(long_tfs))} vs SHORT={'/'.join(sorted(short_tfs))} — may coexist"
                    ),
                }
            )
    return conflicts


def _tag_duplicate_picks(active_picks: list, smart_picks: list) -> None:
    """Tag picks with duplicate/conflict metadata for frontend display.

    Mutates picks in place, adding:
      - _dup: bool — appears more than once in active (same symbol)
      - _dup_icon: str — emoji icon for display
      - _dup_tooltip: str — human-readable explanation
      - _dup_count: int — how many picks share this symbol in active
      - _dup_sources: list[str] — source_systems of the other picks
      - _cross_feed_dup: bool — also appears in smart picks
      - _direction_conflict: bool — same symbol has opposite direction picks
    """
    from collections import defaultdict

    # Build active-by-symbol index
    active_by_sym = defaultdict(list)
    for p in active_picks:
        sym = _normalize_symbol(p.get("symbol", ""))
        if sym:
            active_by_sym[sym].append(p)

    # Build smart-symbol set for cross-feed checking
    smart_sym_dir = set()
    for p in smart_picks:
        sym = _normalize_symbol(p.get("symbol", ""))
        d = (p.get("direction") or "").upper()
        if sym:
            smart_sym_dir.add((sym, d))

    for sym, picks in active_by_sym.items():
        # Rank same-symbol picks by a simple portfolio priority so the payload can
        # identify a single primary entry without collapsing the rest of the group.
        def _portfolio_priority(pick: dict) -> tuple:
            score = pick.get("score") or pick.get("elite_score") or 0
            confidence = pick.get("confidence") or 0
            agreement = pick.get("agreement_count") or pick.get("agreement_level") or 0
            trust = pick.get("trust_score") or pick.get("system_trust") or 0
            try:
                score = float(score)
            except (TypeError, ValueError):
                score = 0.0
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0.0
            try:
                agreement = float(agreement)
            except (TypeError, ValueError):
                agreement = 0.0
            try:
                trust = float(trust)
            except (TypeError, ValueError):
                trust = 0.0
            return (score, confidence, agreement, trust)

        ranked_picks = sorted(picks, key=_portfolio_priority, reverse=True)
        directions = set((p.get("direction") or "").upper() for p in picks)
        has_conflict = len(directions) > 1
        is_dup = len(picks) > 1

        for rank, pick in enumerate(ranked_picks, start=1):
            pd = (pick.get("direction") or "").upper()
            ps = pick.get("source_system", "unknown")

            # Collect other sources on same symbol
            other_sources = [
                p2.get("source_system", "unknown") for p2 in picks if p2 is not pick
            ]
            other_strategies = [
                p2.get("strategy", "?") for p2 in picks if p2 is not pick
            ]

            # Cross-feed check
            in_smart = (sym, pd) in smart_sym_dir

            # Build tooltip parts
            tip_parts = []
            pick["_dup"] = is_dup
            pick["_dup_count"] = len(picks)
            pick["_dup_sources"] = other_sources
            pick["_cross_feed_dup"] = in_smart
            pick["_direction_conflict"] = has_conflict
            pick["_dup_rank"] = rank
            pick["_dup_is_primary"] = rank == 1

            if has_conflict:
                pick["_dup_icon"] = "\u26a0\ufe0f"  # ⚠️ warning
                same_dir = [
                    p2
                    for p2 in picks
                    if (p2.get("direction") or "").upper() == pd and p2 is not pick
                ]
                opp_dir = [
                    p2 for p2 in picks if (p2.get("direction") or "").upper() != pd
                ]
                if same_dir:
                    same_strats = [p2.get("strategy", "?") for p2 in same_dir]
                    tip_parts.append(
                        f"{len(same_dir)} other {pd} signal(s) on {sym}: {', '.join(same_strats[:3])}"
                    )
                if opp_dir:
                    opp_dirs = set((p2.get("direction") or "?") for p2 in opp_dir)
                    opp_strats = [p2.get("strategy", "?") for p2 in opp_dir]
                    tip_parts.append(
                        f"DIRECTION CONFLICT: {len(opp_dir)} {('/'.join(opp_dirs))} signal(s): {', '.join(opp_strats[:3])}"
                    )
            elif is_dup:
                pick["_dup_icon"] = "\U0001f501"  # 🔁 repeat
                tip_parts.append(
                    f"{len(picks) - 1} other {pd} signal(s) on {sym} from: {', '.join(other_sources[:3])}"
                )
                tip_parts.append(
                    "Multiple systems agree on this direction (confluence)"
                )
            else:
                pick["_dup_icon"] = ""
                pick["_dup_tooltip"] = ""

                continue

            if in_smart:
                tip_parts.append(f"Also in Smart Picks feed ({pd})")

            pick["_dup_tooltip"] = " | ".join(tip_parts)


def _compute_portfolio_uniqueness_stats(active_picks: list) -> dict:
    """Summarize symbol-level duplication and direction conflicts for the payload."""
    from collections import defaultdict

    by_symbol = defaultdict(list)
    by_symbol_direction = defaultdict(list)

    for pick in active_picks:
        sym = _normalize_symbol(pick.get("symbol", ""))
        if not sym:
            continue
        by_symbol[sym].append(pick)
        direction = (pick.get("direction") or "").upper()
        if direction in ("LONG", "SHORT"):
            by_symbol_direction[(sym, direction)].append(pick)

    duplicate_symbol_groups = 0
    duplicate_symbol_picks = 0
    conflict_symbol_count = 0
    conflict_active_pick_count = 0

    for sym, picks in by_symbol.items():
        if len(picks) > 1:
            duplicate_symbol_groups += 1
            duplicate_symbol_picks += len(picks) - 1
            directions = {
                (p.get("direction") or "").upper()
                for p in picks
                if (p.get("direction") or "").upper() in ("LONG", "SHORT")
            }
            if len(directions) > 1:
                conflict_symbol_count += 1
                conflict_active_pick_count += len(picks)

    duplicate_symbol_direction_groups = sum(
        1 for picks in by_symbol_direction.values() if len(picks) > 1
    )
    duplicate_symbol_direction_picks = sum(
        len(picks) - 1 for picks in by_symbol_direction.values() if len(picks) > 1
    )

    cross_feed_duplicate_count = sum(
        1 for pick in active_picks if pick.get("_cross_feed_dup")
    )

    return {
        "raw_active_picks": len(active_picks),
        "unique_symbol_count": len(by_symbol),
        "unique_symbol_direction_positions": len(by_symbol_direction),
        "duplicate_symbol_groups": duplicate_symbol_groups,
        "duplicate_symbol_picks": duplicate_symbol_picks,
        "duplicate_symbol_direction_groups": duplicate_symbol_direction_groups,
        "duplicate_symbol_direction_picks": duplicate_symbol_direction_picks,
        "conflict_symbol_count": conflict_symbol_count,
        "conflict_active_pick_count": conflict_active_pick_count,
        "cross_feed_duplicate_count": cross_feed_duplicate_count,
    }


# ── Confidence extraction (handles varied source formats) ──

_TEXT_CONFIDENCE_MAP = {
    "very high": 0.90,
    "high": 0.80,
    "medium-high": 0.72,
    "medium": 0.65,
    "moderate": 0.60,
    "low-medium": 0.50,
    "low": 0.40,
    "very low": 0.25,
}


def _extract_confidence(raw: dict) -> float:
    """Extract numeric confidence from any pick source format.

    Handles: numeric confidence, text confidence (HIGH/MEDIUM/LOW),
    sentiment_score, probability, ml_score, score, win_rate, sharpe-derived.
    """
    # Try numeric confidence fields first (enhanced_conviction: predictions + audit cross-signal)
    for key in ("enhanced_conviction", "confidence", "ml_score", "score", "probability"):
        val = raw.get(key)
        if val is not None:
            # Handle text values like "HIGH", "MEDIUM", "LOW"
            if isinstance(val, str):
                mapped = _TEXT_CONFIDENCE_MAP.get(val.strip().lower())
                if mapped is not None:
                    return mapped
                # Try parsing as number
                try:
                    fval = float(val)
                    if fval > 0:
                        return min(fval, 1.0) if fval <= 1.0 else min(fval / 100.0, 1.0)
                except (ValueError, TypeError):
                    continue
            try:
                fval = float(val)
                if fval > 0:
                    return min(fval, 1.0) if fval <= 1.0 else min(fval / 100.0, 1.0)
            except (ValueError, TypeError):
                continue

    # Fallback: sentiment_score (predictions system)
    sent = raw.get("sentiment_score", raw.get("sentiment"))
    if sent is not None:
        try:
            return min(float(sent), 1.0)
        except (ValueError, TypeError):
            pass

    # Fallback: win_rate as confidence proxy
    wr = raw.get("win_rate", raw.get("winRate", raw.get("wr")))
    if wr is not None:
        try:
            wrval = float(wr)
            return min(wrval, 1.0) if wrval <= 1.0 else min(wrval / 100.0, 1.0)
        except (ValueError, TypeError):
            pass

    # Fallback: sharpe ratio as confidence proxy (Sharpe > 2 = high confidence)
    sharpe = raw.get("sharpe", raw.get("sharpe_ratio"))
    if sharpe is not None:
        try:
            sv = float(sharpe)
            if sv > 0:
                return min(0.90, 0.40 + sv * 0.15)
        except (ValueError, TypeError):
            pass

    return 0.0


# ── ML enrichment: skyrocket, winner patterns, precursors, momentum ──


def _load_ml_enrichment_data() -> dict:
    """Load ML scanner outputs for pick enrichment. Returns dict of loaded data; missing files are skipped."""
    ml_data = {}

    # a) Skyrocket alerts — keyed by normalized symbol
    skyrocket_path = ROOT / "skyrocket_detector" / "data" / "alerts.json"
    try:
        if skyrocket_path.exists():
            raw = json.loads(skyrocket_path.read_text(encoding="utf-8", errors="replace"))
            alerts = raw.get("alerts", []) if isinstance(raw, dict) else raw
            ml_data["skyrocket"] = {}
            for alert in alerts:
                sym = _normalize_symbol(alert.get("symbol", ""))
                prob = float(alert.get("probability", 0))
                if sym and prob >= 0.65:
                    ml_data["skyrocket"][sym] = {
                        "probability": round(prob, 4),
                        "tp_pct": alert.get("tp_pct"),
                        "timestamp": alert.get("timestamp", ""),
                    }
            log.info(
                "ML enrichment: loaded %d skyrocket alerts (prob >= 0.65)",
                len(ml_data["skyrocket"]),
            )
    except Exception as e:
        log.warning("ML enrichment: skyrocket load failed: %s", e)

    # b) Winner patterns — look for most_frequent_winners list
    winner_path = ROOT / "alpha_engine" / "data" / "winner_patterns.json"
    try:
        if winner_path.exists():
            raw = json.loads(winner_path.read_text(encoding="utf-8", errors="replace"))
            winners = set()
            # Handle both list and dict formats
            if isinstance(raw, dict):
                for sym in raw.get("most_frequent_winners", []):
                    winners.add(_normalize_symbol(str(sym)))
            elif isinstance(raw, list):
                for item in raw:
                    if isinstance(item, str):
                        winners.add(_normalize_symbol(item))
                    elif isinstance(item, dict):
                        winners.add(_normalize_symbol(item.get("symbol", "")))
            ml_data["winners"] = winners
            log.info("ML enrichment: loaded %d winner pattern symbols", len(winners))
    except Exception as e:
        log.warning("ML enrichment: winner_patterns load failed: %s", e)

    # c) Precursor picks — keyed by normalized symbol, filter by precursor_score >= 4
    precursor_path = ROOT / "alpha_engine" / "data" / "precursor_picks.json"
    try:
        if precursor_path.exists():
            raw = json.loads(precursor_path.read_text(encoding="utf-8", errors="replace"))
            picks = raw if isinstance(raw, list) else raw.get("picks", [])
            ml_data["precursors"] = {}
            for p in picks:
                sym = _normalize_symbol(p.get("symbol", ""))
                score = float(p.get("precursor_score", p.get("score", 0)) or 0)
                if sym and score >= 4:
                    ml_data["precursors"][sym] = {
                        "score": score,
                        "reason": p.get("precursor_reason", ""),
                    }
            log.info(
                "ML enrichment: loaded %d precursor symbols (score >= 4)",
                len(ml_data["precursors"]),
            )
    except Exception as e:
        log.warning("ML enrichment: precursor_picks load failed: %s", e)

    # d) Momentum picks — active pumping symbols (status == OPEN)
    momentum_path = ROOT / "alpha_engine" / "data" / "momentum_picks.json"
    try:
        if momentum_path.exists():
            raw = json.loads(momentum_path.read_text(encoding="utf-8", errors="replace"))
            picks = raw if isinstance(raw, list) else raw.get("picks", [])
            ml_data["momentum"] = set()
            for p in picks:
                status = (p.get("status") or "").upper()
                if status == "OPEN":
                    sym = _normalize_symbol(p.get("symbol", ""))
                    if sym:
                        ml_data["momentum"].add(sym)
            log.info(
                "ML enrichment: loaded %d actively pumping momentum symbols",
                len(ml_data["momentum"]),
            )
    except Exception as e:
        log.warning("ML enrichment: momentum_picks load failed: %s", e)

    return ml_data


def _enrich_picks_with_ml(picks: list, ml_data: dict) -> None:
    """Add ML bonus scores to picks in-place. Caps total ML bonus at +10 per pick."""
    if not ml_data:
        return

    skyrocket = ml_data.get("skyrocket", {})
    winners = ml_data.get("winners", set())
    precursors = ml_data.get("precursors", {})
    momentum = ml_data.get("momentum", set())

    enriched_count = 0
    for pick in picks:
        sym = _normalize_symbol(pick.get("symbol", ""))
        if not sym:
            continue

        ml_bonus = 0
        ml_enrichment = {}

        # a) Skyrocket potential: +5
        if sym in skyrocket:
            ml_bonus += 5
            pick["skyrocket_potential"] = True
            ml_enrichment["skyrocket"] = {
                "bonus": 5,
                "probability": skyrocket[sym]["probability"],
            }

        # b) Winner pattern: +3
        if sym in winners:
            ml_bonus += 3
            ml_enrichment["winner_pattern"] = {"bonus": 3}

        # c) Precursor match: +3
        if sym in precursors:
            ml_bonus += 3
            pick["precursor_match"] = True
            ml_enrichment["precursor"] = {
                "bonus": 3,
                "score": precursors[sym]["score"],
                "reason": precursors[sym]["reason"],
            }

        # d) Momentum active: +2
        if sym in momentum:
            ml_bonus += 2
            pick["momentum_active"] = True
            ml_enrichment["momentum"] = {"bonus": 2}

        # Cap total ML bonus at +10
        ml_bonus = min(ml_bonus, 10)

        if ml_bonus > 0:
            current_score = _float(pick.get("score", 0))
            pick["score"] = round(current_score + ml_bonus, 2)
            ml_enrichment["total_bonus"] = ml_bonus
            pick["ml_enrichment"] = ml_enrichment
            enriched_count += 1

    log.info(
        "ML enrichment: enhanced %d/%d picks with ML bonuses",
        enriched_count,
        len(picks),
    )


_TV_EDGE_REGISTRY_PATH = ROOT / "audit_dashboard" / "data" / "tv_crypto_edge_registry.json"


def _infer_tv_mcp_strategy(strategy_name: str):
    """Map pick strategy label to tradingview-mcp built-in id (substring match)."""
    if not strategy_name:
        return None
    s = str(strategy_name).lower().replace("-", "_")
    for token in ("ema_cross", "bollinger", "supertrend", "donchian", "macd", "rsi"):
        if token in s:
            return token
    if "connors" in s and "rsi" in s:
        return "rsi"
    if "bb" in s or "bands" in s:
        return "bollinger"
    return None


def _load_tv_edge_registry():
    """Load Yahoo 2y / 1d rule backtest edge registry (tools/build_tv_crypto_edge_registry.py)."""
    path = _TV_EDGE_REGISTRY_PATH
    if not path.exists():
        log.info(
            "TV edge registry missing (%s); run tools/build_tv_crypto_edge_registry.py",
            path,
        )
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        log.warning("TV edge registry load failed: %s", e)
        return None


def _enrich_picks_with_tv_edge(picks: list, registry: dict) -> None:
    """Boost pick scores from real backtest edge (symbol + strategy vs buy-hold, walk-forward)."""
    by_sym = registry.get("by_symbol")
    if not isinstance(by_sym, dict) or not by_sym:
        return

    enriched = 0
    for pick in picks:
        sym = _normalize_symbol(pick.get("symbol", "") or "")
        if not sym or sym not in by_sym:
            continue

        pack = by_sym[sym]
        by_s = pack.get("by_strategy") or {}
        if not isinstance(by_s, dict):
            continue

        mcp = _infer_tv_mcp_strategy(str(pick.get("strategy") or "").strip())
        if not mcp or mcp not in by_s:
            continue

        row = by_s[mcp]
        if not isinstance(row, dict):
            continue

        edge = float(row.get("edge_0_1") or 0)
        edge = max(0.0, min(1.0, edge))

        bonus = round(8.0 * edge, 2)
        d = str(pick.get("direction") or "").upper()
        if d == "SHORT":
            bonus = round(bonus * 0.25, 2)

        base = _float(pick.get("score", 0))
        pick["score"] = round(base + bonus, 2)
        pick["tv_edge_score"] = round(edge, 4)
        pick["tv_edge_bonus"] = bonus
        pick["tv_edge_meta"] = {
            "mcp_strategy": mcp,
            "vs_bnh_pct": row.get("vs_bnh_pct"),
            "wf_verdict_class": row.get("wf_verdict_class"),
            "period": registry.get("period"),
            "interval": registry.get("interval"),
        }
        enriched += 1

    log.info("TV edge enrichment: score boost on %d/%d picks", enriched, len(picks))


def _compute_data_freshness(active_picks_path: Path) -> dict:
    """Compute data freshness metadata for the payload."""
    now = datetime.now(timezone.utc)
    freshness = {
        "last_dashboard_build": now.isoformat(),
        "last_alpha_scan": None,
        "stale_warning": False,
    }

    try:
        if active_picks_path.exists():
            # Use file modification time as the scan timestamp
            mtime = active_picks_path.stat().st_mtime
            scan_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
            freshness["last_alpha_scan"] = scan_dt.isoformat()

            # Also try to extract most recent scan_timestamp from the picks themselves
            raw = _load_json_resilient(active_picks_path)
            picks = raw if isinstance(raw, list) else raw.get("picks", [])
            latest_ts = None
            for p in picks:
                ts = p.get("scan_timestamp", "")
                if ts and (latest_ts is None or ts > latest_ts):
                    latest_ts = ts
            if latest_ts:
                freshness["last_alpha_scan"] = latest_ts
                try:
                    # Parse the ISO timestamp to check staleness
                    scan_dt = datetime.fromisoformat(latest_ts.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            # Stale if more than 2 hours old
            age_hours = (now - scan_dt).total_seconds() / 3600
            freshness["stale_warning"] = age_hours > 2.0
            freshness["age_hours"] = round(age_hours, 1)
    except Exception as e:
        log.warning("Data freshness check failed: %s", e)
        freshness["stale_warning"] = True

    return freshness


# ── Asset class derivation ──

_CRYPTO_SUFFIXES = ("USDT", "BTC", "ETH", "BUSD", "USDC", "USD")
_FOREX_PREFIXES = ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD")
_KNOWN_CRYPTO = {
    "BTC",
    "ETH",
    "SOL",
    "DOGE",
    "XRP",
    "ADA",
    "AVAX",
    "DOT",
    "LINK",
    "MATIC",
    "UNI",
    "AAVE",
    "SHIB",
    "PEPE",
    "ARB",
    "OP",
}
_KNOWN_EQUITY = {
    # Indices & ETFs
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VEU", "VWO", "ARKK", "XLF", "XLE", "XLK", "XLV", "XLP", "XLY", "XLI", "XLB", "XLU", "XLRE", "XLC",
    "GLD", "SLV", "USO", "TLT", "IEF", "SHY", "VIX", "UVXY", "VIXY", "SVXY", "SQQQ", "TQQQ", "SOXX", "SOXL", "SOXS", "SMH",
    # Leveraged 3x bull/bear pairs (tactical trend-following only)
    "SPXL", "SPXS", "UPRO", "SPXU", "TNA", "TZA", "UDOW", "SDOW",
    "FAS", "FAZ", "ERX", "ERY", "LABU", "LABD", "CURE", "DRN", "DRV",
    "DPST", "WDRW", "RETL", "NAIL",
    # 2x commodity leveraged
    "NUGT", "DUST", "JNUG", "JDST", "GUSH", "DRIP",
    # International leveraged
    "YINN", "YANG", "EDC", "EDZ",
    # Tech / Magnificent 7
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "AMD", "NFLX", "AVGO", "ORCL", "CRM", "ADBE", "CSCO", "IBM", "TXN", "QCOM", "INTC", "MU", "AMAT", "LRCX", "ADI", "KLAC", "SNPS", "CDNS", "PANW", "FTNT", "CRWD", "PLTR", "SNOW", "U", "SHOP", "SE", "TEAM", "SQ", "PYPL", "ABNB", "UBER", "LYFT", "DASH", "MELI", "PDD", "JD", "BABA", "BIDU", "Tencent",
    # Finance
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BRK.B", "BRK.A", "V", "MA", "AXP", "PYPL", "BLK", "BX", "KKR", "APO", "SCHW", "TD", "RY", "BMO", "HSBC", "UBS",
    # Healthcare
    "JNJ", "PFE", "LLY", "ABBV", "UNH", "MRK", "TMO", "ABT", "DHR", "BMY", "AMGN", "GILD", "VRTX", "ISRG", "SYK", "ZTS", "REGN", "ELV", "CI", "CVS", "HCA", "MCK", "ABC", "BIIB", "BSX", "MDT",
    # Energy / Commodities
    "XOM", "CVX", "COP", "SLB", "HAL", "EOG", "PXD", "MPC", "PSX", "VLO", "OXY", "HES", "DVN", "FCX", "NEM", "NUE", "STLD", "AA", "ALB",
    # Industrials / Aerospace
    "BA", "LMT", "RTX", "NOC", "GD", "GE", "HON", "MMM", "CAT", "DE", "UNP", "FDX", "UPS", "WM", "RSG", "ITW", "ETN", "PH", "EMR", "CP", "CNI",
    # Consumer / Retail
    "WMT", "COST", "TGT", "HD", "LOW", "NKE", "SBUX", "MCD", "PEP", "KO", "PG", "PM", "MO", "EL", "CL", "KMB", "GIS", "K", "MDLZ", "TJX", "ROST", "MAR", "HLT", "LVS", "WYNN", "BKNG", "EXPE",
    # Communications
    "T", "VZ", "TMUS", "CMCSA", "CHTR", "DIS", "PARA", "WBD", "NFLX", "SONY",
    # Crypto-Linked
    "COIN", "MSTR", "MARA", "RIOT", "CLSK", "BITF", "HUT", "CAN", "WULF",
    # Re-added from previous set for safety
    "GME", "AMC", "PARA", "WBD", "RIVN", "NIO", "SOFI", "BEAT",
}
_COMMODITY_ROOTS = {
    "CL",
    "GC",
    "HG",
    "NG",
    "SI",
    "PL",
    "PA",
    "ZC",
    "ZW",
    "ZS",
    "ZM",
    "ZL",
    "KE",
    "LE",
    "HE",
    "KC",
    "CC",
    "SB",
    "CT",
    "OJ",
    "RB",
    "HO",
    "BZ",
    "CO",
    "LB",
    "BO",
    "OJ",
}
_INDEX_FUTURES_ROOTS = {
    "ES",
    "NQ",
    "YM",
    "RTY",
    "MES",
    "MNQ",
    "MYM",
    "M2K",
    "VX",
    "DX",
    "ZN",
    "ZB",
    "ZT",
    "ZF",
    "6E",
    "6B",
    "6J",
    "6A",
    "6C",
    "6S",
}
# Per research/21 (peer w03yqel9): the `"meme": "CRYPTO"` hint was
# hardcoded, bypassing the `ASSET_CLASS_MAP_MEME_TO_CRYPTO` env flag
# convention. Result: 174 memecoin picks (49x DOGE-USD, 12x WIFUSDT,
# 9x SHIBUSDT, 4x BONK, 3x PENGU) inflated the CRYPTO tile cosmetically.
# Per research/24, removing them does NOT change CRYPTO MaxDD materially
# (memes 2.4% of n, per-pick WR 46.67%) — but the dashboard tile still
# shows wrong volume. Default ON for back-compat. Set the env var to
# "0" to unmap memes (they will then fall through symbol/hint heuristics
# in `_derive_asset_class` rather than being short-circuited to CRYPTO
# by category="meme" alone).
_MEME_TO_CRYPTO = os.environ.get("ASSET_CLASS_MAP_MEME_TO_CRYPTO", "1") == "1"

_ASSET_CLASS_HINTS = {
    "crypto": "CRYPTO",
    "cryptocurrency": "CRYPTO",
    "coin": "CRYPTO",
    "token": "CRYPTO",
    **({"meme": "CRYPTO"} if _MEME_TO_CRYPTO else {}),
    "forex": "FOREX",
    "fx": "FOREX",
    "currency": "FOREX",
    "currencies": "FOREX",
    "equity": "EQUITY",
    "stock": "EQUITY",
    "stocks": "EQUITY",
    "share": "EQUITY",
    "etf": "ETF",
    "bond": "BOND",
    "bonds": "BOND",
    "futures": "FUTURES",
    "future": "FUTURES",
    "commodity": "COMMODITY",
    "commodities": "COMMODITY",
    "index": "FUTURES",
    "penny": "EQUITY",
}


def _compact_symbol(symbol: str) -> str:
    return (
        str(symbol).upper().strip().replace("-", "").replace("/", "").replace("_", "")
    )


def _looks_like_quote_symbol(symbol: str) -> bool:
    text = str(symbol or "").strip().upper()
    if not text:
        return False
    if any(ch.isspace() for ch in text):
        return False
    if len(text) > 24:
        return False
    return all(ch.isalnum() or ch in {"=", "^", ".", "_", "-"} for ch in text)


def _normalize_asset_class_hint(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    compact = text.replace("-", "_").replace(" ", "_")
    if compact in _ASSET_CLASS_HINTS:
        return _ASSET_CLASS_HINTS[compact]
    for needle, asset_class in _ASSET_CLASS_HINTS.items():
        if needle in compact:
            return asset_class
    return None


def _derive_asset_class(
    symbol: str, raw: dict | None = None, source_system: str = "", strategy: str = ""
) -> str:
    raw = raw if isinstance(raw, dict) else {}
    raw_symbol = str(symbol or "").strip().upper()
    compact_symbol = _compact_symbol(symbol)
    stripped_symbol = compact_symbol
    is_explicit_futures_contract = raw_symbol.endswith("=F") or compact_symbol.endswith(
        "=F"
    )

    # 2026-05-16: Additive contract_type tag (from alpha_engine/contract_type.py)
    # takes precedence for true futures. This makes the FUTURES tile actually
    # populate (index/rates/currency futures) without breaking historical
    # COMMODITY numbers for energy/metal/grain =F symbols.
    # See tools/swarm_v2/_task_futures_tile_from_contract_type.md.
    _ct = str(raw.get("contract_type") or "").strip().lower()
    if _ct in ("index_future", "rates_future", "currency_future"):
        return "FUTURES"

    # Strip common venue suffixes before applying the symbol heuristics.
    for suffix in ("=X", "=F", ".TO", ".L", ".AX"):
        if stripped_symbol.endswith(suffix):
            stripped_symbol = stripped_symbol[: -len(suffix)]
            break

    # 1. Unambiguous crypto symbols trump wrong upstream category/asset_class (common JSON bug).
    def _symbol_strongly_crypto(stripped: str) -> bool:
        if not stripped:
            return False
        if stripped in ("XAUUSD", "XAGUSD", "XPDUSD", "XPTUSD"):
            return False
        # Forex pairs suffixed with USDT/USDC are NOT crypto (e.g. EURUSDT, GBPUSDT)
        _fx_bases = ("EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "SEK", "NOK",
                     "SGD", "HKD", "MXN", "ZAR", "TRY", "INR", "BRL", "KRW")
        for _fb in _fx_bases:
            if stripped.startswith(_fb) and any(stripped.endswith(sfx) for sfx in ("USDT", "USDC", "BUSD", "USD")):
                return False
        if any(stripped.endswith(sfx) for sfx in ("USDT", "USDC", "BUSD")):
            return True
        if not stripped.endswith("USD") or len(stripped) < 6:
            return False
        if len(stripped) == 6:
            b3, q3 = stripped[:3], stripped[3:6]
            if b3 in _FOREX_PREFIXES and q3 in _FOREX_PREFIXES:
                return False
            return True
        return True

    if _symbol_strongly_crypto(stripped_symbol):
        return "CRYPTO"

    # 1b. Unambiguous forex/commodity: =X or =F suffix overrides upstream hints.
    # Upstream data often mislabels these (e.g. AUDJPY=X tagged as "crypto").
    if raw_symbol.endswith("=X") and len(stripped_symbol) == 6:
        _b3, _q3 = stripped_symbol[:3], stripped_symbol[3:6]
        if _b3 in _FOREX_PREFIXES and _q3 in _FOREX_PREFIXES:
            return "FOREX"
    if is_explicit_futures_contract:
        # Per research/21: ZN=F (10y Treasury futures) was being mislabeled BOND
        # because it fell through to the hint-key lookup which picked up
        # `category="bond"` from upstream metadata. Fix: =F is unambiguously
        # futures-asset-class. Distinguish only between COMMODITY (oil/gold/grain)
        # and FUTURES (index/Treasury); never let upstream hints flip it to BOND.
        #
        # 2026-05-15 exception: if the raw pick was explicitly emitted by our own
        # futures strategies (category="futures" or asset_class="futures" in the
        # payload), honour that intent even for commodity-root symbols (GC, SI,
        # HG).  Background: futures_vol_regime_breakout targets GC=F and SI=F as
        # FUTURES picks (Donchian/ATR breakout strategy), but the COMMODITY_ROOTS
        # heuristic was silently redirecting them to the COMMODITY tile, keeping
        # the FUTURES tile permanently starved.  External metadata (category="bond"
        # from yfinance) is explicitly NOT honoured here — only our own strategy
        # output is.  The guard `category_hint in ("futures", "future")` prevents
        # upstream metadata from abusing this escape hatch.
        _explicit_futures_hint = False
        for _hk in ("category", "asset_class", "assetClass"):
            _hv = str(raw.get(_hk, "") or "").strip().lower()
            if _hv in ("futures", "future"):
                _explicit_futures_hint = True
                break
        _fr = stripped_symbol[:2]
        if _fr in _COMMODITY_ROOTS and not _explicit_futures_hint:
            return "COMMODITY"
        if _fr in _COMMODITY_ROOTS and _explicit_futures_hint:
            return "FUTURES"
        if _fr in _INDEX_FUTURES_ROOTS:
            return "FUTURES"
        # Unknown =F root → still FUTURES (never BOND/EQUITY/ETF — =F is unambiguous)
        return "FUTURES"

    # 1c. Hard-bond symbols (TLT/IEF/SHY/etc.) trump upstream hints.
    # Per research/21: bond ETFs were being labeled ETF in 5+ rows because
    # hand-stamped `category="etf"` beat the BOND_SYMBOLS lookup (BOND_SYMBOLS
    # was checked AFTER the hint loop). Fix: known bond tickers always classify
    # as BOND regardless of category metadata. The alpha_engine.asset_class
    # canonical set is the source of truth — imported at module top
    # (cross-AI PR review 2026-04-28; was per-call try/except before).
    if stripped_symbol in _AC_BOND_SYMBOLS:
        return "BOND"

    # 2. Explicit hints from the raw payload (after symbol-based crypto lock-in).
    hint_keys = (
        "asset_class",
        "assetClass",
        "category",
        "asset_category",
        "instrument_class",
        "asset_type",
        "portfolio_type",
        "type_label",
        "market",
        "instrument_type",
    )
    for key in hint_keys:
        hinted = _normalize_asset_class_hint(raw.get(key))
        if hinted:
            return hinted

    if " VS " in raw_symbol:
        return "SPORTS"

    if raw.get("coin_id") or raw.get("coinId") or raw.get("token_id"):
        return "CRYPTO"

    hint_blob = " ".join(
        str(v).lower()
        for v in (
            source_system,
            strategy or raw.get("strategy", ""),
            raw.get("source", ""),
            raw.get("source_system", ""),
            raw.get("name", ""),
            raw.get("coin_id", ""),
            raw.get("source_systems", ""),
            raw.get("agreeing_systems", ""),
            raw.get("source_strategies", ""),
            raw.get("confluence_strategies", ""),
        )
        if v
    )

    # 3. Hard symbol matches — check ETF and BOND BEFORE equity (they overlap).
    #    Uses alpha_engine.asset_class canonical sets imported at module top
    #    (_AC_BOND_SYMBOLS / _AC_ETF_SYMBOLS) to avoid classification drift.
    #    Per cross-AI PR review (2026-04-28) the per-call import was hoisted.
    if stripped_symbol in ("DXY",):
        return "FUTURES"
    if stripped_symbol in ("XAUUSD", "XAGUSD"):
        return "COMMODITY"
    if stripped_symbol in _AC_BOND_SYMBOLS:
        return "BOND"
    if stripped_symbol in _AC_ETF_SYMBOLS:
        return "ETF"
    if stripped_symbol in _KNOWN_EQUITY:
        return "EQUITY"
    # 6-char commodity / forex before *USD crypto suffix (EURUSD is forex, not crypto)
    if len(stripped_symbol) >= 6:
        base, quote = stripped_symbol[:3], stripped_symbol[3:6]
        if base in {"XAU", "XAG", "XPD", "XPT"}:
            return "COMMODITY"
        if base in _FOREX_PREFIXES and quote in _FOREX_PREFIXES:
            return "FOREX"
    if any(stripped_symbol.endswith(sfx) for sfx in _CRYPTO_SUFFIXES):
        return "CRYPTO"
    if stripped_symbol in _KNOWN_CRYPTO:
        return "CRYPTO"

    # Futures roots like CO / HO / SI overlap with legitimate equity and crypto
    # tickers, so only treat them as futures when the contract or context is explicit.
    futures_root = stripped_symbol[:2]
    if futures_root in _COMMODITY_ROOTS and (
        is_explicit_futures_contract
        or any(
            token in hint_blob
            for token in ("futures", "future", "commodity", "commod", "cta", "cot")
        )
    ):
        return "COMMODITY"
    if is_explicit_futures_contract or futures_root in _INDEX_FUTURES_ROOTS:
        return "FUTURES"

    # 4. Source/strategy hints disambiguate plain tickers like TAO, XMR, FET.
    if any(token in hint_blob for token in ("forex", "fx", "oanda", "myfxbook")):
        return "FOREX"
    if any(token in hint_blob for token in ("commodity", "commod")):
        return "COMMODITY"
    if any(token in hint_blob for token in ("futures", "future", "cta", "cot")):
        return "FUTURES"
    if any(
        token in hint_blob
        for token in (
            "crypto",
            "copy_trader",
            "copy_hl",
            "clone_hl",
            "whale",
            "smart_money",
            "coinglass",
            "claude_gainer",
            "crypto_signal",
            "crypto_ml",
            "binance",
            "rapid_fire",
            "genome",
        )
    ):
        return "CRYPTO"

    if any(token in hint_blob for token in ("stock", "equity", "etf", "goldmine", "portfolio")):
        return "EQUITY"
    if any(
        token in hint_blob
        for token in (
            "equity",
            "stock",
            "stocks",
            "earnings",
            "analyst",
            "penny",
            "dividend",
            "sector",
        )
    ):
        return "EQUITY"

    # Default to equity only after all more-specific evidence failed.
    return "EQUITY"


def _coerce_asset_class(p: dict) -> str:
    """Final UNKNOWN-trap: re-derive when stamped value is empty / 'UNKNOWN' / 'NONE'.

    Some upstream paths (regime_terminal, ad-hoc importers) set
    asset_class='UNKNOWN' before _normalize_pick runs. This trap forces a
    canonical re-derive via _derive_asset_class so 'stocks' category → EQUITY,
    USDT-quoted symbols → CRYPTO, =X → FOREX, =F → COMMODITY/FUTURES, etc.

    Per reports/DASHBOARD_3_ISSUES_2026_05_03.md §3.3 — additive, runs only
    when the stamped value is unusable; otherwise returns the existing
    upstream label unchanged.
    """
    if not isinstance(p, dict):
        return "UNKNOWN"
    raw_ac = str(p.get("asset_class") or "").strip().upper()
    if raw_ac and raw_ac not in ("UNKNOWN", "NONE"):
        return raw_ac
    cat = str(p.get("category") or "").strip().upper()
    if cat and cat != "UNKNOWN":
        # Re-run through derivation with full pick context.
        return _derive_asset_class(
            symbol=p.get("symbol") or "",
            raw=p,
            source_system=str(p.get("source_system") or ""),
            strategy=str(p.get("strategy") or ""),
        )
    # No category either — try symbol-only derivation as a last resort.
    sym = str(p.get("symbol") or "").strip()
    if sym:
        return _derive_asset_class(
            symbol=sym,
            raw=p,
            source_system=str(p.get("source_system") or ""),
            strategy=str(p.get("strategy") or ""),
        )
    return "UNKNOWN"


# ── JSON Pick Sources (skip mirrors/deploy copies) ──

JSON_PICK_SOURCES = [
    # (system_name, active_path_relative, closed_path_relative)
    (
        "alpha_engine",
        "alpha_engine/data/active_picks.json",
        "alpha_engine/data/closed_picks.json",
    ),
    (
        "battleground",
        "battleground/data/active_picks.json",
        "battleground/data/closed_picks.json",
    ),
    ("mercury2", "mercury2/data/active_picks.json", "mercury2/data/closed_picks.json"),
    (
        "paper_trading",
        "paper_trading/data/active_picks.json",
        "paper_trading/data/closed_picks.json",
    ),
    (
        "ml_bg_system_a",
        "ml_battleground/system_a_filter/data/active_picks.json",
        "ml_battleground/system_a_filter/data/closed_picks.json",
    ),
    (
        "ml_bg_system_b",
        "ml_battleground/system_b_regime/data/active_picks.json",
        "ml_battleground/system_b_regime/data/closed_picks.json",
    ),
    (
        "ml_bg_system_c",
        "ml_battleground/system_c_deeplearn/data/active_picks.json",
        "ml_battleground/system_c_deeplearn/data/closed_picks.json",
    ),
    (
        "ml_bg_system_d",
        "ml_battleground/system_d_carry/data/active_picks.json",
        "ml_battleground/system_d_carry/data/closed_picks.json",
    ),
    (
        "ml_bg_system_e",
        "ml_battleground/system_e_momentum/data/active_picks.json",
        "ml_battleground/system_e_momentum/data/closed_picks.json",
    ),
    (
        "ml_bg_system_f",
        "ml_battleground/system_f_clawsofdoom/data/active_picks.json",
        "ml_battleground/system_f_clawsofdoom/data/closed_picks.json",
    ),
    (
        "ml_bg_ensemble",
        "ml_battleground/ensemble_data/active_picks.json",
        "ml_battleground/ensemble_data/closed_picks.json",
    ),
    (
        "breakout_a_sr",
        "breakout_arena/approach_a_sr_breakout/data/active_picks.json",
        "breakout_arena/approach_a_sr_breakout/data/closed_picks.json",
    ),
    (
        "breakout_b_ml",
        "breakout_arena/approach_b_ml_breakout/data/active_picks.json",
        "breakout_arena/approach_b_ml_breakout/data/closed_picks.json",
    ),
    (
        "breakout_c_spike",
        "breakout_arena/approach_c_spike_reverse/data/active_picks.json",
        "breakout_arena/approach_c_spike_reverse/data/closed_picks.json",
    ),
    (
        "crypto_signal_engine",
        "crypto_signal_engine/data/active_picks.json",
        "crypto_signal_engine/data/closed_picks.json",
    ),
    ("coinglass", "coinglass_strategies/data/active_picks.json", None),
    ("crypto_ml_edge", "crypto_ml_edge/data/active_picks.json", None),
    ("rl_agent", "rl_agent/data/active_picks.json", "rl_agent/data/closed_picks.json"),
    ("genome", "genome/data/universal_picks.json", None),
    # ── DARWIN ENGINE DNA Evolution Systems ──
    ("genetic_programmer", "genome/data/gp_active_picks.json", None),
    ("audit_ensemble", "genome/data/ae_active_picks.json", None),
    ("mape_evolver", "genome/data/mape_active_picks.json", None),
    ("ensemble_evolver", "genome/data/ensemble_active_picks.json", None),
    ("neat_neural", "genome/data/neat_active_picks.json", None),
    ("hyperparam_dna", "genome/data/hyperparam_active_picks.json", None),
    ("failure_evolver", "genome/data/failure_evolved_picks.json", None),
    ("momentum_evolver", "genome/data/momentum_active_picks.json", None),
    ("multitf_evolver", "genome/data/multitf_active_picks.json", None),
    ("contrarian_evolver", "genome/data/contrarian_active_picks.json", None),
    ("macd_dna_mutations", "genome/data/macd_mutation_picks.json", None),
    ("mutation_lab", "genome/data/mutation_lab_picks.json", None),
    ("mega_strategies", "alpha_engine/data/mega_strategy_picks.json", None),
    ("pumpwatch_mutations", "genome/data/pumpwatch_mutation_picks.json", None),
    ("signal_engine_mutations", "genome/data/signal_engine_mutation_picks.json", None),
    ("dna_winner_picks", "genome/data/dna_winner_picks.json", None),
    ("battleground_mutations", "genome/data/battleground_mutation_picks.json", None),
    # ── Revival systems (stale-system reviver generates picks for dormant systems) ──
    ("revival_all", "genome/data/revival_all_picks.json", None),
    ("revival_dormant_strategies", "genome/data/revival_dormant_strategies_picks.json", None),
    ("revival_battleground", "genome/data/revival_battleground_picks.json", None),
    ("revival_breakout_a", "genome/data/revival_breakout_a_pure_sr_picks.json", None),
    ("revival_breakout_b", "genome/data/revival_breakout_b_ml_picks.json", None),
    (
        "revival_signal_engine",
        "genome/data/revival_crypto_signal_engine_picks.json",
        None,
    ),
    ("revival_kimi", "genome/data/revival_kimi_riseoftheclaw_picks.json", None),
    ("revival_mercury2", "genome/data/revival_mercury2_picks.json", None),
    ("revival_paper_trading", "genome/data/revival_paper_trading_picks.json", None),
    # Extra revival outputs (revive_stale_systems) + trusted genome + DNA daily mutations
    ("revival_breakout_spike", "genome/data/revival_breakout_spike_picks.json", None),
    ("revival_crypto_gainer_ml", "genome/data/revival_crypto_gainer_ml_picks.json", None),
    ("revival_ml_system_b_regime", "genome/data/revival_ml_system_b_regime_picks.json", None),
    ("revival_ml_system_c_deeplearn", "genome/data/revival_ml_system_c_deeplearn_picks.json", None),
    ("trusted_genome", "genome/data/trusted_genome_picks_live.json", None),
    ("dna_rapid_fire_mutations", "genome/data/rapid_fire_mutation_picks.json", None),
    ("dna_confluence_mutations", "genome/data/confluence_mutation_picks.json", None),
    ("universal_picks", "genome/data/universal_picks.json", None),
    ("predictions", "predictions/data/active_predictions.json", None),
    ("super_signals", "cross_aggregation/data/super_signals.json", None),
    (
        "aggregated_picks",
        None,
        None,
    ),  # populated from consensus_outcomes.json special handler
    # regime_terminal is a regime CLASSIFIER, not a pick system — no TP/SL/entry.
    # Kept for visibility but tagged as informational (no win/loss tracking).
    ("regime_terminal", "regime_terminal/data/active_signals.json", None),
    # kimi handled separately below (special activePicks key + kimi_riseoftheclaw system name)
    # incubator_fwd handled separately below (open_trades key)
    # claude_gainer handled separately below (needs direction=BUY default + tp1_price remap)
    (
        "ml_crypto_pred",
        "ml_crypto_predictor/enhanced_models/live_picks/active_picks.json",
        "ml_crypto_predictor/enhanced_models/live_picks/closed_picks.json",
    ),
    # ── Additional systems wired 2026-03-06 ──
    ("riseoftheclaw", "riseoftheclaw/data/active_picks.json", None),
    ("crypto_gainer_ml", "crypto_gainer_ml/tracker/live_picks.json", None),
    (
        "abc_forward_a",
        "ml_battleground/abc_forward_test/data/approach_a_picks.json",
        None,
    ),
    (
        "abc_forward_b",
        "ml_battleground/abc_forward_test/data/approach_b_picks.json",
        None,
    ),
    (
        "abc_forward_c",
        "ml_battleground/abc_forward_test/data/approach_c_picks.json",
        None,
    ),
    ("fc_crypto_pro", "data/fc_crypto_pro_picks.json", None),
    ("aggregated_picks", "data/aggregated_picks.json", None),
    ("signal_aggregator", "signal_aggregator/data/master_picks_tracker.json", None),
    ("kimi_live_signals", "KIMI_RISEOFTHECLAW/data/live_signals_now.json", None),
    ("kimi_signal_tracking", "riseoftheclaw/data/signal_tracking.json", None),
    ("goldmine_unified", "data/goldmine/unified_picks.json", None),
    (
        "incubator_gainer",
        "incubator/agents/claude_code_01/data/gainer_scores_latest.json",
        None,
    ),
    # ── Stock & Multi-Asset systems ──
    # stocks_competition + fast_stocks_competition: loaded by special handlers (line ~1761, ~1770)
    # which correctly route OPEN/WON/LOST statuses. Generic loader would wrongly load all as OPEN.
    # Keep entries with None paths so they appear in "all systems" enumeration.
    ("stocks_competition", None, None),
    ("fast_stocks_competition", None, None),
    ("stocks_crypto_comp", "STOCKS/competition/competition-crypto.json", None),
    ("stocks_forex_comp", "STOCKS/competition/competition-forex.json", None),
    ("stocks_penny_comp", "STOCKS/competition/competition-penny_stocks.json", None),
    ("stocks_meme_comp", "STOCKS/competition/competition-meme_coins.json", None),
    (
        "goldmine_stocks",
        "data/goldmine/stock_picks.json",
        "data/goldmine/closed_trades.json",
    ),
    ("goldmine_meme", "data/goldmine/meme_winners.json", None),
    # ── Rapid Fire (NOW.py) — real-time 1h crypto scanner ──
    (
        "rapid_fire",
        "rapid_fire_data/active_picks.json",
        "rapid_fire_data/now_picks.json",
    ),
    # ── Claude Gainer Short-Term — 1h/4h ML predictor ──
    # NOTE: closed path now wired to short_term_closed.json — populated by resolve_pending_picks_json()
    # in short_term_scanner.py each scan cycle. short_term_picks.json stores all 500+ history picks
    # with outcome field; closed file contains only resolved (TP_HIT/SL_HIT/EXPIRED) picks.
    (
        "claude_gainer_st",
        "claude_gainer_ml/tracker/short_term_active.json",
        "claude_gainer_ml/tracker/short_term_closed.json",
    ),
    # ── QuanEngine — quant prop-strategy scanner ──
    ("quan_engine", "quan_engine/data/active_signals.json", None),
    # ── Meme Scanner & Live Spike Trader (wired 2026-03-14, JSON exports from workflows) ──
    ("meme_scanner", "data/meme_scanner_active.json", None),
    ("live_spike_trader", "data/spike_trader_active.json", None),
    # ── Prop Firm Strategies — specialized prop firm strategies ──
    ("prop_firm_strategies", "audit_trail/data/prop_firm_picks.json", None),
    # ── Alpha Engine FAST — tighter TP/SL, shorter holds for more frequent signals ──
    (
        "alpha_engine_fast",
        "alpha_engine/data/active_picks_fast.json",
        "alpha_engine/data/closed_picks_fast.json",
    ),
    # ── Multi-Asset (forex + equity + crypto institutional scanner) ──
    (
        "multi_asset",
        "multi_asset/data/active_picks.json",
        "multi_asset/data/multi_asset_closed.json",
    ),
    (
        "multi_asset_institutional",
        "multi_asset/data/institutional_picks.json",
        "multi_asset/data/institutional_closed.json",
    ),
    (
        "multi_asset_copytrader",
        "copy_trader_intel/data/multi_asset_picks.json",
        None,
    ),
    (
        "multi_asset_copytrader",
        "copy_trader_intel/data/forex_copytrader_picks.json",
        None,
    ),
    (
        "multi_asset_copytrader",
        "copy_trader_intel/data/stocks_copytrader_picks.json",
        None,
    ),
    (
        "multi_asset_copytrader",
        "copy_trader_intel/data/commodity_copytrader_picks.json",
        None,
    ),
    ("cta_replicator", "copy_trader_intel/data/cta_picks.json", None),
    # Non-Crypto Consensus (forex/equities/commodities with ≥2 independent source agreement)
    ("non_crypto_consensus", "copy_trader_intel/data/non_crypto_consensus_picks.json", None),
    # Non-Crypto Enhanced (consensus picks validated with TA + whale signals)
    ("non_crypto_enhanced", "copy_trader_intel/data/non_crypto_enhanced_picks.json", None),
    # Battleground Incubator (9 strategies: tournament winners, DLinear, spike MACD, etc.)
    ("incubator_battleground", "battleground/data/incubator_signals.json", None),
    # Agreement Alpha (System A+C consensus filter)
    (
        "agreement_alpha",
        "ml_battleground/ensemble_data/agreement_alpha_picks.json",
        None,
    ),
    # Mega Mutation Tournament — walk-forward validated DNA mutations (live tracker)
    # Uses mega_mutation_picks.json (open_picks key) as primary source; active_picks.json is a flat mirror
    (
        "mega_mutation",
        "genome/data/mega_mutation_picks.json",
        "genome/data/closed_picks.json",
    ),
    # ── Added 2026-03-13: Missing sources found in comprehensive audit ──
    ("signal_validation", "signals_database.json", None),
    (
        "ml_crypto_pred_v12",
        "ml_crypto_predictor/enhanced_models/live_picks/archive_v1.2/active_picks.json",
        "ml_crypto_predictor/enhanced_models/live_picks/archive_v1.2/closed_picks.json",
    ),
    # kimi_claw_research picks are frozen paper P/L from Feb 2026 research portfolio.
    # They should NOT count toward forward-tested performance metrics.
    # Marked paper_only=True — see _PAPER_ONLY_SYSTEMS below.
    ("kimi_claw_research", "KIMI_CLAW_RESEARCH_FEB162026/data/active_picks.json", None),
    (
        "deploy_riseoftheclaw",
        "deploy_riseoftheclaw/riseoftheclaw/data/active_picks.json",
        None,
    ),
    ("forward_signals", "incubator/backtest_results/forward_signals.json", None),
    # ── LuxAlgo-Inspired Confluence Filters (RSI Prediction + Breakout + Streak + Vol + SVM) ──
    (
        "luxalgo_filters",
        "battleground/data/luxalgo_active_picks.json",
        "battleground/data/luxalgo_closed_picks.json",
    ),
    # ── ChatGPT Combined v1 (MavilimW + Range Filter + Cyberpunk Analyzer + Volume) ──
    ("chatgpt_combined", "battleground/data/chatgpt_combined_signals.json", None),
    # ── 4 AI Challenge Curators (Round-based picks merged by merge_ai_challenge_picks.py) ──
    (
        "ai_challenge_claude",
        "audit_dashboard/data/ai_challenge_claude_active_picks.json",
        None,
    ),
    (
        "ai_challenge_grok",
        "audit_dashboard/data/ai_challenge_grok_active_picks.json",
        None,
    ),
    (
        "ai_challenge_kimi_moonshot",
        "audit_dashboard/data/ai_challenge_kimi_moonshot_active_picks.json",
        None,
    ),
    (
        "ai_challenge_antigravity",
        "audit_dashboard/data/ai_challenge_antigravity_active_picks.json",
        None,
    ),
    (
        "ai_challenge_mercury",
        "audit_dashboard/data/ai_challenge_mercury_active_picks.json",
        None,
    ),
    (
        "ai_challenge_predictable",
        "audit_dashboard/data/ai_challenge_predictable_active_picks.json",
        None,
    ),
    (
        "ai_challenge_scanner",
        "audit_dashboard/data/ai_challenge_scanner_active_picks.json",
        None,
    ),
    # ── Smart Money Intelligence — Wall Street analyst ratings + insider sentiment for equities ──
    ("smart_money", "smart_money/data/active_picks.json", None),
    # ── Orphaned systems wired 2026-03-18: 12 previously untracked sources ──
    ("kimi_feb172026", "KIMI_FEB172026/data/active_picks.json", None),
    ("conviction_picks", "cross_aggregation/data/conviction_picks.json", None),
    ("momentum_scalp", "genome/data/momentum_scalp_picks.json", None),
    ("asterdex_paper", "trading/data/dashboard_data.json", None),
    ("incubator_pipeline", "alpha_engine/data/incubator_report.json", None),
    ("meta_strategy", "meta_strategy/data/active_picks.json", None),
    ("overnight_mutations", "alpha_engine/data/massive_mutation_results.json", None),
    ("contested_picks", "cross_aggregation/data/contested_picks_tracker.json", None),
    ("buy_now_analysis", "signal_aggregator/data/pick_tracking.json", None),
    ("strategy_health", "strategy_health/data/banned_strategies.json", None),
    ("live_position_monitor", "live_monitor/data/position_state.json", None),
    ("alpha_engine_daily", "alpha_engine/output/latest_picks.json", None),
    # ── Copy Trader Intelligence — Hyperliquid top trader positions (on-chain verified) ──
    (
        "copy_trader_intel",
        "copy_trader_intel/data/active_picks.json",
        "copy_trader_intel/data/closed_trades.json",
    ),
    # ── Copy Trader High-Score: proven edge picks from verified high-WR traders ──
    (
        "copy_trader_highscore",
        "copy_trader_intel/data/highscore_active_picks.json",
        "copy_trader_intel/data/highscore_closed_picks.json",
    ),
    # ── Copy Trader Clones: our reverse-engineered versions (lower confidence until proven) ──
    (
        "copy_trader_clones",
        "copy_trader_intel/data/clone_active_picks.json",
        "copy_trader_intel/data/clone_closed_picks.json",
    ),
    # ── Copy Trader Variations: paper-trading strategy mutations (process-of-elimination tournament) ──
    (
        "copy_trader_variations",
        "copy_trader_intel/data/variation_active_picks.json",
        None,
    ),
    # ── Copy Trader Consensus: 2+ independent traders agree on same symbol+direction (highest conviction) ──
    (
        "copy_trader_consensus",
        "copy_trader_intel/data/consensus_active_picks.json",
        "copy_trader_intel/data/consensus_closed_picks.json",
    ),
    # ── Proven Strategies (backtested, research-backed: RSI-BB, TSMOM, Forex RSI-2) ──
    ("proven_strategies", "proven_strategies/data/proven_strategy_picks.json", None),
    ("funding_rate_arb", "alpha_engine/data/funding_rate_picks.json", None),
    ("btc_breakout", "alpha_engine/data/btc_breakout_picks.json", None),
    # ── Orphaned sources wired 2026-03-26 (data flow audit found 242 picks not reaching dashboard) ──
    ("rocket_scanner", "alpha_engine/data/rocket_picks.json", None),
    ("short_engine", "alpha_engine/data/short_dominant_picks.json", None),
    ("tsmom_strategy", "alpha_engine/data/tsmom_picks.json", None),
    ("bbkc_squeeze", "alpha_engine/data/bbkc_squeeze_picks.json", None),
    ("maplestax_cbc", "alpha_engine/data/maplestax_picks.json", None),
    ("contrarian_consensus", "alpha_engine/data/contrarian_picks.json", None),
    ("inverse_mutations", "alpha_engine/data/inverse_picks.json", None),
    # Leveraged ETF decay-harvest SHORTs (backtest-validated per TESTING_PROTOCOL.MD)
    # B11 fix (2026-05-02): path updated to etf_decay_picks.json — the actual output
    # of alpha_engine/strategies/etf_decay_shorts.py. The legacy leveraged_etf_decay_picks.json
    # was a manually-crafted stub; the script writes etf_decay_picks.json.
    ("leveraged_etf_decay", "alpha_engine/data/etf_decay_picks.json", None),
    # ETF sector rotation — Faber TAA (SPDR XLK/XLF/XLE/XLV/IWM/TLT/HYG, 10-month SMA filter)
    # Opt-in sidecar (B11, 2026-05-01): 14-day shadow run before any gate promotion.
    # Emitter: tools/etf_sector_emitter.py. Workflow: alpha-engine-etf.yml.
    ("etf_sector_rotation", "alpha_engine/data/etf_sector_picks.json", None),
    # BOND scanner — 3 strategies (yield_momentum, duration_rotation, mean_reversion)
    # over 14 BOND symbols (TLT, IEF, SHY, LQD, HYG, AGG, BND, EMB, MUB, etc.).
    # Emitter: alpha_engine/bond_scanner.py:run_bond_scanner(). Workflow:
    # .github/workflows/alpha-engine-bond.yml writes the JSON; this registry
    # entry lets dashboard_generator ingest it. Added 2026-05-12 per
    # reports/asset_class_expansion_2026-05-12.md (BOND n=18 sub-floor; wiring
    # gap was blocking volume ramp).
    ("bond_scanner", "alpha_engine/data/active_picks_bond.json", None),
    # Walk-forward builtins (4h Binance OHLCV; weekly refresh with walk-forward job)
    ("wf_audit_signals", "alpha_engine/data/wf_audit_picks.json", None),
    ("top_gainer_predictor", "alpha_engine/data/top_gainer_predictions.json", None),
    ("polymarket_signals", "copy_trader_intel/data/polymarket_picks.json", None),
    # ── Prediction Market Agents — momentum, whale, Kalshi signals ──
    # consensus_signals.json is handled by a special collector below (field remapping needed).
    # Keep only the explicit PM source files here; do not double-load generic
    # aliases or cross-system consensus ledgers under a PM label.
    (
        "pm_momentum_signals",
        "prediction_market_agents/data/momentum_signals.json",
        None,
    ),
    ("pm_whale_signals", "prediction_market_agents/data/whale_signals.json", None),
    ("pm_kalshi_signals", "prediction_market_agents/data/kalshi_signals.json", None),
    # ── ML Gatekeeper & Consensus (Mercury-validated, Apr 2026) ──
    (
        "ml_gatekeeper",
        "ml_gatekeeper/data/active_picks.json",
        "ml_gatekeeper/data/closed_picks.json",
    ),
    (
        "ml_consensus",
        "ml_consensus/data/active_picks.json",
        "ml_consensus/data/closed_picks.json",
    ),
]

# ── Orphan-emitter wire-up (2026-04-28) ──────────────────────────────────
# bond-agent.yml, etf-agent.yml, futures-agent.yml all emit pick JSONs to
# non_crypto_agent/data/{bond,etf,futures}_picks.json on a daily cron, and
# alpha_engine/outcome_resolver.py writes audit_dashboard/data/forex_futures_picks.json
# on every resolver run — but dashboard_generator.py NEVER read any of them.
# Per reports/asset_class_under_deployment_audit_2026_04_28.md (agent a73a3f8d
# small-N audit), this is the root cause of "small-N for BOND/ETF/FUTURES":
# the picks exist on disk; the dashboard pick-load loop just doesn't see them.
# Behind opt-in env var AUDIT_LOAD_ORPHAN_EMITTERS (default ON — supply, not
# silence). Each entry uses a unique source_system tag prefixed with
# "orphan_emitter_" so downstream filters/strategy stats can disambiguate
# from existing systems. See _normalize_orphan_emitter_pick() for schema
# normalization (asset_class inference, at_issue_trust_tier defaults).
ORPHAN_EMITTER_SOURCES = [
    # (system_name, active_path, closed_path, inferred_asset_class)
    ("orphan_emitter_bond",
     "non_crypto_agent/data/bond_picks.json", None, "BOND"),
    ("orphan_emitter_etf",
     "non_crypto_agent/data/etf_picks.json", None, "EQUITY"),
    ("orphan_emitter_futures",
     "non_crypto_agent/data/futures_picks.json", None, "FUTURES"),
    ("orphan_emitter_forex_futures",
     "audit_dashboard/data/forex_futures_picks.json", None, None),  # picks self-tag asset_class
]
if os.environ.get("AUDIT_LOAD_ORPHAN_EMITTERS", "1") == "1":
    for _sys, _act, _cls, _ac in ORPHAN_EMITTER_SOURCES:
        JSON_PICK_SOURCES.append((_sys, _act, _cls))

# TradingAgents-style consensus emitter (alpha_engine.tradingagents_emitter).
# The emitter is opt-in (TRADINGAGENTS_EMITTER_ENABLED=1) and writes only when
# enabled; an empty / missing JSON file is a no-op for the loader. Registering
# the source unconditionally lets picks surface on /audit the moment the cron
# runs without a separate dashboard-side flag flip. The schema
# `active_picks: [...]` matches the existing `_safe_json` reader contract.
JSON_PICK_SOURCES.append((
    "tradingagents",
    "alpha_engine/data/tradingagents_picks.json",
    None,  # closed picks not yet emitted; outcomes settle via universal resolver
))

# Penny skyrocket detector (alpha_engine/strategies/skyrocket_detector.py).
# Wired by .github/workflows/penny-skyrocket-runner.yml on a daily cron.
# Output schema: { generated_at, strategy, count, picks: [...] } — the
# reader's _extract_picks() already recognizes the `picks` key. Picks emit
# under source_system="skyrocket_detector", strategy="skyrocket_detector",
# asset_class=EQUITY, category="penny", max_hold_days=5 (→ SWING via the
# timeframe classifier). Concept tag for the audit_concepts integration
# (Cursor's plan): concept_family="penny_stock" can be derived from
# category="penny" downstream when the taxonomy helper lands.
JSON_PICK_SOURCES.append((
    "skyrocket_detector",
    "alpha_engine/data/skyrocket_picks.json",
    None,  # closed-pick outcomes settle via universal resolver
))

# UEPS (Universal Equity Picking System) direct feed (B28 2026-05-01).
# Replaces the racy sync_to_active_picks() → active_picks.json path that
# caused UEPS rows to be wiped within ~4h by competing crons (alpha-engine-
# live.yml writes active_picks.json from scratch every hour).  Registering
# here follows the same pattern as tradingagents and skyrocket_detector.
# Schema: { long_picks: [...], swing_picks: [...], short_picks: [...] }
# _extract_picks() handles the multi-list format (concatenates all three).
JSON_PICK_SOURCES.append((
    "ueps",
    "audit_dashboard/data/ueps_picks.json",
    None,  # closed-pick outcomes tracked via universal resolver by pick_type
))

# Penny stock screener (B20 2026-05-02). Emitted daily (weekdays 12:00 UTC)
# by .github/workflows/penny-stock-picks.yml via scripts/penny_stock_picks.py.
# Schema: { top_picks: [...], all_scores: [...], generated_at, date, ... }
# _extract_picks() handles the top_picks key with direction/strategy/asset_class
# normalization so picks surface on /audit without a racy sync step.
JSON_PICK_SOURCES.append((
    "penny_screener",
    "findstocks/portfolio2/data/penny_picks_latest.json",
    None,  # closed-pick outcomes tracked via universal resolver
))

# COT positioning (B7 prereq 2026-05-02).  Emitted by alpha_engine/cot_positioning.py
# when run on the forex-agent cron (CFTC weekly, Fridays ~15:30 ET).
# Schema: { scanner: "cot_positioning", generated_at, picks: [{symbol, direction,
#   strategy, asset_class, timeframe, confidence, pair, signal, percentile, ...}] }
# _extract_picks() applies a content-freshness guard (>14d → []) and normalises the
# legacy {pair, signal} format to the full pick schema.
# _FRESHNESS_REQUIRED_HOURS["cot_positioning"] = 14*24 provides mtime belt-and-suspenders.
# NOTE: The actual "flip to live" step (adding a cron job call to cot_positioning.py in
# forex-agent.yml) belongs in B7 proper, not this prerequisite audit PR.
JSON_PICK_SOURCES.append((
    "cot_positioning",
    "alpha_engine/data/cot_signals.json",
    None,  # no separate closed-pick file; resolved via universal resolver
))

# STOCKSUNIFY2 sibling-repo equity picks (top-7 swarm #1 2026-05-08).
# Pulled daily by .github/workflows/stocksunify2-pull.yml from
# https://github.com/eltonaguiar/STOCKSUNIFY2 main branch and transformed
# by tools/sync_stocksunify2.py into the standard active-picks schema.
# Source repo's `data/daily-stocks.json` schema:
#   { lastUpdated, totalPicks, stocks: [{symbol, rating, algorithm, score,
#     entryPrice, stopLoss, ...}] }
# Sync writes audit_dashboard/data/stocksunify2_active_picks.json with
# normalized fields (symbol, direction=BUY, strategy=<algorithm-slug>,
# source=stocksunify2, asset_class=EQUITY, score, entry_price, stop_loss,
# pick_type=long_term_value).
JSON_PICK_SOURCES.append((
    "stocksunify2",
    "audit_dashboard/data/stocksunify2_active_picks.json",
    None,  # closed-pick outcomes settle via universal resolver
))

# Growth Stock Screener (PR-X 2026-05-12, methodology from starboi-63/growth-stock-screener).
# Daily cron at 14:00 UTC writes EQUITY picks meeting 5-stage filter:
# RS rating >= 90, market cap >= $1B, price >= $10, stage-2 uptrend, revenue growth >= 25% YoY.
JSON_PICK_SOURCES.append((
    "growth_stock_screener",
    "audit_dashboard/data/growth_stock_picks.json",
    None,  # outcomes settle via universal resolver
))

# 20 academically-backed equity/commodity strategies (opt-in sidecar 2026-05-16).
# Emitted by tools/new_strategies_emitter.py (Wire-Up Rule: production caller).
# 10 equity/ETF + 10 commodity strategies; gated through passes_active_gate().
# 14-day shadow validation recommended before gate promotion.
# Guard: NEW_STRATS_RUNNER_ENABLED env var (default "1").
JSON_PICK_SOURCES.append((
    "new_equity_commodity_strategies_20",
    "alpha_engine/data/scanner_output/new_strategies_picks.json",
    None,  # outcomes settle via universal resolver
))

# Commodity carry+momentum double-sort (Miffre/Fuertes 2010, CT=F diversifier, 2026-05-16).
# Emitted by tools/research/commodity_carry_momo.py (--quintile 3, 17-symbol universe).
# Also run in .github/workflows/ab_analysis.yml + audit-dashboard.yml.
# Schema: { strategy_name, generated_at, picks: [{symbol, direction, strategy,
#   source_system, asset_class="COMMODITY", entry_price, confidence, timeframe,
#   status, generated_at, reason}], rows, basket }
# Purpose: diversify COMMODITY PnL away from CT=F (~73% PnL mass) by surfacing
#   non-cotton longs/shorts ranked by 12-1 momentum AND carry proxy.
# Wire-Up Rule status: WIRED (production caller; picks reach dashboard on next run).
# Shadow validation: recommended 14 days before gate promotion.
JSON_PICK_SOURCES.append((
    "commodity_carry_momo",
    "audit_dashboard/data/commodity_carry_momo.json",
    None,  # outcomes settle via universal resolver
))

# Phase-5 hourly refresh picks (Wire-Up Rule compliance 2026-05-16).
# Emitted by alpha_engine/phase5_dashboard_integration.py:load_hourly_picks()
# which reads alpha_engine/data/hourly_refresh_picks.json (schema: {picks:[...]}).
# Picks receive deployment_status=AWAITING_VALIDATION and trust_tier=UNPROVEN
# until quality_gates/system_trust_registry promote them; see enrich_pick_with_metadata().
# The entry here is the production caller that satisfies the Wire-Up Rule; the
# _extract_picks() reader already handles the `picks` key format.
try:
    from alpha_engine.phase5_dashboard_integration import load_hourly_picks as _load_hourly_picks
    _PHASE5_HOURLY_AVAILABLE = True
except ImportError:
    _PHASE5_HOURLY_AVAILABLE = False
    def _load_hourly_picks():
        return []

JSON_PICK_SOURCES.append((
    "phase5_hourly",
    "alpha_engine/data/hourly_refresh_picks.json",
    None,  # closed outcomes settle via universal resolver; validity_hours=1 → EXPIRED in-memory
))

PORTFOLIO_SOURCES = [
    ("paper_trading", "paper_trading/data/portfolios.json"),
    ("kimi_algorithms", "KIMI_RISEOFTHECLAW/data/portfolio_state.json"),
    ("kimi_paper", "KIMI_RISEOFTHECLAW/data/paper_portfolio.json"),
    ("portfolio_tracker", "portfolio_tracker/data/portfolio_metrics.json"),
]

# ── Paper-only systems ──
# These systems contain frozen/paper P&L that should NOT count toward
# forward-tested performance metrics (win rate, trade count, expectancy).
# Picks are still loaded for display but flagged with paper_trade=True.
_PAPER_ONLY_SYSTEMS = {
    "kimi_claw_research",  # Frozen Feb 2026 research portfolio — unrealized paper gains counted as "wins"
}

# ── Hidden/inactive systems ──
# Systems that are genuinely defunct: missing data files with no workflow to
# generate them, or legacy/one-off systems that will never produce new picks.
# Hidden systems are excluded from the dashboard UI to reduce clutter.
# NOTE: Do NOT add systems that are merely temporarily inactive (no picks right
# now but have a running workflow).  Only add truly dead systems.
_HIDDEN_SYSTEMS = {
    "agreement_alpha",  # No data file, no workflow — never wired
    "alpha_engine_daily",  # No data file, no workflow — superseded by alpha_engine
    "kimi_feb172026",  # No data file, no workflow — frozen Feb 17 snapshot, superseded
    "universal_picks",  # Duplicate of genome (same file: genome/data/universal_picks.json)
    "stocks_crypto_comp",  # Competition results format, not tradeable picks
    "stocks_forex_comp",  # Competition results format, not tradeable picks
    "stocks_penny_comp",  # Competition results format, not tradeable picks
    "stocks_meme_comp",  # Competition results format, not tradeable picks
    # ── Retired 2026-04-18 ────────────────────────────────────────────────
    # The 5 LLM-curated AI Challenge tournament systems. The tournament ended
    # at Round 5 on 2026-04-12 and no Round 6 generator exists; the freshness
    # gate already excluded them from consensus, and this entry fully removes
    # them from the dashboard UI so they don't show up as "present but stale".
    # `ai_challenge_predictable` and `ai_challenge_scanner` are NOT hidden —
    # they are auto-regenerated by tools/regenerate_predictable_scanner_picks.py.
    # Re-add if you run a Round 6 LLM tournament.
    "ai_challenge_claude",
    "ai_challenge_grok",
    "ai_challenge_kimi_moonshot",
    "ai_challenge_antigravity",
    "ai_challenge_mercury",
    # ── Retired 2026-04-18 (stale-JSON audit) ────────────────────────────
    # The "revive_stale_systems" orphan outputs: no workflow writes these
    # paths (git grep confirms zero producers in .github/workflows/), all
    # last written 2026-04-11 during a one-off run. Hide from dashboard UI.
    # Re-add to an active workflow if stale-system revival is resumed.
    "revival_all",
    "revival_battleground",
    "revival_breakout_a",
    "revival_breakout_b",
    "revival_breakout_spike",
    "revival_crypto_gainer_ml",
    "revival_dormant_strategies",
    "revival_kimi",
    "revival_mercury2",
    "revival_ml_system_b_regime",
    "revival_ml_system_c_deeplearn",
    "revival_paper_trading",
    "revival_signal_engine",
}

# Systems whose picks require freshness to be trustworthy. If the source file's
# mtime is older than this many hours, the system is treated as stale and its
# picks are skipped entirely (they don't feed consensus or GOLDEN/VERIFIED math).
# This prevents Apr-12 round5 curators from polluting Apr-18+ consensus when the
# tournament hasn't advanced. Add here any system where reading 6-day-old picks
# as "live votes" is actively misleading.
_FRESHNESS_REQUIRED_HOURS = {
    "ai_challenge_claude": 24,
    "ai_challenge_grok": 24,
    "ai_challenge_kimi_moonshot": 24,
    "ai_challenge_antigravity": 24,
    "ai_challenge_mercury": 24,
    "ai_challenge_predictable": 24,
    "ai_challenge_scanner": 24,
    # ── Added 2026-04-18 stale-JSON audit ─────────────────────────────────
    # Systems whose source files have not been rewritten for ≥24h as of the
    # 2026-04-18 audit. Most were last touched 2026-04-11 (≈166h) in a mass
    # commit; underlying GHA workflows either no longer target these paths
    # or silently swallow failures (see HYROTRADER_PIPELINE_FIXES.md pattern).
    # Using a 72h soft cutoff lets them re-engage automatically if a writer
    # produces a fresh file, without corrupting consensus in the meantime.
    "breakout_a_sr": 72,
    "breakout_b_ml": 72,
    "breakout_c_spike": 72,
    "chatgpt_combined": 72,
    "coinglass": 72,
    "contested_picks": 72,
    "contrarian_consensus": 72,
    "contrarian_evolver": 72,
    "copy_trader_clones": 72,
    "copy_trader_highscore": 72,
    "copy_trader_variations": 72,
    "crypto_gainer_ml": 72,
    "crypto_signal_engine": 72,
    "failure_evolver": 72,
    "hyperparam_dna": 72,
    "incubator_battleground": 72,
    "leveraged_etf_decay": 72,
    "macd_dna_mutations": 72,
    "maplestax_cbc": 72,
    "ml_bg_ensemble": 72,
    "ml_bg_system_a": 72,
    "ml_bg_system_b": 72,
    "ml_bg_system_c": 72,
    "ml_bg_system_d": 72,
    "ml_bg_system_e": 72,
    "ml_bg_system_f": 72,
    "ml_consensus": 72,
    "ml_crypto_pred": 72,
    "ml_crypto_pred_v12": 72,
    "ml_gatekeeper": 72,
    "momentum_evolver": 72,
    "multi_asset_institutional": 72,
    "multitf_evolver": 72,
    "neat_neural": 72,
    "paper_trading": 72,
    "prop_firm_strategies": 72,
    "proven_strategies": 72,
    "rl_agent": 72,
    "signal_aggregator": 72,
    "wf_audit_signals": 72,
    # COT positioning: CFTC data is released weekly (Friday ~15:30 ET).
    # Reject cot_signals.json if the file is older than 14 days (2 missed releases).
    # The content-level check in _extract_picks handles the mtime ≠ generated_at
    # divergence case; this mtime guard is belt-and-suspenders.
    "cot_positioning": 14 * 24,
}
_stale_skipped = {}  # module-level counter populated during load, surfaced in summary

# Systems that have NEVER produced data files — skip to avoid noise in logs/stats
_GHOST_SYSTEMS = {
    "meta_strategy",      # FILE MISSING
    "abc_forward_a",
    "abc_forward_b",
    "abc_forward_c",
    "funding_rate_arb",
    "momentum_scalp",
    "pm_momentum_signals",
    "pumpwatch_mutations",
    "strategy_health",
    "live_spike_trader",
    "buy_now_analysis",
    "btc_breakout",
    "bbkc_squeeze",
}


# ── Pick normalization ──

_CLOSED_STATUSES = {
    "closed",
    "resolved",
    "time_exit",
    "expired",
    "tp_hit",
    "sl_hit",
    "trail",
    "max_hold",
    "force_closed",
    "won",
    "lost",
}

# Exit reasons / statuses that indicate a pick auto-expired without any real outcome.
# These should NOT count toward win rate or trade count metrics.
_AUTO_EXPIRED_PATTERNS = {
    "stale",
    "expired",
    "auto",
    "time_exit",
    "max_hold",
    "timed_out",
    "timeout",
}
_NON_PERFORMANCE_EXIT_REASONS = {
    "FORCE_CLOSED_TOXIC",
    "STALE_DATA_NO_PRICE",
    "UNSCORED_CLEANUP",
    "MC_QUALITY_PURGE",
}
_NON_PERFORMANCE_STATUSES = {"KILLED"}
_MIN_REALIZED_PNL_PCT = 0.01
_MULTI_ASSET_BRIDGE_PREFIXES = ("multi_asset_", "cta_")

# pnl_pct sanity check thresholds (Codex finding 2026-04-18: corrupt JPY rows
# from copy_trader feeders had |pnl_pct| up to 2305 while actual entry→exit
# move was < 0.25%. Five such rows alone summed to -4855% PnL and dropped
# forex headline PF from 2.23 to 0.007.)
_PNL_PCT_CORRUPT_MIN_REPORTED = 20.0   # only check rows where |reported| > 20%
_PNL_PCT_CORRUPT_MAX_IMPLIED = 1.0     # implied move must be < 1% to flag
_PNL_PCT_CORRUPT_DIVERGENCE = 10.0     # reported / implied ratio must exceed this (non-JPY)
# 2026-05-03: JPY pairs trade at 2-decimal scale (USDJPY 150.25) vs 4-decimal
# majors (EURUSD 1.0850). Legitimate 5-pip wins compute as +0.0316% implied;
# some feeders report 0.5%-25% pnl_pct on the same outcome → 15-790x divergence
# at the 10x threshold this filter rejected ~258 valid JPY wins, contributing
# to the false FOREX PF 0.27 (verified 2026-05-03 deep-dive). The original
# 2026-04-18 Codex corrupt rows had 9000x+ divergence on JPY pairs, so 50x
# still catches genuine corruption while admitting valid wins.
# Rollback: PNL_PCT_CORRUPT_DIVERGENCE_JPY env var override.
_PNL_PCT_CORRUPT_DIVERGENCE_JPY = 50.0

# Sane per-class price-move ceilings (per single closed trade).
# Forex pairs and bond ETFs cannot move 50%+ in a swing window without the
# row being corrupted (entry or exit price stamped wrong). Crypto can pump
# 100%+ legitimately so it's exempt. Equity is rarely > 50% on a single
# trade window — 50% catches obvious data errors without touching real
# tail outcomes. Used by _pnl_pct_looks_corrupt as a class-aware sanity
# check that catches entry/exit price corruption (a different failure mode
# from the pip-as-percent pnl_pct corruption).
_NON_CRYPTO_MAX_REASONABLE_MOVE_PCT = 50.0

# Even crypto can't realistically have a single-trade entry/exit price ratio
# above ~100x. When entry and exit differ by more than this, the row is
# almost certainly upstream price-stamping corruption (e.g. ZKUSDT entry=9.41
# stamped against exit=0.01542 on the real ZKUSDT price ~$0.015 — that's a
# 612x mismatch and produces a fake -99.84% loss). Bumped to 100x to allow
# for legitimate 100x crypto pumps but reject orders-of-magnitude data errors.
_PRICE_MAGNITUDE_RATIO_CORRUPT = 100.0


def _implied_move_pct(pick: dict) -> float | None:
    """Return signed pnl% implied by (entry, exit, direction), or None if unknown.

    Used as ground truth against the recorded ``pnl_pct`` field. A large
    divergence indicates upstream corruption (e.g. JPY pip-vs-percent confusion
    in copy-trader feeders).
    """
    try:
        entry = float(pick.get("entry_price") or 0)
        exit_price = float(pick.get("exit_price") or 0)
    except (TypeError, ValueError):
        return None
    if entry <= 0 or exit_price <= 0:
        return None
    raw = (exit_price - entry) / entry * 100.0
    direction = str(pick.get("direction", "") or "").upper()
    if direction == "SHORT":
        raw = -raw
    return raw


def _pnl_pct_looks_corrupt(pick: dict) -> bool:
    """Detect rows whose ``pnl_pct`` is wildly inconsistent with prices.

    Returns True only when ALL of:
      * ``|pnl_pct|`` exceeds ``_PNL_PCT_CORRUPT_MIN_REPORTED`` (20%)
      * implied move from (entry, exit, direction) is computable
      * ``|implied_move_pct|`` is < ``_PNL_PCT_CORRUPT_MAX_IMPLIED`` (1%)
      * the ratio of reported to implied exceeds
        ``_PNL_PCT_CORRUPT_DIVERGENCE`` (10x)

    Conservative on purpose — rows with no exit_price or moderate divergence
    are kept (the goal is to neutralize the JPY-pip artifact without disturbing
    legitimate large-PnL outcomes like crypto pumps).
    """
    try:
        reported = float(pick.get("pnl_pct") or 0)
    except (TypeError, ValueError):
        return False
    if abs(reported) <= _PNL_PCT_CORRUPT_MIN_REPORTED:
        return False
    implied = _implied_move_pct(pick)
    if implied is None:
        return False
    if abs(implied) >= _PNL_PCT_CORRUPT_MAX_IMPLIED:
        return False
    # Avoid divide-by-zero edge case; tiny implied moves with huge reported PnL
    # are exactly the corruption pattern we want to catch.
    if abs(implied) < 1e-6:
        return True
    # JPY-aware divergence threshold (Phase 3 opt-in, 2026-05-03).
    # Default: keeps original 10x threshold (no behavior change).
    # Opt-in via PNL_PCT_CORRUPT_DIVERGENCE_JPY_RELAX=1 → use 50x for JPY pairs.
    # Rationale: the FOREX rescue 2026-05-03 deep-dive proposed relaxing JPY
    # divergence to admit legitimate JPY wins that pip-vs-percent feeder
    # confusion makes look corrupt; smoke-testing showed divergence often
    # exceeds 50x even on plausibly-legitimate cases (750x for USDJPY 5-pip
    # win reported as 25%), so default is conservative until offline A/B
    # backfill proves recovery > false-admission risk. Env opt-in allows
    # measurement without committing to default behavior change.
    sym = str(pick.get("symbol", "") or "").upper()
    # 2026-05-03: scope the JPY-aware relax to FOREX asset_class only.
    # Prior behavior fired on any symbol containing "JPY" (e.g. a hypothetical
    # crypto pseudo-symbol), which would silently widen corruption tolerance
    # outside the documented FOREX rescue scope. Tighten via asset_class
    # check + the =X yfinance suffix as a belt-and-suspenders signal.
    pick_ac = str(pick.get("asset_class", "") or pick.get("category", "") or "").upper()
    is_forex_jpy = (
        "JPY" in sym
        and (pick_ac == "FOREX" or sym.endswith("=X"))
    )
    if is_forex_jpy and os.environ.get("PNL_PCT_CORRUPT_DIVERGENCE_JPY_RELAX", "0") == "1":
        try:
            jpy_threshold = float(
                os.environ.get("PNL_PCT_CORRUPT_DIVERGENCE_JPY",
                               _PNL_PCT_CORRUPT_DIVERGENCE_JPY)
            )
        except (TypeError, ValueError):
            jpy_threshold = _PNL_PCT_CORRUPT_DIVERGENCE_JPY
        return abs(reported / implied) >= jpy_threshold
    return abs(reported / implied) >= _PNL_PCT_CORRUPT_DIVERGENCE


def _looks_like_crypto(pick: dict) -> bool:
    """True if the pick is a crypto asset (broad, for class-aware sanity)."""
    sym = str(pick.get("symbol", "") or "").upper()
    if sym.endswith(("USDT", "USDC", "BUSD", "DAI", "TUSD", "USDP")):
        return True
    cat = str(pick.get("asset_class", "") or pick.get("category", "") or "").upper()
    return cat in {"CRYPTO", "MEME"}


def _price_move_corrupt_for_non_crypto(pick: dict) -> bool:
    """Detect non-crypto rows whose entry/exit prices are inconsistent.

    Catches a failure mode distinct from `_pnl_pct_looks_corrupt`:
    upstream feeders sometimes stamp the wrong entry or exit price (e.g.
    AUDUSD=X with `entry=0.715, exit=76430` — exit stamped as bps×price
    or simply truncated). Such rows produce implied moves of 100x-10000x
    that get propagated into the aggregate as catastrophic single-trade
    contributions (one row contributed -106,700% to the forex aggregate).

    Forex pairs cannot move 50%+ in a swing window. Equity rarely does.
    Crypto can (legit pumps), so this rule is non-crypto only.
    """
    if _looks_like_crypto(pick):
        return False
    implied = _implied_move_pct(pick)
    if implied is None:
        return False
    return abs(implied) > _NON_CRYPTO_MAX_REASONABLE_MOVE_PCT


def _price_magnitude_corrupt(pick: dict) -> bool:
    """True if entry/exit prices differ by more than 100x.

    Catches a corruption pattern that even affects crypto (where the
    `_price_move_corrupt_for_non_crypto` check is bypassed). Real example:
    ZKUSDT entry=9.41, exit=0.01542 (610x mismatch) producing fake -99.84%.
    Real crypto pumps almost never exceed 100x in a single trade window,
    so this catches obvious price-stamping bugs without affecting
    legitimate big winners.
    """
    try:
        entry = float(pick.get("entry_price") or 0)
        exit_price = float(pick.get("exit_price") or 0)
    except (TypeError, ValueError):
        return False
    if entry <= 0 or exit_price <= 0:
        return False
    ratio = max(entry / exit_price, exit_price / entry)
    return ratio > _PRICE_MAGNITUDE_RATIO_CORRUPT


# Lazy-load blocked sets so this module's import order isn't fragile.
_BLOCKED_SETS_CACHE: dict = {}


def _get_blocked_sets() -> dict:
    """Cache BLOCKED_SYMBOLS, BLOCKED_ASSET_STRATEGY_PAIRS, and the
    strategy-blocked checker from quality_gates.

    Both block-sets must be consulted because they have different shapes:
    BLOCKED_STRATEGIES is `(strategy_name_fragment, asset_class_or_None)` and
    is checked by is_strategy_blocked() with substring matching;
    BLOCKED_ASSET_STRATEGY_PAIRS is `(asset_class, strategy)` and is checked
    by direct tuple lookup at the active-pick gate. Both express the same
    intent (this strategy is dead on this asset class), so the historical
    filter has to consult both.
    """
    if _BLOCKED_SETS_CACHE:
        return _BLOCKED_SETS_CACHE
    try:
        from audit_trail.quality_gates import (
            BLOCKED_SYMBOLS,
            BLOCKED_ASSET_STRATEGY_PAIRS,
            is_strategy_blocked,
        )
        _BLOCKED_SETS_CACHE['symbols'] = BLOCKED_SYMBOLS
        _BLOCKED_SETS_CACHE['is_strategy_blocked'] = is_strategy_blocked
        _BLOCKED_SETS_CACHE['asset_strategy_pairs'] = BLOCKED_ASSET_STRATEGY_PAIRS
    except Exception:
        _BLOCKED_SETS_CACHE['symbols'] = set()
        _BLOCKED_SETS_CACHE['is_strategy_blocked'] = lambda s, ac: False
        _BLOCKED_SETS_CACHE['asset_strategy_pairs'] = set()
    # Direction-aware triples (ml_crypto_predictor SHORT etc.) — separate
    # try/except since it was added in commit 0548fb746d follow-on; avoid
    # breaking older deployments that don't yet ship BLOCKED_DIRECTION_TRIPLES.
    try:
        from audit_trail.quality_gates import BLOCKED_DIRECTION_TRIPLES
        _BLOCKED_SETS_CACHE['direction_triples'] = BLOCKED_DIRECTION_TRIPLES
    except Exception:
        _BLOCKED_SETS_CACHE['direction_triples'] = set()
    # Symbol-aware triples (ghost-row cohorts: quan_engine MATIC, KIMI ETH/BTC,
    # irb_hoffman ADA, funding_rate_carry ROBO). Separate try/except for the
    # same forward-compat reason — older deployments may not ship the set yet.
    try:
        from audit_trail.quality_gates import BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES
        _BLOCKED_SETS_CACHE['symbol_triples'] = BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES
    except Exception:
        _BLOCKED_SETS_CACHE['symbol_triples'] = set()
    # PERMANENTLY_KILLED_STRATEGIES — kept separate from BLOCKED_STRATEGIES.
    # Active-pick gating already drops new picks from these (via
    # _KILLED_STRATEGIES_LOWER), but the historical filter wasn't consulting
    # this set, so old closed picks from yahoo_analyst_consensus,
    # cta_tsmom_blend, hl_funding_fade, etc. were still polluting aggregations.
    # OpenClaw-MiMo 2026-04-17 investigation flagged this as a P0.
    try:
        from audit_trail.quality_gates import PERMANENTLY_KILLED_STRATEGIES
        _BLOCKED_SETS_CACHE['permanently_killed'] = {s.lower() for s in PERMANENTLY_KILLED_STRATEGIES}
    except Exception:
        _BLOCKED_SETS_CACHE['permanently_killed'] = set()
    # REQUIRES_WALKAHEAD_AUDIT — systems flagged for mandatory walk-forward
    # before live use (Money-Maker-Ready P0 2026-05-14).
    try:
        from audit_trail.quality_gates import REQUIRES_WALKAHEAD_AUDIT
        _BLOCKED_SETS_CACHE["requires_walkahead_audit"] = REQUIRES_WALKAHEAD_AUDIT
    except Exception:
        _BLOCKED_SETS_CACHE["requires_walkahead_audit"] = set()

    return _BLOCKED_SETS_CACHE


def _is_historical_blocked_pick(pick: dict) -> bool:
    """True if this closed pick is on a strategy/symbol we've since blocked.

    Picks resolved BEFORE we identified a strategy or symbol as toxic stay in
    the closed ledger forever and continue to drag down headline metrics.
    Example surfaced 2026-04-18 audit: 7 historical TRXUSDT closes from
    `ml_enhanced_TRXUSDT_1d_B_light` contributed -554% to alpha_engine
    aggregate, even though TRXUSDT has been hard-blocked since 2026-04-02
    (nothing new can land on it). Excluding these from aggregations
    preserves the row in `recent_closed` but stops the bleed in WR/PF/PnL.

    Also addresses ml_crypto_pred (138/141 picks on `enhanced_ml_A_xgboost`,
    already in BLOCKED_STRATEGIES) and similar cleanup cases.
    """
    blocked = _get_blocked_sets()
    sym = str(pick.get("symbol") or "").upper()
    if sym in blocked['symbols']:
        return True
    strategy = pick.get("strategy") or ""
    asset_class = (
        str(pick.get("asset_class") or pick.get("category") or "").upper()
    )
    if blocked['is_strategy_blocked'](strategy, asset_class):
        return True
    # Also check the (asset_class, strategy) tuple set used by active-pick
    # gating. Same intent, different shape — see _get_blocked_sets() docstring.
    if (asset_class, str(strategy)) in blocked['asset_strategy_pairs']:
        return True
    # Direction-aware triples (ml_crypto_predictor SHORT etc.) — use this
    # when a strategy has edge in only one direction.
    direction = str(pick.get("direction", "") or "").upper()
    if direction and (asset_class, str(strategy), direction) in blocked['direction_triples']:
        return True
    # Symbol-aware triples (ghost-row cohorts) — drops constant-pnl template
    # rows from historical aggregates so dashboard WR/PF/MDD stop reflecting
    # the artifacts flagged at db_health.json::ghost_rows.
    if sym and (asset_class, str(strategy), sym) in blocked['symbol_triples']:
        return True
    # Zero-PnL noise filter (2026-05-12) — per user audit 2026-05-12, ~69% of
    # resolved trades have pnl_pct = 0. These are likely (a) writer dropped
    # pnl computation, (b) auto-expired rows where exit_price was filled at
    # entry_price (no actual move), (c) lm_signals expire-cron skipping the
    # resolver. Until the upstream zero-PnL backfill SQL ships (draft at
    # reports/zero_pnl_backfill_sql_2026-05-12.md Option A), the read-side
    # filter excludes terminal-status rows with pnl_pct = 0 *AND* either
    # (i) no exit_price OR (ii) exit_price == entry_price. Genuine
    # exit-price=entry break-even closes are very rare; the bulk of zero-pnl
    # rows under this signature are book-keeping artifacts. WON/LOST rows
    # with non-zero exit_price differences are NEVER filtered (those are
    # genuine outcomes; if pnl_pct=0 there it's an Option-A backfill
    # candidate, not a filter target).
    try:
        pnl_pct_val = float(pick.get("pnl_pct", 0) or 0)
    except (ValueError, TypeError):
        pnl_pct_val = 0.0
    if pnl_pct_val == 0.0:
        status_upper = str(pick.get("status", "")).upper().strip()
        terminal_set = ("WON", "LOST", "WIN", "LOSS", "TP_HIT", "SL_HIT",
                        "EXPIRED", "CLOSED_WIN", "CLOSED_LOSS")
        if status_upper in terminal_set:
            try:
                entry_p = float(pick.get("entry_price", 0) or 0)
                exit_p = float(pick.get("exit_price", 0) or 0)
            except (ValueError, TypeError):
                entry_p = exit_p = 0.0
            zero_pnl_artifact = (
                exit_p <= 0 or
                (entry_p > 0 and abs(exit_p - entry_p) < 1e-9)
            )
            if zero_pnl_artifact:
                return True
    # Permanently killed strategies — case-insensitive match. Active-pick
    # gating already drops these but the historical filter needs this
    # explicitly (OpenClaw-MiMo 2026-04-17). Includes yahoo_analyst_consensus
    # (0% WR n=55), cta_tsmom_blend (16.7% WR forex), binance_smart_money,
    # hl_funding_fade, winner_pattern_precursor, and many others.
    if str(strategy).lower() in blocked['permanently_killed']:
        return True
    return False


def _is_auto_expired_pick(pick: dict) -> bool:
    """Check if a closed pick is an auto-expired stale pick with no real outcome.

    Auto-expired picks have pnl_pct=0 and an exit_reason/status indicating
    staleness rather than a genuine TP/SL hit. Counting them inflates trade
    counts and deflates system-wide win rates.
    """
    pnl = float(pick.get("pnl_pct", 0) or 0)
    if pnl != 0:
        return False  # Has real PnL — not a no-outcome expiry

    # Check exit_reason field
    exit_reason = str(pick.get("exit_reason", "") or "").lower()
    for pattern in _AUTO_EXPIRED_PATTERNS:
        if pattern in exit_reason:
            return True

    # Check status field
    status = str(pick.get("status", "") or "").lower()
    if status in ("expired", "time_exit", "max_hold", "timed_out"):
        return True

    return False


def _is_valid_resolved_pick(pick: dict) -> bool:
    """Return True only for picks that should count in performance metrics.

    The dashboard displays many kinds of "closed" rows from different source
    systems. Some are legitimate realized outcomes; others are stale/snapshot
    rows that should not feed win rate, profit factor, or total PnL.
    """
    if not isinstance(pick, dict):
        return False
    if (
        pick.get("paper_trade")
        or pick.get("expired_no_pnl")
        or pick.get("_auto_expired")
    ):
        return False

    pnl_raw = pick.get("pnl_pct")
    if pnl_raw is None:
        return False

    # Reject rows where the recorded pnl_pct is incompatible with
    # (entry_price, exit_price, direction). These come from JPY-pair feeders
    # that confuse pips with percent — a single row can swing aggregate PF
    # by 100×. See _pnl_pct_looks_corrupt() above for thresholds.
    if _pnl_pct_looks_corrupt(pick):
        return False

    # Reject non-crypto rows whose entry/exit prices imply impossible moves
    # (>50% on forex/equity). Catches a separate failure mode where the
    # entry or exit price itself was stamped wrong (one AUDUSD=X row had
    # exit=76430 vs entry=0.715, contributing -106,700% to forex aggregate).
    # See _price_move_corrupt_for_non_crypto() above.
    if _price_move_corrupt_for_non_crypto(pick):
        return False

    # Reject ANY row (including crypto) where entry vs exit prices differ
    # by more than 100x. Catches symbol/price stamping bugs that even
    # affect crypto. Example: ZKUSDT entry=9.41 vs exit=0.01542 (612x
    # ratio) producing fake -99.84% wipeout that polluted super_signals.
    if _price_magnitude_corrupt(pick):
        return False

    # Reject historical rows from strategies/symbols we've since blocked.
    # These rows can't be re-traded but stay in the ledger and drag down
    # current performance metrics. Example: 7 historical TRXUSDT trades
    # contribute -554% to alpha_engine aggregate even though TRXUSDT has
    # been hard-blocked since 2026-04-02. See _is_historical_blocked_pick().
    if _is_historical_blocked_pick(pick):
        return False

    exit_reason = str(pick.get("exit_reason", "") or "").upper().strip()
    if exit_reason in _NON_PERFORMANCE_EXIT_REASONS:
        return False
    if exit_reason.startswith("STALE") or exit_reason == "INVALID_ENTRY":
        return False
    # Exclude outcome-resolver breakeven-fallback picks (yfinance returned None →
    # pnl_pct forced to 0.0). These are NOT real trade outcomes; counting them as
    # losses inflates the LOSS count and deflates PF/WR for EQUITY/ETF/BOND/FUTURES.
    # exit_reason values: "RESOLVE_FAILED_BREAKEVEN" (mid-cap) and
    # "RESOLVE_FAILED_MAX_RETRIES" (exhausted retries). Both should be invisible
    # to all performance-metric aggregators. See outcome_resolver.py:950-986.
    if exit_reason.startswith("RESOLVE_FAILED"):
        return False

    terminal_status = str(pick.get("status", "") or "").upper().strip()
    if terminal_status in _NON_PERFORMANCE_STATUSES:
        return False

    if exit_reason in ("", "UNKNOWN"):
        close_markers = (
            pick.get("closed_at")
            or pick.get("exit_timestamp")
            or pick.get("exit_time_est")
            or pick.get("exit_date")
        )
        if not close_markers and terminal_status not in {
            "WON",
            "LOST",
            "EXPIRED",
            "CLOSED",
        }:
            return False

    return True


def _filter_valid_resolved_picks(picks):
    """Filter a pick list down to realized, metric-safe resolved trades."""
    return [pick for pick in picks if _is_valid_resolved_pick(pick)]


def _compound_equal_weight_capped_sequence(
    picks: list[dict], max_pnl_pct: float = 500.0
) -> float:
    """Equal-notional geometric compound of capped per-trade PnL% (chronological).

    Each trade's ``pnl_pct`` is treated as a percent return on one unit of capital,
    capped at +/- ``max_pnl_pct`` to match headline summation, then multiplied in
    timestamp order (tie-break by symbol).

    DEPRECATED 2026-05-09: at large N (>1000) the metric balloons unboundedly
    even with tight per-trade caps (mean ~0.11%/trade × 9634 trades → e^10.6
    ≈ 4M%, ceiling-clamped to 9999%). Prefer ``_compound_rolling_window`` for
    headline display and ``_compound_per_day_geomean_annualized`` for an
    annualized rate. Kept for back-compat — callers may still import it. See
    PR replacing `total_pnl_pct_compounded_ew` semantics with rolling+geomean
    keys (T1.4 + loop2 #6 redesign).
    """
    if not picks:
        return 0.0

    def _sort_key(p: dict) -> tuple[str, str]:
        return (str(p.get("timestamp") or ""), str(p.get("symbol") or ""))

    prod = 1.0
    for p in sorted(picks, key=_sort_key):
        raw = float(p.get("pnl_pct", 0) or 0)
        capped = max(-max_pnl_pct, min(max_pnl_pct, raw))
        prod *= 1.0 + capped / 100.0
    return round((prod - 1.0) * 100.0, 2)


def _compound_rolling_window(
    picks: list[dict], window: int = 100, max_pnl_pct: float = 10.0
) -> float:
    """Geometric compound of the LAST ``window`` resolved trades (chronological).

    Replaces _compound_equal_weight_capped_sequence for headline display: the
    headline number tracks recent performance (last 100 trades) instead of the
    full ledger, so the metric stays bounded as N grows. Per-trade pnl_pct is
    capped at +/- ``max_pnl_pct`` (default 10%) to neutralize price-stamp bugs
    that the resolved-pick filter doesn't catch.

    Returns the compound return % over the window. Empty input → 0.0.
    """
    if not picks:
        return 0.0

    def _sort_key(p: dict) -> tuple[str, str]:
        return (str(p.get("timestamp") or ""), str(p.get("symbol") or ""))

    sorted_picks = sorted(picks, key=_sort_key)
    tail = sorted_picks[-window:] if len(sorted_picks) > window else sorted_picks

    prod = 1.0
    for p in tail:
        raw = float(p.get("pnl_pct", 0) or 0)
        capped = max(-max_pnl_pct, min(max_pnl_pct, raw))
        prod *= 1.0 + capped / 100.0
    return round((prod - 1.0) * 100.0, 2)


# Hard bounds for any annualized-return metric the dashboard emits. A
# degenerate input must never be able to produce 9999 or astronomical CAGRs.
_ANNUALIZED_FLOOR_PCT = -99.9
_ANNUALIZED_CEIL_PCT = 999.9
# Minimum data span / count required to annualize meaningfully.
_ANNUALIZE_MIN_DAYS = 30
_ANNUALIZE_MIN_TRADES = 2


def _annualize_cagr(
    final_equity: float,
    initial_equity: float,
    days_elapsed: float,
) -> float | None:
    """True geometric CAGR over an actual elapsed-time window.

    CAGR = ((final_equity / initial_equity) ** (365.25 / days_elapsed) - 1) * 100

    Returns None when inputs are too thin to annualize (< 30 days span) or
    non-positive equities. The result is hard-clamped to
    [_ANNUALIZED_FLOOR_PCT, _ANNUALIZED_CEIL_PCT] so a degenerate input can
    never emit a 9999-style sentinel or an absurd value.
    """
    if days_elapsed is None or days_elapsed < _ANNUALIZE_MIN_DAYS:
        return None
    if initial_equity <= 0 or final_equity <= 0:
        return None
    try:
        growth = final_equity / initial_equity
        cagr = (growth ** (365.25 / days_elapsed) - 1.0) * 100.0
    except (OverflowError, ValueError, ZeroDivisionError):
        # Explosive input: clamp by sign rather than fabricate a number.
        return _ANNUALIZED_CEIL_PCT if final_equity > initial_equity else _ANNUALIZED_FLOOR_PCT
    if not math.isfinite(cagr):
        return _ANNUALIZED_CEIL_PCT if final_equity > initial_equity else _ANNUALIZED_FLOOR_PCT
    cagr = max(_ANNUALIZED_FLOOR_PCT, min(_ANNUALIZED_CEIL_PCT, cagr))
    return round(cagr, 2)


def _compound_per_day_geomean_annualized(
    picks: list[dict],
    max_pnl_pct: float = 10.0,
    sanity_cap: float = 500.0,  # retained for back-compat signature; unused
) -> float | None:
    """True geometric CAGR of an equal-weight closed-trade equity curve.

    BROKEN PREDECESSOR (the source of the 9999 sentinel): the old formula
    annualized an *additive* sum of capped daily PnL% with the exponent
    ``252 / trading_days``. With a short window (e.g. 8 trading days) and a
    modestly positive additive total return, ``252/8 = 31.5`` and
    ``(1 + total_return)^31.5`` exploded into the thousands, then got
    ceiling-clamped to 9999 — a misleading headline.

    CORRECT APPROACH (this implementation):
      1. Build an equal-weight compounding equity curve: start at 1.0, and for
         each closed trade in timestamp order multiply by ``(1 + capped_pnl)``.
         This is a real geometric product, not an additive sum.
      2. Measure the ACTUAL elapsed calendar span between the first and last
         trade timestamp (days), not an assumed 252.
      3. CAGR = ((final_equity / 1.0) ** (365.25 / days_elapsed) - 1) * 100.
      4. Hard-clamp to [-99.9%, +999.9%].

    Returns None when the data is too thin to annualize meaningfully:
    < 2 trades, or an elapsed span < 30 days.
    """
    if not picks:
        return None

    dated: list[tuple[str, float]] = []
    for p in picks:
        ts = str(p.get("timestamp") or "")
        if len(ts) < 10 or ts[4] != "-":
            continue
        raw = float(p.get("pnl_pct", 0) or 0)
        capped = max(-max_pnl_pct, min(max_pnl_pct, raw))
        dated.append((ts, capped))

    if len(dated) < _ANNUALIZE_MIN_TRADES:
        return None

    dated.sort(key=lambda t: t[0])

    # Elapsed calendar span from first to last trade, in days.
    try:
        first = datetime.fromisoformat(dated[0][0][:19].replace("Z", ""))
        last = datetime.fromisoformat(dated[-1][0][:19].replace("Z", ""))
        days_elapsed = (last - first).total_seconds() / 86400.0
    except (ValueError, TypeError):
        return None
    if days_elapsed < _ANNUALIZE_MIN_DAYS:
        return None

    # Equal-weight compounding equity curve (geometric product).
    equity = 1.0
    for _, capped in dated:
        equity *= (1.0 + capped / 100.0)
        if equity <= 0:
            equity = 1e-9  # bankrupt; floor so CAGR clamps to -99.9
            break

    result = _annualize_cagr(equity, 1.0, days_elapsed)

    # Honesty guard: if the result saturated to the ceiling sentinel, return
    # None instead of emitting a misleading clamped headline. Short windows
    # (<60 days) silently fall back to n/a; longer windows still return None
    # but log a structured warning so the producer-side anomaly is visible.
    if result is not None and result >= _ANNUALIZED_CEIL_PCT:
        try:
            unclamped = (equity ** (365.25 / days_elapsed) - 1.0) * 100.0
        except (OverflowError, ValueError, ZeroDivisionError):
            unclamped = float("inf")
        if days_elapsed >= 60:
            sys.stderr.write(
                "[dashboard_generator] WARN: _compound_per_day_geomean_annualized "
                f"unclamped={unclamped!r} days_elapsed={days_elapsed:.2f} "
                f"n_trades={len(dated)} ceiling={_ANNUALIZED_CEIL_PCT} -> returning None\n"
            )
        return None

    return result


def _per_trade_sharpe(
    picks: list[dict], days_span: int | None = None
) -> tuple[float, float]:
    """Per-trade Sharpe + annualized variant.

    Returns ``(sharpe_per_trade, sharpe_per_trade_annualized)``. When variance
    is zero (or n<2), returns (0.0, 0.0) — never raises.

    Per-trade Sharpe = mean(pnl_pct) / stdev(pnl_pct). Annualized version
    estimates trades_per_year from ``days_span`` (calendar days observed) and
    scales by sqrt(trades_per_year). When ``days_span`` is None, falls back
    to len(picks) for the annualization factor (degenerate but stable).

    Comment for callers (see also `mercury_net_sharpe_daily` block):
      - Use **daily Sharpe** for portfolio-aggregate Sharpe (institutional /
        Morningstar-comparable; collapses intra-day vol).
      - Use **per-trade Sharpe** for strategy-quality Sharpe (each trade is
        an independent draw; what KPI tables typically want).
    """
    trade_pnls = [
        float(p.get("pnl_pct", 0) or 0)
        for p in picks
        if p.get("pnl_pct") is not None
    ]
    n = len(trade_pnls)
    if n < 2:
        return (0.0, 0.0)

    mean_t = sum(trade_pnls) / n
    var_t = sum((x - mean_t) ** 2 for x in trade_pnls) / (n - 1)
    std_t = math.sqrt(var_t)
    if std_t <= 0:
        return (0.0, 0.0)

    sharpe = mean_t / std_t
    days = days_span if (days_span and days_span > 0) else n
    trades_per_year = (n / days) * 252
    annual = sharpe * math.sqrt(max(trades_per_year, 1.0))
    return (round(sharpe, 4), round(annual, 4))


def _outcome_bucket_from_pnl(
    pnl: float, threshold: float = _MIN_REALIZED_PNL_PCT
) -> str:
    """Classify a realized trade as win/loss/flat using a small noise threshold."""
    if pnl > threshold:
        return "win"
    if pnl < -threshold:
        return "loss"
    return "flat"


def _calculate_win_rate_pct(wins: int, losses: int, flat: int = 0) -> float:
    """Standardized WR formula: wins / (wins + losses + flat)."""
    total = wins + losses + flat
    return round(wins / total * 100, 1) if total > 0 else 0.0


def _calculate_expectancy_pct(
    total_pnl: float, wins: int, losses: int, flat: int = 0
) -> float:
    """Average PnL per resolved trade, including flat outcomes in the denominator."""
    total = wins + losses + flat
    return round(total_pnl / total, 2) if total > 0 else 0.0


def _looks_resolved_source_pick(raw: dict) -> bool:
    """Detect closed/resolved rows embedded inside an "active" source file."""
    if not isinstance(raw, dict):
        return False
    if _is_closed_status(raw.get("status", "")):
        return True

    explicit_close_time = (
        raw.get("resolved_at")
        or raw.get("_resolved_at")
        or raw.get("resolvedAt")
        or raw.get("resolved_at_est")
        or raw.get("closed_at")
        or raw.get("closedAt")
        or raw.get("closed_at_est")
        or raw.get("exit_time")
        or raw.get("exitTime")
        or raw.get("exit_time_est")
        or raw.get("exit_timestamp")
        or raw.get("exitDate")
        or raw.get("exit_date")
        or raw.get("close_time")
        or raw.get("closeTime")
        or raw.get("closeDate")
    )
    if explicit_close_time:
        return True

    outcome_marker = (
        str(
            raw.get(
                "exit_reason",
                raw.get(
                    "close_reason", raw.get("resolved_reason", raw.get("outcome", ""))
                ),
            )
            or ""
        )
        .upper()
        .strip()
    )
    if outcome_marker and outcome_marker not in {
        "OPEN",
        "ACTIVE",
        "PENDING",
        "LIVE",
        "READY",
        "UNRESOLVED",
        "UNKNOWN",
        "NONE",
        "NULL",
    }:
        return True

    exit_price = _float(
        raw.get(
            "exit_price",
            raw.get(
                "close_price",
                raw.get("_resolved_price", 0),
            ),
        )
    )
    if exit_price > 0:
        return True
    pnl_raw = raw.get(
        "pnl_pct",
        raw.get(
            "actual_pnl_pct",
            raw.get(
                "outcome_pnl_pct",
                raw.get(
                    "plPercent",
                    raw.get(
                        "_resolved_pnl_pct",
                        raw.get("pnl_dollar", raw.get("unrealized_pnl_pct", None)),
                    ),
                ),
            ),
        ),
    )
    try:
        if (
            pnl_raw not in (None, "")
            and abs(float(pnl_raw)) >= _MIN_REALIZED_PNL_PCT
            and outcome_marker
            and outcome_marker
            not in {
                "OPEN",
                "ACTIVE",
                "PENDING",
                "LIVE",
                "READY",
                "UNRESOLVED",
                "UNKNOWN",
                "NONE",
                "NULL",
            }
        ):
            return True
    except (TypeError, ValueError):
        pass
    return False


def _pick_identity_key(pick: dict):
    """Stable logical identity used to match active picks to resolved outcomes."""
    raw_id = pick.get(
        "id", pick.get("pick_id", pick.get("signal_id", pick.get("prediction_id", "")))
    )
    if raw_id not in (None, ""):
        return ("id", pick.get("source_system", ""), str(raw_id))
    ts = str(pick.get("timestamp", "") or "").strip()
    ts_key = ts[:19] if ts else ""
    entry = _float(pick.get("entry_price", 0) or 0)
    return (
        "fallback",
        pick.get("source_system", ""),
        _normalize_symbol(pick.get("symbol", "")),
        str(pick.get("direction", "")).upper(),
        str(pick.get("strategy", "") or ""),
        round(entry, 8) if entry else 0.0,
        ts_key,
    )


def _closed_conflict_key(pick: dict):
    """Broader key used to drop stale shadow rows when a real resolved twin exists."""
    raw_id = pick.get(
        "id", pick.get("pick_id", pick.get("signal_id", pick.get("prediction_id", "")))
    )
    if raw_id not in (None, ""):
        return ("id", pick.get("source_system", ""), str(raw_id))
    entry = _float(pick.get("entry_price", 0) or 0)
    return (
        "fallback",
        pick.get("source_system", ""),
        _normalize_symbol(pick.get("symbol", "")),
        str(pick.get("direction", "")).upper(),
        str(pick.get("strategy", "") or ""),
        round(entry, 8) if entry else 0.0,
    )


def _prefer_metric_safe_closed_picks(picks: list[dict]) -> tuple[list[dict], int]:
    """When the same logical pick appears twice, keep the metric-safe resolved version."""
    grouped = defaultdict(list)
    for pick in picks:
        grouped[_closed_conflict_key(pick)].append(pick)

    kept = []
    dropped = 0
    for group in grouped.values():
        valid = [p for p in group if _is_valid_resolved_pick(p)]
        if valid:
            kept.extend(valid)
            dropped += len(group) - len(valid)
        else:
            kept.extend(group)
    return kept, dropped


def _is_closed_status(raw_status: str) -> bool:
    """Check if a status string represents a closed/resolved pick."""
    return str(raw_status).lower().strip() in _CLOSED_STATUSES


def _logical_dashboard_source_system(
    source_system: str, raw: dict, asset_class: str
) -> str:
    """Map bridge-managed rows back to the logical dashboard system.

    The multi-asset bridge mirrors non-crypto picks into both alpha-engine and the
    dedicated multi-asset files. We need one stable logical system name so actives and
    realized closes line up on /audit. Preserve the explicit multi-asset subsystem
    (`multi_asset_copytrader`, `multi_asset_scanner`, etc.) instead of collapsing those
    rows into a generic `multi_asset` bucket.
    """
    if source_system != "alpha_engine" or not isinstance(raw, dict):
        if source_system == "multi_asset":
            raw_source = str(raw.get("source_system", "") or "").strip()
            if asset_class.upper() != "CRYPTO" and raw_source.startswith(
                "multi_asset_"
            ):
                return raw_source
        return source_system

    raw_source = str(raw.get("source_system", "") or "").strip()
    if not raw_source:
        return source_system

    if asset_class.upper() == "CRYPTO":
        return source_system

    if raw_source.startswith("multi_asset_"):
        return raw_source
    if raw_source.startswith("cta_"):
        return "multi_asset"

    return source_system


def _is_prediction_market_pick(
    source_system: str,
    dashboard_source_system: str,
    raw: dict,
    strategy: str,
) -> bool:
    candidates = {
        str(source_system or "").strip().lower(),
        str(dashboard_source_system or "").strip().lower(),
        str(raw.get("source_system", "") or "").strip().lower(),
        str(raw.get("source_subsystem", "") or "").strip().lower(),
    }
    if candidates & {
        "pm_whale_signals",
        "pm_momentum_signals",
        "pm_kalshi_signals",
        "prediction_market_consensus",
        "pm_high_conviction",
        "polymarket_whale_tracker",
        "polymarket_momentum",
        "kalshi_signal_agent",
        "polymarket_signals",
        "polymarket",
    }:
        return True

    strat = (
        str(strategy or raw.get("strategy") or raw.get("strategy_name") or "")
        .strip()
        .lower()
    )
    return (
        strat.startswith("copy_pm_")
        or strat.startswith("pm_whale_")
        or strat.startswith("pm_momentum")
        or "polymarket" in strat
        or "kalshi" in strat
    )


def _derive_prediction_market_trade_levels(
    entry_price: float,
    direction: str,
    confidence: float,
    source_count: int = 1,
) -> tuple[float, float]:
    """Convert a PM signal-only row into a concrete spot trade frame."""
    if entry_price <= 0:
        return (0.0, 0.0)

    conf = max(0.55, min(0.95, _float(confidence or 0.70)))
    source_bonus = max(0, min(int(source_count or 1) - 1, 3))
    tp_pct = min(0.04, max(0.015, 0.014 + (conf - 0.55) * 0.04 + source_bonus * 0.0025))
    sl_pct = max(0.009, tp_pct / 1.67)

    if str(direction).upper() == "SHORT":
        return (
            round(entry_price * (1 - tp_pct), 8),
            round(entry_price * (1 + sl_pct), 8),
        )
    return (
        round(entry_price * (1 + tp_pct), 8),
        round(entry_price * (1 - sl_pct), 8),
    )


def _snapshot_prediction_market_entry(pick: dict, current_price: float) -> bool:
    """Backfill entry/TP/SL for PM rows that arrive as signal-only objects."""
    if current_price <= 0:
        return False
    if _float(pick.get("entry_price", 0)) > 0:
        return False

    direction = str(pick.get("direction", "LONG") or "LONG").upper()
    if direction not in {"LONG", "SHORT"}:
        direction = "LONG"

    source_count = 1
    consensus_data = pick.get("consensus_data")
    if isinstance(consensus_data, dict):
        source_count = (
            consensus_data.get("source_category_count")
            or consensus_data.get("num_sources")
            or source_count
        )

    entry_price = round(float(current_price), 8)
    pick["entry_price"] = entry_price
    if _float(pick.get("take_profit", 0)) <= 0 or _float(pick.get("stop_loss", 0)) <= 0:
        take_profit, stop_loss = _derive_prediction_market_trade_levels(
            entry_price,
            direction,
            _float(pick.get("confidence", 0.70)),
            int(source_count or 1),
        )
        pick["take_profit"] = take_profit
        pick["stop_loss"] = stop_loss
    return True


# Verified Alpha sources - prediction markets + auditable copy trading
_VERIFIED_ALPHA_PM_SOURCES = {
    "pm_whale_signals",
    "pm_kalshi_signals",
    "prediction_market_consensus",
    "polymarket_signals",
    "pm_high_conviction",
    "pm_momentum_signals",
}
_VERIFIED_ALPHA_COPY_SOURCES = {
    "copy_trader_intel",
    "copy_trader_highscore",
    "copy_trader_consensus",
    "copy_trader_clones",
    "highscore_pick",
    "alpha_engine",
    "smart_picks",
    "claude_gainer_st",
}
_VERIFIED_ALPHA_CURATED_COPY_STRATEGIES = {
    "forex_rsi2_mean_reversion",
    "stocks_rsi2_pullback",
    "cftc_cot_commercial_signal",
    "cot_positioning",
    "cta_commodity_momentum_term",
    "cta_cross_asset_tsmom",
    "cta_golden_cross_200",
}
# Strategy prefixes that indicate verified copy trading with audit trail
_VERIFIED_ALPHA_COPY_PREFIXES = (
    "copy_pm_",
    "clone_hl_",
    "copy_hl_",
    "hs_",
    "consensus_",
)
_TRACK_RECORD_CLOSED_SOURCES = {
    "copy_trader_intel",
    "multi_asset_copytrader",
    "multi_asset",
    "multi_asset_institutional",
    "cta_replicator",
    "pm_whale_signals",
    "pm_kalshi_signals",
    "polymarket_signals",
    "prediction_market_consensus",
}
# Non-crypto asset classes that should always have reserved closed-pick slots.
# Without reservation, high-frequency crypto picks crowd them out of the 1000 cap.
_NON_CRYPTO_ASSET_CLASSES = {"EQUITY", "ETF", "FOREX", "FUTURES", "COMMODITY", "BOND"}


def _track_stats_key(strategy: str, symbol: str) -> str:
    """Return canonical key for per-(strategy, symbol) track stats lookup."""
    return f"{strategy}::{symbol}"


def _source_symbol_track_key(source_system: str, symbol: str) -> str:
    """Key for per-(source_system, symbol) stats (super-signal `via` is a system id)."""
    sys_key = (source_system or "").strip().lower()
    sym = _normalize_symbol(symbol)
    return f"{sys_key}::{sym}"


def _super_signal_via_feeder_candidates(via_token: str) -> list[str]:
    """Expand `via` segment to possible source_system values on closed rows.

    Super signals label strategies as ``super signal (tier) via <X>`` where ``X``
    comes from ``source_system`` of the winning feeder pick, not from that
    pick's ``strategy`` field (see ``cross_aggregation/super_signal.py``).
    Closed-trade rows keep real algo names in ``strategy`` and the feeder in
    ``source_system``, so we must match the ledger by system+symbol too.
    """
    v0 = (via_token or "").strip()
    if not v0:
        return []
    v = v0.lower()
    out: list[str] = []
    seen: set[str] = set()

    def add(x: str) -> None:
        x = (x or "").strip()
        if not x or x.lower() in seen:
            return
        seen.add(x.lower())
        out.append(x)

    add(v0)
    # Common dashboard / file variants for the same feeder
    alias_extra: dict[str, tuple[str, ...]] = {
        "kimi": ("kimi_live_signals", "kimi_live"),
        "kimi_live": ("kimi", "kimi_live_signals"),
        "kimi_live_signals": ("kimi", "kimi_live"),
        "alpha_engine": ("alpha_engine_fast",),
        "alpha_engine_fast": ("alpha_engine",),
    }
    for extra in alias_extra.get(v, ()):
        add(extra)
    return out


def _build_source_symbol_track_stats(closed_picks: list) -> dict:
    """Like _build_strategy_symbol_track_stats but keyed by source_system+symbol."""
    stats: dict[str, dict] = {}
    for pick in closed_picks:
        sys_name = (pick.get("source_system") or "").strip()
        sym = _normalize_symbol(pick.get("symbol", ""))
        if not sys_name or not sym:
            continue
        key = _source_symbol_track_key(sys_name, sym)
        if key not in stats:
            stats[key] = {
                "sym_track_total": 0,
                "sym_track_wins": 0,
                "sym_track_losses": 0,
                "sym_track_wr": None,
                "sym_track_pnl": 0.0,
            }
        entry = stats[key]
        entry["sym_track_total"] += 1
        pnl = float(pick.get("pnl_pct", 0) or 0)
        entry["sym_track_pnl"] = round(entry["sym_track_pnl"] + pnl, 4)
        status = (pick.get("status") or pick.get("outcome") or "").upper()
        exit_reason = (pick.get("exit_reason") or "").upper()
        if exit_reason == "TP_HIT":
            entry["sym_track_wins"] += 1
        elif exit_reason == "SL_HIT":
            entry["sym_track_losses"] += 1
        elif status in ("WON", "WIN", "TP_HIT", "CLOSED_TP"):
            entry["sym_track_wins"] += 1
        elif status in ("LOST", "LOSS", "SL_HIT", "CLOSED_SL"):
            entry["sym_track_losses"] += 1
        elif exit_reason == "TIME_EXIT" or status == "CLOSED":
            if pnl > 0.01:
                entry["sym_track_wins"] += 1
            elif pnl < -0.01:
                entry["sym_track_losses"] += 1
    for entry in stats.values():
        resolved = entry["sym_track_wins"] + entry["sym_track_losses"]
        entry["sym_track_wr"] = (
            round(entry["sym_track_wins"] / resolved * 100, 1) if resolved > 0 else None
        )
    return stats


def _build_strategy_symbol_track_stats(closed_picks: list) -> dict:
    """Build per-(strategy, symbol) win statistics from closed picks.

    Returns a dict keyed by ``_track_stats_key(strat, sym)`` where each value
    has keys: sym_track_total, sym_track_wins, sym_track_losses, sym_track_wr,
    sym_track_pnl.
    """
    stats: dict[str, dict] = {}
    for pick in closed_picks:
        strat = pick.get("strategy", "")
        sym = _normalize_symbol(pick.get("symbol", ""))
        if not strat or not sym:
            continue
        key = _track_stats_key(strat, sym)
        if key not in stats:
            stats[key] = {
                "sym_track_total": 0,
                "sym_track_wins": 0,
                "sym_track_losses": 0,
                "sym_track_wr": None,
                "sym_track_pnl": 0.0,
            }
        entry = stats[key]
        entry["sym_track_total"] += 1
        pnl = float(pick.get("pnl_pct", 0) or 0)
        entry["sym_track_pnl"] = round(entry["sym_track_pnl"] + pnl, 4)
        status = (pick.get("status") or pick.get("outcome") or "").upper()
        exit_reason = (pick.get("exit_reason") or "").upper()
        # Universal resolver rows often use status=CLOSED + exit_reason=TP_HIT/SL_HIT/TIME_EXIT
        if exit_reason == "TP_HIT":
            entry["sym_track_wins"] += 1
        elif exit_reason == "SL_HIT":
            entry["sym_track_losses"] += 1
        elif status in ("WON", "WIN", "TP_HIT", "CLOSED_TP"):
            entry["sym_track_wins"] += 1
        elif status in ("LOST", "LOSS", "SL_HIT", "CLOSED_SL"):
            entry["sym_track_losses"] += 1
        elif exit_reason == "TIME_EXIT" or status == "CLOSED":
            if pnl > 0.01:
                entry["sym_track_wins"] += 1
            elif pnl < -0.01:
                entry["sym_track_losses"] += 1
    # Compute WR for each entry
    for entry in stats.values():
        resolved = entry["sym_track_wins"] + entry["sym_track_losses"]
        entry["sym_track_wr"] = (
            round(entry["sym_track_wins"] / resolved * 100, 1) if resolved > 0 else None
        )
    return stats


def _track_win_loss(pick: dict) -> tuple:
    """Return (win, loss) as 1/0 flags for a closed pick.

    Uses the exact same status/exit_reason/pnl precedence as
    ``_build_strategy_symbol_track_stats`` so the point-in-time shadow metric
    classifies outcomes identically to the leaky all-time metric.
    """
    pnl = float(pick.get("pnl_pct", 0) or 0)
    status = (pick.get("status") or pick.get("outcome") or "").upper()
    exit_reason = (pick.get("exit_reason") or "").upper()
    if exit_reason == "TP_HIT":
        return (1, 0)
    if exit_reason == "SL_HIT":
        return (0, 1)
    if status in ("WON", "WIN", "TP_HIT", "CLOSED_TP"):
        return (1, 0)
    if status in ("LOST", "LOSS", "SL_HIT", "CLOSED_SL"):
        return (0, 1)
    if exit_reason == "TIME_EXIT" or status == "CLOSED":
        if pnl > 0.01:
            return (1, 0)
        if pnl < -0.01:
            return (0, 1)
    return (0, 0)


def _stamp_pit_sym_track(picks_to_stamp: list, resolved_closed: list) -> None:
    """Stamp a leakage-FREE point-in-time (strategy, symbol) win rate.

    Writes ``sym_track_wr_pit`` and ``sym_track_total_pit`` onto each pick in
    ``picks_to_stamp``. For each pick the win rate is computed over ONLY
    ``resolved_closed`` history in the same (strategy, symbol) bucket whose
    timestamp is STRICTLY earlier than that pick's timestamp — the pick itself
    and every same-or-later sibling are excluded.

    This is a SHADOW column alongside the existing all-time ``sym_track_wr``,
    which is target-leaked (computed over a window that includes the pick being
    scored). See reports/AUDIT_STAT_VALIDATION_2026-05-22.md. ``sym_track_wr``
    is intentionally left untouched for backward compatibility.
    """
    _min_dt = datetime.min.replace(tzinfo=timezone.utc)

    def _ts(p):
        raw = p.get("timestamp") or p.get("created_at") or p.get("entry_time") or ""
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return _min_dt

    # Bucket closed history by (strategy, symbol), sorted ascending by time.
    hist: dict = {}
    for cp in resolved_closed:
        strat = cp.get("strategy", "")
        sym = _normalize_symbol(cp.get("symbol", ""))
        if not strat or not sym:
            continue
        win, loss = _track_win_loss(cp)
        hist.setdefault(_track_stats_key(strat, sym), []).append((_ts(cp), win, loss))
    for rows in hist.values():
        rows.sort(key=lambda r: r[0])

    for p in picks_to_stamp:
        strat = p.get("strategy", "")
        sym = _normalize_symbol(p.get("symbol", ""))
        if not strat or not sym:
            p["sym_track_wr_pit"] = None
            p["sym_track_total_pit"] = 0
            continue
        rows = hist.get(_track_stats_key(strat, sym)) or []
        p_ts = _ts(p)
        wins = losses = 0
        for h_ts, win, loss in rows:
            if h_ts >= p_ts:  # strictly-earlier only — rest are same/later
                break
            wins += win
            losses += loss
        resolved = wins + losses
        p["sym_track_wr_pit"] = round(wins / resolved * 100, 1) if resolved else None
        p["sym_track_total_pit"] = resolved


def _build_smart_gate_failure_histogram(active_picks: list) -> dict:
    """Per-(asset_class, first_failure_code) histogram for smart-gate funnel.

    Emits {asset_class: {code: count, ..., "_passed": k, "_total": n}}.
    Mirrors tools/audit_smart_gate_funnel.py shape but grouped by class so the
    dashboard can explain smartCount=0 per class (PR #6, swarm 2026-05-04).
    """
    try:
        import copy as _copy
        from audit_trail.quality_gates import evaluate_smart_gate_funnel
    except Exception:
        return {}
    out: dict = {}
    for raw in active_picks or []:
        ac = (raw.get("asset_class") or "UNKNOWN") if isinstance(raw, dict) else "UNKNOWN"
        ac = str(ac).upper() or "UNKNOWN"
        bucket = out.setdefault(ac, {"_passed": 0, "_total": 0})
        bucket["_total"] += 1
        try:
            ok, reason = evaluate_smart_gate_funnel(_copy.deepcopy(raw))
        except Exception:
            ok, reason = False, "evaluator_error"
        if ok:
            bucket["_passed"] += 1
            continue
        code = reason or "unknown"
        bucket[code] = bucket.get(code, 0) + 1
    return out


def _registry_backed_ac_breakdown():
    """M-067: build an `ac_breakdown` dict from the canonical pf_registry.json
    (net, policy-clean view) so `compute_asset_class_health` reads ONE source
    of truth instead of recomputing PF/WR independently.

    Gated by env `AUDIT_HEALTH_SOURCE` — only active when set to "registry"
    (default "recompute" keeps the legacy in-generator path). Returns None on
    ANY fail-open trigger; the caller then falls back to the recompute:
      - flag not set to "registry"
      - pf_registry.json missing / unreadable / bad JSON
      - schema_version missing
      - source_files_canonical is False (registry not reconcilable to /audit)
      - registry is STALE (generated before the closed-pick ledger's mtime)
      - the net policy-clean view is missing or empty

    The returned dict is shape-compatible with what compute_asset_class_health
    consumes (wins / losses / win_rate / pnl / profit_factor) so the status,
    tier and sizing logic inside that function is untouched.
    """
    import json as _json
    import time as _time
    from datetime import datetime as _dt, timezone as _tz

    # M-067 default flipped to "registry" 2026-05-17 after the per-class
    # sizing_allowed diff (reports/m067_sizing_diff_2026-05-17.md) confirmed
    # NO blocked->allowed flip — the only change is EQUITY allowed->blocked,
    # which is protective (registry net PF 0.72 correctly blocks what the
    # inflated recompute's PF 2.04 wrongly allowed). Rollback: set
    # AUDIT_HEALTH_SOURCE=recompute to restore the legacy in-generator path.
    if os.environ.get("AUDIT_HEALTH_SOURCE", "registry").strip().lower() != "registry":
        return None
    try:
        _repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _reg_path = os.path.join(_repo, "audit_dashboard", "data", "pf_registry.json")
        if not os.path.isfile(_reg_path):
            log.warning("M-067: pf_registry.json missing — fallback to recompute")
            return None
        with open(_reg_path, "r", encoding="utf-8") as _fh:
            reg = _json.load(_fh)
        if not reg.get("schema_version"):
            log.warning("M-067: pf_registry.json has no schema_version — fallback")
            return None
        if not reg.get("source_files_canonical", False):
            log.warning("M-067: pf_registry built from fallback sources "
                        "(not reconcilable) — fallback to recompute")
            return None
        # Staleness: registry must be newer than the main closed-pick ledger.
        _gen = reg.get("generated_utc")
        _ledger = os.path.join(_repo, "alpha_engine", "data", "closed_picks.json")
        if _gen and os.path.isfile(_ledger):
            try:
                _gen_ts = _dt.strptime(_gen, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=_tz.utc).timestamp()
                if _gen_ts < os.path.getmtime(_ledger) - 60:
                    log.warning("M-067: pf_registry.json is STALE (generated "
                                "%s, older than closed_picks.json) — fallback", _gen)
                    return None
            except (ValueError, OSError):
                pass
        net_view = reg.get("by_asset_class_policy_clean_net") or []
        if not net_view:
            log.warning("M-067: pf_registry net view empty — fallback")
            return None
        out: dict[str, dict] = {}
        for row in net_view:
            ac = str(row.get("asset_class") or "").upper()
            if not ac or ac == "UNKNOWN":
                continue
            out[ac] = {
                "wins": int(row.get("wins") or 0),
                "losses": int(row.get("losses") or 0),
                "win_rate": float(row.get("win_rate_pct") or 0.0),
                "pnl": float(row.get("total_pnl_pct") or 0.0),
                "profit_factor": row.get("profit_factor"),
                # Q2 (2026-05-19): class-level max drawdown persisted in
                # pf_registry.json (fraction, 0.20 = 20%). Pass through so
                # asset_class_health carries PF + WR + MDD together. None on
                # older registry files that predate the key.
                "max_drawdown_pct": row.get("max_drawdown_pct"),
            }
        if not out:
            return None
        log.info("M-067: asset_class_health SOURCED FROM pf_registry.json "
                 "(net policy-clean view, %d classes)", len(out))
        return out
    except Exception as exc:  # noqa: BLE001 — fail-open by design
        log.warning("M-067: registry-backed breakdown failed (%s) — fallback", exc)
        return None


def compute_asset_class_health(ac_breakdown: dict) -> dict:
    """Min-N aware health labels per asset class for dashboard UI.

    Uses resolved win/loss counts from ``ac_breakdown`` (same basis as WR/PF).

    Tiered n-guard (Tier-A #3, 2026-05-04 — per
    reports/audit_unified_implementation_queue_2026_05_04.md):
      n < 10                    -> insufficient_data (suppress all stats)
      10 <= n < min_candidate_n -> thin_sample
      min_candidate_n <= n < min_stable_n -> candidate (eligible to display
                                              metrics, NOT eligible for
                                              "stable"/deploy badge)
      n >= min_stable_n         -> stable/watch/stressed by metrics

    The min_stable_n threshold was raised 50 -> 100 to match CLAUDE.md
    Tier-2 charter floor (n>=100). Previously ETF (n=87) and similar
    borderline classes could be labeled "stable" without meeting the
    charter floor; now they fall into "candidate" until n grows.
    """
    min_display_n = 10
    min_candidate_n = 50
    min_stable_n = 100  # CLAUDE.md charter T2 floor
    # PR-A (2026-05-12): exclude sports betting classes from /audit
    # asset_class_health. Sports lives at /live-monitor/sports-betting.html
    # with separate KPIs (CLV, vig, sport-tier matrices). Mixing inflates the
    # asset-class dropdown and pollutes alpha-trading verdicts.
    _SPORTS_EXCLUDED = {"SPORTS", "BETTING", "SPORT", "BET"}
    out: dict[str, dict] = {}
    for ac_raw, b in (ac_breakdown or {}).items():
        ac = str(ac_raw).upper()
        if ac in _SPORTS_EXCLUDED:
            continue
        wins = int(b.get("wins") or 0)
        losses = int(b.get("losses") or 0)
        n = wins + losses
        wr = float(b.get("win_rate") or 0)
        pnl = float(b.get("pnl") or 0)
        pf_raw = b.get("profit_factor")
        try:
            pf = float(pf_raw) if pf_raw is not None else None
        except (TypeError, ValueError):
            pf = None
        # Q2 (2026-05-19): class-level max drawdown (fraction; None if absent).
        mdd_raw = b.get("max_drawdown_pct")
        try:
            mdd_pct = float(mdd_raw) if mdd_raw is not None else None
        except (TypeError, ValueError):
            mdd_pct = None
        if n < min_display_n:
            status = "insufficient_data"
        elif n < min_candidate_n:
            status = "thin_sample"
        elif n < min_stable_n:
            # Has enough trades to compute reasonably stable metrics but
            # below the charter T2 deploy floor (n>=100). Surface as
            # "candidate" so the dashboard knows not to render the stable
            # badge or downstream sizing logic.
            status = "candidate"
        elif wr < 38.0 or pnl < -80.0 or (pf is not None and pf < 0.82):
            status = "stressed"
        elif wr >= 45.0 and (pf is None or pf >= 1.0) and pnl >= 0:
            status = "stable"
        else:
            status = "watch"
        sample_tier = {
            "insufficient_data": "insufficient",
            "thin_sample": "thin",
            "candidate": "candidate",
        }.get(status, "stable")
        # PF<1.0 means gross losses exceed gross wins; never allow sizing
        # regardless of "watch" status (2026-05-15, M-048 FOREX cold-start gap).
        sizing_allowed = status in ("stable", "watch") and (pf is None or pf >= 1.0)
        # COMMODITY headline PF (7.71 @ WR 85.5%) is a COT/CT=F over-emission
        # + leakage artifact: CT=F is COMMODITY_BLACKLIST (Phase 2-D kill), COT
        # edge is leakage-falsified. _build_readiness_payload already forces
        # MONITORING via COMMODITY_FORCE_MONITOR; mirror that guard onto the
        # raw asset_class_health dict so direct consumers (template.html,
        # hc_filter.js, sizers) cannot read sizing_allowed=True off a phantom
        # edge. Override: COMMODITY_FORCE_MONITOR=0 disables (default ON=safe).
        if ac == "COMMODITY":
            _cmod_guard = os.environ.get("COMMODITY_FORCE_MONITOR", "1") not in (
                "0", "false", "FALSE", "False"
            )
            if _cmod_guard:
                sizing_allowed = False
        out[ac] = {
            "status": status,
            "sample_tier": sample_tier,
            "sizing_allowed": sizing_allowed,
            # `n` is the canonical alias for resolved_n. Surfaced 2026-05-13
            # because swarm round 2 (reports/swarm_round_2_etf_commodity_triage_)
            # had to use closed_n as a proxy when the dashboard only exposed
            # resolved_n; consumers shouldn't need to know that quirk.
            "n": n,
            "resolved_n": n,
            "win_rate": wr,
            "total_pnl_pct": round(pnl, 2),
            "profit_factor": pf,
            # Aliases expected by template.html and hc_filter.js (contract fix 2026-05-16)
            "wr_pct": wr,
            "pf": pf,
            "pnl_pct": round(pnl, 2),
            # Q2 (2026-05-19): class-level max drawdown as a fraction
            # (0.20 = 20%). Third tier-certification leg alongside pf/wr.
            "max_drawdown_pct": mdd_pct,
            "min_display_n": min_display_n,
            "min_candidate_n": min_candidate_n,
            "min_stable_n": min_stable_n,
        }
    # Guarantee all 6 canonical trading classes always appear so dashboard
    # consumers and tests never need to guard against a missing key.
    _CANONICAL = {"CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND"}
    _stub = {
        "status": "insufficient_data",
        "sample_tier": "insufficient",
        "sizing_allowed": False,
        "n": 0,
        "resolved_n": 0,
        "win_rate": 0.0,
        "total_pnl_pct": 0.0,
        "profit_factor": None,
        "wr_pct": 0.0,
        "pf": None,
        "pnl_pct": 0.0,
        "max_drawdown_pct": None,
        "min_display_n": min_display_n,
        "min_candidate_n": min_candidate_n,
        "min_stable_n": min_stable_n,
    }
    for _cls in _CANONICAL:
        if _cls not in out:
            out[_cls] = dict(_stub)
    return out


def _resolution_class_for_pick(pick: dict) -> str:
    """Bucket a pick into one of the 6 canonical classes (or CRYPTO/OTHER).

    Reuses ``nc_asset_category_for_pick`` for non-crypto buckets and falls back
    to the pick's own ``asset_class`` field (closed picks carry it) so that the
    resolution-coverage panel uses the SAME class taxonomy as
    ``asset_class_health``. FUTURES is folded into COMMODITY only if it is not
    a canonical key on its own — we keep FUTURES separate here since the closed
    ledger carries a distinct FUTURES bucket.
    """
    nc = nc_asset_category_for_pick(pick)
    if nc:
        return nc
    raw = str((pick or {}).get("asset_class") or "").upper()
    if raw in {"CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND", "FUTURES"}:
        return raw
    # Symbol heuristic: crypto pairs end in USDT/USD/BTC etc.
    sym = str((pick or {}).get("symbol") or "").upper()
    if sym.endswith(("USDT", "USDC", "BUSD")) or "USDT" in sym:
        return "CRYPTO"
    return "CRYPTO" if raw == "" else raw


def _open_pick_unresolved_reason(pick: dict) -> str:
    """Classify WHY an open (non-terminal) pick has not been resolved yet.

    Buckets (matches the deliverable's by_reason taxonomy):
      - no-price       : pick has no usable entry/current price -> resolver
                         cannot mark an outcome.
      - orphan-source  : pick's source_system is blank or in the blocked /
                         orphan aggregator set -> nothing feeds it a close.
      - past-max-hold  : pick is older than the per-class max-hold window but
                         still flagged open -> resolver should have expired it.
      - pending        : legitimately still inside its hold window.
    """
    entry = pick.get("entry_price") or pick.get("entry") or pick.get("price")
    current = (
        pick.get("currentPrice")
        or pick.get("current_price")
        or pick.get("_resolved_price")
    )
    try:
        entry_f = float(entry) if entry not in (None, "") else 0.0
    except (TypeError, ValueError):
        entry_f = 0.0
    if entry_f <= 0 and not current:
        return "no-price"
    src = str(pick.get("source_system") or pick.get("source") or "").strip().lower()
    if not src:
        return "orphan-source"
    try:
        if src in {s.lower() for s in BLOCKED_SOURCE_SYSTEMS}:
            return "orphan-source"
    except Exception:
        pass
    # past-max-hold: generous 7-day (168h) ceiling; anything still "open"
    # past that should have been EXPIRED by the resolver.
    try:
        age_h = float(pick.get("age_hours") or 0)
    except (TypeError, ValueError):
        age_h = 0.0
    if age_h > 168.0:
        return "past-max-hold"
    return "pending"


def _build_resolution_coverage(
    resolved_closed: list, open_picks: list
) -> dict:
    """Resolver fix Step 4: per-asset-class resolution-coverage metric.

    For each canonical asset class compute::

        resolved_pct = resolved / (resolved + open_non_terminal)

    plus an ``by_reason`` breakdown of WHY the open picks are unresolved
    (no-price / orphan-source / past-max-hold / pending).

    Inputs are the SAME lists the rest of the payload already uses:
      - ``resolved_closed``: metric-safe resolved trades (closed ledger).
      - ``open_picks``:      currently-open active picks (final_active_picks).

    No live DB call — reads only in-memory pick lists. The 80% gate
    (``RESOLUTION_GATE_PCT``) is surfaced so the dashboard can show a
    visual cue when a class falls below it.
    """
    _CANONICAL = ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND", "FUTURES"]
    gate_pct = 80.0
    out: dict[str, dict] = {}
    for cls in _CANONICAL:
        out[cls] = {
            "resolved": 0,
            "open": 0,
            "resolved_pct": None,
            "by_reason": {
                "no-price": 0,
                "orphan-source": 0,
                "past-max-hold": 0,
                "pending": 0,
            },
        }

    for p in resolved_closed or []:
        cls = _resolution_class_for_pick(p)
        if cls not in out:
            out[cls] = {
                "resolved": 0,
                "open": 0,
                "resolved_pct": None,
                "by_reason": {
                    "no-price": 0,
                    "orphan-source": 0,
                    "past-max-hold": 0,
                    "pending": 0,
                },
            }
        out[cls]["resolved"] += 1

    for p in open_picks or []:
        cls = _resolution_class_for_pick(p)
        if cls not in out:
            out[cls] = {
                "resolved": 0,
                "open": 0,
                "resolved_pct": None,
                "by_reason": {
                    "no-price": 0,
                    "orphan-source": 0,
                    "past-max-hold": 0,
                    "pending": 0,
                },
            }
        out[cls]["open"] += 1
        reason = _open_pick_unresolved_reason(p)
        out[cls]["by_reason"][reason] = out[cls]["by_reason"].get(reason, 0) + 1

    for cls, rec in out.items():
        denom = rec["resolved"] + rec["open"]
        if denom > 0:
            rec["resolved_pct"] = round(rec["resolved"] / denom * 100.0, 1)
        rec["meets_gate"] = (
            rec["resolved_pct"] is not None and rec["resolved_pct"] >= gate_pct
        )

    return {
        "gate_pct": gate_pct,
        "by_class": out,
    }


def _build_slippage_validation(closed_picks: list) -> dict:
    """M-041: Wire slippage_validator scaffold into dashboard payload.

    Analyzes bid-ask slippage per strategy and asset class against closed picks.
    Returns summary with flagged strategies (WARNING/CRITICAL) for the /audit
    dashboard slippage panel. Fail-open: returns {} on any error.
    """
    try:
        from audit_trail.slippage_validator import validate_closed_picks
        if not closed_picks:
            return {}
        result = validate_closed_picks(closed_picks)
        flagged = result.get("flagged_strategies", {})
        summary = result.get("summary", {})
        return {
            "generated_at": result.get("generated_at", ""),
            "summary": summary,
            "flagged_strategies": flagged,
            "asset_class_stats": result.get("asset_class_stats", {}),
        }
    except Exception as _sv_err:
        log.debug("M-041 slippage_validation skip (fail-open): %s", _sv_err)
        return {}


def _build_readiness_payload(asset_class_health: dict, generated_at: str) -> dict:
    """M-031: Build readiness.by_class payload from asset_class_health.

    Derives per-class gate_state, sample_tier, sizing_allowed, and a human-
    readable tier_vs_charter assessment.  Fail-open: any per-class error
    returns an empty dict for that class so the rest of the payload is intact.

    gate_state logic:
      - "DISABLED": FOREX_HARD_DISABLE env is "1" (or not set, default ON)
      - "BLOCKED":  class is in quality_gates.BLOCKED_ASSET_CLASSES
      - "ACTIVE":   sizing_allowed == True (T2 or better)
      - "MONITORING": everything else (below T2 but not blocked/disabled)

    sample_tier / sizing thresholds (CLAUDE.md charter):
      T1:         PF>=2.0, WR>=55, n>=200
      T2:         PF>=1.5, WR>=50, n>=100
      T3:         PF>=1.2, WR>=45, n>=100
      BELOW_T2:   anything else
    """
    # Read FOREX kill-switch (default ON per alpha_engine/config.py line 270)
    _forex_disabled = os.environ.get("FOREX_HARD_DISABLE", "1") not in (
        "0", "false", "FALSE", "False"
    )

    # Read blocked classes from quality_gates (fail-open)
    _blocked_classes: set = set()
    try:
        from audit_trail.quality_gates import BLOCKED_ASSET_CLASSES
        _blocked_classes = set(str(ac).upper() for ac in (BLOCKED_ASSET_CLASSES or set()))
    except Exception:
        pass

    by_class: dict = {}
    for ac, health in (asset_class_health or {}).items():
        try:
            ac_upper = str(ac).upper()
            n = int(health.get("n") or health.get("resolved_n") or 0)
            pf_raw = health.get("profit_factor")
            pf = float(pf_raw) if pf_raw is not None else None
            wr = float(health.get("win_rate") or 0)

            # Determine sample_tier per CLAUDE.md charter thresholds
            if pf is not None and pf >= 2.0 and wr >= 55.0 and n >= 200:
                sample_tier = "T1"
            elif pf is not None and pf >= 1.5 and wr >= 50.0 and n >= 100:
                sample_tier = "T2"
            elif pf is not None and pf >= 1.2 and wr >= 45.0 and n >= 100:
                sample_tier = "T3"
            else:
                sample_tier = "BELOW_T2"

            # sizing_allowed: T2 or better (re-derived; circuit_breaker may
            # have already forced it False on the health dict — honour that)
            _base_sizing = sample_tier in ("T1", "T2")
            sizing_allowed = _base_sizing and health.get("sizing_allowed", True)

            # P0 override: COMMODITY headline PF 2.52 is a COT over-emission
            # artifact (PR #994 dedup; post-dedup real PF 0.12-0.33 per forensic
            # report 2026-05-16). Force sizing_allowed=False until a clean 50-pick
            # post-dedup cohort validates real edge. Override flag:
            # COMMODITY_FORCE_MONITOR=0 disables this guard (default ON = safe).
            if ac_upper == "COMMODITY":
                _cmod_guard = os.environ.get("COMMODITY_FORCE_MONITOR", "1") not in (
                    "0", "false", "FALSE", "False"
                )
                if _cmod_guard:
                    sizing_allowed = False

            # gate_state
            if ac_upper == "FOREX" and _forex_disabled:
                gate_state = "DISABLED"
            elif ac_upper in _blocked_classes:
                gate_state = "BLOCKED"
            elif sizing_allowed:
                gate_state = "ACTIVE"
            else:
                gate_state = "MONITORING"

            # tier_vs_charter: human-readable assessment
            if sample_tier == "T1":
                tier_vs_charter = "RENAISSANCE_TIER"
            elif sample_tier == "T2":
                tier_vs_charter = "T2_CHARTER_MET"
            elif sample_tier == "T3":
                tier_vs_charter = "T3_ELIGIBLE"
            elif n < 100:
                tier_vs_charter = "INSUFFICIENT_SAMPLE"
            else:
                tier_vs_charter = "SUB_T2"

            by_class[ac_upper] = {
                "n": n,
                "pf": round(pf, 2) if pf is not None else None,
                "wr": round(wr, 1),
                "gate_state": gate_state,
                "sizing_allowed": sizing_allowed,
                "sample_tier": sample_tier,
                "tier_vs_charter": tier_vs_charter,
            }
        except Exception:
            by_class[str(ac).upper()] = {}

    # VIX snapshot — M-031 extension (2026-05-16)
    # Gate logic: equity picks blocked only when BOTH gate is active AND regime is HIGH_VOL.
    _vix_level = None
    _vix_regime = "UNKNOWN"
    try:
        from audit_trail.vix_regime_gate import get_cached_vix
        _vix_raw = get_cached_vix()
        if _vix_raw is not None:
            _vix_level = round(float(_vix_raw), 4)
            _vix_threshold = 22.0
            _vix_regime = "LOW_VOL" if _vix_level < _vix_threshold else "HIGH_VOL"
    except Exception:
        pass

    _vix_threshold = 22.0
    _gate_active = os.environ.get("VIX_REGIME_GATE_ENABLED", "0") == "1"
    # Picks allowed: always allowed when gate is off; blocked only on HIGH_VOL when gate is on
    _equity_picks_allowed = not (_gate_active and _vix_regime == "HIGH_VOL")

    vix_snapshot = {
        "vix_level": _vix_level,
        "vix_threshold": _vix_threshold,
        "regime": _vix_regime,
        "equity_gate_active": _gate_active,
        "equity_picks_allowed": _equity_picks_allowed,
    }

    return {
        "generated_at": generated_at,
        "by_class": by_class,
        "vix_snapshot": vix_snapshot,
    }


def enrich_health_with_recent_window(
    asset_class_health: dict,
    recent_closed: list,
    *,
    window_days: int = 60,
    now=None,
) -> None:
    """Stamp `pf_60d`, `wr_60d`, `n_60d` onto each class in asset_class_health.

    Detects baseline shifts (e.g., COMMODITY headline PF 4.03 vs historical
    1.78 — see reports/swarm_round_2_etf_commodity_triage_2026-05-13.md).
    Compares recent-window edge against full-history; a large divergence
    flags the headline as either regime change or resolver-baseline shift.

    Mutates `asset_class_health` in place. Fail-open: any per-class error
    is swallowed so a single bad timestamp can't break the dashboard.
    """
    from datetime import datetime, timedelta, timezone

    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)

    def _parse_ts(ts):
        if not ts:
            return None
        if isinstance(ts, datetime):
            return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    by_class: dict[str, dict] = {}
    for r in recent_closed or []:
        if not isinstance(r, dict):
            continue
        ac = str(r.get("asset_class", "") or "").upper()
        if not ac:
            continue
        outc = (r.get("_outcome") or r.get("status") or "").upper()
        # Accept both WIN/LOSS (_outcome field) and WON/LOST (status field).
        if outc not in ("WIN", "WON", "LOSS", "LOST"):
            continue
        ts = _parse_ts(r.get("timestamp") or r.get("close_time"))
        if ts is None or ts < cutoff:
            continue
        slot = by_class.setdefault(ac, {"wins": 0, "losses": 0,
                                        "win_pnl": 0.0, "loss_pnl": 0.0})
        try:
            pnl = float(r.get("pnl_pct", 0) or 0)
        except (TypeError, ValueError):
            pnl = 0.0
        if outc in ("WIN", "WON"):
            slot["wins"] += 1
            slot["win_pnl"] += abs(pnl)
        else:
            slot["losses"] += 1
            slot["loss_pnl"] += abs(pnl)

    for ac, agg in by_class.items():
        if ac not in asset_class_health:
            continue
        try:
            n = agg["wins"] + agg["losses"]
            if n == 0:
                continue
            wr = 100.0 * agg["wins"] / n
            pf = (agg["win_pnl"] / agg["loss_pnl"]) if agg["loss_pnl"] > 0 else None
            asset_class_health[ac]["n_60d"] = n
            asset_class_health[ac]["wr_60d"] = round(wr, 1)
            asset_class_health[ac]["pf_60d"] = round(pf, 2) if pf is not None else None
        except Exception:  # pragma: no cover
            pass


def _compute_closed_pnl_concentration_by_source(
    resolved_closed: list, max_pnl_cap: float = 500.0
):
    """Share of capped *winning* PnL by source_system (pipeline concentration)."""
    by_sys: dict[str, float] = {}
    for p in resolved_closed:
        sys = (p.get("source_system") or "unknown").strip() or "unknown"
        raw = float(p.get("pnl_pct", 0) or 0)
        pnl = max(-max_pnl_cap, min(max_pnl_cap, raw))
        if pnl > 0:
            by_sys[sys] = by_sys.get(sys, 0.0) + pnl
    pos_total = sum(by_sys.values())
    if pos_total <= 0:
        return None
    ranked = sorted(by_sys.items(), key=lambda x: x[1], reverse=True)
    top1_sys, top1_pnl = ranked[0]
    top3_pnl = sum(v for _, v in ranked[:3])
    top_sources = []
    for s, v in ranked[:5]:
        top_sources.append(
            {
                "source_system": s,
                "share_pct": round(100.0 * v / pos_total, 1),
                "pnl_capped_sum": round(v, 2),
            }
        )
    return {
        "positive_pnl_sum_capped": round(pos_total, 2),
        "top1_source_system": top1_sys,
        "top1_share_pct": round(100.0 * top1_pnl / pos_total, 1),
        "top3_share_pct": round(100.0 * top3_pnl / pos_total, 1),
        "top_sources": top_sources,
    }


def _is_verified_alpha_pick(pick: dict) -> bool:
    """Determine if a pick qualifies as 'Verified Alpha'.

    Verified Alpha includes:
    - Prediction market signals (Kalshi, Polymarket, consensus)
    - Copy trader signals with verified track records
    - High-score and consensus copy trader picks
    """
    source = str((pick or {}).get("source_system", "") or "").strip().lower()
    strategy = str((pick or {}).get("strategy", "") or "").strip().lower()

    # Prediction market sources
    if source in _VERIFIED_ALPHA_PM_SOURCES:
        return True

    # Copy trader sources with audit trail
    if source in _VERIFIED_ALPHA_COPY_SOURCES:
        return True

    # Strategy prefixes indicating verified copy trading
    if any(strategy.startswith(prefix) for prefix in _VERIFIED_ALPHA_COPY_PREFIXES):
        return True

    # Curated multi-asset strategies
    if (
        source == "multi_asset_copytrader"
        and strategy in _VERIFIED_ALPHA_CURATED_COPY_STRATEGIES
    ):
        return True

    # Picks with verified trader labels or strong forward track records
    # Normalize WR: could be stored as 0.60 (60%) or 60 (60%)
    forward_wr = _float((pick or {}).get("forward_wr"))
    if forward_wr > 1.5:  # Stored as percentage (e.g., 60 = 60%)
        forward_wr = forward_wr / 100.0
    forward_trades = int(_float((pick or {}).get("forward_trades", 0)))
    if forward_wr >= 0.55 and forward_trades >= 10:  # Tightened n>=5->10 (compromise) (2026-04-15): n>=5..9 picks had 66.7% WR; n>=5 passed 94%% of picks, no edge
        return True

    # v102: Expanded verified-alpha gates
    # Systems with history WR >= 55% on 20+ closed trades
    history_wr = _float((pick or {}).get("history_wr"))
    if history_wr > 1.5:
        history_wr = history_wr / 100.0
    history_trades = int(_float((pick or {}).get("history_trades", 0)))
    # 2026-04-05 (tweak #1): Add rolling freshness check. Stale history_wr was letting
    # alpha_engine (1094 closed picks, 34.5% realized WR) flood VA cohort and drag
    # realized WR from 55%+ down to 44%. Now require rolling_90d_wr or recent live
    # performance to confirm history is still applicable.
    if history_wr >= 0.55 and history_trades >= 20:
        _rolling_90d_wr = _float((pick or {}).get("rolling_90d_wr"))
        if _rolling_90d_wr > 1.5: _rolling_90d_wr = _rolling_90d_wr / 100.0
        _recent_wr = _float((pick or {}).get("strat_last10_wr") or (pick or {}).get("fwd_last10_wr") or 0)
        if _recent_wr > 1.5: _recent_wr = _recent_wr / 100.0
        # If we have recent data, it must still show edge (>=0.50). If no recent data,
        # fall through to other gates rather than promoting on stale history alone.
        if (_rolling_90d_wr >= 0.50) or (_recent_wr >= 0.50):
            return True
        if _rolling_90d_wr == 0 and _recent_wr == 0:
            # No recent data available — use history with caution, keep old behavior
            return True

    # Walk-forward validated picks (p-value < 0.05)
    wf_p = _float((pick or {}).get("wf_p_value"))
    if 0 < wf_p < 0.05:
        return True

    # v102: Robustness - check strat_fwd_wr fields if primary forward_wr is missing
    fwd_wr = _float(pick.get("strat_fwd_wr", pick.get("forward_wr")))
    if fwd_wr > 1.5:
        fwd_wr = fwd_wr / 100.0
    fwd_trades = int(_float(pick.get("strat_fwd_trades", pick.get("forward_trades", 0))))
    if fwd_wr >= 0.55 and fwd_trades >= 10:  # Tightened n>=5->10 (compromise) (2026-04-15): n>=5..9 picks had 66.7% WR; n>=5 passed 94%% of picks, no edge
        return True

    # High-score + high-trust picks (score >= 80, trust_score >= 5)
    # Lowered 6→5: ts=5 WR=75.9% (n=428) > ts=6 WR=67.0% (n=215); triples HC volume
    score = _float((pick or {}).get("score", 0))
    trust = _float((pick or {}).get("trust_score", 0))
    if score >= 80 and trust >= 5:
        return True

    # High-conviction consensus with decent history
    agreement = int(_float(pick.get("agreement_count", 0)))
    if agreement >= 3 and fwd_wr >= 0.50 and fwd_trades >= 3:
        return True

    # 2026-04-05 (tweak #2): Explicit REALIZED ALPHA exemption.
    # Sources with >=100 closed picks at realized WR >=55% are auto-promoted to VA.
    # This whitelist was computed from 3500 closed picks: claude_gainer_st (540 closed,
    # 63.0% WR, +248% cum), kimi_riseoftheclaw (54, 57.4%, +37%), signal_validation
    # (21, 76.2%, +29%). Prevents under-representation of proven winners - previously
    # claude_gainer_st had only 2/35 VA slots despite being the best-realized source.
    _REALIZED_ALPHA_SOURCES = {
        "claude_gainer_st",       # 540 closed, 63.0% WR, +248% cum
        "signal_validation",      # 21 closed, 76.2% WR, +29% cum
        "dna_winner_picks",       # 57 closed, 56.1% WR, +42% cum
    }
    if source in _REALIZED_ALPHA_SOURCES:
        return True

    return False


def _normalize_wr_pct(value) -> float | None:
    wr = _float(value)
    if wr <= 0:
        return None
    if wr <= 1.5:
        wr *= 100.0
    if wr > 100:
        return None
    return round(wr, 2)


def _shrink_wr_pct(
    wr_pct: float | None, sample_size: int | float | None
) -> float | None:
    if wr_pct is None:
        return None
    sample = max(0, int(_float(sample_size)))
    weight = min(sample, 20) / 20.0
    return round(50.0 + (float(wr_pct) - 50.0) * weight, 2)


def _extract_verified_alpha_audit(pick: dict) -> dict | None:
    sample_candidates = [
        int(_float((pick or {}).get("history_trades"))),
        int(_float((pick or {}).get("forward_trades"))),
        int(_float((pick or {}).get("consensus_count"))),
    ]
    sample = max(sample_candidates) if sample_candidates else 0

    for field in (
        "history_wr_bayes",
        "profile_crypto_wr_bayes",
        "history_wr",
        "profile_crypto_wr",
        "forward_wr",
    ):
        wr_pct = _normalize_wr_pct((pick or {}).get(field))
        if wr_pct is None:
            continue
        shrunk = _shrink_wr_pct(wr_pct, sample)
        return {
            "wr_pct": wr_pct,
            "shrunk_wr_pct": shrunk,
            "sample_size": sample,
            "field": field,
        }
    return None


def _enrich_va_cohort_fields(pick: dict) -> None:
    """Attach verifiable cohort metadata for Verified Alpha rows (HF P0 truth layer)."""
    if not _is_verified_alpha_pick(pick):
        return
    if pick.get("va_cohort_id"):
        return
    audit = _extract_verified_alpha_audit(pick)
    pick["va_rule_version"] = "1"
    if audit:
        fld = str(audit.get("field") or "wr").replace(" ", "_")
        n = int(_float(audit.get("sample_size")))
        pick["va_cohort_id"] = "va_%s_n%d" % (fld, n)
        pick["va_cohort_n"] = n
        pick["va_cohort_basis"] = str(audit.get("field") or "")
        pick["va_cohort_wr_pct"] = audit.get("wr_pct")
    else:
        n = max(
            int(_float(pick.get("forward_trades", 0))),
            int(_float(pick.get("history_trades", 0))),
            int(_float(pick.get("strat_fwd_trades", 0))),
        )
        pick["va_cohort_id"] = "va_multi_gate"
        pick["va_cohort_n"] = n
        pick["va_cohort_basis"] = "composite_gate"
        pick["va_cohort_wr_pct"] = None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _closed_pick_identity(pick: dict) -> tuple:
    return (
        str((pick or {}).get("source_system") or ""),
        str((pick or {}).get("strategy") or ""),
        str((pick or {}).get("symbol") or ""),
        str((pick or {}).get("direction") or ""),
        str((pick or {}).get("timestamp") or ""),
        str((pick or {}).get("status") or ""),
    )


def _should_reserve_closed_pick_for_track_record(pick: dict) -> bool:
    source = str((pick or {}).get("source_system", "") or "").strip().lower()
    if source in _TRACK_RECORD_CLOSED_SOURCES:
        return True
    # Reserve non-crypto picks so they aren't crowded out by high-frequency crypto
    asset_class = str((pick or {}).get("asset_class") or (pick or {}).get("category") or "").upper().strip()
    if asset_class in _NON_CRYPTO_ASSET_CLASSES:
        return True
    return _is_verified_alpha_pick(pick)


_NC_ASSET_CLASSES = frozenset(
    {"FOREX", "EQUITY", "STOCK", "COMMODITY", "FUTURES", "ETF", "BOND"}
)
_NC_ALIAS_MAP = {
    "FX": "FOREX",
    "EQUITIES": "EQUITY",
    "STOCKS": "STOCK",
    "COMMODITIES": "COMMODITY",
    "FUTURE": "FUTURES",
    "BONDS": "BOND",
}


def _normalize_nc_asset(value) -> str:
    ac = str(value or "").upper().strip()
    return _NC_ALIAS_MAP.get(ac, ac)


_PER_ASSET_CLASSES = ("CRYPTO", "EQUITY", "FOREX", "COMMODITY", "FUTURES", "BOND", "ETF")


def _normalize_per_asset_class(value) -> str:
    ac = str(value or "").upper().strip()
    return {
        "COMMODITIES": "COMMODITY",
        "BONDS": "BOND",
        "ETFS": "ETF",
        "STOCK": "EQUITY",
        "STOCKS": "EQUITY",
    }.get(ac, ac)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 3) if values else 0.0


def _build_per_asset_quality_summary(
    active_rows: list[dict], smart_rows: list[dict], generated_at: str
) -> tuple[dict[str, list[dict]], dict[str, dict[str, object]]]:
    smart_by_asset: dict[str, list[dict]] = {ac: [] for ac in _PER_ASSET_CLASSES}
    active_by_asset: dict[str, list[dict]] = {ac: [] for ac in _PER_ASSET_CLASSES}
    for row in active_rows or []:
        ac = _normalize_per_asset_class(row.get("asset_class"))
        if ac in active_by_asset:
            active_by_asset[ac].append(row)
    for row in smart_rows or []:
        ac = _normalize_per_asset_class(row.get("asset_class"))
        if ac in smart_by_asset:
            smart_by_asset[ac].append(row)

    summary: dict[str, dict[str, object]] = {}
    for ac in _PER_ASSET_CLASSES:
        class_active = active_by_asset[ac]
        class_smart = smart_by_asset[ac]
        score_vals = [
            float(r.get("score"))
            for r in class_active
            if r.get("score") is not None and str(r.get("score")).strip() != ""
        ]
        fwr_vals: list[float] = []
        for r in class_active:
            raw = r.get("forward_wr", r.get("forward_win_rate"))
            if raw is None or str(raw).strip() == "":
                continue
            try:
                v = float(raw)
                if v > 1.0:
                    v = v / 100.0
                fwr_vals.append(v)
            except (TypeError, ValueError):
                continue
        cfg = ASSET_CLASS_SMART_THRESHOLDS.get(ac) or {}
        min_score = float(cfg.get("min_score", 0.0))
        min_fwr = float(cfg.get("min_fwr", 0.0))
        min_trades = int(cfg.get("min_trades", 0))
        avg_score = _mean(score_vals)
        avg_fwr = _mean(fwr_vals)
        active_count = len(class_active)
        smart_count = len(class_smart)
        threshold_pass = (
            active_count == 0
            or (
                smart_count > 0
                and avg_score >= min_score
                and (avg_fwr == 0.0 or avg_fwr >= min_fwr)
                and active_count >= min_trades
            )
        )
        summary[ac] = {
            "activeCount": active_count,
            "smartCount": smart_count,
            "avgScore": avg_score,
            "forwardWR": avg_fwr,
            "thresholdPass": bool(threshold_pass),
            "lastUpdated": generated_at,
            "thresholds": {
                "minScore": min_score,
                "minForwardWR": min_fwr,
                "minTrades": min_trades,
            },
        }
    return smart_by_asset, summary


def nc_asset_category_for_pick(pick: dict) -> str | None:
    """Non-crypto performance bucket: asset_class/category first, then symbol heuristics
    aligned with ``audit_dashboard/template.html`` ``matchCategory`` (forex =X, XAU/XAG, =F).
    Falls back to ``classify_asset`` so plain tickers (ETF, equity, bond) still bucket
    when feeders omit ``asset_class`` (fixes under-counted Futures / ETF / Bond cards).
    """
    for field in ("asset_class", "category"):
        normalized = _normalize_nc_asset(pick.get(field))
        if normalized == "MICRO_FUTURES":
            return "FUTURES"
        if normalized in _NC_ASSET_CLASSES:
            return normalized
    sym = str((pick or {}).get("symbol") or "").upper()
    if "=X" in sym:
        return "FOREX"
    if sym.startswith("XAU") or sym.startswith("XAG"):
        return "COMMODITY"
    if sym.endswith("=F"):
        return "FUTURES"
    if not sym:
        return None
    try:
        from audit_trail.asset_classification import AssetClass, classify_asset

        resolved = classify_asset(sym)
        if resolved in (AssetClass.CRYPTO, AssetClass.MEME, AssetClass.UNKNOWN):
            return None
        if resolved == AssetClass.MICRO_FUTURES:
            return "FUTURES"
        val = resolved.value
        if val in _NC_ASSET_CLASSES:
            return val
    except Exception:
        pass
    return None


def _dedupe_closed_trades_by_canonical_id(
    closed: list[dict],
) -> tuple[list[dict], int]:
    """Collapse duplicate closed rows that share the same ``id`` (institutional shadow rows,
    MySQL re-ingest, etc.). Keeps the copy whose ``pnl_pct`` best matches entry/exit-implied PnL.
    """
    from collections import defaultdict

    buckets: dict[str, list[dict]] = defaultdict(list)
    out_no_id: list[dict] = []
    for p in closed or []:
        if not isinstance(p, dict):
            continue
        pid = str((p.get("id") or "")).strip()
        if pid and pid.lower() not in ("null", "none", "-"):
            buckets[pid].append(p)
        else:
            out_no_id.append(p)
    merged: list[dict] = []
    dropped = 0

    def _implied_pnl_entry_exit(p: dict) -> float | None:
        e = _float(p.get("entry_price", 0) or 0)
        x = _float(p.get("exit_price", 0) or 0)
        if e <= 0 or x <= 0:
            return None
        d = str(p.get("direction", "LONG")).upper()
        if d == "SHORT":
            return round((e - x) / e * 100, 4)
        return round((x - e) / e * 100, 4)

    for _pid, group in buckets.items():
        if len(group) == 1:
            merged.append(group[0])
            continue

        def _quality_score(p: dict) -> float:
            stored = _float(p.get("pnl_pct", 0) or 0)
            imp = _implied_pnl_entry_exit(p)
            score = 0.0
            if imp is not None:
                score -= abs(stored - imp)
                if abs(stored - imp) < 0.05:
                    score += 100.0
            else:
                score -= min(500.0, abs(stored))
            if _float(p.get("exit_price", 0) or 0) > 0:
                score += 20.0
            if abs(stored) > 75:
                score -= 200.0
            er = str(p.get("exit_reason", "") or "").upper()
            if er in ("", "CLOSED", "UNKNOWN") and abs(stored) > 20:
                score -= 50.0
            return score

        best = max(group, key=_quality_score)
        merged.append(best)
        dropped += len(group) - 1

    return out_no_id + merged, dropped


def _build_recent_closed_picks(
    resolved_closed: list[dict],
    max_picks: int = MAX_CLOSED_PICKS,
    reserved_slots: int = RESERVED_TRACK_RECORD_CLOSED_PICKS,
    nc_reserved_slots: int = RESERVED_NON_CRYPTO_CLOSED_PICKS,
) -> list[dict]:
    """Build the published closed list with reservations for track-record and non-crypto.

    Two reservation passes run first (non-crypto + track-record) so that the
    payload cap never crowds out equity/forex/commodity/ETF history.

    Non-crypto reservation is balanced per asset class so smaller categories
    (ETF, FUTURES, BOND) don't get crowded out by larger ones (FOREX, EQUITY).
    """
    ordered = sorted(
        resolved_closed or [], key=lambda x: x.get("timestamp", ""), reverse=True
    )
    # Strip banned-source and banned-tier rows before reservation/cap logic so
    # they never pollute class-level PF/WR/MaxDD metrics in the dashboard.
    ordered = [
        pick
        for pick in ordered
        if str(get_tier(str(pick.get("source_system") or "")) or "").upper() != "BANNED"
        and str(
            pick.get("trust_tier") or pick.get("at_issue_trust_tier") or ""
        ).upper()
        not in _HARD_BLOCKED_TRUST_TIERS
    ]
    if len(ordered) <= max_picks:
        return ordered

    reserved_slots = max(0, min(int(reserved_slots), int(max_picks)))
    nc_reserved_slots = max(0, min(int(nc_reserved_slots), int(max_picks) - reserved_slots))
    seen: set[tuple] = set()

    # Pass 1: Reserve non-crypto closed picks, BALANCED per category.
    # Without per-category quota, FOREX/EQUITY (largest populations) crowd out
    # ETF/FUTURES/BOND entirely — drill-down modals then show empty tables.
    nc_reserved: list[dict] = []
    if nc_reserved_slots > 0:
        # Bucket non-crypto picks by category (same rules as compute_non_crypto_performance)
        nc_buckets: dict[str, list[dict]] = {}
        for pick in ordered:
            cat = nc_asset_category_for_pick(pick)
            if cat is None:
                continue
            nc_buckets.setdefault(cat, []).append(pick)

        # Per-category quota: at least floor(nc_reserved_slots / 7) per category,
        # but never more than what the category has. Remaining slots distributed
        # proportionally to category size.
        num_cats = len(_NC_ASSET_CLASSES)  # 7 categories
        base_quota = max(1, nc_reserved_slots // num_cats)
        quotas: dict[str, int] = {}
        for cat in _NC_ASSET_CLASSES:
            available = len(nc_buckets.get(cat, []))
            quotas[cat] = min(base_quota, available)

        # Distribute remaining slots (from unused small-category quota)
        # proportionally among categories that have more picks to offer.
        used = sum(quotas.values())
        remaining = nc_reserved_slots - used
        if remaining > 0:
            # Categories that can hold more
            expandable = [c for c in _NC_ASSET_CLASSES if len(nc_buckets.get(c, [])) > quotas[c]]
            while remaining > 0 and expandable:
                # Round-robin among expandable categories by remaining capacity
                expandable.sort(key=lambda c: -(len(nc_buckets.get(c, [])) - quotas[c]))
                progress = False
                for cat in list(expandable):
                    if remaining <= 0:
                        break
                    if len(nc_buckets.get(cat, [])) > quotas[cat]:
                        quotas[cat] += 1
                        remaining -= 1
                        progress = True
                    else:
                        expandable.remove(cat)
                if not progress:
                    break

        # Fill reservation per category quota (in timestamp desc order per bucket)
        for cat, bucket in nc_buckets.items():
            quota = quotas.get(cat, 0)
            for pick in bucket[:quota]:
                key = _closed_pick_identity(pick)
                if key in seen:
                    continue
                nc_reserved.append(pick)
                seen.add(key)

    # Pass 2: Reserve track-record picks (copy-traders, prediction markets)
    tr_reserved: list[dict] = []
    for pick in ordered:
        if not _should_reserve_closed_pick_for_track_record(pick):
            continue
        key = _closed_pick_identity(pick)
        if key in seen:
            continue
        tr_reserved.append(pick)
        seen.add(key)
        if len(tr_reserved) >= reserved_slots:
            break

    # Pass 3: Fill remaining slots with most recent picks
    recent_closed: list[dict] = nc_reserved + tr_reserved
    for pick in ordered:
        key = _closed_pick_identity(pick)
        if key in seen:
            continue
        recent_closed.append(pick)
        seen.add(key)
        if len(recent_closed) >= max_picks:
            break

    # Resolver-gap fix 2026-05-13: outcome_resolver.py:960 sets `status`,
    # but walkforward_validator.py:59/231 and the new charter_drift_circuit_
    # breaker.py both expect `_outcome`. Backfill `_outcome` from `status` so
    # every consumer downstream sees the resolved verdict. Subagent
    # investigation confirmed this field-name mismatch was the root cause
    # of "0 of 3,500 picks have WIN/LOSS outcomes" in recent_closed.
    return sorted(
        [
            {**p, "_outcome": (p.get("_outcome") or p.get("status") or "").upper()}
            for p in recent_closed[:max_picks]
        ],
        key=lambda x: x.get("timestamp", ""),
        reverse=True,
    )


def _apply_issue186_exit_normalization(resolved_closed: list[dict]) -> int:
    """Refine legacy binary exit labels using TP/SL distance (issue #186).

    See ``normalize_exit_reason`` in ``quality_gates.py``. Skipped when env
    ``AUDIT_SKIP_EXIT_NORMALIZATION=1`` is set. Persists ``exit_reason_raw`` once
    for audit; sets ``exit_reason`` to the canonical refined value.
    """
    if os.environ.get("AUDIT_SKIP_EXIT_NORMALIZATION", "").strip() == "1":
        return 0
    if not resolved_closed:
        return 0
    changed = 0
    for p in resolved_closed:
        if not isinstance(p, dict):
            continue
        if "exit_reason_raw" not in p:
            p["exit_reason_raw"] = str(
                p.get("exit_reason") or p.get("close_reason") or ""
            )
        before_display = str(p.get("exit_reason") or "").strip().upper()
        p["exit_reason"] = p["exit_reason_raw"]
        try:
            after = normalize_exit_reason(p)
        except Exception:
            after = before_display or "UNKNOWN"
        if str(after).upper() != before_display:
            changed += 1
        p["exit_reason"] = after
    return changed


def _compute_verified_alpha_summary(
    active_picks: list[dict],
    smart_picks: list[dict],
    closed_picks: list[dict],
) -> dict:
    active_rows = [p for p in (active_picks or []) if _is_verified_alpha_pick(p)]
    smart_rows = [p for p in (smart_picks or []) if _is_verified_alpha_pick(p)]
    closed_rows = [p for p in (closed_picks or []) if _is_verified_alpha_pick(p)]

    wins = losses = flat = 0
    total_pnl = 0.0
    for pick in closed_rows:
        pnl = _float(pick.get("pnl_pct"))
        total_pnl += pnl
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1
        else:
            flat += 1

    realized_total = wins + losses + flat
    realized_wr = round((wins / realized_total) * 100, 1) if realized_total else None
    expectancy = round(total_pnl / realized_total, 2) if realized_total else None

    source_mix = defaultdict(int)
    audited_rows = []
    shrunk_values = []
    raw_values = []
    weighted_sum = 0.0
    weighted_weight = 0.0
    for pick in active_rows:
        source_mix[str(pick.get("source_system") or "unknown")] += 1
        audit_meta = _extract_verified_alpha_audit(pick)
        if not audit_meta:
            continue
        audited_rows.append(audit_meta)
        raw_values.append(audit_meta["wr_pct"])
        if audit_meta["shrunk_wr_pct"] is not None:
            shrunk_values.append(audit_meta["shrunk_wr_pct"])
            weight = max(1.0, min(float(audit_meta["sample_size"] or 0), 20.0))
            weighted_sum += audit_meta["shrunk_wr_pct"] * weight
            weighted_weight += weight

    audited_weighted = (
        round(weighted_sum / weighted_weight, 1) if weighted_weight > 0 else None
    )
    audited_avg = round(sum(raw_values) / len(raw_values), 1) if raw_values else None
    audited_median = round(_median(shrunk_values), 1) if shrunk_values else None
    audited_sample_avg = (
        round(sum(a["sample_size"] for a in audited_rows) / len(audited_rows), 1)
        if audited_rows
        else None
    )

    note = (
        "No resolved verified-alpha trades yet; use audited source WR for upstream edge and the live verified-alpha mix for current portfolio composition."
        if realized_total == 0
        else "Verified-alpha realized WR reflects only the PM / auditable pro-trader cohort, separate from the all-systems headline."
    )

    return {
        "active_count": len(active_rows),
        "smart_count": len(smart_rows),
        "active_share_pct": round(
            len(active_rows) / max(len(active_picks or []), 1) * 100, 1
        ),
        "smart_share_pct": round(
            len(smart_rows) / max(len(smart_picks or []), 1) * 100, 1
        )
        if smart_picks
        else 0.0,
        "unique_sources": len(source_mix),
        "source_mix": dict(
            sorted(source_mix.items(), key=lambda item: (-item[1], item[0]))
        ),
        "realized": {
            "trades": realized_total,
            "wins": wins,
            "losses": losses,
            "flat": flat,
            "win_rate": realized_wr,
            "total_pnl_pct": round(total_pnl, 2),
            "expectancy": expectancy,
        },
        "audited": {
            "covered_active_picks": len(audited_rows),
            "avg_wr_pct": audited_avg,
            "weighted_wr_pct": audited_weighted,
            "median_wr_pct": audited_median,
            "avg_sample_size": audited_sample_avg,
        },
        # Slim list so peers / APIs need not re-run _is_verified_alpha_pick on the full book.
        "active_pick_refs": [
            {
                "id": pick.get("id"),
                "symbol": pick.get("symbol"),
                "source_system": pick.get("source_system"),
                "strategy": pick.get("strategy"),
                "direction": pick.get("direction") or pick.get("signal_type"),
            }
            for pick in active_rows
        ],
        "status_note": note,
    }


def _prepare_prediction_market_consensus_signal(raw_pick: dict) -> dict:
    pick = dict(raw_pick or {})
    consensus_data = pick.get("consensus_data", {}) or {}
    source_count = int(
        _float(
            pick.get("source_count")
            or consensus_data.get("source_category_count")
            or consensus_data.get("num_sources")
            or pick.get("agreement_count")
            or 0
        )
    )
    pick["agreement_count"] = source_count
    pick["source_count"] = source_count
    source_systems = (
        pick.get("pm_source_systems")
        or pick.get("source_systems")
        or pick.get("sources")
        or consensus_data.get("sources")
        or []
    )
    if isinstance(source_systems, str):
        source_systems = [s.strip() for s in source_systems.split(",") if s.strip()]
    deduped_sources = []
    seen_sources = set()
    for source_name in source_systems:
        clean_name = str(source_name or "").strip()
        if not clean_name or clean_name in seen_sources:
            continue
        seen_sources.add(clean_name)
        deduped_sources.append(clean_name)
    pick["pm_source_systems"] = deduped_sources
    if not pick.get("source_systems"):
        pick["source_systems"] = list(deduped_sources)

    if pick.get("high_conviction") is None:
        fwd_wr = _float(
            pick.get("forward_wr")
            or pick.get("strat_fwd_wr")
            or consensus_data.get("forward_wr")
            or 0
        )
        fwd_trades = int(
            _float(
                pick.get("forward_trades")
                or pick.get("strat_fwd_trades")
                or consensus_data.get("forward_trades")
                or 0
            )
        )
        consensus_bias = _float(
            consensus_data.get("consensus_score")
            or pick.get("consensus_score")
            or 0
        )
        pick["high_conviction"] = bool(
            consensus_data.get("high_conviction")
            or (
                source_count >= 3
                and fwd_wr >= 55
                and fwd_trades >= 8
                and consensus_bias >= 0
            )
        )

    pick["source_system"] = "prediction_market_consensus"
    if not pick.get("strategy"):
        pick["strategy"] = "prediction_market_consensus"
    if not pick.get("type_label"):
        pick["type_label"] = "🔮 PM Consensus"

    return pick


def _load_prediction_market_consensus_signals() -> tuple[list[dict], str | None]:
    primary_path = ROOT / "alpha_engine" / "data" / "prediction_market_picks.json"
    primary_raw = _safe_json(primary_path)
    primary_signals = []
    if isinstance(primary_raw, dict):
        primary_signals = primary_raw.get("picks", []) or []
    elif isinstance(primary_raw, list):
        primary_signals = primary_raw
    if primary_signals:
        return (
            [
                _prepare_prediction_market_consensus_signal(p)
                for p in primary_signals
                if isinstance(p, dict)
            ],
            str(primary_path),
        )

    fallback_path = (
        ROOT / "prediction_market_agents" / "data" / "consensus_signals.json"
    )
    fallback_raw = _safe_json(fallback_path)
    fallback_signals = []
    if isinstance(fallback_raw, dict):
        fallback_signals = fallback_raw.get("signals", []) or []
    elif isinstance(fallback_raw, list):
        fallback_signals = fallback_raw
    if fallback_signals:
        return (
            [
                _prepare_prediction_market_consensus_signal(p)
                for p in fallback_signals
                if isinstance(p, dict)
            ],
            str(fallback_path),
        )

    return ([], None)


def _refresh_verified_alpha_system_stats(
    systems: list[dict], active_picks: list[dict]
) -> None:
    """Refresh audited WR fallback fields from the final enriched active feed."""
    if not systems or not active_picks:
        return

    audit_by_system: dict[str, dict] = {}
    for pick in active_picks:
        if not _is_verified_alpha_pick(pick):
            continue
        audit_meta = _extract_verified_alpha_audit(pick)
        if not audit_meta:
            continue
        sys_name = str(pick.get("source_system") or "").strip()
        if not sys_name:
            continue
        bucket = audit_by_system.setdefault(
            sys_name,
            {
                "covered": 0,
                "weighted_sum": 0.0,
                "weighted_weight": 0.0,
                "sample_sum": 0.0,
            },
        )
        sample = max(1, int(_float(audit_meta.get("sample_size"))))
        effective_wr = audit_meta.get("shrunk_wr_pct")
        if effective_wr is None:
            effective_wr = audit_meta.get("wr_pct")
        if effective_wr is None:
            continue
        bucket["covered"] += 1
        bucket["weighted_sum"] += float(effective_wr) * sample
        bucket["weighted_weight"] += sample
        bucket["sample_sum"] += sample

    for system in systems:
        name = str((system or {}).get("name") or "").strip()
        stats = audit_by_system.get(name)
        if not stats or stats["weighted_weight"] <= 0:
            continue
        audited_wr = round(stats["weighted_sum"] / stats["weighted_weight"], 1)
        system["audited_wr_pct"] = audited_wr
        system["audited_wr_coverage"] = int(stats["covered"])
        system["audited_avg_sample_size"] = round(
            stats["sample_sum"] / stats["covered"], 1
        )
        if int(_float(system.get("resolved_picks"))) <= 0:
            system["win_rate_basis"] = "audited"
            system["display_win_rate_pct"] = audited_wr
            # P1 Money-Maker-Ready 2026-05-14: flag systems requiring
            # walk-forward validation before paper/live use.
            _requires_walkahead = _get_blocked_sets().get("requires_walkahead_audit", set())
            if name in _requires_walkahead:
                system["requires_walkforward_audit"] = True
                system["walkforward_audit_reason"] = (
                    "Suspicious headline metrics — may be data artifact "
                    "(over-emission, single-symbol concentration, or look-ahead bias). "
                    "Requires clean walk-forward split (train pre-2025 / test 2025+) "
                    "before paper/live use. See reports/cot_pipeline_audit_20260514.md."
                )


def _derive_pm_trader_label(raw: dict) -> str | None:
    label = raw.get("trader_label")
    if label:
        return str(label)

    whale_data = (
        raw.get("whale_data") if isinstance(raw.get("whale_data"), dict) else {}
    )
    label = (
        raw.get("trader_name")
        or raw.get("username")
        or raw.get("user_name")
        or whale_data.get("username")
    )
    if label:
        return str(label)

    wallet = raw.get("trader_address") or whale_data.get("wallet")
    if not wallet:
        return None
    wallet = str(wallet)
    if len(wallet) <= 12:
        return wallet
    return f"{wallet[:8]}...{wallet[-4:]}"


def _derive_pm_type_label(raw: dict, dashboard_source_system: str) -> str:
    existing = raw.get("type_label")
    if existing:
        return str(existing)

    if dashboard_source_system == "pm_high_conviction" or raw.get("high_conviction"):
        return "🔮 PM High Conviction"

    source_hint = " ".join(
        [
            str(dashboard_source_system or ""),
            str(raw.get("source_system", "") or ""),
            str(raw.get("strategy", "") or ""),
        ]
    ).lower()
    if "kalshi" in source_hint:
        return "🔮 PM Kalshi"
    if "momentum" in source_hint:
        return "🔮 PM Momentum"

    origin = str(raw.get("signal_origin") or "").strip().lower()
    if origin == "vetted_wallet_copy":
        return "🔮 PM Vetted"
    if origin == "direct_position_inference":
        return "🔮 PM Whale"
    return "🔮 PM"


def _resolve_status(raw: dict, caller_status: str, pnl_val: float) -> str:
    """Preserve original WIN/LOSS status for closed picks instead of flattening to CLOSED.
    BUG FIX: _normalize_pick was destroying original status values, causing Agreement Matrix
    to show 0W/0L for all systems."""
    if caller_status != "CLOSED":
        return caller_status
    # Check original status from source data
    orig = (
        str(
            raw.get(
                "status",
                raw.get(
                    "outcome",
                    raw.get("exit_reason", raw.get("_resolved_exit_reason", "")),
                ),
            )
        )
        .upper()
        .strip()
    )
    if orig in (
        "WIN",
        "WON",
        "TP_HIT",
        "TP_1_5_HIT",
        "TP_2_0_HIT",
        "CLOSED_TP",
        "TAKE_PROFIT",
    ):
        return "WON"
    if orig in ("LOSS", "LOST", "SL_HIT", "CLOSED_SL", "STOP_LOSS"):
        return "LOST"
    if orig in ("TRAIL_SL", "TRAILING_STOP"):
        return "LOST"
    if orig in ("EXPIRED", "TIMEOUT", "TIME", "TIME_EXIT", "TIME_EXIT_AFTER_TP_1_5"):
        # Use PnL to determine win/loss for expired picks
        if pnl_val > 0:
            return "WON"
        elif pnl_val < 0:
            return "LOST"
        return "EXPIRED"
    # Recognize outcome_resolver exit reasons
    if orig in ("TP_HIT_RESOLVED", "EXIT_PRICE_RESOLVED", "PRICE_RESOLVED"):
        if pnl_val > 0:
            return "WON"
        elif pnl_val < 0:
            return "LOST"
        return "FLAT"
    if orig in ("SL_HIT_RESOLVED",):
        return "LOST"
    if orig in ("FLAT",):
        return "FLAT"
    # Fallback: use PnL to classify
    if pnl_val > 0:
        return "WON"
    elif pnl_val < 0:
        return "LOST"
    # 0-PnL picks that have no exit reason: mark as UNRESOLVED so dashboard
    # can distinguish them from genuine flat outcomes
    exit_reason = str(raw.get("exit_reason", "")).upper().strip()
    if not exit_reason and pnl_val == 0:
        return "UNRESOLVED"
    return "CLOSED"


def _coerce_closed_zero_pnl_from_outcome(
    raw: dict, caller_status: str, pnl_val: float
) -> float:
    """Use a tiny signed sentinel when a closed outcome is explicit but PnL is missing."""
    if caller_status != "CLOSED" or abs(pnl_val) > 1e-9:
        return pnl_val
    orig = (
        str(
            raw.get(
                "status",
                raw.get(
                    "outcome",
                    raw.get("exit_reason", raw.get("_resolved_exit_reason", "")),
                ),
            )
        )
        .upper()
        .strip()
    )
    if orig in {"LOSS", "LOST", "SL_HIT", "CLOSED_SL", "STOP_LOSS"}:
        return -0.01
    if orig in {"WIN", "WON", "TP_HIT", "CLOSED_TP", "TAKE_PROFIT"}:
        return 0.01
    return pnl_val


def _normalize_goldmine_closed_trade(raw: dict) -> dict:
    """Pre-normalize goldmine closed_trades.json schema to match _normalize_pick expectations.

    Goldmine uses: ticker, final_return_pct, entry_date, exit_date, algo_count.
    _normalize_pick expects: symbol, pnl_pct, timestamp, closed_at, strategy.
    Without this mapping, goldmine closed trades have no symbol/strategy -> fwdN=0 for all picks.
    """
    pick = dict(raw)
    # ticker -> symbol (pop to avoid duplicate)
    pick["symbol"] = pick.pop("ticker", pick.get("symbol", ""))
    # final_return_pct -> pnl_pct (sign already correct for most;
    # LOSS with frp=0 happens on "removed_from_consensus" exits)
    frp = float(pick.pop("final_return_pct", 0) or 0)
    pick["pnl_pct"] = frp
    # timestamps
    pick["closed_at"] = pick.get("exit_date")
    pick["timestamp"] = pick.get("entry_date")
    # Derive strategy from consensus_count (matching active handler) falling back to algo_count
    algo_n = int(pick.pop("consensus_count", None) or pick.pop("algo_count", 1) or 1)
    pick["strategy"] = "goldmine_%dx_consensus" % algo_n
    return pick


# ── Concept taxonomy (Phase 1, 2026-04-30) ────────────────────────────────
# Per the Cursor "Audit Concepts Integration" plan:
# C:\Users\zerou\.cursor\plans\audit_concepts_integration_2c10565d.plan.md
#
# Stamps `concept_family` + `concept_source` on every pick that flows
# through `_normalize_pick`. Concepts are derived from existing fields
# (strategy / source_system / category / pick_type) — no new data
# dependencies, no runtime API calls. Default `concept_family="standard"`
# preserves backward compatibility for picks that don't match a concept.
#
# Concept families currently recognized:
#   - long_term_value : UEPS picks (pick_type=long_term_value or
#                       source_system in {value_screener, ueps_*})
#   - skyrocket       : penny-stock skyrocket detector
#                       (alpha_engine/strategies/skyrocket_detector.py)
#   - penny_stock     : any pick with category=penny that isn't already
#                       tagged skyrocket
#   - meme_coin       : strategy/source contains "meme" (meme_scanner,
#                       meme-scanner-live, Meme Coin Scout, etc.)
#   - mercury2        : Mercury2 + revival_mercury2 + ai_challenge_mercury
#   - reverse_engineer: winner_reverse_engineer / strategy_reverse_engineer
#                       / gainer_predictor outputs
#   - tradingagents   : PR #544 emitter (decision-committee LLM consensus)
#   - standard        : everything else (default)
#
# Phase 2: concept taxonomy delegated to alpha_engine.concept_registry.
# Feature flags (TAXONOMY_EMISSION / CONCEPT_SCORING_SHADOW / CONCEPT_GATE_ENFORCE)
# are managed there and read from environment at import time.
try:
    from alpha_engine.concept_registry import (  # noqa: E402
        MERCURY2_SOURCES as _MERCURY2_SOURCES,
        REVERSE_ENGINEER_STRATEGIES as _REVERSE_ENGINEER_STRATEGIES,
        get_concept_family as _get_concept_family,
    )
    _CONCEPT_REGISTRY_AVAILABLE = True
except ImportError:
    # Fallback inline definitions — used only when alpha_engine is not on sys.path.
    _MERCURY2_SOURCES = frozenset({
        "mercury2", "mercury2_fast", "revival_mercury2", "ai_challenge_mercury",
    })
    _REVERSE_ENGINEER_STRATEGIES = frozenset({
        "winner_reverse_engineer", "strategy_reverse_engineer",
        "gainer_predictor", "gainer_predictor_score",
    })

    def _get_concept_family(pick: dict) -> str:  # type: ignore[misc]
        strategy = str(pick.get("strategy") or "").strip()
        source_system = str(pick.get("source_system") or "").strip()
        source_lc = source_system.lower()
        category = str(pick.get("category") or "").strip().lower()
        pick_type = str(pick.get("pick_type") or "").strip().lower()
        if pick_type == "long_term_value" or source_lc.startswith(("value_screener", "ueps_")):
            return "long_term_value"
        if strategy == "skyrocket_detector" or source_system == "skyrocket_detector":
            return "skyrocket"
        if strategy == "tradingagents_consensus" or source_system == "tradingagents":
            return "tradingagents"
        if category == "penny":
            return "penny_stock"
        if "meme" in strategy.lower() or "meme" in source_lc or category == "meme":
            return "meme_coin"
        if source_system in _MERCURY2_SOURCES:
            return "mercury2"
        if strategy in _REVERSE_ENGINEER_STRATEGIES or source_lc.startswith("winner_reverse"):
            return "reverse_engineer"
        return "standard"

    _CONCEPT_REGISTRY_AVAILABLE = False


def assign_concept_fields(pick: dict) -> dict:
    """Stamp concept_family + concept_source on a pick dict (mutates in-place).

    Delegates to :func:`alpha_engine.concept_registry.get_concept_family` when
    the registry module is available; falls back to inline logic otherwise.

    Returns the pick dict for chaining.
    """
    if not isinstance(pick, dict):
        return pick

    # Already stamped (e.g. by an upstream emitter that wants to override
    # the default derivation). Trust the upstream tag — UNLESS it is the
    # default "standard" placeholder, which an earlier _normalize_pick pass
    # may have stamped before pick_type/source was fully populated. Allow
    # the registry to upgrade "standard" to a real concept (loop3 2026-05-08:
    # was blocking 16 UEPS picks from getting concept_family=long_term_value).
    cur = pick.get("concept_family")
    if cur and str(cur).lower() != "standard":
        if "concept_source" not in pick:
            pick["concept_source"] = pick.get("strategy") or pick.get("source_system") or ""
        return pick

    source_for_attribution = (
        str(pick.get("strategy") or "").strip()
        or str(pick.get("source_system") or "").strip()
    )
    pick["concept_family"] = _get_concept_family(pick)
    pick["concept_source"] = source_for_attribution
    return pick


# ---------------------------------------------------------------------------
# B17 — After-cost field stamping (2026-05-02)
# ---------------------------------------------------------------------------
# Reads the latest forward_edge_audit_*.json produced by tools/forward_edge_audit.py
# (B16) and stamps three new fields on every pick:
#   after_cost_net_per_trade  — mean after-cost PnL % per trade for the strategy
#   wilson_lb_wr              — Wilson 95% lower bound on the strategy win rate
#   is_ac_survivor            — bool: survives both after-cost > 0 AND wilson_lb >= 50%
#
# Fields are None when the strategy is absent from the index or the artifact is
# >25 h stale (one dashboard-rebuild cycle). None = unknown (not the same as False
# = non-survivor). Stamping never raises or blocks normalization.
#
# Shadow HC gate passes_hc_after_cost() in tools/hc_gates_python.py uses these
# fields behind HC_AFTER_COST_GATE_ENABLED=1 env flag (default OFF).
# ---------------------------------------------------------------------------
_AC_STRATEGY_INDEX_CACHE: dict | None = None   # None = not loaded; {} = loaded, empty
_AC_STRATEGY_INDEX_LOADED_AT: float = 0.0      # epoch time of last successful load
_AC_STRATEGY_INDEX_MAX_AGE_S = 25 * 3600       # 25 hours


def _load_ac_strategy_index() -> dict:
    """Load (or return cached) the B16 forward-edge-audit strategy index.

    Index keys: (strategy_lower, asset_class_upper) → row dict.
    Fallback key: strategy_lower → first matching row (for picks without asset_class).
    Returns an empty dict when no artifact is found or the latest is too stale.
    """
    global _AC_STRATEGY_INDEX_CACHE, _AC_STRATEGY_INDEX_LOADED_AT
    import time as _time
    now = _time.time()
    if _AC_STRATEGY_INDEX_CACHE is not None and (now - _AC_STRATEGY_INDEX_LOADED_AT) < _AC_STRATEGY_INDEX_MAX_AGE_S:
        return _AC_STRATEGY_INDEX_CACHE

    import glob as _glob
    import json as _json
    import datetime as _datetime

    artifacts = sorted(_glob.glob(
        os.path.join(os.path.dirname(__file__), "..", "reports", "forward_edge_audit_*.json")
    ))
    if not artifacts:
        _AC_STRATEGY_INDEX_CACHE = {}
        _AC_STRATEGY_INDEX_LOADED_AT = now
        return {}

    latest = artifacts[-1]
    try:
        with open(latest, encoding="utf-8") as fh:
            data = _json.load(fh)
    except Exception:
        _AC_STRATEGY_INDEX_CACHE = {}
        _AC_STRATEGY_INDEX_LOADED_AT = now
        return {}

    # Staleness check against the artifact's own generated_at timestamp
    gen_at_str = data.get("generated_at", "")
    if gen_at_str:
        try:
            gen_dt = _datetime.datetime.fromisoformat(gen_at_str.replace("Z", "+00:00"))
            age_s = (
                _datetime.datetime.now(_datetime.timezone.utc) - gen_dt
            ).total_seconds()
            if age_s > _AC_STRATEGY_INDEX_MAX_AGE_S:
                _AC_STRATEGY_INDEX_CACHE = {}
                _AC_STRATEGY_INDEX_LOADED_AT = now
                return {}
        except Exception:
            pass  # malformed timestamp — proceed with file-mtime check below

    index: dict = {}
    for row in data.get("strategies", []):
        strat = str(row.get("strategy") or "").strip().lower()
        ac = str(row.get("asset_class") or "").strip().upper()
        if not strat:
            continue
        # Compound key: exact (strategy, asset_class) match
        index[(strat, ac)] = row
        # Fallback key: strategy only — keep first seen (highest-n entry usually first)
        if strat not in index:
            index[strat] = row

    _AC_STRATEGY_INDEX_CACHE = index
    _AC_STRATEGY_INDEX_LOADED_AT = now
    return index


def stamp_after_cost_fields(pick: dict, index: dict) -> None:
    """Stamp after_cost_net_per_trade / wilson_lb_wr / is_ac_survivor (mutates in-place).

    Looks up pick's strategy in the B16 forward-edge-audit index.
    All three fields are set to None when the strategy is not found.
    """
    strat = str(pick.get("strategy") or pick.get("source_system") or "").strip().lower()
    ac = str(pick.get("asset_class") or "").strip().upper()

    row = index.get((strat, ac)) if (strat and ac) else None
    if row is None and strat:
        row = index.get(strat)

    if row is not None:
        pick["after_cost_net_per_trade"] = row.get("after_cost_mean_pnl_pct")
        pick["wilson_lb_wr"] = row.get("wilson_lb_wr_pct")
        pick["is_ac_survivor"] = bool(row.get("both_survive"))
    else:
        pick["after_cost_net_per_trade"] = None
        pick["wilson_lb_wr"] = None
        pick["is_ac_survivor"] = None


def _classify_contract_safe(symbol) -> str:
    """Fail-soft wrapper around alpha_engine.contract_type.classify_contract.

    Returns the finer contract_type label (commodity_future / index_future /
    rates_future / currency_future / crypto / forex / equity / unknown).
    Any import/runtime error degrades to "unknown" — must never break the
    dashboard build.
    """
    try:
        from alpha_engine.contract_type import classify_contract
        return classify_contract(str(symbol or ""))
    except Exception:  # noqa: BLE001
        return "unknown"


def _normalize_pick(raw, source_system: str, status: str = "OPEN") -> dict:
    """Normalize a pick from any source into a common schema."""
    if not isinstance(raw, dict):
        return {"symbol": "", "direction": "", "skip": True}  # malformed entry
    symbol = raw.get("symbol", raw.get("pair", raw.get("ticker", "")))
    direction = str(
        raw.get(
            "direction",
            raw.get("signal_type", raw.get("signal", raw.get("action", ""))),
        )
    ).upper()
    if "BUY" in direction or "LONG" in direction or direction == "OVER":
        direction = "LONG"
    elif "SELL" in direction or "SHORT" in direction or direction == "UNDER":
        direction = "SHORT"
    elif not direction or direction in ("", "NONE", "UNKNOWN"):
        # Infer from TP/SL vs entry: if TP > entry, it's LONG
        _e = _float(raw.get("entry_price", raw.get("entryPrice", raw.get("entry", 0))))
        _t = _float(
            raw.get(
                "take_profit",
                raw.get(
                    "target_price",
                    raw.get("targetPrice", raw.get("tp", raw.get("tp1_price", 0))),
                ),
            )
        )
        if _e and _t:
            direction = "LONG" if _t > _e else "SHORT"
        else:
            direction = "LONG"  # default assumption

    entry = raw.get(
        "entry_price", raw.get("entryPrice", raw.get("entry", raw.get("price", 0)))
    )
    tp_candidates = [
        "take_profit", "target_price", "targetPrice", "tp", "tp_price",
        "tp_price_1_5", "tp_pct", "suggested_tp_pct"
    ]
    tp = 0
    for k in tp_candidates:
        if raw.get(k) is not None:
            tp = raw.get(k)
            break

    sl_candidates = [
        "stop_loss", "stop_price", "stopPrice", "sl", "sl_price",
        "sl_pct", "suggested_sl_pct"
    ]
    sl = 0
    for k in sl_candidates:
        if raw.get(k) is not None:
            sl = raw.get(k)
            break
    conf = _extract_confidence(raw)
    # Resolve the strategy label across the producer zoo. mega_mutation engine
    # writes `mutation_name` (e.g. "ema_momentum_m006") rather than `strategy`,
    # so picks reached the dashboard unlabeled and were filtered out.
    # See reports/EDGE_DELIVERY_INVESTIGATION_2026_04_29.md (Fix C).
    strategy = (
        raw.get("strategy")
        or raw.get("strategy_name")
        or raw.get("algorithm")
        or raw.get("mutation_name")
        or ""
    )
    # Goldmine equity: align strategy with active consensus rows so closed ledger
    # forward stats join as goldmine_stocks::goldmine_Nx_consensus.
    if (
        not strategy
        and str(source_system).lower() == "goldmine_stocks"
    ):
        _gm_n = raw.get("consensus_count")
        if _gm_n is None:
            _gm_n = raw.get("algo_count")
        if _gm_n is not None:
            try:
                _gm_i = int(_gm_n)
                if _gm_i > 0:
                    strategy = "goldmine_%dx_consensus" % _gm_i
            except (TypeError, ValueError):
                pass
    # Consensus/aggregated picks often have strategy=null — build from available fields
    if not strategy:
        consensus_tier = raw.get("consensus_tier", "")
        src_systems = raw.get("source_systems", [])
        src_strategies = raw.get("source_strategies", {})
        if src_strategies and isinstance(src_strategies, dict):
            # Use the first strategy from the highest-priority system
            for prio_sys in [
                "battleground",
                "alpha_engine",
                "kimi_riseoftheclaw",
                "kimi",
            ]:
                if prio_sys in src_strategies:
                    strategy = src_strategies[prio_sys]
                    break
            if not strategy:
                strategy = next(iter(src_strategies.values()), "")
        if not strategy and src_systems:
            strategy = (
                f"{consensus_tier.lower()} consensus ({', '.join(src_systems[:3])})"
            )
        elif not strategy and consensus_tier:
            strategy = f"{consensus_tier.lower()} consensus"
    if not strategy:
        strategy = raw.get("source") or raw.get("source_system") or source_system
    asset_class = _derive_asset_class(
        symbol, raw=raw, source_system=source_system, strategy=strategy
    )
    # CRYPTO TAGGING FIX (2026-04-05): Explicit source-based crypto assignment
    # Fixes ~1,142+ untagged crypto picks from CEX integrations (okx_picks, bybit_picks, etc)
    # These copy trader intel sources are 99%+ crypto instruments
    if asset_class == "UNKNOWN" and source_system in (
        "copy_trader_intel",
        "copy_trader_highscore",
        "copy_trader_clones",
        "copy_trader_variations",
        "copy_trader_consensus",
    ):
        # If symbol doesn't match explicit non-crypto patterns, assume CRYPTO
        sym_upper = str(symbol or "").upper()
        is_futures_or_forex = any(
            sym_upper.endswith(sfx) for sfx in ["=F", "=X", ".TO", ".L", ".AX"]
        )
        if not is_futures_or_forex:
            asset_class = "CRYPTO"
    # 2026-05-20 SUBAGENT FIX: UNKNOWN-class 40 picks rooted in emitters that omit
    # asset_class but DO write category (experimental_strategies / statistical_strategies /
    # community_strategies). Fallback: derive from raw.get("category") if asset_class
    # is still UNKNOWN after the explicit source-based assignment above.
    if asset_class == "UNKNOWN":
        _cat = (raw.get("category") or raw.get("Category") or "").strip().lower()
        _cat_map = {
            "crypto": "CRYPTO", "cryptocurrency": "CRYPTO", "altcoin": "CRYPTO",
            "equity": "EQUITY", "stock": "EQUITY", "stocks": "EQUITY",
            "etf": "ETF", "etfs": "ETF",
            "forex": "FOREX", "fx": "FOREX", "currency": "FOREX",
            "commodity": "COMMODITY", "commodities": "COMMODITY",
            "futures": "FUTURES", "future": "FUTURES",
            "bond": "BOND", "bonds": "BOND", "fixed_income": "BOND",
            "meme": "MEME", "meme_coin": "MEME", "memecoin": "MEME",
        }
        if _cat in _cat_map:
            asset_class = _cat_map[_cat]
    dashboard_source_system = _logical_dashboard_source_system(
        source_system, raw, asset_class
    )
    is_pm_pick = _is_prediction_market_pick(
        source_system, dashboard_source_system, raw, strategy
    )
    trader_label = (
        _derive_pm_trader_label(raw) if is_pm_pick else raw.get("trader_label")
    )
    type_label = (
        _derive_pm_type_label(raw, dashboard_source_system)
        if is_pm_pick
        else raw.get("type_label")
    )
    pm_source_systems = (
        raw.get("pm_source_systems", []) or raw.get("source_systems", []) or []
    )
    if isinstance(pm_source_systems, str):
        pm_source_systems = [
            s.strip() for s in pm_source_systems.split(",") if s.strip()
        ]
    source_count = raw.get("source_count")
    if source_count is None:
        consensus_data = raw.get("consensus_data", {}) or {}
        source_count = (
            consensus_data.get("source_category_count")
            or consensus_data.get("num_sources")
            or raw.get("consensus_count")
        )
    # Pass source_strategies through for frontend display
    source_strategies = raw.get("source_strategies", {})
    raw_status_u = str(raw.get("status", "") or "").upper()
    pipeline_status_u = str(status or "").upper()
    prefer_book_pnl = pipeline_status_u == "CLOSED" or raw_status_u in (
        "CLOSED",
        "WON",
        "LOST",
        "EXPIRED",
        "RESOLVED",
    )
    if prefer_book_pnl:
        pnl = raw.get(
            "net_pnl_pct",
            raw.get(
                "realized_pnl_pct",
                raw.get(
                    "final_return_pct",
                    raw.get(
                        "pnl_pct",
                        raw.get(
                            "actual_pnl_pct",
                            raw.get(
                                "plPercent",
                                raw.get(
                                    "unrealized_pnl_pct",
                                    raw.get(
                                        "_resolved_pnl_pct",
                                        raw.get("pnl_dollar", 0),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
    else:
        pnl = raw.get(
            "pnl_pct",
            raw.get(
                "actual_pnl_pct",
                raw.get(
                    "plPercent",
                    raw.get(
                        "unrealized_pnl_pct",
                        # 2026-04-14: goldmine_stocks closed_trades.json reports
                        # final_return_pct (e.g. -1.66, +11.88) — add it to the
                        # fallback chain so goldmine closes get real PnL instead
                        # of defaulting to 0 (which made every goldmine WIN look
                        # like a flat trade in the strategy leaderboard).
                        raw.get(
                            "final_return_pct",
                            raw.get("_resolved_pnl_pct", raw.get("pnl_dollar", 0)),
                        ),
                    ),
                ),
            ),
        )
    exit_reason = raw.get(
        "exit_reason",
        raw.get(
            "close_reason",
            raw.get(
                "resolved_reason",
                raw.get("outcome", raw.get("_resolved_exit_reason", "")),
            ),
        ),
    )

    pnl_val = _float(pnl)
    entry_val = _float(entry)
    exit_price = _float(
        raw.get(
            "exit_price",
            raw.get(
                "close_price",
                raw.get(
                    "current_price",
                    raw.get("currentPrice", raw.get("_resolved_price", 0)),
                ),
            ),
        )
    )
    if entry_val > 0 and exit_price <= 0 and pnl_val != 0 and status != "OPEN":
        if direction == "SHORT":
            exit_price = round(entry_val * (1 - pnl_val / 100), 8)
        else:
            exit_price = round(entry_val * (1 + pnl_val / 100), 8)

    # PnL normalization: prefer calculating from prices (no ambiguity),
    # fall back to reported value with careful fraction detection.
    if entry_val > 0 and exit_price > 0:
        # Always trust price-derived PnL over reported values
        if direction == "SHORT":
            pnl_val = round((entry_val - exit_price) / entry_val * 100, 4)
        else:
            pnl_val = round((exit_price - entry_val) / entry_val * 100, 4)
    elif pnl_val != 0 and -1.0 < pnl_val < 1.0:
        # No prices available — must decide if reported PnL is a fraction or percentage.
        # Only convert if it looks unambiguously like a fraction (e.g. 0.05 = 5%).
        # Values like -0.5 or +0.8 are ambiguous: could be -0.5% or -50%.
        # Use a tight threshold: only auto-convert values whose magnitude < 0.10
        # (i.e., < 10% when converted). Larger values stay as-is (treated as percentages).
        if abs(pnl_val) < 0.10:
            pnl_val = round(pnl_val * 100, 4)

    # Asset-aware cap at ingest: crypto may exceed ±100% legitimately; FX/equity
    # rows beyond ±200% are almost always pip/price corruption (see pnl_ingest_sanity).
    _pnl_pre_clamp = float(pnl_val)
    pnl_val, pnl_was_clamped = clamp_pnl_pct_for_pick(
        _pnl_pre_clamp, str(asset_class or "UNKNOWN").upper()
    )

    pnl_val = _coerce_closed_zero_pnl_from_outcome(raw, status, pnl_val)

    tp_val = _float(tp)
    sl_val = _float(sl)
    conf_val = conf  # Already a float from _extract_confidence()

    # Auto-compute missing TP/SL from ATR when available
    # A pick without exit levels is untradeable — estimate from ATR or % fallback
    if entry_val > 0:
        atr_val = _float(raw.get("atr_at_entry", raw.get("atr", 0)))
        if not tp_val and not sl_val:
            # No TP and no SL — use ATR if available, else asset-class defaults
            if atr_val > 0:
                if direction == "LONG":
                    tp_val = round(entry_val + 2.5 * atr_val, 8)
                    sl_val = round(entry_val - 1.5 * atr_val, 8)
                else:
                    tp_val = round(entry_val - 2.5 * atr_val, 8)
                    sl_val = round(entry_val + 1.5 * atr_val, 8)
            else:
                # Fallback: asset-class-appropriate TP/SL from policy caps
                _ac_defaults = {
                    "EQUITY": (0.08, 0.05),   # 8% TP, 5% SL
                    "ETF":    (0.05, 0.03),   # 5% TP, 3% SL
                    "FOREX":  (0.015, 0.01),  # 1.5% TP, 1% SL
                    "COMMODITY": (0.03, 0.02),# 3% TP, 2% SL
                    "FUTURES": (0.03, 0.02),  # 3% TP, 2% SL
                }
                _fb_tp, _fb_sl = _ac_defaults.get(
                    str(asset_class or "").upper(), (0.025, 0.015)
                )
                if direction == "LONG":
                    tp_val = round(entry_val * (1 + _fb_tp), 8)
                    sl_val = round(entry_val * (1 - _fb_sl), 8)
                else:
                    tp_val = round(entry_val * (1 - _fb_tp), 8)
                    sl_val = round(entry_val * (1 + _fb_sl), 8)
        elif not tp_val and sl_val:
            # Has SL but no TP — compute TP for 1.67:1 R:R
            sl_dist = abs(entry_val - sl_val)
            if direction == "LONG":
                tp_val = round(entry_val + sl_dist * 1.67, 8)
            else:
                tp_val = round(entry_val - sl_dist * 1.67, 8)
        elif tp_val and not sl_val:
            # Has TP but no SL — compute SL for 1.67:1 R:R
            tp_dist = abs(tp_val - entry_val)
            if direction == "LONG":
                sl_val = round(entry_val - tp_dist / 1.67, 8)
            else:
                sl_val = round(entry_val + tp_dist / 1.67, 8)

    # Preserve a dedicated entry timestamp when the source exposes one.
    # Closed picks often reuse `timestamp` for resolution/update recency, so export
    # code should not have to guess whether it represents the original entry.
    _entry_ts_keys = (
        "entry_date",
        "entryDate",
        "entry_time",
        "created_at",
        "generated_at",
        "signal_time",
        "signal_time_est",
        "opened_at",
        "timestamp_est",
        "scraped_at",
        "scan_time",
    )
    entry_ts = ""
    for _k in _entry_ts_keys:
        _v = raw.get(_k)
        if _v:
            entry_ts = str(_v)
            break

    # Timestamp extraction (each system uses different field names)
    # Preserve the existing generic timestamp semantics because downstream recency
    # sorting relies on it for recently closed picks.
    _ts_keys = (
        "timestamp",
        "entry_date",
        "entryDate",
        "entry_time",
        "created_at",
        "generated_at",
        "signal_time",
        "signal_time_est",
        "opened_at",
        "timestamp_est",
        "scraped_at",
        "scan_time",
        "last_checked",
        "last_checked_est",
        "resolved_at",
        "closed_at",
        "exit_time",
    )
    ts = ""
    for _k in _ts_keys:
        _v = raw.get(_k)
        if _v:
            ts = str(_v)
            break

    # Age in hours (from timestamp to now)
    age_hours = None
    try:
        if ts:
            # Strip timezone abbreviations that fromisoformat can't handle
            _ts_clean = ts.strip()
            for _tz_suffix in (
                " EST",
                " EDT",
                " UTC",
                " GMT",
                " PST",
                " PDT",
                " CST",
                " CDT",
            ):
                if _ts_clean.endswith(_tz_suffix):
                    _ts_clean = _ts_clean[: -len(_tz_suffix)]
                    # Append proper UTC offset for known abbreviations
                    _tz_offsets = {
                        "EST": "-05:00",
                        "EDT": "-04:00",
                        "UTC": "+00:00",
                        "GMT": "+00:00",
                        "PST": "-08:00",
                        "PDT": "-07:00",
                        "CST": "-06:00",
                        "CDT": "-05:00",
                    }
                    _ts_clean += _tz_offsets.get(_tz_suffix.strip(), "+00:00")
                    break
            pick_dt = datetime.fromisoformat(_ts_clean.replace("Z", "+00:00"))
            if pick_dt.tzinfo is None:
                pick_dt = pick_dt.replace(tzinfo=timezone.utc)
            age_hours = round(
                (datetime.now(timezone.utc) - pick_dt).total_seconds() / 3600, 1
            )
    except Exception:
        pass

    # TP remaining % and SL remaining % (how far current price is from TP/SL)
    tp_remaining_pct = None
    sl_remaining_pct = None
    current = (
        exit_price if exit_price > 0 else entry_val
    )  # best proxy for current price
    if entry_val > 0 and tp_val > 0 and sl_val > 0 and current > 0:
        try:
            if direction == "LONG":
                tp_range = tp_val - entry_val
                sl_range = entry_val - sl_val
                if tp_range > 0:
                    tp_remaining_pct = round(
                        max(0, (tp_val - current) / tp_range * 100), 1
                    )
                if sl_range > 0:
                    sl_remaining_pct = round(
                        max(0, (current - sl_val) / sl_range * 100), 1
                    )
            else:  # SHORT
                tp_range = entry_val - tp_val
                sl_range = sl_val - entry_val
                if tp_range > 0:
                    tp_remaining_pct = round(
                        max(0, (current - tp_val) / tp_range * 100), 1
                    )
                if sl_range > 0:
                    sl_remaining_pct = round(
                        max(0, (sl_val - current) / sl_range * 100), 1
                    )
        except Exception:
            pass

    resolved_status = _resolve_status(raw, status, pnl_val)
    if not exit_reason and resolved_status in {
        "WON",
        "LOST",
        "FLAT",
        "EXPIRED",
        "TP_HIT",
        "SL_HIT",
        "UNRESOLVED",
    }:
        exit_reason = resolved_status

    pick_id = (
        raw.get(
            "id", raw.get("pick_id", raw.get("signal_id", raw.get("prediction_id", "")))
        )
        or ""
    )
    if not pick_id:
        safe_symbol = str(symbol or "").strip().upper() or "UNKNOWN"
        safe_direction = direction or "LONG"
        safe_strategy = (
            str(strategy or source_system or "pick").strip().lower().replace(" ", "_")
        )
        safe_ts = (
            str(ts or raw.get("generated_at") or raw.get("created_at") or "")
            .replace(":", "")
            .replace("-", "")
        )
        pick_id = (
            f"{dashboard_source_system}_{safe_symbol}_{safe_direction}_{safe_strategy}"
        )
        if safe_ts:
            pick_id += f"_{safe_ts}"

    source_score_meta = _extract_normalized_source_scores(raw, source_system)

    _pick = {
        "id": pick_id,
        "symbol": str(symbol),
        "direction": direction,
        "entry_price": entry_val,
        "current_price": _float(raw.get("current_price", raw.get("currentPrice", 0)))
        or None,
        "take_profit": tp_val,
        "stop_loss": sl_val,
        "confidence": conf_val,
        "score": source_score_meta["score"],
        "elite_score": source_score_meta["elite_score"],
        "ml_score": source_score_meta["ml_score"],
        "ml_composite_score": source_score_meta["ml_composite_score"],
        "method_a_score": source_score_meta["method_a_score"],
        "precursor_score": source_score_meta["precursor_score"],
        "confluence_score": source_score_meta["confluence_score"],
        "safety_score": source_score_meta["safety_score"],
        "elite_grade": source_score_meta["elite_grade"],
        "grade": source_score_meta["grade"],
        "strategy": str(strategy),
        "source": str(
            raw.get("source")
            or raw.get("source_system")
            or dashboard_source_system
            or source_system
            or "unknown"
        ),
        "system": str(
            raw.get("system")
            or raw.get("source_system")
            or dashboard_source_system
            or source_system
            or "unknown"
        ),
        "source_system": dashboard_source_system,
        "asset_class": _coerce_asset_class({
            "asset_class": asset_class,
            "symbol": symbol,
            "source_system": source_system,
            "strategy": strategy,
            "category": raw.get("category"),
        }),
        # Additive contract-type tag (2026-05-16). Distinguishes
        # commodity_future / index_future / rates_future / currency_future so
        # the FUTURES tile can show honest n — most `=F` symbols route to the
        # COMMODITY asset_class, starving FUTURES. Does NOT change asset_class
        # routing; purely a finer label for downstream tiles/filters.
        "contract_type": _classify_contract_safe(symbol),
        "source_subsystem": raw.get("source_system")
        if dashboard_source_system != source_system
        else raw.get("source_subsystem"),
        "status": resolved_status,
        "pnl_pct": pnl_val,
        "exit_reason": str(exit_reason) if exit_reason else "",
        "timestamp": ts,
        "signal_time": entry_ts or ts,
        "entry_time": entry_ts,
        # 2026-05-20: resolved_at fallback chain — fixes quan_engine_scalp + similar emitters
        # that write only closed_at/exit_time. Harness reads resolved_at; without this fallback,
        # 5,293 quan_engine_scalp closed picks invisible to edge_stability_harness. (peer freebuff
        # discovery, this session.)
        "resolved_at": raw.get("resolved_at")
        or raw.get("_resolved_at")
        or raw.get("resolvedAt")
        or raw.get("resolved_at_est")
        or raw.get("closed_at")
        or raw.get("closedAt")
        or raw.get("closed_at_est")
        or raw.get("exit_time")
        or raw.get("exitTime")
        or raw.get("exit_time_est")
        or raw.get("exit_timestamp")
        or raw.get("exitDate")
        or raw.get("exit_date")
        or raw.get("close_time")
        or raw.get("closeTime")
        or raw.get("closeDate")
        or "",
        "closed_at": raw.get("resolved_at")
        or raw.get("_resolved_at")
        or raw.get("resolvedAt")
        or raw.get("resolved_at_est")
        or raw.get("closed_at")
        or raw.get("closedAt")
        or raw.get("closed_at_est")
        or raw.get("exit_time")
        or raw.get("exitTime")
        or raw.get("exit_time_est")
        or raw.get("exit_timestamp")
        or raw.get("exitDate")
        or raw.get("exit_date")
        or raw.get("close_time")
        or raw.get("closeTime")
        or raw.get("closeDate")
        or "",
        "age_hours": age_hours,
        "tp_remaining_pct": tp_remaining_pct,
        "sl_remaining_pct": sl_remaining_pct,
        "rr_ratio": min(round(abs(tp_val - entry_val) / abs(entry_val - sl_val), 2), 10.0)
        if entry_val and tp_val and sl_val and abs(entry_val - sl_val) > 0
        else None,
        "trade_timeframe": classify_timeframe(raw, source_system),
        "beta_score": raw.get("beta_score"),
        "beta_breakdown": raw.get("beta_breakdown"),
        "beta_qualified": raw.get("beta_qualified", False),
        "research_cohort": raw.get("research_cohort"),
        "agreeing_systems": raw.get("agreeing_systems", []),
        "source_strategies": source_strategies
        if isinstance(source_strategies, dict) and source_strategies
        else {},
        # Entry reason & confluence data — needed for Excel export audit trail
        "reason": str(
            raw.get(
                "reason",
                raw.get(
                    "signal_reason",
                    raw.get(
                        "entry_reason",
                        raw.get("notes", (raw.get("extra") or {}).get("reason", "")),
                    ),
                ),
            )
        )
        or "",
        "notes": str(raw.get("notes", "")) or "",
        "confluence_strategies": raw.get("confluence_strategies", []) or [],
        "source_systems": raw.get("source_systems", []) or [],
        "pm_source_systems": pm_source_systems,
        "source_count": source_count,
        "agreement_count": raw.get("agreement_count", 0) or 0,
        # Copy trader metadata — preserve these so downstream scoring and UI
        # can reason about tracked history and true multi-trader agreement.
        "trader_label": trader_label,
        "type_label": type_label,
        "consensus_count": raw.get("consensus_count"),
        "consensus_traders": raw.get("consensus_traders", []) or [],
        "agreeing_traders": raw.get("agreeing_traders", []) or [],
        "agreeing_sources": raw.get("agreeing_sources", []) or [],
        "history_trades": raw.get("history_trades"),
        "history_wr_bayes": raw.get("history_wr_bayes"),
        "history_wr": raw.get("history_wr"),
        "history_avg_pnl": raw.get("history_avg_pnl"),
        "history_basis": raw.get("history_basis"),
        "history_bonus": raw.get("history_bonus"),
        "profile_crypto_wr_bayes": raw.get("profile_crypto_wr_bayes"),
        "profile_crypto_wr": raw.get("profile_crypto_wr"),
        # Forward validation data
        "forward_wr": raw.get("forward_wr")
        if raw.get("forward_wr") is not None
        else None,
        "forward_trades": raw.get("forward_trades")
        if raw.get("forward_trades") is not None
        else None,
        "forward_validated": raw.get("forward_validated", False),
        "forward_status": str(raw.get("forward_status", "")) or "",
        "exit_price": exit_price,
        "_metaWinProb": raw.get("_metaWinProb"),
        "_metaGrade": raw.get("_metaGrade"),
        "trust_score": raw.get("trust_score"),
        "trust_label": source_score_meta["trust_label"],
        "trust_tier": source_score_meta["trust_tier"],
        "regime": raw.get("regime") or raw.get("sentinel_regime"),
        "has_conflict": raw.get("has_conflict", False),
        "_source_score_breakdown": source_score_meta["_source_score_breakdown"],
        # Leverage safety gate
        "max_safe_leverage": raw.get("max_safe_leverage", 2),
        "leverage_factors": raw.get("leverage_factors", {}),
        "leverage_warning": raw.get("leverage_warning", ""),
        # Paper-only flag: set True for frozen/research portfolios that should not
        # count toward forward-tested performance metrics (WR, trade count, expectancy).
        "paper_trade": dashboard_source_system in _PAPER_ONLY_SYSTEMS,
        # ── Winner-predictor columns (IC-validated): regime, RSI, volume, HTF, strong ──
        # These fields come from source scanners (alpha_engine, KIMI, etc.) and must be
        # passed through so the dashboard template can render Trust/Regime/Track/HTF/Strong/RSI/VOL columns.
        "regime_at_entry": raw.get(
            "regime_at_entry",
            raw.get(
                "regime_trend_direction",
                raw.get("hmm_regime", raw.get("market_regime", "")),
            ),
        ),
        "rsi_at_entry": _float(
            raw.get("rsi_at_entry", raw.get("rsi", raw.get("rsi_14", 0)))
        )
        or None,
        "volume_ratio": _float(
            raw.get(
                "volume_ratio", raw.get("vol_ratio", raw.get("volume_acceleration", 0))
            )
        )
        or None,
        "volume": _float(raw.get("volume")) or None,
        "htf_bias": raw.get(
            "htf_bias",
            raw.get(
                "htf_alignment",
                raw.get("htf_aligned", (raw.get("extra") or {}).get("htf_bias", "")),
            ),
        ),
        "htf_confirmation": raw.get(
            "htf_confirmation",
            raw.get(
                "htf_bias",
                raw.get("htf_alignment", (raw.get("extra") or {}).get("htf_bias", "")),
            ),
        ),
        "ml_features_at_entry": raw.get("ml_features_at_entry", ""),
    }
    if pnl_was_clamped:
        _pick["pnl_pct_ingest_clamped"] = True
        _pick["pnl_pct_pre_clamp"] = round(_pnl_pre_clamp, 4)
    # VA gate Option A (antigrav-dash-integrity 2026-04-04): stamp research_cohort so
    # UI can filter verified-alpha picks without re-running the gate at render time.
    if _pick.get("research_cohort") is None and _is_verified_alpha_pick(_pick):
        _pick["research_cohort"] = "verified_alpha"
    _enrich_va_cohort_fields(_pick)
    # Concept taxonomy (Phase 1, 2026-04-30): stamp concept_family +
    # concept_source on every pick so /audit can filter / aggregate by
    # concept (penny / meme / skyrocket / mercury2 / long_term_value /
    # reverse_engineer). Pure derivation from existing fields — no new
    # data dependencies.
    assign_concept_fields(_pick)

    # B17 (2026-05-02): stamp after-cost fields from B16 forward-edge-audit artifact.
    # Default-ON (artifact lookup only — never breaks normalization if file absent).
    _ac_idx = _load_ac_strategy_index()
    if _ac_idx:
        stamp_after_cost_fields(_pick, _ac_idx)
    else:
        _pick.setdefault("after_cost_net_per_trade", None)
        _pick.setdefault("wilson_lb_wr", None)
        _pick.setdefault("is_ac_survivor", None)

    # Net-of-cost PnL overlay (PR-A, 2026-05-02). Per the hedge-fund-uplift
    # roadmap (reports/HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md) and the
    # PR #626 backtest empirical finding ("transaction-cost overlay flips
    # every class except CRYPTO from gross-positive to net-negative at
    # literature-prior slippage"), this stamps `net_of_cost_pnl_pct`
    # alongside the existing `pnl_pct` so the audit dashboard can surface
    # cost-adjusted PF without breaking any consumer of `pnl_pct`.
    #
    # Default-OFF behind HF_NET_PF_ENABLED env flag per CLAUDE.md 14-day
    # shadow rule. When OFF: no behavior change. When ON: net_of_cost_pnl_pct
    # is added to every normalized pick; downstream PF aggregators can
    # opt in by reading the new field.
    if os.environ.get("HF_NET_PF_ENABLED", "0") == "1":
        try:
            from audit_trail.transaction_cost_model import apply_costs_to_pick as _apply_costs
            _pick = _apply_costs(_pick)
        except Exception:
            # Cost overlay must never break pick normalization. Swallow
            # silently and leave the pick unchanged. The flag-OFF default
            # means this code path is dormant in production unless flipped.
            pass

    # M-014: confidence schema 0-1 normalizer — the single chokepoint that
    # every source flows through. ML model outputs may produce values outside
    # this range (raw logit probabilities, softmax scores > 1.0, negative
    # "confidence" from some scoring APIs). Issue #1241: several emitters
    # (claude_gainer short-term, NOW, copy-trader) store confidence on a 0-100
    # PERCENT scale, leaking percent-as-integer values 15-78 into closed_picks
    # ledgers. A flat min(1.0, ...) here would silently collapse 70 -> 1.0 and
    # destroy the signal, so percent-looking values (1.0 < c <= 100) are
    # rescaled /100; anything still out of range is clamped to [0.0, 1.0].
    if _pick.get("confidence") is not None:
        try:
            _c = float(_pick.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            _c = 0.0
        if 1.0 < _c <= 100.0:
            _c = _c / 100.0  # percent-as-integer leak → fraction
        _pick["confidence"] = max(0.0, min(1.0, _c))

    return _pick


def _extract_picks(data):
    """Extract pick list from various JSON formats (array or object)."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # UEPS format (B28 2026-05-01): ueps_picks.json splits picks into
        # long_picks / swing_picks / short_picks sub-lists.  Concatenate all
        # three so UEPS picks reach the main active-picks table without relying
        # on the racy sync_to_active_picks() → active_picks.json path.
        if "long_picks" in data:
            parent_ts = (
                data.get("generated_at")
                or data.get("scan_time")
                or data.get("timestamp")
                or data.get("created_at")
            )
            combined: list = []
            for sub_key in ("long_picks", "swing_picks", "short_picks"):
                sub = data.get(sub_key)
                if isinstance(sub, list):
                    combined.extend(sub)
            if parent_ts:
                for p in combined:
                    if not any(
                        p.get(_k)
                        for _k in (
                            "timestamp",
                            "generated_at",
                            "entry_date",
                            "entryDate",
                            "detected_at",
                            "created_at",
                        )
                    ):
                        p["generated_at"] = parent_ts
            return combined
        # B7 prereq (2026-05-02): cot_signals.json written by alpha_engine/cot_positioning.py
        # uses scanner="cot_positioning" as the discriminator.  Legacy __main__ output used
        # {pair, signal, confidence, percentile} without symbol/direction/strategy/asset_class;
        # the __main__ block was fixed in this PR to write the full schema, but the adapter
        # handles both old and new format as defence-in-depth.
        # Content-freshness guard: CFTC COT data is weekly; reject if generated_at > 14d stale.
        if data.get("scanner") == "cot_positioning":
            from datetime import timedelta as _td
            parent_ts = data.get("generated_at")
            if parent_ts:
                try:
                    import datetime as _dt
                    _cot_age = _dt.datetime.now(_dt.timezone.utc) - _dt.datetime.fromisoformat(
                        parent_ts.replace("Z", "+00:00")
                    )
                    if _cot_age > _td(days=14):
                        log.warning(
                            "[COT] Skipping cot_signals.json: content is %dd stale (max 14d). "
                            "Re-run alpha_engine/cot_positioning.py to refresh.",
                            _cot_age.days,
                        )
                        return []
                except Exception:
                    pass
            picks = data.get("picks", [])
            for p in picks:
                # Legacy format uses "pair" instead of "symbol" and lacks =X suffix.
                if not p.get("symbol") and p.get("pair"):
                    p["symbol"] = p["pair"] + "=X"
                # Map BUY/SELL signal to canonical direction (normalize_pick also does this,
                # but setting it here ensures it survives any early-exit paths).
                if not p.get("direction") and p.get("signal"):
                    _sig = str(p["signal"]).upper()
                    p["direction"] = "SHORT" if "SELL" in _sig else "LONG"
                if not p.get("strategy"):
                    p["strategy"] = "cftc_cot_commercial_signal"
                if not p.get("asset_class"):
                    p["asset_class"] = "FOREX"
                if not p.get("timeframe"):
                    p["timeframe"] = "1w"
                if parent_ts and not any(
                    p.get(_k)
                    for _k in ("timestamp", "generated_at", "entry_date", "detected_at", "created_at")
                ):
                    p["generated_at"] = parent_ts
            return picks
        # B20 (2026-05-02): penny_picks_latest.json uses "top_picks" as its
        # pick-list key.  Handle it before the generic key loop so the
        # normalization step (direction + strategy + asset_class) applies.
        if "top_picks" in data and isinstance(data.get("top_picks"), list) and data["top_picks"]:
            picks = data["top_picks"]
            parent_ts = data.get("generated_at") or data.get("date")
            _rating_to_dir = {
                "STRONG_BUY": "LONG", "BUY": "LONG", "MODERATE_BUY": "LONG",
                "STRONG_SELL": "SHORT", "SELL": "SHORT",
            }
            for p in picks:
                if not p.get("direction"):
                    p["direction"] = _rating_to_dir.get(
                        str(p.get("rating", "")).upper(), "LONG"
                    )
                if not p.get("strategy"):
                    p["strategy"] = "penny_stock_screener"
                if not p.get("asset_class"):
                    p["asset_class"] = "EQUITY"
                if parent_ts and not any(
                    p.get(_k)
                    for _k in ("timestamp", "generated_at", "entry_date", "detected_at", "created_at")
                ):
                    p["generated_at"] = parent_ts
            return picks
        for key in (
            "consensus_picks",
            "activePicks",
            "active_picks",
            "open_picks",
            "picks",
            "forward_picks",
            "open_trades",
            "trades",
            "top",
            "winners",
            "super_signals",
            "signals",
            "predictions",
            "forward_signals",
            "closedPicks",
            "closed_picks",
            # 2026-04-14: goldmine_stocks closed_trades.json uses "trades" as the
            # top-level key. Without this entry, _extract_picks returned [] and
            # all 85 goldmine closed trades were silently dropped — meaning the
            # strategy leaderboard never saw goldmine, fwd_trades stayed 0,
            # and goldmine picks could never satisfy hc_filter Gate 4.
            "trades",
        ):
            if key in data and isinstance(data[key], list) and data[key]:
                picks = data[key]
                # Propagate parent-level timestamps into child picks that would
                # otherwise be dropped later as "no timestamp" actives.
                parent_ts = (
                    data.get("generated_at")
                    or data.get("scan_time")
                    or data.get("timestamp")
                    or data.get("created_at")
                )
                if parent_ts:
                    for p in picks:
                        if not any(
                            p.get(_k)
                            for _k in (
                                "timestamp",
                                "generated_at",
                                "entry_date",
                                "entryDate",
                                "detected_at",
                                "created_at",
                            )
                        ):
                            p["generated_at"] = parent_ts
                if key == "super_signals":
                    for p in picks:
                        # Set a descriptive strategy name from signal tier + source system
                        if not p.get("strategy") and not p.get("algorithm"):
                            tier = p.get("signal_tier", "consensus").lower()
                            src = p.get("source_system", "")
                            p["strategy"] = f"super signal ({tier})" + (
                                f" via {src}" if src else ""
                            )
                return picks
    return []


# ── Orphan-emitter schema normalizer (2026-04-28) ────────────────────────
# Maps orphan_emitter_* source_system tags to expected asset_class + sane
# defaults for fields the downstream pipeline expects but the bond/etf/
# futures-agent emitters don't currently set.
_ORPHAN_EMITTER_ASSET_CLASS = {
    "orphan_emitter_bond": "BOND",
    "orphan_emitter_etf": "EQUITY",  # ETFs roll up to EQUITY in the dashboard
    "orphan_emitter_futures": "FUTURES",
    "orphan_emitter_forex_futures": None,  # picks self-tag (FOREX/FUTURES/COMMODITY/STOCKS/EQUITY)
}


def _normalize_orphan_emitter_pick(raw: dict, source_system: str) -> dict:
    """Pre-normalize an orphan-emitter raw pick before _normalize_pick().

    Fills:
      - asset_class (if missing) from filename-inferred class
      - source_system (if missing) so derive_asset_class can use it
      - at_issue_trust_tier="UNTRUSTED" (these picks bypassed production
        scanner gates by virtue of going to a sidecar JSON, so they should
        not be treated as trusted until forward-validated).

    Idempotent: never overwrites a field the emitter set.
    """
    if not isinstance(raw, dict):
        return raw
    inferred_ac = _ORPHAN_EMITTER_ASSET_CLASS.get(source_system)
    # 2026-05-19 defense-in-depth (resolver-step7 BOND dispatch bug): refuse a
    # non-crypto label on an obviously-crypto symbol. The bond_picks.json
    # filename used to stamp BOND on any contents, which is how 500 memecoin
    # rows landed in at_raw_picks tagged BOND.
    sym = str(raw.get("symbol") or "")
    if inferred_ac and inferred_ac != "CRYPTO":
        try:
            from audit_trail.asset_classification import is_obviously_crypto_symbol
        except Exception:
            is_obviously_crypto_symbol = lambda _s: False  # fail-soft
        if is_obviously_crypto_symbol(sym):
            logging.warning(
                "[orphan_emitter] refusing %s tag on crypto symbol %s (source=%s) - "
                "downgrading to CRYPTO to prevent at_raw_picks contamination",
                inferred_ac, sym, source_system,
            )
            raw["asset_class"] = "CRYPTO"
            raw["_orphan_emitter_class_override"] = (
                f"refused_{inferred_ac}_for_crypto_symbol"
            )
            inferred_ac = "CRYPTO"
    if inferred_ac and not raw.get("asset_class"):
        raw["asset_class"] = inferred_ac
    if not raw.get("source_system"):
        raw["source_system"] = source_system
    if not raw.get("at_issue_trust_tier"):
        raw["at_issue_trust_tier"] = "UNTRUSTED"
    return raw


# Sandbox / test-harness blocklist for non-crypto picks.
# Per reports/EDGE_DELIVERY_INVESTIGATION_2026_04_29.md (Fix B), the prior
# rule was a substring check `"rsi2" in strat` that incorrectly killed the
# legitimate Connors RSI2 family (e.g. stocks_rsi2_pullback, EQUITY 73.7% WR /
# PF 5.06 / n=19). Replaced with an explicit equality-or-startswith blocklist.
# Add new test harnesses here with a comment naming the producer.
_NON_CRYPTO_TEST_STRATEGY_BLOCKLIST = frozenset(
    s.lower() for s in (
        # Confirmed test/synthetic strategies — extend conservatively.
        "rsi2_test",
        "rsi2_synthetic",
        "rsi2_sandbox",
    )
)
# Strategy names that are known-good and must NEVER be filtered as test harnesses,
# even if a future heuristic flags them. Used as a safety whitelist.
_NON_CRYPTO_LEGIT_STRATEGY_ALLOWLIST = frozenset(
    s.lower() for s in (
        "stocks_rsi2_pullback",   # Connors RSI2 — EQUITY S-tier (PF 5.06, WR 73.7%)
        "forex_rsi2_mean_reversion",  # Connors RSI2 FX variant
        "connors_rsi2",
    )
)


def _is_non_crypto_test_harness(src: str, strat: str) -> bool:
    """Return True if a non-crypto pick should be filtered as a test harness.

    Replaces the prior substring rule (`"rsi2" in strat`) with an explicit
    blocklist + allowlist. See reports/EDGE_DELIVERY_INVESTIGATION_2026_04_29.md.
    """
    src_l = (src or "").lower()
    strat_l = (strat or "").lower()
    # Allowlist short-circuits any heuristic.
    if strat_l in _NON_CRYPTO_LEGIT_STRATEGY_ALLOWLIST:
        return False
    # Source-level filter: known sandbox sources.
    if src_l in {"signal_validation", "kimi_signal_tracking"}:
        return True
    # Strategy-level filter: explicit blocklist (exact or prefix-match).
    if strat_l in _NON_CRYPTO_TEST_STRATEGY_BLOCKLIST:
        return True
    # Other test/sandbox markers retained from prior rule (these are not
    # legitimate live strategies on EQUITY/FOREX/COMMODITY).
    if "scanner-live" in strat_l:
        return True
    if "momentumema" in strat_l:
        return True
    return False


# ── Data collectors ──


def collect_all_picks():
    """Read all JSON pick sources.

    Returns (active, closed, all_closed_including_expired, active_raw_snapshot).
    ``active_raw_snapshot`` is the full active-pick pool captured BEFORE the
    staleness auto-expiry pass and before any dedup/gate filtering — it backs
    payload's picks.active_raw diagnostic view.
    MySQL non-crypto closed history is merged into ``closed`` in-process; see logs.
    """
    active, closed = [], []
    sources_loaded = 0

    # Counters for external source gate summary
    _gate_killed, _gate_stale, _gate_low_rr = 0, 0, 0
    _ghost_skipped = 0

    for sys_name, active_path, closed_path in JSON_PICK_SOURCES:
        if sys_name in _HIDDEN_SYSTEMS:
            continue
        if sys_name in _GHOST_SYSTEMS:
            log.debug("Skipping ghost system: %s", sys_name)
            _ghost_skipped += 1
            continue
        # Freshness gate: if this system requires fresh data (e.g. tournament
        # curators) and the file is older than the threshold, skip it entirely
        # so stale votes don't bias consensus. See _FRESHNESS_REQUIRED_HOURS.
        if sys_name in _FRESHNESS_REQUIRED_HOURS and active_path:
            try:
                _p = ROOT / active_path
                if _p.exists():
                    import time as _time
                    _age_h = (_time.time() - _p.stat().st_mtime) / 3600.0
                    _max_h = _FRESHNESS_REQUIRED_HOURS[sys_name]
                    if _age_h > _max_h:
                        _stale_skipped[sys_name] = round(_age_h, 1)
                        log.warning(
                            "[FRESHNESS] Skipping %s: %.1fh stale (max %dh)",
                            sys_name, _age_h, _max_h,
                        )
                        continue
            except Exception as _e:
                log.debug("Freshness check failed for %s: %s", sys_name, _e)
        if active_path:
            data = _safe_json(ROOT / active_path)
            if data:
                picks = _extract_picks(data)
                for p in picks:
                    if (
                        sys_name == "pm_consensus_5plus"
                        and int(p.get("agreement_level", 0)) < 5
                    ):
                        continue
                    # Orphan-emitter pre-normalization: fills asset_class /
                    # source_system / at_issue_trust_tier defaults for picks
                    # coming from bond/etf/futures-agent + forex_futures
                    # JSONs that bypass production_scanner gates.
                    if sys_name.startswith("orphan_emitter_"):
                        p = _normalize_orphan_emitter_pick(p, sys_name)
                    bucket_status = (
                        "CLOSED" if _looks_resolved_source_pick(p) else "OPEN"
                    )
                    normalized = _normalize_pick(p, sys_name, bucket_status)

                    # Apply external source quality gate for picks bypassing production_scanner
                    if sys_name in _EXTERNAL_SOURCES and bucket_status == "OPEN":
                        action, reason = _apply_external_source_gate(
                            normalized, sys_name
                        )
                        if action == "killed":
                            _gate_killed += 1
                            log.debug(
                                "[DASHBOARD GATE] Killed %s pick: %s", sys_name, reason
                            )
                            continue  # Hard-remove killed strategy picks
                        if action == "tagged":
                            log.debug(
                                "[DASHBOARD GATE] Tagged %s pick: %s", sys_name, reason
                            )
                            if normalized.get("_stale"):
                                _gate_stale += 1
                            if normalized.get("_low_rr"):
                                _gate_low_rr += 1

                    if bucket_status == "OPEN":
                        active.append(normalized)
                    else:
                        # Some "active" source files are really mixed ledgers with
                        # resolved rows embedded beside open ones. Route those
                        # resolved entries into the closed bucket immediately.
                        closed.append(normalized)
                sources_loaded += 1

        if closed_path:
            data = _safe_json(ROOT / closed_path)
            if data:
                picks = _extract_picks(data)
                for p in picks:
                    # For rapid_fire now_picks.json, only count as closed if outcome is resolved (not PENDING)
                    if sys_name == "rapid_fire" and closed_path.endswith(
                        "now_picks.json"
                    ):
                        outcome_1_5 = p.get("outcome_1_5", "")
                        outcome_2_0 = p.get("outcome_2_0", "")
                        # If both outcomes are PENDING, this is actually an active pick
                        if outcome_1_5 == "PENDING" and outcome_2_0 == "PENDING":
                            active.append(_normalize_pick(p, sys_name, "OPEN"))
                            continue
                    # Goldmine closed_trades.json uses a different schema (ticker,
                    # final_return_pct, entry_date/exit_date, algo_count) -- pre-normalize
                    # so _normalize_pick can find symbol, pnl_pct, closed_at, strategy.
                    if sys_name == "goldmine_stocks":
                        p = _normalize_goldmine_closed_trade(p)
                    closed.append(_normalize_pick(p, sys_name, "CLOSED"))
                sources_loaded += 1

    # ── Special sources with non-standard formats ──

    # KIMI Rise of the Claw (object with activePicks)
    kimi = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/active_picks.json")
    if kimi and kimi.get("activePicks"):
        for p in kimi["activePicks"]:
            active.append(_normalize_pick(p, "kimi_riseoftheclaw", "OPEN"))
        sources_loaded += 1

    # STOCKS competition (object with picks array)
    stocks = _safe_json(ROOT / "STOCKS/competition/forward_picks.json")
    if stocks and stocks.get("picks"):
        for p in stocks["picks"]:
            status = "CLOSED" if _is_closed_status(p.get("status", "")) else "OPEN"
            bucket = closed if status == "CLOSED" else active
            bucket.append(_normalize_pick(p, "stocks_competition", status))
        sources_loaded += 1

    # Fast STOCKS competition (object with picks array)
    fast_stocks = _safe_json(ROOT / "STOCKS/competition/fast_forward_picks.json")
    if fast_stocks and fast_stocks.get("picks"):
        for p in fast_stocks["picks"]:
            status = "CLOSED" if _is_closed_status(p.get("status", "")) else "OPEN"
            bucket = closed if status == "CLOSED" else active
            bucket.append(_normalize_pick(p, "fast_stocks_competition", status))
        sources_loaded += 1

    # Mercury2 Fast (object with picks array)
    mercury2_fast = _safe_json(ROOT / "mercury2/mercury2_fast_picks.json")
    if mercury2_fast and mercury2_fast.get("picks"):
        for p in mercury2_fast["picks"]:
            # Skip picks with broken entry prices (mercury2_fast bug: 10x-1000x too high)
            entry = p.get("entry_price", 0)
            if isinstance(entry, (int, float)) and entry > 500000:
                continue
            s = str(p.get("status", "")).upper()
            status = (
                "CLOSED"
                if s in ("CLOSED", "TIME_EXIT", "EXPIRED", "TP_HIT", "SL_HIT")
                else "OPEN"
            )
            bucket = closed if status == "CLOSED" else active
            bucket.append(_normalize_pick(p, "mercury2_fast", status))
        sources_loaded += 1

    # Claude Gainer ML (object with picks dict — all are BUY, tp is tp1_price)
    claude = _safe_json(ROOT / "claude_gainer_ml/tracker/claude_live_picks.json")
    if claude and claude.get("picks"):
        picks_data = claude["picks"]
        pick_list = (
            picks_data
            if isinstance(picks_data, list)
            else list(picks_data.values())
            if isinstance(picks_data, dict)
            else []
        )
        for p in pick_list:
            # Remap fields: no direction field (all BUY), tp is tp1_price, no strategy field
            p.setdefault("direction", "BUY")
            if not p.get("strategy"):
                p["strategy"] = f"claude_gainer_{p.get('bar_size', '4H').lower()}"
            if not p.get("take_profit") and p.get("tp1_price"):
                p["take_profit"] = p["tp1_price"]
            if not p.get("stop_loss") and p.get("sl_price"):
                p["stop_loss"] = p["sl_price"]
            status = "CLOSED" if _is_closed_status(p.get("status", "")) else "OPEN"
            bucket = closed if status == "CLOSED" else active
            bucket.append(_normalize_pick(p, "claude_gainer", status))
        sources_loaded += 1

    # Cross-Aggregation consensus outcomes (object with "active" and "closed" arrays)
    consensus_out = _safe_json(ROOT / "cross_aggregation/data/consensus_outcomes.json")
    if consensus_out and isinstance(consensus_out, dict):
        co_count = 0
        for bucket_key, default_status in [("active", "OPEN"), ("closed", "CLOSED")]:
            items = consensus_out.get(bucket_key, [])
            if not isinstance(items, list):
                continue
            for p in items:
                if not isinstance(p, dict):
                    continue
                # Map source field to system name: "super_signal" -> super_signals, "consensus" -> aggregated_picks
                src = str(p.get("source", "consensus")).lower()
                if "super" in src:
                    sys_name = "super_signals"
                else:
                    sys_name = "aggregated_picks"
                # Determine status: closed array items use their status field (WON/LOST/etc.)
                if default_status == "CLOSED":
                    status = "CLOSED"
                else:
                    status = (
                        "CLOSED" if _is_closed_status(p.get("status", "")) else "OPEN"
                    )
                target = closed if status == "CLOSED" else active
                target.append(_normalize_pick(p, sys_name, status))
                co_count += 1
        if co_count:
            sources_loaded += 1
            log.info("  Consensus outcomes: %d picks", co_count)

    # ML Crypto Predictor (all_picks_log) — hot shard (OPEN/ACTIVE only
    # after the 2026-05-14 status-shard rotation; legacy file pre-split is
    # still a flat list).
    mlcp = _safe_json(
        ROOT / "ml_crypto_predictor/enhanced_models/live_picks/all_picks_log.json"
    )
    if mlcp and isinstance(mlcp, list):
        for p in mlcp:
            status = "CLOSED" if _is_closed_status(p.get("status", "")) else "OPEN"
            bucket = closed if status == "CLOSED" else active
            bucket.append(_normalize_pick(p, "ml_crypto_predictor", status))
        sources_loaded += 1

    # ML Crypto Predictor cold shards — gzipped monthly archives of
    # terminal-status picks, written by live_picks_tracker.py at close time.
    # See tools/migrate_all_picks_log.py for the migration history.
    import gzip as _gz_mlcp
    _cold_dir_mlcp = ROOT / "ml_crypto_predictor/enhanced_models/live_picks/closed"
    if _cold_dir_mlcp.exists():
        _cold_count = 0
        for _shard in sorted(_cold_dir_mlcp.glob("closed_*.json.gz")):
            try:
                with _gz_mlcp.open(_shard, "rt", encoding="utf-8") as f:
                    import json as _j_mlcp
                    _shard_data = _j_mlcp.load(f)
            except Exception as _e_mlcp:
                log.warning("  ml_crypto cold shard %s read failed: %s",
                            _shard.name, _e_mlcp)
                continue
            if not isinstance(_shard_data, list):
                continue
            for p in _shard_data:
                closed.append(_normalize_pick(p, "ml_crypto_predictor", "CLOSED"))
                _cold_count += 1
        if _cold_count:
            log.info("  ml_crypto cold shards: %d closed picks across %d files",
                     _cold_count, sum(1 for _ in _cold_dir_mlcp.glob("closed_*.json.gz")))

    # Baby Strats Dashboard — forward trades embedded in each strategy
    bsd = _safe_json(ROOT / "battleground/data/baby_strats_dashboard.json")
    if bsd:
        bsd_count = 0
        for strat in bsd.get("strategies", []):
            ft = strat.get("forward_trades", [])
            # Derive confidence from parent strategy metrics if trade has none
            strat_wr = _float(strat.get("win_rate", strat.get("wr", 0)))
            strat_sharpe = _float(strat.get("sharpe", strat.get("sharpe_ratio", 0)))
            strat_conf = 0
            if strat_wr > 0:
                strat_conf = min(
                    0.90, strat_wr if strat_wr <= 1.0 else strat_wr / 100.0
                )
            elif strat_sharpe > 0:
                strat_conf = min(0.90, 0.40 + strat_sharpe * 0.15)
            for t in ft:
                trade_conf = t.get("confidence", 0)
                if not trade_conf or _float(trade_conf) == 0:
                    trade_conf = (
                        strat_conf if strat_conf > 0 else 0.55
                    )  # default moderate
                pick = {
                    "symbol": t.get("symbol", strat.get("symbol", "BTCUSDT")),
                    "direction": t.get("direction", ""),
                    "entry_price": t.get("entry_price", 0),
                    "exit_price": t.get("exit_price", 0),
                    "take_profit": t.get("tp", 0),
                    "stop_loss": t.get("sl", 0),
                    "pnl_pct": t.get("pnl_pct", 0),
                    "strategy": strat.get("name", ""),
                    "timestamp": t.get("entry_time", t.get("exit_time", "")),
                    "exit_time": t.get("exit_time", t.get("entry_time", "")),
                    "exit_reason": t.get("exit_reason", ""),
                    "confidence": trade_conf,
                }
                status = "CLOSED" if t.get("pnl_pct") is not None else "OPEN"
                bucket = closed if status == "CLOSED" else active
                bucket.append(_normalize_pick(pick, "baby_strats_forward", status))
                bsd_count += 1
        if bsd_count:
            sources_loaded += 1
            log.info("  Baby strats forward trades: %d", bsd_count)

    # KIMI Rise of the Claw — live_competition.json (closed trades per algorithm)
    kimi_comp = _safe_json(ROOT / "riseoftheclaw/data/live_competition.json")
    if kimi_comp:
        kimi_closed_count = 0
        algos = kimi_comp.get("algorithms", [])
        if isinstance(algos, dict):
            algos = list(algos.values())
        for algo in algos:
            if not isinstance(algo, dict):
                continue
            algo_name = algo.get("id", algo.get("name", "kimi_unknown"))
            for t in algo.get("closedPicks", algo.get("closedTrades", [])):
                if not isinstance(t, dict):
                    continue
                # Compute PnL from prices when pnlPct is empty (same fix as Pump Watch)
                raw_pnl = t.get("pnlPct", t.get("pnl_pct", 0))
                entry_price = _float(t.get("entryPrice", t.get("entry_price", 0)))
                exit_price = _float(
                    t.get("exitPrice", t.get("exit_price", t.get("currentPrice", 0)))
                )
                if (
                    (not raw_pnl or _float(raw_pnl) == 0)
                    and entry_price > 0
                    and exit_price > 0
                ):
                    sig = t.get("signal", "BUY")
                    if str(sig).upper() in ("SELL", "SHORT"):
                        raw_pnl = round(
                            (entry_price - exit_price) / entry_price * 100, 4
                        )
                    else:
                        raw_pnl = round(
                            (exit_price - entry_price) / entry_price * 100, 4
                        )
                pick = {
                    "symbol": t.get("symbol", t.get("pair", "")),
                    "direction": "BUY"
                    if str(t.get("signal", "BUY")).upper() in ("BUY", "LONG")
                    else "SELL",
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "take_profit": t.get("tp", 0),
                    "stop_loss": t.get("sl", 0),
                    "pnl_pct": raw_pnl,
                    "strategy": algo_name,
                    "timestamp": t.get("entryDate", t.get("exitDate", "")),
                    "exit_time": t.get("exitDate", ""),
                    "exit_reason": t.get("outcome", t.get("exitReason", "")),
                    "confidence": t.get("confidence", 0.6),
                }
                closed.append(_normalize_pick(pick, "kimi_riseoftheclaw", "CLOSED"))
                kimi_closed_count += 1
            # Also pick up active picks per algorithm
            for p in algo.get("activePicks", []):
                if not isinstance(p, dict):
                    continue
                pick = {
                    "symbol": p.get("symbol", p.get("pair", "")),
                    "direction": "BUY"
                    if str(p.get("signal", "BUY")).upper() in ("BUY", "LONG")
                    else "SELL",
                    "entry_price": p.get("entryPrice", p.get("entry_price", 0)),
                    "take_profit": p.get("tp", 0),
                    "stop_loss": p.get("sl", 0),
                    "strategy": algo_name,
                    "timestamp": p.get("entryDate", p.get("timestamp", "")),
                    "confidence": p.get("confidence", 0.6),
                }
                active.append(_normalize_pick(pick, "kimi_riseoftheclaw", "OPEN"))
        if kimi_closed_count:
            sources_loaded += 1
            log.info("  KIMI live_competition closed trades: %d", kimi_closed_count)

    # KIMI_RISEOFTHECLAW direct closed picks (contains forex + equity trades not in live_competition)
    kimi_direct_closed = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/closed_picks.json")
    if kimi_direct_closed and isinstance(kimi_direct_closed, list):
        kdc_count = 0
        for p in kimi_direct_closed:
            if not isinstance(p, dict):
                continue
            # Normalize the pick properly with asset class preservation
            norm = _normalize_pick(p, "kimi_riseoftheclaw", "CLOSED")
            # Ensure asset_class is preserved for non-crypto picks
            ac = (p.get("asset_class") or p.get("category") or "").upper()
            if ac in ("FOREX", "EQUITY", "STOCK", "ETF", "FUTURES", "COMMODITY", "BOND"):
                norm["asset_class"] = ac
            closed.append(norm)
            kdc_count += 1
        if kdc_count:
            sources_loaded += 1
            log.info("  KIMI_RISEOFTHECLAW direct closed picks: %d", kdc_count)

    # Incubator forward signals
    inc = _safe_json(ROOT / "incubator/backtest_results/forward_signals.json")
    if inc:
        for t in inc.get("open_trades", []):
            active.append(_normalize_pick(t, "incubator_forward", "OPEN"))
        sources_loaded += 1

    # Battleground incubator ledger (9 new strategies with TP/SL tracking)
    inc_ledger = _safe_json(ROOT / "battleground/data/incubator_ledger.json")
    if inc_ledger:
        for t in inc_ledger.get("open_picks", []):
            active.append(_normalize_pick(t, "incubator_battleground", "OPEN"))
        for t in inc_ledger.get("closed_trades", []):
            closed.append(
                _normalize_pick(t, "incubator_battleground", t.get("outcome", "CLOSED"))
            )

    # Incubator Gainer (non-standard: picks in "top" array with composite scores)
    inc_gainer = _safe_json(
        ROOT / "incubator/agents/claude_code_01/data/gainer_scores_latest.json"
    )
    if inc_gainer and inc_gainer.get("top"):
        inc_count = 0
        for p in inc_gainer["top"]:
            if not isinstance(p, dict) or not p.get("is_buy"):
                continue
            pick = {
                "symbol": p.get("symbol", ""),
                "direction": "BUY",
                "entry_price": p.get("price", 0),
                "take_profit": p.get("tp", 0),
                "stop_loss": p.get("sl", 0),
                "confidence": p.get("confidence", 0),
                "strategy": "incubator_gainer_composite",
                "timestamp": inc_gainer.get("generated_at", ""),
            }
            active.append(_normalize_pick(pick, "incubator_gainer", "OPEN"))
            inc_count += 1
        if inc_count:
            sources_loaded += 1
            log.info("  Incubator gainer picks: %d", inc_count)

    # Goldmine Unified Picks (non-standard: picks in "picks" array — already compatible)
    gm_unified = _safe_json(ROOT / "data/goldmine/unified_picks.json")
    if gm_unified and gm_unified.get("picks"):
        gm_count = 0
        for p in gm_unified["picks"]:
            if not isinstance(p, dict):
                continue
            p_type = p.get("type", "unknown")
            sys_name = "goldmine_meme" if "meme" in p_type else "goldmine_stocks"
            status = "CLOSED" if _is_closed_status(p.get("status", "")) else "OPEN"
            bucket = closed if status == "CLOSED" else active
            bucket.append(_normalize_pick(p, sys_name, status))
            gm_count += 1
        if gm_count:
            sources_loaded += 1
            log.info("  Goldmine unified picks: %d", gm_count)

    # Goldmine Stock Picks (non-standard: picks in "consensus_picks" array)
    gm_stocks = _safe_json(ROOT / "data/goldmine/stock_picks.json")
    if gm_stocks and gm_stocks.get("consensus_picks"):
        gs_count = 0
        for p in gm_stocks["consensus_picks"]:
            if not isinstance(p, dict):
                continue
            # Normalize confidence from avg_score (per-algo avg, 0-100)
            # rather than consensus_score (sum across algos, can be 500+)
            avg_score = p.get("avg_score", 0)
            if avg_score > 1:
                conf = round(min(1.0, avg_score / 100.0), 3)  # round to avoid 0.7490000000001
            else:
                conf = round(avg_score, 3) if avg_score > 0 else 0.5

            # Get technical data if available
            rsi = p.get("rsi") or p.get("rsi_14h")
            volume = p.get("volume")
            volume_ratio = p.get("volume_ratio")
            htf_trend = p.get("htf_trend", "")

            # Determine regime from trend
            regime = ""
            if htf_trend == "bull":
                regime = "bullish"
            elif htf_trend == "bear":
                regime = "bearish"
            else:
                regime = "neutral"

            pick = {
                "symbol": p.get("ticker", ""),
                "direction": "BUY",
                "entry_price": p.get("avg_entry_price", p.get("latest_price", 0)),
                "confidence": conf,
                "strategy": f"goldmine_{p.get('consensus_count', 0)}x_consensus",
                "timestamp": gm_stocks.get("generated_at", ""),
                "take_profit": p.get("tp_price", 0),
                "stop_loss": p.get("sl_price", 0),
                # Technical indicators
                "rsi": rsi,
                "rsi_at_entry": rsi,
                "volume": volume,
                "volume_ratio": volume_ratio,
                "htf_trend": htf_trend,
                "htf_bias": htf_trend,
                "htf_alignment": htf_trend,
                "regime_at_entry": regime,
                "market_regime": regime,
            }
            active.append(_normalize_pick(pick, "goldmine_stocks", "OPEN"))
            gs_count += 1
        if gs_count:
            sources_loaded += 1
            log.info("  Goldmine stock consensus picks: %d", gs_count)

    # KIMI Live Signals (non-standard: "crypto_signals" + "forex_signals" keys)
    kimi_live = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/live_signals_now.json")
    if kimi_live:
        kls_count = 0
        for sig_key in ("crypto_signals", "forex_signals"):
            for p in kimi_live.get(sig_key, []):
                if not isinstance(p, dict):
                    continue
                pick = {
                    "symbol": p.get("symbol", ""),
                    "direction": "BUY"
                    if str(p.get("signal", "BUY")).upper() in ("BUY", "LONG")
                    else "SELL",
                    "entry_price": p.get("entryPrice", p.get("price", 0)),
                    "take_profit": p.get("take_profit", p.get("targetPrice", 0)),
                    "stop_loss": p.get("stop_loss", p.get("stopPrice", 0)),
                    "confidence": (p.get("confidence", 0) / 100.0)
                    if p.get("confidence", 0) > 1
                    else p.get("confidence", 0),
                    "strategy": p.get("algorithm", "kimi_live"),
                    "timestamp": p.get(
                        "entryDate",
                        p.get("timestamp", kimi_live.get("generated_at", "")),
                    ),
                }
                active.append(_normalize_pick(pick, "kimi_live_signals", "OPEN"))
                kls_count += 1
        if kls_count:
            sources_loaded += 1
            log.info("  KIMI live signals: %d", kls_count)

    # ── Prediction Market Consensus Signals ──
    # Prefer the stricter alpha_engine consensus feed; fall back to the older
    # cross-market file only when the curated feed is unavailable.
    pm_signals, pm_consensus_source = _load_prediction_market_consensus_signals()
    if pm_signals:
        pm_count = 0
        pm_hc_count = 0
        for p in pm_signals:
            if not isinstance(p, dict):
                continue
            high_conviction = bool(p.get("high_conviction", False))
            p["high_conviction"] = high_conviction
            # Boost confidence slightly for high-conviction consensus entries
            if high_conviction and p.get("confidence", 0) < 0.9:
                p["confidence"] = min(0.95, _float(p.get("confidence", 0.7)) + 0.08)
            norm = _normalize_pick(p, "prediction_market_consensus", "OPEN")
            active.append(norm)
            pm_count += 1
            # Virtual high-conviction tier: duplicate into pm_high_conviction for dashboard highlighting
            if high_conviction:
                hc_norm = dict(norm)
                hc_norm["source_system"] = "pm_high_conviction"
                hc_norm["strategy"] = "pm_consensus_high_conviction"
                hc_norm["type_label"] = "🔮 PM High Conviction"
                active.append(hc_norm)
                pm_hc_count += 1
        if pm_count:
            sources_loaded += 1
            log.info(
                "  PM consensus signals: %d (%d high conviction) from %s",
                pm_count,
                pm_hc_count,
                pm_consensus_source,
            )

    # ── Crypto Winners (PHP API) ──
    # Fetches historical picks from the findtorontoevents.ca crypto_winners API
    # and caches the result locally for offline/fast access.
    crypto_winners_cache = ROOT / "audit_trail" / "data" / "crypto_winners_cache.json"
    try:
        url = "https://findtorontoevents.ca/findcryptopairs/api/crypto_winners.php?action=history"
        req = urllib.request.Request(url, headers={"User-Agent": "AuditDashboard/1.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        cw_data = json.loads(resp.read().decode("utf-8"))
        # Cache for offline use
        crypto_winners_cache.parent.mkdir(parents=True, exist_ok=True)
        crypto_winners_cache.write_text(json.dumps(cw_data), encoding="utf-8")
        log.info("  Crypto Winners API: fetched successfully")
    except Exception as e:
        log.warning("Crypto Winners API fetch failed (%s), using cache", e)
        cw_data = _safe_json(crypto_winners_cache)

    if cw_data:
        cw_history = cw_data.get(
            "history", cw_data if isinstance(cw_data, list) else []
        )
        cw_count = 0
        for entry in cw_history:
            if not isinstance(entry, dict):
                continue
            # Map crypto_winners fields to standard pick format
            verdict = str(entry.get("verdict", "")).upper()
            direction = (
                "LONG"
                if verdict in ("BUY", "LEAN_BUY")
                else "SHORT"
                if verdict == "SELL"
                else "LONG"
            )
            outcome = str(entry.get("outcome", "")).lower()
            is_closed = outcome in ("win", "loss", "partial_win", "partial_loss")
            status = "CLOSED" if is_closed else "OPEN"
            pick = {
                "symbol": entry.get("pair", ""),
                "direction": direction,
                "entry_price": entry.get("price_at_signal", 0),
                "exit_price": entry.get("price_at_resolve", 0),
                "take_profit": _float(entry.get("price_at_signal", 0))
                * (1 + _float(entry.get("target_pct", 0)) / 100)
                if _float(entry.get("price_at_signal", 0)) > 0
                and _float(entry.get("target_pct", 0)) != 0
                else 0,
                "stop_loss": _float(entry.get("price_at_signal", 0))
                * (1 - _float(entry.get("risk_pct", 0)) / 100)
                if _float(entry.get("price_at_signal", 0)) > 0
                and _float(entry.get("risk_pct", 0)) != 0
                else 0,
                "pnl_pct": entry.get("pnl_pct", 0),
                "score": entry.get("score", 0),
                "confidence": min(1.0, _float(entry.get("score", 0)) / 100)
                if _float(entry.get("score", 0)) > 0
                else 0.5,
                "strategy": "crypto_winners",
                "timestamp": entry.get("created_at", ""),
                "exit_reason": outcome if is_closed else "",
                "resolved_at": entry.get("resolved_at", ""),
            }
            bucket = closed if status == "CLOSED" else active
            bucket.append(_normalize_pick(pick, "crypto_winners", status))
            cw_count += 1
        if cw_count:
            sources_loaded += 1
            log.info("  Crypto Winners: %d picks loaded", cw_count)

    # ── Claude Gainer ML performance enrichment ──
    # The live picks are already handled above (claude_gainer special handler).
    # Also load performance summary for closed trade stats.
    cg_perf = _safe_json(ROOT / "claude_gainer_ml/tracker/claude_performance.json")
    if cg_perf and cg_perf.get("recent_10"):
        # Use the file's updated_at timestamp as a fallback for picks without timestamps
        fallback_timestamp = cg_perf.get("updated_at", "")
        cg_history = _safe_json(
            ROOT / "claude_gainer_ml/tracker/claude_pick_history.json"
        )
        cg_live = _safe_json(ROOT / "claude_gainer_ml/tracker/claude_live_picks.json")
        perf_index = _build_claude_perf_index(
            cg_history if isinstance(cg_history, list) else [],
            cg_live.get("picks", []) if isinstance(cg_live, dict) else [],
        )
        enriched_count = 0
        for t in cg_perf["recent_10"]:
            if not isinstance(t, dict):
                continue
            matched_row = _match_claude_perf_row(t, perf_index)
            if matched_row:
                enriched_count += 1
            pick = _build_claude_perf_pick(t, matched_row, fallback_timestamp)
            closed.append(_normalize_pick(pick, "claude_gainer_ml_perf", "CLOSED"))
        sources_loaded += 1
        log.info(
            "  Claude Gainer ML performance: %d recent trades (%d enriched from tracker history)",
            len(cg_perf.get("recent_10", [])),
            enriched_count,
        )

    log.info(
        "Loaded picks from %d sources: %d active, %d closed",
        sources_loaded,
        len(active),
        len(closed),
    )

    # ── CAPTURE the true raw pre-filter pool (2026-05-19 active_raw bug fix) ──
    # Snapshot the FULL active-pick list here — before the staleness auto-expiry
    # pass and before any dedup/gate filtering below. This becomes payload's
    # picks.active_raw, the diagnostic "what was generated before filtering" view.
    # Previously active_raw was snapshotted AFTER auto-expiry had already dropped
    # non-crypto emitter picks (ETF/BOND especially via NON_CRYPTO_MAX_AGE), so
    # those picks never appeared even in the raw view. Shallow copy of the list
    # is enough — we only need the membership snapshot, the pick dicts themselves
    # may continue to be enriched/mutated in place downstream.
    active_raw_snapshot = list(active)

    # ── Auto-expire stale picks (asset-class-aware cutoffs) ──
    # Must match audit_trail/quality_gates.py (CRYPTO_MAX_AGE_HOURS / NON_CRYPTO_MAX_AGE_HOURS)
    from datetime import datetime, timedelta, timezone

    _CRYPTO_MAX_AGE = timedelta(hours=float(CRYPTO_MAX_AGE_HOURS))
    _NON_CRYPTO_MAX_AGE = timedelta(hours=float(NON_CRYPTO_MAX_AGE_HOURS))
    _NON_CRYPTO_CLASSES = {
        "equity",
        "equities",
        "forex",
        "futures",
        "commodity",
        "commodities",
        "bond",
        "bonds",
        "etf",
        "stock",
        "stocks",
    }
    now = datetime.now(timezone.utc)
    _tz_map = {
        "EST": "-05:00",
        "EDT": "-04:00",
        "CST": "-06:00",
        "CDT": "-05:00",
        "PST": "-08:00",
        "PDT": "-07:00",
        "UTC": "+00:00",
    }
    fresh_active = []
    expired_count = 0
    for p in active:
        ts = _extract_freshness_timestamp_str(p)
        asset_cls = str(p.get("asset_class") or p.get("category") or "").lower().strip()
        max_age = (
            _NON_CRYPTO_MAX_AGE if asset_cls in _NON_CRYPTO_CLASSES else _CRYPTO_MAX_AGE
        )
        if ts:
            try:
                # Strip timezone abbreviations and replace with offset
                ts_clean = ts.strip()
                for abbr, offset in _tz_map.items():
                    if ts_clean.endswith(" " + abbr):
                        ts_clean = ts_clean[: -len(abbr) - 1].strip() + offset
                        break
                ts_clean = ts_clean.replace("Z", "+00:00")
                if (
                    "+" not in ts_clean
                    and "-" not in ts_clean[10:]
                    and len(ts_clean) >= 19
                ):
                    ts_clean += "+00:00"
                dt = datetime.fromisoformat(ts_clean)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_h = int((now - dt).total_seconds() / 3600)
                if now - dt > max_age:
                    p["status"] = "EXPIRED"
                    p["exit_reason"] = f"STALE (auto-expired >{age_h}h)"
                    # Mark expired picks with no PnL data so stats excludes them
                    # from win/loss calculations (they aren't real resolved trades)
                    pnl_val = _float(float(p.get("pnl_pct", 0) or 0))
                    if pnl_val == 0:
                        p["expired_no_pnl"] = True
                    closed.append(p)
                    expired_count += 1
                    continue
            except (ValueError, TypeError):
                pass
        fresh_active.append(p)
    if expired_count:
        log.info(
            "  Auto-expired %d stale picks (crypto >%sh, non-crypto >%sh)",
            expired_count,
            CRYPTO_MAX_AGE_HOURS,
            NON_CRYPTO_MAX_AGE_HOURS,
        )
    active = fresh_active

    # ── Separate auto-expired picks from real closed picks ──
    # Auto-expired picks (pnl=0 + stale/expired exit_reason) inflate trade counts
    # and deflate win rates. We keep them in the payload for transparency but
    # exclude them from all performance metrics.
    real_closed = []
    auto_expired = []
    for p in closed:
        if _is_auto_expired_pick(p):
            p["_auto_expired"] = True
            auto_expired.append(p)
        else:
            p["_auto_expired"] = False
            real_closed.append(p)

    if auto_expired:
        log.info(
            "  Excluded %d auto-expired picks (0%% PnL, stale/expired) from metrics",
            len(auto_expired),
        )
        # Log per-system breakdown for visibility
        _exp_by_sys = {}
        for ep in auto_expired:
            sys_name = ep.get("source_system", "unknown")
            _exp_by_sys[sys_name] = _exp_by_sys.get(sys_name, 0) + 1
        for sys_name, count in sorted(_exp_by_sys.items(), key=lambda x: -x[1]):
            log.info("    %s: %d auto-expired", sys_name, count)

    # Use real_closed for all metric computations; keep full closed list for display
    all_closed_including_expired = closed  # full list for the payload's recent_closed
    closed = real_closed  # metrics use only real outcomes

    # ── Filter out garbage picks with nonsensical entry prices ──
    # Symbol-aware maximum price thresholds (generous upper bounds).
    # Catches BTC-scale prices leaking onto altcoins (e.g. DOGE at $50K).
    _PRICE_CEILINGS = {
        # Meme / micro-cap tokens
        "DOGE": 10,
        "SHIB": 1,
        "PEPE": 1,
        "FLOKI": 1,
        "BONK": 1,
        "1000SHIB": 1000,
        "1000PEPE": 1000,
        "1000FLOKI": 1000,
        # Mid-cap alts
        "SOL": 5_000,
        "DOT": 5_000,
        "AVAX": 5_000,
        "LINK": 5_000,
        "ADA": 5_000,
        "NEAR": 5_000,
        "UNI": 5_000,
        "AAVE": 5_000,
        "XRP": 100,
        "MATIC": 100,
        "ALGO": 100,
        "ATOM": 5_000,
        # Majors
        "ETH": 50_000,
        "BTC": 500_000,
    }

    def _is_valid_pick(p):
        entry = _float(p.get("entry_price", 0))
        sym = str(p.get("symbol", "")).upper()

        # Hard ceiling: anything > $1M is always garbage
        if entry > 1_000_000:
            return False

        # Symbol-aware ceiling: catch BTC-scale prices on altcoins
        if entry > 0:
            for token, ceiling in _PRICE_CEILINGS.items():
                if token in sym and entry > ceiling:
                    log.warning(
                        "  Corrupt price: %s entry=$%.2f exceeds %s ceiling $%s (strategy=%s)",
                        sym,
                        entry,
                        token,
                        ceiling,
                        p.get("strategy", "?"),
                    )
                    return False

        # --- SANDBOX TEST FILTER ---
        src = str(p.get("source_system", p.get("source", ""))).lower()
        strat = str(p.get("strategy", "")).lower()
        asset = str(p.get("asset_class", "")).upper()

        # Rule 1: EURUSDT is not a real Forex pair, it's a stablecoin crypto.
        if sym == "EURUSDT" and "rapid" in src:
            return False

        # Rule 2: Exclude non-production test harnesses bleeding into live non-crypto stats.
        # Substring rule replaced with explicit blocklist+allowlist to unblock
        # legitimate Connors RSI2 strategies (stocks_rsi2_pullback, etc.).
        # See reports/EDGE_DELIVERY_INVESTIGATION_2026_04_29.md (Fix B).
        _non_crypto = ["FOREX", "FX", "EQUITY", "STOCKS", "COMMODITY", "ETF", "BOND"]
        if asset in _non_crypto:
            if _is_non_crypto_test_harness(src, strat):
                return False

        # entry_price=0 is allowed (for prediction markets, tests, etc)
        # if it reached here, it's not a corrupt price.
        return True

    garbage_count = 0
    clean_active = []
    for p in active:
        if _is_valid_pick(p):
            clean_active.append(p)
        else:
            garbage_count += 1
    clean_closed = []
    for p in closed:
        if _is_valid_pick(p):
            clean_closed.append(p)
        else:
            garbage_count += 1
    if garbage_count:
        log.info("  Filtered %d garbage picks (corrupt entry_price)", garbage_count)
    active = clean_active
    closed = clean_closed

    # ── Universal Pick Resolver: inject resolved picks for untracked systems ──
    resolved_path = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
    if resolved_path.exists():
        try:
            resolved_data = json.loads(resolved_path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(resolved_data, list):
                resolved_count = 0
                for rp in resolved_data:
                    if not isinstance(rp, dict):
                        continue
                    # Normalize resolved pick into dashboard format
                    norm = _normalize_pick(
                        rp, rp.get("source_system", "universal_resolver"), "CLOSED"
                    )
                    # Transfer resolved-specific fields
                    norm["pnl_pct"] = _float(rp.get("pnl_pct", 0) or 0)
                    norm["exit_reason"] = rp.get("exit_reason", "")
                    norm["exit_price"] = _float(rp.get("exit_price", 0) or 0)
                    norm["resolved_at"] = rp.get("resolved_at", "")
                    closed.append(norm)
                    resolved_count += 1
                if resolved_count:
                    log.info(
                        "  Loaded %d universally resolved picks from %s",
                        resolved_count,
                        resolved_path.name,
                    )
        except Exception as e:
            log.warning("  Failed to load universal resolved picks: %s", e)

    # ── Staleness filter: same max-age policy as audit_trail/quality_gates.py ──
    now_utc = datetime.now(timezone.utc)
    stale_count = 0
    kept_no_ts = 0
    kept_unparsed_ts = 0
    fresh_active = []
    for p in active:
        if not isinstance(p, dict) or p.get("skip") or not p.get("symbol"):
            continue
        ts_raw = _extract_freshness_timestamp_str(p)
        asset_cls = str(p.get("asset_class") or p.get("category") or "").lower().strip()
        max_hours = (
            float(NON_CRYPTO_MAX_AGE_HOURS)
            if asset_cls in _NON_CRYPTO_CLASSES
            else float(CRYPTO_MAX_AGE_HOURS)
        )
        if not ts_raw:
            kept_no_ts += 1
            fresh_active.append(p)
            continue
        pick_time = _parse_pick_timestamp_utc(ts_raw)
        if pick_time is None:
            kept_unparsed_ts += 1
            fresh_active.append(p)
            continue
        age_h = (now_utc - pick_time).total_seconds() / 3600
        if age_h > max_hours:
            stale_count += 1
            continue
        fresh_active.append(p)
    if stale_count or kept_no_ts or kept_unparsed_ts:
        log.info(
            "  Staleness filter: removed %d older than max age; kept %d without ts; "
            "kept %d unparseable ts (crypto max=%sh, non-crypto max=%sh)",
            stale_count,
            kept_no_ts,
            kept_unparsed_ts,
            CRYPTO_MAX_AGE_HOURS,
            NON_CRYPTO_MAX_AGE_HOURS,
        )
    active = fresh_active

    closed, _canon_id_drops = _dedupe_closed_trades_by_canonical_id(closed)
    if _canon_id_drops:
        log.info(
            "  Canonical trade ID dedup: removed %d shadow duplicate closed rows",
            _canon_id_drops,
        )

    # ── Deduplication: per (system, symbol, direction, strategy) keep only most recent ──
    # Old dedup included timestamp in key, so ml_crypto_predictor's FETUSDT LONG
    # appeared 11 times at different hours. Now: keep ONE per system+symbol+dir+strategy.
    def _dedup_picks(picks, keep_most_recent=False):
        if keep_most_recent:
            # For active picks: keep the most recent per (system, symbol, direction, strategy)
            best = {}
            dup_count = 0
            for p in picks:
                key = (
                    p.get("source_system", ""),
                    _normalize_symbol(p.get("symbol", "")),
                    p.get("direction", ""),
                    p.get("strategy", ""),
                )
                ts = p.get("timestamp", "")
                if key in best:
                    dup_count += 1
                    # Keep whichever has the more recent timestamp
                    if ts > best[key].get("timestamp", ""):
                        best[key] = p
                else:
                    best[key] = p
            return list(best.values()), dup_count
        else:
            # For closed picks: use the original approach (include timestamp)
            seen = set()
            deduped = []
            dup_count = 0
            for p in picks:
                ts = p.get("timestamp", "")
                ts_key = ts[:16] if ts else ""
                key = (
                    p.get("source_system", ""),
                    _normalize_symbol(p.get("symbol", "")),
                    p.get("direction", ""),
                    str(p.get("entry_price", "")),
                    p.get("strategy", ""),
                    ts_key,
                )
                if key in seen:
                    dup_count += 1
                    continue
                seen.add(key)
                deduped.append(p)
            return deduped, dup_count

    closed, shadow_drops = _prefer_metric_safe_closed_picks(closed)
    if shadow_drops:
        log.info(
            "  Closed-outcome reconciliation: dropped %d stale shadow rows in favor of resolved outcomes",
            shadow_drops,
        )

    active, active_dups = _dedup_picks(active, keep_most_recent=True)
    closed, closed_dups = _dedup_picks(closed, keep_most_recent=False)

    total_dups = active_dups + closed_dups
    if total_dups:
        log.info(
            "  Deduplication: removed %d duplicates (%d active, %d closed)",
            total_dups,
            active_dups,
            closed_dups,
        )

    # ── Second-pass dedup: collapse same-system multi-strategy duplicates ──
    # Within the same source_system, multiple strategies can fire on the same
    # symbol+direction at the same timestamp.  Keep only the highest-scored pick
    # per (source_system, symbol, direction, timestamp[:16]); remove the rest.
    def _collapse_intra_system_dupes(picks):
        """Collapse same-system multi-strategy duplicates, keep highest score."""
        from collections import defaultdict as _dd

        buckets = _dd(list)
        for p in picks:
            key = (
                p.get("source_system", ""),
                _normalize_symbol(p.get("symbol", "")),
                (p.get("direction") or "").upper(),
                (p.get("timestamp") or "")[:16],
            )
            buckets[key].append(p)

        kept = []
        collapsed_count = 0
        for _key, group in buckets.items():
            if len(group) == 1:
                kept.append(group[0])
                continue
            # Sort by score descending, then by strategy name for determinism
            group.sort(
                key=lambda p: (
                    -(p.get("score") or p.get("elite_score") or 0),
                    p.get("strategy") or "",
                ),
            )
            winner = group[0]
            # Record which strategies were collapsed into this pick
            collapsed_strats = [p.get("strategy", "") for p in group[1:]]
            winner["_collapsed_strategies"] = collapsed_strats
            winner["_collapsed_count"] = len(collapsed_strats)
            kept.append(winner)
            collapsed_count += len(group) - 1
        return kept, collapsed_count

    active, intra_collapsed = _collapse_intra_system_dupes(active)
    closed, intra_collapsed_closed = _collapse_intra_system_dupes(closed)
    if intra_collapsed + intra_collapsed_closed:
        log.info(
            "  Intra-system dedup: removed %d duplicate picks (%d active, %d closed)",
            intra_collapsed + intra_collapsed_closed,
            intra_collapsed,
            intra_collapsed_closed,
        )

    # ── Pass 2b: collapse active picks that share (source_system, symbol, direction) ──
    # The previous pass only collapses when timestamps match within 1 minute.
    # But the same system can emit picks for the same symbol+direction via
    # different strategies at different times (e.g. super_signals fires
    # SHIBUSDT LONG from both "super_signal_(strong)_via_kimi" and
    # "super_consensus_(alpha_engine,_kimi,_ml_crypto_pred)" hours apart).
    # For active picks, keep only the highest-scored pick per system+symbol+direction.
    def _collapse_active_same_system_symbol(picks):
        """Remove same-system same-symbol-direction duplicates regardless of strategy/timestamp."""
        from collections import defaultdict as _dd_b

        buckets = _dd_b(list)
        for p in picks:
            key = (
                p.get("source_system", ""),
                _normalize_symbol(p.get("symbol", "")),
                (p.get("direction") or "").upper(),
            )
            buckets[key].append(p)

        kept = []
        collapsed_count = 0
        for _key, group in buckets.items():
            if len(group) == 1:
                kept.append(group[0])
                continue
            # Sort: highest score first, then most recent timestamp, then strategy name
            def _ts_sort_key(p):
                ts = p.get("timestamp") or p.get("created_at") or ""
                try:
                    from datetime import datetime
                    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                except Exception:
                    return 0

            group.sort(
                key=lambda p: (
                    -(p.get("score") or p.get("elite_score") or 0),
                    -_ts_sort_key(p),
                    p.get("strategy") or "",
                ),
            )
            winner = group[0]
            # Record collapsed strategies (merge with any already collapsed)
            prev_collapsed = winner.get("_collapsed_strategies", [])
            new_collapsed = [p.get("strategy", "") for p in group[1:]]
            winner["_collapsed_strategies"] = prev_collapsed + new_collapsed
            winner["_collapsed_count"] = len(winner["_collapsed_strategies"])
            kept.append(winner)
            collapsed_count += len(group) - 1
        return kept, collapsed_count

    active, same_sys_collapsed = _collapse_active_same_system_symbol(active)
    if same_sys_collapsed:
        log.info(
            "  Same-system symbol dedup: removed %d active picks (same source_system + symbol + direction, different strategy/timestamp)",
            same_sys_collapsed,
        )

    # ── Third-pass: tag cross-system (symbol, direction) duplicates ──
    # Cross-system duplicates are intentionally preserved for confluence/agreement
    # counting, but we tag all except the highest-scored per (symbol, direction)
    # with _dup_cross=True so the CSV export can optionally exclude them.
    # Virtual tiers like pm_high_conviction are NOT collapsed.
    def _tag_cross_system_dupes(picks):
        """Tag cross-system dupes: keep highest score per (symbol, direction)."""
        from collections import defaultdict as _dd2

        buckets = _dd2(list)
        for p in picks:
            key = (
                _normalize_symbol(p.get("symbol", "")),
                (p.get("direction") or "").upper(),
            )
            buckets[key].append(p)

        cross_tagged = 0
        for _key, group in buckets.items():
            if len(group) <= 1:
                for p in group:
                    p["_dup_cross"] = False
                continue
            group.sort(
                key=lambda p: (
                    -(p.get("score") or p.get("elite_score") or 0),
                    p.get("source_system") or "",
                ),
            )
            group[0]["_dup_cross"] = False
            for p in group[1:]:
                p["_dup_cross"] = True
                cross_tagged += 1
        return cross_tagged

    cross_tagged_active = _tag_cross_system_dupes(active)
    cross_tagged_closed = _tag_cross_system_dupes(closed)
    if cross_tagged_active + cross_tagged_closed:
        log.info(
            "  Cross-system dedup tags: %d active, %d closed picks marked as lower-priority cross-system duplicates",
            cross_tagged_active,
            cross_tagged_closed,
        )

    # ── Filter out resolved picks (TP/SL already hit) ──
    resolved_path = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
    resolved_ids = set()
    if resolved_path.exists():
        try:
            rdata = json.loads(resolved_path.read_text(encoding="utf-8", errors="replace"))
            rlist = rdata if isinstance(rdata, list) else rdata.get("resolved", [])
            for r in rlist:
                if isinstance(r, dict):
                    resolved_ids.add(_pick_identity_key(r))
            log.info(
                "  Loaded %d resolved pick IDs from universal_resolved_picks.json",
                len(resolved_ids),
            )
        except Exception as e:
            log.warning("  Failed to load resolved picks: %s", e)

    if resolved_ids:
        pre = len(active)
        active = [p for p in active if _pick_identity_key(p) not in resolved_ids]
        removed = pre - len(active)
        if removed:
            log.info("  Filtered out %d resolved picks (TP/SL already hit)", removed)

    # ── Quality gates: kill list + SHORT block (mirrors production_scanner) ──
    # Without this, the dashboard payload shows picks from killed strategies
    # and SHORTs (25% WR, -618% PnL) that production_scanner would block.
    try:
        wl_path = ROOT / "alpha_engine" / "data" / "core_whitelist.json"
        if wl_path.exists():
            wl_data = json.loads(wl_path.read_text(encoding="utf-8", errors="replace"))
            core_strats = {s.lower() for s in wl_data.get("core_strategies", [])}
            kill_set = set()
            for s in wl_data.get("kill_list", []):
                kill_set.add(s.lower())
                if "::" in s:
                    bare = s.split("::", 1)[1].lower()
                    if (
                        bare not in core_strats
                    ):  # Don't kill core strategies via namespace spill
                        kill_set.add(bare)
            pre = len(active)
            active = [
                p for p in active if p.get("strategy", "").lower() not in kill_set
            ]
            killed = pre - len(active)
            if killed:
                log.info(
                    "  Kill list gate: removed %d picks from %d killed strategies",
                    killed,
                    len(kill_set),
                )
        # SHORT penalty — don't blanket-block, but flag for reduced sizing.
        # Some ML 15m strategies have winning shorts. Blanket block removed
        # per user feedback — selective gating handled by production_scanner.
        short_count = sum(
            1 for p in active if p.get("direction", "").upper() in ("SHORT", "SELL")
        )
        if short_count:
            log.info(
                "  SHORT picks: %d (not blocked — selective gating in production_scanner)",
                short_count,
            )
    except Exception as e:
        log.warning("  Quality gates failed (non-fatal): %s", e)

    # ── Apply deferred stale penalty to picks whose score was set after tagging ──
    for p in active:
        if p.get("_stale") and p.get("_stale_penalty"):
            score = _float(p.get("score", 0))
            if score > 0:
                p["score"] = max(0, score - p["_stale_penalty"])

    # ── External source gate summary ──
    if _gate_killed or _gate_stale or _gate_low_rr:
        log.info(
            "[DASHBOARD GATE] Filtered %d killed, %d stale, %d low-R:R from external sources",
            _gate_killed,
            _gate_stale,
            _gate_low_rr,
        )

    if _ghost_skipped:
        log.info("Skipped %d ghost systems", _ghost_skipped)

    if _stale_skipped:
        log.warning(
            "[FRESHNESS] Skipped %d stale systems (hours old): %s",
            len(_stale_skipped),
            ", ".join(f"{k}={v}h" for k, v in sorted(_stale_skipped.items())),
        )

    # ── MySQL non-crypto closed picks ──
    # The local JSON files have sparse non-crypto closed data. Pull from MySQL
    # trading_picks table which has comprehensive equity/forex/commodity history.
    non_crypto_mysql_meta: dict = {
        "status": "pending",
        "fetched": 0,
        "appended": 0,
        "error": None,
    }
    try:
        from audit_trail.mysql_client import mysql_fetch_closed_non_crypto

        # Institutional-grade audit: expand history to 1 year and 5000 picks (TESTING_PROTOCOL v104)
        mysql_closed, fetch_meta = mysql_fetch_closed_non_crypto(max_age_days=365, limit=5000)
        non_crypto_mysql_meta["fetched"] = int(fetch_meta.get("fetched") or 0)
        non_crypto_mysql_meta["error"] = fetch_meta.get("error")
        if not fetch_meta.get("ok"):
            non_crypto_mysql_meta["status"] = "error"
        elif not mysql_closed:
            non_crypto_mysql_meta["status"] = "empty"
        else:
            # Deduplicate: skip if same symbol+direction+strategy already in closed
            existing_keys = set()
            for p in closed:
                _k = (p.get("symbol", ""), p.get("direction", ""), p.get("strategy", ""),
                       str(p.get("pnl_pct", "")))
                existing_keys.add(_k)
            added = 0
            for mp in mysql_closed:
                _k = (mp.get("symbol", ""), mp.get("direction", ""), mp.get("strategy", ""),
                       str(mp.get("pnl_pct", "")))
                if _k not in existing_keys:
                    existing_keys.add(_k)
                    closed.append(mp)
                    all_closed_including_expired.append(mp)
                    added += 1
            non_crypto_mysql_meta["appended"] = added
            non_crypto_mysql_meta["status"] = "ok"
            if added:
                log.info(
                    "MySQL: added %d non-crypto closed picks (deduped from %d)",
                    added,
                    len(mysql_closed),
                )
    except Exception as e:
        log.warning("MySQL non-crypto fetch skipped: %s", e)
        non_crypto_mysql_meta["status"] = "error"
        non_crypto_mysql_meta["error"] = str(e)[:500]

    # ── Active pick deduplication ──
    # Multiple sources emit the same (symbol, direction, strategy) — the
    # audit dashboard previously had 7 exact duplicates. Dedup by normalized
    # key, keeping the pick with the highest score (ties broken by latest
    # timestamp).
    if active:
        _seen_key: dict[tuple, dict] = {}
        for _p in active:
            _norm_sym = _normalize_symbol(str(_p.get("symbol") or ""))
            _dir = str(_p.get("direction") or "").upper().strip()
            _strat = str(_p.get("strategy") or "").strip()
            _key = (_norm_sym, _dir, _strat)
            if _key == ("", "", ""):
                continue  # malformed — leave in place, elsewhere handled
            _existing = _seen_key.get(_key)
            if _existing is None:
                _seen_key[_key] = _p
            else:
                _s_new = _float(_p.get("score", 0))
                _s_old = _float(_existing.get("score", 0))
                if _s_new > _s_old:
                    _seen_key[_key] = _p
                elif _s_new == _s_old:
                    # Prefer newest timestamp
                    _ts_new = str(_p.get("timestamp") or "")
                    _ts_old = str(_existing.get("timestamp") or "")
                    if _ts_new > _ts_old:
                        _seen_key[_key] = _p
        _deduped_active = list(_seen_key.values())
        _removed = len(active) - len(_deduped_active)
        if _removed > 0:
            log.info("Active pick dedup: removed %d exact duplicates (%d -> %d)",
                     _removed, len(active), len(_deduped_active))
        # Preserve any malformed picks that were skipped above
        _kept_malformed = [_p for _p in active
                           if (_normalize_symbol(str(_p.get("symbol") or "")),
                               str(_p.get("direction") or "").upper().strip(),
                               str(_p.get("strategy") or "").strip()) == ("", "", "")]
        active = _deduped_active + _kept_malformed

    return active, closed, all_closed_including_expired, active_raw_snapshot


def collect_portfolios():
    """Read all portfolio data sources."""
    portfolios = []

    # Paper trading portfolios (array format)
    data = _safe_json(ROOT / "paper_trading/data/portfolios.json")
    if data and isinstance(data, list):
        for p in data:
            portfolios.append(
                {
                    "name": p.get("name", "Unknown"),
                    "source": "paper_trading",
                    "type": p.get("type", ""),
                    "equity": _float(p.get("equity")),
                    "cash": _float(p.get("cash")),
                    "pnl_pct": _float(p.get("pnl_pct")),
                    "win_rate": _float(p.get("win_rate")),
                    "total_trades": p.get("total_trades", 0),
                    "positions": p.get("active_positions", 0),
                    "max_drawdown": _float(p.get("max_drawdown")),
                }
            )

    # Paper trading performance JSON
    perf = _safe_json(ROOT / "paper_trading/data/performance.json")
    if perf and perf.get("portfolios"):
        for p in perf["portfolios"]:
            # Only add if not already present by name
            names = {x["name"] for x in portfolios}
            if p.get("name") not in names:
                portfolios.append(
                    {
                        "name": p.get("name", ""),
                        "source": "paper_trading_perf",
                        "type": p.get("type", ""),
                        "equity": _float(p.get("equity")),
                        "cash": 0.0,
                        "pnl_pct": _float(p.get("pnl_pct")),
                        "win_rate": _float(p.get("win_rate")),
                        "total_trades": p.get("total_trades", 0),
                        "positions": 0,
                        "max_drawdown": _float(p.get("max_drawdown")),
                    }
                )

    # KIMI algorithm portfolios (object with algorithm keys)
    data = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/portfolio_state.json")
    if data and data.get("algorithms"):
        for name, algo in data["algorithms"].items():
            portfolios.append(
                {
                    "name": name,
                    "source": "kimi_algorithms",
                    "type": "algorithm",
                    "equity": _float(
                        algo.get("cash", algo.get("starting_value", 10000))
                    ),
                    "cash": _float(algo.get("cash", 0)),
                    "pnl_pct": 0.0,
                    "win_rate": 0.0,
                    "total_trades": len(algo.get("closed_positions", [])),
                    "positions": len(algo.get("positions", [])),
                    "max_drawdown": 0.0,
                }
            )

    # KIMI paper portfolio
    data = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/paper_portfolio.json")
    if data:
        portfolios.append(
            {
                "name": "KIMI Paper Portfolio",
                "source": "kimi_paper",
                "type": "paper",
                "equity": _float(data.get("starting_capital", 10000)),
                "cash": 0.0,
                "pnl_pct": 0.0,
                "win_rate": 0.0,
                "total_trades": len(data.get("closed_positions", [])),
                "positions": len(data.get("positions", [])),
                "max_drawdown": 0.0,
            }
        )

    # Paper trading SQLite
    rows = _safe_sqlite(
        ROOT / "paper_trading/data/paper.db",
        "SELECT name, portfolio_type, equity, cash, total_trades, wins, losses, "
        "max_drawdown_pct, starting_capital FROM portfolios",
    )
    existing_names = {p["name"] for p in portfolios}
    for r in rows:
        if r.get("name") not in existing_names:
            total_t = (r.get("wins", 0) or 0) + (r.get("losses", 0) or 0)
            wr = ((r.get("wins", 0) or 0) / total_t * 100) if total_t > 0 else 0
            starting = _float(r.get("starting_capital")) or 10000
            equity = _float(r.get("equity"))
            pnl = (
                ((equity - starting) / starting * 100)
                if starting > 0 and equity > 0
                else 0
            )
            portfolios.append(
                {
                    "name": r.get("name", ""),
                    "source": "paper_db",
                    "type": r.get("portfolio_type", ""),
                    "equity": equity,
                    "cash": _float(r.get("cash")),
                    "pnl_pct": round(pnl, 2),
                    "win_rate": round(wr, 1),
                    "total_trades": r.get("total_trades", 0) or 0,
                    "positions": 0,
                    "max_drawdown": _float(r.get("max_drawdown_pct")),
                }
            )

    log.info("Loaded %d portfolios", len(portfolios))
    return portfolios


DEAD_SYSTEM_DAYS = 30


def _compute_system_staleness(last_ts: str) -> tuple[bool, float | None]:
    """Return explicit stale metadata from a system last-signal timestamp.

    This function is observability-only and does not influence strategy gating.
    """
    if not last_ts:
        return (True, None)
    try:
        import re as _re
        from datetime import datetime as _dt, timezone as _tz
        ts_str = _re.sub(r"\s+[A-Z]{2,5}$", "", str(last_ts)).strip()
        ts_str = ts_str.replace("Z", "+00:00").replace(" ", "T")
        last_dt = _dt.fromisoformat(ts_str)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=_tz.utc)
        age_days = (_dt.now(_tz.utc) - last_dt).total_seconds() / 86400
        return (age_days > DEAD_SYSTEM_DAYS, round(age_days, 1))
    except (ValueError, TypeError, OverflowError):
        return (True, None)


def _compute_system_status(s: dict, total: int) -> str:
    """Classify system status with DEAD-via-staleness override.

    Per money-maker-ready skill rule: a system whose last_signal_at is
    >30 days old is DEAD regardless of whether it has resolved trades.
    Example: ml_crypto_pred_v12 has 123 resolved trades but last signal
    was 2026-02-22 (80 days ago) — it must not be advertised as 'monitoring'.
    """
    if s.get("active", 0) > 0:
        return "active"
    last_ts = s.get("last_ts")
    if last_ts:
        try:
            from datetime import datetime as _dt, timezone as _tz
            # Strip named TZ tokens (e.g. "EST") — fromisoformat rejects them
            import re as _re
            ts_str = _re.sub(r"\s+[A-Z]{2,5}$", "", str(last_ts)).strip()
            ts_str = ts_str.replace("Z", "+00:00").replace(" ", "T")
            last_dt = _dt.fromisoformat(ts_str)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=_tz.utc)
            age_days = (_dt.now(_tz.utc) - last_dt).total_seconds() / 86400
            if age_days > DEAD_SYSTEM_DAYS:
                return "dead"
        except (ValueError, TypeError):
            pass
    if total > 0:
        return "monitoring"
    if s.get("closed", 0) > 0:
        return "stale"
    return "empty"


def collect_system_stats(active, closed, all_closed=None):
    """Compute per-system stats from active picks, resolved closed picks, and shadow closed rows."""
    systems = {}
    sys_strategies = {}
    system_audits = {}

    def _ensure_buckets(pick):
        sys_name = pick["source_system"]
        if sys_name not in systems:
            systems[sys_name] = {
                "active": 0,
                "closed": 0,
                "wins": 0,
                "losses": 0,
                "zero_pnl": 0,
                "excluded_closed": 0,
                "total_pnl": 0.0,
                # 2026-05-12 P0-#3: capped_vs_raw_pnl_gap payload.
                # raw_total_pnl mirrors total_pnl but accumulates the
                # PRE-Layer-2 pnl (only pre-Layer-2; legacy ingest clamp
                # at +-500%/+-200% per pnl_ingest_sanity already applied).
                # Pre-MDD clamp pnl too.
                "raw_total_pnl": 0.0,
                "raw_pnl_series": [],
                "n_picks_clamped_l2": 0,
                "unrealized_pnl": 0.0,
                "win_pnl": 0.0,
                "loss_pnl": 0.0,
                "asset_classes": set(),
                "last_ts": "",
                "pnl_series": [],
                # Direction-based stats for F1 score
                "long_wins": 0,
                "long_losses": 0,
                "long_flat": 0,
                "short_wins": 0,
                "short_losses": 0,
                "short_flat": 0,
            }
        s = systems[sys_name]
        if sys_name not in sys_strategies:
            sys_strategies[sys_name] = {}
        s["asset_classes"].add(pick["asset_class"])
        ts = pick.get("timestamp", "")
        if ts:
            prev = s["last_ts"]
            da = _parse_pick_timestamp_utc(ts)
            db = _parse_pick_timestamp_utc(prev) if prev else None
            if not prev or db is None or (da is not None and da >= db):
                s["last_ts"] = ts
        # Strategy-level tracking
        strat_name = pick.get("strategy") or pick.get("signal_type") or "default"
        direction = pick.get("direction", "LONG")
        symbol = pick.get("symbol", "")
        if strat_name not in sys_strategies[sys_name]:
            sys_strategies[sys_name][strat_name] = {
                "active": 0,
                "wins": 0,
                "losses": 0,
                "flat": 0,
                "total_pnl": 0.0,
                "long_wins": 0,
                "long_losses": 0,
                "long_flat": 0,
                "short_wins": 0,
                "short_losses": 0,
                "short_flat": 0,
                "symbols": {},
                "last_ts": "",
                # Per-strategy realized-pnl series (percent units, capped at
                # ±500% by MAX_PNL above). Feeds the optional
                # STAT_RIGOR_ENABLED audit_metrics_block stamping in
                # _build_strategy_breakdown.
                "pnl_series": [],
            }
        strat = sys_strategies[sys_name][strat_name]
        if ts:
            pprev = strat["last_ts"]
            dsa = _parse_pick_timestamp_utc(ts)
            dsb = _parse_pick_timestamp_utc(pprev) if pprev else None
            if not pprev or dsb is None or (dsa is not None and dsa >= dsb):
                strat["last_ts"] = ts
        return sys_name, s, strat

    for pick in active:
        _, s, strat = _ensure_buckets(pick)
        if pick["status"] == "OPEN":
            s["active"] += 1
            strat["active"] += 1
            # Add unrealized PNL for active picks (cap outliers from bad entry prices)
            # Exclude suspicious-entry picks from portfolio PnL aggregation
            if not pick.get("_suspicious_entry"):
                unrealized = pick.get("unrealized_pnl_pct", pick.get("pnl_pct", 0))
                if abs(unrealized) > 500:
                    unrealized = 500.0 if unrealized > 0 else -500.0
                s["unrealized_pnl"] += unrealized
        if _is_verified_alpha_pick(pick):
            audit_meta = _extract_verified_alpha_audit(pick)
            if audit_meta:
                audit_bucket = system_audits.setdefault(
                    pick["source_system"],
                    {
                        "covered": 0,
                        "weighted_sum": 0.0,
                        "weighted_weight": 0.0,
                        "sample_sum": 0.0,
                    },
                )
                audit_bucket["covered"] += 1
                shrunk_wr = audit_meta.get("shrunk_wr_pct")
                if shrunk_wr is not None:
                    weight = max(
                        1.0, min(float(audit_meta.get("sample_size") or 0), 20.0)
                    )
                    audit_bucket["weighted_sum"] += float(shrunk_wr) * weight
                    audit_bucket["weighted_weight"] += weight
                audit_bucket["sample_sum"] += float(audit_meta.get("sample_size") or 0)

    for pick in closed:
        sys_name, s, strat = _ensure_buckets(pick)
        s["closed"] += 1
        if not _is_valid_resolved_pick(pick):
            s["excluded_closed"] += 1
            continue

        # ── Entry/exit price ratio sanity check ──
        # Catches decimal-scale corruption (e.g. WLDUSDT closed with
        # entry=66936.96, exit=0.2614 — off by ~256,000x). If the ratio
        # between entry and exit is absurdly large, the entry price was
        # almost certainly written from another symbol's scale. Exclude
        # from metrics rather than poisoning the system's total PnL.
        _entry_p = _float(pick.get("entry_price", 0))
        _exit_p = _float(pick.get("exit_price", 0))
        if _entry_p > 0 and _exit_p > 0:
            _ratio = _entry_p / _exit_p if _entry_p >= _exit_p else _exit_p / _entry_p
            if _ratio > 100.0:
                pick["_entry_corrupt"] = True
                pick["_entry_corrupt_reason"] = (
                    f"entry/exit ratio {_ratio:.0f}x (entry={_entry_p}, "
                    f"exit={_exit_p}) — likely decimal-scale corruption"
                )
                log.warning(
                    "Corrupt entry price detected: %s system=%s entry=%.6f "
                    "exit=%.6f ratio=%.0fx — excluded from metrics",
                    pick.get("symbol"),
                    sys_name,
                    _entry_p,
                    _exit_p,
                    _ratio,
                )
                s["excluded_closed"] += 1
                continue

        pnl = pick.get("pnl_pct", 0)
        # Guard: cap per-pick PnL at ±500% — anything beyond is almost
        # certainly a bad entry price (e.g. APT at $0.000131 instead of $9.58).
        # Log and clamp rather than discard so the trade still counts in W/L.
        MAX_PNL = 500.0
        # 2026-05-12 P0-#3: record the pre-Layer-2 value for raw aggregation
        # so the dashboard can surface capped_vs_raw_pnl_gap.
        raw_pnl_pre_l2 = float(pnl or 0)
        s["raw_total_pnl"] += raw_pnl_pre_l2
        s["raw_pnl_series"].append(raw_pnl_pre_l2)
        if abs(pnl) > MAX_PNL:
            log.warning(
                f"Outlier PnL capped: {pick.get('symbol')} {pnl:.1f}% -> "
                f"{MAX_PNL if pnl > 0 else -MAX_PNL:.1f}% "
                f"(entry={pick.get('entry_price')}, system={sys_name})"
            )
            pnl = MAX_PNL if pnl > 0 else -MAX_PNL
            s["n_picks_clamped_l2"] += 1
        s["total_pnl"] += pnl
        s["pnl_series"].append(pnl)
        strat["total_pnl"] += pnl
        strat["pnl_series"].append(pnl)
        symbol = pick.get("symbol", "")
        if symbol not in strat["symbols"]:
            strat["symbols"][symbol] = {"wins": 0, "losses": 0, "flat": 0, "pnl": 0.0}
        strat["symbols"][symbol]["pnl"] += pnl
        direction = pick.get("direction", "LONG")
        outcome_bucket = _outcome_bucket_from_pnl(pnl)
        if outcome_bucket == "win":
            s["wins"] += 1
            strat["wins"] += 1
            strat["symbols"][symbol]["wins"] += 1
            s["win_pnl"] += pnl
            if direction == "SHORT":
                s["short_wins"] += 1
                strat["short_wins"] += 1
            else:
                s["long_wins"] += 1
                strat["long_wins"] += 1
        elif outcome_bucket == "loss":
            s["losses"] += 1
            strat["losses"] += 1
            strat["symbols"][symbol]["losses"] += 1
            s["loss_pnl"] += pnl
            if direction == "SHORT":
                s["short_losses"] += 1
                strat["short_losses"] += 1
            else:
                s["long_losses"] += 1
                strat["long_losses"] += 1
        else:
            s["zero_pnl"] += 1
            strat["flat"] += 1
            strat["symbols"][symbol]["flat"] += 1
            if direction == "SHORT":
                s["short_flat"] += 1
                strat["short_flat"] += 1
            else:
                s["long_flat"] += 1
                strat["long_flat"] += 1

    if all_closed:
        for pick in all_closed:
            if not isinstance(pick, dict) or _is_valid_resolved_pick(pick):
                continue
            _, s, _ = _ensure_buckets(pick)
            s["closed"] += 1
            s["excluded_closed"] += 1

    # Ensure all registered JSON_PICK_SOURCES appear even with 0 picks
    # (skip hidden/inactive/ghost systems)
    for sys_name, _, _ in JSON_PICK_SOURCES:
        if sys_name in _HIDDEN_SYSTEMS:
            continue
        if sys_name in _GHOST_SYSTEMS:
            continue
        if sys_name not in systems:
            systems[sys_name] = {
                "active": 0,
                "closed": 0,
                "wins": 0,
                "losses": 0,
                "zero_pnl": 0,
                "excluded_closed": 0,
                "total_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "win_pnl": 0.0,
                "loss_pnl": 0.0,
                "asset_classes": {"CRYPTO"},
                "last_ts": "",
                "pnl_series": [],
                "long_wins": 0,
                "long_losses": 0,
                "long_flat": 0,
                "short_wins": 0,
                "short_losses": 0,
                "short_flat": 0,
            }

    # M-033: Load permanently-killed strategies so their source systems
    # are marked stale/blocked in the dashboard (fail-open).
    try:
        from audit_trail.quality_gates import PERMANENTLY_KILLED_STRATEGIES as _PKS
        _permanently_killed_lower = {str(s).lower() for s in _PKS}
    except Exception:
        _permanently_killed_lower = set()

    result = []
    for name, s in sorted(systems.items()):
        if name in _HIDDEN_SYSTEMS:
            continue
        if name in _GHOST_SYSTEMS:
            continue
        total = s["wins"] + s["losses"] + s["zero_pnl"]
        wr = _calculate_win_rate_pct(s["wins"], s["losses"], s["zero_pnl"])
        avg_pnl = (s["total_pnl"] / total) if total > 0 else 0
        avg_win = round(s["win_pnl"] / s["wins"], 2) if s["wins"] > 0 else 0
        avg_loss = round(abs(s["loss_pnl"]) / s["losses"], 2) if s["losses"] > 0 else 0
        pf = round(s["win_pnl"] / abs(s["loss_pnl"]), 2) if s["loss_pnl"] < 0 else None
        expectancy = _calculate_expectancy_pct(
            s["total_pnl"], s["wins"], s["losses"], s["zero_pnl"]
        )
        # Common Sense Ratio: (WR × AvgWin) / (LR × AvgLoss) — >1 profitable, >2 strong, >3 excellent
        csr = None
        if total >= 5 and s["wins"] > 0 and s["losses"] > 0 and avg_loss > 0:
            csr = round((wr / 100 * avg_win) / ((1 - wr / 100) * avg_loss), 2)
        # Max drawdown from cumulative PnL series
        # 2026-05-11 SUPREME EDGE P0 #7: clamp each pnl element to [-100, 200]%
        # on READ before cumulating. PR #876 added the writer-side clamp in
        # mysql_sync 2026-05-09 but legacy rows pre-clamp can still emit
        # -106,700% (FOREX unit corruption) which compounds into a 680% MDD
        # per Kimi audit. Read-side clamp defends downstream metrics
        # (Calmar, Recovery Factor) from any remaining poisoned rows.
        max_dd = 0.0
        if s["pnl_series"]:
            cum = 0.0
            peak = 0.0
            for p in s["pnl_series"]:
                # Clamp matches PR #876 [-100, 200] writer-side bounds
                p_clamped = max(-100.0, min(200.0, float(p))) if p is not None else 0.0
                cum += p_clamped
                if cum > peak:
                    peak = cum
                dd = peak - cum
                if dd > max_dd:
                    max_dd = dd

        # ── Calmar Ratio: annualized return / max drawdown ──
        # Approximate CAGR from total PnL and number of closed trades
        # Assume ~1 trade/day on average for annualization
        calmar = None
        if max_dd > 0 and s["closed"] > 0 and s["total_pnl"] != 0:
            # Annualize: assume each trade ≈ 1 day, so closed trades ≈ trading days
            trading_days = max(s["closed"], 1)
            annualized_return = (s["total_pnl"] / trading_days) * 252
            calmar = round(annualized_return / max_dd, 2)

        # ── Recovery Factor: net profit / max drawdown ──
        recovery_factor = None
        if max_dd > 0 and s["total_pnl"] > 0:
            recovery_factor = round(s["total_pnl"] / max_dd, 2)

        # ── F1 Score for BUY (LONG) and SELL (SHORT) signal classification ──
        # For LONG signals: precision = long_wins / (long_wins + long_losses)
        #                   recall = long_wins / (long_wins + short_losses)  [true positives among all actual ups]
        # Simplified: treat each direction independently as a binary classifier
        # Precision = wins / total_signals_in_direction, Recall = wins / all_wins
        buy_f1 = None
        sell_f1 = None
        lw, ll = s["long_wins"], s["long_losses"]
        sw, sl = s["short_wins"], s["short_losses"]
        total_wins = s["wins"]
        if lw + ll > 0 and total_wins > 0:
            buy_precision = lw / (lw + ll)
            buy_recall = lw / total_wins if total_wins > 0 else 0
            if buy_precision + buy_recall > 0:
                buy_f1 = round(
                    2 * (buy_precision * buy_recall) / (buy_precision + buy_recall), 3
                )
        if sw + sl > 0 and total_wins > 0:
            sell_precision = sw / (sw + sl)
            sell_recall = sw / total_wins if total_wins > 0 else 0
            if sell_precision + sell_recall > 0:
                sell_f1 = round(
                    2 * (sell_precision * sell_recall) / (sell_precision + sell_recall),
                    3,
                )

        # ── Toxic symbol concentration flag ──
        # Flags systems where a single symbol dominates total PnL (>70% share).
        # Example: ml_crypto_predictor has 93% TRXUSDT concentration producing
        # −15,238% total PnL — the headline number is meaningless without
        # surfacing the concentration.
        _toxic_concentration = None
        _toxic_symbol = None
        _toxic_share_pct = None
        if sys_strategies.get(name) and abs(s["total_pnl"]) > 50.0:
            _sym_pnl: dict = {}
            for _strat_obj in sys_strategies[name].values():
                for _sym, _sstats in _strat_obj.get("symbols", {}).items():
                    _sym_pnl[_sym] = _sym_pnl.get(_sym, 0.0) + _sstats.get("pnl", 0.0)
            if _sym_pnl:
                _top_sym, _top_pnl = max(_sym_pnl.items(), key=lambda kv: abs(kv[1]))
                _denom = sum(abs(v) for v in _sym_pnl.values())
                if _denom > 0:
                    _share = abs(_top_pnl) / _denom
                    if _share >= 0.70:
                        _toxic_concentration = True
                        _toxic_symbol = _top_sym
                        _toxic_share_pct = round(_share * 100, 1)

        # 2026-05-12 P0-#3 disclosure: capped_vs_raw_pnl_gap surfaces the
        # delta between pre-Layer-2 and post-Layer-2 aggregates. >0 means
        # the cap is doing real work on this system; reviewers should pull
        # the underlying picks to confirm the cap is legitimate (data
        # corruption) and not silently clipping real edge.
        _raw_pnl = float(s.get("raw_total_pnl", 0.0))
        _capped_pnl = float(s["total_pnl"])
        _cap_gap_pct = round(_raw_pnl - _capped_pnl, 2)
        _cap_gap_share = round(
            abs(_cap_gap_pct) / abs(_capped_pnl) * 100 if abs(_capped_pnl) > 0.01 else 0, 2
        )
        _capped_vs_raw_pnl_gap = {
            "raw_total_pnl_pct": round(_raw_pnl, 2),
            "capped_total_pnl_pct": round(_capped_pnl, 2),
            "gap_pct": _cap_gap_pct,
            "gap_share_pct": _cap_gap_share,
            "n_picks_clamped_l2": int(s.get("n_picks_clamped_l2", 0)),
            "cap_value_pct": 500.0,  # Layer-2 constant — see pnl_cap_thresholds_audit
        }
        _is_stale, _stale_days = _compute_system_staleness(s["last_ts"])
        # M-033: If this system's name matches a PERMANENTLY_KILLED_STRATEGIES entry,
        # it is a blocked aggregator. Override staleness + active_picks so the dashboard
        # does not falsely show it as healthy when its source strategy is killed.
        _is_blocked_aggregator = name.lower() in _permanently_killed_lower
        if _is_blocked_aggregator:
            _is_stale = True
            _stale_days = _stale_days if _stale_days else 0
            s["last_ts"] = None  # No valid signal from a killed system
        result.append(
            {
                "name": name,
                "active_picks": 0 if _is_blocked_aggregator else s["active"],
                "closed_picks": s["closed"],
                "resolved_picks": total,
                "capped_vs_raw_pnl_gap": _capped_vs_raw_pnl_gap,
                "zero_pnl": s["zero_pnl"],
                "flat_picks": s["zero_pnl"],
                "excluded_closed": s["excluded_closed"],
                "toxic_concentration": _toxic_concentration,
                "toxic_symbol": _toxic_symbol,
                "toxic_share_pct": _toxic_share_pct,
                "wins": s["wins"],
                "losses": s["losses"],
                "win_rate": round(wr, 1),
                "avg_pnl_pct": round(avg_pnl, 2),
                "total_pnl_pct": round(s["total_pnl"], 2),
                "unrealized_pnl_pct": round(s["unrealized_pnl"], 2),
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "gross_win": round(s["win_pnl"], 2),
                "gross_loss": round(s["loss_pnl"], 2),
                "profit_factor": pf,
                "expectancy": expectancy,
                "common_sense_ratio": csr,
                "max_drawdown": round(max_dd, 2),
                "calmar_ratio": calmar,
                "recovery_factor": recovery_factor,
                "buy_f1": buy_f1,
                "sell_f1": sell_f1,
                "asset_classes": sorted(s["asset_classes"]),
                "last_signal_at": s["last_ts"],
                "last_signal_date": (s["last_ts"] or "")[:10] or None,  # M-030: plain YYYY-MM-DD for UI staleness badge
                "is_stale": _is_stale,
                "is_blocked_aggregator": _is_blocked_aggregator,
                "stale_days": _stale_days,
                "status": "BLOCKED" if _is_blocked_aggregator else _compute_system_status(s, total),
                "audited_wr_pct": (
                    round(
                        system_audits[name]["weighted_sum"]
                        / system_audits[name]["weighted_weight"],
                        1,
                    )
                    if name in system_audits
                    and system_audits[name]["weighted_weight"] > 0
                    else None
                ),
                "audited_wr_coverage": (
                    int(system_audits[name]["covered"]) if name in system_audits else 0
                ),
                "audited_avg_sample_size": (
                    round(
                        system_audits[name]["sample_sum"]
                        / system_audits[name]["covered"],
                        1,
                    )
                    if name in system_audits and system_audits[name]["covered"] > 0
                    else None
                ),
                "win_rate_basis": (
                    "realized"
                    if total > 0
                    else "audited"
                    if name in system_audits
                    and system_audits[name]["weighted_weight"] > 0
                    else "none"
                ),
                "display_win_rate_pct": (
                    round(wr, 1)
                    if total > 0
                    else round(
                        system_audits[name]["weighted_sum"]
                        / system_audits[name]["weighted_weight"],
                        1,
                    )
                    if name in system_audits
                    and system_audits[name]["weighted_weight"] > 0
                    else None
                ),
                # Per-strategy breakdown within this system
                "strategies": _build_strategy_breakdown(sys_strategies.get(name, {})),
            }
        )
    return result


# ── M-012: DSR audit lookup (anti_overfit_audit.json → per-strategy DSR) ──
# Loaded once, keyed by strategy name. Fail-open: {} when file missing.
_DSR_AUDIT_CACHE: dict | None = None


def _load_dsr_audit() -> dict:
    """Load anti_overfit_audit.json and return {strategy_name: {dsr, verdict}}."""
    global _DSR_AUDIT_CACHE
    if _DSR_AUDIT_CACHE is not None:
        return _DSR_AUDIT_CACHE
    try:
        path = ROOT / "audit_dashboard" / "data" / "anti_overfit_audit.json"
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            _DSR_AUDIT_CACHE = {
                s["strategy"]: {"dsr_score": s.get("dsr"), "dsr_verdict": s.get("verdict")}
                for s in raw.get("strategies", [])
                if "strategy" in s
            }
        else:
            _DSR_AUDIT_CACHE = {}
    except Exception as _e:
        log.warning("M-012: failed to load anti_overfit_audit.json: %s", _e)
        _DSR_AUDIT_CACHE = {}
    return _DSR_AUDIT_CACHE


def _build_strategy_breakdown(strat_dict):
    """Build per-strategy stats list from raw strategy dict.

    Optional STAT_RIGOR_ENABLED=1 stamps a `_stat_rigor_block` field per
    strategy with bootstrap-CI'd PF / WR / Sharpe + PSR-vs-zero (see
    alpha_engine.statistical_rigor.audit_metrics_block). Default-OFF;
    intended for a 14-day shadow before promotion to a default-on field.
    """
    _stat_rigor_on = (
        _STAT_RIGOR_AVAILABLE
        and os.environ.get("STAT_RIGOR_ENABLED", "0") == "1"
    )
    result = []
    for strat_name, sd in sorted(strat_dict.items()):
        resolved = sd["wins"] + sd["losses"] + sd["flat"]
        if resolved == 0 and sd["active"] == 0:
            continue
        wr = _calculate_win_rate_pct(sd["wins"], sd["losses"], sd["flat"])
        avg_pnl = round(sd["total_pnl"] / resolved, 2) if resolved > 0 else 0
        long_total = sd["long_wins"] + sd["long_losses"] + sd["long_flat"]
        short_total = sd["short_wins"] + sd["short_losses"] + sd["short_flat"]
        long_wr = (
            round(sd["long_wins"] / long_total * 100, 1) if long_total > 0 else None
        )
        short_wr = (
            round(sd["short_wins"] / short_total * 100, 1) if short_total > 0 else None
        )
        # Top symbols by trade count (max 5)
        top_symbols = sorted(
            sd["symbols"].items(),
            key=lambda x: x[1]["wins"] + x[1]["losses"] + x[1]["flat"],
            reverse=True,
        )[:5]
        top_syms = []
        for sym, sym_stats in top_symbols:
            sym_res = sym_stats["wins"] + sym_stats["losses"] + sym_stats["flat"]
            top_syms.append(
                {
                    "symbol": sym,
                    "wins": sym_stats["wins"],
                    "losses": sym_stats["losses"],
                    "flat": sym_stats["flat"],
                    "wr": round(sym_stats["wins"] / sym_res * 100, 1)
                    if sym_res > 0
                    else 0,
                    "pnl": round(sym_stats["pnl"], 2),
                }
            )
        row = {
            "name": strat_name,
            "active": sd["active"],
            "resolved": resolved,
            "wins": sd["wins"],
            "losses": sd["losses"],
            "flat": sd["flat"],
            "win_rate": wr,
            "avg_pnl": avg_pnl,
            "total_pnl": round(sd["total_pnl"], 2),
            "long_wins": sd["long_wins"],
            "long_losses": sd["long_losses"],
            "long_wr": long_wr,
            "short_wins": sd["short_wins"],
            "short_losses": sd["short_losses"],
            "short_wr": short_wr,
            "last_signal_at": sd["last_ts"],
            "top_symbols": top_syms,
        }
        # Phase 2 wire-in: STAT_RIGOR_ENABLED=1 stamps bootstrap-CI'd
        # PF / WR / Sharpe + PSR-vs-zero per strategy. Default-OFF
        # (14-day shadow). Skipped for n<4 (audit_metrics_block degenerates).
        # pnl_pct is percent-typed; convert to fractional (÷100) before passing
        # in. n_resamples=200 keeps dashboard generation under perf budget.
        if _stat_rigor_on:
            _series_pct = sd.get("pnl_series") or []
            if len(_series_pct) >= 4:
                try:
                    _series = [float(p) / 100.0 for p in _series_pct]
                    row["_stat_rigor_block"] = _audit_metrics_block(
                        _series, n_resamples=200, seed=42
                    )
                except Exception as _e:
                    # Never let a metrics computation break the dashboard, but
                    # surface the failure — silent except: pass made bugs
                    # invisible (DeepSeek + Grok external review, 2026-05-02).
                    log.warning(
                        "stat_rigor_block computation failed for strategy=%s n=%d: %s",
                        strat_name, len(_series_pct), _e,
                    )
        # ── M-012: Stamp DSR score + verdict from anti_overfit_audit.json ──
        # Enables HC filter DSR gate (hc_filter.js extracts p.dsr_score /
        # p.dsr_verdict). Fail-open: fields are null when audit data is absent.
        _dsr_entry = _load_dsr_audit().get(strat_name, {})
        row["dsr_score"] = _dsr_entry.get("dsr_score")
        row["dsr_verdict"] = _dsr_entry.get("dsr_verdict")
        result.append(row)
    result.sort(key=lambda x: x["resolved"], reverse=True)
    return result


def collect_audit_events(limit=50):
    """Read recent audit events from multiple sources."""
    events = []

    # Source 1: audit_trail.db
    db_events = _safe_sqlite(
        ROOT / "data" / "audit_trail.db",
        "SELECT event_type, pick_id, symbol, payload, origin, timestamp "
        "FROM audit_events ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )
    events.extend(db_events)

    # Source 2: KIMI audit_log.json (most recent entries)
    kimi_log = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/audit_log.json")
    if kimi_log and isinstance(kimi_log, list):
        for entry in kimi_log[-limit:]:
            events.append(
                {
                    "event_type": f"KIMI_{entry.get('tier', 'SIGNAL')}",
                    "pick_id": None,
                    "symbol": entry.get("symbol", ""),
                    "payload": json.dumps(
                        {
                            "algorithm": entry.get("algorithm", ""),
                            "strategy": entry.get("strategy", ""),
                            "signal": entry.get("signal", ""),
                            "reason": entry.get("reason", ""),
                        }
                    ),
                    "origin": "kimi_riseoftheclaw",
                    "timestamp": entry.get("timestamp", ""),
                }
            )

    # Source 3: crypto_signal_engine audit
    cse = _safe_json(ROOT / "crypto_signal_engine/data/audit.json")
    if cse and cse.get("new_picks"):
        for pick in cse["new_picks"][-20:]:
            events.append(
                {
                    "event_type": "CSE_NEW_PICK",
                    "pick_id": None,
                    "symbol": pick.get("symbol", ""),
                    "payload": json.dumps(
                        {
                            "strategy": pick.get("strategy", ""),
                            "direction": pick.get("direction", ""),
                        }
                    ),
                    "origin": "crypto_signal_engine",
                    "timestamp": cse.get("timestamp_utc", ""),
                }
            )

    # Sort all events by timestamp desc, return top N
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return events[:limit]


def collect_filter_log(limit=50):
    """Read recent filter log entries."""
    return _safe_sqlite(
        ROOT / "data" / "audit_trail.db",
        "SELECT filter_reason, symbol, direction, source_system, details, timestamp "
        "FROM filter_log ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )


def collect_backtest_vs_forward():
    """Compare backtest vs forward win rates.

    Uses multiple data sources:
    1. baby_strats_dashboard.json (baby strat BT + FWD)
    2. survivor_backtest_results.json (alpha engine BT results)
    3. Baby strat meta.json files (forward metrics per strategy)
    4. audit_trail.db tables (strategy_stats + bt_backtest_runs)
    5. Coinglass signal DB (coinglass strategy performance)
    """
    results = []
    seen = set()

    # ── Source 1: Baby strats dashboard ──
    bsd = _safe_json(ROOT / "battleground/data/baby_strats_dashboard.json")
    if bsd:
        for strat in bsd.get("strategies", []):
            name = strat.get("name", "")
            if not name:
                continue
            bt = strat.get("backtest_metrics", strat.get("backtest", {})) or {}
            ft = strat.get("forward_trades", []) or []
            bt_trades = bt.get("total_trades", 0) or 0
            bt_wr_raw = bt.get("win_rate", 0) or 0
            # win_rate may be 0-100 or 0-1 — normalize to 0-100
            if bt_wr_raw > 0 and bt_wr_raw <= 1:
                bt_wr_raw = bt_wr_raw * 100
            bt_wr = round(bt_wr_raw, 1) if bt_trades > 0 else None

            fwd_wins = sum(1 for t in ft if _float(t.get("pnl_pct", 0)) > 0)
            fwd_losses = sum(1 for t in ft if _float(t.get("pnl_pct", 0)) < 0)
            fwd_total = fwd_wins + fwd_losses
            fwd_wr = round(fwd_wins / fwd_total * 100, 1) if fwd_total > 0 else None

            if bt_wr is None and fwd_wr is None:
                continue
            decay = (
                round(fwd_wr - bt_wr, 1)
                if (fwd_wr is not None and bt_wr is not None)
                else None
            )
            results.append(
                {
                    "strategy": name,
                    "system": "baby_strats",
                    "bt_wr": bt_wr,
                    "fwd_wr": fwd_wr,
                    "decay": decay,
                    "bt_trades": bt_trades,
                    "fwd_trades": len(ft),
                }
            )
            seen.add(name)

    # ── Source 2: Survivor backtest results (alpha engine) ──
    survivor = _safe_json(ROOT / "alpha_engine/data/survivor_backtest_results.json")
    if survivor and survivor.get("results"):
        for name, r in survivor["results"].items():
            if name in seen:
                continue
            bt_wr = r.get("win_rate_pct")
            bt_trades = r.get("total_trades", 0)
            if bt_wr is None and bt_trades == 0:
                continue
            results.append(
                {
                    "strategy": name,
                    "system": "alpha_engine",
                    "bt_wr": round(bt_wr, 1) if bt_wr is not None else None,
                    "fwd_wr": None,
                    "decay": None,
                    "bt_trades": bt_trades,
                    "fwd_trades": 0,
                    "bt_sharpe": _cap_sharpe(r.get("sharpe")),
                    "bt_verdict": r.get("verdict", ""),
                }
            )
            seen.add(name)

    # ── Source 3: Baby strat meta.json files (forward testing metrics) ──
    for meta_path in sorted(
        glob.glob(str(ROOT / "incubator/agents/**/*.py.meta.json"), recursive=True)
    ):
        try:
            meta = json.loads(Path(meta_path).read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        name = meta.get("strategy_name", "")
        if not name or name in seen:
            continue
        fm = meta.get("forward_metrics", {})
        total_fwd = fm.get("total_trades") or 0
        fwd_wr_raw = fm.get("win_rate")
        fwd_wr = (
            round(fwd_wr_raw * 100, 1)
            if fwd_wr_raw is not None and total_fwd > 0
            else None
        )
        if fwd_wr is None and total_fwd == 0:
            continue
        # Check if survivor BT data exists for this strategy
        existing = next((r for r in results if r["strategy"] == name), None)
        if existing:
            existing["fwd_wr"] = fwd_wr
            existing["fwd_trades"] = total_fwd
            if existing["bt_wr"] is not None and fwd_wr is not None:
                existing["decay"] = round(fwd_wr - existing["bt_wr"], 1)
            seen.add(name)
            continue
        results.append(
            {
                "strategy": name,
                "system": meta.get("agent_id", "incubator"),
                "bt_wr": None,
                "fwd_wr": fwd_wr,
                "decay": None,
                "bt_trades": 0,
                "fwd_trades": total_fwd,
            }
        )
        seen.add(name)

    # ── Source 4: Audit DB tables (if they exist) ──
    db = ROOT / "data" / "audit_trail.db"
    fwd = _safe_sqlite(
        db,
        """
        SELECT strategy, source_system, total_picks, wins, losses, win_rate, avg_pnl_pct
        FROM strategy_stats WHERE total_picks >= 3
    """,
    )
    bt = _safe_sqlite(
        db,
        """
        SELECT strategy, total_trades, wins, losses, win_rate, total_return, sharpe
        FROM bt_backtest_runs WHERE total_trades >= 5
    """,
    )
    fwd_map = {r["strategy"]: r for r in fwd}
    bt_map = {r["strategy"]: r for r in bt}
    for strat in sorted(set(list(fwd_map.keys()) + list(bt_map.keys()))):
        if strat in seen:
            continue
        f = fwd_map.get(strat, {})
        b = bt_map.get(strat, {})
        fwd_wr = _float(f.get("win_rate")) if f else None
        bt_wr_raw = _float(b.get("win_rate")) if b else None
        bt_wr = (
            (bt_wr_raw * 100 if bt_wr_raw and bt_wr_raw <= 1.0 else bt_wr_raw)
            if bt_wr_raw
            else None
        )
        decay = (
            round(fwd_wr - bt_wr, 1)
            if (fwd_wr is not None and bt_wr is not None)
            else None
        )
        results.append(
            {
                "strategy": strat,
                "system": f.get("source_system", ""),
                "bt_wr": round(bt_wr, 1) if bt_wr is not None else None,
                "fwd_wr": round(fwd_wr, 1) if fwd_wr is not None else None,
                "decay": decay,
                "bt_trades": b.get("total_trades", 0) if b else 0,
                "fwd_trades": f.get("total_picks", 0) if f else 0,
            }
        )
        seen.add(strat)

    # ── Source 5: Coinglass signal DB ──
    cg_db = ROOT / "coinglass_strategies" / "data" / "coinglass.db"
    if cg_db.exists():
        try:
            # Try closed positions first (positions table has pnl_pct)
            cg_signals = _safe_sqlite(
                cg_db,
                """
                SELECT s.strategy, COUNT(p.id) as total,
                       SUM(CASE WHEN p.pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN p.pnl_pct <= 0 THEN 1 ELSE 0 END) as losses
                FROM positions p
                JOIN signals s ON p.signal_id = s.signal_id
                WHERE p.status = 'CLOSED'
                GROUP BY s.strategy HAVING total >= 3
            """,
            )
            for r in cg_signals:
                name = r.get("strategy", "")
                if not name or name in seen:
                    continue
                total = r.get("wins", 0) + r.get("losses", 0)
                fwd_wr = round(r["wins"] / total * 100, 1) if total > 0 else None
                results.append(
                    {
                        "strategy": name,
                        "system": "coinglass",
                        "bt_wr": None,
                        "fwd_wr": fwd_wr,
                        "decay": None,
                        "bt_trades": 0,
                        "fwd_trades": total,
                    }
                )
                seen.add(name)

            # Fallback: show strategies with signals but no closed positions yet
            cg_signal_counts = _safe_sqlite(
                cg_db,
                """
                SELECT strategy, COUNT(*) as signal_count
                FROM signals GROUP BY strategy
            """,
            )
            for r in cg_signal_counts:
                name = r.get("strategy", "")
                if not name or name in seen:
                    continue
                results.append(
                    {
                        "strategy": name,
                        "system": "coinglass",
                        "bt_wr": None,
                        "fwd_wr": None,
                        "decay": None,
                        "bt_trades": 0,
                        "fwd_trades": 0,
                        "fwd_signals": r.get("signal_count", 0),
                        "note": "No closed positions yet",
                    }
                )
                seen.add(name)
        except Exception as e:
            log.warning("Coinglass DB query failed: %s", e)

    # ── Source 6: KIMI competition algorithms (91 algos with forward trading data) ──
    kimi_comp = _safe_json(ROOT / "riseoftheclaw/data/live_competition.json")
    if kimi_comp:
        algos = kimi_comp.get("algorithms", [])
        if isinstance(algos, dict):
            algos = list(algos.values())
        kimi_bt_count = 0
        for algo in algos:
            if not isinstance(algo, dict):
                continue
            name = algo.get("id", algo.get("name", ""))
            if not name or name in seen:
                continue
            cp = algo.get("closedPicks", algo.get("closedTrades", []))
            ap = algo.get("activePicks", [])
            if not cp and not ap:
                continue
            wins = sum(
                1 for t in cp if _float(t.get("pnlPct", t.get("pnl_pct", 0))) > 0
            )
            losses = sum(
                1 for t in cp if _float(t.get("pnlPct", t.get("pnl_pct", 0))) < 0
            )
            total = wins + losses
            fwd_wr = round(wins / total * 100, 1) if total > 0 else None
            results.append(
                {
                    "strategy": name,
                    "system": "kimi_competition",
                    "bt_wr": None,
                    "fwd_wr": fwd_wr,
                    "decay": None,
                    "bt_trades": 0,
                    "fwd_trades": total,
                    "active_picks": len(ap),
                    "drought_scans": algo.get("droughtScans", 0),
                }
            )
            seen.add(name)
            kimi_bt_count += 1
        if kimi_bt_count:
            log.info("  KIMI competition algorithms BT vs FWD: %d", kimi_bt_count)

    # ── Source 7: Backtest rankings from backtest_engine ──
    bt_rankings = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/backtest_rankings.json")
    if bt_rankings:
        rankings_list = (
            bt_rankings
            if isinstance(bt_rankings, list)
            else bt_rankings.get("rankings", bt_rankings.get("results", []))
        )
        for r in rankings_list:
            if not isinstance(r, dict):
                continue
            name = r.get("strategy_id", r.get("id", r.get("name", "")))
            if not name or name in seen:
                continue
            bt_wr = r.get("win_rate") or r.get("win_rate_pct")
            bt_trades = r.get("total_trades", 0) or r.get("trades", 0)
            bt_sharpe = _cap_sharpe(r.get("sharpe"))
            tier = r.get("tier", r.get("status", ""))
            results.append(
                {
                    "strategy": name,
                    "system": "backtest_arena",
                    "bt_wr": round(bt_wr, 1) if bt_wr is not None else None,
                    "fwd_wr": None,
                    "decay": None,
                    "bt_trades": bt_trades,
                    "fwd_trades": 0,
                    "bt_sharpe": bt_sharpe,
                    "tier": tier,
                    "eliminated": str(tier).upper() == "ELIMINATED",
                }
            )
            seen.add(name)

    log.info(
        "BT vs Forward: %d strategies from %d sources",
        len(results),
        len(set(r.get("system", "") for r in results)),
    )
    return results


def _compute_fwd_vs_bt_divergence(bt_vs_fwd_rows: list, limit: int = 12) -> dict:
    """F8 Forward-vs-Backtest divergence card (top-7 swarm #6 2026-05-08).

    Statistical-rigor companion to ``_compute_hf_decay_watchlist``:
      - WR z-score using sqrt(p*(1-p)/n) std-error on backtest rate
      - PF ratio fwd_pf / bt_pf
      - Severity = max(|wr_z|, 1.0 - pf_ratio); higher = more divergent

    Flags any row where wr_z <= -2.0 OR pf_ratio < 0.6 (and n_fwd >= 20).

    Would have caught alpha_engine_fast (BT WR ~55, FWD WR ~38 on n=80+,
    PF 0.62) before live drag accumulated.

    NOT FINANCIAL ADVICE — research/ops visibility only.
    """
    import math

    flagged: list[dict] = []
    for r in bt_vs_fwd_rows or []:
        ft = int(_float(r.get("fwd_trades", 0)))
        bt_n = int(_float(r.get("bt_trades", 0)))
        if ft < 20 or bt_n < 20:
            continue
        bt_wr = r.get("bt_wr")
        fw_wr = r.get("fwd_wr")
        if bt_wr is None or fw_wr is None:
            continue
        # Win-rate z-score under H0: forward draws from same distribution
        # as backtest. p = bt_wr/100; sigma = sqrt(p*(1-p)/n_fwd).
        p = max(0.001, min(0.999, _float(bt_wr) / 100.0))
        sigma = math.sqrt(p * (1.0 - p) / max(ft, 1))
        wr_z = ((_float(fw_wr) / 100.0) - p) / sigma if sigma > 0 else 0.0

        bt_pf = r.get("bt_pf")
        fw_pf = r.get("fwd_pf")
        try:
            pf_ratio = (_float(fw_pf) / _float(bt_pf)) if (bt_pf and _float(bt_pf) > 0) else None
        except Exception:
            pf_ratio = None

        wr_alarm = wr_z <= -2.0
        pf_alarm = pf_ratio is not None and pf_ratio < 0.6
        if not (wr_alarm or pf_alarm):
            continue

        severity = max(abs(wr_z), (1.0 - pf_ratio) if pf_ratio is not None else 0.0)
        flagged.append({
            "strategy": r.get("strategy"),
            "system": r.get("system"),
            "bt_wr": bt_wr,
            "fwd_wr": fw_wr,
            "wr_z": round(wr_z, 2),
            "bt_pf": bt_pf,
            "fwd_pf": fw_pf,
            "pf_ratio": round(pf_ratio, 2) if pf_ratio is not None else None,
            "bt_trades": bt_n,
            "fwd_trades": ft,
            "decay": r.get("decay"),
            "severity": round(severity, 2),
            "flags": (["WR_2SIGMA"] if wr_alarm else []) + (["PF_RATIO_LOW"] if pf_alarm else []),
        })
    flagged.sort(key=lambda x: x.get("severity", 0), reverse=True)
    return {
        "rows": flagged[:limit],
        "min_fwd_trades": 20,
        "min_bt_trades": 20,
        "wr_z_threshold": -2.0,
        "pf_ratio_threshold": 0.6,
        "policy_note": "Forward draws diverge from backtest distribution at 2sigma WR z-score OR PF ratio < 0.6 (n_fwd, n_bt >= 20).",
        "disclaimer": "NOT FINANCIAL ADVICE — research/ops visibility only.",
    }


def _compute_cross_asset_correlation(closed_picks: list, lookback_days: int = 30) -> dict:
    """T2.2/B7: Cross-asset correlation matrix from daily realized PnL series.

    Buckets ``closed_picks`` by (asset_class, day) over a trailing window,
    computes the daily total realized PnL per asset class, and emits a pairwise
    Pearson correlation matrix across asset classes.

    Returns:
        dict with keys:
          - matrix: {AC1: {AC2: rho, ...}, ...}  (diagonal = 1.0; missing = None)
          - n_days: int (count of dates spanning at least one observation)
          - asset_classes: sorted list of asset classes observed
          - lookback_days: echo of input
          - generated_at: ISO timestamp (UTC)

    Empty closed_picks → matrix={}, asset_classes=[], n_days=0.

    Pure numpy — uses np.corrcoef on aligned per-class daily PnL vectors over
    the union of observed dates (missing dates filled with 0.0 so unobserved
    days do not bias the rho).

    NOT FINANCIAL ADVICE — research/ops visibility only.
    """
    from datetime import datetime, timezone, timedelta

    generated_at = datetime.now(timezone.utc).isoformat()
    empty_payload = {
        "matrix": {},
        "n_days": 0,
        "asset_classes": [],
        "lookback_days": lookback_days,
        "generated_at": generated_at,
        "disclaimer": "NOT FINANCIAL ADVICE — research/ops visibility only.",
    }

    if not closed_picks:
        return empty_payload

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)

    # Bucket: {asset_class: {date_str: total_pnl}}
    buckets: dict[str, dict[str, float]] = {}

    for p in closed_picks:
        if not isinstance(p, dict):
            continue
        # Asset class — prefer existing helper if present, else upper().strip().
        try:
            ac = _coerce_asset_class(p)
        except Exception:
            ac = str(p.get("asset_class") or "").upper().strip()
        if not ac or ac in ("UNKNOWN", "NONE"):
            continue

        ts_raw = (
            p.get("closed_at")
            or p.get("close_time")
            or p.get("exit_time")
            or p.get("timestamp")
        )
        if not ts_raw:
            continue
        try:
            pick_dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            if pick_dt.tzinfo is None:
                pick_dt = pick_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if pick_dt < cutoff:
            continue

        try:
            pnl = float(p.get("pnl_pct") if p.get("pnl_pct") is not None else p.get("pnlPct"))
        except (TypeError, ValueError):
            continue

        date_str = pick_dt.strftime("%Y-%m-%d")
        buckets.setdefault(ac, {}).setdefault(date_str, 0.0)
        buckets[ac][date_str] += pnl

    if not buckets:
        return empty_payload

    asset_classes = sorted(buckets.keys())
    all_dates = sorted({d for series in buckets.values() for d in series})
    n_days = len(all_dates)

    # Single-class or n_days==0: identity matrix — no numpy needed.
    if len(asset_classes) <= 1 or n_days == 0:
        return {
            "matrix": {ac: {ac: 1.0} for ac in asset_classes},
            "n_days": n_days,
            "asset_classes": asset_classes,
            "lookback_days": lookback_days,
            "generated_at": generated_at,
            "disclaimer": "NOT FINANCIAL ADVICE — research/ops visibility only.",
        }

    # Multi-class path requires numpy for Pearson correlation.
    try:
        import numpy as np
    except ImportError:
        return empty_payload

    # Build aligned per-class vectors over the union of dates (0.0 for missing).
    vectors = {
        ac: np.array([buckets[ac].get(d, 0.0) for d in all_dates], dtype=float)
        for ac in asset_classes
    }

    matrix: dict[str, dict[str, float | None]] = {}
    for ac_a in asset_classes:
        matrix[ac_a] = {}
        va = vectors[ac_a]
        for ac_b in asset_classes:
            if ac_a == ac_b:
                matrix[ac_a][ac_b] = 1.0
                continue
            vb = vectors[ac_b]
            # np.corrcoef requires both vectors to have non-zero variance.
            if len(va) < 2 or va.std() == 0 or vb.std() == 0:
                matrix[ac_a][ac_b] = None
                continue
            try:
                rho = float(np.corrcoef(va, vb)[0, 1])
                if np.isnan(rho) or np.isinf(rho):
                    matrix[ac_a][ac_b] = None
                else:
                    matrix[ac_a][ac_b] = round(rho, 4)
            except Exception:
                matrix[ac_a][ac_b] = None

    return {
        "matrix": matrix,
        "n_days": n_days,
        "asset_classes": asset_classes,
        "lookback_days": lookback_days,
        "generated_at": generated_at,
        "disclaimer": "NOT FINANCIAL ADVICE — research/ops visibility only.",
    }


def _compute_hf_decay_watchlist(bt_vs_fwd_rows: list, limit: int = 10) -> dict:
    """Worst BT-vs-FWD decay rows for HF transparency (matches gate A sample size).

    NOT FINANCIAL ADVICE — research/ops visibility only.
    """
    try:
        from audit_trail.hf_policy_thresholds import decay_hard_gate_triggers
    except ImportError:
        def decay_hard_gate_triggers(bt_wr, fwd_wr, n_closed, gap_pp=15.0, min_closed=20):
            return False

    eligible = []
    for r in bt_vs_fwd_rows or []:
        if r.get("decay") is None:
            continue
        ft = int(_float(r.get("fwd_trades", 0)))
        if ft < 20:
            continue
        bt = r.get("bt_wr")
        fw = r.get("fwd_wr")
        if bt is None or fw is None:
            continue
        row = {
            "strategy": r.get("strategy"),
            "system": r.get("system"),
            "bt_wr": bt,
            "fwd_wr": fw,
            "decay": r.get("decay"),
            "bt_trades": r.get("bt_trades"),
            "fwd_trades": ft,
            "hf_threshold_a": bool(decay_hard_gate_triggers(bt, fw, ft)),
        }
        eligible.append(row)
    eligible.sort(key=lambda x: _float(x.get("decay", 0)))
    return {
        "rows": eligible[:limit],
        "min_fwd_trades": 20,
        "policy_note": "Subset of backtest_vs_forward with FWD n>=20 and decay computed; hf_threshold_a=user-approved gate A.",
        "disclaimer": "NOT FINANCIAL ADVICE — historical research only.",
    }


# ── Tier-2 Hero Card promotion ──
# Surfaces 4 buried-but-high-edge strategies (signal_validation, mega_mutation,
# rl_agent, claude_gainer) as DOM hero cards above the alphabetical systems
# grid on /audit. Honest tier classification per docs/PERFORMANCE_CHARTER.md
# §2 — strategies that clear the (PF >= 1.5, WR >= 50, MDD <= 20, n >= 100)
# floor get a "Tier 2" badge; those that don't get the actual classification
# (Tier 3 / Building / Below Tier 3) and a `flag` reason. Reference:
# updates/long_term_value_project_2026-04-27/research/13_goldmine_audit.md
# (research found these 4 in the alphabetical grid; recompute confirms only
# signal_validation actually meets all 4 thresholds as of 2026-04-28).

_TIER2_PROMOTION_TARGETS = (
    "signal_validation",
    "mega_mutation",
    "rl_agent",
    "claude_gainer",
)


def _classify_tier(wr_pct, pf, max_dd_pct, n) -> tuple[str, str]:
    """Return (tier_label, reason) per PERFORMANCE_CHARTER.md §2.

    Tier 1: PF >= 2.0, WR >= 55, MDD <= 10, n >= 200
    Tier 2: PF >= 1.5, WR >= 50, MDD <= 20, n >= 100
    Tier 3: PF >= 1.2, WR >= 45, MDD <= 25, n >= 100
    Below n>=100 floor: "Building"
    Else: "Below Tier 3"
    """
    n = int(n or 0)
    wr = _float(wr_pct)
    pf_v = _float(pf)
    dd = _float(max_dd_pct)
    if n < 100:
        return "Building", f"n={n} below 100-pick floor (CHARTER s10)"
    if pf_v >= 2.0 and wr >= 55 and dd <= 10 and n >= 200:
        return "Tier 1", "clears Renaissance-grade thresholds"
    if pf_v >= 1.5 and wr >= 50 and dd <= 20:
        return "Tier 2", "clears institutional sized-up floor"
    if pf_v >= 1.2 and wr >= 45 and dd <= 25:
        return "Tier 3", "paper-trading floor"
    failed = []
    if pf_v < 1.5:
        failed.append(f"PF={pf_v:.2f}<1.5")
    if wr < 50:
        failed.append(f"WR={wr:.1f}%<50")
    if dd > 20:
        failed.append(f"MDD={dd:.1f}%>20")
    return "Below Tier 3", "; ".join(failed) if failed else "below thresholds"


def _strategy_recent_picks(closed_picks: list, system_name: str, limit: int = 3) -> list:
    """Return the most-recent `limit` resolved picks for a system, newest first."""
    if not closed_picks:
        return []
    rows = []
    for p in closed_picks:
        if (p.get("source_system") or "") != system_name:
            continue
        status = (p.get("status") or "").lower()
        if status not in ("win", "loss", "tp", "sl", "closed", "filled"):
            # Allow any non-active status that has a real pnl_pct
            if p.get("pnl_pct") in (None, 0, "0", 0.0):
                continue
        rows.append(p)
    # Sort by closed_at / timestamp, newest first
    def _ts_key(pick):
        return (
            pick.get("closed_at")
            or pick.get("timestamp")
            or pick.get("entry_time")
            or ""
        )
    rows.sort(key=_ts_key, reverse=True)
    out = []
    for p in rows[:limit]:
        pnl = _float(p.get("pnl_pct"))
        out.append({
            "symbol": (p.get("symbol") or "").upper(),
            "direction": (p.get("direction") or "").upper(),
            "pnl_pct": round(pnl, 2),
            "outcome": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "FLAT"),
            "closed_at": p.get("closed_at") or p.get("timestamp"),
        })
    return out


def _strategy_pnl_sparkline(
    closed_picks: list, system_name: str, days: int = 90, max_points: int = 30
) -> list:
    """Return cumulative-PnL-percent series for `system_name` over the last
    `days` days, downsampled to roughly `max_points` points for sparkline use.
    """
    if not closed_picks:
        return []
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    series = []
    for p in closed_picks:
        if (p.get("source_system") or "") != system_name:
            continue
        ts = (
            p.get("closed_at") or p.get("timestamp") or p.get("entry_time") or ""
        )
        if not ts or ts < cutoff_iso[:10]:
            continue
        pnl = _float(p.get("pnl_pct"))
        if pnl == 0:
            continue
        series.append((ts, pnl))
    if not series:
        return []
    series.sort(key=lambda x: x[0])
    # Build cumulative
    cum = 0.0
    cum_series = []
    for _, v in series:
        cum += v
        cum_series.append(round(cum, 2))
    # Downsample
    if len(cum_series) <= max_points:
        return cum_series
    step = max(1, len(cum_series) // max_points)
    return cum_series[::step][:max_points]


def _load_latest_ta_baseline() -> dict:
    """Opt A: load latest reports/tv_backtest_benchmark_*.json for /audit panel.

    Per reports/tradingview_backtest_benchmark_2026-05-11.md. Surfaces 6-strategy
    TradingView baseline (compare_strategies + walk_forward_backtest) for direct
    apples-to-apples vs our Tier-2 systems. Picks the newest file by mtime.

    Returns:
      {
        "generated_at": ISO timestamp,
        "period": "2y", "interval": "1d", "robustness_gate": 0.60,
        "by_class": { CRYPTO/EQUITY/COMMODITY/BOND: {symbols, best_winners, avg_buy_hold_pct, any_passing_gate} },
        "results": [ per-symbol rows ],
        "source_file": basename,
      }
    Empty dict if no benchmark file or load error (fail-open).
    """
    try:
        import glob as _glob
        import os as _os
        pattern = str(ROOT / "reports" / "tv_backtest_benchmark_*.json")
        files = _glob.glob(pattern)
        if not files:
            return {}
        latest = max(files, key=_os.path.getmtime)
        with open(latest, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        d["source_file"] = _os.path.basename(latest)
        return d
    except Exception as _e:
        log.warning("  TA baseline load failed (non-fatal): %s", _e)
        return {}


def _load_swarm_picks_data(data_dir: Path) -> dict:
    """Load Swarm Pick Tracking artifacts for the audit dashboard panel.

    Reads three JSON files from ``data_dir`` (typically
    ``audit_dashboard/data``):
      * ``swarm_picks.json``        — raw pick records (list[dict])
      * ``swarm_leaderboard.json``  — per-tier / per-class / per-persona / per-underlying-model rollup
      * ``swarm_pattern_tags.json`` — winning/losing/sparse pattern cells

    All three are graceful — missing or unreadable files yield empty defaults.

    Returns a dict with the canonical keys consumed by the template panel
    (see ``audit_dashboard/template.html`` Swarm Pick Tracking section):
        {
          "picks":       [ ... ],          # raw pick records
          "leaderboard": { ... },          # passthrough of swarm_leaderboard.json
          "patterns":    { ... },          # passthrough of swarm_pattern_tags.json
          "summary":     {                 # computed from picks
              "n_total": int,
              "n_resolved": int,
              "n_open": int,
              "win_rate_pct": float,
              "profit_factor": float | None,
          },
        }
    """
    out: dict = {"picks": [], "leaderboard": {}, "patterns": {}, "summary": {}}
    try:
        picks_path = Path(data_dir) / "swarm_picks.json"
        if picks_path.exists():
            with open(picks_path, "r", encoding="utf-8") as fh:
                _picks = json.load(fh)
                if isinstance(_picks, list):
                    out["picks"] = _picks
    except Exception as _e:  # pragma: no cover
        log.warning("  swarm_picks.json load failed (non-fatal): %s", _e)
    try:
        lb_path = Path(data_dir) / "swarm_leaderboard.json"
        if lb_path.exists():
            with open(lb_path, "r", encoding="utf-8") as fh:
                _lb = json.load(fh)
                if isinstance(_lb, dict):
                    out["leaderboard"] = _lb
    except Exception as _e:  # pragma: no cover
        log.warning("  swarm_leaderboard.json load failed (non-fatal): %s", _e)
    try:
        pt_path = Path(data_dir) / "swarm_pattern_tags.json"
        if pt_path.exists():
            with open(pt_path, "r", encoding="utf-8") as fh:
                _pt = json.load(fh)
                if isinstance(_pt, dict):
                    out["patterns"] = _pt
    except Exception as _e:  # pragma: no cover
        log.warning("  swarm_pattern_tags.json load failed (non-fatal): %s", _e)

    # Compute summary stats from picks
    n_total = len(out["picks"])
    n_resolved = 0
    wins = 0
    losses = 0
    gross_win_pct = 0.0
    gross_loss_pct = 0.0
    for p in out["picks"]:
        outcome = p.get("outcome") if isinstance(p, dict) else None
        if not outcome:
            continue
        n_resolved += 1
        try:
            pnl_pct = float(outcome.get("pnl_pct") or 0.0)
        except (TypeError, ValueError):
            pnl_pct = 0.0
        if pnl_pct > 0:
            wins += 1
            gross_win_pct += pnl_pct
        elif pnl_pct < 0:
            losses += 1
            gross_loss_pct += abs(pnl_pct)
    win_rate_pct = round((wins / n_resolved) * 100.0, 1) if n_resolved else 0.0
    if gross_loss_pct > 0:
        profit_factor = round(gross_win_pct / gross_loss_pct, 2)
    elif gross_win_pct > 0:
        profit_factor = None  # division-by-zero edge (no losses) — keep None
    else:
        profit_factor = 0.0
    out["summary"] = {
        "n_total": n_total,
        "n_resolved": n_resolved,
        "n_open": n_total - n_resolved,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": win_rate_pct,
        "profit_factor": profit_factor,
        "gross_win_pct": round(gross_win_pct, 2),
        "gross_loss_pct": round(gross_loss_pct, 2),
    }
    return out


def _walkforward_promotion_gate(
    asset_classes: list,
    wf_by_class: dict,
    min_consistency: float = 60.0,
    require_positive_sharpe: bool = True,
    min_wf_n_trades: int = 30,
) -> tuple[bool, str]:
    """Tier-1 promotion gate (Opt B per reports/tradingview_backtest_benchmark_2026-05-11.md).

    A system claiming PF>=2.0 / WR>=55 / MDD<=10 (classic Tier-1 thresholds)
    only earns the Renaissance-grade label if its PRIMARY asset class also
    passes walk-forward robustness:

      walkforward.by_class[CLASS].window_config.n_trades >= min_wf_n_trades  (default 30)
      walkforward.by_class[CLASS].consistency >= min_consistency             (default 60)
      walkforward.by_class[CLASS].oos_sharpe  > 0                            (default ON)

    Rationale: classic thresholds reward in-sample backtest fitting; walk-forward
    consistency measures OOS edge stability. A system that passes in-sample but
    has 48% fold consistency (FOREX as of 2026-05-10) is regime-lucky, not Tier-1.

    n-floor (added 2026-05-14 per PR #993 review): without an n-floor, classes
    with tiny n (BOND n=12, test_size=2) can produce explosive oos_sharpe
    estimates (Monte-Carlo std ~941 on zero-edge processes) that pass the
    sharpe>0 check ~28% of the time on pure noise. The n>=30 floor matches
    the empirical threshold below which 2-element-window Sharpe is unreliable.

    Returns (passed, reason). Fail-open if wf_by_class missing or asset_classes
    empty — never block a promotion on missing data.
    """
    if not wf_by_class or not asset_classes:
        return (True, "wf_data_missing_or_no_class_tags_fail_open")
    fails = []
    checked = []
    for cls in asset_classes:
        cls_u = str(cls or "").upper()
        if not cls_u:
            continue
        block = wf_by_class.get(cls_u) or {}
        if not block:
            continue
        checked.append(cls_u)
        wc = block.get("window_config") or {}
        n_trades = int(_float(wc.get("n_trades")))
        if n_trades and n_trades < min_wf_n_trades:
            fails.append(f"{cls_u}: wf_n_trades={n_trades}<{min_wf_n_trades} (sharpe unreliable)")
            continue
        consistency = _float(block.get("consistency"))
        oos_sharpe = _float(block.get("oos_sharpe"))
        if consistency < min_consistency:
            fails.append(f"{cls_u}: consistency={consistency:.1f}%<{min_consistency:.0f}%")
            continue
        if require_positive_sharpe and oos_sharpe <= 0:
            fails.append(f"{cls_u}: oos_sharpe={oos_sharpe:.2f}<=0")
            continue
    if not checked:
        return (True, "no_classes_with_wf_data_fail_open")
    if fails:
        return (False, "; ".join(fails))
    return (True, f"wf_pass: {','.join(checked)}")


def _compute_tier2_proven_strategies(systems: list, closed_picks: list) -> dict:
    """Surface buried Tier-2 candidates as hero-card data for /audit.

    Looks up the 4 promotion targets in `systems`, recomputes per-CHARTER
    tier classification, and packages each card with sparkline + recent picks.
    Returns a dict consumed by template.html `renderTier2Heroes()`.

    Staleness: systems whose last_signal_at is > 30 days ago (or missing)
    are marked ``is_stale`` so the dashboard can display a warning badge.
    Stale systems may still have good historical metrics but are no longer
    emitting active picks — they should NOT be treated as actionable.

    NOT FINANCIAL ADVICE — promotional surface for research-grade strategies.
    """
    now_utc = datetime.now(timezone.utc)
    sys_by_name = {s.get("name"): s for s in (systems or [])}
    cards = []
    flagged = []
    for target in _TIER2_PROMOTION_TARGETS:
        s = sys_by_name.get(target)
        if not s:
            flagged.append({"name": target, "reason": "not in systems[] feed"})
            continue
        n_resolved = int(s.get("resolved_picks", 0) or 0)
        wr = _float(s.get("win_rate"))
        pf = _float(s.get("profit_factor"))
        mdd = _float(s.get("max_drawdown"))
        tier_label, tier_reason = _classify_tier(wr, pf, mdd, n_resolved)
        is_strict_tier2 = (tier_label == "Tier 2")
        # Thin-sample badge per CHARTER §10
        thin_sample = n_resolved < 200
        recent = _strategy_recent_picks(closed_picks, target, limit=3)
        sparkline = _strategy_pnl_sparkline(closed_picks, target, days=90)
        # Asset class tags (set in collect_system_stats already, normalised to list)
        asset_classes = list(s.get("asset_classes") or [])
        # Staleness: flag systems inactive > 30 days
        last_signal = s.get("last_signal_at")
        is_stale = True
        stale_days = None
        if last_signal:
            try:
                ts_str = str(last_signal)
                last_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                delta = now_utc - last_dt
                stale_days = round(delta.total_seconds() / 86400, 1)
                is_stale = stale_days > 30
            except (ValueError, TypeError, OverflowError):
                pass
        if not is_strict_tier2:
            flagged.append({
                "name": target,
                "reason": f"{tier_label}: {tier_reason}",
                "n": n_resolved,
                "wr_pct": wr,
                "profit_factor": pf,
                "max_drawdown": mdd,
            })
        cards.append({
            "name": target,
            "tier": tier_label,
            "tier_reason": tier_reason,
            "is_strict_tier2": is_strict_tier2,
            "thin_sample": thin_sample,
            "n": n_resolved,
            "n_closed": int(s.get("closed_picks", 0) or 0),
            "wins": int(s.get("wins", 0) or 0),
            "losses": int(s.get("losses", 0) or 0),
            "wr_pct": round(wr, 1),
            "profit_factor": round(pf, 2),
            "max_drawdown": round(mdd, 2),
            "expectancy_pct": round(_float(s.get("expectancy")), 2),
            "total_pnl_pct": round(_float(s.get("total_pnl_pct")), 2),
            "asset_classes": asset_classes,
            "last_signal_at": s.get("last_signal_at"),
            "is_stale": is_stale,
            "stale_days": stale_days,
            "status": s.get("status"),
            "recent_picks": recent,
            "pnl_sparkline_90d": sparkline,
        })
    return {
        "cards": cards,
        "flagged_dropouts": flagged,
        "promotion_targets": list(_TIER2_PROMOTION_TARGETS),
        "charter_ref": "docs/PERFORMANCE_CHARTER.md §2",
        "research_ref": "updates/long_term_value_project_2026-04-27/research/13_goldmine_audit.md",
        "disclaimer": "NOT FINANCIAL ADVICE — research surface only.",
    }


# ── Sidecar promotion tracker (2026-05-09) ──
# Per-strategy promotion gates for opt-in / wired sidecar strategies. Each entry
# defines the (n, wr%, pf) thresholds a sidecar must clear to be eligible for
# promotion to a production caller. The ``_PROMOTED_SIDECARS`` set lists those
# already wired into production pick-generation paths (status overrides stats).
#
# Refs: 214d2468b93 (confluence/PROVEN_RESEARCH/equity wires), 398bbdf0036
# (commodity_cot_contrarian opt-in), 98f8fa4a845 (volume_weighted_candle_sequence
# + market_structure_volume opt-in), 54c1d5868a5 (pm_consensus_overlay opt-in).
_SIDECAR_PROMOTION_GATES = {
    "sentiment_macro_contrarian":      {"gate_n": 30,  "gate_wr": 55.0, "gate_pf": 1.3},
    "crypto_pairs_arb":                {"gate_n": 30,  "gate_wr": 50.0, "gate_pf": 1.3},
    "regime_filtered_momentum":        {"gate_n": 20,  "gate_wr": 50.0, "gate_pf": 1.2},
    "commodity_cot_contrarian":        {"gate_n": 20,  "gate_wr": 55.0, "gate_pf": 1.5},
    "volume_weighted_candle_sequence": {"gate_n": 100, "gate_wr": 38.9, "gate_pf": 1.3},
    "market_structure_volume":         {"gate_n": 50,  "gate_wr": 50.0, "gate_pf": 1.3},
    "pm_consensus_overlay":            {"gate_n": 10,  "gate_wr": 60.0, "gate_pf": 1.5},
}

# Strategies already wired into production pick-generation callers (PROMOTED).
_PROMOTED_SIDECARS = {
    "sentiment_macro_contrarian",
    "crypto_pairs_arb",
    "regime_filtered_momentum",
}


def _compute_sidecar_promotion_status(closed_picks: list, leaderboard=None) -> dict:
    """Sidecar live-validation tracker for /audit promotion gates.

    For each registered sidecar strategy, computes live forward stats from
    ``closed_picks`` and classifies it on a 4-state promotion ladder:

        INCUBATING        — n < gate_n (insufficient sample)
        BELOW_GATE        — n >= gate_n but failing wr or pf threshold
        READY_TO_PROMOTE  — passing all 3 gates (n, wr, pf)
        PROMOTED          — already wired into a production caller

    PROMOTED status is sticky — driven by ``_PROMOTED_SIDECARS`` not stats.

    ``eta_to_promotion_days`` is a simple linear extrapolation: if the strategy
    has been trading for ``days_since_first_trade`` days at pace
    ``P_d = n / days``, then ETA = ``(gate_n - n) / P_d``. Returns None when
    promoted, when the gate is already met, or when pace is unmeasurable.

    Args:
        closed_picks: list of closed-pick dicts (uses ``strategy``,
            ``source_system``, ``pnl_pct``, and a timestamp field).
        leaderboard: optional, currently unused (reserved for future cross-ref
            against backtest baselines).

    Returns:
        dict mapping strategy_name -> 9-key entry:
            {n, wr, pf, gate_n, gate_wr, gate_pf, status,
             days_since_first_trade, eta_to_promotion_days}

    Empty closed_picks -> all sidecars present with n=0 in INCUBATING (or
    PROMOTED if in the hardcoded list).

    NOT FINANCIAL ADVICE — promotion-readiness visibility only.
    """
    buckets = {name: [] for name in _SIDECAR_PROMOTION_GATES}
    sidecar_names_lc = {name.lower(): name for name in _SIDECAR_PROMOTION_GATES}

    for p in (closed_picks or []):
        if not isinstance(p, dict):
            continue
        strat_raw = str(p.get("strategy") or p.get("source_system") or "").strip().lower()
        if not strat_raw:
            continue
        canonical = sidecar_names_lc.get(strat_raw)
        if canonical is None:
            continue
        buckets[canonical].append(p)

    out = {}
    for name, gates in _SIDECAR_PROMOTION_GATES.items():
        rows = buckets[name]
        n = len(rows)
        is_promoted = name in _PROMOTED_SIDECARS

        if n == 0:
            wr = 0.0
            pf = 0.0
            days_since_first = 0
        else:
            wins = 0
            win_pnl = 0.0
            loss_pnl = 0.0
            timestamps = []
            for r in rows:
                pnl = _float(r.get("pnl_pct") if r.get("pnl_pct") is not None else r.get("pnlPct"))
                if pnl > 0:
                    wins += 1
                    win_pnl += pnl
                else:
                    loss_pnl += abs(pnl)
                ts_raw = (
                    r.get("closed_at") or r.get("close_time")
                    or r.get("exit_time") or r.get("timestamp")
                )
                if ts_raw:
                    try:
                        dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        timestamps.append(dt)
                    except (ValueError, TypeError):
                        pass

            wr = round(100.0 * wins / n, 2) if n else 0.0
            if loss_pnl > 0:
                pf = round(win_pnl / loss_pnl, 3)
            elif win_pnl > 0:
                pf = 999.0  # all-wins sentinel
            else:
                pf = 0.0

            if timestamps:
                first = min(timestamps)
                now = datetime.now(timezone.utc)
                days_since_first = max(0, int((now - first).total_seconds() // 86400))
            else:
                days_since_first = 0

        # Status — PROMOTED is sticky.
        if is_promoted:
            status = "PROMOTED"
        elif n < gates["gate_n"]:
            status = "INCUBATING"
        elif wr >= gates["gate_wr"] and pf >= gates["gate_pf"]:
            status = "READY_TO_PROMOTE"
        else:
            status = "BELOW_GATE"

        # ETA — linear extrapolation; only meaningful if INCUBATING with pace.
        eta = None
        if status == "INCUBATING" and n > 0 and days_since_first > 0:
            pace = n / float(days_since_first)
            if pace > 0:
                eta = round((gates["gate_n"] - n) / pace, 1)

        out[name] = {
            "n": n,
            "wr": wr,
            "pf": pf,
            "gate_n": gates["gate_n"],
            "gate_wr": gates["gate_wr"],
            "gate_pf": gates["gate_pf"],
            "status": status,
            "days_since_first_trade": days_since_first,
            "eta_to_promotion_days": eta,
        }
    return out


def collect_strategy_leaderboard(active, closed):
    """Build a per-strategy leaderboard combining backtest + forward metrics."""
    strats = {}

    # ── Source 1: Survivor backtest results (BT metrics) ──
    bt_data = _safe_json(ROOT / "alpha_engine/data/survivor_backtest_results.json")
    if bt_data and bt_data.get("results"):
        for name, r in bt_data["results"].items():
            strats[name] = {
                "strategy": name,
                "bt_wr": r.get("win_rate_pct"),
                "bt_trades": r.get("total_trades", 0),
                "bt_sharpe": r.get("sharpe"),
                "bt_pf": r.get("profit_factor"),
                "bt_return": r.get("total_return_pct"),
                "bt_verdict": r.get("verdict", ""),
                "bt_oos_wr": r.get("oos_wr"),
                "bt_symbols_profitable": r.get("symbols_profitable", 0),
                "bt_symbols_tested": r.get("symbols_tested", 0),
                "fwd_wr": None,
                "fwd_trades": 0,
                "fwd_wins": 0,
                "fwd_losses": 0,
                "fwd_avg_pnl": 0.0,
                "fwd_total_pnl": 0.0,
                "_win_pnl": 0.0,
                "_loss_pnl": 0.0,
                "_max_dd": 0.0,
                "systems": set(),
                "portfolio_type": "",
            }

    # ── Source 2: Forward-testing from all closed picks ──
    # COLLISION-SAFE AGGREGATION (Agent F, follow-up to PR #160):
    # Re-keyed on (source_system, strategy) tuple. Previously keyed on
    # `strategy` alone, which caused distinct feeder systems emitting picks
    # with the same strategy tag to collapse into one leaderboard row. See
    # `docs/forensics/fear_greed_contrarian_collapse_2026-04-13.md` — the
    # "st_fear_greed_contrarian 80.9% WR" figure was actually ``claude_gainer_st``
    # picks wearing the tag, summed on top of ~60 real paper-trading picks.
    #
    # We also still maintain a by-name aggregation (``strats``) for display
    # compatibility with external sources that have no ``source_system`` (BT
    # rankings, baby-strat meta files, coinglass signals, KIMI competition),
    # and so the legacy name-keyed lookup in ``strat_lookup`` still resolves.
    _strat_picks = {}  # by-name PnL series (legacy, for max drawdown)
    _strat_trades = {}  # by-name trade dicts (legacy, for rolling WR)
    _sys_strat_picks: dict[tuple[str, str], list[float]] = {}
    _sys_strat_trades: dict[tuple[str, str], list[dict]] = {}
    sys_strat_rows: dict[tuple[str, str], dict] = {}

    def _blank_row(name: str, source_system: str = "") -> dict:
        return {
            "strategy": name,
            "source_system": source_system,
            "bt_wr": None,
            "bt_trades": 0,
            "bt_sharpe": None,
            "bt_pf": None,
            "bt_return": None,
            "bt_verdict": "",
            "bt_oos_wr": None,
            "bt_symbols_profitable": 0,
            "bt_symbols_tested": 0,
            "fwd_wr": None,
            "fwd_trades": 0,
            "fwd_wins": 0,
            "fwd_losses": 0,
            "fwd_avg_pnl": 0.0,
            "fwd_total_pnl": 0.0,
            "_win_pnl": 0.0,
            "_loss_pnl": 0.0,
            "systems": set(),
            "portfolio_type": "",
        }

    for pick in _filter_valid_resolved_picks(closed):
        name = pick.get("strategy", "")
        if not name:
            continue
        sys_name = pick.get("source_system", "") or ""
        pnl = pick.get("pnl_pct", 0)

        # --- Legacy by-name aggregation (kept for display/lookup compat) ---
        if name not in strats:
            strats[name] = _blank_row(name)
        s = strats[name]
        s["fwd_trades"] += 1
        s["fwd_total_pnl"] += pnl
        if pnl > 0:
            s["fwd_wins"] += 1
            s.setdefault("_win_pnl", 0.0)
            s["_win_pnl"] += pnl
        elif pnl < 0:
            s["fwd_losses"] += 1
            s.setdefault("_loss_pnl", 0.0)
            s["_loss_pnl"] += pnl
        _strat_picks.setdefault(name, []).append(pnl)
        _strat_trades.setdefault(name, []).append(pick)
        s["systems"].add(sys_name)

        # --- Collision-safe (source_system, strategy) aggregation ---
        if sys_name:
            sys_key = (sys_name, name)
            if sys_key not in sys_strat_rows:
                sys_strat_rows[sys_key] = _blank_row(name, sys_name)
            ss = sys_strat_rows[sys_key]
            ss["fwd_trades"] += 1
            ss["fwd_total_pnl"] += pnl
            if pnl > 0:
                ss["fwd_wins"] += 1
                ss["_win_pnl"] += pnl
            elif pnl < 0:
                ss["fwd_losses"] += 1
                ss["_loss_pnl"] += pnl
            ss["systems"].add(sys_name)
            _sys_strat_picks.setdefault(sys_key, []).append(pnl)
            _sys_strat_trades.setdefault(sys_key, []).append(pick)

    # Compute max drawdown per strategy from PnL series (legacy by-name)
    for name, pnl_series in _strat_picks.items():
        if name in strats:
            cum = 0.0
            peak = 0.0
            max_dd = 0.0
            for p in pnl_series:
                cum += p
                if cum > peak:
                    peak = cum
                dd = peak - cum
                if dd > max_dd:
                    max_dd = dd
            strats[name]["_max_dd"] = round(max_dd, 2)

    # Max drawdown for (source_system, strategy) rows
    for sys_key, pnl_series in _sys_strat_picks.items():
        if sys_key in sys_strat_rows:
            cum = 0.0
            peak = 0.0
            max_dd = 0.0
            for p in pnl_series:
                cum += p
                if cum > peak:
                    peak = cum
                dd = peak - cum
                if dd > max_dd:
                    max_dd = dd
            sys_strat_rows[sys_key]["_max_dd"] = round(max_dd, 2)

    # ── Source 3: Active picks count ──
    active_counts = {}
    for pick in active:
        name = pick.get("strategy", "")
        if name:
            active_counts[name] = active_counts.get(name, 0) + 1

    # ── Source 4: Paper trading strategy metadata ──
    try:
        from paper_trading.strategies import STRATEGY_METADATA

        for name, meta in STRATEGY_METADATA.items():
            if name in strats:
                strats[name]["portfolio_type"] = meta.get("portfolio_type", "")
                strats[name]["system_name"] = meta.get("system_name", "")
            elif name not in strats:
                strats[name] = {
                    "strategy": name,
                    "bt_wr": None,
                    "bt_trades": 0,
                    "bt_sharpe": None,
                    "bt_pf": None,
                    "bt_return": None,
                    "bt_verdict": "",
                    "bt_oos_wr": None,
                    "bt_symbols_profitable": 0,
                    "bt_symbols_tested": 0,
                    "fwd_wr": None,
                    "fwd_trades": 0,
                    "fwd_wins": 0,
                    "fwd_losses": 0,
                    "fwd_avg_pnl": 0.0,
                    "fwd_total_pnl": 0.0,
                    "systems": set(),
                    "portfolio_type": meta.get("portfolio_type", ""),
                    "system_name": meta.get("system_name", ""),
                }
    except ImportError:
        pass

    # ── Source 5: Baby strat meta.json files (forward metrics) ──
    _default_strat = lambda name: {
        "strategy": name,
        "bt_wr": None,
        "bt_trades": 0,
        "bt_sharpe": None,
        "bt_pf": None,
        "bt_return": None,
        "bt_verdict": "",
        "bt_oos_wr": None,
        "bt_symbols_profitable": 0,
        "bt_symbols_tested": 0,
        "fwd_wr": None,
        "fwd_trades": 0,
        "fwd_wins": 0,
        "fwd_losses": 0,
        "fwd_avg_pnl": 0.0,
        "fwd_total_pnl": 0.0,
        "systems": set(),
        "portfolio_type": "incubator",
    }
    for meta_path in glob.glob(
        str(ROOT / "incubator/agents/**/*.py.meta.json"), recursive=True
    ):
        try:
            meta = json.loads(Path(meta_path).read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        name = meta.get("strategy_name", "")
        if not name:
            continue
        fm = meta.get("forward_metrics", {})
        total_fwd = fm.get("total_trades") or 0
        fwd_wr_raw = fm.get("win_rate")
        if name not in strats:
            strats[name] = _default_strat(name)
        s = strats[name]
        if total_fwd > 0 and fwd_wr_raw is not None:
            s["fwd_trades"] = max(s["fwd_trades"], total_fwd)
            # Compute wins/losses from forward trades in meta
            ft = meta.get("forward_trades", [])
            meta_wins = sum(1 for t in ft if (t.get("pnl_pct") or 0) > 0)
            meta_losses = sum(1 for t in ft if (t.get("pnl_pct") or 0) < 0)
            meta_total_pnl = sum(t.get("pnl_pct", 0) for t in ft)
            if meta_wins + meta_losses > s["fwd_wins"] + s["fwd_losses"]:
                s["fwd_wins"] = meta_wins
                s["fwd_losses"] = meta_losses
                s["fwd_total_pnl"] = meta_total_pnl
        agent = meta.get("agent_id", "")
        if agent:
            s["systems"].add(agent)

    # ── Source 6: Baby strats dashboard (BT + FWD metrics for ALL baby strategies) ──
    bsd = _safe_json(ROOT / "battleground/data/baby_strats_dashboard.json")
    if bsd:
        for strat in bsd.get("strategies", []):
            name = strat.get("name", "")
            if not name:
                continue
            bm = strat.get("backtest_metrics", {}) or {}
            fm = strat.get("forward_metrics", {}) or {}
            ft = strat.get("forward_trades", []) or []
            bt_trades = bm.get("total_trades", 0) or 0
            bt_wr_raw = bm.get("win_rate", 0) or 0
            if bt_wr_raw > 0 and bt_wr_raw <= 1:
                bt_wr_raw = bt_wr_raw * 100
            bt_sharpe = _cap_sharpe(bm.get("sharpe", 0))
            bt_pf = bm.get("profit_factor", 0) or 0
            bt_return = bm.get("total_return", 0) or 0

            if name not in strats:
                strats[name] = _default_strat(name)
            s = strats[name]
            # Fill in backtest data if not already populated from survivor results
            if s["bt_wr"] is None and bt_trades > 0:
                s["bt_wr"] = round(bt_wr_raw, 1)
                s["bt_trades"] = bt_trades
                s["bt_sharpe"] = bt_sharpe
                s["bt_pf"] = bt_pf
                s["bt_return"] = bt_return
            # Fill forward data from baby_strats forward_trades if richer
            if ft:
                meta_wins = sum(
                    1
                    for t in ft
                    if isinstance(t, dict) and (t.get("pnl_pct", 0) or 0) > 0
                )
                meta_losses = sum(
                    1
                    for t in ft
                    if isinstance(t, dict) and (t.get("pnl_pct", 0) or 0) < 0
                )
                meta_pnl = sum(
                    t.get("pnl_pct", 0) or 0 for t in ft if isinstance(t, dict)
                )
                if meta_wins + meta_losses > s["fwd_wins"] + s["fwd_losses"]:
                    s["fwd_wins"] = meta_wins
                    s["fwd_losses"] = meta_losses
                    s["fwd_trades"] = max(s["fwd_trades"], len(ft))
                    s["fwd_total_pnl"] = meta_pnl
            # Track live picks
            live_count = strat.get("forward_live_pick_count", 0) or 0
            if live_count > 0:
                s.setdefault("live_picks", 0)
                s["live_picks"] = max(s.get("live_picks", 0), live_count)
            s["systems"].add("baby_strats_forward")
            s["portfolio_type"] = s.get("portfolio_type") or "incubator"
            s["baby_status"] = strat.get("status", "")
            s["baby_stage"] = strat.get("stage", 0)
            s["category"] = strat.get("category", "")

    # ── Source 7: Coinglass signal DB ──
    cg_db = ROOT / "coinglass_strategies" / "data" / "coinglass.db"
    if cg_db.exists():
        try:
            cg_signals = _safe_sqlite(
                cg_db,
                """
                SELECT s.strategy, COUNT(p.id) as total,
                       SUM(CASE WHEN p.pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN p.pnl_pct <= 0 THEN 1 ELSE 0 END) as losses,
                       AVG(CASE WHEN p.pnl_pct IS NOT NULL THEN p.pnl_pct ELSE 0 END) as avg_pnl
                FROM positions p
                JOIN signals s ON p.signal_id = s.signal_id
                WHERE p.status = 'CLOSED'
                GROUP BY s.strategy
            """,
            )
            for r in cg_signals:
                name = r.get("strategy", "")
                if not name:
                    continue
                if name not in strats:
                    strats[name] = _default_strat(name)
                s = strats[name]
                cg_wins = r.get("wins", 0) or 0
                cg_losses = r.get("losses", 0) or 0
                if cg_wins + cg_losses > s["fwd_wins"] + s["fwd_losses"]:
                    s["fwd_wins"] = cg_wins
                    s["fwd_losses"] = cg_losses
                    s["fwd_trades"] = r.get("total", 0) or 0
                s["fwd_avg_pnl"] = round(r.get("avg_pnl", 0) or 0, 2)
                s["systems"].add("coinglass")
                s["portfolio_type"] = "incubator"
        except Exception as e:
            log.warning("Coinglass leaderboard query failed: %s", e)

    # ── Source 8: KIMI competition algorithms (91 algos with actual forward picks) ──
    kimi_comp = _safe_json(ROOT / "riseoftheclaw/data/live_competition.json")
    if kimi_comp:
        algos = kimi_comp.get("algorithms", [])
        if isinstance(algos, dict):
            algos = list(algos.values())
        kimi_lb_count = 0
        for algo in algos:
            if not isinstance(algo, dict):
                continue
            name = algo.get("id", algo.get("name", ""))
            if not name:
                continue
            cp = algo.get("closedPicks", algo.get("closedTrades", []))
            ap = algo.get("activePicks", [])
            if name not in strats:
                strats[name] = _default_strat(name)
            s = strats[name]
            # Merge forward data from competition (may have more data than audit picks)
            kimi_wins = sum(
                1 for t in cp if _float(t.get("pnlPct", t.get("pnl_pct", 0))) > 0
            )
            kimi_losses = sum(
                1 for t in cp if _float(t.get("pnlPct", t.get("pnl_pct", 0))) < 0
            )
            kimi_pnl = sum(_float(t.get("pnlPct", t.get("pnl_pct", 0))) for t in cp)
            if kimi_wins + kimi_losses > s["fwd_wins"] + s["fwd_losses"]:
                s["fwd_wins"] = kimi_wins
                s["fwd_losses"] = kimi_losses
                s["fwd_trades"] = max(s["fwd_trades"], len(cp))
                s["fwd_total_pnl"] = kimi_pnl
                s.setdefault("_win_pnl", 0.0)
                s["_win_pnl"] = sum(
                    _float(t.get("pnlPct", 0))
                    for t in cp
                    if _float(t.get("pnlPct", 0)) > 0
                )
                s.setdefault("_loss_pnl", 0.0)
                s["_loss_pnl"] = sum(
                    _float(t.get("pnlPct", 0))
                    for t in cp
                    if _float(t.get("pnlPct", 0)) < 0
                )
                # Collect individual PnL values for omega/tail ratio computation
                _strat_picks[name] = [
                    _float(t.get("pnlPct", t.get("pnl_pct", 0))) for t in cp
                ]
            s["systems"].add("kimi_competition")
            s["portfolio_type"] = s.get("portfolio_type") or "kimi"
            s["drought_scans"] = algo.get("droughtScans", 0)
            s["kimi_tier"] = algo.get("tier", "")
            kimi_lb_count += 1
        if kimi_lb_count:
            log.info("  KIMI competition leaderboard: %d algos", kimi_lb_count)

    # ── Source 9: Backtest rankings JSON (from weekly backtest engine) ──
    bt_rankings = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/backtest_rankings.json")
    if bt_rankings:
        rankings_list = (
            bt_rankings
            if isinstance(bt_rankings, list)
            else bt_rankings.get("rankings", bt_rankings.get("results", []))
        )
        for r in rankings_list:
            if not isinstance(r, dict):
                continue
            name = r.get("strategy_id", r.get("id", r.get("name", "")))
            if not name:
                continue
            if name not in strats:
                strats[name] = _default_strat(name)
            s = strats[name]
            # Fill BT data if not already richer
            bt_wr = r.get("win_rate") or r.get("win_rate_pct")
            bt_trades = r.get("total_trades", 0) or r.get("trades", 0)
            if s["bt_wr"] is None and bt_wr is not None:
                s["bt_wr"] = round(bt_wr, 1)
                s["bt_trades"] = bt_trades
                s["bt_sharpe"] = _cap_sharpe(r.get("sharpe"))
                s["bt_pf"] = r.get("profit_factor")
            s["bt_tier"] = r.get("tier", r.get("status", ""))
            s["bt_eliminated"] = str(s.get("bt_tier", "")).upper() == "ELIMINATED"
            s["systems"].add("backtest_arena")

    # ── Compute final metrics ──
    # We finalize two logical row-sets:
    #   1. Legacy by-name rows (``strats``) — carry BT, baby-strat, coinglass,
    #      KIMI data merged from external sources that have no source_system.
    #      These preserve backward-compat for any downstream lookup keyed on
    #      strategy name alone.
    #   2. Collision-safe per-(source_system, strategy) rows (``sys_strat_rows``) —
    #      computed above from closed-picks forward aggregation. Each row carries
    #      an explicit ``source_system`` field so downstream enrichment can pick
    #      the right row when two feeder systems share a strategy tag.
    result = []

    def _finalize_row(name: str, s: dict, pnl_series_map: dict, trades_map: dict, key) -> None:
        # Ensure every row carries a source_system field (empty string for
        # legacy by-name rows that pre-date the re-key) so downstream
        # consumers can rely on the schema.
        s.setdefault("source_system", "")
        total_fwd = s["fwd_wins"] + s["fwd_losses"]
        s["fwd_wr"] = (
            round(s["fwd_wins"] / total_fwd * 100, 1) if total_fwd > 0 else None
        )
        s["fwd_avg_pnl"] = (
            round(s["fwd_total_pnl"] / s["fwd_trades"], 2) if s["fwd_trades"] > 0 else 0
        )
        s["fwd_total_pnl"] = round(s["fwd_total_pnl"], 2)
        s["active_picks"] = active_counts.get(name, 0)

        # Enhanced forward metrics: avg_win, avg_loss, profit_factor, expectancy
        win_pnl = s.pop("_win_pnl", 0.0)
        loss_pnl = s.pop("_loss_pnl", 0.0)
        s["fwd_avg_win"] = round(win_pnl / s["fwd_wins"], 2) if s["fwd_wins"] > 0 else 0
        s["fwd_avg_loss"] = (
            round(abs(loss_pnl) / s["fwd_losses"], 2) if s["fwd_losses"] > 0 else 0
        )
        s["fwd_pf"] = round(win_pnl / abs(loss_pnl), 2) if loss_pnl < 0 else None
        wr_frac = s["fwd_wr"] / 100 if s["fwd_wr"] is not None else 0
        s["fwd_expectancy"] = (
            round((wr_frac * s["fwd_avg_win"]) - ((1 - wr_frac) * s["fwd_avg_loss"]), 2)
            if total_fwd > 0
            else None
        )
        # Common Sense Ratio: (WR × AvgWin) / (LR × AvgLoss)
        s["fwd_csr"] = None
        if (
            total_fwd >= 5
            and s["fwd_wins"] > 0
            and s["fwd_losses"] > 0
            and s["fwd_avg_loss"] > 0
        ):
            s["fwd_csr"] = round(
                (wr_frac * s["fwd_avg_win"]) / ((1 - wr_frac) * s["fwd_avg_loss"]), 2
            )
        s["fwd_max_dd"] = s.pop("_max_dd", 0.0)

        # Omega Ratio and Tail Ratio (require 5+ closed trades with PnL series)
        pnl_series = pnl_series_map.get(key, [])
        if len(pnl_series) >= 5:
            # Omega Ratio: sum of gains above threshold(0) / sum of losses below threshold(0)
            gains_sum = sum(p for p in pnl_series if p > 0)
            losses_sum = sum(-p for p in pnl_series if p < 0)  # positive value
            s["omega_ratio"] = (
                round(gains_sum / losses_sum, 2) if losses_sum > 0 else None
            )

            # Tail Ratio: 95th pctile of positive returns / abs(5th pctile of negative returns)
            positive_returns = sorted([p for p in pnl_series if p > 0])
            negative_returns = sorted([p for p in pnl_series if p < 0])
            if len(positive_returns) >= 2 and len(negative_returns) >= 2:
                # Percentile using linear interpolation (stdlib, no numpy)
                def _percentile(sorted_data, pct):
                    n = len(sorted_data)
                    k = (pct / 100.0) * (n - 1)
                    f = int(k)
                    c = f + 1 if f + 1 < n else f
                    d = k - f
                    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])

                p95_win = _percentile(positive_returns, 95)
                p5_loss = abs(_percentile(negative_returns, 5))
                s["tail_ratio"] = round(p95_win / p5_loss, 2) if p5_loss > 0 else None
            else:
                s["tail_ratio"] = None
        else:
            s["omega_ratio"] = None
            s["tail_ratio"] = None

        # Sample quality label
        if s["fwd_trades"] >= 20:
            s["sample_quality"] = "strong"
        elif s["fwd_trades"] >= 10:
            s["sample_quality"] = "moderate"
        elif s["fwd_trades"] >= 5:
            s["sample_quality"] = "weak"
        else:
            s["sample_quality"] = "insufficient"

        # Decay: FWD WR - BT WR
        decay = None
        if s["fwd_wr"] is not None and s["bt_wr"] is not None:
            decay = round(s["fwd_wr"] - s["bt_wr"], 1)
        s["decay"] = decay

        # Rolling WR (last 10 trades) and health score
        trades_list = trades_map.get(key, [])
        s["fwd_last10_wr"] = (
            round(_rolling_wr(trades_list) * 100, 1) if trades_list else None
        )
        s["health"] = _health_score(s)

        # Convert sets to lists for JSON
        s["systems"] = sorted(s["systems"] - {""})

        # F2: dominant asset_class for per-class leaderboard switcher.
        # Computed from realized trades; if a strategy has mixed classes,
        # `asset_class` = the most-traded one and `asset_classes` lists all.
        ac_counts: dict[str, int] = {}
        for t in trades_list:
            ac = (t.get("asset_class") or t.get("category") or "").upper().strip()
            if ac:
                ac_counts[ac] = ac_counts.get(ac, 0) + 1
        if ac_counts:
            s["asset_class"] = max(ac_counts.items(), key=lambda kv: kv[1])[0]
            s["asset_classes"] = sorted(ac_counts.keys())
        else:
            s["asset_class"] = ""
            s["asset_classes"] = []

        result.append(s)

    # Finalize legacy by-name rows (for external-source merge and legacy lookup)
    for name, s in strats.items():
        _finalize_row(name, s, _strat_picks, _strat_trades, key=name)

    # Finalize collision-safe (source_system, strategy) rows. Each emits its
    # own independent metrics plus an explicit ``source_system`` field.
    for sys_key, s in sys_strat_rows.items():
        _finalize_row(s["strategy"], s, _sys_strat_picks, _sys_strat_trades, key=sys_key)

    # ── ML group aggregation ──
    # ML sub-strategies (ml_enhanced_*) each have only 1-2 trades, making their
    # individual forward stats meaningless. We aggregate them into group rows
    # (e.g. "ml_enhanced_group") so picks can inherit meaningful composite stats.
    _ml_group_agg: dict[str, dict] = {}  # group_name -> aggregated row
    for r in result:
        gname = _ml_group_name(r.get("strategy", ""))
        if not gname:
            continue
        if gname not in _ml_group_agg:
            _ml_group_agg[gname] = {
                "strategy": gname,
                "source_system": "",
                "bt_wr": None, "bt_trades": 0, "bt_sharpe": None,
                "bt_pf": None, "bt_return": None, "bt_verdict": "",
                "bt_oos_wr": None, "bt_symbols_profitable": 0, "bt_symbols_tested": 0,
                "fwd_wr": None, "fwd_trades": 0, "fwd_wins": 0, "fwd_losses": 0,
                "fwd_avg_pnl": 0.0, "fwd_total_pnl": 0.0,
                "fwd_avg_win": 0.0, "fwd_avg_loss": 0.0,
                "fwd_pf": None, "fwd_expectancy": None, "fwd_csr": None,
                "fwd_max_dd": 0.0,
                "omega_ratio": None, "tail_ratio": None,
                "_win_pnl": 0.0, "_loss_pnl": 0.0,
                "_pnl_series": [],
                "_trades_series": [],
                "systems": set(), "portfolio_type": "ml_group",
                "active_picks": 0, "_is_ml_group": True,
                "_child_strategies": [],
                # F2 leaderboard chips: track constituent asset_class
                # frequencies so the rollup can derive a dominant class +
                # full union from the children that actually fed in.
                "_ac_counts": {},
            }
        g = _ml_group_agg[gname]
        # Accumulate forward stats
        g["fwd_trades"] += r.get("fwd_trades", 0) or 0
        g["fwd_wins"] += r.get("fwd_wins", 0) or 0
        g["fwd_losses"] += r.get("fwd_losses", 0) or 0
        g["fwd_total_pnl"] += r.get("fwd_total_pnl", 0) or 0
        wp = r.get("fwd_avg_win", 0) or 0
        lp = r.get("fwd_avg_loss", 0) or 0
        w = r.get("fwd_wins", 0) or 0
        l = r.get("fwd_losses", 0) or 0
        g["_win_pnl"] += wp * w
        g["_loss_pnl"] += lp * l
        g["active_picks"] += r.get("active_picks", 0) or 0
        # Merge PnL series for omega/tail ratio computation
        pnl_s = _strat_picks.get(r.get("strategy", ""), [])
        g["_pnl_series"].extend(pnl_s)
        trades_s = _strat_trades.get(r.get("strategy", ""), [])
        g["_trades_series"].extend(trades_s)
        for sys in (r.get("systems", []) or []):
            g["systems"].add(sys)
        g["_child_strategies"].append(r.get("strategy", ""))
        # Inherit asset_class info from the constituent row. Prefer the
        # multi-class `asset_classes` list (already populated by the F2
        # block in _finalize_row); fall back to the dominant `asset_class`.
        # Weight each child's contribution by its trade count so the
        # group's dominant class reflects realized volume, not row count.
        _child_trades = max(int(r.get("fwd_trades") or 0), 1)
        _child_acs = r.get("asset_classes") or []
        if not _child_acs:
            _ac_single = str(r.get("asset_class") or "").upper().strip()
            if _ac_single:
                _child_acs = [_ac_single]
        for _ac in _child_acs:
            _ac_u = str(_ac).upper().strip()
            if _ac_u:
                g["_ac_counts"][_ac_u] = (
                    g["_ac_counts"].get(_ac_u, 0) + _child_trades
                )

    # Finalize ML group rows using the same helper
    for gname, g in _ml_group_agg.items():
        # Reuse the same finalization logic
        total_fwd = g["fwd_wins"] + g["fwd_losses"]
        g["fwd_wr"] = round(g["fwd_wins"] / total_fwd * 100, 1) if total_fwd > 0 else None
        g["fwd_avg_pnl"] = round(g["fwd_total_pnl"] / g["fwd_trades"], 2) if g["fwd_trades"] > 0 else 0
        g["fwd_total_pnl"] = round(g["fwd_total_pnl"], 2)
        win_pnl = g.pop("_win_pnl", 0.0)
        loss_pnl = g.pop("_loss_pnl", 0.0)
        g["fwd_avg_win"] = round(win_pnl / g["fwd_wins"], 2) if g["fwd_wins"] > 0 else 0
        g["fwd_avg_loss"] = round(abs(loss_pnl) / g["fwd_losses"], 2) if g["fwd_losses"] > 0 else 0
        g["fwd_pf"] = round(win_pnl / abs(loss_pnl), 2) if loss_pnl < 0 else None
        wr_frac = g["fwd_wr"] / 100 if g["fwd_wr"] is not None else 0
        g["fwd_expectancy"] = (
            round((wr_frac * g["fwd_avg_win"]) - ((1 - wr_frac) * g["fwd_avg_loss"]), 2)
            if total_fwd > 0 else None
        )
        g["fwd_csr"] = None
        if total_fwd >= 5 and g["fwd_wins"] > 0 and g["fwd_losses"] > 0 and g["fwd_avg_loss"] > 0:
            g["fwd_csr"] = round(
                (wr_frac * g["fwd_avg_win"]) / ((1 - wr_frac) * g["fwd_avg_loss"]), 2
            )
        # Max drawdown from combined PnL series
        pnl_series = g.pop("_pnl_series", [])
        if pnl_series:
            cum = peak = max_dd = 0.0
            for pv in pnl_series:
                cum += pv
                if cum > peak:
                    peak = cum
                dd = peak - cum
                if dd > max_dd:
                    max_dd = dd
            g["fwd_max_dd"] = round(max_dd, 2)
        else:
            g["fwd_max_dd"] = 0.0
        # Omega/tail ratios
        if len(pnl_series) >= 5:
            gains_sum = sum(pv for pv in pnl_series if pv > 0)
            losses_sum = sum(-pv for pv in pnl_series if pv < 0)
            g["omega_ratio"] = round(gains_sum / losses_sum, 2) if losses_sum > 0 else None
            pos = sorted([pv for pv in pnl_series if pv > 0])
            neg = sorted([pv for pv in pnl_series if pv < 0])
            if len(pos) >= 2 and len(neg) >= 2:
                def _pct(sorted_data, pct):
                    n = len(sorted_data)
                    k = (pct / 100.0) * (n - 1)
                    f = int(k)
                    c = f + 1 if f + 1 < n else f
                    d = k - f
                    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])
                p95 = _pct(pos, 95)
                p5 = abs(_pct(neg, 5))
                g["tail_ratio"] = round(p95 / p5, 2) if p5 > 0 else None
            else:
                g["tail_ratio"] = None
        else:
            g["omega_ratio"] = None
            g["tail_ratio"] = None
        # Sample quality
        if g["fwd_trades"] >= 20:
            g["sample_quality"] = "strong"
        elif g["fwd_trades"] >= 10:
            g["sample_quality"] = "moderate"
        elif g["fwd_trades"] >= 5:
            g["sample_quality"] = "weak"
        else:
            g["sample_quality"] = "insufficient"
        g["decay"] = None  # No BT data for ML groups
        trades_series = g.pop("_trades_series", [])
        g["fwd_last10_wr"] = round(_rolling_wr(trades_series) * 100, 1) if trades_series else None
        g["health"] = _health_score(g)
        g["systems"] = sorted(g["systems"] - {""})
        # Store child strategy count for UI
        g["ml_child_count"] = len(g.pop("_child_strategies", []))
        g["_is_ml_group"] = True
        # F2 leaderboard chips: derive dominant asset_class + full union
        # from constituent strategies. Mirrors the per-row injection in
        # _finalize_row so rollup rows are NOT missing these fields.
        _ac_counts = g.pop("_ac_counts", {}) or {}
        if _ac_counts:
            g["asset_class"] = max(
                _ac_counts.items(), key=lambda kv: kv[1]
            )[0]
            g["asset_classes"] = sorted(_ac_counts.keys())
        else:
            g["asset_class"] = ""
            g["asset_classes"] = []
        result.append(g)

    if _ml_group_agg:
        log.info(
            "ML group aggregation: %d group rows from %d ML sub-strategies",
            len(_ml_group_agg),
            sum(g.get("ml_child_count", 0) for g in _ml_group_agg.values()),
        )

    # PR-F (2026-05-12): mark + demote blacklisted strategies in leaderboard.
    # Memory ref `feedback_gate_at_execution_not_generation` — gate-at-intake
    # alone doesn't prevent the dashboard from crowning a blacklisted strategy
    # via historical leaderboard data. We preserve the row (data integrity) but
    # set `is_blacklisted=True` + push to the bottom of the sort.
    try:
        from alpha_engine.config import BLACKLISTED_STRATEGIES as _BLACKLISTED_STRATEGIES
    except Exception:
        _BLACKLISTED_STRATEGIES = ()
    _BLACKLIST_SET = {s.lower() for s in _BLACKLISTED_STRATEGIES}
    for row in result:
        name = (row.get("strategy") or "").lower()
        if name in _BLACKLIST_SET:
            row["is_blacklisted"] = True

    # Sort by: not-blacklisted first, then forward-tested first, then fwd_wr desc, then bt_wr desc
    result.sort(
        key=lambda x: (
            not x.get("is_blacklisted"),  # blacklisted -> False -> bottom
            x["fwd_trades"] > 0,
            x["fwd_wr"] or 0,
            x["bt_wr"] or 0,
        ),
        reverse=True,
    )

    log.info(
        "Strategy leaderboard: %d strategies (%d with forward data, %d blacklisted demoted)",
        len(result),
        sum(1 for r in result if r["fwd_trades"] > 0),
        sum(1 for r in result if r.get("is_blacklisted")),
    )
    return result


def collect_bundles():
    """Read baby strat bundles from battleground dashboard."""
    data = _safe_json(ROOT / "battleground/data/baby_strats_dashboard.json")
    if not data:
        return []
    for section in data.get("sections", []):
        if section.get("section") == "BUNDLE_BABIES_TOP":
            return section.get("bundles", [])
    return []


def collect_consensus_analysis(active, closed):
    """Analyze which strategy combinations / consensus signals produce the best results.

    Returns:
      - consensus_picks: active picks where 2+ systems agree on symbol+direction
      - algo_consensus_stats: which algorithm combos correlate with wins
      - symbol_performance: per-symbol win rate across all strategies
      - holding_period_analysis: best holding periods by strategy/symbol
    """
    # === Consensus picks (active): where multiple systems agree ===
    from collections import defaultdict

    symbol_dir = defaultdict(list)  # (normalized_symbol, direction) -> [pick, ...]
    for p in active:
        norm_sym = _normalize_symbol(p.get("symbol", ""))
        key = (norm_sym, p.get("direction", "BUY"))
        symbol_dir[key].append(p)

    consensus_picks = []
    for (sym, direction), picks in symbol_dir.items():
        if not sym:
            continue
        # Count unique SYSTEMS, not picks (one system with 10 picks = 1 agreement)
        systems = list(set(p.get("source_system", "") for p in picks) - {""})
        if len(systems) < 2:
            continue
        strategies = list(
            set(p.get("strategy", "") for p in picks if p.get("strategy"))
        )
        avg_conf = sum(_float(p.get("confidence", 0.5)) for p in picks) / len(picks)
        consensus_picks.append(
            {
                "symbol": sym,
                "direction": direction,
                "agreement_count": len(systems),  # unique systems, not pick count
                "systems": systems,
                "strategies": strategies,
                "avg_confidence": round(avg_conf, 3),
                "certainty": "VERY HIGH"
                if len(systems) >= 4
                else "HIGH"
                if len(systems) >= 3
                else "MODERATE",
            }
        )
    consensus_picks.sort(key=lambda x: x["agreement_count"], reverse=True)

    # === Algorithm consensus stats (from closed trades): which combos win ===
    # Group closed trades by normalized symbol to find where multiple algos agreed
    # Filter out expired picks with no PnL data (not real resolved trades)
    resolved_closed = _filter_valid_resolved_picks(closed)
    sym_closed = defaultdict(list)
    for p in resolved_closed:
        sym = _normalize_symbol(p.get("symbol", ""))
        if sym:
            sym_closed[sym].append(p)

    algo_combo_wins = defaultdict(lambda: {"wins": 0, "total": 0, "pnl": 0.0})
    for sym, trades in sym_closed.items():
        if len(trades) < 2:
            continue
        strategies = sorted(
            set(t.get("strategy", "") for t in trades if t.get("strategy"))
        )
        if len(strategies) < 2:
            continue
        combo_key = " + ".join(strategies[:4])  # Cap at 4 for readability
        for t in trades:
            algo_combo_wins[combo_key]["total"] += 1
            pnl = _float(t.get("pnl_pct", 0))
            algo_combo_wins[combo_key]["pnl"] += pnl
            if pnl > 0:
                algo_combo_wins[combo_key]["wins"] += 1

    algo_consensus_stats = []
    for combo, stats in algo_combo_wins.items():
        if stats["total"] >= 3:
            wr = round(stats["wins"] / stats["total"] * 100, 1)
            algo_consensus_stats.append(
                {
                    "combo": combo,
                    "trades": stats["total"],
                    "wins": stats["wins"],
                    "win_rate": wr,
                    "total_pnl": round(stats["pnl"], 2),
                }
            )
    algo_consensus_stats.sort(key=lambda x: x["win_rate"], reverse=True)

    # === Per-symbol performance ===
    sym_perf = defaultdict(
        lambda: {"wins": 0, "losses": 0, "pnl": 0.0, "strategies": set()}
    )
    for p in resolved_closed:
        sym = _normalize_symbol(p.get("symbol", ""))
        if not sym:
            continue
        pnl = _float(float(p.get("pnl_pct", 0) or 0))
        sp = sym_perf[sym]
        sp["pnl"] += pnl
        sp["strategies"].add(p.get("strategy", ""))
        if pnl > 0:
            sp["wins"] += 1
        elif pnl < 0:
            sp["losses"] += 1

    symbol_performance = []
    for sym, sp in sym_perf.items():
        total = sp["wins"] + sp["losses"]
        if total < 2:
            continue
        symbol_performance.append(
            {
                "symbol": sym,
                "trades": total,
                "wins": sp["wins"],
                "win_rate": round(sp["wins"] / total * 100, 1),
                "total_pnl": round(sp["pnl"], 2),
                "strategy_count": len(sp["strategies"] - {""}),
            }
        )
    symbol_performance.sort(key=lambda x: x["win_rate"], reverse=True)

    # === Best holding period analysis ===
    holding_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0})
    for p in resolved_closed:
        ts_str = p.get("timestamp", "")
        exit_str = p.get(
            "exit_timestamp",
            p.get("closed_at", p.get("exit_time_est", p.get("exit_date", ""))),
        )
        if not ts_str or not exit_str:
            continue
        try:
            ts_open = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            ts_close = datetime.fromisoformat(exit_str.replace("Z", "+00:00"))
            hours = (ts_close - ts_open).total_seconds() / 3600
            bucket = (
                "<1h"
                if hours < 1
                else "1-4h"
                if hours < 4
                else "4-12h"
                if hours < 12
                else "12-24h"
                if hours < 24
                else "1-3d"
                if hours < 72
                else "3-7d"
                if hours < 168
                else "7d+"
            )
            pnl = _float(float(p.get("pnl_pct", 0) or 0))
            hs = holding_stats[bucket]
            hs["pnl"] += pnl
            if pnl > 0:
                hs["wins"] += 1
            else:
                hs["losses"] += 1
        except Exception:
            continue

    holding_analysis = []
    for bucket, hs in holding_stats.items():
        total = hs["wins"] + hs["losses"]
        if total < 2:
            continue
        holding_analysis.append(
            {
                "period": bucket,
                "trades": total,
                "wins": hs["wins"],
                "win_rate": round(hs["wins"] / total * 100, 1),
                "avg_pnl": round(hs["pnl"] / total, 2),
            }
        )

    log.info(
        "Consensus: %d consensus picks, %d algo combos, %d symbols, %d holding periods",
        len(consensus_picks),
        len(algo_consensus_stats),
        len(symbol_performance),
        len(holding_analysis),
    )

    return {
        "consensus_picks": consensus_picks[:50],
        "algo_consensus_stats": algo_consensus_stats[:30],
        "symbol_performance": symbol_performance[:50],
        "holding_period_analysis": holding_analysis,
    }


def collect_volatility_tracking(active, closed):
    """Track extreme volatility moves and potential rug pulls across all picks.

    Returns alerts for:
      - Extreme pumps (>30% gain from entry)
      - Potential rug pulls (>20% drop on meme/penny coins)
      - High volatility movers (>10% move either direction)
    """
    alerts = []
    volatile_movers = []
    # P2: metric-grade closed rows only (same gate as _filter_valid_resolved_picks)
    _closed_vol = _filter_valid_resolved_picks(closed)

    for p in active + _closed_vol:
        sym = p.get("symbol", "")
        entry = _float(p.get("entry_price", 0))
        current = _float(p.get("current_price", p.get("exit_price", 0)))
        if not sym or not entry or not current:
            continue
        pnl_pct = ((current - entry) / entry) * 100
        abs_move = abs(pnl_pct)
        strat = p.get("strategy", "")
        source = p.get("source_system", "")
        is_meme = any(
            kw in strat.lower() for kw in ["meme", "pump", "velocity", "penny"]
        )
        is_meme = is_meme or any(
            kw in sym.upper()
            for kw in ["DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME"]
        )

        if abs_move > 10:
            volatile_movers.append(
                {
                    "symbol": sym,
                    "strategy": strat,
                    "source": source,
                    "entry_price": entry,
                    "current_price": current,
                    "pnl_pct": round(pnl_pct, 2),
                    "status": p.get("status", "OPEN"),
                    "is_meme": is_meme,
                }
            )

        # Rug pull alert: meme/penny coin dropped >20%
        if pnl_pct < -20 and is_meme:
            alerts.append(
                {
                    "type": "RUG_PULL",
                    "severity": "HIGH" if pnl_pct < -40 else "MEDIUM",
                    "symbol": sym,
                    "strategy": strat,
                    "pnl_pct": round(pnl_pct, 2),
                    "entry_price": entry,
                    "current_price": current,
                }
            )
        # Extreme pump alert: >50% gain (potential manipulation)
        elif pnl_pct > 50:
            alerts.append(
                {
                    "type": "EXTREME_PUMP",
                    "severity": "HIGH" if pnl_pct > 100 else "MEDIUM",
                    "symbol": sym,
                    "strategy": strat,
                    "pnl_pct": round(pnl_pct, 2),
                    "entry_price": entry,
                    "current_price": current,
                }
            )

    volatile_movers.sort(key=lambda x: abs(x["pnl_pct"]), reverse=True)
    alerts.sort(key=lambda x: abs(x["pnl_pct"]), reverse=True)

    log.info(
        "Volatility: %d alerts, %d volatile movers (>10%% move)",
        len(alerts),
        len(volatile_movers),
    )
    return {
        "alerts": alerts[:30],
        "volatile_movers": volatile_movers[:50],
    }


def collect_cross_system_permutations(active, closed):
    """Track cross-system permutation portfolios and their performance.

    This analyzes which combinations of systems (solo, pairs, triplets, etc.)
    are performing best in forward testing.
    """
    from collections import defaultdict

    # Define the system permutations we want to track
    PERMUTATIONS = {
        # Solo systems
        "solo_alpha": {
            "name": "Solo: Alpha Engine",
            "systems": ["alpha_engine"],
            "min_agree": 1,
        },
        "solo_battleground": {
            "name": "Solo: Battleground",
            "systems": ["battleground"],
            "min_agree": 1,
        },
        "solo_rapid_fire": {
            "name": "Solo: Rapid Fire",
            "systems": ["rapid_fire"],
            "min_agree": 1,
        },
        "solo_kimi": {
            "name": "Solo: KIMI Signals",
            "systems": ["kimi_signal_tracking"],
            "min_agree": 1,
        },
        "solo_claude": {
            "name": "Solo: Claude Gainer",
            "systems": ["claude_gainer_ml_perf"],
            "min_agree": 1,
        },
        "solo_crypto_ml": {
            "name": "Solo: Crypto ML Edge",
            "systems": ["crypto_ml_edge"],
            "min_agree": 1,
        },
        # Pairs
        "pair_alpha_battle": {
            "name": "Pair: Alpha + Battleground",
            "systems": ["alpha_engine", "battleground"],
            "min_agree": 2,
        },
        "pair_alpha_kimi": {
            "name": "Pair: Alpha + KIMI",
            "systems": ["alpha_engine", "kimi_signal_tracking"],
            "min_agree": 2,
        },
        "pair_battle_kimi": {
            "name": "Pair: Battleground + KIMI",
            "systems": ["battleground", "kimi_signal_tracking"],
            "min_agree": 2,
        },
        "pair_alpha_claude": {
            "name": "Pair: Alpha + Claude",
            "systems": ["alpha_engine", "claude_gainer_ml_perf"],
            "min_agree": 2,
        },
        # Triplets
        "triple_alpha_battle_kimi": {
            "name": "Triple: Alpha + Battle + KIMI",
            "systems": ["alpha_engine", "battleground", "kimi_signal_tracking"],
            "min_agree": 3,
        },
        "triple_alpha_kimi_claude": {
            "name": "Triple: Alpha + KIMI + Claude",
            "systems": [
                "alpha_engine",
                "kimi_signal_tracking",
                "claude_gainer_ml_perf",
            ],
            "min_agree": 3,
        },
        # Flexible consensus
        "flex_2of3_alpha_battle_kimi": {
            "name": "Flex 2/3: Alpha/Battle/KIMI",
            "systems": ["alpha_engine", "battleground", "kimi_signal_tracking"],
            "min_agree": 2,
        },
    }

    # Calculate performance for each permutation
    permutation_stats = {}

    for perm_id, config in PERMUTATIONS.items():
        stats = {
            "id": perm_id,
            "name": config["name"],
            "systems": config["systems"],
            "min_agreement": config["min_agree"],
            "active_picks": [],
            "closed_picks": [],
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
            "profit_factor": None,
        }

        target_systems = set(config["systems"])
        min_agree = config["min_agree"]

        # Analyze active picks
        for pick in active:
            pick_systems = set(pick.get("source_systems", []))
            if not pick_systems:
                pick_systems = {pick.get("source_system", "unknown")}

            # Count how many target systems are in this pick
            agreement = len(pick_systems.intersection(target_systems))

            if agreement >= min_agree:
                stats["active_picks"].append(
                    {
                        "symbol": pick.get("symbol"),
                        "direction": pick.get("direction"),
                        "systems": list(pick_systems),
                        "agreement_count": agreement,
                        "confidence": pick.get("confidence"),
                        "pnl_pct": pick.get("pnl_pct"),
                    }
                )

        # Analyze closed picks (skip auto-expired with no real PnL)
        for pick in closed:
            if pick.get("expired_no_pnl") or pick.get("_auto_expired"):
                continue
            pick_systems = set(pick.get("source_systems", []))
            if not pick_systems:
                pick_systems = {pick.get("source_system", "unknown")}

            agreement = len(pick_systems.intersection(target_systems))

            if agreement >= min_agree:
                pnl = pick.get("pnl_pct", 0)
                stats["closed_picks"].append(
                    {
                        "symbol": pick.get("symbol"),
                        "direction": pick.get("direction"),
                        "systems": list(pick_systems),
                        "agreement_count": agreement,
                        "pnl_pct": pnl,
                        "exit_reason": pick.get("exit_reason"),
                    }
                )
                stats["total_trades"] += 1
                stats["total_pnl"] += pnl
                if pnl > 0:
                    stats["wins"] += 1
                else:
                    stats["losses"] += 1

        # Calculate derived metrics
        if stats["total_trades"] > 0:
            stats["win_rate"] = round(stats["wins"] / stats["total_trades"] * 100, 1)
            stats["avg_pnl"] = round(stats["total_pnl"] / stats["total_trades"], 2)

        # Calculate profit factor
        win_pnl = sum(p["pnl_pct"] for p in stats["closed_picks"] if p["pnl_pct"] > 0)
        loss_pnl = abs(
            sum(p["pnl_pct"] for p in stats["closed_picks"] if p["pnl_pct"] < 0)
        )
        if loss_pnl > 0:
            stats["profit_factor"] = round(win_pnl / loss_pnl, 2)

        permutation_stats[perm_id] = stats

    # Calculate trust scores
    for perm_id, stats in permutation_stats.items():
        score = 0
        if stats["total_trades"] >= 10:
            score += min(40, stats["win_rate"] * 0.4)
            score += min(30, max(0, stats["total_pnl"]) * 1.5)
            score += min(20, stats["total_trades"] * 0.2)
            if stats["profit_factor"] and stats["profit_factor"] > 1:
                score += 10
        stats["trust_score"] = round(score, 1)
        stats["trust_tier"] = (
            "Highly Trusted"
            if score >= 70
            else "Trusted"
            if score >= 50
            else "Promising"
            if score >= 30
            else "Unproven"
            if stats["total_trades"] < 10
            else "Untrustworthy"
        )

    # Sort by trust score
    sorted_perms = sorted(
        permutation_stats.values(), key=lambda x: x["trust_score"], reverse=True
    )

    log.info(
        "Cross-system permutations: %d tracked, top trust score: %.1f",
        len(sorted_perms),
        sorted_perms[0]["trust_score"] if sorted_perms else 0,
    )

    return {
        "permutations": sorted_perms,
        "summary": {
            "total_tracked": len(sorted_perms),
            "highly_trusted": sum(1 for p in sorted_perms if p["trust_score"] >= 70),
            "trusted": sum(1 for p in sorted_perms if 50 <= p["trust_score"] < 70),
            "with_trades": sum(1 for p in sorted_perms if p["total_trades"] > 0),
        },
    }


def collect_cross_strategy_permutations(active, closed):
    """Track cross-strategy permutation portfolios and their performance.

    This analyzes which combinations of strategies (solo, pairs, triplets, etc.)
    are performing best in forward testing.
    """

    def _flatten_strategy_names(value) -> list[str]:
        names = []

        def _walk(item):
            if isinstance(item, dict):
                for child in item.values():
                    _walk(child)
                return
            if isinstance(item, (list, tuple, set)):
                for child in item:
                    _walk(child)
                return
            if item in (None, ""):
                return
            text = str(item).strip()
            if text:
                names.append(text)

        _walk(value)
        return names

    # Define strategy permutations to track
    STRATEGY_PERMUTATIONS = {
        # Solo strategies - top performers
        "solo_ema_stack": {
            "name": "Solo: EMA Stack",
            "strategies": ["ema_stack"],
            "min_agree": 1,
            "category": "trend",
        },
        "solo_macd": {
            "name": "Solo: MACD Crossover",
            "strategies": ["macd_crossover"],
            "min_agree": 1,
            "category": "trend",
        },
        "solo_stochrsi": {
            "name": "Solo: StochRSI MACD",
            "strategies": ["stochrsi_macd_combo"],
            "min_agree": 1,
            "category": "momentum",
        },
        "solo_volume_breakout": {
            "name": "Solo: Volume Breakout",
            "strategies": ["volume_spike_breakout"],
            "min_agree": 1,
            "category": "breakout",
        },
        "solo_bollinger": {
            "name": "Solo: Bollinger Squeeze",
            "strategies": ["bollinger_squeeze"],
            "min_agree": 1,
            "category": "volatility",
        },
        "solo_irb": {
            "name": "Solo: IRB Hoffman",
            "strategies": ["irb_hoffman"],
            "min_agree": 1,
            "category": "prop_firm",
        },
        # Strategy pairs - confluence
        "pair_trend_momentum": {
            "name": "Pair: Trend + Momentum",
            "strategies": ["ema_stack", "macd_crossover", "stochrsi_macd_combo"],
            "min_agree": 2,
            "category": "confluence",
        },
        "pair_breakout_volatility": {
            "name": "Pair: Breakout + Volatility",
            "strategies": ["volume_spike_breakout", "bollinger_squeeze"],
            "min_agree": 2,
            "category": "confluence",
        },
        "pair_prop_tech": {
            "name": "Pair: Prop + Technical",
            "strategies": ["irb_hoffman", "ema_stack", "macd_crossover"],
            "min_agree": 2,
            "category": "confluence",
        },
        # Category combinations
        "cat_trend_following": {
            "name": "Category: All Trend",
            "strategies": [
                "ema_stack",
                "macd_crossover",
                "hma_trend",
                "triple_confirmation",
            ],
            "min_agree": 1,
            "category": "category",
        },
        "cat_mean_reversion": {
            "name": "Category: All Mean Rev",
            "strategies": [
                "rsi_bounce",
                "stochrsi_macd_combo",
                "williams_r_reversion",
                "vwap_reversion",
            ],
            "min_agree": 1,
            "category": "category",
        },
        "cat_breakout": {
            "name": "Category: All Breakout",
            "strategies": [
                "volume_spike_breakout",
                "bollinger_squeeze",
                "generic_volatility_breakout",
            ],
            "min_agree": 1,
            "category": "category",
        },
        # Strict confluence - must agree
        "conf_2strat_any": {
            "name": "Confluence: Any 2 Strategies",
            "strategies": [
                "ema_stack",
                "macd_crossover",
                "rsi_bounce",
                "volume_spike_breakout",
                "irb_hoffman",
            ],
            "min_agree": 2,
            "category": "strict",
        },
        "conf_2strat_trend": {
            "name": "Confluence: 2 Trend Agree",
            "strategies": ["ema_stack", "macd_crossover", "hma_trend"],
            "min_agree": 2,
            "category": "strict",
        },
        # ML + Technical
        "ml_plus_tech": {
            "name": "ML + Technical",
            "strategies": ["enhanced_ml_A_xgboost", "ema_stack", "macd_crossover"],
            "min_agree": 2,
            "category": "hybrid",
        },
    }

    # Calculate performance for each permutation
    permutation_stats = {}

    for perm_id, config in STRATEGY_PERMUTATIONS.items():
        stats = {
            "id": perm_id,
            "name": config["name"],
            "strategies": config["strategies"],
            "category": config["category"],
            "min_agreement": config["min_agree"],
            "active_picks": [],
            "closed_picks": [],
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
            "profit_factor": None,
        }

        target_strategies = set(config["strategies"])
        min_agree = config["min_agree"]

        # Analyze active picks
        for pick in active:
            pick_strategy_names = _flatten_strategy_names(pick.get("strategy", ""))
            pick_strategy = pick_strategy_names[0] if pick_strategy_names else ""
            # Check if this pick's strategy is in the target set
            if pick_strategy in target_strategies:
                stats["active_picks"].append(
                    {
                        "symbol": pick.get("symbol"),
                        "direction": pick.get("direction"),
                        "strategy": pick_strategy,
                        "confidence": pick.get("confidence"),
                        "pnl_pct": pick.get("pnl_pct"),
                    }
                )
            # For confluence strategies, also check agreement count
            pick_strategies = _flatten_strategy_names(pick.get("source_strategies", []))
            if not pick_strategies:
                pick_strategies = _flatten_strategy_names(
                    pick.get("confluence_strategies", [])
                )
            if not pick_strategies and pick_strategy:
                pick_strategies = [pick_strategy]

            agreement = len(set(pick_strategies).intersection(target_strategies))
            if (
                config["category"] in ["confluence", "strict", "hybrid"]
                and agreement >= min_agree
            ):
                if pick not in stats["active_picks"]:  # Avoid duplicates
                    stats["active_picks"].append(
                        {
                            "symbol": pick.get("symbol"),
                            "direction": pick.get("direction"),
                            "strategies": pick_strategies,
                            "agreement_count": agreement,
                            "confidence": pick.get("confidence"),
                            "pnl_pct": pick.get("pnl_pct"),
                        }
                    )

        # Analyze closed picks (skip auto-expired with no real PnL)
        for pick in closed:
            if pick.get("expired_no_pnl") or pick.get("_auto_expired"):
                continue
            pick_strategy_names = _flatten_strategy_names(pick.get("strategy", ""))
            pick_strategy = pick_strategy_names[0] if pick_strategy_names else ""
            pick_strategies = _flatten_strategy_names(pick.get("source_strategies", []))
            if not pick_strategies:
                pick_strategies = _flatten_strategy_names(
                    pick.get("confluence_strategies", [])
                )
            if not pick_strategies and pick_strategy:
                pick_strategies = [pick_strategy]

            # For solo strategies
            if config["category"] == "trend" and pick_strategy in target_strategies:
                pnl = pick.get("pnl_pct", 0)
                stats["closed_picks"].append(
                    {
                        "symbol": pick.get("symbol"),
                        "direction": pick.get("direction"),
                        "strategy": pick_strategy,
                        "pnl_pct": pnl,
                    }
                )
                stats["total_trades"] += 1
                stats["total_pnl"] += pnl
                _bucket = _outcome_bucket_from_pnl(pnl)
                if _bucket == "win":
                    stats["wins"] += 1
                elif _bucket == "loss":
                    stats["losses"] += 1
            # For confluence/category strategies
            elif config["category"] in ["confluence", "strict", "hybrid", "category"]:
                agreement = len(set(pick_strategies).intersection(target_strategies))
                if agreement >= min_agree:
                    pnl = pick.get("pnl_pct", 0)
                    stats["closed_picks"].append(
                        {
                            "symbol": pick.get("symbol"),
                            "direction": pick.get("direction"),
                            "strategies": pick_strategies,
                            "agreement_count": agreement,
                            "pnl_pct": pnl,
                        }
                    )
                    stats["total_trades"] += 1
                    stats["total_pnl"] += pnl
                    _bucket = _outcome_bucket_from_pnl(pnl)
                    if _bucket == "win":
                        stats["wins"] += 1
                    elif _bucket == "loss":
                        stats["losses"] += 1

        # Calculate derived metrics
        if stats["total_trades"] > 0:
            stats["win_rate"] = round(stats["wins"] / stats["total_trades"] * 100, 1)
            stats["avg_pnl"] = round(stats["total_pnl"] / stats["total_trades"], 2)

        # Calculate profit factor
        win_pnl = sum(p["pnl_pct"] for p in stats["closed_picks"] if p["pnl_pct"] > 0)
        loss_pnl = abs(
            sum(p["pnl_pct"] for p in stats["closed_picks"] if p["pnl_pct"] < 0)
        )
        if loss_pnl > 0:
            stats["profit_factor"] = round(win_pnl / loss_pnl, 2)

        permutation_stats[perm_id] = stats

    # Calculate trust scores
    for perm_id, stats in permutation_stats.items():
        score = 0
        if stats["total_trades"] >= 10:
            score += min(40, stats["win_rate"] * 0.4)
            score += min(30, max(0, stats["total_pnl"]) * 1.5)
            score += min(20, stats["total_trades"] * 0.2)
            if stats["profit_factor"] and stats["profit_factor"] > 1:
                score += 10
        stats["trust_score"] = round(score, 1)
        stats["trust_tier"] = (
            "Highly Trusted"
            if score >= 70
            else "Trusted"
            if score >= 50
            else "Promising"
            if score >= 30
            else "Unproven"
            if stats["total_trades"] < 10
            else "Untrustworthy"
        )

    # Sort by trust score
    sorted_perms = sorted(
        permutation_stats.values(), key=lambda x: x["trust_score"], reverse=True
    )

    # Group by category
    by_category = defaultdict(list)
    for p in sorted_perms:
        by_category[p["category"]].append(p)

    log.info(
        "Cross-strategy permutations: %d tracked, top trust score: %.1f",
        len(sorted_perms),
        sorted_perms[0]["trust_score"] if sorted_perms else 0,
    )

    return {
        "permutations": sorted_perms,
        "by_category": dict(by_category),
        "summary": {
            "total_tracked": len(sorted_perms),
            "highly_trusted": sum(1 for p in sorted_perms if p["trust_score"] >= 70),
            "trusted": sum(1 for p in sorted_perms if 50 <= p["trust_score"] < 70),
            "with_trades": sum(1 for p in sorted_perms if p["total_trades"] > 0),
        },
    }


def collect_predictions_leaderboard():
    """Read analyst/predictor leaderboard from the predictions engine.

    Returns top analysts sorted by win rate, including platform and tier data.
    Also loads claude_gainer_ml performance summary.
    """
    analysts = []

    # Source 1: predictions/data/leaderboard.json
    lb = _safe_json(ROOT / "predictions/data/leaderboard.json")
    if lb:
        for entry in lb.get("leaderboard", []):
            if not isinstance(entry, dict):
                continue
            analysts.append(
                {
                    "predictor_id": entry.get("predictor_id", ""),
                    "platform": entry.get("platform", ""),
                    "display_name": entry.get("display_name", ""),
                    "total_predictions": entry.get("total_predictions", 0),
                    "wins": entry.get("wins", 0),
                    "losses": entry.get("losses", 0),
                    "win_rate": round(_float(entry.get("win_rate", 0)) * 100, 1)
                    if _float(entry.get("win_rate", 0)) <= 1.0
                    else round(_float(entry.get("win_rate", 0)), 1),
                    "avg_pnl_pct": round(_float(entry.get("avg_pnl_pct", 0)), 2),
                    "sharpe": round(_cap_sharpe(entry.get("sharpe", 0)), 2),
                    "tier": entry.get("tier", ""),
                    "first_seen": entry.get("first_seen", ""),
                    "last_active": entry.get("last_active", ""),
                    "source": "predictions_engine",
                }
            )

    # Source 2: claude_gainer_ml/tracker/claude_performance.json
    cg_perf = _safe_json(ROOT / "claude_gainer_ml/tracker/claude_performance.json")
    if cg_perf:
        analysts.append(
            {
                "predictor_id": "claude_gainer_ml",
                "platform": "ml_model",
                "display_name": "Claude Gainer ML",
                "total_predictions": cg_perf.get("total_picks", 0),
                "wins": cg_perf.get("total_wins", 0),
                "losses": cg_perf.get("total_losses", 0),
                "win_rate": round(_float(cg_perf.get("win_rate", 0)), 1),
                "avg_pnl_pct": round(_float(cg_perf.get("avg_pnl_pct", 0)), 2),
                "sharpe": round(_cap_sharpe(cg_perf.get("sharpe_ratio", 0)), 2),
                "profit_factor": cg_perf.get("profit_factor"),
                "max_drawdown": cg_perf.get("max_drawdown_pct"),
                "tier": "ML_MODEL",
                "source": "claude_gainer_ml",
            }
        )

    # Sort by win rate descending
    analysts.sort(key=lambda x: x.get("win_rate", 0), reverse=True)
    log.info("Predictions leaderboard: %d analysts/predictors", len(analysts))
    return analysts


# ── Regime Validation (Mercury's checklist) ──


def compute_regime_validation(active: list, closed: list) -> dict:
    """
    Compute Mercury's regime validation metrics from pick data.

    Checks:
      1. Signal-to-Trade Ratio: picks generated vs picks surviving regime filter
      2. Regime-Specific WR: WR per canonical regime
      3. Alignment uplift: WR for regime-aligned vs regime-misaligned picks

    Closed picks carry regime metadata if processed by regime_meta_router:
      - regime_alignment: 'aligned' | 'misaligned' | 'neutral'
      - consensus_regime: the regime at entry time
      - regime_score_adj: confidence adjustment applied
      - regime_at_entry: (alpha_engine picks) regime label at entry
    """
    CANONICAL = ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "HIGH_VOLATILITY", "CRASH"]

    # ── 1. Regime-Specific WR breakdown ──
    regime_wr = {}
    for regime in CANONICAL:
        regime_wr[regime] = {"wins": 0, "losses": 0, "total": 0, "win_rate": 0.0}

    picks_with_regime = 0
    picks_without_regime = 0

    for pick in closed:
        if not _is_valid_resolved_pick(pick):
            continue
        regime = (
            pick.get("consensus_regime")
            or (pick.get("regime_at_entry") or "").upper()
            or None
        )
        if regime and regime not in CANONICAL:
            regime_map = {
                "BULL": "TRENDING_UP",
                "BULLISH": "TRENDING_UP",
                "BEAR": "TRENDING_DOWN",
                "BEARISH": "TRENDING_DOWN",
                "NEUTRAL": "RANGING",
                "RANGE": "RANGING",
                "RANGE_BOUND": "RANGING",
                "VOLATILE": "HIGH_VOLATILITY",
                "HIGH_VOL": "HIGH_VOLATILITY",
                "CRASH": "CRASH",
            }
            regime = regime_map.get(regime, None)

        if not regime or regime not in CANONICAL:
            picks_without_regime += 1
            continue

        picks_with_regime += 1
        pnl = float(pick.get("pnl_pct", 0) or 0)

        bucket = regime_wr[regime]
        bucket["total"] += 1
        if pnl > 0:
            bucket["wins"] += 1
        elif pnl < 0:
            bucket["losses"] += 1

    for regime in CANONICAL:
        b = regime_wr[regime]
        b["win_rate"] = (
            round(b["wins"] / b["total"] * 100, 1) if b["total"] > 0 else 0.0
        )

    # ── 2. Alignment uplift: aligned vs misaligned WR ──
    aligned_wins = 0
    aligned_losses = 0
    misaligned_wins = 0
    misaligned_losses = 0
    neutral_wins = 0
    neutral_losses = 0
    picks_with_alignment = 0

    for pick in closed:
        if not _is_valid_resolved_pick(pick):
            continue
        alignment = pick.get("regime_alignment")
        if not alignment:
            continue
        picks_with_alignment += 1
        pnl = float(pick.get("pnl_pct", 0) or 0)

        if alignment == "aligned":
            if pnl > 0:
                aligned_wins += 1
            elif pnl < 0:
                aligned_losses += 1
        elif alignment == "misaligned":
            if pnl > 0:
                misaligned_wins += 1
            elif pnl < 0:
                misaligned_losses += 1
        else:
            if pnl > 0:
                neutral_wins += 1
            elif pnl < 0:
                neutral_losses += 1

    aligned_total = aligned_wins + aligned_losses
    misaligned_total = misaligned_wins + misaligned_losses
    neutral_total = neutral_wins + neutral_losses

    aligned_wr = (
        round(aligned_wins / aligned_total * 100, 1) if aligned_total > 0 else 0.0
    )
    misaligned_wr = (
        round(misaligned_wins / misaligned_total * 100, 1)
        if misaligned_total > 0
        else 0.0
    )
    neutral_wr = (
        round(neutral_wins / neutral_total * 100, 1) if neutral_total > 0 else 0.0
    )

    alignment_uplift = (
        round(aligned_wr - misaligned_wr, 1)
        if (aligned_total > 0 and misaligned_total > 0)
        else None
    )

    # ── 3. Signal reduction rate ──
    active_with_regime = sum(1 for p in active if p.get("regime_alignment"))
    active_aligned = sum(1 for p in active if p.get("regime_alignment") == "aligned")
    active_misaligned = sum(
        1 for p in active if p.get("regime_alignment") == "misaligned"
    )
    active_neutral = sum(1 for p in active if p.get("regime_alignment") == "neutral")

    total_active = len(active)
    signal_reduction_pct = (
        round(active_misaligned / total_active * 100, 1) if total_active > 0 else 0.0
    )

    # ── Mercury validation checks ──
    mercury_checks = {
        "signal_to_trade_ratio": {
            "description": "Signal-to-Trade Ratio: ~30% drop while WR improves >=5pp",
            "misaligned_pct": signal_reduction_pct,
            "target_pct": 30.0,
            "aligned_wr": aligned_wr,
            "misaligned_wr": misaligned_wr,
            "wr_improvement_pp": alignment_uplift,
            "target_wr_improvement_pp": 5.0,
            "pass": (alignment_uplift is not None and alignment_uplift >= 5.0)
            if alignment_uplift is not None
            else None,
        },
        "regime_specific_wr": {
            "description": "Regime-Specific WR: RANGING >55%, HIGH_VOLATILITY >50%",
            "ranging_wr": regime_wr["RANGING"]["win_rate"],
            "ranging_trades": regime_wr["RANGING"]["total"],
            "ranging_pass": regime_wr["RANGING"]["win_rate"] > 55.0
            if regime_wr["RANGING"]["total"] >= 5
            else None,
            "high_vol_wr": regime_wr["HIGH_VOLATILITY"]["win_rate"],
            "high_vol_trades": regime_wr["HIGH_VOLATILITY"]["total"],
            "high_vol_pass": regime_wr["HIGH_VOLATILITY"]["win_rate"] > 50.0
            if regime_wr["HIGH_VOLATILITY"]["total"] >= 5
            else None,
        },
        "max_dd_reduction": {
            "description": "Max-DD rolling 30d should shrink >=15%",
            "status": "PENDING",
            "note": "Requires rolling 30-day PnL time series; computed when enough daily data accumulates",
        },
    }

    # ── Data coverage assessment ──
    data_coverage = {
        "closed_with_regime": picks_with_regime,
        "closed_without_regime": picks_without_regime,
        "closed_with_alignment": picks_with_alignment,
        "closed_total": len(closed),
        "coverage_pct": round(picks_with_regime / len(closed) * 100, 1)
        if closed
        else 0.0,
        "alignment_coverage_pct": round(picks_with_alignment / len(closed) * 100, 1)
        if closed
        else 0.0,
        "enrichment_note": (
            "Picks need 'consensus_regime' and 'regime_alignment' fields at entry time. "
            "The regime_meta_router (score_picks_by_regime) adds these to active picks in the aggregator. "
            "For historical closed picks, 'regime_at_entry' from alpha_engine DB is used as fallback. "
            "Going forward, ensure all systems persist these fields when closing picks."
        )
        if picks_without_regime > picks_with_regime
        else None,
    }

    log.info(
        "Regime validation: %d/%d closed picks have regime data (%.1f%% coverage)",
        picks_with_regime,
        len(closed),
        data_coverage["coverage_pct"],
    )

    return {
        "regime_wr_breakdown": regime_wr,
        "alignment_uplift": {
            "aligned_wr": aligned_wr,
            "aligned_trades": aligned_total,
            "misaligned_wr": misaligned_wr,
            "misaligned_trades": misaligned_total,
            "neutral_wr": neutral_wr,
            "neutral_trades": neutral_total,
            "uplift_pp": alignment_uplift,
        },
        "signal_reduction_pct": signal_reduction_pct,
        "active_regime_composition": {
            "total": total_active,
            "with_regime_data": active_with_regime,
            "aligned": active_aligned,
            "misaligned": active_misaligned,
            "neutral": active_neutral,
        },
        "mercury_checks": mercury_checks,
        "data_coverage": data_coverage,
    }


def compute_non_crypto_performance(active: list, closed: list) -> dict:
    """Compute non-crypto aggregate/category metrics from active + resolved closed picks."""

    categories = ("FOREX", "EQUITY", "STOCK", "COMMODITY", "FUTURES", "BOND", "ETF")

    stats = {
        c: {
            "active": 0,
            "closed": 0,
            "wins": 0,
            "losses": 0,
            "flat": 0,
            "resolved": 0,
            "win_rate": None,
            "total_pnl_pct": 0.0,
        }
        for c in categories
    }

    for pick in active:
        cat = nc_asset_category_for_pick(pick)
        if cat:
            stats[cat]["active"] += 1

    for pick in closed:
        cat = nc_asset_category_for_pick(pick)
        if not cat:
            continue
        pnl = _float(pick.get("net_pnl_pct", pick.get("pnl_pct", 0)))
        capped = max(-500.0, min(500.0, pnl))
        bucket = stats[cat]
        bucket["closed"] += 1
        bucket["total_pnl_pct"] += capped
        outcome = _outcome_bucket_from_pnl(pnl)
        if outcome == "win":
            bucket["wins"] += 1
        elif outcome == "loss":
            bucket["losses"] += 1
        else:
            bucket["flat"] += 1

    for cat in categories:
        bucket = stats[cat]
        bucket["resolved"] = bucket["wins"] + bucket["losses"] + bucket["flat"]
        bucket["win_rate"] = (
            round(bucket["wins"] / bucket["resolved"] * 100, 1)
            if bucket["resolved"] > 0
            else None
        )
        bucket["total_pnl_pct"] = round(bucket["total_pnl_pct"], 2)

    aggregate = {
        "active": 0,
        "closed": 0,
        "wins": 0,
        "losses": 0,
        "flat": 0,
        "resolved": 0,
        "win_rate": None,
        "total_pnl_pct": 0.0,
    }
    for cat in categories:
        bucket = stats[cat]
        aggregate["active"] += bucket["active"]
        aggregate["closed"] += bucket["closed"]
        aggregate["wins"] += bucket["wins"]
        aggregate["losses"] += bucket["losses"]
        aggregate["flat"] += bucket["flat"]
        aggregate["total_pnl_pct"] += bucket["total_pnl_pct"]

    aggregate["resolved"] = aggregate["wins"] + aggregate["losses"] + aggregate["flat"]
    aggregate["win_rate"] = (
        round(aggregate["wins"] / aggregate["resolved"] * 100, 1)
        if aggregate["resolved"] > 0
        else None
    )
    aggregate["total_pnl_pct"] = round(aggregate["total_pnl_pct"], 2)

    return {
        "categories": stats,
        "aggregate": aggregate,
    }


# B2 (2026-05-02): Asset-Class × Timeframe coverage grid
_AC_TF_GRID_ASSET_CLASSES = ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "BOND", "ETF", "FUTURES"]
_AC_TF_GRID_TIMEFRAMES = ["SCALP", "INTRADAY", "SWING", "POSITION"]


def _build_ac_timeframe_grid(active_picks: list) -> dict:
    """Build a (asset_class × timeframe) count matrix from active picks.

    Returns a dict with:
      classes   — ordered list of asset class labels (fixed base + any extras observed)
      timeframes — ordered list of timeframe labels (fixed order + "UNKNOWN" if needed)
      cells      — dict mapping "CLASS|TF" to {"count": int, "pick_ids": [str, ...]}
      totals_by_class — dict mapping class → total active count
      empty_lanes — list of {"asset_class": str, "timeframe": str} for zero cells
    """
    from collections import defaultdict

    cell_data: dict = defaultdict(lambda: {"count": 0, "pick_ids": []})
    observed_classes: set = set()
    has_unknown_tf = False

    for pick in active_picks:
        ac = (pick.get("asset_class") or "UNKNOWN").upper()
        tf = (pick.get("trade_timeframe") or "").upper().strip() or "UNKNOWN"
        observed_classes.add(ac)
        if tf == "UNKNOWN":
            has_unknown_tf = True
        key = f"{ac}|{tf}"
        cell_data[key]["count"] += 1
        pid = pick.get("id") or pick.get("pick_id") or ""
        if pid:
            cell_data[key]["pick_ids"].append(str(pid))

    # Build class list: fixed base first, then any extras observed
    base_classes = _AC_TF_GRID_ASSET_CLASSES
    extra_classes = sorted(observed_classes - set(base_classes) - {"UNKNOWN"})
    all_classes = base_classes + extra_classes

    timeframes = list(_AC_TF_GRID_TIMEFRAMES)
    if has_unknown_tf:
        timeframes.append("UNKNOWN")

    cells: dict = {}
    empty_lanes: list = []
    totals_by_class: dict = {}

    for ac in all_classes:
        total = 0
        for tf in timeframes:
            key = f"{ac}|{tf}"
            entry = cell_data.get(key, {"count": 0, "pick_ids": []})
            cells[key] = {"count": entry["count"], "pick_ids": entry["pick_ids"]}
            total += entry["count"]
            if entry["count"] == 0:
                empty_lanes.append({"asset_class": ac, "timeframe": tf})
        totals_by_class[ac] = total

    return {
        "classes": all_classes,
        "timeframes": timeframes,
        "cells": cells,
        "totals_by_class": totals_by_class,
        "empty_lanes": empty_lanes,
    }


def _filter_active_picks_with_gate(active_picks: list[dict]) -> tuple[list[dict], int]:
    """Re-apply ``passes_active_gate`` to the current in-memory pick state.

    Active rows are mutated after the first gate pass. Late-stage penalties can
    push a pick below the final visibility floor, so the published
    ``payload["picks"]["active"]`` must be re-checked against the same gate
    before downstream summaries are computed.
    """
    filtered_active: list[dict] = []
    filtered_out = 0
    for pick in active_picks:
        if passes_active_gate(pick):
            pick["_gate_passed"] = True
            filtered_active.append(pick)
        else:
            pick["_gate_passed"] = False
            filtered_out += 1
    return filtered_active, filtered_out


# ── B18: Shadow-mode auto-promotion ──

def _apply_shadow_promotion(
    active_picks: list,
    raw_pool: list,
    all_closed: list,
) -> tuple:
    """Inject shadow-promoted picks for zero-history strategies (B18, default-OFF).

    Returns (updated_active_picks, shadow_probation_summary).
    Picks that pass the gate normally are unchanged.  Shadow picks are tagged
    shadow_mode=True + shadow_size_multiplier=0.1 and are excluded from HC by
    passes_high_conviction_pick() in dashboard_hc_rules.py.
    """
    from audit_trail.quality_gates import (
        _SHADOW_MAX_CONCURRENT,
        _SHADOW_MIN_RAW_EMITS,
        _SHADOW_SIZE_MULTIPLIER,
        should_shadow_promote,
    )

    shadow_probation: dict = {"enabled": False, "shadow_picks": [], "candidate_strategies": []}

    if os.environ.get("SHADOW_MODE_AUTO_PROMOTE_ENABLED", "0") != "1":
        return active_picks, shadow_probation

    shadow_probation["enabled"] = True

    # Count closed picks per strategy (full history)
    closed_by_strategy: dict = {}
    for p in all_closed:
        s = str(p.get("strategy", "") or "").strip()
        if s:
            closed_by_strategy[s] = closed_by_strategy.get(s, 0) + 1

    # Count raw emits per strategy from the current raw-active pool
    raw_emits: dict = {}
    for p in raw_pool:
        s = str(p.get("strategy", "") or "").strip()
        if not s:
            continue
        if s not in raw_emits:
            raw_emits[s] = []
        raw_emits[s].append(p)

    # Strategies already in the filtered-active list (pass gate normally)
    active_strategies = {str(p.get("strategy", "") or "").strip() for p in active_picks}

    # Find shadow candidates: zero closed + enough raw emits + not already active
    candidates = []
    for strat, picks in raw_emits.items():
        if strat in active_strategies:
            continue
        closed_n = closed_by_strategy.get(strat, 0)
        if not should_shadow_promote(strat, len(picks), closed_n):
            continue
        shadow_probation["candidate_strategies"].append(
            {"strategy": strat, "raw_emit_count": len(picks), "closed_count": closed_n}
        )
        # Promote the highest-confidence pick from this strategy
        best = max(picks, key=lambda p: float(p.get("confidence", 0) or 0))
        promoted = dict(best)
        promoted["shadow_mode"] = True
        promoted["shadow_size_multiplier"] = _SHADOW_SIZE_MULTIPLIER
        promoted["shadow_strategy_raw_emit_count"] = len(picks)
        promoted["_gate_passed"] = True
        candidates.append(promoted)

    # Apply global cap (highest-confidence candidates first)
    if len(candidates) > _SHADOW_MAX_CONCURRENT:
        candidates.sort(key=lambda p: float(p.get("confidence", 0) or 0), reverse=True)
        candidates = candidates[:_SHADOW_MAX_CONCURRENT]

    if candidates:
        log.info(
            "Shadow promotion (B18): %d/%d candidates promoted (cap=%d)",
            len(candidates), len(shadow_probation["candidate_strategies"]), _SHADOW_MAX_CONCURRENT,
        )
        for c in candidates:
            shadow_probation["shadow_picks"].append(
                {"strategy": c.get("strategy"), "symbol": c.get("symbol"), "direction": c.get("direction")}
            )
        active_picks = active_picks + candidates

    return active_picks, shadow_probation


def _apply_alert_shadow_demotion(active_picks, perf_alerts, shadow_probation):
    """2026-05-05 (PR #3 of 6 from quant-performance-auditor agent run):
    auto-demote strategies with HIGH STRATEGY_DEGRADATION alerts into the
    existing shadow_probation pipeline. Default-OFF via
    SHADOW_ALERT_DEMOTE_ENABLED=1.

    Wires existing infrastructure: `perf_alerts` (computed at
    `check_all_alerts(active, closed, systems)`) and `shadow_probation`
    (built by `_apply_shadow_promotion`). No new module — pure wire-up.

    Active picks whose `strategy` matches a degraded one are tagged
    `shadow_mode=True` + `shadow_size_multiplier=0.1` so
    `passes_high_conviction_pick()` excludes them from HC and downstream
    sizing routes them at 10% size. The strategy is also appended to
    `shadow_probation.candidate_strategies` with `kind="demoted"` so the
    UI can surface degraded systems alongside zero-history candidates.

    Returns the updated active picks list (same shape) and mutates
    shadow_probation in place.
    """
    if os.environ.get("SHADOW_ALERT_DEMOTE_ENABLED", "0") != "1":
        return active_picks

    if not perf_alerts:
        return active_picks

    degraded = set()
    for a in perf_alerts:
        if (a.get("severity") or "").upper() != "HIGH":
            continue
        if (a.get("type") or "") != "STRATEGY_DEGRADATION":
            continue
        details = a.get("details") or {}
        strat = (details.get("strategy") or "").strip()
        if strat:
            degraded.add(strat)
            shadow_probation["candidate_strategies"].append({
                "strategy": strat,
                "kind": "demoted",
                "rolling_wr": details.get("rolling_wr"),
                "baseline_wr": details.get("baseline_wr"),
                "n_recent": details.get("n_recent"),
            })

    if not degraded:
        return active_picks

    # Mutate matching active picks. Preserve order; do not drop any pick.
    demoted_n = 0
    for p in active_picks:
        s = (p.get("strategy") or "").strip()
        if s in degraded:
            p["shadow_mode"] = True
            p["shadow_size_multiplier"] = 0.1
            p["_demotion_reason"] = "degradation_alert"
            demoted_n += 1

    if demoted_n:
        log.info(
            "Alert-shadow-demote: %d active picks demoted across %d strategy(ies): %s",
            demoted_n, len(degraded), sorted(degraded),
        )
        shadow_probation["enabled"] = True
        shadow_probation.setdefault("alert_demoted_strategies", []).extend(sorted(degraded))

    return active_picks


# ── Main generator ──


def generate():
    """Main entry point: collect all data, write payload JSON."""
    now = datetime.now(timezone.utc).isoformat()
    log.info("Generating unified audit dashboard payload...")
    _maybe_refresh_universal_resolved()

    active, closed, all_closed_including_expired, _active_raw_snapshot = collect_all_picks()

    # ── Enrich active picks with live prices from Binance ──
    active = _enrich_live_pnl(active)

    # ── Entry price drift guard: penalize picks with entry >15% from live price ──
    # If entry is 15%+ away from current price, flag it with a score penalty
    # instead of removing it. The pick still shows but sorts lower.
    drift_flagged = 0
    for p in active:
        live = _float(p.get("current_price", 0))
        entry = _float(p.get("entry_price", 0))
        if live > 0 and entry > 0:
            drift_pct = abs(live - entry) / live * 100
            if drift_pct > 15:
                drift_flagged += 1
                p["_entry_drift_pct"] = round(drift_pct, 1)
                p["score"] = max(0, _float(p.get("score", 50)) - 20)
                log.warning(
                    "Entry drift guard: %s %s entry=%.4f live=%.4f drift=%.1f%% — score penalty -20",
                    p.get("symbol"),
                    p.get("source_system"),
                    entry,
                    live,
                    drift_pct,
                )
    if drift_flagged:
        log.info(
            "  Entry drift guard: penalized %d picks with >15%% entry/live drift",
            drift_flagged,
        )

    # ── Kill list enforcement: remove picks from killed strategies ──
    # 270+ picks were leaking because dashboard_generator had no kill list check.
    # This filters picks whose strategy name matches ANY kill list entry (exact or partial).
    try:
        _kill_set = set()
        _kl_path = (
            Path(__file__).resolve().parent.parent
            / "alpha_engine"
            / "data"
            / "core_whitelist.json"
        )
        if _kl_path.exists():
            with open(_kl_path, "r", encoding="utf-8", errors="replace") as _kf:
                _kl_data = json.load(_kf)
            _kill_set.update(
                s.lower().split("::")[-1] for s in _kl_data.get("kill_list", [])
            )
        try:
            from alpha_engine.auto_tuner import PERMANENTLY_KILLED as _AUTO_KILLED

            _kill_set.update(str(s).lower().split("::")[-1] for s in _AUTO_KILLED)
        except Exception as _auto_kill_err:
            log.warning("  Auto-tuner kill list unavailable: %s", _auto_kill_err)
        if _kill_set:
            _killed_count = 0
            _already_penalized = 0
            for p in active:
                strat_lower = (p.get("strategy", "") or "").lower().split("::")[-1]
                if strat_lower in _kill_set:
                    # BUG FIX (2026-04-04 claude-opus-scoring): skip if quality_gates.py
                    # already penalized via 'killed_strategy' or 'corroborated_killed_strategy'
                    # _penalties marker. Previously this double-penalized: -40 on top of
                    # the -40/-10 already applied, zeroing out 22 picks that should score 15-30.
                    _pens = p.get("_penalties", []) or []
                    _already_killed = any(
                        "killed_strategy" in str(pen) for pen in _pens
                    )
                    if _already_killed:
                        p["_killed_strategy"] = True
                        _already_penalized += 1
                    else:
                        p["score"] = max(0, _float(p.get("score", 50)) - 40)
                        p["_killed_strategy"] = True
                        _killed_count += 1
            if _killed_count or _already_penalized:
                log.info(
                    "  Kill list enforcement: penalized %d picks (%d already penalized via quality_gates)",
                    _killed_count,
                    _already_penalized,
                )
    except Exception as _ke:
        log.warning("  Kill list enforcement failed: %s", _ke)

    # Flag non-active/non-tradeable picks with penalty instead of removing
    _flagged_non_active = 0
    for p in active:
        if not _is_active_pick(p):
            p["score"] = max(0, _float(p.get("score", 50)) - 30)
            p["_flag"] = "non_active_status"
            _flagged_non_active += 1
        elif not _has_tradeable_entry(p):
            p["score"] = max(0, _float(p.get("score", 50)) - 15)
            p["_flag"] = "no_tradeable_entry"
            _flagged_non_active += 1
    if _flagged_non_active:
        log.info(
            "  Active-feed hygiene: penalized %d non-tradeable or resolved picks (still shown)",
            _flagged_non_active,
        )

    # DISABLED: Active quality floor - now handled by score penalties in quality_gates.py
    # With the new score-based approach, ALL picks reach the dashboard. Quality signals
    # adjust the score (lower = weaker) rather than hiding picks entirely.
    # The _apply_score_penalties function in quality_gates.py handles low confidence
    # and other quality issues via score adjustments.
    try:
        _before_quality_floor = len(active)
        # Keep all picks - score penalties will rank them appropriately
        _removed_quality_floor = 0
        if _removed_quality_floor:
            log.info(
                "  Active quality floor: removed %d low-confidence unproven picks",
                _removed_quality_floor,
            )
    except Exception as e:
        log.warning("  Active quality floor failed (non-fatal): %s", e)

    # Use metric-grade closed trades for WR/PnL, but also pass the full shadow
    # closed bucket so auto-expired rows still show up as excluded transparency counts.
    # D2 fix (reports/crypto_edge_artifact_audit_2026_05_17.md): the systems[]
    # leaderboard was built from the RAW closed ledger, which double-counts
    # mirrored trades — inflating per-source PF (e.g. aggregated_picks showed
    # systems[] PF ~4.5 vs its true deduped PF ~0.53). Dedupe on
    # (symbol, direction, entry, pnl) first — same key as the headline-stats
    # dedup below (~line 13794).
    _seen_sys: set = set()
    _closed_for_systems = []
    # D2 review fix: validity-filter BEFORE dedup. Deduping raw `closed`
    # first lets a breakeven / RESOLVE_FAILED row consume a dedup key and
    # suppress a legitimate pick with the same (symbol,dir,entry,pnl) key.
    # Matches the headline-stats ordering (_filter_valid_resolved_picks
    # then dedup) used ~line 13822.
    for _p in _filter_valid_resolved_picks(closed):
        _k = (
            str(_p.get("symbol", "")).upper(),
            str(_p.get("direction", "") or _p.get("signal_type", "")).upper()[:1],
            round(float(_p.get("entry_price", 0) or 0), 6),
            round(float(_p.get("pnl_pct", 0) or 0), 4),
        )
        if _k in _seen_sys:
            continue
        _seen_sys.add(_k)
        _closed_for_systems.append(_p)
    systems = collect_system_stats(active, _closed_for_systems, all_closed_including_expired)
    portfolios = collect_portfolios()
    audit_events = collect_audit_events(50)
    filter_events = collect_filter_log(50)
    bt_vs_fwd = collect_backtest_vs_forward()
    hf_decay_watchlist = _compute_hf_decay_watchlist(bt_vs_fwd)
    fwd_vs_bt_divergence = _compute_fwd_vs_bt_divergence(bt_vs_fwd)
    # Top-7 swarm #2: FRED macro context for FOREX/BOND regime overlay.
    # Off-by-default in production (no caller wiring yet); dashboard surface
    # is the first wire-in point. Empty dict if FRED_MACRO_DISABLED=1.
    try:
        from alpha_engine.fred_macro_context import summarize_for_dashboard as _fred_dash
        macro_context = _fred_dash() or {}
    except Exception as _fred_exc:
        log.warning("  FRED macro context fetch failed (non-fatal): %s", _fred_exc)
        macro_context = {}
    # T2.2/B7: Cross-asset correlation matrix (concentration vs diversification).
    try:
        cross_asset_correlation = _compute_cross_asset_correlation(closed, lookback_days=30)
    except Exception as _xac_exc:
        log.warning("  Cross-asset correlation computation failed (non-fatal): %s", _xac_exc)
        cross_asset_correlation = {
            "matrix": {},
            "n_days": 0,
            "asset_classes": [],
            "lookback_days": 30,
            "error": str(_xac_exc),
        }
    # Sidecar promotion tracker (2026-05-09) — promotion-gate readiness for the
    # 7 newly-shipped sidecar strategies. Surfaced under the BtVsFwd tab.
    try:
        sidecar_promotion_status = _compute_sidecar_promotion_status(closed, leaderboard=None)
    except Exception as _spr_exc:
        log.warning("  Sidecar promotion status computation failed (non-fatal): %s", _spr_exc)
        sidecar_promotion_status = {}
    # Tier-2 hero-card promotion surface — surfaces 4 buried-but-high-edge
    # strategies (signal_validation, mega_mutation, rl_agent, claude_gainer)
    # as hero cards above the alphabetical /audit systems grid.
    # See `_compute_tier2_proven_strategies` for honest CHARTER §2 tiering.
    try:
        tier2_proven_strategies = _compute_tier2_proven_strategies(systems, closed)
    except Exception as _t2_exc:
        log.warning("  Tier-2 hero card computation failed (non-fatal): %s", _t2_exc)
        tier2_proven_strategies = {
            "cards": [],
            "flagged_dropouts": [],
            "promotion_targets": list(_TIER2_PROMOTION_TARGETS),
            "error": str(_t2_exc),
        }
    bundles = collect_bundles()
    leaderboard = collect_strategy_leaderboard(active, closed)
    consensus = collect_consensus_analysis(active, closed)
    volatility = collect_volatility_tracking(active, closed)
    predictions_lb = collect_predictions_leaderboard()
    cross_system_perms = collect_cross_system_permutations(active, closed)
    cross_strategy_perms = collect_cross_strategy_permutations(active, closed)
    regime_validation = compute_regime_validation(active, closed)
    smart_picks_feed = _load_smart_picks_feed()
    smart_picks_snapshot_summary = _summarize_smart_picks_history()
    big_mover_monitor_3pct = _summarize_big_movers(active, closed, threshold_pct=3.0)
    concentration_summary = _concentration_summary_from_active(active)
    probation_quarantine_summary = _probation_quarantine_summary(smart_picks_feed)

    # ── Performance Alerts ──
    try:
        perf_alerts = check_all_alerts(active, closed, systems)
        if perf_alerts:
            log.info(
                "  Perf alerts:   %d (%s)",
                len(perf_alerts),
                ", ".join(a["severity"] for a in perf_alerts[:5]),
            )
    except Exception as e:
        log.warning("Performance alerts failed: %s", e)
        perf_alerts = []

    # Sync permutation data to MySQL audit database
    try:
        from audit_trail.mysql_client import mysql_sync_permutations

        perm_sync = mysql_sync_permutations(cross_system_perms, cross_strategy_perms)
        if perm_sync.get("success"):
            log.info(
                "Permutation MySQL sync: %d system + %d strategy snapshots",
                perm_sync["system_snapshots"],
                perm_sync["strategy_snapshots"],
            )
        else:
            log.warning(
                "Permutation MySQL sync failed — dashboard data still generated locally"
            )
    except Exception as e:
        log.warning("Permutation MySQL sync skipped: %s", e)

    # Summary stats — exclude auto-expired picks with no PnL and paper-only
    # picks (frozen research portfolios) from resolved counts, matching
    # collect_system_stats methodology (line ~2356).
    total_active = len(active)
    total_closed = len(closed)
    resolved_closed = _filter_valid_resolved_picks(closed)
    invalid_closed_count = total_closed - len(resolved_closed)

    # DEDUPLICATE mirrored trades for headline metrics (critical fix for inflated WR/PnL)
    seen = set()
    deduped_closed = []
    mirror_dupe_count = 0
    for p in resolved_closed:
        key = (
            str(p.get("symbol", "")).upper(),
            str(p.get("direction", "") or p.get("signal_type", "")).upper()[:1],
            round(float(p.get("entry_price", 0) or 0), 6),
            round(float(p.get("pnl_pct", 0) or 0), 4),
        )
        if key in seen:
            mirror_dupe_count += 1
            continue
        seen.add(key)
        deduped_closed.append(p)

    resolved_closed = deduped_closed  # Use deduplicated list for headline stats
    _exit_norm_changed = _apply_issue186_exit_normalization(resolved_closed)
    if _exit_norm_changed:
        log.info(
            "  Exit normalization (#186): refined exit_reason on %d/%d resolved closed picks",
            _exit_norm_changed,
            len(resolved_closed),
        )
    closed_pnl_concentration = _compute_closed_pnl_concentration_by_source(
        resolved_closed
    )

    # Minimum threshold: |pnl| < 0.01% = effectively flat (not a real win/loss)
    _SUMMARY_MIN_PNL = 0.01
    wins = sum(
        1 for p in resolved_closed if float(p.get("pnl_pct", 0) or 0) > _SUMMARY_MIN_PNL
    )
    losses = sum(
        1
        for p in resolved_closed
        if float(p.get("pnl_pct", 0) or 0) < -_SUMMARY_MIN_PNL
    )
    zero_pnl_count = sum(
        1
        for p in resolved_closed
        if abs(float(p.get("pnl_pct", 0) or 0)) <= _SUMMARY_MIN_PNL
    )
    total_resolved = wins + losses + zero_pnl_count
    overall_wr = _calculate_win_rate_pct(wins, losses, zero_pnl_count)
    # Apply same MAX_PNL cap (500%) as system-level aggregation to avoid summary inflation
    _MAX_PNL_SUMMARY = 500
    total_pnl = round(
        sum(
            max(
                -_MAX_PNL_SUMMARY,
                min(_MAX_PNL_SUMMARY, float(p.get("pnl_pct", 0) or 0)),
            )
            for p in resolved_closed
        ),
        2,
    )
    # 2026-05-08: tighter cap for EW compound (was 500% = absurd at long N).
    # 2026-05-09: post-resolver run on N=9634 trades produced +4,092,342% at
    # cap=10 (mean per-trade capped pnl ~0.11% compounded over 9634 = e^10.6).
    # Tightened cap to 2.0% — still too generous mathematically (the metric is
    # fundamentally broken for sequences w/ N>1000) but acts as the safety
    # ceiling pending the rolling-window / log-return redesign.
    # KNOWN LIMITATION: TODO 2026-05-22 replace with rolling-window
    # (last 100 trades) compound OR per-day geomean × 252 annualization.
    # Until then, the metric should be read with the disclaimer:
    #   "fictitious sequential reinvestment of 1 unit on every trade"
    _MAX_PNL_COMPOUND = 10  # bumped from 2% (2026-06-04): 2% destroyed edge at scale; 10% loss-protective
    total_pnl_pct_compounded_ew = _compound_equal_weight_capped_sequence(
        resolved_closed, float(_MAX_PNL_COMPOUND)
    )
    # Hard sanity ceiling so the summary card doesn't show absurd numbers
    # while the redesign lands. 9999% is well above any realistic portfolio
    # return but visually communicates "uncapped".
    if total_pnl_pct_compounded_ew is not None and total_pnl_pct_compounded_ew > 9999:
        total_pnl_pct_compounded_ew = 9999.0
    elif total_pnl_pct_compounded_ew is not None and total_pnl_pct_compounded_ew < -99:
        total_pnl_pct_compounded_ew = -99.0
    # T1.4 redesign (2026-05-09): rolling-window compound (last 100 trades)
    # is the bounded headline replacement for the unbounded full-ledger EW
    # compound. Per-day geomean × 252 is the annualized rate companion. Both
    # use a 10% per-trade cap (looser than the 2% summary-cap above because
    # the rolling window already bounds N).
    total_pnl_pct_compounded_rolling_100 = _compound_rolling_window(
        resolved_closed, window=100, max_pnl_pct=10.0
    )
    total_pnl_pct_geomean_annualized = _compound_per_day_geomean_annualized(
        resolved_closed, max_pnl_pct=10.0
    )
    total_win_pnl = sum(
        max(0, min(_MAX_PNL_SUMMARY, float(p.get("pnl_pct", 0) or 0)))
        for p in resolved_closed
        if float(p.get("pnl_pct", 0) or 0) > 0
    )
    total_loss_pnl = sum(
        max(-_MAX_PNL_SUMMARY, min(0, float(p.get("pnl_pct", 0) or 0)))
        for p in resolved_closed
        if float(p.get("pnl_pct", 0) or 0) < 0
    )
    overall_pf = (
        round(total_win_pnl / abs(total_loss_pnl), 2) if total_loss_pnl < 0 else None
    )
    overall_avg_win = round(total_win_pnl / wins, 2) if wins > 0 else 0
    overall_avg_loss = round(abs(total_loss_pnl) / losses, 2) if losses > 0 else 0
    overall_expectancy = _calculate_expectancy_pct(
        total_pnl, wins, losses, zero_pnl_count
    )

    # ── Mercury Validation Metrics ──
    # Group closed picks by date for daily P&L computation
    daily_pnl = defaultdict(float)
    for p in resolved_closed:
        ts = p.get("timestamp", "")
        if ts:
            try:
                day = ts[:10]  # Extract YYYY-MM-DD from ISO timestamp
                if len(day) == 10 and day[4] == "-":
                    daily_pnl[day] += float(p.get("pnl_pct", 0) or 0)
            except Exception:
                pass

    # Daily volatility: std dev of daily P&L as % of equity
    mercury_daily_vol = None
    mercury_net_sharpe = None
    mercury_rolling_30d_dd = None
    # loop2 #6 redesign (2026-05-09): keep the daily-aggregated Sharpe (valid
    # for portfolio-aggregate / institutional comparison) AND emit a per-trade
    # Sharpe (strategy-quality signal). Annualization rules:
    #   - daily Sharpe → × sqrt(252)              (calendar-day basis)
    #   - per-trade Sharpe → × sqrt(trades_per_year)  (estimated from span)
    # See `_per_trade_sharpe()` docstring for guidance on which to cite.
    mercury_net_sharpe_daily = None
    mercury_net_sharpe_daily_annual = None
    mercury_net_sharpe_per_trade = None
    mercury_net_sharpe_per_trade_annual = None
    if len(daily_pnl) >= 2:
        daily_returns = sorted(daily_pnl.items())  # sorted by date
        daily_vals = [v for _, v in daily_returns]
        mean_daily = sum(daily_vals) / len(daily_vals)
        variance = sum((x - mean_daily) ** 2 for x in daily_vals) / (
            len(daily_vals) - 1
        )
        mercury_daily_vol = round(math.sqrt(variance), 4)

        # Net Sharpe: (avg_return - transaction_cost) / daily_vol
        # 0.02% cost per trade; estimate trades_per_day from data
        total_days = len(daily_vals)
        trades_per_day = total_resolved / total_days if total_days > 0 else 0
        cost_per_day = (
            0.0002 * trades_per_day
        )  # 0.02% = 0.0002 as a fraction, but pnl_pct is in %, so cost = 0.02 * trades
        cost_per_day_pct = 0.02 * trades_per_day  # in percentage terms to match pnl_pct
        if mercury_daily_vol > 0:
            mercury_net_sharpe = round(
                (mean_daily - cost_per_day_pct) / mercury_daily_vol, 4
            )
            # Annualize: multiply by sqrt(252) for reference
            mercury_net_sharpe_annual = round(mercury_net_sharpe * math.sqrt(252), 2)
            mercury_net_sharpe_daily = mercury_net_sharpe
            mercury_net_sharpe_daily_annual = mercury_net_sharpe_annual
        else:
            mercury_net_sharpe = 0.0
            mercury_net_sharpe_annual = 0.0
            mercury_net_sharpe_daily = 0.0
            mercury_net_sharpe_daily_annual = 0.0

        # Per-trade Sharpe (strategy-quality lens). Pass days_span = number of
        # observed days so the annualization factor is calibrated to the data
        # window rather than degenerating to sqrt(N).
        _spt, _spt_annual = _per_trade_sharpe(resolved_closed, days_span=total_days)
        mercury_net_sharpe_per_trade = _spt
        mercury_net_sharpe_per_trade_annual = _spt_annual

        # Rolling 30-day max drawdown
        # NOTE: daily_pnl[day] is a SUM of pnl_pct across all trades that day.
        # With 500+ trades/day at 1-2% each, raw sums reach 500-1000% and make
        # drawdown values meaningless (was displaying 19,702%). To make the
        # metric reflect a per-trade portfolio return instead, normalize each
        # day's sum by average trades-per-day (equal-weight sizing assumption).
        if len(daily_vals) >= 30:
            # Normalize daily sums to average per-trade return
            _tpd = trades_per_day if trades_per_day > 0 else 1.0
            daily_vals_norm = [v / _tpd for v in daily_vals]
            worst_30d_dd = 0.0
            for i in range(len(daily_vals_norm) - 29):
                window = daily_vals_norm[i : i + 30]
                cum = 0.0
                peak = 0.0
                window_dd = 0.0
                for v in window:
                    cum += v
                    if cum > peak:
                        peak = cum
                    dd = peak - cum
                    if dd > window_dd:
                        window_dd = dd
                if window_dd > worst_30d_dd:
                    worst_30d_dd = window_dd
            # Cap at 100% as a sanity floor (DD can't exceed initial capital)
            mercury_rolling_30d_dd = round(min(worst_30d_dd, 100.0), 2)
    else:
        mercury_net_sharpe_annual = None

    # ── Sortino Ratio ──
    # Per-TRADE Sortino (more accurate than daily aggregation which distorts with 500+ trades/day)
    # Sortino = mean_return / downside_deviation
    sortino_ratio = None
    sortino_ratio_annual = None
    trade_pnls = [
        float(p.get("pnl_pct", 0) or 0)
        for p in resolved_closed
        if float(p.get("pnl_pct", 0) or 0) != 0
    ]
    if len(trade_pnls) >= 10:
        mean_trade = sum(trade_pnls) / len(trade_pnls)
        risk_free_per_trade = 0.0  # no risk-free per trade
        downside_sq = [min(0, r - risk_free_per_trade) ** 2 for r in trade_pnls]
        downside_dev = (
            math.sqrt(sum(downside_sq) / len(downside_sq)) if downside_sq else 0
        )
        if downside_dev > 0:
            sortino_ratio = round((mean_trade - risk_free_per_trade) / downside_dev, 4)
            # Annualize: estimate trades per year from data span
            if len(daily_pnl) >= 2:
                days_span = max(1, len(daily_pnl))
                trades_per_day = len(trade_pnls) / days_span
                trades_per_year = trades_per_day * 252
                sortino_ratio_annual = round(
                    sortino_ratio * math.sqrt(trades_per_year), 2
                )
            else:
                sortino_ratio_annual = round(sortino_ratio * math.sqrt(252), 2)
        else:
            sortino_ratio = 0.0
            sortino_ratio_annual = 0.0

    # ── Calmar Ratio ──
    # annualized_return / max_drawdown (from rolling DD already computed)
    calmar_ratio = None
    if len(daily_pnl) >= 2:
        daily_vals_c = [v for _, v in sorted(daily_pnl.items())]
        total_return_c = sum(daily_vals_c)
        trading_days_c = len(daily_vals_c)
        annualized_return_c = (
            total_return_c * (252 / trading_days_c) if trading_days_c > 0 else 0
        )
        # Compute max drawdown from cumulative daily P&L
        cum_c = 0.0
        peak_c = 0.0
        max_dd_c = 0.0
        for v in daily_vals_c:
            cum_c += v
            if cum_c > peak_c:
                peak_c = cum_c
            dd_c = peak_c - cum_c
            if dd_c > max_dd_c:
                max_dd_c = dd_c
        if max_dd_c > 0:
            calmar_ratio = round(annualized_return_c / max_dd_c, 2)
        elif annualized_return_c > 0:
            calmar_ratio = 99.0  # No drawdown, positive return
        else:
            calmar_ratio = 0.0

    # ── Backtest-Forward Correlation ──
    # Compute correlation between backtest WR and forward WR across strategies
    bt_fwd_correlation = None
    bt_fwd_n = 0
    try:
        bt_wrs = []
        fwd_wrs = []
        for entry in bt_vs_fwd:
            bw = entry.get("bt_wr")
            fw = entry.get("fwd_wr")
            if bw is not None and fw is not None:
                bt_wrs.append(bw)
                fwd_wrs.append(fw)
        bt_fwd_n = len(bt_wrs)
        if bt_fwd_n >= 3:
            # Pearson correlation
            mean_bt = sum(bt_wrs) / bt_fwd_n
            mean_fw = sum(fwd_wrs) / bt_fwd_n
            cov = sum((b - mean_bt) * (f - mean_fw) for b, f in zip(bt_wrs, fwd_wrs))
            var_bt = sum((b - mean_bt) ** 2 for b in bt_wrs)
            var_fw = sum((f - mean_fw) ** 2 for f in fwd_wrs)
            denom = math.sqrt(var_bt * var_fw)
            if denom > 0:
                bt_fwd_correlation = round(cov / denom, 3)
            else:
                bt_fwd_correlation = 0.0
    except Exception:
        pass

    # Signal-to-trade ratio: total signals seen vs trades taken
    # Count all picks (active + closed including expired) as "signals seen"
    total_signals_seen = len(active) + len(all_closed_including_expired)
    trades_taken = total_resolved
    mercury_signal_to_trade = (
        round(trades_taken / total_signals_seen * 100, 1)
        if total_signals_seen > 0
        else None
    )

    # Regime-specific win rates: check regime_at_entry, consensus_regime, regime, market_regime
    # Maps variant labels to canonical regime names for consistent bucketing
    _REGIME_ALIASES = {
        "BULL": "TRENDING_UP",
        "BULLISH": "TRENDING_UP",
        "TRENDING_UP": "TRENDING_UP",
        "BEAR": "TRENDING_DOWN",
        "BEARISH": "TRENDING_DOWN",
        "TRENDING_DOWN": "TRENDING_DOWN",
        "NEUTRAL": "RANGING",
        "RANGE": "RANGING",
        "RANGE_BOUND": "RANGING",
        "RANGING": "RANGING",
        "VOLATILE": "HIGH_VOLATILITY",
        "HIGH_VOL": "HIGH_VOLATILITY",
        "HIGH_VOLATILITY": "HIGH_VOLATILITY",
        "CRASH": "CRASH",
        "MOMENTUM": "TRENDING_UP",
    }
    regime_wr = {}
    regime_buckets = defaultdict(lambda: {"wins": 0, "losses": 0})
    picks_with_regime_data = 0
    for p in resolved_closed:
        # Try multiple regime fields in priority order
        raw_regime = (
            p.get("regime_at_entry")
            or p.get("consensus_regime")
            or p.get("regime")
            or p.get("market_regime")
            or ""
        )
        regime = _REGIME_ALIASES.get(str(raw_regime).upper().strip())
        if regime:
            picks_with_regime_data += 1
            pnl = float(p.get("pnl_pct", 0) or 0)
            bucket = regime_buckets[regime]
            if pnl > 0:
                bucket["wins"] += 1
            elif pnl < 0:
                bucket["losses"] += 1

    # If no picks have regime data, compute a global regime from BTC 30-day SMA
    # and assign all picks to that single regime for a baseline breakdown
    if picks_with_regime_data == 0 and resolved_closed:
        global_regime = "RANGING"  # default
        try:
            btc_url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=30"
            req = urllib.request.Request(
                btc_url, headers={"User-Agent": "AuditDashboard/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                klines = json.loads(resp.read())
            if klines and len(klines) >= 10:
                closes = [float(k[4]) for k in klines]
                sma_30 = sum(closes) / len(closes)
                current_price = closes[-1]
                if current_price > sma_30 * 1.02:
                    global_regime = "TRENDING_UP"
                elif current_price < sma_30 * 0.98:
                    global_regime = "TRENDING_DOWN"
                else:
                    global_regime = "RANGING"
                log.info(
                    "  Regime fallback: BTC price=%.0f, SMA30=%.0f -> %s",
                    current_price,
                    sma_30,
                    global_regime,
                )
        except Exception as e:
            log.warning("  Regime fallback BTC fetch failed: %s -- using RANGING", e)

        bucket = regime_buckets[global_regime]
        for p in resolved_closed:
            pnl = float(p.get("pnl_pct", 0) or 0)
            if pnl > 0:
                bucket["wins"] += 1
            elif pnl < 0:
                bucket["losses"] += 1
        log.info(
            "  Regime WR: no per-pick regime data; used global BTC regime (%s) for %d picks",
            global_regime,
            len(resolved_closed),
        )
    else:
        log.info(
            "  Regime WR: %d/%d closed picks have regime data",
            picks_with_regime_data,
            len(resolved_closed) if resolved_closed else 0,
        )

    for regime_name, bucket in regime_buckets.items():
        total_r = bucket["wins"] + bucket["losses"]
        if total_r > 0:
            regime_wr[regime_name] = {
                "win_rate": round(bucket["wins"] / total_r * 100, 1),
                "trades": total_r,
                "wins": bucket["wins"],
                "losses": bucket["losses"],
            }

    log.info(
        "  Mercury metrics: daily_vol=%.4f%%, net_sharpe=%.2f (annual=%.2f), rolling_30d_dd=%s%%, signal_to_trade=%s%%",
        mercury_daily_vol or 0,
        mercury_net_sharpe or 0,
        mercury_net_sharpe_annual or 0,
        mercury_rolling_30d_dd if mercury_rolling_30d_dd is not None else "N/A",
        mercury_signal_to_trade if mercury_signal_to_trade is not None else "N/A",
    )
    log.info(
        "  Sortino=%.2f (annual=%.2f), Calmar=%.2f, BT/FWD corr=%s (n=%d)",
        sortino_ratio or 0,
        sortino_ratio_annual or 0,
        calmar_ratio or 0,
        bt_fwd_correlation if bt_fwd_correlation is not None else "N/A",
        bt_fwd_n,
    )

    # ── Institutional Stats Cleaner ──
    # Capped returns, concentration risk, risk-adjusted metrics
    try:
        from alpha_engine.stats_cleaner import (
            compute_clean_metrics,
            compute_timeframe_stats,
            compute_system_clean_metrics,
        )

        clean_metrics = compute_clean_metrics(resolved_closed, cap_pct=10.0)
        timeframe_stats = compute_timeframe_stats(resolved_closed, cap_pct=10.0)
        system_clean_metrics = compute_system_clean_metrics(
            resolved_closed, cap_pct=10.0
        )
        log.info(
            "  Stats cleaner: raw=%+.1f%% capped=%+.1f%% outliers=%d median=%+.2f%% top_sym=%s (%.1f%%)",
            clean_metrics.get("total_pnl_raw", 0),
            clean_metrics.get("total_pnl_capped", 0),
            clean_metrics.get("outlier_count", 0),
            clean_metrics.get("median_trade_pnl", 0),
            clean_metrics.get("top_symbol", "?"),
            clean_metrics.get("top_symbol_pnl_pct", 0),
        )
        if clean_metrics.get("concentration_warning"):
            log.warning("  %s", clean_metrics["concentration_warning"])
    except Exception as e:
        log.warning("Stats cleaner failed (non-fatal): %s", e)
        clean_metrics = {}
        timeframe_stats = {}
        system_clean_metrics = {}

    # Asset class breakdown
    ac_breakdown = {}
    # 2026-05-12 P0-#2: per-class symbol concentration accumulator.
    # Tracks abs(pnl_pct) mass per symbol within each class so we can
    # flag classes where a single ticker drives the headline edge.
    # WARN default; BLOCK opt-in via ASSET_CLASS_CONCENTRATION_BLOCK env.
    ac_sym_pnl: dict = {}
    # 2026-05-12 A3 (post-concentration plan, 4-engine unanimous SHIP_NOW):
    # also accumulate per-strategy share so we can answer
    # "WHICH strategy within COMMODITY drives the 75% CT=F dominance?"
    ac_strat_pnl: dict = {}
    # 2026-05-16 P0 fix: exclude blacklisted symbols from asset_class_health stats.
    # The COMMODITY_BLACKLIST / ETF_BLACKLIST in quality_gates.py blocks NEW picks
    # at emit-time, but historical closed picks for those symbols (e.g. CT=F with
    # WR 81.4% / PF 6.33) remained in the ac_breakdown accumulator, inflating the
    # headline stats. CT=F alone drove 75% of COMMODITY PnL mass, producing a
    # phantom PF 2.57 / WR 62.6% (T1 reading) when the true tradeable COMMODITY
    # universe (HG=F + PL=F only) is PF ~0.12-0.33, sub-floor.
    # Rollback: COMMODITY_SUBCLASS_KILL_DISABLED=1 / ETF_IWM_GLD_KILL_DISABLED=1
    _comm_blacklist_active = (
        os.environ.get("COMMODITY_SUBCLASS_KILL_DISABLED", "0") != "1"
    )
    _etf_blacklist_active = (
        os.environ.get("ETF_IWM_GLD_KILL_DISABLED", "0") != "1"
    )
    # 2026-05-17 P0: PERMANENTLY_KILLED_STRATEGIES (e.g. quan_engine /
    # quan_engine_scalp / quan_engine_position) are documented dead strategies
    # that passes_active_gate blocks at emit-time. Their historical resolved
    # rows (quan_engine alone = ~5.9k closed picks @ PF 0.38, 70% of the
    # CRYPTO ledger) still polluted asset_class_health, dragging the CRYPTO
    # verdict aggregate down to a quan_engine-weighted average. The existing
    # BLOCKED_SOURCE_SYSTEMS filter (below) only checks source_system; the
    # quan_engine family is killed at the STRATEGY level, so it slipped
    # through. Honour the existing kill in the verdict aggregate too.
    # Rollback: KILLED_STRATEGY_AGG_EXCLUDE_DISABLED=1.
    _killed_strat_excl_active = (
        os.environ.get("KILLED_STRATEGY_AGG_EXCLUDE_DISABLED", "0") != "1"
    )
    _killed_strat_lower: set = set()
    if _killed_strat_excl_active:
        try:
            from audit_trail.quality_gates import PERMANENTLY_KILLED_STRATEGIES
            _killed_strat_lower = {
                str(s).lower() for s in PERMANENTLY_KILLED_STRATEGIES
            }
        except Exception:
            _killed_strat_lower = set()

    def _cot_release_week_key(entry_dt) -> str:
        """Map a pick's entry timestamp to its CFTC COT release week.

        The CFTC COT report covers positions as of a TUESDAY settlement and
        is published the following Friday. Every pick that fires within the
        same publication week is a RE-EMISSION of one weekly release.

        We snap the entry date back to the most recent Tuesday and return
        an ISO year-week string (e.g. "2026-W18").
        """
        from datetime import datetime as _dt, date as _date, timedelta as _td
        if isinstance(entry_dt, _dt):
            d = entry_dt.date()
        elif isinstance(entry_dt, _date):
            d = entry_dt
        else:
            if not entry_dt:
                return "UNKNOWN"
            try:
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                    try:
                        d = _dt.strptime(str(entry_dt), fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    d = _dt.fromisoformat(str(entry_dt).replace("Z", "+00:00")).date()
            except Exception:
                return "UNKNOWN"
        days_since_tuesday = (d.weekday() - 1) % 7
        release_tuesday = d - _td(days=days_since_tuesday)
        iso_year, iso_week, _ = release_tuesday.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    def _dedup_cot_over_emission(closed_picks: list) -> list:
        """Dedup COT over-emission from historical closed picks.

        PR #961 added 1-per-(symbol, release_week, direction) dedup for
        go-forward emissions in cot_paper_pilot.py, but the dashboard
        fallback path's historical reads never applied it — inflating
        COMMODITY win rate and profit factor with re-emissions of the
        same CFTC weekly release.

        This mirrors dedupe_by_release_week() but also keys on (symbol,
        direction) so two different symbols or opposing directions within
        the same week are NOT collapsed together.
        """
        if not COT_DEDUP_SYSTEMS or not closed_picks:
            return list(closed_picks)
        cot_picks = []
        non_cot_picks = []
        for p in closed_picks:
            ss = str(p.get("source_system") or "")
            if ss in COT_DEDUP_SYSTEMS:
                cot_picks.append(p)
            else:
                non_cot_picks.append(p)
        if not cot_picks:
            return list(closed_picks)
        from datetime import datetime as _dt, timedelta as _td
        annotated = []
        for p in cot_picks:
            created = p.get("created_at")
            try:
                if isinstance(created, _dt):
                    entry_dt = created
                elif isinstance(created, str) and created:
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                        try:
                            entry_dt = _dt.strptime(created, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        entry_dt = _dt.fromisoformat(created.replace("Z", "+00:00"))
                else:
                    entry_dt = _dt.max
            except Exception:
                entry_dt = _dt.max
            symbol = str(p.get("symbol") or "").upper().strip()
            direction = str(p.get("direction") or "").upper().strip()
            release_week = _cot_release_week_key(
                entry_dt if entry_dt is not _dt.max else None
            )
            if release_week == "UNKNOWN":
                release_week = f"UNKNOWN::{p.get('id', id(p))}"
            dedup_key = f"{symbol}::{release_week}::{direction}"
            annotated.append((entry_dt, dedup_key, p))
        annotated.sort(key=lambda t: t[0])
        seen = {}
        for entry_dt, dedup_key, p in annotated:
            if dedup_key not in seen:
                seen[dedup_key] = p
        deduped_cot = list(seen.values())
        return non_cot_picks + deduped_cot

    # M-077: dedup COT over-emission from closed picks (fallback path only).
    # pf_registry.json is built by build_pf_registry.py which applies the
    # 1-per-(symbol,release_week,direction) dedup from PR #961. The fallback
    # path's raw `closed` list never was — inflating COMMODITY WR/PF with
    # repeated re-emissions of the same CFTC weekly release.
    if COT_DEDUP_SYSTEMS:
        _closed_fallback = _dedup_cot_over_emission(closed)
    else:
        _closed_fallback = closed
    for p in active + _closed_fallback:
        if is_corrupted_outcome_row(p):
            continue
        ac = p["asset_class"]
        _ac_upper = str(ac or "").upper().strip()
        _sym_upper = str(p.get("symbol") or "").upper().strip()
        # Skip blacklisted COMMODITY symbols (CT=F, GC=F, SI=F, CL=F, etc.)
        if (
            _comm_blacklist_active
            and _ac_upper in ("COMMODITY", "COMMODITIES")
            and _sym_upper in COMMODITY_BLACKLIST
        ):
            continue
        # Skip blacklisted ETF symbols (IWM, GLD)
        if (
            _etf_blacklist_active
            and _ac_upper == "ETF"
            and _sym_upper in ETF_BLACKLIST
        ):
            continue
        # C3 / claim A3 (reports/crypto_edge_artifact_audit_2026_05_17.md):
        # blocked source systems are statistically proven losers (PF < 1.0).
        # passes_active_gate blocks them from NEW picks, but their historical
        # resolved trades still polluted this verdict aggregate. Exclude them.
        if BLOCKED_SOURCE_SYSTEMS and str(p.get("source_system") or "") in BLOCKED_SOURCE_SYSTEMS:
            continue
        # 2026-05-17 P0: also drop rows whose strategy OR source_system is in
        # PERMANENTLY_KILLED_STRATEGIES (quan_engine family etc.). Killed at
        # the strategy level, so BLOCKED_SOURCE_SYSTEMS (source-keyed) missed
        # them — they were silently inflating the closed-row count and
        # dragging the verdict aggregate.
        if _killed_strat_lower and (
            str(p.get("strategy") or "").lower() in _killed_strat_lower
            or str(p.get("source_system") or "").lower() in _killed_strat_lower
        ):
            continue
        if ac not in ac_breakdown:
            ac_breakdown[ac] = {
                "active": 0,
                "closed": 0,
                "wins": 0,
                "losses": 0,
                "flat": 0,
                "pnl": 0.0,
                "win_pnl": 0.0,
                "loss_pnl": 0.0,
            }
            ac_sym_pnl[ac] = {}
            ac_strat_pnl[ac] = {}
        b = ac_breakdown[ac]
        if p["status"] == "OPEN":
            b["active"] += 1
        else:
            if not _is_valid_resolved_pick(p):
                continue  # Skip stale/snapshot closures from asset class stats
            # `closed` is incremented only for valid resolved picks so the
            # object stays internally coherent: closed == wins + losses + flat.
            # (Pre-2026-05-22 this counted every non-OPEN row incl. stale
            # snapshots, so closed disagreed with wins+losses — see
            # reports/AUDIT_STAT_VALIDATION_2026-05-22.md.)
            b["closed"] += 1
            # C2 / claim A4 (reports/crypto_edge_artifact_audit_2026_05_17.md):
            # the verdict aggregate must use NET pnl (after round-trip
            # execution cost), not gross. A near-zero gross "win" is a real
            # loss after fees; gross PF overstates the edge.
            pnl = deduct_slippage(float(p.get("pnl_pct", 0) or 0), ac)
            b["pnl"] += pnl
            sym = str(p.get("symbol") or "")
            if sym:
                ac_sym_pnl[ac][sym] = ac_sym_pnl[ac].get(sym, 0.0) + abs(pnl)
            strat = str(p.get("strategy") or "")
            if strat:
                ac_strat_pnl[ac][strat] = ac_strat_pnl[ac].get(strat, 0.0) + abs(pnl)
            if pnl > 0:
                b["wins"] += 1
                b["win_pnl"] += pnl
            elif pnl < 0:
                b["losses"] += 1
                b["loss_pnl"] += pnl
            else:
                b["flat"] += 1

    for ac, b in ac_breakdown.items():
        total = b["wins"] + b["losses"]
        b["win_rate"] = round(b["wins"] / total * 100, 1) if total > 0 else 0
        b["pnl"] = round(b["pnl"], 2)
        b["avg_win"] = round(b["win_pnl"] / b["wins"], 2) if b["wins"] > 0 else 0
        b["avg_loss"] = (
            round(abs(b["loss_pnl"]) / b["losses"], 2) if b["losses"] > 0 else 0
        )
        b["profit_factor"] = (
            round(b["win_pnl"] / abs(b["loss_pnl"]), 2) if b["loss_pnl"] < 0 else None
        )
        wr_frac = b["win_rate"] / 100
        b["expectancy"] = (
            round((wr_frac * b["avg_win"]) - ((1 - wr_frac) * b["avg_loss"]), 2)
            if total > 0
            else 0
        )
        # Clean up internal fields
        del b["win_pnl"]
        del b["loss_pnl"]

    # M-067: prefer the canonical pf_registry.json (net, policy-clean) as the
    # single source of truth. _registry_backed_ac_breakdown() returns None —
    # and we fall back to the in-generator recompute — unless AUDIT_HEALTH_SOURCE
    # is "registry" AND the registry is present, canonical and fresh. The
    # locally-built ac_breakdown is still computed above because ac_sym_pnl /
    # ac_strat_pnl feed the concentration disclosure block below.
    _registry_breakdown = _registry_backed_ac_breakdown()
    if _registry_breakdown is not None:
        asset_class_health = compute_asset_class_health(_registry_breakdown)
    else:
        asset_class_health = compute_asset_class_health(ac_breakdown)

    # 2026-05-12 P0-#2: per-class symbol concentration disclosure.
    # WARN default at share>=0.70; BLOCK opt-in via env at share>=0.85.
    # Surfaces "CT=F drives 89% of COMMODITY PnL" so a phantom-class
    # edge can be spotted without a system-level autopsy.
    _ASSET_CLASS_CONCENTRATION_WARN = 0.70
    _ASSET_CLASS_CONCENTRATION_BLOCK = float(
        os.environ.get("ASSET_CLASS_CONCENTRATION_BLOCK_THRESHOLD", "0.85")
    )
    _ASSET_CLASS_CONCENTRATION_ENFORCE = (
        os.environ.get("ASSET_CLASS_CONCENTRATION_ENFORCE", "0") == "1"
    )
    # 2026-05-13 SPORTS-removal: exclude sports-betting from concentration
    # (already excluded from asset_class_health at 5409-5413). Sports lives
    # at /live-monitor/sports-betting.html with separate KPIs; mixing pollutes
    # alpha-trading verdicts.
    _CONC_SPORTS_EXCLUDED = {"SPORTS", "BETTING", "SPORT", "BET"}
    asset_class_concentration: dict = {}
    for ac_key, sym_pnl_map in (ac_sym_pnl or {}).items():
        ac_upper = str(ac_key).upper()
        if ac_upper in _CONC_SPORTS_EXCLUDED:
            continue
        strat_pnl_map = ac_strat_pnl.get(ac_key, {}) or {}
        if not sym_pnl_map:
            asset_class_concentration[ac_upper] = {
                "top_symbol": None,
                "top_share_pct": 0.0,
                "top_strategy": None,
                "top_strategy_share_pct": 0.0,
                "is_concentrated_warn": False,
                "is_concentrated_block": False,
                "tier": "OK",
            }
            continue
        _top_sym, _top_pnl_mass = max(sym_pnl_map.items(), key=lambda kv: kv[1])
        _denom = sum(sym_pnl_map.values())
        _share = (_top_pnl_mass / _denom) if _denom > 0 else 0.0
        # A3 extension: per-strategy top-share within the same class
        _top_strat = None
        _top_strat_mass = 0.0
        _strat_share = 0.0
        if strat_pnl_map:
            _top_strat, _top_strat_mass = max(strat_pnl_map.items(), key=lambda kv: kv[1])
            _strat_denom = sum(strat_pnl_map.values())
            _strat_share = (_top_strat_mass / _strat_denom) if _strat_denom > 0 else 0.0
        if _share >= _ASSET_CLASS_CONCENTRATION_BLOCK:
            _tier = "BLOCK"
        elif _share >= _ASSET_CLASS_CONCENTRATION_WARN:
            _tier = "WARN"
        else:
            _tier = "OK"
        # Compose a one-sentence honest description for the dashboard banner.
        # Example: "COMMODITY edge = multi_asset_cot on CT=F (75% of class PnL)"
        _label = None
        if _top_sym and _top_strat:
            _label = f"{ac_upper} edge = {_top_strat} on {_top_sym} ({round(_share*100)}% of class PnL)"
        asset_class_concentration[ac_upper] = {
            "top_symbol": _top_sym,
            "top_share_pct": round(_share * 100, 2),
            "top_symbol_pnl_mass_pct": round(_top_pnl_mass, 2),
            "total_pnl_mass_pct": round(_denom, 2),
            "top_strategy": _top_strat,
            "top_strategy_share_pct": round(_strat_share * 100, 2),
            "top_strategy_pnl_mass_pct": round(_top_strat_mass, 2),
            "is_concentrated_warn": _share >= _ASSET_CLASS_CONCENTRATION_WARN,
            "is_concentrated_block": _share >= _ASSET_CLASS_CONCENTRATION_BLOCK,
            "tier": _tier,
            "honest_label": _label,
            "sizing_block_applied": (
                _share >= _ASSET_CLASS_CONCENTRATION_BLOCK
                and _ASSET_CLASS_CONCENTRATION_ENFORCE
            ),
        }

    # =========================================================================
    # Hourly Performance by Asset Class (last 24 hours)
    # =========================================================================
    def _compute_hourly_performance_24h(
        active: list[dict],
        recent_closed: list[dict],
        now_iso: str,
    ) -> dict:
        """Compute per-hour performance breakdown by asset class for the last 24h."""
        try:
            now_dt = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
            if now_dt.tzinfo is None:
                now_dt = now_dt.replace(tzinfo=timezone.utc)
        except Exception:
            now_dt = datetime.now(timezone.utc)

        cutoff = now_dt - timedelta(hours=24)
        hours: list[dict] = []
        all_acs: set[str] = set()

        for i in range(24):
            h_start = cutoff + timedelta(hours=i)
            h_end = h_start + timedelta(hours=1)
            h_label = h_start.strftime("%Y-%m-%d %H:00")

            # Active picks created in this hour
            h_active = []
            for p in active:
                try:
                    t = p.get("created_at") or p.get("timestamp") or ""
                    if not t:
                        continue
                    pt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                    if pt.tzinfo is None:
                        pt = pt.replace(tzinfo=timezone.utc)
                    if h_start <= pt < h_end:
                        h_active.append(p)
                except Exception:
                    pass

            # Closed picks resolved in this hour
            h_closed = []
            for p in recent_closed:
                try:
                    t = p.get("closed_at") or ""
                    if not t:
                        continue
                    pt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                    if pt.tzinfo is None:
                        pt = pt.replace(tzinfo=timezone.utc)
                    if h_start <= pt < h_end:
                        h_closed.append(p)
                except Exception:
                    pass

            # Group by asset class
            ac_data: dict[str, dict] = {}
            all_picks = h_active + h_closed
            for p in all_picks:
                ac = p.get("asset_class") or "CRYPTO"
                if ac not in ac_data:
                    ac_data[ac] = {
                        "wins": 0, "losses": 0, "flat": 0,
                        "pnl": 0.0, "win_pnl": 0.0, "loss_pnl": 0.0,
                        "active_count": 0,
                    }
                    all_acs.add(ac)
                d = ac_data[ac]
                if p.get("status") == "OPEN":
                    d["active_count"] += 1
                else:
                    pnl = float(p.get("pnl_pct") or 0)
                    d["pnl"] += pnl
                    if pnl > 0:
                        d["wins"] += 1
                        d["win_pnl"] += pnl
                    elif pnl < 0:
                        d["losses"] += 1
                        d["loss_pnl"] += pnl
                    else:
                        d["flat"] += 1

            # Finalize metrics per asset class
            by_asset_class: dict[str, dict] = {}
            for ac, d in ac_data.items():
                total = d["wins"] + d["losses"] + d["flat"]
                by_asset_class[ac] = {
                    "active": d["active_count"],
                    "new": len(h_active),
                    "wins": d["wins"],
                    "losses": d["losses"],
                    "flat": d["flat"],
                    "total": total,
                    "win_rate": round(d["wins"] / total * 100, 1) if total > 0 else None,
                    "pnl": round(d["pnl"], 2),
                    "avg_win": round(d["win_pnl"] / d["wins"], 2) if d["wins"] > 0 else None,
                    "avg_loss": round(abs(d["loss_pnl"]) / d["losses"], 2) if d["losses"] > 0 else None,
                }

            total_wins = sum(d["wins"] for d in ac_data.values())
            total_losses = sum(d["losses"] for d in ac_data.values())
            total_flat = sum(d["flat"] for d in ac_data.values())
            total_trades = total_wins + total_losses + total_flat
            total_pnl = sum(d["pnl"] for d in ac_data.values())

            hours.append({
                "hour": h_label,
                "hour_unix": int(h_start.timestamp()),
                "new_picks": len(h_active),
                "closed_picks": len(h_closed),
                "wins": total_wins,
                "losses": total_losses,
                "flat": total_flat,
                "total": total_trades,
                "win_rate": round(total_wins / total_trades * 100, 1) if total_trades > 0 else None,
                "pnl": round(total_pnl, 2),
                "by_asset_class": by_asset_class,
            })

        # Summary totals by asset class across all 24 hours
        ac_totals: dict[str, dict] = {}
        for h in hours:
            for ac, d in h["by_asset_class"].items():
                if ac not in ac_totals:
                    ac_totals[ac] = {
                        "wins": 0, "losses": 0, "flat": 0,
                        "active": 0, "new": 0, "pnl": 0.0,
                    }
                t = ac_totals[ac]
                t["wins"] += d["wins"]
                t["losses"] += d["losses"]
                t["flat"] += d["flat"]
                t["active"] += d["active"]
                t["new"] += d["new"]
                t["pnl"] += d["pnl"]

        summary_by_ac: dict[str, dict] = {}
        for ac, t in ac_totals.items():
            total = t["wins"] + t["losses"] + t["flat"]
            summary_by_ac[ac] = {
                "active": t["active"],
                "new": t["new"],
                "wins": t["wins"],
                "losses": t["losses"],
                "flat": t["flat"],
                "total": total,
                "win_rate": round(t["wins"] / total * 100, 1) if total > 0 else None,
                "pnl": round(t["pnl"], 2),
            }

        return {
            "hours": hours,
            "summary_by_asset_class": summary_by_ac,
            "generated_at": now_iso,
            "cutoff_hours": 24,
        }

    # NOTE: _compute_hourly_performance_24h call moved below recent_closed
    # assignment (was at this location, which raised UnboundLocalError since
    # recent_closed is assigned ~60 lines down and Python scope-hoists local
    # names for the whole function body — see fix PR for details).

    # =========================================================================
    # Strategy Pruning: Remove noise / dead strategies from dashboard payload
    # =========================================================================
    _strat_pnl = defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0, "pnl": 0.0})
    for p in resolved_closed:
        s = p.get("strategy", "unknown")
        pnl = float(p.get("pnl_pct", 0) or 0)
        _strat_pnl[s]["total"] += 1
        _strat_pnl[s]["pnl"] += pnl
        if p.get("status") in ("WON", "WIN", "TP_HIT"):
            _strat_pnl[s]["wins"] += 1
        elif p.get("status") in ("LOST", "LOSS", "SL_HIT"):
            _strat_pnl[s]["losses"] += 1

    _active_strats = {p.get("strategy", "unknown") for p in active}

    _dead_strats = set()
    for s, stats in _strat_pnl.items():
        if s in _active_strats:
            continue  # Keep anything currently active

        wr = stats["wins"] / stats["total"] if stats["total"] else 0
        avg_pnl = stats["pnl"] / stats["total"] if stats["total"] else 0

        # Kill if: (low sample) OR (proven loser) OR (negative pnl)
        if stats["total"] < 3:
            _dead_strats.add(s)
        elif stats["total"] >= 5 and wr < 0.30:
            _dead_strats.add(s)
        elif stats["total"] >= 3 and avg_pnl < -3.0:
            _dead_strats.add(s)

    if _dead_strats:
        # Never drop non-crypto closed rows for "dead" strategies — strategy pruning
        # is for crypto HFT noise. Removing e.g. hyperopt_connors_rsi2 (5L, 0% WR)
        # erased entire FUTURES audit history from NC cards + drill-down (cursor 2026-04-02).
        def _strategy_prune_keep_pick(p: dict) -> bool:
            s = str(p.get("strategy", "unknown") or "unknown")
            if s not in _dead_strats:
                return True
            if nc_asset_category_for_pick(p) is not None:
                return True
            return False

        _pre_nc = sum(1 for p in resolved_closed if nc_asset_category_for_pick(p))
        resolved_closed = [p for p in resolved_closed if _strategy_prune_keep_pick(p)]
        closed = [p for p in closed if _strategy_prune_keep_pick(p)]
        _post_nc = sum(1 for p in resolved_closed if nc_asset_category_for_pick(p))
        log.info(
            "Pruning %d dead/noise strategies from dashboard payload (non-crypto closed preserved: %d -> %d rows)",
            len(_dead_strats),
            _pre_nc,
            _post_nc,
        )

    # Cap closed picks for payload size, but reserve a slice for PM / copy-trader
    # track-record sources so the closed tab and CSV export do not erase their
    # realized history behind bulk HFT / baby-strategy ledgers.
    recent_closed = _build_recent_closed_picks(
        resolved_closed,
        max_picks=MAX_CLOSED_PICKS,
        reserved_slots=RESERVED_TRACK_RECORD_CLOSED_PICKS,
    )

    # Compute hourly performance AFTER recent_closed is built. Previously this
    # call lived above the strategy-pruning block which caused UnboundLocalError
    # at runtime — dashboard workflow had been failing since 2026-04-12 22:18Z.
    hourly_24h = _compute_hourly_performance_24h(active, recent_closed, now)

    # ── Build symbol+direction to systems map for cross-system analysis ──
    # P2 (peer review): use deduped/pruned resolved_closed — not raw closed — so agreement SETs
    # match the headline performance truth set (junk mirror rows excluded).
    symdir_systems = defaultdict(set)
    for pick in active + resolved_closed:
        key = (_normalize_symbol(pick.get("symbol", "")), pick.get("direction"))
        sys_name = pick.get("source_system", "unknown")
        symdir_systems[key].add(sys_name)

    # Add source_systems to each pick
    for pick in active + closed:
        key = (_normalize_symbol(pick.get("symbol", "")), pick.get("direction"))
        if _is_prediction_market_pick(
            str(pick.get("source_system", "") or ""),
            str(pick.get("source_system", "") or ""),
            pick,
            str(pick.get("strategy", "") or ""),
        ) and not pick.get("pm_source_systems"):
            existing_pm_sources = pick.get("source_systems", []) or []
            if isinstance(existing_pm_sources, list) and existing_pm_sources:
                pick["pm_source_systems"] = list(existing_pm_sources)
        pick["source_systems"] = sorted(symdir_systems[key])
        pick["system_agreement_count"] = len(symdir_systems[key])

    # ── Per (strategy, symbol) closed stats for TRACK column + tooltips ──
    # Use resolved_closed (deduped / metric-grade) so symbol n/WR matches forward ledger truth.
    _strategy_symbol_track_map = _build_strategy_symbol_track_stats(resolved_closed)
    _source_symbol_track_map = _build_source_symbol_track_stats(resolved_closed)

    # ── Universal Forward Stats: compute forward_wr/forward_trades for ALL systems ──
    # Build lookup: (source_system, strategy) -> {wins, losses, total, pnl_sum}
    _fwd_by_sys_strat = {}  # key: "sys::strategy"
    _fwd_by_sys = {}  # key: "sys"
    _fwd_by_strat = {}  # key: "strategy"
    for cp in closed:
        sys_name = cp.get("source_system", "")
        strat = cp.get("strategy", "")
        status = (cp.get("status") or cp.get("outcome") or "").upper()
        pnl = float(cp.get("pnl_pct", 0) or 0)
        is_win = status in ("WON", "WIN", "TP_HIT", "CLOSED_TP")
        is_loss = status in ("LOST", "LOSS", "SL_HIT", "CLOSED_SL")

        for key_name, key_val in [
            ("sys_strat", f"{sys_name}::{strat}"),
            ("sys", sys_name),
            ("strat", strat),
        ]:
            store = {
                "sys_strat": _fwd_by_sys_strat,
                "sys": _fwd_by_sys,
                "strat": _fwd_by_strat,
            }[key_name]
            if key_val and key_val != "::":
                if key_val not in store:
                    store[key_val] = {"wins": 0, "losses": 0, "total": 0, "pnl": 0.0}
                store[key_val]["total"] += 1
                store[key_val]["pnl"] += pnl
                if is_win:
                    store[key_val]["wins"] += 1
                if is_loss:
                    store[key_val]["losses"] += 1


    def _get_fwd_stats(sys_name, strat):
        """Get best available forward stats: sys+strat > strat > sys."""
        key = f"{sys_name}::{strat}"
        if key in _fwd_by_sys_strat and _fwd_by_sys_strat[key]["total"] >= 1:
            return _fwd_by_sys_strat[key]
        if strat and strat in _fwd_by_strat and _fwd_by_strat[strat]["total"] >= 1:
            return _fwd_by_strat[strat]
        if sys_name and sys_name in _fwd_by_sys and _fwd_by_sys[sys_name]["total"] >= 1:
            return _fwd_by_sys[sys_name]
        return None

    # ── Load walk-forward validation results for strategy enrichment ──
    _wf_lookup = {}
    # Per-asset-class walk-forward block (PR #654 walk_forward_by_class()).
    # Surfaced on /audit dashboard MAJOR GOAL banner card. Restored after
    # accidental removal in PR #665 (see issue #696).
    _wf_by_class: dict = {}
    _wf_results_generated_at = None
    try:
        _wf_path = ROOT / "alpha_engine" / "data" / "walkforward_results.json"
        if _wf_path.exists():
            _wf_data = json.loads(_wf_path.read_text(encoding="utf-8"))
            for _wfs in _wf_data.get("strategies", []):
                _wf_lookup[(_wfs.get("strategy") or "").lower()] = _wfs
            log.info("  Walk-forward results loaded: %d strategies", len(_wf_lookup))
            # Pull by_class block (alpha_engine/walkforward_validator.py:424).
            # Empty/missing → graceful no-op; template renders "no data".
            _wf_by_class_raw = _wf_data.get("by_class") or {}
            if isinstance(_wf_by_class_raw, dict):
                _wf_by_class = _wf_by_class_raw
            _wf_results_generated_at = _wf_data.get("generated_at")
            log.info("  Walk-forward by_class: %d asset classes", len(_wf_by_class))
    except Exception as e:
        log.warning("  Walk-forward results failed (non-fatal): %s", e)

    # Charter §7 P0.5-3 wire-up 2026-05-13. Stamp drift-circuit-breaker
    # verdicts onto asset_class_health using walk-forward baseline + 30-day
    # realized WR from recent_closed. When realized WR drops more than
    # 2-sigma below backtest, override sizing_allowed=False. See
    # alpha_engine/charter_drift_circuit_breaker.py + tests.
    try:
        from alpha_engine.charter_drift_circuit_breaker import evaluate_all_classes
        _cb_verdicts = evaluate_all_classes(recent_closed, _wf_by_class)
        for _ac, _verdict in _cb_verdicts.items():
            if _ac in asset_class_health:
                asset_class_health[_ac]["circuit_breaker"] = {
                    "breached": _verdict["breached"],
                    "reason": _verdict["reason"],
                    "realized_wr_30d": _verdict["realized_wr_30d"],
                    "realized_n_30d": _verdict["realized_n_30d"],
                }
                if _verdict["breached"]:
                    asset_class_health[_ac]["sizing_allowed"] = False
        log.info("  Drift circuit-breaker verdicts stamped on %d classes",
                 len(_cb_verdicts))
    except Exception as e:
        log.warning("  Drift circuit-breaker wire failed (non-fatal): %s", e)

    # 60-day recent-window enrichment (swarm round 2 follow-up). Surfaces
    # pf_60d/wr_60d/n_60d so consumers can detect baseline shifts (e.g.,
    # COMMODITY headline PF 4.03 vs historical 1.78) without reading the
    # raw closed list. Fail-open: any error is logged and skipped.
    try:
        enrich_health_with_recent_window(asset_class_health, recent_closed)
        log.info("  asset_class_health 60d-window stamped")
    except Exception as e:
        log.warning("  60d-window enrichment failed (non-fatal): %s", e)

    # ── Opt B: Tier-1 walk-forward promotion gate ──
    # Per reports/tradingview_backtest_benchmark_2026-05-11.md. Re-tier any
    # tier2_proven_strategies card that earned "Tier 1" from classic thresholds
    # but fails walk-forward consistency >=60% AND oos_sharpe>0. Downgrade
    # to "Tier 2" with an explicit walkforward_gate_failed reason.
    # Phase 1.5.3 (real-money-edge plan v2): walk-forward by_class is ADVISORY ONLY
    # while concept_drift.drift_alert==TRUE. 3-engine swarm unanimous (deepseek+xai
    # +cerebras) consensus: OOS distribution non-stationary during regime collapse;
    # PF>1.5 can be regime artefact not edge. Demote nothing while drift is hot;
    # tag Tier-1 cards as ADVISORY pending drift clearance.
    try:
        _drift_alert_hot = False
        try:
            import json as _json2
            from pathlib import Path as _Path2
            _dd_path = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
            if _dd_path.exists():
                with open(_dd_path, "r", encoding="utf-8") as _fh:
                    _drift_alert_hot = bool(
                        (
                            (_json2.load(_fh).get("hf_stats") or {}).get("concept_drift") or {}
                        ).get("drift_alert")
                    )
        except Exception:
            _drift_alert_hot = False

        if _wf_by_class and tier2_proven_strategies and tier2_proven_strategies.get("cards"):
            _gate_demotions = []
            for _card in tier2_proven_strategies["cards"]:
                if (_card.get("tier") or "") != "Tier 1":
                    continue
                _passed, _reason = _walkforward_promotion_gate(
                    asset_classes=_card.get("asset_classes") or [],
                    wf_by_class=_wf_by_class,
                )
                _card["walkforward_gate"] = {
                    "passed": _passed,
                    "reason": _reason,
                    "drift_alert_hot": _drift_alert_hot,
                    "advisory_only": _drift_alert_hot,
                }
                if not _passed:
                    if _drift_alert_hot:
                        # Phase 1.5.3: do NOT demote during drift — advisory tag only
                        _card["tier_reason"] = (
                            f"Tier-1 classical pass, walk-forward gate fail "
                            f"(ADVISORY ONLY — drift_alert TRUE; demotion deferred): {_reason}"
                        )
                    else:
                        _gate_demotions.append({
                            "name": _card.get("name"),
                            "from_tier": "Tier 1",
                            "to_tier": "Tier 2",
                            "reason": _reason,
                        })
                        _card["tier"] = "Tier 2"
                        _card["tier_reason"] = (
                            f"Tier-1 classical pass, walk-forward gate fail: {_reason}"
                        )
                        _card["is_strict_tier2"] = True
            if _gate_demotions:
                tier2_proven_strategies["walkforward_gate_demotions"] = _gate_demotions
                log.info(
                    "  Opt-B walk-forward gate demoted %d Tier-1 cards to Tier 2",
                    len(_gate_demotions),
                )
            elif _drift_alert_hot:
                log.info(
                    "  Opt-B walk-forward gate ADVISORY-ONLY (drift_alert=TRUE); demotions deferred"
                )
    except Exception as _wfg_exc:
        log.warning("  Opt-B walk-forward promotion gate failed (non-fatal): %s", _wfg_exc)

    # ── Enrich active picks with strategy leaderboard stats ──
    # Collision-safe dual lookup (Agent F, follow-up to PR #160):
    #   * ``strat_lookup`` — legacy name-keyed (for backward compat with any
    #     caller that falls back to strategy name alone).
    #   * ``strat_lookup_by_sys_strat`` — preferred composite key
    #     ``"{source_system}::{strategy}"`` so two feeder systems that share
    #     a strategy tag get their own independent leaderboard row.
    strat_lookup: dict[str, dict] = {}
    strat_lookup_by_sys_strat: dict[str, dict] = {}
    for s in leaderboard:
        name = (s.get("strategy") or "").strip()
        if not name:
            continue
        src = (s.get("source_system") or "").strip()
        if src:
            composite = f"{src}::{name}"
            strat_lookup_by_sys_strat[composite] = s
            # Don't clobber the legacy name-keyed row with per-(sys,strat)
            # rows — we want the name key to continue to resolve to the
            # by-name aggregate (which external BT/baby-strat sources have
            # merged into), not to an arbitrary first-seen per-system row.
            continue
        strat_lookup[name] = s
        nk = _normalize_strategy_tooltip_key(name)
        if nk and nk not in strat_lookup:
            strat_lookup[nk] = s
    conflict_symbols = set()
    for c in _detect_conflicts(active):
        conflict_symbols.add(
            c.get("symbol", "")
        )  # already normalized by _detect_conflicts
    # Build recent PnL metrics from closed picks per strategy
    _recent_strat = {}
    for pick in sorted(closed, key=lambda x: x.get("timestamp", ""), reverse=True):
        sn = pick.get("strategy", "")
        if not sn:
            continue
        if sn not in _recent_strat:
            _recent_strat[sn] = []
        if len(_recent_strat[sn]) < 10:
            _recent_strat[sn].append(pick.get("pnl_pct", 0) or 0)

    _snapshot_at_issue_for_recent_closed(recent_closed, pre_leaderboard=True)

    # Leakage-free shadow metric: stamp sym_track_wr_pit / sym_track_total_pit
    # (point-in-time, strictly-earlier history only) alongside the all-time
    # sym_track_wr stamped in the loop below. See
    # reports/AUDIT_STAT_VALIDATION_2026-05-22.md.
    _stamp_pit_sym_track(active + recent_closed, resolved_closed)

    for pick in active + recent_closed:
        strat_name = pick.get("strategy", "")
        pick_src = (pick.get("source_system") or "").strip()
        # Prefer the collision-safe (source_system, strategy) row so picks
        # from two different feeder systems sharing the same strategy tag
        # don't cross-contaminate their forward stats. Fall back to the
        # legacy name-keyed lookup if no per-system row exists.
        lb = {}
        if pick_src and strat_name:
            lb = strat_lookup_by_sys_strat.get(f"{pick_src}::{strat_name}", {}) or {}
        if not lb:
            lb = _resolve_leaderboard_row(strat_lookup, pick, strat_name)
        # ML group fallback: if resolved row has < 5 fwd_trades and
        # strategy is an ML sub-strategy, try the ML group row instead.
        if not lb or (lb.get("fwd_trades", 0) or 0) < 5:
            ml_group = _ml_group_name(strat_name)
            if ml_group and ml_group in strat_lookup:
                group_lb = strat_lookup[ml_group]
                # Use group row if it has more trades than individual row
                if (group_lb.get("fwd_trades", 0) or 0) > (lb.get("fwd_trades", 0) or 0):
                    lb = group_lb

        pick["strat_fwd_wr"] = lb.get("fwd_wr")
        pick["strat_fwd_pf"] = lb.get("fwd_pf")
        pick["strat_fwd_trades"] = lb.get("fwd_trades", 0)
        # v101: Walk-forward validation scores from walkforward_validator.py
        wf_strat = None
        for _wf_cand in _leaderboard_name_candidates_for_pick(pick, strat_name):
            wf_strat = _wf_lookup.get(_wf_cand.lower())
            if wf_strat:
                break
        if wf_strat:
            pick["wf_p_value"] = wf_strat.get("p_value")
            pick["wf_final_score"] = wf_strat.get("final_score")
            pick["wf_verdict"] = wf_strat.get("verdict")
            pick["wf_oos_wr"] = wf_strat.get("wf_oos_wr")
        # track_level: 'symbol' if 3+ symbol-specific trades, 'strategy' if 5+ strategy trades, else 'none'
        # Template uses this to decide bold (symbol-specific) vs italic (strategy-wide) vs dash (no data)
        _fwd_t = lb.get("fwd_trades", 0) or 0
        # Count symbol-specific trades for this strategy from closed picks
        _pick_sym = _normalize_symbol(pick.get("symbol", ""))
        # Resolve wrapper strategy names to base for counting (e.g. "super signal via X" -> X)
        _count_strat = strat_name
        if strat_name:
            _sn_low = strat_name.lower()
            if "via " in _sn_low:
                _count_strat = strat_name.split("via ", 1)[-1].strip().strip(",).(") or strat_name
            elif " (" in strat_name and "consensus" in _sn_low:
                try:
                    _inner = strat_name.split("(", 1)[1].rstrip(")").split(",")[0].strip()
                    if _inner: _count_strat = _inner
                except Exception: pass
        _sym_trades = (
            sum(
                1
                for cp in closed
                if (cp.get("strategy", "") == strat_name or cp.get("strategy", "") == _count_strat)
                and _normalize_symbol(cp.get("symbol", "")) == _pick_sym
            )
            if strat_name and _pick_sym
            else 0
        )
        # Super-signal `via` is source_system; closed rows use real strategy ids — count by feeder system.
        if strat_name and _pick_sym:
            _low_tr = strat_name.lower()
            if _low_tr.startswith("super signal") and "via " in _low_tr:
                _via_sym = strat_name.split("via ", 1)[-1].strip().strip(",).(")
                _cand_syss = {
                    c.lower() for c in _super_signal_via_feeder_candidates(_via_sym)
                }
                _sym_trades_src = sum(
                    1
                    for cp in resolved_closed
                    if _normalize_symbol(cp.get("symbol", "")) == _pick_sym
                    and (cp.get("source_system") or "").strip().lower() in _cand_syss
                )
                _sym_trades = max(_sym_trades, _sym_trades_src)
        if _sym_trades >= 3:
            pick["track_level"] = "symbol"
        elif _fwd_t >= 5:
            pick["track_level"] = "strategy"
        else:
            pick["track_level"] = "none"
        # Symbol-specific forward stats (same closed ledger as _sym_trades)
        _tkey = _track_stats_key(strat_name, _pick_sym)
        _sym_st = _strategy_symbol_track_map.get(_tkey)
        # Fallback: resolve wrapper strategy names (e.g. "super signal (strong) via X",
        # "moderate consensus (X, Y)") to their underlying base strategy so TRACK populates
        # for aggregated/super-signal picks. 2026-04-05: +26% TRACK coverage on active picks.
        if not _sym_st and strat_name:
            _base = None
            _sn_low = strat_name.lower()
            if "via " in _sn_low:
                # "super signal (strong) via claude_gainer_st" -> "claude_gainer_st"
                _base = strat_name.split("via ", 1)[-1].strip().strip(",).(")
            elif " (" in strat_name and "consensus" in _sn_low:
                # "moderate consensus (claude_gainer_st, mercury2)" -> try first entry
                try:
                    _inner = strat_name.split("(", 1)[1].rstrip(")").split(",")[0].strip()
                    if _inner: _base = _inner
                except Exception: pass
            if _base and _base != strat_name:
                _tkey_fallback = _track_stats_key(_base, _pick_sym)
                _sym_st = _strategy_symbol_track_map.get(_tkey_fallback)
                if _sym_st:
                    pick["track_base_strategy"] = _base  # audit trail for fallback resolution
        # Fallback: leaderboard name candidates (id prefix, BT alias, ML group) when primary
        # strategy string does not match closed-pick keys for this symbol.
        if (
            (not _sym_st or int(_sym_st.get("sym_track_total", 0) or 0) == 0)
            and strat_name
            and _pick_sym
        ):
            _seen_try: set[str] = set()
            for _cand in _leaderboard_name_candidates_for_pick(pick, strat_name):
                if _cand in _seen_try:
                    continue
                _seen_try.add(_cand)
                _tk2 = _track_stats_key(_cand, _pick_sym)
                _st2 = _strategy_symbol_track_map.get(_tk2)
                if _st2 and int(_st2.get("sym_track_total", 0) or 0) > 0:
                    _sym_st = _st2
                    pick["track_sym_lookup_strategy"] = _cand
                    break
        # Super-signal: "via X" is feeder source_system, not closed-row strategy name.
        if (
            (not _sym_st or int(_sym_st.get("sym_track_total", 0) or 0) == 0)
            and strat_name
            and _pick_sym
        ):
            _sn_low = strat_name.lower()
            if _sn_low.startswith("super signal") and "via " in _sn_low:
                _via_raw = strat_name.split("via ", 1)[-1].strip().strip(",).(")
                for _via_try in _super_signal_via_feeder_candidates(_via_raw):
                    _st3 = _source_symbol_track_map.get(
                        _source_symbol_track_key(_via_try, _pick_sym)
                    )
                    if _st3 and int(_st3.get("sym_track_total", 0) or 0) > 0:
                        _sym_st = _st3
                        pick["track_sym_lookup_strategy"] = f"source_system:{_via_try}"
                        break
        if _sym_st:
            pick["sym_track_total"] = _sym_st["sym_track_total"]
            pick["sym_track_wins"] = _sym_st["sym_track_wins"]
            pick["sym_track_losses"] = _sym_st["sym_track_losses"]
            pick["sym_track_wr"] = _sym_st["sym_track_wr"]
            pick["sym_track_pnl"] = _sym_st["sym_track_pnl"]
            if _sym_st["sym_track_total"] >= 1:
                _wr_disp = (
                    ("%s" % _sym_st["sym_track_wr"])
                    if _sym_st["sym_track_wr"] is not None
                    else "n/a"
                )
                pick["track_record_tooltip"] = (
                    "%s closed on %s · WR %s%% · ΣPnL %+.1f%%"
                    % (
                        _sym_st["sym_track_total"],
                        _pick_sym or "?",
                        _wr_disp,
                        _sym_st["sym_track_pnl"],
                    )
                )
        else:
            pick["sym_track_total"] = 0
            pick["sym_track_wins"] = 0
            pick["sym_track_losses"] = 0
            pick["sym_track_wr"] = None
            pick["sym_track_pnl"] = 0.0
        pick["strat_health"] = lb.get("health")
        pick["strat_fwd_expectancy"] = lb.get("fwd_expectancy")
        pick["strat_csr"] = lb.get("fwd_csr")
        pick["strat_last10_wr"] = lb.get("fwd_last10_wr")
        pick["strat_sample_quality"] = lb.get("sample_quality", "insufficient")
        pick["strat_decay"] = lb.get("decay")
        # Backtest metrics for active picks columns
        pick["bt_win_rate"] = lb.get("bt_wr")
        pick["bt_profit_factor"] = lb.get("bt_pf")
        # Recent performance from last 10 closed trades for this strategy
        recent_pnls = _recent_strat.get(strat_name, [])
        if recent_pnls:
            pick["recent_pnl"] = round(sum(recent_pnls), 2)
            cum = 0.0
            peak = 0.0
            max_dd = 0.0
            for p in recent_pnls:
                cum += p
                if cum > peak:
                    peak = cum
                dd = peak - cum
                if dd > max_dd:
                    max_dd = dd
            pick["recent_max_dd"] = round(max_dd, 2) if max_dd > 0 else None
        else:
            pick["recent_pnl"] = None
            pick["recent_max_dd"] = None
        pick["has_conflict"] = (
            _normalize_symbol(pick.get("symbol", "")) in conflict_symbols
        )
        pick["trust_tier"] = get_tier(pick.get("source_system", ""))
        # ── Backfill antigravity_score for picks that skip production_scanner ──
        # Only ~4/61 picks currently have it because only production_scanner
        # emits antigravity_score/antigravity_safe/antigravity_tooltip at
        # alpha_engine/production_scanner.py:443. Backfill using same formula
        # so the AGV column on /audit/ renders for all picks, not just alpha_engine.
        if pick.get("antigravity_score") is None:
            _conf = _float(pick.get("confidence", 0))
            _elite = _float(pick.get("elite_score", 0))
            _score_raw = _float(pick.get("score", 0))
            # Prefer elite_score (0-100), fallback to confidence*100, floor at score
            if _elite > 0:
                _ag = _elite
            elif _conf > 0:
                _ag = _conf * 100
            else:
                _ag = min(_score_raw, 100)
            _ag = max(0, min(100, round(_ag, 1)))
            _wci = _float(pick.get("whale_index", 0))
            _ag_safe = _ag >= 80 and _wci >= 60
            _parts = []
            if _ag >= 80:
                _parts.append("ML/Elite >= 80")
            elif _ag >= 60:
                _parts.append("Confirmed band 60-79")
            elif _ag >= 40:
                _parts.append("Speculative band 40-59")
            else:
                _parts.append("Below institutional threshold")
            if _wci >= 60:
                _parts.append("Whale Index >= 60")
            _tooltip_suffix = (
                " (CLEARED for Paper/Real)"
                if _ag_safe
                else " (Paper only)"
            )
            pick["antigravity_score"] = _ag
            pick["antigravity_safe"] = _ag_safe
            pick["antigravity_tooltip"] = (
                "Safe Trading Protocol: "
                + "; ".join(_parts)
                + _tooltip_suffix
            )
        # Count how many unique SYSTEMS have the same symbol+direction active
        # (not picks — if one system has 10 picks, that's still 1 system agreeing)
        pick_sym = _normalize_symbol(pick.get("symbol", ""))
        pick_dir = pick.get("direction")
        pick_sys = pick.get("source_system")
        agreeing_systems = set()
        agreeing_details = []  # system name + strategy for tooltip
        for p in active:
            p_sys = p.get("source_system")
            if (
                p_sys
                and p_sys != pick_sys
                and _normalize_symbol(p.get("symbol", "")) == pick_sym
                and p.get("direction") == pick_dir
            ):
                agreeing_systems.add(p_sys)
                agreeing_details.append(
                    {
                        "system": p_sys,
                        "strategy": p.get("strategy", "unknown"),
                    }
                )
        pick["agreement_count"] = len(agreeing_systems)
        # Deduplicate by system name, keep first strategy per system
        seen_sys = set()
        unique_details = []
        for d in agreeing_details:
            if d["system"] not in seen_sys:
                seen_sys.add(d["system"])
                unique_details.append(d)
        pick["agreeing_systems"] = unique_details

        # Normalize forward_wr when upstream stores a win-rate fraction (e.g. 0.8182)
        # as a float. Integer1 is treated as 1% (percent points), not 100%.
        _rfw_raw = pick.get("forward_wr")
        if isinstance(_rfw_raw, float) and not isinstance(_rfw_raw, bool):
            _rfw = float(_rfw_raw)
            if 0 < _rfw <= 1.0:
                pick["forward_wr"] = round(_rfw * 100.0, 1)

        # ── Universal forward stats: ensure ALL picks have forward_wr/forward_trades ──
        # Only fill if not already set by a system-specific validator (e.g., alpha_engine)
        if pick.get("forward_trades") is None or pick.get("forward_trades") == 0:
            fwd = _get_fwd_stats(pick.get("source_system", ""), strat_name)
            if fwd:
                total_fwd = fwd["total"]
                wr_fwd = round(fwd["wins"] / total_fwd * 100, 1) if total_fwd > 0 else 0
                pick["forward_trades"] = total_fwd
                pick["forward_wr"] = wr_fwd
                pick["forward_validated"] = total_fwd >= 5 and wr_fwd >= 45
                pick["forward_status"] = (
                    f"{'PASS' if pick['forward_validated'] else 'WATCH'}: "
                    f"{fwd['wins']}W/{fwd['losses']}L from closed picks"
                )
                pick["forward_pnl"] = round(fwd["pnl"], 2)
            else:
                pick["forward_trades"] = 0
                pick["forward_wr"] = 0
                pick["forward_validated"] = False
                pick["forward_status"] = (
                    "NO_DATA: no closed picks found for this system/strategy"
                )
                pick["forward_pnl"] = 0
        # ── Fallback: sync strat_fwd_wr/track_level from universal forward stats ──
        # The leaderboard lookup above only covers strategies with 5+ trades.
        # If not already set, use the universal forward stats so TRACK column shows data.
        # Align with dashboard TRACK column: show strategy-wide WR from universal
        # forward stats when leaderboard row is sparse (threshold 3+ matches insight gates).
        if pick.get("strat_fwd_wr") is None and (pick.get("forward_trades") or 0) >= 3:
            pick["strat_fwd_wr"] = pick.get("forward_wr", 0)
            if not pick.get("strat_fwd_trades"):
                pick["strat_fwd_trades"] = pick["forward_trades"]
            if (pick.get("track_level") or "none") == "none":
                pick["track_level"] = "strategy"  # system-level fallback

    _snapshot_at_issue_for_recent_closed(recent_closed, pre_leaderboard=False)

    # ── Compute trust scores (0-10) for active + published closed picks ──
    # Closed export rows need the same trust context as active picks; otherwise
    # the CSV shows blank trust fields and misleading probation labels.
    try:
        from alpha_engine.trust_score import enrich_picks_with_trust_score

        enrich_picks_with_trust_score(active)
        enrich_picks_with_trust_score(recent_closed)
        log.info(
            "Trust scores computed for %d active picks and %d recent closed picks",
            len(active),
            len(recent_closed),
        )
    except Exception as _ts_err:
        log.warning("Trust score computation failed (non-fatal): %s", _ts_err)

    # ── Bulk RSI/regime enrichment for crypto picks missing data ──
    # Many sources (rapid_fire, incubator, etc.) don't provide RSI/regime.
    # Fetch from Binance for unique symbols, then apply to all picks.
    try:
        import urllib.request as _urllib_req

        _NON_CRYPTO_CLASSES = {"FOREX", "EQUITY", "COMMODITY", "ETF", "FUTURES", "BOND"}

        _rsi_cache: dict = {}
        _regime_data = {}
        try:
            _hmm_path = ROOT / "alpha_engine" / "data" / "hmm_regime.json"
            if _hmm_path.exists():
                _regime_data = json.loads(_hmm_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            pass
        _global_regime = _regime_data.get("aggregate", {}).get(
            "market_regime", _regime_data.get("market_regime", "CHOPPY")
        )

        # Collect unique symbols needing RSI
        _need_rsi = set()
        for _p in active:
            if (_p.get("asset_class") or "").upper() != "CRYPTO":
                continue
            if _p.get("rsi_at_entry") or _p.get("rsi") or _p.get("rsi_14"):
                continue
            _sym = (_p.get("symbol") or "").upper().replace("-", "")
            if (
                (_sym.endswith("USDT") or _sym.endswith("USDC"))
                and _sym.isascii()
                and len(_sym) <= 20
            ):
                _need_rsi.add(_sym)

        log.info("RSI enrichment: %d unique symbols need RSI", len(_need_rsi))

        # Fetch RSI for each — try multiple Binance mirrors (GH Actions often geo-blocked)
        _BINANCE_MIRRORS = [
            "https://api.binance.com",
            "https://api1.binance.com",
            "https://api2.binance.com",
            "https://api3.binance.com",
            "https://data-api.binance.vision",
            "https://api.binance.us",
        ]
        for _sym in sorted(_need_rsi)[:100]:
            _klines = None
            for _base in _BINANCE_MIRRORS:
                try:
                    _url = f"{_base}/api/v3/klines?symbol={_sym}&interval=1h&limit=15"
                    _req = _urllib_req.Request(
                        _url, headers={"User-Agent": "AuditDashboard/1.0"}
                    )
                    with _urllib_req.urlopen(_req, timeout=5) as _resp:
                        _klines = json.loads(_resp.read())
                    if _klines:
                        break
                except Exception:
                    continue
            if not _klines:
                continue
            try:
                _closes = [float(k[4]) for k in _klines]
                _volumes = [float(k[5]) for k in _klines]
                if len(_closes) >= 14:
                    _gains, _losses = [], []
                    for _i in range(1, len(_closes)):
                        _d = _closes[_i] - _closes[_i - 1]
                        _gains.append(max(_d, 0))
                        _losses.append(max(-_d, 0))
                    _ag = sum(_gains[-14:]) / 14
                    _al = sum(_losses[-14:]) / 14
                    _rsi = 100 - (100 / (1 + (_ag / _al))) if _al > 0 else 100
                    _avg_vol = sum(_volumes[:-1]) / max(len(_volumes) - 1, 1)
                    _vol_ratio = (
                        round(_volumes[-1] / _avg_vol, 2) if _avg_vol > 0 else 1.0
                    )
                    _rsi_cache[_sym] = {"rsi": round(_rsi, 1), "vol": _vol_ratio}
            except Exception:
                pass

        log.info(
            "RSI enrichment: fetched %d/%d symbols", len(_rsi_cache), len(_need_rsi)
        )

        # Apply RSI + regime to all crypto picks
        _enriched_count = 0
        for _p in active:
            if (_p.get("asset_class") or "").upper() != "CRYPTO":
                continue
            _sym = (_p.get("symbol") or "").upper().replace("-", "")
            # RSI
            if not (_p.get("rsi_at_entry") or _p.get("rsi")) and _sym in _rsi_cache:
                _p["rsi_at_entry"] = _rsi_cache[_sym]["rsi"]
                _p["rsi"] = _rsi_cache[_sym]["rsi"]
                _p["volume_ratio"] = _rsi_cache[_sym]["vol"]
                _enriched_count += 1
            # Regime
            if not _p.get("regime_at_entry"):
                _p["regime_at_entry"] = _global_regime
            # HTF bias from RSI
            _rsi_val = _p.get("rsi_at_entry") or _p.get("rsi")
            if _rsi_val and not _p.get("htf_bias"):
                _r = float(_rsi_val)
                _p["htf_bias"] = (
                    "BULL" if _r > 55 else ("BEAR" if _r < 45 else "NEUTRAL")
                )

        log.info("RSI enrichment: applied to %d active picks", _enriched_count)
        def _internal_to_yfinance_sym(sym, asset_class):
            """Convert internal symbol to yfinance ticker format."""
            sym = sym.strip().upper()
            ac = (asset_class or "").upper()
            # Forex: 6-char CCY pair -> append =X  (EURUSD -> EURUSD=X)
            if ac == "FOREX" and len(sym) == 6 and not sym.endswith("=X"):
                return sym + "=X"
            # Commodity precious metals
            if sym == "XAUUSD": return "GC=F"
            if sym == "XAGUSD": return "SI=F"
            if sym == "XPDUSD": return "PA=F"
            if sym == "XPTUSD": return "PL=F"
            # Crude oil variants
            if sym in ("CLUSD", "OILUSD", "WTIUSD", "BRENTUSD"): return "CL=F"
            if sym == "NGUSD": return "NG=F"
            # Futures: already have =F suffix or CME codes
            if ac == "FUTURES" and not sym.endswith("=F"):
                return sym.split("=")[0] + "=F"
            return sym

        # ── RSI / VOL enrichment for NON-CRYPTO assets (forex, equity, commodity, ETF, futures) ──
        # Uses yfinance (3mo daily bars) to compute RSI-14 and volume_ratio.
        # Forex spot often lacks volume on Yahoo → volume_ratio set to None.
        _need_nc_rsi: dict[str, str] = {}  # internal_sym -> yfinance_sym
        for _p in active:
            _ac = (_p.get("asset_class") or "").upper()
            if _ac not in _NON_CRYPTO_CLASSES:
                continue
            if _p.get("rsi_at_entry") or _p.get("rsi") or _p.get("rsi_14"):
                continue
            _sym = (_p.get("symbol") or "").strip().upper()
            if not _sym:
                continue
            # Build yfinance ticker via shared helper
            _yf_sym = _internal_to_yfinance_sym(_sym, _ac)
            if _yf_sym not in _need_nc_rsi:
                _need_nc_rsi[_yf_sym] = _sym

        if _need_nc_rsi:
            log.info("Non-crypto RSI enrichment: %d symbols via yfinance", len(_need_nc_rsi))
            try:
                import yfinance as _yf
            except ImportError:
                _yf = None
                log.warning("yfinance not installed, skipping non-crypto RSI enrichment")

            if _yf is not None:
                _nc_cache: dict = {}  # yf_sym -> {rsi, vol}
                # Batch download for equities/ETFs (most efficient)
                _eq_syms = [_yf_sym for _yf_sym in _need_nc_rsi
                            if _need_nc_rsi[_yf_sym] in _EQUITY_SYMBOLS
                            or str(_need_nc_rsi[_yf_sym]).upper().strip() in _EQUITY_SYMBOLS]
                _other_syms = [_yf_sym for _yf_sym in _need_nc_rsi if _yf_sym not in _eq_syms]

                # Batch equity download
                if _eq_syms:
                    try:
                        _eq_df = _yf.download(_eq_syms, period="3mo", interval="1d",
                                               progress=False, threads=True)
                        for _yf_sym in _eq_syms:
                            try:
                                if len(_eq_syms) > 1:
                                    _close = _eq_df["Close"][_yf_sym].dropna()
                                else:
                                    _close = _eq_df["Close"].dropna()
                                _vol_s = None
                                try:
                                    if len(_eq_syms) > 1:
                                        _vol_s = _eq_df["Volume"][_yf_sym].dropna()
                                    else:
                                        _vol_s = _eq_df["Volume"].dropna()
                                except Exception:
                                    pass
                                if len(_close) >= 15:
                                    _closes = _close.values.tolist()
                                    _g, _l = 0.0, 0.0
                                    for _i in range(1, min(15, len(_closes))):
                                        _d = _closes[-_i] - _closes[-_i - 1]
                                        if _d > 0: _g += _d
                                        else: _l -= _d
                                    _g /= 14; _l /= 14
                                    _rsi = 100 - (100 / (1 + (_g / _l))) if _l > 0 else 100
                                    _vr = None
                                    if _vol_s is not None and len(_vol_s) >= 2:
                                        _vols = _vol_s.values.tolist()
                                        _avg_v = sum(_vols[:-1][-20:]) / max(len(_vols[:-1][-20:]), 1)
                                        if _avg_v > 0:
                                            _vr = round(_vols[-1] / _avg_v, 2)
                                    _nc_cache[_yf_sym] = {"rsi": round(_rsi, 1), "vol": _vr}
                            except Exception:
                                pass
                    except Exception:
                        log.warning("yfinance batch download failed for equities")

                # Individual downloads for forex/commodities/futures
                for _yf_sym in _other_syms:
                    try:
                        _tkr = _yf.Ticker(_yf_sym)
                        _hist = _tkr.history(period="3mo", interval="1d")
                        if _hist is None or len(_hist) < 15:
                            continue
                        _closes = _hist["Close"].dropna().values.tolist()
                        if len(_closes) < 15:
                            continue
                        _g, _l = 0.0, 0.0
                        for _i in range(1, min(15, len(_closes))):
                            _d = _closes[-_i] - _closes[-_i - 1]
                            if _d > 0: _g += _d
                            else: _l -= _d
                        _g /= 14; _l /= 14
                        _rsi = 100 - (100 / (1 + (_g / _l))) if _l > 0 else 100
                        _vr = None
                        if "Volume" in _hist.columns:
                            _vols = _hist["Volume"].dropna().values.tolist()
                            if len(_vols) >= 2:
                                _avg_v = sum(_vols[:-1][-20:]) / max(len(_vols[:-1][-20:]), 1)
                                if _avg_v > 0:
                                    _vr = round(_vols[-1] / _avg_v, 2)
                        _nc_cache[_yf_sym] = {"rsi": round(_rsi, 1), "vol": _vr}
                    except Exception:
                        pass

                log.info("Non-crypto RSI: fetched %d/%d symbols", len(_nc_cache), len(_need_nc_rsi))

                # Apply to active picks
                _nc_enriched = 0
                for _p in active:
                    _ac = (_p.get("asset_class") or "").upper()
                    if _ac not in _NON_CRYPTO_CLASSES:
                        continue
                    if _p.get("rsi_at_entry") or _p.get("rsi"):
                        continue
                    _sym = (_p.get("symbol") or "").strip().upper()
                    # Reconstruct yfinance key via shared helper
                    _yf_key = _internal_to_yfinance_sym(_sym, _ac)
                    if _yf_key in _nc_cache:
                        _p["rsi_at_entry"] = _nc_cache[_yf_key]["rsi"]
                        _p["rsi"] = _nc_cache[_yf_key]["rsi"]
                        _p["rsi_source"] = "yfinance_1d"
                        if _nc_cache[_yf_key]["vol"] is not None:
                            _p["volume_ratio"] = _nc_cache[_yf_key]["vol"]
                        # HTF bias
                        if not _p.get("htf_bias"):
                            _r = _nc_cache[_yf_key]["rsi"]
                            _p["htf_bias"] = (
                                "BULL" if _r > 55 else ("BEAR" if _r < 45 else "NEUTRAL")
                            )
                        _nc_enriched += 1
                log.info("Non-crypto RSI: applied to %d active picks", _nc_enriched)


        # ── Persist regime_at_entry + htf_bias on closed picks ──
        # Closed picks historically lacked these fields because enrichment only ran
        # on active picks.  Backfill from the raw source data or derive from RSI
        # so that closed-trade analytics can correlate HTF alignment with outcomes.
        _closed_enriched = 0
        for _p in recent_closed:
            _ac_cl = (_p.get("asset_class") or "").upper()
            if _ac_cl not in {"CRYPTO"} | _NON_CRYPTO_CLASSES:
                continue
            # Regime: persist the regime that was active when the pick was generated
            if not _p.get("regime_at_entry"):
                _p["regime_at_entry"] = _p.get("regime") or _global_regime
            # HTF bias: derive from RSI if available, else from technical verdict
            if not _p.get("htf_bias"):
                _rsi_val = _p.get("rsi_at_entry") or _p.get("rsi")
                if _rsi_val:
                    _r = float(_rsi_val)
                    _p["htf_bias"] = (
                        "BULL" if _r > 55 else ("BEAR" if _r < 45 else "NEUTRAL")
                    )
                else:
                    # Fallback: use technical_verdict if available
                    _tv = str(
                        _p.get("technical_v_4h")
                        or _p.get("technical_v_1d")
                        or ""
                    ).upper()
                    if "BUY" in _tv:
                        _p["htf_bias"] = "BULL"
                    elif "SELL" in _tv:
                        _p["htf_bias"] = "BEAR"
                    elif _tv:
                        _p["htf_bias"] = "NEUTRAL"
                if _p.get("htf_bias"):
                    _closed_enriched += 1
        log.info("Closed pick enrichment: htf_bias/regime backfilled on %d closed picks", _closed_enriched)

    except Exception as _rsi_err:
        log.warning("RSI bulk enrichment failed (non-fatal): %s", _rsi_err)

    # ── ML Health monitoring ──
    ml_health = []
    try:
        # 1. KIMI ML Ranker
        kimi_weights_path = ROOT / "KIMI_RISEOFTHECLAW" / "data" / "ml_weights.json"
        if kimi_weights_path.exists():
            kimi_w = json.loads(kimi_weights_path.read_text(encoding="utf-8", errors="replace"))
            ml_health.append(
                {
                    "system": "KIMI ML Ranker",
                    "model_type": "RandomForest (200 trees)",
                    "mode": kimi_w.get("mode", "unknown"),
                    "cv_auc": kimi_w.get("cv_auc"),
                    "updated_at": kimi_w.get("updated_at", ""),
                    "status": "active"
                    if kimi_w.get("mode") != "heuristic"
                    else "heuristic_fallback",
                    "link": "https://findtorontoevents.ca/riseoftheclaw.html",
                }
            )

        # 2. Alpha Engine ML Ranker
        alpha_weights_path = ROOT / "alpha_engine" / "data" / "ml_weights.json"
        if alpha_weights_path.exists():
            alpha_w = json.loads(alpha_weights_path.read_text(encoding="utf-8", errors="replace"))
            ml_health.append(
                {
                    "system": "Alpha Engine ML Ranker",
                    "model_type": "XGBoost (300 trees)",
                    "mode": "ml" if alpha_w.get("model_trained") else "heuristic",
                    "updated_at": alpha_w.get("generated_at", ""),
                    "status": "active"
                    if alpha_w.get("model_trained")
                    else "heuristic_fallback",
                    "link": "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/",
                }
            )

        # 3. Claude Gainer ML
        gainer_meta_path = ROOT / "claude_gainer_ml" / "models" / "training_meta.json"
        if gainer_meta_path.exists():
            gainer_m = json.loads(gainer_meta_path.read_text(encoding="utf-8", errors="replace"))
            gainer_auc = (gainer_m.get("metrics") or {}).get("roc_auc", 0)
            ml_health.append(
                {
                    "system": "Claude Gainer ML",
                    "model_type": "RF+XGBoost Ensemble",
                    "mode": "ml",
                    "cv_auc": gainer_auc,
                    "updated_at": gainer_m.get("trained_at", ""),
                    "version": gainer_m.get("model_version", "?"),
                    "status": "active" if gainer_auc > 0.50 else "anti_predictive",
                    "link": "https://findtorontoevents.ca/updates/antigravity-ml-gainer.html",
                }
            )

        # 4. ML Crypto Predictor (disabled)
        ml_health.append(
            {
                "system": "ML Crypto Predictor",
                "model_type": "RF+GBT+XGB Calibrated Ensemble",
                "mode": "disabled",
                "updated_at": "",
                "status": "disabled",
                "reason": "36.8% WR, -32% PnL",
                "link": "",
            }
        )
    except Exception as e:
        log.warning("ML health collection failed: %s", e)

    final_active_picks = sorted(
        [p for p in active if _is_pre_score_active_candidate(p)],
        key=lambda x: x.get("timestamp", ""),
        reverse=True,
    )
    # Filter self-hedging LONG+SHORT conflicts: keep trust-weighted majority direction
    if _CONFLICT_RESOLVER_AVAILABLE:
        try:
            pre_conflict_count = len(final_active_picks)
            final_active_picks = filter_direction_conflicts(final_active_picks, strategy="trust_weighted")
            removed_by_conflict = pre_conflict_count - len(final_active_picks)
            if removed_by_conflict > 0:
                log.info("Direction conflict resolver: removed %d minority-direction picks", removed_by_conflict)
        except Exception as e:
            log.warning("Direction conflict resolver failed (non-fatal): %s", e)
    total_active_final = len(final_active_picks)
    verified_alpha_summary = _compute_verified_alpha_summary(
        final_active_picks,
        [],
        resolved_closed,
    )
    research_reports = collect_research_reports()
    _repo_sha, _last_code_change_at, _lag_err = _git_head_meta(ROOT)
    _risk_policy = load_risk_policy()
    _last_policy_change_at = (_risk_policy.get("non_crypto") or {}).get("last_policy_change_at")
    _payload_lag_seconds = _compute_payload_lag_seconds(now, _last_code_change_at)

    # ── PCG-5 Portfolio Gate Stack — shadow-mode hook ──────────────────────────
    # Runs all 5 portfolio gates (regime, cross-account, concentration,
    # profit-lock, correlation) across active picks. Shadow mode (PCG5_ENFORCE=0,
    # default) logs results to audit_dashboard/data/pcg5_log.json but does NOT
    # filter picks. Set PCG5_ENFORCE=1 in env to enable live blocking.
    # Wrapped in try/except: never let PCG-5 break the dashboard build.
    _pcg5_shadow_summary: dict = {}
    try:
        from audit_trail.portfolio_gates import evaluate_portfolio_gates as _pcg5_batch
        _pcg5_shadow_summary = _pcg5_batch(
            final_active_picks,
            context={"all_positions": final_active_picks},
        )
        log.info(
            "  PCG-5 shadow gate: n_picks=%d would_reject=%d shadow=%s",
            _pcg5_shadow_summary.get("n_picks", 0),
            _pcg5_shadow_summary.get("n_would_reject", 0),
            _pcg5_shadow_summary.get("shadow_mode", True),
        )
    except Exception as _pcg5_err:
        log.debug("PCG-5 shadow hook failed (non-critical): %s", _pcg5_err)
    # ──────────────────────────────────────────────────────────────────────────

    payload = {
        "generated_at": now,
        "metadata": {
            "generated_at": now,
            "repo_sha": _repo_sha,
            "last_code_change_at": _last_code_change_at,
            "last_code_change_sha": _repo_sha,
            "payload_lag_seconds": _payload_lag_seconds,
            "last_policy_change_at": _last_policy_change_at,
            "lag_compute_error": _lag_err,
        },
        "summary": {
            "total_systems": len(systems),
            "total_active_picks": total_active_final,
            "total_closed_picks": total_closed,
            "valid_closed_picks": len(resolved_closed),
            "headline_closed_unique": len(resolved_closed),  # after dedupe
            "headline_mirror_duplicates_removed": mirror_dupe_count,
            "integrity_excluded": invalid_closed_count,
            "total_resolved": total_resolved,
            "zero_pnl_count": zero_pnl_count,
            "flat_count": zero_pnl_count,
            "auto_expired_excluded": len(all_closed_including_expired) - total_closed,
            "overall_win_rate": overall_wr,
            # total_pnl_pct is now compounded equal-weight (replaces raw additive sum).
            # Kimi audit §1.1 (2026-04-05): raw sum produced misleading -17,657% / -18,126%
            # figures. Compounded equal-weight is the mathematically correct figure
            # (-100% floor = full account drawdown). Raw sum retained below for
            # transparency/debugging as total_pnl_pct_sum_raw.
            "total_pnl_pct": total_pnl_pct_compounded_rolling_100,  # rolling-100 (replaced deprecated EW compound 2026-06-04)
            "total_pnl_pct_sum_raw": total_pnl,  # deprecated, retained for debugging
            "total_pnl_pct_compounded_ew": total_pnl_pct_compounded_ew,  # deprecated — kept for back-compat
            # T1.4 redesign (2026-05-09): bounded headline replacements for the
            # unbounded full-ledger EW compound. Rolling = last 100 trades only;
            # geomean_annualized = ((1 + mu_d/100)^252 - 1) * 100 from daily means.
            "total_pnl_pct_compounded_rolling_100": total_pnl_pct_compounded_rolling_100,
            "total_pnl_pct_geomean_annualized": total_pnl_pct_geomean_annualized,
            "profit_factor": overall_pf,
            "avg_win": overall_avg_win,
            "avg_loss": overall_avg_loss,
            "expectancy": overall_expectancy,
            "total_portfolios": len(portfolios),
            "wins": wins,
            "losses": losses,
            # Mercury validation metrics
            "daily_volatility_pct": mercury_daily_vol,
            "net_sharpe": mercury_net_sharpe,
            "net_sharpe_annual": mercury_net_sharpe_annual,
            # loop2 #6 redesign (2026-05-09): explicit daily-vs-per-trade Sharpe
            # split. Daily = portfolio-aggregate (institutional/Morningstar);
            # per-trade = strategy-quality (each trade independent draw).
            "net_sharpe_daily": mercury_net_sharpe_daily,
            "net_sharpe_daily_annual": mercury_net_sharpe_daily_annual,
            "net_sharpe_per_trade": mercury_net_sharpe_per_trade,
            "net_sharpe_per_trade_annual": mercury_net_sharpe_per_trade_annual,
            "rolling_30d_max_dd": mercury_rolling_30d_dd,
            "signal_to_trade_pct": mercury_signal_to_trade,
            "regime_win_rates": regime_wr if regime_wr else None,
            "daily_pnl_days": len(daily_pnl),
            # Sortino & Calmar ratios
            "sortino_ratio": sortino_ratio,
            "sortino_ratio_annual": sortino_ratio_annual,
            "calmar_ratio": calmar_ratio,
            # Backtest-forward correlation
            "bt_fwd_correlation": bt_fwd_correlation,
            "bt_fwd_correlation_n": bt_fwd_n,
            # Institutional stats cleaner
            "clean_metrics": clean_metrics if clean_metrics else None,
            "timeframe_stats": timeframe_stats if timeframe_stats else None,
            # Quality gate statistics
            "quality_gates_enabled": _QUALITY_GATES_AVAILABLE,
            "quality_stats": {
                "total_active_before_gates": len(active),
                "active_after_gates": total_active_final,
                "smart_picks_count": sum(1 for p in active if passes_smart_gate(p)),
                "smart_picks_percentage": round(
                    sum(1 for p in active if passes_smart_gate(p))
                    / max(total_active_final, 1)
                    * 100,
                    1,
                ),
            }
            if _QUALITY_GATES_AVAILABLE
            else None,
            "non_crypto_performance": compute_non_crypto_performance(
                final_active_picks, resolved_closed
            ),
            "research_report_count": len(research_reports),
            "closed_pnl_concentration": closed_pnl_concentration,
            "big_mover_monitor_3pct": big_mover_monitor_3pct,
            "concentration_summary": concentration_summary,
            "probation_quarantine": probation_quarantine_summary,
        },
        "systems": systems,
        "system_clean_metrics": system_clean_metrics if system_clean_metrics else {},
        "picks": {
            # Keep all asset classes in the active feed. The frontend already has
            # dedicated panels/badges for non-crypto assets, so only malformed
            # rows without a usable strategy are filtered here.
            #
            # QUALITY GATES APPLIED (2026-03-26):
            # - Active Picks: tradeable (entry>0), not stale, not killed strategy
            # - Smart Picks: top quartile score, confidence sweet spot, R:R >= 1.5
            "active": final_active_picks,
            "recent_closed": [_slim_closed_pick(p) for p in recent_closed],
        },
        "portfolios": portfolios,
        "performance": {
            "by_asset_class": ac_breakdown,
            "hourly_24h": hourly_24h,
            "asset_class_health": asset_class_health,
            "asset_class_concentration": asset_class_concentration,
            # Resolver fix Step 4: per-asset-class resolution-coverage metric.
            # resolved_pct = resolved / (resolved + open_non_terminal), plus an
            # unresolved-by-reason breakdown. Reads only the in-memory pick
            # lists (resolved_closed + final_active_picks) — no live DB call.
            "resolution_coverage": _build_resolution_coverage(
                resolved_closed, final_active_picks
            ),
            "asset_class_timeframe_grid": _build_ac_timeframe_grid(final_active_picks),
            "smart_gate_failure_histogram": _build_smart_gate_failure_histogram(active),
        },
        "backtest_vs_forward": bt_vs_fwd,
        "hf_decay_watchlist": hf_decay_watchlist,
        "fwd_vs_bt_divergence": fwd_vs_bt_divergence,
        "macro_context": macro_context,
        "cross_asset_correlation": cross_asset_correlation,
        "sidecar_promotion_status": sidecar_promotion_status,
        "tier2_proven_strategies": tier2_proven_strategies,

        # ── Opt A: TA-baseline panel (TradingView 6-strategy benchmark) ──
        # Per reports/tradingview_backtest_benchmark_2026-05-11.md.
        # Latest reports/tv_backtest_benchmark_*.json loaded for /audit dashboard.
        # Fail-open if no benchmark file present.
        "ta_baseline": _load_latest_ta_baseline(),

        # ── Swarm Pick Tracking — consensus-driven multi-persona picks ──
        # Reads audit_dashboard/data/swarm_{picks,leaderboard,pattern_tags}.json.
        # Consumed by the "Swarm Pick Tracking" panel in template.html.
        # Contract keys (template reads): swarm_picks_data.summary.*,
        # .leaderboard.by_tier, .leaderboard.by_asset_class,
        # .leaderboard.by_underlying_model, .picks[].
        "swarm_picks_data": _load_swarm_picks_data(ROOT / "audit_dashboard" / "data"),

        # ── Walk-forward per-asset-class (PR #654; restored after #665 removal) ──
        # Top-level payload key. Live consumers:
        #   audit_dashboard/template.html:834-864 (MAJOR GOAL banner card)
        #   battleground/app.js:2556 (different schema, graceful fallback)
        # Issue #696 documents the regression history.
        "walkforward": {
            "by_class": _wf_by_class,
            "generated_at": _wf_results_generated_at,
        },

        # ── M-031: Per-class real-money readiness payload ──
        # Derives gate_state / sizing_allowed / sample_tier / tier_vs_charter
        # from asset_class_health (post circuit-breaker enrichment).
        # Consumers: /audit dashboard readiness panel, money-maker-ready skill.
        # Fail-open: missing source data → empty dict for that class.
        "readiness": _build_readiness_payload(asset_class_health, now),

        # ── HF-Grade Statistical Toolbox ──
        "hf_stats": _hf_stats_summary(),
        "bundles": bundles,
        "leaderboard": leaderboard,
        "conflicts": _detect_conflicts(active),
        "consensus": consensus,
        "volatility": volatility,
        "predictions_leaderboard": predictions_lb,
        "analyst_active_calls": _safe_json(
            ROOT / "predictions/data/analyst_active_calls.json"
        )
        or {},
        "analyst_leaderboard": _safe_json(
            ROOT / "predictions/data/analyst_leaderboard.json"
        )
        or {},
        "cross_system_permutations": cross_system_perms,
        "cross_strategy_permutations": cross_strategy_perms,
        "audit_events": audit_events,
        "filter_events": filter_events,
        "regime_validation": regime_validation,
        "performance_alerts": perf_alerts,
        "ml_health": ml_health,
        "data_freshness": _compute_data_freshness(
            ROOT / "alpha_engine" / "data" / "active_picks.json"
        ),
        "smart_picks_feed": smart_picks_feed,
        "smart_picks_snapshot_summary": smart_picks_snapshot_summary,
        "verified_alpha": verified_alpha_summary,
        "research_reports": research_reports,
        "pcg5_shadow_summary": _pcg5_shadow_summary,

        # ── M-061: Statistical readiness (DSR + PBO + SPA per class) ──
        # Richer than M-031 readiness: uses actual pick-level returns for
        # Deflated Sharpe Ratio, Probability of Backtest Overfitting, and
        # Stochastic Permutation test. Fail-open: {} when numpy unavailable.
        "money_ready_verdicts": _money_ready_verdict() if _HAS_MONEY_READY else {},
        # ── Pre-SPA governance: strategies with 5≤n<20 (below SPA testability) ──
        # Surfaces early warning alerts before SPA can formally decide.
        # Fail-open: {} when tools.pending_spa_scan unavailable.
        "pending_spa_alerts": _get_pending_spa_alerts() if _HAS_PENDING_SPA else {},

        # ── M-041: Slippage validation (PR #1026 scaffold wire-in) ──
        # Analyzes bid-ask spread slippage per strategy/asset-class against
        # closed picks. Flags strategies where slippage > 10% of avg PnL
        # (WARNING) or > 25% (CRITICAL). Observability-only — no gate logic.
        # Fail-open: {} on any error.
        "slippage_validation": _build_slippage_validation(closed),
    }

    # Write payload
    out_dir = ROOT / "audit_trail" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dashboard_payload.json"
    # ── Enrich picks with technical analysis (RSI/MACD/SMA multi-timeframe) ──
    # Must run BEFORE elite scoring so the scorer can apply alignment bonus/penalty
    try:
        _ta_path = ROOT / "copy_trader_intel" / "data" / "technical_analysis.json"
        if _ta_path.exists():
            _ta_data = json.loads(_ta_path.read_text(encoding="utf-8", errors="replace"))
            _ta_by_sym = {p["sym"]: p for p in _ta_data.get("picks", []) if "sym" in p}
            _ta_enriched = 0
            for pick_list in [
                payload["picks"]["active"],
                payload["picks"]["recent_closed"],
            ]:
                for pick in pick_list:
                    sym = (pick.get("symbol") or "").upper()
                    ta_entry = _ta_by_sym.get(sym)
                    if ta_entry:
                        pick["technical_alignment"] = ta_entry.get("aligned", False)
                        pick["technical_verdict"] = ta_entry.get("v_4h", "?")
                        pick["technical_rsi_1h"] = ta_entry.get("rsi_1h")
                        pick["technical_rsi_4h"] = ta_entry.get("rsi_4h")
                        pick["technical_v_1h"] = ta_entry.get("v_1h", "?")
                        pick["technical_v_4h"] = ta_entry.get("v_4h", "?")
                        pick["technical_v_1d"] = ta_entry.get("v_1d", "?")
                        pick["technical_buy_tfs"] = ta_entry.get("buy_tfs", 0)
                        pick["technical_sell_tfs"] = ta_entry.get("sell_tfs", 0)
                        pick["technical_alignment_str"] = ta_entry.get("alignment", "?")
                        
                        # Set STRONG signal flag based on technical alignment
                        buy_tfs = ta_entry.get("buy_tfs", 0)
                        sell_tfs = ta_entry.get("sell_tfs", 0)
                        v_4h = ta_entry.get("v_4h", "?")
                        if pick.get("direction") == "LONG" and buy_tfs >= 3 and v_4h == "STRONG BUY":
                            pick["strong"] = True
                        elif pick.get("direction") == "SHORT" and sell_tfs >= 3 and v_4h == "STRONG SELL":
                            pick["strong"] = True
                        else:
                            pick["strong"] = False
                        
                        _ta_enriched += 1
            print(
                f"  [DASHBOARD] Technical analysis enriched {_ta_enriched} picks ({len(_ta_by_sym)} symbols in TA data)"
            )
        else:
            print(
                "  [DASHBOARD] No technical_analysis.json found -- skipping TA enrichment"
            )
    except Exception as e:
        print(f"  [DASHBOARD] Technical analysis enrichment warning: {e}")

    # ── Score ALL picks with elite scorer (v100) ──
    # Without this, most picks have score=0 because source systems don't compute scores
    try:
        from alpha_engine.elite_scorer import (
            compute_elite_score,
            load_copy_trader_scorebook,
            load_monte_carlo_results,
            load_strategy_performance,
        )

        _mc = load_monte_carlo_results()
        _sp = load_strategy_performance()
        _ct = load_copy_trader_scorebook()
        _scored = 0

        def _attach_strategy_concentration_meta(pick: dict) -> None:
            strat_name = str(pick.get("strategy") or "")
            if not strat_name:
                return
            strat_meta = _sp.get(strat_name)
            if not isinstance(strat_meta, dict):
                return
            top_symbol = str(strat_meta.get("top_symbol") or "").strip()
            if top_symbol:
                pick["strat_top_symbol"] = top_symbol
            top_symbol_pct = _float(strat_meta.get("top_symbol_pnl_pct"))
            if top_symbol_pct > 0:
                pick["strat_top_symbol_pnl_pct"] = round(top_symbol_pct, 1)
            pnl_ex_top = strat_meta.get("pnl_ex_top_symbol")
            if pnl_ex_top not in (None, ""):
                pick["strat_pnl_ex_top_symbol"] = round(_float(pnl_ex_top), 4)
            conc_penalty = _float(strat_meta.get("concentration_penalty"))
            if conc_penalty > 0:
                pick["strat_concentration_penalty"] = round(conc_penalty, 1)
            conc_level = str(strat_meta.get("concentration_level") or "").strip()
            if conc_level:
                pick["strat_concentration_level"] = conc_level
            conc_warning = str(strat_meta.get("concentration_warning") or "").strip()
            if conc_warning:
                pick["strat_concentration_warning"] = conc_warning

        # ===================================================================
        # P0-A FIX (2026-04-04 claude-noncrypto-drilldown):
        # Post-aggregation enrichment + scoring pass that runs on ALL picks
        # regardless of upstream source. Previously aggregator sources
        # (battleground, super_signals, ml_crypto_pred, alpha_engine) bypassed
        # Method C scoring because they arrived with their own `score` value
        # but elite_score=null, and the result fields (ml_composite_score,
        # method_a_score, ml_composite_breakdown, etc.) were never persisted
        # onto the pick. This left 35+ fields null on 95%+ of active picks.
        # See docs/EMPTY_FIELDS_AUDIT_20260405.md.
        # ===================================================================
        _AGGREGATOR_SOURCES = {
            "battleground",
            "super_signals",
            "ml_crypto_pred",
            "ml_crypto_pred_v12",
            "alpha_engine",
            "aggregated_picks",
            "consensus",
            "super_consensus",
        }
        _capped_count = 0
        for pick_list in [
            payload["picks"]["active"],
            payload["picks"]["recent_closed"],
        ]:
            for pick in pick_list:
                _attach_strategy_concentration_meta(pick)
                # Run compute_elite_score on EVERY pick that lacks Method C
                # output. Previously keyed on `elite_score`, which aggregator
                # picks silently filled with None, leaving the scorer's full
                # result (ml_composite_score, method_a_score, breakdowns,
                # grades) absent from the pick row.
                if pick.get("ml_composite_score") is None or not pick.get("elite_score"):
                    result = compute_elite_score(pick, _mc, _sp, _ct)

                    # --- Persist BOTH Method A and Method C outputs so the
                    #     dashboard can show/sort by either and the UI columns
                    #     (_metaWinProb, _metaGrade, method_a_score, etc.)
                    #     have data to render.
                    if "ml_composite_score" in result:
                        pick["ml_composite_score"] = result["ml_composite_score"]
                        pick["ml_composite_breakdown"] = result.get("ml_composite_breakdown")
                        pick["ml_composite_grade"] = result.get("ml_composite_grade")
                    if pick.get("elite_score") is None:
                        pick["elite_score"] = result.get("elite_score")
                    if pick.get("method_a_score") is None:
                        pick["method_a_score"] = result.get("elite_score")
                    if pick.get("method_a_grade") is None:
                        pick["method_a_grade"] = result.get("elite_grade")
                    if pick.get("elite_breakdown") is None:
                        pick["elite_breakdown"] = result.get("elite_breakdown")

                    # Use Method C (ml_composite) when available — it's 2.5x more predictive
                    pick["score"] = (
                        result.get("ml_composite_score") or result["elite_score"]
                    )
                    pick["elite_grade"] = (
                        result.get("ml_composite_grade") or result["elite_grade"]
                    )
                    # Calculate grade from score for dashboard display
                    score = pick["score"] or 0
                    pick["grade"] = (
                        "A"
                        if score >= 60
                        else "B"
                        if score >= 45
                        else "C"
                        if score >= 30
                        else "D"
                        if score >= 15
                        else "F"
                    )
                    # _scoreBreakdown was a byte-identical duplicate of elite_breakdown
                    # adding ~4.4 MB to dashboard_data.json (1267 B/pick * 3500 picks).
                    # Removed 2026-05-03 to cut mobile load times. JS reads now prefer
                    # elite_breakdown directly. The L14016 _fallback marker still ships
                    # for picks that did not get a breakdown computed.
                    for meta_key in (
                        "strategy_top_symbol",
                        "strategy_top_symbol_pnl_pct",
                        "strategy_distinct_symbols",
                        "strategy_concentration_warning",
                        "strategy_concentration_risk",
                        "strategy_concentration_penalty",
                    ):
                        if meta_key in result:
                            pick[meta_key] = result[meta_key]
                    _scored += 1

                # --- Null-ml safety cap: if the scorer couldn't produce a
                #     ml_composite_score (e.g. missing ml_score + confidence)
                #     AND the pick came through an aggregator source that
                #     assigns max scores directly, cap the score at 70. This
                #     prevents the 14-pick score=120 bug where aggregator
                #     sources bypassed the ml_composite penalty in
                #     smart_picks_engine.py (diagnosed by claude-bus-setup
                #     2026-04-04T02:06Z on redis bus).
                if pick.get("ml_composite_score") is None:
                    _src = str(pick.get("source") or pick.get("system") or "").lower()
                    if _src in _AGGREGATOR_SOURCES:
                        try:
                            _cur_score = float(pick.get("score") or 0)
                        except (TypeError, ValueError):
                            _cur_score = 0.0
                        if _cur_score > 70:
                            pick["score"] = 70
                            pick["_score_capped_null_ml"] = True
                            pick["grade"] = "A" if 70 >= 60 else "B"
                            _capped_count += 1

        # --- Historical-stats & backtest joins (fills history_wr,
        #     history_trades, history_avg_pnl, bt_profit_factor, bt_win_rate,
        #     strat_* concentration fields for picks whose upstream source
        #     didn't emit them). Uses strategy_performance.json (_sp), which
        #     is already loaded and rebuilt if stale.
        _history_enriched = 0
        for pick_list in [
            payload["picks"]["active"],
            payload["picks"]["recent_closed"],
        ]:
            for pick in pick_list:
                strat_name = str(pick.get("strategy") or "").strip()
                if not strat_name:
                    continue
                sp_row = _sp.get(strat_name)
                if not isinstance(sp_row, dict):
                    continue
                _wr = sp_row.get("win_rate")
                _trades = sp_row.get("closed_picks")
                _avg = sp_row.get("avg_pnl")
                _pf = sp_row.get("profit_factor")
                did_fill = False
                if pick.get("history_wr") is None and _wr is not None:
                    pick["history_wr"] = round(float(_wr) * 100, 1)
                    did_fill = True
                if pick.get("history_trades") in (None, 0) and _trades:
                    pick["history_trades"] = int(_trades)
                    did_fill = True
                if pick.get("history_avg_pnl") is None and _avg is not None:
                    pick["history_avg_pnl"] = round(float(_avg), 4)
                    did_fill = True
                if pick.get("history_basis") is None and _trades:
                    pick["history_basis"] = "strategy_performance"
                    did_fill = True
                if pick.get("bt_profit_factor") is None and _pf is not None:
                    pick["bt_profit_factor"] = round(float(_pf), 3)
                    did_fill = True
                if pick.get("bt_win_rate") is None and _wr is not None:
                    pick["bt_win_rate"] = round(float(_wr) * 100, 1)
                    did_fill = True
                # strat_decay: forward degradation signal (win_rate vs
                # declared source WR). Only flag if we have both values.
                _fwd_wr = pick.get("forward_wr")
                if pick.get("strat_decay") is None and _fwd_wr is not None and _wr is not None:
                    try:
                        _decay = round(float(_fwd_wr) - float(_wr) * 100, 1)
                        pick["strat_decay"] = _decay
                        did_fill = True
                    except (TypeError, ValueError):
                        pass
                if did_fill:
                    _history_enriched += 1

        print(
            f"  [DASHBOARD] Elite-scored {_scored} picks, "
            f"capped {_capped_count} null-ml aggregator picks, "
            f"history-enriched {_history_enriched} picks"
        )
    except Exception as e:
        print(f"  [DASHBOARD] Elite scorer warning: {e}")

    # ── Fallback scoring for picks still at score=0 after elite scorer ──
    # External sources (contrarian, tsmom, genome, etc.) lack enrichment data,
    # so elite_scorer returns 0. Use confidence + PnL as a simple fallback.
    _fallback_scored = 0
    for pick_list in [payload["picks"]["active"], payload["picks"]["recent_closed"]]:
        for pick in pick_list:
            # BUG FIX (2026-04-04 claude-opus-scoring): use pick.score only.
            # Previously: score = pick.get("score") or pick.get("elite_score") or 0
            # That skipped picks with score=0 but elite_score>0, leaving 87 picks unscored
            # after kill-list penalties zeroed them out. Now any pick with score<1
            # gets a fallback score regardless of elite_score presence.
            score = pick.get("score") or 0
            if score < 1:
                conf = pick.get("confidence") or 0.5
                pnl = pick.get("pnl_pct") or 0
                # Simple fallback: confidence * 60 + PnL bonus (capped)
                pnl_bonus = min(max(pnl * 2, -20), 20)  # -20 to +20 from PnL
                fallback = max(1, min(100, int(conf * 60 + pnl_bonus + 10)))
                pick["score"] = fallback
                pick["elite_grade"] = (
                    "C" if fallback >= 40 else "D" if fallback >= 20 else "F"
                )
                # FIXED: Realistic grading scale based on actual score distribution
                pick["grade"] = (
                    "A"
                    if fallback >= 60
                    else "B"
                    if fallback >= 45
                    else "C"
                    if fallback >= 30
                    else "D"
                    if fallback >= 15
                    else "F"
                )
                pick.setdefault("_scoreBreakdown", {})["_fallback"] = True
                _fallback_scored += 1
    if _fallback_scored:
        print(
            f"  [DASHBOARD] Fallback-scored {_fallback_scored} picks (external sources without enrichment)"
        )

    # ── Ensure all picks have grade calculated from score ──
    # Force recalculate grade for all picks to ensure consistency
    for pick_list in [payload["picks"]["active"], payload["picks"]["recent_closed"]]:
        for pick in pick_list:
            if pick.get("score"):
                score = pick["score"]
                # FIXED: Realistic grading scale based on actual score distribution
                pick["grade"] = (
                    "A"
                    if score >= 60
                    else "B"
                    if score >= 45
                    else "C"
                    if score >= 30
                    else "D"
                    if score >= 15
                    else "F"
                )

    # ── ML enrichment: skyrocket alerts, winner patterns, precursors, momentum ──
    # Applied AFTER elite scoring so ML bonuses stack on top of base scores
    try:
        ml_data = _load_ml_enrichment_data()
        if ml_data:
            all_picks = payload["picks"]["active"] + payload["picks"]["recent_closed"]
            _enrich_picks_with_ml(all_picks, ml_data)
        tv_reg = _load_tv_edge_registry()
        if tv_reg and isinstance(tv_reg, dict):
            all_picks = payload["picks"]["active"] + payload["picks"]["recent_closed"]
            _enrich_picks_with_tv_edge(all_picks, tv_reg)
            payload.setdefault("summary", {})
            payload["summary"]["tv_crypto_edge"] = {
                "generated_at": tv_reg.get("generated_at"),
                "period": tv_reg.get("period"),
                "interval": tv_reg.get("interval"),
                "symbol_count": len(tv_reg.get("by_symbol") or {}),
            }
    except Exception as e:
        log.warning("ML/TV edge enrichment failed (non-fatal): %s", e)

    # Sanitize inf/-inf/nan to None — see _sanitize_for_json docstring.
    # Also patched at the final write (line ~13727), but applying here keeps
    # the intermediate dashboard_payload.json valid for downstream consumers.
    payload = _sanitize_for_json(payload)
    payload_json = json.dumps(payload, indent=2, default=str, allow_nan=False)
    _write_text_file(out_path, payload_json)

    # Reapply family/lesson-based score boosts to the freshly written payload.
    # The HTML build must use the boosted copy so the browser matches the JSON.
    try:
        from alpha_engine.score_booster import run_score_booster

        boost_summary = run_score_booster(out_path)
        if "error" not in boost_summary:
            payload = json.loads(out_path.read_text(encoding="utf-8", errors="replace"))
            payload = _sanitize_for_json(payload)
            payload_json = json.dumps(payload, indent=2, default=str, allow_nan=False)
    except Exception as e:
        log.warning("Score booster failed (non-fatal): %s", e)

    # ── MISSING FIELD BACKFILLER (re-applied — lost in concurrent rebase) ──
    try:
        from audit_trail.missing_field_backfiller import backfill_picks
        payload["picks"]["active"], _bf_stats = backfill_picks(payload["picks"]["active"])
        log.info("  Backfiller: filled %d fields", _bf_stats.get("total_filled", 0))
    except Exception as _bf_e:
        log.warning("Backfiller skipped: %s", _bf_e)

    # Score boosting and downstream penalties can change a pick's final score
    # after the first active-gate pass. Re-apply the active gates here so the
    # published active feed reflects the final scored state, not the pre-boost
    # snapshot.
    published_active_count = len(payload["picks"]["active"])
    if _QUALITY_GATES_AVAILABLE:
        # ── CROSS-ASSET CONFLUENCE (HF-§extra, 2026-04-05) ──
        # Pre-compute cross-asset confluence across active + recent_closed so that
        # _apply_score_penalties() (invoked inside passes_active_gate) can award the
        # +8 bonus when 2+ asset classes agree on direction for the same underlying.
        # Must run BEFORE the re-apply gate loop below.
        try:
            _all_picks_for_confluence = (
                payload["picks"]["active"] + payload["picks"].get("recent_closed", [])
            )
            _confluence_map = _compute_cross_asset_confluence(_all_picks_for_confluence)
            if _confluence_map:
                log.info(
                    "cross_asset_confluence: %d picks flagged across active+recent_closed",
                    len(_confluence_map),
                )
        except Exception as _e:  # noqa: BLE001
            log.warning("cross_asset_confluence computation failed (non-fatal): %s", _e)

        # picks.active_raw is the "Show All Picks" toggle's full pool (2026-04-05
        # user ask). It is the genuine pre-FILTER pool: every active pick loaded
        # from all sources BEFORE the staleness auto-expiry pass and BEFORE
        # passes_active_gate (BANNED trust, stale, blocked symbols, GC=F band,
        # etc). Captured in collect_all_picks() right after source load — see
        # `active_raw_snapshot` there (2026-05-19 bug fix: the old snapshot was
        # taken AFTER auto-expiry, so non-crypto emitter picks — ETF/BOND via
        # NON_CRYPTO_MAX_AGE — were dropped before they could reach the raw
        # view). UI toggle switches between picks.active (gate-filtered) and
        # picks.active_raw (full pool). Each pick tagged _gate_passed=True/False.
        filtered_active, filtered_out = _filter_active_picks_with_gate(
            payload["picks"]["active"]
        )
        payload["picks"]["active"] = filtered_active
        # Sort by score descending so best picks appear first
        payload["picks"]["active"] = sorted(
            payload["picks"]["active"],
            key=lambda x: _float(x.get("score", 0)),
            reverse=True,
        )
        # Store raw pool (pre-expiry, pre-gate — all picks incl. expired + gate
        # rejects) for the Show All Picks toggle.
        payload["picks"]["active_raw"] = sorted(
            list(_active_raw_snapshot),
            key=lambda x: _float(x.get("score", 0)),
            reverse=True,
        )
        # Tag any raw-pool pick the gate loop never saw (auto-expired before the
        # gate ran) so the Show All Picks UI marks it gate-rejected, not unknown.
        for _rp in payload["picks"]["active_raw"]:
            if "_gate_passed" not in _rp:
                _rp["_gate_passed"] = False
        # B18: shadow-promote zero-history strategy picks (default-OFF flag)
        payload["picks"]["active"], _shadow_probation = _apply_shadow_promotion(
            payload["picks"]["active"],
            payload["picks"]["active_raw"],
            closed,
        )
        # 2026-05-05 PR #3: alert-driven shadow demotion of degraded strategies.
        # Default-OFF via SHADOW_ALERT_DEMOTE_ENABLED=1. Reads from already-computed
        # `perf_alerts` (line ~12286) and mutates `_shadow_probation` in place.
        payload["picks"]["active"] = _apply_alert_shadow_demotion(
            payload["picks"]["active"],
            perf_alerts,
            _shadow_probation,
        )
        payload["shadow_probation"] = _shadow_probation

        payload["summary"]["total_active_picks"] = len(payload["picks"]["active"])
        payload["summary"]["total_active_raw_picks"] = len(payload["picks"]["active_raw"])
        # B10 Path B: UEPS KPI sidecar panel (active_raw is now fully assembled).
        payload["picks"]["ueps_kpi"] = _build_ueps_kpi_sidecar(
            payload["picks"].get("active_raw", [])
        )
        quality_stats = dict(payload["summary"].get("quality_stats") or {})
        quality_stats.update(
            {
                "total_active_before_gates": published_active_count,
                "active_after_gates": len(payload["picks"]["active"]),
                "active_filtered_out": filtered_out,
                "active_filtered_out_post_score": 0,
            }
        )
        payload["summary"]["quality_stats"] = quality_stats

        # ── Score safety-net ──
        # Ensure no active pick has score < 10 after all scoring passes.
        # 70% of picks were showing score=0 in the payload because external
        # sources (pm_whale, dna_winner, super_signals, tsmom, wf_audit)
        # don't emit confidence/kelly/strategy_win_rate fields. Force a
        # minimum floor so they rank consistently below enriched picks.
        # v102: Tightened from 20-40 to 15-25 and require confidence >= 0.5.
        # Safety-net picks are NOT high-quality; they are data-quality orphans.
        _safety_net_applied = 0
        for _p in payload["picks"]["active"]:
            _s = _p.get("score") or _p.get("elite_score") or 0
            try:
                _s = float(_s)
            except (TypeError, ValueError):
                _s = 0
            if _s < 10:
                _conf = _p.get("confidence")
                if _conf is None or _conf == 0:
                    _conf = 0.0
                try:
                    _conf = float(_conf)
                except (TypeError, ValueError):
                    _conf = 0.0
                # Only rescue if there is SOME signal (confidence >= 0.5)
                if _conf >= 0.5:
                    _p["score"] = max(15, min(25, int(_conf * 25 + 10)))
                    _p["_score_from_safety_net"] = True
                    _safety_net_applied += 1
                else:
                    # Zero-confidence orphan — drop it rather than mask the issue
                    _p["_score_too_low_rejected"] = True
                    _p["score"] = 0
        # Remove safety-net rejects that fell to 0
        _pre_reject_count = len(payload["picks"]["active"])
        payload["picks"]["active"] = [
            _p for _p in payload["picks"]["active"]
            if not _p.get("_score_too_low_rejected")
        ]
        _rejected_count = _pre_reject_count - len(payload["picks"]["active"])
        if _safety_net_applied > 0 or _rejected_count > 0:
            quality_stats["score_safety_net_applied"] = _safety_net_applied
            quality_stats["score_safety_net_rejected"] = _rejected_count
            payload["summary"]["quality_stats"] = quality_stats
            log.info(
                "  Score safety-net: rescued %d, rejected %d low-confidence orphans",
                _safety_net_applied, _rejected_count,
            )

        # ── Duplicate symbol deduplication ──
        # Keep only the highest-scored pick per (symbol, direction) pair.
        # Multiple LONGs on ETHUSDT from different sources is over-concentration,
        # not diversification. The highest-scored pick wins; others are dropped.
        # This runs BEFORE direction conflict resolution so the winner pool is clean.
        _dedup_key = lambda p: (str(p.get("symbol", "")).upper(), str(p.get("direction", "")).upper())
        _dedup_best = {}
        for _p in payload["picks"]["active"]:
            _key = _dedup_key(_p)
            _score = _float(_p.get("score", 0))
            if _key not in _dedup_best or _score > _dedup_best[_key][0]:
                _dedup_best[_key] = (_score, _p)
        _pre_dedup = len(payload["picks"]["active"])
        payload["picks"]["active"] = [_p for (_s, _p) in _dedup_best.values()]
        _dedup_removed = _pre_dedup - len(payload["picks"]["active"])
        if _dedup_removed > 0:
            quality_stats["duplicate_symbols_removed"] = _dedup_removed
            payload["summary"]["quality_stats"] = quality_stats
            log.info("  Duplicate dedup: removed %d lower-scored duplicate picks", _dedup_removed)

        # ── Direction conflict resolution ──
        # Drops minority-direction picks on symbols with LONG+SHORT conflicts,
        # using trust-weighted voting (system_trust_registry). Prevents
        # self-hedging that wastes capital (9 symbols, ~22 minority picks
        # observed on 2026-04-04).
        # Uses module-level filter_direction_conflicts (imported at top with fallback stub).
        if _CONFLICT_RESOLVER_AVAILABLE:
            try:
                _pre_conflict_count = len(payload["picks"]["active"])
                payload["picks"]["active"] = filter_direction_conflicts(
                    payload["picks"]["active"], strategy="trust_weighted", tag_survivors=True
                )
                _conflict_dropped = _pre_conflict_count - len(payload["picks"]["active"])
                quality_stats["conflict_minority_dropped"] = _conflict_dropped
                payload["summary"]["quality_stats"] = quality_stats
                if _conflict_dropped > 0:
                    log.info(
                        "  Direction conflict filter: dropped %d minority-direction picks (%d -> %d)",
                        _conflict_dropped, _pre_conflict_count, len(payload["picks"]["active"]),
                    )
            except Exception as _e:
                log.warning("Direction conflict filter skipped: %s", _e)

        # ── Forward-degradation penalty ──
        # Apply score penalty to picks from strategies whose realized forward
        # WR has decayed significantly below their reported source WR.
        # Live data (2026-04-04): identified st_fear_greed_contrarian (-21.9pp),
        # claude_gainer_1h (-16.4pp, -162% PnL), enhanced_ml_A_xgboost
        # (-15.6pp, -35% PnL) as kill candidates.
        try:
            from audit_trail.forward_degradation_tracker import (
                compute_degradation_stats, flag_degraded_picks,
                compute_rehabilitation_hints,
            )
            _degr_stats = compute_degradation_stats(resolved_closed)
            flag_degraded_picks(payload["picks"]["active"], _degr_stats, apply_penalty=True)
            # Expose summary to dashboard quality_stats
            _sev = sum(1 for s in _degr_stats["by_strategy"].values() if s.get("severity") == "SEVERE")
            _high = sum(1 for s in _degr_stats["by_strategy"].values() if s.get("severity") == "HIGH")
            _lift = sum(1 for s in _degr_stats["by_strategy"].values() if s.get("severity") == "LIFTING")
            quality_stats["degradation_severe_strategies"] = _sev
            quality_stats["degradation_high_strategies"] = _high
            quality_stats["degradation_lifting_strategies"] = _lift
            # Per-strategy breakdown for inspection (top 10 worst only, bounded size)
            _worst = sorted(
                (
                    {"strategy": k, **{kk: vv for kk, vv in v.items() if kk not in ("trades",)}}
                    for k, v in _degr_stats["by_strategy"].items()
                    if v.get("delta_pp") is not None and v.get("resolved", 0) >= 5
                ),
                key=lambda x: x.get("delta_pp") or 0,
            )[:10]
            # Mutate-Before-Kill: attach rehabilitation hints to severe/high cases
            for _w in _worst:
                if _w.get("severity") in ("SEVERE", "HIGH"):
                    _w["rehabilitation"] = compute_rehabilitation_hints(
                        resolved_closed, _w["strategy"]
                    )
            payload["summary"]["forward_degradation"] = {
                "aggregate": _degr_stats["aggregate"],
                "worst_strategies": _worst,
                "policy_note": "Mutate-Before-Kill: rehabilitation hints attached to SEVERE/HIGH strategies. Salvage paths: symbol_whitelist, direction_restrict, asset_rotation, inverse_candidate, dna_mutation.",
            }
            payload["summary"]["quality_stats"] = quality_stats
            log.info(
                "  Forward degradation: %d SEVERE, %d HIGH, %d LIFTING strategies (with rehab hints)",
                _sev, _high, _lift,
            )
        except Exception as _e:
            log.warning("Forward degradation tracker skipped: %s", _e)

        # ── v100: Non-crypto quality gate (FINAL pass, after score booster) ──
        # Systems with zero non-crypto track record should not score 100 on
        # equity/forex picks. Applied after late score mutations so the final
        # payload reflects the post-penalty state, not the earlier snapshot.
        # NOTE: Use resolved_closed (full list) instead of payload["picks"]["recent_closed"]
        # (capped to 1000). The cap crowded out non-crypto closed picks, causing the gate
        # to see zero history and apply a 0.35x penalty even to systems with real track records.
        _nc_sys_closed = {}
        for _p in resolved_closed:
            _pac = nc_asset_category_for_pick(_p)
            if _pac in _NC_ASSET_CLASSES:
                _psys = _p.get("source_system", "")
                _nc_sys_closed[_psys] = _nc_sys_closed.get(_psys, 0) + 1

        _nc_penalized = 0
        for _p in payload["picks"]["active"]:
            _pac = (_p.get("asset_class") or "").upper()
            if _pac not in _NC_ASSET_CLASSES:
                continue
            _psys = _p.get("source_system", "")
            _nc_closed_ct = _nc_sys_closed.get(_psys, 0)
            _old_score = _p.get("score", 0) or 0
            if _old_score < 1:
                continue
            if _nc_closed_ct == 0:
                _mult = 0.35
            elif _nc_closed_ct < 5:
                _mult = 0.50
            elif _nc_closed_ct < 10:
                _mult = 0.70
            else:
                _mult = 1.0
            if _mult < 1.0:
                _new_score = max(1, int(_old_score * _mult))
                _pnl = _p.get("pnl_pct") or 0
                if _pnl >= 5:
                    _new_score = max(_new_score, 45)
                elif _pnl >= 1:
                    _new_score = max(_new_score, 30)
                _p["score"] = _new_score
                _p["grade"] = (
                    "A" if _new_score >= 60
                    else "B" if _new_score >= 45
                    else "C" if _new_score >= 30
                    else "D" if _new_score >= 15
                    else "F"
                )
                _nc_penalized += 1
        if _nc_penalized:
            log.info(
                "  Non-crypto quality gate: penalized %d picks from unvalidated systems",
                _nc_penalized,
            )

        # ── v101: Clamp ALL scores to [0, 100] — score_booster can push above 100 ──
        _clamped = 0
        for _pick_list in [payload["picks"]["active"], payload["picks"]["recent_closed"]]:
            for _p in _pick_list:
                _sc = _p.get("score", 0) or 0
                if _sc > 100:
                    _p["score"] = 100
                    _clamped += 1
                elif _sc < 0:
                    _p["score"] = 0
                    _clamped += 1
        if _clamped:
            log.info("  Score clamped: %d picks forced to [0, 100]", _clamped)

        # Re-run the active gate after late-stage score mutations. This closes
        # the leak where a pick can pass early, then get downgraded below the
        # visibility floor and still remain in payload["picks"]["active"].
        payload["picks"]["active"], _post_score_filtered_out = _filter_active_picks_with_gate(
            payload["picks"]["active"]
        )
        quality_stats["active_filtered_out_post_score"] = _post_score_filtered_out
        quality_stats["active_after_gates"] = len(payload["picks"]["active"])
        quality_stats["active_filtered_out"] = (
            published_active_count - len(payload["picks"]["active"])
        )
        payload["summary"]["quality_stats"] = quality_stats
        payload["summary"]["total_active_picks"] = len(payload["picks"]["active"])
        if _post_score_filtered_out:
            log.info(
                "  Final active re-gate: dropped %d late-stage picks (%d remain)",
                _post_score_filtered_out,
                len(payload["picks"]["active"]),
            )

        # ── STRONG flag — hedge-fund-level conviction signal ──
        # Every active pick gets a `strong` boolean. Previously only set when
        # technical-analysis enrichment matched narrow criteria (3+ timeframes
        # + v_4h='STRONG BUY/SELL'), leaving 73/189 picks with no flag at all.
        # Expand criteria to combine multiple high-conviction signals so users
        # can quickly filter to trusted picks suitable for TV paper trading.
        _strong_cnt = 0
        for _p in payload["picks"]["active"]:
            # Signal 1: already flagged by technical alignment above
            if _p.get("strong") is True:
                _strong_cnt += 1
                continue
            # Collect conviction signals
            _sigs = 0
            _score = 0.0
            try:
                _score = float(_p.get("score") or _p.get("elite_score") or 0)
            except (TypeError, ValueError):
                _score = 0.0
            # Signal A: high score (top of distribution)
            if _score >= 70:
                _sigs += 1
            # Signal B: PROVEN trust tier
            _tier = str(_p.get("trust_tier") or "").upper()
            if _tier == "PROVEN":
                _sigs += 1
            # Signal C: forward-tested edge (55%+ WR with 10+ trades)
            try:
                _fwd_wr = float(_p.get("strat_fwd_wr") or 0)
                _fwd_n = int(_p.get("strat_fwd_total") or _p.get("sym_track_total") or 0)
                if _fwd_wr >= 55 and _fwd_n >= 10:
                    _sigs += 1
            except (TypeError, ValueError):
                pass
            # Signal D: multi-source agreement (3+ sources same direction)
            try:
                _agree = int(_p.get("agreement_count") or _p.get("agreement_level") or 0)
                if _agree >= 3:
                    _sigs += 1
            except (TypeError, ValueError):
                pass
            # Require 2+ independent signals to be strong
            _p["strong"] = _sigs >= 2
            if _p["strong"]:
                _strong_cnt += 1
        quality_stats["strong_active_count"] = _strong_cnt
        payload["summary"]["quality_stats"] = quality_stats
        log.info("  Strong flag: %d / %d active picks flagged as hedge-fund-level conviction",
                 _strong_cnt, len(payload["picks"]["active"]))

        # ── Tier-routing: surface profitable systems, deprioritize losers ──
        # Assigns display_tier to each active pick so the template can visually
        # group and highlight picks by conviction level.
        #
        # Data thresholds (TESTING_PROTOCOL.MD + 1000-pick closed analysis):
        #   ELITE:   strong=True, trust=PROVEN, score≥70, strat_fwd_wr≥65, n≥10
        #   PREMIUM: trust in PROVEN/RELIABLE, score≥55, strat_fwd_wr≥50, n≥5
        #   STANDARD: score≥40 (passes score floor gate)
        #   WATCH:   unscored (score=0/safety-net) or underperforming strategies
        _tier_counts = {"ELITE": 0, "PREMIUM": 0, "STANDARD": 0, "WATCH": 0}
        for _p in payload["picks"]["active"]:
            _dt_score = 0.0
            try:
                _dt_score = float(_p.get("score") or 0)
            except (TypeError, ValueError):
                _dt_score = 0.0
            _dt_trust = str(_p.get("trust_tier") or "").upper()
            _dt_fwd_wr = 0.0
            _dt_fwd_n = 0
            try:
                _dt_fwd_wr = float(_p.get("strat_fwd_wr") or 0)
                _dt_fwd_n = int(_p.get("strat_fwd_total") or _p.get("sym_track_total") or 0)
            except (TypeError, ValueError):
                pass
            _dt_strong = bool(_p.get("strong"))

            if _dt_strong and _dt_trust == "PROVEN" and _dt_score >= 70 and _dt_fwd_wr >= 65 and _dt_fwd_n >= 10:
                _p["display_tier"] = "ELITE"
            elif _dt_trust in ("PROVEN", "RELIABLE") and _dt_score >= 55 and _dt_fwd_wr >= 50 and _dt_fwd_n >= 5:
                _p["display_tier"] = "PREMIUM"
            elif _dt_score >= 40:
                _p["display_tier"] = "STANDARD"
            else:
                _p["display_tier"] = "WATCH"
            _tier_counts[_p["display_tier"]] = _tier_counts.get(_p["display_tier"], 0) + 1

        quality_stats["display_tier_counts"] = _tier_counts
        payload["summary"]["quality_stats"] = quality_stats
        log.info(
            "  Tier-routing: ELITE=%d PREMIUM=%d STANDARD=%d WATCH=%d",
            _tier_counts["ELITE"], _tier_counts["PREMIUM"],
            _tier_counts["STANDARD"], _tier_counts["WATCH"],
        )

        # ── HF CONVICTION TIERS (re-applied — lost in concurrent rebase) ──
        _hf_tier_counts = {"S": 0, "A": 0, "B": 0}
        try:
            from alpha_engine.conviction_stack import classify_hf_conviction_tier
            for _p in payload["picks"]["active"]:
                _hf_tier, _hf_reasons = classify_hf_conviction_tier(_p)
                _p["hf_conviction_tier"] = _hf_tier
                _p["hf_conviction_reasons"] = _hf_reasons
                _p["conviction_tier"] = _hf_tier or ""
                if _hf_tier:
                    _hf_tier_counts[_hf_tier] = _hf_tier_counts.get(_hf_tier, 0) + 1
            quality_stats["hf_conviction_tiers"] = _hf_tier_counts
            payload["summary"]["quality_stats"] = quality_stats
            payload["extreme_conviction"] = {
                "total": sum(_hf_tier_counts.values()),
                "by_tier": _hf_tier_counts,
                "picks": [p for p in payload["picks"]["active"] if p.get("hf_conviction_tier") in ("S","A","B")][:50],
            }
            log.info("  HF conviction: S=%d A=%d B=%d", _hf_tier_counts.get("S",0), _hf_tier_counts.get("A",0), _hf_tier_counts.get("B",0))
        except Exception as _e:
            log.warning("HF conviction skipped: %s", _e)
            payload["extreme_conviction"] = {"total": 0, "by_tier": {}, "picks": []}

        # Recompute non_crypto_performance with FINAL (post-gate, post-conflict)
        # active picks so the card numbers match what the drill-down modal shows.
        payload["summary"]["non_crypto_performance"] = compute_non_crypto_performance(
            payload["picks"]["active"], payload["picks"]["recent_closed"]
        )
        log.info(
            "  Post-score quality gate: kept %d/%d active picks (%d filtered out)",
            len(payload["picks"]["active"]),
            published_active_count,
            filtered_out,
        )

    # Re-sort after non-crypto gate
    payload["picks"]["active"] = sorted(
        payload["picks"]["active"],
        key=lambda x: _float(x.get("score", 0)),
        reverse=True,
    )

    # ── SMART PICKS: Calculate after all scoring is complete ──
    # Quality gates applied to final scored picks for premium tier
    smart_picks = []
    smart_candidates = []
    try:
        if _QUALITY_GATES_AVAILABLE:
            active_picks = payload["picks"]["active"]
            for pick in active_picks:
                if not passes_smart_gate(pick):
                    continue
                pick_copy = dict(pick)
                pick_copy["smart_score"] = calculate_smart_score(pick_copy)
                smart_candidates.append(pick_copy)
            smart_picks = sorted(
                smart_candidates,
                key=lambda x: (
                    x.get("smart_score", 0),
                    _float(x.get("score", 0)),
                    x.get("timestamp", ""),
                ),
                reverse=True,
            )[:50]  # Top 50 max
    except Exception as e:
        log.warning("Smart picks calculation failed (non-fatal): %s", e)
    payload["picks"]["smart_picks"] = smart_picks
    # ── opt-in pick-surface snapshot — populates at_pick_surface_eval so every
    # /audit surface (Smart Picks / High Conviction / Money Ready) is traceable.
    # Env-gated (PICK_SURFACE_SNAPSHOT_ENABLED, default OFF) — pure sidecar,
    # fail-open, zero production behavior change. See tools/pick_surface_snapshot.py.
    try:
        from tools.pick_surface_snapshot import (
            is_enabled as _pss_enabled,
            snapshot_pick as _pss_snap,
            write_rows as _pss_write,
        )
        if _pss_enabled():
            _smart_ids = {id(_sp) for _sp in smart_picks}
            _pss_rows = [
                _pss_snap(_ap, {"in_active": 1,
                                "in_smart_picks": 1 if id(_ap) in _smart_ids else 0})
                for _ap in payload["picks"]["active"]
            ]
            log.info("  Pick-surface snapshot: wrote %d rows", _pss_write(_pss_rows))
    except Exception as e:  # never break dashboard generation
        log.warning("Pick-surface snapshot failed (non-fatal): %s", e)
    # ── opt-in pick-audit-trail writer — populates at_pick_audit_trail with an
    # ordered STAGE-level decision trace (EMIT -> ACTIVE_GATE -> SMART_GATE ->
    # HC_GATE) per active pick. Env-gated (PICK_AUDIT_TRAIL_ENABLED, default
    # OFF) — pure sidecar, fail-open, zero production behavior change.
    # See tools/pick_audit_trail_writer.py.
    try:
        from tools.pick_audit_trail_writer import (
            is_enabled as _pat_enabled,
            build_trace_rows as _pat_build,
            write_rows as _pat_write,
        )
        if _pat_enabled():
            _pat_smart_ids = {id(_sp) for _sp in smart_picks}
            _pat_rows = []
            for _ap in payload["picks"]["active"]:
                _pat_rows.extend(_pat_build(_ap, {
                    "in_active": 1,
                    "in_smart_picks": 1 if id(_ap) in _pat_smart_ids else 0,
                }))
            log.info("  Pick-audit-trail: wrote %d rows", _pat_write(_pat_rows))
    except Exception as e:  # never break dashboard generation
        log.warning("Pick-audit-trail writer failed (non-fatal): %s", e)
    if _QUALITY_GATES_AVAILABLE:
        quality_stats = dict(payload["summary"].get("quality_stats") or {})
        quality_stats.update(
            {
                "smart_picks_count": len(smart_picks),
                "smart_picks_percentage": round(
                    len(smart_picks) / max(len(payload["picks"]["active"]), 1) * 100, 1
                ),
            }
        )
        payload["summary"]["quality_stats"] = quality_stats
        log.info(
            "  Smart picks: %d (%.1f%% of active)",
            len(smart_picks),
            len(smart_picks) / max(len(payload["picks"]["active"]), 1) * 100,
        )
    _smart_by_asset, _asset_summary = _build_per_asset_quality_summary(
        payload["picks"]["active"],
        smart_candidates,
        payload.get("generated_at", now),
    )
    payload["smart_picks_by_asset"] = _smart_by_asset
    payload["asset_class_summary"] = _asset_summary
    # CamelCase mirrors for frontend/backward compatibility with alternate readers.
    payload["smartPicksByAsset"] = _smart_by_asset
    payload["assetClassSummary"] = _asset_summary

    # Verified-alpha cohort tag (server-side, matches _is_verified_alpha_pick) so QA/tools
    # can filter without treating payload["verified_alpha"] as a picks array.
    for _rp in payload["picks"]["active"]:
        if _is_verified_alpha_pick(_rp):
            _rp["research_cohort"] = "verified_alpha"
            _enrich_va_cohort_fields(_rp)
    for _rp in payload["picks"].get("smart_picks") or []:
        if _is_verified_alpha_pick(_rp):
            _rp["research_cohort"] = "verified_alpha"
            _enrich_va_cohort_fields(_rp)

    _refresh_verified_alpha_system_stats(
        payload.get("systems", []),
        payload["picks"].get("active", []),
    )
    payload["verified_alpha"] = _compute_verified_alpha_summary(
        payload["picks"]["active"],
        payload["picks"].get("smart_picks", []),
        payload["picks"].get("recent_closed", []),
    )
    payload["summary"]["verified_alpha_active_picks"] = payload["verified_alpha"][
        "active_count"
    ]
    payload["summary"]["verified_alpha_smart_picks"] = payload["verified_alpha"][
        "smart_count"
    ]
    payload["summary"]["verified_alpha_audited_wr"] = payload["verified_alpha"][
        "audited"
    ].get("weighted_wr_pct")
    payload["summary"]["verified_alpha_realized_wr"] = payload["verified_alpha"][
        "realized"
    ].get("win_rate")

    # ── Tag duplicate picks across active and smart feeds ──
    # Adds _dup, _dup_icon, _dup_tooltip, _cross_feed_dup, _direction_conflict
    try:
        _tag_duplicate_picks(
            payload["picks"]["active"],
            payload.get("smart_picks_feed", {}).get("picks", []),
        )
        _dup_count = sum(1 for p in payload["picks"]["active"] if p.get("_dup"))
        _conflict_count = sum(
            1 for p in payload["picks"]["active"] if p.get("_direction_conflict")
        )
        _portfolio_uniqueness = _compute_portfolio_uniqueness_stats(
            payload["picks"]["active"]
        )
        payload["summary"]["portfolio_uniqueness"] = _portfolio_uniqueness
        quality_stats = dict(payload["summary"].get("quality_stats") or {})
        quality_stats.update(
            {
                "unique_symbol_count": _portfolio_uniqueness["unique_symbol_count"],
                "unique_symbol_direction_positions": _portfolio_uniqueness[
                    "unique_symbol_direction_positions"
                ],
                "duplicate_symbol_groups": _portfolio_uniqueness[
                    "duplicate_symbol_groups"
                ],
                "duplicate_symbol_picks": _portfolio_uniqueness[
                    "duplicate_symbol_picks"
                ],
                "duplicate_symbol_direction_groups": _portfolio_uniqueness[
                    "duplicate_symbol_direction_groups"
                ],
                "duplicate_symbol_direction_picks": _portfolio_uniqueness[
                    "duplicate_symbol_direction_picks"
                ],
                "conflict_symbol_count": _portfolio_uniqueness["conflict_symbol_count"],
                "conflict_active_pick_count": _portfolio_uniqueness[
                    "conflict_active_pick_count"
                ],
                "cross_feed_duplicate_count": _portfolio_uniqueness[
                    "cross_feed_duplicate_count"
                ],
            }
        )
        payload["summary"]["quality_stats"] = quality_stats
        print(
            f"  [DUPLICATE TAG] {_dup_count} duplicate picks, {_conflict_count} direction conflicts tagged; "
            f"{_portfolio_uniqueness['duplicate_symbol_groups']} duplicate-symbol groups, "
            f"{_portfolio_uniqueness['conflict_symbol_count']} conflict symbols"
        )
    except Exception as e:
        print(f"  [DUPLICATE TAG] Failed (non-fatal): {e}")

    # ── Phase 5: Wilson-LB gated Guide band (PROVEN + confidence 0.8–0.9) ──
    # Replaces the unreproducible "Maximum Conviction Combo" block. See
    # docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md. Hysteresis state
    # persists across dashboard regens via audit_dashboard/data/guide_band_state.json.
    try:
        from audit_trail.guide_band_activation import (
            should_activate_guide_band,
            wilson_lower_bound,
        )

        _gb_state_path = ROOT / "audit_dashboard" / "data" / "guide_band_state.json"
        _gb_last_active = False
        if _gb_state_path.exists():
            try:
                _gb_last_active = bool(
                    json.loads(_gb_state_path.read_text(encoding="utf-8")).get(
                        "guide_band_proven_conf_80_90_active", False
                    )
                )
            except Exception:
                _gb_last_active = False

        _gb_matches = [
            _p for _p in payload["picks"].get("recent_closed", [])
            if str(_p.get("trust_tier") or "").upper() == "PROVEN"
            and isinstance(_p.get("confidence"), (int, float))
            and 0.8 <= float(_p["confidence"]) <= 0.9
            and _p.get("pnl_pct") is not None
        ]
        _gb_n = len(_gb_matches)
        _gb_wins = sum(1 for _p in _gb_matches if float(_p.get("pnl_pct") or 0) > 0)
        _gb_active = should_activate_guide_band(_gb_wins, _gb_n, _gb_last_active)
        _gb_lb = wilson_lower_bound(_gb_wins, _gb_n) if _gb_n > 0 else None

        payload["summary"]["guide_band_proven_conf_80_90"] = {
            "active": _gb_active,
            "n": _gb_n,
            "wins": _gb_wins,
            "wilson_lb": _gb_lb,
        }

        _gb_state_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write (security reviewer): tmp + os.replace avoids leaving a
        # truncated/empty JSON if the process dies mid-write.
        _gb_tmp_path = _gb_state_path.with_suffix(".json.tmp")
        _gb_tmp_path.write_text(
            json.dumps({"guide_band_proven_conf_80_90_active": _gb_active}),
            encoding="utf-8",
        )
        os.replace(_gb_tmp_path, _gb_state_path)
        log.info(
            "  [guide-band] active=%s n=%d wins=%d wilson_lb=%s (was %s)",
            _gb_active, _gb_n, _gb_wins,
            f"{_gb_lb:.3f}" if _gb_lb is not None else "n/a",
            _gb_last_active,
        )
    except Exception as _e:  # noqa: BLE001
        log.warning("[guide-band] failed (non-fatal): %s", _e)

    # ── SPORTS leak guard ──
    # SPORTS/BETTING picks are not trading picks — they should never reach the
    # audit dashboard trading view. Upstream goldmine_unified merges sports
    # betting picks into the same active list as trading picks, so the client
    # has been dropping them at data-load via [sports-filter]. That client-side
    # workaround wastes payload bytes and creates a 1-frame flicker. Drop them
    # here, at the last possible moment before serialization, so no consumer
    # has to deal with them.
    try:
        _sports_classes = {"SPORTS", "BETTING", "SPORT", "BET"}
        _before = len(payload["picks"]["active"])
        payload["picks"]["active"] = [
            _p for _p in payload["picks"]["active"]
            if str(_p.get("asset_class") or "").upper() not in _sports_classes
        ]
        _after = len(payload["picks"]["active"])
        if _before != _after:
            log.info("  [sports-filter] dropped %d SPORTS picks from active feed", _before - _after)
    except Exception as _e:  # noqa: BLE001
        log.warning("sports filter failed (non-fatal): %s", _e)

    # ── ML feature persistence + edge analytics (optional, soft-fail) ──
    # Persists ML/technical fields needed for post-hoc edge validation and
    # optionally refreshes feature-bucket and symbol-strategy edge summaries.
    try:
        if _EDGE_TRACKING_AVAILABLE:
            _db_path = ROOT / "data" / "audit_trail.db"
            if _db_path.exists():
                _persist_enabled = os.environ.get("AUDIT_PERSIST_PICK_FEATURES", "1") != "0"
                _edge_enabled = os.environ.get("AUDIT_RUN_FEATURE_EDGE_ANALYSIS", "1") != "0"
                _rebuild_symbol_stats = os.environ.get("AUDIT_REBUILD_SYMBOL_STRATEGY", "0") == "1"

                _persisted_rows = 0
                with sqlite3.connect(str(_db_path), timeout=15) as _edge_conn:
                    run_sqlite_migration(_edge_conn)

                    if _persist_enabled:
                        _candidates = (
                            list(payload["picks"].get("active", []))
                            + list(payload["picks"].get("recent_closed", []))
                            + list(payload["picks"].get("smart_picks", []))
                        )
                        # 2026-04-27 (perf, audit-C3): single bulk-commit at
                        # end of loop. store_pick_features used to commit per
                        # row; ~3,600 picks × per-row fsync was a meaningful
                        # chunk of the workflow runtime that PR #436 widened.
                        # See docs/CODE_REVIEW_2026_04_27.md.
                        for _pick in _candidates:
                            if isinstance(_pick, dict) and _pick.get("id"):
                                if store_pick_features(_pick, _edge_conn):
                                    _persisted_rows += 1
                        try:
                            _edge_conn.commit()
                        except sqlite3.Error as _commit_exc:
                            log.warning(
                                "  Feature persistence commit failed: %s",
                                _commit_exc,
                            )

                    if _rebuild_symbol_stats:
                        _rebuilt = rebuild_from_closed_picks(_edge_conn)
                        log.info("  Symbol-strategy tracker rebuilt: %d rows", _rebuilt)

                    payload["summary"]["symbol_strategy_edge"] = get_symbol_strategy_summary(
                        _edge_conn
                    )
                    payload["symbol_strategy_top"] = get_edge_picks(
                        _edge_conn,
                        min_win_rate=0.55,
                        min_picks=5,
                        limit=50,
                    )

                    if _edge_enabled:
                        _edge_run = run_full_analysis(_edge_conn)
                        payload["summary"]["feature_edge"] = get_feature_edge_summary(
                            _edge_conn
                        )
                        payload["feature_edge_top"] = get_top_feature_edges(
                            _edge_conn,
                            min_picks=10,
                            top_n=25,
                        )
                        payload["summary"]["feature_edge"].update(
                            {
                                "computed_at": _edge_run.get("computed_at"),
                                "total_buckets": _edge_run.get("total_buckets", 0),
                            }
                        )

                payload.setdefault("summary", {}).setdefault("quality_stats", {})[
                    "feature_rows_persisted"
                ] = _persisted_rows
                log.info(
                    "  Feature persistence: %d rows written to audit_trail.db",
                    _persisted_rows,
                )
    except Exception as _e:  # noqa: BLE001
        log.warning("ML feature persistence/edge analytics skipped: %s", _e)

    # Sanitize inf/-inf/nan to None — JSON spec forbids these literals, and
    # browser JSON.parse() rejects the whole file on the first occurrence
    # (which is what broke /audit on 2026-04-27 with "profit_factor": Infinity).
    payload = _sanitize_for_json(payload)
    payload_json = json.dumps(payload, indent=2, default=str, allow_nan=False)
    _write_text_file(out_path, payload_json)

    # ── Post-write integrity check: read back and validate JSON ──
    try:
        _readback = out_path.read_text(encoding="utf-8")
        json.loads(_readback)
    except json.JSONDecodeError as e:
        log.error(
            "CRITICAL: %s is CORRUPTED after write! line %d col %d: %s "
            "— possible concurrent write or disk issue",
            out_path.name, e.lineno, e.colno, e.msg,
        )
    except OSError as e:
        log.error("CRITICAL: could not read back %s for validation: %s", out_path.name, e)

    size_kb = len(payload_json) / 1024

    if size_kb > PAYLOAD_SIZE_WARN_KB:
        log.warning(
            "Payload size %.1f KB exceeds %d KB threshold!",
            size_kb,
            PAYLOAD_SIZE_WARN_KB,
        )

    log.info("  Active picks:  %d", published_active_count)
    auto_expired_count = len(all_closed_including_expired) - total_closed
    log.info(
        "  Closed picks:  %d real + %d auto-expired excluded (showing %d most recent)",
        total_closed,
        auto_expired_count,
        len(recent_closed),
    )
    log.info("  Systems:       %d", len(systems))
    log.info("  Portfolios:    %d", len(portfolios))
    log.info("  Leaderboard:   %d strategies", len(leaderboard))
    log.info("  BT vs FWD:     %d strategies", len(bt_vs_fwd))
    log.info("  Bundles:       %d", len(bundles))
    log.info("  Predictors:    %d", len(predictions_lb))
    log.info("  Overall WR:    %.1f%%", overall_wr)
    log.info("  Payload size:  %.1f KB", size_kb)
    log.info("  Written to:    %s", out_path)

    return payload


def _build_ueps_kpi_sidecar(active_raw_picks):
    """Build UEPS KPI payload from sidecar active_raw picks (B10 Path B).

    Gate 2 of B10 (n>=10 closed UEPS picks) is architecturally blocked: the
    UEPS B28 sidecar path bypasses outcome_resolver, so picks never accumulate
    in recent_closed. This function builds the KPI panel from live open
    positions instead (unrealized PnL, position metadata, TP/SL/RR).

    Contract keys consumed by template.html::ueps-kpi-panel:
      open_positions, status, message, strategies, tickers, aggregate
    """
    ueps_picks = [
        p for p in (active_raw_picks or [])
        if isinstance(p, dict) and p.get("source_system") == "ueps"
    ]

    if not ueps_picks:
        return {
            "open_positions": 0,
            "status": "empty",
            "message": "No UEPS positions open. UEPS cron runs every 4h.",
            "strategies": [],
            "tickers": [],
            "aggregate": None,
            "picks": [],
        }

    scores = [p["score"] for p in ueps_picks if p.get("score") is not None]
    confidences = [p["confidence"] for p in ueps_picks if p.get("confidence") is not None]
    ages = [p["age_hours"] for p in ueps_picks if p.get("age_hours") is not None]
    pnl_pcts = [p["pnl_pct"] for p in ueps_picks if p.get("pnl_pct") is not None]

    tp_pcts, sl_pcts = [], []
    for p in ueps_picks:
        ep = p.get("entry_price") or 0
        tp = p.get("take_profit") or 0
        sl = p.get("stop_loss") or 0
        if ep and tp and sl:
            tp_pcts.append((tp - ep) / ep * 100)
            sl_pcts.append((sl - ep) / ep * 100)

    avg_tp = sum(tp_pcts) / len(tp_pcts) if tp_pcts else None
    avg_sl = sum(sl_pcts) / len(sl_pcts) if sl_pcts else None
    avg_rr = abs(avg_tp / avg_sl) if (avg_tp and avg_sl) else None

    slim_picks = [
        {
            "symbol": p.get("symbol") or p.get("ticker") or "?",
            "direction": p.get("direction", "LONG"),
            "entry_price": p.get("entry_price"),
            "take_profit": p.get("take_profit"),
            "stop_loss": p.get("stop_loss"),
            "score": p.get("score"),
            "confidence": p.get("confidence"),
            "age_hours": p.get("age_hours"),
            "pnl_pct": p.get("pnl_pct"),
            "concept_family": p.get("concept_family", "long_term_value"),
        }
        for p in ueps_picks
    ]

    return {
        "open_positions": len(ueps_picks),
        "status": "active",
        "message": (
            "Accumulating trade history — closed-pick metrics (WR/PF) available after first UEPS exits."
        ),
        "strategies": sorted(set(p.get("strategy") or "UEPS" for p in ueps_picks)),
        "tickers": [p.get("symbol") or p.get("ticker") or "?" for p in ueps_picks],
        "aggregate": {
            "avg_score": sum(scores) / len(scores) if scores else None,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else None,
            "avg_age_hours": sum(ages) / len(ages) if ages else None,
            "sum_unrealized_pnl_pct": sum(pnl_pcts) if pnl_pcts else 0.0,
            "avg_unrealized_pnl_pct": sum(pnl_pcts) / len(pnl_pcts) if pnl_pcts else None,
            "avg_tp_pct": avg_tp,
            "avg_sl_pct": avg_sl,
            "avg_rr": avg_rr,
            "n_closed": 0,
            "closed_wr": None,
            "closed_pf": None,
        },
        "picks": slim_picks,
    }


def _build_ueps_aggregate_stats(closed_picks):
    """Compute aggregate WR / PF / n per strategy from CLOSED long_term_value
    + swing picks.

    Per docs/PERFORMANCE_CHARTER.md §10 ("n=value" rule), aggregate stats use
    the closed-pick population only — active picks have no realized outcome.
    """
    by_strategy = defaultdict(list)
    for p in closed_picks or []:
        if not isinstance(p, dict):
            continue
        if p.get("pick_type") not in ("long_term_value", "swing"):
            continue
        strategy = p.get("strategy") or "UEPS"
        by_strategy[strategy].append(p)

    out = {}
    for strategy, picks in by_strategy.items():
        n = len(picks)
        wins = 0
        gross_profit = 0.0
        gross_loss = 0.0
        for p in picks:
            pnl = _pick_pnl_pct(p)
            if pnl is None:
                continue
            if pnl > 0:
                wins += 1
                gross_profit += pnl
            else:
                gross_loss += abs(pnl)
        wr = (wins / n) if n > 0 else None
        if gross_loss > 0:
            pf = gross_profit / gross_loss
        elif gross_profit > 0:
            pf = float("inf")
        else:
            pf = None
        pf_safe = pf if (pf is not None and pf != float("inf")) else None
        out[strategy] = {
            "strategy": strategy,
            "wr": wr,
            "pf": pf_safe,
            "n": n,
        }
    return out


def _render_ueps_section_html(active_picks, closed_picks):
    """Render the UEPS dashboard section HTML.

    Replaces the `<!-- __UEPS_SECTION_HTML_PLACEHOLDER__ -->` marker in
    template.html. Filters picks to pick_type ∈ {long_term_value, swing}.
    Closed long_term_value/swing picks reach the renderer's "Closed Holds"
    sub-tab. Aggregate stats use closed picks only per CHARTER §10.

    Returns "" if the renderer module is missing — the template's static
    "Building (n=0/100)" placeholder stays visible in that case.
    """
    if not _UEPS_RENDERER_AVAILABLE or _render_ueps_section is None:
        return ""

    active_picks = active_picks or []
    closed_picks = closed_picks or []

    ueps_active = [
        p for p in active_picks
        if isinstance(p, dict) and p.get("pick_type") in ("long_term_value", "swing")
    ]
    ueps_closed = [
        p for p in closed_picks
        if isinstance(p, dict) and p.get("pick_type") in ("long_term_value", "swing")
    ]

    enriched_closed = []
    for p in ueps_closed:
        q = dict(p)
        q.setdefault("status", "CLOSED")
        enriched_closed.append(q)

    combined = ueps_active + enriched_closed
    aggregate_stats_by_strategy = _build_ueps_aggregate_stats(enriched_closed)

    try:
        return _render_ueps_section(
            picks=combined,
            aggregate_stats_by_strategy=aggregate_stats_by_strategy,
        )
    except Exception as e:  # pragma: no cover - defensive
        log.error("UEPS section render failed: %s", e)
        return ""


def _load_ueps_picks_from_disk():
    """Load (active, closed) UEPS pick lists from
    alpha_engine/data/{active,closed}_picks.json. Used when build_html() is
    called without explicit picks. Defensive: missing files return [], not
    an error."""
    active_path = ROOT / "alpha_engine" / "data" / "active_picks.json"
    closed_path = ROOT / "alpha_engine" / "data" / "closed_picks.json"
    active = _load_json_resilient(active_path) if active_path.exists() else []
    closed = _load_json_resilient(closed_path) if closed_path.exists() else []
    active = active or []
    closed = closed or []
    if not isinstance(active, list):
        active = []
    if not isinstance(closed, list):
        closed = []
    return active, closed


def build_html(payload, ueps_active_picks=None, ueps_closed_picks=None):
    """Inject payload JSON into the HTML dashboard template.

    Reads audit_dashboard/template.html (the clean template with placeholder),
    writes audit_dashboard/index.html (the built version with data).
    Also writes audit_dashboard/data/dashboard_data.json (external data file)
    to prevent merge conflicts — the template can load from either source.

    UEPS section: replaces the `<!-- __UEPS_SECTION_HTML_PLACEHOLDER__ -->`
    marker in template.html with audit_dashboard.ueps_section_renderer
    output. If `ueps_active_picks`/`ueps_closed_picks` are not provided,
    they're loaded from alpha_engine/data/{active,closed}_picks.json.
    """
    template_path = ROOT / "audit_dashboard" / "template.html"
    output_path = ROOT / "audit_dashboard" / "index.html"
    external_data_path = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"

    # ── Write external JSON data file (always, even if template is missing) ──
    # Sanitize inf/-inf/nan -> None first; browser JSON.parse rejects them and
    # bricked the live dashboard 2026-04-27 (see _sanitize_for_json docstring).
    payload = _sanitize_for_json(payload)
    external_data_path.parent.mkdir(parents=True, exist_ok=True)
    external_data_path.write_text(
        json.dumps(payload, default=str, allow_nan=False), encoding="utf-8"
    )
    ext_kb = external_data_path.stat().st_size / 1024
    log.info("  External data: %s (%.1f KB)", external_data_path, ext_kb)

    # M-004: Write per-system concentration summary for quality_gates auto-quarantine.
    # Computes {asset_class: {system_name: {pf, vol_pct, resolved_n}}} so passes_active_gate
    # can check if a source system has >40% concentration AND PF<1 without loading the full
    # dashboard_data.json. Fail-open: any exception here must not prevent dashboard generation.
    try:
        _systems_list = payload.get("systems", [])
        _class_totals: dict = {}
        for _sys in _systems_list:
            for _ac in (_sys.get("asset_classes") or []):
                _class_totals[_ac] = _class_totals.get(_ac, 0) + (_sys.get("resolved_picks") or 0)
        _conc_out: dict = {}
        for _sys in _systems_list:
            _sys_name = _sys.get("name", "")
            _pf = _sys.get("profit_factor")
            _n = _sys.get("resolved_picks") or 0
            for _ac in (_sys.get("asset_classes") or []):
                _total = _class_totals.get(_ac, 0)
                _vol_pct = round(_n / _total * 100, 2) if _total > 0 else 0.0
                if _ac not in _conc_out:
                    _conc_out[_ac] = {}
                _conc_out[_ac][_sys_name] = {
                    "pf": _pf,
                    "vol_pct": _vol_pct,
                    "resolved_n": _n,
                }
        _conc_path = ROOT / "audit_trail" / "data" / "system_concentration.json"
        _conc_path.parent.mkdir(parents=True, exist_ok=True)
        _conc_path.write_text(
            json.dumps({"generated_at": payload.get("generated_at", ""), "by_class": _conc_out},
                       indent=2, default=str),
            encoding="utf-8",
        )
        log.info("  M-004: system_concentration.json written (%d classes)", len(_conc_out))
    except Exception as _m004_err:
        log.warning("M-004: failed to write system_concentration.json: %s", _m004_err)

    if not template_path.exists():
        log.warning("audit_dashboard/template.html not found, skipping HTML build")
        return

    html = template_path.read_text(encoding="utf-8", errors="replace")
    payload_json = json.dumps(payload, default=str, allow_nan=False)
    payload_mb = len(payload_json) / 1024 / 1024
    marker = "// __DASHBOARD_DATA_PLACEHOLDER__"

    # v101: Skip embedding if payload > 8MB — mobile browsers crash on 14MB+ HTML.
    # The external dashboard_data.json fetch (loadExternalDashboardDataIfFresher) handles loading.
    if payload_mb > 8:
        log.info("  Payload %.1fMB > 8MB threshold — skipping HTML embed for mobile compat", payload_mb)
        replacement = "// Data too large to embed (%dMB). Loading from data/dashboard_data.json instead." % int(payload_mb)
    else:
        replacement = f"window.DASHBOARD_DATA = {payload_json};"

    if marker in html:
        html = html.replace(marker, replacement)
    else:
        # Fallback: inject as a new script tag before </body>
        inject = f"<script>\n{replacement}\n</script>\n</body>"
        if "</body>" in html:
            html = html.replace("</body>", inject)
            log.warning(
                "Placeholder not found in template, injected data before </body>"
            )
        else:
            log.error("Could not inject data into HTML — no </body> tag found")
            return

    # ── UEPS section render (server-side) ──
    # Replace the `<!-- __UEPS_SECTION_HTML_PLACEHOLDER__ -->` marker with
    # rendered HTML from audit_dashboard.ueps_section_renderer. With no
    # qualifying picks (or renderer missing), the marker is left untouched
    # and the template's static "Building (n=0/100)" placeholder remains
    # visible — never blank/broken HTML.
    ueps_marker = "<!-- __UEPS_SECTION_HTML_PLACEHOLDER__ -->"
    if ueps_marker in html:
        if ueps_active_picks is None and ueps_closed_picks is None:
            ueps_active_picks, ueps_closed_picks = _load_ueps_picks_from_disk()
        ueps_html = _render_ueps_section_html(ueps_active_picks, ueps_closed_picks)
        if ueps_html:
            html = html.replace(ueps_marker, ueps_html)
            log.info(
                "  UEPS section rendered: %d active + %d closed picks",
                len(ueps_active_picks or []),
                len(ueps_closed_picks or []),
            )
        else:
            log.info(
                "  UEPS section: 0 qualifying picks; static 'Building (n=0/100)' placeholder kept"
            )

    output_path.write_text(html, encoding="utf-8")
    size_kb = output_path.stat().st_size / 1024
    log.info("  HTML built: %s (%.1f KB)", output_path, size_kb)


if __name__ == "__main__":
    if not _acquire_lock():
        log.error("Could not acquire lock — exiting")
        sys.exit(1)
    try:
        payload = generate()
        build_html(payload)
        
        # Run sync_strategy_performance (Option B from PR #289)
        try:
            import subprocess
            sync_script = ROOT / "tools" / "sync_strategy_performance.py"
            if sync_script.exists():
                log.info("  Syncing strategy performance from dashboard payload...")
                subprocess.run([sys.executable, str(sync_script)], check=False)
        except Exception as e:
            log.error("Failed to run sync_strategy_performance: %s", e)
    finally:
        _release_lock()
