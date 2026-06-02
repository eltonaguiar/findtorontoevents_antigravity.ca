#!/usr/bin/env python3
"""
Strategy Verification Runner — Orchestrates the verification pipeline with REAL data.
Multi-asset, multi-symbol, extended-history approach for robust statistical validation.
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
import logging

sys.path.append(os.getcwd())

from verified_strategies.strategy_verification_engine import StrategyVerificationEngine, generate_report
from verified_strategies.strategies.carry_trade import CarryTradeStrategy
from verified_strategies.strategies.cta_trend_following import CTATrendFollowingStrategy
from verified_strategies.strategies.faber_taa import FaberTAAStrategy
from verified_strategies.strategies.faber_rotation import FaberRotationStrategy
from verified_strategies.strategies.connors_rsi2 import ConnorsRSI2Strategy, ConnorsRSIConfig

# New strategies
from verified_strategies.strategies.crypto_donchian_breakout import CryptoDonchianBreakout
from verified_strategies.strategies.crypto_funding_arb import CryptoFundingRateArb
from verified_strategies.strategies.crypto_multi_tf_momentum import CryptoMultiTFMomentum
from verified_strategies.strategies.equity_momentum_12_1 import EquityCrossSectionalMomentum
from verified_strategies.strategies.commodity_gold_trend import GoldTrendFollowing
from verified_strategies.strategies.fx_usd_momentum import FXUSDMomentum

# Backup crypto strategies (ported from baby_strategies/)
from verified_strategies.strategies.bollinger_mean_reversion import BollingerMeanReversionStrategy
from verified_strategies.strategies.bb_squeeze_breakout import BBSqueezeBreakoutStrategy
from verified_strategies.strategies.vwap_reversion import VWAPReversionStrategy
from verified_strategies.strategies.dual_momentum_crypto import DualMomentumCryptoStrategy
from verified_strategies.strategies.funding_rate_mean_reversion import FundingRateMeanReversionStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_LIMIT = 1500
KLINE_INTERVAL = "1d"

CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT"]
EQUITY_SYMBOLS = ["SPY", "QQQ", "IWM", "GLD", "XLF", "XLE"]
FX_CARRY = "AUDJPY=X"


def load_crypto_data(symbol: str, limit: int = DATA_LIMIT) -> pd.DataFrame | None:
    from alpha_engine.api_failover import fetch_klines
    raw = fetch_klines(symbol, interval=KLINE_INTERVAL, limit=limit)
    if not raw:
        logger.warning(f"No data for {symbol}")
        return None

    df = pd.DataFrame(raw, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col])
    df.attrs['symbol'] = symbol
    logger.info(f"Crypto {symbol}: {len(df)} bars, {df.index[0].date()} → {df.index[-1].date()}")
    return df


def load_equity_data(symbol: str, period_days: int = 1500) -> pd.DataFrame | None:
    from verified_strategies.data_fetcher import fetch_ohlcv
    df, provider = fetch_ohlcv(symbol, period_days)
    if df is None:
        logger.warning(f"No equity data for {symbol}")
        return None
    df.attrs['symbol'] = symbol
    logger.info(f"Equity {symbol}: {len(df)} bars via {provider}, {df.index[0].date()} → {df.index[-1].date()}")
    return df


def run_pipeline():
    engine = StrategyVerificationEngine(mc_iterations=2000)
    results = {}
    data_sources = {}

    # ── 1. Faber TAA — equities + crypto ──────────────────────────────
    print(f"\n{'='*60}")
    print("Faber TAA — Equity sweep")
    faber = FaberTAAStrategy()
    all_trades = []
    for sym in EQUITY_SYMBOLS:
        data = load_equity_data(sym)
        if data is None:
            continue
        try:
            metrics = engine.verify_strategy(faber, data, asset_class="EQUITY")
            key = f"FaberTAA_{sym}"
            results[key] = metrics
            data_sources[key] = "yfinance"
            all_trades.extend([t for t in [metrics] if metrics.trades_count > 0])
            print(f"  {sym}: Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                  f"Ret={metrics.total_return:+.1%}, WR={metrics.win_rate:.1%}, "
                  f"Trades={metrics.trades_count}, MC-p={metrics.mc_p_value:.3f}")
        except Exception as e:
            print(f"  {sym}: Error — {e}")

    print(f"\nFaber TAA — Crypto sweep")
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        data = load_crypto_data(sym)
        if data is None:
            continue
        try:
            metrics = engine.verify_strategy(faber, data, asset_class="CRYPTO")
            key = f"FaberTAA_{sym}"
            results[key] = metrics
            data_sources[key] = "binance"
            print(f"  {sym}: Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                  f"Ret={metrics.total_return:+.1%}, WR={metrics.win_rate:.1%}, "
                  f"Trades={metrics.trades_count}, MC-p={metrics.mc_p_value:.3f}")
        except Exception as e:
            print(f"  {sym}: Error — {e}")

    # ── 2. CTA Trend — crypto ─────────────────────────────────────────
    print(f"\n{'='*60}")
    print("CTA Trend Following — Crypto sweep")
    cta = CTATrendFollowingStrategy()
    for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        data = load_crypto_data(sym)
        if data is None:
            continue
        try:
            metrics = engine.verify_strategy(cta, data, asset_class="CRYPTO")
            key = f"CTATrend_{sym}"
            results[key] = metrics
            data_sources[key] = "binance"
            print(f"  {sym}: Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                  f"Ret={metrics.total_return:+.1%}, WR={metrics.win_rate:.1%}, "
                  f"Trades={metrics.trades_count}, MC-p={metrics.mc_p_value:.3f}")
        except Exception as e:
            print(f"  {sym}: Error — {e}")

    # ── 3. Connors RSI-2 — crypto with looser + tighter variants ──────
    print(f"\n{'='*60}")
    print("Connors RSI-2 — Crypto sweep")

    configs = {
        "ConnorsRSI2_Crypto15": ConnorsRSIConfig(rsi_period=2, rsi_oversold=15.0, rsi_overbought=70.0),
        "ConnorsRSI2_Crypto10": ConnorsRSIConfig(rsi_period=2, rsi_oversold=10.0, rsi_overbought=65.0),
    }

    for variant_name, cfg in configs.items():
        strategy = ConnorsRSI2Strategy(cfg)
        all_trades = []
        for sym in CRYPTO_SYMBOLS:
            data = load_crypto_data(sym)
            if data is None:
                continue
            try:
                equity_curve, trades = strategy.run(data, 100000)
                all_trades.extend(trades)
                print(f"  {variant_name} {sym}: {len(trades)} trades, "
                      f"final=${equity_curve.iloc[-1]:,.0f}")
            except Exception as e:
                print(f"  {variant_name} {sym}: Error — {e}")

        if all_trades:
            pnls = [t['pnl'] for t in all_trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            wr = len(wins) / len(all_trades)
            pf = sum(wins) / abs(sum(losses)) if losses else 999
            print(f"  COMBINED {variant_name}: {len(all_trades)} trades, "
                  f"WR={wr:.1%}, PF={pf:.2f}")

    # ── 4. Carry Trade — FX data via yfinance + FRED ──────────────────
    print(f"\n{'='*60}")
    print("Carry Trade — AUDJPY FX via yfinance + FRED")
    from verified_strategies.data_fetcher import load_carry_data

    carry_data, carry_source = load_carry_data("AUDJPY=X", period_days=2200)
    if carry_data is not None:
        data_sources["CarryTrade"] = carry_source
        strategy = CarryTradeStrategy()
        try:
            equity_curve, trades = strategy.run_backtest(carry_data, 100000)
            print(f"  AUDJPY carry trades: {len(trades)}")
            if trades:
                pnls = [t['pnl'] for t in trades]
                wins = [p for p in pnls if p > 0]
                losses = [p for p in pnls if p < 0]
                wr = len(wins) / len(trades)
                pf = sum(wins) / abs(sum(losses)) if losses else 999
                print(f"  WR={wr:.1%}, PF={pf:.2f}")
                avg_ret = np.mean([p / 100000 for p in pnls]) if pnls else 0
                print(f"  Avg trade ret: {avg_ret:.4%}")

            # Wrap so verify_strategy sees the standard (equity, trades) interface
            class _CarryAdapter:
                def __init__(self, eq, tr):
                    self.eq = eq
                    self.tr = tr
                def run(self, _data, _capital):
                    return self.eq, self.tr

            metrics = engine.verify_strategy(_CarryAdapter(equity_curve, trades), carry_data, asset_class="FX")
            results["CarryTrade"] = metrics
            print(f"  Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                  f"Ret={metrics.total_return:+.1%}, MaxDD={metrics.max_drawdown:.1%}, "
                  f"WR={metrics.win_rate:.1%}, Trades={metrics.trades_count}, "
                  f"MC-p={metrics.mc_p_value:.3f}")
        except Exception as e:
            print(f"  CarryTrade error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("  SKIPPED: Could not load FX data for AUDJPY carry trade")

    # ── 5. Faber TAA — equities as multi-symbol engine run ────────────
    print(f"\n{'='*60}")
    print("Faber TAA — Full engine on equities")
    for sym in ["SPY", "QQQ", "GLD"]:
        data = load_equity_data(sym)
        if data is None:
            continue
        try:
            metrics = engine.verify_strategy(FaberTAAStrategy(), data, asset_class="EQUITY")
            key = f"FaberTAA_Engine_{sym}"
            results[key] = metrics
            print(f"  {sym}: Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                  f"Ret={metrics.total_return:+.1%}, WR={metrics.win_rate:.1%}, "
                  f"Trades={metrics.trades_count}, MC-p={metrics.mc_p_value:.3f}")
        except Exception as e:
            print(f"  {sym}: Error — {e}")

    # ── 6. Faber TAA — Multi-asset rotation engine ───────────────────
    print(f"\n{'='*60}")
    print("Faber TAA — Multi-Asset Rotation Engine")
    print("  Loading SPY, QQQ, IWM, GLD, XLF, XLE...")
    rotation_dfs = {}
    for sym in EQUITY_SYMBOLS:
        d = load_equity_data(sym)
        if d is not None:
            rotation_dfs[sym] = d

    if len(rotation_dfs) >= 3:
        # Align all to common index and build MultiIndex DataFrame
        common_idx = None
        for sym, d in rotation_dfs.items():
            if common_idx is None:
                common_idx = d.index
            else:
                common_idx = common_idx.intersection(d.index)

        if len(common_idx) > 200:
            multi_data = {}
            for sym, d in rotation_dfs.items():
                aligned = d.reindex(common_idx)
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    multi_data[(sym, col)] = aligned[col]
            multi_df = pd.DataFrame(multi_data)
            multi_df.index = pd.DatetimeIndex(common_idx)

            rotation = FaberRotationStrategy()
            try:
                rot_eq, rot_trades = rotation.run(multi_df, 100_000)
                print(f"  Rotation: {len(rot_trades)} trades, final=${rot_eq.iloc[-1]:,.0f}")
                if rot_trades:
                    pnls = [t['pnl'] for t in rot_trades]
                    wins = [p for p in pnls if p > 0]
                    losses = [p for p in pnls if p < 0]
                    wr = len(wins) / len(rot_trades)
                    pf = sum(wins) / abs(sum(losses)) if losses else 999
                    print(f"  WR={wr:.1%}, PF={pf:.2f}")

                # Wrap for verification engine
                class _RotationAdapter:
                    def __init__(self, eq, tr):
                        self.eq = eq
                        self.tr = tr
                    def run(self, _data, _capital):
                        return self.eq, self.tr

                metrics = engine.verify_strategy(_RotationAdapter(rot_eq, rot_trades), multi_df, asset_class="EQUITY")
                results["FaberTAA_Rotation"] = metrics
                data_sources["FaberTAA_Rotation"] = "yfinance_multi"
                print(f"  Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                      f"Ret={metrics.total_return:+.1%}, WR={metrics.win_rate:.1%}, "
                      f"Trades={metrics.trades_count}, MC-p={metrics.mc_p_value:.3f}")
            except Exception as e:
                print(f"  Rotation error: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"  SKIPPED: Only {len(common_idx)} common bars across assets")
    else:
        print(f"  SKIPPED: Only {len(rotation_dfs)} assets loaded (need >=3)")

    # ── 7. NEW CRYPTO STRATEGIES ───────────────────────────────────────
    print(f"\n{'='*60}")
    print("NEW CRYPTO STRATEGIES — Multi-symbol sweep")

    crypto_strategies = {
        "DonchianBreakout": CryptoDonchianBreakout(),
        "FundingRateArb": CryptoFundingRateArb(),
        "MultiTFMomentum": CryptoMultiTFMomentum(),
    }

    for strat_name, strategy in crypto_strategies.items():
        print(f"\n  {strat_name}:")
        all_trades = []
        for sym in CRYPTO_SYMBOLS[:5]:  # Top 5 by liquidity
            data = load_crypto_data(sym)
            if data is None:
                continue
            try:
                metrics = engine.verify_strategy(strategy, data, asset_class="CRYPTO")
                key = f"{strat_name}_{sym}"
                results[key] = metrics
                data_sources[key] = "binance"
                all_trades.extend([t for t in [metrics] if metrics.trades_count > 0])
                print(f"    {sym}: Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                      f"Ret={metrics.total_return:+.1%}, WR={metrics.win_rate:.1%}, "
                      f"Trades={metrics.trades_count}, MC-p={metrics.mc_p_value:.3f}")
            except Exception as e:
                print(f"    {sym}: Error — {e}")

    # ── 8. EQUITY MOMENTUM ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Equity Momentum 12-1 — Equity sweep")
    eq_mom = EquityCrossSectionalMomentum()
    for sym in EQUITY_SYMBOLS:
        data = load_equity_data(sym)
        if data is None:
            continue
        try:
            metrics = engine.verify_strategy(eq_mom, data, asset_class="EQUITY")
            key = f"EqMom12_1_{sym}"
            results[key] = metrics
            data_sources[key] = "yfinance"
            print(f"  {sym}: Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                  f"Ret={metrics.total_return:+.1%}, WR={metrics.win_rate:.1%}, "
                  f"Trades={metrics.trades_count}, MC-p={metrics.mc_p_value:.3f}")
        except Exception as e:
            print(f"  {sym}: Error — {e}")

    # ── 9. GOLD TREND ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Gold Trend-Following — GLD + crypto gold proxies")
    gold = GoldTrendFollowing()
    for sym in ["GLD", "BTCUSDT"]:
        data = load_equity_data(sym) if sym != "BTCUSDT" else load_crypto_data(sym)
        if data is None:
            continue
        try:
            asset_class = "CRYPTO" if "USDT" in sym else "COMMODITY"
            metrics = engine.verify_strategy(gold, data, asset_class=asset_class)
            key = f"GoldTrend_{sym}"
            results[key] = metrics
            data_sources[key] = "binance" if "USDT" in sym else "yfinance"
            print(f"  {sym}: Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                  f"Ret={metrics.total_return:+.1%}, WR={metrics.win_rate:.1%}, "
                  f"Trades={metrics.trades_count}, MC-p={metrics.mc_p_value:.3f}")
        except Exception as e:
            print(f"  {sym}: Error — {e}")

    # ── 10. FX MOMENTUM ───────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("FX USD Momentum — Major pairs")
    fx_mom = FXUSDMomentum()
    for sym in ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]:
        data = load_equity_data(sym, period_days=1500)
        if data is None:
            continue
        try:
            metrics = engine.verify_strategy(fx_mom, data, asset_class="FX")
            key = f"FXMom_{sym.replace('=X','')}"
            results[key] = metrics
            data_sources[key] = "yfinance"
            print(f"  {sym}: Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                  f"Ret={metrics.total_return:+.1%}, WR={metrics.win_rate:.1%}, "
                  f"Trades={metrics.trades_count}, MC-p={metrics.mc_p_value:.3f}")
        except Exception as e:
            print(f"  {sym}: Error — {e}")

    # ── 11. BACKUP CRYPTO STRATEGIES (ported from baby_strategies/) ──
    print(f"\n{'='*60}")
    print("BACKUP CRYPTO STRATEGIES — Multi-symbol sweep")

    backup_strategies = {
        "BollingerMR": BollingerMeanReversionStrategy(),
        "BBSqueeze": BBSqueezeBreakoutStrategy(),
        "VWAPReversion": VWAPReversionStrategy(),
        "DualMomentumCrypto": DualMomentumCryptoStrategy(),
        "FundingRateMR": FundingRateMeanReversionStrategy(),
    }

    for strat_name, strategy in backup_strategies.items():
        print(f"\n  {strat_name}:")
        all_trades = []
        for sym in CRYPTO_SYMBOLS[:5]:
            data = load_crypto_data(sym)
            if data is None:
                continue
            try:
                metrics = engine.verify_strategy(strategy, data, asset_class="CRYPTO")
                key = f"{strat_name}_{sym}"
                results[key] = metrics
                data_sources[key] = "binance"
                pass  # trades collected in combined sweep below
                print(f"    {sym}: Tier={metrics.tier.value}, Sharpe={metrics.sharpe_ratio:.2f}, "
                      f"Ret={metrics.total_return:+.1%}, WR={metrics.win_rate:.1%}, "
                      f"Trades={metrics.trades_count}, MC-p={metrics.mc_p_value:.3f}")
            except Exception as e:
                print(f"    {sym}: Error — {e}")

        # Combined multi-symbol sweep
        combined_trades = []
        for sym in CRYPTO_SYMBOLS[:5]:
            data = load_crypto_data(sym)
            if data is None:
                continue
            try:
                _, trades = strategy.run(data, 100000)
                combined_trades.extend(trades)
            except Exception:
                pass

        if combined_trades:
            pnls = [t['pnl'] for t in combined_trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            wr = len(wins) / len(combined_trades)
            pf = sum(wins) / abs(sum(losses)) if losses else 999
            print(f"  COMBINED {strat_name}: {len(combined_trades)} trades, "
                  f"WR={wr:.1%}, PF={pf:.2f}")

    # ── Generate report ────────────────────────────────────────────
    generate_report(results, data_sources=data_sources)
    print(f"\n{'='*60}")
    print("Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()
