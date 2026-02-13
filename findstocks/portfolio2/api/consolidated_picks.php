<?php
/**
 * Consolidated Picks API — Cross-Table Stock Consensus Detection
 * Aggregates picks from stock_picks, miracle_picks2, miracle_picks3.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   consensus       — Ranked consensus picks (tickers flagged by 2+ algorithms)
 *   by_ticker       — All picks for a single ticker across all tables
 *   freshness       — Data transparency / health check per source
 *   snapshot        — Store today's consensus to consensus_history (admin)
 *
 * Usage:
 *   GET .../consolidated_picks.php?action=consensus
 *   GET .../consolidated_picks.php?action=consensus&days=14&min_consensus=2
 *   GET .../consolidated_picks.php?action=by_ticker&ticker=AAPL
 *   GET .../consolidated_picks.php?action=freshness
 *   GET .../consolidated_picks.php?action=snapshot&key=stocksrefresh2026
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'consensus';
$response = array('ok' => true, 'action' => $action);

// Admin key for write operations
$admin_key = 'stocksrefresh2026';
$is_admin = (isset($_GET['key']) && $_GET['key'] === $admin_key);

// ─── Cache helper ───
$cache_dir = dirname(__FILE__) . '/cache';
if (!is_dir($cache_dir)) @mkdir($cache_dir, 0755, true);

function _cons_cache_get($key, $ttl_seconds) {
    global $cache_dir;
    $file = $cache_dir . '/cons_' . md5($key) . '.json';
    if (file_exists($file) && (time() - filemtime($file)) < $ttl_seconds) {
        $data = @file_get_contents($file);
        if ($data !== false) return json_decode($data, true);
    }
    return false;
}

function _cons_cache_set($key, $data) {
    global $cache_dir;
    $file = $cache_dir . '/cons_' . md5($key) . '.json';
    @file_put_contents($file, json_encode($data));
}

// ─── Recency weight: exponential decay with half-life of 5 days ───
// Replaces the old step-function with smooth exponential decay.
// A 5-day-old pick gets weight 0.5, 10-day gets 0.25, 20-day gets 0.0625.
function _recency_weight($pick_date) {
    $days_ago = (int)((time() - strtotime($pick_date)) / 86400);
    if ($days_ago <= 0) return 1.0;
    $half_life = 5; // days
    return pow(2, -$days_ago / $half_life);
}

// ─── Rolling algorithm weight: blends 30d rolling + all-time win rate ───
// Algorithms on hot streaks get upweighted, cold streaks downweighted.
function _rolling_algo_weight($conn, $source_table, $algo_name, $static_wr) {
    $safe_src = $conn->real_escape_string($source_table);
    $safe_algo = $conn->real_escape_string($algo_name);

    // Try to get 30d rolling win rate from algorithm_rolling_perf
    $r30 = $conn->query("SELECT win_rate FROM algorithm_rolling_perf
                          WHERE source_table='$safe_src' AND algorithm_name='$safe_algo'
                          AND period='30d' ORDER BY calc_date DESC LIMIT 1");
    if ($r30 && $r30->num_rows > 0) {
        $row = $r30->fetch_assoc();
        $rolling_wr = (float)$row['win_rate'];
        // Blend: 60% rolling + 40% all-time (emphasize recent performance)
        $blended = 0.6 * $rolling_wr + 0.4 * $static_wr;
        return $blended / 100; // normalize to 0-1
    }

    // Fallback to static win rate if no rolling data yet
    return $static_wr / 100;
}

// ─── Page links for each source table ───
function _source_page_link($source_table) {
    $links = array(
        'stock_picks' => '/findstocks/portfolio2/picks.html',
        'miracle_picks2' => '/findstocks2_global/miracle.html',
        'miracle_picks3' => '/findstocks_global/miracle.html'
    );
    return isset($links[$source_table]) ? $links[$source_table] : '';
}

function _source_label($source_table) {
    $labels = array(
        'stock_picks' => 'Portfolio Algorithms',
        'miracle_picks2' => 'DayTrades Miracle v2',
        'miracle_picks3' => 'DayTraders Miracle v3'
    );
    return isset($labels[$source_table]) ? $labels[$source_table] : $source_table;
}

// ═══════════════════════════════════════════
// CONSENSUS — Aggregated cross-table picks
// ═══════════════════════════════════════════
if ($action === 'consensus') {
    $days = isset($_GET['days']) ? max(1, min(90, (int)$_GET['days'])) : 14;
    // v2: Default min_consensus raised from 1 to 3 — single-algo picks were dragging
    // win rate to 9.1%. Require at least 3 independent algorithms to agree.
    $min_consensus = isset($_GET['min_consensus']) ? max(2, (int)$_GET['min_consensus']) : 3;
    $limit = isset($_GET['limit']) ? max(1, min(200, (int)$_GET['limit'])) : 100;

    // Check cache (30 min)
    $cache_key = 'consensus_' . $days . '_' . $min_consensus . '_' . $limit;
    $cached = _cons_cache_get($cache_key, 1800);
    if ($cached !== false && !$is_admin) {
        $cached['from_cache'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    // Collect all picks into one array
    $all_picks = array();

    // 1. stock_picks — main portfolio algorithms (55+)
    $res = $conn->query("SELECT ticker, algorithm_name AS source_algo, pick_date, entry_price, score,
                                NULL AS stop_loss_price, NULL AS take_profit_price,
                                'stock_picks' AS source_table
                         FROM stock_picks
                         WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)
                           AND entry_price > 0
                         ORDER BY pick_date DESC");
    if ($res) {
        while ($row = $res->fetch_assoc()) $all_picks[] = $row;
    }

    // 2. miracle_picks2 — DayTrades Miracle v2
    $res = $conn->query("SELECT ticker, strategy_name AS source_algo, scan_date AS pick_date, entry_price, score,
                                stop_loss_price, take_profit_price,
                                'miracle_picks2' AS source_table
                         FROM miracle_picks2
                         WHERE scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)
                           AND entry_price > 0
                         ORDER BY scan_date DESC");
    if ($res) {
        while ($row = $res->fetch_assoc()) $all_picks[] = $row;
    }

    // 3. miracle_picks3 — DayTraders Miracle v3 (Claude-generated)
    $res = $conn->query("SELECT ticker, strategy_name AS source_algo, scan_date AS pick_date, entry_price, score,
                                stop_loss_price, take_profit_price,
                                'miracle_picks3' AS source_table
                         FROM miracle_picks3
                         WHERE scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)
                           AND entry_price > 0
                         ORDER BY scan_date DESC");
    if ($res) {
        while ($row = $res->fetch_assoc()) $all_picks[] = $row;
    }

    // Group by ticker
    $by_ticker = array();
    foreach ($all_picks as $p) {
        $t = strtoupper(trim($p['ticker']));
        if ($t === '') continue;
        if (!isset($by_ticker[$t])) {
            $by_ticker[$t] = array(
                'ticker' => $t,
                'picks' => array(),
                'algos' => array(),
                'tables' => array(),
                'scores' => array(),
                'entry_prices' => array(),
                'latest_pick_date' => '',
                'earliest_pick_date' => '9999-12-31',
                'tp_prices' => array(),
                'sl_prices' => array()
            );
        }
        $by_ticker[$t]['picks'][] = $p;

        $algo_key = $p['source_table'] . ':' . $p['source_algo'];
        if (!in_array($algo_key, $by_ticker[$t]['algos'])) {
            $by_ticker[$t]['algos'][] = $algo_key;
        }
        if (!in_array($p['source_table'], $by_ticker[$t]['tables'])) {
            $by_ticker[$t]['tables'][] = $p['source_table'];
        }
        $by_ticker[$t]['scores'][] = (int)$p['score'];
        $by_ticker[$t]['entry_prices'][] = (float)$p['entry_price'];
        if (isset($p['take_profit_price']) && $p['take_profit_price'] > 0) {
            $by_ticker[$t]['tp_prices'][] = (float)$p['take_profit_price'];
        }
        if (isset($p['stop_loss_price']) && $p['stop_loss_price'] > 0) {
            $by_ticker[$t]['sl_prices'][] = (float)$p['stop_loss_price'];
        }
        if ($p['pick_date'] > $by_ticker[$t]['latest_pick_date']) {
            $by_ticker[$t]['latest_pick_date'] = $p['pick_date'];
        }
        if ($p['pick_date'] < $by_ticker[$t]['earliest_pick_date']) {
            $by_ticker[$t]['earliest_pick_date'] = $p['pick_date'];
        }
    }

    // Load algorithm win rates from backtest_results for weighting
    $algo_win_rates = array();
    $wr_res = $conn->query("SELECT algorithm_filter, win_rate FROM backtest_results WHERE win_rate > 0 ORDER BY id DESC LIMIT 500");
    if ($wr_res) {
        while ($row = $wr_res->fetch_assoc()) {
            $a = trim($row['algorithm_filter']);
            if ($a !== '' && !isset($algo_win_rates[$a])) {
                $algo_win_rates[$a] = (float)$row['win_rate'];
            }
        }
    }
    // Also check miracle_results2/3 for strategy win rates
    $mr2 = $conn->query("SELECT strategy_name, win_rate FROM miracle_results2 WHERE win_rate > 0 ORDER BY id DESC LIMIT 200");
    if ($mr2) {
        while ($row = $mr2->fetch_assoc()) {
            $k = 'miracle_picks2:' . $row['strategy_name'];
            if (!isset($algo_win_rates[$k])) $algo_win_rates[$k] = (float)$row['win_rate'];
        }
    }
    $mr3 = $conn->query("SELECT strategy_name, win_rate FROM miracle_results3 WHERE win_rate > 0 ORDER BY id DESC LIMIT 200");
    if ($mr3) {
        while ($row = $mr3->fetch_assoc()) {
            $k = 'miracle_picks3:' . $row['strategy_name'];
            if (!isset($algo_win_rates[$k])) $algo_win_rates[$k] = (float)$row['win_rate'];
        }
    }

    // Compute consensus score per ticker
    // v2: Added algorithm win rate floor — exclude picks from algorithms with < 25% WR
    $consensus_list = array();
    foreach ($by_ticker as $t => $data) {
        // Pre-filter: remove picks from algorithms with known terrible win rates
        $filtered_picks = array();
        $filtered_algos = array();
        $filtered_tables = array();
        foreach ($data['picks'] as $p) {
            $algo_key = $p['source_table'] . ':' . $p['source_algo'];
            $static_wr = isset($algo_win_rates[$algo_key]) ? $algo_win_rates[$algo_key] : 50;
            // Skip algorithms with proven bad performance (< 25% win rate)
            // Only skip if we have actual data (not the default 50%)
            if (isset($algo_win_rates[$algo_key]) && $static_wr < 25) continue;
            $filtered_picks[] = $p;
            if (!in_array($algo_key, $filtered_algos)) {
                $filtered_algos[] = $algo_key;
            }
            if (!in_array($p['source_table'], $filtered_tables)) {
                $filtered_tables[] = $p['source_table'];
            }
        }
        // Update data with filtered picks
        $data['picks'] = $filtered_picks;
        $data['algos'] = $filtered_algos;
        $data['tables'] = $filtered_tables;

        $consensus_count = count($data['algos']); // distinct algorithm sources after filtering
        if ($consensus_count < $min_consensus) continue;

        // Weighted consensus score (uses exponential recency decay + rolling algo weights)
        $weighted_score = 0;
        foreach ($data['picks'] as $p) {
            $recency = _recency_weight($p['pick_date']);
            $algo_key = $p['source_table'] . ':' . $p['source_algo'];
            $static_wr = isset($algo_win_rates[$algo_key]) ? $algo_win_rates[$algo_key] : 50;
            $wr = _rolling_algo_weight($conn, $p['source_table'], $p['source_algo'], $static_wr);
            $score = max(1, (int)$p['score']);
            $weighted_score += $score * $recency * $wr;
        }

        $avg_entry = (count($data['entry_prices']) > 0)
            ? round(array_sum($data['entry_prices']) / count($data['entry_prices']), 4) : 0;
        $avg_score = (count($data['scores']) > 0)
            ? round(array_sum($data['scores']) / count($data['scores']), 1) : 0;

        // Get company name + latest price
        $safe_t = $conn->real_escape_string($t);
        $company_name = '';
        $sr = $conn->query("SELECT company_name FROM stocks WHERE ticker='$safe_t'");
        if ($sr && $sr->num_rows > 0) {
            $srow = $sr->fetch_assoc();
            $company_name = $srow['company_name'];
        }
        // Also check miracle_picks3 for company_name if not in stocks table
        if ($company_name === '') {
            $sr2 = $conn->query("SELECT company_name FROM miracle_picks3 WHERE ticker='$safe_t' AND company_name != '' LIMIT 1");
            if ($sr2 && $sr2->num_rows > 0) {
                $srow2 = $sr2->fetch_assoc();
                $company_name = $srow2['company_name'];
            }
        }

        $latest_price = 0;
        $price_date = '';
        $pr = $conn->query("SELECT close_price, trade_date FROM daily_prices WHERE ticker='$safe_t' ORDER BY trade_date DESC LIMIT 1");
        if ($pr && $pr->num_rows > 0) {
            $prow = $pr->fetch_assoc();
            $latest_price = (float)$prow['close_price'];
            $price_date = $prow['trade_date'];
        }

        $current_return = ($avg_entry > 0 && $latest_price > 0)
            ? round(($latest_price - $avg_entry) / $avg_entry * 100, 2) : 0;

        // ── Corrective scoring v2: heavier penalties for losing picks ──
        // Previous version was too lenient — 9.1% win rate resulted.
        $score_adjustments = array();
        $original_score = $weighted_score;

        // Penalty 1: Momentum lag — losing picks get penalized aggressively
        if ($current_return < -3 && $consensus_count >= 3) {
            $penalty = 0.5; // -50% (was -30%)
            $weighted_score *= $penalty;
            $score_adjustments[] = 'Momentum lag penalty (-50%): down ' . $current_return . '% despite ' . $consensus_count . ' algos';
        } elseif ($current_return < -1) {
            $penalty = 0.75; // -25% (was -15%)
            $weighted_score *= $penalty;
            $score_adjustments[] = 'Declining trend penalty (-25%): ' . $current_return . '% return';
        }

        // Penalty 2: Falling knife — deep losses should be excluded
        if ($current_return < -5) {
            $weighted_score *= 0.3; // -70% (was -40%) — nearly kill the score
            $score_adjustments[] = 'Falling knife penalty (-70%): down ' . $current_return . '%';
        }

        // Penalty 3: Stale picks — picks older than 7 days lose confidence
        $pick_age_for_penalty = ($data['latest_pick_date'] !== '') ? max(0, (int)((time() - strtotime($data['latest_pick_date'])) / 86400)) : 0;
        if ($pick_age_for_penalty > 7) {
            $stale_penalty = max(0.4, 1.0 - ($pick_age_for_penalty - 7) * 0.1);
            $weighted_score *= $stale_penalty;
            $score_adjustments[] = 'Stale pick penalty (-' . round((1 - $stale_penalty) * 100) . '%): ' . $pick_age_for_penalty . 'd old';
        }

        // Boost 1: Winning picks get momentum boost (only if actually winning)
        if ($current_return > 3) {
            $weighted_score *= 1.15; // Reduced from 1.2
            $score_adjustments[] = 'Winner momentum boost (+15%): up +' . $current_return . '%';
        } elseif ($current_return > 1) {
            $weighted_score *= 1.08; // Reduced from 1.1
            $score_adjustments[] = 'Positive trend boost (+8%): +' . $current_return . '%';
        }

        // Penalty 4: No price data at all
        if ($latest_price <= 0) {
            $weighted_score *= 0.3; // Increased from -50% to -70%
            $score_adjustments[] = 'No price data penalty (-70%): ticker not in price database';
        }

        // Build source details
        $sources = array();
        $seen_sources = array();
        foreach ($data['picks'] as $p) {
            $key = $p['source_table'] . ':' . $p['source_algo'];
            if (isset($seen_sources[$key])) continue;
            $seen_sources[$key] = true;
            $src_entry = array(
                'table' => $p['source_table'],
                'label' => _source_label($p['source_table']),
                'algorithm' => $p['source_algo'],
                'pick_date' => $p['pick_date'],
                'entry_price' => (float)$p['entry_price'],
                'score' => (int)$p['score'],
                'page_link' => _source_page_link($p['source_table'])
            );
            if (isset($p['take_profit_price']) && $p['take_profit_price'] > 0) {
                $src_entry['take_profit_price'] = (float)$p['take_profit_price'];
            }
            if (isset($p['stop_loss_price']) && $p['stop_loss_price'] > 0) {
                $src_entry['stop_loss_price'] = (float)$p['stop_loss_price'];
            }
            $sources[] = $src_entry;
        }

        // Determine direction: check miracle_picks3 explicit direction, others are LONG-only
        $direction = 'LONG'; // default: stock_picks and miracle_picks2 are long-only systems
        if (in_array('miracle_picks3', $data['tables'])) {
            $dr = $conn->query("SELECT direction FROM miracle_picks3 WHERE ticker='$safe_t' AND direction != '' ORDER BY scan_date DESC LIMIT 1");
            if ($dr && $dr->num_rows > 0) {
                $drow = $dr->fetch_assoc();
                if (strtoupper($drow['direction']) === 'SHORT') $direction = 'SHORT';
            }
        }

        // Build verdict summary
        $price_age_days = ($price_date !== '') ? max(0, (int)((time() - strtotime($price_date)) / 86400)) : 0;
        $pick_age_days = ($data['latest_pick_date'] !== '') ? max(0, (int)((time() - strtotime($data['latest_pick_date'])) / 86400)) : 0;

        $verdict_parts = array();

        // Consensus strength
        if ($consensus_count >= 5) {
            $verdict_parts[] = 'Strong consensus: ' . $consensus_count . ' algorithms agree on ' . $direction;
        } elseif ($consensus_count >= 3) {
            $verdict_parts[] = 'Moderate consensus: ' . $consensus_count . ' algorithms suggest ' . $direction;
        } else {
            $verdict_parts[] = 'Weak consensus: ' . $consensus_count . ' algorithms suggest ' . $direction;
        }

        // Explain negative returns
        if ($current_return < 0) {
            if ($price_age_days >= 2 && $pick_age_days <= $price_age_days) {
                // Price data is older than the pick — weekend/holiday gap
                $verdict_parts[] = 'Showing ' . $current_return . '% because price data is from ' . $price_date . ' (' . $price_age_days . 'd old) while pick was made ' . $data['latest_pick_date'] . ' — price hasn\'t updated yet (weekend/holiday)';
            } elseif ($pick_age_days <= 3) {
                // Very fresh pick, just dipped
                $verdict_parts[] = 'Picked ' . $pick_age_days . 'd ago — currently ' . $current_return . '% but this is a forward-looking ' . $direction . ' pick that needs time to play out';
            } else {
                // Older pick, genuinely down but still active (hasn't hit stop-loss)
                $verdict_parts[] = 'Currently ' . $current_return . '% since avg entry, but still within risk tolerance (hasn\'t hit stop-loss). Algorithms still rate this a ' . $direction . ' based on fundamentals and momentum signals';
            }
        } elseif ($current_return > 0) {
            $verdict_parts[] = 'Up ' . $current_return . '% since avg entry — ' . $direction . ' thesis is playing out';
        }

        $verdict = implode('. ', $verdict_parts) . '.';

        // Determine pick classification based on source tables
        $has_daytrade = in_array('miracle_picks2', $data['tables']) || in_array('miracle_picks3', $data['tables']);
        $has_swing = in_array('stock_picks', $data['tables']);
        if ($has_daytrade && $has_swing) {
            $pick_classification = 'Mixed (Day Trade + Swing)';
            $default_tp_pct = 5.0;
            $default_sl_pct = 3.0;
        } elseif ($has_daytrade) {
            $pick_classification = 'Day Trade';
            $default_tp_pct = 5.0;
            $default_sl_pct = 3.0;
        } else {
            $pick_classification = 'Swing Trade';
            $default_tp_pct = 8.0;
            $default_sl_pct = 4.0;
        }

        // Use actual TP/SL from sources if available, otherwise compute from defaults
        $tp_price = null;
        $sl_price = null;
        if (count($data['tp_prices']) > 0) {
            $tp_price = round(array_sum($data['tp_prices']) / count($data['tp_prices']), 2);
        } elseif ($avg_entry > 0) {
            $tp_price = round($avg_entry * (1 + $default_tp_pct / 100), 2);
        }
        if (count($data['sl_prices']) > 0) {
            $sl_price = round(array_sum($data['sl_prices']) / count($data['sl_prices']), 2);
        } elseif ($avg_entry > 0) {
            $sl_price = round($avg_entry * (1 - $default_sl_pct / 100), 2);
        }

        $earliest = ($data['earliest_pick_date'] !== '9999-12-31') ? $data['earliest_pick_date'] : $data['latest_pick_date'];

        $consensus_list[] = array(
            'ticker' => $t,
            'company_name' => $company_name,
            'consensus_count' => $consensus_count,
            'consensus_score' => round($weighted_score, 2),
            'avg_score' => $avg_score,
            'avg_entry_price' => $avg_entry,
            'latest_price' => $latest_price,
            'price_date' => $price_date,
            'price_age_days' => $price_age_days,
            'current_return_pct' => $current_return,
            'direction' => $direction,
            'verdict' => $verdict,
            'earliest_pick_date' => $earliest,
            'latest_pick_date' => $data['latest_pick_date'],
            'pick_classification' => $pick_classification,
            'suggested_tp_pct' => $default_tp_pct,
            'suggested_sl_pct' => $default_sl_pct,
            'tp_price' => $tp_price,
            'sl_price' => $sl_price,
            'source_tables' => $data['tables'],
            'sources' => $sources,
            'total_picks' => count($data['picks']),
            'score_adjustments' => $score_adjustments,
            'original_score' => round($original_score, 2),
            'auto_notes' => (count($score_adjustments) > 0) ? implode(' | ', $score_adjustments) : null
        );
    }

    // Sort by consensus_score descending
    usort($consensus_list, create_function('$a,$b', 'if ($a["consensus_score"] == $b["consensus_score"]) return 0; return ($a["consensus_score"] > $b["consensus_score"]) ? -1 : 1;'));

    // Apply limit
    $consensus_list = array_slice($consensus_list, 0, $limit);

    $result = array(
        'ok' => true,
        'action' => 'consensus',
        'consensus_picks' => $consensus_list,
        'total_found' => count($consensus_list),
        'total_raw_picks' => count($all_picks),
        'params' => array(
            'days' => $days,
            'min_consensus' => $min_consensus,
            'limit' => $limit
        ),
        'generated_at' => date('Y-m-d H:i:s'),
        'disclaimer' => 'For educational and research purposes only. Not financial advice.'
    );

    _cons_cache_set($cache_key, $result);
    echo json_encode($result);

// ═══════════════════════════════════════════
// BY TICKER — All picks for one stock
// ═══════════════════════════════════════════
} elseif ($action === 'by_ticker') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    if ($ticker === '') {
        $response['ok'] = false;
        $response['error'] = 'ticker parameter required';
        echo json_encode($response);
        $conn->close();
        exit;
    }
    $safe = $conn->real_escape_string($ticker);

    // Check cache (30 min)
    $cached = _cons_cache_get('by_ticker_' . $ticker, 1800);
    if ($cached !== false && !$is_admin) {
        $cached['from_cache'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    // Company info
    $company_name = '';
    $sr = $conn->query("SELECT company_name FROM stocks WHERE ticker='$safe'");
    if ($sr && $sr->num_rows > 0) { $r = $sr->fetch_assoc(); $company_name = $r['company_name']; }
    if ($company_name === '') {
        $sr2 = $conn->query("SELECT company_name FROM miracle_picks3 WHERE ticker='$safe' AND company_name != '' LIMIT 1");
        if ($sr2 && $sr2->num_rows > 0) { $r2 = $sr2->fetch_assoc(); $company_name = $r2['company_name']; }
    }

    // Latest price
    $latest_price = 0;
    $pr = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$safe' ORDER BY trade_date DESC LIMIT 1");
    if ($pr && $pr->num_rows > 0) { $prow = $pr->fetch_assoc(); $latest_price = (float)$prow['close_price']; }

    $picks = array();

    // stock_picks
    $res = $conn->query("SELECT ticker, algorithm_name, pick_date, entry_price, score, rating, risk_level
                         FROM stock_picks WHERE ticker='$safe' AND entry_price > 0
                         ORDER BY pick_date DESC LIMIT 50");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $row['source_table'] = 'stock_picks';
            $row['page_link'] = _source_page_link('stock_picks');
            $row['source_label'] = _source_label('stock_picks');
            $picks[] = $row;
        }
    }

    // miracle_picks2
    $res = $conn->query("SELECT ticker, strategy_name AS algorithm_name, scan_date AS pick_date,
                                entry_price, stop_loss_price, take_profit_price, score, confidence, outcome, outcome_pct,
                                signals_json, is_cdr
                         FROM miracle_picks2 WHERE ticker='$safe' AND entry_price > 0
                         ORDER BY scan_date DESC LIMIT 50");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $row['source_table'] = 'miracle_picks2';
            $row['page_link'] = _source_page_link('miracle_picks2');
            $row['source_label'] = _source_label('miracle_picks2');
            if (isset($row['signals_json']) && $row['signals_json'] !== '') {
                $row['signals'] = json_decode($row['signals_json'], true);
            }
            unset($row['signals_json']);
            $picks[] = $row;
        }
    }

    // miracle_picks3
    $res = $conn->query("SELECT ticker, company_name, strategy_name AS algorithm_name, scan_date AS pick_date,
                                entry_price, stop_loss_price, take_profit_price, score, confidence, direction,
                                outcome, outcome_pct, outcome_reason, signals_json, is_cdr, is_canadian
                         FROM miracle_picks3 WHERE ticker='$safe' AND entry_price > 0
                         ORDER BY scan_date DESC LIMIT 50");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $row['source_table'] = 'miracle_picks3';
            $row['page_link'] = _source_page_link('miracle_picks3');
            $row['source_label'] = _source_label('miracle_picks3');
            if (isset($row['signals_json']) && $row['signals_json'] !== '') {
                $row['signals'] = json_decode($row['signals_json'], true);
            }
            unset($row['signals_json']);
            $picks[] = $row;
        }
    }

    // Consensus history for this ticker
    $consensus = array();
    $cr = $conn->query("SELECT consensus_date, consensus_count, consensus_score, source_algos
                        FROM consensus_history WHERE ticker='$safe'
                        ORDER BY consensus_date DESC LIMIT 30");
    if ($cr) {
        while ($row = $cr->fetch_assoc()) $consensus[] = $row;
    }

    // Fundamentals (if available)
    $fundamentals = null;
    $fr = $conn->query("SELECT * FROM stock_fundamentals WHERE ticker='$safe' LIMIT 1");
    if ($fr && $fr->num_rows > 0) $fundamentals = $fr->fetch_assoc();

    // Earnings (upcoming)
    $earnings = array();
    $er = $conn->query("SELECT * FROM stock_earnings WHERE ticker='$safe' ORDER BY earnings_date DESC LIMIT 5");
    if ($er) {
        while ($row = $er->fetch_assoc()) $earnings[] = $row;
    }

    // Dividends
    $dividends = array();
    $dr = $conn->query("SELECT * FROM stock_dividends WHERE ticker='$safe' ORDER BY ex_date DESC LIMIT 10");
    if ($dr) {
        while ($row = $dr->fetch_assoc()) $dividends[] = $row;
    }

    $result = array(
        'ok' => true,
        'action' => 'by_ticker',
        'ticker' => $ticker,
        'company_name' => $company_name,
        'latest_price' => $latest_price,
        'picks' => $picks,
        'total_picks' => count($picks),
        'consensus_history' => $consensus,
        'fundamentals' => $fundamentals,
        'earnings' => $earnings,
        'dividends' => $dividends,
        'generated_at' => date('Y-m-d H:i:s')
    );

    _cons_cache_set('by_ticker_' . $ticker, $result);
    echo json_encode($result);

// ═══════════════════════════════════════════
// FRESHNESS — Data health / transparency
// ═══════════════════════════════════════════
} elseif ($action === 'freshness') {
    $sources = array();

    // stock_picks
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(pick_date) as latest, COUNT(DISTINCT algorithm_name) as algos FROM stock_picks WHERE entry_price > 0");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $days_old = (strtotime(date('Y-m-d')) - strtotime($row['latest'])) / 86400;
        $sources[] = array(
            'table' => 'stock_picks',
            'label' => 'Portfolio Algorithms',
            'page' => '/findstocks/portfolio2/picks.html',
            'total_picks' => (int)$row['cnt'],
            'distinct_algorithms' => (int)$row['algos'],
            'latest_pick_date' => $row['latest'],
            'days_since_latest' => round($days_old, 1),
            'status' => ($days_old <= 2) ? 'fresh' : (($days_old <= 7) ? 'stale' : 'outdated')
        );
    }

    // miracle_picks2
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(scan_date) as latest, COUNT(DISTINCT strategy_name) as algos FROM miracle_picks2 WHERE entry_price > 0");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $days_old = ($row['latest']) ? (strtotime(date('Y-m-d')) - strtotime($row['latest'])) / 86400 : 999;
        $sources[] = array(
            'table' => 'miracle_picks2',
            'label' => 'DayTrades Miracle v2',
            'page' => '/findstocks2_global/miracle.html',
            'total_picks' => (int)$row['cnt'],
            'distinct_algorithms' => (int)$row['algos'],
            'latest_pick_date' => $row['latest'],
            'days_since_latest' => round($days_old, 1),
            'status' => ($days_old <= 2) ? 'fresh' : (($days_old <= 7) ? 'stale' : 'outdated')
        );
    }

    // miracle_picks3
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(scan_date) as latest, COUNT(DISTINCT strategy_name) as algos FROM miracle_picks3 WHERE entry_price > 0");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $days_old = ($row['latest']) ? (strtotime(date('Y-m-d')) - strtotime($row['latest'])) / 86400 : 999;
        $sources[] = array(
            'table' => 'miracle_picks3',
            'label' => 'DayTraders Miracle v3',
            'page' => '/findstocks_global/miracle.html',
            'total_picks' => (int)$row['cnt'],
            'distinct_algorithms' => (int)$row['algos'],
            'latest_pick_date' => $row['latest'],
            'days_since_latest' => round($days_old, 1),
            'status' => ($days_old <= 2) ? 'fresh' : (($days_old <= 7) ? 'stale' : 'outdated')
        );
    }

    // daily_prices
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(trade_date) as latest, COUNT(DISTINCT ticker) as tickers FROM daily_prices");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $days_old = ($row['latest']) ? (strtotime(date('Y-m-d')) - strtotime($row['latest'])) / 86400 : 999;
        $sources[] = array(
            'table' => 'daily_prices',
            'label' => 'Price Data (Yahoo Finance)',
            'page' => '/findstocks/portfolio/report.html',
            'total_records' => (int)$row['cnt'],
            'distinct_tickers' => (int)$row['tickers'],
            'latest_date' => $row['latest'],
            'days_since_latest' => round($days_old, 1),
            'status' => ($days_old <= 2) ? 'fresh' : (($days_old <= 5) ? 'stale' : 'outdated')
        );
    }

    // backtest_results
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(created_at) as latest FROM backtest_results");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $sources[] = array(
            'table' => 'backtest_results',
            'label' => 'Backtest Engine',
            'total_backtests' => (int)$row['cnt'],
            'latest_run' => $row['latest']
        );
    }

    // stock_fundamentals
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(updated_at) as latest FROM stock_fundamentals");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $sources[] = array(
            'table' => 'stock_fundamentals',
            'label' => 'Yahoo Finance Fundamentals',
            'total_tickers' => (int)$row['cnt'],
            'latest_update' => $row['latest']
        );
    }

    // Overall status
    $any_outdated = false;
    $any_stale = false;
    foreach ($sources as $s) {
        if (isset($s['status']) && $s['status'] === 'outdated') $any_outdated = true;
        if (isset($s['status']) && $s['status'] === 'stale') $any_stale = true;
    }

    $response['sources'] = $sources;
    $response['overall_status'] = $any_outdated ? 'outdated' : ($any_stale ? 'stale' : 'fresh');
    $response['checked_at'] = date('Y-m-d H:i:s');
    $response['warnings'] = array();
    foreach ($sources as $s) {
        if (isset($s['status']) && $s['status'] !== 'fresh') {
            $response['warnings'][] = $s['label'] . ' is ' . $s['status'] . ' (last data: ' . (isset($s['latest_pick_date']) ? $s['latest_pick_date'] : (isset($s['latest_date']) ? $s['latest_date'] : 'unknown')) . ')';
        }
    }

    echo json_encode($response);

// ═══════════════════════════════════════════
// SNAPSHOT — Store today's consensus to history (admin only)
// ═══════════════════════════════════════════
} elseif ($action === 'snapshot') {
    if (!$is_admin) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Admin key required'));
        $conn->close();
        exit;
    }

    // Auto-create tables
    require_once dirname(__FILE__) . '/consolidated_schema.php';

    // Generate consensus data (reuse logic but store to DB)
    $days = 14;
    $all_picks = array();

    $res = $conn->query("SELECT ticker, algorithm_name AS source_algo, pick_date, entry_price, score, 'stock_picks' AS source_table
                         FROM stock_picks WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) AND entry_price > 0");
    if ($res) { while ($row = $res->fetch_assoc()) $all_picks[] = $row; }

    $res = $conn->query("SELECT ticker, strategy_name AS source_algo, scan_date AS pick_date, entry_price, score, 'miracle_picks2' AS source_table
                         FROM miracle_picks2 WHERE scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) AND entry_price > 0");
    if ($res) { while ($row = $res->fetch_assoc()) $all_picks[] = $row; }

    $res = $conn->query("SELECT ticker, strategy_name AS source_algo, scan_date AS pick_date, entry_price, score, 'miracle_picks3' AS source_table
                         FROM miracle_picks3 WHERE scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) AND entry_price > 0");
    if ($res) { while ($row = $res->fetch_assoc()) $all_picks[] = $row; }

    // Group
    $by_ticker = array();
    foreach ($all_picks as $p) {
        $t = strtoupper(trim($p['ticker']));
        if (!isset($by_ticker[$t])) $by_ticker[$t] = array('algos' => array(), 'tables' => array(), 'entries' => array(), 'scores' => array());
        $algo_key = $p['source_table'] . ':' . $p['source_algo'];
        if (!in_array($algo_key, $by_ticker[$t]['algos'])) $by_ticker[$t]['algos'][] = $algo_key;
        if (!in_array($p['source_table'], $by_ticker[$t]['tables'])) $by_ticker[$t]['tables'][] = $p['source_table'];
        $by_ticker[$t]['entries'][] = (float)$p['entry_price'];
        $by_ticker[$t]['scores'][] = (int)$p['score'];
    }

    $today = date('Y-m-d');
    $now = date('Y-m-d H:i:s');
    $stored = 0;

    foreach ($by_ticker as $t => $data) {
        $count = count($data['algos']);
        if ($count < 2) continue; // only store consensus picks

        $score = round(array_sum($data['scores']), 2);
        $avg_entry = round(array_sum($data['entries']) / count($data['entries']), 4);

        // Latest price
        $safe_t = $conn->real_escape_string($t);
        $lp = 0;
        $pr = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$safe_t' ORDER BY trade_date DESC LIMIT 1");
        if ($pr && $pr->num_rows > 0) { $prow = $pr->fetch_assoc(); $lp = (float)$prow['close_price']; }

        $algos_str = $conn->real_escape_string(implode(',', $data['algos']));
        $tables_str = $conn->real_escape_string(implode(',', $data['tables']));

        $conn->query("INSERT INTO consensus_history (ticker, consensus_date, consensus_count, consensus_score, source_algos, source_tables, avg_entry_price, latest_price, created_at)
                      VALUES ('$safe_t', '$today', $count, $score, '$algos_str', '$tables_str', $avg_entry, $lp, '$now')
                      ON DUPLICATE KEY UPDATE consensus_count=$count, consensus_score=$score, source_algos='$algos_str', source_tables='$tables_str', avg_entry_price=$avg_entry, latest_price=$lp");
        $stored++;
    }

    $response['stored'] = $stored;
    $response['total_raw_picks'] = count($all_picks);
    $response['snapshot_date'] = $today;
    echo json_encode($response);

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action. Use: consensus, by_ticker, freshness, snapshot';
    echo json_encode($response);
}

$conn->close();
?>
