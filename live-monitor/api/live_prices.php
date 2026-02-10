<?php
/**
 * Live Price Monitor API — real-time crypto & forex prices.
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator).
 *
 * Actions:
 *   ?action=fetch   — Poll external APIs, update lm_price_cache (admin key required)
 *   ?action=get     — Return cached prices (public). Optional &asset_class=CRYPTO
 *   ?action=candles — Fetch hourly candles for a symbol. &symbol=BTCUSD&interval=1h&limit=24
 *   ?action=status  — API health / cache age info
 */
require_once dirname(__FILE__) . '/db_connect.php';

// ─── Constants ───────────────────────────────────────────────────────
$LP_ADMIN_KEY = 'livetrader2026';

$LP_CRYPTO_SYMBOLS = array(
    'BTCUSD', 'ETHUSD', 'SOLUSD', 'BNBUSD', 'XRPUSD', 'ADAUSD', 'DOTUSD',
    'MATICUSD', 'LINKUSD', 'AVAXUSD', 'DOGEUSD', 'SHIBUSD', 'UNIUSD', 'ATOMUSD',
    // Expanded volatile altcoins
    'EOSUSD', 'NEARUSD', 'FILUSD', 'TRXUSD', 'LTCUSD', 'BCHUSD',
    'APTUSD', 'ARBUSD', 'FTMUSD', 'AXSUSD', 'HBARUSD', 'AAVEUSD',
    'OPUSD', 'MKRUSD', 'INJUSD', 'SUIUSD', 'PEPEUSD', 'FLOKIUSD'
);

$LP_FOREX_SYMBOLS = array(
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'AUDUSD', 'NZDUSD', 'USDCHF',
    'EURGBP', 'EURJPY', 'GBPJPY'
);

$LP_STOCK_SYMBOLS = array(
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META',
    'JPM', 'WMT', 'XOM', 'NFLX', 'JNJ', 'BAC'
);

