import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SWARM_DIR = REPO_ROOT / "tools" / "swarm"
sys.path.insert(0, str(SWARM_DIR))


class SwarmToolingTests(unittest.TestCase):
    def test_load_dotenv_overrides_empty_env(self):
        from config_loader import load_dotenv

        old_xai = os.environ.get("X_AI_KEY")
        old_other = os.environ.get("OTHER_KEY")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                env_file = Path(tmp) / ".env"
                env_file.write_text("X_AI_KEY=real-key\nOTHER_KEY=kept\n", encoding="utf-8")

                os.environ["X_AI_KEY"] = "   "
                os.environ["OTHER_KEY"] = "already-set"

                applied = load_dotenv(env_file)

                self.assertEqual(os.environ["X_AI_KEY"], "real-key")
                self.assertEqual(os.environ["OTHER_KEY"], "already-set")
                self.assertEqual(applied, {"X_AI_KEY": "real-key"})
        finally:
            if old_xai is None:
                os.environ.pop("X_AI_KEY", None)
            else:
                os.environ["X_AI_KEY"] = old_xai
            if old_other is None:
                os.environ.pop("OTHER_KEY", None)
            else:
                os.environ["OTHER_KEY"] = old_other

    def test_copilot_prompt_preserves_metacharacters(self):
        import worker_runner

        captured = {}

        def fake_run(cmd, stdin_data=None, timeout=600, env=None):
            captured["cmd"] = cmd
            return 0, "ok", ""

        prompt = (
            'Return JSON: {"engine_status":"substantive|limited|failed", '
            '"rule":"PF > 1.5 and WR < 50%"}\n- keep bullets'
        )

        with mock.patch.object(worker_runner, "_resolve_copilot_cli", return_value=["copilot.exe"]):
            with mock.patch.object(worker_runner, "_run", side_effect=fake_run):
                out, sid, meta = worker_runner.call_copilot(prompt, argparse.Namespace())

        self.assertEqual(out, "ok")
        self.assertEqual(sid, "")
        self.assertEqual(meta["transport_status"], "ok")
        self.assertEqual(captured["cmd"][0], "copilot.exe")
        self.assertEqual(captured["cmd"][2], prompt)
        self.assertIn("substantive|limited|failed", captured["cmd"][2])
        self.assertIn("PF > 1.5", captured["cmd"][2])
        self.assertIn("WR < 50%", captured["cmd"][2])
        self.assertIn("\n- keep bullets", captured["cmd"][2])


if __name__ == "__main__":
    unittest.main()
