/**
 * Stock API Keys Configuration
 * 
 * Extracted from existing projects in C:\Users\zerou\Documents\Coding
 * These keys are used as fallbacks when Yahoo Finance (free) is unavailable
 */

export const STOCK_API_KEYS = {
  // Polygon.io - Real-time and historical market data
  POLYGON: '2xiTaFKgrJA8eGyxd_tF5GTu3OTXMUWC',
  
  // Finnhub - Real-time stock data, news, and fundamentals (multiple keys)
  FINNHUB: 'cvstlkhr01qhup0t0j7gcvstlkhr01qhup0t0j80',
  FINNHUB_NEW: 'cvrl241r01qnpem84d0gcvrl241r01qnpem84d10', // New key found
  
  // Alpha Vantage - Stock market data (multiple keys for failover)
  ALPHA_VANTAGE: '1618K3H5MFCONH92',
  ALPHA_VANTAGE_FAILOVER: 'OJUUINBH3E50UGWO',
  ALPHA_VANTAGE_ALT: '5RD6VT5ZEGO6HA8P', // From MyPredictor
  ALPHA_VANTAGE_NEW: '6XN7LYXEYUOIAM7M', // New key found
  
  // Tiingo - Financial data API
  TIINGO: '2247aa4e93338de698597f58f44136f08e17694d',
  
  // Marketstack - Market data API
  MARKETSTACK: 'f4a2dd73fbd3cbb068a7dc56b6192cfc',
  
  // RapidAPI - Gateway to multiple APIs (can be used for scraping APIs too)
  RAPIDAPI: 'b1ee5c7d46msh15d35e04e051ad2p1b5e14jsncfbcbb51b443',
  
  // Google Custom Search (can be used for web scraping/search)
  GOOGLE_CUSTOM_SEARCH: 'AIzaSyB3jhUkndfV6_c99tCh_h0byKpTjTh3ETU',
  GOOGLE_CSE_ID: 'd0432542ea931417b',
  
  // Alpaca Markets - Trading API (paper trading)
  ALPACA_API_KEY: 'PKNMXSCXURUCGRHDY6C3',
  ALPACA_SECRET_KEY: '2l6gkJA7j4biMNK4tU70c055mBb5qkGeD6q7IVFz',
  ALPACA_PAPER: true,
  
  // Nasdaq Data Link
  NASDAQ_DATALINK: 'GCRzsLSfx9DmxyCbM6u3',
  
  // Twelve Data - Real-time and historical stock data
  TWELVE_DATA: '43e686519f7b4155a4a90eaae82fb63a',
};

/**
 * API Rate Limits (calls per minute/day)
 * Used to prevent hitting rate limits
 */
export const API_RATE_LIMITS = {
  POLYGON: { callsPerMinute: 5, callsPerDay: 200 },
  FINNHUB: { callsPerMinute: 60, callsPerDay: 500 },
  ALPHA_VANTAGE: { callsPerMinute: 5, callsPerDay: 500 },
  TIINGO: { callsPerMinute: 5, callsPerDay: 500 },
  MARKETSTACK: { callsPerMinute: 5, callsPerDay: 1000 },
  TWELVE_DATA: { callsPerMinute: 8, callsPerDay: 800 }, // Free tier: 800 calls/day
  YAHOO_FINANCE: { callsPerMinute: 2, callsPerDay: 500 }, // Free, no key needed
};

/**
 * API Priority Order
 * Try these in order when fetching stock data
 */
export const API_PRIORITY = [
  'YAHOO_FINANCE',  // Free, no key needed
  'POLYGON',        // Good rate limits
  'TWELVE_DATA',    // Good free tier (800 calls/day)
  'FINNHUB',        // High rate limits
  'TIINGO',         // Backup
  'MARKETSTACK',    // Backup
  'ALPHA_VANTAGE',  // Last resort
];
