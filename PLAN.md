# CATBRAIN — Full Plan (v0.1 → token → beyond)

Goal: ship a CrowBrain-equivalent "3D cat brain" observation terminal, host it publicly, and launch a CATBRAIN token on pump.fun so trading fees flow to us as creator rewards.

Status: RESEARCH COMPLETE. No code written, nothing launched, no money spent. Awaiting MTG's go-ahead (see CHECKLIST.md).

## 1. What we're building (v0.1)

A clean-room rebuild of CROW v0.1, reskinned to cat:

- `cat/engine.py` — same transparent MA rule (fast-5 vs slow-20, ±0.30% threshold, 20-sample warmup, activity score). Keep identical for parity; tune only after paper-trading data.
- `cat/providers.py` — same read-only DEX Screener adapter (strict pair match, visible errors, no fake fallback).
- `app.py` — same stdlib-only server + SQLite journal + JSON export, renamed (User-Agent `CATBRAIN/0.1`, DB `cat.sqlite3`).
- `web/` — same layout, new skin: low-poly cat concept art, cat-head/brain point cloud driven by `activity`, chart, journal, source explorer, mobile + reduced-motion support.
- `config.json` — Solana pair configured (our token's pool AFTER launch; starter pool before that), second market configurable but blank until verified (same honesty as CROW's Robinhood slot).
- Modes: Showcase (deterministic, labeled illustrative, works offline) + Live · DEX Screener (30s poll, ~10 min warmup, 90s-gap reset).

Explicitly OUT of v0.1: wallets, auto-trading, trained neural nets, real connectome data, profitability claims, Robinhood-chain claims we can't verify.

## 2. The cat-brain story (honest, cited)

- Headline number: ~250M cortical neurons (Herculano-Houzel / Jardim-Messeder 2017, Frontiers in Neuroanatomy — dogs ~530M, cats ~250M, humans ~16B). Always footnoted: biological estimate, not software capability — same pattern as crowbrain.live.
- Site copy mirrors CROWBRAIN's arc: "Inside the cat's mind" → radar → execution trace → flight plan → source. Original art + procedural geometry, never presented as a scientific reconstruction.
- Fly connectome (166k neurons / 125M synapses) + fly-brain LIF repo stay as "research shelf" narrative, not v0.1 tech.

## 3. Hosting (public site)

v0.1 runs on 127.0.0.1 only — do NOT expose the dev server directly.
- Fast path: Railway / Render / Fly.io (persistent Python process + disk for SQLite, env-driven port, custom domain + HTTPS).
- Control path: cheap VPS (Hetzner/DigitalOcean) + Caddy or Nginx reverse proxy + systemd + HTTPS + backups.
- Not suitable: Vercel/Netlify serverless (kills the persistent loop + SQLite model).
- Domain + HTTPS before sharing the link anywhere; UptimeKuma-style checks after.

## 4. Token launch + creator rewards (the money loop, verified vs pump.fun docs May 2026)

- Create coin: free. Graduation to PumpSwap: 0.015 SOL.
- Bonding curve: every trade costs 1.25% total → creator gets 0.30%, protocol 0.95%.
- Graduated canonical PumpSwap pool: first tier (0–420 SOL mcap) still 0.30% to creator; then creator cut PEAKS at 0.95% (420–1470 SOL mcap, total fee 1.20%) and tapers tier-by-tier down to 0.05% at 98,240+ SOL mcap. Non-canonical pools pay creator 0%.
- USDC-paired tokens have a parallel tier table (same shape, USDC thresholds).
- Rewards accrue automatically on-chain to the creator wallet; claim anytime via profile → Creator rewards → Claim all (gas only, no minimum). The wallet that creates the coin IS the fee recipient — create from the wallet we control and back up. Fees can change without notice; rewards scale with volume and are never guaranteed.
- Launch order: finalize branding/site/repo → create token from the rewards wallet → verify DEX Screener pair → point site's `config.json` at our pool → announce with live radar showing our own token.

## 5. Roadmap

- v0.1 (now): reskin + parity, local demo, tests green.
- v0.1-public: hosted, HTTPS, our-token pair live, showcase video.
- v0.2: persistent history, paper positions, fees/slippage, baseline comparisons (CROW's stated "Measure & learn").
- v0.3+: evaluate a documented learning model only after baselines exist; optional execution adapters only after simulation + explicit wallet setup (CROW's "Controlled execution").
- Research shelf: fly-brain LIF experiments on the RTX/GPU lane, separate repo, GPL respected.

## 6. Risks (say them plainly)

- Signals are observations, not advice; no profitability; memecoin volume is volatile — rewards may be near zero.
- Never imply Solana/Robinhood endorsement; never present art as science; pick a repo license before inviting reuse; keep `data/` + secrets out of git.
- Token launch is irreversible and public — ticker, art, and copy must be final before creating the coin.

## 7. What happens after MTG says go

See CHECKLIST.md — branding decisions first, then scaffold, then demo, then host, then token. One gate at a time, hold-on-fail like MTG likes.
