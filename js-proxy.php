<?php
// Proxy to serve JavaScript files and bypass ModSecurity
$requestUri = $_SERVER['REQUEST_URI'];
$path = parse_url($requestUri, PHP_URL_PATH);

// Extract filename from path like /js-proxy.php?file=a2ac3a6616d60872.js
$file = $_GET['file'] ?? basename($path);

// Remove query parameters from filename
$file = preg_replace('/\?.*$/', '', $file);

// Map to actual file location
$filePath = __DIR__ . '/_next/static/chunks/' . basename($file);

if (file_exists($filePath) && pathinfo($filePath, PATHINFO_EXTENSION) === 'js') {
    header('Content-Type: application/javascript');
    header('Cache-Control: public, max-age=31536000');
    readfile($filePath);
    exit;
}

http_response_code(404);
?>
