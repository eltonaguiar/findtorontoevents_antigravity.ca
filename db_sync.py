#!/usr/bin/env python3
"""
db_sync.py — FindTorontoEvents Database Sync
=============================================
1. Dumps all databases from findtorontoevents.ca (50webs):
   - Direct PyMySQL for DBs with remote access enabled
   - PHP-over-FTP export for DBs that block remote MySQL
2. Archives old dumps in .DATABASES/old_YYYYMMDD_HHMMSS/
3. Saves fresh .sql.gz dumps to .DATABASES/
4. FTP-uploads dumps to tdotevent.ca (/tdotevent.ca/db_backups/) as offsite backup
5. Wipes + restores all databases on torontoevent.net (GoDaddy) from the fresh dumps

Run:  python db_sync.py
      python db_sync.py --skip-godaddy     # skip step 5
      python db_sync.py --skip-ftp         # skip step 4
      python db_sync.py --only-local       # steps 1-3 only
"""

import sys, os, gzip, shutil, ftplib, ssl, time, argparse, secrets, json, base64, urllib.request

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
from datetime import datetime
from io import BytesIO

# ── Try to import pymysql; install if missing ──────────────────────────────────
try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("📦 Installing pymysql...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"], stdout=subprocess.DEVNULL)
    import pymysql
    import pymysql.cursors

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).parent
DB_DIR     = SCRIPT_DIR / ".DATABASES"

# ── Source: findtorontoevents.ca on 50webs ─────────────────────────────────────
SOURCE_MYSQL_HOST = "mysql.50webs.com"
SOURCE_MYSQL_PORT = 3306
SOURCE_FTP_HOST   = "ftps2.50webs.com"
SOURCE_FTP_USER   = "ejaguiar1"
SOURCE_FTP_PASS   = os.environ.get("FTPGODADDYPASS", "")
SOURCE_FTP_ROOT   = "/findtorontoevents.ca"
SOURCE_HTTP_BASE  = "https://findtorontoevents.ca"

# Each database: (db_name, mysql_user, mysql_password)
# Password "" = unknown, will use PHP export fallback
SOURCE_DATABASES = [
    # (db_name,                      mysql_user,                      mysql_password)
    # Direct MySQL (remote access enabled on mysql.50webs.com):
    ("ejaguiar1_events",             "ejaguiar1_events",              "0nOj4g4RA%FD9P4c7iq)"),
    ("ejaguiar1_memecoin",           "ejaguiar1_memecoin",            os.environ.get("MEMECOIN_DB_PASS", "")),
    ("ejaguiar1_stocks",             "ejaguiar1_stocks",              "stocks"),
    # PHP export fallback (remote MySQL blocked, server-side access only):
    ("ejaguiar1_sportsbet",          "ejaguiar1_sportsbet",           "eltonsportsbets"),
    ("ejaguiar1_tvmoviestrailers",   "ejaguiar1_tvmoviestrailers",    "tvmoviestrailers"),
    ("ejaguiar1_favcreators",        "ejaguiar1_favcreators",         "3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl"),
    ("ejaguiar1_deals",              "ejaguiar1_deals",               "deals123"),
    ("ejaguiar1_news",               "ejaguiar1_news",                "newsnews"),
]

# ── Destination 1: tdotevent.ca FTP backup (same 50webs host) ─────────────────
TDOT_FTP_HOST   = "ftps2.50webs.com"
TDOT_FTP_USER   = "ejaguiar1"
TDOT_FTP_PASS   = os.environ.get("FTPGODADDYPASS", "")
TDOT_FTP_ROOT   = "/tdotevent.ca"
TDOT_BACKUP_DIR = "db_backups"

# ── Destination 2: torontoevent.net MySQL (GoDaddy, remote MySQL enabled) ─────
GODADDY_HOST = "torontoevent.net"
GODADDY_PORT = 3306
GODADDY_USER = "admin"
GODADDY_PASS = os.environ.get(
    "DB_PASS_SERVER_FAVCREATORS",
    "3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl"
)

