"""Fetch stock prices server-side and write to JSON for dashboard consumption.
Run in CI where there's no CORS restriction."""
import json
import os
import sys
import time


def fetch_prices(symbols):
    """Fetch stock prices using yfinance (no API key needed, no CORS)."""
    prices = {}
    try:
        import yfinance as yf
        # Batch fetch - yfinance handles this efficiently
        tickers = yf.Tickers(' '.join(symbols))
        for sym in symbols:
            try:
                t = tickers.tickers.get(sym)
                if t:
                    info = t.fast_info
                    p = getattr(info, 'last_price', None) or getattr(info, 'previous_close', None)
                    if p and p > 0:
                        prices[sym] = round(float(p), 2)
            except Exception:
                pass
    except ImportError:
        print("yfinance not available, trying requests fallback")

    # Fallback for missing symbols: FMP API (server-side, no CORS issue)
    # API key is read from the environment — never hardcode credentials in source.
    fmp_api_key = os.getenv("FMP_API_KEY", "")
    missing = [s for s in symbols if s not in prices]
    if missing and fmp_api_key:
        try:
            import requests
            for i in range(0, len(missing), 5):
                batch = missing[i:i+5]
                for sym in batch:
                    try:
                        r = requests.get(
                            f"https://financialmodelingprep.com/stable/profile?symbol={sym}&apikey={fmp_api_key}",
                            timeout=10
                        )
                        if r.status_code == 200:
                            data = r.json()
                            if isinstance(data, list) and data:
                                prices[data[0].get('symbol', sym)] = data[0].get('price', 0)
                            elif isinstance(data, dict) and data.get('price'):
                                prices[sym] = data['price']
                    except Exception:
                        pass
                time.sleep(1)  # rate limit protection
        except ImportError:
            pass

    return prices


def _symbols_from_dashboard_data(path):
    """Symbols from the payload CI ACTUALLY regenerates (2026-10-18).

    The legacy branch above reads `audit_trail/data/dashboard_payload.json`, a
    2026-06-03-era file nothing regenerates any more — verified by comparing the
    live `audit/data/stock_prices.json` symbol set against the hardcoded
    `known` list: they were IDENTICAL (61/61), i.e. the payload branch
    contributed zero symbols. Consequence: every active pick outside those 61
    tickers had no price source at all, so the dashboard rendered it at
    `current_price == entry_price` → a flat 0.00% PnL (seen on TIP/VLUE/USO/
    VYM/XLB/VCSH/XLK/EFA/XLV + NQ=F/GC=F/PA=F on 2026-10-18).

    `audit_dashboard/data/dashboard_data.json` is written earlier in the same
    audit-dashboard.yml run, so it is always fresh here. Actives are taken from
    every non-crypto class; closed picks only if they closed within RECENT_DAYS
    (the file holds months of history and would otherwise bloat the batch).
    Fail-open: any read/shape problem returns an empty set.
    """
    import datetime as _dt
    RECENT_DAYS = 14
    _PRICEABLE = {"EQUITY", "ETF", "FUTURES", "COMMODITY", "BOND", "STOCK"}
    if not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"dashboard_data.json unreadable ({e}) — skipping its symbols")
        return set()

    def _want(pick):
        if not isinstance(pick, dict):
            return False
        if str(pick.get("asset_class", "")).upper() not in _PRICEABLE:
            return False
        sym = str(pick.get("symbol") or "")
        if not sym or sym.endswith("USDT") or sym.endswith("-USD"):
            return False
        return True

    def _recent(pick):
        for key in ("closed_at", "exit_time", "timestamp", "recorded_at", "entry_time"):
            raw = pick.get(key)
            if not raw:
                continue
            try:
                ts = _dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=_dt.timezone.utc)
                return (_dt.datetime.now(_dt.timezone.utc) - ts).days <= RECENT_DAYS
            except Exception:
                continue
        return False  # undated closed row → skip

    syms = set()
    picks = data.get("picks") or {}
    if isinstance(picks, dict):
        for key, needs_recency in (("active", False), ("active_raw", False),
                                   ("recent_closed", True)):
            for pick in picks.get(key) or []:
                if _want(pick) and (not needs_recency or _recent(pick)):
                    syms.add(str(pick["symbol"]).strip())
    print(f"dashboard_data.json contributed {len(syms)} priceable symbols")
    return syms


def main():
    # Collect all unique stock symbols from dashboard data
    symbols = set()

    # Read dashboard_payload.json for pick symbols (legacy — see helper docstring)
    payload_path = os.path.join(os.path.dirname(__file__), 'data', 'dashboard_payload.json')
    if os.path.exists(payload_path):
        with open(payload_path) as f:
            payload = json.load(f)
        for section in ['active_picks', 'closed_picks', 'picks']:
            items = payload.get(section, [])
            if not isinstance(items, list):
                continue
            for pick in items:
                if not isinstance(pick, dict):
                    continue
                sym = pick.get('symbol', '')
                ac = pick.get('asset_class', '').lower()
                if ac in ('equity', 'stock', 'etf', 'futures') or (
                    sym and not sym.endswith('USDT') and '-USD' not in sym
                    and len(sym) <= 5 and sym.isalpha()
                ):
                    symbols.add(sym)

    # Fresh source: the payload this same workflow run regenerates (see helper)
    dd_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           'audit_dashboard', 'data', 'dashboard_data.json')
    symbols.update(_symbols_from_dashboard_data(dd_path))

    # Also add known goldmine + smart money symbols
    known = [
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'TSLA', 'META', 'JPM', 'V',
        'JNJ', 'UNH', 'XOM', 'BAC', 'NFLX', 'CAT', 'MCD', 'WMT', 'ADBE', 'NKE',
        'KO', 'LIN', 'IBM', 'AMT', 'CRM', 'PLD', 'ABBV', 'PEP', 'MS', 'GS',
        'SLB', 'RTX', 'COST', 'SCHW', 'LLY', 'UPS', 'ORCL', 'WFC', 'AVGO', 'HON',
        'SO', 'HD', 'DIS', 'BA', 'PG', 'COP', 'CSCO', 'AMD', 'CVX', 'NEE',
        'GE', 'PFE', 'MRK', 'SPY', 'QQQ', 'IWM', 'XLE', 'XLF', 'GLD', 'SLV', 'HYG',
    ]
    symbols.update(known)

    symbols = sorted(symbols)
    print(f"Fetching prices for {len(symbols)} stock symbols...")

    prices = fetch_prices(symbols)
    print(f"Got {len(prices)}/{len(symbols)} prices")

    # Write to JSON
    output = {
        'prices': prices,
        'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'count': len(prices),
    }

    output_path = os.path.join(os.path.dirname(__file__), 'data', 'stock_prices.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tmp_path = f"{output_path}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp_path, output_path)
    print(f"Written to {output_path}")


if __name__ == '__main__':
    main()
