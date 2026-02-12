<?php
/**
 * Alpha Engine PHP Bridge
 * DEEPSEEK MOTHERLOAD Implementation
 * Bridge between PHP frontend and Python Alpha Engine
 */

require_once dirname(__FILE__) . '/db_connect.php';

class AlphaEngineBridge {
    private $python_path;
    private $alpha_engine_path;
    
    public function __construct() {
        // Adjust path for Windows environment
        $this->python_path = 'python'; // Windows uses 'python', Linux uses 'python3'
        $this->alpha_engine_path = dirname(__FILE__) . '/../alpha_engine';
        
        // Windows-specific path adjustment
        if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
            $this->python_path = 'python';
        } else {
            $this->python_path = 'python3';
        }
    }
    
    public function generate_picks($regime = null) {
        $command = $this->python_path . ' ' . $this->alpha_engine_path . '/alpha_engine.py';
        if ($regime) {
            $command .= ' --regime ' . escapeshellarg($regime);
        }
        
        $output = shell_exec($command . ' 2>&1');
        
        if ($output === null) {
            return ['error' => 'Failed to execute Alpha Engine'];
        }
        
        $result = json_decode($output, true);
        
        if (json_last_error() !== JSON_ERROR_NONE) {
            return ['error' => 'Invalid JSON response from Alpha Engine: ' . json_last_error_msg()];
        }
        
        return $result;
    }
    
    public function get_factor_scores($ticker) {
        $command = $this->python_path . ' ' . $this->alpha_engine_path . '/factor_calculator.py';
        $command .= ' --ticker ' . escapeshellarg($ticker);
        
        $output = shell_exec($command . ' 2>&1');
        
        if ($output === null) {
            return ['error' => 'Failed to calculate factor scores'];
        }
        
        return json_decode($output, true);
    }
    
    public function update_dashboard() {
        $picks = $this->generate_picks();
        
        if (isset($picks['error'])) {
            return ['success' => false, 'error' => $picks['error']];
        }
        
        // Update database with new picks
        $conn = db_connect();
        
        $picks_generated = 0;
        
        foreach ($picks['picks'] as $pick) {
            $ticker = $conn->real_escape_string($pick['ticker']);
            $strategy = $conn->real_escape_string($pick['strategy']);
            $score = (float)$pick['score'];
            $rationale = $conn->real_escape_string($pick['rationale']);
            $entry_price = (float)$pick['entry_price'];
            
            $sql = "INSERT INTO alpha_picks (ticker, strategy, score, rationale, entry_price, created_at) 
                    VALUES ('$ticker', '$strategy', $score, '$rationale', $entry_price, NOW())
                    ON DUPLICATE KEY UPDATE 
                    score = VALUES(score), 
                    rationale = VALUES(rationale), 
                    entry_price = VALUES(entry_price)";
            
            if ($conn->query($sql)) {
                $picks_generated++;
            }
        }
        
        return ['success' => true, 'picks_generated' => $picks_generated];
    }
    
    public function get_regime() {
        $command = $this->python_path . ' ' . $this->alpha_engine_path . '/regime_detector.py';
        $output = shell_exec($command . ' 2>&1');
        
        if ($output === null) {
            return ['error' => 'Failed to detect regime'];
        }
        
        return json_decode($output, true);
    }
    
    public function health_check() {
        $checks = [
            'python_executable' => $this->check_python_executable(),
            'alpha_engine_files' => $this->check_alpha_engine_files(),
            'database_connection' => $this->check_database_connection()
        ];
        
        $all_healthy = true;
        foreach ($checks as $check => $result) {
            if (!$result['healthy']) {
                $all_healthy = false;
                break;
            }
        }
        
        return [
            'healthy' => $all_healthy,
            'checks' => $checks,
            'timestamp' => date('Y-m-d H:i:s')
        ];
    }
    
    private function check_python_executable() {
        $output = shell_exec($this->python_path . ' --version 2>&1');
        return [
            'healthy' => !empty($output),
            'message' => $output ? 'Python executable found' : 'Python executable not found'
        ];
    }
    
    private function check_alpha_engine_files() {
        $required_files = [
            'alpha_engine.py',
            'factor_calculator.py', 
            'regime_detector.py'
        ];
        
        $missing_files = [];
        foreach ($required_files as $file) {
            if (!file_exists($this->alpha_engine_path . '/' . $file)) {
                $missing_files[] = $file;
            }
        }
        
        return [
            'healthy' => empty($missing_files),
            'message' => empty($missing_files) ? 'All Alpha Engine files present' : 'Missing files: ' . implode(', ', $missing_files)
        ];
    }
    
    private function check_database_connection() {
        try {
            $conn = db_connect();
            $result = $conn->query("SELECT 1");
            return [
                'healthy' => ($result !== false),
                'message' => 'Database connection successful'
            ];
        } catch (Exception $e) {
            return [
                'healthy' => false,
                'message' => 'Database connection failed: ' . $e->getMessage()
            ];
        }
    }
}

// API Endpoint
header('Content-Type: application/json');

if (isset($_GET['action'])) {
    $bridge = new AlphaEngineBridge();
    
    switch ($_GET['action']) {
        case 'generate_picks':
            $result = $bridge->generate_picks($_GET['regime'] ?? null);
            echo json_encode($result);
            break;
            
        case 'factor_scores':
            if (isset($_GET['ticker'])) {
                $result = $bridge->get_factor_scores($_GET['ticker']);
                echo json_encode($result);
            } else {
                echo json_encode(['error' => 'Ticker parameter required']);
            }
            break;
            
        case 'update_dashboard':
            $result = $bridge->update_dashboard();
            echo json_encode($result);
            break;
            
        case 'get_regime':
            $result = $bridge->get_regime();
            echo json_encode($result);
            break;
            
        case 'health_check':
            $result = $bridge->health_check();
            echo json_encode($result);
            break;
            
        default:
            echo json_encode(['error' => 'Unknown action']);
    }
} else {
    echo json_encode(['error' => 'No action specified']);
}
?>