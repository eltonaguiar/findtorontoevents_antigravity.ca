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

SCHEMA_VERSION = "1.1.0"

# ---------------------------------------------------------------------------
# Single-source concentration flag (FINDING_OVERALL#8, 2026-05-30)
# ---------------------------------------------------------------------------
# The /money-maker-readyv2 audit found `crypto_liquidity_wick_reversal_v1`
# looked like a unique PF>=1.5/n>=30/WR>=50 edge — but 100% of its 30 picks
# came from one source (`battleground`). Skill rule #2: if >60% of decisive
# picks come from one source_system, it is concentration, not edge.
#
# Threshold is configurable via env var so audit consumers can experiment.
# n_min=5 avoids flagging tiny-n rows where one extra pick swings >60%.
SOURCE_CONCENTRATION_THRESHOLD_DEFAULT = 0.60
SOURCE_CONCENTRATION_MIN_N = 5


def _source_concentration_threshold() -> float:
    """Read threshold from env var on each call so tests can monkey-patch it."""
    raw = os.environ.get("PF_REGISTRY_SOURCE_CONCENTRATION_THRESHOLD")
    if raw is None or raw == "":
        return SOURCE_CONCENTRATION_THRESHOLD_DEFAULT
    try:
        return float(raw)
    except ValueError:
        return SOURCE_CONCENTRATION_THRESHOLD_DEFAULT


def _row_source(row) -> str:
    """Canonical source identifier for concentration analysis.

    Uses `source_system` (the engine that emitted the pick, e.g. `battleground`,
    `alpha_engine`, `mercury2`) which is what the skill rule references. Falls
    back to `_origin_file` basename when missing (e.g. legacy mercury2 ledger
    rows) so EVERY kept row contributes a source identifier.
    """
    src = row.get("source_system")
    if src:
        s = str(src).strip()
        if s:
            return s
    origin = row.get("_origin_file")
    if origin:
        base = os.path.basename(str(origin))
        # closed_picks.json is repeated across folders; prefer parent dir name
        # when the basename is a generic ledger filename.
        if base in ("closed_picks.json", "closed_picks_fast.json"):
            # Path shape: <engine>/data/closed_picks.json — the engine name
            # lives in the grandparent (parent of `data/`). Fall back to the
            # immediate parent when there is no `data/` segment.
            parent_dir = os.path.dirname(str(origin))
            parent = os.path.basename(parent_dir)
            if parent == "data":
                gp = os.path.basename(os.path.dirname(parent_dir))
                if gp:
                    return f"file:{gp}"
            return f"file:{parent or 'unknown'}"
        return f"file:{base}"
    return "unknown"


