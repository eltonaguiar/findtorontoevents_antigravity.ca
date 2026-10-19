import re, sys, os

def update_toc_pane(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find <style> tag
    style_match = re.search(r'(<style[^>]*>)(.*?)(</style>)', content, re.DOTALL)
    if not style_match:
        print(f'No <style> tag found in {html_path}')
        return False
    style_open, css, style_close = style_match.groups()
    
    # New .toc rule
    new_toc_rule = '''.toc {
  position: sticky;
  top: 24px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 6px 18px rgba(20,47,57,0.04);
  padding: 16px;
  max-height: calc(100vh - 80px);
  overflow-y: auto;
}
.toc h2 {
  margin: 0 0 0.65rem;
  font-size: 1rem;
  color: var(--muted);
}
.toc ol { margin: 0; padding-left: 1.3rem; }
.toc li { padding: 0.18rem 0; font-size: 0.91rem; }
.toc a { text-decoration: none; }'''
    
    # Replace the standalone .toc block (preceded by newline)
    # Pattern: \n\s*\.toc\s*\{[^}]*\}
    # We'll do a balanced brace replacement for safety
    def replace_standalone_toc(css_text):
        # Find pattern: newline, optional spaces, .toc, optional whitespace, {
        import re
        # We'll iterate through the string to find the pattern
        pattern = re.compile(r'\n\s*\.toc\s*\{')
        match = pattern.search(css_text)
        if not match:
            return css_text
        start = match.start()  # position of newline
        # Find matching closing brace
        brace_start = match.end() - 1  # position of {
        depth = 0
        i = brace_start
        while i < len(css_text):
            if css_text[i] == '{':
                depth += 1
            elif css_text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1  # include closing brace
                    break
            i += 1
        else:
            return css_text
        # Replace from start to end with newline + new_toc_rule
        # Keep the newline before .toc? We'll keep the newline as part of start.
        return css_text[:start] + '\n' + new_toc_rule + css_text[end:]
    
    new_css = replace_standalone_toc(css)
    
    # If no replacement made (maybe .toc not preceded by newline), try another pattern
    if new_css == css:
        # Try to replace any .toc { ... } block that is not part of a list
        # Simpler: replace all occurrences of .toc { ... } with our rule, but avoid the combined selector.
        # We'll just append our rule after the combined selector block.
        # Find the combined selector block: \.toc, article, .course-card, .concept, .checklist
        combined_pattern = re.compile(r'\.toc,\s*article,\s*\.course-card,\s*\.concept,\s*\.checklist\s*\{[^}]*\}')
        match = combined_pattern.search(css)
        if match:
            # Insert after this block
            pos = match.end()
            new_css = css[:pos] + '\n\n' + new_toc_rule + css[pos:]
        else:
            # Fallback: append before </style>
            new_css = css + '\n\n' + new_toc_rule
    
    new_content = content[:style_match.start(1)] + style_open + new_css + style_close + content[style_match.end(3):]
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'Updated TOC pane in {html_path}')
    return True

files = [
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/findtorontoevents.ca/CIS-CSM/index.html',
    '/home/eaguiar2015/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html'
]

for f in files:
    if os.path.exists(f):
        update_toc_pane(f)
    else:
        print(f'File not found: {f}')