<?php
/**
 * Meme Coin Prediction Backtesting Framework
 * 
 * Validates trading strategies on historical data with walk-forward analysis.
 * Focus on correctness over speed - prevents lookahead bias at all costs.
 */

require_once __DIR__ . '/../../shared/config/database.php';

class BacktestEngine {
    private $db;
    private $config;
    private $tradeLog = [];
    private $equityCurve = [];
    private $currentEquity = 10000; // Starting capital
    private $metrics = [];
    private $signals = [];
    private $ohlcvCache = [];
    
    // Transaction costs configuration
    private $tradingFeePercent = 0.001; // 0.1% per trade (maker/taker)
    private $slippageModel = 'volume_based'; // 'fixed' or 'volume_based'
    private $spreadPercent = 0.002; // 0.2% spread
    
    public function __construct($config = []) {
        $this->config = array_merge([
            'initial_capital' => 10000,
            'position_size_pct' => 0.1, // 10% of capital per trade
            'max_concurrent_positions' => 5,
            'risk_per_trade_pct' => 0.02, // 2% max loss per trade
        ], $config);
        
        $this->currentEquity = $this->config['initial_capital'];
        $this->db = Database::getInstance();
    }
    
    /**
     * Main backtest runner
     * 
     * @param string $startDate Backtest start date (Y-m-d)
     * @param string $endDate Backtest end date (Y-m-d)
     * @param array $strategy Strategy configuration
     * @param array $filters Optional filters (tiers, coins, etc.)
     * @return array Backtest results
     */
    public function runBacktest($startDate, $endDate, $strategy, $filters = []) {
        $this->validateInputs($startDate, $endDate, $strategy);
        
        $backtestId = $this->generateBacktestId($startDate, $endDate, $strategy);
        
        // Clear previous run data
        $this->tradeLog = [];
        $this->equityCurve = [];
        $this->currentEquity = $this->config['initial_capital'];
        $this->signals = [];
        
        // Load historical signals for the period
        $this->signals = $this->loadHistoricalSignals($startDate, $endDate, $filters);
        
        if (empty($this->signals)) {
            return $this->createEmptyResult($startDate, $endDate, $backtestId);
        }
        
        // Sort signals by timestamp (critical for chronological processing)
        usort($this->signals, function($a, $b) {
            return $a['timestamp'] <=> $b['timestamp'];
        });
        
        // Process each signal
        foreach ($this->signals as $signal) {
            $this->processSignal($signal, $strategy);
        }
        
        // Calculate all metrics
        $this->metrics = $this->calculateMetrics($this->tradeLog);
        
        // Store backtest results
        $this->storeBacktestResults($backtestId, $startDate, $endDate, $strategy);
        
        return $this->buildReport($backtestId, $startDate, $endDate);
    }
    
    /**
     * Walk-forward analysis
     * 
     * @param string $startDate Overall start date
     * @param string $endDate Overall end date
     * @param int $trainWindowDays Training window in days
     * @param int $testWindowDays Testing window in days
     * @param array $strategy Strategy configuration
     * @return array Walk-forward results
     */
    public function runWalkForward($startDate, $endDate, $trainWindowDays, $testWindowDays, $strategy) {
        $results = [];
        $currentStart = new DateTime($startDate);
        $overallEnd = new DateTime($endDate);
        
        $fold = 1;
        while (true) {
            // Calculate train period
            $trainStart = clone $currentStart;
            $trainEnd = clone $currentStart;
            $trainEnd->modify("+{$trainWindowDays} days");
            
            // Calculate test period
            $testStart = clone $trainEnd;
            $testEnd = clone $trainEnd;
            $testEnd->modify("+{$testWindowDays} days");
            
            // Stop if test period exceeds overall end
            if ($testStart >= $overallEnd) {
                break;
            }
            
            // Adjust test end if it exceeds overall end
            if ($testEnd > $overallEnd) {
                $testEnd = clone $overallEnd;
            }
            
            // Run backtest for this fold
            $foldResult = $this->runBacktest(
                $testStart->format('Y-m-d'),
                $testEnd->format('Y-m-d'),
                $strategy
            );
            
            $foldResult['fold'] = $fold;
            $foldResult['train_period'] = [
                'start' => $trainStart->format('Y-m-d'),
                'end' => $trainEnd->format('Y-m-d')
            ];
            
            $results[] = $foldResult;
            
            // Move window forward
            $currentStart->modify("+{$testWindowDays} days");
            $fold++;
            
            // Safety limit
            if ($fold > 100) break;
        }
        
        // Aggregate walk-forward results
        return $this->aggregateWalkForwardResults($results);
    }
    
