#!/usr/bin/env python3
"""
Consolidated Performance Dashboard
===================================
Collects data from ALL live trading systems and outputs a single JSON summary.

Usage:
    python -m consolidated_dashboard                  # JSON output + table
    python -m consolidated_dashboard --format html    # Also generate HTML report
    python -m consolidated_dashboard --format json    # JSON only (no table)

Run from ml_battleground/ directory:
    python -m consolidated_dashboard
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths  (all relative to repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent

SYSTEM_CONFIGS = [
    {
        "name": "KIMI Rise of the Claw",
        "type": "kimi",
        "data_file": "KIMI_RISEOFTHECLAW/data/live_signals_now.json",
        "tracker_db": "KIMI_RISEOFTHECLAW/data/signal_tracker.db",
    },
    {
        "name": "Alpha Engine",
        "type": "alpha_engine",
        "data_file": "alpha_engine/data/active_picks.json",
    },
    {
        "name": "crypto_ml_edge",
        "type": "ml_edge",
        "data_file": "crypto_ml_edge/data/active_picks.json",
    },
    {
        "name": "ML Battleground System A",
        "type": "battleground",
        "data_file": "ml_battleground/system_a_filter/data/active_picks.json",
        "closed_file": "ml_battleground/system_a_filter/data/closed_picks.json",
        "summary_file": "ml_battleground/system_a_filter/data/scan_summary.json",
    },
    {
        "name": "ML Battleground System B",
        "type": "battleground",
        "data_file": "ml_battleground/system_b_regime/data/active_picks.json",
        "closed_file": "ml_battleground/system_b_regime/data/closed_picks.json",
        "summary_file": "ml_battleground/system_b_regime/data/scan_summary.json",
    },
    {
        "name": "ML Battleground System C",
        "type": "battleground",
        "data_file": "ml_battleground/system_c_deeplearn/data/active_picks.json",
        "closed_file": "ml_battleground/system_c_deeplearn/data/closed_picks.json",
        "summary_file": "ml_battleground/system_c_deeplearn/data/scan_summary.json",
    },
    {
        "name": "ABC Forward Test",
        "type": "generic_json",
        "data_file": "ml_battleground/abc_forward_test/data/abc_results.json",
    },
    {
        "name": "Breakout Arena",
        "type": "generic_json",
        "data_file": "breakout_arena/data/arena_results.json",
    },
    {
        "name": "HMM Regime Gate Pilot",
        "type": "generic_json",
        "data_file": "ml_battleground/pilots/data/hmm_regime_gate.json",
    },
    {
        "name": "Funding Rate Carry Pilot",
        "type": "generic_json",
        "data_file": "ml_battleground/pilots/data/funding_rate_carry.json",
    },
    {
        "name": "Cross-Asset Momentum Pilot",
        "type": "generic_json",
        "data_file": "ml_battleground/pilots/data/cross_asset_momentum.json",
    },
    {
        "name": "OU Pairs Trading Pilot",
        "type": "generic_json",
        "data_file": "ml_battleground/pilots/data/ou_pairs_trading.json",
    },
]

OUTPUT_JSON = REPO_ROOT / "ml_battleground" / "data" / "consolidated_status.json"
OUTPUT_HTML = REPO_ROOT / "ml_battleground" / "data" / "consolidated_report.html"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _safe_read_json(path: Path) -> dict | list | None:
    """Read a JSON file, returning None on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _file_mtime_iso(path: Path) -> str | None:
    """Return ISO-8601 mtime of a file, or None."""
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _extract_latest_picks(picks: list, limit: int = 5) -> list[dict]:
    """Normalize a list of picks into a uniform format, returning up to *limit*."""
    out = []
    for p in picks[:limit]:
        symbol = p.get("symbol") or p.get("pair") or p.get("symbol_display") or "?"
        direction = (
            p.get("signal_type")
            or p.get("direction")
            or p.get("signal")
            or "?"
        )
        entry = p.get("entry_price") or p.get("price")
        pnl = p.get("unrealized_pnl_pct") or p.get("net_pnl_pct") or p.get("pnl_pct") or 0
        status = p.get("status") or "unknown"
        out.append({
            "symbol": symbol,
            "direction": str(direction).upper(),
            "entry_price": entry,
            "current_pnl": round(float(pnl), 4) if pnl is not None else None,
            "status": status,
        })
    return out


