"""All paper trading strategies."""
from paper_trading.strategies.defi_tvl_momentum import DefiTvlMomentum
from paper_trading.strategies.fear_greed_contrarian import FearGreedContrarian
from paper_trading.strategies.funding_rate_carry import FundingRateCarry
from paper_trading.strategies.volume_breakout import VolumeBreakout
from paper_trading.strategies.stablecoin_supply import StablecoinSupply
from paper_trading.strategies.exchange_netflow import ExchangeNetflow
from paper_trading.strategies.rsi2_mean_reversion import Rsi2MeanReversion
from paper_trading.strategies.whale_accumulation import WhaleAccumulation
from paper_trading.strategies.cross_exchange_spread import CrossExchangeSpread
from paper_trading.strategies.btc_dominance_rotation import BtcDominanceRotation

# Correlation Strategies (10)
from paper_trading.strategies.corr_trend_strategies import (
    CorrHMATrend, CorrKAMAAdaptive, CorrTripleCrown,
)
from paper_trading.strategies.corr_reversion_strategies import (
    CorrVWAPReversion, CorrZScoreExtreme, CorrEltonNetConsensus,
    CorrRSIMomentum, CorrHMAEltonConfluence, CorrVWAPZScore, CorrKAMARSI,
)

# Leap Contest Strategies (6)
from paper_trading.strategies.leap_strategies import (
    LeapSwingTrailPT, LeapHTFMomentumPT, LeapConcentratedRR_PT,
    LeapHarmonicPT, LeapElliottPT, LeapFeeAwarePT,
)

# Simpleton Trend Reversal (EMA crossover)
from paper_trading.strategies.simpleton_trend_reversal import SimpletonTrendReversal

# Mercury Framework Strategies (6) — InceptionLabs Leap analysis
from paper_trading.strategies.mercury_vol_crossover import MercuryVolCrossover
from paper_trading.strategies.mercury_conservative import MercuryConservative
from paper_trading.strategies.mercury_aggressive import MercuryAggressive
from paper_trading.strategies.simpleton_mercury_hybrid import SimpletonMercuryHybrid
from paper_trading.strategies.mercury_funding_enhanced import MercuryFundingEnhanced
from paper_trading.strategies.mercury_hma_filtered import MercuryHMAFiltered

# Triple Confirmation (Golden Cross + BB + Z-Score) — Kimi Agent Challenge Winners
from paper_trading.strategies.triple_confirmation import TripleConfirmation

# FundedRelay Strategies (8) — Verified from The Leap Feb 2026 (+77.7%)
from paper_trading.strategies.fr_strategies import (
    FRBaseReversalPT, FRMtfAlignedPT, FRLiquidityFilteredPT,
    FRRsiDivergencePT, FRAdxRegimePT, FRPullbackEntryPT,
    FRVolumeSpikePT, FRFullConfluencePT,
)

# Verified Research Strategies (8) — Backtested with documented performance
from paper_trading.strategies.verified_strategies import (
    VerifiedSuperTrendPT, VerifiedWaveTrendPT, VerifiedEMAStackPT,
    VerifiedStochRsiPT, VerifiedKeltnerPT, VerifiedDonchianPT,
    VerifiedWilliamsRPT, VerifiedBTC50MAPT,
)

# Kimi Claw + Academic Strategies (6) — Competition winners + peer-reviewed
from paper_trading.strategies.kimi_strategies import (
    KimiVPINReversionPT, KimiEMA600MomentumPT, KimiLGBMFeatureProxyPT,
    KimiVolMomentumBlendPT, AcademicTSMOMPT, RiskManagedMomentumPT,
    KimiVPINLGBMEnsemblePT,
)

# Gemini Deep Research Championship Strategies (4) — Rob Hoffman, Bellet, Quant League
from paper_trading.strategies.irb_hoffman import IRBHoffman
from paper_trading.strategies.fib_rsi_divergence import FibRSIDivergence
from paper_trading.strategies.protective_momentum import ProtectiveMomentum
from paper_trading.strategies.adaptive_regime_wrapper import AdaptiveIRBHoffman

