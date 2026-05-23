/**
 * HIGH CONVICTION preset filter v3 — shared hard gates + stamped HF tier / per-class contract.
 * Node: loads config/hc_gate_params.json at require time. Browser: fetches same JSON on init (see initHcGateParamsForAudit).
 * Optional override: window.__HC_GATE_PARAMS__ (shallow merge).
 */
/* eslint-disable no-var */

function hcMergeShallow(base, over) {
  var out = {};
  var k;
  for (k in base) {
    if (Object.prototype.hasOwnProperty.call(base, k)) out[k] = base[k];
  }
  if (over) {
    for (k in over) {
      if (Object.prototype.hasOwnProperty.call(over, k)) out[k] = over[k];
    }
  }
  return out;
}

/** Embedded defaults — keep in sync with config/hc_gate_params.json */
var HC_GATE_PARAMS_EMBEDDED = {
  scoreAbsoluteFloor: 40,
  scoreCompoundFloor: 45,  // 2026-04-30: lowered 50->45 per reports/EDGE_ANALYSIS_2026_04_30.md
  scoreCompoundTrustMin: 8,
  trustTierBlacklist: ['SANDBOX', 'UNPROVEN', 'PROBATION', 'DEMOTED'],
  trustScoreMinCrypto: 6,   // 2026-05-15: raised 4→6 — confidence anti-predictive on CRYPTO (IC=-0.14); trust_score is the correct signal
  trustScoreMinOther: 6,    // 2026-05-15: raised 5→6 — TRUSTED tier floor (0-10 scale); 6 = institutional minimum conviction
  forwardTradesMin: 5,
  forwardWRMinPct: 55,
  // 2026-05-01: FIXED impossible FWD WR floors per asset-class reality check.
  // Old 70% floors blocked ALL FOREX (WR~30%), FUTURES (WR~6%), BOND (WR~47%).
  // New floors based on achievable WR from 3,500-pick audit (2026-04-20).
  forwardWRMinPctCrypto: 60,  // achievable ~60-65% (lowered from 70)
  forwardWRMinPctEquity: 55,  // achievable ~55-60% (lowered from 70)
  forwardWRMinPctForex: 45,  // achievable ~30-47%, relaxed from 70 -> 45
  forwardWRMinPctCommodity: 50,  // achievable ~59% (new, was missing)
  forwardWRMinPctFutures: 35,  // achievable ~6-20% (new, was missing)
  forwardWRMinPctBond: 40,  // achievable ~47% (new, was missing)
  forwardWRMinPctETF: 45,  // achievable ~51% (new, was missing)
  scoreFloorCrypto: 55,       // unchanged
  scoreFloorEquity: 50,       // lowered from 45 -> 50 to match config.py MIN_ELITE_SCORE_BY_CLASS
  scoreFloorForex: 50,       // raised from 45 -> 50 to match config.py
  scoreFloorCommodity: 50,  // new per-class floor (match config.py)
  scoreFloorFutures: 40,    // new per-class floor
  scoreFloorBond: 40,        // new per-class floor
  scoreFloorETF: 50,         // new per-class floor
  forexRelaxedWRMinPct: 40, // lowered from 65 -> 40 to match FOREX reality
  confidenceMax: 0.80,  // 2026-05-16: lowered 0.90→0.80 — OOS backtest shows 0.80-0.90 is the actual danger zone (PF=0.96, WR collapses); >0.90 was already blocked but 0.80-0.90 band is worse than random
  commodityConfidenceMin: 0.55,  // 2026-05-17: floor at 0.55 not 0.60 — COT strategies (our best COMMODITY edge) emit at 0.55-0.67 (cot_positioning min=0.55, cftc_cot_commercial_signal min=0.58). A 0.60 floor would cut 17.2% of cot_positioning picks (WR=80%/PF=4.94). Verified: no known-good COMMODITY strategy emits below 0.55.
  confidenceFwdTradesMax: 20,
  confidenceExtremeMax: 0.95,
  confidenceExtremeFwdTradesMax: 30,
  confidenceLoBand: 0.85,
  confidenceHiBand: 0.95,
  confidenceLoBandFwdTradesMin: 30,
  longBlockedInBear: true,
  bearRegimes: ['bear', 'trending_down', 'crash', 'distribution'],
  shortBlockedInBull: true,
  bullRegimes: ['bull', 'trending_up', 'strong_bull'],
  shortInBullRequiresProven: true,
  rejectWalkForwardFailing: true,
  independentGroupsMin: 3,
  tierSABypassIndependentConsensus: true,
  signalGroups: {
    ml_engine: [
      'alpha_engine', 'alpha_engine_fast', 'ml_crypto_pred', 'ml_crypto_pred_v12',
      'mercury2', 'predictions', 'crypto_ml_edge', 'dna_winner_picks',
    ],
    technical: [
      'luxalgo_filters', 'rapid_fire', 'breakout_b_ml', 'breakout_c_spike',
      'baby_strats_forward', 'tsmom_strategy', 'super_signals',
    ],
    regime_group: [
      'regime_terminal', 'battleground', 'quan_engine', 'fear_greed_contrarian',
    ],
    prediction_market: [
      'pm_whale_signals', 'pm_kalshi_signals', 'prediction_market_consensus',
      'pm_momentum_signals',
    ],
    copy_trader: [
      'copy_trader_highscore', 'copy_trader_intel', 'copy_trader_clones',
      'copy_trader_consensus',
    ],
    ai_challenge: [
      // Retired 2026-04-18: LLM tournament ended Round 5; removed
      // ai_challenge_antigravity/grok/mercury/claude/kimi_moonshot.
      // predictable + scanner remain (auto-regenerated from alpha_engine).
      'ai_challenge_predictable', 'ai_challenge_scanner',
      'claude_gainer_st', 'chatgpt_combined', 'kimi_riseoftheclaw',
    ],
    fundamentals: [
      'pead_earnings_drift', 'quality_minus_junk', 'quality_value', 'earnings_drift',
    ],
  },
  corrPairs: {
    ETHUSDT: ['SOLUSDT', 'AVAXUSDT', 'NEARUSDT'],
    SOLUSDT: ['ETHUSDT', 'AVAXUSDT', 'NEARUSDT'],
    BTCUSDT: ['ETHUSDT', 'BNBUSDT'],
    BNBUSDT: ['BTCUSDT'],
    AVAXUSDT: ['ETHUSDT', 'SOLUSDT'],
    NEARUSDT: ['ETHUSDT', 'SOLUSDT'],
  },
};

