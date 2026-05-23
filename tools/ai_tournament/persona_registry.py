"""
Persona Registry — canonical source of truth for tournament personas.

Each persona documents: strategy philosophy, entry criteria, risk/reward,
suggested backtesting protocol, confidence calibration, and market conditions.

This file is the DB-independent canonical source. The pipeline syncs it to MySQL.
"""
from __future__ import annotations

from typing import Any

PERSONA_REGISTRY: dict[str, dict[str, Any]] = {
    # ═══════════════════════════════════════════════════════════════════
    # CORE TECHNICAL PERSONAS
    # ═══════════════════════════════════════════════════════════════════
    "momentum_scalp": {
        "display_name": "Momentum Scalper",
        "strategy_family": "technical_momentum",
        "philosophy": "Captures short-term price acceleration following volume-confirmed breakouts. Enters on the first pullback after the initial surge, targeting the next liquidity pocket.",
        "entry_criteria": [
            "Price above VWAP with >1.5x average volume in the last 3 candles",
            "RSI(14) between 50-70 and rising — not overbought but gaining steam",
            "Recent candle closed above prior swing high with wide range",
            "Bid/ask imbalance > 60% on the entry side (Level 2 confirmation)",
        ],
        "exit_criteria": [
            "Trailing stop at 2x ATR(14) from peak",
            "Profit target at prior resistance level or 1.5x initial risk",
            "Exit if volume drops below 50% of entry candle within 3 periods",
        ],
        "risk_reward_target": "1.5 to 2.5",
        "max_risk_per_trade_pct": 1.0,
        "suggested_backtesting_protocol": "Walk-forward on 6-month windows with 1-month out-of-sample. Minimum 50 trades per window. Use 15min-1h data. Filter out low-liquidity periods.",
        "confidence_calibration": "High confidence when volume > 2x avg + RSI rising through 55. Low confidence when volume confirms but price stalls at prior resistance.",
        "best_market_conditions": ["Trending markets with clear directional bias", "High-volume sessions (NYSE open, London open)", "Post-news/earnings momentum continuation"],
        "worst_market_conditions": ["Sideways/choppy price action", "Low-volatility summer doldrums", "Immediately before major macro events"],
        "min_historical_trades": 100,
    },
    "trend_follower": {
        "display_name": "Trend Follower",
        "strategy_family": "technical_trend",
        "philosophy": "Rides established trends identified through multi-timeframe moving average alignment. Buys pullbacks in uptrends, sells rallies in downtrends. Let winners run with trailing stops.",
        "entry_criteria": [
            "20 EMA above 50 EMA and 50 EMA above 200 EMA (bullish alignment)",
            "ADX > 25 (trending) with +DI above -DI",
            "Price pulled back to 20 EMA with declining volume (lack of selling pressure)",
            "Previous higher low confirmed prior to entry",
        ],
        "exit_criteria": [
            "Trailing stop at 3x ATR or below the most recent higher low",
            "Exit if 20 EMA crosses below 50 EMA",
            "Partial profits at 2:1 reward-to-risk, remainder trails",
        ],
        "risk_reward_target": "2.0 to 4.0",
        "max_risk_per_trade_pct": 1.5,
        "suggested_backtesting_protocol": "Rolling 12-month windows, 3-month OOS. Use daily data. Require ADX>25 at entry. Track max adverse excursion for stop placement validation.",
        "confidence_calibration": "High with bullish alignment across all 3 timeframes + ADX>30. Low when alignment exists but price overextended from 20 EMA (>2 ATR).",
        "best_market_conditions": ["Strong directional trends", "Markets with low correlation to broad index", "Post-trend establishment following consolidation breakout"],
        "worst_market_conditions": ["Ranging markets with frequent false breakouts", "Volatile reversals after extended moves", "News-driven spike and reversal days"],
        "min_historical_trades": 80,
    },
    "mean_reversion": {
        "display_name": "Mean Reversion Trader",
        "strategy_family": "technical_mean_reversion",
        "philosophy": "Takes counter-trend positions when price has deviated statistically from its mean. Relies on the tendency of prices to revert to moving averages after statistically significant moves.",
        "entry_criteria": [
            "RSI(14) below 25 or above 75 (oversold/overbought extreme)",
            "Price 2+ standard deviations from 20-period SMA (Bollinger Band touch)",
            "Bearish/bullish exhaustion candle on the extreme touch",
            "Volume declining as price moves further from mean (exhaustion)",
        ],
        "exit_criteria": [
            "Target at 20-period SMA (first target) and opposite Bollinger Band (second)",
            "Stop loss beyond the extreme (outside Bollinger Band by 0.5 ATR)",
            "Exit if RSI recovers above 40 (for longs) or below 60 (for shorts)",
        ],
        "risk_reward_target": "1.0 to 2.0",
        "max_risk_per_trade_pct": 1.0,
        "suggested_backtesting_protocol": "Require full Bollinger Band touch with volume divergence. Exit at middle band minimum. Track reversion speed to calibrate hold time.",
        "confidence_calibration": "High when multiple timeframe extremes align. Low when only single-timeframe overextended.",
        "best_market_conditions": ["Ranging markets with clear support/resistance", "Post-volatility expansion settling into mean", "Mean-reverting asset classes (forex, bonds)"],
        "worst_market_conditions": ["Strong trending markets", "Markets with momentum-driven participants", "Gap openings with no opportunity to enter at extreme"],
        "min_historical_trades": 120,
    },
    "breakout_scanner": {
        "display_name": "Breakout Scanner",
        "strategy_family": "technical_breakout",
        "philosophy": "Identifies and enters on breakouts from established consolidation patterns with volume confirmation. Targets the measured move based on the consolidation width.",
        "entry_criteria": [
            "Price breaking above/below 20-day consolidation range with >1.5x avg volume",
            "Consolidation period minimum 10 bars (longer consolidation = stronger breakout)",
            "Bollinger Bands narrowing then expanding on the breakout candle",
            "No conflicting divergence on RSI or MACD",
        ],
        "exit_criteria": [
            "First target: measured move (= consolidation height from breakout level)",
            "Second target: 1.618x measured move",
            "Stop loss at the far side of the consolidation range",
        ],
        "risk_reward_target": "2.0 to 3.0",
        "max_risk_per_trade_pct": 1.5,
        "suggested_backtesting_protocol": "Test false breakouts vs true breakouts using volume filter. Compare consolidation length vs. breakout success rate. Optimize volume threshold per asset.",
        "confidence_calibration": "High when volume > 2x avg, consolidation > 20 bars, and sector/market confirmation. Low when volume barely exceeds average.",
        "best_market_conditions": ["Post-consolidation directional moves", "Low-volatility compression releasing into high volatility", "Sector-wide breakout coordination"],
        "worst_market_conditions": ["Fakeout-prone markets (low liquidity)", "Overhead resistance in downtrends", "News-driven breakouts that reverse same day"],
        "min_historical_trades": 100,
    },
    # ═══════════════════════════════════════════════════════════════════
    # MACRO / FUNDAMENTAL PERSONAS
    # ═══════════════════════════════════════════════════════════════════
    "cycle_rotator": {
        "display_name": "Cycle Rotator",
        "strategy_family": "macro_cycle",
        "philosophy": "Positions portfolios along the economic cycle — early cycle (cyclicals, consumer discretionary), mid cycle (industrials, tech), late cycle (defensives, energy), recession (bonds, gold). Uses ISM, credit spreads, and yield curve as regime indicators.",
        "entry_criteria": [
            "ISM Manufacturing trending above/below 50 signals expansion/contraction regime",
            "Credit spreads (IG/HY OAS) compressing = risk-on, widening = risk-off",
            "Yield curve slope (2s10s) indicating accommodation or restriction",
            "Leading Economic Index (LEI) showing inflection from prior regime",
        ],
        "exit_criteria": [
            "Rotate out of cyclical holdings when ISM peaks and starts declining",
            "Reduce equity exposure when credit spreads widen 20%+ in a month",
            "Add duration when yield curve begins steepening from inversion",
        ],
        "risk_reward_target": "N/A (sector rotation — portfolio-level)",
        "max_risk_per_trade_pct": "N/A",
        "suggested_backtesting_protocol": "Test monthly signals vs. 3-month hold periods. Compare ISM-based rotation vs. simple buy-and-hold for each phase. Minimum 3 full economic cycles.",
        "confidence_calibration": "High when ISM, credit spreads, and yield curve all confirm same regime. Low when indicators conflict.",
        "best_market_conditions": ["Clear economic expansion/contraction phases", "Post-recession recovery with policy accommodation", "Late-cycle overheating with commodity demand"],
        "worst_market_conditions": ["Transitional regimes where indicators conflict", "Policy-driven markets disconnected from fundamentals", "Black swan events bypassing normal cycle progression"],
        "min_historical_trades": "Portfolio-level rotation, not individual trades",
    },
    "value_investor": {
        "display_name": "Value Investor",
        "strategy_family": "fundamental_value",
        "philosophy": "Identifies securities trading below their intrinsic value using fundamental metrics. Seeks companies with strong balance sheets, sustainable competitive advantages, and reasonable valuations relative to earnings power.",
        "entry_criteria": [
            "P/E ratio below sector median by at least 20%",
            "P/B below 1.5 with ROE > 12% (quality at discount)",
            "Free cash flow yield > 5% (owner earnings check)",
            "Debt/equity ratio below industry average",
        ],
        "exit_criteria": [
            "Price reaches intrinsic value estimate (DCF or comparable analysis)",
            "Fundamental thesis breaks (earnings deterioration, debt increase)",
            "More attractive opportunity identified (portfolio turnover)",
        ],
        "risk_reward_target": "1.5 to 3.0 (value realization may take 6-18 months)",
        "max_risk_per_trade_pct": 5.0,
        "suggested_backtesting_protocol": "Quarterly rebalancing with rolling 5-year windows. Compare value factor performance across market regimes. Test different value metrics (E/P, CF/P, B/P) independently.",
        "confidence_calibration": "High when multiple value metrics align + insider buying + low institutional ownership. Low when stock is cheap for structural reasons (industry decline, technological disruption).",
        "best_market_conditions": ["Post-recession recoveries", "Factor rotation favoring value over growth", "Periods of mean reversion after growth stock outperformance"],
        "worst_market_conditions": ["Extended low-interest-rate environments favoring growth", "Technological disruption making historical valuation metrics less relevant", "Market concentration in momentum/growth factors"],
        "min_historical_trades": 50,
    },
    "moat_measurer": {
        "display_name": "Moat Measurer",
        "strategy_family": "fundamental_quality",
        "philosophy": "Identifies companies with durable competitive advantages — intangible assets (brands, patents), switching costs, network effects, cost advantages, and efficient scale. Prefers to buy at reasonable valuations.",
        "entry_criteria": [
            "ROIC consistently above WACC by 600+ basis points (moat evidence)",
            "Gross margin stable or expanding over 5 years (pricing power)",
            "Customer retention above 90% (switching cost evidence)",
            "Free cash flow conversion above 80% of net income",
        ],
        "exit_criteria": [
            "Moat erosion confirmed (margin compression, market share loss)",
            "Valuation exceeds 3x intrinsic estimate (excessive premium)",
            "Capital allocation deterioration (value-destructive acquisitions)",
        ],
        "risk_reward_target": "1.0 to 2.0 (long-term compounding, not trade-oriented)",
        "max_risk_per_trade_pct": 5.0,
        "suggested_backtesting_protocol": "Compare ROIC-based portfolio vs. broad market. Test different moat duration estimates. Minimum 5-year holding periods per signal.",
        "confidence_calibration": "High when ROIC > WACC by 1000+ bps, revenue visibility > 3 years, and management has proven capital allocator track record.",
        "best_market_conditions": ["Stable competitive landscapes", "Regulatory environments protecting incumbents", "Inflationary periods where pricing power compounds"],
        "worst_market_conditions": ["Rapid technological disruption making moats irrelevant", "Regulatory attacks on incumbent advantages", "Hyper-competitive markets with low barriers to entry"],
        "min_historical_trades": 30,
    },
    # ═══════════════════════════════════════════════════════════════════
    # EVENT / CATALYST PERSONAS
    # ═══════════════════════════════════════════════════════════════════
    "catalyst_sniper": {
        "display_name": "Catalyst Sniper",
        "strategy_family": "event_catalyst",
        "philosophy": "Targets asymmetric payoff opportunities around identifiable catalysts — earnings releases, FDA decisions, regulatory rulings, product launches. Exploits mispriced implied volatility vs. realized outcomes.",
        "entry_criteria": [
            "Identifiable catalyst with specific date window (earnings, FDA, regulatory)",
            "Implied move (options market) underpricing historical realized move by 20%+",
            "Positive drift bias in pre-catalyst period (for event-driven longs)",
            "Insider buying or institutional accumulation ahead of catalyst",
        ],
        "exit_criteria": [
            "Exit immediately post-catalyst (capture event-driven move)",
            "Trailing stop if catalyst delayed (limit drawdown on extended holds)",
            "Full exit if thesis invalidated before catalyst date",
        ],
        "risk_reward_target": "2.0 to 5.0 (asymmetry from mispriced event risk)",
        "max_risk_per_trade_pct": 2.0,
        "suggested_backtesting_protocol": "Compare implied vs. realized moves for each catalyst type. Test entry timing (T-5, T-1, T+0). Exclude gap-filled data. Minimum 200 events per catalyst type.",
        "confidence_calibration": "High when implied move < historical average, position sizing < 5% of ADV, catalyst is binary and date-certain. Low when multiple catalysts in same week causing noise.",
        "best_market_conditions": ["Predictable event calendar (earnings seasons, FDA cycles)", "Low VIX environment where options are cheap", "High institutional attention on the specific catalyst"],
        "worst_market_conditions": ["Event crowded with consensus expectations", "Multiple competing catalysts clouding the signal", "Macro-driven markets overriding stock-specific catalysts"],
        "min_historical_trades": 200,
    },
    # ═══════════════════════════════════════════════════════════════════
    # QUANTITATIVE / ML PERSONAS
    # ═══════════════════════════════════════════════════════════════════
    "signal_miner": {
        "display_name": "Signal Miner",
        "strategy_family": "quant_statistical",
        "philosophy": "Extracts statistically significant patterns from market data using mathematical modeling. Combines multiple weak signals into a strong composite score. Emphasizes regime detection and signal decay monitoring.",
        "entry_criteria": [
            "Composite alpha score above 2nd standard deviation from mean",
            "Factor crowding measure (HHI) below 90th percentile (not a crowded trade)",
            "Cross-asset correlation regime confirming the signal direction",
            "Signal persistence check — score has remained above threshold for 3+ periods",
        ],
        "exit_criteria": [
            "Exit when alpha score drops below 1st standard deviation",
            "Stop loss at 2x expected volatility (volatility-adjusted stop)",
            "Forced exit if regime detection flips (correlation structure changes)",
        ],
        "risk_reward_target": "1.5 to 2.5",
        "max_risk_per_trade_pct": 1.0,
        "suggested_backtesting_protocol": "Ensure proper train/test split (no lookahead). Walk-forward optimization with 24-month train, 6-month test. Track signal decay rate. Purged cross-validation to avoid leakage.",
        "confidence_calibration": "High when signal is near 3-sigma, factor not crowded, and regime confirms. Low when signal is weak or conflicting across independent model ensembles.",
        "best_market_conditions": ["Stable correlation regimes", "Environments where historical patterns repeat", "Periods of factor mean reversion"],
        "worst_market_conditions": ["Regime changes breaking historical correlations", "Extreme volatility overwhelming signal/noise ratio", "Markets dominated by non-quantitative flows (central bank intervention)"],
        "min_historical_trades": 300,
    },
    "forensic_short": {
        "display_name": "Forensic Short Seller",
        "strategy_family": "fundamental_short",
        "philosophy": "Identifies companies with accounting red flags, earnings manipulation, or unsustainable business models. Takes short positions based on forensic accounting analysis and regulatory filings.",
        "entry_criteria": [
            "Receivables growing faster than revenue for 3+ consecutive quarters",
            "Related-party transactions exceeding 15% of COGS without arm's-length justification",
            "Capitalized expenses surging while operating cash flow stagnates",
            "Frequent changes in auditors or accounting policies",
        ],
        "exit_criteria": [
            "Short squeeze (borrow rate spikes, price jumps 20%+ in a day)",
            "Thesis validated (stock declines to fair value, cover into weakness)",
            "Time stop (hold max 90 days — shorting has negative carry)",
        ],
        "risk_reward_target": "1.0 to 3.0 (short selling is asymmetric: max gain 100%, max loss infinite)",
        "max_risk_per_trade_pct": 1.5,
        "suggested_backtesting_protocol": "Use only event-driven short signals (not systematic short). Account for borrow costs and buy-in risk. Compare fundamental shorts vs. technical shorts.",
        "confidence_calibration": "High when multiple red flags present + short interest not already elevated + management selling stock. Low when only one flag present.",
        "best_market_conditions": ["Late-cycle markets with inflated valuations", "Periods of accounting scrutiny post-scandal", "Markets where low-quality companies have been bid up"],
        "worst_market_conditions": ["Melt-up markets punishing short sellers", "Stocks with hard-to-borrow shares", "Companies with activist shareholders pushing for change"],
        "min_historical_trades": 50,
    },
    # ═══════════════════════════════════════════════════════════════════
    # PENNY / MICRO-CAP PERSONAS
    # ═══════════════════════════════════════════════════════════════════
    "microcap_momentum": {
        "display_name": "Micro-Cap Momentum",
        "strategy_family": "microcap",
        "philosophy": "Exploits the momentum factor in micro-cap stocks where retail participation drives persistent price trends. Focuses on low-float, high-volatility names with increasing social media attention.",
        "entry_criteria": [
            "Low float (< 20M shares) with increasing daily volume (2x+ average)",
            "Price above 20 and 50 SMA with upward slope",
            "Social media mention velocity increasing (Reddit, StockTwits signals)",
            "No recent dilutive offerings (ATM or registered direct)",
        ],
        "exit_criteria": [
            "Trailing stop at 1.5x ATR from the higher of 20 SMA or peak",
            "Volume divergence — price rising but volume declining",
            "Time exit after 5 trading days (micro-cap momentum is short-lived)",
        ],
        "risk_reward_target": "1.5 to 3.0",
        "max_risk_per_trade_pct": 2.0,
        "suggested_backtesting_protocol": "Short hold windows (1-5 days). Use high-frequency data (15min minimum). Account for slippage (wide spreads in micro-caps). Filter by market cap and volume thresholds.",
        "confidence_calibration": "High when price/volume/social all confirm. Low when only price action confirms without volume or social backing.",
        "best_market_conditions": ["Low-rate environments with retail speculation", "Rotations out of large caps into small/micro-caps", "Seasonally strong periods (January effect)"],
        "worst_market_conditions": ["Risk-off environments", "Market-wide liquidity crises", "Periods with no retail risk appetite"],
        "min_historical_trades": 200,
    },
    "safety_net": {
        "display_name": "Safety Net Value",
        "strategy_family": "deep_value",
        "philosophy": "Benjamin Graham-style deep value: buys at a discount to net current asset value (NCAV), liquidation value, or tangible book. Focuses on stocks where downside is protected by hard assets on the balance sheet.",
        "entry_criteria": [
            "Price-to-NCAV below 1.0 (Graham net-net screen)",
            "Price-to-tangible-book below 0.7",
            "Market cap below net cash + marketable securities",
            "Zero or minimal debt (debt/equity < 0.3)",
        ],
        "exit_criteria": [
            "Price reaches 1.5x NCAV (catalyst-driven value realization)",
            "Merger/takeover (book value play realized)",
            "If cash burn reduces NCAV by 20% in a quarter — exit immediately",
        ],
        "risk_reward_target": "2.0 to 4.0",
        "max_risk_per_trade_pct": 3.0,
        "suggested_backtesting_protocol": "Screen quarterly. Hold until price reaches 1.5x NCAV or 1 year, whichever comes first. Test across different market cap ranges. Account for long hold periods.",
        "confidence_calibration": "High when market cap < net cash, positive operating CF, and insider buying. Low when company is a 'value trap' — burning cash and destroying book value.",
        "best_market_conditions": ["Post-selloff periods with broad undervaluation", "Recession recoveries", "Spin-offs and corporate simplifications"],
        "worst_market_conditions": ["Asset-light business models dominating returns", "Prolonged periods where value factors underperform", "Technological disruption making physical assets obsolete"],
        "min_historical_trades": 30,
    },
}

