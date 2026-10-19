import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PHP = os.environ.get("PHP_BINARY") or shutil.which("php")


def test_version_one_wrapper_uses_php52_compatible_directory_lookup():
    source = (ROOT / "TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS/index.php").read_text()
    assert "__DIR__" not in source, "PHP 5.2 treats __DIR__ as a literal, triggering the MS2 redirect"
    assert "dirname(__FILE__)" in source


def test_version_one_wrapper_serves_its_own_html(tmp_path):
    wrapper = ROOT / "TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS/index.php"
    shutil.copyfile(wrapper, tmp_path / "index.php")
    (tmp_path / "index.html").write_text("<html><body>Version one content</body></html>")
    result = subprocess.run(
        [PHP, "-n", str(tmp_path / "index.php")],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert "Version one content" in result.stdout
    assert '<script src="ms1-upgrade-toast.js' in result.stdout
    assert result.stderr == ""