    /**
     * Load historical signals from database
     */
    private function loadHistoricalSignals($startDate, $endDate, $filters) {
        $query = "
            SELECT 
                s.id,
                s.coin_id,
                c.symbol,
                c.name,
                s.timestamp,
                s.signal_type,
                s.tier,
                s.entry_price,
                s.tp1,
                s.tp2,
                s.tp3,
                s.stop_loss,
                s.confidence,
                s.features,
                m.regime as market_regime
            FROM ml_signals s
            JOIN coins c ON s.coin_id = c.id
            LEFT JOIN market_regimes m ON s.regime_id = m.id
            WHERE DATE(FROM_UNIXTIME(s.timestamp)) BETWEEN :start AND :end
        ";
        
        $params = [':start' => $startDate, ':end' => $endDate];
        
        // Apply tier filter
        if (!empty($filters['tiers'])) {
            $tiers = implode(',', array_map(function($t) { return "'" . addslashes($t) . "'"; }, $filters['tiers']));
            $query .= " AND s.tier IN ($tiers)";
        }
        
        // Apply coin filter
        if (!empty($filters['coins'])) {
            $coins = implode(',', array_map(function($c) { return "'" . addslashes($c) . "'"; }, $filters['coins']));
            $query .= " AND c.symbol IN ($coins)";
        }
        
        $query .= " ORDER BY s.timestamp ASC";
        
        $stmt = $this->db->prepare($query);
        foreach ($params as $key => $value) {
            $stmt->bindValue($key, $value);
        }
        $stmt->execute();
        
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
    
    /**
     * Load OHLCV data for a coin
     * Uses caching to avoid repeated database queries
     */
    private function loadOHLCV($coinId, $startTimestamp, $endTimestamp) {
        $cacheKey = "{$coinId}_{$startTimestamp}_{$endTimestamp}";
        
        if (isset($this->ohlcvCache[$cacheKey])) {
            return $this->ohlcvCache[$cacheKey];
        }
        
        // Check if file-based historical data exists
        $filePath = __DIR__ . "/data/historical/{$coinId}.json";
        if (file_exists($filePath)) {
            $data = json_decode(file_get_contents($filePath), true);
            $filtered = array_filter($data, function($candle) use ($startTimestamp, $endTimestamp) {
                return $candle['timestamp'] >= $startTimestamp && $candle['timestamp'] <= $endTimestamp;
            });
            $this->ohlcvCache[$cacheKey] = array_values($filtered);
            return $this->ohlcvCache[$cacheKey];
        }
        
        // Fallback to database
        $query = "
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv_data
            WHERE coin_id = :coin_id
            AND timestamp BETWEEN :start AND :end
            ORDER BY timestamp ASC
        ";
        
        $stmt = $this->db->prepare($query);
        $stmt->bindValue(':coin_id', $coinId, PDO::PARAM_INT);
        $stmt->bindValue(':start', $startTimestamp, PDO::PARAM_INT);
        $stmt->bindValue(':end', $endTimestamp, PDO::PARAM_INT);
        $stmt->execute();
        
        $this->ohlcvCache[$cacheKey] = $stmt->fetchAll(PDO::FETCH_ASSOC);
        return $this->ohlcvCache[$cacheKey];
    }
    
    /**
     * Process a single signal - check if TP or SL was hit
     */
    private function processSignal($signal, $strategy) {
        $entryTime = $signal['timestamp'];
        $entryPrice = (float)$signal['entry_price'];
        $tp1 = (float)$signal['tp1'];
        $tp2 = (float)$signal['tp2'];
        $tp3 = (float)$signal['tp3'];
        $stopLoss = (float)$signal['stop_loss'];
        
        // Load subsequent price data (lookahead prevention: only data AFTER signal)
        $lookaheadWindow = $strategy['max_hold_days'] ?? 30;
        $endTimestamp = $entryTime + ($lookaheadWindow * 86400);
        
        $ohlcv = $this->loadOHLCV($signal['coin_id'], $entryTime + 1, $endTimestamp);
        
        if (empty($ohlcv)) {
            return; // No price data available
        }
        
        // Determine position size
        $positionSize = $this->calculatePositionSize($signal);
        
        // Simulate the trade
        $trade = $this->simulateTrade($signal, $ohlcv, $positionSize, $strategy);
        
        if ($trade) {
            $this->tradeLog[] = $trade;
            $this->updateEquityCurve($trade);
        }
    }
    
    /**
     * Simulate a single trade
     * 
     * @param array $signal Signal data
     * @param array $ohlcv OHLCV data after signal
     * @param float $positionSize Position size in base currency
     * @param array $strategy Strategy configuration
     * @return array|null Trade result
     */
    public function simulateTrade($signal, $ohlcv, $positionSize, $strategy) {
        $entryPrice = (float)$signal['entry_price'];
        $tp1 = (float)$signal['tp1'];
        $tp2 = (float)$signal['tp2'];
        $tp3 = (float)$signal['tp3'];
        $stopLoss = (float)$signal['stop_loss'];
        
        $entryTime = $signal['timestamp'];
        $position = $positionSize / $entryPrice; // Amount of coin bought
        
        // Apply entry slippage and fees
        $entrySlippage = $this->calculateSlippage($ohlcv[0], 'entry');
        $entryPriceWithCosts = $entryPrice * (1 + $entrySlippage + $this->tradingFeePercent);
        $entryCost = $position * $entryPriceWithCosts;
        
        $trade = [
            'signal_id' => $signal['id'],
            'coin_symbol' => $signal['symbol'],
            'coin_name' => $signal['name'],
            'signal_type' => $signal['signal_type'],
            'tier' => $signal['tier'],
            'market_regime' => $signal['market_regime'] ?? 'unknown',
            'entry_time' => $entryTime,
            'entry_price' => $entryPriceWithCosts,
            'position_size' => $positionSize,
            'tp1' => $tp1,
            'tp2' => $tp2,
            'tp3' => $tp3,
            'stop_loss' => $stopLoss,
            'exit_time' => null,
            'exit_price' => null,
            'exit_reason' => null,
            'pnl_percent' => null,
            'pnl_absolute' => null,
            'holding_period_hours' => null,
            'tp_level_hit' => null
        ];
        
        // Track partial exits
        $remainingPosition = $position;
        $realizedPnL = 0;
        $avgExitPrice = 0;
        $exitOccurred = false;
        $tpLevelHit = null;
        
        // Partial exit configuration
        $tp1ExitPct = $strategy['tp1_exit_pct'] ?? 0.33; // 33% at TP1
        $tp2ExitPct = $strategy['tp2_exit_pct'] ?? 0.33; // 33% at TP2
        $tp3ExitPct = $strategy['tp3_exit_pct'] ?? 0.34; // 34% at TP3
        
        foreach ($ohlcv as $candle) {
            $high = (float)$candle['high'];
            $low = (float)$candle['low'];
            $close = (float)$candle['close'];
            $candleTime = $candle['timestamp'];
            
            // Check TP3 hit (highest priority)
            if ($remainingPosition > 0 && $high >= $tp3) {
                $exitSlippage = $this->calculateSlippage($candle, 'exit');
                $exitPrice = $tp3 * (1 - $exitSlippage - $this->tradingFeePercent);
                $exitQty = $position * $tp3ExitPct;
                
                $realizedPnL += $exitQty * ($exitPrice - $entryPriceWithCosts);
                $avgExitPrice = $avgExitPrice > 0 
                    ? ($avgExitPrice * ($position - $remainingPosition) + $exitPrice * $exitQty) / ($position - $remainingPosition + $exitQty)
                    : $exitPrice;
                
                $remainingPosition -= $exitQty;
                if (!$exitOccurred) {
                    $trade['exit_time'] = $candleTime;
                    $tpLevelHit = 3;
                }
                $exitOccurred = true;
            }
            
            // Check TP2 hit
            if ($remainingPosition > 0 && $high >= $tp2) {
                $exitSlippage = $this->calculateSlippage($candle, 'exit');
                $exitPrice = $tp2 * (1 - $exitSlippage - $this->tradingFeePercent);
                $exitQty = $position * $tp2ExitPct;
                
                $realizedPnL += $exitQty * ($exitPrice - $entryPriceWithCosts);
                $avgExitPrice = $avgExitPrice > 0 
                    ? ($avgExitPrice * ($position - $remainingPosition) + $exitPrice * $exitQty) / ($position - $remainingPosition + $exitQty)
                    : $exitPrice;
                
                $remainingPosition -= $exitQty;
                if (!$exitOccurred) {
                    $trade['exit_time'] = $candleTime;
                    $tpLevelHit = 2;
                }
                $exitOccurred = true;
            }
            
            // Check TP1 hit
            if ($remainingPosition > 0 && $high >= $tp1) {
                $exitSlippage = $this->calculateSlippage($candle, 'exit');
                $exitPrice = $tp1 * (1 - $exitSlippage - $this->tradingFeePercent);
                $exitQty = $position * $tp1ExitPct;
                
                $realizedPnL += $exitQty * ($exitPrice - $entryPriceWithCosts);
                $avgExitPrice = $avgExitPrice > 0 
                    ? ($avgExitPrice * ($position - $remainingPosition) + $exitPrice * $exitQty) / ($position - $remainingPosition + $exitQty)
                    : $exitPrice;
                
                $remainingPosition -= $exitQty;
                if (!$exitOccurred) {
                    $trade['exit_time'] = $candleTime;
                    $tpLevelHit = 1;
                }
                $exitOccurred = true;
            }
            
            // Check Stop Loss hit
            if ($low <= $stopLoss) {
                $exitSlippage = $this->calculateSlippage($candle, 'exit_sl');
                $exitPrice = $stopLoss * (1 + $exitSlippage + $this->tradingFeePercent);
                
                // Exit entire remaining position at SL
                $realizedPnL += $remainingPosition * ($exitPrice - $entryPriceWithCosts);
                
                $trade['exit_time'] = $candleTime;
                $trade['exit_price'] = $exitPrice;
                $trade['exit_reason'] = 'stop_loss';
                $trade['tp_level_hit'] = $tpLevelHit;
                $trade['pnl_absolute'] = $realizedPnL;
                $trade['pnl_percent'] = ($realizedPnL / $positionSize) * 100;
                $trade['holding_period_hours'] = ($candleTime - $entryTime) / 3600;
                
                return $trade;
            }
            
            // Check for time-based exit (if configured)
            $maxHoldHours = $strategy['max_hold_hours'] ?? 168; // Default 7 days
            if (($candleTime - $entryTime) / 3600 >= $maxHoldHours && !$exitOccurred) {
                $exitSlippage = $this->calculateSlippage($candle, 'exit');
                $exitPrice = $close * (1 - $exitSlippage - $this->tradingFeePercent);
                
                $realizedPnL = $position * ($exitPrice - $entryPriceWithCosts);
                
                $trade['exit_time'] = $candleTime;
                $trade['exit_price'] = $exitPrice;
                $trade['exit_reason'] = 'time_exit';
                $trade['tp_level_hit'] = null;
                $trade['pnl_absolute'] = $realizedPnL;
                $trade['pnl_percent'] = ($realizedPnL / $positionSize) * 100;
                $trade['holding_period_hours'] = ($candleTime - $entryTime) / 3600;
                
                return $trade;
            }
        }
        
        // If we reached the end of data without exit, mark as unresolved
        if (!$exitOccurred) {
            return null; // Signal hasn't resolved yet
        }
        
        // If we partially exited but haven't closed fully, close at last price
        if ($remainingPosition > 0) {
            $lastCandle = end($ohlcv);
            $exitSlippage = $this->calculateSlippage($lastCandle, 'exit');
            $exitPrice = $lastCandle['close'] * (1 - $exitSlippage - $this->tradingFeePercent);
            
            $realizedPnL += $remainingPosition * ($exitPrice - $entryPriceWithCosts);
        }
        
        $trade['exit_price'] = $avgExitPrice;
        $trade['exit_reason'] = 'take_profit';
        $trade['tp_level_hit'] = $tpLevelHit;
        $trade['pnl_absolute'] = $realizedPnL;
        $trade['pnl_percent'] = ($realizedPnL / $positionSize) * 100;
        $trade['holding_period_hours'] = ($trade['exit_time'] - $entryTime) / 3600;
        
        return $trade;
    }
    
    /**
     * Calculate position size based on risk management
     */
    private function calculatePositionSize($signal) {
        $riskPerTrade = $this->currentEquity * $this->config['risk_per_trade_pct'];
        $positionRisk = abs($signal['entry_price'] - $signal['stop_loss']) / $signal['entry_price'];
        
        if ($positionRisk == 0) {
            $positionRisk = 0.05; // Default 5% risk if SL not set
        }
        
        $positionSize = min(
            ($riskPerTrade / $positionRisk) * ($signal['entry_price'] / $signal['entry_price']),
            $this->currentEquity * $this->config['position_size_pct']
        );
        
        return $positionSize;
    }
    
    /**
     * Calculate slippage based on volume
     */
    private function calculateSlippage($candle, $type) {
        if ($this->slippageModel === 'fixed') {
            return 0.001; // Fixed 0.1% slippage
        }
        
        // Volume-based slippage model
        $volume = (float)($candle['volume'] ?? 0);
        $baseSlippage = 0.0005; // Base 0.05%
        
        if ($volume < 100000) {
            $baseSlippage = 0.002; // 0.2% for low volume
        } elseif ($volume < 1000000) {
            $baseSlippage = 0.001; // 0.1% for medium volume
        } else {
            $baseSlippage = 0.0005; // 0.05% for high volume
        }
        
        // Additional slippage for stop loss exits
        if ($type === 'exit_sl') {
            $baseSlippage *= 1.5;
        }
        
        return $baseSlippage;
    }
    
    /**
     * Update equity curve after each trade
     */
    private function updateEquityCurve($trade) {
        $this->currentEquity += $trade['pnl_absolute'];
        
        $this->equityCurve[] = [
            'timestamp' => $trade['exit_time'],
            'equity' => $this->currentEquity,
            'trade_pnl' => $trade['pnl_absolute'],
            'trade_pnl_pct' => $trade['pnl_percent']
        ];
    }
    
    /**
     * Calculate all backtest metrics
     * 
     * @param array $trades Array of completed trades
     * @return array Calculated metrics
     */
    public function calculateMetrics($trades) {
        if (empty($trades)) {
            return $this->getEmptyMetrics();
        }
        
        $winningTrades = array_filter($trades, function($t) { return $t['pnl_absolute'] > 0; });
        $losingTrades = array_filter($trades, function($t) { return $t['pnl_absolute'] <= 0; });
        
        $winCount = count($winningTrades);
        $lossCount = count($losingTrades);
        $totalTrades = count($trades);
        
        $winRate = $winCount / $totalTrades;
        
        $avgWin = $winCount > 0 ? array_sum(array_column($winningTrades, 'pnl_percent')) / $winCount : 0;
        $avgLoss = $lossCount > 0 ? array_sum(array_column($losingTrades, 'pnl_percent')) / $lossCount : 0;
        
        // Expectancy: (Win% × Avg Win) - (Loss% × |Avg Loss|)
        $lossRate = 1 - $winRate;
        $expectancy = ($winRate * $avgWin) - ($lossRate * abs($avgLoss));
        
        // Profit factor
        $grossProfit = array_sum(array_column($winningTrades, 'pnl_absolute'));
        $grossLoss = abs(array_sum(array_column($losingTrades, 'pnl_absolute')));
        $profitFactor = $grossLoss > 0 ? $grossProfit / $grossLoss : ($grossProfit > 0 ? INF : 0);
        
        // Average trade duration
        $avgDuration = array_sum(array_column($trades, 'holding_period_hours')) / $totalTrades;
        
        // Sharpe ratio calculation
        $sharpeRatio = $this->calculateSharpeRatio();
        
        // Max drawdown
        $maxDrawdown = $this->calculateMaxDrawdown();
        
        // Consecutive wins/losses
        $consecutiveStats = $this->calculateConsecutiveStats($trades);
        
        // Tier-based metrics
        $tierMetrics = $this->calculateTierMetrics($trades);
        
        // Market regime metrics
        $regimeMetrics = $this->calculateRegimeMetrics($trades);
        
        // Monthly performance
        $monthlyPerformance = $this->calculateMonthlyPerformance($trades);
        
        // Statistical validity
        $statisticalValidity = $this->calculateStatisticalValidity($winRate, $totalTrades);
        
        return [
            'total_trades' => $totalTrades,
            'winning_trades' => $winCount,
            'losing_trades' => $lossCount,
            'win_rate' => round($winRate, 4),
            'expectancy' => round($expectancy, 4),
            'sharpe_ratio' => round($sharpeRatio, 4),
            'max_drawdown' => round($maxDrawdown, 4),
            'profit_factor' => round($profitFactor, 4),
            'avg_trade_duration_hours' => round($avgDuration, 2),
            'avg_win_percent' => round($avgWin, 4),
            'avg_loss_percent' => round($avgLoss, 4),
            'max_consecutive_wins' => $consecutiveStats['max_wins'],
            'max_consecutive_losses' => $consecutiveStats['max_losses'],
            'by_tier' => $tierMetrics,
            'by_market_regime' => $regimeMetrics,
            'monthly_performance' => $monthlyPerformance,
            'statistical_validity' => $statisticalValidity,
            'total_return' => round(($this->currentEquity - $this->config['initial_capital']) / $this->config['initial_capital'], 4),
            'final_equity' => round($this->currentEquity, 2)
        ];
    }
    
    /**
     * Calculate Sharpe ratio
     */
    private function calculateSharpeRatio() {
        if (count($this->equityCurve) < 2) {
            return 0;
        }
        
        $returns = [];
        $prevEquity = $this->config['initial_capital'];
        
        foreach ($this->equityCurve as $point) {
            $ret = ($point['equity'] - $prevEquity) / $prevEquity;
            $returns[] = $ret;
            $prevEquity = $point['equity'];
        }
        
        $avgReturn = array_sum($returns) / count($returns);
        $variance = 0;
        foreach ($returns as $ret) {
            $variance += pow($ret - $avgReturn, 2);
        }
        $stdDev = sqrt($variance / count($returns));
        
        // Annualized Sharpe (assuming daily returns, 252 trading days)
        if ($stdDev == 0) {
            return 0;
        }
        
        return ($avgReturn * 252) / ($stdDev * sqrt(252));
    }
    
    /**
     * Calculate maximum drawdown
     */
    private function calculateMaxDrawdown() {
        if (empty($this->equityCurve)) {
            return 0;
        }
        
        $peak = $this->config['initial_capital'];
        $maxDD = 0;
        
        foreach ($this->equityCurve as $point) {
            if ($point['equity'] > $peak) {
                $peak = $point['equity'];
            }
            
            $drawdown = ($peak - $point['equity']) / $peak;
            if ($drawdown > $maxDD) {
                $maxDD = $drawdown;
            }
        }
        
        return -$maxDD; // Return as negative value
    }
    
    /**
     * Calculate consecutive wins/losses
     */
    private function calculateConsecutiveStats($trades) {
        $maxWins = 0;
        $maxLosses = 0;
        $currentWins = 0;
        $currentLosses = 0;
        
        foreach ($trades as $trade) {
            if ($trade['pnl_absolute'] > 0) {
                $currentWins++;
                $currentLosses = 0;
                if ($currentWins > $maxWins) {
                    $maxWins = $currentWins;
                }
            } else {
                $currentLosses++;
                $currentWins = 0;
                if ($currentLosses > $maxLosses) {
                    $maxLosses = $currentLosses;
                }
            }
        }
        
        return ['max_wins' => $maxWins, 'max_losses' => $maxLosses];
    }
    
    /**
     * Calculate metrics by tier
     */
    private function calculateTierMetrics($trades) {
        $tiers = ['lean_buy', 'moderate_buy', 'strong_buy'];
        $metrics = [];
        
        foreach ($tiers as $tier) {
            $tierTrades = array_filter($trades, function($t) use ($tier) {
                return $t['tier'] === $tier;
            });
            
            if (empty($tierTrades)) {
                $metrics[$tier] = ['signals' => 0, 'win_rate' => 0, 'avg_return' => 0];
                continue;
            }
            
            $wins = array_filter($tierTrades, function($t) { return $t['pnl_absolute'] > 0; });
            $winRate = count($wins) / count($tierTrades);
            $avgReturn = array_sum(array_column($tierTrades, 'pnl_percent')) / count($tierTrades);
            
            $metrics[$tier] = [
                'signals' => count($tierTrades),
                'win_rate' => round($winRate, 4),
                'avg_return' => round($avgReturn, 4)
            ];
        }
        
        return $metrics;
    }
    
    /**
     * Calculate metrics by market regime
     */
    private function calculateRegimeMetrics($trades) {
        $regimes = ['bull', 'bear', 'sideways'];
        $metrics = [];
        
        foreach ($regimes as $regime) {
            $regimeTrades = array_filter($trades, function($t) use ($regime) {
                return ($t['market_regime'] ?? 'unknown') === $regime;
            });
            
            if (empty($regimeTrades)) {
                $metrics[$regime] = ['signals' => 0, 'win_rate' => 0, 'avg_return' => 0];
                continue;
            }
            
            $wins = array_filter($regimeTrades, function($t) { return $t['pnl_absolute'] > 0; });
            $winRate = count($wins) / count($regimeTrades);
            $avgReturn = array_sum(array_column($regimeTrades, 'pnl_percent')) / count($regimeTrades);
            
            $metrics[$regime] = [
                'signals' => count($regimeTrades),
                'win_rate' => round($winRate, 4),
                'avg_return' => round($avgReturn, 4)
            ];
        }
        
        return $metrics;
    }
    
    /**
     * Calculate monthly performance breakdown
     */
    private function calculateMonthlyPerformance($trades) {
        $monthly = [];
        
        foreach ($trades as $trade) {
            $monthKey = date('Y-m', $trade['entry_time']);
            
            if (!isset($monthly[$monthKey])) {
                $monthly[$monthKey] = [
                    'month' => $monthKey,
                    'trades' => 0,
                    'wins' => 0,
                    'losses' => 0,
                    'total_return_pct' => 0,
                    'win_rate' => 0
                ];
            }
            
            $monthly[$monthKey]['trades']++;
            if ($trade['pnl_absolute'] > 0) {
                $monthly[$monthKey]['wins']++;
            } else {
                $monthly[$monthKey]['losses']++;
            }
            $monthly[$monthKey]['total_return_pct'] += $trade['pnl_percent'];
        }
        
        // Calculate win rates
        foreach ($monthly as &$month) {
            $month['win_rate'] = round($month['wins'] / $month['trades'], 4);
            $month['total_return_pct'] = round($month['total_return_pct'], 4);
        }
        
        // Sort by month
        ksort($monthly);
        
        return array_values($monthly);
    }
    
    /**
     * Calculate statistical validity metrics
     */
    private function calculateStatisticalValidity($winRate, $totalTrades) {
        // Minimum sample size for 95% CI with 5% margin of error
        $minSampleSize = 350;
        
        // Wilson score interval for win rate
        $z = 1.96; // 95% confidence
        $n = $totalTrades;
        $p = $winRate;
        
        $wilsonLower = ($p + ($z * $z) / (2 * $n) - $z * sqrt(($p * (1 - $p) + ($z * $z) / (4 * $n)) / $n)) / (1 + ($z * $z) / $n);
        $wilsonUpper = ($p + ($z * $z) / (2 * $n) + $z * sqrt(($p * (1 - $p) + ($z * $z) / (4 * $n)) / $n)) / (1 + ($z * $z) / $n);
        
        return [
            'sample_size_sufficient' => $totalTrades >= $minSampleSize,
            'min_recommended_signals' => $minSampleSize,
            'win_rate_95ci_lower' => round(max(0, $wilsonLower), 4),
            'win_rate_95ci_upper' => round(min(1, $wilsonUpper), 4),
            'confidence_level' => 0.95,
            'note' => $totalTrades < $minSampleSize 
                ? 'Sample size too small for reliable inference' 
                : 'Sample size sufficient for statistical validity'
        ];
    }
    
    /**
     * Build final report
     */
    private function buildReport($backtestId, $startDate, $endDate) {
        $totalSignals = count($this->signals);
        $resolvedSignals = count($this->tradeLog);
        
        return [
            'backtest_id' => $backtestId,
            'backtest_period' => [
                'start' => $startDate,
                'end' => $endDate
            ],
            'total_signals' => $totalSignals,
            'resolved_signals' => $resolvedSignals,
            'unresolved_signals' => $totalSignals - $resolvedSignals,
            'overall_metrics' => [
                'win_rate' => $this->metrics['win_rate'],
                'expectancy' => $this->metrics['expectancy'],
                'sharpe_ratio' => $this->metrics['sharpe_ratio'],
                'max_drawdown' => $this->metrics['max_drawdown'],
                'profit_factor' => $this->metrics['profit_factor'],
                'avg_trade_duration_hours' => $this->metrics['avg_trade_duration_hours'],
                'total_return' => $this->metrics['total_return'],
                'final_equity' => $this->metrics['final_equity']
            ],
            'by_tier' => $this->metrics['by_tier'],
            'by_market_regime' => $this->metrics['by_market_regime'],
            'monthly_performance' => $this->metrics['monthly_performance'],
            'statistical_validity' => $this->metrics['statistical_validity'],
            'equity_curve' => $this->equityCurve,
            'trade_log' => $this->tradeLog,
            'config' => $this->config
        ];
    }
    
    /**
     * Store backtest results in database
     */
    private function storeBacktestResults($backtestId, $startDate, $endDate, $strategy) {
        $data = [
            'backtest_id' => $backtestId,
            'start_date' => $startDate,
            'end_date' => $endDate,
            'strategy_config' => json_encode($strategy),
            'metrics' => json_encode($this->metrics),
            'trade_count' => count($this->tradeLog),
            'created_at' => date('Y-m-d H:i:s')
        ];
        
        // Check if table exists, if not create it
        $this->ensureBacktestTableExists();
        
        $sql = "INSERT INTO ml_backtests 
                (backtest_id, start_date, end_date, strategy_config, metrics, trade_count, created_at)
                VALUES 
                (:backtest_id, :start_date, :end_date, :strategy_config, :metrics, :trade_count, :created_at)
                ON DUPLICATE KEY UPDATE
                strategy_config = VALUES(strategy_config),
                metrics = VALUES(metrics),
                trade_count = VALUES(trade_count),
                created_at = VALUES(created_at)";
        
        $stmt = $this->db->prepare($sql);
        foreach ($data as $key => $value) {
            $stmt->bindValue(':' . $key, $value);
        }
        $stmt->execute();
        
        // Store trade log
        $this->storeTradeLog($backtestId);
    }
    
    /**
     * Store individual trades
     */
    private function storeTradeLog($backtestId) {
        $this->ensureTradeLogTableExists();
        
        $sql = "INSERT INTO ml_backtest_trades 
                (backtest_id, signal_id, coin_symbol, entry_time, exit_time, entry_price, exit_price, 
                 pnl_percent, pnl_absolute, exit_reason, tp_level_hit, holding_hours)
                VALUES 
                (:backtest_id, :signal_id, :coin_symbol, :entry_time, :exit_time, :entry_price, :exit_price,
                 :pnl_percent, :pnl_absolute, :exit_reason, :tp_level_hit, :holding_hours)";
        
        $stmt = $this->db->prepare($sql);
        
        foreach ($this->tradeLog as $trade) {
            $stmt->bindValue(':backtest_id', $backtestId);
            $stmt->bindValue(':signal_id', $trade['signal_id']);
            $stmt->bindValue(':coin_symbol', $trade['coin_symbol']);
            $stmt->bindValue(':entry_time', $trade['entry_time']);
            $stmt->bindValue(':exit_time', $trade['exit_time']);
            $stmt->bindValue(':entry_price', $trade['entry_price']);
            $stmt->bindValue(':exit_price', $trade['exit_price']);
            $stmt->bindValue(':pnl_percent', $trade['pnl_percent']);
            $stmt->bindValue(':pnl_absolute', $trade['pnl_absolute']);
            $stmt->bindValue(':exit_reason', $trade['exit_reason']);
            $stmt->bindValue(':tp_level_hit', $trade['tp_level_hit']);
            $stmt->bindValue(':holding_hours', $trade['holding_period_hours']);
            $stmt->execute();
        }
    }
    
    /**
     * Ensure database tables exist
     */
    private function ensureBacktestTableExists() {
        $sql = "CREATE TABLE IF NOT EXISTS ml_backtests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            backtest_id VARCHAR(64) UNIQUE NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            strategy_config JSON,
            metrics JSON,
            trade_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_backtest_id (backtest_id),
            INDEX idx_dates (start_date, end_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";
        
        $this->db->exec($sql);
    }
    
    private function ensureTradeLogTableExists() {
        $sql = "CREATE TABLE IF NOT EXISTS ml_backtest_trades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            backtest_id VARCHAR(64) NOT NULL,
            signal_id INT NOT NULL,
            coin_symbol VARCHAR(20) NOT NULL,
            entry_time INT NOT NULL,
            exit_time INT NOT NULL,
            entry_price DECIMAL(18, 8) NOT NULL,
            exit_price DECIMAL(18, 8) NOT NULL,
            pnl_percent DECIMAL(10, 4) NOT NULL,
            pnl_absolute DECIMAL(18, 8) NOT NULL,
            exit_reason VARCHAR(20) NOT NULL,
            tp_level_hit INT DEFAULT NULL,
            holding_hours DECIMAL(10, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_backtest_id (backtest_id),
            INDEX idx_exit_reason (exit_reason)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";
        
        $this->db->exec($sql);
    }
    
    /**
     * Generate unique backtest ID
     */
    private function generateBacktestId($startDate, $endDate, $strategy) {
        return hash('sha256', $startDate . $endDate . json_encode($strategy) . time());
    }
    
    /**
     * Validate input parameters
     */
    private function validateInputs($startDate, $endDate, $strategy) {
        if (!strtotime($startDate) || !strtotime($endDate)) {
            throw new InvalidArgumentException('Invalid date format. Use YYYY-MM-DD');
        }
        
        if (strtotime($startDate) >= strtotime($endDate)) {
            throw new InvalidArgumentException('Start date must be before end date');
        }
        
        if (empty($strategy) || !is_array($strategy)) {
            throw new InvalidArgumentException('Strategy configuration required');
        }
    }
    
    /**
     * Create empty result for no data
     */
    private function createEmptyResult($startDate, $endDate, $backtestId) {
        return [
            'backtest_id' => $backtestId,
            'backtest_period' => ['start' => $startDate, 'end' => $endDate],
            'total_signals' => 0,
            'resolved_signals' => 0,
            'overall_metrics' => $this->getEmptyMetrics(),
            'by_tier' => [],
            'by_market_regime' => [],
            'monthly_performance' => [],
            'equity_curve' => [],
            'trade_log' => [],
            'warning' => 'No signals found for the specified period'
        ];
    }
    
    /**
     * Get empty metrics structure
     */
    private function getEmptyMetrics() {
        return [
            'win_rate' => 0,
            'expectancy' => 0,
            'sharpe_ratio' => 0,
            'max_drawdown' => 0,
            'profit_factor' => 0,
            'avg_trade_duration_hours' => 0,
            'total_return' => 0,
            'final_equity' => $this->config['initial_capital']
        ];
    }
    
    /**
     * Aggregate walk-forward results
     */
    private function aggregateWalkForwardResults($results) {
        if (empty($results)) {
            return ['error' => 'No walk-forward results generated'];
        }
        
        $totalTrades = array_sum(array_column($results, 'resolved_signals'));
        $avgWinRate = array_sum(array_column(array_column($results, 'overall_metrics'), 'win_rate')) / count($results);
        $avgSharpe = array_sum(array_column(array_column($results, 'overall_metrics'), 'sharpe_ratio')) / count($results);
        $avgMaxDD = array_sum(array_column(array_column($results, 'overall_metrics'), 'max_drawdown')) / count($results);
        
        return [
            'walk_forward_summary' => [
                'folds' => count($results),
                'total_trades' => $totalTrades,
                'avg_win_rate' => round($avgWinRate, 4),
                'avg_sharpe_ratio' => round($avgSharpe, 4),
                'avg_max_drawdown' => round($avgMaxDD, 4),
            ],
            'fold_results' => $results
        ];
    }
    
    // Getters for external access
    public function getTradeLog() { return $this->tradeLog; }
    public function getEquityCurve() { return $this->equityCurve; }
    public function getMetrics() { return $this->metrics; }
}

// API Endpoint Handling
if (php_sapi_name() !== 'cli' && isset($_GET['action'])) {
    header('Content-Type: application/json');
    
    $engine = new BacktestEngine();
    $action = $_GET['action'];
    
    try {
        switch ($action) {
            case 'run':
                $start = $_GET['start'] ?? date('Y-m-d', strtotime('-1 year'));
                $end = $_GET['end'] ?? date('Y-m-d');
                $strategy = json_decode($_GET['strategy'] ?? '{}', true);
                
                echo json_encode($engine->runBacktest($start, $end, $strategy));
                break;
                
            case 'walkforward':
                $start = $_GET['start'] ?? date('Y-m-d', strtotime('-2 years'));
                $end = $_GET['end'] ?? date('Y-m-d');
                $trainDays = intval($_GET['train_days'] ?? 180);
                $testDays = intval($_GET['test_days'] ?? 60);
                $strategy = json_decode($_GET['strategy'] ?? '{}', true);
                
                echo json_encode($engine->runWalkForward($start, $end, $trainDays, $testDays, $strategy));
                break;
                
            case 'compare':
                $strategies = explode(',', $_GET['strategies'] ?? 'rule_based');
                $start = $_GET['start'] ?? date('Y-m-d', strtotime('-1 year'));
                $end = $_GET['end'] ?? date('Y-m-d');
                
                $comparison = [];
                foreach ($strategies as $stratName) {
                    $strategy = loadStrategyConfig($stratName);
                    $comparison[$stratName] = $engine->runBacktest($start, $end, $strategy);
                }
                
                echo json_encode([
                    'comparison' => $comparison,
                    'best_strategy' => array_reduce(array_keys($comparison), function($best, $key) use ($comparison) {
                        $metric = $comparison[$key]['overall_metrics']['sharpe_ratio'] ?? 0;
                        $bestMetric = $comparison[$best]['overall_metrics']['sharpe_ratio'] ?? 0;
                        return $metric > $bestMetric ? $key : $best;
                    }, array_key_first($comparison))
                ]);
                break;
                
            case 'metrics':
                $backtestId = $_GET['backtest_id'] ?? '';
                if (empty($backtestId)) {
                    http_response_code(400);
                    echo json_encode(['error' => 'backtest_id required']);
                    exit;
                }
                
                $db = Database::getInstance();
                $stmt = $db->prepare("SELECT * FROM ml_backtests WHERE backtest_id = :id");
                $stmt->bindValue(':id', $backtestId);
                $stmt->execute();
                $result = $stmt->fetch(PDO::FETCH_ASSOC);
                
                if (!$result) {
                    http_response_code(404);
                    echo json_encode(['error' => 'Backtest not found']);
                } else {
                    echo json_encode([
                        'backtest_id' => $result['backtest_id'],
                        'period' => ['start' => $result['start_date'], 'end' => $result['end_date']],
                        'metrics' => json_decode($result['metrics'], true),
                        'trade_count' => $result['trade_count'],
                        'created_at' => $result['created_at']
                    ]);
                }
                break;
                
            case 'equity_curve':
                $backtestId = $_GET['backtest_id'] ?? '';
                if (empty($backtestId)) {
                    http_response_code(400);
                    echo json_encode(['error' => 'backtest_id required']);
                    exit;
                }
                
                $db = Database::getInstance();
                $stmt = $db->prepare("
                    SELECT entry_time, exit_time, pnl_absolute, pnl_percent 
                    FROM ml_backtest_trades 
                    WHERE backtest_id = :id 
                    ORDER BY exit_time ASC
                ");
                $stmt->bindValue(':id', $backtestId);
                $stmt->execute();
                $trades = $stmt->fetchAll(PDO::FETCH_ASSOC);
                
                // Reconstruct equity curve
                $equity = 10000;
                $curve = [['timestamp' => 0, 'equity' => $equity]];
                foreach ($trades as $trade) {
                    $equity += $trade['pnl_absolute'];
                    $curve[] = [
                        'timestamp' => $trade['exit_time'],
                        'equity' => round($equity, 2),
                        'trade_pnl' => $trade['pnl_absolute'],
                        'trade_pnl_pct' => $trade['pnl_percent']
                    ];
                }
                
                echo json_encode(['equity_curve' => $curve]);
                break;
                
            case 'trade_log':
                $backtestId = $_GET['backtest_id'] ?? '';
                $limit = intval($_GET['limit'] ?? 100);
                $offset = intval($_GET['offset'] ?? 0);
                
                if (empty($backtestId)) {
                    http_response_code(400);
                    echo json_encode(['error' => 'backtest_id required']);
                    exit;
                }
                
                $db = Database::getInstance();
                $stmt = $db->prepare("
                    SELECT * FROM ml_backtest_trades 
                    WHERE backtest_id = :id 
                    ORDER BY exit_time DESC
                    LIMIT :limit OFFSET :offset
                ");
                $stmt->bindValue(':id', $backtestId);
                $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
                $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
                $stmt->execute();
                
                echo json_encode(['trades' => $stmt->fetchAll(PDO::FETCH_ASSOC)]);
                break;
                
            default:
                http_response_code(400);
                echo json_encode(['error' => 'Unknown action: ' . $action]);
        }
    } catch (Exception $e) {
        http_response_code(500);
        echo json_encode(['error' => $e->getMessage()]);
    }
}

/**
 * Load predefined strategy configuration
 */
function loadStrategyConfig($name) {
    $strategies = [
        'rule_based' => [
            'tp1_exit_pct' => 0.33,
            'tp2_exit_pct' => 0.33,
            'tp3_exit_pct' => 0.34,
            'max_hold_hours' => 168
        ],
        'conservative' => [
            'tp1_exit_pct' => 0.5,
            'tp2_exit_pct' => 0.3,
            'tp3_exit_pct' => 0.2,
            'max_hold_hours' => 72
        ],
        'aggressive' => [
            'tp1_exit_pct' => 0.25,
            'tp2_exit_pct' => 0.25,
            'tp3_exit_pct' => 0.5,
            'max_hold_hours' => 336
        ]
    ];
    
    return $strategies[$name] ?? $strategies['rule_based'];
}
