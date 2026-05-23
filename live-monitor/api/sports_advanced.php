<?php
/**
 * Static capability map for scripts and guardrails (no DB required).
 * PHP 5.2 compatible.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$action = isset($_GET['action']) ? $_GET['action'] : 'capabilities';

if ($action === 'capabilities') {
    echo json_encode(array(
        'ok' => true,
        'action' => 'capabilities',
        'repo_scripts' => array(
            'portfolio_correlation' => 'scripts/sports_portfolio_corr.py',
            'monte_carlo_paper' => 'scripts/sports_monte_carlo.py',
            'walk_forward_stub' => 'scripts/sports_walkforward_stub.py',
            'api_schema_ci' => 'tools/validate_sports_api_schema.py',
        ),
        'api_endpoints' => array(
            'forensics_segments_ci' => 'sports_forensics.php?action=segments&include_ci=1',
            'forensics_pre_game' => 'sports_forensics.php?action=pre_game_status',
            'daily_returns' => 'sports_forensics.php?action=daily_returns',
        ),
        'generated_at' => date('c'),
    ));
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'unknown action'));
