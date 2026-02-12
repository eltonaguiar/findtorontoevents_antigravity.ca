<?php
/**
 * Unified Predictions Leaderboard API - Week 1 Foundation
 * Returns consolidated performance data from high-performing systems
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Mock data for Week 1 (replace with real DB queries in Phase 2)
$highPerformers = [
  [
    'name' => 'Cursor Genius',
    'return_pct' => 1324.31,
    'win_rate' => 65.3,
    'picks' => 308,
    'status' => 'active'
  ],
  [
    'name' => 'Sector Rotation',
    'return_pct' => 354.24,
    'win_rate' => 64.0,
    'picks' => 275,
    'status' => 'active'
  ],
  [
    'name' => 'Sports Betting',
    'return_pct' => 25.3,
    'win_rate' => 33.3,
    'picks' => 3,
    'status' => 'active'
  ],
  [
    'name' => 'Blue Chip Growth',
    'return_pct' => 1648.0,
    'win_rate' => 60.57,
    'picks' => 350,
    'status' => 'active'
  ]
];

$regime = [
  'hmm_state' => 'sideways',
  'confidence' => 99.94,
  'hurst' => 0.560,
  'vix' => 18.12
];

echo json_encode([
  'success' => true,
  'timestamp' => date('Y-m-d H:i:s'),
  'high_performers' => $highPerformers,
  'market_regime' => $regime,
  'message' => 'Week 1 Foundation API - Mock data. Real integration in Phase 2.'
]);