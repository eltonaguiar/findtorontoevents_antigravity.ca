<?php
/**
 * Curious Ichimoku Cloud Strategy
 * 
 * Multi-timeframe trend alignment strategy:
 * 1. 1D Chart: Ichimoku Cloud identifies primary trend
 * 2. 4H/1H Chart: Ichimoku confirms trend alignment
 * 3. 15m/5m Chart: Entry edge using Stochastics + Bollinger Bands + confluence
 * 
 * @author Curious Trader Strategy
 * @version 1.0.0
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Database configuration
require_once '../../findstocks/portfolio2/api/db_config.php';

class CuriousIchimokuStrategy {
    private $db;
    private $minScore = 70; // Minimum score for Strong Buy
    
    // Indicator weights for final score
    private $weights = array(
        'daily_ichi_trend' => 25,      // Daily Ichimoku trend alignment
        'hourly_ichi_confirm' => 20,   // 4H/1H confirmation
        'bollinger_position' => 15,    // Price between 1std and 2std
        'stoch_setup' => 15,           // Stochastics (30,10,10) setup
        'sr_confluence' => 10,         // Support/Resistance confluence
        'relative_strength' => 10,     // vs BTC/SPY
        'candlestick_pattern' => 5     // Pinbar/trendline break
    );
    
    public function __construct($db) {
        $this->db = $db;
    }
    
    /**
     * Main scan function
     */
    public function scan($symbol = null, $assetClass = 'crypto') {
        $results = array();
        $symbols = $symbol ? array($symbol) : $this->getSymbols($assetClass);
        
        foreach ($symbols as $sym) {
            $analysis = $this->analyzeSymbol($sym, $assetClass);
            if ($analysis && $analysis['total_score'] >= 60) {
                $results[] = $analysis;
            }
        }
        
        // Sort by score descending
        usort($results, function($a, $b) {
            return $b['total_score'] - $a['total_score'];
        });
        
        return $results;
    }
    
    /**
     * Analyze single symbol across all timeframes
     */
    private function analyzeSymbol($symbol, $assetClass) {
        // Fetch OHLCV data for multiple timeframes
        $daily = $this->fetchOHLCV($symbol, '1d', 60);
        $hourly4 = $this->fetchOHLCV($symbol, '4h', 60);
        $hourly1 = $this->fetchOHLCV($symbol, '1h', 60);
        $min15 = $this->fetchOHLCV($symbol, '15m', 100);
        $min5 = $this->fetchOHLCV($symbol, '5m', 100);
        
        if (!$daily || !$hourly4 || !$min15) {
            return null;
        }
        
        // Calculate Ichimoku Cloud for each timeframe
        $dailyIchi = $this->calculateIchimoku($daily);
        $hourly4Ichi = $this->calculateIchimoku($hourly4);
        $hourly1Ichi = $this->calculateIchimoku($hourly1);
        
        // Calculate entry indicators on 15m/5m
        $bollinger = $this->calculateBollinger($min15, 20, 2);
        $stoch = $this->calculateStochastics($min15, 30, 10, 10);
        $candlePattern = $this->detectCandlestickPatterns($min15);
        $relativeStrength = $this->calculateRelativeStrength($symbol, $assetClass);
        
        // Score each component
        $scores = array();
        $signals = array();
        
        // 1. Daily Ichimoku Trend (25 pts)
        $dailyTrend = $this->scoreDailyIchimoku($dailyIchi, $daily);
        $scores['daily_ichi_trend'] = $dailyTrend['score'];
        $signals['daily_ichi'] = $dailyTrend['signal'];
        
        // 2. Hourly Ichimoku Confirmation (20 pts)
        $hourlyConfirm = $this->scoreHourlyConfirmation($hourly4Ichi, $hourly1Ichi, $dailyTrend['trend']);
        $scores['hourly_ichi_confirm'] = $hourlyConfirm['score'];
        $signals['hourly_ichi'] = $hourlyConfirm['signal'];
        
        // 3. Bollinger Bands Position (15 pts)
        $bbScore = $this->scoreBollingerPosition($bollinger, $min15);
        $scores['bollinger_position'] = $bbScore['score'];
        $signals['bollinger'] = $bbScore['signal'];
        
        // 4. Stochastics Setup (15 pts)
        $stochScore = $this->scoreStochastics($stoch, $dailyTrend['trend']);
        $scores['stoch_setup'] = $stochScore['score'];
        $signals['stochastics'] = $stochScore['signal'];
        
        // 5. Support/Resistance Confluence (10 pts)
        $srScore = $this->scoreSRConfluence($dailyIchi, $hourly4Ichi, $min15);
        $scores['sr_confluence'] = $srScore['score'];
        $signals['sr_levels'] = $srScore['levels'];
        
        // 6. Relative Strength (10 pts)
        $rsScore = $this->scoreRelativeStrength($relativeStrength);
        $scores['relative_strength'] = $rsScore['score'];
        $signals['rel_strength'] = $rsScore['signal'];
        
        // 7. Candlestick Pattern (5 pts)
        $patternScore = $this->scoreCandlestickPattern($candlePattern, $dailyTrend['trend']);
        $scores['candlestick_pattern'] = $patternScore['score'];
        $signals['candle_pattern'] = $patternScore['pattern'];
        
        // Calculate total weighted score
        $totalScore = 0;
        foreach ($scores as $key => $score) {
            $totalScore += ($score / 100) * $this->weights[$key];
        }
        
        // Determine tier
        $tier = $this->calculateTier($totalScore, $scores);
        
        // Calculate entry parameters
        $entryParams = $this->calculateEntryParameters($min15, $dailyTrend['trend'], $bollinger);
        
        return array(
            'symbol' => $symbol,
            'asset_class' => $assetClass,
            'timestamp' => time(),
            'total_score' => round($totalScore, 1),
            'max_possible' => 100,
            'tier' => $tier,
            'trend_direction' => $dailyTrend['trend'],
            'individual_scores' => $scores,
            'signals' => $signals,
            'entry' => $entryParams,
            'recommendation' => $this->generateRecommendation($tier, $dailyTrend['trend']),
            'analysis_summary' => $this->generateSummary($signals, $dailyTrend['trend'])
        );
    }
    
    /**
     * Calculate Ichimoku Cloud
     */
    private function calculateIchimoku($data) {
        $tenkanPeriod = 9;
        $kijunPeriod = 26;
        $senkouBPeriod = 52;
        $displacement = 26;
        
        $closes = array_column($data, 'close');
        $highs = array_column($data, 'high');
        $lows = array_column($data, 'low');
        
        $tenkan = $this->donchian($highs, $lows, $tenkanPeriod);
        $kijun = $this->donchian($highs, $lows, $kijunPeriod);
        
        // Senkou Span A (Tenkan + Kijun)/2 displaced forward
        $senkouA = array();
        for ($i = 0; $i < count($tenkan); $i++) {
            $senkouA[$i] = ($tenkan[$i] + $kijun[$i]) / 2;
        }
        
        // Senkou Span B (Donchian of past 52 periods) displaced forward
        $senkouB = $this->donchian($highs, $lows, $senkouBPeriod);
        
        // Chikou Span (close displaced backward)
        $chikou = $closes;
        
        return array(
            'tenkan' => $tenkan,
            'kijun' => $kijun,
            'senkou_a' => $senkouA,
            'senkou_b' => $senkouB,
            'chikou' => $chikou,
            'cloud_top' => array_map('max', $senkouA, $senkouB),
            'cloud_bottom' => array_map('min', $senkouA, $senkouB)
        );
    }
    
    /**
     * Calculate Bollinger Bands
     */
    private function calculateBollinger($data, $period = 20, $stdDev = 2) {
        $closes = array_column($data, 'close');
        $sma = $this->sma($closes, $period);
        
        $upper1 = array();
        $upper2 = array();
        $lower1 = array();
        $lower2 = array();
        
        for ($i = $period - 1; $i < count($closes); $i++) {
            $slice = array_slice($closes, $i - $period + 1, $period);
            $mean = array_sum($slice) / $period;
            $variance = 0;
            foreach ($slice as $val) {
                $variance += pow($val - $mean, 2);
            }
            $std = sqrt($variance / $period);
            
            $upper2[$i] = $mean + ($stdDev * $std);
            $upper1[$i] = $mean + ($stdDev/2 * $std); // 1 std dev
            $lower1[$i] = $mean - ($stdDev/2 * $std);
            $lower2[$i] = $mean - ($stdDev * $std);
        }
        
        return array(
            'sma' => $sma,
            'upper_1std' => $upper1,
            'upper_2std' => $upper2,
            'lower_1std' => $lower1,
            'lower_2std' => $lower2
        );
    }
    
    /**
     * Calculate Stochastics with custom settings (30,10,10)
     */
    private function calculateStochastics($data, $kPeriod = 30, $smooth1 = 10, $smooth2 = 10) {
        $highs = array_column($data, 'high');
        $lows = array_column($data, 'low');
        $closes = array_column($data, 'close');
        
        $k = array();
        for ($i = $kPeriod - 1; $i < count($closes); $i++) {
            $highSlice = array_slice($highs, $i - $kPeriod + 1, $kPeriod);
            $lowSlice = array_slice($lows, $i - $kPeriod + 1, $kPeriod);
            $highest = max($highSlice);
            $lowest = min($lowSlice);
            
            if ($highest - $lowest != 0) {
                $k[$i] = 100 * (($closes[$i] - $lowest) / ($highest - $lowest));
            } else {
                $k[$i] = 50;
            }
        }
        
        // Smooth K (first smoothing)
        $kSmooth = $this->sma($k, $smooth1);
        // Smooth D (second smoothing)
        $d = $this->sma($kSmooth, $smooth2);
        
        return array(
            'k' => $kSmooth,
            'd' => $d,
            'raw_k' => $k
        );
    }
    
    /**
     * Score Daily Ichimoku Trend (25 pts max)
     */
    private function scoreDailyIchimoku($ichi, $data) {
        $last = count($data) - 1;
        $price = $data[$last]['close'];
        $prevPrice = $data[$last - 1]['close'];
        
        $tenkan = $ichi['tenkan'][$last];
        $kijun = $ichi['kijun'][$last];
        $cloudTop = $ichi['cloud_top'][$last];
        $cloudBottom = $ichi['cloud_bottom'][$last];
        
        $score = 0;
        $signal = array();
        $trend = 'neutral';
        
        // Price above cloud = bullish (10 pts)
        if ($price > $cloudTop) {
            $score += 10;
            $signal[] = 'Price above cloud';
            $trend = 'bullish';
        } elseif ($price < $cloudBottom) {
            $signal[] = 'Price below cloud';
            $trend = 'bearish';
        } else {
            $signal[] = 'Price in cloud (consolidation)';
            $score += 3;
        }
        
        // Tenkan above Kijun = bullish momentum (7 pts)
        if ($tenkan > $kijun) {
            $score += 7;
            $signal[] = 'Tenkan > Kijun (bullish momentum)';
        } elseif ($tenkan < $kijun) {
            $signal[] = 'Tenkan < Kijun (bearish momentum)';
        } else {
            $score += 2;
        }
        
        // Future cloud is bullish (Senkou A > Senkou B) (8 pts)
        $futureIdx = min($last + 26, count($ichi['senkou_a']) - 1);
        if ($ichi['senkou_a'][$futureIdx] > $ichi['senkou_b'][$futureIdx]) {
            $score += 8;
            $signal[] = 'Future cloud bullish';
        } else {
            $signal[] = 'Future cloud bearish';
        }
        
        // Chikou span confirmation (price 26 periods ago vs current)
        $chikouIdx = max(0, $last - 26);
        if ($chikouIdx < count($data)) {
            $chikouPrice = $data[$chikouIdx]['close'];
            if ($chikouPrice < $price) {
                $signal[] = 'Chikou confirms bullish';
            }
        }
        
        return array(
            'score' => $score,
            'trend' => $trend,
            'signal' => implode('; ', $signal)
        );
    }
    
    /**
     * Score Hourly Confirmation (20 pts max)
     */
    private function scoreHourlyConfirmation($ichi4h, $ichi1h, $dailyTrend) {
        $last4h = count($ichi4h['tenkan']) - 1;
        $last1h = count($ichi1h['tenkan']) - 1;
        
        $score = 0;
        $signal = array();
        
        // 4H trend aligns with daily (10 pts)
        $price4h = $ichi4h['tenkan'][$last4h]; // proxy for current price
        if ($dailyTrend == 'bullish' && $price4h > $ichi4h['cloud_top'][$last4h]) {
            $score += 10;
            $signal[] = '4H confirms bullish trend';
        } elseif ($dailyTrend == 'bearish' && $price4h < $ichi4h['cloud_bottom'][$last4h]) {
            $score += 10;
            $signal[] = '4H confirms bearish trend';
        } else {
            $signal[] = '4H trend not aligned';
        }
        
        // 1H additional confirmation (10 pts)
        $price1h = $ichi1h['tenkan'][$last1h];
        if ($dailyTrend == 'bullish' && $price1h > $ichi1h['cloud_top'][$last1h]) {
            $score += 10;
            $signal[] = '1H confirms bullish';
        } elseif ($dailyTrend == 'bearish' && $price1h < $ichi1h['cloud_bottom'][$last1h]) {
            $score += 10;
            $signal[] = '1H confirms bearish';
        } else {
            $signal[] = '1H neutral/mixed';
            $score += 3;
        }
        
        return array(
            'score' => $score,
            'signal' => implode('; ', $signal)
        );
    }
    
    /**
     * Score Bollinger Position (15 pts max)
     * Price between 1std and 2std = trending nicely
     */
    private function scoreBollingerPosition($bb, $data) {
        $last = count($data) - 1;
        $price = $data[$last]['close'];
        
        $bbKeys = array_keys($bb['upper_2std']);
        $lastBB = end($bbKeys);
        
        $upper2 = $bb['upper_2std'][$lastBB];
        $upper1 = $bb['upper_1std'][$lastBB];
        $lower1 = $bb['lower_1std'][$lastBB];
        $lower2 = $bb['lower_2std'][$lastBB];
        $sma = $bb['sma'][$lastBB];
        
        $score = 0;
        $signal = '';
        
        // Price between 1std and 2std upper = strong uptrend (15 pts)
        if ($price <= $upper2 && $price > $upper1) {
            $score = 15;
            $signal = 'Price between 1std and 2std upper (trending up)';
        }
        // Price between 1std and 2std lower = strong downtrend (15 pts for shorts)
        elseif ($price >= $lower2 && $price < $lower1) {
            $score = 15;
            $signal = 'Price between 1std and 2std lower (trending down)';
        }
        // Price above 2std = overextended (0 pts)
        elseif ($price > $upper2) {
            $score = 2;
            $signal = 'Price above 2std (overextended)';
        }
        // Price below 2std = oversold (0 pts)
        elseif ($price < $lower2) {
            $score = 2;
            $signal = 'Price below 2std (oversold/extreme)';
        }
        // Price between 0 and 1std = normal (8 pts)
        elseif ($price > $sma && $price <= $upper1) {
            $score = 8;
            $signal = 'Price between SMA and 1std upper';
        }
        elseif ($price < $sma && $price >= $lower1) {
            $score = 8;
            $signal = 'Price between SMA and 1std lower';
        }
        
        return array(
            'score' => $score,
            'signal' => $signal,
            'sma' => $sma,
            'upper_1std' => $upper1,
            'upper_2std' => $upper2,
            'lower_1std' => $lower1,
            'lower_2std' => $lower2
        );
    }
    
    /**
     * Score Stochastics (15 pts max)
     * Settings: 30,10,10 (slower than default)
     */
    private function scoreStochastics($stoch, $trend) {
        $last = count($stoch['k']) - 1;
        $k = $stoch['k'][$last];
        $d = $stoch['d'][$last];
        $prevK = $stoch['k'][$last - 1];
        
        $score = 0;
        $signal = '';
        
        if ($trend == 'bullish') {
            // In bullish trend, look for pullback to 20-40 zone then up
            if ($k > 20 && $k < 50 && $k > $d && $prevK < $stoch['k'][$last - 2]) {
                $score = 15;
                $signal = 'Stoch turning up from 20-50 zone (bullish continuation)';
            } elseif ($k > 50 && $k < 80 && $k > $d) {
                $score = 10;
                $signal = 'Stoch in 50-80 zone, bullish';
            } elseif ($k < 20) {
                $score = 8;
                $signal = 'Stoch oversold (<20), potential bounce';
            } else {
                $signal = 'Stoch at ' . round($k, 1) . ', neutral';
            }
        } else { // bearish
            // In bearish trend, look for rally to 60-80 zone then down
            if ($k > 60 && $k < 80 && $k < $d && $prevK > $stoch['k'][$last - 2]) {
                $score = 15;
                $signal = 'Stoch turning down from 60-80 zone (bearish continuation)';
            } elseif ($k > 20 && $k < 50 && $k < $d) {
                $score = 10;
                $signal = 'Stoch in 20-50 zone, bearish';
            } elseif ($k > 80) {
                $score = 8;
                $signal = 'Stoch overbought (>80), potential reversal';
            } else {
                $signal = 'Stoch at ' . round($k, 1) . ', neutral';
            }
        }
        
        return array(
            'score' => $score,
            'signal' => $signal,
            'k' => round($k, 2),
            'd' => round($d, 2)
        );
    }
    
    /**
     * Score Support/Resistance Confluence (10 pts)
     */
    private function scoreSRConfluence($dailyIchi, $hourlyIchi, $minData) {
        $last = count($minData) - 1;
        $price = $minData[$last]['close'];
        
        $score = 0;
        $levels = array();
        
        // Daily Kijun as major S/R
        $dailyKijunIdx = count($dailyIchi['kijun']) - 1;
        $dailyKijun = $dailyIchi['kijun'][$dailyKijunIdx];
        $distKijun = abs($price - $dailyKijun) / $price * 100;
        
        if ($distKijun < 1) {
            $score += 4;
            $levels[] = 'At Daily Kijun (' . round($dailyKijun, 2) . ')';
        }
        
        // Hourly cloud edge
        $hourlyIdx = count($hourlyIchi['cloud_top']) - 1;
        $hourlyCloudTop = $hourlyIchi['cloud_top'][$hourlyIdx];
        $hourlyCloudBottom = $hourlyIchi['cloud_bottom'][$hourlyIdx];
        
        $distCloudTop = abs($price - $hourlyCloudTop) / $price * 100;
        $distCloudBottom = abs($price - $hourlyCloudBottom) / $price * 100;
        
        if ($distCloudTop < 0.5 || $distCloudBottom < 0.5) {
            $score += 3;
            $levels[] = 'At Hourly Cloud edge';
        }
        
        // Recent swing high/low from 15m data
        $recentHighs = array();
        $recentLows = array();
        for ($i = max(0, $last - 20); $i <= $last; $i++) {
            $recentHighs[] = $minData[$i]['high'];
            $recentLows[] = $minData[$i]['low'];
        }
        $recentResistance = max($recentHighs);
        $recentSupport = min($recentLows);
        
        $distRes = abs($price - $recentResistance) / $price * 100;
        $distSup = abs($price - $recentSupport) / $price * 100;
        
        if ($distRes < 0.3) {
            $score += 3;
            $levels[] = 'Near 15m resistance (' . round($recentResistance, 2) . ')';
        } elseif ($distSup < 0.3) {
            $score += 3;
            $levels[] = 'Near 15m support (' . round($recentSupport, 2) . ')';
        }
        
        return array(
            'score' => min($score, 10),
            'levels' => $levels
        );
    }
    
    /**
     * Score Relative Strength (10 pts)
     */
    private function scoreRelativeStrength($symbol, $assetClass) {
        // Compare to benchmark (BTC for crypto, SPY for stocks)
        $benchmark = $assetClass == 'crypto' ? 'BTC' : 'SPY';
        
        // Fetch 7-day performance
        $symChange = $this->getPriceChange($symbol, 7);
        $benchChange = $this->getPriceChange($benchmark, 7);
        
        $score = 0;
        $signal = '';
        
        if ($symChange !== null && $benchChange !== null) {
            $relativePerf = $symChange - $benchChange;
            
            if ($relativePerf > 10) {
                $score = 10;
                $signal = "Strong outperformance vs $benchmark (+" . round($relativePerf, 1) . "%)";
            } elseif ($relativePerf > 5) {
                $score = 7;
                $signal = "Outperforming $benchmark (+" . round($relativePerf, 1) . "%)";
            } elseif ($relativePerf > 0) {
                $score = 5;
                $signal = "Slightly outperforming $benchmark (+" . round($relativePerf, 1) . "%)";
            } elseif ($relativePerf > -5) {
                $score = 3;
                $signal = "Underperforming $benchmark (" . round($relativePerf, 1) . "%)";
            } else {
                $signal = "Weak vs $benchmark (" . round($relativePerf, 1) . "%)";
            }
        } else {
            $signal = 'No RS data available';
        }
        
        return array(
            'score' => $score,
            'signal' => $signal,
            'symbol_change' => $symChange,
            'benchmark_change' => $benchChange
        );
    }
    
    /**
     * Score Candlestick Patterns (5 pts)
     */
    private function scoreCandlestickPattern($patterns, $trend) {
        $score = 0;
        $pattern = 'None';
        
        if (!empty($patterns)) {
            $lastPattern = end($patterns);
            
            if ($trend == 'bullish') {
                // Bullish patterns
                if (in_array($lastPattern, array('hammer', 'morning_star', 'bullish_engulfing'))) {
                    $score = 5;
                    $pattern = $lastPattern;
                } elseif (in_array($lastPattern, array('pinbar_bullish', 'trendline_break_bullish'))) {
                    $score = 4;
                    $pattern = $lastPattern;
                }
            } else {
                // Bearish patterns
                if (in_array($lastPattern, array('shooting_star', 'evening_star', 'bearish_engulfing'))) {
                    $score = 5;
                    $pattern = $lastPattern;
                } elseif (in_array($lastPattern, array('pinbar_bearish', 'trendline_break_bearish'))) {
                    $score = 4;
                    $pattern = $lastPattern;
                }
            }
        }
        
        return array(
            'score' => $score,
            'pattern' => $pattern
        );
    }
    
    /**
     * Detect candlestick patterns
     */
    private function detectCandlestickPatterns($data) {
        $patterns = array();
        $count = count($data);
        
        if ($count < 3) return $patterns;
        
        for ($i = 2; $i < $count; $i++) {
            $c = $data[$i];
            $p1 = $data[$i - 1];
            $p2 = $data[$i - 2];
            
            $body = abs($c['close'] - $c['open']);
            $upperShadow = $c['high'] - max($c['open'], $c['close']);
            $lowerShadow = min($c['open'], $c['close']) - $c['low'];
            $range = $c['high'] - $c['low'];
            
            if ($range == 0) continue;
            
            // Hammer (long lower shadow, small body at top)
            if ($lowerShadow > 2 * $body && $upperShadow < $body && $c['close'] > $c['open']) {
                $patterns[$i] = 'hammer';
            }
            // Shooting star (long upper shadow, small body at bottom)
            elseif ($upperShadow > 2 * $body && $lowerShadow < $body && $c['close'] < $c['open']) {
                $patterns[$i] = 'shooting_star';
            }
            // Bullish engulfing
            elseif ($c['close'] > $c['open'] && $p1['close'] < $p1['open'] &&
                    $c['open'] < $p1['close'] && $c['close'] > $p1['open']) {
                $patterns[$i] = 'bullish_engulfing';
            }
            // Bearish engulfing
            elseif ($c['close'] < $c['open'] && $p1['close'] > $p1['open'] &&
                    $c['open'] > $p1['close'] && $c['close'] < $p1['open']) {
                $patterns[$i] = 'bearish_engulfing';
            }
            // Pinbar (simplified)
            elseif ($upperShadow > 3 * $body && $c['close'] < $c['open']) {
                $patterns[$i] = 'pinbar_bearish';
            }
            elseif ($lowerShadow > 3 * $body && $c['close'] > $c['open']) {
                $patterns[$i] = 'pinbar_bullish';
            }
        }
        
        return $patterns;
    }
    
    /**
     * Calculate tier based on score
     */
    private function calculateTier($score, $componentScores) {
        // Require minimum component scores for higher tiers
        $dailyMin = $componentScores['daily_ichi_trend'] >= 15;
        $hourlyMin = $componentScores['hourly_ichi_confirm'] >= 12;
        
        if ($score >= 80 && $dailyMin && $hourlyMin) {
            return 'Strong Buy';
        } elseif ($score >= 65 && $dailyMin) {
            return 'Moderate Buy';
        } elseif ($score >= 50) {
            return 'Lean Buy';
        } elseif ($score >= 40) {
            return 'Watch';
        } else {
            return 'Avoid';
        }
    }
    
    /**
     * Calculate entry parameters
     */
    private function calculateEntryParameters($minData, $trend, $bollinger) {
        $last = count($minData) - 1;
        $currentPrice = $minData[$last]['close'];
        
        $entry = $currentPrice;
        
        // TP based on Bollinger bands or 2:1 RR
        if ($trend == 'bullish') {
            $tp = isset($bollinger['upper_2std']) ? end($bollinger['upper_2std']) : $currentPrice * 1.04;
            $sl = $currentPrice * 0.985; // 1.5% stop
        } else {
            $tp = isset($bollinger['lower_2std']) ? end($bollinger['lower_2std']) : $currentPrice * 0.96;
            $sl = $currentPrice * 1.015;
        }
        
        $risk = abs($entry - $sl) / $entry * 100;
        $reward = abs($tp - $entry) / $entry * 100;
        $rr = $risk > 0 ? $reward / $risk : 0;
        
        return array(
            'entry_price' => round($entry, 4),
            'target_price' => round($tp, 4),
            'stop_loss' => round($sl, 4),
            'risk_percent' => round($risk, 2),
            'reward_percent' => round($reward, 2),
            'risk_reward_ratio' => round($rr, 2),
            'position_size_suggestion' => $rr >= 2 ? 'Full' : ($rr >= 1.5 ? 'Half' : 'Skip')
        );
    }
    
    /**
     * Generate recommendation text
     */
    private function generateRecommendation($tier, $trend) {
        if ($tier == 'Strong Buy') {
            return "STRONG BUY: Multi-timeframe Ichimoku alignment confirmed. Enter on 15m/5m pullback to value.";
        } elseif ($tier == 'Moderate Buy') {
            return "MODERATE BUY: Trend aligned, wait for optimal entry on lower timeframe.";
        } elseif ($tier == 'Lean Buy') {
            return "LEAN BUY: Early setup forming. Monitor for confirmation.";
        } elseif ($tier == 'Watch') {
            return "WATCH: Potential setup developing. Not yet actionable.";
        } else {
            return "AVOID: No clear edge or trend alignment missing.";
        }
    }
    
    /**
     * Generate human-readable summary
     */
    private function generateSummary($signals, $trend) {
        $summary = array();
        
        $summary[] = "Daily Trend: " . $signals['daily_ichi'];
        $summary[] = "Hourly Confirmation: " . $signals['hourly_ichi'];
        $summary[] = "Entry Context: " . $signals['bollinger'];
        $summary[] = "Momentum: " . $signals['stochastics'];
        
        if (!empty($signals['sr_levels'])) {
            $summary[] = "Key Levels: " . implode(', ', $signals['sr_levels']);
        }
        
        $summary[] = "Relative Strength: " . $signals['rel_strength'];
        
        if ($signals['candle_pattern'] != 'None') {
            $summary[] = "Pattern: " . $signals['candle_pattern'];
        }
        
        return $summary;
    }
    
    /**
     * Helper: Donchian Channel
     */
    private function donchian($highs, $lows, $period) {
        $result = array();
        for ($i = $period - 1; $i < count($highs); $i++) {
            $highSlice = array_slice($highs, $i - $period + 1, $period);
            $lowSlice = array_slice($lows, $i - $period + 1, $period);
            $result[$i] = (max($highSlice) + min($lowSlice)) / 2;
        }
        return $result;
    }
    
    /**
     * Helper: Simple Moving Average
     */
    private function sma($data, $period) {
        $result = array();
        for ($i = $period - 1; $i < count($data); $i++) {
            $slice = array_slice($data, $i - $period + 1, $period);
            $result[$i] = array_sum($slice) / $period;
        }
        return $result;
    }
    
    /**
     * Fetch OHLCV data
     */
    private function fetchOHLCV($symbol, $timeframe, $limit) {
        // Try to fetch from cache or database first
        $cacheKey = "curious_ichi_{$symbol}_{$timeframe}";
        $cacheFile = "../../tmp/{$cacheKey}.json";
        
        if (file_exists($cacheFile) && (time() - filemtime($cacheFile)) < 300) {
            return json_decode(file_get_contents($cacheFile), true);
        }
        
        // Fetch from TwelveData or similar provider
        $apiKey = TWELVE_DATA_API_KEY;
        $interval = str_replace('m', 'min', str_replace('h', 'hour', str_replace('d', 'day', $timeframe)));
        
        $url = "https://api.twelvedata.com/time_series?symbol={$symbol}&interval={$interval}&outputsize={$limit}&apikey={$apiKey}";
        
        $response = @file_get_contents($url);
        if (!$response) return null;
        
        $data = json_decode($response, true);
        if (!isset($data['values'])) return null;
        
        $ohlcv = array();
        foreach (array_reverse($data['values']) as $row) {
            $ohlcv[] = array(
                'datetime' => $row['datetime'],
                'open' => floatval($row['open']),
                'high' => floatval($row['high']),
                'low' => floatval($row['low']),
                'close' => floatval($row['close']),
                'volume' => floatval($row['volume'])
            );
        }
        
        file_put_contents($cacheFile, json_encode($ohlcv));
        return $ohlcv;
    }
    
    /**
     * Get price change over N days
     */
    private function getPriceChange($symbol, $days) {
        $data = $this->fetchOHLCV($symbol, '1d', $days + 5);
        if (!$data || count($data) < 2) return null;
        
        $old = $data[0]['close'];
        $new = end($data)['close'];
        
        return (($new - $old) / $old) * 100;
    }
    
    /**
     * Get symbols to scan
     */
    private function getSymbols($assetClass) {
        if ($assetClass == 'crypto') {
            return array('BTC/USD', 'ETH/USD', 'SOL/USD', 'ADA/USD', 'DOT/USD', 
                        'LINK/USD', 'MATIC/USD', 'UNI/USD', 'AAVE/USD', 'SNX/USD');
        } else {
            return array('AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 
                        'TSLA', 'NFLX', 'AMD', 'CRM', 'PYPL', 'UBER');
        }
    }
}

