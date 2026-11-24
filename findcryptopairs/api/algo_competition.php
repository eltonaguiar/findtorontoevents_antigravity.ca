<?php
// Simple stub to provide pump-watch-live data for demo purposes
header('Content-Type: application/json');
$demo = file_get_contents(__DIR__ . '/pump_watch_demo.json');
if ($demo === false) {
    echo json_encode(['by_algo' => ['pump-watch-live' => []]]);
} else {
    echo $demo;
}
?>