"""ETF sector-rotation runner — emits a sample picks JSON.

Opt-in sidecar caller for `alpha_engine/etf_rebalancer.py`. Per CLAUDE.md
Wire-Up Rule, the first production caller for the orphan Riskfolio-Lib pin
at `scripts/worldclass/requirements.txt:20`.

Default OFF: requires ``ETF_SECTOR_ROTATION_ENABLED=1``. The follow-up PR
(consumer via PR #472 orphan-emitter wire) flips the gate after verification.

OUTPUT: ``non_crypto_agent/data/etf_sector_rotation_picks.json``. Schema:
  {agent, generated_at, universe, lookback_days, top_n, signal, picks[]}.
Never overwrites HTML — JSON only.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make sibling alpha_engine importable when run as `python tools/...`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine.etf_rebalancer import (  # noqa: E402
    SPDR_SECTOR_ETFS,
    sector_rotation_signal,
)

logger = logging.getLogger(__name__)

ETF_PICKS_PATH = Path("non_crypto_agent/data/etf_sector_rotation_picks.json")
DEFAULT_LOOKBACK = 60
DEFAULT_TOP_N = 3
ENV_GATE = "ETF_SECTOR_ROTATION_ENABLED"


def fetch_prices(tickers: list[str], lookback_days: int) -> "Any":
    """Pull recent closes for `tickers` via yfinance. Returns a DataFrame
    indexed by date with one column per ticker, or None on failure."""
    try:
        import yfinance as yf  # lazy import — avoids regressing scanner imports
        import pandas as pd
    except ImportError as exc:
        logger.error("fetch_prices: yfinance/pandas missing (%s).", exc)
        return None

    # Pull ~2x the lookback to give the 12-1 skip room + market-closure padding.
    period_days = max(lookback_days * 2 + 30, 180)
    try:
        df = yf.download(
            tickers,
            period=f"{period_days}d",
            interval="1d",
            progress=False,
            auto_adjust=True,
            group_by="column",
            threads=True,
        )
    except Exception as exc:
        logger.error("fetch_prices: yfinance.download raised %s.", exc)
        return None

    if df is None or df.empty:
        logger.error("fetch_prices: empty DataFrame from yfinance.")
        return None

    # yfinance returns multi-index columns when multiple tickers present.
    if isinstance(df.columns, pd.MultiIndex):
        if "Close" in df.columns.get_level_values(0):
            closes = df["Close"]
        elif "Adj Close" in df.columns.get_level_values(0):
            closes = df["Adj Close"]
        else:
            logger.error("fetch_prices: no Close/Adj Close in columns.")
            return None
    else:
        closes = df[["Close"]].rename(columns={"Close": tickers[0]}) \
            if "Close" in df.columns else df

    return closes.dropna(how="all")


def build_payload(
    tickers: list[str],
    lookback_days: int,
    top_n: int,
    *,
    prices_df=None,
) -> dict[str, Any]:
    """Run the signal end-to-end and return a serialisable payload."""
    if prices_df is None:
        prices_df = fetch_prices(tickers, lookback_days)
    signal: dict[str, Any]
    if prices_df is None or prices_df.empty:
        signal = {"top_n": [], "momentum": {}, "weights": {},
                  "method": "no_prices", "lookback": lookback_days,
                  "n_sectors": len(tickers)}
    else:
        signal = sector_rotation_signal(
            prices_df, lookback=lookback_days, top_n=top_n,
        )

    picks = [
        {
            "ticker": t,
            "weight": float(signal["weights"].get(t, 0.0)),
            "momentum": float(signal["momentum"].get(t, 0.0)),
            "method": signal["method"],
        }
        for t in signal["top_n"]
    ]

    return {
        "agent": "etf_sector_rotation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe": list(tickers),
        "lookback_days": lookback_days,
        "top_n": top_n,
        "signal": signal,
        "picks": picks,
    }


def write_payload(payload: dict[str, Any], path: Path = ETF_PICKS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.info(
        "Wrote %s (top_n=%d method=%s)",
        path, len(payload["picks"]), payload["signal"]["method"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", nargs="*", default=list(SPDR_SECTOR_ETFS),
                        help="ETF tickers (default: 11 SPDR sectors).")
    parser.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK)
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--output", type=Path, default=ETF_PICKS_PATH)
    parser.add_argument("--dry-run", action="store_true",
                        help="Build payload but do not write the JSON.")
    parser.add_argument("--force", action="store_true",
                        help=f"Run even when {ENV_GATE} is unset (debug only).")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    enabled = os.environ.get(ENV_GATE, "0") == "1"
    if not enabled and not args.force:
        logger.warning(
            "%s != 1 — runner is opt-in. Pass --force to bypass for local sanity-check.",
            ENV_GATE,
        )
        return 0

    payload = build_payload(args.universe, args.lookback, args.top_n)

    if args.dry_run:
        logger.info("Dry run — not writing payload to %s", args.output)
    else:
        write_payload(payload, args.output)

    print(json.dumps({
        "method": payload["signal"]["method"],
        "lookback_days": payload["lookback_days"],
        "top_n": payload["top_n"],
        "picks": payload["picks"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
