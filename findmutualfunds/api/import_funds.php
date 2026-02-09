<?php
/**
 * Auto-generate fund selections from the mf_funds table using mf_strategies.
 * This acts as the "stock picks import" equivalent for mutual funds.
 * Assigns each fund to matching strategies based on asset_class and category.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../import_funds.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$now = date('Y-m-d H:i:s');
$today = date('Y-m-d');

// Strategy-to-fund matching rules
$strategy_rules = array(
    'Growth Leaders'      => array('asset' => 'Equity',        'cats' => array('Large Growth', 'Large Blend'), 'min_star' => 4),
    'Income Focus'        => array('asset' => 'Bond',          'cats' => array(),                              'min_star' => 3),
    'Balanced Moderate'   => array('asset' => 'Balanced',      'cats' => array(),                              'min_star' => 3),
    'Aggressive Growth'   => array('asset' => 'Equity',        'cats' => array('Large Growth'),                'min_star' => 0),
    'Index Tracker'       => array('asset' => 'Equity',        'cats' => array('Large Blend'),                 'max_exp' => 0.002),
    'Sector Rotation'     => array('asset' => 'Sector',        'cats' => array(),                              'min_star' => 3),
    'International Blend' => array('asset' => 'International', 'cats' => array(),                              'min_star' => 3),
    'ESG/Sustainable'     => array('asset' => 'Equity',        'cats' => array(),                              'min_star' => 4),
    'Contrarian Value'    => array('asset' => 'Equity',        'cats' => array('Large Value'),                 'min_star' => 3)
);

// Fetch all strategies
$strats = array();
$r = $conn->query("SELECT * FROM mf_strategies ORDER BY id");
if ($r) { while ($row = $r->fetch_assoc()) $strats[$row['name']] = $row; }

// Fetch all funds
$funds = array();
$r = $conn->query("SELECT * FROM mf_funds ORDER BY ticker");
if ($r) { while ($row = $r->fetch_assoc()) $funds[] = $row; }

// Get latest NAV for each fund
$latest_navs = array();
$r = $conn->query("SELECT ticker, adj_nav, nav_date FROM mf_nav_history WHERE (ticker, nav_date) IN (SELECT ticker, MAX(nav_date) FROM mf_nav_history GROUP BY ticker)");
if (!$r) {
    // Fallback for MySQL versions that don't support tuple IN
    $r = $conn->query("SELECT nh.ticker, nh.adj_nav, nh.nav_date FROM mf_nav_history nh INNER JOIN (SELECT ticker, MAX(nav_date) as max_date FROM mf_nav_history GROUP BY ticker) t ON nh.ticker=t.ticker AND nh.nav_date=t.max_date");
}
if ($r) { while ($row = $r->fetch_assoc()) $latest_navs[$row['ticker']] = $row; }

$imported = 0;
$skipped = 0;

foreach ($strats as $sname => $strat) {
    if (!isset($strategy_rules[$sname])) continue;
    $rule = $strategy_rules[$sname];

    foreach ($funds as $fund) {
        // Match asset class
        if (isset($rule['asset']) && $fund['asset_class'] !== $rule['asset']) continue;

        // Match category
        if (isset($rule['cats']) && count($rule['cats']) > 0) {
            $cat_match = false;
            foreach ($rule['cats'] as $cat) {
                if (stripos($fund['category'], $cat) !== false) { $cat_match = true; break; }
            }
            if (!$cat_match) continue;
        }

        // Match star rating
        if (isset($rule['min_star']) && (int)$fund['morningstar_rating'] < $rule['min_star']) continue;

        // Match expense ratio
        if (isset($rule['max_exp']) && (float)$fund['expense_ratio'] > $rule['max_exp']) continue;

        // Get NAV at selection
        $nav = 0;
        if (isset($latest_navs[$fund['ticker']])) {
            $nav = (float)$latest_navs[$fund['ticker']]['adj_nav'];
            $select_date = $latest_navs[$fund['ticker']]['nav_date'];
        } else {
            $select_date = $today;
        }

        // Check duplicate
        $safe_t = $conn->real_escape_string($fund['ticker']);
        $safe_s = $conn->real_escape_string($sname);
        $chk = $conn->query("SELECT id FROM mf_selections WHERE ticker='$safe_t' AND strategy_name='$safe_s' AND select_date='$select_date'");
        if ($chk && $chk->num_rows > 0) { $skipped++; continue; }

        $hash = sha1($fund['ticker'] . $sname . $select_date . $now);
        $rationale = $conn->real_escape_string('Auto-matched: ' . $fund['asset_class'] . ' / ' . $fund['category'] . ' / ' . $fund['morningstar_rating'] . ' stars');
        $sid = isset($strat['id']) ? (int)$strat['id'] : 0;

        $sql = "INSERT INTO mf_selections (ticker, strategy_id, strategy_name, select_date, nav_at_select, category, expense_ratio, morningstar_rating, rationale, select_hash)
                VALUES ('$safe_t', $sid, '$safe_s', '$select_date', $nav, '" . $conn->real_escape_string($fund['category']) . "', " . (float)$fund['expense_ratio'] . ", " . (int)$fund['morningstar_rating'] . ", '$rationale', '$hash')";
        if ($conn->query($sql)) $imported++;
    }
}

// Audit
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO mf_audit_log (action_type, details, ip_address, created_at) VALUES ('import_funds', 'Imported $imported, skipped $skipped', '$ip', '$now')");

echo json_encode(array('ok' => true, 'imported' => $imported, 'skipped' => $skipped, 'strategies_matched' => count($strategy_rules), 'funds_checked' => count($funds)));
$conn->close();
?>
