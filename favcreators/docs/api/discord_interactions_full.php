<?php
/**
 * Discord Interactions Full Command Handler
 * Handles all /fc-* slash commands for MyFavCreators Discord Bot
 * 
 * Commands:
 *   /fc-crypto   — Show live ML crypto picks with TP/SL
 *   /fc-forex    — Show forex signals
 *   /fc-picks    — Show current active picks across all scanners
 *   /fc-momentum — Show momentum indicators
 *   /fc-realtime — Show real-time market data
 */

function debug_log($msg) {
    $file = dirname(__FILE__) . '/discord_debug.log';
    $time = date('Y-m-d H:i:s');
    file_put_contents($file, "[$time] $msg\n", FILE_APPEND);
}

function handle_interaction($interaction) {
    $data = isset($interaction['data']) ? $interaction['data'] : array();
    $command_name = isset($data['name']) ? $data['name'] : '';
    $options = isset($data['options']) ? $data['options'] : array();
    
    debug_log("Command: $command_name");
    
    switch ($command_name) {
        case 'fc-crypto':
            handle_crypto_command($options);
            break;
        case 'fc-forex':
            handle_forex_command($options);
            break;
        case 'fc-picks':
            handle_picks_command($options);
            break;
        case 'fc-momentum':
            handle_momentum_command($options);
            break;
        case 'fc-realtime':
            handle_realtime_command($options);
            break;
        case 'fc-baby-winning':
            handle_baby_winning_command($options);
            break;
        case 'top-graduation-candidates':
            handle_top_graduation_candidates_command($options);
            break;
        default:
            send_discord_response("Unknown command: `/$command_name`", 0xFF0000, true);
            break;
    }
}

function get_option_value($options, $name, $default = null) {
    foreach ($options as $opt) {
        if (isset($opt['name']) && $opt['name'] === $name) {
            return isset($opt['value']) ? $opt['value'] : $default;
        }
    }
    return $default;
}

function send_discord_response($content, $color = 0x22c55e, $ephemeral = false) {
    $response = array(
        'type' => 4,
        'data' => array(
            'embeds' => array(
                array(
                    'description' => $content,
                    'color' => $color,
                )
            )
        )
    );
    
    if ($ephemeral) {
        $response['data']['flags'] = 64;
    }
    
    header('Content-Type: application/json');
    echo json_encode($response);
}

function send_discord_embed_response($embed, $ephemeral = false) {
    $response = array(
        'type' => 4,
        'data' => array(
            'embeds' => array($embed)
        )
    );
    
    if ($ephemeral) {
        $response['data']['flags'] = 64;
    }
    
    header('Content-Type: application/json');
    echo json_encode($response);
}

/**
 * /fc-crypto — Fetch and display ML crypto picks
 */
