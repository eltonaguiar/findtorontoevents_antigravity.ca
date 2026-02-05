<?php
header('Content-Type: application/json');
echo json_encode(array('test' => 'works', 'time' => date('Y-m-d H:i:s')));