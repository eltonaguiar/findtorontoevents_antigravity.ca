"""
ALPHA_ENGINE -- Configuration
============================
Symbols, risk parameters, strategy parameters, API endpoints.
All thresholds are research-backed with citations in strategy files.
"""

from __future__ import annotations
import json
import os
from pathlib import Path

# Macro tickers for macro data loading
MACRO_TICKERS = {
    "VIX": "^VIX",
    "TNX": "^TNX",
    "DXY": "DX-Y.N",
    "GOLD": "GC=F",
    # "OIL": "CL=F",  # REMOVED: 26 futures trades, 3.8% WR, -29.82% PnL — worse than random
    "SPY": "SPY",
}

# Backtest start date for data loading (YYYY-MM-DD)
BACKTEST_START = "2020-01-01"

# Default universe for UniverseManager (must be a list of tickers, NOT a string)
DEFAULT_UNIVERSE = [
    # Mega-cap tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    # Financials
    "JPM", "GS", "WFC", "BAC", "V", "MA",
    # Healthcare
    "UNH", "JNJ", "PFE", "ABBV", "LLY",
    # Consumer
    "WMT", "HD", "MCD", "KO", "PEP", "PG", "COST",
    # Industrials / Energy
    "BA", "CAT", "CVX", "XOM",
    # Telecom / Media
    "DIS", "VZ", "T", "NFLX", "CRM",
    # Broad ETFs (benchmark)
    "SPY", "QQQ", "IWM",
]

# Sector ETFs for sector analysis (used by UniverseManager)
SECTOR_ETFS = ["XLK", "XLV", "XLF", "XLY", "XLP", "XLI", "XLE", "XLB", "XLU", "XLRE", "XLC"]

# Dividend aristocrat tickers for quality value strategy
DIVIDEND_ARISTOCRATS = [
    "AAPL", "MSFT", "JNJ", "KO", "PEP", "PG", "V", "WMT", "HD", "UNH",
    "DIS", "VZ", "T", "MCD", "IBM", "CVX", "BA", "WFC", "GS", "JPM"
]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
DB_PATH = DATA_DIR / "alpha.db"
ML_MODEL_PATH = DATA_DIR / "rf_model.pkl"
ML_WEIGHTS_PATH = DATA_DIR / "ml_weights.json"

# ---------------------------------------------------------------------------
# Capital & position sizing (v1.2: risk-based sizing)
# ---------------------------------------------------------------------------
STARTING_CAPITAL = 10_000.0

# v1.2: Risk-based position sizing replaces fixed $2K allocation
# Old: ALLOCATION_PER_PICK = 2_000.0 (20% of capital -- way too concentrated)
# New: Size = risk_amount / stop_distance, capped at MAX_ALLOCATION_PER_PICK
MAX_RISK_PER_TRADE = 0.02        # Risk 2% of capital per trade ($200 on $10K)
MAX_ALLOCATION_PER_PICK = 0.15   # Max 15% of capital in any single pick ($1,500)
MAX_TOTAL_EXPOSURE = 0.80        # Max 80% of capital deployed at once
MAX_CORRELATED_EXPOSURE = 0.40   # Max 40% in same asset class (was 30% -- too restrictive for crypto-heavy portfolio)

# Pick cap system:
# - Overall cap set to 20 (institutional risk audit fix -- was 999/disabled).
#   production_scanner.py also enforces MAX_ACTIVE_PICKS=20 independently.
# - Per-strategy and per-symbol caps remain to prevent domination.
# - Directional cap remains for risk management.
MAX_OPEN_PICKS = 100             # Hard cap to match production_scanner MAX_CAP (v1.3 Fix)
MAX_PICKS_PER_STRATEGY = 3       # Reduced from 4 -- prevent single-strategy domination
MAX_PICKS_PER_SYMBOL = 1         # Reduced from 2 -- TRANSFORMATION BLUEPRINT Phase 1: prevent FET-style concentration (237% of PnL from 1 symbol)
MAX_PICKS_PER_SECTOR = 3         # Sector concentration cap -- correlated same-sector picks compound losses
MAX_SAME_DIRECTION_CRYPTO = 40   # Raised per-user request to restore signal liquidity
KELLY_CAP = 0.05  # Max 5% of capital per trade (Kelly capped)

# ---------------------------------------------------------------------------
# Sector map for concentration risk management
# BTC and ETH get their own sectors (uncapped by MAX_PICKS_PER_SECTOR).
# All other symbols are grouped by sector. Unknown symbols default to "other".
# ---------------------------------------------------------------------------
SECTOR_MAP: dict[str, str] = {
    # Majors -- each gets its own sector (no cap)
    "BTCUSDT": "btc", "ETHUSDT": "eth",
    # Layer 1
    "SOLUSDT": "l1", "AVAXUSDT": "l1", "NEARUSDT": "l1", "SUIUSDT": "l1",
    "ADAUSDT": "l1", "DOTUSDT": "l1", "ATOMUSDT": "l1", "APTUSDT": "l1",
    "TONUSDT": "l1", "MATICUSDT": "l1", "POLUSDT": "l1", "ALGOUSDT": "l1",
    "ICPUSDT": "l1", "SEIUSDT": "l1", "INJUSDT": "l1", "TIAUSDT": "l1",
    # DeFi
    "AAVEUSDT": "defi", "UNIUSDT": "defi", "LINKUSDT": "defi",
    "MKRUSDT": "defi", "SNXUSDT": "defi", "COMPUSDT": "defi",
    "CRVUSDT": "defi", "LDOUSDT": "defi", "PENDLEUSDT": "defi",
    "JUPUSDT": "defi", "ENAUSDT": "defi", "EIGENUSDT": "defi",
    # Meme
    "DOGEUSDT": "meme", "SHIBUSDT": "meme", "PEPEUSDT": "meme",
    "FARTCOINUSDT": "meme", "BONKUSDT": "meme", "FLOKIUSDT": "meme",
    "WIFUSDT": "meme", "TRUMPUSDT": "meme", "BRETTUSDT": "meme",
    # AI / DePin
    "RENDERUSDT": "ai", "TAOUSDT": "ai", "FETUSDT": "ai",
    "OCEANUSDT": "ai", "ARKMUSDT": "ai", "VIRTUSDT": "ai",
    # Gaming / Metaverse
    "AXSUSDT": "gaming", "SANDUSDT": "gaming", "MANAUSDT": "gaming",
    "IMXUSDT": "gaming", "GALAUSDT": "gaming",
    # Layer 2
    "ARBUSDT": "l2", "OPUSDT": "l2", "STRKUSDT": "l2",
    # Payments / Store-of-value
    "XLMUSDT": "payments", "LTCUSDT": "payments", "BCHUSDT": "payments",
    "ETCUSDT": "l1", "KASUSDT": "l1", "HBARUSDT": "l1",
    # Storage / Privacy / Utility
    "FILUSDT": "storage", "ZECUSDT": "privacy", "BATUSDT": "utility",
    "QNTUSDT": "enterprise", "XMRUSDT": "privacy",
    # Exchange / Perp DEX
    "BNBUSDT": "exchange", "FTMUSDT": "l1", "HYPEUSDT": "exchange",
    # Forex (no sector cap -- different asset class)
    "EURUSD": "forex", "GBPUSD": "forex", "USDJPY": "forex",
    "AUDUSD": "forex", "USDCAD": "forex", "NZDUSD": "forex",
    "USDCHF": "forex", "EURGBP": "forex", "EURJPY": "forex",
    "GBPJPY": "forex", "XAUUSD": "forex",
    # Equities (no sector cap -- different asset class)
}
# Sectors exempt from MAX_PICKS_PER_SECTOR (majors + non-crypto)
SECTOR_CAP_EXEMPT = {"btc", "eth", "forex"}

# ---------------------------------------------------------------------------
# Quick Win 3: Strategy weight overrides for position sizing
# Maps strategy name -> allocation multiplier (1.0 = default)
# funding_carry has 8.19 Sharpe but gets flat allocation -- scale to 2.5x
# ---------------------------------------------------------------------------
STRATEGY_WEIGHT_OVERRIDES: dict[str, float] = {
    # ETF strategies — highest Sharpe in system (6.375, 60.9% WR)
    # All 5 backed by academic research; scale up aggressively.
    "etf_dual_momentum":        3.0,  # Antonacci 2014: 75%+ WR, top Sharpe
    "etf_sector_momentum":      3.0,  # Faber 2007: 10-mo SMA filter, Sharpe ~0.76
    "etf_faber_tactical":       3.0,  # Faber TAA: same paper, 99% return retention
    "etf_risk_parity_rotation": 2.5,  # Bridgewater/AQR risk-parity, 60d corr edge
    "etf_trend_following":      2.5,  # Kirby & Ostdiek 2012: simple timing beats naive
    # New improved strategies (2026-05-28) — replacing worst performers
    "etf_dual_momentum_rotation": 2.0,  # dual-momentum sector rotation, DIA 58.8% WR PF 2.64
    "equity_rsi_momentum_drift":  1.5,  # RSI pullback + momentum drift, AAPL 66.7% WR PF 3.36
    "bond_yield_steepener_carry": 1.5,  # yield steepener + carry, IEF 52.9% WR PF 2.13
    "futures_session_breakout_cot": 2.0,  # session breakout + COT proxy, ES=F 61.5% WR PF 1.39
    "forex_carry_bb_hybrid":      1.0,  # carry + BB hybrid, experimental (GBPUSD 75% WR, sparse)
    "penny_volume_gap_reversion":  0.5,  # volume surge + gap reversion, low WR, high vol
    # Carry strategies (high Sharpe, proven edge)
    "funding_rate_carry":       2.5,  # 8.19 Sharpe, deserves bigger allocation
    "funding_carry":            2.5,  # Alias
    "funding_rate_carry_pro":   2.5,  # Cerebrus enhanced variant
    "funding_rate_arbitrage":   2.0,  # Related carry strategy, 19-115% annual
    "cross_exchange_basis_carry": 2.5, # Cross-exchange funding spread, 3:1 R:R
    # Cycle 13: Volatility Mean Reversion — 30/30 symbols profitable, universal across all classes
    # XLF PF=5.0/WR=66.7%, SI=F PF=4.08, GC=F PF=3.95, AVAX PF=3.16, USDJPY PF=3.28
    "volatility_mean_reversion": 3.0,  # Highest confidence new strategy — universal edge
    # Cycle 13: Cross-Asset Rotation — ALL-CLASSES PF=3.24/WR=62.5%/n=56
    "cross_asset_rotation":      2.0,  # 21-day rebalance across momentum leaders
    # Cycle 13: Trend Triple Confirmation — CL=F PF=4.65, AVAX PF=4.10, GLD PF=3.92
    "trend_triple_confirmation": 2.0,  # 3 EMA alignment + ADX proxy
    # COMMODITY — Tier 1 per asset_class_health 2026-05-08 (PF 4.07 / WR 67.2% / n=750).
    # Charter "size up where edge is best worth the risk". Per-symbol concentration
    # cap added in config/risk_policy.json::commodity to mitigate inverse-momentum
    # blowup. Banned strategies (commodity_inverse_momentum, cta_commodity_momentum_term)
    # are already excluded by commodity_kill_switch / hedge_fund_quality_gate.
    "cta_commodity_momentum":   2.0,  # cta_bridge.py — metals/energy/grains TSMOM
    "commodity_momentum_12_1":  2.0,  # 12-1 month classical momentum (Asness)
    # Cycle 16 strategies: MACD divergence, momentum breakout, mean reversion ATR, trend ensemble
    "macd_divergence": 2.5,
    "momentum_breakout": 2.0,
    "mean_reversion_atr": 2.0,
    "trend_ensemble": 2.5,
    # Cycle 17 strategies: stoch_rsi, pivot_reversion, ichimoku, yield_curve_proxy, range_trading
    "stoch_rsi": 2.0,
    "pivot_reversion": 1.8,
    "ichimoku": 2.5,
    "yield_curve_proxy": 1.8,
    "range_trading": 1.8,
}
DEFAULT_ALLOCATION = 2000.0  # Base per-pick allocation in dollars

# ---------------------------------------------------------------------------
# Per-category risk parameters  (stop_loss_pct, take_profit_pct, max_hold_days)
# These are DEFAULTS -- strategies can override with ATR-based TP/SL
# Tuned from forward-test MFE analysis (Feb 2026):
#   - Forex: max_hold 7->14d (mean-reversion needs 10-14d to play out)
#            TP 5%->3% (avg MFE ~1.4%, 80th pctile ~2.5%)
#   - Crypto: max_hold 5->7d (too many TIME_EXPIRY at 5d)
#   - Stock: max_hold 7->10d (swing trades need room)
# ---------------------------------------------------------------------------
CATEGORY_RISK: dict[str, tuple[float, float, int]] = {
    "crypto":  (-0.08, 0.15, 7),
    "meme":    (-0.15, 0.35, 3),
    "penny":   (-0.12, 0.25, 5),
    "forex":   (-0.010, 0.015, 7),     # PR3 (2026-05-27): WIDENED SL -0.8% -> -1.0%
    # to clear median daily FX ATR for all G10 pairs. TP unchanged at 1.5%.
    # Prior: 2026-04-25 widened from -0.005/+0.0075. See updates/2026-04-25-forex-tpsl-review.md.
    "stock":   (-0.06, 0.12, 10),
    "equity":  (-0.03, 0.05, 14),      # 3% SL, 5% TP, 14-day hold (earnings/catalysts need time)
}

# Fast variant: 50% tighter TP/SL, 50% shorter hold times
# Produces more frequent signal resolution (TP/SL hit faster)
CATEGORY_RISK_FAST: dict[str, tuple[float, float, int]] = {
    "crypto":  (-0.04, 0.075, 3),
    "meme":    (-0.075, 0.175, 2),
    "penny":   (-0.06, 0.125, 3),
    "forex":   (-0.010, 0.015, 5),     # PR3 (2026-05-27): SL -0.8% -> -1.0% (see CATEGORY_RISK)
    "stock":   (-0.03, 0.06, 5),
    "equity":  (-0.015, 0.025, 7),     # 1.5% SL, 2.5% TP, 7-day hold
}

# Fast mode: swap to tighter risk parameters when ALPHA_FAST_MODE=1
FAST_MODE = bool(os.environ.get("ALPHA_FAST_MODE"))
if FAST_MODE:
    CATEGORY_RISK = CATEGORY_RISK_FAST  # noqa: F811 -- intentional reassignment

# Trailing stop (activates after TRAIL_ACTIVATE_PCT profit)
TRAILING_STOP: dict[str, float] = {
    "crypto": 0.10, "meme": 0.15, "penny": 0.10, "forex": 0.02, "stock": 0.06,
    "equity": 0.04,
}
TRAIL_ACTIVATE_PCT = 0.04

# ---------------------------------------------------------------------------
# COT publication-lag correction + MATCH gate (M-008 / M-021)
# 2026-05-15: 3-calendar-day CFTC publication lag applied to multi_asset_cot
# effective_date to eliminate look-ahead bias. COT_MATCH_REQUIRED gates
# COMMODITY picks on commercial-vs-speculator directional opposition.
# Both flags default ON for COMMODITY; wire-up in quality_gates.passes_active_gate.
# Env overrides: COT_MATCH_GATE_ENABLED=shadow|1|0, COT_LAG_CORRECTION=1|0.
# ---------------------------------------------------------------------------
COT_LAG_CORRECTION: int = 1    # 1 = apply 3-day effective_date lag (default ON)
COT_MATCH_REQUIRED: int = 1    # 1 = require MATCH verdict for COMMODITY (default ON)

# COMMODITY direction policy (2026-05-17):
# LONG blocked via M-042 COMMODITY_SHORT_ONLY=1 (cta_replicator LONG WR=0%, n=24).
# SHORT-only: PF=2.10/WR=58.06% (n=62). Re-enable LONG when:
#   (a) trailing 30-trade WR for COMMODITY LONG > 40%, AND
#   (b) reviewed at next PROBATION checkpoint (2026-06-06 with CT=F review).
# Kill-switch: set COMMODITY_SHORT_ONLY=0 in .env to re-enable LONG immediately.
COMMODITY_LONG_REENABLE_WR_THRESHOLD: float = 0.40   # min WR to re-enable COMMODITY LONG
COMMODITY_LONG_REENABLE_MIN_N: int = 30               # min n trades before re-evaluating

