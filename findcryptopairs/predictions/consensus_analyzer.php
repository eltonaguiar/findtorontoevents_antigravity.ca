<?php
/**
 * Consensus Analyzer - Tracks algorithm agreement and performance
 * PHP 5.2 Compatible
 */

header('Content-Type: application/json');

// Load current predictions and history
$predictionsFile = '../active_calls_v2.json';
$historyFile = 'algorithm_history.json';
$consensusFile = 'consensus_analysis.json';

function loadJson($file) {
    if (!file_exists($file)) return array();
    $content = file_get_contents($file);
    return $content ? json_decode($content, true) : array();
}

function saveJson($file, $data) {
    file_put_contents($file, json_encode($data, JSON_PRETTY_PRINT));
}

// Algorithm definitions
$algorithms = array(
    'KIMI-MTF' => array('type' => 'MINE', 'category' => 'Multi-Timeframe'),
    'A1-TimeSeriesMomentum' => array('type' => 'ACADEMIC', 'category' => 'Momentum'),
    'A2-PairsTrading' => array('type' => 'ACADEMIC', 'category' => 'Mean Reversion'),
    'A3-SimplifiedML' => array('type' => 'ACADEMIC', 'category' => 'Machine Learning'),
    'A4-OpeningRangeBreakout' => array('type' => 'ACADEMIC', 'category' => 'Volatility'),
    'A5-VWAP' => array('type' => 'ACADEMIC', 'category' => 'Volume'),
    'S1-5MinMacro' => array('type' => 'SOCIAL', 'category' => 'Scalping'),
    'S2-RSIMACD' => array('type' => 'SOCIAL', 'category' => 'Oscillator'),
    'S3-WhaleShadow' => array('type' => 'SOCIAL', 'category' => 'On-Chain'),
    'S4-NarrativeVelocity' => array('type' => 'SOCIAL', 'category' => 'Sentiment'),
    'S5-PortfolioSpray' => array('type' => 'SOCIAL', 'category' => 'Risk Management')
);

