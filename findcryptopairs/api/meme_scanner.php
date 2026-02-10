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
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

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
$key    = isset($_GET['key']) ? $_GET['key'] : '';
$ADMIN_KEY = 'memescan2026';

// Tier 1: established meme coins (always scanned)
$MEME_TIER1 = array(
    'DOGE_USDT', 'SHIB_USDT', 'PEPE_USDT', 'FLOKI_USDT',
    'BONK_USDT', 'WIF_USDT', 'MEME_USDT'
);

// Meme keyword fragments for dynamic discovery
$MEME_KEYWORDS = array(
    'DOGE', 'SHIB', 'INU', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'MEME',
    'BABY', 'MOON', 'ELON', 'CAT', 'DOG', 'NEIRO', 'TURBO', 'BRETT',
    'MOG', 'POPCAT', 'MYRO', 'SLERF', 'BOME', 'WOJAK', 'LADYS',
    'SATS', 'ORDI', 'COQ', 'TOSHI'
);

_mc_ensure_schema($conn);

switch ($action) {
    case 'scan':
        if ($key !== $ADMIN_KEY) { _mc_err('Unauthorized'); }
        _mc_action_scan($conn);
        break;
    case 'winners':
        _mc_action_winners($conn);
        break;
    case 'history':
        _mc_action_history($conn);
        break;
    case 'resolve':
        if ($key !== $ADMIN_KEY) { _mc_err('Unauthorized'); }
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
        if ($key !== $ADMIN_KEY) { _mc_err('Unauthorized'); }
        _mc_action_snapshot($conn);
        break;
    default:
        _mc_err('Unknown action: ' . $action);
}

