"use strict";
/* audit2 — candidate & methodology library.
   Live numbers come from audit3_ledger.json; the pod registry is a static
   snapshot (reports/ is not web-served). Generated 2026-11-19. */

var PODS = [
  {id:"POD-EQUITY-BREAKOUT", status:"pre_registered", hypothesis:"H-BABY-EQUITY-VT-PATTERN-SWEEP-001", klass:"EQUITY / ETF", dir:"LONG",
   evidence:"EQUITY OOS Sharpe +0.61 (33 folds), ETF +0.21 (53 folds); ~364 resolved trades net +0.46%.",
   gate:"n>=100 forward, net CI-LB>0 at 2x slippage, IR>=0.5 vs a matched SPY leg, split-half stable."},
  {id:"POD-CRYPTO-VWAP-REVERSION", status:"observe", hypothesis:"H-2026-11-19-01", klass:"CRYPTO", dir:"LONG",
   evidence:"Lab OOS 516/953, Sharpe 3.10, DSR 21.4, PBO 0.18 — CONTESTED: a 1-bar execution lag drops PF to 0.957 and CSCV PBO to 0.84-0.97.",
   gate:"Promote only after a lagged-entry + intrabar-stop replay clears the acceptance criteria."},
  {id:"POD-CRYPTO-BOLLINGER-MR", status:"observe", hypothesis:"H-2026-11-19-02", klass:"CRYPTO", dir:"LONG",
   evidence:"OOS 38 trades, PF 1.673, Sharpe 1.376; n below the 100 floor.",
   gate:"n>=100 forward rows."},
  {id:"POD-FABER-TAA", status:"observe", hypothesis:"H-2026-11-19-03", klass:"EQUITY / ETF", dir:"LONG",
   evidence:"FaberTAA SPY n=11 Sharpe 1.743; QQQ n=7 Sharpe 1.652; the forward pilot has 0 ETF closes.",
   gate:"n>=100 forward rows."},
  {id:"POD-FOREX-USDJPY-MOMENTUM", status:"observe", hypothesis:"H-2026-11-19-04", klass:"FOREX", dir:"LONG",
   evidence:"FXMom USDJPY n=42, Sharpe 2.018, MC p=0.48; FX data blocker (fx_prices stale to 2026-02-09).",
   gate:"Backfill the FX price history, then n>=100 forward rows."},
  {id:"POD-COMMODITY-ROLL-YIELD", status:"observe", hypothesis:"H-2026-11-19-05", klass:"COMMODITY", dir:"LONG / SHORT",
   evidence:"Academic factor (Erb-Harvey / Gorton-Rouwenhorst); the in-repo emitter is dormant (0 rows).",
   gate:"Needs a second-nearby contract feed before it can emit."}
];

var MEASURES = [
  ["DSR (Deflated Sharpe Ratio)","Sharpe deflated by the number of trials / effective N — the honest 'did we overfit' score."],
  ["PBO (Probability of Backtest Overfitting)","Probability the 'best' backtest is a fluke across the tried configurations."],
  ["SPA (Superior Predictive Ability)","Multiple-testing-corrected out-of-sample comparison against a benchmark."],
  ["FDR / Benjamini-Hochberg","False-discovery control across the cells tested in a family."],
  ["Wilson CI","Binomial confidence interval for a win rate; never claims certainty on tiny n."],
  ["Bootstrap net-expectancy CI","2,000 seeded resamples of per-trade net return; the primary edge test (G2)."],
  ["Selection alpha (M1b)","Pick net return minus direction-adjusted buy-and-hold over the same entry-to-exit window."],
  ["Walk-forward + purged K-fold + embargo","Time-series cross-validation with purge/embargo (Lopez de Prado)."],
  ["Intrabar-true resolution","Stop-first-touch within the bar; fixes EXPIRED-to-WON and daily-resolution inflation."],
  ["Effective-N accounting","Correlated candidates count as more than one trial."],
  ["2x cost stress","The net CI recomputed at twice the per-class slippage; a required gate."],
  ["Benchmark-relative (IR, down-capture)","Excess return and capture versus a matched-exposure benchmark leg."],
  ["Brier score / calibration","Probability calibration for meta-labeling and prediction markets."],
  ["Meta-labeling","A secondary model predicts whether the primary signal will work, not the price."]
];

var TRAPS = [
  ["Connors RSI-2","DEAD in-repo: high win rate but average loss far larger than average win; crypto Sharpe -2.6."],
  ["SMC order blocks alone","Systematic backtests negative almost everywhere without confluence."],
  ["Meme / gainer ML","Forward claims (e.g. 580%) contradict live results (5% WR v2); survivorship."],
  ["Copy-trading wallets","KILL family on the ledger (n=81, PF 0.31)."],
  ["COT positional shorts","Look-ahead leakage (M-095); after the fix WR 30%, PF 0.51."],
  ["Fixed-TP 'milestones' / spike reverse-engineering","Label artefact: TP-first exits manufacture win rate without expectancy."],
  ["CRYPTO SWING","n=243, PF 0.457, -328.6pp on the per-class paths analysis."],
  ["KSS cointegration",">160% max drawdown; use Engle-Granger instead."]
];

