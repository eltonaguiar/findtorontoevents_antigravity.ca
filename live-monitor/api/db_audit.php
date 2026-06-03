<?php
header('Content-Type: application/json');
require_once __DIR__ . '/db_config.php';

function audit_database($host, $user, $pass, $db) {
    $conn = @new mysqli($host, $user, $pass, $db);
    if ($conn->connect_error) {
        return array(
            'ok' => false,
            'error' => $conn->connect_error,
        );
    }

    $tables = array();
    $res = $conn->query("SHOW TABLES");
    if ($res) {
        while ($row = $res->fetch_row()) {
            $table = $row[0];
            $count_res = $conn->query("SELECT COUNT(*) FROM `$table`");
            $count = 0;
            if ($count_res) {
                $count_row = $count_res->fetch_row();
                $count = $count_row[0];
            }

            $last_res = $conn->query("SELECT created_at FROM `$table` ORDER BY created_at DESC LIMIT 1");
            if (!$last_res) $last_res = $conn->query("SELECT updated_at AS created_at FROM `$table` ORDER BY updated_at DESC LIMIT 1");
            if (!$last_res) $last_res = $conn->query("SELECT scan_time AS created_at FROM `$table` ORDER BY scan_time DESC LIMIT 1");
            if (!$last_res) $last_res = $conn->query("SELECT pick_date AS created_at FROM `$table` ORDER BY pick_date DESC LIMIT 1");

            $last_date = 'never';
            if ($last_res && $last_row = $last_res->fetch_assoc()) {
                $last_date = $last_row['created_at'];
            }

            $tables[] = array(
                'name' => $table,
                'rows' => $count,
                'latest' => $last_date
            );
        }
    }

    $conn->close();
    return array(
        'ok' => true,
        'tables' => $tables,
    );
}

$databases = array(
    $dbname => audit_database($servername, $username, $password, $dbname),
    $sports_dbname => audit_database($sports_servername, $sports_username, $sports_password, $sports_dbname),
);

$all_ok = true;
foreach ($databases as $result) {
    if (!$result['ok']) {
        $all_ok = false;
        break;
    }
}

echo json_encode(array(
    'ok' => $all_ok,
    'databases' => $databases,
));
