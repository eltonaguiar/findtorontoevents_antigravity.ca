<?php
/**
 * Discord Interactions Backend
 * Called by Cloudflare Worker proxy (broad-sky-e096)
 * Worker handles signature verification — this just processes commands
 * 
 * MUST be PHP 5.2 compatible (server runs 5.2.17)
 */

error_reporting(0);
ini_set('display_errors', 0);

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$body = file_get_contents('php://input');
$interaction = json_decode($body, true);

if (!$interaction) {
    echo json_encode(array(
        'type' => 4,
        'data' => array('content' => 'Invalid request body')
    ));
    exit;
}

$type = isset($interaction['type']) ? intval($interaction['type']) : 0;

// PING (shouldn't reach here — Worker handles it, but just in case)
if ($type === 1) {
    echo json_encode(array('type' => 1));
    exit;
}

// Application Commands
if ($type === 2) {
    $data = isset($interaction['data']) ? $interaction['data'] : array();
    $command_name = isset($data['name']) ? $data['name'] : '';
    $options = isset($data['options']) ? $data['options'] : array();

    switch ($command_name) {
        case 'fc-crypto':
            handle_crypto($options);
            break;
        case 'fc-forex':
            send_embed('💱 Forex Signals', "Forex signal engine is being enhanced.\n\n🔗 Live Monitor: https://findtorontoevents.ca/live-monitor/live-monitor.html", 0x3b82f6);
            break;
        case 'fc-picks':
            handle_all_picks();
            break;
        case 'fc-momentum':
            handle_momentum();
            break;
        case 'fc-realtime':
            send_embed(
                '⚡ Real-Time Market Data',
                "View real-time trading signals:\n\n" .
                "🔗 Live Trading Monitor: https://findtorontoevents.ca/live-monitor/live-monitor.html\n" .
                "🔗 ML Dashboard: https://findtorontoevents.ca/updates/antigravity-ml-gainer.html\n" .
                "🔗 Crypto Pairs: https://findtorontoevents.ca/findcryptopairs/",
                0x06b6d4
            );
            break;
        case 'fc-baby-winning':
            handle_baby_winning();
            break;
        case 'top-graduation-candidates':
            handle_top_graduation_candidates();
            break;
        case 'fc-live':
            handle_live();
            break;
        case 'fc-creators':
            handle_creators();
            break;
        case 'fc-events':
            handle_events($options);
            break;
        case 'fc-about':
            handle_about($options);
            break;
        default:
            send_embed('❓ Unknown Command', 'Command /' . $command_name . ' is not recognized.', 0xef4444);
            break;
    }
    exit;
}

// Fallback
echo json_encode(array(
    'type' => 4,
    'data' => array('content' => 'Unhandled interaction type: ' . $type)
));

// ═══════════════════════════════════════════════════════
//  HELPER FUNCTIONS (PHP 5.2 compatible)
// ═══════════════════════════════════════════════════════

function send_embed($title, $description, $color, $fields_arr = array(), $footer_text = 'Not financial advice')
{
    $embed = array(
        'title' => $title,
        'description' => $description,
        'color' => $color,
    );
    if (!empty($fields_arr)) {
        $embed['fields'] = $fields_arr;
    }
    if ($footer_text) {
        $embed['footer'] = array('text' => $footer_text);
    }
    echo json_encode(array(
        'type' => 4,
        'data' => array('embeds' => array($embed))
    ));
}

function get_opt($options, $name, $default_val = '')
{
    if (!is_array($options))
        return $default_val;
    foreach ($options as $opt) {
        if (isset($opt['name']) && $opt['name'] === $name) {
            return isset($opt['value']) ? $opt['value'] : $default_val;
        }
    }
    return $default_val;
}

function load_json($path)
{
    if (!file_exists($path))
        return null;
    $raw = @file_get_contents($path);
    if (!$raw)
        return null;
    $data = json_decode($raw, true);
    return $data;
}

