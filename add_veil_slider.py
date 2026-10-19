import re, sys

path = '/home/eaguiar2015/findtorontoevents_antigravity.ca/.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add CSS variable :root
# Find the :root block (lines after <style>)
# We'll insert after the opening :root { line, before the first property.
# Simpler: insert after the closing } of :root? Actually we can add at end of :root block.
# Let's find the :root block and add after its closing brace.
# We'll use regex to find :root { ... } and insert before the closing brace.
def add_var_to_root(match):
    inner = match.group(1)
    # Insert before the closing brace
    return f':root {{\n{inner}  --veil-opacity: 0.4;\n}}'
# Pattern to capture :root {
content = re.sub(r':root\s*\{\n([^}]*)\n\}', add_var_to_root, content, flags=re.DOTALL)

# 2. Replace .bg-veil block
new_veil = '''.bg-veil {
    position: fixed;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background: rgba(0,0,0, var(--veil-opacity));
}'''
content = re.sub(r'\.bg-veil\s*\{[^}]+\}', new_veil, content, flags=re.DOTALL)

# 3. Insert slider HTML after the background divs but before skip-link.
# Find the position after the five divs.
# We'll locate the closing </div> of the last bg-veil? Actually the divs are:
#   <div class="bg-scene"></div>
#   <div class="bg-aurora"></div>
#   <div class="bg-orbit"></div>
#   <div class="bg-grain"></div>
#   <div class="bg-veil"></div>
# Then there is a newline and the skip-link.
# We'll insert after the </div> of bg-veil.
# Let's find the index of '</div>' after the veils, but easier: insert right after the string '</div>\n\n  <a class="skip-link"'
# We'll replace that occurrence with '</div>\n\n  <div id=\"veil-slider-container\"...>\n\n  <a class=\"skip-link\"'
slider_html = '''  <div id="veil-slider-container" style="position:fixed; top:10px; right:10px; z-index:1000; background:rgba(0,0,0,0.5); padding:10px; border-radius:5px; color:#fff; font-family:sans-serif;">
    <label>Veil opacity: <span id="veil-value">0.4</span></label><br>
    <input type="range" id="veil-slider" min="0" max="1" step="0.01" value="0.4">
  </div>'''
# Find pattern: '</div>\n\n  <a class="skip-link"'
pattern = r'\)(</div>\n\n\s*<a class=\"skip-link\")'
# We'll do a simple replace.
if '</div>\n\n  <a class="skip-link"' in content:
    content = content.replace('</div>\n\n  <a class="skip-link"',
                              f'</div>\n\n{slider_html}\n\n  <a class="skip-link"')
else:
    # fallback: insert after the last </div> before skip-link
    # locate the last </div> before the skip-link
    import re
    # find all </div> positions
    matches = list(re.finditer(r'</div>', content))
    if matches:
        last = matches[-1]
        pos = last.end()
        content = content[:pos] + f'\n\n{slider_html}' + content[pos:]

# 4. Insert JS before </body>
js_script = '''
  <script>
    const slider = document.getElementById('veil-slider');
    const valueSpan = document.getElementById('veil-value');
    const root = document.documentElement;
    function update() {
      const val = parseFloat(slider.value);
      valueSpan.textContent = val.toFixed(2);
      root.style.setProperty('--veil-opacity', val);
    }
    slider.addEventListener('input', update);
    // Initialize
    update();
  </script>'''
# Insert before </body>
if '</body>' in content:
    content = content.replace('</body>', f'{js_script}\n</body>')
else:
    # fallback: append at end
    content = content + js_script

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated CIS-VR index.html with veil opacity slider')