def _win_rate(picks: list) -> float | None:
    """Compute win-rate from a list of closed picks."""
    closed = [p for p in picks if p.get("exit_reason") or p.get("closed_at") or p.get("net_pnl_pct") is not None]
    if not closed:
        return None
    wins = sum(1 for p in closed if (p.get("net_pnl_pct") or p.get("gross_pnl_pct") or 0) > 0)
    return round(wins / len(closed) * 100, 1)


def _overall_pnl(picks: list) -> float | None:
    """Sum net P&L across picks."""
    vals = [p.get("net_pnl_pct") or p.get("gross_pnl_pct") or p.get("unrealized_pnl_pct") for p in picks]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return round(sum(float(v) for v in vals), 4)


# ---------------------------------------------------------------------------
# Per-system collectors
# ---------------------------------------------------------------------------

def _collect_kimi(cfg: dict) -> dict:
    """Collect from KIMI Rise of the Claw (JSON + SQLite)."""
    data_path = REPO_ROOT / cfg["data_file"]
    db_path = REPO_ROOT / cfg["tracker_db"]
    result = _base_result(cfg["name"])

    raw = _safe_read_json(data_path)
    if raw is None:
        result["status"] = "no_data"
        return result

    result["status"] = "active"
    result["last_updated"] = raw.get("generated_at") or _file_mtime_iso(data_path)

    # Combine crypto + forex signals
    all_signals = raw.get("crypto_signals", []) + raw.get("forex_signals", [])
    result["active_picks"] = len(all_signals)
    result["latest_picks"] = _extract_latest_picks(all_signals)

    # Query SQLite tracker for closed picks stats
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM tracked_signals WHERE status != 'OPEN'")
            closed_count = cur.fetchone()[0]
            result["closed_picks"] = closed_count

            cur.execute("SELECT COUNT(*) FROM tracked_signals WHERE status != 'OPEN' AND pnl_pct > 0")
            wins = cur.fetchone()[0]
            if closed_count > 0:
                result["win_rate"] = round(wins / closed_count * 100, 1)

            cur.execute("SELECT COALESCE(SUM(pnl_pct), 0) FROM tracked_signals WHERE status != 'OPEN'")
            result["overall_pnl"] = round(cur.fetchone()[0], 4)

            conn.close()
        except Exception:
            pass  # SQLite errors are non-fatal

    return result


def _collect_alpha_engine(cfg: dict) -> dict:
    """Collect from Alpha Engine (active_picks.json has nested 'picks' key or is a list)."""
    data_path = REPO_ROOT / cfg["data_file"]
    result = _base_result(cfg["name"])

    raw = _safe_read_json(data_path)
    if raw is None:
        result["status"] = "no_data"
        return result

    result["status"] = "active"

    # Alpha engine JSON has {generated_at, picks: [...]} or may be a list
    if isinstance(raw, dict):
        result["last_updated"] = raw.get("generated_at") or _file_mtime_iso(data_path)
        picks = raw.get("picks", [])
    else:
        result["last_updated"] = _file_mtime_iso(data_path)
        picks = raw

    active = [p for p in picks if str(p.get("status", "")).lower() in ("active", "open")]
    closed = [p for p in picks if str(p.get("status", "")).lower() not in ("active", "open", "")]

    result["active_picks"] = len(active)
    result["closed_picks"] = len(closed)
    result["win_rate"] = _win_rate(closed)
    result["overall_pnl"] = _overall_pnl(picks)
    result["latest_picks"] = _extract_latest_picks(active or picks)

    return result


