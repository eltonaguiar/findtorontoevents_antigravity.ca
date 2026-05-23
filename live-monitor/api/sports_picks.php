<?php
/**
 * Daily picks, performance analytics, pick history, analyze; settle_picks grades via Odds /scores.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/sports_db.php';
require_once dirname(__FILE__) . '/sports_metrics_lib.php';
require_once dirname(__FILE__) . '/sports_scores_settle_lib.php';
require_once dirname(__FILE__) . '/sports_value_nhl_goalie_lib.php';
require_once dirname(__FILE__) . '/tennis_elo_lib.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'today';

function sports_picks_key_ok($k) {
    $expected = getenv('ADMIN_API_KEY');
    if ($expected === false || $expected === '') {
        return false; // Key not configured — deny all admin access
    }
    return ($k === $expected);
}

function sports_ca_book($key) {
    $k = strtolower($key);
    $ca = array('fanduel', 'draftkings', 'betmgm', 'betrivers', 'espnbet', 'ballybet', 'hardrockbet', 'pinnacle', 'coolbet', 'leovegas', 'thescorebet', 'thescore', 'betway', 'unibet', 'olg_prolineplus', 'olg', 'prolineplus');
    for ($i = 0; $i < count($ca); $i++) {
        if (strpos($k, $ca[$i]) !== false) {
            return true;
        }
    }
    return false;
}

function sports_ev_to_grade($ev) {
    if ($ev >= 12) {
        return 'A';
    }
    if ($ev >= 8) {
        return 'B+';
    }
    if ($ev >= 5) {
        return 'B';
    }
    if ($ev >= 3) {
        return 'C+';
    }
    return 'C';
}

function sports_ev_to_rec($ev) {
    if ($ev >= 10) {
        return 'STRONG TAKE';
    }
    if ($ev >= 6) {
        return 'TAKE';
    }
    if ($ev >= 3) {
        return 'LEAN';
    }
    if ($ev >= 1) {
        return 'LOW EDGE';
    }
    return 'SKIP';
}

/**
 * Return a one-line explanation for each recommendation tier, suitable for a
 * tooltip or secondary text. Context-aware so "LOW EDGE" no longer reads as
 * a generic "wait for something".
 */
function sports_ev_rec_detail($rec) {
    if ($rec === 'STRONG TAKE') {
        return 'Strong value: 10%+ EV vs. multi-book consensus. Full Kelly sizing.';
    }
    if ($rec === 'TAKE') {
        return 'Solid value: 6-10% EV. Standard Kelly sizing.';
    }
    if ($rec === 'LEAN') {
        return 'Modest value: 3-6% EV. Smaller stake or part of a portfolio.';
    }
    if ($rec === 'LOW EDGE') {
        return 'Marginal value: 1-3% EV. Below confident-bet threshold - skip as a standalone pick; monitor for line movement or stack with correlated picks.';
    }
    return 'No meaningful edge - consensus agrees with the book price.';
}

function sports_decimal_to_american($dec) {
    $d = floatval($dec);
    if ($d <= 1.01) {
        return '-';
    }
    if ($d >= 2.0) {
        return '+' . strval(round(($d - 1.0) * 100));
    }
    return strval(round(-100.0 / ($d - 1.0)));
}

function sports_pm_norm($s) {
    $v = strtolower((string)$s);
    $v = preg_replace('/[^a-z0-9]+/', ' ', $v);
    $v = trim($v);
    return $v;
}

function sports_pm_load_signals() {
    $candidates = array(
        dirname(__FILE__) . '/../backfill/sports_prediction_market_signals.json',
        dirname(__FILE__) . '/../../alpha_engine/data/sports_prediction_market_signals.json',
    );
    for ($i = 0; $i < count($candidates); $i++) {
        $p = $candidates[$i];
        if (!file_exists($p)) {
            continue;
        }
        $raw = @file_get_contents($p);
        if ($raw === false || $raw === '') {
            continue;
        }
        $obj = @json_decode($raw, true);
        if (!is_array($obj) || !isset($obj['signals']) || !is_array($obj['signals'])) {
            continue;
        }
        return $obj['signals'];
    }
    return array();
}

function sports_pm_best_match($signals, $home_team, $away_team) {
    $home = sports_pm_norm($home_team);
    $away = sports_pm_norm($away_team);
    if ($home === '' && $away === '') {
        return null;
    }

    $best = null;
    $bestScore = -1.0;
    for ($i = 0; $i < count($signals); $i++) {
        $s = $signals[$i];
        if (!is_array($s)) {
            continue;
        }
        $q = sports_pm_norm(isset($s['question']) ? $s['question'] : '');
        if ($q === '') {
            continue;
        }

        $score = 0.0;
        if ($home !== '' && strpos($q, $home) !== false) {
            $score += 1.0;
        }
        if ($away !== '' && strpos($q, $away) !== false) {
            $score += 1.0;
        }

        if ($score < 1.0) {
            continue;
        }

        $conf = floatval(isset($s['confidence']) ? $s['confidence'] : 0);
        $vol = floatval(isset($s['volume_usd']) ? $s['volume_usd'] : 0);
        $quality = $score * 1000000.0 + $conf * 1000.0 + $vol;
        if ($quality > $bestScore) {
            $bestScore = $quality;
            $best = $s;
        }
    }
    return $best;
}

/**
 * AND-clause for filtering lm_sports_value_bets by the same sport / alias
 * rules as WHERE on lm_sports_daily_picks in sports_action_today.
 */
function sports_picks_vb_sport_and_clause($mysqli, $sport) {
    if ($sport === '' || $sport === 'all') {
        return '';
    }
    if ($sport === 'NBA') {
        return " AND sport LIKE '%basketball_nba%'";
    }
    if ($sport === 'NHL') {
        return " AND sport LIKE '%icehockey_nhl%'";
    }
    if ($sport === 'NFL') {
        return " AND sport LIKE '%americanfootball_nfl%'";
    }
    if ($sport === 'MLB') {
        return " AND sport LIKE '%baseball_mlb%'";
    }
    if ($sport === 'MLS') {
        return " AND sport LIKE '%soccer_usa_mls%'";
    }
    if ($sport === 'NCAAB') {
        return " AND sport LIKE '%basketball_ncaab%'";
    }
    if ($sport === 'NCAAF') {
        return " AND sport LIKE '%americanfootball_ncaaf%'";
    }
    if ($sport === 'CFL') {
        return " AND sport LIKE '%americanfootball_cfl%'";
    }
    $sp = $mysqli->real_escape_string($sport);
    return " AND sport = '" . $sp . "'";
}

/**
 * High-EV active rows in lm_sports_value_bets that do not pass auto_place
 * policy (true_prob<0.25 or best_odds>5). Key-authenticated; read-only.
 */
function sports_action_edge_policy_audit($mysqli) {
    $minEv = isset($_GET['min_ev']) ? floatval($_GET['min_ev']) : 4.0;
    if ($minEv < 0) {
        $minEv = 0.0;
    }
    $evSql = (string) $minEv;
    $base = "SELECT id, event_id, sport, home_team, away_team, market, bet_type, outcome_name, best_book, best_book_key, best_odds, true_prob, ev_pct, edge_pct, commence_time "
        . "FROM lm_sports_value_bets "
        . "WHERE status = 'active' AND commence_time >= NOW() AND commence_time < DATE_ADD(NOW(), INTERVAL 48 HOUR) AND ev_pct >= " . $evSql;

    $lowTp = array();
    $q1 = $mysqli->query($base . " AND (true_prob IS NULL OR true_prob < 0.25) ORDER BY ev_pct DESC LIMIT 30");
    if ($q1) {
        while ($row = $q1->fetch_assoc()) {
            $lowTp[] = array(
                'id' => intval($row['id']),
                'event_id' => $row['event_id'],
                'sport' => $row['sport'],
                'matchup' => $row['away_team'] . ' @ ' . $row['home_team'],
                'bet_type' => isset($row['bet_type']) ? $row['bet_type'] : '',
                'best_book_key' => isset($row['best_book_key']) ? $row['best_book_key'] : '',
                'best_odds' => floatval($row['best_odds']),
                'true_prob' => isset($row['true_prob']) ? floatval($row['true_prob']) : null,
                'ev_pct' => floatval($row['ev_pct']),
                'commence_time' => $row['commence_time'],
                'auto_place_block' => 'min_true_prob_0.25',
            );
        }
    }
    $highOdds = array();
    $q2 = $mysqli->query($base . " AND best_odds > 5.0 ORDER BY ev_pct DESC LIMIT 30");
    if ($q2) {
        while ($row = $q2->fetch_assoc()) {
            $highOdds[] = array(
                'id' => intval($row['id']),
                'event_id' => $row['event_id'],
                'sport' => $row['sport'],
                'matchup' => $row['away_team'] . ' @ ' . $row['home_team'],
                'bet_type' => isset($row['bet_type']) ? $row['bet_type'] : '',
                'best_book_key' => isset($row['best_book_key']) ? $row['best_book_key'] : '',
                'best_odds' => floatval($row['best_odds']),
                'true_prob' => isset($row['true_prob']) ? floatval($row['true_prob']) : null,
                'ev_pct' => floatval($row['ev_pct']),
                'commence_time' => $row['commence_time'],
                'auto_place_block' => 'max_decimal_odds_5.0',
            );
        }
    }
    echo json_encode(array(
        'ok' => true,
        'min_ev_param' => $minEv,
        'explanation' => 'Rows on both lists may show on the Today page but be skipped or dampened in sports_bets.php auto_place (true_prob, odds, book whitelist, caps).',
        'low_true_prob' => $lowTp,
        'high_odds' => $highOdds,
    ));
}

