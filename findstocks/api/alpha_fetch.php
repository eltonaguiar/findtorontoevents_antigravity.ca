<?php
/**
 * Alpha Suite - Data Fetcher
 * Fetches fundamentals, earnings, and macro data from Yahoo Finance.
 * PHP 5.2 compatible. Uses v7/quote (batch) and v10/quoteSummary (per-ticker).
 *
 * Usage:
 *   ?action=fundamentals          - Fetch fundamentals for all universe stocks
 *   ?action=macro                 - Fetch VIX, TNX, DXY, SPY macro data
 *   ?action=earnings&batch=N      - Fetch earnings history batch N (10 per batch)
 *   ?action=prices&batch=N        - Fetch/update prices batch N (10 per batch)
 *   ?action=all                   - Fetch everything (may timeout; use steps)
 *   ?action=prices_check          - Check which tickers need price updates
 *
 * Auth: ?key=alpharefresh2026 (required for write operations)
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'status';
$key    = isset($_GET['key']) ? $_GET['key'] : '';
$batch  = isset($_GET['batch']) ? (int)$_GET['batch'] : 1;

// Auth check for write operations
$write_actions = array('fundamentals', 'macro', 'earnings', 'prices', 'all');
$needs_auth = in_array($action, $write_actions);
if ($needs_auth && $key !== 'alpharefresh2026') {
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    exit;
}

$result = array('ok' => true, 'action' => $action, 'data' => array(), 'errors' => array());

/* ================================================================
   HELPER: Yahoo Finance crumb + cookie (required since 2023)
   ================================================================ */
$_ALPHA_YAHOO_COOKIE = '';
$_ALPHA_YAHOO_CRUMB  = '';

function alpha_yahoo_get_crumb() {
    global $_ALPHA_YAHOO_COOKIE, $_ALPHA_YAHOO_CRUMB;
    if ($_ALPHA_YAHOO_CRUMB !== '') return true;

    // Step 1: Get cookie from fc.yahoo.com
    $ctx1 = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n",
            'timeout' => 10,
            'ignore_errors' => true
        )
    ));
    @file_get_contents('https://fc.yahoo.com/', false, $ctx1);
    $cookie = '';
    if (isset($http_response_header)) {
        foreach ($http_response_header as $hdr) {
            if (stripos($hdr, 'Set-Cookie:') === 0) {
                $parts = explode(';', substr($hdr, 12));
                $cookie .= trim($parts[0]) . '; ';
            }
        }
    }
    if ($cookie === '') {
        // Fallback: try consent page
        $ctx1b = stream_context_create(array(
            'http' => array(
                'method' => 'GET',
                'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\nAccept: text/html\r\n",
                'timeout' => 10,
                'follow_location' => true,
                'ignore_errors' => true
            )
        ));
        @file_get_contents('https://finance.yahoo.com/quote/AAPL', false, $ctx1b);
        if (isset($http_response_header)) {
            foreach ($http_response_header as $hdr) {
                if (stripos($hdr, 'Set-Cookie:') === 0) {
                    $parts = explode(';', substr($hdr, 12));
                    $cookie .= trim($parts[0]) . '; ';
                }
            }
        }
    }
    $_ALPHA_YAHOO_COOKIE = trim($cookie, '; ');

    // Step 2: Get crumb
    if ($_ALPHA_YAHOO_COOKIE !== '') {
        $ctx2 = stream_context_create(array(
            'http' => array(
                'method' => 'GET',
                'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\nCookie: " . $_ALPHA_YAHOO_COOKIE . "\r\n",
                'timeout' => 10,
                'ignore_errors' => true
            )
        ));
        $crumb = @file_get_contents('https://query2.finance.yahoo.com/v1/test/getcrumb', false, $ctx2);
        if ($crumb !== false && strlen($crumb) > 5 && strlen($crumb) < 60) {
            $_ALPHA_YAHOO_CRUMB = trim($crumb);
            return true;
        }
    }
    return false;
}

/* ================================================================
   HELPER: Yahoo Finance HTTP fetch with retry + crumb
   ================================================================ */
