<?php
/**
 * TicTacToe — Real-Time Multiplayer Matchmaking API
 *
 * Server-side matchmaking queue + game state for cross-device human vs human.
 * PHP 5.2+ compatible.  Uses the same DB as vr_user_progress.
 *
 * Actions (via GET/POST ?action=...):
 *   join           — Join matchmaking queue      (POST: player_id, player_name)
 *   poll           — Poll match state            (GET:  player_id, match_id)
 *   move           — Make a move                 (POST: player_id, match_id, cell 0-8)
 *   leave          — Leave queue / forfeit       (POST: player_id, match_id)
 *   rematch        — Request a rematch           (POST: player_id, match_id)
 *   queue_count    — How many are waiting        (GET)
 *   players_online — Recent active players       (GET)
 *   list_active    — Active games for spectating (GET)
 *   spectate_join  — Join match as spectator     (POST: spectator_id, spectator_name, match_id)
 *   spectate_leave — Leave spectating            (POST: spectator_id, match_id)
 *   spectate_poll  — Poll match as spectator     (GET: match_id)
 *   chat_send      — Send chat message           (POST: match_id, sender_name, sender_type, message)
 *   chat_poll      — Poll chat messages          (GET: match_id, after_id)
 *   chat_request   — Spectator requests to chat  (POST: match_id, spectator_id)
 *   chat_approve   — Player approves spectator   (POST: match_id, spectator_name)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

/* ── .env loader (same pattern as vr_user_progress.php) ── */
$envFile = dirname(__FILE__) . '/.env';
if (file_exists($envFile) && is_readable($envFile)) {
    $raw = file_get_contents($envFile);
    foreach (preg_split('/\r?\n/', $raw) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#' || strpos($line, '=') === false) continue;
        $eq  = strpos($line, '=');
        $k   = trim(substr($line, 0, $eq));
        $val = trim(substr($line, $eq + 1), " \t\"'");
        if (!array_key_exists($k, $_ENV)) $_ENV[$k] = $val;
        if (getenv($k) === false) putenv("$k=$val");
    }
}

function _ttt_env($keys, $default) {
    foreach ((array)$keys as $k) {
        $v = getenv($k);
        if ($v !== false && $v !== '') return $v;
        if (isset($_ENV[$k]) && (string)$_ENV[$k] !== '') return (string)$_ENV[$k];
    }
    return $default;
}

$servername = _ttt_env(array('FC_MYSQL_HOST', 'MYSQL_HOST'), 'localhost');
$username   = _ttt_env(array('FC_MYSQL_USER', 'MYSQL_USER'), 'ejaguiar1_favcreators');
$password   = _ttt_env(array('DB_PASS_SERVER_FAVCREATORS', 'FC_MYSQL_PASSWORD', 'MYSQL_PASSWORD'), '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl');
$dbname     = _ttt_env(array('DB_NAME_SERVER_FAVCREATORS', 'FC_MYSQL_DATABASE', 'MYSQL_DATABASE'), 'ejaguiar1_favcreators');

/* ── Connect ── */
$conn = @new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('error' => 'db_connect_failed', 'detail' => $conn->connect_error));
    exit;
}
$conn->set_charset('utf8');

