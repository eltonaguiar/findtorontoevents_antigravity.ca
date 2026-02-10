"""Deploy a single file to FTP production."""
import ftplib
import ssl

SERVER = "ftps2.50webs.com"
USER = "ejaguiar1"
PASS = r"$a^FzN7BqKapSQMsZxD&^FeTJ"

LOCAL = r"e:/findtorontoevents_antigravity.ca/findstocks/index.html"
REMOTE = "/findtorontoevents.ca/findstocks/index.html"

def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    ftp = ftplib.FTP_TLS(context=ctx)
    ftp.connect(SERVER, 21)
    ftp.login(USER, PASS)
    ftp.prot_p()
    print("Connected and secured.")

    remote_dir = "/findtorontoevents.ca/findstocks"
    try:
        ftp.mkd(remote_dir)
        print(f"Created directory: {remote_dir}")
    except ftplib.error_perm:
        print(f"Directory already exists: {remote_dir}")

    with open(LOCAL, "rb") as f:
        ftp.storbinary(f"STOR {REMOTE}", f)
    print(f"Uploaded: {LOCAL} -> {REMOTE}")

    ftp.quit()
    print("Done.")

if __name__ == "__main__":
    main()
