<?php
/**
 * Settled-bet metrics: win rate denominator = wins + losses only (excludes push/void).
 * PHP 5.2 safe. Normalizes won/lost from DB.
 */

function sports_normalize_result($raw) {
    if ($raw === null) {
        return 'pending';
    }
    $r = strtolower(trim(strval($raw)));
    if ($r === '') {
        return 'pending';
    }
    if ($r === 'won' || $r === 'win') {
        return 'win';
    }
    if ($r === 'lost' || $r === 'loss') {
        return 'loss';
    }
    if ($r === 'push') {
        return 'push';
    }
    if ($r === 'void' || $r === 'cancelled' || $r === 'canceled') {
        return 'void';
    }
    return 'pending';
}

/**
 * Map lm_sports_bets row to internal bet array for metrics.
 * Optional closing_odds column; if missing, pass 0.
 */
function sports_bet_row_to_metric_array($row) {
    $closing = 0;
    if (isset($row['closing_odds']) && $row['closing_odds'] !== null && $row['closing_odds'] !== '') {
        $closing = floatval($row['closing_odds']);
    }
    return array(
        'result' => sports_normalize_result(isset($row['result']) ? $row['result'] : ''),
        'stake' => floatval(isset($row['bet_amount']) ? $row['bet_amount'] : 0),
        'pnl' => floatval(isset($row['pnl']) ? $row['pnl'] : 0),
        'odds' => floatval(isset($row['odds']) ? $row['odds'] : 0),
        'closing_odds' => $closing,
    );
}

function sports_compute_settled_metrics($bets) {
    $wins = 0;
    $losses = 0;
    $pushes = 0;
    $voids = 0;
    $pending = 0;
    $total_staked_settled = 0.0;
    $net_pnl = 0.0;
    $clv_sum = 0.0;
    $clv_count = 0;
    $clv_positive = 0;
    $clv_negative = 0;

    if (!is_array($bets)) {
        $bets = array();
    }

    foreach ($bets as $bet) {
        $result = isset($bet['result']) ? $bet['result'] : 'pending';
        $stake = floatval(isset($bet['stake']) ? $bet['stake'] : 0);
        $pnl = floatval(isset($bet['pnl']) ? $bet['pnl'] : 0);
        $odds = floatval(isset($bet['odds']) ? $bet['odds'] : 0);
        $closing = floatval(isset($bet['closing_odds']) ? $bet['closing_odds'] : 0);

        if ($result === 'win' || $result === 'loss') {
            $total_staked_settled += $stake;
        }

        if ($result === 'win') {
            $wins += 1;
            $net_pnl += $pnl;
        } else if ($result === 'loss') {
            $losses += 1;
            $net_pnl += $pnl;
        } else if ($result === 'push') {
            $pushes += 1;
            $net_pnl += $pnl;
        } else if ($result === 'void') {
            $voids += 1;
            $net_pnl += $pnl;
        } else {
            $pending += 1;
        }

        if ($closing > 0 && $odds > 0 && ($result === 'win' || $result === 'loss')) {
            $clv_sum += ($odds - $closing) * ($stake / $odds);
            $clv_count += 1;
            if ($odds > $closing) {
                $clv_positive += 1;
            } else if ($odds < $closing) {
                $clv_negative += 1;
            }
        }
    }

    $settled = $wins + $losses;
    $win_rate = ($settled > 0) ? round(100.0 * $wins / $settled, 2) : 0.0;
    $roi = ($total_staked_settled > 0) ? round(100.0 * $net_pnl / $total_staked_settled, 2) : 0.0;
    $avg_clv = ($clv_count > 0) ? round($clv_sum / $clv_count, 4) : 0.0;
    $clv_beat_rate_pct = ($clv_count > 0) ? round(100.0 * $clv_positive / $clv_count, 2) : 0.0;

    $total_recorded = count($bets);
    $closed = $wins + $losses + $pushes + $voids;
    $reconciliation_ok = ($total_recorded === ($closed + $pending));

    return array(
        'wins' => $wins,
        'losses' => $losses,
        'pushes' => $pushes,
        'voids' => $voids,
        'pushes_voids' => $pushes + $voids,
        'pending' => $pending,
        'settled_for_wr' => $settled,
        'win_rate_pct' => $win_rate,
        'total_staked_settled' => $total_staked_settled,
        'net_pnl' => $net_pnl,
        'roi_pct' => $roi,
        'avg_clv' => $avg_clv,
        'avg_clv_sample' => $clv_count,
        'clv_positive_count' => $clv_positive,
        'clv_negative_count' => $clv_negative,
        'clv_beat_rate_pct' => $clv_beat_rate_pct,
        'total_bets' => $total_recorded,
        'closed_bets' => $closed,
        'reconciliation_ok' => $reconciliation_ok,
    );
}

