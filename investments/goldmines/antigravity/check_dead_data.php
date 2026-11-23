<?php
/**
 * Dead Data Detection Script
 * Checks all prediction systems for stale data and broken pipelines
 * Run via: php check_dead_data.php
 */

// Database configuration.
// PHP 5.2 / credential fix (2026-11-23): this file previously shipped the
// template placeholders ($db_user='root', $db_pass='', $db_name='your_database')
// which can never authenticate on the live host, so every run died with
//   Access denied for user 'root'@'localhost' (using password: NO)
// Use the shared connector instead; it reads the FTP-deployed, gitignored .env
// that already holds the current password.
require_once dirname(__FILE__) . '/../../../findforex2/portfolio/api/db_connect.php';
if (!isset($conn) || !$conn) {
    die("Connection failed: no database handle from db_connect.php\n");
}

// Define all prediction systems to check
$systems = array(
    'crypto_winners' => array(
        'name' => 'Crypto Winner Scanner',
        'table' => 'cw_winners',
        'timestamp_col' => 'created_at',
        'max_age_hours' => 24,
        'url' => '/findcryptopairs/api/crypto_winners.php?action=winners'
    ),
    'meme_scanner' => array(
        'name' => 'Meme Coin Scanner',
        'table' => 'mc_winners',
        'timestamp_col' => 'created_at',
        'max_age_hours' => 24,
        'url' => '/findcryptopairs/api/meme_scanner.php?action=winners'
    ),
    'sports_picks' => array(
        'name' => 'Sports Betting Picks',
        'table' => 'sports_picks',
        'timestamp_col' => 'generated_at',
        'max_age_hours' => 48,
        // Served from a static JSON file, not a database table. Checking it for
        // rows produced a permanent false 'Table does not exist' CRITICAL alert.
        'db_backed' => false,
        'source' => 'static JSON feed (no database)',
        'url' => '/live-monitor/api/sports_picks.php'
    ),
    'stock_intel' => array(
        'name' => 'Stock Intelligence',
        'table' => 'stock_picks',
        'timestamp_col' => 'pick_date',
        'max_age_hours' => 72,
        'url' => '/findstocks/portfolio2/api/stock_intel.php'
    ),
    'penny_stocks' => array(
        'name' => 'Penny Stocks',
        'table' => 'penny_stocks',
        'timestamp_col' => 'last_updated',
        'max_age_hours' => 72,
        // penny_stocks.php proxies the Yahoo Finance screener and touches no
        // database at all, so every freshness query against it was a false alarm.
        'db_backed' => false,
        'source' => 'Yahoo Finance screener proxy (no database)',
        'url' => '/findstocks/portfolio2/api/penny_stocks.php'
    ),
    'forex_insights' => array(
        'name' => 'Forex Insights',
        'table' => 'fxp_price_history',
        'timestamp_col' => 'timestamp',
        'max_age_hours' => 24,
        'url' => '/findforex2/portfolio/api/forex_insights.php?action=market_overview'
    ),
    'mutual_funds' => array(
        'name' => 'Mutual Funds',
        'table' => 'mf2_fund_picks',
        'timestamp_col' => 'pick_date',
        'max_age_hours' => 168, // 1 week
        'url' => '/findmutualfunds2/portfolio2/api/data.php?type=stats',
        // 2026-11-23: neither `mf2_fund_picks` nor its universe table `mf2_funds`
        // has a writer in this repo OR the Windows source tree. With no fund
        // universe there is nothing to generate picks from, so no writer can be
        // restored -- only invented, which would be fabrication. The table holds
        // 600 historical rows and the app was superseded by the /audit equity
        // surface. Reporting this as STALE forever raised a permanent alert that
        // no action could ever clear; DECOMMISSIONED is the truthful status.
        'decommissioned' => true,
        'decommissioned_reason' => 'No upstream source: mf2_funds has no writer, so there is no fund universe to generate picks from'
    )
);

$results = array();
$alerts = array();
$now = time();

echo "=== ANTIGRAVITY PREDICTION SYSTEMS - DEAD DATA CHECK ===\n";
echo "Timestamp: " . date('Y-m-d H:i:s') . "\n\n";