/**
 * Composite-score nudge when a high-quality PM market confirms the side.
 * Gated on a delta-vs-bookmaker check: PM confidence must beat the
 * bookmaker's raw implied probability by >= 3pp, otherwise the PM signal
 * is in agreement-with-vig (not real confirmation) and we skip the nudge.
 *
 * Without the delta gate, a PM market at 60% confidence on a sportsbook
 * 90%-implied favorite would earn a +2 nudge — but that's actually
 * disagreement, not confirmation. See PR #399 review for rationale.
 *
 * Pass $bookOdds (decimal) when available; pass null/<=1.0 to fall back
 * to the absolute-confidence behavior (preserves call-sites that don't
 * have odds in scope yet).
 */
function sports_pm_score_nudge($pmConf, $pmVol, $bookOdds = null) {
    if ($bookOdds !== null && floatval($bookOdds) > 1.0) {
        $bookImplied = 1.0 / floatval($bookOdds);
        // Require PM to lead the bookmaker raw implied by >= 3pp before any nudge.
        if (floatval($pmConf) - $bookImplied < 0.03) {
            return 0;
        }
    }
    if ($pmConf >= 0.70 && $pmVol >= 100000.0) {
        return 6;
    }
    if ($pmConf >= 0.65 && $pmVol >= 25000.0) {
        return 4;
    }
    if ($pmConf >= 0.60 && $pmVol >= 5000.0) {
        return 2;
    }
    return 0;
}

/**
 * Annotate a pick payload with goalie overlay metadata when the bucket
 * (sport/home_team/away_team) matches a confirmed NHL starter pair with
 * GP >= 10 in nhl_goalies_today.json. No-op for non-NHL or missing data.
 * Mutates $vb in place.
 */
function sports_picks_annotate_goalie_overlay(&$vb) {
    $bucket = array(
        'sport' => isset($vb['sport']) ? $vb['sport'] : '',
        'home_team' => isset($vb['home_team']) ? $vb['home_team'] : '',
        'away_team' => isset($vb['away_team']) ? $vb['away_team'] : '',
    );
    if (strpos(strval($bucket['sport']), 'icehockey_nhl') === false) {
        return;
    }
    $mkt = isset($vb['market']) ? strtolower(strval($vb['market'])) : '';
    if ($mkt !== '' && $mkt !== 'h2h') {
        return;
    }
    $info = sports_value_nhl_goalie_lookup_for_bucket($bucket);
    if ($info === null || empty($info['both_confirmed'])) {
        return;
    }
    $hg = $info['home_goalie'];
    $ag = $info['away_goalie'];
    $hgp = isset($hg['gp']) ? intval($hg['gp']) : 0;
    $agp = isset($ag['gp']) ? intval($ag['gp']) : 0;
    if ($hgp < 10 || $agp < 10) {
        return;
    }
    if (!isset($hg['gsax_per60']) || $hg['gsax_per60'] === null
            || !isset($ag['gsax_per60']) || $ag['gsax_per60'] === null) {
        return;
    }
    $delta = floatval($hg['gsax_per60']) - floatval($ag['gsax_per60']);
    $shift = $delta * 5.0;
    if ($shift > 5.0) { $shift = 5.0; }
    if ($shift < -5.0) { $shift = -5.0; }
    if (isset($hg['rest_days']) && intval($hg['rest_days']) === 0) { $shift -= 1.0; }
    if (isset($ag['rest_days']) && intval($ag['rest_days']) === 0) { $shift += 1.0; }
    $vb['goalie_overlay_applied'] = true;
    $vb['goalie_shift_pp'] = round($shift, 2);
    $vb['goalie_home_name'] = isset($hg['name']) ? $hg['name'] : '';
    $vb['goalie_away_name'] = isset($ag['name']) ? $ag['name'] : '';
    $vb['goalie_gsax_delta'] = round($delta, 3);
}

