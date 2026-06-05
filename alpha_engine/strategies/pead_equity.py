"""
PEAD Equity Strategy — Post-Earnings Announcement Drift on EQUITY Top-100

Focuses on a short 2-day post-earnings window (not the 6-8 week hold of the
existing EarningsDriftStrategy). The 2-day window exploits the institutional
underreaction anomaly before HFT fully digests the surprise. Targets EQUITY
top-100 by market cap to avoid liquidity constraints.

Academic basis: Ball & Brown (1968), Bernard & Thomas (1990). AQR R3 from
supreme plan: "PEAD edge is real, not yet shipped." Partially supported by
existing incubator_picks.json earnings calendar.

Institutional goal: lift EQUITY PF 1.55 → 1.80+ (T2 → T1 candidate).

## Wiring Plan
NOT wired to production_scanner.py yet.
Wire condition: backtest must clear PF >= 1.5, WR >= 50%, n >= 50 on EQUITY cohort.
Target caller: alpha_engine/production_scanner.py::_run_equity_scanner()
Target PR: filed after 30-day paper-pilot clears thresholds.
Kill-switch: PEAD_EQUITY_ENABLED=0 (default 0 until wired).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

# 2-day window: day 0 (earnings day) + day 1 (drift confirmation)
# Academic: day 0 shows the initial surprise reaction; day 1 confirms
# institutional re-rating vs retail over-reaction fade.
PEAD_WINDOW_DAYS = 2

# Minimum earnings surprise to trigger a signal.
# 5% beat = clean institutional surprise with minimal noise contamination.
MIN_EARNINGS_BEAT_PCT = 0.05

# Require guidance raise (management conviction). Eliminates one-time beats.
# Shadow probation: PEAD_REQUIRE_GUIDANCE_RAISE=0 allows earnings-cache signals.
REQUIRE_GUIDANCE_RAISE = os.environ.get("PEAD_REQUIRE_GUIDANCE_RAISE", "1") == "1"

# Score thresholds — not wired to production until these are met in backtest.
MIN_PF_THRESHOLD = 1.5
MIN_WR_THRESHOLD = 0.50
MIN_SAMPLE_THRESHOLD = 50

# Universe: EQUITY top-100 S&P 500 components by market cap.
# Filtered at runtime from incubator_picks.json or yfinance screener.
EQUITY_TOP100_MAX = 100

# ── Main signal generator ─────────────────────────────────────────────────────


def generate_pead_signals(
    earnings_events: List[Dict[str, Any]],
    as_of: Optional[datetime] = None,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """Generate 2-day PEAD signals from post-earnings events.

    Args:
        earnings_events: List of dicts with keys:
            - symbol (str): ticker
            - earnings_date (str or datetime): announcement date
            - eps_actual (float): reported EPS
            - eps_estimate (float): consensus estimate
            - guidance_raised (bool): whether mgmt raised guidance
            - asset_class (str): should be "EQUITY"
            - market_cap_rank (int): rank in top-100 universe (1=largest)
        as_of: evaluation timestamp (default: now UTC)
        dry_run: if True, do not emit picks (returns signals with _dry_run=True)

    Returns:
        List of pick dicts ready for scoring pipeline injection.
        NOT wired to production_scanner — must pass backtest gates first.
    """
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    signals: List[Dict[str, Any]] = []
    window_cutoff = as_of - timedelta(days=PEAD_WINDOW_DAYS)

    for event in earnings_events:
        try:
            symbol = str(event.get("symbol", "") or "").upper().strip()
            if not symbol:
                continue

            # Only EQUITY class
            asset_class = str(event.get("asset_class", "EQUITY") or "EQUITY").upper()
            if asset_class != "EQUITY":
                continue

            # Top-100 universe filter
            rank = event.get("market_cap_rank")
            if rank is not None and int(rank) > EQUITY_TOP100_MAX:
                log.debug("PEAD skip %s: rank %d > top-%d", symbol, rank, EQUITY_TOP100_MAX)
                continue

            # Parse earnings date
            ed_raw = event.get("earnings_date")
            if ed_raw is None:
                continue
            if isinstance(ed_raw, str):
                ed_raw = ed_raw.replace("Z", "+00:00")
                earnings_dt = datetime.fromisoformat(ed_raw)
                if earnings_dt.tzinfo is None:
                    earnings_dt = earnings_dt.replace(tzinfo=timezone.utc)
            else:
                earnings_dt = ed_raw
                if earnings_dt.tzinfo is None:
                    earnings_dt = earnings_dt.replace(tzinfo=timezone.utc)

            # Must be within 2-day window
            if not (window_cutoff <= earnings_dt <= as_of):
                continue

            # Earnings surprise check
            eps_actual = float(event.get("eps_actual", 0) or 0)
            eps_estimate = float(event.get("eps_estimate", 0) or 0)
            if eps_estimate == 0:
                continue  # can't compute surprise safely
            beat_pct = (eps_actual - eps_estimate) / abs(eps_estimate)
            if beat_pct < MIN_EARNINGS_BEAT_PCT:
                log.debug("PEAD skip %s: beat=%.1f%% < %.1f%% threshold",
                          symbol, beat_pct * 100, MIN_EARNINGS_BEAT_PCT * 100)
                continue

            # Guidance requirement
            guidance_raised = bool(event.get("guidance_raised", False))
            if REQUIRE_GUIDANCE_RAISE and not guidance_raised:
                log.debug("PEAD skip %s: guidance not raised", symbol)
                continue

            # Score: higher beat + guidance raise = higher score
            base_score = 50  # baseline
            beat_bonus = min(20, int(beat_pct * 100))  # up to +20 pts for big beats
            guidance_bonus = 10 if guidance_raised else 0
            score = base_score + beat_bonus + guidance_bonus

            signal: Dict[str, Any] = {
                "symbol": symbol,
                "asset_class": "EQUITY",
                "strategy": "pead_equity_2day",
                "source_system": "pead_equity",
                "direction": "LONG",
                "signal_type": "LONG",
                "score": score,
                "confidence": min(0.80, 0.50 + beat_pct * 2),  # capped at 0.80
                "created_at": as_of.isoformat(),
                "earnings_date": earnings_dt.isoformat(),
                "eps_beat_pct": round(beat_pct * 100, 2),
                "guidance_raised": guidance_raised,
                "_pead_window_days": PEAD_WINDOW_DAYS,
                "_wired_to_production": False,  # explicit: not yet in production_scanner
            }
            if dry_run:
                signal["_dry_run"] = True

            signals.append(signal)
            log.info(
                "PEAD signal: %s beat=%.1f%% guidance=%s score=%d dry_run=%s",
                symbol, beat_pct * 100, guidance_raised, score, dry_run,
            )

        except Exception as exc:
            log.warning("PEAD signal error for event %s: %s", event, exc)
            continue

    log.info("PEAD equity: generated %d signals from %d events (as_of=%s)",
             len(signals), len(earnings_events), as_of.isoformat())
    return signals


# ── Backtest runner (standalone, not called by production_scanner) ─────────────


def run_backtest(
    earnings_history: List[Dict[str, Any]],
    price_data: Dict[str, Any],
    verbose: bool = False,
) -> Dict[str, Any]:
    """Standalone PEAD backtest — measures PF/WR/n before production wiring.

    Does NOT run automatically. Call explicitly:
        python -m alpha_engine.strategies.pead_equity --backtest

    Wire to production_scanner ONLY if result satisfies:
        PF >= {MIN_PF_THRESHOLD}, WR >= {MIN_WR_THRESHOLD}, n >= {MIN_SAMPLE_THRESHOLD}

    Returns dict with keys: pf, wr, n, trades (list of outcomes).
    """
    wins, losses, total = 0, 0, 0
    trades: List[Dict[str, Any]] = []

    for event in earnings_history:
        symbol = str(event.get("symbol", "") or "").upper()
        earnings_dt_raw = event.get("earnings_date")
        if not symbol or not earnings_dt_raw:
            continue

        signals = generate_pead_signals([event], as_of=None, dry_run=True)
        if not signals:
            continue

        # Look up 2-day forward return from price_data
        sym_prices = price_data.get(symbol, {})
        entry_price = sym_prices.get(str(earnings_dt_raw)[:10])
        exit_key = None
        if entry_price:
            try:
                entry_date = datetime.fromisoformat(str(earnings_dt_raw)[:10])
                exit_date = entry_date + timedelta(days=2)
                exit_key = exit_date.strftime("%Y-%m-%d")
            except Exception:
                pass

        exit_price = sym_prices.get(exit_key) if exit_key else None
        if not entry_price or not exit_price or entry_price <= 0:
            continue

        pnl_pct = (exit_price - entry_price) / entry_price * 100
        won = pnl_pct > 0
        if won:
            wins += 1
        else:
            losses += 1
        total += 1
        trades.append({
            "symbol": symbol,
            "eps_beat_pct": event.get("eps_beat_pct", 0),
            "pnl_pct": round(pnl_pct, 3),
            "won": won,
        })

        if verbose:
            log.info("BACKTEST %s pnl=%.2f%%", symbol, pnl_pct)

    wr = wins / total if total > 0 else 0.0
    avg_win = sum(t["pnl_pct"] for t in trades if t["won"]) / wins if wins > 0 else 0
    avg_loss = abs(sum(t["pnl_pct"] for t in trades if not t["won"])) / losses if losses > 0 else 1
    pf = (avg_win * wins) / (avg_loss * losses) if losses > 0 else float("inf")

    result = {
        "pf": round(pf, 3),
        "wr": round(wr, 4),
        "n": total,
        "wins": wins,
        "losses": losses,
        "avg_win_pct": round(avg_win, 3),
        "avg_loss_pct": round(avg_loss, 3),
        "production_eligible": pf >= MIN_PF_THRESHOLD and wr >= MIN_WR_THRESHOLD and total >= MIN_SAMPLE_THRESHOLD,
        "thresholds": {
            "min_pf": MIN_PF_THRESHOLD,
            "min_wr": MIN_WR_THRESHOLD,
            "min_n": MIN_SAMPLE_THRESHOLD,
        },
        "trades": trades,
    }
    log.info(
        "PEAD backtest: PF=%.2f WR=%.1f%% n=%d eligible=%s",
        pf, wr * 100, total, result["production_eligible"],
    )
    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if "--backtest" in sys.argv:
        log.info("PEAD backtest mode — provide earnings_history + price_data via caller.")
        log.info("Production wire condition: PF>=%.1f, WR>=%.0f%%, n>=%d",
                 MIN_PF_THRESHOLD, MIN_WR_THRESHOLD * 100, MIN_SAMPLE_THRESHOLD)
    else:
        log.info("PEAD equity strategy loaded. Use generate_pead_signals() with earnings events.")
        log.info("Kill-switch: PEAD_EQUITY_ENABLED=0 (default OFF until wired to production_scanner).")
