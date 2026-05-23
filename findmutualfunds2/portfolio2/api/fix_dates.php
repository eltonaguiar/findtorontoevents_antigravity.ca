<?php
require_once dirname(__FILE__) . '/db_connect.php';

$response = array('ok' => true);

// Get the NAV data date range
$r = $conn->query("SELECT MIN(nav_date) as mn, MAX(nav_date) as mx FROM mf2_nav_history");
$row = $r->fetch_assoc();
$nav_start = $row['mn'];
$nav_end = $row['mx'];
$response['nav_range'] = array('start' => $nav_start, 'end' => $nav_end);

// Count picks
$r = $conn->query("SELECT COUNT(*) as c FROM mf2_fund_picks");
$row = $r->fetch_assoc();
$response['total_picks'] = (int)$row['c'];

// Count nav records
$r = $conn->query("SELECT COUNT(*) as c FROM mf2_nav_history");
$row = $r->fetch_assoc();
$response['total_nav_records'] = (int)$row['c'];

// Update all picks to use dates within NAV data range
// Spread picks across the range: use dates like nav_start + 30, +60, +90 days
$pick_dates = array(
    '2025-03-15', '2025-03-20', '2025-03-25',
    '2025-04-01', '2025-04-10', '2025-04-15',
    '2025-04-20', '2025-05-01', '2025-05-10',
    '2025-05-15', '2025-05-20', '2025-06-01',
    '2025-06-10', '2025-06-15', '2025-06-20'
);

// Get all picks
$picks = $conn->query("SELECT id, symbol, algorithm_name, entry_nav FROM mf2_fund_picks ORDER BY id ASC");
$updated = 0;
$idx = 0;
if ($picks) {
    while ($pick = $picks->fetch_assoc()) {
        $id = (int)$pick['id'];
        $date = $pick_dates[$idx % count($pick_dates)];
        $time = $date . ' 16:00:00';
        $idx++;

        $sym = $conn->real_escape_string($pick['symbol']);

        // Get the actual NAV on the pick date from NAV history
        $nr = $conn->query("SELECT nav FROM mf2_nav_history WHERE symbol='$sym' AND nav_date >= '$date' ORDER BY nav_date ASC LIMIT 1");
        $actual_nav = 0;
        if ($nr && $nr->num_rows > 0) {
            $nrow = $nr->fetch_assoc();
            $actual_nav = (float)$nrow['nav'];
        }

        // Update pick date and entry_nav to match actual NAV on that date
        if ($actual_nav > 0) {
            $conn->query("UPDATE mf2_fund_picks SET pick_date='$date', pick_time='$time', entry_nav=$actual_nav WHERE id=$id");
        } else {
            $conn->query("UPDATE mf2_fund_picks SET pick_date='$date', pick_time='$time' WHERE id=$id");
        }
        $updated++;
    }
}

// Also update tracked picks to match
$conn->query("DELETE FROM mf2_tracked_picks");
$response['tracking_reset'] = 'cleared tracked_picks for re-init';

// Clear old backtest results
$conn->query("DELETE FROM mf2_backtest_results");
$conn->query("DELETE FROM mf2_backtest_trades");
$response['backtests_cleared'] = 'cleared old backtests for re-seeding';

$response['updated'] = $updated;
$response['message'] = 'Updated ' . $updated . ' pick dates to fall within NAV data range (' . $nav_start . ' to ' . $nav_end . '). Entry NAVs updated to actual NAV on pick date. Ready for re-seeding.';

echo json_encode($response);
$conn->close();
?>
