#!/bin/bash
# Reusable failure notification to Discord sandbox channel
# Usage: bash .github/notify-failure.sh "Workflow Name" "$DISCORD_WEBHOOK_SANDBOX" "$GITHUB_REPOSITORY" "$GITHUB_RUN_ID"

WORKFLOW_NAME="${1:-Unknown Workflow}"
WEBHOOK_URL="$2"
REPO="$3"
RUN_ID="$4"

if [ -z "$WEBHOOK_URL" ]; then
  echo "No DISCORD_WEBHOOK_SANDBOX set, skipping failure notification"
  exit 0
fi

TIMESTAMP=$(date -u +'%Y-%m-%d %H:%M UTC')

curl -s -H "Content-Type: application/json" -d "{
  \"embeds\": [{
    \"title\": \"\u274c ${WORKFLOW_NAME} FAILED\",
    \"description\": \"**Time:** ${TIMESTAMP}\n[View Run](https://github.com/${REPO}/actions/runs/${RUN_ID})\",
    \"color\": 15548997,
    \"footer\": {\"text\": \"Sandbox Failure Monitor\"}
  }]
}" "$WEBHOOK_URL" || true
