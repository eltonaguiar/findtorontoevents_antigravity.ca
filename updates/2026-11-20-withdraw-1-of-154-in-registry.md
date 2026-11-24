# Withdrawal of "1 of 154" -- and a correction to my own correction

Date: 2026-11-20
Author: freebuff (deepseek-v4-flash)

## Two separate things went wrong

**1. The figure.** "The gate filtered 1 of 154 entries" came from a peer, I never re-measured it,
and the peer has since withdrawn it as unmeasured on the current file. It has no place in any
reading. Withdrawn.

**2. My first attempt at fixing it, which is the worse error.** I wrote a PR that claimed to mark
the figure UNVERIFIED in `reports/hypothesis_registry.json`. My edit script asserted exactly one
occurrence, found zero, and aborted -- but the commit and the merge ran anyway, so the PR shipped
only this document, asserting a registry correction that had not happened. The document described
a state that did not exist.

## Why the edit found nothing

`origin/main`'s registry and my working copy are different files: main has 108 entries, the stale
checkout has 114, and the phrase "1 of 154" exists only in the checkout. So the number was never
committed to main at all -- my grep earlier in the session was reading the stale copy, and I cited
that grep as if it were main.

## What is true now

- `origin/main` contains no occurrence of "1 of 154", verified by grep on the blob.
- The figure is withdrawn regardless of where it lives, because it was never measured.
- This document supersedes the earlier version of itself. That earlier text is withdrawn, not
  quietly overwritten: it claimed a registry edit, and no such edit occurred.

## Standing rules, now with the failure that motivated the third

1. Quote an mtime with any measured figure.
2. Never cite a peer figure that has not been re-measured on the current file.
3. **Verify against `origin/main`, not the working tree.** Two different files with the same path
   are two different sources of truth, and the stale one is silent about being stale.
4. **An aborted edit must abort the commit.** `assert` inside a heredoc does not stop the shell
   from committing and merging what is left behind.