foreach ($systems as $key => $config) {
    echo "Checking: {$config['name']}...\n";
    
    $result = array(
        'system' => $config['name'],
        'status' => 'unknown',
        'last_update' => null,
        'hours_ago' => null,
        'record_count' => 0,
        'is_stale' => false
    );
    
    // A decommissioned system has a table and historical rows but no upstream
    // producer. Freshness is not a meaningful question for it, and no amount of
    // waiting will ever clear a staleness alert -- so it is reported as its own
    // status rather than as dead data.
    if (!empty($config['decommissioned'])) {
        $result['status'] = 'DECOMMISSIONED';
        $result['is_stale'] = false;
        $result['source'] = isset($config['decommissioned_reason']) ? $config['decommissioned_reason'] : 'decommissioned';
        $results[] = $result;
        echo "  - Decommissioned (" . $result['source'] . ") - not an alert\n\n";
        continue;
    }

    // Systems with no database behind them cannot be assessed for data freshness.
    // Saying so is the correct answer; querying a non-existent table and raising
    // CRITICAL is a false alarm (see the db_backed note in the config above).
    if (isset($config['db_backed']) && $config['db_backed'] === false) {
        $result['status'] = 'NOT_DB_BACKED';
        $result['is_stale'] = false;
        $result['source'] = isset($config['source']) ? $config['source'] : 'no database';
        $results[] = $result;
        echo "  ℹ️ Not database-backed (" . $result['source'] . ") - skipped\n\n";
        continue;
    }

    // Check if table exists
    $table_check = $conn->query("SHOW TABLES LIKE '{$config['table']}'");
    if ($table_check->num_rows === 0) {
        $result['status'] = 'TABLE_NOT_FOUND';
        $result['is_stale'] = true;
        $alerts[] = "⚠️ CRITICAL: {$config['name']} - Table '{$config['table']}' does not exist!";
        $results[] = $result;
        echo "  ❌ Table not found!\n\n";
        continue;
    }
    
    // Get total record count.
    // MySQL returns COUNT(*) as a STRING, and the empty-table test below uses
    // `=== 0`, so without this cast that branch was dead code: an empty table
    // fell through to the timestamp check and was reported as "no timestamp"
    // instead of "table is empty". Cast once, here.
    $count_sql = "SELECT COUNT(*) as total FROM {$config['table']}";
    $count_result = $conn->query($count_sql);
    if ($count_result) {
        $count_row = $count_result->fetch_assoc();
        $result['record_count'] = (int)$count_row['total'];
    }
    
    // Check for empty table
    if ($result['record_count'] === 0) {
        $result['status'] = 'EMPTY_TABLE';
        $result['is_stale'] = true;
        $alerts[] = "⚠️ WARNING: {$config['name']} - Table is empty (0 records)";
        $results[] = $result;
        echo "  ⚠️ Table is empty!\n\n";
        continue;
    }
    
    // Auto-detect the timestamp column instead of trusting a hardcoded name.
    // Every remaining false alarm in this checker came from schema drift: it asked
    // for 'timestamp' on fxp_price_history and 'last_updated' on tables that never
    // had those columns, then reported the resulting SQL error as data staleness.
    $ts_candidates = array(
        $config['timestamp_col'], 'created_at', 'updated_at', 'pick_date',
        'price_date', 'scan_date', 'snapshot_date', 'trade_date', 'as_of_date',
        'bar_date', 'end_date', 'generated_at', 'scan_time', 'timestamp',
        'last_updated', 'date'
    );
    $available_cols = array();
    $cols_result = $conn->query("SHOW COLUMNS FROM {$config['table']}");
    if ($cols_result) {
        while ($col = $cols_result->fetch_assoc()) {
            $available_cols[] = $col['Field'];
        }
    }
    // Only consider columns that actually exist, in preference order.
    $present_candidates = array();
    foreach ($ts_candidates as $cand) {
        if (in_array($cand, $available_cols) && !in_array($cand, $present_candidates)) {
            $present_candidates[] = $cand;
        }
    }
    if (count($present_candidates) === 0) {
        $result['status'] = 'NO_TIMESTAMP_COLUMN';
        $result['is_stale'] = true;
        $result['available_columns'] = array_slice($available_cols, 0, 8);
        $alerts[] = "⚠️ WARNING: {$config['name']} - no recognised timestamp column in '{$config['table']}'";
        $results[] = $result;
        echo "  ⚠️ No timestamp column (has: " . implode(', ', array_slice($available_cols, 0, 6)) . ")\n\n";
        continue;
    }

    // Try each candidate until one actually holds a value. A column can exist and
    // still be entirely NULL (e.g. created_at on rows written by a different path),
    // in which case reporting "no timestamp" while a populated date column sits
    // right next to it would be another false alarm.
    $ts_col = null;
    $last_value = null;
    $tried_cols = array();
    $last_query_error = null;
    foreach ($present_candidates as $cand) {
        $tried_cols[] = $cand;
        $try_sql = "SELECT MAX({$cand}) as last_update FROM {$config['table']}";
        $try_result = $conn->query($try_sql);
        if (!$try_result) {
            $last_query_error = $conn->error;
            continue;
        }
        $try_row = $try_result->fetch_assoc();
        if ($try_row && $try_row['last_update']) {
            $ts_col = $cand;
            $last_value = $try_row['last_update'];
            break;
        }
    }

    if ($ts_col === null) {
        $result['status'] = ($last_query_error === null) ? 'NO_TIMESTAMP' : 'QUERY_ERROR';
        $result['is_stale'] = true;
        $result['timestamp_columns_tried'] = $tried_cols;
        if ($last_query_error === null) {
            // Distinguish 'no rows' from 'rows exist but every date is NULL'.
            // Without this the message was ambiguous and could not be acted on.
            $probe_note = '';
            if (count($tried_cols) > 0) {
                $probe = $conn->query("SELECT COUNT({$tried_cols[0]}) as nn FROM {$config['table']}");
                $probe_row = $probe ? $probe->fetch_assoc() : null;
                if ($probe_row) {
                    $probe_note = ' [rows=' . $result['record_count'] . ', non_null_' . $tried_cols[0] . '=' . $probe_row['nn'] . ']';
                    $result['null_probe'] = array('rows' => (int)$result['record_count'],
                                                  'column' => $tried_cols[0],
                                                  'non_null' => (int)$probe_row['nn']);
                }
            }
            $alerts[] = "⚠️ WARNING: {$config['name']} - all date columns are NULL (" . implode(', ', $tried_cols) . ")" . $probe_note;
            echo "  ⚠️ All date columns NULL (tried: " . implode(', ', $tried_cols) . ")" . $probe_note . "\n\n";
        } else {
            $alerts[] = "⚠️ ERROR: {$config['name']} - Query failed: " . $last_query_error;
            echo "  ❌ Query error!\n\n";
        }
        $results[] = $result;
        continue;
    }
    $result['timestamp_col_used'] = $ts_col;

    $last_update_ts = strtotime($last_value);
    $hours_ago = ($now - $last_update_ts) / 3600;
    
    $result['last_update'] = $row['last_update'];
    $result['hours_ago'] = round($hours_ago, 2);
    
    if ($hours_ago > $config['max_age_hours']) {
        $result['status'] = 'STALE';
        $result['is_stale'] = true;
        $alerts[] = "🚨 DEAD DATA: {$config['name']} has no updates in {$result['hours_ago']} hours (threshold: {$config['max_age_hours']}h)";
        echo "  🚨 STALE DATA! Last update: {$result['hours_ago']} hours ago\n";
    } else {
        $result['status'] = 'ACTIVE';
        echo "  ✅ Active - Last update: {$result['hours_ago']} hours ago\n";
    }
    
    echo "  Records: {$result['record_count']}\n\n";
    $results[] = $result;
}