def _compute_source_concentration(source_counts: dict) -> dict:
    """Given {source -> n} return concentration fields.

    Returns dict with keys: single_source_pct, top_source, is_single_source_artifact.
    n is the sum of source_counts.values().
    """
    n_total = sum(source_counts.values())
    if n_total <= 0:
        return {
            "single_source_pct": None,
            "top_source": None,
            "is_single_source_artifact": False,
        }
    top_source, top_n = max(source_counts.items(), key=lambda kv: (kv[1], kv[0]))
    pct = top_n / n_total
    threshold = _source_concentration_threshold()
    flag = (pct > threshold) and (n_total >= SOURCE_CONCENTRATION_MIN_N)
    return {
        "single_source_pct": round(pct, 6),
        "top_source": top_source,
        "is_single_source_artifact": bool(flag),
    }

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

    at_pick_outcomes synthetic pick_ids (v1::signal_validation::...) share a
    10-char prefix — use the full id so dedup does not collapse distinct rows.
    """
    pid = str(row.get("pick_id") or "")
    if pid.startswith("v1::"):
        return pid
    for field in ("entry_date", "entry_time", "timestamp", "created_at",
                   "closed_at", "resolved_at", "exit_date", "exit_time"):
        v = row.get(field)
        if v:
            s = str(v)
            if s.startswith("v1::"):
                return s
            # ISO strings: take the date portion
            return s[:10]
    return "UNKNOWN"


def _asset_class(row) -> str:
    """Resolve asset class via the canonical classifier when missing/UNKNOWN."""
    ac = _norm(row.get("asset_class"), default="")
    if not ac:
        ac = _norm(row.get("category"), default="")
    if ac:
        up = ac.upper()
        if up in ("UNKNOWN", "NONE", "NULL", "NAN"):
            ac = ""
        elif up == "STOCKS":
            return "EQUITY"
        else:
            return up
    if not isinstance(row, dict):
        row = {}
    try:
        from alpha_engine.asset_class import classify_pick_asset_class_upper

        derived = classify_pick_asset_class_upper(row)
        if derived and derived not in ("UNKNOWN", "NONE"):
            return derived
    except Exception:
        pass
    # Last-resort legacy heuristic (crypto suffix only).
    sym = str(row.get("symbol", "")).upper()
    if sym.endswith("USDT") or (sym.endswith("USD") and len(sym) <= 8):
        return "CRYPTO"
    return "EQUITY"


def _strategy(row) -> str:
    """Strategy identity for keying. Prefer source_system (the emission
    grouping that the COT dedup bug lives in), fall back to strategy."""
    return _norm(row.get("source_system") or row.get("strategy"))


def _is_win(pnl_pct) -> bool:
    return pnl_pct is not None and pnl_pct > 0


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def _load_mysql_rows(days: int = 90) -> tuple[list, dict]:
    """Read closed picks from MySQL trading_picks (Action Item from
    reports/2026-05-25_policy_clean_vs_top_edges_funnel.md).

    Gated by env var PF_REGISTRY_INCLUDE_DB=1 (default off) so the historic
    JSON-only behavior is preserved unless explicitly opted in. Reuses the
    existing extract_funnel.fetch_picks reader so column selection stays in
    sync with the audit pipeline.

    Returns (rows, meta). rows match the JSON shape consumed by classify_rows:
      - `category` from MySQL is copied into `asset_class` (which _asset_class
        reads) so dedup / NET / policy all see the same field name as JSON
        rows.
      - `_origin_file` is set to a synthetic identifier so source_meta can
        report DB contributions distinctly.
      - status is uppercased and entry_date is filled from created_at so the
        existing dedup key (strategy, symbol, direction, entry_date,
        ~entry_price) groups DB rows identically to JSON re-emissions.
    """
    rows: list = []
    meta: dict = {"enabled": True, "days": days}
    try:
        from tools import db_env  # type: ignore[import-not-found]
        from tools.audit_pick_funnel import extract_funnel  # type: ignore[import-not-found]
    except ImportError as exc:
        meta.update({"loaded": 0, "error": f"import failed: {exc}"})
        return rows, meta
    try:
        import pymysql  # type: ignore[import-not-found]
    except ImportError as exc:
        meta.update({"loaded": 0, "error": f"pymysql missing: {exc}"})
        return rows, meta
    try:
        creds = db_env.get_stocks_creds()
        creds.setdefault("cursorclass", pymysql.cursors.DictCursor)
        conn = pymysql.connect(**creds)
    except Exception as exc:  # broad: host-block / network / auth
        meta.update({"loaded": 0, "error": f"connect failed: {type(exc).__name__}"})
        return rows, meta
    try:
        raw = extract_funnel.fetch_picks(conn, days=days)
    except Exception as exc:
        meta.update({"loaded": 0, "error": f"fetch failed: {type(exc).__name__}"})
        try:
            conn.close()
        except Exception:
            pass
        return rows, meta
    try:
        conn.close()
    except Exception:
        pass
    for r in raw:
        if not isinstance(r, dict):
            continue
        r = dict(r)
        # Bridge schema: MySQL has `category` and `created_at`; classify_rows
        # reads `asset_class` and falls back through entry_date->...->created_at
        # for the dedup key. Set asset_class explicitly so _asset_class doesn't
        # have to infer.
        if r.get("category") and not r.get("asset_class"):
            r["asset_class"] = r["category"]
        status = str(r.get("status") or "").upper()
        if status:
            r["status"] = status
        r["_origin_file"] = f"mysql:trading_picks:{days}d"
        rows.append(r)
    meta["loaded"] = len(rows)
    return rows, meta


def _load_tournament_picks_rows(days: int = 90) -> tuple[list, dict]:
    """Read resolved picks from MySQL `tournament_picks` (the AI-tournament
    table populated by `tools/ai_tournament/ingest_to_db.py`). 40 models ×
    ~1613 resolved trades that are otherwise invisible to pf_registry.

    Gated by env var `PF_REGISTRY_INCLUDE_TOURNAMENT_DB=1` (separate from
    `PF_REGISTRY_INCLUDE_DB` so operators can opt into tournament + trading
    picks independently). Only `status IN ('WIN','LOSS')` rows are returned.

    Returns (rows, meta). rows match the JSON shape consumed by classify_rows:
      - `strategy` from `strategy_name` (falls back to `persona_id`).
      - `asset_class` carried through as-is.
      - `_origin_file` tagged `mysql:tournament_picks:Nd`.
      - `entry_date` filled from `submitted_at` (else `created_at`).
    """
    rows: list = []
    meta: dict = {"enabled": True, "days": days}
    try:
        from tools import db_env  # type: ignore[import-not-found]
    except ImportError as exc:
        meta.update({"loaded": 0, "error": f"import failed: {exc}"})
        return rows, meta
    try:
        import pymysql  # type: ignore[import-not-found]
    except ImportError as exc:
        meta.update({"loaded": 0, "error": f"pymysql missing: {exc}"})
        return rows, meta
    try:
        creds = db_env.get_stocks_creds()
        creds.setdefault("cursorclass", pymysql.cursors.DictCursor)
        conn = pymysql.connect(**creds)
    except Exception as exc:
        meta.update({"loaded": 0, "error": f"connect failed: {type(exc).__name__}"})
        return rows, meta
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT strategy_name, persona_id, model_id, asset_class,
                       symbol, direction, entry_price, exit_price, pnl_pct,
                       status, submitted_at, resolved_at, created_at,
                       data_integrity_flag
                FROM tournament_picks
                WHERE status IN ('WIN','LOSS')
                  AND COALESCE(submitted_at, created_at) >= NOW() - INTERVAL %s DAY
                """,
                (days,),
            )
            raw = list(cur.fetchall())
    except Exception as exc:
        meta.update({"loaded": 0, "error": f"fetch failed: {type(exc).__name__}"})
        try:
            conn.close()
        except Exception:
            pass
        return rows, meta
    try:
        conn.close()
    except Exception:
        pass
    for r in raw:
        if not isinstance(r, dict):
            continue
        r = dict(r)
        strategy = (
            r.get("strategy_name")
            or r.get("persona_id")
            or r.get("model_id")
            or "tournament_unknown"
        )
        r["strategy"] = str(strategy)
        if r.get("asset_class"):
            r["asset_class"] = str(r["asset_class"])
        status = str(r.get("status") or "").upper()
        if status:
            r["status"] = status
        # entry_date: classify_rows dedup key reads entry_date with fallbacks;
        # set it explicitly so DB rows dedup against JSON re-emissions cleanly.
        if not r.get("entry_date"):
            r["entry_date"] = (
                r.get("submitted_at") or r.get("created_at") or ""
            )
        r["_origin_file"] = f"mysql:tournament_picks:{days}d"
        rows.append(r)
    meta["loaded"] = len(rows)
    return rows, meta