def _collect_ml_edge(cfg: dict) -> dict:
    """Collect from crypto_ml_edge."""
    data_path = REPO_ROOT / cfg["data_file"]
    result = _base_result(cfg["name"])

    raw = _safe_read_json(data_path)
    if raw is None:
        result["status"] = "no_data"
        return result

    result["status"] = "active"

    if isinstance(raw, dict):
        result["last_updated"] = raw.get("generated_at") or _file_mtime_iso(data_path)
        picks = raw.get("picks", [])
    else:
        result["last_updated"] = _file_mtime_iso(data_path)
        picks = raw

    active = [p for p in picks if str(p.get("status", "")).lower() in ("active", "open")]
    closed = [p for p in picks if str(p.get("status", "")).lower() not in ("active", "open", "")]

    result["active_picks"] = len(active)
    result["closed_picks"] = len(closed)
    result["win_rate"] = _win_rate(closed)
    result["overall_pnl"] = _overall_pnl(picks)
    result["latest_picks"] = _extract_latest_picks(active or picks)

    return result


def _collect_battleground(cfg: dict) -> dict:
    """Collect from ML Battleground systems (active + closed + scan_summary)."""
    data_path = REPO_ROOT / cfg["data_file"]
    closed_path = REPO_ROOT / cfg.get("closed_file", "")
    summary_path = REPO_ROOT / cfg.get("summary_file", "")
    result = _base_result(cfg["name"])

    active_raw = _safe_read_json(data_path)
    closed_raw = _safe_read_json(closed_path) if closed_path.name else None
    summary_raw = _safe_read_json(summary_path) if summary_path.name else None

    if active_raw is None and summary_raw is None:
        result["status"] = "no_data"
        return result

    result["status"] = "active"

    # Prefer scan_summary timestamp
    if summary_raw and isinstance(summary_raw, dict):
        result["last_updated"] = summary_raw.get("timestamp") or _file_mtime_iso(summary_path)
        result["win_rate"] = (
            round(summary_raw["win_rate"] * 100, 1)
            if summary_raw.get("win_rate") is not None
            else None
        )
        if summary_raw.get("sharpe") is not None:
            result["sharpe"] = round(summary_raw["sharpe"], 2)
        if summary_raw.get("drawdown") is not None:
            result["max_drawdown"] = round(summary_raw["drawdown"] * 100, 2)
        result["fear_greed"] = summary_raw.get("fear_greed")
        result["market_health"] = summary_raw.get("market_health")
    else:
        result["last_updated"] = _file_mtime_iso(data_path)

    active_picks = active_raw if isinstance(active_raw, list) else []
    closed_picks = closed_raw if isinstance(closed_raw, list) else []

    result["active_picks"] = len(active_picks)
    result["closed_picks"] = len(closed_picks)
    if not result.get("win_rate") and closed_picks:
        result["win_rate"] = _win_rate(closed_picks)
    result["overall_pnl"] = _overall_pnl(closed_picks)
    result["latest_picks"] = _extract_latest_picks(active_picks or closed_picks)

    return result


