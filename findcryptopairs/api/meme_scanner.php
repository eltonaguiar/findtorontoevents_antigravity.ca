<?php
/**
 * Meme Coin Scanner — high-volatility, short-term momentum plays
 * Uses Crypto.com Exchange public API (no auth needed)
 *
 * Actions:
 *   scan          — scan meme coins, score, return top winners (key required)
 *   winners       — get latest cached winners (public)
 *   history       — get past scans + outcomes (public)
 *   resolve       — check if past winners actually went up (key required)
 *   leaderboard   — best patterns by win rate (public)
 *   stats         — overall scanner stats (public)
 *   scan_log      — full analysis log with all indicators (public)
 *
 * PHP 5.2 compatible. No short arrays, no http_response_code().
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

// Dedicated meme coin database (separate from stocks)
error_reporting(0);
ini_set('display_errors', '0');
$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed'));
    exit;
}
$conn->set_charset('utf8');

$action = isset($_GET['action']) ? $_GET['action'] : 'winners';
$key = isset($_GET['key']) ? $_GET['key'] : '';
$ADMIN_KEY = 'memescan2026';

// Tier 1: established meme coins (always scanned — NO filters applied)
$MEME_TIER1 = array(
    'DOGE_USDT',
    'SHIB_USDT',
    'PEPE_USDT',
    'FLOKI_USDT',
    'BONK_USDT',
    'WIF_USDT',
    'TURBO_USDT',
    'NEIRO_USDT'
);

// CoinGecko IDs for Tier 1 (fallback when not on Crypto.com Exchange)
$CG_TIER1_IDS = array(
    'DOGE_USDT' => 'dogecoin',
    'SHIB_USDT' => 'shiba-inu',
    'PEPE_USDT' => 'pepe',
    'FLOKI_USDT' => 'floki',
    'BONK_USDT' => 'bonk',
    'WIF_USDT' => 'dogwifhat',
    'TURBO_USDT' => 'turbo',
    'NEIRO_USDT' => 'neiro-3'
);

// Meme keyword fragments for dynamic discovery (Kimi: expanded from 27→55+)
$MEME_KEYWORDS = array(
    // Original 27
    'DOGE',
    'SHIB',
    'INU',
    'PEPE',
    'FLOKI',
    'BONK',
    'WIF',
    'MEME',
    'BABY',
    'MOON',
    'ELON',
    'CAT',
    'DOG',
    'NEIRO',
    'TURBO',
    'BRETT',
    'MOG',
    'POPCAT',
    'MYRO',
    'SLERF',
    'BOME',
    'WOJAK',
    'LADYS',
    'SATS',
    'ORDI',
    'COQ',
    'TOSHI',
    // 2025-2026 meme cycle additions
    'PNUT',
    'GOAT',
    'ACT',
    'CHILLGUY',
    'SPX',
    'GIGA',
    'PONKE',
    'NEIROCTO',
    'PORK',
    'BODEN',
    'TREMP',
    'TRUMP',
    'FWOG',
    'MICHI',
    'WENMOON',
    'NEKO',
    'HAMSTER',
    'CATE',
    'DEGEN',
    'CHAD',
    'BASED',
    'RIZZ',
    'SNAIL',
    'TOAD',
    'APE',
    'PIG',
    'BEAR',
    'BULL',
    'FROG'
);

_mc_ensure_schema($conn);

switch ($action) {
    case 'scan':
        if ($key !== $ADMIN_KEY) {
            _mc_err('Unauthorized');
        }
        _mc_action_scan($conn);
        break;
    case 'winners':
        _mc_action_winners($conn);
        break;
    case 'history':
        _mc_action_history($conn);
        break;
    case 'resolve':
        if ($key !== $ADMIN_KEY) {
            _mc_err('Unauthorized');
        }
        _mc_action_resolve($conn);
        break;
    case 'leaderboard':
        _mc_action_leaderboard($conn);
        break;
    case 'stats':
        _mc_action_stats($conn);
        break;
    case 'scan_log':
        _mc_action_scan_log($conn);
        break;
    case 'daily_picks':
        _mc_action_daily_picks($conn);
        break;
    case 'performance':
        _mc_action_performance($conn);
        break;
    case 'snapshot':
        if ($key !== $ADMIN_KEY) {
            _mc_err('Unauthorized');
        }
        _mc_action_snapshot($conn);
        break;
    case 'adaptive_weights':
        if ($key !== $ADMIN_KEY) {
            _mc_err('Unauthorized');
        }
        _mc_action_adaptive_weights($conn);
        break;
    case 'ml_status':
        _mc_action_ml_status($conn);
        break;
    default:
        _mc_err('Unknown action: ' . $action);
}

// ═══════════════════════════════════════════════════════════════════════
//  SCAN — the meme engine
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_scan($conn)
{
    global $MEME_TIER1, $MEME_KEYWORDS, $CG_TIER1_IDS;
    $start = microtime(true);

    // ── CIRCUIT BREAKER: pause scanning if recent performance is terrible ──
    // If win rate < 15% over last 7 days with 3+ resolved trades, skip scan entirely.
    $cb_res = $conn->query("SELECT COUNT(*) as total,
        SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins
        FROM mc_winners WHERE outcome IS NOT NULL
        AND resolved_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)");
    if ($cb_res) {
        $cb = $cb_res->fetch_assoc();
        $cb_total = intval($cb['total']);
        $cb_wins = intval($cb['wins']);
        if ($cb_total >= 3 && $cb_total > 0) {
            $cb_wr = ($cb_wins / $cb_total) * 100;
            if ($cb_wr < 15) {
                echo json_encode(array(
                    'ok' => true,
                    'scan_id' => 'PAUSED',
                    'circuit_breaker' => true,
                    'reason' => 'Scanning paused: 7-day win rate is ' . round($cb_wr, 1) . '% (' . $cb_wins . '/' . $cb_total . ' wins). Minimum 15% required to resume.',
                    'recent_win_rate' => round($cb_wr, 1),
                    'recent_trades' => $cb_total,
                    'winners_found' => 0,
                    'winners_saved' => 0,
                    'winners' => array()
                ));
                return;
            }
        }
    }

    // ── PHASE 1: Crypto.com Exchange data ──
    $instruments = _mc_api('public/get-instruments');
    $all_usdt_pairs = array();
    if ($instruments && isset($instruments['result']['data'])) {
        foreach ($instruments['result']['data'] as $inst) {
            $sym = isset($inst['symbol']) ? $inst['symbol'] : (isset($inst['instrument_name']) ? $inst['instrument_name'] : '');
            $itype = isset($inst['inst_type']) ? $inst['inst_type'] : '';
            if ($itype === 'CCY_PAIR' && _mc_ends_with($sym, '_USDT')) {
                $all_usdt_pairs[] = $sym;
            }
        }
    }

    $tickers_raw = _mc_api('public/get-tickers');
    $tickers = array();
    if ($tickers_raw && isset($tickers_raw['result']['data'])) {
        foreach ($tickers_raw['result']['data'] as $t) {
            $k = isset($t['i']) ? $t['i'] : (isset($t['symbol']) ? $t['symbol'] : '');
            if ($k)
                $tickers[$k] = $t;
        }
    }

    // ── PHASE 2: CoinGecko meme discovery (aggregated across ALL exchanges) ──
    $cg_memes = _mc_coingecko_meme_market();

    // ── PHASE 3: Build candidate list ──
    $candidates = array();
    $tier1_found = 0;
    $tier2_found = 0;
    $seen_pairs = array();

    // Tier 1: established memes — ALWAYS include, NO volume/change filters
    foreach ($MEME_TIER1 as $meme) {
        $has_cc = isset($tickers[$meme]);
        $cg_match = _mc_find_cg_match($meme, $cg_memes, $CG_TIER1_IDS);

        if (!$has_cc && !$cg_match)
            continue;

        if ($has_cc) {
            $t = $tickers[$meme];
            $price = isset($t['a']) ? floatval($t['a']) : 0;
            $volUsd = isset($t['vv']) ? floatval($t['vv']) : (floatval(isset($t['v']) ? $t['v'] : 0) * $price);
            $chg24 = isset($t['c']) ? floatval($t['c']) * 100 : 0;
            // Use CoinGecko aggregate volume if available (much more representative)
            if ($cg_match && $cg_match['total_volume'] > $volUsd) {
                $volUsd = floatval($cg_match['total_volume']);
                $chg24 = floatval($cg_match['price_change_percentage_24h']);
            }
        } else {
            $price = floatval($cg_match['current_price']);
            $volUsd = floatval($cg_match['total_volume']);
            $chg24 = floatval($cg_match['price_change_percentage_24h']);
        }

        $candidates[] = array(
            'pair' => $meme,
            'price' => $price,
            'vol_usd' => $volUsd,
            'chg_24h' => $chg24,
            'high_24h' => $has_cc && isset($tickers[$meme]['h']) ? floatval($tickers[$meme]['h']) : ($cg_match ? floatval($cg_match['high_24h']) : $price),
            'low_24h' => $has_cc && isset($tickers[$meme]['l']) ? floatval($tickers[$meme]['l']) : ($cg_match ? floatval($cg_match['low_24h']) : $price),
            'tier' => 'tier1',
            'source' => $has_cc ? 'crypto_com' : 'coingecko',
            'cg_id' => $cg_match ? $cg_match['id'] : (isset($CG_TIER1_IDS[$meme]) ? $CG_TIER1_IDS[$meme] : null),
            'has_cc' => $has_cc
        );
        $seen_pairs[$meme] = true;
        $tier1_found++;
    }

    // Tier 2 from Crypto.com: relaxed filters
    $tier2_pool = array();
    foreach ($all_usdt_pairs as $pair) {
        if (isset($seen_pairs[$pair]))
            continue;
        if (!isset($tickers[$pair]))
            continue;

        $t = $tickers[$pair];
        $price = isset($t['a']) ? floatval($t['a']) : 0;
        $volUsd = isset($t['vv']) ? floatval($t['vv']) : (floatval(isset($t['v']) ? $t['v'] : 0) * $price);
        $chg24 = isset($t['c']) ? floatval($t['c']) * 100 : 0;

        if ($chg24 < 2)
            continue;          // relaxed from 5% to 2%
        if ($volUsd < 25000)
            continue;      // relaxed from 100K to 25K
        if ($volUsd > 500000000)
            continue;

        $is_meme = false;
        $base = str_replace('_USDT', '', $pair);
        foreach ($MEME_KEYWORDS as $kw) {
            if (strpos($base, $kw) !== false) {
                $is_meme = true;
                break;
            }
        }
        $is_extreme_pump = ($chg24 >= 10 && $volUsd >= 100000);
        if (!$is_meme && !$is_extreme_pump)
            continue;

        $tier2_pool[] = array(
            'pair' => $pair,
            'price' => $price,
            'vol_usd' => $volUsd,
            'chg_24h' => $chg24,
            'high_24h' => isset($t['h']) ? floatval($t['h']) : $price,
            'low_24h' => isset($t['l']) ? floatval($t['l']) : $price,
            'tier' => 'tier2',
            'source' => 'crypto_com',
            'cg_id' => null,
            'has_cc' => true
        );
    }

    // Tier 2 from CoinGecko: find pumping meme coins not already seen
    foreach ($cg_memes as $cg) {
        $pair = strtoupper($cg['symbol']) . '_USDT';
        if (isset($seen_pairs[$pair]))
            continue;

        $vol = floatval($cg['total_volume']);
        $chg24 = floatval($cg['price_change_percentage_24h']);
        $mcap = floatval($cg['market_cap']);

        // CoinGecko Tier 2 filters (these are aggregate volumes, so higher thresholds)
        if ($chg24 < 3)
            continue;
        if ($vol < 1000000)
            continue;        // $1M aggregate min
        if ($mcap > 10000000000)
            continue;   // skip $10B+ (BTC, ETH not in meme category anyway)

        $tier2_pool[] = array(
            'pair' => $pair,
            'price' => floatval($cg['current_price']),
            'vol_usd' => $vol,
            'chg_24h' => $chg24,
            'high_24h' => floatval($cg['high_24h']),
            'low_24h' => floatval($cg['low_24h']),
            'tier' => 'tier2',
            'source' => isset($tickers[$pair]) ? 'crypto_com' : 'coingecko',
            'cg_id' => $cg['id'],
            'has_cc' => isset($tickers[$pair])
        );
        $seen_pairs[$pair] = true;
    }

    usort($tier2_pool, '_mc_sort_by_change');
    $tier2_pool = array_slice($tier2_pool, 0, 15);
    foreach ($tier2_pool as $t2) {
        $candidates[] = $t2;
        $seen_pairs[$t2['pair']] = true;
        $tier2_found++;
    }

    // ── PHASE 3.5: Detect BTC regime for adaptive scoring (Kimi P0) ──
    $btc_regime = _mc_detect_btc_regime();

    // ── PHASE 4: Deep analysis with candles ──
    $scored = array();
    foreach ($candidates as $c) {
        $c15m = array();
        $c5m = array();
        $has_volume_data = false;

        // Try Crypto.com candles first (best: 5m + 15m with volume)
        if ($c['has_cc']) {
            $candles_15m = _mc_api('public/get-candlestick?instrument_name=' . $c['pair'] . '&timeframe=M15');
            $candles_5m = _mc_api('public/get-candlestick?instrument_name=' . $c['pair'] . '&timeframe=M5');
            $c15m = isset($candles_15m['result']['data']) ? $candles_15m['result']['data'] : array();
            $c5m = isset($candles_5m['result']['data']) ? $candles_5m['result']['data'] : array();
            $has_volume_data = (count($c15m) >= 8);
        }

        // Fallback to CoinGecko OHLC (30-min candles, no volume)
        if (count($c15m) < 8 && isset($c['cg_id']) && $c['cg_id']) {
            $cg_ohlc = _mc_coingecko_ohlc($c['cg_id']);
            if (count($cg_ohlc) >= 8) {
                $c15m = $cg_ohlc;
                $c5m = $cg_ohlc; // same granularity, less ideal but functional
                $has_volume_data = false;
            }
        }

        if (count($c15m) < 8)
            continue;
        if (count($c5m) < 8)
            $c5m = $c15m;

        $score_details = _mc_score_pair($c, $c15m, $c5m, $has_volume_data);

        // Kimi: Apply BTC regime adjustment to score
        $raw_score = $score_details['total'];
        $regime_adj = _mc_regime_score_adjust($raw_score, $score_details['factors'], $btc_regime);
        $score_details['total'] = $regime_adj['adjusted_score'];
        $score_details['factors']['btc_regime'] = array(
            'regime' => $btc_regime['regime'],
            'btc_trend_pct' => $btc_regime['trend_pct'],
            'adjustment' => $regime_adj['adjustment'],
            'raw_score' => $raw_score
        );
        // Re-evaluate verdict with adjusted score (v3 thresholds)
        $adj = $score_details['total'];
        if ($adj >= 88) {
            $score_details['verdict'] = 'STRONG_BUY';
        } elseif ($adj >= 82) {
            $score_details['verdict'] = 'BUY';
        } elseif ($adj >= 78) {
            $score_details['verdict'] = 'LEAN_BUY';
        } else {
            $score_details['verdict'] = 'SKIP';
        }

        $c['score'] = $score_details['total'];
        $c['factors'] = $score_details['factors'];
        $c['verdict'] = $score_details['verdict'];
        $c['target_pct'] = $score_details['target_pct'];
        $c['risk_pct'] = $score_details['risk_pct'];

        $scored[] = $c;
    }

    usort($scored, '_mc_sort_by_score');

    // 5. Save winners (score >= 78) to DB — raised from 70 to match v3 thresholds
    $scan_id = date('YmdHis');
    $winners = array();
    $saved = 0;

    foreach ($scored as $s) {
        if ($s['score'] < 78)
            continue;
        $winners[] = $s;

        $esc_pair = $conn->real_escape_string($s['pair']);
        $esc_scan = $conn->real_escape_string($scan_id);
        $esc_factors = $conn->real_escape_string(json_encode($s['factors']));
        $esc_verdict = $conn->real_escape_string($s['verdict']);
        $esc_tier = $conn->real_escape_string($s['tier']);

        $sql = "INSERT INTO mc_winners (scan_id, pair, price_at_signal, score, factors_json, verdict, target_pct, risk_pct, vol_usd_24h, chg_24h, tier, created_at)
                VALUES ('$esc_scan', '$esc_pair', " . floatval($s['price']) . ", " . intval($s['score']) . ", '$esc_factors', '$esc_verdict', " . floatval($s['target_pct']) . ", " . floatval($s['risk_pct']) . ", " . floatval($s['vol_usd']) . ", " . floatval($s['chg_24h']) . ", '$esc_tier', NOW())";
        $conn->query($sql);
        $saved++;
    }

    $elapsed = round(microtime(true) - $start, 2);

    // Discord alert for strong meme signals
    if (count($winners) > 0) {
        _mc_discord_alert($winners, $scan_id, count($scored), $elapsed);
    }

    // Save ALL analyzed to scan_log (with Kraken eligibility)
    $kraken_lookup = _mc_get_kraken_lookup();
    foreach ($scored as $s) {
        $esc_pair_log = $conn->real_escape_string($s['pair']);
        $esc_scan_log = $conn->real_escape_string($scan_id);
        $esc_factors_log = $conn->real_escape_string(json_encode($s['factors']));
        $esc_verdict_log = $conn->real_escape_string($s['verdict']);
        $esc_tier_log = $conn->real_escape_string($s['tier']);
        $base_sym = strtoupper(str_replace('_USDT', '', $s['pair']));
        $is_on_kraken = isset($kraken_lookup[$base_sym]) ? 1 : 0;
        $sql_log = "INSERT INTO mc_scan_log (scan_id, pair, price, score, factors_json, verdict, chg_24h, vol_usd_24h, tier, on_kraken, created_at)
                    VALUES ('$esc_scan_log', '$esc_pair_log', " . floatval($s['price']) . ", " . intval($s['score']) . ", '$esc_factors_log', '$esc_verdict_log', " . floatval($s['chg_24h']) . ", " . floatval($s['vol_usd']) . ", '$esc_tier_log', $is_on_kraken, NOW())";
        $conn->query($sql_log);
    }

    $top_candidates = array();
    foreach (array_slice($scored, 0, 10) as $tc) {
        $top_candidates[] = array(
            'pair' => $tc['pair'],
            'score' => $tc['score'],
            'verdict' => $tc['verdict'],
            'tier' => $tc['tier'],
            'chg_24h' => round($tc['chg_24h'], 2),
            'vol_usd' => round($tc['vol_usd'], 0),
            'source' => isset($tc['source']) ? $tc['source'] : 'crypto_com'
        );
    }

    echo json_encode(array(
        'ok' => true,
        'scan_id' => $scan_id,
        'total_usdt_pairs' => count($all_usdt_pairs),
        'coingecko_memes' => count($cg_memes),
        'tier1_found' => $tier1_found,
        'tier2_found' => $tier2_found,
        'deep_analyzed' => count($scored),
        'winners_found' => count($winners),
        'winners_saved' => $saved,
        'btc_regime' => $btc_regime['regime'],
        'btc_trend_pct' => $btc_regime['trend_pct'],
        'elapsed_sec' => $elapsed,
        'winners' => array_slice($winners, 0, 15),
        'top_candidates' => $top_candidates
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  SCORING ENGINE — meme-specific factors (ACCURACY IMPROVED v2)
// ═══════════════════════════════════════════════════════════════════════
function _mc_score_pair($candidate, $candles_15m, $candles_5m, $has_volume_data = true)
{
    $total = 0;
    $factors = array();
    $current_price = $candidate['price'];
    $vol_usd = $candidate['vol_usd'];

    // NEW: Quality gates - must pass these to be considered at all
    $quality_score = 0;
    $quality_issues = array();

    // Extract close prices — handle both Crypto.com objects and CoinGecko arrays
    $closes_15m = array();
    $volumes_15m = array();
    $highs_15m = array();
    $lows_15m = array();
    foreach ($candles_15m as $c) {
        if (is_array($c) && isset($c[4])) {
            // CoinGecko format: [timestamp, open, high, low, close]
            $closes_15m[] = floatval($c[4]);
            $highs_15m[] = floatval($c[2]);
            $lows_15m[] = floatval($c[3]);
            $volumes_15m[] = 0; // CoinGecko OHLC has no volume
        } else {
            // Crypto.com format: {t, o, h, l, c, v}
            $closes_15m[] = floatval($c['c']);
            $highs_15m[] = floatval($c['h']);
            $lows_15m[] = floatval($c['l']);
            $volumes_15m[] = floatval(isset($c['v']) ? $c['v'] : 0);
        }
    }
    $closes_5m = array();
    foreach ($candles_5m as $c) {
        if (is_array($c) && isset($c[4])) {
            $closes_5m[] = floatval($c[4]);
        } else {
            $closes_5m[] = floatval($c['c']);
        }
    }

    $n15 = count($closes_15m);
    $n5 = count($closes_5m);

    // ═══════════════════════════════════════════════════════════════════════
    //  PUMP-AND-DUMP DETECTION — hard reject before quality gates
    //  Saves processing time by rejecting obvious P&D patterns early
    // ═══════════════════════════════════════════════════════════════════════
    $pnd_result = _mc_detect_pump_and_dump($closes_15m, $closes_5m, $highs_15m, $lows_15m, $volumes_15m, $candidate);
    $factors['pump_dump'] = $pnd_result;

    if ($pnd_result['detected']) {
        // 2+ P&D signals = hard reject — do not generate a signal
        return null;
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  QUALITY GATE 1: Trend Confirmation (NEW)
    //  Price must be above 1-hour EMA (8 periods of 15m = 2h trend)
    // ═══════════════════════════════════════════════════════════════════════
    $ema8 = _mc_calc_ema($closes_15m, 8);
    $trend_aligned = ($current_price > $ema8);
    $factors['trend_confirm'] = array(
        'ema8' => round($ema8, 8),
        'price' => round($current_price, 8),
        'aligned' => $trend_aligned
    );
    if (!$trend_aligned) {
        $quality_issues[] = 'below_ema8';
    } else {
        $quality_score += 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  QUALITY GATE 2: Momentum Direction (NEW)
    //  Must have positive momentum on both timeframes
    // ═══════════════════════════════════════════════════════════════════════
    $mom_15m = ($n15 >= 4 && $closes_15m[$n15 - 4] > 0) ?
        (($closes_15m[$n15 - 1] - $closes_15m[$n15 - 4]) / $closes_15m[$n15 - 4]) * 100 : 0;
    $mom_5m = ($n5 >= 6 && $closes_5m[$n5 - 6] > 0) ?
        (($closes_5m[$n5 - 1] - $closes_5m[$n5 - 6]) / $closes_5m[$n5 - 6]) * 100 : 0;

    $momentum_positive = ($mom_15m > 0.5 && $mom_5m > 0.3);
    $factors['momentum_gate'] = array(
        'mom_15m' => round($mom_15m, 2),
        'mom_5m' => round($mom_5m, 2),
        'passed' => $momentum_positive
    );
    if (!$momentum_positive) {
        $quality_issues[] = 'weak_momentum';
    } else {
        $quality_score += 1;
    }

    // ═══════════════════════════════════════════════════════════════════════
    //  QUALITY GATE 3: Volume Confirmation (NEW)
    //  Must show volume increase (not just high aggregate volume)
    // ═══════════════════════════════════════════════════════════════════════
    $volume_increasing = true;
    if ($has_volume_data && count($volumes_15m) >= 6) {
        $recent_vol = array_sum(array_slice($volumes_15m, -3)) / 3;
        $prev_vol = array_sum(array_slice($volumes_15m, -6, 3)) / 3;
        $volume_increasing = ($recent_vol > $prev_vol * 1.2); // 20% increase
        $factors['volume_gate'] = array(
            'recent_vol' => round($recent_vol, 2),
            'prev_vol' => round($prev_vol, 2),
            'ratio' => round($recent_vol / ($prev_vol > 0 ? $prev_vol : 1), 2),
            'passed' => $volume_increasing
        );
        if (!$volume_increasing) {
            $quality_issues[] = 'volume_fading';
        } else {
            $quality_score += 1;
        }
    }

    // ── Factor 1: Explosive Volume (0-25 pts) ──
    // Compare recent volume to average (candle data) or use aggregate volume rank (CoinGecko)
    $vol_score = 0;
    if ($has_volume_data && count($volumes_15m) >= 10) {
        $vol_count = count($volumes_15m);
        $avg_vol = array_sum($volumes_15m) / $vol_count;
        $recent_3 = array_slice($volumes_15m, -3);
        $recent_vol = array_sum($recent_3) / 3;

        $vol_ratio = ($avg_vol > 0) ? $recent_vol / $avg_vol : 1;

        if ($vol_ratio >= 10)
            $vol_score = 25;
        elseif ($vol_ratio >= 5)
            $vol_score = 18;
        elseif ($vol_ratio >= 3)
            $vol_score = 12;
        elseif ($vol_ratio >= 2)
            $vol_score = 8;
        elseif ($vol_ratio >= 1.5)
            $vol_score = 4;

        $factors['explosive_volume'] = array(
            'score' => $vol_score,
            'max' => 25,
            'ratio' => round($vol_ratio, 1),
            'recent_avg' => round($recent_vol, 2),
            'method' => 'candle'
        );
    } else {
        // No per-candle volume — use 24h aggregate volume as proxy
        // Award points based on volume tier (higher aggregate vol = more interest)
        if ($vol_usd >= 100000000)
            $vol_score = 20;       // $100M+ = very active meme
        elseif ($vol_usd >= 50000000)
            $vol_score = 15;
        elseif ($vol_usd >= 10000000)
            $vol_score = 10;
        elseif ($vol_usd >= 1000000)
            $vol_score = 6;
        elseif ($vol_usd >= 100000)
            $vol_score = 3;

        $factors['explosive_volume'] = array(
            'score' => $vol_score,
            'max' => 25,
            'vol_usd_24h' => round($vol_usd, 0),
            'method' => 'aggregate'
        );
    }
    $total += $vol_score;

    // ── Factor 2: Parabolic Momentum (0-20 pts) — IMPROVED v2 ──
    // Steep price acceleration on 15m + 5m with stricter thresholds
    $mom_score = 0;
    if ($n15 >= 4 && $n5 >= 6) {
        // 15m momentum: last 4 candles (~1 hour)
        $mom_15m = ($closes_15m[$n15 - 4] > 0) ? (($closes_15m[$n15 - 1] - $closes_15m[$n15 - 4]) / $closes_15m[$n15 - 4]) * 100 : 0;
        // 5m momentum: last 6 candles (~30 min)
        $mom_5m = ($closes_5m[$n5 - 6] > 0) ? (($closes_5m[$n5 - 1] - $closes_5m[$n5 - 6]) / $closes_5m[$n5 - 6]) * 100 : 0;

        // NEW: Check for acceleration (momentum increasing)
        $mom_15m_prev = ($n15 >= 8 && $closes_15m[$n15 - 8] > 0) ?
            (($closes_15m[$n15 - 5] - $closes_15m[$n15 - 8]) / $closes_15m[$n15 - 8]) * 100 : $mom_15m;
        $accelerating_15m = ($mom_15m > $mom_15m_prev);

        // Both positive = confirmed uptrend (reduced from 8 to 5)
        if ($mom_15m > 0.5 && $mom_5m > 0.3)
            $mom_score += 5;

        // Steep 15m momentum (stricter thresholds)
        if ($mom_15m >= 5)
            $mom_score += 8;           // Was 3%
        elseif ($mom_15m >= 3)
            $mom_score += 5;       // Was 1.5%
        elseif ($mom_15m >= 1.5)
            $mom_score += 2;     // Was 0.5%

        // Accelerating 5m momentum (stricter thresholds)
        if ($mom_5m >= 4)
            $mom_score += 7;            // Was 2%
        elseif ($mom_5m >= 2)
            $mom_score += 4;        // Was 1%
        elseif ($mom_5m >= 1)
            $mom_score += 2;        // Was 0.3%

        // NEW: Bonus for acceleration
        if ($accelerating_15m && $mom_15m > 2)
            $mom_score += 3;

        if ($mom_score > 20)
            $mom_score = 20;

        $factors['parabolic_momentum'] = array(
            'score' => $mom_score,
            'max' => 20,
            'mom_15m' => round($mom_15m, 2),
            'mom_5m' => round($mom_5m, 2),
            'accelerating' => $accelerating_15m,
            'mom_15m_prev' => round($mom_15m_prev, 2)
        );
    } else {
        $factors['parabolic_momentum'] = array('score' => 0, 'max' => 20);
    }
    $total += $mom_score;

    // ── Factor 3: RSI Hype Zone (0-15 pts) — IMPROVED v2 ──
    // Memes sustain higher RSI — sweet spot 60-75 (tightened from 55-80)
    $rsi = _mc_calc_rsi($closes_15m, 14);
    $rsi_score = 0;

    // NEW: Also check RSI trend (rising = more bullish)
    $rsi_prev = _mc_calc_rsi(array_slice($closes_15m, 0, -2), 14);
    $rsi_rising = ($rsi > $rsi_prev);

    if ($rsi >= 60 && $rsi <= 75) {           // Tightened hype zone
        $rsi_score = $rsi_rising ? 15 : 12;   // Full points only if rising
    } elseif ($rsi >= 50 && $rsi < 60) {
        $rsi_score = $rsi_rising ? 8 : 5;     // Warming up
    } elseif ($rsi > 75 && $rsi <= 85) {
        $rsi_score = $rsi_rising ? 6 : 3;     // Hot but riskier
    } elseif ($rsi >= 40 && $rsi < 50) {
        $rsi_score = $rsi_rising ? 4 : 2;     // Potential bounce
    }

    // NEW: Penalty for extreme overbought (>85 = likely reversal)
    if ($rsi > 85)
        $rsi_score = 0;

    $factors['rsi_hype_zone'] = array(
        'score' => $rsi_score,
        'max' => 15,
        'rsi' => round($rsi, 1),
        'rsi_prev' => round($rsi_prev, 1),
        'rising' => $rsi_rising
    );
    $total += $rsi_score;

    // ── Factor 4: Social Momentum Proxy (0-15 pts) ──
    // Velocity = price_chg_1h × volume_surge_ratio — proxy for hype/social buzz
    $social_score = 0;
    if ($n15 >= 4 && $has_volume_data && count($volumes_15m) >= 10) {
        $mom_1h = ($closes_15m[$n15 - 4] > 0) ? abs(($closes_15m[$n15 - 1] - $closes_15m[$n15 - 4]) / $closes_15m[$n15 - 4]) * 100 : 0;
        $vol_count2 = count($volumes_15m);
        $avg_v = array_sum($volumes_15m) / $vol_count2;
        $recent_v = array_sum(array_slice($volumes_15m, -3)) / 3;
        $vr = ($avg_v > 0) ? $recent_v / $avg_v : 1;

        $velocity = $mom_1h * $vr;

        if ($velocity >= 20)
            $social_score = 15;
        elseif ($velocity >= 10)
            $social_score = 12;
        elseif ($velocity >= 5)
            $social_score = 8;
        elseif ($velocity >= 2)
            $social_score = 5;
        elseif ($velocity >= 1)
            $social_score = 2;

        $factors['social_proxy'] = array(
            'score' => $social_score,
            'max' => 15,
            'velocity' => round($velocity, 1),
            'mom_1h' => round($mom_1h, 2),
            'vol_ratio' => round($vr, 1),
            'method' => 'candle'
        );
    } elseif ($n15 >= 4) {
        // No per-candle volume — use price momentum × aggregate volume rank
        $mom_1h = ($closes_15m[$n15 - 4] > 0) ? abs(($closes_15m[$n15 - 1] - $closes_15m[$n15 - 4]) / $closes_15m[$n15 - 4]) * 100 : 0;
        $vol_rank = 1.0;
        if ($vol_usd >= 100000000)
            $vol_rank = 3.0;
        elseif ($vol_usd >= 50000000)
            $vol_rank = 2.5;
        elseif ($vol_usd >= 10000000)
            $vol_rank = 2.0;
        elseif ($vol_usd >= 1000000)
            $vol_rank = 1.5;

        $velocity = $mom_1h * $vol_rank;

        if ($velocity >= 15)
            $social_score = 15;
        elseif ($velocity >= 8)
            $social_score = 12;
        elseif ($velocity >= 4)
            $social_score = 8;
        elseif ($velocity >= 2)
            $social_score = 5;
        elseif ($velocity >= 0.5)
            $social_score = 2;

        $factors['social_proxy'] = array(
            'score' => $social_score,
            'max' => 15,
            'velocity' => round($velocity, 1),
            'mom_1h' => round($mom_1h, 2),
            'vol_rank' => $vol_rank,
            'method' => 'aggregate'
        );
    } else {
        $factors['social_proxy'] = array('score' => 0, 'max' => 15, 'velocity' => 0);
    }
    $total += $social_score;

    // ── Factor 5: Volume Concentration (0-10 pts) ──
    // What % of recent volume is in the last 3 candles? Burst = pump starting
    $conc_score = 0;
    if ($has_volume_data && count($volumes_15m) >= 12) {
        $last12_vol = array_sum(array_slice($volumes_15m, -12));
        $last3_vol = array_sum(array_slice($volumes_15m, -3));
        $conc_pct = ($last12_vol > 0) ? ($last3_vol / $last12_vol) * 100 : 0;

        if ($conc_pct >= 60)
            $conc_score = 10;
        elseif ($conc_pct >= 45)
            $conc_score = 7;
        elseif ($conc_pct >= 35)
            $conc_score = 4;
        elseif ($conc_pct >= 28)
            $conc_score = 2;

        $factors['volume_concentration'] = array(
            'score' => $conc_score,
            'max' => 10,
            'pct' => round($conc_pct, 1),
            'method' => 'candle'
        );
    } else {
        // No per-candle volume — use price-range concentration as proxy
        // If recent candles have larger price swings = activity concentrating
        if ($n15 >= 12) {
            $ranges_all = array();
            for ($ri = max(0, $n15 - 12); $ri < $n15; $ri++) {
                if (is_array($candles_15m[$ri]) && isset($candles_15m[$ri][2])) {
                    $rh = floatval($candles_15m[$ri][2]);
                    $rl = floatval($candles_15m[$ri][3]);
                } else {
                    $rh = floatval($candles_15m[$ri]['h']);
                    $rl = floatval($candles_15m[$ri]['l']);
                }
                $ranges_all[] = ($rl > 0) ? ($rh - $rl) / $rl * 100 : 0;
            }
            $total_range = array_sum($ranges_all);
            $recent_range = array_sum(array_slice($ranges_all, -3));
            $range_pct = ($total_range > 0) ? ($recent_range / $total_range) * 100 : 0;

            if ($range_pct >= 50)
                $conc_score = 8;
            elseif ($range_pct >= 40)
                $conc_score = 5;
            elseif ($range_pct >= 30)
                $conc_score = 3;

            $factors['volume_concentration'] = array(
                'score' => $conc_score,
                'max' => 10,
                'pct' => round($range_pct, 1),
                'method' => 'price_range'
            );
        } else {
            $factors['volume_concentration'] = array('score' => 0, 'max' => 10, 'pct' => 0, 'method' => 'none');
        }
    }
    $total += $conc_score;

    // ── Factor 6: Breakout vs 4h High (0-10 pts) ──
    // Is price breaking above its recent 4-hour high?
    $breakout_score = 0;
    if ($n15 >= 16) {
        // 4h high = max of last 16 candles
        $high_4h = 0;
        for ($i = max(0, $n15 - 16); $i < $n15 - 1; $i++) {
            if (is_array($candles_15m[$i]) && isset($candles_15m[$i][2])) {
                $ch = floatval($candles_15m[$i][2]); // CoinGecko: [ts, o, h, l, c]
            } else {
                $ch = floatval($candles_15m[$i]['h']); // Crypto.com
            }
            if ($ch > $high_4h)
                $high_4h = $ch;
        }
        if ($high_4h > 0) {
            $breakout_pct = (($current_price - $high_4h) / $high_4h) * 100;
            if ($breakout_pct >= 2)
                $breakout_score = 10;      // strong breakout
            elseif ($breakout_pct >= 0.5)
                $breakout_score = 7;  // mild breakout
            elseif ($breakout_pct >= 0)
                $breakout_score = 4;    // at the high
            elseif ($breakout_pct >= -1)
                $breakout_score = 2;   // near the high

            $factors['breakout_4h'] = array(
                'score' => $breakout_score,
                'max' => 10,
                'breakout_pct' => round($breakout_pct, 2),
                'high_4h' => round($high_4h, 8)
            );
        } else {
            $factors['breakout_4h'] = array('score' => 0, 'max' => 10, 'breakout_pct' => 0);
        }
    } else {
        $factors['breakout_4h'] = array('score' => 0, 'max' => 10, 'breakout_pct' => 0);
    }
    $total += $breakout_score;

    // ── Factor 7: Low Market Cap Bonus (0-5 pts) ──
    // Smaller coins are more explosive
    $cap_score = 0;
    if ($vol_usd < 1000000)
        $cap_score = 5;         // <$1M vol = micro
    elseif ($vol_usd < 5000000)
        $cap_score = 3;     // <$5M vol = small
    elseif ($vol_usd < 20000000)
        $cap_score = 1;    // <$20M = mid
    $factors['low_cap_bonus'] = array('score' => $cap_score, 'max' => 5, 'vol_usd' => round($vol_usd, 0));
    $total += $cap_score;

    // ── Volatility-adjusted targets using ATR ──
    $atr = _mc_calc_atr($candles_15m);
    $atr_pct = ($current_price > 0) ? ($atr / $current_price) * 100 : 3.0;
    $atr_pct = max(1.0, min(15.0, $atr_pct)); // wider clamp for memes

    // FLAW #4 FIX v3: Quality gates are HARD exclusions — ALL 3 required.
    // Previous v2 required 2/3 but still let through weak signals (0% win rate).
    // Now: must pass ALL 3 quality gates (trend + momentum + volume).
    if ($quality_score < 3) {
        // Hard reject: ALL three gates required for meme signals
        $factors['quality_check'] = array(
            'score' => $quality_score,
            'issues' => $quality_issues,
            'verdict' => 'REJECTED',
            'reason' => 'Failed ' . (3 - $quality_score) . ' of 3 quality gates (all 3 required)',
            'raw_total' => $total
        );
        return null; // Do not generate a signal
    }
    $quality_penalty = 0; // Passed gates, no penalty needed
    $adjusted_total = $total;

    $factors['quality_check'] = array(
        'score' => $quality_score,
        'issues' => $quality_issues,
        'penalty' => $quality_penalty,
        'raw_total' => $total,
        'adjusted_total' => $adjusted_total
    );

    $verdict = 'SKIP';
    $target_pct = 0;
    $risk_pct = 0;

    // v3: Raised thresholds — previous version had 0% win rate, too loose.
    // All verdicts require ALL 3 quality gates (enforced above).
    // Score thresholds raised: STRONG_BUY 88+, BUY 82+, LEAN_BUY 78+
    // Tighter stop losses: max risk clamped to 3% (was 4%)
    if ($adjusted_total >= 88 && $quality_score >= 3) {
        $verdict = 'STRONG_BUY';
        $target_pct = round(max(3.5, min(8.0, $atr_pct * 1.5)), 1);  // Reduced max from 12% to 8%
        $risk_pct = round(max(1.5, min(3.0, $atr_pct * 0.7)), 1);    // Tighter: max 3%
    } elseif ($adjusted_total >= 82 && $quality_score >= 3) {
        $verdict = 'BUY';
        $target_pct = round(max(3.0, min(6.0, $atr_pct * 1.2)), 1);  // Reduced max from 8% to 6%
        $risk_pct = round(max(1.5, min(2.5, $atr_pct * 0.6)), 1);    // Tighter: max 2.5%
    } elseif ($adjusted_total >= 78 && $quality_score >= 3) {
        $verdict = 'LEAN_BUY';
        $target_pct = round(max(2.0, min(4.0, $atr_pct * 0.9)), 1);  // Reduced max from 5% to 4%
        $risk_pct = round(max(1.0, min(2.0, $atr_pct * 0.5)), 1);    // Tighter: max 2%
    }

    // Tier 2 coins: even higher bar (85+ for any signal, 92+ for STRONG_BUY)
    if ($candidate['tier'] === 'tier2' && $verdict !== 'SKIP') {
        if ($adjusted_total < 85) {
            $verdict = 'SKIP';
            $target_pct = 0;
            $risk_pct = 0;
        } elseif ($verdict === 'STRONG_BUY' && $adjusted_total < 92) {
            $verdict = 'BUY'; // Downgrade tier 2 strong buys unless exceptional
        }
    }

    $factors['volatility'] = array('atr' => round($atr, 8), 'atr_pct' => round($atr_pct, 2));

    return array(
        'total' => $adjusted_total,
        'factors' => $factors,
        'verdict' => $verdict,
        'target_pct' => $target_pct,
        'risk_pct' => $risk_pct
    );
}

// ═══════════════════════════════════════════════════════════════════════
//  BTC REGIME DETECTION + ADAPTIVE SCORING (Kimi P0)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Detect BTC market regime using 1h candles: bull, bear, or chop.
 * Uses SMA20 vs SMA50 crossover on BTC_USDT.
 * Returns array('regime' => 'bull|bear|chop', 'trend_pct' => float)
 */
