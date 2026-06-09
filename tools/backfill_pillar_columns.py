#!/usr/bin/env python3
"""
backfill_pillar_columns.py
==========================

Partial backfill for the 4 pillar columns added by
`tools/migrate_add_pillar_columns.py` on 2026-06-09.

What it backfills
-----------------
  - `sector`                  : hardcoded map (crypto/forex/equity/etf/commodity/bond/futures
                                bucket) keyed by `(asset_class, symbol)`. Falls back to a
                                class-level default (`crypto-other`, `equity-other`, etc.)
                                for symbols not in the map. NOTE: `stock_assets.sector`
                                is empty in the live DB, so equity sector is hardcoded too.
  - `market_regime_id`        : per-symbol LATEST regime, computed from the most-recent
                                OHLCV bars in `crypto_ohlcv` / `stock_ohlcv` via a 3m-return
                                + 20d-ATR/close proxy.
                                (NOT per-row historical — that requires per-timestamp lookups
                                and is deferred to a follow-up.)
  - `volatility_atr`          : per-symbol LATEST 14d ATR, computed from the most-recent
                                OHLCV bars in `crypto_ohlcv` / `stock_ohlcv`.
                                (NOT per-row historical — same deferral.)
  - `execution_slippage_pct`  : LEFT NULL. No fill-price data exists anywhere; needs a
                                separate decision (default 0.05% paper / 0.10% live vs
                                wire-the-price-failover-chain to log slippage at insert-time).

What it does NOT do
-------------------
  - Per-row historical regime/ATR (would need a `(symbol, time_key)` join against OHLCV
    for each of the 80k+ rows; deferred).
  - Forex / commodity / bond / futures OHLCV: those OHLCV tables don't exist in this DB
    (only `crypto_ohlcv` + `stock_ohlcv`); those asset classes get NULL for regime + ATR
    and we log the omission.
  - Symbol-level forward-WR scoring or any of the 5-pillar scoring itself (that's a
    separate tool, `tools/picks_now_reliability_panel.py`).

Idempotency
-----------
  - Only updates rows where the target column IS NULL (existing values are preserved).
  - Re-running is safe and a no-op once coverage reaches 100% (or N% for asset classes
    with no OHLCV data).

Usage
-----
  python3 tools/backfill_pillar_columns.py                       # dry-run
  python3 tools/backfill_pillar_columns.py --apply               # execute
  python3 tools/backfill_pillar_columns.py --apply --batch-size 2000

Co-Authored-By: Claude <noreply@anthropic.com>
"""
import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pymysql  # noqa: E402
from tools.db_env import get_stocks_creds  # noqa: E402

# ---------------------------------------------------------------------------
# Hardcoded sector maps (asset-class specific, fine-grained where possible)
# ---------------------------------------------------------------------------

# Each entry maps SYMBOL -> sector label. Unmapped symbols fall back to the
# class default in DEFAULT_SECTOR_BY_CLASS. The keys cover the top symbols
# per asset class discovered in pre-flight (>= ~80% coverage by row count).

