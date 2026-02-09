<?php
/**
 * Data listing endpoint for portfolio2 dashboard.
 * PHP 5.2 compatible.
 *
 * Types: picks, algorithms, portfolios, backtests, scenarios, stats, prices,
 *        algo_performance, trades
 */
require_once dirname(__FILE__) . '/db_connect.php';

$type = isset($_GET['type']) ? trim($_GET['type']) : 'stats';
$response = array('ok' => true, 'type' => $type);

if ($type === 'picks') {
    $algo_filter = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';
    $where = '';
    if ($algo_filter !== '') {
        $safe = $conn->real_escape_string($algo_filter);
        $where = " WHERE sp.algorithm_name = '$safe'";
    }
    $sql = "SELECT sp.*, s.company_name
            FROM stock_picks sp
            LEFT JOIN stocks s ON sp.ticker = s.ticker
            $where
            ORDER BY sp.score DESC, sp.pick_date DESC";
    $res = $conn->query($sql);
    $picks = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $picks[] = $row;
        }
    }
    $response['picks'] = $picks;
    $response['count'] = count($picks);

} elseif ($type === 'algorithms') {
    $sql = "SELECT a.*, COUNT(sp.id) as pick_count
            FROM algorithms a
            LEFT JOIN stock_picks sp ON a.name = sp.algorithm_name
            GROUP BY a.id
            ORDER BY a.family, a.name";
    $res = $conn->query($sql);
    $algos = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $algos[] = $row;
        }
    }
    $response['algorithms'] = $algos;

} elseif ($type === 'portfolios') {
    $sql = "SELECT * FROM portfolios ORDER BY strategy_type, name";
    $res = $conn->query($sql);
    $portfolios = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $portfolios[] = $row;
        }
    }
    $response['portfolios'] = $portfolios;

} elseif ($type === 'backtests') {
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;
    if ($limit < 1) $limit = 50;
    if ($limit > 200) $limit = 200;
    $sql = "SELECT * FROM backtest_results ORDER BY created_at DESC LIMIT $limit";
    $res = $conn->query($sql);
    $backtests = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $backtests[] = $row;
        }
    }
    $response['backtests'] = $backtests;

} elseif ($type === 'trades') {
    $bt_id = isset($_GET['backtest_id']) ? (int)$_GET['backtest_id'] : 0;
    if ($bt_id <= 0) {
        $response['ok'] = false;
        $response['error'] = 'backtest_id parameter required';
    } else {
        $sql = "SELECT * FROM backtest_trades WHERE backtest_id=$bt_id ORDER BY entry_date ASC";
        $res = $conn->query($sql);
        $trades = array();
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $trades[] = $row;
            }
        }
        $response['trades'] = $trades;
        $response['count'] = count($trades);
    }

} elseif ($type === 'scenarios') {
    $response['scenarios'] = array(
        array('key' => 'daytrader_eod',       'name' => 'Day Trader (EOD Exit)',      'tp' => 5,   'sl' => 3,  'hold' => 1,   'desc' => 'Buy at open, sell at close same day.'),
        array('key' => 'daytrader_2day',      'name' => 'Day Trader (2-Day Max)',     'tp' => 10,  'sl' => 5,  'hold' => 2,   'desc' => 'Buy in morning, sell within 2 days.'),
        array('key' => 'weekly_10',           'name' => 'Weekly Hold (10% Target)',   'tp' => 10,  'sl' => 5,  'hold' => 7,   'desc' => 'Hold up to 7 days, 10% profit target.'),
        array('key' => 'weekly_20',           'name' => 'Weekly Hold (20% Target)',   'tp' => 20,  'sl' => 8,  'hold' => 7,   'desc' => 'Hold up to 7 days, 20% profit target.'),
        array('key' => 'swing_conservative',  'name' => 'Conservative Swing',        'tp' => 10,  'sl' => 5,  'hold' => 20,  'desc' => 'Hold 2-4 weeks with tight stops.'),
        array('key' => 'swing_aggressive',    'name' => 'Aggressive Swing',          'tp' => 30,  'sl' => 15, 'hold' => 20,  'desc' => 'Hold 2-4 weeks with wide stops.'),
        array('key' => 'buy_hold_3m',         'name' => 'Buy & Hold (3 Months)',     'tp' => 999, 'sl' => 999,'hold' => 60,  'desc' => 'No TP/SL, hold 60 trading days.'),
        array('key' => 'buy_hold_6m',         'name' => 'Buy & Hold (6 Months)',     'tp' => 999, 'sl' => 999,'hold' => 126, 'desc' => 'No TP/SL, hold 126 trading days.'),
        array('key' => 'tight_scalp',         'name' => 'Tight Scalp',              'tp' => 3,   'sl' => 2,  'hold' => 1,   'desc' => 'Quick 3% target, 2% stop, 1 day.'),
        array('key' => 'momentum_ride',       'name' => 'Momentum Ride',            'tp' => 50,  'sl' => 10, 'hold' => 30,  'desc' => 'Let winners run. 50% target, 30 days.'),
        array('key' => 'questrade_cdr_weekly','name' => 'Questrade CDR Weekly',    'tp' => 10,  'sl' => 5,  'hold' => 7,   'desc' => 'CDR stocks, $0 commission, 7-day hold.'),
        array('key' => 'questrade_cdr_momentum','name'=>'Questrade CDR Momentum',  'tp' => 50,  'sl' => 10, 'hold' => 30,  'desc' => 'CDR stocks, $0 commission, ride momentum.'),
        array('key' => 'questrade_us_swing', 'name' => 'Questrade US (1.5% FX)',  'tp' => 10,  'sl' => 5,  'hold' => 7,   'desc' => 'US stocks, $0 comm but 1.5% FX conversion fee.'),
        array('key' => 'blue_chip_hold',     'name' => 'Blue Chip Hold (1 Year)',  'tp' => 999, 'sl' => 999,'hold' => 252, 'desc' => 'MCD/JNJ/WMT compounders, hold 1 year.'),
        array('key' => 'blue_chip_quarter',  'name' => 'Blue Chip Quarterly',     'tp' => 15,  'sl' => 8,  'hold' => 63,  'desc' => 'Blue chips, quarterly rebalance.'),
        array('key' => 'claude_genius_standard', 'name' => 'Claude Genius (Standard)',  'tp' => 20, 'sl' => 5,  'hold' => 14,  'desc' => 'AI meta-algo: multi-signal, $0 commission.'),
        array('key' => 'claude_genius_aggressive','name'=> 'Claude Genius (Aggressive)', 'tp' => 30, 'sl' => 8,  'hold' => 7,   'desc' => 'Aggressive AI: wider targets, faster exit.'),
        array('key' => 'claude_genius_patient',  'name' => 'Claude Genius (Patient)',   'tp' => 50, 'sl' => 10, 'hold' => 30,  'desc' => 'Patient AI: let winners run.'),
        array('key' => 'etf_buy_hold',           'name' => 'ETF Buy & Hold (1Y)',      'tp' => 999,'sl' => 999,'hold' => 252, 'desc' => 'Index ETFs, hold 1 year.'),
        array('key' => 'sector_rotation_monthly', 'name' => 'Sector Rotation Monthly', 'tp' => 15, 'sl' => 8,  'hold' => 30,  'desc' => 'Monthly sector rotation.'),
        // God-Mode Scenarios
        array('key' => 'god_mode_standard',     'name' => 'God-Mode Standard',         'tp' => 25, 'sl' => 8,  'hold' => 21,  'desc' => 'Meta-learner ensemble: regime-aware, Kelly-sized.'),
        array('key' => 'god_mode_aggressive',   'name' => 'God-Mode Aggressive',       'tp' => 40, 'sl' => 12, 'hold' => 30,  'desc' => 'Full alpha: 40% target, 12% stop.'),
        array('key' => 'god_mode_conservative', 'name' => 'God-Mode Conservative',     'tp' => 15, 'sl' => 5,  'hold' => 14,  'desc' => 'Quality + safety: 15% target, 5% stop.'),
        array('key' => 'earnings_drift_6w',     'name' => 'Earnings Drift (6 Week)',   'tp' => 25, 'sl' => 10, 'hold' => 42,  'desc' => 'PEAD: buy after earnings beat, ride 6-week drift.'),
        array('key' => 'safe_bet_annual',       'name' => 'Safe Bet (Annual)',         'tp' => 999,'sl' => 999,'hold' => 252, 'desc' => 'Dividend Aristocrats + Quality, hold 1 year.'),
        array('key' => 'safe_bet_quarterly',    'name' => 'Safe Bet (Quarterly)',      'tp' => 15, 'sl' => 8,  'hold' => 63,  'desc' => 'Quality compounders, quarterly rebalance.'),
        array('key' => 'flow_momentum',         'name' => 'Smart Money Flow',          'tp' => 20, 'sl' => 8,  'hold' => 14,  'desc' => 'Follow insider + dark pool signals.'),
        array('key' => 'factor_rank_monthly',   'name' => 'Factor Rank Monthly',       'tp' => 15, 'sl' => 8,  'hold' => 30,  'desc' => 'Cross-sectional top-K by composite factor rank.'),
        array('key' => 'mean_reversion_3d',     'name' => 'Mean Reversion (3-Day)',    'tp' => 8,  'sl' => 3,  'hold' => 3,   'desc' => 'Oversold bounce: z-score < -2, quick reversal.'),
        array('key' => 'regime_adaptive_swing', 'name' => 'Regime-Adaptive Swing',     'tp' => 20, 'sl' => 8,  'hold' => 21,  'desc' => 'Switches strategy by market regime.'),
        array('key' => 'kelly_optimal',         'name' => 'Kelly Criterion Optimal',   'tp' => 20, 'sl' => 8,  'hold' => 21,  'desc' => 'Mathematically optimal position sizing.'),
        array('key' => 'all_weather',           'name' => 'All-Weather Portfolio',     'tp' => 15, 'sl' => 10, 'hold' => 30,  'desc' => 'Long quality + short failures, any regime.'),
        // Alpha Forge Scenarios
        array('key' => 'alpha_forge_standard',  'name' => 'Alpha Forge Standard',      'tp' => 25, 'sl' => 8,  'hold' => 30,  'desc' => 'Ultimate multi-factor ensemble. Regime-weighted, Kelly-sized.'),
        array('key' => 'alpha_forge_aggressive', 'name'=> 'Alpha Forge Aggressive',    'tp' => 40, 'sl' => 12, 'hold' => 30,  'desc' => 'Full alpha generation. 40% target, 12% stop.'),
        array('key' => 'human_capital_hold',    'name' => 'Human Capital (6 Month)',   'tp' => 25, 'sl' => 10, 'hold' => 126, 'desc' => 'Employee satisfaction alpha. Georgetown study-backed.'),
        array('key' => 'esg_quality_annual',    'name' => 'ESG + Quality (Annual)',    'tp' => 999,'sl' => 999,'hold' => 252, 'desc' => 'ESG momentum + quality compounders, 1 year hold.'),
        array('key' => 'supply_chain_swing',    'name' => 'Supply Chain Swing',        'tp' => 20, 'sl' => 8,  'hold' => 30,  'desc' => 'BDI-driven cyclical trades. Monthly rebalance.'),
        array('key' => 'deep_flow_weekly',      'name' => 'Deep Flow (Weekly)',        'tp' => 20, 'sl' => 8,  'hold' => 14,  'desc' => 'Dark pool + congressional + squeeze signals.'),
        array('key' => 'innovation_growth_6m',  'name' => 'Innovation Growth (6M)',    'tp' => 30, 'sl' => 12, 'hold' => 126, 'desc' => 'Patent surge + network effects. Forward-looking growth.'),
        array('key' => 'three_sleeve_balanced', 'name' => 'Three-Sleeve Balanced',     'tp' => 20, 'sl' => 8,  'hold' => 30,  'desc' => 'Momentum 40% + Quality 40% + Event 20%.'),
        // Research-Backed Academic Scenarios
        array('key' => 'gross_profitability',   'name' => 'Gross Profitability (GP/A)', 'tp' => 20, 'sl' => 8,  'hold' => 60,  'desc' => 'Novy-Marx: buy high GP/A stocks, hold quarterly.'),
        array('key' => 'piotroski_fscore',      'name' => 'Piotroski F-Score',         'tp' => 25, 'sl' => 10, 'hold' => 126, 'desc' => '9-criteria quality scoring. Buy F>=7, hold 6 months.'),
        array('key' => 'bab_low_beta',          'name' => 'Betting Against Beta',      'tp' => 15, 'sl' => 8,  'hold' => 60,  'desc' => 'Long low-beta, leverage-adjusted. Quarterly hold.'),
        array('key' => 'qmj_quality',           'name' => 'Quality Minus Junk',        'tp' => 20, 'sl' => 8,  'hold' => 60,  'desc' => 'AQR QMJ: long quality, short junk. Quarterly.'),
        array('key' => 'shareholder_yield',     'name' => 'Shareholder Yield',         'tp' => 999,'sl' => 999,'hold' => 252, 'desc' => 'Dividend + buyback + debt paydown. Annual hold.'),
        array('key' => 'factor_momentum',       'name' => 'Factor Momentum',           'tp' => 15, 'sl' => 8,  'hold' => 30,  'desc' => 'Momentum on factors themselves. Monthly rebalance.'),
        array('key' => 'ts_momentum',           'name' => 'Time-Series Momentum',      'tp' => 20, 'sl' => 10, 'hold' => 30,  'desc' => 'Trend-following: long if 12mo return positive.'),
        array('key' => 'st_reversal',           'name' => 'Short-Term Reversal',       'tp' => 5,  'sl' => 2,  'hold' => 5,   'desc' => 'Oversold bounce: 1-5 day reversal plays.'),
        array('key' => 'lt_reversal',           'name' => 'Long-Term Reversal',        'tp' => 999,'sl' => 999,'hold' => 252, 'desc' => 'DeBondt-Thaler: 3-5yr losers outperform.'),
        array('key' => 'halloween_seasonal',    'name' => 'Halloween (Nov-Apr)',       'tp' => 20, 'sl' => 10, 'hold' => 126, 'desc' => 'Sell in May: only hold Nov through April.'),
        array('key' => 'merger_arb',            'name' => 'Merger Arbitrage',          'tp' => 8,  'sl' => 5,  'hold' => 60,  'desc' => 'Buy target post-announcement, capture spread.'),
        array('key' => 'spinoff_alpha',         'name' => 'Spin-Off Alpha',            'tp' => 30, 'sl' => 12, 'hold' => 252, 'desc' => 'Buy spin-offs, hold 1 year. 10%+ outperformance.'),
        array('key' => 'risk_parity',           'name' => 'Risk Parity',               'tp' => 999,'sl' => 999,'hold' => 60,  'desc' => 'Equal risk allocation. Quarterly rebalance.'),
        array('key' => 'trend_cta',             'name' => 'CTA Trend Following',      'tp' => 20, 'sl' => 10, 'hold' => 30,  'desc' => '10-month SMA crossover. Crisis alpha.'),
        array('key' => 'vol_risk_premium',      'name' => 'Volatility Risk Premium',  'tp' => 10, 'sl' => 8,  'hold' => 30,  'desc' => 'Sell implied vs realized vol. Consistent premium.'),
        array('key' => 'factor_zoo_full',       'name' => 'Factor Zoo Full',           'tp' => 20, 'sl' => 8,  'hold' => 30,  'desc' => 'All academic factors combined. Maximum diversification.'),
        array('key' => 'academic_allstar',      'name' => 'Academic All-Star',         'tp' => 25, 'sl' => 8,  'hold' => 30,  'desc' => 'Best of 50 yrs of research: GP/A+BAB+Piotroski+momentum.'),
        // No-Bed-Time Scenarios
        array('key' => 'nobed_standard',        'name' => 'No-Bed-Time Standard',      'tp' => 20, 'sl' => 5,  'hold' => 14,  'desc' => 'Dual consensus: only when top 2 algos agree. High conviction.'),
        array('key' => 'nobed_full_suite',      'name' => 'No-Bed-Time Full Suite',    'tp' => 25, 'sl' => 8,  'hold' => 14,  'desc' => 'All 5 NoBedTime variants. Never-sleeping meta-ensemble.'),
        array('key' => 'nobed_overnight',       'name' => 'No-Bed-Time Overnight',     'tp' => 5,  'sl' => 3,  'hold' => 1,   'desc' => 'Overnight premium: enter at close, exit at open.'),
        array('key' => 'nobed_contrarian',      'name' => 'No-Bed-Time Contrarian',    'tp' => 10, 'sl' => 5,  'hold' => 5,   'desc' => '3-8% dip bounce on quality names. Mean reversion.'),
        // ── Alt-Data Factor Scenarios ──
        array('key' => 'human_capital_6m',      'name' => 'Human Capital (6 Month)',    'tp' => 25, 'sl' => 10, 'hold' => 126, 'desc' => 'Glassdoor alpha: high culture + improving ratings. Georgetown study-backed.'),
        array('key' => 'culture_momentum_3m',   'name' => 'Culture Momentum (3M)',      'tp' => 15, 'sl' => 8,  'hold' => 60,  'desc' => 'Employee satisfaction trend. Culture shock events. Penalize downgrades.'),
        array('key' => 'esg_composite_annual',  'name' => 'ESG Composite (Annual)',     'tp' => 999,'sl' => 999,'hold' => 252, 'desc' => 'ESG + employee + low controversy. Quality compounders. 1 year hold.'),
        array('key' => 'climate_risk_filter',   'name' => 'Climate Risk Defensive',     'tp' => 15, 'sl' => 8,  'hold' => 60,  'desc' => 'Limit exposure to physically climate-exposed names. Seasonal stress.'),
        array('key' => 'bdi_cyclical_swing',    'name' => 'BDI Cyclical Swing',         'tp' => 20, 'sl' => 8,  'hold' => 30,  'desc' => 'Baltic Dry Index regime. Long cyclicals when BDI inflects up.'),
        array('key' => 'freight_bottleneck',    'name' => 'Freight Bottleneck',         'tp' => 15, 'sl' => 8,  'hold' => 30,  'desc' => 'Supply-tight vs slack flags. Freight rates + port congestion signals.'),
        array('key' => 'gpr_defensive',         'name' => 'GPR Defensive',              'tp' => 15, 'sl' => 5,  'hold' => 30,  'desc' => 'High geopolitical risk: overweight quality/defensive. Low GPR: ride momentum.'),
        array('key' => 'sanctions_avoidance',   'name' => 'Sanctions Avoidance',        'tp' => 10, 'sl' => 5,  'hold' => 14,  'desc' => 'Avoid/underweight firms with high revenue in sanctioned regions.'),
        array('key' => 'dark_pool_flow',        'name' => 'Dark Pool Flow',             'tp' => 20, 'sl' => 8,  'hold' => 14,  'desc' => 'Dark pool volume spikes + block clustering. Institutional footprints.'),
        array('key' => 'congressional_short',   'name' => 'Congressional Shorts',       'tp' => 15, 'sl' => 5,  'hold' => 15,  'desc' => 'Harvard study: negative Congressional trades earn abnormal returns. 10-15d window.'),
        array('key' => 'insider_cluster_buy',   'name' => 'Insider Cluster Buy',        'tp' => 20, 'sl' => 8,  'hold' => 30,  'desc' => 'Multiple Form 4 insider buys within 2 weeks. Strongest insider signal.'),
        array('key' => 'patent_surge_6m',       'name' => 'Patent Surge (6M)',          'tp' => 30, 'sl' => 12, 'hold' => 126, 'desc' => 'Patent count growth + citation-weighted. New CPC class entries. Innovation alpha.'),
        array('key' => 'innovation_compounder', 'name' => 'Innovation Compounder (1Y)', 'tp' => 999,'sl' => 999,'hold' => 252, 'desc' => 'Consistent patent output + quality fundamentals. Long-term compounders.'),
        array('key' => 'alpha_forge_ultimate',  'name' => 'Alpha Forge Ultimate',       'tp' => 25, 'sl' => 8,  'hold' => 30,  'desc' => 'All 7 factor families combined. Regime-weighted, Kelly-sized ensemble.'),
        array('key' => 'quality_compounder',    'name' => 'Quality Compounder (1Y)',    'tp' => 999,'sl' => 999,'hold' => 252, 'desc' => 'Glassdoor + ESG + Patents + Piotroski. Ultimate quality filter.'),
        array('key' => 'macro_regime_switch',   'name' => 'Macro Regime Switcher',      'tp' => 20, 'sl' => 8,  'hold' => 30,  'desc' => 'VIX + BDI + GPR + DXY + yield curve unified regime model.'),
        array('key' => 'full_factor_alt',       'name' => 'Full Factor + Alt Data',     'tp' => 20, 'sl' => 8,  'hold' => 30,  'desc' => 'Academic factors + all alt-data families. Maximum factor diversification.')
    );

} elseif ($type === 'prices') {
    $ticker = isset($_GET['ticker']) ? trim($_GET['ticker']) : '';
    if ($ticker === '') {
        $response['ok'] = false;
        $response['error'] = 'ticker parameter required';
    } else {
        $safe = $conn->real_escape_string(strtoupper($ticker));
        $sql = "SELECT trade_date, open_price, high_price, low_price, close_price, volume
                FROM daily_prices WHERE ticker='$safe' ORDER BY trade_date ASC";
        $res = $conn->query($sql);
        $prices = array();
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $prices[] = $row;
            }
        }
        $response['ticker'] = strtoupper($ticker);
        $response['prices'] = $prices;
        $response['count'] = count($prices);
    }

} elseif ($type === 'algo_performance') {
    $sql = "SELECT * FROM algorithm_performance ORDER BY win_rate DESC";
    $res = $conn->query($sql);
    $perfs = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $perfs[] = $row;
        }
    }
    $response['performance'] = $perfs;

} elseif ($type === 'stats') {
    $stats = array();

    $res = $conn->query("SELECT COUNT(*) as c FROM stocks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_stocks'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM stock_picks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_picks'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM daily_prices");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_price_records'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM backtest_results");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_backtests'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(DISTINCT algorithm_name) as c FROM stock_picks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['active_algorithms'] = (int)$row['c'];

    $res = $conn->query("SELECT MIN(pick_date) as mn, MAX(pick_date) as mx FROM stock_picks");
    if ($res) {
        $row = $res->fetch_assoc();
        $stats['pick_date_range'] = array('earliest' => $row['mn'], 'latest' => $row['mx']);
    }

    $res = $conn->query("SELECT MIN(trade_date) as mn, MAX(trade_date) as mx FROM daily_prices");
    if ($res) {
        $row = $res->fetch_assoc();
        $stats['price_date_range'] = array('earliest' => $row['mn'], 'latest' => $row['mx']);
    }

    $algo_breakdown = array();
    $res = $conn->query("SELECT algorithm_name, COUNT(*) as cnt, AVG(score) as avg_score
                         FROM stock_picks GROUP BY algorithm_name ORDER BY cnt DESC");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $algo_breakdown[] = $row;
        }
    }
    $stats['algorithm_breakdown'] = $algo_breakdown;

    $response['stats'] = $stats;

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown type. Use: picks, algorithms, portfolios, backtests, scenarios, stats, prices, algo_performance, trades';
}

echo json_encode($response);
$conn->close();
?>
