<?php
/**
 * Sports Data Bridge
 *
 * Bridges data from the unified lm_sports_odds table (populated by The Odds API)
 * into the individual sport-specific tables that the ML pipeline expects.
 * Also computes sports ML metrics from settled bets.
 *
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=bridge      — Copy odds from lm_sports_odds to individual sport tables
 *   ?action=ml_metrics   — Compute and store sports ML performance metrics
 *   ?action=status       — Show current sports data status
 */

error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

// Connect to sportsbet DB
$sb_conn = new mysqli('mysql.50webs.com', 'ejaguiar1_sportsbet', 'wannabet', 'ejaguiar1_sportsbet');
if ($sb_conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Sportsbet DB connection failed'));
    exit;
}
$sb_conn->set_charset('utf8');

$action = isset($_GET['action']) ? $_GET['action'] : 'status';

switch ($action) {
    case 'bridge':     _sdb_bridge($sb_conn); break;
    case 'ml_metrics': _sdb_ml_metrics($sb_conn); break;
    case 'status':     _sdb_status($sb_conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}
$sb_conn->close();

// ═══════════════════════════════════════════════════════════════
//  BRIDGE: Copy unified odds to individual sport tables
// ═══════════════════════════════════════════════════════════════
function _sdb_bridge($conn) {
    $sport_map = array(
        'basketball_nba' => 'lm_nba_odds',
        'icehockey_nhl'  => 'lm_nhl_odds',
        'americanfootball_nfl' => 'lm_nfl_odds',
        'baseball_mlb'   => 'lm_mlb_odds'
    );

    // Ensure target tables exist
    foreach ($sport_map as $sport_key => $table) {
        $conn->query("CREATE TABLE IF NOT EXISTS " . $table . " (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_id VARCHAR(100) DEFAULT '',
            home_team VARCHAR(100) DEFAULT '',
            away_team VARCHAR(100) DEFAULT '',
            commence_time DATETIME,
            bookmaker VARCHAR(50) DEFAULT '',
            market VARCHAR(30) DEFAULT 'h2h',
            home_odds FLOAT DEFAULT 0,
            away_odds FLOAT DEFAULT 0,
            draw_odds FLOAT DEFAULT 0,
            spread_home FLOAT DEFAULT 0,
            spread_away FLOAT DEFAULT 0,
            total_over FLOAT DEFAULT 0,
            total_under FLOAT DEFAULT 0,
            fetched_at DATETIME,
            KEY event_idx (event_id),
            KEY team_idx (home_team)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }

    $copied = array();
    foreach ($sport_map as $sport_key => $table) {
        $count = 0;
        // Get recent odds from unified table
        $r = $conn->query("SELECT * FROM lm_sports_odds WHERE sport_key LIKE '%" . $conn->real_escape_string($sport_key) . "%' ORDER BY id DESC LIMIT 500");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                // Check duplicate
                $eid = isset($row['event_id']) ? $conn->real_escape_string($row['event_id']) : '';
                $bk = isset($row['bookmaker']) ? $conn->real_escape_string($row['bookmaker']) : '';
                $dup = $conn->query("SELECT id FROM " . $table . " WHERE event_id='" . $eid . "' AND bookmaker='" . $bk . "' LIMIT 1");
                if ($dup && $dup->num_rows > 0) continue;

                $conn->query(sprintf(
                    "INSERT INTO %s (event_id, home_team, away_team, commence_time, bookmaker, market,
                     home_odds, away_odds, draw_odds, fetched_at) VALUES ('%s','%s','%s','%s','%s','%s',%.4f,%.4f,%.4f,'%s')",
                    $table,
                    $eid,
                    $conn->real_escape_string(isset($row['home_team']) ? $row['home_team'] : ''),
                    $conn->real_escape_string(isset($row['away_team']) ? $row['away_team'] : ''),
                    $conn->real_escape_string(isset($row['commence_time']) ? $row['commence_time'] : ''),
                    $bk,
                    $conn->real_escape_string(isset($row['market']) ? $row['market'] : 'h2h'),
                    isset($row['home_odds']) ? (float)$row['home_odds'] : 0,
                    isset($row['away_odds']) ? (float)$row['away_odds'] : 0,
                    isset($row['draw_odds']) ? (float)$row['draw_odds'] : 0,
                    date('Y-m-d H:i:s')
                ));
                $count++;
            }
        }
        $copied[$table] = $count;
    }

    echo json_encode(array('ok' => true, 'bridged' => $copied));
}

