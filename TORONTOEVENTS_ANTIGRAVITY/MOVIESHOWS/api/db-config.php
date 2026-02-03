<?php
/**
 * Database Configuration for MovieShows
 * Database: ejaguiar1_tvmoviestrailers
 */

// Database credentials
define('DB_HOST', 'localhost'); // Update if different
define('DB_NAME', 'ejaguiar1_tvmoviestrailers');
define('DB_USER', 'ejaguiar1_tvmoviestrailers');
define('DB_PASS', 'virus2016');
define('DB_CHARSET', 'utf8mb4');

// CORS headers for API access
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');
header('Content-Type: application/json; charset=utf-8');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit();
}

// Polyfill for http_response_code (PHP 5.4+)
if (!function_exists('http_response_code')) {
    function http_response_code($code = NULL)
    {
        static $current_code = 200;

        if ($code !== NULL) {
            switch ($code) {
                case 200:
                    $text = 'OK';
                    break;
                case 201:
                    $text = 'Created';
                    break;
                case 400:
                    $text = 'Bad Request';
                    break;
                case 404:
                    $text = 'Not Found';
                    break;
                case 500:
                    $text = 'Internal Server Error';
                    break;
                default:
                    $text = 'Unknown';
                    break;
            }
            header("HTTP/1.1 $code $text");
            $current_code = $code;
        }

        return $current_code;
    }
}

/**
 * Get database connection
 * @return PDO|null
 */
function getDbConnection()
{
    static $pdo = null;

    if ($pdo === null) {
        try {
            $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET;
            $options = array(
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
                PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
            );

            $pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
        } catch (PDOException $e) {
            error_log("Database connection failed: " . $e->getMessage());
            return null;
        }
    }

    return $pdo;
}

/**
 * Send JSON response
 */
function sendJson($data, $statusCode = 200)
{
    http_response_code($statusCode);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit();
}

/**
 * Send error response
 */
function sendError($message, $statusCode = 500, $details = null)
{
    $response = array('error' => $message);
    if ($details !== null) {
        $response['details'] = $details;
    }
    sendJson($response, $statusCode);
}

/**
 * Get request body as JSON
 */
function getRequestBody()
{
    $body = file_get_contents('php://input');
    return json_decode($body, true);
}