# ---------------------------------------------------------------------------
# Priority 1: Stop the Bleeding - Junk Signal Filters
# ---------------------------------------------------------------------------
# binance_smart_money: 45.8% WR, -0.21% PnL — net loser
# hl_funding_fade: 0/11 = 0% WR — consistently wrong on funding rate reversals
BLACKLISTED_STRATEGIES = [
    'binance_smart_money',       # 45.8% WR, -0.21% PnL — net loser
    'hl_funding_fade',           # 0/11 = 0% WR — consistently wrong on funding rate reversals
    'quan_engine_scalp',         # PF 0.42 / WR 37% — degraded, dead per edge_decay_heatmap
    'claude_gainer_st',          # 26.5% WR / -355% total PnL / 778/790 PROVEN picks (2026-05-01 fix)
    'kimi_signal_tracking',      # -954% PnL / PF 0.26 (SUPREME EDGE P0 #2, 2026-05-11)
    # 2026-05-28 quant review P0 kills — see reports/QUANT_STRATEGY_REVIEW_2026-05-28.md
    'rapid_fire',                # 217 trades, PF 0.77, -70% PnL — biggest volume drag
    'ensemble',                  # 84 CRYPTO trades, PF 0.009, -6066% PnL — worst strategy in system
    'battleground_luxalgo',      # 32 trades, PF 0.18, -117% PnL — grinding losses
    'multi_period_rsi_confluence_eth',  # 16 trades, PF 0.43, -248% PnL
    'ml_breakout',               # 21 trades, 0% WR — ML model completely inverted
    'genome_mutations',          # 6 trades, 0% WR, -107% PnL — mutation engine not working
    # 2026-05-31 (tick 33): stocks_rsi2_pullback UN-KILLED — was killed at n=10 (premature per Phase 3 MC P(T2)=52% @ n=100).
    # Definition lives at copy_trader_intel/multi_asset_copytrader_scraper.py:1247 (scan_stocks_rsi2_pullback) and is dispatched
    # via scan loop at line 2480. quality_gates.py:2791 block already removed 2026-05-19 (WR 50.7% @ n=73 cleared 45% floor).
    # Re-kill trigger: WR<40% on next 30 resolved picks. Mandatory review: 2026-06-15 or n_resolved>=30 post-unkill.
    'multi_asset_scanner',       # FOREX n=11 WR 9.1%, FUTURES n=11 WR 9.1% — universal loser
    'ctar_replicator',           # FOREX n=5 WR 40% PF 0.62, COMMODITY n=2 WR 0% PF 0.0
    # INC FOREX P0 (2026-05-31): block proven losers; only cta_cross_asset_tsmom SHORT + forex_carry probation remain
    'forex_rsi2_mean_reversion',
    'inverse_carry_contrarian',
    'carry_trade_momentum',
    'forex_carry_momentum',
    'forex_carry_ppp',
    'myfxbook_retail_contrarian',
    'forex_carry_bb_hybrid',
]
BLACKLISTED_EXCHANGES = ['bitget']

# ---------------------------------------------------------------------------
# Minimum elite_score gate for pick admission (2026-04-22 edge analysis)
# Data: elite_score >= 70 -> 73.7% WR, +4.06% avg PnL, PF 3.59
#        elite_score < 70  -> 42.1% WR, -0.94% avg PnL, PF 0.87
# Picks below this threshold are structurally unprofitable.
#
# 2026-04-22 REGRESSION FIX: the single global floor of 70 was
# CRYPTO-calibrated. Audit of closed-pick elite_score distribution:
#   CRYPTO: median 32, pct>=70 = 1.3%
#   EQUITY: median 36, pct>=70 = 0.0%
# The global 70 floor hard-killed 100% of EQUITY picks (active count
# 8 → 0 after PR #311 merged). Replaced with a per-asset-class dict
# tuned to each class's score distribution; the global variable is
# kept as a fallback for callers that don't know the class.
# ---------------------------------------------------------------------------
MIN_ELITE_SCORE_FOR_PICKS = 70  # fallback / legacy callers (CRYPTO default)
MIN_ELITE_SCORE_BY_CLASS: dict[str, int] = {
    "CRYPTO":    70,  # preserves original intent; CRYPTO pool bleeds at <70
    "EQUITY":    40,  # 2026-05-14: lowered 60→40 per kilocode vet — active max=30, closed reach 40-60; PF 1.55 warrants wider admission
    "ETF":       35,  # 2026-05-14: lowered 50→35 per kilocode vet — active max=32, closed reach 50-60; PF 1.41 warrants wider admission
    "FOREX":     60,  # 2026-05-14: lowered 70→60 per kilocode vet — active max=18, closed reach 38-42; moderate drop (10pts) per code-reviewer caution: original hard-cap constraint PF≥0.8 still applies
    "COMMODITY": 30,  # 2026-05-15: lowered 45→30 for copper/platinum admission path.
    # After reclassifying HG=F/PL=F from FUTURES to COMMODITY: base(25) + COMMODITY
    # copytrader override(+30) − COMMODITY probation(−16, no_sample) − concentration(−4) = 35.
    # Floor must be ≤35 to admit the first copper pick. Set to 30 for headroom.
    # Tighten to 40 once HG=F accumulates ≥10 live trades (probation penalty drops).
    "BOND":      33,  # 2026-05-15: lowered 40→33 to match bond-agent.yml default + unblock n accrual (n=11, need 100 for T2). Floor 33 lets TIPS/curve-carry pilots emit; tighten to 40 when n≥50.
    # 2026-05-15: Added FUTURES with permissive floor to allow HG=F/PL=F copper/platinum
    # picks through. Without this entry, FUTURES falls back to global floor of 70 which
    # hard-blocks all futures picks. HG=F copper pick scores ~25 elite from multi_asset
    # scanner; class-specific floor of 20 + grade-D/source-trust exemptions = admissible.
    # Tighten if FUTURES WR drops below 45% on first 50 closed picks.
    "FUTURES":   20,
    "CHEAP_STOCKS": 35,
    "IPO":       40,
}

# FOREX hard disable — 2026-05-15
# FOREX class re-enabled 2026-06-05: forex_carry_g10 extended backtest meets unlock condition.
#   PF=1.593, WR=60.4%, n=197 (reports/forex_carry_backtest_extended_20260606.json)
# Kill-switch: set env FOREX_HARD_DISABLE=0 to re-enable.
import os as _forex_os
FOREX_HARD_DISABLE: bool = _forex_os.environ.get("FOREX_HARD_DISABLE", "0") not in ("0", "false", "FALSE", "False")
del _forex_os


# ---------------------------------------------------------------------------
# Source volume cap reference (canonical values in alpha_engine/per_source_volume_cap.py).
# quan_engine drives ~18% of CRYPTO volume at PF=0.70 — a net drag on system PF.
# Active cap in per_source_volume_cap.py: quan_engine CRYPTO=5% (tighter than the
# requested 12%; updated 2026-05-16).
# This dict is informational only — not read by enforcement code.
# ---------------------------------------------------------------------------
SOURCE_VOLUME_CAP_DOC: dict[str, dict[str, float]] = {
    "quan_engine": {"CRYPTO": 0.05},  # enforced in per_source_volume_cap.py
}

# ---------------------------------------------------------------------------
# CRYPTO UTC-hour gate (NS-C filter) — env-var reference
# Implemented in audit_trail/quality_gates.py passes_active_gate() ~line 6543.
# Hours 6, 8, 9 UTC are the "death zone" — rejects picks created in those hours.
# Set to "0" to disable (e.g. for backtesting).
# ---------------------------------------------------------------------------
CRYPTO_UTC_HOUR_FILTER: bool = os.environ.get("CRYPTO_UTC_HOUR_FILTER", "1") not in ("0", "false", "FALSE", "False")

# ---------------------------------------------------------------------------
# P1 quality gates (expert_feedback_action_plan_2026-05-17.md)
# ---------------------------------------------------------------------------

# ETF tight gate — score >= 60 for real-money allocation.
# ETF observed PF=2.25 / WR=66.7% at the looser 35-point floor (n=75).
# Tightening to 60 concentrates edge further.
# Default OFF; enable with ETF_TIGHT_GATE=1 when n >= 100 is confirmed.
# Implemented in audit_trail/quality_gates.py passes_smart_gate().
SMART_PICKS_MIN_SCORE_ETF_TIGHT = 60  # tight gate for real-money; standard is 35

# CRYPTO source-consensus floor — require >= 3 source systems to agree.
# Targets the 7,766 → ~300 reduction to concentrate on proven T1 picks.
# Default 3 (env-var override: CRYPTO_MIN_SOURCE_CONSENSUS).
# Implemented in audit_trail/quality_gates.py passes_smart_gate().
CRYPTO_MIN_SOURCE_CONSENSUS: int = int(os.getenv("CRYPTO_MIN_SOURCE_CONSENSUS", "3"))

# EQUITY confidence inversion penalty — env-var reference
# Implemented in audit_trail/quality_gates.py calculate_smart_score() ~line 3251.
# Applies -15 score penalty when EQUITY pick confidence > 0.70.
# LOW-conf EQUITY WR=70.2%/PF=4.31 vs HIGH-conf WR=38.1%/PF=1.04 (2026-05-16 audit).
# Set EQUITY_CONFIDENCE_INVERSION_PENALTY_DISABLED=1 to disable.
EQUITY_CONFIDENCE_INVERSION_PENALTY: bool = os.environ.get("EQUITY_CONFIDENCE_INVERSION_PENALTY_DISABLED", "0") not in ("1", "true", "TRUE", "True")

# Quarter-Kelly position sizing for EQUITY (hedge-fund risk discipline)
# Full Kelly = edge/odds; quarter-Kelly = F* / 4 (reduces risk of ruin)
EQUITY_KELLY_FRACTION = 0.25  # quarter-Kelly
EQUITY_MAX_POSITION_PCT = 0.02  # 2% account max per pick ($200 per $10k)
EQUITY_DD_HALT_THRESHOLD = 0.30  # pause all sizing if 30-day drawdown > 30%

# Tiered conviction sizing for EQUITY (2026-05-17, swarm recommendation)
# Concentrates capital in higher-conviction picks to push PF 1.65 → 2.0+
# Applied as a multiplier on top of EQUITY_KELLY_FRACTION base size.
# Tiers: high (score>80) = 1.5x, medium (60-80) = 1.0x, low (<60) = 0.5x
# Env-gated: EQUITY_CONVICTION_TIERS=1 (default OFF until shadow validates)
EQUITY_CONVICTION_TIER_HIGH_SCORE: int = 80   # score threshold for high tier
EQUITY_CONVICTION_TIER_HIGH_MULT: float = 1.5  # 1.5x base Kelly
EQUITY_CONVICTION_TIER_MED_SCORE: int = 60    # score threshold for medium tier
EQUITY_CONVICTION_TIER_MED_MULT: float = 1.0  # 1.0x base Kelly
EQUITY_CONVICTION_TIER_LOW_MULT: float = 0.5  # 0.5x base Kelly (< med threshold)

def min_elite_score_for(asset_class: str | None) -> int:
    """Return the per-asset-class elite-score floor, with sensible fallback.

    Callers that don't know the asset class should continue to use
    MIN_ELITE_SCORE_FOR_PICKS directly; this helper is for the
    asset-class-aware enforcement path.
    """
    if not asset_class:
        return MIN_ELITE_SCORE_FOR_PICKS
    key = str(asset_class).upper().strip()
    return MIN_ELITE_SCORE_BY_CLASS.get(key, MIN_ELITE_SCORE_FOR_PICKS)

# ---------------------------------------------------------------------------
# Per-strategy confidence gates (2026-04-22 edge analysis)
# ml_crypto_predictor: confidence=0.50, elite_score=43 -> worst performer.
#   8 of 17 crypto picks from this source, avg PnL -0.26%.
#   Raising min confidence to 0.70 eliminates low-conviction spam.
# ---------------------------------------------------------------------------
STRATEGY_MIN_CONFIDENCE: dict[str, float] = {
    "ml_crypto_predictor": 0.70,
}
MIN_COPY_TRADER_PF = 1.5    # Was 10.01 — too strict, blocked 90% of sources (2026-05-01 fix)
MIN_CLOSED_TRADES = 10     # Was 50 — too strict for newer sources (2026-05-01 fix)

# ---------------------------------------------------------------------------
# P0 CRYPTO hard-gate thresholds (expert feedback 2026-05-17)
# All three are env-var overridable at admission time.
# ---------------------------------------------------------------------------
# M-035: confidence > 0.85 = inversion zone (WR drops below 40% empirically).
# Raised from 0.90→0.85 (2026-05-17 AG swarm recommendation) to close the gap
# previously left open between M-034 (0.85-0.90, OFF) and M-035 (0.90, ON).
# M-034 is no longer needed as the sole guard for 0.85-0.90 since M-035 now covers it.
CRYPTO_MAX_CONFIDENCE = 0.85

# M-036: direction="BUY" is anti-predictive for CRYPTO (PF=0.38 / WR=28.9%)
# Only LONG / SHORT are valid directional values for CRYPTO picks.
CRYPTO_BLOCKED_DIRECTIONS = frozenset({"BUY"})

# M-037: ml_score floor — bottom 30% = 32.5% WR, top 30% = 60% WR
MIN_ML_SCORE_CRYPTO = 0.65

CRYPTO_SYMBOL_REGEX = r'^[A-Z0-9]+USDT$'

# ---------------------------------------------------------------------------
# Symbol universes
# ---------------------------------------------------------------------------

