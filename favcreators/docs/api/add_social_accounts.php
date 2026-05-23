<?php
/**
 * Add social media accounts to all user_id=2 creators who are missing them
 */

header('Content-Type: text/plain; charset=utf-8');
echo "Adding social media accounts to all creators...\n\n";

require_once dirname(__FILE__) . '/db_connect.php';

if (!isset($conn) || !$conn) {
    die("ERROR: Database not available\n");
}

// Helper function to normalize username
function normalizeUsername($name) {
    // Convert to lowercase, remove special chars
    $username = strtolower(trim($name));
    $username = preg_replace('/[^a-z0-9._]/', '', $username);
    return $username;
}

// Helper to guess username variations
function getUsernameVariations($name) {
    $variations = array();
    $base = strtolower(trim($name));
    
    // Remove spaces and special chars
    $clean = preg_replace('/[^a-z0-9]/', '', $base);
    $variations[] = $clean;
    
    // With underscores for spaces
    $underscored = str_replace(' ', '_', $base);
    $variations[] = preg_replace('/[^a-z0-9._]/', '', $underscored);
    
    // Just first word
    $parts = explode(' ', $base);
    if (count($parts) > 1) {
        $variations[] = $parts[0];
    }
    
    return array_unique(array_filter($variations));
}

// Comprehensive social media mappings for each creator
$social_mappings = array(
    'Tony Robbins' => array(
        array('platform' => 'youtube', 'username' => 'tonyrobbinslive'),
        array('platform' => 'instagram', 'username' => 'tonyrobbins'),
        array('platform' => 'tiktok', 'username' => 'tonyrobbins'),
    ),
    'Chantellfloress' => array(
        array('platform' => 'tiktok', 'username' => 'chantellfloress'),
        array('platform' => 'instagram', 'username' => 'chantellfloress'),
    ),
    'WTFPreston' => array(
        array('platform' => 'youtube', 'username' => 'wtfprestonlive'),
        array('platform' => 'tiktok', 'username' => 'wtfprestonlive'),
        array('platform' => 'kick', 'username' => 'wtfpreston'),
    ),
    'Clavicular' => array(
        array('platform' => 'twitch', 'username' => 'clavicular'),
        array('platform' => 'kick', 'username' => 'clavicular'),
        array('platform' => 'youtube', 'username' => 'clavicular'),
    ),
    'The Benji Show' => array(
        array('platform' => 'tiktok', 'username' => 'thebenjishow'),
        array('platform' => 'youtube', 'username' => 'thebenjishow'),
        array('platform' => 'instagram', 'username' => 'thebenjishow'),
    ),
    'Zarthestar' => array(
        array('platform' => 'twitch', 'username' => 'zarthestar'),
        array('platform' => 'youtube', 'username' => 'zarthestarcomedy'),
        array('platform' => 'tiktok', 'username' => 'zarthestar'),
    ),
    'Adin Ross' => array(
        array('platform' => 'kick', 'username' => 'adinross'),
        array('platform' => 'youtube', 'username' => 'adinross'),
        array('platform' => 'instagram', 'username' => 'adinross'),
    ),
    'Starfireara' => array(
        array('platform' => 'tiktok', 'username' => 'starfireara'),
        array('platform' => 'instagram', 'username' => 'starfireara'),
    ),
    'Chavcriss' => array(
        array('platform' => 'youtube', 'username' => 'chavcriss'),
        array('platform' => 'tiktok', 'username' => 'chavcriss'),
        array('platform' => 'instagram', 'username' => 'chavcriss'),
    ),
    'Jubal Fresh' => array(
        array('platform' => 'youtube', 'username' => 'jubalfresh'),
        array('platform' => 'instagram', 'username' => 'jubalfresh'),
        array('platform' => 'tiktok', 'username' => 'jubalfresh'),
    ),
    'Brooke & Jeffrey' => array(
        array('platform' => 'youtube', 'username' => 'brookeandjeffrey'),
        array('platform' => 'instagram', 'username' => 'brookeandjeffrey'),
    ),
    'Clip2prankmain' => array(
        array('platform' => 'tiktok', 'username' => 'clip2prankmain'),
        array('platform' => 'youtube', 'username' => 'clip2prankmain'),
        array('platform' => 'instagram', 'username' => 'clip2prankmain'),
    ),
    'Hasanabi' => array(
        array('platform' => 'youtube', 'username' => 'hasanabi'),
        array('platform' => 'twitch', 'username' => 'hasanabi'),
        array('platform' => 'instagram', 'username' => 'hasandpiker'),
    ),
    'Stableronaldo' => array(
        array('platform' => 'youtube', 'username' => 'stableronaldo'),
        array('platform' => 'tiktok', 'username' => 'stableronaldo'),
        array('platform' => 'instagram', 'username' => 'stableronaldo'),
    ),
    'Jasontheween' => array(
        array('platform' => 'youtube', 'username' => 'jasontheween'),
        array('platform' => 'tiktok', 'username' => 'jasontheween'),
        array('platform' => 'instagram', 'username' => 'jasontheween'),
    ),
    'Shabellow' => array(
        array('platform' => 'tiktok', 'username' => 'shabellow'),
        array('platform' => 'youtube', 'username' => 'shabellow'),
        array('platform' => 'instagram', 'username' => 'shabellow'),
    ),
    'Nelkboys' => array(
        array('platform' => 'youtube', 'username' => 'nelkboys'),
        array('platform' => 'instagram', 'username' => 'nelkboys'),
        array('platform' => 'tiktok', 'username' => 'nelkboys'),
    ),
    'Pokimane' => array(
        array('platform' => 'twitch', 'username' => 'pokimane'),
        array('platform' => 'youtube', 'username' => 'pokimane'),
        array('platform' => 'instagram', 'username' => 'pokimanelol'),
    ),
    'Seherrrizvii' => array(
        array('platform' => 'tiktok', 'username' => 'seherrrizvii'),
        array('platform' => 'instagram', 'username' => 'seherrrizvii'),
    ),
    'Lofe' => array(
        array('platform' => 'youtube', 'username' => 'lofe'),
        array('platform' => 'tiktok', 'username' => 'lofe'),
        array('platform' => 'instagram', 'username' => 'lofe'),
    ),
    'Rajneetkk' => array(
        array('platform' => 'tiktok', 'username' => 'rajneetkk'),
        array('platform' => 'instagram', 'username' => 'rajneetkk'),
    ),
    'Jerodtheguyofficial' => array(
        array('platform' => 'tiktok', 'username' => 'jerodtheguyofficial'),
        array('platform' => 'instagram', 'username' => 'jerodtheguyofficial'),
    ),
    'Saruuuhhhh' => array(
        array('platform' => 'tiktok', 'username' => 'saruuuhhhh'),
        array('platform' => 'instagram', 'username' => 'saruuuhhhh'),
    ),
    'Abz' => array(
        array('platform' => 'tiktok', 'username' => 'abz'),
        array('platform' => 'youtube', 'username' => 'abz'),
        array('platform' => 'instagram', 'username' => 'abz'),
    ),
    'Zherka' => array(
        array('platform' => 'youtube', 'username' => 'zherka'),
        array('platform' => 'tiktok', 'username' => 'zherka'),
        array('platform' => 'instagram', 'username' => 'zherka'),
    ),
    'Orientgent' => array(
        array('platform' => 'tiktok', 'username' => 'orientgent'),
        array('platform' => 'instagram', 'username' => 'orientgent'),
    ),
    'A.r.a.moore' => array(
        array('platform' => 'tiktok', 'username' => 'a.r.a.moore'),
        array('platform' => 'instagram', 'username' => 'a.r.a.moore'),
    ),
    'Lolalocaaaa' => array(
        array('platform' => 'tiktok', 'username' => 'lolalocaaaa'),
        array('platform' => 'instagram', 'username' => 'lolalocaaaa'),
    ),
    'Khadija.mx_' => array(
        array('platform' => 'tiktok', 'username' => 'khadija.mx_'),
        array('platform' => 'instagram', 'username' => 'khadija.mx_'),
    ),
    'Dantes' => array(
        array('platform' => 'youtube', 'username' => 'dantes'),
        array('platform' => 'twitch', 'username' => 'dantes'),
        array('platform' => 'tiktok', 'username' => 'dantes'),
    ),
    'Fredbeyer' => array(
        array('platform' => 'tiktok', 'username' => 'fredbeyer'),
        array('platform' => 'instagram', 'username' => 'fredbeyer'),
    ),
    'Zople' => array(
        array('platform' => 'tiktok', 'username' => 'zople'),
        array('platform' => 'instagram', 'username' => 'zople'),
    ),
    'Ninja' => array(
        array('platform' => 'youtube', 'username' => 'ninja'),
        array('platform' => 'twitch', 'username' => 'ninja'),
        array('platform' => 'instagram', 'username' => 'ninja'),
    ),
    'Nazakanawaki' => array(
        array('platform' => 'tiktok', 'username' => 'nazakanawaki'),
        array('platform' => 'instagram', 'username' => 'nazakanawaki'),
    ),
    'Nevsrealm' => array(
        array('platform' => 'tiktok', 'username' => 'nevsrealm'),
        array('platform' => 'instagram', 'username' => 'nevsrealm'),
    ),
    'Alkvlogs' => array(
        array('platform' => 'tiktok', 'username' => 'alkvlogs'),
        array('platform' => 'youtube', 'username' => 'alkvlogs'),
        array('platform' => 'instagram', 'username' => 'alkvlogs'),
    ),
    'Cuffem' => array(
        array('platform' => 'youtube', 'username' => 'cuffem'),
        array('platform' => 'tiktok', 'username' => 'cuffem'),
        array('platform' => 'instagram', 'username' => 'cuffem'),
    ),
    'Chessur' => array(
        array('platform' => 'youtube', 'username' => 'chessur'),
        array('platform' => 'twitch', 'username' => 'chessur'),
        array('platform' => 'tiktok', 'username' => 'chessur'),
    ),
    'Demisux' => array(
        array('platform' => 'twitch', 'username' => 'demisux'),
        array('platform' => 'youtube', 'username' => 'demisux'),
        array('platform' => 'instagram', 'username' => 'demisux'),
    ),
    'Biancita' => array(
        array('platform' => 'tiktok', 'username' => 'biancita'),
        array('platform' => 'instagram', 'username' => 'biancita'),
    ),
    'Jcelynaa' => array(
        array('platform' => 'tiktok', 'username' => 'jcelynaa'),
        array('platform' => 'instagram', 'username' => 'jcelynaa'),
    ),
    'Honeymoontarot30' => array(
        array('platform' => 'tiktok', 'username' => 'honeymoontarot30'),
        array('platform' => 'instagram', 'username' => 'honeymoontarot30'),
    ),
    'Xqc' => array(
        array('platform' => 'youtube', 'username' => 'xqc'),
        array('platform' => 'twitch', 'username' => 'xqc'),
        array('platform' => 'kick', 'username' => 'xqc'),
    ),
    'Loltyler1' => array(
        array('platform' => 'youtube', 'username' => 'loltyler1'),
        array('platform' => 'twitch', 'username' => 'loltyler1'),
        array('platform' => 'instagram', 'username' => 'tyler1_alpha'),
    ),
    '333ak.s' => array(
        array('platform' => 'tiktok', 'username' => '333ak.s'),
        array('platform' => 'instagram', 'username' => '333ak.s'),
    ),
    'Carenview' => array(
        array('platform' => 'tiktok', 'username' => 'carenview'),
        array('platform' => 'instagram', 'username' => 'carenview'),
    ),
    'Baabytrinity' => array(
        array('platform' => 'tiktok', 'username' => 'baabytrinity'),
        array('platform' => 'instagram', 'username' => 'baabytrinity'),
    ),
    'Gabbyvn3' => array(
        array('platform' => 'tiktok', 'username' => 'gabbyvn3'),
        array('platform' => 'kick', 'username' => 'gabbyvn3'),
        array('platform' => 'instagram', 'username' => 'gabbyvn3'),
    ),
    'Gillianunrestricted' => array(
        array('platform' => 'tiktok', 'username' => 'gillianunrestricted'),
        array('platform' => 'instagram', 'username' => 'gillianunrestricted'),
    ),
    'Pripeepoopoo' => array(
        array('platform' => 'tiktok', 'username' => 'pripeepoopoo'),
        array('platform' => 'instagram', 'username' => 'pripeepoopoo'),
    ),
    'Brunitarte' => array(
        array('platform' => 'tiktok', 'username' => 'brunitarte'),
        array('platform' => 'instagram', 'username' => 'brunitarte'),
    ),
);

