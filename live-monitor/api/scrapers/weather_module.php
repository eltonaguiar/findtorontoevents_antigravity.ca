<?php
/**
 * Weather Integration Module for Sports Betting
 * Provides weather data for NFL (outdoor) and MLB games
 * Free tier APIs: OpenWeatherMap, WeatherAPI, or NOAA
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

class WeatherModule {
    private $conn;
    private $errors = array();
    private $cache_ttl = 1800; // 30 minutes
    
    // Stadium coordinates for NFL and MLB
    private $stadiums = array(
        // NFL Stadiums
        'arizona cardinals' => array('lat' => 33.5276, 'lon' => -112.2626, 'roof' => 'retractable', 'city' => 'Glendale, AZ'),
        'atlanta falcons' => array('lat' => 33.7554, 'lon' => -84.4009, 'roof' => 'retractable', 'city' => 'Atlanta, GA'),
        'baltimore ravens' => array('lat' => 39.2780, 'lon' => -76.6227, 'roof' => 'open', 'city' => 'Baltimore, MD'),
        'buffalo bills' => array('lat' => 42.7738, 'lon' => -78.7869, 'roof' => 'open', 'city' => 'Orchard Park, NY'),
        'carolina panthers' => array('lat' => 35.2258, 'lon' => -80.8528, 'roof' => 'open', 'city' => 'Charlotte, NC'),
        'chicago bears' => array('lat' => 41.8623, 'lon' => -87.6167, 'roof' => 'open', 'city' => 'Chicago, IL'),
        'cincinnati bengals' => array('lat' => 39.0955, 'lon' => -84.5161, 'roof' => 'open', 'city' => 'Cincinnati, OH'),
        'cleveland browns' => array('lat' => 41.5061, 'lon' => -81.6996, 'roof' => 'open', 'city' => 'Cleveland, OH'),
        'dallas cowboys' => array('lat' => 32.7473, 'lon' => -97.0945, 'roof' => 'retractable', 'city' => 'Arlington, TX'),
        'denver broncos' => array('lat' => 39.7439, 'lon' => -105.0201, 'roof' => 'open', 'city' => 'Denver, CO', 'altitude' => 5280),
        'detroit lions' => array('lat' => 42.3400, 'lon' => -83.0456, 'roof' => 'dome', 'city' => 'Detroit, MI'),
        'green bay packers' => array('lat' => 44.5013, 'lon' => -88.0622, 'roof' => 'open', 'city' => 'Green Bay, WI'),
        'houston texans' => array('lat' => 29.6847, 'lon' => -95.4107, 'roof' => 'retractable', 'city' => 'Houston, TX'),
        'indianapolis colts' => array('lat' => 39.7601, 'lon' => -86.1639, 'roof' => 'retractable', 'city' => 'Indianapolis, IN'),
        'jacksonville jaguars' => array('lat' => 30.3239, 'lon' => -81.6373, 'roof' => 'open', 'city' => 'Jacksonville, FL'),
        'kansas city chiefs' => array('lat' => 39.0489, 'lon' => -94.4839, 'roof' => 'open', 'city' => 'Kansas City, MO'),
        'las vegas raiders' => array('lat' => 36.0909, 'lon' => -115.1833, 'roof' => 'dome', 'city' => 'Las Vegas, NV'),
        'los angeles chargers' => array('lat' => 33.9534, 'lon' => -118.3390, 'roof' => 'open', 'city' => 'Inglewood, CA'),
        'los angeles rams' => array('lat' => 33.9534, 'lon' => -118.3390, 'roof' => 'open', 'city' => 'Inglewood, CA'),
        'miami dolphins' => array('lat' => 25.9580, 'lon' => -80.2389, 'roof' => 'open', 'city' => 'Miami Gardens, FL'),
        'minnesota vikings' => array('lat' => 44.9745, 'lon' => -93.2581, 'roof' => 'dome', 'city' => 'Minneapolis, MN'),
        'new england patriots' => array('lat' => 42.0909, 'lon' => -71.2643, 'roof' => 'open', 'city' => 'Foxborough, MA'),
        'new orleans saints' => array('lat' => 29.9511, 'lon' => -90.0814, 'roof' => 'dome', 'city' => 'New Orleans, LA'),
        'new york giants' => array('lat' => 40.8135, 'lon' => -74.0745, 'roof' => 'open', 'city' => 'East Rutherford, NJ'),
        'new york jets' => array('lat' => 40.8135, 'lon' => -74.0745, 'roof' => 'open', 'city' => 'East Rutherford, NJ'),
        'philadelphia eagles' => array('lat' => 39.9008, 'lon' => -75.1675, 'roof' => 'open', 'city' => 'Philadelphia, PA'),
        'pittsburgh steelers' => array('lat' => 40.4468, 'lon' => -80.0158, 'roof' => 'open', 'city' => 'Pittsburgh, PA'),
        'san francisco 49ers' => array('lat' => 37.4030, 'lon' => -121.9700, 'roof' => 'open', 'city' => 'Santa Clara, CA'),
        'seattle seahawks' => array('lat' => 47.5952, 'lon' => -122.3316, 'roof' => 'open', 'city' => 'Seattle, WA'),
        'tampa bay buccaneers' => array('lat' => 27.9759, 'lon' => -82.5033, 'roof' => 'open', 'city' => 'Tampa, FL'),
        'tennessee titans' => array('lat' => 36.1665, 'lon' => -86.7713, 'roof' => 'open', 'city' => 'Nashville, TN'),
        'washington commanders' => array('lat' => 38.9078, 'lon' => -76.8645, 'roof' => 'open', 'city' => 'Landover, MD'),
        
        // MLB Stadiums (open air only - weather matters)
        'arizona diamondbacks' => array('lat' => 33.4453, 'lon' => -112.0667, 'roof' => 'retractable', 'city' => 'Phoenix, AZ'),
        'atlanta braves' => array('lat' => 33.8908, 'lon' => -84.4678, 'roof' => 'open', 'city' => 'Atlanta, GA'),
        'baltimore orioles' => array('lat' => 39.2839, 'lon' => -76.6217, 'roof' => 'open', 'city' => 'Baltimore, MD'),
        'boston red sox' => array('lat' => 42.3467, 'lon' => -71.0972, 'roof' => 'open', 'city' => 'Boston, MA'),
        'chicago cubs' => array('lat' => 41.9484, 'lon' => -87.6553, 'roof' => 'open', 'city' => 'Chicago, IL'),
        'chicago white sox' => array('lat' => 41.8299, 'lon' => -87.6338, 'roof' => 'open', 'city' => 'Chicago, IL'),
        'cincinnati reds' => array('lat' => 39.0979, 'lon' => -84.5082, 'roof' => 'open', 'city' => 'Cincinnati, OH'),
        'cleveland guardians' => array('lat' => 41.4962, 'lon' => -81.6852, 'roof' => 'open', 'city' => 'Cleveland, OH'),
        'colorado rockies' => array('lat' => 39.7561, 'lon' => -104.9942, 'roof' => 'open', 'city' => 'Denver, CO', 'altitude' => 5182),
        'detroit tigers' => array('lat' => 42.3390, 'lon' => -83.0485, 'roof' => 'open', 'city' => 'Detroit, MI'),
        'houston astros' => array('lat' => 29.7573, 'lon' => -95.3555, 'roof' => 'retractable', 'city' => 'Houston, TX'),
        'kansas city royals' => array('lat' => 39.0517, 'lon' => -94.4803, 'roof' => 'open', 'city' => 'Kansas City, MO'),
        'los angeles angels' => array('lat' => 33.8003, 'lon' => -117.8827, 'roof' => 'open', 'city' => 'Anaheim, CA'),
        'los angeles dodgers' => array('lat' => 34.0739, 'lon' => -118.2400, 'roof' => 'open', 'city' => 'Los Angeles, CA'),
        'miami marlins' => array('lat' => 25.7781, 'lon' => -80.2195, 'roof' => 'retractable', 'city' => 'Miami, FL'),
        'milwaukee brewers' => array('lat' => 43.0280, 'lon' => -87.9712, 'roof' => 'open', 'city' => 'Milwaukee, WI'),
        'minnesota twins' => array('lat' => 44.9817, 'lon' => -93.2775, 'roof' => 'open', 'city' => 'Minneapolis, MN'),
        'new york mets' => array('lat' => 40.7571, 'lon' => -73.8458, 'roof' => 'open', 'city' => 'Flushing, NY'),
        'new york yankees' => array('lat' => 40.8296, 'lon' => -73.9262, 'roof' => 'open', 'city' => 'Bronx, NY'),
        'oakland athletics' => array('lat' => 37.7516, 'lon' => -122.2005, 'roof' => 'open', 'city' => 'Oakland, CA'),
        'philadelphia phillies' => array('lat' => 39.9055, 'lon' => -75.1664, 'roof' => 'open', 'city' => 'Philadelphia, PA'),
        'pittsburgh pirates' => array('lat' => 40.4469, 'lon' => -80.0057, 'roof' => 'open', 'city' => 'Pittsburgh, PA'),
        'san diego padres' => array('lat' => 32.7073, 'lon' => -117.1566, 'roof' => 'open', 'city' => 'San Diego, CA'),
        'san francisco giants' => array('lat' => 37.7786, 'lon' => -122.3893, 'roof' => 'open', 'city' => 'San Francisco, CA'),
        'seattle mariners' => array('lat' => 47.5914, 'lon' => -122.3325, 'roof' => 'retractable', 'city' => 'Seattle, WA'),
        'st. louis cardinals' => array('lat' => 38.6226, 'lon' => -90.1928, 'roof' => 'open', 'city' => 'St. Louis, MO'),
        'tampa bay rays' => array('lat' => 27.7682, 'lon' => -82.6534, 'roof' => 'dome', 'city' => 'St. Petersburg, FL'),
        'texas rangers' => array('lat' => 32.7513, 'lon' => -97.0824, 'roof' => 'retractable', 'city' => 'Arlington, TX'),
        'toronto blue jays' => array('lat' => 43.6414, 'lon' => -79.3894, 'roof' => 'retractable', 'city' => 'Toronto, ON'),
        'washington nationals' => array('lat' => 38.8730, 'lon' => -77.0074, 'roof' => 'open', 'city' => 'Washington, DC')
    );
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->_ensure_tables();
    }
    
    /**
     * Get weather impact score for a game
     * Returns: -5 (severe negative) to +5 (severe positive) for totals
     */
    public function get_weather_impact($home_team, $sport, $game_time = null) {
        $team_key = strtolower($home_team);
        
        // Normalize team names
        $team_key = $this->_normalize_team_name($team_key, $sport);
        
        if (!isset($this->stadiums[$team_key])) {
            return array('impact' => 0, 'reason' => 'Stadium not found', 'weather' => null);
        }
        
        $stadium = $this->stadiums[$team_key];
        
        // Check if dome - minimal weather impact
        if ($stadium['roof'] === 'dome') {
            return array(
                'impact' => 0,
                'reason' => 'Indoor stadium - no weather impact',
                'weather' => null,
                'altitude_effect' => isset($stadium['altitude']) ? $this->_calculate_altitude_effect($stadium['altitude']) : 0
            );
        }
        
        // Get weather data
        $weather = $this->_fetch_weather($stadium['lat'], $stadium['lon'], $game_time);
        
        if (!$weather) {
            return array('impact' => 0, 'reason' => 'Weather data unavailable', 'weather' => null);
        }
        
        // Calculate impact based on sport
        $impact = $this->_calculate_impact($weather, $sport, $stadium);
        
        return array(
            'impact' => $impact['score'],
            'reason' => $impact['reason'],
            'weather' => $weather,
            'altitude_effect' => isset($stadium['altitude']) ? $this->_calculate_altitude_effect($stadium['altitude']) : 0,
            'betting_recommendation' => $impact['recommendation']
        );
    }
    
    /**
     * Batch process weather for multiple games
     */
    public function batch_weather_impact($games, $sport) {
        $results = array();
        foreach ($games as $game) {
            $home = isset($game['home_team']) ? $game['home_team'] : (isset($game['home']) ? $game['home'] : '');
            $game_time = isset($game['game_time']) ? $game['game_time'] : null;
            
            if ($home) {
                $results[] = array(
                    'home_team' => $home,
                    'impact' => $this->get_weather_impact($home, $sport, $game_time)
                );
            }
        }
        return $results;
    }
    
    /**
     * Store weather data for a game
     */
    public function store_game_weather($game_id, $home_team, $sport, $game_time) {
        $impact = $this->get_weather_impact($home_team, $sport, $game_time);
        
        if (!$impact['weather']) return false;
        
        $w = $impact['weather'];
        $game_id_esc = $this->conn->real_escape_string($game_id);
        $team_esc = $this->conn->real_escape_string($home_team);
        $sport_esc = $this->conn->real_escape_string($sport);
        $temp = isset($w['temp']) ? $w['temp'] : 'NULL';
        $wind = isset($w['wind_speed']) ? $w['wind_speed'] : 'NULL';
        $wind_dir = isset($w['wind_dir']) ? $this->conn->real_escape_string($w['wind_dir']) : '';
        $precip = isset($w['precip_chance']) ? $w['precip_chance'] : 'NULL';
        $conditions = isset($w['conditions']) ? $this->conn->real_escape_string($w['conditions']) : '';
        $impact_score = $impact['impact'];
        $rec = $this->conn->real_escape_string($impact['betting_recommendation']);
        
        $query = "INSERT INTO lm_weather_data 
                  (game_id, home_team, sport, game_time, temperature, wind_speed, wind_direction, 
                   precip_chance, conditions, impact_score, recommendation, recorded_at)
                  VALUES ('$game_id_esc', '$team_esc', '$sport_esc', '$game_time', $temp, $wind, '$wind_dir',
                          $precip, '$conditions', $impact_score, '$rec', NOW())
                  ON DUPLICATE KEY UPDATE
                  temperature=VALUES(temperature), wind_speed=VALUES(wind_speed), wind_direction=VALUES(wind_direction),
                  precip_chance=VALUES(precip_chance), conditions=VALUES(conditions), 
                  impact_score=VALUES(impact_score), recommendation=VALUES(recommendation), recorded_at=NOW()";
        
        return $this->conn->query($query);
    }
    
    /**
     * Fetch weather from NOAA/NWS (free, no key required)
     */
    private function _fetch_weather($lat, $lon, $game_time = null) {
        // Check cache first
        $cache_key = md5($lat . ',' . $lon . ',' . date('Y-m-d-H'));
        $cached = $this->_get_cache($cache_key);
        if ($cached) return $cached;
        
        // Try NOAA first (US only, free)
        $weather = $this->_fetch_noaa($lat, $lon);
        
        if (!$weather) {
            // Fallback to OpenWeatherMap if available
            $weather = $this->_fetch_openweather($lat, $lon);
        }
        
        if ($weather) {
            $this->_set_cache($cache_key, $weather);
        }
        
        return $weather;
    }
    
    /**
     * NOAA National Weather Service API (free, US only)
     */
    private function _fetch_noaa($lat, $lon) {
        // Get forecast grid endpoint
        $points_url = "https://api.weather.gov/points/$lat,$lon";
        $points = $this->_http_get($points_url);
        
        if (!$points) return null;
        
        $points_data = json_decode($points, true);
        if (!$points_data || !isset($points_data['properties']['forecast'])) return null;
        
        // Get forecast
        $forecast_url = $points_data['properties']['forecast'];
        $forecast = $this->_http_get($forecast_url);
        
        if (!$forecast) return null;
        
        $forecast_data = json_decode($forecast, true);
        if (!$forecast_data || !isset($forecast_data['properties']['periods'])) return null;
        
        $period = $forecast_data['properties']['periods'][0];
        
        // Parse wind
        $wind_speed = 0;
        $wind_dir = '';
        if (isset($period['windSpeed'])) {
            preg_match('/(\d+)/', $period['windSpeed'], $matches);
            $wind_speed = isset($matches[1]) ? (int)$matches[1] : 0;
        }
        if (isset($period['windDirection'])) {
            $wind_dir = $period['windDirection'];
        }
        
        // Extract temperature
        $temp = isset($period['temperature']) ? (int)$period['temperature'] : null;
        if ($temp && isset($period['temperatureUnit']) && $period['temperatureUnit'] === 'F') {
            // Convert F to C for consistency
            $temp = round(($temp - 32) * 5/9, 1);
        }
        
        return array(
            'temp' => $temp,
            'temp_f' => isset($period['temperature']) ? (int)$period['temperature'] : null,
            'conditions' => isset($period['shortForecast']) ? $period['shortForecast'] : '',
            'wind_speed' => $wind_speed,
            'wind_dir' => $wind_dir,
            'precip_chance' => isset($period['probabilityOfPrecipitation']['value']) ? (int)$period['probabilityOfPrecipitation']['value'] : 0,
            'humidity' => null, // Not always available
            'source' => 'NOAA'
        );
    }
    
    /**
     * OpenWeatherMap (requires API key)
     */
    private function _fetch_openweather($lat, $lon) {
        global $OPENWEATHER_API_KEY;
        
        if (empty($OPENWEATHER_API_KEY)) return null;
        
        $url = "https://api.openweathermap.org/data/2.5/weather?lat=$lat&lon=$lon&appid=$OPENWEATHER_API_KEY&units=metric";
        $response = $this->_http_get($url);
        
        if (!$response) return null;
        
        $data = json_decode($response, true);
        if (!$data) return null;
        
        return array(
            'temp' => isset($data['main']['temp']) ? round($data['main']['temp'], 1) : null,
            'temp_f' => isset($data['main']['temp']) ? round($data['main']['temp'] * 9/5 + 32, 1) : null,
            'conditions' => isset($data['weather'][0]['main']) ? $data['weather'][0]['main'] : '',
            'wind_speed' => isset($data['wind']['speed']) ? round($data['wind']['speed'] * 2.237, 1) : 0, // m/s to mph
            'wind_dir' => isset($data['wind']['deg']) ? $this->_degrees_to_direction($data['wind']['deg']) : '',
            'precip_chance' => isset($data['pop']) ? round($data['pop'] * 100) : 0,
            'humidity' => isset($data['main']['humidity']) ? (int)$data['main']['humidity'] : null,
            'source' => 'OpenWeatherMap'
        );
    }
    
    /**
     * Calculate weather impact on game
     */
    private function _calculate_impact($weather, $sport, $stadium) {
        $score = 0;
        $reasons = array();
        $recommendation = 'No significant weather impact';
        
        if ($sport === 'nfl') {
            // Wind impact on passing game
            if ($weather['wind_speed'] > 20) {
                $score -= 3;
                $reasons[] = 'High winds (' . $weather['wind_speed'] . ' mph) - hurts passing game';
                $recommendation = 'Consider UNDER on passing props';
            } elseif ($weather['wind_speed'] > 15) {
                $score -= 2;
                $reasons[] = 'Moderate winds (' . $weather['wind_speed'] . ' mph)';
            }
            
            // Temperature extremes
            if ($weather['temp_f'] !== null) {
                if ($weather['temp_f'] < 32) {
                    $score -= 2;
                    $reasons[] = 'Freezing temps - affects grip/kicking';
                    $recommendation = 'Favor run-heavy teams, UNDER total';
                } elseif ($weather['temp_f'] > 85) {
                    $score += 1;
                    $reasons[] = 'Hot weather - fatigue factor';
                }
            }
            
            // Precipitation
            if ($weather['precip_chance'] > 70) {
                $score -= 2;
                $reasons[] = 'High rain/snow chance';
                $recommendation = 'Favor UNDER, run-heavy teams';
            }
            
        } elseif ($sport === 'mlb') {
            // Wind impact on home runs
            if ($weather['wind_speed'] > 15) {
                if (strpos($weather['wind_dir'], 'Out') !== false || 
                    strpos(strtolower($weather['wind_dir']), 'w') !== false) {
                    // Wind blowing out
                    $score += 3;
                    $reasons[] = 'Wind blowing out at ' . $weather['wind_speed'] . ' mph - HR friendly';
                    $recommendation = 'Consider OVER on game total, player HR props';
                } else {
                    $score -= 1;
                    $reasons[] = 'Wind blowing in';
                }
            }
            
            // Temperature impact on ball flight
            if ($weather['temp_f'] !== null) {
                if ($weather['temp_f'] > 80) {
                    $score += 2;
                    $reasons[] = 'Warm weather - ball carries better';
                } elseif ($weather['temp_f'] < 50) {
                    $score -= 2;
                    $reasons[] = 'Cold weather - deadens ball';
                    $recommendation = 'Consider UNDER';
                }
            }
            
            // Rain delays
            if ($weather['precip_chance'] > 60) {
                $score -= 1;
                $reasons[] = 'Rain likely - possible delay';
            }
        }
        
        // Altitude effect (always apply)
        if (isset($stadium['altitude'])) {
            $alt_effect = $this->_calculate_altitude_effect($stadium['altitude']);
            if ($alt_effect !== 0) {
                $score += $alt_effect;
                $reasons[] = 'High altitude (' . $stadium['altitude'] . ' ft)';
            }
        }
        
        return array(
            'score' => max(-5, min(5, $score)),
            'reason' => implode('; ', $reasons),
            'recommendation' => $recommendation
        );
    }
    
    /**
     * Calculate altitude effect on scoring
     */
    private function _calculate_altitude_effect($altitude_feet) {
        // Denver = 5280 ft = +1.5 to totals (thinner air = ball travels farther)
        // Approximate: every 1000 ft above sea level = +0.3 to total
        if ($altitude_feet > 4000) {
            return round(($altitude_feet - 4000) / 1000 * 0.3, 1);
        }
        return 0;
    }
    
    private function _normalize_team_name($name, $sport) {
        $name = strtolower(trim($name));
        
        // Common normalizations
        $replacements = array(
            'new york' => 'new york',
            'los angeles' => 'los angeles',
            'st ' => 'st. ',
            'saint ' => 'st. '
        );
        
        foreach ($replacements as $from => $to) {
            $name = str_replace($from, $to, $name);
        }
        
        // Try to match against known stadiums
        foreach ($this->stadiums as $key => $info) {
            if (strpos($key, $name) !== false || strpos($name, $key) !== false) {
                return $key;
            }
            // Check city match
            if (isset($info['city'])) {
                $city = strtolower(explode(',', $info['city'])[0]);
                if (strpos($name, $city) !== false) {
                    return $key;
                }
            }
        }
        
        return $name;
    }
    
    private function _degrees_to_direction($degrees) {
        $directions = array('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW');
        $index = round($degrees / 22.5) % 16;
        return $directions[$index];
    }
    
    private function _http_get($url, $timeout = 10) {
        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (WeatherBot/1.0)');
            $body = curl_exec($ch);
            $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            if ($body !== false && $code >= 200 && $code < 300) return $body;
            return null;
        }
        $ctx = stream_context_create(array(
            'http' => array('method' => 'GET', 'timeout' => $timeout, 'header' => "User-Agent: Mozilla/5.0\r\n"),
            'ssl' => array('verify_peer' => false)
        ));
        $body = @file_get_contents($url, false, $ctx);
        return ($body === false) ? null : $body;
    }
    
    private function _ensure_tables() {
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_weather_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id VARCHAR(50),
            home_team VARCHAR(100),
            sport VARCHAR(20),
            game_time DATETIME,
            temperature DECIMAL(4,1),
            wind_speed DECIMAL(4,1),
            wind_direction VARCHAR(10),
            precip_chance INT,
            conditions VARCHAR(100),
            impact_score DECIMAL(3,1),
            recommendation VARCHAR(255),
            recorded_at DATETIME DEFAULT NOW(),
            INDEX idx_game (game_id),
            INDEX idx_team (home_team),
            INDEX idx_sport (sport)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_weather_cache (
            cache_key VARCHAR(32) PRIMARY KEY,
            cache_data TEXT,
            expires_at DATETIME
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
    
    private function _get_cache($key) {
        $esc_key = $this->conn->real_escape_string($key);
        $res = $this->conn->query("SELECT cache_data FROM lm_weather_cache WHERE cache_key='$esc_key' AND expires_at > NOW()");
        if ($res && $row = $res->fetch_assoc()) {
            return json_decode($row['cache_data'], true);
        }
        return null;
    }
    
    private function _set_cache($key, $data) {
        $esc_key = $this->conn->real_escape_string($key);
        $esc_data = $this->conn->real_escape_string(json_encode($data));
        $ttl = $this->cache_ttl;
        $this->conn->query("INSERT INTO lm_weather_cache (cache_key, cache_data, expires_at) 
                           VALUES ('$esc_key', '$esc_data', DATE_ADD(NOW(), INTERVAL $ttl SECOND))
                           ON DUPLICATE KEY UPDATE cache_data=VALUES(cache_data), expires_at=VALUES(expires_at)");
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'impact';
$weather = new WeatherModule($conn);

if ($action === 'impact') {
    $home = isset($_GET['home']) ? $_GET['home'] : '';
    $sport = isset($_GET['sport']) ? strtolower($_GET['sport']) : '';
    $time = isset($_GET['time']) ? $_GET['time'] : null;
    
    if ($home && $sport) {
        $result = $weather->get_weather_impact($home, $sport, $time);
        echo json_encode(array('ok' => true, 'data' => $result));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing home or sport parameter'));
    }
} elseif ($action === 'batch') {
    $games_json = isset($_GET['games']) ? $_GET['games'] : '';
    $sport = isset($_GET['sport']) ? strtolower($_GET['sport']) : '';
    $games = json_decode($games_json, true);
    if (is_array($games) && $sport) {
        $results = $weather->batch_weather_impact($games, $sport);
        echo json_encode(array('ok' => true, 'results' => $results));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Invalid games or sport'));
    }
} elseif ($action === 'store') {
    $game_id = isset($_GET['game_id']) ? $_GET['game_id'] : '';
    $home = isset($_GET['home']) ? $_GET['home'] : '';
    $sport = isset($_GET['sport']) ? $_GET['sport'] : '';
    $time = isset($_GET['time']) ? $_GET['time'] : null;
    
    if ($game_id && $home && $sport) {
        $weather->store_game_weather($game_id, $home, $sport, $time);
        echo json_encode(array('ok' => true, 'message' => 'Weather stored'));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing required parameters'));
    }
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
