"""Insert AI research section into updates.html - v3."""
import re

filepath = r"e:\findtorontoevents_antigravity.ca\findstocks\updates.html"

with open(filepath, "rb") as f:
    data = f.read()

# Remove BOM if present
if data.startswith(b'\xef\xbb\xbf'):
    data = data[3:]

content = data.decode("utf-8")
print(f"File: {len(content)} chars")

# Find the last </style> or </head> to skip CSS, then find 'container' div after that
body_start = content.find("<body>")
print(f"<body> at char: {body_start}")

# Find the container div after body
div_container = content.find('"container"', body_start)
print(f'container div at: {div_container}')
if div_container == -1:
    # try unicode quotes
    div_container = content.find("\u201ccontainer\u201d", body_start)
    print(f'smart quotes container at: {div_container}')

# Find the closing > of this div tag
gt = content.find(">", div_container)
print(f'> at: {gt}')

# Find the first <!-- comment after the container div
comment = content.find("<!--", gt)
print(f'First <!-- at: {comment}')
print(f'Context around comment: {repr(content[comment:comment+60])}')

new_section = '''
    <!-- AI System Evaluation / Deep Research -->
    <div class="update-entry" style="border-color: rgba(167, 139, 250, 0.4); box-shadow: 0 0 16px rgba(167, 139, 250, 0.1);">
        <div class="update-date">February 12, 2026</div>
        <div class="update-title">\U0001F9E0 AI System Evaluation &amp; Deep Research</div>
        <div class="update-body">
            <p>Comprehensive algorithm analysis performed by <strong>9 different AI systems</strong>, each independently evaluating our trading algorithms, comparing against industry standards (Renaissance, Two Sigma, Citadel, AQR), and proposing enhancement roadmaps. <a href="/findstocks/ai-research/">View all &rarr;</a></p>
            <ul>
                <li><span class="tag tag-review">Research</span> <strong><a href="/findstocks/ai-research/antigravity-motherload.html">Antigravity (Gemini 2.0 Flash)</a></strong> &mdash; Complete algorithm analysis &amp; industry standards comparison</li>
                <li><span class="tag tag-review">Research</span> <strong><a href="/findstocks/ai-research/windsurf-motherload.html">Windsurf Cascade</a></strong> &mdash; Battle plan with 50+ upgrades, live data audit</li>
                <li><span class="tag tag-review">Research</span> <strong><a href="/findstocks/ai-research/kimi-agentswarm-motherload.html">Kimi Agent Swarm</a></strong> &mdash; Agent swarm architecture &amp; technical deep-dive</li>
                <li><span class="tag tag-review">Research</span> <strong><a href="/findstocks/ai-research/kimi-motherload.html">Kimi AI</a></strong> &mdash; 23-algorithm inventory &amp; performance analysis</li>
                <li><span class="tag tag-review">Research</span> <strong><a href="/findstocks/ai-research/deepseek-motherload.html">DeepSeek V3.1 (671B)</a></strong> &mdash; Enhancement roadmap &amp; phased implementation</li>
                <li><span class="tag tag-review">Research</span> <strong><a href="/findstocks/ai-research/opus46-motherload.html">Opus 4.6 (Anthropic)</a></strong> &mdash; Zero-budget quant empire roadmap</li>
                <li><span class="tag tag-review">Research</span> <strong><a href="/findstocks/ai-research/grok-xai-motherload.html">Grok-4 (xAI)</a></strong> &mdash; Zero-budget quant arsenal &amp; code drafts</li>
                <li><span class="tag tag-review">Research</span> <strong><a href="/findstocks/ai-research/github-motherload.html">GitHub Copilot</a></strong> &mdash; Underdog vs. big players strategy</li>
                <li><span class="tag tag-review">Research</span> <strong><a href="/findstocks/ai-research/chatgpt-codex-motherload.html">ChatGPT Codex</a></strong> &mdash; Phased strategy roadmap</li>
            </ul>
            <p style="margin-top:0.75rem; color: #666688; font-size: 0.85rem;">All documents have been sanitized &mdash; security-sensitive information (database schemas, API keys, internal infrastructure) has been redacted.</p>
        </div>
    </div>

    '''

new_content = content[:comment] + new_section + content[comment:]

with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"\nSUCCESS! File size: {len(content)} -> {len(new_content)} chars")
