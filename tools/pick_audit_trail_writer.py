#!/usr/bin/env python3
"""pick_audit_trail_writer.py — opt-in writer that POPULATES at_pick_audit_trail.

This is a PURE SIDECAR. For one pick it emits an ordered STAGE-level decision
trace — one row per pipeline_stage the pick reached — so the full EMIT ->
ACTIVE_GATE -> SMART_GATE -> HC_GATE path is reproducible from the DB.

It changes NO production behavior. It is gated by the env var
PICK_AUDIT_TRAIL_ENABLED (default OFF). When OFF, build_trace_rows still
returns the row list (so callers/tests work) but is_enabled() / write_rows()
do nothing.

Decision semantics per stage:
    EMIT          — always PASS (the pick exists).
    ACTIVE_GATE   — PASS if in_active else REJECT.
    SMART_GATE    — PASS if in_smart_picks else REJECT.
    HC_GATE       — PASS if in_high_conviction else REJECT.
Once a stage REJECTs, every later stage is SKIP (the pick never reached it).
gate_order increments 1,2,3,4 across the four stages.

DB: host mysql.50webs.com, db ejaguiar1_stocks. Honors AUDIT_DB_HOST /
AUDIT_DB_USER / AUDIT_DB_PASS. py_compile-clean. Schema:
audit_integration/05_pick_audit_trail_schema.sql.

═══════════════════════════════════════════════════════════════════════════
## Wiring Plan
═══════════════════════════════════════════════════════════════════════════
Target caller : audit_trail/dashboard_generator.py
Location      : immediately AFTER the existing opt-in pick-surface snapshot
                block (right after `payload["picks"]["smart_picks"] =
                smart_picks`).
Integration   :

    from tools.pick_audit_trail_writer import (
        is_enabled, build_trace_rows, write_rows,
    )
    if is_enabled():                       # env-gated, default OFF
        _smart_ids = {id(_sp) for _sp in smart_picks}
        _trace_rows = []
        for _ap in payload["picks"]["active"]:
            _stage_results = {
                "in_active": 1,
                "in_smart_picks": 1 if id(_ap) in _smart_ids else 0,
            }
            _trace_rows.extend(build_trace_rows(_ap, _stage_results))
        write_rows(_trace_rows)            # single bulk insert

Status        : WIRED as opt-in sidecar (flip PICK_AUDIT_TRAIL_ENABLED=1 in
                the dashboard workflow once verified). No production behavior
                change while the flag is unset — sidecar by design.
═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

ENV_FLAG = "PICK_AUDIT_TRAIL_ENABLED"

# ── columns inserted, in order ───────────────────────────────────────────────
_COLUMNS = (
    "raw_pick_id", "dedup_hash", "aggregation_run_id", "symbol", "asset_class",
    "source_system", "strategy", "direction",
    "pipeline_stage", "gate_name", "gate_order", "decision", "reason",
    "detail", "score_snapshot",
)

# ── stage sequence: (pipeline_stage, gate_name, surface flag key) ────────────
# EMIT has no surface flag — it is always PASS.
_STAGES = (
    ("EMIT",        "emit",               None),
    ("ACTIVE_GATE", "active_gate",        "in_active"),
    ("SMART_GATE",  "smart_gate",         "in_smart_picks"),
    ("HC_GATE",     "high_conviction_gate", "in_high_conviction"),
)


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


def build_trace_rows(pick: dict, stage_results: dict) -> list[dict]:
    """Build the ordered STAGE-level audit trace for one pick.

    `pick` is a dashboard pick dict. `stage_results` supplies the surface
    flags, e.g. {"in_active": 1, "in_smart_picks": 0, "in_high_conviction": 0}.
    Any missing flag is treated as 0 (not in that surface).

    Returns a list of at_pick_audit_trail row dicts — one per pipeline_stage
    the pick reached. EMIT is always PASS. A stage PASSes iff its surface flag
    is truthy; the FIRST non-PASS stage is REJECT and every later stage is
    SKIP (the pick never reached it). Safe to call when the sidecar is
    disabled — write_rows() is the gated step.
    """
    pick = dict(pick or {})
    stage_results = dict(stage_results or {})

    asset_class = (str(_first(pick, "asset_class", "category") or "") or None)
    if asset_class:
        asset_class = asset_class.upper()

    base = {
        "raw_pick_id":        _int(_first(pick, "raw_pick_id", "raw_id")),
        "dedup_hash":         _first(pick, "dedup_hash"),
        "aggregation_run_id": _first(pick, "aggregation_run_id", "run_id"),
        "symbol":             str(_first(pick, "symbol") or "")[:32],
        "asset_class":        asset_class,
        "source_system":      _first(pick, "source_system", "source"),
        "strategy":           _first(pick, "strategy", "source_system"),
        "direction":          _first(pick, "direction", "signal_type"),
    }
    score = _num(_first(pick, "smart_score", "elite_score", "trust_score"))

    rows: list[dict] = []
    rejected = False  # becomes True once a stage fails — later stages SKIP
    for order, (stage, gate_name, flag_key) in enumerate(_STAGES, start=1):
        if stage == "EMIT":
            decision, reason = "PASS", "pick emitted by source system"
        elif rejected:
            decision = "SKIP"
            reason = "stage not reached (rejected upstream)"
        else:
            in_surface = _bool01(stage_results.get(flag_key, 0))
            if in_surface:
                decision = "PASS"
                reason = f"pick present in {flag_key}"
            else:
                decision = "REJECT"
                reason = f"pick absent from {flag_key}"
                rejected = True

        row = dict(base)
        row.update({
            "pipeline_stage": stage,
            "gate_name":      gate_name,
            "gate_order":     order,
            "decision":       decision,
            "reason":         (reason or "")[:255],
            "detail":         json.dumps({"flag_key": flag_key,
                                          "stage": stage}),
            "score_snapshot": score,
        })
        rows.append(row)
    return rows


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
    """Bulk-insert trace rows into at_pick_audit_trail.

    No-op (returns 0) when the sidecar is disabled via env flag. Returns the
    number of rows inserted. Each `row` must be a dict from build_trace_rows().
    """
    if not is_enabled():
        print(f"[pick_audit_trail_writer] disabled "
              f"({ENV_FLAG} not set) — skipping write of {len(rows or [])} rows")
        return 0
    if not rows:
        return 0

    placeholders = ", ".join(["%s"] * len(_COLUMNS))
    sql = (f"INSERT INTO at_pick_audit_trail ({', '.join(_COLUMNS)}) "
           f"VALUES ({placeholders})")
    values = [tuple(r.get(c) for c in _COLUMNS) for r in rows]

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, values)
        conn.commit()
        print(f"[pick_audit_trail_writer] inserted {len(values)} rows "
              f"into at_pick_audit_trail")
        return len(values)
    except Exception as exc:  # pragma: no cover - network path
        conn.rollback()
        print(f"[pick_audit_trail_writer] write FAILED, rolled back: {exc}")
        raise
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════════════
def _selftest() -> int:
    # ── case 1: pick rejected at SMART_GATE ──────────────────────────────────
    pick = {
        "symbol": "BTCUSDT", "category": "crypto", "direction": "LONG",
        "strategy": "dna_winner", "source_system": "dna_winner",
        "smart_score": 55.5, "raw_pick_id": 42,
    }
    rows = build_trace_rows(pick, {"in_active": 1, "in_smart_picks": 0,
                                   "in_high_conviction": 0})
    assert len(rows) == 4, len(rows)
    decisions = {r["pipeline_stage"]: r["decision"] for r in rows}
    assert decisions == {"EMIT": "PASS", "ACTIVE_GATE": "PASS",
                         "SMART_GATE": "REJECT", "HC_GATE": "SKIP"}, decisions
    assert [r["gate_order"] for r in rows] == [1, 2, 3, 4]
    assert all(set(r.keys()) == set(_COLUMNS) for r in rows)
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["asset_class"] == "CRYPTO"
    assert rows[0]["score_snapshot"] == 55.5
    assert json.loads(rows[2]["detail"])["flag_key"] == "in_smart_picks"

    # ── case 2: pick rejected at ACTIVE_GATE => SMART + HC both SKIP ──────────
    rows2 = build_trace_rows({"symbol": "X"}, {"in_active": 0})
    d2 = {r["pipeline_stage"]: r["decision"] for r in rows2}
    assert d2 == {"EMIT": "PASS", "ACTIVE_GATE": "REJECT",
                  "SMART_GATE": "SKIP", "HC_GATE": "SKIP"}, d2

    # ── case 3: pick passing all the way to HC_GATE ──────────────────────────
    rows3 = build_trace_rows({"symbol": "Y"},
                             {"in_active": 1, "in_smart_picks": 1,
                              "in_high_conviction": 1})
    d3 = {r["pipeline_stage"]: r["decision"] for r in rows3}
    assert d3 == {"EMIT": "PASS", "ACTIVE_GATE": "PASS",
                  "SMART_GATE": "PASS", "HC_GATE": "PASS"}, d3

    # ── case 4: missing flags default to 0 (REJECT at ACTIVE_GATE) ───────────
    rows4 = build_trace_rows({"symbol": "Z"}, {})
    d4 = {r["pipeline_stage"]: r["decision"] for r in rows4}
    assert d4 == {"EMIT": "PASS", "ACTIVE_GATE": "REJECT",
                  "SMART_GATE": "SKIP", "HC_GATE": "SKIP"}, d4

    # ── disabled => write_rows no-op ─────────────────────────────────────────
    os.environ.pop(ENV_FLAG, None)
    assert is_enabled() is False
    assert write_rows(rows) == 0

    print("pick_audit_trail_writer self-test: ALL PASS")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print("usage: python tools/pick_audit_trail_writer.py --selftest")
    sys.exit(0)
