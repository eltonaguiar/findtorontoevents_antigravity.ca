<?php
/**
 * Segmented forensics: sport x market x odds bucket x EV bucket x book.
 * PHP 5.2 compatible. Prefer this JSON over raw SQL for older MySQL hosts.
 */
require_once dirname(__FILE__) . '/sports_db.php';
require_once dirname(__FILE__) . '/sports_metrics_lib.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'segments';

function sports_forensics_odds_bucket($odds) {
    $o = floatval($odds);
    if ($o < 2.0) {
        return 'lt_2';
    }
    if ($o < 3.0) {
        return '2_to_3';
    }
    if ($o < 6.0) {
        return '3_to_6';
    }
    return 'ge_6';
}

function sports_forensics_ev_bucket($ev) {
    $e = floatval($ev);
    if ($e >= 10) {
        return 'ev_10p';
    }
    if ($e >= 6) {
        return 'ev_6_10';
    }
    if ($e >= 3) {
        return 'ev_3_6';
    }
    if ($e >= 0) {
        return 'ev_0_3';
    }
    return 'ev_neg';
}

if ($action === 'segments') {
    $include_ci = (isset($_GET['include_ci']) && $_GET['include_ci'] === '1');
    $z_ci = 1.96;
    $q = "SELECT b.*, c.closing_price AS closing_odds FROM lm_sports_bets b
          LEFT JOIN lm_sports_clv c ON b.event_id = c.event_id AND b.bookmaker_key = c.bookmaker_key
          AND b.market = c.market AND b.pick = c.outcome_name
          WHERE b.result IS NOT NULL AND b.result != ''";
    $r = $sports_mysqli->query($q);
    $seg = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $nr = sports_normalize_result($row['result']);
            $sport = isset($row['sport']) ? $row['sport'] : '';
            $market = isset($row['market']) ? $row['market'] : '';
            $bk = isset($row['bookmaker']) ? $row['bookmaker'] : '';
            $bkk = isset($row['bookmaker_key']) ? $row['bookmaker_key'] : '';
            $ob = sports_forensics_odds_bucket($row['odds']);
            $eb = sports_forensics_ev_bucket($row['ev_pct']);
            $key = $sport . '|' . $market . '|' . $ob . '|' . $eb . '|' . $bk;
            if (!isset($seg[$key])) {
                $seg[$key] = array(
                    'sport' => $sport,
                    'sport_short' => sports_sport_short($sport),
                    'market' => $market,
                    'odds_bucket' => $ob,
                    'ev_bucket' => $eb,
                    'book' => $bk,
                    'bookmaker_key' => $bkk,
                    'wins' => 0,
                    'losses' => 0,
                    'pushes' => 0,
                    'voids' => 0,
                    'pnl' => 0.0,
                    'staked_wl' => 0.0,
                    'odds_sum_wl' => 0.0,
                    'clv_sum' => 0.0,
                    'clv_n' => 0,
                );
            }
            $pnl = floatval($row['pnl']);
            $stake = floatval($row['bet_amount']);
            $odds = floatval($row['odds']);
            $closing = floatval(isset($row['closing_odds']) ? $row['closing_odds'] : 0);
            $seg[$key]['pnl'] += $pnl;
            if ($nr === 'win') {
                $seg[$key]['wins']++;
            } else if ($nr === 'loss') {
                $seg[$key]['losses']++;
            } else if ($nr === 'push') {
                $seg[$key]['pushes']++;
            } else if ($nr === 'void') {
                $seg[$key]['voids']++;
            }
            if ($nr === 'win' || $nr === 'loss') {
                $seg[$key]['staked_wl'] += $stake;
                $seg[$key]['odds_sum_wl'] += $odds;
            }
            if ($closing > 0 && $odds > 0 && ($nr === 'win' || $nr === 'loss')) {
                $seg[$key]['clv_sum'] += ($odds - $closing) * ($stake / $odds);
                $seg[$key]['clv_n']++;
            }
        }
    }
    $out = array();
    foreach ($seg as $k => $s) {
        $wl = $s['wins'] + $s['losses'];
        $wr = ($wl > 0) ? round(100.0 * $s['wins'] / $wl, 2) : 0;
        $behr = 0;
        if ($wl > 0 && $s['odds_sum_wl'] > 0) {
            $avgO = $s['odds_sum_wl'] / $wl;
            $behr = ($avgO > 0) ? round(100.0 / $avgO, 2) : 0;
        }
        $roi = ($s['staked_wl'] > 0) ? round(100.0 * $s['pnl'] / $s['staked_wl'], 2) : 0;
        $avgClv = ($s['clv_n'] > 0) ? round($s['clv_sum'] / $s['clv_n'], 4) : 0;
        $rowOut = array(
            'sport' => $s['sport'],
            'sport_short' => $s['sport_short'],
            'market' => $s['market'],
            'odds_bucket' => $s['odds_bucket'],
            'ev_bucket' => $s['ev_bucket'],
            'book' => $s['book'],
            'bookmaker_key' => $s['bookmaker_key'],
            'wins' => $s['wins'],
            'losses' => $s['losses'],
            'pushes_voids' => $s['pushes'] + $s['voids'],
            'settled_directional' => $wl,
            'win_rate_pct' => $wr,
            'approx_behr_pct' => $behr,
            'edge_vs_behr_pct' => ($wl > 0) ? round($wr - $behr, 2) : 0,
            'pnl' => round($s['pnl'], 2),
            'roi_pct' => $roi,
            'avg_clv_usd' => $avgClv,
            'clv_sample' => intval($s['clv_n']),
        );
        if ($include_ci && $wl >= 1) {
            $ciPair = sports_wilson_ci_pct($s['wins'], $wl, $z_ci);
            $rowOut['win_rate_ci_low_pct'] = $ciPair[0];
            $rowOut['win_rate_ci_high_pct'] = $ciPair[1];
            $rowOut['ci_method'] = 'wilson_95';
        }
        $out[] = $rowOut;
    }
    $bookRank = array();
    $br2 = $sports_mysqli->query("SELECT bookmaker, SUM(pnl) AS pnl, SUM(CASE WHEN result IN ('won','win','lost','loss') THEN bet_amount ELSE 0 END) AS st,
        SUM(CASE WHEN result IN ('won','win') THEN 1 ELSE 0 END) AS w,
        SUM(CASE WHEN result IN ('lost','loss') THEN 1 ELSE 0 END) AS l
        FROM lm_sports_bets WHERE result IS NOT NULL AND result != '' GROUP BY bookmaker");
    if ($br2) {
        while ($brow = $br2->fetch_assoc()) {
            $bn = $brow['bookmaker'];
            $st = floatval($brow['st']);
            $pnlB = floatval($brow['pnl']);
            $roiB = ($st > 0) ? round(100.0 * $pnlB / $st, 2) : 0;
            $wlB = intval($brow['w']) + intval($brow['l']);
            $wrB = ($wlB > 0) ? round(100.0 * intval($brow['w']) / $wlB, 2) : 0;
            $bookRank[] = array(
                'book' => $bn,
                'roi_pct' => $roiB,
                'win_rate_pct' => $wrB,
                'settled_directional' => $wlB,
                'pnl' => round($pnlB, 2),
            );
        }
    }
    $nr = count($bookRank);
    for ($ri = 0; $ri < $nr; $ri++) {
        for ($rj = $ri + 1; $rj < $nr; $rj++) {
            if ($bookRank[$rj]['roi_pct'] > $bookRank[$ri]['roi_pct']) {
                $tmp = $bookRank[$ri];
                $bookRank[$ri] = $bookRank[$rj];
                $bookRank[$rj] = $tmp;
            }
        }
    }
    echo json_encode(array(
        'ok' => true,
        'action' => 'segments',
        'segment_count' => count($out),
        'segments' => $out,
        'book_rank' => $bookRank,
        'include_ci' => $include_ci,
        'bonferroni_note' => 'Many segments: interpret CIs with multiplicity control (Bonferroni / BH) when mining buckets.',
        'generated_at' => date('c'),
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'pre_game_status') {
    $exists = false;
    $chk = $sports_mysqli->query("SHOW TABLES LIKE 'lm_sports_pre_game_features'");
    if ($chk && $chk->num_rows > 0) {
        $exists = true;
    }
    $sample = array();
    if ($exists) {
        $s2 = $sports_mysqli->query("SELECT event_id, sport, updated_at, CHAR_LENGTH(feature_json) AS json_len FROM lm_sports_pre_game_features ORDER BY updated_at DESC LIMIT 5");
        if ($s2) {
            while ($sx = $s2->fetch_assoc()) {
                $sample[] = array(
                    'event_id' => $sx['event_id'],
                    'sport' => $sx['sport'],
                    'updated_at' => $sx['updated_at'],
                    'feature_json_chars' => intval($sx['json_len']),
                );
            }
        }
    }
    echo json_encode(array(
        'ok' => true,
        'action' => 'pre_game_status',
        'table' => 'lm_sports_pre_game_features',
        'table_exists' => $exists,
        'join_to_bets' => 'lm_sports_bets.event_id = lm_sports_pre_game_features.event_id',
        'sample_rows' => $sample,
        'generated_at' => date('c'),
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'daily_returns') {
    $dr = $sports_mysqli->query("SELECT DATE(COALESCE(settled_at, placed_at)) AS d, sport,
        SUM(COALESCE(pnl,0)) AS day_pnl
        FROM lm_sports_bets
        WHERE result IS NOT NULL AND result != ''
        GROUP BY d, sport
        ORDER BY d DESC
        LIMIT 2000");
    $rows = array();
    if ($dr) {
        while ($drow = $dr->fetch_assoc()) {
            $rows[] = array(
                'date' => $drow['d'],
                'sport' => $drow['sport'],
                'sport_short' => sports_sport_short($drow['sport']),
                'pnl' => round(floatval($drow['day_pnl']), 2),
            );
        }
    }
    echo json_encode(array(
        'ok' => true,
        'daily_rows' => $rows,
        'note' => 'Use for correlation of daily PnL by sport; pivot client-side or in Python (scripts/sports_portfolio_corr.py).',
        'generated_at' => date('c'),
    ));
    $sports_mysqli->close();
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'unknown action'));
$sports_mysqli->close();
