#!/usr/bin/env python3
"""
Contested Pick Checker — Hourly price tracker for AI-disagreed picks.
Fetches live Binance prices, records hourly snapshots, determines winner.
Updates contested_picks_tracker.json and appends findings to CHATWITHIT.md
when a pick is resolved (>1% move sustained or 72h elapsed).

Also applies historical lessons learned to annotate each check with
which data source SHOULD be trusted based on past accuracy.
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKER_PATH = os.path.join(SCRIPT_DIR, "data", "contested_picks_tracker.json")
LESSONS_PATH = os.path.join(SCRIPT_DIR, "data", "conflict_lessons_learned.json")
CHATWITHIT_PATH = os.path.join(SCRIPT_DIR, "..", "docs", "CHATWITHIT.md")
BINANCE_API = "https://api.binance.com/api/v3/ticker/price?symbol="

# 72-hour resolution window
RESOLUTION_HOURS = 72
# Thresholds
WIN_PCT = 1.0
LOSS_PCT = -1.0

# ---------------------------------------------------------------------------
# CONFLICT RESOLUTION RULES — derived from historical PnL data
# See conflict_lessons_learned.json for full documentation.
# ---------------------------------------------------------------------------
# Trust hierarchy (by proven WR + PnL):
#   1. Battleground DNA (65.2% WR, +105%)
#   2. Cross-Agg SUPER 4+ systems (57.5% WR, +64%)
#   3. Mega Mutation MACD_RSI (77-88% WR, Sharpe 5-8)
#   4. System F Fear Contrarian (52.5% WR, +41%) — first bounce only
#   5. LuxAlgo SELL (valid 24-48h scalp when RSI>70, large-caps only)
# Never trust: System A/B (5.3% WR), stale predictions, KIMI standalone (20% WR)
# ---------------------------------------------------------------------------

TRUST_HIERARCHY = {
    "battleground": {"rank": 1, "wr": 0.652, "pnl": 105.30, "trades": 210},
    "cross_agg_super": {"rank": 2, "wr": 0.575, "pnl": 64.28, "trades": 40},
    "mega_mutation_macd_rsi": {"rank": 3, "wr": 0.833, "pnl": None, "trades": 7},
    "system_f": {"rank": 4, "wr": 0.525, "pnl": 41.01, "trades": 59},
    "luxalgo_sell": {"rank": 5, "wr": None, "pnl": None, "trades": 15},
    "alpha_engine_short": {"rank": 6, "wr": 0.667, "pnl": 18.40, "trades": 6},
}

NEVER_TRUST = {
    "system_a": {"wr": 0.053, "pnl": -62.49},
    "system_b": {"wr": 0.053, "pnl": -64.15},
    "predictions_stale": {"wr": None, "pnl": None, "note": "324 old picks, massive drawdowns"},
    "kimi_standalone": {"wr": 0.200, "pnl": -125.38},
    "paper_trading": {"wr": 0.382, "pnl": -124.45},
}


def fetch_price(symbol: str) -> float | None:
    """Fetch current price from Binance."""
    try:
        url = f"{BINANCE_API}{symbol}"
        req = urllib.request.Request(url, headers={"User-Agent": "ContestTracker/1.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        return float(data["price"])
    except Exception as e:
        print(f"  [WARN] Failed to fetch {symbol}: {e}")
        return None


def pct_change(baseline: float, current: float) -> float:
    """Calculate percentage change."""
    if baseline == 0:
        return 0.0
    return ((current - baseline) / baseline) * 100


def determine_winner(pick: dict, change_pct: float) -> tuple[str | None, str]:
    """
    Determine if there's a winner based on price movement.
    Returns (winner_name, explanation) or (None, reason).
    """
    claude = pick["claude_call"].upper()
    antigravity = pick["antigravity_call"].upper()

    # Check if either side is validated
    if change_pct > WIN_PCT:
        # Price went UP — LONG callers win
        long_callers = []
        short_callers = []
        if claude in ("LONG", "LEAN_BUY", "BUY"):
            long_callers.append("CLAUDE")
        if claude in ("SELL", "SHORT"):
            short_callers.append("CLAUDE")
        if antigravity in ("LONG", "LEAN_BUY", "BUY"):
            long_callers.append("ANTIGRAVITY")
        if antigravity in ("SELL", "SHORT"):
            short_callers.append("ANTIGRAVITY")

        if long_callers and short_callers:
            winners = " + ".join(long_callers)
            losers = " + ".join(short_callers)
            return winners, f"Price UP {change_pct:+.2f}% — {winners} (LONG) correct, {losers} (SHORT) wrong"
        elif long_callers:
            return " + ".join(long_callers), f"Price UP {change_pct:+.2f}% — {' + '.join(long_callers)} LONG validated"
        else:
            return None, f"Price UP {change_pct:+.2f}% but neither called LONG clearly"

    elif change_pct < LOSS_PCT:
        # Price went DOWN — SHORT/SELL callers win
        short_callers = []
        long_callers = []
        if claude in ("SELL", "SHORT", "AVOID"):
            short_callers.append("CLAUDE")
        if claude in ("LONG", "LEAN_BUY", "BUY"):
            long_callers.append("CLAUDE")
        if antigravity in ("SELL", "SHORT", "AVOID", "HOLD"):
            short_callers.append("ANTIGRAVITY")
        if antigravity in ("LONG", "LEAN_BUY", "BUY"):
            long_callers.append("ANTIGRAVITY")

        if short_callers and long_callers:
            winners = " + ".join(short_callers)
            losers = " + ".join(long_callers)
            return winners, f"Price DOWN {change_pct:+.2f}% — {winners} (SELL/AVOID) correct, {losers} (LONG) wrong"
        elif short_callers:
            return " + ".join(short_callers), f"Price DOWN {change_pct:+.2f}% — {' + '.join(short_callers)} SELL validated"
        else:
            return None, f"Price DOWN {change_pct:+.2f}% but neither called SHORT clearly"

    else:
        # Within +/-1% — NEUTRAL/AVOID callers are vindicated
        neutral_callers = []
        if claude in ("AVOID", "NEUTRAL", "CAUTION"):
            neutral_callers.append("CLAUDE")
        if antigravity in ("NEUTRAL", "HOLD", "AVOID"):
            neutral_callers.append("ANTIGRAVITY")
        return None, f"Price flat at {change_pct:+.2f}% — no clear winner yet"


def apply_lessons(pick: dict, change_pct: float, hours_elapsed: float) -> str:
    """
    Apply historical lessons learned to annotate which caller the data
    suggests should be trusted, and why.
    Returns a short annotation string.
    """
    reasoning = pick.get("claude_reasoning", "") + " " + pick.get("antigravity_reasoning", "")
    reasoning_lower = reasoning.lower()
    notes = []

    # Rule 1: If stale predictions inflated BUY consensus, discount it
    if "stale" in reasoning_lower or "predictions" in reasoning_lower:
        notes.append("RULE1(recency>count): stale BUY consensus discounted")

    # Rule 2: If LuxAlgo SELL + RSI>70, valid short-term (24-48h)
    if "luxalgo" in reasoning_lower and "rsi" in reasoning_lower:
        if hours_elapsed <= 48:
            notes.append("RULE2(LuxAlgo-RSI): SELL valid for 24-48h scalp window")
        else:
            notes.append("RULE2(LuxAlgo-RSI): past 48h scalp window, medium-term trend may override")

    # Rule 3: Mega Mutation MACD_RSI picks override LuxAlgo on altcoins
    if "mega mutation" in reasoning_lower or "tournament" in reasoning_lower:
        notes.append("RULE3(MegaMutation): tournament-proven picks (Sharpe 5-8) override short-term SELL on alts")

    # Rule 4: Hayes Liquidity = direction only, not entry timing
    if "hayes" in reasoning_lower:
        notes.append("RULE4(Hayes): macro direction correct but poor entry timing — use for bias not entries")

    # Rule 5: KIMI standalone (20% WR) only useful as confirmer
    if "kimi" in reasoning_lower:
        notes.append("RULE5(KIMI): standalone 20% WR — only trust when 3+ other systems agree")

    # Rule 6: Cross-agg SUPER (4+ systems) beats all individual signals
    if "cross-agg" in reasoning_lower or "consensus" in reasoning_lower or "7/11" in reasoning_lower or "6/11" in reasoning_lower:
        notes.append("RULE6(SUPER): 4+ system consensus (57.5% WR, +64% PnL) historically beats individual signals")

    # Rule 7: Check if price action is confirming or denying
    if hours_elapsed >= 6:
        if abs(change_pct) < 0.5:
            notes.append(f"PRICE_ACTION: flat after {hours_elapsed:.0f}h — neither side confirmed yet")
        elif change_pct > WIN_PCT:
            notes.append(f"PRICE_ACTION: sustained UP {change_pct:+.1f}% — LONG thesis gaining evidence")
        elif change_pct < LOSS_PCT:
            notes.append(f"PRICE_ACTION: sustained DOWN {change_pct:+.1f}% — SELL thesis gaining evidence")

    return " | ".join(notes) if notes else "No specific historical rule applies"


def check_resolution_time(pick: dict) -> bool:
    """Check if 72 hours have passed since baseline."""
    baseline_time = datetime.fromisoformat(pick["baseline_time"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - baseline_time).total_seconds() >= RESOLUTION_HOURS * 3600


def update_chatwithit(resolved_picks: list[dict]):
    """Append resolution summary to CHATWITHIT.md."""
    if not resolved_picks:
        return

    now_utc = datetime.now(timezone.utc)
    est = now_utc - timedelta(hours=4)
    timestamp_utc = now_utc.strftime("%H:%M UTC")
    timestamp_est = est.strftime("%H:%M EST")
    date_str = now_utc.strftime("%Y-%m-%d")

    entry_lines = [
        f"\n## [SYSTEM] {date_str} ~{timestamp_utc} (~{timestamp_est}) — CONTESTED PICK RESOLUTION\n",
        "",
        "| Symbol | Baseline | Final | Change | Winner | Explanation |",
        "|--------|----------|-------|--------|--------|-------------|",
    ]

    for p in resolved_picks:
        checks = p.get("hourly_checks", [])
        final_price = checks[-1]["price"] if checks else p["baseline_price"]
        change = pct_change(p["baseline_price"], final_price)
        entry_lines.append(
            f"| {p['symbol']} | ${p['baseline_price']:,.2f} | ${final_price:,.2f} "
            f"| {change:+.2f}% | {p.get('winner', 'TBD')} | {p.get('resolution', 'N/A')} |"
        )

    entry_lines.append("")

    # Add lessons learned section
    entry_lines.append("### Lessons Validated/Busted")
    entry_lines.append("")
    for p in resolved_picks:
        lessons = p.get("lessons_validated", "N/A")
        entry_lines.append(f"- **{p['symbol']}**: {lessons}")
    entry_lines.append("")
    entry_lines.append("---\n")
    entry_text = "\n".join(entry_lines)

    # Insert after the protocol line
    try:
        with open(CHATWITHIT_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        marker = "Tag with [CLAUDE], [ANTIGRAVITY], [GROK], [MERCURY], or [KILO-CODE].\n"
        idx = content.find(marker)
        if idx != -1:
            insert_pos = idx + len(marker)
            content = content[:insert_pos] + entry_text + content[insert_pos:]
            with open(CHATWITHIT_PATH, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  [OK] Updated CHATWITHIT.md with {len(resolved_picks)} resolution(s)")
    except Exception as e:
        print(f"  [WARN] Could not update CHATWITHIT.md: {e}")


def _summarize_lessons(pick: dict) -> str:
    """Summarize which historical rules were validated or busted by the outcome."""
    checks = pick.get("hourly_checks", [])
    if not checks:
        return "No data"

    final_change = checks[-1].get("change_pct", 0)
    annotations = [c.get("lesson_annotation", "") for c in checks if c.get("lesson_annotation")]
    reasoning = (pick.get("claude_reasoning", "") + " " + pick.get("antigravity_reasoning", "")).lower()

    findings = []

    # Did LuxAlgo short-term SELL play out?
    if "luxalgo" in reasoning:
        # Check if price dropped within first 48h
        early_checks = [c for c in checks if c.get("hours_elapsed", 0) <= 48]
        if early_checks:
            min_price_change = min(c.get("change_pct", 0) for c in early_checks)
            if min_price_change < -1.0:
                findings.append(f"VALIDATED: LuxAlgo SELL correct short-term (dropped {min_price_change:.1f}% within 48h)")
            else:
                findings.append("BUSTED: LuxAlgo SELL did NOT produce >1% drop within 48h")

    # Did SUPER consensus hold?
    if "6/11" in reasoning or "7/11" in reasoning:
        if final_change > 1.0:
            findings.append("VALIDATED: Multi-system LONG consensus was correct")
        elif final_change < -1.0:
            findings.append("BUSTED: Multi-system LONG consensus failed — fresh SELL was right")

    # Did stale predictions mislead?
    if "stale" in reasoning:
        findings.append("NOTE: Recency-weighted analysis should replace raw system count")

    if not findings:
        if final_change > 1.0:
            findings.append(f"LONG callers were correct ({final_change:+.1f}%)")
        elif final_change < -1.0:
            findings.append(f"SELL callers were correct ({final_change:+.1f}%)")
        else:
            findings.append(f"Inconclusive ({final_change:+.1f}%)")

    return " | ".join(findings)


def run_check():
    """Main hourly check routine."""
    print(f"\n{'='*60}")
    print(f"CONTESTED PICK CHECKER — {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}")

    # Load tracker
    if not os.path.exists(TRACKER_PATH):
        print("[ERROR] Tracker file not found:", TRACKER_PATH)
        sys.exit(1)

    with open(TRACKER_PATH, "r", encoding="utf-8") as f:
        tracker = json.load(f)

    newly_resolved = []
    active_count = 0
    resolved_count = 0

    for pick in tracker["contested_picks"]:
        symbol = pick["symbol"]

        # Skip already resolved
        if pick["resolution"] is not None:
            resolved_count += 1
            continue

        active_count += 1

        # Fetch current price
        current_price = fetch_price(symbol)
        if current_price is None:
            print(f"  [{symbol}] Skipped — price fetch failed")
            continue

        change_pct = pct_change(pick["baseline_price"], current_price)
        hours_elapsed = (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(pick["baseline_time"].replace("Z", "+00:00"))
        ).total_seconds() / 3600

        # Apply lessons learned
        lesson_note = apply_lessons(pick, change_pct, hours_elapsed)

        # Record hourly check
        check_entry = {
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "price": current_price,
            "change_pct": round(change_pct, 4),
            "hours_elapsed": round(hours_elapsed, 1),
            "lesson_annotation": lesson_note,
        }
        pick["hourly_checks"].append(check_entry)

        print(f"  [{symbol}] ${current_price:,.4f} | {change_pct:+.2f}% from baseline ${pick['baseline_price']:,.4f} | {hours_elapsed:.1f}h elapsed")
        print(f"    Claude: {pick['claude_call']} | Antigravity: {pick['antigravity_call']}")
        print(f"    Lessons: {lesson_note}")

        # Check for resolution
        winner, explanation = determine_winner(pick, change_pct)
        time_expired = check_resolution_time(pick)

        # Resolve if: clear winner with sustained move OR time expired
        sustained_checks = sum(
            1 for c in pick["hourly_checks"]
            if abs(c["change_pct"]) > WIN_PCT
        )
        sustained = sustained_checks >= 3  # Need 3+ consecutive checks above threshold

        if winner and sustained:
            pick["winner"] = winner
            pick["resolution"] = explanation
            pick["lessons_validated"] = _summarize_lessons(pick)
            newly_resolved.append(pick)
            print(f"    >>> RESOLVED: {explanation}")
            print(f"    >>> Lessons: {pick['lessons_validated']}")
        elif time_expired:
            # Force resolve at 72h
            if winner:
                pick["winner"] = winner
                pick["resolution"] = f"[72h] {explanation}"
            else:
                # Determine by final direction
                if change_pct > 0.5:
                    pick["winner"] = "LEAN LONG callers"
                    pick["resolution"] = f"[72h] Price drifted UP {change_pct:+.2f}% — slight edge to LONG callers"
                elif change_pct < -0.5:
                    pick["winner"] = "LEAN SHORT callers"
                    pick["resolution"] = f"[72h] Price drifted DOWN {change_pct:+.2f}% — slight edge to SHORT callers"
                else:
                    pick["winner"] = "DRAW"
                    pick["resolution"] = f"[72h] Price flat at {change_pct:+.2f}% — neither side vindicated"
            pick["lessons_validated"] = _summarize_lessons(pick)
            newly_resolved.append(pick)
            print(f"    >>> TIME EXPIRED: {pick['resolution']}")
            print(f"    >>> Lessons: {pick['lessons_validated']}")
        else:
            print(f"    Status: tracking... ({len(pick['hourly_checks'])} checks so far)")

    # Save tracker
    with open(TRACKER_PATH, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2)

    print(f"\nSummary: {active_count} active, {resolved_count} resolved, {len(newly_resolved)} newly resolved")

    # Update CHATWITHIT.md if any picks resolved
    if newly_resolved:
        update_chatwithit(newly_resolved)

    return newly_resolved


if __name__ == "__main__":
    run_check()
