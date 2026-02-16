<?php
/**
 * Rapid Validation Signal Engine API
 * CLAUDECODE_Feb152026
 *
 * Executes Python validation scripts on the server (bypasses GitHub Actions DB connection issues)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$action = isset($_GET['action']) ? $_GET['action'] : 'status';
$key = isset($_GET['key']) ? $_GET['key'] : '';

// Simple authentication
if ($action !== 'status' && $key !== 'livetrader2026') {
    http_response_code(401);
    echo json_encode(['ok' => false, 'error' => 'Unauthorized']);
    exit;
}

$base_path = dirname(__DIR__);
$python = '/usr/bin/python3'; // Adjust if needed

switch ($action) {
    case 'validate':
        // Run fast validator
        $cmd = "cd " . escapeshellarg($base_path) . " && $python fast_validator_CLAUDECODE_Feb152026.py 2>&1";
        $output = [];
        $return_var = 0;
        exec($cmd, $output, $return_var);

        echo json_encode([
            'ok' => $return_var === 0,
            'action' => 'validate',
            'output' => implode("\n", $output),
            'exit_code' => $return_var,
            'timestamp' => date('Y-m-d H:i:s')
        ]);
        break;

    case 'rank':
        // Run strategy ranker
        $cmd = "cd " . escapeshellarg($base_path) . " && $python strategy_ranker_CLAUDECODE_Feb152026.py 2>&1";
        $output = [];
        $return_var = 0;
        exec($cmd, $output, $return_var);

        echo json_encode([
            'ok' => $return_var === 0,
            'action' => 'rank',
            'output' => implode("\n", $output),
            'exit_code' => $return_var,
            'timestamp' => date('Y-m-d H:i:s')
        ]);
        break;

    case 'cycle':
        // Run full validation + ranking cycle
        $results = [];

        // 1. Validate signals
        $cmd1 = "cd " . escapeshellarg($base_path) . " && $python fast_validator_CLAUDECODE_Feb152026.py 2>&1";
        exec($cmd1, $output1, $ret1);
        $results['validate'] = [
            'ok' => $ret1 === 0,
            'output' => implode("\n", $output1),
            'exit_code' => $ret1
        ];

        // 2. Rank strategies
        $cmd2 = "cd " . escapeshellarg($base_path) . " && $python strategy_ranker_CLAUDECODE_Feb152026.py 2>&1";
        exec($cmd2, $output2, $ret2);
        $results['rank'] = [
            'ok' => $ret2 === 0,
            'output' => implode("\n", $output2),
            'exit_code' => $ret2
        ];

        // 3. Check if rankings file exists
        $rankings_file = $base_path . '/rankings_CLAUDECODE_Feb152026.json';
        $rankings = null;
        if (file_exists($rankings_file)) {
            $rankings = json_decode(file_get_contents($rankings_file), true);
        }

        echo json_encode([
            'ok' => $ret1 === 0 && $ret2 === 0,
            'action' => 'cycle',
            'results' => $results,
            'rankings' => $rankings ? [
                'promoted' => count(isset($rankings['promoted']) ? $rankings['promoted'] : []),
                'testing' => count(isset($rankings['testing']) ? $rankings['testing'] : []),
                'eliminated' => count(isset($rankings['eliminated']) ? $rankings['eliminated'] : [])
            ] : null,
            'timestamp' => date('Y-m-d H:i:s')
        ]);
        break;

    case 'status':
        // Check status of rapid validation system
        $rankings_file = $base_path . '/rankings_CLAUDECODE_Feb152026.json';
        $rankings_exists = file_exists($rankings_file);
        $rankings = null;
        $last_updated = null;

        if ($rankings_exists) {
            $rankings = json_decode(file_get_contents($rankings_file), true);
            $last_updated = filemtime($rankings_file);
        }

        echo json_encode([
            'ok' => true,
            'action' => 'status',
            'initialized' => $rankings_exists,
            'last_updated' => $last_updated ? date('Y-m-d H:i:s', $last_updated) : null,
            'rankings' => $rankings ? [
                'promoted' => count(isset($rankings['promoted']) ? $rankings['promoted'] : []),
                'testing' => count(isset($rankings['testing']) ? $rankings['testing'] : []),
                'eliminated' => count(isset($rankings['eliminated']) ? $rankings['eliminated'] : []),
                'timestamp' => isset($rankings['timestamp']) ? $rankings['timestamp'] : null
            ] : null
        ]);
        break;

    default:
        echo json_encode([
            'ok' => false,
            'error' => 'Unknown action',
            'valid_actions' => ['status', 'validate', 'rank', 'cycle']
        ]);
        break;
}
