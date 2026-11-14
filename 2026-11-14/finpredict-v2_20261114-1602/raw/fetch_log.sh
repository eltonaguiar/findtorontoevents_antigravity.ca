#!/bin/bash
id="$1"
repo=eltonaguiar/findtorontoevents_antigravity.ca
gh run view "$id" --repo "$repo" --log-failed > "raw/logs/${id}.log" 2>&1 || gh run view "$id" --repo "$repo" --log > "raw/logs/${id}.log" 2>&1
echo "$id $(wc -c < raw/logs/${id}.log)"
