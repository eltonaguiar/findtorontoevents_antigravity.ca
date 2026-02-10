<?php
/**
 * sec_edgar.php — SEC EDGAR data fetcher for insider trades (Form 4)
 * and institutional holdings (13F filings).
 * PHP 5.2 compatible — no closures, no short arrays, no http_response_code().
 *
 * Actions:
 *   ?action=fetch_form4&key=livetrader2026     — Admin: fetch Form 4 insider trades
 *   ?action=fetch_13f&key=livetrader2026       — Admin: fetch 13F institutional holdings
 *   ?action=insider_activity&ticker=AAPL       — Public: recent insider trades for ticker
 *   ?action=insider_clusters                   — Public: stocks with 3+ insiders buying
 *   ?action=fund_holdings&ticker=AAPL          — Public: which tracked funds hold a stock
 *   ?action=new_positions                      — Public: new positions opened by funds
 *   ?action=conviction_picks                   — Public: stocks held by 3+ funds
 */

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/goldmine_schema.php';

// Ensure schema (lightweight IF NOT EXISTS)
_gm_ensure_schema($conn);

$action = isset($_GET['action']) ? $_GET['action'] : '';
$key    = isset($_GET['key'])    ? $_GET['key']    : '';
$admin  = ($key === 'livetrader2026');
$now    = date('Y-m-d H:i:s');
$today  = date('Y-m-d');

// ── Stock universe ──
$TICKERS = array('AAPL','MSFT','GOOGL','AMZN','NVDA','META','JPM','WMT','XOM','NFLX','JNJ','BAC',
    'GS','TSLA','V','MA','DIS','COST','PG','UNH','HD','CRM','INTC','AMD','PYPL','SQ','SHOP','ABNB');

// ── Top funds to track (13F) ──
$FUNDS = array(
    array('cik' => '0001067983', 'name' => 'Berkshire Hathaway'),
    array('cik' => '0001336528', 'name' => 'Bridgewater Associates'),
    array('cik' => '0001649339', 'name' => 'Citadel Advisors'),
    array('cik' => '0001061768', 'name' => 'Renaissance Technologies'),
    array('cik' => '0001350694', 'name' => 'Two Sigma Investments'),
    array('cik' => '0001364742', 'name' => 'DE Shaw'),
    array('cik' => '0001037389', 'name' => 'Soros Fund Management'),
    array('cik' => '0001510524', 'name' => 'Appaloosa Management'),
    array('cik' => '0001336326', 'name' => 'Baupost Group'),
    array('cik' => '0001279708', 'name' => 'Viking Global')
);

// ── Cache directory ──
$SEC_CACHE_DIR = dirname(__FILE__) . '/cache/';
if (!is_dir($SEC_CACHE_DIR)) { @mkdir($SEC_CACHE_DIR, 0755, true); }

// ── Cache helpers ──
function _sec_cache_get($cache_key, $ttl_sec) {
    global $SEC_CACHE_DIR;
    $f = $SEC_CACHE_DIR . 'sec_' . md5($cache_key) . '.json';
    if (file_exists($f) && (time() - filemtime($f)) < $ttl_sec) {
        $d = @file_get_contents($f);
        if ($d !== false) return json_decode($d, true);
    }
    return false;
}

function _sec_cache_set($cache_key, $data) {
    global $SEC_CACHE_DIR;
    $f = $SEC_CACHE_DIR . 'sec_' . md5($cache_key) . '.json';
    @file_put_contents($f, json_encode($data));
}

// ── HTTP helper with SEC User-Agent ──
function _sec_http_get($url) {
    $ua = 'GoldmineTracker contact@findtorontoevents.ca';
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 20);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'User-Agent: ' . $ua,
            'Accept: application/json, application/xml, text/xml, */*',
            'Accept-Encoding: gzip'
        ));
        curl_setopt($ch, CURLOPT_USERAGENT, $ua);
        curl_setopt($ch, CURLOPT_ENCODING, 'gzip');
        $resp = curl_exec($ch);
        curl_close($ch);
        if ($resp !== false) return $resp;
    }
    $ctx = stream_context_create(array('http' => array(
        'timeout' => 20,
        'user_agent' => $ua,
        'header' => "Accept: application/json, application/xml, text/xml, */*\r\n"
    )));
    return @file_get_contents($url, false, $ctx);
}

// ── Escape helper ──
function _sec_esc($val) {
    global $conn;
    return $conn->real_escape_string($val);
}

// ── Get ticker-to-CIK mapping (cached 24hr) ──
function _sec_get_cik_map() {
    $cached = _sec_cache_get('company_tickers_json', 86400);
    if ($cached) return $cached;

    $raw = _sec_http_get('https://www.sec.gov/files/company_tickers.json');
    if (!$raw) return array();

    $data = json_decode($raw, true);
    if (!$data) return array();

    // Build ticker => CIK (zero-padded to 10 digits)
    $map = array();
    foreach ($data as $entry) {
        if (isset($entry['ticker']) && isset($entry['cik_str'])) {
            $ticker = strtoupper($entry['ticker']);
            $cik = str_pad($entry['cik_str'], 10, '0', STR_PAD_LEFT);
            $map[$ticker] = $cik;
        }
    }

    _sec_cache_set('company_tickers_json', $map);
    return $map;
}

