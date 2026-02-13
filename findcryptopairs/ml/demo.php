<?php
/**
 * Backtesting Framework Demo
 * 
 * Demonstrates usage of the backtesting engine with sample data.
 */

require_once __DIR__ . '/backtest.php';
require_once __DIR__ . '/backtest_report.php';

echo "=== Meme Coin Backtesting Framework Demo ===\n\n";

// ============================================================
// Demo 1: Basic Backtest
// ============================================================
echo "Demo 1: Running basic backtest...\n";

try {
    $engine = new BacktestEngine([
        'initial_capital' => 10000,
        'position_size_pct' => 0.1,
        'risk_per_trade_pct' => 0.02
    ]);
    
    $strategy = [
        'tp1_exit_pct' => 0.33,
        'tp2_exit_pct' => 0.33,
        'tp3_exit_pct' => 0.34,
        'max_hold_hours' => 168
    ];
    
    // Note: This will only work if you have signal data in your database
    // For demo purposes, we'll show the expected output format
    
    echo "Strategy Configuration:\n";
    echo json_encode($strategy, JSON_PRETTY_PRINT) . "\n\n";
    
    echo "To run actual backtest:\n";
    echo "  \$result = \$engine->runBacktest('2024-01-01', '2024-12-31', \$strategy);\n\n";
    
} catch (Exception $e) {
    echo "Note: " . $e->getMessage() . "\n";
    echo "This is expected if no database is configured.\n\n";
}

// ============================================================
// Demo 2: Walk-Forward Analysis
// ============================================================
echo "Demo 2: Walk-Forward Analysis Configuration\n";
echo "=============================================\n";

$walkForwardConfig = [
    'description' => 'Train on 6 months, test on 2 months',
    'train_window_days' => 180,
    'test_window_days' => 60,
    'total_period' => '2023-01-01 to 2024-12-31',
    'expected_folds' => 'Approximately 8 folds'
];

echo json_encode($walkForwardConfig, JSON_PRETTY_PRINT) . "\n\n";

// ============================================================
// Demo 3: Strategy Comparison
// ============================================================
echo "Demo 3: Strategy Comparison\n";
echo "============================\n";

$strategies = [
    'conservative' => [
        'tp1_exit_pct' => 0.5,
        'tp2_exit_pct' => 0.3,
        'tp3_exit_pct' => 0.2,
        'max_hold_hours' => 72,
        'description' => 'Quick exits, smaller but consistent gains'
    ],
    'rule_based' => [
        'tp1_exit_pct' => 0.33,
        'tp2_exit_pct' => 0.33,
        'tp3_exit_pct' => 0.34,
        'max_hold_hours' => 168,
        'description' => 'Balanced approach, equal position scaling'
    ],
    'aggressive' => [
        'tp1_exit_pct' => 0.25,
        'tp2_exit_pct' => 0.25,
        'tp3_exit_pct' => 0.5,
        'max_hold_hours' => 336,
        'description' => 'Hold longer for bigger moves'
    ]
];

echo json_encode($strategies, JSON_PRETTY_PRINT) . "\n\n";

// ============================================================
// Demo 4: Expected Metrics Output
// ============================================================
echo "Demo 4: Sample Backtest Output Format\n";
echo "======================================\n";

$sampleOutput = [
    'backtest_id' => 'abc123def456',
    'backtest_period' => [
        'start' => '2024-01-01',
        'end' => '2024-12-31'
    ],
    'total_signals' => 500,
    'resolved_signals' => 450,
    'unresolved_signals' => 50,
    
    'overall_metrics' => [
        'win_rate' => 0.42,
        'expectancy' => 0.08,
        'sharpe_ratio' => 1.2,
        'max_drawdown' => -0.15,
        'profit_factor' => 1.5,
        'avg_trade_duration_hours' => 18.5,
        'total_return' => 0.85,
        'final_equity' => 18500.00
    ],
    
    'by_tier' => [
        'lean_buy' => ['signals' => 200, 'win_rate' => 0.35, 'avg_return' => 0.025],
        'moderate_buy' => ['signals' => 150, 'win_rate' => 0.45, 'avg_return' => 0.045],
        'strong_buy' => ['signals' => 100, 'win_rate' => 0.52, 'avg_return' => 0.085]
    ],
    
    'by_market_regime' => [
        'bull' => ['signals' => 200, 'win_rate' => 0.55, 'avg_return' => 0.065],
        'bear' => ['signals' => 150, 'win_rate' => 0.25, 'avg_return' => -0.025],
        'sideways' => ['signals' => 100, 'win_rate' => 0.35, 'avg_return' => 0.015]
    ],
    
    'statistical_validity' => [
        'sample_size_sufficient' => true,
        'min_recommended_signals' => 350,
        'win_rate_95ci_lower' => 0.38,
        'win_rate_95ci_upper' => 0.46,
        'confidence_level' => 0.95,
        'note' => 'Sample size sufficient for statistical validity'
    ],
    
    'monthly_performance' => [
        ['month' => '2024-01', 'trades' => 42, 'wins' => 18, 'losses' => 24, 'win_rate' => 0.43, 'total_return_pct' => 3.5],
        ['month' => '2024-02', 'trades' => 38, 'wins' => 16, 'losses' => 22, 'win_rate' => 0.42, 'total_return_pct' => 2.8],
        ['month' => '2024-03', 'trades' => 45, 'wins' => 22, 'losses' => 23, 'win_rate' => 0.49, 'total_return_pct' => 5.2]
    ]
];

