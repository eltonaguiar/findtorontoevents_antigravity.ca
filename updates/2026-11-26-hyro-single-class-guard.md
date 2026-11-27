# Hyro ML pick optimizer — single-class training guard

## What was broken

`audit-dashboard.yml` runs the step **"Run Hyro ML pick optimizer (adaptive edge scoring + drift detection)"** as:

```
python tools/hyro_ml_pick_optimizer.py --save
```

Workflow run **45748152095** failed in that step with:

```
ValueError: y contains 1 class after sample_weight trimmed classes with zero weights,
while a minimum of 2 classes are required.
```

Raised from `sklearn.ensemble.GradientBoostingClassifier.fit` inside
`train_model()` (`tools/hyro_ml_pick_optimizer.py`). When enough labeled
samples exist (`len(X_rows) >= MIN_SAMPLES_FOR_ML`, i.e. >= 10) but every
label is the same outcome (all WIN or all LOSS), the label array `y` has a
single class and a binary classifier cannot be fit.

Note: despite the wording, this sklearn message is also emitted when
`sample_weight is None` — sklearn's `_gb.py` sets
`n_trim_classes = n_classes` in that case, so a one-class `y` triggers the
same `ValueError`. This matches the code path in this file exactly (no
`sample_weight`, no `Pipeline`). Reproduced locally on scikit-learn 1.8.0.

## Fix

Minimal, local guard in `train_model()`, immediately after `X`/`y` are built
and NaN-cleaned, before any model is constructed:

- Compute `classes = np.unique(y)`.
- If `classes.size < 2`: log a clear warning and `return None`.

Returning `None` is the module's existing "not enough data" contract:
`run()` then scores with the heuristic fallback (`scoring_method:
"heuristic"`) instead of crashing the workflow step. No thresholds, features,
or model choice were changed, and the behaviour for >= 2 classes is
untouched.

File changed: `tools/hyro_ml_pick_optimizer.py` (guard at lines 393-405).

## Verification

1. `python3 -m py_compile tools/hyro_ml_pick_optimizer.py` -> OK.
2. Synthetic calls to the imported `train_model()` (model/history paths
   redirected to a temp dir):
   - 12 samples, all labels 0 -> returned `None`, warning logged, no model
     file written, no exception. PASS
   - 12 samples, all labels 1 -> returned `None`. PASS
   - 12 samples, two classes -> `GradientBoosting` trained,
     `samples=12`, model file written. PASS

Reproduced the original failure first: `GradientBoostingClassifier.fit` on a
one-class `y` raises the exact log error on scikit-learn 1.8.0, confirming the
log evidence matches this code path.
