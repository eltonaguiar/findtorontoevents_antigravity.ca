<?php
/**
 * Live Signal Generator — 23 Algorithms for Crypto, Forex & Stocks (19 Technical + 4 Fundamental/Contrarian)
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator)
 *
 * Actions:
 *   ?action=scan&key=livetrader2026   — Run all 23 algorithms, generate signals (admin only)
 *   ?action=list[&asset_class=CRYPTO] — Show active (non-expired) signals (public)
 *   ?action=expire                    — Mark expired signals
 *
 * Algorithms (Original 8):
 *   1. Momentum Burst       — 1h candle > 2% move
 *   2. RSI Reversal          — RSI(14) < 30 buy, > 70 short
 *   3. Breakout 24h          — Price above 24h high with volume confirm
 *   4. DCA Dip               — 24h change < -5%
 *   5. Bollinger Squeeze     — Bandwidth squeeze + breakout
 *   6. MACD Crossover        — MACD/Signal crossover
 *   7. Consensus             — 2+ daily algo picks on same symbol
 *   8. Volatility Breakout   — ATR spike + upward move
 *
 * Science-Backed Algorithms (5):
 *   9.  Trend Sniper         — 6-indicator confluence + regime gate (Brock et al. 1992)
 *   10. Dip Recovery          — Multi-candle reversal detector (Lo et al. 2000)
 *   11. Volume Spike          — Whale/institutional Z-Score detection (NBER 2024)
 *   12. VAM                   — Volatility-Adjusted Momentum / Martin Ratio (Moskowitz 2012)
 *   13. Mean Reversion Sniper — Bollinger + RSI + MACD convergence (academic consensus)
 *
 * Repo-Sourced Algorithms (6 — from eltonaguiar stock repos):
 *   14. ADX Trend Strength    — ADX(14) > 25 + DI directional (STOCKSUNIFY2 Alpha Predator)
 *   15. StochRSI Crossover    — StochRSI(14,14,3,3) K/D crossover at extremes
 *   16. Awesome Oscillator    — AO zero-line cross (STOCKSUNIFY2, Bill Williams)
 *   17. RSI(2) Scalp          — Ultra-short mean reversion (STOCKSUNIFY2)
 *   18. Ichimoku Cloud        — Tenkan/Kijun cross + cloud position
 *   19. Alpha Predator        — 4-factor alignment: ADX+RSI+AO+Volume (STOCKSUNIFY2)
 *
 * Fundamental/Contrarian (4):
 *   20. Insider Cluster Buy    — 3+ insiders buying same stock (Lakonishok & Lee 2001)
 *   21. 13F New Position       — Fund opens new position (SSRN 4767576)
 *   22. Sentiment Divergence   — News sentiment diverges from price action
 *   23. Contrarian Fear/Greed  — Reverses crowd at extremes (Buffett contrarian)
 */

require_once dirname(__FILE__) . '/db_connect.php';

// ────────────────────────────────────────────────────────────
//  Auto-create signals table
// ────────────────────────────────────────────────────────────

$conn->query("CREATE TABLE IF NOT EXISTS lm_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_class VARCHAR(10) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    signal_type VARCHAR(20) NOT NULL DEFAULT 'BUY',
    signal_strength INT NOT NULL DEFAULT 0,
    entry_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    target_tp_pct DECIMAL(6,2) NOT NULL DEFAULT 5,
    target_sl_pct DECIMAL(6,2) NOT NULL DEFAULT 3,
    max_hold_hours INT NOT NULL DEFAULT 24,
    timeframe VARCHAR(20) NOT NULL DEFAULT '1h',
    rationale TEXT,
    signal_time DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    KEY idx_asset (asset_class),
    KEY idx_symbol (symbol),
    KEY idx_status (status),
    KEY idx_time (signal_time)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ────────────────────────────────────────────────────────────
//  Symbol lists
// ────────────────────────────────────────────────────────────

$crypto_symbols = array(
    'BTCUSD', 'ETHUSD', 'SOLUSD', 'BNBUSD', 'XRPUSD',
    'ADAUSD', 'DOTUSD', 'LINKUSD', 'AVAXUSD', 'DOGEUSD',
    'MATICUSD', 'SHIBUSD', 'UNIUSD', 'ATOMUSD',
    // Expanded volatile altcoins
    'EOSUSD', 'NEARUSD', 'FILUSD', 'TRXUSD', 'LTCUSD', 'BCHUSD',
    'APTUSD', 'ARBUSD', 'FTMUSD', 'AXSUSD', 'HBARUSD', 'AAVEUSD',
    'OPUSD', 'MKRUSD', 'INJUSD', 'SUIUSD', 'PEPEUSD', 'FLOKIUSD'
);

$forex_symbols = array(
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD',
    'AUDUSD', 'NZDUSD', 'USDCHF', 'EURGBP'
);

$stock_symbols = array(
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META',
    'JPM', 'WMT', 'XOM', 'NFLX', 'JNJ', 'BAC'
);

// ────────────────────────────────────────────────────────────
//  PAUSED STOCK ALGORITHMS (Feb 11, 2026)
//  All 7 backtested stock algorithms are deeply unprofitable:
//  ETF Masters (3.37% WR), Sector Rotation (2.19%), Sector Momentum (0%),
//  Blue Chip Growth (5.56%), Technical Momentum (0%), Composite Rating (0%),
//  Cursor Genius (11.54%). Paused until fundamentally redesigned.
//  See ANALYSIS_FINANCES_FEB11_2026_CLAUDE.md for backtest data.
// ────────────────────────────────────────────────────────────
$PAUSED_STOCK_ALGOS = array(
    'ETF Masters',
    'Sector Rotation',
    'Sector Momentum',
    'Blue Chip Growth',
    'Technical Momentum',
    'Composite Rating',
    'Cursor Genius'
);

// ────────────────────────────────────────────────────────────
//  TEMPORARY SYMBOL EXCLUSIONS (Feb 11, 2026)
//  ETH/USD alpha composite is -4.390 (most bearish asset).
//  Recent stop-loss hits on ETH trades. Excluded from signal
//  generation until alpha score turns positive.
// ────────────────────────────────────────────────────────────
$EXCLUDED_SYMBOLS = array(
    'ETHUSD'
);

// ────────────────────────────────────────────────────────────
//  Symbol mapping helpers
// ────────────────────────────────────────────────────────────

function _ls_to_binance($s) {
    // BTCUSD -> BTCUSDT — generic: append T to USD-ending symbols
    // Special cases only needed if the ticker name differs
    $map = array(
        'MATICUSD' => 'MATICUSDT',
        'SHIBUSD'  => 'SHIBUSDT',
        'PEPEUSD'  => 'PEPEUSDT',
        'FLOKIUSD' => 'FLOKIUSDT',
        'HBARUSD'  => 'HBARUSDT'
    );
    if (isset($map[$s])) return $map[$s];
    // Generic: XXXUSD -> XXXUSDT
    if (substr($s, -3) === 'USD') return $s . 'T';
    return $s;
}

function _ls_to_twelvedata($s) {
    // EURUSD -> EUR/USD
    $map = array(
        'EURUSD' => 'EUR/USD', 'GBPUSD' => 'GBP/USD',
        'USDJPY' => 'USD/JPY', 'USDCAD' => 'USD/CAD',
        'AUDUSD' => 'AUD/USD', 'NZDUSD' => 'NZD/USD',
        'USDCHF' => 'USD/CHF', 'EURGBP' => 'EUR/GBP'
    );
    if (isset($map[$s])) return $map[$s];
    return substr($s, 0, 3) . '/' . substr($s, 3);
}

// ────────────────────────────────────────────────────────────
//  HTTP helper
// ────────────────────────────────────────────────────────────

function _ls_http_get($url) {
    // Try cURL first (more reliable on shared hosting)
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept: application/json'
        ));
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($body !== false && $code >= 200 && $code < 300) {
            return $body;
        }
    }

    // Fallback to file_get_contents
    $ctx = stream_context_create(array(
        'http' => array(
            'method'  => 'GET',
            'timeout' => 10,
            'header'  => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\nAccept: application/json\r\n"
        ),
        'ssl' => array(
            'verify_peer' => false
        )
    ));
    $body = @file_get_contents($url, false, $ctx);
    if ($body === false) return null;
    return $body;
}

// ────────────────────────────────────────────────────────────
//  Funding Rate fetcher — Bybit public API (Kimi: free, no auth)
// ────────────────────────────────────────────────────────────

/**
 * Fetch latest funding rate for a crypto symbol from Bybit.
 * Returns array('rate' => float, 'annualized' => float) or null on failure.
 * Positive rate = longs pay shorts (overleveraged longs).
 * Negative rate = shorts pay longs (potential short squeeze).
 */
function _ls_fetch_funding_rate($symbol) {
    // Map internal symbols to Bybit format: BTCUSD -> BTCUSDT
    $bybit_sym = str_replace('USD', 'USDT', strtoupper($symbol));
    // Handle double-T: BTCUSDTT -> BTCUSDT
    $bybit_sym = str_replace('USDTT', 'USDT', $bybit_sym);

    $url = 'https://api.bybit.com/v5/market/funding/history?category=linear&symbol=' . $bybit_sym . '&limit=1';
    $body = _ls_http_get($url);
    if ($body === null) return null;

    $data = json_decode($body, true);
    if (!isset($data['result']['list'][0])) return null;

    $entry = $data['result']['list'][0];
    $rate = isset($entry['fundingRate']) ? (float)$entry['fundingRate'] : 0;

    return array(
        'rate' => $rate,
        'annualized' => round($rate * 3 * 365 * 100, 2), // 3 funding periods/day * 365 days
        'symbol' => $bybit_sym
    );
}

/**
 * Apply funding rate signal boost/penalty to a crypto signal.
 * - Very negative funding (< -0.01%): boost BUY strength +10 (short squeeze setup)
 * - Moderately negative (< -0.005%): boost BUY +5
 * - Very positive funding (> 0.03%): boost SHORT/penalize BUY +10/-5
 * Returns modified signal with funding_rate info in rationale.
 */
function _ls_apply_funding_rate($sig, $funding) {
    if ($funding === null || $sig === null) return $sig;

    $rate = $funding['rate'];
    $rationale = json_decode($sig['rationale'], true);
    if (!is_array($rationale)) $rationale = array();
    $rationale['funding_rate'] = $rate;
    $rationale['funding_annualized'] = $funding['annualized'];

    $boost = 0;
    if ($rate < -0.0001 && ($sig['signal_type'] === 'BUY' || $sig['signal_type'] === 'STRONG_BUY')) {
        // Negative funding + BUY signal = short squeeze potential
        $boost = ($rate < -0.001) ? 10 : 5;
        $rationale['funding_boost'] = $boost;
    } elseif ($rate > 0.0003 && ($sig['signal_type'] === 'BUY' || $sig['signal_type'] === 'STRONG_BUY')) {
        // High positive funding + BUY = overleveraged longs, penalize
        $boost = -5;
        $rationale['funding_penalty'] = 5;
    } elseif ($rate > 0.0003 && ($sig['signal_type'] === 'SHORT' || $sig['signal_type'] === 'STRONG_SHORT')) {
        // High positive funding + SHORT = good confirmation
        $boost = 5;
        $rationale['funding_boost'] = $boost;
    }

    $sig['signal_strength'] = max(0, min(100, $sig['signal_strength'] + $boost));
    $sig['rationale'] = json_encode($rationale);

    return $sig;
}

// ────────────────────────────────────────────────────────────
//  Candle fetching — Crypto (CoinGecko OHLC primary, Binance fallback)
// ────────────────────────────────────────────────────────────

function _ls_fetch_binance_klines($symbol, $limit) {
    $limit = (int)$limit;
    if ($limit < 1) $limit = 24;

    // Try Kraken OHLC first (Ontario-valid exchange, includes volume, no auth)
    $candles = _ls_fetch_kraken_ohlc($symbol, $limit);
    if (count($candles) >= 2) return $candles;

    // Try CoinGecko OHLC second (works on shared hosting, but no volume)
    $candles = _ls_fetch_coingecko_ohlc($symbol, $limit);
    if (count($candles) >= 2) return $candles;

    // Fallback: Binance klines (may be blocked on shared hosting)
    $bin = _ls_to_binance($symbol);
    $cache_file = sys_get_temp_dir() . '/lm_klines_' . md5($bin . '_' . $limit) . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 30) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $arr = json_decode($cached, true);
            if (is_array($arr) && count($arr) > 0) return $arr;
        }
    }

    $url = 'https://api.binance.com/api/v3/klines?symbol=' . urlencode($bin)
         . '&interval=1h&limit=' . $limit;
    $body = _ls_http_get($url);
    if ($body === null) return array();

    $raw = json_decode($body, true);
    if (!is_array($raw)) return array();

    $candles = array();
    foreach ($raw as $k) {
        $candles[] = array(
            'time'   => (float)$k[0] / 1000,
            'open'   => (float)$k[1],
            'high'   => (float)$k[2],
            'low'    => (float)$k[3],
            'close'  => (float)$k[4],
            'volume' => (float)$k[5]
        );
    }

    @file_put_contents($cache_file, json_encode($candles));
    return $candles;
}

// Kraken OHLC — hourly candles WITH volume (free, no auth, Ontario-valid exchange)
// Endpoint: GET https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60
// Returns: [time, open, high, low, close, vwap, volume, count]
function _ls_fetch_kraken_ohlc($symbol, $limit) {
    $kr_pair = _ls_symbol_to_kraken($symbol);
    if ($kr_pair === '') return array();

    $cache_file = sys_get_temp_dir() . '/lm_kr_ohlc_ls_' . md5($kr_pair . '_' . $limit) . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 60) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $arr = json_decode($cached, true);
            if (is_array($arr) && count($arr) > 0) return $arr;
        }
    }

    // interval=60 gives hourly candles, up to 720 entries
    $url = 'https://api.kraken.com/0/public/OHLC?pair=' . urlencode($kr_pair) . '&interval=60';
    $body = _ls_http_get($url);
    if ($body === null) return array();

    $data = json_decode($body, true);
    if (!is_array($data) || !isset($data['result'])) return array();

    // Find OHLC data (first key that's not 'last')
    $ohlc_raw = null;
    foreach ($data['result'] as $key => $val) {
        if ($key === 'last') continue;
        $ohlc_raw = $val;
        break;
    }
    if (!is_array($ohlc_raw) || count($ohlc_raw) === 0) return array();

    $candles = array();
    foreach ($ohlc_raw as $k) {
        // [time, open, high, low, close, vwap, volume, count]
        if (!is_array($k) || count($k) < 7) continue;
        $candles[] = array(
            'time'   => (float)$k[0],
            'open'   => (float)$k[1],
            'high'   => (float)$k[2],
            'low'    => (float)$k[3],
            'close'  => (float)$k[4],
            'volume' => (float)$k[6]
        );
    }

    if (count($candles) > $limit) {
        $candles = array_slice($candles, count($candles) - $limit);
    }

    @file_put_contents($cache_file, json_encode($candles));
    return $candles;
}

// Kraken symbol mapping: BTCUSD -> XBTUSD, DOGEUSD -> XDGUSD, etc.
function _ls_symbol_to_kraken($symbol) {
    $map = array(
        'BTCUSD'   => 'XBTUSD',
        'DOGEUSD'  => 'XDGUSD',
        'BNBUSD'   => ''         // BNB not on Kraken
    );
    if (isset($map[$symbol])) return $map[$symbol];
    return $symbol;
}

// CoinGecko OHLC — hourly candles (free, no auth, works from shared hosting)
function _ls_fetch_coingecko_ohlc($symbol, $limit) {
    $cg_id = _ls_symbol_to_coingecko($symbol);
    if ($cg_id === '') return array();

    $cache_file = sys_get_temp_dir() . '/lm_cg_ohlc_ls_' . md5($cg_id . '_' . $limit) . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 60) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $arr = json_decode($cached, true);
            if (is_array($arr) && count($arr) > 0) return $arr;
        }
    }

    // days=2 gives ~48 hourly candles
    $url = 'https://api.coingecko.com/api/v3/coins/' . urlencode($cg_id)
         . '/ohlc?vs_currency=usd&days=2';
    $body = _ls_http_get($url);
    if ($body === null) return array();

    $raw = json_decode($body, true);
    if (!is_array($raw)) return array();

    $candles = array();
    foreach ($raw as $k) {
        if (!is_array($k) || count($k) < 5) continue;
        $candles[] = array(
            'time'   => (float)$k[0] / 1000,
            'open'   => (float)$k[1],
            'high'   => (float)$k[2],
            'low'    => (float)$k[3],
            'close'  => (float)$k[4],
            'volume' => 0
        );
    }

    if (count($candles) > $limit) {
        $candles = array_slice($candles, count($candles) - $limit);
    }

    @file_put_contents($cache_file, json_encode($candles));
    return $candles;
}

// CoinGecko ID map for signal scanner
function _ls_symbol_to_coingecko($symbol) {
    $map = array(
        'BTCUSD'   => 'bitcoin',       'ETHUSD'   => 'ethereum',
        'SOLUSD'   => 'solana',         'BNBUSD'   => 'binancecoin',
        'XRPUSD'   => 'ripple',         'ADAUSD'   => 'cardano',
        'DOTUSD'   => 'polkadot',       'MATICUSD' => 'polygon-ecosystem-token',
        'LINKUSD'  => 'chainlink',      'AVAXUSD'  => 'avalanche-2',
        'DOGEUSD'  => 'dogecoin',       'SHIBUSD'  => 'shiba-inu',
        'UNIUSD'   => 'uniswap',        'ATOMUSD'  => 'cosmos',
        'EOSUSD'   => 'eos',            'NEARUSD'  => 'near',
        'FILUSD'   => 'filecoin',        'TRXUSD'   => 'tron',
        'LTCUSD'   => 'litecoin',        'BCHUSD'   => 'bitcoin-cash',
        'APTUSD'   => 'aptos',           'ARBUSD'   => 'arbitrum',
        'FTMUSD'   => 'fantom',          'AXSUSD'   => 'axie-infinity',
        'HBARUSD'  => 'hedera-hashgraph','AAVEUSD'  => 'aave',
        'OPUSD'    => 'optimism',        'MKRUSD'   => 'maker',
        'INJUSD'   => 'injective-protocol', 'SUIUSD' => 'sui',
        'PEPEUSD'  => 'pepe',            'FLOKIUSD' => 'floki'
    );
    return isset($map[$symbol]) ? $map[$symbol] : '';
}

// ────────────────────────────────────────────────────────────
//  Candle fetching — Twelve Data (forex)
// ────────────────────────────────────────────────────────────

function _ls_fetch_twelvedata_series($symbol, $limit) {
    $limit = (int)$limit;
    if ($limit < 1) $limit = 24;
    $td = _ls_to_twelvedata($symbol);

    // File cache 30 seconds
    $cache_file = sys_get_temp_dir() . '/lm_klines_' . md5($td . '_' . $limit) . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 30) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $arr = json_decode($cached, true);
            if (is_array($arr) && count($arr) > 0) return $arr;
        }
    }

    $apikey = '43e686519f7b4155a4a90eaae82fb63a';
    $url = 'https://api.twelvedata.com/time_series?symbol=' . urlencode($td)
         . '&interval=1h&outputsize=' . $limit
         . '&apikey=' . $apikey;
    $body = _ls_http_get($url);
    if ($body === null) return array();

    $data = json_decode($body, true);
    if (!is_array($data) || !isset($data['values']) || !is_array($data['values'])) return array();

    // Twelve Data returns newest first — reverse so oldest first
    $values = array_reverse($data['values']);

    $candles = array();
    foreach ($values as $v) {
        $candles[] = array(
            'time'   => (float)strtotime($v['datetime']),
            'open'   => (float)$v['open'],
            'high'   => (float)$v['high'],
            'low'    => (float)$v['low'],
            'close'  => (float)$v['close'],
            'volume' => isset($v['volume']) ? (float)$v['volume'] : 0
        );
    }

    @file_put_contents($cache_file, json_encode($candles));
    return $candles;
}

// ────────────────────────────────────────────────────────────
//  Candle fetching — Finnhub (stocks)
//  resolution=60 for hourly candles
// ────────────────────────────────────────────────────────────