// ─── Auto-create table ──────────────────────────────────────────────
$conn->query("CREATE TABLE IF NOT EXISTS lm_price_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_class VARCHAR(10) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(18,8) NOT NULL DEFAULT 0,
    bid_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    ask_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    spread_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    volume_24h DECIMAL(24,2) NOT NULL DEFAULT 0,
    change_1h_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    change_24h_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    high_24h DECIMAL(18,8) NOT NULL DEFAULT 0,
    low_24h DECIMAL(18,8) NOT NULL DEFAULT 0,
    data_source VARCHAR(50) NOT NULL DEFAULT '',
    data_delay_seconds INT NOT NULL DEFAULT 0,
    last_updated DATETIME NOT NULL,
    UNIQUE KEY idx_asset_symbol (asset_class, symbol),
    KEY idx_updated (last_updated)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ─── Route action ────────────────────────────────────────────────────
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'get';

if ($action === 'fetch') {
    _lp_action_fetch($conn, $LP_ADMIN_KEY, $LP_CRYPTO_SYMBOLS, $LP_FOREX_SYMBOLS, $LP_STOCK_SYMBOLS);
} elseif ($action === 'get') {
    _lp_action_get($conn);
} elseif ($action === 'candles') {
    _lp_action_candles();
} elseif ($action === 'status') {
    _lp_action_status($conn);
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;


// =====================================================================
//  ACTION: fetch — Poll APIs, update lm_price_cache
// =====================================================================
function _lp_action_fetch($conn, $admin_key, $crypto_symbols, $forex_symbols, $stock_symbols) {
    // Require admin key
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key === '') {
        $key = isset($_POST['key']) ? trim($_POST['key']) : '';
    }
    if ($key !== $admin_key) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $result = array(
        'ok' => true,
        'crypto_fetched' => 0,
        'crypto_errors' => array(),
        'forex_fetched' => 0,
        'forex_errors' => array(),
        'stock_fetched' => 0,
        'stock_errors' => array(),
        'market_open' => _lp_is_market_hours(),
        'total_updated' => 0
    );

    // ── Fetch crypto: FreeCryptoAPI batch (primary), CoinGecko batch (fallback) ──
    $batch_data = array();

    // Try FreeCryptoAPI first (includes technical data: RSI, MACD, signal)
    if (isset($GLOBALS['FREECRYPTO_API_KEY']) && $GLOBALS['FREECRYPTO_API_KEY'] !== '') {
        $batch_data = _lp_fetch_all_crypto_freecryptoapi($crypto_symbols, $GLOBALS['FREECRYPTO_API_KEY']);
    }

    // Fallback to CoinGecko batch for any symbols FreeCryptoAPI missed
    $remaining_for_cg = array();
    foreach ($crypto_symbols as $symbol) {
        if (!isset($batch_data[$symbol])) {
            $remaining_for_cg[] = $symbol;
        }
    }
    if (count($remaining_for_cg) > 0) {
        $cg_batch = _lp_fetch_all_crypto_coingecko($remaining_for_cg);
        foreach ($cg_batch as $sym => $d) {
            $batch_data[$sym] = $d;
        }
    }

    foreach ($crypto_symbols as $symbol) {
        $data = isset($batch_data[$symbol]) ? $batch_data[$symbol] : null;
        if ($data !== null) {
            if (_lp_upsert_price($conn, 'CRYPTO', $symbol, $data)) {
                $result['crypto_fetched']++;
                $result['total_updated']++;
            } else {
                $result['crypto_errors'][] = $symbol . ': DB insert failed';
            }
        } else {
            $result['crypto_errors'][] = $symbol . ': all sources failed';
        }
    }

    // ── Fetch forex: TwelveData first 8, CurrencyLayer batch fallback, Yahoo last resort ──
    $td_count = 0;
    $forex_remaining = array();
    foreach ($forex_symbols as $symbol) {
        $data = null;

        // Try TwelveData for first 8
        if ($td_count < 8) {
            $data = _lp_fetch_forex_twelvedata($symbol);
            if ($data !== null) $td_count++;
        }

        if ($data !== null) {
            if (_lp_upsert_price($conn, 'FOREX', $symbol, $data)) {
                $result['forex_fetched']++;
                $result['total_updated']++;
            } else {
                $result['forex_errors'][] = $symbol . ': DB insert failed';
            }
        } else {
            $forex_remaining[] = $symbol;
        }
    }

    // CurrencyLayer batch for remaining forex (one call gets all pairs)
    if (count($forex_remaining) > 0 && isset($GLOBALS['CURRENCYLAYER_API_KEY']) && $GLOBALS['CURRENCYLAYER_API_KEY'] !== '') {
        $cl_data = _lp_fetch_forex_currencylayer($forex_remaining, $GLOBALS['CURRENCYLAYER_API_KEY']);
        $still_remaining = array();
        foreach ($forex_remaining as $symbol) {
            if (isset($cl_data[$symbol])) {
                if (_lp_upsert_price($conn, 'FOREX', $symbol, $cl_data[$symbol])) {
                    $result['forex_fetched']++;
                    $result['total_updated']++;
                } else {
                    $result['forex_errors'][] = $symbol . ': DB insert failed';
                }
            } else {
                $still_remaining[] = $symbol;
            }
        }
        $forex_remaining = $still_remaining;
    }

    // Yahoo Finance last resort for any still missing
    foreach ($forex_remaining as $symbol) {
        $data = _lp_fetch_forex_yahoo($symbol);
        if ($data === null) {
            $result['forex_errors'][] = $symbol . ': all sources failed';
            continue;
        }
        if (_lp_upsert_price($conn, 'FOREX', $symbol, $data)) {
            $result['forex_fetched']++;
            $result['total_updated']++;
        } else {
            $result['forex_errors'][] = $symbol . ': DB insert failed';
        }
    }

    // ── Fetch stocks: Finnhub (primary), Yahoo Finance (fallback) ──
    // Stocks only fetch during market hours OR if forced via &force_stocks=1
    $force_stocks = isset($_GET['force_stocks']) ? (int)$_GET['force_stocks'] : 0;
    $market_open = _lp_is_market_hours();
    if ($market_open || $force_stocks) {
        $finnhub_key = isset($GLOBALS['FINNHUB_API_KEY']) ? $GLOBALS['FINNHUB_API_KEY'] : '';
        foreach ($stock_symbols as $symbol) {
            $data = null;
            if ($finnhub_key !== '') {
                $data = _lp_fetch_stock_finnhub($symbol, $finnhub_key);
            }
            // Yahoo Finance fallback for stocks
            if ($data === null) {
                $data = _lp_fetch_stock_yahoo($symbol);
            }
            if ($data !== null) {
                if (_lp_upsert_price($conn, 'STOCK', $symbol, $data)) {
                    $result['stock_fetched']++;
                    $result['total_updated']++;
                } else {
                    $result['stock_errors'][] = $symbol . ': DB insert failed';
                }
            } else {
                $result['stock_errors'][] = $symbol . ': all sources failed';
            }
        }
    } else {
        $result['stock_errors'][] = 'Market closed — stocks not fetched (use force_stocks=1 to override)';
    }

    echo json_encode($result);
}


// =====================================================================
//  ACTION: get — Return cached prices
// =====================================================================
function _lp_action_get($conn) {
    $asset_class = isset($_GET['asset_class']) ? strtoupper(trim($_GET['asset_class'])) : '';

    $sql = "SELECT * FROM lm_price_cache";
    if ($asset_class !== '') {
        $sql .= " WHERE asset_class = '" . $conn->real_escape_string($asset_class) . "'";
    }
    $sql .= " ORDER BY asset_class ASC, symbol ASC";

    $res = $conn->query($sql);
    if (!$res) {
        header('HTTP/1.0 500 Internal Server Error');
        echo json_encode(array('ok' => false, 'error' => 'Query failed'));
        return;
    }

    $prices = array();
    $now = time();
    while ($row = $res->fetch_assoc()) {
        $updated_ts = strtotime($row['last_updated']);
        $cache_age = $now - $updated_ts;
        if ($cache_age < 0) $cache_age = 0;

        $prices[] = array(
            'asset_class'       => $row['asset_class'],
            'symbol'            => $row['symbol'],
            'price'             => (float)$row['price'],
            'bid_price'         => (float)$row['bid_price'],
            'ask_price'         => (float)$row['ask_price'],
            'spread_pct'        => (float)$row['spread_pct'],
            'volume_24h'        => (float)$row['volume_24h'],
            'change_1h_pct'     => (float)$row['change_1h_pct'],
            'change_24h_pct'    => (float)$row['change_24h_pct'],
            'high_24h'          => (float)$row['high_24h'],
            'low_24h'           => (float)$row['low_24h'],
            'data_source'       => $row['data_source'],
            'data_delay_seconds'=> (int)$row['data_delay_seconds'],
            'last_updated'      => $row['last_updated'],
            'cache_age_seconds' => $cache_age
        );
    }

    echo json_encode(array(
        'ok'    => true,
        'count' => count($prices),
        'prices'=> $prices
    ));
}


// =====================================================================
//  ACTION: candles — Fetch recent hourly klines for a symbol
// =====================================================================
function _lp_action_candles() {
    $symbol   = isset($_GET['symbol']) ? strtoupper(trim($_GET['symbol'])) : '';
    $interval = isset($_GET['interval']) ? trim($_GET['interval']) : '1h';
    $limit    = isset($_GET['limit']) ? (int)$_GET['limit'] : 24;

    if ($symbol === '') {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'symbol parameter required'));
        return;
    }

    // Validate interval
    $valid_intervals = array('1m', '5m', '15m', '30m', '1h', '4h', '1d');
    $interval_valid = false;
    foreach ($valid_intervals as $vi) {
        if ($vi === $interval) { $interval_valid = true; break; }
    }
    if (!$interval_valid) $interval = '1h';

    // Clamp limit
    if ($limit < 1) $limit = 1;
    if ($limit > 500) $limit = 500;

    // Check file cache (30-second TTL)
    $cache_file = sys_get_temp_dir() . '/lm_candles_' . md5($symbol . $interval . $limit) . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file) < 30)) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            echo $cached;
            return;
        }
    }

    // Determine asset class and fetch candles accordingly
    $candles = null;
    $asset_type = isset($_GET['asset_class']) ? strtoupper(trim($_GET['asset_class'])) : '';
    if ($asset_type === 'STOCK' || (!$asset_type && _lp_is_stock_symbol($symbol))) {
        // Stock candles via Finnhub
        $finnhub_key = isset($GLOBALS['FINNHUB_API_KEY']) ? $GLOBALS['FINNHUB_API_KEY'] : '';
        if ($finnhub_key !== '') {
            $candles = _lp_fetch_stock_candles_finnhub($symbol, $interval, $limit, $finnhub_key);
        }
    } else {
        $candles = _lp_fetch_crypto_klines($symbol, $interval, $limit);
    }

    if ($candles === null) {
        header('HTTP/1.0 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Failed to fetch candle data for ' . $symbol));
        return;
    }

    $response = json_encode(array(
        'ok'       => true,
        'symbol'   => $symbol,
        'interval' => $interval,
        'count'    => count($candles),
        'candles'  => $candles
    ));

    // Write to cache
    @file_put_contents($cache_file, $response);

    echo $response;
}


