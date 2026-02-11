<?php
/**
 * smart_money.php — Smart Money Intelligence API
 * Unified API for analyst ratings, insider sentiment, 13F holdings,
 * consensus scoring, challenger bot signals, and performance tracking.
 * PHP 5.2 compatible.
 */

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/smart_money_schema.php';

_sm_ensure_schema($conn);

$action = isset($_GET['action']) ? $_GET['action'] : '';
$key    = isset($_GET['key'])    ? $_GET['key']    : '';
$admin  = ($key === 'livetrader2026');
$now    = date('Y-m-d H:i:s');
$today  = date('Y-m-d');

// ────────────────────────────────────────────────────────────
//  API Key
// ────────────────────────────────────────────────────────────

$FINNHUB_KEY = isset($FINNHUB_API_KEY) ? $FINNHUB_API_KEY : 'cvstlkhr01qhup0t0j7gcvstlkhr01qhup0t0j80';

// ────────────────────────────────────────────────────────────
//  Ticker universe
// ────────────────────────────────────────────────────────────

$SM_TICKERS = array('AAPL','MSFT','GOOGL','AMZN','NVDA','META','JPM','WMT','XOM','NFLX','JNJ','BAC');

$SM_SECTORS = array(
    'AAPL' => 'Technology', 'MSFT' => 'Technology', 'GOOGL' => 'Technology',
    'AMZN' => 'Consumer', 'NVDA' => 'Technology', 'META' => 'Technology',
    'JPM' => 'Financial', 'WMT' => 'Consumer', 'XOM' => 'Energy',
    'NFLX' => 'Consumer', 'JNJ' => 'Healthcare', 'BAC' => 'Financial'
);

// ────────────────────────────────────────────────────────────
//  Helper functions
// ────────────────────────────────────────────────────────────

$SM_CACHE_DIR = dirname(__FILE__) . '/cache/';
if (!is_dir($SM_CACHE_DIR)) { @mkdir($SM_CACHE_DIR, 0755, true); }

function _sm_cache_get($key, $ttl) {
    if (isset($_GET['nocache']) && $_GET['nocache'] == '1') return false;
    global $SM_CACHE_DIR;
    $f = $SM_CACHE_DIR . 'sm_' . md5($key) . '.json';
    if (file_exists($f) && (time() - filemtime($f)) < $ttl) {
        $d = @file_get_contents($f);
        if ($d !== false) return json_decode($d, true);
    }
    return false;
}

function _sm_cache_set($key, $data) {
    global $SM_CACHE_DIR;
    $f = $SM_CACHE_DIR . 'sm_' . md5($key) . '.json';
    @file_put_contents($f, json_encode($data));
}

function _sm_http_get($url) {
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'SmartMoneyTracker/1.0');
        $resp = curl_exec($ch);
        curl_close($ch);
        if ($resp !== false) return $resp;
    }
    return @file_get_contents($url);
}

function _sm_esc($val) {
    global $conn;
    return $conn->real_escape_string($val);
}

// ════════════════════════════════════════════════════════════
//  ADMIN ACTIONS
// ════════════════════════════════════════════════════════════


// ── fetch_analyst ──────────────────────────────────────────
if ($action === 'fetch_analyst') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    global $SM_TICKERS, $FINNHUB_KEY;
    $ratings_fetched = 0;
    $targets_fetched = 0;
    $errors = array();

    foreach ($SM_TICKERS as $ticker) {
        // 1) Fetch recommendation history
        $url = 'https://finnhub.io/api/v1/stock/recommendation?symbol=' . urlencode($ticker) . '&token=' . $FINNHUB_KEY;
        $raw = _sm_http_get($url);
        if ($raw) {
            $arr = json_decode($raw, true);
            if (is_array($arr)) {
                foreach ($arr as $rec) {
                    $period     = isset($rec['period'])     ? _sm_esc($rec['period'])         : $today;
                    $strong_buy = isset($rec['strongBuy'])  ? intval($rec['strongBuy'])       : 0;
                    $buy_v      = isset($rec['buy'])        ? intval($rec['buy'])             : 0;
                    $hold_v     = isset($rec['hold'])       ? intval($rec['hold'])            : 0;
                    $sell_v     = isset($rec['sell'])        ? intval($rec['sell'])            : 0;
                    $strong_sell= isset($rec['strongSell']) ? intval($rec['strongSell'])      : 0;

                    $sql = "INSERT INTO lm_analyst_ratings (ticker, period, strong_buy, buy, hold, sell, strong_sell, fetch_date, created_at)
                            VALUES ('" . _sm_esc($ticker) . "', '" . $period . "', " . $strong_buy . ", " . $buy_v . ", " . $hold_v . ", " . $sell_v . ", " . $strong_sell . ", '" . _sm_esc($today) . "', '" . _sm_esc($now) . "')
                            ON DUPLICATE KEY UPDATE strong_buy=VALUES(strong_buy), buy=VALUES(buy), hold=VALUES(hold), sell=VALUES(sell), strong_sell=VALUES(strong_sell), fetch_date=VALUES(fetch_date)";
                    if ($conn->query($sql)) {
                        $ratings_fetched++;
                    }
                }
            }
        } else {
            $errors[] = $ticker . ': recommendation fetch failed';
        }

        usleep(1100000); // Finnhub 60/min limit

        // 2) Fetch price target
        $url2 = 'https://finnhub.io/api/v1/stock/price-target?symbol=' . urlencode($ticker) . '&token=' . $FINNHUB_KEY;
        $raw2 = _sm_http_get($url2);
        if ($raw2) {
            $pt = json_decode($raw2, true);
            if (is_array($pt) && isset($pt['targetMean'])) {
                $t_high   = isset($pt['targetHigh'])   ? floatval($pt['targetHigh'])   : 0;
                $t_low    = isset($pt['targetLow'])    ? floatval($pt['targetLow'])    : 0;
                $t_mean   = isset($pt['targetMean'])   ? floatval($pt['targetMean'])   : 0;
                $t_median = isset($pt['targetMedian']) ? floatval($pt['targetMedian']) : 0;
                $t_upd    = isset($pt['lastUpdated'])  ? _sm_esc($pt['lastUpdated'])   : $today;

                $sql2 = "INSERT INTO lm_price_targets (ticker, target_high, target_low, target_mean, target_median, last_updated, fetch_date, created_at)
                         VALUES ('" . _sm_esc($ticker) . "', " . $t_high . ", " . $t_low . ", " . $t_mean . ", " . $t_median . ", '" . $t_upd . "', '" . _sm_esc($today) . "', '" . _sm_esc($now) . "')
                         ON DUPLICATE KEY UPDATE target_high=VALUES(target_high), target_low=VALUES(target_low), target_mean=VALUES(target_mean), target_median=VALUES(target_median), last_updated=VALUES(last_updated), fetch_date=VALUES(fetch_date)";
                if ($conn->query($sql2)) {
                    $targets_fetched++;
                }
            }
        } else {
            $errors[] = $ticker . ': price-target fetch failed';
        }

        usleep(1100000);
    }

    $result = array('ok' => true, 'action' => 'fetch_analyst', 'ratings_fetched' => $ratings_fetched, 'targets_fetched' => $targets_fetched);
    if (count($errors) > 0) {
        $result['errors'] = $errors;
    }
    echo json_encode($result);
    exit;
}


// ── fetch_sentiment ────────────────────────────────────────
if ($action === 'fetch_sentiment') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    global $SM_TICKERS, $FINNHUB_KEY;
    $tickers_processed = 0;
    $rows_upserted = 0;
    $errors = array();

    foreach ($SM_TICKERS as $ticker) {
        $url = 'https://finnhub.io/api/v1/stock/insider-sentiment?symbol=' . urlencode($ticker) . '&from=2025-01-01&to=2026-12-31&token=' . $FINNHUB_KEY;
        $raw = _sm_http_get($url);
        if ($raw) {
            $json = json_decode($raw, true);
            if (is_array($json) && isset($json['data']) && is_array($json['data'])) {
                foreach ($json['data'] as $row) {
                    $year_v   = isset($row['year'])   ? intval($row['year'])      : 0;
                    $month_v  = isset($row['month'])  ? intval($row['month'])     : 0;
                    $change_v = isset($row['change']) ? floatval($row['change'])  : 0;
                    $mspr_v   = isset($row['mspr'])   ? floatval($row['mspr'])    : 0;

                    if ($year_v == 0 || $month_v == 0) continue;

                    $sql = "INSERT INTO lm_insider_sentiment (ticker, year, month, mspr, change_val, fetch_date, created_at)
                            VALUES ('" . _sm_esc($ticker) . "', " . $year_v . ", " . $month_v . ", " . $mspr_v . ", " . $change_v . ", '" . _sm_esc($today) . "', '" . _sm_esc($now) . "')
                            ON DUPLICATE KEY UPDATE mspr=VALUES(mspr), change_val=VALUES(change_val), fetch_date=VALUES(fetch_date)";
                    if ($conn->query($sql)) {
                        $rows_upserted++;
                    }
                }
                $tickers_processed++;
            }
        } else {
            $errors[] = $ticker . ': sentiment fetch failed';
        }

        usleep(1100000);
    }

    $result = array('ok' => true, 'action' => 'fetch_sentiment', 'tickers_processed' => $tickers_processed, 'rows_upserted' => $rows_upserted);
    if (count($errors) > 0) {
        $result['errors'] = $errors;
    }
    echo json_encode($result);
    exit;
}


// ── ingest_wsb (POST) ──────────────────────────────────────
if ($action === 'ingest_wsb') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    $raw = file_get_contents('php://input');
    $payload = json_decode($raw, true);

    if (!is_array($payload) || !isset($payload['data']) || !is_array($payload['data'])) {
        echo json_encode(array('ok' => false, 'error' => 'Invalid payload: expected {data: [...]}'));
        exit;
    }

    $rows_ingested = 0;
    foreach ($payload['data'] as $item) {
        $t_ticker     = isset($item['ticker'])         ? _sm_esc($item['ticker'])          : '';
        $t_mentions   = isset($item['mentions_24h'])   ? intval($item['mentions_24h'])     : 0;
        $t_sentiment  = isset($item['sentiment'])      ? floatval($item['sentiment'])      : 0;
        $t_upvotes    = isset($item['total_upvotes'])  ? intval($item['total_upvotes'])    : 0;
        $t_score      = isset($item['wsb_score'])      ? floatval($item['wsb_score'])      : 0;
        $t_title      = isset($item['top_post_title']) ? _sm_esc($item['top_post_title'])  : '';

        if ($t_ticker === '') continue;

        $sql = "INSERT INTO lm_wsb_sentiment (ticker, scan_date, mentions_24h, sentiment, total_upvotes, wsb_score, top_post_title, created_at)
                VALUES ('" . $t_ticker . "', '" . _sm_esc($today) . "', " . $t_mentions . ", " . $t_sentiment . ", " . $t_upvotes . ", " . $t_score . ", '" . $t_title . "', '" . _sm_esc($now) . "')
                ON DUPLICATE KEY UPDATE mentions_24h=VALUES(mentions_24h), sentiment=VALUES(sentiment), total_upvotes=VALUES(total_upvotes), wsb_score=VALUES(wsb_score), top_post_title=VALUES(top_post_title)";
        if ($conn->query($sql)) {
            $rows_ingested++;
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'ingest_wsb', 'rows_ingested' => $rows_ingested));
    exit;
}


