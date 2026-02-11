<?php
/**
 * Fear & Greed Composite Index API
 * Aggregates crypto F&G (alternative.me), VIX-based market F&G,
 * and a composite score from news sentiment + insider activity + 13F data.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=index         — All three scores (crypto, cnn, composite)
 *   ?action=crypto        — Crypto Fear & Greed (alternative.me)
 *   ?action=cnn           — CNN/VIX-based Fear & Greed
 *   ?action=composite     — Weighted composite with breakdown
 *   ?action=history       — 30-day history from DB
 *   ?action=fetch&key=... — Admin: force-fetch and store all sources
 */
require_once dirname(__FILE__) . '/db_connect.php';

// ── Ensure schema ──
$conn->query("CREATE TABLE IF NOT EXISTS lm_fear_greed (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(20) NOT NULL,
    score INT NOT NULL DEFAULT 50,
    classification VARCHAR(30) NOT NULL DEFAULT 'neutral',
    components TEXT,
    fetch_date DATE NOT NULL,
    fetch_time DATETIME NOT NULL,
    UNIQUE KEY idx_source_date (source, fetch_date),
    KEY idx_source (source),
    KEY idx_date (fetch_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? $_GET['action'] : 'index';
$admin_key = isset($_GET['key']) ? $_GET['key'] : '';
$nocache = isset($_GET['nocache']) ? true : false;

// ─────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────
function _fg_esc($conn, $val) {
    return $conn->real_escape_string($val);
}

function _fg_classify($score) {
    if ($score <= 20) return 'extreme_fear';
    if ($score <= 40) return 'fear';
    if ($score <= 60) return 'neutral';
    if ($score <= 80) return 'greed';
    return 'extreme_greed';
}

function _fg_http_get($url) {
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'FearGreedTracker/1.0 contact@findtorontoevents.ca');
        $result = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($code >= 200 && $code < 300 && $result !== false) return $result;
    }
    $ctx = stream_context_create(array('http' => array(
        'timeout' => 15,
        'header' => "User-Agent: FearGreedTracker/1.0\r\n"
    )));
    $result = @file_get_contents($url, false, $ctx);
    return ($result !== false) ? $result : null;
}

// File cache
function _fg_cache_get($key, $ttl) {
    $file = dirname(__FILE__) . '/cache/fg_' . md5($key) . '.json';
    if (!file_exists($file)) return null;
    if ((time() - filemtime($file)) > $ttl) return null;
    $data = @file_get_contents($file);
    return ($data !== false) ? json_decode($data, true) : null;
}

function _fg_cache_set($key, $data) {
    $dir = dirname(__FILE__) . '/cache';
    if (!is_dir($dir)) @mkdir($dir, 0777, true);
    $file = $dir . '/fg_' . md5($key) . '.json';
    @file_put_contents($file, json_encode($data));
}

// ─────────────────────────────────────────
//  Fetch: Crypto Fear & Greed (alternative.me)
// ─────────────────────────────────────────
function _fg_fetch_crypto() {
    $cached = _fg_cache_get('crypto_fg', 3600);
    if ($cached !== null) return $cached;

    $raw = _fg_http_get('https://api.alternative.me/fng/?limit=30&format=json');
    if ($raw === null) return array('score' => 50, 'classification' => 'neutral', 'source' => 'alternative.me', 'error' => 'fetch_failed');

    $json = json_decode($raw, true);
    if (!isset($json['data']) || !is_array($json['data']) || count($json['data']) === 0) {
        return array('score' => 50, 'classification' => 'neutral', 'source' => 'alternative.me', 'error' => 'parse_failed');
    }

    $latest = $json['data'][0];
    $score = intval($latest['value']);
    $result = array(
        'score' => $score,
        'classification' => _fg_classify($score),
        'label' => isset($latest['value_classification']) ? $latest['value_classification'] : _fg_classify($score),
        'source' => 'alternative.me',
        'timestamp' => isset($latest['timestamp']) ? intval($latest['timestamp']) : time(),
        'history' => array()
    );

    // Include 30-day history
    foreach ($json['data'] as $d) {
        $result['history'][] = array(
            'score' => intval($d['value']),
            'date' => date('Y-m-d', intval($d['timestamp'])),
            'label' => isset($d['value_classification']) ? $d['value_classification'] : ''
        );
    }

    _fg_cache_set('crypto_fg', $result);
    return $result;
}

