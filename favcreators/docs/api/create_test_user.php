<?php
/**
 * Create test user johndoe with same data as user 2. Admin only.
 */

header('Content-Type: text/plain; charset=utf-8');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_config.php';
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

echo "=== Creating Test User: johndoe ===\n\n";

// 1. Check if user exists
$check = $conn->query("SELECT id FROM users WHERE email = 'johndoe'");
if ($check && $check->num_rows > 0) {
    $user = $check->fetch_assoc();
    $test_user_id = $user['id'];
    echo "User 'johndoe' already exists with ID: $test_user_id\n";
} else {
    // Create user
    $conn->query("INSERT INTO users (email, password, role, display_name) VALUES ('johndoe', 'johndoe', 'user', 'John Doe')");
    $test_user_id = $conn->insert_id;
    echo "Created user 'johndoe' with ID: $test_user_id\n";
}

// 2. Copy user_lists from user 2
$user2_list = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if ($user2_list && $user2_list->num_rows > 0) {
    $row = $user2_list->fetch_assoc();
    $creators_json = $row['creators'];
    $creators_json_esc = $conn->real_escape_string($creators_json);

    // Delete existing list for test user
    $conn->query("DELETE FROM user_lists WHERE user_id = $test_user_id");

    // Insert new list
    $conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($test_user_id, '$creators_json_esc')");

    $creators = json_decode($creators_json, true);
    $count = is_array($creators) ? count($creators) : 0;
    echo "Copied $count creators from user 2 to johndoe\n";
} else {
    echo "ERROR: Could not find user 2's creator list!\n";
}

// 3. Copy user_notes from user 2
$user2_notes = $conn->query("SELECT creator_id, note FROM user_notes WHERE user_id = 2");
if ($user2_notes) {
    // Delete existing notes
    $conn->query("DELETE FROM user_notes WHERE user_id = $test_user_id");

    $note_count = 0;
    while ($note = $user2_notes->fetch_assoc()) {
        $creator_id = $conn->real_escape_string($note['creator_id']);
        $note_text = $conn->real_escape_string($note['note']);
        $conn->query("INSERT INTO user_notes (user_id, creator_id, note) VALUES ($test_user_id, '$creator_id', '$note_text')");
        $note_count++;
    }
    echo "Copied $note_count notes from user 2 to johndoe\n";
}

// 4. Copy user_secondary_notes from user 2
$user2_secondary = $conn->query("SELECT creator_id, secondary_note FROM user_secondary_notes WHERE user_id = 2");
if ($user2_secondary) {
    // Delete existing secondary notes
    $conn->query("DELETE FROM user_secondary_notes WHERE user_id = $test_user_id");

    $sec_count = 0;
    while ($sec = $user2_secondary->fetch_assoc()) {
        $creator_id = $conn->real_escape_string($sec['creator_id']);
        $sec_note = $conn->real_escape_string($sec['secondary_note']);
        $conn->query("INSERT INTO user_secondary_notes (user_id, creator_id, secondary_note) VALUES ($test_user_id, '$creator_id', '$sec_note')");
        $sec_count++;
    }
    echo "Copied $sec_count secondary notes from user 2 to johndoe\n";
}

echo "\n=== Test User Ready ===\n";
echo "Login at: https://findtorontoevents.ca/fc/\n";
echo "Email: johndoe\n";
echo "Password: johndoe\n";

$conn->close();
?>