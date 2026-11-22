# In-store / pickup availability hunt — NEW Xbox Series + PS5, Toronto & GTA

**Date:** 2026-11-20
**Target repo:** https://github.com/eltonaguiar/GTA5TORONTOTRACKER
**Working clone:** `/tmp/gta5tracker` (already at `86a762a`, pushed)

## What the user asked for

1. Extensive search for **in-store / pickup-available NEW** consoles — Xbox Series and PlayStation, **top-quality latest models** — starting downtown Toronto, expanding to the GTA.
2. Only if that fails, cover **used** listings.
3. In the GitHub README: NEW/in-store findings in the main verified section; **used listings at the very bottom, behind a warning**, with a **last-updated date/time in EST (UTC−5)**.

## The lead that reframes this

The user reported Walmart showing **free pickup today at Stockyards** for the Xbox Series S All-Digital 512GB:

`https://www.walmart.ca/en/ip/XBOX-Series-S-All-Digital-Gaming-Console-512GB-SSD-Includes-XBOX-Wireless-Controller-120FPS-Robot-White/7IY33NVWJOKP?selectedSellerId=0`

Stockyards (1980 St Clair Ave W) is Toronto but **not downtown core** — roughly 7 km west. If it verifies, it belongs in the in-store section with the store named exactly as the retailer names it, and a note that it is GTA-adjacent rather than downtown.

**This is a lead from the user, not evidence.** It must be independently verified before it is published. Screenshot-of-a-lead is not a stock check.

## Non-negotiable verification rules

These are the rules that stopped me publishing false positives last round. They carry over:

1. **A page containing "add to cart" is not a stock check.** Best Buy's PS5 Slim Disc page showed both "add to cart" and "sold out" simultaneously; the button belonged to accessories. Never infer assembly from keyword presence.
2. **`shipping.status` is not `pickup.status`.** Best Buy returned `NotAvailable` for pickup on every console while shipping showed `InStock`. In-store means pickup, so pickup is the only field that counts.
3. **Never hand-type a store address.** Take the store name and address from the retailer's own response (DOM text or API field). Hand-typed addresses are how the earlier README ended up listing chain names with no store identity.
4. **One SKU per request on Best Buy's availability API.** The `skus` parameter grammar is `^[A-Za-z\d]\d{5,7}(([|][A-Za-z\d]\d{5,7})|(;[A-Za-z\d]{5,8})){0,200}$` — separators are `|` or `;`, **not commas**. Batched comma queries return 412, which looks like rate limiting and isn't.
5. **Bots-blocked ≠ out of stock.** Every "unknown" gets its own row in the UNVERIFIED table with the reason and the URL for a human to check. Never promote an unknown into either table.
6. **Timestamp every row.** Each row carries the moment *it* was observed, not the publish time. A table with one global timestamp implies uniform freshness that we do not have.
7. **A marketplace seller at ~2× MSRP is not "in stock".** The Best Buy PS5 at $1699.99 was a third-party scalper listing. It goes in a clearly-labelled marketplace note, not the verified table.
8. **Take deliverable status from the filesystem** — `git show origin/main:README.md | head`, not from intent or a subagent's summary. This has burned me twice.

## Source matrix — ordered by reliability

### Tier A — structured, first-party, machine-readable

| Source | Method | What it yields | Notes |
|---|---|---|---|
| Best Buy CA | `https://www.bestbuy.ca/ecomm-api/availability/products?accept=application%2Fvnd.bestbuy.standardproduct.v1%2Bjson&accept-language=en-CA&skus=<SKU>&postalCode=<FSA>` | `shipping.status`, `shipping.quantityRemaining`, `pickup.status` | Already probed. **Pickup was `NotAvailable` for all consoles** as of 2026-11-20 21:46Z. Re-probe with several downtown FSAs (M5B, M5G, M5V, M4Y, M5H) because pickup eligibility is postal-code dependent. |

### Tier B — retailer DOM with a per-store availability widget (needs a real browser)

All of these bot-wall plain HTTP but render fine in the CDP-attached Chrome. Read the store table from the DOM, never from a keyword regex over `innerText`.

| Source | Where the stock lives | Downtown / GTA stores worth reading |
|---|---|---|
| **Walmart.ca** | Product page → "Pickup" / "Delivery" tabs. Store list is client-rendered. Also try `https://www.walmart.ca/en/ip/<id>` with the store cookie set. | Stockyards (1980 St Clair W) — **the reported lead**. Plus Dufferin Mall, Queen & Portland, Square One, Scarborough Town Centre, Vaughan Mills. |
| **Canada Computers** | Product page "In Store Availability" table, per-store qty. | College St (downtown), North York, Markham, Richmond Hill, Scarborough, Mississauga, Vaughan, Ajax. |
| **GameStop / EB Games Canada** | Product page store inventory checker. | Eaton Centre, Yonge & Dundas area, Dufferin Mall, Yorkdale, Scarborough Town Centre. |
| **Staples Canada** | Product page → store availability. | Downtown (Bay & College area), plus GTA. |
| **Toys R Us Canada** | Product page → "Check store availability". | Eaton Centre / Yonge, Vaughan Mills, Scarborough. |
| **Costco Canada** | Warehouse stock is app-gated; web shows online only. | Treat as **manual-check** unless the app-level endpoint is found. |
| **Microsoft Store** | Online only, no physical stock check. | Contributes to the online table, not in-store. |
| **The Source** | Most stores closed. | Skip unless a live locator exists. |

