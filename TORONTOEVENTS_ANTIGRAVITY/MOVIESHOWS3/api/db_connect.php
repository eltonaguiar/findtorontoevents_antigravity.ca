<?php
// Database connection for MovieShows3
// Using FavCreators database for shared user authentication

$host = 'localhost';
$dbname = 'ejaguiar1_favcreators';
$username = 'ejaguiar1_favcreators';
$password = '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl';

$conn = new mysqli($host, $username, $password, $dbname);

if ($conn->connect_error) {
    header('HTTP/1.0 500 Internal Server Error');
    die(json_encode(array('error' => 'Database connection failed')));
}

$conn->set_charset('utf8mb4');
?>