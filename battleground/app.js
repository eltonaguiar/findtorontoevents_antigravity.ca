// Survivor-validated strategies — passed 8/8 anti-overfit checks on 24 symbols, 5yr data
// Source: alpha_engine/survivor_backtest.py results (2026-02-28)
const SYSTEMS_AE = [
  {
    name: "Keltner Mean Rev",
    letter: "1",
    color: "#22c55e",
    trades: 111,
    winRate: "67.6%",
    sharpe: 2.06,
    status: "PROVEN",
    badge: "badge-passed",
    source: "Keltner 1960 / Raschke",
    desc: "Mean-reversion strategy using Keltner Channels (EMA + ATR bands). Buys when price drops below the lower channel and sells when it returns to the mean. Based on Chester Keltner's 1960 channel breakout system refined by Linda Raschke.",
  },
  {
    name: "Connors R3",
    letter: "2",
    color: "#3b82f6",
    trades: 803,
    winRate: "71.4%",
    sharpe: 1.53,
    status: "PROVEN",
    badge: "badge-passed",
    source: "Connors & Alvarez 2008",
    desc: "3-period RSI mean-reversion. Buys when RSI(3) drops below 10 (extremely oversold) and sells when it rises above 90. From Larry Connors' 'Short Term Trading Strategies That Work' (2008). High win rate with small, frequent gains.",
  },
  {
    name: "Connors RSI-2",
    letter: "3",
    color: "#a855f7",
    trades: 895,
    winRate: "68.4%",
    sharpe: 1.17,
    status: "PROVEN",
    badge: "badge-passed",
    source: "Connors & Alvarez 2008",
    desc: "Ultra-short 2-period RSI mean-reversion. Even more aggressive than R3 -- buys when RSI(2) < 5 and sells when RSI(2) > 95. Highest trade frequency of all survivors. Statistically proven with p-value < 0.001.",
  },
  {
    name: "Supertrend ATR",
    letter: "4",
    color: "#f97316",
    trades: 34,
    winRate: "52.9%",
    sharpe: 1.18,
    status: "PROVEN",
    badge: "badge-passed",
    source: "Trend following",
    desc: "ATR-based trend-following indicator. Plots a trailing stop above/below price using Average True Range. Goes long when price crosses above the Supertrend line, short when it crosses below. Low frequency but catches big moves.",
  },
  {
    name: "Bollinger Mean Rev",
    letter: "5",
    color: "#ec4899",
    trades: 361,
    winRate: "60.7%",
    sharpe: 0.72,
    status: "PROVEN",
    badge: "badge-passed",
    source: "Bollinger 1980s",
    desc: "Bollinger Bands mean-reversion. Buys when price touches the lower band (2 std dev below 20-period SMA) and sells at the middle band. Based on John Bollinger's statistical volatility bands from the 1980s.",
  },
  {
    name: "RSI Extreme Rev",
    letter: "6",
    color: "#14b8a6",
    trades: 118,
    winRate: "58.5%",
    sharpe: 0.7,
    status: "PROVEN",
    badge: "badge-passed",
    source: "Wilder 1978",
    desc: "RSI(14) extreme reversal. Buys at RSI < 20 (deep oversold) and sells at RSI > 80 (overbought). Based on J. Welles Wilder's original 1978 RSI framework. Fewer trades than Connors variants but targets bigger reversals.",
  },
  {
    name: "MACD Divergence",
    letter: "7",
    color: "#eab308",
    trades: 515,
    winRate: "67.8%",
    sharpe: 0.57,
    status: "PROVEN",
    badge: "badge-passed",
    source: "Appel 1979",
    desc: "MACD histogram divergence. Detects when price makes new lows but MACD histogram makes higher lows (bullish divergence) or vice versa. Created by Gerald Appel in 1979. Signals trend exhaustion before reversal.",
  },
  {
    name: "VWAP Mean Rev",
    letter: "8",
    color: "#06b6d4",
    trades: 732,
    winRate: "64.3%",
    sharpe: 0.53,
    status: "PROVEN",
    badge: "badge-passed",
    source: "VWAP z-score",
    desc: "Volume-Weighted Average Price mean-reversion. Calculates z-score of price vs VWAP and buys when z-score < -2 (price far below VWAP) and sells at mean. Institutional-grade benchmark used by algo traders.",
  },
  {
    name: "Williams %R",
    letter: "9",
    color: "#8b5cf6",
    trades: 475,
    winRate: "59.8%",
    sharpe: 0.39,
    status: "PROVEN",
    badge: "badge-passed",
    source: "Larry Williams 1979",
    desc: "Williams %R oscillator mean-reversion. Buys when %R drops below -80 (oversold) and sells above -20 (overbought). Created by Larry Williams in 1979. Measures current close relative to the high-low range over N periods.",
  },
  {
    name: "Vol-Scaled Momentum",
    letter: "10",
    color: "#ef4444",
    trades: 568,
    winRate: "65.8%",
    sharpe: 0.32,
    status: "PROVEN",
    badge: "badge-passed",
    source: "Moreira & Muir 2017 JFE",
    desc: "Volatility-managed momentum. Scales position size inversely with recent realized volatility -- bigger positions when calm, smaller when volatile. Based on Moreira & Muir (2017, Journal of Financial Economics). Improves Sharpe of raw momentum by ~50%.",
  },
];

const STATUS_OPTIONS = [
  { id: "all", label: "All" },
  { id: "backtest_passed", label: "Passed" },
  { id: "validating", label: "Validating" },
  { id: "insufficient_data", label: "Insufficient" },
  { id: "failed", label: "Failed" },
  { id: "backtest_error", label: "Error" },
  { id: "paper_trading", label: "Paper" },
  { id: "graduated", label: "Graduated/Live" },
  { id: "awaiting_backtest", label: "Awaiting Backtest" },
  { id: "bundle_candidate", label: "Bundle Candidate" },
];

const STATUS_ORDER = {
  paper_trading: 0,
  backtest_passed: 1,
  bundle_candidate: 1.5,
  validating: 2,
  insufficient_data: 3,
  failed: 4,
  backtest_error: 5,
  graduated: 6,
  live: 6,
  awaiting_backtest: 7,
};

let DASHBOARD_DATA = null;
let BABY_STRATS = [];
let METRIC_MODE = "forward";
let CALENDAR_MODE = "forward";
let CALENDAR_NORM = "average"; // "average" (per-strategy avg) or "sum" (raw sum)
let DATA_BASIS = "real_only";
let ACTIVE_STATUS_FILTERS = new Set(["all"]);
let CALENDAR_STRATEGY = "all";
let FW_SORT_COL = "trades";
let FW_SORT_ASC = false;
let FW_FILTER = "all"; // "all" or "active" (has FW WR > 0)
let SURVIVORS_ONLY = true; // Default ON — only show strategies with WR>50% AND Sharpe>0 in forward
let ALL_STRATEGY_FILES = [];