function _ls_fetch_finnhub_klines($symbol, $limit) {
    $limit = (int)$limit;
    if ($limit < 1) $limit = 24;

    // File cache 30 seconds
    $cache_file = sys_get_temp_dir() . '/lm_klines_finnhub_' . md5($symbol . '_' . $limit) . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 30) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $arr = json_decode($cached, true);
            if (is_array($arr) && count($arr) > 0) return $arr;
        }
    }

    $api_key = isset($GLOBALS['FINNHUB_API_KEY']) ? $GLOBALS['FINNHUB_API_KEY'] : '';
    if ($api_key === '') return array();

    $to = time();
    $from = $to - ($limit * 3600 * 3); // extra buffer for weekends

    $url = 'https://finnhub.io/api/v1/stock/candle'
         . '?symbol=' . urlencode($symbol)
         . '&resolution=60'
         . '&from=' . $from
         . '&to=' . $to
         . '&token=' . urlencode($api_key);

    $body = _ls_http_get($url);
    if ($body === null) return array();

    $data = json_decode($body, true);
    if (!is_array($data) || !isset($data['s']) || $data['s'] !== 'ok') return array();
    if (!isset($data['c']) || !is_array($data['c'])) return array();

    $candles = array();
    $count = count($data['c']);
    for ($i = 0; $i < $count; $i++) {
        $candles[] = array(
            'time'   => (float)$data['t'][$i],
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

    @file_put_contents($cache_file, json_encode($candles));
    return $candles;
}

// ────────────────────────────────────────────────────────────
//  Market Hours Detection (NYSE/NASDAQ: Mon-Fri 9:30-16:00 ET)
// ────────────────────────────────────────────────────────────

function _ls_is_market_hours() {
    $et = new DateTime('now', new DateTimeZone('America/New_York'));
    $dow = (int)$et->format('N'); // 1=Mon, 7=Sun
    if ($dow > 5) return false;
    $hour = (int)$et->format('G');
    $min  = (int)$et->format('i');
    $time_mins = $hour * 60 + $min;
    return ($time_mins >= 570 && $time_mins < 960); // 9:30-16:00
}

// ────────────────────────────────────────────────────────────
//  Technical Indicators
// ────────────────────────────────────────────────────────────

/**
 * RSI(period) — standard Wilder's smoothed RSI
 * @param array $closes Array of closing prices (oldest first)
 * @param int $period Usually 14
 * @return float|null RSI value (0-100) or null if not enough data
 */
function _ls_calc_rsi($closes, $period) {
    $n = count($closes);
    if ($n < $period + 1) return null;

    // Calculate gains and losses
    $gains = array();
    $losses = array();
    for ($i = 1; $i < $n; $i++) {
        $diff = $closes[$i] - $closes[$i - 1];
        if ($diff > 0) {
            $gains[] = $diff;
            $losses[] = 0;
        } else {
            $gains[] = 0;
            $losses[] = abs($diff);
        }
    }

    // First average over initial period
    $avg_gain = 0;
    $avg_loss = 0;
    for ($i = 0; $i < $period; $i++) {
        $avg_gain += $gains[$i];
        $avg_loss += $losses[$i];
    }
    $avg_gain = $avg_gain / $period;
    $avg_loss = $avg_loss / $period;

    // Smoothed RS for remaining bars
    $gc = count($gains);
    for ($i = $period; $i < $gc; $i++) {
        $avg_gain = ($avg_gain * ($period - 1) + $gains[$i]) / $period;
        $avg_loss = ($avg_loss * ($period - 1) + $losses[$i]) / $period;
    }

    if ($avg_loss == 0) return 100;
    $rs = $avg_gain / $avg_loss;
    return 100 - (100 / (1 + $rs));
}

/**
 * EMA (Exponential Moving Average)
 * @param array $data Array of values (oldest first)
 * @param int $period
 * @return array Array of EMA values (same length as input; first period-1 are SMA-seeded)
 */
function _ls_calc_ema($data, $period) {
    $n = count($data);
    if ($n < $period) return array();

    $mult = 2.0 / ($period + 1);
    $ema = array();

    // Seed with SMA of first $period values
    $sum = 0;
    for ($i = 0; $i < $period; $i++) {
        $sum += $data[$i];
        $ema[$i] = 0; // placeholder until SMA ready
    }
    $ema[$period - 1] = $sum / $period;

    // Calculate EMA from period onward
    for ($i = $period; $i < $n; $i++) {
        $ema[$i] = ($data[$i] - $ema[$i - 1]) * $mult + $ema[$i - 1];
    }

    return $ema;
}

/**
 * Bollinger Bands
 * @param array $closes Closing prices (oldest first)
 * @param int $period Usually 20
 * @param float $std_dev_mult Usually 2.0
 * @return array array('upper'=>float, 'middle'=>float, 'lower'=>float, 'bandwidth'=>float,
 *               'history_bw'=>array()) or null
 */
function _ls_calc_bollinger($closes, $period, $std_dev_mult) {
    $n = count($closes);
    if ($n < $period) return null;

    // Calculate bandwidth history for squeeze detection
    $bw_history = array();
    $last_upper = 0;
    $last_middle = 0;
    $last_lower = 0;

    for ($start = 0; $start <= $n - $period; $start++) {
        $slice = array_slice($closes, $start, $period);
        $mean = array_sum($slice) / $period;

        // Standard deviation
        $sq_sum = 0;
        foreach ($slice as $v) {
            $sq_sum += ($v - $mean) * ($v - $mean);
        }
        $std = sqrt($sq_sum / $period);

        $upper  = $mean + $std_dev_mult * $std;
        $lower  = $mean - $std_dev_mult * $std;
        $bw = ($mean > 0) ? ($upper - $lower) / $mean : 0;

        $bw_history[] = $bw;
        $last_upper  = $upper;
        $last_middle = $mean;
        $last_lower  = $lower;
    }

    return array(
        'upper'      => $last_upper,
        'middle'     => $last_middle,
        'lower'      => $last_lower,
        'bandwidth'  => end($bw_history),
        'history_bw' => $bw_history
    );
}

/**
 * ATR (Average True Range)
 * @param array $highs
 * @param array $lows
 * @param array $closes
 * @param int $period Usually 14
 * @return array array('atr'=>float, 'history'=>array()) or null
 */
function _ls_calc_atr($highs, $lows, $closes, $period) {
    $n = count($closes);
    if ($n < $period + 1) return null;

    $trs = array();
    for ($i = 1; $i < $n; $i++) {
        $hl = $highs[$i] - $lows[$i];
        $hc = abs($highs[$i] - $closes[$i - 1]);
        $lc = abs($lows[$i] - $closes[$i - 1]);
        $tr = max($hl, max($hc, $lc));
        $trs[] = $tr;
    }

    // SMA of TR over period
    $atr_history = array();
    $tc = count($trs);
    for ($start = 0; $start <= $tc - $period; $start++) {
        $slice = array_slice($trs, $start, $period);
        $atr_history[] = array_sum($slice) / $period;
    }

    if (count($atr_history) == 0) return null;
    return array(
        'atr'     => end($atr_history),
        'history' => $atr_history
    );
}

/**
 * MACD — EMA(12) - EMA(26), Signal = EMA(9) of MACD, Histogram = MACD - Signal
 * @param array $closes
 * @return array array('macd'=>float, 'signal'=>float, 'histogram'=>float,
 *               'prev_histogram'=>float) or null
 */
function _ls_calc_macd($closes) {
    $n = count($closes);
    if ($n < 26) return null;

    $ema12 = _ls_calc_ema($closes, 12);
    $ema26 = _ls_calc_ema($closes, 26);

    // MACD line = EMA12 - EMA26 (valid from index 25 onward)
    $macd_line = array();
    for ($i = 25; $i < $n; $i++) {
        $macd_line[] = $ema12[$i] - $ema26[$i];
    }

    if (count($macd_line) < 9) return null;

    // Signal = EMA(9) of MACD line
    $signal = _ls_calc_ema($macd_line, 9);
    $mc = count($macd_line);
    $sc = count($signal);

    $cur_macd = $macd_line[$mc - 1];
    $cur_signal = $signal[$sc - 1];
    $cur_hist = $cur_macd - $cur_signal;

    $prev_hist = 0;
    if ($mc >= 2 && $sc >= 2) {
        $prev_hist = $macd_line[$mc - 2] - $signal[$sc - 2];
    }

    return array(
        'macd'           => $cur_macd,
        'signal'         => $cur_signal,
        'histogram'      => $cur_hist,
        'prev_histogram' => $prev_hist
    );
}

// ────────────────────────────────────────────────────────────
//  Helper: extract arrays from candles
// ────────────────────────────────────────────────────────────

function _ls_extract_closes($candles) {
    $out = array();
    foreach ($candles as $c) $out[] = (float)$c['close'];
    return $out;
}

function _ls_extract_highs($candles) {
    $out = array();
    foreach ($candles as $c) $out[] = (float)$c['high'];
    return $out;
}

function _ls_extract_lows($candles) {
    $out = array();
    foreach ($candles as $c) $out[] = (float)$c['low'];
    return $out;
}

function _ls_extract_volumes($candles) {
    $out = array();
    foreach ($candles as $c) $out[] = (float)$c['volume'];
    return $out;
}

// ────────────────────────────────────────────────────────────
//  Ulcer Index — drawdown-weighted volatility (for VAM algorithm)
//  Science: Martin Ratio = Return / Ulcer Index (Moskowitz 2012)
// ────────────────────────────────────────────────────────────

function _ls_calc_ulcer_index($closes, $period) {
    $n = count($closes);
    if ($n < $period) return null;

    $start = $n - $period;
    $peak = $closes[$start];
    $sq_sum = 0;
    $count = 0;

    for ($i = $start; $i < $n; $i++) {
        if ($closes[$i] > $peak) $peak = $closes[$i];
        if ($peak > 0) {
            $dd_pct = (($closes[$i] - $peak) / $peak) * 100;
            $sq_sum += $dd_pct * $dd_pct;
        }
        $count++;
    }

    if ($count == 0) return null;
    return sqrt($sq_sum / $count);
}

// ────────────────────────────────────────────────────────────
//  Volume Z-Score — statistical volume anomaly detection
//  Science: Trading Volume Alpha (NBER 2024)
// ────────────────────────────────────────────────────────────

function _ls_calc_volume_zscore($volumes) {
    $n = count($volumes);
    if ($n < 3) return null;

    $lookback = min($n - 1, 20);
    $start = $n - 1 - $lookback;

    $sum = 0;
    $count = 0;
    for ($i = $start; $i < $n - 1; $i++) {
        $sum += $volumes[$i];
        $count++;
    }
    if ($count == 0) return null;

    $mean = $sum / $count;

    $sq_sum = 0;
    for ($i = $start; $i < $n - 1; $i++) {
        $sq_sum += ($volumes[$i] - $mean) * ($volumes[$i] - $mean);
    }
    $stddev = sqrt($sq_sum / $count);

    if ($stddev == 0) return null;

    $last_vol = $volumes[$n - 1];
    return ($last_vol - $mean) / $stddev;
}

// ────────────────────────────────────────────────────────────
//  ADX (Average Directional Index) — Wilder's ADX with +DI/-DI
//  Science: STOCKSUNIFY2 Alpha Predator uses ADX > 25 as trend gate
// ────────────────────────────────────────────────────────────

function _ls_calc_adx($highs, $lows, $closes, $period) {
    $n = count($closes);
    if ($n < $period + 2) return null;

    // True Range, +DM, -DM
    $tr_arr = array();
    $plus_dm = array();
    $minus_dm = array();
    for ($i = 1; $i < $n; $i++) {
        $hl = $highs[$i] - $lows[$i];
        $hc = abs($highs[$i] - $closes[$i - 1]);
        $lc = abs($lows[$i] - $closes[$i - 1]);
        $tr_arr[] = max($hl, max($hc, $lc));

        $up_move = $highs[$i] - $highs[$i - 1];
        $down_move = $lows[$i - 1] - $lows[$i];

        if ($up_move > $down_move && $up_move > 0) {
            $plus_dm[] = $up_move;
        } else {
            $plus_dm[] = 0;
        }
        if ($down_move > $up_move && $down_move > 0) {
            $minus_dm[] = $down_move;
        } else {
            $minus_dm[] = 0;
        }
    }

    $tc = count($tr_arr);
    if ($tc < $period) return null;

    // Wilder's smoothing for ATR, +DM, -DM
    $atr_s = 0;
    $pdm_s = 0;
    $mdm_s = 0;
    for ($i = 0; $i < $period; $i++) {
        $atr_s += $tr_arr[$i];
        $pdm_s += $plus_dm[$i];
        $mdm_s += $minus_dm[$i];
    }

    $dx_arr = array();
    for ($i = $period; $i < $tc; $i++) {
        $atr_s = $atr_s - ($atr_s / $period) + $tr_arr[$i];
        $pdm_s = $pdm_s - ($pdm_s / $period) + $plus_dm[$i];
        $mdm_s = $mdm_s - ($mdm_s / $period) + $minus_dm[$i];

        $plus_di = ($atr_s > 0) ? ($pdm_s / $atr_s) * 100 : 0;
        $minus_di = ($atr_s > 0) ? ($mdm_s / $atr_s) * 100 : 0;
        $di_sum = $plus_di + $minus_di;
        $dx = ($di_sum > 0) ? abs($plus_di - $minus_di) / $di_sum * 100 : 0;
        $dx_arr[] = $dx;
    }

    $dxc = count($dx_arr);
    if ($dxc < $period) return null;

    // ADX = Wilder's smoothed average of DX
    $adx = 0;
    for ($i = 0; $i < $period; $i++) {
        $adx += $dx_arr[$i];
    }
    $adx = $adx / $period;
    for ($i = $period; $i < $dxc; $i++) {
        $adx = ($adx * ($period - 1) + $dx_arr[$i]) / $period;
    }

    // Recalc final +DI/-DI
    $plus_di_final = ($atr_s > 0) ? ($pdm_s / $atr_s) * 100 : 0;
    $minus_di_final = ($atr_s > 0) ? ($mdm_s / $atr_s) * 100 : 0;

    return array(
        'adx'      => $adx,
        'plus_di'  => $plus_di_final,
        'minus_di' => $minus_di_final
    );
}

// ────────────────────────────────────────────────────────────
//  RSI Series — returns array of all RSI values (needed for StochRSI)
// ────────────────────────────────────────────────────────────

function _ls_calc_rsi_series($closes, $period) {
    $n = count($closes);
    if ($n < $period + 1) return array();

    $gains = array();
    $losses = array();
    for ($i = 1; $i < $n; $i++) {
        $diff = $closes[$i] - $closes[$i - 1];
        if ($diff > 0) {
            $gains[] = $diff;
            $losses[] = 0;
        } else {
            $gains[] = 0;
            $losses[] = abs($diff);
        }
    }

    // First average
    $avg_gain = 0;
    $avg_loss = 0;
    for ($i = 0; $i < $period; $i++) {
        $avg_gain += $gains[$i];
        $avg_loss += $losses[$i];
    }
    $avg_gain = $avg_gain / $period;
    $avg_loss = $avg_loss / $period;

    $rsi_arr = array();
    if ($avg_loss == 0) {
        $rsi_arr[] = 100;
    } else {
        $rs = $avg_gain / $avg_loss;
        $rsi_arr[] = 100 - (100 / (1 + $rs));
    }

    $gc = count($gains);
    for ($i = $period; $i < $gc; $i++) {
        $avg_gain = ($avg_gain * ($period - 1) + $gains[$i]) / $period;
        $avg_loss = ($avg_loss * ($period - 1) + $losses[$i]) / $period;
        if ($avg_loss == 0) {
            $rsi_arr[] = 100;
        } else {
            $rs = $avg_gain / $avg_loss;
            $rsi_arr[] = 100 - (100 / (1 + $rs));
        }
    }

    return $rsi_arr;
}

// ────────────────────────────────────────────────────────────
//  Stochastic RSI — StochRSI(rsi_period, stoch_period, K_smooth, D_smooth)
//  Science: Combines RSI with Stochastic oscillator for oversold/overbought extremes
// ────────────────────────────────────────────────────────────

function _ls_calc_stoch_rsi($closes, $rsi_period, $stoch_period, $k_smooth, $d_smooth) {
    $rsi_arr = _ls_calc_rsi_series($closes, $rsi_period);
    $rc = count($rsi_arr);
    if ($rc < $stoch_period) return null;

    // Raw Stochastic of RSI
    $stoch_raw = array();
    for ($i = $stoch_period - 1; $i < $rc; $i++) {
        $slice = array_slice($rsi_arr, $i - $stoch_period + 1, $stoch_period);
        $min_rsi = min($slice);
        $max_rsi = max($slice);
        $range = $max_rsi - $min_rsi;
        if ($range == 0) {
            $stoch_raw[] = 50;
        } else {
            $stoch_raw[] = ($rsi_arr[$i] - $min_rsi) / $range * 100;
        }
    }

    $src = count($stoch_raw);
    if ($src < $k_smooth) return null;

    // K line = SMA(k_smooth) of stoch_raw
    $k_arr = array();
    for ($i = $k_smooth - 1; $i < $src; $i++) {
        $slice = array_slice($stoch_raw, $i - $k_smooth + 1, $k_smooth);
        $k_arr[] = array_sum($slice) / $k_smooth;
    }

    $kc = count($k_arr);
    if ($kc < $d_smooth) return null;

    // D line = SMA(d_smooth) of K
    $d_arr = array();
    for ($i = $d_smooth - 1; $i < $kc; $i++) {
        $slice = array_slice($k_arr, $i - $d_smooth + 1, $d_smooth);
        $d_arr[] = array_sum($slice) / $d_smooth;
    }

    $dc = count($d_arr);
    if ($dc < 2 || $kc < 2) return null;

    return array(
        'k'      => $k_arr[$kc - 1],
        'd'      => $d_arr[$dc - 1],
        'prev_k' => $k_arr[$kc - 2],
        'prev_d' => ($dc >= 2) ? $d_arr[$dc - 2] : $d_arr[$dc - 1]
    );
}

// ────────────────────────────────────────────────────────────
//  Awesome Oscillator — SMA(5, median) - SMA(34, median)
//  Science: Bill Williams momentum indicator, used in STOCKSUNIFY2
// ────────────────────────────────────────────────────────────

function _ls_calc_awesome_oscillator($highs, $lows) {
    $n = count($highs);
    if ($n < 34) return null;

    // Median prices = (high + low) / 2
    $medians = array();
    for ($i = 0; $i < $n; $i++) {
        $medians[] = ($highs[$i] + $lows[$i]) / 2;
    }

    // SMA(5) and SMA(34) of medians — compute last 2 values for crossover detection
    $ao_values = array();
    for ($i = 33; $i < $n; $i++) {
        $sma5 = 0;
        for ($j = $i - 4; $j <= $i; $j++) {
            $sma5 += $medians[$j];
        }
        $sma5 = $sma5 / 5;

        $sma34 = 0;
        for ($j = $i - 33; $j <= $i; $j++) {
            $sma34 += $medians[$j];
        }
        $sma34 = $sma34 / 34;

        $ao_values[] = $sma5 - $sma34;
    }

    $ac = count($ao_values);
    if ($ac < 2) return null;

    return array(
        'ao'      => $ao_values[$ac - 1],
        'prev_ao' => $ao_values[$ac - 2]
    );
}

// ────────────────────────────────────────────────────────────
//  Ichimoku Cloud — Tenkan-sen, Kijun-sen, Senkou Span A/B
//  Adapted periods for hourly data: Tenkan(9), Kijun(26), Senkou B(26)
//  (Standard 52 for Senkou B needs too many candles; 26 works for 48-candle window)
// ────────────────────────────────────────────────────────────

function _ls_calc_ichimoku($highs, $lows, $tenkan_p, $kijun_p, $senkou_b_p) {
    $n = count($highs);
    if ($n < max($tenkan_p, max($kijun_p, $senkou_b_p))) return null;

    // Helper: highest high / lowest low over last $p candles ending at index $idx
    // Tenkan-sen = (highest high + lowest low) / 2 over tenkan_p
    $last = $n - 1;

    // Tenkan-sen (conversion line)
    $hh_t = $highs[$last];
    $ll_t = $lows[$last];
    for ($i = $last - $tenkan_p + 1; $i <= $last; $i++) {
        if ($i < 0) continue;
        if ($highs[$i] > $hh_t) $hh_t = $highs[$i];
        if ($lows[$i] < $ll_t) $ll_t = $lows[$i];
    }
    $tenkan = ($hh_t + $ll_t) / 2;

    // Kijun-sen (base line)
    $hh_k = $highs[$last];
    $ll_k = $lows[$last];
    for ($i = $last - $kijun_p + 1; $i <= $last; $i++) {
        if ($i < 0) continue;
        if ($highs[$i] > $hh_k) $hh_k = $highs[$i];
        if ($lows[$i] < $ll_k) $ll_k = $lows[$i];
    }
    $kijun = ($hh_k + $ll_k) / 2;

    // Previous Tenkan/Kijun (1 candle back) for crossover detection
    $prev_last = $last - 1;
    $prev_tenkan = $tenkan;
    $prev_kijun = $kijun;
    if ($prev_last >= $tenkan_p) {
        $hh = $highs[$prev_last];
        $ll = $lows[$prev_last];
        for ($i = $prev_last - $tenkan_p + 1; $i <= $prev_last; $i++) {
            if ($i < 0) continue;
            if ($highs[$i] > $hh) $hh = $highs[$i];
            if ($lows[$i] < $ll) $ll = $lows[$i];
        }
        $prev_tenkan = ($hh + $ll) / 2;

        $hh = $highs[$prev_last];
        $ll = $lows[$prev_last];
        for ($i = $prev_last - $kijun_p + 1; $i <= $prev_last; $i++) {
            if ($i < 0) continue;
            if ($highs[$i] > $hh) $hh = $highs[$i];
            if ($lows[$i] < $ll) $ll = $lows[$i];
        }
        $prev_kijun = ($hh + $ll) / 2;
    }

    // Senkou Span A = (Tenkan + Kijun) / 2 (projected 26 periods ahead, but for current we use now)
    $senkou_a = ($tenkan + $kijun) / 2;

    // Senkou Span B = (highest high + lowest low) / 2 over senkou_b_p
    $hh_b = $highs[$last];
    $ll_b = $lows[$last];
    for ($i = $last - $senkou_b_p + 1; $i <= $last; $i++) {
        if ($i < 0) continue;
        if ($highs[$i] > $hh_b) $hh_b = $highs[$i];
        if ($lows[$i] < $ll_b) $ll_b = $lows[$i];
    }
    $senkou_b = ($hh_b + $ll_b) / 2;

    $cloud_top = max($senkou_a, $senkou_b);
    $cloud_bottom = min($senkou_a, $senkou_b);

    return array(
        'tenkan'       => $tenkan,
        'kijun'        => $kijun,
        'prev_tenkan'  => $prev_tenkan,
        'prev_kijun'   => $prev_kijun,
        'senkou_a'     => $senkou_a,
        'senkou_b'     => $senkou_b,
        'cloud_top'    => $cloud_top,
        'cloud_bottom' => $cloud_bottom
    );
}

// ────────────────────────────────────────────────────────────
//  Regime Detection — UPGRADED: HMM + Hurst + SMA fallback
//  Science: Ang & Bekaert (2004) HMM, Mandelbrot (1963) Hurst
//  Replaces simple SMA cross with 3-state HMM when available
// ────────────────────────────────────────────────────────────

// World-Class: fetch intelligence metrics from DB
function _ls_get_intelligence($conn, $metric_name, $asset_class) {
    if (!isset($GLOBALS['_ls_intelligence_cache'])) {
        $GLOBALS['_ls_intelligence_cache'] = array();
    }
    $cache_key = $metric_name . '_' . $asset_class;
    if (isset($GLOBALS['_ls_intelligence_cache'][$cache_key])) {
        return $GLOBALS['_ls_intelligence_cache'][$cache_key];
    }

    $safe_metric = $conn->real_escape_string($metric_name);
    $safe_asset = $conn->real_escape_string($asset_class);
    $r = $conn->query("SELECT metric_value, metric_label, metadata, updated_at
        FROM lm_intelligence
        WHERE metric_name='$safe_metric' AND asset_class='$safe_asset'
        ORDER BY updated_at DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $r->free();
        $result = array(
            'value' => (float)$row['metric_value'],
            'label' => $row['metric_label'],
            'metadata' => $row['metadata'],
            'updated' => $row['updated_at']
        );
        $GLOBALS['_ls_intelligence_cache'][$cache_key] = $result;
        return $result;
    }
    return null;
}

// World-Class: get algo health / online learning weight
function _ls_get_algo_weight($conn, $algo_name, $asset_class) {
    if (!isset($GLOBALS['_ls_algo_weights'])) {
        // Load all weights at once
        $GLOBALS['_ls_algo_weights'] = array();
        $r = $conn->query("SELECT algorithm_name, asset_class, online_weight, decay_status
            FROM lm_algo_health ORDER BY algorithm_name");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $key = $row['algorithm_name'] . '|' . $row['asset_class'];
                $GLOBALS['_ls_algo_weights'][$key] = array(
                    'weight' => (float)$row['online_weight'],
                    'status' => $row['decay_status']
                );
            }
            $r->free();
        }
    }

    $key = $algo_name . '|' . $asset_class;
    if (isset($GLOBALS['_ls_algo_weights'][$key])) {
        return $GLOBALS['_ls_algo_weights'][$key];
    }
    // Fallback: check ALL asset class
    $key_all = $algo_name . '|ALL';
    if (isset($GLOBALS['_ls_algo_weights'][$key_all])) {
        return $GLOBALS['_ls_algo_weights'][$key_all];
    }
    return array('weight' => 1.0, 'status' => 'unknown');
}