function _mc_detect_btc_regime()
{
    $default = array('regime' => 'chop', 'trend_pct' => 0.0);

    // Try Crypto.com 1h candles for BTC
    $raw = _mc_api('public/get-candlestick?instrument_name=BTC_USDT&timeframe=H1');
    $candles = isset($raw['result']['data']) ? $raw['result']['data'] : array();

    if (count($candles) < 50)
        return $default;

    $closes = array();
    foreach ($candles as $c) {
        $closes[] = floatval(isset($c['c']) ? $c['c'] : 0);
    }
    $n = count($closes);

    // Calculate SMA20 and SMA50
    $sma20 = 0;
    $sma50 = 0;
    for ($i = $n - 20; $i < $n; $i++)
        $sma20 += $closes[$i];
    $sma20 /= 20;
    for ($i = $n - 50; $i < $n; $i++)
        $sma50 += $closes[$i];
    $sma50 /= 50;

    $current = $closes[$n - 1];
    $trend_pct = ($sma50 > 0) ? (($sma20 - $sma50) / $sma50) * 100 : 0;

    if ($current > $sma20 && $sma20 > $sma50 && $trend_pct > 0.5) {
        return array('regime' => 'bull', 'trend_pct' => round($trend_pct, 2));
    } elseif ($current < $sma20 && $sma20 < $sma50 && $trend_pct < -0.5) {
        return array('regime' => 'bear', 'trend_pct' => round($trend_pct, 2));
    }
    return array('regime' => 'chop', 'trend_pct' => round($trend_pct, 2));
}