function toNum(v) {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function toPct(v) {
  const n = toNum(v);
  if (n === null) return null;
  return Math.abs(n) <= 1.5 ? n * 100 : n;
}

function normalizeStatus(status) {
  const s = String(status || "").toLowerCase();
  if (s === "backtest_failed" || s === "failed") return "failed";
  if (s === "backtest_error") return "backtest_error";
  if (s === "backtest_passed") return "backtest_passed";
  if (s === "insufficient_data" || s === "failed_insufficient_trades")
    return "insufficient_data";
  if (
    s === "paper_trading" ||
    s === "graduated" ||
    s === "live" ||
    s === "validating"
  )
    return s;
  return "validating";
}

function normalizeMetrics(raw) {
  return {
    winRate: toPct(raw?.win_rate),
    sharpe: toNum(raw?.sharpe),
    maxDrawdown: toPct(raw?.max_drawdown),
    trades: Number(raw?.total_trades || 0),
  };
}

function normalizeDirectional(raw) {
  return {
    trades: Number(raw?.trades || 0),
    winRate: toPct(raw?.win_rate),
    sharpe: toNum(raw?.sharpe),
  };
}

function normalizeDaily(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((d) => ({
      date: String(d?.date || ""),
      pnlPct: toNum(d?.pnl_pct) ?? 0,
      trades: Number(d?.trades || 0),
      wins: Number(d?.wins || 0),
      losses: Number(d?.losses || 0),
    }))
    .filter((d) => d.date.length === 10);
}

function mapStrategy(s) {
  const verification = s?.verification || {};
  const dailyForward = normalizeDaily(s?.forward_daily_pnl);
  const forwardPnlFromDaily = dailyForward.length
    ? dailyForward.reduce((acc, d) => acc + Number(d?.pnlPct || 0), 0)
    : null;
  const forwardPnlFromPaper = toNum(s?.paper_trading?.current_pnl);

  // Compute forward metrics from raw trades — always prefer computed from actual trades
  let fwd = normalizeMetrics(s?.forward_metrics || {});
  const fwTrades = Array.isArray(s?.forward_trades) ? s.forward_trades : [];
  if (fwTrades.length > 0) {
    const fm = computeForwardMetrics(fwTrades);
    if (fm.wr !== null) fwd.winRate = fm.wr;
    if (fm.sharpe !== null) fwd.sharpe = fm.sharpe;
    if (fwd.trades <= 0) fwd.trades = fwTrades.length;
  }

  return {
    name: s?.name || s?.strategy_name || "unknown",
    agent: s?.agent_id || "unknown",
    status: normalizeStatus(s?.status),
    backtest: normalizeMetrics(s?.backtest_metrics || {}),
    forward: fwd,
    directional: {
      overall: normalizeDirectional(s?.directional_metrics?.overall || {}),
      long: normalizeDirectional(s?.directional_metrics?.long || {}),
      short: normalizeDirectional(s?.directional_metrics?.short || {}),
    },
    dailyBacktest: normalizeDaily(s?.daily_pnl),
    dailyForward,
    forwardPnlPct: forwardPnlFromDaily ?? forwardPnlFromPaper,
    failureReason: s?.failure_reason || null,
    realDataVerified: verification?.real_data_verified === true,
    verificationLevel: String(verification?.verification_level || "unknown"),
    forwardTrades: Array.isArray(s?.forward_trades) ? s.forward_trades : [],
    forwardLivePicks: Array.isArray(s?.forward_live_picks)
      ? s.forward_live_picks
      : [],
    multiPairVerified: s?.multi_pair_verified === true,
    multiPairMetrics: s?.multi_pair_metrics || {},
  };
}

function statusBadge(status, hasForwardTrades) {
  if (status === "paper_trading") return { text: hasForwardTrades ? "FORWARD" : "PAPER", cls: "badge-paper" };
  if (status === "graduated" || status === "live")
    return { text: "GRADUATED", cls: "badge-graduated" };
  if (status === "backtest_passed")
    return { text: "PASSED", cls: "badge-passed" };
  if (status === "insufficient_data")
    return { text: "INSUFFICIENT", cls: "badge-insufficient" };
  if (status === "backtest_error")
    return { text: "ERROR", cls: "badge-failed" };
  if (status === "failed") return { text: "FAILED", cls: "badge-failed" };
  return { text: "VALIDATING", cls: "badge-validating" };
}

function fmtPct(v, digits = 1, signed = false) {
  if (v === null || v === undefined) return "n/a";
  const n = Number(v);
  if (!Number.isFinite(n)) return "n/a";
  const t = n.toFixed(digits) + "%";
  if (!signed) return t;
  return n > 0 ? "+" + t : t;
}

function fmtNum(v, digits = 2) {
  if (v === null || v === undefined) return "n/a";
  const n = Number(v);
  if (!Number.isFinite(n)) return "n/a";
  return n.toFixed(digits);
}

// Compute forward metrics from raw trade data (since JSON pre-computed fields are often null)
function computeForwardMetrics(trades) {
  if (!trades || !trades.length) return { wr: null, sharpe: null, pnl: 0, wins: 0, losses: 0 };
  let wins = 0, losses = 0, totalPnl = 0;
  const returns = [];
  for (const t of trades) {
    const p = Number(t.pnl_pct) || 0;
    totalPnl += p;
    returns.push(p);
    if (p > 0) wins++; else losses++;
  }
  const wr = trades.length > 0 ? (100 * wins / trades.length) : null;
  // Sharpe: mean / stdev (annualized assuming ~3 trades/day)
  let sharpe = null;
  if (returns.length >= 2) {
    const mean = totalPnl / returns.length;
    const variance = returns.reduce((s, r) => s + (r - mean) ** 2, 0) / (returns.length - 1);
    const stdev = Math.sqrt(variance);
    if (stdev > 0.0001) sharpe = (mean / stdev) * Math.sqrt(returns.length);
  }
  return { wr, sharpe, pnl: totalPnl, wins, losses };
}

function metricClass(v, positiveIsGood = true) {
  if (v === null || v === undefined || Number.isNaN(v)) return "gray";
  const n = Number(v);
  if (!Number.isFinite(n)) return "gray";
  if (positiveIsGood) return n >= 0 ? "positive" : "negative";
  return n <= 0 ? "positive" : "negative";
}

function updateTimestamps() {
  const now = new Date();
  document.getElementById("last-updated").textContent =
    "Updated: " + now.toLocaleString("en-US", { timeZone: "America/New_York" });
  const next = new Date(now);
  next.setHours(next.getHours() + 1, 0, 0, 0);
  document.getElementById("next-update").textContent =
    "Next update: " +
    next.toLocaleTimeString("en-US", {
      timeZone: "America/New_York",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    }) +
    " EST";
}

let SYSTEMS_MODE = "backtest"; // "backtest" or "forward"
let SYSTEMS_SORT_COL = "sharpe";
let SYSTEMS_SORT_ASC = false;

let BUNDLE_MODE = "forward"; // "backtest" or "forward" — forward is default
let HIDE_LOW_WR_BUNDLES = true; // Hide bundles with <50% WR by default
let DIRECTIONAL_SORT_COL = "name";
let DIRECTIONAL_SORT_ASC = true;
let GRADUATED_SORT_COL = "trades";
let GRADUATED_SORT_ASC = false;
let COMBO_SORT_COL = "trades";
let COMBO_SORT_ASC = false;
let COMBO_DATA_CACHE = null;
let ACTIVE_TRADES_SORT_COL = "strategy";
let ACTIVE_TRADES_SORT_ASC = true;

function sortSystems(col) {
  if (SYSTEMS_SORT_COL === col) { SYSTEMS_SORT_ASC = !SYSTEMS_SORT_ASC; } else { SYSTEMS_SORT_COL = col; SYSTEMS_SORT_ASC = false; }
  renderSystemsAE();
}

function sortDirectional(col) {
  if (DIRECTIONAL_SORT_COL === col) { DIRECTIONAL_SORT_ASC = !DIRECTIONAL_SORT_ASC; } else { DIRECTIONAL_SORT_COL = col; DIRECTIONAL_SORT_ASC = true; }
  renderDirectionalTable();
}

function sortGraduated(col) {
  if (GRADUATED_SORT_COL === col) { GRADUATED_SORT_ASC = !GRADUATED_SORT_ASC; } else { GRADUATED_SORT_COL = col; GRADUATED_SORT_ASC = false; }
  renderGraduatedStrats();
}

function sortCombo(col) {
  if (COMBO_SORT_COL === col) { COMBO_SORT_ASC = !COMBO_SORT_ASC; } else { COMBO_SORT_COL = col; COMBO_SORT_ASC = false; }
  if (COMBO_DATA_CACHE) renderComboMetrics(COMBO_DATA_CACHE);
}

function sortActiveTrades(col) {
  if (ACTIVE_TRADES_SORT_COL === col) { ACTIVE_TRADES_SORT_ASC = !ACTIVE_TRADES_SORT_ASC; } else { ACTIVE_TRADES_SORT_COL = col; ACTIVE_TRADES_SORT_ASC = true; }
  if (window._allOpenTrades) renderActiveTradesTable(window._allOpenTrades);
}

// Map survivor display names to baby strat names for forward lookups
// Map survivor display names to baby strat names.
// Some survivors have close baby-strat equivalents; others don't have one yet.
const SURVIVOR_STRAT_MAP = {
  "Keltner Mean Rev": "keltner",
  "Connors R3": "connors",
  "Connors RSI-2": "connors_rsi",
  "Supertrend ATR": "supertrend",
  "Bollinger Mean Rev": "bollinger",
  "RSI Extreme Rev": "rsi_extreme",
  "MACD Divergence": "macd",
  "VWAP Mean Rev": "vwap",
  "Williams %R": "williams",
  "Vol-Scaled Momentum": "volatility_scaled",
};

function findSurvivorBabyStrat(sysName) {
  const mapped = SURVIVOR_STRAT_MAP[sysName];
  if (!mapped) return null;
  // Try exact match, then partial match. Prefer strats with forward trades.
  const exact = BABY_STRATS.find((s) => s.name === mapped);
  if (exact) return exact;
  const partials = BABY_STRATS.filter((s) => s.name.includes(mapped));
  if (!partials.length) return null;
  // Prefer one with the most forward trades
  const withTrades = partials.filter(s => s.forwardTrades.length > 0);
  if (withTrades.length) return withTrades.sort((a, b) => b.forwardTrades.length - a.forwardTrades.length)[0];
  return partials[0];
}

function renderSystemsAE() {
  const tbody = document.getElementById("systems-tbody");

  // Update toggle button active states
  const btnBT = document.getElementById("sys-mode-backtest");
  const btnFW = document.getElementById("sys-mode-forward");
  if (btnBT) btnBT.classList.toggle("active", SYSTEMS_MODE === "backtest");
  if (btnFW) btnFW.classList.toggle("active", SYSTEMS_MODE === "forward");

  // Sortable headers
  const thead = document.getElementById("systems-thead");
  const arrow = (col) => SYSTEMS_SORT_COL === col ? (SYSTEMS_SORT_ASC ? " ▲" : " ▼") : "";
  const thStyle = 'style="cursor:pointer;user-select:none"';
  if (thead) {
    thead.innerHTML = SYSTEMS_MODE === "forward"
      ? `<tr><th ${thStyle} onclick="sortSystems('name')">Strategy${arrow("name")}</th><th ${thStyle} onclick="sortSystems('trades')">Trades${arrow("trades")}</th><th ${thStyle} onclick="sortSystems('wr')">FW Win Rate${arrow("wr")}</th><th ${thStyle} onclick="sortSystems('sharpe')">FW Sharpe${arrow("sharpe")}</th><th ${thStyle} onclick="sortSystems('pnl')">Realized P/L${arrow("pnl")}</th><th>Status</th></tr>`
      : `<tr><th ${thStyle} onclick="sortSystems('name')">Strategy${arrow("name")}</th><th ${thStyle} onclick="sortSystems('trades')">Trades${arrow("trades")}</th><th ${thStyle} onclick="sortSystems('wr')">Win Rate${arrow("wr")}</th><th ${thStyle} onclick="sortSystems('sharpe')">Sharpe${arrow("sharpe")}</th><th>Source</th><th>Status</th></tr>`;
  }

  // Build sortable row data — compute metrics from raw trades (pre-computed fields are often null)
  const rowData = SYSTEMS_AE.map((sys) => {
    const baby = findSurvivorBabyStrat(sys.name);
    const closedTrades = baby ? baby.forwardTrades.length : 0;
    const openTrades = baby ? baby.forwardLivePicks.length : 0;
    const fm = baby ? computeForwardMetrics(baby.forwardTrades) : { wr: null, sharpe: null, pnl: 0, wins: 0, losses: 0 };
    return { sys, baby, closedTrades, openTrades, fwPnl: fm.pnl, fwWR: fm.wr, fwSharpe: fm.sharpe, fwWins: fm.wins, fwLosses: fm.losses };
  });

  // Sort
  rowData.sort((a, b) => {
    let va, vb;
    const col = SYSTEMS_SORT_COL;
    if (SYSTEMS_MODE === "forward") {
      if (col === "name") { va = a.sys.name; vb = b.sys.name; }
      else if (col === "trades") { va = a.closedTrades + a.openTrades; vb = b.closedTrades + b.openTrades; }
      else if (col === "wr") { va = a.fwWR ?? -999; vb = b.fwWR ?? -999; }
      else if (col === "sharpe") { va = a.fwSharpe ?? -999; vb = b.fwSharpe ?? -999; }
      else if (col === "pnl") { va = a.fwPnl; vb = b.fwPnl; }
      else { va = 0; vb = 0; }
    } else {
      if (col === "name") { va = a.sys.name; vb = b.sys.name; }
      else if (col === "trades") { va = a.sys.trades; vb = b.sys.trades; }
      else if (col === "wr") { va = parseFloat(a.sys.winRate) || 0; vb = parseFloat(b.sys.winRate) || 0; }
      else if (col === "sharpe") { va = a.sys.sharpe; vb = b.sys.sharpe; }
      else { va = 0; vb = 0; }
    }
    if (typeof va === "string") return SYSTEMS_SORT_ASC ? va.localeCompare(vb) : vb.localeCompare(va);
    return SYSTEMS_SORT_ASC ? va - vb : vb - va;
  });

  tbody.innerHTML = rowData.map(({ sys, baby, closedTrades, openTrades, fwPnl, fwWR, fwSharpe, fwWins, fwLosses }) => {
    if (SYSTEMS_MODE === "forward") {
      const hasData = closedTrades > 0 || openTrades > 0;
      const clickAttr = hasData && baby ? `style="cursor:pointer" onclick="showTradeAudit('${baby.name}')" title="Click to view trades"` : "";
      const nameExtra = baby ? `<br><small style="color:#666;font-size:.55rem">via ${baby.name}</small>` : "";
      const noDataMsg = !baby ? '<span style="font-size:.55rem;color:#f59e0b" title="Strategy exists but not yet enrolled in forward testing pipeline">awaiting enrollment</span>' : '';
      const descTip = sys.desc ? ` title="${sys.desc.replace(/"/g, '&quot;')}"` : "";
      return `
<tr ${clickAttr}>
<td><div class="system-name"><span class="letter" style="background:${sys.color}">${sys.letter}</span><span${descTip} style="${sys.desc ? 'cursor:help;border-bottom:1px dotted #555' : ''}">${sys.name}</span>${nameExtra}</div></td>
<td>${closedTrades > 0 ? closedTrades : (noDataMsg || "--")}${openTrades > 0 ? ` <span style="font-size:.6rem;color:#60a5fa">(${openTrades} open)</span>` : ""}</td>
<td class="metric-value ${fwWR !== null && fwWR > 50 ? "positive" : fwWR !== null ? "negative" : ""}">${fwWR !== null ? fwWR.toFixed(1) + "%" : "--"}</td>
<td class="metric-value ${fwSharpe !== null && fwSharpe > 0 ? "positive" : fwSharpe !== null ? "negative" : ""}">${fwSharpe !== null ? fwSharpe.toFixed(2) : "--"}</td>
<td style="font-size:.75rem"><span class="metric-value ${fwPnl >= 0 ? "positive" : "negative"}">${closedTrades > 0 ? fmtPct(fwPnl, 2, true) : "--"}</span></td>
<td>${hasData ? '<span class="badge badge-paper">FORWARD</span>' : (baby ? '<span class="badge badge-validating">PENDING</span>' : '<span class="badge badge-validating">N/A</span>')}</td>
</tr>`;
    }

    // Backtest mode
    const clickAttr = baby ? `style="cursor:pointer" onclick="showTradeAudit('${baby.name}')" title="Click to view forward trades"` : "";
    const descTip = sys.desc ? ` title="${sys.desc.replace(/"/g, '&quot;')}"` : "";
    return `
<tr ${clickAttr}>
<td><div class="system-name"><span class="letter" style="background:${sys.color}">${sys.letter}</span><span${descTip} style="${sys.desc ? 'cursor:help;border-bottom:1px dotted #555' : ''}">${sys.name}</span></div></td>
<td>${sys.trades}</td>
<td class="metric-value positive">${sys.winRate}</td>
<td class="metric-value ${sys.sharpe >= 1.0 ? "positive" : ""}">${sys.sharpe.toFixed(2)}</td>
<td style="font-size:.75rem;color:#888">${sys.source || ""}</td>
<td><span class="badge ${sys.badge}">${sys.status}</span></td>
</tr>`;
  }).join("");
}

function isDataBasisMatch(s) {
  if (DATA_BASIS === "all") return true;
  return s.realDataVerified === true;
}

function isStatusMatch(s) {
  if (ACTIVE_STATUS_FILTERS.has("all")) return true;
  if (
    ACTIVE_STATUS_FILTERS.has("graduated") &&
    (s.status === "graduated" || s.status === "live")
  )
    return true;
  return ACTIVE_STATUS_FILTERS.has(s.status);
}

function filteredStrategies() {
  return BABY_STRATS.filter((s) => {
    if (!isDataBasisMatch(s) || !isStatusMatch(s)) return false;
    if (FW_FILTER === "active" && METRIC_MODE === "forward") {
      const wr = s.forward.winRate;
      if (wr === null || wr === undefined || wr <= 0) return false;
    }
    // Survivors Only filter: WR>50% AND Sharpe>0 in the active metric mode
    if (SURVIVORS_ONLY) {
      const m = METRIC_MODE === "forward" ? s.forward : s.backtest;
      const wr = m.winRate;
      const sh = m.sharpe;
      const trades = m.trades || 0;
      // Must have data + WR>50% + Sharpe>0 + at least some trades
      if (trades < 1) return false;
      if (wr === null || wr === undefined || wr <= 50) return false;
      if (sh === null || sh === undefined || sh <= 0) return false;
    }
    return true;
  });
}
function setModeButtons() {
  document
    .getElementById("mode-forward")
    .classList.toggle("active", METRIC_MODE === "forward");
  document
    .getElementById("mode-backtest")
    .classList.toggle("active", METRIC_MODE === "backtest");
  document
    .getElementById("cal-mode-forward")
    .classList.toggle("active", CALENDAR_MODE === "forward");
  document
    .getElementById("cal-mode-backtest")
    .classList.toggle("active", CALENDAR_MODE === "backtest");
  document
    .getElementById("cal-norm-avg")
    .classList.toggle("active", CALENDAR_NORM === "average");
  document
    .getElementById("cal-norm-sum")
    .classList.toggle("active", CALENDAR_NORM === "sum");
  document
    .getElementById("basis-real")
    .classList.toggle("active", DATA_BASIS === "real_only");
  document
    .getElementById("basis-all")
    .classList.toggle("active", DATA_BASIS === "all");
  document
    .getElementById("fw-filter-all")
    .classList.toggle("active", FW_FILTER === "all");
  document
    .getElementById("fw-filter-active")
    .classList.toggle("active", FW_FILTER === "active");
  const survBtn = document.getElementById("survivors-toggle");
  if (survBtn) survBtn.classList.toggle("active", SURVIVORS_ONLY);
}

function renderStatusFilters() {
  const base = BABY_STRATS.filter((s) => isDataBasisMatch(s));
  const counts = {
    all: base.length,
    backtest_passed: base.filter((s) => s.status === "backtest_passed").length,
    validating: base.filter((s) => s.status === "validating").length,
    insufficient_data: base.filter((s) => s.status === "insufficient_data")
      .length,
    failed: base.filter((s) => s.status === "failed").length,
    backtest_error: base.filter((s) => s.status === "backtest_error").length,
    paper_trading: base.filter((s) => s.status === "paper_trading").length,
    graduated: base.filter(
      (s) => s.status === "graduated" || s.status === "live",
    ).length,
  };

  // Tooltip descriptions for each status
  const statusTooltips = {
    all: "Show all strategies regardless of status",
    backtest_passed:
      "Passed Stage 1 backtest (Sharpe ≥1.0, WR ≥45%). Ready for paper trading.",
    validating: "New strategies awaiting or running initial validation",
    insufficient_data:
      "Backtest completed but too few trades for confidence (<20)",
    failed: "Failed backtest gates (Sharpe <1.0 or WR <45% or Max DD <-20%)",
    backtest_error: "Backtest failed to complete due to errors",
    paper_trading:
      "In 30-day forward paper trading (Stage 2). Live simulated trades.",
    graduated: "Completed paper test successfully. Ready for live deployment.",
  };

  document.getElementById("status-filters").innerHTML = STATUS_OPTIONS.map(
    (s) =>
      `<button class="status-chip ${ACTIVE_STATUS_FILTERS.has(s.id) ? "active" : ""}" data-status="${s.id}" data-desc="${statusTooltips[s.id] || ""}">${s.label} (${counts[s.id] || 0})</button>`,
  ).join("");
}

function renderVerificationSummary() {
  const summary = DASHBOARD_DATA?.verification_summary || {};
  document.getElementById("verification-grid").innerHTML = `
<div class="verification-pill" data-tooltip="Total number of strategies in the incubator"><span class="k">Total</span><span class="v">${BABY_STRATS.length}</span></div>
<div class="verification-pill" data-tooltip="Verified with 100% real market data from Binance/CoinGecko. No synthetic data."><span class="k">Real verified</span><span class="v metric-value positive">${summary.real_data_verified ?? 0}</span></div>
<div class="verification-pill" data-tooltip="Uses real data for primary assets + BTC-derived proxies for cross-asset indicators (SPX, DXY, VIX)"><span class="k">Mixed real+proxy</span><span class="v metric-value">${summary.mixed_real_plus_proxy ?? 0}</span></div>
<div class="verification-pill" data-tooltip="Data source not verified. May use synthetic or incomplete feeds."><span class="k">Unverified</span><span class="v metric-value ${summary.unverified > 0 ? "negative" : "positive"}">${summary.unverified ?? 0}</span></div>`;
  document.getElementById("verification-note").textContent =
    summary.note || "Real-only mode excludes mixed/proxy strategies.";
}

function sortForwardLeaders(col) {
  if (FW_SORT_COL === col) {
    FW_SORT_ASC = !FW_SORT_ASC;
  } else {
    FW_SORT_COL = col;
    FW_SORT_ASC = false;
  }
  renderForwardLeaders();
}

function renderForwardLeaders() {
  const box = document.getElementById("forward-leaders");
  const list = filteredStrategies().filter((s) => (s.forward.trades || 0) > 0);

  // Sort by selected column
  const getter = {
    name: (s) => s.name.toLowerCase(),
    trades: (s) => s.forward.trades || 0,
    wr: (s) => s.forward.winRate ?? -999,
    sharpe: (s) => s.forward.sharpe ?? -999,
  };
  const fn = getter[FW_SORT_COL] || getter.trades;
  list.sort((a, b) => {
    const va = fn(a),
      vb = fn(b);
    const cmp = typeof va === "string" ? va.localeCompare(vb) : va - vb;
    return FW_SORT_ASC ? cmp : -cmp;
  });
  const top = list.slice(0, 10);

  if (!top.length) {
    box.innerHTML =
      '<h4>Top Real Forward Picks</h4><div style="color:#8d92bf;font-size:.72rem">No strategies with closed forward trades yet.</div>';
    return;
  }

  const arrow = (col) =>
    FW_SORT_COL === col ? (FW_SORT_ASC ? " ▲" : " ▼") : "";
  box.innerHTML = `
<h4>Top Real Forward Picks</h4>
<table>
<thead><tr>
  <th class="sortable-th" onclick="sortForwardLeaders('name')">Strategy${arrow("name")}</th>
  <th class="sortable-th" onclick="sortForwardLeaders('trades')">FW Trades${arrow("trades")}</th>
  <th class="sortable-th" onclick="sortForwardLeaders('wr')">FW WR${arrow("wr")}</th>
  <th class="sortable-th" onclick="sortForwardLeaders('sharpe')">FW Sharpe${arrow("sharpe")}</th>
</tr></thead>
<tbody>
${top
  .map(
    (s) => `
<tr>
  <td>${s.name}</td>
  <td class="metric-value positive">${s.forward.trades}</td>
  <td>${fmtPct(s.forward.winRate)}</td>
  <td>${fmtNum(s.forward.sharpe)}</td>
</tr>`,
  )
  .join("")}
</tbody>
</table>`;
}

function renderBabyStrats() {
  const grid = document.getElementById("baby-strat-grid");
  const list = filteredStrategies().sort(
    (a, b) => (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99),
  );
  document.getElementById("strat-count").textContent =
    `${list.length} shown / ${BABY_STRATS.length} total` + (SURVIVORS_ONLY ? " (survivors only)" : "");

  if (!list.length) {
    grid.innerHTML =
      '<div class="no-strats">No strategies match current filters.</div>';
    return;
  }

  grid.innerHTML = list
    .map((s) => {
      const hasForwardTrades = s.forwardTrades.length > 0 || s.forwardLivePicks.length > 0;
      const badge = statusBadge(s.status, hasForwardTrades);
      const m = METRIC_MODE === "forward" ? s.forward : s.backtest;
      const forwardMissing =
        METRIC_MODE === "forward" &&
        m.trades <= 0 &&
        m.winRate === null &&
        m.sharpe === null;
      const wr = forwardMissing ? null : m.winRate;
      const sh = forwardMissing ? null : m.sharpe;
      const dd = forwardMissing ? null : m.maxDrawdown;
      const pnl =
        METRIC_MODE === "forward" && !forwardMissing ? s.forwardPnlPct : null;
      const trades = forwardMissing ? 0 : m.trades || 0;
      const dataClass = s.realDataVerified
        ? "real"
        : s.verificationLevel.includes("mixed")
          ? "mixed"
          : "unknown";
      const dataText = s.realDataVerified
        ? "REAL"
        : s.verificationLevel.includes("mixed")
          ? "MIXED"
          : "UNKNOWN";

      // Determine trade label and tooltip based on metric mode
      const tradeLabel = METRIC_MODE === "forward" ? "FW Trades" : "BT Trades";
      const tradeTooltip =
        METRIC_MODE === "forward"
          ? "Forward trades: Live paper trading since promotion"
          : "Backtest trades: Historical simulation over 180 days";

      // Multi-pair verification badge
      const multiPairClass = s.multiPairVerified
        ? "multi-pair"
        : "no-multi-pair";
      const multiPairText = s.multiPairVerified ? "MULTI" : "SINGLE";
      const multiPairTitle = s.multiPairVerified
        ? "Verified on multiple pairs (BTC, ETH, SOL)"
        : "Single pair only - not multi-pair verified";

      return `
<div class="baby-strat-card" id="strat-${s.name}">
<div class="strat-header"><span class="strat-name">${s.name.replace(/_/g, "_<wbr>")}</span><span class="badge ${badge.cls}">${badge.text}</span></div>
<div class="strat-meta"><span>by ${s.agent}</span><span class="data-badge ${dataClass}" title="${s.realDataVerified ? "Uses real market data (Binance OHLCV)" : "Uses mixed/proxy data"}">${dataText}</span><span class="data-badge ${multiPairClass}" title="${multiPairTitle}">${multiPairText}</span></div>
<div class="backtest-preview">
<div class="metric"><label>${METRIC_MODE === "forward" ? "FW WR" : "BT WR"}</label><span class="metric-value ${metricClass((wr ?? 0) - 50)}">${wr === null ? "n/a" : wr.toFixed(1) + "%"}</span></div>
<div class="metric"><label>${METRIC_MODE === "forward" ? "FW Sharpe" : "BT Sharpe"}</label><span class="metric-value ${metricClass(sh)}">${sh === null ? "n/a" : sh.toFixed(2)}</span></div>
<div class="metric"><label>${METRIC_MODE === "forward" ? "FW P/L %" : "BT Max DD"}</label><span class="metric-value ${METRIC_MODE === "forward" ? metricClass(pnl) : metricClass(dd, false)}">${METRIC_MODE === "forward" ? (pnl === null ? "n/a" : fmtPct(pnl, 2, true)) : dd === null ? "n/a" : dd.toFixed(1) + "%"}</span></div>
<div class="metric" title="${tradeTooltip}"><label>${tradeLabel}</label><span class="metric-value ${trades > 0 ? "positive" : "gray"}">${trades}</span></div>
</div>
${forwardMissing ? '<div class="trades-count" style="text-align:left;color:#9aa0d1;margin-top:8px"><strong>No forward data yet.</strong> This strategy is in backtest stage. Switch to Backtest mode to see historical results.</div>' : ""}
${s.failureReason ? `<div class="trades-count" style="text-align:left;margin-top:8px;color:#999">${s.failureReason}</div>` : ""}
${(() => {
  const hasTrades = s.forwardTrades.length > 0 || s.forwardLivePicks.length > 0 || (s.forward.trades > 0 && !forwardMissing);
  if (!hasTrades) return "";
  const realizedPnl = s.forwardTrades.reduce((a, t) => a + (Number(t.pnl_pct) || 0), 0);
  const realizedStr = s.forwardTrades.length > 0 ? fmtPct(realizedPnl, 2, true) : s.forwardPnlPct !== null ? fmtPct(s.forwardPnlPct, 2, true) : "pending";
  const realizedCls = realizedPnl >= 0 ? "positive" : "negative";

  // Last pick date — most recent from closed trades or live picks
  const dates = [];
  for (const t of s.forwardTrades) { if (t.exit_time) dates.push(t.exit_time); else if (t.entry_time) dates.push(t.entry_time); }
  for (const p of s.forwardLivePicks) { if (p.generated_at) dates.push(p.generated_at); else if (p.entry_time) dates.push(p.entry_time); }
  dates.sort((a, b) => String(b).localeCompare(String(a)));
  const lastPickDate = dates[0] ? toEST(dates[0]) : "";

  // Unrealized P/L for live picks
  let unrealizedHtml = "";
  if (s.forwardLivePicks.length > 0) {
    let totalUnrealized = 0;
    let hasPrice = false;
    for (const p of s.forwardLivePicks) {
      const sym = p.symbol || "BTCUSDT";
      const entry = parseFloat(p.entry_price) || 0;
      let cur = parseFloat(p.current_price) || 0;
      if (!cur && DASHBOARD_DATA?.prices) {
        cur = DASHBOARD_DATA.prices[sym] || DASHBOARD_DATA.prices[sym.replace("USDT", "/USDT")] || 0;
      }
      if (entry && cur) {
        const side = String(p.side || p.direction || "BUY").toUpperCase();
        const pnl = (side === "BUY" || side === "LONG") ? ((cur - entry) / entry) * 100 : ((entry - cur) / entry) * 100;
        totalUnrealized += pnl;
        hasPrice = true;
      }
    }
    const uCls = totalUnrealized >= 0 ? "positive" : "negative";
    unrealizedHtml = `<span class="unrealized-label">Open: <strong>${s.forwardLivePicks.length}</strong>${hasPrice ? ` <span class="metric-value ${uCls}">(${totalUnrealized >= 0 ? "+" : ""}${totalUnrealized.toFixed(2)}%)</span>` : ""}</span>`;
  }

  return `<div class="audit-bar"><span class="realized-label">Realized: <strong class="metric-value ${realizedCls}">${realizedStr}</strong></span>${unrealizedHtml}${lastPickDate ? `<span class="last-pick-label" style="color:#9aa0d1;font-size:.65rem" title="Most recent pick">Last: ${lastPickDate}</span>` : ""}<button class="audit-btn" onclick="event.stopPropagation();showTradeAudit('${s.name}')">Audit Trades</button></div>`;
})()}
</div>`;
    })
    .join("");
}

function renderGraduatedStrats() {
  const tbody = document.getElementById("graduated-tbody");
  const graduated = BABY_STRATS.filter((s) => isDataBasisMatch(s)).filter(
    (s) => s.status === "graduated" || s.status === "live",
  );

  // Sortable headers
  const thead = document.getElementById("graduated-thead");
  if (thead) {
    const arrow = (col) => GRADUATED_SORT_COL === col ? (GRADUATED_SORT_ASC ? " ▲" : " ▼") : "";
    const thS = 'style="cursor:pointer;user-select:none"';
    thead.innerHTML = `<tr><th ${thS} onclick="sortGraduated('name')">Strategy${arrow("name")}</th><th ${thS} onclick="sortGraduated('status')">Status${arrow("status")}</th><th ${thS} onclick="sortGraduated('wr')">Win Rate (BT → FW)${arrow("wr")}</th><th ${thS} onclick="sortGraduated('sharpe')">Sharpe (BT → FW)${arrow("sharpe")}</th><th ${thS} onclick="sortGraduated('maxdd')">Max DD (BT → FW)${arrow("maxdd")}</th><th ${thS} onclick="sortGraduated('trades')">Trades${arrow("trades")}</th><th>Data</th></tr>`;
  }

  if (!graduated.length) {
    tbody.innerHTML =
      '<tr><td colspan="7" style="text-align:center;color:#666;padding:30px">No graduated strategies in current filter.</td></tr>';
    return;
  }

  // Sort
  const sorted = [...graduated];
  sorted.sort((a, b) => {
    let va, vb;
    const col = GRADUATED_SORT_COL;
    if (col === "name") { va = a.name.toLowerCase(); vb = b.name.toLowerCase(); }
    else if (col === "status") { va = a.status; vb = b.status; }
    else if (col === "wr") { va = a.forward.winRate ?? a.backtest.winRate ?? -999; vb = b.forward.winRate ?? b.backtest.winRate ?? -999; }
    else if (col === "sharpe") { va = a.forward.sharpe ?? a.backtest.sharpe ?? -999; vb = b.forward.sharpe ?? b.backtest.sharpe ?? -999; }
    else if (col === "maxdd") { va = a.forward.maxDrawdown ?? a.backtest.maxDrawdown ?? 999; vb = b.forward.maxDrawdown ?? b.backtest.maxDrawdown ?? 999; }
    else if (col === "trades") { va = a.forward.trades || 0; vb = b.forward.trades || 0; }
    else { va = 0; vb = 0; }
    if (typeof va === "string") return GRADUATED_SORT_ASC ? va.localeCompare(vb) : vb.localeCompare(va);
    return GRADUATED_SORT_ASC ? va - vb : vb - va;
  });

  tbody.innerHTML = sorted
    .map(
      (s) => `
<tr>
<td><strong>${s.name}</strong><br><small style="color:#666">${s.agent}</small></td>
<td><span class="badge badge-graduated">${s.status === "live" ? "LIVE" : "PROVEN"}</span></td>
<td>${fmtPct(s.backtest.winRate)} → ${fmtPct(s.forward.winRate)}</td>
<td>${fmtNum(s.backtest.sharpe)} → ${fmtNum(s.forward.sharpe)}</td>
<td>${fmtPct(s.backtest.maxDrawdown)} → ${fmtPct(s.forward.maxDrawdown)}</td>
<td>${s.forward.trades || 0}</td>
<td><span class="data-badge ${s.realDataVerified ? "real" : "mixed"}">${s.realDataVerified ? "REAL" : "MIXED"}</span></td>
</tr>`,
    )
    .join("");
}

function dirText(m) {
  if (!m || !m.trades) return "0 / n-a / n-a";
  return `${m.trades} / ${fmtPct(m.winRate)} / ${fmtNum(m.sharpe)}`;
}

function renderDirectionalTable() {
  const tbody = document.getElementById("directional-tbody");
  const rows = filteredStrategies().filter(
    (s) => s.directional.overall.trades > 0,
  );
  if (!rows.length) {
    tbody.innerHTML =
      '<tr><td colspan="6" style="text-align:center;color:#666;padding:24px">No directional metrics for current filter.</td></tr>';
    return;
  }

  // Sortable headers
  const thead = document.getElementById("directional-thead");
  if (thead) {
    const arrow = (col) => DIRECTIONAL_SORT_COL === col ? (DIRECTIONAL_SORT_ASC ? " ▲" : " ▼") : "";
    const thS = 'style="cursor:pointer;user-select:none"';
    thead.innerHTML = `<tr><th ${thS} onclick="sortDirectional('name')">Strategy${arrow("name")}</th><th ${thS} onclick="sortDirectional('status')">Status${arrow("status")}</th><th ${thS} onclick="sortDirectional('overall')">Overall (T/WR/S)${arrow("overall")}</th><th ${thS} onclick="sortDirectional('long')">Long (T/WR/S)${arrow("long")}</th><th ${thS} onclick="sortDirectional('short')">Short (T/WR/S)${arrow("short")}</th><th>Data/Stage</th></tr>`;
  }

  // Sort rows
  const sorted = [...rows];
  sorted.sort((a, b) => {
    let va, vb;
    const col = DIRECTIONAL_SORT_COL;
    if (col === "name") { va = a.name; vb = b.name; }
    else if (col === "status") { va = a.status; vb = b.status; }
    else if (col === "overall") { va = a.directional.overall.winRate || 0; vb = b.directional.overall.winRate || 0; }
    else if (col === "long") { va = a.directional.long?.winRate || 0; vb = b.directional.long?.winRate || 0; }
    else if (col === "short") { va = a.directional.short?.winRate || 0; vb = b.directional.short?.winRate || 0; }
    else { va = 0; vb = 0; }
    if (typeof va === "string") return DIRECTIONAL_SORT_ASC ? va.localeCompare(vb) : vb.localeCompare(va);
    return DIRECTIONAL_SORT_ASC ? va - vb : vb - va;
  });

  tbody.innerHTML = sorted
    .map((s) => {
      const badge = statusBadge(s.status, s.forwardTrades.length > 0);
      const stage = "BT";
      const dataLabel = s.realDataVerified ? `REAL-${stage}` : `MIXED-${stage}`;
      const dataTitle = s.realDataVerified
        ? "REAL-BT: real market data, backtest directional metrics (not forward)."
        : "MIXED-BT: mixed/proxy data, backtest directional metrics (not forward).";
      return `
<tr>
<td><strong>${s.name}</strong><br><small style="color:#666">${s.agent}</small></td>
<td><span class="badge ${badge.cls}">${badge.text}</span></td>
<td>${dirText(s.directional.overall)}</td>
<td>${dirText(s.directional.long)}</td>
<td>${dirText(s.directional.short)}</td>
<td><span class="data-badge ${s.realDataVerified ? "real" : "mixed"}" title="${dataTitle}">${dataLabel}</span></td>
</tr>`;
    })
    .join("");
}
function parseDateParts(dateText) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateText);
  if (!m) return null;
  return { y: Number(m[1]), m: Number(m[2]), d: Number(m[3]) };
}

