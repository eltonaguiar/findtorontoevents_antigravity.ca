#!/usr/bin/env python3
"""
Algorithm Pauser - Automated Algorithm Performance Monitoring
DEEPSEEK MOTHERLOAD Implementation
Purpose: Automatically pause failing algorithms based on performance thresholds
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

class AlgorithmPauser:
    def __init__(self):
        self.performance_thresholds = {
            'win_rate': 40.0,  # Minimum win rate %
            'sharpe_ratio': 0.1,  # Minimum Sharpe ratio
            'max_drawdown': -20.0,  # Maximum drawdown %
            'min_trades': 10,  # Minimum trades for evaluation
            'consecutive_losses': 5,  # Max consecutive losses
            'recent_performance_weight': 0.7  # Weight for recent performance
        }
        
    def evaluate_algorithm_performance(self, algorithm_data):
        """Evaluate algorithm performance against thresholds"""
        
        evaluation = {
            'algorithm': algorithm_data.get('name', 'Unknown'),
            'total_trades': algorithm_data.get('total_trades', 0),
            'win_rate': algorithm_data.get('win_rate', 0),
            'sharpe_ratio': algorithm_data.get('sharpe_ratio', 0),
            'max_drawdown': algorithm_data.get('max_drawdown', 0),
            'consecutive_losses': algorithm_data.get('consecutive_losses', 0),
            'recent_performance': algorithm_data.get('recent_performance', 0),
            'status': 'ACTIVE',
            'reasons': [],
            'recommendation': 'CONTINUE'
        }
        
        # Check if enough trades for evaluation
        if evaluation['total_trades'] < self.performance_thresholds['min_trades']:
            evaluation['status'] = 'EVALUATING'
            evaluation['recommendation'] = 'CONTINUE'
            evaluation['reasons'].append(f"Insufficient trades ({evaluation['total_trades']} < {self.performance_thresholds['min_trades']})")
            return evaluation
        
        # Check performance thresholds
        failures = []
        
        if evaluation['win_rate'] < self.performance_thresholds['win_rate']:
            failures.append(f"Win rate {evaluation['win_rate']:.1f}% < {self.performance_thresholds['win_rate']}%")
        
        if evaluation['sharpe_ratio'] < self.performance_thresholds['sharpe_ratio']:
            failures.append(f"Sharpe ratio {evaluation['sharpe_ratio']:.3f} < {self.performance_thresholds['sharpe_ratio']}")
        
        if evaluation['max_drawdown'] < self.performance_thresholds['max_drawdown']:
            failures.append(f"Max drawdown {evaluation['max_drawdown']:.1f}% < {self.performance_thresholds['max_drawdown']}%")
        
        if evaluation['consecutive_losses'] >= self.performance_thresholds['consecutive_losses']:
            failures.append(f"Consecutive losses {evaluation['consecutive_losses']} >= {self.performance_thresholds['consecutive_losses']}")
        
        # Calculate weighted performance score
        recent_weight = self.performance_thresholds['recent_performance_weight']
        historical_weight = 1 - recent_weight
        
        performance_score = (
            recent_weight * evaluation['recent_performance'] +
            historical_weight * evaluation['win_rate']
        )
        
        if failures:
            evaluation['status'] = 'FAILING'
            evaluation['recommendation'] = 'PAUSE'
            evaluation['reasons'] = failures
            evaluation['performance_score'] = performance_score
        else:
            evaluation['status'] = 'HEALTHY'
            evaluation['recommendation'] = 'CONTINUE'
            evaluation['performance_score'] = performance_score
        
        return evaluation
    
    def analyze_all_algorithms(self, algorithms_data):
        """Analyze all algorithms and generate pause recommendations"""
        
        evaluations = []
        algorithms_to_pause = []
        
        for algo_data in algorithms_data:
            evaluation = self.evaluate_algorithm_performance(algo_data)
            evaluations.append(evaluation)
            
            if evaluation['recommendation'] == 'PAUSE':
                algorithms_to_pause.append({
                    'algorithm': evaluation['algorithm'],
                    'reasons': evaluation['reasons'],
                    'performance_score': evaluation['performance_score']
                })
        
        return {
            'evaluations': evaluations,
            'algorithms_to_pause': algorithms_to_pause,
            'total_algorithms': len(algorithms_data),
            'algorithms_paused': len(algorithms_to_pause),
            'pause_rate': len(algorithms_to_pause) / len(algorithms_data) if algorithms_data else 0
        }
    
    def generate_pause_commands(self, algorithms_to_pause):
        """Generate actual commands to pause algorithms"""
        
        commands = []
        
        for algo in algorithms_to_pause:
            # Generate PHP command to update algorithm status
            php_command = f"""
// Pause algorithm: {algo['algorithm']}
$update_sql = "UPDATE algorithms SET active = 0 WHERE name = '{algo['algorithm']}';";
// Log the pause
$log_sql = "INSERT INTO algorithm_pause_log (algorithm_name, pause_reason, paused_at) 
            VALUES ('{algo['algorithm']}', '{'; '.join(algo['reasons'])}', NOW());";
