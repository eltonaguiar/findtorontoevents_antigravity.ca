<?php
/**
 * Dead Data Detection Script
 * Checks all prediction systems for stale data and broken pipelines
 * Run via: php check_dead_data.php
 */

// Database configuration - update with your credentials
$db_host = 'localhost';
$db_user = 'root';
$db_pass = '';
$db_name = 'your_database';

$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Define all prediction systems to check
$systems = [
    'crypto_winners' => [
        'name' => 'Crypto Winner Scanner',
        'table' => 'cw_winners',
        'timestamp_col' => 'created_at',
        'max_age_hours' => 24,
        'url' => '/findcryptopairs/api/crypto_winners.php?action=winners'
    ],
    'meme_scanner' => [
        'name' => 'Meme Coin Scanner',
        'table' => 'mc_winners',
        'timestamp_col' => 'created_at',
        'max_age_hours' => 24,
        'url' => '/findcryptopairs/api/meme_scanner.php?action=winners'
    ],
    'sports_picks' => [
        'name' => 'Sports Betting Picks',
        'table' => 'sports_picks',
        'timestamp_col' => 'generated_at',
        'max_age_hours' => 48,
        'url' => '/live-monitor/api/sports_picks.php'
    ],
    'stock_intel' => [
        'name' => 'Stock Intelligence',
        'table' => 'stock_picks',
        'timestamp_col' => 'pick_date',
        'max_age_hours' => 72,
        'url' => '/findstocks/portfolio2/api/stock_intel.php'
    ],
    'penny_stocks' => [
        'name' => 'Penny Stocks',
        'table' => 'penny_stocks',
        'timestamp_col' => 'last_updated',
        'max_age_hours' => 72,
        'url' => '/findstocks/portfolio2/api/penny_stocks.php'
    ],
    'forex_insights' => [
        'name' => 'Forex Insights',
        'table' => 'fxp_price_history',
        'timestamp_col' => 'timestamp',
        'max_age_hours' => 24,
        'url' => '/findforex2/portfolio/api/forex_insights.php?action=market_overview'
    ],
    'mutual_funds' => [
        'name' => 'Mutual Funds',
        'table' => 'mf2_fund_picks',
        'timestamp_col' => 'pick_date',
        'max_age_hours' => 168, // 1 week
        'url' => '/findmutualfunds2/portfolio2/api/data.php?type=stats'
    ]
];

$results = [];
$alerts = [];
$now = time();

echo "=== ANTIGRAVITY PREDICTION SYSTEMS - DEAD DATA CHECK ===\n";
echo "Timestamp: " . date('Y-m-d H:i:s') . "\n\n";

foreach ($systems as $key => $config) {
    echo "Checking: {$config['name']}...\n";
    
    $result = [
        'system' => $config['name'],
        'status' => 'unknown',
        'last_update' => null,
        'hours_ago' => null,
        'record_count' => 0,
        'is_stale' => false
    ];
    
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
    
    // Get total record count
    $count_sql = "SELECT COUNT(*) as total FROM {$config['table']}";
    $count_result = $conn->query($count_sql);
    if ($count_result) {
        $count_row = $count_result->fetch_assoc();
        $result['record_count'] = $count_row['total'];
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
    
    // Get last update timestamp
    $sql = "SELECT MAX({$config['timestamp_col']}) as last_update FROM {$config['table']}";
    $query_result = $conn->query($sql);
    
    if (!$query_result) {
        $result['status'] = 'QUERY_ERROR';
        $result['is_stale'] = true;
        $alerts[] = "⚠️ ERROR: {$config['name']} - Query failed: " . $conn->error;
        $results[] = $result;
        echo "  ❌ Query error!\n\n";
        continue;
    }
    
    $row = $query_result->fetch_assoc();
    if (!$row || !$row['last_update']) {
        $result['status'] = 'NO_TIMESTAMP';
        $result['is_stale'] = true;
        $alerts[] = "⚠️ WARNING: {$config['name']} - No valid timestamp found";
        $results[] = $result;
        echo "  ⚠️ No timestamp!\n\n";
        continue;
    }
    
    $last_update_ts = strtotime($row['last_update']);
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
echo "\n=== SUMMARY ===\n";
$active_count = 0;
$stale_count = 0;

foreach ($results as $r) {
    if ($r['status'] === 'ACTIVE') $active_count++;
    elseif ($r['is_stale']) $stale_count++;
}

echo "Active Systems: $active_count\n";
echo "Stale/Dead Systems: $stale_count\n";
echo "Total Systems Checked: " . count($results) . "\n\n";

if (count($alerts) > 0) {
    echo "=== ALERTS ===\n";
    foreach ($alerts as $alert) {
        echo "$alert\n";
    }
    echo "\n";
}

// Export JSON report
$report = [
    'timestamp' => date('Y-m-d H:i:s'),
    'summary' => [
        'total_systems' => count($results),
        'active' => $active_count,
        'stale' => $stale_count
    ],
    'systems' => $results,
    'alerts' => $alerts
];

$json_file = __DIR__ . '/dead_data_report_' . date('Ymd_His') . '.json';
file_put_contents($json_file, json_encode($report, JSON_PRETTY_PRINT));
echo "Report saved to: $json_file\n";

// Exit code: 0 if all active, 1 if any stale
exit($stale_count > 0 ? 1 : 0);