function fmt_price($price)
{
    $price = floatval($price);
    if ($price <= 0)
        return '$0.00';
    if ($price >= 100)
        return '$' . number_format($price, 2);
    if ($price >= 1)
        return '$' . number_format($price, 4);
    if ($price >= 0.001)
        return '$' . number_format($price, 6);
    return '$' . sprintf('%.3e', $price);
}

function find_base_path()
{
    // Server confirmed: DOCUMENT_ROOT = /home/www/findtorontoevents.ca
    // dirname(__FILE__)/../../.. resolves to /home/www (WRONG)
    $candidates = array(
        $_SERVER['DOCUMENT_ROOT'],                  // /home/www/findtorontoevents.ca (confirmed working)
        '/home/www/findtorontoevents.ca',          // absolute fallback
        dirname(__FILE__) . '/../../..',           // fc/api/ -> root (may not work on 50webs)
    );
    foreach ($candidates as $base) {
        if (file_exists($base . '/updates/data')) {
            return $base;
        }
    }
    return '/home/www/findtorontoevents.ca'; // fallback
}

// ═══════════════════════════════════════════════════════
//  COMMAND HANDLERS
// ═══════════════════════════════════════════════════════

function handle_crypto($options)
{
    $base = find_base_path();
    $active_picks = array();
    $source = '';

    // Source 1: Antigravity ML live picks (array format)
    $path = $base . '/updates/data/antigravity_ml_live_picks.json';
    $data = load_json($path);
    if (is_array($data) && !empty($data) && isset($data[0])) {
        foreach ($data as $p) {
            $p['_source'] = 'Antigravity ML';
            $active_picks[] = $p;
        }
        $source = 'Antigravity ML';
    }

    // Source 2: Antigravity ML performance (has active_picks)
    if (empty($active_picks)) {
        $path = $base . '/updates/data/antigravity_ml_performance.json';
        $data = load_json($path);
        if (is_array($data) && isset($data['active_picks']) && !empty($data['active_picks'])) {
            foreach ($data['active_picks'] as $p) {
                $p['_source'] = 'Antigravity ML';
                $active_picks[] = $p;
            }
            $source = 'Antigravity ML';
        }
    }

    // Source 3: Claude ML picks
    if (empty($active_picks)) {
        $path = $base . '/updates/data/claude_ml_picks.json';
        $data = load_json($path);
        if (is_array($data) && isset($data['picks'])) {
            foreach ($data['picks'] as $p) {
                if (!isset($p['status']) || $p['status'] === 'ACTIVE') {
                    $p['_source'] = 'Claude Code ML';
                    $active_picks[] = $p;
                }
            }
            if (!empty($active_picks)) {
                $source = 'Claude Code ML';
            }
        }
    }

    // Source 4: Claude tracker
    if (empty($active_picks)) {
        $path = $base . '/claude_gainer_ml/tracker/claude_live_picks.json';
        $data = load_json($path);
        if (is_array($data) && isset($data['picks'])) {
            foreach ($data['picks'] as $p) {
                if (!isset($p['status']) || $p['status'] === 'ACTIVE') {
                    $p['_source'] = 'Claude Code ML';
                    $active_picks[] = $p;
                }
            }
            if (!empty($active_picks)) {
                $source = 'Claude Code ML Tracker';
            }
        }
    }

    // No picks found
    if (empty($active_picks)) {
        send_embed(
            '📊 Crypto ML Picks — No Active Picks',
            "No active ML predictions currently available.\n\n" .
            "The ML scanner runs every 4 hours. Next scan should produce new picks.\n\n" .
            "🔗 Dashboard: https://findtorontoevents.ca/updates/antigravity-ml-gainer.html\n" .
            "🔗 Live Monitor: https://findtorontoevents.ca/live-monitor/live-monitor.html",
            0xf59e0b,
            array(),
            'CLAUDE CODE ML v2.0 | Not financial advice'
        );
        return;
    }

    // Build embed fields (max 8)
    $fields = array();
    $count = 0;
    foreach ($active_picks as $pick) {
        if ($count >= 8)
            break;

        $symbol = isset($pick['symbol']) ? strtoupper($pick['symbol']) : (isset($pick['coin_id']) ? strtoupper($pick['coin_id']) : '???');

        // Entry price
        $entry = 0;
        if (isset($pick['entry_price']))
            $entry = floatval($pick['entry_price']);
        elseif (isset($pick['price']))
            $entry = floatval($pick['price']);
        elseif (isset($pick['current_price']))
            $entry = floatval($pick['current_price']);

        // TP/SL
        $tp = isset($pick['tp_price']) ? floatval($pick['tp_price']) : (isset($pick['tp1_price']) ? floatval($pick['tp1_price']) : $entry * 1.10);
        $sl = isset($pick['sl_price']) ? floatval($pick['sl_price']) : $entry * 0.93;

        // Confidence
        $confidence = 'N/A';
        $prob = 0;
        if (isset($pick['pump_probability'])) {
            $prob = floatval($pick['pump_probability']);
            if ($prob >= 0.80)
                $confidence = 'VERY HIGH';
            elseif ($prob >= 0.65)
                $confidence = 'HIGH';
            elseif ($prob >= 0.50)
                $confidence = 'MEDIUM';
            else
                $confidence = 'LOW';
        } elseif (isset($pick['gainer_score'])) {
            $score = intval($pick['gainer_score']);
            $prob = $score / 100.0;
            if ($score >= 70)
                $confidence = 'HIGH';
            elseif ($score >= 50)
                $confidence = 'MEDIUM';
            else
                $confidence = 'LOW';
        }

        // Signals
        $signals = array('ML Signal');
        if (isset($pick['signals']) && is_array($pick['signals'])) {
            $signals = array_slice($pick['signals'], 0, 3);
        }
        $sig_str = implode(' | ', $signals);

        $tp_pct = $entry > 0 ? round(($tp - $entry) / $entry * 100, 1) : 0;
        $sl_pct = $entry > 0 ? round(($sl - $entry) / $entry * 100, 1) : 0;

        $fields[] = array(
            'name' => $symbol . ' — ' . $confidence . ' (' . round($prob * 100) . '%)',
            'value' => 'Entry: ' . fmt_price($entry) . "\n" .
                'TP: ' . fmt_price($tp) . ' (+' . $tp_pct . '%)  SL: ' . fmt_price($sl) . ' (' . $sl_pct . "%" . ")\n" .
                'Signals: ' . $sig_str,
            'inline' => false,
        );

        $count++;
    }

    send_embed(
        '📊 Crypto ML Picks — ' . count($active_picks) . ' Active',
        "**CLAUDE CODE - REVERSE ENGINEERED DAILY TOP GAINERS STRAT**\n" .
        "Source: " . $source . "\n\n" .
        "🔗 [Full Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html) | " .
        "[Live Monitor](https://findtorontoevents.ca/live-monitor/live-monitor.html)",
        0x22c55e,
        $fields,
        'PAPER TRADE ONLY — Not financial advice'
    );
}

