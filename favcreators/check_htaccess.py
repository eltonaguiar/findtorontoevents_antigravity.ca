import ftplib

ftp = ftplib.FTP_TLS()
ftp.connect('ftps2.50webs.com', 21, timeout=30)
ftp.login('ejaguiar1', '$a^FzN7BqKapSQMsZxD&^FeTJ')
ftp.prot_p()

# Check for .htaccess files in parent directories
paths = [
    '/findtorontoevents.ca/.htaccess',
    '/findtorontoevents.ca/fc/.htaccess', 
    '/findtorontoevents.ca/fc/public/.htaccess',
    '/findtorontoevents.ca/fc/public/api/.htaccess'
]

for path in paths:
    try:
        size = ftp.size(path)
        print(f'{path}: EXISTS ({size} bytes)')
    except Exception as e:
        print(f'{path}: NOT FOUND ({e})')

ftp.quit()