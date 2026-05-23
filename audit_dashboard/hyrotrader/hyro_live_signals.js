/**
 * Live 1h signal evaluators aligned with tools/hyro_backtest.py + hyro_backtest_extended.py
 * (donchian, heikin_ashi). Loaded by audit/hyrotrader/index.html.
 */
(function (global) {
  "use strict";

  function calcSma(closes, period) {
    var n = closes.length;
    var out = new Array(n);
    for (var i = 0; i < n; i++) out[i] = null;
    for (var i = period - 1; i < n; i++) {
      var s = 0;
      for (var j = i - period + 1; j <= i; j++) s += closes[j];
      out[i] = s / period;
    }
    return out;
  }

  function calcStd(closes, period) {
    var n = closes.length;
    var out = new Array(n);
    for (var i = 0; i < n; i++) out[i] = null;
    for (var i = period - 1; i < n; i++) {
      var s = 0;
      for (var j = i - period + 1; j <= i; j++) s += closes[j];
      var mean = s / period;
      var v = 0;
      for (var k = i - period + 1; k <= i; k++) v += Math.pow(closes[k] - mean, 2);
      out[i] = Math.sqrt(v / period);
    }
    return out;
  }

  function calcEma(closes, period) {
    var n = closes.length;
    var out = new Array(n);
    for (var i = 0; i < n; i++) out[i] = null;
    if (n < period) return out;
    var k = 2 / (period + 1);
    var s = 0;
    for (var j = 0; j < period; j++) s += closes[j];
    out[period - 1] = s / period;
    for (var i = period; i < n; i++) {
      out[i] = closes[i] * k + out[i - 1] * (1 - k);
    }
    return out;
  }

  function calcRsi(closes, period) {
    var n = closes.length;
    var out = new Array(n);
    for (var i = 0; i < n; i++) out[i] = null;
    if (n < period + 1) return out;
    var gains = [];
    var losses = [];
    for (var i = 1; i < n; i++) {
      var ch = closes[i] - closes[i - 1];
      gains.push(Math.max(0, ch));
      losses.push(Math.max(0, -ch));
    }
    var ag = 0,
      al = 0;
    for (var g = 0; g < period; g++) {
      ag += gains[g];
      al += losses[g];
    }
    ag /= period;
    al /= period;
    var rsiAt = function (avgG, avgL) {
      if (avgL === 0) return 100;
      var rs = avgG / avgL;
      return 100 - 100 / (1 + rs);
    };
    out[period] = rsiAt(ag, al);
    for (var i = period; i < gains.length; i++) {
      ag = (ag * (period - 1) + gains[i]) / period;
      al = (al * (period - 1) + losses[i]) / period;
      out[i + 1] = rsiAt(ag, al);
    }
    return out;
  }

  function calcAtr(candles, period) {
    var n = candles.length;
    var out = new Array(n);
    for (var i = 0; i < n; i++) out[i] = null;
    if (n < period + 1) return out;
    var trs = [];
    for (var i = 1; i < n; i++) {
      var hi = candles[i].high,
        lo = candles[i].low,
        pc = candles[i - 1].close;
      trs.push(Math.max(hi - lo, Math.abs(hi - pc), Math.abs(lo - pc)));
    }
    var sum = 0;
    for (var t = 0; t < period; t++) sum += trs[t];
    out[period] = sum / period;
    for (var i = period; i < trs.length; i++) {
      out[i + 1] = (out[i] * (period - 1) + trs[i]) / period;
    }
    return out;
  }

  function calcAdx(candles, period) {
    var n = candles.length;
    var adx = new Array(n);
    var plusDi = new Array(n);
    var minusDi = new Array(n);
    for (var i = 0; i < n; i++) {
      adx[i] = null;
      plusDi[i] = null;
      minusDi[i] = null;
    }
    if (n < period * 3) return { adx: adx, plusDi: plusDi, minusDi: minusDi };
    var tr = [];
    var pDm = [];
    var mDm = [];
    for (var j = 1; j < n; j++) {
      var h = candles[j].high;
      var l = candles[j].low;
      var pc = candles[j - 1].close;
      var h1 = candles[j - 1].high;
      var l1 = candles[j - 1].low;
      tr.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
      var up = h - h1;
      var dn = l1 - l;
      pDm.push(up > dn && up > 0 ? up : 0);
      mDm.push(dn > up && dn > 0 ? dn : 0);
    }
    var dxVals = [];
    var dxIdx = [];
    for (var k = period - 1; k < tr.length; k++) {
      var iC = k + 1;
      var trSum = 0;
      var pSum = 0;
      var mSum = 0;
      for (var w = k - period + 1; w <= k; w++) {
        trSum += tr[w];
        pSum += pDm[w];
        mSum += mDm[w];
      }
      var trMean = trSum / period;
      if (trMean <= 0) continue;
      var pp = 100 * (pSum / period) / trMean;
      var mm = 100 * (mSum / period) / trMean;
      plusDi[iC] = pp;
      minusDi[iC] = mm;
      var total = pp + mm;
      dxVals.push(total > 0 ? (100 * Math.abs(pp - mm)) / total : 0);
      dxIdx.push(iC);
    }
    for (var q = period - 1; q < dxVals.length; q++) {
      var outIdx = dxIdx[q];
      var dxSum = 0;
      for (var z = q - period + 1; z <= q; z++) dxSum += dxVals[z];
      adx[outIdx] = dxSum / period;
    }
    return { adx: adx, plusDi: plusDi, minusDi: minusDi };
  }

  function lastSignalBollinger(candles, p) {
    p = p || {};
    var bb = p.bb_period || 20,
      mult = p.bb_std_mult || 2,
      rsiP = p.rsi_period || 14,
      rsiL = p.rsi_long || 35,
      rsiS = p.rsi_short || 65,
      atrP = p.atr_period || 14;
    var need = Math.max(bb, rsiP, atrP) + 2;
    if (candles.length < need) return null;
    var closes = candles.map(function (c) {
      return c.close;
    });
    var sma = calcSma(closes, bb);
    var std = calcStd(closes, bb);
    var rsi = calcRsi(closes, rsiP);
    var atr = calcAtr(candles, atrP);
    var i = candles.length - 1;
    if (sma[i] == null || std[i] == null || rsi[i] == null || atr[i] == null) return null;
    var upper = sma[i] + mult * std[i];
    var lower = sma[i] - mult * std[i];
    var mid = sma[i];
    var c = candles[i];
    if (c.low <= lower && rsi[i] < rsiL) {
      var entry = lower;
      var sl = lower - atr[i];
      var tp = mid;
      var rr = entry !== sl ? (tp - entry) / (entry - sl) : 0;
      if (rr >= 1)
        return {
          direction: "LONG",
          entry: Math.round(entry * 100) / 100,
          sl: Math.round(sl * 100) / 100,
          tp: Math.round(tp * 100) / 100,
          rr: Math.round(rr * 100) / 100,
        };
    }
    if (c.high >= upper && rsi[i] > rsiS) {
      entry = upper;
      sl = upper + atr[i];
      tp = mid;
      rr = sl !== entry ? (entry - tp) / (sl - entry) : 0;
      if (rr >= 1)
        return {
          direction: "SHORT",
          entry: Math.round(entry * 100) / 100,
          sl: Math.round(sl * 100) / 100,
          tp: Math.round(tp * 100) / 100,
          rr: Math.round(rr * 100) / 100,
        };
    }
    return null;
  }

  function lastSignalRsi2(candles, p) {
    p = p || {};
    var rsiP = p.rsi_period || 2,
      sf = p.sma_filter || 200,
      stp = p.sma_tp || 20,
      atrP = p.atr_period || 14,
      atrSl = p.atr_sl_mult != null ? p.atr_sl_mult : 2,
      rsiLong = p.rsi_long != null ? p.rsi_long : 5,
      rsiShort = p.rsi_short != null ? p.rsi_short : 95;
    var need = Math.max(sf, stp, atrP) + 2;
    if (candles.length < need) return null;
    var closes = candles.map(function (c) {
      return c.close;
    });
    var rsi = calcRsi(closes, rsiP);
    var smaF = calcSma(closes, sf);
    var smaT = calcSma(closes, stp);
    var atr = calcAtr(candles, atrP);
    var i = candles.length - 1;
    if (rsi[i] == null || smaF[i] == null || smaT[i] == null || atr[i] == null) return null;
    var c = candles[i];
    if (rsi[i] < rsiLong && c.close > smaF[i]) {
      var entry = c.close;
      var sl = entry - atrSl * atr[i];
      var tp = smaT[i];
      if (tp > entry) {
        var rr = entry !== sl ? (tp - entry) / (entry - sl) : 0;
        if (rr >= 1)
          return {
            direction: "LONG",
            entry: Math.round(entry * 100) / 100,
            sl: Math.round(sl * 100) / 100,
            tp: Math.round(tp * 100) / 100,
            rr: Math.round(rr * 100) / 100,
          };
      }
    }
    if (rsi[i] > rsiShort && c.close < smaF[i]) {
      entry = c.close;
      sl = entry + atrSl * atr[i];
      tp = smaT[i];
      if (tp < entry) {
        rr = sl !== entry ? (entry - tp) / (sl - entry) : 0;
        if (rr >= 1)
          return {
            direction: "SHORT",
            entry: Math.round(entry * 100) / 100,
            sl: Math.round(sl * 100) / 100,
            tp: Math.round(tp * 100) / 100,
            rr: Math.round(rr * 100) / 100,
          };
      }
    }
    return null;
  }

  function lastSignalVolume(candles, p) {
    p = p || {};
    var lb = p.lookback || 20,
      vm = p.vol_mult || 2,
      atrP = p.atr_period || 14,
      tpR = p.tp_r || 2,
      slM = p.sl_atr_mult || 1.5;
    var need = Math.max(lb, atrP) + 3;
    if (candles.length < need) return null;
    var atr = calcAtr(candles, atrP);
    var i = candles.length - 1;
    if (atr[i] == null) return null;
    var c = candles[i];
    var win = candles.slice(i - lb, i);
    var ph = -Infinity,
      pl = Infinity,
      vs = 0;
    for (var w = 0; w < win.length; w++) {
      ph = Math.max(ph, win[w].high);
      pl = Math.min(pl, win[w].low);
      vs += win[w].volume;
    }
    var avgV = vs / win.length;
    if (avgV === 0) return null;
    if (c.close > ph && c.volume > vm * avgV) {
      var entry = c.close;
      var sl = entry - slM * atr[i];
      var risk = entry - sl;
      var tp = entry + tpR * risk;
      return {
        direction: "LONG",
        entry: Math.round(entry * 100) / 100,
        sl: Math.round(sl * 100) / 100,
        tp: Math.round(tp * 100) / 100,
        rr: tpR,
      };
    }
    if (c.close < pl && c.volume > vm * avgV) {
      entry = c.close;
      sl = entry + slM * atr[i];
      risk = sl - entry;
      tp = entry - tpR * risk;
      return {
        direction: "SHORT",
        entry: Math.round(entry * 100) / 100,
        sl: Math.round(sl * 100) / 100,
        tp: Math.round(tp * 100) / 100,
        rr: tpR,
      };
    }
    return null;
  }

  function lastSignalSr(candles, p) {
    p = p || {};
    var piv = p.pivot_lookback || 5,
      srL = p.sr_lookback || 50,
      atrP = p.atr_period || 14,
      tol = p.touch_tolerance_atr || 0.5,
      tpR = p.tp_r || 2;
    var need = Math.max(srL, atrP, piv * 2) + 3;
    if (candles.length < need) return null;
    var atr = calcAtr(candles, atrP);
    var i = candles.length - 1;
    if (atr[i] == null) return null;
    var candle = candles[i];
    var window = candles.slice(i - srL, i);
    var supports = [];
    var resistances = [];
    for (var j = piv; j < window.length - piv; j++) {
      var isLow = true;
      for (var k = 1; k <= piv; k++) {
        if (window[j].low > window[j - k].low || window[j].low > window[j + k].low) isLow = false;
      }
      if (isLow) supports.push(window[j].low);
      var isHi = true;
      for (k = 1; k <= piv; k++) {
        if (window[j].high < window[j - k].high || window[j].high < window[j + k].high) isHi = false;
      }
      if (isHi) resistances.push(window[j].high);
    }
    if (!supports.length || !resistances.length) return null;
    var tolerance = tol * atr[i];
    for (var s = 0; s < supports.length; s++) {
      var sup = supports[s];
      if (Math.abs(candle.low - sup) < tolerance && candle.close > sup) {
        var entry = candle.close;
        var sl = sup - 1.5 * atr[i];
        var risk = entry - sl;
        var resAbove = resistances.filter(function (r) {
          return r > entry;
        });
        var tp;
        var rr;
        if (resAbove.length) {
          tp = Math.min.apply(null, resAbove);
          rr = risk > 0 ? (tp - entry) / risk : 0;
          if (rr >= 1)
            return {
              direction: "LONG",
              entry: Math.round(entry * 100) / 100,
              sl: Math.round(sl * 100) / 100,
              tp: Math.round(tp * 100) / 100,
              rr: Math.round(rr * 100) / 100,
            };
        } else {
          tp = entry + tpR * risk;
          return {
            direction: "LONG",
            entry: Math.round(entry * 100) / 100,
            sl: Math.round(sl * 100) / 100,
            tp: Math.round(tp * 100) / 100,
            rr: tpR,
          };
        }
      }
    }
    for (var r = 0; r < resistances.length; r++) {
      var res = resistances[r];
      if (Math.abs(candle.high - res) < tolerance && candle.close < res) {
        entry = candle.close;
        sl = res + 1.5 * atr[i];
        risk = sl - entry;
        var supBelow = supports.filter(function (x) {
          return x < entry;
        });
        if (supBelow.length) {
          tp = Math.max.apply(null, supBelow);
          rr = risk > 0 ? (entry - tp) / risk : 0;
          if (rr >= 1)
            return {
              direction: "SHORT",
              entry: Math.round(entry * 100) / 100,
              sl: Math.round(sl * 100) / 100,
              tp: Math.round(tp * 100) / 100,
              rr: Math.round(rr * 100) / 100,
            };
        } else {
          tp = entry - tpR * risk;
          return {
            direction: "SHORT",
            entry: Math.round(entry * 100) / 100,
            sl: Math.round(sl * 100) / 100,
            tp: Math.round(tp * 100) / 100,
            rr: tpR,
          };
        }
      }
    }
    return null;
  }

  function donchianBoundsAt(candles, endIdx, period) {
    var start = endIdx - period + 1;
    if (start < 0) return null;
    var hi = -Infinity,
      lo = Infinity;
    for (var j = start; j <= endIdx; j++) {
      hi = Math.max(hi, candles[j].high);
      lo = Math.min(lo, candles[j].low);
    }
    return { upper: hi, lower: lo };
  }

  function lastSignalDonchian(candles, p) {
    p = p || {};
    var period = p.period || 20;
    var tpR = p.tp_r != null ? p.tp_r : 2;
    var atrSl = p.atr_sl != null ? p.atr_sl : 1.5;
    var atrP = p.atr_period != null ? p.atr_period : 14;
    if (candles.length < period + 2) return null;
    var atr = calcAtr(candles, atrP);
    var i = candles.length - 1;
    var ip = i - 1;
    if (atr[i] == null) return null;
    var upPrev = donchianBoundsAt(candles, ip, period);
    var loPrev = upPrev;
    if (!upPrev) return null;
    var c = candles[i];
    var cp = candles[ip];
    if (c.close > upPrev.upper && cp.close <= upPrev.upper) {
      var entry = c.close;
      var sl = entry - atrSl * atr[i];
      var risk = entry - sl;
      var tp = entry + tpR * risk;
      return {
        direction: "LONG",
        entry: Math.round(entry * 100) / 100,
        sl: Math.round(sl * 100) / 100,
        tp: Math.round(tp * 100) / 100,
        rr: tpR,
      };
    }
    if (c.close < loPrev.lower && cp.close >= loPrev.lower) {
      entry = c.close;
      sl = entry + atrSl * atr[i];
      risk = sl - entry;
      tp = entry - tpR * risk;
      return {
        direction: "SHORT",
        entry: Math.round(entry * 100) / 100,
        sl: Math.round(sl * 100) / 100,
        tp: Math.round(tp * 100) / 100,
        rr: tpR,
      };
    }
    return null;
  }

  function lastSignalHeikinAshi(candles, p) {
    p = p || {};
    var emaLen = p.ema_period || 21;
    var atrP = p.atr_period || 14;
    var tpR = p.tp_r != null ? p.tp_r : 2;
    var atrMult = p.atr_sl_mult != null ? p.atr_sl_mult : 2;
    var n = candles.length;
    if (n < Math.max(emaLen, atrP) + 3) return null;
    var ha = [];
    var h0 = {
      close: (candles[0].open + candles[0].high + candles[0].low + candles[0].close) / 4,
      open: (candles[0].open + candles[0].close) / 2,
    };
    h0.high = Math.max(candles[0].high, h0.open, h0.close);
    h0.low = Math.min(candles[0].low, h0.open, h0.close);
    ha.push(h0);
    for (var i = 1; i < n; i++) {
      var cl = (candles[i].open + candles[i].high + candles[i].low + candles[i].close) / 4;
      var op = (ha[i - 1].open + ha[i - 1].close) / 2;
      var hi = Math.max(candles[i].high, op, cl);
      var lo = Math.min(candles[i].low, op, cl);
      ha.push({ open: op, close: cl, high: hi, low: lo });
    }
    var closes = candles.map(function (c) {
      return c.close;
    });
    var ema21 = calcEma(closes, emaLen);
    var atr = calcAtr(candles, atrP);
    var i = n - 1;
    if (ema21[i] == null || ema21[i - 1] == null || atr[i] == null) return null;
    var c = candles[i];
    function nearEq(a, b) {
      return Math.abs(a - b) < 1e-6;
    }
    if (
      ha[i].close > ha[i].open &&
      ha[i - 1].close > ha[i - 1].open &&
      ha[i - 2].close > ha[i - 2].open &&
      nearEq(ha[i].open, ha[i].low) &&
      nearEq(ha[i - 1].open, ha[i - 1].low) &&
      ema21[i] > ema21[i - 1]
    ) {
      var entryL = c.close;
      var slL = entryL - atrMult * atr[i];
      var riskL = entryL - slL;
      var tpL = entryL + tpR * riskL;
      return {
        direction: "LONG",
        entry: Math.round(entryL * 100) / 100,
        sl: Math.round(slL * 100) / 100,
        tp: Math.round(tpL * 100) / 100,
        rr: tpR,
      };
    }
    if (
      ha[i].close < ha[i].open &&
      ha[i - 1].close < ha[i - 1].open &&
      ha[i - 2].close < ha[i - 2].open &&
      nearEq(ha[i].open, ha[i].high) &&
      nearEq(ha[i - 1].open, ha[i - 1].high) &&
      ema21[i] < ema21[i - 1]
    ) {
      var entryS = c.close;
      var slS = entryS + atrMult * atr[i];
      var riskS = slS - entryS;
      var tpS = entryS - tpR * riskS;
      return {
        direction: "SHORT",
        entry: Math.round(entryS * 100) / 100,
        sl: Math.round(slS * 100) / 100,
        tp: Math.round(tpS * 100) / 100,
        rr: tpR,
      };
    }
    return null;
  }

  function lastSignalEmaPullbackAdx(candles, p) {
    p = p || {};
    var fast = p.fast || 21;
    var slow = p.slow || 55;
    var atrP = p.atr_period || 14;
    var adxP = p.adx_period || 14;
    var adxMin = p.adx_min != null ? p.adx_min : 20;
    var touchAtr = p.touch_atr != null ? p.touch_atr : 0.35;
    var tpR = p.tp_r != null ? p.tp_r : 2.2;
    var slAtr = p.sl_atr != null ? p.sl_atr : 1.4;
    var need = Math.max(slow, atrP, adxP * 3) + 2;
    if (candles.length < need) return null;
    var closes = candles.map(function (c) {
      return c.close;
    });
    var emaFast = calcEma(closes, fast);
    var emaSlow = calcEma(closes, slow);
    var atr = calcAtr(candles, atrP);
    var adxPack = calcAdx(candles, adxP);
    var adx = adxPack.adx;
    var plusDi = adxPack.plusDi;
    var minusDi = adxPack.minusDi;
    var i = candles.length - 1;
    var c = candles[i];
    if (
      emaFast[i] == null ||
      emaSlow[i] == null ||
      emaFast[i - 1] == null ||
      emaSlow[i - 1] == null ||
      atr[i] == null ||
      adx[i] == null ||
      plusDi[i] == null ||
      minusDi[i] == null
    ) {
      return null;
    }
    var bullTrend =
      emaFast[i] > emaSlow[i] &&
      emaFast[i] >= emaFast[i - 1] &&
      emaSlow[i] >= emaSlow[i - 1] &&
      c.close > emaSlow[i] &&
      plusDi[i] > minusDi[i] &&
      adx[i] >= adxMin;
    if (bullTrend && c.low <= emaFast[i] + touchAtr * atr[i] && c.close > emaFast[i]) {
      var entry = c.close;
      var sl = entry - slAtr * atr[i];
      var risk = entry - sl;
      var tp = entry + tpR * risk;
      return {
        direction: "LONG",
        entry: Math.round(entry * 100) / 100,
        sl: Math.round(sl * 100) / 100,
        tp: Math.round(tp * 100) / 100,
        rr: Math.round(tpR * 100) / 100,
      };
    }
    var bearTrend =
      emaFast[i] < emaSlow[i] &&
      emaFast[i] <= emaFast[i - 1] &&
      emaSlow[i] <= emaSlow[i - 1] &&
      c.close < emaSlow[i] &&
      minusDi[i] > plusDi[i] &&
      adx[i] >= adxMin;
    if (bearTrend && c.high >= emaFast[i] - touchAtr * atr[i] && c.close < emaFast[i]) {
      entry = c.close;
      sl = entry + slAtr * atr[i];
      risk = sl - entry;
      tp = entry - tpR * risk;
      return {
        direction: "SHORT",
        entry: Math.round(entry * 100) / 100,
        sl: Math.round(sl * 100) / 100,
        tp: Math.round(tp * 100) / 100,
        rr: Math.round(tpR * 100) / 100,
      };
    }
    return null;
  }

  function lastSignalSqueezeBreakout(candles, p) {
    p = p || {};
    var bb = p.bb_period || 20;
    var mult = p.bb_std_mult != null ? p.bb_std_mult : 2;
    var emaLen = p.ema_period || 50;
    var atrP = p.atr_period || 14;
    var volLookback = p.vol_lookback || 20;
    var volMult = p.vol_mult != null ? p.vol_mult : 1.4;
    var squeezeLookback = p.squeeze_lookback || 40;
    var squeezeMult = p.squeeze_mult != null ? p.squeeze_mult : 1.05;
    var tpR = p.tp_r != null ? p.tp_r : 2.2;
    var slAtr = p.sl_atr != null ? p.sl_atr : 1.4;
    var need = Math.max(bb, emaLen, atrP, volLookback, squeezeLookback) + 3;
    if (candles.length < need) return null;
    var closes = candles.map(function (c) {
      return c.close;
    });
    var sma = calcSma(closes, bb);
    var std = calcStd(closes, bb);
    var ema = calcEma(closes, emaLen);
    var atr = calcAtr(candles, atrP);
    var widths = new Array(candles.length);
    for (var i = 0; i < candles.length; i++) {
      widths[i] = null;
      if (sma[i] == null || std[i] == null || sma[i] === 0) continue;
      var upperI = sma[i] + mult * std[i];
      var lowerI = sma[i] - mult * std[i];
      widths[i] = (upperI - lowerI) / sma[i];
    }
    var idx = candles.length - 1;
    if (sma[idx] == null || std[idx] == null || ema[idx] == null || ema[idx - 1] == null || atr[idx] == null) return null;
    var prevWidth = widths[idx - 1];
    if (prevWidth == null) return null;
    var minWidth = Infinity;
    for (var j = idx - squeezeLookback; j < idx; j++) {
      if (widths[j] == null) return null;
      minWidth = Math.min(minWidth, widths[j]);
    }
    if (prevWidth > minWidth * squeezeMult) return null;
    var volSum = 0;
    for (var k = idx - volLookback; k < idx; k++) volSum += candles[k].volume;
    var avgVol = volSum / volLookback;
    if (avgVol <= 0) return null;
    var c = candles[idx];
    var upper = sma[idx] + mult * std[idx];
    var lower = sma[idx] - mult * std[idx];
    if (c.close > upper && c.volume >= avgVol * volMult && c.close > ema[idx] && ema[idx] > ema[idx - 1]) {
      var entry = c.close;
      var sl = entry - slAtr * atr[idx];
      var risk = entry - sl;
      var tp = entry + tpR * risk;
      return {
        direction: "LONG",
        entry: Math.round(entry * 100) / 100,
        sl: Math.round(sl * 100) / 100,
        tp: Math.round(tp * 100) / 100,
        rr: Math.round(tpR * 100) / 100,
      };
    }
    if (c.close < lower && c.volume >= avgVol * volMult && c.close < ema[idx] && ema[idx] < ema[idx - 1]) {
      entry = c.close;
      sl = entry + slAtr * atr[idx];
      risk = sl - entry;
      tp = entry - tpR * risk;
      return {
        direction: "SHORT",
        entry: Math.round(entry * 100) / 100,
        sl: Math.round(sl * 100) / 100,
        tp: Math.round(tp * 100) / 100,
        rr: Math.round(tpR * 100) / 100,
      };
    }
    return null;
  }

  // ADX Trend (backtest: ETHUSDT +$1088, 37.1% WR)
  function lastSignalAdxTrend(candles, params) {
    var adxP = params.adx_period || 14, threshold = params.adx_threshold || 25;
    var n = candles.length; if (n < adxP * 3) return null;
    var tr = [], pDM = [], mDM = [];
    for (var i = 1; i < n; i++) {
      var h = candles[i].high, l = candles[i].low, pc = candles[i-1].close;
      tr.push(Math.max(h-l, Math.abs(h-pc), Math.abs(l-pc)));
      var up = h - candles[i-1].high, dn = candles[i-1].low - l;
      pDM.push(up > dn && up > 0 ? up : 0);
      mDM.push(dn > up && dn > 0 ? dn : 0);
    }
    function ws(arr, p) { var s=0; for (var j=arr.length-p; j<arr.length; j++) s+=arr[j]; return s/p; }
    var atr = ws(tr, adxP), pDI = atr>0?(ws(pDM,adxP)/atr)*100:0, mDI = atr>0?(ws(mDM,adxP)/atr)*100:0;
    var dx = (pDI+mDI)>0?Math.abs(pDI-mDI)/(pDI+mDI)*100:0;
    if (dx >= threshold && pDI > mDI) return {direction:'LONG', label:'ADX +DI='+Math.round(pDI)+' -DI='+Math.round(mDI)+' DX='+Math.round(dx)};
    if (dx >= threshold && mDI > pDI) return {direction:'SHORT', label:'ADX -DI='+Math.round(mDI)+' +DI='+Math.round(pDI)+' DX='+Math.round(dx)};
    return null;
  }
  // Connors RSI(2) (backtest: BNBUSDT 68.5% WR, +$335)
  function lastSignalConnorsRsi2(candles, params) {
    var rsiP = params.rsi_period||2, rsiL = params.rsi_long||10, rsiS = params.rsi_short||90;
    var n = candles.length; if (n < 210) return null;
    var c = candles.map(function(x){return x.close;}), g=0, l=0;
    for (var i=n-rsiP; i<n; i++) { var d=c[i]-c[i-1]; if(d>0)g+=d; else l-=d; }
    var rsi = l>0?100-(100/(1+g/l)):100;
    var s=0; for(var j=n-200;j<n;j++) s+=c[j]; var sma=s/200;
    if (rsi<=rsiL && c[n-1]>sma) return {direction:'LONG',label:'CRSI('+rsiP+')='+rsi.toFixed(1)+' <'+rsiL};
    if (rsi>=rsiS && c[n-1]<sma) return {direction:'SHORT',label:'CRSI('+rsiP+')='+rsi.toFixed(1)+' >'+rsiS};
    return null;
  }
  // MACD Trend (backtest: SOLUSDT +$188, 35.1% WR)
  function lastSignalMacdTrend(candles, params) {
    var fast=params.fast||12, slow=params.slow||26, n=candles.length;
    if (n < slow*3+5) return null;
    var c = candles.map(function(x){return x.close;});
    function ema(arr,p){var k=2/(p+1),e=arr[0];for(var i=1;i<arr.length;i++)e=arr[i]*k+e*(1-k);return e;}
    var ml = ema(c.slice(-fast*3),fast)-ema(c.slice(-slow*3),slow);
    var mp = ema(c.slice(-fast*3-1,-1),fast)-ema(c.slice(-slow*3-1,-1),slow);
    if (ml>0 && mp<=0) return {direction:'LONG',label:'MACD bull cross '+ml.toFixed(4)};
    if (ml<0 && mp>=0) return {direction:'SHORT',label:'MACD bear cross '+ml.toFixed(4)};
    return null;
  }

  // CCI Divergence (batch2 #1 passer: BTC +$1125, PF 2.15)
  function lastSignalCciDivergence(candles, p) {
    p = p || {};
    var cciPeriod = p.cci_period || 20;
    var cciLong = p.cci_long != null ? p.cci_long : -100;
    var cciShort = p.cci_short != null ? p.cci_short : 100;
    var atrP = p.atr_period || 14;
    var tpR = p.tp_r != null ? p.tp_r : 2;
    var slAtr = p.sl_atr != null ? p.sl_atr : 1.5;
    var n = candles.length;
    if (n < cciPeriod + 2) return null;
    var atr = calcAtr(candles, atrP);
    var i = n - 1;
    if (atr[i] == null) return null;
    function cciAt(idx) {
      if (idx < cciPeriod - 1) return null;
      var tp = [];
      for (var j = idx - cciPeriod + 1; j <= idx; j++) {
        tp.push((candles[j].high + candles[j].low + candles[j].close) / 3);
      }
      var smaTp = 0; for (var k = 0; k < tp.length; k++) smaTp += tp[k]; smaTp /= cciPeriod;
      var mad = 0; for (var k = 0; k < tp.length; k++) mad += Math.abs(tp[k] - smaTp); mad /= cciPeriod;
      if (mad === 0) return 0;
      return (tp[tp.length - 1] - smaTp) / (0.015 * mad);
    }
    var cciNow = cciAt(i);
    var cciPrev = cciAt(i - 1);
    if (cciNow == null || cciPrev == null) return null;
    var c = candles[i];
    if (cciNow > cciLong && cciPrev <= cciLong) {
      var entry = c.close;
      var sl = entry - slAtr * atr[i];
      var risk = entry - sl;
      var tp = entry + tpR * risk;
      return { direction: 'LONG', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    if (cciNow < cciShort && cciPrev >= cciShort) {
      entry = c.close; sl = entry + slAtr * atr[i]; risk = sl - entry; tp = entry - tpR * risk;
      return { direction: 'SHORT', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    return null;
  }

  // ADX Volatility Breakout (batch2 passer: ETH PF 1.76, DD $207)
  function lastSignalAdxVolBreakout(candles, p) {
    p = p || {};
    var adxP = p.adx_period || 14;
    var adxThresh = p.adx_threshold || 25;
    var atrP = p.atr_period || 14;
    var volLb = p.vol_lookback || 20;
    var volMult = p.vol_mult != null ? p.vol_mult : 1.5;
    var tpR = p.tp_r != null ? p.tp_r : 2;
    var slAtr = p.sl_atr != null ? p.sl_atr : 1.5;
    var n = candles.length;
    if (n < Math.max(adxP * 3, volLb) + 2) return null;
    var atr = calcAtr(candles, atrP);
    var adxPack = calcAdx(candles, adxP);
    var i = n - 1;
    if (atr[i] == null || adxPack.adx[i] == null || adxPack.plusDi[i] == null || adxPack.minusDi[i] == null) return null;
    if (adxPack.adx[i] < adxThresh) return null;
    var volSum = 0;
    for (var j = i - volLb; j < i; j++) volSum += candles[j].volume;
    var avgVol = volSum / volLb;
    if (avgVol <= 0) return null;
    var c = candles[i];
    if (c.volume < volMult * avgVol) return null;
    if (adxPack.plusDi[i] > adxPack.minusDi[i]) {
      var entry = c.close; var sl = entry - slAtr * atr[i]; var risk = entry - sl; var tp = entry + tpR * risk;
      return { direction: 'LONG', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    if (adxPack.minusDi[i] > adxPack.plusDi[i]) {
      entry = c.close; sl = entry + slAtr * atr[i]; risk = sl - entry; tp = entry - tpR * risk;
      return { direction: 'SHORT', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    return null;
  }

  // CMF Cross (batch2 passer: AVAX +$962, PF 1.53)
  function lastSignalCmfCross(candles, p) {
    p = p || {};
    var cmfP = p.cmf_period || 20;
    var atrP = p.atr_period || 14;
    var tpR = p.tp_r != null ? p.tp_r : 2;
    var slAtr = p.sl_atr != null ? p.sl_atr : 1.5;
    var n = candles.length;
    if (n < cmfP + 2) return null;
    var atr = calcAtr(candles, atrP);
    var i = n - 1;
    if (atr[i] == null) return null;
    function cmfAt(idx) {
      if (idx < cmfP - 1) return null;
      var mfVol = 0, volSum = 0;
      for (var j = idx - cmfP + 1; j <= idx; j++) {
        var rng = candles[j].high - candles[j].low;
        var mfm = rng === 0 ? 0 : ((candles[j].close - candles[j].low) - (candles[j].high - candles[j].close)) / rng;
        mfVol += mfm * candles[j].volume;
        volSum += candles[j].volume;
      }
      return volSum > 0 ? mfVol / volSum : 0;
    }
    var cmfNow = cmfAt(i);
    var cmfPrev = cmfAt(i - 1);
    if (cmfNow == null || cmfPrev == null) return null;
    var c = candles[i];
    if (cmfNow > 0.05 && cmfPrev <= 0.05) {
      var entry = c.close; var sl = entry - slAtr * atr[i]; var risk = entry - sl; var tp = entry + tpR * risk;
      return { direction: 'LONG', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    if (cmfNow < -0.05 && cmfPrev >= -0.05) {
      entry = c.close; sl = entry + slAtr * atr[i]; risk = sl - entry; tp = entry - tpR * risk;
      return { direction: 'SHORT', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    return null;
  }

  // MACD + EMA50 trend filter (blog-researched: XRP +$856, 41% WR)
  function lastSignalMacdEma50(candles, p) {
    p = p || {};
    var emaFilter = p.ema_filter || 50;
    var tpR = p.tp_r != null ? p.tp_r : 2;
    var slAtr = p.atr_sl != null ? p.atr_sl : 1.5;
    var atrP = p.atr_period || 14;
    var n = candles.length;
    if (n < emaFilter + 30) return null;
    var closes = candles.map(function(c) { return c.close; });
    var ema12 = calcEma(closes, 12);
    var ema26 = calcEma(closes, 26);
    var ema50 = calcEma(closes, emaFilter);
    var atr = calcAtr(candles, atrP);
    var i = n - 1;
    if (ema12[i] == null || ema26[i] == null || ema12[i-1] == null || ema26[i-1] == null || ema50[i] == null || atr[i] == null) return null;
    var macdNow = ema12[i] - ema26[i];
    var macdPrev = ema12[i-1] - ema26[i-1];
    var macdSeq = [];
    for (var j = 0; j < n; j++) {
      if (ema12[j] != null && ema26[j] != null) macdSeq.push(ema12[j] - ema26[j]);
    }
    if (macdSeq.length < 9) return null;
    var sigEma = macdSeq[macdSeq.length - 9];
    var kk = 2 / 10;
    for (var s = macdSeq.length - 8; s < macdSeq.length; s++) {
      sigEma = macdSeq[s] * kk + sigEma * (1 - kk);
    }
    var sigPrev = macdSeq[macdSeq.length - 10];
    var kkp = 2 / 10;
    for (var sp = macdSeq.length - 9; sp < macdSeq.length - 1; sp++) {
      sigPrev = macdSeq[sp] * kkp + sigPrev * (1 - kkp);
    }
    var c = candles[i];
    if (macdNow > sigEma && macdPrev <= sigPrev && c.close > ema50[i]) {
      var entry = c.close; var sl = entry - slAtr * atr[i]; var risk = entry - sl; var tp = entry + tpR * risk;
      return { direction: 'LONG', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    if (macdNow < sigEma && macdPrev >= sigPrev && c.close < ema50[i]) {
      entry = c.close; sl = entry + slAtr * atr[i]; risk = sl - entry; tp = entry - tpR * risk;
      return { direction: 'SHORT', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    return null;
  }

  // ===== NEW TREND-FOLLOWING STRATEGIES (April 2026) =====
  // Designed for trending markets (Hurst > 0.55) with loose gates

  // 1. Triple EMA Trend Follower — enters when 3 EMAs align and price is with the trend
  // Fires MORE than ema_pullback_adx because no ADX/DI/tight-pullback requirement
  function lastSignalTripleEmaTrend(candles, p) {
    p = p || {};
    var fast = p.fast || 9, mid = p.mid || 21, slow = p.slow || 55;
    var atrP = p.atr_period || 14, tpR = p.tp_r != null ? p.tp_r : 2.0, slAtr = p.sl_atr != null ? p.sl_atr : 1.2;
    var n = candles.length;
    if (n < slow + 10) return null;
    var closes = candles.map(function(c) { return c.close; });
    var emaF = calcEma(closes, fast);
    var emaM = calcEma(closes, mid);
    var emaS = calcEma(closes, slow);
    var rsi = calcRsi(closes, 14);
    var atr = calcAtr(candles, atrP);
    var i = n - 1;
    if (emaF[i] == null || emaM[i] == null || emaS[i] == null || atr[i] == null || rsi[i] == null) return null;
    var c = candles[i];
    // Bullish: EMA9 > EMA21 > EMA55, price near EMA21 (within 1% of EMA21), RSI 40-70
    if (emaF[i] > emaM[i] && emaM[i] > emaS[i] && rsi[i] > 40 && rsi[i] < 70) {
      var dist = Math.abs(c.close - emaM[i]) / emaM[i];
      if (dist < 0.015) { // within 1.5% of EMA21 = pullback zone
        var entry = c.close; var sl = emaS[i] - 0.5 * atr[i]; var risk = entry - sl; var tp = entry + tpR * risk;
        if (risk > 0) return { direction: 'LONG', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
      }
    }
    // Bearish: EMA9 < EMA21 < EMA55, price near EMA21, RSI 30-60
    if (emaF[i] < emaM[i] && emaM[i] < emaS[i] && rsi[i] > 30 && rsi[i] < 60) {
      var distS = Math.abs(c.close - emaM[i]) / emaM[i];
      if (distS < 0.015) {
        var entry = c.close; var sl = emaS[i] + 0.5 * atr[i]; var risk = sl - entry; var tp = entry - tpR * risk;
        if (risk > 0) return { direction: 'SHORT', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
      }
    }
    return null;
  }

  // 2. ADX Slope Momentum — enters when ADX is RISING (momentum building), no extreme gates
  function lastSignalAdxSlopeMomentum(candles, p) {
    p = p || {};
    var atrP = p.atr_period || 14, adxP = p.adx_period || 14;
    var tpR = p.tp_r != null ? p.tp_r : 2.5, slAtr = p.sl_atr != null ? p.sl_atr : 1.0;
    var slopeBack = p.slope_lookback || 5;
    var n = candles.length;
    if (n < adxP * 3 + slopeBack) return null;
    var closes = candles.map(function(c) { return c.close; });
    var adxData = calcAdx(candles, adxP);
    var ema9 = calcEma(closes, 9);
    var ema21 = calcEma(closes, 21);
    var atr = calcAtr(candles, atrP);
    var i = n - 1;
    if (adxData.adx[i] == null || adxData.adx[i - slopeBack] == null || ema9[i] == null || ema21[i] == null || atr[i] == null) return null;
    var adxSlope = adxData.adx[i] - adxData.adx[i - slopeBack];
    if (adxSlope <= 0) return null; // ADX must be rising
    if (adxData.adx[i] < 15) return null; // minimum directional movement
    var c = candles[i];
    // EMA9 slope: compare current to 3 bars ago
    if (ema9[i - 3] == null) return null;
    var emaSlope = (ema9[i] - ema9[i - 3]) / ema9[i - 3] * 100;
    // LONG: EMA9 > EMA21, EMA slope positive, +DI > -DI
    if (ema9[i] > ema21[i] && emaSlope > 0.1 && adxData.plusDi[i] > adxData.minusDi[i]) {
      var entry = c.close; var sl = entry - slAtr * atr[i]; var risk = entry - sl; var tp = entry + tpR * risk;
      if (risk > 0) return { direction: 'LONG', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    // SHORT: EMA9 < EMA21, EMA slope negative, -DI > +DI
    if (ema9[i] < ema21[i] && emaSlope < -0.1 && adxData.minusDi[i] > adxData.plusDi[i]) {
      var entry = c.close; var sl = entry + slAtr * atr[i]; var risk = sl - entry; var tp = entry - tpR * risk;
      if (risk > 0) return { direction: 'SHORT', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    return null;
  }

  // 3. RSI Pullback in Trend — enters when RSI pulls back to neutral (45-55) in established trend
  // Much looser than RSI extremes (30/70); fires 5x more often
  function lastSignalRsiPullback(candles, p) {
    p = p || {};
    var atrP = p.atr_period || 14, tpR = p.tp_r != null ? p.tp_r : 2.0, slAtr = p.sl_atr != null ? p.sl_atr : 1.2;
    var rsiPeriod = p.rsi_period || 14;
    var emaSlow = p.ema_slow || 50;
    var n = candles.length;
    if (n < emaSlow + 10) return null;
    var closes = candles.map(function(c) { return c.close; });
    var rsi = calcRsi(closes, rsiPeriod);
    var ema9 = calcEma(closes, 9);
    var ema21 = calcEma(closes, 21);
    var ema50 = calcEma(closes, emaSlow);
    var atr = calcAtr(candles, atrP);
    var i = n - 1;
    if (rsi[i] == null || ema9[i] == null || ema21[i] == null || ema50[i] == null || atr[i] == null) return null;
    // Check if RSI was recently elevated/depressed (last 5 bars)
    var wasHigh = false, wasLow = false;
    for (var j = i - 5; j < i; j++) {
      if (j >= 0 && rsi[j] != null) {
        if (rsi[j] > 60) wasHigh = true;
        if (rsi[j] < 40) wasLow = true;
      }
    }
    var c = candles[i];
    // LONG: uptrend (EMA9 > EMA21 > EMA50), RSI was > 60 recently, NOW pulled back to 42-55
    if (ema9[i] > ema21[i] && ema21[i] > ema50[i] && wasHigh && rsi[i] >= 42 && rsi[i] <= 55) {
      if (c.close > ema21[i]) { // still above trend EMA
        var entry = c.close; var sl = ema50[i] - 0.5 * atr[i]; var risk = entry - sl;
        var tp = entry + tpR * risk;
        if (risk > 0) return { direction: 'LONG', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
      }
    }
    // SHORT: downtrend (EMA9 < EMA21 < EMA50), RSI was < 40 recently, NOW rallied to 45-58
    if (ema9[i] < ema21[i] && ema21[i] < ema50[i] && wasLow && rsi[i] >= 45 && rsi[i] <= 58) {
      if (c.close < ema21[i]) {
        var entry = c.close; var sl = ema50[i] + 0.5 * atr[i]; var risk = sl - entry;
        var tp = entry - tpR * risk;
        if (risk > 0) return { direction: 'SHORT', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
      }
    }
    return null;
  }

  // 5. VWAP Trend Continuation — uses volume-weighted price to detect trend entries
  // Approximates VWAP with volume-weighted EMA; enters on pullback to VWAP in trend
  function lastSignalVwapTrend(candles, p) {
    p = p || {};
    var vwapPeriod = p.vwap_period || 20;
    var atrP = p.atr_period || 14, tpR = p.tp_r != null ? p.tp_r : 2.0, slAtr = p.sl_atr != null ? p.sl_atr : 1.2;
    var n = candles.length;
    if (n < vwapPeriod + 30) return null;
    var closes = candles.map(function(c) { return c.close; });
    var atr = calcAtr(candles, atrP);
    var ema21 = calcEma(closes, 21);
    var ema50 = calcEma(closes, 50);
    var i = n - 1;
    if (atr[i] == null || ema21[i] == null || ema50[i] == null) return null;
    // Compute rolling VWAP over the lookback window
    var cumVol = 0, cumPV = 0;
    for (var j = i - vwapPeriod + 1; j <= i; j++) {
      var vol = candles[j].volume || 1;
      cumVol += vol;
      cumPV += candles[j].close * vol;
    }
    var vwap = cumPV / cumVol;
    var c = candles[i];
    // Calculate distance from VWAP
    var vwapDist = (c.close - vwap) / vwap;
    // LONG: Price near or slightly below VWAP in uptrend (EMA21 > EMA50)
    if (ema21[i] > ema50[i] && vwapDist >= -0.01 && vwapDist <= 0.005) {
      // Price touching VWAP from above = pullback in uptrend
      var entry = c.close; var sl = entry - slAtr * atr[i]; var risk = entry - sl; var tp = entry + tpR * risk;
      if (risk > 0) return { direction: 'LONG', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    // SHORT: Price near or slightly above VWAP in downtrend (EMA21 < EMA50)
    if (ema21[i] < ema50[i] && vwapDist >= -0.005 && vwapDist <= 0.01) {
      var entry = c.close; var sl = entry + slAtr * atr[i]; var risk = sl - entry; var tp = entry - tpR * risk;
      if (risk > 0) return { direction: 'SHORT', entry: Math.round(entry*100)/100, sl: Math.round(sl*100)/100, tp: Math.round(tp*100)/100, rr: tpR };
    }
    return null;
  }

  var DISPATCH = {
    bollinger: lastSignalBollinger,
    rsi2: lastSignalRsi2,
    volume: lastSignalVolume,
    sr: lastSignalSr,
    donchian: lastSignalDonchian,
    heikin_ashi: lastSignalHeikinAshi,
    ema_pullback_adx: lastSignalEmaPullbackAdx,
    squeeze_breakout: lastSignalSqueezeBreakout,
    adx_trend: lastSignalAdxTrend,
    connors_rsi2: lastSignalConnorsRsi2,
    macd_trend: lastSignalMacdTrend,
    cci_divergence: lastSignalCciDivergence,
    adx_vol_breakout: lastSignalAdxVolBreakout,
    cmf_cross: lastSignalCmfCross,
    macd_ema50_trend: lastSignalMacdEma50,
    triple_ema_trend: lastSignalTripleEmaTrend,
    adx_slope_momentum: lastSignalAdxSlopeMomentum,
    rsi_pullback: lastSignalRsiPullback,
    vwap_trend: lastSignalVwapTrend,
  };

  function evaluateLastBar(candles, strategyKey, params) {
    var fn = DISPATCH[strategyKey];
    if (!fn) return null;
    return fn(candles, params || {});
  }

  global.HyroLiveSignals = {
    calcSma: calcSma,
    calcEma: calcEma,
    calcRsi: calcRsi,
    calcAtr: calcAtr,
    evaluateLastBar: evaluateLastBar,
  };
})(typeof window !== "undefined" ? window : this);