// ═══════════════════════════════════════════════════════════════════════
//  SCAN — the meme engine
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_scan($conn) {
    global $MEME_TIER1, $MEME_KEYWORDS;
    $start = microtime(true);

    // 1. Get all instruments from Crypto.com
    $instruments = _mc_api('public/get-instruments');
    if (!$instruments || !isset($instruments['result']['data'])) {
        _mc_err('Failed to fetch instruments from Crypto.com');
    }

    $all_usdt_pairs = array();
    foreach ($instruments['result']['data'] as $inst) {
        $sym = isset($inst['symbol']) ? $inst['symbol'] : (isset($inst['instrument_name']) ? $inst['instrument_name'] : '');
        $itype = isset($inst['inst_type']) ? $inst['inst_type'] : '';
        if ($itype === 'CCY_PAIR' && _mc_ends_with($sym, '_USDT')) {
            $all_usdt_pairs[] = $sym;
        }
    }

    // 2. Get all tickers
    $tickers_raw = _mc_api('public/get-tickers');
    if (!$tickers_raw || !isset($tickers_raw['result']['data'])) {
        _mc_err('Failed to fetch tickers');
    }
    $tickers = array();
    foreach ($tickers_raw['result']['data'] as $t) {
        $k = isset($t['i']) ? $t['i'] : (isset($t['symbol']) ? $t['symbol'] : '');
        if ($k) $tickers[$k] = $t;
    }

    // 3. Build candidate list: Tier 1 (always) + Tier 2 (dynamic discovery)
    $candidates = array();
    $tier1_found = 0;
    $tier2_found = 0;

    // Tier 1: established memes — always include if they have volume
    foreach ($MEME_TIER1 as $meme) {
        if (!isset($tickers[$meme])) continue;
        $t = $tickers[$meme];
        $price  = isset($t['a']) ? floatval($t['a']) : 0;
        $volUsd = isset($t['vv']) ? floatval($t['vv']) : (floatval(isset($t['v']) ? $t['v'] : 0) * $price);
        $chg24  = isset($t['c']) ? floatval($t['c']) * 100 : 0;

        if ($volUsd < 50000) continue; // lower threshold for established memes
        if ($chg24 <= -5) continue;    // allow small dips for tier 1

        $candidates[] = array(
            'pair'     => $meme,
            'price'    => $price,
            'vol_usd'  => $volUsd,
            'chg_24h'  => $chg24,
            'high_24h' => isset($t['h']) ? floatval($t['h']) : $price,
            'low_24h'  => isset($t['l']) ? floatval($t['l']) : $price,
            'tier'     => 'tier1'
        );
        $tier1_found++;
    }

    // Tier 2: dynamic discovery — find pumping meme-like coins
    $tier2_pool = array();
    foreach ($all_usdt_pairs as $pair) {
        if (in_array($pair, $MEME_TIER1)) continue; // skip tier 1
        if (!isset($tickers[$pair])) continue;

        $t = $tickers[$pair];
        $price  = isset($t['a']) ? floatval($t['a']) : 0;
        $volUsd = isset($t['vv']) ? floatval($t['vv']) : (floatval(isset($t['v']) ? $t['v'] : 0) * $price);
        $chg24  = isset($t['c']) ? floatval($t['c']) * 100 : 0;

        // Tier 2 filters: pumping + small-to-mid cap + meme-like
        if ($chg24 < 5) continue;         // must be pumping
        if ($volUsd < 100000) continue;    // minimum liquidity
        if ($volUsd > 500000000) continue; // skip mega-caps (BTC, ETH)

        // Check if it matches meme keywords
        $is_meme = false;
        $base = str_replace('_USDT', '', $pair);
        foreach ($MEME_KEYWORDS as $kw) {
            if (strpos($base, $kw) !== false) {
                $is_meme = true;
                break;
            }
        }

        // Also accept extreme volume spikes as "meme-like" behavior
        // even without keyword match (new memes we don't know yet)
        $is_extreme_pump = ($chg24 >= 15 && $volUsd >= 500000);

        if (!$is_meme && !$is_extreme_pump) continue;

        $tier2_pool[] = array(
            'pair'     => $pair,
            'price'    => $price,
            'vol_usd'  => $volUsd,
            'chg_24h'  => $chg24,
            'high_24h' => isset($t['h']) ? floatval($t['h']) : $price,
            'low_24h'  => isset($t['l']) ? floatval($t['l']) : $price,
            'tier'     => 'tier2'
        );
    }

    // Sort tier 2 by 24h change, take top 15
    usort($tier2_pool, '_mc_sort_by_change');
    $tier2_pool = array_slice($tier2_pool, 0, 15);
    foreach ($tier2_pool as $t2) {
        $candidates[] = $t2;
        $tier2_found++;
    }

    // 4. Deep analysis with meme-specific scoring
    $scored = array();
    foreach ($candidates as $c) {
        // Get 15m candles (96 = 24h) and 5m candles (48 = 4h)
        $candles_15m = _mc_api('public/get-candlestick?instrument_name=' . $c['pair'] . '&timeframe=M15');
        $candles_5m  = _mc_api('public/get-candlestick?instrument_name=' . $c['pair'] . '&timeframe=M5');

        $c15m = isset($candles_15m['result']['data']) ? $candles_15m['result']['data'] : array();
        $c5m  = isset($candles_5m['result']['data']) ? $candles_5m['result']['data'] : array();

        if (count($c15m) < 8 || count($c5m) < 8) continue;

        $score_details = _mc_score_pair($c, $c15m, $c5m);
        $c['score']      = $score_details['total'];
        $c['factors']    = $score_details['factors'];
        $c['verdict']    = $score_details['verdict'];
        $c['target_pct'] = $score_details['target_pct'];
        $c['risk_pct']   = $score_details['risk_pct'];

        $scored[] = $c;
    }

    usort($scored, '_mc_sort_by_score');

    // 5. Save winners (score >= 70) to DB
    $scan_id = date('YmdHis');
    $winners = array();
    $saved = 0;

    foreach ($scored as $s) {
        if ($s['score'] < 70) continue;
        $winners[] = $s;

        $esc_pair    = $conn->real_escape_string($s['pair']);
        $esc_scan    = $conn->real_escape_string($scan_id);
        $esc_factors = $conn->real_escape_string(json_encode($s['factors']));
        $esc_verdict = $conn->real_escape_string($s['verdict']);
        $esc_tier    = $conn->real_escape_string($s['tier']);

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

    // Save ALL analyzed to scan_log
    foreach ($scored as $s) {
        $esc_pair_log    = $conn->real_escape_string($s['pair']);
        $esc_scan_log    = $conn->real_escape_string($scan_id);
        $esc_factors_log = $conn->real_escape_string(json_encode($s['factors']));
        $esc_verdict_log = $conn->real_escape_string($s['verdict']);
        $esc_tier_log    = $conn->real_escape_string($s['tier']);
        $sql_log = "INSERT INTO mc_scan_log (scan_id, pair, price, score, factors_json, verdict, chg_24h, vol_usd_24h, tier, created_at)
                    VALUES ('$esc_scan_log', '$esc_pair_log', " . floatval($s['price']) . ", " . intval($s['score']) . ", '$esc_factors_log', '$esc_verdict_log', " . floatval($s['chg_24h']) . ", " . floatval($s['vol_usd']) . ", '$esc_tier_log', NOW())";
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
            'vol_usd' => round($tc['vol_usd'], 0)
        );
    }

    echo json_encode(array(
        'ok' => true,
        'scan_id' => $scan_id,
        'total_usdt_pairs' => count($all_usdt_pairs),
        'tier1_found' => $tier1_found,
        'tier2_found' => $tier2_found,
        'deep_analyzed' => count($scored),
        'winners_found' => count($winners),
        'winners_saved' => $saved,
        'elapsed_sec' => $elapsed,
        'winners' => array_slice($winners, 0, 15),
        'top_candidates' => $top_candidates
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  SCORING ENGINE — meme-specific factors
// ═══════════════════════════════════════════════════════════════════════
function _mc_score_pair($candidate, $candles_15m, $candles_5m) {
    $total = 0;
    $factors = array();
    $current_price = $candidate['price'];
    $vol_usd = $candidate['vol_usd'];

    // Extract close prices
    $closes_15m = array();
    $volumes_15m = array();
    foreach ($candles_15m as $c) {
        $closes_15m[] = floatval($c['c']);
        $volumes_15m[] = floatval(isset($c['v']) ? $c['v'] : 0);
    }
    $closes_5m = array();
    foreach ($candles_5m as $c) {
        $closes_5m[] = floatval($c['c']);
    }

    $n15 = count($closes_15m);
    $n5  = count($closes_5m);

    // ── Factor 1: Explosive Volume (0-25 pts) ──
    // Compare recent volume to average
    $vol_score = 0;
    if (count($volumes_15m) >= 10) {
        $recent_vol = 0;
        $avg_vol = 0;
        $vol_count = count($volumes_15m);
        // Average of all candles
        $avg_vol = array_sum($volumes_15m) / $vol_count;
        // Recent 3 candles
        $recent_3 = array_slice($volumes_15m, -3);
        $recent_vol = array_sum($recent_3) / 3;

        $vol_ratio = ($avg_vol > 0) ? $recent_vol / $avg_vol : 1;

        if ($vol_ratio >= 10) $vol_score = 25;
        elseif ($vol_ratio >= 5) $vol_score = 18;
        elseif ($vol_ratio >= 3) $vol_score = 12;
        elseif ($vol_ratio >= 2) $vol_score = 8;
        elseif ($vol_ratio >= 1.5) $vol_score = 4;

        $factors['explosive_volume'] = array(
            'score' => $vol_score,
            'max' => 25,
            'ratio' => round($vol_ratio, 1),
            'recent_avg' => round($recent_vol, 2)
        );
    } else {
        $factors['explosive_volume'] = array('score' => 0, 'max' => 25, 'ratio' => 0);
    }
    $total += $vol_score;

    // ── Factor 2: Parabolic Momentum (0-20 pts) ──
    // Steep price acceleration on 15m + 5m
    $mom_score = 0;
    if ($n15 >= 4 && $n5 >= 6) {
        // 15m momentum: last 4 candles (~1 hour)
        $mom_15m = ($closes_15m[$n15 - 4] > 0) ? (($closes_15m[$n15 - 1] - $closes_15m[$n15 - 4]) / $closes_15m[$n15 - 4]) * 100 : 0;
        // 5m momentum: last 6 candles (~30 min)
        $mom_5m = ($closes_5m[$n5 - 6] > 0) ? (($closes_5m[$n5 - 1] - $closes_5m[$n5 - 6]) / $closes_5m[$n5 - 6]) * 100 : 0;

        // Both positive = confirmed uptrend
        if ($mom_15m > 0 && $mom_5m > 0) $mom_score += 8;

        // Steep 15m momentum
        if ($mom_15m >= 3) $mom_score += 6;
        elseif ($mom_15m >= 1.5) $mom_score += 4;
        elseif ($mom_15m >= 0.5) $mom_score += 2;

        // Accelerating 5m momentum
        if ($mom_5m >= 2) $mom_score += 6;
        elseif ($mom_5m >= 1) $mom_score += 4;
        elseif ($mom_5m >= 0.3) $mom_score += 2;

        if ($mom_score > 20) $mom_score = 20;

        $factors['parabolic_momentum'] = array(
            'score' => $mom_score,
            'max' => 20,
            'mom_15m' => round($mom_15m, 2),
            'mom_5m' => round($mom_5m, 2)
        );
    } else {
        $factors['parabolic_momentum'] = array('score' => 0, 'max' => 20);
    }
    $total += $mom_score;

    // ── Factor 3: RSI Hype Zone (0-15 pts) ──
    // Memes sustain higher RSI — sweet spot 55-80
    $rsi = _mc_calc_rsi($closes_15m, 14);
    $rsi_score = 0;
    if ($rsi >= 55 && $rsi <= 80) $rsi_score = 15;      // hype zone
    elseif ($rsi >= 45 && $rsi < 55) $rsi_score = 8;     // warming up
    elseif ($rsi > 80 && $rsi <= 90) $rsi_score = 5;     // very hot but not dead yet
    elseif ($rsi >= 35 && $rsi < 45) $rsi_score = 3;     // oversold bounce possible
    $factors['rsi_hype_zone'] = array('score' => $rsi_score, 'max' => 15, 'rsi' => round($rsi, 1));
    $total += $rsi_score;

    // ── Factor 4: Social Momentum Proxy (0-15 pts) ──
    // Velocity = price_chg_1h × volume_surge_ratio — proxy for hype/social buzz
    $social_score = 0;
    if ($n15 >= 4 && count($volumes_15m) >= 10) {
        $mom_1h = ($closes_15m[$n15 - 4] > 0) ? abs(($closes_15m[$n15 - 1] - $closes_15m[$n15 - 4]) / $closes_15m[$n15 - 4]) * 100 : 0;
        $vol_count2 = count($volumes_15m);
        $avg_v = array_sum($volumes_15m) / $vol_count2;
        $recent_v = array_sum(array_slice($volumes_15m, -3)) / 3;
        $vr = ($avg_v > 0) ? $recent_v / $avg_v : 1;

        $velocity = $mom_1h * $vr;

        if ($velocity >= 20) $social_score = 15;
        elseif ($velocity >= 10) $social_score = 12;
        elseif ($velocity >= 5) $social_score = 8;
        elseif ($velocity >= 2) $social_score = 5;
        elseif ($velocity >= 1) $social_score = 2;

        $factors['social_proxy'] = array(
            'score' => $social_score,
            'max' => 15,
            'velocity' => round($velocity, 1),
            'mom_1h' => round($mom_1h, 2),
            'vol_ratio' => round($vr, 1)
        );
    } else {
        $factors['social_proxy'] = array('score' => 0, 'max' => 15, 'velocity' => 0);
    }
    $total += $social_score;

    // ── Factor 5: Volume Concentration (0-10 pts) ──
    // What % of recent volume is in the last 3 candles? Burst = pump starting
    $conc_score = 0;
    if (count($volumes_15m) >= 12) {
        $last12_vol = array_sum(array_slice($volumes_15m, -12));
        $last3_vol  = array_sum(array_slice($volumes_15m, -3));
        $conc_pct = ($last12_vol > 0) ? ($last3_vol / $last12_vol) * 100 : 0;

        if ($conc_pct >= 60) $conc_score = 10;       // 60%+ in last 3 of 12 = massive burst
        elseif ($conc_pct >= 45) $conc_score = 7;
        elseif ($conc_pct >= 35) $conc_score = 4;
        elseif ($conc_pct >= 28) $conc_score = 2;    // 25% would be even distribution

        $factors['volume_concentration'] = array(
            'score' => $conc_score,
            'max' => 10,
            'pct' => round($conc_pct, 1)
        );
    } else {
        $factors['volume_concentration'] = array('score' => 0, 'max' => 10, 'pct' => 0);
    }
    $total += $conc_score;

    // ── Factor 6: Breakout vs 4h High (0-10 pts) ──
    // Is price breaking above its recent 4-hour high?
    $breakout_score = 0;
    if ($n15 >= 16) {
        // 4h high = max of last 16 × 15m candles
        $high_4h = 0;
        for ($i = max(0, $n15 - 16); $i < $n15 - 1; $i++) {
            $ch = floatval($candles_15m[$i]['h']);
            if ($ch > $high_4h) $high_4h = $ch;
        }
        if ($high_4h > 0) {
            $breakout_pct = (($current_price - $high_4h) / $high_4h) * 100;
            if ($breakout_pct >= 2) $breakout_score = 10;      // strong breakout
            elseif ($breakout_pct >= 0.5) $breakout_score = 7;  // mild breakout
            elseif ($breakout_pct >= 0) $breakout_score = 4;    // at the high
            elseif ($breakout_pct >= -1) $breakout_score = 2;   // near the high

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
    if ($vol_usd < 1000000) $cap_score = 5;         // <$1M vol = micro
    elseif ($vol_usd < 5000000) $cap_score = 3;     // <$5M vol = small
    elseif ($vol_usd < 20000000) $cap_score = 1;    // <$20M = mid
    $factors['low_cap_bonus'] = array('score' => $cap_score, 'max' => 5, 'vol_usd' => round($vol_usd, 0));
    $total += $cap_score;

    // ── Volatility-adjusted targets using ATR ──
    $atr = _mc_calc_atr($candles_15m);
    $atr_pct = ($current_price > 0) ? ($atr / $current_price) * 100 : 3.0;
    $atr_pct = max(1.0, min(15.0, $atr_pct)); // wider clamp for memes

    $verdict = 'SKIP';
    $target_pct = 0;
    $risk_pct = 0;

    if ($total >= 85) {
        $verdict = 'STRONG_BUY';
        $target_pct = round(max(5.0, min(15.0, $atr_pct * 2.0)), 1);
        $risk_pct   = round(max(2.0, min(5.0, $atr_pct * 1.0)), 1);
    } elseif ($total >= 75) {
        $verdict = 'BUY';
        $target_pct = round(max(3.0, min(10.0, $atr_pct * 1.5)), 1);
        $risk_pct   = round(max(2.0, min(4.0, $atr_pct * 0.8)), 1);
    } elseif ($total >= 70) {
        $verdict = 'LEAN_BUY';
        $target_pct = round(max(2.0, min(6.0, $atr_pct * 1.2)), 1);
        $risk_pct   = round(max(1.5, min(3.0, $atr_pct * 0.7)), 1);
    }

    $factors['volatility'] = array('atr' => round($atr, 8), 'atr_pct' => round($atr_pct, 2));

    return array(
        'total'      => $total,
        'factors'    => $factors,
        'verdict'    => $verdict,
        'target_pct' => $target_pct,
        'risk_pct'   => $risk_pct
    );
}

// ═══════════════════════════════════════════════════════════════════════
//  RESOLVE — continuous resolve with 2-hour window
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_resolve($conn) {
    $sql = "SELECT id, pair, price_at_signal, target_pct, risk_pct, score, created_at
            FROM mc_winners
            WHERE outcome IS NULL
            AND created_at < DATE_SUB(NOW(), INTERVAL 2 HOUR)
            ORDER BY created_at ASC
            LIMIT 20";
    $res = $conn->query($sql);
    if (!$res) { _mc_err('Query failed'); }

    $resolved = 0;
    $wins = 0;
    $losses = 0;
    $details = array();

    while ($row = $res->fetch_assoc()) {
        $entry_price  = floatval($row['price_at_signal']);
        $target       = floatval($row['target_pct']);
        $risk         = floatval($row['risk_pct']);
        $target_price = $entry_price * (1 + $target / 100);
        $stop_price   = $entry_price * (1 - $risk / 100);

        // Continuous resolve: 5-min candles in 2h window (24 candles)
        $candles_raw = _mc_api('public/get-candlestick?instrument_name=' . $row['pair'] . '&timeframe=M5');
        $candles = isset($candles_raw['result']['data']) ? $candles_raw['result']['data'] : array();

        $peak_price   = $entry_price;
        $trough_price = $entry_price;
        $hit_target   = false;
        $hit_stop     = false;
        $hit_target_first = false;

        if (count($candles) >= 8) {
            foreach ($candles as $c) {
                $candle_high = floatval($c['h']);
                $candle_low  = floatval($c['l']);
                if ($candle_high > $peak_price) $peak_price = $candle_high;
                if ($candle_low < $trough_price) $trough_price = $candle_low;

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
        $pnl_pct  = (($current_price - $entry_price) / $entry_price) * 100;
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
            'pair'     => $row['pair'],
            'entry'    => $entry_price,
            'current'  => $current_price,
            'peak'     => round($peak_price, 8),
            'peak_pnl' => round($peak_pnl, 2),
            'pnl_pct'  => round($pnl_pct, 2),
            'outcome'  => $outcome,
            'hit_target' => $hit_target,
            'hit_stop'   => $hit_stop,
            'score'      => intval($row['score'])
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
function _mc_action_winners($conn) {
    $sql = "SELECT * FROM mc_winners WHERE created_at > DATE_SUB(NOW(), INTERVAL 2 HOUR) ORDER BY score DESC LIMIT 20";
    $res = $conn->query($sql);
    if (!$res) { _mc_err('Query failed'); }

    $winners = array();
    while ($row = $res->fetch_assoc()) {
        $row['factors_json'] = json_decode($row['factors_json'], true);
        $winners[] = $row;
    }

    echo json_encode(array(
        'ok' => true,
        'count' => count($winners),
        'winners' => $winners
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  HISTORY — past signals with outcomes
// ═══════════════════════════════════════════════════════════════════════
function _mc_action_history($conn) {
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
    if ($limit > 200) $limit = 200;

    $sql = "SELECT pair, score, verdict, target_pct, risk_pct, pnl_pct, outcome, tier, chg_24h, created_at, resolved_at
            FROM mc_winners ORDER BY created_at DESC LIMIT $limit";
    $res = $conn->query($sql);
    if (!$res) { _mc_err('Query failed'); }

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
function _mc_action_leaderboard($conn) {
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
function _mc_action_stats($conn) {
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
function _mc_action_scan_log($conn) {
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 100;
    if ($limit > 500) $limit = 500;

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
    if (!$res) { _mc_err('Query failed'); }

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

function _mc_calc_rsi($closes, $period) {
    $n = count($closes);
    if ($n < $period + 1) return 50;

    $gains = 0;
    $losses_val = 0;
    for ($i = $n - $period; $i < $n; $i++) {
        $diff = $closes[$i] - $closes[$i - 1];
        if ($diff > 0) $gains += $diff;
        else $losses_val += abs($diff);
    }
    $avg_gain = $gains / $period;
    $avg_loss = $losses_val / $period;
    if ($avg_loss == 0) return 100;
    $rs = $avg_gain / $avg_loss;
    return 100 - (100 / (1 + $rs));
}

function _mc_calc_atr($candles, $period = 14) {
    $n = count($candles);
    if ($n < 2) return 0;

    $trs = array();
    for ($i = 1; $i < $n; $i++) {
        $high = floatval($candles[$i]['h']);
        $low  = floatval($candles[$i]['l']);
        $prev_close = floatval($candles[$i - 1]['c']);
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

function _mc_binomial_significance($wins, $total, $null_p) {
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
    if ($abs_z >= 3.29) $p_value = 0.0005;
    elseif ($abs_z >= 2.58) $p_value = 0.005;
    elseif ($abs_z >= 2.33) $p_value = 0.01;
    elseif ($abs_z >= 1.96) $p_value = 0.025;
    elseif ($abs_z >= 1.65) $p_value = 0.05;
    elseif ($abs_z >= 1.28) $p_value = 0.10;
    else $p_value = 0.5;
    if ($z < 0) $p_value = 1 - $p_value;

    $is_sig = ($z > 0 && $p_value < 0.05);
    $confidence = 'not_significant';
    if ($total < 30) $confidence = 'insufficient_data';
    elseif ($is_sig && $p_value < 0.01) $confidence = 'highly_significant';
    elseif ($is_sig) $confidence = 'significant';
    elseif ($z > 0) $confidence = 'trending_positive';

    // Wilson CI
    $z95 = 1.96;
    $denom = 1 + $z95 * $z95 / $total;
    $center = ($observed_p + $z95 * $z95 / (2 * $total)) / $denom;
    $margin = $z95 * sqrt(($observed_p * (1 - $observed_p) + $z95 * $z95 / (4 * $total)) / $total) / $denom;
    $ci_low  = round(max(0, ($center - $margin)) * 100, 1);
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

function _mc_api($endpoint) {
    $url = 'https://api.crypto.com/exchange/v1/' . $endpoint;
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'MemeScanner/1.0');
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp) return null;
    return json_decode($resp, true);
}

function _mc_ends_with($str, $suffix) {
    return substr($str, -strlen($suffix)) === $suffix;
}

function _mc_sort_by_change($a, $b) {
    if ($b['chg_24h'] == $a['chg_24h']) return 0;
    return ($b['chg_24h'] > $a['chg_24h']) ? 1 : -1;
}

function _mc_sort_by_score($a, $b) {
    if ($b['score'] == $a['score']) return 0;
    return ($b['score'] > $a['score']) ? 1 : -1;
}

function _mc_discord_alert($winners, $scan_id, $analyzed, $elapsed) {
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

    $strong = 0;
    $buy = 0;
    $lean = 0;
    $msg_lines = array();
    foreach (array_slice($winners, 0, 8) as $w) {
        $pair = str_replace('_USDT', '/USDT', $w['pair']);
        $tier_label = ($w['tier'] === 'tier1') ? '' : ' [NEW]';
        $emoji = '';
        if ($w['verdict'] === 'STRONG_BUY') { $emoji = "\xF0\x9F\x9A\x80"; $strong++; }
        elseif ($w['verdict'] === 'BUY') { $emoji = "\xF0\x9F\x94\xB5"; $buy++; }
        else { $emoji = "\xF0\x9F\x9F\xA1"; $lean++; }
        $msg_lines[] = $emoji . ' **' . $pair . '**' . $tier_label . ' Score:' . $w['score'] . ' +' . round($w['chg_24h'], 1) . '% Target:+' . $w['target_pct'] . '%';
    }
    if (count($winners) > 8) {
        $msg_lines[] = '... and ' . (count($winners) - 8) . ' more';
    }

    $title = "\xF0\x9F\x90\xB8 Meme Scanner: " . count($winners) . ' meme' . (count($winners) > 1 ? 's' : '') . ' pumping!';
    $embed = array(
        'title' => $title,
        'description' => implode("\n", $msg_lines),
        'color' => ($strong > 0) ? 15277667 : (($buy > 0) ? 10181046 : 16776960),
        'footer' => array('text' => 'Scan #' . $scan_id . ' | ' . $analyzed . ' analyzed in ' . $elapsed . 's'),
        'url' => 'https://findtorontoevents.ca/findcryptopairs/meme.html'
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
function _mc_action_daily_picks($conn) {
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
function _mc_action_performance($conn) {
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
        if ($equity > $peak_equity) $peak_equity = $equity;
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
    if ($period === '7d') $period_sql = "AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)";
    elseif ($period === '30d') $period_sql = "AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)";
    elseif ($period === 'today') $period_sql = "AND DATE(created_at) = CURDATE()";

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
                if ($win_streak > $max_win_streak) $max_win_streak = $win_streak;
                $current_streak = $win_streak;
                $current_type = 'W';
            } else {
                $loss_streak++;
                $win_streak = 0;
                if ($loss_streak > $max_loss_streak) $max_loss_streak = $loss_streak;
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
function _mc_action_snapshot($conn) {
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

function _mc_err($msg) {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => $msg));
    exit;
}

function _mc_ensure_schema($conn) {
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
        created_at DATETIME NOT NULL,
        INDEX idx_mc_log_scan (scan_id),
        INDEX idx_mc_log_created (created_at)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

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
?>
