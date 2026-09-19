# KITTYBRAIN v0.1 — Spec (Phase 1: local scaffold + engine + tests)

Source: `PLAN.md` + `muse-vault/decisions.md` (2026-09-17 rulings).
Scope: Phases 1–2 (Phase 1 scaffold + §6 web UI addendum).
Hosting and token stay gated out.

## 1. Goal

A clean-room, stdlib-only observation terminal scaffold that computes
transparent moving-average observations over a price feed, journals them to
SQLite, and serves the last-80 as JSON — running locally with green tests.

## 2. Non-negotiables (from AGENTS.md + manager rulings)

- Rule engine + illustrative output only. No neural-net, connectome, or
  "AI prediction" claims anywhere, including code comments.
- Signals are observations, not financial advice. No profit language.
- Biological numbers (e.g. ~250M cat cortical neurons¹) are footnoted
  estimates of inspiration, never software capability.
- Clean-room code: no copied CROW/FLYBRAIN files (GPL respected).
- Python 3.11+ stdlib only. No pip deps, no API keys in showcase.
- Branding string `KITTYBRAIN` exists as ONE central placeholder constant
  (renamed from CATBRAIN 2026-09-18; still not final). Ticker UNDECIDED
  (MTG call).
- Bind 127.0.0.1 only. No hosting, token, wallet, spend, or push.

¹ Herculano-Houzel / Jardim-Messeder 2017 estimate; inspiration only.

## 3. Components

### 3.1 `cat/__init__.py` — brand constant

- `BRAND = "KITTYBRAIN"` — the single placeholder. Every user-visible
  brand string and the HTTP User-Agent derive from it.

### 3.2 `cat/engine.py` — observation engine (pure, deterministic)

- Inputs: `add_sample(price, ts)` with `price > 0`, `ts` seconds.
- Windows: fast MA5 vs slow MA20. Threshold ±0.30%.
- Warmup: first 19 samples return `None` (warming up); the 20th sample
  yields the first observation.
- Gap reset: if `ts - last_ts > 90s`, the buffer resets and warmup restarts.
  Explicit `reset()` does the same.
- Signal: `spread = (ma5 - ma20) / ma20`;
  `spread > +0.0030` → `positive`, `< -0.0030` → `negative`, else `neutral`.
  Exact ±0.30% is `neutral`.