### Tier C — manual-verification bucket (name + phone + URL, explicitly flagged)

Local independents that carry new or used consoles but publish no inventory feed. These go in a **PHONE TO CONFIRM** sub-table, never in the verified table:

- Invictus Game Station — Yonge St 2nd Floor, M4Y 1Z1 — `https://invictusgamestation.com/` (already in PLAY NOW; also ask about console sales)
- Gamerama — 2470 Yonge St, M4P 2H5 — 416-487-8802
- A&C Games — Toronto
- Game Centre — Toronto
- Buy & Sell Kings — 2852 Danforth Ave, M4C 1M1 — 647-348-1763
- Queen East Appliance Centre — 1180 Queen St E, M4M 1L4 — 416-463-6551

Addresses above are **carried from the prior README / user input** and are flagged as *not re-verified this round* unless a store's own site confirms them.

### Tier D — used listings (only if Tier A/B produce no downtown in-store hit)

| Source | Method | Caveat |
|---|---|---|
| Kijiji Toronto | DOM search, `xbox series x`, `ps5`, filter `Toronto (GTA)` | Private sellers; no stock notion; prices vary wildly |
| Craigslist Toronto | Plain HTML, easy to parse | Low volume for consoles |
| GameStop pre-owned | DOM, filter condition | Chain-backed, returnable — the only used source with a warranty |
| Facebook Marketplace | Login-walled | **Manual check only** — cannot be automated honestly |

## README structure after this round

```
# GTA5 Toronto Console Tracker
(last updated line — EST, explicit UTC offset)

## Table of contents

## 🟢 AVAILABLE IN STORE / PICKUP TODAY — NEW
   (the section the user actually wants; per-row timestamp + store name from retailer)

## 🔵 AVAILABLE ONLINE — NEW (delivery)
   (Best Buy availability API + any retailer that ships)

## 🟡 PHONE TO CONFIRM — local shops with no inventory feed
   (name, address as published by the shop, phone, URL, "not verified this round")

## 🟠 UNVERIFIED / BOT-BLOCKED
   (source, URL, reason, what a human should do)

## PLAY NOW — internet cafes, Downtown Toronto only
   (unchanged in intent)

## ⚠️ USED LISTINGS — BUYER BEWARE
   > WARNING block: private sales, no warranty, verify serial + test before paying,
   > meet in public, no e-transfer deposits.
   (this section is LAST among the data sections)

## Notes / methodology
## Scrape findings (pointer to FINDINGS.md)
```

The used section is **last**, behind a warning block, with its own timestamp — exactly as asked.

## Durability

`stock-monitor.yml` regenerates `README.md` and previously wiped my hand-written sections. Two mitigations, both already learned:

1. Keep the narrative and reasoning in `FINDINGS.md`; keep only the changing numbers in generated tables.
2. After any push, verify with `git show origin/main:README.md | head -40` — do not trust the local file.

## Execution phases

### Phase 0 — Re-probe the lead (highest value, cheapest)
- Drive the Walmart product page over CDP on port 9222, open Pickup, read the store list for Stockyards.
- Record store name, address, pickup date window, price, and observation timestamp.
- If it is genuinely pickup-available, this becomes the headline row.

### Phase 1 — Tier A sweep
- Best Buy availability API, one SKU per request, for downtown FSAs M5B/M5G/M5V/M4Y/M5H.
- Extract `pickup.status` specifically; discard `shipping.status` for the in-store table.

### Phase 2 — Tier B sweep over CDP
- Canada Computers first (server-rendered per-store table, most likely to have real downtown qty).
- Then GameStop/EB, Staples, Toys R Us.
- Each store row captured as `(retailer, product, store name, address, qty|status, observed_at)`.

### Phase 3 — Assemble the tables
- Split into in-store / online / phone-to-confirm / unverified.
- Every row timestamped individually.

### Phase 4 — Used listings (only if Phase 1–2 yield no downtown in-store NEW hit)
- Kijiji + Craigslist + GameStop pre-owned via DOM.
- Facebook Marketplace listed as manual-check with URL.

### Phase 5 — Publish
- Rewrite README to the structure above, used section last behind the warning.
- `git add README.md FINDINGS.md`, commit, push to `eltonaguiar/GTA5TORONTOTRACKER`.
- Verify from the remote, not the working tree.

## Acceptance criteria

- [ ] The Walmart Stockyards lead is either verified with a store-level citation, or explicitly recorded as unverified with the reason.
- [ ] Every row in the in-store table cites a retailer-returned store name/address and its own observation timestamp.
- [ ] No row in the in-store table is derived from a keyword match or from `shipping.status`.
- [ ] Bot-walled sources appear in the UNVERIFIED table with a URL, not silently dropped.
- [ ] Used listings appear only at the bottom, behind a warning block, with a timestamp.
- [ ] The last-updated line states EST / UTC−5 explicitly.
- [ ] `git show origin/main:README.md` confirms the published content.

## What this plan refuses

- Claiming a downtown in-store hit without a retailer-reported store-level signal.
- Treating a search-results marker count as stock.
- Counting Walmart's uniformly-false `isOutOfStock` flags or Microsoft's boilerplate "in stock" strings.
- Presenting a marketplace scalper listing as availability.
- Filling the in-store table with "call them" entries and calling that a search.