function alpha_yahoo_fetch($url, $retries) {
    global $_ALPHA_YAHOO_COOKIE, $_ALPHA_YAHOO_CRUMB;
    $attempt = 0;
    $data = false;

    // Add crumb if we have one and URL doesn't already have it
    $use_url = $url;
    if ($_ALPHA_YAHOO_CRUMB !== '' && strpos($url, 'crumb=') === false) {
        $sep = (strpos($url, '?') !== false) ? '&' : '?';
        $use_url = $url . $sep . 'crumb=' . urlencode($_ALPHA_YAHOO_CRUMB);
    }

    while ($attempt < $retries) {
        $headers = "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\nAccept: application/json\r\n";
        if ($_ALPHA_YAHOO_COOKIE !== '') {
            $headers .= "Cookie: " . $_ALPHA_YAHOO_COOKIE . "\r\n";
        }

        $ctx = stream_context_create(array(
            'http' => array(
                'method' => 'GET',
                'header' => $headers,
                'timeout' => 15,
                'ignore_errors' => true
            )
        ));
        $raw = @file_get_contents($use_url, false, $ctx);
        if ($raw !== false && strlen($raw) > 50) {
            $data = json_decode($raw, true);
            if ($data !== null) {
                return $data;
            }
        }
        $attempt++;
        if ($attempt < $retries) {
            usleep(500000 * $attempt);
        }
    }
    return false;
}

// Initialize crumb at start
alpha_yahoo_get_crumb();

/* ================================================================
   HELPER: Safe numeric extraction from Yahoo data
   ================================================================ */
function alpha_safe_num($arr, $key) {
    if (!isset($arr[$key])) return 0;
    $v = $arr[$key];
    if (is_array($v) && isset($v['raw'])) return (float)$v['raw'];
    if (is_numeric($v)) return (float)$v;
    return 0;
}

/* ================================================================
   HELPER: Insert one ticker's fundamentals into alpha_fundamentals
   ================================================================ */
function alpha_insert_fundamental($conn, $ticker, $q, $today) {
    $safe_ticker = $conn->real_escape_string($ticker);
    $mcap    = alpha_safe_num($q, 'marketCap');
    $pe_t    = alpha_safe_num($q, 'trailingPE');
    $pe_f    = alpha_safe_num($q, 'forwardPE');
    $peg     = alpha_safe_num($q, 'pegRatio');
    $pb      = alpha_safe_num($q, 'priceToBook');
    $ps      = alpha_safe_num($q, 'priceToSalesTrailing12Months');
    $dy      = alpha_safe_num($q, 'trailingAnnualDividendYield');
    if ($dy == 0) $dy = alpha_safe_num($q, 'dividendYield');
    $beta    = alpha_safe_num($q, 'beta');
    $hi52    = alpha_safe_num($q, 'fiftyTwoWeekHigh');
    $lo52    = alpha_safe_num($q, 'fiftyTwoWeekLow');
    $ma50    = alpha_safe_num($q, 'fiftyDayAverage');
    $ma200   = alpha_safe_num($q, 'twoHundredDayAverage');
    $avgvol  = alpha_safe_num($q, 'averageDailyVolume3Month');
    if ($avgvol == 0) $avgvol = alpha_safe_num($q, 'avgVolume');
    $price   = alpha_safe_num($q, 'regularMarketPrice');
    if ($price == 0) $price = alpha_safe_num($q, 'currentPrice');
    $shares  = alpha_safe_num($q, 'sharesOutstanding');
    // financialData fields
    $roe     = alpha_safe_num($q, 'returnOnEquity');
    $roa     = alpha_safe_num($q, 'returnOnAssets');
    $gm      = alpha_safe_num($q, 'grossMargins');
    $om      = alpha_safe_num($q, 'operatingMargins');
    $pm      = alpha_safe_num($q, 'profitMargins');
    $rg      = alpha_safe_num($q, 'revenueGrowth');
    $eg      = alpha_safe_num($q, 'earningsGrowth');
    $td      = alpha_safe_num($q, 'totalDebt');
    $tc      = alpha_safe_num($q, 'totalCash');
    $dte     = alpha_safe_num($q, 'debtToEquity');
    $cr      = alpha_safe_num($q, 'currentRatio');
    $fcf     = alpha_safe_num($q, 'freeCashflow');
    $ocf     = alpha_safe_num($q, 'operatingCashflow');

    $raw = $conn->real_escape_string(json_encode($q));

    $sql = "INSERT INTO alpha_fundamentals
            (ticker, fetch_date, market_cap, pe_trailing, pe_forward, peg_ratio,
             price_to_book, price_to_sales, dividend_yield, beta,
             fifty_two_week_high, fifty_two_week_low, fifty_day_avg, two_hundred_day_avg,
             avg_volume, regular_market_price, shares_outstanding,
             return_on_equity, return_on_assets, gross_margins, operating_margins, profit_margins,
             revenue_growth, earnings_growth, total_debt, total_cash, debt_to_equity,
             current_ratio, free_cashflow, operating_cashflow, raw_json)
            VALUES ('$safe_ticker', '$today', $mcap, $pe_t, $pe_f, $peg,
                    $pb, $ps, $dy, $beta,
                    $hi52, $lo52, $ma50, $ma200,
                    $avgvol, $price, $shares,
                    $roe, $roa, $gm, $om, $pm,
                    $rg, $eg, $td, $tc, $dte,
                    $cr, $fcf, $ocf, '$raw')
            ON DUPLICATE KEY UPDATE
                market_cap=$mcap, pe_trailing=$pe_t, pe_forward=$pe_f, peg_ratio=$peg,
                price_to_book=$pb, price_to_sales=$ps, dividend_yield=$dy, beta=$beta,
                fifty_two_week_high=$hi52, fifty_two_week_low=$lo52,
                fifty_day_avg=$ma50, two_hundred_day_avg=$ma200,
                avg_volume=$avgvol, regular_market_price=$price, shares_outstanding=$shares,
                return_on_equity=$roe, return_on_assets=$roa, gross_margins=$gm,
                operating_margins=$om, profit_margins=$pm, revenue_growth=$rg, earnings_growth=$eg,
                total_debt=$td, total_cash=$tc, debt_to_equity=$dte, current_ratio=$cr,
                free_cashflow=$fcf, operating_cashflow=$ocf, raw_json='$raw'";
    return $conn->query($sql);
}