// ── Build CUSIP-to-ticker map from company_tickers.json (best effort) ──
// Note: company_tickers.json does not contain CUSIPs.
// We build a name-to-ticker map from 13F issuer names for approximate matching.
function _sec_get_cusip_ticker_map() {
    // This uses a hardcoded common CUSIP map for our tracked universe
    return array(
        '037833100' => 'AAPL',  // Apple
        '594918104' => 'MSFT',  // Microsoft
        '02079K305' => 'GOOGL', // Alphabet Class A
        '02079K107' => 'GOOG',  // Alphabet Class C
        '023135106' => 'AMZN',  // Amazon
        '67066G104' => 'NVDA',  // NVIDIA
        '30303M102' => 'META',  // Meta Platforms
        '46625H100' => 'JPM',   // JPMorgan
        '931142103' => 'WMT',   // Walmart
        '30231G102' => 'XOM',   // ExxonMobil
        '64110L106' => 'NFLX',  // Netflix
        '478160104' => 'JNJ',   // Johnson & Johnson
        '060505104' => 'BAC',   // Bank of America
        '38141G104' => 'GS',    // Goldman Sachs
        '88160R101' => 'TSLA',  // Tesla
        '92826C839' => 'V',     // Visa
        '57636Q104' => 'MA',    // Mastercard
        '254687106' => 'DIS',   // Disney
        '22160K105' => 'COST',  // Costco
        '742718109' => 'PG',    // Procter & Gamble
        '91324P102' => 'UNH',   // UnitedHealth
        '437076102' => 'HD',    // Home Depot
        '79466L302' => 'CRM',   // Salesforce
        '458140100' => 'INTC',  // Intel
        '007903107' => 'AMD',   // AMD
        '70450Y103' => 'PYPL',  // PayPal
        '852234103' => 'SQ',    // Block (Square)
        '82509L107' => 'SHOP',  // Shopify
        '00917P104' => 'ABNB'   // Airbnb
    );
}

// ── Parse Form 4 XML ──
function _sec_parse_form4_xml($xml_str, $ticker, $cik) {
    $trades = array();
    // Suppress warnings for malformed XML
    $prev = libxml_use_internal_errors(true);
    $xml = @simplexml_load_string($xml_str);
    libxml_use_internal_errors($prev);
    if (!$xml) return $trades;

    // Filer info
    $filer_name = '';
    $filer_title = '';
    $is_director = 0;
    $is_officer = 0;
    $is_ten_pct = 0;

    // reportingOwner
    if (isset($xml->reportingOwner)) {
        $owner = $xml->reportingOwner;
        if (isset($owner->reportingOwnerId->rptOwnerName)) {
            $filer_name = (string)$owner->reportingOwnerId->rptOwnerName;
        }
        if (isset($owner->reportingOwnerRelationship)) {
            $rel = $owner->reportingOwnerRelationship;
            if (isset($rel->isDirector) && ((string)$rel->isDirector === '1' || strtolower((string)$rel->isDirector) === 'true')) {
                $is_director = 1;
            }
            if (isset($rel->isOfficer) && ((string)$rel->isOfficer === '1' || strtolower((string)$rel->isOfficer) === 'true')) {
                $is_officer = 1;
            }
            if (isset($rel->officerTitle)) {
                $filer_title = (string)$rel->officerTitle;
            }
            if (isset($rel->isTenPercentOwner) && ((string)$rel->isTenPercentOwner === '1' || strtolower((string)$rel->isTenPercentOwner) === 'true')) {
                $is_ten_pct = 1;
            }
        }
    }

    // Non-derivative transactions
    if (isset($xml->nonDerivativeTable->nonDerivativeTransaction)) {
        foreach ($xml->nonDerivativeTable->nonDerivativeTransaction as $txn) {
            $trade = _sec_extract_transaction($txn, $ticker, $cik, $filer_name, $filer_title,
                $is_director, $is_officer, $is_ten_pct);
            if ($trade) $trades[] = $trade;
        }
    }

    // Derivative transactions
    if (isset($xml->derivativeTable->derivativeTransaction)) {
        foreach ($xml->derivativeTable->derivativeTransaction as $txn) {
            $trade = _sec_extract_transaction($txn, $ticker, $cik, $filer_name, $filer_title,
                $is_director, $is_officer, $is_ten_pct);
            if ($trade) $trades[] = $trade;
        }
    }

    return $trades;
}

