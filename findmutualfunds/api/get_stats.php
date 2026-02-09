<?php
/**
 * Operational statistics endpoint for Mutual Fund Portfolio system.
 * Returns DB health, refresh status, data freshness, audit trail.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

$stats = array('ok' => true);

// ─── Table row counts ───
$table_counts = array();
$tables = array('mf_funds', 'mf_nav_history', 'mf_strategies', 'mf_selections',
                'mf_portfolios', 'mf_backtest_results', 'mf_backtest_trades',
                'mf_whatif_scenarios', 'mf_benchmarks', 'mf_audit_log',
                'mf_report_cache', 'mf_simulation_grid', 'mf_simulation_meta');
foreach ($tables as $tbl) {
    $r = $conn->query("SELECT COUNT(*) as cnt FROM $tbl");
    if ($r && $row = $r->fetch_assoc()) $table_counts[$tbl] = (int)$row['cnt'];
    else $table_counts[$tbl] = 0;
}
$stats['table_counts'] = $table_counts;

// ─── Cache status ───
$caches = array();
$r = $conn->query("SELECT cache_key, updated_at, LENGTH(cache_data) as data_size FROM mf_report_cache ORDER BY updated_at DESC");
if ($r) { while ($row = $r->fetch_assoc()) $caches[] = $row; }
$stats['caches'] = $caches;

// ─── Data freshness ───
$freshness = array();
// Latest NAV date
$r = $conn->query("SELECT MAX(nav_date) as latest FROM mf_nav_history");
if ($r && $row = $r->fetch_assoc()) $freshness['latest_nav_date'] = $row['latest'];
// Funds with NAV data
$r = $conn->query("SELECT COUNT(DISTINCT ticker) as cnt FROM mf_nav_history");
if ($r && $row = $r->fetch_assoc()) $freshness['funds_with_nav'] = (int)$row['cnt'];
// Funds without NAV data
$r = $conn->query("SELECT COUNT(*) as cnt FROM mf_funds f WHERE NOT EXISTS (SELECT 1 FROM mf_nav_history n WHERE n.ticker=f.ticker)");
if ($r && $row = $r->fetch_assoc()) $freshness['funds_without_nav'] = (int)$row['cnt'];
// Latest selection date
$r = $conn->query("SELECT MAX(select_date) as latest FROM mf_selections");
if ($r && $row = $r->fetch_assoc()) $freshness['latest_selection_date'] = $row['latest'];
// Strategies with selections
$r = $conn->query("SELECT COUNT(DISTINCT strategy_name) as cnt FROM mf_selections");
if ($r && $row = $r->fetch_assoc()) $freshness['active_strategies'] = (int)$row['cnt'];
// Selections per strategy
$sps = array();
$r = $conn->query("SELECT strategy_name, COUNT(*) as cnt FROM mf_selections GROUP BY strategy_name ORDER BY cnt DESC");
if ($r) { while ($row = $r->fetch_assoc()) $sps[] = $row; }
$freshness['selections_per_strategy'] = $sps;
// Fund coverage
$fpc = array();
$r = $conn->query("SELECT f.ticker, f.fund_name, (SELECT COUNT(*) FROM mf_nav_history n WHERE n.ticker=f.ticker) as nav_count,
                    (SELECT MAX(nav_date) FROM mf_nav_history n WHERE n.ticker=f.ticker) as latest_nav
                    FROM mf_funds f ORDER BY f.ticker");
if ($r) { while ($row = $r->fetch_assoc()) $fpc[] = $row; }
$freshness['fund_coverage'] = $fpc;
$stats['freshness'] = $freshness;

// ─── Health indicators ───
$health = array();
$today = date('Y-m-d');
// Refreshed today?
$r = $conn->query("SELECT COUNT(*) as cnt FROM mf_audit_log WHERE action_type='daily_refresh' AND created_at >= '$today 00:00:00'");
$health['refreshed_today'] = ($r && $row = $r->fetch_assoc()) ? (int)$row['cnt'] > 0 : false;

// NAV staleness
$latest_nav = isset($freshness['latest_nav_date']) ? $freshness['latest_nav_date'] : '';
$days_since = ($latest_nav !== '' && $latest_nav !== null) ? (int)((time() - strtotime($latest_nav)) / 86400) : 999;
$health['nav_days_stale'] = $days_since;
$health['nav_status'] = ($days_since <= 3) ? 'fresh' : (($days_since <= 7) ? 'stale' : 'very_stale');

// Report cache age
$r = $conn->query("SELECT updated_at FROM mf_report_cache WHERE cache_key='daily_summary'");
$cache_age = 999;
if ($r && $row = $r->fetch_assoc()) {
    $cache_age = (int)((time() - strtotime($row['updated_at'])) / 3600);
}
$health['report_cache_hours_old'] = $cache_age;
$health['report_status'] = ($cache_age <= 24) ? 'fresh' : (($cache_age <= 72) ? 'stale' : 'very_stale');

$stats['health'] = $health;

// ─── Audit log ───
$recent_audits = array();
$r = $conn->query("SELECT * FROM mf_audit_log ORDER BY created_at DESC LIMIT 20");
if ($r) { while ($row = $r->fetch_assoc()) $recent_audits[] = $row; }
$stats['recent_audits'] = $recent_audits;

// Audit summary
$audit_summary = array();
$r = $conn->query("SELECT action_type, COUNT(*) as cnt, MAX(created_at) as latest FROM mf_audit_log GROUP BY action_type ORDER BY latest DESC");
if ($r) { while ($row = $r->fetch_assoc()) $audit_summary[] = $row; }
$stats['audit_summary'] = $audit_summary;

// ─── Last refresh snapshot ───
$r = $conn->query("SELECT cache_data FROM mf_report_cache WHERE cache_key='stats_snapshot'");
if ($r && $row = $r->fetch_assoc()) {
    $snap = json_decode($row['cache_data'], true);
    if ($snap) $stats['last_refresh'] = $snap;
}

echo json_encode($stats);
$conn->close();
?>
