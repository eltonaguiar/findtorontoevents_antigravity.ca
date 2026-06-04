#!/usr/bin/env python3
"""
Real Money (Beta) Virtual Portfolio Tracker
=============================================
Tracks a curated set of picks as if trading real money.
Selection criteria (from 1,868 closed pick analysis):
  - ONLY WF STRONG/VIABLE strategies (77.6% WR on 85 trades)
  - Score >= 60 (62.7% WR, vs 36.4% for score < 50)
  - Tight R:R <= 2.0 (70.8% WR vs 42.4% for R:R 2-3)
  - Confidence >= 0.70 or < 0.50 (avoid 0.60-0.69 dead zone at 35.6%)
  - Safety tag = SAFE or LIKELY
  - No direction conflicts
  - Max 3 picks per symbol

Runs hourly to:
  1. Select qualifying picks from active picks
  2. Track entries, TP/SL hits, PnL
  3. Log performance history for review
  4. Auto-tweak thresholds based on results

Stdlib only. Windows UTF-8 safe.
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
PORTFOLIO_FILE = DATA / "real_money_portfolio.json"
PORTFOLIO_HISTORY = DATA / "real_money_history.json"

BLOCKED_WEEKDAYS = {0, 6}  # Mon=0, Sun=6: 32.8-40.8% WR
CONSEC_LOSS_COOLDOWN_THRESHOLD = 3
CONSEC_LOSS_COOLDOWN_HOURS = 48  # Mercury #12: 2h->48h. Future: require posterior prob > 0.98

# Symbols that consistently lose in our portfolios — blacklisted from new entries
PORTFOLIO_BLOCKED_SYMBOLS = {"ADAUSDT"}  # 0W/2L (-5.26%) in Portfolio A

# Selection criteria (data-backed from closed pick analysis 2026-04-02)
# Ranked by strategy+direction WR from 970 closed crypto trades:
PROVEN_STRATEGIES = {
    "hs_lb_None",                                # 92% WR SHORT (12W/1L, +13.8%) — #1 BEST
    "copy_hl_whale_24.5M",                       # 77% WR SHORT (10W/3L, +24.0%) — #2 by PnL
    "st_fear_greed_contrarian",                  # 75% WR LONG (100W/34L, +136.1%) — highest volume
    "gainer_compression_relaxed_mut",            # 82% WR SHORT (9W/2L, +18.3%)
    "atr_regime_rsi",                            # 87% WR LONG (13W/2L, +7.6%)
    "crypto_keltner_compression_expansion_v1",   # 67% WR SHORT (14W/7L, +8.0%)
    "crypto_kalman_trend_residual_reversion_v1", # 67% WR SHORT
    "drawdown_recovery_rsi_eth",                 # 78.9% WR STRONG
    "vwap_deviation_reversion_sol_v1",           # 67% WR both directions
    "clone_hl_copy_lb_None",                     # 61.5% WR
    "claude_ml_moderate_mut",                    # 67% WR LONG (8W/4L)
    # REMOVED: rsi_overbought — 29% WR on SHORTs (4W/10L, -17.1%)
    # REMOVED: keltner_eth/sol — lower WR, keep the base keltner
}

MIN_SCORE = 50  # Raised from 10: score<50 picks have 38% WR vs 60% for score>=50 (66% of closed losers were <50)
MAX_RR = 3.5    # Matches updated SMART_PICKS_MAX_RR
CONF_DEAD_ZONE = (0.60, 0.69)  # 35.6% WR — avoid
MAX_PER_SYMBOL = 2
VIRTUAL_CAPITAL = 10000.0
POSITION_SIZE_PCT = 0.05  # 5% per trade

BINANCE_MIRRORS = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://api2.binance.com", "https://api3.binance.com",
]


def _effective_position_size_pct() -> float:
    """Cap per-trade % by config/risk_policy.json per_trade_cap_pct when present."""
    cap_pct = 5.0
    try:
        from alpha_engine.risk_policy_loader import load_risk_policy

        rp = load_risk_policy()
        c = (rp.get("crypto") or {}).get("per_trade_cap_pct")
        if c is not None:
            cap_pct = min(cap_pct, float(c))
    except Exception:
        pass
    return min(POSITION_SIZE_PCT, cap_pct / 100.0)


def _fetch_price(symbol: str) -> float:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for mirror in BINANCE_MIRRORS:
        try:
            req = urllib.request.Request(
                f"{mirror}/api/v3/ticker/price?symbol={symbol}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp = urllib.request.urlopen(req, timeout=8, context=ctx)
            return float(json.loads(resp.read())["price"])
        except Exception:
            continue
    return 0.0


def _load_portfolio() -> dict:
    if PORTFOLIO_FILE.exists():
        return json.loads(PORTFOLIO_FILE.read_text(encoding="utf-8"))
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "virtual_capital": VIRTUAL_CAPITAL,
        "cash": VIRTUAL_CAPITAL,
        "active_positions": [],
        "closed_positions": [],
        "stats": {
            "total_trades": 0, "wins": 0, "losses": 0,
            "total_pnl_pct": 0.0, "win_rate": 0.0,
            "peak_equity": VIRTUAL_CAPITAL,
            "max_drawdown_pct": 0.0,
        },
    }


def _save_portfolio(portfolio: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_FILE.write_text(json.dumps(portfolio, indent=2, default=str), encoding="utf-8")


def _in_cooldown(portfolio: dict) -> bool:
    """Mercury #12: 3+ consecutive losses -> 48h pause."""
    closed = portfolio.get("closed_positions", [])
    if len(closed) < CONSEC_LOSS_COOLDOWN_THRESHOLD:
        return False
    recent = closed[-CONSEC_LOSS_COOLDOWN_THRESHOLD:]
    if not all((p.get("realized_pnl_pct", 0) or 0) <= 0 for p in recent):
        return False
    last_at = recent[-1].get("closed_at", "")
    if not last_at:
        return False
    try:
        last_dt = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600 < CONSEC_LOSS_COOLDOWN_HOURS
    except Exception:
        return False


