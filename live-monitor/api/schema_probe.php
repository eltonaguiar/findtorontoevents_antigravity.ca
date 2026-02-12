&lt;?php
/**
 * schema_probe.php — Remote DB schema verifier for OPUS46 analysis.
 * Dumps table list and key structures. PHP 5.2 compatible.
 */

// Load DB connection (assume shared config)
require_once __DIR__ . '/../../favcreators/public/api/config.php'; // Adjust if needed

// Key tables to probe
$key_tables = array(
    'lm_signals', 'lm_trades', 'lm_market_regime', 'lm_kelly_fractions',
    'daily_prices', 'algo_performance', 'lm_algo_health', 'gm_unified_picks'
);

$output = array();

// List all tables
$r = $conn->query("SHOW TABLES");
if ($r) {
    $all_tables = array();
    while ($row = $r->fetch_row()) {
        $all_tables[] = $row[0];
    }
    $output['all_tables'] = $all_tables;
}

// Describe key tables
foreach ($key_tables as $table) {
    $exists = in_array($table, $all_tables);
    $output[$table] = array('exists' => $exists);
    
    if ($exists) {
        $desc = $conn->query("DESCRIBE $table");
        if ($desc) {
            $structure = array();
            while ($col = $desc->fetch_assoc()) {
                $structure[] = $col;
            }
            $output[$table]['structure'] = $structure;
        }
    }
}

header('Content-Type: application/json');
echo json_encode($output);

$conn->close();
?&gt;