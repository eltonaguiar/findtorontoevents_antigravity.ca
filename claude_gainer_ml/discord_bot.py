#!/usr/bin/env python3
"""
Claude Gainer Discord Bot — Enhanced v3.0 (Quant Lab Integration)
==================================================================
Commands:
  !refresh    — Request an on-demand scan (lock-safe, shows ETA)
  !dashboard  — Link to the live web dashboard
  !status     — Show current picks summary + next scheduled run
  !update     — Trigger dashboard update via GitHub Actions dispatch
  !fc-pro     — Show FC-CRYPTO PRO top actionable picks (all pages, no truncation)
  !superpicks — Alias for !fc-pro (unified top picks from ALL 16 systems)
  !fc-bundle  — Show top performing Bundle Babies with forward test data
  !fc-baby    — Show forward-testing baby strategies (usage: !fc-baby 2 for page 2, !fc-baby all)
  !fc-fresh   — Show active picks with live prices + Room to TP (usage: !fc-fresh 2, !fc-fresh all)

  Smart Entry Commands (NEW in v3.1):
  !bestpicks  — Top scored picks ready to buy with live prices + entry window (usage: !bestpicks 5)
  !check      — Live price check + entry window analysis (usage: !check BTC ETH SOL)

  Quant Lab Commands (NEW in v3.0):
  !edge       — Strategy edge report (expectancy, Sharpe, Kelly, verdict per strategy)
  !regime     — Market regime analysis (vol buckets, correlation, diversification score)
  !stress     — Stress test scenarios (crash/ban/freeze impact + ruin probability)
  !gems       — Hidden gem discovery (low WR + high payoff = asymmetric alpha)
  !compliance — Regulated asset screening + compliance-constrained allocation
  !alerts     — Risk alerts (Sharpe < 0.8, DD > 25%, negative Kelly)
  !walkforward — Walk-forward validation (edge persistence across time periods)
  !quant-help — Full guide to all Quant Lab commands with examples

  Spam Picks (Live Stream):
  !spam-picks  — Start 5-min pick stream (16 Correlation + 6 Leap strategies, 2hr default)
  !spam-end    — Stop the pick stream (!spam-stop, !spam-picks-end also work)
  !spam-extend — Extend by 2hr (max 8hr total)

Run with: python discord_bot.py
Requires: DISCORD_BOT_TOKEN, DISCORD_ML_CHANNEL_ID env vars
Optional: GITHUB_TOKEN (for !update dispatch)
"""

import discord
from discord.ext import commands
import asyncio
import subprocess
import sys
import json
import time
import os
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = BASE_DIR.parent  # findtorontoevents_antigravity.ca/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
TRACKER_DIR = BASE_DIR / "tracker"
LOCK_FILE = TRACKER_DIR / "refresh_lock.json"
LIVE_PICKS_FILE = TRACKER_DIR / "claude_live_picks.json"
SCAN_LOG_FILE = TRACKER_DIR / "claude_scan_log.json"
STATUS_FILE = TRACKER_DIR / "dashboard_status.json"
LIVE_SCANNER = BASE_DIR / "live_scanner.py"

DASHBOARD_URL = "https://findtorontoevents.ca/updates/antigravity-ml-gainer.html"
GITHUB_REPO = "eltonaguiar/findtorontoevents_antigravity.ca"
GITHUB_WORKFLOW = "claude-gainer-tracker.yml"

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
ML_CHANNEL_ID = int(os.environ.get("DISCORD_ML_CHANNEL_ID", 0)) or None
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Estimated scan time in seconds (adjusts based on history)
EST_SCAN_TIME = 900  # 15 minutes default

if not DISCORD_BOT_TOKEN:
    print("[ERROR] DISCORD_BOT_TOKEN env var required")
    sys.exit(1)

# Try with message_content intent first; fall back to mention-only if not enabled
intents = discord.Intents.default()
intents.message_content = True

def _make_bot(prefix='!'):
    return commands.Bot(command_prefix=prefix, intents=intents)

bot = _make_bot('!')


def get_lock_info():
    """Check if a refresh is currently in progress."""
    if not LOCK_FILE.exists():
        return None
    try:
        with open(LOCK_FILE, 'r') as f:
            lock_data = json.load(f)
        elapsed = time.time() - lock_data.get('timestamp', 0)
        if elapsed < 1200:  # 20 min max lock
            return lock_data
    except Exception:
        pass
    return None


def get_eta_string(lock_data):
    """Calculate ETA string based on lock start time."""
    elapsed = time.time() - lock_data.get('timestamp', 0)
    remaining = max(0, EST_SCAN_TIME - elapsed)
    if remaining <= 0:
        return "any moment now"
    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    if minutes > 0:
        return f"~{minutes}m {seconds}s"
    return f"~{seconds}s"


def get_picks_summary():
    """Get current picks summary for status display."""
    if not LIVE_PICKS_FILE.exists():
        return None
    try:
        with open(LIVE_PICKS_FILE) as f:
            data = json.load(f)
        picks = data.get("picks", [])
        active = [p for p in picks if p.get("status") == "ACTIVE"]
        resolved = [p for p in picks if p.get("status") != "ACTIVE"]
        tp_hits = sum(1 for p in resolved if p.get("tp1_hit") or p.get("exit_reason") == "TP1_HIT")
        sl_hits = sum(1 for p in resolved if p.get("sl_hit") or p.get("exit_reason") == "SL_HIT")
        return {
            "active": len(active),
            "resolved": len(resolved),
            "tp_hits": tp_hits,
            "sl_hits": sl_hits,
            "updated_at": data.get("updated_at", ""),
            "active_picks": active[:5],
        }
    except Exception:
        return None


def get_last_scan_time():
    """Get the last scan timestamp from scan log."""
    if not SCAN_LOG_FILE.exists():
        return None
    try:
        with open(SCAN_LOG_FILE) as f:
            logs = json.load(f)
        if logs:
            return logs[-1].get("scan_time", "")
    except Exception:
        pass
    return None


def get_next_scheduled_run():
    """Calculate next scheduled run (every 4h at :15)."""
    now = datetime.now(timezone.utc)
    hours = [1, 5, 9, 13, 17, 21]  # :15 past these hours
    for h in sorted(hours):
        candidate = now.replace(hour=h, minute=15, second=0, microsecond=0)
        if candidate > now:
            return candidate
    # Next day first run
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=1, minute=15, second=0, microsecond=0)


