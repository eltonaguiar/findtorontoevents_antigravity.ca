#!/usr/bin/env python3
import ftplib

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

ftp = ftplib.FTP(FTP_HOST, timeout=15)
ftp.login(FTP_USER, FTP_PASS)
for f in ['/fc/api/_dbdiag.php', '/fc/api/_dbdiag2.php', '/fc/api/_dbdiag3.php', '/fc/api/dbstatus.php']:
    try:
        ftp.delete(f)
        print(f'Deleted {f}')
    except Exception as e:
        print(f'Could not delete {f}: {e}')
ftp.quit()
print('Done')
