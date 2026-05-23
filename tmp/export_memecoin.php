<?php
$pdo = new PDO('mysql:host=localhost;dbname=ejaguiar1_memecoin;charset=utf8mb4',
    'ejaguiar1_memecoin', getenv('MEMECOIN_DB_PASS') ?: '');
$pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$missing = array(
    'crypto_assets','crypto_indicators','crypto_market_data','crypto_ohlcv',
    'crypto_patterns','crypto_signals','meme_coin_stats','ml_model_performance',
    'ml_models','tv_signals'
);

$result = array();
foreach ($missing as $t) {
    $ddl = $pdo->query("SHOW CREATE TABLE `$t`")->fetch(PDO::FETCH_NUM);
    $rows = $pdo->query("SELECT * FROM `$t`")->fetchAll(PDO::FETCH_ASSOC);
    $result[$t] = array('ddl' => $ddl[1], 'rows' => $rows);
}

header('Content-Type: application/json');
echo json_encode($result);
