# CATBRAIN — Sources (all 5 understood)

## 1. https://crowbrain.live/#engine

What it is: marketing + live demo site for CROWBRAIN.
- Hero: "Inside the crow's mind. 1.5 billion neurons." with honest footnote: biological estimate, not software neuron count (links to a MEDACF bulletin).
- Positions as watcher of Solana + Robinhood Chain tokens, turning market data into inspectable signals.
- Core UX blocks: brain explorer (drag rotate, scroll zoom, double-click reset, illustrative activity), token select → decision panel (NO DATA / waiting states, "No order submitted"), market radar table (price, 1h change, volume 24h, liquidity, signal), live execution trace (Observe → Evaluate → Make it inspectable, actual session events, executing rule with highlighted line), flight plan (Observe & explore → Measure & learn → Controlled execution), source link to GitHub.
- Takeaway for CATBRAIN: copy this page structure beat-for-beat, swapped to cat framing.

## 2. https://pump.fun/coin/BjHCvuKDisEXg7DnaKztVs3YGEszfd9PqQK4Q7VWpump

What it is: the live CrowBrain token page on pump.fun.
- Shows bonding-curve → graduation mechanics, creator wallet (2JxPmU…), market cap, stats (5m/1h/24h), "Rewards → creator" routing.
- Takeaway: the money loop is creator fees on every trade, routed to the wallet that created the coin. Our token must be created from the wallet we want paid. Verified fee math is in `reference/pumpfun-creator-fees.md` (pump.fun docs, May 2026).

## 3. Google Research blog — male fruit fly connectome (Sep 2026)

- 166,000+ neurons, 125M synapses, largest proofread brain map to date (HHMI Janelia + Google). Complements female maps; enables courtship/aggression/vision/taste research. Methods: EM slices → flood-filling nets → PATHFINDER → human proofreading. Next: zebrafish, mouse.
- Takeaway: narrative fuel ("real brain mapping is happening") + a hard boundary: we are NOT doing connectomics. CROW's honesty ("does not reproduce a crow's biological brain") is the template. The eons fly-brain repo is the "later research phase," never v0.1.

## 4. https://github.com/eonsystemspbc/fly-brain (GPL-2.0-or-later)

- Whole-brain LIF model from FlyWire (~138k neurons, ~5M synapses). Activate/silence neurons, watch spike propagation. Entrypoint `main.py` → `code/benchmark.py` → backends (Brian2 CPU/CUDA, PyTorch CUDA, NEST GPU, GeNN, Brian2GeNN). Ground truth = Brian2 CPU (Shiu et al., 91% vs experimental data). Data: FlyWire v783 (3.2MB csv + 97MB parquet). Needs Linux + NVIDIA CUDA 12.x + conda; NEST GPU from source.
- Takeaway: real neural simulation is heavy GPU science — Phase 2+ curiosity only. v0.1 stays with CROW's 20-line moving-average rule. Do NOT copy GPL code into a closed build; keep any future fly-brain experiments in a separate repo with license intact.

## 5. https://github.com/sopersone/CROWBRAIN (v0.1, 28 stars / 10 forks, Sep 15 2026)

The direct template. Fully read (README + `app.py` + `crow/engine.py` + `crow/providers.py` + `config.json`):

- Zero-dependency Python 3.11 stdlib server (`app.py`, ThreadingHTTPServer on 127.0.0.1:8000). No pip, no Node, no API keys for showcase mode.
- `crow/engine.py` — the whole signal rule (verified):
  - need ≥20 samples or WAIT ("Collecting samples: n/20")
  - fast = mean(last 5), slow = mean(last 20), spread = fast/slow − 1
  - spread > +0.003 → BUY, < −0.003 → SELL, else WAIT; activity = min(1, |spread|*30 + .12)
- `crow/providers.py` — read-only DEX Screener adapter: GET `https://api.dexscreener.com/latest/dex/pairs/{chain}/{pair}`, 10s timeout, 2MB cap, strict chainId+pairAddress match, returns USD price + base symbol. No synthetic fallback — errors surface in UI, signals pause.
- Loop: showcase ticks every 3s (deterministic sine-wave prices, labeled illustrative); live polls every 30s; 20 live samples (~10 min) before first real decision; mode/market switch resets window; >90s feed gap resets window; journal = SQLite `signals` table, export latest 80 as JSON.
- `config.json`: `{solana: {chain_id: "solana", pair_address: "58oQ…LYQo2"}, robinhood: {chain_id: "robinhood", pair_address: ""}}` — chain_id is the provider string, pair_address is the DEX pool (not mint). Robinhood side intentionally blank/unverified.
- Frontend `web/`: point-cloud crow driven by engine `activity`, chart, journal, source explorer, mobile layout, pause-motion + reduced-motion support. Security: same-origin POST check, CSP headers, no-store.
- Tests: `python -m unittest discover -s tests -v`. License: none selected yet (owner must choose before reuse).

Verified 2026-09-17 via raw file reads. Full engine + provider logic is captured above — enough to reimplement clean-room as CAT without copying files.