# Alpha Arena Competition Strategies (6) — Qwen 3 Max + DeepSeek V3.1 winners
from paper_trading.strategies.alpha_arena_strategies import (
    AlphaAggressivePatience_PT, AlphaRiskParity_PT, AlphaFourLayerConfluence_PT,
    AlphaRegimeSwitcher_PT, AlphaDrawdownResponsive_PT, AlphaPartialScaleOut_PT,
)

# Proven Outperformers — Williams %R (81% WR) + Triple RSI (91% WR)
from paper_trading.strategies.williams_r_reversion import WilliamsRReversion
from paper_trading.strategies.triple_rsi_confluence import TripleRSIConfluence

# Generic Volatility Breakout — works on any TF/symbol (BB squeeze + volume + SMA-200)
from paper_trading.strategies.generic_volatility_breakout import GenericVolatilityBreakout

# Incubator Strategies (5) — crypto-only, need to prove themselves
from paper_trading.strategies.incubator_strategies import (
    KeltnerSqueezeBreakout, FundingRateContrarian, StochasticMomentumIndex,
    ADXBreakoutMomentum, MACDHistogramDivergence,
)

# New Mean Reversion Strategies (3) — academic-backed replacements for underperformers
from paper_trading.strategies.williams_percent_r_extreme import WilliamsPercentRExtremePT
from paper_trading.strategies.stochastic_rsi_divergence import StochasticRSIDivergencePT
from paper_trading.strategies.keltner_channel_reversion import KeltnerChannelReversionPT

# Advanced Trend Reversal Emoji (4 timeframes) — incubator multi-TF comparison
from paper_trading.strategies.trend_reversal_emoji import (
    TrendReversalEmoji5m, TrendReversalEmoji15m,
    TrendReversalEmoji1h, TrendReversalEmoji4h,
)

# Variation Strategies (6) — parameter variations of existing strategies, literature-backed
from paper_trading.strategies.variation_strategies import (
    WilliamsR5Reversion, KeltnerTightSqueeze, FastMACDDivergence,
    BB25VolBreakout, FundingContrarian30_70, EMA9_21CrossTrend,
)

# HMA Variation Strategies (4) — Hull Moving Average period + entry experiments
from paper_trading.strategies.hma_variation_strategies import (
    HMA9FastTrend, HMA25SwingTrend, HMACrossover9_25, HMARSIConfluence,
    HMAFullSystem,
)

# Symbol-Catered Strategies (6) — backtest winners per symbol, forward-testing validation
from paper_trading.strategies.catered_symbol_strategies import ALL_CATERED as _CATERED_STRATS

# Hoffman Winning Combos (5) — breakthrough >50% WR from exhaustive combination testing
try:
    from paper_trading.strategies.hoffman_winning_strategies import (
        HoffmanEliteComboPT, HoffmanRSI2RibbonPT, HoffmanVolumeHTFPT,
        HoffmanVolumePowerPT, HoffmanMACDRegimePT,
    )
    _HOFFMAN_WINNING = [
        HoffmanEliteComboPT(),    # 78.9% WR, PF 5.61, Sharpe 14.35
        HoffmanRSI2RibbonPT(),   # 75.0% WR, PF 5.70, Sharpe 14.08
        HoffmanVolumeHTFPT(),    # 53.6% WR, PF 1.59, Sharpe 3.54
        HoffmanVolumePowerPT(),  # 53.2% WR, +92.55% PnL — best money maker
        HoffmanMACDRegimePT(),   # 48.8% WR, 258 trades — reliable workhorse
    ]
except ImportError as _e:
    import logging as _log
    _log.getLogger("paper_trading").warning(f"Hoffman winning combos unavailable: {_e}")
    _HOFFMAN_WINNING = []