var RETIRED = [
  ["H-143 tactical algorithm","Net CAGR 9.34% vs same-window SPY 18.09% (-8.75pp/yr); every paired block lower bound negative. Removed from the alpha-forward queue."],
  ["luxalgo_confluence SHORT (slice candidate)","CANDIDATE on the 3,500-row export slice, but WEAK on the canonical full book (n=1,924, net -0.089%/trade, 2x CI negative). Refuted, not pending."],
  ["POD-CRYPTO-ENSEMBLE-GRADE","Declined: a reconstructed score proxy (n=33), not a named emitter; CRYPTO class aggregate is a proven-harm cell."],
  ["POD-LUXALGO-SHORT","post_hoc: registered after the rows were scored, 97.7% single-source; observe only."]
];

var BENCHMARKS = [
  ["CRYPTO", "BTC-USD hold", "excess vs hold; 2x slippage; IR>=0.5"],
  ["EQUITY", "SPY total return", "IR>=0.5, down-capture, n>=100 forward"],
  ["ETF", "SPY total return", "monthly cadence only (intraday cost artefact)"],
  ["BOND", "AGG / T-bills", "duration-matched"],
  ["COMMODITY", "GSG", "term-structure neutral"],
  ["FUTURES", "GSG", "term-structure neutral"],
  ["FOREX", "DXY", "trend/carry matched"]
];

function el(id){ return document.getElementById(id); }
function esc(s){ return String(s==null?"":s).replace(/[&<>]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];}); }
function fmt(v,d){ if(v==null) return "—"; var n=Number(v); return isNaN(n)?esc(v):n.toFixed(d==null?3:d); }
function ci(arr){ if(!arr||arr.length<2||arr[0]==null) return "—"; return "["+fmt(arr[0],3)+", "+fmt(arr[1],3)+"]"; }

function renderStatic(){
  el("measures").innerHTML = MEASURES.map(function(m){
    return "<tr><td><strong>"+esc(m[0])+"</strong></td><td>"+esc(m[1])+"</td></tr>"; }).join("");
  el("traps").innerHTML = TRAPS.map(function(t){
    return "<tr><td><strong>"+esc(t[0])+"</strong></td><td>"+esc(t[1])+"</td></tr>"; }).join("");
  el("retired").innerHTML = RETIRED.map(function(t){
    return "<tr><td><strong>"+esc(t[0])+"</strong></td><td>"+esc(t[1])+"</td></tr>"; }).join("");
  el("benchRows").innerHTML = BENCHMARKS.map(function(b){
    return "<tr><td><strong>"+esc(b[0])+"</strong></td><td>"+esc(b[1])+"</td><td>"+esc(b[2])+"</td></tr>";
  }).join("");
  el("pods").innerHTML = PODS.map(function(p){
    var b = p.status==="pre_registered" ? "b-pre" : (p.status==="observe" ? "b-observe" : (p.status==="post_hoc"?"b-post":"b-declined"));
    return '<div class="card">'+
      '<div style="display:flex;justify-content:space-between;gap:8px;align-items:center">'+
        '<strong>'+esc(p.id)+'</strong><span class="badge '+b+'">'+esc(p.status)+'</span></div>'+
      '<div class="small muted" style="margin:6px 0">'+esc(p.klass)+' · '+esc(p.dir)+' · '+esc(p.hypothesis)+'</div>'+
      '<div class="small">'+esc(p.evidence)+'</div>'+
      '<div class="small muted" style="margin-top:6px"><strong>Gate:</strong> '+esc(p.gate)+'</div>'+
    '</div>';
  }).join("");
}