# -- Crypto (yfinance tickers) --
CRYPTO_SYMBOLS: dict[str, dict] = {
    # Majors -- signature-specific strategies tuned for each
    "BTC-USD":  {"name": "Bitcoin",   "tier": "major", "cat": "crypto",
                 "binance": "BTCUSDT",  "halving_cycle_pos": 0.55},
    "ETH-USD":  {"name": "Ethereum",  "tier": "major", "cat": "crypto",
                 "binance": "ETHUSDT",  "merge_era": True},
    "SOL-USD":  {"name": "Solana",    "tier": "major", "cat": "crypto",
                 "binance": "SOLUSDT"},
    "BNB-USD":  {"name": "BNB",       "tier": "major", "cat": "crypto",
                 "binance": "BNBUSDT"},
    "XRP-USD":  {"name": "XRP",       "tier": "major", "cat": "crypto",
                 "binance": "XRPUSDT"},
    "ADA-USD":  {"name": "Cardano",   "tier": "major", "cat": "crypto",
                 "binance": "ADAUSDT"},
    "AVAX-USD": {"name": "Avalanche", "tier": "major", "cat": "crypto",
                 "binance": "AVAXUSDT"},
    "LINK-USD": {"name": "Chainlink", "tier": "major", "cat": "crypto",
                 "binance": "LINKUSDT"},
    # Rotated Feb 26 2026: DOT → TAO (AI narrative momentum)
    # NOTE: "TAO-USD" on yfinance is WRONG token ("Together As One"). Bittensor = TAO22974-USD.
    "TAO-USD":  {"name": "Bittensor", "tier": "major", "cat": "crypto",
                 "binance": "TAOUSDT", "yf_ticker": "TAO22974-USD"},
    "NEAR-USD": {"name": "NEAR",      "tier": "major", "cat": "crypto",
                 "binance": "NEARUSDT"},
    "TRX-USD":  {"name": "TRON",      "tier": "major", "cat": "crypto",
                 "binance": "TRXUSDT"},
    "TON11419-USD": {"name": "Toncoin", "tier": "major", "cat": "crypto",
                     "binance": "TONUSDT"},
    # NOTE: "TON-USD" on yfinance is WRONG token ($0.004). Toncoin = TON11419-USD.
    # Rotated Feb 26 2026: LTC → RENDER (AI/GPU narrative momentum)
    # NOTE: yfinance has both RNDR-USD and RENDER-USD; RENDER-USD is the rebranded ticker
    "RNDR-USD": {"name": "Render",    "tier": "major", "cat": "crypto",
                 "binance": "RENDERUSDT", "yf_ticker": "RENDER-USD"},
    "ETC-USD":  {"name": "Ethereum Classic", "tier": "major", "cat": "crypto",
                 "binance": "ETCUSDT"},
    "LTC-USD":  {"name": "Litecoin",  "tier": "major", "cat": "crypto",
                 "binance": "LTCUSDT"},

    # Alts / L1
    # NOTE: "SUI-USD" on yfinance doesn't work. Sui = SUI20947-USD.
    "SUI-USD":      {"name": "Sui",      "tier": "alt", "cat": "crypto",
                     "binance": "SUIUSDT", "yf_ticker": "SUI20947-USD"},
    "TIA-USD":      {"name": "Celestia", "tier": "alt", "cat": "crypto",
                     "binance": "TIAUSDT"},
    "INJ-USD":      {"name": "Injective","tier": "alt", "cat": "crypto",
                     "binance": "INJUSDT"},
    "ATOM-USD":     {"name": "Cosmos",   "tier": "alt", "cat": "crypto",
                     "binance": "ATOMUSDT"},
    "FIL-USD":      {"name": "Filecoin", "tier": "alt", "cat": "crypto",
                     "binance": "FILUSDT"},
    "APT-USD":      {"name": "Aptos",    "tier": "alt", "cat": "crypto",
                     "binance": "APTUSDT"},
    "SEI-USD":      {"name": "Sei",      "tier": "alt", "cat": "crypto",
                     "binance": "SEIUSDT"},
    "PENDLE-USD":   {"name": "Pendle",   "tier": "alt", "cat": "crypto",
                     "binance": "PENDLEUSDT"},
    "GALA-USD":     {"name": "Gala",     "tier": "alt", "cat": "crypto",
                     "binance": "GALAUSDT"},
    "WLD-USD":      {"name": "Worldcoin","tier": "alt", "cat": "crypto",
                     "binance": "WLDUSDT"},
    "NOT-USD":      {"name": "Notcoin",  "tier": "alt", "cat": "crypto",
                     "binance": "NOTUSDT"},
    "TURBO-USD":    {"name": "Turbo",    "tier": "alt", "cat": "crypto",
                     "binance": "TURBOUSDT"},
    
    # -- Added 2026-03-16: Expanding crypto universe (missed top gainers + top 30 gaps) --
    "ZRO-USD":      {"name": "LayerZero","tier": "alt", "cat": "crypto",
                     "binance": "ZROUSDT", "yf_ticker": "ZRO1-USD"},  # ZRO-USD delisted; rebranded ticker
    # NOTE: "HYPE-USD" on yfinance is wrong. Hyperliquid = HYPE32196-USD.
    "HYPE-USD":     {"name": "Hyperliquid","tier": "major", "cat": "crypto",
                     "binance": "HYPEUSDT", "yf_ticker": "HYPE32196-USD"},  # Top-15 by market cap ($9B)
    "XLM-USD":      {"name": "Stellar",  "tier": "major", "cat": "crypto",
                     "binance": "XLMUSDT"},   # Top-21, $5.6B cap, in ZERO scanners
    "ZEC-USD":      {"name": "Zcash",    "tier": "alt", "cat": "crypto",
                     "binance": "ZECUSDT"},   # +8.2% gainer, $3.9B cap, was KIMI-only
    "CAKE-USD":     {"name": "PancakeSwap","tier": "defi", "cat": "crypto",
                     "binance": "CAKEUSDT"},  # +7.7% gainer, DeFi narrative
    "HBAR-USD":     {"name": "Hedera",   "tier": "alt", "cat": "crypto",
                     "binance": "HBARUSDT"},  # In dashboard TRACKED_SYMBOLS but not in scanner
    "DOT-USD":      {"name": "Polkadot", "tier": "alt", "cat": "crypto",
                     "binance": "DOTUSDT"},   # Top-15, in Battleground but missing from Alpha Engine
    "DOGE-USD":     {"name": "Dogecoin", "tier": "meme", "cat": "meme",
                     "binance": "DOGEUSDT"},  # Top-10 by cap, was in KIMI but not Alpha Engine
    "JUP-USD":      {"name": "Jupiter",  "tier": "alt", "cat": "crypto",
                     "binance": "JUPUSDT"},   # Solana DEX, in Battleground incubators only
    "STX-USD":      {"name": "Stacks",   "tier": "alt", "cat": "crypto",
                     "binance": "STXUSDT"},   # Bitcoin L2, in Battleground incubators only
    "ENA-USD":      {"name": "Ethena",   "tier": "alt", "cat": "crypto",
                     "binance": "ENAUSDT"},   # Stablecoin yield, in Battleground incubators only

    # -- Added 2026-03-18: Top-100 coins missing from tracking universe --
    "KAS-USD":      {"name": "Kaspa",    "tier": "alt", "cat": "crypto",
                     "binance": "KASUSDT"},    # #54 by market cap, L1/PoW
    "ONDO-USD":     {"name": "Ondo",     "tier": "alt", "cat": "crypto",
                     "binance": "ONDOUSDT"},   # #50 by market cap, RWA tokenization
    "ICP-USD":      {"name": "Internet Computer", "tier": "alt", "cat": "crypto",
                     "binance": "ICPUSDT"},    # #48 by market cap, L1

    # DeFi
    "UNI-USD":      {"name": "Uniswap",  "tier": "defi", "cat": "crypto",
                     "binance": "UNIUSDT"},
    "AAVE-USD":     {"name": "Aave",     "tier": "defi", "cat": "crypto",
                     "binance": "AAVEUSDT"},
    "MAV-USD":      {"name": "Maverick","tier": "defi", "cat": "crypto",
                     "binance": "MAVUSDT"},
    # NOTE: "PEPE-USD" on yfinance is wrong. Pepe = PEPE24478-USD.
    "PEPE-USD":     {"name": "Pepe",    "tier": "meme", "cat": "meme",
                     "binance": "PEPEUSDT", "yf_ticker": "PEPE24478-USD"},
    "WIF-USD":      {"name": "dogwifhat","tier": "meme", "cat": "meme",
                     "binance": "WIFUSDT"},
    "BONK-USD":     {"name": "Bonk",     "tier": "meme", "cat": "meme",
                     "binance": "BONKUSDT"},
    "FLOKI-USD":    {"name": "Floki",    "tier": "meme", "cat": "meme",
                     "binance": "FLOKIUSDT"},
    "MEME-USD":     {"name": "Meme",     "tier": "meme", "cat": "crypto",
                     "binance": "MEMEUSDT"},
    "BOME-USD":     {"name": "Book of Meme","tier": "meme", "cat": "crypto",
                     "binance": "BOMEUSDT"},

    # -- Added 2026-03-16: Expanded universe (user request -- 41 symbol scan list) --
    "MATIC-USD":    {"name": "Polygon",    "tier": "alt", "cat": "crypto",
                     "binance": "POLUSDT"},    # Note: yfinance still uses MATIC-USD, Binance rebranded to POL
    "BCH-USD":      {"name": "Bitcoin Cash","tier": "major", "cat": "crypto",
                     "binance": "BCHUSDT"},
    "SHIB-USD":     {"name": "Shiba Inu",  "tier": "meme", "cat": "meme",
                     "binance": "SHIBUSDT"},
    "ARB11841-USD": {"name": "Arbitrum",   "tier": "alt", "cat": "crypto",
                     "binance": "ARBUSDT"},    # Note: yfinance uses ARB11841-USD for Arbitrum
    "OP-USD":       {"name": "Optimism",   "tier": "alt", "cat": "crypto",
                     "binance": "OPUSDT"},
    "DYDX-USD":     {"name": "dYdX",       "tier": "defi", "cat": "crypto",
                     "binance": "DYDXUSDT"},
    "APE-USD":      {"name": "ApeCoin",    "tier": "alt", "cat": "crypto",
                     "binance": "APEUSDT"},
    "ALGO-USD":     {"name": "Algorand",   "tier": "alt", "cat": "crypto",
                     "binance": "ALGOUSDT"},
    "STRK-USD":     {"name": "StarkNet",   "tier": "alt", "cat": "crypto",
                     "binance": "STRKUSDT"},
    "ZK-USD":       {"name": "ZKsync",     "tier": "alt", "cat": "crypto",
                     "binance": "ZKUSDT", "yf_ticker": "ZKSYNC-USD"},  # ZK-USD delisted; rebranded
    "CHZ-USD":      {"name": "Chiliz",     "tier": "alt", "cat": "crypto",
                     "binance": "CHZUSDT"},
    "W-USD":        {"name": "Wormhole",   "tier": "alt", "cat": "crypto",
                     "binance": "WUSDT"},
    "JTO-USD":      {"name": "Jito",       "tier": "alt", "cat": "crypto",
                     "binance": "JTOUSDT"},
    "FET-USD":      {"name": "Fetch.ai",   "tier": "alt", "cat": "crypto",
                     "binance": "FETUSDT"},

    # -- Added 2026-03-18 Wave 40: Expanded to full top-100 coverage --
    "FTM-USD":      {"name": "Fantom/Sonic","tier": "alt", "cat": "crypto", "binance": "FTMUSDT",
                     "yf_ticker": "S-USD"},  # Fantom rebranded to Sonic; FTM-USD delisted on yfinance
    "THETA-USD":    {"name": "Theta",      "tier": "alt", "cat": "crypto", "binance": "THETAUSDT"},
    "VET-USD":      {"name": "VeChain",    "tier": "alt", "cat": "crypto", "binance": "VETUSDT"},
    "EOS-USD":      {"name": "EOS",        "tier": "alt", "cat": "crypto", "binance": "EOSUSDT"},
    "XTZ-USD":      {"name": "Tezos",      "tier": "alt", "cat": "crypto", "binance": "XTZUSDT"},
    "SAND-USD":     {"name": "Sandbox",    "tier": "alt", "cat": "crypto", "binance": "SANDUSDT"},
    "MANA-USD":     {"name": "Decentraland","tier": "alt", "cat": "crypto", "binance": "MANAUSDT"},
    "AXS-USD":      {"name": "Axie Infinity","tier": "alt", "cat": "crypto", "binance": "AXSUSDT"},
    "CRV-USD":      {"name": "Curve",      "tier": "defi", "cat": "crypto", "binance": "CRVUSDT"},
    "RUNE-USD":     {"name": "THORChain",  "tier": "defi", "cat": "crypto", "binance": "RUNEUSDT"},
    "LDO-USD":      {"name": "Lido",       "tier": "defi", "cat": "crypto", "binance": "LDOUSDT"},
    "MKR-USD":      {"name": "Maker",      "tier": "defi", "cat": "crypto", "binance": "MKRUSDT"},
    "COMP-USD":     {"name": "Compound",   "tier": "defi", "cat": "crypto", "binance": "COMPUSDT",
                     "yf_ticker": "COMP1-USD"},  # COMP-USD delisted on yfinance; rebranded ticker
    "SNX-USD":      {"name": "Synthetix",  "tier": "defi", "cat": "crypto", "binance": "SNXUSDT"},
    "ENS-USD":      {"name": "ENS",        "tier": "alt", "cat": "crypto", "binance": "ENSUSDT"},
    "1INCH-USD":    {"name": "1inch",      "tier": "defi", "cat": "crypto", "binance": "1INCHUSDT"},
    "SUSHI-USD":    {"name": "SushiSwap",  "tier": "defi", "cat": "crypto", "binance": "SUSHIUSDT"},
    "BAT-USD":      {"name": "Basic Attention","tier": "alt", "cat": "crypto", "binance": "BATUSDT"},
    "ZRX-USD":      {"name": "0x",         "tier": "defi", "cat": "crypto", "binance": "ZRXUSDT"},
    "IMX-USD":      {"name": "ImmutableX", "tier": "alt", "cat": "crypto", "binance": "IMXUSDT",
                     "yf_ticker": "IMX1-USD"},  # IMX-USD delisted on yfinance; rebranded ticker
    "EGLD-USD":     {"name": "MultiversX", "tier": "alt", "cat": "crypto", "binance": "EGLDUSDT"},
    "FLOW-USD":     {"name": "Flow",       "tier": "alt", "cat": "crypto", "binance": "FLOWUSDT"},
    "MINA-USD":     {"name": "Mina",       "tier": "alt", "cat": "crypto", "binance": "MINAUSDT"},
    "NEO-USD":      {"name": "Neo",        "tier": "alt", "cat": "crypto", "binance": "NEOUSDT"},
    "IOTA-USD":     {"name": "IOTA",       "tier": "alt", "cat": "crypto", "binance": "IOTAUSDT"},
    "YFI-USD":      {"name": "Yearn",      "tier": "defi", "cat": "crypto", "binance": "YFIUSDT"},
    "BLUR-USD":     {"name": "Blur",       "tier": "alt", "cat": "crypto", "binance": "BLURUSDT"},
    "JASMY-USD":    {"name": "JasmyCoin",  "tier": "alt", "cat": "crypto", "binance": "JASMYUSDT"},
    "POPCAT-USD":   {"name": "Popcat",     "tier": "meme", "cat": "meme", "binance": "POPCATUSDT",
                     "yf_ticker": "POPCAT1-USD"},  # POPCAT-USD delisted on yfinance; rebranded ticker
    "MEW-USD":      {"name": "cat in a dogs world","tier": "meme", "cat": "meme", "binance": "MEWUSDT",
                     "yf_ticker": "MEW1-USD"},  # MEW-USD delisted on yfinance; rebranded ticker
    "NEIRO-USD":    {"name": "Neiro",      "tier": "meme", "cat": "meme", "binance": "NEIROUSDT"},
    "PYTH-USD":     {"name": "Pyth",       "tier": "alt", "cat": "crypto", "binance": "PYTHUSDT"},

    # -- Added 2026-03-19: Hindsight learner most-missed symbols (17 evals) --
    "ROBO-USD":     {"name": "Robo",       "tier": "alt", "cat": "crypto", "binance": "ROBOUSDT",
                     "yf_ticker": "ROBO1-USD"},  # ROBO-USD delisted; rebranded ticker
    "JTO-USD2":     {"name": "Jito",       "tier": "alt", "cat": "crypto", "binance": "JTOUSDT",
                     "yf_ticker": "JTO-USD"},  # Duplicate key; maps to real JTO-USD on yfinance
    "PIXEL-USD":    {"name": "Pixels",     "tier": "alt", "cat": "crypto", "binance": "PIXELUSDT",
                     "yf_ticker": "PORTAL-USD"},  # PIXEL-USD delisted; rebranded to Portal
    "DEGO-USD":     {"name": "Dego",       "tier": "alt", "cat": "crypto", "binance": "DEGOUSDT", "yf_skip": True},
    "ENJ-USD":      {"name": "Enjin",      "tier": "alt", "cat": "crypto", "binance": "ENJUSDT"},
    "THE-USD":      {"name": "Thena",      "tier": "alt", "cat": "crypto", "binance": "THEUSDT",
                     "yf_ticker": "THE1-USD"},  # THE-USD delisted; rebranded ticker
    "HOT-USD":      {"name": "Holo",       "tier": "alt", "cat": "crypto", "binance": "HOTUSDT"},
    "SAHARA-USD":   {"name": "Sahara AI",  "tier": "alt", "cat": "crypto", "binance": "SAHARAUSDT", "yf_skip": True},
    # BARD-USD removed -- not a real token (fake/non-existent on exchanges)
    "ANKR-USD":     {"name": "Ankr",       "tier": "alt", "cat": "crypto", "binance": "ANKRUSDT"},

    # -- Added 2026-03-19: 1h gainer analysis -- high-volume missed movers --
    # TRUSTWORTHY (large-cap, established projects, $10M+ daily volume)
    "ETHFI-USD":    {"name": "ether.fi",   "tier": "defi", "cat": "crypto", "binance": "ETHFIUSDT"},  # Liquid staking, $24M vol
    "XMR-USD":      {"name": "Monero",     "tier": "major", "cat": "crypto", "binance": "XMRUSDT"},  # Privacy coin, established since 2014
    "QNT-USD":      {"name": "Quant",      "tier": "alt", "cat": "crypto", "binance": "QNTUSDT"},    # Enterprise blockchain, $3.3M vol

    # MODERATE RISK (mid-cap, $2-10M daily volume) -- [WARN]️ wider stops recommended
    "DEXE-USD":     {"name": "DeXe",       "tier": "alt", "cat": "crypto", "binance": "DEXEUSDT",
                     "risk_warning": "Small-cap DeFi governance, volatile, use wider SL"},
    "LIT-USD":      {"name": "Litentry",   "tier": "alt", "cat": "crypto", "binance": "LITUSDT",
                     "risk_warning": "Low liquidity (<$1M vol), prone to pump/dump"},
    "TOMO-USD":     {"name": "TomoChain",  "tier": "alt", "cat": "crypto", "binance": "TOMOUSDT",
                     "risk_warning": "Rebranded (Viction), thin order book"},

    # HIGHER RISK (small-cap, <$2M daily volume) -- [WARN]️[WARN]️ meme/micro-cap territory
    "BAKE-USD":     {"name": "BakerySwap", "tier": "defi", "cat": "crypto", "binance": "BAKEUSDT",
                     "risk_warning": "BSC DeFi micro-cap, extreme volatility, +12% 1h swings common"},
    "HIFI-USD":     {"name": "Hifi Finance","tier": "defi", "cat": "crypto", "binance": "HIFIUSDT",
                     "risk_warning": "Sub-$1M volume, fixed-rate lending protocol, illiquid",
                     "yf_ticker": "HIFI1-USD"},  # HIFI-USD delisted on yfinance; rebranded ticker

    # -- Tier 7: Top Gainers Discovery (Mar 23, 2026) --
    "KITE-USD":     {"name": "Kite",       "tier": "alt", "cat": "crypto", "binance": "KITEUSDT", "yf_skip": True},
    "XDC-USD":      {"name": "XDC Network","tier": "alt", "cat": "crypto", "binance": "XDCUSDT"},
    "NEXO-USD":     {"name": "Nexo",       "tier": "alt", "cat": "crypto", "binance": "NEXOUSDT"},
    "BGB-USD":      {"name": "Bitget Token","tier": "alt", "cat": "crypto", "binance": "BGBUSDT", "yf_skip": True},
    "AERO-USD":     {"name": "Aerodrome",  "tier": "defi", "cat": "crypto", "binance": "AEROUSDT", "yf_skip": True},
    "HNT-USD":      {"name": "Helium",     "tier": "alt", "cat": "crypto", "binance": "HNTUSDT"},
    "KAITO-USD":    {"name": "Kaito",      "tier": "alt", "cat": "crypto", "binance": "KAITOUSDT", "yf_skip": True},
    "PEAQ-USD":     {"name": "peaq",       "tier": "alt", "cat": "crypto", "binance": "PEAQUSDT", "yf_skip": True},
}

