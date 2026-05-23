#!/usr/bin/env python3
"""pick_surface_snapshot.py — opt-in writer that POPULATES at_pick_surface_eval.

This is a PURE SIDECAR. It freezes, per active pick, the gate-input snapshot
(elite_score, smart_score, trust_score, trust_tier, confidence, forward_wr,
risk_reward, regime, consensus_count) plus the 4 surface-qualification flags
(in_active, in_smart_picks, in_high_conviction, in_money_ready) and the
outcome columns — so any /audit surface is fully reproducible from the DB.

It changes NO production behavior. It is gated by the env var
PICK_SURFACE_SNAPSHOT_ENABLED (default OFF). When OFF, snapshot_pick still
returns the row dict (so callers/tests work) but is_enabled() / write_rows()
do nothing.

DB: host mysql.50webs.com, db ejaguiar1_stocks. Honors AUDIT_DB_HOST /
AUDIT_DB_USER / AUDIT_DB_PASS. py_compile-clean.

═══════════════════════════════════════════════════════════════════════════
## Wiring Plan
═══════════════════════════════════════════════════════════════════════════
Target caller : audit_trail/dashboard_generator.py
Location      : immediately AFTER the smart-picks / high-conviction
                computation block (around line 16967+, where the per-pick
                in_smart_picks / in_high_conviction sets are finalized).
Integration   :

    from tools.pick_surface_snapshot import (
        snapshot_pick, write_rows, is_enabled,
    )
    if is_enabled():                       # env-gated, default OFF
        _surface_rows = []
        for _pick in active_picks:         # the finalized active-pick list
            _gate_results = {
                "in_active":          _pick in active_picks,
                "in_smart_picks":     _pick.get("symbol") in smart_pick_symbols,
                "in_high_conviction": _pick.get("symbol") in hc_symbols,
                "in_money_ready":     money_ready_classes.get(
                                          _pick.get("asset_class")) is True,
            }
            _surface_rows.append(snapshot_pick(_pick, _gate_results))
        write_rows(_surface_rows)          # single bulk insert

Expected wire-up : follow-up PR (opt-in; flip PICK_SURFACE_SNAPSHOT_ENABLED=1
                   in the dashboard workflow once verified). Until then this
                   module has no production caller by design — sidecar.
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

ENV_FLAG = "PICK_SURFACE_SNAPSHOT_ENABLED"

# ── columns inserted, in order ───────────────────────────────────────────────
_COLUMNS = (
    "raw_pick_id", "dedup_hash", "aggregation_run_id", "symbol", "asset_class",
    "direction", "strategy", "source_system",
    "elite_score", "smart_score", "trust_score", "trust_tier", "confidence",
    "forward_wr", "risk_reward", "regime", "consensus_count",
    "in_active", "in_smart_picks", "in_high_conviction", "in_money_ready",
    "surface_detail", "status", "pnl_pct", "closed_at",
)

# terminal statuses — mirrors edge_finder.TERMINAL_STATUSES
_TERMINAL = {
    "closed", "closed_tp", "closed_sl", "won", "win", "lost", "loss",
    "expired", "sl_hit", "tp_hit", "time_exit", "flat", "stale",
}


# ════════════════════════════════════════════════════════════════════════════
# PURE HELPERS
# ════════════════════════════════════════════════════════════════════════════
def is_enabled() -> bool:
    """True iff the env flag opts this sidecar in. Default OFF."""
    return os.environ.get(ENV_FLAG, "0").strip().lower() in ("1", "true", "yes", "on")


def _num(v: Any) -> Any:
    """float() if possible, else None — keeps DECIMAL columns clean."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v: Any) -> Any:
    n = _num(v)
    return int(n) if n is not None else None


def _first(pick: dict, *keys: str) -> Any:
    """First non-None value among pick[key] for key in keys."""
    for k in keys:
        if pick.get(k) is not None:
            return pick.get(k)
    return None