function handle_crypto_command($options) {
    debug_log("Handling /fc-crypto");
    
    $timeline = get_option_value($options, 'timeline', 'daytrader');
    $budget = get_option_value($options, 'budget', 'medium');
    
    // Try multiple data sources in order
    $picks = null;
    $source = '';
    
    // Source 1: Claude ML picks (primary)
    $claude_picks_path = dirname(__FILE__) . '/../../../updates/data/claude_ml_picks.json';
    $claude_picks_alt = dirname(__FILE__) . '/../../../claude_gainer_ml/tracker/claude_live_picks.json';
    
    // Source 2: Antigravity ML picks
    $ag_picks_path = dirname(__FILE__) . '/../../../updates/data/antigravity_ml_picks.json';
    $ag_perf_path = dirname(__FILE__) . '/../../../updates/data/antigravity_ml_performance.json';
    
    // Source 3: Cursor ML picks
    $cursor_picks_path = dirname(__FILE__) . '/../../../updates/data/cursor_ml_picks.json';
    
    // Try Antigravity ML first (most feature-rich)
    if (file_exists($ag_picks_path)) {
        $raw = file_get_contents($ag_picks_path);
        $data = json_decode($raw, true);
        if ($data && !empty($data)) {
            $picks = $data;
            $source = 'Antigravity ML';
            debug_log("Loaded Antigravity ML picks");
        }
    }
    
    // Try Antigravity performance data (has active_picks)
    if (!$picks && file_exists($ag_perf_path)) {
        $raw = file_get_contents($ag_perf_path);
        $data = json_decode($raw, true);
        if ($data && isset($data['active_picks']) && !empty($data['active_picks'])) {
            $picks = $data;
            $source = 'Antigravity ML Performance';
            debug_log("Loaded Antigravity ML performance picks");
        }
    }
    
    // Try Claude ML picks
    if (!$picks && file_exists($claude_picks_path)) {
        $raw = file_get_contents($claude_picks_path);
        $data = json_decode($raw, true);
        if ($data && isset($data['picks']) && !empty($data['picks'])) {
            $picks = $data;
            $source = 'Claude Code ML';
            debug_log("Loaded Claude ML picks");
        }
    }
    
    // Try Claude tracker directly
    if (!$picks && file_exists($claude_picks_alt)) {
        $raw = file_get_contents($claude_picks_alt);
        $data = json_decode($raw, true);
        if ($data && isset($data['picks']) && !empty($data['picks'])) {
            $picks = $data;
            $source = 'Claude Code ML (Tracker)';
            debug_log("Loaded Claude ML tracker picks");
        }
    }
    
    // Try Cursor ML picks
    if (!$picks && file_exists($cursor_picks_path)) {
        $raw = file_get_contents($cursor_picks_path);
        $data = json_decode($raw, true);
        if ($data && !empty($data)) {
            $picks = $data;
            $source = 'Cursor ML';
            debug_log("Loaded Cursor ML picks");
        }
    }
    
    // If still no picks, try fetching from the web dashboard data
    if (!$picks) {
        $url = 'https://findtorontoevents.ca/updates/data/antigravity_ml_picks.json';
        $ctx = stream_context_create(array(
            'http' => array('timeout' => 5)
        ));
        $raw = @file_get_contents($url, false, $ctx);
        if ($raw) {
            $data = json_decode($raw, true);
            if ($data && !empty($data)) {
                $picks = $data;
                $source = 'Dashboard API';
                debug_log("Loaded picks from dashboard API");
            }
        }
    }
    
    if (!$picks) {
        debug_log("No picks data found from any source");
        $embed = array(
            'title' => '📊 Crypto ML Picks — No Active Picks',
            'description' => "No active ML predictions currently available.\n\nThe ML scanner runs every 4 hours. Next scan should produce new picks.\n\n🔗 [View Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)\n🔗 [Live Monitor](https://findtorontoevents.ca/live-monitor/live-monitor.html)",
            'color' => 0xf59e0b,
            'footer' => array('text' => 'CLAUDE CODE - REVERSE ENGINEERED DAILY TOP GAINERS STRAT | Not financial advice')
        );
        send_discord_embed_response($embed, false);
        return;
    }
    
    // Extract active picks from various data formats
    $active_picks = array();
    
    if (isset($picks['active_picks'])) {
        $active_picks = $picks['active_picks'];
    } elseif (isset($picks['picks'])) {
        foreach ($picks['picks'] as $p) {
            $status = isset($p['status']) ? $p['status'] : 'ACTIVE';
            if ($status === 'ACTIVE') {
                $active_picks[] = $p;
            }
        }
    } elseif (is_array($picks) && isset($picks[0])) {
        // Array of picks directly
        foreach ($picks as $p) {
            $status = isset($p['status']) ? $p['status'] : 'ACTIVE';
            if ($status === 'ACTIVE') {
                $active_picks[] = $p;
            }
        }
    }
    
    if (empty($active_picks)) {
        $embed = array(
            'title' => '📊 Crypto ML Picks — No Active Picks',
            'description' => "All picks have been resolved. Next scan should produce new predictions.\n\n🔗 [View Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)",
            'color' => 0xf59e0b,
            'footer' => array('text' => "Source: $source | Not financial advice")
        );
        send_discord_embed_response($embed, false);
        return;
    }
    
    // Build response fields
    $fields = array();
    $count = 0;
    foreach ($active_picks as $pick) {
        if ($count >= 8) break; // Max 8 picks in embed
        
        $symbol = isset($pick['symbol']) ? strtoupper($pick['symbol']) : (isset($pick['coin_id']) ? strtoupper($pick['coin_id']) : '???');
        
        // Handle different data formats
        $entry = 0;
        $tp = 0;
        $sl = 0;
        $confidence = 'N/A';
        $signals_str = '';
        $probability = 0;
        
        // Entry price
        if (isset($pick['entry_price'])) $entry = floatval($pick['entry_price']);
        elseif (isset($pick['entry'])) $entry = floatval($pick['entry']);
        elseif (isset($pick['price'])) $entry = floatval($pick['price']);
        elseif (isset($pick['current_price'])) $entry = floatval($pick['current_price']);
        
        // TP price  
        if (isset($pick['tp1_price'])) $tp = floatval($pick['tp1_price']);
        elseif (isset($pick['tp_price'])) $tp = floatval($pick['tp_price']);
        elseif (isset($pick['tp'])) $tp = floatval($pick['tp']);
        elseif ($entry > 0) $tp = $entry * 1.10; // Default 10%
        
        // SL price
        if (isset($pick['sl_price'])) $sl = floatval($pick['sl_price']);
        elseif (isset($pick['sl'])) $sl = floatval($pick['sl']);
        elseif ($entry > 0) $sl = $entry * 0.93; // Default -7%
        
        // Confidence  
        if (isset($pick['confidence'])) $confidence = $pick['confidence'];
        elseif (isset($pick['pump_probability'])) {
            $prob = floatval($pick['pump_probability']);
            $probability = $prob;
            if ($prob >= 0.80) $confidence = 'VERY HIGH';
            elseif ($prob >= 0.65) $confidence = 'HIGH';
            elseif ($prob >= 0.50) $confidence = 'MEDIUM';
            else $confidence = 'LOW';
        } elseif (isset($pick['gainer_score'])) {
            $score = intval($pick['gainer_score']);
            $probability = $score / 100.0;
            if ($score >= 70) $confidence = 'HIGH';
            elseif ($score >= 50) $confidence = 'MEDIUM';
            else $confidence = 'LOW';
        }
        
        // Signals
        if (isset($pick['signals']) && is_array($pick['signals'])) {
            $sig_names = array_slice($pick['signals'], 0, 3);
            $signals_str = implode(' | ', $sig_names);
        }
        if (empty($signals_str)) $signals_str = 'ML Signal';
        
        // Format prices
        $entry_fmt = format_crypto_price($entry);
        $tp_fmt = format_crypto_price($tp);
        $sl_fmt = format_crypto_price($sl);
        
        $tp_pct = $entry > 0 ? round(($tp - $entry) / $entry * 100, 1) : 0;
        $sl_pct = $entry > 0 ? round(($sl - $entry) / $entry * 100, 1) : 0;
        
        $prob_str = $probability > 0 ? ' (' . round($probability * 100) . '%)' : '';
        
        $value = "Entry: $entry_fmt\n" .
                 "TP1: $tp_fmt (+{$tp_pct}%)\n" .
                 "SL: $sl_fmt ({$sl_pct}%)\n" .
                 "Signals: $signals_str";
        
        $fields[] = array(
            'name' => "$symbol — $confidence$prob_str",
            'value' => $value,
            'inline' => false
        );
        
        $count++;
    }
    
    $updated = '';
    if (isset($picks['updated_at'])) {
        $updated = $picks['updated_at'];
    } elseif (isset($picks['last_run'])) {
        $updated = $picks['last_run'];
    }
    $updated_str = $updated ? (' | Updated: ' . substr($updated, 0, 19) . ' UTC') : '';
    
    $embed = array(
        'title' => "📊 Crypto ML Picks — " . count($active_picks) . " Active",
        'description' => "**CLAUDE CODE - REVERSE ENGINEERED DAILY TOP GAINERS STRAT**\n" .
                        "Source: $source$updated_str\n\n" .
                        "🔗 [Full Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html) | " .
                        "[Live Monitor](https://findtorontoevents.ca/live-monitor/live-monitor.html)",
        'color' => 0x22c55e,
        'fields' => $fields,
        'footer' => array('text' => "Timeline: $timeline | Budget: $budget | ⚠️ PAPER TRADE ONLY — Not financial advice")
    );
    
    send_discord_embed_response($embed, false);
}

