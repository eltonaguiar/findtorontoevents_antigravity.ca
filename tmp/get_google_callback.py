#!/usr/bin/env python3
import ftplib
from io import BytesIO

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

ftp = ftplib.FTP(FTP_HOST, timeout=15)
ftp.login(FTP_USER, FTP_PASS)

buf = BytesIO()
ftp.retrbinary("RETR /fc/api/google_callback.php", buf.write)
print(buf.getvalue().decode("utf-8"))
ftp.quit()