def update_status(status, message="", eta_seconds=0):
    """Update the dashboard status file for the web UI to read."""
    try:
        TRACKER_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "status": status,
            "message": message,
            "eta_seconds": eta_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "triggered_by": "discord_bot",
        }
        with open(STATUS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[BOT] Status update error: {e}")


@bot.command(name='refresh')
async def refresh(ctx):
    """Request an on-demand ML scan with lock safety and ETA."""
    if ML_CHANNEL_ID and ctx.channel.id != ML_CHANNEL_ID:
        await ctx.send("❌ Use this command in the ML channel only!", delete_after=10)
        return

    # Check lock
    lock_info = get_lock_info()
    if lock_info:
        eta = get_eta_string(lock_info)
        triggered_by = lock_info.get('triggered_by', 'auto_scan')
        started = datetime.fromtimestamp(lock_info['timestamp'], tz=timezone.utc).strftime('%H:%M UTC')

        embed = discord.Embed(
            title="⏳ Refresh Already In Progress",
            description=f"A scan is currently running (started **{started}** by `{triggered_by}`).",
            color=0xf59e0b,
        )
        embed.add_field(name="⏱️ ETA", value=f"**{eta}**", inline=True)
        embed.add_field(name="📊 Dashboard", value=f"[View Live]({DASHBOARD_URL})", inline=True)
        embed.set_footer(text="CLAUDE CODE ML v2.0 | The dashboard will auto-update when complete")
        await ctx.reply(embed=embed, mention_author=False)
        return

    # Start refresh
    embed_start = discord.Embed(
        title="🔄 Starting On-Demand Refresh",
        description="Scanning top 100 coins with ML ensemble prediction...",
        color=0x3b82f6,
    )
    embed_start.add_field(name="⏱️ Estimated Time", value=f"**~{EST_SCAN_TIME // 60} minutes**", inline=True)
    embed_start.add_field(name="📊 Dashboard", value=f"[Watch Live]({DASHBOARD_URL})", inline=True)
    embed_start.add_field(name="🔔 Notification", value="You'll be notified when picks are ready", inline=False)
    embed_start.set_footer(text="CLAUDE CODE ML v2.0 | Dashboard will show progress")
    msg = await ctx.reply(embed=embed_start)

    update_status("scanning", "On-demand refresh triggered via Discord", EST_SCAN_TIME)

    # Run scanner
    cmd = [sys.executable, str(LIVE_SCANNER), "--top", "100", "--max-picks", "8"]
    scan_start = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(BASE_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=1800)  # 30 min max

        elapsed = time.time() - scan_start
        elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"

        if proc.returncode == 0:
            # Success - get picks count
            summary = get_picks_summary()
            new_picks = 0
            try:
                output = stdout.decode()
                for line in output.split('\n'):
                    if 'new picks' in line.lower():
                        import re
                        m = re.search(r'(\d+)\s+new picks', line)
                        if m:
                            new_picks = int(m.group(1))
            except Exception:
                pass

            embed_done = discord.Embed(
                title="✅ Refresh Complete!",
                description=f"Scan finished in **{elapsed_str}**",
                color=0x22c55e,
            )
            embed_done.add_field(name="📈 New Picks", value=f"**{new_picks}**", inline=True)
            if summary:
                embed_done.add_field(name="📊 Active", value=f"**{summary['active']}**", inline=True)
                embed_done.add_field(name="📋 Total Resolved", value=f"**{summary['resolved']}**", inline=True)
            embed_done.add_field(name="🔗 Dashboard", value=f"[View Updated Picks]({DASHBOARD_URL})", inline=False)
            embed_done.set_footer(text="CLAUDE CODE ML v2.0 | Not financial advice")
            await ctx.reply(embed=embed_done)
            update_status("idle", f"Last refresh completed in {elapsed_str}")
        else:
            error = stderr.decode()[:800]
            embed_fail = discord.Embed(
                title="❌ Refresh Failed",
                description=f"Process exited with code {proc.returncode} after {elapsed_str}",
                color=0xef4444,
            )
            embed_fail.add_field(name="Error", value=f"```\n{error[:500]}\n```", inline=False)
            embed_fail.set_footer(text="Check logs for details")
            await ctx.reply(embed=embed_fail)
            update_status("error", f"Refresh failed: {error[:200]}")

    except asyncio.TimeoutError:
        embed_timeout = discord.Embed(
            title="⏰ Refresh Timed Out",
            description="Scan exceeded 30 minute limit. This may indicate API issues.",
            color=0xef4444,
        )
        embed_timeout.add_field(name="🔗 Dashboard", value=f"[Check Status]({DASHBOARD_URL})", inline=False)
        await ctx.reply(embed=embed_timeout)
        update_status("error", "Refresh timed out after 30 minutes")

    except Exception as e:
        await ctx.reply(f"❌ Unexpected error: {str(e)}")
        update_status("error", str(e))


@bot.command(name='dashboard')
async def dashboard(ctx):
    """Post the live dashboard link with current stats."""
    summary = get_picks_summary()
    last_scan = get_last_scan_time()
    next_run = get_next_scheduled_run()

    embed = discord.Embed(
        title="📊 Claude Code ML — Live Dashboard",
        description=f"Real-time crypto gainer predictions with tracked TP/SL outcomes.\n\n🔗 **[Open Dashboard]({DASHBOARD_URL})**",
        color=0x6366f1,
    )

    if summary:
        embed.add_field(name="📈 Active Picks", value=f"**{summary['active']}**", inline=True)
        embed.add_field(name="📋 Resolved", value=f"**{summary['resolved']}**", inline=True)
        wr = f"{summary['tp_hits']}/{summary['tp_hits'] + summary['sl_hits']}" if (summary['tp_hits'] + summary['sl_hits']) > 0 else "N/A"
        embed.add_field(name="🎯 Win Rate", value=f"**{wr}**", inline=True)

    if last_scan:
        embed.add_field(name="🕐 Last Scan", value=last_scan[:19].replace('T', ' ') + " UTC", inline=True)

    embed.add_field(name="⏭️ Next Scheduled", value=next_run.strftime('%H:%M UTC'), inline=True)
    embed.add_field(name="🔄 On-Demand", value="Type `!refresh`", inline=True)

    # Show active picks
    if summary and summary.get('active_picks'):
        picks_text = ""
        for p in summary['active_picks'][:5]:
            sym = p.get('symbol', '?')
            prob = p.get('pump_probability', 0)
            conf = p.get('confidence', 'LOW')
            picks_text += f"**{sym}** — {conf} ({prob:.0%})\n"
        if picks_text:
            embed.add_field(name="🎯 Current Picks", value=picks_text, inline=False)

    embed.set_footer(text="CLAUDE CODE - REVERSE ENGINEERED DAILY TOP GAINERS STRAT | Not financial advice")
    await ctx.send(embed=embed)


@bot.command(name='status')
async def status(ctx):
    """Show current system status including lock state and next run."""
    lock_info = get_lock_info()
    summary = get_picks_summary()
    next_run = get_next_scheduled_run()
    time_to_next = next_run - datetime.now(timezone.utc)
    minutes_until = int(time_to_next.total_seconds() // 60)

    if lock_info:
        eta = get_eta_string(lock_info)
        status_text = f"🔄 **SCANNING** — ETA: {eta}"
        status_color = 0xf59e0b
    else:
        status_text = "🟢 **IDLE** — Ready for refresh"
        status_color = 0x22c55e

    embed = discord.Embed(
        title="⚡ System Status",
        description=status_text,
        color=status_color,
    )

    if summary:
        embed.add_field(name="Active Picks", value=str(summary['active']), inline=True)
        embed.add_field(name="Resolved", value=str(summary['resolved']), inline=True)
        embed.add_field(name="TP Hits", value=str(summary['tp_hits']), inline=True)
        embed.add_field(name="SL Hits", value=str(summary['sl_hits']), inline=True)

    embed.add_field(name="⏭️ Next Auto-Run", value=f"{next_run.strftime('%H:%M UTC')} ({minutes_until}m)", inline=True)
    embed.add_field(name="📊 Dashboard", value=f"[View]({DASHBOARD_URL})", inline=True)
    embed.set_footer(text="CLAUDE CODE ML v2.0")
    await ctx.send(embed=embed)


@bot.command(name='update')
async def update_dashboard(ctx):
    """Trigger a GitHub Actions workflow dispatch to update the dashboard."""
    if ML_CHANNEL_ID and ctx.channel.id != ML_CHANNEL_ID:
        await ctx.send("❌ Use this command in the ML channel only!", delete_after=10)
        return

    if not GITHUB_TOKEN:
        embed = discord.Embed(
            title="⚠️ GitHub Token Not Configured",
            description="Cannot trigger workflow dispatch without `GITHUB_TOKEN` env var.\n\nAlternatively, use `!refresh` to run a local scan.",
            color=0xf59e0b,
        )
        await ctx.reply(embed=embed)
        return

    # Trigger GitHub Actions
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "ref": "main",
        "inputs": {"mode": "predict"},
    }

    try:
        r = requests.post(url, json=data, headers=headers, timeout=15)
        if r.status_code in (204, 200):
            embed = discord.Embed(
                title="🚀 Dashboard Update Triggered",
                description="GitHub Actions workflow dispatched successfully!",
                color=0x22c55e,
            )
            embed.add_field(name="⏱️ ETA", value="**~18-25 minutes**", inline=True)
            embed.add_field(name="📊 Dashboard", value=f"[Watch Live]({DASHBOARD_URL})", inline=True)
            embed.add_field(
                name="📝 What Happens",
                value="1️⃣ Track active TP/SL outcomes\n2️⃣ Run new ML predictions\n3️⃣ Self-improvement feedback loop\n4️⃣ Update dashboard data\n5️⃣ Send Discord notification",
                inline=False,
            )
            embed.set_footer(text="You'll receive a notification when the updated picks notification arrives")
            await ctx.reply(embed=embed)
            update_status("github_dispatch", "Dashboard update triggered via Discord !update command", 1500)
        else:
            await ctx.reply(f"❌ GitHub dispatch failed: {r.status_code}\n```\n{r.text[:300]}\n```")
    except Exception as e:
        await ctx.reply(f"❌ Error triggering workflow: {e}")


@bot.command(name='fc-pro', aliases=['fcpro', 'pro', 'superpicks', 'super'])
async def fc_pro(ctx):
    """Show FC-CRYPTO PRO top actionable picks from all trading systems."""
    FC_PRO_FILE = BASE_DIR.parent / "data" / "fc_crypto_pro_picks.json"
    FC_PRO_RAW_URL = "https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/data/fc_crypto_pro_picks.json"

    data = None
    # Try fetching latest from GitHub first (always up to date)
    try:
        resp = requests.get(FC_PRO_RAW_URL, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
    except Exception:
        pass

    # Fallback to local file
    if data is None and FC_PRO_FILE.exists():
        try:
            with open(FC_PRO_FILE) as f:
                data = json.load(f)
        except Exception:
            pass

    if data is None:
        await ctx.reply("❌ No FC-PRO data yet. Waiting for first scan cycle.")
        return

    picks = data.get("picks", [])
    generated = data.get("generated_at", "")
    system_wrs = data.get("system_wrs", {})
    filters = data.get("filters", {})

    if not picks:
        embed = discord.Embed(
            title="FC-CRYPTO PRO — No Qualifying Picks",
            description="All systems scanned. No picks pass the quality filter right now.",
            color=0x888888,
        )
        embed.set_footer(text=f"Last scan: {generated[:19].replace('T', ' ')} UTC")
        await ctx.send(embed=embed)
        return

    qualified = [f"{v['name']} ({v['wins']}W/{v['losses']}L, {v['wr']*100:.0f}%)" for v in system_wrs.values() if v.get("qualified")]

    def _fmt_price(val):
        """Format price without scientific notation."""
        if val is None or val == 0:
            return "$0"
        val = float(val)
        if val >= 1000:
            return f"${val:,.2f}"
        elif val >= 1:
            return f"${val:.4f}"
        elif val >= 0.001:
            return f"${val:.6f}"
        else:
            return f"${val:.10f}"

    def _fmt_time(iso_str):
        """Convert UTC ISO string to EST display."""
        try:
            from datetime import datetime, timezone, timedelta
            EST = timezone(timedelta(hours=-5))
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt.astimezone(EST).strftime("%b %d, %Y %I:%M %p EST")
        except Exception:
            return iso_str[:16].replace("T", " ") + " UTC"

    gen_display = _fmt_time(generated)

    # Build embeds — pack picks into pages, each under 4096 char limit
    pages = []
    current_lines = []
    current_len = 0
    MAX_DESC = 3800

    for p in picks:
        emoji = "\U0001f4c8" if p["direction"] == "LONG" else "\U0001f4c9"
        room_pct = p.get("entry_room_pct", 0)
        room_bar = "\u2588" * int(room_pct / 10) + "\u2591" * (10 - int(room_pct / 10))
        conflict_line = f"\n  \u2694\ufe0f *{p['conflict_warning']}*" if p.get("conflict_warning") else ""
        tier_badge = " \U0001f3c6" if p.get("tier") == "pro" else ""

        # System W/L
        sys_data = system_wrs.get(p.get("system_id", ""), {})
        sys_w = sys_data.get("wins", 0)
        sys_l = sys_data.get("losses", 0)
        sys_wr_str = f"{sys_w}W/{sys_l}L, {p['system_wr']}% WR"

        # Strategy W/L
        strat_w = p.get("strat_wins", 0)
        strat_l = p.get("strat_losses", 0)
        strat_total = p.get("strat_total", 0)
        strat_name = p.get("strategy", "?")[:25]
        if strat_total > 0:
            strat_wr = p.get("strat_wr", 0)
            strat_str = f"`{strat_name}` {strat_wr}% ({strat_w}W/{strat_l}L)"
        else:
            strat_str = f"`{strat_name}` *(new)*"

        line = (
            f"**{emoji} {p['symbol']}** {p['direction']} \u2014 {p['system']}{tier_badge} ({sys_wr_str})\n"
            f"  Entry: {_fmt_price(p['entry_price'])} \u2192 TP: {_fmt_price(p['tp_price'])} (+{p['tp_pct']}%)\n"
            f"  Now: {_fmt_price(p['current_price'])} | Room to TP: {room_bar} {room_pct}%\n"
            f"  SL: {_fmt_price(p['sl_price'])} (-{p['sl_pct']}%) | R:R {p['risk_reward']} | {strat_str}"
            f"{conflict_line}"
        )
        line_len = len(line) + 2
        if current_len + line_len > MAX_DESC and current_lines:
            pages.append(current_lines)
            current_lines = []
            current_len = 0
        current_lines.append(line)
        current_len += line_len

    if current_lines:
        pages.append(current_lines)

    # Send first page as reply
    first_desc = "\n\n".join(pages[0])
    embed = discord.Embed(
        title=f"🏆 FC-CRYPTO PRO v2.0 — {len(picks)} Quality Picks",
        description=first_desc[:4090],
        color=0x22c55e,  # Green — conflicts are now auto-resolved
    )
    if len(pages) > 1:
        embed.set_footer(text=f"Page 1/{len(pages)} \u2014 showing {len(pages[0])}/{len(picks)} picks")
    else:
        embed.set_footer(text=f"Showing all {len(picks)} picks | {gen_display}")
    msg = await ctx.reply(embed=embed)

    # Send remaining pages as follow-up messages
    for i, page in enumerate(pages[1:], start=2):
        desc = "\n\n".join(page)
        embed = discord.Embed(
            title=f"📋 FC-PRO v2.0 — Page {i}/{len(pages)}",
            description=desc[:4090],
            color=0x22c55e if i % 2 == 1 else 0x3b82f6,
        )
        if i == len(pages):
            # Last page — add summary footer
            min_wr = filters.get("min_system_wr", 0.5)
            summary = f"**Filters:** WR>{min_wr*100:.0f}% | Qualified: {', '.join(qualified) or 'None'}"
            embed.description = desc[:3900] + f"\n\n━━━━━━━━━━━━\n{summary}"
            embed.set_footer(text=f"FC-PRO v2.0 | Quality Gates + Auto-Resolution | {gen_display}")
        else:
            embed.set_footer(text=f"Page {i}/{len(pages)} \u2014 scroll down for more")
        await ctx.send(embed=embed)

    # Summary line
    longs = sum(1 for p in picks if p["direction"] == "LONG")
    shorts = len(picks) - longs
    resolved = sum(1 for p in picks if p.get("conflict_warning"))
    resolved_str = f"\n\u2694\ufe0f {resolved} conflicts auto-resolved (higher WR system wins)" if resolved else ""
    await ctx.send(f"\U0001f4ca **Summary:** {len(picks)} quality picks ({longs} LONG, {shorts} SHORT) from {', '.join(qualified) or 'no qualified systems'}. Data from {gen_display}.{resolved_str}")

    # ── Audit trail: show all systems and their status ──
    audit = data.get("systems_audit", {})
    if audit:
        audit_lines = ["**📋 All Systems Scanned:**"]
        for sys_id, info in audit.items():
            tier = info.get("tier", "watch")
            total = info.get("total", 0)
            w = info.get("wins", 0)
            l = info.get("losses", 0)
            wr = info.get("wr", 0)
            ml = info.get("ml", "?")
            if tier == "retired":
                icon = "⛔"
            elif tier == "demoted":
                icon = "⬇️"
            elif info.get("qualified"):
                icon = "✅"
            elif total < 3:
                icon = "🔄"
            else:
                icon = "❌"
            name = info.get("name", sys_id)
            if total > 0:
                audit_lines.append(f"{icon} **{name}** {w}W/{l}L ({wr*100:.0f}%) — {ml}")
            else:
                audit_lines.append(f"{icon} **{name}** collecting — {ml}")
        audit_lines.append("✅=qualified ❌=below WR 🔄=collecting ⬇️=demoted ⛔=retired")
        audit_text = "\n".join(audit_lines)
        audit_embed = discord.Embed(
            title=f"🔍 System Audit — {len(audit)} Systems Tracked",
            description=audit_text[:4090],
            color=0x6366f1,
        )
        audit_embed.set_footer(text=f"New systems auto-qualify at WR>50% with 3+ trades | {gen_display}")
        await ctx.send(embed=audit_embed)


# ─── !fc-bundle command ───

@bot.command(name='fc-bundle', aliases=['fcbundle', 'bundle'])
async def fc_bundle(ctx):
    """Show top performing Bundle Babies with forward test data."""
    loading = await ctx.send("Loading bundle data...")

    try:
        # Import the bundle message generator
        sys.path.insert(0, str(BASE_DIR.parent))
        from discord_bundle_baby import generate_discord_message as gen_bundle_msg
        msg = gen_bundle_msg()
    except Exception as e:
        await loading.edit(content=f"Error loading bundles: {e}")
        return

    await loading.delete()

    # Send in chunks (Discord 2000 char limit)
    while msg:
        if len(msg) <= 2000:
            await ctx.send(msg)
            break
        split = msg.rfind('\n\n', 0, 2000)
        if split == -1:
            split = msg.rfind('\n', 0, 2000)
        if split == -1:
            split = 2000
        await ctx.send(msg[:split])
        msg = msg[split:]


# ─── !fc-baby command ───
# Usage: !fc-baby        → page 1 (picks 1-10)
#        !fc-baby 2      → page 2 (picks 11-20)
#        !fc-baby all    → all picks across multiple messages

@bot.command(name='fc-baby', aliases=['fcbaby', 'baby'])
async def fc_baby(ctx, page: str = "1"):
    """Show forward-testing baby strategies. Use !fc-baby 2 for page 2, !fc-baby all for everything."""
    loading = await ctx.send(":mag: Loading baby strat data...")

    try:
        sys.path.insert(0, str(BASE_DIR.parent))
        from discord_baby_forward_test import generate_messages
        all_msgs = generate_messages()
    except Exception as e:
        await loading.edit(content=f"Error loading baby strats: {e}")
        return

    await loading.delete()

    if page.lower() == "all":
        for msg in all_msgs:
            await ctx.send(msg)
    else:
        try:
            pg = max(1, int(page))
        except ValueError:
            pg = 1
        # Each message is roughly one "page" — show requested page
        total_pages = len(all_msgs)
        if pg > total_pages:
            await ctx.send(f"Page {pg} doesn't exist. There are {total_pages} page(s). Use `!fc-baby all` for everything.")
            return
        await ctx.send(all_msgs[pg - 1])
        if total_pages > 1:
            await ctx.send(f"*Page {pg}/{total_pages} — use `!fc-baby {pg+1 if pg < total_pages else 'all'}` for more*")


# ─── !fc-fresh command ───
# Usage: !fc-fresh       → page 1
#        !fc-fresh 2     → page 2
#        !fc-fresh all   → all picks

@bot.command(name='fc-fresh', aliases=['fcfresh', 'fresh', 'freshpicks'])
async def fc_fresh(ctx, page: str = "1"):
    """Show active baby-bundle picks with live prices + Room to TP. Use !fc-fresh 2 for page 2."""
    loading = await ctx.send(":mag: Loading freshpicks...")

    try:
        sys.path.insert(0, str(BASE_DIR.parent))
        from discord_freshpicks_baby import generate_plain_messages
        all_msgs = generate_plain_messages()
    except Exception as e:
        await loading.edit(content=f"Error loading freshpicks: {e}")
        return

    await loading.delete()

    if page.lower() == "all":
        for msg in all_msgs:
            await ctx.send(msg)
    else:
        try:
            pg = max(1, int(page))
        except ValueError:
            pg = 1
        total_pages = len(all_msgs)
        if pg > total_pages:
            await ctx.send(f"Page {pg} doesn't exist. There are {total_pages} page(s). Use `!fc-fresh all` for everything.")
            return
        await ctx.send(all_msgs[pg - 1])
        if total_pages > 1:
            await ctx.send(f"*Page {pg}/{total_pages} — use `!fc-fresh {pg+1 if pg < total_pages else 'all'}` for more*")


# ─────────────────────────────────────────────────────────────────
# Quant Lab Commands (v3.0)
# ─────────────────────────────────────────────────────────────────

QUANT_LAB_DIR = BASE_DIR.parent / "quant_lab"


def _load_quant_module(module_name):
    """Safely import a quant_lab module."""
    sys.path.insert(0, str(BASE_DIR.parent))
    sys.path.insert(0, str(QUANT_LAB_DIR))
    import importlib
    return importlib.import_module(f"quant_lab.{module_name}")


ALPHA_DASHBOARD_URL = "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/"


def _to_est(iso_str):
    """Convert an ISO timestamp string to EST display string."""
    if not iso_str:
        return "?"
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        est = dt.astimezone(timezone(timedelta(hours=-5)))
        return est.strftime("%b %d %I:%M%p EST")
    except (ValueError, TypeError):
        return iso_str[:16] if len(iso_str) > 16 else iso_str


@bot.command(name='edge', aliases=['kpi', 'expectancy'])
async def quant_edge(ctx):
    """Strategy edge report — expectancy, Sharpe, Kelly, verdict per strategy."""
    loading = await ctx.send("📊 Computing KPIs across all strategies...")

    try:
        kpi_mod = _load_quant_module("kpi_engine")
        results = kpi_mod.compute_all_kpis(min_trades=2)
    except Exception as e:
        await loading.edit(content=f"❌ Error loading KPI engine: {e}")
        return

    # Load active picks and latest closed per strategy
    try:
        active_by_strat = kpi_mod.get_active_counts_by_strategy()
        latest_closed = kpi_mod.get_latest_closed_per_strategy()
    except Exception:
        active_by_strat = {}
        latest_closed = {}

    await loading.delete()

    if not results:
        await ctx.send("❌ No closed picks found for analysis.")
        return

    ranked = sorted(results, key=lambda x: x["expectancy_pct"], reverse=True)
    positive = [r for r in ranked if r["expectancy_pct"] > 0]
    negative = [r for r in ranked if r["expectancy_pct"] <= 0]
    total_pnl = sum(r["total_pnl_dollar"] for r in ranked)
    total_open = sum(len(v) for v in active_by_strat.values())

    embed = discord.Embed(
        title="📊 Strategy Edge Report",
        description=(
            f"**{len(positive)} strategies making money** | "
            f"{len(negative)} losing money | Total PnL: **${total_pnl:+,.2f}**\n"
            f"Open positions: **{total_open}** across "
            f"**{len(active_by_strat)}** strategies\n\n"
            "📖 **What is Edge?** A strategy has \"edge\" if it makes money over many trades — "
            "not just from luck, but from a repeatable pattern."
        ),
        color=0x22c55e if len(positive) > len(negative) else 0xef4444,
    )

    # Top 8 strategies with context
    top_text = ""
    for i, r in enumerate(ranked[:8], 1):
        strat_id = r['entity_id']
        verdict = kpi_mod.compute_edge_verdict(r)
        emoji = "🟢" if verdict == "EDGE" else "🟡" if verdict in ("MARGINAL", "EDGE_UNCONFIRMED") else "🔴"

        # Active picks count
        open_picks = active_by_strat.get(strat_id, [])
        open_count = len(open_picks)

        # Last closed pick
        last = latest_closed.get(strat_id)
        last_info = ""
        if last:
            last_sym = last.get("symbol", "?")
            last_pnl = last.get("pnl_pct", 0)
            last_dt = _to_est(last.get("exit_date") or last.get("entry_date", ""))
            last_info = f" | Last: {last_sym} {last_pnl:+.2f}% ({last_dt})"

        open_info = f" | **{open_count} open**" if open_count else ""

        top_text += (
            f"{emoji} **{i}. {strat_id[:25]}** — "
            f"Avg: {r['expectancy_pct']:+.4f}% | "
            f"Sharpe: {r['sharpe']:.1f} | "
            f"WR: {r['win_rate']*100:.0f}% | "
            f"[{verdict}]"
            f"{open_info}{last_info}\n"
        )

    embed.add_field(name="🏆 Best Strategies (by avg profit per trade)", value=top_text[:1024] or "None", inline=False)

    # Active positions detail (top 5 strategies by open count)
    if active_by_strat:
        active_sorted = sorted(active_by_strat.items(), key=lambda x: -len(x[1]))[:5]
        active_text = ""
        for strat, picks in active_sorted:
            symbols = sorted(set(p.get("symbol", "?") for p in picks))[:4]
            sym_str = ", ".join(symbols)
            if len(symbols) < len(set(p.get("symbol", "?") for p in picks)):
                sym_str += "..."
            oldest = min(picks, key=lambda p: p.get("entry_date", "z"))
            entry_est = _to_est(oldest.get("entry_date", ""))
            active_text += f"**{strat[:22]}** — {len(picks)} open ({sym_str}) since {entry_est}\n"
        embed.add_field(name="📈 Active Positions", value=active_text[:1024], inline=False)

    # Jargon guide
    embed.add_field(
        name="📖 What do these numbers mean?",
        value=(
            "**Avg** = Average % you make (or lose) per trade\n"
            "**Sharpe** = Return vs risk — above 1.0 is good, above 2.0 is great\n"
            "**WR** = Win Rate — how often the strategy wins\n"
            "**Verdict**: EDGE=proven winner, MARGINAL=borderline, TRAP=looks good but isn't, DEAD=stop using"
        ),
        inline=False,
    )

    # Bottom 3
    if negative:
        bottom_text = ""
        for r in ranked[-3:]:
            verdict = kpi_mod.compute_edge_verdict(r)
            open_count = len(active_by_strat.get(r['entity_id'], []))
            open_tag = f" | {open_count} open" if open_count else ""
            bottom_text += (
                f"🔴 **{r['entity_id'][:25]}** — "
                f"Avg: {r['expectancy_pct']:+.4f}% | Kelly: {r['kelly_fraction']:+.0%} | "
                f"[{verdict}]{open_tag}\n"
            )
        embed.add_field(name="⚠️ Worst Performers (consider stopping these)", value=bottom_text[:1024], inline=False)

    embed.set_footer(text=f"!gems for hidden gems | !regime for diversification | Dashboard: {ALPHA_DASHBOARD_URL}")
    await ctx.send(embed=embed)


@bot.command(name='regime', aliases=['correlation', 'corr'])
async def quant_regime(ctx):
    """Market regime analysis — regime sensitivity, correlation, diversification."""
    loading = await ctx.send("🔬 Analyzing regimes and correlations...")

    try:
        regime_mod = _load_quant_module("regime_analyzer")
        regimes = regime_mod.analyze_regime_sensitivity(min_trades=3)
        matrix, strategies = regime_mod.compute_correlation_matrix(min_trades=5)
        conc = regime_mod.compute_concentration_risk()
    except Exception as e:
        await loading.edit(content=f"❌ Error: {e}")
        return

    await loading.delete()

    embed = discord.Embed(
        title="🔬 Market Conditions & Strategy Overlap",
        description=(
            f"Analyzing {len(regimes)} strategies across different market conditions.\n\n"
            "📖 **Why this matters:** Some strategies only work in calm markets, others in wild markets. "
            "If all your strategies do the same thing, one bad day could hurt everything at once."
        ),
        color=0x8b5cf6,
    )

    # Regime sensitivity
    if regimes:
        regime_text = ""
        for r in sorted(regimes, key=lambda x: x["high_vol_expectancy"], reverse=True)[:6]:
            pref_emoji = "⚡" if r["regime_preference"] == "high_vol" else "🌊" if r["regime_preference"] == "low_vol" else "⚖️"
            pref_label = "wild markets" if r["regime_preference"] == "high_vol" else "calm markets" if r["regime_preference"] == "low_vol" else "all markets"
            regime_text += (
                f"{pref_emoji} **{r['strategy'][:22]}** — "
                f"Calm: {r['low_vol_expectancy']:+.4f}% | "
                f"Wild: {r['high_vol_expectancy']:+.4f}% | "
                f"Best in: {pref_label}\n"
            )
        embed.add_field(name="📈 Which market suits each strategy? (Top 6)", value=regime_text[:1024] or "Insufficient data", inline=False)

    # Diversification score
    if strategies and len(strategies) >= 2:
        div_score = regime_mod.compute_diversification_score(matrix, strategies)
        corr_pairs = regime_mod.find_correlated_pairs(matrix, strategies, threshold=0.5)
        hedges = regime_mod.find_hedge_pairs(matrix, strategies, threshold=-0.3)

        div_emoji = "🟢" if div_score > 0.8 else "🟡" if div_score > 0.5 else "🔴"
        div_label = "Well spread out — different strategies doing different things" if div_score > 0.8 else "Somewhat spread out — some overlap" if div_score > 0.5 else "Too similar — strategies are copying each other"

        embed.add_field(
            name="🎯 Are your strategies spread out? (Diversification Score)",
            value=f"{div_emoji} Score: **{div_score:.0%}** — {div_label}\n"
                  f"Strategies analyzed: {len(strategies)} | "
                  f"Doing the same thing: {len(corr_pairs)} pairs | "
                  f"Protecting each other: {len(hedges)} pairs",
            inline=False,
        )

        if corr_pairs:
            pairs_text = "These strategy pairs move together — you might only need one:\n"
            for p in corr_pairs[:3]:
                similarity = abs(p['correlation']) * 100
                pairs_text += f"⚠️ {p['strategy_1'][:18]} & {p['strategy_2'][:18]} — {similarity:.0f}% similar\n"
            embed.add_field(name="🔗 Overlapping Strategies (pick one)", value=pairs_text, inline=True)

        if hedges:
            hedge_text = "These pairs balance each other — when one loses, the other tends to win:\n"
            for h in hedges[:3]:
                hedge_text += f"🛡️ {h['strategy_1'][:18]} & {h['strategy_2'][:18]}\n"
            embed.add_field(name="🛡️ Natural Safety Nets", value=hedge_text, inline=True)

    # Concentration risk
    if conc:
        high_conc = [(s, d) for s, d in conc.items() if d["concentration_risk"] == "HIGH"]
        if high_conc:
            conc_text = "Too many strategies betting on the same coin — risky if it drops:\n"
            for sym, data in high_conc[:5]:
                conc_text += f"🔴 **{sym}** — {data['strategies_using']} strategies all trading this\n"
            embed.add_field(name="⚠️ Too Many Eggs in One Basket", value=conc_text[:1024], inline=False)

    embed.set_footer(text="Higher diversification = safer portfolio | Not financial advice")
    await ctx.send(embed=embed)


@bot.command(name='stress', aliases=['scenarios', 'stresstest'])
async def quant_stress(ctx, budget: str = "1000"):
    """Stress test — scenario analysis + ruin probability. Usage: !stress 500"""
    try:
        budget_val = float(budget)
    except ValueError:
        budget_val = 1000

    loading = await ctx.send(f"🔥 Running stress tests on ${budget_val:,.0f} portfolio...")

    try:
        stress_mod = _load_quant_module("stress_tester")
        scenarios = stress_mod.run_scenario_analysis(budget_val)
        ruin = stress_mod.monte_carlo_ruin_probability(budget_val, n_simulations=3000)
    except Exception as e:
        await loading.edit(content=f"❌ Error: {e}")
        return

    await loading.delete()

    embed = discord.Embed(
        title=f"🔥 What If Things Go Wrong? — ${budget_val:,.0f} Portfolio",
        description=(
            "We test your portfolio against real-world disaster scenarios to see how much you could lose.\n"
            "📖 Think of it like a fire drill for your money."
        ),
        color=0xef4444,
    )

    if isinstance(scenarios, dict) and "error" not in scenarios:
        scenario_text = ""
        for sid, s in scenarios.items():
            emoji = "🔴" if s["total_portfolio_impact_pct"] < -30 else "🟡" if s["total_portfolio_impact_pct"] < -10 else "🟢"
            scenario_text += (
                f"{emoji} **{s['scenario']}** — "
                f"You'd lose **{abs(s['total_portfolio_impact_pct']):.1f}%** "
                f"(${abs(s['total_portfolio_impact_usd']):,.0f}) | "
                f"Chance of happening: {s['probability']:.0%}\n"
            )
        embed.add_field(name="📉 Disaster Scenarios — How bad could it get?", value=scenario_text[:1024], inline=False)

    if isinstance(ruin, dict) and "error" not in ruin:
        ruin_emoji = "🟢" if ruin["verdict"] == "SAFE" else "🟡" if ruin["verdict"] == "CAUTION" else "🔴"
        verdict_plain = "You're safe" if ruin["verdict"] == "SAFE" else "Be careful" if ruin["verdict"] == "CAUTION" else "High risk of losing big"
        embed.add_field(
            name="🎰 Could you go broke? (Simulated 3,000 possible futures)",
            value=(
                f"{ruin_emoji} Chance of losing half your money: **{ruin['ruin_probability_pct']:.1f}%** — {verdict_plain}\n"
                f"After 100 trades, you'd most likely have: **${ruin['median_final_equity']:,.2f}**\n"
                f"Worst case (bottom 5%): ${ruin['p5_equity']:,.2f} | Best case (top 5%): ${ruin['p95_equity']:,.2f}\n"
                f"Biggest dip along the way: {ruin['avg_max_drawdown']:.1%}"
            ),
            inline=False,
        )

    embed.set_footer(text="Based on 3,000 simulated futures using your real trade history | Not financial advice")
    await ctx.send(embed=embed)


@bot.command(name='ruin', aliases=['montecarlo', 'mc'])
async def quant_ruin(ctx):
    """Monte Carlo ruin probability across all budget tiers."""
    loading = await ctx.send("🎰 Running Monte Carlo across all budget tiers...")

    try:
        stress_mod = _load_quant_module("stress_tester")
    except Exception as e:
        await loading.edit(content=f"❌ Error: {e}")
        return

    embed = discord.Embed(
        title="🎰 Could You Go Broke? — All Budget Sizes",
        description=(
            "We simulated **3,000 possible futures** for each budget size, "
            "each running 100 trades based on your real strategy performance.\n\n"
            "📖 **How to read this:** If you started with $1,000, what would you most likely end up with? "
            "And what's the chance you'd lose half or more?"
        ),
        color=0x6366f1,
    )

    ruin_text = ""
    for budget in [200, 500, 1000, 2000, 5000]:
        ruin = stress_mod.monte_carlo_ruin_probability(budget, n_simulations=3000)
        if "error" in ruin:
            continue
        emoji = "🟢" if ruin["verdict"] == "SAFE" else "🟡" if ruin["verdict"] == "CAUTION" else "🔴"
        verdict_plain = "Safe" if ruin["verdict"] == "SAFE" else "Careful" if ruin["verdict"] == "CAUTION" else "Risky"
        ruin_text += (
            f"{emoji} **${budget:,}** → You'd most likely have **${ruin['median_final_equity']:,.0f}** | "
            f"Lose-half chance: {ruin['ruin_probability_pct']:.1f}% | "
            f"Worst case: ${ruin['p5_equity']:,.0f} | Best: ${ruin['p95_equity']:,.0f} | "
            f"{verdict_plain}\n"
        )

    embed.add_field(name="💰 What happens to your money after 100 trades?", value=ruin_text[:1024] or "No data", inline=False)

    await loading.delete()
    embed.set_footer(text="Use !stress 500 for detailed disaster scenarios | Not financial advice")
    await ctx.send(embed=embed)


@bot.command(name='gems', aliases=['hidden', 'hiddengems', 'asymmetric'])
async def quant_gems(ctx):
    """Hidden gem discovery — low WR + high payoff = asymmetric alpha."""
    loading = await ctx.send("💎 Scanning for hidden gems...")

    try:
        scoring_mod = _load_quant_module("scoring_engine")
        kpi_mod = _load_quant_module("kpi_engine")
        kpis = kpi_mod.compute_all_kpis(min_trades=2)
        gems = scoring_mod.detect_hidden_gems(kpis)
        tails = scoring_mod.find_tail_catchers(kpis)
    except Exception as e:
        await loading.edit(content=f"❌ Error: {e}")
        return

    await loading.delete()

    embed = discord.Embed(
        title="💎 Hidden Gems — Ugly Ducklings That Actually Make Money",
        description=(
            "Some strategies lose more often than they win, but when they DO win, they win **big**. "
            "These \"ugly ducklings\" can be more profitable than strategies with high win rates!\n\n"
            "📖 **Example:** A strategy that wins only 30% of the time but makes 5x when it wins "
            "is better than one that wins 60% but only makes 0.5x."
        ),
        color=0xeab308,
    )

    if gems:
        gem_text = ""
        for g in gems[:6]:
            gem_text += (
                f"💎 **{g['strategy'][:25]}**\n"
                f"   Wins {g['win_rate']:.0%} of the time | Avg profit/trade: {g['expectancy']:+.4f}% | "
                f"When it wins, it wins **{g['payoff_ratio']:.1f}x** bigger than when it loses\n"
            )
            for reason in g["reasons"][:2]:
                gem_text += f"   → {reason}\n"
        embed.add_field(name=f"💎 Hidden Gems ({len(gems)} found)", value=gem_text[:1024], inline=False)
    else:
        embed.add_field(name="💎 Hidden Gems", value="No hidden gems found right now.", inline=False)

    if tails:
        tail_text = "These strategies catch rare but massive price moves (10%+ in one trade):\n"
        for t in tails[:5]:
            tail_text += (
                f"🎯 **{t['strategy'][:25]}** — caught {t['big_wins']} huge moves out of {t['total_trades']} trades | "
                f"Biggest win: {t['biggest_win_pct']:+.1%} | Coins: {', '.join(t['symbols_caught'][:3])}\n"
            )
        embed.add_field(name="🎯 Big Move Catchers (10%+ winners)", value=tail_text[:1024], inline=False)

    embed.set_footer(text="Low win rate ≠ bad strategy. Look at the payoff! | Not financial advice")
    await ctx.send(embed=embed)


@bot.command(name='compliance', aliases=['regulated', 'assets', 'screen'])
async def quant_compliance(ctx, budget: str = "1000"):
    """Regulated asset screening + compliance-constrained allocation."""
    try:
        budget_val = float(budget)
    except ValueError:
        budget_val = 1000

    loading = await ctx.send(f"🛡️ Screening assets for ${budget_val:,.0f} compliance allocation...")

    try:
        reg_mod = _load_quant_module("regulated_assets")
        screened = reg_mod.screen_traded_assets()
        alloc = reg_mod.constrained_allocation(budget_val)
    except Exception as e:
        await loading.edit(content=f"❌ Error: {e}")
        return

    await loading.delete()

    embed = discord.Embed(
        title=f"🛡️ Which Coins Are Safe to Trade? — ${budget_val:,.0f}",
        description=(
            "Not all crypto is created equal. Some coins are safe and liquid (easy to buy/sell), "
            "while others can be manipulated by big players.\n\n"
            "📖 **Manipulation risk** = Can whales or insiders move the price against you?"
        ),
        color=0x3b82f6,
    )

    if screened:
        screen_text = ""
        for a in screened[:8]:
            status_emoji = "✅" if a["regulated_status"] == "approved" else "⚠️" if a["regulated_status"] == "review_needed" else "🚫"
            risk_emoji = "🟢" if a["manipulation_risk"] == "low" else "🟡" if a["manipulation_risk"] == "medium" else "🔴"
            risk_label = "Safe" if a["manipulation_risk"] == "low" else "Some risk" if a["manipulation_risk"] == "medium" else "Risky"
            screen_text += (
                f"{status_emoji} **{a['symbol']}** — "
                f"{risk_emoji} {risk_label} | "
                f"{a['trades']} trades | PnL: {a['total_pnl']:+.4f}%\n"
            )
        embed.add_field(name="📋 Coin Safety Check", value=screen_text[:1024], inline=False)

    if isinstance(alloc, dict) and "error" not in alloc:
        alloc_text = (
            f"Of your ${alloc['budget']:,.0f}, we'd put **${alloc['total_allocated_usd']:,.2f}** to work "
            f"and keep **${alloc['unallocated_usd']:,.2f}** as a safety cushion.\n\n"
        )
        for a in alloc.get("allocations", [])[:6]:
            cap_note = ""
            if a["cap_reason"] == "meme_cap":
                cap_note = " (meme coin — capped at 2%)"
            elif a["cap_reason"] == "max_asset_cap":
                cap_note = " (capped at 5% max)"
            alloc_text += (
                f"  **{a['strategy'][:22]}** ({a['primary_symbol']}) — "
                f"${a['capped_allocation_usd']:,.2f} ({a['allocation_pct']:.1f}%){cap_note}\n"
            )
        embed.add_field(name="💰 How to Split Your Money (Safe Limits)", value=alloc_text[:1024], inline=False)

    embed.set_footer(text="Rule: Never put more than 5% in one coin. Meme coins max 2%. | Not financial advice")
    await ctx.send(embed=embed)


@bot.command(name='alerts', aliases=['riskalerts', 'risk'])
async def quant_alerts(ctx):
    """Risk alerts — strategies breaching Sharpe, DD, Kelly thresholds."""
    loading = await ctx.send("🚨 Checking risk alerts...")

    try:
        stress_mod = _load_quant_module("stress_tester")
        alerts = stress_mod.check_risk_alerts()
    except Exception as e:
        await loading.edit(content=f"❌ Error: {e}")
        return

    await loading.delete()

    critical = [a for a in alerts if any(al["level"] == "CRITICAL" for al in a["alerts"])]
    warnings = [a for a in alerts if a not in critical]

    embed = discord.Embed(
        title="🚨 Strategy Health Check",
        description=(
            f"**{len(critical)} need immediate attention** | {len(warnings)} worth watching\n\n"
            "📖 **What triggers an alert?**\n"
            "• Return-to-risk ratio too low (not worth the risk)\n"
            "• Lost more than 25% from peak (big drawdown)\n"
            "• Math says don't bet on it (negative Kelly = stop trading this)"
        ),
        color=0xef4444 if critical else 0xf59e0b if warnings else 0x22c55e,
    )

    if critical:
        crit_text = ""
        for a in critical[:5]:
            verdict_plain = {"DEAD": "Dead — stop using", "TRAP": "Trap — looks good but isn't", "NO_EDGE": "No real edge"}.get(a["verdict"], a["verdict"])
            crit_text += f"🚨 **{a['strategy'][:25]}** — {verdict_plain}\n"
            for al in a["alerts"]:
                if al["level"] == "CRITICAL":
                    crit_text += f"   → {al['message'][:80]}\n"
        embed.add_field(name="🚨 Stop or Review These Now", value=crit_text[:1024], inline=False)

    if warnings:
        warn_text = ""
        for a in warnings[:5]:
            warn_text += f"⚠️ **{a['strategy'][:25]}**\n"
            for al in a["alerts"][:1]:
                warn_text += f"   → {al['message'][:80]}\n"
        embed.add_field(name="⚠️ Keep an Eye On These", value=warn_text[:1024], inline=False)

    if not alerts:
        embed.add_field(name="✅ All Clear!", value="Every strategy is within healthy limits. Nothing to worry about right now.", inline=False)

    embed.set_footer(text="Checks run automatically. Use !edge for full strategy details | Not financial advice")
    await ctx.send(embed=embed)


@bot.command(name='walkforward', aliases=['wf', 'persistence'])
async def quant_walkforward(ctx):
    """Walk-forward validation — does the edge persist across time periods?"""
    loading = await ctx.send("🔄 Running walk-forward validation (3-fold)...")

    try:
        stress_mod = _load_quant_module("stress_tester")
        wf = stress_mod.walk_forward_analysis(n_folds=3)
    except Exception as e:
        await loading.edit(content=f"❌ Error: {e}")
        return

    await loading.delete()

    embed = discord.Embed(
        title="🔄 Is the Edge Real or Just Luck?",
        description=(
            "We split your trade history into 3 time periods and check if each strategy "
            "made money in **all** of them — not just one lucky streak.\n\n"
            "📖 **Why?** A strategy that only worked last month might be lucky. "
            "One that worked across ALL periods has a real, repeatable edge."
        ),
        color=0x6366f1,
    )

    if isinstance(wf, dict):
        cp = wf.get("consistently_profitable", [])
        ic = wf.get("inconsistent", [])

        if cp:
            cp_text = ""
            for s in cp[:8]:
                c = wf["consistency"].get(s, {})
                cp_text += (
                    f"✅ **{s[:25]}** — Avg profit/trade: {c.get('avg_expectancy', 0):+.4f}% "
                    f"(profitable in {c.get('folds_positive', 0)}/{c.get('folds_present', 0)} time periods)\n"
                )
            embed.add_field(name=f"✅ Real Edge — Made money in every period ({len(cp)})", value=cp_text[:1024], inline=False)

        if ic:
            ic_text = "These only worked some of the time — could be lucky:\n"
            for s in ic[:5]:
                c = wf["consistency"].get(s, {})
                ic_text += f"🟡 **{s[:25]}** — Only worked in {c.get('folds_positive', 0)} out of {c.get('folds_present', 0)} periods\n"
            embed.add_field(name=f"🟡 Might Be Luck ({len(ic)})", value=ic_text[:1024], inline=False)

        # Fold details
        for fold in wf.get("folds", []):
            fold_strats = fold.get("strategies", {})
            positive = sum(1 for s in fold_strats.values() if s.get("expectancy", 0) > 0)
            embed.add_field(
                name=f"Period {fold['fold']}: {fold['period']}",
                value=f"{fold['n_trades']} trades | {positive}/{len(fold_strats)} strategies profitable",
                inline=True,
            )
    else:
        embed.add_field(name="Result", value="Not enough trade history yet to run this test.", inline=False)

    embed.set_footer(text="Profitable in all periods = real edge. Only some = might be luck. | Not financial advice")
    await ctx.send(embed=embed)


@bot.command(name='quant-help', aliases=['quanthelp', 'qh', 'quant'])
async def quant_help(ctx):
    """Complete guide to all Quant Lab commands — beginner friendly."""
    embed = discord.Embed(
        title="📚 Quant Lab — Your Trading Strategy Checkup Tool",
        description=(
            "Think of this as a **doctor's checkup for your trading strategies**. "
            "Each command answers a plain question about your portfolio's health.\n\n"
            "All results are based on real trade data — no guessing."
        ),
        color=0x8b5cf6,
    )

    embed.add_field(
        name="📊 `!edge` — \"Which strategies are actually making money?\"",
        value=(
            "Shows each strategy's average profit per trade, risk-adjusted score, "
            "and a simple verdict: EDGE (keep it), MARGINAL (watch it), TRAP (looks good but isn't), DEAD (stop).\n"
            "Also: `!kpi`, `!expectancy`"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔬 `!regime` — \"Are my strategies too similar?\"",
        value=(
            "Checks if your strategies are doing the same thing (risky) or different things (safer). "
            "Also shows which strategies work best in calm vs wild markets.\n"
            "Also: `!correlation`, `!corr`"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔥 `!stress 1000` — \"What if the market crashes?\"",
        value=(
            "Tests your portfolio against 6 disaster scenarios (70% crash, regulatory ban, etc.) "
            "and simulates 3,000 possible futures to estimate your chance of a big loss.\n"
            "Replace 1000 with your budget. Also: `!scenarios`, `!stresstest`"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎰 `!ruin` — \"Could I go broke?\"",
        value=(
            "Simulates 3,000 possible futures for budgets from $200 to $5,000. "
            "Shows what you'd most likely end up with, and the chance of losing half your money.\n"
            "Also: `!montecarlo`, `!mc`"
        ),
        inline=False,
    )
    embed.add_field(
        name="💎 `!gems` — \"Are there strategies that look bad but are secretly good?\"",
        value=(
            "Finds strategies with low win rates that still make money because their wins are much "
            "bigger than their losses. Also finds strategies that catch rare 10%+ moves.\n"
            "Also: `!hidden`, `!hiddengems`"
        ),
        inline=False,
    )
    embed.add_field(
        name="🛡️ `!compliance 1000` — \"Which coins are safe to trade?\"",
        value=(
            "Screens coins for manipulation risk and suggests how to split your budget safely. "
            "No more than 5% in one coin, meme coins limited to 2%.\n"
            "Replace 1000 with your budget. Also: `!regulated`, `!screen`"
        ),
        inline=False,
    )
    embed.add_field(
        name="🚨 `!alerts` — \"Should I stop trading anything?\"",
        value=(
            "Instant health check — flags strategies that are losing too much, "
            "too risky, or where the math says you shouldn't be trading them.\n"
            "Also: `!riskalerts`, `!risk`"
        ),
        inline=False,
    )
    embed.add_field(
        name="🔄 `!walkforward` — \"Is my strategy's edge real or just luck?\"",
        value=(
            "Splits your trade history into 3 time periods. If a strategy made money in ALL "
            "periods, it's real. If only some, it might just be lucky timing.\n"
            "Also: `!wf`, `!persistence`"
        ),
        inline=False,
    )

    embed.add_field(
        name="🔥 `!spam-picks` — \"Send me picks every 5 minutes!\"",
        value=(
            "Starts a live pick stream — scans all 16 Correlation + 6 Leap strategies every 5 min "
            "and posts BUY/SELL signals with entry/TP/SL and strategy performance stats.\n"
            "Auto-stops after 2 hours. Use `!spam-extend` to add 2 more hours (max 8hr).\n"
            "Also: `!spam`, `!spampicks`"
        ),
        inline=False,
    )
    embed.add_field(
        name="🛑 `!spam-end` — \"Stop the pick stream\"",
        value=(
            "Immediately stops the spam-picks loop in this channel.\n"
            "Also: `!spam-stop`, `!spamend`, `!spam-picks-end`"
        ),
        inline=False,
    )
    embed.add_field(
        name="⏳ `!spam-extend` — \"Keep it going longer\"",
        value=(
            "Extends the current spam session by 2 hours (max 8hr total).\n"
            "Also: `!spamextend`"
        ),
        inline=False,
    )

    embed.set_footer(text="Also available: !fc-pro !fc-bundle !fc-baby !fc-fresh !refresh !status !dashboard")
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────────
# Spam Picks — Live 5-Minute Pick Stream
# ─────────────────────────────────────────────────────────────────

# In-memory state: channel_id -> {"task": asyncio.Task, "remaining": int, "started": datetime, "max_cycles": int}
_spam_sessions = {}

SPAM_INTERVAL = 300       # 5 minutes
DEFAULT_CYCLES = 24       # 2 hours (24 * 5min)
EXTEND_CYCLES = 24        # +2 hours per extend
MAX_TOTAL_CYCLES = 96     # 8 hours max


def _run_single_strategy(strat, timeout_sec=30):
    """Run a single strategy with a per-strategy timeout. Returns (picks, error_str)."""
    import threading

    result = {"picks": [], "error": None}

    def _worker():
        try:
            result["picks"] = strat.run()
        except Exception as e:
            result["error"] = f"{strat.name}: {type(e).__name__}: {e}"

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)
    if t.is_alive():
        result["error"] = f"{strat.name}: timed out ({timeout_sec}s)"
        return [], result["error"]
    return result["picks"], result["error"]


# Priority strategies that always run first (proven strategies get guaranteed slots)
PRIORITY_STRATEGIES = {
    "irb_hoffman", "adaptive_irb_hoffman", "fib_rsi_divergence",
    "protective_momentum", "hoffman_irb_1h", "hoffman_irb_2h", "hoffman_irb_4h",
    "hoffman_adaptive_atr", "hoffman_kalman_trend", "hoffman_trailing_atr",
    "hoffman_momentum_tp", "hoffman_kelly_sized", "hoffman_htf_confluence",
    "hoffman_45_degree", "hoffman_scalper_20m",
}


def _prewarm_kline_cache():
    """Pre-fetch all common klines so strategies read from cache instantly.

    This is the key optimization: instead of 70 strategies each fetching
    BTCUSDT 1h independently (with rate limits), we fetch each unique
    (symbol, interval, limit) combo ONCE upfront. Strategies then get
    instant cache hits with zero API calls.
    """
    import time as _time
    from paper_trading.multi_source import fetch_klines, clear_cache

    clear_cache()  # Fresh data each cycle

    # All symbols used across strategies
    SYMBOLS_MAJOR = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                     "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "DOGEUSDT"]
    SYMBOLS_HOFFMAN = ["BTCUSDT", "DOGEUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]

    # All (interval, limit) combos used by strategies
    # Cache superset logic: a 300-bar fetch covers any smaller request (limit=10, 30, 100)
    FETCH_SPECS = [
        ("1h", 250, SYMBOLS_MAJOR),      # Mercury, IRB Hoffman, Simpleton, Fib RSI, Protective Mom + Corr/Leap (100)
        ("4h", 300, SYMBOLS_MAJOR),       # FR, Verified, Kimi, Alpha Arena strategies
        ("1d", 300, SYMBOLS_MAJOR),       # Triple Confirmation, Volume Breakout, RSI-2, Whale (10/30)
        ("15m", 200, SYMBOLS_HOFFMAN),    # Hoffman IRB 1H/2H/4H hold variants
    ]

    start = _time.monotonic()
    fetched = 0
    errors = 0
    for interval, limit, symbols in FETCH_SPECS:
        for sym in symbols:
            try:
                klines = fetch_klines(sym, interval=interval, limit=limit)
                if klines:
                    fetched += 1
            except Exception:
                errors += 1

    elapsed = _time.monotonic() - start
    print(f"[SPAM] Cache pre-warmed: {fetched} kline sets in {elapsed:.1f}s ({errors} errors)")
    return fetched


def _run_spam_scan_sync():
    """Run all paper trading strategies with pre-warmed cache and per-strategy timeouts."""
    import time as _time

    picks = []
    diag = {"total": 0, "ran": 0, "with_picks": 0, "errors": [], "by_strategy": {}}
    scan_start = _time.monotonic()
    SCAN_BUDGET = 240  # 4 min total budget

    try:
        # Phase 1: Pre-warm kline cache (all API calls happen here)
        _prewarm_kline_cache()

        from paper_trading.strategies import ALL_STRATEGIES
        diag["total"] = len(ALL_STRATEGIES)

        # Split into priority (Hoffman etc.) and rest
        priority = [s for s in ALL_STRATEGIES if s.name in PRIORITY_STRATEGIES]
        rest = [s for s in ALL_STRATEGIES if s.name not in PRIORITY_STRATEGIES]

        # Phase 2: Run priority strategies (data already cached, should be fast)
        for strat in priority:
            strat_picks, err = _run_single_strategy(strat, timeout_sec=15)
            if err:
                diag["errors"].append(err)
                print(f"[SPAM] {err}")
            else:
                diag["ran"] += 1
                diag["by_strategy"][strat.display_name] = len(strat_picks)
                if strat_picks:
                    diag["with_picks"] += 1
                    picks.extend(strat_picks)

        # Phase 3: Run remaining strategies (also cached, 10s timeout each)
        for strat in rest:
            elapsed = _time.monotonic() - scan_start
            if elapsed >= SCAN_BUDGET:
                remaining_count = len(rest) - (diag["ran"] - len(priority))
                if remaining_count > 0:
                    diag["errors"].append(f"Budget exhausted after {elapsed:.0f}s, {remaining_count} skipped")
                    print(f"[SPAM] Budget exhausted, skipping remaining strategies")
                break
            strat_picks, err = _run_single_strategy(strat, timeout_sec=10)
            if err:
                diag["errors"].append(err)
                print(f"[SPAM] {err}")
            else:
                diag["ran"] += 1
                diag["by_strategy"][strat.display_name] = len(strat_picks)
                if strat_picks:
                    diag["with_picks"] += 1
                    picks.extend(strat_picks)

    except ImportError as e:
        diag["errors"].append(f"import: {e}")
        print(f"[SPAM] Import error: {e}")

    elapsed = _time.monotonic() - scan_start
    print(f"[SPAM] Scan complete: {diag['ran']}/{diag['total']} strategies in {elapsed:.1f}s, {len(picks)} picks")
    return picks, diag


def _market_snapshot_sync():
    """Quick market snapshot for context when no signals fire."""
    snapshot = {}
    try:
        from paper_trading.helpers import fetch_json
        # BTC price + 24h change
        ticker = fetch_json("https://api.binance.com/api/v3/ticker/24hr",
                            params={"symbol": "BTCUSDT"})
        if ticker:
            snapshot["BTC"] = {
                "price": float(ticker.get("lastPrice", 0)),
                "change_pct": float(ticker.get("priceChangePercent", 0)),
            }
        # ETH
        ticker = fetch_json("https://api.binance.com/api/v3/ticker/24hr",
                            params={"symbol": "ETHUSDT"})
        if ticker:
            snapshot["ETH"] = {
                "price": float(ticker.get("lastPrice", 0)),
                "change_pct": float(ticker.get("priceChangePercent", 0)),
            }
        # Fear & Greed
        try:
            fg = fetch_json("https://api.alternative.me/fng/?limit=1")
            if fg and fg.get("data"):
                snapshot["fear_greed"] = {
                    "value": int(fg["data"][0]["value"]),
                    "label": fg["data"][0]["value_classification"],
                }
        except Exception:
            pass
    except Exception as e:
        print(f"[SPAM] Snapshot error: {e}")
    return snapshot


def _load_portfolio_stats():
    """Load paper trading performance stats."""
    stats = {}
    perf_file = Path(__file__).parent.parent / "paper_trading" / "data" / "portfolios.json"
    if perf_file.exists():
        try:
            data = json.loads(perf_file.read_text())
            for p in data:
                stats[p.get("name", "")] = p
        except Exception:
            pass

    # Also try to load per-strategy stats from closed picks
    closed_file = Path(__file__).parent.parent / "paper_trading" / "data" / "closed_picks.json"
    strat_stats = {}
    if closed_file.exists():
        try:
            closed = json.loads(closed_file.read_text())
            for pick in closed:
                sname = pick.get("strategy", "")
                if sname not in strat_stats:
                    strat_stats[sname] = {"wins": 0, "losses": 0, "total_pnl": 0.0}
                if pick.get("pnl_pct", 0) > 0:
                    strat_stats[sname]["wins"] += 1
                else:
                    strat_stats[sname]["losses"] += 1
                strat_stats[sname]["total_pnl"] += pick.get("pnl_pct", 0)
        except Exception:
            pass

    return stats, strat_stats


async def _spam_loop(channel_id):
    """Background loop: scan every 5 min and post picks."""
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    session = _spam_sessions.get(channel_id)
    if not session:
        return

    cycle = 0
    portfolio_stats, strat_stats = _load_portfolio_stats()

    while channel_id in _spam_sessions:
        session = _spam_sessions[channel_id]
        remaining = session["remaining"]

        if remaining <= 0:
            # Session expired
            embed = discord.Embed(
                title="Spam Picks Session Ended",
                description=(
                    f"Ran for {cycle} cycles ({cycle * 5} minutes).\n"
                    "Use `!spam-picks` to start a new session."
                ),
                color=0x6b7280,
            )
            try:
                await channel.send(embed=embed)
            except Exception:
                pass
            _spam_sessions.pop(channel_id, None)
            return

        cycle += 1
        time_left_min = remaining * 5
        hours_left = time_left_min // 60
        mins_left = time_left_min % 60
        time_str = f"{hours_left}h {mins_left}m" if hours_left > 0 else f"{mins_left}m"

        # Run strategies in thread pool (they are synchronous/blocking)
        diag = {"total": 0, "ran": 0, "with_picks": 0, "errors": [], "by_strategy": {}}
        try:
            loop = asyncio.get_event_loop()
            picks, diag = await asyncio.wait_for(
                loop.run_in_executor(None, _run_spam_scan_sync),
                timeout=240  # 4-minute timeout to stay within 5-min interval
            )
        except asyncio.TimeoutError:
            picks = []
            diag["errors"].append("Scan timed out after 4 minutes")
            print(f"[SPAM] Scan timed out after 4 minutes")
        except Exception as e:
            picks = []
            diag["errors"].append(f"Scan crash: {type(e).__name__}: {e}")
            print(f"[SPAM] Scan error: {e}")

        # Record picks to audit trail
        if picks:
            try:
                from audit_trail import start_run, finish_run, record_raw_pick
                run_id = start_run(regime_data={"scanner": "spam_picks", "cycle": cycle})
                for p in picks:
                    record_raw_pick("spam_picks", {
                        "symbol": p.symbol, "direction": p.direction,
                        "entry_price": p.entry_price, "take_profit": p.tp,
                        "stop_loss": p.sl, "confidence": p.confidence,
                        "strategy": p.strategy, "timestamp": str(p.picked_at),
                        "reason": p.reason,
                    }, run_id)
                finish_run(run_id, consensus_count=0, systems_loaded=1, raw_count=len(picks))
            except Exception as e:
                print(f"[SPAM] Audit trail error: {e}")

        title = f"SPAM PICKS \u2014 Cycle {cycle}/{session.get('max_cycles', DEFAULT_CYCLES)} ({time_str} remaining)"

        if picks:
            # Sort by confidence desc, take top 10
            picks.sort(key=lambda p: p.confidence, reverse=True)
            top_picks = picks[:10]

            embed = discord.Embed(
                title=title,
                description=f"{len(picks)} signals from {diag.get('with_picks', '?')}/{diag.get('ran', '?')} strategies",
                color=0xf59e0b,
            )

            for p in top_picks:
                direction_emoji = "\U0001f4c8" if p.direction == "LONG" else "\U0001f4c9"
                rr = f"{p.risk_reward:.1f}:1" if p.risk_reward else "N/A"

                # Strategy stats
                ss = strat_stats.get(p.strategy, {})
                wins = ss.get("wins", 0)
                losses = ss.get("losses", 0)
                total = wins + losses
                wr = f"{wins/total*100:.0f}%" if total > 0 else "NEW"
                pnl = f"{ss.get('total_pnl', 0):+.1f}%" if total > 0 else "N/A"

                embed.add_field(
                    name=f"{direction_emoji} {p.symbol} {p.direction} | {p.strategy_name}",
                    value=(
                        f"Entry: `${p.entry_price:,.4f}` | TP: `${p.tp:,.4f}` | SL: `${p.sl:,.4f}`\n"
                        f"Signal: `{p.confidence:.0%}` | R:R: `{rr}` | Track: `WR {wr} | P&L {pnl} | {total} trades`"
                    ),
                    inline=False,
                )

            embed.set_footer(text="!spam-end to stop | !spam-extend +2hr | Not financial advice")
        else:
            # ── Rich "no signals" embed with diagnostics ──
            ran = diag.get("ran", 0)
            total_strats = diag.get("total", 0)
            errors = diag.get("errors", [])

            # Get market snapshot for context
            try:
                snap = await loop.run_in_executor(None, _market_snapshot_sync)
            except Exception:
                snap = {}

            desc_parts = [f"Scanned **{ran}/{total_strats}** strategies — none met entry criteria."]

            # Market context
            if snap:
                market_lines = []
                for sym in ("BTC", "ETH"):
                    if sym in snap:
                        s = snap[sym]
                        arrow = "\u2B06" if s["change_pct"] >= 0 else "\u2B07"
                        market_lines.append(
                            f"{sym}: `${s['price']:,.0f}` {arrow} `{s['change_pct']:+.1f}%` 24h")
                if snap.get("fear_greed"):
                    fg = snap["fear_greed"]
                    market_lines.append(f"Fear & Greed: `{fg['value']}` ({fg['label']})")
                if market_lines:
                    desc_parts.append("\n**Market:**\n" + "\n".join(market_lines))

            embed = discord.Embed(
                title=title,
                description="\n".join(desc_parts),
                color=0x6b7280,
            )

            # Show errors if any
            if errors:
                err_str = "\n".join(f"`{e}`" for e in errors[:5])
                if len(errors) > 5:
                    err_str += f"\n... +{len(errors) - 5} more"
                embed.add_field(name=f"Errors ({len(errors)})", value=err_str, inline=False)

            # Strategy breakdown — group by portfolio type
            by_strat = diag.get("by_strategy", {})
            if by_strat:
                # Group categories
                categories = {}
                try:
                    from paper_trading.strategies import ALL_STRATEGIES as _strats
                    for s in _strats:
                        cat = getattr(s, "portfolio_type", "other")
                        if cat not in categories:
                            categories[cat] = {"ran": 0, "picks": 0, "names": []}
                        if s.display_name in by_strat:
                            categories[cat]["ran"] += 1
                            n_picks = by_strat[s.display_name]
                            categories[cat]["picks"] += n_picks
                            if n_picks == 0:
                                categories[cat]["names"].append(s.display_name)
                except ImportError:
                    pass

                if categories:
                    cat_lines = []
                    for cat, info in sorted(categories.items()):
                        status = "\u2705" if info["picks"] > 0 else "\u274C"
                        cat_lines.append(
                            f"{status} **{cat}**: {info['ran']} strategies, {info['picks']} picks")
                    embed.add_field(
                        name="Strategy Groups",
                        value="\n".join(cat_lines[:8]),
                        inline=False,
                    )

            embed.set_footer(text="!spam-end to stop | !spam-extend +2hr | Waiting for entry criteria...")

        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"[SPAM] Send error: {e}")

        # Decrement remaining cycles
        session["remaining"] -= 1
        _spam_sessions[channel_id] = session

        # Wait 5 minutes
        await asyncio.sleep(SPAM_INTERVAL)

    # Cleaned up externally
    print(f"[SPAM] Session ended for channel {channel_id}")


@bot.command(name='spam-picks', aliases=['spam', 'spampicks'])
async def spam_picks(ctx):
    """Start a 5-minute pick stream. Runs all Correlation + Leap strategies. Auto-stops after 2 hours."""
    cid = ctx.channel.id

    if cid in _spam_sessions:
        session = _spam_sessions[cid]
        remaining_min = session["remaining"] * 5
        await ctx.send(
            f"A spam session is already running in this channel ({remaining_min} min remaining).\n"
            f"Use `!spam-end` to stop it first, or `!spam-extend` to add more time."
        )
        return

    session = {
        "remaining": DEFAULT_CYCLES,
        "max_cycles": DEFAULT_CYCLES,
        "started": datetime.now(timezone.utc),
        "started_by": str(ctx.author),
    }
    _spam_sessions[cid] = session

    # Count available strategies
    try:
        from paper_trading.strategies import ALL_STRATEGIES as _all_strats
        strat_count = len(_all_strats)
    except ImportError:
        strat_count = 50

    embed = discord.Embed(
        title="SPAM PICKS ACTIVATED",
        description=(
            f"Scanning **{strat_count} strategies** every 5 minutes.\n\n"
            f"**Duration:** 2 hours (24 cycles)\n"
            f"**Portfolios:** Correlation, Leap, FundedRelay, Verified Research, "
            f"Kimi/Academic, Mercury, Triple Confirmation + Original 10\n\n"
            f"First scan starting now..."
        ),
        color=0x22c55e,
    )
    embed.add_field(name="Stop", value="`!spam-end`", inline=True)
    embed.add_field(name="Extend", value="`!spam-extend` (+2hr, max 8hr)", inline=True)
    embed.set_footer(text=f"Started by {ctx.author} | Not financial advice")
    await ctx.send(embed=embed)

    # Start background loop
    task = bot.loop.create_task(_spam_loop(cid))
    session["task"] = task
    _spam_sessions[cid] = session


@bot.command(name='spam-end', aliases=['spam-stop', 'spamend', 'spam-picks-end', 'spamstop'])
async def spam_end(ctx):
    """Stop the spam-picks stream in this channel."""
    cid = ctx.channel.id

    if cid not in _spam_sessions:
        await ctx.send("No spam session running in this channel. Use `!spam-picks` to start one.")
        return

    session = _spam_sessions.pop(cid, {})
    task = session.get("task")
    if task and not task.done():
        task.cancel()

    started = session.get("started", datetime.now(timezone.utc))
    duration = datetime.now(timezone.utc) - started
    dur_min = int(duration.total_seconds() // 60)

    embed = discord.Embed(
        title="SPAM PICKS STOPPED",
        description=f"Session ended after {dur_min} minutes.\nUse `!spam-picks` to start a new one.",
        color=0xef4444,
    )
    embed.set_footer(text=f"Stopped by {ctx.author}")
    await ctx.send(embed=embed)


@bot.command(name='spam-extend', aliases=['spamextend'])
async def spam_extend(ctx):
    """Extend the current spam session by 2 hours (max 8hr total)."""
    cid = ctx.channel.id

    if cid not in _spam_sessions:
        await ctx.send("No spam session running. Use `!spam-picks` to start one first.")
        return

    session = _spam_sessions[cid]
    current_max = session.get("max_cycles", DEFAULT_CYCLES)

    if current_max >= MAX_TOTAL_CYCLES:
        await ctx.send(f"Already at maximum duration (8 hours / {MAX_TOTAL_CYCLES} cycles). Cannot extend further.")
        return

    new_max = min(current_max + EXTEND_CYCLES, MAX_TOTAL_CYCLES)
    added = new_max - current_max
    session["remaining"] += added
    session["max_cycles"] = new_max
    _spam_sessions[cid] = session

    total_hours = new_max * 5 / 60
    remaining_min = session["remaining"] * 5

    embed = discord.Embed(
        title="SPAM PICKS EXTENDED",
        description=(
            f"Added {added * 5} minutes ({added} cycles).\n"
            f"**Total allowed:** {total_hours:.0f} hours | **Remaining:** {remaining_min} min\n"
        ),
        color=0x3b82f6,
    )
    if new_max >= MAX_TOTAL_CYCLES:
        embed.set_footer(text="Maximum duration reached (8hr). No more extensions possible.")
    else:
        embed.set_footer(text=f"Use !spam-extend again to add more (max {MAX_TOTAL_CYCLES * 5 // 60}hr total)")
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────────
# Best Picks + Live Price Check Commands (v3.1)
# ─────────────────────────────────────────────────────────────────

def _fetch_live_price(symbol: str) -> dict | None:
    """Fetch live price from Binance. Returns {price, change_24h} or None."""
    sym = symbol.upper().replace("-", "").replace("/", "")
    if not sym.endswith("USDT") and not sym.endswith("USD"):
        sym += "USDT"
    sym = sym.replace("USD", "USDT") if not sym.endswith("USDT") else sym
    try:
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            params={"symbol": sym}, timeout=8,
        )
        if resp.status_code == 200:
            d = resp.json()
            return {
                "price": float(d.get("lastPrice", 0)),
                "change_24h": float(d.get("priceChangePercent", 0)),
                "symbol": sym,
            }
    except Exception:
        pass
    # Fallback: try without trailing T (e.g. XRPUSDT -> XRPUSD won't work, but covers edge cases)
    return None


def _fetch_forex_price(symbol: str) -> dict | None:
    """Fetch forex/commodity price from Yahoo Finance API (free)."""
    # Map common symbols
    yahoo_map = {
        "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X", "NZDUSD": "NZDUSD=X",
        "CL=F": "CL=F", "GC=F": "GC=F", "SI=F": "SI=F", "NG=F": "NG=F",
        "SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM", "DIA": "DIA",
        "ES=F": "ES=F", "NQ=F": "NQ=F",
    }
    sym_upper = symbol.upper().replace("-", "").replace("/", "")
    yahoo_sym = yahoo_map.get(sym_upper, sym_upper)
    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}",
            params={"interval": "1d", "range": "2d"},
            headers={"User-Agent": "Mozilla/5.0"}, timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                price = meta.get("regularMarketPrice", 0)
                prev = meta.get("previousClose", price)
                change = ((price - prev) / prev * 100) if prev else 0
                return {"price": price, "change_24h": round(change, 2), "symbol": yahoo_sym}
    except Exception:
        pass
    return None


def _get_live_price(symbol: str) -> dict | None:
    """Try Binance first, then Yahoo for forex/equities."""
    result = _fetch_live_price(symbol)
    if result and result["price"] > 0:
        return result
    return _fetch_forex_price(symbol)


def _compute_pick_score(pick: dict, system_stats: dict = None) -> dict:
    """
    Python port of computeScore() from audit_dashboard/template.html.
    Returns {score, breakdown, entry_status, entry_drift}.
    """
    breakdown = {}

    # 1. Strategy Performance (20%)
    fwd_wr = pick.get("strat_wr", pick.get("strat_fwd_wr", 0)) or 0
    if isinstance(fwd_wr, (int, float)) and fwd_wr <= 1:
        fwd_wr *= 100  # normalize to percentage
    fwd_pf = pick.get("strat_fwd_pf", pick.get("profit_factor", 0)) or 0
    health = pick.get("strat_health", "unknown")
    perf_base = min(100, fwd_wr * 0.6 + min(fwd_pf, 3) / 3 * 100 * 0.4)
    health_mult = {"healthy": 1.0, "watch": 0.75, "degraded": 0.4}.get(health, 0.5)
    breakdown["strategy"] = round(perf_base * health_mult)

    # 2. Signal Quality (20%)
    conf = (pick.get("confidence", 0) or 0)
    if conf <= 1:
        conf *= 100
    entry = float(pick.get("entry_price", 0) or 0)
    tp = float(pick.get("take_profit", pick.get("tp_price", 0)) or 0)
    sl = float(pick.get("stop_loss", pick.get("sl_price", 0)) or 0)
    rr_score = 50
    rr_val = 0
    if entry and tp and sl:
        rr_val = abs(tp - entry) / (abs(entry - sl) or 1)
        rr_score = min(100, rr_val * 40)
    breakdown["signal"] = round(conf * 0.6 + rr_score * 0.4)

    # 3. Freshness (20%)
    age_hours = pick.get("age_hours", 999)
    if age_hours == 999 and pick.get("timestamp"):
        try:
            ts = pick["timestamp"]
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        except Exception:
            age_hours = 999
    freshness = max(0, min(100,
        100 if age_hours <= 1 else
        85 if age_hours <= 4 else
        65 if age_hours <= 12 else
        45 if age_hours <= 24 else
        25 if age_hours <= 48 else 10
    ))
    breakdown["freshness"] = round(freshness)

    # 4. Forward Performance (10%)
    fwd_score = 50
    sys_id = pick.get("system_id", pick.get("system", pick.get("source_system", "")))
    if system_stats and sys_id in system_stats:
        ss = system_stats[sys_id]
        if ss.get("closed", 0) >= 5:
            wr_s = min(100, (ss.get("wr", 0)) * 1.2)
            pf_s = min(100, (ss.get("pf", 1) - 0.5) * 100)
            exp_s = min(100, max(0, (ss.get("exp", 0) + 5) * 10))
            fwd_score = round(wr_s * 0.5 + pf_s * 0.3 + exp_s * 0.2)
    breakdown["forward"] = max(0, min(100, fwd_score))

    # 5. Consensus (10%)
    agree = pick.get("agreeing_systems", pick.get("agreement_count", 0)) or 0
    breakdown["consensus"] = min(100, agree * 35)

    # 6. No-conflict (20%)
    has_conflict = pick.get("conflict", pick.get("has_conflict", False))
    breakdown["noConflict"] = 0 if has_conflict else 100

    # Weighted raw score
    raw = round(
        breakdown["strategy"] * 0.20 +
        breakdown["signal"] * 0.20 +
        breakdown["freshness"] * 0.20 +
        breakdown["forward"] * 0.10 +
        breakdown["consensus"] * 0.10 +
        breakdown["noConflict"] * 0.20
    )

    # Entry drift penalty (based on current PnL vs entry)
    pnl_pct = pick.get("pnl_pct", pick.get("unrealized_pnl_pct", 0)) or 0
    if abs(pnl_pct) > 1 and abs(pnl_pct) < 100:
        pass  # already percentage
    elif abs(pnl_pct) <= 1:
        pnl_pct *= 100  # was decimal

    entry_drift = 1.0
    entry_status = "IDEAL"
    if pnl_pct < -3:
        entry_drift = 0.3
        entry_status = "UNDERWATER"
    elif pnl_pct < -2:
        entry_drift = 0.5
        entry_status = "LOSING"
    elif pnl_pct < -1:
        entry_drift = 0.7
        entry_status = "SLIPPING"
    elif pnl_pct > 8:
        entry_drift = 0.4
        entry_status = "WAY_PAST"
    elif pnl_pct > 5:
        entry_drift = 0.6
        entry_status = "LATE"
    elif pnl_pct > 3:
        entry_drift = 0.85
        entry_status = "RUNNING"

    # Time decay
    time_decay = (
        1.0 if age_hours <= 2 else
        0.95 if age_hours <= 6 else
        0.85 if age_hours <= 12 else
        0.70 if age_hours <= 24 else
        0.55 if age_hours <= 36 else
        0.40 if age_hours <= 48 else 0.25
    )

    # Conflict penalty
    conflict_penalty = 0.7 if has_conflict else 1.0

    final = round(raw * entry_drift * time_decay * conflict_penalty)
    final = max(0, min(100, final))

    return {
        "score": final,
        "breakdown": breakdown,
        "entry_status": entry_status,
        "entry_drift": round(entry_drift * 100),
        "time_decay": round(time_decay * 100),
        "rr": round(rr_val, 2),
        "age_hours": round(age_hours, 1),
        "pnl_pct": round(pnl_pct, 2),
    }


def _load_all_active_picks() -> list[dict]:
    """Load active picks from all major systems."""
    picks = []
    systems = {
        "alpha_engine": "alpha_engine/data/active_picks.json",
        "baby_battleground": "battleground/data/active_picks.json",
        "kimi_claw": "KIMI_RISEOFTHECLAW/data/active_picks.json",
        "crypto_signal": "crypto_signal_engine/data/active_picks.json",
        "paper_trading": "paper_trading/data/active_picks.json",
        "multi_asset": "multi_asset/data/active_picks.json",
        "institutional": "multi_asset/data/institutional_picks.json",
        "mercury2": "mercury2/data/active_picks.json",
        "ml_system_b": "ml_battleground/system_b_regime/data/active_picks.json",
        "ml_system_c": "ml_battleground/system_c_deeplearn/data/active_picks.json",
        "ml_system_d": "ml_battleground/system_d_carry/data/active_picks.json",
        "ml_system_e": "ml_battleground/system_e_momentum/data/active_picks.json",
        "breakout_a": "breakout_arena/approach_a_sr_breakout/data/active_picks.json",
        "breakout_b": "breakout_arena/approach_b_ml_breakout/data/active_picks.json",
        "coinglass": "coinglass_strategies/data/active_picks.json",
        "crypto_ml_edge": "crypto_ml_edge/data/active_picks.json",
    }

    for sys_id, rel_path in systems.items():
        fpath = PROJECT_ROOT / rel_path
        if not fpath.exists():
            continue
        try:
            with open(fpath) as f:
                data = json.load(f)
            # Handle both list and {picks: [...]} formats
            if isinstance(data, list):
                sys_picks = data
            elif isinstance(data, dict):
                sys_picks = data.get("picks", data.get("active", []))
            else:
                continue
            for p in sys_picks:
                if p.get("status", "OPEN").upper() not in ("OPEN", "ACTIVE", "PENDING"):
                    continue
                p.setdefault("system_id", sys_id)
                p.setdefault("source_system", sys_id)
                picks.append(p)
        except Exception as e:
            print(f"[BESTPICKS] Error loading {sys_id}: {e}")
    return picks


def _fmt_price_bot(val):
    """Format price for Discord display."""
    if val is None or val == 0:
        return "$0"
    val = float(val)
    if val >= 1000:
        return f"${val:,.2f}"
    elif val >= 1:
        return f"${val:.4f}"
    elif val >= 0.001:
        return f"${val:.6f}"
    else:
        return f"${val:.10f}"


def _entry_window_analysis(pick: dict, live_price: float) -> dict:
    """Analyze if a pick is still in a good entry window."""
    entry = float(pick.get("entry_price", 0) or 0)
    tp = float(pick.get("take_profit", pick.get("tp_price", 0)) or 0)
    sl = float(pick.get("stop_loss", pick.get("sl_price", 0)) or 0)
    direction = (pick.get("direction", "") or "").upper()

    if not entry or not live_price:
        return {"verdict": "NO_DATA", "room_pct": 0, "pnl_pct": 0, "emoji": "❓"}

    # PnL from entry
    if direction in ("LONG", "BUY"):
        pnl_pct = (live_price - entry) / entry * 100
    else:
        pnl_pct = (entry - live_price) / entry * 100

    # Room to TP
    room_pct = 0
    if tp and entry:
        if direction in ("LONG", "BUY"):
            total_range = tp - entry
            used = live_price - entry
        else:
            total_range = entry - tp
            used = entry - live_price
        if total_range > 0:
            room_pct = max(0, (1 - used / total_range)) * 100

    # Verdict
    if pnl_pct < -3:
        verdict, emoji = "UNDERWATER", "🔴"
    elif pnl_pct < -1:
        verdict, emoji = "DIPPED (better entry!)", "🟡"
    elif pnl_pct < 1:
        verdict, emoji = "AT ENTRY (ideal!)", "🟢"
    elif pnl_pct < 3:
        verdict, emoji = "CONFIRMED (still OK)", "🟢"
    elif pnl_pct < 5:
        verdict, emoji = "RUNNING (late entry)", "🟡"
    else:
        verdict, emoji = "MISSED (chasing)", "🔴"

    return {
        "verdict": verdict,
        "room_pct": round(room_pct, 1),
        "pnl_pct": round(pnl_pct, 2),
        "emoji": emoji,
    }


@bot.command(name='bestpicks', aliases=['best', 'top', 'topbuys', 'readytobuy'])
async def bestpicks(ctx, count: str = "10"):
    """Top scored picks ready to buy — live prices + entry window analysis."""
    loading = await ctx.send("🔍 Scanning all systems for best entry opportunities...")

    try:
        num = min(20, max(3, int(count)))
    except ValueError:
        num = 10

    # 1. Load picks from all systems
    all_picks = _load_all_active_picks()

    # Also try fc_crypto_pro_picks.json for pre-scored data
    fc_pro_file = PROJECT_ROOT / "data" / "fc_crypto_pro_picks.json"
    fc_pro_url = "https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/data/fc_crypto_pro_picks.json"
    fc_pro_data = None
    try:
        resp = requests.get(fc_pro_url, timeout=8)
        if resp.status_code == 200:
            fc_pro_data = resp.json()
    except Exception:
        pass
    if fc_pro_data is None and fc_pro_file.exists():
        try:
            with open(fc_pro_file) as f:
                fc_pro_data = json.load(f)
        except Exception:
            pass

    # Merge fc-pro picks (they have richer data like system WR, strat WR)
    seen_keys = set()
    merged = []
    if fc_pro_data and fc_pro_data.get("picks"):
        for p in fc_pro_data["picks"]:
            key = f"{p.get('symbol')}_{p.get('direction')}_{p.get('system_id', p.get('system', ''))}"
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append(p)
    for p in all_picks:
        key = f"{p.get('symbol')}_{p.get('direction')}_{p.get('system_id', p.get('source_system', ''))}"
        if key not in seen_keys:
            seen_keys.add(key)
            merged.append(p)

    if not merged:
        await loading.edit(content="❌ No active picks found across any system.")
        return

    # 2. Fetch live prices (batch unique symbols)
    unique_symbols = list({p.get("symbol", ""): True for p in merged if p.get("symbol")}.keys())
    live_prices = {}
    for sym in unique_symbols[:30]:  # cap to avoid rate limits
        price_data = _get_live_price(sym)
        if price_data:
            live_prices[sym] = price_data

    # 3. Score each pick with live price + entry window
    scored = []
    for p in merged:
        sym = p.get("symbol", "")
        lp = live_prices.get(sym)
        live = lp["price"] if lp else float(p.get("current_price", 0) or 0)

        # Update PnL with live price
        entry = float(p.get("entry_price", 0) or 0)
        direction = (p.get("direction", "") or "").upper()
        if live and entry:
            if direction in ("LONG", "BUY"):
                p["pnl_pct"] = (live - entry) / entry * 100
            else:
                p["pnl_pct"] = (entry - live) / entry * 100

        score_data = _compute_pick_score(p)
        window = _entry_window_analysis(p, live) if live else {"verdict": "NO_DATA", "emoji": "❓", "room_pct": 0, "pnl_pct": 0}

        scored.append({
            **p,
            "_score": score_data["score"],
            "_breakdown": score_data["breakdown"],
            "_entry_status": score_data["entry_status"],
            "_window": window,
            "_live_price": live,
            "_rr": score_data["rr"],
            "_age": score_data["age_hours"],
        })

    # 4. Sort by score, take top N
    scored.sort(key=lambda x: x["_score"], reverse=True)
    top = scored[:num]

    await loading.delete()

    # 5. Build Discord embeds
    now_est = datetime.now(timezone(timedelta(hours=-5))).strftime("%b %d %I:%M%p EST")

    # Summary embed
    buyable = sum(1 for p in top if p["_window"]["emoji"] == "🟢")
    embed = discord.Embed(
        title=f"🏆 Best {len(top)} Picks — Ready to Buy",
        description=(
            f"**{buyable}/{len(top)} in ideal entry window** | "
            f"Scanned {len(merged)} picks across {len(set(p.get('system_id', p.get('source_system', '')) for p in merged))} systems\n"
            f"Score = Strategy(20%) + Signal(20%) + Fresh(20%) + Forward(10%) + Consensus(10%) + NoConflict(20%)\n"
            f"Penalties: entry drift, time decay, conflict"
        ),
        color=0x22c55e,
    )
    embed.set_footer(text=f"Live prices from Binance | {now_est}")

    picks_text = []
    for i, p in enumerate(top, 1):
        sym = p.get("symbol", "???")
        direction = (p.get("direction", "") or "").upper()
        dir_emoji = "📈" if direction in ("LONG", "BUY") else "📉"
        score = p["_score"]
        w = p["_window"]
        live = p["_live_price"]
        entry = float(p.get("entry_price", 0) or 0)
        tp = float(p.get("take_profit", p.get("tp_price", 0)) or 0)
        sl = float(p.get("stop_loss", p.get("sl_price", 0)) or 0)
        sys_name = p.get("system_id", p.get("source_system", p.get("system", "?")))
        strat = p.get("strategy", "?")

        # Score bar (filled blocks out of 10)
        score_blocks = "█" * (score // 10) + "░" * (10 - score // 10)

        line = (
            f"**{i}. {dir_emoji} {sym} {direction}** — Score: **{score}**/100 `{score_blocks}`\n"
            f"   {w['emoji']} Entry: {w['verdict']} | PnL: {w['pnl_pct']:+.2f}% | Room to TP: {w['room_pct']:.0f}%\n"
            f"   💰 Live: {_fmt_price_bot(live)} | Entry: {_fmt_price_bot(entry)}"
        )
        if tp:
            line += f" | TP: {_fmt_price_bot(tp)}"
        if sl:
            line += f" | SL: {_fmt_price_bot(sl)}"
        if p["_rr"] > 0:
            line += f" | R:R {p['_rr']}:1"
        line += f"\n   🏷️ {sys_name} / {strat}"
        if p["_age"] < 999:
            line += f" | ⏱️ {p['_age']:.0f}h ago"

        picks_text.append(line)

    # Split into pages if needed (Discord 4096 char limit)
    pages = []
    current = []
    current_len = 0
    for line in picks_text:
        if current_len + len(line) + 2 > 3500:
            pages.append("\n\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line) + 2
    if current:
        pages.append("\n\n".join(current))

    if pages:
        embed.description += "\n\n" + pages[0]
    await ctx.send(embed=embed)

    for extra_page in pages[1:]:
        page_embed = discord.Embed(description=extra_page, color=0x22c55e)
        await ctx.send(embed=page_embed)


@bot.command(name='check', aliases=['price', 'lookup', 'entry'])
async def check_symbol(ctx, *, symbols: str = ""):
    """Check live price + entry window for any symbol. Usage: !check BTC ETH SOL"""
    if not symbols.strip():
        await ctx.reply(
            "**Usage:** `!check BTC ETH SOL` — check live prices\n"
            "Also compares against any open picks for those symbols."
        )
        return

    symbol_list = [s.strip().upper() for s in symbols.replace(",", " ").split() if s.strip()][:10]
    loading = await ctx.send(f"🔍 Checking {', '.join(symbol_list)}...")

    # Load active picks to cross-reference
    all_picks = _load_all_active_picks()
    picks_by_sym = {}
    for p in all_picks:
        sym = (p.get("symbol", "") or "").upper().replace("-", "").replace("/", "")
        picks_by_sym.setdefault(sym, []).append(p)

    lines = []
    for sym_input in symbol_list:
        # Normalize symbol for lookup
        sym_norm = sym_input.replace("-", "").replace("/", "")
        if not sym_norm.endswith("USDT") and not sym_norm.endswith("USD"):
            sym_lookup = sym_norm + "USDT"
        else:
            sym_lookup = sym_norm

        price_data = _get_live_price(sym_input)
        if not price_data or price_data["price"] <= 0:
            lines.append(f"❌ **{sym_input}** — price not found")
            continue

        live = price_data["price"]
        change = price_data["change_24h"]
        change_emoji = "📈" if change >= 0 else "📉"

        line = f"{change_emoji} **{sym_input}** — {_fmt_price_bot(live)} ({change:+.2f}% 24h)"

        # Check if we have active picks for this symbol
        matching_picks = picks_by_sym.get(sym_lookup, []) + picks_by_sym.get(sym_norm, [])
        if matching_picks:
            for p in matching_picks[:3]:  # max 3 picks per symbol
                direction = (p.get("direction", "") or "").upper()
                entry = float(p.get("entry_price", 0) or 0)
                tp = float(p.get("take_profit", p.get("tp_price", 0)) or 0)
                sl = float(p.get("stop_loss", p.get("sl_price", 0)) or 0)
                sys_name = p.get("system_id", p.get("source_system", p.get("system", "?")))
                window = _entry_window_analysis(p, live)

                pick_line = (
                    f"   └ {window['emoji']} **{direction}** by {sys_name}: "
                    f"Entry {_fmt_price_bot(entry)}"
                )
                if tp:
                    pick_line += f" → TP {_fmt_price_bot(tp)}"
                if sl:
                    pick_line += f" / SL {_fmt_price_bot(sl)}"
                pick_line += f" | {window['verdict']} ({window['pnl_pct']:+.2f}%)"
                line += "\n" + pick_line
        else:
            line += "\n   └ No active picks for this symbol"

        lines.append(line)

    await loading.delete()

    embed = discord.Embed(
        title=f"💰 Live Price Check — {len(symbol_list)} Symbol(s)",
        description="\n\n".join(lines),
        color=0x06b6d4,
    )
    now_est = datetime.now(timezone(timedelta(hours=-5))).strftime("%b %d %I:%M%p EST")
    embed.set_footer(text=f"Binance + Yahoo Finance | {now_est}")
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────────────────────────
# Hourly Auto-Announce — New Quant Lab Commands
# ─────────────────────────────────────────────────────────────────

QUANT_ANNOUNCEMENTS = [
    {
        "title": "📊 Try `!edge` — Which strategies are making money?",
        "desc": (
            "Get a simple report card for every strategy.\n\n"
            "See the **average profit per trade**, how risky it is, and a clear verdict: "
            "EDGE (keep it), MARGINAL (watch it), TRAP (looks good but isn't), or DEAD (stop using it).\n\n"
            "**Try it now:** `!edge`\n"
            "**New here?** Type `!quant-help` for a full guide"
        ),
        "color": 0x22c55e,
    },
    {
        "title": "🔬 Try `!regime` — Are your strategies too similar?",
        "desc": (
            "If all your strategies do the same thing, **one bad day could hurt everything**.\n\n"
            "This checks if your strategies are diversified (doing different things) "
            "or overlapping (all copying each other). Also shows which work in calm vs wild markets.\n\n"
            "**Try it now:** `!regime`\n"
            "**New here?** Type `!quant-help` for a full guide"
        ),
        "color": 0x8b5cf6,
    },
    {
        "title": "🔥 Try `!stress 1000` — What if the market crashes?",
        "desc": (
            "We test your portfolio against **real disaster scenarios**: a 70% crypto crash, "
            "regulatory bans, liquidity freezes, and more.\n\n"
            "See exactly how much you'd lose in each scenario. "
            "Replace 1000 with your own budget.\n\n"
            "**Try it now:** `!stress 1000`\n"
            "**New here?** Type `!quant-help` for a full guide"
        ),
        "color": 0xef4444,
    },
    {
        "title": "💎 Try `!gems` — Find secretly profitable strategies",
        "desc": (
            "Some strategies win less than half the time but are **still profitable** "
            "because their wins are way bigger than their losses.\n\n"
            "Think of it like fishing — you don't catch one every time, "
            "but when you do, it's a big one!\n\n"
            "**Try it now:** `!gems`\n"
            "**New here?** Type `!quant-help` for a full guide"
        ),
        "color": 0xeab308,
    },
    {
        "title": "🛡️ Try `!compliance 1000` — Which coins are safe?",
        "desc": (
            "Not all coins are equal. Some can be **manipulated by big players** (whales).\n\n"
            "This screens every coin for safety and tells you how to split your budget — "
            "never more than 5% in one coin, and meme coins capped at 2%.\n\n"
            "**Try it now:** `!compliance 1000`\n"
            "**New here?** Type `!quant-help` for a full guide"
        ),
        "color": 0x3b82f6,
    },
    {
        "title": "🚨 Try `!alerts` — Should you stop trading something?",
        "desc": (
            "Instant health check for all your strategies.\n\n"
            "Flags anything that's **losing too much**, too risky, or where the numbers say "
            "you should stop. Think of it like a check-engine light for your portfolio.\n\n"
            "**Try it now:** `!alerts`\n"
            "**New here?** Type `!quant-help` for a full guide"
        ),
        "color": 0xf59e0b,
    },
    {
        "title": "🎰 Try `!ruin` — Could you go broke?",
        "desc": (
            "We simulate **3,000 possible futures** to answer: if you keep trading, "
            "what are the chances you'd lose half your money?\n\n"
            "Tests budgets from $200 to $5,000 and shows your most likely outcome.\n\n"
            "**Try it now:** `!ruin`\n"
            "**New here?** Type `!quant-help` for a full guide"
        ),
        "color": 0x6366f1,
    },
    {
        "title": "🔄 Try `!walkforward` — Is it skill or luck?",
        "desc": (
            "A strategy that only worked last month might just be **lucky**.\n\n"
            "We split your trade history into 3 time periods. If a strategy made money "
            "in ALL of them, it's real skill. If only some — it might be luck.\n\n"
            "**Try it now:** `!walkforward`\n"
            "**New here?** Type `!quant-help` for a full guide"
        ),
        "color": 0x06b6d4,
    },
]

_announce_index = 0


async def hourly_quant_announce():
    """Send one quant lab command announcement per hour, rotating through all 8."""
    global _announce_index
    await bot.wait_until_ready()

    # Wait 5 minutes after startup before first announcement
    await asyncio.sleep(300)

    while not bot.is_closed():
        if ML_CHANNEL_ID:
            channel = bot.get_channel(ML_CHANNEL_ID)
            if channel:
                ann = QUANT_ANNOUNCEMENTS[_announce_index % len(QUANT_ANNOUNCEMENTS)]
                embed = discord.Embed(
                    title=ann["title"],
                    description=ann["desc"],
                    color=ann["color"],
                )
                embed.set_footer(text="🆕 Quant Lab v3.0 — Mercury/Inception Labs Framework | Rotates hourly")
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"[BOT] Announce error: {e}")

                _announce_index += 1

        await asyncio.sleep(3600)  # Wait 1 hour


@bot.event
async def on_ready():
    print(f'{bot.user} logged in | ML Channel: {ML_CHANNEL_ID}')
    print(f'Commands: !refresh, !dashboard, !status, !update, !fc-pro, !fc-bundle, !fc-baby, !fc-fresh, !bestpicks, !check')
    print(f'Quant Lab: !edge, !regime, !stress, !ruin, !gems, !compliance, !alerts, !walkforward, !quant-help')
    bot.loop.create_task(hourly_quant_announce())


if __name__ == "__main__":
    try:
        bot.run(DISCORD_BOT_TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        print("[WARN] Message Content Intent not enabled — falling back to mention prefix (@bot command)")
        print("[WARN] Enable Message Content Intent at https://discord.com/developers/applications/ for ! prefix commands")
        intents.message_content = False
        # Recreate bot without privileged intent — users must @mention the bot
        bot2 = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

        # Re-register all commands on the fallback bot
        import copy
        for cmd in list(bot.commands):
            bot2.add_command(copy.copy(cmd))

        @bot2.event
        async def on_ready():
            print(f'{bot2.user} logged in (MENTION-ONLY MODE) | ML Channel: {ML_CHANNEL_ID}')
            print(f'Commands: @{bot2.user.name} fc-pro, @{bot2.user.name} refresh, etc.')
            # Notify the channel that ! prefix won't work
            if ML_CHANNEL_ID:
                ch = bot2.get_channel(ML_CHANNEL_ID)
                if ch:
                    try:
                        await ch.send(
                            "⚠️ **Bot running in mention-only mode** — `!` prefix commands won't work.\n"
                            f"Use `@{bot2.user.name} spam-picks` instead of `!spam`.\n"
                            "To fix: enable **Message Content Intent** at "
                            "<https://discord.com/developers/applications/>"
                        )
                    except Exception:
                        pass

        bot2.run(DISCORD_BOT_TOKEN)