function handle_all_picks()
{
    $base = find_base_path();
    $total = 0;
    $lines = array();

    // Antigravity
    $data = load_json($base . '/updates/data/antigravity_ml_live_picks.json');
    if (is_array($data)) {
        $cnt = count($data);
        $total += $cnt;
        $lines[] = '**Antigravity ML**: ' . $cnt . ' active picks';
    }

    // Claude
    $data = load_json($base . '/updates/data/claude_ml_picks.json');
    if (is_array($data) && isset($data['picks'])) {
        $cnt = 0;
        foreach ($data['picks'] as $p) {
            if (!isset($p['status']) || $p['status'] === 'ACTIVE')
                $cnt++;
        }
        $total += $cnt;
        $lines[] = '**Claude Code ML**: ' . $cnt . ' active picks';
    }

    if (empty($lines))
        $lines[] = 'No scanner data available.';

    send_embed(
        '📋 All Active Picks — ' . $total . ' Total',
        implode("\n", $lines) . "\n\n🔗 [Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)",
        0x6366f1
    );
}

function handle_momentum()
{
    $base = find_base_path();
    $desc = "Momentum data from the latest ML scan.\n\n";

    $logs = load_json($base . '/claude_gainer_ml/tracker/claude_scan_log.json');
    if (is_array($logs) && !empty($logs)) {
        $latest = end($logs);
        $desc .= '**Last Scan**: ' . (isset($latest['scan_time']) ? substr($latest['scan_time'], 0, 19) : 'N/A') . " UTC\n";
        $desc .= '**Coins Scanned**: ' . (isset($latest['coins_scanned']) ? $latest['coins_scanned'] : 'N/A') . "\n";
        $desc .= '**Top Coin**: ' . (isset($latest['top_coin']) ? strtoupper($latest['top_coin']) : 'N/A') . "\n";
        $desc .= '**Top Probability**: ' . (isset($latest['top_probability']) ? round($latest['top_probability'] * 100, 1) . '%' : 'N/A') . "\n";
    }

    $desc .= "\n🔗 [Full Dashboard](https://findtorontoevents.ca/updates/antigravity-ml-gainer.html)";

    send_embed('📈 Momentum Indicators', $desc, 0x22c55e, array(), 'CLAUDE CODE ML | Not financial advice');
}

