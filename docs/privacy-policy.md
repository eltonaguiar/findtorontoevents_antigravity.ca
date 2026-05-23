# Privacy Policy — FindTorontoEvents / Antigravity Financial Prediction Platform

**Effective date:** 2026-05-16  
**Last updated:** 2026-05-16  
**Applies to:** findtorontoevents.ca, tdotevent.ca, torontoevent.net, and the Antigravity algorithmic-trading audit dashboard at `/audit`.

---

## 1. Who We Are

Findtorontoevents.ca (operated by Elton Aguiar, Toronto, Canada) runs two distinct product surfaces:

1. **Events listing** — a public directory of Toronto events (concerts, sports, film, etc.).
2. **Antigravity financial prediction platform** — an algorithmic trading signal system that tracks and grades live pick performance across asset classes (CRYPTO, EQUITY, COMMODITY, BOND, ETF, FOREX).

This policy covers both surfaces. Where a section is specific to one, it is labelled accordingly.

---

## 2. Information We Collect

### 2.1 Automatically Collected (all visitors)
| Data | Purpose | Retention |
|------|---------|-----------|
| IP address (anonymised last octet) | Rate-limiting; abuse prevention | 30 days |
| Browser user-agent | Dashboard compatibility | 30 days |
| Pages visited, referrer | Aggregate traffic analytics | 90 days |
| Session timestamp | System health monitoring | 30 days |

We do **not** use third-party tracking pixels, Facebook Pixel, or Google Ads tracking.

### 2.2 Financial Platform (`/audit` dashboard)
The audit dashboard is **read-only and unauthenticated**. It displays aggregated backtested and forward-tested trading signal performance. No personal financial data is collected from visitors.

Internally, the platform stores:
- **Trade signal records** in MySQL — ticker symbol, entry/exit prices, timestamps, strategy name, outcome. No personally identifiable information (PII) is attached to trade records.
- **API keys** (Binance, CoinGecko, etc.) stored as GitHub Actions Secrets and environment variables — never logged or transmitted to third parties.

### 2.3 Events Listing
- No account registration is required to browse events.
- If you contact us via email, we store your email address solely to reply and delete it within 90 days of resolution.

---

## 3. How We Use Your Information

- **Service delivery** — render the events grid, the audit dashboard, and live pick feeds.
- **Security** — detect and block automated abuse; rate-limit excessive API calls.
- **Performance** — aggregate page-load metrics to prioritise optimisation work.
- **No sale or sharing** — we do not sell, rent, or share your data with advertisers or data brokers.

---

## 4. Cookies

We use **no advertising cookies** and **no cross-site tracking cookies**.

| Cookie | Purpose | Lifespan |
|--------|---------|----------|
| `theme` (localStorage) | Remembers light/dark mode preference | Until cleared |
| `filter_state` (sessionStorage) | Retains active dashboard filter between page reloads | Session |

These are functional-only cookies. You may clear them at any time via your browser settings without losing access to any feature.

---

## 5. Data Retention

| Category | Retention |
|----------|-----------|
| Trade signal records (MySQL) | Indefinite — historical performance data is the core product |
| Server access logs (anonymised) | 90 days, then auto-deleted |
| Email correspondence | 90 days after resolution |
| GitHub Actions logs | 30 days (GitHub default) |

---

## 6. Third-Party Services

| Service | Purpose | Their Privacy Policy |
|---------|---------|---------------------|
| GitHub (Microsoft) | Code hosting, CI/CD, Actions | https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement |
| Binance / CoinGecko / KuCoin / CryptoCompare | Market price data (server-side only) | Per respective provider |
| 50webs.com / GoDaddy | Web hosting | Per respective provider |
| Discord | Notification webhooks | https://discord.com/privacy |

We do not embed Google Analytics, Meta Pixel, or any advertising network.

---

## 7. Financial Disclaimer

The Antigravity audit dashboard provides **algorithmic signal performance data for informational purposes only**. It is **not** investment advice. Past signal performance does not guarantee future results. Users are solely responsible for any trading decisions made based on information displayed on this platform.

We are **not** a registered investment adviser, broker-dealer, or financial institution under Canadian, US, or any other jurisdiction's securities law.

---

## 8. Your Rights (PIPEDA / GDPR)

Under Canada's PIPEDA and, where applicable, the EU General Data Protection Regulation (GDPR):

- **Access** — you may request a copy of any personal data we hold about you.
- **Correction** — you may request correction of inaccurate data.
- **Deletion** — you may request deletion of your personal data (server log entries and any email correspondence).
- **Portability** — we will provide data in machine-readable format on request.
- **Opt-out** — there are no marketing communications to opt out of; we do not send newsletters or promotional emails.

To exercise any right, email: **zerounderscore@gmail.com** with subject line `Privacy Request`. We will respond within 30 days.

---

## 9. Children's Privacy

This platform is not directed at children under 13 (COPPA) or under 16 (GDPR Article 8). We do not knowingly collect data from minors. If you believe a minor has submitted personal data, contact us and we will delete it promptly.

---

## 10. Security

- All data in transit is protected by TLS 1.2+.
- MySQL credentials are stored as encrypted GitHub Secrets; they are never committed to the repository.
- API keys follow a 90-day rotation reminder policy (see `docs/DB_ROTATION_RUNBOOK_2026-05-13.md`).
- No credit card or payment data is collected or stored.

---

## 11. Changes to This Policy

We will update this document as our data practices change. The "Last updated" date at the top of this page will reflect the most recent revision. Material changes will be noted in `updates/index.html`.

---

## 12. Contact

**Elton Aguiar**  
Email: zerounderscore@gmail.com  
Platform: findtorontoevents.ca  
Toronto, Ontario, Canada