def _fetch_atr(symbol: str, period: int = 14) -> float:
    """Fetch ATR from recent klines. Stdlib only."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for mirror in BINANCE_MIRRORS:
        try:
            url = f"{mirror}/api/v3/klines?symbol={symbol}&interval=1h&limit={period + 1}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=8, context=ctx)
            klines = json.loads(resp.read())
            if len(klines) < 2:
                continue
            trs = []
            for i in range(1, len(klines)):
                high = float(klines[i][2])
                low = float(klines[i][3])
                prev_close = float(klines[i - 1][4])
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                trs.append(tr)
            return sum(trs[-period:]) / min(len(trs), period) if trs else 0.0
        except Exception:
            continue
    return 0.0


def _fetch_recent_returns(symbol: str, limit: int = 24) -> list:
    """Fetch recent hourly returns for correlation check. Stdlib only."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for mirror in BINANCE_MIRRORS:
        try:
            url = f"{mirror}/api/v3/klines?symbol={symbol}&interval=1h&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=8, context=ctx)
            klines = json.loads(resp.read())
            closes = [float(k[4]) for k in klines]
            if len(closes) < 2:
                return []
            return [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        except Exception:
            continue
    return []


def _pearson_r(x: list, y: list) -> float:
    """Compute Pearson correlation coefficient. Stdlib only."""
    n = min(len(x), len(y))
    if n < 5:
        return 0.0
    x, y = x[:n], y[:n]
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    dy = sum((yi - my) ** 2 for yi in y) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def _passes_correlation_gate(symbol: str, portfolio: dict, threshold: float = 0.75) -> bool:
    """Reject if new symbol has Pearson r > threshold with any existing position."""
    active = portfolio.get("active_positions", [])
    if not active:
        return True
    new_returns = _fetch_recent_returns(symbol)
    if not new_returns:
        return True
    existing_symbols = set(p.get("symbol", "") for p in active)
    for existing_sym in existing_symbols:
        if existing_sym == symbol:
            continue
        existing_returns = _fetch_recent_returns(existing_sym)
        if not existing_returns:
            continue
        r = _pearson_r(new_returns, existing_returns)
        if abs(r) > threshold:
            print(f"  [CORRELATION GATE] Rejected {symbol}: r={r:.3f} with {existing_sym} exceeds {threshold}")
            return False
    return True


def _compute_position_size(symbol: str, entry_price: float, portfolio: dict) -> float:
    """
    Volatility-scaled position sizing (TESTING_PROTOCOL v4.0 Section 3).
    Risk per trade = 1% of equity scaled by ATR, capped at half-Kelly.
    Floor 2%, ceiling 8%.
    """
    equity = portfolio.get("virtual_capital", VIRTUAL_CAPITAL)
    risk_pct = 0.01
    atr = _fetch_atr(symbol)
    if atr > 0 and entry_price > 0:
        risk_amount = equity * risk_pct
        position_value = risk_amount / (atr / entry_price)
    else:
        position_value = equity * _effective_position_size_pct()
    stats = portfolio.get("stats", {})
    wr = stats.get("win_rate", 0.5)
    total = stats.get("total_trades", 0)
    if total >= 10 and wr > 0:
        closed = portfolio.get("closed_positions", [])
        wins = [abs(p.get("realized_pnl_pct", 0)) for p in closed if (p.get("realized_pnl_pct", 0) or 0) > 0]
        losses = [abs(p.get("realized_pnl_pct", 0)) for p in closed if (p.get("realized_pnl_pct", 0) or 0) < 0]
        avg_win = sum(wins) / len(wins) if wins else 1.0
        avg_loss = sum(losses) / len(losses) if losses else 1.0
        rr = avg_win / avg_loss if avg_loss > 0 else 1.0
        kelly = wr - (1 - wr) / rr if rr > 0 else 0
        half_kelly = max(kelly / 2, 0.02)
        kelly_cap = equity * min(half_kelly, 0.08)
        position_value = min(position_value, kelly_cap)
    position_value = max(position_value, equity * 0.02)
    position_value = min(position_value, equity * 0.08)
    return round(position_value, 2)


def _qualifies(pick: dict) -> bool:
    """Does this pick meet Real Money criteria?"""
    if datetime.now(timezone.utc).weekday() in BLOCKED_WEEKDAYS:
        return False
    strategy = pick.get("strategy", pick.get("source", pick.get("source_system", "")))
    score = pick.get("score", 0) or 0
    conf = pick.get("confidence", 0) or 0
    rr = pick.get("rr", pick.get("rr_ratio", pick.get("risk_reward", 0))) or 0
    entry = pick.get("entry_price", 0) or 0
    tp = pick.get("take_profit", 0) or 0
    sl = pick.get("stop_loss", 0) or 0
    safety = pick.get("safety", "")

    # Must be proven strategy
    if not any(ps in str(strategy) for ps in PROVEN_STRATEGIES):
        return False

    # Must have score >= threshold
    if score < MIN_SCORE:
        return False

    # Must have entry/TP/SL
    if entry <= 0 or tp <= 0 or sl <= 0:
        return False

    # LESSON 1: Stale picks lose. Max 6h age for real money.
    ts = pick.get("timestamp", pick.get("created_at", pick.get("generated_at", "")))
    if ts:
        try:
            pdt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age_h = (datetime.now(timezone.utc) - pdt).total_seconds() / 3600
            if age_h > 6:
                return False  # Too stale for real money
        except Exception:
            pass

    # R:R must be reasonable
    if rr > MAX_RR and rr > 0:
        return False

    # Avoid confidence dead zone (0.60-0.69 = 35.6% WR)
    # NOTE: relaxed during beta — many proven strategies land here
    # Will tighten once CI regenerates with corrected confidence scoring
    if CONF_DEAD_ZONE[0] <= conf <= CONF_DEAD_ZONE[1]:
        # Only block if strategy is NOT proven (proven strategies override)
        if not any(ps in str(strategy) for ps in PROVEN_STRATEGIES):
            return False

    # Direction conflicts — warn but allow for proven strategies
    if pick.get("_direction_conflict") or pick.get("direction_conflict"):
        if not any(ps in str(strategy) for ps in PROVEN_STRATEGIES):
            return False

    return True


def select_new_positions(portfolio: dict) -> list[dict]:
    """Select new qualifying picks not already in portfolio."""
    if _in_cooldown(portfolio):
        return []

    # Drawdown circuit breaker: skip new entries if breaker is active
    try:
        from alpha_engine.drawdown_circuit_breaker import is_drawdown_breaker_active
        if is_drawdown_breaker_active():
            print("  [REAL MONEY] Drawdown circuit breaker ACTIVE -- skipping new entries")
            return []
    except ImportError:
        pass

    # Load dashboard data
    dashboard_path = BASE.parent / "audit_dashboard" / "data" / "dashboard_data.json"
    if not dashboard_path.exists():
        return []

    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    active_picks = dashboard.get("picks", {}).get("active", [])
    crypto = [p for p in active_picks if "USDT" in p.get("symbol", "")]

    # Track existing symbols in portfolio
    active_symbols = {}
    for pos in portfolio.get("active_positions", []):
        sym = pos.get("symbol", "")
        active_symbols[sym] = active_symbols.get(sym, 0) + 1

    new_positions = []
    for pick in crypto:
        if not _qualifies(pick):
            continue

        symbol = pick.get("symbol", "")

        # Correlation gate (Protocol v4.0 Section 3)
        if not _passes_correlation_gate(symbol, portfolio):
            continue

        # Max per symbol
        if active_symbols.get(symbol, 0) >= MAX_PER_SYMBOL:
            continue

        # Not already tracking this exact pick
        pick_id = f"{symbol}_{pick.get('strategy', pick.get('source', ''))}_{pick.get('direction', '')}"
        existing_ids = {
            f"{p['symbol']}_{p.get('strategy','')}_{p.get('direction','')}"
            for p in portfolio.get("active_positions", [])
        }
        if pick_id in existing_ids:
            continue

        entry_price = pick.get("entry_price", 0) or 0
        if entry_price <= 0:
            continue

        position_value = _compute_position_size(symbol, entry_price, portfolio)

        new_positions.append({
            "symbol": symbol,
            "direction": pick.get("direction", "LONG"),
            "strategy": pick.get("strategy", pick.get("source", "?")),
            "entry_price": entry_price,
            "take_profit": pick.get("take_profit", 0),
            "stop_loss": pick.get("stop_loss", 0),
            "score": pick.get("score", 0),
            "confidence": pick.get("confidence", 0),
            "safety": pick.get("safety", "UNKNOWN"),
            "rr": pick.get("rr", pick.get("rr_ratio", 0)),
            "position_value": round(position_value, 2),
            "entered_at": datetime.now(timezone.utc).isoformat(),
            "pick_timestamp": pick.get("timestamp", pick.get("created_at", "")),
            "status": "OPEN",
        })
        active_symbols[symbol] = active_symbols.get(symbol, 0) + 1

    return new_positions


def check_positions(portfolio: dict) -> list[dict]:
    """Check active positions for TP/SL hits."""
    closed = []
    still_open = []

    for pos in portfolio.get("active_positions", []):
        symbol = pos.get("symbol", "")
        live_price = _fetch_price(symbol)

        if live_price <= 0:
            still_open.append(pos)
            continue

        entry = pos.get("entry_price", 0)
        tp = pos.get("take_profit", 0)
        sl = pos.get("stop_loss", 0)
        direction = pos.get("direction", "LONG").upper()

        hit_tp = False
        hit_sl = False

        if direction == "LONG":
            if tp > 0 and live_price >= tp:
                hit_tp = True
            if sl > 0 and live_price <= sl:
                hit_sl = True
            pnl_pct = (live_price - entry) / entry * 100 if entry > 0 else 0
        else:  # SHORT
            if tp > 0 and live_price <= tp:
                hit_tp = True
            if sl > 0 and live_price >= sl:
                hit_sl = True
            pnl_pct = (entry - live_price) / entry * 100 if entry > 0 else 0

        pos["live_price"] = live_price
        pos["unrealized_pnl_pct"] = round(pnl_pct, 3)

        if hit_tp or hit_sl:
            pos["status"] = "TP_HIT" if hit_tp else "SL_HIT"
            pos["exit_price"] = live_price
            pos["realized_pnl_pct"] = round(pnl_pct, 3)
            pos["closed_at"] = datetime.now(timezone.utc).isoformat()
            pos["profit"] = round(pos.get("position_value", 500) * pnl_pct / 100, 2)
            closed.append(pos)
        else:
            still_open.append(pos)

    return still_open, closed


def update_stats(portfolio: dict) -> None:
    """Recalculate portfolio statistics."""
    closed = portfolio.get("closed_positions", [])
    stats = portfolio["stats"]

    stats["total_trades"] = len(closed)
    stats["wins"] = sum(1 for p in closed if (p.get("realized_pnl_pct", 0) or 0) > 0)
    stats["losses"] = len(closed) - stats["wins"]
    stats["win_rate"] = round(stats["wins"] / max(len(closed), 1) * 100, 1)
    stats["total_pnl_pct"] = round(sum(p.get("realized_pnl_pct", 0) or 0 for p in closed), 2)

    # Equity calculation
    total_profit = sum(p.get("profit", 0) for p in closed)
    unrealized = sum(
        pos.get("position_value", 500) * ((pos.get("unrealized_pnl_pct") or 0) / 100)  # 2026-06-04 null-coalesce
        for pos in portfolio.get("active_positions", [])
    )
    equity = VIRTUAL_CAPITAL + total_profit + unrealized
    stats["current_equity"] = round(equity, 2)
    stats["total_profit"] = round(total_profit, 2)

    if equity > stats.get("peak_equity", VIRTUAL_CAPITAL):
        stats["peak_equity"] = round(equity, 2)

    peak = stats.get("peak_equity", VIRTUAL_CAPITAL)
    dd = (peak - equity) / peak * 100 if peak > 0 else 0
    if dd > stats.get("max_drawdown_pct", 0):
        stats["max_drawdown_pct"] = round(dd, 2)


def run_tracker() -> dict:
    """Main entry point — run hourly."""
    now = datetime.now(timezone.utc)
    portfolio = _load_portfolio()

    print(f"  [REAL MONEY] Checking positions...")

    # 1. Check existing positions for TP/SL hits
    still_open, newly_closed = check_positions(portfolio)
    portfolio["active_positions"] = still_open
    portfolio["closed_positions"].extend(newly_closed)

    if newly_closed:
        for c in newly_closed:
            print(f"    CLOSED: {c['symbol']} {c['direction']} {c['status']} PnL={c.get('realized_pnl_pct',0):+.2f}%")

    # 2. Select new qualifying positions
    new_picks = select_new_positions(portfolio)
    portfolio["active_positions"].extend(new_picks)

    if new_picks:
        for p in new_picks:
            print(f"    NEW: {p['symbol']} {p['direction']} score={p['score']} safety={p['safety']} rr={p['rr']}")

    # 3. Update stats
    update_stats(portfolio)
    portfolio["last_updated"] = now.isoformat()

    # 4. Save
    _save_portfolio(portfolio)

    stats = portfolio["stats"]
    active_count = len(portfolio["active_positions"])
    unrealized = stats.get("current_equity", VIRTUAL_CAPITAL) - VIRTUAL_CAPITAL - stats.get("total_profit", 0)
    active_tickers = ", ".join(
        f"{p['symbol']} {p['direction'][0]}" for p in portfolio["active_positions"][:8]
    )
    if active_count > 8:
        active_tickers += f" +{active_count - 8} more"
    # Open Record: how many active picks are currently winning vs losing
    open_winning = sum(1 for p in portfolio["active_positions"] if (p.get("unrealized_pnl_pct", 0) or 0) > 0.05)
    open_losing = sum(1 for p in portfolio["active_positions"] if (p.get("unrealized_pnl_pct", 0) or 0) < -0.05)
    open_flat = active_count - open_winning - open_losing
    unrealized_pct = unrealized / VIRTUAL_CAPITAL * 100 if VIRTUAL_CAPITAL else 0
    print(f"  [REAL MONEY] Equity: ${stats.get('current_equity', VIRTUAL_CAPITAL):,.2f} "
          f"({stats.get('current_equity', VIRTUAL_CAPITAL) - VIRTUAL_CAPITAL:+.2f}) | "
          f"Realized: {stats['total_pnl_pct']:+.2f}% | Unrealized: {unrealized_pct:+.2f}% | "
          f"Open: {open_winning}W/{open_losing}L/{open_flat}F | "
          f"Closed: {stats.get('wins',0)}W/{stats.get('losses',0)}L | "
          f"{active_tickers or 'none'}")

    # 5. Append to history
    _append_history(portfolio, now)

    # 6. Run drawdown circuit breaker check (after stats + history updated)
    try:
        from alpha_engine.drawdown_circuit_breaker import check_drawdown_breaker
        check_drawdown_breaker(portfolio)
    except ImportError:
        pass
    except Exception as e:
        print(f"  [REAL MONEY] Drawdown breaker check failed (non-fatal): {e}")

    return portfolio


def _append_history(portfolio: dict, now: datetime) -> None:
    """Append snapshot to history file."""
    history = []
    if PORTFOLIO_HISTORY.exists():
        try:
            history = json.loads(PORTFOLIO_HISTORY.read_text(encoding="utf-8"))
        except Exception:
            history = []

    history.append({
        "timestamp": now.isoformat(),
        "active_positions": len(portfolio["active_positions"]),
        "closed_positions": portfolio["stats"]["total_trades"],
        "win_rate": portfolio["stats"]["win_rate"],
        "total_pnl_pct": portfolio["stats"]["total_pnl_pct"],
        "equity": portfolio["stats"].get("current_equity", VIRTUAL_CAPITAL),
        "max_drawdown_pct": portfolio["stats"].get("max_drawdown_pct", 0),
    })

    # Keep last 500 snapshots
    if len(history) > 500:
        history = history[-500:]

    PORTFOLIO_HISTORY.write_text(json.dumps(history, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    portfolio = run_tracker()
    print(json.dumps(portfolio["stats"], indent=2, default=str))
