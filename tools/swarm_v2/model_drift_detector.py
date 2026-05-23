from __future__ import annotations

"""
Model Drift Detector

Detects drift between backtest and live trading performance by comparing
key metrics (win rate, profit factor, max drawdown) and running a manual
chi-squared test on the win/loss distribution.  Also provides walk-forward
validation to guard against overfitting — all without external ML libraries.
"""

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger: logging.Logger = logging.getLogger("swarm_v2.drift")


# ---------------------------------------------------------------------------
# Drift thresholds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriftThresholds:
    """Default thresholds for drift classification."""

    win_rate_decay_pct: float = 15.0       # WR decay > 15 % → WARNING
    profit_factor_decay_pct: float = 25.0  # PF decay > 25 % → WARNING
    max_drawdown_increase_pct: float = 50.0  # DD increase > 50 % → CRITICAL
    distribution_p_value: float = 0.05     # p < 0.05 → SIGNIFICANT_DRIFT


DEFAULT_THRESHOLDS = DriftThresholds()


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


@dataclass
class TradeRecord:
    """Normalised trade record used by the detector."""

    result: str  # "win" or "loss"
    pnl: float
    timestamp: str | None = None
    module: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TradeRecord:
        return cls(
            result="win" if d.get("result") in ("win", "W", True, 1) else "loss",
            pnl=float(d.get("pnl", d.get("profit", 0.0))),
            timestamp=d.get("timestamp"),
            module=d.get("module"),
        )


# ---------------------------------------------------------------------------
# Chi-squared helper (manual — no scipy)
# ---------------------------------------------------------------------------

def chi_squared_test(
    observed: list[int], expected: list[float]
) -> tuple[float, float]:
    """
    Perform a Pearson chi-squared test.

    Parameters
    ----------
    observed:
        Observed frequencies.
    expected:
        Expected frequencies (must sum to same total as *observed*).

    Returns
    -------
    tuple
        ``(chi2_statistic, p_value)`` with 1 degree of freedom.
        The p-value is a rough approximation using the chi-square CDF
        for df=1.
    """
    if len(observed) != len(expected) or sum(observed) == 0:
        return 0.0, 1.0

    chi2 = sum(
        ((o - e) ** 2) / e if e > 0 else 0.0
        for o, e in zip(observed, expected)
    )

    # Approximate p-value for df=1 using the survival function:
    #   p ≈ erfc(sqrt(chi2 / 2))
    p_value = math.erfc(math.sqrt(chi2 / 2.0))
    return chi2, max(0.0, min(1.0, p_value))


# ---------------------------------------------------------------------------
# ModelDriftDetector
# ---------------------------------------------------------------------------


