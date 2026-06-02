#!/usr/bin/env python3
"""
Walk-forward OOS validation with transaction costs for verified strategies.

Outputs: verified_strategies/WALKFORWARD_REPORT.json
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from verified_strategies.data_fetcher import fetch_crypto_ohlcv_paginated, fetch_ohlcv
from verified_strategies.strategies.connors_rsi2 import ConnorsRSI2Strategy, ConnorsRSIConfig
from verified_strategies.strategies.faber_taa import FaberTAAStrategy
from verified_strategies.strategies.bollinger_mean_reversion import BollingerMeanReversionStrategy
from verified_strategies.strategies.bb_squeeze_breakout import BBSqueezeBreakoutStrategy
from verified_strategies.strategies.vwap_reversion import VWAPReversionStrategy
from verified_strategies.strategies.dual_momentum_crypto import DualMomentumCryptoStrategy
from verified_strategies.strategies.funding_rate_mean_reversion import FundingRateMeanReversionStrategy
from verified_strategies.strategies.crypto_donchian_breakout import CryptoDonchianBreakout
from verified_strategies.strategies.etf_dual_momentum import ETFDualMomentumStrategy
from verified_strategies.strategies.equity_momentum_12_1 import EquityCrossSectionalMomentum

CRYPTO_COMMISSION_RT = 0.0010   # 10 bps round-trip
EQUITY_COMMISSION_RT = 0.0002   # 2 bps/side -> 4 bps RT (conservative ETF)


def apply_costs(trades: List[dict], commission_rt: float) -> List[dict]:
    out = []
    for t in trades:
        gross = float(t.get("pnl_pct", 0.0))
        net = gross - commission_rt
        tc = dict(t)
        tc["pnl_pct_net"] = net
        out.append(tc)
    return out


def walk_forward_trades(
    trades: List[dict],
    train_frac: float = 0.7,
    min_oos: int = 10,
) -> Dict:
    """Time-ordered split; report IS vs OOS metrics on net pnl_pct."""
    dated = sorted(trades, key=lambda t: str(t.get("exit_date", t.get("entry_date", ""))))
    if len(dated) < min_oos * 2:
        return {"verdict": "INSUFFICIENT", "n": len(dated)}

    cut = int(len(dated) * train_frac)
    is_trades = dated[:cut]
    oos_trades = dated[cut:]

    def _stats(batch: List[dict]) -> dict:
        rets = [float(t.get("pnl_pct_net", t.get("pnl_pct", 0))) for t in batch]
        if not rets:
            return {"n": 0, "wr": 0.0, "pf": 0.0, "mean_ret": 0.0, "sharpe": 0.0}
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r <= 0]
        wr = len(wins) / len(rets)
        pf = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else 0.0
        std = statistics.pstdev(rets) if len(rets) > 1 else 0.0
        sharpe = (statistics.fmean(rets) / std) * (len(rets) ** 0.5) if std > 0 else 0.0
        return {
            "n": len(rets),
            "wr": round(wr, 4),
            "pf": round(pf, 3),
            "mean_ret": round(statistics.fmean(rets), 6),
            "sharpe": round(sharpe, 3),
        }

    is_m = _stats(is_trades)
    oos_m = _stats(oos_trades)
    decay = None
    if is_m["mean_ret"] and is_m["mean_ret"] != 0:
        decay = round(oos_m["mean_ret"] / is_m["mean_ret"], 3)

    oos_pass = oos_m["pf"] >= 1.05 and oos_m["mean_ret"] > 0 and oos_m["n"] >= min_oos
    return {
        "verdict": "PASS" if oos_pass else "FAIL",
        "train_frac": train_frac,
        "in_sample": is_m,
        "out_of_sample": oos_m,
        "decay_ratio": decay,
    }


def run_faber_sleeve() -> Dict:
    all_trades: List[dict] = []
    for sym in ("SPY", "QQQ", "IWM"):
        df, _ = fetch_ohlcv(sym, 1260)
        if df is None:
            continue
        _, trades = FaberTAAStrategy().run(df, 100_000.0)
        for t in trades:
            t["symbol"] = sym
        all_trades.extend(apply_costs(trades, EQUITY_COMMISSION_RT))
    return {"strategy": "FaberTAA_sleeve", "symbols": ["SPY", "QQQ", "IWM"], **walk_forward_trades(all_trades)}


def run_connors_crypto() -> Dict:
    all_trades: List[dict] = []
    cfg = ConnorsRSIConfig(rsi_oversold=10.0, tp_atr_mult=2.0)
    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"):
        df, _ = fetch_crypto_ohlcv_paginated(sym, target_bars=2500)
        if df is None:
            continue
        _, trades = ConnorsRSI2Strategy(cfg).run(df, 100_000.0)
        for t in trades:
            t["symbol"] = sym
        all_trades.extend(apply_costs(trades, CRYPTO_COMMISSION_RT))
    return {"strategy": "ConnorsRSI2_crypto", **walk_forward_trades(all_trades)}


def _run_crypto_strategy(name: str, strategy, symbols=None) -> Dict:
    """Run a strategy across multiple crypto symbols and walk-forward the combined trades."""
    if symbols is None:
        symbols = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT")
    all_trades: List[dict] = []
    for sym in symbols:
        df, _ = fetch_crypto_ohlcv_paginated(sym, target_bars=2500)
        if df is None:
            continue
        try:
            _, trades = strategy.run(df, 100_000.0)
            for t in trades:
                t["symbol"] = sym
            all_trades.extend(apply_costs(trades, CRYPTO_COMMISSION_RT))
        except Exception as e:
            print(f"  {name} {sym}: Error — {e}")
    return {"strategy": name, "symbols": list(symbols), **walk_forward_trades(all_trades)}


def run_bollinger_mr() -> Dict:
    return _run_crypto_strategy("BollingerMR", BollingerMeanReversionStrategy())


def run_bb_squeeze() -> Dict:
    return _run_crypto_strategy("BBSqueeze", BBSqueezeBreakoutStrategy())


def run_vwap_reversion() -> Dict:
    return _run_crypto_strategy("VWAPReversion", VWAPReversionStrategy())


def run_dual_momentum() -> Dict:
    return _run_crypto_strategy("DualMomentumCrypto", DualMomentumCryptoStrategy())


def run_funding_rate_mr() -> Dict:
    return _run_crypto_strategy("FundingRateMR", FundingRateMeanReversionStrategy())


def run_crypto_donchian() -> Dict:
    """Lab sleeve: Donchian breakout multi-symbol (Hyro pilot gate)."""
    return _run_crypto_strategy(
        "CryptoDonchianBreakout",
        CryptoDonchianBreakout(),
        symbols=(
            "BTCUSDT",
            "ETHUSDT",
            "SOLUSDT",
            "BNBUSDT",
            "XRPUSDT",
            "ADAUSDT",
            "DOGEUSDT",
            "AVAXUSDT",
        ),
    )


def run_equity_momentum_12_1() -> Dict:
    """Lab SUB_TIER_2: 12-1 momentum on equity universe."""
    symbols = ["SPY", "QQQ", "IWM", "GLD", "XLF", "XLE", "SMH"]
    strat = EquityCrossSectionalMomentum()
    all_trades: List[dict] = []
    for sym in symbols:
        df, _ = fetch_ohlcv(sym, 1260)
        if df is None:
            continue
        _, trades = strat.run(df, 100_000.0)
        for t in trades:
            t["symbol"] = sym
        all_trades.extend(apply_costs(trades, EQUITY_COMMISSION_RT))
    return {"strategy": "EquityMomentum12_1", "symbols": symbols, **walk_forward_trades(all_trades)}


def run_etf_dual_momentum() -> Dict:
    """Lab Tier-2 sleeve: sector dual momentum vs SPY."""
    spy_df, _ = fetch_ohlcv("SPY", 1260)
    if spy_df is None:
        return {"strategy": "ETFDualMomentum", "verdict": "INSUFFICIENT", "n": 0}
    _, trades = ETFDualMomentumStrategy().run(spy_df, 100_000.0)
    net = apply_costs(trades, EQUITY_COMMISSION_RT)
    syms = sorted({t.get("symbol") for t in net if t.get("symbol")})
    return {"strategy": "ETFDualMomentum", "symbols": syms or ["SPY"], **walk_forward_trades(net)}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Verified strategies walk-forward OOS")
    parser.add_argument(
        "--only",
        choices=["all", "pilot", "hyro", "faber", "connors", "donchian", "etf_dm", "eq_12m"],
        default="all",
        help="pilot = etf_dm + donchian; hyro = vwap + bollinger_mr + dual_momentum; eq_12m = equity 12-1 sleeve",
    )
    args = parser.parse_args()

    out = Path(__file__).resolve().parent / "WALKFORWARD_REPORT.json"
    prior: Dict = {}
    if out.exists() and args.only != "all":
        try:
            prior = json.loads(out.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prior = {}

    results = {"timestamp": datetime.now(timezone.utc).isoformat(), "mode": args.only}
    for k, v in prior.items():
        if k not in results and k not in ("timestamp", "mode") and isinstance(v, dict):
            results[k] = v
    if args.only in ("all", "faber"):
        results["faber"] = run_faber_sleeve()
    if args.only in ("all", "connors"):
        results["connors_crypto"] = run_connors_crypto()
    if args.only in ("all", "hyro"):
        results["bollinger_mr"] = run_bollinger_mr()
        results["vwap_reversion"] = run_vwap_reversion()
        results["dual_momentum"] = run_dual_momentum()
    if args.only == "all":
        results["bb_squeeze"] = run_bb_squeeze()
        results["funding_rate_mr"] = run_funding_rate_mr()
    if args.only in ("all", "pilot", "donchian"):
        results["crypto_donchian"] = run_crypto_donchian()
    if args.only in ("all", "pilot", "etf_dm"):
        results["etf_dual_momentum"] = run_etf_dual_momentum()
    if args.only in ("all", "eq_12m"):
        results["equity_momentum_12_1"] = run_equity_momentum_12_1()
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()