// ── Extract a single transaction from XML node ──
function _sec_extract_transaction($txn, $ticker, $cik, $filer_name, $filer_title,
    $is_director, $is_officer, $is_ten_pct) {

    $txn_date = '';
    if (isset($txn->transactionDate->value)) {
        $txn_date = (string)$txn->transactionDate->value;
    }
    if (!$txn_date) return null;

    // Transaction coding: A=Award, P=Purchase, S=Sale, M=Exercise, etc.
    $txn_code = '';
    if (isset($txn->transactionCoding->transactionCode)) {
        $txn_code = strtoupper((string)$txn->transactionCoding->transactionCode);
    }

    // We mainly care about P (purchase) and S (sale on open market)
    $txn_type = '';
    if ($txn_code === 'P') {
        $txn_type = 'P';
    } elseif ($txn_code === 'S') {
        $txn_type = 'S';
    } elseif ($txn_code === 'A') {
        $txn_type = 'A'; // Award/grant
    } elseif ($txn_code === 'M') {
        $txn_type = 'M'; // Option exercise
    } elseif ($txn_code === 'F') {
        $txn_type = 'F'; // Tax withholding
    } elseif ($txn_code === 'G') {
        $txn_type = 'G'; // Gift
    } else {
        $txn_type = $txn_code ? $txn_code : 'U'; // Unknown
    }

    $shares = 0;
    if (isset($txn->transactionAmounts->transactionShares->value)) {
        $shares = floatval((string)$txn->transactionAmounts->transactionShares->value);
    }

    $price = 0;
    if (isset($txn->transactionAmounts->transactionPricePerShare->value)) {
        $price = floatval((string)$txn->transactionAmounts->transactionPricePerShare->value);
    }

    $shares_after = 0;
    if (isset($txn->postTransactionAmounts->sharesOwnedFollowingTransaction->value)) {
        $shares_after = floatval((string)$txn->postTransactionAmounts->sharesOwnedFollowingTransaction->value);
    }

    $total_value = $shares * $price;

    return array(
        'ticker'             => $ticker,
        'cik'                => $cik,
        'filer_name'         => $filer_name,
        'filer_title'        => $filer_title,
        'transaction_date'   => $txn_date,
        'transaction_type'   => $txn_type,
        'shares'             => $shares,
        'price_per_share'    => $price,
        'total_value'        => $total_value,
        'shares_owned_after' => $shares_after,
        'is_director'        => $is_director,
        'is_officer'         => $is_officer,
        'is_ten_pct_owner'   => $is_ten_pct
    );
}

// ── Insert insider trade with dedup ──
function _sec_insert_insider_trade($trade, $accession, $filing_date) {
    global $conn, $now;

    $check = $conn->query("SELECT id FROM gm_sec_insider_trades
        WHERE accession_number = '" . _sec_esc($accession) . "'
        AND ticker = '" . _sec_esc($trade['ticker']) . "'
        AND transaction_type = '" . _sec_esc($trade['transaction_type']) . "'
        AND transaction_date = '" . _sec_esc($trade['transaction_date']) . "'
        LIMIT 1");
    if ($check && $check->num_rows > 0) return false; // already exists

    $sql = "INSERT INTO gm_sec_insider_trades
        (cik, ticker, filer_name, filer_title, transaction_date, transaction_type,
         shares, price_per_share, total_value, shares_owned_after, filing_date,
         accession_number, is_director, is_officer, is_ten_pct_owner, created_at)
        VALUES (
            '" . _sec_esc($trade['cik']) . "',
            '" . _sec_esc($trade['ticker']) . "',
            '" . _sec_esc($trade['filer_name']) . "',
            '" . _sec_esc($trade['filer_title']) . "',
            '" . _sec_esc($trade['transaction_date']) . "',
            '" . _sec_esc($trade['transaction_type']) . "',
            " . floatval($trade['shares']) . ",
            " . floatval($trade['price_per_share']) . ",
            " . floatval($trade['total_value']) . ",
            " . floatval($trade['shares_owned_after']) . ",
            '" . _sec_esc($filing_date) . "',
            '" . _sec_esc($accession) . "',
            " . intval($trade['is_director']) . ",
            " . intval($trade['is_officer']) . ",
            " . intval($trade['is_ten_pct_owner']) . ",
            '" . _sec_esc($now) . "'
        )";
    $conn->query($sql);
    return true;
}

// ════════════════════════════════════════════════════════════════
//  ACTION: fetch_form4 (admin)
// ════════════════════════════════════════════════════════════════
if ($action === 'fetch_form4') {
    if (!$admin) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
        exit;
    }

    $cik_map = _sec_get_cik_map();
    if (empty($cik_map)) {
        echo json_encode(array('ok' => false, 'error' => 'Failed to fetch CIK mapping'));
        exit;
    }

    // Optional: batch param to process subset (0-based batch index, 5 tickers per batch)
    $batch = isset($_GET['batch']) ? intval($_GET['batch']) : -1;
    $batch_size = 5;

    $tickers_to_process = $TICKERS;
    if ($batch >= 0) {
        $offset = $batch * $batch_size;
        $tickers_to_process = array_slice($TICKERS, $offset, $batch_size);
    }

    $stats = array(
        'tickers_processed' => 0,
        'filings_found'     => 0,
        'trades_inserted'   => 0,
        'trades_skipped'    => 0,
        'errors'            => array()
    );

    foreach ($tickers_to_process as $ticker) {
        if (!isset($cik_map[$ticker])) {
            $stats['errors'][] = $ticker . ': CIK not found';
            continue;
        }

        $cik = $cik_map[$ticker];
        $stats['tickers_processed']++;

        // Fetch company submissions
        $url = 'https://data.sec.gov/submissions/CIK' . $cik . '.json';
        usleep(150000); // rate limit
        $raw = _sec_http_get($url);
        if (!$raw) {
            $stats['errors'][] = $ticker . ': Failed to fetch submissions';
            continue;
        }

        $sub = json_decode($raw, true);
        if (!$sub || !isset($sub['filings']['recent'])) {
            $stats['errors'][] = $ticker . ': Invalid submissions response';
            continue;
        }

        $recent = $sub['filings']['recent'];
        $forms = isset($recent['form']) ? $recent['form'] : array();
        $accessions = isset($recent['accessionNumber']) ? $recent['accessionNumber'] : array();
        $dates = isset($recent['filingDate']) ? $recent['filingDate'] : array();
        $primary_docs = isset($recent['primaryDocument']) ? $recent['primaryDocument'] : array();

        // 30-day lookback for Form 4
        $cutoff = date('Y-m-d', strtotime('-30 days'));
        $form4_count = 0;
        $max_form4 = 10; // limit per ticker

        for ($i = 0; $i < count($forms); $i++) {
            if ($form4_count >= $max_form4) break;
            if ($forms[$i] !== '4') continue;
            if (isset($dates[$i]) && $dates[$i] < $cutoff) continue;

            $accession = isset($accessions[$i]) ? $accessions[$i] : '';
            $filing_date = isset($dates[$i]) ? $dates[$i] : $today;
            $primary_doc = isset($primary_docs[$i]) ? $primary_docs[$i] : '';

            if (!$accession || !$primary_doc) continue;

            $stats['filings_found']++;
            $form4_count++;

            // Build URL: accession dashes removed for path
            $acc_nodash = str_replace('-', '', $accession);
            $cik_num = ltrim($cik, '0');
            if (!$cik_num) $cik_num = '0';
            $xml_url = 'https://www.sec.gov/Archives/edgar/data/' . $cik_num . '/' . $acc_nodash . '/' . $primary_doc;

            usleep(150000); // rate limit
            $xml_raw = _sec_http_get($xml_url);
            if (!$xml_raw) {
                $stats['errors'][] = $ticker . ': Failed to fetch Form 4 XML ' . $accession;
                continue;
            }

            $trades = _sec_parse_form4_xml($xml_raw, $ticker, $cik);
            foreach ($trades as $trade) {
                $inserted = _sec_insert_insider_trade($trade, $accession, $filing_date);
                if ($inserted) {
                    $stats['trades_inserted']++;
                } else {
                    $stats['trades_skipped']++;
                }
            }
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'fetch_form4', 'stats' => $stats));
    exit;
}

