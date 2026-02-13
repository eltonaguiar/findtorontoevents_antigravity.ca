<?php
/**
 * Historical Data Manager
 * 
 * Manages OHLCV data for backtesting:
 * - Import from various sources (CSV, API, exchange exports)
 * - Validation and cleaning
 * - Storage optimization
 * - Gap detection and handling
 */

class HistoricalDataManager {
    private $dataDir;
    private $db;
    
    public function __construct($dataDir = __DIR__ . '/historical') {
        $this->dataDir = $dataDir;
        
        if (!is_dir($dataDir)) {
            mkdir($dataDir, 0755, true);
        }
        
        // Initialize database connection if available
        try {
            $this->db = Database::getInstance();
        } catch (Exception $e) {
            $this->db = null;
        }
    }
    
    /**
     * Import OHLCV data from CSV
     * Expected format: timestamp,open,high,low,close,volume
     */
    public function importFromCSV($coinId, $filePath, $timeframe = '1h') {
        if (!file_exists($filePath)) {
            throw new Exception("File not found: {$filePath}");
        }
        
        $data = [];
        $handle = fopen($filePath, 'r');
        
        // Skip header
        fgetcsv($handle);
        
        while (($row = fgetcsv($handle)) !== false) {
            $data[] = [
                'timestamp' => (int)$row[0],
                'open' => (float)$row[1],
                'high' => (float)$row[2],
                'low' => (float)$row[3],
                'close' => (float)$row[4],
                'volume' => (float)($row[5] ?? 0)
            ];
        }
        
        fclose($handle);
        
        // Sort by timestamp
        usort($data, function($a, $b) {
            return $a['timestamp'] <=> $b['timestamp'];
        });
        
        // Validate data
        $this->validateOHLCV($data);
        
        // Store
        $this->storeData($coinId, $data, $timeframe);
        
        return [
            'coin_id' => $coinId,
            'records_imported' => count($data),
            'timeframe' => $timeframe,
            'date_range' => [
                'start' => date('Y-m-d H:i:s', $data[0]['timestamp']),
                'end' => date('Y-m-d H:i:s', $data[count($data) - 1]['timestamp'])
            ]
        ];
    }
    
    /**
     * Import from Binance API format
     */
    public function importFromBinance($coinId, $apiResponse, $timeframe = '1h') {
        $data = [];
        
        // Binance kline format:
        // [timestamp, open, high, low, close, volume, ...]
        foreach ($apiResponse as $kline) {
            $data[] = [
                'timestamp' => (int)($kline[0] / 1000), // Binance uses ms
                'open' => (float)$kline[1],
                'high' => (float)$kline[2],
                'low' => (float)$kline[3],
                'close' => (float)$kline[4],
                'volume' => (float)$kline[5]
            ];
        }
        
        $this->validateOHLCV($data);
        $this->storeData($coinId, $data, $timeframe);
        
        return [
            'coin_id' => $coinId,
            'records_imported' => count($data),
            'timeframe' => $timeframe
        ];
    }
    
    /**
     * Validate OHLCV data integrity
     */
    private function validateOHLCV(&$data) {
        $errors = [];
        $cleaned = [];
        
        $prevTimestamp = 0;
        $expectedInterval = null;
        
        foreach ($data as $i => $candle) {
            // Check required fields
            if (!isset($candle['timestamp'], $candle['open'], $candle['high'], $candle['low'], $candle['close'])) {
                $errors[] = "Row {$i}: Missing required fields";
                continue;
            }
            
            // OHLC logic check
            if ($candle['high'] < $candle['low']) {
                $errors[] = "Row {$i}: High < Low (auto-corrected)";
                $temp = $candle['high'];
                $candle['high'] = $candle['low'];
                $candle['low'] = $temp;
            }
            
            if ($candle['high'] < max($candle['open'], $candle['close'])) {
                $errors[] = "Row {$i}: High < max(Open, Close) (auto-corrected)";
                $candle['high'] = max($candle['open'], $candle['close']);
            }
            
            if ($candle['low'] > min($candle['open'], $candle['close'])) {
                $errors[] = "Row {$i}: Low > min(Open, Close) (auto-corrected)";
                $candle['low'] = min($candle['open'], $candle['close']);
            }
            
            // Detect gaps
            if ($prevTimestamp > 0 && $expectedInterval) {
                $gap = $candle['timestamp'] - $prevTimestamp;
                if ($gap > $expectedInterval * 2) {
                    $errors[] = "Row {$i}: Gap detected (" . ($gap / $expectedInterval) . " intervals missing)";
                }
            } else if ($prevTimestamp > 0) {
                $expectedInterval = $candle['timestamp'] - $prevTimestamp;
            }
            
            $prevTimestamp = $candle['timestamp'];
            $cleaned[] = $candle;
        }
        
        $data = $cleaned;
        
        return [
            'valid' => empty($errors),
            'errors' => $errors,
            'records_cleaned' => count($cleaned)
        ];
    }
    
