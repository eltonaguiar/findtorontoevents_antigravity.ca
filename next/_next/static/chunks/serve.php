<?php
// Serve JS files and bypass ModSecurity query param blocking
$requestUri = $_SERVER['REQUEST_URI'];
$file = basename(parse_url($requestUri, PHP_URL_PATH));

// Remove query parameters from filename
$file = preg_replace('/\?.*$/', '', $file);

$filePath = __DIR__ . '/' . $file;

if (file_exists($filePath) && pathinfo($filePath, PATHINFO_EXTENSION) === 'js') {
    header('Content-Type: application/javascript');
    header('Cache-Control: public, max-age=31536000');
    readfile($filePath);
    exit;
}

http_response_code(404);
?>
