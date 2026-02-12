<?php
// metrics.php - Real-time metrics endpoint
require_once __DIR__ . '/../../favcreators/public/api/config.php';

$query = "SELECT 
    AVG(return_pct) / STDDEV(return_pct) as sharpe,
    SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100 as win_rate,
    MIN(cum_pnl) as max_dd
    FROM (
        SELECT return_pct, 
        SUM(return_pct) OVER (ORDER BY entry_date) as cum_pnl
        FROM lm_trades WHERE status = 'closed'
    ) t";

$r = $conn->query($query);
$metrics = $r ? $r->fetch_assoc() : array('sharpe' => 0, 'win_rate' => 0, 'max_dd' => 0);

echo json_encode($metrics);
?>