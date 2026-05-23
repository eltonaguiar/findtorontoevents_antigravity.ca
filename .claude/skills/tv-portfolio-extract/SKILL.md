---
name: tv-portfolio-extract
description: Extract the FULL dataset of a TradingView paper portfolio — open positions, working orders, order history, balance history, and the trading journal — by scraping all five Paper Trading tabs. Use before any portfolio review/audit. Aliases - tv-extract, tv-portfolio-dump, portfolio-extract, tv-scrape-portfolio.
---

# tv-portfolio-extract — dump every tab of a TV paper portfolio

> **MCP server:** [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) — the `mcp__tradingview-desktop__*` tool family.

Scrapes all five Paper Trading tabs for one account into structured JSON.
Feeds `/tv-portfolio-review`. For driving the JS reliably use `/tv-eval-bridge`
(MCP tool direct, or base64). Account switching: `/tv-account-switch`.

## The five tabs

The Paper Trading panel has a tab strip:
`Positions · Orders · Order history · Balance history · Trading journal`.

Each tab renders its own table. The plan: switch to the target account, then
for each tab — click the tab header, wait, scrape the table.

## Step 1 — switch + verify account

Per `/tv-account-switch`. **Verify the account name** before scraping — wrong
account = wrong data. Record the verified name.

## Step 2 — per-tab scrape

For each of the five tab labels, click the tab then read the table. Generic
scraper — captures the header row + every data row as cell-text arrays, so it
works regardless of which columns a given tab shows:

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(TAB){
  // click the tab header by exact text
  var tabEl=[].slice.call(document.querySelectorAll('*')).find(function(e){
    return !e.children.length && e.textContent.trim()===TAB;});
  if(tabEl){var t=tabEl;for(var i=0;i<4;i++){try{t.click();}catch(e){}t=t.parentElement;if(!t)break;}}
  // scrape the visible table
  var rows=document.querySelectorAll('table tr'), out=[], hdr=null;
  for(var r=0;r<rows.length;r++){
    var cells=rows[r].querySelectorAll('th,td');
    if(!cells.length)continue;
    var vals=[].slice.call(cells).map(function(c){return c.textContent.trim();});
    if(vals.some(function(v){return v;})){
      if(!hdr && rows[r].querySelector('th')){hdr=vals;}
      else out.push(vals);
    }
  }
  return JSON.stringify({tab:TAB,header:hdr,rows:out,n:out.length});
})('TAB_LABEL')`)
```

Run it 5×, substituting `TAB_LABEL` = `Positions`, `Orders`,
`Order history`, `Balance history`, `Trading journal`. Put a short wait
between the click and the scrape if a tab lazy-loads.

**Positions tab** also expose via the dedicated reader (`/tv-positions-read`)
if you need the symbol-regex-filtered, TP/SL-audited form — but the generic
scraper above is fine for a full dump.

## Step 2.5 — closed trades (the "Order history" trap)

**Verified 2026-05-16:** clicking the "Order history" tab via a broad text
search frequently surfaces the **open-positions table again** (same columns,
an `Unrealized PnL` column) — NOT the realized closed-trade list. Same class
of bug as the History-tab shadowing in `/tv-debug`. So a naive scrape of
"Order history" gives you positions, not closures.

To get realized closes (e.g. everything since a date):

1. **Confirm which table you scraped.** If the rows carry `Unrealized PnL`
   and match the Positions tab, you got positions — not history. A real
   closed-trade row has a close time + realized PnL, no "unrealized".
2. **Apply the panel's own filter.** Inside Order history look for a
   date-range control or a "Closed" / "Filled" sub-toggle and set it before
   scraping. The bottom-bar may also expose a separate `History` tab with its
   own count badge — scrape that, not the button that re-renders Positions.
3. **CSV export is the reliable path.** TV's account menu (the ⚙/⋯ near the
   account name) has an export — it dumps the complete realized P/L. For a
   full multi-week closure history, export the CSV and parse it; do not fight
   the DOM.
4. **The audit ledger is the cross-check.** `audit_dashboard/data/dashboard_data.json::picks.recent_closed`
   already holds realized outcomes with `source_system` labels — many of the
   FOREX/equity closes are there. Use it to corroborate TV's closed list.

Record in the dump which method produced `order_history` /
`closed_trades` so the reviewer knows whether it is real closures or a
positions-shadow.

## Step 3 — write the dump

Write one JSON file per portfolio under
`reports/tv_portfolio_<ACCOUNT>_<UTCDATE>/dump.json`:

```json
{
  "account": "HYROTRADER",
  "extracted_utc": "2026-05-...",
  "positions":      {"header": [...], "rows": [[...], ...]},
  "orders":         {"header": [...], "rows": [...]},
  "order_history":  {"header": [...], "rows": [...]},
  "balance_history":{"header": [...], "rows": [...]},
  "trading_journal":{"header": [...], "rows": [...]}
}
```

Also capture the account summary strip (Account balance, Equity, Realized PnL,
Unrealized PnL, Account margin, Available funds) — it sits above the tabs:

```javascript
mcp__tradingview-desktop__ui_evaluate(expression=`(function(){
  var labels=['Account balance','Equity','Realized PnL','Unrealized PnL',
              'Account margin','Available funds','Margin buffer'];
  var o={};
  labels.forEach(function(l){
    var le=[].slice.call(document.querySelectorAll('*')).find(function(e){
      return !e.children.length && e.textContent.trim()===l;});
    if(le){var sib=le.parentElement;o[l]=(sib?sib.textContent.replace(l,'').trim():'');}
  });
  return JSON.stringify(o);
})()`)
```

## Step 4 — all portfolios

To sweep every book: loop the account list (`THEWINNERS`, `SCALPER`,
`TESTER`, `TRUSTOURSCORE`, `BROKIE`, `zerounderscore`, `HYROTRADER`, … — read
the dropdown for the live set), running Steps 1-3 per account. One dump file
per portfolio.

## Failure modes

| Failure | Fix |
|---|---|
| tab click does nothing | walk up the ancestor chain clicking (the scraper does this); or click by `data-name` if present |
| `ui eval` quoting error | use `/tv-eval-bridge` (base64) |
| History/Journal tab empty | genuinely no rows yet, OR tab lazy-loads — wait then re-scrape |
| wrong account's data | account not verified — redo Step 1 |

## Companion skills

- `/tv-portfolio-review` — analyze the dump (pick-source classification, close candidates, lessons)
- `/tv-account-switch` · `/tv-positions-read` · `/tv-eval-bridge`