function renderLedger(d){
  var cov = d.coverage || {};
  var den = cov.denominator || {};
  var scored = cov.scored_rows, total = cov.total_closed_picks;
  var pct = (scored!=null && total) ? (100*scored/total).toFixed(1) : null;
  var mode = den.mode || "unknown";
  el("coverage").innerHTML = "This ledger scores <strong>"+fmt(scored,0)+"</strong> of <strong>"+fmt(total,0)+"</strong> closed picks"+
    (pct?(" ("+pct+"%)"):"")+". Denominator: <code>"+esc(mode)+"</code>."+
    (mode!=="canonical" ? " <strong>The canonical full-book view was not used for this build.</strong>" : "");
  el("coverage").className = "banner" + (mode==="canonical" ? "" : " warn");

  var rows = (d.classes||[]).map(function(c){
    return "<tr><td><strong>"+esc(c.asset_class)+"</strong></td>"+
      '<td class="v-'+esc(c.verdict)+'">'+esc(c.verdict)+"</td>"+
      '<td class="num">'+fmt(c.n,0)+"</td>"+
      '<td class="num">'+fmt(c.net_expectancy_pct,4)+"</td>"+
      '<td class="num">'+ci(c.net_ci_pct)+"</td>"+
      "<td>"+(c.stress_2x_ok?"yes":"no")+"</td>"+
      '<td class="num">'+fmt(c.dsr,3)+"</td>"+
      '<td class="num">'+fmt(c.required_n,0)+"</td></tr>";
  }).join("");
  el("classRows").innerHTML = rows || '<tr><td colspan="8" class="muted">no class rows</td></tr>';

  var sum = d.summary || {};
  el("trialBudget").innerHTML = "Rolls used: <strong>"+fmt(sum.n_cells_tested,0)+"</strong> tested cells / <strong>"+fmt(sum.n_cells_total,0)+"</strong> total &middot; "+
    "verdicts: proven "+fmt(sum.n_proven,0)+", candidate "+fmt(sum.n_candidate,0)+", weak "+fmt(sum.n_weak,0)+", kill "+fmt(sum.n_kill,0)+". "+
    "Nothing promotes without forward rows.";

  var prov = d.provenance || {};
  var src = String(prov.source || d.source || "");
  var tmpWarn = /\/tmp\//.test(src) ? ' <strong style="color:var(--warn)">Warning: source is a /tmp build path, not a committed file.</strong>' : "";
  el("provenance").innerHTML =
    "generator <code>"+esc(prov.generator_version||"—")+"</code> · "+
    "input sha <code>"+esc(prov.input_sha256||"—")+"</code> · "+
    "git <code>"+esc(prov.git_sha||"—")+"</code> · "+
    "generated <code>"+esc(d.generated_at||"—")+"</code>"+tmpWarn;
}

renderStatic();
var LEDGER_PATHS = ["audit3_ledger.json", "../audit3/audit3_ledger.json",
                    "../audit/data/audit3_ledger.json", "data/audit3_ledger.json"];

function loadLedger(i){
  if(i >= LEDGER_PATHS.length){
    throw new Error("not found in any known location");
  }
  return fetch(LEDGER_PATHS[i], {cache:"no-store"}).then(function(r){
    if(!r.ok) throw new Error("HTTP "+r.status+" at "+LEDGER_PATHS[i]);
    return r.json();
  }).catch(function(err){
    if(err && /HTTP 404/.test(err.message)) return loadLedger(i+1);
    throw err;
  });
}

function loadForward(){
  return fetch("audit2_forward.json", {cache:"no-store"}).then(function(r){
    if(!r.ok) throw new Error("HTTP "+r.status); return r.json();
  }).then(function(f){
    var rows = Object.keys(f.by_hypothesis||{}).map(function(h){
      var v=f.by_hypothesis[h];
      var ok = v.n>=100 && v.intrabar===v.n && v.benchmark_leg>=0.9*v.n;
      var status;
      if (v.gate && v.gate.eligible) {
        status = "gate-ready";
      } else if (v.gate && (v.gate.reasons||[]).length) {
        // The ledger already computes exactly why this cannot promote; show it
        // instead of a vague "accruing".
        status = v.gate.reasons[0];
      } else {
        status = v.n===0 ? "0 rows — clock not accruing" : (ok ? "gate-ready" : "accruing");
      }
      return "<tr><td><strong>"+esc(h)+"</strong></td><td class=\"num\">"+fmt(v.n,0)+"</td><td class=\"num\">"+
        fmt(v.benchmark_leg,0)+"/"+fmt(v.n,0)+"</td><td class=\"num\">"+fmt(v.intrabar,0)+"/"+fmt(v.n,0)+"</td><td>"+esc(status)+"</td></tr>";
    }).join("");
    el("forwardRows").innerHTML = rows || '<tr><td colspan="5" class="muted">no forward rows yet</td></tr>';
  }).catch(function(){
    el("forwardRows").innerHTML = '<tr><td colspan="5" class="muted">forward ledger unavailable</td></tr>';
  });
}

// The pod registry is a projection of reports/audit3_confirmatory.json
// (tools/build_audit2_pods.py). When the sidecar is present it replaces the
// bundled copy, so a manifest change no longer needs a JavaScript edit.
function adoptPods(d){
  if (!d || !Array.isArray(d.pods) || !d.pods.length) return false;
  PODS = d.pods.map(function(p){
    return {id:p.id, status:p.status, hypothesis:p.hypothesis,
            klass:p.klass, dir:p.dir,
            evidence:p.thesis || p.evidence || "",
            gate:p.gate || ""};
  });
  return true;
}

fetch("audit2_pods.json", {cache:"no-store"})
  .then(function(r){ return r.ok ? r.json() : null; })
  .then(adoptPods)
  .catch(function(){})
  .then(function(){
    renderStatic();
    loadForward();
    return loadLedger(0);
  })
  .then(function(d){
    renderLedger(d);
    el("ledgerStatus").className = "banner";
    el("ledgerStatus").textContent = "Ledger loaded: "+(d.generated_at||"")+".";
  })
  .catch(function(err){
    el("ledgerStatus").className = "banner warn";
    el("ledgerStatus").textContent = "Ledger unavailable ("+err.message+"). Showing the static pod registry and measures only — no live verdicts.";
    el("coverage").textContent = "no ledger";
  });
