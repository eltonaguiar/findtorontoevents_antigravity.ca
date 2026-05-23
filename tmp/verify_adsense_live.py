import urllib.request

# Check ads.txt
print("=== ads.txt ===")
req = urllib.request.Request("https://torontoevent.net/ads.txt", headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=10)
print("Status:", resp.getcode())
print("Content:", resp.read().decode("utf-8").strip())
print()

# Check index.html
print("=== index.html AdSense check ===")
req = urllib.request.Request("https://torontoevent.net/", headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=15)
html = resp.read().decode("utf-8", errors="ignore")
head_end = html.lower().find("</head>")
head = html[:head_end] if head_end > 0 else ""

# Check for direct script tag
tag = 'src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7893721225790912"'
has_direct = tag in head
print("Direct <script> tag in <head>:", has_direct)

# Show context around first occurrence
idx = head.find("pagead2.googlesyndication.com")
if idx >= 0:
    start = max(0, idx - 60)
    end = min(len(head), idx + 120)
    print("Context:")
    print(head[start:end])

print()
old = html.count("findtorontoevents.ca")
new = html.count("torontoevent.net")
print("Old domain refs:", old)
print("New domain refs:", new)