def _load_outcomes_rows() -> tuple[list, dict]:
    """Resolver-grade at_pick_outcomes (PF_REGISTRY_INCLUDE_OUTCOMES=1)."""
    rows: list = []
    meta: dict = {"enabled": True}
    try:
        from tools import db_env  # type: ignore[import-not-found]
        import pymysql  # type: ignore[import-not-found]
    except ImportError as exc:
        return rows, {"enabled": True, "loaded": 0, "error": str(exc)}
    try:
        creds = {k: v for k, v in db_env.get_stocks_creds().items()
                 if k not in ("cursorclass", "connect_timeout")}
        conn = pymysql.connect(**creds, connect_timeout=15,
                               cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pick_id, symbol, strategy, asset_class, status, pnl_pct, resolved_at "
                "FROM at_pick_outcomes WHERE status IN ('WON','LOST') AND pnl_pct IS NOT NULL"
            )
            raw = list(cur.fetchall())
        conn.close()
    except Exception as exc:
        return rows, {"enabled": True, "loaded": 0, "error": type(exc).__name__}
    for r in raw:
        r = dict(r)
        pnl = r.get("pnl_pct")
        if pnl is not None:
            pnl_f = float(pnl)
            r["pnl_pct"] = pnl_f / 100.0 if abs(pnl_f) > 1.0 else pnl_f
        status = str(r.get("status") or "").upper()
        r["status"] = "WIN" if status == "WON" else "LOSS"
        if r.get("asset_class"):
            r["asset_class"] = str(r["asset_class"]).upper()
        r["entry_date"] = str(r.get("pick_id") or r.get("resolved_at") or "")
        # Keep strategy as dedup identity — do not set source_system here
        # (_strategy prefers source_system and would collapse all rows to one key).
        r["_origin_file"] = "mysql:at_pick_outcomes"
        rows.append(r)
    meta["loaded"] = len(rows)
    return rows, meta