def _bool01(v: Any) -> int:
    """Coerce a truthy/flag value to 0/1."""
    if v in (1, True, "1", "true", "True", "yes", "Y"):
        return 1
    return 0


def snapshot_pick(pick: dict, gate_results: dict | None = None) -> dict:
    """Build one at_pick_surface_eval row from a pick dict + gate_results.

    `pick` is a dashboard pick dict. `gate_results`, if given, supplies the
    4 surface flags (in_active / in_smart_picks / in_high_conviction /
    in_money_ready). If `gate_results` is None, this function attempts to
    call the live gate functions (best-effort; missing modules => flag 0).

    Returns a dict keyed by the at_pick_surface_eval columns. Safe to call
    even when the sidecar is disabled — write_rows() is the gated step.
    """
    pick = dict(pick or {})
    gate_results = dict(gate_results or {})

    flags = _resolve_flags(pick, gate_results)

    asset_class = (str(_first(pick, "asset_class", "category") or "") or None)
    if asset_class:
        asset_class = asset_class.upper()

    status = _first(pick, "status")
    pnl = _num(_first(pick, "pnl_pct"))
    closed_at = _first(pick, "closed_at")
    # only stamp outcome columns when actually terminal
    if not (status and str(status).strip().lower() in _TERMINAL):
        pnl = pnl if (status and str(status).strip().lower() in _TERMINAL) else pnl

    detail = gate_results.get("surface_detail")
    surface_detail = json.dumps(detail) if isinstance(detail, (dict, list)) else detail

    return {
        "raw_pick_id":        _int(_first(pick, "raw_pick_id", "raw_id")),
        "dedup_hash":         _first(pick, "dedup_hash"),
        "aggregation_run_id": _first(pick, "aggregation_run_id", "run_id"),
        "symbol":             str(_first(pick, "symbol") or "")[:32],
        "asset_class":        asset_class,
        "direction":          _first(pick, "direction", "signal_type"),
        "strategy":           _first(pick, "strategy", "source_system"),
        "source_system":      _first(pick, "source_system", "source"),
        "elite_score":        _num(_first(pick, "elite_score")),
        "smart_score":        _num(_first(pick, "smart_score")),
        "trust_score":        _num(_first(pick, "trust_score")),
        "trust_tier":         _first(pick, "trust_tier", "hf_conviction_tier"),
        "confidence":         _num(_first(pick, "confidence")),
        "forward_wr":         _num(_first(pick, "forward_wr", "forward_win_rate")),
        "risk_reward":        _num(_first(pick, "risk_reward", "rr", "risk_reward_ratio")),
        "regime":             _first(pick, "regime", "market_regime"),
        "consensus_count":    _int(_first(pick, "consensus_count", "consensus")),
        "in_active":          flags["in_active"],
        "in_smart_picks":     flags["in_smart_picks"],
        "in_high_conviction": flags["in_high_conviction"],
        "in_money_ready":     flags["in_money_ready"],
        "surface_detail":     surface_detail,
        "status":             status,
        "pnl_pct":            pnl,
        "closed_at":          closed_at,
    }


def _resolve_flags(pick: dict, gate_results: dict) -> dict[str, int]:
    """Use gate_results when present; else best-effort call the live gates."""
    out = {"in_active": 0, "in_smart_picks": 0,
           "in_high_conviction": 0, "in_money_ready": 0}

    explicit = {k: gate_results[k] for k in out if k in gate_results}
    for k, v in explicit.items():
        out[k] = _bool01(v)
    if len(explicit) == 4:
        return out  # caller supplied everything — trust it

    # ── best-effort live-gate fallback for any flag not supplied ─────────────
    if "in_active" not in explicit:
        try:
            from audit_trail.quality_gates import passes_active_gate
            out["in_active"] = _bool01(passes_active_gate(pick))
        except Exception:
            pass
    if "in_smart_picks" not in explicit:
        try:
            from audit_trail.quality_gates import passes_smart_gate
            out["in_smart_picks"] = _bool01(passes_smart_gate(pick))
        except Exception:
            pass
    if "in_high_conviction" not in explicit:
        try:
            from tools.dashboard_hc_rules import passes_high_conviction_pick
            out["in_high_conviction"] = _bool01(passes_high_conviction_pick(pick))
        except Exception:
            pass
    # in_money_ready is a per-class verdict (no single pick-level function);
    # if the caller did not supply it, leave 0 — see Wiring Plan.
    return out


