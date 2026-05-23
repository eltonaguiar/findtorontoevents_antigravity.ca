# HyroTrader — $5,000 **2-step** challenge (reference table)

**Source:** HyroTrader / community summary — **confirm** every row on your purchase agreement and in-app **Challenge rules** before trading.

| Rule | Phase 1 | Phase 2 | Funded |
|------|---------|---------|--------|
| **Profit target** | **10% ($500)** | **5% ($250)** | — |
| **Max daily loss** | **5% ($250)** | **5% ($250)** | **5%** |
| **Max overall loss** | **10% ($500)** | **10% ($500)** | **10%** |
| **Min trading days** | **10** | **10** | — |
| **Time limit** | Unlimited | Unlimited | Indefinite |
| **Profit split** | — | — | **70% → 90%** (over ~16 mo, per Hyro) |

---

## Key rules to watch

1. **Tick-by-tick trailing drawdown** — The loss floor can move up on **new equity highs**, including **unrealized** P&amp;L. A spike that reverses can consume room fast.
2. **Stop-loss mandatory** — Typically required **within minutes of entry** (often cited as **5 minutes**). **Max risk per trade** is often **3% of account** → **$150 on a $5K** account. **Second breach** of key rules may **fail** the eval — verify exact wording.
3. **~40% “consistency” rule** — No single day may exceed **~40%** of **total evaluation profit** toward the phase target. Illustration: Phase 1 target **$500** → cap ~**$200** profit in one day; Phase 2 target **$250** → cap ~**$100**/day. **Verify** the precise formula on Hyro.
4. **Fees** — Example: **$89** challenge fee, **refunded** on first funded payout (confirm current policy).

---

## Implications for $5K

- **Daily budget:** **$250** max daily loss — one sloppy session can end the day.
- **Overall budget:** **$500** max trail — two very bad days can end the eval.
- **Hard risk cap:** **$150** per trade (3%) is the **ceiling**; many traders use **less** (e.g. **0.75% = $37.50**) to survive trailing DD.

---

## Repo tools

| Tool | Location |
|------|----------|
| Tracker + calculators | [findtorontoevents.ca/audit/hyrotrader/](https://findtorontoevents.ca/audit/hyrotrader/) |
| Picks + challenge JSON | `audit_dashboard/data/hyrotrader_picks.json` |
| Trade journal (you edit) | `audit_dashboard/data/hyrotrader_journal.json` |
| Playbook | [`HYROTRADER_CHALLENGE_STRATEGY.md`](./HYROTRADER_CHALLENGE_STRATEGY.md) |
| Sizes / formula | [`HYROTRADER_POSITION_SIZES.md`](./HYROTRADER_POSITION_SIZES.md) |

---

*Not financial advice. Rules change — Hyro’s contract and UI win over this file.*
