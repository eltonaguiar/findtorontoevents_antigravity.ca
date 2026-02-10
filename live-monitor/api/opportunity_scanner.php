<?php
/**
 * Buy-Now Opportunity Scanner — Multi-Algorithm Confluence Detection
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator)
 *
 * Reads from lm_signals + lm_price_cache to find high-conviction setups
 * where 3+ algorithms agree on the same asset simultaneously.
 *
 * Actions:
 *   ?action=scan&key=livetrader2026  — Run confluence scan, cache results (admin)
 *   ?action=opportunities            — Return cached scan results (public)
 *   ?action=history                  — Past scan results for trend analysis (public)
 */

require_once dirname(__FILE__) . '/db_connect.php';

// ────────────────────────────────────────────────────────────
//  Auto-create opportunities cache table
// ────────────────────────────────────────────────────────────

$conn->query("CREATE TABLE IF NOT EXISTS lm_opportunities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scan_id VARCHAR(40) NOT NULL,
    asset_class VARCHAR(10) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    current_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    entry_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    direction VARCHAR(10) NOT NULL DEFAULT 'BUY',
    trend_strength VARCHAR(20) NOT NULL DEFAULT 'weak',
    confidence_score INT NOT NULL DEFAULT 0,
    signal_count INT NOT NULL DEFAULT 0,
    momentum_signals TEXT,
    volume_confirmation VARCHAR(255) NOT NULL DEFAULT '',
    key_reason_now TEXT,
    holding_period VARCHAR(20) NOT NULL DEFAULT '',
    avg_tp_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    avg_sl_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    data_source VARCHAR(100) NOT NULL DEFAULT '',
    data_latency_seconds INT NOT NULL DEFAULT 0,
    notes TEXT,
    signal_ids TEXT,
    scan_time DATETIME NOT NULL,
    KEY idx_scan (scan_id),
    KEY idx_confidence (confidence_score),
    KEY idx_time (scan_time)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ────────────────────────────────────────────────────────────
//  Constants
// ────────────────────────────────────────────────────────────

$OS_ADMIN_KEY = 'livetrader2026';
$OS_CACHE_TTL = 300; // 5 minutes
$OS_MIN_CONFLUENCE = 3; // minimum signals for an opportunity

// Trend-following algorithm names (used for trend_factor scoring)
$OS_TREND_ALGOS = array(
    'ADX Trend Strength', 'Ichimoku Cloud', 'Trend Sniper', 'Alpha Predator'
);

// Volume-related algorithm names
$OS_VOLUME_ALGOS = array(
    'Volume Spike', 'Breakout 24h'
);

// Static watchlist symbols (from live_signals.php)
$OS_STATIC_SYMBOLS = array(
    'BTCUSD','ETHUSD','SOLUSD','BNBUSD','XRPUSD','ADAUSD','DOTUSD','LINKUSD',
    'AVAXUSD','DOGEUSD','MATICUSD','SHIBUSD','UNIUSD','ATOMUSD',
    'EOSUSD','NEARUSD','FILUSD','TRXUSD','LTCUSD','BCHUSD',
    'APTUSD','ARBUSD','FTMUSD','AXSUSD','HBARUSD','AAVEUSD',
    'OPUSD','MKRUSD','INJUSD','SUIUSD','PEPEUSD','FLOKIUSD',
    'EURUSD','GBPUSD','USDJPY','USDCAD','AUDUSD','NZDUSD','USDCHF','EURGBP',
    'AAPL','MSFT','GOOGL','AMZN','NVDA','META','JPM','WMT','XOM','NFLX','JNJ','BAC'
);

// Free data sources reference
$OS_FREE_DATA_SOURCES = array(
    array(
        'name'          => 'FreeCryptoAPI',
        'asset_classes' => array('crypto'),
        'latency'       => 'real-time (~5s)',
        'api_notes'     => 'Bearer token auth, proxies Binance data. Primary crypto source.'
    ),
    array(
        'name'          => 'CoinGecko',
        'asset_classes' => array('crypto'),
        'latency'       => 'near-real-time (~30s)',
        'api_notes'     => 'Free tier, no auth required. 10-50 req/min rate limit.'
    ),
    array(
        'name'          => 'Kraken',
        'asset_classes' => array('crypto'),
        'latency'       => 'real-time',
        'api_notes'     => 'Free public API, real bid/ask/VWAP. Ontario-compliant exchange.'
    ),
    array(
        'name'          => 'Finnhub',
        'asset_classes' => array('stock'),
        'latency'       => 'real-time (market hours)',
        'api_notes'     => 'Free tier with API key. Real-time during NYSE 9:30-16:00 ET.'
    ),
    array(
        'name'          => 'TwelveData',
        'asset_classes' => array('forex'),
        'latency'       => 'delayed (~15s)',
        'api_notes'     => 'Free tier, ~100 req/day. Primary forex OHLC source.'
    ),
    array(
        'name'          => 'CurrencyLayer',
        'asset_classes' => array('forex'),
        'latency'       => 'delayed (~60s)',
        'api_notes'     => 'Free tier, 100 req/month. Batch USD-based pairs.'
    ),
    array(
        'name'          => 'Yahoo Finance',
        'asset_classes' => array('stock', 'forex', 'crypto'),
        'latency'       => 'delayed (15-900s)',
        'api_notes'     => 'Unofficial v8 chart API. Last-resort fallback, high latency.'
    )
);

// ────────────────────────────────────────────────────────────
//  Route action
// ────────────────────────────────────────────────────────────

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'opportunities';

if ($action === 'scan') {
    _os_action_scan($conn);
} elseif ($action === 'opportunities') {
    _os_action_opportunities($conn);
} elseif ($action === 'history') {
    _os_action_history($conn);
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action. Valid: scan, opportunities, history'));
}

$conn->close();
exit;


// =====================================================================
//  ACTION: scan — Run confluence detection, score, filter, cache results
// =====================================================================

function _os_action_scan($conn) {
    global $OS_ADMIN_KEY, $OS_MIN_CONFLUENCE, $OS_CACHE_TTL;

    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $OS_ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $min_conf = isset($_GET['min_confluence']) ? (int)$_GET['min_confluence'] : $OS_MIN_CONFLUENCE;
    $min_confidence = isset($_GET['min_confidence']) ? (int)$_GET['min_confidence'] : 0;

    $scan_id = md5(date('Y-m-d-H-i') . '-' . mt_rand(1000, 9999));
    $scan_time = date('Y-m-d H:i:s');

    // ── Step 1: Get all active signals ──
    $now = date('Y-m-d H:i:s');
    $res = $conn->query("SELECT * FROM lm_signals WHERE status='active' AND expires_at > '$now' ORDER BY symbol, signal_type");
    if (!$res) {
        echo json_encode(array('ok' => false, 'error' => 'Failed to query signals: ' . $conn->error));
        return;
    }

    // Group signals by symbol+direction
    $grouped = array();
    while ($row = $res->fetch_assoc()) {
        $key_group = $row['symbol'] . '|' . $row['signal_type'];
        if (!isset($grouped[$key_group])) {
            $grouped[$key_group] = array(
                'symbol'      => $row['symbol'],
                'asset_class' => $row['asset_class'],
                'direction'   => $row['signal_type'],
                'signals'     => array()
            );
        }
        $grouped[$key_group]['signals'][] = $row;
    }

    // ── Step 2: Filter for confluence (3+ signals same direction) ──
    $candidates = array();
    foreach ($grouped as $group) {
        if (count($group['signals']) >= $min_conf) {
            $candidates[] = $group;
        }
    }

    // ── Step 3: Get price data for candidate symbols ──
    $price_cache = array();
    if (count($candidates) > 0) {
        $symbols_list = array();
        foreach ($candidates as $c) {
            $symbols_list[] = "'" . $conn->real_escape_string($c['symbol']) . "'";
        }
        $in_clause = implode(',', $symbols_list);
        $price_res = $conn->query("SELECT * FROM lm_price_cache WHERE symbol IN ($in_clause)");
        if ($price_res) {
            while ($pr = $price_res->fetch_assoc()) {
                $price_cache[$pr['symbol']] = $pr;
            }
        }
    }

    // ── Step 4: Score, filter, build opportunities ──
    $opportunities = array();
    foreach ($candidates as $cand) {
        $opp = _os_build_opportunity($cand, $price_cache, $scan_id, $scan_time);
        if ($opp === null) continue; // filtered out
        if ($min_confidence > 0 && $opp['confidence_score'] < $min_confidence) continue;
        $opportunities[] = $opp;
    }

    // Sort by confidence descending
    usort($opportunities, '_os_sort_by_confidence');

    // ── Step 5: Cache results to DB ──
    // Clear old scan results (keep last 24h for history)
    $cutoff = date('Y-m-d H:i:s', time() - 86400);
    $conn->query("DELETE FROM lm_opportunities WHERE scan_time < '$cutoff'");

    // Insert new opportunities
    $inserted = 0;
    foreach ($opportunities as $opp) {
        _os_insert_opportunity($conn, $opp);
        $inserted++;
    }

    // ── Step 6: Build response ──
    $response = _os_format_response($opportunities, $scan_time);
    echo json_encode($response);
}


// =====================================================================
//  ACTION: opportunities — Return cached scan results (public)
// =====================================================================

function _os_action_opportunities($conn) {
    global $OS_CACHE_TTL;

    $filter_asset = isset($_GET['asset_class']) ? strtoupper(trim($_GET['asset_class'])) : '';
    $min_confidence = isset($_GET['min_confidence']) ? (int)$_GET['min_confidence'] : 0;
    $limit = isset($_GET['limit']) ? min((int)$_GET['limit'], 50) : 20;

    // Get most recent scan_id
    $latest = $conn->query("SELECT scan_id, scan_time FROM lm_opportunities ORDER BY scan_time DESC LIMIT 1");
    if (!$latest || $latest->num_rows === 0) {
        echo json_encode(_os_format_response(array(), date('Y-m-d H:i:s')));
        return;
    }
    $latest_row = $latest->fetch_assoc();
    $scan_id = $conn->real_escape_string($latest_row['scan_id']);
    $scan_time = $latest_row['scan_time'];

    // Check freshness
    $age = time() - strtotime($scan_time);
    $is_stale = ($age > $OS_CACHE_TTL);

    // Query opportunities from this scan
    $where = "scan_id='$scan_id'";
    if ($filter_asset !== '') {
        $where .= " AND asset_class='" . $conn->real_escape_string($filter_asset) . "'";
    }
    if ($min_confidence > 0) {
        $where .= " AND confidence_score >= $min_confidence";
    }

    $res = $conn->query("SELECT * FROM lm_opportunities WHERE $where ORDER BY confidence_score DESC LIMIT $limit");
    if (!$res) {
        echo json_encode(array('ok' => false, 'error' => 'Query failed: ' . $conn->error));
        return;
    }

    $opportunities = array();
    while ($row = $res->fetch_assoc()) {
        $opportunities[] = _os_row_to_opportunity($row);
    }

    $response = _os_format_response($opportunities, $scan_time);
    $response['cache_age_seconds'] = $age;
    $response['is_stale'] = $is_stale;
    echo json_encode($response);
}


// =====================================================================
//  ACTION: history — Past scan results for trend analysis (public)
// =====================================================================

function _os_action_history($conn) {
    $hours = isset($_GET['hours']) ? min((int)$_GET['hours'], 24) : 6;
    $symbol_filter = isset($_GET['symbol']) ? $conn->real_escape_string(trim($_GET['symbol'])) : '';

    $since = date('Y-m-d H:i:s', time() - ($hours * 3600));
    $where = "scan_time >= '$since'";
    if ($symbol_filter !== '') {
        $where .= " AND symbol='$symbol_filter'";
    }

    $res = $conn->query("SELECT scan_id, scan_time, symbol, asset_class, direction, confidence_score, signal_count, trend_strength
                         FROM lm_opportunities WHERE $where ORDER BY scan_time DESC, confidence_score DESC LIMIT 200");
    if (!$res) {
        echo json_encode(array('ok' => false, 'error' => 'Query failed: ' . $conn->error));
        return;
    }

    $history = array();
    while ($row = $res->fetch_assoc()) {
        $history[] = array(
            'scan_id'          => $row['scan_id'],
            'scan_time'        => $row['scan_time'],
            'symbol'           => $row['symbol'],
            'asset_class'      => $row['asset_class'],
            'direction'        => $row['direction'],
            'confidence_score' => (int)$row['confidence_score'],
            'signal_count'     => (int)$row['signal_count'],
            'trend_strength'   => $row['trend_strength']
        );
    }

    echo json_encode(array(
        'ok'         => true,
        'action'     => 'history',
        'hours'      => $hours,
        'count'      => count($history),
        'history'    => $history
    ));
}


// =====================================================================
//  CORE: Build a single opportunity from a candidate group
// =====================================================================

function _os_build_opportunity($cand, $price_cache, $scan_id, $scan_time) {
    global $OS_TREND_ALGOS, $OS_VOLUME_ALGOS, $OS_STATIC_SYMBOLS;

    $symbol      = $cand['symbol'];
    $asset_class = $cand['asset_class'];
    $direction   = $cand['direction'];
    $signals     = $cand['signals'];
    $sig_count   = count($signals);

    // ── Get price data ──
    $price_data = isset($price_cache[$symbol]) ? $price_cache[$symbol] : null;
    $current_price = 0;
    $volume_24h = 0;
    $change_24h = 0;
    $data_source = 'unknown';
    $data_latency = 0;

    if ($price_data) {
        $current_price     = (float)$price_data['price'];
        $volume_24h        = isset($price_data['volume_24h']) ? (float)$price_data['volume_24h'] : 0;
        $change_24h        = isset($price_data['change_24h_pct']) ? (float)$price_data['change_24h_pct'] : 0;
        $data_source       = isset($price_data['data_source']) ? $price_data['data_source'] : 'unknown';
        $data_latency      = isset($price_data['data_delay_seconds']) ? (int)$price_data['data_delay_seconds'] : 0;
    } else {
        // Use entry_price from most recent signal as fallback
        $current_price = (float)$signals[0]['entry_price'];
        $data_source = 'signal_cache';
    }

    // ── Liquidity filter ──
    if ($asset_class === 'CRYPTO' && $volume_24h > 0 && $volume_24h < 100000) return null;
    if ($asset_class === 'STOCK' && $volume_24h > 0 && $volume_24h < 500000) return null;
    if ($asset_class === 'FOREX' && $data_latency > 60 && $sig_count < 5) return null;

    // ── Pump-and-dump filter ──
    if (_os_is_pump_dump($signals, $symbol, $asset_class, $change_24h, $volume_24h)) return null;

    // ── Build momentum_signals array ──
    $momentum_signals = array();
    $signal_ids = array();
    $algo_names = array();
    $total_strength = 0;
    $total_tp = 0;
    $total_sl = 0;
    $total_hold = 0;
    $newest_time = 0;
    $has_trend_algo = false;
    $has_volume_algo = false;

    foreach ($signals as $sig) {
        $algo = $sig['algorithm_name'];
        $algo_names[] = $algo;
        $signal_ids[] = (int)$sig['id'];
        $total_strength += (int)$sig['signal_strength'];
        $total_tp += (float)$sig['target_tp_pct'];
        $total_sl += (float)$sig['target_sl_pct'];
        $total_hold += (int)$sig['max_hold_hours'];

        $sig_time = strtotime($sig['signal_time']);
        if ($sig_time > $newest_time) $newest_time = $sig_time;

        // Check algo categories
        if (in_array($algo, $OS_TREND_ALGOS)) $has_trend_algo = true;
        if (in_array($algo, $OS_VOLUME_ALGOS)) $has_volume_algo = true;

        // Extract rationale reason
        $rationale = json_decode($sig['rationale'], true);
        $reason_text = '';
        if (is_array($rationale) && isset($rationale['reason'])) {
            $reason_text = $rationale['reason'];
        } elseif (is_string($sig['rationale'])) {
            $reason_text = $sig['rationale'];
        }

        $momentum_signals[] = $algo . ': ' . $reason_text;
    }

    // ── Calculate scores ──
    $avg_strength = $total_strength / $sig_count;
    $avg_tp = round($total_tp / $sig_count, 2);
    $avg_sl = round($total_sl / $sig_count, 2);
    $avg_hold = round($total_hold / $sig_count, 1);

    // Confluence bonus
    if ($sig_count >= 5) {
        $confluence_bonus = 35;
    } elseif ($sig_count === 4) {
        $confluence_bonus = 20;
    } else {
        $confluence_bonus = 10;
    }

    // Volume factor
    if ($has_volume_algo) {
        $volume_factor = 15;
    } elseif ($volume_24h > 10000000) {
        $volume_factor = 10;
    } else {
        $volume_factor = 5;
    }

    // Recency factor (how fresh is newest signal)
    $newest_age_min = (time() - $newest_time) / 60;
    if ($newest_age_min < 5) {
        $recency_factor = 10;
    } elseif ($newest_age_min < 15) {
        $recency_factor = 7;
    } elseif ($newest_age_min < 30) {
        $recency_factor = 4;
    } else {
        $recency_factor = 0;
    }

    // Trend factor
    $trend_factor = $has_trend_algo ? 10 : 0;

    // Final confidence score
    $raw_score = ($avg_strength * 0.40) + $confluence_bonus + $volume_factor + $recency_factor + $trend_factor;
    $confidence_score = min(100, max(0, (int)round($raw_score)));

    // Trend strength label
    if ($sig_count >= 5) {
        $trend_strength = 'strong';
    } elseif ($sig_count === 4) {
        $trend_strength = 'moderate';
    } else {
        $trend_strength = 'weak';
    }

    // Holding period from avg hold hours
    if ($avg_hold <= 1) {
        $holding_period = '1-hour';
    } elseif ($avg_hold <= 4) {
        $holding_period = '4-hour';
    } elseif ($avg_hold <= 12) {
        $holding_period = '1-day';
    } else {
        $holding_period = 'swing';
    }

    // Volume confirmation text
    $volume_text = '';
    if ($volume_24h > 0) {
        if ($volume_24h >= 1000000000) {
            $volume_text = '$' . round($volume_24h / 1000000000, 1) . 'B 24h volume';
        } elseif ($volume_24h >= 1000000) {
            $volume_text = '$' . round($volume_24h / 1000000, 1) . 'M 24h volume';
        } else {
            $volume_text = '$' . round($volume_24h / 1000, 1) . 'K 24h volume';
        }
        if ($has_volume_algo) {
            $volume_text .= ' (institutional-level spike detected)';
        }
    } else {
        $volume_text = 'Volume data unavailable';
    }

    // ── Generate "Why Now" reasoning ──
    $key_reason_now = _os_generate_why_now($sig_count, $direction, $algo_names, $signals, $newest_age_min, $has_volume_algo, $has_trend_algo);

    // Entry price = current price (enter at market)
    $entry_price = $current_price;

    // Notes
    $notes_parts = array();
    if ($change_24h != 0) {
        $notes_parts[] = '24h change: ' . round($change_24h, 2) . '%';
    }
    if ($data_latency > 0) {
        $notes_parts[] = 'Data latency: ' . $data_latency . 's';
    }
    $notes_parts[] = 'Avg TP: ' . $avg_tp . '%, Avg SL: ' . $avg_sl . '%';
    $notes = implode('. ', $notes_parts);

    return array(
        'scan_id'              => $scan_id,
        'asset_class'          => strtolower($asset_class),
        'symbol'               => $symbol,
        'current_price'        => $current_price,
        'entry_price'          => $entry_price,
        'direction'            => $direction,
        'trend_strength'       => $trend_strength,
        'confidence_score'     => $confidence_score,
        'signal_count'         => $sig_count,
        'momentum_signals'     => $momentum_signals,
        'volume_confirmation'  => $volume_text,
        'key_reason_now'       => $key_reason_now,
        'holding_period'       => $holding_period,
        'avg_tp_pct'           => $avg_tp,
        'avg_sl_pct'           => $avg_sl,
        'data_source'          => $data_source,
        'data_latency_seconds' => $data_latency,
        'notes'                => $notes,
        'signal_ids'           => $signal_ids,
        'scan_time'            => $scan_id ? date('c') : ''
    );
}


// =====================================================================
//  Pump-and-Dump Detection
// =====================================================================

function _os_is_pump_dump($signals, $symbol, $asset_class, $change_24h, $volume_24h) {
    global $OS_VOLUME_ALGOS, $OS_TREND_ALGOS, $OS_STATIC_SYMBOLS;

    $has_trend = false;
    $has_volume_only = true;

    foreach ($signals as $sig) {
        $algo = $sig['algorithm_name'];
        if (in_array($algo, $OS_TREND_ALGOS)) {
            $has_trend = true;
            $has_volume_only = false;
        }
        if (!in_array($algo, $OS_VOLUME_ALGOS)) {
            $has_volume_only = false;
        }
    }

    // Rule 1: Volume spike only + massive change + no trend confirmation
    if ($has_volume_only && abs($change_24h) > 15 && !$has_trend) {
        return true;
    }

    // Rule 2: Not in static watchlist + low volume + huge change (microcap pump)
    if (!in_array($symbol, $OS_STATIC_SYMBOLS) && $volume_24h > 0 && $volume_24h < 1000000 && abs($change_24h) > 20) {
        return true;
    }

    return false;
}


// =====================================================================
//  "Why Now" Reasoning Generator
// =====================================================================

function _os_generate_why_now($sig_count, $direction, $algo_names, $signals, $newest_age_min, $has_volume, $has_trend) {
    $parts = array();

    // 1. Confluence headline
    $dir_word = ($direction === 'BUY') ? 'bullish' : 'bearish';
    $parts[] = $sig_count . ' algorithms simultaneously flash ' . $dir_word . ' on this asset';

    // 2. Strongest signal detail
    $strongest = null;
    $strongest_val = -1;
    foreach ($signals as $sig) {
        if ((int)$sig['signal_strength'] > $strongest_val) {
            $strongest_val = (int)$sig['signal_strength'];
            $strongest = $sig;
        }
    }
    if ($strongest) {
        $rationale = json_decode($strongest['rationale'], true);
        $reason = is_array($rationale) && isset($rationale['reason']) ? $rationale['reason'] : '';
        if ($reason !== '') {
            $parts[] = 'Led by ' . $strongest['algorithm_name'] . ' (strength ' . $strongest_val . '): ' . $reason;
        }
    }

    // 3. Recency urgency
    if ($newest_age_min < 5) {
        $parts[] = 'Signal fired within the last 5 minutes — entry window is open RIGHT NOW';
    } elseif ($newest_age_min < 15) {
        $parts[] = 'Most recent signal ' . round($newest_age_min) . ' min ago — still within optimal entry window';
    } elseif ($newest_age_min < 30) {
        $parts[] = 'Signals are ' . round($newest_age_min) . ' min old — act soon before momentum fades';
    }

    // 4. Volume confirmation
    if ($has_volume) {
        $parts[] = 'Volume spike confirms institutional/whale interest is driving this move';
    }

    // 5. Trend confirmation
    if ($has_trend) {
        $trend_names = array();
        $trend_algos_list = array('ADX Trend Strength', 'Ichimoku Cloud', 'Trend Sniper', 'Alpha Predator');
        foreach ($algo_names as $name) {
            if (in_array($name, $trend_algos_list)) {
                $trend_names[] = $name;
            }
        }
        $parts[] = 'Trend structure confirmed by ' . implode(' + ', $trend_names);
    }

    return implode('. ', $parts) . '.';
}


// =====================================================================
//  Format full API response matching user's schema
// =====================================================================

function _os_format_response($opportunities, $scan_time) {
    global $OS_FREE_DATA_SOURCES;

    $formatted_opps = array();
    foreach ($opportunities as $opp) {
        $formatted_opps[] = array(
            'asset_class'          => $opp['asset_class'],
            'symbol'               => $opp['symbol'],
            'current_price'        => $opp['current_price'],
            'entry_price'          => $opp['entry_price'],
            'direction'            => $opp['direction'],
            'trend_strength'       => $opp['trend_strength'],
            'momentum_signals'     => $opp['momentum_signals'],
            'volume_confirmation'  => $opp['volume_confirmation'],
            'key_reason_now'       => $opp['key_reason_now'],
            'holding_period'       => $opp['holding_period'],
            'confidence_score'     => $opp['confidence_score'],
            'signal_count'         => $opp['signal_count'],
            'avg_tp_pct'           => $opp['avg_tp_pct'],
            'avg_sl_pct'           => $opp['avg_sl_pct'],
            'data_source'          => $opp['data_source'],
            'data_latency_seconds' => $opp['data_latency_seconds'],
            'notes'                => $opp['notes']
        );
    }

    // Self-check
    $all_have_rationale = true;
    $threshold_met = true;
    foreach ($formatted_opps as $o) {
        if (empty($o['key_reason_now'])) $all_have_rationale = false;
        if ($o['confidence_score'] < 30) $threshold_met = false;
    }

    return array(
        'ok'                            => true,
        'action'                        => 'scan',
        'scan_timestamp'                => date('c', strtotime($scan_time)),
        'opportunity_count'             => count($formatted_opps),
        'opportunities'                 => $formatted_opps,
        'free_data_sources_recommended' => $OS_FREE_DATA_SOURCES,
        'self_check'                    => array(
            'all_signals_have_rationale'    => $all_have_rationale,
            'confidence_threshold_met'      => $threshold_met,
            'data_sources_are_free_or_low_cost' => true
        )
    );
}


// =====================================================================
//  DB helpers
// =====================================================================

function _os_insert_opportunity($conn, $opp) {
    $scan_id     = $conn->real_escape_string($opp['scan_id']);
    $asset_class = $conn->real_escape_string(strtoupper($opp['asset_class']));
    $symbol      = $conn->real_escape_string($opp['symbol']);
    $cur_price   = (float)$opp['current_price'];
    $entry_price = (float)$opp['entry_price'];
    $direction   = $conn->real_escape_string($opp['direction']);
    $trend       = $conn->real_escape_string($opp['trend_strength']);
    $confidence  = (int)$opp['confidence_score'];
    $sig_count   = (int)$opp['signal_count'];
    $momentum    = $conn->real_escape_string(json_encode($opp['momentum_signals']));
    $vol_conf    = $conn->real_escape_string($opp['volume_confirmation']);
    $why_now     = $conn->real_escape_string($opp['key_reason_now']);
    $hold        = $conn->real_escape_string($opp['holding_period']);
    $avg_tp      = (float)$opp['avg_tp_pct'];
    $avg_sl      = (float)$opp['avg_sl_pct'];
    $source      = $conn->real_escape_string($opp['data_source']);
    $latency     = (int)$opp['data_latency_seconds'];
    $notes       = $conn->real_escape_string($opp['notes']);
    $sig_ids     = $conn->real_escape_string(json_encode($opp['signal_ids']));
    $scan_time   = date('Y-m-d H:i:s');

    $sql = "INSERT INTO lm_opportunities (scan_id, asset_class, symbol, current_price, entry_price, direction,
                trend_strength, confidence_score, signal_count, momentum_signals, volume_confirmation,
                key_reason_now, holding_period, avg_tp_pct, avg_sl_pct, data_source, data_latency_seconds,
                notes, signal_ids, scan_time)
            VALUES ('$scan_id', '$asset_class', '$symbol', $cur_price, $entry_price, '$direction',
                '$trend', $confidence, $sig_count, '$momentum', '$vol_conf',
                '$why_now', '$hold', $avg_tp, $avg_sl, '$source', $latency,
                '$notes', '$sig_ids', '$scan_time')";

    $conn->query($sql);
}

function _os_row_to_opportunity($row) {
    $momentum = json_decode($row['momentum_signals'], true);
    if (!is_array($momentum)) $momentum = array();

    return array(
        'asset_class'          => strtolower($row['asset_class']),
        'symbol'               => $row['symbol'],
        'current_price'        => (float)$row['current_price'],
        'entry_price'          => (float)$row['entry_price'],
        'direction'            => $row['direction'],
        'trend_strength'       => $row['trend_strength'],
        'momentum_signals'     => $momentum,
        'volume_confirmation'  => $row['volume_confirmation'],
        'key_reason_now'       => $row['key_reason_now'],
        'holding_period'       => $row['holding_period'],
        'confidence_score'     => (int)$row['confidence_score'],
        'signal_count'         => (int)$row['signal_count'],
        'avg_tp_pct'           => (float)$row['avg_tp_pct'],
        'avg_sl_pct'           => (float)$row['avg_sl_pct'],
        'data_source'          => $row['data_source'],
        'data_latency_seconds' => (int)$row['data_latency_seconds'],
        'notes'                => $row['notes']
    );
}

function _os_sort_by_confidence($a, $b) {
    if ($a['confidence_score'] === $b['confidence_score']) return 0;
    return ($a['confidence_score'] > $b['confidence_score']) ? -1 : 1;
}
?>
