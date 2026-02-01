<?php
// JavaScript file proxy - Fixed to check both chunk locations
// CACHE BUST: 2026-01-31-23-45-00 - Force PHP opcode cache reload
// This file serves JavaScript chunks and bypasses ModSecurity

// Get the requested file from query parameter or URI path
$requestUri = $_SERVER['REQUEST_URI'];
$path = parse_url($requestUri, PHP_URL_PATH);

// Extract filename - compatible with older PHP versions
if (isset($_GET['file']) && !empty($_GET['file'])) {
    $file = $_GET['file'];
} else {
    $file = basename($path);
}

// Clean up filename - remove query parameters
$file = preg_replace('/\?.*$/', '', $file);

// Security: only allow .js files, use basename to prevent path traversal
$filename = basename($file);

// Map to actual file location - check both possible locations
// First try next/_next/static/chunks/ (matches how index.html references them)
$filePath1 = __DIR__ . '/next/_next/static/chunks/' . $filename;
// Fallback to _next/static/chunks/
$filePath2 = __DIR__ . '/_next/static/chunks/' . $filename;

// Try first location, then fallback
$filePath = null;
if (file_exists($filePath1) && pathinfo($filePath1, PATHINFO_EXTENSION) === 'js') {
    $filePath = $filePath1;
} elseif (file_exists($filePath2) && pathinfo($filePath2, PATHINFO_EXTENSION) === 'js') {
    $filePath = $filePath2;
}

if ($filePath) {
    // Set proper headers
    header('Content-Type: application/javascript; charset=utf-8');
    header('Cache-Control: public, max-age=31536000');
    header('Access-Control-Allow-Origin: *');
    
    // Output the file
    readfile($filePath);
    exit;
}

// File not found - return plain text 404 to avoid HTML being parsed as JS
http_response_code(404);
header('Content-Type: text/plain; charset=utf-8');
echo 'JavaScript file not found';
?>
