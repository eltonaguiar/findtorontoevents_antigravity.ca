<?php
/**
 * Setup database schema for Mutual Fund Portfolio Analysis
 * All tables prefixed with mf_ to distinguish from stock tables.
 * Run once via HTTP to create all tables.
 * PHP 5.2 compatible.
 *
 * Usage: GET https://findtorontoevents.ca/findmutualfunds/api/setup_schema.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'actions' => array());

$tables = array(

// 1. Mutual fund master list
"CREATE TABLE IF NOT EXISTS mf_funds (
    ticker VARCHAR(15) NOT NULL,
    fund_name VARCHAR(300) NOT NULL DEFAULT '',
    category VARCHAR(150) NOT NULL DEFAULT '',
    family VARCHAR(150) NOT NULL DEFAULT '',
    expense_ratio DECIMAL(5,4) NOT NULL DEFAULT 0,
    min_investment DECIMAL(12,2) NOT NULL DEFAULT 0,
    load_type VARCHAR(30) NOT NULL DEFAULT 'no-load',
    front_load_pct DECIMAL(5,2) NOT NULL DEFAULT 0,
    back_load_pct DECIMAL(5,2) NOT NULL DEFAULT 0,
    morningstar_rating TINYINT NOT NULL DEFAULT 0,
    asset_class VARCHAR(50) NOT NULL DEFAULT '',
    inception_date DATE,
    net_assets VARCHAR(30) NOT NULL DEFAULT '',
    PRIMARY KEY (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 2. Daily NAV history
"CREATE TABLE IF NOT EXISTS mf_nav_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(15) NOT NULL,
    nav_date DATE NOT NULL,
    nav_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    adj_nav DECIMAL(12,4) NOT NULL DEFAULT 0,
    change_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    volume BIGINT NOT NULL DEFAULT 0,
    UNIQUE KEY idx_ticker_date (ticker, nav_date),
    KEY idx_date (nav_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 3. Fund screening criteria / strategy definitions
"CREATE TABLE IF NOT EXISTS mf_strategies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL DEFAULT 'general',
    selection_criteria TEXT,
    ideal_timeframe VARCHAR(30) NOT NULL DEFAULT '',
    risk_level VARCHAR(20) NOT NULL DEFAULT 'Medium',
    UNIQUE KEY idx_name (name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 4. Fund selections / picks
"CREATE TABLE IF NOT EXISTS mf_selections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(15) NOT NULL,
    strategy_id INT NOT NULL DEFAULT 0,
    strategy_name VARCHAR(200) NOT NULL DEFAULT '',
    select_date DATE NOT NULL,
    nav_at_select DECIMAL(12,4) NOT NULL DEFAULT 0,
    category VARCHAR(150) NOT NULL DEFAULT '',
    expense_ratio DECIMAL(5,4) NOT NULL DEFAULT 0,
    morningstar_rating TINYINT NOT NULL DEFAULT 0,
    rationale TEXT,
    select_hash VARCHAR(64) NOT NULL DEFAULT '',
    KEY idx_ticker (ticker),
    KEY idx_strategy (strategy_name),
    KEY idx_date (select_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 5. Portfolio templates
"CREATE TABLE IF NOT EXISTS mf_portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL DEFAULT 'balanced',
    strategy_filter VARCHAR(500) NOT NULL DEFAULT '',
    initial_capital DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    commission_buy DECIMAL(6,2) NOT NULL DEFAULT 0,
    commission_sell DECIMAL(6,2) NOT NULL DEFAULT 0,
    hold_period_days INT NOT NULL DEFAULT 90,
    rebalance_freq VARCHAR(20) NOT NULL DEFAULT 'quarterly',
    target_return_pct DECIMAL(5,2) NOT NULL DEFAULT 0,
    stop_loss_pct DECIMAL(5,2) NOT NULL DEFAULT 0,
    expense_drag_annual DECIMAL(5,4) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 6. Backtest results (aggregate per run)
"CREATE TABLE IF NOT EXISTS mf_backtest_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL DEFAULT 0,
    run_name VARCHAR(200) NOT NULL DEFAULT '',
    strategy_filter VARCHAR(500) NOT NULL DEFAULT '',
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
    max_drawdown_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    total_expenses DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_commissions DECIMAL(12,2) NOT NULL DEFAULT 0,
    sharpe_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
    alpha DECIMAL(10,4) NOT NULL DEFAULT 0,
    beta DECIMAL(10,4) NOT NULL DEFAULT 0,
    params_json TEXT,
    created_at DATETIME NOT NULL,
    KEY idx_portfolio (portfolio_id),
    KEY idx_strategy (strategy_type)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 7. Individual trade records from backtests
"CREATE TABLE IF NOT EXISTS mf_backtest_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    backtest_id INT NOT NULL DEFAULT 0,
    ticker VARCHAR(15) NOT NULL,
    strategy_name VARCHAR(200) NOT NULL DEFAULT '',
    entry_date DATE NOT NULL,
    entry_nav DECIMAL(12,4) NOT NULL DEFAULT 0,
    exit_date DATE,
    exit_nav DECIMAL(12,4) NOT NULL DEFAULT 0,
    shares DECIMAL(12,4) NOT NULL DEFAULT 0,
    gross_profit DECIMAL(12,2) NOT NULL DEFAULT 0,
    expense_cost DECIMAL(8,2) NOT NULL DEFAULT 0,
    commission_paid DECIMAL(8,2) NOT NULL DEFAULT 0,
    net_profit DECIMAL(12,2) NOT NULL DEFAULT 0,
    return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(50) NOT NULL DEFAULT '',
    hold_days INT NOT NULL DEFAULT 0,
    KEY idx_backtest (backtest_id),
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 8. What-if scenario history
"CREATE TABLE IF NOT EXISTS mf_whatif_scenarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario_name VARCHAR(200) NOT NULL DEFAULT '',
    query_text TEXT,
    params_json TEXT,
    results_json TEXT,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 9. Benchmark comparison data (S&P 500 index fund, bond fund, etc.)
"CREATE TABLE IF NOT EXISTS mf_benchmarks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(15) NOT NULL,
    bench_name VARCHAR(200) NOT NULL DEFAULT '',
    bench_type VARCHAR(50) NOT NULL DEFAULT '',
    nav_date DATE NOT NULL,
    nav_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    UNIQUE KEY idx_ticker_date (ticker, nav_date),
    KEY idx_type (bench_type)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 10. Audit log
"CREATE TABLE IF NOT EXISTS mf_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    KEY idx_action (action_type),
    KEY idx_date (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 11. Report cache
"CREATE TABLE IF NOT EXISTS mf_report_cache (
    cache_key VARCHAR(50) PRIMARY KEY,
    cache_data LONGTEXT,
    updated_at DATETIME
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 12. Simulation grid
"CREATE TABLE IF NOT EXISTS mf_simulation_grid (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id INT DEFAULT 0,
    strategy VARCHAR(200) DEFAULT '',
    hold_days INT DEFAULT 90,
    stop_loss DECIMAL(6,2) DEFAULT 0,
    target_return DECIMAL(6,2) DEFAULT 0,
    commission DECIMAL(6,2) DEFAULT 0,
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    win_rate DECIMAL(6,2) DEFAULT 0,
    total_return_pct DECIMAL(10,4) DEFAULT 0,
    annualized_return_pct DECIMAL(10,4) DEFAULT 0,
    final_value DECIMAL(12,2) DEFAULT 10000,
    max_drawdown_pct DECIMAL(8,4) DEFAULT 0,
    sharpe_ratio DECIMAL(8,4) DEFAULT 0,
    total_pnl DECIMAL(12,2) DEFAULT 0,
    total_expenses DECIMAL(10,2) DEFAULT 0,
    created_at DATETIME,
    INDEX idx_strat (strategy),
    INDEX idx_ret (total_return_pct)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 13. Simulation meta
"CREATE TABLE IF NOT EXISTS mf_simulation_meta (
    meta_key VARCHAR(50) PRIMARY KEY,
    meta_value TEXT,
    updated_at DATETIME
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

// ─── Seed default strategies ───
$strategies = array(
    array('Growth Leaders',      'Morningstar 5-star large-cap growth funds with low expense ratios.',               'growth',       'Morningstar >= 4, Expense < 0.50%, Large Cap Growth', '1y',  'Medium'),
    array('Income Focus',        'High-yield bond and dividend-focused funds.',                                      'income',       'Yield >= 3%, Bond/Dividend category',                 '1y',  'Low'),
    array('Balanced Moderate',   'Mixed equity/bond funds targeting moderate growth with downside protection.',       'balanced',     '60/40 or 50/50 allocation, Morningstar >= 3',         '2y',  'Low'),
    array('Aggressive Growth',   'Small/mid-cap growth funds with higher volatility tolerance.',                      'aggressive',   'Small/Mid Growth, High 3yr return',                   '6m',  'High'),
    array('Index Tracker',       'Low-cost index funds that track major benchmarks (S&P 500, Total Market).',        'passive',      'Expense < 0.10%, Index fund, Tracking error < 0.5%', '5y',  'Low'),
    array('Sector Rotation',     'Funds in sectors showing momentum: tech, healthcare, energy, etc.',                'sector',       'Top sector 3-month momentum, Morningstar >= 3',      '3m',  'High'),
    array('International Blend', 'Diversified international and emerging market funds.',                              'international','International/EM, Morningstar >= 3, Expense < 0.75%','1y',  'Medium'),
    array('Target Date 2030',    'Target-date funds adjusting allocation toward 2030 retirement.',                    'target_date',  'Target Date 2030, Auto-rebalancing',                  '5y',  'Low'),
    array('ESG/Sustainable',     'Funds scoring high on environmental, social, governance criteria.',                 'esg',          'ESG Rating >= 4, Morningstar Sustainability > Avg',   '2y',  'Medium'),
    array('Contrarian Value',    'Underperforming funds with strong 10yr track records and new management.',          'value',        'Below 3yr avg, Above 10yr avg, Morningstar >= 3',    '1y',  'Medium')
);

$strat_count = 0;
foreach ($strategies as $s) {
    $name  = $conn->real_escape_string($s[0]);
    $desc  = $conn->real_escape_string($s[1]);
    $stype = $conn->real_escape_string($s[2]);
    $crit  = $conn->real_escape_string($s[3]);
    $tf    = $conn->real_escape_string($s[4]);
    $risk  = $conn->real_escape_string($s[5]);
    $sql = "INSERT INTO mf_strategies (name, description, strategy_type, selection_criteria, ideal_timeframe, risk_level)
            VALUES ('$name','$desc','$stype','$crit','$tf','$risk')
            ON DUPLICATE KEY UPDATE description='$desc', strategy_type='$stype'";
    if ($conn->query($sql)) $strat_count++;
}
$results['actions'][] = 'Seeded ' . $strat_count . ' strategies';

// ─── Seed default portfolio templates ───
$now = date('Y-m-d H:i:s');
$ports = array(
    array('Conservative Income',  'income',      '',  10000, 0, 0, 365, 'quarterly', 5,  3,   0.004),
    array('Balanced Growth',      'balanced',    '',  10000, 0, 0, 180, 'quarterly', 10, 8,   0.005),
    array('Aggressive Growth',    'aggressive',  '',  10000, 0, 0, 90,  'monthly',   15, 10,  0.006),
    array('Index Only',           'passive',     'Index Tracker', 10000, 0, 0, 365, 'annual', 8, 5, 0.001),
    array('Growth Leaders Only',  'growth',      'Growth Leaders', 10000, 0, 0, 180, 'quarterly', 12, 8, 0.005),
    array('Sector Rotator',       'sector',      'Sector Rotation', 10000, 0, 0, 90, 'monthly', 15, 10, 0.006),
    array('Diversified All',      'diversified', '',  10000, 0, 0, 180, 'quarterly', 10, 8,  0.005),
    array('With $49.95 Commission','balanced',   '',  10000, 49.95, 49.95, 180, 'quarterly', 10, 8, 0.005)
);

$port_count = 0;
foreach ($ports as $p) {
    $pname = $conn->real_escape_string($p[0]);
    $stype = $conn->real_escape_string($p[1]);
    $sfilt = $conn->real_escape_string($p[2]);
    $chk = $conn->query("SELECT id FROM mf_portfolios WHERE name='$pname'");
    if ($chk && $chk->num_rows == 0) {
        $sql = "INSERT INTO mf_portfolios (name, strategy_type, strategy_filter, initial_capital, commission_buy, commission_sell, hold_period_days, rebalance_freq, target_return_pct, stop_loss_pct, expense_drag_annual, created_at)
                VALUES ('$pname','$stype','$sfilt'," . (float)$p[3] . "," . (float)$p[4] . "," . (float)$p[5] . "," . (int)$p[6] . ",'" . $conn->real_escape_string($p[7]) . "'," . (float)$p[8] . "," . (float)$p[9] . "," . (float)$p[10] . ",'$now')";
        if ($conn->query($sql)) $port_count++;
    }
}
$results['actions'][] = 'Seeded ' . $port_count . ' portfolio templates';

// ─── Seed well-known mutual funds ───
$funds = array(
    array('VFIAX',  'Vanguard 500 Index Fund Admiral',         'Large Blend',          'Vanguard',    0.0004, 3000,   'no-load', 0, 0, 5, 'Equity'),
    array('FXAIX',  'Fidelity 500 Index Fund',                 'Large Blend',          'Fidelity',    0.0015, 0,      'no-load', 0, 0, 5, 'Equity'),
    array('VTSAX',  'Vanguard Total Stock Market Index',       'Large Blend',          'Vanguard',    0.0004, 3000,   'no-load', 0, 0, 5, 'Equity'),
    array('VBTLX',  'Vanguard Total Bond Market Index',        'Intermediate Core Bond','Vanguard',   0.0005, 3000,   'no-load', 0, 0, 4, 'Bond'),
    array('VWELX',  'Vanguard Wellington Fund',                'Allocation 60-70% Eq', 'Vanguard',    0.0025, 3000,   'no-load', 0, 0, 5, 'Balanced'),
    array('FCNTX',  'Fidelity Contrafund',                     'Large Growth',         'Fidelity',    0.0039, 0,      'no-load', 0, 0, 4, 'Equity'),
    array('TRBCX',  'T. Rowe Price Blue Chip Growth',          'Large Growth',         'T. Rowe Price',0.0069,2500,   'no-load', 0, 0, 5, 'Equity'),
    array('PIMIX',  'PIMCO Income Fund Institutional',         'Multisector Bond',     'PIMCO',       0.0055, 1000000,'no-load', 0, 0, 4, 'Bond'),
    array('VWIGX',  'Vanguard Intl Growth Fund',               'Foreign Large Growth', 'Vanguard',    0.0032, 3000,   'no-load', 0, 0, 4, 'International'),
    array('DODFX',  'Dodge & Cox International Stock',         'Foreign Large Value',  'Dodge & Cox', 0.0063, 2500,   'no-load', 0, 0, 4, 'International'),
    array('VGHCX',  'Vanguard Health Care Fund',               'Health',               'Vanguard',    0.0032, 3000,   'no-load', 0, 0, 4, 'Sector'),
    array('FSPHX',  'Fidelity Select Health Care',             'Health',               'Fidelity',    0.0069, 0,      'no-load', 0, 0, 3, 'Sector'),
    array('VWINX',  'Vanguard Wellesley Income',               'Allocation 30-50% Eq', 'Vanguard',    0.0023, 3000,   'no-load', 0, 0, 5, 'Balanced'),
    array('PRWCX',  'T. Rowe Price Capital Appreciation',      'Allocation 50-70% Eq', 'T. Rowe Price',0.0070,2500,   'no-load', 0, 0, 5, 'Balanced'),
    array('VEIPX',  'Vanguard Equity Income Fund',             'Large Value',          'Vanguard',    0.0027, 3000,   'no-load', 0, 0, 4, 'Equity'),
    array('VTIAX',  'Vanguard Total Intl Stock Index Admiral', 'Foreign Large Blend',  'Vanguard',    0.0011, 3000,   'no-load', 0, 0, 4, 'International'),
    array('SWPPX',  'Schwab S&P 500 Index Fund',               'Large Blend',          'Schwab',      0.0002, 0,      'no-load', 0, 0, 5, 'Equity'),
    array('SWTSX',  'Schwab Total Stock Market Index',          'Large Blend',          'Schwab',      0.0003, 0,      'no-load', 0, 0, 5, 'Equity'),
    array('VGSLX',  'Vanguard Real Estate Index Admiral',      'Real Estate',          'Vanguard',    0.0012, 3000,   'no-load', 0, 0, 4, 'Real Estate'),
    array('VTMFX',  'Vanguard Tax-Managed Balanced',           'Allocation 50-70% Eq', 'Vanguard',    0.0009, 10000,  'no-load', 0, 0, 4, 'Balanced')
);

$fund_count = 0;
foreach ($funds as $f) {
    $t = $conn->real_escape_string($f[0]);
    $fn = $conn->real_escape_string($f[1]);
    $cat = $conn->real_escape_string($f[2]);
    $fam = $conn->real_escape_string($f[3]);
    $sql = "INSERT INTO mf_funds (ticker, fund_name, category, family, expense_ratio, min_investment, load_type, front_load_pct, back_load_pct, morningstar_rating, asset_class)
            VALUES ('$t','$fn','$cat','$fam'," . (float)$f[4] . "," . (float)$f[5] . ",'" . $conn->real_escape_string($f[6]) . "'," . (float)$f[7] . "," . (float)$f[8] . "," . (int)$f[9] . ",'" . $conn->real_escape_string($f[10]) . "')
            ON DUPLICATE KEY UPDATE fund_name='$fn', category='$cat'";
    if ($conn->query($sql)) $fund_count++;
}
$results['actions'][] = 'Seeded ' . $fund_count . ' well-known funds';

// Log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO mf_audit_log (action_type, details, ip_address, created_at) VALUES ('setup_schema', 'MF schema created/verified', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
