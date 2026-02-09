<?php
/**
 * Returns the cached daily summary report JSON.
 * Used by the report page to load pre-computed data quickly.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

$res = $conn->query("SELECT cache_data, updated_at FROM report_cache WHERE cache_key='daily_summary'");
if ($res && $row = $res->fetch_assoc()) {
    echo '{"ok":true,"updated_at":' . json_encode($row['updated_at']) . ',"report":' . $row['cache_data'] . '}';
} else {
    echo json_encode(array('ok' => false, 'error' => 'No cached report. Run daily_refresh.php first.'));
}
$conn->close();
?>