# ── PHP export script (deployed on-the-fly for DBs with no remote MySQL) ───────
PHP_SCRIPT_NAME = f"_dbex_{secrets.token_hex(6)}.php"   # random name per run
PHP_SCRIPT_REMOTE = f"{SOURCE_FTP_ROOT}/{PHP_SCRIPT_NAME}"
PHP_RUN_TOKEN = secrets.token_hex(24)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def banner(msg):
    width = 70
    print("\n" + "═" * width)
    print(f"  {msg}")
    print("═" * width)

def log_ok(msg):   print(f"  ✅  {msg}")
def log_warn(msg): print(f"  ⚠️   {msg}")
def log_err(msg):  print(f"  ❌  {msg}")
def log_info(msg): print(f"  ℹ️   {msg}")


def archive_old_dumps():
    existing = list(DB_DIR.glob("*.sql.gz"))
    if not existing:
        log_info("No existing dumps to archive")
        return
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    old = DB_DIR / f"old_{ts}"
    old.mkdir(parents=True, exist_ok=True)
    for f in existing:
        shutil.move(str(f), str(old / f.name))
    log_ok(f"Moved {len(existing)} old dump(s) → .DATABASES/old_{ts}/")


# ── FTP helpers ───────────────────────────────────────────────────────────────

def ftps_connect(host, user, pw) -> ftplib.FTP_TLS:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ftp = ftplib.FTP_TLS(context=ctx)
    ftp.connect(host, 21, timeout=30)
    ftp.login(user, pw)
    ftp.prot_p()
    return ftp


def ftp_ensure_dir(ftp, path: str):
    ftp.cwd("/")
    for part in path.strip("/").split("/"):
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            try:
                ftp.mkd(part)
                ftp.cwd(part)
            except Exception as e:
                log_warn(f"mkd '{part}' failed: {e}")
                return


# ── Direct MySQL dump (for DBs with remote access) ────────────────────────────

def pymysql_dump(dbname: str, user: str, password: str) -> bytes | None:
    """Connect and dump via PyMySQL. Returns gzipped SQL or None on failure."""
    try:
        conn = pymysql.connect(
            host=SOURCE_MYSQL_HOST, port=SOURCE_MYSQL_PORT,
            user=user, password=password, database=dbname,
            connect_timeout=15, charset="utf8mb4",
        )
    except Exception as e:
        return None  # let caller decide on fallback

    sql_lines = [
        f"-- FindTorontoEvents DB Dump: {dbname}",
        f"-- Generated: {datetime.utcnow().isoformat()}Z",
        "-- Source: mysql.50webs.com\n",
        "SET FOREIGN_KEY_CHECKS=0;",
        "SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';",
        "SET NAMES utf8mb4;\n",
    ]

    cursor = conn.cursor()
    cursor.execute("SHOW FULL TABLES")
    tables = cursor.fetchall()

    for row in tables:
        table_name = row[0]
        table_type = row[1]

        sql_lines.append(f"\n-- ── {table_name} ──")
        if table_type == "VIEW":
            cursor.execute(f"SHOW CREATE VIEW `{table_name}`")
            sql_lines.append(f"DROP VIEW IF EXISTS `{table_name}`;")
            sql_lines.append(cursor.fetchone()[1] + ";")
            continue

        cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
        sql_lines.append(f"DROP TABLE IF EXISTS `{table_name}`;")
        sql_lines.append(cursor.fetchone()[1] + ";\n")

        cursor.execute(f"SELECT * FROM `{table_name}`")
        cols = [d[0] for d in cursor.description]
        col_list = ", ".join(f"`{c}`" for c in cols)

        rows = cursor.fetchmany(500)
        while rows:
            vals_list = []
            for row_data in rows:
                vals = []
                for v in row_data:
                    if v is None:
                        vals.append("NULL")
                    elif isinstance(v, (int, float)):
                        vals.append(str(v))
                    elif isinstance(v, (bytes, bytearray)):
                        vals.append("0x" + v.hex())
                    else:
                        esc = str(v).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
                        vals.append(f"'{esc}'")
                vals_list.append("(" + ", ".join(vals) + ")")
            sql_lines.append(f"INSERT INTO `{table_name}` ({col_list}) VALUES\n" + ",\n".join(vals_list) + ";")
            rows = cursor.fetchmany(500)

    sql_lines.append("\nSET FOREIGN_KEY_CHECKS=1;")
    conn.close()

    buf = BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6) as gz:
        gz.write("\n".join(sql_lines).encode("utf-8"))
    return buf.getvalue()


