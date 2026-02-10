import urllib.request, json

# Check failing workflows and stock-related workflows
url = 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs?per_page=50'
req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Python'})
data = json.loads(urllib.request.urlopen(req, timeout=15).read())

# Group by workflow name, show last result
seen = {}
for run in data['workflow_runs']:
    name = run['name']
    if name not in seen:
        seen[name] = run

print("=== WORKFLOW STATUS (Most Recent Run Per Workflow) ===\n")
for name, run in sorted(seen.items()):
    status = run.get('conclusion', run['status'])
    emoji = 'PASS' if status == 'success' else 'FAIL' if status == 'failure' else status.upper()
    print(f"  [{emoji:>4}] {name:<50} {run['created_at']}")

# Now check specifically for stock-related failures
print("\n=== STOCK/PORTFOLIO WORKFLOW RUNS (last 5 each) ===")
stock_keywords = ['stock', 'portfolio', 'mutual', 'simulation']
for run in data['workflow_runs']:
    if any(kw in run['name'].lower() for kw in stock_keywords):
        print(f"  {run['name']:<50} {run.get('conclusion','?'):<10} {run['created_at']}")

# Check for the failing ones
print("\n=== FAILING WORKFLOWS DETAIL ===")
for name, run in sorted(seen.items()):
    if run.get('conclusion') == 'failure':
        print(f"\n  {name}: run_id={run['id']}")
        # Try to get jobs
        jobs_url = f"https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/{run['id']}/jobs"
        try:
            req2 = urllib.request.Request(jobs_url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Python'})
            jobs_data = json.loads(urllib.request.urlopen(req2, timeout=10).read())
            for job in jobs_data.get('jobs', []):
                print(f"    Job: {job['name']} -> {job.get('conclusion','?')}")
                for step in job.get('steps', []):
                    if step.get('conclusion') == 'failure':
                        print(f"      FAILED step: {step['name']}")
        except Exception as e:
            print(f"    Could not fetch jobs: {e}")