// ── ingest_13f (POST) ──────────────────────────────────────
if ($action === 'ingest_13f') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    $raw = file_get_contents('php://input');
    $payload = json_decode($raw, true);

    if (!is_array($payload) || !isset($payload['data']) || !is_array($payload['data'])) {
        echo json_encode(array('ok' => false, 'error' => 'Invalid payload: expected {data: [...]}'));
        exit;
    }

    $rows_ingested = 0;
    foreach ($payload['data'] as $item) {
        $h_cik            = isset($item['cik'])             ? _sm_esc($item['cik'])             : '';
        $h_fund_name      = isset($item['fund_name'])       ? _sm_esc($item['fund_name'])       : '';
        $h_ticker         = isset($item['ticker'])          ? _sm_esc($item['ticker'])          : '';
        $h_cusip          = isset($item['cusip'])           ? _sm_esc($item['cusip'])           : '';
        $h_issuer         = isset($item['name_of_issuer'])  ? _sm_esc($item['name_of_issuer'])  : '';
        $h_val_k          = isset($item['value_thousands']) ? intval($item['value_thousands'])  : 0;
        $h_shares         = isset($item['shares'])          ? intval($item['shares'])           : 0;
        $h_quarter        = isset($item['filing_quarter'])  ? _sm_esc($item['filing_quarter'])  : '';
        $h_filing_date    = isset($item['filing_date'])     ? _sm_esc($item['filing_date'])     : $today;
        $h_prev_shares    = isset($item['prev_shares'])     ? intval($item['prev_shares'])      : 0;
        $h_change_pct     = isset($item['change_pct'])      ? floatval($item['change_pct'])     : 0;
        $h_change_type    = isset($item['change_type'])     ? _sm_esc($item['change_type'])     : '';

        if ($h_cik === '' || $h_cusip === '') continue;

        $sql = "INSERT INTO gm_sec_13f_holdings (cik, fund_name, ticker, cusip, name_of_issuer, value_thousands, shares, filing_quarter, filing_date, prev_shares, change_pct, change_type, created_at)
                VALUES ('" . $h_cik . "', '" . $h_fund_name . "', '" . $h_ticker . "', '" . $h_cusip . "', '" . $h_issuer . "', " . $h_val_k . ", " . $h_shares . ", '" . $h_quarter . "', '" . $h_filing_date . "', " . $h_prev_shares . ", " . $h_change_pct . ", '" . $h_change_type . "', '" . _sm_esc($now) . "')
                ON DUPLICATE KEY UPDATE fund_name=VALUES(fund_name), ticker=VALUES(ticker), name_of_issuer=VALUES(name_of_issuer), value_thousands=VALUES(value_thousands), shares=VALUES(shares), prev_shares=VALUES(prev_shares), change_pct=VALUES(change_pct), change_type=VALUES(change_type)";
        if ($conn->query($sql)) {
            $rows_ingested++;
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'ingest_13f', 'rows_ingested' => $rows_ingested));
    exit;
}


