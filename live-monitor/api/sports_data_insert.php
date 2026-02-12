<?php
/**
 * sports_data_insert.php — Script to insert sample bet data for testing/ML bootstrapping.
 * PHP 5.2 compatible.
 *
 * Usage: POST to https://findtorontoevents.ca/live-monitor/api/sports_data_insert.php
 * with JSON body: {"key": "livetrader2026", "bets": [array of bet objects]}
 * Or run via CLI with sample data.
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';
require_once dirname(__FILE__) . '/sports_schema.php';

// Ensure schema exists
_sb_ensure_schema($conn);

header('Content-Type: application/json');

// Security key (from env or hardcoded for 5.2)
$admin_key = 'livetrader2026';  // Replace with getenv if possible

function insert_bet($conn, $bet) {
    $sql = "INSERT INTO lm_sports_bets 
            (event_id, sport, home_team, away_team, commence_time, game_date,
             bet_type, market, pick, bookmaker, bookmaker_key, odds, implied_prob,
             bet_amount, potential_payout, algorithm, ev_pct, status, result, pnl,
             settled_at, actual_home_score, actual_away_score, placed_at)
            VALUES ('" . mysql_real_escape_string($bet['event_id']) . "',
                    '" . mysql_real_escape_string($bet['sport']) . "',
                    '" . mysql_real_escape_string($bet['home_team']) . "',
                    '" . mysql_real_escape_string($bet['away_team']) . "',
                    '" . mysql_real_escape_string($bet['commence_time']) . "',
                    '" . mysql_real_escape_string($bet['game_date']) . "',
                    '" . mysql_real_escape_string($bet['bet_type']) . "',
                    '" . mysql_real_escape_string($bet['market']) . "',
                    '" . mysql_real_escape_string($bet['pick']) . "',
                    '" . mysql_real_escape_string($bet['bookmaker']) . "',
                    '" . mysql_real_escape_string($bet['bookmaker_key']) . "',
                    " . (float)$bet['odds'] . ",
                    " . (float)$bet['implied_prob'] . ",
                    " . (float)$bet['bet_amount'] . ",
                    " . (float)$bet['potential_payout'] . ",
                    '" . mysql_real_escape_string($bet['algorithm']) . "',
                    " . (float)$bet['ev_pct'] . ",
                    '" . mysql_real_escape_string($bet['status']) . "',
                    " . ($bet['result'] ? "'" . mysql_real_escape_string($bet['result']) . "'" : 'NULL') . ",
                    " . ($bet['pnl'] ? (float)$bet['pnl'] : 'NULL') . ",
                    " . ($bet['settled_at'] ? "'" . mysql_real_escape_string($bet['settled_at']) . "'" : 'NULL') . ",
                    " . ($bet['actual_home_score'] ? (int)$bet['actual_home_score'] : 'NULL') . ",
                    " . ($bet['actual_away_score'] ? (int)$bet['actual_away_score'] : 'NULL') . ",
                    '" . mysql_real_escape_string($bet['placed_at']) . "')";
    
    if (mysql_query($sql, $conn)) {
        return true;
    } else {
        return mysql_error($conn);
    }
}

// Handle request
$input = json_decode(file_get_contents('php://input'), true);
if (isset($input['key']) && $input['key'] === $admin_key && isset($input['bets'])) {
    $success = 0;
    $errors = array();
    foreach ($input['bets'] as $bet) {
        $result = insert_bet($conn, $bet);
        if ($result === true) {
            $success++;
        } else {
            $errors[] = $result;
        }
    }
    echo '{\"ok\":true,\"inserted\":' . $success . ',\"errors\":' . json_encode($errors) . '}'; 
} else {
    // Sample data for CLI/testing
    $sample_bets = array(
        array(
            'event_id' => 'sample1',
            'sport' => 'basketball_nba',
            'home_team' => 'Team A',
            'away_team' => 'Team B',
            'commence_time' => '2026-02-13 00:00:00',
            'game_date' => '2026-02-12',
            'bet_type' => 'moneyline',
            'market' => 'h2h',
            'pick' => 'Team A',
            'bookmaker' => 'FanDuel',
            'bookmaker_key' => 'fanduel',
            'odds' => 2.1,
            'implied_prob' => 0.4762,
            'bet_amount' => 10.0,
            'potential_payout' => 21.0,
            'algorithm' => 'value_bet',
            'ev_pct' => 5.0,
            'status' => 'settled',
            'result' => 'won',
            'pnl' => 11.0,
            'settled_at' => '2026-02-13 02:00:00',
            'actual_home_score' => 110,
            'actual_away_score' => 105,
            'placed_at' => '2026-02-12 23:00:00'
        ),
        // Add more samples as needed
    );
    
    $success = 0;
    $errors = array();
    foreach ($sample_bets as $bet) {
        $result = insert_bet($conn, $bet);
        if ($result === true) {
            $success++;
        } else {
            $errors[] = $result;
        }
    }
echo '{\"ok\":true,\"inserted\":' . $success . ',\"errors\":' . json_encode($errors) . ',\"note\":\"Sample data inserted (CLI mode)\"}'; 
}

mysql_close($conn);
?>