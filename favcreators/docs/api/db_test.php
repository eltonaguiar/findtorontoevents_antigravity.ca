<?php
header('Content-Type: application/json');
mysqli_report(MYSQLI_REPORT_OFF);

$envFile = dirname(__FILE__) . '/.env';
$env_exists = file_exists($envFile);
$env_readable = $env_exists && is_readable($envFile);

function read_env_key($key) {
    $f = dirname(__FILE__) . '/.env';
    if (!file_exists($f)) return null;
    foreach (preg_split('/\r?\n/', file_get_contents($f)) as $line) {
        $line = trim($line);
        if (!$line || $line[0] === '#') continue;
        $eq = strpos($line, '=');
        if ($eq === false) continue;
        if (trim(substr($line, 0, $eq)) !== $key) continue;
        $v = trim(substr($line, $eq + 1));
        $len = strlen($v);
        if ($len >= 2 && $v[0] === '"' && $v[$len-1] === '"') return substr($v, 1, -1);
        if ($len >= 2 && $v[0] === "'" && $v[$len-1] === "'") return substr($v, 1, -1);
        return $v;
    }
    return null;
}

$_h = read_env_key('MYSQL_HOST');
$host = ($_h !== null && $_h !== '') ? $_h : 'localhost';
$_u = read_env_key('MYSQL_USER');
$user = ($_u !== null && $_u !== '') ? $_u : 'ejaguiar1_favcreators';
$_p = read_env_key('MYSQL_PASSWORD');
$pass = ($_p !== null) ? $_p : '';
$_d = read_env_key('MYSQL_DATABASE');
$db   = ($_d !== null && $_d !== '') ? $_d : 'ejaguiar1_favcreators';

$conn = @new mysqli($host, $user, $pass, $db);
$err  = $conn ? $conn->connect_error : 'constructor returned null';

echo json_encode(array(
    'php'        => PHP_VERSION,
    'env_exists' => $env_exists,
    'env_readable'=> $env_readable,
    'host'       => $host,
    'user'       => $user,
    'db'         => $db,
    'pass_len'   => strlen($pass),
    'pass_first3'=> $pass ? substr($pass, 0, 3) . '...' : '(empty)',
    'connect_err'=> $err,
    'ok'         => !$err,
));
