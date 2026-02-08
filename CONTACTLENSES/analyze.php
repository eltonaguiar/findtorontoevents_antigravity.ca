<?php
/**
 * Contact Lens Orientation Analyzer - PHP Backend
 * 
 * Handles image uploads and calls the Python/OpenCV analyzer.
 * Returns JSON response for AJAX calls from the frontend.
 * 
 * Endpoint: POST /CONTACTLENSES/analyze.php
 * Expects: multipart/form-data with 'lens_image' file
 * Returns: JSON with status, message, confidence
 * 
 * Note: Uses PHP 5.3 compatible syntax for shared hosting
 */

// Suppress PHP errors from appearing in output - we'll return JSON instead
error_reporting(0);
ini_set('display_errors', 0);

// Always return JSON
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Helper: Check if shell_exec is available
function is_shell_exec_available() {
    if (!function_exists('shell_exec')) {
        return false;
    }
    $disabled = ini_get('disable_functions');
    if (!empty($disabled)) {
        $disabled_array = array_map('trim', explode(',', $disabled));
        if (in_array('shell_exec', $disabled_array)) {
            return false;
        }
    }
    return true;
}

// Status check endpoint - GET request returns server capabilities
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $shell_available = is_shell_exec_available();
    $python_available = false;
    $opencv_available = false;
    
    // Check if Python is available
    if ($shell_available) {
        $python_check = @shell_exec('python3 --version 2>&1');
        if (empty($python_check)) {
            $python_check = @shell_exec('python --version 2>&1');
        }
        $python_available = !empty($python_check) && stripos($python_check, 'python') !== false;
        
        // Check for OpenCV
        if ($python_available) {
            $cv_check = @shell_exec('python3 -c "import cv2; print(cv2.__version__)" 2>&1');
            $opencv_available = !empty($cv_check) && stripos($cv_check, 'error') === false && stripos($cv_check, 'No module') === false;
        }
    }
    
    $server_available = $shell_available && $python_available && $opencv_available;
    
    $capabilities = array(
        'status' => 'ok',
        'shell_exec' => $shell_available,
        'python' => $python_available,
        'opencv' => $opencv_available,
        'server_analysis_available' => $server_available
    );
    
    if (!$server_available) {
        $capabilities['message'] = 'Server-side analysis not available on this hosting. The client-side analysis is still fully functional.';
        if (!$shell_available) {
            $capabilities['reason'] = 'shell_exec disabled';
        } elseif (!$python_available) {
            $capabilities['reason'] = 'Python not installed';
        } else {
            $capabilities['reason'] = 'OpenCV not installed';
        }
    }
    
    echo json_encode($capabilities);
    exit;
}

// Handle preflight
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Only accept POST for analysis
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(array(
        'status' => 'error',
        'message' => 'Method not allowed. Use POST for analysis or GET to check capabilities.'
    ));
    exit;
}

// Check if shell_exec is available before proceeding
if (!is_shell_exec_available()) {
    echo json_encode(array(
        'status' => 'error',
        'message' => 'Server-side analysis not available. shell_exec is disabled on this hosting.',
        'fallback' => 'js',
        'tip' => 'The client-side Quick Scan analysis is still accurate for most cases.'
    ));
    exit;
}

// Check for file upload
if (!isset($_FILES['lens_image']) || $_FILES['lens_image']['error'] !== UPLOAD_ERR_OK) {
    $error_messages = array(
        UPLOAD_ERR_INI_SIZE => 'File too large (server limit)',
        UPLOAD_ERR_FORM_SIZE => 'File too large (form limit)',
        UPLOAD_ERR_PARTIAL => 'File only partially uploaded',
        UPLOAD_ERR_NO_FILE => 'No file was uploaded',
        UPLOAD_ERR_NO_TMP_DIR => 'Server missing temp folder',
        UPLOAD_ERR_CANT_WRITE => 'Failed to write file to disk',
        UPLOAD_ERR_EXTENSION => 'Upload blocked by extension'
    );
    
    $error_code = isset($_FILES['lens_image']['error']) ? $_FILES['lens_image']['error'] : UPLOAD_ERR_NO_FILE;
    $error_msg = isset($error_messages[$error_code]) ? $error_messages[$error_code] : 'Unknown upload error';
    
    http_response_code(400);
    echo json_encode(array(
        'status' => 'error',
        'message' => $error_msg
    ));
    exit;
}

