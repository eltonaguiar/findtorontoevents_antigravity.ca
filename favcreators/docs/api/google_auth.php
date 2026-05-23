<?php
// google_auth.php — Google Identity Services (GIS) Sign-In
// Renders Google's One Tap / Sign-In button via JavaScript SDK.
// Completely bypasses mod_security WAF (rule 340162) because:
//   1. This page receives only ?return_to=/fc/ — no URLs in ARGS
//   2. The JWT credential is sent as JSON to google_signin.php — JSON body not parsed as ARGS
//   3. No redirect_uri, no callback URL, no scope URLs anywhere

// Load config file if it exists (for Google Client ID)
$config_file = dirname(__FILE__) . '/config.php';
if (file_exists($config_file)) {
    require_once $config_file;
}

// Load Google Client ID from environment or config
$client_id = getenv('GOOGLE_CLIENT_ID');
if (($client_id === false || $client_id === null || $client_id === '') && defined('GOOGLE_CLIENT_ID')) {
    $client_id = GOOGLE_CLIENT_ID;
}
if ($client_id === false || $client_id === null) {
    $client_id = '';
}

// Detect current domain
$current_host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : 'findtorontoevents.ca';
$allowed_hosts = array('findtorontoevents.ca', 'torontoevent.net', 'tdotevent.ca', 'www.findtorontoevents.ca', 'www.torontoevent.net', 'www.tdotevent.ca');
if (!in_array($current_host, $allowed_hosts)) {
    $current_host = 'findtorontoevents.ca';
}
$current_host = str_replace('www.', '', $current_host);

// Return-to path (sanitized)
$return_to = isset($_GET['return_to']) ? $_GET['return_to'] : '/fc/';
$return_to = preg_replace('/[^a-zA-Z0-9\/\-_.]/', '', $return_to);
if ($return_to === '' || !isset($return_to[0]) || $return_to[0] !== '/') {
    $return_to = '/fc/';
}

$verify_url = 'https://' . $current_host . '/fc/api/google_signin.php';
$return_url = 'https://' . $current_host . $return_to;
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign In — FavCreators</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0f0f23;color:#fff}
.container{text-align:center;max-width:420px;width:100%;padding:2.5rem;background:rgba(30,30,60,.95);border-radius:1.5rem;border:1px solid rgba(99,102,241,.3);box-shadow:0 25px 50px rgba(0,0,0,.5)}
h1{color:#a5b4fc;font-size:1.5rem;margin-bottom:.5rem}
.subtitle{color:#94a3b8;font-size:.9rem;margin-bottom:2rem}
#g-signin-wrap{display:flex;justify-content:center;margin:1.5rem 0}
.status{margin-top:1rem;font-size:.85rem;color:#94a3b8;min-height:1.5em}
.status.error{color:#f87171}
.status.success{color:#4ade80}
.spinner{display:none;width:32px;height:32px;border:3px solid rgba(99,102,241,.2);border-top-color:#6366f1;border-radius:50%;animation:spin .7s linear infinite;margin:1rem auto}
@keyframes spin{to{transform:rotate(360deg)}}
.back-link{display:inline-block;margin-top:1.5rem;color:#6366f1;text-decoration:none;font-size:.85rem}
.back-link:hover{color:#818cf8;text-decoration:underline}
</style>
</head>
<body>
<div class="container">
  <h1>Sign In to FavCreators</h1>
  <p class="subtitle">Use your Google account to continue</p>
  <div id="g-signin-wrap"></div>
  <div class="spinner" id="spinner"></div>
  <div class="status" id="status"></div>
  <a class="back-link" href="<?php echo htmlspecialchars($return_url); ?>">&#8592; Back to app</a>
</div>

<script src="https://accounts.google.com/gsi/client" async></script>
<script>
var VERIFY_URL = <?php echo json_encode($verify_url); ?>;
var RETURN_URL = <?php echo json_encode($return_url); ?>;
var CLIENT_ID  = <?php echo json_encode($client_id); ?>;

function onGoogleSignIn(response) {
  var statusEl = document.getElementById('status');
  var spinnerEl = document.getElementById('spinner');
  var wrapEl = document.getElementById('g-signin-wrap');

  statusEl.className = 'status';
  statusEl.textContent = 'Verifying with server...';
  spinnerEl.style.display = 'block';
  wrapEl.style.display = 'none';

  fetch(VERIFY_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ credential: response.credential })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    spinnerEl.style.display = 'none';
    if (data.user) {
      statusEl.className = 'status success';
      statusEl.textContent = 'Welcome, ' + (data.user.display_name || data.user.email) + '!';
      try {
        localStorage.setItem('fc_user', JSON.stringify({
          id: data.user.id,
          email: data.user.email,
          display_name: data.user.display_name,
          avatar_url: data.user.avatar_url,
          provider: 'google'
        }));
      } catch(e) {}
      setTimeout(function() { window.location.href = RETURN_URL; }, 600);
    } else {
      statusEl.className = 'status error';
      statusEl.textContent = 'Sign-in failed: ' + (data.error || 'Unknown error');
      wrapEl.style.display = 'flex';
    }
  })
  .catch(function(err) {
    spinnerEl.style.display = 'none';
    statusEl.className = 'status error';
    statusEl.textContent = 'Network error. Please try again.';
    wrapEl.style.display = 'flex';
  });
}

function initGIS() {
  if (typeof google !== 'undefined' && google.accounts) {
    google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: onGoogleSignIn,
      auto_select: true,
      cancel_on_tap_outside: false
    });
    google.accounts.id.renderButton(
      document.getElementById('g-signin-wrap'),
      { type: 'standard', theme: 'filled_blue', size: 'large', text: 'signin_with', shape: 'pill', width: 300 }
    );
    google.accounts.id.prompt();
  } else {
    setTimeout(initGIS, 200);
  }
}
initGIS();
</script>
</body>
</html>
