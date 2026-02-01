---
description: [How to test the application locally]
---

### 🚀 Local Testing Workflow

1.  **Ensure Server is Running**:
    - Port: `3333`
    - Command: `npx http-server -p 3333`
2.  **Access URL**:
    - **Primary URL**: [http://localhost:3333](http://localhost:3333)
3.  **Run Playwright Tests**:
    - Command: `npx playwright test events-loading.spec.ts`
4.  **Important Notes**:
    - Port `3333` is a "safe" port and won't trigger standard browser blocks.
    - If events don't load, verify that the Fetch Interceptor in `index.html` is redirecting to `/next/events.json`.
    - Hydration errors (Error #418) are usually caused by inconsistent version strings in `index.html` script tags.
