"""ml_battleground.shared.drift_monitor
Concept drift detection using ADWIN on prediction residuals.

Priority: This is the PRIMARY early-warning signal for model degradation.
The feedback_loop.py module serves as the EMERGENCY circuit breaker.

Monitors prediction residuals (predicted_prob - actual_outcome), NOT raw features.
Raw crypto features (RSI, funding, volume) are inherently non-stationary ---
ADWIN on them would fire constantly.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

DRIFT_STATE_DIR = Path(__file__).parent.parent / "drift_state"
COOLDOWN_HOURS = 24  # Min hours between retrains


class DriftMonitor:
    """Lightweight ADWIN-inspired drift detector for prediction residuals.

    Uses a sliding window approach since the ``river`` library may not be installed.
    Detects when the mean of prediction residuals shifts significantly.
    """

    def __init__(self, system_name: str, window_size: int = 50, delta: float = 0.002):
        self.system_name = system_name
        self.window_size = window_size
        self.delta = delta
        self.state_path = DRIFT_STATE_DIR / f"{system_name}_drift.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _load_state(self):
        if self.state_path.exists():
            try:
                state = json.loads(self.state_path.read_text())
                self.residuals = state.get("residuals", [])
                self.last_retrain = state.get("last_retrain")
                self.drift_events = state.get("drift_events", [])
            except (json.JSONDecodeError, OSError):
                self.residuals = []
                self.last_retrain = None
                self.drift_events = []
        else:
            self.residuals = []
            self.last_retrain = None
            self.drift_events = []

    def _save_state(self):
        state = {
            "residuals": self.residuals[-self.window_size * 2 :],  # Keep bounded
            "last_retrain": self.last_retrain,
            "drift_events": self.drift_events[-20:],  # Keep last 20
        }
        self.state_path.write_text(json.dumps(state, indent=2))

    def update(self, predicted_prob: float, actual_outcome: float) -> bool:
        """Add a new observation. Returns True if drift detected.

        Args:
            predicted_prob: Model's predicted probability (0-1)
            actual_outcome: Actual result (1.0 for TP hit, 0.0 for SL/expiry)
        """
        residual = predicted_prob - actual_outcome
        self.residuals.append(residual)

        if len(self.residuals) < self.window_size:
            self._save_state()
            return False

        # Split window in half and compare means (simplified ADWIN)
        mid = len(self.residuals) // 2
        old_window = self.residuals[:mid]
        new_window = self.residuals[mid:]

        old_mean = sum(old_window) / len(old_window)
        new_mean = sum(new_window) / len(new_window)

        # Welch's t-test approximation for drift significance
        old_var = sum((x - old_mean) ** 2 for x in old_window) / max(
            len(old_window) - 1, 1
        )
        new_var = sum((x - new_mean) ** 2 for x in new_window) / max(
            len(new_window) - 1, 1
        )

        se = ((old_var / len(old_window)) + (new_var / len(new_window))) ** 0.5
        if se == 0:
            self._save_state()
            return False

        t_stat = abs(new_mean - old_mean) / se
        drift_detected = t_stat > 2.576  # ~99% confidence

        if drift_detected:
            # Check cooldown
            now = datetime.now(timezone.utc)
            if self.last_retrain:
                try:
                    last = datetime.fromisoformat(self.last_retrain)
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    if (now - last) < timedelta(hours=COOLDOWN_HOURS):
                        self.drift_events.append(
                            {
                                "time": now.isoformat(),
                                "t_stat": round(t_stat, 3),
                                "old_mean": round(old_mean, 4),
                                "new_mean": round(new_mean, 4),
                                "suppressed": True,
                                "reason": "within_cooldown",
                            }
                        )
                        self._save_state()
                        return False
                except ValueError:
                    pass

            self.drift_events.append(
                {
                    "time": now.isoformat(),
                    "t_stat": round(t_stat, 3),
                    "old_mean": round(old_mean, 4),
                    "new_mean": round(new_mean, 4),
                    "suppressed": False,
                }
            )
            self._save_state()
            return True

        self._save_state()
        return False

    def mark_retrained(self):
        """Call after successful retrain to reset cooldown."""
        self.last_retrain = datetime.now(timezone.utc).isoformat()
        self.residuals = []  # Reset after retrain
        self._save_state()

    def get_status(self) -> dict:
        """Return current drift monitor status for dashboard."""
        n = len(self.residuals)
        if n == 0:
            return {"status": "no_data", "samples": 0}
        recent_mean = sum(self.residuals[-min(20, n) :]) / min(20, n)
        return {
            "status": "monitoring",
            "samples": n,
            "recent_residual_mean": round(recent_mean, 4),
            "drift_events_total": len(self.drift_events),
            "last_retrain": self.last_retrain,
        }