// World-Class: get Hurst exponent for strategy selection
function _ls_get_hurst($conn, $asset_class) {
    $intel = _ls_get_intelligence($conn, 'hurst_exponent', $asset_class);
    if ($intel) {
        return array('value' => $intel['value'], 'label' => $intel['label']);
    }
    return array('value' => 0.50, 'label' => 'random_walk'); // Default
}

// World-Class: check if algo should be disabled based on Hurst exponent
function _ls_hurst_gate($conn, $algo_name, $asset_class) {
    $hurst = _ls_get_hurst($conn, $asset_class);
    $h = $hurst['value'];

    // Momentum algos: disable when market is mean-reverting (H < 0.45)
    $momentum_algos = array(
        'Momentum Burst', 'Breakout 24h', 'Volatility Breakout',
        'Trend Sniper', 'Volume Spike', 'VAM',
        'ADX Trend Strength', 'Alpha Predator'
    );

    // Mean-reversion algos: disable when market is trending (H > 0.55)
    $mr_algos = array(
        'RSI Reversal', 'DCA Dip', 'Dip Recovery', 'Mean Reversion Sniper'
    );

    if (in_array($algo_name, $momentum_algos) && $h < 0.45) {
        return false; // Disable momentum in mean-reverting market
    }
    if (in_array($algo_name, $mr_algos) && $h > 0.55) {
        return false; // Disable mean-reversion in trending market
    }
    return true; // Allow
}

function _ls_get_regime($conn, $asset, $candles, $symbol) {
    // ── Try HMM regime first (from Python ML pipeline) ──
    $hmm = _ls_get_intelligence($conn, 'hmm_regime', $asset);
    if ($hmm) {
        $label = $hmm['label'];
        // Map HMM labels to existing regime gate format
        if ($label === 'bull') return 'bull';
        if ($label === 'bear') return 'bear';
        if ($label === 'sideways') return 'neutral';
    }

    // ── Fallback: original SMA-based regime detection ──
    // Crypto regime: BTC above 24h SMA = bull
    if ($asset === 'CRYPTO') {
        if (!isset($GLOBALS['_ls_btc_regime'])) {
            if ($symbol === 'BTCUSD') {
                $btc_candles = $candles;
            } else {
                $btc_candles = _ls_fetch_binance_klines('BTCUSD', 48);
            }
            $btc_closes = _ls_extract_closes($btc_candles);
            $bc = count($btc_closes);
            if ($bc >= 12) {
                $sum = 0;
                for ($i = 0; $i < $bc; $i++) $sum += $btc_closes[$i];
                $sma = $sum / $bc;
                $GLOBALS['_ls_btc_regime'] = ($btc_closes[$bc - 1] >= $sma) ? 'bull' : 'bear';
            } else {
                $GLOBALS['_ls_btc_regime'] = 'bull';
            }
        }
        return $GLOBALS['_ls_btc_regime'];
    }

    // Forex regime: USD strength via USDJPY trend, mapped to pair-specific bull/bear
    // (Feb 2026 fix) Previous code returned 'usd_strong'/'usd_weak' which never
    // matched the 'bear'/'bull' checks in algo regime gates, so forex signals
    // were NEVER regime-gated. This caused counter-trend entries (e.g. LONG
    // EUR/USD when USD was strengthening). Now maps to pair-specific direction.
    if ($asset === 'FOREX') {
        if (!isset($GLOBALS['_ls_fx_regime_raw'])) {
            $jpy_candles = _ls_fetch_twelvedata_series('USDJPY', 48);
            $jpy_closes = _ls_extract_closes($jpy_candles);
            $jc = count($jpy_closes);
            if ($jc >= 12) {
                $sum = 0;
                for ($i = 0; $i < $jc; $i++) $sum += $jpy_closes[$i];
                $sma = $sum / $jc;
                $GLOBALS['_ls_fx_regime_raw'] = ($jpy_closes[$jc - 1] > $sma) ? 'usd_strong' : 'usd_weak';
            } else {
                $GLOBALS['_ls_fx_regime_raw'] = 'neutral';
            }
        }
        $usd_regime = $GLOBALS['_ls_fx_regime_raw'];
        if ($usd_regime === 'neutral') return 'neutral';

        // Map USD strength to pair-specific direction:
        // Pairs where USD is QUOTE (EURUSD, GBPUSD, AUDUSD, NZDUSD):
        //   usd_strong → pair falls → 'bear' | usd_weak → pair rises → 'bull'
        // Pairs where USD is BASE (USDJPY, USDCAD, USDCHF):
        //   usd_strong → pair rises → 'bull' | usd_weak → pair falls → 'bear'
        // Non-USD pairs (EURGBP): neutral — USD regime doesn't apply
        $sym_upper = strtoupper($symbol);
        $usd_is_base  = (strpos($sym_upper, 'USD') === 0); // USD is first 3 chars
        $usd_is_quote = (!$usd_is_base && strpos($sym_upper, 'USD') !== false);

        if (!$usd_is_base && !$usd_is_quote) return 'neutral'; // e.g. EURGBP

        if ($usd_regime === 'usd_strong') {
            return $usd_is_base ? 'bull' : 'bear';
        } else {
            return $usd_is_base ? 'bear' : 'bull';
        }
    }

    // Stock regime: own price above 20-candle SMA
    if ($asset === 'STOCK') {
        $stk_closes = _ls_extract_closes($candles);
        $sc = count($stk_closes);
        if ($sc >= 20) {
            $sum = 0;
            for ($i = $sc - 20; $i < $sc; $i++) $sum += $stk_closes[$i];
            $sma = $sum / 20;
            return ($stk_closes[$sc - 1] >= $sma) ? 'bull' : 'bear';
        }
    }

    return 'neutral';
}

// ────────────────────────────────────────────────────────────
//  Helper: fetch learned params for an algorithm
// ────────────────────────────────────────────────────────────

