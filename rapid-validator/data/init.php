<?php
/**
 * Initialize RSVE Data Files
 * Run this once to set up the data structure
 */

header('Content-Type: application/json');

$data_dir = __DIR__ . '/';

$files = array(
    'active_signals.json' => array('signals' => array()),
    'signal_outcomes.json' => array('outcomes' => array()),
    'evaluation_state.json' => array(),
    'elimination_log.json' => array(),
    'promotion_log.json' => array(),
    'generation_log.txt' => ''
);

try {
    foreach ($files as $filename => $default_content) {
        $filepath = $data_dir . $filename;
        
        if (!file_exists($filepath)) {
            if (is_array($default_content)) {
                file_put_contents($filepath, json_encode($default_content, JSON_PRETTY_PRINT));
            } else {
                file_put_contents($filepath, $default_content);
            }
            echo "Created: $filename\n";
        }
    }
    
    echo json_encode(array(
        'ok' => true,
        'message' => 'RSVE data files initialized successfully',
        'files_created' => count($files)
    ));
    
} catch (Exception $e) {
    echo json_encode(array(
        'ok' => false,
        'error' => $e->getMessage()
    ));
}