// Handle API requests
$action = isset($_GET['action']) ? $_GET['action'] : 'scan';
$symbol = isset($_GET['symbol']) ? $_GET['symbol'] : null;
$assetClass = isset($_GET['asset']) ? $_GET['asset'] : 'crypto';

$strategy = new CuriousIchimokuStrategy($pdo);

switch ($action) {
    case 'scan':
        $results = $strategy->scan($symbol, $assetClass);
        echo json_encode(array(
            'ok' => true,
            'strategy' => 'Curious Ichimoku Cloud',
            'timestamp' => time(),
            'scan_type' => $symbol ? 'single' : 'full',
            'asset_class' => $assetClass,
            'results_count' => count($results),
            'results' => $results
        ));
        break;
        
    case 'explain':
        echo json_encode(array(
            'ok' => true,
            'strategy_name' => 'Curious Ichimoku Cloud',
            'description' => 'Multi-timeframe trend alignment strategy combining Ichimoku Cloud with Bollinger Bands and Stochastics',
            'methodology' => array(
                'daily_ichi' => '1D Ichimoku identifies primary trend direction',
                'hourly_confirm' => '4H/1H Ichimoku confirms trend alignment',
                'entry_edge' => '15m/5m Stochastics (30,10,10) + Bollinger Bands (1std-2std) for entry',
                'confluence' => 'S/R levels from Ichimoku + candlestick patterns for confirmation'
            ),
            'weights' => array(
                'Daily Ichimoku Trend' => '25%',
                'Hourly Confirmation' => '20%',
                'Bollinger Position' => '15%',
                'Stochastics Setup' => '15%',
                'S/R Confluence' => '10%',
                'Relative Strength' => '10%',
                'Candlestick Pattern' => '5%'
            ),
            'tiers' => array(
                'Strong Buy' => '80+ points, requires daily 15+ and hourly 12+',
                'Moderate Buy' => '65+ points, requires daily 15+',
                'Lean Buy' => '50+ points',
                'Watch' => '40+ points',
                'Avoid' => '<40 points'
            ),
            'workflow' => array(
                'Sunday Analysis' => '30 mins scanning 1D charts',
                'Alert Setup' => 'Set price alerts at key levels',
                'Weekly Trading' => 'Wait for alerts, execute on confirmation',
                'Time Required' => '20-30 mins/week'
            )
        ));
        break;
        
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}
