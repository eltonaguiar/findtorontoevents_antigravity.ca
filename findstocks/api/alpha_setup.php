<?php
/**
 * Alpha Suite - Schema Setup & Universe Seeding
 * Creates alpha_* tables and seeds 50-stock universe across all sectors.
 * PHP 5.2 compatible. Idempotent (safe to run multiple times).
 *
 * Usage: GET /findstocks/api/alpha_setup.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'actions' => array(), 'errors' => array());

/* ================================================================
   TABLE DEFINITIONS
   ================================================================ */
$tables = array(

// 1. Stock universe for alpha analysis
"CREATE TABLE IF NOT EXISTS alpha_universe (
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(200) NOT NULL DEFAULT '',
    sector VARCHAR(100) NOT NULL DEFAULT '',
    industry VARCHAR(200) NOT NULL DEFAULT '',
    market_cap_tier VARCHAR(20) NOT NULL DEFAULT 'large',
    added_date DATE NOT NULL,
    active TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (ticker),
    KEY idx_sector (sector),
    KEY idx_active (active)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 2. Fundamental data snapshots from Yahoo Finance
"CREATE TABLE IF NOT EXISTS alpha_fundamentals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    fetch_date DATE NOT NULL,
    market_cap DECIMAL(20,2) NOT NULL DEFAULT 0,
    pe_trailing DECIMAL(12,4) NOT NULL DEFAULT 0,
    pe_forward DECIMAL(12,4) NOT NULL DEFAULT 0,
    peg_ratio DECIMAL(12,4) NOT NULL DEFAULT 0,
    price_to_book DECIMAL(12,4) NOT NULL DEFAULT 0,
    price_to_sales DECIMAL(12,4) NOT NULL DEFAULT 0,
    ev_to_ebitda DECIMAL(12,4) NOT NULL DEFAULT 0,
    return_on_equity DECIMAL(12,4) NOT NULL DEFAULT 0,
    return_on_assets DECIMAL(12,4) NOT NULL DEFAULT 0,
    gross_margins DECIMAL(12,4) NOT NULL DEFAULT 0,
    operating_margins DECIMAL(12,4) NOT NULL DEFAULT 0,
    profit_margins DECIMAL(12,4) NOT NULL DEFAULT 0,
    revenue_growth DECIMAL(12,4) NOT NULL DEFAULT 0,
    earnings_growth DECIMAL(12,4) NOT NULL DEFAULT 0,
    total_debt DECIMAL(20,2) NOT NULL DEFAULT 0,
    total_cash DECIMAL(20,2) NOT NULL DEFAULT 0,
    debt_to_equity DECIMAL(12,4) NOT NULL DEFAULT 0,
    current_ratio DECIMAL(12,4) NOT NULL DEFAULT 0,
    free_cashflow DECIMAL(20,2) NOT NULL DEFAULT 0,
    operating_cashflow DECIMAL(20,2) NOT NULL DEFAULT 0,
    dividend_yield DECIMAL(12,6) NOT NULL DEFAULT 0,
    payout_ratio DECIMAL(12,4) NOT NULL DEFAULT 0,
    shares_outstanding BIGINT NOT NULL DEFAULT 0,
    beta DECIMAL(12,4) NOT NULL DEFAULT 0,
    fifty_two_week_high DECIMAL(12,4) NOT NULL DEFAULT 0,
    fifty_two_week_low DECIMAL(12,4) NOT NULL DEFAULT 0,
    fifty_day_avg DECIMAL(12,4) NOT NULL DEFAULT 0,
    two_hundred_day_avg DECIMAL(12,4) NOT NULL DEFAULT 0,
    avg_volume BIGINT NOT NULL DEFAULT 0,
    regular_market_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    raw_json TEXT,
    UNIQUE KEY idx_ticker_date (ticker, fetch_date),
    KEY idx_date (fetch_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 3. Earnings history and surprises
"CREATE TABLE IF NOT EXISTS alpha_earnings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    quarter_end DATE NOT NULL,
    eps_actual DECIMAL(12,4) NOT NULL DEFAULT 0,
    eps_estimate DECIMAL(12,4) NOT NULL DEFAULT 0,
    eps_surprise DECIMAL(12,4) NOT NULL DEFAULT 0,
    surprise_pct DECIMAL(12,4) NOT NULL DEFAULT 0,
    fetch_date DATE NOT NULL,
    UNIQUE KEY idx_ticker_quarter (ticker, quarter_end),
    KEY idx_ticker (ticker),
    KEY idx_date (fetch_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 4. Macro regime data (daily)
"CREATE TABLE IF NOT EXISTS alpha_macro (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trade_date DATE NOT NULL,
    vix_close DECIMAL(12,4) NOT NULL DEFAULT 0,
    spy_close DECIMAL(12,4) NOT NULL DEFAULT 0,
    spy_sma50 DECIMAL(12,4) NOT NULL DEFAULT 0,
    spy_sma200 DECIMAL(12,4) NOT NULL DEFAULT 0,
    tnx_close DECIMAL(12,4) NOT NULL DEFAULT 0,
    two_yr_yield DECIMAL(12,4) NOT NULL DEFAULT 0,
    yield_spread DECIMAL(12,4) NOT NULL DEFAULT 0,
    dxy_close DECIMAL(12,4) NOT NULL DEFAULT 0,
    dxy_sma50 DECIMAL(12,4) NOT NULL DEFAULT 0,
    regime VARCHAR(50) NOT NULL DEFAULT 'unknown',
    regime_score INT NOT NULL DEFAULT 0,
    regime_detail TEXT,
    UNIQUE KEY idx_date (trade_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 5. Computed factor scores per ticker per date
"CREATE TABLE IF NOT EXISTS alpha_factor_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    score_date DATE NOT NULL,
    momentum_12m DECIMAL(12,4) NOT NULL DEFAULT 0,
    momentum_6m DECIMAL(12,4) NOT NULL DEFAULT 0,
    momentum_3m DECIMAL(12,4) NOT NULL DEFAULT 0,
    momentum_1m DECIMAL(12,4) NOT NULL DEFAULT 0,
    momentum_score DECIMAL(12,4) NOT NULL DEFAULT 0,
    momentum_rank INT NOT NULL DEFAULT 0,
    quality_roe DECIMAL(12,4) NOT NULL DEFAULT 0,
    quality_margins DECIMAL(12,4) NOT NULL DEFAULT 0,
    quality_fcf_yield DECIMAL(12,4) NOT NULL DEFAULT 0,
    quality_debt DECIMAL(12,4) NOT NULL DEFAULT 0,
    quality_score DECIMAL(12,4) NOT NULL DEFAULT 0,
    quality_rank INT NOT NULL DEFAULT 0,
    value_pe DECIMAL(12,4) NOT NULL DEFAULT 0,
    value_pb DECIMAL(12,4) NOT NULL DEFAULT 0,
    value_ps DECIMAL(12,4) NOT NULL DEFAULT 0,
    value_div_yield DECIMAL(12,6) NOT NULL DEFAULT 0,
    value_score DECIMAL(12,4) NOT NULL DEFAULT 0,
    value_rank INT NOT NULL DEFAULT 0,
    earnings_surprise_avg DECIMAL(12,4) NOT NULL DEFAULT 0,
    earnings_beat_rate DECIMAL(12,4) NOT NULL DEFAULT 0,
    earnings_growth_rate DECIMAL(12,4) NOT NULL DEFAULT 0,
    earnings_score DECIMAL(12,4) NOT NULL DEFAULT 0,
    earnings_rank INT NOT NULL DEFAULT 0,
    vol_realized_60d DECIMAL(12,4) NOT NULL DEFAULT 0,
    vol_beta DECIMAL(12,4) NOT NULL DEFAULT 0,
    vol_max_dd_90d DECIMAL(12,4) NOT NULL DEFAULT 0,
    vol_score DECIMAL(12,4) NOT NULL DEFAULT 0,
    vol_rank INT NOT NULL DEFAULT 0,
    growth_revenue DECIMAL(12,4) NOT NULL DEFAULT 0,
    growth_earnings DECIMAL(12,4) NOT NULL DEFAULT 0,
    growth_score DECIMAL(12,4) NOT NULL DEFAULT 0,
    growth_rank INT NOT NULL DEFAULT 0,
    composite_score DECIMAL(12,4) NOT NULL DEFAULT 0,
    composite_rank INT NOT NULL DEFAULT 0,
    regime_adj_score DECIMAL(12,4) NOT NULL DEFAULT 0,
    regime_adj_rank INT NOT NULL DEFAULT 0,
    factors_json TEXT,
    UNIQUE KEY idx_ticker_date (ticker, score_date),
    KEY idx_date (score_date),
    KEY idx_composite (composite_rank),
    KEY idx_regime (regime_adj_rank)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 6. Alpha strategy picks
"CREATE TABLE IF NOT EXISTS alpha_picks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    pick_date DATE NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    score DECIMAL(12,4) NOT NULL DEFAULT 0,
    conviction VARCHAR(20) NOT NULL DEFAULT 'medium',
    expected_horizon VARCHAR(20) NOT NULL DEFAULT '1m',
    risk_level VARCHAR(20) NOT NULL DEFAULT 'Medium',
    position_size_pct DECIMAL(12,4) NOT NULL DEFAULT 0,
    stop_loss_pct DECIMAL(12,4) NOT NULL DEFAULT 0,
    take_profit_pct DECIMAL(12,4) NOT NULL DEFAULT 0,
    rationale TEXT,
    top_factors TEXT,
    avoid_reasons TEXT,
    pick_hash VARCHAR(64) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_hash (pick_hash),
    KEY idx_strategy (strategy),
    KEY idx_date (pick_date),
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 7. Refresh log with timestamps
"CREATE TABLE IF NOT EXISTS alpha_refresh_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    refresh_date DATETIME NOT NULL,
    step VARCHAR(100) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'started',
    details TEXT,
    duration_seconds INT NOT NULL DEFAULT 0,
    tickers_processed INT NOT NULL DEFAULT 0,
    errors_count INT NOT NULL DEFAULT 0,
    KEY idx_date (refresh_date),
    KEY idx_step (step)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 8. Alpha status (singleton table for dashboard)
"CREATE TABLE IF NOT EXISTS alpha_status (
    id INT NOT NULL DEFAULT 1,
    last_refresh_start DATETIME,
    last_refresh_end DATETIME,
    last_refresh_status VARCHAR(20) NOT NULL DEFAULT 'never',
    next_expected_refresh DATETIME,
    universe_count INT NOT NULL DEFAULT 0,
    factors_computed INT NOT NULL DEFAULT 0,
    picks_generated INT NOT NULL DEFAULT 0,
    current_regime VARCHAR(50) NOT NULL DEFAULT 'unknown',
    regime_detail TEXT,
    summary_json TEXT,
    PRIMARY KEY (id)
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
        $results['errors'][] = 'FAIL: ' . $conn->error;
    }
}

/* ================================================================
   SEED ALPHA UNIVERSE (50 stocks across all sectors)
   ================================================================ */
$today = date('Y-m-d');
$universe = array(
    // Technology (10)
    array('AAPL',  'Apple Inc',               'Technology',    'Consumer Electronics',      'mega'),
    array('MSFT',  'Microsoft Corp',          'Technology',    'Software - Infrastructure', 'mega'),
    array('GOOGL', 'Alphabet Inc',            'Technology',    'Internet Content',          'mega'),
    array('AMZN',  'Amazon.com Inc',          'Technology',    'Internet Retail',           'mega'),
    array('NVDA',  'NVIDIA Corp',             'Technology',    'Semiconductors',            'mega'),
    array('META',  'Meta Platforms Inc',      'Technology',    'Internet Content',          'mega'),
    array('AVGO',  'Broadcom Inc',            'Technology',    'Semiconductors',            'mega'),
    array('CRM',   'Salesforce Inc',          'Technology',    'Software - Application',    'large'),
    array('ADBE',  'Adobe Inc',               'Technology',    'Software - Application',    'large'),
    array('ORCL',  'Oracle Corp',             'Technology',    'Software - Infrastructure', 'large'),
    // Healthcare (8)
    array('UNH',   'UnitedHealth Group',      'Healthcare',    'Health Care Plans',         'mega'),
    array('JNJ',   'Johnson & Johnson',       'Healthcare',    'Drug Manufacturers',        'mega'),
    array('LLY',   'Eli Lilly and Co',        'Healthcare',    'Drug Manufacturers',        'mega'),
    array('PFE',   'Pfizer Inc',              'Healthcare',    'Drug Manufacturers',        'large'),
    array('ABBV',  'AbbVie Inc',              'Healthcare',    'Drug Manufacturers',        'large'),
    array('MRK',   'Merck & Co Inc',          'Healthcare',    'Drug Manufacturers',        'large'),
    array('TMO',   'Thermo Fisher Scientific','Healthcare',    'Diagnostics & Research',    'large'),
    array('ABT',   'Abbott Laboratories',     'Healthcare',    'Medical Devices',           'large'),
    // Financials (8)
    array('JPM',   'JPMorgan Chase & Co',     'Financials',    'Diversified Banks',         'mega'),
    array('BAC',   'Bank of America Corp',    'Financials',    'Diversified Banks',         'mega'),
    array('WFC',   'Wells Fargo & Co',        'Financials',    'Diversified Banks',         'large'),
    array('GS',    'Goldman Sachs Group',     'Financials',    'Capital Markets',           'large'),
    array('MS',    'Morgan Stanley',          'Financials',    'Capital Markets',           'large'),
    array('BLK',   'BlackRock Inc',           'Financials',    'Asset Management',          'large'),
    array('SCHW',  'Charles Schwab Corp',     'Financials',    'Capital Markets',           'large'),
    array('AXP',   'American Express Co',     'Financials',    'Credit Services',           'large'),
    // Consumer (8)
    array('WMT',   'Walmart Inc',             'Consumer',      'Discount Stores',           'mega'),
    array('PG',    'Procter & Gamble Co',     'Consumer',      'Household Products',        'mega'),
    array('KO',    'Coca-Cola Co',            'Consumer',      'Beverages',                 'mega'),
    array('PEP',   'PepsiCo Inc',             'Consumer',      'Beverages',                 'large'),
    array('COST',  'Costco Wholesale Corp',   'Consumer',      'Discount Stores',           'large'),
    array('HD',    'Home Depot Inc',          'Consumer',      'Home Improvement',          'large'),
    array('MCD',   'McDonalds Corp',          'Consumer',      'Restaurants',               'large'),
    array('NKE',   'NIKE Inc',                'Consumer',      'Footwear & Accessories',    'large'),
    // Industrials (6)
    array('CAT',   'Caterpillar Inc',         'Industrials',   'Farm & Heavy Equipment',    'large'),
    array('HON',   'Honeywell International', 'Industrials',   'Conglomerates',             'large'),
    array('UPS',   'United Parcel Service',   'Industrials',   'Integrated Freight',        'large'),
    array('GE',    'GE Aerospace',            'Industrials',   'Aerospace & Defense',       'large'),
    array('RTX',   'RTX Corp',                'Industrials',   'Aerospace & Defense',       'large'),
    array('BA',    'Boeing Co',               'Industrials',   'Aerospace & Defense',       'large'),
    // Energy (4)
    array('XOM',   'Exxon Mobil Corp',        'Energy',        'Oil & Gas Integrated',      'mega'),
    array('CVX',   'Chevron Corp',            'Energy',        'Oil & Gas Integrated',      'large'),
    array('COP',   'ConocoPhillips',          'Energy',        'Oil & Gas E&P',             'large'),
    array('SLB',   'Schlumberger NV',         'Energy',        'Oil & Gas Services',        'large'),
    // Real Estate (2)
    array('AMT',   'American Tower Corp',     'Real Estate',   'REIT - Specialty',          'large'),
    array('PLD',   'Prologis Inc',            'Real Estate',   'REIT - Industrial',         'large'),
    // Utilities (2)
    array('NEE',   'NextEra Energy Inc',      'Utilities',     'Utilities - Regulated',     'large'),
    array('SO',    'Southern Company',        'Utilities',     'Utilities - Regulated',     'large'),
    // Materials (2)
    array('LIN',   'Linde PLC',              'Materials',     'Specialty Chemicals',       'large'),
    array('APD',   'Air Products & Chemicals','Materials',     'Specialty Chemicals',       'large'),
    // Communication (2)
    array('DIS',   'Walt Disney Co',          'Communication', 'Entertainment',             'large'),
    array('NFLX',  'Netflix Inc',             'Communication', 'Entertainment',             'large')
);

$uni_count = 0;
foreach ($universe as $s) {
    $t = $conn->real_escape_string($s[0]);
    $n = $conn->real_escape_string($s[1]);
    $sec = $conn->real_escape_string($s[2]);
    $ind = $conn->real_escape_string($s[3]);
    $tier = $conn->real_escape_string($s[4]);
    $sql = "INSERT INTO alpha_universe (ticker, company_name, sector, industry, market_cap_tier, added_date, active)
            VALUES ('$t','$n','$sec','$ind','$tier','$today',1)
            ON DUPLICATE KEY UPDATE company_name='$n', sector='$sec', industry='$ind', market_cap_tier='$tier', active=1";
    if ($conn->query($sql)) {
        $uni_count++;
    }
    // Also ensure stock exists in main stocks table
    $conn->query("INSERT INTO stocks (ticker, company_name, sector) VALUES ('$t','$n','$sec')
                  ON DUPLICATE KEY UPDATE company_name='$n', sector='$sec'");
}
$results['actions'][] = 'Seeded ' . $uni_count . ' universe stocks';

/* ================================================================
   SEED ALPHA ALGORITHMS into main algorithms table
   ================================================================ */
$alpha_algos = array(
    array('Alpha Factor Momentum',   'AlphaFactor', 'Cross-sectional momentum: ranks universe by 12M/6M/3M returns composite. Buys top 10. Monthly rebalance. Academic: Jegadeesh & Titman (1993).', 'momentum', '30d'),
    array('Alpha Factor Quality',    'AlphaFactor', 'Quality composite: ROE, gross margins, FCF yield, low debt. Buys top 10 quality names. Quarterly rebalance. Academic: Asness et al QMJ (2014).', 'quality', '90d'),
    array('Alpha Factor Value',      'AlphaFactor', 'Sector-neutral value composite: P/E, P/B, P/S, EV/EBITDA, dividend yield. Buys cheapest quintile. Quarterly. Academic: Fama-French (1993).', 'value', '90d'),
    array('Alpha Factor Earnings',   'AlphaFactor', 'Earnings surprise momentum: consistent beats + positive surprise drift. Targets PEAD anomaly. Academic: Ball & Brown (1968).', 'event_arb', '60d'),
    array('Alpha Factor Low Vol',    'AlphaFactor', 'Low volatility anomaly: lowest realized vol + beta + drawdown. Defensive. Academic: Blitz & van Vliet (2007).', 'defensive', '90d'),
    array('Alpha Factor Growth',     'AlphaFactor', 'Revenue + earnings growth consistency. Forward-looking via P/E compression. Quarterly rebalance.', 'growth', '90d'),
    array('Alpha Factor Composite',  'AlphaFactor', 'Regime-adjusted multi-factor blend: Momentum 25%, Quality 20%, Value 20%, Earnings 15%, Volatility 10%, Growth 10%. Weights shift with macro regime.', 'multi_factor', '30d'),
    array('Alpha Factor Safe Bets',  'AlphaFactor', 'Compounding quality sleeve: low vol + high quality + reasonable value + earnings consistency. Long-term hold. Dividend aristocrat bias.', 'quality', '180d'),
    array('Alpha Factor Consensus',  'AlphaFactor', 'Meta-ensemble: stocks appearing in 3+ alpha factor strategies. Highest conviction picks with multi-signal confirmation.', 'ensemble', '30d')
);

$algo_count = 0;
foreach ($alpha_algos as $a) {
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
$results['actions'][] = 'Seeded ' . $algo_count . ' alpha algorithms';

/* ================================================================
   SEED ALPHA PORTFOLIO TEMPLATES
   ================================================================ */
$now = date('Y-m-d H:i:s');
$alpha_portfolios = array(
    array('Alpha Momentum (30D)',          'alpha_factor', 'Alpha Factor Momentum',                           10000, 0, 0, 8.00, 20.00, 30, 0.005),
    array('Alpha Quality (90D)',           'alpha_factor', 'Alpha Factor Quality',                            10000, 0, 0, 12.00, 30.00, 90, 0.005),
    array('Alpha Value (90D)',             'alpha_factor', 'Alpha Factor Value',                              10000, 0, 0, 10.00, 25.00, 90, 0.005),
    array('Alpha Low Vol Defensive',       'alpha_factor', 'Alpha Factor Low Vol',                            10000, 0, 0, 8.00, 999.00, 90, 0.003),
    array('Alpha Safe Compounder (6M)',    'alpha_factor', 'Alpha Factor Safe Bets',                          10000, 0, 0, 15.00, 999.00, 180, 0.003),
    array('Alpha Composite Regime (30D)',  'alpha_factor', 'Alpha Factor Composite',                          10000, 0, 0, 8.00, 25.00, 30, 0.005),
    array('Alpha Consensus Best Ideas',    'alpha_factor', 'Alpha Factor Consensus',                          10000, 0, 0, 10.00, 25.00, 30, 0.005),
    array('Alpha Full Suite',              'alpha_factor', 'Alpha Factor Momentum,Alpha Factor Quality,Alpha Factor Value,Alpha Factor Earnings,Alpha Factor Low Vol,Alpha Factor Growth,Alpha Factor Composite,Alpha Factor Safe Bets,Alpha Factor Consensus', 10000, 0, 0, 10.00, 25.00, 60, 0.005)
);

$port_count = 0;
foreach ($alpha_portfolios as $p) {
    $pname = $conn->real_escape_string($p[0]);
    $chk = $conn->query("SELECT id FROM portfolios WHERE name='$pname'");
    if ($chk && $chk->num_rows == 0) {
        $stype = $conn->real_escape_string($p[1]);
        $afilt = $conn->real_escape_string($p[2]);
        $sql = "INSERT INTO portfolios (name, strategy_type, algorithm_filter, initial_capital, commission_buy, commission_sell, stop_loss_pct, take_profit_pct, max_hold_days, slippage_pct, created_at)
                VALUES ('$pname','$stype','$afilt'," . (float)$p[3] . "," . (float)$p[4] . "," . (float)$p[5] . "," . (float)$p[6] . "," . (float)$p[7] . "," . (int)$p[8] . "," . (float)$p[9] . ",'$now')";
        if ($conn->query($sql)) {
            $port_count++;
        }
    }
}
$results['actions'][] = 'Seeded ' . $port_count . ' alpha portfolios';

// Initialize alpha_status if empty
$st_chk = $conn->query("SELECT id FROM alpha_status WHERE id=1");
if ($st_chk && $st_chk->num_rows == 0) {
    $conn->query("INSERT INTO alpha_status (id, last_refresh_status, universe_count) VALUES (1, 'never', $uni_count)");
    $results['actions'][] = 'Initialized alpha_status';
}

// Log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('alpha_setup', 'Alpha schema created/verified', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
