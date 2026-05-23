import requests
import os

# GitHub repo details
owner = 'eltonaguiar'
repo = 'findtorontoevents_antigravity.ca'
workflow_id = 'train_crypto_models.yml'  # Or the workflow file name

# Get PAT from environment variable
pat = os.getenv('GITHUB_PAT')  # Ensure GITHUB_PAT is set in your environment

if not pat:
    print("Error: GITHUB_PAT environment variable not set.")
    exit(1)

# GitHub API endpoint for workflow dispatch
url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"

headers = {
    'Authorization': f'token {pat}',
    'Accept': 'application/vnd.github.v3+json',
    'Content-Type': 'application/json'
}

data = {
    'ref': 'main'  # Branch to run on
    # Optional: inputs if your workflow accepts them
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 204:
    print("Workflow triggered successfully!")
else:
    print(f"Error: {response.status_code} - {response.text}")
