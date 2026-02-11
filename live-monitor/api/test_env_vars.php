<?php
/**
 * Test script to verify API keys are configured correctly
 * Checks db_config.php and environment variables
 */

header('Content-Type: application/json');

// Load the config to check what's defined
require_once dirname(__FILE__) . '/db_config.php';

$fmp_key = isset($FMP_API_KEY) ? $FMP_API_KEY : '';
$massive_key = isset($MASSIVE_API_KEY) ? $MASSIVE_API_KEY : (isset($POLYGON_API_KEY) ? $POLYGON_API_KEY : '');

// Also check environment variables
$fmp_env = getenv('FMP_API_KEY');
$massive_env = getenv('MASSIVE_API_KEY');
$polygon_env = getenv('POLYGON_API_KEY');

$result = array(
    'ok' => true,
    'timestamp' => date('Y-m-d H:i:s'),
    'config_file' => 'db_config.php',
    'keys_from_config' => array(
        'FMP_API_KEY' => ($fmp_key && $fmp_key !== 'YOUR_FMP_KEY_HERE') ? 'SET (length: ' . strlen($fmp_key) . ')' : 'NOT CONFIGURED',
        'MASSIVE_API_KEY' => ($massive_key && $massive_key !== 'YOUR_MASSIVE_KEY_HERE' && $massive_key !== 'YOUR_POLYGON_KEY_HERE') ? 'SET (length: ' . strlen($massive_key) . ')' : 'NOT CONFIGURED',
        'POLYGON_API_KEY (fallback)' => isset($POLYGON_API_KEY) ? 'SET' : 'NOT SET'
    ),
    'keys_from_env' => array(
        'FMP_API_KEY' => $fmp_env ? 'SET' : 'NOT SET',
        'MASSIVE_API_KEY' => $massive_env ? 'SET' : 'NOT SET',
        'POLYGON_API_KEY' => $polygon_env ? 'SET' : 'NOT SET'
    ),
    'active_keys' => array()
);

// Determine which keys are actually being used
$active_fmp = ($fmp_key && $fmp_key !== 'YOUR_FMP_KEY_HERE') ? $fmp_key : $fmp_env;
$active_massive = ($massive_key && $massive_key !== 'YOUR_MASSIVE_KEY_HERE' && $massive_key !== 'YOUR_POLYGON_KEY_HERE') ? $massive_key : ($massive_env ? $massive_env : $polygon_env);

if ($active_fmp && strlen($active_fmp) > 10) {
    $result['active_keys'][] = 'FMP_API_KEY (first 4: ' . substr($active_fmp, 0, 4) . '***)';
}

if ($active_massive && strlen($active_massive) > 10) {
    $result['active_keys'][] = 'MASSIVE_API_KEY (first 4: ' . substr($active_massive, 0, 4) . '***)';
}

// Test FMP API if key is available
if ($active_fmp && strlen($active_fmp) > 10) {
    $test_url = "https://financialmodelingprep.com/api/v3/quote-short/AAPL?apikey=" . urlencode($active_fmp);
    $resp = @file_get_contents($test_url);
    if ($resp) {
        $data = json_decode($resp, true);
        $result['fmp_api_test'] = (is_array($data) && count($data) > 0) ? 'SUCCESS' : 'FAILED';
    } else {
        $result['fmp_api_test'] = 'FAILED - Check API key validity';
    }
} else {
    $result['fmp_api_test'] = 'SKIPPED - No API key configured';
}

// Test Massive API if key is available
if ($active_massive && strlen($active_massive) > 10) {
    $test_url = "https://api.polygon.io/v1/marketstatus/now?apiKey=" . urlencode($active_massive);
    $resp = @file_get_contents($test_url);
    if ($resp) {
        $data = json_decode($resp, true);
        $result['massive_api_test'] = (isset($data['market']) || isset($data['status'])) ? 'SUCCESS' : 'FAILED';
    } else {
        $result['massive_api_test'] = 'FAILED - Check API key validity';
    }
} else {
    $result['massive_api_test'] = 'SKIPPED - No API key configured';
}

echo json_encode($result, JSON_PRETTY_PRINT);
?>
