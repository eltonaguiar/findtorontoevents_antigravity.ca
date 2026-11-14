#!/bin/bash
id="$1"
out="raw/wf/${id}.json"
mkdir -p raw/wf
repo=eltonaguiar/findtorontoevents_antigravity.ca
if [ -s "$out" ]; then exit 0; fi
a=$(gh api "repos/$repo/actions/workflows/$id/runs?per_page=10" --jq '{total_count, runs:[.workflow_runs[]|{id,created_at,updated_at,status,conclusion,event,head_branch,name,run_number,run_started_at}]}' 2>/dev/null)
b=$(gh api "repos/$repo/actions/workflows/$id/runs?per_page=100&created=%3E%3D2026-11-07T16:05:00Z" --jq '{total_count, runs:[.workflow_runs[]|{id,created_at,updated_at,status,conclusion,event,run_started_at}]}' 2>/dev/null)
c=$(gh api "repos/$repo/actions/workflows/$id/runs?per_page=100&created=%3E%3D2026-11-13T16:05:00Z" --jq '{total_count, runs:[.workflow_runs[]|{id,created_at,updated_at,status,conclusion,event,run_started_at}]}' 2>/dev/null)
if [ -z "$a" ] || [ -z "$b" ] || [ -z "$c" ]; then echo "FAIL $id" >&2; exit 1; fi
printf '{"id":%s,"last10":%s,"d7":%s,"d1":%s}\n' "$id" "$a" "$b" "$c" > "$out"
