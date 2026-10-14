# Interview page: section 5 — eleven iconic problems reduced to reusable concepts (2026-10-14)

## What was asked

Update our interview problems with the **key building blocks** — particularly
the **reusable concepts** — for a pasted set of canonical LeetCode-style
JavaScript solutions: Two Sum, Longest Substring Without Repeating Characters,
3Sum, Invert Binary Tree, Validate Binary Search Tree, Number of Islands,
Course Schedule, LRU Cache, House Robber, Coin Change, and Best Time to Buy
and Sell Stock.

## What changed — `findtorontoevents.ca/servicenow/javascript/js-interview.html`

**New section 5, "Iconic problems → the one reusable concept each drills"**
(20,085 → 34,843 bytes, 238 → 457 lines), organised around the *concept*, not
the problem:

1. A **summary table** — 11 problems, the reusable concept each teaches, and
   which earlier section it builds on (so the page stays one system instead of
   a list of snippets).
2. **Five groups**, each ending in a "transferable bits" box that says what
   carries over to other problems:
   - **5.1 Arrays & strings** — Two Sum (complement lookup, check-before-insert),
     Best Time to Buy and Sell Stock (running aggregate), Longest Substring
     (shrink-until-valid window — `while`, not `if`), 3Sum (sort → fix one →
     two pointers, skip duplicates at all three positions).
   - **5.2 Trees** — Invert (the four-line recursion template + destructuring
     swap), Validate BST (thread a `(min, max)` range down instead of comparing
     to the immediate parent).
   - **5.3 Graphs** — Number of Islands (flood fill; the input grid *is* the
     visited set), Course Schedule (0/1/2 colour DFS cycle detection).
   - **5.4 Design** — LRU Cache (JS `Map` insertion order *is* recency order;
     delete+re-insert = move-to-most-recent, first key = oldest — no linked
     list needed in JS).
   - **5.5 Dynamic programming** — House Robber (rolling variables when
     `dp[i]` depends on two cells), Coin Change (bottom-up table with an
     `Infinity` "impossible" sentinel resolved once, after the loop).
3. A closing "how to use this in a real interview" notice: **name the concept
   out loud before you code** — the specific problem is just the concept in
   costume.

**Section 4** ("Which building block each medium pattern needs") gained three
rows it was missing: graph flood fill, cycle detection → valid order, and
rolling DP vs DP table (7 → 10 pattern rows). The page **lede** now advertises
the eleven iconic problems too.

No other page (`quiz.html`, `js-essentials.html`, `index.html`) needed edits —
they already link to `js-interview.html`, and the section lives under the
existing "Interview JS" nav entry.

## Verification — the same discipline as the 2026-10-12 work

Every code block on the page is extracted from the HTML itself (decoding the
entities), syntax-checked individually, executed, then asserted — so the
*rendered page* is what was tested, not a private copy.

- **`node /tmp/verify_iconic.js` → EXIT=0**: 12/12 blocks parse, **58/58
  behavioural assertions pass** — two-sum cases (incl. no-solution `[]`),
  `dvdf`/`abba` window cases that fail with `if` instead of `while`, 3Sum
  uniqueness and duplicate-skipping, tree mirrors, BST counterexample
  `[5,4,6,null,null,3,7]`, island counts (1/3/0/0/1), course-schedule cycles,
  full LRU lifecycle (both eviction and `get()`-moves-to-recent), `rob`,
  `coinChange` (incl. amount 0 and unreachable `-1`), `maxProfit`.
- **Structure**: h2 = 5, `iconic-` h3 = 5, `<pre><code>` = 12, pattern-table
  rows = 10, tag balance clean, **0 raw `&` and 0 raw `<` anywhere** outside
  HTML entities.
- **Playwright — new `tests/js-interview-iconic.spec.ts`, 1/1 passed**
  (`PW_EXIT=0`): section 5 + all five group headings visible, 12 code blocks,
  each of the 11 functions present exactly once, summary table = 11 rows,
  pattern table = 10 rows, entities render as real characters in the DOM,
  no horizontal page overflow, **0 console errors**. Registered in
  `playwright.config.ts` `testMatch` (the allowlist — a spec not listed there
  is silently "No tests found").

## Four traps this caught (worth remembering)

1. **Escaped markup kept arriving raw.** Round-tripping `<` and `&&` through
   the edit pipeline stripped their encoding, so the first pass left raw
   markup inside the code blocks and prose. A Python scan for characters
   that are not valid entity starts found **5 occurrences** (3 in prose, 2 in
   inline `<code>`); all fixed by building the escape sequences programmatically
   instead of typing them, then re-scanning: **0 raw, 0 raw `<`**.
2. **`import.meta.url` breaks Playwright specs in this repo.** `package.json`
   is `"type": "commonjs"`, so a spec using `import.meta` fails at load with
   *"require is not defined in ES module scope"* and reports "No tests found".
   The spec now resolves the page from `process.cwd()`. (The older
   `tests/servicenow_js_es6_overflow.spec.ts` has the same latent problem and
   is also missing from `testMatch` — not touched here, just noted.)
3. **The published frequency-count block is a fragment.** It reads an input
   named `s` that the page never defines, so executing the page's code blocks
   as-is throws `s is not defined`. The verifier now supplies a sample input;
   the block itself is correct as teaching material.
4. **A prose claim needed proof, not trust.** The section says comparing each
   node to its *immediate parent* is the classic wrong answer. The verifier
   implements that wrong rule and asserts it **accepts**
   `[5,4,6,null,null,3,7]` while `isValidBST` rejects it — first run failed
   because my "wrong" helper was itself wrong (it compared right-children with
   the left-child rule); fixed the helper, and the claim now has executable
   evidence.

## Files touched

| File | Change |
|---|---|
| `findtorontoevents.ca/servicenow/javascript/js-interview.html` | section 5 added, 3 pattern rows, lede |
| `tests/js-interview-iconic.spec.ts` | new — browser verification of section 5 |
| `playwright.config.ts` | +1 line: register the spec in `testMatch` |
| `updates/2026-10-14-js-interview-iconic-problems.md` | this file |

## Limitations

- Behavioural assertions ran under **Node 22**; browser rendering under
  Chromium via Playwright. The ES6 version stars in the prose follow the
  page's existing convention and were not re-derived here.
- The page is updated **locally only** — not FTP-deployed, so live
  `findtorontoevents.ca/servicenow/javascript/js-interview.html` still serves
  the 20,085-byte version until a deploy is run.
