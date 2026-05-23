# HyroTrader Syntax Fix (2026-04-11)

## Issue

Public page error:

- `hyrotrader/:657 Uncaught SyntaxError: Unexpected identifier 'escHtml'`

## Root Cause

The inline JavaScript row builder in `audit_dashboard/hyrotrader/index.html` had a broken string concatenation.

Broken form:

```js
"<tr" + rowClass + "><td class=\"mono\">"
escHtml(x.sym) +
```

Fixed form:

```js
"<tr" + rowClass + "><td class=\"mono\">" + escHtml(x.sym) +
```

## Local Fix State

The repo file is corrected at:

- `audit_dashboard/hyrotrader/index.html` line ~656

## Important Note

If the public site still throws the error, then the fix exists locally but the updated `audit_dashboard/hyrotrader/index.html` has not been redeployed yet.
