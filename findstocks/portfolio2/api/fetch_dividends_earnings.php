<?php
/**
 * Fetch and serve dividend + earnings data.
 * Uses Yahoo Finance v8 chart API (dividends) and v10 quoteSummary (earnings/fundamentals).
 * PHP 5.2 compatible.
 *
 * Actions:
 *   fetch_all               — fetch 5 tickers at a time (batch mode)
 *   fetch_one&ticker=AAPL   — fetch single ticker
 *   get_dividends&ticker=X  — read stored dividend history
 *   get_earnings&ticker=X   — read stored earnings history
 *   get_fundamentals&ticker=X (or ticker=all) — read fundamentals
 *   upcoming                — upcoming dividends & earnings next 30 days
 *   dividend_leaders        — top 20 by dividend yield
 *   earnings_surprises      — recent positive/negative surprises
 */
require_once dirname(__FILE__) . '/db_connect.php';

// Ensure tables exist (silent — no JSON output)
$conn->query("CREATE TABLE IF NOT EXISTS stock_dividends (
    id INT AUTO_INCREMENT PRIMARY KEY, ticker VARCHAR(10) NOT NULL, ex_date DATE NOT NULL,
    payment_date DATE DEFAULT NULL, amount DECIMAL(10,6) NOT NULL DEFAULT 0,
    frequency VARCHAR(20) NOT NULL DEFAULT 'quarterly', source VARCHAR(20) NOT NULL DEFAULT 'yahoo_v8',
    updated_at DATETIME NOT NULL, UNIQUE KEY idx_ticker_exdate (ticker, ex_date),
    KEY idx_exdate (ex_date), KEY idx_ticker (ticker)) ENGINE=MyISAM DEFAULT CHARSET=utf8");
$conn->query("CREATE TABLE IF NOT EXISTS stock_earnings (
    id INT AUTO_INCREMENT PRIMARY KEY, ticker VARCHAR(10) NOT NULL, quarter_end DATE NOT NULL,
    earnings_date DATE DEFAULT NULL, eps_actual DECIMAL(10,4) DEFAULT NULL,
    eps_estimate DECIMAL(10,4) DEFAULT NULL, eps_surprise DECIMAL(10,4) DEFAULT NULL,
    surprise_pct DECIMAL(10,4) DEFAULT NULL, revenue_actual BIGINT DEFAULT NULL,
    revenue_estimate BIGINT DEFAULT NULL, source VARCHAR(20) NOT NULL DEFAULT 'yahoo_v10',
    updated_at DATETIME NOT NULL, UNIQUE KEY idx_ticker_quarter (ticker, quarter_end),
    KEY idx_earnings_date (earnings_date), KEY idx_ticker (ticker)) ENGINE=MyISAM DEFAULT CHARSET=utf8");
$conn->query("CREATE TABLE IF NOT EXISTS stock_fundamentals (
    id INT AUTO_INCREMENT PRIMARY KEY, ticker VARCHAR(10) NOT NULL,
    trailing_eps DECIMAL(10,4) DEFAULT NULL, forward_eps DECIMAL(10,4) DEFAULT NULL,
    trailing_pe DECIMAL(10,4) DEFAULT NULL, forward_pe DECIMAL(10,4) DEFAULT NULL,
    peg_ratio DECIMAL(10,4) DEFAULT NULL, dividend_rate DECIMAL(10,4) DEFAULT NULL,
    dividend_yield DECIMAL(10,6) DEFAULT NULL, trailing_annual_div_rate DECIMAL(10,4) DEFAULT NULL,
    trailing_annual_div_yield DECIMAL(10,6) DEFAULT NULL, five_yr_avg_div_yield DECIMAL(10,6) DEFAULT NULL,
    payout_ratio DECIMAL(10,4) DEFAULT NULL, ex_dividend_date DATE DEFAULT NULL,
    next_earnings_date DATE DEFAULT NULL, price_to_book DECIMAL(10,4) DEFAULT NULL,
    enterprise_to_revenue DECIMAL(10,4) DEFAULT NULL, total_revenue BIGINT DEFAULT NULL,
    ebitda BIGINT DEFAULT NULL, total_debt BIGINT DEFAULT NULL, current_ratio DECIMAL(10,4) DEFAULT NULL,
    roe DECIMAL(10,4) DEFAULT NULL, gross_margins DECIMAL(10,4) DEFAULT NULL,
    operating_margins DECIMAL(10,4) DEFAULT NULL, recommendation_key VARCHAR(20) DEFAULT NULL,
    target_mean_price DECIMAL(10,4) DEFAULT NULL, source VARCHAR(20) NOT NULL DEFAULT 'yahoo_v10',
    updated_at DATETIME NOT NULL, UNIQUE KEY idx_ticker (ticker)) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? trim($_GET['action']) : '';
$ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';

// ═══════════════════════════════════════════════
// Helper: safe value extraction from Yahoo JSON
// ═══════════════════════════════════════════════
function _yraw($obj, $key) {
    if (!is_array($obj) || !isset($obj[$key])) return null;
    $v = $obj[$key];
    if (is_array($v) && isset($v['raw'])) return $v['raw'];
    return $v;
}

function _yraw_date($obj, $key) {
    $ts = _yraw($obj, $key);
    if ($ts === null || !is_numeric($ts)) return null;
    return date('Y-m-d', (int)$ts);
}

// ═══════════════════════════════════════════════
// Yahoo Finance v8: fetch dividend events
// ═══════════════════════════════════════════════
function fetch_dividend_events($tk) {
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/'
         . urlencode($tk)
         . '?range=2y&interval=1d&events=div&includeAdjustedClose=true';

    $ctx = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\n",
            'timeout' => 15,
            'ignore_errors' => true
        )
    ));

    $json = @file_get_contents($url, false, $ctx);
    if ($json === false) return array('_error' => 'v8 fetch failed');

    $data = json_decode($json, true);
    if (!$data || !isset($data['chart']['result'][0])) {
        return array('_error' => 'v8 parse failed: ' . substr($json, 0, 200));
    }

    $result = $data['chart']['result'][0];
    if (!isset($result['events']['dividends'])) return array(); // No dividends for this ticker

    $divs = $result['events']['dividends'];
    $out = array();
    foreach ($divs as $ts => $d) {
        $amount = isset($d['amount']) ? (float)$d['amount'] : 0;
        if ($amount <= 0) continue;
        $out[] = array(
            'ex_date' => date('Y-m-d', (int)$ts),
            'amount'  => round($amount, 6)
        );
    }
    return $out;
}

// ═══════════════════════════════════════════════
// Yahoo Finance v10: fetch quoteSummary
// ═══════════════════════════════════════════════
function fetch_quote_summary($tk) {
    $modules = 'earningsHistory,calendarEvents,summaryDetail,defaultKeyStatistics,financialData';
    $url = 'https://query1.finance.yahoo.com/v10/finance/quoteSummary/'
         . urlencode($tk)
         . '?modules=' . $modules;

    $ctx = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\n",
            'timeout' => 15,
            'ignore_errors' => true
        )
    ));

    $json = @file_get_contents($url, false, $ctx);
    if ($json === false) return array('_error' => 'v10 fetch failed');

    $data = json_decode($json, true);
    if (!$data || !isset($data['quoteSummary']['result'][0])) {
        return array('_error' => 'v10 parse failed: ' . substr($json, 0, 300));
    }

    return $data['quoteSummary']['result'][0];
}

// ═══════════════════════════════════════════════
// Save dividends to DB
// ═══════════════════════════════════════════════
function save_dividends($conn, $tk, $dividends) {
    $saved = 0;
    $safe_tk = $conn->real_escape_string($tk);
    $now = date('Y-m-d H:i:s');
    foreach ($dividends as $d) {
        $safe_date = $conn->real_escape_string($d['ex_date']);
        $amount = (float)$d['amount'];
        $sql = "INSERT INTO stock_dividends (ticker, ex_date, amount, source, updated_at)
                VALUES ('$safe_tk', '$safe_date', $amount, 'yahoo_v8', '$now')
                ON DUPLICATE KEY UPDATE amount=$amount, updated_at='$now'";
        if ($conn->query($sql)) $saved++;
    }
    return $saved;
}

