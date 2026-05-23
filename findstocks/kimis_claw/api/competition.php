<?php
/**
 * Kimi's Claw - REAL Database Data
 * No demo data - only real picks from stock_picks table
 */

error_reporting(0);
ini_set('display_errors', 0);
ob_start();

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-cache, no-store, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('Expires: Thu, 01 Jan 1970 00:00:00 GMT');
header('Vary: *');

// Database credentials from db_config.php
$db_host = 'mysql.50webs.com';
$db_user = 'ejaguiar1_stocks';
$db_pass = 'stocks';
$db_name = 'ejaguiar1_stocks';

// Connect
$conn = @new mysqli($db_host, $db_user, $db_pass, $db_name);

if ($conn->connect_error) {
    ob_end_clean();
    echo json_encode(array(
        'ok' => false,
        'error' => 'Database connection failed: ' . $conn->connect_error,
        'message' => 'Cannot connect to stocks database.'
    ));
    exit;
}

$conn->set_charset('utf8');

$action = isset($_GET['action']) ? $_GET['action'] : 'dashboard';

// Get market status in EST
$est = new DateTime('now', new DateTimeZone('America/New_York'));
$hour = (int)$est->format('H');
$day = (int)$est->format('w');
$isMarketOpen = ($hour >= 9 && $hour < 16 && $day > 0 && $day < 6);

// Function to check if date is a valid trading day (not weekend)
function isTradingDay($dateStr) {
    $date = new DateTime($dateStr, new DateTimeZone('America/New_York'));
    $dayOfWeek = (int)$date->format('w');
    return ($dayOfWeek > 0 && $dayOfWeek < 6); // Mon-Fri only
}