// Validate file type
$allowed_types = array('image/jpeg', 'image/png', 'image/webp', 'image/gif');
$finfo = finfo_open(FILEINFO_MIME_TYPE);
$mime_type = finfo_file($finfo, $_FILES['lens_image']['tmp_name']);
finfo_close($finfo);

if (!in_array($mime_type, $allowed_types)) {
    http_response_code(400);
    echo json_encode(array(
        'status' => 'error',
        'message' => 'Invalid file type. Please upload a JPG, PNG, or WebP image.'
    ));
    exit;
}

// Create uploads directory if needed
$upload_dir = dirname(__FILE__) . '/uploads';
if (!is_dir($upload_dir)) {
    if (!mkdir($upload_dir, 0755, true)) {
        http_response_code(500);
        echo json_encode(array(
            'status' => 'error',
            'message' => 'Server error: Could not create upload directory'
        ));
        exit;
    }
}

// Generate unique filename
$ext = pathinfo($_FILES['lens_image']['name'], PATHINFO_EXTENSION);
if (empty($ext)) {
    $ext = 'jpg';
}
$filename = 'lens_' . time() . '_' . substr(md5(mt_rand()), 0, 8) . '.' . $ext;
$filepath = $upload_dir . '/' . $filename;

// Move uploaded file
if (!move_uploaded_file($_FILES['lens_image']['tmp_name'], $filepath)) {
    http_response_code(500);
    echo json_encode(array(
        'status' => 'error',
        'message' => 'Server error: Could not save uploaded file'
    ));
    exit;
}

// Find Python interpreter
$python_paths = array(
    '/usr/bin/python3',
    '/usr/local/bin/python3',
    '/usr/bin/python',
    'python3',
    'python'
);

$python_cmd = null;
foreach ($python_paths as $path) {
    // Check if command exists
    $check = @shell_exec("which $path 2>/dev/null");
    if (empty($check)) {
        $check = @shell_exec("where $path 2>NUL");
    }
    if (!empty($check)) {
        $python_cmd = trim($check);
        break;
    }
}

// Fallback: try python3 directly
if (empty($python_cmd)) {
    $python_cmd = 'python3';
}

// Path to analyzer script
$script_path = dirname(__FILE__) . '/analyze_lens.py';

if (!file_exists($script_path)) {
    // Clean up uploaded file
    @unlink($filepath);
    
    http_response_code(500);
    echo json_encode(array(
        'status' => 'error',
        'message' => 'Server error: Analyzer script not found'
    ));
    exit;
}

// Execute Python script
$command = escapeshellcmd($python_cmd) . ' ' . 
           escapeshellarg($script_path) . ' ' . 
           escapeshellarg($filepath) . ' 2>&1';

$output = @shell_exec($command);

// Clean up uploaded file (privacy - don't store user photos)
@unlink($filepath);

// Parse output
if ($output === null || $output === false) {
    http_response_code(500);
    echo json_encode(array(
        'status' => 'error',
        'message' => 'Server error: Could not execute analyzer. shell_exec may be disabled.',
        'fallback' => 'js'
    ));
    exit;
}

// Try to decode JSON response
$result = json_decode($output, true);

if (json_last_error() !== JSON_ERROR_NONE) {
    // Python script had an error
    http_response_code(500);
    echo json_encode(array(
        'status' => 'error',
        'message' => 'Analyzer returned invalid response',
        'raw_output' => substr($output, 0, 500),
        'fallback' => 'js'
    ));
    exit;
}

// Return result
echo json_encode($result);