// =====================================================================
//  ACTION: status — API health & cache ages
// =====================================================================
function _lp_action_status($conn) {
    $total = 0;
    $oldest_age = 0;
    $newest_age = 0;
    $oldest_updated = '';
    $newest_updated = '';

    $res = $conn->query("SELECT COUNT(*) as cnt FROM lm_price_cache");
    if ($res && $row = $res->fetch_assoc()) {
        $total = (int)$row['cnt'];
    }

    $now = time();

    if ($total > 0) {
        // Oldest entry
        $res = $conn->query("SELECT last_updated FROM lm_price_cache ORDER BY last_updated ASC LIMIT 1");
        if ($res && $row = $res->fetch_assoc()) {
            $oldest_updated = $row['last_updated'];
            $oldest_age = $now - strtotime($row['last_updated']);
            if ($oldest_age < 0) $oldest_age = 0;
        }

        // Newest entry
        $res = $conn->query("SELECT last_updated FROM lm_price_cache ORDER BY last_updated DESC LIMIT 1");
        if ($res && $row = $res->fetch_assoc()) {
            $newest_updated = $row['last_updated'];
            $newest_age = $now - strtotime($row['last_updated']);
            if ($newest_age < 0) $newest_age = 0;
        }
    }

    // Count by asset class
    $by_class = array();
    $res = $conn->query("SELECT asset_class, COUNT(*) as cnt FROM lm_price_cache GROUP BY asset_class");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $by_class[$row['asset_class']] = (int)$row['cnt'];
        }
    }

    echo json_encode(array(
        'ok'                => true,
        'total_cached'      => $total,
        'by_asset_class'    => $by_class,
        'oldest_cache_age_seconds' => $oldest_age,
        'oldest_updated'    => $oldest_updated,
        'newest_cache_age_seconds' => $newest_age,
        'newest_updated'    => $newest_updated,
        'server_time'       => date('Y-m-d H:i:s'),
        'api_version'       => '1.0'
    ));
}


// =====================================================================
//  DB Helper: INSERT ... ON DUPLICATE KEY UPDATE
// =====================================================================
function _lp_upsert_price($conn, $asset_class, $symbol, $data) {
    $ac   = $conn->real_escape_string($asset_class);
    $sym  = $conn->real_escape_string($symbol);
    $now  = date('Y-m-d H:i:s');

    $price       = isset($data['price'])       ? (float)$data['price']       : 0;
    $bid         = isset($data['bid_price'])    ? (float)$data['bid_price']  : 0;
    $ask         = isset($data['ask_price'])    ? (float)$data['ask_price']  : 0;
    $spread      = isset($data['spread_pct'])   ? (float)$data['spread_pct'] : 0;
    $vol         = isset($data['volume_24h'])   ? (float)$data['volume_24h'] : 0;
    $chg_1h      = isset($data['change_1h_pct'])  ? (float)$data['change_1h_pct']  : 0;
    $chg_24h     = isset($data['change_24h_pct']) ? (float)$data['change_24h_pct'] : 0;
    $high        = isset($data['high_24h'])     ? (float)$data['high_24h']   : 0;
    $low         = isset($data['low_24h'])      ? (float)$data['low_24h']    : 0;
    $source      = isset($data['data_source'])  ? $conn->real_escape_string($data['data_source']) : '';
    $delay       = isset($data['data_delay_seconds']) ? (int)$data['data_delay_seconds'] : 0;

    $sql = "INSERT INTO lm_price_cache "
         . "(asset_class, symbol, price, bid_price, ask_price, spread_pct, "
         . "volume_24h, change_1h_pct, change_24h_pct, high_24h, low_24h, "
         . "data_source, data_delay_seconds, last_updated) "
         . "VALUES ('$ac', '$sym', $price, $bid, $ask, $spread, "
         . "$vol, $chg_1h, $chg_24h, $high, $low, "
         . "'$source', $delay, '$now') "
         . "ON DUPLICATE KEY UPDATE "
         . "price=$price, bid_price=$bid, ask_price=$ask, spread_pct=$spread, "
         . "volume_24h=$vol, change_1h_pct=$chg_1h, change_24h_pct=$chg_24h, "
         . "high_24h=$high, low_24h=$low, "
         . "data_source='$source', data_delay_seconds=$delay, last_updated='$now'";

    return $conn->query($sql) ? true : false;
}