function sports_action_today($mysqli) {
    $sport = isset($_GET['sport']) ? $_GET['sport'] : 'all';
    $pmSignals = sports_pm_load_signals();
    $pmMatchedCount = 0;
    $dual_mode = 'ev_primary';
    if (isset($_GET['dual_mode']) && $_GET['dual_mode'] === 'stability') {
        $dual_mode = 'stability';
    }
    $dr = $mysqli->query("SELECT MAX(pick_date) AS d FROM lm_sports_daily_picks");
    
    // Default to EST today
    $estTz = new DateTimeZone('America/New_York');
    $estNow = new DateTime('now', $estTz);
    $pickDate = $estNow->format('Y-m-d');

    if ($dr && ($drow = $dr->fetch_assoc()) && $drow['d'] !== null && $drow['d'] !== '') {
        $pickDate = $drow['d'];
    }
    $where = "pick_date = '" . $mysqli->real_escape_string($pickDate) . "'";
    if ($sport !== '' && $sport !== 'all') {
        $sp = $mysqli->real_escape_string($sport);
        if ($sport === 'NBA') {
            $where .= " AND sport LIKE '%basketball_nba%'";
        } else if ($sport === 'NHL') {
            $where .= " AND sport LIKE '%icehockey_nhl%'";
        } else if ($sport === 'NFL') {
            $where .= " AND sport LIKE '%americanfootball_nfl%'";
        } else if ($sport === 'MLB') {
            $where .= " AND sport LIKE '%baseball_mlb%'";
        } else if ($sport === 'MLS') {
            $where .= " AND sport LIKE '%soccer_usa_mls%'";
        } else if ($sport === 'NCAAB') {
            $where .= " AND sport LIKE '%basketball_ncaab%'";
        } else {
            $where .= " AND sport = '" . $sp . "'";
        }
    }
    $r = $mysqli->query("SELECT * FROM lm_sports_daily_picks WHERE " . $where . " ORDER BY ev_pct DESC");
    $value_bets = array();
    $strong = 0;
    $takes = 0;
    $waits = 0;
    $sumEv = 0.0;
    $line_shops = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $ev = floatval($row['ev_pct']);
            $sumEv += $ev;
            $rec = sports_ev_to_rec($ev);
            if ($rec === 'STRONG TAKE') {
                $strong++;
            }
            if ($rec === 'TAKE' || $rec === 'STRONG TAKE') {
                $takes++;
            }
            if ($rec === 'LOW EDGE' || $rec === 'WAIT' || $rec === 'SKIP') {
                $waits++;
            }
            $grade = sports_ev_to_grade($ev);
            $score = min(100, intval(35 + $ev * 4));
            $bk = isset($row['best_book_key']) ? $row['best_book_key'] : '';
            $decOdds = floatval($row['best_odds']);
            $bookBonus = sports_ca_book($bk) ? 6 : 0;
            $oddNudge = 0;
            if ($decOdds > 0 && $decOdds < 2.5) {
                $oddNudge = 4;
            } else if ($decOdds >= 6.0) {
                $oddNudge = 2;
            }
            $composite_score = min(100, intval(22 + $ev * 2.6 + $bookBonus + $oddNudge));
            if ($dual_mode === 'stability') {
                $composite_score = min(100, intval(30 + $ev * 2.0 + ($bookBonus * 0.5)));
            }
            $vb = array(
                'sport' => $row['sport'],
                'sport_short' => sports_sport_short($row['sport']),
                'home_team' => $row['home_team'],
                'away_team' => $row['away_team'],
                'commence_time' => $row['commence_time'],
                'game_date' => isset($row['pick_date']) ? $row['pick_date'] : '',
                'market' => $row['market'],
                'bet_type' => $row['pick_type'],
                'outcome_name' => $row['outcome_name'],
                'best_book' => $row['best_book'],
                'best_odds' => $decOdds,
                'american_odds' => sports_decimal_to_american($row['best_odds']),
                'ev_pct' => $ev,
                'kelly_bet' => floatval($row['kelly_bet']),
                'win_probability' => ($row['best_odds'] > 0) ? round(100.0 / floatval($row['best_odds']), 2) : 0,
                'rating_grade' => $grade,
                'rating_score' => $score,
                'composite_score' => $composite_score,
                'dual_mode' => $dual_mode,
                'recommendation' => $rec,
                'rec_detail' => sports_ev_rec_detail($rec),
                'rating_reasons' => array('EV% from multi-book consensus', 'CA-legal book boost when applicable', 'Composite blends EV, book quality, odds bucket'),
                'is_canadian_book' => sports_ca_book($bk),
                'event_id' => $row['event_id'],
                'result' => isset($row['result']) ? $row['result'] : null,
                'is_finished' => (
                    (isset($row['result']) && $row['result'] !== null && $row['result'] !== '')
                    || (!empty($row['commence_time']) && strtotime($row['commence_time']) < (time() - 3 * 3600))
                ),
            );

            $pm = sports_pm_best_match($pmSignals, $row['home_team'], $row['away_team']);
            if (is_array($pm)) {
                $pmMatchedCount++;
                $pmConf = floatval(isset($pm['confidence']) ? $pm['confidence'] : 0);
                $pmVol = floatval(isset($pm['volume_usd']) ? $pm['volume_usd'] : 0);
                $vb['prediction_market_source'] = isset($pm['source']) ? $pm['source'] : 'polymarket';
                $vb['prediction_market_confidence'] = round($pmConf, 4);
                $vb['prediction_market_volume_usd'] = round($pmVol, 2);
                $vb['prediction_market_hint'] = isset($pm['question']) ? $pm['question'] : '';
                $vb['rating_reasons'][] = 'Prediction market confirmation: conf ' . round($pmConf * 100.0, 1) . '%, vol $' . round($pmVol, 0);

                // Additive composite-score nudge when a high-quality PM market
                // confirms the side. Caps at +6 pts; EV%, grade, recommendation
                // and Kelly are unchanged. A liquid (>= $25k) and confident
                // (>= 0.65) market is treated as an independent signal channel.
                $pmNudge = sports_pm_score_nudge($pmConf, $pmVol, $vb['best_odds']);
                if ($pmNudge > 0) {
                    $vb['composite_score'] = min(100, intval($vb['composite_score']) + $pmNudge);
                    $vb['prediction_market_score_boost'] = $pmNudge;
                }
            }
            sports_picks_annotate_goalie_overlay($vb);
            sports_picks_annotate_tennis_elo($vb);
            $value_bets[] = $vb;

            $ao = isset($row['all_odds']) ? $row['all_odds'] : '';
            if ($ao !== '' && count($line_shops) < 8) {
                $decoded = json_decode($ao, true);
                if (is_array($decoded) && count($decoded) > 0) {
                    $mkts = array();
                    $bestP = 0;
                    $worstP = 999;
                    $bestB = '';
                    $worstB = '';
                    for ($oi = 0; $oi < count($decoded); $oi++) {
                        $o = $decoded[$oi];
                        $pr = isset($o['price']) ? floatval($o['price']) : 0;
                        if ($pr > $bestP) {
                            $bestP = $pr;
                            $bestB = isset($o['book_name']) ? $o['book_name'] : '';
                        }
                        if ($pr > 0 && $pr < $worstP) {
                            $worstP = $pr;
                            $worstB = isset($o['book_name']) ? $o['book_name'] : '';
                        }
                    }
                    $sav = ($worstP > 0 && $bestP > 0) ? round(100.0 * ($bestP - $worstP) / $worstP, 2) : 0;
                    $mkts[] = array(
                        'market' => $row['market'],
                        'outcomes' => array(array(
                            'outcome_name' => $row['outcome_name'],
                            'best_book' => $bestB,
                            'best_price' => $bestP,
                            'worst_book' => $worstB,
                            'worst_price' => $worstP,
                            'savings_pct' => $sav,
                            'key_number_alert' => false,
                        )),
                    );
                    $line_shops[] = array(
                        'sport_short' => sports_sport_short($row['sport']),
                        'home_team' => $row['home_team'],
                        'away_team' => $row['away_team'],
                        'commence_time' => $row['commence_time'],
                        'game_date' => $row['pick_date'],
                        'markets' => $mkts,
                    );
                }
            }
        }
    }

    // Live augmentation: daily snapshot lags; value_bets has fresh rows after each
    // analyze. Always merge for every sport filter (not only all/NBA/NHL) so
    // NFL/MLB/NCA* tabs see the same +EV as "All" after analyze runs.
    $seen_keys = array();
    for ($vi = 0; $vi < count($value_bets); $vi++) {
        $_v = $value_bets[$vi];
        $seen_keys[(isset($_v['event_id']) ? $_v['event_id'] : '') . '|'
                 . (isset($_v['market']) ? $_v['market'] : '') . '|'
                 . (isset($_v['outcome_name']) ? $_v['outcome_name'] : '')] = true;
    }
    $liveWhere = "status = 'active' AND commence_time >= NOW() AND commence_time < DATE_ADD(NOW(), INTERVAL 48 HOUR)";
    $liveWhere .= sports_picks_vb_sport_and_clause($mysqli, $sport);
    $rl = $mysqli->query("SELECT * FROM lm_sports_value_bets WHERE " . $liveWhere . " ORDER BY ev_pct DESC LIMIT 50");
    if ($rl) {
            while ($lrow = $rl->fetch_assoc()) {
                $lkey = (isset($lrow['event_id']) ? $lrow['event_id'] : '') . '|'
                      . (isset($lrow['market']) ? $lrow['market'] : '') . '|'
                      . (isset($lrow['outcome_name']) ? $lrow['outcome_name'] : '');
                if (isset($seen_keys[$lkey])) { continue; }
                $seen_keys[$lkey] = true;

                $ev = floatval($lrow['ev_pct']);
                $sumEv += $ev;
                $rec = sports_ev_to_rec($ev);
                if ($rec === 'STRONG TAKE') { $strong++; }
                if ($rec === 'TAKE' || $rec === 'STRONG TAKE') { $takes++; }
                if ($rec === 'LOW EDGE' || $rec === 'WAIT' || $rec === 'SKIP') { $waits++; }
                $grade = sports_ev_to_grade($ev);
                $score = min(100, intval(35 + $ev * 4));
                $bk = isset($lrow['best_book_key']) ? $lrow['best_book_key'] : '';
                $decOdds = floatval($lrow['best_odds']);
                $bookBonus = sports_ca_book($bk) ? 6 : 0;
                $oddNudge = 0;
                if ($decOdds > 0 && $decOdds < 2.5) { $oddNudge = 4; }
                else if ($decOdds >= 6.0) { $oddNudge = 2; }
                $composite_score = min(100, intval(22 + $ev * 2.6 + $bookBonus + $oddNudge));
                if ($dual_mode === 'stability') {
                    $composite_score = min(100, intval(30 + $ev * 2.0 + ($bookBonus * 0.5)));
                }
                $value_bets[] = array(
                    'sport' => $lrow['sport'],
                    'sport_short' => sports_sport_short($lrow['sport']),
                    'home_team' => $lrow['home_team'],
                    'away_team' => $lrow['away_team'],
                    'commence_time' => $lrow['commence_time'],
                    'game_date' => substr(isset($lrow['commence_time']) ? $lrow['commence_time'] : '', 0, 10),
                    'market' => $lrow['market'],
                    'bet_type' => isset($lrow['bet_type']) ? $lrow['bet_type'] : $lrow['outcome_name'],
                    'outcome_name' => $lrow['outcome_name'],
                    'best_book' => $lrow['best_book'],
                    'best_odds' => $decOdds,
                    'american_odds' => sports_decimal_to_american($lrow['best_odds']),
                    'ev_pct' => $ev,
                    'kelly_bet' => floatval(isset($lrow['kelly_bet']) ? $lrow['kelly_bet'] : 0),
                    'win_probability' => ($lrow['best_odds'] > 0) ? round(100.0 / floatval($lrow['best_odds']), 2) : 0,
                    'rating_grade' => $grade,
                    'rating_score' => $score,
                    'composite_score' => $composite_score,
                    'dual_mode' => $dual_mode,
                    'recommendation' => $rec,
                    'rec_detail' => sports_ev_rec_detail($rec),
                    'rating_reasons' => array('EV% from multi-book consensus (live augmented)', 'CA-legal book boost when applicable', 'Composite blends EV, book quality, odds bucket'),
                    'is_canadian_book' => sports_ca_book($bk),
                    'event_id' => $lrow['event_id'],
                    'result' => isset($lrow['result']) ? $lrow['result'] : null,
                    'is_finished' => (
                        (isset($lrow['result']) && $lrow['result'] !== null && $lrow['result'] !== '')
                        || (!empty($lrow['commence_time']) && strtotime($lrow['commence_time']) < (time() - 3 * 3600))
                    ),
                );

                $lastIdx = count($value_bets) - 1;
                if ($lastIdx >= 0) {
                    $pm2 = sports_pm_best_match($pmSignals, $lrow['home_team'], $lrow['away_team']);
                    if (is_array($pm2)) {
                        $pmMatchedCount++;
                        $pmConf2 = floatval(isset($pm2['confidence']) ? $pm2['confidence'] : 0);
                        $pmVol2 = floatval(isset($pm2['volume_usd']) ? $pm2['volume_usd'] : 0);
                        $value_bets[$lastIdx]['prediction_market_source'] = isset($pm2['source']) ? $pm2['source'] : 'polymarket';
                        $value_bets[$lastIdx]['prediction_market_confidence'] = round($pmConf2, 4);
                        $value_bets[$lastIdx]['prediction_market_volume_usd'] = round($pmVol2, 2);
                        $value_bets[$lastIdx]['prediction_market_hint'] = isset($pm2['question']) ? $pm2['question'] : '';
                        $value_bets[$lastIdx]['rating_reasons'][] = 'Prediction market confirmation: conf ' . round($pmConf2 * 100.0, 1) . '%, vol $' . round($pmVol2, 0);

                        $pmNudge2 = sports_pm_score_nudge($pmConf2, $pmVol2, $value_bets[$lastIdx]['best_odds']);
                        if ($pmNudge2 > 0) {
                            $value_bets[$lastIdx]['composite_score'] = min(100, intval($value_bets[$lastIdx]['composite_score']) + $pmNudge2);
                            $value_bets[$lastIdx]['prediction_market_score_boost'] = $pmNudge2;
                        }
                    }
                    sports_picks_annotate_goalie_overlay($value_bets[$lastIdx]);
                    sports_picks_annotate_tennis_elo($value_bets[$lastIdx]);
                }
            }
    }

    $n = count($value_bets);
    $avgEv = ($n > 0) ? round($sumEv / $n, 2) : 0;
    echo json_encode(array(
        'ok' => true,
        'last_updated' => $pickDate,
        'generated_at' => $pickDate,
        'value_bet_count' => $n,
        'value_bets' => $value_bets,
        'line_shops' => $line_shops,
        'summary' => array(
            'strong_takes' => $strong,
            'takes' => $takes,
            'waits' => $waits,
            'avg_ev_pct' => $avgEv,
            'pm_matched_count' => $pmMatchedCount,
            'dual_mode' => $dual_mode,
            'scoring_version' => 'composite_v1',
            'source' => 'daily_picks+live_augment',
        ),
    ));
}