/** Mirrors config/hf_conviction_tiers.json — stamped-tier contract (per-class). */
var HF_TIER_CONTRACT = {
  fearGreedSubstrings: ['fear_greed_contrarian'],
  tierSSymbols: ['DOTUSDT', 'SUIUSDT', 'LTCUSDT', 'NEARUSDT', 'XRPUSDT'],
  tierAExtraSymbols: ['LINKUSDT', 'ATOMUSDT', 'AVAXUSDT', 'SOLUSDT', 'ADAUSDT', 'BNBUSDT'],
  tierBMajors: ['BTCUSDT', 'ETHUSDT'],
  nonCryptoTierAStrats: ['pead_earnings_drift', 'quality_value'],
  nonCryptoTierBStrats: [
    'pead_earnings_drift', 'quality_minus_junk', 'quality_value', 'earnings_drift',
  ],
};

var _HC_PARAMS_CACHE = null;

function resetHcGateParamsCache() {
  _HC_PARAMS_CACHE = null;
}

function _loadFileParamsNode() {
  if (typeof require === 'undefined' || typeof __dirname === 'undefined') return null;
  try {
    var fs = require('fs');
    var path = require('path');
    var fp = path.join(__dirname, '..', 'config', 'hc_gate_params.json');
    var raw = fs.readFileSync(fp, 'utf8');
    var j = JSON.parse(raw);
    delete j._doc;
    return j;
  } catch (e) {
    return null;
  }
}

function getHcGateParams() {
  if (_HC_PARAMS_CACHE) return _HC_PARAMS_CACHE;
  var fileP = _loadFileParamsNode();
  var merged = hcMergeShallow(HC_GATE_PARAMS_EMBEDDED, fileP);
  if (typeof window !== 'undefined' && window.__HC_GATE_PARAMS__) {
    merged = hcMergeShallow(merged, window.__HC_GATE_PARAMS__);
  }
  _HC_PARAMS_CACHE = merged;
  return merged;
}

/**
 * Browser: fetch deployed config/hc_gate_params.json and merge into runtime params.
 * Tries URL relative to current page (audit_dashboard/index.html -> ../config/...).
 */
