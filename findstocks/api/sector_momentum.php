<?php
/**
 * Sector Momentum Algorithm — Overweight Hot Sectors, Underweight Laggards
 *
 * Core thesis: Sectors with strong recent relative performance tend to
 * continue outperforming (momentum factor). This algorithm ranks all 11
 * GICS sectors by their trailing 60-day return, then ONLY enters positions
 * in the top 4 performing sectors. Skips lagging sectors entirely.
 *
 * This simulates "Sector Performance vs News" by rotating into sectors
 * that are being driven by news/macro catalysts (rate cuts -> XLF,
 * oil spike -> XLE, AI boom -> XLK, etc.)
 *
 * PHP 5.2 compatible.
 *
 * Usage: GET .../sector_momentum.php?action=seed
 *        GET .../sector_momentum.php?action=info
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'seed';
$results = array('ok' => true, 'algorithm' => 'Sector Momentum', 'action' => $action);

$algo_name = 'Sector Momentum';
$algo_desc = 'News/macro-driven sector rotation. Ranks all 11 GICS sectors by 60-day relative performance, enters only the top 4 momentum sectors each month. Simulates rotating into sectors driven by macro catalysts: rate cuts (XLF), oil spikes (XLE), AI boom (XLK), etc.';

// Same 11 sector ETFs
$sectors = array(
    array('ticker' => 'XLK',  'name' => 'Technology Select Sector SPDR',      'sector' => 'Technology'),
    array('ticker' => 'XLF',  'name' => 'Financial Select Sector SPDR',       'sector' => 'Financials'),
    array('ticker' => 'XLE',  'name' => 'Energy Select Sector SPDR',          'sector' => 'Energy'),
    array('ticker' => 'XLV',  'name' => 'Health Care Select Sector SPDR',     'sector' => 'Healthcare'),
    array('ticker' => 'XLI',  'name' => 'Industrial Select Sector SPDR',      'sector' => 'Industrials'),
    array('ticker' => 'XLC',  'name' => 'Communication Services Select SPDR', 'sector' => 'Communication'),
    array('ticker' => 'XLY',  'name' => 'Consumer Discretionary Select SPDR', 'sector' => 'Consumer Discretionary'),
    array('ticker' => 'XLP',  'name' => 'Consumer Staples Select Sector SPDR','sector' => 'Consumer Staples'),
    array('ticker' => 'XLU',  'name' => 'Utilities Select Sector SPDR',       'sector' => 'Utilities'),
    array('ticker' => 'XLRE', 'name' => 'Real Estate Select Sector SPDR',     'sector' => 'Real Estate'),
    array('ticker' => 'XLB',  'name' => 'Materials Select Sector SPDR',       'sector' => 'Materials')
);

// ─── Ensure algorithm exists ───
$check = $conn->query("SELECT id FROM algorithms WHERE name='" . $conn->real_escape_string($algo_name) . "'");
$algo_id = 0;
if ($check && $check->num_rows > 0) {
    $row = $check->fetch_assoc();
    $algo_id = (int)$row['id'];
    $conn->query("UPDATE algorithms SET description='" . $conn->real_escape_string($algo_desc) . "', family='Sector', algo_type='momentum_rotation', ideal_timeframe='30d' WHERE id=$algo_id");
} else {
    $conn->query("INSERT INTO algorithms (name, family, description, algo_type, ideal_timeframe) VALUES ('" . $conn->real_escape_string($algo_name) . "','Sector','" . $conn->real_escape_string($algo_desc) . "','momentum_rotation','30d')");
    $algo_id = (int)$conn->insert_id;
}
$results['algo_id'] = $algo_id;

if ($action === 'info') {
    $all = array();
    foreach ($sectors as $t) $all[] = $t['ticker'];
    $pick_count = 0;
    $r = $conn->query("SELECT COUNT(*) as cnt FROM stock_picks WHERE algorithm_name='" . $conn->real_escape_string($algo_name) . "'");
    if ($r && $row = $r->fetch_assoc()) $pick_count = (int)$row['cnt'];
    $results['tickers'] = $all;
    $results['picks_in_db'] = $pick_count;
    echo json_encode($results);
    $conn->close();
    exit;
}

// ─── Upsert stock records ───
foreach ($sectors as $stock) {
    $safe_ticker = $conn->real_escape_string($stock['ticker']);
    $safe_name = $conn->real_escape_string($stock['name']);
    $safe_sector = $conn->real_escape_string($stock['sector']);
    $conn->query("INSERT INTO stocks (ticker, company_name, sector) VALUES ('$safe_ticker','$safe_name','$safe_sector') ON DUPLICATE KEY UPDATE company_name='$safe_name', sector='$safe_sector'");
}

// ─── Load ALL sector prices into memory ───
$all_prices = array(); // ticker => array of {date, open, close}
$all_dates_map = array(); // ticker => date => index
foreach ($sectors as $stock) {
    $ticker = $stock['ticker'];
    $safe_ticker = $conn->real_escape_string($ticker);
    $pr = $conn->query("SELECT trade_date, open_price, close_price FROM daily_prices WHERE ticker='$safe_ticker' ORDER BY trade_date ASC");
    if (!$pr || $pr->num_rows === 0) continue;
    $all_prices[$ticker] = array();
    $all_dates_map[$ticker] = array();
    $idx = 0;
    while ($row = $pr->fetch_assoc()) {
        $all_prices[$ticker][] = array('date' => $row['trade_date'], 'open' => (float)$row['open_price'], 'close' => (float)$row['close_price']);
        $all_dates_map[$ticker][$row['trade_date']] = $idx;
        $idx++;
    }
}

// ─── Identify monthly entry dates (first trading day of each month) ───
// Use SPY's dates as reference calendar
$ref_ticker = 'XLK';
if (!isset($all_prices[$ref_ticker]) || count($all_prices[$ref_ticker]) === 0) {
    $results['error'] = 'No price data for ' . $ref_ticker . '. Fetch prices first.';
    echo json_encode($results);
    $conn->close();
    exit;
}

$monthly_dates = array();
$current_month = '';
foreach ($all_prices[$ref_ticker] as $p) {
    $ym = substr($p['date'], 0, 7);
    if ($ym !== $current_month) {
        $current_month = $ym;
        $monthly_dates[] = $p['date'];
    }
}

// ─── For each month, rank sectors by trailing 60-day return and pick top 4 ───
$seeded = 0;
$skipped = 0;
$top_n = 4; // Top 4 momentum sectors per month
$lookback = 60; // 60-day trailing return
$per_ticker = array();
$monthly_picks = array();

foreach ($sectors as $s) $per_ticker[$s['ticker']] = array('sector' => $s['sector'], 'seeded' => 0, 'selected_months' => 0);

foreach ($monthly_dates as $entry_date) {
    // Rank all sectors by 60-day trailing return
    $rankings = array();
    foreach ($sectors as $stock) {
        $ticker = $stock['ticker'];
        if (!isset($all_dates_map[$ticker][$entry_date])) continue;
        $idx = $all_dates_map[$ticker][$entry_date];
        $prices = $all_prices[$ticker];

        // Need at least 60 days of history
        if ($idx < $lookback) continue;

        $current_close = $prices[$idx]['close'];
        $past_close = $prices[$idx - $lookback]['close'];
        if ($past_close <= 0) continue;

        $trailing_return = (($current_close - $past_close) / $past_close) * 100;

        $rankings[] = array(
            'ticker' => $ticker,
            'sector' => $stock['sector'],
            'return_60d' => $trailing_return,
            'entry_price' => $prices[$idx]['open']
        );
    }

    if (count($rankings) < $top_n) continue;

    // Sort by trailing return descending
    // PHP 5.2 compatible sort
    for ($i = 0; $i < count($rankings); $i++) {
        for ($j = $i + 1; $j < count($rankings); $j++) {
            if ($rankings[$j]['return_60d'] > $rankings[$i]['return_60d']) {
                $tmp = $rankings[$i];
                $rankings[$i] = $rankings[$j];
                $rankings[$j] = $tmp;
            }
        }
    }

    // Pick top N sectors
    $top_sectors = array_slice($rankings, 0, $top_n);
    $month_picks_info = array();

    foreach ($top_sectors as $rank_idx => $ranked) {
        $ticker = $ranked['ticker'];
        $safe_ticker = $conn->real_escape_string($ticker);
        $entry_price = $ranked['entry_price'];
        if ($entry_price <= 0) continue;

        $hash = sha1('sector_momentum_' . $ticker . '_' . $entry_date . '_' . $algo_name);
        $safe_hash = $conn->real_escape_string($hash);
        $dup = $conn->query("SELECT id FROM stock_picks WHERE pick_hash='$safe_hash' LIMIT 1");
        if ($dup && $dup->num_rows > 0) {
            $skipped++;
            continue;
        }

        $pick_time = $entry_date . ' 09:30:00';
        $momentum_rank = $rank_idx + 1;
        $indicators = json_encode(array(
            'strategy' => 'sector_momentum_top4',
            'sector' => $ranked['sector'],
            'momentum_rank' => $momentum_rank,
            'trailing_60d_return' => round($ranked['return_60d'], 2),
            'rationale' => 'Top ' . $momentum_rank . ' momentum sector (' . round($ranked['return_60d'], 1) . '% 60d return)'
        ));
        $safe_ind = $conn->real_escape_string($indicators);

        $score = 90 - ($momentum_rank - 1) * 5; // #1 = 90, #2 = 85, #3 = 80, #4 = 75
        $rating = ($momentum_rank <= 2) ? 'Strong Buy' : 'Buy';

        $sql = "INSERT INTO stock_picks (ticker, algorithm_id, algorithm_name, pick_date, pick_time, entry_price, simulated_entry_price, score, rating, risk_level, timeframe, stop_loss_price, pick_hash, indicators_json, verified)
                VALUES ('$safe_ticker', $algo_id, '" . $conn->real_escape_string($algo_name) . "', '$entry_date', '$pick_time', $entry_price, $entry_price, $score, '$rating', 'Medium', '30d', 0, '$safe_hash', '$safe_ind', 1)";
        if ($conn->query($sql)) {
            $seeded++;
            $per_ticker[$ticker]['seeded']++;
            $per_ticker[$ticker]['selected_months']++;
            $month_picks_info[] = $ticker . ' (' . round($ranked['return_60d'], 1) . '%)';
        }
    }
    $monthly_picks[] = array('date' => $entry_date, 'picks' => $month_picks_info);
}

$results['seeded'] = $seeded;
$results['skipped'] = $skipped;
$results['top_n_per_month'] = $top_n;
$results['lookback_days'] = $lookback;
$results['monthly_entries'] = count($monthly_dates);
$results['per_ticker'] = $per_ticker;
$results['recent_rotations'] = array_slice($monthly_picks, -6);

$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('sector_momentum_seed', '" . $conn->real_escape_string("Seeded $seeded, skipped $skipped, top $top_n of 11 sectors") . "', '" . $conn->real_escape_string($ip) . "', '" . date('Y-m-d H:i:s') . "')");

echo json_encode($results);
$conn->close();
?>