function format_crypto_price($price) {
    if ($price >= 100) return '$' . number_format($price, 2);
    if ($price >= 1) return '$' . number_format($price, 4);
    if ($price >= 0.001) return '$' . number_format($price, 6);
    return '$' . sprintf('%.3e', $price);
}

/**
 * /fc-forex — Show forex signals
 */
function handle_forex_command($options) {
    $embed = array(
        'title' => '💱 Forex Signals',
        'description' => "Forex signal engine is being enhanced.\n\n🔗 [Live Monitor](https://findtorontoevents.ca/live-monitor/live-monitor.html)",
        'color' => 0x3b82f6,
        'footer' => array('text' => 'Not financial advice')
    );
    send_discord_embed_response($embed, false);
}

/**
 * /fc-picks — Show all active picks across scanners
 */
function handle_picks_command($options) {
    $sources = array(
        'Antigravity ML' => dirname(__FILE__) . '/../../../updates/data/antigravity_ml_picks.json',
        'Claude Code ML' => dirname(__FILE__) . '/../../../updates/data/claude_ml_picks.json',
        'Cursor ML' => dirname(__FILE__) . '/../../../updates/data/cursor_ml_picks.json',
    );
    
    $lines = array();
    $total = 0;
    
    foreach ($sources as $name => $path) {
        if (file_exists($path)) {
            $data = json_decode(file_get_contents($path), true);
            $count = 0;
            if (isset($data['picks'])) {
                foreach ($data['picks'] as $p) {
                    if (isset($p['status']) && $p['status'] === 'ACTIVE') $count++;
                }
            } elseif (isset($data['active_picks'])) {
                $count = count($data['active_picks']);
            }
            $total += $count;
            $lines[] = "**$name**: $count active picks";
        }
    }
    
    if (empty($lines)) {
        $lines[] = "No scanner data available.";
    }
    
    $embed = array(
        'title' => "📋 All Active Picks — $total Total",
        'description' => implode("\n", $lines) . "\n\n🔗 [Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)",
        'color' => 0x6366f1,
        'footer' => array('text' => 'Not financial advice')
    );
    send_discord_embed_response($embed, false);
}