# ── Registry access helpers ──

def get_persona(persona_id: str) -> dict | None:
    return PERSONA_REGISTRY.get(persona_id)


def get_all_persona_ids() -> list[str]:
    return list(PERSONA_REGISTRY.keys())


def build_persona_summary(persona_id: str) -> str:
    """Build a concise summary string for database logging."""
    p = get_persona(persona_id)
    if not p:
        return persona_id
    return (f"[{p['strategy_family']}] {p['display_name']}: {p['philosophy'][:120]} "
            f"| RR: {p['risk_reward_target']} | Conf: {p['confidence_calibration'][:100]}")


def build_persona_rationale(persona_id: str, symbol: str, direction: str, confidence: float) -> str:
    """Build a detailed pick-level rationale string for database logging."""
    p = get_persona(persona_id)
    if not p:
        return f"{persona_id} pick for {symbol} ({direction})"
    
    direction_text = "LONG (expecting appreciation)" if direction == "LONG" else "SHORT (expecting decline)"
    entry_hints = p['entry_criteria'][:2]
    exit_hints = p['exit_criteria'][:1]
    
    return (
        f"Strategy: {p['display_name']} ({p['strategy_family']})\n"
        f"Philosophy: {p['philosophy'][:200]}\n"
        f"Direction: {direction_text} on {symbol}\n"
        f"Confidence: {confidence:.0%}\n"
        f"Entry triggers: {' // '.join(entry_hints)}\n"
        f"Exit plan: {exit_hints[0] if exit_hints else 'Per strategy rules'}\n"
        f"RR target: {p['risk_reward_target']}\n"
        f"Max risk: {p['max_risk_per_trade_pct']}"
    )