/* ================================================================
   ACTION: fundamentals - Multi-source fetch with fallbacks
   Strategy: 1) v7/quote batch  2) v10/quoteSummary per-ticker  3) FMP API
   ================================================================ */
if ($action === 'fundamentals' || $action === 'all') {
    $tickers = array();
    $res = $conn->query("SELECT ticker FROM alpha_universe WHERE active=1 ORDER BY ticker");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $tickers[] = $row['ticker'];
        }
    }

    if (count($tickers) === 0) {
        $result['errors'][] = 'No tickers in universe. Run alpha_setup.php first.';
    } else {
        $today = date('Y-m-d');
        $fetched = 0;
        $method_used = 'none';

        // ── METHOD 1: Try v7/finance/quote batch (fastest) ──
        $batch_size = 20;
        $v7_works = false;
        $remaining = $tickers;

        $batch_chunks = array();
        $chunk = array();
        foreach ($tickers as $idx => $t) {
            $chunk[] = $t;
            if (count($chunk) >= $batch_size || $idx === count($tickers) - 1) {
                $batch_chunks[] = $chunk;
                $chunk = array();
            }
        }

        foreach ($batch_chunks as $batch_tickers) {
            $symbols = implode(',', $batch_tickers);
            $url = 'https://query2.finance.yahoo.com/v7/finance/quote?symbols=' . urlencode($symbols);
            $data = alpha_yahoo_fetch($url, 2);

            if ($data !== false && isset($data['quoteResponse']['result']) && count($data['quoteResponse']['result']) > 0) {
                $v7_works = true;
                $method_used = 'v7_quote';
                foreach ($data['quoteResponse']['result'] as $q) {
                    $ticker = isset($q['symbol']) ? $q['symbol'] : '';
                    if ($ticker === '') continue;
                    if (alpha_insert_fundamental($conn, $ticker, $q, $today)) {
                        $fetched++;
                        // Remove from remaining
                        $key = array_search($ticker, $remaining);
                        if ($key !== false) {
                            unset($remaining[$key]);
                        }
                    }
                }
            }
            usleep(300000);
        }

        // ── METHOD 2: Per-ticker v10/quoteSummary for remaining tickers ──
        if (count($remaining) > 0 && !$v7_works) {
            $remaining = array_values($remaining);
            // Only process up to 15 per call to stay within 30s
            $per_ticker_limit = min(15, count($remaining));
            for ($i = 0; $i < $per_ticker_limit; $i++) {
                $ticker = $remaining[$i];
                $enc = urlencode($ticker);
                $url = 'https://query2.finance.yahoo.com/v10/finance/quoteSummary/' . $enc
                     . '?modules=financialData,defaultKeyStatistics,summaryDetail,price';
                $data = alpha_yahoo_fetch($url, 2);

                if ($data !== false && isset($data['quoteSummary']['result'][0])) {
                    $qs = $data['quoteSummary']['result'][0];
                    // Merge all modules into flat array
                    $merged = array();
                    foreach ($qs as $module_name => $module_data) {
                        if (is_array($module_data)) {
                            foreach ($module_data as $k => $v) {
                                $merged[$k] = $v;
                            }
                        }
                    }
                    if (alpha_insert_fundamental($conn, $ticker, $merged, $today)) {
                        $fetched++;
                        $method_used = ($method_used === 'none') ? 'v10_summary' : $method_used . '+v10';
                    }
                }
                usleep(400000);
            }
        }

        // ── METHOD 3: Financial Modeling Prep free API fallback ──
        if ($fetched === 0) {
            // FMP free key (demo) - limited to 250 requests/day
            $fmp_key = 'demo';
            $fmp_base = 'https://financialmodelingprep.com/api/v3';

            // Batch profile endpoint (up to 50 tickers)
            $symbols = implode(',', array_slice($tickers, 0, 50));
            $fmp_url = $fmp_base . '/profile/' . $symbols . '?apikey=' . $fmp_key;
            $fmp_data = alpha_yahoo_fetch($fmp_url, 2);

            if (is_array($fmp_data) && count($fmp_data) > 0) {
                $method_used = 'fmp';
                foreach ($fmp_data as $item) {
                    $ticker = isset($item['symbol']) ? $item['symbol'] : '';
                    if ($ticker === '') continue;
                    // Map FMP fields to our standard names
                    $mapped = array(
                        'marketCap' => isset($item['mktCap']) ? $item['mktCap'] : 0,
                        'regularMarketPrice' => isset($item['price']) ? $item['price'] : 0,
                        'beta' => isset($item['beta']) ? $item['beta'] : 0,
                        'trailingPE' => isset($item['pe']) ? $item['pe'] : 0,
                        'dividendYield' => isset($item['lastDiv']) ? ($item['lastDiv'] / max(1, $item['price'])) : 0,
                        'fiftyTwoWeekHigh' => isset($item['range']) ? (float)substr(strrchr($item['range'], '-'), 1) : 0,
                        'fiftyTwoWeekLow' => isset($item['range']) ? (float)$item['range'] : 0,
                        'avgVolume' => isset($item['volAvg']) ? $item['volAvg'] : 0,
                        'sharesOutstanding' => isset($item['sharesOutstanding']) ? $item['sharesOutstanding'] : 0
                    );
                    if (alpha_insert_fundamental($conn, $ticker, $mapped, $today)) {
                        $fetched++;
                    }
                }
            }
        }

        $result['data']['fundamentals'] = array(
            'fetched' => $fetched,
            'total' => count($tickers),
            'method' => $method_used,
            'crumb_available' => ($_ALPHA_YAHOO_CRUMB !== '') ? 'yes' : 'no'
        );
    }
}

