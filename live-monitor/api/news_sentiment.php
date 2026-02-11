<?php
/**
 * news_sentiment.php — Finnhub News Sentiment Fetcher
 * Fetches company news sentiment for tracked tickers.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=fetch&key=livetrader2026  — Fetch sentiment for all tickers (admin)
 *   ?action=sentiment&ticker=AAPL     — Latest sentiment for one ticker (public)
 *   ?action=buzz                      — High-buzz tickers (public)
 *   ?action=sector_sentiment          — Sentiment by sector (public)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/goldmine_schema.php';

_gm_ensure_schema($conn);

$action = isset($_GET['action']) ? $_GET['action'] : 'buzz';
$key    = isset($_GET['key'])    ? $_GET['key']    : '';
$admin  = ($key === 'livetrader2026');
$now    = date('Y-m-d H:i:s');
$today  = date('Y-m-d');

// Finnhub API key (from db_config.php)
$FINNHUB_KEY = isset($FINNHUB_API_KEY) ? $FINNHUB_API_KEY : 'cvstlkhr01qhup0t0j7gcvstlkhr01qhup0t0j80';

// Stock universe with sectors
$TICKERS_SECTORS = array(
    'AAPL'  => 'Technology',
    'MSFT'  => 'Technology',
    'GOOGL' => 'Technology',
    'AMZN'  => 'Consumer',
    'NVDA'  => 'Technology',
    'META'  => 'Technology',
    'JPM'   => 'Financial',
    'WMT'   => 'Consumer',
    'XOM'   => 'Energy',
    'NFLX'  => 'Consumer',
    'JNJ'   => 'Healthcare',
    'BAC'   => 'Financial',
    'GS'    => 'Financial',
    'TSLA'  => 'Technology',
    'V'     => 'Financial',
    'MA'    => 'Financial',
    'DIS'   => 'Consumer',
    'COST'  => 'Consumer',
    'PG'    => 'Consumer',
    'UNH'   => 'Healthcare',
    'HD'    => 'Consumer',
    'CRM'   => 'Technology',
    'INTC'  => 'Technology',
    'AMD'   => 'Technology',
    'PYPL'  => 'Financial',
    'SQ'    => 'Financial',
    'SHOP'  => 'Technology',
    'ABNB'  => 'Consumer'
);

// Cache helpers
$NS_CACHE_DIR = dirname(__FILE__) . '/cache/';
if (!is_dir($NS_CACHE_DIR)) { @mkdir($NS_CACHE_DIR, 0755, true); }

function _ns_cache_get($key, $ttl) {
    if (isset($_GET['nocache']) && $_GET['nocache'] == '1') return false;
    global $NS_CACHE_DIR;
    $f = $NS_CACHE_DIR . 'ns_' . md5($key) . '.json';
    if (file_exists($f) && (time() - filemtime($f)) < $ttl) {
        $d = @file_get_contents($f);
        if ($d !== false) return json_decode($d, true);
    }
    return false;
}
function _ns_cache_set($key, $data) {
    global $NS_CACHE_DIR;
    $f = $NS_CACHE_DIR . 'ns_' . md5($key) . '.json';
    @file_put_contents($f, json_encode($data));
}

function _ns_http_get($url) {
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'GoldmineTracker/1.0');
        $resp = curl_exec($ch);
        curl_close($ch);
        if ($resp !== false) return $resp;
    }
    return @file_get_contents($url);
}

// ════════════════════════════════════════════════════════════
//  FETCH — Admin: pull sentiment for all tickers from Finnhub
// ════════════════════════════════════════════════════════════

if ($action === 'fetch') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    $tickers = array_keys($TICKERS_SECTORS);
    $fetched = 0;
    $errors = array();
    $from = date('Y-m-d', strtotime('-7 days'));
    $to   = $today;

    // Batch: max 28 tickers at 60 calls/min = need ~1s between calls
    foreach ($tickers as $ticker) {
        // Check if already fetched today
        $chk = $conn->query("SELECT id FROM gm_news_sentiment
            WHERE ticker = '" . $conn->real_escape_string($ticker) . "' AND fetch_date = '" . $today . "'");
        if ($chk && $chk->num_rows > 0) continue;

        // Finnhub company news endpoint
        $url = 'https://finnhub.io/api/v1/company-news?symbol=' . urlencode($ticker)
             . '&from=' . $from . '&to=' . $to . '&token=' . $FINNHUB_KEY;

        $resp = _ns_http_get($url);
        usleep(1100000); // 1.1 second delay (60 calls/min limit)

        if (!$resp) {
            $errors[] = $ticker . ': fetch failed';
            continue;
        }

        $articles = json_decode($resp, true);
        if (!is_array($articles)) {
            $errors[] = $ticker . ': bad response';
            continue;
        }

        // Calculate sentiment from article headlines
        $positive = 0;
        $negative = 0;
        $neutral  = 0;
        $total    = count($articles);

        // Simple keyword-based sentiment (Finnhub doesn't always return sentiment scores)
        $pos_words = array('surge', 'soar', 'jump', 'gain', 'rally', 'beat', 'upgrade', 'bullish',
            'record', 'strong', 'profit', 'growth', 'buy', 'outperform', 'positive', 'boost',
            'exceed', 'optimistic', 'breakthrough', 'success', 'expansion', 'raise', 'momentum');
        $neg_words = array('drop', 'fall', 'decline', 'loss', 'crash', 'plunge', 'downgrade', 'bearish',
            'miss', 'weak', 'cut', 'sell', 'underperform', 'negative', 'risk', 'concern',
            'warning', 'layoff', 'lawsuit', 'investigation', 'slump', 'recession', 'fear');

        foreach ($articles as $art) {
            $text = strtolower(isset($art['headline']) ? $art['headline'] : '');
            $text .= ' ' . strtolower(isset($art['summary']) ? $art['summary'] : '');

            $pos_score = 0;
            $neg_score = 0;
            foreach ($pos_words as $w) {
                if (strpos($text, $w) !== false) $pos_score++;
            }
            foreach ($neg_words as $w) {
                if (strpos($text, $w) !== false) $neg_score++;
            }

            if ($pos_score > $neg_score) $positive++;
            elseif ($neg_score > $pos_score) $negative++;
            else $neutral++;
        }

        // Sentiment score: -1.0 to +1.0
        $sentiment = 0;
        if ($total > 0) {
            $sentiment = ($positive - $negative) / $total;
        }

        // Buzz score: articles per week, normalized (avg is ~10/week)
        $buzz = ($total > 0) ? round($total / 7, 2) : 0;

        // Get sector for sector average later
        $sector = isset($TICKERS_SECTORS[$ticker]) ? $TICKERS_SECTORS[$ticker] : 'Other';

        $conn->query("INSERT INTO gm_news_sentiment
            (ticker, fetch_date, articles_analyzed, sentiment_score,
             positive_count, negative_count, neutral_count,
             buzz_score, sector_avg_sentiment, relative_sentiment,
             source, created_at)
            VALUES (
             '" . $conn->real_escape_string($ticker) . "', '" . $today . "',
             " . $total . ", " . round($sentiment, 4) . ",
             " . $positive . ", " . $negative . ", " . $neutral . ",
             " . $buzz . ", 0, 0,
             'finnhub', '" . $now . "')
            ON DUPLICATE KEY UPDATE
             articles_analyzed = " . $total . ",
             sentiment_score = " . round($sentiment, 4) . ",
             positive_count = " . $positive . ",
             negative_count = " . $negative . ",
             neutral_count = " . $neutral . ",
             buzz_score = " . $buzz);
        $fetched++;
    }

    // Update sector averages
    _ns_update_sector_averages($conn);

    echo json_encode(array(
        'ok' => true,
        'fetched' => $fetched,
        'total_tickers' => count($tickers),
        'errors' => $errors
    ));
    exit;
}

// ════════════════════════════════════════════════════════════
//  SENTIMENT — Public: latest sentiment for one ticker
// ════════════════════════════════════════════════════════════

if ($action === 'sentiment') {
    $ticker = isset($_GET['ticker']) ? strtoupper($_GET['ticker']) : '';
    if ($ticker === '') { echo json_encode(array('ok' => false, 'error' => 'ticker required')); exit; }

    $cached = _ns_cache_get('sentiment_' . $ticker, 3600);
    if ($cached) { echo json_encode($cached); exit; }

    $r = $conn->query("SELECT * FROM gm_news_sentiment
        WHERE ticker = '" . $conn->real_escape_string($ticker) . "'
        ORDER BY fetch_date DESC LIMIT 7");

    $rows = array();
    $latest = null;
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $rows[] = $row;
            if (!$latest) $latest = $row;
        }
    }

    // Trend: compare latest to 7-day avg
    $trend = 'neutral';
    if (count($rows) >= 2) {
        $avg = 0;
        foreach ($rows as $rw) { $avg += floatval($rw['sentiment_score']); }
        $avg = $avg / count($rows);
        if ($latest && floatval($latest['sentiment_score']) > $avg + 0.1) $trend = 'improving';
        elseif ($latest && floatval($latest['sentiment_score']) < $avg - 0.1) $trend = 'declining';
    }

    $label = 'Neutral';
    if ($latest) {
        $s = floatval($latest['sentiment_score']);
        if ($s > 0.3) $label = 'Very Positive';
        elseif ($s > 0.1) $label = 'Positive';
        elseif ($s < -0.3) $label = 'Very Negative';
        elseif ($s < -0.1) $label = 'Negative';
    }

    $data = array(
        'ok' => true,
        'ticker' => $ticker,
        'latest' => $latest,
        'history' => $rows,
        'trend' => $trend,
        'sentiment_label' => $label
    );
    _ns_cache_set('sentiment_' . $ticker, $data);
    echo json_encode($data);
    exit;
}

// ════════════════════════════════════════════════════════════
//  BUZZ — Public: high-buzz tickers (most news articles)
// ════════════════════════════════════════════════════════════

if ($action === 'buzz') {
    $cached = _ns_cache_get('buzz', 3600);
    if ($cached) { echo json_encode($cached); exit; }

    $rows = array();
    $r = $conn->query("SELECT ticker, articles_analyzed, sentiment_score, buzz_score,
        positive_count, negative_count, neutral_count, fetch_date
        FROM gm_news_sentiment
        WHERE fetch_date >= DATE_SUB(CURDATE(), INTERVAL 3 DAY)
        ORDER BY buzz_score DESC LIMIT 20");
    if ($r) { while ($row = $r->fetch_assoc()) { $rows[] = $row; } }

    // Add sentiment label
    foreach ($rows as $i => $row) {
        $s = floatval($row['sentiment_score']);
        $label = 'Neutral';
        if ($s > 0.3) $label = 'Very Positive';
        elseif ($s > 0.1) $label = 'Positive';
        elseif ($s < -0.3) $label = 'Very Negative';
        elseif ($s < -0.1) $label = 'Negative';
        $rows[$i]['sentiment_label'] = $label;
    }

    $data = array('ok' => true, 'buzz_tickers' => $rows);
    _ns_cache_set('buzz', $data);
    echo json_encode($data);
    exit;
}

// ════════════════════════════════════════════════════════════
//  SECTOR SENTIMENT — Public: aggregated by sector
// ════════════════════════════════════════════════════════════

if ($action === 'sector_sentiment') {
    $cached = _ns_cache_get('sector_sentiment', 3600);
    if ($cached) { echo json_encode($cached); exit; }

    // Get latest sentiment for each ticker, join with sector info
    $sectors = array();
    foreach ($TICKERS_SECTORS as $ticker => $sector) {
        if (!isset($sectors[$sector])) {
            $sectors[$sector] = array(
                'sector' => $sector,
                'tickers' => array(),
                'total_sentiment' => 0,
                'count' => 0,
                'total_buzz' => 0,
                'most_positive' => array('ticker' => '', 'score' => -2),
                'most_negative' => array('ticker' => '', 'score' => 2)
            );
        }

        $r = $conn->query("SELECT sentiment_score, buzz_score FROM gm_news_sentiment
            WHERE ticker = '" . $conn->real_escape_string($ticker) . "'
            ORDER BY fetch_date DESC LIMIT 1");
        if ($r && ($row = $r->fetch_assoc())) {
            $s = floatval($row['sentiment_score']);
            $sectors[$sector]['tickers'][] = array('ticker' => $ticker, 'sentiment' => $s);
            $sectors[$sector]['total_sentiment'] += $s;
            $sectors[$sector]['count']++;
            $sectors[$sector]['total_buzz'] += floatval($row['buzz_score']);

            if ($s > $sectors[$sector]['most_positive']['score']) {
                $sectors[$sector]['most_positive'] = array('ticker' => $ticker, 'score' => $s);
            }
            if ($s < $sectors[$sector]['most_negative']['score']) {
                $sectors[$sector]['most_negative'] = array('ticker' => $ticker, 'score' => $s);
            }
        }
    }

    // Calculate averages
    $result = array();
    foreach ($sectors as $sec) {
        $avg = ($sec['count'] > 0) ? round($sec['total_sentiment'] / $sec['count'], 4) : 0;
        $label = 'Neutral';
        if ($avg > 0.2) $label = 'Bullish';
        elseif ($avg > 0.05) $label = 'Slightly Bullish';
        elseif ($avg < -0.2) $label = 'Bearish';
        elseif ($avg < -0.05) $label = 'Slightly Bearish';

        $result[] = array(
            'sector' => $sec['sector'],
            'avg_sentiment' => $avg,
            'sentiment_label' => $label,
            'ticker_count' => $sec['count'],
            'total_buzz' => round($sec['total_buzz'], 2),
            'most_positive' => $sec['most_positive'],
            'most_negative' => $sec['most_negative'],
            'tickers' => $sec['tickers']
        );
    }

    // Sort by avg sentiment desc
    usort($result, '_ns_sort_by_sentiment');

    $data = array('ok' => true, 'sectors' => $result);
    _ns_cache_set('sector_sentiment', $data);
    echo json_encode($data);
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
exit;

// ════════════════════════════════════════════════════════════
//  HELPERS
// ════════════════════════════════════════════════════════════

function _ns_sort_by_sentiment($a, $b) {
    if ($a['avg_sentiment'] == $b['avg_sentiment']) return 0;
    return ($a['avg_sentiment'] > $b['avg_sentiment']) ? -1 : 1;
}

function _ns_update_sector_averages($conn) {
    global $TICKERS_SECTORS, $today;

    // Calculate sector averages from today's data
    $sector_avgs = array();
    foreach ($TICKERS_SECTORS as $ticker => $sector) {
        if (!isset($sector_avgs[$sector])) {
            $sector_avgs[$sector] = array('total' => 0, 'count' => 0);
        }
        $r = $conn->query("SELECT sentiment_score FROM gm_news_sentiment
            WHERE ticker = '" . $conn->real_escape_string($ticker) . "' AND fetch_date = '" . $today . "'");
        if ($r && ($row = $r->fetch_assoc())) {
            $sector_avgs[$sector]['total'] += floatval($row['sentiment_score']);
            $sector_avgs[$sector]['count']++;
        }
    }

    // Update each ticker's sector_avg and relative sentiment
    foreach ($TICKERS_SECTORS as $ticker => $sector) {
        $avg = 0;
        if ($sector_avgs[$sector]['count'] > 0) {
            $avg = $sector_avgs[$sector]['total'] / $sector_avgs[$sector]['count'];
        }

        $conn->query("UPDATE gm_news_sentiment SET
            sector_avg_sentiment = " . round($avg, 4) . ",
            relative_sentiment = sentiment_score - " . round($avg, 4) . "
            WHERE ticker = '" . $conn->real_escape_string($ticker) . "' AND fetch_date = '" . $today . "'");
    }
}
?>
