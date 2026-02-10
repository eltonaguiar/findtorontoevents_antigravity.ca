<?php
/**
 * Dynamic Crypto Mover Discovery — finds top gainers/losers not in our static watchlist.
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator).
 *
 * Actions:
 *   ?action=discover&key=livetrader2026  — Find top movers, run algorithms, return signals
 *   ?action=movers                       — Show cached top movers (public, no signals)
 *
 * Sources:
 *   1. Binance 24hr ticker (all USDT pairs, no auth)
 *   2. Filters: abs(change%) > 3%, quoteVolume > $500K, not in static list
 *   3. Top 15 movers get candles fetched + 19 algorithms run
 */
require_once dirname(__FILE__) . '/db_connect.php';

// ─── Constants ───────────────────────────────────────────────
$DM_ADMIN_KEY = 'livetrader2026';

// Static symbols already scanned by live_signals.php — skip these
$DM_STATIC_SYMBOLS = array(
    'BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','ADAUSDT','DOTUSDT',
    'MATICUSDT','LINKUSDT','AVAXUSDT','DOGEUSDT','SHIBUSDT','UNIUSDT','ATOMUSDT',
    'EOSUSDT','NEARUSDT','FILUSDT','TRXUSDT','LTCUSDT','BCHUSDT',
    'APTUSDT','ARBUSDT','FTMUSDT','AXSUSDT','HBARUSDT','AAVEUSDT',
    'OPUSDT','MKRUSDT','INJUSDT','SUIUSDT','PEPEUSDT','FLOKIUSDT'
);

