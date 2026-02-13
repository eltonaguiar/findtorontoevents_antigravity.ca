<?php
/**
 * Backtest Report Generation
 * 
 * Generates comprehensive HTML and JSON reports for backtest results.
 * Includes visualizations, statistical analysis, and actionable insights.
 */

require_once __DIR__ . '/backtest.php';

class BacktestReport {
    private $db;
    private $backtestId;
    private $data;
    
    public function __construct($backtestId = null) {
        $this->db = Database::getInstance();
        $this->backtestId = $backtestId;
        
        if ($backtestId) {
            $this->loadBacktestData($backtestId);
        }
    }
    
    /**
     * Load backtest data from database
     */
    private function loadBacktestData($backtestId) {
        $stmt = $this->db->prepare("SELECT * FROM ml_backtests WHERE backtest_id = :id");
        $stmt->bindValue(':id', $backtestId);
        $stmt->execute();
        $result = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if (!$result) {
            throw new Exception("Backtest not found: {$backtestId}");
        }
        
        $this->data = [
            'backtest_id' => $result['backtest_id'],
            'period' => ['start' => $result['start_date'], 'end' => $result['end_date']],
            'metrics' => json_decode($result['metrics'], true),
            'strategy_config' => json_decode($result['strategy_config'], true),
            'trade_count' => $result['trade_count'],
            'created_at' => $result['created_at']
        ];
        
        // Load trades
        $stmt = $this->db->prepare("
            SELECT * FROM ml_backtest_trades 
            WHERE backtest_id = :id 
            ORDER BY exit_time ASC
        ");
        $stmt->bindValue(':id', $backtestId);
        $stmt->execute();
        $this->data['trades'] = $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
    
    /**
     * Generate HTML report
     */
    public function generateHTMLReport($backtestId = null) {
        if ($backtestId) {
            $this->loadBacktestData($backtestId);
        }
        
        if (!$this->data) {
            throw new Exception("No backtest data loaded");
        }
        
        $data = $this->data;
        $metrics = $data['metrics'];
        
        // Calculate displayed values
        $winRatePct = round($metrics['win_rate'] * 100, 1);
        $maxDDPct = round($metrics['max_drawdown'] * 100, 1);
        $totalReturnPct = round($metrics['total_return'] * 100, 1);
        
        $html = '<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest Report - ' . $data['backtest_id'] . '</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0a0e27;
            color: #e0e6ed;
            line-height: 1.6;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #1a1f3a 0%, #0a0e27 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 1px solid #2a314d;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header-meta {
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
            margin-top: 15px;
            color: #8892a0;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: #1a1f3a;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #2a314d;
            transition: transform 0.2s, border-color 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            border-color: #00d4ff;
        }
        .metric-label {
            font-size: 12px;
            color: #8892a0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 28px;
            font-weight: 700;
        }
        .metric-value.positive { color: #00d4aa; }
        .metric-value.negative { color: #ff4757; }
        .metric-value.neutral { color: #ffd700; }
        .chart-container {
            background: #1a1f3a;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #2a314d;
            margin-bottom: 30px;
        }
        .chart-title {
            font-size: 16px;
            margin-bottom: 15px;
            color: #e0e6ed;
        }
        .section {
            background: #1a1f3a;
            padding: 25px;
            border-radius: 10px;
            border: 1px solid #2a314d;
            margin-bottom: 30px;
        }
        .section h2 {
            font-size: 20px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #2a314d;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #2a314d;
        }
        th {
            color: #8892a0;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }
        tr:hover { background: rgba(255,255,255,0.02); }
        .badge {
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-lean { background: #3b82f6; color: white; }
        .badge-moderate { background: #f59e0b; color: white; }
        .badge-strong { background: #10b981; color: white; }
        .badge-win { background: #00d4aa; color: #0a0e27; }
        .badge-loss { background: #ff4757; color: white; }
        .validity-banner {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .validity-valid {
            background: rgba(0, 212, 170, 0.1);
            border: 1px solid #00d4aa;
            color: #00d4aa;
        }
        .validity-invalid {
            background: rgba(255, 71, 87, 0.1);
            border: 1px solid #ff4757;
            color: #ff4757;
        }
        .insights {
            background: linear-gradient(135deg, #1a1f3a 0%, #0f1429 100%);
            padding: 25px;
            border-radius: 10px;
            border: 1px solid #2a314d;
        }
        .insights h3 {
            margin-bottom: 15px;
            color: #00d4ff;
        }
        .insights ul {
            list-style: none;
            padding: 0;
        }
        .insights li {
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
        }
        .insights li::before {
            content: "→";
            position: absolute;
            left: 0;
            color: #00d4ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Meme Coin Backtest Report</h1>
            <div class="header-meta">
                <div>📅 Period: ' . $data['period']['start'] . ' to ' . $data['period']['end'] . '</div>
                <div>🎯 Total Trades: ' . $data['trade_count'] . '</div>
                <div>🕐 Generated: ' . $data['created_at'] . '</div>
                <div>🔑 ID: ' . substr($data['backtest_id'], 0, 16) . '...</div>
            </div>
        </div>';
        
        // Validity banner
        $validity = $metrics['statistical_validity'] ?? [];
        if (!empty($validity)) {
            $isValid = $validity['sample_size_sufficient'] ?? false;
            $class = $isValid ? 'validity-valid' : 'validity-invalid';
            $icon = $isValid ? '✅' : '⚠️';
            $message = htmlspecialchars($validity['note'] ?? '');
            $ciLower = $validity['win_rate_95ci_lower'] ?? 0;
            $ciUpper = $validity['win_rate_95ci_upper'] ?? 0;
            $minSample = $validity['min_recommended_signals'] ?? 350;
            
            $html .= '
        <div class="validity-banner ' . $class . '">
            ' . $icon . ' ' . $message . '
            <div style="margin-top: 8px; font-size: 13px; opacity: 0.8;">
                95% CI: [' . round($ciLower * 100, 1) . '%, ' . round($ciUpper * 100, 1) . '%] | 
                Sample: ' . $minSample . ' signals required
            </div>
        </div>';
        }
        
        // Metric cards
        $html .= '
        <div class="metric-grid">';
        
        $cards = [
            ['Win Rate', $winRatePct . '%', $metrics['win_rate'] > 0.4 ? 'positive' : 'negative'],
            ['Expectancy', round($metrics['expectancy'], 2) . '%', $metrics['expectancy'] > 0 ? 'positive' : 'negative'],
            ['Sharpe Ratio', round($metrics['sharpe_ratio'], 2), $metrics['sharpe_ratio'] > 1 ? 'positive' : 'neutral'],
            ['Max Drawdown', $maxDDPct . '%', 'negative'],
            ['Profit Factor', round($metrics['profit_factor'], 2), $metrics['profit_factor'] > 1.5 ? 'positive' : 'neutral'],
            ['Avg Duration', round($metrics['avg_trade_duration_hours'], 1) . 'h', 'neutral'],
            ['Total Return', $totalReturnPct . '%', $metrics['total_return'] > 0 ? 'positive' : 'negative'],
            ['Final Equity', '$' . number_format($metrics['final_equity'], 2), $metrics['final_equity'] > 10000 ? 'positive' : 'negative'],
        ];
        
        foreach ($cards as $card) {
            $html .= '
            <div class="metric-card">
                <div class="metric-label">' . $card[0] . '</div>
                <div class="metric-value ' . $card[2] . '">' . $card[1] . '</div>
            </div>';
        }
        
        $html .= '
        </div>
        
        <div class="chart-container">
            <div class="chart-title">📈 Equity Curve</div>
            <canvas id="equityChart" height="80"></canvas>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 30px;">
            <div class="chart-container">
                <div class="chart-title">📊 Performance by Tier</div>
                <canvas id="tierChart"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">🌊 Performance by Market Regime</div>
                <canvas id="regimeChart"></canvas>
            </div>
        </div>';
        
        // Monthly performance
        $html .= '
        <div class="section">
            <h2>📅 Monthly Performance</h2>
            ' . $this->renderMonthlyTable($metrics['monthly_performance'] ?? []) . '
        </div>';
        
        // Tier details
        $html .= '
        <div class="section">
            <h2>📋 Detailed Metrics by Tier</h2>
            ' . $this->renderTierTable($metrics['by_tier'] ?? []) . '
        </div>';
        
        // Insights
        $html .= '
        <div class="insights">
            <h3>💡 Key Insights</h3>
            ' . $this->generateInsights($metrics) . '
        </div>
    </div>
    
    <script>
        ' . $this->generateChartScripts() . '
    </script>
</body>
</html>';
        
        return $html;
    }
    
    /**
     * Render monthly performance table
     */
    private function renderMonthlyTable($monthly) {
        if (empty($monthly)) return '<p>No monthly data available</p>';
        
        $html = '
        <table>
            <thead>
                <tr>
                    <th>Month</th>
                    <th>Trades</th>
                    <th>Wins</th>
                    <th>Losses</th>
                    <th>Win Rate</th>
                    <th>Return %</th>
                </tr>
            </thead>
            <tbody>';
        
        foreach ($monthly as $month) {
            $returnClass = $month['total_return_pct'] >= 0 ? 'positive' : 'negative';
            $html .= '
            <tr>
                <td>' . $month['month'] . '</td>
                <td>' . $month['trades'] . '</td>
                <td>' . $month['wins'] . '</td>
                <td>' . $month['losses'] . '</td>
                <td>' . round($month['win_rate'] * 100, 1) . '%</td>
                <td class="' . $returnClass . '">' . round($month['total_return_pct'], 2) . '%</td>
            </tr>';
        }
        
        $html .= '
            </tbody>
        </table>';
        
        return $html;
    }
    
    /**
     * Render tier performance table
     */
    private function renderTierTable($tiers) {
        if (empty($tiers)) return '<p>No tier data available</p>';
        
        $tierBadges = [
            'lean_buy' => '<span class="badge badge-lean">LEAN BUY</span>',
            'moderate_buy' => '<span class="badge badge-moderate">MODERATE BUY</span>',
            'strong_buy' => '<span class="badge badge-strong">STRONG BUY</span>',
        ];
        
        $html = '
        <table>
            <thead>
                <tr>
                    <th>Tier</th>
                    <th>Signals</th>
                    <th>Win Rate</th>
                    <th>Avg Return</th>
                </tr>
            </thead>
            <tbody>';
        
        foreach ($tiers as $tier => $data) {
            $badge = $tierBadges[$tier] ?? $tier;
            $winRateClass = $data['win_rate'] > 0.4 ? 'positive' : 'negative';
            $returnClass = $data['avg_return'] >= 0 ? 'positive' : 'negative';
            
            $html .= '
            <tr>
                <td>' . $badge . '</td>
                <td>' . $data['signals'] . '</td>
                <td class="' . $winRateClass . '">' . round($data['win_rate'] * 100, 1) . '%</td>
                <td class="' . $returnClass . '">' . round($data['avg_return'], 2) . '%</td>
            </tr>';
        }
        
        $html .= '
            </tbody>
        </table>';
        
        return $html;
    }
    
    /**
     * Generate insights list
     */
    private function generateInsights($metrics) {
        $insights = [];
        
        // Overall performance
        if ($metrics['win_rate'] > 0.5) {
            $insights[] = "Strong win rate of " . round($metrics['win_rate'] * 100, 1) . "% indicates effective signal generation";
        } elseif ($metrics['win_rate'] < 0.35) {
            $insights[] = "Win rate below 35% suggests need for signal quality improvements";
        }
        
        // Expectancy
        if ($metrics['expectancy'] > 0.05) {
            $insights[] = "Positive expectancy of " . round($metrics['expectancy'], 2) . "% suggests profitable edge";
        } elseif ($metrics['expectancy'] < 0) {
            $insights[] = "Negative expectancy - consider revising exit strategy or filters";
        }
        
        // Sharpe ratio
        if ($metrics['sharpe_ratio'] > 1.5) {
            $insights[] = "Excellent risk-adjusted returns (Sharpe > 1.5)";
        } elseif ($metrics['sharpe_ratio'] < 0.5) {
            $insights[] = "Low Sharpe ratio suggests high volatility relative to returns";
        }
        
        // Drawdown
        if ($metrics['max_drawdown'] < -0.3) {
            $insights[] = "High maximum drawdown (" . round($metrics['max_drawdown'] * 100, 1) . "%) - consider tighter risk controls";
        }
        
        // Tier analysis
        $tierMetrics = $metrics['by_tier'] ?? [];
        if (!empty($tierMetrics)) {
            $bestTier = array_reduce(array_keys($tierMetrics), function($best, $key) use ($tierMetrics) {
                return ($tierMetrics[$key]['win_rate'] ?? 0) > ($tierMetrics[$best]['win_rate'] ?? 0) ? $key : $best;
            }, array_key_first($tierMetrics));
            
            $insights[] = ucfirst(str_replace('_', ' ', $bestTier)) . " tier shows strongest performance - consider prioritizing these signals";
        }
        
        // Market regime
        $regimeMetrics = $metrics['by_market_regime'] ?? [];
        if (!empty($regimeMetrics)) {
            $bestRegime = array_reduce(array_keys($regimeMetrics), function($best, $key) use ($regimeMetrics) {
                return ($regimeMetrics[$key]['win_rate'] ?? 0) > ($regimeMetrics[$best]['win_rate'] ?? 0) ? $key : $best;
            }, array_key_first($regimeMetrics));
            
            $insights[] = "Strategy performs best in " . $bestRegime . " market conditions";
        }
        
        // Sample size
        $validity = $metrics['statistical_validity'] ?? [];
        if (!($validity['sample_size_sufficient'] ?? false)) {
            $insights[] = "Insufficient sample size for statistical confidence - extend backtest period";
        }
        
        if (empty($insights)) {
            $insights[] = "Backtest completed successfully. Review detailed metrics for optimization opportunities.";
        }
        
        $html = '<ul>';
        foreach ($insights as $insight) {
            $html .= '<li>' . htmlspecialchars($insight) . '</li>';
        }
        $html .= '</ul>';
        
        return $html;
    }
    
    /**
     * Generate Chart.js scripts
     */
    private function generateChartScripts() {
        // Prepare equity curve data
        $trades = $this->data['trades'] ?? [];
        $equity = 10000;
        $labels = [];
        $equityData = [];
        
        foreach ($trades as $i => $trade) {
            $equity += $trade['pnl_absolute'];
            $labels[] = date('Y-m-d', $trade['exit_time']);
            $equityData[] = round($equity, 2);
        }
        
        // Tier data
        $tierLabels = [];
        $tierWinRates = [];
        
        foreach ($this->data['metrics']['by_tier'] ?? [] as $tier => $data) {
            $tierLabels[] = ucfirst(str_replace('_', ' ', $tier));
            $tierWinRates[] = round($data['win_rate'] * 100, 1);
        }
        
        // Regime data
        $regimeLabels = [];
        $regimeWinRates = [];
        
        foreach ($this->data['metrics']['by_market_regime'] ?? [] as $regime => $data) {
            $regimeLabels[] = ucfirst($regime);
            $regimeWinRates[] = round($data['win_rate'] * 100, 1);
        }
        
        return '
        // Equity Curve Chart
        const equityCtx = document.getElementById("equityChart").getContext("2d");
        new Chart(equityCtx, {
            type: "line",
            data: {
                labels: ' . json_encode($labels) . ',
                datasets: [{
                    label: "Portfolio Value",
                    data: ' . json_encode($equityData) . ',
                    borderColor: "#00d4ff",
                    backgroundColor: "rgba(0, 212, 255, 0.1)",
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { 
                        grid: { color: "#2a314d" },
                        ticks: { color: "#8892a0", maxTicksLimit: 8 }
                    },
                    y: {
                        grid: { color: "#2a314d" },
                        ticks: { 
                            color: "#8892a0",
                            callback: function(value) { return "$" + value.toLocaleString(); }
                        }
                    }
                }
            }
        });
        
        // Tier Performance Chart
        const tierCtx = document.getElementById("tierChart").getContext("2d");
        new Chart(tierCtx, {
            type: "bar",
            data: {
                labels: ' . json_encode($tierLabels) . ',
                datasets: [{
                    label: "Win Rate %",
                    data: ' . json_encode($tierWinRates) . ',
                    backgroundColor: ["#3b82f6", "#f59e0b", "#10b981"],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: "#2a314d" },
                        ticks: { color: "#8892a0" }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: "#8892a0" }
                    }
                }
            }
        });
        
        // Market Regime Chart
        const regimeCtx = document.getElementById("regimeChart").getContext("2d");
        new Chart(regimeCtx, {
            type: "doughnut",
            data: {
                labels: ' . json_encode($regimeLabels) . ',
                datasets: [{
                    data: ' . json_encode($regimeWinRates) . ',
                    backgroundColor: ["#10b981", "#ff4757", "#f59e0b"],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                cutout: "60%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: "#8892a0" }
                    }
                }
            }
        });';
    }
    
    /**
     * Generate JSON report
     */
    public function generateJSONReport($backtestId = null) {
        if ($backtestId) {
            $this->loadBacktestData($backtestId);
        }
        
        return json_encode($this->data, JSON_PRETTY_PRINT);
    }
    
    /**
     * Generate CSV trade log
     */
    public function generateCSVReport($backtestId = null) {
        if ($backtestId) {
            $this->loadBacktestData($backtestId);
        }
        
        $trades = $this->data['trades'] ?? [];
        
        $csv = "Signal ID,Coin,Entry Time,Exit Time,Entry Price,Exit Price,PnL %,PnL \$,Exit Reason,TP Level,Hours Held\n";
        
        foreach ($trades as $trade) {
            $csv .= implode(',', [
                $trade['signal_id'],
                $trade['coin_symbol'],
                date('Y-m-d H:i:s', $trade['entry_time']),
                date('Y-m-d H:i:s', $trade['exit_time']),
                $trade['entry_price'],
                $trade['exit_price'],
                $trade['pnl_percent'],
                $trade['pnl_absolute'],
                $trade['exit_reason'],
                $trade['tp_level_hit'] ?? 'N/A',
                $trade['holding_hours']
            ]) . "\n";
        }
        
        return $csv;
    }
    
    /**
     * Compare multiple backtests
     */
    public function compareBacktests($backtestIds) {
        $comparisons = [];
        
        foreach ($backtestIds as $id) {
            try {
                $this->loadBacktestData($id);
                $comparisons[] = [
                    'backtest_id' => $id,
                    'metrics' => $this->data['metrics'],
                    'period' => $this->data['period'],
                    'trade_count' => $this->data['trade_count']
                ];
            } catch (Exception $e) {
                $comparisons[] = [
                    'backtest_id' => $id,
                    'error' => $e->getMessage()
                ];
            }
        }
        
        return $comparisons;
    }
    
    /**
     * Export report to file
     */
    public function exportReport($backtestId, $format = 'html', $outputPath = null) {
        if (!$outputPath) {
            $outputPath = __DIR__ . "/reports/backtest_{$backtestId}.{$format}";
        }
        
        // Ensure directory exists
        $dir = dirname($outputPath);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        
        switch ($format) {
            case 'html':
                $content = $this->generateHTMLReport($backtestId);
                break;
            case 'json':
                $content = $this->generateJSONReport($backtestId);
                break;
            case 'csv':
                $content = $this->generateCSVReport($backtestId);
                break;
            default:
                throw new Exception("Unsupported format: {$format}");
        }
        
        file_put_contents($outputPath, $content);
        return $outputPath;
    }
}

// CLI usage
if (php_sapi_name() === 'cli' && isset($argc)) {
    $options = getopt('i:f:o:', ['id:', 'format:', 'output:']);
    
    $backtestId = $options['i'] ?? $options['id'] ?? null;
    $format = $options['f'] ?? $options['format'] ?? 'html';
    $output = $options['o'] ?? $options['output'] ?? null;
    
    if (!$backtestId) {
        echo "Usage: php backtest_report.php -i <backtest_id> [-f <format>] [-o <output>]\n";
        echo "Formats: html, json, csv\n";
        exit(1);
    }
    
    try {
        $report = new BacktestReport();
        $path = $report->exportReport($backtestId, $format, $output);
        echo "Report exported to: {$path}\n";
    } catch (Exception $e) {
        echo "Error: " . $e->getMessage() . "\n";
        exit(1);
    }
}
