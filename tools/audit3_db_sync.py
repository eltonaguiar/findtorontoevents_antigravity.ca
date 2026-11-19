"""audit3_db_sync.py — persist audit3's verdict *history* into ejaguiar1_stocks.

Why this exists
---------------
audit3 already produces the right objects, but they are written as files that are
replaced in place:

  audit_dashboard/data/audit3_ledger.json     overwritten every hour
  reports/forward_observations.jsonl          append-only, but only in git
  reports/hypothesis_registry.json            append-only, but only in git

That makes every question about *change* unanswerable in SQL:

  * when did CRYPTO flip KILL -> WEAK, and did the n grow enough to explain it?
  * which cells churned between WEAK and CANDIDATE across the week?
  * how many forward rows has POD-CRYPTO-POSITION accrued per day?
  * was a pod's hypothesis registered BEFORE its first forward row?

ejaguiar1_stocks has 409 tables (at_pick_outcomes, at_raw_picks, at_pick_flow_daily,
...) and none of them hold any audit3 state. This tool mirrors the five stateful
objects into that database so the questions above become SELECTs:

  audit3_ledger_snapshots      one row per generator run
  audit3_cell_verdicts         one row per (snapshot, namespace, class, strategy, direction)
  audit3_pod_clocks            one row per (snapshot, pod)
  audit3_forward_observations  append-only mirror of the JSONL, keyed by observation id
  audit3_hypotheses            one row per registry entry, so pods/forward rows join to
                               their pre-registered acceptance criteria

Safety
------
* **Dry run by default.** Nothing touches the network unless ``--apply`` is passed.
  ``--apply`` is the operator's deliberate act; there is no environment variable or
  ambient flag that can turn writing on.
* Only ``CREATE TABLE IF NOT EXISTS`` and ``INSERT ... ON DUPLICATE KEY UPDATE`` are
  issued. No DELETE, no TRUNCATE, no ALTER, no UPDATE of existing columns outside an
  upsert. A re-run is therefore idempotent and cannot lose history.
* All values go through ``%s`` placeholders. The only interpolated identifier is the
  table name, which comes from this module's own ``TABLES`` constant.
* Credentials come from ``tools/db_env.get_stocks_creds()`` and are never printed.

Usage
-----
  # always start here: prints the plan, touches nothing
  python3 tools/audit3_db_sync.py

  python3 tools/audit3_db_sync.py --apply

  # write the plan to a sidecar instead of a database
  python3 tools/audit3_db_sync.py --json-out /tmp/audit3_sync_plan.json

Exit codes: 0 plan built (dry run) or rows written; 2 unusable input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:  # direct `python3 tools/audit3_db_sync.py`
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_LEDGER = REPO_ROOT / "audit_dashboard/data/audit3_ledger.json"
DEFAULT_FORWARD = REPO_ROOT / "reports/forward_observations.jsonl"
DEFAULT_REGISTRY = REPO_ROOT / "reports/hypothesis_registry.json"

DDL_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS audit3_ledger_snapshots (
  snapshot_id            VARCHAR(32)  NOT NULL,
  generated_at           DATETIME     NOT NULL,
  source_generated_at    DATETIME     NULL,
  git_sha                VARCHAR(64)  NULL,
  input_sha256           VARCHAR(64)  NULL,
  generator_version      VARCHAR(32)  NULL,
  n_rows                 INT          NULL,
  n_cells_total          INT          NULL,
  n_cells_tested         INT          NULL,
  n_proven               INT          NULL,
  n_candidate            INT          NULL,
  n_weak                 INT          NULL,
  n_kill                 INT          NULL,
  n_insufficient         INT          NULL,
  selection_alpha_available TINYINT(1) NOT NULL DEFAULT 0,
  forward_n_rows         INT          NULL,
  forward_fingerprint    VARCHAR(32)  NULL,
  synced_at              DATETIME     NOT NULL,
  PRIMARY KEY (snapshot_id),
  KEY idx_generated (generated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

DDL_CELLS = """
CREATE TABLE IF NOT EXISTS audit3_cell_verdicts (
  snapshot_id            VARCHAR(32)  NOT NULL,
  namespace              VARCHAR(32)  NOT NULL,
  asset_class            VARCHAR(32)  NOT NULL,
  strategy               VARCHAR(190) NOT NULL DEFAULT '',
  direction              VARCHAR(16)  NOT NULL DEFAULT '',
  n                      INT          NULL,
  wins                   INT          NULL,
  wr                     DECIMAL(10,6) NULL,
  pf                     DECIMAL(12,6) NULL,
  net_expectancy_pct     DECIMAL(14,6) NULL,
  net_ci_lo_pct          DECIMAL(14,6) NULL,
  net_ci_hi_pct          DECIMAL(14,6) NULL,
  net_ci_lo_2x_pct       DECIMAL(14,6) NULL,
  mean_cost_pct          DECIMAL(12,6) NULL,
  materiality_floor_pct  DECIMAL(12,6) NULL,
  q_value                DECIMAL(12,6) NULL,
  harm_q                 DECIMAL(12,6) NULL,
  dsr                    DECIMAL(12,6) NULL,
  required_n             INT          NULL,
  verdict                VARCHAR(24)  NOT NULL DEFAULT '',
  raw_verdict            VARCHAR(24)  NULL,
  alpha_status           VARCHAR(24)  NULL,
  recent_ok              TINYINT(1)   NULL,
  stress_2x_ok           TINYINT(1)   NULL,
  reasons_json           LONGTEXT     NULL,
  PRIMARY KEY (snapshot_id, namespace, asset_class, strategy, direction),
  KEY idx_verdict (verdict),
  KEY idx_cell (asset_class, strategy, direction)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

DDL_PODS = """
CREATE TABLE IF NOT EXISTS audit3_pod_clocks (
  snapshot_id            VARCHAR(32)  NOT NULL,
  pod_id                 VARCHAR(64)  NOT NULL,
  hypothesis_id          VARCHAR(64)  NULL,
  status                 VARCHAR(24)  NULL,
  n_forward              INT          NULL,
  min_n                  INT          NULL,
  eligible               TINYINT(1)   NOT NULL DEFAULT 0,
  promotion_blocked_by   VARCHAR(24)  NULL,
  pf_ci_lb               DECIMAL(12,6) NULL,
  ir                     DECIMAL(12,6) NULL,
  reasons_json           LONGTEXT     NULL,
  PRIMARY KEY (snapshot_id, pod_id),
  KEY idx_pod (pod_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

DDL_FORWARD = """
CREATE TABLE IF NOT EXISTS audit3_forward_observations (
  observation_id         VARCHAR(64)  NOT NULL,
  first_seen_snapshot    VARCHAR(32)  NULL,
  hypothesis_id          VARCHAR(64)  NULL,
  symbol                 VARCHAR(48)  NULL,
  asset_class            VARCHAR(32)  NULL,
  side                   VARCHAR(16)  NULL,
  opened_at              DATETIME     NULL,
  closed_at              DATETIME     NULL,
  entry_px               DECIMAL(20,8) NULL,
  exit_px                DECIMAL(20,8) NULL,
  gross_mismatch_pp      DECIMAL(14,6) NULL,
  slippage_bps           DECIMAL(14,6) NULL,
  intrabar_first_touch   TINYINT(1)   NULL,
  regime_ok              TINYINT(1)   NULL,
  resolver_version       VARCHAR(48)  NULL,
  PRIMARY KEY (observation_id),
  KEY idx_hyp (hypothesis_id),
  KEY idx_closed (closed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

DDL_HYPOTHESES = """
CREATE TABLE IF NOT EXISTS audit3_hypotheses (
  hypothesis_id          VARCHAR(64)  NOT NULL,
  asset_class            VARCHAR(32)  NULL,
  family                 VARCHAR(96)  NULL,
  status                 VARCHAR(32)  NULL,
  registered_at          DATETIME     NULL,
  description            TEXT         NULL,
  acceptance_json        LONGTEXT     NULL,
  result_json            LONGTEXT     NULL,
  synced_at              DATETIME     NOT NULL,
  PRIMARY KEY (hypothesis_id),
  KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


# ───────────────────────────────────────────────────────────────── value coercion ──
def _float(value: Any) -> Optional[float]:
    try:
        return None if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> Optional[int]:
    try:
        return None if value is None or value == "" else int(float(value))
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> Optional[int]:
    if value is None:
        return None
    return 1 if value else 0


def _key(value: Any) -> str:
    """Primary-key columns are NOT NULL: NULL would defeat the unique index."""
    return "" if value is None else str(value)[:190]


def _json(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, default=str, sort_keys=True)


def _dt(value: Any) -> Optional[str]:
    """Normalise an ISO timestamp to MySQL DATETIME text (UTC, no offset)."""
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _ci_pair(value: Any) -> tuple[Optional[float], Optional[float]]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return _float(value[0]), _float(value[1])
    return None, None


# ─────────────────────────────────────────────────────────────────────── builders ──
def snapshot_id_for(ledger: dict) -> str:
    provenance = ledger.get("provenance") or {}
    basis = "|".join(
        str(x)
        for x in (
            ledger.get("generated_at"),
            provenance.get("git_sha"),
            provenance.get("input_sha256"),
        )
    )
    return "snap_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]


def build_snapshot(ledger: dict, synced_at: str) -> tuple[str, list]:
    summary = ledger.get("summary") or {}
    provenance = ledger.get("provenance") or {}
    selection_alpha = ledger.get("selection_alpha") or {}
    forward = ledger.get("forward_gate") or {}
    row = (
        snapshot_id_for(ledger),
        _dt(ledger.get("generated_at")) or synced_at,
        _dt(ledger.get("source_generated_at")),
        (provenance.get("git_sha") or None),
        (provenance.get("input_sha256") or None),
        (provenance.get("generator_version") or None),
        _int(summary.get("n_rows")),
        _int(summary.get("n_cells_total")),
        _int(summary.get("n_cells_tested")),
        _int(summary.get("n_proven")),
        _int(summary.get("n_candidate")),
        _int(summary.get("n_weak")),
        _int(summary.get("n_kill")),
        _int(summary.get("n_insufficient")),
        1 if selection_alpha.get("available") else 0,
        _int(forward.get("n_rows")),
        (forward.get("fingerprint") or None),
        synced_at,
    )
    sql = (
        "INSERT INTO audit3_ledger_snapshots (snapshot_id, generated_at, source_generated_at, "
        "git_sha, input_sha256, generator_version, n_rows, n_cells_total, n_cells_tested, "
        "n_proven, n_candidate, n_weak, n_kill, n_insufficient, selection_alpha_available, "
        "forward_n_rows, forward_fingerprint, synced_at) VALUES (" + ",".join(["%s"] * 18) + ") "
        "ON DUPLICATE KEY UPDATE n_rows=VALUES(n_rows), n_cells_tested=VALUES(n_cells_tested), "
        "n_proven=VALUES(n_proven), n_candidate=VALUES(n_candidate), n_weak=VALUES(n_weak), "
        "n_kill=VALUES(n_kill), n_insufficient=VALUES(n_insufficient), "
        "selection_alpha_available=VALUES(selection_alpha_available), synced_at=VALUES(synced_at)"
    )
    return sql, [row]


def _cell_row(entry: dict, snapshot_id: str, namespace: str) -> tuple:
    lo, hi = _ci_pair(entry.get("net_ci_pct"))
    lo2, _hi2 = _ci_pair(entry.get("net_ci_pct_2x"))
    return (
        snapshot_id,
        namespace,
        _key(entry.get("asset_class") or "UNKNOWN")[:32],
        _key(entry.get("strategy")),
        _key(entry.get("direction")),
        _int(entry.get("n")),
        _int(entry.get("wins")),
        _float(entry.get("wr")),
        _float(entry.get("pf")),
        _float(entry.get("net_expectancy_pct")),
        lo,
        hi,
        lo2,
        _float(entry.get("mean_cost_pct")),
        _float(entry.get("materiality_floor_pct")),
        _float(entry.get("q_value")),
        _float(entry.get("harm_q")),
        _float(entry.get("dsr")),
        _int(entry.get("required_n")),
        _key(entry.get("verdict"))[:24],
        _key(entry.get("raw_verdict"))[:24] or None,
        _key((entry.get("alpha_gate") or {}).get("status"))[:24] or None,
        _bool(entry.get("recent_ok")),
        _bool(entry.get("stress_2x_ok")),
        _json(entry.get("reasons")),
    )


CELL_COLUMNS = (
    "snapshot_id, namespace, asset_class, strategy, direction, n, wins, wr, pf, "
    "net_expectancy_pct, net_ci_lo_pct, net_ci_hi_pct, net_ci_lo_2x_pct, mean_cost_pct, "
    "materiality_floor_pct, q_value, harm_q, dsr, required_n, verdict, raw_verdict, "
    "alpha_status, recent_ok, stress_2x_ok, reasons_json"
)


def build_cells(ledger: dict, snapshot_id: str) -> tuple[str, list]:
    rows = [_cell_row(c, snapshot_id, _key(c.get("namespace"))[:32] or "discovery")
            for c in (ledger.get("cells") or [])]
    rows += [_cell_row(c, snapshot_id, "__class__") for c in (ledger.get("classes") or [])]
    sql = (
        f"INSERT INTO audit3_cell_verdicts ({CELL_COLUMNS}) VALUES ("
        + ",".join(["%s"] * 25)
        + ") ON DUPLICATE KEY UPDATE n=VALUES(n), verdict=VALUES(verdict), "
        "q_value=VALUES(q_value), net_ci_lo_pct=VALUES(net_ci_lo_pct), dsr=VALUES(dsr), "
        "reasons_json=VALUES(reasons_json)"
    )
    return sql, rows


def build_pods(ledger: dict, snapshot_id: str) -> tuple[str, list]:
    forward = ledger.get("forward_gate") or {}
    rows = []
    for pod_id, pod in (forward.get("pods") or {}).items():
        if not isinstance(pod, dict):
            continue
        rows.append(
            (
                snapshot_id,
                _key(pod_id)[:64],
                (pod.get("hypothesis_id") or None),
                (pod.get("status") or None),
                _int(pod.get("n_forward")),
                _int(pod.get("min_n")),
                _bool(pod.get("eligible")) or 0,
                (pod.get("promotion_blocked_by_status") or None),
                _float(pod.get("pf_ci_lb")),
                _float(pod.get("ir")),
                _json(pod.get("reasons")),
            )
        )
    sql = (
        "INSERT INTO audit3_pod_clocks (snapshot_id, pod_id, hypothesis_id, status, n_forward, "
        "min_n, eligible, promotion_blocked_by, pf_ci_lb, ir, reasons_json) VALUES ("
        + ",".join(["%s"] * 11)
        + ") ON DUPLICATE KEY UPDATE status=VALUES(status), n_forward=VALUES(n_forward), "
        "eligible=VALUES(eligible), promotion_blocked_by=VALUES(promotion_blocked_by), "
        "pf_ci_lb=VALUES(pf_ci_lb), ir=VALUES(ir)"
    )
    return sql, rows


def build_forward(forward_path: Path, snapshot_id: str, errors: list) -> tuple[str, list]:
    seen: set[str] = set()
    rows = []
    if not forward_path.exists():
        return "", rows
    with forward_path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obs = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"{forward_path.name}:{lineno} not JSON")
                continue
            obs_id = (obs.get("id") or "").strip()
            if not obs_id:
                errors.append(f"{forward_path.name}:{lineno} missing id")
                continue
            if obs_id in seen:
                continue
            seen.add(obs_id)
            rows.append(
                (
                    obs_id[:64],
                    snapshot_id,
                    (obs.get("hypothesis_id") or None),
                    (obs.get("symbol") or None),
                    (obs.get("asset_class") or None),
                    (obs.get("side") or None),
                    _dt(obs.get("opened_at")),
                    _dt(obs.get("closed_at")),
                    _float(obs.get("entry_px")),
                    _float(obs.get("exit_px")),
                    _float(obs.get("gross_mismatch_pp")),
                    _float(obs.get("slippage_bps")),
                    _bool(obs.get("intrabar_first_touch")),
                    _bool(obs.get("regime_ok")),
                    (obs.get("resolver_version") or None),
                )
            )
    sql = (
        "INSERT INTO audit3_forward_observations (observation_id, first_seen_snapshot, "
        "hypothesis_id, symbol, asset_class, side, opened_at, closed_at, entry_px, exit_px, "
        "gross_mismatch_pp, slippage_bps, intrabar_first_touch, regime_ok, resolver_version) "
        "VALUES (" + ",".join(["%s"] * 15) + ") ON DUPLICATE KEY UPDATE "
        "exit_px=VALUES(exit_px), closed_at=VALUES(closed_at), "
        "gross_mismatch_pp=VALUES(gross_mismatch_pp), intrabar_first_touch=VALUES(intrabar_first_touch)"
    )
    return sql, rows


def build_hypotheses(registry_path: Path, synced_at: str, errors: list) -> tuple[str, list]:
    rows = []
    if not registry_path.exists():
        errors.append(f"{registry_path.name} missing")
        return "", rows
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{registry_path.name}: {exc}")
        return "", rows
    entries = registry.get("hypotheses") if isinstance(registry, dict) else registry
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        hyp_id = (entry.get("id") or "").strip()
        if not hyp_id:
            errors.append("registry entry missing id")
            continue
        rows.append(
            (
                hyp_id[:64],
                (entry.get("asset_class") or None),
                (entry.get("family") or None),
                (entry.get("status") or None),
                _dt(entry.get("registered_at")),
                (entry.get("description") or None),
                _json(entry.get("acceptance_criteria")),
                _json(entry.get("result")),
                synced_at,
            )
        )
    sql = (
        "INSERT INTO audit3_hypotheses (hypothesis_id, asset_class, family, status, registered_at, "
        "description, acceptance_json, result_json, synced_at) VALUES ("
        + ",".join(["%s"] * 9)
        + ") ON DUPLICATE KEY UPDATE status=VALUES(status), result_json=VALUES(result_json), "
        "acceptance_json=VALUES(acceptance_json), synced_at=VALUES(synced_at)"
    )
    return sql, rows


# ─────────────────────────────────────────────────────────────────────────── plan ──
def plan(
    ledger_path: Path = DEFAULT_LEDGER,
    forward_path: Path = DEFAULT_FORWARD,
    registry_path: Path = DEFAULT_REGISTRY,
    synced_at: Optional[str] = None,
) -> dict:
    """Build the full write plan without touching a database or the network."""
    synced_at = synced_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    snapshot_id = snapshot_id_for(ledger)
    errors: list[str] = []

    snap_sql, snap_rows = build_snapshot(ledger, synced_at)
    cell_sql, cell_rows = build_cells(ledger, snapshot_id)
    pod_sql, pod_rows = build_pods(ledger, snapshot_id)
    fwd_sql, fwd_rows = build_forward(Path(forward_path), snapshot_id, errors)
    hyp_sql, hyp_rows = build_hypotheses(Path(registry_path), synced_at, errors)

    return {
        "snapshot_id": snapshot_id,
        "snapshot": {"ddl": DDL_SNAPSHOTS, "sql": snap_sql, "rows": snap_rows},
        "cells": {"ddl": DDL_CELLS, "sql": cell_sql, "rows": cell_rows},
        "pods": {"ddl": DDL_PODS, "sql": pod_sql, "rows": pod_rows},
        "forward": {"ddl": DDL_FORWARD, "sql": fwd_sql, "rows": fwd_rows},
        "hypotheses": {"ddl": DDL_HYPOTHESES, "sql": hyp_sql, "rows": hyp_rows},
        "errors": errors,
    }


ORDER = ("snapshot", "cells", "pods", "forward", "hypotheses")
TABLE_NAMES = {
    "snapshot": "audit3_ledger_snapshots",
    "cells": "audit3_cell_verdicts",
    "pods": "audit3_pod_clocks",
    "forward": "audit3_forward_observations",
    "hypotheses": "audit3_hypotheses",
}


def counts(write_plan: dict) -> dict[str, int]:
    return {key: len(write_plan[key]["rows"]) for key in ORDER}


def apply_plan(
    write_plan: dict,
    connector: Optional[Callable[[], Any]] = None,
) -> dict[str, int]:
    """Execute the plan. The caller is responsible for having decided to apply."""
    if connector is None:
        from tools.db_env import get_stocks_creds  # local import: dry runs need no creds

        import pymysql

        creds = get_stocks_creds()
        creds.pop("read_timeout", None)

        def connector() -> Any:  # noqa: F811 - deliberately shadows the parameter
            return pymysql.connect(read_timeout=120, write_timeout=120, autocommit=False, **creds)

    written: dict[str, int] = {}
    connection = connector()
    try:
        cursor = connection.cursor()
        for key in ORDER:
            section = write_plan[key]
            cursor.execute(section["ddl"])
            if section["rows"]:
                cursor.executemany(section["sql"], section["rows"])
            written[TABLE_NAMES[key]] = cursor.rowcount if cursor.rowcount >= 0 else len(section["rows"])
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        try:
            connection.close()
        except Exception:
            pass
    return written


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Mirror audit3 state into ejaguiar1_stocks.")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--forward", type=Path, default=DEFAULT_FORWARD)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--apply", action="store_true",
                        help="actually write. Without this flag nothing leaves the machine.")
    parser.add_argument("--json-out", type=Path, default=None,
                        help="write the plan (counts + snapshot id, never credentials) here")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        write_plan = plan(args.ledger, args.forward, args.registry)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unusable input: {exc}", file=sys.stderr)
        return 2

    tally = counts(write_plan)
    print(f"snapshot_id {write_plan['snapshot_id']}")
    for key in ORDER:
        print(f"  {TABLE_NAMES[key]:34s} {tally[key]:>6d} rows")
    for err in write_plan["errors"][:10]:
        print(f"  skip: {err}", file=sys.stderr)

    payload = {
        "dry_run": not args.apply,
        "snapshot_id": write_plan["snapshot_id"],
        "counts": tally,
        "errors": write_plan["errors"][:50],
    }
    if args.json_out:
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if not args.apply:
        print("dry run: no database connection was opened (pass --apply to write)")
        return 0
    if len(write_plan["snapshot"]["rows"]) != 1:
        print("refusing to apply: expected exactly one snapshot row", file=sys.stderr)
        return 2
    written = apply_plan(write_plan)
    print("written:")
    for table, n in written.items():
        print(f"  {table:34s} {n:>6d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
