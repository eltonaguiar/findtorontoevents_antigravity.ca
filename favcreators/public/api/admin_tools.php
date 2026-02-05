<?php
/**
 * Simple admin page to run backfill and check system status
 * Access: https://findtorontoevents.ca/fc/api/admin_tools.php
 * Login with admin/admin first
 */

session_start();
$is_admin = false;
if (isset($_SESSION['user']) && isset($_SESSION['user']['role'])) {
    $is_admin = $_SESSION['user']['role'] === 'admin';
} elseif (isset($_SESSION['user']) && isset($_SESSION['user']['provider'])) {
    $is_admin = $_SESSION['user']['provider'] === 'admin';
}

if (!$is_admin) {
    die("Unauthorized - admin only. Please login at /fc/ with admin/admin first.");
}

require_once dirname(__FILE__) . '/db_config.php';
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

$action = isset($_GET['action']) ? $_GET['action'] : '';
$output = '';

if ($action === 'backfill') {
    $output .= "=== Backfill Guest List to Existing Users ===\n\n";

    // Get guest list
    $guest_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
    if (!$guest_query || $guest_query->num_rows === 0) {
        $output .= "ERROR: No guest list found (user_id=0).\n";
    } else {
        $guest_row = $guest_query->fetch_assoc();
        $guest_creators = $guest_row['creators'];
        $guest_creators_esc = $conn->real_escape_string($guest_creators);

        $guest_data = json_decode($guest_creators, true);
        $guest_count = is_array($guest_data) ? count($guest_data) : 0;

        $output .= "Guest list contains $guest_count creators.\n\n";

        // Get all users
        $users_query = $conn->query("SELECT id, email, display_name FROM users WHERE role != 'admin'");
        if (!$users_query) {
            $output .= "ERROR: Could not fetch users: " . $conn->error . "\n";
        } else {
            $total_users = $users_query->num_rows;
            $output .= "Found $total_users users to process.\n\n";

            $updated = 0;
            $skipped = 0;

            while ($user = $users_query->fetch_assoc()) {
                $user_id = (int) $user['id'];
                $email = $user['email'];

                // Check if user already has a list
                $check = $conn->query("SELECT user_id FROM user_lists WHERE user_id = $user_id");
                if ($check && $check->num_rows > 0) {
                    $output .= "  [SKIP] User $user_id ($email) already has a list.\n";
                    $skipped++;
                    continue;
                }

                // Copy guest list
                $insert = $conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($user_id, '$guest_creators_esc')");
                if ($insert) {
                    $output .= "  [OK] Copied guest list to user $user_id ($email).\n";
                    $updated++;
                } else {
                    $output .= "  [ERROR] Failed for user $user_id: " . $conn->error . "\n";
                }
            }

            $output .= "\n=== Summary ===\n";
            $output .= "Total users: $total_users\n";
            $output .= "Updated: $updated\n";
            $output .= "Skipped: $skipped\n";
        }
    }
} elseif ($action === 'check_tables') {
    $output .= "=== Database Tables Check ===\n\n";

    $tables = array('users', 'user_lists', 'creators', 'favcreatorslogs', 'creator_defaults', 'user_notes');
    foreach ($tables as $table) {
        $result = $conn->query("SHOW TABLES LIKE '$table'");
        if ($result && $result->num_rows > 0) {
            $count_result = $conn->query("SELECT COUNT(*) as cnt FROM $table");
            $count = 0;
            if ($count_result) {
                $row = $count_result->fetch_assoc();
                $count = $row['cnt'];
            }
            $output .= "✓ $table exists ($count rows)\n";
        } else {
            $output .= "✗ $table MISSING\n";
        }
    }
} elseif ($action === 'check_user2') {
    $output .= "=== Check User ID 2 (zerounderscore@gmail.com) ===\n\n";

    // Check user_lists
    $result = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
    if ($result && $result->num_rows > 0) {
        $row = $result->fetch_assoc();
        $creators = json_decode($row['creators'], true);
        $count = is_array($creators) ? count($creators) : 0;
        $output .= "User 2 has $count creators in their list.\n";

        // Check for brunitarte
        $has_brunitarte = false;
        if (is_array($creators)) {
            foreach ($creators as $creator) {
                if (isset($creator['name']) && stripos($creator['name'], 'brunitarte') !== false) {
                    $has_brunitarte = true;
                    $output .= "✓ Found Brunitarte in list!\n";
                    $output .= "  ID: " . (isset($creator['id']) ? $creator['id'] : 'N/A') . "\n";
                    $output .= "  Name: " . $creator['name'] . "\n";
                    break;
                }
                if (isset($creator['id']) && stripos($creator['id'], 'brunitarte') !== false) {
                    $has_brunitarte = true;
                    $output .= "✓ Found Brunitarte in list (by ID)!\n";
                    break;
                }
            }
        }
        if (!$has_brunitarte) {
            $output .= "✗ Brunitarte NOT found in user 2's list.\n";
        }
    } else {
        $output .= "✗ User 2 has NO creator list!\n";
    }
}

$conn->close();
?>
<!DOCTYPE html>
<html>

<head>
    <title>FavCreators Admin Tools</title>
    <style>
        body {
            font-family: monospace;
            padding: 20px;
            background: #1e1e1e;
            color: #d4d4d4;
        }

        h1 {
            color: #4ec9b0;
        }

        .btn {
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            background: #0e639c;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }

        .btn:hover {
            background: #1177bb;
        }

        pre {
            background: #252526;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
        }

        .success {
            color: #4ec9b0;
        }

        .error {
            color: #f48771;
        }
    </style>
</head>

<body>
    <h1>🔧 FavCreators Admin Tools</h1>

    <div>
        <a href="?action=check_tables" class="btn">Check Tables</a>
        <a href="?action=check_user2" class="btn">Check User 2</a>
        <a href="?action=backfill" class="btn">Run Backfill</a>
        <a href="/fc/" class="btn">Back to FavCreators</a>
    </div>

    <?php if ($output): ?>
        <h2>Output:</h2>
        <pre><?php echo htmlspecialchars($output); ?></pre>
    <?php else: ?>
        <p>Select an action above.</p>
    <?php endif; ?>
</body>

</html>