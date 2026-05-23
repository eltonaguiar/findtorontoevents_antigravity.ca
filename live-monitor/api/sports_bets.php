<?php
/**
 * Paper sports bets: dashboard, active/history, auto_place, settle.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/sports_db.php';
require_once dirname(__FILE__) . '/sports_metrics_lib.php';
require_once dirname(__FILE__) . '/sports_scores_settle_lib.php';

$action = isset($_GET['action']) ? $_GET['action'] : (isset($_POST['action']) ? $_POST['action'] : 'dashboard');
$key = isset($_GET['key']) ? $_GET['key'] : (isset($_POST['key']) ? $_POST['key'] : '');

function sports_api_key_ok($k) {
    $expected = getenv('ADMIN_API_KEY');
    if ($expected === false || $expected === '') {
        return false; // Key not configured — deny all admin access
    }
    return ($k === $expected);
}

/**
 * Sport-specific auto-place policy loader (Copilot Cloud 2026-04-26 Q3).
 * Reads config/auto_place_policy.json. Returns the policy or null when
 * disabled / file missing. Static-cached.
 */
function sports_auto_place_policy() {
    static $cache = false;
    if ($cache !== false) {
        return $cache;
    }
    $cache = null;
    $p = dirname(__FILE__) . '/../../config/auto_place_policy.json';
    if (!file_exists($p)) {
        return $cache;
    }
    $raw = @file_get_contents($p);
    if ($raw === false || $raw === '') {
        return $cache;
    }
    $obj = @json_decode($raw, true);
    if (!is_array($obj) || empty($obj['enabled'])) {
        return $cache;
    }
    $cache = $obj;
    return $cache;
}

/**
 * Apply policy v2 gate. Returns ['pass'=>bool,'reason'=>string].
 * Empty/null policy => ['pass'=>true,'reason'=>'legacy'] (no behavior change).
 */
function sports_auto_place_policy_check($policy, $row) {
    if (!is_array($policy)) {
        return array('pass' => true, 'reason' => 'legacy');
    }
    $sport = isset($row['sport']) ? strval($row['sport']) : '';
    $ev = isset($row['ev_pct']) ? floatval($row['ev_pct']) : 0.0;
    $tier = 'LOW EDGE';
    if ($ev >= 8.0) { $tier = 'STRONG TAKE'; }
    else if ($ev >= 5.0) { $tier = 'TAKE'; }
    else if ($ev >= 3.0) { $tier = 'LEAN'; }
    $rule = isset($policy['per_sport'][$sport]) ? $policy['per_sport'][$sport] : (isset($policy['fallback']) ? $policy['fallback'] : (isset($policy['global_baseline']) ? $policy['global_baseline'] : null));
    if (!is_array($rule)) {
        return array('pass' => true, 'reason' => 'no_rule');
    }
    if (!empty($rule['pause'])) {
        return array('pass' => false, 'reason' => 'sport_paused:' . $sport);
    }
    if (!empty($rule['manual_review_only'])) {
        return array('pass' => false, 'reason' => 'manual_review_only:' . $sport);
    }
    $minEv = isset($rule['min_ev_pct']) ? floatval($rule['min_ev_pct']) : 0.0;
    if ($ev < $minEv) {
        return array('pass' => false, 'reason' => 'below_min_ev:' . $sport);
    }
    $tierWl = isset($rule['require_recommendation_in']) ? $rule['require_recommendation_in'] : null;
    if (is_array($tierWl) && count($tierWl) > 0 && !in_array($tier, $tierWl, true)) {
        return array('pass' => false, 'reason' => 'tier_not_allowed:' . $tier . '_for_' . $sport);
    }
    if (!empty($rule['require_goalie_overlay_applied'])) {
        $goa = isset($row['goalie_overlay_applied']) ? intval($row['goalie_overlay_applied']) : 0;
        if ($goa !== 1) {
            return array('pass' => false, 'reason' => 'goalie_overlay_required:' . $sport);
        }
    }
    return array('pass' => true, 'reason' => 'policy_v2_pass');
}

/**
 * auto_place ticket placement: Odds API bookmaker_key allow-list only (lowercase).
 * CA-legal / sharp bucket per claude-sports-db-fix SHIP PLAN 2026-04-04.
 */
function sports_auto_place_book_whitelisted($bookKey) {
    $k = strtolower(trim(strval($bookKey)));
    $ok = array(
        'fanduel' => 1,
        'draftkings' => 1,
        'betmgm' => 1,
        'betrivers' => 1,
        'espnbet' => 1,
        'pinnacle' => 1,
        'caesars' => 1,
        'coolbet' => 1,
        'ballybet' => 1,
        'hardrockbet' => 1,
        'thescorebet' => 1,
        'thescore' => 1,
        'betway' => 1,
        'unibet' => 1,
    );
    if (isset($ok[$k])) {
        return true;
    }
    if (strpos($k, 'betway') !== false || strpos($k, 'unibet') !== false) {
        return true;
    }
    return false;
}

/**
 * SQL predicate: pending ticket is old enough to void (no score-grade available).
 * Uses commence_time OR game_date so bad commence timestamps still clear via game_date.
 * PHP 5.2 / MySQL 5.0+.
 */
function sports_bets_stale_pending_predicate_sql($staleDays) {
    $d = intval($staleDays);
    return "(commence_time < DATE_SUB(NOW(), INTERVAL " . $d . " DAY) OR (game_date IS NOT NULL AND game_date <> '0000-00-00' AND game_date < DATE_SUB(CURDATE(), INTERVAL " . $d . " DAY)))";
}

/** Apr 2026 auto_place / analyzer guardrails — explicit DB tag + algorithm fallback. */
function sports_bets_cohort_post_guardrail_key() {
    return 'post_guardrail_20260404';
}

function sports_bets_has_cohort_column($mysqli) {
    static $cache = null;
    if ($cache !== null) {
        return $cache;
    }
    $chk = $mysqli->query("SHOW COLUMNS FROM lm_sports_bets LIKE 'cohort'");
    $cache = ($chk && $chk->num_rows > 0);
    return $cache;
}

/**
 * SQL predicate on table alias b: post–policy-fix cohort (cohort tag or legacy algorithm rows).
 */
function sports_bets_post_guardrail_where_b($mysqli) {
    $ck = $mysqli->real_escape_string(sports_bets_cohort_post_guardrail_key());
    if (sports_bets_has_cohort_column($mysqli)) {
        return "((COALESCE(b.cohort,'') = '" . $ck . "') OR (b.algorithm = 'value_bet_gr202604'))";
    }
    return "(b.algorithm = 'value_bet_gr202604')";
}

function sports_fetch_all_bets_for_metrics($mysqli) {
    $q = "SELECT b.*, c.closing_price AS closing_odds FROM lm_sports_bets b
          LEFT JOIN lm_sports_clv c ON b.event_id = c.event_id AND b.bookmaker_key = c.bookmaker_key
          AND b.market = c.market AND b.pick = c.outcome_name";
    $r = $mysqli->query($q);
    $rows = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $rows[] = sports_bet_row_to_metric_array($row);
        }
    }
    return $rows;
}

