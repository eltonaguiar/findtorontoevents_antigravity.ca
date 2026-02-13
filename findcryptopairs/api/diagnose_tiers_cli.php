<?php
/**
 * CLI Wrapper for Tier Diagnostic Tool
 * Run from command line: php diagnose_tiers_cli.php [action] [--synthetic]
 * 
 * Actions:
 *   full_diagnosis - Complete analysis (default)
 *   correlations   - Feature correlation only
 *   thresholds     - Threshold optimization only
 *   inversion      - Signal inversion test only
 *   exhaustion     - Momentum exhaustion analysis only
 */

// Allow CLI execution even without HTTP headers
if (php_sapi_name() === 'cli') {
    // Parse command line arguments
    $action = 'full_diagnosis';
    $synthetic = false;
    
    foreach ($argv as $i => $arg) {
        if ($i === 0) continue; // Skip script name
        
        if ($arg === '--synthetic' || $arg === '-s') {
            $synthetic = true;
        } elseif ($arg === '--help' || $arg === '-h') {
            echo "Usage: php diagnose_tiers_cli.php [action] [--synthetic]\n\n";
            echo "Actions:\n";
            echo "  full_diagnosis  Complete analysis (default)\n";
            echo "  correlations    Feature correlation only\n";
            echo "  thresholds      Threshold optimization only\n";
            echo "  inversion       Signal inversion test only\n";
            echo "  exhaustion      Momentum exhaustion analysis only\n\n";
            echo "Options:\n";
            echo "  --synthetic, -s  Use synthetic data for testing\n";
            echo "  --help, -h       Show this help\n";
            exit(0);
        } else {
            $action = $arg;
        }
    }
    
    // Build query string
    $_GET['action'] = $action;
    if ($synthetic) {
        $_GET['synthetic'] = '1';
    }
    
    echo "═══════════════════════════════════════════════════════════════\n";
    echo "  MEME COIN CONFIDENCE TIER DIAGNOSTIC TOOL\n";
    echo "═══════════════════════════════════════════════════════════════\n";
    echo "Action: " . strtoupper($action) . "\n";
    echo "Data: " . ($synthetic ? "SYNTHETIC (testing mode)" : "REAL from database") . "\n";
    echo "Started: " . date('Y-m-d H:i:s') . "\n";
    echo "───────────────────────────────────────────────────────────────\n\n";
    
    // Capture output from main script
    ob_start();
    include dirname(__FILE__) . '/diagnose_tiers.php';
    $output = ob_get_clean();
    
    // Parse and display formatted results
    $data = json_decode($output, true);
    
    if (!$data || !$data['ok']) {
        echo "ERROR: " . ($data['error'] ?? 'Unknown error') . "\n";
        echo "Raw output:\n$output\n";
        exit(1);
    }
    
    // Display formatted results based on action
    display_results($data, $action);
    
    echo "\n═══════════════════════════════════════════════════════════════\n";
    echo "Completed: " . date('Y-m-d H:i:s') . "\n";
    
    if (isset($data['saved_to'])) {
        echo "Report saved to: " . $data['saved_to'] . "\n";
    }
    echo "═══════════════════════════════════════════════════════════════\n";
    
    exit(0);
} else {
    // If accessed via web, redirect to main script
    include dirname(__FILE__) . '/diagnose_tiers.php';
}

/**
 * Display formatted CLI output
 */
function display_results($data, $action) {
    switch ($action) {
        case 'full_diagnosis':
            display_full_diagnosis($data);
            break;
        case 'correlations':
            display_correlations($data);
            break;
        case 'thresholds':
            display_thresholds($data);
            break;
        case 'inversion':
            display_inversion($data);
            break;
        case 'exhaustion':
            display_exhaustion($data);
            break;
        default:
            echo json_encode($data, JSON_PRETTY_PRINT) . "\n";
    }
}

