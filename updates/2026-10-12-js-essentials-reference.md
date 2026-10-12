# JavaScript Essentials reference + coverage enforcement (2026-10-12)

## The rule being enforced

> *If a method is not written down in the essentials reference, no example on this
> site is allowed to use it.*

That was the constraint in the request, and it is now **machine-checked** rather
than promised. `js-essentials.html` is the documented inventory;
`js-interview.html` is checked against it, both locally and against the
deployed files.

## New page — `js-essentials.html`

Ten sections, 12 tables, 15 code blocks (7 reference + 8 runnable patterns):

| # | Section | Covers |
|---|---|---|
| 1 | **Strings** | `length`, `s[i]`, `at`, `charAt`, `charCodeAt`/`codePointAt`, `slice`/`substring`, `concat`, `trim*`, case, `includes`/`indexOf`/`startsWith`/`endsWith`, `search`/`match`/`matchAll`, `replace`/`replaceAll`, `split`, `repeat`, `padStart`/`padEnd`, `fromCodePoint`, `for...of` |
| 2 | **Arrays** | creation (`new Array(n)` sparsity, `Array.of`, `Array.from`, `isArray`), read/search (`at`, `indexOf`, `includes`, `find`/`findIndex`, `flat`/`flatMap`), test/transform (`map`/`filter`/`reduce`/`forEach`/`every`/`some`), mutate (`push`/`pop`/`shift`/`unshift`/`splice`/`fill`/`concat`), order (`reverse`, `sort`, ES2023 `toSorted`/`toReversed`/`toSpliced`), iteration |
| 3 | **Objects** | literal, computed keys, shorthand methods, `Object.keys`/`values`/`entries`/`fromEntries`/`assign`/`freeze`/`seal`/`create`/`hasOwn`, iteration, full destructuring (defaults, rename, nested, rest) |
| 4 | **Numbers & Math** | `parseInt` radix, `parseFloat`, `Number`, `isInteger`/`isFinite`/`isNaN`, `toFixed`, `floor`/`ceil`/`round`/`trunc`/`abs`/`sign`, `max`/`min`, `pow`/`**`/`sqrt`, `random`, `BigInt`, radix `toString`, float-equality |
| 5 | **Functions & scope** | declaration/expression/arrow, default + rest params, hoisting & TDZ, `this` and `call`/`apply`/`bind`, closures, memoisation, recursion depth, higher-order, generators |
| 6 | **ES6+ syntax** | 21 features with version and the gotcha each: `let`/`const` binding vs contents, template literals, destructuring, spread/rest, shorthand & computed keys, arrows, `for...of`, classes, modules, iterators, `Symbol`, `**`, `Object.entries`, `async`/`await`, `?.`, `??`, `replaceAll`, `at`, `Object.hasOwn`, non-mutating array methods, logical assignment |
| 7 | **Collections** | `Set` / `Map` / `{}` / `WeakMap`/`WeakSet` — when to reach for each, key API, and the trap |
| 8 | **Async** | `Promise` states, `then`/`catch`/`finally`, `Promise.all` vs `allSettled`, `async`/`await` with `try`/`catch`, and the "await in a loop is serial" note |
| 9 | **Key logic patterns** | 8 runnable solutions: two pointers, sliding window, frequency map, binary search, stack, Kadane, sort-by-comparator top-K, BFS |
| 10 | **Gotchas that fail tests** | 14-row wrong/right table |

Linked from the quiz nav + footnote and from the interview page's nav + footer.

## Verification — snippets executed, not quoted

- **Parse:** all 15 code blocks through `node --check` — **0 failures**.
- **Behaviour:** the 8 pattern functions extracted and run against 26 assertions
  covering the classic LeetCode cases — **26/26 pass**. Includes
  `longestUnique('abcabcbb') === 3`, `maxSubArray([-2,1,-3,4,-1,2,1,-5,4]) === 6`,
  `groupAnagrams` on the standard 6-word input, `lowerBound` edge cases
  (empty array, absent target, past end), `validParens` on `'{'`, `topK` mode
  selection, and BFS depth.
- **UI (Playwright), local *and* live:** essentials **8/8** (`ESSENTIALS_UI_EXIT=0`,
  `LIVE_ESSENTIALS_EXIT=0`) — 10 sections, 10 TOC entries, 0 broken anchors,
  12 tables all populated, no horizontal overflow, 15 code blocks, every TOC
  target resolves to a real `h2[id]`, **0 console errors**. Interview page
  **6/6** live; quiz **36/36** after the nav change.

## The coverage rule, checked both ways

Extracting every method call and `<code>` token used on the interview page and
diffing against the essentials inventory:

- **32 methods used, 0 undocumented** — `ESSENTIALS_VERIFY_EXIT=0`.
- Re-run against the **live-served HTML** rather than the working tree:
  **32 methods, 0 undocumented**.

So the rule holds on the deployed site, not just locally.

## Defects found and fixed

1. **The destructuring block declared `a` twice** (`const { a, b = 2 }` then
   `const { a, ...rest }`), so copying the block threw
   `SyntaxError: Identifier 'a' has already been declared`. Renamed the second
   to `d` and made the whole block self-consistent — same class of bug as the
   duplicated `const count` fixed on the interview page earlier today.

Three test failures were **my assertions being wrong, not the page**:

- I expected `longestUnique('😀😀ab')` to be 3, but the snippet indexes by code
  unit and correctly returns **4**. Rather than change the code to fit the
  test, the page now says so explicitly under that snippet — the sliding-window
  example is code-unit based, matching how the JS judge treats strings.
- `topK` returns **numbers** (`[1,2]`), not the `["1","2"]` I asserted.
- Two UI expectations (14 tables, 8 code blocks) were simply miscounts — the
  real figures are 12 and 15.

## Deployed

Five files, all byte-identical to local after upload, with remote backups
(`*.bak-20261012-quiz`): `js-essentials.html` 40,053 · `js-interview.html`
17,444 · `quiz.html` 24,456 · `quiz-data.js` 44,043 · `index.html` 390,294.

## Limitations

- Snippets and behavioural claims were executed under **Node 22**. The features
  used span ES2015–ES2023, so engines agree, but the run itself was Node rather
  than a browser.
- The coverage check is textual: it proves every method *name* used on the
  interview page appears in an essentials table. It cannot prove the surrounding
  prose describes it correctly — that is what the executed assertions cover.
