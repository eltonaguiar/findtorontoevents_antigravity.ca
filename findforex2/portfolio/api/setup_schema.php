<?php
/**
 * Setup database schema for Forex Portfolio Analysis
 * All tables prefixed with fxp_ to distinguish from stock/mf tables.
 * PHP 5.2 compatible.
 *
 * Usage: GET https://findtorontoevents.ca/findforex2/portfolio/api/setup_schema.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'actions' => array());

// --- Core Data Tables (all prefixed fxp_) ---

$tables = array(

// 1. Forex pairs master list
"CREATE TABLE IF NOT EXISTS fxp_pairs (
    symbol VARCHAR(20) NOT NULL,
    base_currency VARCHAR(10) NOT NULL DEFAULT '',
    quote_currency VARCHAR(10) NOT NULL DEFAULT '',
    category VARCHAR(30) NOT NULL DEFAULT 'major',
    pip_value DECIMAL(10,6) NOT NULL DEFAULT 0.0001,
    PRIMARY KEY (symbol)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 2. Daily price history (OHLCV)
"CREATE TABLE IF NOT EXISTS fxp_price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,
    open_price DECIMAL(12,6) NOT NULL DEFAULT 0,
    high_price DECIMAL(12,6) NOT NULL DEFAULT 0,
    low_price DECIMAL(12,6) NOT NULL DEFAULT 0,
    close_price DECIMAL(12,6) NOT NULL DEFAULT 0,
    volume BIGINT NOT NULL DEFAULT 0,
    UNIQUE KEY idx_symbol_date (symbol, price_date),
    KEY idx_date (price_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 3. Forex algorithm definitions
"CREATE TABLE IF NOT EXISTS fxp_algorithms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    family VARCHAR(50) NOT NULL DEFAULT '',
    description TEXT,
    algo_type VARCHAR(50) NOT NULL DEFAULT 'general',
    ideal_timeframe VARCHAR(20) NOT NULL DEFAULT '',
    UNIQUE KEY idx_name (name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 4. Pair picks from algorithms
"CREATE TABLE IF NOT EXISTS fxp_pair_picks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    algorithm_id INT NOT NULL DEFAULT 0,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    pick_date DATE NOT NULL,
    pick_time DATETIME NOT NULL,
    entry_price DECIMAL(12,6) NOT NULL DEFAULT 0,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    score INT NOT NULL DEFAULT 0,
    rating VARCHAR(20) NOT NULL DEFAULT '',
    risk_level VARCHAR(20) NOT NULL DEFAULT 'Medium',
    timeframe VARCHAR(20) NOT NULL DEFAULT '',
    pick_hash VARCHAR(64) NOT NULL DEFAULT '',
    KEY idx_symbol (symbol),
    KEY idx_algorithm (algorithm_name),
    KEY idx_date (pick_date),
    KEY idx_hash (pick_hash)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 5. Portfolio definitions (forex strategies)
"CREATE TABLE IF NOT EXISTS fxp_portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL DEFAULT 'balanced',
    algorithm_filter VARCHAR(500) NOT NULL DEFAULT '',
    initial_capital DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    leverage INT NOT NULL DEFAULT 1,
    spread_pips DECIMAL(6,2) NOT NULL DEFAULT 1.5,
    stop_loss_pips DECIMAL(8,2) NOT NULL DEFAULT 50.00,
    take_profit_pips DECIMAL(8,2) NOT NULL DEFAULT 100.00,
    max_hold_days INT NOT NULL DEFAULT 30,
    position_size_pct DECIMAL(5,2) NOT NULL DEFAULT 2.00,
    max_positions INT NOT NULL DEFAULT 5,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 6. Backtest results (aggregate per run) - pip-based metrics
"CREATE TABLE IF NOT EXISTS fxp_backtest_results (
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
    avg_win_pips DECIMAL(10,2) NOT NULL DEFAULT 0,
    avg_loss_pips DECIMAL(10,2) NOT NULL DEFAULT 0,
    best_trade_pips DECIMAL(10,2) NOT NULL DEFAULT 0,
    worst_trade_pips DECIMAL(10,2) NOT NULL DEFAULT 0,
    max_drawdown_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    total_spread_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
    sharpe_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
    sortino_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
    profit_factor DECIMAL(10,4) NOT NULL DEFAULT 0,
    expectancy_pips DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_hold_days DECIMAL(8,2) NOT NULL DEFAULT 0,
    leverage_used INT NOT NULL DEFAULT 1,
    params_json TEXT,
    created_at DATETIME NOT NULL,
    KEY idx_portfolio (portfolio_id),
    KEY idx_strategy (strategy_type)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 7. Individual trade records from backtests
"CREATE TABLE IF NOT EXISTS fxp_backtest_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    backtest_id INT NOT NULL DEFAULT 0,
    symbol VARCHAR(20) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    entry_date DATE NOT NULL,
    entry_price DECIMAL(12,6) NOT NULL DEFAULT 0,
    exit_date DATE,
    exit_price DECIMAL(12,6) NOT NULL DEFAULT 0,
    lot_size DECIMAL(12,4) NOT NULL DEFAULT 0,
    pip_profit DECIMAL(10,2) NOT NULL DEFAULT 0,
    spread_cost DECIMAL(8,2) NOT NULL DEFAULT 0,
    gross_profit DECIMAL(12,2) NOT NULL DEFAULT 0,
    net_profit DECIMAL(12,2) NOT NULL DEFAULT 0,
    return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(50) NOT NULL DEFAULT '',
    hold_days INT NOT NULL DEFAULT 0,
    KEY idx_backtest (backtest_id),
    KEY idx_symbol (symbol)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 8. What-if scenario history
"CREATE TABLE IF NOT EXISTS fxp_whatif_scenarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario_name VARCHAR(200) NOT NULL DEFAULT '',
    query_text TEXT,
    params_json TEXT,
    results_json TEXT,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 9. Audit log
"CREATE TABLE IF NOT EXISTS fxp_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    KEY idx_action (action_type),
    KEY idx_date (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 10. Algorithm performance summary
"CREATE TABLE IF NOT EXISTS fxp_algo_performance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    algorithm_name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL DEFAULT '',
    total_picks INT NOT NULL DEFAULT 0,
    total_trades INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_pips DECIMAL(10,2) NOT NULL DEFAULT 0,
    best_for VARCHAR(200) NOT NULL DEFAULT '',
    worst_for VARCHAR(200) NOT NULL DEFAULT '',
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_algo_strat (algorithm_name, strategy_type)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 11. Portfolio comparison results
"CREATE TABLE IF NOT EXISTS fxp_comparisons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comparison_name VARCHAR(200) NOT NULL DEFAULT '',
    scenarios_json TEXT,
    best_scenario VARCHAR(200) NOT NULL DEFAULT '',
    worst_scenario VARCHAR(200) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 12. Pair category performance tracking
"CREATE TABLE IF NOT EXISTS fxp_category_perf (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(200) NOT NULL,
    period VARCHAR(20) NOT NULL DEFAULT '1m',
    avg_pips DECIMAL(10,2) NOT NULL DEFAULT 0,
    top_pair VARCHAR(20) NOT NULL DEFAULT '',
    worst_pair VARCHAR(20) NOT NULL DEFAULT '',
    pair_count INT NOT NULL DEFAULT 0,
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

// --- Seed forex algorithms ---
$algos = array(
    array('FX Trend Following',  'Trend',      '200 SMA crossover direction. Goes long above SMA, short below. Classic trend system for forex.', 'trend', '1d'),
    array('FX Momentum',         'Momentum',   'RSI + MACD divergence system. Identifies momentum shifts using multi-indicator confirmation.', 'momentum', '4h'),
    array('FX Mean Reversion',   'Contrarian', 'Bollinger Band bounce strategy. Fades moves to upper/lower bands expecting reversion to mean.', 'mean_reversion', '1h'),
    array('FX Carry Trade',      'Carry',      'Interest rate differential strategy. Longs high-yield currencies, shorts low-yield. Earns swap income.', 'carry', '1w'),
    array('FX Breakout',         'Breakout',   'Range breakout detection. Identifies consolidation zones and trades the breakout direction.', 'breakout', '4h'),
    array('FX Scalper',          'Scalper',    'Quick 10-20 pip targets with tight stops. High-frequency entries on short timeframes.', 'scalp', '15m'),
    array('FX Swing',            'Swing',      'Multi-day position trades. Captures larger moves using daily chart patterns and key levels.', 'swing', '1d'),
    array('FX CAD Focus',        'Regional',   'Specialized in USD/CAD and CAD crosses. Uses oil correlation and Bank of Canada policy analysis.', 'regional', '4h')
);

$algo_count = 0;
foreach ($algos as $a) {
    $name  = $conn->real_escape_string($a[0]);
    $fam   = $conn->real_escape_string($a[1]);
    $desc  = $conn->real_escape_string($a[2]);
    $atype = $conn->real_escape_string($a[3]);
    $tf    = $conn->real_escape_string($a[4]);
    $sql = "INSERT INTO fxp_algorithms (name, family, description, algo_type, ideal_timeframe)
            VALUES ('$name','$fam','$desc','$atype','$tf')
            ON DUPLICATE KEY UPDATE family='$fam', description='$desc', algo_type='$atype', ideal_timeframe='$tf'";
    if ($conn->query($sql)) {
        $algo_count++;
    }
}
$results['actions'][] = 'Seeded ' . $algo_count . ' forex algorithms';

// --- Seed portfolio templates ---
$now = date('Y-m-d H:i:s');
// name, desc, strategy_type, algo_filter, capital, leverage, spread, sl_pips, tp_pips, max_hold, pos_size, max_pos
$portfolios = array(
    // Scalper
    array('Scalper',             'Tight stops, quick 10-20 pip targets. High frequency.',               'scalp',        'FX Scalper',             10000, 50, 1.0,  15,   20,   1,  2, 10),
    // Day Trader
    array('Day Trader',          'Intraday positions closed by end of session. 30-50 pip targets.',     'day_trade',     'FX Momentum,FX Breakout', 10000, 30, 1.5,  30,   50,   1,  3, 8),
    // Swing Trader
    array('Swing Trader',        'Multi-day positions. 100-200 pip targets over 3-10 days.',            'swing',         'FX Swing,FX Trend Following', 10000, 10, 1.5, 80, 200,  10, 5, 5),
    // Carry Trade
    array('Carry Trade',         'Long high-yield currencies. Earns swap/interest differential.',       'carry',         'FX Carry Trade',         10000,  5, 2.0,  150, 300,  60, 5, 4),
    // Trend Following
    array('Trend Following',     'Follow major trends using 200 SMA. Large targets, wide stops.',       'trend',         'FX Trend Following',     10000, 10, 1.5,  100, 250,  30, 5, 5),
    // Conservative
    array('Conservative',        'Low leverage, wide stops, patient entries. Risk-averse approach.',     'conservative',  '',                       10000,  3, 2.0,  100, 150,  30, 2, 3),
    // Aggressive
    array('Aggressive',          'High leverage, tight stops. High risk/reward ratio.',                  'aggressive',    'FX Momentum,FX Breakout', 10000, 50, 1.0,  25,  75,    5, 5, 10),
    // CAD Pairs Only
    array('CAD Pairs Only',      'Exclusively trades CAD crosses. Uses oil/BoC correlation.',           'regional',      'FX CAD Focus',           10000, 10, 1.5,  60, 120,   14, 5, 4),
    // Major Pairs Only
    array('Major Pairs Only',    'Only trades EUR/USD, GBP/USD, USD/JPY. Most liquid pairs.',           'major_only',    '',                       10000, 10, 1.0,  50, 100,   14, 3, 5),
    // Balanced
    array('Balanced',            'Mix of scalping, swing, and trend. Diversified timeframe approach.',  'balanced',      '',                       10000, 10, 1.5,  60, 120,   14, 3, 6)
);

$port_count = 0;
foreach ($portfolios as $p) {
    $pname = $conn->real_escape_string($p[0]);
    $pdesc = $conn->real_escape_string($p[1]);
    $stype = $conn->real_escape_string($p[2]);
    $afilt = $conn->real_escape_string($p[3]);
    $cap   = (float)$p[4];
    $lev   = (int)$p[5];
    $spr   = (float)$p[6];
    $sl    = (float)$p[7];
    $tp    = (float)$p[8];
    $mhd   = (int)$p[9];
    $psz   = (float)$p[10];
    $mpos  = (int)$p[11];

    $chk = $conn->query("SELECT id FROM fxp_portfolios WHERE name='$pname'");
    if ($chk && $chk->num_rows == 0) {
        $sql = "INSERT INTO fxp_portfolios (name, description, strategy_type, algorithm_filter, initial_capital, leverage, spread_pips, stop_loss_pips, take_profit_pips, max_hold_days, position_size_pct, max_positions, created_at)
                VALUES ('$pname','$pdesc','$stype','$afilt',$cap,$lev,$spr,$sl,$tp,$mhd,$psz,$mpos,'$now')";
        if ($conn->query($sql)) {
            $port_count++;
        }
    }
}
$results['actions'][] = 'Seeded ' . $port_count . ' portfolio templates';

// Log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$ip = $conn->real_escape_string($ip);
$conn->query("INSERT INTO fxp_audit_log (action_type, details, ip_address, created_at) VALUES ('setup_schema', 'FX Schema created/verified', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
