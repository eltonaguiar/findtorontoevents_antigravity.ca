<?php
/**
 * Setup database schema for Stock Portfolio Analysis
 * Run once via HTTP to create all tables.
 * PHP 5.2 compatible.
 *
 * Usage: GET https://findtorontoevents.ca/findstocks/api/setup_schema.php
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

// 4. Stock picks from our algorithms
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

// 5. Portfolio definitions
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
    total_trades INT NOT NULL DEFAULT 0,
    winning_trades INT NOT NULL DEFAULT 0,
    losing_trades INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_win_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_loss_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    max_drawdown_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    total_commissions DECIMAL(12,2) NOT NULL DEFAULT 0,
    sharpe_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
    sortino_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
    profit_factor DECIMAL(10,4) NOT NULL DEFAULT 0,
    expectancy DECIMAL(10,4) NOT NULL DEFAULT 0,
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

// 9. Audit log for trust/compliance
"CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    KEY idx_action (action_type),
    KEY idx_date (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 10. Market regime tracking (bull/bear/sideways)
"CREATE TABLE IF NOT EXISTS market_regimes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    spy_close DECIMAL(10,2) NOT NULL DEFAULT 0,
    spy_sma200 DECIMAL(10,2) NOT NULL DEFAULT 0,
    vix_close DECIMAL(10,2) NOT NULL DEFAULT 0,
    regime VARCHAR(20) NOT NULL DEFAULT 'unknown',
    UNIQUE KEY idx_date (trade_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8"

);

foreach ($tables as $sql) {
    if ($conn->query($sql)) {
        // Extract table name from SQL
        $matches = array();
        preg_match('/CREATE TABLE IF NOT EXISTS (\w+)/', $sql, $matches);
        $tname = isset($matches[1]) ? $matches[1] : 'unknown';
        $results['actions'][] = 'OK: ' . $tname;
    } else {
        $results['ok'] = false;
        $results['actions'][] = 'FAIL: ' . $conn->error;
    }
}

// ─── Seed default algorithms ───
$algos = array(
    array('CAN SLIM',              'CAN SLIM',   "O'Neil growth screener. RS Rating, Stage-2 Uptrend, 52W High.", 'growth',       '3m'),
    array('CAN SLIM + 1',          'CAN SLIM',   'CAN SLIM variant with additional momentum filter.',             'growth',       '3m'),
    array('CAN SLIM + 2',          'CAN SLIM',   'CAN SLIM variant with sector rotation.',                        'growth',       '3m'),
    array('CAN SLIM + 3',          'CAN SLIM',   'CAN SLIM variant with macro overlay.',                          'growth',       '3m'),
    array('Technical Momentum',     'Technical',  'Volume surge, RSI, breakouts, Bollinger squeeze.',              'momentum',     '3d'),
    array('Technical Momentum + 1', 'Technical',  'Technical Momentum with enhanced volume filter.',               'momentum',     '3d'),
    array('Technical Momentum + 2', 'Technical',  'Technical Momentum with volatility-adjusted targets.',          'momentum',     '7d'),
    array('Composite Rating',       'Composite',  'Multi-factor: technicals, volume, fundamentals, regime.',       'multi_factor', '1m'),
    array('ML Ensemble',            'ML',         'XGBoost + Gradient Boosting for next-day returns.',             'ml',           '3d'),
    array('Statistical Arbitrage',  'StatArb',    'Pairs mean reversion: z-score spread, Sharpe/return.',          'stat_arb',     '7d'),
    array('Alpha Predator',         'Alpha',      'Momentum-based with regime awareness.',                         'momentum',     '3d'),
    array('Penny Sniper',           'Penny',      'High-risk penny stock screener.',                               'speculative',  '24h'),
    array('Penny Sniper + 2',       'Penny',      'Penny Sniper with volume confirmation.',                        'speculative',  '24h'),
    array('Blue Chip Growth',       'Blue Chip',  'Large-cap consistent growers: dividend aristocrats, mega-cap wide-moat stocks with 10+ yr track records.', 'value_growth', '3m'),
    array('Cursor Genius',          'Meta',       'Data-driven meta-strategy. Eliminates underperformers, overweights winners, buys dips from 20-day highs with MA50 trend confirmation. 15 tickers across 3 tiers.', 'data_driven', '90d'),
    array('ETF Masters',            'ETF',        'Diversified ETF portfolio: core index (SPY/QQQ/VTI), growth (VGT/SOXX), income (SCHD/VYM), defensive (TLT/GLD/BND), international (EFA/VWO/INDA).', 'passive_index', '90d'),
    array('Sector Rotation',        'Sector',     'Equal-weight allocation across all 11 GICS sectors via Select Sector SPDRs. Monthly DCA. Maximum diversification, no sector bias.', 'diversified', '90d'),
    array('Sector Momentum',        'Sector',     'News/macro-driven rotation. Ranks 11 sectors by 60-day return, enters top 4 momentum sectors each month. Rides sector catalysts.', 'momentum_rotation', '30d'),
    // ── Alternative Data & Human Capital ──
    array('Human Capital Alpha',    'AltData',    'Georgetown-backed: long firms with high/improving Glassdoor ratings. Culture+leadership composite. 4-factor alpha documented.', 'quality', '6m'),
    array('Culture Momentum',       'AltData',    'Tracks 6-12mo change in employee satisfaction. Shock events (large rating moves) trigger entries. Penalizes culture downgrades.', 'momentum', '3m'),
    array('ESG Quality Composite',  'ESG',        'Combined ESG score + employee satisfaction + low controversy velocity. AlphaArchitect study-backed. Long quality, avoid junk.', 'quality', '1y'),
    array('Climate Risk Filter',    'ESG',        'Limits exposure to physically climate-exposed names. Emissions intensity, storm/flood/fire zone risk. Seasonal stress flags.', 'risk_filter', '6m'),
    array('ESG Momentum',           'ESG',        'Trend in ESG ratings improvement. Rising ESG + quality fundamentals. Forward-looking responsible investing alpha.', 'momentum', '6m'),
    // ── Supply Chain & Macro ──
    array('BDI Cyclical Swing',     'SupplyChain','Baltic Dry Index regime-driven. Long cyclicals/shippers when BDI inflects up from depressed. Haircut when BDI collapses.', 'regime_macro', '30d'),
    array('Freight Bottleneck',     'SupplyChain','Supply-tight vs supply-slack flags. Freight rates + port congestion. Pushes toward/away from exporters and industrials.', 'regime_macro', '30d'),
    array('Supply Chain Composite', 'SupplyChain','Combines BDI, freight indices, container rates. Rolling correlation per stock. Industry/region sensitivity mapping.', 'multi_factor', '3m'),
    // ── Geopolitical Risk ──
    array('GPR Defensive',          'Geopolitical','Caldara-Iacoviello GPR index. High GPR overweights quality/defensive, underweights cyclical momentum. Documented equity effect.', 'regime_macro', '30d'),
    array('Sanctions Avoidance',    'Geopolitical','Flags firms with high revenue exposure to sanctioned or conflict regions. Forces smaller sizes or avoid list. Event-driven.', 'risk_filter', '30d'),
    array('Geopolitical Regime',    'Geopolitical','GPR high/low regime switching. Low GPR favors momentum/event-arb. High GPR favors quality/defensive/low-beta.', 'regime_macro', '3m'),
    // ── Institutional Flow / Dark Pool ──
    array('Deep Flow Scanner',      'InstFlow',   'Dark pool volume as pct of consolidated volume. Spike detection + clustering zones. Bookmap-style institutional footprints.', 'flow', '14d'),
    array('Block Trade Momentum',   'InstFlow',   'Tracks repeated block prints at similar levels. Large institutional positions create hidden support/resistance. Requires supportive flow for entry.', 'flow', '14d'),
    array('Congressional Alpha',    'InstFlow',   'Nuanced Congress trades. Harvard study: negative trades earn abnormal returns. Long trades weaker. Committee jurisdiction weight.', 'event_arb', '15d'),
    array('Congressional Short',    'InstFlow',   'Focuses on negative Congressional trades as explicit downside signals. 10-15 trading day event window. Harvard Law documented edge.', 'event_arb', '15d'),
    array('Insider Cluster',        'InstFlow',   'Form 4 cluster buys: multiple insiders buying same name within 2 weeks. Stronger signal than single insider buy.', 'event_arb', '30d'),
    // ── Patent / IP & Innovation ──
    array('Patent Surge Growth',    'Innovation', 'Patent count growth vs 3-5yr history. Citation-weighted. Entry into new CPC technology classes. Forward-looking growth proxy.', 'growth', '6m'),
    array('Innovation Compounder',  'Innovation', 'High and consistent patent output + quality fundamentals. Rewards multi-year compounders. Penalizes high-innovation cash burners.', 'quality_growth', '1y'),
    array('Network Effect Moat',    'Innovation', 'Identifies firms with strengthening network effects via patent clusters, platform metrics, and user-base growth indicators.', 'growth', '1y'),
    // ── Multi-Sleeve Ensembles ──
    array('Alpha Forge Ultimate',   'AlphaForge', 'Ultimate ensemble: all 7 factor families. Human capital + BDI + GPR + dark pool + ESG + patents + academic factors. Regime-weighted, Kelly-sized.', 'ensemble', '30d'),
    array('Three Sleeve Plus',      'AlphaForge', 'Enhanced 3-sleeve: Momentum 35% + Quality 35% + Event 20% + Alt-Data overlay 10%. Uses culture, GPR, BDI as regime filters.', 'ensemble', '30d'),
    array('Quality Compounder',     'AlphaForge', 'Requires: high Glassdoor + low controversy + strong patents + Piotroski F>=7. The ultimate quality filter. Long-only compounders.', 'quality', '1y'),
    array('Macro Regime Switcher',  'AlphaForge', 'Combines VIX + BDI + GPR + DXY + yield curve into unified regime model. Switches between momentum, quality, and defensive sleeves.', 'regime_macro', '30d'),
    // ── Alpha Forge Sleeve-Specific ──
    array('AF Momentum Hunter',     'AlphaForge', 'Multi-horizon momentum (5d/20d/60d composite) with volume surge confirmation and ATR trailing stops. Regime-aware: scales down in bear/high-vol. Kelly-sized, 3% max per position.', 'momentum', '20d'),
    array('AF Event Arbitrage',     'AlphaForge', 'Earnings drift + volume anomaly plays. Targets post-catalyst momentum with tight risk (2% position, 10% SL). Captures PEAD and insider cluster signals.', 'event_driven', '40d'),
    array('AF Mean Reversion',      'AlphaForge', 'Z-score < -2 oversold bounces with volume confirmation. Quick 5-10 day holds targeting mean reversion. Scales up in low-vol regimes where reversion is reliable.', 'mean_reversion', '10d'),
    array('AF Sector Relative',     'AlphaForge', 'Cross-sectional strength: buys stocks outperforming their sector ETF over 60d. Filters by liquidity (Amihud) and tail risk. Captures relative alpha vs beta.', 'cross_sectional', '30d'),
    array('AF Meta Ensemble',       'AlphaForge', 'Regime-aware meta-allocator. Dynamically weights Momentum/Quality/Event sleeves based on 4-quadrant regime (Bull-Bear x High-Low Vol). Targets 12-15% portfolio vol with risk parity overlay.', 'meta_ensemble', '90d'),
    // ── Research-Backed Academic Algorithms (2024-2025 Papers) ──
    array('PEAD Earnings Drift',    'Academic',   'Post-Earnings Announcement Drift: 60-90 day price continuation after earnings surprises. Ball & Brown (1968), Bernard & Thomas (1989). 2024: 6.78% quarterly alpha. Factor-model-independent anomaly.', 'event_arb', '90d'),
    array('13F Hedge Fund Clone',   'Academic',   'Clones top-quartile hedge fund 13F holdings. 2024 research: 24.3% annualized risk-adjusted alpha. ML-enhanced 13F features achieve 15-19.8% annualized returns.', 'smart_money', '90d'),
    array('Sentiment Alpha',        'Academic',   'NLP/LLM sentiment from news, earnings calls, social media. 2024: 35.56% annualized, Sharpe 2.21. Reddit/Twitter 70-84% above buy-and-hold. Event-aware IC > 0.05.', 'sentiment', '30d'),
    array('Risk Parity HRP',        'Academic',   'Hierarchical Risk Parity: equal risk contribution across uncorrelated assets. Lopez de Prado (2016). 2024: less noisy weights than Markowitz. Schur Complementary Allocation.', 'risk_parity', '90d'),
    array('Multi-Factor AIPT',      'Academic',   'Artificial Intelligence Pricing Theory: many factors via nonlinear combination. SSRN 4971349 (2024): large factor models dominate sparse APT. 8 factor families. R-sq > 22%.', 'multi_factor', '30d'),
    array('Overnight Return Alpha', 'Academic',   'Overnight return (close-to-open) premium as institutional accumulation proxy. 2024: off-hours info flow with 6.78% quarterly alpha. Distinct from intraday momentum.', 'overnight', '14d'),
    array('Firm-Specific Momentum', 'Academic',   'Firm-specific momentum isolated from systematic/sector momentum. Schmid et al (Dec 2024): firm components drive stock momentum. Company catalysts = purer momentum, lower reversal risk.', 'momentum', '30d')
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

// ─── Seed default portfolio templates ───
$now = date('Y-m-d H:i:s');
$portfolios = array(
    array('Day Trader (EOD Exit)',       'daytrader',    '',  10000, 10, 10, 3.00, 5.00,   1, 0.005),
    array('Day Trader (2-Day Max)',      'daytrader',    '',  10000, 10, 10, 5.00, 10.00,  2, 0.005),
    array('Weekly Swing (10% Target)',   'swing',        '',  10000, 10, 10, 5.00, 10.00,  7, 0.005),
    array('Weekly Swing (20% Target)',   'swing',        '',  10000, 10, 10, 8.00, 20.00,  7, 0.005),
    array('Conservative Hold',           'conservative', '',  10000, 10, 10, 5.00, 10.00, 30, 0.005),
    array('Aggressive Hold',             'aggressive',   '',  10000, 10, 10, 15.00, 30.00, 90, 0.005),
    array('Buy and Hold (6 Months)',     'buy_hold',     '',  10000, 10, 10, 20.00, 50.00, 180, 0.005),
    array('CAN SLIM Only',              'single_algo',  'CAN SLIM,CAN SLIM + 1,CAN SLIM + 2,CAN SLIM + 3', 10000, 10, 10, 5.00, 15.00, 30, 0.005),
    array('Tech Momentum Only',         'single_algo',  'Technical Momentum,Technical Momentum + 1,Technical Momentum + 2', 10000, 10, 10, 5.00, 10.00, 7, 0.005),
    array('Diversified (One Per Algo)',  'diversified',  '',  10000, 10, 10, 5.00, 15.00, 14, 0.005),
    array('Penny Sniper Only',          'single_algo',  'Penny Sniper,Penny Sniper + 2', 10000, 10, 10, 10.00, 20.00, 3, 0.005),
    array('Alpha Predator Only',        'single_algo',  'Alpha Predator', 10000, 10, 10, 5.00, 15.00, 7, 0.005),
    // ── Alt-Data & Factor Portfolios ──
    array('Human Capital Alpha (6M)',   'alt_data',     'Human Capital Alpha,Culture Momentum', 10000, 0, 0, 10.00, 25.00, 126, 0.005),
    array('ESG + Quality Annual',       'alt_data',     'ESG Quality Composite,ESG Momentum,Climate Risk Filter', 10000, 0, 0, 20.00, 999.00, 252, 0.005),
    array('Supply Chain Swing',         'macro',        'BDI Cyclical Swing,Freight Bottleneck,Supply Chain Composite', 10000, 10, 10, 8.00, 20.00, 30, 0.005),
    array('Geopolitical Defensive',     'macro',        'GPR Defensive,Sanctions Avoidance,Geopolitical Regime', 10000, 10, 10, 8.00, 15.00, 30, 0.005),
    array('Deep Institutional Flow',    'flow',         'Deep Flow Scanner,Block Trade Momentum,Congressional Alpha,Insider Cluster', 10000, 0, 0, 8.00, 20.00, 14, 0.005),
    array('Innovation Growth (6M)',     'growth',       'Patent Surge Growth,Innovation Compounder,Network Effect Moat', 10000, 10, 10, 12.00, 30.00, 126, 0.005),
    array('Quality Compounder (1Y)',    'quality',      'Quality Compounder', 10000, 0, 0, 15.00, 999.00, 252, 0.005),
    array('Alpha Forge Ultimate',       'ensemble',     'Alpha Forge Ultimate,Three Sleeve Plus,Macro Regime Switcher', 10000, 0, 0, 8.00, 25.00, 30, 0.005),
    array('Congressional Shorts Only',  'event_arb',    'Congressional Short', 10000, 0, 0, 5.00, 15.00, 15, 0.005),
    array('Full Factor Zoo + Alt',      'diversified',  '', 10000, 10, 10, 8.00, 20.00, 30, 0.005),
    // ── Research-Backed Academic Portfolios (2024-2025) ──
    array('PEAD Earnings Drift (90D)', 'academic',    'PEAD Earnings Drift', 10000, 0, 0, 10.00, 30.00, 90, 0.005),
    array('13F Smart Money Clone',     'academic',    '13F Hedge Fund Clone', 10000, 0, 0, 12.00, 40.00, 90, 0.005),
    array('Sentiment Alpha (30D)',     'academic',    'Sentiment Alpha', 10000, 0, 0, 8.00, 20.00, 30, 0.005),
    array('Risk Parity All-Weather',   'academic',    'Risk Parity HRP', 10000, 0, 0, 15.00, 999.00, 90, 0.005),
    array('AIPT Multi-Factor',         'academic',    'Multi-Factor AIPT', 10000, 0, 0, 8.00, 25.00, 30, 0.005),
    array('Overnight Gaps (14D)',      'academic',    'Overnight Return Alpha', 10000, 10, 10, 5.00, 12.00, 14, 0.005),
    array('Firm Catalyst Momentum',    'academic',    'Firm-Specific Momentum', 10000, 0, 0, 8.00, 20.00, 30, 0.005),
    array('Academic Research Blend',   'academic',    'PEAD Earnings Drift,13F Hedge Fund Clone,Sentiment Alpha,Multi-Factor AIPT,Firm-Specific Momentum', 10000, 0, 0, 10.00, 25.00, 60, 0.005),
    array('Full Academic + Alt Zoo',   'diversified', 'PEAD Earnings Drift,13F Hedge Fund Clone,Sentiment Alpha,Risk Parity HRP,Multi-Factor AIPT,Overnight Return Alpha,Firm-Specific Momentum', 10000, 0, 0, 10.00, 30.00, 60, 0.005)
);

$port_count = 0;
foreach ($portfolios as $p) {
    $pname   = $conn->real_escape_string($p[0]);
    $stype   = $conn->real_escape_string($p[1]);
    $afilt   = $conn->real_escape_string($p[2]);
    $cap     = (float)$p[3];
    $cb      = (float)$p[4];
    $cs      = (float)$p[5];
    $sl      = (float)$p[6];
    $tp      = (float)$p[7];
    $mhd     = (int)$p[8];
    $slip    = (float)$p[9];

    $chk = $conn->query("SELECT id FROM portfolios WHERE name='$pname'");
    if ($chk && $chk->num_rows == 0) {
        $sql = "INSERT INTO portfolios (name, strategy_type, algorithm_filter, initial_capital, commission_buy, commission_sell, stop_loss_pct, take_profit_pct, max_hold_days, slippage_pct, created_at)
                VALUES ('$pname','$stype','$afilt',$cap,$cb,$cs,$sl,$tp,$mhd,$slip,'$now')";
        if ($conn->query($sql)) {
            $port_count++;
        }
    }
}
$results['actions'][] = 'Seeded ' . $port_count . ' portfolio templates';

// ─── Kimi: Add composite indexes for common query patterns ───
$composite_indexes = array(
    "CREATE INDEX idx_algo_date ON stock_picks (algorithm_name, pick_date)",
    "CREATE INDEX idx_ticker_pickdate ON stock_picks (ticker, pick_date)",
    "CREATE INDEX idx_ticker_tradedate ON daily_prices (ticker, trade_date)"
);
foreach ($composite_indexes as $idx_sql) {
    // Ignore errors (index may already exist)
    $conn->query($idx_sql);
}
$results['actions'][] = 'Composite indexes ensured';

// Log this setup
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$ip = $conn->real_escape_string($ip);
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('setup_schema', 'Schema created/verified', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
