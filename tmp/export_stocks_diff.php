<?php
$pdo = new PDO('mysql:host=localhost;dbname=ejaguiar1_stocks;charset=utf8mb4',
    'ejaguiar1_stocks', 'stocks');
$pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$out = array();

// Get lm_signals schema + all rows (we'll upsert on GoDaddy)
$ddl = $pdo->query("SHOW CREATE TABLE lm_signals")->fetch(PDO::FETCH_NUM);
$out['lm_signals_ddl'] = $ddl[1];
$out['lm_signals'] = $pdo->query("SELECT * FROM lm_signals")->fetchAll(PDO::FETCH_ASSOC);

// Get ss_baselines schema + all rows (truncate+replace on GoDaddy since 50webs is source)
$ddl2 = $pdo->query("SHOW CREATE TABLE ss_baselines")->fetch(PDO::FETCH_NUM);
$out['ss_baselines_ddl'] = $ddl2[1];
$out['ss_baselines'] = $pdo->query("SELECT * FROM ss_baselines")->fetchAll(PDO::FETCH_ASSOC);

header('Content-Type: application/json');
echo json_encode($out);