echo json_encode($sampleOutput, JSON_PRETTY_PRINT) . "\n\n";

// ============================================================
// Demo 5: API Usage Examples
// ============================================================
echo "Demo 5: API Usage Examples\n";
echo "===========================\n\n";

echo "1. Run backtest via HTTP:\n";
echo "   GET /ml/backtest.php?action=run&start=2024-01-01&end=2024-12-31\n\n";

echo "2. Walk-forward analysis:\n";
echo "   GET /ml/backtest.php?action=walkforward&train_days=180&test_days=60\n\n";

echo "3. Compare strategies:\n";
echo "   GET /ml/backtest.php?action=compare&strategies=conservative,rule_based,aggressive\n\n";

echo "4. Get metrics:\n";
echo "   GET /ml/backtest.php?action=metrics&backtest_id=abc123\n\n";

echo "5. Get equity curve:\n";
echo "   GET /ml/backtest.php?action=equity_curve&backtest_id=abc123\n\n";

// ============================================================
// Demo 6: Transaction Cost Analysis
// ============================================================
echo "Demo 6: Transaction Cost Impact Analysis\n";
echo "=========================================\n\n";

$capital = 10000;
$trades = 100;

$costScenarios = [
    'low_fees' => [
        'trading_fee' => 0.0008,  // 0.08% (Binance VIP)
        'slippage' => 0.0005,
        'spread' => 0.001,
        'description' => 'Low fee exchange, high volume'
    ],
    'medium_fees' => [
        'trading_fee' => 0.001,  // 0.1%
        'slippage' => 0.001,
        'spread' => 0.002,
        'description' => 'Standard exchange conditions'
    ],
    'high_fees' => [
        'trading_fee' => 0.005,  // 0.5%
        'slippage' => 0.002,
        'spread' => 0.003,
        'description' => 'High fee exchange, low volume'
    ]
];

foreach ($costScenarios as $name => $scenario) {
    $totalCostPerTrade = ($scenario['trading_fee'] * 2) + $scenario['slippage'] + $scenario['spread'];
    $totalCost = $totalCostPerTrade * $trades;
    $costPct = ($totalCost / $capital) * 100;
    
    echo "Scenario: {$name}\n";
    echo "  Description: {$scenario['description']}\n";
    echo "  Cost per trade: " . round($totalCostPerTrade * 100, 3) . "%\n";
    echo "  Total cost ({$trades} trades): \$" . round($totalCost, 2) . "\n";
    echo "  Impact on capital: " . round($costPct, 2) . "%\n\n";
}

// ============================================================
// Demo 7: Key Metrics Explained
// ============================================================
echo "Demo 7: Key Metrics Explained\n";
echo "==============================\n\n";

$metricsExplained = [
    'Win Rate' => [
        'formula' => 'Winning Trades / Total Trades',
        'interpretation' => '40-50% is typical for trend-following strategies',
        'good_value' => '> 45%',
        'warning' => '< 35% suggests poor signal quality'
    ],
    'Expectancy' => [
        'formula' => '(Win% × Avg Win) - (Loss% × |Avg Loss|)',
        'interpretation' => 'Expected return per trade as percentage',
        'good_value' => '> 0.05 (5%)',
        'warning' => '< 0 suggests unprofitable strategy'
    ],
    'Sharpe Ratio' => [
        'formula' => '(Return - Risk Free Rate) / Std Dev of Returns',
        'interpretation' => 'Risk-adjusted return measure',
        'good_value' => '> 1.0',
        'warning' => '< 0.5 suggests poor risk-adjusted returns'
    ],
    'Max Drawdown' => [
        'formula' => 'Peak Equity - Trough Equity / Peak Equity',
        'interpretation' => 'Largest peak-to-trough decline',
        'good_value' => '< 20%',
        'warning' => '> 30% suggests excessive risk'
    ],
    'Profit Factor' => [
        'formula' => 'Gross Profit / Gross Loss',
        'interpretation' => 'How much profit per unit of loss',
        'good_value' => '> 1.5',
        'warning' => '< 1.0 means losing money overall'
    ]
];

foreach ($metricsExplained as $metric => $info) {
    echo "{$metric}:\n";
    echo "  Formula: {$info['formula']}\n";
    echo "  Interpretation: {$info['interpretation']}\n";
    echo "  Good Value: {$info['good_value']}\n";
    echo "  Warning: {$info['warning']}\n\n";
}

// ============================================================
// Summary
// ============================================================
echo "=== Summary ===\n\n";
echo "The backtesting framework provides:\n";
echo "✓ Chronological signal processing (no lookahead bias)\n";
echo "✓ Realistic transaction cost modeling\n";
echo "✓ Walk-forward validation\n";
echo "✓ Comprehensive performance metrics\n";
echo "✓ Statistical validity checks\n";
echo "✓ HTML/JSON/CSV report generation\n\n";

echo "Next Steps:\n";
echo "1. Import historical OHLCV data using HistoricalDataManager\n";
echo "2. Ensure ml_signals table has historical predictions\n";
echo "3. Run backtest: \$engine->runBacktest(...)\n";
echo "4. Generate reports: php backtest_report.php -i <id>\n\n";

echo "For more details, see README.md\n";