// ─────────────────────────────────────────
//  Fetch: CNN/VIX-based Fear & Greed
// ─────────────────────────────────────────
function _fg_fetch_cnn($conn) {
    $cached = _fg_cache_get('cnn_fg', 3600);
    if ($cached !== null) return $cached;

    // Compute from VIX in market_regimes table
    $r = $conn->query("SELECT vix_close, regime, trade_date FROM market_regimes ORDER BY trade_date DESC LIMIT 1");
    $vix = 20;
    $regime = 'moderate_bull';
    $trade_date = date('Y-m-d');
    if ($r && $row = $r->fetch_assoc()) {
        $vix = floatval($row['vix_close']);
        $regime = $row['regime'];
        $trade_date = $row['trade_date'];
    }

    // VIX → inverted Fear/Greed score
    // VIX 40+ = extreme fear (score ~5), VIX 10 = extreme greed (score ~90)
    $vix_score = max(0, min(100, round(100 - ($vix - 10) * (100 / 30))));

    // Regime → score mapping
    $regime_scores = array(
        'extreme_vol'   => 10,
        'high_vol'      => 25,
        'moderate_bear'  => 35,
        'calm_bear'      => 45,
        'moderate_bull'  => 65,
        'calm_bull'      => 80
    );
    $regime_score = isset($regime_scores[$regime]) ? $regime_scores[$regime] : 50;

    // Blend: 60% VIX score + 40% regime score
    $score = round($vix_score * 0.6 + $regime_score * 0.4);
    $score = max(0, min(100, $score));

    $result = array(
        'score' => $score,
        'classification' => _fg_classify($score),
        'source' => 'vix_regime',
        'vix' => $vix,
        'vix_score' => $vix_score,
        'regime' => $regime,
        'regime_score' => $regime_score,
        'trade_date' => $trade_date
    );

    _fg_cache_set('cnn_fg', $result);
    return $result;
}

