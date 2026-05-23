<?php
$conn = new PDO('mysql:host=localhost;dbname=ejaguiar1_favcreators;charset=utf8mb4',
    'ejaguiar1_favcreators', '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl');
$conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$export = array();

// Get CREATE TABLE for missing tables
$missing = array('streamer_content','ttt_chat','ttt_matches','ttt_spectators','user_content_preferences','user_saved_events');
$schemas = array();
foreach ($missing as $t) {
    $r = $conn->query("SHOW CREATE TABLE `$t`")->fetch(PDO::FETCH_NUM);
    $schemas[$t] = $r[1];
}
$export['schemas'] = $schemas;

// Get data for tables with data
$tables_with_data = array('ttt_matches','streamer_last_seen','user_preferences','user_secondary_notes','user_visit_days');
$data = array();
foreach ($tables_with_data as $t) {
    $rows = $conn->query("SELECT * FROM `$t`")->fetchAll(PDO::FETCH_ASSOC);
    $data[$t] = $rows;
}
$export['data'] = $data;

// Get users 2,3,4 (all except zerounderscore which is user_id=2 on 50webs)
$users = $conn->query("SELECT * FROM users WHERE email != 'zerounderscore@gmail.com'")->fetchAll(PDO::FETCH_ASSOC);
$export['other_users'] = $users;

// Get user_lists for other users
$lists = $conn->query("SELECT user_id, JSON_LENGTH(creators) as cnt FROM user_lists")->fetchAll(PDO::FETCH_ASSOC);
$export['user_lists_summary'] = $lists;

// Get user_notes for all users (for reference)
$notes = $conn->query("SELECT user_id, creator_id, note FROM user_notes")->fetchAll(PDO::FETCH_ASSOC);
$export['user_notes'] = $notes;

header('Content-Type: application/json');
echo json_encode($export);
