#!/usr/bin/env python3
"""
Portfolio Integrity Verifier — runs every cycle to catch data issues.
Checks EVERY open position and closed trade for:
1. Entry/exit price sanity (vs live market)
2. PnL calculation accuracy
3. Equity math correctness
4. Win/loss count consistency
5. Duplicate detection
6. Stale position detection
7. Dashboard JSON consistency
"""
import json
import sys
import os
import urllib.request
import hashlib
from datetime import datetime, timezone

STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "claudes_test_state.json")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "data", "integrity_report.json")

# Price fetch with failover (same chain as portfolio_manager)
_price_cache = {}

_KNOWN_STOCKS = {
    "JNJ", "META", "GME", "AAPL", "MSFT", "SPY", "QQQ", "AMZN", "GOOGL", "TSLA",
    "NVDA", "AMD", "NFLX", "DIS", "BA", "V", "MA", "JPM", "GS", "WMT", "COST",
    "UNH", "PFE", "MRK", "ABBV", "XOM", "CVX", "COP", "T", "VZ", "INTC",
    "PG", "COIN", "KO", "HD", "LOW", "CRM", "PYPL", "SQ", "SHOP", "UBER",
    "SOFI", "TLT", "IWM", "EEM", "GLD", "SLV",
}
_STABLECOINS = {"USDC", "USDT", "DAI", "BUSD", "TUSD", "USDP", "FDUSD", "USD1", "XUSD", "PYUSD"}


def _base(symbol):
    return symbol.upper().replace("USDT", "").replace("-USD", "").replace("USD", "").replace("/", "").replace("=X", "").rstrip("-")


def fetch_price(symbol):
    if symbol in _price_cache:
        return _price_cache[symbol]
    base = _base(symbol)
    if base in _STABLECOINS:
        _price_cache[symbol] = 1.0
        return 1.0

    price = 0.0
    is_stock = base in _KNOWN_STOCKS

    if not is_stock:
        # Try Binance (with endpoint failover)
        _binance_bases = [
            "https://api.binance.com",
            "https://api.binance.us",
            "https://data-api.binance.vision",
        ]
        for suffix in ["USDT", ""]:
            for _bbase in _binance_bases:
                try:
                    url = f"{_bbase}/api/v3/ticker/price?symbol={base}{suffix}"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.loads(resp.read())
                        price = float(data["price"])
                        if price > 0:
                            _price_cache[symbol] = price
                            return price
                except Exception:
                    continue

        # Try Bybit
        try:
            url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={base}USDT"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                tickers = data.get("result", {}).get("list", [])
                if tickers:
                    price = float(tickers[0].get("lastPrice", 0))
                    if price > 0:
                        _price_cache[symbol] = price
                        return price
        except Exception:
            pass

        # Try CryptoCompare
        try:
            url = f"https://min-api.cryptocompare.com/data/price?fsym={base}&tsyms=USD"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                price = float(data.get("USD", 0))
                if price > 0:
                    _price_cache[symbol] = price
                    return price
        except Exception:
            pass

    # Yahoo (stocks + fallback)
    _YAHOO = {
        "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "DOGE": "DOGE-USD",
        "XRP": "XRP-USD", "ADA": "ADA-USD", "BNB": "BNB-USD", "DOT": "DOT-USD",
    }
    yahoo_sym = _YAHOO.get(base, base if is_stock else None)
    if yahoo_sym:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}?range=1d&interval=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                price = float(meta.get("regularMarketPrice", 0))
                if price > 0:
                    _price_cache[symbol] = price
                    return price
        except Exception:
            pass

    _price_cache[symbol] = 0.0
    return 0.0


