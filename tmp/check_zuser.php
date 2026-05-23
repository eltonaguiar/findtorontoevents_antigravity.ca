<?php
$conn = new PDO('mysql:host=localhost;dbname=ejaguiar1_favcreators;charset=utf8mb4',
    'ejaguiar1_favcreators', '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl');
$conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$u = $conn->prepare("SELECT id, email FROM users WHERE email='zerounderscore@gmail.com'");
$u->execute();
$user = $u->fetch(PDO::FETCH_ASSOC);
$uid = $user ? $user['id'] : null;

$count = 0; $creators = null; $notes = array();
if ($uid) {
    $q = $conn->prepare("SELECT creators FROM user_lists WHERE user_id=?");
    $q->execute(array($uid));
    $row = $q->fetch(PDO::FETCH_ASSOC);
    if ($row) {
        $creators = $row['creators'];
        $arr = json_decode($creators, true);
        $count = $arr ? count($arr) : 0;
    }
    $q2 = $conn->prepare("SELECT creator_id, note FROM user_notes WHERE user_id=?");
    $q2->execute(array($uid));
    $notes = $q2->fetchAll(PDO::FETCH_ASSOC);
}

header('Content-Type: application/json');
echo json_encode(array(
    'user' => $user,
    'uid' => $uid,
    'creator_count' => $count,
    'creators_json' => $creators,
    'notes' => $notes,
    'note_count' => count($notes)
));
