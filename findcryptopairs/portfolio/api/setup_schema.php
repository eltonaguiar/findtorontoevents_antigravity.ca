<?php
/**
 * Setup database schema for Crypto Pairs Portfolio Analysis
 * All tables prefixed with cr_ to distinguish from stock/fund tables.
 * PHP 5.2 compatible.
 *
 * Usage: GET https://findtorontoevents.ca/findcryptopairs/portfolio/api/setup_schema.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'actions' => array());

// ─── Core Data Tables (all prefixed cr_) ───

$tables = array(

// 1. Crypto pairs master list
"CREATE TABLE IF NOT EXISTS cr_pairs (
    symbol VARCHAR(20) NOT NULL,
    base_asset VARCHAR(20) NOT NULL DEFAULT '',
    quote_asset VARCHAR(10) NOT NULL DEFAULT 'USD',
    category VARCHAR(50) NOT NULL DEFAULT 'major',
    pair_name VARCHAR(200) NOT NULL DEFAULT '',
    PRIMARY KEY (symbol)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 2. Daily price history (OHLCV)
"CREATE TABLE IF NOT EXISTS cr_price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,
    open DECIMAL(18,8) NOT NULL DEFAULT 0,
    high DECIMAL(18,8) NOT NULL DEFAULT 0,
    low DECIMAL(18,8) NOT NULL DEFAULT 0,
    close DECIMAL(18,8) NOT NULL DEFAULT 0,
    volume DECIMAL(24,2) NOT NULL DEFAULT 0,
    UNIQUE KEY idx_symbol_date (symbol, price_date),
    KEY idx_date (price_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 3. Crypto algorithm definitions
"CREATE TABLE IF NOT EXISTS cr_algorithms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    family VARCHAR(50) NOT NULL DEFAULT '',
    description TEXT,
    algo_type VARCHAR(50) NOT NULL DEFAULT 'general',
    ideal_timeframe VARCHAR(20) NOT NULL DEFAULT '',
    UNIQUE KEY idx_name (name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 4. Crypto pair picks from algorithms
"CREATE TABLE IF NOT EXISTS cr_pair_picks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    algorithm_id INT NOT NULL DEFAULT 0,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    pick_date DATE NOT NULL,
    pick_time DATETIME NOT NULL,
    entry_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    score INT NOT NULL DEFAULT 0,
    rating VARCHAR(20) NOT NULL DEFAULT '',
    risk_level VARCHAR(20) NOT NULL DEFAULT 'Medium',
    timeframe VARCHAR(20) NOT NULL DEFAULT '',
    pick_hash VARCHAR(64) NOT NULL DEFAULT '',
    rationale_json TEXT,
    KEY idx_symbol (symbol),
    KEY idx_algorithm (algorithm_name),
    KEY idx_date (pick_date),
    KEY idx_hash (pick_hash),
    KEY idx_direction (direction)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 5. Portfolio definitions (crypto strategies)
"CREATE TABLE IF NOT EXISTS cr_portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL DEFAULT 'balanced',
    algorithm_filter VARCHAR(500) NOT NULL DEFAULT '',
    initial_capital DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    stop_loss_pct DECIMAL(5,2) NOT NULL DEFAULT 10.00,
    take_profit_pct DECIMAL(5,2) NOT NULL DEFAULT 20.00,
    max_hold_days INT NOT NULL DEFAULT 90,
    position_size_pct DECIMAL(5,2) NOT NULL DEFAULT 20.00,
    max_positions INT NOT NULL DEFAULT 5,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 6. Backtest results (aggregate per run)
"CREATE TABLE IF NOT EXISTS cr_backtest_results (
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
"CREATE TABLE IF NOT EXISTS cr_backtest_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    backtest_id INT NOT NULL DEFAULT 0,
    symbol VARCHAR(20) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    entry_date DATE NOT NULL,
    entry_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    exit_date DATE,
    exit_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    position_size DECIMAL(12,4) NOT NULL DEFAULT 0,
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
"CREATE TABLE IF NOT EXISTS cr_whatif_scenarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scenario_name VARCHAR(200) NOT NULL DEFAULT '',
    query_text TEXT,
    params_json TEXT,
    results_json TEXT,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 9. Audit log
"CREATE TABLE IF NOT EXISTS cr_audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    KEY idx_action (action_type),
    KEY idx_date (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 10. Algorithm performance summary
"CREATE TABLE IF NOT EXISTS cr_algo_performance (
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
"CREATE TABLE IF NOT EXISTS cr_comparisons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comparison_name VARCHAR(200) NOT NULL DEFAULT '',
    scenarios_json TEXT,
    best_scenario VARCHAR(200) NOT NULL DEFAULT '',
    worst_scenario VARCHAR(200) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 12. Category performance tracking
"CREATE TABLE IF NOT EXISTS cr_category_perf (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(200) NOT NULL,
    period VARCHAR(20) NOT NULL DEFAULT '1m',
    avg_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
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

// ─── Seed crypto algorithms ───
$algos = array(
    array('CR Momentum',         'Momentum',   'RSI + volume surge detection. Buys when RSI crosses above 30 with above-average volume. Sells when RSI exceeds 70.', 'momentum', '1w'),
    array('CR DCA',              'DCA',        'Dollar Cost Averaging - systematic buying at regular intervals regardless of price. Reduces impact of volatility.', 'dca', '1m'),
    array('CR Trend Following',  'Trend',      '50/200 day moving average crossover. Golden cross = buy, death cross = sell. Classic trend system for crypto.', 'trend', '3m'),
    array('CR Mean Reversion',   'Contrarian', 'Buy oversold (RSI<25, price below lower Bollinger Band), sell overbought. Contrarian approach for range-bound markets.', 'mean_reversion', '1w'),
    array('CR Breakout',         'Breakout',   'Range breakout after consolidation. Buys when price breaks above 20-day high with volume confirmation.', 'breakout', '1d'),
    array('CR Sentiment',        'Sentiment',  'Social media sentiment + Fear & Greed Index based entries. Buys at extreme fear, sells at extreme greed.', 'sentiment', '1w'),
    array('CR Halving Cycle',    'Cycle',      'Bitcoin halving cycle timing. Accumulate 6-12 months before halving, take profits 12-18 months after.', 'cycle', '6m'),
    array('CR Altcoin Rotation', 'Rotation',   'Rotate into strongest performing altcoins. Monthly rebalance based on relative strength vs BTC.', 'rotation', '1m')
);

$algo_count = 0;
foreach ($algos as $a) {
    $name  = $conn->real_escape_string($a[0]);
    $fam   = $conn->real_escape_string($a[1]);
    $desc  = $conn->real_escape_string($a[2]);
    $atype = $conn->real_escape_string($a[3]);
    $tf    = $conn->real_escape_string($a[4]);
    $sql = "INSERT INTO cr_algorithms (name, family, description, algo_type, ideal_timeframe)
            VALUES ('$name','$fam','$desc','$atype','$tf')
            ON DUPLICATE KEY UPDATE family='$fam', description='$desc', algo_type='$atype', ideal_timeframe='$tf'";
    if ($conn->query($sql)) {
        $algo_count++;
    }
}
$results['actions'][] = 'Seeded ' . $algo_count . ' crypto algorithms';

// ─── Seed portfolio templates ───
$now = date('Y-m-d H:i:s');
// name, desc, strategy_type, algo_filter, capital, sl, tp, max_hold, pos_size, max_pos
$portfolios = array(
    // HODLer
    array('HODLer (1 Year)',         'Buy and hold for 1 year. No targets, no stops. Pure conviction.',                    'hodl',         '',                        10000, 999, 999, 365, 25, 4),
    // DCA
    array('DCA Weekly',              'Dollar cost average weekly into top crypto. Systematic accumulation.',                 'dca',          'CR DCA',                  10000, 999, 999, 365, 10, 10),
    array('DCA Monthly',             'Monthly DCA into blue chip crypto. Lower frequency, lower fees.',                      'dca',          'CR DCA',                  10000, 999, 999, 365, 20, 5),
    // Swing
    array('Swing Trader',            'Swing trade crypto on 1-4 week cycles. Momentum + breakout signals.',                  'swing',        'CR Momentum,CR Breakout', 10000, 15, 25, 30,  25, 4),
    // Day Trader
    array('Day Trader',              'Short-term trades, tight stops, quick profits. High frequency.',                       'day_trade',    'CR Breakout,CR Momentum', 10000, 5,  8,  3,   20, 5),
    // Conservative
    array('Conservative (BTC/ETH)',  'BTC and ETH only. Blue chip crypto with trend following.',                              'conservative', 'CR Trend Following',      10000, 10, 20, 120, 50, 2),
    // Aggressive
    array('Aggressive Altcoins',     'High-beta altcoins. Rotation + momentum for maximum upside.',                           'aggressive',   'CR Altcoin Rotation,CR Momentum', 10000, 20, 50, 60, 20, 5),
    // Meme
    array('Meme Coin Gambler',       'High risk meme coins. Sentiment-driven entries, wide stops.',                           'meme',         'CR Sentiment,CR Breakout', 5000, 30, 100, 14, 10, 10),
    // Blue Chip
    array('Blue Chip Crypto',        'Top 5 crypto by market cap. Halving cycle + trend following.',                          'blue_chip',    'CR Halving Cycle,CR Trend Following', 10000, 15, 30, 180, 20, 5),
    // Balanced
    array('Balanced Portfolio',      'Mix of strategies: trend, mean reversion, and DCA across major pairs.',                 'balanced',     '',                        10000, 12, 20, 90,  20, 5)
);

$port_count = 0;
foreach ($portfolios as $p) {
    $pname = $conn->real_escape_string($p[0]);
    $pdesc = $conn->real_escape_string($p[1]);
    $stype = $conn->real_escape_string($p[2]);
    $afilt = $conn->real_escape_string($p[3]);
    $cap   = (float)$p[4];
    $sl    = (float)$p[5];
    $tp    = (float)$p[6];
    $mhd   = (int)$p[7];
    $psz   = (float)$p[8];
    $mpos  = (int)$p[9];

    $chk = $conn->query("SELECT id FROM cr_portfolios WHERE name='$pname'");
    if ($chk && $chk->num_rows == 0) {
        $sql = "INSERT INTO cr_portfolios (name, description, strategy_type, algorithm_filter, initial_capital, stop_loss_pct, take_profit_pct, max_hold_days, position_size_pct, max_positions, created_at)
                VALUES ('$pname','$pdesc','$stype','$afilt',$cap,$sl,$tp,$mhd,$psz,$mpos,'$now')";
        if ($conn->query($sql)) {
            $port_count++;
        }
    }
}
$results['actions'][] = 'Seeded ' . $port_count . ' portfolio templates';

// Log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$ip = $conn->real_escape_string($ip);
$conn->query("INSERT INTO cr_audit_log (action_type, details, ip_address, created_at) VALUES ('setup_schema', 'CR Schema created/verified', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