/**
 * Adjust score based on BTC regime (IMPROVED v2 - more conservative):
 * - Bull: +3 bonus to momentum-driven coins (reduced from +5)
 * - Bear: -10 penalty to ALL signals (bear market = avoid memes)
 * - Chop: no adjustment (0)
 * Returns array('adjusted_score' => int, 'adjustment' => int)
 */
function _mc_regime_score_adjust($raw_score, $factors, $btc_regime)
{
    $adjustment = 0;
    $regime = $btc_regime['regime'];

    $mom = isset($factors['parabolic_momentum']['score']) ? $factors['parabolic_momentum']['score'] : 0;
    $vol = isset($factors['explosive_volume']['score']) ? $factors['explosive_volume']['score'] : 0;
    $brk = isset($factors['breakout_4h']['score']) ? $factors['breakout_4h']['score'] : 0;
    $trend = isset($factors['trend_confirm']['aligned']) ? $factors['trend_confirm']['aligned'] : true;

    if ($regime === 'bull') {
        // Bull market: small boost to strong momentum coins
        if ($mom >= 12 && $trend)
            $adjustment += 3;
        elseif ($mom >= 8 && $trend)
            $adjustment += 2;
    } elseif ($regime === 'bear') {
        // Bear market: heavy penalty — memes are death in bear markets.
        // Previous -5 was far too lenient (0% win rate resulted).
        // Now -12 base, -5 extra for weak plays = effectively blocks most signals.
        $adjustment -= 12;
        // Extra penalty for momentum-only plays without volume confirmation
        if ($mom >= 10 && $vol < 6)
            $adjustment -= 5;
        // Extra penalty for breakout plays in bear (usually bull traps)
        if ($brk >= 5)
            $adjustment -= 3;
    } else {
        // Chop regime: memes are still risky — apply moderate penalty
        $adjustment -= 4;
        if ($mom < 10 && $vol < 10)
            $adjustment -= 3; // Extra penalty for weak signals in chop
    }

    $adjusted = max(0, min(100, $raw_score + $adjustment));
    return array('adjusted_score' => $adjusted, 'adjustment' => $adjustment, 'regime' => $regime);
}

