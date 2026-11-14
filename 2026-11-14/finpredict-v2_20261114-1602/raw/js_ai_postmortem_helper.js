/* <!-- AI POSTMORTEM HELPER --> */
/* Per-pick AI-postmortem prompt builder + localStorage save layer.
 * Used by /audit (template.html) and /audit/ai-tournament.html.
 *
 * Phase 1 (this file): manual-copy mode — user clicks "AI explain this",
 * sees a rendered prompt, copies it into a /consult-* slash command, then
 * pastes the model's response back into a textarea that is persisted to
 * localStorage under "_ai_postmortem_v1" keyed by pick_id.
 *
 * Phase 2 (TODO, NOT this PR): server-side ai_postmortem.json populated by
 * a GitHub Actions cron that consumes losing picks, calls the source AI's
 * API directly, and commits the response. When that exists, this client
 * should hydrate from `audit_dashboard/data/ai_postmortem.json` first and
 * fall back to localStorage for any pick not yet in the server file. See
 * the prompt template below for the exact contract; the cron just needs
 * to fill the same placeholders and write {pick_id: {prompt, response, model, ts}}.
 */
(function(){
  if (window._aiPostmortem) return; // idempotent — safe to include twice
  var LS_KEY = '_ai_postmortem_v1';
  var MAX_ENTRIES = 200;

  function loadAll(){
    try { return JSON.parse(localStorage.getItem(LS_KEY) || '{}') || {}; }
    catch(e){ return {}; }
  }
  function saveAll(obj){
    try {
      var keys = Object.keys(obj);
      if (keys.length > MAX_ENTRIES){
        // FIFO eviction: drop oldest by saved_at
        keys.sort(function(a,b){ return (obj[a].saved_at||0) - (obj[b].saved_at||0); });
        var drop = keys.length - MAX_ENTRIES;
        for (var i=0;i<drop;i++) delete obj[keys[i]];
      }
      localStorage.setItem(LS_KEY, JSON.stringify(obj));
      return true;
    } catch(e){ return false; }
  }
  function pickId(p){
    if (!p) return '';
    return p.pick_id || p.id || ((p.symbol||'?') + '_' + (p.source_system || p.model_id || '?') + '_' + (p.submitted_at || p.created_at || ''));
  }
  function get(pId){ return loadAll()[pId] || null; }
  function set(pId, data){
    var all = loadAll();
    all[pId] = Object.assign({}, all[pId]||{}, data, { saved_at: Date.now() });
    return saveAll(all);
  }
  function remove(pId){ var all = loadAll(); delete all[pId]; return saveAll(all); }

  function fmtPct(v){
    if (v == null || isNaN(v)) return 'n/a';
    return (v >= 0 ? '+' : '') + Number(v).toFixed(2) + '%';
  }
  function fmtN(v, d){
    if (v == null || isNaN(v)) return 'n/a';
    return Number(v).toFixed(d == null ? 2 : d);
  }

  function isRiskyWinner(p){
    if (!p) return false;
    var pnl = Number(p.pnl_pct || 0);
    if (pnl <= 0) return false;
    var planned = Number(p.rr_ratio || p.planned_rr || 0);
    var realized = Number(p.realized_rr || 0);
    if (planned > 0 && realized > 0 && realized < 0.5 * planned) return true;
    var mdd = Number(p.max_drawdown_during_trade || p.recent_max_dd || 0);
    if (mdd > 0 && mdd > 2 * pnl) return true;
    return false;
  }

  function classifyOutcome(p){
    var s = String(p.status || '').toUpperCase();
    if (s === 'WIN' || (p.pnl_pct != null && p.pnl_pct > 0 && s !== 'OPEN')) return 'WIN';
    if (s === 'LOSS' || (p.pnl_pct != null && p.pnl_pct < 0 && s !== 'OPEN')) return 'LOSS';
    return 'STILL_OPEN';
  }

  function buildPrompt(p){
    if (!p) return '';
    var srcName = p.source_ai_name || p.model_id || p.source_system || 'this AI';
    var pickDate = p.submitted_at || p.created_at || p.timestamp || 'unknown date';
    var convBand = p.conviction_band || p.tier || p.trust_tier ||
                   (p.confidence != null ? (p.confidence >= 0.75 ? 'HIGH' : p.confidence >= 0.5 ? 'MED' : 'LOW') : 'UNKNOWN');
    var strategy = p.strategy || p.strategy_name || 'unknown strategy';
    var conf = fmtN(p.confidence, 2);
    var es = fmtN(p.elite_score != null ? p.elite_score : p.score, 1);
    var ts = fmtN(p.trust_score, 1);
    var outcome = classifyOutcome(p);
    var pnl = fmtPct(p.pnl_pct);
    var actualRR = fmtN(p.realized_rr, 2);
    var plannedRR = fmtN(p.rr_ratio || p.planned_rr, 2);
    var N = p.strat_fwd_trades != null ? p.strat_fwd_trades : (p.forward_trades != null ? p.forward_trades : 'n/a');
    var WR = p.strat_fwd_wr != null ? (Number(p.strat_fwd_wr).toFixed(1) + '%') : 'n/a';
    var PF = p.strat_fwd_pf != null ? Number(p.strat_fwd_pf).toFixed(2) : 'n/a';
    var WRh = p.strat_fwd_wr_holdout != null ? (Number(p.strat_fwd_wr_holdout).toFixed(1) + '%') : 'n/a';
    var PFh = p.strat_fwd_pf_holdout != null ? Number(p.strat_fwd_pf_holdout).toFixed(2) : 'n/a';
    var edgePersists = (p.strat_fwd_wr != null && p.strat_fwd_wr_holdout != null)
      ? (Number(p.strat_fwd_wr_holdout) >= 0.9 * Number(p.strat_fwd_wr) ? 'Y' : 'N')
      : '?';
    var regime = p.regime_at_entry || p.market_regime || (window._marketRegime || 'unknown');
    var trend = p.btc_trend || p.market_trend || 'unknown';
    var vix = p.vix_at_entry != null ? Number(p.vix_at_entry).toFixed(1) : 'n/a';
    var breadth = p.breadth_at_entry || p.market_breadth || 'n/a';

    // Same-side / opposite-side AIs — best-effort lookup against window data
    var sameSide = [], oppSide = [];
    try {
      var dir = String(p.direction || '').toUpperCase();
      var sym = String(p.symbol || '').toUpperCase();
      var pool = (window._renderedPicks || window.allPicks || []);
      pool.forEach(function(q){
        if (!q || q === p) return;
        if (String(q.symbol||'').toUpperCase() !== sym) return;
        var qd = String(q.direction||'').toUpperCase();
        var qn = q.source_ai_name || q.model_id || q.source_system;
        if (!qn) return;
        if (qd === dir) { if (sameSide.indexOf(qn) === -1) sameSide.push(qn); }
        else if (qd) { if (oppSide.indexOf(qn) === -1) oppSide.push(qn); }
      });
    } catch(e){}
    var sameSideStr = sameSide.length ? sameSide.slice(0,8).join(', ') : 'none on record';
    var oppSideStr  = oppSide.length  ? oppSide.slice(0,8).join(', ')  : 'none on record';

    return ''
      + 'ROLE: you are ' + srcName + '. On ' + pickDate + ', you emitted this pick as a\n'
      + '"' + convBand + '" call backed by your "' + strategy + '" strategy with claimed\n'
      + 'statistical edge (confidence=' + conf + ', elite_score=' + es + ', trust_score=' + ts + ').\n\n'
      + 'OUTCOME: ' + outcome + ' · realized PnL: ' + pnl + ' ·\n'
      + 'realized R:R: ' + actualRR + ' vs planned ' + plannedRR + '.\n\n'
      + 'YOUR HISTORICAL TRACK ON THIS SLICE:\n'
      + '- Same strategy × same asset_class × same conf-band: n=' + N + ', WR=' + WR + ', PF=' + PF + '\n'
      + '- Holdout (last 40%): WR=' + WRh + ', PF=' + PFh + ' ← edge persisted? ' + edgePersists + '\n\n'
      + 'CONTEXT AT PICK TIME:\n'
      + '- Regime: ' + regime + ', BTC trend: ' + trend + ', VIX: ' + vix + ', breadth: ' + breadth + '\n'
      + '- Other AIs that also took the same side: ' + sameSideStr + '\n'
      + '- AIs that took the OPPOSITE side: ' + oppSideStr + '\n\n'
      + 'QUESTION: explain in <=200 words:\n'
      + '1. Why did your model emit this pick?\n'
      + '2. If LOSS: which assumption broke? (regime, factor exposure, news,\n'
      + '   liquidity, microstructure, your own model drift)\n'
      + '3. If WIN-but-risky: was the realized R:R worse than planned? if so why?\n'
      + '4. What ONE filter would have prevented this exact failure mode?\n'
      + '   (cite a concrete gate threshold change)';
  }

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  function renderSection(p){
    var pId = pickId(p);
    var prompt = buildPrompt(p);
    var saved = get(pId) || {};
    var slashCmds = ['/consult-grok','/consult-cursor-agent','/consult-gemini','/consult-ring','/consult-codex','/consult-opencode'];
    var promptId = 'aipm-prompt-' + Math.random().toString(36).slice(2,8);
    var respId = 'aipm-resp-' + Math.random().toString(36).slice(2,8);
    var savedId = 'aipm-saved-' + Math.random().toString(36).slice(2,8);
    var isRisky = isRiskyWinner(p);
    var outcome = classifyOutcome(p);
    var badge = outcome === 'LOSS' ? '<span style="background:#ef444433;color:#ef4444;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:700">LOSS</span>'
             : isRisky            ? '<span style="background:#f59e0b33;color:#f59e0b;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:700">RISKY WIN</span>'
             : outcome === 'WIN'  ? '<span style="background:#22c55e33;color:#22c55e;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:700">WIN</span>'
             : '<span style="background:#3b82f633;color:#3b82f6;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:700">OPEN</span>';
    var savedBlock = saved && saved.response
      ? '<div id="' + savedId + '" style="margin-top:8px;padding:8px;background:#0f172a;border-left:3px solid #22c55e;border-radius:4px;font-size:11px;color:#cbd5e1;white-space:pre-wrap">'
        + '<div style="font-size:10px;color:#22c55e;font-weight:700;margin-bottom:4px">Saved postmortem (' + new Date(saved.saved_at||0).toLocaleString() + ')</div>'
        + esc(saved.response)
        + '<div style="margin-top:4px;text-align:right"><button data-aipm-clear="' + esc(pId) + '" style="background:transparent;border:1px solid #475569;color:#94a3b8;border-radius:3px;padding:2px 8px;cursor:pointer;font-size:10px">Clear</button></div>'
        + '</div>'
      : '<div id="' + savedId + '" style="display:none"></div>';

    return ''
      + '<div style="padding:14px 20px;border-top:1px solid #1e293b;background:#0b1220">'
      + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
      +   '<div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:1px">AI Postmortem Prompt</div>'
      +   badge
      + '</div>'
      + '<div style="font-size:10px;color:#94a3b8;margin-bottom:6px">Copy the prompt below, paste into one of these slash commands, then paste the model\'s answer back. <span style="color:#64748b">(Saved locally in this browser, max ' + MAX_ENTRIES + ' postmortems.)</span></div>'
      + '<div style="font-size:10px;color:#94a3b8;margin-bottom:6px">Suggested: '
      +   slashCmds.map(function(c){ return '<code style="background:#1e293b;color:#a78bfa;padding:1px 4px;border-radius:3px;font-size:10px">' + c + '</code>'; }).join(' ')
      + '</div>'
      + '<textarea id="' + promptId + '" readonly style="width:100%;min-height:180px;background:#0f172a;border:1px solid #334155;color:#cbd5e1;font-family:ui-monospace,Menlo,monospace;font-size:11px;padding:8px;border-radius:4px;box-sizing:border-box">' + esc(prompt) + '</textarea>'
      + '<div style="margin-top:6px;text-align:right">'
      +   '<button data-aipm-copy="' + promptId + '" style="background:#3b82f6;color:#fff;border:none;border-radius:4px;padding:4px 12px;cursor:pointer;font-size:11px">Copy to clipboard</button>'
      + '</div>'
      + '<div style="margin-top:10px;font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:1px">Paste the AI\'s response here</div>'
      + '<textarea id="' + respId + '" placeholder="Paste the model\'s 200-word answer here, then Save..." style="width:100%;min-height:100px;margin-top:4px;background:#0f172a;border:1px solid #334155;color:#cbd5e1;font-family:ui-monospace,Menlo,monospace;font-size:11px;padding:8px;border-radius:4px;box-sizing:border-box">' + esc(saved && saved.response || '') + '</textarea>'
      + '<div style="margin-top:6px;text-align:right">'
      +   '<button data-aipm-save="' + esc(pId) + '" data-aipm-resp-id="' + respId + '" data-aipm-saved-id="' + savedId + '" style="background:#22c55e;color:#0f172a;border:none;border-radius:4px;padding:4px 12px;cursor:pointer;font-size:11px;font-weight:700">Save</button>'
      + '</div>'
      + savedBlock
      + '</div>';
  }

  // Delegated handlers — wired once.
  document.addEventListener('click', function(ev){
    var t = ev.target;
    if (!t || !t.getAttribute) return;
    var copyId = t.getAttribute('data-aipm-copy');
    if (copyId){
      var el = document.getElementById(copyId);
      if (el){
        try {
          el.select(); document.execCommand('copy');
          var orig = t.textContent; t.textContent = 'Copied!';
          setTimeout(function(){ t.textContent = orig; }, 1500);
        } catch(e){}
      }
      ev.stopPropagation(); return;
    }
    var savePid = t.getAttribute('data-aipm-save');
    if (savePid){
      var respEl = document.getElementById(t.getAttribute('data-aipm-resp-id'));
      var savedEl = document.getElementById(t.getAttribute('data-aipm-saved-id'));
      if (respEl){
        var v = String(respEl.value || '').trim();
        if (!v){ t.textContent = '(empty)'; setTimeout(function(){ t.textContent = 'Save'; }, 1200); return; }
        var ok = set(savePid, { response: v, prompt_preview: 'see modal' });
        var orig = t.textContent;
        t.textContent = ok ? 'Saved' : 'Save failed';
        setTimeout(function(){ t.textContent = orig; }, 1500);
        if (ok && savedEl){
          savedEl.style.display = 'block';
          savedEl.innerHTML = '<div style="font-size:10px;color:#22c55e;font-weight:700;margin-bottom:4px">Saved postmortem (' + new Date().toLocaleString() + ')</div>'
            + esc(v)
            + '<div style="margin-top:4px;text-align:right"><button data-aipm-clear="' + esc(savePid) + '" style="background:transparent;border:1px solid #475569;color:#94a3b8;border-radius:3px;padding:2px 8px;cursor:pointer;font-size:10px">Clear</button></div>';
        }
      }
      ev.stopPropagation(); return;
    }
    var clearPid = t.getAttribute('data-aipm-clear');
    if (clearPid){
      remove(clearPid);
      var holder = t.closest('div[id^="aipm-saved-"]') || t.parentElement && t.parentElement.parentElement;
      if (holder){ holder.style.display = 'none'; holder.innerHTML = ''; }
      ev.stopPropagation(); return;
    }
    // "AI explain this" inline button on ai-tournament rows
    var aitBtn = t.getAttribute && t.getAttribute('data-aipm-explain');
    if (aitBtn){
      var p = null;
      try {
        if (window.allPicks){
          p = window.allPicks.find(function(q){ return pickId(q) === aitBtn; });
        }
      } catch(e){}
      if (!p){ return; }
      var existing = document.getElementById('aipm-modal');
      if (existing) existing.remove();
      var modal = document.createElement('div');
      modal.id = 'aipm-modal';
      modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:9999;overflow-y:auto;padding:40px 20px;box-sizing:border-box';
      modal.innerHTML = '<div style="max-width:760px;margin:0 auto;background:#0f172a;border:1px solid #334155;border-radius:12px;color:#e2e8f0">'
        + '<div style="padding:12px 20px;border-bottom:1px solid #1e293b;display:flex;justify-content:space-between;align-items:center">'
        +   '<div style="font-weight:700">AI Postmortem &middot; ' + esc(p.symbol||'?') + ' ' + esc(p.direction||'') + '</div>'
        +   '<button id="aipm-modal-close" style="background:#334155;color:#94a3b8;border:none;border-radius:4px;padding:4px 10px;cursor:pointer">Close</button>'
        + '</div>'
        + renderSection(p)
        + '</div>';
      modal.addEventListener('click', function(e){ if (e.target === modal) modal.remove(); });
      document.body.appendChild(modal);
      var cb = document.getElementById('aipm-modal-close');
      if (cb) cb.onclick = function(){ modal.remove(); };
      ev.stopPropagation();
    }
  });

  window._aiPostmortem = {
    LS_KEY: LS_KEY,
    MAX_ENTRIES: MAX_ENTRIES,
    pickId: pickId,
    buildPrompt: buildPrompt,
    isRiskyWinner: isRiskyWinner,
    classifyOutcome: classifyOutcome,
    renderSection: renderSection,
    get: get, set: set, remove: remove, loadAll: loadAll
  };
})();
