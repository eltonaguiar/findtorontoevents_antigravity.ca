<?php
/**
 * One-time: add lm_sports_bets.cohort and backfill from algorithm tag.
 * PHP 5.2 safe. Call after deploy: ensure_sports_bets_cohort.php?key=<ADMIN_API_KEY>
 */
require_once dirname(__FILE__) . '/sports_db.php';

$key = isset($_GET['key']) ? $_GET['key'] : '';
$_admin_key = getenv('ADMIN_API_KEY');
if ($_admin_key === false || $_admin_key === '' || $key !== $_admin_key) {
    echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
    $sports_mysqli->close();
    exit;
}

$out = array('ok' => true, 'steps' => array());
$chk = $sports_mysqli->query("SHOW COLUMNS FROM lm_sports_bets LIKE 'cohort'");
if ($chk && $chk->num_rows > 0) {
    $out['steps'][] = 'cohort_column_already_present';
} else {
    $sql = "ALTER TABLE lm_sports_bets ADD COLUMN cohort varchar(64) DEFAULT NULL";
    if ($sports_mysqli->query($sql)) {
        $out['steps'][] = 'cohort_column_added';
    } else {
        echo json_encode(array('ok' => false, 'error' => $sports_mysqli->error));
        $sports_mysqli->close();
        exit;
    }
}

$bf = $sports_mysqli->query("UPDATE lm_sports_bets SET cohort = 'post_guardrail_20260404' WHERE algorithm = 'value_bet_gr202604' AND (cohort IS NULL OR cohort = '')");
if ($bf) {
    $out['backfill_affected'] = $sports_mysqli->affected_rows;
    $out['steps'][] = 'backfill_algorithm_tagged_rows';
} else {
    $out['steps'][] = 'backfill_skipped_db_error';
    $out['backfill_error'] = $sports_mysqli->error;
}

echo json_encode($out);
$sports_mysqli->close();
