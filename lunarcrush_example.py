# Example: Using LunarCRUSH API with a free API key
#
# 1. Install requests library (if not already installed)
#    pip install requests
#
# 2. Replace 'YOUR_FREE_API_KEY' with the key you obtained from https://lunarcrush.com/api
#
# 3. This script fetches the latest market data for Bitcoin (symbol: BTC) and prints the price and social sentiment.
#
import requests

API_KEY = "YOUR_FREE_API_KEY"
BASE_URL = "https://api.lunarcrush.com/v2"


def get_crypto_data(symbol: str):
    """Fetch market and social data for a given cryptocurrency symbol.

    Args:
        symbol: Ticker symbol, e.g., 'BTC' for Bitcoin.

    Returns:
        JSON response from LunarCRUSH API.
    """
    params = {
        "key": API_KEY,
        "symbol": symbol,
        "data": "assets",
        "type": "price,volume,market_cap,social_volume"
    }
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    symbol = "BTC"
    data = get_crypto_data(symbol)
    # The response structure: {'data': [{'symbol': 'BTC', 'price': ..., 'social_volume': ...}]}
    asset = data.get('data', [{}])[0]
    print(f"{symbol} price: ${asset.get('price')}")
    print(f"Social volume: {asset.get('social_volume')}")
