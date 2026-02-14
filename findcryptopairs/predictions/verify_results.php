<?php
/**
 * Prediction Tracker - Verifies outcomes and tracks accuracy
 * PHP 5.2 Compatible
 * 
 * Usage: cron job every hour to check prediction outcomes
 */

header('Content-Type: application/json');

$predictionsFile = 'active_calls.json';
$historyFile = 'prediction_history.json';

// Load predictions
$json = file_get_contents($predictionsFile);
$data = json_decode($json, true);
$predictions = $data['predictions'];

$results = array(
    'verified_at' => date('c'),
    'total_predictions' => count($predictions),
    'active' => 0,
    'expired' => 0,
    'hit_target' => 0,
    'hit_stop' => 0,
    'neutral' => 0,
    'updated_predictions' => array()
);

foreach ($predictions as $key => $pred) {
    if ($pred['status'] !== 'ACTIVE') {
        continue;
    }
    
    $results['active']++;
    $symbol = $pred['symbol'];
    $currentPrice = getCurrentPrice($symbol);
    
    $targetPrice = $pred['target_price'];
    $stopLoss = $pred['stop_loss'];
    $entryPrice = $pred['current_price'];
    $prediction = $pred['prediction'];
    
    $pChange = (($currentPrice - $entryPrice) / $entryPrice) * 100;
    $result = 'PENDING';
    $resultNotes = '';
    
    // Check if prediction expired
    $now = time();
    $expiry = strtotime($pred['expires_at']);
    $isExpired = $now > $expiry;
    
    // Determine outcome based on prediction type
    if ($prediction === 'BULLISH') {
        if ($currentPrice >= $targetPrice) {
            $result = 'WIN';
            $resultNotes = sprintf('Target hit! Price reached $%.4f (+%.1f%%)', $currentPrice, $pChange);
            $results['hit_target']++;
        } elseif ($currentPrice <= $stopLoss) {
            $result = 'LOSS';
            $resultNotes = sprintf('Stop loss hit! Price dropped to $%.4f (%.1f%%)', $currentPrice, $pChange);
            $results['hit_stop']++;
        } elseif ($isExpired) {
            $result = 'EXPIRED';
            $resultNotes = sprintf('Expired. Final price: $%.4f (%.1f%%)', $currentPrice, $pChange);
            $results['neutral']++;
        }
    } elseif ($prediction === 'BEARISH') {
        if ($currentPrice <= $targetPrice) {
            $result = 'WIN';
            $resultNotes = sprintf('Target hit! Price dropped to $%.4f (%.1f%%)', $currentPrice, $pChange);
            $results['hit_target']++;
        } elseif ($currentPrice >= $stopLoss) {
            $result = 'LOSS';
            $resultNotes = sprintf('Stop loss hit! Price rallied to $%.4f (+%.1f%%)', $currentPrice, $pChange);
            $results['hit_stop']++;
        } elseif ($isExpired) {
            $result = 'EXPIRED';
            $resultNotes = sprintf('Expired. Final price: $%.4f (%.1f%%)', $currentPrice, $pChange);
            $results['neutral']++;
        }
    } elseif ($prediction === 'CONSOLIDATION') {
        // For consolidation, check if price stayed within expected range
        $upperBound = $entryPrice * 1.02; // +2%
        $lowerBound = $entryPrice * 0.95; // -5%
        
        if ($currentPrice >= $lowerBound && $currentPrice <= $upperBound) {
            $result = 'WIN';
            $resultNotes = sprintf('Consolidation confirmed. Price: $%.2f', $currentPrice);
            $results['hit_target']++;
        } elseif ($isExpired) {
            $result = 'EXPIRED';
            $resultNotes = sprintf('Expired. Moved to $%.2f (%.1f%%)', $currentPrice, $pChange);
            $results['neutral']++;
        }
    }
    
    // Update prediction
    if ($result !== 'PENDING') {
        $data['predictions'][$key]['status'] = $result;
        $data['predictions'][$key]['actual_result'] = $result;
        $data['predictions'][$key]['result_notes'] = $resultNotes;
        $data['predictions'][$key]['final_price'] = $currentPrice;
        $data['predictions'][$key]['percent_change'] = round($pChange, 2);
        $data['predictions'][$key]['verified_at'] = date('c');
    }
    
    $results['updated_predictions'][] = array(
        'id' => $pred['id'],
        'symbol' => $symbol,
        'result' => $result,
        'current_price' => $currentPrice,
        'percent_change' => round($pChange, 2),
        'notes' => $resultNotes
    );
}

// Save updated predictions
file_put_contents($predictionsFile, json_encode($data, JSON_PRETTY_PRINT));

// Calculate accuracy if we have history
$accuracy = calculateAccuracy($predictions);
$results['accuracy_stats'] = $accuracy;

echo json_encode($results, JSON_PRETTY_PRINT);

// Helper: Get current price (mock for now, replace with real API)
function getCurrentPrice($symbol) {
    // In production: call Kraken API or CoinGecko
    // For now return simulated prices based on mock data
    $prices = array(
        'POPCAT' => 0.435,  // Simulated: up 6% from 0.41
        'PENGU' => 0.0071,  // Simulated: up 6% from 0.0067
        'DOGE' => 0.0985,   // Simulated: up 1.5% from 0.097
        'AZTEC' => 0.035,   // Simulated: down 5% from 0.037
        'BTC' => 95500      // Simulated: down 1.5% from 97000
    );
    
    return isset($prices[$symbol]) ? $prices[$symbol] : 0;
}

// Calculate accuracy stats
function calculateAccuracy($predictions) {
    $wins = 0;
    $losses = 0;
    $expired = 0;
    $total = 0;
    
    foreach ($predictions as $p) {
        if ($p['status'] === 'WIN') {
            $wins++;
            $total++;
        } elseif ($p['status'] === 'LOSS') {
            $losses++;
            $total++;
        } elseif ($p['status'] === 'EXPIRED') {
            $expired++;
            $total++;
        }
    }
    
    $winRate = $total > 0 ? round(($wins / $total) * 100, 1) : 0;
    
    return array(
        'total_completed' => $total,
        'wins' => $wins,
        'losses' => $losses,
        'expired' => $expired,
        'win_rate' => $winRate . '%'
    );
}
?>