function handle_live()
{
    // Check which creators are live — read from DB or static file
    $base = find_base_path();
    $desc = "Check who's live right now:\n\n🔗 https://findtorontoevents.ca/favcreators/\n\nUse the FavCreators app to track your favorite streamers.";
    send_embed('📺 Live Creators', $desc, 0x9333ea);
}

function handle_creators()
{
    send_embed(
        '👥 Your Tracked Creators',
        "View and manage your tracked creators:\n\n🔗 https://findtorontoevents.ca/favcreators/\n\nSign in to see your personalized creator list.",
        0x6366f1
    );
}

function handle_events($options)
{
    $category = get_opt($options, 'category', 'all');
    send_embed(
        '🎉 Toronto Events',
        "Find events in Toronto:\n\n🔗 https://findtorontoevents.ca/\n\nCategory: " . $category,
        0xf97316
    );
}

function handle_about($options)
{
    $creator = get_opt($options, 'creator', '');
    if ($creator) {
        send_embed(
            'ℹ️ About ' . $creator,
            "Look up creator info at:\n\n🔗 https://findtorontoevents.ca/favcreators/",
            0x06b6d4
        );
    } else {
        send_embed(
            'ℹ️ About',
            "FavCreators — Track your favorite content creators.\n\n🔗 https://findtorontoevents.ca/favcreators/",
            0x06b6d4
        );
    }
}

function load_baby_dashboard_data()
{
    $base = find_base_path();
    $candidates = array(
        $base . '/battleground/data/baby_strats_dashboard.json',
        dirname(__FILE__) . '/../../../battleground/data/baby_strats_dashboard.json',
        dirname(__FILE__) . '/../../../../battleground/data/baby_strats_dashboard.json',
    );

    foreach ($candidates as $path) {
        $data = load_json($path);
        if (is_array($data) && isset($data['strategies']) && is_array($data['strategies'])) {
            return $data;
        }
    }

    // Fallback to public mirror if local file isn't available on this host.
    $url = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/data/baby_strats_dashboard.json';
    $ctx = stream_context_create(array('http' => array('timeout' => 6)));
    $raw = @file_get_contents($url, false, $ctx);
    if ($raw) {
        $data = json_decode($raw, true);
        if (is_array($data) && isset($data['strategies']) && is_array($data['strategies'])) {
            return $data;
        }
    }
    return null;
}

function is_real_verified_strategy($s)
{
    if (!is_array($s))
        return false;
    if (!isset($s['verification']) || !is_array($s['verification']))
        return false;
    return !empty($s['verification']['real_data_verified']);
}

function get_forward_metric($s, $key)
{
    if (!isset($s['forward_metrics']) || !is_array($s['forward_metrics']))
        return null;
    if (!isset($s['forward_metrics'][$key]))
        return null;
    return $s['forward_metrics'][$key];
}

function to_pct_or_null($v)
{
    if ($v === null || $v === '' || !is_numeric($v))
        return null;
    $f = floatval($v);
    if (abs($f) <= 1.5)
        return $f * 100.0;
    return $f;
}

