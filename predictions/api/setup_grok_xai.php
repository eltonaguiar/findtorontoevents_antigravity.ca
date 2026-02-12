<?php
include 'db_connect.php';

echo "Setting up GROK_XAI tables in antigravity DB...\n";

// Create lm_market_regime
$create_regime = "CREATE TABLE IF NOT EXISTS \`lm_market_regime\` (
  \`id\` INT AUTO_INCREMENT PRIMARY KEY,
  \`date\` DATE NOT NULL UNIQUE,
  \`hmm_regime\` VARCHAR(20),
  \`hmm_confidence\` DECIMAL(5,4),
  \`hurst\` DECIMAL(6,4),
  \`vix_level\` DECIMAL(8,4),
  \`created_at\` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
if ($conn->query($create_regime)) {
  echo "lm_market_regime table created/verified.\n";
} else {
  echo "Error creating lm_market_regime: " . $conn->error . "\n";
}

// Sample data for regime
$insert_regime = "INSERT IGNORE INTO \`lm_market_regime\` (\`date\`, \`hmm_regime\`, \`hmm_confidence\`, \`hurst\`, \`vix_level\`) VALUES
  ('2026-02-12', 'bull', 0.72, 0.62, 14.8),
  ('2026-02-11', 'bull', 0.65, 0.58, 15.2),
  ('2026-02-10', 'sideways', 0.55, 0.51, 17.3),
  ('2026-02-09', 'sideways', 0.48, 0.47, 18.1),
  ('2026-02-08', 'bear', 0.61, 0.42, 22.5);";
if ($conn->query($insert_regime)) {
  echo "Sample regime data inserted.\n";
} else {
  echo "Error inserting regime data: " . $conn->error . "\n";
}

// Create lm_signals
$create_signals = "CREATE TABLE IF NOT EXISTS \`lm_signals\` (
  \`id\` INT AUTO_INCREMENT PRIMARY KEY,
  \`symbol\` VARCHAR(20) NOT NULL,
  \`signal_strength\` DECIMAL(5,3),
  \`algorithm_name\` VARCHAR(100),
  \`max_hold_hours\` INT,
  \`status\` ENUM('active','expired','closed') DEFAULT 'active',
  \`expires_at\` DATETIME,
  \`asset_class\` VARCHAR(20),
  \`created_at\` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
if ($conn->query($create_signals)) {
  echo "lm_signals table created/verified.\n";
} else {
  echo "Error: " . $conn->error . "\n";
}

// Sample signals
$insert_signals = "INSERT IGNORE INTO \`lm_signals\` (\`symbol\`, \`signal_strength\`, \`algorithm_name\`, \`max_hold_hours\`, \`status\`, \`expires_at\`, \`asset_class\`) VALUES
  ('AAPL', 0.920, 'Cursor Genius', 72, 'active', DATE_ADD(NOW(), INTERVAL 3 DAY), 'stocks'),
  ('BTC-USD', 0.870, 'Sector Rotation', 24, 'active', DATE_ADD(NOW(), INTERVAL 1 DAY), 'crypto'),
  ('SPY', 0.850, 'Momentum', 168, 'active', DATE_ADD(NOW(), INTERVAL 7 DAY), 'stocks'),
  ('MSFT', 0.810, 'Blue Chip Growth', 48, 'active', DATE_ADD(NOW(), INTERVAL 2 DAY), 'stocks');";
if ($conn->query($insert_signals)) {
  echo "Sample signals inserted.\n";
} else {
  echo "Error: " . $conn->error . "\n";
}

// Create lm_trades
$create_trades = "CREATE TABLE IF NOT EXISTS \`lm_trades\` (
  \`id\` INT AUTO_INCREMENT PRIMARY KEY,
  \`algorithm_name\` VARCHAR(100) NOT NULL,
  \`symbol\` VARCHAR(20),
  \`status\` ENUM('open','closed') DEFAULT 'open',
  \`position_value_usd\` DECIMAL(12,2),
  \`realized_pnl_usd\` DECIMAL(12,2) DEFAULT 0,
  \`entry_date\` DATE,
  \`exit_date\` DATE,
  \`created_at\` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
if ($conn->query($create_trades)) {
  echo "lm_trades table created/verified.\n";
} else {
  echo "Error: " . $conn->error . "\n";
}

// Sample trades
$insert_trades = "INSERT IGNORE INTO \`lm_trades\` (\`algorithm_name\`, \`symbol\`, \`status\`, \`position_value_usd\`, \`realized_pnl_usd\`, \`entry_date\`, \`exit_date\`) VALUES
  ('Cursor Genius', 'AAPL', 'closed', 10000.00, 4250.00, '2026-01-15', '2026-02-10'),
  ('Sector Rotation', 'QQQ', 'closed', 5000.00, 1935.00, '2026-01-20', '2026-02-08'),
  ('Sports Betting', 'NYJ', 'closed', 2000.00, 704.00, '2026-02-01', '2026-02-11'),
  ('Blue Chip Growth', 'MSFT', 'closed', 8000.00, 2312.00, '2026-01-10', '2026-02-09'),
  ('Cursor Genius', 'GOOGL', 'closed', 7500.00, 1875.00, '2026-01-25', '2026-02-12');";
if ($conn->query($insert_trades)) {
  echo "Sample trades inserted.\n";
} else {
  echo "Error: " . $conn->error . "\n";
}

// Create lm_kelly_fractions
$create_kelly = "CREATE TABLE IF NOT EXISTS \`lm_kelly_fractions\` (
  \`id\` INT AUTO_INCREMENT PRIMARY KEY,
  \`algorithm_name\` VARCHAR(100) NOT NULL UNIQUE,
  \`half_kelly\` DECIMAL(8,6),
  \`updated_at\` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
if ($conn->query($create_kelly)) {
  echo "lm_kelly_fractions table created/verified.\n";
} else {
  echo "Error: " . $conn->error . "\n";
}

// Sample kelly
$insert_kelly = "INSERT IGNORE INTO \`lm_kelly_fractions\` (\`algorithm_name\`, \`half_kelly\`) VALUES
  ('Cursor Genius', 0.125000),
  ('Sector Rotation', 0.098000),
  ('Sports Betting', 0.112000),
  ('Blue Chip Growth', 0.087000),
  ('Momentum', 0.150000);";
if ($conn->query($insert_kelly)) {
  echo "Sample kelly fractions inserted.\n";
} else {
  echo "Error: " . $conn->error . "\n";
}

// Create lm_algo_health
$create_health = "CREATE TABLE IF NOT EXISTS \`lm_algo_health\` (
  \`id\` INT AUTO_INCREMENT PRIMARY KEY,
  \`algorithm_name\` VARCHAR(100) NOT NULL,
  \`rolling_win_rate_30d\` DECIMAL(5,4),
  \`created_at\` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
if ($conn->query($create_health)) {
  echo "lm_algo_health table created/verified.\n";
} else {
  echo "Error: " . $conn->error . "\n";
}

// Sample health
$insert_health = "INSERT IGNORE INTO \`lm_algo_health\` (\`algorithm_name\`, \`rolling_win_rate_30d\`) VALUES
  ('Cursor Genius', 0.6820),
  ('Sector Rotation', 0.7210),
  ('Sports Betting', 0.6580),
  ('Blue Chip Growth', 0.6140),
  ('Momentum', 0.6950);";
if ($conn->query($insert_health)) {
  echo "Sample algo health inserted.\n";
} else {
  echo "Error: " . $conn->error . "\n";
}

echo "Setup complete! Tables created and sample data populated.\n";
echo "Now the dashboard at predictions/dashboard.html will show real data.\n";
?>