"""Strategy Registry — watches incoming/ and merges into master JSON."""

import json
import logging
from pathlib import Path

from strategy_registry.envelope_schema import validate_envelope

log = logging.getLogger("StrategyRegistry")


class StrategyRegistry:
    def __init__(
        self,
        incoming_dir: Path = Path("incoming_strategies"),
        failed_dir: Path = Path("failed_strategies"),
        master_path: Path = Path("battleground/data/tiered_backtest_results_master.json"),
    ):
        self.incoming_dir = Path(incoming_dir)
        self.failed_dir = Path(failed_dir)
        self.master_path = Path(master_path)

    def _load_master(self) -> dict:
        if self.master_path.exists():
            return json.loads(self.master_path.read_text())
        return {"strategies": {}, "updated_at": ""}

    def _save_master(self, data: dict) -> None:
        from datetime import datetime, timezone
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.master_path.parent.mkdir(parents=True, exist_ok=True)
        self.master_path.write_text(json.dumps(data, indent=2))

    def process_one(self, file_path: Path) -> bool:
        """Process a single envelope file. Returns True if successful."""
        try:
            envelope = json.loads(file_path.read_text())
        except Exception as e:
            log.error("Cannot parse %s: %s", file_path.name, e)
            file_path.rename(self.failed_dir / file_path.name)
            return False

        ok, errors = validate_envelope(envelope)
        if not ok:
            log.error("Validation failed for %s: %s", file_path.name, errors)
            file_path.rename(self.failed_dir / file_path.name)
            return False

        master = self._load_master()
        sid = envelope["strategy_id"]
        master["strategies"][sid] = {
            "name": envelope["name"],
            "type": envelope["type"],
            "source_system": envelope["source_system"],
            "backtest_results": envelope.get("backtest_results", {}),
            "tags": envelope.get("tags", {}),
            "parameters": envelope.get("parameters", {}),
            "generated_at": envelope["generated_at"],
        }
        self._save_master(master)
        log.info("Integrated strategy: %s (%s)", sid, envelope["type"])
        file_path.unlink()
        return True

    def process_all(self) -> int:
        """Process all envelopes in the incoming directory. Returns count of successful."""
        count = 0
        for fp in sorted(self.incoming_dir.glob("*.json")):
            if self.process_one(fp):
                count += 1
        return count
