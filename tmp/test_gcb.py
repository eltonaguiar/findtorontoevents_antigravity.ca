#!/usr/bin/env python3
import ftplib
from io import BytesIO
import urllib.request, ssl, time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

ftp = ftplib.FTP(FTP_HOST, timeout=30)
ftp.login(FTP_USER, FTP_PASS)

# Simple diagnostic that avoids curl timeouts
diag = r'''<?php
header("Content-Type: application/json");
$r = ["step" => "start"];

// 1. Check config.php
$config_file = dirname(__FILE__) . "/config.php";
$r["config_exists"] = file_exists($config_file);
if ($r["config_exists"]) {
    require_once $config_file;
    $r["step"] = "config_loaded";
}

// 2. Check db_config.php
try {
    require_once dirname(__FILE__) . "/db_config.php";
    $r["step"] = "db_config_loaded";
    $r["servername"] = $servername;
    $r["username"] = $username;
    $r["dbname"] = $dbname;
    $r["pass_len"] = strlen($password);
} catch (Throwable $e) {
    $r["db_config_error"] = $e->getMessage();
    echo json_encode($r);
    exit;
}

// 3. mysqli connect
if (function_exists("mysqli_report")) mysqli_report(MYSQLI_REPORT_OFF);
$conn = @new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    $r["connect_error"] = $conn->connect_error;
} else {
    $r["step"] = "db_connected";
    // Check users table
    $res = $conn->query("SHOW TABLES LIKE 'users'");
    $r["users_table"] = ($res && $res->num_rows > 0);
    $conn->close();
}

// 4. curl
$r["curl"] = function_exists("curl_init");

// 5. Google credentials from config
$r["google_client_id_defined"] = defined("GOOGLE_CLIENT_ID");
$r["google_client_id_len"] = defined("GOOGLE_CLIENT_ID") ? strlen(GOOGLE_CLIENT_ID) : 0;
$r["google_secret_len"] = defined("GOOGLE_CLIENT_SECRET") ? strlen(GOOGLE_CLIENT_SECRET) : 0;

echo json_encode($r, JSON_PRETTY_PRINT);
'''

ftp.storbinary("STOR /fc/api/_gcbtest.php", BytesIO(diag.encode()))
print("Uploaded _gcbtest.php")
ftp.quit()

time.sleep(1)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    req = urllib.request.Request(
        "https://torontoevent.net/fc/api/_gcbtest.php",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    resp = urllib.request.urlopen(req, timeout=15, context=ctx)
    print(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.reason}")
    try: print(e.read().decode("utf-8")[:500])
    except: pass
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
