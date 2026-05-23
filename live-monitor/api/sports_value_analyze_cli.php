<?php
/**
 * sports_value_analyze_cli.php
 *
 * CLI wrapper around sports_value_analyze_run() for backtesting. Drives the
 * production devig + EV math against historical odds with a time-traveled
 * "as of" instant, writing synthetic picks to lm_sports_synthetic_bets.
 *
 * Production zero-touch contract:
 *   - Reads from lm_sports_odds_historical (NOT lm_sports_odds).
 *   - Writes to lm_sports_synthetic_bets (NOT lm_sports_value_bets).
 *   - Skips the expiry sweep entirely.
 *   - Devig + EV + Kelly math is unchanged (single source of truth in
 *     sports_value_analyze_lib.php). This wrapper just passes overrides.
 *
 * Invoked by: live-monitor/sportsbetting_lib/backtest_runner.py
 *
 * Usage:
 *   php sports_value_analyze_cli.php \
 *       --as-of "2024-03-15 18:00:00" \
 *       --run-id "bt_20260425_a1b2" \
 *       --sport "basketball_nba" \
 *       --bankroll 1000 \
 *       --min-ev 1.5
 *
 * Exit codes: 0 ok, 2 bad args, 3 db error.
 *
 * PHP 5.2 compatible (matches the rest of the api/ tree).
 */

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    echo "CLI only\n";
    exit(3);
}

require_once dirname(__FILE__) . '/db_config.php';
require_once dirname(__FILE__) . '/sports_value_analyze_lib.php';

function cli_args($argv) {
    $out = array();
    $n = count($argv);
    for ($i = 1; $i < $n; $i++) {
        $a = $argv[$i];
        if (substr($a, 0, 2) !== '--') {
            continue;
        }
        $key = substr($a, 2);
        $val = '';
        if (strpos($key, '=') !== false) {
            $parts = explode('=', $key, 2);
            $key = $parts[0];
            $val = $parts[1];
        } else if (($i + 1) < $n && substr($argv[$i + 1], 0, 2) !== '--') {
            $val = $argv[$i + 1];
            $i++;
        } else {
            $val = '1';
        }
        $out[$key] = $val;
    }
    return $out;
}

$args = cli_args($argv);

$asOf      = isset($args['as-of'])     ? trim($args['as-of'])     : '';
$runId     = isset($args['run-id'])    ? trim($args['run-id'])    : '';
$sport     = isset($args['sport'])     ? trim($args['sport'])     : '';
$bankroll  = isset($args['bankroll'])  ? floatval($args['bankroll']) : 1000.0;
$minEv     = isset($args['min-ev'])    ? floatval($args['min-ev'])   : 1.5;
$oddsTbl   = isset($args['odds-table']) ? trim($args['odds-table'])  : 'lm_sports_odds_historical';
$betsTbl   = isset($args['bets-table']) ? trim($args['bets-table'])  : 'lm_sports_synthetic_bets';

if ($asOf === '' || $runId === '') {
    fwrite(STDERR, "ERROR: --as-of and --run-id are required\n");
    fwrite(STDERR, "Usage: php sports_value_analyze_cli.php --as-of 'YYYY-MM-DD HH:MM:SS' --run-id <id> [--sport <key>] [--bankroll N] [--min-ev N]\n");
    exit(2);
}

// Loose ISO timestamp validation: lets the analyzer's escape_string be the
// last line of defense; we just want an obviously-malformed string rejected.
if (!preg_match('/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$/', $asOf)) {
    fwrite(STDERR, "ERROR: --as-of must look like 'YYYY-MM-DD HH:MM:SS'\n");
    exit(2);
}
$asOf = str_replace('T', ' ', $asOf);
if (strlen($asOf) === 16) {
    $asOf .= ':00';
}

$server = isset($sports_servername) ? $sports_servername : 'localhost';
$user   = isset($sports_username)   ? $sports_username   : 'root';
$pass   = isset($sports_password)   ? $sports_password   : '';
$db     = isset($sports_dbname)     ? $sports_dbname     : 'ejaguiar1_sportsbet';

$mysqli = @new mysqli($server, $user, $pass, $db);
if ($mysqli->connect_error) {
    fwrite(STDERR, "ERROR: db connect: " . $mysqli->connect_error . "\n");
    exit(3);
}
$mysqli->set_charset('utf8');

// Extra columns appended to the INSERT so synthetic rows carry their backtest
// metadata. is_synthetic=1 is redundant (the column defaults to 1) but explicit.
$asOfEsc = $mysqli->real_escape_string($asOf);
$runEsc  = $mysqli->real_escape_string($runId);
$extraCols = ", as_of, is_synthetic, backtest_run_id";
$extraVals = ",'" . $asOfEsc . "',1,'" . $runEsc . "'";

$result = sports_value_analyze_run(
    $mysqli,
    $bankroll,
    $minEv,
    $sport,
    $asOf,
    $oddsTbl,
    $betsTbl,
    $extraCols,
    $extraVals
);

$result['as_of']           = $asOf;
$result['run_id']          = $runId;
$result['sport_filter']    = $sport;
$result['odds_table']      = $oddsTbl;
$result['bets_table']      = $betsTbl;

$mysqli->close();

echo json_encode($result) . "\n";
exit(0);