// ─── Auto-create discovery cache table ──────────────────────
$conn->query("CREATE TABLE IF NOT EXISTS lm_discovered_movers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    binance_symbol VARCHAR(20) NOT NULL,
    price DECIMAL(18,8) NOT NULL DEFAULT 0,
    change_24h_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    volume_usd DECIMAL(24,2) NOT NULL DEFAULT 0,
    direction VARCHAR(10) NOT NULL DEFAULT '',
    signal_count INT NOT NULL DEFAULT 0,
    signals TEXT,
    discovered_at DATETIME NOT NULL,
    UNIQUE KEY idx_symbol (symbol),
    KEY idx_discovered (discovered_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ─── Route action ───────────────────────────────────────────
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'movers';

if ($action === 'discover') {
    _dm_action_discover($conn);
} elseif ($action === 'movers') {
    _dm_action_movers($conn);
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action. Valid: discover, movers'));
}

$conn->close();
exit;


// =====================================================================
//  ACTION: discover — Fetch Binance 24hr tickers, find movers, run algos
// =====================================================================
function _dm_action_discover($conn) {
    global $DM_ADMIN_KEY, $DM_STATIC_SYMBOLS;

    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $DM_ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    // Thresholds (configurable via GET params)
    $min_change = isset($_GET['min_change']) ? (float)$_GET['min_change'] : 3.0;
    $min_volume = isset($_GET['min_volume']) ? (float)$_GET['min_volume'] : 500000;
    $max_movers = isset($_GET['max_movers']) ? (int)$_GET['max_movers'] : 15;

    // ── Step 1: Fetch top coins from CoinGecko + CoinLore ──
    $tickers = _dm_fetch_coingecko_markets();
    $tickers_checked = count($tickers);

    // Fallback to CoinLore if CoinGecko fails
    if ($tickers_checked === 0) {
        $tickers = _dm_fetch_coinlore_tickers();
        $tickers_checked = count($tickers);
    }

    if ($tickers_checked === 0) {
        echo json_encode(array('ok' => false, 'error' => 'Failed to fetch market data from CoinGecko and CoinLore'));
        return;
    }

    // ── Step 2: Filter for significant movers ──
    // Build a lookup of static symbol bases (BTC, ETH, SOL, etc.)
    $static_bases = array();
    foreach ($DM_STATIC_SYMBOLS as $ss) {
        $static_bases[] = strtoupper(str_replace('USDT', '', $ss));
    }

    $movers = array();
    foreach ($tickers as $t) {
        $ticker = strtoupper(isset($t['ticker']) ? $t['ticker'] : '');
        if ($ticker === '') continue;

        $change = isset($t['change_24h']) ? (float)$t['change_24h'] : 0;
        $volume = isset($t['volume_24h']) ? (float)$t['volume_24h'] : 0;
        $price  = isset($t['price']) ? (float)$t['price'] : 0;

        // Must meet volume and change thresholds
        if (abs($change) < $min_change) continue;
        if ($volume < $min_volume) continue;
        if ($price <= 0) continue;

        // Skip stablecoins
        $skip = array('USDC','USDT','BUSD','DAI','TUSD','FDUSD','USDD','USDP','UST');
        $is_skip = false;
        foreach ($skip as $sb) {
            if ($ticker === $sb) { $is_skip = true; break; }
        }
        if ($is_skip) continue;

        // Skip if already in static watchlist
        $in_static = false;
        foreach ($static_bases as $sb) {
            if ($ticker === $sb) { $in_static = true; break; }
        }
        if ($in_static) continue;

        $binance_sym = $ticker . 'USDT';
        $movers[] = array(
            'binance_symbol' => $binance_sym,
            'symbol'         => $ticker . 'USD',
            'coingecko_id'   => isset($t['coingecko_id']) ? $t['coingecko_id'] : '',
            'price'          => $price,
            'change_24h_pct' => $change,
            'volume_usd'     => $volume,
            'direction'      => ($change > 0) ? 'GAINER' : 'LOSER'
        );
    }

    // Sort by abs change descending
    usort($movers, '_dm_sort_by_change');

    // Cap at max_movers
    if (count($movers) > $max_movers) {
        $movers = array_slice($movers, 0, $max_movers);
    }

    // ── Step 3: For each mover, fetch candles + run algorithms ──
    $results = array();
    $total_signals = 0;

    foreach ($movers as $m) {
        $bin_sym = $m['binance_symbol'];
        $sym     = $m['symbol'];
        $price   = $m['price'];
        $cg_id   = isset($m['coingecko_id']) ? $m['coingecko_id'] : '';

        // Fetch hourly candles — try Kraken (has volume), CoinGecko OHLC, Binance fallback
        $candles = array();
        $candles = _dm_fetch_kraken_ohlc($sym, 48);
        if (count($candles) < 2 && $cg_id !== '') {
            $candles = _dm_fetch_coingecko_ohlc($cg_id, 48);
        }
        if (count($candles) < 2) {
            $candles = _dm_fetch_binance_klines($bin_sym, 48);
        }
        $signal_list = array();

        if (count($candles) >= 2) {
            // Use last candle close as price if needed
            if ($price <= 0) {
                $last = $candles[count($candles) - 1];
                $price = (float)$last['close'];
            }

            // Include the required signal functions
            if (!function_exists('_ls_algo_momentum_burst')) {
                // Load signal algorithms
                $signals_file = dirname(__FILE__) . '/live_signals.php';
                // We can't include the full file (it has routing). Instead, use the candle data inline.
                // Run a subset of fast algorithms via candle analysis
                $signal_list = _dm_run_quick_algorithms($candles, $price, $sym);
            } else {
                // Full algorithm suite available
                $signal_list = _dm_run_full_algorithms($candles, $price, $sym);
            }
        }

        $sig_count = count($signal_list);
        $total_signals += $sig_count;

        $row = array(
            'binance_symbol' => $bin_sym,
            'symbol'         => $sym,
            'price'          => $price,
            'change_24h_pct' => $m['change_24h_pct'],
            'volume_usd'     => $m['volume_usd'],
            'direction'      => $m['direction'],
            'signal_count'   => $sig_count,
            'signals'        => $signal_list
        );
        $results[] = $row;

        // Cache in DB
        $safe_sym  = $conn->real_escape_string($sym);
        $safe_bin  = $conn->real_escape_string($bin_sym);
        $safe_dir  = $conn->real_escape_string($m['direction']);
        $safe_sigs = $conn->real_escape_string(json_encode($signal_list));
        $now       = date('Y-m-d H:i:s');

        $conn->query("DELETE FROM lm_discovered_movers WHERE symbol='$safe_sym'");
        $conn->query("INSERT INTO lm_discovered_movers
            (symbol, binance_symbol, price, change_24h_pct, volume_usd, direction, signal_count, signals, discovered_at)
            VALUES ('$safe_sym','$safe_bin',$price,{$m['change_24h_pct']},{$m['volume_usd']},'$safe_dir',$sig_count,'$safe_sigs','$now')");
    }

    echo json_encode(array(
        'ok'              => true,
        'action'          => 'discover',
        'tickers_checked' => $tickers_checked,
        'movers_found'    => count($results),
        'total_signals'   => $total_signals,
        'min_change_pct'  => $min_change,
        'min_volume_usd'  => $min_volume,
        'movers'          => $results
    ));
}


// =====================================================================
//  ACTION: movers — Show cached discovered movers (public)
// =====================================================================
function _dm_action_movers($conn) {
    $res = $conn->query("SELECT * FROM lm_discovered_movers ORDER BY ABS(change_24h_pct) DESC LIMIT 50");
    if (!$res) {
        echo json_encode(array('ok' => false, 'error' => 'Query failed'));
        return;
    }

    $movers = array();
    while ($row = $res->fetch_assoc()) {
        $sigs = json_decode($row['signals'], true);
        if (!is_array($sigs)) $sigs = array();
        $movers[] = array(
            'symbol'         => $row['symbol'],
            'binance_symbol' => $row['binance_symbol'],
            'price'          => (float)$row['price'],
            'change_24h_pct' => (float)$row['change_24h_pct'],
            'volume_usd'     => (float)$row['volume_usd'],
            'direction'      => $row['direction'],
            'signal_count'   => (int)$row['signal_count'],
            'signals'        => $sigs,
            'discovered_at'  => $row['discovered_at']
        );
    }

    echo json_encode(array(
        'ok'     => true,
        'count'  => count($movers),
        'movers' => $movers
    ));
}


// =====================================================================
//  CoinGecko Markets — top 250 coins sorted by market cap (includes 24h change)
//  Free API, no auth needed, rate-limited (~10-30 req/min)
// =====================================================================
function _dm_fetch_coingecko_markets() {
    $result = array();

    // File cache: 5 minutes
    $cache_file = sys_get_temp_dir() . '/lm_cg_markets.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 300) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $arr = json_decode($cached, true);
            if (is_array($arr) && count($arr) > 0) return $arr;
        }
    }

    // Fetch page 1 (top 250 by market cap, includes % change)
    $url = 'https://api.coingecko.com/api/v3/coins/markets'
         . '?vs_currency=usd&order=market_cap_desc&per_page=250&page=1'
         . '&sparkline=false&price_change_percentage=24h';

    $body = _dm_http_get($url, 20);
    if ($body === null) return $result;

    $data = json_decode($body, true);
    if (!is_array($data)) return $result;

    foreach ($data as $coin) {
        $ticker = isset($coin['symbol']) ? strtoupper($coin['symbol']) : '';
        if ($ticker === '') continue;

        $result[] = array(
            'ticker'       => $ticker,
            'name'         => isset($coin['name']) ? $coin['name'] : '',
            'coingecko_id' => isset($coin['id']) ? $coin['id'] : '',
            'price'        => isset($coin['current_price']) ? (float)$coin['current_price'] : 0,
            'change_24h'   => isset($coin['price_change_percentage_24h']) ? (float)$coin['price_change_percentage_24h'] : 0,
            'volume_24h'   => isset($coin['total_volume']) ? (float)$coin['total_volume'] : 0
        );
    }

    @file_put_contents($cache_file, json_encode($result));
    return $result;
}


// =====================================================================
//  CoinLore Tickers — fallback (top 200 coins by market cap)
//  Free API, no auth needed, no rate limits
// =====================================================================
function _dm_fetch_coinlore_tickers() {
    $result = array();

    // File cache: 5 minutes
    $cache_file = sys_get_temp_dir() . '/lm_coinlore_tickers.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 300) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $arr = json_decode($cached, true);
            if (is_array($arr) && count($arr) > 0) return $arr;
        }
    }

    // Fetch 200 coins in 2 batches of 100
    $all = array();
    for ($start = 0; $start <= 100; $start += 100) {
        $url = 'https://api.coinlore.net/api/tickers/?start=' . $start . '&limit=100';
        $body = _dm_http_get($url, 15);
        if ($body === null) continue;
        $data = json_decode($body, true);
        if (!is_array($data) || !isset($data['data'])) continue;
        foreach ($data['data'] as $coin) {
            $all[] = $coin;
        }
    }

    foreach ($all as $coin) {
        $ticker = isset($coin['symbol']) ? strtoupper($coin['symbol']) : '';
        if ($ticker === '') continue;

        $result[] = array(
            'ticker'     => $ticker,
            'name'       => isset($coin['name']) ? $coin['name'] : '',
            'price'      => isset($coin['price_usd']) ? (float)$coin['price_usd'] : 0,
            'change_24h' => isset($coin['percent_change_24h']) ? (float)$coin['percent_change_24h'] : 0,
            'volume_24h' => isset($coin['volume24']) ? (float)$coin['volume24'] : 0
        );
    }

    @file_put_contents($cache_file, json_encode($result));
    return $result;
}