function display_full_diagnosis($data) {
    $report = $data['report'];
    
    echo "📊 DATA SUMMARY\n";
    echo "─────────────────────────────────────────────────────────────\n";
    $summary = $report['data_summary'];
    echo "Samples: " . $summary['samples_loaded'] . "\n";
    echo "Wins: " . $summary['wins'] . " | Losses: " . $summary['losses'] . "\n";
    if (isset($summary['note'])) {
        echo "Note: " . $summary['note'] . "\n";
    }
    echo "\n";
    
    echo "📈 CURRENT TIER PERFORMANCE\n";
    echo "─────────────────────────────────────────────────────────────\n";
    $tiers = $report['current_tier_performance'];
    foreach ($tiers as $tier_name => $perf) {
        echo strtoupper(str_replace('_', ' ', $tier_name)) . ":\n";
        echo "  Signals: " . $perf['count'];
        if ($perf['count'] > 0) {
            echo " | Win Rate: " . $perf['win_rate'] . "%";
            echo " | Avg Return: " . $perf['avg_return'] . "%\n";
        } else {
            echo " (no data)\n";
        }
    }
    echo "\n";
    
    if (isset($report['correlation_summary'])) {
        echo "🔗 FEATURE CORRELATION SUMMARY\n";
        echo "─────────────────────────────────────────────────────────────\n";
        $corr = $report['correlation_summary'];
        echo "Positive correlations: " . $corr['features_with_positive_correlation'] . "\n";
        echo "NEGATIVE correlations: " . $corr['features_with_negative_correlation'] . "\n";
        if (count($corr['inverted_features']) > 0) {
            echo "⚠️  INVERTED features: " . implode(', ', $corr['inverted_features']) . "\n";
        }
        echo "Verdict: " . $corr['verdict'] . "\n\n";
    }
    
    if (isset($report['inversion_hypothesis']['evidence_for_inversion'])) {
        echo "🔄 INVERSION HYPOTHESIS\n";
        echo "─────────────────────────────────────────────────────────────\n";
        $ev = $report['inversion_hypothesis']['evidence_for_inversion'];
        echo "Evidence Score: " . $ev['score'] . "/" . $ev['max_score'] . "\n";
        echo "Verdict: " . $ev['verdict'] . "\n";
        if (count($ev['points']) > 0) {
            echo "Key findings:\n";
            foreach ($ev['points'] as $point) {
                echo "  • " . $point . "\n";
            }
        }
        echo "\n";
    }
    
    if (isset($report['momentum_exhaustion'])) {
        echo "⚡ MOMENTUM EXHAUSTION\n";
        echo "─────────────────────────────────────────────────────────────\n";
        $ex = $report['momentum_exhaustion'];
        if (isset($ex['exhaustion_detected'])) {
            echo "Exhaustion detected: " . ($ex['exhaustion_detected'] ? 'YES ⚠️' : 'No') . "\n";
        }
        if (isset($ex['score_vs_time_to_peak_correlation'])) {
            echo "Score vs Time-to-Peak correlation: " . $ex['score_vs_time_to_peak_correlation']['r'] . "\n";
            echo "Interpretation: " . $ex['score_vs_time_to_peak_correlation']['interpretation'] . "\n";
        }
        echo "\n";
    }
    
    if (isset($report['recommendations'])) {
        echo "📋 RECOMMENDATIONS\n";
        echo "─────────────────────────────────────────────────────────────\n";
        foreach ($report['recommendations'] as $i => $rec) {
            echo ($i + 1) . ". [" . $rec['priority'] . "] " . $rec['category'] . "\n";
            echo "   Issue: " . $rec['issue'] . "\n";
            echo "   Action: " . $rec['action'] . "\n\n";
        }
    }
}

function display_correlations($data) {
    echo "🔗 FEATURE CORRELATIONS\n";
    echo "─────────────────────────────────────────────────────────────\n\n";
    
    if (isset($data['feature_correlations'])) {
        foreach ($data['feature_correlations'] as $fname => $info) {
            echo strtoupper($fname) . ":\n";
            if (isset($info['error'])) {
                echo "  " . $info['error'] . "\n";
            } else {
                echo "  Correlation with win: " . $info['correlation_with_win'];
                if ($info['correlation_with_win'] < -0.2) {
                    echo " ⚠️ INVERTED";
                }
                echo "\n";
                echo "  Correlation with return: " . $info['correlation_with_return'] . "\n";
                echo "  Sample count: " . $info['sample_count'] . "\n";
                echo "  Interpretation: " . $info['interpretation'] . "\n";
            }
            echo "\n";
        }
    }
    
    if (isset($data['summary'])) {
        echo "SUMMARY: " . $data['summary']['verdict'] . "\n";
    }
}

