&lt;?php
/**
 * Setup audit_trails table for pick audit logging
 */

require_once dirname(__FILE__) . '/db_connect.php';

$sql = "
    CREATE TABLE IF NOT EXISTS audit_trails (
        id INT AUTO_INCREMENT PRIMARY KEY,
        asset_class VARCHAR(50) NOT NULL,
        symbol VARCHAR(50) NOT NULL,
        pick_timestamp DATETIME NOT NULL,
        generation_source VARCHAR(100) NOT NULL,
        reasons TEXT,
        supporting_data TEXT,
        pick_details TEXT,
        formatted_for_ai TEXT,
        KEY idx_pick (asset_class, symbol, pick_timestamp)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8
";

if ($conn-&gt;query($sql) === TRUE) {
    echo json_encode(array(
        'success' =&gt; true,
        'message' =&gt; 'audit_trails table created successfully'
    ));
} else {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array(
        'success' =&gt; false,
        'error' =&gt; $conn-&gt;error
    ));
}

$conn-&gt;close();
?&gt;