- Activity scalar: `activity = min(1.0, abs(spread) * 30 + 0.12)` —
  idle glow 0.12 at rest so the point cloud never goes fully dead,
  saturating at 1.0 near a ~2.93% spread. Deterministic; drives the
  Phase 2 point cloud. (Ruling #8: dossier/CROW parity.)
- Observation dict keys: `price, ma_fast, ma_slow, spread, signal,
  activity, sample_count`.
- Invalid input (`price <= 0`, non-finite) raises `ValueError` loudly.

### 3.3 `cat/providers.py` — read-only DEX Screener pair adapter

- `fetch_pair_price(chain, pair_address, ...)` over HTTPS (stdlib urllib),
   User-Agent derived from `BRAND` (`KITTYBRAIN/0.1`).
- Strict match: response `chainId` must equal `chain` and `pairAddress`
  must equal the requested pair (case-insensitive); else `ProviderError`.
- Missing/unparseable `priceUsd` → `ProviderError`. Transport errors are
  wrapped in `ProviderError` with the cause visible.
- NO synthetic fallback: every failure raises. The app must surface the
  error, never invent a price.
- A pluggable fetcher keeps unit tests offline (no network in tests).

### 3.4 `cat/showcase.py` — deterministic showcase generator

- `generate_series(seed, n, start)` — seeded synthetic price walk.
  Same inputs → identical outputs, every run.
- Exports `MODE = "showcase"`, `ILLUSTRATIVE = True`, and a disclaimer
  stating the data is illustrative/synthetic and observations are not
  financial advice.

### 3.5 `app.py` — stdlib server + SQLite journal + JSON export

- `ThreadingHTTPServer` on 127.0.0.1 only (any non-loopback config value
  is clamped back to loopback with a stderr warning).
- SQLite journal `cat.sqlite3`, table `observations`: ts, price, ma_fast,
  ma_slow, spread, signal, activity, mode, source.
- Routes: `GET /` (minimal status page, showcase banner when illustrative),
  `GET /api/latest`, `GET /api/history?limit=N` (cap 80, default 80),
  `GET /api/status` (mode, warmup, last error — errors visible).
- Modes from `config.json`: `showcase` (seeded series, labeled illustrative
  in every response) or `live` (30s provider poll → engine → journal).
  Live with a blank/unverified pair refuses to poll and reports the error.
- Every JSON response carries `brand`, `mode`, and `illustrative`.

### 3.6 `config.json`, `start.sh`, `start.bat`

- Config: `mode`, `chain`, `pair` (blank until a verified pool exists —
  our pool only after launch), `second_market` blank until
  verified, `poll_seconds`, `showcase_seed`, `showcase_step_seconds`
  (seconds between showcase samples), `port`.
- `sample_count` counts accepted samples since construction/reset; the
  engine buffer itself is capped at the 20-sample slow window.
- Launchers run the local server; nothing exposes it publicly.

## 4. Tests (`tests/`, unittest, offline)

- Engine decisions: positive / negative / neutral incl. exact ±0.30%.
- Warmup: `None` until sample 20; `reset()`; 90s-gap auto-reset.
- Activity: bounds [0,1], formula spot-checks, determinism.
- Providers: strict chain/pair match, missing-price error, wrapped
  transport error — all via stub fetcher, zero network.
- Showcase: same seed → identical series; labeling constants present.
- App journal: record + last-N round-trip in temp DB; history cap 80.
- Gate: `python3 -m unittest discover -s tests -v` green.

## 5. Out of scope (Phase 3+ gates)

Public hosting/HTTPS, pump.fun token, rewards wallet, paper trading,
learning models, execution adapters.

## 6. Phase 2 addendum — web UI + concept art (2026-09-17)

- `app.py` serves `web/` statically (`/`, `/app.js`, `/cat.js`,
  `/style.css`, `/assets/*`) with traversal-proof `read_web_file`;
  unknown API paths 404 in-envelope. Missing `web/index.html` falls
  back to the minimal status page.
- `GET /api/radar` → one row for the tracked market (label, pool, price,
  signal, spread, activity); 1h change / 24h volume / liquidity are null
  with `unavailable_reason` — UI shows NO DATA, never zeros.
- `GET /api/events?limit=N` (cap 60) → real session events only, stages
  observe → evaluate → inspect, ring-capped, consecutive dupes skipped.
- `web/index.html` — radar table, decision panel (NO DATA / waiting /
  active + permanent "No order submitted"), live execution trace,
  honesty-engine sections (preregistered experiments, failure log,
  measured-vs-chosen, what-isn't-real), source explorer, mobile layout,
  pause-motion + `prefers-reduced-motion`.
- `web/cat.js` — vanilla-JS procedural cat-head point cloud (~700 pts,
  seeded), motion/brightness driven by engine activity (idle glow 0.12
  minimum). Labeled illustrative; not brain data.
- `web/assets/cat-concept.png` — original low-poly Blender render
  (placeholder-grade, labeled in UI); source `.blend` + headless script
  in `web/assets_src/`.

### 6.1 v0.3 volumetric activity graph (2026-09-18, ruling #10)

Supersedes the §6 flat point cloud: v0.2 read as a 2D cartoon outline
(~710 pts, near-zero depth) and failed the visual bar. The v0.3
`web/cat.js` (vanilla JS, no deps) renders a VOLUMETRIC graph:

- Nodes: exactly 2200 in 7 seeded-gaussian clusters (seed 20260918):
  4 cranium quadrants (420 each) clamped inside an ellipsoid cranium
  (radii 0.60/0.52/0.48 — depth the same order as width, NOT a flat
  layout), 1 midline lobe (200), 2 ear cones (160 each, stacked discs
  to an apex, full z-depth).
- Links: each node joins its 2 nearest neighbors within radius 0.14,
  deduped, capped at 5000 total; precomputed once per `init()` from
  the seeded layout, so the graph is deterministic across inits.
- Projection: yaw/pitch orbit + perspective divide; node size and
  alpha are depth-driven (near = larger/brighter); links drawn first
  in 3 faint depth buckets (alpha ≤ 0.20 per ruling #12). Muted lab
  palette, 3 region hues (cranium teal-slate, ear bone, lobe sage) on
  near-black.
- Firing subset: a per-frame deterministic fraction of nodes
  (`0.03 + 0.32·activity`, so ~3% at rest, ~35% at full activity) is
  drawn bright, chosen by a seeded (index, tick) hash — no
  `Math.random` in the draw path. Engine idle glow 0.12 floor kept.
- v0.2 interactions retained: drag/touch rotate, clamped zoom
  (0.5–2.5, pitch ±1.2), dblclick reset, idle drift yielding to first
  interaction + pause-motion + reduced-motion, one-line hint.
  `CatCloud` API keeps `getCamera`, adds `getStats()` (node/edge
  counts, firing count, tick, z-spread, layout hash).

Honesty note: the graph is an illustrative procedural drawing — seeded
decorative geometry, not brain data, not a brain model, and never a
neural net. UI copy and code comments must keep those labels.

### 6.2 v0.3.1 remediation (2026-09-18, ruling #12 build order)

Approved remediation of the Kimi audit, hold-on-fail gates unchanged:

- Brightness/density pass (verified by `.agents/audit/catjs_harness_density.py`
  sampled metrics, not code inspection): larger base nodes
  (`max(2.0, 2.6·dpr)`, size factor 0.7–1.5×depth), brighter non-firing
  floor (alpha 0.38 + 0.50·depth + act·0.25·shimmer), brighter firing subset
  (alpha 0.85 + 0.15·depth), link buckets 0.08/0.135/0.20 (cap 0.20),
  ear cones rebased inside the cranium shell (base y 0.34, h 0.46,
  r 0.17) so ears read attached at rest view, and the cloud fills ~99%
  of canvas height at zoom 1 (`CANVAS_FILL = 0.74`).
- Graph-first layout: the activity field is the hero visual, placed
  above the radar grid with an enlarged viewport (520 px CSS height);
  the concept-art card is visually secondary (narrower hero column,
  capped at 300 px). Hero lede trimmed. The activity readout carries a
  meaning hint: `activity X.XX / 1.00 — band`, bands `resting glow`
  (<0.25), `stirring` (<0.55), `bright` (≥0.55) — plain labels for the
  documented 0–1 scalar with its 0.12 idle-glow floor.
- Determinism kept (seed 20260918; re-init draws byte-identical frames;
  layout hash `fb3d83b3`), idle glow floor kept, all v0.2/v0.3
  interactions retained. Honesty labels untouched.

### 6.3 v0.3.2 full-body cartoon sprite (2026-09-18, MTG direction)

The hero mascot stops being head-only. The hand-coded inline SVG in
`web/index.html` (`#cat-sprite`, unchanged `0 0 240 240` viewBox, so the
hero card's rendered size and the mobile layout do not move) now draws a
full front-facing sitting cat: body (`#cat-body`: flanked sitting shape,
cream chest patch, front-leg seam lines), front paws (`#cat-paw-l`,
`#cat-paw-r` with toe lines), tail re-anchored at the body's right side
(`#cat-tail`, curl with darker tip), and the head regrouped into
`#cat-head` (ears, eyes, lids, nose, mouth, whiskers). Same palette and
style as the head-only sprite; honesty figcaption unchanged.

- Tap animations: 8 total. The 6 existing ones (blink, ear-twitch,
  bounce, wink, tail-swish, purr — 320–560ms) are retained on the new
  geometry; two body-level animations are added: `paw-wave` (480ms,
  `#cat-paw-r` lifts and tilts) and `loaf-squash` (540ms, `#cat-body`
  squashes toward the ground while `#cat-head` dips so the neck never
  shows a seam). Every tap still plays exactly one animation; the tap
  queue stays capped (QUEUE_CAP 3, serialized, drops at cap).
- Reduced-motion stays JS-blink-only. Bug fixed in the same pass: the
  JS previously set an inline transform on the `#cat-lids` GROUP, which
  could not override the stylesheet's `scaleY(0)` on the lid circles, so
  the reduced-motion blink was never visible (pre-existing defect). The
  JS now sets inline `scaleY(1)` on `#cat-lid-l`/`#cat-lid-r` directly
  (inline beats stylesheet) and clears it after 140ms. No CSS classes in
  the reduced-motion path.
- Activity glow unchanged (`#cat-halo` + `#cat-eyeglow` scale with the
  engine activity scalar).
- Harness regression coverage extended
  (`.agents/audit/catsprite_harness.py`): exactly 8 animations, coverage
  sequence maps all 8 random indices, reduced-motion asserts the inline
  lid override against a stubbed hidden state, CSS hooks must name their
  exact target selectors, geometry ids cross-checked against
  `index.html`, durations held to 300–600ms.
- Honesty: sprite + caption remain "illustrative, hand-coded, not a
  scientific reconstruction, not final branding". No new dependencies;
  vanilla SVG/CSS/JS.

### 6.4 v0.3.3 brand rename (2026-09-18, MTG feature order)

The brand placeholder is renamed `CATBRAIN` → `KITTYBRAIN`. The single
central constant (`BRAND` in `cat/__init__.py`) is the source; the HTTP
User-Agent, server header, startup log prefix, and every JSON envelope's
`brand` field all derive from it, plus the one-time text sweep of
`<title>`, header brand wordmark, hero lede, footer copy, file-header
comments, README title, launcher comments, and this spec. The repo
directory and file names are unchanged; ticker remains UNDECIDED (MTG
call). Honesty labels (`Placeholder name · ticker undecided`, no-AI /
no-wallet / NO DATA copy) are untouched.

### 6.5 v0.3.3 mood circuits (2026-09-18, MTG feature order)

A row of three buttons (`Normal | Fear | Hunt`) sits directly beneath the
graph; exactly one is active (`aria-pressed`), Normal on load.

- Graph (`web/cat.js`): Fear/Hunt highlight a seeded subset of exactly 15%
  of the 2200 nodes (330 each) as the "active circuit" — a bright red core
  (rgba 255/78/66, alpha 0.78+0.22·depth, 1.25× node size) plus a soft red
  halo (three layered alpha circles per node, 2.8×/1.9×/1.25× node size at
  alpha 0.05/0.10/0.17) so it reads as glow on near-black. Subsets come
  from ONE Fisher–Yates shuffle of all node indices with
  `mulberry32(SEED ^ 0xc11c17)` (same seed mechanism as the layout, salted
  independently): fear takes the first 330, hunt the next 330 — disjoint by
  construction, identical across frames and re-inits. Normal restores the
  existing palette. `CatCloud` gains `setMood`/`getMood`/`getCircuit`;
  `setMood` redraws immediately (pause/reduced-motion safe), unknown moods
  are ignored; `getStats()` adds `mood`, `circuit`, `circuitSize`.
- Hero (`web/moods.js` + inline SVG in `index.html`): Normal keeps the
  tappable mascot and its 8 animations untouched. Fear swaps it for a
  looped cartoon of a dog chasing the fleeing cat; Hunt for the cat
  chasing a mouse — both hand-coded inline SVG/CSS loops (no asset files),
  running until another mood is picked. Each scene is a complete composed
  frame: with `prefers-reduced-motion` the global motion-off rule freezes
  the loops and a "static frame" note is shown. The mascot caption swaps
  per mood and always carries the fiction label.
- Honesty (non-negotiable): the buttons carry an `illustrative fiction`
  group label, a note under them states that no real fear or hunt neurons
  are modeled and no neuroscience claim is made, the same sentence is in
  each swapped caption, and the "What isn't real" honesty panel lists the
  mood circuits as fiction. No brain-behavior, neuroscience, or prediction
  claim anywhere in the code or copy.
- Kept intact: orbit/zoom/reset, pause toggle and reduced-motion handling,
  sprite tap animations + queue cap, mobile layout, NO DATA rules, the
  layout hash (`fb3d83b3`), and all prior harness checks. New harness
  `.agents/audit/catmoods_harness.py` covers the mood state machine,
  subset determinism + disjointness + 330 sizing, glow batching, the hero
  swap per mood, and the reduced-motion static note. No new dependencies;
  vanilla JS/CSS/SVG only.

### 6.6 v0.3.4 mood-scene rewrite + Hunt-blue (2026-09-18, MTG direction)

Two refinements, manager-audited and cleared (suite 58/58, circuits 5/5):

- Hunt glow is BLUE (`[89,167,255]` core + same halo layers), Fear stays
  red (`[255,78,66]`) — per MTG. Copy updated everywhere (§6.5's
  "red core ... plus soft red halo" now reads red/blue per mood).
- Chase scenes rewritten direct (no shared `<defs>`/`<use>`): cross-SVG
  `<use href="#cbg-*">` references fail on the live page, and literal
  reuse of the front-facing mascot parts regressed (near-black body
  vanishes on the scene background). Consistency is via the mascot's
  EXACT palette + flat-vector hand, geometry pose-correct: side-profile
  running cats (tan body, cream belly, taupe stripes, amber eye, pink
  nose/inner-ear) — Fear: dog (brightened tan, floppy ear, collar + tag)
  pursues the wide-eyed fleeing cat; Hunt: the cat stalks a distinct
   gray-blue mouse (round ears, thin S-tail). Both scenes add speed lines,
   dust puffs, and seamless-loop run-cycle legs; reduced-motion still
   freezes a composed static frame. Fear ≈6.7KB / Hunt ≈5.7KB inline SVG,
   no asset files, honesty/fiction labels untouched.

### 6.7 v0.3.5 Fear-scene rebalance (2026-09-18, MTG direction)

The Fear chase scene is rebalanced so the pursuer reads as the threat: the
fleeing cat is scaled to 0.77 of its §6.6 size (`translate(150 144)
scale(0.77)`, feet re-planted on the same ground line, identical mascot
palette/stripes/amber eye/fleeing pose), and the dog is recolored GREY —
cool mid-grey body `#9aa3ad`, darker grey legs `#6e767f` and floppy ear
`#5b636c`, light grey belly/snout `#c9ced4` — keeping the pink collar
`#c1666b` and gold tag `#d9a441` for readability on the near-black panel
(≈7:1 body contrast). This supersedes §6.6's "brightened tan" dog note.
Chase order is unchanged (dog behind-left, cat ahead-right, both moving
right); the cat's dust puffs shift to its new heel line; ground dashes and
speed lines are untouched. Reduced-motion static frame, honesty
caption/fiction label, and all harness checks remain intact.

### 6.8 v0.3.6 Fear-scene tail/face collision fix (2026-09-18, MTG direction)

The fleeing cat's tail overlapped the dog's face (MTG report, verified:
at the −12° wag extreme the streaming tail tip swept deep into the dog
head disk). Micro-fix, scene-local: the cat tail is shortened and
re-curved upright (`M-36 -6 C -40 -16 -40 -30 -36 -42` + dark tip
`M-37 -28 C -38 -34 -37 -39 -36 -42`, same mascot-palette strokes and
9px width, wag pivot unchanged) so it reads as a scared upright tail,
and the dog translate is nudged left 64→52. Worst-case tail-to-face
clearance across the full −12°..+14° wag sweep is ≈2.8 scene-px (vs.
nose dot); ≈6.9 scene-px on the frozen reduced-motion frame. Everything
else frozen: 0.77 cat scale, grey dog palette, collar + tag, chase order,
ground dashes, speed lines, dust, loop timing, caption + fiction labels,
§6.5–6.7 honesty text. Verified: suite 58/58, node --check ×4,
catmoods harness green, and raster previews
(`.agents/audit/previews/fear-tail-fix-{rest,wag}.svg.png`) show clean
separation at rest and at the deepest wag frame with no new overlaps.
