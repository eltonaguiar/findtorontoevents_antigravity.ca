<?php
/**
 * Return ALL unique creators across every user list (for avatar prefetch).
 * Protected by X-Avatar-Token header or ?token= param.
 * Returns a flat array of creators with id, name, accounts.
 */
error_reporting(0);
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-Avatar-Token');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 204 No Content');
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

/* Optional token check */
$expected_token = '';
$env_token = getenv('AVATAR_CACHE_TOKEN');
if ($env_token !== false && $env_token !== '') {
    $expected_token = $env_token;
}
$token_file = dirname(__FILE__) . '/avatar_cache_token.txt';
if ($expected_token === '' && file_exists($token_file)) {
    $expected_token = trim(file_get_contents($token_file));
}
if ($expected_token !== '') {
    $provided = isset($_SERVER['HTTP_X_AVATAR_TOKEN']) ? $_SERVER['HTTP_X_AVATAR_TOKEN'] : '';
    if ($provided === '' && isset($_GET['token'])) {
        $provided = $_GET['token'];
    }
    if ($provided !== $expected_token) {
        header('HTTP/1.1 403 Forbidden');
        echo json_encode(array('error' => 'Invalid token'));
        $conn->close();
        exit;
    }
}

/* Gather creators from all user_lists rows */
$q = $conn->query("SELECT user_id, creators FROM user_lists");
$seen_ids = array();
$all_creators = array();

if ($q) {
    while ($row = $q->fetch_assoc()) {
        $list = json_decode($row['creators'], true);
        if (!is_array($list)) continue;
        foreach ($list as $c) {
            $cid = isset($c['id']) ? $c['id'] : '';
            if ($cid === '' || isset($seen_ids[$cid])) continue;
            $seen_ids[$cid] = true;

            $accounts = isset($c['accounts']) ? $c['accounts'] : array();
            if (is_string($accounts)) {
                $decoded = json_decode($accounts, true);
                $accounts = is_array($decoded) ? $decoded : array();
            }

            $all_creators[] = array(
                'id'       => $cid,
                'name'     => isset($c['name']) ? $c['name'] : '',
                'accounts' => $accounts
            );
        }
    }
}

/* Also include creators from the global creators table (in_guest_list) */
$g = $conn->query("SELECT id, name, accounts FROM creators WHERE in_guest_list = 1");
if ($g) {
    while ($row = $g->fetch_assoc()) {
        $cid = $row['id'];
        if (isset($seen_ids[$cid])) continue;
        $seen_ids[$cid] = true;
        $accounts = json_decode($row['accounts'], true);
        if (!is_array($accounts)) $accounts = array();
        $all_creators[] = array(
            'id'       => $cid,
            'name'     => $row['name'],
            'accounts' => $accounts
        );
    }
}

echo json_encode(array(
    'ok'       => true,
    'count'    => count($all_creators),
    'creators' => $all_creators
));
$conn->close();
?>