# ── PHP-over-FTP export (for DBs blocked from remote MySQL) ──────────────────

PHP_SCRIPT_TEMPLATE = '''<?php
$tok = {TOKEN_Q};
$given = isset($_GET['token']) ? $_GET['token'] : '';
if ($tok !== $given) { header('HTTP/1.0 403 Forbidden'); exit; }

$dbs = {DBS_ARRAY};
$results = array();
$errors  = array();

foreach ($dbs as $info) {
    $dbname = $info['db'];
    $user   = $info['user'];
    $pass   = $info['pass'];
    $dump   = '';

    // Try mysqldump via exec()
    if (function_exists('exec')) {
        $tmp = tempnam(sys_get_temp_dir(), 'dbex_') . '.sql';
        $cmd = 'mysqldump -h localhost -u ' . escapeshellarg($user)
             . ' -p' . escapeshellarg($pass)
             . ' --single-transaction ' . escapeshellarg($dbname)
             . ' > ' . escapeshellarg($tmp) . ' 2>/dev/null';
        $out2 = array();
        exec($cmd, $out2, $rc);
        if ($rc === 0 && file_exists($tmp) && filesize($tmp) > 0) {
            $dump = file_get_contents($tmp);
            unlink($tmp);
        }
    }

    // Fallback: old mysql_ extension (available in PHP 5.2)
    if (empty($dump)) {
        $conn = @mysql_connect('localhost', $user, $pass);
        if ($conn) {
            @mysql_select_db($dbname, $conn);
            @mysql_query("SET NAMES utf8", $conn);
            $lines = array(
                "-- PHP export: $dbname",
                "-- " . date('c'),
                "SET FOREIGN_KEY_CHECKS=0;",
                "SET NAMES utf8;",
                ""
            );
            $tr = mysql_query("SHOW TABLES", $conn);
            while ($tr && $row = mysql_fetch_row($tr)) {
                $tbl = $row[0];
                $cr = mysql_query("SHOW CREATE TABLE `$tbl`", $conn);
                $crow = mysql_fetch_row($cr);
                $lines[] = "DROP TABLE IF EXISTS `$tbl`;";
                $lines[] = $crow[1] . ";";
                $dr = mysql_query("SELECT * FROM `$tbl`", $conn);
                if ($dr && mysql_num_rows($dr) > 0) {
                    $num_fields = mysql_num_fields($dr);
                    $fnames = array();
                    for ($i = 0; $i < $num_fields; $i++) {
                        $fnames[] = '`' . mysql_field_name($dr, $i) . '`';
                    }
                    $cols = implode(', ', $fnames);
                    $batch = array();
                    while ($drow = mysql_fetch_row($dr)) {
                        $vals = array();
                        foreach ($drow as $v) {
                            if ($v === NULL) { $vals[] = 'NULL'; }
                            else { $vals[] = "'" . mysql_real_escape_string($v, $conn) . "'"; }
                        }
                        $batch[] = '(' . implode(', ', $vals) . ')';
                        if (count($batch) >= 500) {
                            $lines[] = "INSERT INTO `$tbl` ($cols) VALUES\\n" . implode(",\\n", $batch) . ";";
                            $batch = array();
                        }
                    }
                    if (!empty($batch)) {
                        $lines[] = "INSERT INTO `$tbl` ($cols) VALUES\\n" . implode(",\\n", $batch) . ";";
                    }
                }
            }
            $lines[] = "SET FOREIGN_KEY_CHECKS=1;";
            $dump = implode("\\n", $lines);
            mysql_close($conn);
        }
    }

    if (!empty($dump)) {
        $results[$dbname] = base64_encode(gzencode($dump, 6));
    } else {
        $errors[] = $dbname . ': export failed';
    }
}

header('Content-Type: application/json');
echo json_encode(array('status' => 'ok', 'dumps' => $results, 'errors' => $errors));
'''