$conn->close();

// Summary
// Counts must reconcile: skipped systems used to fall into neither the active nor
// the stale bucket while still being counted in the total, so '5 stale of 7' hid
// two systems that were simply never assessed.
echo "\n=== SUMMARY ===\n";
$active_count = 0;
$stale_count = 0;
$skipped_count = 0;
$decommissioned_count = 0;

foreach ($results as $r) {
    if ($r['status'] === 'ACTIVE') $active_count++;
    elseif ($r['status'] === 'NOT_DB_BACKED') $skipped_count++;
    elseif ($r['status'] === 'DECOMMISSIONED') $decommissioned_count++;
    elseif ($r['is_stale']) $stale_count++;
}

echo "Active Systems: $active_count\n";
echo "Stale/Dead Systems: $stale_count\n";
echo "Skipped (no database): $skipped_count\n";
echo "Decommissioned (no upstream source): $decommissioned_count\n";
echo "Total Systems Checked: " . count($results) . " (" . $active_count . " active + " . $stale_count . " stale + " . $skipped_count . " skipped + " . $decommissioned_count . " decommissioned)\n\n";

if (count($alerts) > 0) {
    echo "=== ALERTS ===\n";
    foreach ($alerts as $alert) {
        echo "$alert\n";
    }
    echo "\n";
}

// Export JSON report
$report = array(
    'timestamp' => date('Y-m-d H:i:s'),
    'summary' => array(
        'total_systems' => count($results),
        'active' => $active_count,
        'stale' => $stale_count,
        'skipped' => $skipped_count,
        'decommissioned' => $decommissioned_count
    ),
    'systems' => $results,
    'alerts' => $alerts
);

// One overwritten report instead of a new dated file per run: the dated files
// accumulated inside a web-served directory, and fetching them back returned
// 200/0 bytes or 404 -- so the old "Report saved to: ..." line was not a claim
// anyone could check. Also JSON_PRETTY_PRINT is PHP 5.4+ and this host is 5.2.
$json_file = dirname(__FILE__) . '/dead_data_report.json';
$encoded = json_encode($report);
$written = false;
if ($encoded !== false) {
    $written = @file_put_contents($json_file, $encoded);
}
if ($written === false || $written === 0) {
    echo "Report NOT saved: write failed for $json_file (directory may not be writable)\n";
} else {
    echo "Report saved: $json_file ($written bytes)\n";
}

// Exit code: 0 if all active, 1 if any stale
exit($stale_count > 0 ? 1 : 0);
