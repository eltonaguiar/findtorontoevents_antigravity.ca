<?php
// Temporary diagnostic — remove after debugging
header('Content-Type: text/plain');
header('Access-Control-Allow-Origin: *');

$host = 'localhost';
$serverHost = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : 'unknown';
echo "Server: $serverHost\n";

// Try credential combos for ejaguiar1_tvmoviestrailers
$configs = array(
    array('ejaguiar1_tvmoviestrailers', 'admin', '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl'),
    array('ejaguiar1_tvmoviestrailers', 'ejaguiar1_tvmoviestrailers', 'tvmoviestrailers'),
    array('ejaguiar1_tvmoviestrailers', 'ejaguiar1_tvmoviestrailers', '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl'),
);

foreach ($configs as $i => $cfg) {
    list($db, $user, $pass) = $cfg;
    echo "\nAttempt " . ($i+1) . ": db=$db, user=$user\n";
    try {
        $pdo = new PDO("mysql:host=$host;dbname=$db;charset=utf8mb4", $user, $pass);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $stmt = $pdo->query("SELECT COUNT(*) as cnt FROM movies");
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        echo "  OK! Movies: " . $row['cnt'] . "\n";
    } catch (PDOException $e) {
        echo "  FAIL: " . $e->getMessage() . "\n";
    }
}
?>