def deploy_php_exporter(ftp: ftplib.FTP_TLS, db_list: list[tuple]) -> str | None:
    """Build + upload the PHP export script. Returns the public URL."""
    # Build the PHP db array in PHP 5.2-compatible syntax
    php_db_entries = []
    for db, user, pw in db_list:
        # Escape single quotes in password (shouldn't happen but safety first)
        pw_esc   = pw.replace("'", "\\'")
        user_esc = user.replace("'", "\\'")
        db_esc   = db.replace("'", "\\'")
        php_db_entries.append(
            f"    array('db' => '{db_esc}', 'user' => '{user_esc}', 'pass' => '{pw_esc}')"
        )
    php_dbs = "array(\n" + ",\n".join(php_db_entries) + "\n)"

    php_content = PHP_SCRIPT_TEMPLATE \
        .replace("{TOKEN_Q}", f"'{PHP_RUN_TOKEN}'") \
        .replace("{DBS_ARRAY}", php_dbs)

    try:
        ftp.cwd("/findtorontoevents.ca")
        ftp.storbinary(f"STOR {PHP_SCRIPT_NAME}", BytesIO(php_content.encode("utf-8")))
        log_ok(f"PHP exporter deployed: {PHP_SCRIPT_NAME}")
        return f"{SOURCE_HTTP_BASE}/{PHP_SCRIPT_NAME}"
    except Exception as e:
        log_err(f"Failed to deploy PHP exporter: {e}")
        return None