    /**
     * Store data to file
     */
    private function storeData($coinId, $data, $timeframe) {
        $fileName = "{$coinId}_{$timeframe}.json";
        $filePath = $this->dataDir . '/' . $fileName;
        
        // Check if file exists and merge
        if (file_exists($filePath)) {
            $existing = json_decode(file_get_contents($filePath), true);
            $data = $this->mergeData($existing, $data);
        }
        
        file_put_contents($filePath, json_encode($data));
        
        // Update metadata
        $this->updateMetadata($coinId, $timeframe, $data);
    }
    
    /**
     * Merge existing and new data (deduplicate)
     */
    private function mergeData($existing, $new) {
        $merged = [];
        $timestamps = [];
        
        foreach ($existing as $candle) {
            $ts = $candle['timestamp'];
            if (!isset($timestamps[$ts])) {
                $timestamps[$ts] = true;
                $merged[] = $candle;
            }
        }
        
        foreach ($new as $candle) {
            $ts = $candle['timestamp'];
            if (!isset($timestamps[$ts])) {
                $timestamps[$ts] = true;
                $merged[] = $candle;
            }
        }
        
        // Sort by timestamp
        usort($merged, function($a, $b) {
            return $a['timestamp'] <=> $b['timestamp'];
        });
        
        return $merged;
    }
    
    /**
     * Update metadata file
     */
    private function updateMetadata($coinId, $timeframe, $data) {
        $metaFile = $this->dataDir . '/metadata.json';
        
        $metadata = [];
        if (file_exists($metaFile)) {
            $metadata = json_decode(file_get_contents($metaFile), true);
        }
        
        $key = "{$coinId}_{$timeframe}";
        $metadata[$key] = [
            'coin_id' => $coinId,
            'timeframe' => $timeframe,
            'records' => count($data),
            'start_timestamp' => $data[0]['timestamp'],
            'end_timestamp' => $data[count($data) - 1]['timestamp'],
            'start_date' => date('Y-m-d H:i:s', $data[0]['timestamp']),
            'end_date' => date('Y-m-d H:i:s', $data[count($data) - 1]['timestamp']),
            'updated_at' => date('Y-m-d H:i:s')
        ];
        
        file_put_contents($metaFile, json_encode($metadata, JSON_PRETTY_PRINT));
    }
    
    /**
     * Load data for a specific coin and time range
     */
    public function loadData($coinId, $startTimestamp, $endTimestamp, $timeframe = '1h') {
        $fileName = "{$coinId}_{$timeframe}.json";
        $filePath = $this->dataDir . '/' . $fileName;
        
        if (!file_exists($filePath)) {
            return [];
        }
        
        $data = json_decode(file_get_contents($filePath), true);
        
        // Filter by timestamp range
        return array_filter($data, function($candle) use ($startTimestamp, $endTimestamp) {
            return $candle['timestamp'] >= $startTimestamp && $candle['timestamp'] <= $endTimestamp;
        });
    }
    
    /**
     * Get available data ranges
     */
    public function getDataRanges($coinId = null) {
        $metaFile = $this->dataDir . '/metadata.json';
        
        if (!file_exists($metaFile)) {
            return [];
        }
        
        $metadata = json_decode(file_get_contents($metaFile), true);
        
        if ($coinId) {
            return array_filter($metadata, function($m) use ($coinId) {
                return $m['coin_id'] == $coinId;
            });
        }
        
        return $metadata;
    }
    
    /**
     * Detect and report data gaps
     */
    public function detectGaps($coinId, $timeframe = '1h', $maxGapMinutes = null) {
        $data = $this->loadData(
            $coinId,
            0,
            PHP_INT_MAX,
            $timeframe
        );
        
        if (empty($data)) {
            return ['error' => 'No data available'];
        }
        
        // Determine expected interval
        $intervals = [];
        $prev = null;
        foreach ($data as $candle) {
            if ($prev) {
                $intervals[] = $candle['timestamp'] - $prev['timestamp'];
            }
            $prev = $candle;
        }
        
        sort($intervals);
        $expectedInterval = $intervals[floor(count($intervals) / 2)]; // Median
        
        $maxGap = $maxGapMinutes ? ($maxGapMinutes * 60) : ($expectedInterval * 2);
        
        $gaps = [];
        $prev = null;
        foreach ($data as $candle) {
            if ($prev) {
                $gap = $candle['timestamp'] - $prev['timestamp'];
                if ($gap > $maxGap) {
                    $gaps[] = [
                        'start' => date('Y-m-d H:i:s', $prev['timestamp'] + $expectedInterval),
                        'end' => date('Y-m-d H:i:s', $candle['timestamp']),
                        'duration_hours' => round($gap / 3600, 2),
                        'missing_candles' => floor($gap / $expectedInterval) - 1
                    ];
                }
            }
            $prev = $candle;
        }
        
        return [
            'coin_id' => $coinId,
            'timeframe' => $timeframe,
            'expected_interval_seconds' => $expectedInterval,
            'total_candles' => count($data),
            'gaps_found' => count($gaps),
            'gaps' => $gaps
        ];
    }
    