/* ================================================================
   ACTION: macro - Fetch VIX, Treasury yields, DXY, SPY
   ================================================================ */
if ($action === 'macro' || $action === 'all') {
    $macro_tickers = array(
        array('symbol' => '%5EVIX',     'name' => 'VIX',    'field' => 'vix_close'),
        array('symbol' => '%5EGSPC',    'name' => 'S&P 500','field' => 'spy_close'),
        array('symbol' => '%5ETNX',     'name' => '10Y Yield','field' => 'tnx_close'),
        array('symbol' => '%5EIRX',     'name' => '13W TBill','field' => 'two_yr_yield'),
        array('symbol' => 'DX-Y.NYB',  'name' => 'DXY',    'field' => 'dxy_close')
    );

    $macro_data = array(); // date => array of fields
    $macro_fetched = 0;

    foreach ($macro_tickers as $mt) {
        $url = 'https://query1.finance.yahoo.com/v8/finance/chart/' . $mt['symbol']
             . '?range=6mo&interval=1d&includeAdjustedClose=true';
        $data = alpha_yahoo_fetch($url, 3);

        if ($data !== false && isset($data['chart']['result'][0])) {
            $chart = $data['chart']['result'][0];
            $timestamps = isset($chart['timestamp']) ? $chart['timestamp'] : array();
            $closes = array();
            if (isset($chart['indicators']['quote'][0]['close'])) {
                $closes = $chart['indicators']['quote'][0]['close'];
            }

            for ($i = 0; $i < count($timestamps); $i++) {
                $dt = date('Y-m-d', $timestamps[$i]);
                if (!isset($closes[$i]) || $closes[$i] === null) continue;
                if (!isset($macro_data[$dt])) {
                    $macro_data[$dt] = array(
                        'vix_close' => 0, 'spy_close' => 0,
                        'tnx_close' => 0, 'two_yr_yield' => 0,
                        'dxy_close' => 0
                    );
                }
                $macro_data[$dt][$mt['field']] = round((float)$closes[$i], 4);
            }
            $macro_fetched++;
        } else {
            $result['errors'][] = 'Failed to fetch macro: ' . $mt['name'];
        }
        usleep(200000);
    }

    // Compute SPY moving averages and yield spread, then insert
    // First, get all SPY closes sorted by date for SMA calculation
    $spy_dates = array();
    foreach ($macro_data as $dt => $vals) {
        if ($vals['spy_close'] > 0) {
            $spy_dates[$dt] = $vals['spy_close'];
        }
    }
    ksort($spy_dates);
    $spy_arr = array_values($spy_dates);
    $spy_keys = array_keys($spy_dates);

    // Similarly for DXY
    $dxy_dates = array();
    foreach ($macro_data as $dt => $vals) {
        if ($vals['dxy_close'] > 0) {
            $dxy_dates[$dt] = $vals['dxy_close'];
        }
    }

    $macro_inserted = 0;
    foreach ($macro_data as $dt => $vals) {
        $safe_dt = $conn->real_escape_string($dt);
        $vix  = (float)$vals['vix_close'];
        $spy  = (float)$vals['spy_close'];
        $tnx  = (float)$vals['tnx_close'];
        $twoyr = (float)$vals['two_yr_yield'];
        $dxy  = (float)$vals['dxy_close'];
        $spread = round($tnx - $twoyr, 4);

        // Compute SPY SMA50 and SMA200
        $spy_idx = array_search($dt, $spy_keys);
        $spy_sma50 = 0;
        $spy_sma200 = 0;
        if ($spy_idx !== false) {
            // SMA50
            $start50 = max(0, $spy_idx - 49);
            $slice50 = array_slice($spy_arr, $start50, $spy_idx - $start50 + 1);
            if (count($slice50) >= 20) {
                $spy_sma50 = round(array_sum($slice50) / count($slice50), 4);
            }
            // SMA200 (use what we have, may be less than 200 with 6mo data)
            $start200 = max(0, $spy_idx - 199);
            $slice200 = array_slice($spy_arr, $start200, $spy_idx - $start200 + 1);
            if (count($slice200) >= 20) {
                $spy_sma200 = round(array_sum($slice200) / count($slice200), 4);
            }
        }

        // DXY SMA50
        $dxy_sma50 = 0;
        $dxy_vals_arr = array_values($dxy_dates);
        $dxy_keys_arr = array_keys($dxy_dates);
        $dxy_idx = array_search($dt, $dxy_keys_arr);
        if ($dxy_idx !== false) {
            $dxy_start = max(0, $dxy_idx - 49);
            $dxy_slice = array_slice($dxy_vals_arr, $dxy_start, $dxy_idx - $dxy_start + 1);
            if (count($dxy_slice) >= 10) {
                $dxy_sma50 = round(array_sum($dxy_slice) / count($dxy_slice), 4);
            }
        }

        // Determine regime
        $regime = 'unknown';
        $regime_score = 50;
        if ($spy > 0 && $vix > 0) {
            $spy_trend_up = ($spy_sma50 > 0 && $spy > $spy_sma50) ? true : false;
            if ($vix > 35) {
                $regime = 'extreme_vol';
                $regime_score = 10;
            } elseif ($vix > 25) {
                $regime = $spy_trend_up ? 'high_vol_bull' : 'high_vol_bear';
                $regime_score = $spy_trend_up ? 30 : 15;
            } elseif ($vix > 20) {
                $regime = $spy_trend_up ? 'moderate_bull' : 'moderate_bear';
                $regime_score = $spy_trend_up ? 55 : 35;
            } elseif ($vix > 16) {
                $regime = $spy_trend_up ? 'calm_bull' : 'calm_bear';
                $regime_score = $spy_trend_up ? 70 : 50;
            } else {
                $regime = $spy_trend_up ? 'goldilocks' : 'low_vol_bear';
                $regime_score = $spy_trend_up ? 85 : 60;
            }

            // Yield curve inversion warning
            if ($spread < -0.25) {
                $regime = $regime . '_inverted';
                $regime_score = max(5, $regime_score - 15);
            }
        }

        $safe_regime = $conn->real_escape_string($regime);
        $regime_detail_arr = array(
            'vix' => $vix, 'spy' => $spy, 'tnx' => $tnx,
            'yield_spread' => $spread, 'dxy' => $dxy,
            'spy_above_sma50' => ($spy > $spy_sma50 && $spy_sma50 > 0) ? 1 : 0,
            'dxy_above_sma50' => ($dxy > $dxy_sma50 && $dxy_sma50 > 0) ? 1 : 0
        );
        $safe_detail = $conn->real_escape_string(json_encode($regime_detail_arr));

        $sql = "INSERT INTO alpha_macro
                (trade_date, vix_close, spy_close, spy_sma50, spy_sma200, tnx_close,
                 two_yr_yield, yield_spread, dxy_close, dxy_sma50, regime, regime_score, regime_detail)
                VALUES ('$safe_dt', $vix, $spy, $spy_sma50, $spy_sma200, $tnx,
                        $twoyr, $spread, $dxy, $dxy_sma50, '$safe_regime', $regime_score, '$safe_detail')
                ON DUPLICATE KEY UPDATE
                    vix_close=$vix, spy_close=$spy, spy_sma50=$spy_sma50, spy_sma200=$spy_sma200,
                    tnx_close=$tnx, two_yr_yield=$twoyr, yield_spread=$spread,
                    dxy_close=$dxy, dxy_sma50=$dxy_sma50,
                    regime='$safe_regime', regime_score=$regime_score, regime_detail='$safe_detail'";
        if ($conn->query($sql)) {
            $macro_inserted++;
        }
    }

    $result['data']['macro'] = array('fetched' => $macro_fetched, 'days_inserted' => $macro_inserted);
}