// ─────────────────────────────────────────
//  Compute: Composite from all sources
// ─────────────────────────────────────────
function _fg_compute_composite($conn) {
    $cached = _fg_cache_get('composite_fg', 3600);
    if ($cached !== null) return $cached;

    $components = array();

    // 1. VIX component (30% weight)
    $cnn = _fg_fetch_cnn($conn);
    $vix_score = $cnn['score'];
    $components['vix'] = array('score' => $vix_score, 'weight' => 0.30, 'detail' => 'VIX=' . $cnn['vix'] . ' regime=' . $cnn['regime']);

    // 2. News sentiment avg (20% weight)
    $r = $conn->query("SELECT AVG(sentiment_score) as avg_sent FROM gm_news_sentiment WHERE fetch_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)");
    $news_score = 50;
    if ($r && $row = $r->fetch_assoc() && $row['avg_sent'] !== null) {
        // sentiment_score is -1 to +1, map to 0-100
        $news_score = round(($row['avg_sent'] + 1) * 50);
        $news_score = max(0, min(100, $news_score));
    }
    $components['news_sentiment'] = array('score' => $news_score, 'weight' => 0.20, 'detail' => 'avg_sentiment_7d');

    // 3. Insider net buy ratio (20% weight)
    $r2 = $conn->query("SELECT
        SUM(CASE WHEN transaction_type = 'P' THEN total_value ELSE 0 END) as buy_val,
        SUM(CASE WHEN transaction_type = 'S' THEN total_value ELSE 0 END) as sell_val
        FROM gm_sec_insider_trades
        WHERE transaction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)");
    $insider_score = 50;
    if ($r2 && $row2 = $r2->fetch_assoc()) {
        $buy = floatval($row2['buy_val']);
        $sell = floatval($row2['sell_val']);
        $total = $buy + $sell;
        if ($total > 0) {
            $insider_score = round(($buy / $total) * 100);
            $insider_score = max(0, min(100, $insider_score));
        }
    }
    $components['insider_activity'] = array('score' => $insider_score, 'weight' => 0.20, 'detail' => 'net_buy_ratio_30d');

    // 4. 13F net bullish (15% weight)
    $r3 = $conn->query("SELECT
        SUM(CASE WHEN change_type IN ('new','increased') THEN 1 ELSE 0 END) as bullish,
        SUM(CASE WHEN change_type IN ('decreased','sold_all') THEN 1 ELSE 0 END) as bearish,
        COUNT(*) as total
        FROM gm_sec_13f_holdings
        WHERE filing_quarter = (SELECT MAX(filing_quarter) FROM gm_sec_13f_holdings)");
    $f13_score = 50;
    if ($r3 && $row3 = $r3->fetch_assoc()) {
        $bull = intval($row3['bullish']);
        $bear = intval($row3['bearish']);
        $total = $bull + $bear;
        if ($total > 0) {
            $f13_score = round(($bull / $total) * 100);
            $f13_score = max(0, min(100, $f13_score));
        }
    }
    $components['13f_holdings'] = array('score' => $f13_score, 'weight' => 0.15, 'detail' => 'latest_quarter_bullish_ratio');

    // 5. Crypto Fear & Greed (15% weight)
    $crypto = _fg_fetch_crypto();
    $crypto_score = intval($crypto['score']);
    $components['crypto_fg'] = array('score' => $crypto_score, 'weight' => 0.15, 'detail' => 'alternative.me');

    // Weighted composite
    $composite = 0;
    foreach ($components as $c) {
        $composite += $c['score'] * $c['weight'];
    }
    $composite = round(max(0, min(100, $composite)));

    $result = array(
        'score' => $composite,
        'classification' => _fg_classify($composite),
        'source' => 'composite',
        'components' => $components,
        'computed_at' => gmdate('Y-m-d H:i:s')
    );

    _fg_cache_set('composite_fg', $result);
    return $result;
}

// ─────────────────────────────────────────
//  Store scores in DB
// ─────────────────────────────────────────
function _fg_store($conn, $source, $score, $classification, $components_json) {
    $src = _fg_esc($conn, $source);
    $cls = _fg_esc($conn, $classification);
    $cmp = _fg_esc($conn, $components_json);
    $today = date('Y-m-d');
    $now = gmdate('Y-m-d H:i:s');

    // Upsert (replace if same source+date)
    $conn->query("DELETE FROM lm_fear_greed WHERE source = '$src' AND fetch_date = '$today'");
    $conn->query("INSERT INTO lm_fear_greed (source, score, classification, components, fetch_date, fetch_time)
        VALUES ('$src', $score, '$cls', '$cmp', '$today', '$now')");
}

// ═══════════════════════════════════════════
//  Action: fetch (admin) — force-fetch all
// ═══════════════════════════════════════════
if ($action === 'fetch') {
    if ($admin_key !== 'livetrader2026') {
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        $conn->close();
        exit;
    }

    // Force clear cache
    $dir = dirname(__FILE__) . '/cache';
    foreach (array('crypto_fg', 'cnn_fg', 'composite_fg') as $k) {
        $f = $dir . '/fg_' . md5($k) . '.json';
        if (file_exists($f)) @unlink($f);
    }

    $crypto = _fg_fetch_crypto();
    $cnn = _fg_fetch_cnn($conn);
    $composite = _fg_compute_composite($conn);

    // Store all in DB
    _fg_store($conn, 'crypto', $crypto['score'], $crypto['classification'], json_encode($crypto));
    _fg_store($conn, 'cnn', $cnn['score'], $cnn['classification'], json_encode($cnn));
    _fg_store($conn, 'composite', $composite['score'], $composite['classification'], json_encode($composite['components']));

    echo json_encode(array(
        'ok' => true,
        'action' => 'fetch',
        'crypto_score' => $crypto['score'],
        'cnn_score' => $cnn['score'],
        'composite_score' => $composite['score'],
        'timestamp' => gmdate('Y-m-d H:i:s')
    ));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: index — all three scores
// ═══════════════════════════════════════════
if ($action === 'index') {
    $crypto = _fg_fetch_crypto();
    $cnn = _fg_fetch_cnn($conn);
    $composite = _fg_compute_composite($conn);

    echo json_encode(array(
        'ok' => true,
        'action' => 'index',
        'crypto' => array('score' => $crypto['score'], 'classification' => $crypto['classification'], 'label' => isset($crypto['label']) ? $crypto['label'] : $crypto['classification']),
        'cnn' => array('score' => $cnn['score'], 'classification' => $cnn['classification'], 'vix' => $cnn['vix'], 'regime' => $cnn['regime']),
        'composite' => array('score' => $composite['score'], 'classification' => $composite['classification']),
        'timestamp' => gmdate('Y-m-d H:i:s')
    ));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: crypto — crypto F&G detail
// ═══════════════════════════════════════════
if ($action === 'crypto') {
    $crypto = _fg_fetch_crypto();
    echo json_encode(array('ok' => true, 'action' => 'crypto', 'data' => $crypto));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: cnn — VIX/regime F&G detail
// ═══════════════════════════════════════════
if ($action === 'cnn') {
    $cnn = _fg_fetch_cnn($conn);
    echo json_encode(array('ok' => true, 'action' => 'cnn', 'data' => $cnn));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: composite — full breakdown
// ═══════════════════════════════════════════
if ($action === 'composite') {
    $composite = _fg_compute_composite($conn);
    echo json_encode(array('ok' => true, 'action' => 'composite', 'data' => $composite));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: history — 30-day DB history
// ═══════════════════════════════════════════
if ($action === 'history') {
    $source_filter = isset($_GET['source']) ? _fg_esc($conn, $_GET['source']) : '';
    $where = "fetch_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)";
    if ($source_filter !== '') {
        $where .= " AND source = '$source_filter'";
    }

    $r = $conn->query("SELECT source, score, classification, fetch_date FROM lm_fear_greed WHERE $where ORDER BY fetch_date DESC, source");
    $rows = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $rows[] = $row;
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'history', 'count' => count($rows), 'data' => $rows));
    $conn->close();
    exit;
}

// Default fallback
echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
$conn->close();
?>