// Get current creators from user_lists
$query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if (!$query || $query->num_rows === 0) {
    die("ERROR: No creators found for user_id=2\n");
}

$row = $query->fetch_assoc();
$creators = json_decode($row['creators'], true);
if (!is_array($creators)) {
    die("ERROR: Failed to decode creators JSON\n");
}

echo "Found " . count($creators) . " creators for user_id=2\n\n";

$updated_count = 0;
$now = time();

foreach ($creators as &$creator) {
    $name = $creator['name'];
    $current_accounts = isset($creator['accounts']) ? $creator['accounts'] : array();
    
    // Check if this creator needs social accounts added
    if (empty($current_accounts) && isset($social_mappings[$name])) {
        $accounts_to_add = $social_mappings[$name];
        
        // Build full account objects with URLs
        $new_accounts = array();
        foreach ($accounts_to_add as $account) {
            $platform = $account['platform'];
            $username = $account['username'];
            
            // Build URL based on platform
            switch ($platform) {
                case 'youtube':
                    $url = "https://www.youtube.com/@{$username}";
                    break;
                case 'twitch':
                    $url = "https://www.twitch.tv/{$username}";
                    break;
                case 'tiktok':
                    $url = "https://www.tiktok.com/@{$username}";
                    break;
                case 'kick':
                    $url = "https://kick.com/{$username}";
                    break;
                case 'instagram':
                    $url = "https://www.instagram.com/{$username}/";
                    break;
                default:
                    $url = isset($account['url']) ? $account['url'] : '';
            }
            
            $new_accounts[] = array(
                'id' => $platform . '_' . $username . '_' . $now,
                'platform' => $platform,
                'username' => $username,
                'url' => $url
            );
        }
        
        $creator['accounts'] = $new_accounts;
        echo "✓ Added " . count($new_accounts) . " accounts for: {$name}\n";
        $updated_count++;
    } else {
        echo "  Skipped (has accounts): {$name}\n";
    }
}

echo "\n\n=================================\n";
echo "Updated {$updated_count} creators with social media accounts\n";

// Save back to database
$json = $conn->real_escape_string(json_encode($creators));
$query = "UPDATE user_lists SET creators = '{$json}', updated_at = NOW() WHERE user_id = 2";

if ($conn->query($query)) {
    echo "✓ SUCCESS: Saved updated creators to database\n";
} else {
    echo "✗ ERROR: " . $conn->error . "\n";
}

$conn->close();
?>