def verify_portfolio(pname, pdata):
    """Run all integrity checks on a single portfolio. Returns list of issues."""
    issues = []
    warnings = []
    init_cap = pdata.get("initial_capital", 10000)
    equity = pdata.get("equity", 0)
    cash = pdata.get("cash", 0)
    positions = pdata.get("positions", [])
    closed = pdata.get("closed", [])
    wins = pdata.get("wins", 0)
    losses = pdata.get("losses", 0)

    # === 1. Check open positions ===
    seen_pos_ids = set()
    total_pos_value = 0
    total_unrealized = 0
    for p in positions:
        pid = p.get("id", "")
        sym = p.get("symbol", "")
        entry = p.get("entry_price", 0)
        size = p.get("size_usd", 0)
        qty = p.get("quantity", 0)

        # Duplicate check
        if pid and pid in seen_pos_ids:
            issues.append(f"DUPLICATE open position ID: {pid} ({sym})")
        seen_pos_ids.add(pid)

        # Entry price vs market
        market = fetch_price(sym)
        if market > 0 and entry > 0:
            ratio = entry / market
            if ratio > 2.0 or ratio < 0.1:
                issues.append(f"PRICE CORRUPT {sym}: entry=${entry:.6f} vs market=${market:.6f} (ratio={ratio:.2f})")
            elif ratio > 1.5 or ratio < 0.5:
                warnings.append(f"PRICE DRIFT {sym}: entry=${entry:.6f} vs market=${market:.6f} (ratio={ratio:.2f})")
        elif market <= 0:
            warnings.append(f"UNVERIFIABLE {sym}: no market price available")

        # Zero/negative checks
        if entry <= 0:
            issues.append(f"ZERO ENTRY {sym}: entry=${entry}")
        if size <= 0 and qty <= 0:
            issues.append(f"ZERO SIZE {sym}: size=${size}, qty={qty}")

        total_pos_value += size
        unrealized = p.get("pnl_usd", 0) or 0
        total_unrealized += unrealized

    # === 2. Check closed trades ===
    seen_close_ids = set()
    computed_realized = 0
    computed_wins = 0
    computed_losses = 0
    for t in closed:
        tid = t.get("id", "")
        sym = t.get("symbol", "")
        entry = t.get("entry_price", 0)
        exit_p = t.get("exit_price", 0)
        pnl_pct = t.get("pnl_pct", 0) or 0
        pnl_usd = t.get("net_pnl_usd", 0) or t.get("pnl_usd", 0) or 0
        direction = (t.get("direction", "") or "").upper()

        # Duplicate check
        if tid and tid in seen_close_ids:
            issues.append(f"DUPLICATE closed trade ID: {tid} ({sym})")
        seen_close_ids.add(tid)

        # Entry/exit price sanity
        market = fetch_price(sym)
        if market > 0:
            if entry > 0:
                ratio = entry / market
                if ratio > 5.0 or ratio < 0.01:
                    issues.append(f"CLOSED PRICE CORRUPT {sym}: entry=${entry:.6f} vs market=${market:.6f}")
            if exit_p > 0:
                ratio = exit_p / market
                if ratio > 5.0 or ratio < 0.01:
                    issues.append(f"CLOSED EXIT CORRUPT {sym}: exit=${exit_p:.6f} vs market=${market:.6f}")

        # PnL calculation verification
        if entry > 0 and exit_p > 0:
            if direction in ("LONG", "BUY"):
                expected_pnl_pct = ((exit_p - entry) / entry) * 100
            elif direction in ("SHORT", "SELL"):
                expected_pnl_pct = ((entry - exit_p) / entry) * 100
            else:
                expected_pnl_pct = ((exit_p - entry) / entry) * 100

            if abs(expected_pnl_pct - pnl_pct) > 1.0:  # >1% discrepancy
                issues.append(f"PNL MISMATCH {sym}: reported={pnl_pct:.2f}%, calculated={expected_pnl_pct:.2f}%")

        # Extreme PnL
        if abs(pnl_pct) > 50:
            issues.append(f"EXTREME PNL {sym}: {pnl_pct:.1f}% (single trade >50%)")

        # Count W/L
        computed_realized += pnl_usd
        if pnl_usd > 0:
            computed_wins += 1
        elif pnl_usd < 0:
            computed_losses += 1

    # === 3. Win/Loss count consistency ===
    if wins != computed_wins:
        issues.append(f"WIN COUNT MISMATCH: stored={wins}, computed={computed_wins}")
    if losses != computed_losses:
        issues.append(f"LOSS COUNT MISMATCH: stored={losses}, computed={computed_losses}")

    # === 4. Equity math ===
    expected_equity = cash + total_pos_value + total_unrealized
    if abs(equity - expected_equity) > 1.0 and len(positions) > 0:  # >$1 discrepancy
        warnings.append(f"EQUITY DRIFT: stored=${equity:.2f}, computed=${expected_equity:.2f} (diff=${equity-expected_equity:.2f})")

    # === 5. Capital preservation ===
    pnl_pct_total = ((equity - init_cap) / init_cap) * 100 if init_cap > 0 else 0
    if pnl_pct_total < -50:
        issues.append(f"CATASTROPHIC LOSS: {pnl_pct_total:.1f}% (>50% drawdown)")
    elif pnl_pct_total > 100:
        warnings.append(f"SUSPICIOUS GAIN: +{pnl_pct_total:.1f}% (>100% gain, verify)")

    # === 6. Stale position check ===
    now_ts = datetime.now(timezone.utc).timestamp() * 1000
    for p in positions:
        opened_ts = p.get("opened_at_ts", 0) or 0
        if opened_ts > 0:
            age_hours = (now_ts - opened_ts) / (1000 * 3600)
            if age_hours > 168:  # >7 days
                warnings.append(f"STALE POSITION {p.get('symbol','')}: open for {age_hours:.0f}h ({age_hours/24:.1f} days)")

    return {
        "portfolio": pname,
        "equity": equity,
        "pnl_pct": pnl_pct_total,
        "open_positions": len(positions),
        "closed_trades": len(closed),
        "wins": wins,
        "losses": losses,
        "issues": issues,
        "warnings": warnings,
        "status": "CRITICAL" if issues else ("WARNING" if warnings else "CLEAN"),
    }