/* ================================================================
   ACTION: earnings - Fetch earnings history from v10/quoteSummary
   ================================================================ */
if ($action === 'earnings' || $action === 'all') {
    $tickers = array();
    $res = $conn->query("SELECT ticker FROM alpha_universe WHERE active=1 ORDER BY ticker");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $tickers[] = $row['ticker'];
        }
    }

    // Batch: 10 per request
    $batch_size = 10;
    $start = ($batch - 1) * $batch_size;
    $batch_tickers = array_slice($tickers, $start, $batch_size);

    if (count($batch_tickers) === 0) {
        $result['data']['earnings'] = array('message' => 'No tickers in batch ' . $batch, 'total_batches' => ceil(count($tickers) / $batch_size));
    } else {
        $today = date('Y-m-d');
        $earnings_fetched = 0;

        foreach ($batch_tickers as $ticker) {
            $enc_ticker = urlencode($ticker);
            $url = 'https://query2.finance.yahoo.com/v10/finance/quoteSummary/' . $enc_ticker
                 . '?modules=earningsHistory,financialData';
            $data = alpha_yahoo_fetch($url, 2);

            if ($data !== false && isset($data['quoteSummary']['result'][0])) {
                $qr = $data['quoteSummary']['result'][0];
                $safe_ticker = $conn->real_escape_string($ticker);

                // Earnings history
                if (isset($qr['earningsHistory']['history'])) {
                    foreach ($qr['earningsHistory']['history'] as $eh) {
                        $qdate = '';
                        if (isset($eh['quarter']['fmt'])) {
                            $qdate = $eh['quarter']['fmt'];
                        } elseif (isset($eh['quarter']['raw'])) {
                            $qdate = date('Y-m-d', $eh['quarter']['raw']);
                        }
                        if ($qdate === '') continue;

                        $eps_a = alpha_safe_num($eh, 'epsActual');
                        $eps_e = alpha_safe_num($eh, 'epsEstimate');
                        $eps_s = alpha_safe_num($eh, 'epsDifference');
                        $surp  = alpha_safe_num($eh, 'surprisePercent');

                        $safe_qdate = $conn->real_escape_string($qdate);
                        $sql = "INSERT INTO alpha_earnings
                                (ticker, quarter_end, eps_actual, eps_estimate, eps_surprise, surprise_pct, fetch_date)
                                VALUES ('$safe_ticker', '$safe_qdate', $eps_a, $eps_e, $eps_s, $surp, '$today')
                                ON DUPLICATE KEY UPDATE
                                    eps_actual=$eps_a, eps_estimate=$eps_e, eps_surprise=$eps_s,
                                    surprise_pct=$surp, fetch_date='$today'";
                        $conn->query($sql);
                    }
                }

                // Financial data (detailed fundamentals)
                if (isset($qr['financialData'])) {
                    $fd = $qr['financialData'];
                    $roe = alpha_safe_num($fd, 'returnOnEquity');
                    $roa = alpha_safe_num($fd, 'returnOnAssets');
                    $gm  = alpha_safe_num($fd, 'grossMargins');
                    $om  = alpha_safe_num($fd, 'operatingMargins');
                    $pm  = alpha_safe_num($fd, 'profitMargins');
                    $rg  = alpha_safe_num($fd, 'revenueGrowth');
                    $eg  = alpha_safe_num($fd, 'earningsGrowth');
                    $td  = alpha_safe_num($fd, 'totalDebt');
                    $tc  = alpha_safe_num($fd, 'totalCash');
                    $dte = alpha_safe_num($fd, 'debtToEquity');
                    $cr  = alpha_safe_num($fd, 'currentRatio');
                    $fcf = alpha_safe_num($fd, 'freeCashflow');
                    $ocf = alpha_safe_num($fd, 'operatingCashflow');

                    // Update fundamentals table with detailed data
                    $sql = "UPDATE alpha_fundamentals SET
                                return_on_equity=$roe, return_on_assets=$roa,
                                gross_margins=$gm, operating_margins=$om, profit_margins=$pm,
                                revenue_growth=$rg, earnings_growth=$eg,
                                total_debt=$td, total_cash=$tc, debt_to_equity=$dte,
                                current_ratio=$cr, free_cashflow=$fcf, operating_cashflow=$ocf
                            WHERE ticker='$safe_ticker' AND fetch_date='$today'";
                    $conn->query($sql);
                }

                $earnings_fetched++;
            } else {
                $result['errors'][] = 'v10/quoteSummary failed: ' . $ticker;
            }

            usleep(300000); // 300ms between calls
        }

        $result['data']['earnings'] = array(
            'batch' => $batch,
            'fetched' => $earnings_fetched,
            'batch_size' => count($batch_tickers),
            'total_batches' => ceil(count($tickers) / $batch_size)
        );
    }
}

