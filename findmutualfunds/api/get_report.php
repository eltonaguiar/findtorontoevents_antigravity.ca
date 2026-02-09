<?php
/**
 * Serve cached daily mutual fund report.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

$r = $conn->query("SELECT cache_data, updated_at FROM mf_report_cache WHERE cache_key='daily_summary'");
if ($r && $row = $r->fetch_assoc()) {
    echo $row['cache_data'];
} else {
    echo json_encode(array('ok' => false, 'error' => 'No cached report. Run daily_refresh.php first.'));
}
$conn->close();
?>