// =====================================================================
//  Kraken OHLC — hourly candles WITH volume (free, no auth, Ontario-valid)
//  GET https://api.kraken.com/0/public/OHLC?pair=XXXUSD&interval=60
//  Returns: [time, open, high, low, close, vwap, volume, count]
// =====================================================================
function _dm_fetch_kraken_ohlc($symbol, $limit) {
    // Convert internal symbol (e.g. EOSUSD) to Kraken pair
    $kr_pair = _dm_symbol_to_kraken($symbol);
    if ($kr_pair === '') return array();

    $cache_file = sys_get_temp_dir() . '/lm_kr_ohlc_dm_' . md5($kr_pair) . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 120) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $arr = json_decode($cached, true);
            if (is_array($arr) && count($arr) > 0) return $arr;
        }
    }

    $url = 'https://api.kraken.com/0/public/OHLC?pair=' . urlencode($kr_pair) . '&interval=60';
    $body = _dm_http_get($url, 15);
    if ($body === null) return array();

    $data = json_decode($body, true);
    if (!is_array($data) || !isset($data['result'])) return array();

    $ohlc_raw = null;
    foreach ($data['result'] as $key => $val) {
        if ($key === 'last') continue;
        $ohlc_raw = $val;
        break;
    }
    if (!is_array($ohlc_raw) || count($ohlc_raw) === 0) return array();

    $candles = array();
    foreach ($ohlc_raw as $k) {
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

function _dm_symbol_to_kraken($symbol) {
    // Internal XXXUSD -> Kraken pair
    $base = str_replace('USD', '', $symbol);
    $map = array(
        'BTC' => 'XBTUSD',
        'DOGE' => 'XDGUSD',
        'BNB' => ''          // BNB not on Kraken
    );
    if (isset($map[$base])) return $map[$base];
    return $symbol; // Most coins: EOSUSD stays EOSUSD
}


// =====================================================================
//  CoinGecko OHLC — hourly candles for a coin (free, no auth)
//  /api/v3/coins/{id}/ohlc?vs_currency=usd&days=2  → ~48 hourly candles
// =====================================================================
function _dm_fetch_coingecko_ohlc($coin_id, $limit) {
    if ($coin_id === '') return array();

    $cache_file = sys_get_temp_dir() . '/lm_cg_ohlc_' . md5($coin_id) . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 120) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $arr = json_decode($cached, true);
            if (is_array($arr) && count($arr) > 0) return $arr;
        }
    }

    // days=2 gives ~48 hourly candles for coins with enough data
    $url = 'https://api.coingecko.com/api/v3/coins/' . urlencode($coin_id)
         . '/ohlc?vs_currency=usd&days=2';

    $body = _dm_http_get($url, 15);
    if ($body === null) return array();

    $raw = json_decode($body, true);
    if (!is_array($raw)) return array();

    $candles = array();
    foreach ($raw as $k) {
        // CoinGecko OHLC: [timestamp_ms, open, high, low, close]
        if (!is_array($k) || count($k) < 5) continue;
        $candles[] = array(
            'time'   => (float)$k[0] / 1000,
            'open'   => (float)$k[1],
            'high'   => (float)$k[2],
            'low'    => (float)$k[3],
            'close'  => (float)$k[4],
            'volume' => 0  // CoinGecko OHLC doesn't include volume
        );
    }

    if (count($candles) > $limit) {
        $candles = array_slice($candles, count($candles) - $limit);
    }

    @file_put_contents($cache_file, json_encode($candles));
    return $candles;
}


