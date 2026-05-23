<?php
// DB diagnostic - uses shared db-config credential fallbacks
require_once dirname(__FILE__) . '/db-config.php';

try {
    $pdo = getDbConnection();
    if ($pdo === null) {
        throw new Exception('Connection returned null');
    }

    echo "Connected to ejaguiar1_tvmoviestrailers OK! ";
    $stmt = $pdo->query("SELECT COUNT(*) AS cnt FROM movies");
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    $stmtType = $pdo->query("SELECT type, COUNT(*) AS cnt FROM movies GROUP BY type");
    $typeRows = $stmtType->fetchAll(PDO::FETCH_ASSOC);

    $movieCount = 0;
    $tvCount = 0;
    foreach ($typeRows as $typeRow) {
        if ($typeRow['type'] === 'movie') {
            $movieCount = (int)$typeRow['cnt'];
        } elseif ($typeRow['type'] === 'tv') {
            $tvCount = (int)$typeRow['cnt'];
        }
    }

    echo "Movies table rows: " . $row['cnt'] . " (movie=" . $movieCount . ", tv=" . $tvCount . ")";
} catch (Exception $e) {
    echo "FAIL: " . $e->getMessage();
}
?>
