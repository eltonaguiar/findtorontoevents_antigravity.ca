import re, sys

# Mapping of variable to hardcoded value from javascript page
VAR_MAP = {
    '--panel-border': 'rgba(255,255,255,0.08)',
    '--text': '#e6edf6',
    '--muted': '#8b98ac',
    '--accent': '#62f5c7',
    '--accent-2': '#7aa2ff',
    '--bg': '#080c14',  # not used directly but for reference
}

def replace_vars(css):
    # Replace var(--xxx) with mapping, also handle fallback? Not needed.
    def repl(match):
        var_name = match.group(1)
        if var_name in VAR_MAP:
            return VAR_MAP[var_name]
        # If not found, return original (should not happen)
        return match.group(0)
    return re.sub(r'var\(\s*([a-zA-Z0-9_-]+)\s*\)', repl, css)

def get_sn_lnav_css():
    # Extract from javascript file
    js_path = '/home/eaguiar2015/findtorontoevents_antigravity.ca/findtorontoevents.ca/servicenow/javascript/index.html'
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Find the CSS block for .sn-lnav and related selectors.
    # We'll extract from line starting with '.sn-lnav {' until we hit a line that is not part of the rule set?
    # Simpler: extract between '.sn-lnav {' and the next '}. That's tricky due to nesting.
    # Instead we'll take a known range: from line 82 to line 130 (as earlier).
    lines = content.splitlines()
    start = 81  # zero-indexed line 82
    end = 130   # exclusive
    snippet = '\n'.join(lines[start:end])
    return snippet

def inject_css_into_style(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Find <style> tag
    style_match = re.search(r'(<style[^>]*>)(.*?)(</style>)', content, re.DOTALL)
    if not style_match:
        print(f'No <style> tag found in {html_path}')
        return False
    style_open, css, style_close = style_match.groups()
    sn_lnav_css = get_sn_lnav_css()
    sn_lnav_css = replace_vars(sn_lnav_css)
    # Check if already present (simple check)
    if '.sn-lnav {' in css:
        print(f'.sn-lnav CSS already present in {html_path}')
        # Optionally we could replace, but we'll skip.
        return True
    # Insert before </style>
    new_css = css + '\n\n' + sn_lnav_css
    new_content = content[:style_match.start(1)] + style_open + new_css + style_close + content[style_match.end(3):]
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f' injected .sn-lnav CSS into {html_path}')
    return True

files = [
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/findtorontoevents.ca/CIS-CSM/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/findtorontoevents.ca/servicenow/javascript/index.html',
]

for f in files:
    inject_css_into_style(f)