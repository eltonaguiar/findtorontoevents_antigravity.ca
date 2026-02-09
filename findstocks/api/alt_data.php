<?php
/**
 * Alternative Data Factor Framework API
 * Provides factor scores, data sources, and feature definitions for
 * the 7 alternative data factor families.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET ?action=factors           - List all factor families and features
 *   GET ?action=factor_scores     - Get composite factor scores per ticker
 *   GET ?action=regime_signals    - Current regime signals (BDI, GPR, VIX, etc.)
 *   GET ?action=data_sources      - List external data source endpoints
 *   GET ?action=ticker_factors&ticker=AAPL - Factor profile for a single ticker
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'factors';
$response = array('ok' => true, 'action' => $action);

if ($action === 'factors') {
    // ── All 7 factor families with features and data sources ──
    $response['factor_families'] = array(
        array(
            'id' => 'human_capital',
            'name' => 'Human Capital & Culture',
            'description' => 'Employee satisfaction, culture quality, and leadership sentiment. Georgetown study: high+improving ratings earn significant four-factor alpha.',
            'source_refs' => array('Glassdoor', 'Indeed', 'Comparably'),
            'update_cadence' => 'monthly',
            'features' => array(
                array('name' => 'glassdoor_overall', 'type' => 'level', 'range' => '1.0-5.0', 'description' => 'Current Glassdoor overall rating'),
                array('name' => 'culture_values_score', 'type' => 'level', 'range' => '1.0-5.0', 'description' => 'Culture & Values sub-score'),
                array('name' => 'senior_leadership_score', 'type' => 'level', 'range' => '1.0-5.0', 'description' => 'Senior Leadership sub-score'),
                array('name' => 'rating_6mo_change', 'type' => 'trend', 'range' => '-2.0 to +2.0', 'description' => '6-month change in overall rating'),
                array('name' => 'rating_12mo_change', 'type' => 'trend', 'range' => '-2.0 to +2.0', 'description' => '12-month change in overall rating'),
                array('name' => 'culture_shock', 'type' => 'event', 'range' => 'boolean', 'description' => 'Large rating move (>0.5 in 3 months)'),
                array('name' => 'human_capital_composite', 'type' => 'composite', 'range' => '0-100', 'description' => 'Weighted composite of all sub-scores + trends')
            ),
            'algorithms' => array('Human Capital Alpha', 'Culture Momentum', 'Human Capital Quality'),
            'regime_use' => 'Quality Compounder sleeve: require minimum rating + positive trend. Penalty for culture downgrades on momentum positions >1-3 months.'
        ),
        array(
            'id' => 'supply_chain',
            'name' => 'Supply Chain & Trade Bottleneck',
            'description' => 'Baltic Dry Index, freight rates, port congestion. BDI captures global bulk shipping demand and is a leading indicator of global trade.',
            'source_refs' => array('Baltic Exchange', 'Freightos BDI', 'FRED'),
            'update_cadence' => 'daily',
            'features' => array(
                array('name' => 'bdi_level', 'type' => 'level', 'range' => '300-12000', 'description' => 'Baltic Dry Index current level'),
                array('name' => 'bdi_1mo_momentum', 'type' => 'trend', 'range' => '-100 to +100', 'description' => '1-month BDI momentum (pct change)'),
                array('name' => 'bdi_3mo_momentum', 'type' => 'trend', 'range' => '-100 to +100', 'description' => '3-month BDI momentum'),
                array('name' => 'bdi_zscore_1y', 'type' => 'zscore', 'range' => '-3 to +3', 'description' => 'BDI z-score vs 1-year history'),
                array('name' => 'bdi_zscore_2y', 'type' => 'zscore', 'range' => '-3 to +3', 'description' => 'BDI z-score vs 2-year history'),
                array('name' => 'stock_bdi_correlation', 'type' => 'mapping', 'range' => '-1 to +1', 'description' => 'Rolling 60-day correlation of stock to BDI'),
                array('name' => 'supply_regime', 'type' => 'regime', 'range' => 'tight|slack|neutral', 'description' => 'Supply-tight vs supply-slack classification')
            ),
            'algorithms' => array('BDI Cyclical Swing', 'Freight Bottleneck', 'Supply Chain Composite', 'Supply Chain Monitor'),
            'regime_use' => 'Supply-tight: overweight cyclicals, shippers, exporters. BDI collapsing: haircut for BDI-sensitive names. BDI inflecting up from depressed: risk budget increase.'
        ),
        array(
            'id' => 'geopolitical',
            'name' => 'Geopolitical Risk & Policy',
            'description' => 'Caldara-Iacoviello GPR index, sanctions risk, conflict zones. High GPR raises downside risk and depresses risk assets.',
            'source_refs' => array('matteoiacoviello.com/gpr', 'ACLED', 'GDELT'),
            'update_cadence' => 'daily',
            'features' => array(
                array('name' => 'gpr_level', 'type' => 'level', 'range' => '50-500', 'description' => 'Geopolitical Risk Index level'),
                array('name' => 'gpr_1mo_change', 'type' => 'trend', 'range' => '-200 to +200', 'description' => '1-month change in GPR'),
                array('name' => 'gpr_regime', 'type' => 'regime', 'range' => 'low|moderate|high|extreme', 'description' => 'GPR regime classification'),
                array('name' => 'firm_geo_exposure', 'type' => 'mapping', 'range' => '0-100', 'description' => 'Pct revenue in high-risk regions'),
                array('name' => 'sector_geo_tag', 'type' => 'tag', 'range' => 'defense|energy|em_banks|commodities|safe', 'description' => 'Sector sensitivity to geopolitical events'),
                array('name' => 'sanction_risk_flag', 'type' => 'event', 'range' => 'boolean', 'description' => 'Active sanction or conflict zone risk')
            ),
            'algorithms' => array('GPR Defensive', 'Sanctions Avoidance', 'Geopolitical Regime', 'Geopolitical Risk Filter'),
            'regime_use' => 'High GPR: downweight cyclical momentum and event-arb, overweight quality/defensive. Sanction flags: force smaller sizes or avoid list.'
        ),
        array(
            'id' => 'institutional_flow',
            'name' => 'Institutional Flow & Dark Pool',
            'description' => 'Dark pool block trades, congressional trading, insider clusters. Institutions leave footprints that precede major moves.',
            'source_refs' => array('FINRA ATS data', 'SEC EDGAR Form 4', 'Senate/House disclosures', 'Unusual Whales'),
            'update_cadence' => 'daily',
            'features' => array(
                array('name' => 'dp_pct_volume', 'type' => 'level', 'range' => '0-100', 'description' => 'Dark pool volume as pct of consolidated volume'),
                array('name' => 'dp_spike', 'type' => 'event', 'range' => 'boolean', 'description' => 'Recent dark pool volume spike (>2 std dev)'),
                array('name' => 'dp_cluster_zone', 'type' => 'level', 'range' => 'price level', 'description' => 'Price level with repeated block prints'),
                array('name' => 'block_size_zscore', 'type' => 'zscore', 'range' => '-3 to +3', 'description' => 'Block size distribution vs normal'),
                array('name' => 'congress_trade_type', 'type' => 'tag', 'range' => 'long|short|none', 'description' => 'Congressional trade direction'),
                array('name' => 'congress_committee', 'type' => 'tag', 'range' => 'text', 'description' => 'Committee jurisdiction of trading member'),
                array('name' => 'congress_days_since', 'type' => 'level', 'range' => '0-90', 'description' => 'Days since congressional disclosure'),
                array('name' => 'insider_cluster', 'type' => 'event', 'range' => 'boolean', 'description' => '3+ insiders buying within 14 days'),
                array('name' => 'flow_composite', 'type' => 'composite', 'range' => '-100 to +100', 'description' => 'Net institutional flow sentiment')
            ),
            'algorithms' => array('Deep Flow Scanner', 'Block Trade Momentum', 'Congressional Alpha', 'Congressional Short', 'Insider Cluster', 'Dark Pool Microstructure', 'Congressional Negative'),
            'regime_use' => 'Momentum and event-arb: require positive/supportive dark pool flow near entry. Large opposing clusters as soft stop zones. Negative congressional trades as explicit downside signals over 10-15 trading days.'
        ),
        array(
            'id' => 'esg_climate',
            'name' => 'ESG & Climate Risk',
            'description' => 'ESG scores, controversy velocity, climate physical risk. ESG + employee satisfaction composites show abnormal alpha.',
            'source_refs' => array('MSCI ESG', 'Sustainalytics', 'CDP', 'NOAA climate data'),
            'update_cadence' => 'monthly',
            'features' => array(
                array('name' => 'esg_composite', 'type' => 'level', 'range' => '0-100', 'description' => 'Combined ESG rating'),
                array('name' => 'esg_trend_6mo', 'type' => 'trend', 'range' => '-50 to +50', 'description' => '6-month ESG rating change'),
                array('name' => 'controversy_velocity', 'type' => 'level', 'range' => '0-100', 'description' => 'Rate of new controversies (lower is better)'),
                array('name' => 'climate_exposure_zone', 'type' => 'tag', 'range' => 'storm|flood|fire|drought|none', 'description' => 'Physical climate risk zone'),
                array('name' => 'emissions_intensity', 'type' => 'level', 'range' => '0-1000', 'description' => 'CO2 tonnes per $M revenue'),
                array('name' => 'climate_stress_flag', 'type' => 'event', 'range' => 'boolean', 'description' => 'Active extreme weather event affecting operations'),
                array('name' => 'esg_employee_composite', 'type' => 'composite', 'range' => '0-100', 'description' => 'Combined ESG + employee satisfaction score')
            ),
            'algorithms' => array('ESG Quality Composite', 'Climate Risk Filter', 'ESG Momentum', 'Climate Physical Risk', 'ESG Momentum'),
            'regime_use' => 'Quality sleeve: require minimum composite scores and low controversy velocity. Climate-stress flag limits risk for physically exposed names during relevant seasons.'
        ),
        array(
            'id' => 'patent_innovation',
            'name' => 'Patent / IP & Innovation',
            'description' => 'Patent intensity, citation weighting, new technology class entries. Innovation signals proxy future growth and competitive advantage.',
            'source_refs' => array('USPTO PatentsView', 'Google Patents', 'WIPO'),
            'update_cadence' => 'quarterly',
            'features' => array(
                array('name' => 'patent_count_growth', 'type' => 'trend', 'range' => '-100 to +500', 'description' => 'Patent count growth vs 3-5yr history (pct)'),
                array('name' => 'citation_weighted_patents', 'type' => 'level', 'range' => '0-10000', 'description' => 'Patents weighted by forward citations'),
                array('name' => 'new_cpc_classes', 'type' => 'level', 'range' => '0-50', 'description' => 'Number of new CPC technology classes entered'),
                array('name' => 'patent_quality_score', 'type' => 'composite', 'range' => '0-100', 'description' => 'Citation-weighted quality composite'),
                array('name' => 'innovation_consistency', 'type' => 'level', 'range' => '0-100', 'description' => 'Year-over-year consistency of patent output'),
                array('name' => 'rd_to_revenue', 'type' => 'level', 'range' => '0-100', 'description' => 'R&D spend as pct of revenue'),
                array('name' => 'innovation_composite', 'type' => 'composite', 'range' => '0-100', 'description' => 'Overall innovation score')
            ),
            'algorithms' => array('Patent Surge Growth', 'Innovation Compounder', 'Network Effect Moat', 'Patent Innovation Surge', 'Network Effect Mapper'),
            'regime_use' => 'Growth/Quality sleeve: reward high and consistent innovation for multi-year compounding. Penalize high-innovation but cash-burning names unless combined with quality metrics.'
        ),
        array(
            'id' => 'congressional_nuanced',
            'name' => 'Congressional Trading (Nuanced)',
            'description' => 'Harvard Law study: negative congressional trades earn strongest abnormal returns. Long trades are weaker. Committee jurisdiction matters.',
            'source_refs' => array('Senate EFDS', 'House Clerk', 'Capitol Trades', 'Quiver Quantitative'),
            'update_cadence' => 'daily (45-day disclosure lag)',
            'features' => array(
                array('name' => 'trade_direction', 'type' => 'tag', 'range' => 'buy|sell|exercise', 'description' => 'Direction of congressional trade'),
                array('name' => 'position_type', 'type' => 'tag', 'range' => 'stock|option|fund', 'description' => 'Type of position'),
                array('name' => 'committee_jurisdiction', 'type' => 'tag', 'range' => 'text', 'description' => 'Committee the member sits on (sector relevance)'),
                array('name' => 'trade_clustering', 'type' => 'level', 'range' => '0-20', 'description' => 'Number of congress members trading same name/sector in 30 days'),
                array('name' => 'days_since_disclosure', 'type' => 'level', 'range' => '0-90', 'description' => 'Trading days since public disclosure'),
                array('name' => 'negative_trade_signal', 'type' => 'event', 'range' => 'boolean', 'description' => 'Negative/sell congressional trade (strongest signal)')
            ),
            'algorithms' => array('Congressional Alpha', 'Congressional Short', 'Congressional Negative'),
            'regime_use' => 'Long sleeve: modest, short-window edges from senator buys. Strongest: negative congressional trades as explicit downside event signals over 10-15 trading days.'
        )
    );

    $response['total_features'] = 0;
    foreach ($response['factor_families'] as $fam) {
        $response['total_features'] = $response['total_features'] + count($fam['features']);
    }
    $response['total_families'] = count($response['factor_families']);

} elseif ($action === 'factor_scores') {
    // Return composite factor scores for all tracked tickers
    // Pulls from stock_picks and algorithms to compute which factors apply
    $sql = "SELECT DISTINCT sp.ticker, sp.algorithm_name, sp.score, sp.rating, sp.risk_level,
                   a.family, a.algo_type
            FROM stock_picks sp
            LEFT JOIN algorithms a ON sp.algorithm_name = a.name
            ORDER BY sp.ticker, sp.pick_date DESC";
    $res = $conn->query($sql);
    $tickers = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $t = $row['ticker'];
            if (!isset($tickers[$t])) {
                $tickers[$t] = array(
                    'ticker' => $t,
                    'factors' => array(),
                    'algo_count' => 0,
                    'avg_score' => 0,
                    'families' => array()
                );
            }
            $tickers[$t]['algo_count'] = $tickers[$t]['algo_count'] + 1;
            $tickers[$t]['avg_score'] = $tickers[$t]['avg_score'] + (int)$row['score'];
            $fam = $row['family'];
            if ($fam !== '' && !in_array($fam, $tickers[$t]['families'])) {
                $tickers[$t]['families'][] = $fam;
            }
        }
    }
    // Compute averages
    $result = array();
    foreach ($tickers as $t => $data) {
        if ($data['algo_count'] > 0) {
            $data['avg_score'] = round($data['avg_score'] / $data['algo_count'], 1);
        }
        $data['factor_coverage'] = count($data['families']);
        $result[] = $data;
    }
    // Sort by factor coverage desc
    usort($result, 'sort_by_coverage');
    $response['tickers'] = $result;
    $response['count'] = count($result);

} elseif ($action === 'regime_signals') {
    // Current regime signals from multiple macro indicators
    $response['regimes'] = array(
        'vix' => array(
            'source' => 'CBOE VIX',
            'description' => 'Market fear gauge. <16=calm, 16-20=normal, 20-25=elevated, 25-30=high, >30=extreme',
            'current' => null,
            'regime' => 'unknown',
            'last_updated' => null
        ),
        'bdi' => array(
            'source' => 'Baltic Dry Index',
            'description' => 'Global shipping demand. Rising=supply tight, Falling=supply slack',
            'current' => null,
            'regime' => 'unknown',
            'note' => 'Requires external data feed. Use FRED series DBDI for proxy.'
        ),
        'gpr' => array(
            'source' => 'Caldara-Iacoviello GPR Index',
            'description' => 'Geopolitical risk. <100=low, 100-150=moderate, 150-250=high, >250=extreme',
            'current' => null,
            'regime' => 'unknown',
            'note' => 'Monthly from matteoiacoviello.com/gpr'
        ),
        'dxy' => array(
            'source' => 'US Dollar Index',
            'description' => 'Dollar strength. Rising=risk-off, Falling=risk-on for EM and commodities',
            'current' => null,
            'regime' => 'unknown'
        ),
        'yield_curve' => array(
            'source' => '10Y-2Y Treasury Spread',
            'description' => 'Yield curve shape. Inverted=recession signal, Steepening=growth',
            'current' => null,
            'regime' => 'unknown'
        ),
        'spy_trend' => array(
            'source' => 'SPY vs 200-day SMA',
            'description' => 'Broad market trend. Above SMA200=bull, Below=bear',
            'current' => null,
            'regime' => 'unknown'
        )
    );

    // Fill VIX and SPY from market_regimes table
    $sql = "SELECT * FROM market_regimes ORDER BY trade_date DESC LIMIT 1";
    $res = $conn->query($sql);
    if ($res && $res->num_rows > 0) {
        $row = $res->fetch_assoc();
        $response['regimes']['vix']['current'] = (float)$row['vix_close'];
        $response['regimes']['vix']['last_updated'] = $row['trade_date'];
        $vix = (float)$row['vix_close'];
        if ($vix < 16) {
            $response['regimes']['vix']['regime'] = 'calm';
        } elseif ($vix < 20) {
            $response['regimes']['vix']['regime'] = 'normal';
        } elseif ($vix < 25) {
            $response['regimes']['vix']['regime'] = 'elevated';
        } elseif ($vix < 30) {
            $response['regimes']['vix']['regime'] = 'high';
        } else {
            $response['regimes']['vix']['regime'] = 'extreme';
        }

        $spy = (float)$row['spy_close'];
        $sma = (float)$row['spy_sma200'];
        $response['regimes']['spy_trend']['current'] = $spy;
        $response['regimes']['spy_trend']['last_updated'] = $row['trade_date'];
        $response['regimes']['spy_trend']['regime'] = ($spy > $sma) ? 'bull' : 'bear';
        $response['regimes']['spy_trend']['sma200'] = $sma;
    }

    // Meta regime assessment
    $response['meta_regime'] = array(
        'description' => 'Combined multi-factor regime used by Macro Regime Switcher algorithm',
        'factors_available' => 2,
        'factors_total' => 6,
        'recommendation' => 'Connect BDI, GPR, DXY, and yield curve feeds for full regime model'
    );

} elseif ($action === 'data_sources') {
    // External data source endpoints for connecting real alternative data
    $response['data_sources'] = array(
        array(
            'family' => 'human_capital',
            'source' => 'Glassdoor API / Web Scrape',
            'url' => 'https://www.glassdoor.com/developer/index.htm',
            'free_tier' => false,
            'alternative' => 'Indeed company reviews, Comparably, Blind',
            'update_frequency' => 'Monthly scrape recommended'
        ),
        array(
            'family' => 'supply_chain',
            'source' => 'FRED Baltic Dry Index',
            'url' => 'https://fred.stlouisfed.org/series/DBDI',
            'free_tier' => true,
            'alternative' => 'Freightos Baltic Index (FBX), Drewry WCI',
            'update_frequency' => 'Daily'
        ),
        array(
            'family' => 'geopolitical',
            'source' => 'Caldara-Iacoviello GPR Index',
            'url' => 'https://www.matteoiacoviello.com/gpr.htm',
            'free_tier' => true,
            'alternative' => 'GDELT event data, ACLED conflict data',
            'update_frequency' => 'Monthly (downloadable CSV)'
        ),
        array(
            'family' => 'institutional_flow',
            'source' => 'FINRA ATS Transparency Data',
            'url' => 'https://otctransparency.finra.org/otctransparency/AtsIssueData',
            'free_tier' => true,
            'alternative' => 'Bookmap dark pool data, Unusual Whales',
            'update_frequency' => 'Weekly (2-week lag)'
        ),
        array(
            'family' => 'institutional_flow',
            'source' => 'SEC EDGAR Form 4 (Insider Trades)',
            'url' => 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=4',
            'free_tier' => true,
            'alternative' => 'OpenInsider.com, SEC RSS feed',
            'update_frequency' => 'Daily'
        ),
        array(
            'family' => 'congressional',
            'source' => 'Senate EFDS / House Clerk',
            'url' => 'https://efds.senate.gov/search/',
            'free_tier' => true,
            'alternative' => 'Capitol Trades, Quiver Quantitative, Unusual Whales Congress',
            'update_frequency' => 'Daily (45-day disclosure lag)'
        ),
        array(
            'family' => 'esg_climate',
            'source' => 'MSCI ESG Ratings',
            'url' => 'https://www.msci.com/our-solutions/esg-investing/esg-ratings',
            'free_tier' => false,
            'alternative' => 'Sustainalytics (free summaries), CDP, Yahoo Finance ESG scores',
            'update_frequency' => 'Monthly'
        ),
        array(
            'family' => 'patent_innovation',
            'source' => 'USPTO PatentsView API',
            'url' => 'https://patentsview.org/apis/api-endpoints',
            'free_tier' => true,
            'alternative' => 'Google Patents Public Data, WIPO IP Statistics',
            'update_frequency' => 'Quarterly'
        )
    );

} elseif ($action === 'ticker_factors') {
    // Factor profile for a single ticker
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    if ($ticker === '') {
        $response['ok'] = false;
        $response['error'] = 'ticker parameter required';
    } else {
        $safe = $conn->real_escape_string($ticker);
        // Get all picks for this ticker with algorithm info
        $sql = "SELECT sp.algorithm_name, sp.score, sp.rating, sp.risk_level, sp.pick_date,
                       a.family, a.algo_type, a.description as algo_desc
                FROM stock_picks sp
                LEFT JOIN algorithms a ON sp.algorithm_name = a.name
                WHERE sp.ticker = '$safe'
                ORDER BY sp.pick_date DESC";
        $res = $conn->query($sql);
        $picks = array();
        $families_seen = array();
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $picks[] = $row;
                $fam = $row['family'];
                if ($fam !== '' && !isset($families_seen[$fam])) {
                    $families_seen[$fam] = 0;
                }
                if ($fam !== '') {
                    $families_seen[$fam] = $families_seen[$fam] + 1;
                }
            }
        }
        // Alt-data factor family mapping
        $alt_data_families = array(
            'AltData' => 'human_capital',
            'ESG' => 'esg_climate',
            'SupplyChain' => 'supply_chain',
            'Geopolitical' => 'geopolitical',
            'InstFlow' => 'institutional_flow',
            'Flow' => 'institutional_flow',
            'Innovation' => 'patent_innovation',
            'AlphaForge' => 'multi_factor_ensemble',
            'Macro' => 'supply_chain'
        );

        $alt_coverage = array();
        foreach ($families_seen as $fam => $cnt) {
            if (isset($alt_data_families[$fam])) {
                $alt_coverage[$alt_data_families[$fam]] = $cnt;
            }
        }

        $response['ticker'] = $ticker;
        $response['total_picks'] = count($picks);
        $response['algorithm_families'] = $families_seen;
        $response['alt_data_coverage'] = $alt_coverage;
        $response['alt_data_families_covered'] = count($alt_coverage);
        $response['alt_data_families_total'] = 7;
        $response['recent_picks'] = array_slice($picks, 0, 20);
    }

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action. Use: factors, factor_scores, regime_signals, data_sources, ticker_factors';
}

echo json_encode($response);
$conn->close();

// PHP 5.2 compatible sort function
function sort_by_coverage($a, $b) {
    if ($a['factor_coverage'] == $b['factor_coverage']) {
        return 0;
    }
    return ($a['factor_coverage'] > $b['factor_coverage']) ? -1 : 1;
}
?>
