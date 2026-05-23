"""Model versioning with shadow testing and auto-rollback.

Flow:
1. Trainer saves new model as model_candidate.joblib
2. Validation gates check DSR/PSR
3. If passes: enter shadow mode (run both old + new for 30 picks)
4. After 30 shadow picks: compare metrics, swap if new >= old
5. If new underperforms: auto-rollback to previous version

Files:
  model.joblib          -- production model
  model_previous.joblib -- rollback target
  model_candidate.joblib -- new model under evaluation
  shadow_state.json     -- tracks shadow testing progress
"""
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone

log = logging.getLogger("model_versioning")

SHADOW_PICKS_REQUIRED = 30
WR_TOLERANCE = 0.05  # New model WR must be >= old WR - 5%


class ModelVersionManager:
    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self.shadow_path = self.model_dir / "shadow_state.json"

    def promote_candidate(self, model_name: str = "model") -> bool:
        """Move candidate to production, keeping previous as rollback.
        Returns True if promotion happened.
        """
        candidate = self.model_dir / f"{model_name}_candidate.joblib"
        production = self.model_dir / f"{model_name}.joblib"
        previous = self.model_dir / f"{model_name}_previous.joblib"

        if not candidate.exists():
            log.warning(f"No candidate found at {candidate}")
            return False

        # Backup current production as previous
        if production.exists():
            shutil.copy2(production, previous)

        # Promote candidate
        shutil.move(str(candidate), str(production))
        log.info(f"Promoted {model_name}_candidate -> {model_name} (previous backed up)")
        return True

    def start_shadow(self, model_name: str = "model"):
        """Begin shadow testing period."""
        state = {
            "model_name": model_name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "production_picks": [],
            "candidate_picks": [],
            "status": "active",
        }
        self.shadow_path.write_text(json.dumps(state, indent=2))
        log.info(f"Shadow testing started for {model_name}")

    def record_shadow_pick(self, is_candidate: bool, pick_result: dict):
        """Record a pick from either production or candidate model."""
        if not self.shadow_path.exists():
            return
        state = json.loads(self.shadow_path.read_text())
        key = "candidate_picks" if is_candidate else "production_picks"
        state[key].append(pick_result)
        self.shadow_path.write_text(json.dumps(state, indent=2))

    def evaluate_shadow(self, model_name: str = "model") -> dict:
        """Check if shadow testing is complete and evaluate.
        Returns {"action": "promote"|"rollback"|"continue", "reason": str}
        """
        if not self.shadow_path.exists():
            return {"action": "continue", "reason": "no shadow state"}

        state = json.loads(self.shadow_path.read_text())
        prod_picks = state.get("production_picks", [])
        cand_picks = state.get("candidate_picks", [])

        if len(cand_picks) < SHADOW_PICKS_REQUIRED:
            return {
                "action": "continue",
                "reason": f"{len(cand_picks)}/{SHADOW_PICKS_REQUIRED} shadow picks collected",
            }

        # Calculate WR for both
        prod_wr = sum(1 for p in prod_picks if p.get("pnl", 0) > 0) / max(len(prod_picks), 1)
        cand_wr = sum(1 for p in cand_picks if p.get("pnl", 0) > 0) / max(len(cand_picks), 1)

        if cand_wr >= prod_wr - WR_TOLERANCE:
            self.promote_candidate(model_name)
            self.shadow_path.unlink(missing_ok=True)
            return {
                "action": "promote",
                "reason": f"Candidate WR {cand_wr:.1%} >= Production WR {prod_wr:.1%} - {WR_TOLERANCE:.0%}",
            }
        else:
            # Rollback -- discard candidate
            self.shadow_path.unlink(missing_ok=True)
            candidate = self.model_dir / f"{model_name}_candidate.joblib"
            candidate.unlink(missing_ok=True)
            return {
                "action": "rollback",
                "reason": f"Candidate WR {cand_wr:.1%} < Production WR {prod_wr:.1%} - {WR_TOLERANCE:.0%}",
            }

    def auto_rollback(self, model_name: str = "model") -> bool:
        """Emergency rollback to previous model version."""
        production = self.model_dir / f"{model_name}.joblib"
        previous = self.model_dir / f"{model_name}_previous.joblib"

        if not previous.exists():
            log.warning("No previous model to rollback to")
            return False

        shutil.copy2(previous, production)
        log.info(f"Auto-rollback: restored {model_name}_previous -> {model_name}")
        return True
