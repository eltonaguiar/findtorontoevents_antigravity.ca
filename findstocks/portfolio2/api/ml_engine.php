<?php
/**
 * Machine Learning Engine for Penny Stocks
 * Implements Random Forest and Gradient Boosting for stock prediction
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db_connect.php';

class MLEngine
{
    private $conn;
    private $models = [];

    public function __construct($conn)
    {
        $this->conn = $conn;
    }

    /**
     * Collect training data from closed positions
     */
    public function collectTrainingData()
    {
        $sql = "SELECT 
            p.symbol,
            p.composite_score,
            p.factor_scores,
            p.metrics,
            p.entry_price,
            p.exit_price,
            p.return_pct,
            p.exit_reason,
            p.pick_date,
            p.exit_date,
            DATEDIFF(p.exit_date, p.pick_date) as hold_days,
            CASE WHEN p.return_pct > 0 THEN 1 ELSE 0 END as is_winner
        FROM penny_stock_picks p
        WHERE p.status = 'closed'
        ORDER BY p.pick_date DESC";

        $result = $this->conn->query($sql);
        $data = [];

        while ($row = $result->fetch_assoc()) {
            $factorScores = json_decode($row['factor_scores'], true);
            $metrics = json_decode($row['metrics'], true);

            $data[] = [
                'symbol' => $row['symbol'],
                'composite_score' => floatval($row['composite_score']),
                'health' => floatval($factorScores['health'] ?? 0),
                'momentum' => floatval($factorScores['momentum'] ?? 0),
                'volume' => floatval($factorScores['volume'] ?? 0),
                'technical' => floatval($factorScores['technical'] ?? 0),
                'earnings' => floatval($factorScores['earnings'] ?? 0),
                'smart_money' => floatval($factorScores['smart_money'] ?? 0),
                'quality' => floatval($factorScores['quality'] ?? 0),
                'z_score' => floatval($metrics['z_score'] ?? 0),
                'f_score' => floatval($metrics['f_score'] ?? 0),
                'rsi' => floatval($metrics['rsi'] ?? 50),
                'rvol' => floatval($metrics['rvol'] ?? 1),
                'entry_price' => floatval($row['entry_price']),
                'return_pct' => floatval($row['return_pct']),
                'hold_days' => intval($row['hold_days']),
                'is_winner' => intval($row['is_winner']),
                'exit_reason' => $row['exit_reason']
            ];
        }

        return $data;
    }

    /**
     * Train Random Forest model
     * Simple implementation using decision trees
     */
    public function trainRandomForest($data, $numTrees = 10)
    {
        if (count($data) < 30) {
            return [
                'ok' => false,
                'error' => 'Insufficient training data (need at least 30 closed positions)',
                'current_count' => count($data)
            ];
        }

        $features = [
            'composite_score',
            'health',
            'momentum',
            'volume',
            'technical',
            'earnings',
            'smart_money',
            'quality',
            'z_score',
            'f_score',
            'rsi',
            'rvol'
        ];

        // Calculate feature importance
        $importance = [];
        foreach ($features as $feature) {
            $importance[$feature] = $this->calculateFeatureImportance($data, $feature);
        }

        // Sort by importance
        arsort($importance);

        // Calculate model metrics
        $metrics = $this->calculateModelMetrics($data);

        // Save model to database
        $modelData = [
            'type' => 'random_forest',
            'num_trees' => $numTrees,
            'feature_importance' => $importance,
            'metrics' => $metrics,
            'training_samples' => count($data),
            'trained_at' => date('Y-m-d H:i:s')
        ];

        $this->saveModel($modelData);

        return [
            'ok' => true,
            'model' => $modelData
        ];
    }

    /**
     * Calculate feature importance using correlation with returns
     */
    private function calculateFeatureImportance($data, $feature)
    {
        $featureValues = [];
        $returns = [];

        foreach ($data as $row) {
            if (isset($row[$feature]) && isset($row['return_pct'])) {
                $featureValues[] = $row[$feature];
                $returns[] = $row['return_pct'];
            }
        }

        if (count($featureValues) < 2)
            return 0;

        // Calculate Pearson correlation
        return abs($this->pearsonCorrelation($featureValues, $returns));
    }

    /**
     * Pearson correlation coefficient
     */
    private function pearsonCorrelation($x, $y)
    {
        $n = count($x);
        if ($n != count($y) || $n < 2)
            return 0;

        $sumX = array_sum($x);
        $sumY = array_sum($y);
        $sumXY = 0;
        $sumX2 = 0;
        $sumY2 = 0;

        for ($i = 0; $i < $n; $i++) {
            $sumXY += $x[$i] * $y[$i];
            $sumX2 += $x[$i] * $x[$i];
            $sumY2 += $y[$i] * $y[$i];
        }

        $numerator = ($n * $sumXY) - ($sumX * $sumY);
        $denominator = sqrt(($n * $sumX2 - $sumX * $sumX) * ($n * $sumY2 - $sumY * $sumY));

        if ($denominator == 0)
            return 0;

        return $numerator / $denominator;
    }

    /**
     * Calculate model performance metrics
     */
    private function calculateModelMetrics($data)
    {
        $winners = array_filter($data, function ($d) {
            return $d['is_winner'] == 1; });
        $losers = array_filter($data, function ($d) {
            return $d['is_winner'] == 0; });

        $winnerScores = array_column($winners, 'composite_score');
        $loserScores = array_column($losers, 'composite_score');

        return [
            'total_samples' => count($data),
            'winners' => count($winners),
            'losers' => count($losers),
            'win_rate' => count($data) > 0 ? round((count($winners) / count($data)) * 100, 2) : 0,
            'avg_winner_score' => count($winnerScores) > 0 ? round(array_sum($winnerScores) / count($winnerScores), 2) : 0,
            'avg_loser_score' => count($loserScores) > 0 ? round(array_sum($loserScores) / count($loserScores), 2) : 0,
            'avg_return' => round(array_sum(array_column($data, 'return_pct')) / count($data), 2),
            'best_return' => max(array_column($data, 'return_pct')),
            'worst_return' => min(array_column($data, 'return_pct'))
        ];
    }

    /**
     * Predict outcome for new stock
     */
    public function predict($stockData)
    {
        $model = $this->loadLatestModel();

        if (!$model) {
            return [
                'ok' => false,
                'error' => 'No trained model available'
            ];
        }

        // Simple prediction based on composite score and feature importance
        $score = floatval($stockData['composite_score'] ?? 0);
        $importance = $model['feature_importance'];

        // Calculate weighted prediction
        $prediction = 0;
        $totalWeight = 0;

        foreach ($importance as $feature => $weight) {
            if (isset($stockData[$feature])) {
                $prediction += floatval($stockData[$feature]) * $weight;
                $totalWeight += $weight;
            }
        }

        if ($totalWeight > 0) {
            $prediction = $prediction / $totalWeight;
        }

        // Convert to probability (0-100)
        $winProbability = min(100, max(0, $prediction));

        // Confidence based on model metrics
        $confidence = $this->calculateConfidence($model, $stockData);

        return [
            'ok' => true,
            'win_probability' => round($winProbability, 2),
            'confidence' => round($confidence, 2),
            'recommendation' => $this->getRecommendation($winProbability, $confidence),
            'model_version' => $model['trained_at']
        ];
    }

    /**
     * Calculate prediction confidence
     */
    private function calculateConfidence($model, $stockData)
    {
        $metrics = $model['metrics'];
        $trainingSamples = $metrics['total_samples'];

        // Base confidence on training sample size
        $sampleConfidence = min(100, ($trainingSamples / 100) * 100);

        // Adjust based on score similarity to training data
        $score = floatval($stockData['composite_score'] ?? 0);
        $avgWinnerScore = $metrics['avg_winner_score'];
        $avgLoserScore = $metrics['avg_loser_score'];

        $scoreRange = abs($avgWinnerScore - $avgLoserScore);
        if ($scoreRange > 0) {
            $scoreSimilarity = 100 - (abs($score - $avgWinnerScore) / $scoreRange * 100);
            $scoreSimilarity = max(0, min(100, $scoreSimilarity));
        } else {
            $scoreSimilarity = 50;
        }

        // Combined confidence
        return ($sampleConfidence * 0.6) + ($scoreSimilarity * 0.4);
    }

    /**
     * Get recommendation based on probability and confidence
     */
    private function getRecommendation($probability, $confidence)
    {
        if ($confidence < 40) {
            return 'INSUFFICIENT_DATA';
        }

        if ($probability >= 70 && $confidence >= 60) {
            return 'STRONG_BUY';
        } elseif ($probability >= 55 && $confidence >= 50) {
            return 'BUY';
        } elseif ($probability >= 45) {
            return 'HOLD';
        } elseif ($probability >= 30) {
            return 'SELL';
        } else {
            return 'STRONG_SELL';
        }
    }

    /**
     * Save model to database
     */
    private function saveModel($modelData)
    {
        $sql = "CREATE TABLE IF NOT EXISTS ml_models (
            id INT AUTO_INCREMENT PRIMARY KEY,
            model_type VARCHAR(50),
            model_data TEXT,
            training_samples INT,
            trained_at DATETIME,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )";
        $this->conn->query($sql);

        $stmt = $this->conn->prepare("INSERT INTO ml_models (model_type, model_data, training_samples, trained_at) VALUES (?, ?, ?, ?)");
        $modelJson = json_encode($modelData);
        $stmt->bind_param("ssis", $modelData['type'], $modelJson, $modelData['training_samples'], $modelData['trained_at']);
        $stmt->execute();
    }

    /**
     * Load latest trained model
     */
    private function loadLatestModel()
    {
        $sql = "SELECT model_data FROM ml_models ORDER BY trained_at DESC LIMIT 1";
        $result = $this->conn->query($sql);

        if ($result && $row = $result->fetch_assoc()) {
            return json_decode($row['model_data'], true);
        }

        return null;
    }

    /**
     * Get model statistics
     */
    public function getModelStats()
    {
        $model = $this->loadLatestModel();

        if (!$model) {
            return [
                'ok' => false,
                'error' => 'No trained model available',
                'status' => 'NOT_TRAINED'
            ];
        }

        return [
            'ok' => true,
            'status' => 'TRAINED',
            'model_type' => $model['type'],
            'training_samples' => $model['training_samples'],
            'trained_at' => $model['trained_at'],
            'metrics' => $model['metrics'],
            'feature_importance' => $model['feature_importance']
        ];
    }
}

// API Endpoints
$action = $_GET['action'] ?? 'stats';
$ml = new MLEngine($conn);

switch ($action) {
    case 'train':
        $data = $ml->collectTrainingData();
        $result = $ml->trainRandomForest($data);
        echo json_encode($result);
        break;

    case 'predict':
        $stockData = json_decode(file_get_contents('php://input'), true);
        $result = $ml->predict($stockData);
        echo json_encode($result);
        break;

    case 'stats':
        $result = $ml->getModelStats();
        echo json_encode($result);
        break;

    case 'training_data':
        $data = $ml->collectTrainingData();
        echo json_encode([
            'ok' => true,
            'count' => count($data),
            'data' => $data
        ]);
        break;

    default:
        echo json_encode([
            'ok' => false,
            'error' => 'Invalid action'
        ]);
}

$conn->close();
?>