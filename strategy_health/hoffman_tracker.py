#!/usr/bin/env python3
"""
Hoffman IRB Strategy Tracker
===============================
Dedicated Discord tracker for the Inventory Retracement Bar (IRB) strategy
and its adaptive wrapper variant.

Posts to DISCORD_WEBHOOK_PAPER_TRADE (or falls back to DISCORD_HEALTH_WEBHOOK).
Tracks: irb_hoffman, adaptive_irb_hoffman, fib_rsi_divergence, protective_momentum

Run:  python -m strategy_health.hoffman_tracker
"""

import datetime as dt
import json
import os
import time

import pymysql
import requests

from strategy_health.config import (
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB,
    DISCORD_HEALTH_WEBHOOK,
)

DISCORD_WEBHOOK_HOFFMAN = os.environ.get(
    "DISCORD_WEBHOOK_PAPER_TRADE",
    os.environ.get("DISCORD_WEBHOOK_PAPERTRADE", DISCORD_HEALTH_WEBHOOK),
)

# Strategies from the Gemini Deep Research Championship report
GEMINI_STRATEGIES = [
    "irb_hoffman",
    "adaptive_irb_hoffman",
    "fib_rsi_divergence",
    "protective_momentum",
    "hoffman_irb_1h",
    "hoffman_irb_2h",
    "hoffman_irb_4h",
    "hoffman_adaptive_atr",
    "hoffman_kalman_trend",
    "hoffman_trailing_atr",
    "hoffman_momentum_tp",
    "hoffman_kelly_sized",
    "hoffman_htf_confluence",
    "hoffman_45_degree",
    "hoffman_scalper_20m",
]


def get_connection():
    # Use tools.db_env.get_stocks_creds so credentials follow the 2026-05-13
    # rotation runbook (DB_PASS_STOCKS new-name -> MYSQL_PASSWORD legacy
    # fallback). Previously this function bound to the legacy
    # strategy_health.config.MYSQL_PASSWORD module-level constant which silently
    # broke after the secret rotation. See docs/DB_ROTATION_RUNBOOK_2026-05-13.md.
    try:
        from tools.db_env import get_stocks_creds
        creds = get_stocks_creds()
        creds.setdefault("charset", "utf8mb4")
        creds.setdefault("cursorclass", pymysql.cursors.DictCursor)
        creds.setdefault("connect_timeout", 15)
        creds.setdefault("read_timeout", 30)
        return pymysql.connect(**creds)
    except Exception:
        # Fall back to the legacy path so a missing tools/db_env import does not
        # break local dev. Production credentials should always hit get_stocks_creds.
        return pymysql.connect(
            host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD,
            database=MYSQL_DB, charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=15, read_timeout=30,
        )


def fetch_gemini_strategy_metrics(conn) -> list:
    """Fetch performance metrics for all Gemini championship strategies."""
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(GEMINI_STRATEGIES))

    # Overall metrics from at_signal_outcomes
    cur.execute(f"""
        SELECT
            COALESCE(strategy, 'unknown') AS strategy,
            source_system,
            COUNT(*) AS total_trades,
            SUM(CASE WHEN outcome IN ('WIN','TP_HIT') THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN outcome IN ('LOSS','SL_HIT') THEN 1 ELSE 0 END) AS losses,
            AVG(CASE WHEN outcome IN ('WIN','TP_HIT') THEN pnl_pct END) AS avg_win_pct,
            AVG(CASE WHEN outcome IN ('LOSS','SL_HIT') THEN ABS(pnl_pct) END) AS avg_loss_pct,
            SUM(pnl_pct) AS total_pnl,
            MAX(closed_at) AS last_trade
        FROM at_signal_outcomes
        WHERE outcome IN ('WIN','TP_HIT','LOSS','SL_HIT')
          AND strategy IN ({placeholders})
        GROUP BY strategy, source_system
        ORDER BY strategy
    """, GEMINI_STRATEGIES)
    return list(cur.fetchall())


def fetch_open_picks(conn) -> list:
    """Fetch currently open picks for Gemini strategies."""
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(GEMINI_STRATEGIES))

    cur.execute(f"""
        SELECT strategy, symbol, direction, entry_price, take_profit, stop_loss,
               opened_at
        FROM at_signal_outcomes
        WHERE outcome = 'OPEN'
          AND strategy IN ({placeholders})
        ORDER BY opened_at DESC
        LIMIT 10
    """, GEMINI_STRATEGIES)
    return list(cur.fetchall())


def fetch_recent_trades(conn, limit: int = 5) -> list:
    """Fetch most recent closed trades for Gemini strategies."""
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(GEMINI_STRATEGIES))

    cur.execute(f"""
        SELECT strategy, symbol, direction, outcome, pnl_pct, closed_at
        FROM at_signal_outcomes
        WHERE outcome IN ('WIN','TP_HIT','LOSS','SL_HIT')
          AND strategy IN ({placeholders})
        ORDER BY closed_at DESC
        LIMIT %s
    """, GEMINI_STRATEGIES + [limit])
    return list(cur.fetchall())


