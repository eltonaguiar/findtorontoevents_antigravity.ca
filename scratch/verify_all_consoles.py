#!/usr/bin/env python3
"""Query Best Buy's availability API for every console SKU we can name.

First-party status per SKU: InStock / InStockOnlineOnly / SoldOutOnline.
No keyword scraping -- a page saying "add to cart" tells you nothing about
which product the button belongs to.
"""
import json
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

SKUS = {
    "19422130": "Xbox Series S 512GB",
    "19422127": "Xbox Series S 1TB",
    "20189840": "Xbox Series X 1TB",
    "19422129": "Xbox Series X 1TB Digital",
    "20105824": "Xbox Series X 2TB Galaxy",
    "19446111": "PS5 Slim 1TB",
    "19446112": "PS5 Slim Digital 825GB",
    "19609594": "PS5 Disc Slim",
    "19492009": "PS5 Pro",
    "18477929": "PS5 Pro (alt SKU)",
    "19970410": "PS5 Slim refurb",
    "19827353": "PS5 open-box BO6",
}

url = ("https://www.bestbuy.ca/ecomm-api/availability/products"
       "?accept=application%2Fvnd.bestbuy.standardproduct.v1%2Bjson"
       "&accept-language=en-CA"
       f"&skus={','.join(SKUS)}&postalCode=M5B2H1")

req = urllib.request.Request(url, headers={
    "User-Agent": UA,
    "Accept": "application/vnd.bestbuy.standardproduct.v1+json",
})
with urllib.request.urlopen(req, timeout=40) as r:
    data = json.load(r)

avail = data.get("availabilities") or []
print(f"{len(avail)} SKUs returned\n")
rows = []
for a in avail:
    sku = a.get("sku")
    sh = a.get("shipping") or {}
    pk = a.get("pickup") or {}
    rows.append((SKUS.get(sku, "?"), sku, sh.get("status"), sh.get("quantityRemaining"),
                 pk.get("status")))

# buyable first, then name
rows.sort(key=lambda x: (x[2] not in ("InStock", "InStockOnlineOnly"), x[0]))
for name, sku, status, qty, pickup in rows:
    mark = {"InStock": "OK ", "InStockOnlineOnly": "OK*", "SoldOutOnline": "X  "}.get(status, "?  ")
    print(f"{mark} {name:<26} {sku:<10} {str(status):<18} qty={qty:<6} pickup={pickup}")