// =====================================================================
//  Symbol Mapping Functions
// =====================================================================

/**
 * BTCUSD -> BTCUSDT (Binance uses USDT pairs)
 */
function _lp_symbol_to_binance($symbol) {
    // Special cases
    $map = array(
        'SHIBUSD' => 'SHIBUSDT',
        'MATICUSD' => 'MATICUSDT'
    );
    if (isset($map[$symbol])) return $map[$symbol];

    // Generic: if ends in USD, append T
    if (substr($symbol, -3) === 'USD') {
        return $symbol . 'T';
    }
    return $symbol;
}

/**
 * BTCUSD -> bitcoin (CoinGecko coin IDs)
 */
function _lp_symbol_to_coingecko($symbol) {
    $map = array(
        'BTCUSD'   => 'bitcoin',
        'ETHUSD'   => 'ethereum',
        'SOLUSD'   => 'solana',
        'BNBUSD'   => 'binancecoin',
        'XRPUSD'   => 'ripple',
        'ADAUSD'   => 'cardano',
        'DOTUSD'   => 'polkadot',
        'MATICUSD' => 'polygon-ecosystem-token',
        'LINKUSD'  => 'chainlink',
        'AVAXUSD'  => 'avalanche-2',
        'DOGEUSD'  => 'dogecoin',
        'SHIBUSD'  => 'shiba-inu',
        'UNIUSD'   => 'uniswap',
        'ATOMUSD'  => 'cosmos',
        // Expanded altcoins
        'EOSUSD'   => 'eos',
        'NEARUSD'  => 'near',
        'FILUSD'   => 'filecoin',
        'TRXUSD'   => 'tron',
        'LTCUSD'   => 'litecoin',
        'BCHUSD'   => 'bitcoin-cash',
        'APTUSD'   => 'aptos',
        'ARBUSD'   => 'arbitrum',
        'FTMUSD'   => 'fantom',
        'AXSUSD'   => 'axie-infinity',
        'HBARUSD'  => 'hedera-hashgraph',
        'AAVEUSD'  => 'aave',
        'OPUSD'    => 'optimism',
        'MKRUSD'   => 'maker',
        'INJUSD'   => 'injective-protocol',
        'SUIUSD'   => 'sui',
        'PEPEUSD'  => 'pepe',
        'FLOKIUSD' => 'floki'
    );
    return isset($map[$symbol]) ? $map[$symbol] : '';
}

/**
 * EURUSD -> EUR/USD (TwelveData format)
 */
function _lp_symbol_to_twelvedata($symbol) {
    // Insert / at position 3
    if (strlen($symbol) >= 6) {
        return substr($symbol, 0, 3) . '/' . substr($symbol, 3);
    }
    return $symbol;
}

/**
 * EURUSD -> OANDA:EUR_USD (Finnhub format)
 */
function _lp_symbol_to_finnhub($symbol) {
    if (strlen($symbol) >= 6) {
        return 'OANDA:' . substr($symbol, 0, 3) . '_' . substr($symbol, 3);
    }
    return $symbol;
}


// =====================================================================
//  HTTP helper — cURL primary, file_get_contents fallback
// =====================================================================
function _lp_http_get($url, $timeout) {
    if (!$timeout) $timeout = 10;

    // Try cURL first (more reliable on shared hosting)
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept: application/json'
        ));
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($body !== false && $code >= 200 && $code < 300) {
            $data = json_decode($body, true);
            return $data;
        }
    }

    // Fallback to file_get_contents
    $ctx = stream_context_create(array(
        'http' => array(
            'method'  => 'GET',
            'header'  => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\nAccept: application/json\r\n",
            'timeout' => $timeout
        ),
        'ssl' => array(
            'verify_peer' => false
        )
    ));
    $body = @file_get_contents($url, false, $ctx);
    if ($body === false) return null;
    $data = json_decode($body, true);
    return $data;
}


// =====================================================================
//  Data Source: Binance (crypto) — primary
// =====================================================================
function _lp_fetch_crypto_binance($symbol) {
    $binance_sym = _lp_symbol_to_binance($symbol);
    $url = 'https://api.binance.com/api/v3/ticker/24hr?symbol=' . urlencode($binance_sym);

    $data = _lp_http_get($url, 10);
    if ($data === null || !isset($data['lastPrice'])) return null;

    $last = (float)$data['lastPrice'];
    $bid  = isset($data['bidPrice'])  ? (float)$data['bidPrice']  : 0;
    $ask  = isset($data['askPrice'])  ? (float)$data['askPrice']  : 0;

    // Calculate spread percentage
    $spread_pct = 0;
    if ($last > 0 && $ask > 0 && $bid > 0) {
        $spread_pct = round((($ask - $bid) / $last) * 100, 4);
    }

    return array(
        'price'             => $last,
        'bid_price'         => $bid,
        'ask_price'         => $ask,
        'spread_pct'        => $spread_pct,
        'volume_24h'        => isset($data['quoteVolume']) ? (float)$data['quoteVolume'] : 0,
        'change_1h_pct'     => 0, // Binance 24hr ticker doesn't provide 1h change
        'change_24h_pct'    => isset($data['priceChangePercent']) ? (float)$data['priceChangePercent'] : 0,
        'high_24h'          => isset($data['highPrice']) ? (float)$data['highPrice'] : 0,
        'low_24h'           => isset($data['lowPrice'])  ? (float)$data['lowPrice']  : 0,
        'data_source'       => 'binance',
        'data_delay_seconds'=> 0
    );
}