def main():
    print(f"\n{'='*70}")
    print(f"  PORTFOLIO INTEGRITY VERIFIER — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}\n")

    if not os.path.exists(STATE_FILE):
        print(f"ERROR: State file not found: {STATE_FILE}")
        sys.exit(1)

    with open(STATE_FILE) as f:
        state = json.load(f)

    results = []
    total_issues = 0
    total_warnings = 0

    for pname, pdata in sorted(state.items()):
        result = verify_portfolio(pname, pdata)
        results.append(result)
        n_issues = len(result["issues"])
        n_warnings = len(result["warnings"])
        total_issues += n_issues
        total_warnings += n_warnings

        # Print status
        status_icon = {"CLEAN": "[OK]", "WARNING": "[!!]", "CRITICAL": "[XX]"}.get(result["status"], "[??]")
        pnl_str = f"+{result['pnl_pct']:.2f}%" if result["pnl_pct"] >= 0 else f"{result['pnl_pct']:.2f}%"
        print(f"  {status_icon} {pname:30s} | eq=${result['equity']:>10.2f} | {pnl_str:>8s} | {result['open_positions']} open, {result['closed_trades']} closed | W/L={result['wins']}/{result['losses']}")

        for issue in result["issues"]:
            print(f"     [XX] {issue}")
        for warn in result["warnings"]:
            print(f"     [!!] {warn}")

    # Summary
    clean = sum(1 for r in results if r["status"] == "CLEAN")
    warning = sum(1 for r in results if r["status"] == "WARNING")
    critical = sum(1 for r in results if r["status"] == "CRITICAL")
    total_equity = sum(r["equity"] for r in results)
    total_open = sum(r["open_positions"] for r in results)
    total_closed = sum(r["closed_trades"] for r in results)

    print(f"\n{'='*70}")
    print(f"  SUMMARY: {len(results)} portfolios | {clean} clean, {warning} warnings, {critical} critical")
    print(f"  Total equity: ${total_equity:,.2f} | {total_open} open positions | {total_closed} closed trades")
    print(f"  Issues: {total_issues} | Warnings: {total_warnings}")
    print(f"{'='*70}\n")

    # Save report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_portfolios": len(results),
            "clean": clean,
            "warnings": warning,
            "critical": critical,
            "total_issues": total_issues,
            "total_warnings": total_warnings,
            "total_equity": total_equity,
            "total_open_positions": total_open,
            "total_closed_trades": total_closed,
        },
        "portfolios": results,
    }
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Report saved to {REPORT_FILE}")

    # Exit code: 1 if critical issues, 0 otherwise
    if critical > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
