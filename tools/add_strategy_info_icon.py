#!/usr/bin/env python3
"""Add info icon + strategy description tooltip to the active picks table strategy column."""

import re

filepath = "audit_dashboard/template.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add CSS for the info icon (insert after existing .strat-tip styles)
css_anchor = ".strat-tip .tip-no-data { color: var(--text-dim); font-style: italic; text-align: center; padding: 8px 0; }\n"
css_new = css_anchor + """
.strat-info-icon { display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; border-radius: 50%; background: rgba(139,92,246,0.18); border: 1px solid rgba(139,92,246,0.35); color: var(--purple); font-size: 8px; font-weight: 700; cursor: help; flex-shrink: 0; transition: background 0.15s; }
.strat-info-icon:hover { background: rgba(139,92,246,0.35); }
.strat-tip .tip-desc { font-size: 11px; color: var(--text-dim); line-height: 1.5; }
"""

if css_anchor not in content:
    print("ERROR: CSS anchor not found")
    import sys; sys.exit(1)

content = content.replace(css_anchor, css_new, 1)
print("CSS for .strat-info-icon added")

# 2. Replace the strategy column in the active picks table (line ~10523)
# OLD: plain text with native title tooltip
# NEW: strat-tip-wrap with ℹ icon and rich description tooltip

old_strategy_td = """html += '<td style="padding:8px 10px;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + esc(p.strategy || '') + '">' + esc(p.strategy || '?') + '</td>';"""

new_strategy_td = """var _sn = esc(p.strategy || '?').replace(/_/g, ' ');
    var _sd = _lookupMappedDescription(p.strategy || '', [_STRATEGY_DESCRIPTIONS]);
    html += '<td style="padding:8px 10px;max-width:280px"><span class="strat-tip-wrap" style="display:inline-flex;align-items:center;gap:4px;max-width:270px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + _sn + (_sd ? '<span class="strat-info-icon">\\u2139</span><div class="strat-tip"><div class="tip-title">' + _sn + '</div><div class="tip-divider"></div><div class="tip-desc">' + esc(_sd) + '</div></div>' : '') + '</span></td>';"""

if old_strategy_td not in content:
    print("ERROR: Strategy TD anchor not found!")
    import sys; sys.exit(1)

content = content.replace(old_strategy_td, new_strategy_td, 1)
print("Strategy column replaced with info icon + description tooltip")

# 3. Also add description tooltip to the Score Report strategy column (line ~10132)
# which already uses stratTooltipHtml but could show the description more prominently
# We'll add the description as a subtitle under the tip-title in the stratTooltipHtml fallback
# This is the fallback block at line ~5906 where _strategyTooltipNarrative is used

# Find the fallback tooltip section where blurb is shown
old_blurb_section = """  if (typeof _strategyTooltipNarrative === 'function' && typeof _humanizeExportKey === 'function') {
    var blurb = _strategyTooltipNarrative(stratName);
    var humB = _humanizeExportKey(stratName);
    if (blurb && blurb !== humB) {
      h += '<div class="tip-divider"></div><div style="font-size:11px;color:var(--text-dim);font-style:italic">' + esc(blurb) + '</div>';
    }
  }"""

new_blurb_section = """  // Show _STRATEGY_DESCRIPTIONS as primary description in tooltip
  var _sdTip = _lookupMappedDescription(stratName || '', [_STRATEGY_DESCRIPTIONS]);
  if (_sdTip) {
    h += '<div class="tip-divider"></div><div class="tip-desc">' + esc(_sdTip) + '</div>';
  }
  // Also show _strategyTooltipNarrative if available and different
  if (typeof _strategyTooltipNarrative === 'function' && typeof _humanizeExportKey === 'function') {
    var blurb = _strategyTooltipNarrative(stratName);
    var humB = _humanizeExportKey(stratName);
    if (blurb && blurb !== humB && blurb !== _sdTip) {
      h += '<div style="font-size:10px;color:var(--text-dim);font-style:italic;margin-top:4px">' + esc(blurb) + '</div>';
    }
  }"""

if old_blurb_section in content:
    content = content.replace(old_blurb_section, new_blurb_section, 1)
    print("Score Report tooltip enhanced with _STRATEGY_DESCRIPTIONS")
else:
    # Try alternate match — the code might have slightly different whitespace
    # Let's search more flexibly
    blurb_pattern = r"if \(typeof _strategyTooltipNarrative === 'function' && typeof _humanizeExportKey === 'function'\) \{\s*var blurb = _strategyTooltipNarrative\(stratName\);\s*var humB = _humanizeExportKey\(stratName\);\s*if \(blurb && blurb !== humB\) \{\s*h \+= '<div class=\"tip-divider\"></div><div style=\"font-size:11px;color:var\(--text-dim\);font-style:italic\">' \+ esc\(blurb\) \+ '</div>';\s*\}\s*\}"
    match = re.search(blurb_pattern, content)
    if match:
        content = content[:match.start()] + new_blurb_section + content[match.end():]
        print("Score Report tooltip enhanced with _STRATEGY_DESCRIPTIONS (via regex)")
    else:
        print("WARNING: Could not find blurb section for Score Report enhancement — skipping")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("\nDone! Changes:")
print("  1. Added .strat-info-icon CSS")
print("  2. Replaced active picks strategy column with info icon + description tooltip")
print("  3. Enhanced Score Report tooltip to show _STRATEGY_DESCRIPTIONS")