# ── SQL DDL for persona registry table ──

PERSONA_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS ai_tournament_personas (
    persona_id          VARCHAR(64)     NOT NULL PRIMARY KEY,
    display_name        VARCHAR(128)    NOT NULL,
    strategy_family     VARCHAR(64)     NOT NULL,
    philosophy          TEXT            NOT NULL,
    entry_criteria      TEXT            NOT NULL,
    exit_criteria       TEXT            NOT NULL,
    risk_reward_target  VARCHAR(32)     NOT NULL,
    max_risk_per_trade  VARCHAR(32)     NOT NULL,
    backtesting_protocol TEXT           NOT NULL,
    confidence_calibration TEXT         NOT NULL,
    best_market_conditions TEXT         NOT NULL,
    worst_market_conditions TEXT        NOT NULL,
    min_historical_trades VARCHAR(32)   NOT NULL,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

PERSONA_MODEL_LINK_DDL = """
CREATE TABLE IF NOT EXISTS ai_tournament_model_personas (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    model_id        VARCHAR(64) NOT NULL,
    persona_id      VARCHAR(64) NOT NULL,
    asset_class     VARCHAR(16) NOT NULL,
    is_active       BOOLEAN     DEFAULT TRUE,
    assigned_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    deprecated_at   TIMESTAMP   NULL DEFAULT NULL,
    UNIQUE KEY uq_model_persona_ac (model_id, persona_id, asset_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

PERSONA_RUN_LOG_DDL = """
CREATE TABLE IF NOT EXISTS ai_tournament_persona_runs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_date        DATE        NOT NULL,
    model_id        VARCHAR(64) NOT NULL,
    persona_id      VARCHAR(64) NOT NULL,
    asset_class     VARCHAR(16) NOT NULL,
    picks_generated INT         DEFAULT 0,
    picks_resolved  INT         DEFAULT 0,
    picks_won       INT         DEFAULT 0,
    total_pnl_pct   DECIMAL(10,4) DEFAULT NULL,
    avg_confidence  DECIMAL(5,4)  DEFAULT NULL,
    sharpe_ratio    DECIMAL(8,4)  DEFAULT NULL,
    max_drawdown_pct DECIMAL(8,4) DEFAULT NULL,
    run_log         TEXT        DEFAULT NULL,
    created_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_run (run_date, model_id, persona_id, asset_class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def generate_insert_sqls() -> list[str]:
    """Generate INSERT statements for populating the persona registry."""
    sqls = [PERSONA_TABLE_DDL, PERSONA_MODEL_LINK_DDL, PERSONA_RUN_LOG_DDL]
    insert = """
    INSERT INTO ai_tournament_personas
        (persona_id, display_name, strategy_family, philosophy, entry_criteria,
         exit_criteria, risk_reward_target, max_risk_per_trade,
         backtesting_protocol, confidence_calibration,
         best_market_conditions, worst_market_conditions, min_historical_trades)
    VALUES ('{pid}', '{dn}', '{sf}', '{ph}', '{ec}',
            '{xc}', '{rr}', '{mr}',
            '{bt}', '{cc}',
            '{bm}', '{wm}', '{mh}')
    ON DUPLICATE KEY UPDATE
        display_name = VALUES(display_name),
        philosophy = VALUES(philosophy),
        updated_at = NOW()
    """
    for pid, p in PERSONA_REGISTRY.items():
        safe = lambda s: str(s).replace("'", "''")[:500]
        sqls.append(insert.format(
            pid=pid,
            dn=safe(p['display_name']),
            sf=safe(p['strategy_family']),
            ph=safe(p['philosophy'][:300]),
            ec=safe('; '.join(p['entry_criteria'])),
            xc=safe('; '.join(p['exit_criteria'])),
            rr=safe(str(p['risk_reward_target'])),
            mr=safe(str(p['max_risk_per_trade_pct'])),
            bt=safe(p['suggested_backtesting_protocol'][:300]),
            cc=safe(p['confidence_calibration'][:300]),
            bm=safe('; '.join(p['best_market_conditions'])),
            wm=safe('; '.join(p['worst_market_conditions'])),
            mh=safe(str(p['min_historical_trades'])),
        ))
    return sqls


SQL_FILES_DIR = Path(__file__).resolve().parent.parent / "data" / "ai_tournament"


def write_sqls() -> None:
    """Write the DDL + INSERT SQLs to a file for manual execution or CI ingest."""
    SQL_FILES_DIR.mkdir(parents=True, exist_ok=True)
    sqls = generate_insert_sqls()
    path = SQL_FILES_DIR / "persona_registry.sql"
    path.write_text("-- AI Tournament Persona Registry\n-- Generated: " +
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") +
                    "\n\n" + "\n".join(sqls))
    print(f"[persona_registry] Wrote {len(sqls)} statements to {path}")


if __name__ == "__main__":
    write_sqls()
    print(f"[persona_registry] {len(PERSONA_REGISTRY)} personas registered")
    for pid in PERSONA_REGISTRY:
        p = PERSONA_REGISTRY[pid]
        print(f"  {pid:25s} [{p['strategy_family']}] {p['display_name']}")
