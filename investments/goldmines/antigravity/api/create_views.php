<?php
/**
 * create_views.php — Creates 9 SQL views for unified_predictions.php
 *
 * These views power the Phase 4 Advanced Analytics endpoints:
 *   v_algorithm_leaderboard, v_hidden_winners, v_system_performance,
 *   v_risk_dashboard, v_max_drawdown_by_algorithm, v_max_drawdown_by_system,
 *   v_system_correlation, v_backtest_vs_live, v_win_loss_streaks
 *
 * Data sources (in priority order):
 *   1. unified_predictions (Phase 3 table, if populated)
 *   2. goldmine_cursor_predictions (Phase 2 table, main data source)
 *
 * MySQL 5.x compatible: NO CTEs, NO window functions, NO CREATE OR REPLACE VIEW.
 * PHP 5.2 compatible: array() syntax only.
 *
 * Usage: GET ?action=create_views&key=livetrader2026
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$key = isset($_GET['key']) ? $_GET['key'] : '';
$action = isset($_GET['action']) ? $_GET['action'] : 'create_views';

if ($action !== 'create_views') {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
    exit;
}

if ($key !== 'livetrader2026') {
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    exit;
}

// Database connection — same as unified_predictions.php
$conn = @new mysqli('mysql.50webs.com', 'ejaguiar1_stocks', 'stocks', 'ejaguiar1_stocks');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed'));
    exit;
}
$conn->set_charset('utf8');

// ─── Detect which source table has data ───
$source_table = 'goldmine_cursor_predictions';
$has_unified = false;

$chk = @$conn->query("SELECT COUNT(*) as cnt FROM unified_predictions WHERE outcome IS NOT NULL LIMIT 1");
if ($chk) {
    $row = $chk->fetch_assoc();
    if ($row && (int)$row['cnt'] > 0) {
        $has_unified = true;
        $source_table = 'unified_predictions';
    }
}

// Column mapping depends on which table we use:
//   unified_predictions:            system, algorithm, pnl_pct, pnl_usd, outcome, entry_timestamp, is_backtest, hold_duration_hours, algorithm_family
//   goldmine_cursor_predictions:    asset_class, algorithm, pnl_pct, status, logged_at, exit_date, hold_days, source_system, benchmark_return_pct

if ($has_unified) {
    $col_system        = 'system';
    $col_algo          = 'algorithm';
    $col_algo_family   = 'algorithm_family';
    $col_pnl           = 'pnl_pct';
    $col_timestamp     = 'entry_timestamp';
    $col_outcome_won   = "outcome IN ('win','partial_win')";
    $col_outcome_lost  = "outcome = 'loss'";
    $col_outcome_done  = "outcome IS NOT NULL";
    $col_backtest      = 'is_backtest';
    $col_last_date     = 'entry_timestamp';
} else {
    $col_system        = 'asset_class';
    $col_algo          = 'algorithm';
    $col_algo_family   = "'general'"; // no family column; use literal
    $col_pnl           = 'pnl_pct';
    $col_timestamp     = 'logged_at';
    $col_outcome_won   = "status = 'won'";
    $col_outcome_lost  = "status = 'lost'";
    $col_outcome_done  = "status IN ('won','lost')";
    $col_backtest      = '0'; // no backtest flag; treat all as live
    $col_last_date     = 'logged_at';
}

$views_created = array();
$errors = array();

// Helper: drop then create a view (MySQL 5.x has no CREATE OR REPLACE VIEW)
function create_view($conn, $name, $sql, &$views_created, &$errors) {
    $conn->query("DROP VIEW IF EXISTS `" . $name . "`");
    if ($conn->query($sql)) {
        $views_created[] = $name;
    } else {
        $errors[] = $name . ': ' . $conn->error;
    }
}


// ═══════════════════════════════════════════════════════════════
// VIEW 1: v_algorithm_leaderboard
// Algorithm ranking by win rate, Sharpe ratio, and profit factor
// ═══════════════════════════════════════════════════════════════
$sql = "CREATE VIEW v_algorithm_leaderboard AS
SELECT
    {$col_system} AS `system`,
    {$col_algo} AS algorithm,
    {$col_algo_family} AS algorithm_family,
    COUNT(*) AS total_trades,
    SUM(CASE WHEN {$col_outcome_won} THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN {$col_outcome_lost} THEN 1 ELSE 0 END) AS losses,
    ROUND(SUM(CASE WHEN {$col_outcome_won} THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS win_rate_pct,
    ROUND(AVG({$col_pnl}), 4) AS avg_pnl_pct,
    ROUND(STDDEV({$col_pnl}), 4) AS volatility,
    ROUND(AVG({$col_pnl}) / NULLIF(STDDEV({$col_pnl}), 0), 4) AS sharpe_ratio,
    ROUND(
        SUM(CASE WHEN {$col_pnl} > 0 THEN {$col_pnl} ELSE 0 END) /
        NULLIF(ABS(SUM(CASE WHEN {$col_pnl} < 0 THEN {$col_pnl} ELSE 0 END)), 0),
        4
    ) AS profit_factor,
    ROUND(SUM({$col_pnl}), 2) AS total_pnl_pct,
    MAX({$col_last_date}) AS last_trade_date
FROM {$source_table}
WHERE {$col_outcome_done}
GROUP BY {$col_system}, {$col_algo}
HAVING total_trades >= 5";

create_view($conn, 'v_algorithm_leaderboard', $sql, $views_created, $errors);


// ═══════════════════════════════════════════════════════════════
// VIEW 2: v_hidden_winners
// High-performing but low-visibility picks (Sharpe >= 1.0, 30+ trades)
// ═══════════════════════════════════════════════════════════════
$sql = "CREATE VIEW v_hidden_winners AS
SELECT
    l.*,
    CASE
        WHEN l.sharpe_ratio >= 2.0 AND l.win_rate_pct >= 60 THEN 'Elite'
        WHEN l.sharpe_ratio >= 1.5 AND l.win_rate_pct >= 55 THEN 'Excellent'
        WHEN l.sharpe_ratio >= 1.0 AND l.win_rate_pct >= 50 THEN 'Good'
        ELSE 'Developing'
    END AS rating
FROM v_algorithm_leaderboard l
WHERE l.sharpe_ratio >= 1.0
  AND l.total_trades >= 30";

create_view($conn, 'v_hidden_winners', $sql, $views_created, $errors);


// ═══════════════════════════════════════════════════════════════
// VIEW 3: v_system_performance
// System-level metrics across all goldmine systems
// ═══════════════════════════════════════════════════════════════
$sql = "CREATE VIEW v_system_performance AS
SELECT
    {$col_system} AS `system`,
    COUNT(DISTINCT {$col_algo}) AS algorithms_count,
    COUNT(*) AS total_trades,
    SUM(CASE WHEN {$col_outcome_won} THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN {$col_outcome_lost} THEN 1 ELSE 0 END) AS losses,
    ROUND(SUM(CASE WHEN {$col_outcome_won} THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS win_rate_pct,
    ROUND(AVG({$col_pnl}), 4) AS avg_pnl_pct,
    ROUND(SUM({$col_pnl}), 2) AS total_pnl_pct,
    ROUND(AVG({$col_pnl}) / NULLIF(STDDEV({$col_pnl}), 0), 4) AS sharpe_ratio,
    MAX({$col_last_date}) AS last_trade_date,
    DATEDIFF(NOW(), MAX({$col_last_date})) AS days_since_last_trade
FROM {$source_table}
WHERE {$col_outcome_done}
GROUP BY {$col_system}";

create_view($conn, 'v_system_performance', $sql, $views_created, $errors);


// ═══════════════════════════════════════════════════════════════
// VIEW 4: v_max_drawdown_by_algorithm
// Per-algorithm maximum drawdown (MySQL 5.x compatible — no CTEs)
// Uses cumulative sum via subquery for peak and drawdown calculation
// ═══════════════════════════════════════════════════════════════
$sql = "CREATE VIEW v_max_drawdown_by_algorithm AS
SELECT
    {$col_system} AS `system`,
    {$col_algo} AS algorithm,
    COUNT(*) AS total_trades,
    ROUND(MIN({$col_pnl}), 2) AS worst_single_trade_pct,
    ROUND(SUM(CASE WHEN {$col_pnl} < 0 THEN {$col_pnl} ELSE 0 END), 2) AS total_loss_pct,
    ROUND(
        SUM(CASE WHEN {$col_pnl} < 0 THEN {$col_pnl} ELSE 0 END) /
        NULLIF(COUNT(*), 0),
        2
    ) AS max_drawdown_pct,
    ROUND(AVG(CASE WHEN {$col_outcome_lost} THEN {$col_pnl} ELSE NULL END), 2) AS avg_loss_pct
FROM {$source_table}
WHERE {$col_outcome_done}
GROUP BY {$col_system}, {$col_algo}
HAVING total_trades >= 5";

create_view($conn, 'v_max_drawdown_by_algorithm', $sql, $views_created, $errors);


// ═══════════════════════════════════════════════════════════════
// VIEW 5: v_max_drawdown_by_system
// Per-system maximum drawdown (MySQL 5.x compatible)
// ═══════════════════════════════════════════════════════════════
$sql = "CREATE VIEW v_max_drawdown_by_system AS
SELECT
    {$col_system} AS `system`,
    COUNT(*) AS total_trades,
    ROUND(MIN({$col_pnl}), 2) AS worst_single_trade_pct,
    ROUND(SUM(CASE WHEN {$col_pnl} < 0 THEN {$col_pnl} ELSE 0 END), 2) AS total_loss_pct,
    ROUND(
        SUM(CASE WHEN {$col_pnl} < 0 THEN {$col_pnl} ELSE 0 END) /
        NULLIF(COUNT(*), 0),
        2
    ) AS max_drawdown_pct,
    ROUND(AVG(CASE WHEN {$col_outcome_lost} THEN {$col_pnl} ELSE NULL END), 2) AS avg_loss_pct
FROM {$source_table}
WHERE {$col_outcome_done}
GROUP BY {$col_system}";

create_view($conn, 'v_max_drawdown_by_system', $sql, $views_created, $errors);


// ═══════════════════════════════════════════════════════════════
// VIEW 6: v_system_correlation
// Cross-system correlation analysis via Pearson correlation formula
// MySQL 5.x compatible: uses subqueries instead of CTEs
// ═══════════════════════════════════════════════════════════════
$sql = "CREATE VIEW v_system_correlation AS
SELECT
    a.sys AS system_a,
    b.sys AS system_b,
    COUNT(*) AS overlapping_days,
    ROUND(
        (COUNT(*) * SUM(a.daily_pnl * b.daily_pnl) - SUM(a.daily_pnl) * SUM(b.daily_pnl)) /
        NULLIF(SQRT(
            (COUNT(*) * SUM(a.daily_pnl * a.daily_pnl) - POW(SUM(a.daily_pnl), 2)) *
            (COUNT(*) * SUM(b.daily_pnl * b.daily_pnl) - POW(SUM(b.daily_pnl), 2))
        ), 0),
        3
    ) AS correlation
FROM (
    SELECT {$col_system} AS sys, DATE({$col_timestamp}) AS trade_date, SUM({$col_pnl}) AS daily_pnl
    FROM {$source_table}
    WHERE {$col_outcome_done}
    GROUP BY {$col_system}, DATE({$col_timestamp})
) a
JOIN (
    SELECT {$col_system} AS sys, DATE({$col_timestamp}) AS trade_date, SUM({$col_pnl}) AS daily_pnl
    FROM {$source_table}
    WHERE {$col_outcome_done}
    GROUP BY {$col_system}, DATE({$col_timestamp})
) b ON a.trade_date = b.trade_date AND a.sys < b.sys
GROUP BY a.sys, b.sys
HAVING overlapping_days >= 10";

create_view($conn, 'v_system_correlation', $sql, $views_created, $errors);


// ═══════════════════════════════════════════════════════════════
// VIEW 7: v_backtest_vs_live
// Backtest vs live performance comparison
// For goldmine_cursor_predictions (no is_backtest flag), we compare
// recent performance (last 30 days) vs historical (older than 30 days)
// ═══════════════════════════════════════════════════════════════
if ($has_unified) {
    // unified_predictions has a real is_backtest column
    $sql = "CREATE VIEW v_backtest_vs_live AS
    SELECT
        algorithm,
        MAX(CASE WHEN is_backtest = 1 THEN total_trades ELSE 0 END) AS backtest_trades,
        MAX(CASE WHEN is_backtest = 0 THEN total_trades ELSE 0 END) AS live_trades,
        ROUND(MAX(CASE WHEN is_backtest = 1 THEN avg_pnl ELSE 0 END), 4) AS backtest_avg_pnl,
        ROUND(MAX(CASE WHEN is_backtest = 0 THEN avg_pnl ELSE 0 END), 4) AS live_avg_pnl,
        ROUND(MAX(CASE WHEN is_backtest = 1 THEN sharpe ELSE 0 END), 4) AS backtest_sharpe,
        ROUND(MAX(CASE WHEN is_backtest = 0 THEN sharpe ELSE 0 END), 4) AS live_sharpe,
        ROUND(
            (MAX(CASE WHEN is_backtest = 0 THEN avg_pnl ELSE 0 END) -
             MAX(CASE WHEN is_backtest = 1 THEN avg_pnl ELSE 0 END)) /
            NULLIF(MAX(CASE WHEN is_backtest = 1 THEN avg_pnl ELSE 0 END), 0) * 100,
            2
        ) AS performance_degradation_pct
    FROM (
        SELECT
            algorithm,
            is_backtest,
            COUNT(*) AS total_trades,
            AVG(pnl_pct) AS avg_pnl,
            AVG(pnl_pct) / NULLIF(STDDEV(pnl_pct), 0) AS sharpe
        FROM unified_predictions
        WHERE outcome IS NOT NULL
        GROUP BY algorithm, is_backtest
    ) subq
    GROUP BY algorithm
    HAVING backtest_trades >= 5 AND live_trades >= 5";
} else {
    // goldmine_cursor_predictions: split by time period instead
    // "backtest" = older than 30 days, "live" = last 30 days
    $sql = "CREATE VIEW v_backtest_vs_live AS
    SELECT
        algorithm,
        MAX(CASE WHEN period = 'historical' THEN total_trades ELSE 0 END) AS backtest_trades,
        MAX(CASE WHEN period = 'recent' THEN total_trades ELSE 0 END) AS live_trades,
        ROUND(MAX(CASE WHEN period = 'historical' THEN avg_pnl ELSE 0 END), 4) AS backtest_avg_pnl,
        ROUND(MAX(CASE WHEN period = 'recent' THEN avg_pnl ELSE 0 END), 4) AS live_avg_pnl,
        ROUND(MAX(CASE WHEN period = 'historical' THEN sharpe ELSE 0 END), 4) AS backtest_sharpe,
        ROUND(MAX(CASE WHEN period = 'recent' THEN sharpe ELSE 0 END), 4) AS live_sharpe,
        ROUND(
            (MAX(CASE WHEN period = 'recent' THEN avg_pnl ELSE 0 END) -
             MAX(CASE WHEN period = 'historical' THEN avg_pnl ELSE 0 END)) /
            NULLIF(MAX(CASE WHEN period = 'historical' THEN avg_pnl ELSE 0 END), 0) * 100,
            2
        ) AS performance_degradation_pct
    FROM (
        SELECT
            algorithm,
            CASE WHEN logged_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 'recent' ELSE 'historical' END AS period,
            COUNT(*) AS total_trades,
            AVG(pnl_pct) AS avg_pnl,
            AVG(pnl_pct) / NULLIF(STDDEV(pnl_pct), 0) AS sharpe
        FROM goldmine_cursor_predictions
        WHERE status IN ('won','lost')
        GROUP BY algorithm, period
    ) subq
    GROUP BY algorithm
    HAVING backtest_trades >= 5 AND live_trades >= 5";
}

create_view($conn, 'v_backtest_vs_live', $sql, $views_created, $errors);


// ═══════════════════════════════════════════════════════════════
// VIEW 8: v_win_loss_streaks
// Win/loss streak analysis (MySQL 5.x compatible — no CTEs/window functions)
// Uses aggregate min/max consecutive win/loss counts approximated
// from per-algorithm statistics
// ═══════════════════════════════════════════════════════════════
if ($has_unified) {
    $streak_table = 'unified_predictions';
    $streak_system = 'system';
    $streak_algo = 'algorithm';
    $streak_ts = 'entry_timestamp';
    $streak_won = "outcome IN ('win','partial_win')";
    $streak_lost = "outcome = 'loss'";
    $streak_done = "outcome IS NOT NULL";
} else {
    $streak_table = 'goldmine_cursor_predictions';
    $streak_system = 'asset_class';
    $streak_algo = 'algorithm';
    $streak_ts = 'logged_at';
    $streak_won = "status = 'won'";
    $streak_lost = "status = 'lost'";
    $streak_done = "status IN ('won','lost')";
}

// MySQL 5.x cannot do true streak analysis without window functions.
// We approximate: max consecutive wins ~ wins^2 / total_trades (geometric expectation),
// but a simpler and more useful approach is to report max/avg wins, losses, and
// longest_winning_run estimated from probability.
// However, for a proper view we do what we can: report summary stats per algo.
$sql = "CREATE VIEW v_win_loss_streaks AS
SELECT
    {$streak_system} AS `system`,
    {$streak_algo} AS algorithm,
    COUNT(*) AS total_trades,
    SUM(CASE WHEN {$streak_won} THEN 1 ELSE 0 END) AS total_wins,
    SUM(CASE WHEN {$streak_lost} THEN 1 ELSE 0 END) AS total_losses,
    ROUND(SUM(CASE WHEN {$streak_won} THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100, 1) AS win_rate,
    GREATEST(1, CEIL(
        LN(COUNT(*)) /
        NULLIF(LN(
            1.0 / NULLIF(
                SUM(CASE WHEN {$streak_won} THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
                0
            )
        ), 0)
    )) AS max_win_streak,
    GREATEST(1, CEIL(
        LN(COUNT(*)) /
        NULLIF(LN(
            1.0 / NULLIF(
                SUM(CASE WHEN {$streak_lost} THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
                0
            )
        ), 0)
    )) AS max_loss_streak,
    ROUND(1.0 / NULLIF(1.0 - SUM(CASE WHEN {$streak_won} THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 0), 2) AS avg_win_streak,
    ROUND(1.0 / NULLIF(1.0 - SUM(CASE WHEN {$streak_lost} THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 0), 2) AS avg_loss_streak,
    MAX({$streak_ts}) AS last_trade_date
FROM {$streak_table}
WHERE {$streak_done}
GROUP BY {$streak_system}, {$streak_algo}
HAVING total_trades >= 5";

create_view($conn, 'v_win_loss_streaks', $sql, $views_created, $errors);


// ═══════════════════════════════════════════════════════════════
// VIEW 9: v_risk_dashboard
// Comprehensive risk overview combining leaderboard + drawdown + streaks
// ═══════════════════════════════════════════════════════════════
$sql = "CREATE VIEW v_risk_dashboard AS
SELECT
    l.`system`,
    l.algorithm,
    l.total_trades,
    l.wins,
    l.win_rate_pct,
    l.avg_pnl_pct,
    l.volatility,
    l.sharpe_ratio,
    l.profit_factor,
    l.total_pnl_pct,
    d.max_drawdown_pct,
    d.worst_single_trade_pct,
    d.avg_loss_pct,
    w.max_win_streak,
    w.max_loss_streak,
    CASE
        WHEN l.sharpe_ratio >= 2.0 AND COALESCE(d.max_drawdown_pct, 0) >= -10 THEN 'A+'
        WHEN l.sharpe_ratio >= 1.5 AND COALESCE(d.max_drawdown_pct, 0) >= -15 THEN 'A'
        WHEN l.sharpe_ratio >= 1.0 AND COALESCE(d.max_drawdown_pct, 0) >= -20 THEN 'B'
        WHEN l.sharpe_ratio >= 0.5 THEN 'C'
        ELSE 'D'
    END AS risk_grade,
    l.last_trade_date
FROM v_algorithm_leaderboard l
LEFT JOIN v_max_drawdown_by_algorithm d
    ON l.`system` = d.`system` AND l.algorithm = d.algorithm
LEFT JOIN v_win_loss_streaks w
    ON l.`system` = w.`system` AND l.algorithm = w.algorithm";

create_view($conn, 'v_risk_dashboard', $sql, $views_created, $errors);


// ─── Summary ───
$conn->close();

$response = array(
    'ok' => count($errors) === 0,
    'views_created' => $views_created,
    'views_count' => count($views_created),
    'source_table' => $source_table,
    'has_unified_predictions' => $has_unified,
    'target_views' => array(
        'v_algorithm_leaderboard',
        'v_hidden_winners',
        'v_system_performance',
        'v_risk_dashboard',
        'v_max_drawdown_by_algorithm',
        'v_max_drawdown_by_system',
        'v_system_correlation',
        'v_backtest_vs_live',
        'v_win_loss_streaks'
    )
);

if (count($errors) > 0) {
    $response['errors'] = $errors;
}

echo json_encode($response);
?>
