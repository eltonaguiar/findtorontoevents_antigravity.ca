<?php
/**
 * CoinGecko API Configuration
 * 
 * Provides the CoinGecko Demo API key and a helper to get the auth header.
 * Include this file in any PHP script that calls CoinGecko endpoints.
 *
 * Usage:
 *   require_once dirname(__FILE__) . '/cg_config.php';
 *   // Then add cg_auth_header() to your CURLOPT_HTTPHEADER array:
 *   curl_setopt($ch, CURLOPT_HTTPHEADER, array_merge(
 *       array('Accept: application/json'),
 *       cg_auth_headers()
 *   ));
 *
 * The Demo key gives 30 calls/min (vs 10-30 free) and access to more endpoints.
 */

if (!defined('CG_DEMO_API_KEY')) {
    define('CG_DEMO_API_KEY', 'CG-gYjRbGZZoUcGe8LwAxsXxjeT');
}

/**
 * Returns an array of HTTP headers for CoinGecko Demo API authentication.
 * Safe to merge into any existing header array.
 *
 * @return array
 */
function cg_auth_headers()
{
    return array('x-cg-demo-api-key: ' . CG_DEMO_API_KEY);
}
