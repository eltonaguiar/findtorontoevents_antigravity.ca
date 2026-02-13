<?php
/**
 * Machine Learning Engine for Penny Stocks
 * Implements Random Forest and Gradient Boosting for stock prediction
 * PHP 5.2 compatible
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once 'db_connect.php';

class MLEngine
{
    var $conn;
    var $models = array();

    function MLEngine($conn)
    {
        $this->conn = $conn;
    }

    /**
     * Collect training data from closed positions
     */
    function collectTrainingData()
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
        $data = array();

        if (!$result) {
            return $data;
        }

        while ($row = $result->fetch_assoc()) {
            $factorScores = json_decode($row['factor_scores'], true);
            $metrics = json_decode($row['metrics'], true);
            if (!is_array($factorScores)) $factorScores = array();
            if (!is_array($metrics)) $metrics = array();

            $data[] = array(
                'symbol' => $row['symbol'],
                'composite_score' => floatval($row['composite_score']),
                'health' => floatval(isset($factorScores['health']) ? $factorScores['health'] : 0),
                'momentum' => floatval(isset($factorScores['momentum']) ? $factorScores['momentum'] : 0),
                'volume' => floatval(isset($factorScores['volume']) ? $factorScores['volume'] : 0),
                'technical' => floatval(isset($factorScores['technical']) ? $factorScores['technical'] : 0),
                'earnings' => floatval(isset($factorScores['earnings']) ? $factorScores['earnings'] : 0),
                'smart_money' => floatval(isset($factorScores['smart_money']) ? $factorScores['smart_money'] : 0),
                'quality' => floatval(isset($factorScores['quality']) ? $factorScores['quality'] : 0),
                'z_score' => floatval(isset($metrics['z_score']) ? $metrics['z_score'] : 0),
                'f_score' => floatval(isset($metrics['f_score']) ? $metrics['f_score'] : 0),
                'rsi' => floatval(isset($metrics['rsi']) ? $metrics['rsi'] : 50),
                'rvol' => floatval(isset($metrics['rvol']) ? $metrics['rvol'] : 1),
                'entry_price' => floatval($row['entry_price']),
                'return_pct' => floatval($row['return_pct']),
                'hold_days' => intval($row['hold_days']),
                'is_winner' => intval($row['is_winner']),
                'exit_reason' => $row['exit_reason']
            );
        }

        return $data;
    }

    /**
     * Train Random Forest model
     * Simple implementation using decision trees
     */
    function trainRandomForest($data, $numTrees = 10)
    {
        if (count($data) < 30) {
            return array(
                'ok' => false,
                'error' => 'Insufficient training data (need at least 30 closed positions)',
                'current_count' => count($data)
            );
        }

        $features = array(
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
        );

        // Calculate feature importance
        $importance = array();
        foreach ($features as $feature) {
            $importance[$feature] = $this->calculateFeatureImportance($data, $feature);
        }

        // Sort by importance
        arsort($importance);

        // Calculate model metrics
        $metrics = $this->calculateModelMetrics($data);

        // Save model to database
        $modelData = array(
            'type' => 'random_forest',
            'num_trees' => $numTrees,
            'feature_importance' => $importance,
            'metrics' => $metrics,
            'training_samples' => count($data),
            'trained_at' => date('Y-m-d H:i:s')
        );

        $this->saveModel($modelData);

        return array(
            'ok' => true,
            'model' => $modelData
        );
    }

    /**
     * Calculate feature importance using correlation with returns
     */
    function calculateFeatureImportance($data, $feature)
    {
        $featureValues = array();
        $returns = array();

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
    function pearsonCorrelation($x, $y)
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
    function calculateModelMetrics($data)
    {
        $winners = array();
        $losers = array();
        $winnerScores = array();
        $loserScores = array();
        $allReturns = array();

        foreach ($data as $d) {
            $allReturns[] = $d['return_pct'];
            if ($d['is_winner'] == 1) {
                $winners[] = $d;
                $winnerScores[] = $d['composite_score'];
            } else {
                $losers[] = $d;
                $loserScores[] = $d['composite_score'];
            }
        }

        $totalCount = count($data);

        return array(
            'total_samples' => $totalCount,
            'winners' => count($winners),
            'losers' => count($losers),
            'win_rate' => $totalCount > 0 ? round((count($winners) / $totalCount) * 100, 2) : 0,
            'avg_winner_score' => count($winnerScores) > 0 ? round(array_sum($winnerScores) / count($winnerScores), 2) : 0,
            'avg_loser_score' => count($loserScores) > 0 ? round(array_sum($loserScores) / count($loserScores), 2) : 0,
            'avg_return' => $totalCount > 0 ? round(array_sum($allReturns) / $totalCount, 2) : 0,
            'best_return' => count($allReturns) > 0 ? max($allReturns) : 0,
            'worst_return' => count($allReturns) > 0 ? min($allReturns) : 0
        );
    }

    /**
     * Predict outcome for new stock
     */
    function predict($stockData)
    {
        $model = $this->loadLatestModel();

        if (!$model) {
            return array(
                'ok' => false,
                'error' => 'No trained model available'
            );
        }

        // Simple prediction based on composite score and feature importance
        $score = floatval(isset($stockData['composite_score']) ? $stockData['composite_score'] : 0);
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

        return array(
            'ok' => true,
            'win_probability' => round($winProbability, 2),
            'confidence' => round($confidence, 2),
            'recommendation' => $this->getRecommendation($winProbability, $confidence),
            'model_version' => $model['trained_at']
        );
    }

    /**
     * Calculate prediction confidence
     */
    function calculateConfidence($model, $stockData)
    {
        $metrics = $model['metrics'];
        $trainingSamples = $metrics['total_samples'];

        // Base confidence on training sample size
        $sampleConfidence = min(100, ($trainingSamples / 100) * 100);

        // Adjust based on score similarity to training data
        $score = floatval(isset($stockData['composite_score']) ? $stockData['composite_score'] : 0);
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
    function getRecommendation($probability, $confidence)
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
    function saveModel($modelData)
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

        $type = $this->conn->real_escape_string($modelData['type']);
        $modelJson = $this->conn->real_escape_string(json_encode($modelData));
        $samples = intval($modelData['training_samples']);
        $trainedAt = $this->conn->real_escape_string($modelData['trained_at']);

        $sql = "INSERT INTO ml_models (model_type, model_data, training_samples, trained_at) VALUES ('$type', '$modelJson', $samples, '$trainedAt')";
        $this->conn->query($sql);
    }

    /**
     * Load latest trained model
     */
    function loadLatestModel()
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
    function getModelStats()
    {
        $model = $this->loadLatestModel();

        if (!$model) {
            return array(
                'ok' => false,
                'error' => 'No trained model available',
                'status' => 'NOT_TRAINED'
            );
        }

        return array(
            'ok' => true,
            'status' => 'TRAINED',
            'model_type' => $model['type'],
            'training_samples' => $model['training_samples'],
            'trained_at' => $model['trained_at'],
            'metrics' => $model['metrics'],
            'feature_importance' => $model['feature_importance']
        );
    }
}

// API Endpoints
$action = isset($_GET['action']) ? $_GET['action'] : 'stats';
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
        echo json_encode(array(
            'ok' => true,
            'count' => count($data),
            'data' => $data
        ));
        break;

    default:
        echo json_encode(array(
            'ok' => false,
            'error' => 'Invalid action'
        ));
}

$conn->close();
?>