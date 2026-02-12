<?php
/**
 * sports_ml.php — ML Model Integration for Sports Betting
 * PHP 5.2 compatible.
 *
 * This endpoint bridges the Python ML model (scripts/sports_ml.py) with the
 * PHP betting pipeline. It stores ML predictions and filters value bets.
 *
 * Actions:
 *   ?action=status              — ML system status (public)
 *   ?action=predict&key=...     — Run ML scoring on pending value bets (admin)
 *   ?action=filter&key=...      — Filter value bets through ML (admin)
 *   ?action=metrics             — Latest model metrics (public)
 *   ?action=clv                 — CLV analysis (public)
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';
require_once dirname(__FILE__) . '/sports_schema.php';

_sb_ensure_schema($conn);

$ADMIN_KEY = isset($SPORTS_ADMIN_KEY) ? $SPORTS_ADMIN_KEY : 'livetrader2026';

// ── Ensure ML tables exist ──
$conn->query("CREATE TABLE IF NOT EXISTS lm_sports_ml_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    value_bet_id INT NOT NULL DEFAULT 0,
    event_id VARCHAR(100) NOT NULL,
    sport VARCHAR(50) NOT NULL DEFAULT '',
    home_team VARCHAR(100) NOT NULL DEFAULT '',
    away_team VARCHAR(100) NOT NULL DEFAULT '',
    outcome_name VARCHAR(100) NOT NULL DEFAULT '',
    market VARCHAR(20) NOT NULL DEFAULT 'h2h',
    ev_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    best_odds DECIMAL(10,4) NOT NULL DEFAULT 0,
    ml_win_prob DECIMAL(6,4) NOT NULL DEFAULT 0.5000,
    ml_prediction VARCHAR(20) NOT NULL DEFAULT 'lean',
    ml_confidence VARCHAR(20) NOT NULL DEFAULT 'low',
    ml_should_bet TINYINT NOT NULL DEFAULT 0,
    model_type VARCHAR(50) NOT NULL DEFAULT 'baseline',
    predicted_at DATETIME NOT NULL,
    KEY idx_event (event_id),
    KEY idx_ml_pred (ml_prediction),
    KEY idx_ml_prob (ml_win_prob),
    KEY idx_predicted (predicted_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS lm_sports_ml_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metric_date DATE NOT NULL,
    model_type VARCHAR(50) NOT NULL DEFAULT 'ensemble',
    n_training_bets INT NOT NULL DEFAULT 0,
    accuracy DECIMAL(6,4) DEFAULT NULL,
    auc_roc DECIMAL(6,4) DEFAULT NULL,
    brier_score DECIMAL(6,4) DEFAULT NULL,
    precision_score DECIMAL(6,4) DEFAULT NULL,
    recall_score DECIMAL(6,4) DEFAULT NULL,
    f1_score DECIMAL(6,4) DEFAULT NULL,
    avg_clv DECIMAL(8,4) DEFAULT NULL,
    positive_clv_pct DECIMAL(6,2) DEFAULT NULL,
    top_features TEXT,
    notes TEXT,
    recorded_at DATETIME NOT NULL,
    UNIQUE KEY idx_date_model (metric_date, model_type)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ── Action routing ──
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'status';

if ($action === 'status') {
    _ml_action_status($conn);
} elseif ($action === 'predict') {
    _ml_action_predict($conn);
} elseif ($action === 'filter') {
    _ml_action_filter($conn);
} elseif ($action === 'metrics') {
    _ml_action_metrics($conn);
} elseif ($action === 'clv') {
    _ml_action_clv($conn);
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;


// ════════════════════════════════════════════════════════════
//  ACTION: status — ML system status
// ════════════════════════════════════════════════════════════

function _ml_action_status($conn) {
    // Count settled bets available for training
    $settled_q = $conn->query("SELECT COUNT(*) as total,
        SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses
        FROM lm_sports_bets WHERE result IN ('won', 'lost')");
    $settled = array('total' => 0, 'wins' => 0, 'losses' => 0);
    if ($settled_q && $row = $settled_q->fetch_assoc()) {
        $settled = array(
            'total'  => (int)$row['total'],
            'wins'   => (int)$row['wins'],
            'losses' => (int)$row['losses']
        );
    }

    // Count pending bets
    $pending_q = $conn->query("SELECT COUNT(*) as cnt FROM lm_sports_bets WHERE status='pending'");
    $pending = 0;
    if ($pending_q && $row = $pending_q->fetch_assoc()) {
        $pending = (int)$row['cnt'];
    }

    // Count ML predictions made today
    $pred_q = $conn->query("SELECT COUNT(*) as cnt FROM lm_sports_ml_predictions WHERE predicted_at >= CURDATE()");
    $predictions_today = 0;
    if ($pred_q && $row = $pred_q->fetch_assoc()) {
        $predictions_today = (int)$row['cnt'];
    }

    // Latest metrics
    $metrics_q = $conn->query("SELECT * FROM lm_sports_ml_metrics ORDER BY recorded_at DESC LIMIT 1");
    $latest_metrics = null;
    if ($metrics_q && $row = $metrics_q->fetch_assoc()) {
        $latest_metrics = $row;
    }

    // Data status
    $total = $settled['total'];
    $data_status = 'collecting';
    if ($total >= 500)     $data_status = 'production_ready';
    elseif ($total >= 100) $data_status = 'ideal';
    elseif ($total >= 20)  $data_status = 'trainable';

    echo json_encode(array(
        'ok' => true,
        'settled_bets' => $settled,
        'pending_bets' => $pending,
        'predictions_today' => $predictions_today,
        'data_status' => $data_status,
        'bets_until_trainable' => max(0, 20 - $total),
        'bets_until_ideal' => max(0, 100 - $total),
        'bets_until_production' => max(0, 500 - $total),
        'latest_metrics' => $latest_metrics,
        'ml_features' => array(
            'core' => array('ev_pct', 'odds', 'implied_prob', 'kelly_fraction'),
            'market' => array('h2h', 'spreads', 'totals'),
            'sport' => array('NBA', 'NHL', 'NFL', 'MLB', 'NCAAB', 'MLS'),
            'context' => array('is_underdog', 'hours_to_game', 'day_of_week', 'num_books'),
            'rolling' => array('win_rate_10', 'roi_10', 'clv_10', 'streak', 'bankroll_pct')
        ),
        'models' => array('RandomForest', 'GradientBoosting', 'XGBoost', 'LightGBM', 'LogisticRegression (meta)')
    ));
}


// ════════════════════════════════════════════════════════════
//  ACTION: predict — Run ML scoring via internal heuristic
//  (Pure PHP implementation — no Python dependency on server)
// ════════════════════════════════════════════════════════════

function _ml_action_predict($conn) {
    global $ADMIN_KEY;

    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    // Fetch active value bets
    $vb_q = $conn->query("SELECT * FROM lm_sports_value_bets WHERE status='active' AND commence_time > NOW() ORDER BY ev_pct DESC LIMIT 100");
    if (!$vb_q) {
        echo json_encode(array('ok' => false, 'error' => 'Query failed'));
        return;
    }

    // Fetch current performance stats for rolling features
    $stats = _ml_get_rolling_stats($conn);

    $predictions = array();
    $takes = 0;
    $skips = 0;
    $now = gmdate('Y-m-d H:i:s');

    while ($vb = $vb_q->fetch_assoc()) {
        // ── ML-style scoring (PHP heuristic matching Python model logic) ──
        $score = _ml_score_bet($vb, $stats);

        // Store prediction
        $conn->query("INSERT INTO lm_sports_ml_predictions "
            . "(value_bet_id, event_id, sport, home_team, away_team, outcome_name, market, "
            . "ev_pct, best_odds, ml_win_prob, ml_prediction, ml_confidence, ml_should_bet, "
            . "model_type, predicted_at) VALUES ("
            . (int)$vb['id'] . ", "
            . "'" . $conn->real_escape_string($vb['event_id']) . "', "
            . "'" . $conn->real_escape_string($vb['sport']) . "', "
            . "'" . $conn->real_escape_string($vb['home_team']) . "', "
            . "'" . $conn->real_escape_string($vb['away_team']) . "', "
            . "'" . $conn->real_escape_string($vb['outcome_name']) . "', "
            . "'" . $conn->real_escape_string($vb['market']) . "', "
            . (float)$vb['ev_pct'] . ", "
            . (float)$vb['best_odds'] . ", "
            . (float)$score['ml_win_prob'] . ", "
            . "'" . $conn->real_escape_string($score['prediction']) . "', "
            . "'" . $conn->real_escape_string($score['confidence']) . "', "
            . ($score['should_bet'] ? 1 : 0) . ", "
            . "'php_heuristic_v1', "
            . "'" . $conn->real_escape_string($now) . "')");

        $pred = array(
            'value_bet_id' => (int)$vb['id'],
            'event_id' => $vb['event_id'],
            'sport' => $vb['sport'],
            'matchup' => $vb['away_team'] . ' @ ' . $vb['home_team'],
            'outcome' => $vb['outcome_name'],
            'market' => $vb['market'],
            'ev_pct' => (float)$vb['ev_pct'],
            'best_odds' => (float)$vb['best_odds'],
            'ml_win_prob' => $score['ml_win_prob'],
            'ml_prediction' => $score['prediction'],
            'ml_confidence' => $score['confidence'],
            'ml_should_bet' => $score['should_bet'],
            'ml_reasons' => $score['reasons']
        );
        $predictions[] = $pred;

        if ($score['should_bet']) $takes++;
        else $skips++;
    }

    echo json_encode(array(
        'ok' => true,
        'predictions' => $predictions,
        'total_scored' => count($predictions),
        'ml_takes' => $takes,
        'ml_skips' => $skips,
        'model_type' => 'php_heuristic_v1',
        'scored_at' => $now . ' UTC'
    ));
}


// ════════════════════════════════════════════════════════════
//  ACTION: filter — Filter value bets, only pass ML-approved ones
// ════════════════════════════════════════════════════════════

function _ml_action_filter($conn) {
    global $ADMIN_KEY;

    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    // Get latest ML predictions
    $pred_q = $conn->query("SELECT * FROM lm_sports_ml_predictions "
        . "WHERE predicted_at >= DATE_SUB(NOW(), INTERVAL 6 HOUR) "
        . "AND ml_should_bet = 1 "
        . "ORDER BY ml_win_prob DESC");

    $filtered = array();
    if ($pred_q) {
        while ($row = $pred_q->fetch_assoc()) {
            $filtered[] = array(
                'event_id' => $row['event_id'],
                'sport' => $row['sport'],
                'matchup' => $row['away_team'] . ' @ ' . $row['home_team'],
                'outcome' => $row['outcome_name'],
                'market' => $row['market'],
                'ev_pct' => (float)$row['ev_pct'],
                'ml_win_prob' => (float)$row['ml_win_prob'],
                'ml_confidence' => $row['ml_confidence']
            );
        }
    }

    echo json_encode(array(
        'ok' => true,
        'ml_approved_bets' => $filtered,
        'count' => count($filtered),
        'message' => count($filtered) . ' bets passed ML filter'
    ));
}


// ════════════════════════════════════════════════════════════
//  ACTION: metrics — Latest model metrics
// ════════════════════════════════════════════════════════════

function _ml_action_metrics($conn) {
    $q = $conn->query("SELECT * FROM lm_sports_ml_metrics ORDER BY recorded_at DESC LIMIT 10");
    $metrics = array();
    if ($q) {
        while ($row = $q->fetch_assoc()) {
            $metrics[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'metrics' => $metrics,
        'count' => count($metrics)
    ));
}


// ════════════════════════════════════════════════════════════
//  ACTION: clv — CLV (Closing Line Value) analysis
// ════════════════════════════════════════════════════════════

function _ml_action_clv($conn) {
    // Overall CLV from settled bets
    $clv_q = $conn->query("SELECT b.id, b.event_id, b.sport, b.odds as bet_odds,
        b.result, b.pnl, b.home_team, b.away_team,
        c.opening_price, c.closing_price, c.clv_pct
        FROM lm_sports_bets b
        LEFT JOIN lm_sports_clv c
            ON b.event_id = c.event_id
            AND b.bookmaker_key = c.bookmaker_key
            AND b.market = c.market
        WHERE b.status = 'settled'
        ORDER BY b.placed_at ASC");

    $bets = array();
    $total_clv = 0;
    $clv_count = 0;
    $positive_clv = 0;

    if ($clv_q) {
        while ($row = $clv_q->fetch_assoc()) {
            $bet_odds = (float)$row['bet_odds'];
            $closing = isset($row['closing_price']) ? (float)$row['closing_price'] : 0;
            $computed_clv = 0;

            if ($closing > 1.0 && $bet_odds > 1.0) {
                $computed_clv = ($bet_odds / $closing) - 1.0;
                $total_clv += $computed_clv;
                $clv_count++;
                if ($computed_clv > 0) $positive_clv++;
            }

            $bets[] = array(
                'event_id' => $row['event_id'],
                'sport' => $row['sport'],
                'matchup' => $row['away_team'] . ' @ ' . $row['home_team'],
                'bet_odds' => $bet_odds,
                'closing_odds' => $closing,
                'clv' => round($computed_clv, 4),
                'result' => $row['result'],
                'pnl' => (float)$row['pnl']
            );
        }
    }

    $avg_clv = ($clv_count > 0) ? $total_clv / $clv_count : 0;
    $positive_pct = ($clv_count > 0) ? ($positive_clv / $clv_count) * 100 : 0;

    $interpretation = '';
    if ($avg_clv > 0.02) {
        $interpretation = 'Excellent! Average CLV of +' . round($avg_clv * 100, 1) . '% indicates a strong long-term edge.';
    } elseif ($avg_clv > 0) {
        $interpretation = 'Positive CLV of +' . round($avg_clv * 100, 1) . '% is encouraging. Keep collecting data.';
    } elseif ($avg_clv > -0.02) {
        $interpretation = 'CLV near zero. Need more data to determine if there is an edge.';
    } else {
        $interpretation = 'Negative CLV. The algorithm may be picking stale lines.';
    }

    echo json_encode(array(
        'ok' => true,
        'total_settled' => count($bets),
        'clv_tracked' => $clv_count,
        'avg_clv' => round($avg_clv, 4),
        'avg_clv_pct' => round($avg_clv * 100, 2),
        'positive_clv_pct' => round($positive_pct, 1),
        'interpretation' => $interpretation,
        'bets' => $bets
    ));
}


// ════════════════════════════════════════════════════════════
//  ML Scoring Heuristic (PHP-native, mirrors Python model logic)
// ════════════════════════════════════════════════════════════

function _ml_score_bet($vb, $stats) {
    $ev = (float)$vb['ev_pct'];
    $odds = (float)$vb['best_odds'];
    $ip = (float)$vb['true_prob'];
    $market = isset($vb['market']) ? $vb['market'] : 'h2h';
    $sport = isset($vb['sport']) ? $vb['sport'] : '';
    $reasons = array();

    // Base probability from implied probability
    $base_prob = ($ip > 0 && $ip < 1) ? $ip : 0.5;

    // ── Factor 1: EV adjustment (higher EV = slight boost) ──
    $ev_boost = 0;
    if ($ev >= 10) {
        $ev_boost = 0.08;
        $reasons[] = 'Exceptional EV (+' . round($ev, 1) . '%)';
    } elseif ($ev >= 7) {
        $ev_boost = 0.05;
        $reasons[] = 'Strong EV (+' . round($ev, 1) . '%)';
    } elseif ($ev >= 5) {
        $ev_boost = 0.03;
        $reasons[] = 'Good EV (+' . round($ev, 1) . '%)';
    } elseif ($ev >= 3) {
        $ev_boost = 0.01;
    } else {
        $ev_boost = -0.02;
        $reasons[] = 'Marginal EV — higher risk';
    }

    // ── Factor 2: Market type reliability ──
    $market_adj = 0;
    if ($market === 'h2h') {
        $market_adj = 0.03;
        $reasons[] = 'Moneyline (most predictable market)';
    } elseif ($market === 'spreads') {
        $market_adj = 0.01;
    } elseif ($market === 'totals') {
        $market_adj = -0.02;
        $reasons[] = 'Totals market (less predictable)';
    }

    // ── Factor 3: Underdog penalty ──
    $dog_adj = 0;
    if ($odds > 5.0) {
        $dog_adj = -0.12;
        $reasons[] = 'Heavy underdog (odds ' . round($odds, 1) . ') — high risk';
    } elseif ($odds > 3.0) {
        $dog_adj = -0.06;
        $reasons[] = 'Moderate underdog';
    } elseif ($odds > 2.0) {
        $dog_adj = -0.02;
    } elseif ($odds < 1.3) {
        $dog_adj = 0.04;
        $reasons[] = 'Heavy favorite (lower risk)';
    }

    // ── Factor 4: Consensus strength (num books) ──
    $num_books = 5;
    $ao = isset($vb['all_odds']) ? $vb['all_odds'] : '';
    if (is_string($ao)) {
        $decoded = json_decode($ao, true);
        if (is_array($decoded)) $num_books = count($decoded);
    }
    $consensus_adj = 0;
    if ($num_books >= 7) {
        $consensus_adj = 0.04;
        $reasons[] = $num_books . ' books agree (strong consensus)';
    } elseif ($num_books >= 5) {
        $consensus_adj = 0.02;
    } elseif ($num_books <= 2) {
        $consensus_adj = -0.05;
        $reasons[] = 'Only ' . $num_books . ' books (weak consensus)';
    }

    // ── Factor 5: Rolling performance momentum ──
    $momentum_adj = 0;
    $rolling_wr = (float)$stats['rolling_win_rate'];
    $rolling_roi = (float)$stats['rolling_roi'];
    if ($rolling_wr > 0.4) {
        $momentum_adj = 0.02;
    } elseif ($rolling_wr < 0.2 && $stats['total_bets'] >= 5) {
        $momentum_adj = -0.03;
        $reasons[] = 'Low recent win rate (' . round($rolling_wr * 100) . '%) — caution';
    }

    // ── Factor 6: Sport-specific adjustment ──
    $sport_adj = 0;
    // Some sports are more predictable than others
    if ($sport === 'basketball_nba' || $sport === 'basketball_ncaab') {
        $sport_adj = 0.01;  // Basketball slightly more predictable
    } elseif ($sport === 'americanfootball_nfl') {
        $sport_adj = 0.02;  // NFL home field is significant
    } elseif ($sport === 'baseball_mlb') {
        $sport_adj = -0.01;  // Baseball high variance
    }

    // ── Factor 7: Time to game ──
    $time_adj = 0;
    $commence = strtotime($vb['commence_time']);
    $hours_away = ($commence > 0) ? ($commence - time()) / 3600.0 : 12;
    if ($hours_away > 12) {
        $time_adj = 0.01;  // More time = odds still settling
    } elseif ($hours_away < 1) {
        $time_adj = -0.03;  // Too close — odds likely moved
        $reasons[] = 'Game imminent — odds may be stale';
    }

    // ── Combine all adjustments ──
    $ml_prob = $base_prob + $ev_boost + $market_adj + $dog_adj + $consensus_adj + $momentum_adj + $sport_adj + $time_adj;

    // Clip to valid range
    if ($ml_prob > 0.95) $ml_prob = 0.95;
    if ($ml_prob < 0.05) $ml_prob = 0.05;

    // ── Decision logic ──
    $prediction = 'lean';
    $confidence = 'low';
    $should_bet = false;

    if ($ml_prob > 0.55 && $ev >= 5.0) {
        $prediction = 'strong_take';
        $confidence = 'high';
        $should_bet = true;
    } elseif ($ml_prob > 0.45 && $ev >= 3.0) {
        $prediction = 'take';
        $confidence = 'medium';
        $should_bet = true;
    } elseif ($ml_prob > 0.40 && $ev >= 2.0) {
        $prediction = 'lean';
        $confidence = 'low';
        $should_bet = false;
    } else {
        $prediction = 'skip';
        $confidence = 'low';
        $should_bet = false;
    }

    // ── CRITICAL: Heavy underdog filter ──
    // The system has been picking heavy underdogs (odds 5-19x).
    // While individual wins pay big, the expected hit rate is too low.
    // Filter out bets where odds > 6.0 unless EV is extraordinary.
    if ($odds > 6.0 && $ev < 15.0) {
        $prediction = 'skip';
        $confidence = 'low';
        $should_bet = false;
        $reasons[] = 'ML FILTER: Heavy underdog (odds ' . round($odds, 1) . ') with only ' . round($ev, 1) . '% EV. Need EV 15%+ to justify risk.';
    }

    return array(
        'ml_win_prob' => round($ml_prob, 4),
        'prediction' => $prediction,
        'confidence' => $confidence,
        'should_bet' => $should_bet,
        'reasons' => $reasons
    );
}


// ── Helper: Get rolling performance stats ──

function _ml_get_rolling_stats($conn) {
    $stats = array(
        'total_bets' => 0,
        'wins' => 0,
        'losses' => 0,
        'rolling_win_rate' => 0.5,
        'rolling_roi' => 0,
        'bankroll' => 1000,
        'streak' => 0
    );

    // Last 10 settled bets
    $q = $conn->query("SELECT result, pnl, bet_amount FROM lm_sports_bets WHERE result IN ('won', 'lost') ORDER BY settled_at DESC LIMIT 10");
    if ($q) {
        $wins = 0;
        $losses = 0;
        $pnl_sum = 0;
        $wagered_sum = 0;
        $streak = 0;
        $streak_set = false;

        while ($row = $q->fetch_assoc()) {
            if ($row['result'] === 'won') $wins++;
            else $losses++;
            $pnl_sum += (float)$row['pnl'];
            $wagered_sum += (float)$row['bet_amount'];

            if (!$streak_set) {
                $streak = ($row['result'] === 'won') ? 1 : -1;
                $streak_set = true;
            } elseif (($streak > 0 && $row['result'] === 'won') || ($streak < 0 && $row['result'] === 'lost')) {
                $streak += ($streak > 0) ? 1 : -1;
            }
        }

        $total = $wins + $losses;
        $stats['total_bets'] = $total;
        $stats['wins'] = $wins;
        $stats['losses'] = $losses;
        $stats['rolling_win_rate'] = ($total > 0) ? ($wins / $total) : 0.5;
        $stats['rolling_roi'] = ($wagered_sum > 0) ? ($pnl_sum / $wagered_sum * 100) : 0;
        $stats['streak'] = $streak;
    }

    // Current bankroll
    $bk = $conn->query("SELECT bankroll FROM lm_sports_bankroll ORDER BY snapshot_date DESC LIMIT 1");
    if ($bk && $row = $bk->fetch_assoc()) {
        $stats['bankroll'] = (float)$row['bankroll'];
    }

    return $stats;
}

?>