SECTOR_MAP = {
    # ── CRYPTO ────────────────────────────────────────────────────────────
    "BTCUSDT": "crypto-L1-store-of-value",
    "ETHUSDT": "crypto-L1-smart-contracts",
    "ETH-USD": "crypto-L1-smart-contracts",
    "SOLUSDT": "crypto-L1-smart-contracts",
    "BNBUSDT": "crypto-L1-exchange",
    "XRPUSDT": "crypto-L1-payments",
    "ADAUSDT": "crypto-L1-smart-contracts",
    "AVAXUSDT": "crypto-L1-smart-contracts",
    "DOGEUSDT": "crypto-meme",
    "DOTUSDT": "crypto-L1-smart-contracts",
    "NEARUSDT": "crypto-L1-smart-contracts",
    "SUIUSDT": "crypto-L1-smart-contracts",
    "LINKUSDT": "crypto-oracle",
    "JUPUSDT": "crypto-defi-dex",
    "ENAUSDT": "crypto-defi-synth",
    "STXUSDT": "crypto-L2-bitcoin",
    "ARBUSDT": "crypto-L2-eth",
    "WIFUSDT": "crypto-meme",
    "INJUSDT": "crypto-L1-smart-contracts",
    "ZECUSDT": "crypto-privacy",
    "MATICUSDT": "crypto-L2-eth",
    "OPUSDT": "crypto-L2-eth",
    "ATOMUSDT": "crypto-L1-smart-contracts",
    "APTUSDT": "crypto-L1-smart-contracts",
    "TIAUSDT": "crypto-modular-da",
    "SEIUSDT": "crypto-L1-smart-contracts",
    "ALGOUSDT": "crypto-L1-smart-contracts",
    "EGLDUSDT": "crypto-L1-smart-contracts",
    "GRTUSDT": "crypto-oracle",
    "UNIUSDT": "crypto-defi-dex",
    "AAVEUSDT": "crypto-defi-lending",
    "MKRUSDT": "crypto-defi-lending",
    "DYDXUSDT": "crypto-defi-dex",
    "CRVUSDT": "crypto-defi-dex",
    "SNXUSDT": "crypto-defi-synth",
    "LDOUSDT": "crypto-defi-synth",
    "SHIBUSDT": "crypto-meme",
    "PEPEUSDT": "crypto-meme",
    "FLOKIUSDT": "crypto-meme",
    "BONKUSDT": "crypto-meme",
    "RENDERUSDT": "crypto-depin-gpu",
    # ── FOREX ─────────────────────────────────────────────────────────────
    "EURUSD=X": "forex-major", "EUR-USD": "forex-major",
    "GBPUSD=X": "forex-major", "GBP-USD": "forex-major",
    "USDJPY=X": "forex-major", "USD-JPY": "forex-major",
    "USDCHF=X": "forex-major", "USD-CHF": "forex-major",
    "AUDUSD=X": "forex-major", "AUD-USD": "forex-major",
    "NZDUSD=X": "forex-major",
    "USDCAD=X": "forex-major",
    "EURJPY=X": "forex-major-cross",
    "GBPJPY=X": "forex-major-cross",
    "AUDJPY=X": "forex-major-cross",
    "CADJPY=X": "forex-major-cross",
    "NZDJPY=X": "forex-major-cross",
    "EURGBP=X": "forex-major-cross",
    "CADCHF": "forex-major-cross",
    "AUDNZD=X": "forex-major-cross",
    # ── EQUITY (top tickers only; the rest fall back to 'equity-other') ──
    "NVDA": "equity-semiconductors", "AMD": "equity-semiconductors",
    "INTC": "equity-semiconductors", "AVGO": "equity-semiconductors",
    "QCOM": "equity-semiconductors", "TXN": "equity-semiconductors",
    "AMAT": "equity-semiconductors", "LRCX": "equity-semiconductors",
    "MU": "equity-semiconductors", "MRVL": "equity-semiconductors",
    "AAPL": "equity-mega-cap-tech", "MSFT": "equity-mega-cap-tech",
    "GOOGL": "equity-mega-cap-tech", "META": "equity-mega-cap-tech",
    "AMZN": "equity-mega-cap-tech", "TSLA": "equity-mega-cap-tech",
    "NFLX": "equity-mega-cap-tech", "CRM": "equity-mega-cap-tech",
    "ORCL": "equity-mega-cap-tech", "ADBE": "equity-mega-cap-tech",
    "IBM": "equity-mega-cap-tech", "NOW": "equity-mega-cap-tech",
    "UBER": "equity-mega-cap-tech", "ABNB": "equity-mega-cap-tech",
    "DASH": "equity-mega-cap-tech", "SNOW": "equity-mega-cap-tech",
    "CRWD": "equity-mega-cap-tech", "PANW": "equity-mega-cap-tech",
    "PLTR": "equity-mega-cap-tech", "DDOG": "equity-mega-cap-tech",
    "MDB": "equity-mega-cap-tech", "NET": "equity-mega-cap-tech",
    "ZM": "equity-mega-cap-tech", "WDAY": "equity-mega-cap-tech",
    "JPM": "equity-banks", "BAC": "equity-banks", "GS": "equity-banks",
    "MS": "equity-banks", "WFC": "equity-banks", "C": "equity-banks",
    "BLK": "equity-banks", "SCHW": "equity-banks",
    "AXP": "equity-payments", "V": "equity-payments", "MA": "equity-payments",
    "PYPL": "equity-payments", "SQ": "equity-payments",
    "BRK-B": "equity-insurance", "MET": "equity-insurance",
    "PRU": "equity-insurance", "AIG": "equity-insurance",
    "JNJ": "equity-healthcare", "PFE": "equity-healthcare",
    "MRK": "equity-healthcare", "ABBV": "equity-healthcare",
    "LLY": "equity-healthcare", "TMO": "equity-healthcare",
    "AMGN": "equity-healthcare", "GILD": "equity-healthcare",
    "VRTX": "equity-healthcare", "ISRG": "equity-healthcare",
    "BSX": "equity-healthcare", "SYK": "equity-healthcare",
    "ZTS": "equity-healthcare", "UNH": "equity-healthcare",
    "WMT": "equity-consumer-staples", "COST": "equity-consumer-staples",
    "PG": "equity-consumer-staples", "KO": "equity-consumer-staples",
    "PEP": "equity-consumer-staples", "CL": "equity-consumer-staples",
    "KMB": "equity-consumer-staples", "SYY": "equity-consumer-staples",
    "MCD": "equity-consumer-discretionary", "DIS": "equity-consumer-discretionary",
    "SBUX": "equity-consumer-discretionary", "CMG": "equity-consumer-discretionary",
    "HD": "equity-consumer-discretionary", "LOW": "equity-consumer-discretionary",
    "TJX": "equity-consumer-discretionary", "TGT": "equity-consumer-discretionary",
    "NKE": "equity-consumer-discretionary", "LULU": "equity-consumer-discretionary",
    "DECK": "equity-consumer-discretionary",
    "XOM": "equity-energy", "CVX": "equity-energy", "COP": "equity-energy",
    "EOG": "equity-energy", "PSX": "equity-energy", "VLO": "equity-energy",
    "CAT": "equity-industrials", "GE": "equity-industrials",
    "BA": "equity-industrials", "HON": "equity-industrials",
    "LMT": "equity-industrials", "RTX": "equity-industrials",
    "UPS": "equity-industrials", "FDX": "equity-industrials",
    "DE": "equity-industrials", "CARR": "equity-industrials",
    "CSX": "equity-industrials", "UNP": "equity-industrials",
    "AMT": "equity-real-estate", "PLD": "equity-real-estate",
    "CCI": "equity-real-estate", "EQIX": "equity-real-estate",
    "VZ": "equity-telecom", "T": "equity-telecom", "TMUS": "equity-telecom",
    "CMCSA": "equity-telecom",
    "F": "equity-auto", "GM": "equity-auto",
    "RIVN": "equity-auto", "LCID": "equity-auto",
    "RIOT": "equity-crypto-proxy",
    "EEM": "equity-emerging-markets", "EFA": "equity-intl-developed",
    "IWM": "equity-small-cap",
    "SHOP": "equity-mega-cap-tech",
    "CNQ": "equity-energy", "SU": "equity-energy",
    "BNS": "equity-banks", "RY": "equity-banks",
    # ── ETF (top tickers) ────────────────────────────────────────────────
    "SPY": "etf-broad-market-us-large-cap",
    "IVV": "etf-broad-market-us-large-cap",
    "VOO": "etf-broad-market-us-large-cap",
    "QQQ": "etf-broad-market-us-nasdaq100",
    "VGT": "etf-sector-tech", "XLK": "etf-sector-tech",
    "IWM": "etf-broad-market-us-small-cap",
    "VB": "etf-broad-market-us-small-cap",
    "VTWO": "etf-broad-market-us-small-cap",
    "SOXS": "etf-leveraged-inverse-semis",
    "JDST": "etf-leveraged-inverse-gold-miners",
    "LABD": "etf-leveraged-inverse-biotech",
    "ARKK": "etf-thematic-innovation",
    "BOTZ": "etf-thematic-ai-robotics",
    "FINX": "etf-thematic-fintech",
    "REMX": "etf-thematic-rare-earth",
    "XLE": "etf-sector-energy", "XLY": "etf-sector-consumer-discretionary",
    "XLI": "etf-sector-industrial", "VLUE": "etf-factor-value",
    "GLD": "etf-commodity-gold",
    "VNQ": "etf-real-estate-us-reit",
    "IJH": "etf-broad-market-us-mid-cap",
    # ── COMMODITY (futures codes) ────────────────────────────────────────
    "CL=F": "commodity-energy-crude-oil-wti",
    "NG=F": "commodity-energy-natural-gas",
    "GC=F": "commodity-metal-gold",
    "SI=F": "commodity-metal-silver",
    "PL=F": "commodity-metal-platinum",
    "HG=F": "commodity-metal-copper",
    "ZS=F": "commodity-ag-soybean",
    "ZC=F": "commodity-ag-corn",
    "ZW=F": "commodity-ag-wheat",
    "CT=F": "commodity-ag-cotton",
    "KC=F": "commodity-ag-coffee",
    "SB=F": "commodity-ag-sugar",
    "XAUAUD": "commodity-metal-gold-aud",
    "XAUEUR": "commodity-metal-gold-eur",
    "NKD=F": "commodity-index-nikkei-usd",
    # ── BOND ─────────────────────────────────────────────────────────────
    "TLT": "bond-treasury-long-term",
    "IEF": "bond-treasury-intermediate",
    "SHY": "bond-treasury-short-term",
    "AGG": "bond-aggregate-us-broad",
    "EMB": "bond-emerging-market-usd",
    "HYG": "bond-high-yield-corp-us",
    "LQD": "bond-investment-grade-corp-us",
    "TIP": "bond-treasury-inflation-protected",
    "ZN=F": "bond-future-treasury-10y",
    # ── FUTURES ──────────────────────────────────────────────────────────
    "YM=F": "futures-index-dow-jones",
    "ES=F": "futures-index-spx-500",
    "NQ=F": "futures-index-nasdaq-100",
    "RTY=F": "futures-index-russell-2000",
}

