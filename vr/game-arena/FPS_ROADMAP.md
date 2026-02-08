# FPS Arena Roadmap — v1 / v2 / v3

## Current State: FPS Arena v1

**Engine:** Three.js r128, single HTML file (~5,600 lines, ~235KB)
**Rendering:** WebGL 1.0 via Three.js, `<canvas>` element
**Physics:** Custom AABB box collision, gravity/jump
**Characters:** Primitive geometry (boxes, cylinders) — no skeletal animation
**Audio:** Web Audio API procedural synthesis — no recorded samples
**Multiplayer:** Socket.io (client-side, server optional)
**Map:** Flat arena with box-geometry structures

### What v1 Has
- 6 weapons with different stats
- AI bot system with state machine (patrol/chase/combat/retreat/flank)
- HUD: health, armor, ammo, kill feed, minimap, rank system
- Weapon viewmodel (2D canvas-rendered)
- ADS, crouch, sprint, slide, grenades
- Dynamic crosshair, floating damage numbers
- Voice announcer (Web Speech Synthesis)
- Settings menu, weapon customization
- Multiplayer lobby + Socket.io server

### Why v1 Feels "Primitive"
1. **No real 3D models** — characters are geometric shapes, not rigged meshes
2. **No skeletal animation** — bots don't walk/run/shoot/reload visually
3. **No textures on structures** — flat colors on box geometry
4. **Old Three.js** — r128 is from 2021, missing modern rendering features
5. **No physics engine** — custom AABB only, no real collision response
6. **No skybox** — just fog and a dark background box
7. **No post-processing** — no bloom, SSAO, motion blur, color grading

---

## Benchmarks: What Browser FPS Games Look Like