/* ================================================================
   ACTION: prices - Ensure daily_prices are current for universe
   ================================================================ */
if ($action === 'prices' || $action === 'all') {
    $tickers = array();
    $res = $conn->query("SELECT ticker FROM alpha_universe WHERE active=1 ORDER BY ticker");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $tickers[] = $row['ticker'];
        }
    }

    // Check which tickers need price updates (missing last 5 trading days)
    $cutoff = date('Y-m-d', strtotime('-7 days'));
    $need_update = array();
    foreach ($tickers as $t) {
        $st = $conn->real_escape_string($t);
        $chk = $conn->query("SELECT MAX(trade_date) as last_date FROM daily_prices WHERE ticker='$st'");
        $needs = true;
        if ($chk && $row = $chk->fetch_assoc()) {
            if ($row['last_date'] !== null && $row['last_date'] >= $cutoff) {
                $needs = false;
            }
        }
        if ($needs) {
            $need_update[] = $t;
        }
    }

    // Batch: 10 per request
    $batch_size = 10;
    $start = ($batch - 1) * $batch_size;
    $batch_tickers = array_slice($need_update, $start, $batch_size);

    $prices_fetched = 0;
    foreach ($batch_tickers as $ticker) {
        $enc = urlencode($ticker);
        $url = 'https://query1.finance.yahoo.com/v8/finance/chart/' . $enc
             . '?range=1y&interval=1d&includeAdjustedClose=true';
        $data = alpha_yahoo_fetch($url, 3);

        if ($data !== false && isset($data['chart']['result'][0])) {
            $chart = $data['chart']['result'][0];
            $ts = isset($chart['timestamp']) ? $chart['timestamp'] : array();
            $quote = isset($chart['indicators']['quote'][0]) ? $chart['indicators']['quote'][0] : array();
            $adjc = isset($chart['indicators']['adjclose'][0]['adjclose'])
                  ? $chart['indicators']['adjclose'][0]['adjclose'] : array();

            $safe_ticker = $conn->real_escape_string($ticker);
            $inserted = 0;

            for ($i = 0; $i < count($ts); $i++) {
                $dt = date('Y-m-d', $ts[$i]);
                $o = isset($quote['open'][$i]) ? (float)$quote['open'][$i] : 0;
                $h = isset($quote['high'][$i]) ? (float)$quote['high'][$i] : 0;
                $l = isset($quote['low'][$i]) ? (float)$quote['low'][$i] : 0;
                $c = isset($quote['close'][$i]) ? (float)$quote['close'][$i] : 0;
                $v = isset($quote['volume'][$i]) ? (int)$quote['volume'][$i] : 0;
                $ac = isset($adjc[$i]) ? (float)$adjc[$i] : $c;
                if ($c <= 0) continue;

                $safe_dt = $conn->real_escape_string($dt);
                $sql = "INSERT INTO daily_prices (ticker, trade_date, open_price, high_price, low_price, close_price, adj_close, volume)
                        VALUES ('$safe_ticker','$safe_dt',$o,$h,$l,$c,$ac,$v)
                        ON DUPLICATE KEY UPDATE open_price=$o, high_price=$h, low_price=$l, close_price=$c, adj_close=$ac, volume=$v";
                if ($conn->query($sql)) {
                    $inserted++;
                }
            }
            $prices_fetched++;
        } else {
            // Fallback: Stooq
            $d2 = date('Ymd');
            $d1 = date('Ymd', strtotime('-1 year'));
            $surl = 'https://stooq.com/q/d/l/?s=' . urlencode($ticker) . '.US&d1=' . $d1 . '&d2=' . $d2 . '&i=d';
            $csv = @file_get_contents($surl);
            if ($csv !== false && strlen($csv) > 50) {
                $lines = explode("\n", $csv);
                $safe_ticker = $conn->real_escape_string($ticker);
                foreach ($lines as $li => $line) {
                    if ($li === 0) continue; // header
                    $cols = explode(',', trim($line));
                    if (count($cols) < 5) continue;
                    $dt = $cols[0];
                    $o = (float)$cols[1]; $h = (float)$cols[2]; $l = (float)$cols[3]; $c = (float)$cols[4];
                    $v = isset($cols[5]) ? (int)$cols[5] : 0;
                    if ($c <= 0) continue;
                    $safe_dt = $conn->real_escape_string($dt);
                    $conn->query("INSERT INTO daily_prices (ticker, trade_date, open_price, high_price, low_price, close_price, adj_close, volume)
                                  VALUES ('$safe_ticker','$safe_dt',$o,$h,$l,$c,$c,$v)
                                  ON DUPLICATE KEY UPDATE open_price=$o, high_price=$h, low_price=$l, close_price=$c, volume=$v");
                }
                $prices_fetched++;
            } else {
                $result['errors'][] = 'Price fetch failed: ' . $ticker;
            }
        }
        usleep(500000); // 500ms between tickers
    }

    $result['data']['prices'] = array(
        'batch' => $batch,
        'fetched' => $prices_fetched,
        'needed_update' => count($need_update),
        'batch_size' => count($batch_tickers),
        'total_batches' => ceil(count($need_update) / $batch_size)
    );
}

