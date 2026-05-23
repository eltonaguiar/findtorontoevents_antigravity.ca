<?php
/**
 * ALERT HANDLER - Multi-Dimensional Consensus Engine
 * 
 * This file handles:
 * 1. Recording conviction calculations to history
 * 2. Checking alert conditions
 * 3. Sending notifications (email, webhook)
 * 4. Managing cooldowns
 * 
 * Include this in your multi_dimensional.php after calculating conviction
 */

class AlertHandler
{
    private $conn;
    private $debug = false;
    
    public function __construct($dbConnection, $debug = false)
    {
        $this->conn = $dbConnection;
        $this->debug = $debug;
    }
    
    /**
     * Record conviction calculation to history and performance tracking
     */
    public function recordConviction($ticker, $scores, $conviction, $label, $price, $volume = 0, $detail = '')
    {
        try {
            // Use the stored procedure if available
            $stmt = $this->conn->prepare("CALL RecordConviction(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
            $stmt->execute([
                $ticker,
                $conviction,
                $label,
                $scores['whale'] ?? 0,
                $scores['insider'] ?? 0,
                $scores['analyst'] ?? 0,
                $scores['crowd'] ?? 0,
                $scores['fear_greed'] ?? 0,
                $scores['value'] ?? 0,
                $scores['growth'] ?? 0,
                $scores['momentum'] ?? 0,
                $scores['regime'] ?? 0,
                $price,
                $volume,
                $detail
            ]);
            
            if ($this->debug) {
                error_log("Recorded conviction for $ticker: $conviction ($label)");
            }
            
            return true;
        } catch (PDOException $e) {
            // Fallback to direct insert if stored procedure doesn't exist
            return $this->recordConvictionFallback($ticker, $scores, $conviction, $label, $price, $volume, $detail);
        }
    }
    
    /**
     * Fallback recording without stored procedure
     */
    private function recordConvictionFallback($ticker, $scores, $conviction, $label, $price, $volume, $detail)
    {
        try {
            // Insert into history
            $sql = "INSERT INTO conviction_history (
                ticker, conviction_score, label,
                whale_score, insider_score, analyst_score, crowd_score,
                fear_greed_score, value_score, growth_score, momentum_score, regime_score,
                entry_price, entry_volume, calculation_detail
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
            
            $stmt = $this->conn->prepare($sql);
            $stmt->execute([
                $ticker, $conviction, $label,
                $scores['whale'] ?? 0,
                $scores['insider'] ?? 0,
                $scores['analyst'] ?? 0,
                $scores['crowd'] ?? 0,
                $scores['fear_greed'] ?? 0,
                $scores['value'] ?? 0,
                $scores['growth'] ?? 0,
                $scores['momentum'] ?? 0,
                $scores['regime'] ?? 0,
                $price, $volume, $detail
            ]);
            
            // Upsert into performance tracking
            $sql2 = "INSERT INTO conviction_performance (
                ticker, conviction_date, conviction_score, label, entry_price
            ) VALUES (?, CURDATE(), ?, ?, ?)
            ON DUPLICATE KEY UPDATE
                conviction_score = VALUES(conviction_score),
                label = VALUES(label),
                entry_price = VALUES(entry_price)";
            
            $stmt2 = $this->conn->prepare($sql2);
            $stmt2->execute([$ticker, $conviction, $label, $price]);
            
            return true;
        } catch (PDOException $e) {
            error_log("Failed to record conviction for $ticker: " . $e->getMessage());
            return false;
        }
    }
    