// =====================================================================
//  Data Source: CoinGecko BATCH (crypto) — primary, one call for all
// =====================================================================
function _lp_fetch_all_crypto_coingecko($symbols) {
    $result = array();

    // Build comma-separated coin IDs
    $ids = array();
    $id_to_symbol = array();
    foreach ($symbols as $symbol) {
        $cid = _lp_symbol_to_coingecko($symbol);
        if ($cid !== '') {
            $ids[] = $cid;
            $id_to_symbol[$cid] = $symbol;
        }
    }
    if (count($ids) === 0) return $result;

    $url = 'https://api.coingecko.com/api/v3/simple/price'
         . '?ids=' . urlencode(implode(',', $ids))
         . '&vs_currencies=usd'
         . '&include_24hr_vol=true'
         . '&include_24hr_change=true'
         . '&include_last_updated_at=true';

    $data = _lp_http_get($url, 15);
    if ($data === null) return $result;

    foreach ($id_to_symbol as $cid => $symbol) {
        if (!isset($data[$cid])) continue;
        $coin = $data[$cid];
        $price = isset($coin['usd']) ? (float)$coin['usd'] : 0;
        if ($price <= 0) continue;

        $result[$symbol] = array(
            'price'             => $price,
            'bid_price'         => $price,
            'ask_price'         => $price,
            'spread_pct'        => 0,
            'volume_24h'        => isset($coin['usd_24h_vol']) ? (float)$coin['usd_24h_vol'] : 0,
            'change_1h_pct'     => 0,
            'change_24h_pct'    => isset($coin['usd_24h_change']) ? round((float)$coin['usd_24h_change'], 4) : 0,
            'high_24h'          => 0,
            'low_24h'           => 0,
            'data_source'       => 'coingecko',
            'data_delay_seconds'=> 60
        );
    }

    return $result;
}


// =====================================================================
//  Data Source: FreeCryptoAPI BATCH (crypto) — primary
//  Auth: Authorization: Bearer <key>
//  Separator: + (not comma)
//  Response: { "status":"success", "symbols":[{ "symbol":"BTC", "last":"70000", ... }] }
// =====================================================================
function _lp_fetch_all_crypto_freecryptoapi($symbols, $api_key) {
    $result = array();
    if ($api_key === '') return $result;

    // Map BTCUSD -> BTC etc.
    $api_syms = array();
    $sym_map = array(); // lowercase short -> full symbol
    foreach ($symbols as $symbol) {
        $short = str_replace('USD', '', $symbol);
        if ($short === 'MATIC') $short = 'POL';
        $api_syms[] = $short;
        $sym_map[strtoupper($short)] = $symbol;
    }

    // FreeCryptoAPI uses + separator, not comma
    $url = 'https://api.freecryptoapi.com/v1/getData'
         . '?symbol=' . implode('+', $api_syms);

    // Auth: Bearer token
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept: application/json',
            'Authorization: Bearer ' . $api_key
        ));
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
    } else {
        $ctx = stream_context_create(array(
            'http' => array(
                'method' => 'GET',
                'header' => "Accept: application/json\r\nAuthorization: Bearer " . $api_key . "\r\n",
                'timeout' => 15
            ),
            'ssl' => array('verify_peer' => false)
        ));
        $body = @file_get_contents($url, false, $ctx);
        $code = ($body !== false) ? 200 : 0;
    }

    if (!$body || $code < 200 || $code >= 300) return $result;
    $data = json_decode($body, true);
    if (!is_array($data)) return $result;
    if (!isset($data['status']) || $data['status'] !== 'success') return $result;
    if (!isset($data['symbols']) || !is_array($data['symbols'])) return $result;

    // Response: symbols is an array of objects with 'symbol', 'last', 'lowest', 'highest', etc.
    foreach ($data['symbols'] as $coin) {
        $short = isset($coin['symbol']) ? strtoupper($coin['symbol']) : '';
        if (!isset($sym_map[$short])) continue;
        $full_symbol = $sym_map[$short];

        $price = isset($coin['last']) ? (float)$coin['last'] : 0;
        if ($price <= 0) continue;

        $result[$full_symbol] = array(
            'price'             => $price,
            'bid_price'         => $price,
            'ask_price'         => $price,
            'spread_pct'        => 0,
            'volume_24h'        => 0,
            'change_1h_pct'     => 0,
            'change_24h_pct'    => isset($coin['daily_change_percentage']) ? round((float)$coin['daily_change_percentage'], 4) : 0,
            'high_24h'          => isset($coin['highest']) ? (float)$coin['highest'] : 0,
            'low_24h'           => isset($coin['lowest']) ? (float)$coin['lowest'] : 0,
            'data_source'       => 'freecryptoapi (' . (isset($coin['source_exchange']) ? $coin['source_exchange'] : 'unknown') . ')',
            'data_delay_seconds'=> 5
        );
    }

    return $result;
}


