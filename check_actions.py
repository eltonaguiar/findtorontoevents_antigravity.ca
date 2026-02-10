import urllib.request, json
url = 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs?per_page=20'
req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Python'})
data = json.loads(urllib.request.urlopen(req, timeout=15).read())
print(f"Total workflow runs: {data['total_count']}\n")
print(f"{'Workflow':<50} {'Status':<12} {'Conclusion':<12} {'Created'}")
print("-" * 110)
for run in data['workflow_runs']:
    print(f"{run['name']:<50} {run['status']:<12} {str(run.get('conclusion','')):<12} {run['created_at']}")
