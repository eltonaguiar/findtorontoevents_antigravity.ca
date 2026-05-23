#!/usr/bin/env python3
import ftplib
from io import BytesIO
import urllib.request, ssl, time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

ftp = ftplib.FTP(FTP_HOST, timeout=15)
ftp.login(FTP_USER, FTP_PASS)

# Check if config.php exists
for path in ['/fc/api/config.php', '/fc/api/google_auth.php']:
    buf = BytesIO()
    try:
        ftp.retrbinary(f"RETR {path}", buf.write)
        content = buf.getvalue().decode('utf-8', errors='replace')
        print(f"\n=== {path} ===")
        print(content[:2000])
    except Exception as e:
        print(f"\n{path}: {e}")

# Upload a test diagnostic for google_callback
diag = r'''<?php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

$r = ["step" => "start"];

// Check config
$config_file = dirname(__FILE__) . "/config.php";
$r["config_exists"] = file_exists($config_file);

// Check db_config
try {
    require_once dirname(__FILE__) . "/db_config.php";
    $r["servername"] = $servername;
    $r["username"] = $username;
    $r["dbname"] = $dbname;
    $r["pass_len"] = strlen($password);
    $r["step"] = "db_config_loaded";
} catch (Throwable $e) {
    $r["db_config_error"] = $e->getMessage();
    echo json_encode($r);
    exit;
}

// Try mysqli
if (function_exists("mysqli_report")) mysqli_report(MYSQLI_REPORT_OFF);
$conn = @new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    $r["connect_error"] = $conn->connect_error;
    echo json_encode($r);
    exit;
}
$r["step"] = "db_connected";
$r["server_info"] = $conn->server_info;

// Check users table
$res = $conn->query("SHOW TABLES LIKE 'users'");
$r["users_table_exists"] = ($res && $res->num_rows > 0);

// Check curl
$r["curl_available"] = function_exists("curl_init");

// Check Google env
$r["google_client_id_env"] = getenv("GOOGLE_CLIENT_ID");
$r["google_client_id_len"] = strlen((string)getenv("GOOGLE_CLIENT_ID"));

// Read from .env
$envFile = dirname(__FILE__) . "/.env";
if (file_exists($envFile)) {
    $lines = file($envFile);
    foreach ($lines as $line) {
        $line = trim($line);
        $eq = strpos($line, "=");
        if ($eq === false) continue;
        $k = trim(substr($line, 0, $eq));
        $v = trim(substr($line, $eq + 1), "\" \t\r\n");
        if ($k === "GOOGLE_CLIENT_ID") $r["google_client_id_from_env"] = strlen($v) . " chars";
        if ($k === "GOOGLE_CLIENT_SECRET") $r["google_secret_from_env"] = strlen($v) . " chars";
    }
}

$conn->close();
echo json_encode($r, JSON_PRETTY_PRINT);
'''

ftp.storbinary('/fc/api/_gcb_test.php', BytesIO(diag.encode()))
# Note: FTP STOR path must not start with STOR prefix issue
ftp.storbinary('STOR /fc/api/_gcb_test.php', BytesIO(diag.encode()))
print("\nUploaded _gcb_test.php")
ftp.quit()

time.sleep(1)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    req = urllib.request.Request(
        'https://torontoevent.net/fc/api/_gcb_test.php',
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    resp = urllib.request.urlopen(req, timeout=15, context=ctx)
    print("\n=== Diagnostic Result ===")
    print(resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"\nHTTP {e.code}: {e.reason}")
    try:
        print(e.read().decode('utf-8')[:500])
    except:
        pass
except Exception as e:
    print(f"\nError: {type(e).__name__}: {e}")