// ═══════════════════════════════════════════════
// Save earnings to DB
// ═══════════════════════════════════════════════
function save_earnings($conn, $tk, $earnings_history) {
    $saved = 0;
    $safe_tk = $conn->real_escape_string($tk);
    $now = date('Y-m-d H:i:s');
    foreach ($earnings_history as $e) {
        $quarter_ts = _yraw($e, 'quarter');
        if (!$quarter_ts || !is_numeric($quarter_ts)) continue;
        $quarter_end = date('Y-m-d', (int)$quarter_ts);
        $safe_qe = $conn->real_escape_string($quarter_end);

        $eps_actual   = _yraw($e, 'epsActual');
        $eps_estimate = _yraw($e, 'epsEstimate');
        $eps_surprise = _yraw($e, 'epsDifference');
        $surprise_pct = _yraw($e, 'surprisePercent');

        $sql = "INSERT INTO stock_earnings (ticker, quarter_end, eps_actual, eps_estimate, eps_surprise, surprise_pct, source, updated_at)
                VALUES ('$safe_tk', '$safe_qe', "
                . ($eps_actual !== null ? (float)$eps_actual : 'NULL') . ", "
                . ($eps_estimate !== null ? (float)$eps_estimate : 'NULL') . ", "
                . ($eps_surprise !== null ? (float)$eps_surprise : 'NULL') . ", "
                . ($surprise_pct !== null ? (float)$surprise_pct : 'NULL') . ", "
                . "'yahoo_v10', '$now')
                ON DUPLICATE KEY UPDATE
                    eps_actual=" . ($eps_actual !== null ? (float)$eps_actual : 'NULL') . ",
                    eps_estimate=" . ($eps_estimate !== null ? (float)$eps_estimate : 'NULL') . ",
                    eps_surprise=" . ($eps_surprise !== null ? (float)$eps_surprise : 'NULL') . ",
                    surprise_pct=" . ($surprise_pct !== null ? (float)$surprise_pct : 'NULL') . ",
                    updated_at='$now'";
        if ($conn->query($sql)) $saved++;
    }
    return $saved;
}

// ═══════════════════════════════════════════════
// Save fundamentals to DB
// ═══════════════════════════════════════════════
function save_fundamentals($conn, $tk, $summary) {
    $safe_tk = $conn->real_escape_string($tk);
    $now = date('Y-m-d H:i:s');

    $sd = isset($summary['summaryDetail']) ? $summary['summaryDetail'] : array();
    $ks = isset($summary['defaultKeyStatistics']) ? $summary['defaultKeyStatistics'] : array();
    $fd = isset($summary['financialData']) ? $summary['financialData'] : array();
    $ce = isset($summary['calendarEvents']) ? $summary['calendarEvents'] : array();

    // Extract values
    $trailing_eps = _yraw($ks, 'trailingEps');
    $forward_eps  = _yraw($ks, 'forwardEps');
    $trailing_pe  = _yraw($sd, 'trailingPE');
    $forward_pe   = _yraw($sd, 'forwardPE');
    $peg_ratio    = _yraw($ks, 'pegRatio');

    $div_rate     = _yraw($sd, 'dividendRate');
    $div_yield    = _yraw($sd, 'dividendYield');
    $trail_ann_rate  = _yraw($sd, 'trailingAnnualDividendRate');
    $trail_ann_yield = _yraw($sd, 'trailingAnnualDividendYield');
    $five_yr_avg     = _yraw($sd, 'fiveYearAvgDividendYield');
    $payout_ratio    = _yraw($sd, 'payoutRatio');

    $ex_div_date  = _yraw_date($sd, 'exDividendDate');
    // Next earnings date from calendarEvents
    $next_earn = null;
    if (isset($ce['earnings']['earningsDate']) && is_array($ce['earnings']['earningsDate']) && count($ce['earnings']['earningsDate']) > 0) {
        $next_earn = _yraw_date($ce['earnings']['earningsDate'][0], '');
        // earningsDate items might be raw timestamps directly
        if ($next_earn === null) {
            $ed = $ce['earnings']['earningsDate'][0];
            if (is_array($ed) && isset($ed['raw'])) {
                $next_earn = date('Y-m-d', (int)$ed['raw']);
            } elseif (is_numeric($ed)) {
                $next_earn = date('Y-m-d', (int)$ed);
            }
        }
    }

    $ptb = _yraw($ks, 'priceToBook');
    $etr = _yraw($ks, 'enterpriseToRevenue');
    $rev = _yraw($fd, 'totalRevenue');
    $ebitda = _yraw($fd, 'ebitda');
    $debt = _yraw($fd, 'totalDebt');
    $cr   = _yraw($fd, 'currentRatio');
    $roe  = _yraw($fd, 'returnOnEquity');
    $gm   = _yraw($fd, 'grossMargins');
    $om   = _yraw($fd, 'operatingMargins');
    $rec_key = isset($fd['recommendationKey']) ? $fd['recommendationKey'] : null;
    $target  = _yraw($fd, 'targetMeanPrice');

    // Build REPLACE INTO
    $fields = array(
        'ticker' => "'$safe_tk'",
        'trailing_eps' => ($trailing_eps !== null ? (float)$trailing_eps : 'NULL'),
        'forward_eps' => ($forward_eps !== null ? (float)$forward_eps : 'NULL'),
        'trailing_pe' => ($trailing_pe !== null ? (float)$trailing_pe : 'NULL'),
        'forward_pe' => ($forward_pe !== null ? (float)$forward_pe : 'NULL'),
        'peg_ratio' => ($peg_ratio !== null ? (float)$peg_ratio : 'NULL'),
        'dividend_rate' => ($div_rate !== null ? (float)$div_rate : 'NULL'),
        'dividend_yield' => ($div_yield !== null ? (float)$div_yield : 'NULL'),
        'trailing_annual_div_rate' => ($trail_ann_rate !== null ? (float)$trail_ann_rate : 'NULL'),
        'trailing_annual_div_yield' => ($trail_ann_yield !== null ? (float)$trail_ann_yield : 'NULL'),
        'five_yr_avg_div_yield' => ($five_yr_avg !== null ? (float)$five_yr_avg : 'NULL'),
        'payout_ratio' => ($payout_ratio !== null ? (float)$payout_ratio : 'NULL'),
        'ex_dividend_date' => ($ex_div_date !== null ? "'" . $conn->real_escape_string($ex_div_date) . "'" : 'NULL'),
        'next_earnings_date' => ($next_earn !== null ? "'" . $conn->real_escape_string($next_earn) . "'" : 'NULL'),
        'price_to_book' => ($ptb !== null ? (float)$ptb : 'NULL'),
        'enterprise_to_revenue' => ($etr !== null ? (float)$etr : 'NULL'),
        'total_revenue' => ($rev !== null ? (int)$rev : 'NULL'),
        'ebitda' => ($ebitda !== null ? (int)$ebitda : 'NULL'),
        'total_debt' => ($debt !== null ? (int)$debt : 'NULL'),
        'current_ratio' => ($cr !== null ? (float)$cr : 'NULL'),
        'roe' => ($roe !== null ? (float)$roe : 'NULL'),
        'gross_margins' => ($gm !== null ? (float)$gm : 'NULL'),
        'operating_margins' => ($om !== null ? (float)$om : 'NULL'),
        'recommendation_key' => ($rec_key !== null ? "'" . $conn->real_escape_string($rec_key) . "'" : 'NULL'),
        'target_mean_price' => ($target !== null ? (float)$target : 'NULL'),
        'source' => "'yahoo_v10'",
        'updated_at' => "'$now'"
    );

    $cols = array();
    $vals = array();
    foreach ($fields as $col => $val) {
        $cols[] = $col;
        $vals[] = $val;
    }

    $sql = "REPLACE INTO stock_fundamentals (" . implode(', ', $cols) . ") VALUES (" . implode(', ', $vals) . ")";
    return $conn->query($sql) ? true : false;
}

// ═══════════════════════════════════════════════
// Process one ticker: fetch dividends + earnings + fundamentals
// ═══════════════════════════════════════════════
function process_ticker($conn, $tk) {
    $result = array('ticker' => $tk, 'dividends_saved' => 0, 'earnings_saved' => 0, 'fundamentals' => false, 'errors' => array());

    // 1. Fetch dividend events via v8
    $divs = fetch_dividend_events($tk);
    if (isset($divs['_error'])) {
        $result['errors'][] = 'v8: ' . $divs['_error'];
        $divs = array();
    }
    if (count($divs) > 0) {
        $result['dividends_saved'] = save_dividends($conn, $tk, $divs);
    }

    // Small delay between API calls
    usleep(500000); // 0.5s

    // 2. Fetch quoteSummary via v10
    $summary = fetch_quote_summary($tk);
    if (isset($summary['_error'])) {
        $result['errors'][] = 'v10: ' . $summary['_error'];
        $summary = null;
    }
    if ($summary !== null) {
        // Save earnings history
        if (isset($summary['earningsHistory']['history']) && is_array($summary['earningsHistory']['history'])) {
            $result['earnings_saved'] = save_earnings($conn, $tk, $summary['earningsHistory']['history']);
        }
        // Save fundamentals snapshot
        $result['fundamentals'] = save_fundamentals($conn, $tk, $summary);
    }

    return $result;
}

// ═══════════════════════════════════════════════
// Route actions
// ═══════════════════════════════════════════════

if ($action === 'fetch_one' && $ticker !== '') {
    // Single ticker fetch
    $r = process_ticker($conn, $ticker);
    echo json_encode(array('ok' => true, 'result' => $r));

} elseif ($action === 'fetch_all') {
    // Batch fetch: 5 tickers at a time, skip recently updated (12h)
    $cutoff = date('Y-m-d H:i:s', time() - 43200); // 12 hours ago
    $sql = "SELECT s.ticker FROM stocks s
            LEFT JOIN stock_fundamentals sf ON s.ticker = sf.ticker
            WHERE sf.ticker IS NULL OR sf.updated_at < '$cutoff'
            ORDER BY s.ticker
            LIMIT 5";
    $res = $conn->query($sql);
    $tickers_to_fetch = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $tickers_to_fetch[] = $row['ticker'];
        }
    }

    // Count remaining
    $sql2 = "SELECT COUNT(*) as cnt FROM stocks s
             LEFT JOIN stock_fundamentals sf ON s.ticker = sf.ticker
             WHERE sf.ticker IS NULL OR sf.updated_at < '$cutoff'";
    $res2 = $conn->query($sql2);
    $remaining = 0;
    if ($res2 && $row2 = $res2->fetch_assoc()) {
        $remaining = (int)$row2['cnt'];
    }

    $results_arr = array();
    $processed = 0;
    foreach ($tickers_to_fetch as $tk) {
        $r = process_ticker($conn, $tk);
        $results_arr[] = $r;
        $processed++;
        if ($processed < count($tickers_to_fetch)) {
            sleep(1);
        }
    }

    $remaining_after = $remaining - $processed;
    if ($remaining_after < 0) $remaining_after = 0;

    echo json_encode(array(
        'ok' => true,
        'processed' => $processed,
        'remaining' => $remaining_after,
        'results' => $results_arr
    ));

} elseif ($action === 'get_dividends' && $ticker !== '') {
    // Read stored dividend history
    $safe_tk = $conn->real_escape_string($ticker);
    $sql = "SELECT ex_date, payment_date, amount, frequency, source, updated_at
            FROM stock_dividends WHERE ticker='$safe_tk' ORDER BY ex_date DESC";
    $res = $conn->query($sql);
    $divs = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $row['amount'] = (float)$row['amount'];
            $divs[] = $row;
        }
    }
    echo json_encode(array('ok' => true, 'ticker' => $ticker, 'dividends' => $divs, 'count' => count($divs)));

} elseif ($action === 'get_earnings' && $ticker !== '') {
    // Read stored earnings history
    $safe_tk = $conn->real_escape_string($ticker);
    $sql = "SELECT quarter_end, earnings_date, eps_actual, eps_estimate, eps_surprise, surprise_pct, source, updated_at
            FROM stock_earnings WHERE ticker='$safe_tk' ORDER BY quarter_end DESC";
    $res = $conn->query($sql);
    $earnings = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            if ($row['eps_actual'] !== null) $row['eps_actual'] = (float)$row['eps_actual'];
            if ($row['eps_estimate'] !== null) $row['eps_estimate'] = (float)$row['eps_estimate'];
            if ($row['eps_surprise'] !== null) $row['eps_surprise'] = (float)$row['eps_surprise'];
            if ($row['surprise_pct'] !== null) $row['surprise_pct'] = (float)$row['surprise_pct'];
            $earnings[] = $row;
        }
    }
    echo json_encode(array('ok' => true, 'ticker' => $ticker, 'earnings' => $earnings, 'count' => count($earnings)));

} elseif ($action === 'get_fundamentals') {
    if ($ticker === 'ALL' || $ticker === '') {
        // All tickers
        $sql = "SELECT sf.*, s.company_name FROM stock_fundamentals sf
                LEFT JOIN stocks s ON sf.ticker = s.ticker
                ORDER BY sf.ticker";
        $res = $conn->query($sql);
        $funds = array();
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                // Cast numeric fields
                foreach (array('trailing_eps','forward_eps','trailing_pe','forward_pe','peg_ratio','dividend_rate','dividend_yield','trailing_annual_div_rate','trailing_annual_div_yield','five_yr_avg_div_yield','payout_ratio','price_to_book','enterprise_to_revenue','current_ratio','roe','gross_margins','operating_margins','target_mean_price') as $f) {
                    if ($row[$f] !== null) $row[$f] = (float)$row[$f];
                }
                foreach (array('total_revenue','ebitda','total_debt') as $f) {
                    if ($row[$f] !== null) $row[$f] = (int)$row[$f];
                }
                $funds[] = $row;
            }
        }
        echo json_encode(array('ok' => true, 'fundamentals' => $funds, 'count' => count($funds)));
    } else {
        // Single ticker
        $safe_tk = $conn->real_escape_string($ticker);
        $sql = "SELECT sf.*, s.company_name FROM stock_fundamentals sf
                LEFT JOIN stocks s ON sf.ticker = s.ticker
                WHERE sf.ticker='$safe_tk'";
        $res = $conn->query($sql);
        if ($res && $row = $res->fetch_assoc()) {
            foreach (array('trailing_eps','forward_eps','trailing_pe','forward_pe','peg_ratio','dividend_rate','dividend_yield','trailing_annual_div_rate','trailing_annual_div_yield','five_yr_avg_div_yield','payout_ratio','price_to_book','enterprise_to_revenue','current_ratio','roe','gross_margins','operating_margins','target_mean_price') as $f) {
                if ($row[$f] !== null) $row[$f] = (float)$row[$f];
            }
            foreach (array('total_revenue','ebitda','total_debt') as $f) {
                if ($row[$f] !== null) $row[$f] = (int)$row[$f];
            }
            echo json_encode(array('ok' => true, 'ticker' => $ticker, 'fundamentals' => $row));
        } else {
            echo json_encode(array('ok' => false, 'error' => 'No fundamentals found for ' . $ticker));
        }
    }

} elseif ($action === 'upcoming') {
    // Upcoming dividends and earnings in next 30 days
    $today = date('Y-m-d');
    $in30 = date('Y-m-d', strtotime('+30 days'));

    // Upcoming dividends
    $sql = "SELECT sd.ticker, s.company_name, sd.ex_date, sd.amount, sf.dividend_yield
            FROM stock_dividends sd
            LEFT JOIN stocks s ON sd.ticker = s.ticker
            LEFT JOIN stock_fundamentals sf ON sd.ticker = sf.ticker
            WHERE sd.ex_date >= '$today' AND sd.ex_date <= '$in30'
            ORDER BY sd.ex_date ASC";
    $res = $conn->query($sql);
    $upcoming_divs = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $row['amount'] = (float)$row['amount'];
            if ($row['dividend_yield'] !== null) $row['dividend_yield'] = (float)$row['dividend_yield'];
            $upcoming_divs[] = $row;
        }
    }

    // Upcoming earnings
    $sql2 = "SELECT sf.ticker, s.company_name, sf.next_earnings_date, sf.trailing_eps, sf.forward_eps
             FROM stock_fundamentals sf
             LEFT JOIN stocks s ON sf.ticker = s.ticker
             WHERE sf.next_earnings_date >= '$today' AND sf.next_earnings_date <= '$in30'
             ORDER BY sf.next_earnings_date ASC";
    $res2 = $conn->query($sql2);
    $upcoming_earn = array();
    if ($res2) {
        while ($row = $res2->fetch_assoc()) {
            if ($row['trailing_eps'] !== null) $row['trailing_eps'] = (float)$row['trailing_eps'];
            if ($row['forward_eps'] !== null) $row['forward_eps'] = (float)$row['forward_eps'];
            $upcoming_earn[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'upcoming_dividends' => $upcoming_divs,
        'upcoming_earnings' => $upcoming_earn,
        'dividend_count' => count($upcoming_divs),
        'earnings_count' => count($upcoming_earn)
    ));

} elseif ($action === 'dividend_leaders') {
    // Top 20 by dividend yield
    $sql = "SELECT sf.ticker, s.company_name, sf.dividend_yield, sf.dividend_rate,
                   sf.trailing_annual_div_rate, sf.payout_ratio, sf.ex_dividend_date,
                   sf.trailing_eps, sf.trailing_pe
            FROM stock_fundamentals sf
            LEFT JOIN stocks s ON sf.ticker = s.ticker
            WHERE sf.dividend_yield IS NOT NULL AND sf.dividend_yield > 0
            ORDER BY sf.dividend_yield DESC
            LIMIT 20";
    $res = $conn->query($sql);
    $leaders = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            foreach (array('dividend_yield','dividend_rate','trailing_annual_div_rate','payout_ratio','trailing_eps','trailing_pe') as $f) {
                if ($row[$f] !== null) $row[$f] = (float)$row[$f];
            }
            $leaders[] = $row;
        }
    }
    echo json_encode(array('ok' => true, 'leaders' => $leaders, 'count' => count($leaders)));

} elseif ($action === 'earnings_surprises') {
    // Recent earnings surprises (last 90 days)
    $cutoff = date('Y-m-d', strtotime('-90 days'));
    $sql = "SELECT se.ticker, s.company_name, se.quarter_end, se.eps_actual, se.eps_estimate,
                   se.eps_surprise, se.surprise_pct
            FROM stock_earnings se
            LEFT JOIN stocks s ON se.ticker = s.ticker
            WHERE se.quarter_end >= '$cutoff' AND se.eps_actual IS NOT NULL AND se.eps_estimate IS NOT NULL
            ORDER BY ABS(se.surprise_pct) DESC
            LIMIT 30";
    $res = $conn->query($sql);
    $surprises = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            foreach (array('eps_actual','eps_estimate','eps_surprise','surprise_pct') as $f) {
                if ($row[$f] !== null) $row[$f] = (float)$row[$f];
            }
            $row['beat'] = ($row['surprise_pct'] !== null && $row['surprise_pct'] > 0) ? 1 : 0;
            $surprises[] = $row;
        }
    }
    echo json_encode(array('ok' => true, 'surprises' => $surprises, 'count' => count($surprises)));

} else {
    echo json_encode(array('ok' => false, 'error' => 'Missing or invalid action. Use: fetch_all, fetch_one, get_dividends, get_earnings, get_fundamentals, upcoming, dividend_leaders, earnings_surprises'));
}

$conn->close();
?>
