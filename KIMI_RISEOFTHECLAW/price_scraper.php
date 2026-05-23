<?php
/**
 * PRICE SCRAPER — Server-side fallback for crypto price data
 * Layer 4 of the multi-API cascade.
 * Called only when CoinGecko, Binance, and CryptoCompare all fail client-side.
 * 
 * Strategies: CoinGecko → Binance → CryptoCompare → CoinDesk → CoinMarketCap scrape
 * Usage: price_scraper.php?symbols=BTC-USD,ETH-USD,SOL-USD
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=30');

$coingeckoMap = array(
    'BTC-USD' => 'bitcoin',
    'ETH-USD' => 'ethereum',
    'BNB-USD' => 'binancecoin',
    'SOL-USD' => 'solana',
    'DOGE-USD' => 'dogecoin',
    'AVAX-USD' => 'avalanche-2',
    'LTC-USD' => 'litecoin',
    'XRP-USD' => 'ripple',
    'ADA-USD' => 'cardano',
    'APT-USD' => 'aptos'
);

$binanceMap = array(
    'BTC-USD' => 'BTCUSDT',
    'ETH-USD' => 'ETHUSDT',
    'BNB-USD' => 'BNBUSDT',
    'SOL-USD' => 'SOLUSDT',
    'DOGE-USD' => 'DOGEUSDT',
    'AVAX-USD' => 'AVAXUSDT',
    'LTC-USD' => 'LTCUSDT',
    'XRP-USD' => 'XRPUSDT',
    'ADA-USD' => 'ADAUSDT',
    'APT-USD' => 'APTUSDT'
);

$ccMap = array(
    'BTC-USD' => 'BTC',
    'ETH-USD' => 'ETH',
    'BNB-USD' => 'BNB',
    'SOL-USD' => 'SOL',
    'DOGE-USD' => 'DOGE',
    'AVAX-USD' => 'AVAX',
    'LTC-USD' => 'LTC',
    'XRP-USD' => 'XRP',
    'ADA-USD' => 'ADA',
    'APT-USD' => 'APT'
);

$cmcSlugs = array(
    'BTC-USD' => 'bitcoin',
    'ETH-USD' => 'ethereum',
    'BNB-USD' => 'bnb',
    'SOL-USD' => 'solana',
    'DOGE-USD' => 'dogecoin',
    'AVAX-USD' => 'avalanche',
    'LTC-USD' => 'litecoin',
    'XRP-USD' => 'xrp',
    'ADA-USD' => 'cardano',
    'APT-USD' => 'aptos'
);

$symbolsParam = isset($_GET['symbols']) ? $_GET['symbols'] : '';
$symbols = array_filter(explode(',', $symbolsParam));

if (empty($symbols)) {
    echo json_encode(array('error' => 'No symbols provided', 'usage' => 'price_scraper.php?symbols=BTC-USD,ETH-USD'));
    exit;
}

$prices = array();
$sources = array();
$log = array();
$remaining = $symbols;

function fetchUrl($url, $timeout = 8)
{
    $ctx = stream_context_create(array(
        'http' => array(
            'timeout' => $timeout,
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
        ),
        'ssl' => array(
            'verify_peer' => false,
            'verify_peer_name' => false
        )
    ));
    $result = @file_get_contents($url, false, $ctx);
    return $result;
}

// Strategy 1: CoinGecko (server-side)
$cgIds = array();
foreach ($remaining as $sym) {
    if (isset($coingeckoMap[$sym])) {
        $cgIds[$coingeckoMap[$sym]] = $sym;
    }
}
if (!empty($cgIds)) {
    $ids = implode(',', array_keys($cgIds));
    $url = "https://api.coingecko.com/api/v3/simple/price?ids=" . $ids . "&vs_currencies=usd";
    $data = fetchUrl($url);
    if ($data) {
        $json = json_decode($data, true);
        if ($json) {
            $count = 0;
            foreach ($cgIds as $cgId => $sym) {
                if (isset($json[$cgId]) && isset($json[$cgId]['usd'])) {
                    $prices[$sym] = (float) $json[$cgId]['usd'];
                    $sources[$sym] = 'coingecko_php';
                    $count++;
                }
            }
            $log[] = array('api' => 'CoinGecko (PHP)', 'status' => 'ok', 'count' => $count);
        }
    } else {
        $log[] = array('api' => 'CoinGecko (PHP)', 'status' => 'failed');
    }
    $newRemaining = array();
    foreach ($remaining as $s) {
        if (!isset($prices[$s]))
            $newRemaining[] = $s;
    }
    $remaining = $newRemaining;
}

// Strategy 2: Binance (server-side)
if (!empty($remaining)) {
    $bnSymbols = array();
    foreach ($remaining as $sym) {
        if (isset($binanceMap[$sym])) {
            $bnSymbols[$binanceMap[$sym]] = $sym;
        }
    }
    if (!empty($bnSymbols)) {
        $symbolList = '["' . implode('","', array_keys($bnSymbols)) . '"]';
        $url = "https://api.binance.com/api/v3/ticker/price?symbols=" . $symbolList;
        $data = fetchUrl($url);
        if ($data) {
            $json = json_decode($data, true);
            if ($json) {
                $count = 0;
                foreach ($json as $item) {
                    foreach ($bnSymbols as $bId => $sym) {
                        if ($item['symbol'] === $bId && !isset($prices[$sym])) {
                            $prices[$sym] = (float) $item['price'];
                            $sources[$sym] = 'binance_php';
                            $count++;
                        }
                    }
                }
                $log[] = array('api' => 'Binance (PHP)', 'status' => 'ok', 'count' => $count);
            }
        } else {
            $log[] = array('api' => 'Binance (PHP)', 'status' => 'failed');
        }
        $newRemaining = array();
        foreach ($remaining as $s) {
            if (!isset($prices[$s]))
                $newRemaining[] = $s;
        }
        $remaining = $newRemaining;
    }
}

// Strategy 3: CryptoCompare (server-side)
if (!empty($remaining)) {
    $ccKey = 'qb8ddikglknpseumlz4w';
    $ccSymbols = array();
    foreach ($remaining as $sym) {
        if (isset($ccMap[$sym])) {
            $ccSymbols[$ccMap[$sym]] = $sym;
        }
    }
    if (!empty($ccSymbols)) {
        $fsyms = implode(',', array_keys($ccSymbols));
        $url = "https://min-api.cryptocompare.com/data/pricemulti?fsyms=" . $fsyms . "&tsyms=USD&api_key=" . $ccKey;
        $data = fetchUrl($url);
        if ($data) {
            $json = json_decode($data, true);
            if ($json) {
                $count = 0;
                foreach ($ccSymbols as $cc => $sym) {
                    if (isset($json[$cc]) && isset($json[$cc]['USD']) && !isset($prices[$sym])) {
                        $prices[$sym] = (float) $json[$cc]['USD'];
                        $sources[$sym] = 'cryptocompare_php';
                        $count++;
                    }
                }
                $log[] = array('api' => 'CryptoCompare (PHP)', 'status' => 'ok', 'count' => $count);
            }
        } else {
            $log[] = array('api' => 'CryptoCompare (PHP)', 'status' => 'failed');
        }
        $newRemaining = array();
        foreach ($remaining as $s) {
            if (!isset($prices[$s]))
                $newRemaining[] = $s;
        }
        $remaining = $newRemaining;
    }
}

// Strategy 4: CoinDesk (BTC only)
if (!empty($remaining)) {
    foreach ($remaining as $sym) {
        if ($sym === 'BTC-USD') {
            $url = "https://api.coindesk.com/v1/bpi/currentprice/USD.json";
            $data = fetchUrl($url);
            if ($data) {
                $json = json_decode($data, true);
                if (isset($json['bpi']) && isset($json['bpi']['USD']) && isset($json['bpi']['USD']['rate_float'])) {
                    $prices[$sym] = (float) $json['bpi']['USD']['rate_float'];
                    $sources[$sym] = 'coindesk_php';
                    $log[] = array('api' => 'CoinDesk (PHP)', 'status' => 'ok', 'count' => 1);
                }
            }
        }
    }
    $newRemaining = array();
    foreach ($remaining as $s) {
        if (!isset($prices[$s]))
            $newRemaining[] = $s;
    }
    $remaining = $newRemaining;
}

// Strategy 5: Web Scraping CoinMarketCap (absolute last resort)
if (!empty($remaining)) {
    $scraped = 0;
    foreach ($remaining as $sym) {
        if (isset($cmcSlugs[$sym])) {
            $slug = $cmcSlugs[$sym];
            $url = "https://coinmarketcap.com/currencies/" . $slug . "/";
            $html = fetchUrl($url, 10);
            if ($html) {
                if (preg_match('/"price":"?([\d,]+\.?\d*)"?/', $html, $matches)) {
                    $price = (float) str_replace(',', '', $matches[1]);
                    if ($price > 0) {
                        $prices[$sym] = $price;
                        $sources[$sym] = 'cmc_scrape';
                        $scraped++;
                    }
                }
                if (!isset($prices[$sym]) && preg_match('/price today is \$([\d,]+\.?\d*)/', $html, $matches)) {
                    $price = (float) str_replace(',', '', $matches[1]);
                    if ($price > 0) {
                        $prices[$sym] = $price;
                        $sources[$sym] = 'cmc_scrape';
                        $scraped++;
                    }
                }
            }
        }
    }
    $log[] = array('api' => 'CoinMarketCap Scrape', 'status' => ($scraped > 0 ? 'ok' : 'failed'), 'count' => $scraped);
}

echo json_encode(array(
    'prices' => $prices,
    'sources' => $sources,
    'log' => $log,
    'timestamp' => date('Y-m-d H:i:s'),
    'requested' => $symbols,
    'fulfilled' => count($prices),
    'missing' => array_values(array_diff($symbols, array_keys($prices)))
));
