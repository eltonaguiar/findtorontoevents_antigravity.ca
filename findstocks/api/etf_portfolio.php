<?php
/**
 * ETF Masters Algorithm — Diversified ETF Portfolio
 *
 * Core thesis: Broad-market and thematic ETFs provide lower volatility,
 * instant diversification, and institutional-grade exposure.
 * Uses monthly DCA entries across 5 tiers of ETFs.
 *
 * Tier 1 (Core): SPY, QQQ, VTI — total market exposure
 * Tier 2 (Growth): VGT, SOXX, ARKK — tech/innovation
 * Tier 3 (Income): SCHD, VYM, DVY — dividend/income
 * Tier 4 (Bonds/Defensive): TLT, BND, GLD — risk-off hedges
 * Tier 5 (International): EFA, VWO, INDA — global diversification
 *
 * PHP 5.2 compatible.
 *
 * Usage: GET .../etf_portfolio.php?action=seed
 *        GET .../etf_portfolio.php?action=info
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'seed';
$results = array('ok' => true, 'algorithm' => 'ETF Masters', 'action' => $action);

$algo_name = 'ETF Masters';
$algo_desc = 'Diversified ETF portfolio across 5 tiers: core index (SPY/QQQ/VTI), growth/innovation (VGT/SOXX), income (SCHD/VYM), bonds/defensive (TLT/GLD), and international (EFA/VWO). Monthly DCA entries with broad market exposure.';

// ─── ETF Universe ───
$tier1_core = array(
    array('ticker' => 'SPY',  'name' => 'SPDR S&P 500 ETF',              'sector' => 'Broad Market',   'why' => 'The benchmark. Tracks S&P 500, most liquid ETF in the world'),
    array('ticker' => 'QQQ',  'name' => 'Invesco QQQ (Nasdaq-100)',       'sector' => 'Large Cap Growth','why' => 'Nasdaq-100, heavy tech tilt, strong long-term outperformance'),
    array('ticker' => 'VTI',  'name' => 'Vanguard Total Stock Market',    'sector' => 'Broad Market',   'why' => 'Total US market — large, mid, small cap in one ETF'),
    array('ticker' => 'VOO',  'name' => 'Vanguard S&P 500 ETF',          'sector' => 'Broad Market',   'why' => 'Low-cost S&P 500 tracker, 0.03% expense ratio'),
    array('ticker' => 'IWM',  'name' => 'iShares Russell 2000',           'sector' => 'Small Cap',      'why' => 'Small-cap exposure, diversifies away from mega-cap concentration')
);

$tier2_growth = array(
    array('ticker' => 'VGT',  'name' => 'Vanguard Information Tech ETF',  'sector' => 'Technology',     'why' => 'Pure tech sector play, includes AAPL/MSFT/NVDA'),
    array('ticker' => 'SOXX', 'name' => 'iShares Semiconductor ETF',      'sector' => 'Semiconductors', 'why' => 'Semiconductor supercycle: AI chips, data centers, EVs'),
    array('ticker' => 'XLK',  'name' => 'Technology Select Sector SPDR',  'sector' => 'Technology',     'why' => 'S&P 500 tech sector, lower cost alternative to VGT')
);

$tier3_income = array(
    array('ticker' => 'SCHD', 'name' => 'Schwab US Dividend Equity ETF',  'sector' => 'Dividend',       'why' => 'Quality dividend stocks, strong total return history'),
    array('ticker' => 'VYM',  'name' => 'Vanguard High Dividend Yield',   'sector' => 'Dividend',       'why' => '400+ high-dividend stocks, 3%+ yield'),
    array('ticker' => 'DVY',  'name' => 'iShares Select Dividend ETF',    'sector' => 'Dividend',       'why' => 'Dividend-weighted, screens for 5-yr payout history')
);

$tier4_defensive = array(
    array('ticker' => 'TLT',  'name' => 'iShares 20+ Year Treasury Bond', 'sector' => 'Bonds',          'why' => 'Long-duration Treasuries, classic risk-off hedge'),
    array('ticker' => 'GLD',  'name' => 'SPDR Gold Shares',               'sector' => 'Commodities',    'why' => 'Gold exposure, inflation hedge, crisis safe haven'),
    array('ticker' => 'BND',  'name' => 'Vanguard Total Bond Market',     'sector' => 'Bonds',          'why' => 'Total US bond market, stabilizer in equity downturns')
);

$tier5_intl = array(
    array('ticker' => 'EFA',  'name' => 'iShares MSCI EAFE ETF',          'sector' => 'International',  'why' => 'Developed international — Europe, Australasia, Far East'),
    array('ticker' => 'VWO',  'name' => 'Vanguard Emerging Markets ETF',   'sector' => 'Emerging Markets','why' => 'Broad emerging markets — China, India, Brazil, Taiwan'),
    array('ticker' => 'INDA', 'name' => 'iShares MSCI India ETF',          'sector' => 'India',          'why' => 'Fastest-growing large economy, demographic tailwind')
);

// ─── Ensure algorithm exists ───
$check = $conn->query("SELECT id FROM algorithms WHERE name='" . $conn->real_escape_string($algo_name) . "'");
$algo_id = 0;
if ($check && $check->num_rows > 0) {
    $row = $check->fetch_assoc();
    $algo_id = (int)$row['id'];
    $conn->query("UPDATE algorithms SET description='" . $conn->real_escape_string($algo_desc) . "', family='ETF', algo_type='passive_index', ideal_timeframe='90d' WHERE id=$algo_id");
} else {
    $conn->query("INSERT INTO algorithms (name, family, description, algo_type, ideal_timeframe) VALUES ('" . $conn->real_escape_string($algo_name) . "','ETF','" . $conn->real_escape_string($algo_desc) . "','passive_index','90d')");
    $algo_id = (int)$conn->insert_id;
}
$results['algo_id'] = $algo_id;

if ($action === 'info') {
    $all = array();
    foreach ($tier1_core as $t) $all[] = $t['ticker'];
    foreach ($tier2_growth as $t) $all[] = $t['ticker'];
    foreach ($tier3_income as $t) $all[] = $t['ticker'];
    foreach ($tier4_defensive as $t) $all[] = $t['ticker'];
    foreach ($tier5_intl as $t) $all[] = $t['ticker'];
    $pick_count = 0;
    $r = $conn->query("SELECT COUNT(*) as cnt FROM stock_picks WHERE algorithm_name='" . $conn->real_escape_string($algo_name) . "'");
    if ($r && $row = $r->fetch_assoc()) $pick_count = (int)$row['cnt'];
    $results['tickers'] = $all;
    $results['ticker_count'] = count($all);
    $results['picks_in_db'] = $pick_count;
    echo json_encode($results);
    $conn->close();
    exit;
}

// ─── Seed Picks (Monthly DCA for all tiers) ───
$seeded = 0;
$skipped = 0;
$no_price = 0;
$per_ticker = array();

// Build combined universe
$universe = array();
foreach ($tier1_core as $t) { $t['tier'] = 1; $t['tier_name'] = 'Core Index'; $universe[] = $t; }
foreach ($tier2_growth as $t) { $t['tier'] = 2; $t['tier_name'] = 'Growth'; $universe[] = $t; }
foreach ($tier3_income as $t) { $t['tier'] = 3; $t['tier_name'] = 'Income'; $universe[] = $t; }
foreach ($tier4_defensive as $t) { $t['tier'] = 4; $t['tier_name'] = 'Defensive'; $universe[] = $t; }
foreach ($tier5_intl as $t) { $t['tier'] = 5; $t['tier_name'] = 'International'; $universe[] = $t; }

foreach ($universe as $stock) {
    $ticker = $stock['ticker'];
    $safe_ticker = $conn->real_escape_string($ticker);

    // Upsert stock info
    $safe_name = $conn->real_escape_string($stock['name']);
    $safe_sector = $conn->real_escape_string($stock['sector']);
    $conn->query("INSERT INTO stocks (ticker, company_name, sector) VALUES ('$safe_ticker','$safe_name','$safe_sector') ON DUPLICATE KEY UPDATE company_name='$safe_name', sector='$safe_sector'");

    // Get prices grouped by month
    $pr = $conn->query("SELECT trade_date, open_price, close_price FROM daily_prices WHERE ticker='$safe_ticker' ORDER BY trade_date ASC");
    if (!$pr || $pr->num_rows === 0) {
        $no_price++;
        continue;
    }

    $monthly = array();
    $current_month = '';
    while ($row = $pr->fetch_assoc()) {
        $ym = substr($row['trade_date'], 0, 7);
        if ($ym !== $current_month) {
            $current_month = $ym;
            $monthly[] = array('date' => $row['trade_date'], 'open' => (float)$row['open_price'], 'close' => (float)$row['close_price']);
        }
    }

    $ticker_seeded = 0;
    foreach ($monthly as $entry) {
        $pick_date = $entry['date'];
        $entry_price = $entry['open'];
        if ($entry_price <= 0) continue;

        $hash = sha1('etf_masters_' . $ticker . '_' . $pick_date . '_' . $algo_name);
        $safe_hash = $conn->real_escape_string($hash);
        $dup = $conn->query("SELECT id FROM stock_picks WHERE pick_hash='$safe_hash' LIMIT 1");
        if ($dup && $dup->num_rows > 0) {
            $skipped++;
            continue;
        }

        $pick_time = $pick_date . ' 09:30:00';
        $indicators = json_encode(array(
            'strategy' => 'etf_monthly_dca',
            'tier' => $stock['tier'],
            'tier_name' => $stock['tier_name'],
            'rationale' => $stock['why']
        ));
        $safe_ind = $conn->real_escape_string($indicators);
        $score = 85;
        $rating = 'Buy';
        $risk = ($stock['tier'] <= 2) ? 'Low' : (($stock['tier'] === 4) ? 'Very Low' : 'Low-Medium');

        $sql = "INSERT INTO stock_picks (ticker, algorithm_id, algorithm_name, pick_date, pick_time, entry_price, simulated_entry_price, score, rating, risk_level, timeframe, stop_loss_price, pick_hash, indicators_json, verified)
                VALUES ('$safe_ticker', $algo_id, '" . $conn->real_escape_string($algo_name) . "', '$pick_date', '$pick_time', $entry_price, $entry_price, $score, '$rating', '$risk', '90d', 0, '$safe_hash', '$safe_ind', 1)";
        if ($conn->query($sql)) {
            $seeded++;
            $ticker_seeded++;

            // Audit Trail Logging
            $audit_reasons = $stock['why'] . '. Tier ' . $stock['tier'] . ' (' . $stock['tier_name'] . ') in diversified ETF portfolio.';
            $audit_supporting_data = json_encode(array(
                'tier' =&gt; $stock['tier'],
                'tier_name' =&gt; $stock['tier_name'],
                'strategy' =&gt; 'etf_monthly_dca'
            ));
            $audit_pick_details = json_encode(array(
                'entry_price' =&gt; $entry_price,
                'score' =&gt; $score,
                'rating' =&gt; $rating,
                'risk_level' =&gt; $risk,
                'timeframe' =&gt; '90d'
            ));
            $audit_formatted_for_ai = "Analyze this ETF pick:\nSymbol: " . $ticker . "\nStrategy: ETF Masters\nRationale: " . $audit_reasons . "\nSupporting Data: " . $audit_supporting_data . "\n\nQuestions:\n1. Is this ETF a good fit for diversification?\n2. What are its long-term prospects?";

            $safe_reasons = $conn->real_escape_string($audit_reasons);
            $safe_supporting = $conn->real_escape_string($audit_supporting_data);
            $safe_details = $conn->real_escape_string($audit_pick_details);
            $safe_formatted = $conn->real_escape_string($audit_formatted_for_ai);
            $pick_timestamp = $pick_time;

            $audit_sql = "INSERT INTO audit_trails 
                          (asset_class, symbol, pick_timestamp, generation_source, reasons, supporting_data, pick_details, formatted_for_ai)
                          VALUES ('STOCKS', '$safe_ticker', '$pick_timestamp', 'etf_portfolio.php', '$safe_reasons', '$safe_supporting', '$safe_details', '$safe_formatted')";
            $conn->query($audit_sql);
        }
    }
    $per_ticker[$ticker] = array('tier' => $stock['tier'], 'tier_name' => $stock['tier_name'], 'seeded' => $ticker_seeded);
}

$results['seeded'] = $seeded;
$results['skipped'] = $skipped;
$results['no_price_data'] = $no_price;
$results['ticker_count'] = count($universe);
$results['per_ticker'] = $per_ticker;

$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('etf_masters_seed', '" . $conn->real_escape_string("Seeded $seeded picks, skipped $skipped") . "', '" . $conn->real_escape_string($ip) . "', '" . date('Y-m-d H:i:s') . "')");

echo json_encode($results);
$conn->close();
?>