function sports_fetch_bets_rows($mysqli, $whereSql) {
    $q = "SELECT b.*, c.closing_price AS closing_odds FROM lm_sports_bets b
          LEFT JOIN lm_sports_clv c ON b.event_id = c.event_id AND b.bookmaker_key = c.bookmaker_key
          AND b.market = c.market AND b.pick = c.outcome_name
          WHERE " . $whereSql;
    $r = $mysqli->query($q);
    $rows = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $rows[] = $row;
        }
    }
    return $rows;
}

function sports_dashboard($mysqli) {
    $INITIAL = 1000.0;
    $allMetricRows = sports_fetch_all_bets_for_metrics($mysqli);
    $m = sports_compute_settled_metrics($allMetricRows);

    $pnlRow = $mysqli->query("SELECT COALESCE(SUM(pnl),0) AS tp FROM lm_sports_bets WHERE result IS NOT NULL AND result != ''");
    $total_pnl = 0.0;
    if ($pnlRow && ($pr = $pnlRow->fetch_assoc())) {
        $total_pnl = floatval($pr['tp']);
    }
    $bankroll = $INITIAL + $total_pnl;

    $activeR = $mysqli->query("SELECT COUNT(*) AS c FROM lm_sports_bets WHERE (result IS NULL OR result = '') AND status = 'pending'");
    $active_bets = 0;
    if ($activeR && ($ar = $activeR->fetch_assoc())) {
        $active_bets = intval($ar['c']);
    }

    $resR = $mysqli->query("SELECT COALESCE(SUM(bet_amount),0) AS s FROM lm_sports_bets WHERE (result IS NULL OR result = '') AND status = 'pending'");
    $reserved = 0.0;
    if ($resR && ($rr = $resR->fetch_assoc())) {
        $reserved = floatval($rr['s']);
    }

    $stalePred14 = sports_bets_stale_pending_predicate_sql(14);
    $pending_stale_14d = 0;
    $ps = $mysqli->query("SELECT COUNT(*) AS c FROM lm_sports_bets WHERE status = 'pending' AND (result IS NULL OR result = '') AND " . $stalePred14);
    if ($ps && ($prow = $ps->fetch_assoc())) {
        $pending_stale_14d = intval($prow['c']);
    }
    $oldest_pending_commence = null;
    $pending_stale_stake = 0.0;
    $op = $mysqli->query("SELECT MIN(commence_time) AS oc, COALESCE(SUM(bet_amount),0) AS ss FROM lm_sports_bets WHERE status = 'pending' AND (result IS NULL OR result = '') AND " . $stalePred14);
    if ($op && ($orow = $op->fetch_assoc())) {
        if ($orow['oc'] !== null && $orow['oc'] !== '') {
            $oldest_pending_commence = $orow['oc'];
        }
        $pending_stale_stake = floatval($orow['ss']);
    }

    $hist = array();
    $hr = $mysqli->query("SELECT snapshot_date, bankroll FROM lm_sports_bankroll ORDER BY snapshot_date ASC LIMIT 90");
    if ($hr) {
        while ($hrow = $hr->fetch_assoc()) {
            $hist[] = array(
                'snapshot_date' => $hrow['snapshot_date'],
                'bankroll' => floatval($hrow['bankroll']),
            );
        }
    }

    $by_sport = array();
    $sr = $mysqli->query("SELECT DISTINCT sport FROM lm_sports_bets WHERE result IS NOT NULL AND result != ''");
    $sports = array();
    if ($sr) {
        while ($srow = $sr->fetch_assoc()) {
            $sports[] = $srow['sport'];
        }
    }
    for ($si = 0; $si < count($sports); $si++) {
        $sp = $sports[$si];
        $spEsc = $mysqli->real_escape_string($sp);
        $br = sports_fetch_bets_rows($mysqli, "b.sport = '" . $spEsc . "' AND b.result IS NOT NULL AND b.result != ''");
        $metricArr = array();
        for ($bi = 0; $bi < count($br); $bi++) {
            $metricArr[] = sports_bet_row_to_metric_array($br[$bi]);
        }
        $sm = sports_compute_settled_metrics($metricArr);
        $pnlSp = 0.0;
        for ($bi = 0; $bi < count($br); $bi++) {
            $pnlSp += floatval($br[$bi]['pnl']);
        }
        $staked = floatval($sm['total_staked_settled']);
        $roi_sp = ($staked > 0) ? round(100.0 * $pnlSp / $staked, 2) : 0.0;
        $by_sport[] = array(
            'sport' => $sp,
            'sport_short' => sports_sport_short($sp),
            'bets' => $sm['wins'] + $sm['losses'] + $sm['pushes'] + $sm['voids'],
            'wins' => $sm['wins'],
            'losses' => $sm['losses'],
            'pushes' => $sm['pushes'],
            'voids' => $sm['voids'],
            'settled_directional' => $sm['settled_for_wr'],
            'win_rate' => $sm['win_rate_pct'],
            'pnl' => round($pnlSp, 2),
            'roi' => $roi_sp,
            'avg_clv' => $sm['avg_clv'],
            'clv_beat_rate_pct' => $sm['clv_beat_rate_pct'],
        );
    }

    $by_alg = array();
    $ar2 = $mysqli->query("SELECT DISTINCT algorithm FROM lm_sports_bets WHERE result IS NOT NULL AND result != ''");
    $algs = array();
    if ($ar2) {
        while ($arow = $ar2->fetch_assoc()) {
            $algs[] = $arow['algorithm'];
        }
    }
    for ($ai = 0; $ai < count($algs); $ai++) {
        $alg = $algs[$ai];
        $algEsc = $mysqli->real_escape_string($alg);
        $br = sports_fetch_bets_rows($mysqli, "b.algorithm = '" . $algEsc . "' AND b.result IS NOT NULL AND b.result != ''");
        $metricArr = array();
        for ($bi = 0; $bi < count($br); $bi++) {
            $metricArr[] = sports_bet_row_to_metric_array($br[$bi]);
        }
        $am = sports_compute_settled_metrics($metricArr);
        $pnlA = 0.0;
        for ($bi = 0; $bi < count($br); $bi++) {
            $pnlA += floatval($br[$bi]['pnl']);
        }
        $stakedA = floatval($am['total_staked_settled']);
        $roi_a = ($stakedA > 0) ? round(100.0 * $pnlA / $stakedA, 2) : 0.0;
        $by_alg[] = array(
            'algorithm' => $alg,
            'bets' => $am['wins'] + $am['losses'] + $am['pushes'] + $am['voids'],
            'wins' => $am['wins'],
            'losses' => $am['losses'],
            'win_rate' => $am['win_rate_pct'],
            'pnl' => round($pnlA, 2),
            'roi' => $roi_a,
        );
    }

    $clv_quadrants = sports_compute_clv_quadrants($allMetricRows);

    $by_market = array();
    $mrk = $mysqli->query("SELECT DISTINCT market FROM lm_sports_bets WHERE result IS NOT NULL AND result != '' AND market IS NOT NULL AND market != ''");
    $markets = array();
    if ($mrk) {
        while ($mrow = $mrk->fetch_assoc()) {
            $markets[] = $mrow['market'];
        }
    }
    for ($mi = 0; $mi < count($markets); $mi++) {
        $mk = $markets[$mi];
        $mkEsc = $mysqli->real_escape_string($mk);
        $brm = sports_fetch_bets_rows($mysqli, "b.market = '" . $mkEsc . "' AND b.result IS NOT NULL AND b.result != ''");
        $marr = array();
        for ($bi = 0; $bi < count($brm); $bi++) {
            $marr[] = sports_bet_row_to_metric_array($brm[$bi]);
        }
        $mm = sports_compute_settled_metrics($marr);
        $pnlM = 0.0;
        for ($bi = 0; $bi < count($brm); $bi++) {
            $pnlM += floatval($brm[$bi]['pnl']);
        }
        $stkM = floatval($mm['total_staked_settled']);
        $roiM = ($stkM > 0) ? round(100.0 * $pnlM / $stkM, 2) : 0.0;
        $by_market[] = array(
            'market' => $mk,
            'bets' => $mm['wins'] + $mm['losses'] + $mm['pushes'] + $mm['voids'],
            'wins' => $mm['wins'],
            'losses' => $mm['losses'],
            'win_rate' => $mm['win_rate_pct'],
            'pnl' => round($pnlM, 2),
            'roi' => $roiM,
            'avg_clv' => $mm['avg_clv'],
            'clv_beat_rate_pct' => $mm['clv_beat_rate_pct'],
            'clv_tracked' => $mm['avg_clv_sample'],
        );
    }

    // Performance by recommendation tier (derived from ev_pct).
    // Thresholds match the Today's Picks UI: STRONG TAKE >=8, TAKE >=5,
    // LEAN >=3, else LOW EDGE.
    $by_rec = array();
    $tiers = array(
        array('label' => 'STRONG TAKE', 'min' => 8.0, 'max' => 1000.0),
        array('label' => 'TAKE',        'min' => 5.0, 'max' => 8.0),
        array('label' => 'LEAN',        'min' => 3.0, 'max' => 5.0),
        array('label' => 'LOW EDGE',    'min' => -1000.0, 'max' => 3.0),
    );
    for ($ri = 0; $ri < count($tiers); $ri++) {
        $t = $tiers[$ri];
        $where = "b.result IS NOT NULL AND b.result != '' AND b.ev_pct >= " . floatval($t['min']) . " AND b.ev_pct < " . floatval($t['max']);
        $brec = sports_fetch_bets_rows($mysqli, $where);
        $rarr = array();
        for ($bi = 0; $bi < count($brec); $bi++) {
            $rarr[] = sports_bet_row_to_metric_array($brec[$bi]);
        }
        $rm = sports_compute_settled_metrics($rarr);
        $pnlR = 0.0;
        for ($bi = 0; $bi < count($brec); $bi++) {
            $pnlR += floatval($brec[$bi]['pnl']);
        }
        $stkR = floatval($rm['total_staked_settled']);
        $roiR = ($stkR > 0) ? round(100.0 * $pnlR / $stkR, 2) : 0.0;
        $by_rec[] = array(
            'tier' => $t['label'],
            'ev_min' => $t['min'],
            'ev_max' => ($t['max'] >= 1000.0) ? null : $t['max'],
            'bets' => $rm['wins'] + $rm['losses'] + $rm['pushes'] + $rm['voids'],
            'wins' => $rm['wins'],
            'losses' => $rm['losses'],
            'pushes' => $rm['pushes'],
            'voids' => $rm['voids'],
            'settled_directional' => $rm['wins'] + $rm['losses'],
            'win_rate' => $rm['win_rate_pct'],
            'pnl' => round($pnlR, 2),
            'staked' => round($stkR, 2),
            'roi' => $roiR,
            'avg_clv' => $rm['avg_clv'],
            'clv_beat_rate_pct' => $rm['clv_beat_rate_pct'],
            'clv_tracked' => $rm['avg_clv_sample'],
        );
    }

    // Tier x sport matrix: how each recommendation tier performs in each sport.
    // Same tier thresholds as $by_rec above.
    $by_rec_sport = array();
    for ($si = 0; $si < count($sports); $si++) {
        $sp2 = $sports[$si];
        $spEsc2 = $mysqli->real_escape_string($sp2);
        for ($ri = 0; $ri < count($tiers); $ri++) {
            $t2 = $tiers[$ri];
            $where2 = "b.sport = '" . $spEsc2 . "' AND b.result IS NOT NULL AND b.result != '' AND b.ev_pct >= " . floatval($t2['min']) . " AND b.ev_pct < " . floatval($t2['max']);
            $br2 = sports_fetch_bets_rows($mysqli, $where2);
            if (count($br2) === 0) {
                continue;
            }
            $rarr2 = array();
            for ($bi = 0; $bi < count($br2); $bi++) {
                $rarr2[] = sports_bet_row_to_metric_array($br2[$bi]);
            }
            $rm2 = sports_compute_settled_metrics($rarr2);
            $pnlR2 = 0.0;
            for ($bi = 0; $bi < count($br2); $bi++) {
                $pnlR2 += floatval($br2[$bi]['pnl']);
            }
            $stkR2 = floatval($rm2['total_staked_settled']);
            $roiR2 = ($stkR2 > 0) ? round(100.0 * $pnlR2 / $stkR2, 2) : 0.0;
            // Map sport -> short label using existing $by_sport entries.
            $sportShort = $sp2;
            for ($bsi = 0; $bsi < count($by_sport); $bsi++) {
                if ($by_sport[$bsi]['sport'] === $sp2) {
                    $sportShort = $by_sport[$bsi]['sport_short'];
                    break;
                }
            }
            $by_rec_sport[] = array(
                'sport' => $sp2,
                'sport_short' => $sportShort,
                'tier' => $t2['label'],
                'bets' => $rm2['wins'] + $rm2['losses'] + $rm2['pushes'] + $rm2['voids'],
                'wins' => $rm2['wins'],
                'losses' => $rm2['losses'],
                'pushes' => $rm2['pushes'],
                'voids' => $rm2['voids'],
                'settled_directional' => $rm2['wins'] + $rm2['losses'],
                'win_rate' => $rm2['win_rate_pct'],
                'pnl' => round($pnlR2, 2),
                'staked' => round($stkR2, 2),
                'roi' => $roiR2,
            );
        }
    }

    $pending_by_sport = array();
    $pex = $mysqli->query("SELECT sport, COALESCE(SUM(bet_amount),0) AS s FROM lm_sports_bets WHERE (result IS NULL OR result = '') AND status = 'pending' GROUP BY sport");
    if ($pex) {
        while ($prow = $pex->fetch_assoc()) {
            $pending_by_sport[] = array(
                'sport' => $prow['sport'],
                'sport_short' => sports_sport_short($prow['sport']),
                'pending_stake' => round(floatval($prow['s']), 2),
                'pct_of_bankroll' => ($bankroll > 0) ? round(100.0 * floatval($prow['s']) / $bankroll, 2) : 0,
            );
        }
    }

    $total_settled_tickets = $m['closed_bets'];
    $life = 0;
    $lc = $mysqli->query("SELECT COUNT(*) AS c FROM lm_sports_bets");
    if ($lc && ($lrow = $lc->fetch_assoc())) {
        $life = intval($lrow['c']);
    }
    $wil = sports_wilson_ci_pct($m['wins'], $m['settled_for_wr'], 1.96);
    $predGr = sports_bets_post_guardrail_where_b($mysqli);
    $brGr = sports_fetch_bets_rows($mysqli, $predGr . " AND b.result IS NOT NULL AND b.result != ''");
    $metricGr = array();
    for ($gi = 0; $gi < count($brGr); $gi++) {
        $metricGr[] = sports_bet_row_to_metric_array($brGr[$gi]);
    }
    $mGr = sports_compute_settled_metrics($metricGr);
    $pnlGr = 0.0;
    for ($gi = 0; $gi < count($brGr); $gi++) {
        $pnlGr += floatval($brGr[$gi]['pnl']);
    }
    $wilGr = sports_wilson_ci_pct($mGr['wins'], $mGr['settled_for_wr'], 1.96);
    $out = array(
        'ok' => true,
        'bankroll' => round($bankroll, 2),
        'bankroll_change' => round($bankroll - $INITIAL, 2),
        'total_bets' => $total_settled_tickets,
        'lifetime_bet_rows' => $life,
        'total_wins' => $m['wins'],
        'total_losses' => $m['losses'],
        'total_pushes' => $m['pushes'],
        'total_voids' => $m['voids'],
        'total_pushes_voids_combined' => $m['pushes'] + $m['voids'],
        'win_rate' => $m['win_rate_pct'],
        'win_rate_denominator' => $m['settled_for_wr'],
        'metrics_caption' => 'Win rate uses wins / (wins + losses) only. Pushes and voids are separate. ROI uses stake on win+loss tickets.',
        'win_rate_quality' => array(
            'wilson_95_low_pct' => $wil[0],
            'wilson_95_high_pct' => $wil[1],
            'directional_n' => $m['settled_for_wr'],
            'small_sample' => ($m['settled_for_wr'] < 30),
            'caption' => 'Wilson ~95% CI on win rate (directional sample only). Do not overfit when directional_n is small.',
        ),
        'cohort_guardrail_v1' => array(
            'cohort' => sports_bets_cohort_post_guardrail_key(),
            'algorithm' => 'value_bet_gr202604',
            'directional_n' => $mGr['settled_for_wr'],
            'wins' => $mGr['wins'],
            'losses' => $mGr['losses'],
            'pushes' => $mGr['pushes'],
            'voids' => $mGr['voids'],
            'win_rate_pct' => $mGr['win_rate_pct'],
            'wilson_95_low_pct' => $wilGr[0],
            'wilson_95_high_pct' => $wilGr[1],
            'total_pnl' => round($pnlGr, 2),
            'roi_pct' => $mGr['roi_pct'],
            'note' => 'Paper bets: cohort post_guardrail_20260404 or algorithm value_bet_gr202604 (Apr 2026 policy). Excludes legacy value_bet rows.',
        ),
        'since_policy_fix' => array(
            'cohort' => sports_bets_cohort_post_guardrail_key(),
            'settled_tickets' => $mGr['closed_bets'],
            'wins' => $mGr['wins'],
            'losses' => $mGr['losses'],
            'pushes' => $mGr['pushes'],
            'voids' => $mGr['voids'],
            'directional_n' => $mGr['settled_for_wr'],
            'win_rate_pct' => $mGr['win_rate_pct'],
            'total_pnl' => round($pnlGr, 2),
            'roi_pct' => $mGr['roi_pct'],
            'win_rate_quality' => array(
                'wilson_95_low_pct' => $wilGr[0],
                'wilson_95_high_pct' => $wilGr[1],
                'directional_n' => $mGr['settled_for_wr'],
                'small_sample' => ($mGr['settled_for_wr'] < 30),
                'caption' => 'Wilson ~95% CI on win rate for the post-policy cohort only. Expect 10–30 weeks to reach n≈30 under strict filters.',
            ),
            'caption' => 'Headline slice: bets tagged cohort post_guardrail_20260404 or algorithm value_bet_gr202604. Legacy pre-fix tickets stay in “All settled”.',
        ),
        'roi_pct' => $m['roi_pct'],
        'total_pnl' => round($total_pnl, 2),
        'active_bets' => $active_bets,
        'pending_bets' => $active_bets,
        'reserved_amount' => round($reserved, 2),
        'bankroll_history' => $hist,
        'by_sport' => $by_sport,
        'by_algorithm' => $by_alg,
        'metrics_detail' => $m,
        'avg_clv_dollars' => $m['avg_clv'],
        'clv_beat_rate_pct' => $m['clv_beat_rate_pct'],
        'clv_tracked_settled' => $m['avg_clv_sample'],
        'clv_quadrants' => $clv_quadrants,
        'by_market' => $by_market,
        'by_recommendation' => $by_rec,
        'by_recommendation_sport' => $by_rec_sport,
        'pending_exposure_by_sport' => $pending_by_sport,
        'pending_stale_14d_count' => $pending_stale_14d,
        'pending_stale_14d_stake' => round($pending_stale_stake, 2),
        'oldest_stale_pending_commence' => $oldest_pending_commence,
        'stale_pending_hint' => ($pending_stale_14d > 0) ? 'Run sports_bets.php?action=settle&key=…&stale_days=21 (or 90 for backlog). Void uses commence_time OR game_date vs NOW.' : null,
        'risk_budget' => array(
            'max_single_bet_frac' => 0.05,
            'max_sport_exposure_frac' => 0.20,
            'caption' => 'Auto-place caps: single bet <= 5% bankroll; pending per sport <= 20% bankroll. MLB uses 0.85x Kelly.',
        ),
        'reconciliation_ok' => $m['reconciliation_ok'],
    );
    echo json_encode($out);
}

