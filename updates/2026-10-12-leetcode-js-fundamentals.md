# LeetCode-style JavaScript fundamentals: quiz category + cheat sheet (2026-10-12)

## What was asked for

Coding-interview building blocks that had no home on the site: string methods
(`str.at()` and friends), the JS data structures (`Set`, `Map`) **and when to
use each**, and the frequency-count idiom `list[chr] = (list[chr] || 0) + 1`.

Delivered in two places, because a quiz question can test a building block but
cannot explain *when to choose it*:

## 1. New quiz category — "JavaScript for Interviews"

Added to `findtorontoevents.ca/servicenow/javascript/quiz-data.js` as
`jsfundamentals`, deliberately **independent of the seven ServiceNow categories**
(so it can be practised alone, per the rule that categories stay standalone).

| Subcategory | Covers |
|---|---|
| String methods | `.at(-1)`, `s[i]`, `.slice()`, `.split('')`, `[...s]` vs emoji, `.includes()`, `.replace()` vs `.replaceAll()`, `.padStart()`, counting via `match(/g/)` |
| Set / Map / Object | `[...new Set()]` dedup, `set.has()` for O(1) membership, `map.size`, missing-key → `undefined`, **the `Object.keys(map)` trap**, why Map beats `{}`, `for...in` vs `for...of` |
| Counting idioms | `count[c] = (count[c] \|\| 0) + 1`, the `NaN` reason, the Map form with `??`, `Object.create(null)` for prototype safety, `Math.max(...arr)`, `new Array(26).fill(0)` |

**22 questions.** Bank total is now **87 across 8 categories**.

## 2. New page — `js-interview.html`

A cheat sheet, same visual language as the quiz, linked from the quiz nav +
footnote and from the guide nav as "Interview JS". Four sections:

1. **String building blocks** — need / use / gotcha table, plus the emoji trap
   called out separately (`'😀'.split('').length` is 2, `[...'😀'].length` is 1).
2. **Set, Map or plain object** — a when-to-use comparison, then the two `{}`
   traps that actually fail tests: prototype collisions (`count['constructor']`
   reads a function, not `undefined`) and `for...in` walking inherited
   *enumerable* keys.
3. **The frequency-count idiom** — both the object and Map forms, why the
   `|| 0` is not optional, and a related-idioms table (bucket arrays,
   `charCodeAt(0) - 97`, two-sum lookup, `[...countMap].sort()`).
4. **Which building block each medium pattern needs** — frequency map, Set
   membership, two pointers, sliding window, stack, prefix sum, memoisation.

## Verification — and one thing this caught that documentation could not

Unlike the ServiceNow snippets, plain JavaScript can actually be **executed**,
so every claim was run in Node 22 rather than quoted:

- **37/37 behavioural assertions pass** (`VERIFY_EXIT=0`) — `.at()` negatives,
  the emoji surrogate split, `replace` vs `replaceAll`, Set dedup order,
  `Object.keys(map)` returning `[]`, the prototype trap, `undefined + 1` being
  `NaN`, `new Array(26)` sparsity vs `.fill(0)`, and so on.
- The code sample **printed on the page** was extracted and executed directly:
  `SNIPPET_EXIT=0`.
- Ten further claims quoted verbatim in the tables were re-run inline: 10/10.

**Two real defects were found and fixed this way:**

1. **A wrong claim in the quiz.** The `js-02` hint asserted "`at()` returns null
   instead" of `undefined` when out of range. Executing it showed `at()` returns
   **`undefined`** — exactly like bracket access. The distinction is negative
   indexing, not the out-of-range value. Hint corrected.
2. **A broken code sample on the cheat sheet.** The first version declared
   `const count` **twice** in one block (object form, then Map form), so
   copy-pasting the whole block threw `SyntaxError: Identifier 'count' has
   already been declared`. Renamed the Map variable to `countMap` and updated
   the table that referenced it.

A third failure (`for...in` "inherited keys") was **my test being wrong, not the
claim** — `Object.prototype`'s built-ins are non-enumerable so they don't show.
The test now adds an enumerable inherited property to prove the behaviour, and
the page wording says "inherited *enumerable*" precisely.

## Also verified

- **Data integrity:** 87 questions, 0 problems (no duplicate ids, every cat/sub
  resolves, every `answer` in its own `accept` list). `node --check` clean.
- **Browser (Playwright), local *and* live:** quiz **36/36** (`QUIZ_EXIT=0`,
  `LIVE_QUIZ_EXIT=0`) — including the new category opening with 22 questions,
  the frequency idiom and `.at(-1)` accepted, and the `Object.keys(map)` trap
  rejected. Cheat sheet **6/6** (`JI_EXIT=0`, `LIVE_JI_EXIT=0`) — 4 sections,
  tables rendering with rows, no horizontal overflow, no stray unescaped
  entities, **0 console errors**.
- **Guide still clean** after the nav addition: 0 tag mismatches, 53/53 TOC
  anchors, 0 console errors.
- **Deployed** with remote backups; all four files byte-identical to live:
  `quiz-data.js` 44,043 · `quiz.html` 24,305 · `index.html` 390,294 ·
  `js-interview.html` 17,173 bytes.

## Limitations

- The cheat-sheet table rows are behavioural claims about the JavaScript
  language, all executed under **Node 22**. Browser engines agree on these
  (`String.prototype.at` is ES2022, `replaceAll` ES2020, `??` ES2020), but the
  verification itself was Node, not a browser.
- The "which building block each pattern needs" table is pedagogical
  guidance, not benchmarked advice.