// =====================================================================
//  Data Source: CurrencyLayer BATCH (forex) — fallback
//  API: https://apilayer.net/api/live?access_key=KEY&currencies=EUR,GBP,...
//  Free tier: USD source only, 100 req/month
// =====================================================================
function _lp_fetch_forex_currencylayer($symbols, $api_key) {
    $result = array();
    if ($api_key === '') return $result;

    // Extract unique target currencies from symbol pairs
    // EURUSD -> need EUR, GBPUSD -> need GBP, USDJPY -> need JPY, etc.
    $currencies = array();
    foreach ($symbols as $symbol) {
        $base = substr($symbol, 0, 3);
        $quote = substr($symbol, 3, 3);
        if ($base !== 'USD') $currencies[$base] = 1;
        if ($quote !== 'USD') $currencies[$quote] = 1;
    }

    $url = 'https://apilayer.net/api/live'
         . '?access_key=' . urlencode($api_key)
         . '&currencies=' . urlencode(implode(',', array_keys($currencies)))
         . '&format=1';

    $data = _lp_http_get($url, 10);
    if ($data === null || !isset($data['success']) || !$data['success']) return $result;
    if (!isset($data['quotes']) || !is_array($data['quotes'])) return $result;

    $quotes = $data['quotes'];

    foreach ($symbols as $symbol) {
        $base = substr($symbol, 0, 3);
        $quote = substr($symbol, 3, 3);
        $price = 0;

        if ($base === 'USD') {
            // USDJPY, USDCAD, USDCHF — direct from USDJPY quote
            $key = 'USD' . $quote;
            if (isset($quotes[$key])) {
                $price = (float)$quotes[$key];
            }
        } elseif ($quote === 'USD') {
            // EURUSD, GBPUSD, AUDUSD, NZDUSD — invert USDEUR
            $key = 'USD' . $base;
            if (isset($quotes[$key]) && (float)$quotes[$key] > 0) {
                $price = round(1.0 / (float)$quotes[$key], 6);
            }
        } else {
            // Cross pairs like EURJPY, GBPJPY, EURGBP
            $key_base = 'USD' . $base;
            $key_quote = 'USD' . $quote;
            if (isset($quotes[$key_base]) && isset($quotes[$key_quote])
                && (float)$quotes[$key_base] > 0) {
                // EURJPY = USDJPY / USDEUR
                $price = round((float)$quotes[$key_quote] / (float)$quotes[$key_base], 6);
            }
        }

        if ($price <= 0) continue;

        $result[$symbol] = array(
            'price'             => $price,
            'bid_price'         => $price,
            'ask_price'         => $price,
            'spread_pct'        => 0,
            'volume_24h'        => 0,
            'change_1h_pct'     => 0,
            'change_24h_pct'    => 0, // CurrencyLayer live doesn't include change
            'high_24h'          => 0,
            'low_24h'           => 0,
            'data_source'       => 'currencylayer',
            'data_delay_seconds'=> 60
        );
    }

    return $result;
}


// =====================================================================
//  Data Source: CoinGecko (crypto) — fallback
// =====================================================================
function _lp_fetch_crypto_coingecko($symbol) {
    $coin_id = _lp_symbol_to_coingecko($symbol);
    if ($coin_id === '') return null;

    $url = 'https://api.coingecko.com/api/v3/simple/price'
         . '?ids=' . urlencode($coin_id)
         . '&vs_currencies=usd'
         . '&include_24hr_vol=true'
         . '&include_24hr_change=true'
         . '&include_last_updated_at=true';

    $data = _lp_http_get($url, 10);
    if ($data === null || !isset($data[$coin_id])) return null;

    $coin = $data[$coin_id];
    $price = isset($coin['usd']) ? (float)$coin['usd'] : 0;
    if ($price <= 0) return null;

    return array(
        'price'             => $price,
        'bid_price'         => $price, // CoinGecko doesn't provide bid/ask
        'ask_price'         => $price,
        'spread_pct'        => 0,
        'volume_24h'        => isset($coin['usd_24h_vol']) ? (float)$coin['usd_24h_vol'] : 0,
        'change_1h_pct'     => 0,
        'change_24h_pct'    => isset($coin['usd_24h_change']) ? round((float)$coin['usd_24h_change'], 4) : 0,
        'high_24h'          => 0, // Not available in simple/price endpoint
        'low_24h'           => 0,
        'data_source'       => 'coingecko',
        'data_delay_seconds'=> 60
    );
}


// =====================================================================
//  Data Source: Twelve Data (forex) — primary
// =====================================================================
function _lp_fetch_forex_twelvedata($symbol) {
    $td_sym = _lp_symbol_to_twelvedata($symbol);
    $api_key = '43e686519f7b4155a4a90eaae82fb63a';

    $url = 'https://api.twelvedata.com/quote'
         . '?symbol=' . urlencode($td_sym)
         . '&apikey=' . urlencode($api_key);

    $data = _lp_http_get($url, 10);
    if ($data === null) return null;
    if (isset($data['code']) && (int)$data['code'] !== 200 && isset($data['message'])) return null;
    if (!isset($data['close'])) return null;

    $close  = (float)$data['close'];
    $open   = isset($data['open'])  ? (float)$data['open']  : $close;
    $high   = isset($data['high'])  ? (float)$data['high']  : $close;
    $low    = isset($data['low'])   ? (float)$data['low']   : $close;
    $prev   = isset($data['previous_close']) ? (float)$data['previous_close'] : $close;

    // Calculate change_24h_pct from previous close
    $change_24h = 0;
    if ($prev > 0) {
        $change_24h = round((($close - $prev) / $prev) * 100, 4);
    }

    return array(
        'price'             => $close,
        'bid_price'         => $close, // TwelveData quote doesn't always include bid/ask
        'ask_price'         => $close,
        'spread_pct'        => 0,
        'volume_24h'        => isset($data['volume']) ? (float)$data['volume'] : 0,
        'change_1h_pct'     => 0,
        'change_24h_pct'    => $change_24h,
        'high_24h'          => $high,
        'low_24h'           => $low,
        'data_source'       => 'twelvedata',
        'data_delay_seconds'=> 15
    );
}


