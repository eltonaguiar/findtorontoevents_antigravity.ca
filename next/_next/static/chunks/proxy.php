<?php
// Proxy script to serve JavaScript files and bypass ModSecurity
$file = isset($_GET['file']) ? $_GET['file'] : '';
if (empty($file)) {
    http_response_code(404);
    exit;
}

$basePath = __DIR__;
$filePath = realpath($basePath . '/' . basename($file));

// Security check - ensure file is in the chunks directory
if (!$filePath || strpos($filePath, realpath($basePath)) !== 0) {
    http_response_code(403);
    exit;
}

if (!file_exists($filePath)) {
    http_response_code(404);
    exit;
}

header('Content-Type: application/javascript');
header('Cache-Control: public, max-age=31536000');
readfile($filePath);
?>
