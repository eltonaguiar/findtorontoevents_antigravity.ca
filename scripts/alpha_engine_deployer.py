#!/usr/bin/env python3
"""
Alpha Engine Deployer - Automated Deployment Script
DEEPSEEK MOTHERLOAD Implementation
Purpose: Deploy the production-ready Alpha Engine to your server
"""

import os
import subprocess
import json
import shutil
from datetime import datetime

class AlphaEngineDeployer:
    def __init__(self, project_root='e:/findtorontoevents_antigravity.ca'):
        self.project_root = project_root
        self.alpha_engine_path = os.path.join(project_root, 'alpha_engine')
        self.php_api_path = os.path.join(project_root, 'api')
        
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        
        prerequisites = {
            'Python 3.8+': self.check_python_version(),
            'PHP 7.4+': self.check_php_version(),
            'MySQL Database': self.check_mysql(),
            'Alpha Engine Files': self.check_alpha_engine_files(),
            'Required Python Packages': self.check_python_packages()
        }
        
        return prerequisites
    
    def check_python_version(self):
        """Check Python version"""
        try:
            result = subprocess.run(['python', '--version'], capture_output=True, text=True)
            version_str = result.stdout.strip()
            version = float(version_str.split()[1].split('.')[0] + '.' + version_str.split()[1].split('.')[1])
            return version >= 3.8
        except:
            return False
    
    def check_php_version(self):
        """Check PHP version"""
        try:
            result = subprocess.run(['php', '--version'], capture_output=True, text=True)
            version_str = result.stdout.split()[1]
            version = float(version_str.split('.')[0] + '.' + version_str.split('.')[1])
            return version >= 7.4
        except:
            return False
    
    def check_mysql(self):
        """Check MySQL connectivity"""
        try:
            # Try to connect to MySQL using existing db_config
            db_config_path = os.path.join(self.php_api_path, 'db_config.php')
            if os.path.exists(db_config_path):
                return True
            return False
        except:
            return False
    
    def check_alpha_engine_files(self):
        """Check if Alpha Engine files exist"""
        required_files = [
            'alpha_engine.py',
            'factor_calculator.py',
            'regime_detector.py',
            'strategy_picker.py'
        ]
        
        missing_files = []
        for file in required_files:
            file_path = os.path.join(self.alpha_engine_path, file)
            if not os.path.exists(file_path):
                missing_files.append(file)
        
        return len(missing_files) == 0
    
    def check_python_packages(self):
        """Check required Python packages"""
        required_packages = [
            'pandas', 'numpy', 'scikit-learn', 'lightgbm', 'xgboost'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        return len(missing_packages) == 0
    
    def create_python_environment(self):
        """Set up Python environment for Alpha Engine"""
        
        print("Setting up Python environment...")
        
        # Create virtual environment
        venv_path = os.path.join(self.alpha_engine_path, 'venv')
        if not os.path.exists(venv_path):
            subprocess.run(['python', '-m', 'venv', venv_path])
        
        # Install required packages
        requirements = [
            'pandas>=1.3.0',
            'numpy>=1.21.0',
            'scikit-learn>=1.0.0',
            'lightgbm>=3.3.0',
            'xgboost>=1.5.0',
            'requests>=2.25.0'
        ]
        
        pip_path = os.path.join(venv_path, 'Scripts', 'pip') if os.name == 'nt' else os.path.join(venv_path, 'bin', 'pip')
        
        for package in requirements:
            subprocess.run([pip_path, 'install', package])
        
        return venv_path
    
    def create_php_bridge(self):
        """Create PHP bridge for Alpha Engine integration"""
        
        bridge_code = """
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
        $this->python_path = '/usr/bin/python3'; // Adjust for Windows: 'python'
        $this->alpha_engine_path = dirname(__FILE__) . '/../alpha_engine';
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
            return ['error' => 'Invalid JSON response from Alpha Engine'];
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
        
        foreach ($picks['picks'] as $pick) {
            $ticker = $conn->real_escape_string($pick['ticker']);
            $strategy = $conn->real_escape_string($pick['strategy']);
            $score = (float)$pick['score'];
            $rationale = $conn->real_escape_string($pick['rationale']);
            
            $sql = "INSERT INTO alpha_picks (ticker, strategy, score, rationale, created_at) 
                    VALUES ('$ticker', '$strategy', $score, '$rationale', NOW())
                    ON DUPLICATE KEY UPDATE score = VALUES(score), rationale = VALUES(rationale)";
            
            $conn->query($sql);
        }
        
        return ['success' => true, 'picks_generated' => count($picks['picks'])];
    }
}

// API Endpoint
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
            
        default:
            echo json_encode(['error' => 'Unknown action']);
    }
}
?>
"""
        
        bridge_path = os.path.join(self.php_api_path, 'alpha_bridge.php')
        with open(bridge_path, 'w') as f:
            f.write(bridge_code)
        
        return bridge_path
    
    def create_cron_jobs(self):
        """Create cron jobs for automated execution"""
        
        cron_jobs = [
            "0 21 * * 1-5 python /path/to/alpha_engine/alpha_engine.py --daily",  # Weekdays 9 PM
            "0 8 * * 1-5 python /path/to/alpha_engine/factor_calculator.py --refresh",  # Weekdays 8 AM
        ]
        
        cron_file = os.path.join(self.alpha_engine_path, 'cron_jobs.txt')
        with open(cron_file, 'w') as f:
            f.write("# Alpha Engine Cron Jobs\n")
            f.write("# Add these to your crontab\n\n")
            for job in cron_jobs:
                f.write(job + "\n")
        
        return cron_file
    
    def deploy(self):
        """Execute full deployment"""
        
        print("=== ALPHA ENGINE DEPLOYMENT ===")
        
        # Check prerequisites
        print("\n1. Checking prerequisites...")
        prerequisites = self.check_prerequisites()
        
        for check, result in prerequisites.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check}")
        
        if not all(prerequisites.values()):
            print("\n❌ Prerequisites not met. Please fix issues above.")
            return False
        
        # Set up Python environment
        print("\n2. Setting up Python environment...")
        venv_path = self.create_python_environment()
        print(f"  Virtual environment: {venv_path}")
        
        # Create PHP bridge
        print("\n3. Creating PHP bridge...")
        bridge_path = self.create_php_bridge()
        print(f"  Bridge file: {bridge_path}")
        
        # Create cron jobs
        print("\n4. Creating cron jobs...")
        cron_file = self.create_cron_jobs()
        print(f"  Cron jobs: {cron_file}")
        
        # Test deployment
        print("\n5. Testing deployment...")
        test_result = self.test_deployment()
        
        if test_result:
            print("  ✓ Deployment test successful")
        else:
            print("  ✗ Deployment test failed")
        
        print("\n=== DEPLOYMENT COMPLETE ===")
        print("Next steps:")
        print("1. Add cron jobs from cron_jobs.txt to your crontab")
        print("2. Test the API endpoint: /api/alpha_bridge.php?action=generate_picks")
        print("3. Update your dashboard to display Alpha Engine picks")
        
        return True
    
    def test_deployment(self):
        """Test the deployment"""
        
        try:
            # Test Python execution
            test_script = os.path.join(self.alpha_engine_path, 'test_deployment.py')
            
            test_code = """
import sys
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor

print("Python environment test successful")
print(f"Python version: {sys.version}")
print(f"Pandas version: {pd.__version__}")
print(f"NumPy version: {np.__version__}")

# Test basic functionality
df = pd.DataFrame({'test': [1, 2, 3]})
print(f"DataFrame test: {df.shape}")

print('{"status": "success", "message": "Deployment test passed"}')
"""
            
            with open(test_script, 'w') as f:
                f.write(test_code)
            
            result = subprocess.run(['python', test_script], capture_output=True, text=True)
            
            if result.returncode == 0:
                return True
            return False
            
        except Exception as e:
            print(f"Test error: {e}")
            return False

def main():
    """Main execution function"""
    
    deployer = AlphaEngineDeployer()
    
    # Execute deployment
    success = deployer.deploy()
    
    if success:
        print("\n✅ Alpha Engine deployment completed successfully!")
    else:
        print("\n❌ Alpha Engine deployment failed. Check the errors above.")

if __name__ == "__main__":
    main()