function monthLabel(y, m) {
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

const EXIT_REASON_TOOLTIPS = {
  TP: "Take Profit — Price hit the TP target, trade closed in profit.",
  SL: "Stop Loss — Price hit the SL level, trade closed to limit losses.",
  TIME: "Time Stop — Trade held for the maximum allowed period (12 bars / 12 hours on 1h timeframe) without hitting TP or SL. The position was automatically closed at the current market price.",
};

function exitReasonBadge(reason) {
  const r = reason || "?";
  const tooltip = EXIT_REASON_TOOLTIPS[r] || "Unknown exit reason.";
  const badgeCls = r === "TP" ? "badge-passed" : r === "SL" ? "badge-failed" : "badge-validating";
  return `<span class="badge ${badgeCls}" style="font-size:.65rem;cursor:help" title="${tooltip}">${r} <span style="font-size:.5rem;opacity:.7">ℹ</span></span>`;
}

function renderCalendarStrategyOptions() {
  const select = document.getElementById("calendar-strategy-filter");
  const opts = ['<option value="all">All strategies</option>'];
  for (const s of filteredStrategies()) {
    opts.push(
      `<option value="${s.name}" ${CALENDAR_STRATEGY === s.name ? "selected" : ""}>${s.name}</option>`,
    );
  }
  select.innerHTML = opts.join("");
}

function aggregateCalendarDays() {
  const source = filteredStrategies().filter((s) =>
    CALENDAR_STRATEGY === "all" ? true : s.name === CALENDAR_STRATEGY,
  );
  const byDay = {};
  for (const s of source) {
    const rows = CALENDAR_MODE === "forward" ? s.dailyForward : s.dailyBacktest;
    for (const d of rows) {
      if (!byDay[d.date])
        byDay[d.date] = {
          date: d.date,
          pnlPct: 0,
          trades: 0,
          wins: 0,
          losses: 0,
          _stratCount: 0,
        };
      byDay[d.date].pnlPct += Number(d.pnlPct || 0);
      byDay[d.date].trades += Number(d.trades || 0);
      byDay[d.date].wins += Number(d.wins || 0);
      byDay[d.date].losses += Number(d.losses || 0);
      byDay[d.date]._stratCount += 1;
    }
  }
  // Normalize to per-strategy average when in average mode
  const useAvg = CALENDAR_NORM === "average" && CALENDAR_STRATEGY === "all";
  if (useAvg) {
    for (const day of Object.values(byDay)) {
      if (day._stratCount > 1) {
        day.pnlPct = day.pnlPct / day._stratCount;
      }
    }
  }
  return Object.values(byDay).sort((a, b) => a.date.localeCompare(b.date));
}

function renderCalendar() {
  renderCalendarStrategyOptions();
  const days = aggregateCalendarDays();
  const summaryEl = document.getElementById("calendar-summary");
  const wrap = document.getElementById("calendar-wrap");

  if (!days.length) {
    summaryEl.textContent =
      CALENDAR_MODE === "forward"
        ? "No forward daily P&L records yet for current filters."
        : "No backtest daily P&L records for current filters.";
    wrap.innerHTML =
      '<div class="no-strats">Calendar data unavailable for current filter.</div>';
    return;
  }

  const totalPnl = days.reduce((a, b) => a + Number(b.pnlPct || 0), 0);
  const totalTrades = days.reduce((a, b) => a + Number(b.trades || 0), 0);
  const totalWins = days.reduce((a, b) => a + Number(b.wins || 0), 0);
  const totalLosses = days.reduce((a, b) => a + Number(b.losses || 0), 0);
  const wr =
    totalWins + totalLosses > 0
      ? (100 * totalWins) / (totalWins + totalLosses)
      : null;

  const normLabel = CALENDAR_STRATEGY === "all" ? (CALENDAR_NORM === "average" ? " (Avg/Strategy)" : " (Sum All)") : "";
  summaryEl.innerHTML = `Mode: <strong>${CALENDAR_MODE === "forward" ? "Forward" : "Backtest"}</strong>${normLabel} | Days: <strong>${days.length}</strong> | Trades: <strong>${totalTrades}</strong> | Win rate: <strong>${wr === null ? "n/a" : wr.toFixed(1) + "%"}</strong> | P&amp;L: <strong class="metric-value ${totalPnl >= 0 ? "positive" : "negative"}">${fmtPct(totalPnl, 2, true)}</strong>`;

  let minY = 9999,
    minM = 12,
    maxY = 0,
    maxM = 1;
  const dayMap = {};
  for (const d of days) {
    dayMap[d.date] = d;
    const p = parseDateParts(d.date);
    if (!p) continue;
    if (p.y < minY || (p.y === minY && p.m < minM)) {
      minY = p.y;
      minM = p.m;
    }
    if (p.y > maxY || (p.y === maxY && p.m > maxM)) {
      maxY = p.y;
      maxM = p.m;
    }
  }

  const weekday = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
  const monthHtml = [];
  let y = minY;
  let m = minM;
  while (y < maxY || (y === maxY && m <= maxM)) {
    const first = new Date(Date.UTC(y, m - 1, 1));
    const firstW = first.getUTCDay();
    const dim = new Date(Date.UTC(y, m, 0)).getUTCDate();

    const cells = [];
    for (let i = 0; i < firstW; i += 1)
      cells.push('<div class="day-cell blank"></div>');

    for (let d = 1; d <= dim; d += 1) {
      const key = `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      const row = dayMap[key];
      if (!row) {
        cells.push(
          `<div class="day-cell"><div class="day-num">${d}</div><div class="day-pnl">--</div></div>`,
        );
        continue;
      }

      const pnl = Number(row.pnlPct || 0);
      const cls = pnl > 0.001 ? "positive" : pnl < -0.001 ? "negative" : "flat";
      cells.push(
        `<div class="day-cell ${cls}" style="cursor:pointer" onclick="showCalendarDayBreakdown('${key}')" title="Click for strategy breakdown"><div class="day-num">${d}</div><div class="day-pnl">${fmtPct(pnl, 2, true)}</div><div class="day-trades">${row.trades || 0} trades</div></div>`,
      );
    }

    monthHtml.push(
      `<div class="month-card"><div class="month-title">${monthLabel(y, m)}</div><div class="weekday-row">${weekday.map((w) => `<div class="weekday">${w}</div>`).join("")}</div><div class="day-grid">${cells.join("")}</div></div>`,
    );

    m += 1;
    if (m > 12) {
      m = 1;
      y += 1;
    }
  }

  wrap.innerHTML = monthHtml.join("");
}

function renderStatusDefinitions() {
  const defs = DASHBOARD_DATA?.status_definitions || {};
  const metricDefs = DASHBOARD_DATA?.metric_mode_definitions || {};

  // Comprehensive glossary with detailed explanations
  const glossary = {
    status: {
      title: "📊 Strategy Status Stages",
      items: [
        {
          key: "backtest_passed",
          label: "PASSED",
          color: "#22c55e",
          desc: "Strategy passed Stage 1 historical backtest with Sharpe ≥1.0, Win Rate ≥45%, Max DD ≥-20%. Ready for forward paper testing.",
        },
        {
          key: "validating",
          label: "VALIDATING",
          color: "#8b5cf6",
          desc: "Strategy is new or being re-evaluated. Awaiting or running initial validation checks.",
        },
        {
          key: "paper_trading",
          label: "PAPER",
          color: "#eab308",
          desc: "Strategy is in Stage 2: 30-day forward paper trading. Real-time simulated trades with live market data. Tracks daily PnL to verify edge holds out-of-sample.",
        },
        {
          key: "graduated",
          label: "GRADUATED",
          color: "#3b82f6",
          desc: "Strategy completed 30-day paper test meeting criteria (Sharpe ≥1.0, WR ≥45%). Promoted to Stage 3 for potential live deployment.",
        },
        {
          key: "live",
          label: "LIVE",
          color: "#ec4899",
          desc: "Strategy is actively running in live production with real capital allocation.",
        },
        {
          key: "insufficient_data",
          label: "INSUFFICIENT",
          color: "#f97316",
          desc: "Backtest completed but produced too few trades (<20) for statistical confidence. Needs more data or parameter adjustment.",
        },
        {
          key: "backtest_failed",
          label: "FAILED",
          color: "#ef4444",
          desc: "Backtest completed but failed quality gates (Sharpe <1.0 or WR <45% or Max DD <-20%).",
        },
        {
          key: "backtest_error",
          label: "ERROR",
          color: "#ef4444",
          desc: "Backtest could not complete due to timeout, import error, or runtime exception.",
        },
      ],
    },
    dataVerification: {
      title: "🔍 Data Verification Badges",
      items: [
        {
          key: "real",
          label: "REAL",
          color: "#22c55e",
          desc: "Verified with 100% real market data from Binance/CoinGecko. No synthetic or proxy data used.",
        },
        {
          key: "mixed",
          label: "MIXED",
          color: "#eab308",
          desc: "Uses real data for primary assets (BTC, ETH) plus BTC-derived proxies for cross-asset indicators (SPX, DXY, VIX). Acceptable for strategies where correlation is sufficient.",
        },
        {
          key: "unverified",
          label: "UNVERIFIED",
          color: "#64748b",
          desc: "Data source not verified. May use synthetic data or incomplete feeds.",
        },
      ],
    },
    metrics: {
      title: "📈 Metric Modes",
      items: [
        {
          key: "forward",
          label: "FORWARD",
          color: "#a855f7",
          desc: "Forward-looking paper/live metrics. Shows actual out-of-sample performance since strategy started paper trading. Most reliable indicator of real-world edge.",
        },
        {
          key: "backtest",
          label: "BACKTEST",
          color: "#3b82f6",
          desc: "Historical backtest metrics from 180-day real-data sweep. In-sample performance on past data. Good for initial screening but can overfit.",
        },
      ],
    },
    qualityGates: {
      title: "🎯 Quality Gates (Promotion Criteria)",
      items: [
        {
          key: "sharpe",
          label: "Sharpe ≥1.0",
          color: "#22c55e",
          desc: "Sharpe ratio measures risk-adjusted returns. ≥1.0 means excess returns compensate for volatility taken. Higher = better risk management.",
        },
        {
          key: "winrate",
          label: "Win Rate ≥45%",
          color: "#22c55e",
          desc: "Percentage of winning trades. ≥45% with proper R:R (risk:reward) can be profitable. Higher win rates reduce psychological stress.",
        },
        {
          key: "maxdd",
          label: "Max DD ≥-20%",
          color: "#22c55e",
          desc: "Maximum drawdown from peak equity. ≥-20% means strategy doesn't lose more than 20% at worst. Lower drawdown = better capital preservation.",
        },
      ],
    },
  };

  let html = [];

  // Status stages
  html.push(`<div class="glossary-section"><h4>${glossary.status.title}</h4>`);
  for (const item of glossary.status.items) {
    html.push(
      `<div class="status-item"><div class="key"><span class="badge" style="background:${item.color}22;color:${item.color};border:1px solid ${item.color}44;padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600">${item.label}</span></div><div class="desc">${item.desc}</div></div>`,
    );
  }
  html.push(`</div>`);

  // Data verification
  html.push(
    `<div class="glossary-section"><h4>${glossary.dataVerification.title}</h4>`,
  );
  for (const item of glossary.dataVerification.items) {
    html.push(
      `<div class="status-item"><div class="key"><span class="badge" style="background:${item.color}22;color:${item.color};border:1px solid ${item.color}44;padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600">${item.label}</span></div><div class="desc">${item.desc}</div></div>`,
    );
  }
  html.push(`</div>`);

  // Metric modes
  html.push(`<div class="glossary-section"><h4>${glossary.metrics.title}</h4>`);
  for (const item of glossary.metrics.items) {
    html.push(
      `<div class="status-item"><div class="key"><span class="badge" style="background:${item.color}22;color:${item.color};border:1px solid ${item.color}44;padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600">${item.label}</span></div><div class="desc">${item.desc}</div></div>`,
    );
  }
  html.push(`</div>`);

  // Quality gates
  html.push(
    `<div class="glossary-section"><h4>${glossary.qualityGates.title}</h4>`,
  );
  for (const item of glossary.qualityGates.items) {
    html.push(
      `<div class="status-item"><div class="key"><span class="badge" style="background:${item.color}22;color:${item.color};border:1px solid ${item.color}44;padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600">${item.label}</span></div><div class="desc">${item.desc}</div></div>`,
    );
  }
  html.push(`</div>`);

  // Original definitions from JSON as fallback
  const ordered = [
    "backtest_passed",
    "validating",
    "insufficient_data",
    "backtest_failed",
    "backtest_error",
    "paper_trading",
    "graduated",
    "live",
  ];
  for (const key of ordered) {
    if (!defs[key]) continue;
  }

  document.getElementById("status-definitions").innerHTML = html.join("");
}

function renderGraduationCriteria() {
  const criteria = {
    stage1: {
      title: "Stage 1: Backtest Validation",
      stage: "Entry Gate",
      description:
        "Strategy must pass historical backtest on real market data before advancing to paper trading.",
      items: [
        {
          label: "Sharpe Ratio ≥ 1.0",
          required: true,
          tooltip: "Risk-adjusted returns. Higher is better.",
        },
        {
          label: "Win Rate ≥ 45%",
          required: true,
          tooltip: "Percentage of winning trades.",
        },
        {
          label: "Max Drawdown ≥ -20%",
          required: true,
          tooltip: "Maximum peak-to-trough decline. Less negative is better.",
        },
        {
          label: "Minimum 20 trades",
          required: true,
          tooltip: "Statistical significance threshold.",
        },
        {
          label: "180-day test period",
          required: true,
          tooltip: "Full historical sweep duration.",
        },
      ],
    },
    stage2: {
      title: "Stage 2: Forward Paper Trading",
      stage: "Validation Phase",
      description:
        "30-day out-of-sample testing with live market data but simulated execution.",
      items: [
        {
          label: "30 calendar days minimum",
          required: true,
          tooltip: "Must complete full 30-day period.",
        },
        {
          label: "Sharpe Ratio ≥ 1.0",
          required: true,
          tooltip: "Forward performance must match backtest quality.",
        },
        {
          label: "Win Rate ≥ 45%",
          required: true,
          tooltip: "Real-time edge must persist.",
        },
        {
          label: "Max Drawdown ≥ -20%",
          required: true,
          tooltip: "Risk control maintained in live conditions.",
        },
        {
          label: "At least 5 trades",
          required: false,
          tooltip: "Minimum activity level (flexible based on market).",
        },
      ],
    },
    stage3: {
      title: "Stage 3: Graduation to Live",
      stage: "Graduation",
      description:
        "Strategy receives 'Graduated' status and becomes eligible for live capital allocation.",
      items: [
        {
          label: "All Stage 2 gates passed",
          required: true,
          tooltip: "Must meet all forward test criteria.",
        },
        {
          label: "Consistent performance",
          required: true,
          tooltip: "No severe degradation vs backtest.",
        },
        {
          label: "Stable equity curve",
          required: true,
          tooltip: "Reasonable drawdown recovery pattern.",
        },
        {
          label: "Ready for live allocation",
          required: true,
          tooltip: "Approved for real capital deployment.",
        },
        {
          label: "Continuous monitoring",
          required: false,
          tooltip: "Ongoing surveillance in live mode.",
        },
      ],
    },
  };

  let html = [];

  // Gate explanation banner
  html.push(
    `<div class="gate-explanation"><h5>🎯 Three-Stage Promotion System</h5><p>Strategies progress through rigorous validation: <strong>Backtest → Paper Trading → Live</strong>. Each stage has specific quality gates that must be met before promotion. This ensures only robust, edge-proven strategies reach live capital.</p></div>`,
  );

  // Stage cards
  html.push(`<div class="graduation-criteria">`);

  for (const [key, stage] of Object.entries(criteria)) {
    const stageNum = key.replace("stage", "");
    const isActive = stageNum === "2" ? "active" : "";

    html.push(`<div class="criteria-card ${key}">`);
    html.push(
      `<h4><span class="stage-label ${isActive}">${stage.stage}</span> ${stage.title}</h4>`,
    );
    html.push(
      `<p style="color:#888;font-size:.8rem;margin-bottom:12px">${stage.description}</p>`,
    );
    html.push(`<ul class="criteria-list">`);

    for (const item of stage.items) {
      const badgeClass = item.required ? "required" : "optional";
      const badgeText = item.required ? "✓" : "○";
      html.push(
        `<li><span class="check ${badgeClass}" title="${item.tooltip}">${badgeText}</span> <span title="${item.tooltip}">${item.label}</span></li>`,
      );
    }

    html.push(`</ul>`);
    html.push(`</div>`);
  }

  html.push(`</div>`);

  // Current stats — count strategies that meet backtest quality gates
  // All strats were auto-promoted to paper_trading, so check actual backtest metrics
  const passedCount = BABY_STRATS.filter((s) => {
    if (s.status === "backtest_passed") return true;
    const bt = s.backtest;
    return bt && bt.sharpe !== null && bt.sharpe >= 1.0
      && bt.winRate !== null && bt.winRate >= 45
      && bt.trades >= 20;
  }).length;
  const paperCount = BABY_STRATS.filter(
    (s) => s.status === "paper_trading",
  ).length;
  const graduatedCount = BABY_STRATS.filter(
    (s) => s.status === "graduated" || s.status === "live",
  ).length;

  html.push(
    `<div class="criteria-note" style="margin-top:20px;display:grid;grid-template-columns:repeat(3,1fr);gap:12px;text-align:center">`,
  );
  html.push(
    `<div style="padding:12px;background:#3b82f622;border:1px solid #3b82f644;border-radius:6px"><div style="font-size:1.5rem;font-weight:700;color:#3b82f6">${passedCount}</div><div style="font-size:.75rem;color:#888">Passed Backtest<br><span style="color:#3b82f6">Ready for Paper</span></div></div>`,
  );
  html.push(
    `<div style="padding:12px;background:#eab30822;border:1px solid #eab30844;border-radius:6px"><div style="font-size:1.5rem;font-weight:700;color:#eab308">${paperCount}</div><div style="font-size:.75rem;color:#888">In Paper Trading<br><span style="color:#eab308">30-Day Test</span></div></div>`,
  );
  html.push(
    `<div style="padding:12px;background:#22c55e22;border:1px solid #22c55e44;border-radius:6px"><div style="font-size:1.5rem;font-weight:700;color:#22c55e">${graduatedCount}</div><div style="font-size:.75rem;color:#888">Graduated/Live<br><span style="color:#22c55e">Production Ready</span></div></div>`,
  );
  html.push(`</div>`);

  document.getElementById("graduation-criteria").innerHTML = html.join("");
}

function toEST(isoStr) {
  if (!isoStr) return "n/a";
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return (
      d.toLocaleString("en-US", {
        timeZone: "America/New_York",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      }) + " EST"
    );
  } catch {
    return isoStr;
  }
}

function fmtPrice(v) {
  if (v === null || v === undefined) return "n/a";
  const n = Number(v);
  if (!Number.isFinite(n)) return "n/a";
  return n >= 1000
    ? n.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    : n.toFixed(4);
}

function showTradeAudit(stratName) {
  const s = BABY_STRATS.find((x) => x.name === stratName);
  if (!s) return;

  const modal = document.getElementById("trade-audit-modal");
  const trades = s.forwardTrades || [];
  const livePicks = s.forwardLivePicks || [];

  // Compute realized P/L (from closed trades)
  const tPnls = trades.map(t => Number(t.pnl_pct) || 0);
  const realizedPnl = tPnls.reduce((a, v) => a + v, 0);
  const wins = tPnls.filter(p => p > 0).length;
  const losses = trades.length - wins;
  const tAvg = tPnls.length > 0 ? realizedPnl / tPnls.length : 0;
  const tMin = tPnls.length > 0 ? Math.min(...tPnls) : 0;
  const tMax = tPnls.length > 0 ? Math.max(...tPnls) : 0;
  const tWinPnls = tPnls.filter(p => p > 0);
  const tLossPnls = tPnls.filter(p => p <= 0);
  const tAvgWin = tWinPnls.length > 0 ? tWinPnls.reduce((a,v)=>a+v,0) / tWinPnls.length : 0;
  const tAvgLoss = tLossPnls.length > 0 ? tLossPnls.reduce((a,v)=>a+v,0) / tLossPnls.length : 0;
  const tExitReasons = {};
  for (const t of trades) { const r = t.exit_reason || "?"; tExitReasons[r] = (tExitReasons[r] || 0) + 1; }

  let html = `<div class="audit-overlay" onclick="closeTradeAudit(event)">
<div class="audit-content" onclick="event.stopPropagation()">
<div class="audit-header">
  <h3>${stratName.replace(/_/g, " ")}</h3>
  <button class="audit-close" onclick="closeTradeAudit()">&times;</button>
</div>

<div class="audit-summary">
  <div class="audit-stat"><label>Realized P/L</label><span class="metric-value ${realizedPnl >= 0 ? "positive" : "negative"}">${fmtPct(realizedPnl, 2, true)}</span></div>
  <div class="audit-stat"><label>Closed <span class="badge badge-passed" style="font-size:.55rem;vertical-align:middle">${trades.length}</span></label><span><span style="color:#22c55e">${wins} Wins</span> / <span style="color:#ef4444">${losses} Losses</span></span></div>
  <div class="audit-stat"><label>Open <span class="badge badge-paper" style="font-size:.55rem;vertical-align:middle">${livePicks.length}</span></label><span class="metric-value">${livePicks.length > 0 ? "Active" : "None"}</span></div>
  <div class="audit-stat"><label>Total Trades</label><span class="metric-value">${trades.length + livePicks.length}</span></div>
</div>
${trades.length > 0 ? `<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:8px 0;padding:8px;background:#0f0f1a;border-radius:6px;font-size:.7rem">
  <div><label style="color:#888;display:block">Avg P/L</label><span class="metric-value ${tAvg >= 0 ? "positive" : "negative"}">${fmtPct(tAvg, 3, true)}</span></div>
  <div><label style="color:#888;display:block">Min P/L</label><span class="metric-value negative">${fmtPct(tMin, 3, true)}</span></div>
  <div><label style="color:#888;display:block">Max P/L</label><span class="metric-value positive">${fmtPct(tMax, 3, true)}</span></div>
  <div><label style="color:#888;display:block">WR</label><span class="metric-value ${wins > losses ? "positive" : "negative"}">${(100 * wins / trades.length).toFixed(1)}%</span></div>
  <div><label style="color:#888;display:block">Avg Win</label><span class="metric-value positive">${fmtPct(tAvgWin, 3, true)}</span></div>
  <div><label style="color:#888;display:block">Avg Loss</label><span class="metric-value negative">${fmtPct(tAvgLoss, 3, true)}</span></div>
  <div><label style="color:#888;display:block">Profit Factor</label><span class="metric-value">${tLossPnls.length > 0 && tAvgLoss !== 0 ? Math.abs(tWinPnls.reduce((a,v)=>a+v,0) / tLossPnls.reduce((a,v)=>a+v,0)).toFixed(2) : "n/a"}</span></div>
  <div><label style="color:#888;display:block">Exit Reasons</label><span style="color:#ccc;font-size:.6rem">${Object.entries(tExitReasons).map(([k,v]) => k + ":" + v).join(" ")}</span></div>
</div>` : ""}`;


  // Live picks (unrealized)
  if (livePicks.length) {
    html += `<h4 class="audit-section-title">Open Positions (Unrealized)</h4>
<table class="audit-table">
<thead><tr><th>Side</th><th>Symbol</th><th>Entry</th><th>TP</th><th>SL</th><th>Opened</th></tr></thead>
<tbody>`;
    for (const p of livePicks) {
      const side = String(p.side || "").toUpperCase();
      const sideClass = side === "BUY" ? "positive" : "negative";
      html += `<tr>
<td class="metric-value ${sideClass}">${side}</td>
<td>${p.symbol || "BTCUSDT"}</td>
<td>${fmtPrice(p.entry_price)}</td>
<td>${fmtPrice(p.take_profit)}</td>
<td>${fmtPrice(p.stop_loss)}</td>
<td>${toEST(p.generated_at)}</td>
</tr>`;
    }
    html += `</tbody></table>`;
  }

  // Closed trades (realized)
  if (trades.length) {
    html += `<h4 class="audit-section-title">Closed Trades (Realized)</h4>
<table class="audit-table">
<thead><tr><th>Symbol</th><th>Dir</th><th>Entry $</th><th>Exit $</th><th>P/L %</th><th>Reason</th><th>Entry Time</th><th>Exit Time</th><th>Bars</th></tr></thead>
<tbody>`;
    const sorted = [...trades].sort((a, b) =>
      String(b.exit_time || "").localeCompare(String(a.exit_time || "")),
    );
    for (const t of sorted) {
      const pnl = Number(t.pnl_pct) || 0;
      const dir = String(t.direction || "").toUpperCase();
      const dirClass =
        dir.includes("LONG") || dir.includes("BUY") ? "positive" : "negative";
      html += `<tr>
<td style="font-weight:600">${t.symbol || t.pair || "BTCUSDT"}</td>
<td class="metric-value ${dirClass}">${dir.includes("LONG") || dir.includes("BUY") ? "LONG" : "SHORT"}</td>
<td>${fmtPrice(t.entry_price)}</td>
<td>${fmtPrice(t.exit_price)}</td>
<td class="metric-value ${pnl >= 0 ? "positive" : "negative"}">${fmtPct(pnl, 2, true)}</td>
<td>${exitReasonBadge(t.exit_reason)}</td>
<td>${toEST(t.entry_time)}</td>
<td>${toEST(t.exit_time)}</td>
<td>${t.bars_held ?? "?"}</td>
</tr>`;
    }
    html += `</tbody></table>`;
  }

  if (!trades.length && !livePicks.length && s.forward.trades > 0) {
    html += `<h4 class="audit-section-title">Forward Summary (individual trade records pending)</h4>
<table class="audit-table">
<thead><tr><th>Metric</th><th>Value</th></tr></thead>
<tbody>
<tr><td>Total Trades</td><td>${s.forward.trades}</td></tr>
<tr><td>Win Rate</td><td>${fmtPct(s.forward.winRate)}</td></tr>
<tr><td>Sharpe</td><td>${fmtNum(s.forward.sharpe)}</td></tr>
<tr><td>Max Drawdown</td><td>${fmtPct(s.forward.maxDrawdown)}</td></tr>
<tr><td>P/L %</td><td class="metric-value ${(s.forwardPnlPct || 0) >= 0 ? "positive" : "negative"}">${s.forwardPnlPct !== null ? fmtPct(s.forwardPnlPct, 2, true) : "n/a"}</td></tr>
</tbody></table>
<div style="color:#666;text-align:center;padding:10px;font-size:.7rem">Individual trade records (entry/exit times, TP/SL) will populate on next forward evaluation run.</div>`;
  } else if (!trades.length && !livePicks.length) {
    html += `<div style="color:#666;text-align:center;padding:30px">No trade data available yet.</div>`;
  }

  html += `</div></div>`;
  modal.innerHTML = html;
  modal.style.display = "block";
}

function closeTradeAudit(ev) {
  if (ev && ev.target !== ev.currentTarget) return;
  const modal = document.getElementById("trade-audit-modal");
  modal.style.display = "none";
  modal.innerHTML = "";
}

function showCalendarDayBreakdown(dateStr) {
  const source = CALENDAR_STRATEGY === "all"
    ? filteredStrategies()
    : filteredStrategies().filter(s => s.name === CALENDAR_STRATEGY);
  const rows = [];
  for (const s of source) {
    const dayRows = CALENDAR_MODE === "forward" ? s.dailyForward : s.dailyBacktest;
    const match = dayRows.find(d => d.date === dateStr);
    if (match && (Number(match.trades) || 0) > 0) {
      rows.push({
        name: s.name,
        pnl: Number(match.pnlPct || 0),
        trades: Number(match.trades || 0),
        wins: Number(match.wins || 0),
        losses: Number(match.losses || 0),
      });
    }
  }
  if (!rows.length) return;
  rows.sort((a, b) => b.pnl - a.pnl);
  const totalPnl = rows.reduce((a, r) => a + r.pnl, 0);
  const avgPnl = rows.length > 0 ? totalPnl / rows.length : 0;
  const displayPnl = (CALENDAR_NORM === "average" && CALENDAR_STRATEGY === "all") ? avgPnl : totalPnl;
  const totalTrades = rows.reduce((a, r) => a + r.trades, 0);
  const totalWins = rows.reduce((a, r) => a + r.wins, 0);
  const totalLosses = rows.reduce((a, r) => a + r.losses, 0);
  const wr = totalWins + totalLosses > 0 ? (100 * totalWins / (totalWins + totalLosses)).toFixed(1) + "%" : "n/a";
  const pnlModeNote = (CALENDAR_NORM === "average" && CALENDAR_STRATEGY === "all") ? " (avg/strategy)" : " (sum all)";

  const modal = document.getElementById("trade-audit-modal");
  let html = `<div class="audit-overlay" onclick="closeTradeAudit(event)">
<div class="audit-content" onclick="event.stopPropagation()">
<div class="audit-header">
  <h3>Daily Breakdown: ${dateStr}</h3>
  <button class="audit-close" onclick="closeTradeAudit()">&times;</button>
</div>
<div class="audit-summary">
  <div class="audit-stat"><label>P/L${pnlModeNote}</label><span class="metric-value ${displayPnl >= 0 ? "positive" : "negative"}">${fmtPct(displayPnl, 2, true)}</span></div>
  <div class="audit-stat"><label>Trades</label><span>${totalTrades}</span></div>
  <div class="audit-stat"><label>Win Rate</label><span>${wr}</span></div>
  <div class="audit-stat"><label>Strategies</label><span>${rows.length}</span></div>
</div>
<h4 class="audit-section-title">Per-Strategy Breakdown</h4>
<table class="audit-table">
<thead><tr><th>Strategy</th><th>Trades</th><th>W/L</th><th>Win Rate</th><th>P/L</th></tr></thead>
<tbody>`;
  for (const r of rows) {
    const sWr = r.wins + r.losses > 0 ? (100 * r.wins / (r.wins + r.losses)).toFixed(0) + "%" : "--";
    const clickAttr = `style="cursor:pointer" onclick="closeTradeAudit();showTradeAudit('${r.name}')" title="View all trades for ${r.name}"`;
    html += `<tr ${clickAttr}>
<td style="font-size:.7rem">${r.name.replace(/_/g, " ")}</td>
<td>${r.trades}</td>
<td><span style="color:#22c55e">${r.wins}W</span>/<span style="color:#ef4444">${r.losses}L</span></td>
<td>${sWr}</td>
<td class="metric-value ${r.pnl >= 0 ? "positive" : "negative"}">${fmtPct(r.pnl, 2, true)}</td>
</tr>`;
  }
  html += `</tbody></table>
<div style="color:#555;font-size:.6rem;text-align:center;padding:8px">Click any strategy row to see full trade history</div>
</div></div>`;
  modal.innerHTML = html;
  modal.style.display = "block";
}

let EXPANDED_BUNDLES = new Set();

function scrollToStrategy(stratName) {
  const el = document.getElementById("strat-" + stratName);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.style.outline = "2px solid #60a5fa";
    el.style.outlineOffset = "2px";
    setTimeout(() => { el.style.outline = ""; el.style.outlineOffset = ""; }, 3000);
  }
}

function toggleBundleExpand(bundleId) {
  if (EXPANDED_BUNDLES.has(bundleId)) {
    EXPANDED_BUNDLES.delete(bundleId);
  } else {
    EXPANDED_BUNDLES.add(bundleId);
  }
  renderBundles();
}

function showBundleAudit(bundleId) {
  const sections = DASHBOARD_DATA?.sections || [];
  const bundleSection = sections.find((s) => s.section === "BUNDLE_BABIES_TOP");
  if (!bundleSection) return;
  const bundle = bundleSection.bundles.find((b) => b.bundle_id === bundleId);
  if (!bundle) return;

  const modal = document.getElementById("trade-audit-modal");
  const stratNames = bundle.strategies || [];
  const forward = bundle.forward || {};

  // Gather trades from all strategies in this bundle
  let allTrades = [];
  let allPicks = [];
  const perStrat = [];
  for (const sn of stratNames) {
    const s = BABY_STRATS.find((x) => x.name === sn);
    if (!s) { perStrat.push({ name: sn, trades: 0, picks: 0, wr: null, pnl: 0 }); continue; }
    const trades = s.forwardTrades || [];
    const picks = s.forwardLivePicks || [];
    const wins = trades.filter((t) => (Number(t.pnl_pct) || 0) > 0).length;
    const pnl = trades.reduce((a, t) => a + (Number(t.pnl_pct) || 0), 0);
    perStrat.push({ name: sn, trades: trades.length, picks: picks.length, wr: trades.length > 0 ? ((wins / trades.length) * 100) : null, pnl });
    allTrades = allTrades.concat(trades.map((t) => ({ ...t, _strategy: sn })));
    allPicks = allPicks.concat(picks.map((p) => ({ ...p, _strategy: sn })));
  }

  const tradePnls = allTrades.map(t => Number(t.pnl_pct) || 0);
  const totalPnl = tradePnls.reduce((a, v) => a + v, 0);
  const totalWins = tradePnls.filter(p => p > 0).length;
  const totalLosses = allTrades.length - totalWins;
  const avgPnl = tradePnls.length > 0 ? totalPnl / tradePnls.length : 0;
  const minPnl = tradePnls.length > 0 ? Math.min(...tradePnls) : 0;
  const maxPnl = tradePnls.length > 0 ? Math.max(...tradePnls) : 0;
  const winPnls = tradePnls.filter(p => p > 0);
  const lossPnls = tradePnls.filter(p => p <= 0);
  const avgWin = winPnls.length > 0 ? winPnls.reduce((a, v) => a + v, 0) / winPnls.length : 0;
  const avgLoss = lossPnls.length > 0 ? lossPnls.reduce((a, v) => a + v, 0) / lossPnls.length : 0;
  // Exit reason counts
  const exitReasons = {};
  for (const t of allTrades) { const r = t.exit_reason || "?"; exitReasons[r] = (exitReasons[r] || 0) + 1; }

  let html = `<div class="audit-overlay" onclick="closeTradeAudit(event)">
<div class="audit-content" onclick="event.stopPropagation()" style="max-width:900px">
<div class="audit-header">
  <h3>${(bundle.name || "Bundle").replace(/_/g, " ")}</h3>
  <button class="audit-close" onclick="closeTradeAudit()">&times;</button>
</div>

<div class="audit-summary">
  <div class="audit-stat"><label>Realized P/L</label><span class="metric-value ${totalPnl >= 0 ? "positive" : "negative"}">${fmtPct(totalPnl, 2, true)}</span></div>
  <div class="audit-stat"><label>Closed</label><span class="metric-value">${allTrades.length}</span></div>
  <div class="audit-stat"><label>Wins / Losses</label><span><span style="color:#22c55e">${totalWins} Wins</span> / <span style="color:#ef4444">${totalLosses} Losses</span></span></div>
  <div class="audit-stat"><label>Open</label><span class="metric-value">${allPicks.length}</span></div>
</div>
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:8px 0;padding:8px;background:#0f0f1a;border-radius:6px;font-size:.7rem">
  <div><label style="color:#888;display:block">Avg P/L</label><span class="metric-value ${avgPnl >= 0 ? "positive" : "negative"}">${fmtPct(avgPnl, 3, true)}</span></div>
  <div><label style="color:#888;display:block">Min P/L</label><span class="metric-value negative">${fmtPct(minPnl, 3, true)}</span></div>
  <div><label style="color:#888;display:block">Max P/L</label><span class="metric-value positive">${fmtPct(maxPnl, 3, true)}</span></div>
  <div><label style="color:#888;display:block">WR</label><span class="metric-value ${totalWins > totalLosses ? "positive" : "negative"}">${allTrades.length > 0 ? (100 * totalWins / allTrades.length).toFixed(1) + "%" : "n/a"}</span></div>
  <div><label style="color:#888;display:block">Avg Win</label><span class="metric-value positive">${fmtPct(avgWin, 3, true)}</span></div>
  <div><label style="color:#888;display:block">Avg Loss</label><span class="metric-value negative">${fmtPct(avgLoss, 3, true)}</span></div>
  <div><label style="color:#888;display:block">Profit Factor</label><span class="metric-value">${lossPnls.length > 0 && avgLoss !== 0 ? Math.abs(winPnls.reduce((a,v)=>a+v,0) / lossPnls.reduce((a,v)=>a+v,0)).toFixed(2) : "n/a"}</span></div>
  <div><label style="color:#888;display:block">Exit Reasons</label><span style="color:#ccc">${Object.entries(exitReasons).map(([k,v]) => k + ":" + v).join(" ")}</span></div>
</div>

<h4 class="audit-section-title">Strategies in Bundle (${stratNames.length})</h4>
<table class="audit-table">
<thead><tr><th>Strategy</th><th>Closed</th><th>Open</th><th>WR</th><th>Realized P/L</th><th></th></tr></thead>
<tbody>`;
  for (const ps of perStrat) {
    html += `<tr>
<td style="cursor:pointer;color:#60a5fa" onclick="closeTradeAudit();setTimeout(()=>showTradeAudit('${ps.name}'),100)">${ps.name.replace(/_/g, " ")}</td>
<td>${ps.trades}</td>
<td>${ps.picks}</td>
<td>${ps.wr !== null ? ps.wr.toFixed(1) + "%" : "n/a"}</td>
<td class="metric-value ${ps.pnl >= 0 ? "positive" : "negative"}">${fmtPct(ps.pnl, 2, true)}</td>
<td><button class="audit-btn" style="font-size:.6rem;padding:2px 6px" onclick="closeTradeAudit();setTimeout(()=>showTradeAudit('${ps.name}'),100)">View</button></td>
</tr>`;
  }
  html += `</tbody></table>`;

  // Combined open positions
  if (allPicks.length) {
    html += `<h4 class="audit-section-title">Open Positions (${allPicks.length})</h4>
<table class="audit-table">
<thead><tr><th>Strategy</th><th>Side</th><th>Symbol</th><th>Entry</th><th>TP</th><th>SL</th><th>Opened</th></tr></thead>
<tbody>`;
    for (const p of allPicks) {
      const side = String(p.side || "").toUpperCase();
      const sideClass = side === "BUY" ? "positive" : "negative";
      html += `<tr>
<td style="font-size:.65rem">${(p._strategy || "").replace(/_/g, " ")}</td>
<td class="metric-value ${sideClass}">${side}</td>
<td>${p.symbol || "BTCUSDT"}</td>
<td>${fmtPrice(p.entry_price)}</td>
<td>${fmtPrice(p.take_profit)}</td>
<td>${fmtPrice(p.stop_loss)}</td>
<td>${toEST(p.generated_at)}</td>
</tr>`;
    }
    html += `</tbody></table>`;
  }

  // Combined closed trades
  if (allTrades.length) {
    html += `<h4 class="audit-section-title">Closed Trades (${allTrades.length})</h4>
<table class="audit-table">
<thead><tr><th>Strategy</th><th>Symbol</th><th>Dir</th><th>Entry $</th><th>Exit $</th><th>P/L %</th><th>Reason</th><th>Entry Time</th><th>Exit Time</th><th>Bars</th></tr></thead>
<tbody>`;
    const sorted = [...allTrades].sort((a, b) => String(b.exit_time || "").localeCompare(String(a.exit_time || "")));
    for (const t of sorted) {
      const pnl = Number(t.pnl_pct) || 0;
      const dir = String(t.direction || "").toUpperCase();
      const dirClass = dir.includes("LONG") || dir.includes("BUY") ? "positive" : "negative";
      html += `<tr>
<td style="font-size:.65rem">${(t._strategy || "").replace(/_/g, " ")}</td>
<td style="font-weight:600">${t.symbol || t.pair || "BTCUSDT"}</td>
<td class="metric-value ${dirClass}">${dir.includes("LONG") || dir.includes("BUY") ? "LONG" : "SHORT"}</td>
<td>${fmtPrice(t.entry_price)}</td>
<td>${fmtPrice(t.exit_price)}</td>
<td class="metric-value ${pnl >= 0 ? "positive" : "negative"}">${fmtPct(pnl, 2, true)}</td>
<td>${exitReasonBadge(t.exit_reason)}</td>
<td>${toEST(t.entry_time)}</td>
<td>${toEST(t.exit_time)}</td>
<td>${t.bars_held ?? "?"}</td>
</tr>`;
    }
    html += `</tbody></table>`;
  }

  if (!allTrades.length && !allPicks.length) {
    html += `<div style="color:#666;text-align:center;padding:30px">No trade data available yet for strategies in this bundle.</div>`;
  }

  html += `</div></div>`;
  modal.innerHTML = html;
  modal.style.display = "block";
}

function renderBundles() {
  const container = document.getElementById("bundles-grid");
  if (!container) return;

  // Update toggle button active states
  const btnBT = document.getElementById("bundle-mode-backtest");
  const btnFW = document.getElementById("bundle-mode-forward");
  if (btnBT) btnBT.classList.toggle("active", BUNDLE_MODE === "backtest");
  if (btnFW) btnFW.classList.toggle("active", BUNDLE_MODE === "forward");

  const sections = DASHBOARD_DATA?.sections || [];
  const bundleSection = sections.find((s) => s.section === "BUNDLE_BABIES_TOP");

  if (
    !bundleSection ||
    !bundleSection.bundles ||
    bundleSection.bundles.length === 0
  ) {
    container.innerHTML =
      '<div class="no-strats">No bundles available yet.</div>';
    return;
  }

  const bundles = bundleSection.bundles;
  const isLive = BUNDLE_MODE === "forward";

  // Tiered ranking: WR >= 50% always above WR < 50%, then composite within tier
  const bundlesRanked = bundles.map((b) => {
    const strategies = b.strategies || [];
    let wins = 0, losses = 0, totalPnl = 0;
    for (const sn of strategies) {
      const s = BABY_STRATS.find((x) => x.name === sn) || BABY_STRATS.find((x) => x.name.includes(sn) || sn.includes(x.name));
      if (!s) continue;
      for (const t of (s.forwardTrades || [])) {
        const p = Number(t.pnl_pct) || 0;
        totalPnl += p;
        if (p > 0) wins++; else losses++;
      }
    }
    const total = wins + losses;
    const wr = total > 0 ? (wins / total) : 0;
    const wrPct = wr * 100;
    // Confidence: log scale so 20 trades >> 3 trades, but 200 vs 100 is modest
    const confidence = total > 0 ? Math.min(Math.log2(total + 1) / Math.log2(50), 1) : 0;
    // PnL factor: positive PnL gets a boost, negative gets penalized
    const pnlFactor = total > 0 ? Math.sign(totalPnl) * Math.min(Math.abs(totalPnl) / 20, 0.3) : 0;
    // Composite within tier
    const composite = total > 0 ? (wr * confidence) + pnlFactor : -999;
    // Tier: 2 = winning (WR>=50%), 1 = losing (WR<50% but has trades), 0 = no trades
    const tier = total === 0 ? 0 : (wrPct >= 50 ? 2 : 1);
    return { bundle: b, _score: composite, _tier: tier, _wr: wrPct, _trades: total, _pnl: totalPnl };
  });
  // Sort: tier descending first, then composite descending within tier
  bundlesRanked.sort((a, b) => a._tier !== b._tier ? b._tier - a._tier : b._score - a._score);

  // Filter out low WR bundles if toggle is on
  const showLowWR = !HIDE_LOW_WR_BUNDLES;
  const bundlesToShow = bundlesRanked.filter(({ _tier }) => showLowWR || _tier !== 1);
  const hiddenCount = bundlesRanked.length - bundlesToShow.length;

  // Toggle button + hidden count banner
  const toggleBtnHtml = hiddenCount > 0
    ? `<div style="text-align:center;margin-bottom:12px;padding:8px;background:#1a1a2e;border-radius:8px;border:1px solid #333">
<span style="color:#888;font-size:.75rem">${hiddenCount} bundle${hiddenCount > 1 ? 's' : ''} with &lt;50% win rate hidden</span>
<button onclick="HIDE_LOW_WR_BUNDLES=false;renderBundles()" style="margin-left:12px;padding:4px 14px;font-size:.7rem;background:#2a2a4a;color:#60a5fa;border:1px solid #444;border-radius:4px;cursor:pointer">Show All</button>
</div>`
    : (!showLowWR ? '' : `<div style="text-align:center;margin-bottom:12px;padding:8px;background:#1a1a2e;border-radius:8px;border:1px solid #333">
<span style="color:#888;font-size:.75rem">Showing all bundles</span>
<button onclick="HIDE_LOW_WR_BUNDLES=true;renderBundles()" style="margin-left:12px;padding:4px 14px;font-size:.7rem;background:#2a2a4a;color:#f59e0b;border:1px solid #444;border-radius:4px;cursor:pointer">Hide &lt;50% WR</button>
</div>`);

  container.innerHTML = toggleBtnHtml + bundlesToShow
    .map(({ bundle: b }) => {
      const classification = b.classification || {};
      const backtest = b.backtest || {};
      const forward = b.forward || {};
      const strategies = b.strategies || [];
      const isExpanded = EXPANDED_BUNDLES.has(b.bundle_id);

      // Compute aggregate forward stats from individual strategies
      let totalClosed = 0, totalOpen = 0, totalWins = 0, totalLosses = 0, totalPnl = 0;
      let matchedStrats = 0;
      for (const sn of strategies) {
        // Try exact match first, then partial match
        let s = BABY_STRATS.find((x) => x.name === sn);
        if (!s) s = BABY_STRATS.find((x) => x.name.includes(sn) || sn.includes(x.name));
        if (!s) continue;
        matchedStrats++;
        const closed = s.forwardTrades.length;
        totalClosed += closed;
        totalOpen += s.forwardLivePicks.length;
        for (const t of s.forwardTrades) {
          const p = Number(t.pnl_pct) || 0;
          totalPnl += p;
          if (p > 0) totalWins++; else totalLosses++;
        }
      }
      const fwWR = (totalWins + totalLosses) > 0 ? (100 * totalWins / (totalWins + totalLosses)) : null;

      const fwStatus = forward.status || "paper";
      const hasLiveData = totalClosed > 0 || totalOpen > 0;
      const fwLabel = hasLiveData ? "LIVE FORWARD" : fwStatus === "paper" ? "PAPER (Forward)" : fwStatus.toUpperCase();

      // Gather per-strategy stats for expanded view
      let stratListHtml = "";
      if (isExpanded && strategies.length > 0) {
        stratListHtml = `<div class="bundle-strat-list" style="margin-top:8px;border-top:1px solid #333;padding-top:8px">
<div style="font-size:.7rem;color:#9aa0d1;margin-bottom:4px;font-weight:600">Strategies (${strategies.length}):</div>`;
        const allBundleTrades = [];
        for (const sn of strategies) {
          let s = BABY_STRATS.find((x) => x.name === sn);
          if (!s) s = BABY_STRATS.find((x) => x.name.includes(sn) || sn.includes(x.name));
          const realName = s ? s.name : sn;
          const closedCount = s ? s.forwardTrades.length : 0;
          const openCount = s ? s.forwardLivePicks.length : 0;
          const pnl = s ? s.forwardTrades.reduce((a, t) => a + (Number(t.pnl_pct) || 0), 0) : 0;
          const notFound = !s ? ' <span style="color:#f59e0b;font-size:.55rem">(not in pipeline)</span>' : '';
          if (s) for (const t of s.forwardTrades) allBundleTrades.push({ ...t, _strat: sn });
          stratListHtml += `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:.68rem;border-bottom:1px solid #1a1a2e">
<span style="color:#60a5fa;cursor:pointer;flex:1" onclick="event.stopPropagation();showTradeAudit('${realName}')">${sn.replace(/_/g, " ")}${notFound}</span>
<span style="color:#888;margin:0 6px">${closedCount} closed${openCount > 0 ? `, ${openCount} open` : ""}</span>
<span class="metric-value ${pnl >= 0 ? "positive" : "negative"}" style="font-size:.65rem">${closedCount > 0 ? fmtPct(pnl, 2, true) : "n/a"}</span>
<button class="audit-btn" style="font-size:.55rem;padding:1px 5px;margin-left:4px" onclick="event.stopPropagation();scrollToStrategy('${realName}')" title="Jump to strategy card">Jump</button>
</div>`;
        }
        // Recent trades table (last 10)
        if (allBundleTrades.length > 0) {
          const recent = [...allBundleTrades].sort((a, b) => String(b.exit_time || "").localeCompare(String(a.exit_time || ""))).slice(0, 10);
          stratListHtml += `<div style="margin-top:10px;border-top:1px solid #333;padding-top:8px">
<div style="font-size:.7rem;color:#9aa0d1;margin-bottom:4px;font-weight:600">Recent Trades (${allBundleTrades.length} total — showing last ${recent.length}):</div>
<table style="width:100%;font-size:.62rem;border-collapse:collapse">
<thead><tr style="color:#888;text-align:left"><th style="padding:2px 4px">Strategy</th><th style="padding:2px 4px">Dir</th><th style="padding:2px 4px">P/L</th><th style="padding:2px 4px">Exit</th><th style="padding:2px 4px">Time</th></tr></thead>
<tbody>`;
          for (const t of recent) {
            const p = Number(t.pnl_pct) || 0;
            const dir = String(t.direction || "").toUpperCase();
            const isLong = dir.includes("LONG") || dir.includes("BUY");
            stratListHtml += `<tr style="border-bottom:1px solid #1a1a2e" onclick="event.stopPropagation()">
<td style="padding:2px 4px;color:#60a5fa">${(t._strat || "").replace(/crypto_soc_/g, "").replace(/_v1/g, "").replace(/_/g, " ")}</td>
<td style="padding:2px 4px" class="metric-value ${isLong ? "positive" : "negative"}">${isLong ? "L" : "S"}</td>
<td style="padding:2px 4px" class="metric-value ${p >= 0 ? "positive" : "negative"}">${fmtPct(p, 2, true)}</td>
<td style="padding:2px 4px">${exitReasonBadge(t.exit_reason)}</td>
<td style="padding:2px 4px;color:#888">${toEST(t.exit_time)}</td>
</tr>`;
          }
          stratListHtml += `</tbody></table></div>`;
        }
        stratListHtml += `</div>`;
      }

      // Metrics row changes based on mode
      let metricsHtml;
      if (isLive) {
        const noMatch = matchedStrats === 0;
        metricsHtml = noMatch
          ? `<div style="font-size:.65rem;color:#f59e0b;padding:4px 0">Strategies not yet enrolled in forward testing pipeline (${strategies.length} strategies). Backtest data available.</div>`
          : `
        <div class="metric"><label>Trades</label><value>${totalClosed}${totalOpen > 0 ? ` <span style="font-size:.55rem;color:#60a5fa">(${totalOpen} open)</span>` : ""}</value></div>
        <div class="metric"><label>Win Rate</label><value class="metric-value ${fwWR !== null && fwWR > 50 ? "positive" : fwWR !== null ? "negative" : ""}">${fwWR !== null ? fwWR.toFixed(1) + "%" : "--"}</value></div>
        <div class="metric"><label>Realized PnL</label><value class="metric-value ${totalPnl >= 0 ? "positive" : "negative"}">${totalClosed > 0 ? fmtPct(totalPnl, 2, true) : "--"}</value></div>
        <div class="metric"><label>Wins / Losses</label><value><span style="color:#22c55e">${totalWins}W</span> / <span style="color:#ef4444">${totalLosses}L</span></value></div>`;
      } else {
        metricsHtml = `
        <div class="metric"><label>Sharpe</label><value>${(backtest.sharpe || 0).toFixed(2)}</value></div>
        <div class="metric"><label>Win Rate</label><value>${(backtest.win_rate || 0).toFixed(1)}%</value></div>
        <div class="metric"><label>Max DD</label><value>${(backtest.max_dd || 0).toFixed(1)}%</value></div>
        <div class="metric"><label>Trades</label><value>${backtest.trades || forward.trades || 0}</value></div>`;
      }

      // Confidence badge from rebuild_bundles.py
      const conf = b.confidence || (totalClosed > 0 ? "forward-confirmed" : "backtest-projected");
      const confColors = {"forward-confirmed": "#22c55e", "mixed": "#f59e0b", "backtest-projected": "#60a5fa"};
      const confLabels = {"forward-confirmed": "Forward Confirmed", "mixed": "Mixed (Fwd+BT)", "backtest-projected": "Backtest Projected"};
      const confBadge = `<span style="font-size:.55rem;padding:1px 6px;border-radius:3px;background:${confColors[conf]}22;color:${confColors[conf]};border:1px solid ${confColors[conf]}44;margin-left:6px">${confLabels[conf]}</span>`;
      const tbk = b.trade_breakdown || {};
      const breakdownTip = tbk.forward_trades != null ? `Forward: ${tbk.forward_trades} trades${tbk.forward_wr ? ` (${tbk.forward_wr}% WR)` : ""} | Backtest: ${tbk.backtest_trades || 0} trades${tbk.backtest_wr ? ` (${tbk.backtest_wr}% WR)` : ""}` : "";

      return `
    <div class="baby-strat-card status-${fwStatus}" style="cursor:pointer" onclick="toggleBundleExpand('${b.bundle_id}')">
      <div class="strat-header">
        <div class="strat-name">${b.name || "Unnamed Bundle"}${confBadge}</div>
        <span class="badge badge-${hasLiveData ? "paper" : fwStatus === "graduated" ? "graduated" : "paper"}">${fwLabel}</span>
      </div>
      <div class="strat-meta">
        <span>${classification.symbol_scope || "N/A"} | ${classification.timeframe_scope || "N/A"} | ${classification.direction_bias || "N/A"}</span>
        <span>${strategies.length} strategies</span>
      </div>
      ${breakdownTip ? `<div style="font-size:.58rem;color:#888;padding:2px 8px;margin-top:-4px" title="${breakdownTip}">${breakdownTip}</div>` : ""}
      <div class="backtest-preview">${metricsHtml}</div>
      <div class="audit-bar">
        <span class="realized-label">${isLive ? "Mode: LIVE" : "Mode: Backtest"}</span>
        ${isLive && totalClosed > 0 ? `<span class="metric-value ${totalPnl >= 0 ? "positive" : "negative"}" style="margin-left:8px">${fmtPct(totalPnl, 2, true)} realized</span>` : ""}
        ${isLive && (forward.unrealized_pnl || 0) !== 0 ? `<span class="unrealized-label" style="margin-left:8px">Unrealized: <strong class="metric-value">${(forward.unrealized_pnl || 0).toFixed(2)}%</strong></span>` : ""}
        <button class="audit-btn" onclick="event.stopPropagation();showBundleAudit('${b.bundle_id}')" style="margin-left:auto">Audit Bundle</button>
      </div>
      ${stratListHtml}
      <div style="text-align:center;font-size:.6rem;color:#666;margin-top:4px">${isExpanded ? "▲ Click to collapse" : "▼ Click to expand strategies"}</div>
    </div>
    `;
    })
    .join("");
}

async function loadStrategyManifest() {
  const urls = [
    "./data/all_strategy_files.json?t=" + Date.now(),
    "https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/battleground/data/all_strategy_files.json",
  ];
  for (const url of urls) {
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) continue;
      const d = await r.json();
      if (Array.isArray(d?.strategies)) { ALL_STRATEGY_FILES = d.strategies; return; }
    } catch (e) { console.log("Manifest load failed:", url); }
  }
}

function renderUnregisteredStrategies() {
  const container = document.getElementById("unregistered-strategies");
  if (!container) return;

  if (!ALL_STRATEGY_FILES.length) {
    container.innerHTML = '<p style="color:#666;text-align:center">Loading strategy manifest...</p>';
    return;
  }

  // Get names of all tracked strategies
  const tracked = new Set(BABY_STRATS.map(s => s.name));

  // Find unregistered
  const unregistered = ALL_STRATEGY_FILES.filter(f => !tracked.has(f.name));

  if (unregistered.length === 0) {
    container.innerHTML = '<p style="color:#22c55e;text-align:center">All strategies are registered and tracked!</p>';
    return;
  }

  // Classify unregistered strategies with actionable flags
  const awaitingBacktest = [];
  const bundleCandidates = [];
  const rest = [];

  for (const s of unregistered) {
    // Check if any tracked strategy with same name passed backtest with good metrics
    const matchedTracked = BABY_STRATS.find(b => b.name === s.name);
    if (matchedTracked && matchedTracked.status === 'backtest_passed' &&
        (matchedTracked.win_rate || 0) > 50 && (matchedTracked.sharpe || 0) > 0.5) {
      bundleCandidates.push(s);
    } else {
      awaitingBacktest.push(s);
    }
  }

  let html = `<div style="margin-bottom:12px;color:#f59e0b;font-size:.85rem">
    <strong>${unregistered.length}</strong> strategies exist in the codebase but are NOT tracked in the battleground.
  </div>`;

  // Summary badges
  html += `<div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap">
    <span style="background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b44;padding:4px 12px;border-radius:12px;font-size:.75rem;font-weight:600">
      AWAITING BACKTEST: ${awaitingBacktest.length}
    </span>
    <span style="background:#8b5cf622;color:#8b5cf6;border:1px solid #8b5cf644;padding:4px 12px;border-radius:12px;font-size:.75rem;font-weight:600">
      BUNDLE CANDIDATES: ${bundleCandidates.length}
    </span>
  </div>`;

  // Group by source
  const groups = {};
  for (const s of unregistered) {
    const src = s.source || "unknown";
    if (!groups[src]) groups[src] = [];
    groups[src].push(s);
  }

  html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px">';

  for (const [source, strats] of Object.entries(groups).sort((a,b) => b[1].length - a[1].length)) {
    html += `<div style="background:#1a1a2e;border:1px solid #333;border-radius:8px;padding:12px">
      <div style="font-weight:600;color:#60a5fa;margin-bottom:8px">${source} <span style="color:#666">(${strats.length})</span></div>
      <div style="font-size:.75rem;color:#999;max-height:200px;overflow-y:auto">`;
    for (const s of strats.sort((a,b) => a.name.localeCompare(b.name))) {
      const isBundleCandidate = bundleCandidates.includes(s);
      const flagColor = isBundleCandidate ? '#8b5cf6' : '#f59e0b';
      const flagLabel = isBundleCandidate ? 'BUNDLE' : 'BACKTEST';
      html += `<div style="padding:3px 0;border-bottom:1px solid #222;display:flex;justify-content:space-between;align-items:center">
        <span>${s.name}</span>
        <span style="font-size:.6rem;padding:1px 6px;border-radius:4px;background:${flagColor}22;color:${flagColor};border:1px solid ${flagColor}44;white-space:nowrap">${flagLabel}</span>
      </div>`;
    }
    html += '</div></div>';
  }

  html += '</div>';

  // Action guidance
  html += `<div style="margin-top:12px;padding:10px 14px;background:#1a1a2e;border:1px solid #333;border-radius:8px;font-size:.75rem;color:#888">
    <strong style="color:#fff">Next steps:</strong><br>
    <span style="color:#f59e0b">AWAITING BACKTEST</span> — Run through <code>real_data_sweep_runner.py</code> to get performance data<br>
    <span style="color:#8b5cf6">BUNDLE CANDIDATE</span> — Passed backtest gates, eligible for promotion into a production bundle via <code>register_bundle.py</code>
  </div>`;

  container.innerHTML = html;
}

function renderActiveTrades() {
  const tbody = document.getElementById("active-trades-tbody");
  const countEl = document.getElementById("active-trades-count");
  const filterEl = document.getElementById("active-strategy-filter");
  if (!tbody) return;

  // Collect all open picks from all strategies, with bundle context
  const allOpen = [];
  const sections = DASHBOARD_DATA?.sections || [];
  const bundleSection = sections.find(s => s.section === "BUNDLE_BABIES_TOP");
  const bundleMap = {};
  if (bundleSection?.bundles) {
    for (const b of bundleSection.bundles) {
      for (const stName of (b.strategies || []).map(st => st.name || st)) {
        bundleMap[stName] = b.name || b.bundle_id || "—";
      }
    }
  }

  for (const s of BABY_STRATS) {
    for (const pick of (s.forwardLivePicks || [])) {
      const sym = pick.symbol || pick.pair || "?";
      let rawDir = (pick.direction || pick.signal_type || pick.side || "?").toUpperCase();
      // Normalize BUY/SELL → LONG/SHORT for display
      if (rawDir === "BUY") rawDir = "LONG";
      if (rawDir === "SELL") rawDir = "SHORT";
      const dir = rawDir;
      const entry = pick.entry_price || pick.entryPrice || pick.entry || 0;
      const tp = pick.take_profit || pick.targetPrice || pick.tp || 0;
      const sl = pick.stop_loss || pick.stopPrice || pick.sl || 0;
      const entryDate = pick.entry_date || pick.entryDate || pick.timestamp || pick.issued_at || pick.generated_at || "";
      // Calculate current price from DASHBOARD_DATA prices if available
      let currentPrice = pick.current_price || 0;
      if (!currentPrice && sym && DASHBOARD_DATA?.prices) {
        currentPrice = DASHBOARD_DATA.prices[sym] || DASHBOARD_DATA.prices[sym.replace("USDT", "/USDT")] || 0;
      }
      // Attach strategy-level backtest/forward stats for fallback display
      const bt = s.backtest || {};
      const fw = s.forward || {};
      allOpen.push({
        strategy: s.name, bundle: bundleMap[s.name] || "—", symbol: sym, dir, entry, tp, sl, entryDate, currentPrice,
        btWR: bt.winRate, btSharpe: bt.sharpe, btTrades: bt.trades, btPnl: s.forwardPnlPct,
        fwWR: fw.winRate, fwSharpe: fw.sharpe, fwTrades: fw.trades,
        fwClosedTrades: s.forwardTrades || [],
      });
    }
  }

  if (countEl) countEl.textContent = `(${allOpen.length} open positions)`;

  // Strategy filter chips
  const strategies = [...new Set(allOpen.map(p => p.strategy))].sort();
  if (filterEl && strategies.length > 1) {
    filterEl.innerHTML = `<button class="mode-btn active" onclick="filterActiveTrades('ALL')">All</button>` +
      strategies.map(s => `<button class="mode-btn" onclick="filterActiveTrades('${s}')">${s.slice(0, 25)}</button>`).join("");
  }

  window._allOpenTrades = allOpen;
  renderActiveTradesTable(allOpen);
}

function filterActiveTrades(strat) {
  const btns = document.querySelectorAll("#active-strategy-filter .mode-btn");
  btns.forEach(b => b.classList.toggle("active", b.textContent === strat || (strat === "ALL" && b.textContent === "All")));
  const filtered = strat === "ALL" ? window._allOpenTrades : window._allOpenTrades.filter(p => p.strategy === strat);
  renderActiveTradesTable(filtered);
}

function renderActiveTradesTable(trades) {
  const tbody = document.getElementById("active-trades-tbody");

  // Sortable headers
  const thead = document.getElementById("active-trades-thead");
  if (thead) {
    const arrow = (col) => ACTIVE_TRADES_SORT_COL === col ? (ACTIVE_TRADES_SORT_ASC ? " ▲" : " ▼") : "";
    const thS = 'style="cursor:pointer;user-select:none"';
    thead.innerHTML = `<tr><th ${thS} onclick="sortActiveTrades('strategy')">Strategy${arrow("strategy")}</th><th ${thS} onclick="sortActiveTrades('bundle')">Bundle${arrow("bundle")}</th><th ${thS} onclick="sortActiveTrades('symbol')">Symbol${arrow("symbol")}</th><th ${thS} onclick="sortActiveTrades('dir')">Dir${arrow("dir")}</th><th ${thS} onclick="sortActiveTrades('entry')">Entry${arrow("entry")}</th><th>TP</th><th>SL</th><th ${thS} onclick="sortActiveTrades('pnl')">PnL %${arrow("pnl")}</th><th>Price Position</th><th ${thS} onclick="sortActiveTrades('date')">Opened (EST)${arrow("date")}</th></tr>`;
  }

  if (!trades.length) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:#666;padding:20px">No active trades</td></tr>';
    return;
  }

  // Sort trades
  const sorted = [...trades];
  sorted.sort((a, b) => {
    let va, vb;
    const col = ACTIVE_TRADES_SORT_COL;
    if (col === "strategy") { va = a.strategy.toLowerCase(); vb = b.strategy.toLowerCase(); }
    else if (col === "bundle") { va = a.bundle.toLowerCase(); vb = b.bundle.toLowerCase(); }
    else if (col === "symbol") { va = a.symbol; vb = b.symbol; }
    else if (col === "dir") { va = a.dir; vb = b.dir; }
    else if (col === "entry") { va = Number(a.entry) || 0; vb = Number(b.entry) || 0; }
    else if (col === "pnl") {
      const pnlA = a.entry && a.currentPrice ? (a.dir === "LONG" ? (a.currentPrice - a.entry) / a.entry : (a.entry - a.currentPrice) / a.entry) * 100 : -9999;
      const pnlB = b.entry && b.currentPrice ? (b.dir === "LONG" ? (b.currentPrice - b.entry) / b.entry : (b.entry - b.currentPrice) / b.entry) * 100 : -9999;
      va = pnlA; vb = pnlB;
    }
    else if (col === "date") { va = String(a.entryDate || ""); vb = String(b.entryDate || ""); }
    else { va = 0; vb = 0; }
    if (typeof va === "string") return ACTIVE_TRADES_SORT_ASC ? va.localeCompare(vb) : vb.localeCompare(va);
    return ACTIVE_TRADES_SORT_ASC ? va - vb : vb - va;
  });

  tbody.innerHTML = sorted.map(p => {
    const dirBadge = p.dir === "LONG" ? "badge-passed" : "badge-failed";
    let dateStr = "--";
    if (p.entryDate) {
      try {
        const d = new Date(p.entryDate);
        if (!isNaN(d)) dateStr = d.toLocaleString("en-US", { timeZone: "America/New_York", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", hour12: true });
      } catch {}
    }
    const fmtP = v => v ? (v < 1 ? Number(v).toFixed(6) : Number(v).toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2})) : "--";

    // PnL % calculation — live price first, then backtest/forward fallback
    let pnlStr = "--";
    let pnlColor = "#888";
    let pnlSource = "";
    let hasLivePrice = !!(p.entry && p.currentPrice);
    if (hasLivePrice) {
      const pnl = p.dir === "LONG"
        ? ((p.currentPrice - p.entry) / p.entry) * 100
        : ((p.entry - p.currentPrice) / p.entry) * 100;
      pnlStr = (pnl >= 0 ? "+" : "") + pnl.toFixed(2) + "%";
      pnlColor = pnl >= 0 ? "#22c55e" : "#ef4444";
      pnlSource = "live";
    } else {
      // Fallback: show forward WR or backtest WR
      const wr = p.fwWR ?? p.btWR;
      const sharpe = p.fwSharpe ?? p.btSharpe;
      const trades = p.fwTrades ?? p.btTrades ?? 0;
      const src = p.fwWR != null ? "fwd" : (p.btWR != null ? "bt" : "");
      if (wr != null) {
        pnlStr = `${Number(wr).toFixed(0)}% WR`;
        pnlColor = wr >= 55 ? "#22c55e" : wr >= 45 ? "#f59e0b" : "#ef4444";
        pnlSource = src;
      }
    }

    // Price position gauge — live price first, then backtest WR bar fallback
    let gaugeHtml = "--";
    if (hasLivePrice && p.entry && p.tp && p.sl) {
      const range = Math.abs(p.tp - p.sl);
      if (range > 0) {
        const isLong = p.dir === "LONG";
        const slSide = isLong ? p.sl : p.tp;
        const tpSide = isLong ? p.tp : p.sl;
        const pos = ((p.currentPrice - slSide) / (tpSide - slSide)) * 100;
        const clamped = Math.max(0, Math.min(100, pos));
        const entryPos = ((p.entry - slSide) / (tpSide - slSide)) * 100;
        const entryClamped = Math.max(0, Math.min(100, entryPos));
        const barColor = pos >= entryPos ? "#22c55e" : "#ef4444";
        gaugeHtml = `<div style="position:relative;width:100px;height:16px;background:linear-gradient(90deg,#ef4444 0%,#f59e0b 50%,#22c55e 100%);border-radius:4px;overflow:hidden" title="SL ← Price → TP: ${clamped.toFixed(0)}%">
          <div style="position:absolute;left:${entryClamped}%;top:0;width:2px;height:100%;background:#fff;opacity:.5" title="Entry"></div>
          <div style="position:absolute;left:${clamped}%;top:1px;width:8px;height:14px;margin-left:-4px;background:${barColor};border:1px solid #fff;border-radius:3px" title="Current: ${clamped.toFixed(0)}%"></div>
        </div>`;
      }
    } else {
      // Fallback: show backtest/forward stats as mini bar
      const wr = p.fwWR ?? p.btWR;
      const sharpe = p.fwSharpe ?? p.btSharpe;
      const trades = p.fwTrades ?? p.btTrades ?? 0;
      const src = p.fwWR != null ? "fwd" : (p.btWR != null ? "bt" : "");
      if (wr != null && trades > 0) {
        const wrClamped = Math.max(0, Math.min(100, Number(wr)));
        const wrColor = wrClamped >= 55 ? "#22c55e" : wrClamped >= 45 ? "#f59e0b" : "#ef4444";
        const sharpeTxt = sharpe != null ? ` · S ${Number(sharpe).toFixed(1)}` : "";
        gaugeHtml = `<div style="position:relative;width:100px;height:16px;background:#1a1a2e;border-radius:4px;overflow:hidden" title="${src === 'fwd' ? 'Forward' : 'Backtest'}: ${wrClamped.toFixed(0)}% WR, ${trades} trades${sharpeTxt}">
          <div style="width:${wrClamped}%;height:100%;background:${wrColor};border-radius:4px;opacity:.7"></div>
          <span style="position:absolute;left:4px;top:0;line-height:16px;font-size:9px;color:#fff;text-shadow:0 0 3px #000">${src === 'fwd' ? 'FWD' : 'BT'} ${trades}t</span>
        </div>`;
      }
    }

    return `<tr>
      <td style="font-weight:600;font-size:.78rem;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${p.strategy}">${p.strategy.slice(0, 30)}</td>
      <td style="font-size:.72rem;color:#888">${p.bundle.slice(0, 25)}</td>
      <td><strong>${p.symbol}</strong></td>
      <td><span class="badge ${dirBadge}">${p.dir}</span></td>
      <td>$${fmtP(p.entry)}</td>
      <td>$${fmtP(p.tp)}</td>
      <td>$${fmtP(p.sl)}</td>
      <td style="font-weight:600;color:${pnlColor}" title="${pnlSource === 'live' ? 'Live unrealized PnL' : pnlSource === 'fwd' ? 'Forward test win rate (no live price)' : pnlSource === 'bt' ? 'Backtest win rate (no live price)' : 'No data'}">${pnlStr}${pnlSource && pnlSource !== 'live' ? `<span style="font-size:.6rem;color:#666;margin-left:2px">${pnlSource}</span>` : ''}</td>
      <td>${gaugeHtml}</td>
      <td style="font-size:.72rem;white-space:nowrap">${dateStr}</td>
    </tr>`;
  }).join("");
}

function renderAll() {
  setModeButtons();
  renderStatusFilters();
  renderVerificationSummary();
  renderActiveTrades();
  renderBundles();
  renderForwardLeaders();
  renderBabyStrats();
  renderGraduatedStrats();
  renderDirectionalTable();
  renderCalendar();
  renderGraduationCriteria();
  renderStatusDefinitions();
  renderUnregisteredStrategies();
}

async function loadBabyStrats() {
  const urls = [
    "./data/baby_strats_dashboard.json?t=" + Date.now(),
    "../incubator/config/baby_strats_dashboard.json?t=" + Date.now(),
    "https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/incubator/config/baby_strats_dashboard.json",
  ];

  let data = null;
  for (const url of urls) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) continue;
      data = await response.json();
      if (Array.isArray(data?.strategies)) break;
    } catch (err) {
      console.log("Failed to load", url, err?.message || err);
    }
  }

  DASHBOARD_DATA = data || { strategies: [] };
  BABY_STRATS = Array.isArray(DASHBOARD_DATA.strategies)
    ? DASHBOARD_DATA.strategies.map(mapStrategy)
    : [];

  // Fetch live prices from Binance for active trade PnL/gauge
  try {
    const symbols = new Set();
    for (const s of BABY_STRATS) {
      for (const pick of (s.forwardLivePicks || [])) {
        const sym = pick.symbol || pick.pair;
        if (sym) symbols.add(sym.replace("/", ""));
      }
    }
    if (symbols.size > 0) {
      const symList = JSON.stringify([...symbols]);
      const priceResp = await fetch(`https://api.binance.com/api/v3/ticker/price?symbols=${encodeURIComponent(symList)}`);
      if (priceResp.ok) {
        const priceData = await priceResp.json();
        DASHBOARD_DATA.prices = {};
        for (const p of priceData) {
          DASHBOARD_DATA.prices[p.symbol] = parseFloat(p.price);
        }
      }
    }
  } catch (e) { console.log("Price fetch failed (non-fatal):", e?.message); }

  renderAll();
}

function bindEvents() {
  document.getElementById("mode-forward").addEventListener("click", () => {
    METRIC_MODE = "forward";
    renderAll();
  });
  document.getElementById("mode-backtest").addEventListener("click", () => {
    METRIC_MODE = "backtest";
    renderAll();
  });
  document.getElementById("basis-real").addEventListener("click", () => {
    DATA_BASIS = "real_only";
    CALENDAR_STRATEGY = "all";
    renderAll();
  });
  document.getElementById("basis-all").addEventListener("click", () => {
    DATA_BASIS = "all";
    CALENDAR_STRATEGY = "all";
    renderAll();
  });
  document.getElementById("cal-mode-forward").addEventListener("click", () => {
    CALENDAR_MODE = "forward";
    renderAll();
  });
  document.getElementById("cal-mode-backtest").addEventListener("click", () => {
    CALENDAR_MODE = "backtest";
    renderAll();
  });
  document.getElementById("cal-norm-avg").addEventListener("click", () => {
    CALENDAR_NORM = "average";
    renderAll();
  });
  document.getElementById("cal-norm-sum").addEventListener("click", () => {
    CALENDAR_NORM = "sum";
    renderAll();
  });
  document.getElementById("fw-filter-all").addEventListener("click", () => {
    FW_FILTER = "all";
    renderAll();
  });
  document.getElementById("fw-filter-active").addEventListener("click", () => {
    FW_FILTER = "active";
    renderAll();
  });
  document.getElementById("survivors-toggle").addEventListener("click", () => {
    SURVIVORS_ONLY = !SURVIVORS_ONLY;
    renderAll();
  });

  document.getElementById("status-filters").addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-status]");
    if (!btn) return;
    const status = btn.getAttribute("data-status");
    if (!status) return;
    if (status === "all") {
      ACTIVE_STATUS_FILTERS = new Set(["all"]);
    } else {
      ACTIVE_STATUS_FILTERS.delete("all");
      if (ACTIVE_STATUS_FILTERS.has(status))
        ACTIVE_STATUS_FILTERS.delete(status);
      else ACTIVE_STATUS_FILTERS.add(status);
      if (!ACTIVE_STATUS_FILTERS.size) ACTIVE_STATUS_FILTERS = new Set(["all"]);
    }
    CALENDAR_STRATEGY = "all";
    renderAll();
  });

  document
    .getElementById("calendar-strategy-filter")
    .addEventListener("change", (ev) => {
      CALENDAR_STRATEGY = ev.target.value || "all";
      renderCalendar();
    });

  // Survivor strategies mode toggle
  const sysBT = document.getElementById("sys-mode-backtest");
  const sysFW = document.getElementById("sys-mode-forward");
  if (sysBT) sysBT.addEventListener("click", () => { SYSTEMS_MODE = "backtest"; renderSystemsAE(); });
  if (sysFW) sysFW.addEventListener("click", () => { SYSTEMS_MODE = "forward"; renderSystemsAE(); });

  // Bundle mode toggle
  const bundleBT = document.getElementById("bundle-mode-backtest");
  const bundleFW = document.getElementById("bundle-mode-forward");
  if (bundleBT) bundleBT.addEventListener("click", () => { BUNDLE_MODE = "backtest"; renderBundles(); });
  if (bundleFW) bundleFW.addEventListener("click", () => { BUNDLE_MODE = "forward"; renderBundles(); });
}

