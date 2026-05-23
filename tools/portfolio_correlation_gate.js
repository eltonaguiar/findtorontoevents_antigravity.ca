/**
 * Portfolio-level correlation guard — NOT part of passesHighConvictionPick.
 * Call before placing a pick when you already have open positions in the book.
 *
 *   const { checkCorrelationExposure } = require('./tools/portfolio_correlation_gate.js');
 *   if (!checkCorrelationExposure(newPick, existingPicks)) { return; }
 */
'use strict';

var CORR_GROUPS = {
  ETH: ['SOL', 'AVAX', 'NEAR', 'MATIC', 'ARB', 'OP', 'ETH'],
  BTC: ['ETH', 'BNB', 'BTC'],
  MEME: ['DOGE', 'SHIB', 'PEPE', 'FLOKI', '1000PEPE', '1000SHIB'],
  L1: ['ADA', 'DOT', 'ATOM', 'SUI', 'APT', 'NEAR'],
};

function _strip(sym) {
  return String(sym || '')
    .toUpperCase()
    .replace(/^BINANCE:/, '')
    .replace(/^BYBIT:/, '')
    .replace(/USDT$/i, '')
    .replace(/[^A-Z0-9]/g, '');
}

/**
 * @param {object} pick - { symbol }
 * @param {object[]} existingPicks - open positions
 * @param {{ maxPerGroup?: number }} [opts] - default max 1 concurrent from same corr bucket (stricter than user's 2)
 * @returns {boolean} true if placement is allowed
 */
function checkCorrelationExposure(pick, existingPicks, opts) {
  var maxPer = (opts && opts.maxPerGroup) != null ? opts.maxPerGroup : 1;
  var sym = _strip((pick || {}).symbol);
  if (!sym) return true;
  var groupKeys = Object.keys(CORR_GROUPS);
  var gi;
  var gk;
  var members;
  var mi;
  var bucket = null;
  for (gi = 0; gi < groupKeys.length; gi++) {
    gk = groupKeys[gi];
    members = CORR_GROUPS[gk];
    for (mi = 0; mi < members.length; mi++) {
      if (sym === members[mi] || sym.indexOf(members[mi]) === 0) {
        bucket = gk;
        break;
      }
    }
    if (bucket) break;
  }
  if (!bucket) return true;

  members = CORR_GROUPS[bucket];
  var held = 0;
  var i;
  var p;
  var ps;
  for (i = 0; i < (existingPicks || []).length; i++) {
    p = existingPicks[i];
    ps = _strip((p || {}).symbol);
    var mj;
    for (mj = 0; mj < members.length; mj++) {
      if (ps === members[mj] || ps.indexOf(members[mj]) === 0) {
        held++;
        break;
      }
    }
  }
  return held < maxPer;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    checkCorrelationExposure: checkCorrelationExposure,
    CORR_GROUPS: CORR_GROUPS,
    _stripSymbolForCorr: _strip,
  };
}