def load_rows():
    """Returns (rows, source_meta). rows is a flat list of dicts; source_meta
    records which files were found and how many rows each contributed.

    When env var PF_REGISTRY_INCLUDE_DB=1 is set, ALSO loads closed picks
    direct from MySQL trading_picks via _load_mysql_rows(). When
    PF_REGISTRY_INCLUDE_TOURNAMENT_DB=1 is set, ALSO loads resolved picks
    from MySQL tournament_picks via _load_tournament_picks_rows() (the
    AI-tournament cohort: 40 models, ~1.6k resolved trades). The merged
    cohort then flows through the same classify_rows dedup + flicker filter
    + policy-clean NET aggregation as JSON-sourced rows. See
    reports/2026-05-25_policy_clean_vs_top_edges_funnel.md."""
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
    # Additional non-JSON_PICK_SOURCES feeder: hyrotrader emits closed picks
    # from its real-fills-only journal via tools/hyrotrader_closed_picks_emitter.py.
    # Wired here (rather than added to JSON_PICK_SOURCES in dashboard_generator)
    # so this PR doesn't touch the dashboard generator. Empty journal → file
    # is either absent or has picks=[] → 0 rows contributed.
    _hyro_rel = "audit_dashboard/data/hyrotrader_closed_picks.json"
    _hyro_path = os.path.join(REPO_ROOT, _hyro_rel)
    if os.path.isfile(_hyro_path):
        try:
            with open(_hyro_path, "r", encoding="utf-8") as f:
                _hyro_doc = json.load(f)
            _hyro_picks = _hyro_doc.get("picks") if isinstance(_hyro_doc, dict) else _hyro_doc
            _hyro_n = 0
            if isinstance(_hyro_picks, list):
                for r in _hyro_picks:
                    if not isinstance(r, dict):
                        continue
                    r = dict(r)
                    r["_origin_file"] = _hyro_rel
                    rows.append(r)
                    _hyro_n += 1
            source_meta.append({"file": _hyro_rel, "present": True, "rows": _hyro_n})
        except (OSError, json.JSONDecodeError) as exc:
            source_meta.append({"file": _hyro_rel, "present": True, "rows": 0,
                                "error": f"read failed: {type(exc).__name__}"})
    else:
        source_meta.append({"file": _hyro_rel, "present": False, "rows": 0,
                            "note": "run tools/hyrotrader_closed_picks_emitter.py to materialize closed picks from hyrotrader_journal.json"})
    if os.environ.get("PF_REGISTRY_INCLUDE_DB") == "1":
        db_days_raw = os.environ.get("PF_REGISTRY_DB_DAYS") or "90"
        try:
            db_days = max(1, int(db_days_raw))
        except ValueError:
            db_days = 90
        db_rows, db_meta = _load_mysql_rows(days=db_days)
        rows.extend(db_rows)
        source_meta.append({
            "file": f"mysql://trading_picks?days={db_days}",
            "present": True,
            "rows": db_meta.get("loaded", 0),
            **{k: v for k, v in db_meta.items() if k in ("error", "days")},
        })
    else:
        source_meta.append({
            "file": "mysql://trading_picks",
            "present": False,
            "rows": 0,
            "note": "set PF_REGISTRY_INCLUDE_DB=1 to merge MySQL cohort",
        })
    if os.environ.get("PF_REGISTRY_INCLUDE_TOURNAMENT_DB") == "1":
        t_days_raw = os.environ.get("PF_REGISTRY_TOURNAMENT_DB_DAYS") or "90"
        try:
            t_days = max(1, int(t_days_raw))
        except ValueError:
            t_days = 90
        t_rows, t_meta = _load_tournament_picks_rows(days=t_days)
        rows.extend(t_rows)
        source_meta.append({
            "file": f"mysql://tournament_picks?days={t_days}",
            "present": True,
            "rows": t_meta.get("loaded", 0),
            **{k: v for k, v in t_meta.items() if k in ("error", "days")},
        })
    else:
        source_meta.append({
            "file": "mysql://tournament_picks",
            "present": False,
            "rows": 0,
            "note": "set PF_REGISTRY_INCLUDE_TOURNAMENT_DB=1 to merge AI-tournament cohort (40 models, ~1.6k resolved trades)",
        })
    if os.environ.get("PF_REGISTRY_INCLUDE_OUTCOMES") == "1":
        o_rows, o_meta = _load_outcomes_rows()
        rows.extend(o_rows)
        source_meta.append({
            "file": "mysql://at_pick_outcomes",
            "present": True,
            "rows": o_meta.get("loaded", 0),
            **{k: v for k, v in o_meta.items() if k == "error"},
        })
    else:
        source_meta.append({
            "file": "mysql://at_pick_outcomes",
            "present": False,
            "rows": 0,
            "note": "set PF_REGISTRY_INCLUDE_OUTCOMES=1 for resolver-grade sleeves",
        })
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
    # Per-group source-system tallies for the FINDING_OVERALL#8 single-source
    # artifact flag — { group_key: { source: count } }.
    src_csd = defaultdict(lambda: defaultdict(int))
    src_css = defaultdict(lambda: defaultdict(int))
    src_cs = defaultdict(lambda: defaultdict(int))
    src_c = defaultdict(lambda: defaultdict(int))
    # (trade_date, pnl) pairs per class — sorted by trade_date for the equity
    # curve so the MDD is self-consistent with the PF/WR built above.
    class_series = defaultdict(list)

    for r in kept_rows:
        ac = _asset_class(r)
        strat = _strategy(r)
        sym = _norm_symbol(r.get("symbol"))
        td = _trade_date(r)
        pnl = _net_pnl(r["_pnl_pct"], ac) if net else r["_pnl_pct"]
        src = _row_source(r)

        _accumulate(by_class_strategy_date[(ac, strat, td)], pnl)
        _accumulate(by_class_strategy_symbol[(ac, strat, sym)], pnl)
        _accumulate(by_class_strategy[(ac, strat)], pnl)
        _accumulate(by_class[ac], pnl)
        src_csd[(ac, strat, td)][src] += 1
        src_css[(ac, strat, sym)][src] += 1
        src_cs[(ac, strat)][src] += 1
        src_c[ac][src] += 1
        class_series[ac].append((td, pnl))

    rows_csd = [
        {"asset_class": ac, "strategy": strat, "trade_date": td,
         **_finalize(stat),
         **_compute_source_concentration(src_csd[(ac, strat, td)])}
        for (ac, strat, td), stat in sorted(by_class_strategy_date.items())
    ]
    rows_css = [
        {"asset_class": ac, "strategy": strat, "symbol": sym,
         **_finalize(stat),
         **_compute_source_concentration(src_css[(ac, strat, sym)])}
        for (ac, strat, sym), stat in sorted(by_class_strategy_symbol.items())
    ]
    rows_cs = [
        {"asset_class": ac, "strategy": strat, **_finalize(stat),
         **_compute_source_concentration(src_cs[(ac, strat)])}
        for (ac, strat), stat in sorted(by_class_strategy.items())
    ]
    rows_c = [
        {"asset_class": ac, **_finalize(stat),
         **_compute_source_concentration(src_c[ac])}
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
    src_c = defaultdict(lambda: defaultdict(int))
    for r in rows:
        status = str(r.get("status", "")).upper()
        if status and status not in CLOSED_STATUSES:
            continue
        pnl = _to_float(r.get("pnl_pct"))
        if pnl is None:
            continue
        ac = _asset_class(r)
        _accumulate(by_class[ac], pnl)
        src_c[ac][_row_source(r)] += 1
    return [
        {"asset_class": ac, **_finalize(stat),
         **_compute_source_concentration(src_c[ac])}
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
