<?php
/**
 * setup_sportsbet_tables.php — Migration script to add ML fields to lm_sports_bets
 * PHP 5.2 compatible.
 *
 * Usage: Run via HTTP: https://findtorontoevents.ca/live-monitor/api/setup_sportsbet_tables.php
 * Or via CLI: php setup_sportsbet_tables.php
 *
 * This script safely adds ML prediction fields to the lm_sports_bets table.
 * It checks if columns exist before adding them, so it's safe to run multiple times.
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';
require_once dirname(__FILE__) . '/sports_schema.php';

// Ensure base schema exists
_sb_ensure_schema($conn);

header('Content-Type: application/json');

$results = array();
$errors = array();

// Helper function to check if column exists
function _column_exists($conn, $table, $column)
{
    $check = $conn->query("SHOW COLUMNS FROM " . $conn->real_escape_string($table) . " LIKE '" . $conn->real_escape_string($column) . "'");
    return ($check && $check->num_rows > 0);
}

// ── Add ML fields to lm_sports_bets ──
$ml_fields = array(
    array(
        'name' => 'ml_win_prob',
        'definition' => 'DECIMAL(6,4) NOT NULL DEFAULT 0.5000',
        'after' => 'ev_pct'
    ),
    array(
        'name' => 'ml_prediction',
        'definition' => "VARCHAR(20) NOT NULL DEFAULT 'lean'",
        'after' => 'ml_win_prob'
    ),
    array(
        'name' => 'ml_confidence',
        'definition' => "VARCHAR(20) NOT NULL DEFAULT 'low'",
        'after' => 'ml_prediction'
    ),
    array(
        'name' => 'ml_should_bet',
        'definition' => 'TINYINT NOT NULL DEFAULT 0',
        'after' => 'ml_confidence'
    ),
    array(
        'name' => 'ml_model_type',
        'definition' => "VARCHAR(50) NOT NULL DEFAULT 'baseline'",
        'after' => 'ml_should_bet'
    ),
    array(
        'name' => 'ml_predicted_at',
        'definition' => 'DATETIME DEFAULT NULL',
        'after' => 'ml_model_type'
    )
);

foreach ($ml_fields as $field) {
    if (!_column_exists($conn, 'lm_sports_bets', $field['name'])) {
        $sql = "ALTER TABLE lm_sports_bets ADD COLUMN " . $field['name'] . " " . $field['definition'];
        if (isset($field['after'])) {
            $sql .= " AFTER " . $field['after'];
        }

        if ($conn->query($sql)) {
            $results[] = "Added column: " . $field['name'];
        } else {
            $errors[] = "Failed to add column " . $field['name'] . ": " . $conn->error;
        }
    } else {
        $results[] = "Column already exists: " . $field['name'];
    }
}

// ── Add indexes for ML fields ──
$ml_indexes = array(
    array('name' => 'idx_ml_prediction', 'columns' => 'ml_prediction'),
    array('name' => 'idx_ml_win_prob', 'columns' => 'ml_win_prob'),
    array('name' => 'idx_ml_should_bet', 'columns' => 'ml_should_bet')
);

foreach ($ml_indexes as $idx) {
    // Check if index exists
    $check_idx = $conn->query("SHOW INDEX FROM lm_sports_bets WHERE Key_name = '" . $conn->real_escape_string($idx['name']) . "'");
    if (!$check_idx || $check_idx->num_rows === 0) {
        $sql = "ALTER TABLE lm_sports_bets ADD KEY " . $idx['name'] . " (" . $idx['columns'] . ")";
        if ($conn->query($sql)) {
            $results[] = "Added index: " . $idx['name'];
        } else {
            $errors[] = "Failed to add index " . $idx['name'] . ": " . $conn->error;
        }
    } else {
        $results[] = "Index already exists: " . $idx['name'];
    }
}

// ── Output results ──
$output = array(
    'ok' => (count($errors) === 0),
    'migration' => 'sports_schema_ml_migration',
    'table' => 'lm_sports_bets',
    'results' => $results
);

if (count($errors) > 0) {
    $output['errors'] = $errors;
}

echo json_encode($output, JSON_PRETTY_PRINT);

$conn->close();
?>