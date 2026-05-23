"""
Audit Trail Verification & Query Script
========================================
Run: python -m audit_trail.verify

Prints summary stats from the audit trail DB.
"""

from audit_trail.db import get_connection


def verify():
    conn = get_connection()

    print("=" * 60)
    print("AUDIT TRAIL VERIFICATION")
    print("=" * 60)

    # Schema version
    ver = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    print(f"\nSchema version: {ver[0] if ver else 'UNKNOWN'}")

    # Table counts
    print("\nTable row counts:")
    for table in ["aggregation_runs", "raw_picks", "consensus_picks",
                  "filter_log", "audit_events", "strategy_stats"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:25s} {count:>6d} rows")

    # Latest run
    run = conn.execute(
        "SELECT * FROM aggregation_runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if run:
        print(f"\nLatest run:")
        print(f"  ID:        {run['run_id'][:8]}...")
        print(f"  Started:   {run['started_at']}")
        print(f"  Status:    {run['status']}")
        print(f"  Systems:   {run['systems_loaded']}")
        print(f"  Raw picks: {run['raw_picks_count']}")
        print(f"  Consensus: {run['consensus_count']}")

    # Filter breakdown
    print("\nFilter reasons (all time):")
    rows = conn.execute(
        "SELECT filter_reason, COUNT(*) as cnt FROM filter_log "
        "GROUP BY filter_reason ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r['filter_reason']:25s} {r['cnt']:>6d}")

    # Source system pick counts
    print("\nRaw picks by source system:")
    rows = conn.execute(
        "SELECT source_system, COUNT(*) as cnt FROM raw_picks "
        "GROUP BY source_system ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    for r in rows:
        print(f"  {r['source_system']:25s} {r['cnt']:>6d}")

    # Consensus picks by status
    print("\nConsensus picks by status:")
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM consensus_picks "
        "GROUP BY status ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r['status']:25s} {r['cnt']:>6d}")

    # Event types
    print("\nAudit events by type:")
    rows = conn.execute(
        "SELECT event_type, COUNT(*) as cnt FROM audit_events "
        "GROUP BY event_type ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r['event_type']:30s} {r['cnt']:>6d}")

    # Filter funnel
    total_raw = conn.execute("SELECT COUNT(*) FROM raw_picks").fetchone()[0]
    valid = conn.execute(
        "SELECT COUNT(*) FROM raw_picks WHERE was_stale=0 AND was_banned=0 "
        "AND was_demoted=0 AND was_wr_suppressed=0"
    ).fetchone()[0]
    consensus = conn.execute("SELECT COUNT(*) FROM consensus_picks").fetchone()[0]
    print(f"\nFilter funnel:")
    print(f"  Raw picks loaded:    {total_raw}")
    print(f"  After filters:       {valid}")
    print(f"  Consensus picks:     {consensus}")
    if total_raw > 0:
        print(f"  Pass rate:           {consensus / total_raw * 100:.1f}%")

    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    verify()
