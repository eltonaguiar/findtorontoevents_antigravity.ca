"""Apply performance patches to audit_dashboard/index.html (same as template.html).
Index is huge; run after editing template or standalone."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "audit_dashboard" / "index.html"
s = p.read_text(encoding="utf-8", errors="replace")

# Built index.html has inlined window.DASHBOARD_DATA = {...}; then sync loader + const D.
old_start = s.find("// Always try to load external JSON")
if old_start < 0:
    raise SystemExit("sync-loader comment missing (// Always try to load external JSON)")
old_end = s.find("const D = window.DASHBOARD_DATA || {};", old_start)
if old_end < 0:
    raise SystemExit("const D marker missing")
old_end += len("const D = window.DASHBOARD_DATA || {};")

NEW_BLOCK = r"""// External data/dashboard_data.json is loaded in init() via async fetch only.
// Sync XHR was removed: it blocked the main thread for seconds on large JSON (mobile "page unresponsive").
let D = window.DASHBOARD_DATA || {};

async function loadExternalDashboardDataIfFresher() {
  try {
    var r = await fetch('data/dashboard_data.json?' + Date.now(), { cache: 'no-store' });
    if (!r.ok) return;
    var _ext = await r.json();
    if (!_ext || !_ext.generated_at) return;
    var _embedded = D;
    var _extActive = ((_ext.picks || {}).active || []).length;
    var _embActive = ((_embedded.picks || {}).active || []).length;
    if (!_embedded || !_embedded.generated_at || _ext.generated_at > _embedded.generated_at || _extActive > _embActive) {
      window.DASHBOARD_DATA = _ext;
      D = _ext;
      console.log('[Audit] Using external data (' + _extActive + ' active picks, generated ' + new Date(_ext.generated_at).toLocaleString('en-US', {timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',hour12:true}) + ' EST)');
    } else {
      console.log('[Audit] Using embedded data (' + _embActive + ' active picks, generated ' + new Date(_embedded.generated_at).toLocaleString('en-US', {timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',hour12:true}) + ' EST)');
    }
  } catch (e) {
    console.warn('[Audit] External data/dashboard_data.json fetch failed:', e.message);
  }
  window.DASHBOARD_DATA = D;
}

function yieldToMain() {
  return new Promise(function(resolve) {
    if (typeof requestAnimationFrame === 'function') {
      requestAnimationFrame(function() { setTimeout(resolve, 0); });
    } else {
      setTimeout(resolve, 0);
    }
  });
}"""

s = s[:old_start] + NEW_BLOCK + s[old_end:]

s = s.replace(
    "async function init() {\n  // Pre-fetch regime_flip_detector",
    "async function init() {\n  await loadExternalDashboardDataIfFresher();\n\n  // Pre-fetch regime_flip_detector",
    1,
)

OLD_R = """  renderPicks();
  renderVerifiedAlpha();
  // Fetch live prices and update PnL after initial render
  fetchLivePrices();
  renderPortfolios();
  renderClaudePortfolios();
  renderClaudeTopPicks();
  renderAIBattle();
  renderDashboards();
  renderSystems();
  renderBtVsFwd();
  renderLeaderboard();
  renderBundles();
  renderPermutations();
  renderPerformance();
  renderAuditLog();
  renderMLHealth();"""

NEW_R = """  renderPicks();
  renderVerifiedAlpha();
  // Fetch live prices and update PnL after initial render
  fetchLivePrices();
  await yieldToMain();

  renderPortfolios();
  renderClaudePortfolios();
  renderClaudeTopPicks();
  renderAIBattle();
  await yieldToMain();

  renderDashboards();
  renderSystems();
  renderBtVsFwd();
  renderLeaderboard();
  renderBundles();
  renderPermutations();
  await yieldToMain();

  renderPerformance();
  renderAuditLog();
  renderMLHealth();"""

if OLD_R not in s:
    raise SystemExit("render batch block missing")
s = s.replace(OLD_R, NEW_R, 1)

s = s.replace("init();\n</script>", "setTimeout(function() { init(); }, 0);\n</script>", 1)

OLD_DOM_START = """// Add export buttons + sortable headers + column filters to all major tables
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('table').forEach((table, idx) => {
        if (table.querySelectorAll('tr').length < 3) return;"""

NEW_DOM_START = """// Add export buttons + sortable headers + column filters (deferred: avoids blocking main thread with init())
function auditEnhanceAllTables() {
    document.querySelectorAll('table').forEach((table, idx) => {
        if (table.dataset.auditTableEnhanced === '1') return;
        if (table.querySelectorAll('tr').length < 3) return;"""

if OLD_DOM_START not in s:
    raise SystemExit("DOM block start missing")
s = s.replace(OLD_DOM_START, NEW_DOM_START, 1)

OLD_DOM_END = """        } else if (headers[0]?.parentElement) {
            headers[0].parentElement.parentElement.insertBefore(filterRow, headers[0].parentElement.nextSibling);
        }
    });
});
</script>"""

NEW_DOM_END = """        } else if (headers[0]?.parentElement) {
            headers[0].parentElement.parentElement.insertBefore(filterRow, headers[0].parentElement.nextSibling);
        }
        table.dataset.auditTableEnhanced = '1';
    });
}

document.addEventListener('DOMContentLoaded', function() {
    function scheduleEnhance() {
        if (typeof requestIdleCallback !== 'undefined') {
            requestIdleCallback(function() { auditEnhanceAllTables(); }, { timeout: 4000 });
        } else {
            setTimeout(auditEnhanceAllTables, 800);
        }
    }
    scheduleEnhance();
    setTimeout(auditEnhanceAllTables, 3500);
});
</script>"""

if OLD_DOM_END not in s:
    raise SystemExit("DOM block end missing")
s = s.replace(OLD_DOM_END, NEW_DOM_END, 1)

p.write_text(s, encoding="utf-8")
print("OK:", p)