// ═══════════════════════════════════════════════════════════════════════
//  RESOLVE — continuous resolve with 2-hour window
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_resolve($conn)
{
    // v3: Extended resolve window from 2h to 4h — gives more time for targets to be hit.
    // Previous 2h window was too short for meme moves which can take 3-4h to play out.
    $sql = "SELECT id, pair, price_at_signal, target_pct, risk_pct, score, created_at
            FROM mc_winners
            WHERE outcome IS NULL
            AND created_at < DATE_SUB(NOW(), INTERVAL 4 HOUR)
            ORDER BY created_at ASC
            LIMIT 20";
    $res = $conn->query($sql);
    if (!$res) {
        _mc_err('Query failed');
    }

    $resolved = 0;
    $wins = 0;
    $losses = 0;
    $details = array();

    while ($row = $res->fetch_assoc()) {
        $entry_price = floatval($row['price_at_signal']);
        $target = floatval($row['target_pct']);
        $risk = floatval($row['risk_pct']);
        $target_price = $entry_price * (1 + $target / 100);
        $stop_price = $entry_price * (1 - $risk / 100);

        // Continuous resolve: 5-min candles in 2h window (24 candles)
        $candles_raw = _mc_api('public/get-candlestick?instrument_name=' . $row['pair'] . '&timeframe=M5');
        $candles = isset($candles_raw['result']['data']) ? $candles_raw['result']['data'] : array();

        $peak_price = $entry_price;
        $trough_price = $entry_price;
        $hit_target = false;
        $hit_stop = false;
        $hit_target_first = false;

        if (count($candles) >= 8) {
            foreach ($candles as $c) {
                $candle_high = floatval($c['h']);
                $candle_low = floatval($c['l']);
                if ($candle_high > $peak_price)
                    $peak_price = $candle_high;
                if ($candle_low < $trough_price)
                    $trough_price = $candle_low;

                if (!$hit_stop && !$hit_target && $candle_low <= $stop_price) {
                    $hit_stop = true;
                }
                if (!$hit_target && !$hit_stop && $candle_high >= $target_price) {
                    $hit_target = true;
                    $hit_target_first = true;
                }
                if (!$hit_stop && !$hit_target) {
                    if ($candle_low <= $stop_price && $candle_high >= $target_price) {
                        $candle_open = floatval($c['o']);
                        if (abs($candle_open - $stop_price) < abs($candle_open - $target_price)) {
                            $hit_stop = true;
                        } else {
                            $hit_target = true;
                            $hit_target_first = true;
                        }
                    }
                }
            }
        }

        // Current price for final PnL
        $ticker = _mc_api('public/get-tickers?instrument_name=' . $row['pair']);
        $current_price = $entry_price;
        if ($ticker && isset($ticker['result']['data'][0])) {
            $current_price = floatval($ticker['result']['data'][0]['a']);
        }
        $pnl_pct = (($current_price - $entry_price) / $entry_price) * 100;
        $peak_pnl = (($peak_price - $entry_price) / $entry_price) * 100;

        $outcome = 'neutral';
        if ($hit_target_first || $hit_target) {
            $outcome = 'win';
            $wins++;
        } elseif ($hit_stop) {
            $outcome = 'loss';
            $losses++;
        } elseif ($pnl_pct >= $target) {
            $outcome = 'win';
            $wins++;
        } elseif ($pnl_pct <= -$risk) {
            $outcome = 'loss';
            $losses++;
        } elseif ($pnl_pct > 0) {
            $outcome = 'partial_win';
            $wins++;
        } else {
            $outcome = 'partial_loss';
            $losses++;
        }

        $esc_outcome = $conn->real_escape_string($outcome);
        $sql2 = "UPDATE mc_winners SET outcome = '$esc_outcome', price_at_resolve = $current_price, pnl_pct = " . round($pnl_pct, 4) . ", resolved_at = NOW() WHERE id = " . intval($row['id']);
        $conn->query($sql2);
        $resolved++;

        $details[] = array(
            'pair' => $row['pair'],
            'entry' => $entry_price,
            'current' => $current_price,
            'peak' => round($peak_price, 8),
            'peak_pnl' => round($peak_pnl, 2),
            'pnl_pct' => round($pnl_pct, 2),
            'outcome' => $outcome,
            'hit_target' => $hit_target,
            'hit_stop' => $hit_stop,
            'score' => intval($row['score'])
        );

        usleep(100000); // 100ms between API calls
    }

    echo json_encode(array(
        'ok' => true,
        'resolved' => $resolved,
        'wins' => $wins,
        'losses' => $losses,
        'win_rate' => ($resolved > 0) ? round(($wins / $resolved) * 100, 1) : 0,
        'resolve_method' => 'continuous_2h',
        'details' => $details
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  WINNERS — get latest cached winners
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_winners($conn)
{
    $sql = "SELECT * FROM mc_winners WHERE created_at > DATE_SUB(NOW(), INTERVAL 4 HOUR) ORDER BY score DESC LIMIT 20";
    $res = $conn->query($sql);
    if (!$res) {
        _mc_err('Query failed');
    }

    $winners = array();
    while ($row = $res->fetch_assoc()) {
        $row['factors_json'] = json_decode($row['factors_json'], true);
        $winners[] = $row;
    }

    // Include current BTC regime so the frontend can show market conditions
    $btc_regime = _mc_detect_btc_regime();

    // Also get last scan time
    $last_scan_res = $conn->query("SELECT MAX(created_at) as last_scan FROM mc_winners");
    $last_scan = '';
    if ($last_scan_res && $ls = $last_scan_res->fetch_assoc()) {
        $last_scan = isset($ls['last_scan']) ? $ls['last_scan'] : '';
    }

    echo json_encode(array(
        'ok' => true,
        'count' => count($winners),
        'winners' => $winners,
        'btc_regime' => $btc_regime['regime'],
        'btc_trend_pct' => $btc_regime['trend_pct'],
        'last_scan' => $last_scan
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  HISTORY — past signals with outcomes
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_history($conn)
{
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
    if ($limit > 200)
        $limit = 200;

    $sql = "SELECT pair, score, verdict, target_pct, risk_pct, pnl_pct, outcome, tier, chg_24h, created_at, resolved_at
            FROM mc_winners ORDER BY created_at DESC LIMIT $limit";
    $res = $conn->query($sql);
    if (!$res) {
        _mc_err('Query failed');
    }

    $history = array();
    while ($row = $res->fetch_assoc()) {
        $history[] = $row;
    }

    echo json_encode(array(
        'ok' => true,
        'count' => count($history),
        'history' => $history
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  LEADERBOARD — win rate by tier and pair
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_leaderboard($conn)
{
    // By verdict tier
    $sql = "SELECT verdict,
                COUNT(*) as signals,
                AVG(score) as avg_score,
                SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as losses,
                AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl
            FROM mc_winners
            WHERE verdict != 'SKIP'
            GROUP BY verdict
            ORDER BY avg_score DESC";
    $res = $conn->query($sql);
    $tiers = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $resolved = intval($row['wins']) + intval($row['losses']);
            $row['win_rate'] = ($resolved > 0) ? round(($row['wins'] / $resolved) * 100, 1) : null;
            $row['significance'] = _mc_binomial_significance(intval($row['wins']), $resolved, 0.5);
            $tiers[] = $row;
        }
    }

    // By tier (tier1 vs tier2)
    $sql_t = "SELECT tier,
                COUNT(*) as signals,
                SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as losses,
                AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl
            FROM mc_winners
            GROUP BY tier";
    $res_t = $conn->query($sql_t);
    $tier_comparison = array();
    if ($res_t) {
        while ($row = $res_t->fetch_assoc()) {
            $resolved = intval($row['wins']) + intval($row['losses']);
            $row['win_rate'] = ($resolved > 0) ? round(($row['wins'] / $resolved) * 100, 1) : null;
            $tier_comparison[] = $row;
        }
    }

    // By pair (top performers, min 2 signals)
    $sql2 = "SELECT pair,
                COUNT(*) as signals,
                SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl,
                MAX(pnl_pct) as best_trade
            FROM mc_winners
            GROUP BY pair
            HAVING signals >= 2
            ORDER BY avg_pnl DESC
            LIMIT 15";
    $res2 = $conn->query($sql2);
    $by_pair = array();
    if ($res2) {
        while ($row = $res2->fetch_assoc()) {
            $resolved = intval($row['wins']);
            $total = intval($row['signals']);
            $row['win_rate'] = ($total > 0) ? round(($resolved / $total) * 100, 1) : null;
            $by_pair[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'by_verdict' => $tiers,
        'by_tier' => $tier_comparison,
        'by_pair' => $by_pair
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  STATS — overall performance
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_stats($conn)
{
    $sql = "SELECT
                COUNT(*) as total_signals,
                SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as total_wins,
                SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as total_losses,
                SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) as pending,
                AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl,
                MAX(pnl_pct) as best_trade,
                MIN(pnl_pct) as worst_trade,
                COUNT(DISTINCT pair) as unique_pairs,
                COUNT(DISTINCT scan_id) as total_scans,
                MAX(created_at) as last_scan
            FROM mc_winners";
    $res = $conn->query($sql);
    $stats = $res ? $res->fetch_assoc() : array();

    $resolved = intval($stats['total_wins']) + intval($stats['total_losses']);
    $stats['overall_win_rate'] = ($resolved > 0) ? round(($stats['total_wins'] / $resolved) * 100, 1) : null;
    $stats['resolved'] = $resolved;
    $stats['significance'] = _mc_binomial_significance(intval($stats['total_wins']), $resolved, 0.5);

    echo json_encode(array(
        'ok' => true,
        'stats' => $stats
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  SCAN LOG — full transparency
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_scan_log($conn)
{
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 100;
    if ($limit > 500)
        $limit = 500;

    $scan_filter = '';
    if (isset($_GET['scan_id']) && $_GET['scan_id'] !== '') {
        $scan_filter = " AND scan_id = '" . $conn->real_escape_string($_GET['scan_id']) . "'";
    }

    if ($scan_filter === '') {
        $latest_res = $conn->query("SELECT scan_id FROM mc_scan_log ORDER BY created_at DESC LIMIT 1");
        if ($latest_res && $latest_row = $latest_res->fetch_assoc()) {
            $scan_filter = " AND scan_id = '" . $conn->real_escape_string($latest_row['scan_id']) . "'";
        }
    }

    $sql = "SELECT * FROM mc_scan_log WHERE 1=1 $scan_filter ORDER BY score DESC LIMIT $limit";
    $res = $conn->query($sql);
    if (!$res) {
        _mc_err('Query failed');
    }

    $rows = array();
    while ($row = $res->fetch_assoc()) {
        $row['factors_json'] = json_decode($row['factors_json'], true);
        $rows[] = $row;
    }

    $scans_res = $conn->query("SELECT scan_id, MIN(created_at) as created_at, COUNT(*) as analyzed,
            SUM(CASE WHEN score >= 70 THEN 1 ELSE 0 END) as winners
        FROM mc_scan_log GROUP BY scan_id ORDER BY created_at DESC LIMIT 20");
    $recent_scans = array();
    if ($scans_res) {
        while ($s = $scans_res->fetch_assoc()) {
            $recent_scans[] = $s;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'count' => count($rows),
        'log' => $rows,
        'recent_scans' => $recent_scans
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  TECHNICAL INDICATORS
// ═══════════════════════════════════════════════════════════════════════

function _mc_calc_rsi($closes, $period)
{
    $n = count($closes);
    if ($n < $period + 1)
        return 50;

    $gains = 0;
    $losses_val = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $diff = $closes[$i] - $closes[$i - 1];
        if ($diff > 0)
            $gains += $diff;
        else
            $losses_val += abs($diff);
    }
    $avg_gain = $gains / $period;
    $avg_loss = $losses_val / $period;
    if ($avg_loss == 0)
        return 100;
    $rs = $avg_gain / $avg_loss;
    return 100 - (100 / (1 + $rs));
}

function _mc_calc_ema($closes, $period)
{
    $n = count($closes);
    if ($n < $period)
        return $closes[$n - 1];

    $multiplier = 2 / ($period + 1);
    $ema = array_sum(array_slice($closes, 0, $period)) / $period; // SMA start

    for ($i = $period; $i < $n; $i++) {
        $ema = ($closes[$i] - $ema) * $multiplier + $ema;
    }
    return $ema;
}

function _mc_calc_atr($candles, $period = 14)
{
    $n = count($candles);
    if ($n < 2)
        return 0;

    $trs = array();
    for ($i = 1; $i < $n; $i++) {
        if (is_array($candles[$i]) && isset($candles[$i][2])) {
            // CoinGecko format: [timestamp, open, high, low, close]
            $high = floatval($candles[$i][2]);
            $low = floatval($candles[$i][3]);
            $prev_close = floatval($candles[$i - 1][4]);
        } else {
            // Crypto.com format
            $high = floatval($candles[$i]['h']);
            $low = floatval($candles[$i]['l']);
            $prev_close = floatval($candles[$i - 1]['c']);
        }
        $tr = max($high - $low, abs($high - $prev_close), abs($low - $prev_close));
        $trs[] = $tr;
    }

    $cnt = count($trs);
    if ($cnt < $period) {
        return ($cnt > 0) ? array_sum($trs) / $cnt : 0;
    }
    $sum = 0;
    for ($i = $cnt - $period; $i < $cnt; $i++) {
        $sum += $trs[$i];
    }
    return $sum / $period;
}

function _mc_binomial_significance($wins, $total, $null_p)
{
    if ($total < 1) {
        return array(
            'is_significant' => false,
            'confidence' => 'insufficient_data',
            'sample_size' => $total,
            'min_sample_needed' => 30,
            'note' => 'Need at least 30 resolved signals for meaningful analysis'
        );
    }

    $observed_p = $wins / $total;
    $se = sqrt($null_p * (1 - $null_p) / $total);
    if ($se == 0) {
        return array('is_significant' => false, 'confidence' => 'error', 'sample_size' => $total);
    }

    $z = ($observed_p - $null_p) / $se;
    $abs_z = abs($z);
    if ($abs_z >= 3.29)
        $p_value = 0.0005;
    elseif ($abs_z >= 2.58)
        $p_value = 0.005;
    elseif ($abs_z >= 2.33)
        $p_value = 0.01;
    elseif ($abs_z >= 1.96)
        $p_value = 0.025;
    elseif ($abs_z >= 1.65)
        $p_value = 0.05;
    elseif ($abs_z >= 1.28)
        $p_value = 0.10;
    else
        $p_value = 0.5;
    if ($z < 0)
        $p_value = 1 - $p_value;

    $is_sig = ($z > 0 && $p_value < 0.05);
    $confidence = 'not_significant';
    if ($total < 30)
        $confidence = 'insufficient_data';
    elseif ($is_sig && $p_value < 0.01)
        $confidence = 'highly_significant';
    elseif ($is_sig)
        $confidence = 'significant';
    elseif ($z > 0)
        $confidence = 'trending_positive';

    // Wilson CI
    $z95 = 1.96;
    $denom = 1 + $z95 * $z95 / $total;
    $center = ($observed_p + $z95 * $z95 / (2 * $total)) / $denom;
    $margin = $z95 * sqrt(($observed_p * (1 - $observed_p) + $z95 * $z95 / (4 * $total)) / $total) / $denom;
    $ci_low = round(max(0, ($center - $margin)) * 100, 1);
    $ci_high = round(min(1, ($center + $margin)) * 100, 1);

    return array(
        'is_significant' => $is_sig,
        'confidence' => $confidence,
        'p_value' => round($p_value, 4),
        'z_score' => round($z, 2),
        'observed_win_rate' => round($observed_p * 100, 1),
        'sample_size' => $total,
        'confidence_interval' => array('low' => $ci_low, 'high' => $ci_high)
    );
}

// ═══════════════════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════
//  COINGECKO HELPERS — supplementary data source for better meme coverage
// ═══════════════════════════════════════════════════════════════════════

function _mc_coingecko_meme_market()
{
    // Fetch top meme coins by volume from CoinGecko (free, no key, 30 calls/min)
    $url = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=meme-token&order=volume_desc&per_page=50&page=1';
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 12);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MemeScanner/1.0');
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp)
        return array();
    $data = json_decode($resp, true);
    if (!is_array($data))
        return array();
    return $data;
}

function _mc_coingecko_ohlc($coin_id)
{
    // Fetch 1-day OHLC (30-min candles, ~48 candles)
    // Format: [[timestamp, open, high, low, close], ...]
    $url = 'https://api.coingecko.com/api/v3/coins/' . urlencode($coin_id) . '/ohlc?vs_currency=usd&days=1';
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MemeScanner/1.0');
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp)
        return array();
    $data = json_decode($resp, true);
    if (!is_array($data))
        return array();
    return $data;
}

function _mc_find_cg_match($pair, $cg_memes, $cg_id_map)
{
    // Try explicit ID mapping first
    if (isset($cg_id_map[$pair])) {
        $target_id = $cg_id_map[$pair];
        foreach ($cg_memes as $cg) {
            if ($cg['id'] === $target_id)
                return $cg;
        }
    }
    // Fall back to symbol match
    $base = strtolower(str_replace('_USDT', '', $pair));
    foreach ($cg_memes as $cg) {
        if ($cg['symbol'] === $base)
            return $cg;
    }
    return null;
}

function _mc_api($endpoint)
{
    $url = 'https://api.crypto.com/exchange/v1/' . $endpoint;
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MemeScanner/1.0');
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp)
        return null;
    return json_decode($resp, true);
}

/**
 * Get a lookup table of symbols known to be on Kraken.
 * Reads from the $KRAKEN_MEMES list in meme_market_pulse.php (canonical source).
 * Returns array('PEPE' => true, 'DOGE' => true, ...) for fast checking.
 */
function _mc_get_kraken_lookup()
{
    // Canonical Kraken meme list — kept in sync with meme_market_pulse.php $KRAKEN_MEMES
    $known = array(
        'DOGE',
        'SHIB',
        'PEPE',
        'FLOKI',
        'BONK',
        'WIF',
        'TURBO',
        'NEIRO',
        'MEME',
        'TRUMP',
        'FARTCOIN',
        'PNUT',
        'PENGU',
        'POPCAT',
        'BRETT',
        'MOG',
        'BOME',
        'ACT',
        'SPX',
        'PONKE',
        'FWOG',
        'SLERF',
        'AI16Z',
        'VIRTUAL',
        'MYRO',
        'GOAT',
        'MOODENG',
        'GIGA',
        'DEGEN',
        'BABYDOGE',
        'WOJAK',
        'SATS',
        'COQ',
        'DOG',
        'CHILLGUY'
    );
    $lookup = array();
    for ($i = 0; $i < count($known); $i++) {
        $lookup[$known[$i]] = true;
    }
    return $lookup;
}

function _mc_ends_with($str, $suffix)
{
    return substr($str, -strlen($suffix)) === $suffix;
}

function _mc_sort_by_change($a, $b)
{
    if ($b['chg_24h'] == $a['chg_24h'])
        return 0;
    return ($b['chg_24h'] > $a['chg_24h']) ? 1 : -1;
}

function _mc_sort_by_score($a, $b)
{
    if ($b['score'] == $a['score'])
        return 0;
    return ($b['score'] > $a['score']) ? 1 : -1;
}

function _mc_discord_alert($winners, $scan_id, $analyzed, $elapsed)
{
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
    if (!$webhook_url)
        return;

    $strong = 0;
    $buy = 0;
    $lean = 0;
    $msg_lines = array();

    // Header line with timestamp
    $msg_lines[] = "**🐸 Meme Coin Signals — " . date('M j, g:i A T') . "**";
    $msg_lines[] = "";

    foreach (array_slice($winners, 0, 6) as $w) {
        $pair = str_replace('_USDT', '/USDT', $w['pair']);
        $tier_label = ($w['tier'] === 'tier1') ? ' [T1]' : ' [T2]';

        // Signal strength rating based on score
        $strength = '';
        $strength_emoji = '';
        if ($w['score'] >= 90) {
            $strength = '🔥 EXTREMELY STRONG';
            $strength_emoji = "\xF0\x9F\x94\xA5";
            $strong++;
        } elseif ($w['score'] >= 85) {
            $strength = '🚀 STRONG BUY';
            $strength_emoji = "\xF0\x9F\x9A\x80";
            $strong++;
        } elseif ($w['score'] >= 78) {
            $strength = '🔵 BUY';
            $strength_emoji = "\xF0\x9F\x94\xB5";
            $buy++;
        } else {
            $strength = '🟡 LEAN BUY';
            $strength_emoji = "\xF0\x9F\x9F\xA1";
            $lean++;
        }

        // Calculate TP and SL prices
        $entry = floatval($w['price']);
        $target_pct = floatval($w['target_pct']);
        $risk_pct = floatval($w['risk_pct']);
        $tp_price = $entry * (1 + $target_pct / 100);
        $sl_price = $entry * (1 - $risk_pct / 100);

        // Format prices based on magnitude
        $decimals = $entry >= 1 ? 4 : ($entry >= 0.01 ? 6 : ($entry >= 0.0001 ? 8 : 10));
        $entry_str = number_format($entry, $decimals);
        $tp_str = number_format($tp_price, $decimals);
        $sl_str = number_format($sl_price, $decimals);

        // Build signal line
        $msg_lines[] = $strength_emoji . ' **' . $pair . '**' . $tier_label . ' | **' . $strength . '**';
        $msg_lines[] = '```';
        $msg_lines[] = '💰 Entry: $' . $entry_str;
        $msg_lines[] = '🎯 Target: $' . $tp_str . ' (+' . $target_pct . '%)';
        $msg_lines[] = '🛑 Stop: $' . $sl_str . ' (-' . $risk_pct . '%)';
        $msg_lines[] = '📊 Score: ' . $w['score'] . '/100 | 24h: ' . round($w['chg_24h'], 1) . '%';
        $msg_lines[] = '```';
    }

    if (count($winners) > 6) {
        $msg_lines[] = '';
        $msg_lines[] = '*... and ' . (count($winners) - 6) . ' more signals*';
    }

    // Summary line
    $msg_lines[] = '';
    $msg_lines[] = '📈 **Summary:** ' . $strong . ' Strong | ' . $buy . ' Buy | ' . $lean . ' Lean';

    $title = "\xF0\x9F\x90\xB8 Meme Scanner Alert — " . count($winners) . ' Signal' . (count($winners) > 1 ? 's' : '');
    $embed = array(
        'title' => $title,
        'description' => implode("\n", $msg_lines),
        'color' => ($strong > 0) ? 16729344 : (($buy > 0) ? 3447003 : 16776960),
        'footer' => array('text' => 'Scan #' . $scan_id . ' | ' . $analyzed . ' analyzed in ' . $elapsed . 's | v2 Algorithm'),
        'url' => 'https://findtorontoevents.ca/findcryptopairs/meme.html',
        'timestamp' => date('c')
    );

    $payload = json_encode(array('embeds' => array($embed)));
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

// ═══════════════════════════════════════════════════════════════════════
//  DAILY PICKS — timestamped daily picks from algorithm
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_daily_picks($conn)
{
    $date = isset($_GET['date']) ? $_GET['date'] : date('Y-m-d');
    // Validate date format
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date)) {
        $date = date('Y-m-d');
    }
    $esc_date = $conn->real_escape_string($date);

    // Get all winners for the requested date, ordered by score desc
    $sql = "SELECT pair, score, verdict, target_pct, risk_pct, pnl_pct, outcome, tier,
                   chg_24h, vol_usd_24h, price_at_signal, price_at_resolve, factors_json,
                   created_at, resolved_at
            FROM mc_winners
            WHERE DATE(created_at) = '$esc_date'
            ORDER BY created_at DESC, score DESC
            LIMIT 100";
    $res = $conn->query($sql);
    $picks = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $row['factors_json'] = json_decode($row['factors_json'], true);
            $picks[] = $row;
        }
    }

    // Summary stats for the day
    $sql_sum = "SELECT
                    COUNT(*) as total_picks,
                    SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) as pending,
                    AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl,
                    MAX(pnl_pct) as best_trade,
                    MIN(pnl_pct) as worst_trade,
                    COUNT(DISTINCT pair) as unique_coins,
                    SUM(CASE WHEN verdict='STRONG_BUY' THEN 1 ELSE 0 END) as strong_buys,
                    SUM(CASE WHEN verdict='BUY' THEN 1 ELSE 0 END) as buys,
                    SUM(CASE WHEN verdict='LEAN_BUY' THEN 1 ELSE 0 END) as lean_buys
                FROM mc_winners
                WHERE DATE(created_at) = '$esc_date'";
    $sum_res = $conn->query($sql_sum);
    $day_summary = $sum_res ? $sum_res->fetch_assoc() : array();
    $resolved = intval($day_summary['wins']) + intval($day_summary['losses']);
    $day_summary['win_rate'] = ($resolved > 0) ? round(($day_summary['wins'] / $resolved) * 100, 1) : null;
    $day_summary['resolved'] = $resolved;

    // Available dates (for date picker)
    $dates_res = $conn->query("SELECT DISTINCT DATE(created_at) as pick_date, COUNT(*) as cnt
                               FROM mc_winners
                               GROUP BY DATE(created_at)
                               ORDER BY pick_date DESC
                               LIMIT 30");
    $available_dates = array();
    if ($dates_res) {
        while ($d = $dates_res->fetch_assoc()) {
            $available_dates[] = $d;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'date' => $date,
        'total_picks' => count($picks),
        'picks' => $picks,
        'day_summary' => $day_summary,
        'available_dates' => $available_dates
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  PERFORMANCE — daily/weekly/monthly/all-time tracker
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_performance($conn)
{
    $period = isset($_GET['period']) ? $_GET['period'] : 'all';

    // Daily performance breakdown
    $sql_daily = "SELECT DATE(created_at) as trade_date,
                    COUNT(*) as signals,
                    SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) as pending,
                    AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl,
                    SUM(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct ELSE 0 END) as total_pnl,
                    MAX(pnl_pct) as best_trade,
                    MIN(pnl_pct) as worst_trade,
                    COUNT(DISTINCT pair) as unique_coins
                 FROM mc_winners
                 GROUP BY DATE(created_at)
                 ORDER BY trade_date DESC
                 LIMIT 60";
    $res_daily = $conn->query($sql_daily);
    $daily = array();
    if ($res_daily) {
        while ($row = $res_daily->fetch_assoc()) {
            $resolved = intval($row['wins']) + intval($row['losses']);
            $row['win_rate'] = ($resolved > 0) ? round(($row['wins'] / $resolved) * 100, 1) : null;
            $row['resolved'] = $resolved;
            $daily[] = $row;
        }
    }

    // Cumulative equity curve (starting from $10,000 hypothetical)
    // Walk days chronologically, compound returns
    $equity_data = array();
    $equity = 10000.0;
    $peak_equity = 10000.0;
    $reversed_daily = array_reverse($daily);
    foreach ($reversed_daily as $d) {
        if ($d['avg_pnl'] !== null) {
            // Apply average PnL for the day (assume 5% position size per signal)
            $day_return = floatval($d['avg_pnl']) * intval($d['resolved']) * 0.05 / 100;
            $equity = $equity * (1 + $day_return);
        }
        if ($equity > $peak_equity)
            $peak_equity = $equity;
        $drawdown = ($peak_equity > 0) ? (($peak_equity - $equity) / $peak_equity) * 100 : 0;
        $equity_data[] = array(
            'date' => $d['trade_date'],
            'equity' => round($equity, 2),
            'drawdown' => round($drawdown, 2),
            'day_pnl' => $d['avg_pnl'] !== null ? round(floatval($d['avg_pnl']), 2) : 0,
            'signals' => intval($d['signals']),
            'win_rate' => $d['win_rate']
        );
    }

    // Period summaries
    $period_sql = '';
    if ($period === '7d')
        $period_sql = "AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)";
    elseif ($period === '30d')
        $period_sql = "AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)";
    elseif ($period === 'today')
        $period_sql = "AND DATE(created_at) = CURDATE()";

    $sql_period = "SELECT
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) as pending,
                    AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl,
                    SUM(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct ELSE 0 END) as total_pnl,
                    MAX(pnl_pct) as best_trade,
                    MIN(pnl_pct) as worst_trade,
                    COUNT(DISTINCT pair) as unique_coins,
                    COUNT(DISTINCT DATE(created_at)) as active_days,
                    MIN(created_at) as first_signal,
                    MAX(created_at) as last_signal
                FROM mc_winners WHERE 1=1 $period_sql";
    $pres = $conn->query($sql_period);
    $summary = $pres ? $pres->fetch_assoc() : array();
    $resolved = intval($summary['wins']) + intval($summary['losses']);
    $summary['win_rate'] = ($resolved > 0) ? round(($summary['wins'] / $resolved) * 100, 1) : null;
    $summary['resolved'] = $resolved;
    $summary['significance'] = _mc_binomial_significance(intval($summary['wins']), $resolved, 0.5);

    // Top performers by pair
    $sql_top = "SELECT pair, tier,
                    COUNT(*) as signals,
                    SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                    AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl,
                    MAX(pnl_pct) as best_trade,
                    COUNT(DISTINCT DATE(created_at)) as days_active
                FROM mc_winners WHERE 1=1 $period_sql
                GROUP BY pair
                ORDER BY avg_pnl DESC
                LIMIT 15";
    $top_res = $conn->query($sql_top);
    $top_coins = array();
    if ($top_res) {
        while ($row = $top_res->fetch_assoc()) {
            $t_resolved = intval($row['wins']);
            $t_total = intval($row['signals']);
            $row['win_rate'] = ($t_total > 0) ? round(($t_resolved / $t_total) * 100, 1) : null;
            $top_coins[] = $row;
        }
    }

    // Streaks: longest win streak, longest loss streak, current streak
    $sql_streak = "SELECT outcome, created_at FROM mc_winners
                   WHERE outcome IS NOT NULL $period_sql
                   ORDER BY created_at ASC";
    $streak_res = $conn->query($sql_streak);
    $win_streak = 0;
    $loss_streak = 0;
    $max_win_streak = 0;
    $max_loss_streak = 0;
    $current_streak = 0;
    $current_type = '';
    if ($streak_res) {
        while ($sr = $streak_res->fetch_assoc()) {
            $is_win = ($sr['outcome'] === 'win' || $sr['outcome'] === 'partial_win');
            if ($is_win) {
                $win_streak++;
                $loss_streak = 0;
                if ($win_streak > $max_win_streak)
                    $max_win_streak = $win_streak;
                $current_streak = $win_streak;
                $current_type = 'W';
            } else {
                $loss_streak++;
                $win_streak = 0;
                if ($loss_streak > $max_loss_streak)
                    $max_loss_streak = $loss_streak;
                $current_streak = $loss_streak;
                $current_type = 'L';
            }
        }
    }

    echo json_encode(array(
        'ok' => true,
        'period' => $period,
        'summary' => $summary,
        'daily' => $daily,
        'equity_curve' => $equity_data,
        'top_coins' => $top_coins,
        'streaks' => array(
            'max_win' => $max_win_streak,
            'max_loss' => $max_loss_streak,
            'current' => $current_streak,
            'current_type' => $current_type
        )
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  SNAPSHOT — record daily performance snapshot (called by GitHub Actions)
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_snapshot($conn)
{
    $today = date('Y-m-d');

    // Check if snapshot already exists for today
    $esc_today = $conn->real_escape_string($today);
    $check = $conn->query("SELECT id FROM mc_daily_snapshots WHERE snapshot_date = '$esc_today' LIMIT 1");
    if ($check && $check->num_rows > 0) {
        // Update existing snapshot
        $sql = "SELECT
                    COUNT(*) as signals,
                    SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as losses,
                    AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl,
                    SUM(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct ELSE 0 END) as total_pnl,
                    MAX(pnl_pct) as best_trade,
                    MIN(pnl_pct) as worst_trade,
                    COUNT(DISTINCT pair) as unique_coins
                FROM mc_winners WHERE DATE(created_at) = '$esc_today'";
        $res = $conn->query($sql);
        $s = $res ? $res->fetch_assoc() : array();
        $resolved = intval($s['wins']) + intval($s['losses']);
        $wr = ($resolved > 0) ? round(($s['wins'] / $resolved) * 100, 1) : 0;

        $conn->query("UPDATE mc_daily_snapshots SET
            signals = " . intval($s['signals']) . ",
            wins = " . intval($s['wins']) . ",
            losses = " . intval($s['losses']) . ",
            win_rate = $wr,
            avg_pnl = " . floatval($s['avg_pnl']) . ",
            total_pnl = " . floatval($s['total_pnl']) . ",
            best_trade = " . floatval($s['best_trade']) . ",
            worst_trade = " . floatval($s['worst_trade']) . ",
            unique_coins = " . intval($s['unique_coins']) . ",
            updated_at = NOW()
            WHERE snapshot_date = '$esc_today'");

        echo json_encode(array('ok' => true, 'action' => 'updated', 'date' => $today, 'signals' => intval($s['signals']), 'win_rate' => $wr));
    } else {
        // Create new snapshot
        $sql = "SELECT
                    COUNT(*) as signals,
                    SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as losses,
                    AVG(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct END) as avg_pnl,
                    SUM(CASE WHEN pnl_pct IS NOT NULL THEN pnl_pct ELSE 0 END) as total_pnl,
                    MAX(pnl_pct) as best_trade,
                    MIN(pnl_pct) as worst_trade,
                    COUNT(DISTINCT pair) as unique_coins
                FROM mc_winners WHERE DATE(created_at) = '$esc_today'";
        $res = $conn->query($sql);
        $s = $res ? $res->fetch_assoc() : array();
        $resolved = intval($s['wins']) + intval($s['losses']);
        $wr = ($resolved > 0) ? round(($s['wins'] / $resolved) * 100, 1) : 0;

        $conn->query("INSERT INTO mc_daily_snapshots (snapshot_date, signals, wins, losses, win_rate, avg_pnl, total_pnl, best_trade, worst_trade, unique_coins, updated_at)
                      VALUES ('$esc_today', " . intval($s['signals']) . ", " . intval($s['wins']) . ", " . intval($s['losses']) . ", $wr, " . floatval($s['avg_pnl']) . ", " . floatval($s['total_pnl']) . ", " . floatval($s['best_trade']) . ", " . floatval($s['worst_trade']) . ", " . intval($s['unique_coins']) . ", NOW())");

        echo json_encode(array('ok' => true, 'action' => 'created', 'date' => $today, 'signals' => intval($s['signals']), 'win_rate' => $wr));
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  ADAPTIVE WEIGHTS — learn which indicators predict wins
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_adaptive_weights($conn)
{
    // Ensure mc_adaptive_weights table exists
    $conn->query("CREATE TABLE IF NOT EXISTS mc_adaptive_weights (
        id INT AUTO_INCREMENT PRIMARY KEY,
        weights_json TEXT NOT NULL,
        correlation_json TEXT NOT NULL,
        sample_count INT NOT NULL DEFAULT 0,
        win_rate DOUBLE DEFAULT 0,
        created_at DATETIME NOT NULL,
        INDEX idx_aw_created (created_at)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // Get all resolved signals with factors
    $sql = "SELECT factors_json, outcome, pnl_pct
            FROM mc_winners
            WHERE outcome IS NOT NULL
            AND factors_json IS NOT NULL
            AND created_at > DATE_SUB(NOW(), INTERVAL 90 DAY)
            ORDER BY created_at DESC
            LIMIT 500";
    $res = $conn->query($sql);
    if (!$res) {
        _mc_err('Query failed');
    }

    $factor_keys = array(
        'explosive_volume',
        'parabolic_momentum',
        'rsi_hype_zone',
        'social_proxy',
        'volume_concentration',
        'breakout_4h',
        'low_cap_bonus'
    );
    $max_values = array(25, 20, 15, 15, 10, 10, 5);

    $samples = array();
    $wins = 0;
    $losses = 0;

    while ($row = $res->fetch_assoc()) {
        $factors = json_decode($row['factors_json'], true);
        if (!is_array($factors))
            continue;

        $is_win = ($row['outcome'] === 'win' || $row['outcome'] === 'partial_win') ? 1 : 0;
        if ($is_win)
            $wins++;
        else
            $losses++;

        $scores = array();
        for ($fi = 0; $fi < count($factor_keys); $fi++) {
            $fk = $factor_keys[$fi];
            $val = 0;
            if (isset($factors[$fk])) {
                if (is_array($factors[$fk]) && isset($factors[$fk]['score'])) {
                    $val = floatval($factors[$fk]['score']);
                } elseif (is_numeric($factors[$fk])) {
                    $val = floatval($factors[$fk]);
                }
            }
            // Normalize to 0-1
            $scores[] = ($max_values[$fi] > 0) ? min(1.0, $val / $max_values[$fi]) : 0;
        }

        $samples[] = array('scores' => $scores, 'outcome' => $is_win, 'pnl' => floatval($row['pnl_pct']));
    }

    $total = $wins + $losses;
    if ($total < 10) {
        echo json_encode(array(
            'ok' => false,
            'error' => 'Need at least 10 resolved signals, found ' . $total,
            'wins' => $wins,
            'losses' => $losses
        ));
        return;
    }

    // Calculate Pearson correlation for each factor vs outcome
    $correlations = array();
    for ($fi = 0; $fi < count($factor_keys); $fi++) {
        $sum_x = 0;
        $sum_y = 0;
        $sum_xy = 0;
        $sum_x2 = 0;
        $sum_y2 = 0;
        $n = count($samples);
        for ($si = 0; $si < $n; $si++) {
            $x = $samples[$si]['scores'][$fi];
            $y = $samples[$si]['outcome'];
            $sum_x += $x;
            $sum_y += $y;
            $sum_xy += $x * $y;
            $sum_x2 += $x * $x;
            $sum_y2 += $y * $y;
        }
        $num = $n * $sum_xy - $sum_x * $sum_y;
        $den = sqrt(($n * $sum_x2 - $sum_x * $sum_x) * ($n * $sum_y2 - $sum_y * $sum_y));
        $corr = ($den != 0) ? $num / $den : 0;
        $correlations[$factor_keys[$fi]] = round($corr, 4);
    }

    // Convert correlations to weights (absolute value, normalized)
    $abs_corrs = array();
    $total_abs = 0;
    for ($fi = 0; $fi < count($factor_keys); $fi++) {
        $ac = abs($correlations[$factor_keys[$fi]]);
        $abs_corrs[] = $ac;
        $total_abs += $ac;
    }

    $weights = array();
    for ($fi = 0; $fi < count($factor_keys); $fi++) {
        $w = ($total_abs > 0) ? round($abs_corrs[$fi] / $total_abs, 4) : round(1.0 / count($factor_keys), 4);
        // Clamp minimum weight to 0.02 (no factor should be entirely ignored)
        $w = max(0.02, $w);
        $weights[$factor_keys[$fi]] = $w;
    }
    // Re-normalize after clamping
    $wtotal = 0;
    foreach ($weights as $wv)
        $wtotal += $wv;
    foreach ($weights as $wk => $wv) {
        $weights[$wk] = round($wv / $wtotal, 4);
    }

    $wr = ($total > 0) ? round(($wins / $total) * 100, 1) : 0;

    // Save to database
    $esc_weights = $conn->real_escape_string(json_encode($weights));
    $esc_corr = $conn->real_escape_string(json_encode($correlations));
    $conn->query("INSERT INTO mc_adaptive_weights (weights_json, correlation_json, sample_count, win_rate, created_at)
                  VALUES ('$esc_weights', '$esc_corr', $total, $wr, NOW())");

    echo json_encode(array(
        'ok' => true,
        'samples' => $total,
        'wins' => $wins,
        'losses' => $losses,
        'win_rate' => $wr,
        'correlations' => $correlations,
        'adaptive_weights' => $weights,
        'default_weights' => array(
            'explosive_volume' => 0.25,
            'parabolic_momentum' => 0.20,
            'rsi_hype_zone' => 0.15,
            'social_proxy' => 0.15,
            'volume_concentration' => 0.10,
            'breakout_4h' => 0.10,
            'low_cap_bonus' => 0.05
        )
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  ML STATUS — public endpoint showing ML learning progress
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_ml_status($conn)
{
    // Latest adaptive weights
    $aw_res = $conn->query("SELECT * FROM mc_adaptive_weights ORDER BY created_at DESC LIMIT 1");
    $latest_weights = null;
    if ($aw_res && $aw_res->num_rows > 0) {
        $row = $aw_res->fetch_assoc();
        $latest_weights = array(
            'weights' => json_decode($row['weights_json'], true),
            'correlations' => json_decode($row['correlation_json'], true),
            'sample_count' => intval($row['sample_count']),
            'win_rate' => floatval($row['win_rate']),
            'computed_at' => $row['created_at']
        );
    }

    // Training data stats
    $td_res = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as losses
        FROM mc_winners WHERE outcome IS NOT NULL");
    $td = ($td_res) ? $td_res->fetch_assoc() : array('total' => 0, 'wins' => 0, 'losses' => 0);

    echo json_encode(array(
        'ok' => true,
        'training_data' => array(
            'resolved_signals' => intval($td['total']),
            'wins' => intval($td['wins']),
            'losses' => intval($td['losses']),
            'ready_for_ml' => intval($td['total']) >= 30
        ),
        'latest_adaptive_weights' => $latest_weights,
        'status' => intval($td['total']) >= 30 ? 'active' : 'collecting_data'
    ));
}

function _mc_err($msg)
{
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => $msg));
    exit;
}

function _mc_ensure_schema($conn)
{
    $conn->query("CREATE TABLE IF NOT EXISTS mc_winners (
        id INT AUTO_INCREMENT PRIMARY KEY,
        scan_id VARCHAR(20) NOT NULL,
        pair VARCHAR(30) NOT NULL,
        price_at_signal DOUBLE NOT NULL,
        price_at_resolve DOUBLE DEFAULT NULL,
        score INT NOT NULL DEFAULT 0,
        factors_json TEXT,
        verdict VARCHAR(20) NOT NULL DEFAULT 'SKIP',
        target_pct DOUBLE NOT NULL DEFAULT 3.0,
        risk_pct DOUBLE NOT NULL DEFAULT 2.0,
        pnl_pct DOUBLE DEFAULT NULL,
        outcome VARCHAR(20) DEFAULT NULL,
        vol_usd_24h DOUBLE DEFAULT 0,
        chg_24h DOUBLE DEFAULT 0,
        tier VARCHAR(10) DEFAULT 'tier1',
        created_at DATETIME NOT NULL,
        resolved_at DATETIME DEFAULT NULL,
        INDEX idx_mc_scan (scan_id),
        INDEX idx_mc_pair (pair),
        INDEX idx_mc_outcome (outcome),
        INDEX idx_mc_tier (tier),
        INDEX idx_mc_created (created_at)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    $conn->query("CREATE TABLE IF NOT EXISTS mc_scan_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        scan_id VARCHAR(20) NOT NULL,
        pair VARCHAR(30) NOT NULL,
        price DOUBLE NOT NULL,
        score INT NOT NULL DEFAULT 0,
        factors_json TEXT,
        verdict VARCHAR(20) NOT NULL DEFAULT 'SKIP',
        chg_24h DOUBLE DEFAULT 0,
        vol_usd_24h DOUBLE DEFAULT 0,
        tier VARCHAR(10) DEFAULT '',
        on_kraken TINYINT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        INDEX idx_mc_log_scan (scan_id),
        INDEX idx_mc_log_created (created_at)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // Add on_kraken column if it doesn't exist (for existing tables)
    @$conn->query("ALTER TABLE mc_scan_log ADD COLUMN on_kraken TINYINT NOT NULL DEFAULT 0");

    $conn->query("CREATE TABLE IF NOT EXISTS mc_daily_snapshots (
        id INT AUTO_INCREMENT PRIMARY KEY,
        snapshot_date DATE NOT NULL,
        signals INT DEFAULT 0,
        wins INT DEFAULT 0,
        losses INT DEFAULT 0,
        win_rate DOUBLE DEFAULT 0,
        avg_pnl DOUBLE DEFAULT 0,
        total_pnl DOUBLE DEFAULT 0,
        best_trade DOUBLE DEFAULT 0,
        worst_trade DOUBLE DEFAULT 0,
        unique_coins INT DEFAULT 0,
        updated_at DATETIME,
        UNIQUE KEY idx_mc_snap_date (snapshot_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // Purge old scan log entries (5 days for memes — higher frequency)
    $conn->query("DELETE FROM mc_scan_log WHERE created_at < DATE_SUB(NOW(), INTERVAL 5 DAY)");
}

// ═══════════════════════════════════════════════════════════════════════
//  PUMP-AND-DUMP DETECTION — Multi-signal pattern recognition
//  Detects 4 classic P&D patterns:
//    1. Parabolic Rise — >50% 24h or >15% 1h + >25% 6h
//    2. RSI Exhaustion — RSI >85 + price turning negative (dump starting)
//    3. Volume Dump   — volume surging 5x+ while price dropping (smart $ exit)
//    4. Wick Trap     — long upper wick >3x body (rejected at highs)
//  2+ signals = hard reject, 1 signal = elevated risk warning
// ═══════════════════════════════════════════════════════════════════════
function _mc_detect_pump_and_dump($closes_15m, $closes_5m, $highs_15m, $lows_15m, $volumes_15m, $candidate)
{
    $n15 = count($closes_15m);
    $n5 = count($closes_5m);
    $signals = array();
    $rsi = 0;

    // Calculate short-term price changes
    $chg_24h = floatval(isset($candidate['chg_24h']) ? $candidate['chg_24h'] : 0);
    $chg_1h = 0;
    $chg_6h = 0;
    if ($n15 >= 4 && $closes_15m[$n15 - 4] > 0) {
        $chg_1h = (($closes_15m[$n15 - 1] - $closes_15m[$n15 - 4]) / $closes_15m[$n15 - 4]) * 100;
    }
    if ($n15 >= 24 && $closes_15m[max(0, $n15 - 24)] > 0) {
        $chg_6h = (($closes_15m[$n15 - 1] - $closes_15m[max(0, $n15 - 24)]) / $closes_15m[max(0, $n15 - 24)]) * 100;
    }

    // 1. PARABOLIC RISE — extreme price surge
    if ($chg_24h > 50 || ($chg_1h > 15 && $chg_6h > 25)) {
        $signals[] = 'parabolic_rise';
    }

    // 2. RSI EXHAUSTION — extreme overbought + price turning down
    if ($n15 >= 14) {
        $rsi = _mc_calc_rsi($closes_15m, 14);
        if ($rsi > 85 && $chg_1h < 0) {
            $signals[] = 'rsi_exhaustion';
        }
    }

    // 3. VOLUME SPIKE + REVERSAL — volume surging but price fading (smart money exiting)
    if (count($volumes_15m) >= 10) {
        $total_vol = array_sum($volumes_15m);
        $vol_count = count($volumes_15m);
        $avg_vol = $total_vol / $vol_count;
        $recent_vol = (array_sum(array_slice($volumes_15m, -3))) / 3;
        $vol_ratio = ($avg_vol > 0) ? $recent_vol / $avg_vol : 1;

        if ($vol_ratio >= 5 && $chg_1h < -1) {
            $signals[] = 'volume_dump';
        }
    }

    // 4. WICK TRAP — last candle has a long upper wick (rejected at highs)
    if ($n15 >= 2 && count($highs_15m) >= $n15 && count($lows_15m) >= $n15) {
        $last_high = $highs_15m[$n15 - 1];
        $last_close = $closes_15m[$n15 - 1];
        $last_open = $closes_15m[$n15 - 2]; // previous close as proxy for open
        $body = abs($last_close - $last_open);
        $upper_wick = $last_high - max($last_close, $last_open);

        if ($body > 0 && $upper_wick > $body * 3) {
            $signals[] = 'wick_trap';
        }
    }

    // Decision: 2+ signals = hard reject, 1 = elevated risk
    $signal_count = count($signals);
    $detected = ($signal_count >= 2);
    if ($signal_count >= 2) {
        $risk_level = 'critical';
    } elseif ($signal_count >= 1) {
        $risk_level = 'elevated';
    } else {
        $risk_level = 'none';
    }

    return array(
        'detected' => $detected,
        'signals' => $signals,
        'signal_count' => $signal_count,
        'risk_level' => $risk_level,
        'chg_1h' => round($chg_1h, 2),
        'chg_6h' => round($chg_6h, 2),
        'chg_24h' => round($chg_24h, 2),
        'rsi' => round($rsi, 1)
    );
}
?>