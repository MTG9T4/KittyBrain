# KittyBrain

Experimental cat-brain market observation terminal. Illustrative signals, not financial advice.

Rule-based signal engine (MA5 vs MA20 moving averages) with a cartoon-mascot showcase UI.
No neural net, no connectome, no wallet connection, no auto-trading. Inspired by
CROWBRAIN (`sopersone/CROWBRAIN`) and the fly-brain connectome work — clean-room code,
no GPL copying (MIT licensed).

## Run (local showcase)

```
python3 app.py
# → http://127.0.0.1:8000
```

Tests: `python3 -m unittest discover -s tests -v` (58 green).

Live mode is read-only public market data with strict pair matching; with a blank
pair it reports an error and never polls. Blank until our own pool is verified
after launch — never pointed at anything unverified.

## Honest framing

- Biological neuron counts (cat cortex ~250M, Herculano-Houzel 2017) are inspiration
  with a cited source — never this software's capability.
- Signals are observations, not financial advice. No profitability claims anywhere.

## Links

- Site: https://kittybrain.fyi (wiring in progress)
- X: https://x.com/MTG9T4
- Coin: TBD — created by owner at launch, links added then.

## Docs

- `PLAN.md` — build + launch plan
- `SPEC.md` — formal spec
- `SOURCES.md` — reference sources and what each teaches