function sports_perf_ev_bucket_key($ev) {
    $e = floatval($ev);
    if ($e >= 10) {
        return '10+';
    }
    if ($e >= 6) {
        return '6-10';
    }
    if ($e >= 3) {
        return '3-6';
    }
    return '0-3';
}

function sports_action_performance($mysqli) {
    $q = "SELECT b.*, c.closing_price AS closing_odds FROM lm_sports_bets b
          LEFT JOIN lm_sports_clv c ON b.event_id = c.event_id AND b.bookmaker_key = c.bookmaker_key
          AND b.market = c.market AND b.pick = c.outcome_name
          WHERE b.result IS NOT NULL AND b.result != ''";
    $r = $mysqli->query($q);
    $buckets = array(
        '0-3' => array('range' => '0-3%', 'total' => 0, 'wins' => 0, 'losses' => 0, 'pnl' => 0.0, 'staked_wl' => 0.0, 'odds_sum_wl' => 0.0),
        '3-6' => array('range' => '3-6%', 'total' => 0, 'wins' => 0, 'losses' => 0, 'pnl' => 0.0, 'staked_wl' => 0.0, 'odds_sum_wl' => 0.0),
        '6-10' => array('range' => '6-10%', 'total' => 0, 'wins' => 0, 'losses' => 0, 'pnl' => 0.0, 'staked_wl' => 0.0, 'odds_sum_wl' => 0.0),
        '10+' => array('range' => '10%+', 'total' => 0, 'wins' => 0, 'losses' => 0, 'pnl' => 0.0, 'staked_wl' => 0.0, 'odds_sum_wl' => 0.0),
    );
    $by_book = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $nr = sports_normalize_result($row['result']);
            $ev = floatval($row['ev_pct']);
            $bk = isset($row['bookmaker']) ? $row['bookmaker'] : '';
            $bkey = sports_perf_ev_bucket_key($ev);
            $pnl = floatval($row['pnl']);
            $stake = floatval($row['bet_amount']);
            $odds = floatval($row['odds']);
            $closing = floatval(isset($row['closing_odds']) ? $row['closing_odds'] : 0);

            if ($nr === 'win' || $nr === 'loss') {
                $buckets[$bkey]['total']++;
                if ($nr === 'win') {
                    $buckets[$bkey]['wins']++;
                } else {
                    $buckets[$bkey]['losses']++;
                }
                $buckets[$bkey]['pnl'] += $pnl;
                $buckets[$bkey]['staked_wl'] += $stake;
                $buckets[$bkey]['odds_sum_wl'] += $odds;
            }

            if (!isset($by_book[$bk])) {
                $by_book[$bk] = array(
                    'best_book' => $bk,
                    'bookmaker_key' => isset($row['bookmaker_key']) ? $row['bookmaker_key'] : '',
                    'wins' => 0,
                    'losses' => 0,
                    'pushes' => 0,
                    'voids' => 0,
                    'pnl' => 0.0,
                    'staked_wl' => 0.0,
                    'clv_sum' => 0.0,
                    'clv_n' => 0,
                    'clv_pos' => 0,
                    'odds_sum_wl' => 0.0,
                    'odds_n_wl' => 0,
                );
            }
            $by_book[$bk]['pnl'] += $pnl;
            if ($nr === 'win' || $nr === 'loss') {
                $by_book[$bk]['staked_wl'] += $stake;
                $by_book[$bk]['odds_sum_wl'] += $odds;
                $by_book[$bk]['odds_n_wl']++;
            }
            if ($nr === 'win') {
                $by_book[$bk]['wins']++;
            } else if ($nr === 'loss') {
                $by_book[$bk]['losses']++;
            } else if ($nr === 'push') {
                $by_book[$bk]['pushes']++;
            } else if ($nr === 'void') {
                $by_book[$bk]['voids']++;
            }
            if ($closing > 0 && $odds > 0 && ($nr === 'win' || $nr === 'loss')) {
                $by_book[$bk]['clv_sum'] += ($odds - $closing) * ($stake / $odds);
                $by_book[$bk]['clv_n']++;
                if ($odds > $closing) {
                    $by_book[$bk]['clv_pos']++;
                }
            }
        }
    }
    $ev_buckets = array();
    foreach ($buckets as $k => $b) {
        $wl = $b['wins'] + $b['losses'];
        $wr = ($wl > 0) ? round(100.0 * $b['wins'] / $wl, 2) : 0;
        $behr = 0;
        if ($wl > 0 && $b['odds_sum_wl'] > 0) {
            $avgO = $b['odds_sum_wl'] / $wl;
            $behr = ($avgO > 0) ? round(100.0 / $avgO, 2) : 0;
        }
        $roiB = ($b['staked_wl'] > 0) ? round(100.0 * $b['pnl'] / $b['staked_wl'], 2) : 0;
        $ev_buckets[] = array(
            'range' => $b['range'],
            'total' => $b['total'],
            'wins' => $b['wins'],
            'losses' => $b['losses'],
            'win_rate' => $wr,
            'approx_behr_pct' => $behr,
            'pnl' => round($b['pnl'], 2),
            'roi_pct' => $roiB,
        );
    }
    $book_out = array();
    foreach ($by_book as $bk => $rec) {
        $wl = $rec['wins'] + $rec['losses'];
        $wr = ($wl > 0) ? round(100.0 * $rec['wins'] / $wl, 2) : 0;
        $staked = floatval($rec['staked_wl']);
        $roi = ($staked > 0) ? round(100.0 * $rec['pnl'] / $staked, 2) : 0;
        $avgClv = ($rec['clv_n'] > 0) ? round($rec['clv_sum'] / $rec['clv_n'], 4) : 0;
        $clvBeat = ($rec['clv_n'] > 0) ? round(100.0 * $rec['clv_pos'] / $rec['clv_n'], 2) : 0;
        $avgOdds = ($rec['odds_n_wl'] > 0) ? $rec['odds_sum_wl'] / $rec['odds_n_wl'] : 0;
        $behrBk = ($avgOdds > 0) ? round(100.0 / $avgOdds, 2) : 0;
        $book_out[] = array(
            'best_book' => $bk,
            'bookmaker_key' => $rec['bookmaker_key'],
            'total' => $rec['wins'] + $rec['losses'] + $rec['pushes'] + $rec['voids'],
            'settled_directional' => $wl,
            'wins' => $rec['wins'],
            'losses' => $rec['losses'],
            'pushes_voids' => $rec['pushes'] + $rec['voids'],
            'win_rate' => $wr,
            'approx_behr_pct' => $behrBk,
            'pnl' => round($rec['pnl'], 2),
            'roi_pct' => $roi,
            'avg_clv_usd' => $avgClv,
            'clv_beat_rate_pct' => $clvBeat,
            'clv_sample' => intval($rec['clv_n']),
        );
    }
    $seq = array();
    $streak_q = $mysqli->query("SELECT result FROM lm_sports_bets WHERE result IS NOT NULL AND result != '' ORDER BY COALESCE(settled_at, placed_at) DESC, id DESC LIMIT 400");
    if ($streak_q) {
        while ($srow = $streak_q->fetch_assoc()) {
            $seq[] = sports_normalize_result($srow['result']);
        }
    }
    $cur = 0;
    $curType = 'none';
    $longest_win = 0;
    $longest_loss = 0;
    $run = 0;
    $last = '';
    for ($si = 0; $si < count($seq); $si++) {
        $x = $seq[$si];
        if ($x !== 'win' && $x !== 'loss') {
            continue;
        }
        $u = ($x === 'win') ? 'w' : 'l';
        if ($last === '' || $u === $last) {
            $run++;
        } else {
            if ($last === 'w' && $run > $longest_win) {
                $longest_win = $run;
            }
            if ($last === 'l' && $run > $longest_loss) {
                $longest_loss = $run;
            }
            $run = 1;
        }
        $last = $u;
    }
    if ($last === 'w' && $run > $longest_win) {
        $longest_win = $run;
    }
    if ($last === 'l' && $run > $longest_loss) {
        $longest_loss = $run;
    }
    $i = 0;
    while ($i < count($seq) && ($seq[$i] !== 'win' && $seq[$i] !== 'loss')) {
        $i++;
    }
    if ($i < count($seq)) {
        $t0 = $seq[$i];
        $cur = 1;
        for ($j = $i + 1; $j < count($seq); $j++) {
            if ($seq[$j] === $t0) {
                $cur++;
            } else {
                break;
            }
        }
        $curType = ($t0 === 'win') ? 'won' : 'lost';
    }
    $streaks = array(
        'current' => $cur,
        'current_type' => $curType,
        'longest_win' => $longest_win,
        'longest_loss' => $longest_loss,
    );
    echo json_encode(array(
        'ok' => true,
        'source' => 'lm_sports_bets',
        'ev_buckets' => $ev_buckets,
        'by_book' => $book_out,
        'streaks' => $streaks,
        'generated_at' => date('c'),
    ));
}