// ── Meta-Strategy Combos Panel ──────────────────────────────────
async function loadComboMetrics() {
  const urls = [
    "./data/combo_metrics.json?t=" + Date.now(),
    "https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/battleground/data/combo_metrics.json",
  ];
  let data = null;
  for (const url of urls) {
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (r.ok) { data = await r.json(); break; }
    } catch (_) {}
  }
  if (!data) {
    document.getElementById("combo-tbody").innerHTML =
      '<tr><td colspan="11" style="text-align:center;color:#666;padding:20px">No combo data yet. Run: python -m meta_strategy.permutation_engine</td></tr>';
    return;
  }
  renderComboMetrics(data);
}

function renderComboMetrics(data) {
  COMBO_DATA_CACHE = data;
  // Stats
  const el = (id) => document.getElementById(id);
  el("combo-total").textContent = data.total_permutations || 0;
  el("combo-active").textContent = data.active_combos || 0;
  el("combo-eliminated").textContent = data.eliminated_combos || 0;
  const resurrected = (data.elimination_log || []).filter(e => e.action === "RESURRECTED").length;
  el("combo-resurrected").textContent = resurrected;

  // Sortable headers
  const thead = document.getElementById("combo-thead");
  if (thead) {
    const arrow = (col) => COMBO_SORT_COL === col ? (COMBO_SORT_ASC ? " ▲" : " ▼") : "";
    const thS = 'style="cursor:pointer;user-select:none"';
    thead.innerHTML = `<tr><th>Combo</th><th>Logic</th><th>Systems</th><th ${thS} onclick="sortCombo('trades')">Trades${arrow("trades")}</th><th ${thS} onclick="sortCombo('wr')">WR${arrow("wr")}</th><th ${thS} onclick="sortCombo('sharpe')">Sharpe${arrow("sharpe")}</th><th ${thS} onclick="sortCombo('pf')">PF${arrow("pf")}</th><th ${thS} onclick="sortCombo('maxdd')">Max DD${arrow("maxdd")}</th><th ${thS} onclick="sortCombo('pvalue')">p-value${arrow("pvalue")}</th><th ${thS} onclick="sortCombo('portfolio')">Portfolio${arrow("portfolio")}</th><th>Status</th></tr>`;
  }

  // Winners table — show top 50 by default, sorted by selected column
  const tbody = el("combo-tbody");
  const allWinners = [...(data.winners || [])];
  allWinners.sort((a, b) => {
    let va, vb;
    const col = COMBO_SORT_COL;
    if (col === "trades") { va = a.total_trades || 0; vb = b.total_trades || 0; }
    else if (col === "wr") { va = a.win_rate ?? -999; vb = b.win_rate ?? -999; }
    else if (col === "sharpe") { va = a.sharpe ?? -999; vb = b.sharpe ?? -999; }
    else if (col === "pf") { va = a.profit_factor ?? -999; vb = b.profit_factor ?? -999; }
    else if (col === "maxdd") { va = a.max_drawdown_pct ?? 999; vb = b.max_drawdown_pct ?? 999; }
    else if (col === "pvalue") { va = a.p_value ?? 999; vb = b.p_value ?? 999; }
    else if (col === "portfolio") { va = a.portfolio_final ?? 0; vb = b.portfolio_final ?? 0; }
    else { va = a.total_trades || 0; vb = b.total_trades || 0; }
    return COMBO_SORT_ASC ? va - vb : vb - va;
  });
  const winners = allWinners.slice(0, 50);
  if (!winners.length) {
    tbody.innerHTML = '<tr><td colspan="11" style="text-align:center;color:#666;padding:20px">No winning combos yet</td></tr>';
  } else {
    tbody.innerHTML = winners.map(w => {
      const wr = w.win_rate != null ? (w.win_rate * 100).toFixed(1) + "%" : "--";
      const wrClass = w.win_rate > 0.55 ? "positive" : w.win_rate < 0.48 ? "negative" : "";
      const sharpeClass = w.sharpe > 1.0 ? "positive" : w.sharpe < 0.3 ? "negative" : "";
      const logicBadge = {
        "majority": "badge-passed", "unanimous": "badge-graduated",
        "weighted": "badge-new", "bayesian": "badge-redesigned",
        "dempster_shafer": "badge-redesigned", "regime_aware": "badge-paper",
        "inverse": "badge-failed", "consensus_plus_inverse": "badge-validating",
        "evolved": "badge-new",
      }[w.logic_type] || "badge-insufficient";
      const statusBadge = {
        "ACTIVE": "badge-passed", "RESURRECTED": "badge-redesigned",
        "ELIMINATED": "badge-failed", "PROBATION": "badge-paper",
      }[w.status] || "badge-insufficient";
      const systems = Array.isArray(w.systems) ? w.systems : [];
      const sysDisplay = systems.length > 3
        ? systems.slice(0, 3).join(", ") + ` +${systems.length - 3}`
        : systems.join(", ");
      return `<tr>
        <td style="font-weight:600;color:#fff;font-size:0.78rem;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${w.combo_id}">${w.combo_id.split("|")[0]}</td>
        <td><span class="badge ${logicBadge}">${w.logic_type}</span></td>
        <td style="font-size:0.72rem;color:#888" title="${systems.join(', ')}">${sysDisplay}</td>
        <td>${w.total_trades}</td>
        <td class="metric-value ${wrClass}">${wr}</td>
        <td class="metric-value ${sharpeClass}">${(w.sharpe || 0).toFixed(2)}</td>
        <td class="metric-value">${(w.profit_factor || 0).toFixed(2)}</td>
        <td class="metric-value ${w.max_drawdown_pct > 20 ? 'negative' : ''}">${(w.max_drawdown_pct || 0).toFixed(1)}%</td>
        <td style="font-size:0.75rem;color:${w.p_value < 0.05 ? '#22c55e' : w.p_value < 0.10 ? '#eab308' : '#ef4444'}">${(w.p_value || 1).toFixed(4)}</td>
        <td class="metric-value ${w.portfolio_return_pct > 0 ? 'positive' : 'negative'}">$${(w.portfolio_final || 1000).toFixed(0)}</td>
        <td><span class="badge ${statusBadge}">${w.status || 'ACTIVE'}</span></td>
      </tr>`;
    }).join("");
  }

  // Walk-forward
  const wfDiv = el("combo-walkforward");
  const wf = data.walkforward || [];
  if (!wf.length) {
    wfDiv.innerHTML = '<span style="color:#666">No walk-forward results yet</span>';
  } else {
    // Group by combo_id, show aggregate
    const byCombo = {};
    wf.forEach(f => {
      if (!byCombo[f.combo_id]) byCombo[f.combo_id] = [];
      byCombo[f.combo_id].push(f);
    });
    let html = '<table class="systems-table" style="font-size:0.78rem"><thead><tr><th>Combo</th><th>Folds</th><th>Robust</th><th>Avg OOS Sharpe</th><th>Avg Degradation</th><th>Verdict</th></tr></thead><tbody>';
    for (const [id, folds] of Object.entries(byCombo)) {
      const robust = folds.filter(f => f.is_robust).length;
      const avgSharpe = folds.reduce((s, f) => s + (f.test_sharpe || 0), 0) / folds.length;
      const avgDeg = folds.reduce((s, f) => s + (f.oos_degradation_pct || 0), 0) / folds.length;
      const isRobust = robust >= folds.length * 0.6;
      html += `<tr>
        <td style="font-weight:600;color:#fff;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${id.split("|")[0]}</td>
        <td>${folds.length}</td>
        <td>${robust}/${folds.length}</td>
        <td class="metric-value ${avgSharpe > 0 ? 'positive' : 'negative'}">${avgSharpe.toFixed(2)}</td>
        <td style="color:${avgDeg < 30 ? '#22c55e' : avgDeg < 50 ? '#eab308' : '#ef4444'}">${avgDeg.toFixed(0)}%</td>
        <td><span class="badge ${isRobust ? 'badge-passed' : 'badge-failed'}">${isRobust ? 'ROBUST' : 'OVERFIT'}</span></td>
      </tr>`;
    }
    html += '</tbody></table>';
    wfDiv.innerHTML = html;
  }

  // Adversarial compatibility
  const advDiv = el("combo-adversarial");
  const adv = data.adversarial || [];
  if (!adv.length) {
    advDiv.innerHTML = '<span style="color:#666">No adversarial compatibility data yet</span>';
  } else {
    let html = '<table class="systems-table" style="font-size:0.78rem"><thead><tr><th>Combo</th><th>System A</th><th>System B</th><th>Failure Overlap</th><th>Diversification</th><th>Rating</th></tr></thead><tbody>';
    adv.slice(0, 15).forEach(a => {
      const rating = a.diversification_score > 0.7 ? "EXCELLENT" : a.diversification_score > 0.5 ? "GOOD" : "POOR";
      const ratingBadge = a.diversification_score > 0.7 ? "badge-passed" : a.diversification_score > 0.5 ? "badge-paper" : "badge-failed";
      html += `<tr>
        <td style="font-size:0.72rem;color:#888">${a.combo_id.split("|")[0]}</td>
        <td style="color:#fff">${a.system_a}</td>
        <td style="color:#fff">${a.system_b}</td>
        <td class="metric-value ${a.failure_overlap_pct > 0.5 ? 'negative' : ''}">${(a.failure_overlap_pct * 100).toFixed(0)}%</td>
        <td class="metric-value ${a.diversification_score > 0.5 ? 'positive' : 'negative'}">${a.diversification_score.toFixed(2)}</td>
        <td><span class="badge ${ratingBadge}">${rating}</span></td>
      </tr>`;
    });
    html += '</tbody></table>';
    advDiv.innerHTML = html;
  }

  // Elimination log
  const elimDiv = el("combo-elim-log");
  const elims = data.elimination_log || [];
  if (!elims.length) {
    elimDiv.innerHTML = '<span style="color:#666">No elimination events yet</span>';
  } else {
    let html = '<div style="display:flex;flex-direction:column;gap:6px">';
    elims.slice(0, 10).forEach(e => {
      const icon = e.action === "ELIMINATED" ? "💀" : e.action === "RESURRECTED" ? "🔥" : e.action === "PROBATION" ? "⚠️" : "📋";
      const color = e.action === "ELIMINATED" ? "#ef4444" : e.action === "RESURRECTED" ? "#f59e0b" : "#888";
      const ts = e.timestamp ? new Date(e.timestamp).toLocaleString() : "--";
      html += `<div style="padding:8px;background:#1e1e3a22;border-radius:6px;border-left:3px solid ${color}">
        <span>${icon}</span>
        <span style="color:#fff;font-weight:600">${e.action}</span>
        <span style="color:#888;margin-left:8px">${e.combo_id}</span>
        <div style="font-size:0.72rem;color:#666;margin-top:4px">${e.reason || ''} · ${ts}</div>
      </div>`;
    });
    html += '</div>';
    elimDiv.innerHTML = html;
  }
}