    /**
     * Check all alert conditions and trigger if met
     */
    public function checkAndTriggerAlerts($ticker, $scores, $conviction, $label, $price)
    {
        $alerts = [];
        
        // Get active alert configs
        $configs = $this->getActiveAlertConfigs();
        
        foreach ($configs as $config) {
            $shouldTrigger = false;
            $triggerValue = null;
            $triggerDetail = '';
            
            switch ($config['alert_type']) {
                case 'conviction_spike':
                    if ($conviction >= $config['threshold_value']) {
                        $shouldTrigger = true;
                        $triggerValue = $conviction;
                        $triggerDetail = "Conviction reached $conviction ($label)";
                    }
                    break;
                    
                case 'conviction_extreme':
                    if ($conviction >= $config['threshold_value']) {
                        $shouldTrigger = true;
                        $triggerValue = $conviction;
                        $triggerDetail = "Extreme conviction: $conviction";
                    }
                    break;
                    
                case 'insider_cluster':
                    $clusterCount = $this->getInsiderClusterCount($ticker);
                    if ($clusterCount >= $config['threshold_value']) {
                        $shouldTrigger = true;
                        $triggerValue = $clusterCount;
                        $triggerDetail = "$clusterCount insiders bought in last 7 days";
                    }
                    break;
                    
                case 'insider_massive':
                    $maxPurchase = $this->getMaxInsiderPurchase($ticker);
                    if ($maxPurchase >= $config['threshold_value']) {
                        $shouldTrigger = true;
                        $triggerValue = $maxPurchase;
                        $triggerDetail = "Massive insider purchase: $" . number_format($maxPurchase);
                    }
                    break;
                    
                case 'fear_extreme':
                    if ($scores['fear_greed'] <= $config['threshold_value']) {
                        $shouldTrigger = true;
                        $triggerValue = $scores['fear_greed'];
                        $triggerDetail = "Extreme fear: {$scores['fear_greed']}/100 - potential opportunity";
                    }
                    break;
                    
                case 'greed_extreme':
                    if ($scores['fear_greed'] >= $config['threshold_value']) {
                        $shouldTrigger = true;
                        $triggerValue = $scores['fear_greed'];
                        $triggerDetail = "Extreme greed: {$scores['fear_greed']}/100 - consider caution";
                    }
                    break;
                    
                case 'whale_accumulation':
                    if ($scores['whale'] >= $config['threshold_value']) {
                        $shouldTrigger = true;
                        $triggerValue = $scores['whale'];
                        $triggerDetail = "Smart money accumulating: {$scores['whale']}/100";
                    }
                    break;
                    
                case 'crowd_euphoria':
                    if ($scores['crowd'] >= $config['threshold_value']) {
                        $shouldTrigger = true;
                        $triggerValue = $scores['crowd'];
                        $triggerDetail = "Crowd euphoria detected: {$scores['crowd']}/100";
                    }
                    break;
                    
                case 'conviction_jump':
                    $prevConviction = $this->getPreviousConviction($ticker, 7);
                    if ($prevConviction > 0) {
                        $change = $conviction - $prevConviction;
                        if ($change >= $config['threshold_value']) {
                            $shouldTrigger = true;
                            $triggerValue = $change;
                            $triggerDetail = "Conviction jumped +$change points in 7 days";
                        }
                    }
                    break;
                    
                case 'conviction_drop':
                    $prevConviction = $this->getPreviousConviction($ticker, 7);
                    if ($prevConviction > 0) {
                        $change = $conviction - $prevConviction;
                        if ($change <= $config['threshold_value']) {
                            $shouldTrigger = true;
                            $triggerValue = $change;
                            $triggerDetail = "Conviction dropped $change points in 7 days";
                        }
                    }
                    break;
            }
            
            if ($shouldTrigger) {
                // Check cooldown
                if (!$this->isOnCooldown($config['alert_type'], $ticker, $config['cooldown_hours'])) {
                    $alert = $this->triggerAlert($config, $ticker, $triggerValue, $triggerDetail, $scores, $price);
                    if ($alert) {
                        $alerts[] = $alert;
                    }
                }
            }
        }
        
        return $alerts;
    }
    
    /**
     * Get active alert configurations
     */
    private function getActiveAlertConfigs()
    {
        try {
            $stmt = $this->conn->query("SELECT * FROM alert_configs WHERE is_active = TRUE");
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            return [];
        }
    }
    