// ════════════════════════════════════════════════════════════════
//  ACTION: fetch_13f (admin)
// ════════════════════════════════════════════════════════════════
if ($action === 'fetch_13f') {
    if (!$admin) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
        exit;
    }

    $cusip_ticker_map = _sec_get_cusip_ticker_map();

    $stats = array(
        'funds_processed'    => 0,
        'filings_found'      => 0,
        'holdings_inserted'  => 0,
        'holdings_skipped'   => 0,
        'errors'             => array()
    );

    foreach ($FUNDS as $fund) {
        $fund_cik = $fund['cik'];
        $fund_name = $fund['name'];

        $stats['funds_processed']++;

        // Fetch fund submissions
        $url = 'https://data.sec.gov/submissions/CIK' . $fund_cik . '.json';
        usleep(150000); // rate limit
        $raw = _sec_http_get($url);
        if (!$raw) {
            $stats['errors'][] = $fund_name . ': Failed to fetch submissions';
            continue;
        }

        $sub = json_decode($raw, true);
        if (!$sub || !isset($sub['filings']['recent'])) {
            $stats['errors'][] = $fund_name . ': Invalid submissions response';
            continue;
        }

        $recent = $sub['filings']['recent'];
        $forms = isset($recent['form']) ? $recent['form'] : array();
        $accessions = isset($recent['accessionNumber']) ? $recent['accessionNumber'] : array();
        $dates = isset($recent['filingDate']) ? $recent['filingDate'] : array();
        $primary_docs = isset($recent['primaryDocument']) ? $recent['primaryDocument'] : array();

        // Find latest 13F-HR
        $found_13f = false;
        $filing_accession = '';
        $filing_date = '';
        $filing_doc = '';

        for ($i = 0; $i < count($forms); $i++) {
            if ($forms[$i] === '13F-HR' || $forms[$i] === '13F-HR/A') {
                $filing_accession = isset($accessions[$i]) ? $accessions[$i] : '';
                $filing_date = isset($dates[$i]) ? $dates[$i] : '';
                $filing_doc = isset($primary_docs[$i]) ? $primary_docs[$i] : '';
                $found_13f = true;
                break; // most recent first
            }
        }

        if (!$found_13f || !$filing_accession) {
            $stats['errors'][] = $fund_name . ': No 13F-HR filing found';
            continue;
        }

        $stats['filings_found']++;

        // Derive filing quarter from filing date (e.g., filed 2026-02-14 => quarter Q4-2025)
        // 13F covers the prior quarter-end
        $filing_quarter = _sec_derive_quarter($filing_date);

        // Build URL for the filing index to find the information table
        $acc_nodash = str_replace('-', '', $filing_accession);
        $cik_num = ltrim($fund_cik, '0');
        if (!$cik_num) $cik_num = '0';

        // Try to get the filing index to find the infotable XML
        $index_url = 'https://www.sec.gov/Archives/edgar/data/' . $cik_num . '/' . $acc_nodash . '/';
        usleep(150000);

        // The primary doc might be the main filing; we need the information table
        // Try common names: infotable.xml, primary_doc.xml, or parse the index
        $infotable_url = '';

        // Strategy 1: Try the primary doc directly if it ends in .xml
        if (preg_match('/\.xml$/i', $filing_doc)) {
            $infotable_url = $index_url . $filing_doc;
        }

        // Strategy 2: Try common infotable filenames
        if (!$infotable_url) {
            $common_names = array('infotable.xml', 'InfoTable.xml', 'INFOTABLE.XML',
                'information_table.xml', 'primary_doc.xml');
            foreach ($common_names as $try_name) {
                $try_url = $index_url . $try_name;
                usleep(150000);
                $try_raw = _sec_http_get($try_url);
                if ($try_raw && strlen($try_raw) > 200 && strpos($try_raw, '<') !== false) {
                    $infotable_url = $try_url;
                    break;
                }
            }
        }

        // Strategy 3: Parse the filing index HTML to find infotable link
        if (!$infotable_url) {
            usleep(150000);
            $idx_raw = _sec_http_get($index_url);
            if ($idx_raw) {
                // Look for links to XML files containing "infotable" or "information"
                if (preg_match_all('/href="([^"]*(?:info|table)[^"]*\.xml)"/i', $idx_raw, $matches)) {
                    if (isset($matches[1][0])) {
                        $infotable_url = $index_url . $matches[1][0];
                    }
                }
            }
        }

        if (!$infotable_url) {
            // Fallback: use primary document
            $infotable_url = $index_url . $filing_doc;
        }

        usleep(150000);
        $xml_raw = _sec_http_get($infotable_url);
        if (!$xml_raw) {
            $stats['errors'][] = $fund_name . ': Failed to fetch 13F infotable XML';
            continue;
        }

        $holdings = _sec_parse_13f_xml($xml_raw, $fund_cik, $fund_name, $filing_quarter, $filing_date, $cusip_ticker_map);

        foreach ($holdings as $holding) {
            $inserted = _sec_insert_13f_holding($holding);
            if ($inserted) {
                $stats['holdings_inserted']++;
            } else {
                $stats['holdings_skipped']++;
            }
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'fetch_13f', 'stats' => $stats));
    exit;
}

