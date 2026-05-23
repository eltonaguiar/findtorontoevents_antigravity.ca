#!/usr/bin/env python3
"""
build_pf_registry.py — Canonical Profit-Factor Registry builder (Action Item A8)

PROBLEM
-------
Every surface (`dashboard_generator`, `score_booster`, sizing logic, ad-hoc
verification scripts) recomputes profit factor (PF) its own way. The same
asset class therefore shows wildly different numbers — e.g. the COMMODITY
"PF 2.57 vs 21.33" dispute. The root cause is twofold:

  1. COT re-emissions: `multi_asset_cot` re-emits the same signal up to 9x
     across multiple cycles. Naive aggregators count each emission as an
     independent trade, asymmetrically inflating PF (winners re-emitted more
     than losers). See `reports/commodity_pf_verification_2026-05-17.md`.
  2. Resolver spot-flicker: the non-crypto outcome resolver closes picks at
     yfinance spot on every run with a tiny WIN threshold, producing
     near-zero-pnl artifact rows (see MEMORY: `feedback_noncrypto_resolver_*`).

This script builds ONE source-of-truth registry that:
  - ingests every available closed-pick ledger,
  - DEDUPLICATES re-emissions on (strategy, symbol, direction, entry-date,
    ~entry-price),
  - FLAGS resolver spot-flicker artifacts (tiny |pnl_pct| on non-crypto),
  - recomputes PF/WR at three granularities, and
  - writes a versioned JSON others can simply read instead of recomputing.

It is READ-ONLY w.r.t. all inputs and idempotent. It does NOT run any
dashboard generator.

USAGE
-----
    python tools/build_pf_registry.py

Writes `audit_dashboard/data/pf_registry.json`.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

SCHEMA_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Paths (resolved relative to repo root so the script is location-independent)
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Fallback list — used only if JSON_PICK_SOURCES cannot be imported from the
# dashboard generator. The canonical list is JSON_PICK_SOURCES itself, so the
# registry ingests EXACTLY the closed-pick ledgers the /audit verdict reads.
_FALLBACK_SOURCE_FILES = [
    "alpha_engine/data/closed_picks.json",
    "alpha_engine/data/closed_picks_fast.json",
    "battleground/data/closed_picks.json",
]


def _resolve_source_files() -> tuple[list, bool]:
    """Return (closed_pick_paths, canonical). When canonical is True the list
    came from dashboard_generator.JSON_PICK_SOURCES — i.e. the registry input
    is provably identical to the /audit verdict input. When False the import
    failed and the static fallback (3 files) is used, so registry numbers are
    NOT reconcilable with the dashboard and a warning is emitted."""
    try:
        sys.path.insert(0, REPO_ROOT)
        from audit_trail.dashboard_generator import (  # type: ignore
            JSON_PICK_SOURCES,
        )
        paths, seen = [], set()
        for entry in JSON_PICK_SOURCES:
            # entries are (system_name, active_path, closed_path)
            closed = entry[2] if len(entry) >= 3 else None
            if closed and closed not in seen:
                seen.add(closed)
                paths.append(closed)
        if paths:
            return paths, True
    except Exception as exc:  # noqa: BLE001 — fail-open by design
        print("WARN: JSON_PICK_SOURCES unavailable (%s); using 3-file fallback "
              "— registry will NOT reconcile to /audit" % exc, file=sys.stderr)
    return list(_FALLBACK_SOURCE_FILES), False


SOURCE_FILES, SOURCE_FILES_CANONICAL = _resolve_source_files()

OUTPUT_FILE = "audit_dashboard/data/pf_registry.json"

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
# A non-crypto close whose absolute pnl_pct is below this is treated as a
# resolver spot-flicker artifact (the outcome resolver marking a pick closed
# at near-identical spot). Expressed as a fraction: 2 bp = 0.0002.
SPOT_FLICKER_THRESHOLD = 0.0002

# Futures/non-crypto picks whose pnl_pct exceeds this threshold are treated as
# dollar-scale artifacts (raw P&L in dollars stored in the pnl_pct field instead
# of a fraction). A legitimate pick rarely exceeds 100% (fraction = 1.0).
# futures_connors_rsi2 shows gross_profit=19M from 136 picks — each pick ≈ 140,000%,
# clearly dollar-scale YM=F/ES=F/NQ=F point values stored verbatim.
DOLLAR_SCALE_ARTIFACT_THRESHOLD = 1.0  # fraction; >100% pnl on a single pick = artifact

# Entry prices are rounded to this many decimals when forming the dedup key,
# so two emissions of the same signal with float jitter still collapse.
ENTRY_PRICE_ROUND = 2

# pnl_pct in the ledgers is stored as a fraction (e.g. -0.0327 == -3.27%).
# A win is pnl_pct > 0.

# Statuses that represent a genuinely closed/resolved pick.
CLOSED_STATUSES = {"CLOSED", "WON", "LOST", "LOSS", "EXPIRED", "WIN"}


# ---------------------------------------------------------------------------
# Verdict policy — strategies/sources excluded from the *policy-clean* view.
# These mirror the filters the /audit asset_class_health verdict applies
# (PERMANENTLY_KILLED_STRATEGIES + BLOCKED_SOURCE_SYSTEMS). Without this the
# registry's raw/dedup numbers are NOT comparable to the dashboard verdict —
# registry CRYPTO PF includes ~5.9k quan_engine rows the dashboard drops.
# Loaded best-effort; an import failure just yields an empty policy set
# (policy-clean view then equals the dedup view).
#
# Direction-aware update (2026-05-18, M-110): also loads BLOCKED_DIRECTION_TRIPLES
# and BLOCKED_ASSET_STRATEGY_PAIRS so that only the blocked direction is excluded,
# not the entire strategy. Previously a LONG-blocked strategy's SHORT picks were
# excluded from the clean view, hiding real edge (e.g. FOREX clean PF 0.174 → 2.2).
# ---------------------------------------------------------------------------
def _load_policy_excluded() -> tuple:
    """Returns (flat_excluded: set, direction_triples: set, asset_pairs: set)."""
    excluded: set = set()
    direction_triples: set = set()  # (asset_class_upper, strategy_lower, direction_upper)
    asset_pairs: set = set()       # (asset_class_upper, strategy_lower)
    try:
        sys.path.insert(0, REPO_ROOT)
        from audit_trail.quality_gates import (  # type: ignore
            PERMANENTLY_KILLED_STRATEGIES,
            BLOCKED_SOURCE_SYSTEMS,
            PF_REGISTRY_POLICY_EXCLUDED,
        )
        for s in PERMANENTLY_KILLED_STRATEGIES:
            excluded.add(str(s).lower())
        for s in BLOCKED_SOURCE_SYSTEMS:
            excluded.add(str(s).lower())
        for s in PF_REGISTRY_POLICY_EXCLUDED:
            excluded.add(str(s).lower())
    except ImportError:
        # PF_REGISTRY_POLICY_EXCLUDED may not exist in older quality_gates versions
        try:
            from audit_trail.quality_gates import (  # type: ignore
                PERMANENTLY_KILLED_STRATEGIES,
                BLOCKED_SOURCE_SYSTEMS,
            )
            for s in PERMANENTLY_KILLED_STRATEGIES:
                excluded.add(str(s).lower())
            for s in BLOCKED_SOURCE_SYSTEMS:
                excluded.add(str(s).lower())
        except Exception as exc:  # noqa: BLE001
            print("WARN: policy set unavailable (%s); policy-clean == dedup view"
                  % exc, file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — fail-open by design
        print("WARN: policy set unavailable (%s); policy-clean == dedup view"
              % exc, file=sys.stderr)

    # Direction-aware blocks — loaded separately so import errors don't
    # fall back to the old direction-blind behavior.
    try:
        sys.path.insert(0, REPO_ROOT)
        from audit_trail.quality_gates import (  # type: ignore
            BLOCKED_DIRECTION_TRIPLES,
            BLOCKED_ASSET_STRATEGY_PAIRS,
        )
        for ac, strat, direction in BLOCKED_DIRECTION_TRIPLES:
            direction_triples.add((str(ac).upper(), str(strat).lower(), str(direction).upper()))
        for ac, strat in BLOCKED_ASSET_STRATEGY_PAIRS:
            asset_pairs.add((str(ac).upper(), str(strat).lower()))
    except Exception as exc:  # noqa: BLE001 — fail-open; direction blocks missing degrades to flat exclusion
        print("WARN: direction-aware blocks unavailable (%s); direction filter skipped"
              % exc, file=sys.stderr)

    return excluded, direction_triples, asset_pairs


_POLICY_EXCLUDED, _DIRECTION_TRIPLES, _ASSET_PAIRS = _load_policy_excluded()
# Keep backward-compat name used in reporting
POLICY_EXCLUDED = _POLICY_EXCLUDED


def _is_policy_excluded(row) -> bool:
    """True if the row should be dropped from the policy-clean view.

    Three-layer check (direction-aware, M-110 2026-05-18):
    1. Flat: strategy or source_system in PERMANENTLY_KILLED / BLOCKED_SOURCE_SYSTEMS /
       PF_REGISTRY_POLICY_EXCLUDED.
    2. Direction triple: (asset_class, strategy, direction) in BLOCKED_DIRECTION_TRIPLES.
       Only the blocked direction is excluded; the other direction remains.
    3. Asset-strategy pair: (asset_class, strategy) in BLOCKED_ASSET_STRATEGY_PAIRS.
       All directions of that strategy within that asset class are excluded.
    """
    strat = str(row.get("strategy") or "").lower()
    src = str(row.get("source_system") or "").lower()

    # Layer 1 — flat exclusion (strategy or source system unconditionally blocked)
    if _POLICY_EXCLUDED and (strat in _POLICY_EXCLUDED or src in _POLICY_EXCLUDED):
        return True

    # Use _asset_class() so records missing asset_class field (e.g. mercury2 closed_picks.json)
    # still match BLOCKED_ASSET_STRATEGY_PAIRS via USDT-suffix inference.
    ac = _asset_class(row)
    direction = str(row.get("direction") or "").upper()

    # Layer 2 — direction triple (exclude only the blocked direction)
    if _DIRECTION_TRIPLES and ac and strat and direction:
        if (ac, strat, direction) in _DIRECTION_TRIPLES:
            return True

    # Layer 3 — asset-strategy pair (all directions of this strategy in this class)
    if _ASSET_PAIRS and ac and strat:
        if (ac, strat) in _ASSET_PAIRS:
            return True

    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_float(val):
    try:
        if val is None or val == "":
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def _norm(val, default="UNKNOWN"):
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def _norm_symbol(val, default="UNKNOWN"):
    """Symbol normalizer for grouping/dedup keys. Collapses the yfinance
    suffix forms so the SAME instrument is one cohort, not two — fixes the
    FOREX `EURUSD` vs `EURUSD=X` double-count (2026-05-18, RESOLUTION_PIPELINE
    _FIX_PLAN). `=X` (forex) and `=F` (futures) are stripped; canonical key is
    the bare upper-case root.
    """
    s = _norm(val, default)
    if s == default:
        return s
    s = s.upper()
    if s.endswith("=X") or s.endswith("=F"):
        s = s[:-2]
    return s or default


def _trade_date(row) -> str:
    """Best-effort trade (entry) date as YYYY-MM-DD.

    entry_date is only ~27% populated in the main ledger, so fall back through
    timestamp -> closed_at -> resolved_at -> exit_date.
    """
    for field in ("entry_date", "entry_time", "timestamp", "created_at",
                   "closed_at", "resolved_at", "exit_date", "exit_time"):
        v = row.get(field)
        if v:
            s = str(v)
            # ISO strings: take the date portion
            return s[:10]
    return "UNKNOWN"


def _asset_class(row) -> str:
    ac = _norm(row.get("asset_class"), default="")
    if ac:
        # normalize a couple of known aliases
        up = ac.upper()
        if up == "STOCKS":
            return "EQUITY"
        return up
    # Fast/battleground ledgers may lack asset_class — infer crudely.
    sym = str(row.get("symbol", "")).upper()
    if sym.endswith("USDT") or sym.endswith("USD") and len(sym) <= 8:
        return "CRYPTO"
    return "UNKNOWN"


def _strategy(row) -> str:
    """Strategy identity for keying. Prefer source_system (the emission
    grouping that the COT dedup bug lives in), fall back to strategy."""
    return _norm(row.get("source_system") or row.get("strategy"))


def _is_win(pnl_pct) -> bool:
    return pnl_pct is not None and pnl_pct > 0


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load_rows():
    """Returns (rows, source_meta). rows is a flat list of dicts; source_meta
    records which files were found and how many rows each contributed."""
    rows = []
    source_meta = []
    for rel in SOURCE_FILES:
        path = os.path.join(REPO_ROOT, rel)
        if not os.path.isfile(path):
            source_meta.append({"file": rel, "present": False, "rows": 0})
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            source_meta.append({"file": rel, "present": True, "rows": 0,
                                "error": str(exc)})
            continue
        if isinstance(data, dict):
            data = list(data.values())
        if not isinstance(data, list):
            source_meta.append({"file": rel, "present": True, "rows": 0,
                                "error": "unexpected top-level type"})
            continue
        count = 0
        for r in data:
            if not isinstance(r, dict):
                continue
            r = dict(r)
            r["_origin_file"] = rel
            rows.append(r)
            count += 1
        source_meta.append({"file": rel, "present": True, "rows": count})
    return rows, source_meta


# ---------------------------------------------------------------------------
# Sanitize + dedup
# ---------------------------------------------------------------------------
def classify_rows(rows):
    """Splits rows into kept / dropped buckets.

    Returns dict with:
      kept            -> list of unique, sanitized trade rows
      dropped_dup     -> count of re-emission duplicates removed
      dropped_flicker -> count of resolver spot-flicker artifacts removed
      dropped_open    -> count of rows that are not actually closed
      raw_count       -> total input rows
    """
    raw_count = len(rows)

    # 1. keep only genuinely closed rows with a usable pnl_pct
    closed = []
    dropped_open = 0
    for r in rows:
        status = str(r.get("status", "")).upper()
        pnl = _to_float(r.get("pnl_pct"))
        if status and status not in CLOSED_STATUSES:
            dropped_open += 1
            continue
        if pnl is None:
            dropped_open += 1
            continue
        r["_pnl_pct"] = pnl
        closed.append(r)

    # 2. flag resolver spot-flicker artifacts (non-crypto, tiny |pnl|)
    #    and dollar-scale artifacts (pnl stored in dollars instead of fraction)
    sane = []
    dropped_flicker = 0
    for r in closed:
        ac = _asset_class(r)
        pnl = r["_pnl_pct"]
        if ac != "CRYPTO" and abs(pnl) < SPOT_FLICKER_THRESHOLD:
            dropped_flicker += 1
            continue
        if abs(pnl) > DOLLAR_SCALE_ARTIFACT_THRESHOLD:
            # pnl_pct > 100% — dollar-scale artifact (futures point values stored verbatim)
            dropped_flicker += 1
            continue
        sane.append(r)

    # 3. dedup re-emissions
    #    key = (strategy, symbol, direction, trade_date, entry_price~)
    seen = {}
    kept = []
    dropped_dup = 0
    for r in sane:
        ep = _to_float(r.get("entry_price"))
        ep_key = round(ep, ENTRY_PRICE_ROUND) if ep is not None else None
        key = (
            _strategy(r),
            _norm_symbol(r.get("symbol")),
            _norm(r.get("direction")),
            _trade_date(r),
            ep_key,
        )
        if key in seen:
            dropped_dup += 1
            continue
        seen[key] = True
        kept.append(r)

    return {
        "kept": kept,
        "dropped_dup": dropped_dup,
        "dropped_flicker": dropped_flicker,
        "dropped_open": dropped_open,
        "raw_count": raw_count,
        "closed_count": len(closed),
        "sane_count": len(sane),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def _blank_stat():
    return {
        "n": 0,
        "wins": 0,
        "losses": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,  # stored as a positive magnitude
        "total_pnl_pct": 0.0,
    }


def _accumulate(stat, pnl):
    stat["n"] += 1
    stat["total_pnl_pct"] += pnl
    if pnl > 0:
        stat["wins"] += 1
        stat["gross_profit"] += pnl
    elif pnl < 0:
        stat["losses"] += 1
        stat["gross_loss"] += abs(pnl)
    # pnl == 0 contributes to n only (neither win nor loss)


def _finalize(stat):
    n = stat["n"]
    gp = stat["gross_profit"]
    gl = stat["gross_loss"]
    wr = (stat["wins"] / n * 100.0) if n else None
    if gl > 0:
        pf = gp / gl
    elif gp > 0:
        pf = None  # infinite PF — no losses; flagged separately
    else:
        pf = None
    out = dict(stat)
    out["gross_profit"] = round(gp, 6)
    out["gross_loss"] = round(gl, 6)
    out["total_pnl_pct"] = round(stat["total_pnl_pct"], 6)
    out["win_rate_pct"] = round(wr, 4) if wr is not None else None
    out["profit_factor"] = round(pf, 6) if pf is not None else None
    out["pf_undefined_reason"] = (
        None if pf is not None else
        ("no_losses" if gp > 0 else "no_trades")
    )
    return out


def _net_pnl(gross: float, asset_class: str) -> float:
    """gross pnl_pct minus per-class round-trip slippage (M-069 fraction-unit
    `deduct_slippage`). Fail-open to gross if charter_slippage is unavailable."""
    try:
        from alpha_engine.charter_slippage import deduct_slippage
        return deduct_slippage(gross, asset_class)
    except Exception:
        return gross


def _rolling_mdd(returns):
    """Compute max drawdown of the cumulative equity curve from a return series.

    Algorithm copied verbatim from
    alpha_engine.money_ready_verdict._rolling_mdd so the two stay identical
    (swarm Q2 verdict: a shared tools/mdd_calculator.py refactor is deferred).
    Absolute peak-to-trough drawdown on a cumulative curve starting at 1.0.
    Returns a non-negative float: 0.0 = no drawdown, 0.20 = 20% peak-to-trough.
    """
    if not returns:
        return 0.0
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= (1.0 + r)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def aggregate(kept_rows, net: bool = False):
    """Builds the granularities of PF/WR stats from deduped rows.

    net=True deducts per-class round-trip slippage from each row's pnl before
    aggregation — the real-money (net) view, comparable to the /audit verdict.

    Returns a 5-tuple: rows_csd, rows_css, rows_cs, rows_c, class_mdd. The
    final element `class_mdd` maps asset_class -> max_drawdown_pct (fraction,
    0.20 = 20%) computed on the trade-date-ordered per-pick equity curve built
    from the SAME (net-or-gross) pnl series that feeds the rows_c PF/WR.
    """
    by_class_strategy_date = defaultdict(_blank_stat)
    by_class_strategy_symbol = defaultdict(_blank_stat)
    by_class_strategy = defaultdict(_blank_stat)
    by_class = defaultdict(_blank_stat)
    # (trade_date, pnl) pairs per class — sorted by trade_date for the equity
    # curve so the MDD is self-consistent with the PF/WR built above.
    class_series = defaultdict(list)

    for r in kept_rows:
        ac = _asset_class(r)
        strat = _strategy(r)
        sym = _norm_symbol(r.get("symbol"))
        td = _trade_date(r)
        pnl = _net_pnl(r["_pnl_pct"], ac) if net else r["_pnl_pct"]

        _accumulate(by_class_strategy_date[(ac, strat, td)], pnl)
        _accumulate(by_class_strategy_symbol[(ac, strat, sym)], pnl)
        _accumulate(by_class_strategy[(ac, strat)], pnl)
        _accumulate(by_class[ac], pnl)
        class_series[ac].append((td, pnl))

    rows_csd = [
        {"asset_class": ac, "strategy": strat, "trade_date": td,
         **_finalize(stat)}
        for (ac, strat, td), stat in sorted(by_class_strategy_date.items())
    ]
    rows_css = [
        {"asset_class": ac, "strategy": strat, "symbol": sym,
         **_finalize(stat)}
        for (ac, strat, sym), stat in sorted(by_class_strategy_symbol.items())
    ]
    rows_cs = [
        {"asset_class": ac, "strategy": strat, **_finalize(stat)}
        for (ac, strat), stat in sorted(by_class_strategy.items())
    ]
    rows_c = [
        {"asset_class": ac, **_finalize(stat)}
        for ac, stat in sorted(by_class.items())
    ]
    class_mdd = {}
    for ac, pairs in class_series.items():
        # sort by trade_date (str-sortable ISO dates); None/"" sort first.
        ordered = [pnl for _td, pnl in sorted(pairs, key=lambda p: (p[0] or ""))]
        class_mdd[ac] = round(_rolling_mdd(ordered), 6) if ordered else None
    return rows_csd, rows_css, rows_cs, rows_c, class_mdd


def raw_by_class(rows):
    """PF per asset class WITHOUT dedup/flicker filtering — the 'before'
    picture, so the dedup delta is auditable in the registry itself."""
    by_class = defaultdict(_blank_stat)
    for r in rows:
        status = str(r.get("status", "")).upper()
        if status and status not in CLOSED_STATUSES:
            continue
        pnl = _to_float(r.get("pnl_pct"))
        if pnl is None:
            continue
        _accumulate(by_class[_asset_class(r)], pnl)
    return [
        {"asset_class": ac, **_finalize(stat)}
        for ac, stat in sorted(by_class.items())
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    rows, source_meta = load_rows()
    if not rows:
        print("ERROR: no rows loaded from any source file.", file=sys.stderr)
        return 1

    cls = classify_rows(rows)
    kept = cls["kept"]

    raw_class = raw_by_class(rows)
    csd, css, cs, c, _ = aggregate(kept)

    # Policy-clean view: deduped rows MINUS verdict-excluded strategies/sources.
    # This is the view that IS comparable to /audit asset_class_health.
    kept_policy = [r for r in kept if not _is_policy_excluded(r)]
    _, _, _, c_policy, _ = aggregate(kept_policy)
    # Net (real-money) policy-clean view: same rows, per-class round-trip
    # slippage deducted (M-069). This is the canonical view a money-grade
    # verdict reads — gross PF overstates edge that does not survive costs.
    # class_mdd_net: per-class max drawdown on the net per-pick equity curve —
    # the third tier-certification leg alongside PF/WR (swarm Q2 verdict).
    _, _, cs_policy_net, c_policy_net, class_mdd_net = aggregate(
        kept_policy, net=True)
    # Attach max_drawdown_pct (fraction; null if no series) to every canonical
    # by_asset_class_policy_clean_net row.
    for _row in c_policy_net:
        _row["max_drawdown_pct"] = class_mdd_net.get(_row["asset_class"])
    dropped_policy = len(kept) - len(kept_policy)

    registry = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": _now_utc(),
        "description": (
            "Canonical profit-factor registry. Single source of truth for PF/WR. "
            "Deduplicates signal re-emissions and flags resolver spot-flicker "
            "artifacts. Consumers should READ this instead of recomputing PF."
        ),
        "source_files": source_meta,
        "source_files_canonical": SOURCE_FILES_CANONICAL,
        "methodology": {
            "dedup_key": ["strategy(source_system|strategy)", "symbol",
                          "direction", "trade_date", "entry_price~%dp" % ENTRY_PRICE_ROUND],
            "spot_flicker_threshold_pnl_pct": SPOT_FLICKER_THRESHOLD,
            "spot_flicker_rule": (
                "non-crypto closed pick with abs(pnl_pct) below threshold is "
                "dropped as resolver spot-flicker artifact"
            ),
            "win_definition": "pnl_pct > 0",
            "profit_factor": "gross_profit / gross_loss (loss magnitude); "
                             "null when gross_loss == 0",
            "trade_date_fallback": ["entry_date", "entry_time", "timestamp",
                                    "created_at", "closed_at", "resolved_at",
                                    "exit_date", "exit_time"],
        },
        "counts": {
            "raw_rows": cls["raw_count"],
            "closed_rows": cls["closed_count"],
            "after_flicker_filter": cls["sane_count"],
            "deduped_rows": len(kept),
            "policy_clean_rows": len(kept_policy),
            "dropped_not_closed": cls["dropped_open"],
            "dropped_spot_flicker": cls["dropped_flicker"],
            "dropped_duplicate_reemissions": cls["dropped_dup"],
            "dropped_policy_excluded": dropped_policy,
        },
        "policy_excluded_count": len(POLICY_EXCLUDED),
        "canonical_view": "by_asset_class_policy_clean_net",
        "slippage_model": "alpha_engine.charter_slippage.deduct_slippage "
                          "(M-069 fraction-unit round-trip bps)",
        "by_asset_class_raw": raw_class,
        "by_asset_class": c,
        "by_asset_class_policy_clean": c_policy,
        "by_asset_class_policy_clean_net": c_policy_net,
        "by_asset_class_strategy_policy_clean_net": cs_policy_net,
        "by_asset_class_strategy": cs,
        "by_asset_class_strategy_symbol": css,
        "by_asset_class_strategy_date": csd,
    }

    out_path = os.path.join(REPO_ROOT, OUTPUT_FILE)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(registry, fh, indent=2, sort_keys=False)
        fh.write("\n")

    # ---- console summary -------------------------------------------------
    print("PF REGISTRY built -> %s" % OUTPUT_FILE)
    print("  schema_version: %s" % SCHEMA_VERSION)
    print("  raw rows: %d | closed: %d | deduped: %d" % (
        cls["raw_count"], cls["closed_count"], len(kept)))
    print("  dropped: not-closed=%d  spot-flicker=%d  duplicate-reemission=%d"
          "  policy-excluded=%d" % (
              cls["dropped_open"], cls["dropped_flicker"], cls["dropped_dup"],
              dropped_policy))
    print()
    raw_map = {r["asset_class"]: r for r in raw_class}
    policy_map = {r["asset_class"]: r for r in c_policy}
    print("  %-12s %10s %10s %12s %8s %8s" % (
        "ASSET_CLASS", "RAW_PF", "DEDUP_PF", "POLICY_PF", "RAW_n", "POL_n"))
    for r in c:
        ac = r["asset_class"]
        rr = raw_map.get(ac, {})
        pp = policy_map.get(ac, {})
        print("  %-12s %10s %10s %12s %8s %8s" % (
            ac,
            rr.get("profit_factor", "-"),
            r.get("profit_factor", "-"),
            pp.get("profit_factor", "-"),
            rr.get("n", "-"),
            pp.get("n", "-"),
        ))

    # COMMODITY COT / CT=F sanity check (signal-level, per report)
    # Strategy names in local data: cot_positioning, cftc_cot_commercial_signal
    _COT_STRATS = {"cot_positioning", "cftc_cot_commercial_signal", "multi_asset_cot"}
    print()
    ctf_rows = [r for r in css
                if r["asset_class"] == "COMMODITY"
                and r["strategy"] in _COT_STRATS
                and r.get("symbol") == "CT=F"]
    if ctf_rows:
        for r in ctf_rows:
            print("  SANITY (COMMODITY/%s/CT=F): deduped PF=%s WR=%s "
                  "n=%d (report expects PF~4.69, WR~77.5%%, n~40)" % (
                      r["strategy"], r.get("profit_factor"), r.get("win_rate_pct"), r["n"]))
    else:
        # Aggregate across all COT strategy names for CT=F
        ctf_all = [r for r in css
                   if r["asset_class"] == "COMMODITY" and r.get("symbol") == "CT=F"]
        if ctf_all:
            strats = [r["strategy"] for r in ctf_all]
            print("  SANITY (COMMODITY/CT=F): found under strategy=%s; "
                  "no row with strategy in %s" % (strats, sorted(_COT_STRATS)))
        else:
            print("  SANITY: COMMODITY/CT=F not found in deduped registry "
                  "(likely all excluded or not yet in local closed_picks.json).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
