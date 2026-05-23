<?php
/**
 * Paper shadow / A-B track for optional fade vs main line (separate bankroll in JSON only).
 * Table lm_sports_paper_shadow is created via live-monitor/sql/sports_plan_migrations.sql.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/sports_db.php';
require_once dirname(__FILE__) . '/sports_metrics_lib.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'summary';

function sports_paper_table_ok($mysqli) {
    $r = $mysqli->query("SHOW TABLES LIKE 'lm_sports_paper_shadow'");
    return ($r && $r->num_rows > 0);
}

if ($action === 'summary') {
    if (!sports_paper_table_ok($sports_mysqli)) {
        echo json_encode(array(
            'ok' => true,
            'table_ready' => false,
            'main' => array('settled' => 0, 'wins' => 0, 'losses' => 0, 'win_rate_pct' => 0, 'roi_pct' => 0, 'pnl' => 0),
            'fade' => array('settled' => 0, 'wins' => 0, 'losses' => 0, 'win_rate_pct' => 0, 'roi_pct' => 0, 'pnl' => 0),
            'note' => 'Run sports_plan_migrations.sql to create lm_sports_paper_shadow.',
        ));
        $sports_mysqli->close();
        exit;
    }
    $main = array('settled' => 0, 'wins' => 0, 'losses' => 0, 'win_rate_pct' => 0, 'roi_pct' => 0, 'pnl' => 0);
    $fade = array('settled' => 0, 'wins' => 0, 'losses' => 0, 'win_rate_pct' => 0, 'roi_pct' => 0, 'pnl' => 0);
    $tracks = array('main' => $main, 'fade' => $fade);
    $tr = $sports_mysqli->query("SELECT track, result, pnl, stake FROM lm_sports_paper_shadow WHERE result IS NOT NULL AND result != ''");
    if ($tr) {
        while ($trow = $tr->fetch_assoc()) {
            $tk = isset($trow['track']) ? $trow['track'] : 'main';
            if ($tk !== 'fade') {
                $tk = 'main';
            }
            $nr = sports_normalize_result($trow['result']);
            $tracks[$tk]['pnl'] += floatval($trow['pnl']);
            if ($nr === 'win') {
                $tracks[$tk]['wins']++;
            } else if ($nr === 'loss') {
                $tracks[$tk]['losses']++;
            }
        }
    }
    foreach (array('main', 'fade') as $tk) {
        $wl = $tracks[$tk]['wins'] + $tracks[$tk]['losses'];
        $tracks[$tk]['settled'] = $wl;
        $tracks[$tk]['win_rate_pct'] = ($wl > 0) ? round(100.0 * $tracks[$tk]['wins'] / $wl, 2) : 0;
        $stq = $sports_mysqli->query("SELECT SUM(stake) AS s FROM lm_sports_paper_shadow WHERE track = '" . $sports_mysqli->real_escape_string($tk) . "' AND result IN ('won','win','lost','loss')");
        $st = 0.0;
        if ($stq && ($srow = $stq->fetch_assoc())) {
            $st = floatval($srow['s']);
        }
        $tracks[$tk]['roi_pct'] = ($st > 0) ? round(100.0 * $tracks[$tk]['pnl'] / $st, 2) : 0;
        $tracks[$tk]['pnl'] = round($tracks[$tk]['pnl'], 2);
    }
    $cnt = 0;
    $cq = $sports_mysqli->query("SELECT COUNT(*) AS c FROM lm_sports_paper_shadow");
    if ($cq && ($crow = $cq->fetch_assoc())) {
        $cnt = intval($crow['c']);
    }
    echo json_encode(array(
        'ok' => true,
        'table_ready' => true,
        'row_count' => $cnt,
        'main' => $tracks['main'],
        'fade' => $tracks['fade'],
        'decision_note' => 'Treat 100+ fade rows as early readout; 300+ or CI for policy changes.',
        'generated_at' => date('c'),
    ));
    $sports_mysqli->close();
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'unknown action'));
$sports_mysqli->close();
