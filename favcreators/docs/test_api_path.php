<?php
header('Content-Type: application/json');
echo json_encode(array('message' => 'API path test works', 'path' => __FILE__));