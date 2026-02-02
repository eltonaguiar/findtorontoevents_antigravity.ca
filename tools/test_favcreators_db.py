#!/usr/bin/env python3
"""
Test FavCreators database (ejaguiar1_favcreators) using environment variables.

Required env vars:
  MYSQL_HOST       e.g. localhost or your host's MySQL hostname
  MYSQL_USER       e.g. ejaguiar1_favcreators
  MYSQL_PASSWORD   DB password
  MYSQL_DATABASE   e.g. ejaguiar1_favcreators

Optional:
  MYSQL_PORT       default 3306

Load from .env: set MYSQL_* in favcreators/server/.env or project root .env
and install python-dotenv (pip install python-dotenv); or export vars in shell.

Install: pip install pymysql
Run from project root: python tools/test_favcreators_db.py
  python tools/test_favcreators_db.py --insert-test   # add a test note (creator_id 6) so app can retrieve it
"""
import argparse
import os
import sys
from pathlib import Path

# Optional: load .env from tools/, favcreators/server/, or project root
_script_dir = Path(__file__).resolve().parent
_root = _script_dir.parent
for _env_path in (
    _script_dir / ".env",
    _root / "favcreators" / "server" / ".env",
    _root / ".env",
):
    if _env_path.is_file():
        try:
            from dotenv import load_dotenv
            load_dotenv(_env_path)
            break
        except ImportError:
            break

def main():
    parser = argparse.ArgumentParser(description="Test FavCreators DB (ejaguiar1_favcreators)")
    parser.add_argument("--insert-test", action="store_true", help="Insert a test note for creator_id 6 (Starfireara) so the app can retrieve it")
    args = parser.parse_args()

    host = os.environ.get("MYSQL_HOST")
    user = os.environ.get("MYSQL_USER")
    password = os.environ.get("MYSQL_PASSWORD")
    database = os.environ.get("MYSQL_DATABASE")
    port = int(os.environ.get("MYSQL_PORT", "3306"))

    missing = [n for n, v in [
        ("MYSQL_HOST", host),
        ("MYSQL_USER", user),
        ("MYSQL_PASSWORD", password),
        ("MYSQL_DATABASE", database),
    ] if not v]
    if missing:
        print("Missing env vars:", ", ".join(missing))
        print("Set them (or add favcreators/server/.env with MYSQL_*) then run: python tools/test_favcreators_db.py")
        sys.exit(1)

    try:
        import pymysql
    except ImportError:
        print("Install PyMySQL: pip install pymysql")
        sys.exit(1)

    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=10,
        )
    except Exception as e:
        print("DB connection FAILED:", e)
        sys.exit(1)

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        print("DB connection OK:", database, "on", host)

        # Check FavCreators tables
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES LIKE 'creator_defaults'")
            if cur.fetchone():
                cur.execute("SELECT creator_id, LEFT(note, 60) FROM creator_defaults LIMIT 5")
                rows = cur.fetchall()
                if rows:
                    print("creator_defaults:", [r for r in rows])
                else:
                    print("creator_defaults: table empty")
            else:
                print("creator_defaults: table not found (run setup_notes_tables.php on server)")

            cur.execute("SHOW TABLES LIKE 'user_notes'")
            if cur.fetchone():
                cur.execute("SELECT id, user_id, creator_id, LEFT(note, 40), updated_at FROM user_notes ORDER BY id DESC LIMIT 5")
                rows = cur.fetchall()
                print("user_notes (latest 5):", rows if rows else "empty")
            else:
                print("user_notes: table not found")

        # Insert test entry so app can retrieve it (guest sees creator_defaults; get_notes.php?user_id=0)
        if args.insert_test:
            with conn.cursor() as cur:
                # creator_defaults: guest get_notes.php?user_id=0 returns this. Starfireara = creator_id 6.
                cur.execute("""
                    INSERT INTO creator_defaults (creator_id, note) VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE note = VALUES(note)
                """, ("6", "Test note from local script (retrieve in app)"))
                conn.commit()
                print("Inserted/updated creator_defaults for creator_id 6 -> Starfireara. Open app (e.g. /fc/#/guest) to see note.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
