#!/usr/bin/env python3
import ftplib
from io import BytesIO
import urllib.request, ssl, time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

ftp = ftplib.FTP(FTP_HOST, timeout=15)
ftp.login(FTP_USER, FTP_PASS)

diag = r'''<?php
header("Content-Type: application/json");

$r = [];
$r["getenv_MYSQL_HOST"] = getenv("MYSQL_HOST");
$r["getenv_MYSQL_USER"] = getenv("MYSQL_USER");
$r["_ENV_MYSQL_HOST"] = isset($_ENV["MYSQL_HOST"]) ? $_ENV["MYSQL_HOST"] : "not_set";

// Read env file manually
$envFile = dirname(__FILE__) . "/.env";
$r["env_file_exists"] = file_exists($envFile);

$host = "localhost";
$user = "admin";
$db = "ejaguiar1_favcreators";
$pass = "";

if ($r["env_file_exists"]) {
    $raw = file_get_contents($envFile);
    $lines = explode("\n", $raw);
    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === "" || substr($line, 0, 1) === "#") continue;
        $eq = strpos($line, "=");
        if ($eq === false) continue;
        $k = trim(substr($line, 0, $eq));
        $v = trim(substr($line, $eq + 1), "\" \t\r\n");
        if ($k === "MYSQL_HOST") $host = $v;
        if ($k === "MYSQL_USER") $user = $v;
        if ($k === "MYSQL_DATABASE") $db = $v;
        if ($k === "MYSQL_PASSWORD") $pass = $v;
    }
}

$r["env_host"] = $host;
$r["env_user"] = $user;
$r["env_db"] = $db;
$r["pass_len"] = strlen($pass);

if (function_exists("mysqli_report")) mysqli_report(MYSQLI_REPORT_OFF);
$conn = @new mysqli($host, $user, $pass, $db);
if ($conn->connect_error) {
    $r["connect_error"] = $conn->connect_error;
    $r["connect_errno"] = $conn->connect_errno;

    // Try with 127.0.0.1 instead of localhost
    $conn2 = @new mysqli("127.0.0.1", $user, $pass, $db);
    if ($conn2->connect_error) {
        $r["try_127_error"] = $conn2->connect_error;
    } else {
        $r["try_127_ok"] = true;
        $r["server"] = $conn2->server_info;
        $conn2->close();
    }
} else {
    $r["connected"] = true;
    $r["server"] = $conn->server_info;
    $conn->close();
}

echo json_encode($r, JSON_PRETTY_PRINT);
'''

ftp.storbinary('STOR /fc/api/_dbdiag3.php', BytesIO(diag.encode()))
print('Uploaded _dbdiag3.php')
ftp.quit()
time.sleep(1)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    resp = urllib.request.urlopen('https://torontoevent.net/fc/api/_dbdiag3.php', timeout=15, context=ctx)
    print(resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f'HTTP Error {e.code}: {e.reason}')
    try:
        print(e.read().decode('utf-8')[:1000])
    except:
        pass