/**
 * /fc-momentum — Show momentum indicators
 */
function handle_momentum_command($options) {
    // Try to read from scan log
    $scan_log_path = dirname(__FILE__) . '/../../../claude_gainer_ml/tracker/claude_scan_log.json';
    $desc = "Momentum data from the latest ML scan.\n\n";
    
    if (file_exists($scan_log_path)) {
        $logs = json_decode(file_get_contents($scan_log_path), true);
        if ($logs && !empty($logs)) {
            $latest = end($logs);
            $desc .= "**Last Scan**: " . (isset($latest['scan_time']) ? substr($latest['scan_time'], 0, 19) : 'N/A') . " UTC\n";
            $desc .= "**Coins Scanned**: " . (isset($latest['coins_scanned']) ? $latest['coins_scanned'] : 'N/A') . "\n";
            $desc .= "**Coins Analyzed**: " . (isset($latest['coins_with_features']) ? $latest['coins_with_features'] : 'N/A') . "\n";
            $desc .= "**Top Coin**: " . (isset($latest['top_coin']) ? strtoupper($latest['top_coin']) : 'N/A') . "\n";
            $desc .= "**Top Probability**: " . (isset($latest['top_probability']) ? round($latest['top_probability'] * 100, 1) . '%' : 'N/A') . "\n";
        }
    }
    
    $desc .= "\n🔗 [Full Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)";
    
    $embed = array(
        'title' => '📈 Momentum Indicators',
        'description' => $desc,
        'color' => 0x22c55e,
        'footer' => array('text' => 'CLAUDE CODE ML | Not financial advice')
    );
    send_discord_embed_response($embed, false);
}

/**
 * /fc-realtime — Show real-time market data
 */
function handle_realtime_command($options) {
    $embed = array(
        'title' => '⚡ Real-Time Market Data',
        'description' => "View real-time trading signals and market data:\n\n" .
                        "🔗 [Live Trading Monitor](https://findtorontoevents.ca/live-monitor/live-monitor.html)\n" .
                        "🔗 [ML Gainer Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)\n" .
                        "🔗 [Crypto Pair Scanner](https://findtorontoevents.ca/findcryptopairs/)\n\n" .
                        "The ML scanner runs every 4 hours with adaptive thresholds.",
        'color' => 0x06b6d4,
        'footer' => array('text' => 'Not financial advice')
    );
    send_discord_embed_response($embed, false);
}

