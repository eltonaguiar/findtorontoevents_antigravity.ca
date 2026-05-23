#!/usr/bin/env python3
"""
Fix db_config.php on torontoevent.net to prefer .env over environment variables
for ALL MySQL connection values (not just MYSQL_PASSWORD).
GoDaddy may set conflicting MYSQL_HOST/MYSQL_USER env vars.
"""
import ftplib
from io import BytesIO
import urllib.request, ssl, time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

NEW_DB_CONFIG = r'''<?php
// db_config.php — reads from .env file first, then env vars, then defaults.
// .env file takes priority over server env vars (GoDaddy may set conflicting vars).
error_reporting(0);
ini_set('display_errors', '0');

function _fc_db_read_env_file_val($key) {
    $envFile = dirname(__FILE__) . '/.env';
    if (!file_exists($envFile) || !is_readable($envFile)) return null;
    $raw = file_get_contents($envFile);
    $lines = preg_split('/\r?\n/', $raw);
    $aliases = array(
        'MYSQL_PASSWORD' => array('DB_PASS_SERVER_FAVCREATORS', 'DB_PASSWORD', 'DATABASE_PASSWORD'),
        'MYSQL_USER'     => array('DB_USER'),
        'MYSQL_HOST'     => array('DB_HOST'),
        'MYSQL_DATABASE' => array('DB_NAME'),
    );
    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || substr($line, 0, 1) === '#') continue;
        $eq = strpos($line, '=');
        if ($eq === false) continue;
        $k = trim(substr($line, 0, $eq));
        $val = substr($line, $eq + 1);
        if ($k === $key) return _fc_db_parse_env_value_v2($val);
        if (isset($aliases[$key]) && in_array($k, $aliases[$key])) {
            return _fc_db_parse_env_value_v2($val);
        }
    }
    return null;
}

function _fc_db_parse_env_value_v2($v) {
    $v = trim($v, " \t\r\n");
    $len = strlen($v);
    if ($len >= 2 && $v[0] === '"' && $v[$len-1] === '"') {
        $v = substr($v, 1, -1);
        return str_replace(array('\\"', '\\\\'), array('"', '\\'), $v);
    }
    if ($len >= 2 && $v[0] === "'" && $v[$len-1] === "'") {
        $v = substr($v, 1, -1);
        return str_replace("\\'", "'", $v);
    }
    return $v;
}

function _fc_db_get_val($key, $default) {
    // .env file has priority for all values (server env vars may conflict on GoDaddy)
    $fromFile = _fc_db_read_env_file_val($key);
    if ($fromFile !== null && $fromFile !== '') return $fromFile;
    // Fall back to server env vars
    $v = @getenv($key);
    if ($v !== false && $v !== '') return $v;
    if (isset($_ENV[$key]) && (string)$_ENV[$key] !== '') return (string)$_ENV[$key];
    return $default;
}

function _fc_db_clean_password($v) {
    if (!is_string($v)) return $v;
    $v = str_replace("\0", '', $v);
    return rtrim($v, "\r\n");
}

$servername = _fc_db_get_val('MYSQL_HOST', 'localhost');
$username   = _fc_db_get_val('MYSQL_USER', 'admin');
$password   = _fc_db_get_val('MYSQL_PASSWORD', '');
$password   = _fc_db_clean_password($password);
$dbname     = _fc_db_get_val('MYSQL_DATABASE', 'ejaguiar1_favcreators');
?>
'''

NEW_DB_CONNECT = r'''<?php
// db_connect.php — PHP 8.3 compatible (no exceptions, no exit on failure)
if (function_exists('mysqli_report')) {
    mysqli_report(MYSQLI_REPORT_OFF);
}
error_reporting(0);
ini_set('display_errors', '0');
if (!headers_sent()) {
    header('Content-Type: application/json');
}
require_once dirname(__FILE__) . '/db_config.php';

$conn = null;
if (isset($servername) && isset($username) && isset($password) && isset($dbname)) {
    $conn = @new mysqli($servername, $username, $password, $dbname);
    if ($conn && $conn->connect_error) {
        $conn = null;
    }
}
'''

# Also a simple debug endpoint to verify things work
DEBUG_STATUS = r'''<?php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");
require_once dirname(__FILE__) . "/db_config.php";
$r = array(
    "servername" => $servername,
    "username" => $username,
    "dbname" => $dbname,
    "pass_len" => strlen($password),
);
if (function_exists("mysqli_report")) mysqli_report(MYSQLI_REPORT_OFF);
$conn = @new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    $r["error"] = $conn->connect_error;
    $r["errno"] = $conn->connect_errno;
    // Try 127.0.0.1
    $c2 = @new mysqli("127.0.0.1", $username, $password, $dbname);
    if ($c2->connect_error) {
        $r["try_127_error"] = $c2->connect_error;
    } else {
        $r["try_127_ok"] = true;
        $r["server"] = $c2->server_info;
        $c2->close();
    }
} else {
    $r["connected"] = true;
    $r["server"] = $conn->server_info;
    $conn->close();
}
echo json_encode($r);
'''

def ftp_write(ftp, path, content):
    if isinstance(content, str):
        content = content.encode('utf-8')
    ftp.storbinary(f'STOR {path}', BytesIO(content))
    print(f'  [OK] Uploaded {path}')

def ftp_read(ftp, path):
    buf = BytesIO()
    ftp.retrbinary(f'RETR {path}', buf.write)
    return buf.getvalue().decode('utf-8')

def main():
    ftp = ftplib.FTP(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, FTP_PASS)
    print("Connected to FTP")

    # Backup current db_config.php
    try:
        old = ftp_read(ftp, '/fc/api/db_config.php')
        ftp_write(ftp, '/fc/api/db_config.php.bak', old)
    except Exception as e:
        print(f"  Could not backup db_config.php: {e}")

    # Upload new db_config.php
    ftp_write(ftp, '/fc/api/db_config.php', NEW_DB_CONFIG)
    # Upload db_connect.php (same as before but ensuring it's correct)
    ftp_write(ftp, '/fc/api/db_connect.php', NEW_DB_CONNECT)
    # Upload debug status
    ftp_write(ftp, '/fc/api/dbstatus.php', DEBUG_STATUS)

    ftp.quit()

    # Test
    print("\n--- Testing ---")
    time.sleep(2)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for url, label in [
        ('https://torontoevent.net/fc/api/dbstatus.php', 'DB Status (new)'),
        ('https://torontoevent.net/fc/api/status.php', 'FC Status'),
    ]:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            body = resp.read().decode('utf-8')
            print(f'  [200] {label}: {body[:300]}')
        except urllib.error.HTTPError as e:
            print(f'  [{e.code}] {label}: {e.reason}')
        time.sleep(0.5)

if __name__ == '__main__':
    main()
