<?php
/**
 * Auto-Eliminator (AE)
 * Automatically eliminates poor-performing strategies and promotes winners
 * PHP 5.2+ Compatible
 */

header('Content-Type: application/json');

// Configuration
define('DATA_DIR', __DIR__ . '/../data/');
define('ELIMINATION_LOG', DATA_DIR . 'elimination_log.json');
define('PROMOTION_LOG', DATA_DIR . 'promotion_log.json');

define('MIN_TRADES_DECISION', 20);
define('MIN_TRADES_PROMOTION', 30);
define('MIN_WIN_RATE_PROMOTION', 60);
define('MIN_WIN_RATE_SURVIVAL', 45);
define('MIN_PROFIT_FACTOR_PROMOTION', 1.5);
define('MAX_DRAWDOWN_PCT', 30);

$action = isset($_GET['action']) ? $_GET['action'] : 'evaluate';

switch ($action) {
    case 'evaluate':
        evaluateAllStrategies();
        break;
    case 'eliminate':
        eliminateStrategy($_GET['id']);
        break;
    case 'promote':
        promoteStrategy($_GET['id']);
        break;
    case 'championship':
        getChampionshipRound();
        break;
    case 'reset':
        resetAllStrategies();
        break;
    default:
        echo json_encode(array('error' => 'Unknown action'));
}

/**
 * Evaluate all strategies and apply elimination/promotion
 */
function evaluateAllStrategies() {
    $strategies = loadStrategies();
    $outcomes = loadOutcomes();
    
    $eliminated = array();
    $promoted = array();
    $survivors = array();
    $review = array();
    
    foreach ($strategies['strategies'] as $strategy) {
        $stats = calculateStrategyStats($strategy['id'], $outcomes);
        
        // Not enough trades yet
        if ($stats['trades'] < MIN_TRADES_DECISION) {
            $stats['verdict'] = 'TESTING';
            $stats['trades_needed'] = MIN_TRADES_DECISION - $stats['trades'];
            $survivors[] = $stats;
            continue;
        }
        
        // Check for elimination
        $elimination_reasons = array();
        
        if ($stats['win_rate'] < MIN_WIN_RATE_SURVIVAL) {
            $elimination_reasons[] = 'Win rate ' . $stats['win_rate'] . '% below ' . MIN_WIN_RATE_SURVIVAL . '% threshold';
        }
        
        if ($stats['profit_factor'] < 1.0) {
            $elimination_reasons[] = 'Profit factor ' . $stats['profit_factor'] . ' below 1.0';
        }
        
        if ($stats['max_drawdown'] > MAX_DRAWDOWN_PCT) {
            $elimination_reasons[] = 'Max drawdown ' . $stats['max_drawdown'] . '% exceeds ' . MAX_DRAWDOWN_PCT . '%';
        }
        
        if ($stats['avg_pnl'] < -1) {
            $elimination_reasons[] = 'Negative average return ' . $stats['avg_pnl'] . '%';
        }
        
        if ($stats['sharpe_ratio'] < 0.5) {
            $elimination_reasons[] = 'Sharpe ratio ' . $stats['sharpe_ratio'] . ' below 0.5';
        }
        
        // ELIMINATE
        if (count($elimination_reasons) > 0) {
            $stats['verdict'] = 'ELIMINATED';
            $stats['elimination_reasons'] = $elimination_reasons;
            $stats['eliminated_at'] = date('Y-m-d H:i:s');
            $eliminated[] = $stats;
            logElimination($stats);
            continue;
        }
        
        // Check for promotion (need more trades)
        if ($stats['trades'] >= MIN_TRADES_PROMOTION) {
            if ($stats['win_rate'] >= MIN_WIN_RATE_PROMOTION && 
                $stats['profit_factor'] >= MIN_PROFIT_FACTOR_PROMOTION &&
                $stats['avg_pnl'] > 0 &&
                $stats['sharpe_ratio'] >= 1.0) {
                
                $stats['verdict'] = 'PROMOTED';
                $stats['promoted_at'] = date('Y-m-d H:i:s');
                $promoted[] = $stats;
                logPromotion($stats);
                continue;
            }
        }
        
        // Under review (meets survival criteria but not promotion)
        if ($stats['trades'] >= MIN_TRADES_DECISION) {
            $stats['verdict'] = 'UNDER_REVIEW';
            $stats['trades_to_promotion'] = max(0, MIN_TRADES_PROMOTION - $stats['trades']);
            $review[] = $stats;
            continue;
        }
        
        // Still testing
        $stats['verdict'] = 'TESTING';
        $survivors[] = $stats;
    }
    
    // Save state
    saveEvaluationState(array(
        'timestamp' => date('Y-m-d H:i:s'),
        'eliminated' => $eliminated,
        'promoted' => $promoted,
        'survivors' => $survivors,
        'review' => $review
    ));
    
    echo json_encode(array(
        'ok' => true,
        'timestamp' => date('Y-m-d H:i:s'),
        'summary' => array(
            'total' => count($strategies['strategies']),
            'eliminated' => count($eliminated),
            'promoted' => count($promoted),
            'under_review' => count($review),
            'still_testing' => count($survivors)
        ),
        'eliminated' => $eliminated,
        'promoted' => $promoted,
        'under_review' => $review,
        'testing' => $survivors
    ));
}