function updateStatusBar() {
  const ts = document.getElementById("status-timestamp");
  if (ts) {
    const now = new Date();
    ts.textContent = "As of " + now.toLocaleString("en-US", { timeZone: "America/New_York", month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true }) + " EST";
  }
  const proven = SYSTEMS_AE.filter(s => s.status === "PROVEN");
  const el = (id) => document.getElementById(id);
  if (el("sq-active-strats")) el("sq-active-strats").textContent = proven.length;
  const wrs = proven.map(s => parseFloat(s.winRate));
  const avgWR = wrs.length ? (wrs.reduce((a,b)=>a+b,0)/wrs.length).toFixed(1)+"%" : "--";
  const wrEl = el("sq-avg-wr");
  if (wrEl) { wrEl.textContent = avgWR; wrEl.style.color = parseFloat(avgWR)>=55 ? "#22c55e" : parseFloat(avgWR)>=50 ? "#eab308" : "#ef4444"; }
  const sharpes = proven.map(s => s.sharpe).filter(s => s > 0);
  if (el("sq-best-sharpe")) el("sq-best-sharpe").textContent = sharpes.length ? Math.max(...sharpes).toFixed(2) : "--";
  const comboActive = el("combo-active");
  if (el("sq-dna-combos") && comboActive) el("sq-dna-combos").textContent = comboActive.textContent || "--";
  const qualityEl = el("sq-quality");
  if (qualityEl) {
    const avgSharpe = sharpes.length ? sharpes.reduce((a,b)=>a+b,0)/sharpes.length : 0;
    const avgWRn = wrs.length ? wrs.reduce((a,b)=>a+b,0)/wrs.length : 0;
    const score = Math.min(100, Math.round(avgSharpe*20 + (avgWRn-50)*2));
    qualityEl.textContent = score + "/100";
    qualityEl.style.color = score >= 70 ? "#22c55e" : score >= 50 ? "#eab308" : "#ef4444";
  }
  const badge = el("status-health-badge");
  if (badge) {
    const avgWRn = wrs.length ? wrs.reduce((a,b)=>a+b,0)/wrs.length : 0;
    if (avgWRn >= 60) { badge.textContent = "HEALTHY"; badge.style.background = "#22c55e22"; badge.style.color = "#22c55e"; }
    else if (avgWRn >= 50) { badge.textContent = "MODERATE"; badge.style.background = "#eab30822"; badge.style.color = "#eab308"; }
    else { badge.textContent = "NEEDS ATTENTION"; badge.style.background = "#ef444422"; badge.style.color = "#ef4444"; }
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  renderSystemsAE();
  bindEvents();
  updateTimestamps();
  updateStatusBar();
  await Promise.all([loadBabyStrats(), loadStrategyManifest(), loadComboMetrics()]);
  renderUnregisteredStrategies();
  updateStatusBar();
  setInterval(async () => {
    updateTimestamps();
    updateStatusBar();
    await loadBabyStrats();
  }, 90000);
});
