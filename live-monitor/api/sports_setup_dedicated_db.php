<?php
/**
 * One-time setup: Create schema + migrate data from stocks DB to dedicated sports DB.
 * Run once via URL then delete.
 * PHP 5.2 compatible.
 */
error_reporting(E_ALL);
ini_set('display_errors', '1');
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_config.php';

$out = array('ok' => true, 'steps' => array());

// ── Step 1: Connect to dedicated sports DB ──
// Use credentials from db_config.php (already loaded)
$sports = @new mysqli($sports_servername, $sports_username, $sports_password, $sports_dbname);
if ($sports->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Sports DB connection failed: ' . $sports->connect_error,
        'hint' => 'host=' . $sports_servername . ' user=' . $sports_username . ' db=' . $sports_dbname));
    exit;
}
$sports->set_charset('utf8');
$out['steps'][] = 'Connected to dedicated sports DB: ' . $sports_dbname . ' on ' . $sports_servername;

// ── Step 2: Create schema ──
require_once dirname(__FILE__) . '/sports_schema.php';
_sb_ensure_schema($sports);
$out['steps'][] = 'Schema created (7 core tables)';

// ML tables
$sports->query("CREATE TABLE IF NOT EXISTS lm_sports_ml_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    value_bet_id INT NOT NULL DEFAULT 0,
    event_id VARCHAR(100) NOT NULL,
    sport VARCHAR(50) NOT NULL DEFAULT '',
    home_team VARCHAR(100) NOT NULL DEFAULT '',
    away_team VARCHAR(100) NOT NULL DEFAULT '',
    market VARCHAR(20) NOT NULL DEFAULT 'h2h',
    outcome_name VARCHAR(100) NOT NULL DEFAULT '',
    best_odds DECIMAL(10,4) NOT NULL DEFAULT 0,
    ev_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    ml_win_prob DECIMAL(6,4) NOT NULL DEFAULT 0,
    ml_prediction VARCHAR(10) NOT NULL DEFAULT 'skip',
    ml_confidence VARCHAR(10) NOT NULL DEFAULT 'low',
    ml_should_bet TINYINT(1) NOT NULL DEFAULT 0,
    reasons TEXT,
    predicted_at DATETIME NOT NULL,
    KEY idx_event (event_id),
    KEY idx_sport (sport),
    KEY idx_ml_pred (ml_prediction),
    KEY idx_ml_prob (ml_win_prob),
    KEY idx_predicted (predicted_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$sports->query("CREATE TABLE IF NOT EXISTS lm_sports_ml_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metric_date DATE NOT NULL,
    model_type VARCHAR(50) NOT NULL DEFAULT 'ensemble',
    n_training_bets INT NOT NULL DEFAULT 0,
    accuracy DECIMAL(6,4) DEFAULT NULL,
    precision_score DECIMAL(6,4) DEFAULT NULL,
    recall_score DECIMAL(6,4) DEFAULT NULL,
    f1_score DECIMAL(6,4) DEFAULT NULL,
    auc_roc DECIMAL(6,4) DEFAULT NULL,
    brier_score DECIMAL(6,4) DEFAULT NULL,
    log_loss_val DECIMAL(8,4) DEFAULT NULL,
    feature_importance TEXT,
    notes TEXT,
    KEY idx_date (metric_date),
    KEY idx_model (model_type)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");
$out['steps'][] = 'ML tables created (2 ML tables)';

// ── Step 3: Check existing data in sports DB ──
$res = $sports->query("SELECT COUNT(*) AS c FROM lm_sports_bets");
$row = $res->fetch_assoc();
$existing = (int)$row['c'];

if ($existing > 0) {
    $out['steps'][] = 'Sports DB already has ' . $existing . ' bets — skipping migration';
    $out['migration'] = 'skipped';
    echo json_encode($out);
    exit;
}

// ── Step 4: Connect to stocks DB (source) ──
$stocks = new mysqli($servername, $username, $password, $dbname);
if ($stocks->connect_error) {
    $out['steps'][] = 'WARNING: Stocks DB connection failed: ' . $stocks->connect_error;
    $out['migration'] = 'failed';
    echo json_encode($out);
    exit;
}
$stocks->set_charset('utf8');
$out['steps'][] = 'Connected to source stocks DB for migration';

// ── Step 5: Migrate each table ──
$tables = array(
    'lm_sports_bets',
    'lm_sports_bankroll',
    'lm_sports_odds',
    'lm_sports_value_bets',
    'lm_sports_daily_picks',
    'lm_sports_clv',
    'lm_sports_credit_usage'
);

foreach ($tables as $tbl) {
    // Check if source table exists and has data
    $check = $stocks->query("SELECT COUNT(*) AS c FROM " . $tbl);
    if (!$check) {
        $out['steps'][] = $tbl . ': not found in stocks DB — skipped';
        continue;
    }
    $row = $check->fetch_assoc();
    $count = (int)$row['c'];
    if ($count === 0) {
        $out['steps'][] = $tbl . ': empty in stocks DB — skipped';
        continue;
    }

    // Get all rows
    $result = $stocks->query("SELECT * FROM " . $tbl);
    if (!$result) {
        $out['steps'][] = $tbl . ': query failed — ' . $stocks->error;
        continue;
    }

    $migrated = 0;
    while ($r = $result->fetch_assoc()) {
        $cols = array();
        $vals = array();
        foreach ($r as $col => $val) {
            if ($col === 'id') continue; // skip auto-increment
            $cols[] = '`' . $col . '`';
            if ($val === null) {
                $vals[] = 'NULL';
            } else {
                $vals[] = "'" . $sports->real_escape_string($val) . "'";
            }
        }
        $sql = "INSERT INTO " . $tbl . " (" . implode(',', $cols) . ") VALUES (" . implode(',', $vals) . ")";
        if ($sports->query($sql)) {
            $migrated++;
        }
    }
    $out['steps'][] = $tbl . ': migrated ' . $migrated . '/' . $count . ' rows';
}

$out['migration'] = 'completed';

// ── Step 6: Verify ──
$verify = $sports->query("SELECT COUNT(*) AS c FROM lm_sports_bets");
$vrow = $verify->fetch_assoc();
$out['verification'] = array(
    'bets_in_sports_db' => (int)$vrow['c']
);

$bankroll_check = $sports->query("SELECT COUNT(*) AS c FROM lm_sports_bankroll");
$brow = $bankroll_check->fetch_assoc();
$out['verification']['bankroll_snapshots'] = (int)$brow['c'];

$sports->close();
$stocks->close();

echo json_encode($out);
?>