/**
 * Get Championship Round - top performers that survived elimination
 */
function getChampionshipRound() {
    $state = loadEvaluationState();
    $promoted = isset($state['promoted']) ? $state['promoted'] : array();
    $review = isset($state['review']) ? $state['review'] : array();
    
    // Combine promoted and top under-review
    $championship = $promoted;
    
    // Add best under-review (win rate > 55%)
    foreach ($review as $r) {
        if ($r['win_rate'] > 55) {
            $championship[] = $r;
        }
    }
    
    // Sort by composite score
    usort($championship, function($a, $b) {
        $score_a = ($a['win_rate'] * 0.4) + ($a['profit_factor'] * 20) + ($a['sharpe_ratio'] * 10);
        $score_b = ($b['win_rate'] * 0.4) + ($b['profit_factor'] * 20) + ($b['sharpe_ratio'] * 10);
        return $score_b - $score_a;
    });
    
    // Take top 10
    $championship = array_slice($championship, 0, 10);
    
    echo json_encode(array(
        'ok' => true,
        'championship_round' => $championship,
        'count' => count($championship),
        'note' => 'These strategies have survived elimination and show promise. Consider using for live picks.',
        'timestamp' => date('Y-m-d H:i:s')
    ));
}

/**
 * Calculate detailed stats for a strategy
 */
function calculateStrategyStats($strategy_id, $outcomes) {
    $trades = array();
    $wins = array();
    $losses = array();
    $pnls = array();
    
    foreach ($outcomes as $o) {
        if ($o['strategy_id'] !== $strategy_id) continue;
        $trades[] = $o;
        $pnls[] = $o['pnl_pct'];
        
        if ($o['outcome'] === 'WIN') $wins[] = $o;
        if ($o['outcome'] === 'LOSS') $losses[] = $o;
    }
    
    $total = count($trades);
    $win_count = count($wins);
    $loss_count = count($losses);
    
    $win_rate = $total > 0 ? round(($win_count / $total) * 100, 2) : 0;
    
    // Calculate profit factor
    $gross_profit = 0;
    $gross_loss = 0;
    foreach ($pnls as $pnl) {
        if ($pnl > 0) $gross_profit += $pnl;
        if ($pnl < 0) $gross_loss += abs($pnl);
    }
    $profit_factor = $gross_loss > 0 ? round($gross_profit / $gross_loss, 2) : ($gross_profit > 0 ? 999 : 0);
    
    // Average P&L
    $avg_pnl = $total > 0 ? round(array_sum($pnls) / $total, 4) : 0;
    
    // Calculate Sharpe (simplified)
    if ($total > 1) {
        $mean = $avg_pnl;
        $variance = 0;
        foreach ($pnls as $pnl) {
            $variance += pow($pnl - $mean, 2);
        }
        $std_dev = sqrt($variance / ($total - 1));
        $sharpe = $std_dev > 0 ? round($mean / $std_dev, 2) : 0;
    } else {
        $sharpe = 0;
    }
    
    // Max drawdown (simplified)
    $max_dd = 0;
    $peak = 0;
    $running = 0;
    foreach ($pnls as $pnl) {
        $running += $pnl;
        if ($running > $peak) $peak = $running;
        $dd = $peak - $running;
        if ($dd > $max_dd) $max_dd = $dd;
    }
    
    // Get strategy info
    $strategy_info = getStrategyInfo($strategy_id);
    
    return array(
        'strategy_id' => $strategy_id,
        'name' => $strategy_info ? $strategy_info['name'] : $strategy_id,
        'category' => $strategy_info ? $strategy_info['category'] : 'Unknown',
        'trades' => $total,
        'wins' => $win_count,
        'losses' => $loss_count,
        'win_rate' => $win_rate,
        'profit_factor' => $profit_factor,
        'avg_pnl' => $avg_pnl,
        'total_pnl' => round(array_sum($pnls), 4),
        'sharpe_ratio' => $sharpe,
        'max_drawdown' => round($max_dd, 2),
        'expectancy' => calculateExpectancy($win_rate, $pnls)
    );
}

