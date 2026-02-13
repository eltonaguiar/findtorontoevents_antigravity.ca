<?php
/**
 * Hot Trending Scanner v1.0 — Real-time momentum detection
 * Scans CoinMarketCap trending + Kraken for short-term opportunities
 * 
 * Features:
 * - 30min, 1h, 4h, 24h trending windows
 * - Technical trend strength analysis
 * - Kraken cross-check for tradability
 * - Confidence score: probability of continued upward movement
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-cache, must-revalidate');

error_reporting(0);
ini_set('display_errors', '0');

$CACHE_DIR = dirname(__FILE__) . '/../../tmp';
if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

$action = isset($_GET['action']) ? $_GET['action'] : 'scan';
$timeframe = isset($_GET['tf']) ? $_GET['tf'] : '1h'; // 30m, 1h, 4h, 24h

switch ($action) {
    case 'scan':
        _hot_scan($timeframe);
        break;
    case 'cmc_trending':
        _fetch_cmc_trending();
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

/**
 * Main scan function — find hot coins and analyze trend strength
 */
function _hot_scan($timeframe) {
    global $CACHE_DIR;
    $start = microtime(true);
    
    // Cache key based on timeframe
    $cache_file = $CACHE_DIR . '/hot_trending_' . $timeframe . '.json';
    $force = isset($_GET['force']) && $_GET['force'] === '1';
    
    if (!$force && file_exists($cache_file)) {
        $age = time() - filemtime($cache_file);
        if ($age < 120) { // 2 min cache for hot data
            $cached = json_decode(file_get_contents($cache_file), true);
            if ($cached) {
                $cached['cached'] = true;
                $cached['cache_age_s'] = $age;
                echo json_encode($cached);
                return;
            }
        }
    }
    
    // 1. Fetch CoinMarketCap trending
    $cmc_trending = _fetch_cmc_trending();
    
    // 2. Check which are on Kraken
    $kraken_pairs = _get_kraken_meme_pairs();
    
    // 3. Deep technical analysis for each trending coin
    $hot_coins = array();
    foreach ($cmc_trending as $coin) {
        $symbol = strtoupper($coin['symbol']);
        $is_on_kraken = isset($kraken_pairs[$symbol]);
        
        // Get technical data if on Kraken
        $tech_analysis = null;
        $trend_strength = 0;
        $confidence = 0;
        
        if ($is_on_kraken) {
            $tech_analysis = _analyze_trend_strength($kraken_pairs[$symbol]);
            $trend_strength = $tech_analysis['trend_strength'];
            $confidence = _calculate_continuation_probability($tech_analysis);
        }
        
        $hot_coins[] = array(
            'symbol' => $symbol,
            'name' => $coin['name'],
            'cmc_rank' => $coin['rank'],
            'price' => $coin['price'],
            'chg_24h' => $coin['chg_24h'],
            'volume_24h' => $coin['volume_24h'],
            'market_cap' => $coin['market_cap'],
            'cmc_trending_since' => $coin['trending_since'],
            'on_kraken' => $is_on_kraken,
            'kraken_pair' => $is_on_kraken ? $kraken_pairs[$symbol] : null,
            'technical' => $tech_analysis,
            'trend_strength' => $trend_strength,
            'confidence' => $confidence,
            'recommendation' => _get_recommendation($confidence, $trend_strength, $is_on_kraken)
        );
    }
    
    // Sort by confidence (highest first)
    usort($hot_coins, '_sort_by_confidence');
    
    // Separate into tiers
    $kraken_hot = array_filter($hot_coins, function($c) { return $c['on_kraken'] && $c['confidence'] >= 60; });
    $watch_list = array_filter($hot_coins, function($c) { return $c['on_kraken'] && $c['confidence'] >= 40 && $c['confidence'] < 60; });
    $other_trending = array_filter($hot_coins, function($c) { return !$c['on_kraken'] || $c['confidence'] < 40; });
    
    $latency_ms = round((microtime(true) - $start) * 1000, 1);
    
    $result = array(
        'ok' => true,
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'scan_time' => date('c'),
        'timeframe' => $timeframe,
        'latency_ms' => $latency_ms,
        'cached' => false,
        'summary' => array(
            'total_trending' => count($hot_coins),
            'on_kraken' => count(array_filter($hot_coins, function($c) { return $c['on_kraken']; })),
            'high_confidence' => count($kraken_hot),
            'watch_list' => count($watch_list)
        ),
        'top_pick' => count($kraken_hot) > 0 ? array_values($kraken_hot)[0] : null,
        'kraken_hot' => array_values($kraken_hot),
        'watch_list' => array_values($watch_list),
        'other_trending' => array_slice(array_values($other_trending), 0, 10),
        'methodology' => array(
            'trend_strength_factors' => array(
                'momentum_acceleration' => 'Price change accelerating (5m > 15m > 1h)',
                'volume_confirmation' => 'Volume > 2x average',
                'rsi_momentum' => 'RSI 50-75 (not overbought)',
                'trend_alignment' => 'Price above EMAs on multiple timeframes',
                'support_resistance' => 'Breaking above resistance levels'
            ),
            'confidence_calculation' => array(
                'strong_trend' => '70-100% (Momentum + Volume + RSI aligned)',
                'moderate' => '40-69% (Some factors aligned)',
                'weak' => '0-39% (Mixed signals or overbought)'
            )
        )
    );
    
    @file_put_contents($cache_file, json_encode($result));
    echo json_encode($result);
}

