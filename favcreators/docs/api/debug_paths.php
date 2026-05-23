<?php
// Debug: find where data files are located
header('Content-Type: application/json');
$paths = array(
    '__FILE__' => __FILE__,
    'dirname(__FILE__)' => dirname(__FILE__),
    'DOCUMENT_ROOT' => $_SERVER['DOCUMENT_ROOT'],
    'SERVER_NAME' => $_SERVER['SERVER_NAME'],
);
$candidates = array(
    dirname(__FILE__) . '/../../..',
    dirname(__FILE__) . '/../../../..',
    '/home/www/findtorontoevents.ca',
    $_SERVER['DOCUMENT_ROOT'],
    $_SERVER['DOCUMENT_ROOT'] . '/findtorontoevents.ca',
);
$checks = array();
foreach ($candidates as $base) {
    $real = @realpath($base);
    $checks[$base] = array(
        'real' => $real ? $real : 'N/A',
        'updates_data' => file_exists($base . '/updates/data') ? 'yes' : 'no',
        'antigravity_live' => file_exists($base . '/updates/data/antigravity_ml_live_picks.json') ? 'yes' : 'no',
        'claude_ml' => file_exists($base . '/updates/data/claude_ml_picks.json') ? 'yes' : 'no',
        'tracker' => file_exists($base . '/claude_gainer_ml/tracker') ? 'yes' : 'no',
    );
}
echo json_encode(array('paths' => $paths, 'candidates' => $checks));
