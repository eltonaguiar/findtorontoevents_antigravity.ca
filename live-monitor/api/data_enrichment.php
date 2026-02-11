<?php
/**
 * Data Enrichment API — Free Multi-Source Market Data Fetcher
 * Populates tables used by the Multi-Dimensional Analysis dashboard.
 * PHP 5.2 compatible — no closures, no short arrays, no ?:, no ??.
 *
 * FREE Data Sources:
 *   1. Finnhub (existing key)  — Stock quotes, analyst ratings, price targets
 *   2. Reddit  (no key needed) — WallStreetBets sentiment & mentions
 *   3. Yahoo Finance (no key)  — VIX / S&P 500 for market regime
 *
 * Tables populated:
 *   lm_price_cache       — Stock prices + 24h change
 *   lm_analyst_ratings   — Analyst consensus (strong_buy -> strong_sell)
 *   lm_price_targets     — Mean/median/high/low price targets
 *   market_regimes       — VIX level + regime classification
 *   lm_wsb_sentiment     — Reddit/WSB ticker mentions + sentiment
 *
 * Actions (admin — require key):
 *   ?action=fetch_all&key=...      — Fetch ALL sources sequentially
 *   ?action=fetch_prices&key=...   — Stock prices only (Finnhub)
 *   ?action=fetch_analyst&key=...  — Analyst ratings + price targets (Finnhub)
 *   ?action=fetch_wsb&key=...      — WallStreetBets sentiment (Reddit)
 *   ?action=fetch_market&key=...   — VIX + regime (Yahoo Finance)
 *
 * Actions (public):
 *   ?action=health                 — Data freshness / staleness report
 *   ?action=sources                — List data sources and status
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action    = isset($_GET['action']) ? $_GET['action'] : 'health';
$admin_key = isset($_GET['key']) ? $_GET['key'] : '';
$admin     = ($admin_key === 'livetrader2026');
$now       = date('Y-m-d H:i:s');
$today     = date('Y-m-d');

// Finnhub API key (from db_config or hardcoded fallback)
$FINNHUB_KEY_VAL = isset($FINNHUB_API_KEY) ? $FINNHUB_API_KEY : 'cvstlkhr01qhup0t0j7gcvstlkhr01qhup0t0j80';

// Ticker universe (same as multi_dimensional.php)
$ENRICH_TICKERS = array('AAPL','MSFT','GOOGL','AMZN','NVDA','META','JPM','WMT','XOM','NFLX','JNJ','BAC');

// ─────────────────────────────────────────
//  Ensure all table schemas (safe for pre-existing tables)
// ─────────────────────────────────────────
function _de_table_exists($tbl) {
    global $conn;
    $chk = $conn->query("SHOW TABLES LIKE '" . $conn->real_escape_string($tbl) . "'");
    return ($chk && $chk->num_rows > 0);
}

function _de_column_exists($tbl, $col) {
    global $conn;
    $r = $conn->query("SHOW COLUMNS FROM `" . $conn->real_escape_string($tbl) . "` LIKE '" . $conn->real_escape_string($col) . "'");
    return ($r && $r->num_rows > 0);
}

function _de_add_column($tbl, $col, $def) {
    global $conn;
    if (!_de_column_exists($tbl, $col)) {
        $conn->query("ALTER TABLE `$tbl` ADD COLUMN `$col` $def");
    }
}

// lm_price_cache — may already exist with fewer columns
if (!_de_table_exists('lm_price_cache')) {
    $conn->query("CREATE TABLE lm_price_cache (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(10) NOT NULL,
        price DECIMAL(12,2) NOT NULL DEFAULT 0,
        change_24h_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
        prev_close DECIMAL(12,2) NOT NULL DEFAULT 0,
        day_high DECIMAL(12,2) NOT NULL DEFAULT 0,
        day_low DECIMAL(12,2) NOT NULL DEFAULT 0,
        volume BIGINT NOT NULL DEFAULT 0,
        source VARCHAR(30) NOT NULL DEFAULT 'finnhub',
        updated_at DATETIME NOT NULL,
        UNIQUE KEY idx_symbol (symbol)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
} else {
    // Add missing columns to existing table
    _de_add_column('lm_price_cache', 'prev_close', 'DECIMAL(12,2) NOT NULL DEFAULT 0');
    _de_add_column('lm_price_cache', 'day_high', 'DECIMAL(12,2) NOT NULL DEFAULT 0');
    _de_add_column('lm_price_cache', 'day_low', 'DECIMAL(12,2) NOT NULL DEFAULT 0');
    _de_add_column('lm_price_cache', 'volume', 'BIGINT NOT NULL DEFAULT 0');
    _de_add_column('lm_price_cache', 'source', "VARCHAR(30) NOT NULL DEFAULT 'finnhub'");
    _de_add_column('lm_price_cache', 'updated_at', 'DATETIME');
    _de_add_column('lm_price_cache', 'price', 'DECIMAL(12,2) NOT NULL DEFAULT 0');
    _de_add_column('lm_price_cache', 'change_24h_pct', 'DECIMAL(8,4) NOT NULL DEFAULT 0');
}

// lm_analyst_ratings — may already exist
if (!_de_table_exists('lm_analyst_ratings')) {
    $conn->query("CREATE TABLE lm_analyst_ratings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        strong_buy INT NOT NULL DEFAULT 0,
        buy_count INT NOT NULL DEFAULT 0,
        hold_count INT NOT NULL DEFAULT 0,
        sell_count INT NOT NULL DEFAULT 0,
        strong_sell INT NOT NULL DEFAULT 0,
        period VARCHAR(20) NOT NULL DEFAULT '',
        source VARCHAR(30) NOT NULL DEFAULT 'finnhub',
        fetch_date DATE NOT NULL,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_ticker_date (ticker, fetch_date),
        KEY idx_ticker (ticker)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
} else {
    // The existing table may use 'buy','hold','sell' or 'buy_count','hold_count','sell_count'
    _de_add_column('lm_analyst_ratings', 'strong_buy', 'INT NOT NULL DEFAULT 0');
    _de_add_column('lm_analyst_ratings', 'strong_sell', 'INT NOT NULL DEFAULT 0');
    _de_add_column('lm_analyst_ratings', 'period', "VARCHAR(20) NOT NULL DEFAULT ''");
    _de_add_column('lm_analyst_ratings', 'source', "VARCHAR(30) NOT NULL DEFAULT 'finnhub'");
    _de_add_column('lm_analyst_ratings', 'fetch_date', 'DATE');
    _de_add_column('lm_analyst_ratings', 'created_at', 'DATETIME');
    // Also add buy/hold/sell if missing (some schemas use these names)
    _de_add_column('lm_analyst_ratings', 'buy', 'INT NOT NULL DEFAULT 0');
    _de_add_column('lm_analyst_ratings', 'hold', 'INT NOT NULL DEFAULT 0');
    _de_add_column('lm_analyst_ratings', 'sell', 'INT NOT NULL DEFAULT 0');
}

// lm_price_targets
if (!_de_table_exists('lm_price_targets')) {
    $conn->query("CREATE TABLE lm_price_targets (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        target_mean DECIMAL(10,2) NOT NULL DEFAULT 0,
        target_high DECIMAL(10,2) NOT NULL DEFAULT 0,
        target_low DECIMAL(10,2) NOT NULL DEFAULT 0,
        target_median DECIMAL(10,2) NOT NULL DEFAULT 0,
        num_analysts INT NOT NULL DEFAULT 0,
        source VARCHAR(30) NOT NULL DEFAULT 'finnhub',
        fetch_date DATE NOT NULL,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_ticker_date (ticker, fetch_date),
        KEY idx_ticker (ticker)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
} else {
    // Existing table from smart_money_schema may be missing columns
    _de_add_column('lm_price_targets', 'num_analysts', 'INT NOT NULL DEFAULT 0');
    _de_add_column('lm_price_targets', 'source', "VARCHAR(30) NOT NULL DEFAULT 'finnhub'");
    _de_add_column('lm_price_targets', 'target_median', 'DECIMAL(10,2) NOT NULL DEFAULT 0');
    _de_add_column('lm_price_targets', 'fetch_date', 'DATE');
    _de_add_column('lm_price_targets', 'created_at', 'DATETIME');
}

// market_regimes — may already exist
if (!_de_table_exists('market_regimes')) {
    $conn->query("CREATE TABLE market_regimes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        trade_date DATE NOT NULL,
        vix_close DECIMAL(8,2) NOT NULL DEFAULT 20,
        regime VARCHAR(30) NOT NULL DEFAULT 'moderate_bull',
        sp500_close DECIMAL(10,2) NOT NULL DEFAULT 0,
        sp500_change_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
        source VARCHAR(30) NOT NULL DEFAULT 'computed',
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_date (trade_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
} else {
    _de_add_column('market_regimes', 'sp500_close', 'DECIMAL(10,2) NOT NULL DEFAULT 0');
    _de_add_column('market_regimes', 'sp500_change_pct', 'DECIMAL(8,4) NOT NULL DEFAULT 0');
    _de_add_column('market_regimes', 'source', "VARCHAR(30) NOT NULL DEFAULT 'computed'");
    _de_add_column('market_regimes', 'created_at', 'DATETIME');
}

// lm_wsb_sentiment
if (!_de_table_exists('lm_wsb_sentiment')) {
    $conn->query("CREATE TABLE lm_wsb_sentiment (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        mentions_24h INT NOT NULL DEFAULT 0,
        sentiment DECIMAL(5,3) NOT NULL DEFAULT 0,
        wsb_score DECIMAL(5,2) NOT NULL DEFAULT 50,
        top_posts TEXT,
        fetch_date DATE NOT NULL,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_ticker_date (ticker, fetch_date),
        KEY idx_ticker (ticker)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
} else {
    _de_add_column('lm_wsb_sentiment', 'wsb_score', 'DECIMAL(5,2) NOT NULL DEFAULT 50');
    _de_add_column('lm_wsb_sentiment', 'top_posts', 'TEXT');
    _de_add_column('lm_wsb_sentiment', 'fetch_date', 'DATE');
    _de_add_column('lm_wsb_sentiment', 'created_at', 'DATETIME');
}

// lm_insider_sentiment — Finnhub MSPR (Monthly Share Purchase Ratio)
if (!_de_table_exists('lm_insider_sentiment')) {
    $conn->query("CREATE TABLE lm_insider_sentiment (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        year_month VARCHAR(7) NOT NULL,
        mspr DECIMAL(8,4) NOT NULL DEFAULT 0,
        change_val BIGINT NOT NULL DEFAULT 0,
        source VARCHAR(30) NOT NULL DEFAULT 'finnhub',
        fetch_date DATE NOT NULL,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_ticker_month (ticker, year_month),
        KEY idx_ticker (ticker)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
} else {
    _de_add_column('lm_insider_sentiment', 'change_val', 'BIGINT NOT NULL DEFAULT 0');
    _de_add_column('lm_insider_sentiment', 'source', "VARCHAR(30) NOT NULL DEFAULT 'finnhub'");
    _de_add_column('lm_insider_sentiment', 'fetch_date', 'DATE');
    _de_add_column('lm_insider_sentiment', 'created_at', 'DATETIME');
}

// ─────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────
function _de_esc($val) {
    global $conn;
    return $conn->real_escape_string($val);
}

function _de_http_get($url, $ua) {
    if ($ua === '') {
        $ua = 'DataEnrichment/1.0 contact@findtorontoevents.ca';
    }
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, $ua);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        $result = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($code >= 200 && $code < 300 && $result !== false) {
            return $result;
        }
        return null;
    }
    // Fallback to file_get_contents
    $ctx = stream_context_create(array('http' => array(
        'timeout' => 15,
        'header' => "User-Agent: " . $ua . "\r\n"
    )));
    $result = @file_get_contents($url, false, $ctx);
    return ($result !== false) ? $result : null;
}

function _de_cache_dir() {
    $dir = dirname(__FILE__) . '/cache';
    if (!is_dir($dir)) {
        @mkdir($dir, 0777, true);
    }
    return $dir;
}

function _de_cache_get($key, $ttl) {
    $file = _de_cache_dir() . '/de_' . md5($key) . '.json';
    if (!file_exists($file)) return null;
    if ((time() - filemtime($file)) > $ttl) return null;
    $data = @file_get_contents($file);
    return ($data !== false) ? json_decode($data, true) : null;
}

function _de_cache_set($key, $data) {
    $file = _de_cache_dir() . '/de_' . md5($key) . '.json';
    @file_put_contents($file, json_encode($data));
}

// ─────────────────────────────────────────
//  Source 1: Finnhub — Stock Quotes
// ─────────────────────────────────────────
function _de_fetch_finnhub_quote($ticker) {
    global $FINNHUB_KEY_VAL;
    $url = 'https://finnhub.io/api/v1/quote?symbol=' . urlencode($ticker)
         . '&token=' . $FINNHUB_KEY_VAL;
    $raw = _de_http_get($url, '');
    if ($raw === null) return null;
    $data = json_decode($raw, true);
    if (!is_array($data) || !isset($data['c'])) return null;
    return $data;
}

function _de_store_price($ticker, $quote) {
    global $conn, $now;
    $sym = _de_esc($ticker);
    $price = floatval($quote['c']);
    $change = floatval($quote['dp']);
    $prev = floatval($quote['pc']);
    $high = floatval($quote['h']);
    $low = floatval($quote['l']);
    $vol = 0;
    $nowEsc = _de_esc($now);

    // Upsert
    $conn->query("DELETE FROM lm_price_cache WHERE symbol = '$sym'");
    $sql = "INSERT INTO lm_price_cache (symbol, price, change_24h_pct, prev_close, day_high, day_low, volume, source, updated_at)
        VALUES ('$sym', $price, $change, $prev, $high, $low, $vol, 'finnhub', '$nowEsc')";
    $result = $conn->query($sql);
    if (!$result) {
        return array('ok' => false, 'error' => $conn->error, 'sql' => substr($sql, 0, 200));
    }
    return array('ok' => true);
}

function _de_fetch_all_prices() {
    global $ENRICH_TICKERS;
    $results = array();
    $ok = 0;
    $fail = 0;
    foreach ($ENRICH_TICKERS as $ticker) {
        $quote = _de_fetch_finnhub_quote($ticker);
        if ($quote !== null && floatval($quote['c']) > 0) {
            $store_result = _de_store_price($ticker, $quote);
            $entry = array('ticker' => $ticker, 'price' => floatval($quote['c']), 'change' => floatval($quote['dp']));
            if (is_array($store_result) && isset($store_result['ok']) && !$store_result['ok']) {
                $entry['db_error'] = $store_result['error'];
            }
            $results[] = $entry;
            $ok++;
        } else {
            $results[] = array('ticker' => $ticker, 'error' => 'fetch_failed');
            $fail++;
        }
        // Rate limit: 200ms between calls
        usleep(200000);
    }
    return array('ok_count' => $ok, 'fail_count' => $fail, 'results' => $results);
}

// ─────────────────────────────────────────
//  Source 2: Finnhub — Analyst Recommendations
// ─────────────────────────────────────────
function _de_fetch_finnhub_recommendation($ticker) {
    global $FINNHUB_KEY_VAL;
    $url = 'https://finnhub.io/api/v1/stock/recommendation?symbol=' . urlencode($ticker)
         . '&token=' . $FINNHUB_KEY_VAL;
    $raw = _de_http_get($url, '');
    if ($raw === null) return null;
    $data = json_decode($raw, true);
    if (!is_array($data) || count($data) === 0) return null;
    // Return the most recent period
    return $data[0];
}

function _de_store_analyst($ticker, $rec) {
    global $conn, $today, $now;
    $t = _de_esc($ticker);
    $sb = intval($rec['strongBuy']);
    $b = intval($rec['buy']);
    $h = intval($rec['hold']);
    $s = intval($rec['sell']);
    $ss = intval($rec['strongSell']);
    $period = _de_esc(isset($rec['period']) ? $rec['period'] : '');
    $nowEsc = _de_esc($now);

    // Detect column names: table may use 'buy'/'hold'/'sell' or 'buy_count'/'hold_count'/'sell_count'
    $buy_col = _de_column_exists('lm_analyst_ratings', 'buy') ? 'buy' : 'buy_count';
    $hold_col = _de_column_exists('lm_analyst_ratings', 'hold') ? 'hold' : 'hold_count';
    $sell_col = _de_column_exists('lm_analyst_ratings', 'sell') ? 'sell' : 'sell_count';

    $conn->query("DELETE FROM lm_analyst_ratings WHERE ticker = '$t'");
    $sql = "INSERT INTO lm_analyst_ratings (ticker, strong_buy, $buy_col, $hold_col, $sell_col, strong_sell, period, source, fetch_date, created_at)
        VALUES ('$t', $sb, $b, $h, $s, $ss, '$period', 'finnhub', '$today', '$nowEsc')";
    $result = $conn->query($sql);
    if (!$result) {
        return array('ok' => false, 'error' => $conn->error);
    }
    return array('ok' => true);
}

// ─────────────────────────────────────────
//  Source 3: Price Targets (Finnhub -> Yahoo Finance fallback)
// ─────────────────────────────────────────
function _de_fetch_finnhub_price_target($ticker) {
    global $FINNHUB_KEY_VAL;
    $url = 'https://finnhub.io/api/v1/stock/price-target?symbol=' . urlencode($ticker)
         . '&token=' . $FINNHUB_KEY_VAL;
    $raw = _de_http_get($url, '');
    if ($raw === null) return null;
    $data = json_decode($raw, true);
    if (!is_array($data)) return null;
    // Finnhub returns {"error":"..."} on free tier for this endpoint
    if (isset($data['error'])) return null;
    if (!isset($data['targetMean'])) return null;
    return $data;
}

// Price targets: Finnhub free tier doesn't support this.
// Yahoo Finance targets are handled by _de_fetch_all_yahoo_targets() (Source 7 below)
// via ?action=fetch_targets or as part of ?action=fetch_all.

function _de_store_price_target($ticker, $pt) {
    global $conn, $today, $now;
    $t = _de_esc($ticker);
    $mean = floatval($pt['targetMean']);
    $high = floatval($pt['targetHigh']);
    $low = floatval($pt['targetLow']);
    $median = floatval($pt['targetMedian']);
    $analysts = isset($pt['numAnalysts']) ? intval($pt['numAnalysts']) : 0;
    $src = _de_esc(isset($pt['source']) ? $pt['source'] : 'unknown');
    $nowEsc = _de_esc($now);

    $conn->query("DELETE FROM lm_price_targets WHERE ticker = '$t'");
    $sql = "INSERT INTO lm_price_targets (ticker, target_mean, target_high, target_low, target_median, num_analysts, source, fetch_date, created_at)
        VALUES ('$t', $mean, $high, $low, $median, $analysts, '$src', '$today', '$nowEsc')";
    $result = $conn->query($sql);
    if (!$result) {
        return array('ok' => false, 'error' => $conn->error);
    }
    return array('ok' => true);
}

function _de_fetch_all_analyst() {
    global $ENRICH_TICKERS;
    $ratings_ok = 0;
    $targets_ok = 0;
    $results = array();

    foreach ($ENRICH_TICKERS as $ticker) {
        $entry = array('ticker' => $ticker);

        // Analyst recommendations
        $rec = _de_fetch_finnhub_recommendation($ticker);
        if ($rec !== null) {
            _de_store_analyst($ticker, $rec);
            $entry['analyst'] = 'ok';
            $entry['strong_buy'] = intval($rec['strongBuy']);
            $entry['buy'] = intval($rec['buy']);
            $entry['hold'] = intval($rec['hold']);
            $entry['sell'] = intval($rec['sell']);
            $entry['strong_sell'] = intval($rec['strongSell']);
            $ratings_ok++;
        } else {
            $entry['analyst'] = 'failed';
        }
        usleep(200000);

        // Price targets handled separately by ?action=fetch_targets (Yahoo crumb auth)
        usleep(200000);

        $results[] = $entry;
    }

    return array('ratings_ok' => $ratings_ok, 'targets_ok' => $targets_ok, 'results' => $results);
}

// ─────────────────────────────────────────
//  Source 4: Yahoo Finance — VIX + Market Regime
// ─────────────────────────────────────────
function _de_fetch_vix_yahoo() {
    // Try Yahoo Finance v8 chart API for VIX (no auth required)
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=5d';
    $ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36';
    $raw = _de_http_get($url, $ua);
    if ($raw !== null) {
        $data = json_decode($raw, true);
        if (isset($data['chart']['result'][0]['meta']['regularMarketPrice'])) {
            return array(
                'vix' => floatval($data['chart']['result'][0]['meta']['regularMarketPrice']),
                'prev' => floatval($data['chart']['result'][0]['meta']['chartPreviousClose']),
                'source' => 'yahoo'
            );
        }
    }
    return null;
}

function _de_fetch_sp500_yahoo() {
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=5d';
    $ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36';
    $raw = _de_http_get($url, $ua);
    if ($raw !== null) {
        $data = json_decode($raw, true);
        if (isset($data['chart']['result'][0]['meta']['regularMarketPrice'])) {
            return array(
                'price' => floatval($data['chart']['result'][0]['meta']['regularMarketPrice']),
                'prev' => floatval($data['chart']['result'][0]['meta']['chartPreviousClose']),
                'source' => 'yahoo'
            );
        }
    }
    return null;
}

function _de_compute_regime_from_stocks() {
    // Fallback: compute pseudo-VIX from individual stock changes
    global $conn;
    $r = $conn->query("SELECT AVG(ABS(change_24h_pct)) as avg_abs_change,
        AVG(change_24h_pct) as avg_change,
        COUNT(*) as cnt
        FROM lm_price_cache WHERE updated_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)");
    if (!$r || !($row = $r->fetch_assoc()) || intval($row['cnt']) < 3) {
        return array('vix' => 20, 'regime' => 'moderate_bull', 'source' => 'default');
    }

    $avg_abs = floatval($row['avg_abs_change']);
    $avg_change = floatval($row['avg_change']);

    // Map avg absolute change to pseudo-VIX
    // avg |change| ~0.5% = VIX ~14, ~1% = VIX ~18, ~2% = VIX ~26, ~3%+ = VIX ~35+
    $pseudo_vix = round(12 + $avg_abs * 8, 2);
    if ($pseudo_vix > 50) $pseudo_vix = 50;

    // Determine regime
    $regime = 'moderate_bull';
    if ($pseudo_vix >= 35) {
        $regime = 'extreme_vol';
    } elseif ($pseudo_vix >= 25) {
        $regime = 'high_vol';
    } elseif ($avg_change < -1) {
        $regime = 'moderate_bear';
    } elseif ($avg_change < 0) {
        $regime = 'calm_bear';
    } elseif ($pseudo_vix <= 18) {
        $regime = 'calm_bull';
    }

    return array('vix' => $pseudo_vix, 'regime' => $regime, 'source' => 'computed_from_stocks');
}

function _de_fetch_market_regime() {
    global $conn, $today, $now;

    // Try Yahoo Finance for VIX
    $vix_data = _de_fetch_vix_yahoo();
    $sp500_data = _de_fetch_sp500_yahoo();

    $vix = 20;
    $regime = 'moderate_bull';
    $sp500 = 0;
    $sp500_change = 0;
    $source = 'yahoo';

    if ($vix_data !== null) {
        $vix = $vix_data['vix'];
        $prev_vix = $vix_data['prev'];

        // Determine regime from VIX
        if ($vix >= 35) {
            $regime = 'extreme_vol';
        } elseif ($vix >= 25) {
            $regime = 'high_vol';
        } elseif ($vix >= 20) {
            $regime = 'moderate_bear';
        } elseif ($vix >= 18) {
            $regime = 'calm_bear';
        } elseif ($vix >= 14) {
            $regime = 'moderate_bull';
        } else {
            $regime = 'calm_bull';
        }
    } else {
        // Fallback: compute from stock data
        $computed = _de_compute_regime_from_stocks();
        $vix = $computed['vix'];
        $regime = $computed['regime'];
        $source = $computed['source'];
    }

    if ($sp500_data !== null) {
        $sp500 = $sp500_data['price'];
        $sp_prev = $sp500_data['prev'];
        if ($sp_prev > 0) {
            $sp500_change = round(($sp500 - $sp_prev) / $sp_prev * 100, 4);
        }

        // Refine regime with S&P direction
        if ($sp500_change < -2 && $regime === 'moderate_bull') {
            $regime = 'moderate_bear';
        }
        if ($sp500_change > 1 && $regime === 'calm_bear') {
            $regime = 'moderate_bull';
        }
    }

    // Store in market_regimes
    $regimeEsc = _de_esc($regime);
    $srcEsc = _de_esc($source);
    $nowEsc = _de_esc($now);

    $conn->query("DELETE FROM market_regimes WHERE trade_date = '$today'");
    $conn->query("INSERT INTO market_regimes (trade_date, vix_close, regime, sp500_close, sp500_change_pct, source, created_at)
        VALUES ('$today', $vix, '$regimeEsc', $sp500, $sp500_change, '$srcEsc', '$nowEsc')");

    return array(
        'vix' => $vix,
        'regime' => $regime,
        'sp500' => $sp500,
        'sp500_change' => $sp500_change,
        'source' => $source
    );
}

// ─────────────────────────────────────────
//  Source 5: Reddit — WallStreetBets Sentiment
// ─────────────────────────────────────────

// Bullish keywords
function _de_wsb_bullish_words() {
    return array('buy','calls','moon','tendies','rocket','yolo','hold','squeeze',
        'undervalued','bullish','green','pump','diamond','long','puts on bears',
        'going up','to the moon','lambo','apes','strong','breakout','rip',
        'all in','call options','leaps','gamma squeeze','short squeeze','moass');
}

// Bearish keywords
function _de_wsb_bearish_words() {
    return array('puts','sell','crash','dump','overvalued','bearish','short',
        'red','bag','loss','bubble','drop','tank','plunge','drilling',
        'rugpull','rug pull','falling','dead cat','overbought','correction',
        'recession','collapse','worthless','going down','put options');
}

function _de_wsb_analyze_sentiment($text) {
    $text = strtolower($text);
    $bull_count = 0;
    $bear_count = 0;

    $bull_words = _de_wsb_bullish_words();
    $bear_words = _de_wsb_bearish_words();

    foreach ($bull_words as $w) {
        if (strpos($text, $w) !== false) {
            $bull_count++;
        }
    }
    foreach ($bear_words as $w) {
        if (strpos($text, $w) !== false) {
            $bear_count++;
        }
    }

    $total = $bull_count + $bear_count;
    if ($total === 0) return 0;
    return round(($bull_count - $bear_count) / ($total + 1), 3);
}

function _de_fetch_wsb_sentiment() {
    global $conn, $ENRICH_TICKERS, $today, $now;

    // Fetch hot posts from r/wallstreetbets
    $url = 'https://www.reddit.com/r/wallstreetbets/hot.json?limit=100&raw_json=1';
    $ua = 'DataEnrichment/1.0 (by /u/findtorontoevents)';
    $raw = _de_http_get($url, $ua);

    // Also fetch new posts for more coverage
    usleep(500000);
    $url2 = 'https://www.reddit.com/r/wallstreetbets/new.json?limit=100&raw_json=1';
    $raw2 = _de_http_get($url2, $ua);

    $posts = array();

    // Parse hot posts
    if ($raw !== null) {
        $data = json_decode($raw, true);
        if (isset($data['data']['children']) && is_array($data['data']['children'])) {
            foreach ($data['data']['children'] as $child) {
                if (isset($child['data']['title'])) {
                    $posts[] = array(
                        'title' => $child['data']['title'],
                        'score' => isset($child['data']['score']) ? intval($child['data']['score']) : 0,
                        'comments' => isset($child['data']['num_comments']) ? intval($child['data']['num_comments']) : 0,
                        'selftext' => isset($child['data']['selftext']) ? substr($child['data']['selftext'], 0, 500) : ''
                    );
                }
            }
        }
    }

    // Parse new posts
    if ($raw2 !== null) {
        $data2 = json_decode($raw2, true);
        if (isset($data2['data']['children']) && is_array($data2['data']['children'])) {
            foreach ($data2['data']['children'] as $child) {
                if (isset($child['data']['title'])) {
                    $posts[] = array(
                        'title' => $child['data']['title'],
                        'score' => isset($child['data']['score']) ? intval($child['data']['score']) : 0,
                        'comments' => isset($child['data']['num_comments']) ? intval($child['data']['num_comments']) : 0,
                        'selftext' => isset($child['data']['selftext']) ? substr($child['data']['selftext'], 0, 500) : ''
                    );
                }
            }
        }
    }

    if (count($posts) === 0) {
        return array('ok' => false, 'error' => 'no_posts_fetched', 'tickers_updated' => 0);
    }

    // Scan posts for ticker mentions
    $ticker_data = array();
    foreach ($ENRICH_TICKERS as $t) {
        $ticker_data[$t] = array('mentions' => 0, 'sentiment_sum' => 0, 'top_posts' => array());
    }

    foreach ($posts as $post) {
        $full_text = $post['title'] . ' ' . $post['selftext'];
        $full_upper = strtoupper($full_text);

        foreach ($ENRICH_TICKERS as $t) {
            // Check for ticker mention: $TICKER, or TICKER as standalone word
            $found = false;
            if (strpos($full_upper, '$' . $t) !== false) {
                $found = true;
            }
            // Check for standalone word (surrounded by non-alpha)
            if (!$found && preg_match('/\b' . $t . '\b/', $full_upper)) {
                $found = true;
            }

            if ($found) {
                $ticker_data[$t]['mentions']++;
                $sent = _de_wsb_analyze_sentiment($full_text);
                // Weight by post score (popularity)
                $weight = 1 + min(10, $post['score'] / 100);
                $ticker_data[$t]['sentiment_sum'] += $sent * $weight;
                if (count($ticker_data[$t]['top_posts']) < 3) {
                    $ticker_data[$t]['top_posts'][] = substr($post['title'], 0, 120);
                }
            }
        }
    }

    // Store results
    $updated = 0;
    foreach ($ENRICH_TICKERS as $t) {
        $mentions = $ticker_data[$t]['mentions'];
        $sentiment = 0;
        if ($mentions > 0) {
            $sentiment = round($ticker_data[$t]['sentiment_sum'] / $mentions, 3);
        }
        // WSB score: 50 (neutral) + sentiment * mention_boost
        // More mentions = stronger signal
        $mention_boost = min(30, $mentions * 3);
        $wsb_score = round(50 + $sentiment * $mention_boost, 2);
        $wsb_score = max(0, min(100, $wsb_score));

        $tEsc = _de_esc($t);
        $postsJson = _de_esc(json_encode($ticker_data[$t]['top_posts']));
        $nowEsc = _de_esc($now);

        $conn->query("DELETE FROM lm_wsb_sentiment WHERE ticker = '$tEsc'");
        $conn->query("INSERT INTO lm_wsb_sentiment (ticker, mentions_24h, sentiment, wsb_score, top_posts, fetch_date, created_at)
            VALUES ('$tEsc', $mentions, $sentiment, $wsb_score, '$postsJson', '$today', '$nowEsc')");
        $updated++;
    }

    return array(
        'ok' => true,
        'posts_scanned' => count($posts),
        'tickers_updated' => $updated,
        'summary' => $ticker_data
    );
}

// ─────────────────────────────────────────
//  Source 6: Stocktwits — Crowd Sentiment (no auth needed)
// ─────────────────────────────────────────
function _de_fetch_stocktwits_ticker($ticker) {
    $url = 'https://api.stocktwits.com/api/2/streams/symbol/' . urlencode($ticker) . '.json';
    $raw = _de_http_get($url, 'DataEnrichment/1.0');
    if ($raw === null) return null;
    $data = json_decode($raw, true);
    if (!is_array($data) || !isset($data['symbol'])) return null;

    $messages = isset($data['messages']) ? $data['messages'] : array();
    $bull = 0;
    $bear = 0;
    $total = count($messages);
    $top_posts = array();

    foreach ($messages as $msg) {
        if (isset($msg['entities']['sentiment']['basic'])) {
            $s = $msg['entities']['sentiment']['basic'];
            if ($s === 'Bullish') $bull++;
            elseif ($s === 'Bearish') $bear++;
        }
        if (count($top_posts) < 3 && isset($msg['body'])) {
            $top_posts[] = substr($msg['body'], 0, 120);
        }
    }

    // Compute sentiment: -1 to +1
    $sentiment = 0;
    if (($bull + $bear) > 0) {
        $sentiment = round(($bull - $bear) / ($bull + $bear), 3);
    }

    // Watchlist count as buzz proxy
    $watchers = isset($data['symbol']['watchlist_count']) ? intval($data['symbol']['watchlist_count']) : 0;

    return array(
        'mentions' => $total,
        'sentiment' => $sentiment,
        'bull' => $bull,
        'bear' => $bear,
        'watchers' => $watchers,
        'top_posts' => $top_posts
    );
}

function _de_fetch_stocktwits_all() {
    global $conn, $ENRICH_TICKERS, $today, $now;

    $updated = 0;
    $results = array();

    foreach ($ENRICH_TICKERS as $t) {
        $st = _de_fetch_stocktwits_ticker($t);
        if ($st === null) {
            $results[] = array('ticker' => $t, 'status' => 'failed');
            usleep(2000000); // 2 sec on failure
            continue;
        }

        $mentions = $st['mentions'];
        $sentiment = $st['sentiment'];
        // WSB score: 50 base + sentiment * boost
        $mention_boost = min(30, $mentions);
        $wsb_score = round(50 + $sentiment * $mention_boost, 2);
        $wsb_score = max(0, min(100, $wsb_score));

        $tEsc = _de_esc($t);
        $postsJson = _de_esc(json_encode($st['top_posts']));
        $nowEsc = _de_esc($now);

        $conn->query("DELETE FROM lm_wsb_sentiment WHERE ticker = '$tEsc'");
        $conn->query("INSERT INTO lm_wsb_sentiment (ticker, mentions_24h, sentiment, wsb_score, top_posts, fetch_date, created_at)
            VALUES ('$tEsc', $mentions, $sentiment, $wsb_score, '$postsJson', '$today', '$nowEsc')");
        $updated++;

        $results[] = array(
            'ticker' => $t,
            'mentions' => $mentions,
            'sentiment' => $sentiment,
            'bull' => $st['bull'],
            'bear' => $st['bear'],
            'watchers' => $st['watchers'],
            'wsb_score' => $wsb_score
        );

        usleep(1500000); // 1.5 sec between calls (Stocktwits rate limit ~200/hr)
    }

    return array('ok' => true, 'source' => 'stocktwits', 'tickers_updated' => $updated, 'results' => $results);
}

// ─────────────────────────────────────────
//  Source 7: Yahoo Finance — Price Targets (crumb auth)
// ─────────────────────────────────────────
function _de_yahoo_get_crumb() {
    // Get cookie from fc.yahoo.com
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, 'https://fc.yahoo.com');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_NOBODY, false);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0');
    $resp = curl_exec($ch);
    curl_close($ch);
    if ($resp === false) return null;

    // Extract Set-Cookie
    $cookie = '';
    if (preg_match('/Set-Cookie:\s*([^\r\n]+)/i', $resp, $m)) {
        $cookie = $m[1];
    }
    if ($cookie === '') return null;

    // Get crumb
    $ch2 = curl_init();
    curl_setopt($ch2, CURLOPT_URL, 'https://query2.finance.yahoo.com/v1/test/getcrumb');
    curl_setopt($ch2, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch2, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch2, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch2, CURLOPT_HTTPHEADER, array('Cookie: ' . $cookie));
    curl_setopt($ch2, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0');
    $crumb = curl_exec($ch2);
    curl_close($ch2);
    if ($crumb === false || strlen($crumb) > 50) return null;

    return array('crumb' => $crumb, 'cookie' => $cookie);
}

function _de_fetch_yahoo_targets($ticker, $auth) {
    $url = 'https://query2.finance.yahoo.com/v10/finance/quoteSummary/' . urlencode($ticker)
        . '?modules=financialData&crumb=' . urlencode($auth['crumb']);

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array('Cookie: ' . $auth['cookie']));
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0');
    $raw = curl_exec($ch);
    curl_close($ch);
    if ($raw === false) return null;

    $data = json_decode($raw, true);
    if (!isset($data['quoteSummary']['result'][0]['financialData'])) return null;

    $fd = $data['quoteSummary']['result'][0]['financialData'];
    $mean = isset($fd['targetMeanPrice']['raw']) ? floatval($fd['targetMeanPrice']['raw']) : 0;
    $high = isset($fd['targetHighPrice']['raw']) ? floatval($fd['targetHighPrice']['raw']) : 0;
    $low = isset($fd['targetLowPrice']['raw']) ? floatval($fd['targetLowPrice']['raw']) : 0;
    $median = isset($fd['targetMedianPrice']['raw']) ? floatval($fd['targetMedianPrice']['raw']) : 0;
    $analysts = isset($fd['numberOfAnalystOpinions']['raw']) ? intval($fd['numberOfAnalystOpinions']['raw']) : 0;

    if ($mean <= 0) return null;

    return array(
        'target_mean' => $mean,
        'target_high' => $high,
        'target_low' => $low,
        'target_median' => $median,
        'num_analysts' => $analysts
    );
}

function _de_fetch_all_yahoo_targets() {
    global $conn, $ENRICH_TICKERS, $today, $now;

    $auth = _de_yahoo_get_crumb();
    if ($auth === null) {
        return array('ok' => false, 'error' => 'yahoo_crumb_failed', 'targets_ok' => 0);
    }

    $targets_ok = 0;
    $results = array();

    foreach ($ENRICH_TICKERS as $ticker) {
        $pt = _de_fetch_yahoo_targets($ticker, $auth);
        if ($pt !== null) {
            $t = _de_esc($ticker);
            $nowEsc = _de_esc($now);

            $conn->query("DELETE FROM lm_price_targets WHERE ticker = '$t'");
            $ins = $conn->query("INSERT INTO lm_price_targets (ticker, target_mean, target_high, target_low, target_median, num_analysts, source, fetch_date, created_at)
                VALUES ('$t', " . $pt['target_mean'] . ", " . $pt['target_high'] . ", " . $pt['target_low'] . ", " . $pt['target_median'] . ", " . $pt['num_analysts'] . ", 'yahoo', '$today', '$nowEsc')");
            if ($ins) {
                $targets_ok++;
                $results[] = array('ticker' => $ticker, 'target_mean' => $pt['target_mean'], 'analysts' => $pt['num_analysts']);
            } else {
                $results[] = array('ticker' => $ticker, 'status' => 'insert_failed', 'error' => $conn->error);
            }
        } else {
            $results[] = array('ticker' => $ticker, 'status' => 'failed');
        }
        usleep(500000); // 0.5 sec between calls
    }

    return array('ok' => true, 'source' => 'yahoo', 'targets_ok' => $targets_ok, 'results' => $results);
}

// ─────────────────────────────────────────
//  Source 8: Wikipedia Pageviews — Retail Attention Signal
// ─────────────────────────────────────────
function _de_wiki_ticker_map() {
    return array(
        'AAPL'  => 'Apple_Inc.',
        'MSFT'  => 'Microsoft',
        'GOOGL' => 'Alphabet_Inc.',
        'AMZN'  => 'Amazon_(company)',
        'NVDA'  => 'Nvidia',
        'META'  => 'Meta_Platforms',
        'JPM'   => 'JPMorgan_Chase',
        'WMT'   => 'Walmart',
        'XOM'   => 'ExxonMobil',
        'NFLX'  => 'Netflix',
        'JNJ'   => 'Johnson_%26_Johnson',
        'BAC'   => 'Bank_of_America'
    );
}

function _de_fetch_wiki_pageviews($ticker, $article) {
    $end = date('Ymd');
    $start = date('Ymd', strtotime('-7 days'));
    $url = 'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/'
        . $article . '/daily/' . $start . '/' . $end;

    $raw = _de_http_get($url, 'DataEnrichment/1.0 (findtorontoevents.ca) contact@findtorontoevents.ca');
    if ($raw === null) return null;

    $data = json_decode($raw, true);
    if (!isset($data['items']) || !is_array($data['items'])) return null;

    $total_views = 0;
    $day_count = 0;
    foreach ($data['items'] as $item) {
        $total_views += intval($item['views']);
        $day_count++;
    }

    if ($day_count === 0) return null;

    $avg_daily = round($total_views / $day_count);
    return array(
        'total_views' => $total_views,
        'avg_daily' => $avg_daily,
        'days' => $day_count
    );
}

function _de_fetch_all_wiki_pageviews() {
    global $ENRICH_TICKERS;
    $map = _de_wiki_ticker_map();
    $results = array();

    foreach ($ENRICH_TICKERS as $ticker) {
        if (!isset($map[$ticker])) {
            $results[] = array('ticker' => $ticker, 'status' => 'no_mapping');
            continue;
        }
        $pv = _de_fetch_wiki_pageviews($ticker, $map[$ticker]);
        if ($pv !== null) {
            $results[] = array(
                'ticker' => $ticker,
                'avg_daily_views' => $pv['avg_daily'],
                'total_7d' => $pv['total_views']
            );
        } else {
            $results[] = array('ticker' => $ticker, 'status' => 'fetch_failed');
        }
        usleep(200000); // 200ms between calls
    }

    return array('ok' => true, 'source' => 'wikipedia', 'results' => $results);
}

// ─────────────────────────────────────────
//  Source 9: Finnhub — Insider Sentiment (MSPR)
// ─────────────────────────────────────────
function _de_fetch_finnhub_insider_sentiment($ticker) {
    global $FINNHUB_KEY_VAL;
    $from = date('Y-m-d', strtotime('-6 months'));
    $to = date('Y-m-d');
    $url = 'https://finnhub.io/api/v1/stock/insider-sentiment?symbol=' . urlencode($ticker)
         . '&from=' . $from . '&to=' . $to . '&token=' . $FINNHUB_KEY_VAL;
    $raw = _de_http_get($url, '');
    if ($raw === null) return null;
    $data = json_decode($raw, true);
    if (!is_array($data) || !isset($data['data']) || !is_array($data['data'])) return null;
    if (count($data['data']) === 0) return null;
    return $data['data'];
}

function _de_fetch_all_insider_sentiment() {
    global $conn, $ENRICH_TICKERS, $today, $now;
    $updated = 0;
    $results = array();

    foreach ($ENRICH_TICKERS as $ticker) {
        $records = _de_fetch_finnhub_insider_sentiment($ticker);
        if ($records !== null && count($records) > 0) {
            $tEsc = _de_esc($ticker);
            $nowEsc = _de_esc($now);

            // Store the most recent month
            $latest = $records[count($records) - 1];
            $mspr = floatval($latest['mspr']);
            $change = isset($latest['change']) ? intval($latest['change']) : 0;
            $ym = $latest['year'] . '-' . str_pad($latest['month'], 2, '0', STR_PAD_LEFT);

            $conn->query("DELETE FROM lm_insider_sentiment WHERE ticker = '$tEsc'");
            $conn->query("INSERT INTO lm_insider_sentiment (ticker, year_month, mspr, change_val, source, fetch_date, created_at)
                VALUES ('$tEsc', '$ym', $mspr, $change, 'finnhub', '$today', '$nowEsc')");

            // Compute average MSPR across all months for stability
            $avg_mspr = 0;
            $count = 0;
            foreach ($records as $rec) {
                $avg_mspr += floatval($rec['mspr']);
                $count++;
            }
            if ($count > 0) $avg_mspr = round($avg_mspr / $count, 4);

            $results[] = array(
                'ticker' => $ticker,
                'latest_mspr' => $mspr,
                'avg_mspr' => $avg_mspr,
                'months' => $count,
                'year_month' => $ym
            );
            $updated++;
        } else {
            $results[] = array('ticker' => $ticker, 'status' => 'failed');
        }
        usleep(200000); // 200ms between calls
    }

    return array('ok' => true, 'source' => 'finnhub_insider_sentiment', 'tickers_updated' => $updated, 'results' => $results);
}

// ─────────────────────────────────────────
//  Data Health Check
// ─────────────────────────────────────────
function _de_check_health() {
    global $conn;

    $health = array();

    // Price cache
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(updated_at) as latest FROM lm_price_cache");
    $row = ($r) ? $r->fetch_assoc() : null;
    $health['prices'] = array(
        'table' => 'lm_price_cache',
        'count' => ($row) ? intval($row['cnt']) : 0,
        'latest' => ($row && $row['latest']) ? $row['latest'] : 'never',
        'source' => 'Finnhub (free)',
        'status' => 'unknown'
    );

    // Analyst ratings
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(fetch_date) as latest FROM lm_analyst_ratings");
    $row = ($r) ? $r->fetch_assoc() : null;
    $health['analyst_ratings'] = array(
        'table' => 'lm_analyst_ratings',
        'count' => ($row) ? intval($row['cnt']) : 0,
        'latest' => ($row && $row['latest']) ? $row['latest'] : 'never',
        'source' => 'Finnhub (free)',
        'status' => 'unknown'
    );

    // Price targets
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(fetch_date) as latest FROM lm_price_targets");
    $row = ($r) ? $r->fetch_assoc() : null;
    $health['price_targets'] = array(
        'table' => 'lm_price_targets',
        'count' => ($row) ? intval($row['cnt']) : 0,
        'latest' => ($row && $row['latest']) ? $row['latest'] : 'never',
        'source' => 'Finnhub (free)',
        'status' => 'unknown'
    );

    // Market regimes
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(trade_date) as latest, MAX(vix_close) as vix FROM market_regimes");
    $row = ($r) ? $r->fetch_assoc() : null;
    $health['market_regimes'] = array(
        'table' => 'market_regimes',
        'count' => ($row) ? intval($row['cnt']) : 0,
        'latest' => ($row && $row['latest']) ? $row['latest'] : 'never',
        'source' => 'Yahoo Finance + computed',
        'vix' => ($row && $row['vix']) ? floatval($row['vix']) : 0,
        'status' => 'unknown'
    );

    // WSB sentiment
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(fetch_date) as latest, SUM(mentions_24h) as total_mentions FROM lm_wsb_sentiment");
    $row = ($r) ? $r->fetch_assoc() : null;
    $health['wsb_sentiment'] = array(
        'table' => 'lm_wsb_sentiment',
        'count' => ($row) ? intval($row['cnt']) : 0,
        'latest' => ($row && $row['latest']) ? $row['latest'] : 'never',
        'source' => 'Reddit r/wallstreetbets',
        'total_mentions' => ($row && $row['total_mentions']) ? intval($row['total_mentions']) : 0,
        'status' => 'unknown'
    );

    // Fear & Greed
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(fetch_date) as latest FROM lm_fear_greed");
    $row = ($r) ? $r->fetch_assoc() : null;
    $health['fear_greed'] = array(
        'table' => 'lm_fear_greed',
        'count' => ($row) ? intval($row['cnt']) : 0,
        'latest' => ($row && $row['latest']) ? $row['latest'] : 'never',
        'source' => 'alternative.me + VIX composite',
        'status' => 'unknown'
    );

    // SEC insider trades
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(transaction_date) as latest FROM gm_sec_insider_trades");
    $row = ($r) ? $r->fetch_assoc() : null;
    $health['insider_trades'] = array(
        'table' => 'gm_sec_insider_trades',
        'count' => ($row) ? intval($row['cnt']) : 0,
        'latest' => ($row && $row['latest']) ? $row['latest'] : 'never',
        'source' => 'SEC EDGAR Form 4',
        'status' => 'unknown'
    );

    // SEC 13F holdings
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(filing_quarter) as latest FROM gm_sec_13f_holdings");
    $row = ($r) ? $r->fetch_assoc() : null;
    $health['holdings_13f'] = array(
        'table' => 'gm_sec_13f_holdings',
        'count' => ($row) ? intval($row['cnt']) : 0,
        'latest' => ($row && $row['latest']) ? $row['latest'] : 'never',
        'source' => 'SEC EDGAR 13F',
        'status' => 'unknown'
    );

    // News sentiment
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(fetch_date) as latest FROM gm_news_sentiment");
    $row = ($r) ? $r->fetch_assoc() : null;
    $health['news_sentiment'] = array(
        'table' => 'gm_news_sentiment',
        'count' => ($row) ? intval($row['cnt']) : 0,
        'latest' => ($row && $row['latest']) ? $row['latest'] : 'never',
        'source' => 'Finnhub company news',
        'status' => 'unknown'
    );

    // Multi-dimensional scores
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(calc_date) as latest FROM lm_multi_dimensional");
    $row = ($r) ? $r->fetch_assoc() : null;
    $health['multi_dimensional'] = array(
        'table' => 'lm_multi_dimensional',
        'count' => ($row) ? intval($row['cnt']) : 0,
        'latest' => ($row && $row['latest']) ? $row['latest'] : 'never',
        'source' => 'Computed from all dimensions',
        'status' => 'unknown'
    );

    // Determine status for each (green/yellow/red)
    $today_str = date('Y-m-d');
    $yesterday = date('Y-m-d', strtotime('-1 day'));
    $week_ago = date('Y-m-d', strtotime('-7 days'));

    foreach ($health as $key => $item) {
        $latest = $item['latest'];
        if ($latest === 'never' || $item['count'] === 0) {
            $health[$key]['status'] = 'red';
        } elseif (substr($latest, 0, 10) >= $today_str || substr($latest, 0, 10) >= $yesterday) {
            $health[$key]['status'] = 'green';
        } elseif (substr($latest, 0, 10) >= $week_ago) {
            $health[$key]['status'] = 'yellow';
        } else {
            $health[$key]['status'] = 'red';
        }
    }

    return $health;
}

// ═══════════════════════════════════════════
//  Action: health (public)
// ═══════════════════════════════════════════
if ($action === 'health') {
    $health = _de_check_health();
    echo json_encode(array('ok' => true, 'action' => 'health', 'data' => $health, 'timestamp' => gmdate('Y-m-d H:i:s')));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: sources (public)
// ═══════════════════════════════════════════
if ($action === 'sources') {
    echo json_encode(array('ok' => true, 'action' => 'sources', 'sources' => array(
        array('name' => 'Finnhub', 'type' => 'API (free tier)', 'provides' => 'Stock quotes, analyst ratings, price targets, news sentiment', 'rate_limit' => '60 calls/min', 'auth' => 'API key (included)'),
        array('name' => 'Reddit', 'type' => 'JSON API (no auth)', 'provides' => 'WallStreetBets mentions, crowd sentiment', 'rate_limit' => '~60 calls/min', 'auth' => 'None'),
        array('name' => 'Yahoo Finance', 'type' => 'Unofficial API (no auth)', 'provides' => 'VIX index, S&P 500 for market regime', 'rate_limit' => 'Unknown', 'auth' => 'None'),
        array('name' => 'Alternative.me', 'type' => 'API (free)', 'provides' => 'Crypto Fear & Greed index', 'rate_limit' => 'Generous', 'auth' => 'None'),
        array('name' => 'SEC EDGAR', 'type' => 'Public API (free)', 'provides' => 'Form 4 insider trades, 13F institutional holdings', 'rate_limit' => '10 req/sec', 'auth' => 'None (User-Agent required)'),
        array('name' => 'Stocktwits', 'type' => 'API (free, no auth)', 'provides' => 'Crowd sentiment (bullish/bearish), watchlist buzz', 'rate_limit' => '200/hr', 'auth' => 'None'),
        array('name' => 'Yahoo quoteSummary', 'type' => 'Unofficial API (crumb auth)', 'provides' => 'Analyst price targets (mean/high/low/median)', 'rate_limit' => 'Generous', 'auth' => 'Crumb (auto-obtained)'),
        array('name' => 'Wikipedia', 'type' => 'REST API (free)', 'provides' => 'Article pageviews (retail attention proxy)', 'rate_limit' => 'Unlimited', 'auth' => 'User-Agent only')
    ), 'tickers' => array('AAPL','MSFT','GOOGL','AMZN','NVDA','META','JPM','WMT','XOM','NFLX','JNJ','BAC')));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: diag — database diagnostics (admin)
// ═══════════════════════════════════════════
if ($action === 'diag') {
    if (!$admin) {
        echo json_encode(array('ok' => false, 'error' => 'Admin key required'));
        $conn->close();
        exit;
    }
    $diag = array();

    // Check which tables exist
    $tables = array('lm_price_cache','lm_analyst_ratings','lm_price_targets','market_regimes','lm_wsb_sentiment','lm_fear_greed','gm_sec_insider_trades','gm_sec_13f_holdings','gm_news_sentiment','lm_multi_dimensional');
    foreach ($tables as $tbl) {
        $chk = $conn->query("SHOW TABLES LIKE '" . _de_esc($tbl) . "'");
        $exists = ($chk && $chk->num_rows > 0);
        $cnt = 0;
        if ($exists) {
            $r = $conn->query("SELECT COUNT(*) as c FROM " . $tbl);
            if ($r && $row = $r->fetch_assoc()) $cnt = intval($row['c']);
        }
        $diag[$tbl] = array('exists' => $exists, 'rows' => $cnt);
    }

    // Test INSERT into lm_price_cache
    $test_sql = "INSERT INTO lm_price_cache (symbol, price, change_24h_pct, prev_close, day_high, day_low, volume, source, updated_at) VALUES ('_TEST', 1.23, 0.5, 1.22, 1.25, 1.20, 0, 'diag', '" . _de_esc($now) . "')";
    $test_ok = $conn->query($test_sql);
    $test_error = $test_ok ? null : $conn->error;
    if ($test_ok) {
        $conn->query("DELETE FROM lm_price_cache WHERE symbol = '_TEST'");
    }
    $diag['_test_insert'] = array('ok' => ($test_ok ? true : false), 'error' => $test_error);

    echo json_encode(array('ok' => true, 'action' => 'diag', 'data' => $diag));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Admin actions below — require key
// ═══════════════════════════════════════════
if (!$admin) {
    echo json_encode(array('ok' => false, 'error' => 'Admin key required. Use ?action=health for public data.'));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: fetch_prices (admin)
// ═══════════════════════════════════════════
if ($action === 'fetch_prices') {
    $result = _de_fetch_all_prices();
    echo json_encode(array('ok' => true, 'action' => 'fetch_prices', 'data' => $result, 'timestamp' => gmdate('Y-m-d H:i:s')));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: fetch_analyst (admin)
// ═══════════════════════════════════════════
if ($action === 'fetch_analyst') {
    $result = _de_fetch_all_analyst();
    echo json_encode(array('ok' => true, 'action' => 'fetch_analyst', 'data' => $result, 'timestamp' => gmdate('Y-m-d H:i:s')));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: fetch_wsb (admin) — Reddit first, Stocktwits fallback
// ═══════════════════════════════════════════
if ($action === 'fetch_wsb') {
    // Try Reddit first
    $result = _de_fetch_wsb_sentiment();
    if (!$result['ok'] || $result['tickers_updated'] === 0) {
        // Fallback to Stocktwits
        $result = _de_fetch_stocktwits_all();
    }
    echo json_encode(array('ok' => true, 'action' => 'fetch_wsb', 'data' => $result, 'timestamp' => gmdate('Y-m-d H:i:s')));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: fetch_stocktwits (admin) — Stocktwits directly
// ═══════════════════════════════════════════
if ($action === 'fetch_stocktwits') {
    $result = _de_fetch_stocktwits_all();
    echo json_encode(array('ok' => true, 'action' => 'fetch_stocktwits', 'data' => $result, 'timestamp' => gmdate('Y-m-d H:i:s')));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: fetch_targets (admin) — Yahoo price targets
// ═══════════════════════════════════════════
if ($action === 'fetch_targets') {
    $result = _de_fetch_all_yahoo_targets();
    echo json_encode(array('ok' => true, 'action' => 'fetch_targets', 'data' => $result, 'timestamp' => gmdate('Y-m-d H:i:s')));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: fetch_wiki (admin) — Wikipedia pageviews
// ═══════════════════════════════════════════
if ($action === 'fetch_wiki') {
    $result = _de_fetch_all_wiki_pageviews();
    echo json_encode(array('ok' => true, 'action' => 'fetch_wiki', 'data' => $result, 'timestamp' => gmdate('Y-m-d H:i:s')));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: fetch_insider (admin) — Finnhub insider sentiment (MSPR)
// ═══════════════════════════════════════════
if ($action === 'fetch_insider') {
    $result = _de_fetch_all_insider_sentiment();
    echo json_encode(array('ok' => true, 'action' => 'fetch_insider', 'data' => $result, 'timestamp' => gmdate('Y-m-d H:i:s')));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: fetch_market (admin)
// ═══════════════════════════════════════════
if ($action === 'fetch_market') {
    $result = _de_fetch_market_regime();
    echo json_encode(array('ok' => true, 'action' => 'fetch_market', 'data' => $result, 'timestamp' => gmdate('Y-m-d H:i:s')));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: fetch_all (admin) — run everything
// ═══════════════════════════════════════════
if ($action === 'fetch_all') {
    $start = microtime(true);
    $output = array();

    // 1. Stock prices
    $output['prices'] = _de_fetch_all_prices();

    // 2. Market regime (VIX)
    $output['market'] = _de_fetch_market_regime();

    // 3. Analyst ratings + price targets
    $output['analyst'] = _de_fetch_all_analyst();

    // 4. WSB sentiment (Reddit first, Stocktwits fallback)
    $output['wsb'] = _de_fetch_wsb_sentiment();
    if (!$output['wsb']['ok'] || $output['wsb']['tickers_updated'] === 0) {
        $output['wsb'] = _de_fetch_stocktwits_all();
    }

    // 4a. Insider sentiment (Finnhub MSPR)
    $output['insider_sentiment'] = _de_fetch_all_insider_sentiment();

    // 4b. Yahoo price targets (Finnhub fallback failed, use Yahoo crumb auth)
    $output['yahoo_targets'] = _de_fetch_all_yahoo_targets();

    // 4c. Wikipedia pageviews (retail attention)
    $output['wiki_pageviews'] = _de_fetch_all_wiki_pageviews();

    // 5. Also trigger Fear & Greed fetch
    // Clear F&G cache so it recalculates with fresh data
    $cache_dir = dirname(__FILE__) . '/cache';
    foreach (array('crypto_fg', 'cnn_fg', 'composite_fg') as $k) {
        $f = $cache_dir . '/fg_' . md5($k) . '.json';
        if (file_exists($f)) @unlink($f);
    }

    // 6. Trigger multi-dimensional recalculation
    // Import the calculate function from multi_dimensional.php
    $md_url = 'http' . (isset($_SERVER['HTTPS']) ? 's' : '') . '://' . $_SERVER['HTTP_HOST']
        . '/live-monitor/api/multi_dimensional.php?action=calculate&key=livetrader2026';
    $md_result = _de_http_get($md_url, '');
    $output['multi_dimensional'] = ($md_result !== null) ? json_decode($md_result, true) : array('ok' => false, 'error' => 'self_call_failed');

    // Also trigger fear_greed fetch
    $fg_url = 'http' . (isset($_SERVER['HTTPS']) ? 's' : '') . '://' . $_SERVER['HTTP_HOST']
        . '/live-monitor/api/fear_greed.php?action=fetch&key=livetrader2026';
    $fg_result = _de_http_get($fg_url, '');
    $output['fear_greed'] = ($fg_result !== null) ? json_decode($fg_result, true) : array('ok' => false, 'error' => 'self_call_failed');

    $elapsed = round(microtime(true) - $start, 2);

    // Get final health
    $output['health'] = _de_check_health();

    echo json_encode(array(
        'ok' => true,
        'action' => 'fetch_all',
        'elapsed_seconds' => $elapsed,
        'data' => $output,
        'timestamp' => gmdate('Y-m-d H:i:s')
    ));
    $conn->close();
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
$conn->close();
?>
