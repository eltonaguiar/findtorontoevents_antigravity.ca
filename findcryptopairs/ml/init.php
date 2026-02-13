<?php
/**
 * Initialize ML Pipeline
 * Sets up directories, creates sample data, trains initial model
 * 
 * Usage: php init.php
 */

echo "========================================\n";
echo "  Meme Coin ML Pipeline Initialization\n";
echo "========================================\n\n";

$BASE_DIR = dirname(__FILE__);
$MODELS_DIR = $BASE_DIR . '/models/';
$DATA_DIR = $BASE_DIR . '/data/';
$CACHE_DIR = $DATA_DIR . 'cache/';

// Create directories
echo "Creating directories...\n";
$dirs = array($MODELS_DIR, $DATA_DIR, $CACHE_DIR);
foreach ($dirs as $dir) {
    if (!is_dir($dir)) {
        mkdir($dir, 0755, true);
        echo "  Created: {$dir}\n";
    } else {
        echo "  Exists: {$dir}\n";
    }
}

// Check PHP requirements
echo "\nChecking PHP requirements...\n";
$requiredExtensions = array('curl', 'json', 'mysqli');
foreach ($requiredExtensions as $ext) {
    if (extension_loaded($ext)) {
        echo "  ✓ {$ext}\n";
    } else {
        echo "  ✗ {$ext} (required)\n";
        exit(1);
    }
}

// Check Python availability
echo "\nChecking Python availability...\n";
$pythonCmd = null;
foreach (array('python3', 'python') as $cmd) {
    $output = array();
    exec("{$cmd} --version 2>&1", $output, $returnCode);
    if ($returnCode === 0) {
        $pythonCmd = $cmd;
        echo "  ✓ Found: {$output[0]}\n";
        break;
    }
}

if (!$pythonCmd) {
    echo "  ✗ Python not found (required for training)\n";
} else {
    // Check Python packages
    echo "\nChecking Python packages...\n";
    $packages = array('xgboost', 'sklearn', 'numpy', 'pandas');
    foreach ($packages as $pkg) {
        $output = array();
        exec("{$pythonCmd} -c \"import {$pkg}; print('OK')\" 2>&1", $output, $returnCode);
        if ($returnCode === 0 && isset($output[0]) && $output[0] === 'OK') {
            echo "  ✓ {$pkg}\n";
        } else {
            echo "  ✗ {$pkg} (install with: pip install {$pkg})\n";
        }
    }
}

// Test features API
echo "\nTesting features API...\n";
$featuresUrl = 'http' . (isset($_SERVER['HTTPS']) ? 's' : '') . '://' . 
               $_SERVER['HTTP_HOST'] . 
               dirname($_SERVER['SCRIPT_NAME']) . '/features.php?action=features&symbol=DOGE';

$ch = curl_init($featuresUrl);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode === 200 && $response) {
    $data = json_decode($response, true);
    if ($data && isset($data['ok']) && $data['ok']) {
        echo "  ✓ Features API working\n";
        echo "    Symbol: {$data['symbol']}\n";
        echo "    Features: " . count($data['feature_vector']) . "\n";
    } else {
        echo "  ✗ Features API returned error\n";
    }
} else {
    echo "  ✗ Features API not accessible (HTTP {$httpCode})\n";
}

// Generate sample training data
echo "\nGenerating sample training data...\n";
$symbols = array('DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK');
foreach ($symbols as $symbol) {
    $csvFile = $DATA_DIR . "training_data_{$symbol}.csv";
    if (!file_exists($csvFile)) {
        generateSampleData($csvFile, $symbol);
        echo "  Created: {$csvFile}\n";
    } else {
        echo "  Exists: {$csvFile}\n";
    }
}

// Create .htaccess for security
echo "\nCreating security files...\n";
$htaccess = "Options -Indexes\nDeny from all\n<FilesMatch \"\\.(php|json|csv)$\">\n    Allow from all\n</FilesMatch>\n";

