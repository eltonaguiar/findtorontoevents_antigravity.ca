import urllib.request

print("=== ads.txt ===")
req = urllib.request.Request("https://torontoevent.net/ads.txt", headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=10)
print("Status:", resp.getcode())
print("Content:", resp.read().decode("utf-8").strip())
print()

print("=== AdSense in <head> ===")
req = urllib.request.Request("https://torontoevent.net/", headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=15)
html = resp.read().decode("utf-8", errors="ignore")
head_end = html.lower().find("</head>")
head = html[:head_end] if head_end > 0 else ""
tag = 'pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7893721225790912'
has_direct = tag in head
print("Direct AdSense script in <head>:", has_direct)
print()

print("=== Supercomputer text fix ===")
has_without = "without a supercomputer" in html
has_with_a = "with a supercomputer" in html and "without a supercomputer" not in html
print("Has 'without a supercomputer':", has_without)
print("Still has old 'with a supercomputer':", has_with_a)
print()

print("=== Domain refs ===")
old = html.count("findtorontoevents.ca")
new = html.count("torontoevent.net")
print("Old domain (findtorontoevents.ca):", old)
print("New domain (torontoevent.net):", new)
