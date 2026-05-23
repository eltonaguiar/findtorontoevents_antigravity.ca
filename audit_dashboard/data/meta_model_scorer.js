// META-MODEL SCORER v1.0 — Auto-generated from meta_model_trainer.py
// Trained: 2026-03-16T11:58:26.741263Z
// ROC AUC: 0.7358 (logistic) | 0.734 (GBM diagnostic)
// Optimal threshold: 0.517
// LEAK-FREE: Excludes LivePnL and Freshness from entry scoring

const META_MODEL = {
  "intercept": 1.52863942,
  "threshold": 0.517,
  "features": [
    {
      "name": "entry_score",
      "coef": 0.0,
      "mean": 0.0,
      "std": 1.0
    },
    {
      "name": "comp_strategy",
      "coef": 0.0,
      "mean": 0.0,
      "std": 1.0
    },
    {
      "name": "comp_signal",
      "coef": 0.0,
      "mean": 0.0,
      "std": 1.0
    },
    {
      "name": "comp_forward",
      "coef": 0.0,
      "mean": 0.0,
      "std": 1.0
    },
    {
      "name": "comp_consensus",
      "coef": 0.0,
      "mean": 0.0,
      "std": 1.0
    },
    {
      "name": "comp_noconflict",
      "coef": 0.0,
      "mean": 0.0,
      "std": 1.0
    },
    {
      "name": "comp_timeframe",
      "coef": 0.0,
      "mean": 0.0,
      "std": 1.0
    },
    {
      "name": "Forward WR",
      "coef": 0.0,
      "mean": 0.0,
      "std": 1.0
    },
    {
      "name": "Forward Trades",
      "coef": 0.015654,
      "mean": 0.45674967,
      "std": 5.20136119
    },
    {
      "name": "Confluence Count",
      "coef": 0.30626347,
      "mean": 1.20314548,
      "std": 0.67584465
    },
    {
      "name": "is_long",
      "coef": 0.26453005,
      "mean": 0.87483617,
      "std": 0.33090458
    },
    {
      "name": "short_in_bull",
      "coef": 0.0,
      "mean": 0.0,
      "std": 1.0
    },
    {
      "name": "tf_INTRADAY",
      "coef": -0.00841595,
      "mean": 0.30865007,
      "std": 0.46193636
    },
    {
      "name": "tf_POSITION",
      "coef": -0.20420651,
      "mean": 0.00131062,
      "std": 0.0361787
    },
    {
      "name": "tf_SCALP",
      "coef": -0.28081655,
      "mean": 0.00262123,
      "std": 0.05113082
    },
    {
      "name": "tf_SWING",
      "coef": 0.05529973,
      "mean": 0.68741809,
      "std": 0.46354553
    },
    {
      "name": "trust_code",
      "coef": 0.28493187,
      "mean": 0.91153342,
      "std": 1.37403773
    },
    {
      "name": "grade_code",
      "coef": 2.09919748,
      "mean": 0.30209699,
      "std": 0.47183677
    }
  ]
};

/**
 * Compute meta-model win probability for a pick.
 * @param {Object} f - Feature values keyed by feature name
 * @returns {number} Win probability 0-1
 */
function metaWinProb(f) {
  let z = META_MODEL.intercept;
  for (const feat of META_MODEL.features) {
    const raw = f[feat.name] ?? 0.0;
    const std = feat.std || 1.0;
    const standardized = (raw - feat.mean) / std;
    z += feat.coef * standardized;
  }
  return 1.0 / (1.0 + Math.exp(-z));
}

/**
 * Grade a pick using meta-model probability.
 * @param {number} prob - Win probability from metaWinProb()
 * @returns {string} Grade A-F
 */
function metaGrade(prob) {
  if (prob >= 0.80) return 'A';
  if (prob >= 0.65) return 'B';
  if (prob >= 0.50) return 'C';
  if (prob >= 0.35) return 'D';
  return 'F';
}