// ── Derive quarter from filing date ──
// 13F filings cover the prior quarter end.
// Filed in Feb => Q4 prior year, May => Q1, Aug => Q2, Nov => Q3
function _sec_derive_quarter($filing_date) {
    $m = intval(date('m', strtotime($filing_date)));
    $y = intval(date('Y', strtotime($filing_date)));
    if ($m >= 1 && $m <= 3) {
        return 'Q4-' . ($y - 1);
    } elseif ($m >= 4 && $m <= 6) {
        return 'Q1-' . $y;
    } elseif ($m >= 7 && $m <= 9) {
        return 'Q2-' . $y;
    } else {
        return 'Q3-' . $y;
    }
}

// ── Parse 13F infotable XML ──
function _sec_parse_13f_xml($xml_str, $fund_cik, $fund_name, $filing_quarter, $filing_date, $cusip_ticker_map) {
    $holdings = array();

    $prev = libxml_use_internal_errors(true);
    // Remove namespace declarations that can confuse simplexml
    $xml_str = preg_replace('/xmlns[^=]*="[^"]*"/', '', $xml_str);
    $xml_str = preg_replace('/<([a-zA-Z0-9]+):/', '<', $xml_str);
    $xml_str = preg_replace('/<\/([a-zA-Z0-9]+):/', '</', $xml_str);
    $xml = @simplexml_load_string($xml_str);
    libxml_use_internal_errors($prev);
    if (!$xml) return $holdings;

    // 13F infotable has <infoTable> entries
    $entries = array();

    // Try different XML structures
    if (isset($xml->infoTable)) {
        $entries = $xml->infoTable;
    } elseif (isset($xml->informationTable->infoTable)) {
        $entries = $xml->informationTable->infoTable;
    } else {
        // Try xpath-like direct children
        $children = $xml->children();
        foreach ($children as $child) {
            $name = strtolower($child->getName());
            if ($name === 'infotable') {
                $entries[] = $child;
            }
        }
    }

    foreach ($entries as $entry) {
        $cusip = '';
        $issuer = '';
        $value = 0;
        $shares = 0;

        if (isset($entry->cusip)) $cusip = trim((string)$entry->cusip);
        if (isset($entry->nameOfIssuer)) $issuer = trim((string)$entry->nameOfIssuer);
        if (isset($entry->value)) $value = intval((string)$entry->value);
        if (isset($entry->shrsOrPrnAmt->sshPrnamt)) {
            $shares = intval((string)$entry->shrsOrPrnAmt->sshPrnamt);
        }

        if (!$cusip) continue;

        // Map CUSIP to ticker
        $ticker = '';
        if (isset($cusip_ticker_map[$cusip])) {
            $ticker = $cusip_ticker_map[$cusip];
        } else {
            // Try to guess from issuer name
            $ticker = _sec_guess_ticker_from_name($issuer);
        }

        $holdings[] = array(
            'cik'             => $fund_cik,
            'fund_name'       => $fund_name,
            'ticker'          => $ticker,
            'cusip'           => $cusip,
            'name_of_issuer'  => $issuer,
            'value_thousands' => $value,
            'shares'          => $shares,
            'filing_quarter'  => $filing_quarter,
            'filing_date'     => $filing_date
        );
    }

    return $holdings;
}