# Championship-Winning Strategies (5) — competition winner research
try:
    from paper_trading.strategies.championship_strategies_pt import (
        LiquidationCascadeRecoveryPT, AdaptiveRegimeRouterPT,
        MTFConfluenceSwingPT, VolatilityCompressionBreakoutPT,
        SmartMoneyReversalPT,
    )
    _CHAMPIONSHIP = [
        SmartMoneyReversalPT(),             # 48.6% WR, +66% PnL — best championship
        AdaptiveRegimeRouterPT(),           # 44.4% WR, +38% PnL — regime-aware
        VolatilityCompressionBreakoutPT(),  # 41.3% WR — compression breakout
        MTFConfluenceSwingPT(),             # Hoffman-fixed, all 7 root causes addressed
        LiquidationCascadeRecoveryPT(),     # Crypto-native cascade detection
    ]
except ImportError as _e:
    import logging as _log
    _log.getLogger("paper_trading").warning(f"Championship strategies unavailable: {_e}")
    _CHAMPIONSHIP = []

# Prop Firm Classic Strategies (16) — battle-tested + Justin + J Bravo + Enhanced + Hybrids
try:
    from paper_trading.strategies.prop_firm_classics_pt import (
        OpeningRangeBreakoutPT, TurtleDonchianBreakoutPT, InsideBarBreakoutPT,
        VWAPMeanReversionPT, SessionMomentumPT,
        EMA9CloseCrossoverPT, RSIMultiTimeframeBiasPT, DoubleTweeterPatternPT,
        BravoTripleMAPT, GoGoJuicePT, Bravo9CountExhaustionPT,
        GoGoJuiceEnhancedPT, ConfluencePowerPT,
        VWAPGoGoHybridPT, ExhaustionReversalPT,
    )
    _PROP_CLASSICS = [
        OpeningRangeBreakoutPT(),     # 55-65% WR — session range breakout
        TurtleDonchianBreakoutPT(),   # 36% WR but +0.03% avg — big R:R classic
        InsideBarBreakoutPT(),        # 60-75% WR — consolidation breakout
        VWAPMeanReversionPT(),        # 52.5% WR on 1h — TOP PERFORMER (+159% total)
        SessionMomentumPT(),          # 55-62% WR — high-volume window momentum
        EMA9CloseCrossoverPT(),       # Justin's primary (now w/ regime filter)
        RSIMultiTimeframeBiasPT(),    # Justin's HTF RSI + EMA9
        DoubleTweeterPatternPT(),     # 45.2% WR on 1h — improved from 11% on 15m
        BravoTripleMAPT(),            # 40% WR on 1h — improved from 26% on 15m
        GoGoJuicePT(),                # 53.8% WR — rolling VWAP x EMA20
        Bravo9CountExhaustionPT(),    # 46.7% WR, +1.17% avg PnL — strong R:R
        GoGoJuiceEnhancedPT(),        # GoGo + RSI + proximity trigger
        ConfluencePowerPT(),          # 44.7% WR — 5/5 signals must agree
        VWAPGoGoHybridPT(),           # 48.7% WR, +1.04% avg — VWAP deviation + GoGo
        ExhaustionReversalPT(),       # 60.6% WR, +2.24% avg — 9Count + VWAP reversal
    ]
except ImportError as _e:
    import logging as _log
    _log.getLogger("paper_trading").warning(f"Prop firm classics unavailable: {_e}")
    _PROP_CLASSICS = []

# Hoffman IRB + EMA Angle Strategies (3 hold-time variants) — Coinbase perps
from paper_trading.strategies.hoffman_irb_strategies import (
    HoffmanIRB_1H_PT, HoffmanIRB_2H_PT, HoffmanIRB_4H_PT,
)

# Walk-Forward Elite Strategies (3) — statistically validated via walk-forward pipeline
from paper_trading.strategies.walkforward_elite_strategies import (
    STOBVSupportDivergence, STFearGreedContrarian, STMultiDayMomentum,
)

# H-037 VIX Term Structure Carry — harness-admissible ETF strategy
from paper_trading.strategies.h037_vix_carry import H037VIXCarry