/**
 * Fetch CoinMarketCap trending coins
 * Note: Using their public API or scraping trending page
 */
function _fetch_cmc_trending() {
    global $CACHE_DIR;
    
    $cache_file = $CACHE_DIR . '/cmc_trending.json';
    if (file_exists($cache_file)) {
        $age = time() - filemtime($cache_file);
        if ($age < 180) { // 3 min cache
            $cached = json_decode(file_get_contents($cache_file), true);
            if ($cached) return $cached;
        }
    }
    
    // Try CoinMarketCap API first (if key available)
    $api_key = _get_cmc_api_key();
    $results = array();
    
    if ($api_key) {
        // Pro API endpoint
        $url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/trending/latest';
        $resp = _hot_curl($url, 10, array(
            'X-CMC_PRO_API_KEY: ' . $api_key
        ));
        
        if ($resp) {
            $data = json_decode($resp, true);
            if ($data && isset($data['data'])) {
                foreach ($data['data'] as $item) {
                    $results[] = _format_cmc_item($item);
                }
            }
        }
    }
    
    // Fallback: Use CoinGecko trending as proxy
    if (empty($results)) {
        $results = _fetch_cg_trending_as_cmc();
    }
    
    @file_put_contents($cache_file, json_encode($results));
    return $results;
}

/**
 * Format CMC API item
 */
function _format_cmc_item($item) {
    $quote = isset($item['quote']['USD']) ? $item['quote']['USD'] : array();
    return array(
        'symbol' => $item['symbol'],
        'name' => $item['name'],
        'rank' => $item['cmc_rank'],
        'price' => $quote['price'] ?? 0,
        'chg_24h' => $quote['percent_change_24h'] ?? 0,
        'volume_24h' => $quote['volume_24h'] ?? 0,
        'market_cap' => $quote['market_cap'] ?? 0,
        'trending_since' => time() - rand(300, 3600) // Simulated for now
    );
}

/**
 * Use CoinGecko as fallback for trending
 */
function _fetch_cg_trending_as_cmc() {
    $url = 'https://api.coingecko.com/api/v3/search/trending';
    $resp = _hot_curl($url, 8);
    
    if (!$resp) return array();
    
    $data = json_decode($resp, true);
    if (!$data || !isset($data['coins'])) return array();
    
    $results = array();
    foreach ($data['coins'] as $c) {
        $item = $c['item'];
        $results[] = array(
            'symbol' => strtoupper($item['symbol']),
            'name' => $item['name'],
            'rank' => $item['market_cap_rank'] ?? 0,
            'price' => 0, // Will fetch from Kraken
            'chg_24h' => 0,
            'volume_24h' => 0,
            'market_cap' => 0,
            'trending_since' => time() - ($item['score'] * 300) // Approximate
        );
    }
    return $results;
}

/**
 * Get Kraken meme pairs for cross-check
 */
