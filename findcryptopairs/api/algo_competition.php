<?php
// Simple stub to provide pump-watch-live data for demo purposes.
// PHP 5.2 FIX (2026-11-23): this file used __DIR__ (PHP 5.3+) and short array
// literals (PHP 5.4+), so the live PHP 5.2.17 host failed at PARSE time with
//   Parse error: syntax error, unexpected '[', expecting ')' on line 6
// and every request to the endpoint returned HTML instead of JSON.
header('Content-Type: application/json');
$demo = file_get_contents(dirname(__FILE__) . '/pump_watch_demo.json');
if ($demo === false) {
    echo json_encode(array('by_algo' => array('pump-watch-live' => array())));
} else {
    echo $demo;
}
?>