/* ── Ensure table ── */
$conn->query("
    CREATE TABLE IF NOT EXISTS ttt_matches (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        player_x     VARCHAR(64) NOT NULL,
        player_x_name VARCHAR(30) DEFAULT 'Player 1',
        player_o     VARCHAR(64) DEFAULT NULL,
        player_o_name VARCHAR(30) DEFAULT 'Player 2',
        board        CHAR(9)     DEFAULT '---------',
        current_turn CHAR(1)     DEFAULT 'X',
        status       VARCHAR(10) DEFAULT 'waiting',
        winner       CHAR(1)     DEFAULT NULL,
        rematch_x    TINYINT(1)  DEFAULT 0,
        rematch_o    TINYINT(1)  DEFAULT 0,
        last_move_at DATETIME    DEFAULT NULL,
        created_at   DATETIME    DEFAULT NULL,
        updated_at   DATETIME    DEFAULT NULL,
        INDEX idx_status    (status),
        INDEX idx_player_x  (player_x),
        INDEX idx_player_o  (player_o),
        INDEX idx_updated   (updated_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8
");

/* ── Spectators table ── */
$conn->query("
    CREATE TABLE IF NOT EXISTS ttt_spectators (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        match_id        INT NOT NULL,
        spectator_id    VARCHAR(64) NOT NULL,
        spectator_name  VARCHAR(30) DEFAULT 'Spectator',
        chat_requested  TINYINT(1) DEFAULT 0,
        can_chat        TINYINT(1) DEFAULT 0,
        created_at      DATETIME NOT NULL,
        updated_at      DATETIME NOT NULL,
        INDEX idx_match      (match_id),
        INDEX idx_spectator  (spectator_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8
");

/* ── Chat table ── */
$conn->query("
    CREATE TABLE IF NOT EXISTS ttt_chat (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        match_id        INT NOT NULL,
        sender_name     VARCHAR(30) NOT NULL,
        sender_type     VARCHAR(10) DEFAULT 'player',
        message         VARCHAR(200) NOT NULL,
        created_at      DATETIME NOT NULL,
        INDEX idx_match_time (match_id, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8
");

/* ── Win checker ── */
function ttt_check_winner($board) {
    $lines = array(
        array(0,1,2), array(3,4,5), array(6,7,8),
        array(0,3,6), array(1,4,7), array(2,5,8),
        array(0,4,8), array(2,4,6)
    );
    foreach ($lines as $line) {
        $a = $board[$line[0]];
        if ($a !== '-' && $a === $board[$line[1]] && $a === $board[$line[2]]) {
            return $a;
        }
    }
    return null;
}

/* ── Cleanup stale matches, spectators, chat ── */
function ttt_cleanup($conn) {
    // Waiting matches older than 2 minutes -> delete
    $conn->query("DELETE FROM ttt_matches WHERE status = 'waiting' AND created_at < DATE_SUB(NOW(), INTERVAL 2 MINUTE)");
    // Active matches with no move in 3 minutes -> abandon (no winner)
    $conn->query("UPDATE ttt_matches SET status = 'done', winner = 'A' WHERE status = 'active' AND updated_at < DATE_SUB(NOW(), INTERVAL 3 MINUTE)");
    // Cleanup spectators for finished matches (older than 5 min)
    $conn->query("DELETE FROM ttt_spectators WHERE created_at < DATE_SUB(NOW(), INTERVAL 15 MINUTE)");
    // Cleanup old chat (older than 1 hour)
    $conn->query("DELETE FROM ttt_chat WHERE created_at < DATE_SUB(NOW(), INTERVAL 1 HOUR)");
}

/* ── Helper: safe string ── */
function ttt_safe($conn, $val) {
    return $conn->real_escape_string(trim($val));
}

/* ── Route action ── */
$action = isset($_REQUEST['action']) ? $_REQUEST['action'] : '';

switch ($action) {

/* ══════════════════════════════════════
   JOIN — enter the matchmaking queue
   ══════════════════════════════════════ */
case 'join':
    $pid  = isset($_POST['player_id'])   ? ttt_safe($conn, $_POST['player_id'])   : '';
    $name = isset($_POST['player_name']) ? ttt_safe($conn, $_POST['player_name']) : 'Guest';

    if ($pid === '') { echo json_encode(array('error' => 'player_id required')); break; }

    ttt_cleanup($conn);

    // Remove any stale waiting matches by this player (re-joining)
    $conn->query("DELETE FROM ttt_matches WHERE status = 'waiting' AND player_x = '$pid'");

    // Look for someone waiting (FIFO — oldest first, not self)
    $result = $conn->query("SELECT * FROM ttt_matches WHERE status = 'waiting' AND player_x != '$pid' ORDER BY created_at ASC LIMIT 1");

    if ($result && $result->num_rows > 0) {
        // Match found! Join as O
        $match = $result->fetch_assoc();
        $mid   = intval($match['id']);
        $conn->query("UPDATE ttt_matches SET player_o = '$pid', player_o_name = '$name', status = 'active', updated_at = NOW() WHERE id = $mid");

        echo json_encode(array(
            'success'      => true,
            'matched'      => true,
            'match_id'     => $mid,
            'mark'         => 'O',
            'opponent'     => $match['player_x_name'],
            'status'       => 'active',
            'board'        => $match['board'],
            'current_turn' => $match['current_turn']
        ));
    } else {
        // No one waiting — create a new match and wait
        $now = date('Y-m-d H:i:s');
        $conn->query("INSERT INTO ttt_matches (player_x, player_x_name, board, current_turn, status, created_at, updated_at) VALUES ('$pid', '$name', '---------', 'X', 'waiting', '$now', '$now')");
        $mid = $conn->insert_id;

        echo json_encode(array(
            'success'  => true,
            'matched'  => false,
            'match_id' => $mid,
            'mark'     => 'X',
            'status'   => 'waiting'
        ));
    }
    break;

/* ══════════════════════════════════════
   POLL — check match state
   ══════════════════════════════════════ */
case 'poll':
    $pid = isset($_GET['player_id'])  ? ttt_safe($conn, $_GET['player_id'])  : '';
    $mid = isset($_GET['match_id'])   ? intval($_GET['match_id'])            : 0;

    if ($pid === '' || $mid === 0) { echo json_encode(array('error' => 'player_id and match_id required')); break; }

    $result = $conn->query("SELECT * FROM ttt_matches WHERE id = $mid");
    if (!$result || $result->num_rows === 0) {
        echo json_encode(array('error' => 'match_not_found'));
        break;
    }

    $m = $result->fetch_assoc();
    $myMark = ($m['player_x'] === $pid) ? 'X' : 'O';
    $opName = ($myMark === 'X') ? $m['player_o_name'] : $m['player_x_name'];
    $opId   = ($myMark === 'X') ? $m['player_o']      : $m['player_x'];
    $rematchMe   = ($myMark === 'X') ? intval($m['rematch_x']) : intval($m['rematch_o']);
    $rematchThem = ($myMark === 'X') ? intval($m['rematch_o']) : intval($m['rematch_x']);

    // Spectator info for this match
    $specCnt = 0;
    $specResult2 = $conn->query("SELECT COUNT(*) as cnt FROM ttt_spectators WHERE match_id = $mid");
    if ($specResult2) { $sr2 = $specResult2->fetch_assoc(); $specCnt = intval($sr2['cnt']); }

    $chatReqs = array();
    $reqResult = $conn->query("SELECT spectator_name FROM ttt_spectators WHERE match_id = $mid AND chat_requested = 1");
    if ($reqResult) { while ($rr = $reqResult->fetch_assoc()) { $chatReqs[] = $rr['spectator_name']; } }

    echo json_encode(array(
        'success'          => true,
        'match_id'         => intval($m['id']),
        'board'            => $m['board'],
        'current_turn'     => $m['current_turn'],
        'status'           => $m['status'],
        'winner'           => $m['winner'],
        'my_mark'          => $myMark,
        'opponent'         => $opName,
        'opponent_id'      => $opId,
        'rematch_me'       => $rematchMe,
        'rematch_them'     => $rematchThem,
        'spectator_count'  => $specCnt,
        'chat_requests'    => $chatReqs
    ));
    break;

/* ══════════════════════════════════════
   MOVE — place a mark
   ══════════════════════════════════════ */
case 'move':
    $pid  = isset($_POST['player_id']) ? ttt_safe($conn, $_POST['player_id']) : '';
    $mid  = isset($_POST['match_id'])  ? intval($_POST['match_id'])           : 0;
    $cell = isset($_POST['cell'])      ? intval($_POST['cell'])               : -1;

    if ($pid === '' || $mid === 0 || $cell < 0 || $cell > 8) {
        echo json_encode(array('error' => 'player_id, match_id, and cell (0-8) required'));
        break;
    }

    // Lock row for update
    $result = $conn->query("SELECT * FROM ttt_matches WHERE id = $mid AND status = 'active'");
    if (!$result || $result->num_rows === 0) {
        echo json_encode(array('error' => 'match_not_active'));
        break;
    }

    $m = $result->fetch_assoc();
    $myMark = ($m['player_x'] === $pid) ? 'X' : 'O';

    if ($m['current_turn'] !== $myMark) {
        echo json_encode(array('error' => 'not_your_turn'));
        break;
    }

    $board = $m['board'];
    if ($board[$cell] !== '-') {
        echo json_encode(array('error' => 'cell_taken'));
        break;
    }

    // Place mark
    $board[$cell] = $myMark;
    $boardSafe    = ttt_safe($conn, $board);
    $nextTurn     = ($myMark === 'X') ? 'O' : 'X';

    // Check result
    $winner = ttt_check_winner($board);
    $isDraw = ($winner === null && strpos($board, '-') === false);
    $now    = date('Y-m-d H:i:s');

    if ($winner) {
        $conn->query("UPDATE ttt_matches SET board='$boardSafe', current_turn='$nextTurn', status='done', winner='$winner', last_move_at='$now', updated_at='$now' WHERE id=$mid");
    } elseif ($isDraw) {
        $conn->query("UPDATE ttt_matches SET board='$boardSafe', current_turn='$nextTurn', status='done', winner='D', last_move_at='$now', updated_at='$now' WHERE id=$mid");
    } else {
        $conn->query("UPDATE ttt_matches SET board='$boardSafe', current_turn='$nextTurn', last_move_at='$now', updated_at='$now' WHERE id=$mid");
    }

    echo json_encode(array(
        'success'      => true,
        'board'        => $board,
        'current_turn' => $nextTurn,
        'winner'       => $winner ? $winner : ($isDraw ? 'D' : null),
        'status'       => ($winner || $isDraw) ? 'done' : 'active'
    ));
    break;

/* ══════════════════════════════════════
   LEAVE — quit / forfeit
   ══════════════════════════════════════ */
case 'leave':
    $pid = isset($_POST['player_id']) ? ttt_safe($conn, $_POST['player_id']) : '';
    $mid = isset($_POST['match_id'])  ? intval($_POST['match_id'])           : 0;

    if ($mid > 0) {
        $result = $conn->query("SELECT * FROM ttt_matches WHERE id = $mid");
        if ($result && $result->num_rows > 0) {
            $m = $result->fetch_assoc();
            if ($m['status'] === 'waiting') {
                $conn->query("DELETE FROM ttt_matches WHERE id = $mid");
            } elseif ($m['status'] === 'active') {
                // Forfeit — other player wins
                $winner = ($m['player_x'] === $pid) ? 'O' : 'X';
                $now    = date('Y-m-d H:i:s');
                $conn->query("UPDATE ttt_matches SET status='done', winner='$winner', updated_at='$now' WHERE id=$mid");
            }
        }
    }
    // Also remove any waiting matches by this player
    if ($pid !== '') {
        $conn->query("DELETE FROM ttt_matches WHERE status = 'waiting' AND player_x = '$pid'");
    }
    echo json_encode(array('success' => true));
    break;

/* ══════════════════════════════════════
   REMATCH — request to play again
   ══════════════════════════════════════ */
case 'rematch':
    $pid = isset($_POST['player_id']) ? ttt_safe($conn, $_POST['player_id']) : '';
    $mid = isset($_POST['match_id'])  ? intval($_POST['match_id'])           : 0;

    if ($pid === '' || $mid === 0) { echo json_encode(array('error' => 'player_id and match_id required')); break; }

    $result = $conn->query("SELECT * FROM ttt_matches WHERE id = $mid AND status = 'done'");
    if (!$result || $result->num_rows === 0) {
        echo json_encode(array('error' => 'match_not_found'));
        break;
    }

    $m = $result->fetch_assoc();
    $isX = ($m['player_x'] === $pid);

    // Set my rematch flag
    $col = $isX ? 'rematch_x' : 'rematch_o';
    $conn->query("UPDATE ttt_matches SET $col = 1, updated_at = NOW() WHERE id = $mid");

    // Check if both want rematch
    $otherCol = $isX ? 'rematch_o' : 'rematch_x';
    $result2 = $conn->query("SELECT $otherCol as other_flag FROM ttt_matches WHERE id = $mid");
    $row = $result2->fetch_assoc();

    if (intval($row['other_flag']) === 1) {
        // Both want rematch! Create a NEW match with swapped roles
        $newX     = $m['player_o'];
        $newXName = $m['player_o_name'];
        $newO     = $m['player_x'];
        $newOName = $m['player_x_name'];
        $now      = date('Y-m-d H:i:s');

        $conn->query("INSERT INTO ttt_matches (player_x, player_x_name, player_o, player_o_name, board, current_turn, status, created_at, updated_at)
                       VALUES ('$newX', '$newXName', '$newO', '$newOName', '---------', 'X', 'active', '$now', '$now')");
        $newMid = $conn->insert_id;

        // Mark old match rematch column to point to new match (store in winner field of old match temporarily)
        // Actually better: just let both players poll the rematch endpoint and get the new match_id
        echo json_encode(array(
            'success'      => true,
            'rematch'      => true,
            'new_match_id' => $newMid,
            'mark'         => ($isX ? 'O' : 'X')
        ));
    } else {
        echo json_encode(array(
            'success' => true,
            'rematch' => false,
            'waiting' => true
        ));
    }
    break;

/* ══════════════════════════════════════
   QUEUE_COUNT — how many waiting
   ══════════════════════════════════════ */
case 'queue_count':
    ttt_cleanup($conn);
    $result = $conn->query("SELECT COUNT(*) as cnt FROM ttt_matches WHERE status = 'waiting'");
    $row = $result->fetch_assoc();
    // Also count active games
    $result2 = $conn->query("SELECT COUNT(*) as cnt FROM ttt_matches WHERE status = 'active'");
    $row2 = $result2->fetch_assoc();
    echo json_encode(array(
        'success' => true,
        'waiting' => intval($row['cnt']),
        'active'  => intval($row2['cnt'])
    ));
    break;

/* ══════════════════════════════════════
   PLAYERS_ONLINE — recent active players
   ══════════════════════════════════════ */
case 'players_online':
    ttt_cleanup($conn);
    $players = array();
    $seen    = array();

    // Recent players from matches updated in last 10 minutes
    $sql = "
        SELECT player_x_name AS name, status, updated_at FROM ttt_matches
        WHERE updated_at > DATE_SUB(NOW(), INTERVAL 10 MINUTE) AND player_x_name IS NOT NULL AND player_x_name != ''
        UNION ALL
        SELECT player_o_name AS name, status, updated_at FROM ttt_matches
        WHERE updated_at > DATE_SUB(NOW(), INTERVAL 10 MINUTE) AND player_o_name IS NOT NULL AND player_o_name != ''
        ORDER BY updated_at DESC
    ";
    $result = $conn->query($sql);

    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $name = $row['name'];
            if (!$name || $name === 'Player 1' || $name === 'Player 2') continue;
            if (isset($seen[$name])) continue;
            $seen[$name] = true;

            $isGuest = (substr($name, 0, 6) === 'Guest_');
            $st = $row['status'];
            $gameStatus = ($st === 'active') ? 'In Game' : (($st === 'waiting') ? 'In Lobby' : 'Finished');

            $players[] = array(
                'name'     => $name,
                'status'   => $gameStatus,
                'is_guest' => $isGuest ? 1 : 0
            );
        }
    }

    echo json_encode(array('success' => true, 'players' => $players, 'count' => count($players)));
    break;

/* ══════════════════════════════════════
   LIST_ACTIVE — active games for spectating
   ══════════════════════════════════════ */
case 'list_active':
    ttt_cleanup($conn);
    $result = $conn->query("
        SELECT id, player_x_name, player_o_name, board, current_turn, created_at
        FROM ttt_matches WHERE status = 'active'
        ORDER BY created_at DESC LIMIT 20
    ");
    $games = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $mid2 = intval($row['id']);
            $sc = $conn->query("SELECT COUNT(*) as cnt FROM ttt_spectators WHERE match_id = $mid2");
            $scRow = $sc->fetch_assoc();
            $games[] = array(
                'match_id'    => $mid2,
                'player_x'    => $row['player_x_name'],
                'player_o'    => $row['player_o_name'],
                'board'       => $row['board'],
                'current_turn'=> $row['current_turn'],
                'spectators'  => intval($scRow['cnt'])
            );
        }
    }
    echo json_encode(array('success' => true, 'games' => $games));
    break;

/* ══════════════════════════════════════
   SPECTATE_JOIN — join as spectator
   ══════════════════════════════════════ */
case 'spectate_join':
    $sid  = isset($_POST['spectator_id'])   ? ttt_safe($conn, $_POST['spectator_id'])   : '';
    $snam = isset($_POST['spectator_name']) ? ttt_safe($conn, $_POST['spectator_name']) : 'Spectator';
    $mid  = isset($_POST['match_id'])       ? intval($_POST['match_id'])                : 0;

    if ($sid === '' || $mid === 0) { echo json_encode(array('error' => 'spectator_id and match_id required')); break; }

    $result = $conn->query("SELECT * FROM ttt_matches WHERE id = $mid AND status = 'active'");
    if (!$result || $result->num_rows === 0) {
        echo json_encode(array('error' => 'match_not_found_or_not_active'));
        break;
    }
    $m = $result->fetch_assoc();

    // Upsert spectator
    $conn->query("DELETE FROM ttt_spectators WHERE spectator_id = '$sid' AND match_id = $mid");
    $now = date('Y-m-d H:i:s');
    $conn->query("INSERT INTO ttt_spectators (match_id, spectator_id, spectator_name, created_at, updated_at) VALUES ($mid, '$sid', '$snam', '$now', '$now')");

    // System chat message
    $conn->query("INSERT INTO ttt_chat (match_id, sender_name, sender_type, message, created_at) VALUES ($mid, 'System', 'system', '$snam joined as spectator', '$now')");

    echo json_encode(array(
        'success'      => true,
        'match_id'     => $mid,
        'player_x'     => $m['player_x_name'],
        'player_o'     => $m['player_o_name'],
        'board'        => $m['board'],
        'current_turn' => $m['current_turn'],
        'status'       => $m['status']
    ));
    break;

/* ══════════════════════════════════════
   SPECTATE_LEAVE — leave spectating
   ══════════════════════════════════════ */
case 'spectate_leave':
    $sid = isset($_POST['spectator_id']) ? ttt_safe($conn, $_POST['spectator_id']) : '';
    $mid = isset($_POST['match_id'])     ? intval($_POST['match_id'])              : 0;
    if ($sid !== '') {
        $conn->query("DELETE FROM ttt_spectators WHERE spectator_id = '$sid'" . ($mid ? " AND match_id = $mid" : ''));
    }
    echo json_encode(array('success' => true));
    break;

/* ══════════════════════════════════════
   SPECTATE_POLL — poll match as spectator
   ══════════════════════════════════════ */
case 'spectate_poll':
    $mid = isset($_GET['match_id']) ? intval($_GET['match_id']) : 0;
    if ($mid === 0) { echo json_encode(array('error' => 'match_id required')); break; }

    $result = $conn->query("SELECT * FROM ttt_matches WHERE id = $mid");
    if (!$result || $result->num_rows === 0) {
        echo json_encode(array('error' => 'match_not_found'));
        break;
    }
    $m = $result->fetch_assoc();

    // Spectator count
    $sc = $conn->query("SELECT COUNT(*) as cnt FROM ttt_spectators WHERE match_id = $mid");
    $scRow = $sc->fetch_assoc();

    // Spectator list with chat status
    $specList = array();
    $slr = $conn->query("SELECT spectator_name, chat_requested, can_chat FROM ttt_spectators WHERE match_id = $mid ORDER BY created_at ASC");
    if ($slr) { while ($sr = $slr->fetch_assoc()) {
        $specList[] = array('name' => $sr['spectator_name'], 'chat_requested' => intval($sr['chat_requested']), 'can_chat' => intval($sr['can_chat']));
    }}

    echo json_encode(array(
        'success'         => true,
        'match_id'        => intval($m['id']),
        'board'           => $m['board'],
        'current_turn'    => $m['current_turn'],
        'status'          => $m['status'],
        'winner'          => $m['winner'],
        'player_x'        => $m['player_x_name'],
        'player_o'        => $m['player_o_name'],
        'spectator_count' => intval($scRow['cnt']),
        'spectators'      => $specList
    ));
    break;

/* ══════════════════════════════════════
   CHAT_SEND — send a chat message
   ══════════════════════════════════════ */
case 'chat_send':
    $mid  = isset($_POST['match_id'])    ? intval($_POST['match_id'])               : 0;
    $name = isset($_POST['sender_name']) ? ttt_safe($conn, $_POST['sender_name'])   : '';
    $type = isset($_POST['sender_type']) ? ttt_safe($conn, $_POST['sender_type'])   : 'player';
    $msg  = isset($_POST['message'])     ? ttt_safe($conn, substr(trim($_POST['message']), 0, 200)) : '';

    if ($mid === 0 || $name === '' || $msg === '') {
        echo json_encode(array('error' => 'match_id, sender_name, and message required'));
        break;
    }

    // If spectator, check they have chat permission
    if ($type === 'spectator') {
        $chk = $conn->query("SELECT can_chat FROM ttt_spectators WHERE match_id = $mid AND spectator_name = '$name' AND can_chat = 1 LIMIT 1");
        if (!$chk || $chk->num_rows === 0) {
            echo json_encode(array('error' => 'chat_not_allowed'));
            break;
        }
    }

    $now = date('Y-m-d H:i:s');
    $conn->query("INSERT INTO ttt_chat (match_id, sender_name, sender_type, message, created_at) VALUES ($mid, '$name', '$type', '$msg', '$now')");
    echo json_encode(array('success' => true));
    break;

/* ══════════════════════════════════════
   CHAT_POLL — get recent chat messages
   ══════════════════════════════════════ */
case 'chat_poll':
    $mid   = isset($_GET['match_id']) ? intval($_GET['match_id']) : 0;
    $after = isset($_GET['after_id']) ? intval($_GET['after_id']) : 0;
    $messages = array();
    if ($mid > 0) {
        $sql = "SELECT id, sender_name, sender_type, message, created_at FROM ttt_chat WHERE match_id = $mid";
        if ($after > 0) $sql .= " AND id > $after";
        $sql .= " ORDER BY created_at ASC LIMIT 50";
        $r = $conn->query($sql);
        if ($r) { while ($row = $r->fetch_assoc()) {
            $messages[] = array(
                'id'      => intval($row['id']),
                'name'    => $row['sender_name'],
                'type'    => $row['sender_type'],
                'message' => $row['message'],
                'time'    => $row['created_at']
            );
        }}
    }
    echo json_encode(array('success' => true, 'messages' => $messages));
    break;

/* ══════════════════════════════════════
   CHAT_REQUEST — spectator requests to chat
   ══════════════════════════════════════ */
case 'chat_request':
    $mid = isset($_POST['match_id'])     ? intval($_POST['match_id'])              : 0;
    $sid = isset($_POST['spectator_id']) ? ttt_safe($conn, $_POST['spectator_id']) : '';

    if ($mid === 0 || $sid === '') { echo json_encode(array('error' => 'match_id and spectator_id required')); break; }

    $conn->query("UPDATE ttt_spectators SET chat_requested = 1, updated_at = NOW() WHERE match_id = $mid AND spectator_id = '$sid'");
    echo json_encode(array('success' => true));
    break;

/* ══════════════════════════════════════
   CHAT_APPROVE — player approves spectator chat
   ══════════════════════════════════════ */
case 'chat_approve':
    $mid     = isset($_POST['match_id'])       ? intval($_POST['match_id'])                : 0;
    $specNam = isset($_POST['spectator_name']) ? ttt_safe($conn, $_POST['spectator_name']) : '';

    if ($mid === 0 || $specNam === '') { echo json_encode(array('error' => 'match_id and spectator_name required')); break; }

    $conn->query("UPDATE ttt_spectators SET can_chat = 1, chat_requested = 0, updated_at = NOW() WHERE match_id = $mid AND spectator_name = '$specNam'");

    $now = date('Y-m-d H:i:s');
    $conn->query("INSERT INTO ttt_chat (match_id, sender_name, sender_type, message, created_at) VALUES ($mid, 'System', 'system', '$specNam can now chat', '$now')");

    echo json_encode(array('success' => true));
    break;

default:
    echo json_encode(array('error' => 'Unknown action'));
}

$conn->close();
?>