# Hoffman IRB Variations (8) — incubator portfolio (requires pandas)
try:
    from paper_trading.strategies.hoffman_variation_strategies import (
        HoffmanAdaptiveATR_PT, HoffmanKalmanTrend_PT, HoffmanTrailingATR_PT,
        HoffmanMomentumTP_PT, HoffmanKellySized_PT, HoffmanHTFConfluence_PT,
        Hoffman45Degree_PT, HoffmanScalper_PT,
    )
    _HOFFMAN_VARIATIONS_AVAILABLE = True
except ImportError as _e:
    import logging as _log
    _log.getLogger("paper_trading").warning(f"Hoffman variations unavailable: {_e}")
    _HOFFMAN_VARIATIONS_AVAILABLE = False

ALL_STRATEGIES = [
    # Original 10
    DefiTvlMomentum(),
    FearGreedContrarian(),
    FundingRateCarry(),
    VolumeBreakout(),
    StablecoinSupply(),
    ExchangeNetflow(),
    Rsi2MeanReversion(),
    WhaleAccumulation(),
    CrossExchangeSpread(),
    BtcDominanceRotation(),
    # Correlation Strategies (10) — $1,000 each
    CorrHMATrend(),
    CorrKAMAAdaptive(),
    CorrVWAPReversion(),
    CorrEltonNetConsensus(),
    CorrZScoreExtreme(),
    CorrRSIMomentum(),
    CorrHMAEltonConfluence(),
    CorrVWAPZScore(),
    CorrKAMARSI(),
    CorrTripleCrown(),
    # Leap Contest Strategies (6) — $1,000 each
    LeapSwingTrailPT(),
    LeapHTFMomentumPT(),
    LeapConcentratedRR_PT(),
    LeapHarmonicPT(),
    LeapElliottPT(),
    LeapFeeAwarePT(),
    # Simpleton Trend Reversal (EMA crossover)
    SimpletonTrendReversal(),
    # Mercury Framework Strategies (6) — InceptionLabs Leap analysis
    MercuryVolCrossover(),
    MercuryConservative(),
    MercuryAggressive(),
    SimpletonMercuryHybrid(),
    MercuryFundingEnhanced(),
    MercuryHMAFiltered(),
    # Triple Confirmation (Golden Cross + BB + Z-Score) — Kimi Agent Challenge Winners
    TripleConfirmation(),
    # FundedRelay Strategies (8) — Verified from The Leap (+77.7%)
    FRBaseReversalPT(),
    FRMtfAlignedPT(),
    FRLiquidityFilteredPT(),
    FRRsiDivergencePT(),
    FRAdxRegimePT(),
    FRPullbackEntryPT(),
    FRVolumeSpikePT(),
    FRFullConfluencePT(),
    # Verified Research Strategies (8) — documented backtest performance
    VerifiedSuperTrendPT(),
    VerifiedWaveTrendPT(),
    VerifiedEMAStackPT(),
    VerifiedStochRsiPT(),
    VerifiedKeltnerPT(),
    VerifiedDonchianPT(),
    VerifiedWilliamsRPT(),
    VerifiedBTC50MAPT(),
    # Kimi Claw + Academic Strategies (6)
    KimiVPINReversionPT(),
    KimiEMA600MomentumPT(),
    KimiLGBMFeatureProxyPT(),
    KimiVolMomentumBlendPT(),
    AcademicTSMOMPT(),
    RiskManagedMomentumPT(),
    # VPIN + LightGBM Ensemble (per-symbol configs from Kimi Claw workspace)
    KimiVPINLGBMEnsemblePT(),
    # Gemini Deep Research Championship Strategies (4) — Hoffman, Bellet, Quant League
    IRBHoffman(),
    FibRSIDivergence(),
    ProtectiveMomentum(),
    AdaptiveIRBHoffman(),
    # Alpha Arena Competition Strategies (6) — Qwen 3 Max + DeepSeek V3.1
    AlphaAggressivePatience_PT(),
    AlphaRiskParity_PT(),
    AlphaFourLayerConfluence_PT(),
    AlphaRegimeSwitcher_PT(),
    AlphaDrawdownResponsive_PT(),
    AlphaPartialScaleOut_PT(),
    # Proven Outperformers — beat Hoffman IRB on documented metrics
    WilliamsRReversion(),     # 81% WR, Sharpe 2.9, PF 3.2
    TripleRSIConfluence(),    # 91% WR, PF 5.0 (fires rarely, almost always wins)
    # Generic Volatility Breakout — BB squeeze + volume + SMA-200
    GenericVolatilityBreakout(),   # ~72-78% WR, Sharpe 1.8-2.2
    # Hoffman IRB + EMA Angle (3 hold-time variants) — Coinbase perps
    HoffmanIRB_1H_PT(),
    HoffmanIRB_2H_PT(),
    HoffmanIRB_4H_PT(),
] + ([
    # Hoffman IRB Variations (8) — incubator portfolio
    HoffmanAdaptiveATR_PT(),
    HoffmanKalmanTrend_PT(),
    HoffmanTrailingATR_PT(),
    HoffmanMomentumTP_PT(),
    HoffmanKellySized_PT(),
    HoffmanHTFConfluence_PT(),
    Hoffman45Degree_PT(),
    HoffmanScalper_PT(),
] if _HOFFMAN_VARIATIONS_AVAILABLE else []) + [
    # Incubator Strategies (5) — crypto-only, must prove 55%+ WR to graduate
    KeltnerSqueezeBreakout(),
    FundingRateContrarian(),
    StochasticMomentumIndex(),
    ADXBreakoutMomentum(),
    MACDHistogramDivergence(),
    # New Mean Reversion Strategies (3) — academic-backed, target 58-68% WR
    WilliamsPercentRExtremePT(),    # Williams %R extreme + volume — Williams (1973)
    StochasticRSIDivergencePT(),    # StochRSI crossover in extremes — Chande & Kroll (1994)
    KeltnerChannelReversionPT(),    # Keltner band touch + RSI — Raschke & Connors (1996)
    # Advanced Trend Reversal Emoji (4 TFs) — multi-timeframe incubator comparison
    TrendReversalEmoji5m(),     # 5m — higher frequency, capped at 3 picks
    TrendReversalEmoji15m(),    # 15m — optimal per Hsu & Kuan (2005)
    TrendReversalEmoji1h(),     # 1h — standard timeframe
    TrendReversalEmoji4h(),     # 4h — swing trading
    # Variation Strategies (6) — parameter variations backed by academic literature
    WilliamsR5Reversion(),       # %R(5) per QuantifiedStrategies — faster than period=14
    KeltnerTightSqueeze(),       # 1.5x ATR per Raschke & Connors (1996) original spec
    FastMACDDivergence(),        # MACD(8/17/9) per Bernstein — 40% faster signals
    BB25VolBreakout(),           # BB 2.5 std per Bollinger (2001) — for volatile instruments
    FundingContrarian30_70(),    # RSI 30/70 per Wilder (1978) — stricter thresholds
    EMA9_21CrossTrend(),         # 9/21 cross per Brock et al. (1992) — scalping cross
    # HMA Variation Strategies (4) — Hull Moving Average experiments
    HMA9FastTrend(),             # HMA(9) fast scalping — high frequency
    HMA25SwingTrend(),           # HMA(25) swing — smoother, larger moves
    HMACrossover9_25(),          # HMA(9) x HMA(25) — zero-lag crossover
    HMARSIConfluence(),          # HMA(16) + RSI(14) — quality confluence
    HMAFullSystem(),             # HMA(9) + ADX + RSI + ATR + volume — Sharpe >1.6 target
    # Walk-Forward Elite Strategies (3) — CI-validated, highest statistical confidence
    STOBVSupportDivergence(),     # 68.3% WR, PF 4.75, n=101, Sharpe 9.85
    STFearGreedContrarian(),      # 58.1% WR, PF 2.50, n=344, Sharpe 5.51
    STMultiDayMomentum(),         # 62.7% WR, PF 3.84, n=75, Sharpe 8.32
    # H-037 VIX Term Structure Carry — harness-admissible ETF strategy
    H037VIXCarry(),               # 58.9% WR, PF 1.295, n=1185, eff=0.75
] + _CATERED_STRATS + _HOFFMAN_WINNING + _CHAMPIONSHIP + _PROP_CLASSICS  # Symbol-Catered + Winning combos + Championship + Prop Firm Classics

