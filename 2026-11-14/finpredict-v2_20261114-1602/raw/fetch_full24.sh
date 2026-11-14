#!/bin/bash
id="$1"
repo=eltonaguiar/findtorontoevents_antigravity.ca
mkdir -p raw/wf24_full
gh api "repos/$repo/actions/workflows/$id/runs?per_page=100&created=%3E%3D2026-11-13T16:05:00Z" --paginate \
  --jq '.workflow_runs[]|{id,created_at,updated_at,status,conclusion,event,head_branch,name,run_number,run_started_at}' > "raw/wf24_full/$id.jsonl" || echo "FAIL24 $id" >&2
