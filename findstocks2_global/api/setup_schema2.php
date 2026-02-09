<?php
/**
 * Setup database schema for DayTrades Miracle Claude
 * Creates all "2"-suffixed tables and seeds strategies + portfolios.
 * PHP 5.2 compatible.
 *
 * Usage: GET https://findtorontoevents.ca/findstocks2_global/api/setup_schema2.php
 */
require_once dirname(__FILE__) . '/db_connect2.php';

$results = array('ok' => true, 'actions' => array());

$tables = array(

// 1. Miracle strategies (the 8 scanning algorithms)
"CREATE TABLE IF NOT EXISTS miracle_strategies2 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    family VARCHAR(50) NOT NULL DEFAULT '',
    description TEXT,
    scan_type VARCHAR(50) NOT NULL DEFAULT 'momentum',
    ideal_hold VARCHAR(20) NOT NULL DEFAULT '1d',
    default_tp_pct DECIMAL(5,2) NOT NULL DEFAULT 5.00,
    default_sl_pct DECIMAL(5,2) NOT NULL DEFAULT 3.00,
    enabled TINYINT NOT NULL DEFAULT 1,
    UNIQUE KEY idx_name (name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 2. Miracle picks (individual stock picks with levels)
"CREATE TABLE IF NOT EXISTS miracle_picks2 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    scan_date DATE NOT NULL,
    scan_time DATETIME NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    stop_loss_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    take_profit_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    stop_loss_pct DECIMAL(5,2) NOT NULL DEFAULT 0,
    take_profit_pct DECIMAL(5,2) NOT NULL DEFAULT 0,
    score INT NOT NULL DEFAULT 0,
    confidence VARCHAR(20) NOT NULL DEFAULT 'medium',
    signals_json TEXT,
    is_cdr TINYINT NOT NULL DEFAULT 0,
    questrade_fee DECIMAL(8,2) NOT NULL DEFAULT 0,
    net_profit_if_tp DECIMAL(12,2) NOT NULL DEFAULT 0,
    risk_reward_ratio DECIMAL(5,2) NOT NULL DEFAULT 0,
    outcome VARCHAR(20) NOT NULL DEFAULT 'pending',
    outcome_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    outcome_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    outcome_date DATE,
    pick_hash VARCHAR(64) NOT NULL DEFAULT '',
    KEY idx_ticker (ticker),
    KEY idx_strategy (strategy_name),
    KEY idx_date (scan_date),
    KEY idx_outcome (outcome),
    KEY idx_hash (pick_hash)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 3. Miracle portfolios (strategy combinations with capital/risk settings)
"CREATE TABLE IF NOT EXISTS miracle_portfolios2 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    strategy_filter VARCHAR(500) NOT NULL DEFAULT '',
    initial_capital DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
    position_size_pct DECIMAL(5,2) NOT NULL DEFAULT 10.00,
    max_positions INT NOT NULL DEFAULT 5,
    fee_model VARCHAR(20) NOT NULL DEFAULT 'questrade',
    prefer_cdr TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 4. Miracle results (aggregated performance per strategy/portfolio)
"CREATE TABLE IF NOT EXISTS miracle_results2 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL DEFAULT 0,
    strategy_name VARCHAR(100) NOT NULL DEFAULT '',
    period VARCHAR(20) NOT NULL DEFAULT 'daily',
    calc_date DATE NOT NULL,
    total_picks INT NOT NULL DEFAULT 0,
    winners INT NOT NULL DEFAULT 0,
    losers INT NOT NULL DEFAULT 0,
    pending_count INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_gain_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_loss_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    total_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    best_pick_ticker VARCHAR(10) NOT NULL DEFAULT '',
    best_pick_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    worst_pick_ticker VARCHAR(10) NOT NULL DEFAULT '',
    worst_pick_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    sharpe_ratio DECIMAL(10,4) NOT NULL DEFAULT 0,
    profit_factor DECIMAL(10,4) NOT NULL DEFAULT 0,
    expectancy DECIMAL(10,4) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    KEY idx_strategy (strategy_name),
    KEY idx_date (calc_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 5. Miracle watchlist (universe of tickers to scan)
"CREATE TABLE IF NOT EXISTS miracle_watchlist2 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(200) NOT NULL DEFAULT '',
    sector VARCHAR(100) NOT NULL DEFAULT '',
    reason TEXT,
    is_cdr TINYINT NOT NULL DEFAULT 0,
    added_date DATE NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'scanner',
    active TINYINT NOT NULL DEFAULT 1,
    UNIQUE KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 6. Miracle audit log
"CREATE TABLE IF NOT EXISTS miracle_audit2 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    KEY idx_action (action_type),
    KEY idx_date (created_at)
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

// ─── Seed the 8 Miracle Strategies ───
$strategies = array(
    array('Gap Up Momentum',        'momentum',     'Stocks gapping up >3% from previous close with volume >2x average. Targets continuation of gap momentum. Best for first 30 min of trading.',                                    'gap_scanner',     '1d',  8.00, 3.00),
    array('Volume Surge Breakout',  'breakout',     'Unusual volume (>3x 20-day avg) with price breaking 20-day high. RSI < 80 filter prevents chasing overextended moves. ATR-based targets.',                                      'volume_scanner',  '1-2d', 7.00, 3.50),
    array('Oversold Bounce',        'mean_reversion','RSI(14) < 30 + price at or below Bollinger lower band + volume uptick. Reversal candle after 3+ red days. Targets middle Bollinger band.',                                    'reversal',        '1-3d', 5.00, 3.00),
    array('Momentum Continuation',  'momentum',     'Strong uptrend (SMA20 > SMA50) + pullback to SMA20 + bounce with volume. Targets previous swing high. Trend-following with mean-reversion entry.',                              'trend_pullback',  '2-5d', 6.00, 3.00),
    array('Earnings Catalyst Runner','event_driven', 'Post-earnings gap up with volume >3x avg (PEAD effect). Targets 10% continuation. Stop at gap fill level. Best within 5 days of earnings.',                                    'earnings',        '3-10d',10.00, 5.00),
    array('CDR Zero-Fee Play',      'fee_optimized','Specifically targets CDR-available stocks (37 tickers) showing any momentum signal. Zero commission = lower breakeven = higher net profit on same moves.',                       'cdr_filter',      '1-3d', 4.00, 2.00),
    array('Sector Momentum Leader', 'sector',       'Identifies strongest sector of the day, picks leading stock outperforming sector ETF by >2%. Sector momentum tends to persist intraday.',                                       'sector_scan',     '1d',   5.00, 2.00),
    array('Mean Reversion Sniper',  'mean_reversion','Z-score < -2 (price 2 std devs below 20-day mean) with volume confirmation. SMA200 still rising = not broken trend. Targets Z-score return to 0.',                            'zscore_reversal', '2-5d', 6.00, 4.00)
);

$strat_count = 0;
foreach ($strategies as $s) {
    $name  = $conn->real_escape_string($s[0]);
    $fam   = $conn->real_escape_string($s[1]);
    $desc  = $conn->real_escape_string($s[2]);
    $stype = $conn->real_escape_string($s[3]);
    $hold  = $conn->real_escape_string($s[4]);
    $tp    = (float)$s[5];
    $sl    = (float)$s[6];
    $sql = "INSERT INTO miracle_strategies2 (name, family, description, scan_type, ideal_hold, default_tp_pct, default_sl_pct)
            VALUES ('$name','$fam','$desc','$stype','$hold',$tp,$sl)
            ON DUPLICATE KEY UPDATE family='$fam', description='$desc', scan_type='$stype', ideal_hold='$hold', default_tp_pct=$tp, default_sl_pct=$sl";
    if ($conn->query($sql)) {
        $strat_count++;
    }
}
$results['actions'][] = 'Seeded ' . $strat_count . ' miracle strategies';

// ─── Seed Portfolio Templates ───
$now = date('Y-m-d H:i:s');
$portfolios = array(
    // name, description, strategy_filter, capital, pos_size%, max_pos, fee_model, prefer_cdr
    array('DayTrades Miracle All-In',      'All 8 strategies, CDR preferred, aggressive sizing',             '',                           10000, 20.00, 5,  'questrade', 1),
    array('CDR-Only Miracle',              'Only CDR tickers for zero-fee day trading',                      'CDR Zero-Fee Play',          10000, 25.00, 4,  'questrade', 1),
    array('Momentum Miracle',              'Gap Up + Volume Surge + Momentum Continuation',                  'Gap Up Momentum,Volume Surge Breakout,Momentum Continuation', 10000, 15.00, 5, 'questrade', 1),
    array('Reversal Miracle',              'Oversold Bounce + Mean Reversion Sniper',                        'Oversold Bounce,Mean Reversion Sniper', 10000, 15.00, 4, 'questrade', 1),
    array('Earnings Miracle',              'Post-earnings runners only',                                     'Earnings Catalyst Runner',   10000, 10.00, 3,  'questrade', 1),
    array('Sector Surge Miracle',          'Sector leaders + momentum',                                      'Sector Momentum Leader,Gap Up Momentum', 10000, 15.00, 5, 'questrade', 1),
    array('Conservative Miracle',          'Lower risk: CDR-only + reversals with tight stops',              'CDR Zero-Fee Play,Oversold Bounce', 5000, 10.00, 3, 'questrade', 1),
    array('YOLO Miracle',                  'Maximum aggression: all strategies, big positions, loose stops',  '',                           25000, 25.00, 8,  'questrade', 0)
);

$port_count = 0;
foreach ($portfolios as $p) {
    $pname = $conn->real_escape_string($p[0]);
    $chk = $conn->query("SELECT id FROM miracle_portfolios2 WHERE name='$pname'");
    if ($chk && $chk->num_rows == 0) {
        $pdesc = $conn->real_escape_string($p[1]);
        $sfilt = $conn->real_escape_string($p[2]);
        $cap   = (float)$p[3];
        $psz   = (float)$p[4];
        $mpos  = (int)$p[5];
        $fm    = $conn->real_escape_string($p[6]);
        $pcdr  = (int)$p[7];
        $sql = "INSERT INTO miracle_portfolios2 (name, description, strategy_filter, initial_capital, position_size_pct, max_positions, fee_model, prefer_cdr, created_at)
                VALUES ('$pname','$pdesc','$sfilt',$cap,$psz,$mpos,'$fm',$pcdr,'$now')";
        if ($conn->query($sql)) {
            $port_count++;
        }
    }
}
$results['actions'][] = 'Seeded ' . $port_count . ' miracle portfolios';

// ─── Seed Watchlist (CDR tickers + Blue Chips + Sector ETFs + volatile mid-caps) ───
$watchlist = array(
    // CDR tickers (is_cdr=1)
    array('AAPL', 'Apple Inc', 'Technology', 'CDR available, mega-cap tech leader', 1),
    array('AMD',  'Advanced Micro Devices', 'Technology', 'CDR available, high-beta semiconductor', 1),
    array('AMZN', 'Amazon.com', 'Consumer Cyclical', 'CDR available, e-commerce/cloud', 1),
    array('CSCO', 'Cisco Systems', 'Technology', 'CDR available, networking', 1),
    array('CRM',  'Salesforce', 'Technology', 'CDR available, enterprise SaaS', 1),
    array('GOOG', 'Alphabet Inc', 'Technology', 'CDR available, search/AI leader', 1),
    array('IBM',  'IBM', 'Technology', 'CDR available, enterprise/AI', 1),
    array('INTC', 'Intel Corp', 'Technology', 'CDR available, semiconductor turnaround', 1),
    array('META', 'Meta Platforms', 'Technology', 'CDR available, social media/metaverse', 1),
    array('MSFT', 'Microsoft', 'Technology', 'CDR available, cloud/AI leader', 1),
    array('NFLX', 'Netflix', 'Communication Services', 'CDR available, streaming leader', 1),
    array('NVDA', 'NVIDIA', 'Technology', 'CDR available, AI GPU leader, high volatility', 1),
    array('COST', 'Costco', 'Consumer Defensive', 'CDR available, retail', 1),
    array('DIS',  'Walt Disney', 'Communication Services', 'CDR available, entertainment', 1),
    array('HD',   'Home Depot', 'Consumer Cyclical', 'CDR available, home improvement', 1),
    array('MCD',  'McDonalds', 'Consumer Cyclical', 'CDR available, fast food', 1),
    array('NKE',  'Nike', 'Consumer Cyclical', 'CDR available, sportswear', 1),
    array('SBUX', 'Starbucks', 'Consumer Cyclical', 'CDR available, coffee chain', 1),
    array('TSLA', 'Tesla', 'Consumer Cyclical', 'CDR available, EV leader, extreme volatility', 1),
    array('WMT',  'Walmart', 'Consumer Defensive', 'CDR available, retail giant', 1),
    array('ABBV', 'AbbVie', 'Healthcare', 'CDR available, pharma', 1),
    array('CVS',  'CVS Health', 'Healthcare', 'CDR available, pharmacy', 1),
    array('JNJ',  'Johnson & Johnson', 'Healthcare', 'CDR available, diversified health', 1),
    array('PFE',  'Pfizer', 'Healthcare', 'CDR available, pharma', 1),
    array('UNH',  'UnitedHealth', 'Healthcare', 'CDR available, health insurance', 1),
    array('BAC',  'Bank of America', 'Financial', 'CDR available, banking', 1),
    array('GS',   'Goldman Sachs', 'Financial', 'CDR available, investment banking', 1),
    array('JPM',  'JPMorgan Chase', 'Financial', 'CDR available, banking leader', 1),
    array('MA',   'Mastercard', 'Financial', 'CDR available, payments', 1),
    array('PYPL', 'PayPal', 'Financial', 'CDR available, digital payments', 1),
    array('V',    'Visa', 'Financial', 'CDR available, payments network', 1),
    array('BA',   'Boeing', 'Industrials', 'CDR available, aerospace', 1),
    array('CVX',  'Chevron', 'Energy', 'CDR available, oil major', 1),
    array('XOM',  'Exxon Mobil', 'Energy', 'CDR available, oil major', 1),
    array('HON',  'Honeywell', 'Industrials', 'CDR available, industrial conglomerate', 1),
    array('UPS',  'United Parcel Service', 'Industrials', 'CDR available, logistics', 1),
    array('KO',   'Coca-Cola', 'Consumer Defensive', 'CDR available, beverages', 1),
    array('VZ',   'Verizon', 'Communication Services', 'CDR available, telecom', 1),
    array('UBER', 'Uber Technologies', 'Technology', 'CDR available, ride-sharing/delivery', 1),
    // High-volatility non-CDR stocks (good for day trading)
    array('MARA', 'Marathon Digital', 'Technology', 'Crypto miner, extreme volatility', 0),
    array('RIOT', 'Riot Platforms', 'Technology', 'Crypto miner, extreme volatility', 0),
    array('SOFI', 'SoFi Technologies', 'Financial', 'Fintech, high retail interest', 0),
    array('PLTR', 'Palantir Technologies', 'Technology', 'AI/data analytics, high volatility', 0),
    array('SNAP', 'Snap Inc', 'Technology', 'Social media, volatile on earnings', 0),
    array('RIVN', 'Rivian Automotive', 'Consumer Cyclical', 'EV startup, high beta', 0),
    array('LCID', 'Lucid Group', 'Consumer Cyclical', 'EV startup, speculative', 0),
    array('COIN', 'Coinbase', 'Financial', 'Crypto exchange, follows BTC', 0),
    array('SQ',   'Block Inc', 'Technology', 'Fintech/payments, volatile', 0),
    array('SHOP', 'Shopify', 'Technology', 'E-commerce platform, growth stock', 0),
    array('ROKU', 'Roku Inc', 'Technology', 'Streaming platform, volatile', 0),
    array('DKNG', 'DraftKings', 'Consumer Cyclical', 'Sports betting, momentum plays', 0),
    array('ARM',  'ARM Holdings', 'Technology', 'Chip designer, high valuation swings', 0),
    array('SMCI', 'Super Micro Computer', 'Technology', 'AI server hardware, extreme moves', 0),
    array('MSTR', 'MicroStrategy', 'Technology', 'Bitcoin proxy, extreme volatility', 0),
    // Sector ETFs (for sector momentum)
    array('XLK',  'Technology Select Sector', 'ETF', 'Sector ETF - Technology', 0),
    array('XLF',  'Financial Select Sector', 'ETF', 'Sector ETF - Financials', 0),
    array('XLE',  'Energy Select Sector', 'ETF', 'Sector ETF - Energy', 0),
    array('XLV',  'Health Care Select Sector', 'ETF', 'Sector ETF - Healthcare', 0),
    array('XLI',  'Industrial Select Sector', 'ETF', 'Sector ETF - Industrials', 0),
    array('XLC',  'Communication Services Select', 'ETF', 'Sector ETF - Communication', 0),
    array('XLY',  'Consumer Discretionary Select', 'ETF', 'Sector ETF - Consumer Disc', 0),
    array('XLP',  'Consumer Staples Select', 'ETF', 'Sector ETF - Consumer Staples', 0),
    array('XLU',  'Utilities Select Sector', 'ETF', 'Sector ETF - Utilities', 0),
    array('XLRE', 'Real Estate Select Sector', 'ETF', 'Sector ETF - Real Estate', 0),
    array('XLB',  'Materials Select Sector', 'ETF', 'Sector ETF - Materials', 0),
    // Broad market ETFs
    array('SPY',  'SPDR S&P 500', 'ETF', 'S&P 500 benchmark', 0),
    array('QQQ',  'Invesco QQQ Trust', 'ETF', 'Nasdaq-100 benchmark', 0),
    array('IWM',  'iShares Russell 2000', 'ETF', 'Small-cap benchmark', 0)
);

$watch_count = 0;
foreach ($watchlist as $w) {
    $wticker = $conn->real_escape_string($w[0]);
    $wname   = $conn->real_escape_string($w[1]);
    $wsector = $conn->real_escape_string($w[2]);
    $wreason = $conn->real_escape_string($w[3]);
    $wcdr    = (int)$w[4];
    $wdate   = date('Y-m-d');
    $sql = "INSERT INTO miracle_watchlist2 (ticker, company_name, sector, reason, is_cdr, added_date, source, active)
            VALUES ('$wticker','$wname','$wsector','$wreason',$wcdr,'$wdate','seed',1)
            ON DUPLICATE KEY UPDATE company_name='$wname', sector='$wsector', reason='$wreason', is_cdr=$wcdr";
    if ($conn->query($sql)) {
        $watch_count++;
    }
}
$results['actions'][] = 'Seeded ' . $watch_count . ' watchlist tickers';

// Log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$ip = $conn->real_escape_string($ip);
$conn->query("INSERT INTO miracle_audit2 (action_type, details, ip_address, created_at) VALUES ('setup_schema2', 'DayTrades Miracle Claude schema created', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
