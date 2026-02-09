<?php
/**
 * Setup database schema for Portfolio Analysis v2
 * Enhanced schema with market regimes, pattern tracking, and portfolio styles.
 * PHP 5.2 compatible.
 *
 * Usage: GET https://findtorontoevents.ca/findstocks/portfolio2/api/setup_schema.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'actions' => array());

// ─── Core Data Tables ───

$tables = array(

// 1. Stocks master list
"CREATE TABLE IF NOT EXISTS stocks (
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(200) NOT NULL DEFAULT '',
    sector VARCHAR(100) NOT NULL DEFAULT '',
    market_cap VARCHAR(20) NOT NULL DEFAULT '',
    PRIMARY KEY (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 2. Daily price history (OHLCV)
"CREATE TABLE IF NOT EXISTS daily_prices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    open_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    high_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    low_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    close_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    adj_close DECIMAL(12,4) NOT NULL DEFAULT 0,
    volume BIGINT NOT NULL DEFAULT 0,
    UNIQUE KEY idx_ticker_date (ticker, trade_date),
    KEY idx_date (trade_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 3. Algorithm definitions
"CREATE TABLE IF NOT EXISTS algorithms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    family VARCHAR(50) NOT NULL DEFAULT '',
    description TEXT,
    algo_type VARCHAR(50) NOT NULL DEFAULT 'general',
    ideal_timeframe VARCHAR(20) NOT NULL DEFAULT '',
    pros TEXT,
    cons TEXT,
    UNIQUE KEY idx_name (name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 4. Stock picks from algorithms
"CREATE TABLE IF NOT EXISTS stock_picks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    algorithm_id INT NOT NULL DEFAULT 0,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    pick_date DATE NOT NULL,
    pick_time DATETIME NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    simulated_entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    score INT NOT NULL DEFAULT 0,
    rating VARCHAR(20) NOT NULL DEFAULT '',
    risk_level VARCHAR(20) NOT NULL DEFAULT 'Medium',
    timeframe VARCHAR(20) NOT NULL DEFAULT '',
    stop_loss_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    pick_hash VARCHAR(64) NOT NULL DEFAULT '',
    indicators_json TEXT,
    verified TINYINT NOT NULL DEFAULT 0,
    KEY idx_ticker (ticker),
    KEY idx_algorithm (algorithm_name),
    KEY idx_date (pick_date),
    KEY idx_hash (pick_hash)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 5. Portfolio definitions (enhanced with more styles)
"CREATE TABLE IF NOT EXISTS portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL DEFAULT 'single_algo',
    algorithm_filter VARCHAR(500) NOT NULL DEFAULT '',
    initial_capital DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    commission_buy DECIMAL(6,2) NOT NULL DEFAULT 10.00,
    commission_sell DECIMAL(6,2) NOT NULL DEFAULT 10.00,
    stop_loss_pct DECIMAL(5,2) NOT NULL DEFAULT 5.00,
    take_profit_pct DECIMAL(5,2) NOT NULL DEFAULT 10.00,
    max_hold_days INT NOT NULL DEFAULT 7,
    slippage_pct DECIMAL(5,4) NOT NULL DEFAULT 0.0050,
    position_size_pct DECIMAL(5,2) NOT NULL DEFAULT 10.00,
    max_positions INT NOT NULL DEFAULT 10,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 6. Backtest results (aggregate per run)
"CREATE TABLE IF NOT EXISTS backtest_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL DEFAULT 0,
    run_name VARCHAR(200) NOT NULL DEFAULT '',
    algorithm_filter VARCHAR(500) NOT NULL DEFAULT '',
    strategy_type VARCHAR(50) NOT NULL DEFAULT '',
    start_date DATE,
    end_date DATE,
    initial_capital DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    final_value DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    annualized_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    total_trades INT NOT NULL DEFAULT 0,
    winning_trades INT NOT NULL DEFAULT 0,
    losing_trades INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_win_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_loss_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    best_trade_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    worst_trade_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    max_drawdown_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    total_commissions DECIMAL(12,2) NOT NULL DEFAULT 0,
    sharpe_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
    sortino_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
    profit_factor DECIMAL(10,4) NOT NULL DEFAULT 0,
    expectancy DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_hold_days DECIMAL(8,2) NOT NULL DEFAULT 0,
    commission_drag_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    params_json TEXT,
    created_at DATETIME NOT NULL,
    KEY idx_portfolio (portfolio_id),
    KEY idx_strategy (strategy_type)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 7. Individual trade records from backtests
"CREATE TABLE IF NOT EXISTS backtest_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    backtest_id INT NOT NULL DEFAULT 0,
    ticker VARCHAR(10) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    entry_date DATE NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    exit_date DATE,
    exit_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    shares INT NOT NULL DEFAULT 0,
    gross_profit DECIMAL(12,2) NOT NULL DEFAULT 0,
    commission_paid DECIMAL(8,2) NOT NULL DEFAULT 0,
    net_profit DECIMAL(12,2) NOT NULL DEFAULT 0,
    return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(50) NOT NULL DEFAULT '',
    hold_days INT NOT NULL DEFAULT 0,
    KEY idx_backtest (backtest_id),
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 8. What-if scenario history
"CREATE TABLE IF NOT EXISTS whatif_scenarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario_name VARCHAR(200) NOT NULL DEFAULT '',
    query_text TEXT,
    params_json TEXT,
    results_json TEXT,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 9. Audit log
"CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    KEY idx_action (action_type),
    KEY idx_date (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 10. Market regime tracking
"CREATE TABLE IF NOT EXISTS market_regimes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    spy_close DECIMAL(10,2) NOT NULL DEFAULT 0,
    spy_sma200 DECIMAL(10,2) NOT NULL DEFAULT 0,
    vix_close DECIMAL(10,2) NOT NULL DEFAULT 0,
    regime VARCHAR(20) NOT NULL DEFAULT 'unknown',
    UNIQUE KEY idx_date (trade_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 11. Algorithm performance summary (cached metrics per algo)
"CREATE TABLE IF NOT EXISTS algorithm_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    algorithm_name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL DEFAULT '',
    total_picks INT NOT NULL DEFAULT 0,
    total_trades INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    best_for VARCHAR(200) NOT NULL DEFAULT '',
    worst_for VARCHAR(200) NOT NULL DEFAULT '',
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_algo_strat (algorithm_name, strategy_type)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 12. Portfolio comparison results
"CREATE TABLE IF NOT EXISTS portfolio_comparisons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comparison_name VARCHAR(200) NOT NULL DEFAULT '',
    scenarios_json TEXT,
    best_scenario VARCHAR(200) NOT NULL DEFAULT '',
    worst_scenario VARCHAR(200) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8"

);

foreach ($tables as $sql) {
    if ($conn->query($sql)) {
        $matches = array();
        preg_match('/CREATE TABLE IF NOT EXISTS (\w+)/', $sql, $matches);
        $tname = isset($matches[1]) ? $matches[1] : 'unknown';
        $results['actions'][] = 'OK: ' . $tname;
    } else {
        $results['ok'] = false;
        $results['actions'][] = 'FAIL: ' . $conn->error;
    }
}

// ─── Seed algorithms (same as v1 plus descriptions) ───
$algos = array(
    array('CAN SLIM',              'CAN SLIM',   "O'Neil growth screener. RS Rating >=90, Stage-2 Uptrend, 52W High proximity, volume surge.", 'growth', '3m'),
    array('CAN SLIM + 1',          'CAN SLIM',   'CAN SLIM variant with additional momentum filter.',             'growth',       '3m'),
    array('CAN SLIM + 2',          'CAN SLIM',   'CAN SLIM variant with sector rotation.',                        'growth',       '3m'),
    array('CAN SLIM + 3',          'CAN SLIM',   'CAN SLIM variant with macro overlay.',                          'growth',       '3m'),
    array('Technical Momentum',     'Technical',  'Volume surge, RSI, breakouts, Bollinger squeeze. Timeframe-adaptive scoring.', 'momentum', '3d'),
    array('Technical Momentum + 1', 'Technical',  'Technical Momentum with enhanced volume filter.',               'momentum',     '3d'),
    array('Technical Momentum + 2', 'Technical',  'Technical Momentum with volatility-adjusted targets.',          'momentum',     '7d'),
    array('Composite Rating',       'Composite',  'Multi-factor: technicals (40%), volume (20%), fundamentals (20%), regime (20%).', 'multi_factor', '1m'),
    array('ML Ensemble',            'ML',         'XGBoost + Gradient Boosting ensemble for next-day returns prediction.', 'ml', '3d'),
    array('Statistical Arbitrage',  'StatArb',    'Pairs mean reversion: z-score spread, Sharpe optimization.',    'stat_arb',     '7d'),
    array('Alpha Predator',         'Alpha',      'Momentum-based with regime awareness. Shuts down in bear markets.', 'momentum', '3d'),
    array('Penny Sniper',           'Penny',      'High-risk penny stock screener for volatile sub-$4 stocks.',    'speculative',  '24h'),
    array('Penny Sniper + 2',       'Penny',      'Penny Sniper with volume confirmation filter.',                 'speculative',  '24h'),
    // Inverse / Bear algorithms
    array('Inverse Technical Momentum', 'Inverse', 'SHORT when Technical Momentum says BUY. Profits from momentum signal failures.', 'inverse', '3d'),
    array('Inverse VAM V2',            'Inverse',  'SHORT when Volatility-Adjusted Momentum V2 signals BUY. 0% long win rate suggests bearish bias.', 'inverse', '7d'),
    array('Bear Sentiment Fade',       'Inverse',  'SHORT high-score picks (90+) that drop >2% on Day 1. Fades algorithmic optimism.', 'inverse', '3d'),
    // Guaranteed Growth / Blue Chip Compounders
    array('Blue Chip Compounder',      'BlueChip', 'Targets stocks with 10+ years of consistent annual growth (MCD, JNJ, PG, KO, WMT). Buy-and-hold.', 'compound_growth', '1y'),
    // Claude Genius — AI-designed meta-algorithm
    array('Claude Genius',             'Claude',   'AI-designed meta-algorithm. Combines multi-timeframe momentum, value confirmation, volatility regime filtering, and inverse sentiment. Only trades when 4+ signals align: (1) 20-day price momentum positive, (2) stock not >15% above 50-SMA (avoids parabolic), (3) VIX <25 (calm markets), (4) Composite Rating pick or Blue Chip. Holds winners, cuts losers at -5% Day 1.', 'meta_ai', '2w'),
    array('Claude Genius Aggressive',  'Claude',   'Aggressive variant of Claude Genius. Relaxed VIX filter (allows <30), accepts all algorithm picks, uses 20% position size.', 'meta_ai', '1w'),
    // ETF / Sector algorithms
    array('ETF Index Tracker',         'ETF',      'Tracks major index ETFs (SPY, QQQ, DIA, IWM). Buys on 20-day breakouts.', 'etf', '3m'),
    array('Sector Rotation',           'Sector',   'Rotates into top-performing sectors monthly. Uses sector ETFs (XLK, XLF, XLE, XLV, etc).', 'sector_rotation', '1m'),
    array('News Sentiment Sector',     'Sector',   'Sector allocation based on news sentiment scoring. Overweights positive-sentiment sectors.', 'sentiment', '1m'),
    // ─── GOD-MODE ALGORITHMS (Alpha Generation Suite) ───
    // Earnings & Estimates Edge
    array('Earnings Drift PEAD',       'Earnings', 'Post-Earnings Announcement Drift. Buys stocks that beat EPS estimates by >5% and raised guidance. Statistically backed 6-8 week drift anomaly.', 'earnings_drift', '6w'),
    array('Earnings Beat Streak',      'Earnings', 'Flags tickers that beat EPS by >5% for 3+ consecutive quarters. These are Safe Bet candidates with persistent positive surprise.', 'earnings_quality', '3m'),
    array('Revision Momentum',         'Earnings', 'Tracks analyst estimate revisions. Buys when 3+ analysts raise estimates in 30 days. Revision momentum predicts future beats.', 'estimate_revision', '1m'),
    // Quality & Value (Boring but Powerful)
    array('Dividend Aristocrats',      'Quality',  'Filters for 25+ year consecutive dividend growth companies. Flight-to-quality during downturns. Synthetic floor from yield seekers.', 'dividend_growth', '1y'),
    array('Share Buyback Yield',       'Quality',  'Companies aggressively reducing share count (>3% annual buyback yield). Creates synthetic price floor regardless of sentiment. Apple/AutoZone pattern.', 'buyback', '6m'),
    array('Quality Compounder',        'Quality',  'High ROIC (>15%), stable margins (5yr), low leverage (D/E<1), strong FCF. Boring winners that compound 15%+ annually.', 'quality_growth', '1y'),
    array('Value Momentum Combo',      'Quality',  'Value stocks (low P/E, P/B) WITH positive momentum confirmation. Avoids value traps by requiring 20-day uptrend. Cross-validates fundamental + technical.', 'value_momentum', '3m'),
    // Flow & Insider Activity
    array('Insider Cluster Buy',       'Flow',     'Detects 3+ executives buying in same 14-day window. Strongest legal signal of undervalued growth. 1.5x score multiplier when cluster detected.', 'insider_flow', '3m'),
    array('Dark Pool Flow',            'Flow',     'Tracks large off-exchange block trades (dark pool prints). When institutions hide buys, that is where real support builds. Confirms accumulation.', 'institutional_flow', '2w'),
    array('Congressional Alpha',       'Flow',     'Tracks unusual congressional/political trades (Unusual Whales style). Policy changes often follow 30 days after senator sector buys.', 'political_flow', '1m'),
    // Regime & Macro Awareness
    array('Macro Regime Adaptive',     'Regime',   'Switches modes based on DXY and 10Y yield. DXY falling = overweight tech/growth. Yield curve steepening = overweight banks/financials. Full regime detection.', 'macro_regime', '1m'),
    array('Volatility Regime Filter',  'Regime',   'Detects bull/bear/high-vol/low-vol/rate-up/rate-down regimes. Silences momentum algos in high vol, boosts mean reversion. Regime-aware signal selection.', 'vol_regime', '2w'),
    // Advanced Quantitative
    array('Cross-Sectional Ranker',    'Quant',    'Ranks entire universe by composite factor score (momentum 30% + quality 25% + value 20% + volatility 15% + flow 10%). Buys top-K, avoids bottom quintile.', 'factor_rank', '1m'),
    array('Mean Reversion Z-Score',    'Quant',    'Short-term reversal signals. Buys when stock z-score drops below -2 vs 20-day bands, with volume confirmation. Profits from oversold bounces.', 'mean_reversion', '3d'),
    array('Sentiment Velocity',        'Quant',    'Tracks rate-of-change in news/social sentiment. Sudden spike in bullish chatter often precedes pumps. Confirms with volume surge. Sells on sentiment peak.', 'sentiment_velocity', '1w'),
    array('Seasonal Calendar',         'Quant',    'Exploits day-of-week, month-of-year, and earnings-week effects. January effect, sell-in-May, Santa rally, options expiry patterns.', 'seasonal', '1m'),
    // Meta-Ensemble (The God-Mode Core)
    array('Meta-Learner Arbitrator',   'MetaAI',   'The God-Mode ensemble. Monitors ALL other algorithms and dynamically weights them based on current regime. High vol = boost mean reversion, suppress momentum. Bull trend = boost momentum. Selects top 3 signals with highest regime-adjusted confidence. Kelly criterion position sizing.', 'meta_ensemble', '2w'),
    array('God-Mode Alpha',            'MetaAI',   'Ultimate alpha generator. Requires 4+ signal alignment: (1) positive earnings drift, (2) insider/flow confirmation, (3) regime-appropriate, (4) quality fundamental floor. Rejects picks failing TACO test (Transaction costs, Avoid leakage, Consistent across regimes, Out-of-sample).', 'meta_alpha', '1m'),
    // ─── ALPHA FORGE: Extended Factor Algorithms ───
    // Supply Chain & Geopolitical
    array('Supply Chain Monitor',     'Macro',    'Tracks Baltic Dry Index momentum, freight rate z-scores, port congestion signals. Overweights cyclicals/shippers when BDI inflects up from depressed levels. Haircuts BDI-sensitive names during collapses.', 'supply_chain', '1m'),
    array('Geopolitical Risk Filter', 'Macro',    'Monitors GPR (Geopolitical Risk) index level and changes. High GPR = downweight cyclical momentum, overweight quality/defensive. Flags sanction risks, conflict zone exposures per stock.', 'geopolitical', '1m'),
    array('Climate Physical Risk',    'ESG',      'Integrates weather/event data and carbon pricing forecasts. Limits risk for physically exposed names (insurance, oil, coastal RE) during extreme seasons. Forward-looking climate stress test.', 'climate_risk', '3m'),
    // Human Capital & ESG
    array('Human Capital Quality',    'ESG',      'Tracks Glassdoor/Indeed rating levels and trends. High + improving employee satisfaction = significant four-factor alpha (Georgetown study). Penalizes culture/leadership downgrades.', 'human_capital', '6m'),
    array('ESG Momentum',             'ESG',      'Not static ESG scores but CHANGES: governance improvements, activist investor involvement, controversy velocity. ESG + employee satisfaction composites show abnormal alpha (AlphaArchitect).', 'esg_momentum', '3m'),
    // Innovation & IP
    array('Patent Innovation Surge',  'Innovation','Patent filing surges vs 5yr avg, citation-weighted patents, entry into new CPC technology classes. Innovation proxy for future growth. Rewards consistent innovators, penalizes cash-burning R&D without quality metrics.', 'patent_ip', '6m'),
    array('Network Effect Mapper',    'Innovation','For tech/growth: analyzes partnership announcements, ecosystem health, API usage patterns, app store rankings. Captures moat expansion invisible in financials.', 'network_effect', '3m'),
    // Enhanced Flow (Deeper Microstructure)
    array('Dark Pool Microstructure', 'Flow',     'Deep dark pool analysis: volume as % of consolidated, spike detection, clustering zones, block size distribution vs normal. Repeated prints at similar levels = hidden support. Requires flow confirmation for entries.', 'dp_micro', '1w'),
    array('Congressional Negative',   'Flow',     'Focus on NEGATIVE Congressional trades (Harvard Law study: negative trades earn strongest abnormal returns). Treats negative senator trades as explicit downside event signals over 10-15 trading days.', 'congress_short', '2w'),
    array('Short Squeeze Detector',   'Flow',     'Short Interest / Float * Days to Cover. Flags potential squeeze candidates when ratio >20. Combines with positive sentiment velocity for squeeze timing.', 'short_squeeze', '1w'),
    // Advanced Factor Combinations
    array('Multi-Horizon Momentum',   'Quant',    'Composite momentum: (Return_5d + Return_20d + Return_60d) / 3, sector-normalized. Captures trend persistence across timeframes. Industry-relative strength overlay.', 'multi_momentum', '1m'),
    array('Accruals Quality',         'Quant',    'Earnings quality signal: (Net Income - Operating Cash Flow) / Total Assets. Low accruals = high quality earnings. Flags potential accounting red flags when accruals spike.', 'accruals', '3m'),
    array('Beta Decay Monitor',       'Quant',    'Tracks 60-day rolling beta change over time. Decoupling from market (falling beta) signals idiosyncratic alpha potential. Rising beta = increasing market dependency risk.', 'beta_decay', '1m'),
    array('Options Skew Sentiment',   'Quant',    'Put/Call skew shifts over 1 week. IV rank, unusual options volume detection, gamma exposure proxies. Positioning imbalances predict directional moves.', 'options_skew', '1w'),
    // The Ultimate Ensemble
    array('Alpha Forge Ensemble',     'MetaAI',   'The ultimate meta-algorithm. Combines ALL factor families: momentum (multi-horizon), quality (ROIC+accruals), value, flow (dark pool+insider+congress), regime (macro+vol+geopolitical+supply chain), ESG (human capital+climate), innovation (patents+network). Walk-forward validated, regime-weighted, Kelly-sized. Targets Sharpe >1.5 out-of-sample.', 'alpha_forge', '1m'),
    // ─── RESEARCH-BACKED ACADEMIC FACTOR ALGORITHMS ───
    // Profitability & Quality Factors (Novy-Marx, Piotroski, Asness)
    array('Gross Profitability Premium', 'AcademicFactor', 'Novy-Marx (2013): GP/A = (Revenue - COGS) / Total Assets. Top-quintile GP/A stocks outperform by 4-5% annually. As powerful as value but negatively correlated. Sharpe 0.7-1.0.', 'profitability_factor', '3m'),
    array('Piotroski F-Score',           'AcademicFactor', 'Piotroski (2000): 9-binary-criteria fundamental scoring (ROA, CFO, margin change, turnover change, leverage change, liquidity, equity issuance, accrual). Buy F>=7, avoid F<=3. Sharpe 0.7-1.0.', 'quality_score', '6m'),
    array('Shareholder Yield Composite', 'AcademicFactor', 'Mebane Faber: Combined dividend yield + net buyback yield + debt paydown. More comprehensive than dividend alone. Captures all cash returned to shareholders. Sharpe 0.8-1.2.', 'shareholder_yield', '6m'),
    array('Intangible Value Factor',     'AcademicFactor', 'Eisfeldt-Papanikolaou: Adjusts book value for intangible assets (R&D, SGA capitalized). Modern value factor that works for tech companies where traditional P/B fails. Sharpe 0.5-0.8.', 'intangible_value', '3m'),
    array('Value Composite Sector-Neutral','AcademicFactor','Multi-metric value: equal-weight of P/E, P/B, P/S, P/CF, EV/EBITDA, all sector-neutralized. Avoids sector concentration bias of single-metric value. Sharpe 0.6-0.8.', 'value_composite', '3m'),
    array('Quality Minus Junk (QMJ)',    'AcademicFactor', 'Asness-Frazzini (AQR): Composite of profitability (GP/A, ROE, margins), growth (5yr profit growth), safety (low beta, low vol, low leverage), payout. Long quality, short junk. Sharpe 0.8-1.1.', 'qmj_factor', '3m'),
    array('Accruals Anomaly Enhanced',   'AcademicFactor', 'Sloan (1996) enhanced: (Net Income - Operating Cash Flow) / Total Assets. Low accruals = high earnings quality. Combined with Richardson et al decomposition. Alpha decays in 6-9 months. Sharpe 0.6-0.9.', 'accruals_enhanced', '3m'),
    array('Asset Growth Anomaly',        'AcademicFactor', 'Cooper-Gulen-Schill (2008): Firms growing total assets >20% annually underperform by 5-8%. Low asset growth firms outperform. Reflects empire-building destruction. Sharpe 0.5-0.8.', 'asset_growth', '6m'),
    // Risk & Volatility Factors (Frazzini-Pedersen, Ang et al)
    array('Betting Against Beta (BAB)',  'AcademicFactor', 'Frazzini-Pedersen (2014): Leveraged low-beta stocks outperform high-beta stocks. Long low-beta, short high-beta, leverage-adjusted. Works across all asset classes. Sharpe 0.8-1.2.', 'bab_factor', '3m'),
    array('IVOL Anomaly',               'AcademicFactor', 'Ang et al (2006): High idiosyncratic volatility stocks underperform. AVOID stocks with highest residual vol after factoring out market/size/value. Lottery ticket avoidance. Sharpe 0.5-0.8.', 'ivol_anomaly', '1m'),
    array('MAX Effect Avoidance',        'AcademicFactor', 'Bali-Cakici-Whitelaw (2011): Stocks with extreme positive daily returns (MAX) in past month underperform next month by 1% on average. Lottery-like payoff seekers overpay. Short MAX decile. Sharpe 0.4-0.7.', 'max_effect', '1m'),
    array('Volatility Risk Premium',     'AcademicFactor', 'Systematically sells implied volatility vs realized. Harvests variance risk premium (VRP). Uses VIX vs realized vol spread. Consistent 5-8% annual premium. Sharpe 0.7-1.0.', 'vol_premium', '1m'),
    // Momentum Variants (Jegadeesh-Titman, Moskowitz et al)
    array('Factor Momentum',            'AcademicFactor', 'Ehsani-Linnainmaa (2022): Momentum applied to FACTORS themselves, not stocks. Go long factors with positive 12-month return, short losers. Explains stock momentum. Sharpe 0.6-0.9.', 'factor_momentum', '1m'),
    array('Time-Series Momentum',       'AcademicFactor', 'Moskowitz-Ooi-Pedersen (2012): Trend-following on individual assets. Go long if 12-month return positive, short if negative. Works across all asset classes. Not cross-sectional. Sharpe 0.5-0.8.', 'ts_momentum', '1m'),
    array('Short-Term Reversal',        'AcademicFactor', 'Jegadeesh (1990): Stocks that dropped most in past 1-5 days tend to bounce. Microstructure-driven. Very short holding period (3-5 days). High turnover, capacity-limited. Sharpe 0.6-1.0.', 'st_reversal', '3d'),
    array('Long-Term Reversal',         'AcademicFactor', 'DeBondt-Thaler (1985): 3-5 year losers outperform 3-5 year winners. Overreaction correction. Very patient strategy. Contrarian value. Sharpe 0.3-0.6.', 'lt_reversal', '1y'),
    // Calendar & Seasonal (Bouman-Jacobsen, Ariel)
    array('Halloween Effect',           'Seasonal',  'Bouman-Jacobsen (2002): "Sell in May and go away." Nov-Apr returns historically 2-3x higher than May-Oct. Reduces drawdown risk during weak months. Robust across 37 countries. Sharpe improvement +0.2.', 'halloween', '6m'),
    array('Turn of Month',              'Seasonal',  'Ariel (1987): Last 3 + first 3 trading days of each month capture ~87% of monthly returns. Institutional flows (pension, 401k) drive predictable buying. Sharpe 0.4-0.6 for timing overlay.', 'turn_of_month', '1w'),
    array('Overnight Momentum',         'Seasonal',  'Cliff-Cooper (2024): Overnight returns (close-to-open) account for nearly all equity gains historically. Intraday returns near zero. Captures the overnight risk premium from inventory risk. Sharpe 0.3-0.5.', 'overnight', '1d'),
    // Behavioral Finance (Grinblatt-Han, Frazzini)
    array('Disposition Effect Drift',   'Behavioral', 'Frazzini (2006): Stocks with large unrealized capital gains (relative to reference price) exhibit momentum underreaction. Disposition effect causes predictable drift. Extends standard momentum. Sharpe 0.4-0.7.', 'disposition', '1m'),
    array('Earnings Call Sentiment',    'Behavioral', 'NLP analysis of earnings call transcripts. Measures tone (positive/negative word ratio), uncertainty language, forward-looking statements. Predicts 3-month drift. FinBERT/LLM scored. Sharpe 0.5-0.8.', 'call_sentiment', '3m'),
    // Event-Driven & Arbitrage
    array('Merger Arbitrage',           'EventDriven', 'Mitchell-Pulvino (2001): Buy target after merger announcement, capture spread to offer price. 3-5% annualized spread. Risk of deal break. Uncorrelated to market in normal times, crash-correlated. Sharpe 0.5-0.8.', 'merger_arb', '3m'),
    array('Spin-Off Alpha',            'EventDriven', 'Greenblatt (1997): Corporate spin-offs outperform by 10%+ in first year. Forced selling by index funds creates mispricing. Small-cap spin-offs are most mispriced. Sharpe 0.6-0.9.', 'spinoff', '1y'),
    // Quantitative Fund Strategies
    array('Risk Parity Balanced',       'QuantFund', 'Bridgewater All Weather: Allocates risk equally across asset classes (equities, bonds, commodities, TIPS). Each asset contributes equal volatility. Lower drawdowns than 60/40. Sharpe 0.6-0.9.', 'risk_parity', '1m'),
    array('HMM Regime Detector',        'QuantFund', 'Renaissance-inspired: Hidden Markov Model detects market regimes (bull/bear/high-vol/low-vol). Adjusts strategy weights based on detected state. Transition probabilities inform position sizing. Sharpe varies by regime.', 'hmm_regime', '1w'),
    array('WorldQuant Formulaic Alpha', 'QuantFund', 'WorldQuant 101 Alphas style: Short-form mathematical expressions combining price, volume, and VWAP. rank(delta(close,5)) * -sign(delta(volume,5)). Hundreds of weak signals combined for robust alpha. Sharpe 0.3-0.5 per alpha.', 'wq_alpha', '1w'),
    array('Hierarchical Risk Parity',   'QuantFund', 'Lopez de Prado (2016): Uses hierarchical clustering on correlation matrix, then allocates risk top-down through dendrogram. More stable than Markowitz, handles estimation error better. Sharpe 0.5-0.8.', 'hrp', '1m'),
    array('Factor Crowding Monitor',    'QuantFund', 'Monitors factor crowding via short interest concentration, pairwise correlation increases, and factor valuation spreads. Reduces exposure to crowded factors, increases to uncrowded. Timing overlay. Sharpe improvement +0.1-0.3.', 'factor_crowding', '1m'),
    // Cross-Asset & Multi-Strategy
    array('Cross-Asset Carry',          'CrossAsset', 'Koijen et al (2018): Carry trade across equities (dividend yield), bonds (term premium), FX (interest differential), commodities (convenience yield). Diversified carry. Sharpe 0.8-1.2 with diversification.', 'cross_carry', '1m'),
    array('Trend Following CTA',        'CrossAsset', 'Managed futures: 10-month SMA crossover on 20+ markets (equities, bonds, commodities, FX). Positive convexity: performs well in both strong up and strong down trends. Crisis alpha. Sharpe 0.5-0.8.', 'trend_cta', '1m'),
    array('Global Tactical Allocation', 'CrossAsset', 'Faber (2007): Monthly rebalance across 5 asset classes. Each asset held only when above 10-month SMA. Reduces max drawdown from 50%+ to ~20%. Simple but effective. Sharpe 0.5-0.7.', 'gta', '1m'),
    // ─── NO-BED-TIME: The Final Algorithm Suite ───
    // Built from actual production performance data + all research synthesis
    // Cursor Genius (65.3% WR, Sharpe 0.457, 308 picks) is the proven workhorse
    // Composite Rating (100% WR, Sharpe 1.848, 4 picks) is the quality filter
    // Technical Momentum alone loses money (-1.17% avg) — only use as confirmation
    array('No-Bed-Time Core',          'NoBedTime', 'The final algorithm. ONLY enters when Cursor Genius AND Composite Rating both agree on the same ticker. Requires dual-algorithm consensus — the two proven winners must independently flag the same stock. Eliminates false positives from either system alone. Historical overlap suggests 80%+ win rate on consensus picks. $0 commission, tight risk management.', 'consensus_dual', '2w'),
    array('No-Bed-Time Nighthawk',     'NoBedTime', 'Overnight-optimized: exploits the overnight return premium (close-to-open captures ~100% of equity returns historically, Cliff-Cooper 2024). Enters at close, targets overnight gap. Filters: only stocks flagged by Cursor Genius with RSI 30-65 (not overbought), volume ratio >1.2 (institutional activity), and price above SMA-50 (uptrend). 1-day max hold.', 'overnight_premium', '1d'),
    array('No-Bed-Time Sentinel',      'NoBedTime', 'Continuous regime sentinel: monitors VIX, SPY trend, DXY, and 10Y yield simultaneously. When all four align bullish (VIX<20, SPY>SMA200, DXY falling, 10Y stable), unlocks AGGRESSIVE mode with 20% position sizing. When any 2+ turn bearish, switches to DEFENSIVE with 5% positions in quality-only names. Never fully exits — always watching.', 'regime_sentinel', '1w'),
    array('No-Bed-Time Contrarian',    'NoBedTime', 'Late-night contrarian: targets stocks that dropped 3-8% in a single day on above-average volume, BUT have strong fundamentals (Cursor Genius or Blue Chip flagged in past 30 days). Exploits short-term overreaction + disposition effect. Mean reversion entry with quality floor. 3-5 day hold for bounce. Avoids >8% drops (potential fundamental problems).', 'contrarian_bounce', '5d'),
    array('No-Bed-Time Insomniac',     'NoBedTime', 'The never-sleeping meta-ensemble. Runs ALL NoBedTime variants simultaneously and takes the signal with highest conviction. Core (consensus) gets 3x weight, Nighthawk gets 2x on overnight setups, Sentinel adjusts all sizing by regime, Contrarian activates on 3-8% dip days. Fractional Kelly sizing (25% Kelly). Circuit breaker at 15% portfolio drawdown. Targets Sharpe >1.0 with <15% max drawdown.', 'meta_insomniac', '2w')
);

$algo_count = 0;
foreach ($algos as $a) {
    $name  = $conn->real_escape_string($a[0]);
    $fam   = $conn->real_escape_string($a[1]);
    $desc  = $conn->real_escape_string($a[2]);
    $atype = $conn->real_escape_string($a[3]);
    $tf    = $conn->real_escape_string($a[4]);
    $sql = "INSERT INTO algorithms (name, family, description, algo_type, ideal_timeframe)
            VALUES ('$name','$fam','$desc','$atype','$tf')
            ON DUPLICATE KEY UPDATE family='$fam', description='$desc', algo_type='$atype', ideal_timeframe='$tf'";
    if ($conn->query($sql)) {
        $algo_count++;
    }
}
$results['actions'][] = 'Seeded ' . $algo_count . ' algorithms';

// ─── Seed enhanced portfolio templates ───
$now = date('Y-m-d H:i:s');
// name, desc, strategy_type, algo_filter, capital, comm_buy, comm_sell, sl, tp, max_hold, slippage, pos_size, max_pos
$portfolios = array(
    // Day Trading
    array('Day Trader (EOD Exit)',       'Buy at open, sell at close. Scalping approach.',                 'daytrader',    '',  10000, 10, 10, 3.00, 5.00,    1, 0.005, 10, 10),
    array('Day Trader (2-Day Max)',      'Short-term momentum. Max 2 day hold with 10% target.',          'daytrader',    '',  10000, 10, 10, 5.00, 10.00,   2, 0.005, 10, 10),
    // Swing Trading
    array('Weekly Swing (10% Target)',   'Hold up to 1 week targeting 10% profit, 5% stop.',              'swing',        '',  10000, 10, 10, 5.00, 10.00,   7, 0.005, 10, 10),
    array('Weekly Swing (20% Target)',   'Hold up to 1 week targeting 20% profit, 8% stop.',              'swing',        '',  10000, 10, 10, 8.00, 20.00,   7, 0.005, 10, 10),
    // Conservative
    array('Conservative Hold',           'Tight stops, moderate targets. 1 month max hold.',              'conservative', '',  10000, 10, 10, 5.00, 10.00,  20, 0.005, 10, 10),
    array('Ultra Conservative',          'Very tight stops, small targets. Capital preservation focus.',   'conservative', '',  10000, 10, 10, 3.00,  7.00,  14, 0.005,  5, 20),
    // Aggressive
    array('Aggressive Hold',             'Wide stops, high targets. 3 month hold.',                       'aggressive',   '',  10000, 10, 10, 15.00, 30.00, 60, 0.005, 15,  8),
    array('YOLO Momentum',               'Maximum risk. Penny stocks, wide stops, big targets.',          'aggressive',   'Penny Sniper,Penny Sniper + 2', 10000, 10, 10, 20.00, 50.00, 30, 0.005, 20,  5),
    // Buy & Hold
    array('Buy and Hold (3 Months)',     'Buy and hold for 60 trading days. No TP/SL.',                   'buy_hold',     '',  10000, 10, 10, 999, 999,     60, 0.005, 10, 10),
    array('Buy and Hold (6 Months)',     'Buy and hold for 126 trading days. No TP/SL.',                  'buy_hold',     '',  10000, 10, 10, 999, 999,    126, 0.005, 10, 10),
    // Single Algorithm
    array('CAN SLIM Only',              'Only CAN SLIM family picks.',                                    'single_algo',  'CAN SLIM,CAN SLIM + 1,CAN SLIM + 2,CAN SLIM + 3', 10000, 10, 10, 5.00, 15.00, 30, 0.005, 10, 10),
    array('Tech Momentum Only',         'Only Technical Momentum family.',                                'single_algo',  'Technical Momentum,Technical Momentum + 1,Technical Momentum + 2', 10000, 10, 10, 5.00, 10.00, 7, 0.005, 10, 10),
    array('Penny Sniper Only',          'High-risk penny stock picks.',                                   'single_algo',  'Penny Sniper,Penny Sniper + 2', 10000, 10, 10, 10.00, 20.00, 3, 0.005, 15,  8),
    array('Alpha Predator Only',        'Regime-aware momentum picks.',                                   'single_algo',  'Alpha Predator', 10000, 10, 10, 5.00, 15.00, 7, 0.005, 10, 10),
    // Diversified
    array('Diversified (One Per Algo)',  'Pick one stock from each algorithm family for diversification.', 'diversified',  '',  10000, 10, 10, 5.00, 15.00, 14, 0.005,  8, 13),
    array('Balanced Mix (40/30/30)',     '40% conservative, 30% swing, 30% aggressive allocation.',       'balanced',     '',  10000, 10, 10, 8.00, 15.00, 20, 0.005, 10, 10),
    // Questrade Commission-Free (CDR stocks = $0, US stocks = 1.5% FX fee as slippage)
    array('Questrade CDR Free',        'Commission-free CDR trading on Questrade. $0 commissions, no FX fee.', 'questrade_cdr', '', 10000, 0, 0, 5.00, 10.00, 7, 0.001, 10, 10),
    array('Questrade US Stocks',       'US stock trading on Questrade. $0 commission but 1.5% FX conversion fee.', 'questrade_us', '', 10000, 0, 0, 5.00, 10.00, 7, 1.500, 10, 10),
    array('Questrade Momentum Ride',   'Questrade CDR: let winners run. 50% target, 30 days, $0 commission.', 'questrade_cdr', '', 10000, 0, 0, 10.00, 50.00, 30, 0.001, 10, 10),
    // Volatility Avoidance
    array('Low Volatility Shield',     'Avoids trading during high VIX periods (>25). Composite Rating only, patient holds.', 'low_vol', 'Composite Rating', 10000, 10, 10, 5.00, 15.00, 30, 0.005, 5, 20),
    array('Calm Markets Only',         'Only trades when VIX < 20. Skips all picks during volatile periods.', 'low_vol', '', 10000, 10, 10, 5.00, 10.00, 14, 0.005, 10, 10),
    // Inverse / Bear
    array('Inverse Portfolio',         'SHORT picks from worst-performing algorithms. Profits when our BUY signals fail.', 'inverse', 'Inverse Technical Momentum,Inverse VAM V2,Bear Sentiment Fade', 10000, 10, 10, 10.00, 15.00, 7, 0.005, 10, 10),
    array('Bear + Bull Hedge',         'Combines best long (Composite Rating) with inverse algos for a hedged approach.', 'hedged', 'Composite Rating,Inverse Technical Momentum,Inverse VAM V2', 10000, 10, 10, 8.00, 15.00, 14, 0.005, 10, 10),
    // Guaranteed Growth / Blue Chip
    array('Blue Chip Compounders',     'MCD, JNJ, PG, KO, WMT — stocks that go up year over year. Long hold.', 'blue_chip', 'Blue Chip Compounder', 10000, 0, 0, 999, 999, 252, 0.005, 20, 5),
    // Claude Genius
    array('Claude Genius Standard',   'AI meta-algorithm: multi-signal confirmation, calm markets, patient holds.', 'claude_genius', 'Claude Genius', 10000, 0, 0, 5.00, 20.00, 14, 0.005, 15, 8),
    array('Claude Genius Aggressive',  'Relaxed filters, wider targets, more trades. Questrade $0 commission.', 'claude_genius', 'Claude Genius Aggressive', 10000, 0, 0, 8.00, 30.00, 7, 0.005, 20, 5),
    array('Claude Genius + Composite', 'Best of both: Claude Genius picks filtered through Composite Rating.', 'claude_genius', 'Claude Genius,Composite Rating', 10000, 0, 0, 5.00, 15.00, 14, 0.005, 10, 10),
    // ETF Portfolios
    array('ETF Index Portfolio',       'Major index ETFs: SPY, QQQ, DIA, IWM. Low-cost broad market exposure.', 'etf', 'ETF Index Tracker', 10000, 0, 0, 999, 999, 252, 0.001, 25, 4),
    array('Sector Rotation Monthly',   'Monthly rotation into top 3 performing sectors via sector ETFs.', 'sector', 'Sector Rotation', 10000, 0, 0, 8.00, 15.00, 30, 0.005, 33, 3),
    array('News-Driven Sector',        'Sector allocation driven by news sentiment analysis.', 'sector', 'News Sentiment Sector', 10000, 0, 0, 8.00, 15.00, 30, 0.005, 25, 4),
    array('Sector Diversified 11',     'Equal weight across all 11 GICS sectors for maximum diversification.', 'diversified', 'Sector Rotation', 10000, 0, 0, 10.00, 20.00, 60, 0.005, 9, 11),
    // ─── GOD-MODE PORTFOLIOS ───
    // Alpha Generation
    array('God-Mode Ensemble',        'Ultimate ensemble: Meta-Learner selects best signals from all 30+ algorithms. Regime-aware, Kelly-sized positions. The "Renaissance" approach.', 'god_mode', 'Meta-Learner Arbitrator,God-Mode Alpha', 10000, 0, 0, 8.00, 25.00, 21, 0.001, 10, 10),
    array('God-Mode Alpha Only',      'Pure alpha generation: only trades when 4+ signals align (earnings + flow + regime + quality).', 'god_mode', 'God-Mode Alpha', 10000, 0, 0, 5.00, 20.00, 30, 0.001, 8, 12),
    // Earnings Alpha
    array('Earnings Alpha',           'Combines Earnings Drift + Beat Streak + Revision Momentum. Pure earnings edge exploitation.', 'earnings_alpha', 'Earnings Drift PEAD,Earnings Beat Streak,Revision Momentum', 10000, 0, 0, 8.00, 20.00, 42, 0.001, 10, 10),
    array('Earnings Drift Monthly',   'Post-earnings drift plays: buy after beats, hold 6-8 weeks for drift completion.', 'earnings_alpha', 'Earnings Drift PEAD', 10000, 0, 0, 10.00, 25.00, 42, 0.001, 15, 8),
    // Safe Bet / Quality
    array('Safe Bet Compounders',     'Dividend Aristocrats + Quality Compounder + Buyback Yield. The boring-but-works portfolio. Low turnover, high consistency.', 'safe_bet', 'Dividend Aristocrats,Quality Compounder,Share Buyback Yield', 10000, 0, 0, 999, 999, 252, 0.001, 33, 3),
    array('Quality + Value Momentum', 'Quality floor with value-momentum overlay. Avoids value traps. Targets 15%+ annual compounding.', 'quality', 'Quality Compounder,Value Momentum Combo', 10000, 0, 0, 10.00, 20.00, 60, 0.001, 15, 8),
    // Flow Intelligence
    array('Flow Intelligence',        'Dark Pool + Insider Cluster + Congressional trades. Follow the smart money.', 'flow', 'Insider Cluster Buy,Dark Pool Flow,Congressional Alpha', 10000, 0, 0, 8.00, 20.00, 30, 0.001, 10, 10),
    array('Insider + Earnings Combo', 'Insider buying confirmed by positive earnings trajectory. Double confirmation of undervaluation.', 'flow', 'Insider Cluster Buy,Earnings Beat Streak', 10000, 0, 0, 8.00, 20.00, 42, 0.001, 12, 8),
    // Regime Adaptive
    array('Regime Adaptive',          'Macro Regime + Volatility Filter. Switches strategies based on market conditions. Bull = momentum, Bear = quality/mean reversion.', 'regime', 'Macro Regime Adaptive,Volatility Regime Filter', 10000, 0, 0, 8.00, 20.00, 21, 0.001, 12, 8),
    array('All-Weather Hedge',        'Long quality + short momentum failures. Designed to perform in any market regime. Targets absolute returns.', 'hedged', 'Quality Compounder,Volatility Regime Filter,Inverse Technical Momentum', 10000, 0, 0, 10.00, 15.00, 30, 0.001, 10, 10),
    // Quantitative
    array('Factor Rank Top-K',        'Cross-sectional factor ranking: buy top-10 by composite score. Rebalance monthly. Academic factor investing.', 'quant', 'Cross-Sectional Ranker', 10000, 0, 0, 10.00, 20.00, 30, 0.001, 10, 10),
    array('Mean Reversion Scalp',     'Short-term reversal: buy oversold (z-score < -2), sell on bounce. 3-day hold max.', 'quant', 'Mean Reversion Z-Score', 10000, 0, 0, 3.00, 8.00, 3, 0.001, 15, 8),
    array('Sentiment + Flow',         'Sentiment velocity confirmed by dark pool accumulation. Social buzz + institutional backing = strong entry.', 'quant', 'Sentiment Velocity,Dark Pool Flow', 10000, 0, 0, 8.00, 20.00, 14, 0.001, 12, 8),
    // Risk-Adjusted / Kelly
    array('Kelly Criterion Optimal',  'Position sizes based on Kelly Criterion. Never risks >2% on momentum, allows 5% on Safe Bets. Mathematically optimal bet sizing.', 'risk_adjusted', 'Meta-Learner Arbitrator,Quality Compounder,Earnings Beat Streak', 10000, 0, 0, 8.00, 20.00, 21, 0.001, 8, 12),
    array('Volatility Targeted 10%',  'Targets 10% annual portfolio volatility. Scales position sizes inversely to recent volatility. Risk-parity approach.', 'risk_adjusted', 'Cross-Sectional Ranker,Quality Compounder', 10000, 0, 0, 10.00, 20.00, 30, 0.001, 10, 10),
    // ─── ALPHA FORGE PORTFOLIOS ───
    // Supply Chain & Macro
    array('Supply Chain Adaptive',    'Trades cyclicals/shippers based on BDI momentum and supply chain signals. Overweights when BDI inflects up.', 'alpha_forge', 'Supply Chain Monitor,Macro Regime Adaptive', 10000, 0, 0, 10.00, 20.00, 30, 0.001, 10, 10),
    array('Geopolitical Shield',      'Defensive allocation during high geopolitical risk. Quality + low GPR-exposure names.', 'alpha_forge', 'Geopolitical Risk Filter,Quality Compounder', 10000, 0, 0, 8.00, 15.00, 30, 0.001, 10, 10),
    // ESG & Human Capital
    array('Human Capital Alpha',      'Long companies with high + improving employee satisfaction. Georgetown study-backed four-factor alpha.', 'esg', 'Human Capital Quality,Quality Compounder', 10000, 0, 0, 10.00, 20.00, 60, 0.001, 15, 8),
    array('ESG + Quality',            'ESG momentum + quality fundamentals. Abnormal alpha from improving governance + strong culture.', 'esg', 'ESG Momentum,Quality Compounder,Dividend Aristocrats', 10000, 0, 0, 999, 999, 252, 0.001, 33, 3),
    array('Climate Risk Hedge',       'Avoids climate-exposed names, overweights climate-resilient quality companies.', 'esg', 'Climate Physical Risk,Quality Compounder', 10000, 0, 0, 10.00, 15.00, 60, 0.001, 12, 8),
    // Innovation
    array('Innovation + Growth',      'Patent surge + network effects. Forward-looking growth signals from IP filings and ecosystem health.', 'innovation', 'Patent Innovation Surge,Network Effect Mapper', 10000, 0, 0, 10.00, 25.00, 60, 0.001, 10, 10),
    // Enhanced Flow
    array('Deep Flow Intelligence',   'Dark pool microstructure + congressional negative trades + short squeeze detection. Maximum flow insight.', 'flow_deep', 'Dark Pool Microstructure,Congressional Negative,Short Squeeze Detector', 10000, 0, 0, 8.00, 20.00, 14, 0.001, 10, 10),
    array('Squeeze + Sentiment',      'Short squeeze candidates confirmed by sentiment velocity spikes. High-conviction reversal plays.', 'flow_deep', 'Short Squeeze Detector,Sentiment Velocity', 10000, 0, 0, 10.00, 30.00, 14, 0.001, 12, 8),
    // Multi-Factor Quant
    array('Multi-Factor Alpha',       'Multi-horizon momentum + accruals quality + beta decay + options skew. Pure quant factor combination.', 'quant_multi', 'Multi-Horizon Momentum,Accruals Quality,Beta Decay Monitor,Options Skew Sentiment', 10000, 0, 0, 10.00, 20.00, 30, 0.001, 10, 10),
    // The Ultimate Portfolio
    array('Alpha Forge Ultimate',     'The ultimate portfolio. All factor families combined via Alpha Forge Ensemble. Walk-forward validated, regime-weighted, Kelly-sized. Targets Sharpe >1.5.', 'alpha_forge', 'Alpha Forge Ensemble', 10000, 0, 0, 10.00, 25.00, 30, 0.001, 8, 12),
    array('Three-Sleeve Allocation',  'Momentum Hunters (40%) + Quality Compounders (40%) + Event Arbitrage (20%). Dynamic reallocation based on regime.', 'alpha_forge', 'Multi-Horizon Momentum,Quality Compounder,Earnings Drift PEAD,Insider Cluster Buy', 10000, 0, 0, 10.00, 20.00, 30, 0.001, 10, 10),
    // ─── RESEARCH-BACKED ACADEMIC PORTFOLIOS ───
    // Factor Zoo: Pure Factor Portfolios
    array('Academic Factor Zoo',       'All 30+ academic factors combined. GP/A, Piotroski, BAB, IVOL, momentum variants, seasonals, behavioral. Maximum factor diversification.', 'factor_zoo', 'Gross Profitability Premium,Piotroski F-Score,Betting Against Beta (BAB),Quality Minus Junk (QMJ),Factor Momentum,Time-Series Momentum', 10000, 0, 0, 10.00, 20.00, 30, 0.001, 8, 12),
    array('Quality Factor Pure',       'Pure quality factor: GP/A + Piotroski F-Score + QMJ + Accruals Quality. Academically-backed quality investing.', 'academic', 'Gross Profitability Premium,Piotroski F-Score,Quality Minus Junk (QMJ),Accruals Anomaly Enhanced', 10000, 0, 0, 10.00, 20.00, 60, 0.001, 15, 8),
    array('Value + Profitability',     'Novy-Marx insight: Value (low P/B) combined with Profitability (high GP/A). Negatively correlated factors = superior risk-adjusted returns.', 'academic', 'Gross Profitability Premium,Value Composite Sector-Neutral,Intangible Value Factor', 10000, 0, 0, 10.00, 20.00, 60, 0.001, 12, 8),
    array('Low-Risk Anomaly',          'BAB + IVOL avoidance + low volatility. Exploits the low-risk anomaly: boring stocks outperform on a risk-adjusted basis.', 'academic', 'Betting Against Beta (BAB),IVOL Anomaly,MAX Effect Avoidance', 10000, 0, 0, 8.00, 15.00, 60, 0.001, 10, 10),
    array('Shareholder Yield Kings',   'Combined dividend + buyback + debt paydown. Companies returning maximum cash to shareholders. Faber-style.', 'academic', 'Shareholder Yield Composite,Dividend Aristocrats,Share Buyback Yield', 10000, 0, 0, 999, 999, 252, 0.001, 33, 3),
    // Momentum Variants Portfolio
    array('Momentum Zoo',              'All momentum variants: cross-sectional, time-series, factor momentum, multi-horizon. Maximum momentum exposure with diversification.', 'academic', 'Factor Momentum,Time-Series Momentum,Multi-Horizon Momentum,Short-Term Reversal', 10000, 0, 0, 10.00, 25.00, 21, 0.001, 10, 10),
    array('Contrarian Long-Term',      'Long-term reversal + value composite. Patient 1-year+ contrarian bets on 3-5 year losers. DeBondt-Thaler style.', 'academic', 'Long-Term Reversal,Value Composite Sector-Neutral,Piotroski F-Score', 10000, 0, 0, 999, 999, 252, 0.001, 10, 10),
    // Seasonal / Calendar Portfolios
    array('Seasonal Overlay',          'Halloween + Turn of Month + Overnight. Calendar-based timing overlay for any portfolio. Reduces drawdowns.', 'seasonal', 'Halloween Effect,Turn of Month,Overnight Momentum,Seasonal Calendar', 10000, 0, 0, 10.00, 15.00, 30, 0.001, 10, 10),
    // Event-Driven
    array('Event Arbitrage',           'Merger Arb + Spin-Off + Earnings Drift. Pure event-driven alpha. Uncorrelated to market direction.', 'event_driven', 'Merger Arbitrage,Spin-Off Alpha,Earnings Drift PEAD', 10000, 0, 0, 10.00, 20.00, 60, 0.001, 10, 10),
    // Quant Fund Replication
    array('Renaissance Lite',          'HMM regime detection + WorldQuant formulaic alphas + factor crowding monitor. Simplified quant fund approach.', 'quant_fund', 'HMM Regime Detector,WorldQuant Formulaic Alpha,Factor Crowding Monitor', 10000, 0, 0, 10.00, 25.00, 21, 0.001, 10, 10),
    array('Risk Parity All Weather',   'Bridgewater All Weather: equal risk across assets. Risk Parity + HRP for robust allocation.', 'quant_fund', 'Risk Parity Balanced,Hierarchical Risk Parity', 10000, 0, 0, 999, 999, 60, 0.001, 25, 4),
    array('CTA Trend Following',       'Managed futures style: trend following across multiple timeframes. Crisis alpha + positive convexity.', 'quant_fund', 'Trend Following CTA,Time-Series Momentum,Global Tactical Allocation', 10000, 0, 0, 10.00, 25.00, 30, 0.001, 10, 10),
    // Cross-Asset
    array('Cross-Asset Diversified',   'Carry + Trend + Value across asset classes. Maximum strategy diversification for Sharpe >1.0.', 'cross_asset', 'Cross-Asset Carry,Trend Following CTA,Global Tactical Allocation,Risk Parity Balanced', 10000, 0, 0, 10.00, 20.00, 30, 0.001, 10, 10),
    // Behavioral Alpha
    array('Behavioral Alpha',          'Disposition Effect + Earnings Call Sentiment + Earnings Drift. Exploits systematic human biases in markets.', 'behavioral', 'Disposition Effect Drift,Earnings Call Sentiment,Earnings Drift PEAD,Sentiment Velocity', 10000, 0, 0, 10.00, 20.00, 30, 0.001, 10, 10),
    // The Ultimate Academic Portfolio
    array('Academic All-Star',         'Best of academia: GP/A + BAB + Piotroski + momentum + seasonal overlay + regime detection. 50+ years of peer-reviewed alpha sources.', 'ultimate', 'Gross Profitability Premium,Betting Against Beta (BAB),Piotroski F-Score,Factor Momentum,Halloween Effect,HMM Regime Detector,Quality Minus Junk (QMJ)', 10000, 0, 0, 10.00, 25.00, 30, 0.001, 7, 14),
    // ─── NO-BED-TIME PORTFOLIOS ───
    array('No-Bed-Time Standard',    'Dual consensus (Cursor Genius + Composite Rating agree). Tight stops, proven winners only. The safest aggressive approach.', 'nobed', 'No-Bed-Time Core', 10000, 0, 0, 5.00, 20.00, 14, 0.001, 10, 10),
    array('No-Bed-Time Full Suite',  'All 5 NoBedTime algorithms combined. Meta-ensemble with regime sentinel, overnight premium, contrarian bounces, and dual consensus. The never-sleeping portfolio.', 'nobed', 'No-Bed-Time Insomniac,No-Bed-Time Core,No-Bed-Time Nighthawk,No-Bed-Time Sentinel,No-Bed-Time Contrarian', 10000, 0, 0, 8.00, 25.00, 14, 0.001, 8, 12),
    array('No-Bed-Time + Quality',   'NoBedTime consensus filtered through quality compounders. Triple confirmation: AI picks + composite score + quality fundamentals.', 'nobed', 'No-Bed-Time Core,Quality Compounder,Dividend Aristocrats', 10000, 0, 0, 10.00, 20.00, 60, 0.001, 10, 10),
    array('No-Bed-Time Overnight',   'Pure overnight premium capture. Enter at close, exit at open. Requires bullish Cursor Genius signal + RSI<65 + volume confirmation.', 'nobed', 'No-Bed-Time Nighthawk', 10000, 0, 0, 3.00, 5.00, 1, 0.001, 20, 5)
);

$port_count = 0;
foreach ($portfolios as $p) {
    $pname = $conn->real_escape_string($p[0]);
    $pdesc = $conn->real_escape_string($p[1]);
    $stype = $conn->real_escape_string($p[2]);
    $afilt = $conn->real_escape_string($p[3]);
    $cap   = (float)$p[4];
    $cb    = (float)$p[5];
    $cs    = (float)$p[6];
    $sl    = (float)$p[7];
    $tp    = (float)$p[8];
    $mhd   = (int)$p[9];
    $slip  = (float)$p[10];
    $psz   = (float)$p[11];
    $mpos  = (int)$p[12];

    $chk = $conn->query("SELECT id FROM portfolios WHERE name='$pname'");
    if ($chk && $chk->num_rows == 0) {
        $sql = "INSERT INTO portfolios (name, description, strategy_type, algorithm_filter, initial_capital, commission_buy, commission_sell, stop_loss_pct, take_profit_pct, max_hold_days, slippage_pct, position_size_pct, max_positions, created_at)
                VALUES ('$pname','$pdesc','$stype','$afilt',$cap,$cb,$cs,$sl,$tp,$mhd,$slip,$psz,$mpos,'$now')";
        if ($conn->query($sql)) {
            $port_count++;
        }
    }
}
$results['actions'][] = 'Seeded ' . $port_count . ' portfolio templates';

// Log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$ip = $conn->real_escape_string($ip);
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('setup_schema', 'Schema v2 created/verified', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