function _ls_get_learned_params($conn, $algo_name, $asset_class) {
    $safe_algo  = $conn->real_escape_string($algo_name);
    $safe_asset = $conn->real_escape_string($asset_class);
    $res = $conn->query("SELECT best_tp_pct, best_sl_pct, best_hold_hours FROM lm_hour_learning
        WHERE algorithm_name='$safe_algo' AND asset_class='$safe_asset'
        ORDER BY calc_date DESC LIMIT 1");
    if ($res && $res->num_rows > 0) {
        $lp = $res->fetch_assoc();

        // Clamp learned params to prevent overfitting:
        // TP/SL must stay within 0.3x - 2.5x of the original defaults
        // Hold must stay within 0.25x - 3x of original
        $defaults = _ls_get_original_defaults($algo_name, $asset_class);
        $orig_tp   = $defaults['tp'];
        $orig_sl   = $defaults['sl'];
        $orig_hold = $defaults['hold'];

        $learned_tp   = (float)$lp['best_tp_pct'];
        $learned_sl   = (float)$lp['best_sl_pct'];
        $learned_hold = (int)$lp['best_hold_hours'];

        // Clamp TP: 0.3x to 2.5x original
        if ($learned_tp < $orig_tp * 0.3)  $learned_tp = round($orig_tp * 0.3, 2);
        if ($learned_tp > $orig_tp * 2.5)  $learned_tp = round($orig_tp * 2.5, 2);

        // Clamp SL: 0.3x to 2.5x original
        if ($learned_sl < $orig_sl * 0.3)  $learned_sl = round($orig_sl * 0.3, 2);
        if ($learned_sl > $orig_sl * 2.5)  $learned_sl = round($orig_sl * 2.5, 2);

        // Clamp Hold: 0.25x to 3x original
        if ($learned_hold < $orig_hold * 0.25) $learned_hold = (int)($orig_hold * 0.25);
        if ($learned_hold > $orig_hold * 3)    $learned_hold = (int)($orig_hold * 3);

        // Ensure TP > SL (positive expected value) — minimum 1.2:1 R:R
        if ($learned_tp < $learned_sl * 1.2) {
            $learned_tp = round($learned_sl * 1.2, 2);
        }

        $lp['best_tp_pct']    = $learned_tp;
        $lp['best_sl_pct']    = $learned_sl;
        $lp['best_hold_hours'] = $learned_hold;

        return $lp;
    }
    return null;
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 1: Momentum Burst
//  If latest 1h close/open change > 2% => BUY.
//  Strength based on magnitude. TP 3%, SL 1.5%, Hold 4h.
// ────────────────────────────────────────────────────────────

function _ls_algo_momentum_burst($candles, $price, $symbol, $asset) {
    global $conn;
    $n = count($candles);
    if ($n < 2) return null;

    $last = $candles[$n - 1];
    $open = (float)$last['open'];
    if ($open == 0) return null;

    $change_pct = (($last['close'] - $open) / $open) * 100;

    if (abs($change_pct) < 2.0) return null;

    $signal_type = ($change_pct > 0) ? 'BUY' : 'SHORT';
    $strength = min(100, (int)(abs($change_pct) * 20));

    // Regime gate — suppress counter-regime signals
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($signal_type === 'BUY' && $regime === 'bear') return null;
    if ($signal_type === 'SHORT' && $regime === 'bull') return null;

    $tp  = 3.0;
    $sl  = 1.5;
    $hold = 8;

    // Check learned params
    $lp = _ls_get_learned_params($conn, 'Momentum Burst', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Momentum Burst',
        'signal_type'     => $signal_type,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'     => 'Hourly candle moved ' . round($change_pct, 2) . '% (' . $signal_type . ' momentum)',
            'change_pct' => round($change_pct, 2),
            'open'       => $open,
            'close'      => (float)$last['close']
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 2: RSI Reversal
//  RSI(14) < 30 => BUY (oversold), RSI > 70 => SHORT (overbought).
//  Strength = distance from 50. TP 2%, SL 1%, Hold 6h.
// ────────────────────────────────────────────────────────────

function _ls_algo_rsi_reversal($candles, $price, $symbol, $asset) {
    global $conn;
    $closes = _ls_extract_closes($candles);
    $rsi = _ls_calc_rsi($closes, 14);
    if ($rsi === null) return null;

    if ($rsi >= 30 && $rsi <= 70) return null;

    $signal_type = ($rsi < 30) ? 'BUY' : 'SHORT';
    $strength = min(100, (int)(abs($rsi - 50) * 2));

    // Regime gate — suppress BUY in bear (falling knife risk for mean-reversion)
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($signal_type === 'BUY' && $regime === 'bear') return null;

    $tp   = 2.0;
    $sl   = 1.0;
    $hold = 12;

    $lp = _ls_get_learned_params($conn, 'RSI Reversal', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'RSI Reversal',
        'signal_type'     => $signal_type,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason' => 'RSI at ' . round($rsi, 1) . ($rsi < 30 ? ' (oversold)' : ' (overbought)'),
            'rsi'    => round($rsi, 1)
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 3: Breakout 24h
//  Price > max(high) of last 24 candles => BUY breakout.
//  Volume confirm: current volume > 1.5x avg. TP 3%, SL 2%, Hold 8h.
// ────────────────────────────────────────────────────────────

function _ls_algo_breakout_24h($candles, $price, $symbol, $asset) {
    global $conn;
    $n = count($candles);
    if ($n < 3) return null;

    // Look at all candles except the last one to establish range
    $max_high = 0;
    $vol_sum = 0;
    $lookback = min($n - 1, 24);
    for ($i = $n - $lookback - 1; $i < $n - 1; $i++) {
        if ($i < 0) continue;
        if ((float)$candles[$i]['high'] > $max_high) {
            $max_high = (float)$candles[$i]['high'];
        }
        $vol_sum += (float)$candles[$i]['volume'];
    }

    if ($max_high == 0) return null;

    $avg_vol = $vol_sum / max(1, $lookback);
    $cur_vol = (float)$candles[$n - 1]['volume'];

    // Price must break above 24h high
    if ($price <= $max_high) return null;

    // Volume confirmation
    $vol_ok = ($avg_vol > 0 && $cur_vol > $avg_vol * 1.5);

    // Still signal but lower strength without volume confirm
    $breakout_pct = (($price - $max_high) / $max_high) * 100;
    $strength = min(100, (int)($breakout_pct * 15 + ($vol_ok ? 30 : 0)));
    if ($strength < 20) $strength = 20;

    // Regime gate — suppress breakout BUY in bear market
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($regime === 'bear') return null;

    $tp   = 8.0;
    $sl   = 2.0;
    $hold = 16;

    $lp = _ls_get_learned_params($conn, 'Breakout 24h', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Breakout 24h',
        'signal_type'     => 'BUY',
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'       => 'Price broke above 24h high of ' . round($max_high, 4) . ($vol_ok ? ' with volume confirmation' : ' (no volume confirm)'),
            'high_24h'     => round($max_high, 4),
            'breakout_pct' => round($breakout_pct, 2),
            'volume_ok'    => $vol_ok,
            'cur_volume'   => $cur_vol,
            'avg_volume'   => round($avg_vol, 2)
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 4: DCA Dip
//  24h change < -5% => BUY (dip accumulate).
//  Strength based on dip magnitude. TP 5%, SL 3%, Hold 24h.
// ────────────────────────────────────────────────────────────

function _ls_algo_dca_dip($candles, $price, $symbol, $asset) {
    global $conn;
    $n = count($candles);
    if ($n < 2) return null;

    // Compare current price with close from ~24h ago (first candle)
    $old_close = (float)$candles[0]['close'];
    if ($old_close == 0) return null;

    $change_24h_pct = (($price - $old_close) / $old_close) * 100;

    // Asset-class thresholds: stocks need shallower dip (-2%) vs crypto (-5%)
    $dip_threshold = ($asset === 'STOCK') ? -2.0 : -5.0;
    if ($change_24h_pct >= $dip_threshold) return null;

    $dip_magnitude = abs($change_24h_pct);
    $strength = min(100, (int)($dip_magnitude * 8));

    // Regime gate — suppress dip buying in bear (falling knife risk)
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($regime === 'bear') return null;

    $tp   = 5.0;
    $sl   = 3.0;
    $hold = 48;

    $lp = _ls_get_learned_params($conn, 'DCA Dip', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'DCA Dip',
        'signal_type'     => 'BUY',
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'         => 'Price dipped ' . round($change_24h_pct, 2) . '% in 24h — accumulation zone',
            'change_24h_pct' => round($change_24h_pct, 2),
            'price_24h_ago'  => $old_close,
            'price_now'      => $price
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 5: Bollinger Squeeze
//  Bandwidth in bottom 20th percentile of last 24 candles AND
//  price breaks above upper band => BUY.
//  TP 2.5%, SL 1.5%, Hold 4h.
// ────────────────────────────────────────────────────────────

function _ls_algo_bollinger_squeeze($candles, $price, $symbol, $asset) {
    global $conn;
    $closes = _ls_extract_closes($candles);
    $n = count($closes);
    if ($n < 20) return null;

    $bb = _ls_calc_bollinger($closes, 20, 2.0);
    if ($bb === null) return null;

    $bw_hist = $bb['history_bw'];
    $bw_count = count($bw_hist);
    if ($bw_count < 2) return null;

    // Current bandwidth
    $cur_bw = $bb['bandwidth'];

    // Check if current bandwidth is in bottom 20th percentile
    $sorted_bw = $bw_hist;
    sort($sorted_bw);
    $pct20_idx = max(0, (int)floor($bw_count * 0.20) - 1);
    $pct20_threshold = $sorted_bw[$pct20_idx];

    $is_squeeze = ($cur_bw <= $pct20_threshold);
    if (!$is_squeeze) return null;

    // Price must break above upper band
    if ($price <= $bb['upper']) return null;

    $breakout_pct = (($price - $bb['upper']) / $bb['upper']) * 100;
    $strength = min(100, 50 + (int)($breakout_pct * 20));

    // Regime gate — suppress squeeze breakout BUY in bear
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($regime === 'bear') return null;

    $tp   = 2.5;
    $sl   = 1.5;
    $hold = 8;

    $lp = _ls_get_learned_params($conn, 'Bollinger Squeeze', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Bollinger Squeeze',
        'signal_type'     => 'BUY',
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'         => 'Bollinger squeeze detected — bandwidth at ' . round($cur_bw, 4) . ' (20th pctile: ' . round($pct20_threshold, 4) . '), price broke above upper band ' . round($bb['upper'], 4),
            'bandwidth'      => round($cur_bw, 4),
            'upper_band'     => round($bb['upper'], 4),
            'lower_band'     => round($bb['lower'], 4),
            'middle_band'    => round($bb['middle'], 4),
            'breakout_pct'   => round($breakout_pct, 2)
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 6: MACD Crossover
//  MACD crosses above Signal (histogram positive) => BUY.
//  MACD crosses below Signal => SHORT. TP 2%, SL 1%, Hold 6h.
// ────────────────────────────────────────────────────────────

function _ls_algo_macd_crossover($candles, $price, $symbol, $asset) {
    global $conn;
    $closes = _ls_extract_closes($candles);
    $macd = _ls_calc_macd($closes);
    if ($macd === null) return null;

    // Crossover = histogram changed sign
    $cur_hist  = $macd['histogram'];
    $prev_hist = $macd['prev_histogram'];

    // Bullish crossover: prev <= 0 and cur > 0
    $bullish_cross = ($prev_hist <= 0 && $cur_hist > 0);
    // Bearish crossover: prev >= 0 and cur < 0
    $bearish_cross = ($prev_hist >= 0 && $cur_hist < 0);

    if (!$bullish_cross && !$bearish_cross) return null;

    $signal_type = $bullish_cross ? 'BUY' : 'SHORT';
    $strength = min(100, (int)(abs($cur_hist) * 10000 + 40));
    if ($strength > 100) $strength = 100;
    if ($strength < 30) $strength = 30;

    // Regime gate — suppress counter-regime signals
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($signal_type === 'BUY' && $regime === 'bear') return null;
    if ($signal_type === 'SHORT' && $regime === 'bull') return null;

    $tp   = 2.0;
    $sl   = 1.0;
    $hold = 12;

    $lp = _ls_get_learned_params($conn, 'MACD Crossover', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'MACD Crossover',
        'signal_type'     => $signal_type,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'    => 'MACD ' . ($bullish_cross ? 'bullish' : 'bearish') . ' crossover — histogram flipped to ' . round($cur_hist, 6),
            'macd'      => round($macd['macd'], 6),
            'signal'    => round($macd['signal'], 6),
            'histogram' => round($cur_hist, 6),
            'prev_histogram' => round($prev_hist, 6)
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 7: Consensus
//  2+ different algorithms signal the SAME DIRECTION for this symbol
//  within the last 24h => follow the majority direction.
//  Uses lm_signals (live signals table) for all asset classes.
//  TP 3%, SL 2%, Hold 24h (or learned params).
// ────────────────────────────────────────────────────────────

function _ls_algo_consensus($conn, $price, $symbol, $asset) {
    $safe_sym  = $conn->real_escape_string($symbol);
    $safe_asset = $conn->real_escape_string($asset);

    // Query recent live signals for this symbol (last 24h, exclude Consensus itself)
    $sql = "SELECT algorithm_name, signal_type
            FROM lm_signals
            WHERE symbol = '$safe_sym'
              AND asset_class = '$safe_asset'
              AND algorithm_name != 'Consensus'
              AND signal_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY signal_time DESC";
    $res = $conn->query($sql);
    if (!$res || $res->num_rows == 0) return null;

    // Count unique algorithms per direction
    $buy_algos   = array();
    $short_algos = array();
    while ($row = $res->fetch_assoc()) {
        $algo = $row['algorithm_name'];
        $dir  = strtoupper($row['signal_type']);
        if ($dir === 'BUY' || $dir === 'LONG') {
            $buy_algos[$algo] = 1;
        } elseif ($dir === 'SHORT' || $dir === 'SELL') {
            $short_algos[$algo] = 1;
        }
    }

    $buy_count   = count($buy_algos);
    $short_count = count($short_algos);
    $total       = $buy_count + $short_count;

    if ($total < 2) return null;

    // Determine majority direction — require supermajority (>= 60%)
    $direction = null;
    $majority_count = 0;
    $majority_algos = array();

    if ($buy_count >= 2 && ($buy_count / $total) >= 0.6) {
        $direction = 'BUY';
        $majority_count = $buy_count;
        $majority_algos = array_keys($buy_algos);
    } elseif ($short_count >= 2 && ($short_count / $total) >= 0.6) {
        $direction = 'SHORT';
        $majority_count = $short_count;
        $majority_algos = array_keys($short_algos);
    }

    // No clear consensus — skip
    if ($direction === null) return null;

    $strength = min(100, $majority_count * 25 + 20);

    $tp   = 3.0;
    $sl   = 2.0;
    $hold = 24;

    $lp = _ls_get_learned_params($conn, 'Consensus', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Consensus',
        'signal_type'     => $direction,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'         => $majority_count . '/' . $total . ' algorithms agree on ' . $direction . ' for ' . $symbol,
            'algo_count'     => $majority_count,
            'total_algos'    => $total,
            'direction'      => $direction,
            'buy_count'      => $buy_count,
            'short_count'    => $short_count,
            'algorithms'     => $majority_algos
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 8: Volatility Breakout
//  ATR(14) > 1.5x avg ATR of last 24 candles AND price moving up => BUY.
//  TP 3%, SL 2%, Hold 8h.
// ────────────────────────────────────────────────────────────

function _ls_algo_volatility_breakout($candles, $price, $symbol, $asset) {
    global $conn;
    $highs  = _ls_extract_highs($candles);
    $lows   = _ls_extract_lows($candles);
    $closes = _ls_extract_closes($candles);
    $n = count($candles);
    if ($n < 15) return null;

    $atr_data = _ls_calc_atr($highs, $lows, $closes, 14);
    if ($atr_data === null) return null;

    $cur_atr = $atr_data['atr'];
    $atr_hist = $atr_data['history'];
    $ah_count = count($atr_hist);
    if ($ah_count < 2) return null;

    // Average ATR over history (excluding current)
    $atr_sum = 0;
    for ($i = 0; $i < $ah_count - 1; $i++) {
        $atr_sum += $atr_hist[$i];
    }
    $avg_atr = $atr_sum / max(1, $ah_count - 1);

    // ATR spike: current > 1.5x average
    if ($avg_atr == 0 || $cur_atr < $avg_atr * 1.5) return null;

    // Price moving up: last close > previous close
    $last_close = $closes[$n - 1];
    $prev_close = $closes[$n - 2];
    $moving_up = ($last_close > $prev_close);

    if (!$moving_up) return null;

    $atr_ratio = $cur_atr / $avg_atr;
    $strength = min(100, (int)($atr_ratio * 30 + 20));

    // Regime gate — suppress volatility breakout BUY in bear
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($regime === 'bear') return null;

    $tp   = 3.0;
    $sl   = 2.0;
    $hold = 16;

    $lp = _ls_get_learned_params($conn, 'Volatility Breakout', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Volatility Breakout',
        'signal_type'     => 'BUY',
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'    => 'ATR spike at ' . round($atr_ratio, 1) . 'x avg with upward movement',
            'cur_atr'   => round($cur_atr, 6),
            'avg_atr'   => round($avg_atr, 6),
            'atr_ratio' => round($atr_ratio, 2)
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 9: Trend Sniper — Multi-Indicator Confluence + Regime Gate
//  Science: Brock, Lakonishok & LeBaron 1992 (4+ indicators = 58-65% WR)
//           Moskowitz, Ooi, Pedersen 2012 (Time Series Momentum)
//           STOCKSUNIFY2 RAR (Regime-Aware Reversion)
// ────────────────────────────────────────────────────────────

function _ls_algo_trend_sniper($candles, $price, $symbol, $asset) {
    global $conn;
    $closes  = _ls_extract_closes($candles);
    $highs   = _ls_extract_highs($candles);
    $lows    = _ls_extract_lows($candles);
    $volumes = _ls_extract_volumes($candles);
    $n = count($closes);
    if ($n < 34) return null;

    // ── Regime Gate ──
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);

    // 6 sub-indicators, each scores -100 to +100
    $scores = array();
    $weights = array(0.20, 0.25, 0.25, 0.15, 0.10, 0.05);

    // 1. RSI Momentum (20%)
    $rsi = _ls_calc_rsi($closes, 14);
    if ($rsi === null) return null;
    if ($rsi > 50) {
        $scores[] = min(100, ($rsi - 50) * 2);
    } else {
        $scores[] = max(-100, ($rsi - 50) * 2);
    }

    // 2. MACD Histogram (25%) — asset-class independent scoring
    $macd = _ls_calc_macd($closes);
    if ($macd === null) return null;
    $hist = $macd['histogram'];
    $prev_hist = $macd['prev_histogram'];
    // Bullish crossover
    if ($prev_hist <= 0 && $hist > 0) {
        $macd_score = 90;
    } elseif ($prev_hist >= 0 && $hist < 0) {
        $macd_score = -90;
    } elseif ($hist > 0) {
        $macd_score = ($hist > $prev_hist) ? 80 : 30;
    } elseif ($hist < 0) {
        $macd_score = ($hist > $prev_hist) ? -10 : -80;
    } else {
        $macd_score = 0;
    }
    $scores[] = $macd_score;

    // 3. EMA Stack (25%) — price vs EMA(8) vs EMA(21)
    $ema8  = _ls_calc_ema($closes, 8);
    $ema21 = _ls_calc_ema($closes, 21);
    if (count($ema8) < $n || count($ema21) < $n) return null;
    $e8  = $ema8[$n - 1];
    $e21 = $ema21[$n - 1];
    if ($price > $e8 && $e8 > $e21) {
        $ema_score = 80;
    } elseif ($price > $e21) {
        $ema_score = 40;
    } elseif ($price < $e8 && $e8 < $e21) {
        $ema_score = -80;
    } elseif ($price < $e21) {
        $ema_score = -40;
    } else {
        $ema_score = 0;
    }
    $scores[] = $ema_score;

    // 4. Bollinger %B (15%)
    $bb = _ls_calc_bollinger($closes, 20, 2.0);
    if ($bb === null) return null;
    $bb_range = $bb['upper'] - $bb['lower'];
    if ($bb_range > 0) {
        $pct_b = ($price - $bb['lower']) / $bb_range;
    } else {
        $pct_b = 0.5;
    }
    $bb_score = ($pct_b - 0.5) * 200;
    $bb_score = max(-100, min(100, $bb_score));
    $scores[] = $bb_score;

    // 5. ATR Trend Strength (10%)
    $atr_data = _ls_calc_atr($highs, $lows, $closes, 14);
    if ($atr_data === null) return null;
    $cur_atr = $atr_data['atr'];
    $atr_hist_arr = $atr_data['history'];
    $ahc = count($atr_hist_arr);
    if ($ahc < 2) return null;
    $avg_atr = 0;
    for ($i = 0; $i < $ahc - 1; $i++) $avg_atr += $atr_hist_arr[$i];
    $avg_atr = $avg_atr / max(1, $ahc - 1);
    $atr_ratio = ($avg_atr > 0) ? $cur_atr / $avg_atr : 1;
    $price_dir = ($closes[$n - 1] > $closes[$n - 2]) ? 1 : -1;
    $atr_score = min(100, max(-100, $price_dir * ($atr_ratio - 1) * 100));
    $scores[] = $atr_score;

    // 6. Volume Confirmation (5%)
    $vol_n = count($volumes);
    if ($vol_n < 3) return null;
    $vol_lookback = min($vol_n - 1, 20);
    $vol_sum = 0;
    for ($i = $vol_n - 1 - $vol_lookback; $i < $vol_n - 1; $i++) $vol_sum += $volumes[$i];
    $vol_avg = $vol_sum / max(1, $vol_lookback);
    $vol_ratio = ($vol_avg > 0) ? $volumes[$vol_n - 1] / $vol_avg : 1;
    $vol_score = min(100, max(-100, ($vol_ratio - 1) * 100 * $price_dir));
    $scores[] = $vol_score;

    // Weighted composite score
    $composite = 0;
    $positive_count = 0;
    $negative_count = 0;
    for ($i = 0; $i < 6; $i++) {
        $composite += $scores[$i] * $weights[$i];
        if ($scores[$i] > 10) $positive_count++;
        if ($scores[$i] < -10) $negative_count++;
    }

    // Signal rules
    $signal_type = null;
    if ($composite > 45 && $positive_count >= 4) {
        if ($asset === 'CRYPTO' && $regime === 'bear') {
            // Suppress buy in crypto bear market (regime gate)
        } else {
            $signal_type = 'BUY';
        }
    } elseif ($composite < -45 && $negative_count >= 4) {
        $signal_type = 'SHORT';
    }

    if ($signal_type === null) return null;

    $strength = min(100, (int)(abs($composite)));

    // TP/SL by asset class
    if ($asset === 'CRYPTO') {
        $tp = 1.5; $sl = 0.75; $hold = 8;
    } elseif ($asset === 'FOREX') {
        $tp = 0.4; $sl = 0.2; $hold = 8;
    } else {
        $tp = 1.0; $sl = 0.5; $hold = 8;
    }

    $lp = _ls_get_learned_params($conn, 'Trend Sniper', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Trend Sniper',
        'signal_type'     => $signal_type,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'        => 'Trend Sniper: ' . round($composite, 1) . ' composite (' . $positive_count . '/6 bullish) regime=' . $regime,
            'composite'     => round($composite, 1),
            'regime'        => $regime,
            'bullish_count' => $positive_count,
            'bearish_count' => $negative_count,
            'rsi_score'     => round($scores[0], 1),
            'macd_score'    => round($scores[1], 1),
            'ema_score'     => round($scores[2], 1),
            'bb_score'      => round($scores[3], 1),
            'atr_score'     => round($scores[4], 1),
            'vol_score'     => round($scores[5], 1),
            'rsi_val'       => round($rsi, 1)
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 10: Dip Recovery — Multi-Candle Reversal Detector
//  Science: Short-term mean reversion (Lo, Mamaysky & Wang 2000)
//  Catches 2-4% gradual dips followed by green reversal candle
// ────────────────────────────────────────────────────────────

function _ls_algo_dip_recovery($candles, $price, $symbol, $asset) {
    global $conn;
    $n = count($candles);
    if ($n < 5) return null;

    $closes = _ls_extract_closes($candles);
    $volumes = _ls_extract_volumes($candles);

    // Thresholds by asset class
    if ($asset === 'FOREX') {
        $dip_threshold = 0.5;
        $reversal_min = 0.1;
    } else {
        $dip_threshold = 2.0;
        $reversal_min = 0.5;
    }

    $best_dip = null;
    $best_lookback = 0;

    // Scan 2, 3, and 4-candle lookbacks for cumulative dip
    $lookbacks = array(2, 3, 4);
    foreach ($lookbacks as $lookback) {
        if ($n < $lookback + 1) continue;

        $start_price = $closes[$n - 1 - $lookback];
        $low_price = $closes[$n - 2];

        if ($start_price <= 0) continue;

        $cumul_drop = (($low_price - $start_price) / $start_price) * 100;

        if ($cumul_drop <= -$dip_threshold) {
            if ($best_dip === null || $cumul_drop < $best_dip) {
                $best_dip = $cumul_drop;
                $best_lookback = $lookback;
            }
        }
    }

    if ($best_dip === null) return null;

    // Current candle must be green and close > previous close
    $last = $candles[$n - 1];
    if ((float)$last['close'] <= (float)$last['open']) return null;
    if ($closes[$n - 1] <= $closes[$n - 2]) return null;

    // Reversal candle must be meaningful
    $open_last = (float)$last['open'];
    if ($open_last <= 0) return null;
    $reversal_pct = (($closes[$n - 1] - $open_last) / $open_last) * 100;
    if ($reversal_pct < $reversal_min) return null;

    // Volume bonus
    $vol_bonus = 0;
    $vn = count($volumes);
    if ($vn >= 5) {
        $vol_avg = 0;
        for ($i = $vn - 5; $i < $vn - 1; $i++) $vol_avg += $volumes[$i];
        $vol_avg = $vol_avg / 4;
        if ($vol_avg > 0 && $volumes[$vn - 1] > $vol_avg * 1.2) {
            $vol_bonus = 15;
        }
    }

    $strength = min(100, (int)(abs($best_dip) * 10 + $reversal_pct * 10 + $vol_bonus));
    if ($strength < 25) $strength = 25;

    // Regime gate — suppress dip recovery BUY in bear (falling knife)
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($regime === 'bear') return null;

    if ($asset === 'CRYPTO') {
        $tp = 2.5; $sl = 1.5; $hold = 16;
    } elseif ($asset === 'FOREX') {
        $tp = 0.6; $sl = 0.4; $hold = 16;
    } else {
        $tp = 1.5; $sl = 1.0; $hold = 16;
    }

    $lp = _ls_get_learned_params($conn, 'Dip Recovery', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Dip Recovery',
        'signal_type'     => 'BUY',
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'        => 'Dip Recovery: ' . round($best_dip, 2) . '% dip over ' . $best_lookback . ' candles, reversal +' . round($reversal_pct, 2) . '%',
            'cumul_dip_pct' => round($best_dip, 2),
            'lookback'      => $best_lookback,
            'reversal_pct'  => round($reversal_pct, 2),
            'vol_bonus'     => $vol_bonus
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 11: Volume Spike — Whale/Institutional Detection
//  Science: Trading Volume Alpha (NBER 2024) + STOCKSUNIFY2 Institutional Footprint
//  Volume Z-Score > 2.0 with clear directional candle
// ────────────────────────────────────────────────────────────

function _ls_algo_volume_spike($candles, $price, $symbol, $asset) {
    global $conn;
    $volumes = _ls_extract_volumes($candles);
    $closes = _ls_extract_closes($candles);
    $n = count($candles);
    if ($n < 5) return null;

    $zscore = _ls_calc_volume_zscore($volumes);
    if ($zscore === null || $zscore < 2.0) return null;

    // Candle direction must be clear (> 0.3% move)
    $last = $candles[$n - 1];
    $open_val = (float)$last['open'];
    if ($open_val <= 0) return null;
    $change_pct = (($closes[$n - 1] - $open_val) / $open_val) * 100;

    if (abs($change_pct) < 0.3) return null;

    $signal_type = ($change_pct > 0) ? 'BUY' : 'SHORT';
    $strength = min(100, (int)($zscore * 25));

    // Regime gate — suppress counter-regime volume signals
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($signal_type === 'BUY' && $regime === 'bear') return null;
    if ($signal_type === 'SHORT' && $regime === 'bull') return null;

    if ($asset === 'CRYPTO') {
        $tp = 2.0; $sl = 1.0; $hold = 12;
    } elseif ($asset === 'FOREX') {
        $tp = 0.5; $sl = 0.3; $hold = 12;
    } else {
        $tp = 1.5; $sl = 0.8; $hold = 12;
    }

    $lp = _ls_get_learned_params($conn, 'Volume Spike', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Volume Spike',
        'signal_type'     => $signal_type,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'     => 'Volume Spike: Z-Score ' . round($zscore, 2) . ' with ' . round($change_pct, 2) . '% candle move',
            'zscore'     => round($zscore, 2),
            'change_pct' => round($change_pct, 2),
            'direction'  => $signal_type
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 12: VAM — Volatility-Adjusted Momentum (Martin Ratio)
//  Science: Moskowitz, Ooi, Pedersen 2012 (Time Series Momentum)
//           STOCKSUNIFY2 VAM (Return / Ulcer Index)
//  Smooth uptrends score high, volatile pumps score low
// ────────────────────────────────────────────────────────────

function _ls_algo_vam($candles, $price, $symbol, $asset) {
    global $conn;
    $closes = _ls_extract_closes($candles);
    $n = count($closes);
    if ($n < 13) return null;

    // 12-candle momentum
    $momentum = (($closes[$n - 1] - $closes[$n - 13]) / $closes[$n - 13]) * 100;

    // Ulcer Index over 12 candles
    $ulcer = _ls_calc_ulcer_index($closes, 12);
    if ($ulcer === null || $ulcer < 0.01) return null;

    // Martin Ratio = momentum / Ulcer Index
    $martin = $momentum / $ulcer;

    if (abs($martin) < 2.0) return null;

    $signal_type = ($martin > 0) ? 'BUY' : 'SHORT';
    $strength = min(100, (int)(abs($martin) * 20));

    // Regime gate — suppress counter-regime VAM signals
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($signal_type === 'BUY' && $regime === 'bear') return null;
    if ($signal_type === 'SHORT' && $regime === 'bull') return null;

    if ($asset === 'CRYPTO') {
        $tp = 2.0; $sl = 1.0; $hold = 12;
    } elseif ($asset === 'FOREX') {
        $tp = 0.4; $sl = 0.2; $hold = 12;
    } else {
        $tp = 1.2; $sl = 0.6; $hold = 12;
    }

    $lp = _ls_get_learned_params($conn, 'VAM', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'VAM',
        'signal_type'     => $signal_type,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'       => 'VAM: Martin Ratio ' . round($martin, 2) . ' (momentum ' . round($momentum, 2) . '% / Ulcer ' . round($ulcer, 2) . ')',
            'martin_ratio' => round($martin, 2),
            'momentum_pct' => round($momentum, 2),
            'ulcer_index'  => round($ulcer, 2)
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  ALGORITHM 13: Mean Reversion Sniper
//  Science: Short-term reversals (academic consensus)
//           Bollinger + RSI + MACD convergence at oversold
//  Catches oversold bounces RSI Reversal misses (RSI<35 not <30)
// ────────────────────────────────────────────────────────────

function _ls_algo_mean_reversion_sniper($candles, $price, $symbol, $asset) {
    global $conn;
    $closes = _ls_extract_closes($candles);
    $n = count($closes);
    if ($n < 34) return null;

    // 1. Bollinger %B < 0.15 (near/below lower band)
    $bb = _ls_calc_bollinger($closes, 20, 2.0);
    if ($bb === null) return null;
    $bb_range = $bb['upper'] - $bb['lower'];
    if ($bb_range <= 0) return null;
    $pct_b = ($price - $bb['lower']) / $bb_range;
    if ($pct_b >= 0.15) return null;

    // 2. RSI < 35 (approaching oversold, not extreme)
    $rsi = _ls_calc_rsi($closes, 14);
    if ($rsi === null) return null;
    if ($rsi >= 35) return null;

    // 3. MACD histogram turning up (momentum shifting)
    $macd = _ls_calc_macd($closes);
    if ($macd === null) return null;
    if ($macd['histogram'] <= $macd['prev_histogram']) return null;

    // All 3 conditions met — mean reversion BUY
    $strength = min(100, (int)((35 - $rsi) * 3 + (0.15 - $pct_b) * 200));
    if ($strength < 25) $strength = 25;

    // Regime gate — suppress mean reversion BUY in bear (falling knife)
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($regime === 'bear') return null;

    // TP targets middle Bollinger band
    $tp_from_bb = (($bb['middle'] - $price) / $price) * 100;
    if ($tp_from_bb < 0.3) $tp_from_bb = 0.3;

    if ($asset === 'CRYPTO') {
        $tp = min(3.0, max(0.5, $tp_from_bb));
        $sl = 1.0; $hold = 12;
    } elseif ($asset === 'FOREX') {
        $tp = min(0.8, max(0.15, $tp_from_bb));
        $sl = 0.3; $hold = 12;
    } else {
        $tp = min(2.0, max(0.3, $tp_from_bb));
        $sl = 0.7; $hold = 12;
    }

    $lp = _ls_get_learned_params($conn, 'Mean Reversion Sniper', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Mean Reversion Sniper',
        'signal_type'     => 'BUY',
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'         => 'Mean Reversion: %B=' . round($pct_b, 3) . ', RSI=' . round($rsi, 1) . ', MACD histogram turning up',
            'pct_b'          => round($pct_b, 3),
            'rsi'            => round($rsi, 1),
            'histogram'      => round($macd['histogram'], 6),
            'prev_histogram' => round($macd['prev_histogram'], 6),
            'target_middle'  => round($bb['middle'], 4),
            'tp_dynamic_pct' => round($tp_from_bb, 2)
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  Algorithm #14: ADX Trend Strength
//  Science: STOCKSUNIFY2 Alpha Predator — ADX(14) > 25 = strong trend
//  +DI > -DI = bullish, -DI > +DI = bearish. ADX measures trend strength.
// ────────────────────────────────────────────────────────────

function _ls_algo_adx_trend($candles, $price, $symbol, $asset) {
    $closes = _ls_extract_closes($candles);
    $highs  = _ls_extract_highs($candles);
    $lows   = _ls_extract_lows($candles);
    $n = count($closes);
    if ($n < 20) return null;

    $adx_data = _ls_calc_adx($highs, $lows, $closes, 14);
    if ($adx_data === null) return null;

    $adx = $adx_data['adx'];
    $plus_di = $adx_data['plus_di'];
    $minus_di = $adx_data['minus_di'];

    // ADX must be above 20 (moderate-to-strong trend, per academic optimal)
    if ($adx < 20) return null;

    // DI spread must be meaningful (> 5 points)
    $di_spread = abs($plus_di - $minus_di);
    if ($di_spread < 5) return null;

    // Direction from DI
    $direction = ($plus_di > $minus_di) ? 'BUY' : 'SHORT';

    // Strength: higher ADX + wider DI spread = stronger
    $strength = min(100, (int)(($adx - 20) * 2 + $di_spread));

    // Regime gate — suppress counter-regime ADX signals
    global $conn;
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($direction === 'BUY' && $regime === 'bear') return null;
    if ($direction === 'SHORT' && $regime === 'bull') return null;

    // Asset-class TP/SL
    $tp = 1.5; $sl = 0.75; $hold = 12;
    if ($asset === 'FOREX') { $tp = 0.4; $sl = 0.2; $hold = 12; }
    if ($asset === 'STOCK') { $tp = 1.0; $sl = 0.5; $hold = 12; }

    // Check learned params
    global $conn;
    $learned = _ls_get_learned_params($conn, 'ADX Trend Strength', $asset);
    if ($learned) {
        $tp = (float)$learned['best_tp_pct'];
        $sl = (float)$learned['best_sl_pct'];
        $hold = (int)$learned['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'ADX Trend Strength',
        'signal_type'     => $direction,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'   => 'ADX(' . round($adx, 1) . ') > 25 = strong trend. +DI=' . round($plus_di, 1) . ' -DI=' . round($minus_di, 1) . ' spread=' . round($di_spread, 1),
            'adx'      => round($adx, 1),
            'plus_di'  => round($plus_di, 1),
            'minus_di' => round($minus_di, 1),
            'di_spread' => round($di_spread, 1),
            'source'   => 'STOCKSUNIFY2 Alpha Predator (Wilder ADX)'
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  Algorithm #15: Stochastic RSI Crossover
//  Science: StochRSI(14,14,3,3) K/D crossover at oversold/overbought
//  Combines momentum (RSI) with mean reversion (Stochastic) for better timing
// ────────────────────────────────────────────────────────────

function _ls_algo_stoch_rsi_cross($candles, $price, $symbol, $asset) {
    $closes = _ls_extract_closes($candles);
    $n = count($closes);
    if ($n < 30) return null;

    $stoch = _ls_calc_stoch_rsi($closes, 14, 14, 3, 3);
    if ($stoch === null) return null;

    $k = $stoch['k'];
    $d = $stoch['d'];
    $prev_k = $stoch['prev_k'];
    $prev_d = $stoch['prev_d'];

    $signal = null;

    // Bullish crossover: K crosses above D in oversold zone (< 20)
    if ($prev_k <= $prev_d && $k > $d && $k < 30) {
        $signal = 'BUY';
    }
    // Bearish crossover: K crosses below D in overbought zone (> 80)
    if ($prev_k >= $prev_d && $k < $d && $k > 70) {
        $signal = 'SHORT';
    }

    if ($signal === null) return null;

    // Strength based on how extreme the zone is
    if ($signal === 'BUY') {
        $strength = min(100, (int)((30 - $k) * 3 + abs($k - $d) * 5));
    } else {
        $strength = min(100, (int)(($k - 70) * 3 + abs($k - $d) * 5));
    }
    $strength = max(30, $strength);

    // Regime gate — suppress counter-regime StochRSI signals
    global $conn;
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($signal === 'BUY' && $regime === 'bear') return null;
    if ($signal === 'SHORT' && $regime === 'bull') return null;

    // Asset-class TP/SL
    $tp = 2.0; $sl = 1.0; $hold = 12;
    if ($asset === 'FOREX') { $tp = 0.5; $sl = 0.25; $hold = 12; }
    if ($asset === 'STOCK') { $tp = 1.2; $sl = 0.6; $hold = 12; }

    $learned = _ls_get_learned_params($conn, 'StochRSI Crossover', $asset);
    if ($learned) {
        $tp = (float)$learned['best_tp_pct'];
        $sl = (float)$learned['best_sl_pct'];
        $hold = (int)$learned['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'StochRSI Crossover',
        'signal_type'     => $signal,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'  => 'StochRSI K(' . round($k, 1) . ') crossed ' . ($signal === 'BUY' ? 'above' : 'below') . ' D(' . round($d, 1) . ') in ' . ($signal === 'BUY' ? 'oversold' : 'overbought') . ' zone',
            'k'       => round($k, 1),
            'd'       => round($d, 1),
            'prev_k'  => round($prev_k, 1),
            'prev_d'  => round($prev_d, 1),
            'source'  => 'StochRSI momentum+mean-reversion hybrid'
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  Algorithm #16: Awesome Oscillator Zero-Line Cross
//  Science: Bill Williams AO, used in STOCKSUNIFY2 — momentum shift detection
//  AO = SMA(5,median) - SMA(34,median). Zero-line cross = momentum shift.
// ────────────────────────────────────────────────────────────

function _ls_algo_awesome_osc($candles, $price, $symbol, $asset) {
    $highs = _ls_extract_highs($candles);
    $lows  = _ls_extract_lows($candles);
    $n = count($highs);
    if ($n < 36) return null;

    $ao_data = _ls_calc_awesome_oscillator($highs, $lows);
    if ($ao_data === null) return null;

    $ao = $ao_data['ao'];
    $prev_ao = $ao_data['prev_ao'];

    $signal = null;

    // Bullish: AO crosses from negative to positive (zero-line cross up)
    if ($prev_ao <= 0 && $ao > 0) {
        $signal = 'BUY';
    }
    // Bearish: AO crosses from positive to negative
    if ($prev_ao >= 0 && $ao < 0) {
        $signal = 'SHORT';
    }

    if ($signal === null) return null;

    // Strength: magnitude of AO relative to price (percentage)
    $ao_pct = abs($ao / $price) * 100;
    $strength = min(100, max(30, (int)($ao_pct * 500)));

    // Regime gate — suppress counter-regime AO signals
    global $conn;
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($signal === 'BUY' && $regime === 'bear') return null;
    if ($signal === 'SHORT' && $regime === 'bull') return null;

    // Confirmation gate — AO demoted to confirmation-only (weak standalone per academic research)
    // Require RSI(14) directional agreement to filter false zero-line crosses
    $closes_conf = _ls_extract_closes($candles);
    $rsi_conf = _ls_calc_rsi($closes_conf, 14);
    if ($rsi_conf !== null) {
        if ($signal === 'BUY' && $rsi_conf < 45) return null;
        if ($signal === 'SHORT' && $rsi_conf > 55) return null;
    }

    // Asset-class TP/SL
    $tp = 1.8; $sl = 0.9; $hold = 12;
    if ($asset === 'FOREX') { $tp = 0.4; $sl = 0.2; $hold = 12; }
    if ($asset === 'STOCK') { $tp = 1.0; $sl = 0.5; $hold = 12; }

    $learned = _ls_get_learned_params($conn, 'Awesome Oscillator', $asset);
    if ($learned) {
        $tp = (float)$learned['best_tp_pct'];
        $sl = (float)$learned['best_sl_pct'];
        $hold = (int)$learned['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Awesome Oscillator',
        'signal_type'     => $signal,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'  => 'AO zero-line cross: prev=' . round($prev_ao, 4) . ' now=' . round($ao, 4) . ' (' . $signal . ' momentum shift)',
            'ao'      => round($ao, 6),
            'prev_ao' => round($prev_ao, 6),
            'ao_pct'  => round($ao_pct, 4),
            'source'  => 'STOCKSUNIFY2 Awesome Oscillator (Bill Williams)'
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  Algorithm #17: RSI(2) Scalp — ultra-short-term mean reversion
//  Science: STOCKSUNIFY2 mean reversion — RSI(2) < 10 oversold, > 90 overbought
//  With SMA(20) trend filter: only buy in uptrend, short in downtrend
// ────────────────────────────────────────────────────────────

function _ls_algo_rsi2_scalp($candles, $price, $symbol, $asset) {
    $closes = _ls_extract_closes($candles);
    $n = count($closes);
    if ($n < 22) return null;

    // RSI(2) — ultra-short period
    $rsi2 = _ls_calc_rsi($closes, 2);
    if ($rsi2 === null) return null;

    // SMA(20) trend filter
    $sma20_slice = array_slice($closes, $n - 20, 20);
    $sma20 = array_sum($sma20_slice) / 20;

    $signal = null;

    // RSI(2) < 10 AND price above SMA(20) = oversold in uptrend = BUY
    if ($rsi2 < 10 && $price > $sma20) {
        $signal = 'BUY';
    }
    // RSI(2) > 90 AND price below SMA(20) = overbought in downtrend = SHORT
    if ($rsi2 > 90 && $price < $sma20) {
        $signal = 'SHORT';
    }

    if ($signal === null) return null;

    // Strength: more extreme RSI = stronger
    if ($signal === 'BUY') {
        $strength = min(100, (int)((10 - $rsi2) * 10));
    } else {
        $strength = min(100, (int)(($rsi2 - 90) * 10));
    }
    $strength = max(30, $strength);

    // Regime gate — suppress BUY in bear (mean-reversion falling knife risk)
    global $conn;
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($signal === 'BUY' && $regime === 'bear') return null;

    // Shorter hold for scalp trades
    $tp = 1.2; $sl = 0.6; $hold = 6;
    if ($asset === 'FOREX') { $tp = 0.3; $sl = 0.15; $hold = 6; }
    if ($asset === 'STOCK') { $tp = 0.8; $sl = 0.4; $hold = 6; }

    $learned = _ls_get_learned_params($conn, 'RSI(2) Scalp', $asset);
    if ($learned) {
        $tp = (float)$learned['best_tp_pct'];
        $sl = (float)$learned['best_sl_pct'];
        $hold = (int)$learned['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'RSI(2) Scalp',
        'signal_type'     => $signal,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'   => 'RSI(2)=' . round($rsi2, 1) . ($signal === 'BUY' ? ' < 10 oversold' : ' > 90 overbought') . ' + price ' . ($price > $sma20 ? 'above' : 'below') . ' SMA(20)=' . round($sma20, 4),
            'rsi2'     => round($rsi2, 1),
            'sma20'    => round($sma20, 4),
            'price_vs_sma' => round(($price - $sma20) / $sma20 * 100, 2),
            'source'   => 'STOCKSUNIFY2 ultra-short mean reversion'
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  Algorithm #18: Ichimoku Cloud — Tenkan/Kijun cross + cloud position
//  Science: Ichimoku Kinko Hyo — complete trend + momentum system
//  Adapted for hourly: Tenkan(9), Kijun(26), Senkou B(26)
// ────────────────────────────────────────────────────────────

function _ls_algo_ichimoku_cloud($candles, $price, $symbol, $asset) {
    $highs  = _ls_extract_highs($candles);
    $lows   = _ls_extract_lows($candles);
    $closes = _ls_extract_closes($candles);
    $n = count($closes);
    if ($n < 28) return null;

    $ichi = _ls_calc_ichimoku($highs, $lows, 9, 26, 26);
    if ($ichi === null) return null;

    $tenkan = $ichi['tenkan'];
    $kijun = $ichi['kijun'];
    $prev_tenkan = $ichi['prev_tenkan'];
    $prev_kijun = $ichi['prev_kijun'];
    $cloud_top = $ichi['cloud_top'];
    $cloud_bottom = $ichi['cloud_bottom'];

    $signal = null;
    $factors = 0;

    // Factor 1: Tenkan/Kijun crossover
    $tk_cross_up = ($prev_tenkan <= $prev_kijun && $tenkan > $kijun);
    $tk_cross_down = ($prev_tenkan >= $prev_kijun && $tenkan < $kijun);

    // Factor 2: Price position relative to cloud
    $price_above_cloud = ($price > $cloud_top);
    $price_below_cloud = ($price < $cloud_bottom);

    // Factor 3: Tenkan above/below Kijun (trend direction)
    $tenkan_above = ($tenkan > $kijun);

    // Bullish: TK cross up OR (price above cloud AND Tenkan above Kijun)
    if ($tk_cross_up && $price_above_cloud) {
        $signal = 'BUY';
        $factors = 3; // cross + cloud + alignment
    } elseif ($tk_cross_up && $price > $cloud_bottom) {
        $signal = 'BUY';
        $factors = 2; // cross + partial cloud
    } elseif ($price_above_cloud && $tenkan_above && ($tenkan - $kijun) / $price * 100 > 0.1) {
        $signal = 'BUY';
        $factors = 2; // cloud + separation
    }

    // Bearish: TK cross down OR (price below cloud AND Tenkan below Kijun)
    if ($signal === null) {
        if ($tk_cross_down && $price_below_cloud) {
            $signal = 'SHORT';
            $factors = 3;
        } elseif ($tk_cross_down && $price < $cloud_top) {
            $signal = 'SHORT';
            $factors = 2;
        } elseif ($price_below_cloud && !$tenkan_above && ($kijun - $tenkan) / $price * 100 > 0.1) {
            $signal = 'SHORT';
            $factors = 2;
        }
    }

    if ($signal === null) return null;

    // Strength based on factor count and cloud distance
    $cloud_dist_pct = 0;
    if ($signal === 'BUY') {
        $cloud_dist_pct = ($price - $cloud_top) / $price * 100;
    } else {
        $cloud_dist_pct = ($cloud_bottom - $price) / $price * 100;
    }
    $strength = min(100, max(30, (int)($factors * 25 + $cloud_dist_pct * 10)));

    // Regime gate — suppress counter-regime Ichimoku signals
    global $conn;
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($signal === 'BUY' && $regime === 'bear') return null;
    if ($signal === 'SHORT' && $regime === 'bull') return null;

    // Confirmation gate — Ichimoku demoted (underperforms buy-and-hold 90% of time per research)
    // Require ADX > 20 (trending market) to filter signals in choppy conditions
    $adx_conf = _ls_calc_adx($highs, $lows, $closes, 14);
    if ($adx_conf === null || $adx_conf['adx'] < 20) return null;

    // TP/SL
    $tp = 2.0; $sl = 1.0; $hold = 16;
    if ($asset === 'FOREX') { $tp = 0.5; $sl = 0.25; $hold = 16; }
    if ($asset === 'STOCK') { $tp = 1.2; $sl = 0.6; $hold = 16; }

    $learned = _ls_get_learned_params($conn, 'Ichimoku Cloud', $asset);
    if ($learned) {
        $tp = (float)$learned['best_tp_pct'];
        $sl = (float)$learned['best_sl_pct'];
        $hold = (int)$learned['best_hold_hours'];
    }

    $reason_parts = array();
    if ($tk_cross_up) $reason_parts[] = 'TK bullish cross';
    if ($tk_cross_down) $reason_parts[] = 'TK bearish cross';
    if ($price_above_cloud) $reason_parts[] = 'price above cloud';
    if ($price_below_cloud) $reason_parts[] = 'price below cloud';
    if ($tenkan_above && $signal === 'BUY') $reason_parts[] = 'Tenkan > Kijun';
    if (!$tenkan_above && $signal === 'SHORT') $reason_parts[] = 'Kijun > Tenkan';

    return array(
        'algorithm_name'  => 'Ichimoku Cloud',
        'signal_type'     => $signal,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'       => implode(' + ', $reason_parts) . '. T=' . round($tenkan, 4) . ' K=' . round($kijun, 4) . ' Cloud=' . round($cloud_bottom, 4) . '-' . round($cloud_top, 4),
            'tenkan'       => round($tenkan, 4),
            'kijun'        => round($kijun, 4),
            'cloud_top'    => round($cloud_top, 4),
            'cloud_bottom' => round($cloud_bottom, 4),
            'factors'      => $factors,
            'source'       => 'Ichimoku Kinko Hyo (adapted for hourly)'
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  Algorithm #19: Alpha Predator — 4-factor alignment from STOCKSUNIFY2
//  Science: ADX > 25 + RSI 40-70 (healthy trend zone) + AO > 0 + Volume > 1.2x avg
//  All 4 must pass simultaneously for high-conviction signal
// ────────────────────────────────────────────────────────────

function _ls_algo_alpha_predator($candles, $price, $symbol, $asset) {
    $closes  = _ls_extract_closes($candles);
    $highs   = _ls_extract_highs($candles);
    $lows    = _ls_extract_lows($candles);
    $volumes = _ls_extract_volumes($candles);
    $n = count($closes);
    if ($n < 36) return null;

    // Factor 1: ADX > 25 (strong trend)
    $adx_data = _ls_calc_adx($highs, $lows, $closes, 14);
    if ($adx_data === null) return null;
    $adx = $adx_data['adx'];
    $plus_di = $adx_data['plus_di'];
    $minus_di = $adx_data['minus_di'];
    if ($adx < 20) return null;

    // Factor 2: RSI(14) in healthy trend zone (40-70 for BUY, 30-60 for SHORT)
    $rsi = _ls_calc_rsi($closes, 14);
    if ($rsi === null) return null;

    // Factor 3: Awesome Oscillator confirms momentum direction
    $ao_data = _ls_calc_awesome_oscillator($highs, $lows);
    if ($ao_data === null) return null;
    $ao = $ao_data['ao'];

    // Factor 4: Volume > 1.2x 20-candle average
    $vol_count = count($volumes);
    $vol_lookback = min($vol_count - 1, 20);
    $vol_sum = 0;
    for ($i = $vol_count - 1 - $vol_lookback; $i < $vol_count - 1; $i++) {
        $vol_sum += $volumes[$i];
    }
    $vol_avg = ($vol_lookback > 0) ? $vol_sum / $vol_lookback : 0;
    $vol_ratio = ($vol_avg > 0) ? $volumes[$vol_count - 1] / $vol_avg : 0;

    $signal = null;
    $factors_passed = 0;
    $factor_details = array();

    // Bullish: ADX>25 + +DI>-DI + RSI 40-70 + AO>0 + Vol>1.2x
    if ($plus_di > $minus_di) {
        $factors_passed++;
        $factor_details[] = '+DI>' . round($plus_di, 1) . '>-DI' . round($minus_di, 1);
    }
    if ($rsi >= 40 && $rsi <= 70) {
        $factors_passed++;
        $factor_details[] = 'RSI=' . round($rsi, 1) . ' healthy';
    }
    if ($ao > 0) {
        $factors_passed++;
        $factor_details[] = 'AO=' . round($ao, 4) . '>0';
    }
    if ($vol_ratio > 1.2) {
        $factors_passed++;
        $factor_details[] = 'Vol=' . round($vol_ratio, 1) . 'x avg';
    }

    if ($factors_passed >= 4 && $plus_di > $minus_di) {
        $signal = 'BUY';
    }

    // Bearish: ADX>25 + -DI>+DI + RSI 30-60 + AO<0 + Vol>1.2x
    if ($signal === null) {
        $factors_passed = 0;
        $factor_details = array();

        if ($minus_di > $plus_di) {
            $factors_passed++;
            $factor_details[] = '-DI>' . round($minus_di, 1) . '>+DI' . round($plus_di, 1);
        }
        if ($rsi >= 30 && $rsi <= 60) {
            $factors_passed++;
            $factor_details[] = 'RSI=' . round($rsi, 1) . ' healthy';
        }
        if ($ao < 0) {
            $factors_passed++;
            $factor_details[] = 'AO=' . round($ao, 4) . '<0';
        }
        if ($vol_ratio > 1.2) {
            $factors_passed++;
            $factor_details[] = 'Vol=' . round($vol_ratio, 1) . 'x avg';
        }

        if ($factors_passed >= 4 && $minus_di > $plus_di) {
            $signal = 'SHORT';
        }
    }

    if ($signal === null) return null;

    // High conviction — all 4 factors aligned
    $strength = min(100, max(60, (int)($adx * 1.5 + $factors_passed * 10)));

    // Regime gate — suppress counter-regime Alpha Predator signals
    global $conn;
    $regime = _ls_get_regime($conn, $asset, $candles, $symbol);
    if ($signal === 'BUY' && $regime === 'bear') return null;
    if ($signal === 'SHORT' && $regime === 'bull') return null;

    // TP/SL: tighter for high-conviction
    $tp = 2.0; $sl = 1.0; $hold = 12;
    if ($asset === 'FOREX') { $tp = 0.5; $sl = 0.25; $hold = 12; }
    if ($asset === 'STOCK') { $tp = 1.2; $sl = 0.6; $hold = 12; }

    $learned = _ls_get_learned_params($conn, 'Alpha Predator', $asset);
    if ($learned) {
        $tp = (float)$learned['best_tp_pct'];
        $sl = (float)$learned['best_sl_pct'];
        $hold = (int)$learned['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Alpha Predator',
        'signal_type'     => $signal,
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'    => 'All 4 factors aligned: ' . implode(', ', $factor_details) . '. ADX=' . round($adx, 1),
            'adx'       => round($adx, 1),
            'rsi'       => round($rsi, 1),
            'ao'        => round($ao, 6),
            'vol_ratio' => round($vol_ratio, 2),
            'factors'   => $factors_passed,
            'source'    => 'STOCKSUNIFY2 Alpha Predator (4-factor alignment)'
        ))
    );
}

// ────────────────────────────────────────────────────────────
//  Signal dedup check
// ────────────────────────────────────────────────────────────

function _ls_signal_exists($conn, $symbol, $algo_name) {
    $safe_sym  = $conn->real_escape_string($symbol);
    $safe_algo = $conn->real_escape_string($algo_name);
    $res = $conn->query("SELECT id FROM lm_signals WHERE symbol='$safe_sym' AND algorithm_name='$safe_algo' AND status='active'");
    if ($res && $res->num_rows > 0) return true;
    return false;
}

// ────────────────────────────────────────────────────────────
//  Insert a signal
// ────────────────────────────────────────────────────────────

function _ls_insert_signal($conn, $asset_class, $symbol, $price, $sig) {
    $now = date('Y-m-d H:i:s');
    $expires = date('Y-m-d H:i:s', time() + 1800); // +30 minutes

    $safe_asset  = $conn->real_escape_string($asset_class);
    $safe_sym    = $conn->real_escape_string($symbol);
    $safe_algo   = $conn->real_escape_string($sig['algorithm_name']);
    $safe_type   = $conn->real_escape_string($sig['signal_type']);
    $strength    = (int)$sig['signal_strength'];
    $entry       = $conn->real_escape_string((string)$price);
    $tp          = $conn->real_escape_string((string)$sig['target_tp_pct']);
    $sl          = $conn->real_escape_string((string)$sig['target_sl_pct']);
    $hold        = (int)$sig['max_hold_hours'];
    $tf          = $conn->real_escape_string($sig['timeframe']);
    $rationale   = $conn->real_escape_string($sig['rationale']);

    // ── Determine param_source: learned vs original ──
    $orig = _ls_get_original_defaults($sig['algorithm_name'], $asset_class);
    $orig_tp   = $orig['tp'];
    $orig_sl   = $orig['sl'];
    $orig_hold = $orig['hold'];

    // If signal params differ from hardcoded defaults, self-learning overrode them
    $param_source = 'original';
    if (abs((float)$sig['target_tp_pct'] - $orig_tp) > 0.05
        || abs((float)$sig['target_sl_pct'] - $orig_sl) > 0.05
        || abs($hold - $orig_hold) > 0) {
        $param_source = 'learned';
    }

    $sql = "INSERT INTO lm_signals (asset_class, symbol, algorithm_name, signal_type, signal_strength,
                entry_price, target_tp_pct, target_sl_pct, max_hold_hours, timeframe,
                rationale, param_source, tp_original, sl_original, hold_original,
                signal_time, expires_at, status)
            VALUES ('$safe_asset', '$safe_sym', '$safe_algo', '$safe_type', $strength,
                $entry, $tp, $sl, $hold, '$tf',
                '$rationale', '$param_source', $orig_tp, $orig_sl, $orig_hold,
                '$now', '$expires', 'active')";
    $ok = $conn->query($sql);
    if (!$ok) {
        // Fallback: columns may not exist yet, insert without param tracking
        $sql = "INSERT INTO lm_signals (asset_class, symbol, algorithm_name, signal_type, signal_strength,
                    entry_price, target_tp_pct, target_sl_pct, max_hold_hours, timeframe,
                    rationale, signal_time, expires_at, status)
                VALUES ('$safe_asset', '$safe_sym', '$safe_algo', '$safe_type', $strength,
                    $entry, $tp, $sl, $hold, '$tf',
                    '$rationale', '$now', '$expires', 'active')";
        $conn->query($sql);
    }
    return $conn->insert_id;
}

// ── Hardcoded default params for each algorithm (pre-learning) ──
function _ls_get_original_defaults($algo_name, $asset_class) {
    // (Feb 2026 overhaul) Stock TP/hold targets increased — previous values
    // were too small to overcome slippage + fees, causing 67% max-hold exits
    // and avg loss 16.7x larger than avg win. Min stock TP now 1.5% (CDR $0
    // commission). Fundamental algos get longer holds. Crypto/Forex unchanged.
    $d = array(
        'Momentum Burst'        => array('CRYPTO' => array(3.0, 1.5, 8),   'FOREX' => array(1.5, 0.75, 8),  'STOCK' => array(2.0, 1.0, 16)),
        'RSI Reversal'          => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(2.0, 1.0, 12),  'STOCK' => array(2.5, 1.2, 16)),
        'Breakout 24h'          => array('CRYPTO' => array(8.0, 2.0, 16),  'FOREX' => array(8.0, 2.0, 16),  'STOCK' => array(8.0, 2.5, 24)),
        'DCA Dip'               => array('CRYPTO' => array(5.0, 3.0, 48),  'FOREX' => array(5.0, 3.0, 48),  'STOCK' => array(5.0, 3.0, 48)),
        'Bollinger Squeeze'     => array('CRYPTO' => array(2.5, 1.5, 8),   'FOREX' => array(2.5, 1.5, 8),   'STOCK' => array(3.0, 1.5, 16)),
        'MACD Crossover'        => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(2.0, 1.0, 12),  'STOCK' => array(2.5, 1.2, 16)),
        'Consensus'             => array('CRYPTO' => array(3.0, 2.0, 24),  'FOREX' => array(3.0, 2.0, 24),  'STOCK' => array(3.5, 2.0, 36)),
        'Volatility Breakout'   => array('CRYPTO' => array(3.0, 2.0, 16),  'FOREX' => array(3.0, 2.0, 16),  'STOCK' => array(3.5, 2.0, 24)),
        'Trend Sniper'          => array('CRYPTO' => array(1.5, 0.75, 8),  'FOREX' => array(0.4, 0.2, 8),   'STOCK' => array(1.5, 0.75, 12)),
        'Dip Recovery'          => array('CRYPTO' => array(2.5, 1.5, 16),  'FOREX' => array(0.6, 0.4, 16),  'STOCK' => array(2.0, 1.0, 24)),
        'Volume Spike'          => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(0.5, 0.3, 12),  'STOCK' => array(2.0, 1.0, 16)),
        'VAM'                   => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(0.4, 0.2, 12),  'STOCK' => array(1.8, 0.9, 16)),
        'Mean Reversion Sniper' => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(0.5, 0.3, 12),  'STOCK' => array(2.0, 1.0, 16)),
        'ADX Trend Strength'    => array('CRYPTO' => array(1.5, 0.75, 12), 'FOREX' => array(0.4, 0.2, 12),  'STOCK' => array(1.5, 0.75, 16)),
        'StochRSI Crossover'    => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(0.5, 0.25, 12), 'STOCK' => array(1.5, 0.75, 16)),
        'Awesome Oscillator'    => array('CRYPTO' => array(1.8, 0.9, 12),  'FOREX' => array(0.4, 0.2, 12),  'STOCK' => array(1.5, 0.75, 16)),
        'RSI(2) Scalp'          => array('CRYPTO' => array(1.2, 0.6, 6),   'FOREX' => array(0.3, 0.15, 6),  'STOCK' => array(1.5, 0.75, 8)),
        'Ichimoku Cloud'        => array('CRYPTO' => array(2.0, 1.0, 16),  'FOREX' => array(0.5, 0.25, 16), 'STOCK' => array(1.8, 0.9, 24)),
        'Alpha Predator'        => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(0.5, 0.25, 12), 'STOCK' => array(1.8, 0.9, 16)),
        'Insider Cluster Buy'   => array('STOCK' => array(10.0, 5.0, 504)),
        '13F New Position'      => array('STOCK' => array(12.0, 6.0, 720)),
        'Sentiment Divergence'  => array('STOCK' => array(4.0, 2.5, 240)),
        'Contrarian Fear/Greed' => array('CRYPTO' => array(5.0, 3.0, 168), 'FOREX' => array(2.0, 1.5, 168), 'STOCK' => array(5.0, 3.0, 504))
    );
    if (isset($d[$algo_name]) && isset($d[$algo_name][$asset_class])) {
        $v = $d[$algo_name][$asset_class];
        return array('tp' => $v[0], 'sl' => $v[1], 'hold' => $v[2]);
    }
    return array('tp' => 3.0, 'sl' => 2.0, 'hold' => 12);
}

// ────────────────────────────────────────────────────────────
//  CDR (Canadian Depositary Receipt) availability check
//  CDR stocks trade commission-free ($0) on Cboe Canada NEO Exchange.
//  Used to boost signal strength for zero-cost-to-trade stocks.
// ────────────────────────────────────────────────────────────
function _ls_is_cdr_ticker($ticker) {
    static $cdr_list = null;
    if ($cdr_list === null) {
        $cdr_list = array(
            'AAPL','AMD','AMZN','CSCO','CRM','GOOG','GOOGL','IBM','INTC','META','MSFT','NFLX','NVDA',
            'COST','DIS','HD','MCD','NKE','SBUX','TSLA','WMT',
            'ABBV','CVS','JNJ','PFE','UNH',
            'BAC','BRK.B','JPM','MA','PYPL','V',
            'BA','CVX','XOM','HON','UPS',
            'KO','VZ','UBER'
        );
    }
    $upper = strtoupper(trim($ticker));
    $base  = preg_replace('/\\.(TO|V|CN)$/', '', $upper);
    return in_array($upper, $cdr_list) || in_array($base, $cdr_list);
}

// ────────────────────────────────────────────────────────────
//  ATR-based dynamic TP/SL (Kimi recommendation)
//  Adjusts fixed TP/SL to be ATR-proportional while preserving R:R
// ────────────────────────────────────────────────────────────

function _ls_atr_adjust_tp_sl($candles, $price, $sig) {
    if ($sig === null || $price <= 0) return $sig;

    // Extract highs, lows, closes from candles
    $highs = array(); $lows = array(); $closes = array();
    foreach ($candles as $c) {
        $highs[]  = (float)$c['high'];
        $lows[]   = (float)$c['low'];
        $closes[] = (float)$c['close'];
    }

    $atr_data = _ls_calc_atr($highs, $lows, $closes, 14);
    if ($atr_data === null || $atr_data['atr'] <= 0) return $sig; // Fallback to fixed

    $atr = $atr_data['atr'];
    $atr_pct = ($atr / $price) * 100; // ATR as percentage of price

    // Preserve the original risk:reward ratio
    $orig_tp = (float)$sig['target_tp_pct'];
    $orig_sl = (float)$sig['target_sl_pct'];
    if ($orig_sl <= 0) return $sig;
    $rr_ratio = $orig_tp / $orig_sl;

    // ATR-based SL: 1.5x ATR, but bounded by 0.5x to 2x original SL
    $atr_sl = $atr_pct * 1.5;
    $min_sl = $orig_sl * 0.5;
    $max_sl = $orig_sl * 2.0;
    $new_sl = max($min_sl, min($max_sl, $atr_sl));

    // TP preserves the R:R ratio
    $new_tp = round($new_sl * $rr_ratio, 2);
    $new_sl = round($new_sl, 2);

    $sig['target_tp_pct'] = $new_tp;
    $sig['target_sl_pct'] = $new_sl;

    // Add ATR info to rationale
    $rationale = json_decode($sig['rationale'], true);
    if (!is_array($rationale)) $rationale = array();
    $rationale['atr_adjusted'] = true;
    $rationale['atr_pct']      = round($atr_pct, 3);
    $rationale['orig_tp']      = $orig_tp;
    $rationale['orig_sl']      = $orig_sl;
    $sig['rationale'] = json_encode($rationale);

    return $sig;
}


// ────────────────────────────────────────────────────────────
//  Regime-aware TP/SL scaling
//  Reduces TP targets in sideways/neutral markets so they are
//  more achievable, improving win rate in choppy conditions.
//  Bear regime signals are already suppressed by regime gate,
//  so this primarily helps sideways/neutral regimes.
// ────────────────────────────────────────────────────────────

function _ls_regime_scale_tp_sl($conn, $sig, $asset_class) {
    if ($sig === null) return $sig;

    $regime = _ls_get_regime($conn, $asset_class, array(), '');
    if ($regime === false || $regime === null) return $sig;

    // In bull market, keep targets as-is (full potential)
    if ($regime === 'bull') return $sig;

    $orig_tp = (float)$sig['target_tp_pct'];
    $orig_sl = (float)$sig['target_sl_pct'];

    // In sideways/neutral market: reduce TP by 15%, tighten SL by 10%
    // (Feb 2026 fix) Previous 35% TP cut was too aggressive — made targets
    // unachievable, causing 67% of trades to hit max hold instead of TP.
    // Moderate 15% reduction still accounts for lower volatility without
    // destroying the reward side of the R:R ratio.
    if ($regime === 'neutral' || $regime === 'sideways') {
        $sig['target_tp_pct'] = round($orig_tp * 0.85, 2);
        $sig['target_sl_pct'] = round($orig_sl * 0.90, 2);
    }
    // In bear market (for SHORT signals that pass the regime gate):
    // reduce TP by 10% (bear bounces are unpredictable)
    elseif ($regime === 'bear') {
        $sig['target_tp_pct'] = round($orig_tp * 0.90, 2);
        $sig['target_sl_pct'] = round($orig_sl * 0.95, 2);
    }

    // Ensure minimums
    if ($sig['target_tp_pct'] < 0.1) $sig['target_tp_pct'] = 0.1;
    if ($sig['target_sl_pct'] < 0.05) $sig['target_sl_pct'] = 0.05;

    // Tag rationale
    $rationale = json_decode($sig['rationale'], true);
    if (!is_array($rationale)) $rationale = array();
    $rationale['regime_scaled'] = true;
    $rationale['regime'] = $regime;
    $rationale['pre_regime_tp'] = $orig_tp;
    $rationale['pre_regime_sl'] = $orig_sl;
    $sig['rationale'] = json_encode($rationale);

    return $sig;
}

// ────────────────────────────────────────────────────────────
//  Momentum crash protection (Kimi recommendation)
//  Detects extreme volatility and blocks momentum-based algos
// ────────────────────────────────────────────────────────────

function _ls_is_volatility_extreme($candles) {
    if (count($candles) < 20) return false;

    $highs = array(); $lows = array(); $closes = array();
    foreach ($candles as $c) {
        $highs[]  = (float)$c['high'];
        $lows[]   = (float)$c['low'];
        $closes[] = (float)$c['close'];
    }

    $atr_data = _ls_calc_atr($highs, $lows, $closes, 14);
    if ($atr_data === null) return false;

    // Compare current ATR to historical average
    $hist = $atr_data['history'];
    if (count($hist) < 5) return false;

    $cur_atr = $atr_data['atr'];
    $sum = 0;
    for ($i = 0; $i < count($hist) - 1; $i++) $sum += $hist[$i];
    $avg_atr = $sum / max(1, count($hist) - 1);

    // If current ATR > 2.5x the average, volatility is extreme
    return ($avg_atr > 0 && $cur_atr > $avg_atr * 2.5);
}

// Algorithms that should be skipped during extreme volatility
function _ls_is_momentum_algo($algo_name) {
    $momentum_algos = array(
        'Momentum Burst', 'Trend Sniper', 'Breakout 24h',
        'Volume Spike', 'ADX Trend Strength', 'Alpha Predator'
    );
    return in_array($algo_name, $momentum_algos);
}


// ────────────────────────────────────────────────────────────
//  Fetch current price from lm_price_cache
// ────────────────────────────────────────────────────────────

function _ls_get_cached_price($conn, $symbol) {
    $safe = $conn->real_escape_string($symbol);
    // Check if lm_price_cache table exists
    $chk = $conn->query("SHOW TABLES LIKE 'lm_price_cache'");
    if (!$chk || $chk->num_rows == 0) return 0;

    $res = $conn->query("SELECT price FROM lm_price_cache WHERE symbol='$safe' ORDER BY updated_at DESC LIMIT 1");
    if ($res && $res->num_rows > 0) {
        $row = $res->fetch_assoc();
        return (float)$row['price'];
    }
    return 0;
}

// ────────────────────────────────────────────────────────────
//  Sector mapping for stock concentration cap
// ────────────────────────────────────────────────────────────

function _ls_get_stock_sector($symbol) {
    $map = array(
        'AAPL'  => 'Technology',
        'MSFT'  => 'Technology',
        'GOOGL' => 'Technology',
        'NVDA'  => 'Technology',
        'META'  => 'Technology',
        'AMZN'  => 'Consumer',
        'NFLX'  => 'Consumer',
        'WMT'   => 'Consumer',
        'JPM'   => 'Financial',
        'BAC'   => 'Financial',
        'XOM'   => 'Energy',
        'JNJ'   => 'Healthcare'
    );
    return isset($map[$symbol]) ? $map[$symbol] : 'Other';
}

function _ls_count_sector_signals($conn, $sector, $sector_map) {
    // Count active stock signals in the same sector
    $now = date('Y-m-d H:i:s');
    $res = $conn->query("SELECT symbol FROM lm_signals
        WHERE asset_class='STOCK' AND status='active' AND expires_at > '$now'");
    if (!$res) return 0;
    $count = 0;
    while ($row = $res->fetch_assoc()) {
        $sym_sector = isset($sector_map[$row['symbol']]) ? $sector_map[$row['symbol']] : 'Other';
        if ($sym_sector === $sector) $count++;
    }
    return $count;
}

// ────────────────────────────────────────────────────────────
//  ACTION: scan — Run all 19 algorithms
// ────────────────────────────────────────────────────────────

function _ls_action_scan($conn) {
    global $crypto_symbols, $forex_symbols, $stock_symbols;

    // Admin auth
    $key = isset($_GET['key']) ? $_GET['key'] : '';
    if ($key !== 'livetrader2026') {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $generated = array();
    $symbols_scanned = 0;

    // ── Scan crypto symbols ──
    foreach ($crypto_symbols as $sym) {
        // Cursor: skip excluded symbols (ETH bearish alpha -4.390, see ANALYSIS_FINANCES)
        if (in_array($sym, $EXCLUDED_SYMBOLS)) continue;

        $symbols_scanned++;

        // Get price from cache
        $price = _ls_get_cached_price($conn, $sym);

        // Fetch candles (48 for MACD/Trend Sniper which need 34+)
        $candles = _ls_fetch_binance_klines($sym, 48);
        if (count($candles) < 2) continue;

        // If no cached price, use last candle close
        if ($price <= 0 && count($candles) > 0) {
            $last = $candles[count($candles) - 1];
            $price = (float)$last['close'];
        }
        if ($price <= 0) continue;

        // Run all 19 algorithms
        $algo_results = array(
            _ls_algo_momentum_burst($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_rsi_reversal($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_breakout_24h($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_dca_dip($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_bollinger_squeeze($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_macd_crossover($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_consensus($conn, $price, $sym, 'CRYPTO'),
            _ls_algo_volatility_breakout($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_trend_sniper($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_dip_recovery($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_volume_spike($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_vam($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_mean_reversion_sniper($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_adx_trend($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_stoch_rsi_cross($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_awesome_osc($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_rsi2_scalp($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_ichimoku_cloud($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_alpha_predator($candles, $price, $sym, 'CRYPTO'),
            _ls_algo_contrarian_fg($conn, $candles, $price, $sym, 'CRYPTO')
        );

        // Kimi: check for extreme volatility (momentum crash protection)
        $vol_extreme = _ls_is_volatility_extreme($candles);
        // Kimi: fetch funding rate for this crypto symbol (Bybit, free)
        $funding = _ls_fetch_funding_rate($sym);

        foreach ($algo_results as $sig) {
            if ($sig === null) continue;
            // Kimi: skip momentum algos during extreme volatility
            if ($vol_extreme && _ls_is_momentum_algo($sig['algorithm_name'])) continue;

            // World-Class: Hurst-based strategy selection (disable wrong-regime algos)
            if (!_ls_hurst_gate($conn, $sig['algorithm_name'], 'CRYPTO')) continue;

            // World-Class: Alpha decay check (skip decayed algorithms)
            $algo_health = _ls_get_algo_weight($conn, $sig['algorithm_name'], 'CRYPTO');
            if ($algo_health['status'] === 'decayed') continue;

            // World-Class: Apply online learning weight to signal strength
            if ($algo_health['weight'] > 0 && $algo_health['weight'] != 1.0) {
                $sig['signal_strength'] = min(100, max(10,
                    (int)($sig['signal_strength'] * $algo_health['weight'])));
            }

            // Kimi: ATR-adjust TP/SL
            $sig = _ls_atr_adjust_tp_sl($candles, $price, $sig);
            // Regime-aware TP/SL scaling (reduce targets in sideways markets)
            $sig = _ls_regime_scale_tp_sl($conn, $sig, 'CRYPTO');
            // Kimi: apply funding rate signal boost/penalty (crypto only)
            $sig = _ls_apply_funding_rate($sig, $funding);
            // Dedup
            if (_ls_signal_exists($conn, $sym, $sig['algorithm_name'])) continue;
            $insert_id = _ls_insert_signal($conn, 'CRYPTO', $sym, $price, $sig);
            if ($insert_id > 0) {
                $generated[] = array(
                    'id'              => $insert_id,
                    'symbol'          => $sym,
                    'algorithm_name'  => $sig['algorithm_name'],
                    'signal_type'     => $sig['signal_type'],
                    'signal_strength' => $sig['signal_strength'],
                    'entry_price'     => $price,
                    'target_tp_pct'   => $sig['target_tp_pct'],
                    'target_sl_pct'   => $sig['target_sl_pct'],
                    'max_hold_hours'  => $sig['max_hold_hours'],
                    'rationale'       => json_decode($sig['rationale'], true)
                );
            }
        }
    }

    // ── Scan forex symbols ──
    foreach ($forex_symbols as $sym) {
        $symbols_scanned++;

        $price = _ls_get_cached_price($conn, $sym);

        // Fetch candles (48 for MACD/Trend Sniper which need 34+)
        $candles = _ls_fetch_twelvedata_series($sym, 48);
        if (count($candles) < 2) continue;

        if ($price <= 0 && count($candles) > 0) {
            $last = $candles[count($candles) - 1];
            $price = (float)$last['close'];
        }
        if ($price <= 0) continue;

        // Run all 19 algorithms
        $algo_results = array(
            _ls_algo_momentum_burst($candles, $price, $sym, 'FOREX'),
            _ls_algo_rsi_reversal($candles, $price, $sym, 'FOREX'),
            _ls_algo_breakout_24h($candles, $price, $sym, 'FOREX'),
            _ls_algo_dca_dip($candles, $price, $sym, 'FOREX'),
            _ls_algo_bollinger_squeeze($candles, $price, $sym, 'FOREX'),
            _ls_algo_macd_crossover($candles, $price, $sym, 'FOREX'),
            _ls_algo_consensus($conn, $price, $sym, 'FOREX'),
            _ls_algo_volatility_breakout($candles, $price, $sym, 'FOREX'),
            _ls_algo_trend_sniper($candles, $price, $sym, 'FOREX'),
            _ls_algo_dip_recovery($candles, $price, $sym, 'FOREX'),
            _ls_algo_volume_spike($candles, $price, $sym, 'FOREX'),
            _ls_algo_vam($candles, $price, $sym, 'FOREX'),
            _ls_algo_mean_reversion_sniper($candles, $price, $sym, 'FOREX'),
            _ls_algo_adx_trend($candles, $price, $sym, 'FOREX'),
            _ls_algo_stoch_rsi_cross($candles, $price, $sym, 'FOREX'),
            _ls_algo_awesome_osc($candles, $price, $sym, 'FOREX'),
            _ls_algo_rsi2_scalp($candles, $price, $sym, 'FOREX'),
            _ls_algo_ichimoku_cloud($candles, $price, $sym, 'FOREX'),
            _ls_algo_alpha_predator($candles, $price, $sym, 'FOREX'),
            _ls_algo_contrarian_fg($conn, $candles, $price, $sym, 'FOREX')
        );

        // Kimi: check for extreme volatility (momentum crash protection)
        $vol_extreme = _ls_is_volatility_extreme($candles);

        foreach ($algo_results as $sig) {
            if ($sig === null) continue;
            // Kimi: skip momentum algos during extreme volatility
            if ($vol_extreme && _ls_is_momentum_algo($sig['algorithm_name'])) continue;

            // World-Class: Hurst-based strategy selection
            if (!_ls_hurst_gate($conn, $sig['algorithm_name'], 'FOREX')) continue;

            // World-Class: Alpha decay check
            $algo_health = _ls_get_algo_weight($conn, $sig['algorithm_name'], 'FOREX');
            if ($algo_health['status'] === 'decayed') continue;

            // World-Class: Apply online learning weight
            if ($algo_health['weight'] > 0 && $algo_health['weight'] != 1.0) {
                $sig['signal_strength'] = min(100, max(10,
                    (int)($sig['signal_strength'] * $algo_health['weight'])));
            }

            // Kimi: ATR-adjust TP/SL
            $sig = _ls_atr_adjust_tp_sl($candles, $price, $sig);
            // Regime-aware TP/SL scaling (reduce targets in sideways markets)
            $sig = _ls_regime_scale_tp_sl($conn, $sig, 'FOREX');
            if (_ls_signal_exists($conn, $sym, $sig['algorithm_name'])) continue;
            $insert_id = _ls_insert_signal($conn, 'FOREX', $sym, $price, $sig);
            if ($insert_id > 0) {
                $generated[] = array(
                    'id'              => $insert_id,
                    'symbol'          => $sym,
                    'algorithm_name'  => $sig['algorithm_name'],
                    'signal_type'     => $sig['signal_type'],
                    'signal_strength' => $sig['signal_strength'],
                    'entry_price'     => $price,
                    'target_tp_pct'   => $sig['target_tp_pct'],
                    'target_sl_pct'   => $sig['target_sl_pct'],
                    'max_hold_hours'  => $sig['max_hold_hours'],
                    'rationale'       => json_decode($sig['rationale'], true)
                );
            }
        }
    }

    // ── Scan stock symbols (only during market hours or if forced) ──
    $force_stocks = isset($_GET['force_stocks']) ? (int)$_GET['force_stocks'] : 0;
    $market_open = _ls_is_market_hours();
    $stock_scanned = 0;

    if ($market_open || $force_stocks) {
        foreach ($stock_symbols as $sym) {
            $symbols_scanned++;
            $stock_scanned++;

            $price = _ls_get_cached_price($conn, $sym);

            // Fetch candles via Finnhub (48 for MACD/Trend Sniper)
            $candles = _ls_fetch_finnhub_klines($sym, 48);
            if (count($candles) < 2) continue;

            if ($price <= 0 && count($candles) > 0) {
                $last = $candles[count($candles) - 1];
                $price = (float)$last['close'];
            }
            if ($price <= 0) continue;

            // Run all 23 algorithms (19 technical + 4 fundamental/contrarian)
            $algo_results = array(
                _ls_algo_momentum_burst($candles, $price, $sym, 'STOCK'),
                _ls_algo_rsi_reversal($candles, $price, $sym, 'STOCK'),
                _ls_algo_breakout_24h($candles, $price, $sym, 'STOCK'),
                _ls_algo_dca_dip($candles, $price, $sym, 'STOCK'),
                _ls_algo_bollinger_squeeze($candles, $price, $sym, 'STOCK'),
                _ls_algo_macd_crossover($candles, $price, $sym, 'STOCK'),
                _ls_algo_consensus($conn, $price, $sym, 'STOCK'),
                _ls_algo_volatility_breakout($candles, $price, $sym, 'STOCK'),
                _ls_algo_trend_sniper($candles, $price, $sym, 'STOCK'),
                _ls_algo_dip_recovery($candles, $price, $sym, 'STOCK'),
                _ls_algo_volume_spike($candles, $price, $sym, 'STOCK'),
                _ls_algo_vam($candles, $price, $sym, 'STOCK'),
                _ls_algo_mean_reversion_sniper($candles, $price, $sym, 'STOCK'),
                _ls_algo_adx_trend($candles, $price, $sym, 'STOCK'),
                _ls_algo_stoch_rsi_cross($candles, $price, $sym, 'STOCK'),
                _ls_algo_awesome_osc($candles, $price, $sym, 'STOCK'),
                _ls_algo_rsi2_scalp($candles, $price, $sym, 'STOCK'),
                _ls_algo_ichimoku_cloud($candles, $price, $sym, 'STOCK'),
                _ls_algo_alpha_predator($candles, $price, $sym, 'STOCK'),
                // Fundamental algorithms (#20-23) — including contrarian
                _ls_algo_insider_cluster($conn, $price, $sym, 'STOCK'),
                _ls_algo_13f_new_position($conn, $price, $sym, 'STOCK'),
                _ls_algo_sentiment_divergence($conn, $candles, $price, $sym, 'STOCK'),
                _ls_algo_contrarian_fg($conn, $candles, $price, $sym, 'STOCK')
            );

            // Sector map for concentration cap
            $sector_map = array(
                'AAPL' => 'Technology', 'MSFT' => 'Technology', 'GOOGL' => 'Technology',
                'NVDA' => 'Technology', 'META' => 'Technology',
                'AMZN' => 'Consumer', 'NFLX' => 'Consumer', 'WMT' => 'Consumer',
                'JPM'  => 'Financial', 'BAC' => 'Financial',
                'XOM'  => 'Energy', 'JNJ' => 'Healthcare'
            );

            // Kimi: check for extreme volatility (momentum crash protection)
            $vol_extreme = _ls_is_volatility_extreme($candles);

            foreach ($algo_results as $sig) {
                if ($sig === null) continue;

                // Cursor: skip paused stock algorithms (backtest WR < 12%, see ANALYSIS_FINANCES)
                if (in_array($sig['algorithm_name'], $PAUSED_STOCK_ALGOS)) continue;

                // Kimi: skip momentum algos during extreme volatility
                if ($vol_extreme && _ls_is_momentum_algo($sig['algorithm_name'])) continue;

                // World-Class: Hurst-based strategy selection
                if (!_ls_hurst_gate($conn, $sig['algorithm_name'], 'STOCK')) continue;

                // World-Class: Alpha decay check
                $algo_health = _ls_get_algo_weight($conn, $sig['algorithm_name'], 'STOCK');
                if ($algo_health['status'] === 'decayed') continue;

                // World-Class: Apply online learning weight
                if ($algo_health['weight'] > 0 && $algo_health['weight'] != 1.0) {
                    $sig['signal_strength'] = min(100, max(10,
                        (int)($sig['signal_strength'] * $algo_health['weight'])));
                }

                // Kimi: ATR-adjust TP/SL
                $sig = _ls_atr_adjust_tp_sl($candles, $price, $sig);
                // Regime-aware TP/SL scaling (reduce targets in sideways markets)
                $sig = _ls_regime_scale_tp_sl($conn, $sig, 'STOCK');
                if (_ls_signal_exists($conn, $sym, $sig['algorithm_name'])) continue;

                // CDR preference: boost signal strength for commission-free CDR stocks
                // CDR stocks trade at $0 commission on NEO Exchange — significant edge
                if (_ls_is_cdr_ticker($sym)) {
                    $sig['signal_strength'] = min(100, (int)$sig['signal_strength'] + 8);
                    $rationale = json_decode($sig['rationale'], true);
                    if (!is_array($rationale)) $rationale = array();
                    $rationale['cdr_boost'] = true;
                    $rationale['cdr_note'] = 'CDR: $0 commission on NEO Exchange';
                    $sig['rationale'] = json_encode($rationale);
                }

                // Sector concentration cap — max 3 active signals per sector
                $sym_sector = isset($sector_map[$sym]) ? $sector_map[$sym] : 'Other';
                $sector_count = _ls_count_sector_signals($conn, $sym_sector, $sector_map);
                if ($sector_count >= 3) continue;

                $insert_id = _ls_insert_signal($conn, 'STOCK', $sym, $price, $sig);
                if ($insert_id > 0) {
                    $generated[] = array(
                        'id'              => $insert_id,
                        'symbol'          => $sym,
                        'algorithm_name'  => $sig['algorithm_name'],
                        'signal_type'     => $sig['signal_type'],
                        'signal_strength' => $sig['signal_strength'],
                        'entry_price'     => $price,
                        'target_tp_pct'   => $sig['target_tp_pct'],
                        'target_sl_pct'   => $sig['target_sl_pct'],
                        'max_hold_hours'  => $sig['max_hold_hours'],
                        'rationale'       => json_decode($sig['rationale'], true)
                    );
                }
            }
        }
    }

    // Discord alert for strong signals (strength >= 80)
    $strong_signals = array();
    foreach ($generated as $g) {
        if (intval($g['signal_strength']) >= 80) {
            $strong_signals[] = $g;
        }
    }
    if (count($strong_signals) > 0) {
        _ls_discord_alert($strong_signals, count($generated), $symbols_scanned);
    }

    echo json_encode(array(
        'ok'                => true,
        'action'            => 'scan',
        'signals_generated' => count($generated),
        'symbols_scanned'   => $symbols_scanned,
        'stocks_scanned'    => $stock_scanned,
        'market_open'       => $market_open ? true : false,
        'signals'           => $generated
    ));
}

// ────────────────────────────────────────────────────────────
//  ACTION: list — Show active (non-expired) signals
// ────────────────────────────────────────────────────────────

function _ls_action_list($conn) {
    $now = date('Y-m-d H:i:s');
    $where = "status='active' AND expires_at > '$now'";

    $filter_asset = isset($_GET['asset_class']) ? $conn->real_escape_string($_GET['asset_class']) : '';
    if ($filter_asset !== '') {
        $where .= " AND asset_class='" . strtoupper($filter_asset) . "'";
    }

    $filter_symbol = isset($_GET['symbol']) ? $conn->real_escape_string($_GET['symbol']) : '';
    if ($filter_symbol !== '') {
        $where .= " AND symbol='$filter_symbol'";
    }

    $res = $conn->query("SELECT * FROM lm_signals WHERE $where ORDER BY signal_strength DESC, signal_time DESC LIMIT 200");
    if (!$res) {
        echo json_encode(array('ok' => false, 'error' => 'Query failed: ' . $conn->error));
        return;
    }

    $signals = array();
    while ($row = $res->fetch_assoc()) {
        $rationale_decoded = json_decode($row['rationale'], true);
        if (!is_array($rationale_decoded)) {
            $rationale_decoded = $row['rationale'];
        }

        $signals[] = array(
            'id'              => (int)$row['id'],
            'asset_class'     => $row['asset_class'],
            'symbol'          => $row['symbol'],
            'algorithm_name'  => $row['algorithm_name'],
            'signal_type'     => $row['signal_type'],
            'signal_strength' => (int)$row['signal_strength'],
            'entry_price'     => (float)$row['entry_price'],
            'target_tp_pct'   => (float)$row['target_tp_pct'],
            'target_sl_pct'   => (float)$row['target_sl_pct'],
            'max_hold_hours'  => (int)$row['max_hold_hours'],
            'timeframe'       => $row['timeframe'],
            'rationale'       => $rationale_decoded,
            'signal_time'     => $row['signal_time'],
            'expires_at'      => $row['expires_at'],
            'status'          => $row['status']
        );
    }

    echo json_encode(array(
        'ok'      => true,
        'action'  => 'list',
        'count'   => count($signals),
        'signals' => $signals
    ));
}

// ────────────────────────────────────────────────────────────
//  ACTION: expire — Mark signals past their expires_at
// ────────────────────────────────────────────────────────────

function _ls_action_expire($conn) {
    $now = date('Y-m-d H:i:s');
    $conn->query("UPDATE lm_signals SET status='expired' WHERE status='active' AND expires_at <= '$now'");
    $affected = $conn->affected_rows;

    echo json_encode(array(
        'ok'             => true,
        'action'         => 'expire',
        'signals_expired' => (int)$affected
    ));
}

// ────────────────────────────────────────────────────────────
//  Discord alert for strong signals
// ────────────────────────────────────────────────────────────
function _ls_discord_alert($strong_signals, $total_generated, $symbols_scanned) {
    // Read webhook URL from .env
    $env_file = dirname(__FILE__) . '/../../favcreators/public/api/.env';
    $webhook_url = '';
    if (file_exists($env_file)) {
        $lines = file($env_file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        foreach ($lines as $line) {
            if (strpos($line, 'DISCORD_WEBHOOK_URL=') === 0) {
                $webhook_url = trim(substr($line, 20));
                break;
            }
        }
    }
    if (!$webhook_url) return;

    $lines = array();
    foreach (array_slice($strong_signals, 0, 10) as $s) {
        $emoji = (intval($s['signal_strength']) >= 90) ? '🔴' : '🟠';
        $entry = floatval($s['entry_price']);
        $tp_pct = floatval($s['target_tp_pct']);
        $sl_pct = floatval($s['target_sl_pct']);
        $direction = (isset($s['signal_type']) && $s['signal_type'] === 'SHORT') ? 'SHORT' : 'BUY';

        // Calculate TP/SL prices based on direction
        if ($direction === 'SHORT') {
            $tp_price = $entry * (1 - ($tp_pct / 100));
            $sl_price = $entry * (1 + ($sl_pct / 100));
        } else {
            $tp_price = $entry * (1 + ($tp_pct / 100));
            $sl_price = $entry * (1 - ($sl_pct / 100));
        }

        // Format prices — use more decimals for small-value assets (crypto pairs under $1, forex)
        $decimals = ($entry < 1) ? 6 : (($entry < 100) ? 4 : 2);
        $entry_fmt = number_format($entry, $decimals);
        $tp_fmt = number_format($tp_price, $decimals);
        $sl_fmt = number_format($sl_price, $decimals);

        $dir_label = ($direction === 'SHORT') ? ' 🔻SHORT' : '';

        $lines[] = $emoji . ' **' . $s['symbol'] . '**' . $dir_label . ' — ' . $s['algorithm_name']
            . ' | Str: ' . $s['signal_strength']
            . "\n"
            . '  📍 Entry: $' . $entry_fmt
            . ' | 🎯 TP: $' . $tp_fmt . ' (+' . $tp_pct . '%)'
            . ' | 🛡️ SL: $' . $sl_fmt . ' (-' . $sl_pct . '%)';
    }
    if (count($strong_signals) > 10) {
        $lines[] = '... and ' . (count($strong_signals) - 10) . ' more';
    }

    $embed = array(
        'title' => '⚡ Live Monitor: ' . count($strong_signals) . ' strong signal' . (count($strong_signals) > 1 ? 's' : '') . ' (of ' . $total_generated . ' total)',
        'description' => implode("\n", $lines),
        'color' => 15105570,
        'footer' => array('text' => $symbols_scanned . ' symbols scanned | ' . date('H:i:s') . ' UTC'),
        'url' => 'https://findtorontoevents.ca/live-monitor/live-monitor.html'
    );

    $payload = json_encode(array('embeds' => array($embed)));
    _ls_send_discord_webhook($webhook_url, $payload);

    // ── Extraordinary alerts: top-rated algorithm signals to #notifications ──
    _ls_check_extraordinary_alerts($conn, $strong_signals, $env_file);
}

/**
 * Send payload to a Discord webhook URL
 */
function _ls_send_discord_webhook($webhook_url, $payload) {
    if (!$webhook_url) return;
    $ch = curl_init($webhook_url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_exec($ch);
    curl_close($ch);
}

/**
 * Read the notifications webhook URL from .env (or fall back to main webhook)
 */
function _ls_get_notif_webhook($env_file) {
    $notif_webhook = '';
    $main_webhook = '';
    if (file_exists($env_file)) {
        $lines = file($env_file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        foreach ($lines as $line) {
            if (strpos($line, 'DISCORD_NOTIFICATIONS_WEBHOOK=') === 0) {
                $notif_webhook = trim(substr($line, 30));
            }
            if (strpos($line, 'DISCORD_WEBHOOK_URL=') === 0) {
                $main_webhook = trim(substr($line, 20));
            }
        }
    }
    return $notif_webhook ? $notif_webhook : $main_webhook;
}

/**
 * Format a signal line for Discord embed (reusable)
 */
function _ls_format_signal_line($s) {
    $entry = floatval($s['entry_price']);
    $tp_pct = floatval($s['target_tp_pct']);
    $sl_pct = floatval($s['target_sl_pct']);
    $direction = (isset($s['signal_type']) && $s['signal_type'] === 'SHORT') ? 'SHORT' : 'BUY';

    if ($direction === 'SHORT') {
        $tp_price = $entry * (1 - ($tp_pct / 100));
        $sl_price = $entry * (1 + ($sl_pct / 100));
    } else {
        $tp_price = $entry * (1 + ($tp_pct / 100));
        $sl_price = $entry * (1 - ($sl_pct / 100));
    }

    $decimals = ($entry < 1) ? 6 : (($entry < 100) ? 4 : 2);
    $dir_emoji = ($direction === 'SHORT') ? "\xF0\x9F\x94\xBB" : "\xF0\x9F\x94\xBA";

    return $dir_emoji . ' **' . $s['symbol'] . '** (' . $direction . ') | Strength: ' . $s['signal_strength'] . '/100'
        . ' | ' . $s['algorithm_name']
        . "\n"
        . "\xF0\x9F\x93\x8D" . ' Entry: **$' . number_format($entry, $decimals) . '**'
        . ' | ' . "\xF0\x9F\x8E\xAF" . ' TP: **$' . number_format($tp_price, $decimals) . '** (+' . $tp_pct . '%)'
        . ' | ' . "\xF0\x9F\x9B\xA1" . "\xEF\xB8\x8F" . ' SL: **$' . number_format($sl_price, $decimals) . '** (-' . $sl_pct . '%)';
}

/**
 * Check for extraordinary signals and alert #notifications
 * Covers: top algorithm picks, meme coin rockets, ultra-high-strength crypto
 */
function _ls_check_extraordinary_alerts($conn, $strong_signals, $env_file) {
    $webhook = _ls_get_notif_webhook($env_file);
    if (!$webhook) return;

    // ── 1. Top algorithm signals (best Sharpe ratio algo, strength >= 85) ──
    $best_algo_name = '';
    $best_algo_sharpe = 0;
    $best_algo_win_rate = 0;
    $res = $conn->query("SELECT best_algo_name, best_algo_sharpe, best_algo_win_rate FROM lm_challenger_showdown ORDER BY snapshot_date DESC LIMIT 1");
    if ($res && $row = $res->fetch_assoc()) {
        $best_algo_name = $row['best_algo_name'];
        $best_algo_sharpe = floatval($row['best_algo_sharpe']);
        $best_algo_win_rate = floatval($row['best_algo_win_rate']);
    }

    $top_algo_signals = array();
    if ($best_algo_name) {
        foreach ($strong_signals as $s) {
            if ($s['algorithm_name'] === $best_algo_name && intval($s['signal_strength']) >= 85) {
                $top_algo_signals[] = $s;
            }
        }
    }

    if (count($top_algo_signals) > 0) {
        $alert_lines = array();
        foreach ($top_algo_signals as $s) {
            $alert_lines[] = _ls_format_signal_line($s);
        }

        $embed = array(
            'title' => "\xF0\x9F\x8F\x86" . ' Top Algorithm Alert: ' . $best_algo_name,
            'description' => '**' . count($top_algo_signals) . ' extraordinary signal' . (count($top_algo_signals) > 1 ? 's' : '') . '** from our highest-performing algorithm'
                . "\n" . "\xF0\x9F\x93\x8A" . ' Sharpe: ' . $best_algo_sharpe . ' | Win Rate: ' . $best_algo_win_rate . '%'
                . "\n\n" . implode("\n\n", $alert_lines),
            'color' => 16766720,  // Gold
            'footer' => array('text' => 'Top Algorithm Alerts | ' . date('H:i:s') . ' UTC'),
            'url' => 'https://findtorontoevents.ca/live-monitor/live-monitor.html'
        );

        $payload = json_encode(array(
            'content' => "\xF0\x9F\x9A\xA8" . ' **EXTRAORDINARY SIGNAL** from top-rated algorithm!',
            'embeds' => array($embed)
        ));
        _ls_send_discord_webhook($webhook, $payload);
    }

    // ── 2. Meme coin rockets (PEPE, FLOKI, DOGE, SHIB with strength >= 80) ──
    $meme_tickers = array('PEPEUSD', 'FLOKIUSD', 'DOGEUSD', 'SHIBUSD');
    $meme_signals = array();
    foreach ($strong_signals as $s) {
        if (in_array($s['symbol'], $meme_tickers) && intval($s['signal_strength']) >= 80) {
            // Don't double-alert if already in top algo signals
            $already = false;
            foreach ($top_algo_signals as $ta) {
                if ($ta['symbol'] === $s['symbol'] && $ta['algorithm_name'] === $s['algorithm_name']) {
                    $already = true;
                    break;
                }
            }
            if (!$already) $meme_signals[] = $s;
        }
    }

    if (count($meme_signals) > 0) {
        $alert_lines = array();
        foreach (array_slice($meme_signals, 0, 3) as $s) {
            $alert_lines[] = _ls_format_signal_line($s);
        }

        $embed = array(
            'title' => "\xF0\x9F\x90\xB8" . ' Meme Coin Alert',
            'description' => '**' . count($meme_signals) . ' high-strength meme coin signal' . (count($meme_signals) > 1 ? 's' : '') . '** detected'
                . "\n\n" . implode("\n\n", $alert_lines),
            'color' => 5763719,  // Green
            'footer' => array('text' => 'Meme Coin Alerts | ' . date('H:i:s') . ' UTC'),
            'url' => 'https://findtorontoevents.ca/live-monitor/live-monitor.html'
        );

        $payload = json_encode(array(
            'content' => "\xF0\x9F\x90\xB8" . ' **MEME COIN ROCKET** ' . "\xE2\x80\x94" . ' High-strength signal on meme coins!',
            'embeds' => array($embed)
        ));
        _ls_send_discord_webhook($webhook, $payload);
    }

    // ── 3. Ultra-high crypto signals (any crypto, strength >= 92, any algo) ──
    $ultra_crypto = array();
    foreach ($strong_signals as $s) {
        if (intval($s['signal_strength']) >= 92) {
            // Don't double-alert
            $already = false;
            foreach ($top_algo_signals as $ta) {
                if ($ta['symbol'] === $s['symbol'] && $ta['algorithm_name'] === $s['algorithm_name']) { $already = true; break; }
            }
            foreach ($meme_signals as $ms) {
                if ($ms['symbol'] === $s['symbol'] && $ms['algorithm_name'] === $s['algorithm_name']) { $already = true; break; }
            }
            if (!$already) $ultra_crypto[] = $s;
        }
    }

    if (count($ultra_crypto) > 0) {
        $alert_lines = array();
        foreach (array_slice($ultra_crypto, 0, 3) as $s) {
            $alert_lines[] = _ls_format_signal_line($s);
        }

        $asset_label = 'signal';
        // Check what asset classes are present
        $classes = array();
        foreach ($ultra_crypto as $s) {
            $cls = isset($s['asset_class']) ? $s['asset_class'] : 'CRYPTO';
            $classes[$cls] = true;
        }
        if (isset($classes['CRYPTO']) && count($classes) === 1) $asset_label = 'crypto signal';
        elseif (isset($classes['STOCK']) && count($classes) === 1) $asset_label = 'stock signal';
        elseif (isset($classes['FOREX']) && count($classes) === 1) $asset_label = 'forex signal';

        $embed = array(
            'title' => "\xF0\x9F\x94\xA5" . ' Ultra-High Conviction ' . ucfirst($asset_label) . (count($ultra_crypto) > 1 ? 's' : ''),
            'description' => '**' . count($ultra_crypto) . ' ' . $asset_label . (count($ultra_crypto) > 1 ? 's' : '') . '** with strength 92+/100'
                . "\n\n" . implode("\n\n", $alert_lines),
            'color' => 15158332,  // Red
            'footer' => array('text' => 'Ultra-High Conviction | ' . date('H:i:s') . ' UTC'),
            'url' => 'https://findtorontoevents.ca/live-monitor/live-monitor.html'
        );

        $payload = json_encode(array(
            'content' => "\xF0\x9F\x94\xA5" . ' **ULTRA-HIGH CONVICTION** ' . "\xE2\x80\x94" . ' Strength 92+/100!',
            'embeds' => array($embed)
        ));
        _ls_send_discord_webhook($webhook, $payload);
    }
}

// ────────────────────────────────────────────────────────────
//  ACTION: regime — public market regime classification
// ────────────────────────────────────────────────────────────
function _ls_action_regime($conn) {
    $regimes = array();

    // Crypto regime: BTC trend + volatility
    $btc_candles = _ls_fetch_binance_klines('BTCUSD', 48);
    $btc_closes = _ls_extract_closes($btc_candles);
    $bc = count($btc_closes);
    $crypto_regime = 'unknown';
    $btc_details = array();
    if ($bc >= 20) {
        // SMA 20
        $sum20 = 0;
        for ($i = $bc - 20; $i < $bc; $i++) $sum20 += $btc_closes[$i];
        $sma20 = $sum20 / 20;
        $price = $btc_closes[$bc - 1];

        // Volatility: std dev of returns over last 20 candles
        $returns = array();
        for ($i = $bc - 20; $i < $bc; $i++) {
            if ($btc_closes[$i - 1] > 0) {
                $returns[] = ($btc_closes[$i] - $btc_closes[$i - 1]) / $btc_closes[$i - 1];
            }
        }
        $vol = 0;
        if (count($returns) > 1) {
            $mean = array_sum($returns) / count($returns);
            $sum_sq = 0;
            foreach ($returns as $r) $sum_sq += ($r - $mean) * ($r - $mean);
            $vol = sqrt($sum_sq / (count($returns) - 1)) * 100; // as percentage
        }

        // Classify: bull if above SMA and trending up, bear if below, sideways if near SMA + low vol
        $pct_from_sma = (($price - $sma20) / $sma20) * 100;
        if (abs($pct_from_sma) < 1.0 && $vol < 1.5) {
            $crypto_regime = 'sideways';
        } elseif ($price > $sma20) {
            $crypto_regime = ($vol > 3.0) ? 'volatile_bull' : 'bull';
        } else {
            $crypto_regime = ($vol > 3.0) ? 'volatile_bear' : 'bear';
        }

        $btc_details = array(
            'price' => round($price, 2),
            'sma20' => round($sma20, 2),
            'pct_from_sma' => round($pct_from_sma, 2),
            'volatility_pct' => round($vol, 2),
            'candles_used' => $bc
        );
    }
    $regimes['crypto'] = array('regime' => $crypto_regime, 'benchmark' => 'BTC', 'details' => $btc_details);

    // Forex regime: USDJPY trend
    $jpy_candles = _ls_fetch_twelvedata_series('USDJPY', 48);
    $jpy_closes = _ls_extract_closes($jpy_candles);
    $jc = count($jpy_closes);
    $fx_regime = 'unknown';
    $fx_details = array();
    if ($jc >= 20) {
        $sum20 = 0;
        for ($i = $jc - 20; $i < $jc; $i++) $sum20 += $jpy_closes[$i];
        $sma20 = $sum20 / 20;
        $price = $jpy_closes[$jc - 1];
        $pct_from_sma = (($price - $sma20) / $sma20) * 100;

        $returns = array();
        for ($i = $jc - 20; $i < $jc; $i++) {
            if ($jpy_closes[$i - 1] > 0) {
                $returns[] = ($jpy_closes[$i] - $jpy_closes[$i - 1]) / $jpy_closes[$i - 1];
            }
        }
        $vol = 0;
        if (count($returns) > 1) {
            $mean = array_sum($returns) / count($returns);
            $sum_sq = 0;
            foreach ($returns as $r) $sum_sq += ($r - $mean) * ($r - $mean);
            $vol = sqrt($sum_sq / (count($returns) - 1)) * 100;
        }

        if (abs($pct_from_sma) < 0.3 && $vol < 0.3) {
            $fx_regime = 'sideways';
        } elseif ($price > $sma20) {
            $fx_regime = 'usd_strong';
        } else {
            $fx_regime = 'usd_weak';
        }

        $fx_details = array(
            'price' => round($price, 4),
            'sma20' => round($sma20, 4),
            'pct_from_sma' => round($pct_from_sma, 2),
            'volatility_pct' => round($vol, 3)
        );
    }
    $regimes['forex'] = array('regime' => $fx_regime, 'benchmark' => 'USDJPY', 'details' => $fx_details);

    // Stock regime: SPY/general market via cached stock prices
    $spy_res = $conn->query("SELECT price, last_updated FROM lm_price_cache WHERE symbol = 'AAPL' ORDER BY last_updated DESC LIMIT 1");
    $stock_regime = 'unknown';
    $stk_details = array('note' => 'Stock regime uses individual SMA during scan');
    if ($spy_res && $spy_row = $spy_res->fetch_assoc()) {
        $stk_details['sample_price'] = $spy_row['price'];
        $stk_details['last_updated'] = $spy_row['last_updated'];
        $stock_regime = 'check_individual';
    }
    $regimes['stocks'] = array('regime' => $stock_regime, 'benchmark' => 'individual SMA', 'details' => $stk_details);

    echo json_encode(array(
        'ok' => true,
        'regimes' => $regimes,
        'timestamp' => date('Y-m-d H:i:s')
    ));
}

// ════════════════════════════════════════════════════════════
//  FUNDAMENTAL ALGORITHMS (#20-22) — Read from goldmine DB tables
// ════════════════════════════════════════════════════════════

/**
 * Algorithm 20: Insider Cluster Buy
 * Trigger: 3+ distinct insiders buying same stock within 14 days (SEC Form 4)
 * Basis: Lakonishok & Lee 2001 — insider clusters predict +7-12% outperformance
 * STOCKS ONLY (insiders only exist for stocks)
 */
function _ls_algo_insider_cluster($conn, $price, $symbol, $asset) {
    if ($asset !== 'STOCK') return null;
    if ($price <= 0) return null;

    // Query gm_sec_insider_trades for cluster buys
    $r = $conn->query("SELECT COUNT(DISTINCT filer_name) as insider_count,
        SUM(total_value) as total_bought, SUM(shares) as total_shares,
        MAX(CASE WHEN is_officer = 1 THEN 1 ELSE 0 END) as has_officer,
        MAX(CASE WHEN is_director = 1 THEN 1 ELSE 0 END) as has_director
        FROM gm_sec_insider_trades
        WHERE ticker = '" . $conn->real_escape_string($symbol) . "'
        AND transaction_type = 'P'
        AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)");

    if (!$r || $r->num_rows === 0) return null;
    $row = $r->fetch_assoc();

    $insiders = intval($row['insider_count']);
    if ($insiders < 3) return null;

    $total_val = floatval($row['total_bought']);
    $has_officer = intval($row['has_officer']);
    $has_director = intval($row['has_director']);

    // Strength: base 60 + 5 per extra insider + 10 if officer + 5 if director + value bonus
    $strength = 60 + ($insiders - 3) * 5;
    if ($has_officer) $strength += 10;
    if ($has_director) $strength += 5;
    if ($total_val > 1000000) $strength += 10;
    elseif ($total_val > 500000) $strength += 5;
    $strength = min(95, $strength);

    $rationale = json_encode(array(
        'insider_count' => $insiders,
        'total_value' => $total_val,
        'has_officer' => $has_officer,
        'has_director' => $has_director,
        'basis' => 'Lakonishok & Lee 2001: insider cluster buys predict +7-12% outperformance'
    ));

    return array(
        'algorithm_name' => 'Insider Cluster Buy',
        'signal_type' => 'BUY',
        'signal_strength' => $strength,
        'target_tp_pct' => 8,
        'target_sl_pct' => 4,
        'max_hold_hours' => 336,
        'timeframe' => '14d',
        'rationale' => $rationale
    );
}

/**
 * Algorithm 21: 13F New Position
 * Trigger: 2+ top hedge funds open NEW position in same ticker
 * Basis: SSRN 4767576 (2024) — 24.3% annualized from 13F cloning
 * STOCKS ONLY
 */
function _ls_algo_13f_new_position($conn, $price, $symbol, $asset) {
    if ($asset !== 'STOCK') return null;
    if ($price <= 0) return null;

    // Find latest quarter in DB
    $qr = $conn->query("SELECT MAX(filing_quarter) as latest_q FROM gm_sec_13f_holdings");
    if (!$qr || $qr->num_rows === 0) return null;
    $qrow = $qr->fetch_assoc();
    $latest_q = $qrow['latest_q'];
    if (!$latest_q) return null;

    // Query for multi-fund new positions
    $r = $conn->query("SELECT COUNT(DISTINCT fund_name) as fund_count,
        SUM(value_thousands) as total_value_k,
        GROUP_CONCAT(DISTINCT fund_name SEPARATOR ', ') as funds
        FROM gm_sec_13f_holdings
        WHERE ticker = '" . $conn->real_escape_string($symbol) . "'
        AND filing_quarter = '" . $conn->real_escape_string($latest_q) . "'
        AND change_type = 'new'");

    if (!$r || $r->num_rows === 0) return null;
    $row = $r->fetch_assoc();

    $fund_count = intval($row['fund_count']);
    if ($fund_count < 2) return null;

    $total_val = floatval($row['total_value_k']) * 1000;

    // Strength: base 55 + 10 per fund + value bonus
    $strength = 55 + ($fund_count - 2) * 10;
    if ($total_val > 100000000) $strength += 15;
    elseif ($total_val > 50000000) $strength += 10;
    elseif ($total_val > 10000000) $strength += 5;
    $strength = min(95, $strength);

    $rationale = json_encode(array(
        'fund_count' => $fund_count,
        'funds' => $row['funds'],
        'total_value' => $total_val,
        'quarter' => $latest_q,
        'basis' => 'SSRN 4767576: 13F cloning achieves 24.3% annualized returns'
    ));

    return array(
        'algorithm_name' => '13F New Position',
        'signal_type' => 'BUY',
        'signal_strength' => $strength,
        'target_tp_pct' => 10,
        'target_sl_pct' => 5,
        'max_hold_hours' => 672,
        'timeframe' => '28d',
        'rationale' => $rationale
    );
}

/**
 * Algorithm 22: Sentiment Divergence
 * Trigger: Finnhub sentiment diverges from price action
 * Positive divergence (sentiment high, price falling) = BUY
 * Negative divergence (sentiment low, price rising) = SHORT
 * STOCKS ONLY (sentiment data is for stocks)
 */
function _ls_algo_sentiment_divergence($conn, $candles, $price, $symbol, $asset) {
    if ($asset !== 'STOCK') return null;
    if ($price <= 0 || count($candles) < 10) return null;

    // Get latest sentiment
    $r = $conn->query("SELECT sentiment_score, relative_sentiment, buzz_score, articles_analyzed
        FROM gm_news_sentiment
        WHERE ticker = '" . $conn->real_escape_string($symbol) . "'
        ORDER BY fetch_date DESC LIMIT 1");
    if (!$r || $r->num_rows === 0) return null;
    $sent = $r->fetch_assoc();

    $score = floatval($sent['sentiment_score']);
    $buzz  = floatval($sent['buzz_score']);
    $articles = intval($sent['articles_analyzed']);

    // Need at least 5 articles to trust the sentiment
    if ($articles < 5) return null;

    // Calculate price trend: 10-candle return
    $old_price = floatval($candles[count($candles) - 10]['close']);
    if ($old_price <= 0) return null;
    $price_return = (($price - $old_price) / $old_price) * 100;

    // Positive divergence: sentiment > 0.15 but price falling > 2%
    if ($score > 0.15 && $price_return < -2) {
        $div_magnitude = abs($score) + abs($price_return) / 10;
        $strength = min(85, intval(50 + $div_magnitude * 20));
        if ($buzz > 2) $strength += 5;

        return array(
            'algorithm_name' => 'Sentiment Divergence',
            'signal_type' => 'BUY',
            'signal_strength' => $strength,
            'target_tp_pct' => 3,
            'target_sl_pct' => 2,
            'max_hold_hours' => 168,
            'timeframe' => '7d',
            'rationale' => json_encode(array(
                'sentiment_score' => $score,
                'price_return_10c' => round($price_return, 2),
                'divergence' => 'positive',
                'buzz' => $buzz,
                'articles' => $articles
            ))
        );
    }

    // Negative divergence: sentiment < -0.15 but price rising > 2%
    if ($score < -0.15 && $price_return > 2) {
        $div_magnitude = abs($score) + abs($price_return) / 10;
        $strength = min(85, intval(50 + $div_magnitude * 20));
        if ($buzz > 2) $strength += 5;

        return array(
            'algorithm_name' => 'Sentiment Divergence',
            'signal_type' => 'SHORT',
            'signal_strength' => $strength,
            'target_tp_pct' => 3,
            'target_sl_pct' => 2,
            'max_hold_hours' => 168,
            'timeframe' => '7d',
            'rationale' => json_encode(array(
                'sentiment_score' => $score,
                'price_return_10c' => round($price_return, 2),
                'divergence' => 'negative',
                'buzz' => $buzz,
                'articles' => $articles
            ))
        );
    }

    return null;
}

// ────────────────────────────────────────────────────────────
//  Algorithm 23: Contrarian Fear/Greed
//  BUY during extreme fear near support, SHORT during extreme greed near resistance
//  Academic basis: Buffett "be greedy when others are fearful"
//  Works on all asset classes — uses crypto F&G for crypto, composite for stocks/forex
// ────────────────────────────────────────────────────────────
function _ls_algo_contrarian_fg($conn, $candles, $price, $symbol, $asset) {
    if ($price <= 0 || count($candles) < 10) return null;

    // Read latest Fear & Greed scores from DB (cached by fear_greed.php)
    $composite_score = null;
    $crypto_score = null;

    $r = $conn->query("SELECT source, score FROM lm_fear_greed WHERE source IN ('composite','crypto') AND fetch_date >= DATE_SUB(CURDATE(), INTERVAL 2 DAY) ORDER BY fetch_date DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            if ($row['source'] === 'composite' && $composite_score === null) $composite_score = intval($row['score']);
            if ($row['source'] === 'crypto' && $crypto_score === null) $crypto_score = intval($row['score']);
        }
    }

    // If no F&G data available, skip
    if ($composite_score === null) return null;

    // Effective F&G score based on asset class
    $fg_score = $composite_score;
    if ($asset === 'CRYPTO' && $crypto_score !== null) {
        $fg_score = round($crypto_score * 0.6 + $composite_score * 0.4);
    }

    // Need extreme readings to trigger (<=25 extreme fear, >=75 extreme greed)
    $is_extreme_fear = ($fg_score <= 25);
    $is_extreme_greed = ($fg_score >= 75);
    if (!$is_extreme_fear && !$is_extreme_greed) return null;

    // Calculate support and resistance from candles
    $support = PHP_INT_MAX;
    $resistance = 0;
    $lookback = min(count($candles), 20);
    for ($i = count($candles) - $lookback; $i < count($candles); $i++) {
        $low = (float)$candles[$i]['low'];
        $high = (float)$candles[$i]['high'];
        if ($low < $support) $support = $low;
        if ($high > $resistance) $resistance = $high;
    }

    if ($support <= 0 || $resistance <= 0 || $support >= $resistance) return null;

    $pct_from_support = ($price - $support) / $support * 100;
    $pct_from_resistance = ($resistance - $price) / $resistance * 100;

    // Signal strength: more extreme F&G = stronger signal
    $base_strength = 55 + round(abs($fg_score - 50) / 2);
    $strength = min(90, $base_strength);

    // BUY: extreme fear + price near support (within 5%)
    if ($is_extreme_fear && $pct_from_support <= 5) {
        // Boost if very close to support
        if ($pct_from_support <= 2) $strength = min(90, $strength + 5);

        return array(
            'algorithm_name' => 'Contrarian Fear/Greed',
            'signal_type' => 'BUY',
            'signal_strength' => $strength,
            'target_tp_pct' => ($asset === 'CRYPTO') ? 5 : (($asset === 'FOREX') ? 2 : 4),
            'target_sl_pct' => ($asset === 'CRYPTO') ? 3 : (($asset === 'FOREX') ? 1.5 : 2.5),
            'max_hold_hours' => ($asset === 'STOCK') ? 336 : 168,
            'timeframe' => ($asset === 'STOCK') ? '14d' : '7d',
            'rationale' => json_encode(array(
                'basis' => 'Buffett contrarian: be greedy when others are fearful',
                'fg_score' => $fg_score,
                'fg_classification' => 'extreme_fear',
                'fg_source' => ($asset === 'CRYPTO') ? 'crypto+composite' : 'composite',
                'support_level' => round($support, 6),
                'resistance_level' => round($resistance, 6),
                'distance_to_support_pct' => round($pct_from_support, 2),
                'trigger' => 'extreme_fear + price_near_support'
            ))
        );
    }

    // SHORT: extreme greed + price near resistance (within 5%)
    if ($is_extreme_greed && $pct_from_resistance <= 5) {
        if ($pct_from_resistance <= 2) $strength = min(90, $strength + 5);

        return array(
            'algorithm_name' => 'Contrarian Fear/Greed',
            'signal_type' => 'SHORT',
            'signal_strength' => $strength,
            'target_tp_pct' => ($asset === 'CRYPTO') ? 5 : (($asset === 'FOREX') ? 2 : 4),
            'target_sl_pct' => ($asset === 'CRYPTO') ? 3 : (($asset === 'FOREX') ? 1.5 : 2.5),
            'max_hold_hours' => ($asset === 'STOCK') ? 336 : 168,
            'timeframe' => ($asset === 'STOCK') ? '14d' : '7d',
            'rationale' => json_encode(array(
                'basis' => 'Buffett contrarian: be fearful when others are greedy',
                'fg_score' => $fg_score,
                'fg_classification' => 'extreme_greed',
                'fg_source' => ($asset === 'CRYPTO') ? 'crypto+composite' : 'composite',
                'support_level' => round($support, 6),
                'resistance_level' => round($resistance, 6),
                'distance_to_resistance_pct' => round($pct_from_resistance, 2),
                'trigger' => 'extreme_greed + price_near_resistance'
            ))
        );
    }

    return null;
}

// ────────────────────────────────────────────────────────────
//  Router
// ────────────────────────────────────────────────────────────

$action = isset($_GET['action']) ? $_GET['action'] : 'list';

switch ($action) {
    case 'scan':
        _ls_action_scan($conn);
        break;
    case 'list':
        _ls_action_list($conn);
        break;
    case 'expire':
        _ls_action_expire($conn);
        break;
    case 'regime':
        _ls_action_regime($conn);
        break;
    default:
        echo json_encode(array(
            'ok'    => false,
            'error' => 'Unknown action: ' . $action . '. Valid actions: scan, list, expire, regime'
        ));
        break;
}

$conn->close();
?>