function load_baby_dashboard_json() {
    $paths = array(
        dirname(__FILE__) . '/../../../battleground/data/baby_strats_dashboard.json',
        dirname(__FILE__) . '/../../../../battleground/data/baby_strats_dashboard.json',
    );
    foreach ($paths as $p) {
        if (file_exists($p)) {
            $raw = @file_get_contents($p);
            if ($raw) {
                $data = json_decode($raw, true);
                if ($data && isset($data['strategies']) && is_array($data['strategies'])) {
                    return $data;
                }
            }
        }
    }
    $url = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/data/baby_strats_dashboard.json';
    $ctx = stream_context_create(array('http' => array('timeout' => 6)));
    $raw = @file_get_contents($url, false, $ctx);
    if ($raw) {
        $data = json_decode($raw, true);
        if ($data && isset($data['strategies']) && is_array($data['strategies'])) {
            return $data;
        }
    }
    return null;
}

function strategy_is_real_verified($s) {
    return isset($s['verification']) && isset($s['verification']['real_data_verified']) && $s['verification']['real_data_verified'] === true;
}

function fwd_metric($s, $k) {
    if (!isset($s['forward_metrics']) || !is_array($s['forward_metrics'])) return null;
    return isset($s['forward_metrics'][$k]) ? $s['forward_metrics'][$k] : null;
}

function to_pct_val($v) {
    if ($v === null || $v === '' || !is_numeric($v)) return null;
    $f = floatval($v);
    return (abs($f) <= 1.5) ? ($f * 100.0) : $f;
}

function cmp_winner($a, $b) {
    $awr = to_pct_val(fwd_metric($a, 'win_rate'));
    $bwr = to_pct_val(fwd_metric($b, 'win_rate'));
    $awr = ($awr === null) ? -9999 : $awr;
    $bwr = ($bwr === null) ? -9999 : $bwr;
    if ($awr < $bwr) return 1;
    if ($awr > $bwr) return -1;
    $ash = is_numeric(fwd_metric($a, 'sharpe')) ? floatval(fwd_metric($a, 'sharpe')) : -9999;
    $bsh = is_numeric(fwd_metric($b, 'sharpe')) ? floatval(fwd_metric($b, 'sharpe')) : -9999;
    if ($ash < $bsh) return 1;
    if ($ash > $bsh) return -1;
    $at = intval(fwd_metric($a, 'total_trades'));
    $bt = intval(fwd_metric($b, 'total_trades'));
    if ($at < $bt) return 1;
    if ($at > $bt) return -1;
    return 0;
}

function handle_baby_winning_command($options) {
    $data = load_baby_dashboard_json();
    if (!$data) {
        send_discord_response("Could not load baby strategy data right now.", 0xFF0000, true);
        return;
    }
    $eligible = array();
    foreach ($data['strategies'] as $s) {
        if (!strategy_is_real_verified($s)) continue;
        $tr = fwd_metric($s, 'total_trades');
        $wr = fwd_metric($s, 'win_rate');
        if (!is_numeric($tr) || intval($tr) <= 0) continue;
        if (!is_numeric($wr)) continue;
        $eligible[] = $s;
    }
    if (empty($eligible)) {
        $embed = array(
            'title' => '🍼 Baby Winning Strategy',
            'description' => "No real forward winners yet.\nForward stats appear only after matched forward trades close.",
            'color' => 0xf59e0b,
            'footer' => array('text' => 'Forward-only, real-data policy enforced')
        );
        send_discord_embed_response($embed, false);
        return;
    }
    usort($eligible, 'cmp_winner');
    $top = $eligible[0];
    $wr = to_pct_val(fwd_metric($top, 'win_rate'));
    $sh = fwd_metric($top, 'sharpe');
    $dd = to_pct_val(fwd_metric($top, 'max_drawdown'));
    $tr = intval(fwd_metric($top, 'total_trades'));
    $name = isset($top['name']) ? $top['name'] : 'unknown';
    $status = isset($top['status']) ? strtoupper($top['status']) : 'UNKNOWN';
    $embed = array(
        'title' => '🍼 Baby Winning Strategy',
        'description' => "**Top Forward Winner (Real Data)**\n\n" .
            "**{$name}** ({$status})\n" .
            "FW Win Rate: " . ($wr === null ? 'n/a' : number_format($wr, 1) . '%') . "\n" .
            "FW Sharpe: " . (is_numeric($sh) ? number_format(floatval($sh), 2) : 'n/a') . "\n" .
            "FW Max DD: " . ($dd === null ? 'n/a' : number_format($dd, 1) . '%') . "\n" .
            "FW Trades: {$tr}\n\n" .
            "🔗 https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/",
        'color' => 0x22c55e,
        'footer' => array('text' => 'Forward-only winner from real matched trades')
    );
    send_discord_embed_response($embed, false);
}

