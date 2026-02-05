<?php
// Minimal test - no database, no includes
header('Content-Type: application/json');
echo json_encode(array('test' => 'success', 'php_version' => phpversion()));
?>