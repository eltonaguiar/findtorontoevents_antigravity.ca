#!/usr/bin/env python
"""Add briannasumba to user_id=2's creators list and output updated SQL."""
import re
import json
import time

# Read the SQL file
with open('ejaguiar1_favcreators.sql', 'r', encoding='utf-8') as f:
    content = f.read()

# Find user_id=2's INSERT line
lines = content.split('\n')
user2_line_idx = None
user2_line = None
for i, line in enumerate(lines):
    if line.startswith("(2, '["):
        user2_line_idx = i
        user2_line = line
        break

if not user2_line:
    print("Could not find user_id=2 data")
    exit(1)

# Extract the JSON blob
match = re.match(r"\(2, '(.+)', '(\d{4}-\d{2}-\d{2}[^']*)'", user2_line)
if not match:
    print("Could not parse user_id=2 line")
    exit(1)

json_str = match.group(1)
timestamp = match.group(2)

# Unescape the JSON
json_str = json_str.replace('\\"', '"')
json_str = json_str.replace("\\/", "/")
json_str = json_str.replace("\\'", "'")
json_str = json_str.replace("\\\\", "\\")

creators = json.loads(json_str)
print(f"Current creators: {len(creators)}")

# Check if briannasumba already exists
for c in creators:
    name = c.get('name', '').lower()
    if 'brianna' in name or 'sumba' in name:
        print("briannasumba already exists!")
        exit(0)

# Add briannasumba
briannasumba = {
    "id": f"briannasumba-tiktok-{int(time.time())}",
    "name": "Briannasumba",
    "bio": "TikTok creator",
    "avatarUrl": "",
    "category": "Other",
    "reason": "",
    "tags": [],
    "accounts": [
        {
            "id": "briannasumba-tiktok-acc",
            "platform": "tiktok",
            "username": "briannasumba",
            "url": "https://www.tiktok.com/@briannasumba",
            "isLive": False,
            "checkLive": True,
            "lastChecked": int(time.time() * 1000)
        }
    ],
    "isFavorite": False,
    "isPinned": False,
    "note": "",
    "addedAt": int(time.time() * 1000),
    "lastChecked": 0
}

creators.append(briannasumba)
print(f"Added briannasumba. New total: {len(creators)}")

# Re-escape for SQL
new_json = json.dumps(creators)
new_json = new_json.replace("\\", "\\\\")
new_json = new_json.replace("'", "\\'")
new_json = new_json.replace("/", "\\/")
new_json = new_json.replace('"', '\\"')

# Create the UPDATE statement
update_sql = f"""-- Add briannasumba to user_id=2
UPDATE user_lists 
SET creators = '{new_json}', updated_at = NOW()
WHERE user_id = 2;
"""

# Write the SQL update
with open('add_briannasumba.sql', 'w', encoding='utf-8') as f:
    f.write(update_sql)

print("\nGenerated add_briannasumba.sql")
print("You can run this in phpMyAdmin to update the database")

# Also output a PHP API endpoint to do it
php_content = '''<?php
/**
 * One-time script to add briannasumba to user_id=2's list
 * DELETE THIS FILE AFTER USE
 */
header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    die(json_encode(array('error' => 'Database not available')));
}

// Get current list
$q = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if (!$q || $q->num_rows === 0) {
    die(json_encode(array('error' => 'No user_id=2 record')));
}

$row = $q->fetch_assoc();
$creators = json_decode($row['creators'], true);

if (!is_array($creators)) {
    die(json_encode(array('error' => 'JSON decode failed')));
}

// Check if already exists
foreach ($creators as $c) {
    $name = strtolower($c['name'] ?? '');
    if (strpos($name, 'brianna') !== false || strpos($name, 'sumba') !== false) {
        echo json_encode(array('status' => 'already_exists', 'total' => count($creators)));
        exit;
    }
}

// Add briannasumba
$briannasumba = array(
    'id' => 'briannasumba-tiktok-' . time(),
    'name' => 'Briannasumba', 
    'bio' => 'TikTok creator',
    'avatarUrl' => '',
    'category' => 'Other',
    'reason' => '',
    'tags' => array(),
    'accounts' => array(
        array(
            'id' => 'briannasumba-tiktok-acc',
            'platform' => 'tiktok',
            'username' => 'briannasumba',
            'url' => 'https://www.tiktok.com/@briannasumba',
            'isLive' => false,
            'checkLive' => true,
            'lastChecked' => time() * 1000
        )
    ),
    'isFavorite' => false,
    'isPinned' => false,
    'note' => '',
    'addedAt' => time() * 1000,
    'lastChecked' => 0
);

$creators[] = $briannasumba;

// Save
$json = json_encode($creators);
$escaped = $conn->real_escape_string($json);
$update = $conn->query("UPDATE user_lists SET creators = '$escaped', updated_at = NOW() WHERE user_id = 2");

if ($update) {
    echo json_encode(array(
        'status' => 'added',
        'total' => count($creators),
        'added' => 'Briannasumba'
    ));
} else {
    echo json_encode(array('error' => 'Update failed: ' . $conn->error));
}

$conn->close();
?>
'''

with open('favcreators/public/api/add_briannasumba.php', 'w', encoding='utf-8') as f:
    f.write(php_content)

print("Generated favcreators/public/api/add_briannasumba.php")
print("\nTo add briannasumba:")
print("1. Deploy: python tools/deploy_to_ftp.py --include favcreators/public/api/add_briannasumba.php")
print("2. Call: curl https://findtorontoevents.ca/fc/api/add_briannasumba.php")
