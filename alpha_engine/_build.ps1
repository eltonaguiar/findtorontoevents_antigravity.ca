.Add("import json, logging, io, zipfile")
.Add("from pathlib import Path")
.Add("try:")
.Add("    HAS_YFINANCE = True")
.Add("    HAS_YFINANCE = False")
.Add("try:")
.Add("    HAS_REQUESTS = True")
.Add("    HAS_REQUESTS = False")
.Add("logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')")
.Add("")
.Add("DATA_DIR    = BASE_DIR / 'data'")
.Add("DATA_DIR.mkdir(parents=True, exist_ok=True)")
Write-Host "Lines added: .Count)"
Write-Host "Test OK"