def _collect_generic(cfg: dict) -> dict:
    """Collect from a generic JSON file (pilots, arena, forward test)."""
    data_path = REPO_ROOT / cfg["data_file"]
    result = _base_result(cfg["name"])

    raw = _safe_read_json(data_path)
    if raw is None:
        result["status"] = "no_data"
        return result

    result["status"] = "active"
    result["last_updated"] = _file_mtime_iso(data_path)

    # Attempt to parse various shapes
    if isinstance(raw, dict):
        # Try common keys
        picks = (
            raw.get("picks")
            or raw.get("signals")
            or raw.get("results")
            or raw.get("trades")
            or []
        )
        result["last_updated"] = (
            raw.get("generated_at")
            or raw.get("timestamp")
            or raw.get("last_updated")
            or result["last_updated"]
        )
        # Top-level stats
        if raw.get("win_rate") is not None:
            wr = raw["win_rate"]
            result["win_rate"] = round(wr * 100, 1) if wr <= 1 else round(wr, 1)
        if raw.get("total_pnl") is not None:
            result["overall_pnl"] = round(raw["total_pnl"], 4)
        if raw.get("active_count") is not None:
            result["active_picks"] = raw["active_count"]
        if raw.get("closed_count") is not None:
            result["closed_picks"] = raw["closed_count"]
    elif isinstance(raw, list):
        picks = raw
    else:
        picks = []

    if isinstance(picks, list):
        if result["active_picks"] is None:
            active = [p for p in picks if str(p.get("status", "")).lower() in ("active", "open")]
            result["active_picks"] = len(active) if active else len(picks)
        if result["closed_picks"] is None:
            closed = [p for p in picks if str(p.get("status", "")).lower() not in ("active", "open", "")]
            result["closed_picks"] = len(closed)
        if result["win_rate"] is None:
            result["win_rate"] = _win_rate(picks)
        if result["overall_pnl"] is None:
            result["overall_pnl"] = _overall_pnl(picks)
        result["latest_picks"] = _extract_latest_picks(picks)

    return result


# ---------------------------------------------------------------------------
# Base template
# ---------------------------------------------------------------------------

def _base_result(name: str) -> dict:
    return {
        "name": name,
        "status": "no_data",
        "last_updated": None,
        "active_picks": None,
        "closed_picks": None,
        "win_rate": None,
        "overall_pnl": None,
        "latest_picks": [],
    }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

COLLECTORS = {
    "kimi": _collect_kimi,
    "alpha_engine": _collect_alpha_engine,
    "ml_edge": _collect_ml_edge,
    "battleground": _collect_battleground,
    "generic_json": _collect_generic,
}


def collect_all() -> dict:
    """Run all collectors and return the consolidated summary."""
    systems = []
    for cfg in SYSTEM_CONFIGS:
        collector = COLLECTORS[cfg["type"]]
        try:
            systems.append(collector(cfg))
        except Exception as exc:
            entry = _base_result(cfg["name"])
            entry["status"] = "error"
            entry["error"] = str(exc)
            systems.append(entry)

    # Aggregate totals
    total_active = sum(s["active_picks"] or 0 for s in systems)
    total_closed = sum(s["closed_picks"] or 0 for s in systems)
    active_systems = sum(1 for s in systems if s["status"] == "active")
    wr_vals = [s["win_rate"] for s in systems if s["win_rate"] is not None]
    avg_wr = round(sum(wr_vals) / len(wr_vals), 1) if wr_vals else None
    total_pnl_vals = [s["overall_pnl"] for s in systems if s["overall_pnl"] is not None]
    total_pnl = round(sum(total_pnl_vals), 4) if total_pnl_vals else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_systems": len(systems),
        "active_systems": active_systems,
        "total_active_picks": total_active,
        "total_closed_picks": total_closed,
        "average_win_rate": avg_wr,
        "total_pnl": total_pnl,
        "systems": systems,
    }


# ---------------------------------------------------------------------------
# Output: formatted table
# ---------------------------------------------------------------------------

