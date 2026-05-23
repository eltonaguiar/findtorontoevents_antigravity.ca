<?php
/**
 * Setup database schema for Forex Portfolio Analysis
 * Creates fx_ prefixed tables. PHP 5.2 compatible.
 * Usage: GET .../setup_schema.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'actions' => array());

$tables = array(
    "CREATE TABLE IF NOT EXISTS fx_pairs (
        pair VARCHAR(10) PRIMARY KEY,
        pair_name VARCHAR(100) NOT NULL DEFAULT '',
        base_currency VARCHAR(5) NOT NULL DEFAULT '',
        quote_currency VARCHAR(5) NOT NULL DEFAULT '',
        category VARCHAR(50) NOT NULL DEFAULT 'major',
        pip_value DECIMAL(10,6) NOT NULL DEFAULT 0.0001,
        yahoo_ticker VARCHAR(20) NOT NULL DEFAULT ''
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS fx_prices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pair VARCHAR(10) NOT NULL,
        trade_date DATE NOT NULL,
        open_price DECIMAL(12,6) NOT NULL DEFAULT 0,
        high_price DECIMAL(12,6) NOT NULL DEFAULT 0,
        low_price DECIMAL(12,6) NOT NULL DEFAULT 0,
        close_price DECIMAL(12,6) NOT NULL DEFAULT 0,
        volume BIGINT NOT NULL DEFAULT 0,
        UNIQUE KEY idx_pair_date (pair, trade_date),
        KEY idx_date (trade_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS fx_strategies (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        strategy_type VARCHAR(50) NOT NULL DEFAULT 'trend',
        ideal_timeframe VARCHAR(20) NOT NULL DEFAULT '1d',
        UNIQUE KEY idx_name (name)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS fx_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pair VARCHAR(10) NOT NULL,
        strategy_name VARCHAR(100) NOT NULL DEFAULT '',
        signal_date DATE NOT NULL,
        signal_time DATETIME NOT NULL,
        direction VARCHAR(10) NOT NULL DEFAULT 'long',
        entry_price DECIMAL(12,6) NOT NULL DEFAULT 0,
        stop_loss_price DECIMAL(12,6) NOT NULL DEFAULT 0,
        take_profit_price DECIMAL(12,6) NOT NULL DEFAULT 0,
        signal_hash VARCHAR(64) NOT NULL DEFAULT '',
        score INT NOT NULL DEFAULT 0,
        KEY idx_pair (pair),
        KEY idx_strategy (strategy_name),
        KEY idx_date (signal_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS fx_backtest_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        run_name VARCHAR(200) NOT NULL DEFAULT '',
        strategy_filter VARCHAR(500) NOT NULL DEFAULT '',
        params_json TEXT,
        total_trades INT NOT NULL DEFAULT 0,
        win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
        total_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        sharpe_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
        max_drawdown_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        total_spread_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS fx_audit_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action_type VARCHAR(50) NOT NULL,
        details TEXT,
        ip_address VARCHAR(45) NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS fx_report_cache (
        id INT AUTO_INCREMENT PRIMARY KEY,
        report_date DATE NOT NULL,
        report_json LONGTEXT,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_date (report_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8"
);

foreach ($tables as $sql) {
    if ($conn->query($sql)) {
        preg_match('/TABLE IF NOT EXISTS (\w+)/', $sql, $m);
        $results['actions'][] = 'OK: ' . (isset($m[1]) ? $m[1] : 'table');
    } else {
        $results['actions'][] = 'FAIL: ' . $conn->error;
    }
}

// ─── Seed strategies ───
$strats = array(
    array('Trend Following',     'Follow the prevailing trend using moving average crossovers.',           'trend',       '1d'),
    array('Mean Reversion',      'Trade when price deviates significantly from its average.',              'mean_revert', '4h'),
    array('Breakout',            'Enter on price breaking key support/resistance levels.',                 'breakout',    '1d'),
    array('Carry Trade',         'Exploit interest rate differentials between currency pairs.',            'carry',       '1w'),
    array('Momentum',            'Trade in the direction of strong recent price movement.',                'momentum',    '4h'),
    array('Range Trading',       'Buy at support and sell at resistance in ranging markets.',              'range',       '1d'),
    array('Scalping',            'Quick intraday trades capturing small pip movements.',                   'scalp',       '15m'),
    array('Swing Trading',       'Hold positions for days to capture medium-term moves.',                  'swing',       '1d')
);

$strat_count = 0;
foreach ($strats as $s) {
    $name = $conn->real_escape_string($s[0]);
    $desc = $conn->real_escape_string($s[1]);
    $stype = $conn->real_escape_string($s[2]);
    $tf = $conn->real_escape_string($s[3]);
    $sql = "INSERT INTO fx_strategies (name, description, strategy_type, ideal_timeframe)
            VALUES ('$name','$desc','$stype','$tf')
            ON DUPLICATE KEY UPDATE description='$desc', strategy_type='$stype', ideal_timeframe='$tf'";
    if ($conn->query($sql)) $strat_count++;
}
$results['actions'][] = 'Seeded ' . $strat_count . ' strategies';

// ─── Seed forex pairs ───
$pairs = array(
    array('EURUSD', 'Euro / US Dollar',           'EUR', 'USD', 'major',   0.0001, 'EURUSD=X'),
    array('GBPUSD', 'British Pound / US Dollar',   'GBP', 'USD', 'major',   0.0001, 'GBPUSD=X'),
    array('USDJPY', 'US Dollar / Japanese Yen',    'USD', 'JPY', 'major',   0.01,   'JPY=X'),
    array('USDCAD', 'US Dollar / Canadian Dollar', 'USD', 'CAD', 'major',   0.0001, 'CAD=X'),
    array('AUDUSD', 'Australian Dollar / US Dollar','AUD', 'USD', 'major',   0.0001, 'AUDUSD=X'),
    array('NZDUSD', 'New Zealand Dollar / US Dollar','NZD','USD', 'major',   0.0001, 'NZDUSD=X'),
    array('USDCHF', 'US Dollar / Swiss Franc',     'USD', 'CHF', 'major',   0.0001, 'CHF=X'),
    array('EURGBP', 'Euro / British Pound',        'EUR', 'GBP', 'cross',   0.0001, 'EURGBP=X'),
    array('EURJPY', 'Euro / Japanese Yen',         'EUR', 'JPY', 'cross',   0.01,   'EURJPY=X'),
    array('GBPJPY', 'British Pound / Japanese Yen','GBP', 'JPY', 'cross',   0.01,   'GBPJPY=X'),
    array('EURCHF', 'Euro / Swiss Franc',          'EUR', 'CHF', 'cross',   0.0001, 'EURCHF=X'),
    array('AUDCAD', 'Australian Dollar / CAD',     'AUD', 'CAD', 'cross',   0.0001, 'AUDCAD=X'),
    array('CADJPY', 'Canadian Dollar / Yen',       'CAD', 'JPY', 'cross',   0.01,   'CADJPY=X'),
    array('GBPCAD', 'British Pound / CAD',         'GBP', 'CAD', 'cross',   0.0001, 'GBPCAD=X'),
    array('USDMXN', 'US Dollar / Mexican Peso',   'USD', 'MXN', 'exotic',  0.0001, 'MXN=X')
);

$pair_count = 0;
foreach ($pairs as $p) {
    $pair = $conn->real_escape_string($p[0]);
    $pname = $conn->real_escape_string($p[1]);
    $base = $conn->real_escape_string($p[2]);
    $quote = $conn->real_escape_string($p[3]);
    $cat = $conn->real_escape_string($p[4]);
    $pip = (float)$p[5];
    $yticker = $conn->real_escape_string($p[6]);
    $sql = "INSERT INTO fx_pairs (pair, pair_name, base_currency, quote_currency, category, pip_value, yahoo_ticker)
            VALUES ('$pair','$pname','$base','$quote','$cat',$pip,'$yticker')
            ON DUPLICATE KEY UPDATE pair_name='$pname', category='$cat', yahoo_ticker='$yticker'";
    if ($conn->query($sql)) $pair_count++;
}
$results['actions'][] = 'Seeded ' . $pair_count . ' pairs';

echo json_encode($results);
$conn->close();
?>
