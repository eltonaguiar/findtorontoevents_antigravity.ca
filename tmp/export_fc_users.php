<?php
$pdo = new PDO('mysql:host=localhost;dbname=ejaguiar1_favcreators;charset=utf8mb4',
    'ejaguiar1_favcreators', '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl');
$pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$out = array();

// All users
$out['users'] = $pdo->query("SELECT * FROM users")->fetchAll(PDO::FETCH_ASSOC);

// All user_lists
$out['user_lists'] = $pdo->query(
    "SELECT user_id, JSON_LENGTH(creators) as cnt FROM user_lists"
)->fetchAll(PDO::FETCH_ASSOC);

// All user_lists with creators (full JSON)
$out['user_lists_full'] = $pdo->query(
    "SELECT user_id, creators FROM user_lists WHERE user_id != 2"
)->fetchAll(PDO::FETCH_ASSOC);

// All user_notes excluding zerounderscore (user_id=2)
$out['user_notes'] = $pdo->query(
    "SELECT * FROM user_notes WHERE user_id != 2"
)->fetchAll(PDO::FETCH_ASSOC);

// All user_preferences excluding zerounderscore
$out['user_preferences'] = $pdo->query(
    "SELECT * FROM user_preferences WHERE user_id != 2"
)->fetchAll(PDO::FETCH_ASSOC);

// All user_visit_days excluding zerounderscore
$out['user_visit_days'] = $pdo->query(
    "SELECT * FROM user_visit_days WHERE user_id != 2"
)->fetchAll(PDO::FETCH_ASSOC);

// user_secondary_notes excluding zerounderscore
$out['user_secondary_notes'] = $pdo->query(
    "SELECT * FROM user_secondary_notes WHERE user_id != 2"
)->fetchAll(PDO::FETCH_ASSOC);

header('Content-Type: application/json');
echo json_encode($out);