def print_table(data: dict) -> None:
    """Print a formatted summary table to stdout."""
    print()
    print("=" * 100)
    print(f"  CONSOLIDATED TRADING DASHBOARD  |  {data['generated_at']}")
    print(f"  Systems: {data['active_systems']}/{data['total_systems']} active  |"
          f"  Picks: {data['total_active_picks']} active / {data['total_closed_picks']} closed  |"
          f"  Avg WR: {data['average_win_rate'] or 'N/A'}%  |"
          f"  Total P&L: {data['total_pnl'] or 'N/A'}%")
    print("=" * 100)
    print()

    hdr = f"{'System':<30} {'Status':<9} {'Active':>6} {'Closed':>6} {'WR%':>7} {'P&L%':>9} {'Last Updated':<26}"
    print(hdr)
    print("-" * len(hdr))

    for s in data["systems"]:
        name = s["name"][:29]
        status = s["status"]
        active = s["active_picks"] if s["active_picks"] is not None else "-"
        closed = s["closed_picks"] if s["closed_picks"] is not None else "-"
        wr = f"{s['win_rate']}%" if s["win_rate"] is not None else "-"
        pnl = f"{s['overall_pnl']}%" if s["overall_pnl"] is not None else "-"
        updated = (s["last_updated"] or "-")[:25]

        print(f"{name:<30} {status:<9} {str(active):>6} {str(closed):>6} {wr:>7} {pnl:>9} {updated:<26}")

    print()

    # Latest picks per active system
    for s in data["systems"]:
        if s["latest_picks"]:
            print(f"  >> {s['name']} latest picks:")
            for p in s["latest_picks"]:
                sym = p["symbol"]
                d = p["direction"]
                entry = p["entry_price"] if p["entry_price"] is not None else "N/A"
                cpnl = f"{p['current_pnl']:.2f}%" if p["current_pnl"] is not None else "N/A"
                st = p["status"]
                print(f"     {sym:<14} {d:<6} entry={str(entry):<12} pnl={cpnl:<10} status={st}")
            print()


# ---------------------------------------------------------------------------
# Output: HTML report
# ---------------------------------------------------------------------------