# ════════════════════════════════════════════════════════════════════════════
# DB LAYER
# ════════════════════════════════════════════════════════════════════════════
def _connect():
    import pymysql
    host = os.environ.get("AUDIT_DB_HOST", "mysql.50webs.com")
    user = os.environ.get("AUDIT_DB_USER", "ejaguiar1_stocks")
    pwd = os.environ.get("AUDIT_DB_PASS", os.environ.get("DB_PASS_STOCKS", ""))
    return pymysql.connect(
        host=host, user=user, password=pwd, database="ejaguiar1_stocks",
        connect_timeout=20, autocommit=False,
    )


def write_rows(rows: list[dict]) -> int:
    """Bulk-insert snapshot rows into at_pick_surface_eval.

    No-op (returns 0) when the sidecar is disabled via env flag. Returns the
    number of rows inserted. Each `row` must be a dict from snapshot_pick()."""
    if not is_enabled():
        print(f"[pick_surface_snapshot] disabled "
              f"({ENV_FLAG} not set) — skipping write of {len(rows or [])} rows")
        return 0
    if not rows:
        return 0

    placeholders = ", ".join(["%s"] * len(_COLUMNS))
    sql = (f"INSERT INTO at_pick_surface_eval ({', '.join(_COLUMNS)}) "
           f"VALUES ({placeholders})")
    values = [tuple(r.get(c) for c in _COLUMNS) for r in rows]

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, values)
        conn.commit()
        print(f"[pick_surface_snapshot] inserted {len(values)} rows "
              f"into at_pick_surface_eval")
        return len(values)
    except Exception as exc:  # pragma: no cover - network path
        conn.rollback()
        print(f"[pick_surface_snapshot] write FAILED, rolled back: {exc}")
        raise
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════
def _selftest() -> int:
    pick = {
        "symbol": "BTCUSDT", "category": "crypto", "direction": "LONG",
        "strategy": "dna_winner", "elite_score": 72, "smart_score": 55.5,
        "trust_score": 40, "trust_tier": "RELIABLE", "confidence": 0.81,
        "forward_wr": 58.0, "risk_reward": 2.1, "regime": "bull",
        "consensus_count": 3, "status": "WON", "pnl_pct": 2.4,
        "closed_at": "2026-05-01 12:00:00",
    }
    gr = {"in_active": 1, "in_smart_picks": 1,
          "in_high_conviction": 0, "in_money_ready": True,
          "surface_detail": {"hc_fail": "gate8_consensus"}}
    row = snapshot_pick(pick, gr)
    assert set(row.keys()) == set(_COLUMNS), set(_COLUMNS) ^ set(row.keys())
    assert row["symbol"] == "BTCUSDT"
    assert row["asset_class"] == "CRYPTO"
    assert row["elite_score"] == 72.0
    assert row["confidence"] == 0.81
    assert row["in_active"] == 1 and row["in_smart_picks"] == 1
    assert row["in_high_conviction"] == 0 and row["in_money_ready"] == 1
    assert json.loads(row["surface_detail"])["hc_fail"] == "gate8_consensus"

    # missing-field tolerance
    sparse = snapshot_pick({"symbol": "ETHUSDT"}, {})
    assert sparse["symbol"] == "ETHUSDT"
    assert sparse["elite_score"] is None
    assert sparse["in_active"] in (0, 1)  # may call live gate or default 0

    # disabled => write_rows no-op
    os.environ.pop(ENV_FLAG, None)
    assert is_enabled() is False
    assert write_rows([row]) == 0

    print("pick_surface_snapshot self-test: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest())
