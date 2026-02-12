<?php
/**
 * ML Database Initialization Script
 * Creates tables and seeds with sample training data
 * Run once to initialize the ML system
 */

require_once dirname(dirname(__FILE__)) . '/../live-monitor/api/sports_db_connect.php';

class MLDatabaseInit {
    private $conn;
    private $output = array();
    
    public function __construct($connection) {
        $this->conn = $connection;
    }
    
    /**
     * Initialize all ML tables
     */
    public function init() {
        $this->output[] = "Starting ML Database Initialization...";
        
        // Create tables
        $this->createSignalTables();
        $this->createMLTables();
        
        // Seed sample data if empty
        $this->seedSampleData();
        
        // Create initial model with default weights
        $this->createInitialModel();
        
        $this->output[] = "Initialization complete!";
        
        return array(
            'ok' => true,
            'messages' => $this->output,
            'tables_created' => array(
                'meme_signals',
                'meme_signal_results',
                'meme_ml_models',
                'meme_ml_predictions'
            )
        );
    }
    
    /**
     * Create signal tracking tables
     */
    private function createSignalTables() {
        // Main signals table
        $this->conn->query("CREATE TABLE IF NOT EXISTS meme_signals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            signal_id VARCHAR(50) UNIQUE,
            coin_symbol VARCHAR(20),
            coin_name VARCHAR(100),
            tier ENUM('tier1', 'tier2'),
            
            -- Feature scores (0-100 scale)
            explosive_volume DECIMAL(5,2),
            parabolic_momentum DECIMAL(5,2),
            rsi_hype_zone DECIMAL(5,2),
            social_momentum_proxy DECIMAL(5,2),
            volume_concentration DECIMAL(5,2),
            breakout_4h DECIMAL(5,2),
            low_market_cap_bonus DECIMAL(5,2),
            
            -- Calculated scores
            total_score DECIMAL(5,2),
            verdict VARCHAR(20),
            
            -- Price data
            entry_price DECIMAL(18,10),
            target_price DECIMAL(18,10),
            stop_price DECIMAL(18,10),
            
            -- Timestamps
            signal_time DATETIME,
            resolve_time DATETIME,
            created_at DATETIME DEFAULT NOW(),
            
            INDEX idx_coin (coin_symbol),
            INDEX idx_time (signal_time),
            INDEX idx_score (total_score),
            INDEX idx_verdict (verdict)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->output[] = "Created meme_signals table";
        
        // Signal results table
        $this->conn->query("CREATE TABLE IF NOT EXISTS meme_signal_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            signal_id VARCHAR(50),
            outcome ENUM('win', 'loss', 'pending', 'expired'),
            profit_loss_pct DECIMAL(8,4),
            max_profit_pct DECIMAL(8,4),
            max_loss_pct DECIMAL(8,4),
            exit_price DECIMAL(18,10),
            resolved_at DATETIME,
            resolution_notes TEXT,
            
            INDEX idx_signal (signal_id),
            INDEX idx_outcome (outcome),
            INDEX idx_resolved (resolved_at)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->output[] = "Created meme_signal_results table";
    }
    
    /**
     * Create ML-specific tables
     */
    private function createMLTables() {
        // ML Models table
        $this->conn->query("CREATE TABLE IF NOT EXISTS meme_ml_models (
            id INT AUTO_INCREMENT PRIMARY KEY,
            model_id VARCHAR(50) UNIQUE,
            model_version INT DEFAULT 1,
            
            -- Weights JSON
            weights_json TEXT,
            feature_importance_json TEXT,
            metrics_json TEXT,
            
            -- Training info
            sample_count INT,
            training_samples_wins INT,
            training_samples_losses INT,
            base_win_rate DECIMAL(5,2),
            
            -- Performance metrics
            accuracy DECIMAL(5,4),
            precision_score DECIMAL(5,4),
            recall DECIMAL(5,4),
            f1_score DECIMAL(5,4),
            
            -- Status
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT NOW(),
            last_used DATETIME,
            
            INDEX idx_active (is_active),
            INDEX idx_created (created_at)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->output[] = "Created meme_ml_models table";
        
        // ML Predictions table
        $this->conn->query("CREATE TABLE IF NOT EXISTS meme_ml_predictions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            prediction_id VARCHAR(50) UNIQUE,
            signal_id VARCHAR(50),
            model_id VARCHAR(50),
            
            -- Prediction values
            predicted_probability DECIMAL(5,4),
            predicted_outcome TINYINT COMMENT '1=win, 0=loss',
            confidence_level VARCHAR(10),
            
            -- Feature values used
            feature_values_json TEXT,
            
            -- Actual outcome (filled later)
            actual_outcome TINYINT DEFAULT NULL,
            outcome_verified_at DATETIME,
            
            -- Timestamps
            created_at DATETIME DEFAULT NOW(),
            
            INDEX idx_signal (signal_id),
            INDEX idx_model (model_id),
            INDEX idx_created (created_at)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->output[] = "Created meme_ml_predictions table";
        
        // Training log table
        $this->conn->query("CREATE TABLE IF NOT EXISTS meme_ml_training_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            model_id VARCHAR(50),
            action VARCHAR(50),
            samples_used INT,
            accuracy DECIMAL(5,4),
            message TEXT,
            created_at DATETIME DEFAULT NOW(),
            
            INDEX idx_model (model_id),
            INDEX idx_action (action)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->output[] = "Created meme_ml_training_log table";
    }
    
    /**
     * Seed with sample training data
     */
    private function seedSampleData() {
        // Check if data already exists
        $res = $this->conn->query("SELECT COUNT(*) as cnt FROM meme_signals");
        $row = $res->fetch_assoc();
        
        if ($row['cnt'] > 0) {
            $this->output[] = "Sample data already exists (" . $row['cnt'] . " signals), skipping seed";
            return;
        }
        
        // Generate realistic sample signals with outcomes
        $sample_signals = $this->generateSampleSignals(100);
        
        foreach ($sample_signals as $signal) {
            $this->insertSignal($signal);
        }
        
        $this->output[] = "Seeded " . count($sample_signals) . " sample signals";
    }
    
    /**
     * Generate realistic sample signals
     */
    private function generateSampleSignals($count) {
        $coins = array('DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'MEME', 'BOME', 'WLD', 'GRT');
        $signals = array();
        
        for ($i = 0; $i < $count; $i++) {
            // Generate random feature scores
            $volume = mt_rand(50, 2500) / 100; // 0.50 - 25.00
            $momentum = mt_rand(40, 2000) / 100;
            $rsi = mt_rand(30, 1500) / 100;
            $social = mt_rand(20, 1500) / 100;
            $vol_conc = mt_rand(10, 1000) / 100;
            $breakout = mt_rand(5, 1000) / 100;
            $mcap = mt_rand(0, 500) / 100;
            
            $total = $volume + $momentum + $rsi + $social + $vol_conc + $breakout + $mcap;
            
            // Determine outcome based on score (higher score = higher win rate)
            $win_probability = min(0.8, max(0.1, $total / 150));
            $outcome = (mt_rand(1, 100) / 100) < $win_probability ? 'win' : 'loss';
            
            $profit_loss = $outcome === 'win' 
                ? mt_rand(200, 1500) / 100 // 2-15%
                : -mt_rand(100, 500) / 100; // -1 to -5%
            
            $signals[] = array(
                'signal_id' => 'meme_' . date('Ymd', strtotime("-$i days")) . '_' . mt_rand(1000, 9999),
                'coin_symbol' => $coins[array_rand($coins)],
                'tier' => mt_rand(1, 100) > 70 ? 'tier1' : 'tier2',
                'explosive_volume' => $volume,
                'parabolic_momentum' => $momentum,
                'rsi_hype_zone' => $rsi,
                'social_momentum_proxy' => $social,
                'volume_concentration' => $vol_conc,
                'breakout_4h' => $breakout,
                'low_market_cap_bonus' => $mcap,
                'total_score' => $total,
                'verdict' => $total >= 85 ? 'strong_buy' : ($total >= 75 ? 'buy' : ($total >= 70 ? 'lean_buy' : 'skip')),
                'signal_time' => date('Y-m-d H:i:s', strtotime("-$i days")),
                'outcome' => $outcome,
                'profit_loss' => $profit_loss
            );
        }
        
        return $signals;
    }
    
    /**
     * Insert signal and result
     */
    private function insertSignal($signal) {
        $esc_id = $this->conn->real_escape_string($signal['signal_id']);
        $esc_coin = $this->conn->real_escape_string($signal['coin_symbol']);
        $esc_tier = $this->conn->real_escape_string($signal['tier']);
        
        // Insert signal
        $query = "INSERT INTO meme_signals 
            (signal_id, coin_symbol, tier, explosive_volume, parabolic_momentum, 
             rsi_hype_zone, social_momentum_proxy, volume_concentration, 
             breakout_4h, low_market_cap_bonus, total_score, verdict, signal_time)
            VALUES 
            ('$esc_id', '$esc_coin', '$esc_tier', {$signal['explosive_volume']}, 
             {$signal['parabolic_momentum']}, {$signal['rsi_hype_zone']}, 
             {$signal['social_momentum_proxy']}, {$signal['volume_concentration']}, 
             {$signal['breakout_4h']}, {$signal['low_market_cap_bonus']}, 
             {$signal['total_score']}, '{$signal['verdict']}', '{$signal['signal_time']}')";
        
        $this->conn->query($query);
        
        // Insert result
        $esc_outcome = $this->conn->real_escape_string($signal['outcome']);
        $resolved_at = date('Y-m-d H:i:s', strtotime($signal['signal_time'] . ' +2 hours'));
        
        $query = "INSERT INTO meme_signal_results 
            (signal_id, outcome, profit_loss_pct, resolved_at)
            VALUES ('$esc_id', '$esc_outcome', {$signal['profit_loss']}, '$resolved_at')";
        
        $this->conn->query($query);
    }
    
    /**
     * Create initial model with default weights
     */
    private function createInitialModel() {
        // Check if model exists
        $res = $this->conn->query("SELECT COUNT(*) as cnt FROM meme_ml_models");
        $row = $res->fetch_assoc();
        
        if ($row['cnt'] > 0) {
            $this->output[] = "Model already exists, skipping initial model creation";
            return;
        }
        
        $default_weights = array(
            'explosive_volume' => 0.25,
            'parabolic_momentum' => 0.20,
            'rsi_hype_zone' => 0.15,
            'social_momentum_proxy' => 0.15,
            'volume_concentration' => 0.10,
            'breakout_4h' => 0.10,
            'low_market_cap_bonus' => 0.05
        );
        
        $model_id = 'meme_ml_v1_initial';
        $esc_id = $this->conn->real_escape_string($model_id);
        $esc_weights = $this->conn->real_escape_string(json_encode($default_weights));
        
        $query = "INSERT INTO meme_ml_models 
            (model_id, model_version, weights_json, feature_importance_json, 
             metrics_json, sample_count, is_active, created_at)
            VALUES 
            ('$esc_id', 1, '$esc_weights', '$esc_weights', 
             '{\"accuracy\":0.5,\"precision_score\":0.5,\"recall\":0.5,\"f1_score\":0.5}', 
             0, TRUE, NOW())";
        
        $this->conn->query($query);
        $this->output[] = "Created initial model: $model_id";
        
        // Log the creation
        $this->conn->query("INSERT INTO meme_ml_training_log 
            (model_id, action, message, created_at)
            VALUES ('$esc_id', 'init', 'Initial model created with default weights', NOW())");
    }
    
    /**
     * Reset all ML data (use with caution)
     */
    public function reset() {
        $this->conn->query("DROP TABLE IF EXISTS meme_ml_predictions");
        $this->conn->query("DROP TABLE IF EXISTS meme_ml_training_log");
        $this->conn->query("DROP TABLE IF EXISTS meme_ml_models");
        $this->conn->query("DROP TABLE IF EXISTS meme_signal_results");
        $this->conn->query("DROP TABLE IF EXISTS meme_signals");
        
        $this->output[] = "All ML tables dropped";
        
        return $this->init();
    }
}

// CLI / Web endpoint
$action = isset($_GET['action']) ? $_GET['action'] : 'init';
$init = new MLDatabaseInit($conn);

if ($action === 'init') {
    $result = $init->init();
    echo json_encode($result, JSON_PRETTY_PRINT);
} elseif ($action === 'reset') {
    $result = $init->reset();
    echo json_encode($result, JSON_PRETTY_PRINT);
} elseif ($action === 'status') {
    $tables = array('meme_signals', 'meme_signal_results', 'meme_ml_models', 'meme_ml_predictions');
    $status = array();
    foreach ($tables as $table) {
        $res = $conn->query("SELECT COUNT(*) as cnt FROM $table");
        $row = $res->fetch_assoc();
        $status[$table] = $row['cnt'];
    }
    echo json_encode(array('ok' => true, 'table_counts' => $status));
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