function sports_bet_out_json($mysqli, $rows) {
    $out = array();
    for ($i = 0; $i < count($rows); $i++) {
        $b = $rows[$i];
        $nr = sports_normalize_result(isset($b['result']) ? $b['result'] : '');
        $resUi = $nr;
        if ($resUi === 'win') {
            $resUi = 'won';
        }
        if ($resUi === 'loss') {
            $resUi = 'lost';
        }
        $out[] = array(
            'sport' => $b['sport'],
            'sport_short' => sports_sport_short($b['sport']),
            'home_team' => $b['home_team'],
            'away_team' => $b['away_team'],
            'pick' => $b['pick'],
            'market' => $b['market'],
            'bookmaker' => $b['bookmaker'],
            'odds' => floatval($b['odds']),
            'bet_amount' => floatval($b['bet_amount']),
            'ev_pct' => floatval($b['ev_pct']),
            'commence_time' => $b['commence_time'],
            'game_date' => isset($b['game_date']) ? $b['game_date'] : '',
            'result' => $resUi,
            'pnl' => isset($b['pnl']) ? floatval($b['pnl']) : null,
            'algorithm' => isset($b['algorithm']) ? $b['algorithm'] : '',
            'cohort' => isset($b['cohort']) ? $b['cohort'] : '',
        );
    }
    echo json_encode(array('ok' => true, 'bets' => $out));
}