class ModelDriftDetector:
    """
    Detect drift between backtest and live trading results.

    Parameters
    ----------
    backtest_results_path:
        Path to a JSON file or directory containing backtest trade records.
    live_results_path:
        Path to a JSON file or directory containing live trade records.
    """

    def __init__(
        self,
        backtest_results_path: str,
        live_results_path: str,
    ) -> None:
        self.backtest_path: Path = Path(backtest_results_path)
        self.live_path: Path = Path(live_results_path)
        self.backtest_trades: list[TradeRecord] = []
        self.live_trades: list[TradeRecord] = []
        self._load_trades()
        logger.info(
            "ModelDriftDetector initialised: %d backtest trades, %d live trades",
            len(self.backtest_trades),
            len(self.live_trades),
        )

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def compute_backtest_metrics(self) -> dict[str, float]:
        """
        Compute aggregate performance metrics from backtest trades.

        Returns
        -------
        dict
            ``win_rate``, ``profit_factor``, ``max_drawdown``,
            ``total_trades``, ``net_pnl``, ``sharpe_ratio``.
        """
        return self._compute_metrics(self.backtest_trades)

    def compute_live_metrics(self) -> dict[str, float]:
        """
        Compute aggregate performance metrics from live trades.

        Returns
        -------
        dict
            Same keys as :meth:`compute_backtest_metrics`.
        """
        return self._compute_metrics(self.live_trades)

    def detect_performance_drift(self) -> dict[str, Any]:
        """
        Compare backtest vs live metrics and compute percentage decay.

        Returns
        -------
        dict
            Each key (e.g. ``win_rate``) maps to a sub-dict with
            ``backtest``, ``live``, ``decay_pct``, and ``severity``
            (``OK`` | ``WARNING`` | ``CRITICAL``).
        """
        logger.info("Detecting performance drift …")
        bt = self.compute_backtest_metrics()
        live = self.compute_live_metrics()

        drift: dict[str, Any] = {}
        for key in ("win_rate", "profit_factor", "max_drawdown"):
            bt_val = bt.get(key, 0.0)
            live_val = live.get(key, 0.0)

            if key == "max_drawdown":
                # For drawdown, *increase* is bad (live > backtest)
                decay_pct = (
                    ((live_val - bt_val) / abs(bt_val) * 100.0)
                    if bt_val
                    else 0.0
                )
                severity = (
                    "CRITICAL"
                    if decay_pct > DEFAULT_THRESHOLDS.max_drawdown_increase_pct
                    else "OK"
                )
            else:
                decay_pct = (
                    ((bt_val - live_val) / abs(bt_val) * 100.0)
                    if bt_val
                    else 0.0
                )
                if key == "win_rate":
                    severity = (
                        "WARNING"
                        if decay_pct > DEFAULT_THRESHOLDS.win_rate_decay_pct
                        else "OK"
                    )
                else:  # profit_factor
                    severity = (
                        "WARNING"
                        if decay_pct > DEFAULT_THRESHOLDS.profit_factor_decay_pct
                        else "OK"
                    )

            drift[key] = {
                "backtest": round(bt_val, 6),
                "live": round(live_val, 6),
                "decay_pct": round(decay_pct, 2),
                "severity": severity,
            }

        drift["net_pnl"] = {
            "backtest": round(bt.get("net_pnl", 0.0), 4),
            "live": round(live.get("net_pnl", 0.0), 4),
        }

        logger.info("Performance drift: %s", drift)
        return drift

    def detect_distribution_drift(self) -> dict[str, Any]:
        """
        Run a chi-squared test on the win/loss distribution.

        Tests whether the live win/loss proportion differs significantly
        from the backtest proportion.

        Returns
        -------
        dict
            ``chi2``, ``p_value``, ``significant`` (bool),
            ``backtest_distribution``, ``live_distribution``.
        """
        logger.info("Detecting distribution drift …")
        if not self.backtest_trades or not self.live_trades:
            return {
                "chi2": 0.0,
                "p_value": 1.0,
                "significant": False,
                "backtest_distribution": {"wins": 0, "losses": 0},
                "live_distribution": {"wins": 0, "losses": 0},
            }

        bt_wins = sum(1 for t in self.backtest_trades if t.result == "win")
        bt_losses = len(self.backtest_trades) - bt_wins
        lv_wins = sum(1 for t in self.live_trades if t.result == "win")
        lv_losses = len(self.live_trades) - lv_wins

        # Expected frequencies = backtest proportions scaled to live total
        live_total = len(self.live_trades)
        bt_total = len(self.backtest_trades)
        exp_win = (bt_wins / bt_total) * live_total if bt_total else 0.0
        exp_loss = (bt_losses / bt_total) * live_total if bt_total else 0.0

        chi2, p_value = chi_squared_test(
            observed=[lv_wins, lv_losses],
            expected=[exp_win, exp_loss],
        )

        significant = p_value < DEFAULT_THRESHOLDS.distribution_p_value

        result = {
            "chi2": round(chi2, 4),
            "p_value": round(p_value, 6),
            "significant": significant,
            "backtest_distribution": {"wins": bt_wins, "losses": bt_losses},
            "live_distribution": {"wins": lv_wins, "losses": lv_losses},
        }
        logger.info("Distribution drift: chi2=%.4f, p=%.6f, significant=%s", chi2, p_value, significant)
        return result

    def identify_overfitting_signals(self) -> list[str]:
        """
        Enumerate specific warning signs of overfitting.

        Returns
        -------
        list[str]
            Human-readable warning strings.
        """
        logger.info("Identifying overfitting signals …")
        signals: list[str] = []

        bt = self.compute_backtest_metrics()
        live = self.compute_live_metrics()

        # Signal 1: Win rate collapse
        wr_decay = (
            ((bt["win_rate"] - live["win_rate"]) / bt["win_rate"] * 100.0)
            if bt["win_rate"]
            else 0.0
        )
        if wr_decay > DEFAULT_THRESHOLDS.win_rate_decay_pct:
            signals.append(
                f"OVERFIT_SIGNAL: Win rate decayed {wr_decay:.1f}% from backtest "
                f"({bt['win_rate']:.2%}) to live ({live['win_rate']:.2%}) — "
                "model may be curve-fitted to historical patterns"
            )

        # Signal 2: Profit factor collapse
        pf_decay = (
            ((bt["profit_factor"] - live["profit_factor"]) / bt["profit_factor"] * 100.0)
            if bt["profit_factor"]
            else 0.0
        )
        if pf_decay > DEFAULT_THRESHOLDS.profit_factor_decay_pct:
            signals.append(
                f"OVERFIT_SIGNAL: Profit factor decayed {pf_decay:.1f}% from backtest "
                f"({bt['profit_factor']:.2f}) to live ({live['profit_factor']:.2f}) — "
                "tail-risk behaviour not captured in backtest"
            )

        # Signal 3: Drawdown explosion
        dd_increase = (
            ((live["max_drawdown"] - bt["max_drawdown"]) / bt["max_drawdown"] * 100.0)
            if bt["max_drawdown"]
            else 0.0
        )
        if dd_increase > DEFAULT_THRESHOLDS.max_drawdown_increase_pct:
            signals.append(
                f"OVERFIT_SIGNAL: Max drawdown increased {dd_increase:.1f}% in live "
                f"({live['max_drawdown']:.4f} vs backtest {bt['max_drawdown']:.4f}) — "
                "risk controls likely insufficient"
            )

        # Signal 4: PnL inversion
        if bt.get("net_pnl", 0.0) > 0 and live.get("net_pnl", 0.0) < 0:
            signals.append(
                "OVERFIT_SIGNAL: Net PnL flipped positive in backtest to negative live — "
                "strong evidence of overfitting or regime change"
            )

        # Signal 5: Sharpe degradation
        if bt.get("sharpe_ratio", 0.0) > 1.0 and live.get("sharpe_ratio", 0.0) < 0.5:
            signals.append(
                f"OVERFIT_SIGNAL: Sharpe ratio collapsed from {bt['sharpe_ratio']:.2f} "
                f"to {live['sharpe_ratio']:.2f} — edge not robust out-of-sample"
            )

        # Signal 6: Distribution drift
        dist = self.detect_distribution_drift()
        if dist["significant"]:
            signals.append(
                f"OVERFIT_SIGNAL: Win/loss distribution significantly shifted "
                f"(chi2={dist['chi2']:.2f}, p={dist['p_value']:.4f}) — "
                "statistical evidence of drift"
            )

        # Signal 7: Sample size disparity (backtest much larger than live)
        if len(self.backtest_trades) > len(self.live_trades) * 10:
            signals.append(
                "OVERFIT_SIGNAL: Backtest sample size is >10x live sample — "
                "backtest confidence may be inflated"
            )

        logger.info("Found %d overfitting signals", len(signals))
        return signals

    def generate_drift_alert(self) -> str | None:
        """
        Produce a single alert message if drift exceeds thresholds.

        Returns
        -------
        str | None
            Alert markdown string, or ``None`` if all metrics are OK.
        """
        logger.info("Generating drift alert …")
        perf_drift = self.detect_performance_drift()
        dist_drift = self.detect_distribution_drift()
        signals = self.identify_overfitting_signals()

        max_severity = "OK"
        for metric in ("win_rate", "profit_factor", "max_drawdown"):
            sev = perf_drift[metric]["severity"]
            if sev == "CRITICAL":
                max_severity = "CRITICAL"
                break
            elif sev == "WARNING" and max_severity != "CRITICAL":
                max_severity = "WARNING"

        if dist_drift["significant"] and max_severity != "CRITICAL":
            max_severity = "WARNING"

        if max_severity == "OK" and not signals:
            logger.info("No drift detected — all clear")
            return None

        lines: list[str] = []
        lines.append(f"## [{max_severity}] Model Drift Alert\n")

        # Performance summary
        lines.append("### Performance Decay\n")
        for metric in ("win_rate", "profit_factor", "max_drawdown"):
            d = perf_drift[metric]
            lines.append(
                f"- **{metric.replace('_', ' ').title()}**: "
                f"backtest={d['backtest']:.4f}, live={d['live']:.4f}, "
                f"decay={d['decay_pct']:.1f}% [{d['severity']}]"
            )
        lines.append("")

        # Distribution
        lines.append("### Distribution Drift\n")
        sig_label = "SIGNIFICANT" if dist_drift["significant"] else "not significant"
        lines.append(
            f"- Chi2={dist_drift['chi2']:.4f}, p-value={dist_drift['p_value']:.6f} "
            f"[{sig_label}]"
        )
        lines.append("")

        # Signals
        if signals:
            lines.append("### Overfitting Signals\n")
            for sig in signals:
                lines.append(f"- {sig}")
            lines.append("")

        alert = "\n".join(lines)
        logger.info("Drift alert generated [%s]", max_severity)
        return alert

    @staticmethod
    def walk_forward_validation(
        data: list[Any],
        train_size: float = 0.7,
        n_splits: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Manual walk-forward validation without sklearn.

        Splits *data* into *n_splits* contiguous windows.  For each window,
        the first ``train_size`` fraction is the training fold and the
        remainder is the test fold.  Windows slide forward by one
        test-fold length per split.

        Parameters
        ----------
        data:
            Sequence of records (dicts with at least ``result`` and ``pnl``).
        train_size:
            Fraction of each window used for training (default 0.7).
        n_splits:
            Number of walk-forward splits (default 5).

        Returns
        -------
        list[dict]
            Each dict has ``split``, ``train_start``, ``train_end``,
            ``test_start``, ``test_end``, ``train_metrics``,
            ``test_metrics``.
        """
        logger.info(
            "Walk-forward validation: %d records, %d splits, train_size=%.2f",
            len(data),
            n_splits,
            train_size,
        )

        if not data or n_splits < 1:
            return []

        results: list[dict[str, Any]] = []
        n = len(data)
        test_fold_size = max(1, int(n * (1 - train_size) / n_splits))
        train_fold_size = max(1, int(n * train_size / n_splits))

        for split in range(n_splits):
            test_start = split * test_fold_size
            test_end = min(test_start + test_fold_size, n)
            train_start = max(0, test_start - train_fold_size)
            train_end = test_start

            if train_start >= train_end or test_start >= test_end:
                continue

            train_fold = data[train_start:train_end]
            test_fold = data[test_start:test_end]

            train_metrics = ModelDriftDetector._compute_fold_metrics(train_fold)
            test_metrics = ModelDriftDetector._compute_fold_metrics(test_fold)

            results.append(
                {
                    "split": split + 1,
                    "train_start": train_start,
                    "train_end": train_end,
                    "test_start": test_start,
                    "test_end": test_end,
                    "train_size": len(train_fold),
                    "test_size": len(test_fold),
                    "train_metrics": train_metrics,
                    "test_metrics": test_metrics,
                    "wr_decay_pct": round(
                        (
                            (train_metrics["win_rate"] - test_metrics["win_rate"])
                            / train_metrics["win_rate"]
                            * 100.0
                        )
                        if train_metrics["win_rate"]
                        else 0.0,
                        2,
                    ),
                }
            )

        logger.info("Walk-forward validation produced %d results", len(results))
        return results

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _load_trades(self) -> None:
        """Load trade records from JSON file(s)."""
        self.backtest_trades = self._load_source(self.backtest_path)
        self.live_trades = self._load_source(self.live_path)

    def _load_source(self, path: Path) -> list[TradeRecord]:
        """Load trades from a JSON file or all JSON files under a directory."""
        trades: list[TradeRecord] = []
        files: list[Path] = []

        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.glob("*.json")))
        else:
            logger.warning("Path not found: %s", path)
            return trades

        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Skipping %s: %s", fp, exc)
                continue

            # Payload may be a list of records or a dict with a "trades" key
            records: list[dict[str, Any]] = []
            if isinstance(payload, list):
                records = payload
            elif isinstance(payload, dict):
                records = payload.get("trades", payload.get("results", []))

            for rec in records:
                try:
                    trades.append(TradeRecord.from_dict(rec))
                except (KeyError, ValueError, TypeError) as exc:
                    logger.debug("Skipping malformed record in %s: %s", fp, exc)

        return trades

    @staticmethod
    def _compute_metrics(trades: list[TradeRecord]) -> dict[str, float]:
        """Compute standard performance metrics from a list of trades."""
        if not trades:
            return {
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0.0,
                "net_pnl": 0.0,
                "sharpe_ratio": 0.0,
            }

        wins = sum(1 for t in trades if t.result == "win")
        losses = len(trades) - wins
        win_rate = wins / len(trades)

        gross_profit = sum(t.pnl for t in trades if t.result == "win" and t.pnl > 0)
        gross_loss = sum(abs(t.pnl) for t in trades if t.result == "loss" or t.pnl < 0)
        profit_factor = gross_profit / gross_loss if gross_loss else 0.0
        net_pnl = gross_profit - gross_loss

        # Max drawdown from cumulative PnL curve
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in trades:
            cumulative += t.pnl
            peak = max(peak, cumulative)
            dd = peak - cumulative
            max_dd = max(max_dd, dd)

        # Sharpe-like ratio (no risk-free rate)
        pnls = [t.pnl for t in trades]
        avg_pnl = sum(pnls) / len(pnls)
        variance = sum((p - avg_pnl) ** 2 for p in pnls) / len(pnls)
        std_pnl = math.sqrt(variance) if variance > 0 else 0.0
        sharpe = avg_pnl / std_pnl if std_pnl else 0.0

        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_dd,
            "total_trades": float(len(trades)),
            "net_pnl": net_pnl,
            "sharpe_ratio": sharpe,
        }

    @staticmethod
    def _compute_fold_metrics(fold: list[Any]) -> dict[str, float]:
        """Compute metrics for a walk-forward fold from raw dict records."""
        trades: list[TradeRecord] = []
        for rec in fold:
            if isinstance(rec, dict):
                trades.append(TradeRecord.from_dict(rec))
            elif isinstance(rec, TradeRecord):
                trades.append(rec)
        return ModelDriftDetector._compute_metrics(trades)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover
    """CLI convenience runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Model drift detector")
    parser.add_argument("backtest", help="Path to backtest JSON file or directory")
    parser.add_argument("live", help="Path to live JSON file or directory")
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="Also run walk-forward validation on backtest data",
    )
    parser.add_argument("--report", action="store_true", help="Print full drift report")
    args = parser.parse_args()

    detector = ModelDriftDetector(args.backtest, args.live)

    if args.report:
        bt = detector.compute_backtest_metrics()
        live = detector.compute_live_metrics()
        drift = detector.detect_performance_drift()
        dist = detector.detect_distribution_drift()
        signals = detector.identify_overfitting_signals()
        alert = detector.generate_drift_alert()

        print("# Model Drift Report\n")
        print("## Backtest Metrics")
        for k, v in bt.items():
            print(f"- {k}: {v:.4f}")
        print("\n## Live Metrics")
        for k, v in live.items():
            print(f"- {k}: {v:.4f}")
        print("\n## Performance Drift")
        for k, v in drift.items():
            if isinstance(v, dict):
                print(f"- {k}: {v}")
        print(f"\n## Distribution Drift: {dist}")
        if signals:
            print("\n## Overfitting Signals")
            for s in signals:
                print(f"- {s}")
        if alert:
            print(f"\n{alert}")
        else:
            print("\nAll clear — no significant drift detected.")

    if args.walk_forward:
        # Run walk-forward on backtest data itself
        data = [
            {"result": t.result, "pnl": t.pnl}
            for t in detector.backtest_trades
        ]
        if data:
            wf = ModelDriftDetector.walk_forward_validation(data)
            print(f"\n## Walk-Forward Validation ({len(wf)} splits)")
            for r in wf:
                print(f"\nSplit {r['split']}:")
                print(f"  Train: {r['train_size']} trades, "
                      f"WR={r['train_metrics']['win_rate']:.2%}")
                print(f"  Test:  {r['test_size']} trades, "
                      f"WR={r['test_metrics']['win_rate']:.2%}")
                print(f"  WR decay: {r['wr_decay_pct']:.1f}%")
        else:
            print("No data for walk-forward validation.")

    if not args.report and not args.walk_forward:
        alert = detector.generate_drift_alert()
        if alert:
            print(alert)
        else:
            print("No significant drift detected.")


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    main()
