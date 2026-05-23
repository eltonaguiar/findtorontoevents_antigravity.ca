"""Compute Hyrotrader-style TP/SL levels for a TradingView paper trade.

Fetches the live price + a real 14-period ATR from Binance klines (with the
mandatory failover chain), then derives:
  SL = 1.5 x ATR from entry (against the position)
  TP = 2 x risk from entry (toward the position)  -> clean 2:1 R:R

Usage:
  python tools/tv_calc_levels.py <SYMBOL> <SIDE> [ENTRY]
    SYMBOL : Binance pair, e.g. BNBUSDT, ETHUSDT  (or BINANCE:BNBUSDT)
    SIDE   : LONG | SHORT
    ENTRY  : optional fill price; defaults to the current price

Example:
  python tools/tv_calc_levels.py BNBUSDT LONG 671.80
  -> prints  SL=...  TP=...  with the side-sanity check

No hardcoded numbers — every level is derived from the live tape. Run this for
every position instead of trusting TV's tick placeholders.
"""
import json
import sys
import urllib.request


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def fetch_price(sym: str) -> float:
    for host in ("api", "api1", "api2", "api3"):
        try:
            d = _get(f"https://{host}.binance.com/api/v3/ticker/price?symbol={sym}")
            return float(d["price"])
        except Exception:
            continue
    # CoinGecko / KuCoin fallbacks
    try:
        base = sym.replace("USDT", "").lower()
        d = _get(f"https://api.coingecko.com/api/v3/simple/price?ids={base}&vs_currencies=usd")
        return float(next(iter(d.values()))["usd"])
    except Exception:
        pass
    d = _get(f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={sym[:-4]}-USDT")
    return float(d["data"]["price"])


def fetch_atr(sym: str, period: int = 14) -> float:
    """Real ATR from daily klines, returned as a fraction of the last close."""
    rows = None
    for host in ("api", "api1", "api2", "api3"):
        try:
            rows = _get(f"https://{host}.binance.com/api/v3/klines"
                        f"?symbol={sym}&interval=1d&limit={period + 1}")
            break
        except Exception:
            continue
    if not rows or len(rows) < 2:
        raise RuntimeError("could not fetch klines for ATR")
    trs = []
    prev_close = float(rows[0][4])
    for k in rows[1:]:
        high, low, close = float(k[2]), float(k[3]), float(k[4])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
        prev_close = close
    atr = sum(trs) / len(trs)
    return atr / prev_close  # ATR as a fraction of price


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    sym = sys.argv[1].upper().split(":")[-1]
    side = sys.argv[2].upper()
    if side not in ("LONG", "SHORT"):
        print("SIDE must be LONG or SHORT")
        sys.exit(1)

    price = fetch_price(sym)
    entry = float(sys.argv[3]) if len(sys.argv) > 3 else price
    atr_pct = fetch_atr(sym)
    sl_dist = 1.5 * atr_pct * entry  # 1.5 x ATR

    if side == "LONG":
        sl = entry - sl_dist
        tp = entry + 2 * sl_dist
        valid = tp > price > sl
    else:
        sl = entry + sl_dist
        tp = entry - 2 * sl_dist
        valid = tp < price < sl

    print(f"symbol     : {sym}  ({side})")
    print(f"live price : {price:.4f}")
    print(f"entry      : {entry:.4f}")
    print(f"ATR(14d)   : {atr_pct * 100:.2f}%  (1.5x = {sl_dist:.4f})")
    print(f"SL         : {round(sl, 4)}")
    print(f"TP         : {round(tp, 4)}   (2:1 R:R)")
    print(f"side-sanity: {'OK' if valid else 'FAIL — levels on wrong side of market!'}")
    if not valid:
        print("  -> do NOT place these; recheck side / entry.")


if __name__ == "__main__":
    main()