/**
 * CLV × outcome matrix for settled directional bets with a closing line.
 * +CLV & win = sharp; +CLV & loss = variance; -CLV & win = luck; -CLV & loss = bad line/timing.
 */
function sports_compute_clv_quadrants($bets) {
    $pp = 0;
    $pn = 0;
    $np = 0;
    $nn = 0;
    $unk = 0;
    if (!is_array($bets)) {
        $bets = array();
    }
    foreach ($bets as $bet) {
        $result = isset($bet['result']) ? $bet['result'] : 'pending';
        if ($result !== 'win' && $result !== 'loss') {
            continue;
        }
        $odds = floatval(isset($bet['odds']) ? $bet['odds'] : 0);
        $closing = floatval(isset($bet['closing_odds']) ? $bet['closing_odds'] : 0);
        if ($closing <= 0 || $odds <= 0) {
            $unk++;
            continue;
        }
        $beatClose = ($odds > $closing);
        $won = ($result === 'win');
        if ($beatClose && $won) {
            $pp++;
        } else if ($beatClose && !$won) {
            $pn++;
        } else if (!$beatClose && $won) {
            $np++;
        } else {
            $nn++;
        }
    }
    return array(
        'plus_clv_win' => $pp,
        'plus_clv_loss' => $pn,
        'minus_clv_win' => $np,
        'minus_clv_loss' => $nn,
        'no_closing_line' => $unk,
        'caption' => '+CLV & loss often variance; -CLV & win often luck; -CLV & loss review selection.',
    );
}

/**
 * Wilson score interval for binomial win rate (approx 95% when z=1.96).
 */
function sports_wilson_ci_pct($wins, $n, $z) {
    if ($n < 1) {
        return array(null, null);
    }
    $w = floatval($wins);
    $nf = floatval($n);
    $p = $w / $nf;
    $z2 = $z * $z;
    $denom = 1.0 + $z2 / $nf;
    $centre = ($p + $z2 / (2.0 * $nf)) / $denom;
    $inner = $p * (1.0 - $p) / $nf + $z2 / (4.0 * $nf * $nf);
    if ($inner < 0) {
        $inner = 0;
    }
    $margin = ($z / $denom) * sqrt($inner);
    $lo = 100.0 * max(0.0, $centre - $margin);
    $hi = 100.0 * min(1.0, $centre + $margin);
    return array(round($lo, 2), round($hi, 2));
}

function sports_sport_short($sport) {
    $s = strval($sport);
    if (strpos($s, 'basketball_nba') !== false) {
        return 'NBA';
    }
    if (strpos($s, 'basketball_ncaab') !== false) {
        return 'NCAAB';
    }
    if (strpos($s, 'icehockey_nhl') !== false) {
        return 'NHL';
    }
    if (strpos($s, 'baseball_mlb') !== false) {
        return 'MLB';
    }
    if (strpos($s, 'americanfootball_nfl') !== false) {
        return 'NFL';
    }
    if (strpos($s, 'soccer_usa_mls') !== false) {
        return 'MLS';
    }
    return strtoupper(substr($s, 0, 4));
}