/* ================================================================
   ACTION: prices_check - Check which tickers need updates
   ================================================================ */
if ($action === 'prices_check') {
    $tickers = array();
    $res = $conn->query("SELECT ticker FROM alpha_universe WHERE active=1 ORDER BY ticker");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $tickers[] = $row['ticker'];
        }
    }
    $cutoff = date('Y-m-d', strtotime('-7 days'));
    $need = array();
    $current = array();
    foreach ($tickers as $t) {
        $st = $conn->real_escape_string($t);
        $chk = $conn->query("SELECT MAX(trade_date) as last_date FROM daily_prices WHERE ticker='$st'");
        if ($chk && $row = $chk->fetch_assoc()) {
            if ($row['last_date'] !== null && $row['last_date'] >= $cutoff) {
                $current[] = $t;
            } else {
                $need[] = array('ticker' => $t, 'last_date' => $row['last_date']);
            }
        } else {
            $need[] = array('ticker' => $t, 'last_date' => null);
        }
    }
    $result['data'] = array(
        'need_update' => $need,
        'current' => $current,
        'total_need' => count($need),
        'total_current' => count($current),
        'batches_needed' => ceil(count($need) / 10)
    );
}

// Log this fetch action
if ($action !== 'prices_check') {
    $now = date('Y-m-d H:i:s');
    $safe_action = $conn->real_escape_string($action);
    $err_count = count($result['errors']);
    $detail = $conn->real_escape_string(json_encode($result['data']));
    $conn->query("INSERT INTO alpha_refresh_log (refresh_date, step, status, details, errors_count)
                  VALUES ('$now', 'fetch_$safe_action', 'completed', '$detail', $err_count)");
}

echo json_encode($result);
$conn->close();
?>