    /**
     * Check if alert is on cooldown
     */
    private function isOnCooldown($alertType, $ticker, $cooldownHours)
    {
        try {
            $stmt = $this->conn->prepare("SELECT 1 FROM alert_cooldowns 
                WHERE alert_type = ? AND ticker = ? AND cooldown_until > NOW()");
            $stmt->execute([$alertType, $ticker]);
            return $stmt->fetch() !== false;
        } catch (PDOException $e) {
            return false;
        }
    }
    
    /**
     * Trigger an alert
     */
    private function triggerAlert($config, $ticker, $triggerValue, $triggerDetail, $scores, $price)
    {
        try {
            // Insert alert history
            $sql = "INSERT INTO alert_history (
                alert_config_id, ticker, alert_type, trigger_value, trigger_detail,
                conviction_score, whale_score, insider_score, analyst_score, crowd_score, fear_greed_score,
                trigger_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
            
            $stmt = $this->conn->prepare($sql);
            $stmt->execute([
                $config['id'],
                $ticker,
                $config['alert_type'],
                $triggerValue,
                $triggerDetail,
                $scores['conviction'] ?? 0,
                $scores['whale'] ?? 0,
                $scores['insider'] ?? 0,
                $scores['analyst'] ?? 0,
                $scores['crowd'] ?? 0,
                $scores['fear_greed'] ?? 0,
                $price
            ]);
            
            $alertId = $this->conn->lastInsertId();
            
            // Set cooldown
            $this->setCooldown($config['alert_type'], $ticker, $config['cooldown_hours']);
            
            // Send notifications
            $this->sendNotifications($config, $ticker, $triggerValue, $triggerDetail, $scores, $price, $alertId);
            
            if ($this->debug) {
                error_log("Alert triggered: {$config['alert_type']} for $ticker");
            }
            
            return [
                'id' => $alertId,
                'type' => $config['alert_type'],
                'ticker' => $ticker,
                'value' => $triggerValue,
                'detail' => $triggerDetail
            ];
            
        } catch (PDOException $e) {
            error_log("Failed to trigger alert: " . $e->getMessage());
            return null;
        }
    }
    
    /**
     * Set cooldown for an alert
     */
    private function setCooldown($alertType, $ticker, $cooldownHours)
    {
        try {
            $sql = "INSERT INTO alert_cooldowns (alert_type, ticker, last_triggered, cooldown_until)
                VALUES (?, ?, NOW(), DATE_ADD(NOW(), INTERVAL ? HOUR))
                ON DUPLICATE KEY UPDATE
                last_triggered = VALUES(last_triggered),
                cooldown_until = VALUES(cooldown_until)";
            
            $stmt = $this->conn->prepare($sql);
            $stmt->execute([$alertType, $ticker, $cooldownHours]);
        } catch (PDOException $e) {
            error_log("Failed to set cooldown: " . $e->getMessage());
        }
    }
    
    /**
     * Send notifications (email, webhook)
     */
    private function sendNotifications($config, $ticker, $triggerValue, $triggerDetail, $scores, $price, $alertId)
    {
        // Send email if configured
        if (!empty($config['notify_email'])) {
            $this->sendEmailAlert($config['notify_email'], $config, $ticker, $triggerValue, $triggerDetail, $scores, $price);
        }
        
        // Send webhook if configured
        if (!empty($config['notify_webhook'])) {
            $this->sendWebhookAlert($config['notify_webhook'], $config, $ticker, $triggerValue, $triggerDetail, $scores, $price, $alertId);
        }
    }
    
    /**
     * Send email alert
     */
    private function sendEmailAlert($email, $config, $ticker, $triggerValue, $triggerDetail, $scores, $price)
    {
        $subject = "🚨 Alert: {$config['alert_name']} - $ticker";
        
        $body = "Alert Type: {$config['alert_name']}\n";
        $body .= "Ticker: $ticker\n";
        $body .= "Trigger: $triggerDetail\n";
        $body .= "Current Price: $$price\n\n";
        $body .= "Dimension Scores:\n";
        $body .= "- Conviction: {$scores['conviction']}/100\n";
        $body .= "- Whale: {$scores['whale']}/100\n";
        $body .= "- Insider: {$scores['insider']}/100\n";
        $body .= "- Analyst: {$scores['analyst']}/100\n";
        $body .= "- Crowd: {$scores['crowd']}/100\n";
        $body .= "- F&G: {$scores['fear_greed']}/100\n";
        
        $headers = 'From: alerts@yourdomain.com' . "\r\n";
        
        @mail($email, $subject, $body, $headers);
    }
    
    /**
     * Send webhook alert (Discord, Slack, etc.)
     */
    private function sendWebhookAlert($webhookUrl, $config, $ticker, $triggerValue, $triggerDetail, $scores, $price, $alertId)
    {
        $payload = [
            'alert_id' => $alertId,
            'alert_type' => $config['alert_type'],
            'alert_name' => $config['alert_name'],
            'ticker' => $ticker,
            'trigger_value' => $triggerValue,
            'trigger_detail' => $triggerDetail,
            'price' => $price,
            'timestamp' => date('c'),
            'scores' => $scores
        ];
        
        $ch = curl_init($webhookUrl);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        // Update alert history with webhook response
        try {
            $stmt = $this->conn->prepare("UPDATE alert_history 
                SET webhook_sent = TRUE, webhook_response = ? 
                WHERE id = ?");
            $stmt->execute([$response, $alertId]);
        } catch (PDOException $e) {
            // Ignore
        }
    }
    
    // ========================================================================
    // HELPER METHODS
    // ========================================================================
    
    /**
     * Get number of distinct insiders who bought in last 7 days
     */
    private function getInsiderClusterCount($ticker)
    {
        try {
            $stmt = $this->conn->prepare("SELECT COUNT(DISTINCT filer_name) as cnt
                FROM gm_sec_insider_trades
                WHERE ticker = ? AND transaction_type = 'P'
                AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)");
            $stmt->execute([$ticker]);
            $result = $stmt->fetch(PDO::FETCH_ASSOC);
            return intval($result['cnt'] ?? 0);
        } catch (PDOException $e) {
            return 0;
        }
    }
    
    /**
     * Get max insider purchase amount in last 30 days
     */
    private function getMaxInsiderPurchase($ticker)
    {
        try {
            $stmt = $this->conn->prepare("SELECT MAX(total_value) as max_val
                FROM gm_sec_insider_trades
                WHERE ticker = ? AND transaction_type = 'P'
                AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)");
            $stmt->execute([$ticker]);
            $result = $stmt->fetch(PDO::FETCH_ASSOC);
            return floatval($result['max_val'] ?? 0);
        } catch (PDOException $e) {
            return 0;
        }
    }
    
    /**
     * Get previous conviction score from N days ago
     */
    private function getPreviousConviction($ticker, $daysAgo)
    {
        try {
            $stmt = $this->conn->prepare("SELECT conviction_score 
                FROM conviction_history
                WHERE ticker = ? 
                AND calculation_date <= DATE_SUB(NOW(), INTERVAL ? DAY)
                ORDER BY calculation_date DESC
                LIMIT 1");
            $stmt->execute([$ticker, $daysAgo]);
            $result = $stmt->fetch(PDO::FETCH_ASSOC);
            return intval($result['conviction_score'] ?? 0);
        } catch (PDOException $e) {
            return 0;
        }
    }
    
    /**
     * Get recent alerts for display
     */
    public function getRecentAlerts($limit = 20, $days = 7)
    {
        try {
            $stmt = $this->conn->prepare("SELECT 
                ah.*,
                ac.alert_name,
                ch.conviction_score as current_conviction,
                ch.label as current_label
            FROM alert_history ah
            JOIN alert_configs ac ON ah.alert_config_id = ac.id
            LEFT JOIN v_latest_conviction ch ON ah.ticker = ch.ticker
            WHERE ah.triggered_at >= DATE_SUB(NOW(), INTERVAL ? DAY)
            ORDER BY ah.triggered_at DESC
            LIMIT ?");
            $stmt->execute([$days, $limit]);
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            return [];
        }
    }
    
    /**
     * Get performance statistics
     */
    public function getPerformanceStats($period = '30d')
    {
        try {
            $stmt = $this->conn->prepare("SELECT * FROM conviction_stats 
                WHERE stat_period = ? 
                ORDER BY avg_alpha DESC");
            $stmt->execute([$period]);
            return $stmt->fetchAll(PDO::FETCH_ASSOC);
        } catch (PDOException $e) {
            return [];
        }
    }
}

// ============================================================================
// USAGE EXAMPLE - Add to your multi_dimensional.php
// ============================================================================

/*
// At the top of your file, include the alert handler:
require_once 'alert_handler.php';

// After calculating conviction for each ticker:
$alertHandler = new AlertHandler($conn, true); // true for debug mode

foreach ($tickers as $ticker) {
    // ... your existing conviction calculation ...
    $result = calculateConviction($ticker);
    $conviction = $result['conviction'];
    $scores = $result['scores'];
    $label = getLabel($conviction);
    
    // Record to history
    $alertHandler->recordConviction(
        $ticker, 
        $scores, 
        $conviction, 
        $label, 
        $currentPrice, 
        $volume,
        $calculationDetail
    );
    
    // Check and trigger alerts
    $alerts = $alertHandler->checkAndTriggerAlerts(
        $ticker, 
        $scores, 
        $conviction, 
        $label, 
        $currentPrice
    );
    
    if (!empty($alerts)) {
        echo "Alerts triggered for $ticker: " . count($alerts) . "\n";
    }
}
*/