function _sports_bets_to_pick_row($b) {
    $nr = sports_normalize_result(isset($b['result']) ? $b['result'] : '');
    $resUi = $nr;
    if ($resUi === 'win') { $resUi = 'won'; }
    if ($resUi === 'loss') { $resUi = 'lost'; }
    return array(
        'id' => isset($b['id']) ? $b['id'] : '',
        'pick_date' => isset($b['game_date']) ? $b['game_date'] : '',
        'generated_at' => isset($b['placed_at']) ? $b['placed_at'] : '',
        'sport' => isset($b['sport']) ? $b['sport'] : '',
        'event_id' => isset($b['event_id']) ? $b['event_id'] : '',
        'home_team' => isset($b['home_team']) ? $b['home_team'] : '',
        'away_team' => isset($b['away_team']) ? $b['away_team'] : '',
        'commence_time' => isset($b['commence_time']) ? $b['commence_time'] : '',
        'market' => isset($b['market']) ? $b['market'] : '',
        'pick_type' => isset($b['bet_type']) ? $b['bet_type'] : '',
        'outcome_name' => isset($b['pick']) ? $b['pick'] : '',
        'best_book' => isset($b['bookmaker']) ? $b['bookmaker'] : '',
        'best_book_key' => isset($b['bookmaker_key']) ? $b['bookmaker_key'] : '',
        'best_odds' => isset($b['odds']) ? $b['odds'] : '0',
        'ev_pct' => isset($b['ev_pct']) ? $b['ev_pct'] : '0',
        'kelly_bet' => isset($b['bet_amount']) ? $b['bet_amount'] : '0',
        'algorithm' => isset($b['algorithm']) ? $b['algorithm'] : '',
        'confidence' => 'medium',
        'result' => $resUi,
        'pnl' => isset($b['pnl']) ? $b['pnl'] : null,
        'all_odds' => '',
        'source' => 'bets',
    );
}

function sports_action_pick_history($mysqli) {
    $days = isset($_GET['days']) ? intval($_GET['days']) : 30;
    if ($days < 1) {
        $days = 30;
    }
    if ($days > 365) {
        $days = 365;
    }
    $date = isset($_GET['date']) ? $_GET['date'] : '';
    if ($date !== '') {
        $sport = isset($_GET['sport']) ? $_GET['sport'] : 'all';
        $where = "pick_date = '" . $mysqli->real_escape_string($date) . "'";
        if ($sport !== '' && $sport !== 'all') {
            $where .= " AND sport LIKE '%" . $mysqli->real_escape_string(strtolower($sport)) . "%'";
        }
        $r = $mysqli->query("SELECT * FROM lm_sports_daily_picks WHERE " . $where);
        $picks = array();
        $seenEvents = array();
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $row['source'] = 'picks';
                $picks[] = $row;
                $ek = (isset($row['event_id']) ? $row['event_id'] : '') . "\x1f" . (isset($row['outcome_name']) ? $row['outcome_name'] : '') . "\x1f" . (isset($row['market']) ? $row['market'] : '');
                $seenEvents[$ek] = 1;
            }
        }
        $dateEsc = $mysqli->real_escape_string($date);
        $betsWhere = "game_date = '" . $dateEsc . "'";
        if ($sport !== '' && $sport !== 'all') {
            $betsWhere .= " AND sport LIKE '%" . $mysqli->real_escape_string(strtolower($sport)) . "%'";
        }
        $br = $mysqli->query("SELECT * FROM lm_sports_bets WHERE " . $betsWhere);
        if ($br) {
            while ($brow = $br->fetch_assoc()) {
                $ek = (isset($brow['event_id']) ? $brow['event_id'] : '') . "\x1f" . (isset($brow['pick']) ? $brow['pick'] : '') . "\x1f" . (isset($brow['market']) ? $brow['market'] : '');
                if (isset($seenEvents[$ek])) {
                    continue;
                }
                $picks[] = _sports_bets_to_pick_row($brow);
            }
        }
        echo json_encode(array('ok' => true, 'picks' => $picks));
        return;
    }

    $sport = isset($_GET['sport']) ? $_GET['sport'] : 'all';
    $sportClause = sports_picks_vb_sport_and_clause($mysqli, $sport);

    $byDate = array();
    // Diagnostic counters so the frontend / operator can tell which source
    // is empty without DB access (Apr 2026 bug: lm_sports_daily_picks stale
    // since Feb; bets-fallback was masking '0000-00-00' game_dates as
    // a single zero-day group).
    $_diag = array(
        'daily_picks_rows' => 0,
        'bets_rows' => 0,
        'bets_zero_date_skipped' => 0,
    );

    // Skip zero-date filter in WHERE (PHP 5.2 / MySQL strict-mode casts
    // DATE column comparisons to empty string oddly). Filter in PHP instead.
    $r = $mysqli->query("SELECT pick_date, COUNT(*) AS total_picks, SUM(ev_pct)/COUNT(*) AS avg_ev, SUM(CASE WHEN result='won' OR result='win' THEN 1 ELSE 0 END) AS wins, SUM(CASE WHEN result='lost' OR result='loss' THEN 1 ELSE 0 END) AS losses, SUM(CASE WHEN result IS NULL OR result='' OR result='pending' THEN 1 ELSE 0 END) AS pending, SUM(COALESCE(pnl,0)) AS total_pnl, MAX(generated_at) AS last_generated FROM lm_sports_daily_picks WHERE 1=1" . $sportClause . " GROUP BY pick_date ORDER BY pick_date DESC LIMIT " . intval($days));
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $pd = $row['pick_date'];
            // Filter zero-date / null / empty rows in PHP (avoids strict-mode
            // DATE comparison quirks on the host's PHP 5.2 / MySQL stack).
            if ($pd === null || $pd === '' || $pd === '0000-00-00') {
                continue;
            }
            $byDate[$pd] = array(
                'pick_date' => $pd,
                'total_picks' => intval($row['total_picks']),
                'avg_ev' => round(floatval($row['avg_ev']), 2),
                'wins' => intval($row['wins']),
                'losses' => intval($row['losses']),
                'pending' => intval($row['pending']),
                'total_pnl' => floatval($row['total_pnl']),
                'last_generated' => $row['last_generated'],
                'source' => 'picks',
            );
            $_diag['daily_picks_rows']++;
        }
        $r->free();
    }

    // Use COALESCE(NULLIF(game_date,'0000-00-00'), LEFT(commence_time,10))
    // so the bets fallback fires when game_date is the MySQL zero-date
    // (treats '0000-00-00' as NULL for the COALESCE). NULLIF works
    // reliably on PHP 5.2 / MySQL 5.x; the bare CASE-in-HAVING form
    // we tried earlier was silently failing under strict_mode. Drop the
    // HAVING clause; filter in PHP instead.
    $gdExpr = "COALESCE(NULLIF(game_date, '0000-00-00'), LEFT(commence_time, 10))";
    $betsSql = "SELECT " . $gdExpr . " AS gd,"
        . " COUNT(*) AS total_bets,"
        . " AVG(ev_pct) AS avg_ev,"
        . " SUM(CASE WHEN result='won' OR result='win' THEN 1 ELSE 0 END) AS wins,"
        . " SUM(CASE WHEN result='lost' OR result='loss' THEN 1 ELSE 0 END) AS losses,"
        . " SUM(CASE WHEN result IS NULL OR result='' OR result='pending' THEN 1 ELSE 0 END) AS pending,"
        . " SUM(COALESCE(pnl,0)) AS total_pnl,"
        . " MAX(placed_at) AS last_placed"
        . " FROM lm_sports_bets"
        . " WHERE 1=1" . $sportClause
        . " GROUP BY " . $gdExpr
        . " ORDER BY gd DESC LIMIT " . intval($days);
    $br = $mysqli->query($betsSql);
    if ($br) {
        while ($brow = $br->fetch_assoc()) {
            $gd = $brow['gd'];
            if ($gd === null || $gd === '' || $gd === '0000-00-00') {
                $_diag['bets_zero_date_skipped'] += intval($brow['total_bets']);
                continue;
            }
            $_diag['bets_rows']++;
            if (isset($byDate[$gd])) {
                $existing = $byDate[$gd];
                $bWins = intval($brow['wins']);
                $bLosses = intval($brow['losses']);
                $bPending = intval($brow['pending']);
                $bPnl = floatval($brow['total_pnl']);
                $bCount = intval($brow['total_bets']);
                if ($bWins > $existing['wins'] || $bLosses > $existing['losses'] || $bPnl != $existing['total_pnl']) {
                    $byDate[$gd]['wins'] = max($existing['wins'], $bWins);
                    $byDate[$gd]['losses'] = max($existing['losses'], $bLosses);
                    $byDate[$gd]['total_pnl'] = ($bPnl != 0 && $existing['total_pnl'] == 0) ? $bPnl : $existing['total_pnl'];
                }
                if ($bCount > $existing['total_picks']) {
                    $byDate[$gd]['total_picks'] = $bCount;
                }
                $byDate[$gd]['has_bets'] = true;
                continue;
            }
            $byDate[$gd] = array(
                'pick_date' => $gd,
                'total_picks' => intval($brow['total_bets']),
                'avg_ev' => round(floatval($brow['avg_ev']), 2),
                'wins' => intval($brow['wins']),
                'losses' => intval($brow['losses']),
                'pending' => intval($brow['pending']),
                'total_pnl' => floatval($brow['total_pnl']),
                'last_generated' => $brow['last_placed'],
                'source' => 'bets',
                'has_bets' => true,
            );
        }
    }

    $dateKeys = array_keys($byDate);
    rsort($dateKeys);
    $days_out = array();
    $totP = 0;
    $totW = 0;
    $totL = 0;
    for ($di = 0; $di < count($dateKeys); $di++) {
        $entry = $byDate[$dateKeys[$di]];
        $days_out[] = $entry;
        $totP += intval($entry['total_picks']);
        $totW += intval($entry['wins']);
        $totL += intval($entry['losses']);
    }

    $wl = $totW + $totL;
    $wr = ($wl > 0) ? round(100.0 * $totW / $wl, 2) : 0;
    $tpnl = 0.0;
    $pr = $mysqli->query("SELECT SUM(COALESCE(pnl,0)) AS s FROM lm_sports_bets WHERE 1=1" . $sportClause . " AND result IS NOT NULL AND result != ''");
    if ($pr && ($pro = $pr->fetch_assoc())) {
        $tpnl = floatval($pro['s']);
    }
    $dpPnl = 0.0;
    $dpr = $mysqli->query("SELECT SUM(COALESCE(pnl,0)) AS s FROM lm_sports_daily_picks WHERE 1=1" . $sportClause . " AND result IS NOT NULL AND result != '' AND LOWER(COALESCE(result,'')) != 'pending'");
    if ($dpr && ($dpro = $dpr->fetch_assoc())) {
        $dpPnl = floatval($dpro['s']);
    }
    echo json_encode(array(
        'ok' => true,
        'days' => $days_out,
        'sport_filter' => $sport,
        'overall' => array(
            'total' => $totP,
            'win_rate' => $wr,
            'total_pnl' => $tpnl,
            'daily_picks_pnl' => round($dpPnl, 2),
            'wins' => $totW,
            'losses' => $totL,
        ),
        '_diag' => $_diag,
    ));
}

