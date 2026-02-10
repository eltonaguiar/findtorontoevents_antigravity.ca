import urllib.request, json

base = 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions'

# List all workflows to see their IDs and if they're active
url = f'{base}/workflows?per_page=30'
req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Python'})
data = json.loads(urllib.request.urlopen(req, timeout=10).read())

print(f"Total workflows: {data['total_count']}\n")
for wf in data['workflows']:
    print(f"  [{wf['state']:>10}] {wf['name']:<50} {wf['path']}")
