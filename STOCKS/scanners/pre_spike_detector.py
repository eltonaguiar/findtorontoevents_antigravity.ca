#!/usr/bin/env python3
"""
pre_spike_detector.py — Pre-Spike Early-Warning System (SIDU-style)

Catches penny/micro-cap runners BEFORE the spike tops out by scoring
pre-market signals: volume surge, gap-up, float compression, news freshness,
and short interest squeeze fuel.

Runs at 8am, 9am, 10am ET Mon-Fri (pre-market + first hour) via GitHub Actions.

Usage:
    python pre_spike_detector.py            # Full run, writes picks to JSON
    python pre_spike_detector.py --dry-run  # Print picks, no file writes
    python pre_spike_detector.py --force    # Run outside market hours (testing)
    python pre_spike_detector.py --min-score 70
"""

import argparse
import json
import logging
import os
import sys
import time
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from zoneinfo import ZoneInfo
    _TZ_ET = ZoneInfo("America/New_York")
except ImportError:
    _TZ_ET = None

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
PICKS_FILE = DATA_DIR / "pre_spike_picks.json"
FORWARD_PICKS_FILE = SCRIPT_DIR.parent / "competition" / "forward_picks.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MIN_SCORE_DEFAULT = 60
FORWARD_MIN_SCORE = 65   # minimum to append to forward_picks.json
TP_PCT = 1.00            # +100% take profit (penny runners can go 2-10x)
SL_PCT = 0.20            # -20% stop loss

PRE_FILTER = {
    "min_price": 0.20,
    "max_price": 15.00,
    "max_market_cap": 500_000_000,  # $500M
    "min_premarket_vol": 50_000,
    "max_news_age_hours": 72,
}


# ---------------------------------------------------------------------------
# Market / time helpers
# ---------------------------------------------------------------------------

def _now_et() -> datetime:
    if _TZ_ET is not None:
        return datetime.now(_TZ_ET)
    return datetime.now(timezone(timedelta(hours=-4)))


def in_pre_spike_window() -> bool:
    """True during 6am-10:30am ET Mon-Fri (pre-market + first hour)."""
    now = _now_et()
    if now.weekday() >= 5:
        return False
    window_open  = now.replace(hour=6,  minute=0,  second=0, microsecond=0)
    window_close = now.replace(hour=10, minute=30, second=0, microsecond=0)
    return window_open <= now <= window_close


def signal_stage() -> str:
    """PRE_SPIKE = before 9:30, EARLY = first 30 min, INTRADAY = rest of morning."""
    now = _now_et()
    open_time  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
    early_end  = now.replace(hour=10, minute=0,  second=0, microsecond=0)
    if now < open_time:
        return "PRE_SPIKE"
    if now <= early_end:
        return "EARLY"
    return "INTRADAY"


# ---------------------------------------------------------------------------
# Safe float helper
# ---------------------------------------------------------------------------