// =====================================================================
//  Data Source: Yahoo Finance (forex) — fallback
// =====================================================================
function _lp_fetch_forex_yahoo($symbol) {
    // Yahoo Finance forex: EURUSD -> EURUSD=X
    $yahoo_sym = strtoupper($symbol) . '=X';

    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/'
         . urlencode($yahoo_sym)
         . '?range=1d&interval=1h&includeAdjustedClose=true';

    $data = _lp_http_get($url, 10);
    if ($data === null) return null;
    if (!isset($data['chart']['result'][0])) return null;

    $r = $data['chart']['result'][0];
    $meta = isset($r['meta']) ? $r['meta'] : array();
    $price = isset($meta['regularMarketPrice']) ? (float)$meta['regularMarketPrice'] : 0;
    $prev  = isset($meta['chartPreviousClose']) ? (float)$meta['chartPreviousClose'] : 0;
    if ($price <= 0) return null;

    // Get high/low from today's candles
    $high = $price;
    $low  = $price;
    if (isset($r['indicators']['quote'][0])) {
        $q = $r['indicators']['quote'][0];
        if (isset($q['high']) && is_array($q['high'])) {
            foreach ($q['high'] as $h) {
                if ($h !== null && $h > $high) $high = (float)$h;
            }
        }
        if (isset($q['low']) && is_array($q['low'])) {
            foreach ($q['low'] as $l) {
                if ($l !== null && ($l < $low || $low == $price)) $low = (float)$l;
            }
        }
    }

    $change_24h = 0;
    if ($prev > 0) {
        $change_24h = round((($price - $prev) / $prev) * 100, 4);
    }

    return array(
        'price'             => $price,
        'bid_price'         => $price,
        'ask_price'         => $price,
        'spread_pct'        => 0,
        'volume_24h'        => 0,
        'change_1h_pct'     => 0,
        'change_24h_pct'    => $change_24h,
        'high_24h'          => $high,
        'low_24h'           => $low,
        'data_source'       => 'yahoo',
        'data_delay_seconds'=> 900
    );
}


// =====================================================================
//  Data Source: Binance klines (candles)
// =====================================================================
function _lp_fetch_crypto_klines($symbol, $interval, $limit) {
    $binance_sym = _lp_symbol_to_binance($symbol);

    $url = 'https://api.binance.com/api/v3/klines'
         . '?symbol=' . urlencode($binance_sym)
         . '&interval=' . urlencode($interval)
         . '&limit=' . (int)$limit;

    $data = _lp_http_get($url, 10);
    if ($data === null || !is_array($data) || count($data) === 0) return null;

    $candles = array();
    foreach ($data as $k) {
        // Binance kline format:
        // [0] open_time, [1] open, [2] high, [3] low, [4] close,
        // [5] volume, [6] close_time, [7] quote_asset_volume, ...
        if (!is_array($k) || count($k) < 6) continue;

        $candles[] = array(
            'date'   => date('Y-m-d H:i:s', (int)($k[0] / 1000)),
            'open'   => (float)$k[1],
            'high'   => (float)$k[2],
            'low'    => (float)$k[3],
            'close'  => (float)$k[4],
            'volume' => (float)$k[5]
        );
    }

    return count($candles) > 0 ? $candles : null;
}


// =====================================================================
//  Market Hours Detection (NYSE/NASDAQ: Mon-Fri 9:30-16:00 ET)
// =====================================================================
function _lp_is_market_hours() {
    $et = new DateTime('now', new DateTimeZone('America/New_York'));
    $dow = (int)$et->format('N'); // 1=Mon, 7=Sun
    if ($dow > 5) return false; // Weekend
    $hour = (int)$et->format('G');
    $min  = (int)$et->format('i');
    $time_mins = $hour * 60 + $min;
    // 9:30 AM = 570, 4:00 PM = 960
    return ($time_mins >= 570 && $time_mins < 960);
}

/**
 * Check if a symbol looks like a stock ticker (no USD suffix)
 */
function _lp_is_stock_symbol($symbol) {
    $stocks = array('AAPL','MSFT','GOOGL','AMZN','NVDA','META',
                    'JPM','WMT','XOM','NFLX','JNJ','BAC');
    foreach ($stocks as $s) {
        if ($s === $symbol) return true;
    }
    // Stocks don't end in USD like crypto/forex pairs
    return (strlen($symbol) <= 5 && substr($symbol, -3) !== 'USD');
}