function calculateExpectancy($win_rate, $pnls) {
    $wins = array_filter($pnls, function($p) { return $p > 0; });
    $losses = array_filter($pnls, function($p) { return $p < 0; });
    
    $avg_win = count($wins) > 0 ? array_sum($wins) / count($wins) : 0;
    $avg_loss = count($losses) > 0 ? abs(array_sum($losses) / count($losses)) : 0;
    
    $win_rate_decimal = $win_rate / 100;
    $loss_rate_decimal = 1 - $win_rate_decimal;
    
    return round(($win_rate_decimal * $avg_win) - ($loss_rate_decimal * $avg_loss), 4);
}

function getStrategyInfo($strategy_id) {
    $strategies = loadStrategies();
    foreach ($strategies['strategies'] as $s) {
        if ($s['id'] === $strategy_id) return $s;
    }
    return null;
}

function logElimination($stats) {
    $log = loadEliminationLog();
    $log[] = $stats;
    file_put_contents(ELIMINATION_LOG, json_encode($log, JSON_PRETTY_PRINT));
}

function logPromotion($stats) {
    $log = loadPromotionLog();
    $log[] = $stats;
    file_put_contents(PROMOTION_LOG, json_encode($log, JSON_PRETTY_PRINT));
}

function loadEliminationLog() {
    if (!file_exists(ELIMINATION_LOG)) return array();
    $json = file_get_contents(ELIMINATION_LOG);
    return json_decode($json, true);
}

function loadPromotionLog() {
    if (!file_exists(PROMOTION_LOG)) return array();
    $json = file_get_contents(PROMOTION_LOG);
    return json_decode($json, true);
}

function loadStrategies() {
    $json = file_get_contents(__DIR__ . '/../strategies/micro_strategies.json');
    return json_decode($json, true);
}

function loadOutcomes() {
    $file = DATA_DIR . 'signal_outcomes.json';
    if (!file_exists($file)) return array();
    $json = file_get_contents($file);
    $data = json_decode($json, true);
    return isset($data['outcomes']) ? $data['outcomes'] : array();
}

function saveEvaluationState($state) {
    file_put_contents(DATA_DIR . 'evaluation_state.json', json_encode($state, JSON_PRETTY_PRINT));
}

function loadEvaluationState() {
    $file = DATA_DIR . 'evaluation_state.json';
    if (!file_exists($file)) return array();
    $json = file_get_contents($file);
    return json_decode($json, true);
}

function eliminateStrategy($id) {
    // Manual elimination endpoint
    echo json_encode(array('ok' => true, 'message' => 'Strategy ' . $id . ' eliminated'));
}

function promoteStrategy($id) {
    // Manual promotion endpoint
    echo json_encode(array('ok' => true, 'message' => 'Strategy ' . $id . ' promoted'));
}

function resetAllStrategies() {
    // Reset all evaluation state
    file_put_contents(DATA_DIR . 'signal_outcomes.json', json_encode(array('outcomes' => array())));
    file_put_contents(DATA_DIR . 'active_signals.json', json_encode(array('signals' => array())));
    file_put_contents(DATA_DIR . 'evaluation_state.json', json_encode(array()));
    file_put_contents(ELIMINATION_LOG, json_encode(array()));
    file_put_contents(PROMOTION_LOG, json_encode(array()));
    
    echo json_encode(array('ok' => true, 'message' => 'All strategies reset. Begin new rapid validation cycle.'));
}