def generate_html(data: dict, output_path: Path) -> None:
    """Generate a dark-themed HTML dashboard report."""
    rows_html = ""
    for s in data["systems"]:
        status_color = {
            "active": "#22c55e",
            "no_data": "#6b7280",
            "error": "#ef4444",
        }.get(s["status"], "#6b7280")

        active = s["active_picks"] if s["active_picks"] is not None else "-"
        closed = s["closed_picks"] if s["closed_picks"] is not None else "-"
        wr = f"{s['win_rate']}%" if s["win_rate"] is not None else "-"
        pnl_val = s["overall_pnl"]
        if pnl_val is not None:
            pnl_color = "#22c55e" if pnl_val >= 0 else "#ef4444"
            pnl = f"{pnl_val}%"
        else:
            pnl_color = "#6b7280"
            pnl = "-"
        updated = (s["last_updated"] or "-")[:19]

        # Build picks sub-rows
        picks_html = ""
        if s["latest_picks"]:
            picks_html = '<div class="picks">'
            for p in s["latest_picks"]:
                cpnl = p["current_pnl"]
                cpnl_str = f"{cpnl:.2f}%" if cpnl is not None else "N/A"
                cpnl_color = "#22c55e" if cpnl is not None and cpnl >= 0 else "#ef4444" if cpnl is not None else "#6b7280"
                picks_html += (
                    f'<span class="pick">'
                    f'{p["symbol"]} {p["direction"]} '
                    f'<span style="color:{cpnl_color}">{cpnl_str}</span>'
                    f'</span>'
                )
            picks_html += "</div>"

        rows_html += f"""
        <tr>
            <td>{s['name']}</td>
            <td><span class="status-dot" style="background:{status_color}"></span>{s['status']}</td>
            <td class="num">{active}</td>
            <td class="num">{closed}</td>
            <td class="num">{wr}</td>
            <td class="num" style="color:{pnl_color}">{pnl}</td>
            <td class="ts">{updated}</td>
        </tr>"""
        if picks_html:
            rows_html += f"""
        <tr class="picks-row">
            <td colspan="7">{picks_html}</td>
        </tr>"""

    avg_wr = f"{data['average_win_rate']}%" if data["average_win_rate"] is not None else "N/A"
    total_pnl = data["total_pnl"]
    if total_pnl is not None:
        total_pnl_color = "#22c55e" if total_pnl >= 0 else "#ef4444"
        total_pnl_str = f"{total_pnl}%"
    else:
        total_pnl_color = "#6b7280"
        total_pnl_str = "N/A"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Consolidated Trading Dashboard</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a12; color:#e2e8f0; font-family:'Segoe UI',system-ui,sans-serif; padding:24px; }}
  h1 {{ font-size:1.5rem; margin-bottom:4px; color:#f1f5f9; }}
  .subtitle {{ color:#94a3b8; font-size:0.85rem; margin-bottom:20px; }}
  .stats-bar {{ display:flex; gap:24px; margin-bottom:24px; flex-wrap:wrap; }}
  .stat {{ background:#1e1e2e; border-radius:8px; padding:14px 20px; min-width:140px; }}
  .stat .label {{ font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.05em; }}
  .stat .value {{ font-size:1.4rem; font-weight:700; margin-top:2px; }}
  table {{ width:100%; border-collapse:collapse; background:#1e1e2e; border-radius:8px; overflow:hidden; }}
  th {{ background:#16162a; text-align:left; padding:10px 14px; font-size:0.75rem;
       text-transform:uppercase; letter-spacing:0.05em; color:#94a3b8; }}
  td {{ padding:10px 14px; border-bottom:1px solid #2a2a3e; font-size:0.875rem; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  td.ts {{ font-size:0.78rem; color:#94a3b8; }}
  tr:hover {{ background:#252540; }}
  tr.picks-row:hover {{ background:transparent; }}
  tr.picks-row td {{ padding:4px 14px 10px; border-bottom:1px solid #1a1a30; }}
  .status-dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }}
  .picks {{ display:flex; gap:12px; flex-wrap:wrap; }}
  .pick {{ background:#12122a; border:1px solid #2a2a3e; border-radius:4px; padding:3px 8px;
           font-size:0.78rem; font-family:monospace; }}
  footer {{ margin-top:24px; color:#475569; font-size:0.75rem; text-align:center; }}
</style>
</head>
<body>
<h1>Consolidated Trading Dashboard</h1>
<div class="subtitle">Generated: {data['generated_at']}</div>

<div class="stats-bar">
  <div class="stat">
    <div class="label">Active Systems</div>
    <div class="value">{data['active_systems']}/{data['total_systems']}</div>
  </div>
  <div class="stat">
    <div class="label">Active Picks</div>
    <div class="value">{data['total_active_picks']}</div>
  </div>
  <div class="stat">
    <div class="label">Closed Picks</div>
    <div class="value">{data['total_closed_picks']}</div>
  </div>
  <div class="stat">
    <div class="label">Avg Win Rate</div>
    <div class="value">{avg_wr}</div>
  </div>
  <div class="stat">
    <div class="label">Total P&amp;L</div>
    <div class="value" style="color:{total_pnl_color}">{total_pnl_str}</div>
  </div>
</div>

<table>
<thead>
<tr>
  <th>System</th>
  <th>Status</th>
  <th style="text-align:right">Active</th>
  <th style="text-align:right">Closed</th>
  <th style="text-align:right">Win Rate</th>
  <th style="text-align:right">P&amp;L</th>
  <th>Last Updated</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>

<footer>ML Battleground Consolidated Dashboard &mdash; {data['total_systems']} systems monitored</footer>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML report written to: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Consolidated Trading Dashboard")
    parser.add_argument(
        "--format", choices=["table", "json", "html"], default="table",
        help="Output format (default: table = JSON file + printed table)"
    )
    args = parser.parse_args()

    data = collect_all()

    # Always write consolidated JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Consolidated JSON written to: {OUTPUT_JSON}")

    if args.format == "html":
        generate_html(data, OUTPUT_HTML)
        print_table(data)
    elif args.format == "json":
        pass  # JSON-only, no table
    else:
        print_table(data)


if __name__ == "__main__":
    main()
