import re, json, urllib.request, sys
html = open('audit_full.html','r',encoding='utf-8').read()
links = re.findall(r'href\s*=\s*"([^\"]+)"', html)
results = []
for url in links:
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.getcode()
    except Exception as e:
        status = None
    results.append({'url': url, 'status': status})
print(json.dumps(results, indent=2))