if ($action === 'today') {
    sports_action_today($sports_mysqli);
    $sports_mysqli->close();
    exit;
}

if ($action === 'edge_policy_audit') {
    if (!sports_picks_key_ok(isset($_GET['key']) ? $_GET['key'] : '')) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
    } else {
        sports_action_edge_policy_audit($sports_mysqli);
    }
    $sports_mysqli->close();
    exit;
}

if ($action === 'tier_breakdown') {
    // Diagnostic: counts at each EV tier for the current pick date, plus the
    // upstream funnel — distinct events in lm_sports_odds today and how many
    // had enough usable books to reach the value-bet table. Helps tell
    // "few strong picks because few books" from "few strong picks because
    // model edges are small even with full coverage".
    $estTz = new DateTimeZone('America/New_York');
    $estNow = new DateTime('now', $estTz);
    $today = $estNow->format('Y-m-d');
    $pickDate = $today;
    $dr = $sports_mysqli->query("SELECT MAX(pick_date) AS d FROM lm_sports_daily_picks");
    if ($dr && ($drow = $dr->fetch_assoc()) && $drow['d'] !== null && $drow['d'] !== '') {
        $pickDate = $drow['d'];
    }

    $tiers = array(
        'STRONG TAKE' => 0,
        'TAKE' => 0,
        'LEAN' => 0,
        'LOW EDGE' => 0,
        'SKIP' => 0,
    );
    $bestEv = -999.0;
    $worstEv = 999.0;
    $sumEv = 0.0;
    $nPicks = 0;
    $r = $sports_mysqli->query("SELECT ev_pct FROM lm_sports_daily_picks WHERE pick_date = '" . $sports_mysqli->real_escape_string($pickDate) . "'");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $ev = floatval($row['ev_pct']);
            $rec = sports_ev_to_rec($ev);
            if (isset($tiers[$rec])) { $tiers[$rec]++; }
            $nPicks++;
            $sumEv += $ev;
            if ($ev > $bestEv) { $bestEv = $ev; }
            if ($ev < $worstEv) { $worstEv = $ev; }
        }
    }

    // Upstream funnel: how many distinct events / books are in lm_sports_odds
    // for games starting in the current pick window. A starved funnel here is
    // the main reason STRONG bets are rare.
    $books_total = 0;
    $books_per_book = array();
    $events_total = 0;
    $events_with_3plus_books = 0;
    $sports_seen = array();

    $r2 = $sports_mysqli->query(
        "SELECT event_id, sport, bookmaker_key, COUNT(*) AS n_outcomes "
        . "FROM lm_sports_odds "
        . "WHERE DATE(commence_time) >= '" . $sports_mysqli->real_escape_string($pickDate) . "' "
        . "GROUP BY event_id, sport, bookmaker_key"
    );
    $event_books = array();
    if ($r2) {
        while ($row = $r2->fetch_assoc()) {
            $eid = $row['event_id'];
            $bk  = $row['bookmaker_key'];
            $sp  = $row['sport'];
            if (!isset($event_books[$eid])) { $event_books[$eid] = array('sport' => $sp, 'books' => array()); }
            $event_books[$eid]['books'][$bk] = 1;
            $books_total++;
            if (!isset($books_per_book[$bk])) { $books_per_book[$bk] = 0; }
            $books_per_book[$bk]++;
            $sports_seen[$sp] = 1;
        }
    }
    $events_total = count($event_books);
    foreach ($event_books as $eid => $info) {
        if (count($info['books']) >= 3) {
            $events_with_3plus_books++;
        }
    }
    arsort($books_per_book);
    $top_books = array();
    $i = 0;
    foreach ($books_per_book as $bk => $cnt) {
        if ($i++ >= 12) { break; }
        $top_books[] = array('book' => $bk, 'rows' => $cnt);
    }

    $avgEv = ($nPicks > 0) ? round($sumEv / $nPicks, 2) : 0;
    echo json_encode(array(
        'ok' => true,
        'pick_date' => $pickDate,
        'today' => $today,
        'picks' => array(
            'total' => $nPicks,
            'tiers' => $tiers,
            'avg_ev_pct' => $avgEv,
            'best_ev_pct' => ($nPicks > 0) ? round($bestEv, 2) : null,
            'worst_ev_pct' => ($nPicks > 0) ? round($worstEv, 2) : null,
        ),
        'odds_funnel' => array(
            'distinct_events' => $events_total,
            'events_with_3plus_books' => $events_with_3plus_books,
            'devig_eligible_pct' => ($events_total > 0) ? round(100.0 * $events_with_3plus_books / $events_total, 1) : 0,
            'distinct_sports' => count($sports_seen),
            'sports' => array_keys($sports_seen),
            'top_books_by_row_count' => $top_books,
        ),
        'thresholds' => array(
            'strong_take_min_ev_pct' => 10,
            'take_min_ev_pct' => 6,
            'lean_min_ev_pct' => 3,
        ),
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'performance') {
    sports_action_performance($sports_mysqli);
    $sports_mysqli->close();
    exit;
}

if ($action === 'pick_history') {
    sports_action_pick_history($sports_mysqli);
    $sports_mysqli->close();
    exit;
}

if ($action === 'analyze') {
    if (!sports_picks_key_ok(isset($_GET['key']) ? $_GET['key'] : '')) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        $sports_mysqli->close();
        exit;
    }
    require_once dirname(__FILE__) . '/sports_value_analyze_lib.php';
    $bankroll = isset($_GET['bankroll']) ? floatval($_GET['bankroll']) : 1000.0;
    $minEv = isset($_GET['min_ev']) ? floatval($_GET['min_ev']) : 4.0;
    $sportFilter = isset($_GET['sport']) ? trim($_GET['sport']) : '';

    // Block sports with critically high void rates from generating new value bets.
    // MLS (soccer_usa_mls): 10/10 voids (100%) — call rejected early to skip the pipeline step.
    $highVoidSports = array('soccer_usa_mls');
    $sportBlocked = false;
    foreach ($highVoidSports as $hvs) {
        if (strpos($sportFilter, $hvs) !== false) {
            $sportBlocked = true;
            break;
        }
    }
    if ($sportBlocked) {
        echo json_encode(array(
            'ok' => false,
            'error' => 'sport_excluded_' . join('_', $highVoidSports),
            'reason' => 'High void rate - score settlement unreliable'
        ));
        $sports_mysqli->close();
        exit;
    }

    $res = sports_value_analyze_run($sports_mysqli, $bankroll, $minEv, $sportFilter);
    echo json_encode(array(
        'ok' => true,
        'value_bets_found' => $res['active_count'],
        'new_bets_inserted' => $res['inserted'],
        'expired_prior_active' => $res['expired'],
        'markets_scanned' => $res['buckets'],
        'min_ev_pct' => $minEv,
        'sport_filter' => $sportFilter,
        'bankroll' => $bankroll,
        'top_bets' => $res['top'],
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'daily_picks') {
    if (!sports_picks_key_ok(isset($_GET['key']) ? $_GET['key'] : '')) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        $sports_mysqli->close();
        exit;
    }
    $estTz = new DateTimeZone('America/New_York');
    $estNow = new DateTime('now', $estTz);
    $pickDate = $estNow->format('Y-m-d');
    $now = $estNow->format('Y-m-d H:i:s');

    // Exclude sports with critically high void rates from daily picks.
    // MLS (soccer_usa_mls) has 10/10 voids (100%) — score matching is unreliable.
    // Re-evaluate when the odds API scores endpoint reliably returns MLS results.
    $highVoidSports = array('soccer_usa_mls');

    $q = $sports_mysqli->query(
        "SELECT * FROM lm_sports_value_bets WHERE status = 'active'"
        . " AND commence_time >= NOW()"
        . " AND commence_time < DATE_ADD(CURDATE(), INTERVAL 2 DAY)"
        . " ORDER BY ev_pct DESC"
    );
    $candidates = array();
    if ($q) {
        while ($row = $q->fetch_assoc()) {
            $sp = isset($row['sport']) ? $row['sport'] : '';
            $skip = false;
            foreach ($highVoidSports as $hvs) {
                if (strpos($sp, $hvs) !== false) {
                    $skip = true;
                    break;
                }
            }
            if ($skip) {
                continue;
            }
            $candidates[] = $row;
        }
    }

    $seen = array();
    $toInsert = array();
    for ($ci = 0; $ci < count($candidates); $ci++) {
        $c = $candidates[$ci];
        $dedupeKey = $c['event_id'] . "\x1f" . $c['market'] . "\x1f" . $c['outcome_name'];
        if (isset($seen[$dedupeKey])) {
            continue;
        }
        $seen[$dedupeKey] = 1;
        $toInsert[] = $c;
    }

    $inserted = 0;
    $skippedDup = 0;
    for ($ti = 0; $ti < count($toInsert); $ti++) {
        $c = $toInsert[$ti];
        $eidEsc = $sports_mysqli->real_escape_string($c['event_id']);
        $onEsc = $sports_mysqli->real_escape_string($c['outcome_name']);
        $mktEsc = $sports_mysqli->real_escape_string($c['market']);
        $chk = $sports_mysqli->query(
            "SELECT id FROM lm_sports_daily_picks WHERE event_id = '" . $eidEsc
            . "' AND outcome_name = '" . $onEsc
            . "' AND market = '" . $mktEsc
            . "' AND pick_date = '" . $sports_mysqli->real_escape_string($pickDate) . "' LIMIT 1"
        );
        if ($chk && $chk->num_rows > 0) {
            $skippedDup++;
            continue;
        }

        $ct = isset($c['commence_time']) ? $c['commence_time'] : '';
        $gd = (strlen($ct) >= 10) ? substr($ct, 0, 10) : $pickDate;

        $ev = floatval($c['ev_pct']);
        $conf = 'medium';
        if ($ev >= 10) {
            $conf = 'high';
        } else if ($ev < 3) {
            $conf = 'low';
        }

        $btEsc = $sports_mysqli->real_escape_string(isset($c['bet_type']) ? $c['bet_type'] : '');
        $allOddsEsc = $sports_mysqli->real_escape_string(isset($c['all_odds']) ? $c['all_odds'] : '');

        $ins = "INSERT INTO lm_sports_daily_picks"
            . " (pick_date, generated_at, sport, event_id, home_team, away_team,"
            . " commence_time, market, pick_type, outcome_name,"
            . " best_book, best_book_key, best_odds, ev_pct, kelly_bet,"
            . " algorithm, confidence, all_odds)"
            . " VALUES ("
            . "'" . $sports_mysqli->real_escape_string($pickDate) . "',"
            . "'" . $sports_mysqli->real_escape_string($now) . "',"
            . "'" . $sports_mysqli->real_escape_string($c['sport']) . "',"
            . "'" . $eidEsc . "',"
            . "'" . $sports_mysqli->real_escape_string($c['home_team']) . "',"
            . "'" . $sports_mysqli->real_escape_string($c['away_team']) . "',"
            . "'" . $sports_mysqli->real_escape_string($ct) . "',"
            . "'" . $mktEsc . "',"
            . "'" . $btEsc . "',"
            . "'" . $onEsc . "',"
            . "'" . $sports_mysqli->real_escape_string(isset($c['best_book']) ? $c['best_book'] : '') . "',"
            . "'" . $sports_mysqli->real_escape_string(isset($c['best_book_key']) ? $c['best_book_key'] : '') . "',"
            . round(floatval($c['best_odds']), 4) . ","
            . round(floatval($c['ev_pct']), 2) . ","
            . round(floatval($c['kelly_bet']), 2) . ","
            . "'value_bet_gr202604',"
            . "'" . $sports_mysqli->real_escape_string($conf) . "',"
            . "'" . $allOddsEsc . "')";
        if ($sports_mysqli->query($ins)) {
            $inserted++;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'picks_generated' => $inserted,
        'skipped_duplicate' => $skippedDup,
        'candidates_from_value_bets' => count($toInsert),
        'generated_at' => date('c'),
        'pick_date' => $pickDate,
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'settle_picks') {
    if (!sports_picks_key_ok(isset($_GET['key']) ? $_GET['key'] : '')) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        $sports_mysqli->close();
        exit;
    }
    $apiKey = isset($THE_ODDS_API_KEY) ? $THE_ODDS_API_KEY : '';
    if ($apiKey === '') {
        echo json_encode(array('ok' => false, 'error' => 'missing THE_ODDS_API_KEY'));
        $sports_mysqli->close();
        exit;
    }
    // Odds API /scores: daysFrom must be 1-3 (how far back the API returns completed games).
    $daysFrom = isset($_GET['days_from']) ? intval($_GET['days_from']) : 3;
    if ($daysFrom < 1) {
        $daysFrom = 1;
    }
    if ($daysFrom > 3) {
        $daysFrom = 3;
    }
    // How far back to scan the DB for pending daily picks. Previously this wrongly reused
    // daysFrom=3, so any game older than 3 days never entered settlement and stayed pending forever.
    $lookbackDays = isset($_GET['lookback_days']) ? intval($_GET['lookback_days']) : 30;
    if ($lookbackDays < 1) {
        $lookbackDays = 1;
    }
    if ($lookbackDays > 120) {
        $lookbackDays = 120;
    }
    $pendingWhere = "(result IS NULL OR result = '' OR LOWER(result) = 'pending')";
    $sportsWithPending = array();
    $sw = $sports_mysqli->query("SELECT DISTINCT sport FROM lm_sports_daily_picks WHERE " . $pendingWhere . " AND commence_time < NOW() AND commence_time >= DATE_SUB(NOW(), INTERVAL " . intval($lookbackDays) . " DAY)");
    if ($sw) {
        while ($swr = $sw->fetch_assoc()) {
            $sportsWithPending[] = $swr['sport'];
        }
    }
    if (count($sportsWithPending) === 0) {
        echo json_encode(array(
            'ok' => true,
            'settled' => 0,
            'won' => 0,
            'lost' => 0,
            'push' => 0,
            'voided' => 0,
            'net_pnl' => 0,
            'sports_scanned' => 0,
            'source' => 'lm_sports_daily_picks',
            'lookback_days' => $lookbackDays,
            'scores_api_days_from' => $daysFrom,
            'note' => 'No pending daily picks in lookback (commence_time within lookback_days, game already started).',
            'details' => array(),
        ));
        $sports_mysqli->close();
        exit;
    }
    $totalSettled = 0;
    $totalWon = 0;
    $totalLost = 0;
    $totalPush = 0;
    $netPnl = 0.0;
    $details = array();
    $creditsUsed = 0;
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
        $pq = $sports_mysqli->query(
            "SELECT id, event_id, home_team, away_team, market, outcome_name, outcome_point, best_odds, kelly_bet, commence_time FROM lm_sports_daily_picks WHERE sport = '" . $sportEsc . "' AND " . $pendingWhere
            . " AND commence_time < NOW() AND commence_time >= DATE_SUB(NOW(), INTERVAL " . intval($lookbackDays) . " DAY)"
        );
        if ($pq) {
            while ($b = $pq->fetch_assoc()) {
                $eid = isset($b['event_id']) ? $b['event_id'] : '';
                $sm = sports_scores_find_match($scoreMap, $sport, $eid, $b['home_team'], $b['away_team'], isset($b['commence_time']) ? $b['commence_time'] : '');
                if ($sm === null) {
                    continue;
                }
                $hs = $sm['home'];
                $as = $sm['away'];
                $pick = isset($b['outcome_name']) ? $b['outcome_name'] : '';
                $pt = null;
                if (isset($b['outcome_point']) && $b['outcome_point'] !== null && $b['outcome_point'] !== '') {
                    $pt = floatval($b['outcome_point']);
                }
                $odds = floatval($b['best_odds']);
                $stake = floatval($b['kelly_bet']);
                if ($stake <= 0) {
                    $stake = 1.0;
                }
                $graded = sports_scores_grade_ticket($sm, $b['market'], $pick, $pt, $odds, $stake);
                if ($graded === null) {
                    continue;
                }
                $result = $graded['result'];
                $pnl = $graded['pnl'];
                $resEsc = $sports_mysqli->real_escape_string($result);
                $sports_mysqli->query("UPDATE lm_sports_daily_picks SET result = '" . $resEsc . "', pnl = " . floatval($pnl) . " WHERE id = " . intval($b['id']));
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
                    'pick' => $pick,
                    'score' => $hs . '-' . $as,
                    'result' => $result,
                    'pnl' => $pnl,
                );
            }
        }
    }
    $tpnl = 0.0;
    $pr = $sports_mysqli->query("SELECT SUM(COALESCE(pnl,0)) AS s FROM lm_sports_daily_picks WHERE result IS NOT NULL AND result != '' AND LOWER(result) != 'pending'");
    if ($pr && ($prr = $pr->fetch_assoc())) {
        $tpnl = floatval($prr['s']);
    }
    echo json_encode(array(
        'ok' => true,
        'settled' => $totalSettled,
        'won' => $totalWon,
        'lost' => $totalLost,
        'push' => $totalPush,
        'voided' => 0,
        'net_pnl' => round($netPnl, 2),
        'total_tracked_pick_pnl' => round($tpnl, 2),
        'sports_scanned' => count($sportsWithPending),
        'credits_used' => $creditsUsed,
        'lookback_days' => $lookbackDays,
        'scores_api_days_from' => $daysFrom,
        'source' => 'lm_sports_daily_picks',
        'details' => $details,
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'grade_manual') {
    // Bypass The Odds API /scores when it isn't flagging completed games.
    // POST JSON {"rows":[{sport,event_id,home_team,away_team,commence_time,home_score,away_score},...]}.
    // Same logic as sports_bets.php?action=grade_manual but updates lm_sports_daily_picks.
    if (!sports_picks_key_ok(isset($_GET['key']) ? $_GET['key'] : '')) {
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
    $pendingWhere = "(result IS NULL OR result = '' OR LOWER(result) = 'pending')";
    foreach ($bySport as $sport => $games) {
        $scoreMap = sports_scores_map_from_games_array($sport, $games);
        $sportEsc = $sports_mysqli->real_escape_string($sport);
        // lm_sports_daily_picks does not have an outcome_point column (commit 12f789c396).
        // Line/total/spread point lives in pick_type as the trailing numeric token (e.g. "Over 5.50").
        $pq = $sports_mysqli->query("SELECT id, event_id, home_team, away_team, market, outcome_name, pick_type, best_odds, kelly_bet, commence_time FROM lm_sports_daily_picks WHERE sport = '" . $sportEsc . "' AND " . $pendingWhere);
        if ($pq) {
            while ($b = $pq->fetch_assoc()) {
                $sm = sports_scores_find_match($scoreMap, $sport, isset($b['event_id']) ? $b['event_id'] : '', $b['home_team'], $b['away_team'], isset($b['commence_time']) ? $b['commence_time'] : '');
                if ($sm === null) {
                    continue;
                }
                $pt = null;
                if (isset($b['pick_type']) && $b['pick_type'] !== '') {
                    if (preg_match('/(-?\d+\.?\d*)\s*$/', trim(strval($b['pick_type'])), $mch)) {
                        $pt = floatval($mch[1]);
                    }
                }
                $stake = floatval($b['kelly_bet']);
                if ($stake <= 0) {
                    $stake = 1.0;
                }
                $graded = sports_scores_grade_ticket($sm, $b['market'], $b['outcome_name'], $pt, floatval($b['best_odds']), $stake);
                if ($graded === null) {
                    continue;
                }
                $resEsc = $sports_mysqli->real_escape_string($graded['result']);
                $sports_mysqli->query("UPDATE lm_sports_daily_picks SET result = '" . $resEsc . "', pnl = " . floatval($graded['pnl']) . " WHERE id = " . intval($b['id']));
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
                    'pick' => $b['outcome_name'],
                    'score' => $sm['home'] . '-' . $sm['away'],
                    'result' => $graded['result'],
                    'pnl' => $graded['pnl'],
                );
            }
        }
    }
    echo json_encode(array(
        'ok' => true,
        'settled' => $totalSettled,
        'won' => $totalWon,
        'lost' => $totalLost,
        'push' => $totalPush,
        'net_pnl' => round($netPnl, 2),
        'rows_received' => count($rows),
        'sports_in_payload' => count($bySport),
        'source' => 'lm_sports_daily_picks',
        'details' => $details,
        'note' => 'Manual score grading — bypasses Odds API /scores. Same alias-matching as settle_picks.',
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'ungraded_audit') {
    // Read-only diagnostic: count picks past commence_time with no result.
    // Ref: reports/SPORTSBET_DB_AUDIT_2026_04_25.md §A1.
    // Returns {ungraded_count, oldest_commence_time, sample:[...]} — no writes.
    $lookbackDays = isset($_GET['lookback_days']) ? intval($_GET['lookback_days']) : 90;
    if ($lookbackDays < 1) { $lookbackDays = 1; }
    if ($lookbackDays > 365) { $lookbackDays = 365; }
    $sampleLimit = isset($_GET['sample']) ? min(20, max(1, intval($_GET['sample']))) : 10;

    $pendingWhere = "(result IS NULL OR result = '' OR LOWER(result) = 'pending')"
        . " AND commence_time < NOW() - INTERVAL 1 DAY"
        . " AND commence_time >= DATE_SUB(NOW(), INTERVAL " . intval($lookbackDays) . " DAY)";

    $ungraded_count = 0;
    $oldest = null;
    $cq = $sports_mysqli->query(
        "SELECT COUNT(*) AS n, MIN(commence_time) AS oldest FROM lm_sports_daily_picks WHERE " . $pendingWhere
    );
    if ($cq && ($crow = $cq->fetch_assoc())) {
        $ungraded_count = intval($crow['n']);
        $oldest = $crow['oldest'];
    }

    $sample = array();
    $sq = $sports_mysqli->query(
        "SELECT id, pick_date, sport, event_id, home_team, away_team,"
        . " commence_time, market, outcome_name, best_book_key"
        . " FROM lm_sports_daily_picks WHERE " . $pendingWhere
        . " ORDER BY commence_time ASC LIMIT " . intval($sampleLimit)
    );
    if ($sq) {
        while ($srow = $sq->fetch_assoc()) {
            $sample[] = array(
                'id' => intval($srow['id']),
                'pick_date' => $srow['pick_date'],
                'sport' => $srow['sport'],
                'event_id' => $srow['event_id'],
                'matchup' => $srow['away_team'] . ' @ ' . $srow['home_team'],
                'commence_time' => $srow['commence_time'],
                'market' => $srow['market'],
                'outcome_name' => $srow['outcome_name'],
                'best_book_key' => $srow['best_book_key'],
            );
        }
    }

    echo json_encode(array(
        'ok' => true,
        'lookback_days' => $lookbackDays,
        'ungraded_count' => $ungraded_count,
        'oldest_commence_time' => $oldest,
        'sample' => $sample,
        'note' => 'Picks with result IS NULL/empty where commence_time > 1 day ago. Use settle_picks?lookback_days=N or grade_manual to resolve.',
        'generated_at' => date('c'),
    ));
    $sports_mysqli->close();
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'unknown action'));
$sports_mysqli->close();
