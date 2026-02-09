<?php
/**
 * Setup database schema for Crypto Pairs Portfolio Analysis
 * Creates cp_ prefixed tables. PHP 5.2 compatible.
 * Usage: GET .../setup_schema.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'actions' => array());

$tables = array(
    "CREATE TABLE IF NOT EXISTS cp_pairs (
        pair VARCHAR(15) PRIMARY KEY,
        pair_name VARCHAR(100) NOT NULL DEFAULT '',
        base_asset VARCHAR(10) NOT NULL DEFAULT '',
        quote_asset VARCHAR(10) NOT NULL DEFAULT 'USD',
        category VARCHAR(50) NOT NULL DEFAULT 'large_cap',
        yahoo_ticker VARCHAR(20) NOT NULL DEFAULT ''
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS cp_prices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pair VARCHAR(15) NOT NULL,
        trade_date DATE NOT NULL,
        open_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        high_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        low_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        close_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        volume BIGINT NOT NULL DEFAULT 0,
        UNIQUE KEY idx_pair_date (pair, trade_date),
        KEY idx_date (trade_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS cp_strategies (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        strategy_type VARCHAR(50) NOT NULL DEFAULT 'trend',
        ideal_timeframe VARCHAR(20) NOT NULL DEFAULT '1d',
        UNIQUE KEY idx_name (name)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS cp_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pair VARCHAR(15) NOT NULL,
        strategy_name VARCHAR(100) NOT NULL DEFAULT '',
        signal_date DATE NOT NULL,
        signal_time DATETIME NOT NULL,
        direction VARCHAR(10) NOT NULL DEFAULT 'long',
        entry_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        stop_loss_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        take_profit_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        signal_hash VARCHAR(64) NOT NULL DEFAULT '',
        score INT NOT NULL DEFAULT 0,
        KEY idx_pair (pair),
        KEY idx_strategy (strategy_name),
        KEY idx_date (signal_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS cp_backtest_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        run_name VARCHAR(200) NOT NULL DEFAULT '',
        strategy_filter VARCHAR(500) NOT NULL DEFAULT '',
        params_json TEXT,
        total_trades INT NOT NULL DEFAULT 0,
        win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
        total_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        sharpe_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
        max_drawdown_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        total_fees DECIMAL(12,2) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS cp_audit_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action_type VARCHAR(50) NOT NULL,
        details TEXT,
        ip_address VARCHAR(45) NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8",

    "CREATE TABLE IF NOT EXISTS cp_report_cache (
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
    array('HODL',                'Buy and hold long-term through volatility.',                            'hold',        '1w'),
    array('DCA',                 'Dollar Cost Average — buy fixed amounts at regular intervals.',         'dca',         '1w'),
    array('Trend Following',     'Follow BTC/ETH macro trend using moving averages.',                    'trend',       '1d'),
    array('Breakout Trading',    'Enter on breakout above key resistance with volume confirmation.',     'breakout',    '4h'),
    array('Swing Trading',       'Capture medium-term swings between support and resistance.',           'swing',       '1d'),
    array('Mean Reversion',      'Buy oversold conditions, sell overbought using RSI/Bollinger.',        'mean_revert', '4h'),
    array('Momentum',            'Trade coins showing strong short-term momentum.',                       'momentum',    '1d'),
    array('Alt Season',          'Rotate into altcoins when BTC dominance is falling.',                  'rotation',    '1w'),
    array('Scalping',            'Quick intraday trades on high-volume pairs.',                           'scalp',       '15m'),
    array('Grid Trading',        'Place buy/sell orders at regular intervals in a range.',               'grid',        '1d')
);

$strat_count = 0;
foreach ($strats as $s) {
    $name = $conn->real_escape_string($s[0]);
    $desc = $conn->real_escape_string($s[1]);
    $stype = $conn->real_escape_string($s[2]);
    $tf = $conn->real_escape_string($s[3]);
    $sql = "INSERT INTO cp_strategies (name, description, strategy_type, ideal_timeframe)
            VALUES ('$name','$desc','$stype','$tf')
            ON DUPLICATE KEY UPDATE description='$desc', strategy_type='$stype', ideal_timeframe='$tf'";
    if ($conn->query($sql)) $strat_count++;
}
$results['actions'][] = 'Seeded ' . $strat_count . ' strategies';

// ─── Seed crypto pairs ───
$pairs = array(
    array('BTC-USD',  'Bitcoin / USD',              'BTC',  'USD', 'large_cap',  'BTC-USD'),
    array('ETH-USD',  'Ethereum / USD',             'ETH',  'USD', 'large_cap',  'ETH-USD'),
    array('SOL-USD',  'Solana / USD',               'SOL',  'USD', 'large_cap',  'SOL-USD'),
    array('XRP-USD',  'XRP / USD',                  'XRP',  'USD', 'large_cap',  'XRP-USD'),
    array('ADA-USD',  'Cardano / USD',              'ADA',  'USD', 'large_cap',  'ADA-USD'),
    array('DOGE-USD', 'Dogecoin / USD',             'DOGE', 'USD', 'meme',       'DOGE-USD'),
    array('DOT-USD',  'Polkadot / USD',             'DOT',  'USD', 'mid_cap',    'DOT-USD'),
    array('AVAX-USD', 'Avalanche / USD',            'AVAX', 'USD', 'mid_cap',    'AVAX-USD'),
    array('LINK-USD', 'Chainlink / USD',            'LINK', 'USD', 'mid_cap',    'LINK-USD'),
    array('MATIC-USD','Polygon / USD',              'MATIC','USD', 'mid_cap',    'MATIC-USD'),
    array('UNI-USD',  'Uniswap / USD',              'UNI',  'USD', 'defi',       'UNI-USD'),
    array('AAVE-USD', 'Aave / USD',                 'AAVE', 'USD', 'defi',       'AAVE-USD'),
    array('LTC-USD',  'Litecoin / USD',             'LTC',  'USD', 'large_cap',  'LTC-USD'),
    array('ATOM-USD', 'Cosmos / USD',               'ATOM', 'USD', 'mid_cap',    'ATOM-USD'),
    array('SHIB-USD', 'Shiba Inu / USD',            'SHIB', 'USD', 'meme',       'SHIB-USD')
);

$pair_count = 0;
foreach ($pairs as $p) {
    $pair = $conn->real_escape_string($p[0]);
    $pname = $conn->real_escape_string($p[1]);
    $base = $conn->real_escape_string($p[2]);
    $quote = $conn->real_escape_string($p[3]);
    $cat = $conn->real_escape_string($p[4]);
    $yticker = $conn->real_escape_string($p[5]);
    $sql = "INSERT INTO cp_pairs (pair, pair_name, base_asset, quote_asset, category, yahoo_ticker)
            VALUES ('$pair','$pname','$base','$quote','$cat','$yticker')
            ON DUPLICATE KEY UPDATE pair_name='$pname', category='$cat', yahoo_ticker='$yticker'";
    if ($conn->query($sql)) $pair_count++;
}
$results['actions'][] = 'Seeded ' . $pair_count . ' pairs';

echo json_encode($results);
$conn->close();
?>
