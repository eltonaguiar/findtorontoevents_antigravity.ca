#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Equity 52-Week High + Volume Breakout Scanner
==============================================================
Implements the George & Hwang (2004, J Finance) 52-week high momentum signal.
Empirical WR lift: +8-12% vs baseline per swarm consensus.

Signal logic (LONG only):
  - Price within 3% of 52-week high  (proximity threshold configurable)
  - Today's volume >= 1.5x 20-day average volume  (volume confirmation)

Picks flow: active_picks.json → score_pick() → quality_gates.py → dashboard

Run modes:
  python alpha_engine/equity_breakout_scanner.py              # live run
  python alpha_engine/equity_breakout_scanner.py --dry-run   # no writes
  python alpha_engine/equity_breakout_scanner.py --symbols AAPL,MSFT,NVDA
  python alpha_engine/equity_breakout_scanner.py --top-n 50

Academic basis: George, T.J. & Hwang, C.-Y. (2004). The 52-Week High and
  Momentum Investing. Journal of Finance, 59(5), 2145-2176.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default large-cap universe (30 names, always scanned)
DEFAULT_SYMBOLS: list[str] = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "BRK-B", "JPM", "V",
    "UNH", "XOM", "LLY", "JNJ", "WMT",
    "MA", "AVGO", "PG", "HD", "CVX",
    "MRK", "ABBV", "COST", "KO", "PEP",
    "BAC", "TMO", "CSCO", "ACN", "MCD",
]

# Signal thresholds
PCT_FROM_HIGH_THRESHOLD: float = 0.03   # within 3% of 52-week high
VOLUME_RATIO_THRESHOLD: float = 1.5     # today's vol >= 1.5x 20-day avg
VOLUME_LOOKBACK_DAYS: int = 20          # days to compute avg volume

# Pick geometry
TAKE_PROFIT_PCT: float = 0.08   # 8% TP
STOP_LOSS_PCT: float = 0.05     # 5% SL

# Deduplication window: skip if open equity_breakout pick for same symbol
# exists AND was entered within this many calendar days.
DEDUP_WINDOW_DAYS: int = 5

# Source / strategy identifiers
SOURCE_NAME: str = "equity_breakout_scanner"
STRATEGY_NAME: str = "52wk_high_breakout"