$htaccessModels = $MODELS_DIR . '.htaccess';
if (!file_exists($htaccessModels)) {
    file_put_contents($htaccessModels, $htaccess);
    echo "  Created: {$htaccessModels}\n";
}

$htaccessData = $DATA_DIR . '.htaccess';
if (!file_exists($htaccessData)) {
    file_put_contents($htaccessData, $htaccess);
    echo "  Created: {$htaccessData}\n";
}

echo "\n========================================\n";
echo "Initialization complete!\n\n";

if ($pythonCmd) {
    echo "Next steps:\n";
    echo "  1. Train initial model:\n";
    echo "     {$pythonCmd} {$BASE_DIR}/train_model.py --all-symbols\n";
    echo "\n";
    echo "  2. Test prediction:\n";
    echo "     curl \"" . dirname($featuresUrl) . "/predict.php?action=predict&symbol=DOGE\"\n";
} else {
    echo "Warning: Python not found. Install Python 3.7+ to train models.\n";
    echo "The system will use rule-based fallback for predictions.\n";
}

echo "\n";

/**
 * Generate sample training data
 */
function generateSampleData($csvFile, $symbol) {
    $np = new class {
        public function random() { return mt_rand() / mt_getrandmax(); }
        public function normal($mean, $std) {
            // Box-Muller transform
            $u1 = $this->random();
            $u2 = $this->random();
            $mag = $std * sqrt(-2 * log($u1));
            return $mean + $mag * cos(2 * M_PI * $u2);
        }
        public function uniform($min, $max) {
            return $min + ($max - $min) * $this->random();
        }
        public function exponential($lambda) {
            return -log($this->random()) / $lambda;
        }
    };
    
    $samples = array();
    $nSamples = 500;
    
    for ($i = 0; $i < $nSamples; $i++) {
        $sample = array(
            'symbol' => $symbol,
            'return_5m' => $np->normal(0.1, 2.0),
            'return_15m' => $np->normal(0.3, 3.5),
            'return_1h' => $np->normal(0.8, 5.0),
            'return_4h' => $np->normal(2.5, 8.0),
            'return_24h' => $np->normal(5.0, 15.0),
            'volatility_24h' => $np->uniform(0.01, 0.15),
            'volume_ratio' => exp($np->normal(0, 0.5)),
            'reddit_velocity' => $np->exponential(1/20),
            'trends_velocity' => exp($np->normal(0, 0.3)),
            'sentiment_correlation' => $np->uniform(0, 1),
            'btc_trend_4h' => $np->normal(0.2, 1.5),
            'btc_trend_24h' => $np->normal(0.5, 3.0),
            'hour' => mt_rand(0, 23),
            'day_of_week' => mt_rand(0, 6),
            'is_weekend' => (mt_rand(0, 6) >= 5) ? 1 : 0,
            'hit_tp_before_sl' => 0,
            'pnl_pct' => 0,
            'signal_id' => $i + 1,
            'timestamp' => time() - ($i * 3600)
        );
        
        // Generate target based on feature relationships
        $winProb = (
            0.3 * ($sample['return_1h'] > 2 ? 1 : 0) +
            0.2 * ($sample['reddit_velocity'] > 15 ? 1 : 0) +
            0.2 * ($sample['trends_velocity'] > 1.2 ? 1 : 0) +
            0.15 * ($sample['btc_trend_4h'] > 0 ? 1 : 0) +
            0.15 * ($sample['volatility_24h'] < 0.08 ? 1 : 0)
        );
        
        $sample['hit_tp_before_sl'] = ($np->random() < $winProb) ? 1 : 0;
        $sample['pnl_pct'] = $sample['hit_tp_before_sl'] ? $np->uniform(5, 25) : $np->uniform(-10, -2);
        
        $samples[] = $sample;
    }
    
    // Write CSV
    $fp = fopen($csvFile, 'w');
    fputcsv($fp, array_keys($samples[0]));
    foreach ($samples as $s) {
        fputcsv($fp, $s);
    }
    fclose($fp);
}
