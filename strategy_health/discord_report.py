#!/usr/bin/env python3
"""
Strategy Health Discord Report
================================
Posts a daily health card showing CORE/INCUBATOR/BANNED tiers.

Run:  python -m strategy_health.discord_report
"""

import datetime as dt
import json
import time

import pymysql
import requests

from strategy_health.config import (
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    DISCORD_HEALTH_WEBHOOK,
)


def get_connection():
    return pymysql.connect(
        host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DB, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def fetch_health_data(conn) -> dict:
    """Fetch all strategies grouped by tier."""
    cur = conn.cursor()
    cur.execute("""
        SELECT source_system, strategy, tier, total_trades, wins, losses,
               win_rate, fees_adj_expect, profit_factor, tier_reason, tier_changed_at
        FROM strategy_health
        ORDER BY tier, fees_adj_expect DESC
    """)
    rows = cur.fetchall()

    tiers = {"CORE": [], "INCUBATOR": [], "BANNED": []}
    for r in rows:
        tiers.setdefault(r["tier"], []).append(r)
    return tiers


def fetch_tier_changes_today(conn) -> list:
    """Fetch tier changes from the last 24 hours."""
    cur = conn.cursor()
    cur.execute("""
        SELECT strategy, old_tier, new_tier, reason, created_at
        FROM strategy_health_audit
        WHERE created_at >= NOW() - INTERVAL 24 HOUR
        ORDER BY created_at DESC
    """)
    return list(cur.fetchall())


def format_report(tiers: dict, changes: list) -> str:
    """Format the health report as a Discord code block."""
    today = dt.date.today().isoformat()
    lines = [
        f"Strategy Health Report -- {today}",
        "=" * 42,
        "",
    ]

    for tier_name, icon in [("CORE", "OK"), ("INCUBATOR", ".."), ("BANNED", "XX")]:
        strategies = tiers.get(tier_name, [])
        lines.append(f"{tier_name} ({len(strategies)})")
        if not strategies:
            lines.append("  (none)")
        for s in strategies[:15]:  # cap display
            pf_str = f"{float(s['profit_factor']):.1f}" if s["profit_factor"] else "inf"
            expect = float(s["fees_adj_expect"] or 0)
            lines.append(
                f"  [{icon}] {s['strategy'][:28]:28s} "
                f"{s['wins'] or 0}W/{s['losses'] or 0}L "
                f"expect:{expect:+.2f}% PF:{pf_str}"
            )
        lines.append("")

    if changes:
        lines.append(f"Tier changes (24h): {len(changes)}")
        for c in changes[:5]:
            lines.append(f"  {c['strategy']}: {c['old_tier']} -> {c['new_tier']}")
    else:
        lines.append("No tier changes in last 24h")

    return "\n".join(lines)


def send_to_discord(report: str):
    """Post report to Discord with retry."""
    if not DISCORD_HEALTH_WEBHOOK:
        print("No DISCORD_HEALTH_WEBHOOK set, skipping Discord send")
        print(report)
        return

    payload = {
        "content": f"```\n{report}\n```",
        "username": "Strategy Health Monitor",
    }

    for attempt in range(3):
        try:
            resp = requests.post(DISCORD_HEALTH_WEBHOOK, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                print(f"Discord report sent successfully (attempt {attempt + 1})")
                return
            if resp.status_code == 429:  # rate limited
                retry_after = resp.json().get("retry_after", 5)
                print(f"Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            print(f"Discord returned {resp.status_code}: {resp.text[:200]}")
        except requests.RequestException as e:
            print(f"Discord send failed (attempt {attempt + 1}): {e}")

        if attempt < 2:
            time.sleep(2 ** attempt)

    print("WARNING: All Discord send attempts failed")


def main():
    print(f"Strategy Health Report -- {dt.datetime.utcnow().isoformat()}Z")

    conn = get_connection()
    tiers = fetch_health_data(conn)
    changes = fetch_tier_changes_today(conn)
    conn.close()

    report = format_report(tiers, changes)
    print(report)
    print()
    send_to_discord(report)


if __name__ == "__main__":
    main()
