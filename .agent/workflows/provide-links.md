---
description: Always provide remote site links for testing after any file change
---

# Provide Remote Links

After completing any work that creates or modifies files on the site, ALWAYS provide the corresponding live URL(s) so the user can test on the remote site.

## Rules

1. The base domain is `https://findtorontoevents.ca`
2. Map the local workspace path `e:\findtorontoevents_antigravity.ca\` to the root `/`
3. For example:
   - `e:\findtorontoevents_antigravity.ca\updates\index.html` → `https://findtorontoevents.ca/updates/`
   - `e:\findtorontoevents_antigravity.ca\KIMI_RISEOFTHECLAW\dashboard_live.html` → `https://findtorontoevents.ca/KIMI_RISEOFTHECLAW/dashboard_live.html`
4. Include ALL relevant links, not just the primary one
5. Present links in a clear format the user can click

## CRITICAL: Verify Links Before Providing

6. **ALWAYS verify every link is live** before providing it to the user. Use the `read_url_content` tool or the browser to check that the URL returns a 200 and has expected content.
7. If a link is NOT live (404, error, or hasn't been deployed yet):
   - Do NOT provide the link as a working link
   - Instead, clearly tell the user the file is NOT yet deployed
   - Offer to help run the deploy process first
   - Only provide the link AFTER confirming it is live
8. If a deploy is needed, check if `/.agent/workflows/deploy.md` exists and follow it. Otherwise, ask the user how to deploy.
9. **Never assume deployment happened.** Always verify.