function display_thresholds($data) {
    echo "📊 THRESHOLD OPTIMIZATION\n";
    echo "─────────────────────────────────────────────────────────────\n\n";
    
    if (isset($data['all_tests'])) {
        echo "Tested configurations (sorted by performance):\n\n";
        
        foreach (array_slice($data['all_tests'], 0, 5) as $i => $test) {
            $t = $test['thresholds'];
            $p = $test['performance'];
            
            echo ($i + 1) . ". Thresholds: Lean=" . $t['lean'] . ", Buy=" . $t['buy'] . ", Strong=" . $t['strong'] . "\n";
            echo "   Overall Score: " . $p['overall'] . "\n";
            echo "   Strong Buy: " . $p['strong_buy']['win_rate'] . "% WR (n=" . $p['strong_buy']['count'] . ")\n";
            echo "   Buy: " . $p['buy']['win_rate'] . "% WR (n=" . $p['buy']['count'] . ")\n";
            echo "   Lean Buy: " . $p['lean_buy']['win_rate'] . "% WR (n=" . $p['lean_buy']['count'] . ")\n\n";
        }
    }
    
    if (isset($data['recommended_thresholds'])) {
        $r = $data['recommended_thresholds'];
        echo "✅ RECOMMENDED: Lean=" . $r['lean'] . ", Buy=" . $r['buy'] . ", Strong=" . $r['strong'] . "\n";
    }
}

function display_inversion($data) {
    echo "🔄 SIGNAL INVERSION ANALYSIS\n";
    echo "─────────────────────────────────────────────────────────────\n\n";
    
    if (isset($data['inversion_tests'])) {
        foreach ($data['inversion_tests'] as $test_name => $result) {
            echo strtoupper(str_replace('_', ' ', $test_name)) . ":\n";
            
            if (isset($result['inverted_win_rate'])) {
                echo "  Inverted Win Rate: " . $result['inverted_win_rate'] . "%\n";
                echo "  Edge vs Original: " . $result['edge_vs_original'] . "%\n";
                echo "  Viable Strategy: " . ($result['viable_strategy'] ? 'YES ✅' : 'No') . "\n";
            } else {
                echo "  Count: " . $result['count'] . "\n";
                echo "  Win Rate: " . $result['win_rate'] . "%\n";
                echo "  Avg Return: " . $result['avg_return'] . "%\n";
            }
            echo "\n";
        }
    }
    
    if (isset($data['evidence_for_inversion'])) {
        $ev = $data['evidence_for_inversion'];
        echo "EVIDENCE SCORE: " . $ev['score'] . "/" . $ev['max_score'] . "\n";
        echo "VERDICT: " . $ev['verdict'] . "\n";
    }
}

function display_exhaustion($data) {
    echo "⚡ MOMENTUM EXHAUSTION ANALYSIS\n";
    echo "─────────────────────────────────────────────────────────────\n\n";
    
    if (isset($data['range_analysis'])) {
        echo "Performance by score range:\n\n";
        
        foreach ($data['range_analysis'] as $range => $info) {
            echo $range . ":\n";
            
            if (isset($info['note'])) {
                echo "  " . $info['note'] . "\n";
            } else {
                echo "  Count: " . $info['count'] . " | Win Rate: " . $info['win_rate'] . "%\n";
                echo "  Avg Return: " . $info['avg_return_pct'] . "%\n";
                if ($info['avg_time_to_peak_hours'] !== null) {
                    echo "  Avg Time to Peak: " . $info['avg_time_to_peak_hours'] . " hours\n";
                }
                if (isset($info['exhaustion_indicator'])) {
                    $ex = $info['exhaustion_indicator'];
                    echo "  Exhaustion Level: " . $ex['level'] . "\n";
                }
            }
            echo "\n";
        }
    }
    
    if (isset($data['score_vs_time_to_peak_correlation'])) {
        echo "Correlation Analysis:\n";
        echo "  Score vs Time-to-Peak r: " . $data['score_vs_time_to_peak_correlation']['r'] . "\n";
        echo "  Interpretation: " . $data['score_vs_time_to_peak_correlation']['interpretation'] . "\n";
    }
}
?>