function grad_score($s) {
    $wr = to_pct_val(fwd_metric($s, 'win_rate'));
    $sh = fwd_metric($s, 'sharpe');
    $dd = to_pct_val(fwd_metric($s, 'max_drawdown'));
    $tr = intval(fwd_metric($s, 'total_trades'));
    $paper = isset($s['paper_trading']) && is_array($s['paper_trading']) ? $s['paper_trading'] : array();
    $days = isset($paper['days_elapsed']) ? intval($paper['days_elapsed']) : 0;
    $wrC = ($wr === null) ? 0.0 : min(1.0, max(0.0, $wr / 60.0));
    $shC = is_numeric($sh) ? min(1.0, max(0.0, floatval($sh) / 1.5)) : 0.0;
    $ddC = ($dd === null) ? 0.0 : min(1.0, max(0.0, (20.0 - abs($dd)) / 20.0));
    $trC = min(1.0, max(0.0, $tr / 20.0));
    $dyC = min(1.0, max(0.0, $days / 30.0));
    return (0.30 * $wrC) + (0.25 * $shC) + (0.20 * $ddC) + (0.15 * $trC) + (0.10 * $dyC);
}

function cmp_grad($a, $b) {
    if ($a['_score'] < $b['_score']) return 1;
    if ($a['_score'] > $b['_score']) return -1;
    return cmp_winner($a, $b);
}

function handle_top_graduation_candidates_command($options) {
    $data = load_baby_dashboard_json();
    if (!$data) {
        send_discord_response("Could not load baby strategy data right now.", 0xFF0000, true);
        return;
    }
    $cands = array();
    foreach ($data['strategies'] as $s) {
        if (!strategy_is_real_verified($s)) continue;
        if (!isset($s['status']) || strtolower($s['status']) !== 'paper_trading') continue;
        $s['_score'] = grad_score($s);
        $cands[] = $s;
    }
    if (empty($cands)) {
        $embed = array(
            'title' => '🎓 Top Graduation Candidates',
            'description' => 'No paper-trading strategies found in real-only feed.',
            'color' => 0xf59e0b
        );
        send_discord_embed_response($embed, false);
        return;
    }
    usort($cands, 'cmp_grad');
    $top = array_slice($cands, 0, 5);
    $fields = array();
    foreach ($top as $s) {
        $name = isset($s['name']) ? $s['name'] : 'unknown';
        $wr = to_pct_val(fwd_metric($s, 'win_rate'));
        $sh = fwd_metric($s, 'sharpe');
        $dd = to_pct_val(fwd_metric($s, 'max_drawdown'));
        $tr = intval(fwd_metric($s, 'total_trades'));
        $paper = isset($s['paper_trading']) && is_array($s['paper_trading']) ? $s['paper_trading'] : array();
        $days = isset($paper['days_elapsed']) ? intval($paper['days_elapsed']) : 0;
        $fields[] = array(
            'name' => $name . ' (score ' . number_format(floatval($s['_score']), 2) . ')',
            'value' => 'FW WR: ' . ($wr === null ? 'n/a' : number_format($wr, 1) . '%') .
                ' | FW Sharpe: ' . (is_numeric($sh) ? number_format(floatval($sh), 2) : 'n/a') .
                ' | FW DD: ' . ($dd === null ? 'n/a' : number_format($dd, 1) . '%') . "\n" .
                'FW Trades: ' . $tr . ' | Days elapsed: ' . $days . '/30',
            'inline' => false
        );
    }
    $embed = array(
        'title' => '🎓 Top Graduation Candidates',
        'description' => 'Real-data paper strategies ranked by graduation readiness (forward performance + maturity).',
        'color' => 0x3b82f6,
        'fields' => $fields,
        'footer' => array('text' => 'Forward-paper readiness only; not financial advice')
    );
    send_discord_embed_response($embed, false);
}