### Tier 1: Three.js (our current tier)
- [three-arena](https://github.com/felixgren/three-arena) — Socket.io multiplayer, octree collisions
- [three-fps](https://github.com/mohsenheydari/three-fps) — Ammo.js physics, entity/component, pathfinding AI
- **Ceiling:** Good gameplay feel but limited visuals. No skeletal animation without GLTF loader.

### Tier 2: Full Game Engine (PlayCanvas / Babylon.js)
- [Venge.io](https://venge.io) — PlayCanvas engine, skeletal animations, console-quality feel
- [Fields of Fury](https://fieldsoffury.io) — PlayCanvas, WW2 theme, excellent particles/textures
- **Ceiling:** Near-console quality. Skeletal animation, physics, proper asset pipeline. Requires engine migration.

### Tier 3: Compiled Native Engine (WASM)
- [BananaBread](https://kripken.github.io/misc-js-benchmarks/banana/game.html) — Cube 2 / Sauerbraten compiled via Emscripten
- [QuakeJS](https://www.quakejs.com) — Quake 3 Arena compiled to JS/WASM
- **Ceiling:** Native FPS feel. BSP maps, proper physics, real netcode. Requires compiling a C/C++ engine to WASM.

### Tier 4: Next-Gen (WebGPU)
- [Project Prismatic](https://www.crazygames.com) — WebGPU renderer, AAA-quality lighting
- **Ceiling:** Near-desktop quality rendering. Requires WebGPU (Chrome 113+, not yet in Firefox/Safari).

---

## FPS Arena v2 — "The Polish Update"

**Goal:** Maximum improvement within Three.js, single HTML file.
**Timeline:** Implementable now.
**Target feel:** Like three-arena / three-fps demos.

### Architecture Changes
- **Upgrade Three.js** from r128 to r160+ (ES module from CDN)
  - Enables: `THREE.Octree` for proper collision
  - Enables: `EffectComposer` for post-processing
  - Enables: Better PBR materials, shadow quality
- **Add post-processing pipeline:** Bloom, FXAA, vignette, color grading
- **Add skybox:** 6-face cubemap (procedurally generated or from CDN)
- **Procedural textures on ALL surfaces:** Concrete, metal, rust, grime
- **Particle system:** Smoke trails, bullet sparks, blood splatter, debris

### Movement Overhaul (Quake/Source-style)
- Acceleration-based movement (not instant velocity)
- Air strafing (change direction mid-air)
- Bunny hopping (speed builds with well-timed jumps)
- Proper friction model (ground vs air)
- Slide momentum conservation
- Crouch-jump for extra height

### Map Design
- Multi-level architecture (2-3 floors with ramps/stairs)
- Interconnected rooms with sightlines and flanking routes
- Verticality: catwalks, bridges, elevated platforms with cover
- Distinct visual zones: industrial, tech, outdoor courtyard
- Jump pads for fast vertical traversal
- Teleporters between distant map areas

### Weapon Feel
- Weapon bob animation (sinusoidal with sprint modifier)
- Recoil recovery curves (not just instant snap)
- Bullet tracer improvements (thicker, with fade)
- Muzzle flash as 3D sprite (not just screen overlay)
- Shell casing ejection particles
- Rocket trail smoke particles

### Audio
- Recorded audio samples via base64-encoded WAV/OGG
- Weapon-specific fire sounds (not just procedural synthesis)
- Impact sounds (metal, concrete, flesh)
- Ambient environmental audio
- Spatial audio (3D positioned sounds)

### AI Improvements
- Pathfinding using navigation mesh (simplified)
- Bots use cover properly
- Bots jump pads and teleporters
- Difficulty affects reaction time, not just accuracy

---

## FPS Arena v3 — "The Engine Upgrade"

**Goal:** Near Venge.io quality.
**Timeline:** Requires dedicated development effort + build system.
**Target feel:** Like Venge.io / Fields of Fury.

### Engine Migration Options

#### Option A: PlayCanvas (Recommended)
- **Pros:** Full editor, physics (Ammo.js built-in), skeletal animation, asset pipeline, WebXR support
- **Cons:** Requires learning PlayCanvas editor, hosting on PlayCanvas or self-hosting
- **Example:** Venge.io, Fields of Fury
- **How:** Create project at playcanvas.com, import Mixamo characters, build map in editor

#### Option B: Babylon.js
- **Pros:** Microsoft-backed, excellent documentation, physics (Havok), PBR rendering
- **Cons:** Larger file size, steeper learning curve for FPS-specific features
- **Example:** Various demos on playground.babylonjs.com

#### Option C: Three.js + Build System
- **Pros:** Keep existing codebase, add GLTF loader, Ammo.js, post-processing
- **Cons:** Manual integration of every feature, no editor
- **How:** Migrate to Vite/Webpack build, npm packages, GLTF character models from Mixamo

### Required Assets for v3
- **Character models:** Mixamo (free) — soldier, terrorist, civilian variants
  - Idle, walk, run, jump, shoot, reload, die animations
  - Export as GLTF/GLB with draco compression
- **Weapon models:** Sketchfab (CC-licensed) or custom
  - First-person viewmodel + third-person world model
  - Animations: idle, fire, reload, inspect
- **Environment:** Modular kit pieces
  - Walls, floors, crates, barrels, vehicles, signs
  - PBR textures (albedo, normal, roughness, metalness)
- **Audio:** Freesound.org or similar
  - Weapon fire (per weapon), reload, impact, footsteps (per surface)
  - Ambient (indoor hum, outdoor wind), UI sounds

### v3 Feature List
- [ ] Skeletal animation for all characters (walk, run, shoot, reload, die)
- [ ] Physics engine (Ammo.js or Cannon-es) for proper collision + ragdoll
- [ ] GLTF model loading for characters, weapons, environment
- [ ] PBR materials with normal maps on all surfaces
- [ ] Real-time shadows (cascaded shadow maps)
- [ ] Post-processing: bloom, SSAO, TAA, tone mapping, motion blur
- [ ] Spatial audio with HRTF (Head-Related Transfer Function)
- [ ] Navigation mesh for AI pathfinding
- [ ] Skeletal animation blending (walk → run → shoot transitions)
- [ ] First-person weapon viewmodel with proper animation
- [ ] Decal system (bullet holes on walls, blood splatter)
- [ ] Destructible environment elements
- [ ] Killcam replay
- [ ] Spectator mode
- [ ] Server-authoritative multiplayer with lag compensation
- [ ] WebGPU renderer path (when browser support is stable)

---

## v4+ (Future Vision)

- **WebGPU renderer** for AAA-quality lighting (when Firefox/Safari support it)
- **WebXR** integration for VR headset play (already have VR infrastructure)
- **Map editor** in-browser for community content
- **Ranked matchmaking** with ELO system
- **Clan/team system** integrated with FavCreators accounts
- **Mobile touch controls** for phone play
- **WebAssembly** for performance-critical code (physics, AI)
- **Streaming assets** (load textures/models on demand vs inline)

---

## Tech Stack Comparison

| Feature | v1 (Current) | v2 (Polish) | v3 (Engine) | Venge.io |
|---------|-------------|-------------|-------------|----------|
| Engine | Three.js r128 | Three.js r160+ | PlayCanvas/Babylon | PlayCanvas |
| Physics | Custom AABB | Octree + custom | Ammo.js/Havok | Ammo.js |
| Characters | Box geometry | Improved geometry | GLTF + skeletal | GLTF + skeletal |
| Animation | None | Procedural | Skeletal blend tree | Skeletal blend tree |
| Textures | Flat colors | Procedural canvas | PBR (albedo+normal) | PBR full stack |
| Post-FX | None | Bloom + vignette | Full stack | Full stack |
| Audio | Procedural synth | Base64 samples | Spatial + HRTF | Full spatial |
| Map | Flat box arena | Multi-level | BSP/navmesh | Editor-built |
| AI | State machine | + pathfinding | Navmesh + behavior tree | Full AI |
| Build | Single HTML | Single HTML | Vite/Webpack bundle | PlayCanvas editor |
| File Size | ~235KB | ~300KB | ~5-20MB (with assets) | ~30MB+ |
