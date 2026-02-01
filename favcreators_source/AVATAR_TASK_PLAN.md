# Avatar & Creator QA Plan

## Chunk 1 – helper hygiene
- [x] Identify and remove the duplicate `fetchWithTimeout` / `fetchViaProxy` / `checkLiveStatus` definitions inside `App.tsx`.
- [x] Keep the single module-level versions so TypeScript only sees one declaration.

## Chunk 2 – migration + avatar guarantees
- [x] Rework the follower-migration effect to stop introducing an unused `changed` flag and only rewrite creators that lack follower counts.
- [x] Keep calling `ensureAvatarForCreators` whenever migration actually mutates a creator so no one loses their fallback avatar.

## Chunk 3 – QA + verification
- [x] Run `npm run build` (TS + Vite) to confirm the new helper cleanup and migration code compile cleanly.
- [x] Confirm the existing avatar grabber flow still covers every creator (i.e., no avatar fields were dropped) and document this step in case additional follow-up is required.

