import urllib.request
import binascii

url = "https://findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js"
print(f"Checking URL: {url}")
try:
    with urllib.request.urlopen(url) as response:
        content = response.read(100)
        print(f"Status: {response.status}")
        print(f"Content-Type: {response.getheader('Content-Type')}")
        print(f"Hex: {binascii.hexlify(content).decode()}")
        print(f"Text: {content.decode('utf-8', 'ignore')}")
except Exception as e:
    print(f"Error: {e}")
