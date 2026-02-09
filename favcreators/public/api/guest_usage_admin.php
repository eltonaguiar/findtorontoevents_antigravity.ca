<?php
/**
 * Diagnostic: view all tracking data — IPs, users, clicks, page views.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/guest_usage_schema.php';

// ── IP-based guest tracking ──
$sql = "SELECT id, ip_address, ai_message_count, first_seen_at, last_seen_at, distinct_days, last_day_counted, registered_user_id, registered_at
        FROM guest_usage ORDER BY last_seen_at DESC LIMIT 100";
$result = $conn->query($sql);
$ip_rows = array();
if ($result) { while ($row = $result->fetch_assoc()) { $ip_rows[] = $row; } }

$count_result = $conn->query("SELECT COUNT(*) as total FROM guest_usage");
$ip_total = 0;
if ($count_result && $r = $count_result->fetch_assoc()) { $ip_total = intval($r['total']); }

// ── Per-user visit day tracking ──
$sql2 = "SELECT uvd.user_id, uvd.distinct_days, uvd.last_day_counted, uvd.first_visit_at, uvd.last_visit_at,
                u.email, u.display_name
         FROM user_visit_days uvd
         LEFT JOIN users u ON u.id = uvd.user_id
         ORDER BY uvd.last_visit_at DESC LIMIT 100";
$result2 = $conn->query($sql2);
$user_rows = array();
if ($result2) { while ($row2 = $result2->fetch_assoc()) { $user_rows[] = $row2; } }

$count2 = $conn->query("SELECT COUNT(*) as total FROM user_visit_days");
$user_total = 0;
if ($count2 && $r2 = $count2->fetch_assoc()) { $user_total = intval($r2['total']); }

// ── Recent clicks (last 50) ──
$sql3 = "SELECT cl.id, cl.ip_address, cl.user_id, cl.click_type, cl.page, cl.target_url, cl.target_title, cl.target_id, cl.clicked_at,
                u.email, u.display_name
         FROM click_log cl
         LEFT JOIN users u ON u.id = cl.user_id
         ORDER BY cl.clicked_at DESC LIMIT 50";
$result3 = $conn->query($sql3);
$click_rows = array();
if ($result3) { while ($row3 = $result3->fetch_assoc()) { $click_rows[] = $row3; } }

$count3 = $conn->query("SELECT COUNT(*) as total FROM click_log");
$click_total = 0;
if ($count3 && $r3 = $count3->fetch_assoc()) { $click_total = intval($r3['total']); }

// ── Page views (aggregated by IP+page, sorted by visit_count) ──
$sql4 = "SELECT pvl.ip_address, pvl.user_id, pvl.page, pvl.page_url, pvl.visit_count, pvl.first_visit_at, pvl.last_visit_at,
                u.email, u.display_name
         FROM page_view_log pvl
         LEFT JOIN users u ON u.id = pvl.user_id
         ORDER BY pvl.last_visit_at DESC LIMIT 100";
$result4 = $conn->query($sql4);
$pageview_rows = array();
if ($result4) { while ($row4 = $result4->fetch_assoc()) { $pageview_rows[] = $row4; } }

$count4 = $conn->query("SELECT COUNT(*) as total FROM page_view_log");
$pv_total = 0;
if ($count4 && $r4 = $count4->fetch_assoc()) { $pv_total = intval($r4['total']); }

// ── Click summary by type ──
$sql5 = "SELECT click_type, COUNT(*) as count FROM click_log GROUP BY click_type ORDER BY count DESC";
$result5 = $conn->query($sql5);
$click_summary = array();
if ($result5) { while ($row5 = $result5->fetch_assoc()) { $click_summary[] = $row5; } }

// ── Page view summary (visits per page) ──
$sql6 = "SELECT page, COUNT(DISTINCT ip_address) as unique_visitors, SUM(visit_count) as total_views
         FROM page_view_log GROUP BY page ORDER BY total_views DESC";
$result6 = $conn->query($sql6);
$pv_summary = array();
if ($result6) { while ($row6 = $result6->fetch_assoc()) { $pv_summary[] = $row6; } }

echo json_encode(array(
    'ok' => true,
    'ip_tracking' => array(
        'total' => $ip_total,
        'rows'  => $ip_rows
    ),
    'user_tracking' => array(
        'total' => $user_total,
        'rows'  => $user_rows
    ),
    'clicks' => array(
        'total'   => $click_total,
        'summary' => $click_summary,
        'recent'  => $click_rows
    ),
    'page_views' => array(
        'total'   => $pv_total,
        'summary' => $pv_summary,
        'rows'    => $pageview_rows
    )
));

$conn->close();
?>