// Simulate current predictions (would come from competition_engine.php in production)
$currentPredictions = array(
    'POPCAT' => array(
        'price' => 0.0515,
        'predictions' => array(
            'KIMI-MTF' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'A1-TimeSeriesMomentum' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'A2-PairsTrading' => array('signal' => 'NEUTRAL', 'confidence' => 'LOW'),
            'A3-SimplifiedML' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'A4-OpeningRangeBreakout' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'A5-VWAP' => array('signal' => 'NEUTRAL', 'confidence' => 'MEDIUM'),
            'S1-5MinMacro' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'S2-RSIMACD' => array('signal' => 'NEUTRAL', 'confidence' => 'MEDIUM'),
            'S3-WhaleShadow' => array('signal' => 'NEUTRAL', 'confidence' => 'LOW'),
            'S4-NarrativeVelocity' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'S5-PortfolioSpray' => array('signal' => 'NEUTRAL', 'confidence' => 'LOW')
        )
    ),
    'PENGU' => array(
        'price' => 0.00670,
        'predictions' => array(
            'KIMI-MTF' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'A1-TimeSeriesMomentum' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'A2-PairsTrading' => array('signal' => 'BUY', 'confidence' => 'MEDIUM'),
            'A3-SimplifiedML' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'A4-OpeningRangeBreakout' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'A5-VWAP' => array('signal' => 'SELL', 'confidence' => 'MEDIUM'),
            'S1-5MinMacro' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'S2-RSIMACD' => array('signal' => 'NEUTRAL', 'confidence' => 'MEDIUM'),
            'S3-WhaleShadow' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'S4-NarrativeVelocity' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'S5-PortfolioSpray' => array('signal' => 'NEUTRAL', 'confidence' => 'LOW')
        )
    ),
    'DOGE' => array(
        'price' => 0.0967,
        'predictions' => array(
            'KIMI-MTF' => array('signal' => 'BUY', 'confidence' => 'MEDIUM'),
            'A1-TimeSeriesMomentum' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'A2-PairsTrading' => array('signal' => 'NEUTRAL', 'confidence' => 'LOW'),
            'A3-SimplifiedML' => array('signal' => 'BUY', 'confidence' => 'MEDIUM'),
            'A4-OpeningRangeBreakout' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'A5-VWAP' => array('signal' => 'NEUTRAL', 'confidence' => 'MEDIUM'),
            'S1-5MinMacro' => array('signal' => 'BUY', 'confidence' => 'HIGH'),
            'S2-RSIMACD' => array('signal' => 'NEUTRAL', 'confidence' => 'MEDIUM'),
            'S3-WhaleShadow' => array('signal' => 'NEUTRAL', 'confidence' => 'LOW'),
            'S4-NarrativeVelocity' => array('signal' => 'BUY', 'confidence' => 'MEDIUM'),
            'S5-PortfolioSpray' => array('signal' => 'NEUTRAL', 'confidence' => 'LOW')
        )
    ),
    'BTC' => array(
        'price' => 68851,
        'predictions' => array(
            'KIMI-MTF' => array('signal' => 'BUY', 'confidence' => 'LOW'),
            'A1-TimeSeriesMomentum' => array('signal' => 'BUY', 'confidence' => 'MEDIUM'),
            'A2-PairsTrading' => array('signal' => 'NEUTRAL', 'confidence' => 'N/A'),
            'A3-SimplifiedML' => array('signal' => 'BUY', 'confidence' => 'MEDIUM'),
            'A4-OpeningRangeBreakout' => array('signal' => 'BUY', 'confidence' => 'MEDIUM'),
            'A5-VWAP' => array('signal' => 'NEUTRAL', 'confidence' => 'MEDIUM'),
            'S1-5MinMacro' => array('signal' => 'BUY', 'confidence' => 'MEDIUM'),
            'S2-RSIMACD' => array('signal' => 'NEUTRAL', 'confidence' => 'MEDIUM'),
            'S3-WhaleShadow' => array('signal' => 'NEUTRAL', 'confidence' => 'LOW'),
            'S4-NarrativeVelocity' => array('signal' => 'NEUTRAL', 'confidence' => 'LOW'),
            'S5-PortfolioSpray' => array('signal' => 'NEUTRAL', 'confidence' => 'LOW')
        )
    )
);

// Calculate consensus for each asset
function calculateConsensus($predictions) {
    $buyCount = 0;
    $sellCount = 0;
    $neutralCount = 0;
    $highConfBuy = 0;
    $highConfSell = 0;
    
    foreach ($predictions as $algo => $pred) {
        if ($pred['signal'] == 'BUY') {
            $buyCount++;
            if ($pred['confidence'] == 'HIGH') $highConfBuy++;
        } elseif ($pred['signal'] == 'SELL') {
            $sellCount++;
            if ($pred['confidence'] == 'HIGH') $highConfSell++;
        } else {
            $neutralCount++;
        }
    }
    
    $total = count($predictions);
    $consensusSignal = $buyCount > $sellCount && $buyCount > $neutralCount ? 'BUY' : 
                      ($sellCount > $buyCount && $sellCount > $neutralCount ? 'SELL' : 'NEUTRAL');
    $consensusStrength = max($buyCount, $sellCount, $neutralCount) / $total;
    
    return array(
        'signal' => $consensusSignal,
        'buy_count' => $buyCount,
        'sell_count' => $sellCount,
        'neutral_count' => $neutralCount,
        'high_conf_buy' => $highConfBuy,
        'high_conf_sell' => $highConfSell,
        'strength' => round($consensusStrength * 100, 1),
        'agreement_ratio' => round(max($buyCount, $sellCount, $neutralCount) / ($total - max($buyCount, $sellCount, $neutralCount) + 0.1), 2)
    );
}

