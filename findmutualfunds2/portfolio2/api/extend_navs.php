<?php
/**
 * Extend NAV data through current date for all funds.
 * Fills any gap between existing NAV data and today.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

$response = array('ok' => true, 'extended' => 0, 'funds' => array());

// Get all funds
$funds_res = $conn->query("SELECT symbol FROM mf2_funds ORDER BY symbol");
if (!$funds_res) {
    $response['ok'] = false;
    $response['error'] = 'No funds found';
    echo json_encode($response);
    $conn->close();
    exit;
}

$funds = array();
while ($row = $funds_res->fetch_assoc()) $funds[] = $row['symbol'];

$base_navs = array(
    'RBF460' => 48.52, 'TDB161' => 32.15, 'RBF556' => 55.80, 'TDB902' => 28.44,
    'RBF450' => 6.18,  'TDB162' => 11.22, 'RBF480' => 18.95, 'TDB160' => 22.87,
    'RBF584' => 35.67, 'TDB984' => 14.55, 'TDB900' => 18.20, 'TDB911' => 22.10,
    'RBF596' => 52.30, 'TDB909' => 41.75, 'RBF559' => 12.40
);

$today = date('Y-m-d');

foreach ($funds as $symbol) {
    $safe = $conn->real_escape_string($symbol);

    // Get the last NAV date and value for this fund
    $lr = $conn->query("SELECT nav_date, nav FROM mf2_nav_history WHERE symbol='$safe' ORDER BY nav_date DESC LIMIT 1");
    if (!$lr || $lr->num_rows === 0) {
        // No existing data - generate from 2 years ago
        $last_date = date('Y-m-d', strtotime('-2 years'));
        $last_nav = isset($base_navs[$symbol]) ? $base_navs[$symbol] * 0.92 : 20.0;
    } else {
        $lrow = $lr->fetch_assoc();
        $last_date = $lrow['nav_date'];
        $last_nav = (float)$lrow['nav'];
    }

    // Check if data needs extending
    if ($last_date >= $today) {
        $response['funds'][] = array('symbol' => $symbol, 'status' => 'up_to_date', 'last_date' => $last_date);
        continue;
    }

    // Generate daily NAV data from last_date+1 through today
    $base = isset($base_navs[$symbol]) ? $base_navs[$symbol] : 20.0;
    $volatility = $base * 0.003;
    $nav = $last_nav;
    $prev = $last_nav;
    $date = strtotime($last_date);
    $end = strtotime($today);
    $inserted = 0;

    mt_srand(crc32($symbol . $last_date));

    while ($date < $end) {
        $date = strtotime('+1 day', $date);
        if ($date > $end) break;
        $dow = date('w', $date);
        if ($dow == 0 || $dow == 6) continue;

        $change = (mt_rand(-100, 100) / 100) * $volatility;
        $change += $base * 0.0002;
        $nav = $nav + $change;
        if ($nav < $base * 0.7) $nav = $base * 0.7 + abs($change);
        $nav_val = round($nav, 4);
        $daily_ret = ($prev > 0) ? round(($nav_val - $prev) / $prev * 100, 6) : 0;

        $d = date('Y-m-d', $date);
        $sql = "INSERT INTO mf2_nav_history (symbol, nav_date, nav, prev_nav, daily_return_pct, volume)
                VALUES ('$safe', '$d', $nav_val, " . round($prev, 4) . ", $daily_ret, 0)
                ON DUPLICATE KEY UPDATE nav=$nav_val, prev_nav=" . round($prev, 4) . ", daily_return_pct=$daily_ret";
        if ($conn->query($sql)) $inserted++;
        $prev = $nav_val;
    }

    mt_srand();
    $response['funds'][] = array('symbol' => $symbol, 'records_added' => $inserted, 'last_nav' => round($nav, 4));
    $response['extended'] += $inserted;
}

$response['message'] = 'Extended NAV data for ' . count($funds) . ' funds, added ' . $response['extended'] . ' records through ' . $today;

// Log
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO mf2_audit_log (action_type, details, ip_address, created_at)
              VALUES ('extend_navs', '" . $conn->real_escape_string($response['message']) . "', '$ip', '$now')");

echo json_encode($response);
$conn->close();
?>
