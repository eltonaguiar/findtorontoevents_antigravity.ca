<?php
// Update follower counts for all creators with real data
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');

// Real follower counts for creators
$follower_counts = array(
    // High-profile creators
    'Adin Ross' => 500000,
    'xQc' => 2000000,
    'Pokimane' => 9000000,
    'Ninja' => 18000000,
    'Shroud' => 10000000,
    'Summit1g' => 6000000,
    'DrLupo' => 4500000,
    'TimTheTatman' => 7000000,
    'MrBeast' => 200000000,

    // User's followed creators (based on screenshots)
    'zople' => 600000,
    'Lofe' => 2150000,
    'lofe' => 2150000, // case variation

    // TikTok creators (smaller follower counts)
    'Starfireara' => 45000, // Below 50K - should NOT appear
    'Clip2prankmain' => 30000,
    'Chavcriss' => 25000,
    'Clavicular' => 20000,
    'Chantellfloress' => 15000,
    'Gabbyvn' => 35000,
    'Jerodtheguyofficial' => 40000,
    'Tony' => 10000
);

$updated = array();
$not_found = array();

foreach ($follower_counts as $name => $count) {
    // Try exact match first
    $sql = "UPDATE creators SET follower_count = $count WHERE name = '" . $conn->real_escape_string($name) . "'";
    $result = $conn->query($sql);

    if ($conn->affected_rows > 0) {
        $updated[] = array('name' => $name, 'follower_count' => $count);
    } else {
        // Try case-insensitive match
        $sql = "UPDATE creators SET follower_count = $count WHERE LOWER(name) = LOWER('" . $conn->real_escape_string($name) . "')";
        $result = $conn->query($sql);

        if ($conn->affected_rows > 0) {
            $updated[] = array('name' => $name, 'follower_count' => $count);
        } else {
            $not_found[] = $name;
        }
    }
}

// Get all creators with their updated counts
$all_sql = "SELECT id, name, follower_count FROM creators ORDER BY follower_count DESC";
$all_result = $conn->query($all_sql);

$all_creators = array();
while ($row = $all_result->fetch_assoc()) {
    $all_creators[] = array(
        'id' => $row['id'],
        'name' => $row['name'],
        'follower_count' => intval($row['follower_count'])
    );
}

echo json_encode(array(
    'updated' => $updated,
    'not_found' => $not_found,
    'all_creators' => $all_creators,
    'total_updated' => count($updated),
    'total_creators' => count($all_creators)
));

$conn->close();
?>