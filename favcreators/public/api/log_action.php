<?php
/**
 * Centralized logging function for favcreatorslogs table
 * Include this file and call log_action() to write logs
 * 
 * Usage:
 *   require_once 'log_action.php';
 *   log_action('user_login', 'login.php', $user_id, $email, 'success', 'Login successful');
 */

/**
 * Log an action to the favcreatorslogs table
 * 
 * @param string $action The action being performed (e.g., 'user_login', 'save_creators')
 * @param string $endpoint The PHP file/endpoint where the action occurred
 * @param int|null $user_id The user ID (if applicable)
 * @param string|null $user_email The user's email (if applicable)
 * @param string $status 'success', 'error', 'warning', 'info'
 * @param string $message Human-readable message about what happened
 * @param string $payload_summary Summary of input data (be careful with sensitive data)
 * @param string $error_details Error details if status is 'error'
 * @return bool True if log was written successfully
 */
function log_action($action, $endpoint, $user_id = null, $user_email = null, 
                    $status = 'success', $message = '', $payload_summary = '', 
                    $error_details = '') {
    
    // Silently fail if db_connect doesn't exist (for backwards compatibility)
    $db_connect_path = dirname(__FILE__) . '/db_connect.php';
    if (!file_exists($db_connect_path)) {
        error_log("log_action: db_connect.php not found");
        return false;
    }
    
    require_once $db_connect_path;
    
    // Check connection
    if (!isset($conn) || !$conn) {
        error_log("log_action: Database connection not available");
        return false;
    }
    
    // Get client IP safely
    $user_ip = 'unknown';
    if (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
        $ips = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR']);
        $user_ip = trim($ips[0]);
    } elseif (!empty($_SERVER['REMOTE_ADDR'])) {
        $user_ip = $_SERVER['REMOTE_ADDR'];
    }
    
    // Ensure table exists
    $create_table_sql = "CREATE TABLE IF NOT EXISTS favcreatorslogs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action VARCHAR(64) NOT NULL,
        endpoint VARCHAR(128),
        user_id INT,
        user_email VARCHAR(255),
        user_ip VARCHAR(45),
        status VARCHAR(16) NOT NULL,
        message TEXT,
        payload_summary TEXT,
        error_details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user_email (user_email),
        INDEX idx_action (action),
        INDEX idx_created_at (created_at),
        INDEX idx_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
    
    $conn->query($create_table_sql);
    
    // Prepare and execute INSERT
    $stmt = $conn->prepare("INSERT INTO favcreatorslogs 
        (action, endpoint, user_id, user_email, user_ip, status, message, payload_summary, error_details) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)");
    
    if (!$stmt) {
        error_log("log_action: Prepare failed: " . $conn->error);
        return false;
    }
    
    $stmt->bind_param("ssissssss", 
        $action, $endpoint, $user_id, $user_email, 
        $user_ip, $status, $message, $payload_summary, $error_details
    );
    
    $result = $stmt->execute();
    
    if (!$result) {
        error_log("log_action: Execute failed: " . $stmt->error);
    }
    
    $stmt->close();
    $conn->close();
    
    return $result;
}

/**
 * Convenience function for logging errors
 */
function log_error($action, $endpoint, $error_message, $error_details = '', $user_id = null, $user_email = null) {
    return log_action($action, $endpoint, $user_id, $user_email, 'error', $error_message, '', $error_details);
}

/**
 * Convenience function for logging successful actions
 */
function log_success($action, $endpoint, $message, $payload_summary = '', $user_id = null, $user_email = null) {
    return log_action($action, $endpoint, $user_id, $user_email, 'success', $message, $payload_summary);
}

/**
 * Convenience function for logging warnings
 */
function log_warning($action, $endpoint, $message, $payload_summary = '', $user_id = null, $user_email = null) {
    return log_action($action, $endpoint, $user_id, $user_email, 'warning', $message, $payload_summary);
}
?>