# Path to active picks file (relative to repo root)
_REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_PICKS_PATH = _REPO_ROOT / "alpha_engine" / "data" / "active_picks.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _sanitize_float(v: Any) -> Any:
    """Replace NaN/Infinity with None so json.dump never raises."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def _compute_confidence(pct_from_high: float, volume_ratio: float) -> float:
    """
    Blend two sub-scores into [0, 1]:
      - proximity score: 1.0 when price == 52wk high, 0.0 at threshold
      - volume score: capped at 1.0 when volume_ratio >= 3x, 0 at threshold

    Final confidence = 0.6 * proximity + 0.4 * volume (capped at 0.95).
    """
    # pct_from_high is 0..0.03 when signal fires (0 = at the high)
    proximity = max(0.0, 1.0 - pct_from_high / PCT_FROM_HIGH_THRESHOLD)

    # volume_ratio >= VOLUME_RATIO_THRESHOLD guaranteed at call site
    vol_excess = volume_ratio - VOLUME_RATIO_THRESHOLD
    vol_max_excess = 3.0 - VOLUME_RATIO_THRESHOLD   # 3x is "max"
    volume_score = min(1.0, vol_excess / max(vol_max_excess, 0.001))

    raw = 0.6 * proximity + 0.4 * volume_score
    return round(min(0.95, max(0.05, raw)), 4)


# ---------------------------------------------------------------------------
# Symbol universe
# ---------------------------------------------------------------------------

def _equity_symbols_from_active_picks(active_picks_path: Path) -> list[str]:
    """Extract distinct EQUITY symbols from the existing active picks file."""
    if not active_picks_path.exists():
        return []
    try:
        with open(active_picks_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        picks = data if isinstance(data, list) else data.get("picks", [])
        return list({
            p["symbol"]
            for p in picks
            if isinstance(p, dict)
            and str(p.get("asset_class", "")).upper() == "EQUITY"
            and p.get("symbol")
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read EQUITY symbols from active_picks: %s", exc)
        return []


def build_symbol_universe(
    extra_symbols: list[str] | None = None,
    top_n: int | None = None,
    active_picks_path: Path = ACTIVE_PICKS_PATH,
) -> list[str]:
    """
    Merge DEFAULT_SYMBOLS + EQUITY symbols already in active_picks + any
    caller-supplied extras. Deduplicate, preserve order, optionally cap.
    """
    seen: set[str] = set()
    universe: list[str] = []

    def _add(sym: str) -> None:
        s = sym.strip().upper()
        if s and s not in seen:
            seen.add(s)
            universe.append(s)

    for s in DEFAULT_SYMBOLS:
        _add(s)
    for s in _equity_symbols_from_active_picks(active_picks_path):
        _add(s)
    for s in (extra_symbols or []):
        _add(s)

    if top_n is not None and top_n > 0:
        return universe[:top_n]
    return universe


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _load_active_picks(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else data.get("picks", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load active_picks: %s", exc)
        return []


def _is_duplicate(symbol: str, existing: list[dict], today: str) -> bool:
    """
    Return True if there is already an open equity_breakout pick for
    *symbol* with entry_date within DEDUP_WINDOW_DAYS of today.
    """
    try:
        today_dt = datetime.fromisoformat(today).date()
    except ValueError:
        return False

    for p in existing:
        if not isinstance(p, dict):
            continue
        if str(p.get("symbol", "")).upper() != symbol.upper():
            continue
        if str(p.get("source", "")).lower() != SOURCE_NAME:
            continue
        if str(p.get("status", "")).lower() not in ("open", "active"):
            continue
        entry_raw = p.get("entry_date", "")
        try:
            entry_dt = datetime.fromisoformat(str(entry_raw)[:10]).date()
        except ValueError:
            continue
        if abs((today_dt - entry_dt).days) <= DEDUP_WINDOW_DAYS:
            return True
    return False


# ---------------------------------------------------------------------------
# Signal generation (per-symbol)
# ---------------------------------------------------------------------------

def _fetch_symbol_data(symbol: str) -> dict | None:
    """
    Fetch 52-week high, current close, and volume stats via yfinance.
    Returns a dict with keys: close, fifty_two_week_high, today_volume,
    avg_volume_20d — or None on any failure (fail-open).
    """
    try:
        import yfinance as yf  # lazy import so tests can patch at module level
    except ImportError:
        logger.error("yfinance not installed — cannot fetch %s", symbol)
        return None

    try:
        ticker = yf.Ticker(symbol)

        # Fetch info for 52-week high
        info = ticker.info or {}
        fifty_two_week_high = info.get("fiftyTwoWeekHigh")

        # Fetch recent OHLCV history for close + volume
        hist = ticker.history(period="3mo", auto_adjust=True)
        if hist is None or hist.empty or len(hist) < VOLUME_LOOKBACK_DAYS:
            logger.warning("%s: insufficient history (%s bars)", symbol,
                           len(hist) if hist is not None else 0)
            return None

        close = float(hist["Close"].iloc[-1])
        today_volume = float(hist["Volume"].iloc[-1])
        avg_volume_20d = float(hist["Volume"].iloc[-VOLUME_LOOKBACK_DAYS:].mean())

        # Validate
        if not fifty_two_week_high or fifty_two_week_high <= 0:
            logger.warning("%s: invalid fiftyTwoWeekHigh=%s", symbol, fifty_two_week_high)
            return None
        if close <= 0:
            logger.warning("%s: invalid close=%s", symbol, close)
            return None
        if avg_volume_20d <= 0:
            logger.warning("%s: zero avg volume", symbol)
            return None

        return {
            "close": close,
            "fifty_two_week_high": float(fifty_two_week_high),
            "today_volume": today_volume,
            "avg_volume_20d": avg_volume_20d,
        }

    except Exception as exc:  # noqa: BLE001 — fail-open per spec
        logger.warning("%s: yfinance error — %s", symbol, exc)
        return None


def _check_breakout(data: dict) -> dict | None:
    """
    Apply breakout conditions. Returns a dict of signal fields on pass,
    None if conditions are not met.
    """
    close = data["close"]
    high_52w = data["fifty_two_week_high"]
    today_vol = data["today_volume"]
    avg_vol = data["avg_volume_20d"]

    pct_from_high = (high_52w - close) / high_52w
    volume_ratio = today_vol / avg_vol

    if pct_from_high > PCT_FROM_HIGH_THRESHOLD:
        return None  # price too far below 52-week high
    if volume_ratio < VOLUME_RATIO_THRESHOLD:
        return None  # insufficient volume confirmation

    return {
        "pct_from_high": pct_from_high,
        "volume_ratio": volume_ratio,
    }


def _build_pick(symbol: str, data: dict, signal: dict, today: str) -> dict:
    """Construct a fully-populated pick dict matching quality_gates.py requirements."""
    close = data["close"]
    volume_ratio = signal["volume_ratio"]
    pct_from_high = signal["pct_from_high"]

    confidence = _compute_confidence(pct_from_high, volume_ratio)

    return {
        "id": f"eq_breakout_{symbol}_{today}",
        "symbol": symbol,
        "asset_class": "EQUITY",
        "direction": "LONG",
        "source": SOURCE_NAME,
        "strategy": STRATEGY_NAME,
        "status": "open",
        "confidence": confidence,
        "entry_price": _sanitize_float(close),
        "take_profit": _sanitize_float(round(close * (1.0 + TAKE_PROFIT_PCT), 4)),
        "stop_loss": _sanitize_float(round(close * (1.0 - STOP_LOSS_PCT), 4)),
        "entry_date": today,
        "extra": {
            "pct_from_52wk_high": _sanitize_float(round(pct_from_high, 6)),
            "volume_ratio": _sanitize_float(round(volume_ratio, 4)),
            "fifty_two_week_high": _sanitize_float(data["fifty_two_week_high"]),
        },
    }


# ---------------------------------------------------------------------------
# Main scanner logic
# ---------------------------------------------------------------------------

def run_scanner(
    symbols: list[str] | None = None,
    top_n: int | None = None,
    dry_run: bool = False,
    active_picks_path: Path = ACTIVE_PICKS_PATH,
) -> list[dict]:
    """
    Scan *symbols* for 52-week high + volume breakouts.

    Args:
        symbols:  Override symbol list. If None, use build_symbol_universe().
        top_n:    Cap the universe size (passed to build_symbol_universe when
                  symbols is None).
        dry_run:  If True, do not modify active_picks.json.
        active_picks_path: Path to active_picks.json.

    Returns:
        List of new pick dicts that passed the signal + dedup gate.
    """
    today = _today_utc()

    if symbols is None:
        universe = build_symbol_universe(top_n=top_n, active_picks_path=active_picks_path)
    else:
        universe = [s.strip().upper() for s in symbols if s.strip()]

    logger.info("Equity breakout scanner — %d symbols, dry_run=%s", len(universe), dry_run)

    existing_picks = _load_active_picks(active_picks_path)
    new_picks: list[dict] = []

    for symbol in universe:
        try:
            data = _fetch_symbol_data(symbol)
            if data is None:
                continue  # fail-open: skip this symbol

            signal = _check_breakout(data)
            if signal is None:
                logger.debug("%s: no breakout signal", symbol)
                continue

            if _is_duplicate(symbol, existing_picks, today):
                logger.info("%s: skipping — open equity_breakout pick within %d days",
                            symbol, DEDUP_WINDOW_DAYS)
                continue

            pick = _build_pick(symbol, data, signal, today)
            new_picks.append(pick)
            logger.info(
                "%s: BREAKOUT — pct_from_high=%.2f%% vol_ratio=%.2fx conf=%.3f",
                symbol,
                signal["pct_from_high"] * 100,
                signal["volume_ratio"],
                pick["confidence"],
            )

        except Exception as exc:  # noqa: BLE001 — always fail-open per symbol
            logger.warning("%s: unexpected error — %s", symbol, exc)
            continue

    logger.info("Scanner finished: %d new picks from %d symbols", len(new_picks), len(universe))

    if new_picks and not dry_run:
        _write_picks_atomic(new_picks, existing_picks, active_picks_path)
    elif dry_run and new_picks:
        logger.info("Dry-run: %d picks NOT written", len(new_picks))

    return new_picks


def _write_picks_atomic(
    new_picks: list[dict],
    existing_picks: list[dict],
    path: Path,
) -> None:
    """
    Append new_picks to existing_picks and write atomically via temp file +
    os.replace so a crash mid-write never leaves a partial JSON file.
    """
    merged = existing_picks + new_picks
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        fd, tmp_path = tempfile.mkstemp(
            prefix=".active_picks_tmp_", suffix=".json",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(merged, fh, indent=2, default=str)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        os.replace(tmp_path, str(path))
        logger.info("Wrote %d total picks (%d new) to %s",
                    len(merged), len(new_picks), path)
    except OSError as exc:
        logger.error("Atomic write failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Equity 52-week high + volume breakout scanner (George & Hwang 2004)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Scan and log signals without writing to active_picks.json",
    )
    parser.add_argument(
        "--symbols", type=str, default=None,
        help="Comma-separated list of symbols to scan (overrides default universe)",
    )
    parser.add_argument(
        "--top-n", type=int, default=None,
        help="Cap the symbol universe to top-N (ignored when --symbols is used)",
    )
    parser.add_argument(
        "--picks-path", type=str, default=None,
        help="Override path to active_picks.json",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    args = _parse_args()

    symbols: list[str] | None = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    picks_path = ACTIVE_PICKS_PATH
    if args.picks_path:
        picks_path = Path(args.picks_path)

    picks = run_scanner(
        symbols=symbols,
        top_n=args.top_n,
        dry_run=args.dry_run,
        active_picks_path=picks_path,
    )

    if picks:
        print(f"\nEquity Breakout Scanner: {len(picks)} new picks")
        for p in picks:
            extra = p.get("extra", {})
            print(
                f"  {p['symbol']:8s}  conf={p['confidence']:.3f}  "
                f"entry={p['entry_price']:.2f}  tp={p['take_profit']:.2f}  "
                f"sl={p['stop_loss']:.2f}  "
                f"pct_from_high={extra.get('pct_from_52wk_high', 0)*100:.2f}%  "
                f"vol_ratio={extra.get('volume_ratio', 0):.2f}x"
            )
    else:
        print("Equity Breakout Scanner: 0 new picks")