"""
            
            commands.append({
                'algorithm': algo['algorithm'],
                'php_command': php_command,
                'reasons': algo['reasons']
            })
        
        return commands
    
    def generate_performance_report(self, analysis_results):
        """Generate comprehensive performance report"""
        
        healthy_algorithms = [e for e in analysis_results['evaluations'] if e['status'] == 'HEALTHY']
        failing_algorithms = [e for e in analysis_results['evaluations'] if e['status'] == 'FAILING']
        evaluating_algorithms = [e for e in analysis_results['evaluations'] if e['status'] == 'EVALUATING']
        
        report = {
            'summary': {
                'total_algorithms': analysis_results['total_algorithms'],
                'healthy_algorithms': len(healthy_algorithms),
                'failing_algorithms': len(failing_algorithms),
                'evaluating_algorithms': len(evaluating_algorithms),
                'pause_rate': analysis_results['pause_rate'] * 100
            },
            'top_performers': sorted(healthy_algorithms, key=lambda x: x['performance_score'], reverse=True)[:5],
            'worst_performers': sorted(failing_algorithms, key=lambda x: x['performance_score'])[:5],
            'common_failure_reasons': self.analyze_failure_patterns(failing_algorithms)
        }
        
        return report
    
    def analyze_failure_patterns(self, failing_algorithms):
        """Analyze common failure patterns"""
        
        failure_reasons = {}
        
        for algo in failing_algorithms:
            for reason in algo['reasons']:
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        return sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)

def load_algorithm_data(file_path):
    """Load algorithm performance data"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Algorithm data file {file_path} not found")
        return []

def main():
    """Main execution function"""
    
    # Load algorithm data
    algorithms_data = load_algorithm_data('data/algorithms_performance.json')
    
    if not algorithms_data:
        # Create sample data based on your actual failing algorithms
        algorithms_data = [
            {
                'name': 'ETF Masters', 'total_trades': 425, 'win_rate': 3.37, 
                'sharpe_ratio': -0.5, 'max_drawdown': -25.0, 'consecutive_losses': 8,
                'recent_performance': 2.5
            },
            {
                'name': 'Sector Momentum', 'total_trades': 30, 'win_rate': 0.0,
                'sharpe_ratio': -1.2, 'max_drawdown': -35.0, 'consecutive_losses': 30,
                'recent_performance': -5.0
            },
            {
                'name': 'Cursor Genius', 'total_trades': 308, 'win_rate': 65.26,
                'sharpe_ratio': 0.4565, 'max_drawdown': -8.0, 'consecutive_losses': 3,
                'recent_performance': 12.5
            },
            {
                'name': 'Crypto Scanner', 'total_trades': 7, 'win_rate': 0.0,
                'sharpe_ratio': -2.25, 'max_drawdown': -15.0, 'consecutive_losses': 7,
                'recent_performance': -8.0
            }
        ]
    
    # Initialize pauser
    pauser = AlgorithmPauser()
    
    # Analyze all algorithms
    print("=== ALGORITHM PERFORMANCE ANALYSIS ===")
    analysis = pauser.analyze_all_algorithms(algorithms_data)
    
    print(f"Total Algorithms: {analysis['total_algorithms']}")
    print(f"Algorithms to Pause: {analysis['algorithms_paused']}")
    print(f"Pause Rate: {analysis['pause_rate']:.1%}")
    
    # Generate performance report
    report = pauser.generate_performance_report(analysis)
    
    print("\n=== PERFORMANCE REPORT ===")
    print(f"Healthy Algorithms: {report['summary']['healthy_algorithms']}")
    print(f"Failing Algorithms: {report['summary']['failing_algorithms']}")
    print(f"Evaluating Algorithms: {report['summary']['evaluating_algorithms']}")
    
    print("\n=== TOP PERFORMERS ===")
    for algo in report['top_performers']:
        print(f"{algo['algorithm']}: Score {algo['performance_score']:.1f}, Win Rate {algo['win_rate']:.1f}%")
    
    print("\n=== WORST PERFORMERS ===")
    for algo in report['worst_performers']:
        print(f"{algo['algorithm']}: Score {algo['performance_score']:.1f}, Reasons: {', '.join(algo['reasons'])}")
    
    print("\n=== COMMON FAILURE PATTERNS ===")
    for reason, count in report['common_failure_reasons']:
        print(f"{reason}: {count} algorithms")
    
    # Generate pause commands
    print("\n=== PAUSE COMMANDS ===")
    commands = pauser.generate_pause_commands(analysis['algorithms_to_pause'])
    
    for cmd in commands:
        print(f"\nAlgorithm: {cmd['algorithm']}")
        print(f"Reasons: {', '.join(cmd['reasons'])}")
        print("PHP Command:")
        print(cmd['php_command'])

if __name__ == "__main__":
    main()