# Map strategy name -> portfolio type
STRATEGY_PORTFOLIO_MAP = {s.name: s.portfolio_type for s in ALL_STRATEGIES}


def _get_system_name(strategy) -> str:
    """Get the parent system name for a strategy."""
    name = strategy.name.lower()
    if name.startswith("corr_"):
        return "Correlation Engine"
    if name.startswith("leap_"):
        return "Leap Contest Framework"
    if name.startswith("fr_"):
        return "FundedRelay (The Leap +77.7%)"
    if name.startswith("verified_"):
        return "Verified Research Lab"
    if name.startswith("kimi_") or name.startswith("academic_") or name.startswith("risk_managed"):
        return "Kimi Claw + Academic"
    if name.startswith("mercury_") or name.startswith("simpleton"):
        return "Mercury Framework"
    if name == "triple_confirmation":
        return "Triple Confirmation"
    if name.startswith("alpha_"):
        return "Alpha Arena (Qwen3+DeepSeek)"
    if name in ("williams_r_reversion", "triple_rsi_confluence", "generic_volatility_breakout"):
        return "Proven Outperformers (Research-Backed)"
    if name in ("williams_pct_r_extreme", "stoch_rsi_divergence", "keltner_channel_reversion"):
        return "New Mean Reversion Lab"
    if name.startswith("catered_"):
        return "Symbol-Catered (Backtest Winners)"
    if name.startswith("incub_"):
        return "Incubator (Proving Ground)"
    if name.startswith("trend_reversal_emoji"):
        return "Trend Reversal Emoji (Multi-TF Incubator)"
    if name.startswith("var_"):
        return "Variation Lab (Literature-Backed)"
    if name in ("hoffman_elite_combo", "hoffman_rsi2_ribbon", "hoffman_volume_htf",
                 "hoffman_volume_power", "hoffman_macd_regime"):
        return "Hoffman Winning Combos (>50% WR)"
    if name in ("liquidation_cascade_recovery", "adaptive_regime_router",
                 "mtf_confluence_swing", "volatility_compression_breakout",
                 "smart_money_reversal"):
        return "Championship Strategies (Competition Winners)"
    if name.startswith("prop_"):
        if "bravo" in name or "gogo" in name:
            return "Prop Firm Classics (J Bravo / ChartPrime)"
        if "justin" in name:
            return "Prop Firm Classics (Justin's Methods)"
        return "Prop Firm Classics (Battle-Tested)"
    if name in ("st_obv_support_divergence", "st_fear_greed_contrarian", "st_multi_day_momentum"):
        return "Walk-Forward Elite (CI-Validated)"
    if name == "h037_vix_carry":
        return "H-037 VIX Term Structure Carry (Harness-Admissible)"
    if "hoffman" in name or "irb" in name:
        return "Hoffman IRB System"
    # Original 10 core strategies
    return "Paper Trading Core"


def _get_dashboard_url(strategy) -> str:
    """Get dashboard URL for the strategy's parent system."""
    name = strategy.name.lower()
    if name.startswith("kimi_") or name.startswith("academic_"):
        return "https://findtorontoevents.ca/riseoftheclaw.html"
    if name.startswith("alpha_"):
        return "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/"
    if "hoffman" in name or "irb" in name:
        return "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/"
    if name.startswith("mercury_") or name.startswith("simpleton"):
        return "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/"
    # Default monitor dashboard
    return "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/monitor/"


# Strategy metadata registry -- maps strategy.name to rich metadata
# Used by scanner, mysql_sync, and Discord reporters for proper display names
STRATEGY_METADATA = {}
for _s in ALL_STRATEGIES:
    STRATEGY_METADATA[_s.name] = {
        "display_name": _s.display_name,
        "source": getattr(_s, "source", "Binance"),
        "category": _s.category,
        "portfolio_type": _s.portfolio_type,
        "system_name": _get_system_name(_s),
        "dashboard_url": _get_dashboard_url(_s),
    }
