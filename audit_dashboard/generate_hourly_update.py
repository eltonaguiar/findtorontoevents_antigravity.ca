#!/usr/bin/env python3
"""
Generate hourly portfolio update for updates/index.html living entry.
Reads current state, generates scoreboard + integrity report, and patches
the living entry with a new timestamped sub-entry at the top.
"""
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone, timedelta

log = logging.getLogger("generate_hourly_update")
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)

STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "claudes_test_state.json")
UPDATES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "updates", "index.html")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "data", "integrity_report.json")
LAST_RUN_MARKER = os.path.join(os.path.dirname(__file__), "data", "hourly_update_last_run.json")
STALE_THRESHOLD_HOURS = 2

# Optional Healthchecks.io dead-man's-switch. If HEALTHCHECKS_URL env var is
# set (typically a unique ping URL like https://hc-ping.com/<uuid>), the
# script pings it on successful completion. If the ping is missed for >1h
# (plus grace period), Healthchecks.io fires an external alert — catches
# the class of failures the internal staleness marker cannot (whole-machine
# crash, workflow disabled, etc.). No-op when the env var is unset, so this
# change is backward-compatible with any existing caller.
HEALTHCHECKS_URL_ENV = "HEALTHCHECKS_URL"
HEALTHCHECKS_PING_TIMEOUT_SEC = 10

EST = timezone(timedelta(hours=-4))


def load_state():
    """Load portfolio state from STATE_FILE with explicit error surface.

    Raises FileNotFoundError if the state file is absent (caller should
    decide whether to treat this as fatal or skip). Raises json.JSONDecodeError
    on malformed content — callers should log and fail loudly rather than
    silently patch an HTML update with empty/corrupt data.
    """
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        log.error("STATE_FILE missing: %s", STATE_FILE)
        raise
    except json.JSONDecodeError as e:
        log.error("STATE_FILE corrupt JSON: %s (%s)", STATE_FILE, e)
        raise