if ($action === 'dashboard') {
    $algorithms = array();
    
    // Get last 30 days of picks
    $thirtyDaysAgo = date('Y-m-d', strtotime('-30 days'));
    
    $algoRes = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE pick_date >= '$thirtyDaysAgo' AND entry_price > 0 ORDER BY algorithm_name LIMIT 20");
    
    if ($algoRes && $algoRes->num_rows > 0) {
        $id = 1;
        while ($algoRow = $algoRes->fetch_assoc()) {
            $algoName = $algoRow['algorithm_name'];
            
            // Get picks for this algorithm
            $picksRes = $conn->query("SELECT ticker, pick_date, entry_price, score, rating, risk_level FROM stock_picks WHERE algorithm_name = '$algoName' AND pick_date >= '$thirtyDaysAgo' AND entry_price > 0 ORDER BY pick_date DESC, id DESC LIMIT 10");
            
            $picks = array();
            $wins = 0;
            $losses = 0;
            $totalReturn = 0;
            $latestPickDate = null;
            
            if ($picksRes) {
                while ($pick = $picksRes->fetch_assoc()) {
                    $pickDate = $pick['pick_date'];
                    
                    // Skip picks on weekends/non-trading days
                    if (!isTradingDay($pickDate)) {
                        continue;
                    }
                    
                    if (!$latestPickDate) $latestPickDate = $pickDate;
                    
                    $ticker = $pick['ticker'];
                    $entryPrice = (float)$pick['entry_price'];
                    
                    // Get latest price from daily_prices
                    $priceRes = $conn->query("SELECT close_price, trade_date FROM daily_prices WHERE ticker = '$ticker' ORDER BY trade_date DESC LIMIT 1");
                    $currentPrice = $entryPrice;
                    $priceDate = $pickDate;
                    
                    if ($priceRes && $priceRes->num_rows > 0) {
                        $priceRow = $priceRes->fetch_assoc();
                        $currentPrice = (float)$priceRow['close_price'];
                        $priceDate = $priceRow['trade_date'];
                    }
                    
                    $returnPct = $entryPrice > 0 ? round((($currentPrice - $entryPrice) / $entryPrice) * 100, 2) : 0;
                    
                    if ($returnPct > 0) $wins++;
                    else $losses++;
                    $totalReturn += $returnPct;
                    
                    $daysHeld = (strtotime(date('Y-m-d')) - strtotime($pickDate)) / 86400;
                    
                    $picks[] = array(
                        'ticker' => $ticker,
                        'entryPrice' => $entryPrice,
                        'currentPrice' => round($currentPrice, 2),
                        'return' => $returnPct,
                        'pickDate' => $pickDate,
                        'priceDate' => $priceDate,
                        'daysHeld' => round($daysHeld),
                        'score' => (int)$pick['score'],
                        'rating' => $pick['rating'],
                        'riskLevel' => $pick['risk_level']
                    );
                }
            }
            
            $pickCount = count($picks);
            $winRate = $pickCount > 0 ? round(($wins / $pickCount) * 100) : 0;
            $avgReturn = $pickCount > 0 ? round($totalReturn / $pickCount, 2) : 0;
            
            // Calculate portfolio value
            $startingValue = 10000;
            $currentValue = $startingValue;
            foreach ($picks as $p) {
                $currentValue *= (1 + ($p['return'] / 100) * 0.1);
            }
            $currentValue = round($currentValue, 2);
            $totalReturnPct = round((($currentValue - $startingValue) / $startingValue) * 100, 2);
            
            $algorithms[] = array(
                'id' => $id++,
                'name' => $algoName,
                'type' => detectType($algoName),
                'status' => $latestPickDate === date('Y-m-d') ? 'ACTIVE' : 'IDLE',
                'lastPickDate' => $latestPickDate,
                'startingValue' => $startingValue,
                'currentValue' => $currentValue,
                'totalReturn' => $totalReturnPct,
                'wins' => $wins,
                'losses' => $losses,
                'winRate' => $winRate,
                'avgReturn' => $avgReturn,
                'pickCount' => $pickCount,
                'picks' => $picks
            );
        }
    }
    
    // Sort by total return
    usort($algorithms, 'sortByTotalReturn');
    
    $today = date('Y-m-d');
    $todayRes = $conn->query("SELECT COUNT(*) as cnt FROM stock_picks WHERE pick_date = '$today'");
    $todayRow = $todayRes ? $todayRes->fetch_assoc() : null;
    $todayPicks = $todayRow ? (int)$todayRow['cnt'] : 0;
    
    ob_end_clean();
    echo json_encode(array(
        'ok' => true,
        'live' => true,
        'timestamp' => $est->format('Y-m-d H:i:s') . ' EST',
        'marketStatus' => array(
            'isOpen' => $isMarketOpen,
            'status' => $isMarketOpen ? 'OPEN' : 'CLOSED',
            'message' => $isMarketOpen ? 'Market OPEN (9:30 AM - 4:00 PM ET)' : 'Market CLOSED',
            'timezone' => 'EST'
        ),
        'dataInfo' => array(
            'algorithms' => count($algorithms),
            'picksToday' => $todayPicks,
            'source' => 'stock_picks table (REAL)',
            'disclaimer' => 'All prices are actual entry prices from database. Current prices from daily_prices table.'
        ),
        'algorithms' => $algorithms
    ));
} elseif ($action === 'status') {
    ob_end_clean();
    echo json_encode(array(
        'ok' => true,
        'live' => true,
        'timestamp' => $est->format('Y-m-d H:i:s T'),
        'marketStatus' => array(
            'isOpen' => $isMarketOpen,
            'status' => $isMarketOpen ? 'OPEN' : 'CLOSED',
            'message' => $isMarketOpen ? 'Market OPEN' : 'Market CLOSED'
        )
    ));
} else {
    ob_end_clean();
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();

function detectType($name) {
    $name = strtolower($name);
    if (strpos($name, 'momentum') !== false) return 'Momentum';
    if (strpos($name, 'sector') !== false) return 'Sector';
    if (strpos($name, 'value') !== false) return 'Value';
    if (strpos($name, 'trend') !== false) return 'Trend';
    if (strpos($name, 'blue') !== false) return 'Blue Chip';
    if (strpos($name, 'etf') !== false) return 'ETF';
    if (strpos($name, 'composite') !== false) return 'Composite';
    return 'Strategy';
}

function sortByTotalReturn($a, $b) {
    if ($b['totalReturn'] == $a['totalReturn']) return 0;
    return ($b['totalReturn'] > $a['totalReturn']) ? 1 : -1;
}