function initHcGateParamsForAudit() {
  if (typeof window === 'undefined' || !window.fetch) return;
  var origin = window.location.origin;
  var path = window.location.pathname || '/';
  // pathname like /audit/ makes ../config resolve to /config (404). Prefer known mount paths first.
  var urls = [];
  if (path.indexOf('audit_dashboard') !== -1) {
    urls.push(origin + '/audit_dashboard/config/hc_gate_params.json');
  }
  urls.push(origin + '/audit/config/hc_gate_params.json');
  urls.push(new URL('config/hc_gate_params.json', origin + path).toString());
  // Note: ../config/ from /audit/ resolves to /config/ (404) — removed; /audit/config/ above handles it.
  var seen = {};
  var uniq = [];
  for (var ui = 0; ui < urls.length; ui++) {
    if (!seen[urls[ui]]) {
      seen[urls[ui]] = 1;
      uniq.push(urls[ui]);
    }
  }
  urls = uniq;
  var idx = 0;
  function tryNext() {
    if (idx >= urls.length) return;
    var u = urls[idx++];
    window
      .fetch(u, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('bad status');
        return r.json();
      })
      .then(function (j) {
        if (!j || typeof j !== 'object') throw new Error('bad json');
        delete j._doc;
        window.__HC_GATE_PARAMS__ = hcMergeShallow(window.__HC_GATE_PARAMS__ || {}, j);
        resetHcGateParamsCache();
      })
      .catch(function () {
        tryNext();
      });
  }
  tryNext();
}

function _normalizeAssetClass(pick) {
  var assetClass = String(pick.asset_class || pick.asset_class_type || '').toUpperCase();
  if (assetClass === 'STOCKS' || assetClass === 'PENNY_STOCK' || assetClass === 'EQUITIES') assetClass = 'EQUITY';
  if (assetClass === 'COMMODITIES') assetClass = 'COMMODITY';
  if (!assetClass) assetClass = 'CRYPTO';
  return assetClass;
}

/**
 * Stamped hf_conviction_tier (S/A/B) must match per-class contract (aligns with conviction_stack classify).
 */
function passesPerAssetTierContract(pick) {
  var tier = String(pick.hf_conviction_tier || '').toUpperCase();
  if (tier !== 'S' && tier !== 'A' && tier !== 'B') return false;
  var ac = _normalizeAssetClass(pick);
  var sym = String(pick.symbol || '').toUpperCase();
  var strat = String(pick.strategy || '').toLowerCase();
  var C = HF_TIER_CONTRACT;
  if (ac !== 'CRYPTO') {
    var frags = tier === 'A' ? C.nonCryptoTierAStrats : C.nonCryptoTierBStrats;
    if (tier === 'A' || tier === 'B') {
      for (var i = 0; i < frags.length; i++) {
        if (strat.indexOf(frags[i]) !== -1) return true;
      }
    }
    return false;
  }
  var fear = false;
  var fi;
  for (fi = 0; fi < C.fearGreedSubstrings.length; fi++) {
    if (strat.indexOf(C.fearGreedSubstrings[fi]) !== -1) {
      fear = true;
      break;
    }
  }
  if (tier === 'S' && fear && C.tierSSymbols.indexOf(sym) !== -1) return true;
  if (
    tier === 'A' &&
    fear &&
    (C.tierSSymbols.indexOf(sym) !== -1 || C.tierAExtraSymbols.indexOf(sym) !== -1)
  ) {
    return true;
  }
  if (tier === 'B' && C.tierBMajors.indexOf(sym) !== -1) return true;
  if (tier === 'B' && String(pick.trade_timeframe || pick.timeframe || '').toUpperCase() === 'INTRADAY') {
    return true;
  }
  return false;
}

function hasBypassTierReason(pick) {
  var raw = pick && pick.hf_conviction_reasons;
  var reasons = Array.isArray(raw) ? raw : raw ? [raw] : [];
  for (var i = 0; i < reasons.length; i++) {
    var reason = String(reasons[i] || '').toLowerCase();
    if (reason.indexOf('bypass_tier_a_') === 0 || reason.indexOf('bypass_tier_b_') === 0) {
      return true;
    }
  }
  return false;
}