// =====================================================================
//  Binance klines for any symbol (fallback — may be blocked on shared hosts)
// =====================================================================
function _dm_fetch_binance_klines($binance_symbol, $limit) {
    $limit = (int)$limit;
    if ($limit < 1) $limit = 48;

    $cache_file = sys_get_temp_dir() . '/lm_dk_' . md5($binance_symbol . '_' . $limit) . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 60) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $arr = json_decode($cached, true);
            if (is_array($arr) && count($arr) > 0) return $arr;
        }
    }

    $url = 'https://api.binance.com/api/v3/klines?symbol=' . urlencode($binance_symbol)
         . '&interval=1h&limit=' . $limit;
    $body = _dm_http_get($url, 10);
    if ($body === null) return array();

    $raw = json_decode($body, true);
    if (!is_array($raw)) return array();

    $candles = array();
    foreach ($raw as $k) {
        if (!is_array($k) || count($k) < 6) continue;
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


// =====================================================================
//  Quick algorithms (self-contained, no external deps)
//  Runs 8 core algorithms on candle data
// =====================================================================
function _dm_run_quick_algorithms($candles, $price, $symbol) {
    $signals = array();
    $n = count($candles);
    if ($n < 3) return $signals;

    $closes  = array();
    $highs   = array();
    $lows    = array();
    $volumes = array();
    foreach ($candles as $c) {
        $closes[]  = (float)$c['close'];
        $highs[]   = (float)$c['high'];
        $lows[]    = (float)$c['low'];
        $volumes[] = (float)$c['volume'];
    }

    // 1. Momentum Burst — last candle > 2% move
    $last = $candles[$n - 1];
    $move_pct = ($last['open'] > 0) ? (($last['close'] - $last['open']) / $last['open']) * 100 : 0;
    if (abs($move_pct) > 2.0) {
        $dir = ($move_pct > 0) ? 'BUY' : 'SHORT';
        $signals[] = array(
            'algorithm' => 'Momentum Burst',
            'type'      => $dir,
            'strength'  => min(100, (int)(abs($move_pct) * 15)),
            'reason'    => 'Last 1h candle moved ' . round($move_pct, 2) . '%'
        );
    }

    // 2. RSI Reversal
    $rsi = _dm_calc_rsi($closes, 14);
    if ($rsi !== null) {
        if ($rsi < 30) {
            $signals[] = array(
                'algorithm' => 'RSI Reversal',
                'type'      => 'BUY',
                'strength'  => (int)(100 - $rsi * 2),
                'reason'    => 'RSI(14) = ' . round($rsi, 1) . ' (oversold)'
            );
        } elseif ($rsi > 70) {
            $signals[] = array(
                'algorithm' => 'RSI Reversal',
                'type'      => 'SHORT',
                'strength'  => (int)(($rsi - 50) * 2),
                'reason'    => 'RSI(14) = ' . round($rsi, 1) . ' (overbought)'
            );
        }
    }

    // 3. Breakout 24h — price above 24h high
    $max_high = 0;
    $lookback = min($n - 1, 24);
    for ($i = $n - 1 - $lookback; $i < $n - 1; $i++) {
        if ($i < 0) continue;
        if ($highs[$i] > $max_high) $max_high = $highs[$i];
    }
    if ($max_high > 0 && $price > $max_high) {
        $breakout_pct = (($price - $max_high) / $max_high) * 100;
        $signals[] = array(
            'algorithm' => 'Breakout 24h',
            'type'      => 'BUY',
            'strength'  => min(100, (int)($breakout_pct * 20 + 40)),
            'reason'    => 'Price above 24h high by ' . round($breakout_pct, 2) . '%'
        );
    }

    // 4. DCA Dip — 24h change < -5%
    if ($n > 24) {
        $old_close = $closes[$n - 25];
        if ($old_close > 0) {
            $dip = (($price - $old_close) / $old_close) * 100;
            if ($dip < -5) {
                $signals[] = array(
                    'algorithm' => 'DCA Dip',
                    'type'      => 'BUY',
                    'strength'  => min(100, (int)(abs($dip) * 8)),
                    'reason'    => '24h dip of ' . round($dip, 2) . '%'
                );
            }
        }
    }

    // 5. MACD Crossover
    if ($n >= 34) {
        $ema12 = _dm_calc_ema($closes, 12);
        $ema26 = _dm_calc_ema($closes, 26);
        if ($ema12 !== null && $ema26 !== null) {
            $macd_line = array();
            $count_min = min(count($ema12), count($ema26));
            $offset12 = count($ema12) - $count_min;
            $offset26 = count($ema26) - $count_min;
            for ($i = 0; $i < $count_min; $i++) {
                $macd_line[] = $ema12[$offset12 + $i] - $ema26[$offset26 + $i];
            }
            if (count($macd_line) >= 9) {
                $signal_line = _dm_calc_ema($macd_line, 9);
                if ($signal_line !== null && count($signal_line) >= 2) {
                    $sn = count($signal_line);
                    $mn = count($macd_line);
                    $ml_offset = $mn - $sn;
                    $cur_hist = $macd_line[$mn - 1] - $signal_line[$sn - 1];
                    $prev_hist = $macd_line[$mn - 2] - $signal_line[$sn - 2];
                    if ($prev_hist < 0 && $cur_hist > 0) {
                        $signals[] = array(
                            'algorithm' => 'MACD Crossover',
                            'type'      => 'BUY',
                            'strength'  => 55,
                            'reason'    => 'MACD crossed above signal line'
                        );
                    } elseif ($prev_hist > 0 && $cur_hist < 0) {
                        $signals[] = array(
                            'algorithm' => 'MACD Crossover',
                            'type'      => 'SHORT',
                            'strength'  => 55,
                            'reason'    => 'MACD crossed below signal line'
                        );
                    }
                }
            }
        }
    }

    // 6. Volume Spike — current volume > 2x average
    if ($n > 5) {
        $vol_sum = 0;
        for ($i = $n - 6; $i < $n - 1; $i++) {
            if ($i >= 0) $vol_sum += $volumes[$i];
        }
        $avg_vol = $vol_sum / 5;
        if ($avg_vol > 0 && $volumes[$n - 1] > $avg_vol * 2) {
            $vol_ratio = $volumes[$n - 1] / $avg_vol;
            $dir = ($closes[$n - 1] > $closes[$n - 2]) ? 'BUY' : 'SHORT';
            $signals[] = array(
                'algorithm' => 'Volume Spike',
                'type'      => $dir,
                'strength'  => min(100, (int)($vol_ratio * 15)),
                'reason'    => 'Volume ' . round($vol_ratio, 1) . 'x average'
            );
        }
    }

    // 7. Bollinger Squeeze — bandwidth squeeze + breakout
    if ($n >= 20) {
        $sma20 = 0;
        for ($i = $n - 20; $i < $n; $i++) $sma20 += $closes[$i];
        $sma20 /= 20;
        $variance = 0;
        for ($i = $n - 20; $i < $n; $i++) {
            $diff = $closes[$i] - $sma20;
            $variance += $diff * $diff;
        }
        $std = sqrt($variance / 20);
        $upper = $sma20 + 2 * $std;
        $lower = $sma20 - 2 * $std;
        $bandwidth = ($sma20 > 0) ? ($upper - $lower) / $sma20 * 100 : 0;
        if ($bandwidth < 3 && $price > $upper) {
            $signals[] = array(
                'algorithm' => 'Bollinger Squeeze',
                'type'      => 'BUY',
                'strength'  => 60,
                'reason'    => 'Bollinger squeeze breakout (bandwidth=' . round($bandwidth, 2) . '%)'
            );
        }
    }

    // 8. RSI(2) Scalp — ultra-short reversal
    $rsi2 = _dm_calc_rsi($closes, 2);
    if ($rsi2 !== null) {
        if ($rsi2 < 10) {
            $signals[] = array(
                'algorithm' => 'RSI(2) Scalp',
                'type'      => 'BUY',
                'strength'  => 65,
                'reason'    => 'RSI(2) = ' . round($rsi2, 1) . ' (extreme oversold)'
            );
        } elseif ($rsi2 > 90) {
            $signals[] = array(
                'algorithm' => 'RSI(2) Scalp',
                'type'      => 'SHORT',
                'strength'  => 65,
                'reason'    => 'RSI(2) = ' . round($rsi2, 1) . ' (extreme overbought)'
            );
        }
    }

    return $signals;
}


// =====================================================================
//  Technical indicator helpers
// =====================================================================

function _dm_calc_rsi($closes, $period) {
    $n = count($closes);
    if ($n < $period + 1) return null;

    $gains = 0;
    $losses = 0;
    for ($i = 1; $i <= $period; $i++) {
        $diff = $closes[$i] - $closes[$i - 1];
        if ($diff > 0) $gains += $diff;
        else $losses += abs($diff);
    }
    $avg_gain = $gains / $period;
    $avg_loss = $losses / $period;

    for ($i = $period + 1; $i < $n; $i++) {
        $diff = $closes[$i] - $closes[$i - 1];
        if ($diff > 0) {
            $avg_gain = ($avg_gain * ($period - 1) + $diff) / $period;
            $avg_loss = ($avg_loss * ($period - 1)) / $period;
        } else {
            $avg_gain = ($avg_gain * ($period - 1)) / $period;
            $avg_loss = ($avg_loss * ($period - 1) + abs($diff)) / $period;
        }
    }

    if ($avg_loss == 0) return 100;
    $rs = $avg_gain / $avg_loss;
    return 100 - (100 / (1 + $rs));
}

function _dm_calc_ema($data, $period) {
    $n = count($data);
    if ($n < $period) return null;

    $k = 2.0 / ($period + 1);
    $ema = array();

    // SMA for first value
    $sum = 0;
    for ($i = 0; $i < $period; $i++) $sum += $data[$i];
    $ema[] = $sum / $period;

    // EMA for rest
    for ($i = $period; $i < $n; $i++) {
        $ema[] = $data[$i] * $k + $ema[count($ema) - 1] * (1 - $k);
    }
    return $ema;
}


// =====================================================================
//  Sort helper
// =====================================================================
function _dm_sort_by_change($a, $b) {
    $aa = abs($a['change_24h_pct']);
    $bb = abs($b['change_24h_pct']);
    if ($aa == $bb) return 0;
    return ($aa > $bb) ? -1 : 1;
}


// =====================================================================
//  HTTP helper (same pattern as live_prices.php)
// =====================================================================
function _dm_http_get($url, $timeout) {
    if (!$timeout) $timeout = 10;

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
            return $body;
        }
    }

    $ctx = stream_context_create(array(
        'http' => array(
            'method'  => 'GET',
            'timeout' => $timeout,
            'header'  => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\nAccept: application/json\r\n"
        ),
        'ssl' => array('verify_peer' => false)
    ));
    $body = @file_get_contents($url, false, $ctx);
    if ($body === false) return null;
    return $body;
}
?>
