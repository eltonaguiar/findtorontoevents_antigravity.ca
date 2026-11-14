#!/bin/bash
id="$1"
repo=eltonaguiar/findtorontoevents_antigravity.ca
gh api "repos/$repo/actions/runs/$id/jobs?per_page=100" --jq '{total_count, jobs:[.jobs[]|{name,status,conclusion,started_at,completed_at,steps:[.steps[]?|{name,status,conclusion}]}]}' > "raw/jobs/$id.json" 2>/dev/null || echo "FAILJOB $id" >&2
