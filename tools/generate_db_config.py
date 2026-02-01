import os

def generate_config():
    # Priority: DB_PASS -> FTP_PASS
    db_pass = os.environ.get('DB_PASS')
    ftp_pass = os.environ.get('FTP_PASS')
    
    final_pass = db_pass if db_pass else ftp_pass
    
    if not final_pass:
        print("ERROR: No password found in env vars DB_PASS or FTP_PASS")
        return

    # PHP String Escaping for Single Quoted String
    # 1. Backslash -> Double Backslash
    # 2. Single Quote -> Backslash Single Quote
    safe_pass = final_pass.replace('\\', '\\\\').replace("'", "\\'")
    
    php_content = f"""<?php
$servername = "localhost";
$username = "ejaguiar1_favcreators";
$password = '{safe_pass}';
$dbname = "ejaguiar1_favcreators";
?>"""

    output_path = 'favcreators/public/api/db_config.php'
    with open(output_path, 'w') as f:
        f.write(php_content)
        
    print(f"Successfully generated {output_path}")
    print(f"Password Length: {len(final_pass)}")
    print(f"Password starts with: {final_pass[:2]}...") # Safety check in logs

if __name__ == "__main__":
    generate_config()