function status_badge_label($status)
{
    $s = strtolower(strval($status));
    if ($s === 'paper_trading')
        return 'PAPER';
    if ($s === 'graduated' || $s === 'live')
        return 'GRADUATED';
    if ($s === 'backtest_passed')
        return 'PASSED';
    if ($s === 'backtest_failed' || $s === 'failed')
        return 'FAILED';
    if ($s === 'backtest_error')
        return 'ERROR';
    return strtoupper($s);
}

function handle_baby_winning()
{
    $data = load_baby_dashboard_data();
    if (!$data) {
        send_embed(
            '🍼 Baby Winning Strategy',
            "Could not load baby strategy dashboard data right now.\n\nTry again in a minute.",
            0xef4444
        );
        return;
    }

    $strategies = isset($data['strategies']) && is_array($data['strategies']) ? $data['strategies'] : array();
    $eligible = array();
    foreach ($strategies as $s) {
        if (!is_real_verified_strategy($s))
            continue;
        $trades = get_forward_metric($s, 'total_trades');
        $wr = get_forward_metric($s, 'win_rate');
        if (!is_numeric($trades) || intval($trades) <= 0)
            continue;
        if (!is_numeric($wr))
            continue;
        $eligible[] = $s;
    }

    if (empty($eligible)) {
        send_embed(
            '🍼 Baby Winning Strategy',
            "No real forward winners yet.\n\n" .
            "Forward stats only appear after real matched forward trades close.\n" .
            "Use `/top-graduation-candidates` to see who is closest.",
            0xf59e0b,
            array(),
            'Forward-only, real-data policy enforced'
        );
        return;
    }

    usort($eligible, 'compare_baby_winner');
    $top = $eligible[0];
    $name = isset($top['name']) ? $top['name'] : 'unknown';
    $status = status_badge_label(isset($top['status']) ? $top['status'] : '');
    $wr_pct = to_pct_or_null(get_forward_metric($top, 'win_rate'));
    $sh = get_forward_metric($top, 'sharpe');
    $dd_pct = to_pct_or_null(get_forward_metric($top, 'max_drawdown'));
    $trades = intval(get_forward_metric($top, 'total_trades'));

    $desc = "**Top Forward Winner (Real Data)**\n\n" .
            "**$name** ($status)\n" .
            "FW Win Rate: " . ($wr_pct === null ? 'n/a' : number_format($wr_pct, 1) . '%') . "\n" .
            "FW Sharpe: " . ($sh === null ? 'n/a' : number_format(floatval($sh), 2)) . "\n" .
            "FW Max DD: " . ($dd_pct === null ? 'n/a' : number_format($dd_pct, 1) . '%') . "\n" .
            "FW Trades: " . $trades . "\n\n" .
            "🔗 https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/";

    send_embed('🍼 Baby Winning Strategy', $desc, 0x22c55e, array(), 'Forward-only winner from real matched trades');
}

function compare_baby_winner($a, $b)
{
    $a_wr = to_pct_or_null(get_forward_metric($a, 'win_rate'));
    $b_wr = to_pct_or_null(get_forward_metric($b, 'win_rate'));
    if ($a_wr === null)
        $a_wr = -9999;
    if ($b_wr === null)
        $b_wr = -9999;
    if ($a_wr < $b_wr)
        return 1;
    if ($a_wr > $b_wr)
        return -1;

    $a_sh = get_forward_metric($a, 'sharpe');
    $b_sh = get_forward_metric($b, 'sharpe');
    $a_sh = is_numeric($a_sh) ? floatval($a_sh) : -9999;
    $b_sh = is_numeric($b_sh) ? floatval($b_sh) : -9999;
    if ($a_sh < $b_sh)
        return 1;
    if ($a_sh > $b_sh)
        return -1;

    $a_t = intval(get_forward_metric($a, 'total_trades'));
    $b_t = intval(get_forward_metric($b, 'total_trades'));
    if ($a_t < $b_t)
        return 1;
    if ($a_t > $b_t)
        return -1;
    return 0;
}