function countIndependentGroups(pick, groups) {
  var raw = pick.source_systems || pick.agreeing_sources || '';
  var sources;
  if (Array.isArray(raw)) {
    sources = raw.map(function (s) {
      return s.trim().toLowerCase().replace(/_(standalone|live_signals|signal_tracking)$/, '');
    });
  } else {
    sources = String(raw)
      .split(/[,;|]/)
      .map(function (s) {
        return s.trim().toLowerCase();
      })
      .filter(Boolean);
  }
  if (sources.length === 0) return 0;
  var seen = {};
  var gname, members, gi, si, src, m;
  for (si = 0; si < sources.length; si++) {
    src = sources[si];
    for (gname in groups) {
      if (!Object.prototype.hasOwnProperty.call(groups, gname)) continue;
      if (seen[gname]) continue;
      members = groups[gname];
      for (gi = 0; gi < members.length; gi++) {
        m = String(members[gi]).toLowerCase();
        if (src.indexOf(m) !== -1) {
          seen[gname] = 1;
          break;
        }
      }
    }
  }
  return Object.keys(seen).length;
}

function _extractDsrValue(pick) {
  var p = pick || {};
  var candidates = [p.dsr, p.dsr_value, p.dsr_score, p.overfit_dsr];
  for (var i = 0; i < candidates.length; i++) {
    var v = Number(candidates[i]);
    if (!isNaN(v) && isFinite(v)) return v;
  }
  return null;
}

function _passesDsrGate(pick, params) {
  var p = pick || {};
  var verdict = String(p.dsr_verdict || p.overfit_verdict || '').toUpperCase();
  if (verdict.indexOf('OVERFIT') !== -1 || verdict.indexOf('REJECT') !== -1) {
    p._hf_quality_gate_reason = 'hf_dsr_overfit_verdict';
    return false;
  }

  var dsr = _extractDsrValue(p);
  if (dsr == null) return true; // fail-open when DSR is not present on row
  var dsrMin = Number(params.dsrMin);
  if (isNaN(dsrMin) || !isFinite(dsrMin)) dsrMin = 0.95;
  if (dsr < dsrMin) {
    p._hf_quality_gate_reason = 'hf_dsr_below_min';
    return false;
  }
  return true;
}

/**
 * Shared gates 1–9. If opt.skipIndependentConsensus, Gate 8 is skipped (stamped S/A/B tier path).
 */
