<?php
// config.php - Local configuration (COPY THIS FILE to config.php and fill in your credentials)
// DO NOT commit config.php to GitHub - it contains sensitive secrets!

// Google OAuth Credentials
// Get these from https://console.cloud.google.com/apis/credentials
define('GOOGLE_CLIENT_ID', '975574174292-n332bled0ud1bc51v1hcqpnmp8dass12.apps.googleusercontent.com');
define('GOOGLE_CLIENT_SECRET', 'YOUR_CLIENT_SECRET_HERE'); // <-- Fill in your Client Secret

// Database credentials (if needed)
define('DB_HOST', 'mysql.50webs.com');
define('DB_USER', 'ejaguiar1_favcreators');
define('DB_PASS', ''); // <-- Fill in if not using env var
define('DB_NAME', 'ejaguiar1_favcreators');
?>
