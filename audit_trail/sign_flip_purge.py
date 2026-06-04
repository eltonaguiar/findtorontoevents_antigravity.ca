"""Sign-flip purge tool — operator-approved manual run.

Companion to `audit_trail/sign_coherence_check.py` (PR #431, the read-only
diagnostic). That tool found 367 rows in `at_pick_outcomes` where the
stored `pnl_pct` sign disagrees with the recomputed sign from
`entry_price` / `exit_price` / `direction`. The root cause is the
resolver writing positive `pnl_pct` + `status='TP_HIT'` regardless of
whether the trade actually won.

This script applies the corrections:
  1. Identify suspect rows via the same SQL query as sign_coherence_check
  2. Back up the affected rows to `ejaguiar1_backups.at_pick_outcomes_pre_signflip_purge_<ts>`
  3. For each row: UPDATE at_pick_outcomes SET status=<corrected>,
     pnl_pct=<sign-inverted>, resolver_version='signflip_purge_<ts>'
  4. Verify post-state matches expectations
  5. Write a JSON manifest of every change

**Operator must run this manually after reviewing PR #431's evidence.**
Default mode is DRY-RUN — no DB writes occur without `--apply`.

Usage:
    # Dry-run first (read-only, no DB writes)
    python3 -m audit_trail.sign_flip_purge

    # Apply for real (with backup)
    python3 -m audit_trail.sign_flip_purge --apply

    # Filter to one source for safer staged rollout
    python3 -m audit_trail.sign_flip_purge --source mega_mutation --apply

Exit codes:
    0 — dry-run complete or apply succeeded
    1 — discrepancy in post-state verification (manual review needed)
    2 — DB error / no candidates / preflight failed
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any


def _connect_stocks():
    import mysql.connector
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "mysql.50webs.com"),
        user=os.environ.get("DB_USER", "ejaguiar1_stocks"),
        password=os.environ.get("DB_PASS") or os.environ.get("AUDIT_DB_PASS") or "",  # 2026-06-04 INCIDENT #89 scrub: removed convention literal fallback
        database=os.environ.get("DB_NAME", "ejaguiar1_stocks"),
        connection_timeout=15,
    )


def _connect_backups():
    import mysql.connector
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "mysql.50webs.com"),
        user="ejaguiar1_backups",
        password=os.environ.get("DB_BACKUPS_PASS") or "backups1234560",
        database="ejaguiar1_backups",
        connection_timeout=15,
    )


def _expected(entry: float, exit_: float, direction: str) -> float | None:
    if entry is None or exit_ is None:
        return None
    try:
        e = float(entry); x = float(exit_)
    except (TypeError, ValueError):
        return None
    if e <= 0:
        return None
    sign = -1.0 if str(direction or "LONG").upper().strip() in ("SHORT", "SELL") else 1.0
    return sign * (x - e) / e * 100.0


def _corrected_status(recomputed: float, sl_pct_threshold: float = 0.1) -> str:
    """Map sign of recomputed pnl to corrected status."""
    if recomputed > sl_pct_threshold:
        return "WON"
    if recomputed < -sl_pct_threshold:
        return "LOST"
    return "EXPIRED"


def scan_candidates(source_filter: str | None = None) -> list[dict[str, Any]]:
    """Return the list of rows that need flipping. Read-only."""
    conn = _connect_stocks()
    cur = conn.cursor()
    where = ""
    params: list[Any] = []
    if source_filter:
        where = " AND tp.source_system LIKE %s"
        params.append(f"%{source_filter}%")
    cur.execute(
        f"""
        SELECT tp.id, tp.source_system, tp.symbol, tp.direction,
               tp.entry_price, tp.exit_price,
               apo.status, apo.pnl_pct, apo.resolver_version
        FROM at_pick_outcomes apo
        INNER JOIN trading_picks tp ON apo.pick_id = tp.id
        WHERE tp.entry_price IS NOT NULL AND tp.exit_price IS NOT NULL
          AND tp.entry_price > 0 AND apo.pnl_pct IS NOT NULL
          {where}
        """,
        params,
    )
    rows = cur.fetchall()
    conn.close()
    candidates: list[dict[str, Any]] = []
    for r in rows:
        pid, source, symbol, direction, entry, exit_, status, stored, resver = r
        try:
            stored_f = float(stored)
        except (TypeError, ValueError):
            continue
        rec = _expected(entry, exit_, direction)
        if rec is None:
            continue
        if abs(rec) > 0.1 and abs(stored_f) > 0.1 and (rec * stored_f < 0):
            candidates.append({
                "pick_id": pid,
                "source_system": source,
                "symbol": symbol,
                "direction": direction,
                "entry_price": float(entry),
                "exit_price": float(exit_),
                "old_status": status,
                "old_pnl_pct": stored_f,
                "new_status": _corrected_status(rec),
                "new_pnl_pct": round(rec, 4),
                "old_resolver_version": resver,
            })
    return candidates


def backup_rows(pick_ids: list[str], backup_table: str) -> int:
    """Create backup table + copy the affected rows. Idempotent (DROP+CREATE)."""
    src = _connect_stocks()
    bk = _connect_backups()
    src_cur = src.cursor()
    bk_cur = bk.cursor()

    src_cur.execute("SHOW COLUMNS FROM at_pick_outcomes")
    cols = src_cur.fetchall()
    col_defs = ", ".join(f"`{c[0]}` {c[1]}" + (" NULL" if c[2] == "YES" else " NOT NULL") for c in cols)
    col_names = ", ".join(f"`{c[0]}`" for c in cols)

    bk_cur.execute(f"DROP TABLE IF EXISTS `{backup_table}`")
    bk_cur.execute(f"CREATE TABLE `{backup_table}` ({col_defs}, PRIMARY KEY (pick_id)) ENGINE=InnoDB")
    bk.commit()

    if not pick_ids:
        bk.close(); src.close()
        return 0
    placeholders = ", ".join(["%s"] * len(pick_ids))
    src_cur.execute(f"SELECT {col_names} FROM at_pick_outcomes WHERE pick_id IN ({placeholders})", pick_ids)
    rows = src_cur.fetchall()
    val_ph = ", ".join(["%s"] * len(cols))
    bk_cur.executemany(f"INSERT INTO `{backup_table}` ({col_names}) VALUES ({val_ph})", rows)
    bk.commit()
    bk_cur.execute(f"SELECT COUNT(*) FROM `{backup_table}`")
    n = bk_cur.fetchone()[0]
    bk.close(); src.close()
    return n


def apply_corrections(candidates: list[dict[str, Any]], resolver_version: str) -> int:
    """Apply the UPDATEs. Returns rows affected."""
    conn = _connect_stocks()
    cur = conn.cursor()
    n = 0
    for c in candidates:
        cur.execute(
            "UPDATE at_pick_outcomes SET status=%s, pnl_pct=%s, resolver_version=%s WHERE pick_id=%s",
            (c["new_status"], c["new_pnl_pct"], resolver_version, c["pick_id"]),
        )
        n += cur.rowcount
    conn.commit()
    conn.close()
    return n


def verify_postsweep(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Confirm the UPDATE landed for each pick_id."""
    if not candidates:
        return {"checked": 0, "mismatches": 0}
    conn = _connect_stocks()
    cur = conn.cursor()
    ids = [c["pick_id"] for c in candidates]
    placeholders = ", ".join(["%s"] * len(ids))
    cur.execute(
        f"SELECT pick_id, status, pnl_pct FROM at_pick_outcomes WHERE pick_id IN ({placeholders})",
        ids,
    )
    by_id = {r[0]: (r[1], float(r[2])) for r in cur.fetchall()}
    conn.close()
    mismatches = []
    for c in candidates:
        if c["pick_id"] not in by_id:
            mismatches.append({"pick_id": c["pick_id"], "reason": "row_disappeared"})
            continue
        actual_status, actual_pnl = by_id[c["pick_id"]]
        if actual_status != c["new_status"]:
            mismatches.append({"pick_id": c["pick_id"], "reason": "status_mismatch", "want": c["new_status"], "got": actual_status})
        if abs(actual_pnl - c["new_pnl_pct"]) > 0.001:
            mismatches.append({"pick_id": c["pick_id"], "reason": "pnl_mismatch", "want": c["new_pnl_pct"], "got": actual_pnl})
    return {"checked": len(candidates), "mismatches": mismatches, "n_mismatches": len(mismatches)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign-flip purge (manual operator run)")
    parser.add_argument("--apply", action="store_true", help="Actually apply UPDATEs. Without this, dry-run only.")
    parser.add_argument("--source", default=None, help="Filter to source_system substring (staged rollout)")
    parser.add_argument("--json", default=None, help="Write change manifest to this path")
    parser.add_argument("--skip-backup", action="store_true", help="(DANGEROUS) skip the backup step")
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    resolver_version = f"signflip_purge_{ts[:13]}"[:20]
    backup_table = f"at_pick_outcomes_pre_signflip_purge_{ts}"

    print(f"Scanning candidates" + (f" filtered to source={args.source}" if args.source else "") + "...")
    candidates = scan_candidates(source_filter=args.source)
    print(f"  found: {len(candidates)} sign-flipped rows")
    if not candidates:
        print("  nothing to fix.")
        return 2

    # Per-source breakdown
    from collections import Counter
    by_source = Counter(c["source_system"] for c in candidates)
    print("  by source_system:")
    for src, n in by_source.most_common():
        print(f"    {n:>5d}  {src}")

    if not args.apply:
        print("\nDRY-RUN — no DB writes. Re-run with --apply to actually correct these rows.")
        if args.json:
            with open(args.json, "w") as f:
                json.dump({"ts": ts, "candidates": candidates}, f, indent=2, default=str)
            print(f"  manifest written to {args.json}")
        return 0

    # === APPLY MODE ===
    if not args.skip_backup:
        print(f"\nBacking up {len(candidates)} rows to ejaguiar1_backups.{backup_table}...")
        n_bk = backup_rows([c["pick_id"] for c in candidates], backup_table)
        print(f"  backup row count: {n_bk}")
        if n_bk != len(candidates):
            print(f"[ERR] backup row count mismatch (want {len(candidates)}, got {n_bk}) — aborting", file=sys.stderr)
            return 2

    print(f"\nApplying UPDATEs (resolver_version={resolver_version})...")
    n_applied = apply_corrections(candidates, resolver_version)
    print(f"  rows affected: {n_applied}")

    print("\nVerifying post-state...")
    verify = verify_postsweep(candidates)
    print(f"  checked: {verify['checked']}, mismatches: {verify['n_mismatches']}")
    if verify['n_mismatches'] > 0:
        print(f"[WARN] {verify['n_mismatches']} mismatches detected. Manual review needed.", file=sys.stderr)
        for m in verify.get("mismatches", [])[:10]:
            print(f"  {m}", file=sys.stderr)

    if args.json:
        with open(args.json, "w") as f:
            json.dump({
                "ts": ts,
                "backup_table": backup_table,
                "resolver_version": resolver_version,
                "n_candidates": len(candidates),
                "n_applied": n_applied,
                "verification": verify,
                "candidates": candidates,
            }, f, indent=2, default=str)
        print(f"\nFull manifest: {args.json}")

    return 1 if verify['n_mismatches'] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
