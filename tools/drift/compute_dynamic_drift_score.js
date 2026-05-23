#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

function readJson(p) {
  const s = fs.readFileSync(p, "utf8");
  return JSON.parse(s.charCodeAt(0) === 0xFEFF ? s.slice(1) : s);
}

function writeJson(p, obj) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(obj, null, 2));
}

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    const k = argv[i];
    const v = argv[i + 1];
    if (!k.startsWith("--")) continue;
    out[k.slice(2)] = v;
    i += 1;
  }
  return out;
}

function clampNum(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function parseHourUtc(s) {
  if (!s) return null;
  const normalized = s.replace(" ", "T") + ":00Z";
  const d = new Date(normalized);
  if (Number.isNaN(d.getTime())) return null;
  return d;
}

function inWindowUtc(date, windowSpec) {
  if (!date || !windowSpec) return false;
  const [start, end] = windowSpec.split("-");
  const [sh, sm] = start.split(":").map((x) => Number(x));
  const [eh, em] = end.split(":").map((x) => Number(x));
  const minute = date.getUTCHours() * 60 + date.getUTCMinutes();
  const startMin = sh * 60 + sm;
  const endMin = eh * 60 + em;
  return minute >= startMin && minute <= endMin;
}

function stdDev(values) {
  if (!values.length) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((acc, v) => acc + (v - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function mean(values) {
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function main() {
  const args = parseArgs(process.argv);
  const inputPath = args.input || "audit_dashboard/data/hourly_asset_class_24h_report.json";
  const configPath = args.config || "config/drift_params.json";
  const outputPath = args.output || "audit_dashboard/data/drift_scores_latest.json";

  const report = readJson(inputPath);
  const cfg = readJson(configPath);
  const rows = Array.isArray(report.hourly_by_asset_class) ? report.hourly_by_asset_class.slice() : [];

  rows.sort((a, b) => {
    const ah = parseHourUtc(a.hour_utc)?.getTime() || 0;
    const bh = parseHourUtc(b.hour_utc)?.getTime() || 0;
    if (ah !== bh) return ah - bh;
    return String(a.asset_class || "").localeCompare(String(b.asset_class || ""));
  });

  const emaN = clampNum(cfg.ema_hours, 8);
  const alpha = 2 / (emaN + 1);
  const sigmaK = clampNum(cfg.sigma_threshold, 2.0);
  const probationHits = clampNum(cfg.probation_consecutive_hours, 2);

  const pfEmaByClass = {};
  const wrGapHistoryByClass = {};
  const scoreHistoryByClass = {};
  const consecutiveByClass = {};

  const scored = [];

  for (const row of rows) {
    const assetClass = String(row.asset_class || "UNKNOWN").toUpperCase();
    const baseline = (cfg.asset_class_baselines && cfg.asset_class_baselines[assetClass]) ||
      (cfg.asset_class_baselines && cfg.asset_class_baselines.UNKNOWN) ||
      { win_rate: 50, expectancy: 0 };

    const weights = (cfg.weights && cfg.weights[assetClass]) ||
      (cfg.weights && cfg.weights.default) ||
      { w: 0.6, b: 0.25, c: 0.15 };

    const currentWr = clampNum(row.win_rate_pct, 0);
    const currentExp = clampNum(row.avg_pnl_pct, 0);
    const currentPf = clampNum(row.profit_factor, 0);

    const wrGap = Math.max(0, clampNum(baseline.win_rate, 50) - currentWr);
    const expectancyGap = Math.max(0, clampNum(baseline.expectancy, 0) - currentExp);

    const lastPfEma = pfEmaByClass[assetClass];
    const pfEma = typeof lastPfEma === "number" ? alpha * currentPf + (1 - alpha) * lastPfEma : currentPf;
    pfEmaByClass[assetClass] = pfEma;
    const pfGap = Math.max(0, 1 - pfEma);

    const regimeCfg = cfg.regime_windows && cfg.regime_windows[assetClass];
    const dt = parseHourUtc(row.hour_utc);
    const isRegimeWindow = regimeCfg ? inWindowUtc(dt, regimeCfg.night_window) : false;

    const compMult = (regimeCfg && regimeCfg.components) || { win_rate: 1, pf: 1, expectancy: 1 };
    let score =
      clampNum(weights.w, 0.6) * wrGap * (isRegimeWindow ? clampNum(compMult.win_rate, 1) : 1) +
      clampNum(weights.b, 0.25) * pfGap * (isRegimeWindow ? clampNum(compMult.pf, 1) : 1) +
      clampNum(weights.c, 0.15) * expectancyGap * (isRegimeWindow ? clampNum(compMult.expectancy, 1) : 1);

    if (isRegimeWindow && regimeCfg.weight_multiplier) {
      score *= clampNum(regimeCfg.weight_multiplier, 1);
    }

    const wrGapHistory = wrGapHistoryByClass[assetClass] || [];
    const wrGapMean = mean(wrGapHistory);
    const wrGapStd = stdDev(wrGapHistory);
    const wrGapThreshold = wrGapMean + sigmaK * (wrGapStd || 1);
    const wrGapHighSigma = wrGap > wrGapThreshold;

    const scoreHistory = scoreHistoryByClass[assetClass] || [];
    const scoreMean = mean(scoreHistory);
    const scoreStd = stdDev(scoreHistory);
    const classThreshold = scoreMean + sigmaK * (scoreStd || 1);

    const highDrift = score > classThreshold;
    const prevConsecutive = consecutiveByClass[assetClass] || 0;
    const consecutive = highDrift ? prevConsecutive + 1 : 0;
    consecutiveByClass[assetClass] = consecutive;

    const probation = consecutive >= probationHits;

    const resultRow = {
      event_ts: dt ? dt.toISOString() : null,
      hour_utc: row.hour_utc,
      asset_class: assetClass,
      picks: clampNum(row.picks, 0),
      win_rate_pct: currentWr,
      avg_pnl_pct: currentExp,
      profit_factor: currentPf,
      pf_ema: Number(pfEma.toFixed(6)),
      win_rate_gap: Number(wrGap.toFixed(6)),
      expectancy_gap: Number(expectancyGap.toFixed(6)),
      wr_gap_mean_hist: Number(wrGapMean.toFixed(6)),
      wr_gap_std_hist: Number(wrGapStd.toFixed(6)),
      wr_gap_sigma_threshold: Number(wrGapThreshold.toFixed(6)),
      wr_gap_high_sigma: wrGapHighSigma,
      drift_score: Number(score.toFixed(6)),
      class_score_threshold: Number(classThreshold.toFixed(6)),
      high_drift: highDrift,
      consecutive_high_drift_hours: consecutive,
      probation,
      regime_window_applied: isRegimeWindow
    };

    scored.push(resultRow);

    wrGapHistory.push(wrGap);
    wrGapHistoryByClass[assetClass] = wrGapHistory;
    scoreHistory.push(score);
    scoreHistoryByClass[assetClass] = scoreHistory;
  }

  const latestByClass = {};
  for (const r of scored) {
    latestByClass[r.asset_class] = r;
  }

  const out = {
    generated_at_utc: new Date().toISOString(),
    source: inputPath,
    config: configPath,
    rows: scored,
    latest_by_asset_class: Object.values(latestByClass).sort((a, b) => b.drift_score - a.drift_score)
  };

  writeJson(outputPath, out);
  process.stdout.write(`Wrote ${out.rows.length} rows to ${outputPath}\n`);
}

main();