// ── Guess ticker from issuer name (rough heuristic) ──
function _sec_guess_ticker_from_name($issuer_name) {
    $name = strtoupper($issuer_name);
    $map = array(
        'APPLE' => 'AAPL', 'MICROSOFT' => 'MSFT', 'ALPHABET' => 'GOOGL',
        'AMAZON' => 'AMZN', 'NVIDIA' => 'NVDA', 'META PLATFORMS' => 'META',
        'JPMORGAN' => 'JPM', 'WALMART' => 'WMT', 'EXXON' => 'XOM',
        'NETFLIX' => 'NFLX', 'JOHNSON' => 'JNJ', 'BANK OF AMERICA' => 'BAC',
        'BANK OF AMER' => 'BAC', 'GOLDMAN' => 'GS', 'TESLA' => 'TSLA',
        'VISA' => 'V', 'MASTERCARD' => 'MA', 'DISNEY' => 'DIS',
        'COSTCO' => 'COST', 'PROCTER' => 'PG', 'UNITEDHEALTH' => 'UNH',
        'HOME DEPOT' => 'HD', 'SALESFORCE' => 'CRM', 'INTEL' => 'INTC',
        'ADVANCED MICRO' => 'AMD', 'PAYPAL' => 'PYPL', 'BLOCK INC' => 'SQ',
        'SHOPIFY' => 'SHOP', 'AIRBNB' => 'ABNB'
    );
    foreach ($map as $keyword => $ticker) {
        if (strpos($name, $keyword) !== false) return $ticker;
    }
    return '';
}

// ── Insert 13F holding with dedup + change detection ──
function _sec_insert_13f_holding($holding) {
    global $conn, $now;

    $fund_cik = $holding['cik'];
    $cusip = $holding['cusip'];
    $quarter = $holding['filing_quarter'];

    // Check for existing entry
    $check = $conn->query("SELECT id FROM gm_sec_13f_holdings
        WHERE cik = '" . _sec_esc($fund_cik) . "'
        AND cusip = '" . _sec_esc($cusip) . "'
        AND filing_quarter = '" . _sec_esc($quarter) . "'
        LIMIT 1");
    if ($check && $check->num_rows > 0) return false; // already exists

    // Find previous quarter holdings for change detection
    $prev_shares = 0;
    $change_type = 'new';
    $change_pct = 0;

    $prev_q = _sec_prev_quarter($quarter);
    $prev_r = $conn->query("SELECT shares FROM gm_sec_13f_holdings
        WHERE cik = '" . _sec_esc($fund_cik) . "'
        AND cusip = '" . _sec_esc($cusip) . "'
        AND filing_quarter = '" . _sec_esc($prev_q) . "'
        LIMIT 1");
    if ($prev_r && ($prev_row = $prev_r->fetch_assoc())) {
        $prev_shares = intval($prev_row['shares']);
        $cur_shares = intval($holding['shares']);

        if ($prev_shares == 0 && $cur_shares > 0) {
            $change_type = 'new';
        } elseif ($cur_shares == 0 && $prev_shares > 0) {
            $change_type = 'sold_all';
        } elseif ($cur_shares > $prev_shares) {
            $change_type = 'increased';
            $change_pct = ($prev_shares > 0) ? round((($cur_shares - $prev_shares) / $prev_shares) * 100, 2) : 100;
        } elseif ($cur_shares < $prev_shares) {
            $change_type = 'decreased';
            $change_pct = ($prev_shares > 0) ? round((($cur_shares - $prev_shares) / $prev_shares) * 100, 2) : -100;
        } else {
            $change_type = 'unchanged';
            $change_pct = 0;
        }
    }

    $sql = "INSERT INTO gm_sec_13f_holdings
        (cik, fund_name, ticker, cusip, name_of_issuer, value_thousands, shares,
         filing_quarter, filing_date, prev_shares, change_pct, change_type, created_at)
        VALUES (
            '" . _sec_esc($holding['cik']) . "',
            '" . _sec_esc($holding['fund_name']) . "',
            '" . _sec_esc($holding['ticker']) . "',
            '" . _sec_esc($holding['cusip']) . "',
            '" . _sec_esc($holding['name_of_issuer']) . "',
            " . intval($holding['value_thousands']) . ",
            " . intval($holding['shares']) . ",
            '" . _sec_esc($holding['filing_quarter']) . "',
            '" . _sec_esc($holding['filing_date']) . "',
            " . intval($prev_shares) . ",
            " . floatval($change_pct) . ",
            '" . _sec_esc($change_type) . "',
            '" . _sec_esc($now) . "'
        )";
    $conn->query($sql);
    return true;
}

// ── Get previous quarter string ──
function _sec_prev_quarter($quarter) {
    // e.g., Q1-2026 => Q4-2025, Q4-2025 => Q3-2025
    if (!preg_match('/^Q(\d)-(\d{4})$/', $quarter, $m)) return '';
    $q = intval($m[1]);
    $y = intval($m[2]);
    if ($q == 1) {
        return 'Q4-' . ($y - 1);
    } else {
        return 'Q' . ($q - 1) . '-' . $y;
    }
}

// ════════════════════════════════════════════════════════════════
//  PUBLIC ACTIONS
// ════════════════════════════════════════════════════════════════

// ── insider_activity: Recent insider trades for a ticker ──
if ($action === 'insider_activity') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    if (!$ticker) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing ticker parameter'));
        exit;
    }

    $cache_key = 'insider_activity_' . $ticker;
    $cached = _sec_cache_get($cache_key, 21600); // 6hr cache
    if ($cached) {
        echo json_encode($cached);
        exit;
    }

    $cutoff = date('Y-m-d', strtotime('-90 days'));
    $trades = array();
    $r = $conn->query("SELECT ticker, filer_name, filer_title, transaction_date, transaction_type,
        shares, price_per_share, total_value, shares_owned_after, filing_date,
        accession_number, is_director, is_officer, is_ten_pct_owner
        FROM gm_sec_insider_trades
        WHERE ticker = '" . _sec_esc($ticker) . "'
        AND transaction_date >= '" . _sec_esc($cutoff) . "'
        ORDER BY transaction_date DESC, filing_date DESC
        LIMIT 100");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $row['shares'] = floatval($row['shares']);
            $row['price_per_share'] = floatval($row['price_per_share']);
            $row['total_value'] = floatval($row['total_value']);
            $row['shares_owned_after'] = floatval($row['shares_owned_after']);
            $row['is_director'] = intval($row['is_director']);
            $row['is_officer'] = intval($row['is_officer']);
            $row['is_ten_pct_owner'] = intval($row['is_ten_pct_owner']);
            $trades[] = $row;
        }
    }

    // Summary stats
    $buy_count = 0;
    $sell_count = 0;
    $buy_value = 0;
    $sell_value = 0;
    foreach ($trades as $t) {
        if ($t['transaction_type'] === 'P') {
            $buy_count++;
            $buy_value += $t['total_value'];
        } elseif ($t['transaction_type'] === 'S') {
            $sell_count++;
            $sell_value += $t['total_value'];
        }
    }

    $result = array(
        'ok'     => true,
        'ticker' => $ticker,
        'period' => '90 days',
        'summary' => array(
            'total_transactions' => count($trades),
            'purchases'          => $buy_count,
            'sales'              => $sell_count,
            'total_buy_value'    => round($buy_value, 2),
            'total_sell_value'   => round($sell_value, 2),
            'net_insider_value'  => round($buy_value - $sell_value, 2)
        ),
        'trades' => $trades
    );

    _sec_cache_set($cache_key, $result);
    echo json_encode($result);
    exit;
}