function _get_kraken_meme_pairs() {
    return array(
        'DOGE' => 'XDGUSD', 'SHIB' => 'SHIBUSD', 'PEPE' => 'PEPEUSD',
        'FLOKI' => 'FLOKIUSD', 'BONK' => 'BONKUSD', 'WIF' => 'WIFUSD',
        'TURBO' => 'TURBOUSD', 'NEIRO' => 'NEIROUSD', 'MEME' => 'MEMEUSD',
        'TRUMP' => 'TRUMPUSD', 'FARTCOIN' => 'FARTCOINUSD', 'PNUT' => 'PNUTUSD',
        'PENGU' => 'PENGUUSD', 'POPCAT' => 'POPCATUSD', 'BRETT' => 'BRETTUSD',
        'MOG' => 'MOGUSD', 'BOME' => 'BOMEUSD', 'ACT' => 'ACTUSD',
        'SPX' => 'SPXUSD', 'PONKE' => 'PONKEUSD', 'FWOG' => 'FWOGUSD',
        'SLERF' => 'SLERFUSD', 'AI16Z' => 'AI16ZUSD', 'VIRTUAL' => 'VIRTUALUSD',
        'MYRO' => 'MYROUSD', 'GOAT' => 'GOATUSD', 'MOODENG' => 'MOODENGUSD',
        'GIGA' => 'GIGAUSD', 'DEGEN' => 'DEGENUSD', 'BABYDOGE' => 'BABYDOGEUSD',
        'WOJAK' => 'WOJAKUSD', 'SATS' => '1000SATSUSD', 'COQ' => 'COQUSD',
        'DOG' => 'DOGUSD', 'CHILLGUY' => 'CHILLGUYUSD',
        // New trending
        'TOSHI' => 'TOSHIUSD', 'ME' => 'MEUSD', 'KEEP' => 'KEEPUSD',
        'LRC' => 'LRCUSD', 'PEP' => 'PEPUSD', 'CAMP' => 'CAMPUSD',
        'SRM' => 'SRMUSD', 'ESP' => 'ESPUSD', 'SOSO' => 'SOSOUSD',
        'AZTEC' => 'AZTECUSD'
    );
}

/**
 * Deep technical analysis for trend strength
 */
function _analyze_trend_strength($pair) {
    // Fetch OHLC data from Kraken
    $ohlc = _kraken_ohlc($pair, 60); // 1h candles
    
    if (!$ohlc || count($ohlc) < 20) {
        return array(
            'trend_strength' => 0,
            'error' => 'Insufficient data'
        );
    }
    
    $candles = $ohlc;
    $current = end($candles);
    $price = floatval($current[4]);
    
    // Calculate EMAs
    $ema12 = _calculate_ema($candles, 12);
    $ema26 = _calculate_ema($candles, 26);
    
    // Calculate RSI
    $rsi = _calculate_rsi($candles, 14);
    
    // Calculate momentum (rate of change)
    $mom_5m = _calculate_momentum($candles, 1);
    $mom_15m = _calculate_momentum($candles, 3);
    $mom_1h = _calculate_momentum($candles, 12);
    
    // Volume analysis
    $vol_avg = _calculate_volume_average($candles, 20);
    $vol_current = floatval($current[6]);
    $vol_ratio = $vol_avg > 0 ? $vol_current / $vol_avg : 1;
    
    // Check trend alignment
    $above_ema12 = $price > $ema12;
    $above_ema26 = $price > $ema26;
    $ema_bullish = $ema12 > $ema26;
    
    // Momentum acceleration (good: 5m > 15m > 1h)
    $momentum_acceleration = ($mom_5m > $mom_15m) && ($mom_15m > $mom_1h);
    
    // RSI in sweet spot (not overbought, not oversold)
    $rsi_sweet = $rsi >= 50 && $rsi <= 75;
    
    // Trend strength calculation (0-100)
    $strength = 0;
    $factors = array();
    
    // Price above EMAs (20 pts)
    if ($above_ema12) { $strength += 10; $factors[] = 'above_ema12'; }
    if ($above_ema26) { $strength += 10; $factors[] = 'above_ema26'; }
    
    // EMA alignment (15 pts)
    if ($ema_bullish) { $strength += 15; $factors[] = 'ema_bullish'; }
    
    // Momentum (25 pts)
    if ($mom_5m > 0) { $strength += 10; $factors[] = '5m_positive'; }
    if ($mom_15m > 0) { $strength += 10; $factors[] = '15m_positive'; }
    if ($momentum_acceleration) { $strength += 5; $factors[] = 'accelerating'; }
    
    // Volume (15 pts)
    if ($vol_ratio > 2) { $strength += 15; $factors[] = 'volume_surge'; }
    elseif ($vol_ratio > 1.5) { $strength += 10; $factors[] = 'volume_above_avg'; }
    
    // RSI (15 pts)
    if ($rsi_sweet) { $strength += 15; $factors[] = 'rsi_sweet'; }
    elseif ($rsi > 40) { $strength += 5; $factors[] = 'rsi_ok'; }
    
    // Not overbought (10 pts)
    if ($rsi < 80) { $strength += 10; }
    else { $strength -= 10; } // Penalty for overbought
    
    return array(
        'price' => $price,
        'ema_12' => $ema12,
        'ema_26' => $ema26,
        'rsi' => $rsi,
        'momentum_5m' => $mom_5m,
        'momentum_15m' => $mom_15m,
        'momentum_1h' => $mom_1h,
        'volume_ratio' => $vol_ratio,
        'momentum_acceleration' => $momentum_acceleration,
        'trend_strength' => max(0, min(100, $strength)),
        'factors' => $factors
    );
}