// Calculate algorithm correlations
function calculateCorrelations($predictions) {
    $correlations = array();
    $algos = array_keys($predictions['POPCAT']['predictions']);
    
    foreach ($algos as $algo1) {
        $correlations[$algo1] = array();
        foreach ($algos as $algo2) {
            if ($algo1 == $algo2) {
                $correlations[$algo1][$algo2] = 1.0;
                continue;
            }
            
            $agreements = 0;
            $total = 0;
            
            foreach ($predictions as $asset => $data) {
                $sig1 = $data['predictions'][$algo1]['signal'];
                $sig2 = $data['predictions'][$algo2]['signal'];
                
                // Count agreement (both BUY, both SELL, or both NEUTRAL)
                if ($sig1 == $sig2) $agreements++;
                $total++;
            }
            
            $correlations[$algo1][$algo2] = $total > 0 ? round($agreements / $total, 2) : 0;
        }
    }
    
    return $correlations;
}

// Identify algorithm clusters
function identifyClusters($correlations) {
    $clusters = array();
    $assigned = array();
    
    // Find pairs with >70% agreement
    foreach ($correlations as $algo1 => $row) {
        if (isset($assigned[$algo1])) continue;
        
        $cluster = array($algo1);
        $assigned[$algo1] = true;
        
        foreach ($row as $algo2 => $corr) {
            if ($algo1 != $algo2 && $corr >= 0.7 && !isset($assigned[$algo2])) {
                $cluster[] = $algo2;
                $assigned[$algo2] = true;
            }
        }
        
        if (count($cluster) > 1) {
            $clusters[] = $cluster;
        }
    }
    
    return $clusters;
}

// Calculate consensus performance tiers
function calculateConsensusTiers($predictions) {
    $tiers = array(
        'unanimous' => array(),      // 90%+ agreement
        'strong' => array(),         // 70-90% agreement
        'moderate' => array(),       // 50-70% agreement
        'weak' => array(),           // <50% agreement
        'conflict' => array()        // Mixed signals
    );
    
    foreach ($predictions as $asset => $data) {
        $consensus = calculateConsensus($data['predictions']);
        $strength = $consensus['strength'];
        
        $entry = array(
            'asset' => $asset,
            'price' => $data['price'],
            'consensus' => $consensus
        );
        
        if ($strength >= 90) {
            $tiers['unanimous'][] = $entry;
        } elseif ($strength >= 70) {
            $tiers['strong'][] = $entry;
        } elseif ($strength >= 50) {
            $tiers['moderate'][] = $entry;
        } elseif ($consensus['buy_count'] > 0 && $consensus['sell_count'] > 0) {
            $tiers['conflict'][] = $entry;
        } else {
            $tiers['weak'][] = $entry;
        }
    }
    
    return $tiers;
}

// Find algorithm pairs with highest agreement
function findBestPairs($correlations) {
    $pairs = array();
    
    foreach ($correlations as $algo1 => $row) {
        foreach ($row as $algo2 => $corr) {
            if ($algo1 < $algo2) { // Avoid duplicates
                $pairs[] = array(
                    'algo1' => $algo1,
                    'algo2' => $algo2,
                    'agreement' => $corr
                );
            }
        }
    }
    
    // Sort by agreement
    usort($pairs, function($a, $b) {
        return $b['agreement'] > $a['agreement'] ? 1 : -1;
    });
    
    return array_slice($pairs, 0, 10);
}

// Academic vs Social comparison
function compareCategories($predictions, $algorithms) {
    $results = array(
        'ACADEMIC' => array('BUY' => 0, 'SELL' => 0, 'NEUTRAL' => 0, 'total' => 0),
        'SOCIAL' => array('BUY' => 0, 'SELL' => 0, 'NEUTRAL' => 0, 'total' => 0),
        'MINE' => array('BUY' => 0, 'SELL' => 0, 'NEUTRAL' => 0, 'total' => 0)
    );
    
    foreach ($predictions as $asset => $data) {
        foreach ($data['predictions'] as $algo => $pred) {
            $type = $algorithms[$algo]['type'];
            $results[$type][$pred['signal']]++;
            $results[$type]['total']++;
        }
    }
    
    // Calculate percentages
    foreach ($results as $type => $counts) {
        $total = $counts['total'];
        if ($total > 0) {
            $results[$type]['buy_pct'] = round($counts['BUY'] / $total * 100, 1);
            $results[$type]['sell_pct'] = round($counts['SELL'] / $total * 100, 1);
            $results[$type]['neutral_pct'] = round($counts['NEUTRAL'] / $total * 100, 1);
        }
    }
    
    return $results;
}