// ── insider_clusters: Stocks with 3+ insiders buying in last 14 days ──
if ($action === 'insider_clusters') {
    $cache_key = 'insider_clusters';
    $cached = _sec_cache_get($cache_key, 21600); // 6hr cache
    if ($cached) {
        echo json_encode($cached);
        exit;
    }

    $cutoff = date('Y-m-d', strtotime('-14 days'));
    $clusters = array();
    $r = $conn->query("SELECT ticker,
        COUNT(DISTINCT filer_name) as insiders,
        SUM(total_value) as total_bought,
        SUM(shares) as total_shares,
        MIN(transaction_date) as first_buy,
        MAX(transaction_date) as last_buy,
        GROUP_CONCAT(DISTINCT filer_name SEPARATOR ', ') as buyers
        FROM gm_sec_insider_trades
        WHERE transaction_type = 'P'
        AND transaction_date >= '" . _sec_esc($cutoff) . "'
        GROUP BY ticker
        HAVING insiders >= 3
        ORDER BY insiders DESC, total_bought DESC
        LIMIT 50");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $row['insiders'] = intval($row['insiders']);
            $row['total_bought'] = floatval($row['total_bought']);
            $row['total_shares'] = floatval($row['total_shares']);
            $clusters[] = $row;
        }
    }

    $result = array(
        'ok'       => true,
        'period'   => '14 days',
        'cutoff'   => $cutoff,
        'clusters' => $clusters,
        'count'    => count($clusters)
    );

    _sec_cache_set($cache_key, $result);
    echo json_encode($result);
    exit;
}

// ── fund_holdings: Which tracked funds hold this stock ──
if ($action === 'fund_holdings') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    if (!$ticker) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing ticker parameter'));
        exit;
    }

    $cache_key = 'fund_holdings_' . $ticker;
    $cached = _sec_cache_get($cache_key, 21600); // 6hr cache
    if ($cached) {
        echo json_encode($cached);
        exit;
    }

    // Get the latest filing quarter in the database
    $latest_q = '';
    $qr = $conn->query("SELECT filing_quarter FROM gm_sec_13f_holdings ORDER BY filing_date DESC LIMIT 1");
    if ($qr && ($qrow = $qr->fetch_assoc())) {
        $latest_q = $qrow['filing_quarter'];
    }

    $holdings = array();
    if ($latest_q) {
        $r = $conn->query("SELECT fund_name, cik, ticker, cusip, name_of_issuer,
            value_thousands, shares, filing_quarter, filing_date,
            prev_shares, change_pct, change_type
            FROM gm_sec_13f_holdings
            WHERE ticker = '" . _sec_esc($ticker) . "'
            AND filing_quarter = '" . _sec_esc($latest_q) . "'
            ORDER BY value_thousands DESC");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $row['value_thousands'] = intval($row['value_thousands']);
                $row['shares'] = intval($row['shares']);
                $row['prev_shares'] = intval($row['prev_shares']);
                $row['change_pct'] = floatval($row['change_pct']);
                $holdings[] = $row;
            }
        }
    }

    $total_value = 0;
    $total_shares = 0;
    foreach ($holdings as $h) {
        $total_value += $h['value_thousands'];
        $total_shares += $h['shares'];
    }

    $result = array(
        'ok'              => true,
        'ticker'          => $ticker,
        'filing_quarter'  => $latest_q,
        'funds_holding'   => count($holdings),
        'total_value_k'   => $total_value,
        'total_shares'    => $total_shares,
        'holdings'        => $holdings
    );

    _sec_cache_set($cache_key, $result);
    echo json_encode($result);
    exit;
}

