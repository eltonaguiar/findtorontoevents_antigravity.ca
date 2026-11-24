#!/usr/bin/env python3
"""Immutable experiment tracker (SQLite) matching docs/experiment_schema.sql.

API is append-only by design: there is intentionally no update/delete function.
Every run records git commit, config hash, data snapshot, seed and metrics so a
result can be reproduced or refuted later.

Usage:
  python3 tools/experiment_tracker.py --init runs.db
  python3 tools/experiment_tracker.py --list runs.db
  python3 tools/experiment_tracker.py --show runs.db <run_id>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

# The DDL lives in exactly one place: docs/experiment_schema.sql (a SQLite port of
# the Postgres original, docs/experiment_schema.pg.sql). This module used to carry
# its own five-table literal, which drifted from the twelve-table contract without
# anything noticing. Do not reintroduce a CREATE TABLE literal here.
_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "docs" / "experiment_schema.sql"


def load_schema() -> str:
    """Return the DDL from docs/experiment_schema.sql (single source of truth)."""
    return _SCHEMA_PATH.read_text(encoding="utf-8")


def _now():
    return datetime.now(timezone.utc).isoformat()


def init_db(path):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(p) as cx:
        cx.executescript(load_schema())
    return str(p)


def config_hash(params):
    return hashlib.sha256(json.dumps(params or {}, sort_keys=True).encode()).hexdigest()


def log_run(path, *, run_type, strategy_name, strategy_version, git_commit,
            data_snapshot_id, start_ts, end_ts, status="ok", seed=None,
            notes=None, params=None, metrics=None, artifacts=None, mc=None,
            parent_run_id=None, config_hash_value=None):
    run_id = str(uuid.uuid4())
    with sqlite3.connect(path) as cx:
        cx.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, run_type, parent_run_id, strategy_name, strategy_version,
             git_commit, config_hash_value or config_hash(params),
             data_snapshot_id, seed, start_ts, end_ts, status, notes))
        for k, v in (params or {}).items():
            cx.execute("INSERT INTO run_params VALUES (?,?,?,?)",
                       (run_id, k, json.dumps(v), type(v).__name__))
        for m in (metrics or []):
            cx.execute("INSERT INTO metrics VALUES (?,?,?,?,?)",
                       (run_id, m["name"], m.get("value"), m["scope"],
                        m.get("window_id", "")))
        for a in (artifacts or []):
            cx.execute("INSERT INTO artifacts VALUES (?,?,?,?,?)",
                       (run_id, a["type"], a["path"], a.get("checksum", ""), _now()))
        if mc:
            cx.execute("INSERT INTO mc_runs VALUES (?,?,?,?,?,?,?,?,?)",
                       (run_id, parent_run_id, mc.get("n_sims"), mc.get("block"),
                        mc.get("ruin_threshold"), mc.get("ruin_prob"),
                        mc.get("mdd_p05"), mc.get("mdd_p50"), mc.get("mdd_p95")))
    return run_id


def query_run(path, run_id):
    with sqlite3.connect(path) as cx:
        cx.row_factory = sqlite3.Row
        row = cx.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["params"] = {r["param_name"]: r["param_value"] for r in
                         cx.execute("SELECT * FROM run_params WHERE run_id=?", (run_id,))}
        out["metrics"] = [dict(r) for r in
                          cx.execute("SELECT * FROM metrics WHERE run_id=?", (run_id,))]
        out["artifacts"] = [dict(r) for r in
                            cx.execute("SELECT * FROM artifacts WHERE run_id=?", (run_id,))]
        mc = cx.execute("SELECT * FROM mc_runs WHERE run_id=?", (run_id,)).fetchone()
        out["mc"] = dict(mc) if mc else None
        return out


def list_runs(path, limit=50):
    with sqlite3.connect(path) as cx:
        cx.row_factory = sqlite3.Row
        return [dict(r) for r in cx.execute(
            "SELECT run_id, run_type, strategy_name, git_commit, status, end_ts "
            "FROM runs ORDER BY end_ts DESC LIMIT ?", (limit,))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--show")
    a = ap.parse_args()
    if a.init:
        print("initialised", init_db(a.db))
    elif a.list:
        for r in list_runs(a.db):
            print(f"{r['run_id'][:8]} {r['status']:<6} {r['strategy_name']:<24} "
                  f"{r['git_commit'][:8]} {r['end_ts']}")
    elif a.show:
        print(json.dumps(query_run(a.db, a.show), indent=2))
    else:
        ap.error("choose --init/--list/--show")


if __name__ == "__main__":
    main()
