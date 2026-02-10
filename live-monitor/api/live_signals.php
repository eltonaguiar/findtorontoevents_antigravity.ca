<?php
/**
 * Live Signal Generator — 19 Hour-Trade Algorithms for Crypto, Forex & Stocks
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator)
 *
 * Actions:
 *   ?action=scan&key=livetrader2026   — Run all 19 algorithms, generate signals (admin only)
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
//  Candle fetching — Crypto (CoinGecko OHLC primary, Binance fallback)
// ────────────────────────────────────────────────────────────

function _ls_fetch_binance_klines($symbol, $limit) {
    $limit = (int)$limit;
    if ($limit < 1) $limit = 24;

    // Try CoinGecko OHLC first (works on shared hosting)
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
//  Regime Detection — bull/bear market gate (for Trend Sniper)
//  Science: STOCKSUNIFY2 RAR (Regime-Aware Reversion)
// ────────────────────────────────────────────────────────────

function _ls_get_regime($conn, $asset, $candles, $symbol) {
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

    // Forex regime: USD strength via USDJPY trend
    if ($asset === 'FOREX') {
        if (!isset($GLOBALS['_ls_fx_regime'])) {
            $jpy_candles = _ls_fetch_twelvedata_series('USDJPY', 48);
            $jpy_closes = _ls_extract_closes($jpy_candles);
            $jc = count($jpy_closes);
            if ($jc >= 12) {
                $sum = 0;
                for ($i = 0; $i < $jc; $i++) $sum += $jpy_closes[$i];
                $sma = $sum / $jc;
                $GLOBALS['_ls_fx_regime'] = ($jpy_closes[$jc - 1] > $sma) ? 'usd_strong' : 'usd_weak';
            } else {
                $GLOBALS['_ls_fx_regime'] = 'neutral';
            }
        }
        return $GLOBALS['_ls_fx_regime'];
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
        return $res->fetch_assoc();
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

    $tp  = 3.0;
    $sl  = 1.5;
    $hold = 4;

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

    $tp   = 2.0;
    $sl   = 1.0;
    $hold = 6;

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

    $tp   = 3.0;
    $sl   = 2.0;
    $hold = 8;

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

    if ($change_24h_pct >= -5.0) return null;

    $dip_magnitude = abs($change_24h_pct);
    $strength = min(100, (int)($dip_magnitude * 8));

    $tp   = 5.0;
    $sl   = 3.0;
    $hold = 24;

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

    $tp   = 2.5;
    $sl   = 1.5;
    $hold = 4;

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

    $tp   = 2.0;
    $sl   = 1.0;
    $hold = 6;

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
//  2+ different daily algorithms picked this symbol => BUY boosted.
//  Queries cr_pair_picks (crypto) or fxp_pair_picks (forex).
//  TP avg from picks or 3%, SL avg or 2%, Hold 12h.
// ────────────────────────────────────────────────────────────

function _ls_algo_consensus($conn, $price, $symbol, $asset) {
    $safe_sym = $conn->real_escape_string($symbol);
    $today = date('Y-m-d');
    $yesterday = date('Y-m-d', strtotime('-1 day'));

    if ($asset === 'CRYPTO') {
        $table = 'cr_pair_picks';
    } else {
        $table = 'fxp_pair_picks';
    }

    // Check if the table exists before querying
    $chk = $conn->query("SHOW TABLES LIKE '$table'");
    if (!$chk || $chk->num_rows == 0) return null;

    $sql = "SELECT DISTINCT algorithm_name FROM $table
            WHERE symbol='$safe_sym' AND pick_date >= '$yesterday'
            ORDER BY algorithm_name";
    $res = $conn->query($sql);
    if (!$res) return null;

    $algos = array();
    while ($row = $res->fetch_assoc()) {
        $algos[] = $row['algorithm_name'];
    }

    if (count($algos) < 2) return null;

    $strength = min(100, count($algos) * 25 + 20);

    $tp   = 3.0;
    $sl   = 2.0;
    $hold = 12;

    // Try to get average TP/SL from the picks if columns exist
    // (Pick tables may not have TP/SL columns; use defaults if so)

    $lp = _ls_get_learned_params($conn, 'Consensus', $asset);
    if ($lp !== null) {
        $tp   = (float)$lp['best_tp_pct'];
        $sl   = (float)$lp['best_sl_pct'];
        $hold = (int)$lp['best_hold_hours'];
    }

    return array(
        'algorithm_name'  => 'Consensus',
        'signal_type'     => 'BUY',
        'signal_strength' => $strength,
        'target_tp_pct'   => $tp,
        'target_sl_pct'   => $sl,
        'max_hold_hours'  => $hold,
        'timeframe'       => '1h',
        'rationale'       => json_encode(array(
            'reason'         => count($algos) . ' algorithms picked ' . $symbol . ' in the last 24h',
            'algo_count'     => count($algos),
            'algorithms'     => $algos
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

    $tp   = 3.0;
    $sl   = 2.0;
    $hold = 8;

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
        $tp = 1.5; $sl = 0.75; $hold = 4;
    } elseif ($asset === 'FOREX') {
        $tp = 0.4; $sl = 0.2; $hold = 4;
    } else {
        $tp = 1.0; $sl = 0.5; $hold = 4;
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

    if ($asset === 'CRYPTO') {
        $tp = 2.5; $sl = 1.5; $hold = 8;
    } elseif ($asset === 'FOREX') {
        $tp = 0.6; $sl = 0.4; $hold = 8;
    } else {
        $tp = 1.5; $sl = 1.0; $hold = 8;
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

    if ($asset === 'CRYPTO') {
        $tp = 2.0; $sl = 1.0; $hold = 6;
    } elseif ($asset === 'FOREX') {
        $tp = 0.5; $sl = 0.3; $hold = 6;
    } else {
        $tp = 1.5; $sl = 0.8; $hold = 6;
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

    if ($asset === 'CRYPTO') {
        $tp = 2.0; $sl = 1.0; $hold = 6;
    } elseif ($asset === 'FOREX') {
        $tp = 0.4; $sl = 0.2; $hold = 6;
    } else {
        $tp = 1.2; $sl = 0.6; $hold = 6;
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

    // TP targets middle Bollinger band
    $tp_from_bb = (($bb['middle'] - $price) / $price) * 100;
    if ($tp_from_bb < 0.3) $tp_from_bb = 0.3;

    if ($asset === 'CRYPTO') {
        $tp = min(3.0, max(0.5, $tp_from_bb));
        $sl = 1.0; $hold = 6;
    } elseif ($asset === 'FOREX') {
        $tp = min(0.8, max(0.15, $tp_from_bb));
        $sl = 0.3; $hold = 6;
    } else {
        $tp = min(2.0, max(0.3, $tp_from_bb));
        $sl = 0.7; $hold = 6;
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

    // ADX must be above 25 (strong trend)
    if ($adx < 25) return null;

    // DI spread must be meaningful (> 5 points)
    $di_spread = abs($plus_di - $minus_di);
    if ($di_spread < 5) return null;

    // Direction from DI
    $direction = ($plus_di > $minus_di) ? 'BUY' : 'SHORT';

    // Strength: higher ADX + wider DI spread = stronger
    $strength = min(100, (int)(($adx - 20) * 2 + $di_spread));

    // Asset-class TP/SL
    $tp = 1.5; $sl = 0.75; $hold = 6;
    if ($asset === 'FOREX') { $tp = 0.4; $sl = 0.2; $hold = 6; }
    if ($asset === 'STOCK') { $tp = 1.0; $sl = 0.5; $hold = 6; }

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

    // Asset-class TP/SL
    $tp = 2.0; $sl = 1.0; $hold = 6;
    if ($asset === 'FOREX') { $tp = 0.5; $sl = 0.25; $hold = 6; }
    if ($asset === 'STOCK') { $tp = 1.2; $sl = 0.6; $hold = 6; }

    global $conn;
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

    // Asset-class TP/SL
    $tp = 1.8; $sl = 0.9; $hold = 6;
    if ($asset === 'FOREX') { $tp = 0.4; $sl = 0.2; $hold = 6; }
    if ($asset === 'STOCK') { $tp = 1.0; $sl = 0.5; $hold = 6; }

    global $conn;
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

    // Shorter hold for scalp trades
    $tp = 1.2; $sl = 0.6; $hold = 3;
    if ($asset === 'FOREX') { $tp = 0.3; $sl = 0.15; $hold = 3; }
    if ($asset === 'STOCK') { $tp = 0.8; $sl = 0.4; $hold = 3; }

    global $conn;
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

    // TP/SL
    $tp = 2.0; $sl = 1.0; $hold = 8;
    if ($asset === 'FOREX') { $tp = 0.5; $sl = 0.25; $hold = 8; }
    if ($asset === 'STOCK') { $tp = 1.2; $sl = 0.6; $hold = 8; }

    global $conn;
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
    if ($adx < 25) return null;

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

    // TP/SL: tighter for high-conviction
    $tp = 2.0; $sl = 1.0; $hold = 6;
    if ($asset === 'FOREX') { $tp = 0.5; $sl = 0.25; $hold = 6; }
    if ($asset === 'STOCK') { $tp = 1.2; $sl = 0.6; $hold = 6; }

    global $conn;
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

    $sql = "INSERT INTO lm_signals (asset_class, symbol, algorithm_name, signal_type, signal_strength,
                entry_price, target_tp_pct, target_sl_pct, max_hold_hours, timeframe,
                rationale, signal_time, expires_at, status)
            VALUES ('$safe_asset', '$safe_sym', '$safe_algo', '$safe_type', $strength,
                $entry, $tp, $sl, $hold, '$tf',
                '$rationale', '$now', '$expires', 'active')";
    $conn->query($sql);
    return $conn->insert_id;
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
            _ls_algo_alpha_predator($candles, $price, $sym, 'CRYPTO')
        );

        foreach ($algo_results as $sig) {
            if ($sig === null) continue;
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
            _ls_algo_alpha_predator($candles, $price, $sym, 'FOREX')
        );

        foreach ($algo_results as $sig) {
            if ($sig === null) continue;
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

            // Run all 19 algorithms
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
                _ls_algo_alpha_predator($candles, $price, $sym, 'STOCK')
            );

            foreach ($algo_results as $sig) {
                if ($sig === null) continue;
                if (_ls_signal_exists($conn, $sym, $sig['algorithm_name'])) continue;
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
    default:
        echo json_encode(array(
            'ok'    => false,
            'error' => 'Unknown action: ' . $action . '. Valid actions: scan, list, expire'
        ));
        break;
}

$conn->close();
?>
