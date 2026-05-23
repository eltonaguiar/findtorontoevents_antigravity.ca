#!/usr/bin/env python3
"""
Backtest the 20 institutional vector strategies on a TradingView-style pick list.

Parses comma-separated ``EXCHANGE:SYMBOL`` tokens (e.g. ``BINANCE:BTCUSDT``),
fetches **1d** OHLCV from **Binance spot** (same pair name when listed), using
multi-mirror failover. Non-Binance picks are attempted on Binance by symbol
suffix (e.g. ``KUCOIN:PTBUSDT`` → ``PTBUSDT``) and skipped with an error if
no candles are returned.

Writes real metrics to JSON — no placeholder performance.

Usage:
  python -m alpha_engine.backtest.crypto_tv_universe_runner
  python -m alpha_engine.backtest.crypto_tv_universe_runner --picks "BINANCE:BTCUSDT,BINANCE:ETHUSDT"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from alpha_engine.backtest.institutional_matrix_runner import (  # noqa: E402
    _simulate_long_trades,
)
from alpha_engine.strategies.institutional_vector_signals import (  # noqa: E402
    INSTITUTIONAL_VECTOR_STRATEGIES,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("crypto_tv_universe")

CONFIG_PATH = _REPO / "config" / "institutional_strategy_matrix.json"
OUT_PATH = _REPO / "alpha_engine" / "data" / "crypto_tv_pick_universe_backtest.json"

# API failover: Binance mirrors + vision data API (project rule: never single endpoint)
BINANCE_KLINE_BASES: Sequence[str] = (
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
)

DEFAULT_PICKS = (
    "BINANCE:SHIBUSDT,BINANCE:NOMUSDT,KUCOIN:PTBUSDT,BINANCE:DOGEUSDT,"
    "BINANCE:CHZUSDT,BINANCE:TRXUSDT,BINANCE:ADAUSDT,OKX:ZBCNUSDT,BINANCE:ZKUSDT,"
    "BINANCE:WUSDT,BINANCE:ONTUSDT,KUCOIN:QUSDT,BINANCE:FETUSDT,BINANCE:XRPUSDT,"
    "BINANCE:SEIUSDT,BINANCE:HBARUSDT,BINANCE:ARBUSDT,BINANCE:POLUSDT,BINANCE:STRKUSDT,"
    "BINANCE:SUIUSDT,BINANCE:OPUSDT,BINANCE:DYDXUSDT,BINANCE:APEUSDT,BINANCE:ALGOUSDT,"
    "BINANCE:TIAUSDT,BINANCE:DOTUSDT,BINANCE:JTOUSDT,OKX:TONUSDT,BINANCE:SOLUSDT,"
    "BINANCE:LINKUSDT,KUCOIN:SIRENUSDT,BINANCE:AVAXUSDT,BINANCE:ZROUSDT,BINANCE:INJUSDT,"
    "BYBIT:VVVUSDT,BINANCE:ETCUSDT,BINANCE:LTCUSDT,MEXC:RIVERUSDT,BINANCE:ETHUSDT,"
    "OKX:GLMUSDT,BINANCE:BNBUSDT,BINANCE:AAVEUSDT,BINANCE:BTCUSDT,POLONIEX:WARUSDT,"
    "HTX:ULTIMAUSDT"
)


def _load_cfg() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _parse_tv_picks(raw: str) -> List[str]:
    parts = [p.strip().upper() for p in raw.replace("\n", ",").split(",")]
    seen: set[str] = set()
    out: List[str] = []
    for p in parts:
        if not p or p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def _tv_to_binance_symbol(tv: str) -> Tuple[str, str]:
    """Return (tv_pick, binance_symbol). Symbol is uppercased USDT pair for klines."""
    tv = tv.strip().upper()
    if ":" in tv:
        _, sym = tv.split(":", 1)
    else:
        sym = tv
    sym = sym.replace("-", "").replace("/", "")
    if not sym.endswith("USDT") and sym.endswith("USD"):
        sym = sym.replace("USD", "USDT")
    return tv, sym


def _fetch_binance_daily_klines(symbol: str, limit: int = 1000) -> Optional[pd.DataFrame]:
    """Fetch 1d klines; return DataFrame Open, High, Low, Close, Volume or None."""
    sym = symbol.upper()
    lim = max(50, min(int(limit), 1000))
    for base in BINANCE_KLINE_BASES:
        url = f"{base}/api/v3/klines?symbol={sym}&interval=1d&limit={lim}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue
        if not raw or not isinstance(raw, list):
            continue
        rows = []
        for k in raw:
            if not isinstance(k, (list, tuple)) or len(k) < 6:
                continue
            rows.append(
                {
                    "Open": float(k[1]),
                    "High": float(k[2]),
                    "Low": float(k[3]),
                    "Close": float(k[4]),
                    "Volume": float(k[5]),
                }
            )
        if len(rows) < 60:
            continue
        idx = pd.to_datetime([int(k[0]) for k in raw if isinstance(k, (list, tuple)) and len(k) >= 6], unit="ms", utc=True)
        df = pd.DataFrame(rows, index=idx[: len(rows)])
        df = df.dropna(how="any")
        if len(df) < 60:
            continue
        return df
    return None


def run_universe(picks_csv: Optional[str] = None) -> Dict[str, Any]:
    cfg = _load_cfg()
    strat_ids: List[str] = list(cfg["strategy_ids"])
    if len(strat_ids) != 20:
        raise ValueError("institutional_strategy_matrix.json must list exactly 20 strategy_ids")

    crypto_spec = (cfg.get("per_asset_class") or {}).get("CRYPTO") or {}
    hold_days = int(crypto_spec.get("hold_days", 7))
    defs = cfg.get("runner_defaults") or {}
    fee = float(defs.get("fee_roundtrip", 0.001))

    raw_picks = (picks_csv or DEFAULT_PICKS).strip()
    tv_list = _parse_tv_picks(raw_picks)

    results: List[Dict[str, Any]] = []
    errors: List[str] = []

    for tv in tv_list:
        _, bsym = _tv_to_binance_symbol(tv)
        df = _fetch_binance_daily_klines(bsym)
        if df is None or len(df) < max(120, hold_days * 5):
            errors.append("%s (%s): no or insufficient Binance 1d data" % (tv, bsym))
            continue
        for sid in strat_ids:
            fn = INSTITUTIONAL_VECTOR_STRATEGIES.get(sid)
            if fn is None:
                errors.append("missing strategy %s" % sid)
                continue
            try:
                raw_sig = fn(df)
                stats = _simulate_long_trades(df, raw_sig, hold_days=hold_days, fee_rt=fee)
                results.append(
                    {
                        "tv_pick": tv,
                        "binance_symbol": bsym,
                        "strategy_id": sid,
                        "hold_days": hold_days,
                        "fee_roundtrip": fee,
                        **stats,
                    }
                )
            except Exception as e:
                errors.append("%s %s %s: %s" % (tv, bsym, sid, e))

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "picks_source": "tv_comma_list",
        "picks_raw": raw_picks[:2000],
        "binance_kline_bases": list(BINANCE_KLINE_BASES),
        "config_path": str(CONFIG_PATH.relative_to(_REPO)),
        "hold_days": hold_days,
        "fee_roundtrip": fee,
        "strategies_n": len(strat_ids),
        "tv_picks_n": len(tv_list),
        "rows": results,
        "errors": errors,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    log.info("Wrote %s (%d rows, %d errors)", OUT_PATH, len(results), len(errors))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest TV crypto pick list on Binance 1d + institutional vectors")
    ap.add_argument(
        "--picks",
        default=None,
        help="Comma-separated EXCHANGE:SYMBOL list (default: built-in universe)",
    )
    args = ap.parse_args()
    run_universe(picks_csv=args.picks)


if __name__ == "__main__":
    main()