# -- Forex (yfinance tickers) --
# carry_yield_diff: annualized interest rate differential (base - quote)
# Updated 2026-04-01: Fed 4.25%, ECB 2.50%, BoJ 0.50%, RBA 4.10%, RBNZ 3.75%,
#   BoC 2.75%, SNB 0.25%, BoE 4.50%
FOREX_SYMBOLS: dict[str, dict] = {
    "EURUSD=X": {"name": "EUR/USD", "cat": "forex",
                 "base": "EUR", "quote": "USD", "carry_yield_diff": -1.75},
    "GBPUSD=X": {"name": "GBP/USD", "cat": "forex",
                 "base": "GBP", "quote": "USD", "carry_yield_diff": 0.25},
    "USDJPY=X": {"name": "USD/JPY", "cat": "forex",
                 "base": "USD", "quote": "JPY", "carry_yield_diff": 4.5},
    "AUDUSD=X": {"name": "AUD/USD", "cat": "forex",
                 "base": "AUD", "quote": "USD", "carry_yield_diff": 1.2},
    "USDCAD=X": {"name": "USD/CAD", "cat": "forex",
                 "base": "USD", "quote": "CAD", "carry_yield_diff": -0.3},
    "NZDUSD=X": {"name": "NZD/USD", "cat": "forex",
                 "base": "NZD", "quote": "USD", "carry_yield_diff": 1.5},
    "USDCHF=X": {"name": "USD/CHF", "cat": "forex",
                 "base": "USD", "quote": "CHF", "carry_yield_diff": 4.0},
    "EURJPY=X": {"name": "EUR/JPY", "cat": "forex",
                 "base": "EUR", "quote": "JPY", "carry_yield_diff": 2.0},
    "GBPJPY=X": {"name": "GBP/JPY", "cat": "forex",
                 "base": "GBP", "quote": "JPY", "carry_yield_diff": 4.0},
    "AUDJPY=X": {"name": "AUD/JPY", "cat": "forex",
                 "base": "AUD", "quote": "JPY", "carry_yield_diff": 3.6},
    "EURGBP=X": {"name": "EUR/GBP", "cat": "forex",
                 "base": "EUR", "quote": "GBP", "carry_yield_diff": -2.0},
    # 2026-04-12: expanded forex universe for more RSI-2 oversold signals
    # forex_rsi2_mean_reversion (PF 3.69) needs more pairs to generate volume
    "NZDJPY=X": {"name": "NZD/JPY", "cat": "forex",
                 "base": "NZD", "quote": "JPY", "carry_yield_diff": 3.8},
    "CADJPY=X": {"name": "CAD/JPY", "cat": "forex",
                 "base": "CAD", "quote": "JPY", "carry_yield_diff": 3.5},
    "EURAUD=X": {"name": "EUR/AUD", "cat": "forex",
                 "base": "EUR", "quote": "AUD", "carry_yield_diff": -2.5},
    "GBPAUD=X": {"name": "GBP/AUD", "cat": "forex",
                 "base": "GBP", "quote": "AUD", "carry_yield_diff": -1.0},
    "AUDNZD=X": {"name": "AUD/NZD", "cat": "forex",
                 "base": "AUD", "quote": "NZD", "carry_yield_diff": -0.3},
    "EURCHF=X": {"name": "EUR/CHF", "cat": "forex",
                 "base": "EUR", "quote": "CHF", "carry_yield_diff": 2.0},
    "GBPCHF=X": {"name": "GBP/CHF", "cat": "forex",
                 "base": "GBP", "quote": "CHF", "carry_yield_diff": 3.5},
    "USDSGD=X": {"name": "USD/SGD", "cat": "forex",
                 "base": "USD", "quote": "SGD", "carry_yield_diff": 0.8},
    "USDMXN=X": {"name": "USD/MXN", "cat": "forex",
                 "base": "USD", "quote": "MXN", "carry_yield_diff": -6.0},
    "USDNOK=X": {"name": "USD/NOK", "cat": "forex",
                 "base": "USD", "quote": "NOK", "carry_yield_diff": -0.5},
}

# Per-symbol PnL concentration cap (FETUSDT was 52% of all profits)
MAX_SYMBOL_PNL_CONCENTRATION = 0.30

# -- Stocks / Penny / Meme equities --
EQUITY_SYMBOLS: dict[str, dict] = {
    # Large-cap tech
    "AAPL":  {"name": "Apple",     "cat": "stock"},
    "MSFT":  {"name": "Microsoft", "cat": "stock"},
    "NVDA":  {"name": "Nvidia",    "cat": "stock"},
    "TSLA":  {"name": "Tesla",     "cat": "stock"},
    "AMZN":  {"name": "Amazon",    "cat": "stock"},
    "GOOGL": {"name": "Alphabet",  "cat": "stock"},
    "META":  {"name": "Meta",      "cat": "stock"},
    "AMD":   {"name": "AMD",       "cat": "stock"},
    # ETFs (kept for backward compat; SPY/QQQ also live in ETF_SYMBOLS)
    "SPY":  {"name": "S&P 500 ETF",   "cat": "stock"},
    "QQQ":  {"name": "Nasdaq 100 ETF","cat": "stock"},
    # Penny / speculative
    "PLTR": {"name": "Palantir",  "cat": "penny"},
    "SOFI": {"name": "SoFi",      "cat": "penny"},
    "RIVN": {"name": "Rivian",    "cat": "penny"},
    "LCID": {"name": "Lucid",     "cat": "penny"},
    "NIO":  {"name": "NIO",       "cat": "penny"},
    "SNDL": {"name": "Sundial",   "cat": "penny"},
    # Meme
    "GME":  {"name": "GameStop",  "cat": "meme"},
    "AMC":  {"name": "AMC",       "cat": "meme"},
    "COIN": {"name": "Coinbase",  "cat": "stock"},
    "MSTR": {"name": "MicroStrategy","cat": "stock"},
    # 2026-05-17: +15 liquid large-caps for RSI2 pick acceleration
    # All already in STOCK_SYMBOLS (multi_asset_copytrader_scraper.py) so
    # stocks_rsi2_pullback already generates picks on these. Adding here
    # enables scanner.py --equity-only path + correct asset classification.
    # None conflict with ETF_SYMBOLS. All in LARGE_CAP_EQUITY_SYMBOLS frozenset.
    "JPM":  {"name": "JPMorgan Chase",  "cat": "stock"},
    "BAC":  {"name": "Bank of America", "cat": "stock"},
    "V":    {"name": "Visa",            "cat": "stock"},
    "MA":   {"name": "Mastercard",      "cat": "stock"},
    "WMT":  {"name": "Walmart",         "cat": "stock"},
    "HD":   {"name": "Home Depot",      "cat": "stock"},
    "PG":   {"name": "Procter & Gamble","cat": "stock"},
    "KO":   {"name": "Coca-Cola",       "cat": "stock"},
    "PEP":  {"name": "PepsiCo",         "cat": "stock"},
    "JNJ":  {"name": "Johnson & Johnson","cat": "stock"},
    "PFE":  {"name": "Pfizer",          "cat": "stock"},
    "CVX":  {"name": "Chevron",         "cat": "stock"},
    "AVGO": {"name": "Broadcom",        "cat": "stock"},
    "COST": {"name": "Costco",          "cat": "stock"},
    "LLY":  {"name": "Eli Lilly",       "cat": "stock"},
}

# Large-cap equity filter — institutional-quality names only (2026-05-15)
# Splits EQUITY into liquid large-cap vs speculative. Use is_liquid_equity(symbol)
# before sizing to avoid penny/gap-risk names dragging EQUITY PF.
# Source: CLAUDE.md Goal #1 + Cursor institutional plan E2.
LARGE_CAP_EQUITY_SYMBOLS: frozenset[str] = frozenset({
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "BRK-B",
    "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL", "ADBE",
    "NFLX", "CRM", "ORCL", "IBM", "INTC", "AMD", "QCOM", "TXN", "AVGO",
    "BAC", "WFC", "GS", "MS", "C", "AXP", "BLK", "SCHW",
    "XOM", "CVX", "COP", "SLB", "MPC",
    "LLY", "MRK", "ABT", "TMO", "DHR", "PFE", "AMGN", "GILD",
    "SPY", "QQQ", "IWM",  # broad ETFs sometimes scored as equity
})

GAP_RISK_EQUITY_SYMBOLS: frozenset[str] = frozenset({
    "NIO", "LCID", "RIVN", "GME", "AMC", "BBBY", "SPCE", "CLOV", "WISH",
    "PLTR",  # high volatility / low float
    "SOFI", "SNDL",  # EAGLE 2026-05-27: penny drag on EQUITY class metrics
})

# Production EQUITY scanner must not emit these (research/paper only).
# Union of gap-risk + explicit penny/meme names still listed in EQUITY_SYMBOLS
# for backward-compatible classification in legacy JSON.
RESEARCH_ONLY_SPECULATIVE_SYMBOLS: frozenset[str] = frozenset(
    GAP_RISK_EQUITY_SYMBOLS | {"SOFI", "SNDL"}
)


def is_research_only_speculative(symbol: str) -> bool:
    """True if symbol is quarantined from production EQUITY emissions."""
    return symbol.upper() in RESEARCH_ONLY_SPECULATIVE_SYMBOLS


def is_liquid_equity(symbol: str) -> bool:
    """Return True if symbol is an institutional-quality large-cap equity."""
    return symbol.upper() in LARGE_CAP_EQUITY_SYMBOLS


def is_gap_risk_equity(symbol: str) -> bool:
    """Return True if symbol has elevated gap-risk (low float, meme-adjacent)."""
    return symbol.upper() in GAP_RISK_EQUITY_SYMBOLS


# ---------------------------------------------------------------------------
# M-032: FRED macro data config (2026-05-15)
# Set FRED_API_KEY env var to enable. Free key: https://fred.stlouisfed.org/docs/api/api_key.html
# When enabled, unblocks tools/fred_data_fetcher.py for BOND + ETF + EQUITY macro context.
# ---------------------------------------------------------------------------
import os as _os_fred
FRED_API_KEY: str = _os_fred.environ.get("FRED_API_KEY", "")
FRED_CACHE_TTL_HOURS: int = int(_os_fred.environ.get("FRED_CACHE_TTL_HOURS", "6"))
FRED_ENABLED: bool = bool(FRED_API_KEY)
FRED_SERIES: dict[str, str] = {
    "DGS10":    "10-Year Treasury Constant Maturity Rate",
    "DGS2":     "2-Year Treasury Constant Maturity Rate",
    "T10Y2Y":   "10-Year minus 2-Year Treasury Yield Spread",
    "VIXCLS":   "CBOE Volatility Index (VIX)",
    "DTWEXBGS": "US Dollar Broad Index",
    "UNRATE":   "Unemployment Rate",
    "FEDFUNDS": "Federal Funds Effective Rate",
}