// ═══════════════════════════════════════════════════════════════
//  ML METRICS: Compute sports ML performance
// ═══════════════════════════════════════════════════════════════
function _sdb_ml_metrics($conn) {
    // Calculate from settled bets + ML predictions
    $now = date('Y-m-d H:i:s');
    $today = date('Y-m-d');

    // Count predictions and outcomes
    $total = 0; $correct = 0; $n_bets = 0;
    $r = $conn->query("SELECT COUNT(*) as cnt, 
        SUM(CASE WHEN ml_prediction IS NOT NULL THEN 1 ELSE 0 END) as with_pred
        FROM lm_sports_ml_predictions");
    if ($r) {
        $row = $r->fetch_assoc();
        $total = (int)$row['cnt'];
    }

    // CLV analysis
    $avg_clv = 0; $pos_clv = 0; $clv_total = 0;
    $r = $conn->query("SELECT AVG(clv_pct) as avg_clv,
        SUM(CASE WHEN clv_pct > 0 THEN 1 ELSE 0 END) as pos,
        COUNT(*) as cnt FROM lm_sports_clv WHERE clv_pct IS NOT NULL");
    if ($r) {
        $row = $r->fetch_assoc();
        $avg_clv = (float)$row['avg_clv'];
        $pos_clv = (int)$row['pos'];
        $clv_total = (int)$row['cnt'];
    }

    // Settled bets
    $settled = 0; $won = 0; $total_pnl = 0;
    $r = $conn->query("SELECT COUNT(*) as cnt,
        SUM(CASE WHEN result='WON' THEN 1 ELSE 0 END) as won,
        SUM(profit_loss) as pnl FROM lm_sports_bets WHERE result IN ('WON','LOST')");
    if ($r) {
        $row = $r->fetch_assoc();
        $settled = (int)$row['cnt'];
        $won = (int)$row['won'];
        $total_pnl = (float)$row['pnl'];
    }

    // Insert/update metrics
    $conn->query("CREATE TABLE IF NOT EXISTS lm_sports_ml_metrics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        metric_date DATE NOT NULL,
        model_type VARCHAR(50) DEFAULT 'ensemble',
        n_training_bets INT DEFAULT 0,
        accuracy FLOAT DEFAULT 0,
        avg_clv FLOAT DEFAULT 0,
        positive_clv_pct FLOAT DEFAULT 0,
        settled_bets INT DEFAULT 0,
        won_bets INT DEFAULT 0,
        win_rate FLOAT DEFAULT 0,
        total_pnl FLOAT DEFAULT 0,
        notes TEXT,
        recorded_at DATETIME,
        UNIQUE KEY date_model (metric_date, model_type)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    $wr = ($settled > 0) ? round($won / $settled * 100, 1) : 0;
    $pos_clv_pct = ($clv_total > 0) ? round($pos_clv / $clv_total * 100, 1) : 0;

    $conn->query(sprintf(
        "REPLACE INTO lm_sports_ml_metrics (metric_date, model_type, n_training_bets, accuracy,
         avg_clv, positive_clv_pct, settled_bets, won_bets, win_rate, total_pnl, recorded_at)
         VALUES ('%s','ensemble',%d,0,%.4f,%.1f,%d,%d,%.1f,%.2f,'%s')",
        $today, $total, $avg_clv, $pos_clv_pct, $settled, $won, $wr, $total_pnl, $now
    ));

    echo json_encode(array(
        'ok' => true,
        'date' => $today,
        'ml_predictions' => $total,
        'clv' => array('avg' => round($avg_clv, 4), 'positive_pct' => $pos_clv_pct, 'total' => $clv_total),
        'bets' => array('settled' => $settled, 'won' => $won, 'win_rate' => $wr, 'pnl' => $total_pnl)
    ));
}

// ═══════════════════════════════════════════════════════════════
//  STATUS: Current sports data overview
// ═══════════════════════════════════════════════════════════════
function _sdb_status($conn) {
    $tables = array(
        'lm_sports_odds', 'lm_nba_odds', 'lm_nfl_odds', 'lm_nhl_odds', 'lm_mlb_odds',
        'lm_sports_ml_predictions', 'lm_sports_ml_metrics',
        'lm_sports_daily_picks', 'lm_sports_bets', 'lm_sports_clv',
        'lm_nba_team_stats', 'lm_nhl_team_stats', 'lm_nfl_team_stats', 'lm_mlb_team_stats'
    );
    $status = array();
    foreach ($tables as $tbl) {
        $r = $conn->query("SELECT COUNT(*) as cnt FROM " . $tbl);
        if ($r) {
            $row = $r->fetch_assoc();
            $status[] = array('table' => $tbl, 'rows' => (int)$row['cnt']);
        } else {
            $status[] = array('table' => $tbl, 'rows' => 0, 'note' => 'table may not exist');
        }
    }
    echo json_encode(array('ok' => true, 'tables' => $status));
}
