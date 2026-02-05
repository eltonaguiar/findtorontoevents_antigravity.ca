import ftplib

ftp = ftplib.FTP_TLS()
ftp.connect('ftps2.50webs.com', 21, timeout=30)
ftp.login('ejaguiar1', '$a^FzN7BqKapSQMsZxD&^FeTJ')
ftp.prot_p()

# Download root .htaccess
with open('root_htaccess.txt', 'wb') as f:
    ftp.retrbinary('RETR /findtorontoevents.ca/.htaccess', f.write)

print("Downloaded root .htaccess to root_htaccess.txt")

ftp.quit()