// ── calculate_consensus ────────────────────────────────────
if ($action === 'calculate_consensus') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    global $SM_TICKERS, $SM_SECTORS;
    $scores_calculated = 0;
    $all_scores = array();

    // Detect market regime
    $regime = 'neutral';
    $regime_r = $conn->query("SELECT AVG(change_24h_pct) as avg_chg FROM lm_price_cache WHERE asset_class = 'STOCK'");
    if ($regime_r && $regime_row = $regime_r->fetch_assoc()) {
        $avg_chg = floatval($regime_row['avg_chg']);
        if ($avg_chg > 1) {
            $regime = 'bull';
        } elseif ($avg_chg < -1) {
            $regime = 'bear';
        }
    }

    // Dynamic weight multipliers per regime
    if ($regime === 'bull') {
        $w_tech = 1.2; $w_sm = 1.2; $w_ins = 0.8; $w_an = 0.8; $w_mom = 0.8;
    } elseif ($regime === 'bear') {
        $w_tech = 0.5; $w_sm = 0.8; $w_ins = 1.5; $w_an = 0.8; $w_mom = 1.5;
    } else {
        $w_tech = 1.0; $w_sm = 1.0; $w_ins = 1.0; $w_an = 1.0; $w_mom = 1.0;
    }
    // Normalization factor: sum of weights should map to 100
    $w_sum = ($w_tech * 25) + ($w_sm * 20) + ($w_ins * 20) + ($w_an * 20) + ($w_mom * 15);
    $norm_factor = 100.0 / $w_sum;

    foreach ($SM_TICKERS as $ticker) {
        $notes = array();

        // ── Component 1: Technical (0-25 pts) ──
        $technical = 12; // default neutral
        $r = $conn->query("SELECT
            SUM(CASE WHEN signal_type LIKE '%BUY%' THEN 1 ELSE 0 END) as buys,
            SUM(CASE WHEN signal_type LIKE '%SHORT%' THEN 1 ELSE 0 END) as shorts,
            COUNT(*) as total
            FROM lm_signals
            WHERE symbol LIKE '%" . _sm_esc($ticker) . "%'
            AND signal_time > DATE_SUB(NOW(), INTERVAL 7 DAY)
            AND status = 'active'");
        if ($r && $row = $r->fetch_assoc()) {
            $total = intval($row['total']);
            if ($total > 0) {
                $buys = intval($row['buys']);
                $technical = round(($buys / $total) * 25);
                $notes[] = $ticker . ' tech: ' . $buys . '/' . $total . ' buys';
            }
        }

        // ── Component 2: Smart Money 13F (0-20 pts) ──
        $smart_money = 10; // default neutral
        $qr = $conn->query("SELECT filing_quarter FROM gm_sec_13f_holdings ORDER BY filing_date DESC LIMIT 1");
        $latest_q = '';
        if ($qr && $qrow = $qr->fetch_assoc()) {
            $latest_q = $qrow['filing_quarter'];
        }
        if ($latest_q !== '') {
            $r2 = $conn->query("SELECT change_type, COUNT(*) as cnt FROM gm_sec_13f_holdings
                WHERE ticker = '" . _sm_esc($ticker) . "' AND filing_quarter = '" . _sm_esc($latest_q) . "'
                GROUP BY change_type");
            $funds_holding = 0;
            $increased = 0; $new_pos = 0; $decreased = 0; $sold_out = 0;
            if ($r2) {
                while ($ct_row = $r2->fetch_assoc()) {
                    $ct = $ct_row['change_type'];
                    $cnt = intval($ct_row['cnt']);
                    $funds_holding += $cnt;
                    if ($ct === 'increased' || $ct === 'INCREASED') $increased = $cnt;
                    if ($ct === 'new' || $ct === 'NEW') $new_pos = $cnt;
                    if ($ct === 'decreased' || $ct === 'DECREASED') $decreased = $cnt;
                    if ($ct === 'sold_out' || $ct === 'SOLD_OUT' || $ct === 'sold') $sold_out = $cnt;
                }
            }
            if ($funds_holding > 0) {
                $base = min(($funds_holding / 10.0) * 10, 10);
                $max_f = max($funds_holding, 1);
                $momentum_13f = (($increased + $new_pos - $decreased - $sold_out) / $max_f) * 10;
                $smart_money = min($base + $momentum_13f, 20);
                $smart_money = max($smart_money, 0);
                $notes[] = $ticker . ' 13F: ' . $funds_holding . ' funds, inc=' . $increased . ', new=' . $new_pos;
            }
        }

        // ── Component 3: Insider (0-20 pts) ──
        $insider = 10; // default neutral
        $r3 = $conn->query("SELECT
            SUM(CASE WHEN transaction_type = 'P' THEN total_value ELSE 0 END) as buy_val,
            SUM(CASE WHEN transaction_type = 'S' THEN total_value ELSE 0 END) as sell_val,
            COUNT(DISTINCT CASE WHEN transaction_type = 'P' THEN filer_name ELSE NULL END) as distinct_buyers
            FROM gm_sec_insider_trades
            WHERE ticker = '" . _sm_esc($ticker) . "'
            AND transaction_date > DATE_SUB(CURDATE(), INTERVAL 90 DAY)");
        $insider_has_data = false;
        $base_score_ins = 7.5;
        $cluster_bonus = 0;
        if ($r3 && $ir = $r3->fetch_assoc()) {
            $buy_val = floatval($ir['buy_val']);
            $sell_val = floatval($ir['sell_val']);
            $distinct_buyers = intval($ir['distinct_buyers']);
            if ($buy_val > 0 || $sell_val > 0) {
                $insider_has_data = true;
                $total_val = max($buy_val + $sell_val, 1);
                $net_ratio = ($buy_val - $sell_val) / $total_val; // range -1 to 1
                $base_score_ins = (($net_ratio + 1) / 2.0) * 15; // maps -1..1 to 0..15
                if ($distinct_buyers >= 3) {
                    $cluster_bonus = 5;
                } elseif ($distinct_buyers >= 2) {
                    $cluster_bonus = 3;
                }
                $notes[] = $ticker . ' insider: buy=$' . round($buy_val) . ', sell=$' . round($sell_val) . ', buyers=' . $distinct_buyers;
            }
        }

        // MSPR bonus from Finnhub insider sentiment
        $mspr_bonus = 0;
        $mr = $conn->query("SELECT mspr FROM lm_insider_sentiment WHERE ticker = '" . _sm_esc($ticker) . "' ORDER BY year DESC, month DESC LIMIT 1");
        if ($mr && $mrow = $mr->fetch_assoc()) {
            $mspr = floatval($mrow['mspr']);
            if ($mspr > 0) {
                $mspr_bonus = min($mspr * 10, 5);
            } else {
                $mspr_bonus = max($mspr * 5, -5);
            }
            if (!$insider_has_data) {
                $insider_has_data = true;
            }
        }

        if ($insider_has_data) {
            $insider = $base_score_ins + $cluster_bonus + $mspr_bonus;
            $insider = max(0, min(20, $insider));
        }

        // ── Component 4: Analyst (0-20 pts) ──
        $analyst = 10; // default neutral
        $r4 = $conn->query("SELECT strong_buy, buy, hold, sell, strong_sell FROM lm_analyst_ratings
            WHERE ticker = '" . _sm_esc($ticker) . "' ORDER BY period DESC LIMIT 1");
        if ($r4 && $ar = $r4->fetch_assoc()) {
            $sb = intval($ar['strong_buy']);
            $bv = intval($ar['buy']);
            $hv = intval($ar['hold']);
            $sv = intval($ar['sell']);
            $ss = intval($ar['strong_sell']);
            $total_analysts = $sb + $bv + $hv + $sv + $ss;
            if ($total_analysts > 0) {
                $weighted = ($sb * 2) + ($bv * 1) + ($hv * 0) - ($sv * 1) - ($ss * 2);
                $max_possible = $total_analysts * 2;
                $ratio = ($weighted + $max_possible) / (2.0 * $max_possible); // 0 to 1

                // Check price target upside
                $upside_pts = 0;
                $tr = $conn->query("SELECT target_mean FROM lm_price_targets WHERE ticker = '" . _sm_esc($ticker) . "'");
                if ($tr && $trow = $tr->fetch_assoc()) {
                    $target_mean = floatval($trow['target_mean']);
                    // Get current price
                    $pr = $conn->query("SELECT last_price FROM lm_price_cache WHERE symbol LIKE '%" . _sm_esc($ticker) . "%' AND asset_class = 'STOCK'");
                    if ($pr && $prow = $pr->fetch_assoc()) {
                        $current_price = floatval($prow['last_price']);
                        if ($current_price > 0 && $target_mean > 0) {
                            $upside_pct = (($target_mean - $current_price) / $current_price) * 100;
                            $upside_pts = min($upside_pct / 5.0, 6);
                            $upside_pts = max($upside_pts, -3); // cap downside penalty
                            $notes[] = $ticker . ' target: $' . round($target_mean, 2) . ' (' . round($upside_pct, 1) . '% upside)';
                        }
                    }
                }

                $analyst = ($ratio * 14) + $upside_pts;
                $analyst = max(0, min(20, $analyst));
                $notes[] = $ticker . ' analyst: SB=' . $sb . ',B=' . $bv . ',H=' . $hv . ',S=' . $sv . ',SS=' . $ss;
            }
        }

        // ── Component 5: Momentum + Social (0-15 pts) ──
        $momentum = 7; // default neutral
        $momentum_pts = 3;
        $social_pts = 0;

        // Price momentum
        $pr5 = $conn->query("SELECT last_price, change_24h_pct FROM lm_price_cache WHERE symbol LIKE '%" . _sm_esc($ticker) . "%' AND asset_class = 'STOCK'");
        if ($pr5 && $prow5 = $pr5->fetch_assoc()) {
            $change_24h = floatval($prow5['change_24h_pct']);
            if ($change_24h > 3) {
                $momentum_pts = 8;
            } elseif ($change_24h > 0) {
                $momentum_pts = 5;
            } elseif ($change_24h > -3) {
                $momentum_pts = 3;
            } else {
                $momentum_pts = 0;
            }
        }

        // WSB sentiment bonus
        $wr = $conn->query("SELECT sentiment, wsb_score FROM lm_wsb_sentiment WHERE ticker = '" . _sm_esc($ticker) . "' ORDER BY scan_date DESC LIMIT 1");
        if ($wr && $wrow = $wr->fetch_assoc()) {
            $wsb_sent = floatval($wrow['sentiment']);
            $wsb_sc = floatval($wrow['wsb_score']);
            if ($wsb_sent > 0.3) {
                $social_pts = min($wsb_sc / 10.0, 7);
            } elseif ($wsb_sent > 0) {
                $social_pts = 3;
            } else {
                $social_pts = 0;
            }
        }

        $momentum = min($momentum_pts + $social_pts, 15);

        // ── Apply regime weights and normalize ──
        $adj_tech = $technical * $w_tech;
        $adj_sm   = $smart_money * $w_sm;
        $adj_ins  = $insider * $w_ins;
        $adj_an   = $analyst * $w_an;
        $adj_mom  = $momentum * $w_mom;

        // Re-normalize so total stays in 0-100 range
        $raw_total = $adj_tech + $adj_sm + $adj_ins + $adj_an + $adj_mom;
        $overall = round($raw_total * $norm_factor);
        $overall = max(0, min(100, $overall));

        // Store un-normalized component scores for display (rounded)
        $technical    = round($adj_tech * $norm_factor * (25.0 / 100.0));
        $smart_money  = round($adj_sm   * $norm_factor * (20.0 / 100.0));
        $insider      = round($adj_ins  * $norm_factor * (20.0 / 100.0));
        $analyst      = round($adj_an   * $norm_factor * (20.0 / 100.0));
        $momentum_fin = round($adj_mom  * $norm_factor * (15.0 / 100.0));

        // Direction and confidence
        if ($overall >= 60) {
            $direction = 'BULLISH';
        } elseif ($overall <= 40) {
            $direction = 'BEARISH';
        } else {
            $direction = 'NEUTRAL';
        }

        if ($overall >= 75) {
            $confidence = 'HIGH';
        } elseif ($overall >= 55) {
            $confidence = 'MODERATE';
        } else {
            $confidence = 'LOW';
        }

        // Build explanation
        $explanation = json_encode(array(
            'technical' => $technical,
            'smart_money' => $smart_money,
            'insider' => $insider,
            'analyst' => $analyst,
            'momentum' => $momentum_fin,
            'regime' => $regime,
            'notes' => $notes
        ));

        // Upsert into lm_smart_consensus
        $sql_cons = "INSERT INTO lm_smart_consensus (ticker, calc_date, overall_score, technical_score, smart_money_score, insider_score, analyst_score, momentum_score, social_score, signal_direction, confidence, regime, explanation, created_at)
            VALUES ('" . _sm_esc($ticker) . "', '" . _sm_esc($today) . "', " . $overall . ", " . $technical . ", " . $smart_money . ", " . $insider . ", " . $analyst . ", " . $momentum_fin . ", " . intval($social_pts) . ", '" . _sm_esc($direction) . "', '" . _sm_esc($confidence) . "', '" . _sm_esc($regime) . "', '" . _sm_esc($explanation) . "', '" . _sm_esc($now) . "')
            ON DUPLICATE KEY UPDATE overall_score=VALUES(overall_score), technical_score=VALUES(technical_score), smart_money_score=VALUES(smart_money_score), insider_score=VALUES(insider_score), analyst_score=VALUES(analyst_score), momentum_score=VALUES(momentum_score), social_score=VALUES(social_score), signal_direction=VALUES(signal_direction), confidence=VALUES(confidence), regime=VALUES(regime), explanation=VALUES(explanation)";
        if ($conn->query($sql_cons)) {
            $scores_calculated++;
        }

        $all_scores[] = array('ticker' => $ticker, 'score' => $overall, 'direction' => $direction, 'confidence' => $confidence);
    }

    // Sort by score desc to get top 5
    // PHP 5.2 compatible sort using a named comparison function
    function _sm_sort_scores($a, $b) {
        if ($a['score'] == $b['score']) return 0;
        return ($a['score'] > $b['score']) ? -1 : 1;
    }
    usort($all_scores, '_sm_sort_scores');
    $top_5 = array_slice($all_scores, 0, 5);

    echo json_encode(array('ok' => true, 'action' => 'calculate_consensus', 'scores_calculated' => $scores_calculated, 'top_scores' => $top_5, 'regime' => $regime));
    exit;
}


// ── generate_challenger ────────────────────────────────────
if ($action === 'generate_challenger') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    // Detect regime
    $regime = 'neutral';
    $regime_r = $conn->query("SELECT AVG(change_24h_pct) as avg_chg FROM lm_price_cache WHERE asset_class = 'STOCK'");
    if ($regime_r && $regime_row = $regime_r->fetch_assoc()) {
        $avg_chg = floatval($regime_row['avg_chg']);
        if ($avg_chg > 1) $regime = 'bull';
        elseif ($avg_chg < -1) $regime = 'bear';
    }

    $challenger_signals = 0;
    $signals_detail = array();

    // Get today's consensus scores
    $cr = $conn->query("SELECT ticker, overall_score, signal_direction, confidence FROM lm_smart_consensus WHERE calc_date = '" . _sm_esc($today) . "' ORDER BY overall_score DESC");
    if (!$cr) {
        echo json_encode(array('ok' => false, 'error' => 'No consensus data for today. Run calculate_consensus first.'));
        exit;
    }

    while ($crow = $cr->fetch_assoc()) {
        $c_ticker = $crow['ticker'];
        $c_score = intval($crow['overall_score']);
        $c_dir = $crow['signal_direction'];

        // BULLISH signals: score >= 70
        if ($c_score >= 70 && $c_dir === 'BULLISH') {
            // Get current price
            $pr = $conn->query("SELECT last_price FROM lm_price_cache WHERE symbol LIKE '%" . _sm_esc($c_ticker) . "%' AND asset_class = 'STOCK'");
            if (!$pr) continue;
            $prow = $pr->fetch_assoc();
            if (!$prow) continue;
            $entry_price = floatval($prow['last_price']);
            if ($entry_price <= 0) continue;

            // Get analyst target
            $target_tp_pct = 4.0; // default
            $tr = $conn->query("SELECT target_mean FROM lm_price_targets WHERE ticker = '" . _sm_esc($c_ticker) . "'");
            if ($tr && $trow = $tr->fetch_assoc()) {
                $target_mean = floatval($trow['target_mean']);
                if ($target_mean > $entry_price) {
                    $upside_to_target = (($target_mean - $entry_price) / $entry_price) * 100;
                    $target_tp_pct = $upside_to_target * 0.6; // 60% of upside
                    $target_tp_pct = max(2.0, min(8.0, $target_tp_pct));
                }
            }

            $target_sl_pct = ($regime === 'bull') ? 3.0 : 4.0;
            $max_hold = ($regime === 'bull') ? 96 : 48;
            $signal_strength = min($c_score, 100);

            $rationale = 'Challenger Bot: Consensus score ' . $c_score . '/100 (' . $crow['confidence'] . '). ';
            $rationale .= 'Regime: ' . $regime . '. TP=' . round($target_tp_pct, 1) . '%, SL=' . round($target_sl_pct, 1) . '%, Hold=' . $max_hold . 'h.';

            $expires_at = date('Y-m-d H:i:s', time() + ($max_hold * 3600));

            $sql_sig = "INSERT INTO lm_signals (asset_class, symbol, algorithm_name, signal_type, signal_strength,
                entry_price, target_tp_pct, target_sl_pct, max_hold_hours, rationale, signal_time, expires_at, status)
                VALUES ('STOCK', '" . _sm_esc($c_ticker) . "', 'Challenger Bot', 'STRONG_BUY', " . $signal_strength . ",
                " . $entry_price . ", " . round($target_tp_pct, 2) . ", " . round($target_sl_pct, 2) . ", " . $max_hold . ",
                '" . _sm_esc($rationale) . "', '" . _sm_esc($now) . "', '" . _sm_esc($expires_at) . "', 'active')";
            if ($conn->query($sql_sig)) {
                $challenger_signals++;
                $signals_detail[] = array('ticker' => $c_ticker, 'type' => 'STRONG_BUY', 'score' => $c_score, 'tp' => round($target_tp_pct, 2), 'sl' => round($target_sl_pct, 2));
            }
        }

        // BEARISH signals: score <= 30
        if ($c_score <= 30 && $c_dir === 'BEARISH') {
            $pr2 = $conn->query("SELECT last_price FROM lm_price_cache WHERE symbol LIKE '%" . _sm_esc($c_ticker) . "%' AND asset_class = 'STOCK'");
            if (!$pr2) continue;
            $prow2 = $pr2->fetch_assoc();
            if (!$prow2) continue;
            $entry_price2 = floatval($prow2['last_price']);
            if ($entry_price2 <= 0) continue;

            $target_tp_pct2 = 3.0;
            $target_sl_pct2 = ($regime === 'bear') ? 3.0 : 4.0;
            $max_hold2 = ($regime === 'bear') ? 96 : 48;
            $signal_strength2 = min(100 - $c_score, 100);

            $rationale2 = 'Challenger Bot SHORT: Consensus score ' . $c_score . '/100 (BEARISH). ';
            $rationale2 .= 'Regime: ' . $regime . '. TP=' . round($target_tp_pct2, 1) . '%, SL=' . round($target_sl_pct2, 1) . '%, Hold=' . $max_hold2 . 'h.';

            $expires_at2 = date('Y-m-d H:i:s', time() + ($max_hold2 * 3600));

            $sql_sig2 = "INSERT INTO lm_signals (asset_class, symbol, algorithm_name, signal_type, signal_strength,
                entry_price, target_tp_pct, target_sl_pct, max_hold_hours, rationale, signal_time, expires_at, status)
                VALUES ('STOCK', '" . _sm_esc($c_ticker) . "', 'Challenger Bot', 'SHORT', " . $signal_strength2 . ",
                " . $entry_price2 . ", " . round($target_tp_pct2, 2) . ", " . round($target_sl_pct2, 2) . ", " . $max_hold2 . ",
                '" . _sm_esc($rationale2) . "', '" . _sm_esc($now) . "', '" . _sm_esc($expires_at2) . "', 'active')";
            if ($conn->query($sql_sig2)) {
                $challenger_signals++;
                $signals_detail[] = array('ticker' => $c_ticker, 'type' => 'SHORT', 'score' => $c_score, 'tp' => round($target_tp_pct2, 2), 'sl' => round($target_sl_pct2, 2));
            }
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'generate_challenger', 'challenger_signals' => $challenger_signals, 'signals' => $signals_detail, 'regime' => $regime));
    exit;
}