    /**
     * Export data to CSV
     */
    public function exportToCSV($coinId, $outputPath, $timeframe = '1h') {
        $data = $this->loadData($coinId, 0, PHP_INT_MAX, $timeframe);
        
        $handle = fopen($outputPath, 'w');
        fputcsv($handle, ['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume']);
        
        foreach ($data as $candle) {
            fputcsv($handle, [
                $candle['timestamp'],
                date('Y-m-d H:i:s', $candle['timestamp']),
                $candle['open'],
                $candle['high'],
                $candle['low'],
                $candle['close'],
                $candle['volume']
            ]);
        }
        
        fclose($handle);
        
        return [
            'records_exported' => count($data),
            'output_path' => $outputPath
        ];
    }
    
    /**
     * Resample data to different timeframe
     */
    public function resample($coinId, $sourceTimeframe, $targetTimeframe) {
        $sourceData = $this->loadData($coinId, 0, PHP_INT_MAX, $sourceTimeframe);
        
        if (empty($sourceData)) {
            throw new Exception("No source data found");
        }
        
        // Parse target timeframe
        preg_match('/(\d+)([hmd])/', $targetTimeframe, $matches);
        if (!$matches) {
            throw new Exception("Invalid target timeframe format");
        }
        
        $multiplier = (int)$matches[1];
        $unit = $matches[2];
        
        $secondsMap = ['m' => 60, 'h' => 3600, 'd' => 86400];
        $targetSeconds = $multiplier * $secondsMap[$unit];
        
        // Parse source timeframe
        preg_match('/(\d+)([hmd])/', $sourceTimeframe, $sourceMatches);
        $sourceSeconds = (int)$sourceMatches[1] * $secondsMap[$sourceMatches[2]];
        
        if ($targetSeconds < $sourceSeconds) {
            throw new Exception("Cannot upsample to smaller timeframe");
        }
        
        $ratio = $targetSeconds / $sourceSeconds;
        $resampled = [];
        $bucket = [];
        $bucketStart = null;
        
        foreach ($sourceData as $candle) {
            $candleBucket = floor($candle['timestamp'] / $targetSeconds) * $targetSeconds;
            
            if ($bucketStart !== $candleBucket) {
                if (!empty($bucket)) {
                    $resampled[] = $this->aggregateCandles($bucket, $bucketStart);
                }
                $bucket = [];
                $bucketStart = $candleBucket;
            }
            
            $bucket[] = $candle;
        }
        
        // Don't forget the last bucket
        if (!empty($bucket)) {
            $resampled[] = $this->aggregateCandles($bucket, $bucketStart);
        }
        
        $this->storeData($coinId, $resampled, $targetTimeframe);
        
        return [
            'source_records' => count($sourceData),
            'resampled_records' => count($resampled),
            'ratio' => $ratio
        ];
    }
    
    /**
     * Aggregate candles into single candle
     */
    private function aggregateCandles($candles, $timestamp) {
        $opens = array_column($candles, 'open');
        $highs = array_column($candles, 'high');
        $lows = array_column($candles, 'low');
        $closes = array_column($candles, 'close');
        $volumes = array_column($candles, 'volume');
        
        return [
            'timestamp' => $timestamp,
            'open' => $opens[0],
            'high' => max($highs),
            'low' => min($lows),
            'close' => $closes[count($closes) - 1],
            'volume' => array_sum($volumes)
        ];
    }
}

// CLI usage
if (php_sapi_name() === 'cli') {
    $options = getopt('a:c:f:t:', ['action:', 'coin:', 'file:', 'timeframe:']);
    
    $action = $options['a'] ?? $options['action'] ?? null;
    $coinId = $options['c'] ?? $options['coin'] ?? null;
    $file = $options['f'] ?? $options['file'] ?? null;
    $timeframe = $options['t'] ?? $options['timeframe'] ?? '1h';
    
    $manager = new HistoricalDataManager();
    
    switch ($action) {
        case 'import':
            if (!$file || !$coinId) {
                echo "Usage: php HistoricalDataManager.php -a import -c <coin_id> -f <csv_file>\n";
                exit(1);
            }
            $result = $manager->importFromCSV($coinId, $file, $timeframe);
            echo json_encode($result, JSON_PRETTY_PRINT) . "\n";
            break;
            
        case 'gaps':
            if (!$coinId) {
                echo "Usage: php HistoricalDataManager.php -a gaps -c <coin_id>\n";
                exit(1);
            }
            $result = $manager->detectGaps($coinId, $timeframe);
            echo json_encode($result, JSON_PRETTY_PRINT) . "\n";
            break;
            
        case 'ranges':
            $result = $manager->getDataRanges($coinId);
            echo json_encode($result, JSON_PRETTY_PRINT) . "\n";
            break;
            
        case 'export':
            if (!$coinId) {
                echo "Usage: php HistoricalDataManager.php -a export -c <coin_id> -f <output_file>\n";
                exit(1);
            }
            $output = $file ?? "{$coinId}_{$timeframe}_export.csv";
            $result = $manager->exportToCSV($coinId, $output, $timeframe);
            echo json_encode($result, JSON_PRETTY_PRINT) . "\n";
            break;
            
        default:
            echo "Available actions: import, gaps, ranges, export\n";
            exit(1);
    }
}