def _safe_float(val, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

def _get_watchlist() -> list[str]:
    try:
        # Reuse seed list from sibling scanner
        from top_gainers_scanner import _SEED_WATCHLIST
        seed = list(dict.fromkeys(_SEED_WATCHLIST))
    except ImportError:
        seed = [
            "SIDU", "CTRM", "INDO", "IMPP", "PROG", "MULN", "BBIG", "ATER",
            "SPRT", "ESSC", "IRNT", "OPAD", "GFAI", "TTOO", "MRIN", "TNXP",
            "RLMD", "EXPR", "GME", "AMC", "KOSS", "FFIE", "MMAT", "PHUN",
            "CLOV", "WKHS", "SPCE", "OCGN", "SHIP", "SEEL", "ZOM", "BNGO",
            "FCEL", "GNUS", "INPX", "JAGX", "NNDM", "SNDL", "UVXY",
        ]
    extra = os.environ.get("GAINER_WATCHLIST", "")
    if extra:
        for t in extra.split(","):
            t = t.strip().upper()
            if t and t not in seed:
                seed.append(t)
    # Drop delisted / renamed tickers (break yfinance, spam warnings).
    try:
        from delisted_symbols import filter_delisted
    except ImportError:
        from STOCKS.scanners.delisted_symbols import filter_delisted
    return filter_delisted(seed)


# ---------------------------------------------------------------------------
# Per-ticker enrichment
# ---------------------------------------------------------------------------

def _get_news_age_hours(ticker_obj) -> float:
    """Return hours since most recent news item. Returns 999 on error."""
    try:
        news = ticker_obj.news or []
        if not news:
            return 999.0
        timestamps = [n.get("providerPublishTime", 0) for n in news if n.get("providerPublishTime")]
        if not timestamps:
            return 999.0
        latest = max(timestamps)
        return max(0.0, (time.time() - latest) / 3600)
    except Exception:
        return 999.0


def enrich_ticker(symbol: str) -> dict | None:
    """Download pre-market data for a single ticker. Returns None on error/filter-fail."""
    import yfinance as yf

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        # Current / prev-close prices
        current_price = _safe_float(
            info.get("currentPrice") or info.get("regularMarketPrice") or info.get("ask")
        )
        if current_price <= 0:
            return None

        prev_close = _safe_float(info.get("previousClose") or info.get("regularMarketPreviousClose"))
        open_price = _safe_float(info.get("open") or info.get("regularMarketOpen"))
        market_cap = _safe_float(info.get("marketCap"))
        float_shares = _safe_float(info.get("floatShares"))

        # Pre-market data (may be 0 outside pre-market window)
        premarket_price = _safe_float(info.get("preMarketPrice"))
        premarket_vol   = _safe_float(info.get("preMarketVolume"))
        avg_daily_vol   = _safe_float(info.get("averageVolume") or info.get("averageDailyVolume10Day"))

        # Short interest
        short_pct_float = _safe_float(info.get("shortPercentOfFloat"))
        # yfinance returns 0.xx for percentages (e.g. 0.25 = 25%)
        if 0 < short_pct_float <= 1.0:
            short_pct_float *= 100  # convert to percent

        # Gap calculation — use pre-market price if available else current
        reference_price = premarket_price if premarket_price > 0 else current_price
        gap_pct = ((reference_price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0

        # Pre-market volume ratio (fraction of avg daily volume)
        # Typical pre-market avg is ~5% of regular daily volume
        avg_pm_vol = avg_daily_vol * 0.05 if avg_daily_vol > 0 else 1
        pm_vol_ratio = premarket_vol / avg_pm_vol if avg_pm_vol > 0 and premarket_vol > 0 else 0.0

        news_age_hours = _get_news_age_hours(ticker)

        return {
            "symbol": symbol,
            "current_price": current_price,
            "prev_close": prev_close,
            "open_price": open_price,
            "premarket_price": premarket_price,
            "premarket_vol": premarket_vol,
            "avg_daily_vol": avg_daily_vol,
            "pm_vol_ratio": pm_vol_ratio,
            "float_shares": float_shares,
            "market_cap": market_cap,
            "gap_pct": gap_pct,
            "short_pct_float": short_pct_float,
            "news_age_hours": news_age_hours,
        }
    except Exception as exc:
        log.debug(f"{symbol}: enrich failed — {exc}")
        return None


# ---------------------------------------------------------------------------
# Pre-filter
# ---------------------------------------------------------------------------

def passes_pre_filter(data: dict) -> tuple[bool, str]:
    price = data["current_price"]
    if price < PRE_FILTER["min_price"]:
        return False, f"price ${price:.4f} < ${PRE_FILTER['min_price']}"
    if price > PRE_FILTER["max_price"]:
        return False, f"price ${price:.2f} > ${PRE_FILTER['max_price']}"
    mc = data["market_cap"]
    if mc > 0 and mc > PRE_FILTER["max_market_cap"]:
        return False, f"market_cap ${mc/1e6:.0f}M > $500M"
    pm_vol = data["premarket_vol"]
    if pm_vol < PRE_FILTER["min_premarket_vol"]:
        return False, f"pre-market vol {pm_vol:.0f} < {PRE_FILTER['min_premarket_vol']}"
    news_h = data["news_age_hours"]
    if news_h > PRE_FILTER["max_news_age_hours"]:
        return False, f"news age {news_h:.0f}h > {PRE_FILTER['max_news_age_hours']}h"
    return True, ""


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def score_ticker(data: dict) -> tuple[int, dict]:
    """
    Score a ticker on pre-spike criteria.
    Returns (total_score, breakdown_dict).

    Signals (max 100):
      premarket_vol_surge  0-30 pts
      gap_up               0-25 pts
      float_compression    0-20 pts
      news_freshness       0-15 pts
      short_interest       0-10 pts
    """
    breakdown: dict[str, int] = {}

    # 1. Pre-market volume surge (0-30 pts)
    pmvr = data["pm_vol_ratio"]
    if pmvr >= 10:
        pvs = 30
    elif pmvr >= 5:
        pvs = 20
    elif pmvr >= 2:
        pvs = 10
    else:
        pvs = 0
    breakdown["premarket_vol_surge"] = pvs

    # 2. Gap-up at open vs prev close (0-25 pts)
    gap = data["gap_pct"]
    if gap >= 50:
        gu = 25
    elif gap >= 20:
        gu = 15
    elif gap >= 10:
        gu = 8
    elif gap >= 5:
        gu = 3
    else:
        gu = 0
    breakdown["gap_up"] = gu

    # 3. Float compression (0-20 pts)
    fl = data["float_shares"]
    if 0 < fl < 1_000_000:
        fc = 20
    elif fl < 5_000_000:
        fc = 15
    elif fl < 15_000_000:
        fc = 8
    elif fl < 50_000_000:
        fc = 3
    else:
        fc = 0
    breakdown["float_compression"] = fc

    # 4. News freshness (0-15 pts)
    nh = data["news_age_hours"]
    if nh < 6:
        nf = 15
    elif nh < 24:
        nf = 10
    elif nh < 48:
        nf = 5
    else:
        nf = 0
    breakdown["news_freshness"] = nf

    # 5. Short interest squeeze fuel (0-10 pts)
    si = data["short_pct_float"]
    if si >= 20:
        sq = 10
    elif si >= 10:
        sq = 5
    else:
        sq = 0
    breakdown["short_interest"] = sq

    total = sum(breakdown.values())
    return total, breakdown


# ---------------------------------------------------------------------------
# Pick builder
# ---------------------------------------------------------------------------

def build_pick(data: dict, score: int, breakdown: dict, stage: str) -> dict:
    entry = data["current_price"]
    tp_price = round(entry * (1 + TP_PCT), 4)
    sl_price = round(entry * (1 - SL_PCT), 4)
    risk_reward = round(TP_PCT / SL_PCT, 2)
    confidence = round(min(score / 100, 1.0), 4)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_et_str = _now_et().strftime("%Y-%m-%d %H:%M:%S %Z")
    expiry = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")

    fl = data["float_shares"]
    float_str = f"{fl/1_000_000:.1f}M" if fl > 0 else "unknown"
    pm_vol_str = f"{data['pm_vol_ratio']:.1f}x avg PM vol" if data["pm_vol_ratio"] > 0 else "n/a"

    reasons: dict = {
        "premarket_vol_surge": pm_vol_str,
        "gap_pct": f"{data['gap_pct']:.1f}%",
        "float": float_str,
        "news_age_hours": f"{data['news_age_hours']:.0f}h",
        "short_interest_pct": f"{data['short_pct_float']:.1f}%",
    }

    if 0 < fl < 10_000_000:
        reasons["squeeze_potential"] = "HIGH — float < 10M shares"
    if data["short_pct_float"] >= 20:
        reasons["short_squeeze_fuel"] = f"Short interest {data['short_pct_float']:.1f}% of float"

    pick_id = f"pre_spike_{data['symbol']}_{today}"

    return {
        "id": pick_id,
        "algorithm": "Pre-Spike Detector",
        "algo_type": "PreSpike",
        "asset_class": "penny_stocks",
        "asset_label": "Penny / Micro-Cap Stocks",
        "signal_stage": stage,
        "ticker": data["symbol"],
        "symbol": data["symbol"],
        "action": "BUY",
        "direction": "LONG",
        "entry_price": round(entry, 4),
        "tp_price": tp_price,
        "take_profit": tp_price,
        "sl_price": sl_price,
        "stop_loss": sl_price,
        "tp_pct": round(TP_PCT * 100, 1),
        "sl_pct": round(SL_PCT * 100, 1),
        "score": confidence,
        "score_raw": score,
        "confidence": confidence,
        "score_breakdown": breakdown,
        "reasons": reasons,
        "risk_reward": risk_reward,
        "generated_at": now_et_str,
        "generated_date": today,
        "expiry_date": expiry,
        "hold_days_max": 2,
        "status": "OPEN",
        "prev_close": data["prev_close"],
        "market_cap": data["market_cap"],
        "float_shares": fl,
        "gap_pct": round(data["gap_pct"], 2),
        "pm_vol_ratio": round(data["pm_vol_ratio"], 2),
        "short_pct_float": round(data["short_pct_float"], 2),
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
    tmp = FORWARD_PICKS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(FORWARD_PICKS_FILE)


def append_to_forward_picks(picks: list[dict]) -> int:
    """Append qualifying picks to forward_picks.json; skip duplicates by id."""
    payload = _load_forward_picks()
    existing_ids: set[str] = {p.get("id", "") for p in payload.get("picks", [])}
    added = 0
    for pick in picks:
        if pick["score_raw"] < FORWARD_MIN_SCORE:
            continue
        pick_id = pick.get("id", "")
        if pick_id and pick_id not in existing_ids:
            payload["picks"].append(pick)
            existing_ids.add(pick_id)
            added += 1
    if added:
        _save_forward_picks(payload)
        log.info(f"Appended {added} picks to forward_picks.json")
    return added


# ---------------------------------------------------------------------------
# Atomic file write
# ---------------------------------------------------------------------------

def _write_picks_file(picks: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    scan_output = {
        "scan_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "picks_count": len(picks),
        "picks": picks,
    }
    tmp = PICKS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(scan_output, f, indent=2)
    tmp.replace(PICKS_FILE)
    log.info(f"Saved {len(picks)} picks → {PICKS_FILE}")


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------

def run_scan(dry_run: bool = False, min_score: int = MIN_SCORE_DEFAULT) -> list[dict]:
    watchlist = _get_watchlist()
    stage = signal_stage()
    log.info(f"Pre-spike scan | stage={stage} | {len(watchlist)} tickers | min_score={min_score}")

    import yfinance as yf

    picks: list[dict] = []
    filtered = skipped = 0

    for symbol in watchlist:
        data = enrich_ticker(symbol)
        if data is None:
            skipped += 1
            continue

        ok, reason = passes_pre_filter(data)
        if not ok:
            log.debug(f"{symbol}: filtered — {reason}")
            filtered += 1
            continue

        score, breakdown = score_ticker(data)
        log.info(
            f"{symbol}: score={score} | "
            f"pm_vol={data['pm_vol_ratio']:.1f}x | "
            f"gap={data['gap_pct']:.1f}% | "
            f"float={data['float_shares']/1e6:.1f}M | "
            f"news={data['news_age_hours']:.0f}h | "
            f"short={data['short_pct_float']:.1f}%"
        )

        if score >= min_score:
            pick = build_pick(data, score, breakdown, stage)
            picks.append(pick)

    picks.sort(key=lambda p: p["score_raw"], reverse=True)

    log.info(
        f"\nScan complete: {len(picks)} picks | "
        f"{filtered} pre-filtered | {skipped} fetch-failed"
    )
    if picks:
        log.info(f"{'='*60}")
        log.info(f"PRE-SPIKE PICKS ({len(picks)} found, stage={stage})")
        log.info("="*60)
        for p in picks:
            log.info(
                f"  {p['ticker']:8s} score={p['score_raw']:3d} | "
                f"entry=${p['entry_price']:.2f} | "
                f"TP=${p['tp_price']:.2f} | "
                f"gap={p['reasons']['gap_pct']} | "
                f"stage={p['signal_stage']}"
            )

    if dry_run:
        log.info("[dry-run] No files written.")
        return picks

    _write_picks_file(picks)
    if FORWARD_PICKS_FILE.parent.exists():
        append_to_forward_picks(picks)

    return picks


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-Spike Early Warning Detector")
    parser.add_argument("--dry-run",   action="store_true", help="Print picks only, no file writes")
    parser.add_argument("--force",     action="store_true", help="Run outside the pre-spike window")
    parser.add_argument("--min-score", type=int, default=MIN_SCORE_DEFAULT, help="Minimum score threshold")
    args = parser.parse_args()

    if not args.force and not in_pre_spike_window():
        log.info(
            f"Outside pre-spike window ({_now_et().strftime('%H:%M %Z')}). "
            "Use --force to run anyway."
        )
        _write_picks_file([])
        return 0

    try:
        import yfinance  # noqa: F401
    except ImportError:
        log.error("yfinance not installed. Run: pip install yfinance")
        return 1

    picks = run_scan(dry_run=args.dry_run, min_score=args.min_score)
    return 0


if __name__ == "__main__":
    sys.exit(main())