// =====================================================================
//  Data Source: Finnhub (stocks) — primary
//  Endpoint: GET https://finnhub.io/api/v1/quote?symbol=AAPL&token=KEY
//  Response: { "c":150, "d":1.23, "dp":0.83, "h":151, "l":149, "o":149.5, "pc":148.77, "t":1638000000 }
// =====================================================================
function _lp_fetch_stock_finnhub($symbol, $api_key) {
    $url = 'https://finnhub.io/api/v1/quote'
         . '?symbol=' . urlencode($symbol)
         . '&token=' . urlencode($api_key);

    $data = _lp_http_get($url, 10);
    if ($data === null) return null;
    if (!isset($data['c']) || (float)$data['c'] <= 0) return null;

    $price = (float)$data['c'];
    $prev  = isset($data['pc']) ? (float)$data['pc'] : $price;
    $high  = isset($data['h'])  ? (float)$data['h']  : $price;
    $low   = isset($data['l'])  ? (float)$data['l']  : $price;
    $open  = isset($data['o'])  ? (float)$data['o']  : $price;

    $change_pct = isset($data['dp']) ? (float)$data['dp'] : 0;
    if ($change_pct == 0 && $prev > 0) {
        $change_pct = round((($price - $prev) / $prev) * 100, 4);
    }

    return array(
        'price'             => $price,
        'bid_price'         => $price,
        'ask_price'         => $price,
        'spread_pct'        => 0,
        'volume_24h'        => 0,
        'change_1h_pct'     => 0,
        'change_24h_pct'    => $change_pct,
        'high_24h'          => $high,
        'low_24h'           => $low,
        'data_source'       => 'finnhub',
        'data_delay_seconds'=> 0
    );
}


// =====================================================================
//  Data Source: Yahoo Finance (stocks) — fallback
// =====================================================================
function _lp_fetch_stock_yahoo($symbol) {
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/'
         . urlencode($symbol)
         . '?range=1d&interval=1h&includeAdjustedClose=true';

    $data = _lp_http_get($url, 10);
    if ($data === null) return null;
    if (!isset($data['chart']['result'][0])) return null;

    $r = $data['chart']['result'][0];
    $meta = isset($r['meta']) ? $r['meta'] : array();
    $price = isset($meta['regularMarketPrice']) ? (float)$meta['regularMarketPrice'] : 0;
    $prev  = isset($meta['chartPreviousClose']) ? (float)$meta['chartPreviousClose'] : 0;
    if ($price <= 0) return null;

    $high = $price;
    $low  = $price;
    if (isset($r['indicators']['quote'][0])) {
        $q = $r['indicators']['quote'][0];
        if (isset($q['high']) && is_array($q['high'])) {
            foreach ($q['high'] as $h) {
                if ($h !== null && $h > $high) $high = (float)$h;
            }
        }
        if (isset($q['low']) && is_array($q['low'])) {
            foreach ($q['low'] as $l) {
                if ($l !== null && ($l < $low || $low == $price)) $low = (float)$l;
            }
        }
    }

    $change_pct = 0;
    if ($prev > 0) {
        $change_pct = round((($price - $prev) / $prev) * 100, 4);
    }

    return array(
        'price'             => $price,
        'bid_price'         => $price,
        'ask_price'         => $price,
        'spread_pct'        => 0,
        'volume_24h'        => isset($meta['regularMarketVolume']) ? (float)$meta['regularMarketVolume'] : 0,
        'change_1h_pct'     => 0,
        'change_24h_pct'    => $change_pct,
        'high_24h'          => $high,
        'low_24h'           => $low,
        'data_source'       => 'yahoo',
        'data_delay_seconds'=> 900
    );
}


// =====================================================================
//  Data Source: Finnhub stock candles
//  Endpoint: GET https://finnhub.io/api/v1/stock/candle?symbol=AAPL&resolution=60&from=TS&to=TS&token=KEY
//  Response: { "c":[150,151], "h":[151,152], "l":[149,150], "o":[149.5,150.5], "v":[1000,2000], "t":[ts1,ts2], "s":"ok" }
// =====================================================================
function _lp_fetch_stock_candles_finnhub($symbol, $interval, $limit, $api_key) {
    // Map interval to Finnhub resolution
    $res_map = array(
        '1m' => '1', '5m' => '5', '15m' => '15', '30m' => '30',
        '1h' => '60', '4h' => 'D', '1d' => 'D'
    );
    $resolution = isset($res_map[$interval]) ? $res_map[$interval] : '60';

    // Calculate time range based on limit and resolution
    $to = time();
    $seconds_per_candle = 3600; // default 1h
    if ($resolution === '1') $seconds_per_candle = 60;
    elseif ($resolution === '5') $seconds_per_candle = 300;
    elseif ($resolution === '15') $seconds_per_candle = 900;
    elseif ($resolution === '30') $seconds_per_candle = 1800;
    elseif ($resolution === '60') $seconds_per_candle = 3600;
    elseif ($resolution === 'D') $seconds_per_candle = 86400;
    $from = $to - ($limit * $seconds_per_candle * 2); // extra buffer for weekends/holidays

    $url = 'https://finnhub.io/api/v1/stock/candle'
         . '?symbol=' . urlencode($symbol)
         . '&resolution=' . urlencode($resolution)
         . '&from=' . $from
         . '&to=' . $to
         . '&token=' . urlencode($api_key);

    $data = _lp_http_get($url, 10);
    if ($data === null || !isset($data['s']) || $data['s'] !== 'ok') return null;
    if (!isset($data['c']) || !is_array($data['c'])) return null;

    $candles = array();
    $count = count($data['c']);
    for ($i = 0; $i < $count; $i++) {
        $candles[] = array(
            'date'   => date('Y-m-d H:i:s', (int)$data['t'][$i]),
            'open'   => (float)$data['o'][$i],
            'high'   => (float)$data['h'][$i],
            'low'    => (float)$data['l'][$i],
            'close'  => (float)$data['c'][$i],
            'volume' => (float)$data['v'][$i]
        );
    }

    // Trim to requested limit (take latest N)
    if (count($candles) > $limit) {
        $candles = array_slice($candles, count($candles) - $limit);
    }

    return count($candles) > 0 ? $candles : null;
}
?>