function evaluateHcGates1to9(pick, opt) {
  opt = opt || {};
  var skipIndependentConsensus = !!opt.skipIndependentConsensus;
  var p = pick || {};
  var params = getHcGateParams();

  var sc = Number(p.score || 0);
  var trust = Number(p.trust_score || p.trust_score_1 || 0);
  var trustTier = String(p.trust_tier || '').toUpperCase();
  if (!trustTier && typeof getTrustTier === 'function') {
    trustTier = String(getTrustTier(p).tier || '').toUpperCase();
  }
  var fwdWr = Number(p.strat_fwd_wr || p.forward_wr || 0);
  if (fwdWr > 1.5) fwdWr = fwdWr / 100;
  var fwdN = parseInt(
    String(p.strat_fwd_trades != null ? p.strat_fwd_trades : p.forward_trades || 0),
    10
  ) || 0;
  var cf = Number(p.confidence || 0);
  if (cf > 1) cf = cf / 100;
  var direction = String(p.direction || p.signal_type || 'LONG').toUpperCase();
  var regime = String(p.regime_at_entry || p.market_regime || p.regime || '').toLowerCase();
  var assetClass = _normalizeAssetClass(p);

  if (sc < (params.scoreAbsoluteFloor || 40)) return false;
  if (sc < (params.scoreCompoundFloor || 50) && trust < (params.scoreCompoundTrustMin || 8)) return false;

  var ttu = trustTier;
  var bl = params.trustTierBlacklist || [];
  for (var i = 0; i < bl.length; i++) {
    if (ttu === String(bl[i] || '').toUpperCase()) return false;
  }

  // 2026-04-14: Per-asset-class validated-edge FWD WR + Score floors
  // 2026-04-18: Added explicit COMMODITY/FUTURES/BOND/ETF tiers — previously
  // they fell through to the 55% generic floor which combined with their
  // tiny sample sizes (BOND n=17, FUTURES n=17) silently zero'd those tiles.
  // Per Mercury diagnosis (with corrections — see updates/2026-04-18-non-crypto-
  // synthesis-and-action-plan.md). Lower floors reflect data-collection mode
  // for low-sample classes; cross-checked against forwardTradesMin gate which
  // still requires forward sample evidence before any pick is published.
  var smallSampleLowFloor = assetClass === 'COMMODITY' || assetClass === 'FUTURES'
    || assetClass === 'BOND' || assetClass === 'ETF';
  // forwardTradesMin: don't apply the standard 5-trade floor to BOND/FUTURES
  // (their pipelines are still spinning up). Other classes keep the floor.
  var fwdMinTrades = smallSampleLowFloor ? 2 : (params.forwardTradesMin || 5);
  if (fwdN < fwdMinTrades) return false;
  // Class-specific floor replaces generic forwardWRMinPct (generic is fallback for unlisted classes)
  // 2026-04-23: Raised to 70 for all classes per whatif-analysis (optimal threshold)
  var fwdFloorAC = assetClass === 'CRYPTO' ? (Number(params.forwardWRMinPctCrypto) || 70)
    : assetClass === 'EQUITY' ? (Number(params.forwardWRMinPctEquity) || 70)
    : assetClass === 'FOREX' ? (Number(params.forwardWRMinPctForex) || 70)
    : assetClass === 'COMMODITY' ? (Number(params.forwardWRMinPctCommodity) || 70)
    : assetClass === 'FUTURES' ? (Number(params.forwardWRMinPctFutures) || 70)
    : assetClass === 'BOND' ? (Number(params.forwardWRMinPctBond) || 70)
    : assetClass === 'ETF' ? (Number(params.forwardWRMinPctETF) || 70)
    : (Number(params.forwardWRMinPct) || 70);
  // FOREX auto-relax: if fwdN < 20 (small sample), relax FWD WR floor from 55% to 50%
  // Rationale: FOREX edge was calibrated at N=34; with N<20 the estimate is unreliable,
  // so we relax rather than reject — picks still need Score>=40 + shared gates.
  // Note: forexAutoRelax flag is also used by Gate 7b below to skip the confidence band rejection.
  var forexAutoRelax = assetClass === 'FOREX' && fwdN < 20;
  if (forexAutoRelax) fwdFloorAC = (Number(params.forexRelaxedWRMinPct) || 50);
  if (fwdWr < fwdFloorAC / 100) return false;
  var scoreFloorAC = assetClass === 'CRYPTO' ? (Number(params.scoreFloorCrypto) || 45)
    : assetClass === 'EQUITY' ? (Number(params.scoreFloorEquity) || 45)
    : assetClass === 'FOREX' ? (Number(params.scoreFloorForex) || 40)
    : assetClass === 'COMMODITY' ? (Number(params.scoreFloorCommodity) || 35)
    : assetClass === 'FUTURES' ? (Number(params.scoreFloorFutures) || 35)
    : assetClass === 'BOND' ? (Number(params.scoreFloorBond) || 35)
    : assetClass === 'ETF' ? (Number(params.scoreFloorETF) || 35)
    : (Number(params.scoreCompoundFloor) || 50);
  if (sc < scoreFloorAC) return false;

  var trustFloor =
    assetClass === 'CRYPTO'
      ? params.trustScoreMinCrypto || 4
      : params.trustScoreMinOther || 5;
  if (trust < trustFloor) return false;

  var cxMax = params.confidenceExtremeMax || 0.95;
  var cxFwd = params.confidenceExtremeFwdTradesMax || 30;
  if (cf > cxMax && fwdN < cxFwd) return false;
  var cMax = params.confidenceMax || 0.90;
  var cFwd = params.confidenceFwdTradesMax || 20;
  if (cf > cMax && fwdN < cFwd) return false;

  // Gate 7c: COMMODITY confidence floor — sub-0.60 picks lack COT-signal conviction
  // 0.60-0.70 bucket: WR=79%/PF=5.63/n=236 valid resolved (2026-05-17 session-o analysis)
  if (assetClass === 'COMMODITY') {
    var commConfMin = Number(params.commodityConfidenceMin) || 0;
    if (commConfMin > 0 && cf < commConfMin) return false;
  }

  // Gate 7b: REMOVED 2026-04-23 per whatif-analysis (confidence is anti-predictive on crypto)
  // Previous evidence: PF 0.61 on n=126 picks — but larger analysis shows flat/non-predictive
  // below 0.85+ tier. Now treated as tiebreaker only, not rejection gate.
  // if (!forexAutoRelax) {
  //   var cfLo = params.confidenceLoBand || 0.85;
  //   var cfHi = params.confidenceHiBand || 0.95;
  //   var cfLoFwdMin = params.confidenceLoBandFwdTradesMin || 30;
  //   if (cf >= cfLo && cf <= cfHi && fwdN < cfLoFwdMin) return false;
  // }

  var bearList = params.bearRegimes || ['bear', 'trending_down', 'crash', 'distribution'];
  var bullList = params.bullRegimes || ['bull', 'trending_up', 'strong_bull'];
  if (params.longBlockedInBear && direction === 'LONG') {
    for (var bi = 0; bi < bearList.length; bi++) {
      if (regime.indexOf(bearList[bi]) !== -1) return false;
    }
  }
  if (params.shortBlockedInBull && direction === 'SHORT') {
    for (var ui = 0; ui < bullList.length; ui++) {
      if (regime.indexOf(bullList[ui]) !== -1) {
        if (params.shortInBullRequiresProven && ttu !== 'PROVEN') return false;
      }
    }
  }

  var wf = String(p.wf_verdict || p.wf_verdict_class || p.walk_forward_verdict || '').toUpperCase();
  if (params.rejectWalkForwardFailing && wf === 'FAILING') return false;
  if (!_passesDsrGate(p, params)) return false;

  var igMin = Number(params.independentGroupsMin) || 3;
  if (!skipIndependentConsensus && igMin > 0) {
    var sources = p.source_systems || p.agreeing_sources || '';
    var hasSources = Array.isArray(sources) ? sources.length > 0 : String(sources).trim().length > 0;
    if (hasSources) {
      var ngrp = countIndependentGroups(p, params.signalGroups || {});
      if (ngrp < igMin) return false;
    }
  }

  var corrPairs = params.corrPairs || {};
  var symU = String(p.symbol || '').toUpperCase();
  var reg =
    typeof globalThis !== 'undefined' &&
    globalThis._hcPassedSyms &&
    typeof globalThis._hcPassedSyms === 'object'
      ? globalThis._hcPassedSyms
      : null;
  if (reg && symU && Object.prototype.hasOwnProperty.call(corrPairs, symU)) {
    var neighbors = corrPairs[symU];
    if (Array.isArray(neighbors)) {
      for (var nj = 0; nj < neighbors.length; nj++) {
        var other = String(neighbors[nj] || '').toUpperCase();
        if (reg[other] === direction) return false;
      }
    }
  }

  return true;
}