// MAIN ANALYSIS
$analysis = array(
    'timestamp' => date('c'),
    'consensus_by_asset' => array(),
    'consensus_tiers' => array(),
    'algorithm_correlations' => array(),
    'clusters' => array(),
    'best_pairs' => array(),
    'category_comparison' => array(),
    'meta_consensus' => array()
);

// Calculate per-asset consensus
foreach ($currentPredictions as $asset => $data) {
    $analysis['consensus_by_asset'][$asset] = calculateConsensus($data['predictions']);
}

// Calculate correlations
$analysis['algorithm_correlations'] = calculateCorrelations($currentPredictions);

// Identify clusters
$analysis['clusters'] = identifyClusters($analysis['algorithm_correlations']);

// Find best pairs
$analysis['best_pairs'] = findBestPairs($analysis['algorithm_correlations']);

// Consensus tiers
$analysis['consensus_tiers'] = calculateConsensusTiers($currentPredictions);

// Category comparison
$analysis['category_comparison'] = compareCategories($currentPredictions, $algorithms);

// Meta-consensus: which algorithms agree with the majority?
$metaConsensus = array();
foreach ($currentPredictions as $asset => $data) {
    $consensus = calculateConsensus($data['predictions']);
    foreach ($data['predictions'] as $algo => $pred) {
        if (!isset($metaConsensus[$algo])) {
            $metaConsensus[$algo] = array('with_majority' => 0, 'against_majority' => 0, 'total' => 0);
        }
        
        if ($pred['signal'] == $consensus['signal']) {
            $metaConsensus[$algo]['with_majority']++;
        } else {
            $metaConsensus[$algo]['against_majority']++;
        }
        $metaConsensus[$algo]['total']++;
    }
}

// Calculate conformity scores
foreach ($metaConsensus as $algo => $data) {
    $metaConsensus[$algo]['conformity_score'] = $data['total'] > 0 ? 
        round($data['with_majority'] / $data['total'] * 100, 1) : 0;
}

$analysis['meta_consensus'] = $metaConsensus;

// Save and output
saveJson($consensusFile, $analysis);
echo json_encode($analysis, JSON_PRETTY_PRINT);

// Print summary
echo "\n\n=== CONSENSUS ANALYSIS SUMMARY ===\n\n";

echo "CONSENSUS BY ASSET:\n";
foreach ($analysis['consensus_by_asset'] as $asset => $cons) {
    echo sprintf("  %s: %s (%.0f%% strength) - %d BUY / %d SELL / %d NEUTRAL\n", 
        $asset, $cons['signal'], $cons['strength'], $cons['buy_count'], $cons['sell_count'], $cons['neutral_count']);
}

echo "\nTOP ALGORITHM PAIRS (Agreement %):\n";
foreach (array_slice($analysis['best_pairs'], 0, 5) as $pair) {
    echo sprintf("  %s + %s: %.0f%% agreement\n", $pair['algo1'], $pair['algo2'], $pair['agreement'] * 100);
}

echo "\nALGORITHM CLUSTERS:\n";
foreach ($analysis['clusters'] as $i => $cluster) {
    echo sprintf("  Cluster %d: %s\n", $i + 1, implode(', ', $cluster));
}

echo "\nCATEGORY COMPARISON:\n";
foreach ($analysis['category_comparison'] as $cat => $data) {
    if (isset($data['buy_pct'])) {
        echo sprintf("  %s: %.0f%% BUY, %.0f%% SELL, %.0f%% NEUTRAL\n", 
            $cat, $data['buy_pct'], $data['sell_pct'], $data['neutral_pct']);
    }
}

echo "\nMETA-CONSENSUS (Who follows the crowd?):\n";
arsort($metaConsensus);
foreach ($metaConsensus as $algo => $data) {
    echo sprintf("  %s: %.0f%% conformity\n", $algo, $data['conformity_score']);
}

echo "\n=== ANALYSIS COMPLETE ===\n";