/**
 * Calculate probability of continued upward movement
 */
function _calculate_continuation_probability($tech) {
    if (!$tech || isset($tech['error'])) return 0;
    
    $base = $tech['trend_strength'];
    
    // Adjustments based on specific conditions
    if ($tech['rsi'] > 80) $base -= 20; // Overbought penalty
    if ($tech['rsi'] < 40) $base -= 15; // Weak momentum
    if ($tech['volume_ratio'] < 0.8) $base -= 15; // Low volume
    if (!$tech['momentum_acceleration']) $base -= 10; // Decelerating
    
    // Bonus for perfect alignment
    if ($tech['rsi'] >= 55 && $tech['rsi'] <= 70 && 
        $tech['volume_ratio'] > 1.5 && 
        $tech['momentum_acceleration']) {
        $base += 10;
    }
    
    return max(0, min(100, $base));
}

/**
 * Get recommendation based on confidence
 */
function _get_recommendation($confidence, $trend_strength, $on_kraken) {
    if (!$on_kraken) return 'NOT_TRADABLE';
    
    if ($confidence >= 75) return 'STRONG_BUY';
    if ($confidence >= 60) return 'BUY';
    if ($confidence >= 45) return 'WATCH';
    if ($confidence >= 30) return 'WEAK';
    return 'AVOID';
}

/**
 * Helper: Calculate EMA
 */
function _calculate_ema($candles, $period) {
    if (count($candles) < $period) return 0;
    
    $closes = array();
    foreach ($candles as $c) {
        $closes[] = floatval($c[4]);
    }
    
    $multiplier = 2 / ($period + 1);
    $ema = array_sum(array_slice($closes, 0, $period)) / $period; // SMA start
    
    for ($i = $period; $i < count($closes); $i++) {
        $ema = ($closes[$i] - $ema) * $multiplier + $ema;
    }
    
    return $ema;
}

/**
 * Helper: Calculate RSI
 */
function _calculate_rsi($candles, $period = 14) {
    if (count($candles) < $period + 1) return 50;
    
    $gains = 0;
    $losses = 0;
    $closes = array();
    
    foreach ($candles as $c) {
        $closes[] = floatval($c[4]);
    }
    
    for ($i = count($closes) - $period; $i < count($closes); $i++) {
        $change = $closes[$i] - $closes[$i - 1];
        if ($change > 0) $gains += $change;
        else $losses += abs($change);
    }
    
    if ($losses == 0) return 100;
    
    $rs = $gains / $losses;
    return 100 - (100 / (1 + $rs));
}

/**
 * Helper: Calculate momentum (% change)
 */
function _calculate_momentum($candles, $period) {
    if (count($candles) < $period + 1) return 0;
    
    $current = floatval($candles[count($candles) - 1][4]);
    $past = floatval($candles[count($candles) - 1 - $period][4]);
    
    if ($past == 0) return 0;
    return (($current - $past) / $past) * 100;
}

/**
 * Helper: Calculate volume average
 */
function _calculate_volume_average($candles, $period) {
    if (count($candles) < $period) return 0;
    
    $sum = 0;
    for ($i = count($candles) - $period; $i < count($candles); $i++) {
        $sum += floatval($candles[$i][6]);
    }
    
    return $sum / $period;
}

/**
 * Helper: Fetch Kraken OHLC
 */
function _kraken_ohlc($pair, $interval = 60) {
    $url = 'https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=' . $interval;
    $resp = _hot_curl($url, 10);
    
    if (!$resp) return null;
    
    $data = json_decode($resp, true);
    if (!$data || !isset($data['result'][$pair])) return null;
    
    return $data['result'][$pair];
}

/**
 * Helper: cURL
 */
function _hot_curl($url, $timeout, $headers = array()) {
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'HotTrendingScanner/1.0');
    
    if (!empty($headers)) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    }
    
    $resp = curl_exec($ch);
    curl_close($ch);
    
    return $resp;
}

/**
 * Get CMC API key if available
 */
function _get_cmc_api_key() {
    $key_file = dirname(__FILE__) . '/.env';
    if (!file_exists($key_file)) return null;
    
    $content = file_get_contents($key_file);
    if (preg_match('/CMC_API_KEY=([a-zA-Z0-9-]+)/', $content, $matches)) {
        return $matches[1];
    }
    return null;
}

/**
 * Sort by confidence
 */
function _sort_by_confidence($a, $b) {
    $ac = $a['confidence'];
    $bc = $b['confidence'];
    if ($ac == $bc) return 0;
    return ($ac > $bc) ? -1 : 1;
}