function handle_top_graduation_candidates()
{
    $data = load_baby_dashboard_data();
    if (!$data) {
        send_embed('🎓 Top Graduation Candidates', 'Could not load baby strategy data right now.', 0xef4444);
        return;
    }

    $strategies = isset($data['strategies']) && is_array($data['strategies']) ? $data['strategies'] : array();
    $cands = array();
    foreach ($strategies as $s) {
        if (!is_real_verified_strategy($s))
            continue;
        $status = strtolower(isset($s['status']) ? $s['status'] : '');
        if ($status !== 'paper_trading')
            continue;
        $score = graduation_candidate_score($s);
        $s['_score'] = $score;
        $cands[] = $s;
    }

    if (empty($cands)) {
        send_embed(
            '🎓 Top Graduation Candidates',
            "No paper-trading strategies found in real-only feed.",
            0xf59e0b
        );
        return;
    }

    usort($cands, 'compare_graduation_candidates');
    $top = array_slice($cands, 0, 5);
    $fields = array();
    foreach ($top as $s) {
        $name = isset($s['name']) ? $s['name'] : 'unknown';
        $fw_wr = to_pct_or_null(get_forward_metric($s, 'win_rate'));
        $fw_sh = get_forward_metric($s, 'sharpe');
        $fw_dd = to_pct_or_null(get_forward_metric($s, 'max_drawdown'));
        $fw_t = intval(get_forward_metric($s, 'total_trades'));
        $paper = isset($s['paper_trading']) && is_array($s['paper_trading']) ? $s['paper_trading'] : array();
        $days = isset($paper['days_elapsed']) ? intval($paper['days_elapsed']) : 0;

        $fields[] = array(
            'name' => $name . ' (score ' . number_format(floatval($s['_score']), 2) . ')',
            'value' =>
                'FW WR: ' . ($fw_wr === null ? 'n/a' : number_format($fw_wr, 1) . '%') .
                ' | FW Sharpe: ' . (is_numeric($fw_sh) ? number_format(floatval($fw_sh), 2) : 'n/a') .
                ' | FW DD: ' . ($fw_dd === null ? 'n/a' : number_format($fw_dd, 1) . '%') . "\n" .
                'FW Trades: ' . $fw_t . ' | Days elapsed: ' . $days . '/30',
            'inline' => false
        );
    }

    send_embed(
        '🎓 Top Graduation Candidates',
        "Real-data paper strategies ranked by graduation readiness (forward performance + sample maturity).",
        0x3b82f6,
        $fields,
        'Forward-paper readiness only; not financial advice'
    );
}

function graduation_candidate_score($s)
{
    $wr = to_pct_or_null(get_forward_metric($s, 'win_rate'));
    $sh = get_forward_metric($s, 'sharpe');
    $dd = to_pct_or_null(get_forward_metric($s, 'max_drawdown'));
    $trades = intval(get_forward_metric($s, 'total_trades'));
    $paper = isset($s['paper_trading']) && is_array($s['paper_trading']) ? $s['paper_trading'] : array();
    $days = isset($paper['days_elapsed']) ? intval($paper['days_elapsed']) : 0;

    $wr_component = ($wr === null) ? 0.0 : min(1.0, max(0.0, $wr / 60.0));
    $sh_num = is_numeric($sh) ? floatval($sh) : 0.0;
    $sh_component = min(1.0, max(0.0, $sh_num / 1.5));
    $dd_component = ($dd === null) ? 0.0 : min(1.0, max(0.0, (20.0 - abs($dd)) / 20.0));
    $trade_component = min(1.0, max(0.0, $trades / 20.0));
    $days_component = min(1.0, max(0.0, $days / 30.0));

    return (0.30 * $wr_component) +
           (0.25 * $sh_component) +
           (0.20 * $dd_component) +
           (0.15 * $trade_component) +
           (0.10 * $days_component);
}

function compare_graduation_candidates($a, $b)
{
    $as = isset($a['_score']) ? floatval($a['_score']) : 0.0;
    $bs = isset($b['_score']) ? floatval($b['_score']) : 0.0;
    if ($as < $bs)
        return 1;
    if ($as > $bs)
        return -1;
    return compare_baby_winner($a, $b);
}
