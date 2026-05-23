#!/usr/bin/env python3
"""
Top Gainers / Spike Detector (SIDU-style penny runner scanner)

Catches low-float, high-volume penny stocks BEFORE the spike tops out.
Runs every 30 min during US market hours via GitHub Actions.

Usage:
    python top_gainers_scanner.py            # Full run, writes picks to JSON
    python top_gainers_scanner.py --dry-run  # Print picks, no file writes
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    _TZ_ET = ZoneInfo("America/New_York")
except ImportError:
    _TZ_ET = None  # fallback: use fixed offset below

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
PICKS_FILE = DATA_DIR / "top_gainers_picks.json"
FORWARD_PICKS_FILE = SCRIPT_DIR.parent / "competition" / "forward_picks.json"

# ---------------------------------------------------------------------------
# Market hours helpers  (America/New_York handles EST/EDT automatically)
# ---------------------------------------------------------------------------

def _now_et() -> datetime:
    if _TZ_ET is not None:
        return datetime.now(_TZ_ET)
    # Fallback: approximate EDT offset (-4). During EST (Nov-Mar) this is off by 1h
    # but the market-hours check still works conservatively.
    return datetime.now(timezone(timedelta(hours=-4)))


def market_is_open() -> bool:
    """Return True if US market is currently open (approx 9:30-16:00 ET, Mon-Fri)."""
    now = _now_et()
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close


# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------
MIN_SCORE_FOR_PICK = 60
# SEC/industry definition: penny stock = price under $5; we use $10 to also catch
# micro-cap runners that have already gapped but remain low-float candidates.
MAX_PENNY_PRICE = 10.0
TP_PCT = 0.40   # +40% take profit
SL_PCT = 0.15   # -15% stop loss (wider for penny runners)


# ---------------------------------------------------------------------------
# Data fetching — yfinance primary, Finviz HTML fallback
# ---------------------------------------------------------------------------

def _fetch_yfinance_gainers() -> list[str]:
    """
    Pull a broad watchlist of penny/small-cap tickers and return those that
    are up significantly today.  yfinance doesn't expose a live screener, so
    we maintain a seed list of known runners / micro-cap universe and filter.
    """
    import yfinance as yf

    # Seed watchlist: well-known volatile small-caps + common runner tickers
    seed = [
        # Historical runners / frequently active micro-caps
        "SIDU", "CTRM", "INDO", "IMPP", "PROG", "MULN", "BBIG", "ATER",
        "SPRT", "ESSC", "IRNT", "OPAD", "GFAI", "TTOO", "MRIN", "TNXP",
        "RLMD", "EXPR", "GME", "AMC", "KOSS", "NAKD", "AGTC", "NKLA",
        "FFIE", "MMAT", "PHUN", "GREE", "EBON", "ANY", "IDEX", "OBSV",
        "CLOV", "WISH", "WKHS", "RIDE", "SKLZ", "SPCE", "SENS", "OCGN",
        "SHIP", "SEEL", "HOFV", "ZEST", "ABIO", "CRIS", "DBVT", "GTHX",
        "NLST", "PALI", "RELI", "SURF", "TPVG", "VERB", "WKSP", "XSPA",
        "ZOM", "BNGO", "CIDM", "CLPS", "DGLY", "ENSG", "EYES", "FCEL",
        "GNUS", "HYLN", "INPX", "JAGX", "KBNT", "LODE", "MGNI", "NNDM",
        "OPK", "PRTS", "QFIN", "RSSS", "SNDL", "TORC", "UVXY", "VVPR",
        # Add more via environment variable GAINER_WATCHLIST if needed
    ]

    import os
    extra = os.environ.get("GAINER_WATCHLIST", "")
    if extra:
        seed += [t.strip().upper() for t in extra.split(",") if t.strip()]

    # Drop delisted / renamed tickers — they return all-NaN from yfinance,
    # spam "possibly delisted" warnings, and waste API calls.
    try:
        from delisted_symbols import filter_delisted
    except ImportError:
        from STOCKS.scanners.delisted_symbols import filter_delisted
    _before = len(seed)
    seed = filter_delisted(seed)
    if len(seed) != _before:
        log.info(f"Filtered {_before - len(seed)} delisted ticker(s) from seed list")

    gainers: list[str] = []
    log.info(f"Checking {len(seed)} seed tickers via yfinance …")

    # Batch download 1-day data
    try:
        data = yf.download(
            seed,
            period="2d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if data.empty:
            return gainers

        closes = data["Close"]
        if isinstance(closes, pd.Series):
            closes = closes.to_frame()

        if len(closes) < 2:
            return gainers

        prev_close = closes.iloc[-2]
        today_close = closes.iloc[-1]
        pct_change = ((today_close - prev_close) / prev_close * 100).dropna()
        gainers = list(pct_change[pct_change >= 5].index)
        log.info(f"yfinance: {len(gainers)} tickers up ≥5% today from seed list")
    except Exception as exc:
        log.warning(f"yfinance batch download failed: {exc}")

    return gainers


def _fetch_finviz_gainers() -> list[str]:
    """Scrape Finviz top gainers page — fallback only."""
    import requests
    from bs4 import BeautifulSoup

    url = "https://finviz.com/screener.ashx?v=111&s=ta_topgainers&f=cap_microunder"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        tickers: list[str] = []
        for a in soup.select("a.screener-link-primary"):
            t = a.get_text(strip=True)
            if t and t.isalpha() and len(t) <= 5:
                tickers.append(t.upper())
        log.info(f"Finviz: found {len(tickers)} top-gainer tickers")
        return tickers[:50]  # cap to avoid hammering yfinance
    except Exception as exc:
        log.warning(f"Finviz scrape failed: {exc}")
        return []


def get_gainer_candidates() -> list[str]:
    """Return de-duped list of candidate ticker symbols."""
    tickers = _fetch_yfinance_gainers()
    if not tickers:
        log.info("yfinance seed gave 0 results, trying Finviz fallback …")
        tickers = _fetch_finviz_gainers()
    if not tickers:
        log.warning("All sources returned 0 gainers.")
    seen: set[str] = set()
    unique = []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


# ---------------------------------------------------------------------------
# Per-ticker enrichment via yfinance
# ---------------------------------------------------------------------------

def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None and not (isinstance(val, float) and np.isnan(val)) else default
    except Exception:
        return default


def enrich_ticker(symbol: str) -> dict | None:
    """Download detailed data for a single ticker. Returns None on error."""
    import yfinance as yf

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        # Current price / day stats
        current_price = _safe_float(
            info.get("currentPrice") or info.get("regularMarketPrice") or info.get("ask")
        )
        if current_price <= 0:
            return None

        prev_close = _safe_float(info.get("previousClose") or info.get("regularMarketPreviousClose"))
        open_price = _safe_float(info.get("open") or info.get("regularMarketOpen"))
        day_high = _safe_float(info.get("dayHigh") or info.get("regularMarketDayHigh"))
        day_low = _safe_float(info.get("dayLow") or info.get("regularMarketDayLow"))
        volume_today = _safe_float(info.get("volume") or info.get("regularMarketVolume"))
        avg_volume = _safe_float(info.get("averageVolume") or info.get("averageDailyVolume10Day"))
        float_shares = _safe_float(info.get("floatShares"))
        market_cap = _safe_float(info.get("marketCap"))

        # Derived metrics
        day_change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
        vol_ratio = (volume_today / avg_volume) if avg_volume > 0 else 0.0
        price_vs_open = ((current_price - open_price) / open_price * 100) if open_price > 0 else 0.0
        gap_pct = ((open_price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0

        # News freshness: check most recent news headline date
        news_age_days = _get_news_age(ticker)

        return {
            "symbol": symbol,
            "current_price": current_price,
            "prev_close": prev_close,
            "open_price": open_price,
            "day_high": day_high,
            "day_low": day_low,
            "volume_today": volume_today,
            "avg_volume": avg_volume,
            "float_shares": float_shares,
            "market_cap": market_cap,
            "day_change_pct": day_change_pct,
            "vol_ratio": vol_ratio,
            "price_vs_open": price_vs_open,
            "gap_pct": gap_pct,
            "news_age_days": news_age_days,
        }
    except Exception as exc:
        log.debug(f"{symbol}: enrich failed — {exc}")
        return None


def _get_news_age(ticker) -> float:
    """Return days since most recent news item (0 = today). Returns 99 on error."""
    try:
        news = ticker.news or []
        if not news:
            return 99.0
        # news items have 'providerPublishTime' as Unix timestamp
        timestamps = [n.get("providerPublishTime", 0) for n in news if n.get("providerPublishTime")]
        if not timestamps:
            return 99.0
        latest = max(timestamps)
        age_sec = time.time() - latest
        return max(0.0, age_sec / 86400)
    except Exception:
        return 99.0


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def score_ticker(data: dict) -> tuple[int, dict]:
    """
    Score a ticker on SIDU-style spike criteria.
    Returns (total_score 0-100, breakdown_dict).
    """
    breakdown: dict[str, int] = {}

    # 1. Volume surge (0-25 pts)
    vr = data["vol_ratio"]
    if vr >= 5.0:        # >500%
        vs = 25
    elif vr >= 2.0:      # 200-500%
        vs = 15
    elif vr >= 1.0:      # 100-200%
        vs = 8
    else:
        vs = 0
    breakdown["vol_surge"] = vs

    # 2. Price momentum — day change % (0-25 pts)
    dc = data["day_change_pct"]
    if dc >= 50:
        pm = 25
    elif dc >= 20:
        pm = 15
    elif dc >= 10:
        pm = 8
    elif dc >= 5:
        pm = 3
    else:
        pm = 0
    breakdown["price_momentum"] = pm

    # 3. Float quality (0-20 pts)
    fl = data["float_shares"]
    if 0 < fl < 1_000_000:
        fq = 20
    elif fl < 5_000_000:
        fq = 15
    elif fl < 10_000_000:
        fq = 10
    elif fl < 50_000_000:
        fq = 5
    else:
        fq = 0  # also 0 if unknown (fl==0)
    breakdown["float_quality"] = fq

    # 4. Gap continuation — price vs open (0-15 pts)
    pvo = data["price_vs_open"]
    if pvo >= 0:         # still at or above open
        gc = 15
    elif pvo >= -5:      # slight fade but holding
        gc = 5
    else:
        gc = 0
    breakdown["gap_continuation"] = gc

    # 5. Catalyst freshness — news age (0-15 pts)
    na = data["news_age_days"]
    if na < 1:           # today
        cf = 15
    elif na < 2:         # yesterday
        cf = 8
    else:
        cf = 0
    breakdown["catalyst_freshness"] = cf

    total = sum(breakdown.values())
    return total, breakdown


# ---------------------------------------------------------------------------
# Pick builder
# ---------------------------------------------------------------------------

def build_pick(data: dict, score: int, breakdown: dict) -> dict:
    entry = data["current_price"]
    take_profit = round(entry * (1 + TP_PCT), 4)
    stop_loss = round(entry * (1 - SL_PCT), 4)
    risk_reward = round(TP_PCT / SL_PCT, 2)
    confidence = round(score / 100, 4)

    float_str = (
        f"{data['float_shares'] / 1_000_000:.1f}M"
        if data["float_shares"] > 0
        else "unknown"
    )
    vol_surge_str = f"{data['vol_ratio'] * 100:.0f}%" if data["vol_ratio"] > 0 else "n/a"
    day_gain_str = f"{data['day_change_pct']:.1f}%"

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "symbol": data["symbol"],
        "strategy": "top_gainers_momentum",
        "direction": "LONG",
        "entry_price": round(entry, 4),
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "confidence": confidence,
        "risk_reward": risk_reward,
        "score": score,
        "score_breakdown": breakdown,
        "reasons": {
            "vol_surge": vol_surge_str,
            "float": float_str,
            "day_gain": day_gain_str,
            "gap_pct": f"{data['gap_pct']:.1f}%",
            "price_vs_open": f"{data['price_vs_open']:.1f}%",
        },
        "asset_class": "EQUITY",
        "category": "penny_stocks",
        "hold_days": 1,
        "timestamp": now_utc,
        "status": "OPEN",
        # Extra context for resolution tracking
        "prev_close": data["prev_close"],
        "market_cap": data["market_cap"],
        "float_shares": data["float_shares"],
    }


# ---------------------------------------------------------------------------
# Forward picks integration
# ---------------------------------------------------------------------------

def _load_forward_picks() -> dict:
    try:
        with open(FORWARD_PICKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"picks": []}


def _save_forward_picks(payload: dict) -> None:
    with open(FORWARD_PICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def append_to_forward_picks(picks: list[dict]) -> int:
    """Append new picks to forward_picks.json; skip duplicates. Returns count added."""
    payload = _load_forward_picks()
    existing_keys: set[str] = {
        p.get("symbol", "") + "_" + p.get("strategy", "") + "_" + p.get("timestamp", "")[:10]
        for p in payload.get("picks", [])
    }
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    added = 0
    for pick in picks:
        key = f"{pick['symbol']}_top_gainers_momentum_{today}"
        if key not in existing_keys:
            payload["picks"].append(pick)
            existing_keys.add(key)
            added += 1
    if added:
        _save_forward_picks(payload)
    return added


# ---------------------------------------------------------------------------
# Main scan logic
# ---------------------------------------------------------------------------

def run_scan(dry_run: bool = False) -> list[dict]:
    """
    Run a full top-gainers scan.
    Returns list of picks that scored above threshold.
    """
    candidates = get_gainer_candidates()
    if not candidates:
        log.warning("No gainer candidates found — nothing to score.")
        return []

    log.info(f"Enriching {len(candidates)} candidates …")
    picks: list[dict] = []

    for symbol in candidates:
        data = enrich_ticker(symbol)
        if data is None:
            continue

        # Pre-filter: must be a genuine penny/micro-cap (see MAX_PENNY_PRICE constant)
        if data["current_price"] > MAX_PENNY_PRICE:
            log.debug(f"{symbol}: price ${data['current_price']:.2f} > $10, skipping")
            continue

        # Must be up at least 5% today
        if data["day_change_pct"] < 5:
            continue

        score, breakdown = score_ticker(data)
        log.info(
            f"{symbol}: score={score} | "
            f"vol={data['vol_ratio']:.1f}x | "
            f"day={data['day_change_pct']:.1f}% | "
            f"float={data['float_shares']/1e6:.1f}M | "
            f"price=${data['current_price']:.2f}"
        )

        if score >= MIN_SCORE_FOR_PICK:
            pick = build_pick(data, score, breakdown)
            picks.append(pick)

    picks.sort(key=lambda p: p["score"], reverse=True)

    if not picks:
        log.info("No picks met the minimum score threshold.")
        return []

    log.info(f"\n{'='*60}")
    log.info(f"TOP GAINERS PICKS ({len(picks)} found, min score {MIN_SCORE_FOR_PICK})")
    log.info("="*60)
    for p in picks:
        log.info(
            f"  {p['symbol']:8s} score={p['score']:3d} | "
            f"entry=${p['entry_price']:.2f} | "
            f"TP=${p['take_profit']:.2f} | "
            f"SL=${p['stop_loss']:.2f} | "
            f"vol={p['reasons']['vol_surge']} | "
            f"float={p['reasons']['float']} | "
            f"day={p['reasons']['day_gain']}"
        )

    if dry_run:
        log.info("[DRY RUN] Not writing any files.")
        return picks

    # Save current scan results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    scan_output = {
        "scan_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "picks_count": len(picks),
        "picks": picks,
    }
    with open(PICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(scan_output, f, indent=2)
    log.info(f"Saved {len(picks)} picks → {PICKS_FILE}")

    # Append to forward picks if file exists
    if FORWARD_PICKS_FILE.exists():
        added = append_to_forward_picks(picks)
        log.info(f"Appended {added} new picks → {FORWARD_PICKS_FILE}")
    else:
        log.warning(f"forward_picks.json not found at {FORWARD_PICKS_FILE}, skipping append")

    return picks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Top Gainers / Spike Detector (SIDU-style)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print picks but do not write any files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even when market is closed (for testing)",
    )
    args = parser.parse_args()

    if not args.force and not market_is_open():
        log.info("Market is currently closed. Use --force to override. Exiting cleanly.")
        return 0

    picks = run_scan(dry_run=args.dry_run)

    if picks:
        log.info(f"Scan complete — {len(picks)} actionable picks found.")
    else:
        log.info("Scan complete — no picks this cycle.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
