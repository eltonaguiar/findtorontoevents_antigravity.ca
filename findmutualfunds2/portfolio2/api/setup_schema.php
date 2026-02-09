<?php
/**
 * Setup database schema for Mutual Funds Portfolio Analysis v2
 * All tables prefixed with mf2_ to distinguish from stock tables.
 * PHP 5.2 compatible.
 *
 * Usage: GET https://findtorontoevents.ca/findmutualfunds2/portfolio2/api/setup_schema.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'actions' => array());

// ─── Core Data Tables (all prefixed mf2_) ───

$tables = array(

// 1. Mutual funds master list
"CREATE TABLE IF NOT EXISTS mf2_funds (
    symbol VARCHAR(20) NOT NULL,
    fund_name VARCHAR(300) NOT NULL DEFAULT '',
    fund_family VARCHAR(200) NOT NULL DEFAULT '',
    category VARCHAR(200) NOT NULL DEFAULT '',
    asset_class VARCHAR(50) NOT NULL DEFAULT '',
    expense_ratio DECIMAL(6,4) NOT NULL DEFAULT 0,
    min_investment DECIMAL(12,2) NOT NULL DEFAULT 0,
    inception_date DATE DEFAULT NULL,
    morningstar_rating TINYINT NOT NULL DEFAULT 0,
    PRIMARY KEY (symbol)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 2. Daily NAV history
"CREATE TABLE IF NOT EXISTS mf2_nav_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    nav_date DATE NOT NULL,
    nav DECIMAL(12,4) NOT NULL DEFAULT 0,
    prev_nav DECIMAL(12,4) NOT NULL DEFAULT 0,
    daily_return_pct DECIMAL(10,6) NOT NULL DEFAULT 0,
    volume BIGINT NOT NULL DEFAULT 0,
    UNIQUE KEY idx_symbol_date (symbol, nav_date),
    KEY idx_date (nav_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 3. Fund selection algorithm definitions
"CREATE TABLE IF NOT EXISTS mf2_algorithms (
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

// 4. Fund picks from algorithms
"CREATE TABLE IF NOT EXISTS mf2_fund_picks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    algorithm_id INT NOT NULL DEFAULT 0,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    pick_date DATE NOT NULL,
    pick_time DATETIME NOT NULL,
    entry_nav DECIMAL(12,4) NOT NULL DEFAULT 0,
    score INT NOT NULL DEFAULT 0,
    rating VARCHAR(20) NOT NULL DEFAULT '',
    risk_level VARCHAR(20) NOT NULL DEFAULT 'Medium',
    timeframe VARCHAR(20) NOT NULL DEFAULT '',
    pick_hash VARCHAR(64) NOT NULL DEFAULT '',
    rationale_json TEXT,
    KEY idx_symbol (symbol),
    KEY idx_algorithm (algorithm_name),
    KEY idx_date (pick_date),
    KEY idx_hash (pick_hash)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 5. Portfolio definitions (mutual fund strategies)
"CREATE TABLE IF NOT EXISTS mf2_portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL DEFAULT 'balanced',
    algorithm_filter VARCHAR(500) NOT NULL DEFAULT '',
    initial_capital DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    commission_buy DECIMAL(6,2) NOT NULL DEFAULT 0.00,
    commission_sell DECIMAL(6,2) NOT NULL DEFAULT 0.00,
    redemption_fee_pct DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    target_return_pct DECIMAL(5,2) NOT NULL DEFAULT 10.00,
    stop_loss_pct DECIMAL(5,2) NOT NULL DEFAULT 8.00,
    max_hold_days INT NOT NULL DEFAULT 90,
    position_size_pct DECIMAL(5,2) NOT NULL DEFAULT 20.00,
    max_positions INT NOT NULL DEFAULT 5,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 6. Backtest results (aggregate per run)
"CREATE TABLE IF NOT EXISTS mf2_backtest_results (
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
    total_fees DECIMAL(12,2) NOT NULL DEFAULT 0,
    sharpe_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
    sortino_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
    profit_factor DECIMAL(10,4) NOT NULL DEFAULT 0,
    expectancy DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_hold_days DECIMAL(8,2) NOT NULL DEFAULT 0,
    fee_drag_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    params_json TEXT,
    created_at DATETIME NOT NULL,
    KEY idx_portfolio (portfolio_id),
    KEY idx_strategy (strategy_type)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 7. Individual trade records from backtests
"CREATE TABLE IF NOT EXISTS mf2_backtest_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    backtest_id INT NOT NULL DEFAULT 0,
    symbol VARCHAR(20) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    entry_date DATE NOT NULL,
    entry_nav DECIMAL(12,4) NOT NULL DEFAULT 0,
    exit_date DATE,
    exit_nav DECIMAL(12,4) NOT NULL DEFAULT 0,
    units DECIMAL(12,4) NOT NULL DEFAULT 0,
    gross_profit DECIMAL(12,2) NOT NULL DEFAULT 0,
    fees_paid DECIMAL(8,2) NOT NULL DEFAULT 0,
    net_profit DECIMAL(12,2) NOT NULL DEFAULT 0,
    return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(50) NOT NULL DEFAULT '',
    hold_days INT NOT NULL DEFAULT 0,
    KEY idx_backtest (backtest_id),
    KEY idx_symbol (symbol)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 8. What-if scenario history
"CREATE TABLE IF NOT EXISTS mf2_whatif_scenarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario_name VARCHAR(200) NOT NULL DEFAULT '',
    query_text TEXT,
    params_json TEXT,
    results_json TEXT,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 9. Audit log
"CREATE TABLE IF NOT EXISTS mf2_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    KEY idx_action (action_type),
    KEY idx_date (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 10. Algorithm performance summary
"CREATE TABLE IF NOT EXISTS mf2_algo_performance (
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

// 11. Portfolio comparison results
"CREATE TABLE IF NOT EXISTS mf2_comparisons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comparison_name VARCHAR(200) NOT NULL DEFAULT '',
    scenarios_json TEXT,
    best_scenario VARCHAR(200) NOT NULL DEFAULT '',
    worst_scenario VARCHAR(200) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 12. Fund category performance tracking
"CREATE TABLE IF NOT EXISTS mf2_category_perf (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(200) NOT NULL,
    period VARCHAR(20) NOT NULL DEFAULT '1m',
    avg_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    top_fund VARCHAR(20) NOT NULL DEFAULT '',
    worst_fund VARCHAR(20) NOT NULL DEFAULT '',
    fund_count INT NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_cat_period (category, period)
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

// ─── Seed mutual fund algorithms ───
$algos = array(
    array('MF Momentum',            'Momentum',   'Selects funds with strongest 3/6/12 month returns. Momentum factor investing for mutual funds.', 'momentum', '3m'),
    array('MF Value Tilt',          'Value',      'Favors funds with below-average P/E, P/B ratios. Deep value approach.', 'value', '6m'),
    array('MF Sector Rotation',     'Sector',     'Rotates into top-performing sectors monthly. Uses relative strength.', 'sector_rotation', '1m'),
    array('MF Risk Parity',         'Risk',       'Allocates inversely proportional to volatility. Lower vol = more weight.', 'risk_adjusted', '3m'),
    array('MF Expense Optimizer',   'Cost',       'Selects lowest expense ratio funds per category. Cost-conscious approach.', 'cost_optimization', '1y'),
    array('MF Trend Following',     'Trend',      'Buys above 200-day NAV average, sells below. Classic trend system.', 'trend', '6m'),
    array('MF Mean Reversion',      'Contrarian', 'Buys oversold funds (NAV below 20-day low), sells overbought. Contrarian.', 'mean_reversion', '1m'),
    array('MF Quality Growth',      'Quality',    'Screens for consistent returns, low drawdown, high Sharpe. Quality factor.', 'quality', '1y'),
    array('MF Diversified Income',  'Income',     'Targets high-yield bond and dividend funds. Income-focused allocation.', 'income', '6m'),
    array('MF Balanced Composite',  'Composite',  'Multi-factor: momentum (30%), quality (25%), value (25%), cost (20%).', 'multi_factor', '3m')
);

$algo_count = 0;
foreach ($algos as $a) {
    $name  = $conn->real_escape_string($a[0]);
    $fam   = $conn->real_escape_string($a[1]);
    $desc  = $conn->real_escape_string($a[2]);
    $atype = $conn->real_escape_string($a[3]);
    $tf    = $conn->real_escape_string($a[4]);
    $sql = "INSERT INTO mf2_algorithms (name, family, description, algo_type, ideal_timeframe)
            VALUES ('$name','$fam','$desc','$atype','$tf')
            ON DUPLICATE KEY UPDATE family='$fam', description='$desc', algo_type='$atype', ideal_timeframe='$tf'";
    if ($conn->query($sql)) {
        $algo_count++;
    }
}
$results['actions'][] = 'Seeded ' . $algo_count . ' fund algorithms';

// ─── Seed portfolio templates ───
$now = date('Y-m-d H:i:s');
// name, desc, strategy_type, algo_filter, capital, comm_buy, comm_sell, redemption_fee, target, sl, max_hold, pos_size, max_pos
$portfolios = array(
    // Conservative
    array('Conservative Income',     'Bond/income funds, long hold, low risk.',               'conservative', 'MF Diversified Income',  10000, 0, 0, 0,    8, 5, 180, 25, 4),
    array('Ultra Safe (Index Only)', 'Low-cost index funds, buy and hold.',                    'conservative', 'MF Expense Optimizer',   10000, 0, 0, 0,   10, 8, 365, 20, 5),
    // Balanced
    array('Balanced Growth',         '60/40 equity/bond via quality and income funds.',        'balanced',     '',                       10000, 0, 0, 0,   12, 8, 120, 20, 5),
    array('All-Weather',             'Risk parity across asset classes.',                       'balanced',     'MF Risk Parity',         10000, 0, 0, 0,   10, 5, 180, 20, 5),
    // Growth
    array('Aggressive Growth',       'High-momentum equity funds, sector rotation.',           'growth',       'MF Momentum,MF Sector Rotation', 10000, 0, 0, 0, 20, 10, 90, 25, 4),
    array('Quality Growth',          'Consistent growers with low drawdown.',                   'growth',       'MF Quality Growth',      10000, 0, 0, 0,   15, 8, 120, 20, 5),
    // Tactical
    array('Tactical Rotation',       'Monthly sector rotation based on relative strength.',    'tactical',     'MF Sector Rotation',     10000, 0, 0, 0,   15, 8,  30, 25, 4),
    array('Momentum Chase',          'Top 3-month performers, rebalance monthly.',             'tactical',     'MF Momentum',            10000, 0, 0, 0,   20, 10, 30, 20, 5),
    // Contrarian
    array('Contrarian Rebound',      'Buy beaten-down funds expecting mean reversion.',        'contrarian',   'MF Mean Reversion',      10000, 0, 0, 0,   15, 10, 60, 20, 5),
    array('Value Deep Dive',         'Funds in out-of-favor sectors at low valuations.',        'contrarian',   'MF Value Tilt',          10000, 0, 0, 0,   12, 8, 120, 25, 4),
    // Composite
    array('Multi-Factor Blend',      'Combines momentum, quality, value, and cost factors.',   'composite',    'MF Balanced Composite',  10000, 0, 0, 0,   12, 7,  90, 20, 5),
    array('Trend + Quality',         'Trend-following entry with quality filter.',              'composite',    'MF Trend Following,MF Quality Growth', 10000, 0, 0, 0, 15, 8, 90, 20, 5)
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
    $rf    = (float)$p[7];
    $tp    = (float)$p[8];
    $sl    = (float)$p[9];
    $mhd   = (int)$p[10];
    $psz   = (float)$p[11];
    $mpos  = (int)$p[12];

    $chk = $conn->query("SELECT id FROM mf2_portfolios WHERE name='$pname'");
    if ($chk && $chk->num_rows == 0) {
        $sql = "INSERT INTO mf2_portfolios (name, description, strategy_type, algorithm_filter, initial_capital, commission_buy, commission_sell, redemption_fee_pct, target_return_pct, stop_loss_pct, max_hold_days, position_size_pct, max_positions, created_at)
                VALUES ('$pname','$pdesc','$stype','$afilt',$cap,$cb,$cs,$rf,$tp,$sl,$mhd,$psz,$mpos,'$now')";
        if ($conn->query($sql)) {
            $port_count++;
        }
    }
}
$results['actions'][] = 'Seeded ' . $port_count . ' portfolio templates';

// Log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$ip = $conn->real_escape_string($ip);
$conn->query("INSERT INTO mf2_audit_log (action_type, details, ip_address, created_at) VALUES ('setup_schema', 'MF Schema v2 created/verified', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