# Class-level default (used for symbols not in SECTOR_MAP)
DEFAULT_SECTOR_BY_CLASS = {
    "CRYPTO": "crypto-other",
    "FOREX": "forex-other",
    "EQUITY": "equity-other",
    "STOCK": "equity-other",
    "STOCKS": "equity-other",
    "PENNY": "equity-penny",
    "PENNYSTOCK": "equity-penny",
    "ETF": "etf-other",
    "COMMODITY": "commodity-other",
    "BOND": "bond-other",
    "FUTURES": "futures-other",
    "INDEX": "index-other",
    "MEME": "crypto-meme",
    "UNKNOWN": "unknown",
    None: "unknown",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# trading_picks uses `category` (mixed-case + synonyms) instead of `asset_class`.
# Map category values to canonical asset_class labels (matches at_pick_outcomes.asset_class).
CATEGORY_TO_ASSET_CLASS = {
    "crypto": "CRYPTO",
    "forex": "FOREX", "FOREX": "FOREX",
    "commodity": "COMMODITY", "COMMODITY": "COMMODITY",
    "equity": "EQUITY", "EQUITY": "EQUITY",
    "stock": "STOCK", "stocks": "STOCKS", "STOCK": "STOCK", "STOCKS": "STOCKS",
    "etf": "ETF", "ETF": "ETF",
    "bond": "BOND", "BOND": "BOND",
    "futures": "FUTURES", "FUTURES": "FUTURES",
    "index": "INDEX", "INDEX": "INDEX",
    "meme": "MEME", "MEME": "MEME",
    "penny": "PENNY", "PENNY": "PENNY",
    "pennystock": "PENNYSTOCK", "PENNYSTOCK": "PENNYSTOCK",
    "": "UNKNOWN", None: "UNKNOWN",
}


def get_symbol_universe(cur) -> list:
    """
    Return list of (asset_class, symbol, at_pick_outcomes_rows, trading_picks_rows) tuples.
    - at_pick_outcomes has an `asset_class` column directly.
    - trading_picks has a `category` column (mixed case) which we map to canonical asset_class.
    """
    universe = {}

    # at_pick_outcomes: direct
    cur.execute(
        "SELECT asset_class, symbol, COUNT(*) c FROM `at_pick_outcomes` "
        "GROUP BY asset_class, symbol"
    )
    for r in cur.fetchall():
        key = (r["asset_class"], r["symbol"])
        universe.setdefault(key, {"at_pick_outcomes": 0, "trading_picks": 0})
        universe[key]["at_pick_outcomes"] = r["c"]

    # trading_picks: via `category` → asset_class
    cur.execute(
        "SELECT category, symbol, COUNT(*) c FROM `trading_picks` "
        "GROUP BY category, symbol"
    )
    for r in cur.fetchall():
        ac = CATEGORY_TO_ASSET_CLASS.get(r["category"], "UNKNOWN")
        key = (ac, r["symbol"])
        universe.setdefault(key, {"at_pick_outcomes": 0, "trading_picks": 0})
        universe[key]["trading_picks"] = r["c"]

    # Sort by total rows DESC for nicer output
    return sorted(
        ((k[0], k[1], v["at_pick_outcomes"], v["trading_picks"]) for k, v in universe.items()),
        key=lambda x: -(x[2] + x[3]),
    )


def classify_sector(asset_class: str, symbol: str) -> str:
    """Return the sector label for (asset_class, symbol), falling back to class default."""
    return SECTOR_MAP.get(symbol, DEFAULT_SECTOR_BY_CLASS.get(asset_class, "unknown"))


def fetch_ohlcv_metrics(cur, table: str, symbol: str, lookback: int = 90) -> dict | None:
    """
    Fetch the most-recent `lookback` OHLCV bars for a symbol and return:
      {
        'close_last':   float,
        'close_lookback': float  (close at index -lookback, or None if insufficient data),
        'atr14_pct':    float | None,  # 14d ATR / close as a percent
        'n_bars':       int,
      }
    Returns None if table is missing or no rows.
    """
    try:
        cur.execute(
            f"SELECT high, low, close FROM `{table}` WHERE symbol=%s "
            f"ORDER BY timestamp DESC LIMIT %s",
            (symbol, lookback),
        )
        rows = cur.fetchall()  # newest first
    except pymysql.err.ProgrammingError:
        return None  # table doesn't exist

    if not rows:
        return None
    rows = list(reversed(rows))  # chronological order now

    n_bars = len(rows)
    close_last = float(rows[-1]["close"])
    close_lookback = float(rows[0]["close"]) if n_bars >= lookback else None

    # 14d ATR (simple moving avg of True Range)
    atr14 = None
    if n_bars >= 15:
        trs = []
        for i in range(1, n_bars):
            h = float(rows[i]["high"])
            l = float(rows[i]["low"])
            pc = float(rows[i - 1]["close"])
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trs.append(tr)
        # Take the last 14 TRs (most recent window)
        atr14 = sum(trs[-14:]) / 14.0 if len(trs) >= 14 else None

    atr14_pct = (atr14 / close_last) if (atr14 is not None and close_last) else None

    return {
        "close_last": close_last,
        "close_lookback": close_lookback,
        "atr14_pct": atr14_pct,
        "n_bars": n_bars,
    }


def classify_regime(metrics: dict | None) -> str:
    """
    Map OHLCV metrics to a market_regime_id:
      - 3m return = close_last / close_lookback - 1
      - 20d vol proxy = atr14_pct (which is actually 14d ATR / close; close enough)
    Thresholds (deliberately conservative so we don't over-classify):
      ret >= +10%             -> BULL
      ret <= -10%             -> BEAR
      ret <= -15% & vol > 1.5 -> RISK_OFF
      vol > 2.0%              -> HIGH_VOL
      |ret| <  5%             -> SIDEWAYS
      else                    -> UNKNOWN (caught in between)
    """
    if metrics is None or metrics["n_bars"] < 30 or metrics["close_lookback"] in (None, 0):
        return "UNKNOWN"
    ret = metrics["close_last"] / metrics["close_lookback"] - 1
    vol = metrics["atr14_pct"] or 0

    if ret <= -0.15 and vol > 0.015:
        return "RISK_OFF"
    if ret <= -0.10:
        return "BEAR"
    if vol > 0.02:
        return "HIGH_VOL"
    if ret >= 0.10:
        return "BULL"
    if abs(ret) < 0.05:
        return "SIDEWAYS"
    return "UNKNOWN"


def batch_update_column(cur, table: str, col: str, values: list, batch_size: int = 1000) -> int:
    """
    Apply per-(asset_class, symbol, value) UPDATEs in batches.
    values = list of (asset_class, symbol, value) tuples.
    Returns total rows updated (estimate from cur.rowcount).

    Special handling for trading_picks: it uses `category` (not `asset_class`), so the
    WHERE clause is built per-table. The `asset_class` argument here is the CANONICAL
    form (matches at_pick_outcomes.asset_class); we re-derive the category value for
    trading_picks on the fly.
    """
    if not values:
        return 0

    # For trading_picks, the column that partitions the class is `category` (mixed-case).
    # Build a reverse map: canonical_asset_class -> [list of category values to match].
    REV = defaultdict(set)
    for cat, ac in CATEGORY_TO_ASSET_CLASS.items():
        if cat:
            REV[ac].add(cat)

    total = 0
    for i in range(0, len(values), batch_size):
        batch = values[i : i + batch_size]
        for asset_class, symbol, val in batch:
            if val is None:
                continue
            if table == "at_pick_outcomes":
                cur.execute(
                    f"UPDATE `{table}` SET `{col}`=%s "
                    f"WHERE asset_class=%s AND symbol=%s AND `{col}` IS NULL",
                    (val, asset_class, symbol),
                )
            else:  # trading_picks
                cat_values = list(REV.get(asset_class, set()))
                if not cat_values:
                    continue
                # Build a parameterized IN clause
                placeholders = ",".join(["%s"] * len(cat_values))
                cur.execute(
                    f"UPDATE `{table}` SET `{col}`=%s "
                    f"WHERE symbol=%s AND category IN ({placeholders}) AND `{col}` IS NULL",
                    (val, symbol, *cat_values),
                )
            total += cur.rowcount
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--apply", action="store_true", help="Execute updates. Without this, runs in dry-run mode.")
    ap.add_argument("--batch-size", type=int, default=1000, help="Rows per UPDATE batch (default: 1000).")
    args = ap.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== backfill_pillar_columns.py [{mode}] ===\n")
    t0 = time.time()

    conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()

    # ── Step 1: discover symbol universe ─────────────────────────────────
    print("── Step 1: discover symbol universe ──")
    universe = get_symbol_universe(cur)
    print(f"  distinct (asset_class, symbol) pairs: {len(universe)}\n")

    # ── Step 2: compute per-(class, symbol) sector + regime + ATR ───────
    print("── Step 2: compute sector + regime + ATR per symbol ──")
    sector_values = []      # (asset_class, symbol, sector_str)
    regime_values = []      # (asset_class, symbol, regime_str)
    atr_values = []         # (asset_class, symbol, atr14_pct)
    skipped_no_ohlcv = 0
    skipped_unknown = 0

    for asset_class, symbol, n_outcomes, n_picks in universe:
        # sector: always assignable (has class default)
        sector = classify_sector(asset_class, symbol)
        sector_values.append((asset_class, symbol, sector))

        # regime + ATR: need OHLCV. CRYPTO/EQUITY/STOCK/STOCKS/PENNY/PENNYSTOCK/ETF/MEME
        # are the only classes with OHLCV coverage in this DB.
        if asset_class in ("CRYPTO",):
            metrics = fetch_ohlcv_metrics(cur, "crypto_ohlcv", symbol)
        elif asset_class in ("EQUITY", "STOCK", "STOCKS", "PENNY", "PENNYSTOCK", "ETF", "MEME"):
            # MEME tickers are mostly crypto-flavored; try stock_ohlcv first then crypto
            metrics = fetch_ohlcv_metrics(cur, "stock_ohlcv", symbol)
            if metrics is None:
                metrics = fetch_ohlcv_metrics(cur, "crypto_ohlcv", symbol)
        else:
            metrics = None  # FOREX / COMMODITY / BOND / FUTURES / INDEX have no OHLCV tables

        if metrics is None:
            skipped_no_ohlcv += 1
            if asset_class in ("CRYPTO", "EQUITY", "STOCK", "STOCKS", "PENNY", "PENNYSTOCK", "ETF", "MEME"):
                skipped_unknown += 1
            # Leave regime/ATR NULL
            continue

        regime = classify_regime(metrics)
        atr_pct = metrics["atr14_pct"]
        regime_values.append((asset_class, symbol, regime))
        atr_values.append((asset_class, symbol, atr_pct))

    print(f"  sector assignments:   {len(sector_values)}")
    print(f"  regime assignments:   {len(regime_values)}")
    print(f"  ATR assignments:      {len(atr_values)}")
    print(f"  no-OHLCV skipped:     {skipped_no_ohlcv}  (of which surprising-class skipped: {skipped_unknown})")
    print()

    # ── Step 3: apply UPDATEs (batched) ─────────────────────────────────
    print("── Step 3: apply UPDATEs (batched per table) ──")
    coverage = {}
    for tbl in ("at_pick_outcomes", "trading_picks"):
        n_sec = batch_update_column(cur, tbl, "sector", sector_values, args.batch_size)
        n_reg = batch_update_column(cur, tbl, "market_regime_id", regime_values, args.batch_size)
        n_atr = batch_update_column(cur, tbl, "volatility_atr", atr_values, args.batch_size)
        coverage[tbl] = {"sector": n_sec, "market_regime_id": n_reg, "volatility_atr": n_atr}
        print(
            f"  {tbl:20s}  sector={n_sec:6d}  regime={n_reg:6d}  atr={n_atr:6d}"
        )

    if args.apply:
        conn.commit()
        print("\n[COMMITTED]")
    else:
        conn.rollback()
        print("\n[ROLLED BACK — dry-run, no changes]")

    # ── Step 4: post-coverage snapshot ─────────────────────────────────
    print("\n── Step 4: post-coverage snapshot ──")
    for tbl in ("at_pick_outcomes", "trading_picks"):
        cur.execute(f"SELECT COUNT(*) c FROM `{tbl}`")
        total = cur.fetchone()["c"]
        print(f"\n  {tbl} (total rows: {total})")
        for col in ("sector", "market_regime_id", "volatility_atr", "execution_slippage_pct"):
            cur.execute(f"SELECT COUNT(*) c FROM `{tbl}` WHERE `{col}` IS NOT NULL")
            n = cur.fetchone()["c"]
            pct = (100.0 * n / total) if total else 0
            print(f"    {col:25s} {n:7d} non-NULL  ({pct:5.1f}%)")
        # distribution of market_regime_id values
        cur.execute(
            f"SELECT market_regime_id v, COUNT(*) c FROM `{tbl}` "
            f"GROUP BY market_regime_id ORDER BY c DESC"
        )
        dist = ", ".join(f"{r['v']}={r['c']}" for r in cur.fetchall())
        print(f"    regime distribution: {dist}")

    elapsed = time.time() - t0
    print(f"\n=== done in {elapsed:.1f}s ===")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
