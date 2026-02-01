<?php
// Proxy to serve JavaScript files and bypass ModSecurity
// V2 - Fixed syntax for older PHP versions and checks both chunk locations
// Prevent any PHP notice/warning from being sent before the JS (would cause "Unexpected token" in browser)
error_reporting(0);
ini_set('display_errors', '0');
if (function_exists('ob_start')) { ob_start(); }
$requestUri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '';
$path = parse_url($requestUri, PHP_URL_PATH);

// Extract filename from path like /js-proxy-v2.php?file=next/_next/static/chunks/a2ac3a6616d60872.js
$file = isset($_GET['file']) ? $_GET['file'] : basename($path);

// Remove query parameters from filename
$file = preg_replace('/\?.*$/', '', $file);

// Security: use only basename to prevent path traversal
$filename = basename($file);

// Map to actual file location - check all possible locations (order matters)
// First try next/_next/static/chunks/ (matches how index.html references them)
$filePath1 = __DIR__ . '/next/_next/static/chunks/' . $filename;
// Fallback to _next/static/chunks/
$filePath2 = __DIR__ . '/_next/static/chunks/' . $filename;
// Fallback using DOCUMENT_ROOT in case __DIR__ differs from web root
$docRoot = isset($_SERVER['DOCUMENT_ROOT']) ? rtrim($_SERVER['DOCUMENT_ROOT'], '/') : __DIR__;
$filePath3 = $docRoot . '/next/_next/static/chunks/' . $filename;
$filePath4 = $docRoot . '/_next/static/chunks/' . $filename;

// Try each location (extension check case-insensitive)
$filePath = null;
foreach (array($filePath1, $filePath2, $filePath3, $filePath4) as $p) {
    if (file_exists($p) && strtolower(pathinfo($p, PATHINFO_EXTENSION)) === 'js') {
        $filePath = $p;
        break;
    }
}

if ($filePath) {
    if (function_exists('ob_end_clean')) { @ob_end_clean(); }
    header('Content-Type: application/javascript; charset=utf-8');
    header('Cache-Control: public, max-age=31536000');
    readfile($filePath);
    exit;
}

// File not found - return plain text 404 to avoid HTML being parsed as JS (PHP 5.3 compatible)
if (function_exists('ob_end_clean')) { @ob_end_clean(); }
if (function_exists('http_response_code')) {
    http_response_code(404);
} else {
    header('HTTP/1.0 404 Not Found');
}
header('Content-Type: text/plain; charset=utf-8');
echo 'JavaScript file not found';
