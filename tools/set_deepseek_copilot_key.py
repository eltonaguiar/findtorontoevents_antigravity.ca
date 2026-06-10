#!/usr/bin/env python3
"""Configure DeepSeek for GitHub Copilot Chat on gx10 remote (Copilot only)."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

HOME = Path.home()
DBPASSES = HOME / "dbpasses.txt"
VSCODE_DATA = HOME / ".vscode-server/data"
USER_SETTINGS = VSCODE_DATA / "User/settings.json"
MACHINE_SETTINGS = VSCODE_DATA / "Machine/settings.json"
USER_LM = VSCODE_DATA / "User/chatLanguageModels.json"
MACHINE_LM = VSCODE_DATA / "Machine/chatLanguageModels.json"
STATE_DB = VSCODE_DATA / "User/globalStorage/state.vscdb"
SECRET_KEY = "secret://Vizards.deepseek-v4-for-copilot/deepseek-copilot.apiKey"


def read_deepseek_key() -> str:
    lines = DBPASSES.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "DEEPSEEK_API" and i + 1 < len(lines):
            key = lines[i + 1].strip()
            if key.startswith("sk-"):
                return key
    raise SystemExit("DEEPSEEK_API missing in ~/dbpasses.txt")


def merge_setting(path: Path, api_key: str) -> None:
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data["deepseek-copilot.apiKey"] = api_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent="\t") + "\n", encoding="utf-8")
    print(f"wrote {path}")


def write_secret_store(api_key: str) -> None:
    if not STATE_DB.exists():
        print(f"skip secret db (missing {STATE_DB})")
        return
    conn = sqlite3.connect(STATE_DB)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
            (SECRET_KEY, api_key),
        )
        conn.commit()
        print(f"wrote SecretStorage key for Vizards.deepseek-v4-for-copilot")
    finally:
        conn.close()


def patch_vizards_auth_fallback() -> None:
    """Vizards reads SecretStorage only; add ~/dbpasses.txt fallback for gx10 remote."""
    auth_js = HOME / ".vscode-server/extensions/vizards.deepseek-v4-for-copilot-0.6.0/out/auth.js"
    if not auth_js.exists():
        print("skip auth patch (extension not installed)")
        return
    text = auth_js.read_text(encoding="utf-8")
    if "dbpasses-fallback" in text:
        print("auth patch already applied")
        return
    old = """        if (settingsKey?.trim()) {
            return settingsKey.trim();
        }
        return undefined;
    }
    /**
     * Store API key in SecretStorage.
     */"""
    new = """        if (settingsKey?.trim()) {
            return settingsKey.trim();
        }
        const dbKey = await this._readDbpassesKey();
        if (dbKey) {
            return dbKey;
        }
        return undefined;
    }
    async _readDbpassesKey() {
        try {
            const fs = require('fs');
            const path = require('path');
            const db = path.join(process.env.HOME || '', 'dbpasses.txt');
            const lines = fs.readFileSync(db, 'utf8').split(/\\r?\\n/);
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].trim() === 'DEEPSEEK_API' && lines[i + 1] && lines[i + 1].startsWith('sk-')) {
                    return lines[i + 1].trim();
                }
            }
        }
        catch { }
        return undefined;
    }
    /**
     * Store API key in SecretStorage.
     */"""
    if old not in text:
        print("skip auth patch (unexpected auth.js shape)")
        return
    auth_js.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {auth_js}")


def main() -> int:
    key = read_deepseek_key()
    merge_setting(USER_SETTINGS, key)
    merge_setting(MACHINE_SETTINGS, key)
    write_secret_store(key)
    patch_vizards_auth_fallback()
    print("DeepSeek Copilot key configured on gx10 remote.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())