/**
 * Stamped HF tier path: backend attach_hf_conviction_tiers_to_picks + per-class contract;
 * may skip Gate 8 when tierSABypassIndependentConsensus (see hc_gate_params.json).
 */
function passesStampedTierSupplementalPath(pick) {
  var p = pick || {};
  var tier = String(p.hf_conviction_tier || '').toUpperCase();
  if (tier !== 'S' && tier !== 'A' && tier !== 'B') return false;
  if (!passesPerAssetTierContract(p) && !hasBypassTierReason(p)) return false;
  var params = getHcGateParams();
  var bypass = !!params.tierSABypassIndependentConsensus;
  var skip8 = bypass && (tier === 'S' || tier === 'A');
  if (tier === 'B') skip8 = false;
  return evaluateHcGates1to9(p, { skipIndependentConsensus: skip8 });
}

function passesHighConvictionPick(p) {
  if (evaluateHcGates1to9(p, {})) return true;
  return passesStampedTierSupplementalPath(p);
}

function filterHighConvictionOrdered(picks) {
  if (typeof globalThis !== 'undefined') {
    globalThis._hcPassedSyms = {};
  }
  var out = [];
  var i;
  var pick;
  var sym;
  var dir;
  for (i = 0; i < picks.length; i++) {
    pick = picks[i];
    if (passesHighConvictionPick(pick)) {
      out.push(pick);
      if (typeof globalThis !== 'undefined' && globalThis._hcPassedSyms) {
        sym = String((pick && pick.symbol) || '').toUpperCase();
        dir = String((pick && (pick.direction || pick.signal_type)) || 'LONG').toUpperCase();
        if (sym) globalThis._hcPassedSyms[sym] = dir;
      }
    }
  }
  return out;
}

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHcGateParamsForAudit);
  } else {
    initHcGateParamsForAudit();
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    passesHighConvictionPick: passesHighConvictionPick,
    filterHighConvictionOrdered: filterHighConvictionOrdered,
    evaluateHcGates1to9: evaluateHcGates1to9,
    passesStampedTierSupplementalPath: passesStampedTierSupplementalPath,
    passesPerAssetTierContract: passesPerAssetTierContract,
    initHcGateParamsForAudit: initHcGateParamsForAudit,
    getHcGateParams: getHcGateParams,
    resetHcGateParamsCache: resetHcGateParamsCache,
    countIndependentGroups: countIndependentGroups,
    hcMergeShallow: hcMergeShallow,
    HC_GATE_PARAMS_EMBEDDED: HC_GATE_PARAMS_EMBEDDED,
  };
}