// ── new_positions: New positions opened by tracked funds ──
if ($action === 'new_positions') {
    $cache_key = 'new_positions';
    $cached = _sec_cache_get($cache_key, 21600); // 6hr cache
    if ($cached) {
        echo json_encode($cached);
        exit;
    }

    // Get the latest filing quarter
    $latest_q = '';
    $qr = $conn->query("SELECT filing_quarter FROM gm_sec_13f_holdings ORDER BY filing_date DESC LIMIT 1");
    if ($qr && ($qrow = $qr->fetch_assoc())) {
        $latest_q = $qrow['filing_quarter'];
    }

    $positions = array();
    if ($latest_q) {
        $r = $conn->query("SELECT fund_name, cik, ticker, cusip, name_of_issuer,
            value_thousands, shares, filing_quarter, filing_date
            FROM gm_sec_13f_holdings
            WHERE change_type = 'new'
            AND filing_quarter = '" . _sec_esc($latest_q) . "'
            ORDER BY value_thousands DESC
            LIMIT 100");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $row['value_thousands'] = intval($row['value_thousands']);
                $row['shares'] = intval($row['shares']);
                $positions[] = $row;
            }
        }
    }

    $result = array(
        'ok'              => true,
        'filing_quarter'  => $latest_q,
        'new_positions'   => $positions,
        'count'           => count($positions)
    );

    _sec_cache_set($cache_key, $result);
    echo json_encode($result);
    exit;
}

// ── conviction_picks: Stocks held by 3+ tracked funds ──
if ($action === 'conviction_picks') {
    $cache_key = 'conviction_picks';
    $cached = _sec_cache_get($cache_key, 21600); // 6hr cache
    if ($cached) {
        echo json_encode($cached);
        exit;
    }

    // Get the latest filing quarter
    $latest_q = '';
    $qr = $conn->query("SELECT filing_quarter FROM gm_sec_13f_holdings ORDER BY filing_date DESC LIMIT 1");
    if ($qr && ($qrow = $qr->fetch_assoc())) {
        $latest_q = $qrow['filing_quarter'];
    }

    $picks = array();
    if ($latest_q) {
        $r = $conn->query("SELECT ticker, name_of_issuer,
            COUNT(DISTINCT cik) as fund_count,
            GROUP_CONCAT(DISTINCT fund_name SEPARATOR ', ') as funds,
            SUM(value_thousands) as total_value_k,
            SUM(shares) as total_shares,
            SUM(CASE WHEN change_type = 'increased' THEN 1 ELSE 0 END) as funds_increasing,
            SUM(CASE WHEN change_type = 'decreased' THEN 1 ELSE 0 END) as funds_decreasing,
            SUM(CASE WHEN change_type = 'new' THEN 1 ELSE 0 END) as funds_new
            FROM gm_sec_13f_holdings
            WHERE filing_quarter = '" . _sec_esc($latest_q) . "'
            AND ticker != ''
            GROUP BY ticker, name_of_issuer
            HAVING fund_count >= 3
            ORDER BY fund_count DESC, total_value_k DESC
            LIMIT 50");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $row['fund_count'] = intval($row['fund_count']);
                $row['total_value_k'] = intval($row['total_value_k']);
                $row['total_shares'] = intval($row['total_shares']);
                $row['funds_increasing'] = intval($row['funds_increasing']);
                $row['funds_decreasing'] = intval($row['funds_decreasing']);
                $row['funds_new'] = intval($row['funds_new']);

                // Sentiment: net increasing vs decreasing
                $net = $row['funds_increasing'] + $row['funds_new'] - $row['funds_decreasing'];
                if ($net > 0) {
                    $row['sentiment'] = 'bullish';
                } elseif ($net < 0) {
                    $row['sentiment'] = 'bearish';
                } else {
                    $row['sentiment'] = 'neutral';
                }

                $picks[] = $row;
            }
        }
    }

    $result = array(
        'ok'              => true,
        'filing_quarter'  => $latest_q,
        'conviction_picks' => $picks,
        'count'           => count($picks)
    );

    _sec_cache_set($cache_key, $result);
    echo json_encode($result);
    exit;
}

// ── No matching action ──
header('HTTP/1.0 400 Bad Request');
echo json_encode(array(
    'ok' => false,
    'error' => 'Unknown action: ' . $action,
    'available_actions' => array(
        'fetch_form4'      => 'Admin: fetch Form 4 insider trades (requires key)',
        'fetch_13f'        => 'Admin: fetch 13F institutional holdings (requires key)',
        'insider_activity' => 'Public: recent insider trades for a ticker (?ticker=AAPL)',
        'insider_clusters' => 'Public: stocks with 3+ insiders buying recently',
        'fund_holdings'    => 'Public: which tracked funds hold a stock (?ticker=AAPL)',
        'new_positions'    => 'Public: new positions opened by tracked funds',
        'conviction_picks' => 'Public: stocks held by 3+ tracked funds'
    )
));
exit;

?>
