<?php
/**
 * ALERTS DASHBOARD - Multi-Dimensional Consensus Engine
 * 
 * Simple web dashboard to view:
 * - Recent alerts
 * - Performance statistics
 * - Latest conviction scores
 * - Alert configuration
 */

require_once 'database.php'; // Your existing DB connection

// Initialize alert handler
require_once 'alert_handler.php';
$alertHandler = new AlertHandler($conn);

// Get data
$recentAlerts = $alertHandler->getRecentAlerts(50, 7);
$performanceStats = $alertHandler->getPerformanceStats('30d');

// Get latest conviction scores
$latestScores = [];
try {
    $stmt = $conn->query("SELECT * FROM v_latest_conviction ORDER BY conviction_score DESC LIMIT 20");
    $latestScores = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    // View might not exist yet
}

// Get pending alerts (not sent)
$pendingAlerts = [];
try {
    $stmt = $conn->query("SELECT * FROM alert_history 
        WHERE email_sent = FALSE 
        AND triggered_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        ORDER BY triggered_at DESC");
    $pendingAlerts = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    // Table might not exist yet
}

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consensus Engine - Alerts Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #22d3ee; margin-bottom: 10px; }
        h2 { color: #94a3b8; margin: 30px 0 15px; font-size: 1.2rem; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #1e293b;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #22d3ee;
        }
        .stat-card h3 { font-size: 0.9rem; color: #94a3b8; margin-bottom: 10px; }
        .stat-card .value { font-size: 2rem; font-weight: bold; color: #22d3ee; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 8px;
            overflow: hidden;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }
        th {
            background: #0f172a;
            color: #94a3b8;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
        }
        tr:hover { background: #252f47; }
        
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-strong-buy { background: #065f46; color: #34d399; }
        .badge-buy { background: #1e3a5f; color: #60a5fa; }
        .badge-neutral { background: #451a03; color: #fbbf24; }
        .badge-hold { background: #4c1d95; color: #c4b5fd; }
        .badge-sell { background: #7f1d1d; color: #f87171; }
        
        .score { font-weight: bold; }
        .score-high { color: #34d399; }
        .score-med { color: #fbbf24; }
        .score-low { color: #f87171; }
        
        .alert-type {
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        .alert-icon { font-size: 1.1rem; }
        
        .timestamp { color: #64748b; font-size: 0.85rem; }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            background: #1e293b;
            border: none;
            color: #94a3b8;
            cursor: pointer;
            border-radius: 6px;
        }
        .tab.active {
            background: #22d3ee;
            color: #0f172a;
        }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Consensus Engine - Alerts Dashboard</h1>
        <p style="color: #64748b;">Multi-dimensional stock intelligence system</p>
        
        <!-- Stats Overview -->
        <h2>📊 Performance Overview</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Alerts (7d)</h3>
                <div class="value"><?php echo count($recentAlerts); ?></div>
            </div>
            <div class="stat-card">
                <h3>Pending Notifications</h3>
                <div class="value"><?php echo count($pendingAlerts); ?></div>
            </div>
            <div class="stat-card">
                <h3>Strong Bullish (70+)</h3>
                <div class="value"><?php echo count(array_filter($latestScores, fn($s) => $s['conviction_score'] >= 70)); ?></div>
            </div>
            <div class="stat-card">
                <h3>Tracked Tickers</h3>
                <div class="value"><?php echo count($latestScores); ?></div>
            </div>
        </div>
        
        <!-- Tabs -->
        <div class="tabs">
            <button class="tab active" onclick="showTab('alerts')">🚨 Recent Alerts</button>
            <button class="tab" onclick="showTab('scores')">📈 Latest Scores</button>
            <button class="tab" onclick="showTab('performance')">🏆 Performance</button>
        </div>
        
        <!-- Recent Alerts Tab -->
        <div id="alerts" class="tab-content active">
            <h2>Recent Alerts (Last 7 Days)</h2>
            <?php if (empty($recentAlerts)): ?>
                <div class="empty-state">No alerts triggered yet. Alerts will appear here when conditions are met.</div>
            <?php else: ?>
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Alert Type</th>
                            <th>Ticker</th>
                            <th>Trigger</th>
                            <th>Conviction</th>
                            <th>Price</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($recentAlerts as $alert): ?>
                        <tr>
                            <td class="timestamp"><?php echo date('M d H:i', strtotime($alert['triggered_at'])); ?></td>
                            <td>
                                <span class="alert-type">
                                    <?php
                                    $icons = [
                                        'conviction_spike' => '🚀',
                                        'conviction_extreme' => '🔥',
                                        'insider_cluster' => '🐋',
                                        'insider_massive' => '💰',
                                        'fear_extreme' => '😱',
                                        'greed_extreme' => '🤑',
                                        'whale_accumulation' => '📈',
                                        'crowd_euphoria' => '🎉'
                                    ];
                                    echo ($icons[$alert['alert_type']] ?? '🔔') . ' ';
                                    echo htmlspecialchars($alert['alert_name'] ?? $alert['alert_type']);
                                    ?>
                                </span>
                            </td>
                            <td><strong><?php echo htmlspecialchars($alert['ticker']); ?></strong></td>
                            <td><?php echo htmlspecialchars($alert['trigger_detail']); ?></td>
                            <td class="score <?php echo $alert['conviction_score'] >= 70 ? 'score-high' : ($alert['conviction_score'] >= 50 ? 'score-med' : 'score-low'); ?>">
                                <?php echo $alert['conviction_score']; ?>/100
                            </td>
                            <td>$<?php echo number_format($alert['trigger_price'], 2); ?></td>
                            <td>
                                <?php if ($alert['email_sent']): ?>
                                    <span style="color: #34d399;">✓ Email</span>
                                <?php endif; ?>
                                <?php if ($alert['webhook_sent']): ?>
                                    <span style="color: #34d399;">✓ Webhook</span>
                                <?php endif; ?>
                                <?php if (!$alert['email_sent'] && !$alert['webhook_sent']): ?>
                                    <span style="color: #fbbf24;">⏳ Pending</span>
                                <?php endif; ?>
                            </td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php endif; ?>
        </div>
        
        <!-- Latest Scores Tab -->
        <div id="scores" class="tab-content">
            <h2>Latest Conviction Scores</h2>
            <?php if (empty($latestScores)): ?>
                <div class="empty-state">No scores available. Run the consensus calculation first.</div>
            <?php else: ?>
                <table>
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Conviction</th>
                            <th>Label</th>
                            <th>Whale</th>
                            <th>Insider</th>
                            <th>Analyst</th>
                            <th>Crowd</th>
                            <th>F&G</th>
                            <th>Value</th>
                            <th>Growth</th>
                            <th>Momentum</th>
                            <th>Regime</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($latestScores as $score): ?>
                        <tr>
                            <td><strong><?php echo htmlspecialchars($score['ticker']); ?></strong></td>
                            <td class="score <?php echo $score['conviction_score'] >= 70 ? 'score-high' : ($score['conviction_score'] >= 50 ? 'score-med' : 'score-low'); ?>">
                                <?php echo $score['conviction_score']; ?>
                            </td>
                            <td>
                                <?php
                                $labelClass = 'badge-neutral';
                                if ($score['label'] === 'STRONG BUY') $labelClass = 'badge-strong-buy';
                                elseif ($score['label'] === 'BUY') $labelClass = 'badge-buy';
                                elseif ($score['label'] === 'HOLD') $labelClass = 'badge-hold';
                                elseif ($score['label'] === 'SELL') $labelClass = 'badge-sell';
                                ?>
                                <span class="badge <?php echo $labelClass; ?>"><?php echo $score['label']; ?></span>
                            </td>
                            <td><?php echo $score['whale_score']; ?></td>
                            <td><?php echo $score['insider_score']; ?></td>
                            <td><?php echo $score['analyst_score']; ?></td>
                            <td><?php echo $score['crowd_score']; ?></td>
                            <td><?php echo $score['fear_greed_score']; ?></td>
                            <td><?php echo $score['value_score']; ?></td>
                            <td><?php echo $score['growth_score']; ?></td>
                            <td><?php echo $score['momentum_score']; ?></td>
                            <td><?php echo $score['regime_score']; ?></td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php endif; ?>
        </div>
        
        <!-- Performance Tab -->
        <div id="performance" class="tab-content">
            <h2>Performance by Conviction Level (30 Days)</h2>
            <?php if (empty($performanceStats)): ?>
                <div class="empty-state">No performance data yet. Returns are calculated after 30 days.</div>
            <?php else: ?>
                <table>
                    <thead>
                        <tr>
                            <th>Conviction Bucket</th>
                            <th>Total Signals</th>
                            <th>Win Rate</th>
                            <th>Avg Return</th>
                            <th>Median Return</th>
                            <th>Max Return</th>
                            <th>Min Return</th>
                            <th>vs SPY (Alpha)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($performanceStats as $stat): ?>
                        <tr>
                            <td><strong><?php echo $stat['conviction_bucket']; ?></strong></td>
                            <td><?php echo $stat['total_signals']; ?></td>
                            <td class="<?php echo $stat['win_rate'] >= 60 ? 'score-high' : ($stat['win_rate'] >= 50 ? 'score-med' : 'score-low'); ?>">
                                <?php echo $stat['win_rate']; ?>%
                            </td>
                            <td class="<?php echo $stat['avg_return'] >= 5 ? 'score-high' : ($stat['avg_return'] >= 0 ? 'score-med' : 'score-low'); ?>">
                                <?php echo ($stat['avg_return'] > 0 ? '+' : '') . $stat['avg_return']; ?>%
                            </td>
                            <td><?php echo $stat['median_return']; ?>%</td>
                            <td class="score-high">+<?php echo $stat['max_return']; ?>%</td>
                            <td class="score-low"><?php echo $stat['min_return']; ?>%</td>
                            <td class="<?php echo $stat['avg_alpha'] >= 2 ? 'score-high' : ($stat['avg_alpha'] >= 0 ? 'score-med' : 'score-low'); ?>">
                                <?php echo ($stat['avg_alpha'] > 0 ? '+' : '') . $stat['avg_alpha']; ?>%
                            </td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php endif; ?>
        </div>
    </div>
    
    <script>
        function showTab(tabId) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            
            // Show selected tab
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }
        
        // Auto-refresh every 60 seconds
        setTimeout(() => location.reload(), 60000);
    </script>
</body>
</html>