if ($action === 'dashboard') {
    sports_dashboard($sports_mysqli);
    $sports_mysqli->close();
    exit;
}

if ($action === 'active') {
    $rows = sports_fetch_bets_rows($sports_mysqli, "(b.result IS NULL OR b.result = '') AND b.status = 'pending'");
    sports_bet_out_json($sports_mysqli, $rows);
    $sports_mysqli->close();
    exit;
}

if ($action === 'history') {
    $sport = isset($_GET['sport']) ? $_GET['sport'] : '';
    $where = "b.result IS NOT NULL AND b.result != ''";
    if ($sport !== '' && $sport !== 'all') {
        $where .= " AND b.sport = '" . $sports_mysqli->real_escape_string($sport) . "'";
    }
    $rows = sports_fetch_bets_rows($sports_mysqli, $where . " ORDER BY b.settled_at DESC LIMIT 500");
    sports_bet_out_json($sports_mysqli, $rows);
    $sports_mysqli->close();
    exit;
}

if ($action === 'auto_place') {
    if (!sports_api_key_ok($key)) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        $sports_mysqli->close();
        exit;
    }
    $min_ev = isset($_GET['min_ev']) ? floatval($_GET['min_ev']) : 3.0;
    $max_bets = isset($_GET['max_bets']) ? intval($_GET['max_bets']) : 5;
    if ($max_bets < 1) {
        $max_bets = 1;
    }
    if ($max_bets > 20) {
        $max_bets = 20;
    }

    $denyBooks = array('fliff', 'betanysports');
    $denyParts = array();
    for ($di = 0; $di < count($denyBooks); $di++) {
        $denyParts[] = "'" . $sports_mysqli->real_escape_string($denyBooks[$di]) . "'";
    }
    $denyList = implode(',', $denyParts);

    $mlbPaused = false;
    $mlbN = 0;
    $mlbPnl = 0.0;
    $mlbStake = 0.0;
    $mr = $sports_mysqli->query("SELECT result, pnl, bet_amount FROM lm_sports_bets WHERE sport LIKE '%baseball_mlb%' AND result IN ('won','win','lost','loss') ORDER BY COALESCE(settled_at, placed_at) DESC LIMIT 30");
    if ($mr) {
        while ($mx = $mr->fetch_assoc()) {
            $mlbN++;
            $mlbPnl += floatval($mx['pnl']);
            $mlbStake += floatval($mx['bet_amount']);
        }
    }
    if ($mlbN >= 10 && $mlbStake > 0) {
        $mlbRoi = $mlbPnl / $mlbStake;
        if ($mlbRoi < -0.12) {
            $mlbPaused = true;
        }
    }

    $INITIAL_BR = 1000.0;
    $pnlPre = $sports_mysqli->query("SELECT COALESCE(SUM(pnl),0) AS tp FROM lm_sports_bets WHERE result IS NOT NULL");
    $bankrollNow = $INITIAL_BR;
    if ($pnlPre && ($pr0 = $pnlPre->fetch_assoc())) {
        $bankrollNow = $INITIAL_BR + floatval($pr0['tp']);
    }
    $maxSingleStake = $bankrollNow * 0.05;
    $maxSportPendingFrac = 0.20;
    $pendingBySport = array();
    $pex0 = $sports_mysqli->query("SELECT sport, COALESCE(SUM(bet_amount),0) AS s FROM lm_sports_bets WHERE (result IS NULL OR result = '') AND status = 'pending' GROUP BY sport");
    if ($pex0) {
        while ($px = $pex0->fetch_assoc()) {
            $pendingBySport[$px['sport']] = floatval($px['s']);
        }
    }

    $q = "SELECT * FROM lm_sports_value_bets WHERE status = 'active' AND ev_pct >= " . floatval($min_ev) . "
          AND best_book_key NOT IN (" . $denyList . ")
          AND true_prob IS NOT NULL AND true_prob >= 0.25
          AND best_odds <= 5.0
          ORDER BY ev_pct DESC LIMIT " . intval($max_bets * 3);
    $r = $sports_mysqli->query($q);
    $placed = 0;
    $skipped = 0;
    $details = array();
    // Sport-specific auto-place policy (no-op when enabled=false in JSON).
    $autoPlacePolicy = sports_auto_place_policy();
    $policy_skip_reasons = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            if ($placed >= $max_bets) {
                break;
            }
            $polRes = sports_auto_place_policy_check($autoPlacePolicy, $row);
            if (!$polRes['pass']) {
                $skipped++;
                $reason = $polRes['reason'];
                if (!isset($policy_skip_reasons[$reason])) {
                    $policy_skip_reasons[$reason] = 0;
                }
                $policy_skip_reasons[$reason]++;
                continue;
            }
            $eid = $sports_mysqli->real_escape_string($row['event_id']);
            $chk = $sports_mysqli->query("SELECT id FROM lm_sports_bets WHERE event_id = '" . $eid . "' AND pick = '" . $sports_mysqli->real_escape_string($row['outcome_name']) . "' LIMIT 1");
            if ($chk && $chk->num_rows > 0) {
                $skipped++;
                continue;
            }
            $odds = floatval($row['best_odds']);
            if ($odds > 5.0) {
                $skipped++;
                continue;
            }
            $bkPlace = isset($row['best_book_key']) ? $row['best_book_key'] : '';
            if (!sports_auto_place_book_whitelisted($bkPlace)) {
                $skipped++;
                continue;
            }
            $tpRow = isset($row['true_prob']) ? floatval($row['true_prob']) : 0.0;
            if ($tpRow < 0.25) {
                $skipped++;
                continue;
            }
            if (strpos($row['sport'], 'baseball_mlb') !== false && $mlbPaused) {
                $skipped++;
                continue;
            }
            $kelly = floatval($row['kelly_bet']);
            if ($odds > 3.0) {
                $kelly = $kelly * 0.5;
            }
            if (strpos($row['sport'], 'baseball_mlb') !== false) {
                $kelly = $kelly * 0.85;
            }
            if ($kelly < 0.5) {
                $kelly = 0.5;
            }
            if ($kelly > $maxSingleStake) {
                $kelly = $maxSingleStake;
            }
            $spKey = $row['sport'];
            $pendSp = isset($pendingBySport[$spKey]) ? $pendingBySport[$spKey] : 0.0;
            $sportCap = $bankrollNow * $maxSportPendingFrac;
            if ($pendSp + $kelly > $sportCap) {
                $skipped++;
                continue;
            }
            $ct = $row['commence_time'];
            $gd = (strlen($ct) >= 10) ? substr($ct, 0, 10) : $ct;
            $imp = ($odds > 0) ? round(1.0 / $odds, 4) : 0;
            $cohortKey = $sports_mysqli->real_escape_string(sports_bets_cohort_post_guardrail_key());
            if (sports_bets_has_cohort_column($sports_mysqli)) {
                $ins = "INSERT INTO lm_sports_bets (event_id, sport, home_team, away_team, commence_time, game_date, bet_type, market, pick, pick_point, bookmaker, bookmaker_key, odds, implied_prob, bet_amount, potential_payout, algorithm, cohort, ev_pct, status, placed_at) VALUES ('"
                    . $eid . "','"
                    . $sports_mysqli->real_escape_string($row['sport']) . "','"
                    . $sports_mysqli->real_escape_string($row['home_team']) . "','"
                    . $sports_mysqli->real_escape_string($row['away_team']) . "','"
                    . $sports_mysqli->real_escape_string($ct) . "','"
                    . $sports_mysqli->real_escape_string($gd) . "','"
                    . $sports_mysqli->real_escape_string($row['bet_type']) . "','"
                    . $sports_mysqli->real_escape_string($row['market']) . "','"
                    . $sports_mysqli->real_escape_string($row['outcome_name']) . "',NULL,'"
                    . $sports_mysqli->real_escape_string($row['best_book']) . "','"
                    . $sports_mysqli->real_escape_string($row['best_book_key']) . "',"
                    . $odds . "," . $imp . ","
                    . $kelly . ","
                    . round($kelly * $odds, 2) . ",'value_bet_gr202604','"
                    . $cohortKey . "',"
                    . floatval($row['ev_pct']) . ",'pending',NOW())";
            } else {
                $ins = "INSERT INTO lm_sports_bets (event_id, sport, home_team, away_team, commence_time, game_date, bet_type, market, pick, pick_point, bookmaker, bookmaker_key, odds, implied_prob, bet_amount, potential_payout, algorithm, ev_pct, status, placed_at) VALUES ('"
                    . $eid . "','"
                    . $sports_mysqli->real_escape_string($row['sport']) . "','"
                    . $sports_mysqli->real_escape_string($row['home_team']) . "','"
                    . $sports_mysqli->real_escape_string($row['away_team']) . "','"
                    . $sports_mysqli->real_escape_string($ct) . "','"
                    . $sports_mysqli->real_escape_string($gd) . "','"
                    . $sports_mysqli->real_escape_string($row['bet_type']) . "','"
                    . $sports_mysqli->real_escape_string($row['market']) . "','"
                    . $sports_mysqli->real_escape_string($row['outcome_name']) . "',NULL,'"
                    . $sports_mysqli->real_escape_string($row['best_book']) . "','"
                    . $sports_mysqli->real_escape_string($row['best_book_key']) . "',"
                    . $odds . "," . $imp . ","
                    . $kelly . ","
                    . round($kelly * $odds, 2) . ",'value_bet_gr202604',"
                    . floatval($row['ev_pct']) . ",'pending',NOW())";
            }
            if ($sports_mysqli->query($ins)) {
                $placed++;
                if (!isset($pendingBySport[$spKey])) {
                    $pendingBySport[$spKey] = 0.0;
                }
                $pendingBySport[$spKey] += $kelly;
                $details[] = array(
                    'event' => $row['away_team'] . ' @ ' . $row['home_team'],
                    'pick' => $row['outcome_name'],
                    'market' => $row['market'],
                    'odds' => $odds,
                    'ev_pct' => floatval($row['ev_pct']),
                    'bet_amount' => $kelly,
                );
            }
        }
    }
    $pnlRow = $sports_mysqli->query("SELECT COALESCE(SUM(pnl),0) AS tp FROM lm_sports_bets WHERE result IS NOT NULL");
    $br = 1000.0;
    if ($pnlRow && ($pr = $pnlRow->fetch_assoc())) {
        $br += floatval($pr['tp']);
    }
    echo json_encode(array(
        'ok' => true,
        'bets_placed' => $placed,
        'bets_skipped' => $skipped,
        'bankroll' => round($br, 2),
        'details' => $details,
        'policy' => array(
            'mlb_auto_pause' => $mlbPaused,
            'mlb_last_n' => $mlbN,
            'mlb_sample_roi' => ($mlbStake > 0) ? round(100.0 * $mlbPnl / $mlbStake, 2) : null,
            'deny_book_keys' => $denyBooks,
            'auto_place_ship_20260404' => array(
                'max_decimal_odds' => 5.0,
                'min_true_prob' => 0.25,
                'kelly_halve_if_odds_gt' => 3.0,
                'placement_book_whitelist' => array('fanduel', 'draftkings', 'betmgm', 'betrivers', 'espnbet', 'pinnacle', 'caesars', 'coolbet', 'ballybet', 'hardrockbet', 'thescorebet', 'thescore'),
            ),
            'quarter_kelly_note' => 'Kelly from value table is capped at 25% of full Kelly upstream; odds>3 get extra 0.5x dampening; then capped at 5% bankroll per ticket and 20% bankroll pending per sport.',
            'max_single_bet_dollars' => round($maxSingleStake, 2),
            'max_sport_pending_frac' => $maxSportPendingFrac,
            'bankroll_used_for_caps' => round($bankrollNow, 2),
        ),
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'settle') {
    if (!sports_api_key_ok($key)) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        $sports_mysqli->close();
        exit;
    }
    // Void any pending bet whose game is > stale_days days in the past and
    // was never graded (no score API settlement ran). Voiding preserves
    // accounting honesty: we don't invent a result, we mark it void with pnl=0,
    // freeing the reserved stake. Default stale_days=14; max 730 for backlog drain.
    $staleDays = isset($_GET['stale_days']) ? intval($_GET['stale_days']) : 14;
    if ($staleDays < 1) { $staleDays = 1; }
    if ($staleDays > 730) { $staleDays = 730; }
    $stalePred = sports_bets_stale_pending_predicate_sql($staleDays);
    $pre = $sports_mysqli->query("SELECT id, sport, home_team, away_team, commence_time, game_date, bet_amount FROM lm_sports_bets WHERE status = 'pending' AND (result IS NULL OR result = '') AND " . $stalePred . " ORDER BY commence_time ASC");
    $voidedDetails = array();
    $voidedStake = 0.0;
    if ($pre) {
        while ($vr = $pre->fetch_assoc()) {
            $voidedStake += floatval($vr['bet_amount']);
            $voidedDetails[] = array(
                'id' => intval($vr['id']),
                'event' => $vr['away_team'] . ' @ ' . $vr['home_team'],
                'sport' => $vr['sport'],
                'commence_time' => $vr['commence_time'],
                'game_date' => isset($vr['game_date']) ? $vr['game_date'] : null,
                'stake' => floatval($vr['bet_amount']),
            );
        }
    }
    $upd = $sports_mysqli->query("UPDATE lm_sports_bets SET result = 'void', status = 'void', pnl = 0, settled_at = NOW() WHERE status = 'pending' AND (result IS NULL OR result = '') AND " . $stalePred);
    $voided = $upd ? intval($sports_mysqli->affected_rows) : 0;

    $INITIAL = 1000.0;
    $prow = 0.0;
    $pq = $sports_mysqli->query("SELECT COALESCE(SUM(pnl),0) AS tp FROM lm_sports_bets WHERE result IN ('won','win','lost','loss','push')");
    if ($pq && ($prr = $pq->fetch_assoc())) {
        $prow = floatval($prr['tp']);
    }
    echo json_encode(array(
        'ok' => true,
        'settled' => 0,
        'won' => 0,
        'lost' => 0,
        'push' => 0,
        'voided' => $voided,
        'voided_stake_freed' => round($voidedStake, 2),
        'voided_details' => $voidedDetails,
        'stale_days_threshold' => $staleDays,
        'net_pnl' => 0,
        'bankroll' => round($INITIAL + $prow, 2),
        'note' => 'Void-stale only (commence_time OR game_date older than stale_days). Score-based grading: action=settle_by_scores (Odds API /scores, days_from<=3). Use stale_days=60–120 once to drain multi-month backlog.',
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'settle_by_scores') {
    // Real score-based settlement using The Odds API /scores endpoint.
    // For each sport with recent pending bets, fetch completed game scores
    // (daysFrom=1|2|3), match by event_id, then grade each bet by its market.
    // Credit cost: 2 per sport per call (cheap, fits 500/month budget).
    if (!sports_api_key_ok($key)) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        $sports_mysqli->close();
        exit;
    }
    require_once dirname(__FILE__) . '/db_config.php';
    $apiKey = isset($THE_ODDS_API_KEY) ? $THE_ODDS_API_KEY : '';
    if ($apiKey === '') {
        echo json_encode(array('ok' => false, 'error' => 'missing THE_ODDS_API_KEY'));
        $sports_mysqli->close();
        exit;
    }
    $daysFrom = isset($_GET['days_from']) ? intval($_GET['days_from']) : 3;
    if ($daysFrom < 1) { $daysFrom = 1; }
    if ($daysFrom > 3) { $daysFrom = 3; }
    // DB lookback for which pending rows to consider (was incorrectly tied to daysFrom=3).
    $lookbackDays = isset($_GET['lookback_days']) ? intval($_GET['lookback_days']) : 30;
    if ($lookbackDays < 1) { $lookbackDays = 1; }
    if ($lookbackDays > 120) { $lookbackDays = 120; }

    // Find distinct sports with pending bets in the grading window.
    $sportsWithPending = array();
    $sw = $sports_mysqli->query("SELECT DISTINCT sport FROM lm_sports_bets WHERE status = 'pending' AND (result IS NULL OR result = '') AND commence_time < NOW() AND commence_time >= DATE_SUB(NOW(), INTERVAL " . intval($lookbackDays) . " DAY)");
    if ($sw) {
        while ($swr = $sw->fetch_assoc()) {
            $sportsWithPending[] = $swr['sport'];
        }
    }
    if (count($sportsWithPending) === 0) {
        echo json_encode(array(
            'ok' => true,
            'settled' => 0,
            'won' => 0, 'lost' => 0, 'push' => 0, 'voided' => 0,
            'net_pnl' => 0,
            'sports_scanned' => 0,
            'lookback_days' => $lookbackDays,
            'scores_api_days_from' => $daysFrom,
            'note' => 'No pending bets with commence_time in lookback_days (or none started).',
        ));
        $sports_mysqli->close();
        exit;
    }

    $totalSettled = 0; $totalWon = 0; $totalLost = 0; $totalPush = 0; $totalVoid = 0;
    $netPnl = 0.0; $details = array(); $creditsUsed = 0;
    for ($spi = 0; $spi < count($sportsWithPending); $spi++) {
        $sport = $sportsWithPending[$spi];
        $scoreMap = sports_scores_fetch_score_map($sport, $apiKey, $daysFrom, $creditsUsed);
        if ($scoreMap === null) {
            $details[] = array('sport' => $sport, 'error' => 'http_or_json_fail');
            continue;
        }
        if (sports_scores_completed_count($scoreMap) === 0) {
            $details[] = array('sport' => $sport, 'completed_games' => 0);
            continue;
        }
        $sportEsc = $sports_mysqli->real_escape_string($sport);
        $pq = $sports_mysqli->query("SELECT id, event_id, home_team, away_team, bet_type, market, pick, pick_point, odds, bet_amount, commence_time FROM lm_sports_bets WHERE sport = '" . $sportEsc . "' AND status = 'pending' AND (result IS NULL OR result = '') AND commence_time < NOW() AND commence_time >= DATE_SUB(NOW(), INTERVAL " . intval($lookbackDays) . " DAY)");
        if ($pq) {
            while ($b = $pq->fetch_assoc()) {
                $eid = $b['event_id'];
                $sm = sports_scores_find_match($scoreMap, $sport, $eid, $b['home_team'], $b['away_team'], isset($b['commence_time']) ? $b['commence_time'] : '');
                if ($sm === null) {
                    continue;
                }
                $hs = $sm['home'];
                $as = $sm['away'];
                $pt = ($b['pick_point'] === null || $b['pick_point'] === '') ? null : floatval($b['pick_point']);
                $graded = sports_scores_grade_ticket($sm, $b['market'], $b['pick'], $pt, floatval($b['odds']), floatval($b['bet_amount']));
                if ($graded === null) {
                    continue;
                }
                $result = $graded['result'];
                $pnl = $graded['pnl'];
                $resEsc = $sports_mysqli->real_escape_string($result);
                $sports_mysqli->query("UPDATE lm_sports_bets SET result = '" . $resEsc . "', status = 'settled', pnl = " . floatval($pnl) . ", settled_at = NOW(), actual_home_score = " . intval($hs) . ", actual_away_score = " . intval($as) . " WHERE id = " . intval($b['id']));
                $totalSettled++;
                $netPnl += $pnl;
                if ($result === 'won') {
                    $totalWon++;
                } else if ($result === 'lost') {
                    $totalLost++;
                } else if ($result === 'push') {
                    $totalPush++;
                }
                $details[] = array(
                    'id' => intval($b['id']),
                    'event' => $b['away_team'] . ' @ ' . $b['home_team'],
                    'sport' => $sport,
                    'market' => $b['market'],
                    'pick' => $b['pick'],
                    'score' => $hs . '-' . $as,
                    'result' => $result,
                    'pnl' => $pnl,
                );
            }
        }
    }
    // Recompute bankroll after settlement.
    $INITIAL_BR = 1000.0;
    $prq = $sports_mysqli->query("SELECT COALESCE(SUM(pnl),0) AS tp FROM lm_sports_bets WHERE result IN ('won','win','lost','loss','push')");
    $totalPnlAll = 0.0;
    if ($prq && ($prrr = $prq->fetch_assoc())) {
        $totalPnlAll = floatval($prrr['tp']);
    }
    echo json_encode(array(
        'ok' => true,
        'settled' => $totalSettled,
        'won' => $totalWon,
        'lost' => $totalLost,
        'push' => $totalPush,
        'voided' => $totalVoid,
        'net_pnl' => round($netPnl, 2),
        'bankroll' => round($INITIAL_BR + $totalPnlAll, 2),
        'sports_scanned' => count($sportsWithPending),
        'credits_used' => $creditsUsed,
        'lookback_days' => $lookbackDays,
        'scores_api_days_from' => $daysFrom,
        'details' => $details,
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'void_pending') {
    if (!sports_api_key_ok($key)) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        $sports_mysqli->close();
        exit;
    }
    $idsRaw = isset($_GET['ids']) ? $_GET['ids'] : '';
    $parts = explode(',', $idsRaw);
    $ids = array();
    for ($i = 0; $i < count($parts); $i++) {
        $v = intval(trim($parts[$i]));
        if ($v > 0) {
            $ids[] = $v;
        }
    }
    $ids = array_values(array_unique($ids));
    if (count($ids) < 1) {
        echo json_encode(array('ok' => false, 'error' => 'ids required (comma-separated lm_sports_bets.id)'));
        $sports_mysqli->close();
        exit;
    }
    if (count($ids) > 50) {
        echo json_encode(array('ok' => false, 'error' => 'max 50 ids'));
        $sports_mysqli->close();
        exit;
    }
    $idSql = implode(',', $ids);
    $pre = $sports_mysqli->query("SELECT id, pick, odds, bookmaker_key, bet_amount, home_team, away_team FROM lm_sports_bets WHERE id IN (" . $idSql . ") AND status = 'pending' AND (result IS NULL OR result = '')");
    $before = array();
    $stakeSum = 0.0;
    if ($pre) {
        while ($row = $pre->fetch_assoc()) {
            $stakeSum += floatval($row['bet_amount']);
            $before[] = array(
                'id' => intval($row['id']),
                'pick' => $row['pick'],
                'odds' => floatval($row['odds']),
                'bookmaker_key' => isset($row['bookmaker_key']) ? $row['bookmaker_key'] : '',
                'stake' => floatval($row['bet_amount']),
                'event' => $row['away_team'] . ' @ ' . $row['home_team'],
            );
        }
    }
    $upd = $sports_mysqli->query("UPDATE lm_sports_bets SET result = 'void', status = 'void', pnl = 0, settled_at = NOW() WHERE id IN (" . $idSql . ") AND status = 'pending' AND (result IS NULL OR result = '')");
    $voided = $upd ? intval($sports_mysqli->affected_rows) : 0;
    $reasonOut = isset($_GET['reason']) ? substr(strval($_GET['reason']), 0, 160) : 'manual_void';
    echo json_encode(array(
        'ok' => true,
        'voided' => $voided,
        'reason' => $reasonOut,
        'stake_freed_est' => round($stakeSum, 2),
        'matched_pending' => $before,
        'note' => 'Void selected pending ids: pnl=0; stake freed for paper bankroll. Use action=active or DB to list ids.',
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'grade_manual') {
    // Bypass The Odds API /scores when it's not flagging completed games.
    // Caller posts JSON {"rows":[{sport,event_id,home_team,away_team,commence_time,home_score,away_score},...]}.
    // We fold each row into an Odds-API-shaped game record, build a scoreMap via
    // sports_scores_map_from_games_array, then grade pending lm_sports_bets via the
    // same alias-matching path settle_by_scores uses. event_id match wins; date+team
    // alias is the fallback so backlog tickets with mismatched/missing event_ids still grade.
    if (!sports_api_key_ok($key)) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        $sports_mysqli->close();
        exit;
    }
    $raw = file_get_contents('php://input');
    $payload = @json_decode($raw, true);
    $rows = (isset($payload['rows']) && is_array($payload['rows'])) ? $payload['rows'] : array();
    if (count($rows) === 0) {
        echo json_encode(array(
            'ok' => false,
            'error' => 'no rows',
            'expected' => 'POST {"rows":[{sport,event_id,home_team,away_team,commence_time,home_score,away_score},...]}',
        ));
        $sports_mysqli->close();
        exit;
    }
    $bySport = array();
    for ($ri = 0; $ri < count($rows); $ri++) {
        $r = $rows[$ri];
        $sport = isset($r['sport']) ? trim(strval($r['sport'])) : '';
        $home = isset($r['home_team']) ? strval($r['home_team']) : '';
        $away = isset($r['away_team']) ? strval($r['away_team']) : '';
        if ($sport === '' || $home === '' || $away === '') {
            continue;
        }
        $game = array(
            'id' => isset($r['event_id']) ? strval($r['event_id']) : '',
            'completed' => true,
            'home_team' => $home,
            'away_team' => $away,
            'commence_time' => isset($r['commence_time']) ? strval($r['commence_time']) : '',
            'scores' => array(
                array('name' => $home, 'score' => intval(isset($r['home_score']) ? $r['home_score'] : 0)),
                array('name' => $away, 'score' => intval(isset($r['away_score']) ? $r['away_score'] : 0)),
            ),
        );
        if (!isset($bySport[$sport])) {
            $bySport[$sport] = array();
        }
        $bySport[$sport][] = $game;
    }
    $totalSettled = 0; $totalWon = 0; $totalLost = 0; $totalPush = 0;
    $netPnl = 0.0; $details = array();
    foreach ($bySport as $sport => $games) {
        $scoreMap = sports_scores_map_from_games_array($sport, $games);
        $sportEsc = $sports_mysqli->real_escape_string($sport);
        $pq = $sports_mysqli->query("SELECT id, event_id, home_team, away_team, market, pick, pick_point, bet_type, odds, bet_amount, commence_time FROM lm_sports_bets WHERE sport = '" . $sportEsc . "' AND status = 'pending' AND (result IS NULL OR result = '')");
        if ($pq) {
            while ($b = $pq->fetch_assoc()) {
                $sm = sports_scores_find_match($scoreMap, $sport, $b['event_id'], $b['home_team'], $b['away_team'], isset($b['commence_time']) ? $b['commence_time'] : '');
                if ($sm === null) {
                    continue;
                }
                $pt = ($b['pick_point'] === null || $b['pick_point'] === '') ? null : floatval($b['pick_point']);
                // auto_place historically inserted pick_point=NULL even for spreads/totals,
                // leaving the line in bet_type only (e.g. "Over 5.50", "Spurs +4.5"). Without
                // this fallback every backlog totals/spreads ticket is ungradeable.
                if ($pt === null && isset($b['bet_type']) && $b['bet_type'] !== '') {
                    if (preg_match('/(-?\d+\.?\d*)\s*$/', trim(strval($b['bet_type'])), $mch)) {
                        $pt = floatval($mch[1]);
                    }
                }
                $graded = sports_scores_grade_ticket($sm, $b['market'], $b['pick'], $pt, floatval($b['odds']), floatval($b['bet_amount']));
                if ($graded === null) {
                    continue;
                }
                $resEsc = $sports_mysqli->real_escape_string($graded['result']);
                $sports_mysqli->query("UPDATE lm_sports_bets SET result = '" . $resEsc . "', status = 'settled', pnl = " . floatval($graded['pnl']) . ", settled_at = NOW(), actual_home_score = " . intval($sm['home']) . ", actual_away_score = " . intval($sm['away']) . " WHERE id = " . intval($b['id']));
                $totalSettled++;
                $netPnl += $graded['pnl'];
                if ($graded['result'] === 'won') { $totalWon++; }
                else if ($graded['result'] === 'lost') { $totalLost++; }
                else if ($graded['result'] === 'push') { $totalPush++; }
                $details[] = array(
                    'id' => intval($b['id']),
                    'event' => $b['away_team'] . ' @ ' . $b['home_team'],
                    'sport' => $sport,
                    'market' => $b['market'],
                    'pick' => $b['pick'],
                    'score' => $sm['home'] . '-' . $sm['away'],
                    'result' => $graded['result'],
                    'pnl' => $graded['pnl'],
                );
            }
        }
    }
    $INITIAL_BR = 1000.0;
    $prq = $sports_mysqli->query("SELECT COALESCE(SUM(pnl),0) AS tp FROM lm_sports_bets WHERE result IN ('won','win','lost','loss','push')");
    $totalPnlAll = 0.0;
    if ($prq && ($prr = $prq->fetch_assoc())) {
        $totalPnlAll = floatval($prr['tp']);
    }
    echo json_encode(array(
        'ok' => true,
        'settled' => $totalSettled,
        'won' => $totalWon,
        'lost' => $totalLost,
        'push' => $totalPush,
        'net_pnl' => round($netPnl, 2),
        'bankroll' => round($INITIAL_BR + $totalPnlAll, 2),
        'rows_received' => count($rows),
        'sports_in_payload' => count($bySport),
        'details' => $details,
        'note' => 'Manual score grading — bypasses Odds API /scores. Same alias-matching as settle_by_scores.',
    ));
    $sports_mysqli->close();
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'unknown action'));
$sports_mysqli->close();
