import urllib.request, json

base = 'https://api.github.com/repos/eltonaguiar/findtorontoevents_antigravity.ca/actions'

# Check each stock workflow specifically
stock_workflows = [
    'daily-stock-refresh.yml',
    'refresh-stocks-portfolio.yml',
    'weekly-stock-simulation.yml',
    'daily-mutualfund-refresh.yml',
]

for wf in stock_workflows:
    url = f'{base}/workflows/{wf}/runs?per_page=3'
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Python'})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        runs = data.get('workflow_runs', [])
        print(f"\n=== {wf} (total: {data.get('total_count',0)}) ===")
        if not runs:
            print("  NO RUNS FOUND")
        for run in runs:
            print(f"  {run.get('conclusion','?'):<10} {run['created_at']}  (#{run['run_number']})")
    except Exception as e:
        print(f"\n=== {wf} ===\n  Error: {e}")

# Also check the 3 failing ones for their logs
print("\n\n=== FAILING WORKFLOW LOGS ===")
failing_ids = [21815774660, 21815285693]  # Fetch Movies, Send Reminders
for run_id in failing_ids:
    url = f'{base}/runs/{run_id}/jobs'
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Python'})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        for job in data.get('jobs', []):
            for step in job.get('steps', []):
                if step.get('conclusion') == 'failure':
                    print(f"\n  Run {run_id} - {step['name']}:")
                    # Try to get log
                    log_url = f'{base}/jobs/{job["id"]}/logs'
                    try:
                        req3 = urllib.request.Request(log_url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Python'})
                        log_data = urllib.request.urlopen(req3, timeout=10).read().decode('utf-8', errors='replace')
                        # Get last 30 lines
                        lines = log_data.strip().split('\n')
                        print('    ...')
                        for line in lines[-20:]:
                            print(f'    {line[:120]}')
                    except Exception as e:
                        print(f"    Could not fetch log: {e}")
    except Exception as e:
        print(f"  Error fetching jobs for {run_id}: {e}")