def fetch_health_tier(conn) -> dict:
    """Fetch current health tier for each Gemini strategy."""
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(GEMINI_STRATEGIES))

    cur.execute(f"""
        SELECT strategy, tier, tier_reason, fees_adj_expect, last_evaluated
        FROM strategy_health
        WHERE strategy IN ({placeholders})
    """, GEMINI_STRATEGIES)

    return {row["strategy"]: row for row in cur.fetchall()}


def format_hoffman_report(metrics: list, open_picks: list,
                          recent: list, tiers: dict) -> str:
    """Format the Hoffman tracker report for Discord."""
    now = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"GEMINI CHAMPIONSHIP STRATEGY TRACKER",
        f"Report: {now}",
        "=" * 44,
        "",
    ]

    # Per-strategy metrics
    if metrics:
        lines.append("PERFORMANCE BY STRATEGY")
        lines.append(f"{'Strategy':<24s} {'W':>3s} {'L':>3s} {'WR':>6s} {'Avg$':>7s} {'PF':>5s} {'Tier':>8s}")
        lines.append("-" * 60)

        for row in metrics:
            strat = row["strategy"][:24]
            wins = int(row["wins"] or 0)
            losses = int(row["losses"] or 0)
            total = wins + losses
            wr = f"{wins/total*100:.0f}%" if total > 0 else "N/A"

            avg_win = float(row["avg_win_pct"] or 0)
            avg_loss = float(row["avg_loss_pct"] or 0)
            if losses > 0 and avg_loss > 0:
                pf = f"{(wins * avg_win) / (losses * avg_loss):.1f}"
            else:
                pf = "inf"

            total_pnl = float(row["total_pnl"] or 0)
            tier_info = tiers.get(row["strategy"], {})
            tier = tier_info.get("tier", "NEW") if tier_info else "NEW"

            lines.append(
                f"{strat:<24s} {wins:>3d} {losses:>3d} {wr:>6s} "
                f"{total_pnl:>+6.1f}% {pf:>5s} {tier:>8s}"
            )
        lines.append("")
    else:
        lines.append("No closed trades yet — strategies are collecting data")
        lines.append("")

    # IRB Hoffman spotlight
    irb_data = [m for m in metrics if m["strategy"] == "irb_hoffman"]
    if irb_data:
        m = irb_data[0]
        wins = int(m["wins"] or 0)
        losses = int(m["losses"] or 0)
        total = wins + losses
        lines.append("IRB HOFFMAN SPOTLIGHT")
        lines.append(f"  Trades: {total} ({wins}W / {losses}L)")
        lines.append(f"  Total PnL: {float(m['total_pnl'] or 0):+.2f}%")
        if m["last_trade"]:
            lines.append(f"  Last trade: {m['last_trade']}")
        lines.append("")

    # Open positions
    if open_picks:
        lines.append(f"OPEN POSITIONS ({len(open_picks)})")
        for p in open_picks:
            entry = float(p.get("entry_price") or 0)
            lines.append(
                f"  {p['strategy'][:18]:18s} {p['symbol']:10s} "
                f"{p['direction']:5s} entry=${entry:.2f}"
            )
        lines.append("")

    # Recent trades
    if recent:
        lines.append(f"LAST {len(recent)} TRADES")
        for t in recent:
            icon = "W" if t["outcome"] in ("WIN", "TP_HIT") else "L"
            pnl = float(t["pnl_pct"] or 0)
            lines.append(
                f"  [{icon}] {t['strategy'][:18]:18s} {t['symbol']:10s} "
                f"{pnl:>+5.1f}%"
            )
        lines.append("")

    # Source attribution
    lines.append("Source: Gemini Deep Research Report (Mar 2026)")
    lines.append("Rob Hoffman 23x Champion | Bellet WCTC 2025")
    lines.append("Triton Quant | Lake Forest | Quant League")

    return "\n".join(lines)


def send_to_discord(report: str):
    """Post report to Discord."""
    webhook = DISCORD_WEBHOOK_HOFFMAN
    if not webhook:
        print("No DISCORD_WEBHOOK_HOFFMAN or DISCORD_HEALTH_WEBHOOK set")
        print(report)
        return

    payload = {
        "content": f"```\n{report}\n```",
        "username": "Hoffman IRB Tracker",
    }

    for attempt in range(3):
        try:
            resp = requests.post(webhook, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                print(f"Hoffman tracker posted to Discord (attempt {attempt + 1})")
                return
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 5)
                time.sleep(retry_after)
                continue
            print(f"Discord returned {resp.status_code}: {resp.text[:200]}")
        except requests.RequestException as e:
            print(f"Discord send failed (attempt {attempt + 1}): {e}")
        if attempt < 2:
            time.sleep(2 ** attempt)

    print("WARNING: All Discord send attempts failed")


def main():
    print(f"Hoffman IRB Strategy Tracker — {dt.datetime.utcnow().isoformat()}Z")

    conn = get_connection()

    metrics = fetch_gemini_strategy_metrics(conn)
    open_picks = fetch_open_picks(conn)
    recent = fetch_recent_trades(conn, limit=5)
    tiers = fetch_health_tier(conn)

    conn.close()

    report = format_hoffman_report(metrics, open_picks, recent, tiers)
    print(report)
    print()
    send_to_discord(report)


if __name__ == "__main__":
    main()
