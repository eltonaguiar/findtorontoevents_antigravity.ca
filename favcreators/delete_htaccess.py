import ftplib

ftp = ftplib.FTP_TLS()
ftp.connect('ftps2.50webs.com', 21, timeout=30)
# Use raw string to handle special characters
ftp.login('ejaguiar1', '$a^FzN7BqKapSQMsZxD&^FeTJ')
ftp.prot_p()
print("Logged in successfully")

try:
    ftp.delete('/findtorontoevents.ca/fc/api/.htaccess')
    print('Deleted .htaccess successfully')
except Exception as e:
    print(f'Error deleting: {e}')

ftp.quit()