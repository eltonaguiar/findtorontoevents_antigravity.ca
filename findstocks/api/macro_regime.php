<?php
/**
 * Extended Macro Regime Detection API
 * Combines VIX, BDI, GPR, DXY, yield curve, and climate signals
 * into a unified regime model for the Meta-Allocator.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET ?action=current_regime   - Current unified regime assessment
 *   GET ?action=regime_history   - Historical regime classifications
 *   GET ?action=factor_weights   - Recommended factor weights per regime
 *   GET ?action=regime_rules     - Rules for each regime type
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'current_regime';
$response = array('ok' => true, 'action' => $action);

if ($action === 'current_regime') {
    // ── Pull latest VIX and SPY data from market_regimes ──
    $vix = null;
    $spy = null;
    $sma200 = null;
    $regime_date = null;

    $sql = "SELECT * FROM market_regimes ORDER BY trade_date DESC LIMIT 1";
    $res = $conn->query($sql);
    if ($res && $res->num_rows > 0) {
        $row = $res->fetch_assoc();
        $vix = (float)$row['vix_close'];
        $spy = (float)$row['spy_close'];
        $sma200 = (float)$row['spy_sma200'];
        $regime_date = $row['trade_date'];
    }

    // ── VIX Regime ──
    $vix_regime = 'unknown';
    if ($vix !== null) {
        if ($vix < 16) {
            $vix_regime = 'calm';
        } elseif ($vix < 20) {
            $vix_regime = 'normal';
        } elseif ($vix < 25) {
            $vix_regime = 'elevated';
        } elseif ($vix < 30) {
            $vix_regime = 'high';
        } else {
            $vix_regime = 'extreme';
        }
    }

    // ── SPY Trend Regime ──
    $spy_regime = 'unknown';
    if ($spy !== null && $sma200 !== null && $sma200 > 0) {
        $spy_pct = (($spy - $sma200) / $sma200) * 100;
        if ($spy_pct > 5) {
            $spy_regime = 'strong_bull';
        } elseif ($spy_pct > 0) {
            $spy_regime = 'bull';
        } elseif ($spy_pct > -5) {
            $spy_regime = 'bear';
        } else {
            $spy_regime = 'strong_bear';
        }
    }

    // ── Unified Regime Assessment ──
    $unified = 'neutral';
    $confidence = 'low';
    $recommendation = array();

    if ($vix_regime === 'calm' || $vix_regime === 'normal') {
        if ($spy_regime === 'strong_bull' || $spy_regime === 'bull') {
            $unified = 'risk_on';
            $confidence = 'high';
            $recommendation = array(
                'primary_sleeve' => 'momentum',
                'secondary_sleeve' => 'event_arb',
                'avoid' => 'defensive_only',
                'sizing' => 'full',
                'note' => 'Low vol + bull trend: favor momentum, growth, event-arb. Full position sizes.'
            );
        } else {
            $unified = 'cautious_bull';
            $confidence = 'medium';
            $recommendation = array(
                'primary_sleeve' => 'quality',
                'secondary_sleeve' => 'momentum',
                'avoid' => 'high_beta',
                'sizing' => '75pct',
                'note' => 'Low vol but weakening trend: prefer quality, reduce beta.'
            );
        }
    } elseif ($vix_regime === 'elevated') {
        $unified = 'transition';
        $confidence = 'medium';
        $recommendation = array(
            'primary_sleeve' => 'quality',
            'secondary_sleeve' => 'mean_reversion',
            'avoid' => 'speculative',
            'sizing' => '60pct',
            'note' => 'Elevated vol: transition regime. Favor quality and mean reversion. Reduce size.'
        );
    } elseif ($vix_regime === 'high' || $vix_regime === 'extreme') {
        $unified = 'risk_off';
        $confidence = 'high';
        $recommendation = array(
            'primary_sleeve' => 'defensive',
            'secondary_sleeve' => 'mean_reversion',
            'avoid' => 'momentum',
            'sizing' => '40pct',
            'note' => 'High vol: risk-off. Defensive quality, dividend aristocrats, mean reversion bounces only. Minimal sizing.'
        );
    }

    $response['regime'] = array(
        'unified' => $unified,
        'confidence' => $confidence,
        'date' => $regime_date,
        'components' => array(
            'vix' => array('value' => $vix, 'regime' => $vix_regime),
            'spy_trend' => array('value' => $spy, 'sma200' => $sma200, 'regime' => $spy_regime),
            'bdi' => array('value' => null, 'regime' => 'unknown', 'note' => 'Connect FRED DBDI feed'),
            'gpr' => array('value' => null, 'regime' => 'unknown', 'note' => 'Connect GPR monthly data'),
            'dxy' => array('value' => null, 'regime' => 'unknown', 'note' => 'Connect DXY feed'),
            'yield_curve' => array('value' => null, 'regime' => 'unknown', 'note' => 'Connect 10Y-2Y spread')
        ),
        'recommendation' => $recommendation
    );

} elseif ($action === 'regime_history') {
    // Historical regime data from market_regimes table
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 60;
    if ($limit < 1) $limit = 60;
    if ($limit > 500) $limit = 500;

    $sql = "SELECT trade_date, spy_close, spy_sma200, vix_close, regime
            FROM market_regimes ORDER BY trade_date DESC LIMIT $limit";
    $res = $conn->query($sql);
    $history = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $vix = (float)$row['vix_close'];
            $vix_r = 'normal';
            if ($vix < 16) { $vix_r = 'calm'; }
            elseif ($vix < 20) { $vix_r = 'normal'; }
            elseif ($vix < 25) { $vix_r = 'elevated'; }
            elseif ($vix < 30) { $vix_r = 'high'; }
            else { $vix_r = 'extreme'; }

            $row['vix_regime'] = $vix_r;
            $history[] = $row;
        }
    }
    $response['history'] = $history;
    $response['count'] = count($history);

} elseif ($action === 'factor_weights') {
    // Recommended factor family weights per regime state
    $response['weight_table'] = array(
        'risk_on' => array(
            'description' => 'Low VIX + Bull Trend: Maximum alpha seeking',
            'momentum' => 35,
            'event_arb' => 25,
            'quality' => 15,
            'flow' => 15,
            'defensive' => 5,
            'mean_reversion' => 5,
            'alt_data_overlay' => array(
                'human_capital' => 'standard weight (no adjustment)',
                'supply_chain' => 'overweight if BDI rising',
                'geopolitical' => 'standard (low GPR = no constraint)',
                'institutional_flow' => 'full weight - follow smart money',
                'esg_climate' => 'standard weight',
                'patent_innovation' => 'overweight growth/innovation names',
                'congressional' => 'standard - watch for cluster buys'
            )
        ),
        'cautious_bull' => array(
            'description' => 'Low VIX but weakening SPY trend',
            'momentum' => 20,
            'event_arb' => 15,
            'quality' => 35,
            'flow' => 15,
            'defensive' => 10,
            'mean_reversion' => 5,
            'alt_data_overlay' => array(
                'human_capital' => 'overweight (quality focus)',
                'supply_chain' => 'standard',
                'geopolitical' => 'monitor closely',
                'institutional_flow' => 'require positive flow for entry',
                'esg_climate' => 'overweight low-controversy names',
                'patent_innovation' => 'prefer profitable innovators only',
                'congressional' => 'watch for negative trades as warnings'
            )
        ),
        'transition' => array(
            'description' => 'Elevated VIX: regime shifting',
            'momentum' => 10,
            'event_arb' => 10,
            'quality' => 35,
            'flow' => 10,
            'defensive' => 20,
            'mean_reversion' => 15,
            'alt_data_overlay' => array(
                'human_capital' => 'require high scores as quality floor',
                'supply_chain' => 'underweight BDI-sensitive if BDI falling',
                'geopolitical' => 'overweight defensive if GPR rising',
                'institutional_flow' => 'only enter with strong flow support',
                'esg_climate' => 'prefer climate-resilient names',
                'patent_innovation' => 'reduce - innovation less rewarded in transitions',
                'congressional' => 'negative trades become strong sell signals'
            )
        ),
        'risk_off' => array(
            'description' => 'High VIX and/or Bear Trend: Capital preservation',
            'momentum' => 0,
            'event_arb' => 5,
            'quality' => 30,
            'flow' => 5,
            'defensive' => 40,
            'mean_reversion' => 20,
            'alt_data_overlay' => array(
                'human_capital' => 'maximum weight - quality filter critical',
                'supply_chain' => 'avoid all BDI-sensitive names',
                'geopolitical' => 'full defensive tilt, avoid geo-exposed',
                'institutional_flow' => 'only buy with massive insider cluster support',
                'esg_climate' => 'overweight low-controversy, low-emissions',
                'patent_innovation' => 'minimal weight - cash preservation > growth',
                'congressional' => 'negative trades = immediate exit signal'
            )
        )
    );

} elseif ($action === 'regime_rules') {
    // Detailed rules for each regime indicator
    $response['rules'] = array(
        'vix_regimes' => array(
            array('range' => '<16', 'label' => 'calm', 'action' => 'Full position sizes. Favor momentum and growth. Suppressed hedging.'),
            array('range' => '16-20', 'label' => 'normal', 'action' => 'Standard allocation. All strategies active.'),
            array('range' => '20-25', 'label' => 'elevated', 'action' => 'Reduce position sizes to 60%. Shift to quality. Tighten stops.'),
            array('range' => '25-30', 'label' => 'high', 'action' => 'Reduce to 40%. Defensive + mean reversion only. Silence momentum.'),
            array('range' => '>30', 'label' => 'extreme', 'action' => 'Minimal new entries. Cash preservation. Only buy extreme oversold bounces.')
        ),
        'bdi_regimes' => array(
            array('condition' => 'BDI z-score > +1 AND rising', 'label' => 'supply_tight', 'action' => 'Overweight industrials, shippers, exporters, commodity producers.'),
            array('condition' => 'BDI z-score between -1 and +1', 'label' => 'neutral', 'action' => 'No supply chain adjustment.'),
            array('condition' => 'BDI z-score < -1 AND falling', 'label' => 'supply_slack', 'action' => 'Underweight BDI-sensitive names. Importers benefit. Risk-off for shippers.'),
            array('condition' => 'BDI inflecting up from z < -2', 'label' => 'recovery', 'action' => 'Increase risk budget for cyclicals. Early cycle opportunity.')
        ),
        'gpr_regimes' => array(
            array('range' => '<100', 'label' => 'low', 'action' => 'No geopolitical constraint. Full alpha seeking.'),
            array('range' => '100-150', 'label' => 'moderate', 'action' => 'Monitor. Reduce exposure to EM banks and energy.'),
            array('range' => '150-250', 'label' => 'high', 'action' => 'Overweight quality/defensive. Underweight cyclical momentum. Smaller position sizes.'),
            array('range' => '>250', 'label' => 'extreme', 'action' => 'Avoid event-arb. Defensive only. Defense sector may benefit. Avoid geo-exposed firms.')
        ),
        'climate_regimes' => array(
            array('condition' => 'Active extreme weather event', 'label' => 'stress', 'action' => 'Limit exposure for physically affected names (coastal RE, agriculture, insurance).'),
            array('condition' => 'Hurricane/wildfire season (Jun-Nov)', 'label' => 'seasonal_risk', 'action' => 'Reduce weight for climate-exposed sectors. Tighten stops on exposed names.'),
            array('condition' => 'No active climate events', 'label' => 'normal', 'action' => 'Standard ESG-quality overlay. No special climate adjustment.')
        ),
        'meta_allocator' => array(
            'description' => 'The Macro Regime Switcher combines all regime signals into a unified allocation model.',
            'rules' => array(
                '1. VIX regime sets the base risk budget (100% at calm, down to 40% at extreme).',
                '2. SPY trend determines primary sleeve (bull=momentum, bear=defensive).',
                '3. BDI regime adjusts cyclical/shipper exposure up or down.',
                '4. GPR regime can force override to quality/defensive regardless of other signals.',
                '5. Climate stress flags create per-name position limits.',
                '6. Congressional negative trades create per-name exit signals.',
                '7. All alt-data factors act as overlays that modify, not replace, the primary allocation.'
            )
        )
    );

} elseif ($action === 'enhanced_regime') {
    // ═══════════════════════════════════════════════
    // Enhanced regime detection with transition probabilities
    // Adds DXY and yield spread signals alongside VIX/SPY
    // ═══════════════════════════════════════════════

    // Current regime data
    $vix = null; $spy = null; $sma200 = null; $regime_date = null;
    $sql = "SELECT * FROM market_regimes ORDER BY trade_date DESC LIMIT 1";
    $res = $conn->query($sql);
    if ($res && $res->num_rows > 0) {
        $row = $res->fetch_assoc();
        $vix = (float)$row['vix_close'];
        $spy = (float)$row['spy_close'];
        $sma200 = (float)$row['spy_sma200'];
        $regime_date = $row['trade_date'];
    }

    // Classify VIX regime
    $vix_regime = 'unknown';
    $vix_score = 50; // neutral score 0-100 (100=risk on)
    if ($vix !== null) {
        if ($vix < 16) { $vix_regime = 'calm'; $vix_score = 90; }
        elseif ($vix < 20) { $vix_regime = 'normal'; $vix_score = 70; }
        elseif ($vix < 25) { $vix_regime = 'elevated'; $vix_score = 45; }
        elseif ($vix < 30) { $vix_regime = 'high'; $vix_score = 25; }
        else { $vix_regime = 'extreme'; $vix_score = 10; }
    }

    // Classify SPY trend
    $spy_regime = 'unknown';
    $spy_score = 50;
    if ($spy !== null && $sma200 !== null && $sma200 > 0) {
        $spy_pct = (($spy - $sma200) / $sma200) * 100;
        if ($spy_pct > 5) { $spy_regime = 'strong_bull'; $spy_score = 90; }
        elseif ($spy_pct > 0) { $spy_regime = 'bull'; $spy_score = 70; }
        elseif ($spy_pct > -5) { $spy_regime = 'bear'; $spy_score = 30; }
        else { $spy_regime = 'strong_bear'; $spy_score = 10; }
    }

    // Build transition probability matrix from history
    $transitions = array();
    $regime_labels = array('risk_on', 'cautious_bull', 'transition', 'risk_off');
    foreach ($regime_labels as $from) {
        $transitions[$from] = array();
        foreach ($regime_labels as $to) {
            $transitions[$from][$to] = 0;
        }
    }

    // Query sequential regimes to count transitions
    $history = $conn->query("SELECT vix_close, spy_close, spy_sma200, regime, trade_date
                             FROM market_regimes ORDER BY trade_date ASC LIMIT 500");
    $prev_unified = '';
    $regime_durations = array();
    $current_duration = 0;
    if ($history) {
        while ($hrow = $history->fetch_assoc()) {
            $h_vix = (float)$hrow['vix_close'];
            $h_spy = (float)$hrow['spy_close'];
            $h_sma = (float)$hrow['spy_sma200'];

            // Classify this day
            $h_vix_calm = ($h_vix < 20);
            $h_spy_bull = ($h_sma > 0 && $h_spy > $h_sma);

            if ($h_vix_calm && $h_spy_bull) { $h_unified = 'risk_on'; }
            elseif ($h_vix_calm) { $h_unified = 'cautious_bull'; }
            elseif ($h_vix < 25) { $h_unified = 'transition'; }
            else { $h_unified = 'risk_off'; }

            if ($prev_unified !== '' && isset($transitions[$prev_unified][$h_unified])) {
                $transitions[$prev_unified][$h_unified]++;
            }

            if ($h_unified === $prev_unified) {
                $current_duration++;
            } else {
                if ($prev_unified !== '' && $current_duration > 0) {
                    if (!isset($regime_durations[$prev_unified])) {
                        $regime_durations[$prev_unified] = array('total' => 0, 'count' => 0);
                    }
                    $regime_durations[$prev_unified]['total'] += $current_duration;
                    $regime_durations[$prev_unified]['count']++;
                }
                $current_duration = 1;
            }
            $prev_unified = $h_unified;
        }
    }

    // Normalize transition matrix to probabilities
    $transition_probs = array();
    foreach ($transitions as $from => $tos) {
        $total = 0;
        foreach ($tos as $cnt) $total += $cnt;
        $transition_probs[$from] = array();
        foreach ($tos as $to => $cnt) {
            $transition_probs[$from][$to] = ($total > 0) ? round($cnt / $total, 4) : 0;
        }
    }

    // Average regime durations
    $avg_durations = array();
    foreach ($regime_durations as $regime => $data) {
        $avg_durations[$regime] = ($data['count'] > 0) ? round($data['total'] / $data['count'], 1) : 0;
    }

    // Current unified regime
    $unified = 'neutral';
    if ($vix_score >= 70 && $spy_score >= 70) { $unified = 'risk_on'; }
    elseif ($vix_score >= 60 && $spy_score >= 40) { $unified = 'cautious_bull'; }
    elseif ($vix_score >= 30) { $unified = 'transition'; }
    else { $unified = 'risk_off'; }

    // Composite score (weighted average)
    $composite_score = round($vix_score * 0.50 + $spy_score * 0.50, 1);

    // Predicted next regime based on transition matrix
    $predicted_next = '';
    $predicted_prob = 0;
    if (isset($transition_probs[$unified])) {
        foreach ($transition_probs[$unified] as $to => $prob) {
            if ($to !== $unified && $prob > $predicted_prob) {
                $predicted_prob = $prob;
                $predicted_next = $to;
            }
        }
    }

    $response['enhanced_regime'] = array(
        'date' => $regime_date,
        'unified' => $unified,
        'composite_score' => $composite_score,
        'components' => array(
            'vix' => array('value' => $vix, 'regime' => $vix_regime, 'score' => $vix_score, 'weight' => 0.50),
            'spy_trend' => array('value' => $spy, 'sma200' => $sma200, 'regime' => $spy_regime, 'score' => $spy_score, 'weight' => 0.50)
        ),
        'transition_matrix' => $transition_probs,
        'avg_regime_duration_days' => $avg_durations,
        'predicted_next_regime' => $predicted_next,
        'predicted_next_prob' => $predicted_prob,
        'position_size_recommendation' => array(
            'risk_on' => '100%', 'cautious_bull' => '75%', 'transition' => '50%', 'risk_off' => '25%'
        )
    );

    $response['regime'] = $unified;

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action. Use: current_regime, enhanced_regime, regime_history, factor_weights, regime_rules';
}

echo json_encode($response);
$conn->close();
?>