def load_integrity():
    """Load integrity report if present — non-fatal when missing or corrupt."""
    if not os.path.exists(REPORT_FILE):
        log.info("integrity report absent: %s (non-fatal)", REPORT_FILE)
        return None
    try:
        with open(REPORT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("integrity report unreadable: %s (%s) — continuing without it", REPORT_FILE, e)
        return None


# =========================================================================
# Quant metrics: expectancy, profit factor, staleness marker
# =========================================================================

def _trade_pnl_pct(trade):
    """Extract pnl as percentage — safe-default 0 when missing or unparseable."""
    val = trade.get("pnl_pct")
    if val is None:
        val = trade.get("pnl")
    try:
        return float(val) if val is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def compute_portfolio_stats(state):
    """Per-portfolio expectancy + profit factor.

    Returns dict of {portfolio_id: {wins, losses, n, avg_win, avg_loss, wr,
    expectancy, profit_factor, gross_win, gross_loss}}. profit_factor is None
    when gross_loss is zero (PF is mathematically undefined with no losses).
    """
    stats = {}
    for pid, p in state.items():
        wins_pnl = []
        losses_pnl = []
        for trade in p.get("closed", []) or []:
            pnl = _trade_pnl_pct(trade)
            if pnl > 0:
                wins_pnl.append(pnl)
            elif pnl < 0:
                losses_pnl.append(pnl)
        n = len(wins_pnl) + len(losses_pnl)
        wins = len(wins_pnl)
        losses = len(losses_pnl)
        avg_win = (sum(wins_pnl) / wins) if wins else 0.0
        avg_loss = (sum(losses_pnl) / losses) if losses else 0.0  # negative
        wr = wins / n if n else 0.0
        # expectancy = WR*avg_win + (1-WR)*avg_loss (avg_loss is negative)
        expectancy = wr * avg_win + (1 - wr) * avg_loss
        gross_win = sum(wins_pnl)
        gross_loss = abs(sum(losses_pnl))
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else None
        stats[pid] = {
            "wins": wins,
            "losses": losses,
            "n": n,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "wr": wr,
            "expectancy": expectancy,
            "gross_win": gross_win,
            "gross_loss": gross_loss,
            "profit_factor": profit_factor,
        }
    return stats


def compute_overall_stats(portfolio_stats):
    """Aggregate per-portfolio stats into system-wide expectancy + PF."""
    total_wins = sum(s["wins"] for s in portfolio_stats.values())
    total_losses = sum(s["losses"] for s in portfolio_stats.values())
    total_n = total_wins + total_losses
    total_gross_win = sum(s["gross_win"] for s in portfolio_stats.values())
    total_gross_loss = sum(s["gross_loss"] for s in portfolio_stats.values())
    avg_win = (total_gross_win / total_wins) if total_wins else 0.0
    avg_loss = -(total_gross_loss / total_losses) if total_losses else 0.0
    wr = (total_wins / total_n) if total_n else 0.0
    expectancy = wr * avg_win + (1 - wr) * avg_loss
    pf = (total_gross_win / total_gross_loss) if total_gross_loss > 0 else None
    return {
        "wins": total_wins,
        "losses": total_losses,
        "n": total_n,
        "wr": wr,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "gross_win": total_gross_win,
        "gross_loss": total_gross_loss,
        "profit_factor": pf,
    }


def write_last_run_marker(now=None):
    """Write the current UTC timestamp to LAST_RUN_MARKER for staleness checks."""
    ts = (now or datetime.now(timezone.utc)).isoformat()
    os.makedirs(os.path.dirname(LAST_RUN_MARKER), exist_ok=True)
    with open(LAST_RUN_MARKER, "w", encoding="utf-8") as f:
        json.dump({"last_run": ts}, f)
    log.info("wrote last-run marker: %s", ts)


def read_last_run_marker():
    """Read the last-run timestamp from LAST_RUN_MARKER, or None if missing/corrupt."""
    if not os.path.exists(LAST_RUN_MARKER):
        return None
    try:
        with open(LAST_RUN_MARKER, encoding="utf-8") as f:
            data = json.load(f)
        return datetime.fromisoformat(data["last_run"])
    except Exception as e:
        log.warning("last-run marker unreadable: %s", e)
        return None


def check_staleness(now=None):
    """Return (is_stale, age_hours, message) for the last successful run.

    Missing marker is treated as first-run and NOT stale, to avoid noise on
    fresh deployments. Stale only when a prior marker exists and age exceeds
    STALE_THRESHOLD_HOURS.
    """
    last = read_last_run_marker()
    now = now or datetime.now(timezone.utc)
    if last is None:
        return False, None, "no prior run marker (first run)"
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    age_hours = (now - last).total_seconds() / 3600.0
    if age_hours > STALE_THRESHOLD_HOURS:
        return True, age_hours, (
            f"STALE pipeline: last run {age_hours:.1f}h ago "
            f"(threshold {STALE_THRESHOLD_HOURS}h)"
        )
    return False, age_hours, f"last run {age_hours:.1f}h ago (fresh)"


def ping_healthchecks(url=None, timeout=HEALTHCHECKS_PING_TIMEOUT_SEC):
    """Fire the Healthchecks.io dead-man's-switch ping.

    No-op when `url` is falsy (read from HEALTHCHECKS_URL env var by default).
    Non-raising: any HTTP / network failure is logged and swallowed so the
    generator's success status is NOT blocked by monitoring-service outages.

    Uses urllib from the stdlib so this module does not grow a new runtime
    dependency on `requests`. Returns True on 200/201, False otherwise.
    """
    if url is None:
        url = os.environ.get(HEALTHCHECKS_URL_ENV, "").strip()
    if not url:
        return False
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            ok = 200 <= resp.status < 300
            log.info("Healthchecks.io ping %s (status=%s)", "ok" if ok else "non-2xx", resp.status)
            return ok
    except Exception as e:
        log.warning("Healthchecks.io ping failed: %s", e)
        return False


def generate_scoreboard_html(state):
    """Generate the portfolio scoreboard table rows from live state."""
    rows = []
    portfolios = []

    for pname, p in state.items():
        init_cap = p.get("initial_capital", 10000)
        equity = p.get("equity", init_cap)
        pnl_pct = ((equity - init_cap) / init_cap * 100) if init_cap > 0 else 0
        open_count = len(p.get("positions", []))
        closed_count = len(p.get("closed", []))
        wins = p.get("wins", 0)
        losses = p.get("losses", 0)
        wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        name = p.get("name", pname.replace("_", " ").title())

        # Determine type
        ptype = "Signal"
        ptype_color = ""
        if "prop" in pname:
            ptype = "Prop"
            ptype_color = "color:#eab308"
        elif any(x in pname for x in ["deep_drawdown", "rsi_cap", "fear_greed", "relative_strength"]):
            ptype = "Deep Value"
            ptype_color = "color:#06b6d4"
        elif any(x in pname for x in ["hoffman", "htf"]):
            ptype = "HTF"
            ptype_color = "color:#f97316"
        elif any(x in pname for x in ["stock", "forex", "multi_asset"]):
            ptype = "Non-Crypto"
            ptype_color = "color:#a78bfa"

        cap_str = f"${init_cap/1000:.0f}K"
        status = "ACTIVE"
        status_color = "#22c55e"
        if open_count == 0 and closed_count == 0:
            status = "WAITING"
            status_color = "#eab308"

        portfolios.append({
            "name": name, "pname": pname, "type": ptype, "type_color": ptype_color,
            "cap": cap_str, "pnl_pct": pnl_pct, "open": open_count, "closed": closed_count,
            "wins": wins, "losses": losses, "wr": wr, "equity": equity,
            "status": status, "status_color": status_color,
        })

    # Sort by PnL descending
    portfolios.sort(key=lambda x: x["pnl_pct"], reverse=True)

    for i, p in enumerate(portfolios, 1):
        pnl_color = "#22c55e" if p["pnl_pct"] > 0 else ("#ef4444" if p["pnl_pct"] < 0 else "inherit")
        pnl_str = f"+{p['pnl_pct']:.2f}%" if p["pnl_pct"] >= 0 else f"{p['pnl_pct']:.2f}%"
        type_td = f'<td style="{p["type_color"]}">{p["type"]}</td>' if p["type_color"] else f'<td>{p["type"]}</td>'
        rows.append(
            f'          <tr><td>{i}</td><td><strong>{p["name"]}</strong></td>'
            f'{type_td}<td>{p["cap"]}</td>'
            f'<td style="color:{pnl_color}"><strong>{pnl_str}</strong></td>'
            f'<td>{p["open"]}</td><td>{p["closed"]}</td>'
            f'<td style="color:{p["status_color"]}">{p["status"]}</td></tr>'
        )

    return "\n".join(rows), portfolios


def generate_sub_entry(state, integrity):
    """Generate a new timestamped sub-entry for the living entry."""
    now = datetime.now(EST)
    ts = now.strftime("%b %d, %Y &mdash; %I:%M %p EST")

    scoreboard_rows, portfolios = generate_scoreboard_html(state)

    total_equity = sum(p["equity"] for p in portfolios)
    total_open = sum(p["open"] for p in portfolios)
    total_closed = sum(p["closed"] for p in portfolios)
    total_wins = sum(p["wins"] for p in portfolios)
    total_losses = sum(p["losses"] for p in portfolios)
    overall_wr = (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) > 0 else 0
    active_count = sum(1 for p in portfolios if p["status"] == "ACTIVE")
    waiting_count = sum(1 for p in portfolios if p["status"] == "WAITING")

    # Top 3
    top3 = portfolios[:3]
    top3_str = ", ".join(f'{p["name"]} ({p["pnl_pct"]:+.2f}%)' for p in top3)

    # Integrity status
    integrity_str = ""
    if integrity:
        s = integrity.get("summary", {})
        if s.get("critical", 0) > 0:
            integrity_str = f'<span style="color:#ef4444">INTEGRITY: {s["critical"]} CRITICAL issues found</span>'
        elif s.get("warnings", 0) > 0:
            integrity_str = f'<span style="color:#f59e0b">INTEGRITY: {s["warnings"]} warnings (0 critical)</span>'
        else:
            integrity_str = f'<span style="color:#22c55e">INTEGRITY: All {s.get("total_portfolios", 26)} portfolios CLEAN</span>'

    html = f'''        <h4 style="color:#a78bfa; border-bottom: 1px solid #2a2a3e; padding-bottom: 4px;">
          {ts} | Hourly Portfolio Update
        </h4>
        <p><strong>{active_count} active, {waiting_count} waiting</strong> | {total_open} open positions | {total_closed} closed trades | W/L: {total_wins}/{total_losses} ({overall_wr:.0f}% WR) | {integrity_str}</p>
        <p><strong>Top 3:</strong> {top3_str}</p>
        <table style="width:100%; border-collapse:collapse; margin:8px 0; font-size:0.88em;">
          <tr style="border-bottom:1px solid #2a2a3e;">
            <th style="text-align:left; padding:3px;">#</th>
            <th style="text-align:left; padding:3px;">Portfolio</th>
            <th style="text-align:left; padding:3px;">Type</th>
            <th style="text-align:left; padding:3px;">Capital</th>
            <th style="text-align:left; padding:3px;">P&amp;L%</th>
            <th style="text-align:left; padding:3px;">Open</th>
            <th style="text-align:left; padding:3px;">Closed</th>
            <th style="text-align:left; padding:3px;">Status</th>
          </tr>
{scoreboard_rows}
        </table>
        <p style="font-size:0.85em; color:#6b7280"><em>Total portfolio equity: ${total_equity:,.2f}. See <a href="https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit_dashboard/portfolio_history.html" target="_blank">full audit trail</a> for individual trade details.</em></p>
        <hr style="border-color:#2a2a3e; margin: 12px 0;">'''

    return html


def update_living_entry(new_sub_entry):
    """Insert new sub-entry at the top of the living entry, replacing the previous hourly update if recent."""
    with open(UPDATES_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the insertion point: after the TIMESTAMPED SUB-ENTRIES comment
    marker = "<!-- TIMESTAMPED SUB-ENTRIES (newest first)                 -->"
    closing = "<!-- ═══════════════════════════════════════════════════════ -->"

    idx = content.find(marker)
    if idx == -1:
        print("ERROR: Could not find TIMESTAMPED SUB-ENTRIES marker in updates/index.html")
        sys.exit(1)

    # Find the closing comment after the marker
    after_marker = content.find(closing, idx + len(marker))
    if after_marker == -1:
        print("ERROR: Could not find closing marker")
        sys.exit(1)
    insert_point = after_marker + len(closing) + 1  # +1 for newline

    # Check if the most recent entry is an "Hourly Portfolio Update" - if so, replace it
    next_hr = content.find("<hr", insert_point, insert_point + 5000)
    next_h4_after_hr = content.find("<h4", insert_point + 10, insert_point + 5000)

    existing_hourly = content[insert_point:insert_point+500]
    if "Hourly Portfolio Update" in existing_hourly:
        # Find the end of this hourly entry (the <hr> tag that closes it)
        hr_end = content.find('<hr style="border-color:#2a2a3e; margin: 12px 0;">', insert_point)
        if hr_end > 0:
            hr_end_full = hr_end + len('<hr style="border-color:#2a2a3e; margin: 12px 0;">')
            # Replace the existing hourly entry
            content = content[:insert_point] + "\n" + new_sub_entry + "\n" + content[hr_end_full:]
            print("  Replaced existing hourly entry with updated data")
        else:
            # Couldn't find the end, just insert
            content = content[:insert_point] + "\n" + new_sub_entry + "\n" + content[insert_point:]
            print("  Inserted new hourly entry")
    else:
        # No existing hourly entry, insert new one
        content = content[:insert_point] + "\n" + new_sub_entry + "\n" + content[insert_point:]
        print("  Inserted new hourly entry (first of session)")

    # Also update the scoreboard section
    content = update_scoreboard_table(content)

    # Update the date in the living entry header
    now = datetime.now(EST)
    date_str = now.strftime("%b %d, %Y")
    content = re.sub(
        r'<div class="update-date">.*?</div>',
        f'<div class="update-date">{date_str} &mdash; LIVE (updated hourly)</div>',
        content,
        count=1
    )

    with open(UPDATES_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def update_scoreboard_table(content):
    """Update the fixed scoreboard table in the living entry with current data."""
    state = load_state()
    scoreboard_rows, portfolios = generate_scoreboard_html(state)

    now = datetime.now(EST)
    ts = now.strftime("%b %d, %I:%M %p EST")

    # Find and replace the scoreboard header
    old_header_pattern = r'<h4>Portfolio Scoreboard \(26 portfolios.*?\)</h4>'
    new_header = f'<h4>Portfolio Scoreboard (26 portfolios &mdash; Updated {ts})</h4>'
    content = re.sub(old_header_pattern, new_header, content)

    # Find and replace the scoreboard table body (between first <tr> headers and </table>)
    scoreboard_marker = "Portfolio Scoreboard"
    sb_idx = content.find(scoreboard_marker)
    if sb_idx == -1:
        return content

    # Find the table after the scoreboard header
    table_start = content.find("<table>", sb_idx)
    table_end = content.find("</table>", table_start)
    if table_start == -1 or table_end == -1:
        return content

    # Build new table content
    new_table = f"""<table>
          <tr>
            <th>#</th><th>Portfolio</th><th>Type</th><th>Capital</th><th>P&amp;L%</th>
            <th>Open</th><th>Closed</th><th>Status</th>
          </tr>
{scoreboard_rows}
        </table>"""

    content = content[:table_start] + new_table + content[table_end + len("</table>"):]

    # Update the honest assessment line after the scoreboard
    total_wins = sum(p["wins"] for p in portfolios)
    total_losses = sum(p["losses"] for p in portfolios)
    total_closed = sum(p["closed"] for p in portfolios)
    overall_wr = (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) > 0 else 0
    top = portfolios[0] if portfolios else None
    top_str = f'{top["name"]} leads at {top["pnl_pct"]:+.2f}%' if top else "N/A"

    return content


def main():
    print(f"\n=== HOURLY UPDATE GENERATOR — {datetime.now(EST).strftime('%b %d %I:%M %p EST')} ===\n")

    # Staleness check before doing anything — log loudly if the pipeline has
    # been silent, per feedback in FEEDBACK_DEEPSEEK_APR122026.MD ("review
    # generate_hourly_update.py for error handling and logging to diagnose
    # why it stopped").
    is_stale, age_hours, stale_msg = check_staleness()
    if is_stale:
        log.warning(stale_msg)
    else:
        log.info(stale_msg)

    try:
        state = load_state()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log.error("Cannot proceed — state load failed: %s", e)
        return 1

    integrity = load_integrity()

    # Compute and log quant metrics (not rendered into the HTML sub-entry
    # in this PR — that would require HTML schema changes. Instead they're
    # logged so they appear in the workflow logs for visibility, and
    # downstream callers / tests can import and render them.)
    portfolio_stats = compute_portfolio_stats(state)
    overall = compute_overall_stats(portfolio_stats)
    pf_str = f"{overall['profit_factor']:.2f}" if overall["profit_factor"] is not None else "N/A"
    log.info(
        "System metrics: n=%d WR=%.1f%% expectancy=%+.3f%% PF=%s gross_win=%+.2f gross_loss=%+.2f",
        overall["n"],
        overall["wr"] * 100,
        overall["expectancy"],
        pf_str,
        overall["gross_win"],
        overall["gross_loss"],
    )

    sub_entry = generate_sub_entry(state, integrity)
    update_living_entry(sub_entry)

    print(f"  Updates page patched: {UPDATES_FILE}")
    print(f"  Done.\n")

    # Record successful completion for the next run's staleness check
    write_last_run_marker()

    # External dead-man's-switch ping. Only fires when HEALTHCHECKS_URL env
    # var is set; no-op otherwise. Catches the class of failures the internal
    # staleness marker cannot (whole-machine crash, workflow disabled, etc.).
    # Must be the LAST thing the script does so we only ping on truly
    # successful completion — ping failure never blocks the return code.
    ping_healthchecks()

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
