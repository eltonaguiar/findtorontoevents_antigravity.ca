<?php
/**
 * Blue Chip Growth — seed stock picks for "guaranteed growers" strategy.
 *
 * These are large-cap, dividend-aristocrat, or long-term consistent-growth stocks
 * that historically go up year over year. The strategy is long-term hold (buy & hold).
 *
 * Tickers are seeded as stock_picks with algorithm_name = 'Blue Chip Growth'
 * so they can be backtested against historical prices already in the system.
 *
 * PHP 5.2 compatible.
 *
 * Usage: GET .../blue_chip_picks.php
 *        GET .../blue_chip_picks.php?action=seed       — seed picks from latest prices
 *        GET .../blue_chip_picks.php?action=info       — list all blue chip tickers and status
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'seed';

// ─── Blue Chip Ticker Universe ───
// Criteria: 10+ year track record of consistent growth, dividend aristocrats,
// mega-cap with wide moats, year-over-year revenue/price appreciation.
$blue_chips = array(
    // ──── Consumer Staples / Franchises ────
    array('ticker' => 'MCD',  'name' => "McDonald's Corp",              'sector' => 'Consumer Cyclical',    'why' => '50+ years dividend growth, franchise model, global scale'),
    array('ticker' => 'KO',   'name' => 'Coca-Cola Co',                 'sector' => 'Consumer Defensive',   'why' => '60+ year dividend aristocrat, unmatched global brand'),
    array('ticker' => 'PEP',  'name' => 'PepsiCo Inc',                  'sector' => 'Consumer Defensive',   'why' => '50+ year dividend growth, Frito-Lay diversification'),
    array('ticker' => 'PG',   'name' => 'Procter & Gamble Co',          'sector' => 'Consumer Defensive',   'why' => '67+ year dividend growth, essential products moat'),
    array('ticker' => 'WMT',  'name' => 'Walmart Inc',                  'sector' => 'Consumer Defensive',   'why' => '50+ year dividend growth, e-commerce pivot success'),
    array('ticker' => 'COST', 'name' => 'Costco Wholesale Corp',        'sector' => 'Consumer Defensive',   'why' => 'Membership model, same-store sales growth, loyal base'),
    array('ticker' => 'SBUX', 'name' => 'Starbucks Corp',               'sector' => 'Consumer Cyclical',    'why' => 'Global expansion, mobile payments leader, brand loyalty'),

    // ──── Technology Mega-Caps ────
    array('ticker' => 'AAPL', 'name' => 'Apple Inc',                    'sector' => 'Technology',           'why' => 'Services revenue growth, ecosystem lock-in, $3T market cap'),
    array('ticker' => 'MSFT', 'name' => 'Microsoft Corp',               'sector' => 'Technology',           'why' => 'Azure cloud growth, Office365 recurring revenue, AI leader'),
    array('ticker' => 'GOOG', 'name' => 'Alphabet Inc',                 'sector' => 'Technology',           'why' => 'Search monopoly, YouTube, cloud growth, AI investments'),
    array('ticker' => 'V',    'name' => 'Visa Inc',                     'sector' => 'Financial Services',   'why' => 'Duopoly in payments, asset-light model, secular cashless trend'),
    array('ticker' => 'MA',   'name' => 'Mastercard Inc',               'sector' => 'Financial Services',   'why' => 'Global payment network, high margins, cross-border growth'),

    // ──── Healthcare Giants ────
    array('ticker' => 'JNJ',  'name' => 'Johnson & Johnson',            'sector' => 'Healthcare',           'why' => '60+ year dividend growth, diversified health conglomerate'),
    array('ticker' => 'UNH',  'name' => 'UnitedHealth Group',           'sector' => 'Healthcare',           'why' => 'Largest health insurer, Optum growth engine, aging population'),
    array('ticker' => 'ABBV', 'name' => 'AbbVie Inc',                   'sector' => 'Healthcare',           'why' => 'Humira successor pipeline, strong dividend, immunology leader'),

    // ──── Industrials / Infrastructure ────
    array('ticker' => 'HON',  'name' => 'Honeywell International',      'sector' => 'Industrials',          'why' => 'Aerospace + automation, consistent earnings growth'),
    array('ticker' => 'UNP',  'name' => 'Union Pacific Corp',           'sector' => 'Industrials',          'why' => 'Railroad duopoly, pricing power, buyback machine'),
    array('ticker' => 'CAT',  'name' => 'Caterpillar Inc',              'sector' => 'Industrials',          'why' => 'Infrastructure supercycle, mining recovery, global footprint'),
    array('ticker' => 'WM',   'name' => 'Waste Management Inc',         'sector' => 'Industrials',          'why' => 'Essential service monopoly, pricing power, renewable energy'),

    // ──── Financials ────
    array('ticker' => 'JPM',  'name' => 'JPMorgan Chase & Co',          'sector' => 'Financial Services',   'why' => 'Largest US bank, fortress balance sheet, tech investment'),
    array('ticker' => 'BRK-B','name' => 'Berkshire Hathaway B',         'sector' => 'Financial Services',   'why' => 'Buffett conglomerate, insurance float, massive cash reserves'),

    // ──── Energy ────
    array('ticker' => 'XOM',  'name' => 'Exxon Mobil Corp',             'sector' => 'Energy',               'why' => '40+ year dividend growth, low-cost Permian basin assets'),

    // ──── Real Estate / REITs ────
    array('ticker' => 'AMT',  'name' => 'American Tower Corp',          'sector' => 'Real Estate',          'why' => 'Cell tower REIT, 5G demand, global portfolio expansion'),

    // ──── Consumer Discretionary ────
    array('ticker' => 'HD',   'name' => 'Home Depot Inc',               'sector' => 'Consumer Cyclical',    'why' => 'Housing market moat, Pro customer segment, dividend aristocrat'),
    array('ticker' => 'NKE',  'name' => 'Nike Inc',                     'sector' => 'Consumer Cyclical',    'why' => 'Global brand dominance, DTC pivot, innovation pipeline')
);

$results = array(
    'ok' => true,
    'action' => $action,
    'ticker_count' => count($blue_chips),
    'seeded' => 0,
    'skipped' => 0,
    'prices_fetched' => 0,
    'errors' => array(),
    'tickers' => array()
);

// ─── Ensure algorithm exists ───
$algo_name = 'Blue Chip Growth';
$algo_family = 'Blue Chip';
$algo_desc = 'Large-cap consistent growers: dividend aristocrats, mega-cap wide-moat stocks with 10+ year track records of year-over-year appreciation. Buy-and-hold strategy.';
$algo_type = 'value_growth';
$algo_tf = '3m';

$safe_name = $conn->real_escape_string($algo_name);
$safe_fam  = $conn->real_escape_string($algo_family);
$safe_desc = $conn->real_escape_string($algo_desc);
$safe_type = $conn->real_escape_string($algo_type);
$safe_tf   = $conn->real_escape_string($algo_tf);

$conn->query("INSERT INTO algorithms (name, family, description, algo_type, ideal_timeframe)
              VALUES ('$safe_name','$safe_fam','$safe_desc','$safe_type','$safe_tf')
              ON DUPLICATE KEY UPDATE family='$safe_fam', description='$safe_desc', algo_type='$safe_type', ideal_timeframe='$safe_tf'");

// Get algo ID
$algo_id = 0;
$res = $conn->query("SELECT id FROM algorithms WHERE name='$safe_name'");
if ($res && $row = $res->fetch_assoc()) {
    $algo_id = (int)$row['id'];
}

if ($action === 'info') {
    // Just return info about each ticker
    foreach ($blue_chips as $bc) {
        $t = $conn->real_escape_string($bc['ticker']);
        $pick_res = $conn->query("SELECT COUNT(*) as cnt FROM stock_picks WHERE ticker='$t' AND algorithm_name='$safe_name'");
        $pick_cnt = 0;
        if ($pick_res && $r = $pick_res->fetch_assoc()) $pick_cnt = (int)$r['cnt'];

        $price_res = $conn->query("SELECT COUNT(*) as cnt, MIN(trade_date) as first_date, MAX(trade_date) as last_date FROM daily_prices WHERE ticker='$t'");
        $price_info = array('days' => 0);
        if ($price_res && $r = $price_res->fetch_assoc()) {
            $price_info = array('days' => (int)$r['cnt'], 'first' => $r['first_date'], 'last' => $r['last_date']);
        }

        $results['tickers'][] = array(
            'ticker' => $bc['ticker'],
            'name' => $bc['name'],
            'sector' => $bc['sector'],
            'why' => $bc['why'],
            'picks_in_db' => $pick_cnt,
            'price_data' => $price_info
        );
    }
    echo json_encode($results);
    $conn->close();
    exit;
}

// ─── Seed picks ───
// Strategy: create one pick per month over the past year for each blue chip stock.
// This creates a "DCA" (Dollar Cost Averaging) style entry pattern.
// Each pick uses the actual opening price on that date from daily_prices.
$now = date('Y-m-d H:i:s');

foreach ($blue_chips as $bc) {
    $ticker = $bc['ticker'];
    $safe_ticker = $conn->real_escape_string($ticker);
    $safe_co_name = $conn->real_escape_string($bc['name']);
    $safe_sector = $conn->real_escape_string($bc['sector']);

    // Upsert into stocks table
    $conn->query("INSERT INTO stocks (ticker, company_name, sector) VALUES ('$safe_ticker', '$safe_co_name', '$safe_sector')
                  ON DUPLICATE KEY UPDATE company_name='$safe_co_name', sector='$safe_sector'");

    // Get available price dates for this ticker (first trading day of each month)
    $price_sql = "SELECT trade_date, open_price
                  FROM daily_prices
                  WHERE ticker='$safe_ticker'
                  ORDER BY trade_date ASC";
    $price_res = $conn->query($price_sql);
    if (!$price_res || $price_res->num_rows === 0) {
        $results['errors'][] = $ticker . ': no price data — run fetch_prices.php first';
        continue;
    }

    // Group by month, pick first trading day of each month
    $monthly_entries = array();
    $last_month = '';
    while ($row = $price_res->fetch_assoc()) {
        $month = substr($row['trade_date'], 0, 7); // YYYY-MM
        if ($month !== $last_month) {
            $monthly_entries[] = array(
                'date' => $row['trade_date'],
                'price' => (float)$row['open_price']
            );
            $last_month = $month;
        }
    }

    $ticker_seeded = 0;
    foreach ($monthly_entries as $entry) {
        $pick_date = $entry['date'];
        $entry_price = $entry['price'];

        if ($entry_price <= 0) continue;

        // Build unique hash
        $hash = sha1('bluechip_' . $ticker . '_' . $pick_date . '_' . $algo_name);
        $safe_hash = $conn->real_escape_string($hash);

        // Check duplicate
        $dup = $conn->query("SELECT id FROM stock_picks WHERE ticker='$safe_ticker' AND pick_hash='$safe_hash'");
        if ($dup && $dup->num_rows > 0) {
            $results['skipped']++;
            continue;
        }

        // Insert pick
        $safe_why = $conn->real_escape_string(json_encode(array('rationale' => $bc['why'], 'strategy' => 'monthly_dca')));
        $sql = "INSERT INTO stock_picks (ticker, algorithm_id, algorithm_name, pick_date, pick_time,
                entry_price, simulated_entry_price, score, rating, risk_level, timeframe,
                stop_loss_price, pick_hash, indicators_json)
                VALUES ('$safe_ticker', $algo_id, '$safe_name', '$pick_date', '$pick_date 09:30:00',
                $entry_price, $entry_price, 85, 'Strong Buy', 'Low', '3m',
                0, '$safe_hash', '$safe_why')";

        if ($conn->query($sql)) {
            $ticker_seeded++;

            // Audit Trail Logging
            $audit_reasons = $bc['why'] . '. Strategy: monthly DCA into blue chip growth stock.';
            $audit_supporting_data = json_encode(array(
                'sector' => $bc['sector'],
                'name' => $bc['name'],
                'strategy' => 'monthly_dca'
            ));
            $audit_pick_details = json_encode(array(
                'entry_price' => $entry_price,
                'score' => 85,
                'rating' => 'Strong Buy',
                'risk_level' => 'Low',
                'timeframe' => '3m'
            ));
            $audit_formatted_for_ai = "Analyze this stock pick:\nSymbol: " . $ticker . "\nStrategy: Blue Chip Growth\nRationale: " . $audit_reasons . "\nSupporting Data: " . $audit_supporting_data . "\n\nQuestions:\n1. Is this a good long-term hold?\n2. What are the growth prospects?";

            $safe_reasons = $conn->real_escape_string($audit_reasons);
            $safe_supporting = $conn->real_escape_string($audit_supporting_data);
            $safe_details = $conn->real_escape_string($audit_pick_details);
            $safe_formatted = $conn->real_escape_string($audit_formatted_for_ai);
            $pick_timestamp = $pick_date . ' 09:30:00';

            $audit_sql = "INSERT INTO audit_trails 
                          (asset_class, symbol, pick_timestamp, generation_source, reasons, supporting_data, pick_details, formatted_for_ai)
                          VALUES ('STOCKS', '$safe_ticker', '$pick_timestamp', 'blue_chip_picks.php', '$safe_reasons', '$safe_supporting', '$safe_details', '$safe_formatted')";
            $conn->query($audit_sql);
        } else {
            $results['errors'][] = $ticker . ' ' . $pick_date . ': ' . $conn->error;
        }
    }

    $results['tickers'][] = array(
        'ticker' => $ticker,
        'name' => $bc['name'],
        'sector' => $bc['sector'],
        'monthly_picks_seeded' => $ticker_seeded,
        'months_available' => count($monthly_entries)
    );
    $results['seeded'] += $ticker_seeded;
}

// Audit log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$detail = $conn->real_escape_string('Blue Chip Growth: seeded=' . $results['seeded'] . ' skipped=' . $results['skipped'] . ' tickers=' . count($blue_chips));
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('blue_chip_seed', '$detail', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