def call_php_exporter(url: str) -> dict | None:
    """Call the PHP exporter via HTTPS, return parsed JSON or None."""
    full_url = f"{url}?token={PHP_RUN_TOKEN}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0",
        "Accept": "application/json, */*",
        "Referer": SOURCE_HTTP_BASE + "/",
    }
    for attempt in range(3):
        try:
            req = urllib.request.Request(full_url, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read()
                if not raw.strip():
                    log_warn(f"Empty response on attempt {attempt+1}")
                    time.sleep(5)
                    continue
                return json.loads(raw)
        except Exception as e:
            log_warn(f"HTTP attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(5)
    return None


def delete_php_exporter(ftp: ftplib.FTP_TLS):
    """Overwrite + delete the temp PHP script."""
    try:
        ftp.cwd("/findtorontoevents.ca")
        ftp.storbinary(f"STOR {PHP_SCRIPT_NAME}", BytesIO(b"<?php http_response_code(404);exit;"))
        try:
            ftp.delete(PHP_SCRIPT_NAME)
        except Exception:
            pass
        log_ok("PHP exporter removed from server")
    except Exception as e:
        log_warn(f"Cleanup of PHP exporter failed: {e}")


# ── GoDaddy restore ───────────────────────────────────────────────────────────

def restore_to_godaddy(dump_files: list[Path]) -> bool:
    banner("STEP 5 — Restore databases to torontoevent.net (GoDaddy)")
    log_info(f"Host: {GODADDY_HOST}:{GODADDY_PORT}  User: {GODADDY_USER}")

    try:
        conn = pymysql.connect(
            host=GODADDY_HOST, port=GODADDY_PORT,
            user=GODADDY_USER, password=GODADDY_PASS,
            connect_timeout=20, charset="utf8mb4", autocommit=True,
        )
        log_ok(f"Connected to GoDaddy MySQL at {GODADDY_HOST}")
    except Exception as e:
        log_err(f"Cannot connect to torontoevent.net MySQL: {e}")
        return False

    results = {}
    for dump_file in dump_files:
        dbname = dump_file.stem
        if dbname.endswith(".sql"):
            dbname = dbname[:-4]

        print(f"\n  📂 {dbname}")
        try:
            with gzip.open(dump_file, "rt", encoding="utf-8", errors="replace") as gz:
                sql_content = gz.read()
        except Exception as e:
            log_err(f"Read failed: {e}")
            results[dbname] = "read_error"
            continue

        cur = conn.cursor()
        try:
            cur.execute(f"DROP DATABASE IF EXISTS `{dbname}`")
            cur.execute(f"CREATE DATABASE `{dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cur.execute(f"USE `{dbname}`")
        except Exception as e:
            # GoDaddy sometimes can't DROP/CREATE managed databases — fall back to clearing tables
            log_warn(f"DROP/CREATE failed ({e}), falling back to clear-tables")
            try:
                cur.execute(f"USE `{dbname}`")
                cur.execute("SET FOREIGN_KEY_CHECKS=0")
                cur.execute("SHOW TABLES")
                tables = [row[0] for row in cur.fetchall()]
                for t in tables:
                    cur.execute(f"DROP TABLE IF EXISTS `{t}`")
                cur.execute("SET FOREIGN_KEY_CHECKS=1")
                log_ok(f"Cleared {len(tables)} tables from existing {dbname}")
            except Exception as e2:
                log_err(f"Reset failed completely: {e2}")
                results[dbname] = "reset_error"
                continue

        # Replace MySQL 8.0-only collation with MySQL 5.7-compatible equivalent
        sql_content = sql_content.replace("utf8mb4_0900_ai_ci", "utf8mb4_unicode_ci")
        sql_content = sql_content.replace("utf8_0900_ai_ci", "utf8_unicode_ci")

        # Always explicitly disable FK checks before running statements (the SQL header
        # comment block may swallow the SET FOREIGN_KEY_CHECKS=0 line in the splitter)
        cur.execute("SET FOREIGN_KEY_CHECKS=0")

        statements = [s.strip() for s in sql_content.split(";\n") if s.strip() and not s.strip().startswith("--")]
        executed = errors = 0
        for stmt in statements:
            if not stmt:
                continue
            # Skip pure-comment lines embedded in multi-line chunks
            clean = "\n".join(ln for ln in stmt.splitlines() if not ln.strip().startswith("--")).strip()
            if not clean:
                continue
            try:
                cur.execute(clean)
                executed += 1
            except Exception as e:
                err_msg = str(e)
                if "already exists" not in err_msg.lower():
                    errors += 1
                    if errors <= 3:
                        log_warn(f"  stmt err: {err_msg[:100]}")

        cur.execute("SET FOREIGN_KEY_CHECKS=1")

        log_ok(f"{executed} statements, {errors} errors")
        results[dbname] = "ok" if errors == 0 else f"partial ({errors} errors)"

    conn.close()
    print()
    log_ok("GoDaddy restore summary:")
    for db, status in results.items():
        icon = "✅" if status == "ok" else "⚠️" if "partial" in status else "❌"
        print(f"    {icon}  {db}: {status}")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="FindTorontoEvents DB Sync")
    parser.add_argument("--skip-godaddy", action="store_true")
    parser.add_argument("--skip-ftp",     action="store_true")
    parser.add_argument("--only-local",   action="store_true")
    args = parser.parse_args()

    start_time = time.time()
    DB_DIR.mkdir(parents=True, exist_ok=True)

    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║         FindTorontoEvents — Database Sync Script                     ║
║  Source : mysql.50webs.com / findtorontoevents.ca (PHP fallback)     ║
║  Local  : .DATABASES/                                                ║
║  Backup : tdotevent.ca/db_backups/ (FTP)                             ║
║  Mirror : torontoevent.net MySQL (GoDaddy admin)                     ║
╚══════════════════════════════════════════════════════════════════════╝
  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")

    # Step 1: Archive old dumps
    banner("STEP 1 — Archive old dumps")
    archive_old_dumps()

    # Step 2: Connect FTP (needed for PHP fallback + tdotevent upload)
    banner("STEP 2 — Connect to 50webs FTP")
    try:
        ftp = ftps_connect(SOURCE_FTP_HOST, SOURCE_FTP_USER, SOURCE_FTP_PASS)
        log_ok(f"FTP connected to {SOURCE_FTP_HOST}")
    except Exception as e:
        log_err(f"FTP connection failed: {e}")
        ftp = None

    # Step 3: Dump databases
    banner("STEP 3 — Dump all databases")
    dumped_files = []
    skipped = []
    php_needed = []   # DBs that need PHP fallback

    # First pass: try direct MySQL
    for dbname, user, password in SOURCE_DATABASES:
        print(f"\n  📦 {dbname}")
        if password:
            gz = pymysql_dump(dbname, user, password)
            if gz is not None:
                out = DB_DIR / f"{dbname}.sql.gz"
                out.write_bytes(gz)
                log_ok(f"Dumped via MySQL → {dbname}.sql.gz ({len(gz)/1024:.1f} KB)")
                dumped_files.append(out)
                continue
            else:
                log_warn("Direct MySQL failed → will use PHP fallback")

        php_needed.append((dbname, user, password))

    # Second pass: PHP fallback for remaining DBs
    if php_needed and ftp is not None:
        print(f"\n  📡 PHP export for {len(php_needed)} database(s): {[d[0] for d in php_needed]}")
        url = deploy_php_exporter(ftp, php_needed)
        if url:
            time.sleep(3)  # brief pause for FTP propagation
            result = call_php_exporter(url)
            if result:
                if result.get("errors"):
                    for err in result["errors"]:
                        log_warn(f"PHP export error: {err}")
                for dbname, _, _ in php_needed:
                    b64gz = result.get("dumps", {}).get(dbname)
                    if b64gz:
                        gz_bytes = base64.b64decode(b64gz)
                        out = DB_DIR / f"{dbname}.sql.gz"
                        out.write_bytes(gz_bytes)
                        log_ok(f"Dumped via PHP → {dbname}.sql.gz ({len(gz_bytes)/1024:.1f} KB)")
                        dumped_files.append(out)
                    else:
                        log_err(f"No dump returned for {dbname}")
                        skipped.append(dbname)
            else:
                log_err("PHP exporter returned no data")
                skipped.extend([d[0] for d in php_needed])

            # Clean up PHP script
            delete_php_exporter(ftp)
        else:
            skipped.extend([d[0] for d in php_needed])
    elif php_needed:
        log_warn(f"FTP not available — skipping PHP fallback for: {[d[0] for d in php_needed]}")
        skipped.extend([d[0] for d in php_needed])

    print(f"\n  {'─'*55}")
    log_ok(f"Dumped: {len(dumped_files)} / {len(SOURCE_DATABASES)} databases")
    if skipped:
        log_warn(f"Skipped: {', '.join(skipped)}")

    if not dumped_files:
        log_err("No databases dumped. Exiting.")
        if ftp:
            ftp.quit()
        sys.exit(1)

    # Step 4: FTP upload to tdotevent.ca
    if not args.skip_ftp and not args.only_local and ftp is not None:
        banner("STEP 4 — Upload dumps to tdotevent.ca (FTP offsite backup)")
        try:
            ftp_ensure_dir(ftp, f"{TDOT_FTP_ROOT}/{TDOT_BACKUP_DIR}")
            ftp.cwd(f"/{TDOT_FTP_ROOT.strip('/')}/{TDOT_BACKUP_DIR}")
            uploaded = 0
            for dump_file in dumped_files:
                with open(dump_file, "rb") as f:
                    ftp.storbinary(f"STOR {dump_file.name}", f)
                log_ok(f"Uploaded {dump_file.name}")
                uploaded += 1
            # Upload manifest
            ts = datetime.utcnow().isoformat()
            manifest = f"Backup from findtorontoevents.ca — {ts}\nFiles: {[f.name for f in dumped_files]}\n"
            ftp.storbinary("STOR MANIFEST.txt", BytesIO(manifest.encode()))
            log_ok(f"Uploaded {uploaded} dumps to /tdotevent.ca/{TDOT_BACKUP_DIR}/")
        except Exception as e:
            log_err(f"FTP upload to tdotevent.ca failed: {e}")
    elif args.skip_ftp or args.only_local:
        log_info("Skipping FTP upload to tdotevent.ca")

    if ftp:
        try:
            ftp.quit()
        except Exception:
            pass

    # Step 5: Restore to torontoevent.net
    if not args.skip_godaddy and not args.only_local:
        restore_to_godaddy(dumped_files)
    else:
        log_info("Skipping torontoevent.net restore")

    elapsed = time.time() - start_time
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║  ✅  SYNC COMPLETE  ({elapsed:.0f}s elapsed)
╚══════════════════════════════════════════════════════════════════════╝
  Local dumps  : .DATABASES/ ({len(dumped_files)} files)
  FTP backup   : /tdotevent.ca/db_backups/
  GoDaddy      : torontoevent.net restored
  Skipped      : {skipped or 'none'}
""")


if __name__ == "__main__":
    main()
