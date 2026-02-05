# Real Avatar Validation Plan

## Chunk 1 – Avatar sync sanity
- [x] Refactored the avatar-pass effect to rely on `creatorsRef` and run once on mount (plus a 10-minute interval) so we don’t rerun the worker every time state changes while still checking every creator for Dicebear fallbacks.

## Chunk 2 – Signal the results
- [x] Added a computed `realAvatarCount` and rendered the “Real avatars fetched: X of Y” badge beneath the header, along with minor styling tweaks so the team can see how many creators now have non-Dicebear images.

## Chunk 3 – Validation snapshot
- [x] `npm run lint` still fails because of the pre-existing hook/dependency warnings and unused variables in `src/api/proxy.ts`, `src/components/CreatorCard.tsx`, `src/utils/avatarFetcher.ts`, and `src/utils/googleSearch.ts`; the new avatar work leaves those issues untouched.