# -- Commodities (yfinance tickers) --
COMMODITY_SYMBOLS: dict[str, dict] = {
    "GC=F":  {"name": "Gold",        "cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5, "seasonal_bullish": [1, 2, 8, 9]},
    "SI=F":  {"name": "Silver",      "cat": "commodity", "atr_mult_tp": 2.5, "atr_mult_sl": 1.5, "seasonal_bullish": [1, 2, 7, 8]},
    # "CL=F" REMOVED: 26 futures trades, 3.8% WR, -29.82% PnL — worse than random
    "NG=F":  {"name": "Natural Gas", "cat": "commodity", "atr_mult_tp": 3.0, "atr_mult_sl": 2.0, "seasonal_bullish": [10, 11, 12]},
    "HG=F":  {"name": "Copper",      "cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5, "seasonal_bullish": [1, 2, 3]},
    "ZC=F":  {"name": "Corn",        "cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5, "seasonal_bullish": [5, 6, 7]},
    "ZW=F":  {"name": "Wheat",       "cat": "commodity", "atr_mult_tp": 2.5, "atr_mult_sl": 1.5, "seasonal_bullish": [5, 6, 7]},
    "ZS=F":  {"name": "Soybeans",    "cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5, "seasonal_bullish": [5, 6, 7]},
    "ZM=F":  {"name": "Soybean Meal", "cat": "commodity", "atr_mult_tp": 1.5, "atr_mult_sl": 1.0, "seasonal_bullish": [10, 11, 12, 1, 2]},
    "ZL=F":  {"name": "Soybean Oil",  "cat": "commodity", "atr_mult_tp": 1.5, "atr_mult_sl": 1.0, "seasonal_bullish": [10, 11, 12, 1, 2]},
    "KC=F":  {"name": "Coffee",      "cat": "commodity", "atr_mult_tp": 3.0, "atr_mult_sl": 2.0, "seasonal_bullish": [3, 4, 5]},
    "SB=F":  {"name": "Sugar",       "cat": "commodity", "atr_mult_tp": 2.5, "atr_mult_sl": 1.5, "seasonal_bullish": [2, 3, 4]},
    "PL=F":  {"name": "Platinum",    "cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5, "seasonal_bullish": [1, 4]},
    "CT=F":  {"name": "Cotton",      "cat": "commodity", "atr_mult_tp": 2.5, "atr_mult_sl": 2.0, "seasonal_bullish": [3, 4, 5]},
    "CC=F":  {"name": "Cocoa",        "cat": "commodity", "atr_mult_tp": 3.0, "atr_mult_sl": 2.0, "seasonal_bullish": [10, 11, 12]},
    # 2026-04-17: expansion per non-crypto-supply-pipeline-investigation Step 5.
    # Doubles funnel input (12->24). Live ETF proxies provide signal when futures
    # data is flaky on yfinance.
    "BZ=F":  {"name": "Brent Crude",  "cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5},
    "RB=F":  {"name": "RBOB Gasoline","cat": "commodity", "atr_mult_tp": 2.5, "atr_mult_sl": 1.5},
    "HO=F":  {"name": "Heating Oil",  "cat": "commodity", "atr_mult_tp": 2.5, "atr_mult_sl": 1.5},
    "PA=F":  {"name": "Palladium",    "cat": "commodity", "atr_mult_tp": 2.5, "atr_mult_sl": 1.5},
    "LE=F":  {"name": "Live Cattle",  "cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5},
    "GF=F":  {"name": "Feeder Cattle","cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5},
    "HE=F":  {"name": "Lean Hogs",    "cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5},
    "OJ=F":  {"name": "Orange Juice", "cat": "commodity", "atr_mult_tp": 3.0, "atr_mult_sl": 2.0},
    # ETF proxies (more reliable yfinance feed; treated as commodities)
    "USO":   {"name": "US Oil Fund ETF", "cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5},
    "UNG":   {"name": "US NatGas ETF",   "cat": "commodity", "atr_mult_tp": 3.0, "atr_mult_sl": 2.0},
    "DBA":   {"name": "Agricultural ETF","cat": "commodity", "atr_mult_tp": 2.0, "atr_mult_sl": 1.5},
}

# -- Futures (yfinance tickers) --
FUTURES_SYMBOLS: dict[str, dict] = {
    "ES=F":  {"name": "S&P 500 E-mini",   "cat": "futures", "exchange": "CME"},
    "NQ=F":  {"name": "Nasdaq 100 E-mini", "cat": "futures", "exchange": "CME"},
    "YM=F":  {"name": "Dow E-mini",        "cat": "futures", "exchange": "CBOT"},
    # "CL=F" REMOVED: 26 futures trades, 3.8% WR, -29.82% PnL — worse than random
    "GC=F":  {"name": "Gold",              "cat": "futures", "exchange": "COMEX"},
    "SI=F":  {"name": "Silver",            "cat": "futures", "exchange": "COMEX"},
    "ZN=F":  {"name": "10-Year T-Note",    "cat": "futures", "exchange": "CBOT"},
    "ZT=F":  {"name": "2-Year T-Note",     "cat": "futures", "exchange": "CBOT"},
    "RTY=F": {"name": "Russell 2000 E-mini","cat": "futures", "exchange": "CME"},
    "ZB=F":  {"name": "30-Year T-Bond",    "cat": "futures", "exchange": "CBOT"},
    # 2026-04-15: expand FX / macro coverage for post-gate futures strategies
    "6E=F":  {"name": "Euro FX Future",    "cat": "futures", "exchange": "CME"},
    "6B=F":  {"name": "British Pound Future", "cat": "futures", "exchange": "CME"},
    "6J=F":  {"name": "Japanese Yen Future", "cat": "futures", "exchange": "CME"},
    # 2026-04-15: additional CME FX + industrial metal (more signals for ETF/futures agents)
    "6A=F":  {"name": "Australian Dollar Future", "cat": "futures", "exchange": "CME"},
    "6C=F":  {"name": "Canadian Dollar Future", "cat": "futures", "exchange": "CME"},
    "HG=F":  {"name": "Copper",            "cat": "futures", "exchange": "COMEX"},
}

# -- ETF symbols (distinct from EQUITY_SYMBOLS for clarity) --
ETF_SYMBOLS: dict[str, dict] = {
    # Core beta (also in equity watchlists; kept here for ETF-only strategies)
    "SPY":  {"name": "S&P 500 ETF",       "cat": "etf"},
    "QQQ":  {"name": "Nasdaq 100 ETF",    "cat": "etf"},
    "DIA":  {"name": "Dow Jones ETF",     "cat": "etf"},
    "XLK":  {"name": "Technology Select", "cat": "etf"},
    "XLF":  {"name": "Financial Select",  "cat": "etf"},
    "XLE":  {"name": "Energy Select",     "cat": "etf"},
    "XLV":  {"name": "Healthcare Select", "cat": "etf"},
    "GLD":  {"name": "Gold ETF",          "cat": "etf"},
    "SLV":  {"name": "Silver ETF",        "cat": "etf"},
    # TLT moved to BOND_SYMBOLS (bond-specific classification with duration metadata)
    "IWM":  {"name": "Russell 2000",      "cat": "etf"},
    # HYG moved to BOND_SYMBOLS (bond-specific classification with duration metadata)
    # 2026-04-12: expanded ETF universe for sector rotation + more signal coverage
    # Only 9 symbols → 19 symbols. Sector ETFs have clean mean-reversion.
    "XLI":  {"name": "Industrials",      "cat": "etf"},
    "XLB":  {"name": "Materials",        "cat": "etf"},
    "XLU":  {"name": "Utilities",        "cat": "etf"},
    "XLY":  {"name": "Cons. Discretion", "cat": "etf"},
    "XLP":  {"name": "Cons. Staples",    "cat": "etf"},
    "XLC":  {"name": "Communication",    "cat": "etf"},
    "SMH":  {"name": "Semiconductors",   "cat": "etf"},
    "SOXX": {"name": "PHLX Semis",       "cat": "etf"},
    "ARKK": {"name": "ARK Innovation",   "cat": "etf"},
    "KWEB": {"name": "China Internet",   "cat": "etf"},
    # 2026-04-15: broaden ETF book for sector rotation / macro (liquid yfinance names)
    "EEM":  {"name": "Emerging Markets", "cat": "etf"},
    "EFA":  {"name": "EAFE",             "cat": "etf"},
    "VEA":  {"name": "Developed ex-US",  "cat": "etf"},
    "VNQ":  {"name": "US Real Estate",   "cat": "etf"},
    "DBC":  {"name": "Broad Commodities", "cat": "etf"},
    "TIP":  {"name": "TIPS",             "cat": "etf"},
    # 2026-04-15: expand liquid macro/style ETFs (yfinance) for rotation strategies
    "XLRE": {"name": "Real Estate Select", "cat": "etf"},
    "VTI":  {"name": "Total US Stock Mkt", "cat": "etf"},
    "VOO":  {"name": "S&P 500 Vanguard", "cat": "etf"},
    "SCHD": {"name": "US Dividend Equity", "cat": "etf"},
    "USO":  {"name": "US Oil Fund",       "cat": "etf"},
    "MDY":  {"name": "S&P MidCap 400",    "cat": "etf"},
    "IJH":  {"name": "S&P MidCap 400 iShares", "cat": "etf"},
    "IWD":  {"name": "Russell 1000 Value", "cat": "etf"},
    "IWF":  {"name": "Russell 1000 Growth", "cat": "etf"},
    "EWJ":  {"name": "Japan MSCI",        "cat": "etf"},
    "EWZ":  {"name": "Brazil MSCI",       "cat": "etf"},
    # 2026-04-17: ETF universe expansion per supply-pipeline investigation Step 5.
    # Was 37 symbols, now ~50. Extra liquid names = more rotation signal.
    "VTV":  {"name": "Vanguard Value",    "cat": "etf"},
    "VUG":  {"name": "Vanguard Growth",   "cat": "etf"},
    "IXN":  {"name": "Global Tech",       "cat": "etf"},
    "IYR":  {"name": "US Real Estate",    "cat": "etf"},
    "ACWI": {"name": "All-Country World", "cat": "etf"},
    "FXI":  {"name": "China Large-Cap",   "cat": "etf"},
    "INDA": {"name": "India MSCI",        "cat": "etf"},
    # 3x leveraged ETFs removed 2026-05-18: etf_dual_momentum/sector_momentum were
    # picking SOXL/SQQQ/TQQQ — structurally wrong (Antonacci momentum calibrated for
    # non-leveraged ETFs; 3x vol invalidates TP/SL levels; SQQQ SHORT = synthetic
    # Nasdaq long via double-inverse, confusing signal). Re-add only with a dedicated
    # leveraged_etf_decay strategy or explicit short-term mean-reversion scanner.
    # Sector / theme additions
    "ARKG": {"name": "ARK Genomic Rev",   "cat": "etf"},
    "XBI":  {"name": "Biotech",           "cat": "etf"},
    "GDX":  {"name": "Gold Miners",       "cat": "etf"},  # higher beta than GLD
    "GDXJ": {"name": "Junior Gold Miners","cat": "etf"},
    # Vol ETFs removed 2026-05-18 (M-112): VIXY tracks short-term VIX futures —
    # structural mismatch with momentum/trend strategies (negative carry from VIX
    # contango, strong mean-reversion, no trend persistence). ETF_SYMBOLS drives
    # etf_dual_momentum/etf_trend_following — VIX products invalidate those signals.
    # If regime-gate logic needs VIXY, add it to a separate REGIME_GATE_SYMBOLS list.
    # 2026-05-14: Factor ETFs (swarm P1 — academic backing for factor rotation)
    "MTUM": {"name": "iShares Momentum",  "cat": "etf"},
    "QUAL": {"name": "iShares Quality",   "cat": "etf"},
    "VLUE": {"name": "iShares Value Factor", "cat": "etf"},
    "USMV": {"name": "iShares Min Vol",   "cat": "etf"},
    "SIZE": {"name": "iShares Size Factor", "cat": "etf"},
    # International additions (liquid, covered by yfinance)
    "EWT":  {"name": "Taiwan MSCI",       "cat": "etf"},
    "EWY":  {"name": "South Korea MSCI",  "cat": "etf"},
    "EWG":  {"name": "Germany MSCI",      "cat": "etf"},
    "EWH":  {"name": "Hong Kong MSCI",    "cat": "etf"},
    "EWA":  {"name": "Australia MSCI",    "cat": "etf"},
    "EWC":  {"name": "Canada MSCI",       "cat": "etf"},
    "EWU":  {"name": "UK MSCI",           "cat": "etf"},
    # Sector additions
    "XRT":  {"name": "Retail ETF",        "cat": "etf"},
    "XHB":  {"name": "Homebuilders",      "cat": "etf"},
    "KRE":  {"name": "Regional Banks",    "cat": "etf"},
    "KBE":  {"name": "Banking ETF",       "cat": "etf"},
    "XPH":  {"name": "Pharma ETF",        "cat": "etf"},
    "XOP":  {"name": "Oil & Gas Explor",  "cat": "etf"},
    # Thematic ETFs (high signal frequency)
    "ICLN": {"name": "Clean Energy",      "cat": "etf"},
    "BOTZ": {"name": "Robotics & AI",     "cat": "etf"},
    "HACK": {"name": "Cybersecurity",     "cat": "etf"},
    "REMX": {"name": "Rare Earth/Metals", "cat": "etf"},
    "FINX": {"name": "FinTech",           "cat": "etf"},
    "CIBR": {"name": "Cybersecurity 2",   "cat": "etf"},
    "AIQ":  {"name": "AI & Technology",   "cat": "etf"},
    # Dividend / income
    "VYM":  {"name": "Vanguard High Div", "cat": "etf"},
    "DVY":  {"name": "Dow Dividend 100",  "cat": "etf"},
    "NOBL": {"name": "Dividend Aristocrats", "cat": "etf"},
    # Commodity alternatives
    "PDBC": {"name": "Invesco Commodity", "cat": "etf"},
    "GSG":  {"name": "iShares Commodity", "cat": "etf"},
    # Fixed income alternatives (non-BOND class)
    "VCSH": {"name": "Short-Term Corp",   "cat": "etf"},
    "IGIB": {"name": "Interm Corp Bond",  "cat": "etf"},
}

# -- Bond ETF symbols (2026-04-12: new, was missing entirely) --
# Bond strategies in bond_fixed_income_strategies.py reference these but
# had no config dict. futures_momentum was producing bond-tagged picks
# on ZN=F/ZT=F misclassified as BOND. These are actual bond ETFs.
BOND_SYMBOLS: dict[str, dict] = {
    "TLT":  {"name": "20+ Year Treasury",  "cat": "bond", "duration": "long"},
    "IEF":  {"name": "7-10 Year Treasury",  "cat": "bond", "duration": "intermediate"},
    "SHY":  {"name": "1-3 Year Treasury",   "cat": "bond", "duration": "short"},
    "LQD":  {"name": "Inv Grade Corporate", "cat": "bond", "duration": "intermediate"},
    "HYG":  {"name": "High-Yield Corp",     "cat": "bond", "duration": "intermediate"},
    "AGG":  {"name": "US Aggregate Bond",   "cat": "bond", "duration": "intermediate"},
    "BND":  {"name": "Total Bond Market",   "cat": "bond", "duration": "intermediate"},
    "EMB":  {"name": "Emerging Market Bond", "cat": "bond", "duration": "long"},
    # 2026-04-17: BOND universe expansion per supply-pipeline investigation Step 5.
    # Was 8 symbols, now 14. More duration buckets + credit + intl coverage.
    "TLH":  {"name": "10-20 Year Treasury",   "cat": "bond", "duration": "long"},
    "GOVT": {"name": "US Treasury Bond",      "cat": "bond", "duration": "intermediate"},
    "JNK":  {"name": "High-Yield Bond",       "cat": "bond", "duration": "intermediate"},
    "MUB":  {"name": "Muni Bond",             "cat": "bond", "duration": "intermediate"},
    "TIP":  {"name": "TIPS",                  "cat": "bond", "duration": "intermediate"},
    "BNDX": {"name": "International Bond",    "cat": "bond", "duration": "intermediate"},
}

# Per-category risk parameters for futures & ETFs
CATEGORY_RISK["commodity"] = (-0.05, 0.10, 14)  # 5% stop, 10% target, 14 day max hold
CATEGORY_RISK["futures"] = (-0.04, 0.08, 10)   # Moderate SL, decent TP, 10-day hold
CATEGORY_RISK["etf"]     = (-0.05, 0.10, 15)   # Similar to stocks but longer hold

TRAILING_STOP["commodity"] = 0.08
TRAILING_STOP["futures"] = 0.06
TRAILING_STOP["etf"]     = 0.06
CATEGORY_RISK["bond"] = (-0.04, 0.06, 15)   # 4% stop, 6% target, 15 day max hold (low vol)
TRAILING_STOP["bond"]     = 0.04

# Convenience: all symbols flat list
ALL_SYMBOLS: dict[str, dict] = {
    **CRYPTO_SYMBOLS, **FOREX_SYMBOLS, **EQUITY_SYMBOLS,
    **COMMODITY_SYMBOLS, **FUTURES_SYMBOLS, **ETF_SYMBOLS,
    **BOND_SYMBOLS,
}


# ---------------------------------------------------------------------------
# Asset-class detection + per-class risk params (added 2026-04-17)
#
# Cherry-picked from PR #243 with the 4 BLOCKER fixes applied:
#   (a) Added `bond` branch (PR version tagged TLT/TIP as "macro" → wrong risk)
#   (b) Parenthesized the USDT/USD precedence bug (`A or B and C`)
#   (c) Commodity check BEFORE forex (XAUUSD → commodity, not forex)
#   (d) Uses EXISTING symbol universes (BOND_SYMBOLS/COMMODITY_SYMBOLS/ETF_SYMBOLS)
#       instead of shadow hard-coded sets that drift out of sync
#
# Called by polymarket_signals.py, kalshi_signals.py, downstream non-crypto
# consensus to route picks to the right TP/SL calibration from CATEGORY_RISK.
# ---------------------------------------------------------------------------

def detect_asset_class(symbol: str) -> str:
    """Classify a symbol into one of: crypto / bond / commodity / futures /
    etf / forex / equity / unknown. Uses existing symbol universes (not shadow sets).
    """
    if not symbol:
        return "unknown"
    s = str(symbol).upper().strip()

    # 1. Crypto: USDT/USDC/BUSD suffix, or BTC/ETH quote, or the -USD variants
    #    Parens wrap the `or` chain to avoid boolean-precedence bugs.
    if (s.endswith("USDT") or s.endswith("USDC") or s.endswith("BUSD")
            or (s.endswith("USD") and not (len(s) == 6 and s.isalpha()))):
        return "crypto"
    # Catch bare BTC-USD / ETH-USD etc.
    if s.replace("-", "").replace("/", "") in CRYPTO_SYMBOLS:
        return "crypto"

    # 2. Bond BEFORE commodity: TLT/TIP/AGG... (these could otherwise fall to
    #    ETF branch; bond is the more specific tag).
    if s in BOND_SYMBOLS:
        return "bond"

    # 3. Commodity BEFORE forex: XAUUSD is BOTH forex-shaped AND a commodity.
    #    Commodity wins by design (PR #243 had XAUUSD → forex bug).
    if s in COMMODITY_SYMBOLS:
        return "commodity"
    # Precious-metals FX pairs (XAUUSD=gold, XAGUSD=silver, XPTUSD=platinum,
    # XPDUSD=palladium). Shape-matches forex but risk-wise is commodity.
    if s[:3] in ("XAU", "XAG", "XPT", "XPD") and s.endswith("USD"):
        return "commodity"

    # 4. Futures: =F suffix (e.g. ES=F, NQ=F, ZN=F)
    if s.endswith("=F"):
        return "futures"

    # 5. ETF: SPY/QQQ/IWM/etc. Must come before the generic equity fallback.
    if s in ETF_SYMBOLS:
        return "etf"

    # 6. Forex: 6-letter alpha pairs (EURUSD, GBPJPY, AUDNZD), or in FOREX_SYMBOLS.
    if s in FOREX_SYMBOLS or (len(s) == 6 and s.isalpha()):
        return "forex"

    # 7. Equity: single-ticker alpha (AAPL, META, GOOGL, ...)
    if s in EQUITY_SYMBOLS or (1 <= len(s) <= 5 and s.isalpha()):
        return "equity"

    return "unknown"


def get_risk_params(asset_class: str) -> tuple[float, float, int]:
    """Return (stop_pct, target_pct, max_hold_days) for an asset class.

    Fallback chain: exact match → equity. PR #243 mapped commodity→stock,
    macro→equity, no bond entry — we preserve all the dedicated calibrations
    in CATEGORY_RISK without re-routing.
    """
    if not asset_class:
        return CATEGORY_RISK.get("equity", (-0.03, 0.06, 5))
    ac = asset_class.strip().lower()
    # Cross-mapping for PR #243 callers that pass "macro"/"index"/"stock"
    aliases = {"stock": "equity", "index": "etf", "macro": "equity"}
    ac = aliases.get(ac, ac)
    return CATEGORY_RISK.get(ac, CATEGORY_RISK.get("equity", (-0.03, 0.06, 5)))


# ---------------------------------------------------------------------------
# yfinance ticker resolution
# ---------------------------------------------------------------------------
# Many crypto keys (e.g. "RNDR-USD") don't match the actual yfinance ticker
# (e.g. "RENDER-USD").  Symbols with "yf_ticker" use a remapped ticker;
# symbols with "yf_skip" are fetched exclusively via Binance/exchange APIs.
# This helper builds (yf_download_list, yf_to_key_map) so the scanner can:
#   1. Download using the correct yfinance tickers
#   2. Map the returned data back to the canonical dict keys
# ---------------------------------------------------------------------------

def resolve_yf_symbols(symbol_keys: list[str],
                       symbol_defs: dict[str, dict] | None = None,
                       ) -> tuple[list[str], dict[str, str], list[str]]:
    """Resolve canonical symbol keys into actual yfinance tickers.

    Returns:
        yf_tickers:   list of tickers to send to yfinance (excludes yf_skip)
        yf_to_key:    dict mapping yfinance ticker -> canonical key
        binance_only: list of canonical keys that are yf_skip (Binance fallback)
    """
    if symbol_defs is None:
        symbol_defs = ALL_SYMBOLS

    yf_tickers: list[str] = []
    yf_to_key: dict[str, str] = {}
    binance_only: list[str] = []

    for key in symbol_keys:
        meta = symbol_defs.get(key, {})
        if meta.get("yf_skip"):
            binance_only.append(key)
            continue
        yf_t = meta.get("yf_ticker", key)  # default: use the key itself
        yf_tickers.append(yf_t)
        yf_to_key[yf_t] = key

    return yf_tickers, yf_to_key, binance_only


def resolve_single_yf_ticker(symbol: str,
                              symbol_defs: dict[str, dict] | None = None,
                              ) -> str:
    """Resolve a single symbol key to its correct yfinance ticker.

    Handles both canonical keys ("HYPE-USD") and Binance-style ("HYPEUSDT").
    Returns the correct yfinance ticker (e.g. "HYPE32196-USD") or the naive
    "{BASE}-USD" fallback if the symbol isn't in the config.

    Usage:
        from config import resolve_single_yf_ticker
        yf_sym = resolve_single_yf_ticker("HYPE-USD")   # -> "HYPE32196-USD"
        yf_sym = resolve_single_yf_ticker("HYPEUSDT")   # -> "HYPE32196-USD"
        yf_sym = resolve_single_yf_ticker("BTC-USD")    # -> "BTC-USD" (no remap)
    """
    if symbol_defs is None:
        symbol_defs = ALL_SYMBOLS

    # Try direct lookup (canonical key like "HYPE-USD")
    meta = symbol_defs.get(symbol)
    if meta:
        if meta.get("yf_skip"):
            return symbol  # caller should use Binance instead
        return meta.get("yf_ticker", symbol)

    # Try converting Binance-style XXXUSDT to XXX-USD canonical key
    sym = symbol.strip().upper()
    if sym.endswith("USDT"):
        canonical = sym[:-4] + "-USD"  # HYPEUSDT -> HYPE-USD
        meta = symbol_defs.get(canonical)
        if meta:
            if meta.get("yf_skip"):
                return canonical
            return meta.get("yf_ticker", canonical)
        return canonical  # fallback: naive conversion

    return symbol  # pass through unchanged (forex =X, stock, etc.)


# ---------------------------------------------------------------------------
# External API endpoints (public, no auth)
# ---------------------------------------------------------------------------
BINANCE_BASE = "https://api.binance.com"
BINANCE_FUTURES_BASE = "https://fapi.binance.com"
# Fallbacks for geo-restricted environments (GitHub Actions US runners get HTTP 451)
BINANCE_FALLBACK_URLS = [
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",   # Public data API (unrestricted)
    "https://api.binance.us",            # US-legal endpoint
]
BINANCE_FUTURES_FALLBACK_URLS = [
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
]
# Non-Binance fallback APIs for futures data (OI, funding rate, price)
# Critical: Binance fapi is 100% geo-blocked on GitHub Actions US runners
BYBIT_BASE = "https://api.bybit.com"
OKEX_BASE = "https://www.okx.com"
# In CI, prefer non-geo-blocked endpoints first
if os.environ.get("GITHUB_ACTIONS"):
    _preferred = ["https://data-api.binance.vision", "https://api.binance.us"]
    BINANCE_FALLBACK_URLS = _preferred + [u for u in BINANCE_FALLBACK_URLS if u not in _preferred]
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"
FEAR_GREED_URL = "https://api.alternative.me/fng/"

# ── Global CI API flags ──
# Set DISABLE_BINANCE_FUTURES=1 to skip ALL Binance Futures API calls (OI, funding, premium).
# Set DISABLE_BINANCE=1 to skip ALL Binance API calls entirely.
# These are auto-detected from CI environment but can be overridden.
BINANCE_FUTURES_DISABLED = os.environ.get("DISABLE_BINANCE_FUTURES") == "1"
BINANCE_DISABLED = os.environ.get("DISABLE_BINANCE") == "1"

# Auto-detect: if GITHUB_ACTIONS and Binance Futures ping fails, disable futures
if os.environ.get("GITHUB_ACTIONS") and not BINANCE_FUTURES_DISABLED:
    try:
        import urllib.request as _ur
        _ur.urlopen(_ur.Request("https://fapi.binance.com/fapi/v1/ping",
                                headers={"User-Agent": "AlphaEngine/2.0"}), timeout=3)
    except Exception:
        BINANCE_FUTURES_DISABLED = True
        import logging
        logging.getLogger("alpha_engine.config").warning(
            "Binance Futures ping failed — BINANCE_FUTURES_DISABLED=True for this session")

# Consolidated base URL lists for failover iteration
# Every module should use these instead of BINANCE_BASE directly
SPOT_BASES = [BINANCE_BASE] + BINANCE_FALLBACK_URLS
FAPI_BASES = [BINANCE_FUTURES_BASE] + BINANCE_FUTURES_FALLBACK_URLS


_CIRCUIT_BREAKER: dict = {}  # {endpoint_prefix: consecutive_failures}
_CIRCUIT_BREAKER_THRESHOLD = 2  # After 2 consecutive failures, skip remaining calls (was 3 — too slow with 185 symbols)

def fetch_binance_json(path: str, *, futures: bool = False, timeout: int = 10) -> dict | list | None:
    """Fetch JSON from Binance with automatic failover across all mirrors.

    When all Binance endpoints fail (geo-block on GitHub Actions), automatically
    tries Bybit/OKX as non-Binance fallbacks for common futures endpoints:
    - /fapi/v1/ticker/price  → Bybit v5 tickers → CoinGecko spot
    - /fapi/v1/fundingRate   → Bybit v5 fundingRate
    - /fapi/v1/openInterest  → Bybit v5 open-interest

    Circuit breaker: after 3 consecutive failures for the same endpoint type,
    skips all remaining calls to avoid wasting 60+ seconds on a dead API.

    Usage:
        data = fetch_binance_json("/api/v3/ticker/price?symbol=BTCUSDT")
        data = fetch_binance_json("/fapi/v1/premiumIndex", futures=True)
    """
    import urllib.request
    # Global disable flags — skip immediately without any network calls
    if BINANCE_DISABLED:
        return None
    if futures and BINANCE_FUTURES_DISABLED:
        return None
    # Circuit breaker: extract endpoint prefix (e.g., "/fapi/v1/openInterest")
    _ep = path.split("?")[0]
    if _CIRCUIT_BREAKER.get(_ep, 0) >= _CIRCUIT_BREAKER_THRESHOLD:
        return None  # Skip — this endpoint is confirmed dead for this session
    bases = FAPI_BASES if futures else SPOT_BASES
    last_err = None
    for base in bases:
        try:
            url = f"{base}{path}"
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                _CIRCUIT_BREAKER[_ep] = 0  # Reset on success
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                # Rate limited — immediately trip circuit breaker for this endpoint
                _CIRCUIT_BREAKER[_ep] = _CIRCUIT_BREAKER_THRESHOLD
                break
            continue
        except Exception as e:
            last_err = e
            continue

    # All Binance bases failed -- try non-Binance fallbacks for futures data
    if futures:
        result = _futures_fallback(path, timeout=timeout)
        if result is not None:
            _CIRCUIT_BREAKER[_ep] = 0  # Reset on fallback success
            return result

    # Track consecutive failure for circuit breaker
    _CIRCUIT_BREAKER[_ep] = _CIRCUIT_BREAKER.get(_ep, 0) + 1
    import logging
    _fails = _CIRCUIT_BREAKER[_ep]
    if _fails == _CIRCUIT_BREAKER_THRESHOLD:
        logging.getLogger("alpha_engine.config").warning(
            "CIRCUIT BREAKER: %s failed %d times — skipping all future calls this session", _ep, _fails
        )
    elif _fails < _CIRCUIT_BREAKER_THRESHOLD:
        logging.getLogger("alpha_engine.config").warning(
            "All Binance endpoints failed for %s: %s", path, last_err
        )
    return None


def _futures_fallback(path: str, *, timeout: int = 10) -> dict | list | None:
    """Non-Binance fallbacks for common futures API endpoints.

    Translates Binance fapi paths to Bybit/OKX equivalents and normalizes
    the response back to Binance format so callers don't need to change.
    """
    import urllib.request
    import re
    import logging
    _log = logging.getLogger("alpha_engine.config")

    # Parse symbol from query string
    m = re.search(r"symbol=([A-Z0-9]+)", path)
    symbol = m.group(1) if m else None

    # --- /fapi/v1/ticker/price → Bybit v5 tickers → spot fallback ---
    if "/ticker/price" in path and symbol:
        # Try Bybit linear perpetual
        try:
            url = f"{BYBIT_BASE}/v5/market/tickers?category=linear&symbol={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                price = data["result"]["list"][0].get("lastPrice")
                if price:
                    print(f"  [BYBIT FALLBACK] {symbol} price: {price}")
                    return {"symbol": symbol, "price": price}
        except Exception as e:
            _log.debug("Bybit price fallback failed for %s: %s", symbol, e)

        # Try CoinGecko as ultimate fallback (needs symbol mapping)
        _cg_map = {
            "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
            "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
            "AVAXUSDT": "avalanche-2", "LINKUSDT": "chainlink", "DOTUSDT": "polkadot",
            "DOGEUSDT": "dogecoin", "LTCUSDT": "litecoin", "NEARUSDT": "near",
            "SUIUSDT": "sui", "TAOUSDT": "bittensor", "TONUSDT": "the-open-network",
            "TRXUSDT": "tron", "SHIBUSDT": "shiba-inu", "ARBUSDT": "arbitrum",
            "OPUSDT": "optimism", "UNIUSDT": "uniswap", "AAVEUSDT": "aave",
            "PEPEUSDT": "pepe", "APTUSDT": "aptos", "INJUSDT": "injective-protocol",
            "ATOMUSDT": "cosmos", "FILUSDT": "filecoin", "XLMUSDT": "stellar",
            "BCHUSDT": "bitcoin-cash", "ETCUSDT": "ethereum-classic",
            "RENDERUSDT": "render-token", "HBARUSDT": "hedera-hashgraph",
            "CAKEUSDT": "pancakeswap-token", "WIFUSDT": "dogwifcoin",
            "BONKUSDT": "bonk", "FLOKIUSDT": "floki", "STXUSDT": "blockstack",
            "HYPEUSDT": "hyperliquid", "KASUSDT": "kaspa",
            "ONDOUSDT": "ondo-finance", "ICPUSDT": "internet-computer",
        }
        cg_id = _cg_map.get(symbol)
        if cg_id:
            try:
                url = f"{COINGECKO_BASE}/simple/price?ids={cg_id}&vs_currencies=usd"
                req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read())
                price = data.get(cg_id, {}).get("usd")
                if price:
                    print(f"  [COINGECKO FALLBACK] {symbol} price: {price}")
                    return {"symbol": symbol, "price": str(price)}
            except Exception:
                pass

        # Try Binance SPOT as last resort (not geo-blocked as hard)
        for base in SPOT_BASES:
            try:
                url = f"{base}/api/v3/ticker/price?symbol={symbol}"
                req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read())
                if data.get("price"):
                    print(f"  [SPOT FALLBACK] {symbol} price: {data['price']}")
                    return data
            except Exception:
                continue

    # --- /fapi/v1/fundingRate → Bybit v5 ---
    if "/fundingRate" in path and symbol:
        limit_m = re.search(r"limit=(\d+)", path)
        limit = int(limit_m.group(1)) if limit_m else 1
        try:
            url = f"{BYBIT_BASE}/v5/market/funding/history?category=linear&symbol={symbol}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                # Normalize to Binance format: [{symbol, fundingRate, fundingTime}]
                result = []
                for item in data["result"]["list"][:limit]:
                    result.append({
                        "symbol": symbol,
                        "fundingRate": item.get("fundingRate", "0"),
                        "fundingTime": int(item.get("fundingRateTimestamp", 0)),
                    })
                print(f"  [BYBIT FALLBACK] {symbol} fundingRate ({len(result)} entries)")
                return result
        except Exception:
            pass

    # --- /fapi/v1/openInterest → Bybit v5 ---
    if "/openInterest" in path and symbol:
        try:
            url = f"{BYBIT_BASE}/v5/market/open-interest?category=linear&symbol={symbol}&intervalTime=5min&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                oi_val = data["result"]["list"][0].get("openInterest", "0")
                print(f"  [BYBIT FALLBACK] {symbol} openInterest: {oi_val}")
                # Normalize to Binance format
                return {"symbol": symbol, "openInterest": oi_val, "time": int(data["result"]["list"][0].get("timestamp", 0))}
        except Exception:
            pass

    # --- /fapi/v1/premiumIndex → Bybit v5 ---
    if "/premiumIndex" in path:
        try:
            _sym_param = f"&symbol={symbol}" if symbol else ""
            url = f"{BYBIT_BASE}/v5/market/tickers?category=linear{_sym_param}"
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                # Normalize to Binance premiumIndex format
                if symbol:
                    item = data["result"]["list"][0]
                    return {
                        "symbol": symbol,
                        "markPrice": item.get("markPrice", "0"),
                        "indexPrice": item.get("indexPrice", "0"),
                        "lastFundingRate": item.get("fundingRate", "0"),
                        "nextFundingTime": int(item.get("nextFundingTime", 0)),
                    }
                else:
                    return [
                        {
                            "symbol": i.get("symbol", ""),
                            "markPrice": i.get("markPrice", "0"),
                            "indexPrice": i.get("indexPrice", "0"),
                            "lastFundingRate": i.get("fundingRate", "0"),
                            "nextFundingTime": int(i.get("nextFundingTime", 0)),
                        }
                        for i in data["result"]["list"]
                    ]
        except Exception as e:
            _log.debug("Bybit premiumIndex fallback failed: %s", e)

    # No fallback matched or all failed
    if symbol:
        _log.debug("All non-Binance fallbacks also failed for %s (path=%s)", symbol, path)
    return None

# Data storage optimization
# ---------------------------------------------------------------------------
DATA_STORAGE_FORMAT = "parquet"  # Use Parquet for 2-3x scalability
PARQUET_COMPRESSION = "snappy"   # Optimal compression ratio
MAX_BATCH_SIZE = 10000           # Batch processing for large datasets
MAX_MEMORY_USAGE = "2GB"         # Memory limit for feature engineering

# Timeframe configurations
# ---------------------------------------------------------------------------
TIME_FRAMES = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "45m": 2700,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "12h": 43200,
    "1d": 86400,
    "1w": 604800,
    "2w": 1209600,
    "3w": 1814400,
    "1M": 2592000,
}

# Feature engineering optimization
# ---------------------------------------------------------------------------
FEATURE_BATCH_SIZE = 5000       # Batch size for DataFrame operations
MAX_FEATURES = 500              # Maximum features per symbol
LAG_FEATURES = [1, 3, 5, 10, 20, 50, 100, 200]  # Extended lag features
ROLLING_WINDOWS = [5, 10, 20, 50, 100, 200, 500]  # Extended rolling windows

# ---------------------------------------------------------------------------
# yfinance fetch parameters
# ---------------------------------------------------------------------------
YF_PERIOD_DAILY = "1y"     # 252 trading days for 200d SMA
YF_PERIOD_HOURLY = "60d"   # Max for hourly data
YF_INTERVAL_DAILY = "1d"
YF_INTERVAL_HOURLY = "1h"

# ---------------------------------------------------------------------------
# Strategy-specific parameters (tuned per asset signature)
# ---------------------------------------------------------------------------

# BTC-specific: Ichimoku tuned for crypto (traditional: 9/26/52, crypto: 20/60/120/30)
ICHIMOKU_PARAMS = {
    "BTC-USD":  {"tenkan": 20, "kijun": 60, "senkou_b": 120, "displacement": 30},
    "ETH-USD":  {"tenkan": 20, "kijun": 60, "senkou_b": 120, "displacement": 30},
    "default":  {"tenkan": 9,  "kijun": 26, "senkou_b": 52,  "displacement": 26},
}

# Wyckoff accumulation detection
WYCKOFF_PARAMS = {
    "vol_decline_pct": 0.40,     # Volume must decline 40%+ during accumulation
    "range_max_pct": 0.15,       # Price range < 15% during accumulation phase
    "min_accumulation_days": 14, # Minimum days in accumulation
    "spring_drop_pct": -0.03,    # Spring: brief dip below support
    "breakout_vol_mult": 2.0,    # Breakout volume >= 2x average
}

# Smart Money Concepts -- order block / fair value gap
SMC_PARAMS = {
    "ob_lookback": 20,           # Order block search window
    "fvg_min_gap_pct": 0.005,    # Fair value gap minimum size (0.5%)
    "bos_lookback": 10,          # Break of structure lookback
}

# London session breakout (forex)
LONDON_BREAKOUT_PARAMS = {
    "asian_session_start_utc": 0,   # 00:00 UTC
    "asian_session_end_utc": 7,     # 07:00 UTC
    "london_open_utc": 7,           # 07:00 UTC
    "london_close_utc": 16,         # 16:00 UTC
    "breakout_buffer_pct": 0.001,   # 0.1% above/below Asian range
}

# Carry trade
CARRY_PARAMS = {
    "min_yield_diff": 1.5,       # Minimum rate differential (%)
    "momentum_period": 20,       # Days for momentum filter
    "momentum_threshold": 0.0,   # Must have positive momentum
}

# Regime detection
REGIME_PARAMS = {
    "sma_period": 200,           # Long-term trend
    "vol_period": 20,            # Realized volatility window
    "bull_threshold": 0.0,       # Price above 200d SMA = bull
    "high_vol_threshold": 0.25,  # 25% annualized vol = high volatility
}

# ---------------------------------------------------------------------------
# Order Book Imbalance (OBI) injection into ML pipeline
# ---------------------------------------------------------------------------
# When True, OBI scores are fetched and logged but NOT injected into signals
# (shadow mode for 24h validation per Grok's request). Set to False to go live.
OBI_SHADOW_MODE = False  # Flipped to LIVE -- 30% alpha confirmed by 3 sources (Grok, academic, AG)


# ===========================================================================
# Confluence Engine -- Indicator Family Classification
# ===========================================================================
# Each strategy is assigned to ONE family based on its PRIMARY signal type.
# The confluence engine requires 2+ agreeing strategies from DIFFERENT families
# before generating a trade signal, reducing false positives.
#
# Families:
#   momentum   -- RSI, MACD, Connors RSI, StochRSI, cross-sectional momentum
#   trend      -- EMA, Ichimoku, Hull MA, ADX, SMA bounce, moving average systems
#   volume     -- OBV, VWAP, Volume Profile, CMF, MFI, volume-based signals
#   sentiment  -- Fear & Greed, funding rates, social momentum, carry trade
#   on_chain   -- MVRV, hash ribbon, whale flows, stablecoin supply, exchange flows
#   structure  -- S/R, FVG, BOS, Wyckoff, swing failure, chart patterns
#   volatility -- Bollinger, Keltner, ATR, DVOL, squeeze, mean reversion
# ===========================================================================

INDICATOR_FAMILIES = {
    "momentum",
    "trend",
    "volume",
    "sentiment",
    "on_chain",
    "structure",
    "volatility",
    # Extended families — used by carry/regime/MR/community/earnings strategies
    "carry",            # Funding rate carry, cross-exchange basis carry
    "regime",           # Regime sentinel, adaptive regime router
    "mean_reversion",   # Stat-arb, pairs, ratio mean-reversion strategies
    "community",        # Community overlay signals (Myfxbook, LuxAlgo, COT)
    "earnings",         # Earnings post-earnings-announcement drift (PEAD)
    "macro",            # Macro overlays (yield curve, FRED-driven regime)
    "commodity_seasonal",  # Planting/harvest calendars, seasonal commodity bias
}

STRATEGY_FAMILIES: dict[str, str] = {
    # -----------------------------------------------------------------------
    # CRYPTO_STRATEGIES -- core (crypto_strategies.py)
    # -----------------------------------------------------------------------
    "btc_ichimoku_cloud":               "trend",
    "btc_200d_sma_bounce":              "trend",
    "crypto_fear_greed_contrarian":      "sentiment",
    "funding_rate_extreme":             "sentiment",
    "wyckoff_accumulation":             "structure",
    "smart_money_fvg":                  "structure",
    "rsi_hidden_divergence":            "momentum",
    "crypto_breakout_volume":           "volume",
    "stochrsi_oversold_bounce":         "momentum",
    "hurst_mean_reversion":             "volatility",
    "entropy_adaptive_rsi":             "momentum",
    "coingecko_trending_volume":        "volume",
    "altcoin_season_rotation":          "momentum",
    "ape_wisdom_social_momentum":       "sentiment",
    "btc_dominance_reversal":           "sentiment",
    "crypto_weekend_drift":             "volatility",
    "connors_rsi2_crypto":              "momentum",
    "obv_divergence_breakout":          "volume",
    "liquidity_sweep_reversal":         "structure",
    "volume_climax_reversal":           "volume",
    "vwap_sd_mean_reversion":           "volume",
    "cmf_zero_line_cross":              "volume",
    "mfi_smart_money_detection":        "volume",
    # Wave 2 -- Millionaire trader / quant / SMC
    "swing_failure_pattern":            "structure",
    "break_of_structure":               "structure",
    "funding_rate_carry":               "sentiment",
    "oi_funding_squeeze":               "sentiment",
    "liquidation_cascade_bottom":       "structure",
    "cross_sectional_momentum":         "momentum",
    "atr_volatility_breakout":          "volatility",
    "whale_accumulation_detector":      "volume",
    "multi_timeframe_ema_stack":        "trend",
    "rsi_macd_confluence":              "momentum",

    # -----------------------------------------------------------------------
    # Community strategies (community_strategies.py)
    # -----------------------------------------------------------------------
    "community_ema_9_21_rsi_crypto":            "trend",
    "community_bb_squeeze_breakout_crypto":      "volatility",
    "community_rsi_extreme_reversal_crypto":     "momentum",
    "community_vwap_bounce_crypto":             "volume",
    "community_momentum_breakout_volume_crypto": "momentum",
    "community_ict_fvg_selective":              "structure",
    "community_ema_8_21_scalp_forex":           "trend",
    "community_london_breakout_v2_forex":       "volatility",
    "community_forex_zscore_mean_reversion":    "volatility",
    "community_orb_equity":                     "volatility",
    "community_penny_volume_surge":             "volume",
    # FOREX COT positioning reversal (Grok-4 edge-research #5, default-OFF).
    "forex_cot_positioning_reversal":           "community",

    # -----------------------------------------------------------------------
    # Spike predictor (spike_predictor.py)
    # -----------------------------------------------------------------------
    "spike_momentum_ignition":          "momentum",
    "spike_squeeze_breakout":           "volatility",
    "spike_rsi_extreme":                "momentum",
    "spike_volume_explosion":           "volume",
    "spike_macd_divergence":            "momentum",
    "spike_zscore_extreme":             "volatility",

    # -----------------------------------------------------------------------
    # On-chain strategies (onchain_strategies.py)
    # -----------------------------------------------------------------------
    "mvrv_sma_proxy":                   "on_chain",
    "hash_ribbon_buy":                  "on_chain",
    "stablecoin_buying_power":          "on_chain",
    "nvt_overvaluation":                "on_chain",
    "fear_greed_extreme_dca":           "sentiment",
    "cryptopanic_news_sentiment":       "sentiment",
    "sopr_dip_buy_proxy":               "on_chain",
    "onchain_composite_score":          "on_chain",
    "hayes_liquidity_index":            "on_chain",
    "pentoshi_htf_structure":           "trend",
    "funding_rate_arbitrage":           "sentiment",
    "cross_exchange_basis_carry":       "carry",

    # -----------------------------------------------------------------------
    # On-chain strategies — extended (onchain_strategies.py)
    # 2026-04-14: missing family assignments found by confluence test
    # -----------------------------------------------------------------------
    "nupl_zone_signal":                 "on_chain",     # NUPL zone (profit/loss)
    "difficulty_ribbon_signal":         "on_chain",     # Difficulty ribbon compression
    "active_address_momentum":          "on_chain",     # Active address 30d/90d MA
    "crypto_onchain_momentum":          "structure",    # Glassnode MVRV-Z + active addr / exch balance (default-OFF)

    # -----------------------------------------------------------------------
    # Crypto strategies — extended (crypto_strategies.py)
    # 2026-04-14: missing family assignments found by confluence test
    # -----------------------------------------------------------------------
    "cumulative_rsi_signal":            "momentum",     # Cumulative RSI multi-period
    "williams_r_sma_signal":            "momentum",     # Williams %R + SMA filter
    "donchian_breakout_scalp":          "trend",        # Donchian channel breakout
    "funding_rate_scalp":               "sentiment",    # Funding rate extreme scalping

    # -----------------------------------------------------------------------
    # Quant strategies (quant_strategies.py)
    # -----------------------------------------------------------------------
    "tsmom_28d":                        "momentum",
    "cointegrated_pairs":               "volatility",
    "momentum_mean_rev_blend":          "momentum",
    "oi_price_divergence":              "volume",

    # -----------------------------------------------------------------------
    # Event strategies (event_strategies.py)
    # -----------------------------------------------------------------------
    "token_unlock_short":               "sentiment",
    "token_unlock_pressure":            "sentiment",
    "token_unlock_bounce":              "sentiment",
    "liquidation_cascade_buy":          "structure",
    "exchange_netflow_reversal":        "on_chain",
    "btc_dip_recovery":                 "momentum",
    "narrative_rotation":               "sentiment",
    "new_pair_momentum":                "momentum",
    "cross_exchange_spread":            "volatility",
    "momentum_crash_hedge":             "momentum",

    # -----------------------------------------------------------------------
    # Advanced strategies (advanced_strategies.py)
    # -----------------------------------------------------------------------
    "vol_risk_premium":                 "volatility",
    "dynamic_momentum_scaling":         "momentum",
    "goplus_filtered_sniper":           "sentiment",
    "altcoin_dip_amplifier":            "momentum",
    "unlock_scoring_enhanced":          "sentiment",
    "cascade_volume_detector":          "volume",
    "dvol_extreme_buy":                 "volatility",
    "sector_momentum_7d":               "momentum",
    # KIRA-inspired strategies (advanced_strategies.py)
    "fractal_decay":                    "structure",
    "swing_structure":                  "structure",
    "kalman_filter_trend":              "trend",
    "candle_momentum":                  "momentum",
    "cusum_regime":                     "trend",
    # DNA scalp variants (kira_dna_scalp_variants.py)
    "cusum_regime_scalp_alt":           "trend",
    "kalman_scalp_btc":                 "trend",
    "candle_momentum_high_conviction":  "momentum",
    "fractal_decay_penny":              "structure",
    "red_bar_continuation_meme":        "momentum",
    "cusum_regime_scalp_equity":        "trend",

    # -----------------------------------------------------------------------
    # Statistical strategies (statistical_strategies.py)
    # -----------------------------------------------------------------------
    "multi_sigma_reversal":             "volatility",
    "ornstein_uhlenbeck_reversion":     "volatility",
    "variance_ratio_momentum":          "momentum",
    "hurst_regime_adaptive":            "volatility",
    "bollinger_keltner_squeeze_breakout": "volatility",
    "autocorrelation_exploiter":        "volatility",
    "volume_profile_poc_reversion":     "volume",
    "mean_reversion_halflife":          "volatility",
    "cumulative_delta_divergence":      "volume",
    "multi_factor_composite":           "momentum",

    # -----------------------------------------------------------------------
    # Pattern strategies (pattern_strategies.py)
    # -----------------------------------------------------------------------
    "fractal_sr_bounce":                "structure",
    "head_shoulders_detector":          "structure",
    "ascending_triangle_breakout":      "structure",
    "sr_breakout_retest":               "structure",
    "price_level_magnetism":            "structure",
    "pattern_repetition_forecast":      "structure",
    "volume_profile_value_area":        "volume",
    "multi_touch_level_strength":       "structure",
    "failed_breakout_reversal":         "structure",

    # -----------------------------------------------------------------------
    # Cyclical strategies (cyclical_strategies.py)
    # -----------------------------------------------------------------------
    "halving_cycle_position":           "on_chain",
    "monthly_seasonality":              "sentiment",
    "day_of_week_effect":               "sentiment",
    "btc_dominance_rotation":           "sentiment",
    "turn_of_month_effect":             "sentiment",
    "halloween_effect":                 "sentiment",
    "fourier_cycle_detector":           "volatility",
    "price_touch_recurrence":           "structure",
    "markov_zone_transition":           "volatility",
    "m2_liquidity_lag":                 "on_chain",

    # -----------------------------------------------------------------------
    # Experimental strategies (experimental_strategies.py)
    # -----------------------------------------------------------------------
    "adaptive_vr_confluence":           "volatility",
    "macd_rsi_multi_tf":                "momentum",
    "session_range_breakout":           "volatility",
    "sentiment_fear_z_reversal":        "sentiment",

    # -----------------------------------------------------------------------
    # Mercury AI strategies (mercury_ai_strategies.py)
    # -----------------------------------------------------------------------
    "hurst_regime_momentum":            "volatility",
    "lw_vwap_mean_reversion":           "volume",
    "funding_term_structure":           "sentiment",
    "spot_perp_basis_arb":              "volatility",
    "iv_skew_reversion":                "volatility",

    # -----------------------------------------------------------------------
    # NextGen strategies (nextgen_strategies.py)
    # -----------------------------------------------------------------------
    "cointegration_pair_trade":         "volatility",
    "adx_volatility_breakout":          "trend",
    "seasonal_factor_rotation":         "sentiment",
    "multi_factor_equity_rotation":     "momentum",
    "dead_cat_bounce_momentum":         "momentum",
    "market_structure_break":           "structure",
    "volume_acceleration_reversion":    "volume",
    "night_liquidity_drift":            "volatility",
    "spread_of_candles_gap":            "volatility",
    "vix_correlation_divergence":       "sentiment",
    "profit_taking_reentry":            "momentum",
    "bb_rsi_mean_reversion":            "volatility",
    "pi_cycle_regime_gate":             "on_chain",
    "puell_multiple_extreme":           "on_chain",

    # -----------------------------------------------------------------------
    # Cerebrus strategies (cerebrus_strategies.py)
    # -----------------------------------------------------------------------
    "relative_strength_pair_cmr":       "momentum",
    "funding_rate_carry_pro":           "sentiment",
    "mvrv_contrarian_dip":              "on_chain",
    "volume_spike_breakout":            "volume",
    "liquidity_imbalance_reversal":     "structure",
    "stablecoin_dry_powder":            "on_chain",

    # -----------------------------------------------------------------------
    # Untapped strategies (untapped_strategies.py)
    # -----------------------------------------------------------------------
    "max_pain_gravitational":           "structure",
    "put_call_ratio_contrarian":        "sentiment",
    "google_trends_contrarian":         "sentiment",
    "btc_options_expiry_anomaly":       "volatility",
    "turn_of_month_enhanced":           "sentiment",
    "vix_term_structure_signal":        "sentiment",

    # -----------------------------------------------------------------------
    # Market microstructure (market_microstructure_strategies.py)
    # -----------------------------------------------------------------------
    "options_25delta_skew":             "volatility",
    "coinbase_premium_index":           "on_chain",
    "obi_microstructure":               "volume",
    "perpetual_basis_ms":               "volatility",

    # -----------------------------------------------------------------------
    # Order book strategies (orderbook_strategies.py)
    # -----------------------------------------------------------------------
    "order_book_imbalance":             "volume",

    # -----------------------------------------------------------------------
    # VPIN + OFI + LunarCrush (vpin_signal.py, lunarcrush_signal.py)
    # -----------------------------------------------------------------------
    "vpin_informed_flow":               "volume",
    "galaxy_score_momentum":            "sentiment",
    "sentiment_price_divergence":       "sentiment",

    # -----------------------------------------------------------------------
    # DXY Divergence Alpha (crypto_strategies.py, appended after registry)
    # -----------------------------------------------------------------------
    "dxy_divergence_alpha":             "trend",

    # -----------------------------------------------------------------------
    # Opposite Day strategies (opposite_day_strategies.py)
    # -----------------------------------------------------------------------
    "overbought_reversal_short":        "momentum",
    "macro_regime_short_filter":        "trend",
    "crowd_contrarian_timer":           "sentiment",
    "cluster_short_momentum":           "momentum",
    "news_sentiment_contrarian":        "sentiment",

    # -----------------------------------------------------------------------
    # Fast Variants -- relaxed-threshold mutations of proven strategies
    # (fast_variants.py)
    # -----------------------------------------------------------------------
    "fast_rsi2_relaxed":    "momentum",     # Connors RSI-2 < 10 (relaxed from < 5)
    "fast_rsi2_extended":   "momentum",     # RSI-2 < 10 on expanded universe
    "fast_vix_moderate":    "sentiment",    # VIX > 25 (relaxed from > 30) + F&G < 25
    "fast_funding_wide":    "sentiment",    # Funding rate < -0.005% (relaxed)
    "fast_rsi2_aggressive": "momentum",     # RSI-2 < 15, no SMA200, tight TP/SL
    "fast_triple_confirm":  "momentum",     # RSI-2<10 + RSI-5<25 + volume confirm
    "fast_rsi2_short":      "momentum",     # RSI-2 > 90 + below SMA200 = SHORT

    # -----------------------------------------------------------------------
    # FOREX_STRATEGIES -- core (forex_strategies.py)
    # -----------------------------------------------------------------------
    "carry_trade_momentum":             "sentiment",
    "inverse_carry_contrarian":         "carry",  # FOREX Rescue bonus edge (contrarian to carry-trade-momentum)
    "etf_economic_momentum":            "macro",  # PR-J 2026-05-12: FRED ISM+GDP+M2 momentum
    "growth_stock_screener":            "momentum",  # PR-X 2026-05-12: starboi-63 5-stage RS+revenue growth screener
    "forex_mean_reversion_200d":        "trend",
    "jpy_risk_off":                     "sentiment",
    "dxy_correlation_regime":           "trend",
    "forex_bollinger_squeeze":          "volatility",
    "session_momentum_continuation":    "momentum",
    "dxy_rsi_mean_reversion":           "momentum",
    "sunday_night_gap_trade":           "volatility",
    "session_volatility_expansion":     "volatility",
    "forex_tsmom_12m":                  "momentum",
    "forex_logistic_direction":         "momentum",
    "forex_rsi2_mean_reversion":        "momentum",
    "forex_carry_ppp":                  "carry",        # PPP-enhanced carry trade (Kwas et al. 2024)
    "cot_positioning":                  "sentiment",

    # -----------------------------------------------------------------------
    # FOREX strategies — extended (forex_strategies.py / community)
    # 2026-04-14: missing family assignments found by confluence test
    # -----------------------------------------------------------------------
    "orb_breakout":                     "volatility",   # Opening range breakout
    "asian_range_breakout":             "volatility",   # Asian session range breakout
    "ig_contrarian_sentiment":          "sentiment",   # IG retail client positioning contrarian

    # -----------------------------------------------------------------------
    # EQUITY_STRATEGIES -- core (equity_strategies.py)
    # -----------------------------------------------------------------------
    "momentum_factor_12m":              "momentum",
    "penny_volume_breakout":            "volume",
    "meme_social_velocity":             "sentiment",
    "quality_value_composite":          "momentum",
    "intermarket_risk_on":              "sentiment",
    "support_resistance_bounce":        "structure",
    "connors_rsi2_scanner":             "momentum",
    "connors_rsi2_short_scanner":       "momentum",  # MMR P0 short mirror (2026-05-14)
    "triple_rsi_scanner":               "momentum",
    "vix_spike_reversal_scanner":       "sentiment",
    "turn_of_month_scanner":            "sentiment",
    "earnings_gap_reversal_scanner":    "volatility",
    "gap_reversal_tech_stocks":         "volatility",

    # -----------------------------------------------------------------------
    # Proven strategies -- Wave 20 (proven_scanner_strategies.py)
    # Backtested across crypto/equity/futures, prop-firm elite (March 2026)
    # -----------------------------------------------------------------------
    "proven_keltner_squeeze":           "volatility",
    "proven_triple_ema_pullback":       "trend",
    "proven_vwap_mean_reversion":       "volume",
    "proven_inverse_fvg":               "structure",
    "proven_stochrsi_divergence":       "momentum",
    "proven_propfirm_conservative":     "trend",

    # -----------------------------------------------------------------------
    # Survivor strategies (survivor_strategies.py)
    # Backtested survivors: connors_r3 (71% WR), keltner MR (67.3%), bollinger MR (60.6%)
    # -----------------------------------------------------------------------
    "connors_r3_survivor":                  "momentum",
    "keltner_mean_reversion_survivor":      "volatility",
    "bollinger_mean_reversion_survivor":    "volatility",

    # -----------------------------------------------------------------------
    # Cointegration Pairs (cointegration_pairs.py)
    # -----------------------------------------------------------------------
    "cointegration_pair_zscore":             "volatility",
    "cointegration_half_life_trade":         "volatility",

    # -----------------------------------------------------------------------
    # Candlestick Patterns (candlestick_patterns.py)
    # -----------------------------------------------------------------------
    "hammer_reversal":                       "structure",
    "engulfing_reversal":                    "structure",
    "doji_reversal":                         "structure",
    "morning_evening_star":                  "structure",
    "three_white_soldiers_black_crows":      "momentum",

    # -----------------------------------------------------------------------
    # Hoffman Strategy (hoffman_strategy.py)
    # -----------------------------------------------------------------------
    "hoffman_inventory_retracement":         "trend",
    "hoffman_continuation":                  "trend",

    # -----------------------------------------------------------------------
    # Session Breakout (session_breakout.py)
    # -----------------------------------------------------------------------
    "london_session_breakout":               "volatility",
    "ny_session_breakout":                   "volatility",
    "asian_session_breakout":                "volatility",

    # -----------------------------------------------------------------------
    # Range Breakout (range_breakout.py)
    # -----------------------------------------------------------------------
    "consolidation_range_breakout":          "volatility",
    "volatility_contraction_breakout":       "volatility",
    "opening_range_breakout":                "volatility",

    # -----------------------------------------------------------------------
    # Cascade Contrarian (cascade_contrarian.py)
    # -----------------------------------------------------------------------
    "cascade_contrarian":                    "structure",

    # -----------------------------------------------------------------------
    # Hybrid Confluence strategies (hybrid_strategies.py)
    # World-Class Roadmap -- multi-indicator confluence for higher WR
    # -----------------------------------------------------------------------
    "hurst_volume_profile_confluence":       "volume",
    "adaptive_hurst_markov_gated":           "volatility",
    "multi_sigma_ema_stack":                 "volatility",
    "cross_system_regime_arbitrage":         "sentiment",
    "widened_tp_momentum_carry":             "momentum",
    "vwap_rsi_confluence":                   "volume",
    "hoffman_keltner_expansion":             "trend",
    "ai_ema_pullback":                       "trend",
    # Antigravity (Google Gemini) strategies
    "ag_vwap_rsi_institutional":             "volume",
    "ag_liquidation_cascade_contrarian":     "momentum",
    "ag_regime_sentinel_composite":          "regime",
    "ag_rsi_pairs_arbitrage":                "mean_reversion",
    "ag_vt_williams_r_etf":                  "mean_reversion",
    "ag_vt_sector_rs_momentum_etf":          "momentum",
    "ag_vt_btc_eth_ratio_mr_crypto":       "mean_reversion",
    "ag_vt_low_vol_momentum_etf":            "momentum",
    "ag_vt_xle_uso_ratio_mr_etf":           "mean_reversion",
    "ag_vt_iwm_spy_ratio_mr_etf":            "mean_reversion",
    "ag_vt_vix_spike_gld_long_etf":          "volatility",
    "ag_vt_sol_btc_ratio_mr_crypto":        "mean_reversion",
    "ag_vt_thematic_etf_momentum":           "momentum",
    "ag_vt_stat_arb_gdx_slv":               "mean_reversion",
    "ag_vt_pattern_sweep":                  "structure",
    "ag_vt_adx_rsi2_etf":                   "momentum",
    "ag_vt_adx_rsi2_equity":                "momentum",
    "ag_vt_restatement_short": "sentiment",


    # -----------------------------------------------------------------------
    # Bond strategies (bond_strategies.py)
    # -----------------------------------------------------------------------
    "bond_yield_momentum":                  "trend",
    "bond_duration_rotation":               "regime",
    "bond_mean_reversion":                  "mean_reversion",
    "bond_yield_curve_inversion":           "macro",

    # -----------------------------------------------------------------------
    # Commodity strategies (commodities_strategies.py)
    # -----------------------------------------------------------------------
    "seasonal_momentum": "trend",
    "gold_safe_haven": "sentiment",
    "oil_inventory_momentum": "momentum",
    "metals_mean_reversion": "mean_reversion",
    "agricultural_spread": "mean_reversion",
    "energy_momentum_breakout": "trend",
    "commodity_rsi_divergence": "momentum",
    "dxy_inverse_commodities": "sentiment",

    # -----------------------------------------------------------------------
    # Futures strategies (futures_strategies.py)
    # -----------------------------------------------------------------------
    "futures_tsmom": "trend",
    "futures_connors_rsi2": "momentum",
    "futures_cross_asset_momentum": "trend",
    "futures_vol_regime_breakout": "volatility",

    # -----------------------------------------------------------------------
    # ETF strategies (etf_strategies.py)
    # -----------------------------------------------------------------------
    "etf_dual_momentum": "trend",
    "etf_sector_momentum": "trend",
    "etf_risk_parity_rotation": "regime",
    "etf_trend_following": "trend",
    # -----------------------------------------------------------------------
    # CTA Bridge strategies (cta_bridge.py)
    # Academic CTA replicators: TSMOM, Donchian, Golden Cross, FX Multi, etc.
    # -----------------------------------------------------------------------
    "cta_tsmom_blend":                       "momentum",
    "cta_donchian_55":                       "trend",
    "cta_golden_cross":                      "trend",
    "cta_fx_multifactor":                    "momentum",
    "cta_commodity_momentum":                "momentum",
    "cta_cross_asset_tsmom":                 "momentum",

    # -----------------------------------------------------------------------
    # Vibe-Trading baby strategies (baby_strategies/vt_*.py)
    # Backtested via vibe-trading engine, shipped from Mega V4-V10 + swarms
    # -----------------------------------------------------------------------
    "vt_ichimoku_cloud":                     "trend",
    "vt_aroon_trend":                        "trend",
    "vt_hull_ma_commodity":                  "trend",
    "vt_hull_ma_bond":                       "trend",
    "vt_mean_reversion_bond":                "mean_reversion",
    "vt_donchian_gold":                      "trend",
    "vt_rsi_etf_overlay":                    "momentum",
    "vt_bollinger_mr_etf":                   "mean_reversion",
    "vt_bb_volume_mr_etf":                   "mean_reversion",
    "vt_stoch_rsi_etf":                      "momentum",
    "vt_td_sequential":                      "trend",
    "vt_dual_ma_volfilter_etf":              "trend",
    "vt_risk_on_off_etf":                    "sentiment",
    "vt_multi_factor_equity":                "momentum",
    "vt_multi_factor_commodity":             "momentum",
    "vt_mfi_equity":                         "volume",
    "vt_vol_percentile_equity":              "volatility",
    "vt_momentum_factor_equity":             "momentum",
    "vt_keltner_breakout_crypto":            "volatility",
    "vt_mtf_confluence_crypto":              "trend",
    "vt_funding_regime_crypto":              "sentiment",
    "vt_adx_standalone_crypto":              "trend",
    "vt_oi_divergence_commodity":            "volume",
    "vt_oi_divergence_equity":               "volume",
    "vt_oi_divergence_wider_commodity":      "volume",
    "vt_candlestick_commodity":              "structure",
    "vt_adx_rsi2_commodity":                 "momentum",
    "vt_adx_rsi2_etf":                       "momentum",
    "vt_adx_rsi2_equity":                    "momentum",
    "vt_thematic_etf_momentum":              "momentum",
    "vt_ml_rf_commodity":                    "momentum",
    "vt_smc_order_blocks":                   "structure",
    "vt_dxy_trend_fx":                       "trend",
    "vt_levine_adaptive":                    "trend",
    "vt_vix_regime_filter":                  "volatility",
    "vt_adaptive_regime_router":             "trend",
    "vt_myfxbook_sentiment_forex":           "community",
    "vt_cot_positioning":                    "community",
    "vt_earnings_pead":                      "earnings",
    "vt_stat_arb_gdx_slv":                   "mean_reversion",
    "vt_bond_duration_mr":                   "mean_reversion",
    "vt_forex_connors_rsi2":                 "momentum",
    "vt_futures_es_vol_trend":               "trend",
    "vt_edgar_insider_cluster":              "sentiment",
    "vt_restatement_short":                  "sentiment",
    "vt_13f_tier1_new_positions":            "sentiment",
    "vt_sc13d_activist":                     "sentiment",
    "vt_csv_edge_luxalgo_alts":              "community",
    "vt_williams_r_etf":                     "mean_reversion",
    "vt_sector_rs_momentum_etf":             "momentum",
    "vt_btc_eth_ratio_mr_crypto":            "mean_reversion",
    "vt_low_vol_momentum_etf":               "momentum",
    "vt_xle_uso_ratio_mr_etf":               "mean_reversion",
    "vt_iwm_spy_ratio_mr_etf":               "mean_reversion",
    "vt_vix_spike_gld_long_etf":             "volatility",
    "vt_sol_btc_ratio_mr_crypto":            "mean_reversion",

    # -----------------------------------------------------------------------
    # Combined confidence strategy (combined_confidence_strategy.py)
    # Blends copy-trader edge + prediction market probability
    # -----------------------------------------------------------------------
    "combined_confidence":                   "sentiment",

    # -----------------------------------------------------------------------
    # Commodity seasonal (commodity_seasonal.py)
    # Top-1 edge research candidate 2026-05-12 (USDA planting/harvest cycles)
    # -----------------------------------------------------------------------
    "commodity_seasonal_planting_harvest":   "commodity_seasonal",

    # -----------------------------------------------------------------------
    # Cycle 6 discoveries (2026-05-29) — synthetic backtest, 10-seed stability
    # VWAP Bands MR: CRYPTO PF 1.59 / WR 43.9% / n=99 / Sharpe 3.00 / Stab 0.86
    # ADX Range MR:  CRYPTO PF 1.48 / WR 41.5% / n=28 / EQUITY PF 1.42 / n=31
    # Best geometry: Aggressive (TP 2%, SL 1%, hold 10 bars)
    # Ref: reports/CYCLE_6_STRATEGY_HUNT_2026-05-29.md
    # -----------------------------------------------------------------------
    "vwap_bands_mean_reversion":           "mean_reversion",
    "adx_range_mean_reversion":            "mean_reversion",

    # -----------------------------------------------------------------------
    # Cycle 7 discoveries (2026-05-29) — Kalman filter trend extraction
    # Kalman_MR: CRYPTO PF 1.57 / WR 43.7% / n=130 / Sharpe 2.55 / Stab 0.84
    #            EQUITY PF 1.43 / WR 41.4% / n=68  / Sharpe 1.43 / Stab 0.78
    # Best geometry: Aggressive (TP 2%, SL 1%, hold 10 bars)
    # Ref: reports/CYCLE_7_STRATEGY_HUNT_2026-05-29.md
    # -----------------------------------------------------------------------
    "kalman_mean_reversion":               "mean_reversion",

    # -----------------------------------------------------------------------
    # Cycle 9 discoveries (2026-05-29) — Real data walk-forward validation
    # MTF_RSI: ETH PF 2.71 / WR 60.8% / n=33 / 5/5 folds / +24% PnL
    #          BTC PF 2.16 / WR 51.2% / n=33 / 4/5 folds / USD/JPY PF 2.35
    # Best strategy across ETH, BTC, EUR/USD, USD/JPY (real Yahoo Finance data)
    # Ref: reports/CYCLE_9_REAL_DATA_VALIDATION_2026-05-29.md
    # -----------------------------------------------------------------------
    "mtf_rsi_mean_reversion":              "mean_reversion",
}

# ---------------------------------------------------------------------------
# SYMBOL MAPPINGS & BLACKLISTS (v1.3 Fix for Ticker Collision)
# Prevents Starknet (STRK) from being confused with Strike (STRK-USD, $0.03)
# Prevents Aptos (APT) from being confused with Apricot (APT-USD, $0.86)
# ---------------------------------------------------------------------------
SYMBOL_MAP_YAHOO = {
    "STRKUSDT": "STRK1-USD",
    "APTUSDT": "APT2-USD",
}

ZOMBIE_BLACKLIST = {
    "STRK-USD", # Strike (zombie, $0.03)
    "APT-USD",  # Apricot (zombie, $0.86)
}

# ---------------------------------------------------------------------------
# Strategy Track Aliases — canonical name mapping for track record merging
# When the same strategy logic appears under different names in closed vs
# active picks, these aliases ensure track records are merged under the
# canonical name. The dict maps variant_name -> canonical_name.
# Used by production_scanner.py and audit_dashboard/template.html.
# ---------------------------------------------------------------------------
STRATEGY_TRACK_ALIASES: dict[str, str] = {
    # Bollinger Mean Reversion — 3 known variants
    "mean_reversion_bollinger":            "MeanReversionBB",    # multi_asset/scanner.py name
    "bollinger_mean_reversion_survivor":   "MeanReversionBB",    # old survivor name
    "mean_reversion_bb":                  "MeanReversionBB",    # snake_case form
    "meanreversionbb":                    "MeanReversionBB",    # no-sep form

    # Connors RSI2 — scanner variant
    "multi_asset_futures_connors_rsi2":    "connors_rsi2_scanner",  # multi_asset scanner name
    "connors_rsi2":                       "connors_rsi2_scanner",  # short form

    # Forex RSI2 mean reversion — kept separate pending logic audit
    # TODO: confirm whether forex_rsi2_mean_reversion shares the same signal logic as
    # connors_rsi2_scanner before merging track records. Investigate closed-pick history
    # for both names and compare WR/PF before enabling.
    # Tracked in Copilot code review 2026-04-15.
    # Keep LEADERBOARD_STRATEGY_ALIASES (template.html) in sync when enabling.
    # tools/validate_strategy_alias_parity.py enforces Python/JS map equality.
    # "forex_rsi2_mean_reversion": "connors_rsi2_scanner",  # DISABLED pending audit

    # Keltner compression/expansion variants
    "crypto_keltner_compression_expansion_v1": "keltner_compression_expansion",  # versioned -> base
    "hoffman_keltner_expansion":              "keltner_compression_expansion",  # alternate name
}


# ────────────────────────────────────────────────────────────────────────
# Renaissance LDP-Gate hybrid_score — Grok-extracted via scrapling
# (reports/GROK_SHARE_EXTRACTION_2026-05-20T0110Z.md sec 3 fix2)
# Anti-edge fix per NS-2/H-014: confidence is INVERTED in CRYPTO; replace
# raw ml_score with monotonic composite hybrid. Apply behind env-gate so
# rollback is one env var. Pre-registered for harness clearance before
# any production gating.
# ────────────────────────────────────────────────────────────────────────

HYBRID_SCORE_ENABLED = os.environ.get("HYBRID_SCORE_ENABLED", "0") == "1"

# Charter weights (Grok-supplied; sum to 1.0; tuned for "confidence becomes
# monotonic with forward performance"). Override via env vars for sensitivity
# sweeps. All weights non-negative.
HYBRID_W_ML       = float(os.environ.get("HYBRID_W_ML",       "0.55"))
HYBRID_W_REGIME   = float(os.environ.get("HYBRID_W_REGIME",   "0.25"))
HYBRID_W_FRESH    = float(os.environ.get("HYBRID_W_FRESH",    "0.15"))
HYBRID_W_FWD_WR   = float(os.environ.get("HYBRID_W_FWD_WR",   "0.05"))


def hybrid_score(ml_score, regime_factor=1.0, freshness=1.0, forward_wr_30=0.5):
    """Monotonic hybrid score — fixes confidence-inversion anti-edge.

    Composition: w_ml * ml_score + w_regime * regime_factor + w_fresh * freshness
                 + w_fwd * forward_wr_30

    Inputs are expected normalised to [0,1]. ``forward_wr_30`` is the rolling
    30-day win rate observed for the (strategy, asset_class) cell.

    Returns a float; NaN-propagating per López de Prado convention if any
    input is NaN (consistent with anti_overfit_validator BUG-1 fix
    b19d6d6: refuse to floor garbage to 1e-16).

    Source: Grok share bGVnYWN5LWNvcHk_3251982f-f5b3-41e8-846a-999e8d51b78e
    sec 3 fix2; codified verbatim 2026-05-20.
    """
    import math
    for v in (ml_score, regime_factor, freshness, forward_wr_30):
        try:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                return float("nan")
        except Exception:
            return float("nan")
    return (
        HYBRID_W_ML     * float(ml_score)
        + HYBRID_W_REGIME * float(regime_factor)
        + HYBRID_W_FRESH  * float(freshness)
        + HYBRID_W_FWD_WR * float(forward_wr_30)
    )
