<?php
require_once dirname(__FILE__) . '/db_connect.php';

$response = array('ok' => true);

// Count existing records
$r = $conn->query("SELECT COUNT(*) as c FROM mf2_nav_history");
if ($r) { $row = $r->fetch_assoc(); $response['total_records'] = (int)$row['c']; }

// Date range
$r = $conn->query("SELECT MIN(nav_date) as mn, MAX(nav_date) as mx FROM mf2_nav_history");
if ($r) { $row = $r->fetch_assoc(); $response['earliest'] = $row['mn']; $response['latest'] = $row['mx']; }

// Records after Oct 2025
$r = $conn->query("SELECT COUNT(*) as c FROM mf2_nav_history WHERE nav_date > '2025-10-22'");
if ($r) { $row = $r->fetch_assoc(); $response['records_after_oct22'] = (int)$row['c']; }

// Try inserting a test record
$test_sql = "INSERT INTO mf2_nav_history (symbol, nav_date, nav, prev_nav, daily_return_pct, volume)
             VALUES ('TEST001', '2026-02-12', 10.0, 9.99, 0.1, 0)
             ON DUPLICATE KEY UPDATE nav=10.0";
$ok = $conn->query($test_sql);
$response['test_insert'] = $ok ? 'success' : ('failed: ' . $conn->error);

// Check if test record exists
$r = $conn->query("SELECT * FROM mf2_nav_history WHERE symbol='TEST001' AND nav_date='2026-02-12'");
$response['test_found'] = ($r && $r->num_rows > 0) ? 'yes' : 'no';

// Clean up test
$conn->query("DELETE FROM mf2_nav_history WHERE symbol='TEST001'");

// Check recent records for RBF460
$r = $conn->query("SELECT nav_date, nav FROM mf2_nav_history WHERE symbol='RBF460' ORDER BY nav_date DESC LIMIT 5");
$recent = array();
if ($r) { while ($row = $r->fetch_assoc()) $recent[] = $row; }
$response['rbf460_recent'] = $recent;

echo json_encode($response);
$conn->close();
?>