// ── update_showdown ────────────────────────────────────────
if ($action === 'update_showdown') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    $period_start = date('Y-m-d', strtotime('-30 days'));
    $period_end = $today;

    // Challenger Bot performance
    $ch_r = $conn->query("SELECT
        COUNT(*) as trades,
        SUM(CASE WHEN t.realized_pct > 0 THEN 1 ELSE 0 END) as wins,
        AVG(t.realized_pct) as avg_pnl,
        SUM(t.realized_pct) as total_pnl,
        MIN(t.realized_pct) as max_dd
        FROM lm_trades t
        INNER JOIN lm_signals s ON t.signal_id = s.id
        WHERE s.algorithm_name = 'Challenger Bot'
        AND t.opened_at >= '" . _sm_esc($period_start) . "'
        AND t.status = 'closed'");

    $ch_trades = 0; $ch_wins = 0; $ch_win_rate = 0; $ch_pnl = 0; $ch_sharpe = 0; $ch_max_dd = 0;
    if ($ch_r && $chrow = $ch_r->fetch_assoc()) {
        $ch_trades = intval($chrow['trades']);
        $ch_wins = intval($chrow['wins']);
        $ch_win_rate = ($ch_trades > 0) ? round(($ch_wins / $ch_trades) * 100, 2) : 0;
        $ch_pnl = floatval($chrow['total_pnl']);
        $ch_max_dd = floatval($chrow['max_dd']);

        // Simplified Sharpe: avg_pnl / stddev (estimate from data)
        if ($ch_trades > 1) {
            $avg_pnl = floatval($chrow['avg_pnl']);
            $var_r = $conn->query("SELECT VARIANCE(t.realized_pct) as var_pnl
                FROM lm_trades t INNER JOIN lm_signals s ON t.signal_id = s.id
                WHERE s.algorithm_name = 'Challenger Bot' AND t.opened_at >= '" . _sm_esc($period_start) . "' AND t.status = 'closed'");
            if ($var_r && $vrow = $var_r->fetch_assoc()) {
                $variance = floatval($vrow['var_pnl']);
                $stddev = ($variance > 0) ? sqrt($variance) : 1;
                $ch_sharpe = round($avg_pnl / $stddev, 3);
            }
        }
    }

    // Best-performing non-Challenger algo
    $best_algo_name = ''; $best_algo_trades = 0; $best_algo_wins = 0;
    $best_algo_win_rate = 0; $best_algo_pnl = 0; $best_algo_sharpe = 0; $best_algo_max_dd = 0;
    $challenger_rank = 1; $total_algos = 0;

    $algo_r = $conn->query("SELECT s.algorithm_name,
        COUNT(*) as trades,
        SUM(CASE WHEN t.realized_pct > 0 THEN 1 ELSE 0 END) as wins,
        SUM(t.realized_pct) as total_pnl,
        AVG(t.realized_pct) as avg_pnl,
        MIN(t.realized_pct) as max_dd
        FROM lm_trades t
        INNER JOIN lm_signals s ON t.signal_id = s.id
        WHERE t.opened_at >= '" . _sm_esc($period_start) . "'
        AND t.status = 'closed'
        GROUP BY s.algorithm_name
        HAVING COUNT(*) >= 3
        ORDER BY total_pnl DESC");

    if ($algo_r) {
        $best_pnl_so_far = -999999;
        while ($arow = $algo_r->fetch_assoc()) {
            $total_algos++;
            $this_pnl = floatval($arow['total_pnl']);
            $this_name = $arow['algorithm_name'];

            // Track challenger rank
            if ($this_name !== 'Challenger Bot' && $this_pnl > $ch_pnl) {
                $challenger_rank++;
            }

            // Find best non-challenger algo
            if ($this_name !== 'Challenger Bot' && $this_pnl > $best_pnl_so_far) {
                $best_pnl_so_far = $this_pnl;
                $best_algo_name = $this_name;
                $best_algo_trades = intval($arow['trades']);
                $best_algo_wins = intval($arow['wins']);
                $best_algo_win_rate = ($best_algo_trades > 0) ? round(($best_algo_wins / $best_algo_trades) * 100, 2) : 0;
                $best_algo_pnl = $this_pnl;
                $best_algo_max_dd = floatval($arow['max_dd']);

                // Sharpe for best algo
                if ($best_algo_trades > 1) {
                    $avg_p = floatval($arow['avg_pnl']);
                    $var_r2 = $conn->query("SELECT VARIANCE(t.realized_pct) as var_pnl
                        FROM lm_trades t INNER JOIN lm_signals s ON t.signal_id = s.id
                        WHERE s.algorithm_name = '" . _sm_esc($best_algo_name) . "' AND t.opened_at >= '" . _sm_esc($period_start) . "' AND t.status = 'closed'");
                    if ($var_r2 && $vrow2 = $var_r2->fetch_assoc()) {
                        $variance2 = floatval($vrow2['var_pnl']);
                        $stddev2 = ($variance2 > 0) ? sqrt($variance2) : 1;
                        $best_algo_sharpe = round($avg_p / $stddev2, 3);
                    }
                }
            }
        }
    }

    // Upsert showdown
    $sql_show = "INSERT INTO lm_challenger_showdown (period_start, period_end,
        challenger_trades, challenger_wins, challenger_win_rate, challenger_pnl, challenger_sharpe, challenger_max_dd,
        best_algo_name, best_algo_trades, best_algo_wins, best_algo_win_rate, best_algo_pnl, best_algo_sharpe, best_algo_max_dd,
        challenger_rank, total_algos, snapshot_date, created_at)
        VALUES ('" . _sm_esc($period_start) . "', '" . _sm_esc($period_end) . "',
        " . $ch_trades . ", " . $ch_wins . ", " . $ch_win_rate . ", " . round($ch_pnl, 2) . ", " . $ch_sharpe . ", " . round($ch_max_dd, 2) . ",
        '" . _sm_esc($best_algo_name) . "', " . $best_algo_trades . ", " . $best_algo_wins . ", " . $best_algo_win_rate . ", " . round($best_algo_pnl, 2) . ", " . $best_algo_sharpe . ", " . round($best_algo_max_dd, 2) . ",
        " . $challenger_rank . ", " . $total_algos . ", '" . _sm_esc($today) . "', '" . _sm_esc($now) . "')
        ON DUPLICATE KEY UPDATE
        challenger_trades=VALUES(challenger_trades), challenger_wins=VALUES(challenger_wins), challenger_win_rate=VALUES(challenger_win_rate),
        challenger_pnl=VALUES(challenger_pnl), challenger_sharpe=VALUES(challenger_sharpe), challenger_max_dd=VALUES(challenger_max_dd),
        best_algo_name=VALUES(best_algo_name), best_algo_trades=VALUES(best_algo_trades), best_algo_wins=VALUES(best_algo_wins),
        best_algo_win_rate=VALUES(best_algo_win_rate), best_algo_pnl=VALUES(best_algo_pnl), best_algo_sharpe=VALUES(best_algo_sharpe),
        best_algo_max_dd=VALUES(best_algo_max_dd), challenger_rank=VALUES(challenger_rank), total_algos=VALUES(total_algos)";
    $conn->query($sql_show);

    echo json_encode(array(
        'ok' => true,
        'action' => 'update_showdown',
        'challenger' => array(
            'trades' => $ch_trades, 'wins' => $ch_wins, 'win_rate' => $ch_win_rate,
            'pnl' => round($ch_pnl, 2), 'sharpe' => $ch_sharpe, 'rank' => $challenger_rank . '/' . $total_algos
        ),
        'best_algo' => array(
            'name' => $best_algo_name, 'trades' => $best_algo_trades, 'wins' => $best_algo_wins,
            'win_rate' => $best_algo_win_rate, 'pnl' => round($best_algo_pnl, 2), 'sharpe' => $best_algo_sharpe
        )
    ));
    exit;
}


// ── snapshot ───────────────────────────────────────────────
if ($action === 'snapshot') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    $snapshot = array();

    // Top consensus scores
    $cr = $conn->query("SELECT ticker, overall_score, signal_direction, confidence, regime FROM lm_smart_consensus ORDER BY calc_date DESC, overall_score DESC LIMIT 12");
    $consensus_list = array();
    if ($cr) {
        while ($row = $cr->fetch_assoc()) {
            $consensus_list[] = $row;
        }
    }
    $snapshot['consensus'] = $consensus_list;

    // Recent analyst ratings (latest period per ticker)
    $ar = $conn->query("SELECT a.ticker, a.strong_buy, a.buy, a.hold, a.sell, a.strong_sell, a.period,
        p.target_mean, p.target_high, p.target_low
        FROM lm_analyst_ratings a
        LEFT JOIN lm_price_targets p ON a.ticker = p.ticker
        WHERE a.period = (SELECT MAX(a2.period) FROM lm_analyst_ratings a2 WHERE a2.ticker = a.ticker)
        ORDER BY a.ticker");
    $analyst_list = array();
    if ($ar) {
        while ($row = $ar->fetch_assoc()) {
            $analyst_list[] = $row;
        }
    }
    $snapshot['analyst'] = $analyst_list;

    // Insider clusters (recent buying)
    $ir = $conn->query("SELECT ticker,
        COUNT(DISTINCT CASE WHEN transaction_type = 'P' THEN filer_name ELSE NULL END) as distinct_buyers,
        SUM(CASE WHEN transaction_type = 'P' THEN total_value ELSE 0 END) as total_bought,
        SUM(CASE WHEN transaction_type = 'S' THEN total_value ELSE 0 END) as total_sold
        FROM gm_sec_insider_trades
        WHERE transaction_date > DATE_SUB(CURDATE(), INTERVAL 90 DAY)
        GROUP BY ticker
        HAVING distinct_buyers >= 2
        ORDER BY distinct_buyers DESC, total_bought DESC LIMIT 10");
    $insider_list = array();
    if ($ir) {
        while ($row = $ir->fetch_assoc()) {
            $insider_list[] = $row;
        }
    }
    $snapshot['insider_clusters'] = $insider_list;

    // Challenger showdown
    $sr = $conn->query("SELECT * FROM lm_challenger_showdown ORDER BY snapshot_date DESC LIMIT 1");
    $showdown = null;
    if ($sr && $srow = $sr->fetch_assoc()) {
        $showdown = $srow;
    }
    $snapshot['showdown'] = $showdown;

    $snapshot['generated_at'] = $now;

    _sm_cache_set('overview_snapshot', $snapshot);

    echo json_encode(array('ok' => true, 'action' => 'snapshot', 'cached' => true));
    exit;
}


// ════════════════════════════════════════════════════════════
//  PUBLIC ACTIONS
// ════════════════════════════════════════════════════════════


// ── overview ───────────────────────────────────────────────
if ($action === 'overview') {

    // Try cache first (5 min)
    $cached = _sm_cache_get('overview_snapshot', 300);
    if ($cached) {
        echo json_encode(array('ok' => true, 'action' => 'overview', 'data' => $cached, 'cached' => true));
        exit;
    }

    $data = array();

    // Top 5 consensus scores (latest date)
    $cr = $conn->query("SELECT ticker, overall_score, signal_direction, confidence, regime, explanation
        FROM lm_smart_consensus
        WHERE calc_date = (SELECT MAX(calc_date) FROM lm_smart_consensus)
        ORDER BY overall_score DESC LIMIT 5");
    $top_scores = array();
    if ($cr) {
        while ($row = $cr->fetch_assoc()) {
            $top_scores[] = array(
                'ticker' => $row['ticker'],
                'score' => intval($row['overall_score']),
                'direction' => $row['signal_direction'],
                'confidence' => $row['confidence'],
                'regime' => $row['regime']
            );
        }
    }
    $data['top_consensus'] = $top_scores;

    // Recent insider clusters (last 90 days, 2+ distinct buyers)
    $ir = $conn->query("SELECT ticker,
        COUNT(DISTINCT CASE WHEN transaction_type = 'P' THEN filer_name ELSE NULL END) as distinct_buyers,
        SUM(CASE WHEN transaction_type = 'P' THEN total_value ELSE 0 END) as buy_value
        FROM gm_sec_insider_trades
        WHERE transaction_date > DATE_SUB(CURDATE(), INTERVAL 90 DAY)
        GROUP BY ticker
        HAVING distinct_buyers >= 2
        ORDER BY distinct_buyers DESC, buy_value DESC LIMIT 5");
    $insider_clusters = array();
    if ($ir) {
        while ($row = $ir->fetch_assoc()) {
            $insider_clusters[] = array(
                'ticker' => $row['ticker'],
                'distinct_buyers' => intval($row['distinct_buyers']),
                'buy_value' => floatval($row['buy_value'])
            );
        }
    }
    $data['insider_clusters'] = $insider_clusters;

    // Analyst upgrades — latest period ratings with strong buy > sell
    $ar = $conn->query("SELECT a.ticker, a.strong_buy, a.buy, a.hold, a.sell, a.strong_sell, a.period,
        p.target_mean
        FROM lm_analyst_ratings a
        LEFT JOIN lm_price_targets p ON a.ticker = p.ticker
        WHERE a.period = (SELECT MAX(a2.period) FROM lm_analyst_ratings a2 WHERE a2.ticker = a.ticker)
        AND (a.strong_buy + a.buy) > (a.sell + a.strong_sell)
        ORDER BY (a.strong_buy * 2 + a.buy) DESC LIMIT 5");
    $analyst_picks = array();
    if ($ar) {
        while ($row = $ar->fetch_assoc()) {
            $analyst_picks[] = array(
                'ticker' => $row['ticker'],
                'strong_buy' => intval($row['strong_buy']),
                'buy' => intval($row['buy']),
                'hold' => intval($row['hold']),
                'sell' => intval($row['sell']),
                'strong_sell' => intval($row['strong_sell']),
                'period' => $row['period'],
                'target_mean' => floatval($row['target_mean'])
            );
        }
    }
    $data['analyst_picks'] = $analyst_picks;

    // Challenger status
    $sr = $conn->query("SELECT challenger_trades, challenger_win_rate, challenger_pnl, challenger_rank, total_algos,
        best_algo_name, best_algo_win_rate, best_algo_pnl, snapshot_date
        FROM lm_challenger_showdown ORDER BY snapshot_date DESC LIMIT 1");
    $challenger = null;
    if ($sr && $srow = $sr->fetch_assoc()) {
        $challenger = array(
            'trades' => intval($srow['challenger_trades']),
            'win_rate' => floatval($srow['challenger_win_rate']),
            'pnl' => floatval($srow['challenger_pnl']),
            'rank' => intval($srow['challenger_rank']) . '/' . intval($srow['total_algos']),
            'best_algo' => $srow['best_algo_name'],
            'best_algo_pnl' => floatval($srow['best_algo_pnl']),
            'as_of' => $srow['snapshot_date']
        );
    }
    $data['challenger'] = $challenger;

    _sm_cache_set('overview_snapshot', $data);

    echo json_encode(array('ok' => true, 'action' => 'overview', 'data' => $data));
    exit;
}


// ── analyst ────────────────────────────────────────────────
if ($action === 'analyst') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';

    if ($ticker !== '') {
        // Full history for one ticker
        $cached = _sm_cache_get('analyst_' . $ticker, 600);
        if ($cached) {
            echo json_encode(array('ok' => true, 'action' => 'analyst', 'ticker' => $ticker, 'data' => $cached, 'cached' => true));
            exit;
        }

        $history = array();
        $hr = $conn->query("SELECT period, strong_buy, buy, hold, sell, strong_sell FROM lm_analyst_ratings
            WHERE ticker = '" . _sm_esc($ticker) . "' ORDER BY period DESC LIMIT 12");
        if ($hr) {
            while ($row = $hr->fetch_assoc()) {
                $history[] = array(
                    'period' => $row['period'],
                    'strong_buy' => intval($row['strong_buy']),
                    'buy' => intval($row['buy']),
                    'hold' => intval($row['hold']),
                    'sell' => intval($row['sell']),
                    'strong_sell' => intval($row['strong_sell'])
                );
            }
        }

        // Price target
        $target = null;
        $tr = $conn->query("SELECT target_high, target_low, target_mean, target_median, last_updated FROM lm_price_targets WHERE ticker = '" . _sm_esc($ticker) . "'");
        if ($tr && $trow = $tr->fetch_assoc()) {
            $target = array(
                'high' => floatval($trow['target_high']),
                'low' => floatval($trow['target_low']),
                'mean' => floatval($trow['target_mean']),
                'median' => floatval($trow['target_median']),
                'last_updated' => $trow['last_updated']
            );
        }

        // Current price + upside
        $current_price = 0;
        $upside_pct = 0;
        $pr = $conn->query("SELECT last_price FROM lm_price_cache WHERE symbol LIKE '%" . _sm_esc($ticker) . "%' AND asset_class = 'STOCK'");
        if ($pr && $prow = $pr->fetch_assoc()) {
            $current_price = floatval($prow['last_price']);
            if ($target && $current_price > 0 && $target['mean'] > 0) {
                $upside_pct = round((($target['mean'] - $current_price) / $current_price) * 100, 2);
            }
        }

        $result_data = array(
            'history' => $history,
            'target' => $target,
            'current_price' => $current_price,
            'upside_pct' => $upside_pct
        );

        _sm_cache_set('analyst_' . $ticker, $result_data);

        echo json_encode(array('ok' => true, 'action' => 'analyst', 'ticker' => $ticker, 'data' => $result_data));
        exit;
    }

    // All tickers — latest period
    $cached = _sm_cache_get('analyst_all', 600);
    if ($cached) {
        echo json_encode(array('ok' => true, 'action' => 'analyst', 'data' => $cached, 'cached' => true));
        exit;
    }

    global $SM_TICKERS;
    $all_analyst = array();

    foreach ($SM_TICKERS as $t) {
        $ar = $conn->query("SELECT strong_buy, buy, hold, sell, strong_sell, period FROM lm_analyst_ratings
            WHERE ticker = '" . _sm_esc($t) . "' ORDER BY period DESC LIMIT 1");
        if (!$ar) continue;
        $arow = $ar->fetch_assoc();
        if (!$arow) continue;

        $entry = array(
            'ticker' => $t,
            'strong_buy' => intval($arow['strong_buy']),
            'buy' => intval($arow['buy']),
            'hold' => intval($arow['hold']),
            'sell' => intval($arow['sell']),
            'strong_sell' => intval($arow['strong_sell']),
            'period' => $arow['period']
        );

        // Price target + current price
        $tr = $conn->query("SELECT target_mean FROM lm_price_targets WHERE ticker = '" . _sm_esc($t) . "'");
        if ($tr && $trow = $tr->fetch_assoc()) {
            $entry['target_mean'] = floatval($trow['target_mean']);
        } else {
            $entry['target_mean'] = 0;
        }

        $pr = $conn->query("SELECT last_price FROM lm_price_cache WHERE symbol LIKE '%" . _sm_esc($t) . "%' AND asset_class = 'STOCK'");
        if ($pr && $prow = $pr->fetch_assoc()) {
            $entry['current_price'] = floatval($prow['last_price']);
            if ($entry['target_mean'] > 0 && $entry['current_price'] > 0) {
                $entry['upside_pct'] = round((($entry['target_mean'] - $entry['current_price']) / $entry['current_price']) * 100, 2);
            } else {
                $entry['upside_pct'] = 0;
            }
        } else {
            $entry['current_price'] = 0;
            $entry['upside_pct'] = 0;
        }

        $all_analyst[] = $entry;
    }

    _sm_cache_set('analyst_all', $all_analyst);

    echo json_encode(array('ok' => true, 'action' => 'analyst', 'data' => $all_analyst));
    exit;
}


// ── insider ────────────────────────────────────────────────
if ($action === 'insider') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';

    $where_ticker = '';
    $cache_key = 'insider_all';
    if ($ticker !== '') {
        $where_ticker = " AND ticker = '" . _sm_esc($ticker) . "'";
        $cache_key = 'insider_' . $ticker;
    }

    $cached = _sm_cache_get($cache_key, 600);
    if ($cached) {
        echo json_encode(array('ok' => true, 'action' => 'insider', 'ticker' => $ticker, 'data' => $cached, 'cached' => true));
        exit;
    }

    // Aggregate insider trades
    $ir = $conn->query("SELECT ticker,
        SUM(CASE WHEN transaction_type = 'P' THEN total_value ELSE 0 END) as buy_value,
        SUM(CASE WHEN transaction_type = 'S' THEN total_value ELSE 0 END) as sell_value,
        SUM(CASE WHEN transaction_type = 'P' THEN shares ELSE 0 END) as buy_shares,
        SUM(CASE WHEN transaction_type = 'S' THEN shares ELSE 0 END) as sell_shares,
        COUNT(DISTINCT CASE WHEN transaction_type = 'P' THEN filer_name ELSE NULL END) as distinct_buyers,
        COUNT(DISTINCT CASE WHEN transaction_type = 'S' THEN filer_name ELSE NULL END) as distinct_sellers,
        COUNT(*) as total_transactions,
        MIN(transaction_date) as earliest,
        MAX(transaction_date) as latest
        FROM gm_sec_insider_trades
        WHERE transaction_date > DATE_SUB(CURDATE(), INTERVAL 180 DAY)
        " . $where_ticker . "
        GROUP BY ticker
        ORDER BY buy_value DESC");

    $insider_data = array();
    if ($ir) {
        while ($row = $ir->fetch_assoc()) {
            $t = $row['ticker'];
            $entry = array(
                'ticker' => $t,
                'buy_value' => floatval($row['buy_value']),
                'sell_value' => floatval($row['sell_value']),
                'net_value' => floatval($row['buy_value']) - floatval($row['sell_value']),
                'buy_shares' => floatval($row['buy_shares']),
                'sell_shares' => floatval($row['sell_shares']),
                'distinct_buyers' => intval($row['distinct_buyers']),
                'distinct_sellers' => intval($row['distinct_sellers']),
                'total_transactions' => intval($row['total_transactions']),
                'date_range' => $row['earliest'] . ' to ' . $row['latest']
            );

            // MSPR trend
            $mr = $conn->query("SELECT year, month, mspr FROM lm_insider_sentiment WHERE ticker = '" . _sm_esc($t) . "' ORDER BY year DESC, month DESC LIMIT 3");
            $mspr_trend = array();
            if ($mr) {
                while ($mrow = $mr->fetch_assoc()) {
                    $mspr_trend[] = array(
                        'year' => intval($mrow['year']),
                        'month' => intval($mrow['month']),
                        'mspr' => floatval($mrow['mspr'])
                    );
                }
            }
            $entry['mspr_trend'] = $mspr_trend;

            // Recent notable trades
            if ($ticker !== '') {
                $tr = $conn->query("SELECT filer_name, filer_title, transaction_date, transaction_type, shares, price_per_share, total_value
                    FROM gm_sec_insider_trades
                    WHERE ticker = '" . _sm_esc($t) . "'
                    AND transaction_date > DATE_SUB(CURDATE(), INTERVAL 180 DAY)
                    ORDER BY total_value DESC LIMIT 10");
                $recent_trades = array();
                if ($tr) {
                    while ($trow = $tr->fetch_assoc()) {
                        $recent_trades[] = array(
                            'filer' => $trow['filer_name'],
                            'title' => $trow['filer_title'],
                            'date' => $trow['transaction_date'],
                            'type' => ($trow['transaction_type'] === 'P') ? 'BUY' : 'SELL',
                            'shares' => floatval($trow['shares']),
                            'price' => floatval($trow['price_per_share']),
                            'value' => floatval($trow['total_value'])
                        );
                    }
                }
                $entry['recent_trades'] = $recent_trades;
            }

            $insider_data[] = $entry;
        }
    }

    _sm_cache_set($cache_key, $insider_data);

    echo json_encode(array('ok' => true, 'action' => 'insider', 'ticker' => $ticker, 'data' => $insider_data));
    exit;
}


// ── smart_money / 13f ──────────────────────────────────────
if ($action === 'smart_money' || $action === '13f') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';

    $where_ticker = '';
    $cache_key = '13f_all';
    if ($ticker !== '') {
        $where_ticker = " AND h.ticker = '" . _sm_esc($ticker) . "'";
        $cache_key = '13f_' . $ticker;
    }

    $cached = _sm_cache_get($cache_key, 600);
    if ($cached) {
        echo json_encode(array('ok' => true, 'action' => 'smart_money', 'ticker' => $ticker, 'data' => $cached, 'cached' => true));
        exit;
    }

    // Get latest quarter
    $qr = $conn->query("SELECT filing_quarter FROM gm_sec_13f_holdings ORDER BY filing_date DESC LIMIT 1");
    $latest_q = '';
    if ($qr && $qrow = $qr->fetch_assoc()) {
        $latest_q = $qrow['filing_quarter'];
    }

    if ($latest_q === '') {
        echo json_encode(array('ok' => true, 'action' => 'smart_money', 'ticker' => $ticker, 'data' => array(), 'message' => 'No 13F data available'));
        exit;
    }

    // Fund holdings per ticker
    $hr = $conn->query("SELECT h.ticker, h.fund_name, h.value_thousands, h.shares, h.change_pct, h.change_type, h.filing_quarter, h.filing_date
        FROM gm_sec_13f_holdings h
        WHERE h.filing_quarter = '" . _sm_esc($latest_q) . "'
        " . $where_ticker . "
        ORDER BY h.ticker, h.value_thousands DESC");

    $holdings_by_ticker = array();
    if ($hr) {
        while ($row = $hr->fetch_assoc()) {
            $t = $row['ticker'];
            if (!isset($holdings_by_ticker[$t])) {
                $holdings_by_ticker[$t] = array(
                    'ticker' => $t,
                    'quarter' => $row['filing_quarter'],
                    'funds' => array(),
                    'total_value_k' => 0,
                    'fund_count' => 0
                );
            }
            $holdings_by_ticker[$t]['funds'][] = array(
                'fund_name' => $row['fund_name'],
                'value_thousands' => intval($row['value_thousands']),
                'shares' => intval($row['shares']),
                'change_pct' => floatval($row['change_pct']),
                'change_type' => $row['change_type']
            );
            $holdings_by_ticker[$t]['total_value_k'] += intval($row['value_thousands']);
            $holdings_by_ticker[$t]['fund_count']++;
        }
    }

    // Identify conviction picks (3+ funds)
    $conviction = array();
    foreach ($holdings_by_ticker as $t => $data) {
        if ($data['fund_count'] >= 3) {
            $conviction[] = array(
                'ticker' => $t,
                'fund_count' => $data['fund_count'],
                'total_value_k' => $data['total_value_k']
            );
        }
    }
    // Sort conviction by fund count desc
    function _sm_sort_conviction($a, $b) {
        if ($a['fund_count'] == $b['fund_count']) return 0;
        return ($a['fund_count'] > $b['fund_count']) ? -1 : 1;
    }
    usort($conviction, '_sm_sort_conviction');

    $result_data = array(
        'quarter' => $latest_q,
        'holdings' => array_values($holdings_by_ticker),
        'conviction_picks' => $conviction
    );

    _sm_cache_set($cache_key, $result_data);

    echo json_encode(array('ok' => true, 'action' => 'smart_money', 'ticker' => $ticker, 'data' => $result_data));
    exit;
}


// ── consensus ──────────────────────────────────────────────
if ($action === 'consensus') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';

    $cache_key = ($ticker !== '') ? 'consensus_' . $ticker : 'consensus_all';
    $cached = _sm_cache_get($cache_key, 300);
    if ($cached) {
        echo json_encode(array('ok' => true, 'action' => 'consensus', 'ticker' => $ticker, 'data' => $cached, 'cached' => true));
        exit;
    }

    // Get latest calc_date
    $dr = $conn->query("SELECT MAX(calc_date) as latest_date FROM lm_smart_consensus");
    $latest_date = $today;
    if ($dr && $drow = $dr->fetch_assoc()) {
        if ($drow['latest_date']) {
            $latest_date = $drow['latest_date'];
        }
    }

    $where_ticker = '';
    if ($ticker !== '') {
        $where_ticker = " AND ticker = '" . _sm_esc($ticker) . "'";
    }

    $cr = $conn->query("SELECT ticker, calc_date, overall_score, technical_score, smart_money_score,
        insider_score, analyst_score, momentum_score, social_score,
        signal_direction, confidence, regime, explanation
        FROM lm_smart_consensus
        WHERE calc_date = '" . _sm_esc($latest_date) . "'
        " . $where_ticker . "
        ORDER BY overall_score DESC");

    $consensus_data = array();
    if ($cr) {
        while ($row = $cr->fetch_assoc()) {
            $entry = array(
                'ticker' => $row['ticker'],
                'calc_date' => $row['calc_date'],
                'overall_score' => intval($row['overall_score']),
                'components' => array(
                    'technical' => intval($row['technical_score']),
                    'smart_money' => intval($row['smart_money_score']),
                    'insider' => intval($row['insider_score']),
                    'analyst' => intval($row['analyst_score']),
                    'momentum' => intval($row['momentum_score']),
                    'social' => intval($row['social_score'])
                ),
                'direction' => $row['signal_direction'],
                'confidence' => $row['confidence'],
                'regime' => $row['regime']
            );

            // Parse explanation JSON for notes
            $expl = json_decode($row['explanation'], true);
            if (is_array($expl) && isset($expl['notes'])) {
                $entry['notes'] = $expl['notes'];
            }

            $consensus_data[] = $entry;
        }
    }

    _sm_cache_set($cache_key, $consensus_data);

    echo json_encode(array('ok' => true, 'action' => 'consensus', 'ticker' => $ticker, 'calc_date' => $latest_date, 'data' => $consensus_data));
    exit;
}


// ── leaderboard ────────────────────────────────────────────
if ($action === 'leaderboard') {

    $cached = _sm_cache_get('leaderboard', 600);
    if ($cached) {
        echo json_encode(array('ok' => true, 'action' => 'leaderboard', 'data' => $cached, 'cached' => true));
        exit;
    }

    // Try guru tracker first
    $gr = $conn->query("SELECT guru_name, platform, specialty, total_picks, wins, losses,
        win_rate, roi_percent, avg_return, credibility_score, last_updated
        FROM lm_guru_tracker
        ORDER BY credibility_score DESC, win_rate DESC LIMIT 20");

    $gurus = array();
    if ($gr) {
        while ($row = $gr->fetch_assoc()) {
            $gurus[] = array(
                'name' => $row['guru_name'],
                'platform' => $row['platform'],
                'specialty' => $row['specialty'],
                'total_picks' => intval($row['total_picks']),
                'wins' => intval($row['wins']),
                'losses' => intval($row['losses']),
                'win_rate' => floatval($row['win_rate']),
                'roi' => floatval($row['roi_percent']),
                'avg_return' => floatval($row['avg_return']),
                'credibility' => intval($row['credibility_score']),
                'last_updated' => $row['last_updated']
            );
        }
    }

    if (count($gurus) > 0) {
        _sm_cache_set('leaderboard', array('type' => 'gurus', 'entries' => $gurus));
        echo json_encode(array('ok' => true, 'action' => 'leaderboard', 'data' => array('type' => 'gurus', 'entries' => $gurus)));
        exit;
    }

    // Fallback: signal source performance
    $sr = $conn->query("SELECT signal_source, ticker,
        COUNT(*) as total_signals,
        AVG(return_7d) as avg_7d,
        AVG(return_30d) as avg_30d,
        SUM(CASE WHEN return_7d > 0 THEN 1 ELSE 0 END) as wins_7d,
        SUM(CASE WHEN return_7d <= 0 THEN 1 ELSE 0 END) as losses_7d
        FROM lm_signal_performance
        GROUP BY signal_source
        ORDER BY avg_30d DESC LIMIT 20");

    $sources = array();
    if ($sr) {
        while ($row = $sr->fetch_assoc()) {
            $total = intval($row['total_signals']);
            $wins = intval($row['wins_7d']);
            $sources[] = array(
                'source' => $row['signal_source'],
                'total_signals' => $total,
                'win_rate_7d' => ($total > 0) ? round(($wins / $total) * 100, 2) : 0,
                'avg_return_7d' => floatval($row['avg_7d']),
                'avg_return_30d' => floatval($row['avg_30d'])
            );
        }
    }

    $result = array('type' => 'signal_sources', 'entries' => $sources);
    _sm_cache_set('leaderboard', $result);

    echo json_encode(array('ok' => true, 'action' => 'leaderboard', 'data' => $result));
    exit;
}


// ── ticker (unified view) ──────────────────────────────────
if ($action === 'ticker') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    if ($ticker === '') {
        echo json_encode(array('ok' => false, 'error' => 'ticker parameter required'));
        exit;
    }

    $cached = _sm_cache_get('ticker_' . $ticker, 300);
    if ($cached) {
        echo json_encode(array('ok' => true, 'action' => 'ticker', 'ticker' => $ticker, 'data' => $cached, 'cached' => true));
        exit;
    }

    global $SM_SECTORS;
    $data = array(
        'ticker' => $ticker,
        'sector' => isset($SM_SECTORS[$ticker]) ? $SM_SECTORS[$ticker] : 'Unknown'
    );

    // Current price
    $pr = $conn->query("SELECT last_price, change_24h_pct FROM lm_price_cache WHERE symbol LIKE '%" . _sm_esc($ticker) . "%' AND asset_class = 'STOCK'");
    if ($pr && $prow = $pr->fetch_assoc()) {
        $data['current_price'] = floatval($prow['last_price']);
        $data['change_24h'] = floatval($prow['change_24h_pct']);
    } else {
        $data['current_price'] = 0;
        $data['change_24h'] = 0;
    }

    // Consensus
    $cr = $conn->query("SELECT overall_score, technical_score, smart_money_score, insider_score, analyst_score, momentum_score, social_score, signal_direction, confidence, regime, calc_date
        FROM lm_smart_consensus WHERE ticker = '" . _sm_esc($ticker) . "' ORDER BY calc_date DESC LIMIT 1");
    if ($cr && $crow = $cr->fetch_assoc()) {
        $data['consensus'] = array(
            'overall' => intval($crow['overall_score']),
            'technical' => intval($crow['technical_score']),
            'smart_money' => intval($crow['smart_money_score']),
            'insider' => intval($crow['insider_score']),
            'analyst' => intval($crow['analyst_score']),
            'momentum' => intval($crow['momentum_score']),
            'social' => intval($crow['social_score']),
            'direction' => $crow['signal_direction'],
            'confidence' => $crow['confidence'],
            'regime' => $crow['regime'],
            'date' => $crow['calc_date']
        );
    } else {
        $data['consensus'] = null;
    }

    // Analyst ratings (latest + history)
    $ar = $conn->query("SELECT period, strong_buy, buy, hold, sell, strong_sell FROM lm_analyst_ratings
        WHERE ticker = '" . _sm_esc($ticker) . "' ORDER BY period DESC LIMIT 6");
    $analyst_hist = array();
    if ($ar) {
        while ($row = $ar->fetch_assoc()) {
            $analyst_hist[] = array(
                'period' => $row['period'],
                'strong_buy' => intval($row['strong_buy']),
                'buy' => intval($row['buy']),
                'hold' => intval($row['hold']),
                'sell' => intval($row['sell']),
                'strong_sell' => intval($row['strong_sell'])
            );
        }
    }
    $data['analyst_history'] = $analyst_hist;

    // Price target
    $tr = $conn->query("SELECT target_high, target_low, target_mean, target_median, last_updated FROM lm_price_targets WHERE ticker = '" . _sm_esc($ticker) . "'");
    if ($tr && $trow = $tr->fetch_assoc()) {
        $data['price_target'] = array(
            'high' => floatval($trow['target_high']),
            'low' => floatval($trow['target_low']),
            'mean' => floatval($trow['target_mean']),
            'median' => floatval($trow['target_median']),
            'last_updated' => $trow['last_updated']
        );
        if ($data['current_price'] > 0 && $data['price_target']['mean'] > 0) {
            $data['price_target']['upside_pct'] = round((($data['price_target']['mean'] - $data['current_price']) / $data['current_price']) * 100, 2);
        }
    } else {
        $data['price_target'] = null;
    }

    // Insider trades (last 180 days)
    $ir = $conn->query("SELECT filer_name, filer_title, transaction_date, transaction_type, shares, price_per_share, total_value
        FROM gm_sec_insider_trades WHERE ticker = '" . _sm_esc($ticker) . "'
        AND transaction_date > DATE_SUB(CURDATE(), INTERVAL 180 DAY)
        ORDER BY transaction_date DESC LIMIT 15");
    $insider_trades = array();
    if ($ir) {
        while ($row = $ir->fetch_assoc()) {
            $insider_trades[] = array(
                'filer' => $row['filer_name'],
                'title' => $row['filer_title'],
                'date' => $row['transaction_date'],
                'type' => ($row['transaction_type'] === 'P') ? 'BUY' : 'SELL',
                'shares' => floatval($row['shares']),
                'price' => floatval($row['price_per_share']),
                'value' => floatval($row['total_value'])
            );
        }
    }
    $data['insider_trades'] = $insider_trades;

    // MSPR sentiment
    $mr = $conn->query("SELECT year, month, mspr, change_val FROM lm_insider_sentiment WHERE ticker = '" . _sm_esc($ticker) . "' ORDER BY year DESC, month DESC LIMIT 6");
    $mspr_data = array();
    if ($mr) {
        while ($row = $mr->fetch_assoc()) {
            $mspr_data[] = array(
                'year' => intval($row['year']),
                'month' => intval($row['month']),
                'mspr' => floatval($row['mspr']),
                'change' => floatval($row['change_val'])
            );
        }
    }
    $data['mspr_sentiment'] = $mspr_data;

    // 13F holdings
    $qr = $conn->query("SELECT filing_quarter FROM gm_sec_13f_holdings WHERE ticker = '" . _sm_esc($ticker) . "' ORDER BY filing_date DESC LIMIT 1");
    if ($qr && $qrow = $qr->fetch_assoc()) {
        $q = $qrow['filing_quarter'];
        $fr = $conn->query("SELECT fund_name, value_thousands, shares, change_pct, change_type
            FROM gm_sec_13f_holdings WHERE ticker = '" . _sm_esc($ticker) . "' AND filing_quarter = '" . _sm_esc($q) . "'
            ORDER BY value_thousands DESC LIMIT 20");
        $funds = array();
        if ($fr) {
            while ($row = $fr->fetch_assoc()) {
                $funds[] = array(
                    'fund' => $row['fund_name'],
                    'value_k' => intval($row['value_thousands']),
                    'shares' => intval($row['shares']),
                    'change_pct' => floatval($row['change_pct']),
                    'change_type' => $row['change_type']
                );
            }
        }
        $data['holdings_13f'] = array('quarter' => $q, 'funds' => $funds);
    } else {
        $data['holdings_13f'] = null;
    }

    // WSB sentiment
    $wr = $conn->query("SELECT scan_date, mentions_24h, sentiment, wsb_score, top_post_title
        FROM lm_wsb_sentiment WHERE ticker = '" . _sm_esc($ticker) . "' ORDER BY scan_date DESC LIMIT 5");
    $wsb_data = array();
    if ($wr) {
        while ($row = $wr->fetch_assoc()) {
            $wsb_data[] = array(
                'date' => $row['scan_date'],
                'mentions' => intval($row['mentions_24h']),
                'sentiment' => floatval($row['sentiment']),
                'score' => floatval($row['wsb_score']),
                'top_post' => $row['top_post_title']
            );
        }
    }
    $data['wsb'] = $wsb_data;

    // News sentiment (if exists)
    $nr = $conn->query("SELECT fetch_date, sentiment_score, articles_analyzed, buzz_score
        FROM gm_news_sentiment WHERE ticker = '" . _sm_esc($ticker) . "' ORDER BY fetch_date DESC LIMIT 5");
    $news_data = array();
    if ($nr) {
        while ($row = $nr->fetch_assoc()) {
            $news_data[] = array(
                'date' => $row['fetch_date'],
                'sentiment' => floatval($row['sentiment_score']),
                'articles' => intval($row['articles_analyzed']),
                'buzz' => floatval($row['buzz_score'])
            );
        }
    }
    $data['news_sentiment'] = $news_data;

    _sm_cache_set('ticker_' . $ticker, $data);

    echo json_encode(array('ok' => true, 'action' => 'ticker', 'ticker' => $ticker, 'data' => $data));
    exit;
}


// ── wsb ────────────────────────────────────────────────────
if ($action === 'wsb') {

    $cached = _sm_cache_get('wsb_latest', 300);
    if ($cached) {
        echo json_encode(array('ok' => true, 'action' => 'wsb', 'data' => $cached, 'cached' => true));
        exit;
    }

    // Get latest scan_date
    $dr = $conn->query("SELECT MAX(scan_date) as latest FROM lm_wsb_sentiment");
    $latest_date = $today;
    if ($dr && $drow = $dr->fetch_assoc()) {
        if ($drow['latest']) $latest_date = $drow['latest'];
    }

    $wr = $conn->query("SELECT ticker, scan_date, mentions_24h, sentiment, total_upvotes, wsb_score, top_post_title
        FROM lm_wsb_sentiment WHERE scan_date = '" . _sm_esc($latest_date) . "'
        ORDER BY wsb_score DESC");

    $wsb_data = array();
    if ($wr) {
        while ($row = $wr->fetch_assoc()) {
            $wsb_data[] = array(
                'ticker' => $row['ticker'],
                'date' => $row['scan_date'],
                'mentions' => intval($row['mentions_24h']),
                'sentiment' => floatval($row['sentiment']),
                'upvotes' => intval($row['total_upvotes']),
                'score' => floatval($row['wsb_score']),
                'top_post' => $row['top_post_title']
            );
        }
    }

    _sm_cache_set('wsb_latest', $wsb_data);

    echo json_encode(array('ok' => true, 'action' => 'wsb', 'scan_date' => $latest_date, 'data' => $wsb_data));
    exit;
}


// ── performance ────────────────────────────────────────────
if ($action === 'performance') {

    $cached = _sm_cache_get('signal_performance', 600);
    if ($cached) {
        echo json_encode(array('ok' => true, 'action' => 'performance', 'data' => $cached, 'cached' => true));
        exit;
    }

    $pr = $conn->query("SELECT signal_source,
        COUNT(*) as total_signals,
        AVG(return_7d) as avg_return_7d,
        AVG(return_30d) as avg_return_30d,
        AVG(return_90d) as avg_return_90d,
        SUM(CASE WHEN return_7d > 0 THEN 1 ELSE 0 END) as wins_7d,
        SUM(CASE WHEN return_30d > 0 THEN 1 ELSE 0 END) as wins_30d,
        MIN(signal_date) as earliest_signal,
        MAX(signal_date) as latest_signal
        FROM lm_signal_performance
        GROUP BY signal_source
        ORDER BY avg_return_30d DESC");

    $perf_data = array();
    if ($pr) {
        while ($row = $pr->fetch_assoc()) {
            $total = intval($row['total_signals']);
            $perf_data[] = array(
                'source' => $row['signal_source'],
                'total_signals' => $total,
                'avg_return_7d' => round(floatval($row['avg_return_7d']), 2),
                'avg_return_30d' => round(floatval($row['avg_return_30d']), 2),
                'avg_return_90d' => round(floatval($row['avg_return_90d']), 2),
                'win_rate_7d' => ($total > 0) ? round((intval($row['wins_7d']) / $total) * 100, 2) : 0,
                'win_rate_30d' => ($total > 0) ? round((intval($row['wins_30d']) / $total) * 100, 2) : 0,
                'date_range' => $row['earliest_signal'] . ' to ' . $row['latest_signal']
            );
        }
    }

    _sm_cache_set('signal_performance', $perf_data);

    echo json_encode(array('ok' => true, 'action' => 'performance', 'data' => $perf_data));
    exit;
}


// ── showdown ───────────────────────────────────────────────
if ($action === 'showdown') {

    $cached = _sm_cache_get('showdown_data', 300);
    if ($cached) {
        echo json_encode(array('ok' => true, 'action' => 'showdown', 'data' => $cached, 'cached' => true));
        exit;
    }

    // Get last 10 showdown snapshots
    $sr = $conn->query("SELECT period_start, period_end,
        challenger_trades, challenger_wins, challenger_win_rate, challenger_pnl, challenger_sharpe, challenger_max_dd,
        best_algo_name, best_algo_trades, best_algo_wins, best_algo_win_rate, best_algo_pnl, best_algo_sharpe, best_algo_max_dd,
        challenger_rank, total_algos, snapshot_date
        FROM lm_challenger_showdown ORDER BY snapshot_date DESC LIMIT 10");

    $showdown_data = array();
    if ($sr) {
        while ($row = $sr->fetch_assoc()) {
            $showdown_data[] = array(
                'period' => $row['period_start'] . ' to ' . $row['period_end'],
                'snapshot_date' => $row['snapshot_date'],
                'challenger' => array(
                    'trades' => intval($row['challenger_trades']),
                    'wins' => intval($row['challenger_wins']),
                    'win_rate' => floatval($row['challenger_win_rate']),
                    'pnl' => floatval($row['challenger_pnl']),
                    'sharpe' => floatval($row['challenger_sharpe']),
                    'max_dd' => floatval($row['challenger_max_dd'])
                ),
                'best_algo' => array(
                    'name' => $row['best_algo_name'],
                    'trades' => intval($row['best_algo_trades']),
                    'wins' => intval($row['best_algo_wins']),
                    'win_rate' => floatval($row['best_algo_win_rate']),
                    'pnl' => floatval($row['best_algo_pnl']),
                    'sharpe' => floatval($row['best_algo_sharpe']),
                    'max_dd' => floatval($row['best_algo_max_dd'])
                ),
                'rank' => intval($row['challenger_rank']) . '/' . intval($row['total_algos'])
            );
        }
    }

    _sm_cache_set('showdown_data', $showdown_data);

    echo json_encode(array('ok' => true, 'action' => 'showdown', 'data' => $showdown_data));
    exit;
}


// ── schema ─────────────────────────────────────────────────
if ($action === 'schema') {
    echo json_encode(array('ok' => true, 'action' => 'schema', 'message' => 'Schema ensured'));
    exit;
}


// ════════════════════════════════════════════════════════════
//  DEFAULT — help / status
// ════════════════════════════════════════════════════════════

// Check what data exists
$has_analyst = false;
$has_sentiment = false;
$has_consensus = false;
$has_13f = false;
$has_insider = false;
$has_wsb = false;
$has_showdown = false;

$chk = $conn->query("SELECT COUNT(*) as c FROM lm_analyst_ratings");
if ($chk && $row = $chk->fetch_assoc()) { $has_analyst = intval($row['c']) > 0; }

$chk = $conn->query("SELECT COUNT(*) as c FROM lm_insider_sentiment");
if ($chk && $row = $chk->fetch_assoc()) { $has_sentiment = intval($row['c']) > 0; }

$chk = $conn->query("SELECT COUNT(*) as c FROM lm_smart_consensus");
if ($chk && $row = $chk->fetch_assoc()) { $has_consensus = intval($row['c']) > 0; }

$chk = $conn->query("SELECT COUNT(*) as c FROM gm_sec_13f_holdings");
if ($chk && $row = $chk->fetch_assoc()) { $has_13f = intval($row['c']) > 0; }

$chk = $conn->query("SELECT COUNT(*) as c FROM gm_sec_insider_trades");
if ($chk && $row = $chk->fetch_assoc()) { $has_insider = intval($row['c']) > 0; }

$chk = $conn->query("SELECT COUNT(*) as c FROM lm_wsb_sentiment");
if ($chk && $row = $chk->fetch_assoc()) { $has_wsb = intval($row['c']) > 0; }

$chk = $conn->query("SELECT COUNT(*) as c FROM lm_challenger_showdown");
if ($chk && $row = $chk->fetch_assoc()) { $has_showdown = intval($row['c']) > 0; }

echo json_encode(array(
    'ok' => true,
    'action' => 'help',
    'message' => 'Smart Money Intelligence API',
    'tickers' => $SM_TICKERS,
    'data_status' => array(
        'analyst_ratings' => $has_analyst,
        'insider_sentiment' => $has_sentiment,
        'smart_consensus' => $has_consensus,
        '13f_holdings' => $has_13f,
        'insider_trades' => $has_insider,
        'wsb_sentiment' => $has_wsb,
        'challenger_showdown' => $has_showdown
    ),
    'public_actions' => array(
        'overview' => 'Top consensus, insider clusters, analyst picks, challenger status',
        'analyst' => 'Analyst ratings + price targets (?ticker=AAPL optional)',
        'insider' => 'Insider trades + MSPR sentiment (?ticker=AAPL optional)',
        'smart_money' => '13F fund holdings (?ticker=AAPL optional)',
        '13f' => 'Alias for smart_money',
        'consensus' => 'Consensus scores with component breakdown (?ticker=AAPL optional)',
        'leaderboard' => 'Guru/fund performance rankings',
        'ticker' => 'Unified view for one ticker (?ticker=AAPL required)',
        'wsb' => 'WallStreetBets sentiment data',
        'performance' => 'Signal source performance tracking',
        'showdown' => 'Challenger Bot vs best algo comparison',
        'schema' => 'Trigger schema creation'
    ),
    'admin_actions' => array(
        'fetch_analyst' => 'Fetch analyst ratings + price targets from Finnhub (key required)',
        'fetch_sentiment' => 'Fetch insider sentiment MSPR from Finnhub (key required)',
        'ingest_wsb' => 'POST WSB sentiment data (key required)',
        'ingest_13f' => 'POST 13F holdings data (key required)',
        'calculate_consensus' => 'Calculate consensus scores for all tickers (key required)',
        'generate_challenger' => 'Generate Challenger Bot signals from consensus (key required)',
        'update_showdown' => 'Update Challenger vs algo showdown stats (key required)',
        'snapshot' => 'Cache overview data for fast reads (key required)'
    )
));
?>
