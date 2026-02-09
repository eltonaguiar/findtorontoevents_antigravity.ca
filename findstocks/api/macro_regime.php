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

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action. Use: current_regime, regime_history, factor_weights, regime_rules';
}

echo json_encode($response);
$conn->close();
?>
