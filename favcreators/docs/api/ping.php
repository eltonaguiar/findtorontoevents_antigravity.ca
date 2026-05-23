<?php
header('Content-Type: application/json');
echo json_encode(array('ok' => true, 'time' => date('Y-m-d H:i:s'), 'php_version' => phpversion()));
?>
