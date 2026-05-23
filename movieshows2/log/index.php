<?php
$host = 'mysql.50webs.com';
$db = 'ejaguiar1_tvmoviestrailers';
$user = 'ejaguiar1_tvmoviestrailers';
$pass = getenv('EJAGUIAR1_TVMOVIESTRAILERS') ?: 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD';

header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Movie/TV Series Data Pull Log</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-label { color: #666; font-size: 0.9em; margin-bottom: 5px; }
        .stat-value { color: #333; font-size: 2em; font-weight: bold; }
        .log-section {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .log-section h2 {
            color: #333;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #667eea; color: white; font-weight: 600; }
        tr:hover { background-color: #f5f5f5; }
        .error {
            background-color: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .last-update { text-align: center; color: white; margin-top: 20px; font-size: 0.9em; }
        .type-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .type-movie { background-color: #e3f2fd; color: #1976d2; }
        .type-tv { background-color: #f3e5f5; color: #7b1fa2; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Movie/TV Series Data Pull Log</h1>
        
        <?php
        try {
            $pdo = new PDO("mysql:host=$host;dbname=$db;charset=utf8mb4", $user, $pass);
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            
            $totalStmt = $pdo->query("SELECT COUNT(*) as total FROM movies");
            $totalResult = $totalStmt->fetch(PDO::FETCH_ASSOC);
            $totalRecords = $totalResult['total'];
            
            $movieStmt = $pdo->query("SELECT COUNT(*) as count FROM movies WHERE type = 'movie'");
            $movieResult = $movieStmt->fetch(PDO::FETCH_ASSOC);
            $totalMovies = $movieResult['count'];
            
            $tvStmt = $pdo->query("SELECT COUNT(*) as count FROM movies WHERE type = 'tv'");
            $tvResult = $tvStmt->fetch(PDO::FETCH_ASSOC);
            $totalTV = $tvResult['count'];
            
            $latestStmt = $pdo->query("SELECT MAX(created_at) as latest FROM movies");
            $latestResult = $latestStmt->fetch(PDO::FETCH_ASSOC);
            $lastUpdate = $latestResult['latest'];
            
            echo '<div class="stats-grid">';
            echo '<div class="stat-card"><div class="stat-label">Total Records</div><div class="stat-value">' . number_format($totalRecords) . '</div></div>';
            echo '<div class="stat-card"><div class="stat-label">Movies</div><div class="stat-value">' . number_format($totalMovies) . '</div></div>';
            echo '<div class="stat-card"><div class="stat-label">TV Series</div><div class="stat-value">' . number_format($totalTV) . '</div></div>';
            echo '<div class="stat-card"><div class="stat-label">Last Update</div><div class="stat-value" style="font-size: 1.2em;">' . ($lastUpdate ? date('M d, Y', strtotime($lastUpdate)) : 'N/A') . '</div></div>';
            echo '</div>';
            
            echo '<div class="log-section"><h2>Records by Year and Type</h2><table>';
            echo '<thead><tr><th>Year</th><th>Type</th><th>Count</th><th>Percentage</th></tr></thead><tbody>';
            
            $yearStmt = $pdo->query("SELECT release_year, type, COUNT(*) as count FROM movies GROUP BY release_year, type ORDER BY release_year DESC, type");
            
            while ($row = $yearStmt->fetch(PDO::FETCH_ASSOC)) {
                $percentage = ($totalRecords > 0) ? round(($row['count'] / $totalRecords) * 100, 2) : 0;
                $typeBadge = $row['type'] === 'movie' ? 'type-movie' : 'type-tv';
                echo '<tr><td>' . htmlspecialchars($row['release_year']) . '</td>';
                echo '<td><span class="type-badge ' . $typeBadge . '">' . strtoupper(htmlspecialchars($row['type'])) . '</span></td>';
                echo '<td>' . number_format($row['count']) . '</td><td>' . $percentage . '%</td></tr>';
            }
            
            echo '</tbody></table></div>';
            
            echo '<div class="log-section"><h2>Recent Additions (Last 20)</h2><table>';
            echo '<thead><tr><th>ID</th><th>Title</th><th>Type</th><th>Year</th><th>Rating</th><th>Added</th></tr></thead><tbody>';
            
            $recentStmt = $pdo->query("SELECT id, title, type, release_year, imdb_rating, created_at FROM movies ORDER BY created_at DESC LIMIT 20");
            
            while ($row = $recentStmt->fetch(PDO::FETCH_ASSOC)) {
                $typeBadge = $row['type'] === 'movie' ? 'type-movie' : 'type-tv';
                echo '<tr><td>' . htmlspecialchars($row['id']) . '</td>';
                echo '<td>' . htmlspecialchars($row['title']) . '</td>';
                echo '<td><span class="type-badge ' . $typeBadge . '">' . strtoupper(htmlspecialchars($row['type'])) . '</span></td>';
                echo '<td>' . htmlspecialchars($row['release_year']) . '</td>';
                echo '<td>' . ($row['imdb_rating'] ? number_format($row['imdb_rating'], 1) : 'N/A') . '</td>';
                echo '<td>' . date('M d, Y H:i', strtotime($row['created_at'])) . '</td></tr>';
            }
            
            echo '</tbody></table></div>';
            
            if (file_exists('pull_log.json')) {
                echo '<div class="log-section"><h2>Pull History</h2>';
                $logData = json_decode(file_get_contents('pull_log.json'), true);
                if ($logData && is_array($logData)) {
                    echo '<table><thead><tr><th>Timestamp</th><th>Status</th><th>Movies Added</th><th>TV Added</th><th>Message</th></tr></thead><tbody>';
                    foreach (array_reverse(array_slice($logData, -50)) as $log) {
                        echo '<tr><td>' . htmlspecialchars($log['timestamp'] ?? 'N/A') . '</td>';
                        echo '<td>' . htmlspecialchars($log['status'] ?? 'N/A') . '</td>';
                        echo '<td>' . htmlspecialchars($log['movies_added'] ?? '0') . '</td>';
                        echo '<td>' . htmlspecialchars($log['tv_added'] ?? '0') . '</td>';
                        echo '<td>' . htmlspecialchars($log['message'] ?? '') . '</td></tr>';
                    }
                    echo '</tbody></table>';
                }
                echo '</div>';
            }
            
        } catch (PDOException $e) {
            echo '<div class="error">Database Error: ' . htmlspecialchars($e->getMessage()) . '</div>';
        }
        ?>
        
        <div class="last-update">Page generated: <?php echo date('Y-m-d H:i:s T'); ?></div>
    </div>
</body>
</html>
