<?php
/**
 * Import mutual fund picks into mf2_fund_picks table.
 * Sources: manual entry, JSON feeds, or seeded sample data.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../import_picks.php                — import from JSON feeds
 *        GET .../import_picks.php?source=seed    — seed sample Canadian mutual fund data
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'imported' => 0, 'skipped' => 0, 'errors' => array());
$source = isset($_GET['source']) ? trim($_GET['source']) : 'seed';

// ─── Get algorithm ID map ───
$algo_map = array();
$res = $conn->query("SELECT id, name FROM mf2_algorithms");
if ($res) {
    while ($row = $res->fetch_assoc()) {
        $algo_map[$row['name']] = (int)$row['id'];
    }
}

// ─── Helper: insert a fund pick ───
function import_mf2_pick($conn, $algo_map, $fund, &$results) {
    $symbol = $conn->real_escape_string(isset($fund['symbol']) ? strtoupper($fund['symbol']) : '');
    if ($symbol === '') return;

    $fname   = $conn->real_escape_string(isset($fund['fund_name']) ? $fund['fund_name'] : '');
    $family  = $conn->real_escape_string(isset($fund['fund_family']) ? $fund['fund_family'] : '');
    $cat     = $conn->real_escape_string(isset($fund['category']) ? $fund['category'] : '');
    $aclass  = $conn->real_escape_string(isset($fund['asset_class']) ? $fund['asset_class'] : 'Equity');
    $expense = isset($fund['expense_ratio']) ? (float)$fund['expense_ratio'] : 0;
    $mstar   = isset($fund['morningstar_rating']) ? (int)$fund['morningstar_rating'] : 0;

    $nav      = isset($fund['nav']) ? (float)$fund['nav'] : (isset($fund['entry_nav']) ? (float)$fund['entry_nav'] : 0);
    $algo_nm  = isset($fund['algorithm']) ? $fund['algorithm'] : (isset($fund['algorithm_name']) ? $fund['algorithm_name'] : 'MF Balanced Composite');
    $score_v  = isset($fund['score']) ? (int)$fund['score'] : 0;
    $rating_v = isset($fund['rating']) ? $fund['rating'] : '';
    $risk_v   = isset($fund['risk_level']) ? $fund['risk_level'] : 'Medium';
    $tf_v     = isset($fund['timeframe']) ? $fund['timeframe'] : '';
    $phash    = isset($fund['pick_hash']) ? $fund['pick_hash'] : '';
    $pdate    = isset($fund['pick_date']) ? $fund['pick_date'] : date('Y-m-d');
    $ptime    = isset($fund['pick_time']) ? $fund['pick_time'] : ($pdate . ' 16:00:00');

    $algo_id = isset($algo_map[$algo_nm]) ? $algo_map[$algo_nm] : 0;

    // Upsert fund
    $conn->query("INSERT INTO mf2_funds (symbol, fund_name, fund_family, category, asset_class, expense_ratio, morningstar_rating)
                  VALUES ('$symbol', '$fname', '$family', '$cat', '$aclass', $expense, $mstar)
                  ON DUPLICATE KEY UPDATE fund_name='$fname', fund_family='$family', category='$cat', expense_ratio=$expense, morningstar_rating=$mstar");

    // Check duplicate
    $safe_algo = $conn->real_escape_string($algo_nm);
    $dup = $conn->query("SELECT id FROM mf2_fund_picks WHERE symbol='$symbol' AND pick_date='$pdate' AND algorithm_name='$safe_algo'");
    if ($dup && $dup->num_rows > 0) {
        $results['skipped']++;
        return;
    }

    $safe_rating = $conn->real_escape_string($rating_v);
    $safe_risk   = $conn->real_escape_string($risk_v);
    $safe_tf     = $conn->real_escape_string($tf_v);
    $safe_hash   = $conn->real_escape_string($phash);
    $rationale   = isset($fund['rationale']) ? $conn->real_escape_string(json_encode($fund['rationale'])) : '';

    $sql = "INSERT INTO mf2_fund_picks (symbol, algorithm_id, algorithm_name, pick_date, pick_time,
            entry_nav, score, rating, risk_level, timeframe, pick_hash, rationale_json)
            VALUES ('$symbol', $algo_id, '$safe_algo', '$pdate', '$ptime',
            $nav, $score_v, '$safe_rating', '$safe_risk', '$safe_tf', '$safe_hash', '$rationale')";

    if ($conn->query($sql)) {
        $results['imported']++;
    } else {
        $results['errors'][] = $symbol . ': ' . $conn->error;
    }
}

// ─── Source: Seed sample Canadian mutual fund picks ───
if ($source === 'seed') {
    $sample_funds = array(
        // Canadian Equity
        array('symbol' => 'RBF460', 'fund_name' => 'RBC Canadian Equity Fund', 'fund_family' => 'RBC', 'category' => 'Canadian Equity', 'asset_class' => 'Equity', 'expense_ratio' => 1.71, 'morningstar_rating' => 4, 'nav' => 48.52, 'algorithm' => 'MF Quality Growth', 'score' => 78, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '1y'),
        array('symbol' => 'TDB161', 'fund_name' => 'TD Canadian Equity Fund', 'fund_family' => 'TD', 'category' => 'Canadian Equity', 'asset_class' => 'Equity', 'expense_ratio' => 1.97, 'morningstar_rating' => 3, 'nav' => 32.15, 'algorithm' => 'MF Momentum', 'score' => 72, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '3m'),
        // US Equity
        array('symbol' => 'RBF556', 'fund_name' => 'RBC U.S. Equity Fund', 'fund_family' => 'RBC', 'category' => 'US Equity', 'asset_class' => 'Equity', 'expense_ratio' => 1.72, 'morningstar_rating' => 4, 'nav' => 55.80, 'algorithm' => 'MF Momentum', 'score' => 85, 'rating' => 'Strong Buy', 'risk_level' => 'Medium', 'timeframe' => '3m'),
        array('symbol' => 'TDB902', 'fund_name' => 'TD U.S. Blue Chip Equity Fund', 'fund_family' => 'TD', 'category' => 'US Equity', 'asset_class' => 'Equity', 'expense_ratio' => 1.98, 'morningstar_rating' => 3, 'nav' => 28.44, 'algorithm' => 'MF Quality Growth', 'score' => 80, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '6m'),
        // Bond / Income
        array('symbol' => 'RBF450', 'fund_name' => 'RBC Bond Fund', 'fund_family' => 'RBC', 'category' => 'Canadian Bond', 'asset_class' => 'Fixed Income', 'expense_ratio' => 1.05, 'morningstar_rating' => 3, 'nav' => 6.18, 'algorithm' => 'MF Diversified Income', 'score' => 70, 'rating' => 'Hold', 'risk_level' => 'Low', 'timeframe' => '1y'),
        array('symbol' => 'TDB162', 'fund_name' => 'TD Canadian Bond Fund', 'fund_family' => 'TD', 'category' => 'Canadian Bond', 'asset_class' => 'Fixed Income', 'expense_ratio' => 1.09, 'morningstar_rating' => 4, 'nav' => 11.22, 'algorithm' => 'MF Diversified Income', 'score' => 75, 'rating' => 'Buy', 'risk_level' => 'Low', 'timeframe' => '6m'),
        // Balanced
        array('symbol' => 'RBF480', 'fund_name' => 'RBC Balanced Fund', 'fund_family' => 'RBC', 'category' => 'Canadian Balanced', 'asset_class' => 'Balanced', 'expense_ratio' => 1.76, 'morningstar_rating' => 3, 'nav' => 18.95, 'algorithm' => 'MF Balanced Composite', 'score' => 74, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '6m'),
        array('symbol' => 'TDB160', 'fund_name' => 'TD Balanced Growth Fund', 'fund_family' => 'TD', 'category' => 'Canadian Balanced', 'asset_class' => 'Balanced', 'expense_ratio' => 1.96, 'morningstar_rating' => 3, 'nav' => 22.87, 'algorithm' => 'MF Risk Parity', 'score' => 68, 'rating' => 'Hold', 'risk_level' => 'Low-Medium', 'timeframe' => '6m'),
        // Global / International
        array('symbol' => 'RBF584', 'fund_name' => 'RBC Global Equity Fund', 'fund_family' => 'RBC', 'category' => 'Global Equity', 'asset_class' => 'Equity', 'expense_ratio' => 1.95, 'morningstar_rating' => 4, 'nav' => 35.67, 'algorithm' => 'MF Sector Rotation', 'score' => 82, 'rating' => 'Buy', 'risk_level' => 'Medium-High', 'timeframe' => '3m'),
        array('symbol' => 'TDB984', 'fund_name' => 'TD International Growth Fund', 'fund_family' => 'TD', 'category' => 'International Equity', 'asset_class' => 'Equity', 'expense_ratio' => 2.12, 'morningstar_rating' => 3, 'nav' => 14.55, 'algorithm' => 'MF Trend Following', 'score' => 65, 'rating' => 'Hold', 'risk_level' => 'Medium-High', 'timeframe' => '6m'),
        // Low-cost Index
        array('symbol' => 'TDB900', 'fund_name' => 'TD Canadian Index Fund', 'fund_family' => 'TD', 'category' => 'Canadian Equity Index', 'asset_class' => 'Equity', 'expense_ratio' => 0.33, 'morningstar_rating' => 4, 'nav' => 18.20, 'algorithm' => 'MF Expense Optimizer', 'score' => 90, 'rating' => 'Strong Buy', 'risk_level' => 'Medium', 'timeframe' => '1y'),
        array('symbol' => 'TDB911', 'fund_name' => 'TD U.S. Index Fund', 'fund_family' => 'TD', 'category' => 'US Equity Index', 'asset_class' => 'Equity', 'expense_ratio' => 0.35, 'morningstar_rating' => 5, 'nav' => 22.10, 'algorithm' => 'MF Expense Optimizer', 'score' => 92, 'rating' => 'Strong Buy', 'risk_level' => 'Medium', 'timeframe' => '1y'),
        // Sector / Specialty
        array('symbol' => 'RBF596', 'fund_name' => 'RBC Canadian Dividend Fund', 'fund_family' => 'RBC', 'category' => 'Canadian Dividend', 'asset_class' => 'Equity', 'expense_ratio' => 1.63, 'morningstar_rating' => 4, 'nav' => 52.30, 'algorithm' => 'MF Value Tilt', 'score' => 76, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '6m'),
        array('symbol' => 'TDB909', 'fund_name' => 'TD Dividend Growth Fund', 'fund_family' => 'TD', 'category' => 'Canadian Dividend', 'asset_class' => 'Equity', 'expense_ratio' => 1.89, 'morningstar_rating' => 4, 'nav' => 41.75, 'algorithm' => 'MF Value Tilt', 'score' => 73, 'rating' => 'Buy', 'risk_level' => 'Medium', 'timeframe' => '6m'),
        // Contrarian pick
        array('symbol' => 'RBF559', 'fund_name' => 'RBC Emerging Markets Equity Fund', 'fund_family' => 'RBC', 'category' => 'Emerging Markets', 'asset_class' => 'Equity', 'expense_ratio' => 2.24, 'morningstar_rating' => 3, 'nav' => 12.40, 'algorithm' => 'MF Mean Reversion', 'score' => 60, 'rating' => 'Speculative Buy', 'risk_level' => 'High', 'timeframe' => '6m')
    );

    foreach ($sample_funds as $fund) {
        import_mf2_pick($conn, $algo_map, $fund, $results);
    }
}

// ─── Source: JSON feeds ───
if ($source === 'json' || $source === 'all') {
    $urls = array(
        'https://findtorontoevents.ca/findmutualfunds2/data/daily-funds.json'
    );
    foreach ($urls as $url) {
        $json = @file_get_contents($url);
        if ($json === false) continue;
        $data = json_decode($json, true);
        if (!$data || !isset($data['funds'])) continue;
        foreach ($data['funds'] as $fund) {
            import_mf2_pick($conn, $algo_map, $fund, $results);
        }
    }
}

// Log
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$detail = 'Imported ' . $results['imported'] . ', skipped ' . $results['skipped'] . ' (source: ' . $source . ')';
$detail = $conn->real_escape_string($detail);
$conn->query("INSERT INTO mf2_audit_log (action_type, details, ip_address, created_at) VALUES ('import_picks', '$detail', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
