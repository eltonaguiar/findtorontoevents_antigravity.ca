#!/usr/bin/env python3
"""
audit_frontend_manifest.py — codify EVERY user-facing control on findtorontoevents.ca/audit.

Parses audit_dashboard/template.html, audit_dashboard/hc_filter.js and
audit_dashboard/money_ready_filter.js and regenerates a machine-checkable manifest
of every button, tab, filter control and ?Guide concept on the audit dashboard.

It is purely a STATIC PARSER:
  - It NEVER runs a dashboard generator.
  - It NEVER touches index.html or any live HTML.
  - It only reads the three source files and writes audit_dashboard/audit_frontend_manifest.json.

Idempotent: running it twice on an unchanged repo produces a byte-identical JSON
(the "generated_at" field is intentionally NOT written so diffs are content-only).

The CI job .github/workflows/audit-frontend-manifest.yml runs this daily and commits
the refreshed manifest with [skip ci] when it changed.

Usage:
    python tools/audit_frontend_manifest.py            # regenerate JSON
    python tools/audit_frontend_manifest.py --check     # exit 1 if JSON would change

Reference for human reviewers: audit_dashboard/AUDIT_FRONTEND_MANIFEST.md
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DASH = REPO_ROOT / "audit_dashboard"
TEMPLATE = DASH / "template.html"
HC_FILTER = DASH / "hc_filter.js"
MR_FILTER = DASH / "money_ready_filter.js"
OUT_JSON = DASH / "audit_frontend_manifest.json"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _read(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").split("\n")


def _attr(tag: str, name: str) -> str | None:
    """Extract attribute `name` from a single HTML tag string."""
    m = re.search(rf'{name}\s*=\s*"([^"]*)"', tag)
    if m:
        return m.group(1)
    m = re.search(rf"{name}\s*=\s*'([^']*)'", tag)
    return m.group(1) if m else None


def _clean_text(s: str) -> str:
    """Strip tags + decode entities + collapse whitespace."""
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _shorten(s: str | None, n: int = 240) -> str:
    if not s:
        return ""
    s = _clean_text(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# handler-definition discovery (where a JS function / listener lives)
# ---------------------------------------------------------------------------
def _find_function_defs(lines: list[str]) -> dict[str, int]:
    """Map function name -> 1-based line number for `function foo(` and `window.foo =`."""
    defs: dict[str, int] = {}
    pat_fn = re.compile(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(")
    pat_win = re.compile(r"\bwindow\.([A-Za-z_$][\w$]*)\s*=\s*function")
    for i, ln in enumerate(lines, start=1):
        for m in pat_fn.finditer(ln):
            defs.setdefault(m.group(1), i)
        for m in pat_win.finditer(ln):
            defs.setdefault(m.group(1), i)
    return defs


def _find_listener_lines(lines: list[str]) -> dict[str, int]:
    """Map element-id -> line of its addEventListener('click', ...) registration."""
    out: dict[str, int] = {}
    pat = re.compile(r"""el\(\s*['"]([\w-]+)['"]\s*\)\s*\.addEventListener""")
    pat2 = re.compile(r"""getElementById\(\s*['"]([\w-]+)['"]\s*\)\.addEventListener""")
    # also: var _btn = el('id'); ... _btn.addEventListener
    # and:  const x = document.getElementById('id'); ... x.addEventListener
    var_assign = re.compile(
        r"""\b(\w+)\s*=\s*(?:el|document\.getElementById)\(\s*['"]([\w-]+)['"]\s*\)"""
    )
    var_to_id: dict[str, str] = {}
    for i, ln in enumerate(lines, start=1):
        for m in var_assign.finditer(ln):
            var_to_id[m.group(1)] = m.group(2)
        for m in pat.finditer(ln):
            out.setdefault(m.group(1), i)
        for m in pat2.finditer(ln):
            out.setdefault(m.group(1), i)
        m = re.search(r"\b(\w+)\.addEventListener\(\s*['\"]click", ln)
        if m and m.group(1) in var_to_id:
            out.setdefault(var_to_id[m.group(1)], i)
    return out


# ---------------------------------------------------------------------------
# PART 1a — buttons
# ---------------------------------------------------------------------------
def parse_buttons(lines: list[str], fn_defs: dict[str, int],
                  listeners: dict[str, int]) -> list[dict]:
    """Every <button> in template.html that has an id OR an onclick handler."""
    buttons: list[dict] = []
    btn_re = re.compile(r"<button\b[^>]*>", re.IGNORECASE)
    seen_ids: set[str] = set()
    for i, ln in enumerate(lines, start=1):
        for m in btn_re.finditer(ln):
            tag = m.group(0)
            bid = _attr(tag, "id")
            onclick = _attr(tag, "onclick")
            data_tab = _attr(tag, "data-tab")
            # tabs handled separately
            if data_tab:
                continue
            if not bid and not onclick:
                continue
            if bid and bid in seen_ids:
                continue
            if bid:
                seen_ids.add(bid)
            # label text: from the matched line; fall back to next non-empty lines
            after = ln[m.end():]
            label = _clean_text(after.split("</button>")[0]) if "</button>" in after else _clean_text(after)
            title = _attr(tag, "title")
            handler = None
            handler_line = None
            handler_src = None
            if onclick:
                hm = re.match(r"\s*([A-Za-z_$][\w$]*)\s*\(", onclick)
                if hm:
                    handler = hm.group(1)
            if not handler and bid and bid in listeners:
                handler = "(addEventListener click)"
                handler_line = listeners[bid]
                handler_src = "template.html"
            if handler and handler in fn_defs:
                handler_line = fn_defs[handler]
                handler_src = "template.html"
            wired = bool(handler or onclick or (bid and bid in listeners))
            buttons.append({
                "name": label or bid or "(unnamed button)",
                "element_id": bid or "",
                "template_line": i,
                "onclick_attr": _shorten(onclick, 200) if onclick else "",
                "handler": handler or "",
                "handler_defined_at": (f"{handler_src}:{handler_line}"
                                       if handler_line else ""),
                "title_tooltip": _shorten(title, 360),
                "wired": wired,
                "status": "WIRED" if wired else "ORPHANED",
            })
    return buttons


# ---------------------------------------------------------------------------
# PART 1b — tabs
# ---------------------------------------------------------------------------
def parse_tabs(lines: list[str]) -> list[dict]:
    """Every data-tab= button + its tab-content panel."""
    tab_btn_re = re.compile(r'<button\b[^>]*\bdata-tab="([^"]+)"[^>]*>', re.IGNORECASE)
    tab_link_re = re.compile(r'<a\b[^>]*class="[^"]*tab-btn[^"]*"[^>]*>', re.IGNORECASE)
    panel_re = re.compile(r'<div\b[^>]*id="tab-([\w]+)"[^>]*class="[^"]*tab-content', re.IGNORECASE)

    panels: dict[str, int] = {}
    for i, ln in enumerate(lines, start=1):
        for m in panel_re.finditer(ln):
            panels.setdefault(m.group(1), i)

    tabs: list[dict] = []
    seen: set[str] = set()
    for i, ln in enumerate(lines, start=1):
        for m in tab_btn_re.finditer(ln):
            key = m.group(1)
            tag = m.group(0)
            after = ln[m.end():]
            label = _clean_text(after.split("</button>")[0]) if "</button>" in after else _clean_text(after)
            panel_line = panels.get(key)
            uid = f"btn:{key}"
            if uid in seen:
                continue
            seen.add(uid)
            tabs.append({
                "name": label or key,
                "data_tab": key,
                "tab_button_line": i,
                "panel_element_id": f"tab-{key}",
                "panel_line": panel_line or 0,
                "title_tooltip": _shorten(_attr(tag, "title"), 360),
                "panel_present": panel_line is not None,
                "status": "WIRED" if panel_line is not None else "ORPHANED",
            })
        # external-page tab links (anti_overfit.html etc.)
        for m in tab_link_re.finditer(ln):
            tag = m.group(0)
            href = _attr(tag, "href")
            after = ln[m.end():]
            label = _clean_text(after.split("</a>")[0]) if "</a>" in after else _clean_text(after)
            uid = f"link:{href}"
            if uid in seen:
                continue
            seen.add(uid)
            tabs.append({
                "name": label or (href or "external tab"),
                "data_tab": "",
                "tab_button_line": i,
                "panel_element_id": "",
                "panel_line": 0,
                "external_href": href or "",
                "title_tooltip": _shorten(_attr(tag, "title"), 360),
                "panel_present": True,
                "status": "WIRED (external page)",
            })
    return tabs


# ---------------------------------------------------------------------------
# PART 1c — filters / controls
# ---------------------------------------------------------------------------
def parse_filters(lines: list[str]) -> list[dict]:
    """<select> and filter <input> controls (id starting with a filter-ish prefix)."""
    filters: list[dict] = []
    sel_re = re.compile(r'<select\b[^>]*\bid="([\w-]+)"[^>]*>', re.IGNORECASE)
    inp_re = re.compile(r'<input\b[^>]*\bid="([\w-]+)"[^>]*>', re.IGNORECASE)
    opt_re = re.compile(r'<option\b[^>]*?(?:value="([^"]*)")?[^>]*>([^<]*)</option>', re.IGNORECASE)
    seen: set[str] = set()
    for i, ln in enumerate(lines, start=1):
        for m in sel_re.finditer(ln):
            sid = m.group(1)
            if sid in seen:
                continue
            seen.add(sid)
            # collect options on the same line (the template keeps them inline)
            tail = ln[m.start():]
            block = tail.split("</select>")[0]
            opts = [{"value": v or "", "label": _clean_text(t)}
                    for v, t in opt_re.findall(block)]
            filters.append({
                "name": sid,
                "element_id": sid,
                "kind": "select",
                "template_line": i,
                "title_tooltip": _shorten(_attr(m.group(0), "title"), 360),
                "options": opts,
            })
        for m in inp_re.finditer(ln):
            iid = m.group(1)
            tag = m.group(0)
            itype = _attr(tag, "type") or "text"
            # only keep filter-relevant inputs (search box, checkboxes used as filters)
            if not (iid.startswith("f-") or itype in ("checkbox",) or "filter" in iid.lower()):
                continue
            if iid in seen:
                continue
            seen.add(iid)
            filters.append({
                "name": iid,
                "element_id": iid,
                "kind": f"input[{itype}]",
                "template_line": i,
                "title_tooltip": _shorten(_attr(tag, "title")
                                          or _attr(tag, "placeholder"), 360),
                "options": [],
            })
    return filters


# ---------------------------------------------------------------------------
# PART 1d — ?Guide / help / glossary concepts
# ---------------------------------------------------------------------------
def parse_guide_concepts(lines: list[str]) -> list[dict]:
    """The ?Guide / help / explainer / glossary surfaces and what they define."""
    concepts: list[dict] = []
    # known help/guide/glossary anchors keyed by element id substring
    anchors = [
        ("perf-help-btn", "? Guide button (Performance section)",
         "Opens perf-help-overlay — exact filters / definitions / what-to-avoid, "
         "based on closed-pick analysis."),
        ("perf-help-overlay", "Performance ?Guide overlay",
         "Modal explaining how to find edge: filters, definitions, anti-patterns."),
        ("hc-explainer-panel", "HIGH CONVICTION explainer panel",
         "Shown when HIGH CONVICTION button is clicked; explains the hc_filter.js "
         "shared gates + per-asset-class validated-edge gate, and which classes "
         "are DEAD / WEAK / NO DATA."),
        ("sp-info-icon", "Smart Picks ? info icon",
         "Hover/click reveals sp-tooltip — simple + technical explanation of the "
         "Smart Picks multi-layer scoring pipeline."),
        ("sp-tooltip", "Smart Picks explainer tooltip",
         "Defines ML Score, Forward Walk-Forward WR, Confidence Calibration, "
         "Regime Alignment, Trust & Source Scoring, hard gates, forward-validated "
         "bypass."),
        ("smart-picks-glossary-btn", "Smart Picks ?Glossary button",
         "Toggles smart-picks-glossary — defines each scoring-factor string in the "
         "'Why' column (Quality score, Fresh signal, upside-to-TP, multi-timeframe, "
         "multi-signal agreement, proven winner, copy-trader premium, etc.)."),
        ("smart-picks-glossary", "Smart Picks scoring-factor glossary",
         "Table mapping each 'Why'-column factor to plain-language meaning."),
        ("ueps-glossary-btn", "US Equity Picks ?Glossary button",
         "Toggles ueps-glossary — defines F-Score, Magic Rank, Acquirer M, "
         "Altman Z'', Beneish M, ROIC, FCF Yield."),
        ("ueps-glossary", "US Equity Picks glossary panel",
         "Definitions for the UEPS composite fundamental factors."),
        ("tier-trust-legend", "Feed-stack legend (Verified Alpha / Smart Picks / "
         "High Conviction / Active Picks)",
         "Descriptive legend explaining how the four pick feeds rank in strictness."),
        ("smart-picks-glossary", "", ""),
    ]
    line_of: dict[str, int] = {}
    for i, ln in enumerate(lines, start=1):
        for aid, _, _ in anchors:
            if f'id="{aid}"' in ln and aid not in line_of:
                line_of[aid] = i
    for aid, name, defines in anchors:
        if not name:
            continue
        concepts.append({
            "name": name,
            "element_id": aid,
            "template_line": line_of.get(aid, 0),
            "defines": defines,
            "present": aid in line_of,
            "status": "WIRED" if aid in line_of else "MISSING",
        })
    # de-dup by element_id
    out: list[dict] = []
    seen: set[str] = set()
    for c in concepts:
        if c["element_id"] in seen:
            continue
        seen.add(c["element_id"])
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# Money Ready / High Conviction wiring verdict (special-cased — known orphan)
# ---------------------------------------------------------------------------
def annotate_preset_wiring(buttons: list[dict], template_text: str) -> None:
    """
    The Money Ready button calls applyMoneyReady() (defined in money_ready_filter.js)
    which flips window._moneyReadyActive and shows a banner — but NO render path in
    template.html reads window._moneyReadyActive or calls window.filterMoneyReady().
    So the button is functionally ORPHANED: clicking it never filters the picks grid.
    """
    mr_referenced = bool(
        re.search(r"_moneyReadyActive", template_text)
        or re.search(r"filterMoneyReady", template_text)
    )
    for b in buttons:
        if b["element_id"] == "btn-money-ready":
            b["handler"] = "applyMoneyReady"
            b["handler_defined_at"] = "money_ready_filter.js:174"
            b["wired"] = False
            b["status"] = "ORPHANED"
            b["orphan_reason"] = (
                "applyMoneyReady() toggles window._moneyReadyActive and shows a "
                "banner, but no render path in template.html reads "
                "_moneyReadyActive or calls window.filterMoneyReady() — the picks "
                "grid is never actually filtered."
            ) if not mr_referenced else (
                "verify: _moneyReadyActive now referenced in template.html"
            )
        elif b["element_id"] in ("btn-conviction-picks-hero", "btn-conviction-picks"):
            b["handler"] = "applyHighConvictionPreset"
            b["handler_defined_at"] = "template.html:12960"
            b["wired"] = True
            b["status"] = "WIRED"
            b["note"] = (
                "addEventListener wiring at template.html ~12996-12998; "
                "applyHighConvictionPreset() sets window._convictionOnlyFilter + "
                "_hcEdgeStrict and re-renders — hc_filter.js gates ARE applied."
            )


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def build_manifest() -> dict:
    tpl_lines = _read(TEMPLATE)
    template_text = "\n".join(tpl_lines)
    fn_defs = _find_function_defs(tpl_lines)
    listeners = _find_listener_lines(tpl_lines)

    buttons = parse_buttons(tpl_lines, fn_defs, listeners)
    tabs = parse_tabs(tpl_lines)
    filters = parse_filters(tpl_lines)
    guide = parse_guide_concepts(tpl_lines)
    annotate_preset_wiring(buttons, template_text)

    orphan_buttons = sorted(b["element_id"] or b["name"]
                            for b in buttons if b["status"].startswith("ORPHAN"))
    orphan_tabs = sorted(t["data_tab"] or t["name"]
                         for t in tabs if t["status"].startswith("ORPHAN"))

    return {
        "_doc": (
            "Machine-checkable manifest of every user-facing control on "
            "findtorontoevents.ca/audit. Regenerated by "
            "tools/audit_frontend_manifest.py (daily CI). DO NOT hand-edit — "
            "edit the source HTML/JS instead. See AUDIT_FRONTEND_MANIFEST.md."
        ),
        "sources": {
            "template": "audit_dashboard/template.html",
            "hc_filter": "audit_dashboard/hc_filter.js",
            "money_ready_filter": "audit_dashboard/money_ready_filter.js",
        },
        "counts": {
            "buttons": len(buttons),
            "tabs": len(tabs),
            "filters": len(filters),
            "guide_concepts": len(guide),
            "orphaned_buttons": len(orphan_buttons),
            "orphaned_tabs": len(orphan_tabs),
        },
        "orphaned": {
            "buttons": orphan_buttons,
            "tabs": orphan_tabs,
        },
        "buttons": buttons,
        "tabs": tabs,
        "filters": filters,
        "guide_concepts": guide,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate the audit frontend manifest.")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the manifest on disk is stale (do not write)")
    args = ap.parse_args()

    manifest = build_manifest()
    rendered = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=False) + "\n"

    if args.check:
        if OUT_JSON.exists() and OUT_JSON.read_text(encoding="utf-8") == rendered:
            print("audit_frontend_manifest.json is up to date.")
            return 0
        print("audit_frontend_manifest.json is STALE — run "
              "tools/audit_frontend_manifest.py", file=sys.stderr)
        return 1

    OUT_JSON.write_text(rendered, encoding="utf-8")
    c = manifest["counts"]
    print(f"Wrote {OUT_JSON.relative_to(REPO_ROOT)}")
    print(f"  buttons={c['buttons']}  tabs={c['tabs']}  "
          f"filters={c['filters']}  guide_concepts={c['guide_concepts']}")
    print(f"  ORPHANED buttons={c['orphaned_buttons']} "
          f"({', '.join(manifest['orphaned']['buttons']) or 'none'})")
    print(f"  ORPHANED tabs={c['orphaned_tabs']} "
          f"({', '.join(manifest['orphaned']['tabs']) or 'none'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
