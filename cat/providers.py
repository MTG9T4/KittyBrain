"""Read-only DEX Screener pair adapter (clean-room, stdlib only).

Strict pair/chain match with visible errors. There is deliberately NO
synthetic fallback: every failure raises ProviderError so the app can
surface it instead of inventing a price.
"""

import json
import math
import urllib.error
import urllib.request

from cat import BRAND

USER_AGENT = "%s/0.1" % BRAND
API_URL = "https://api.dexscreener.com/latest/dex/pairs/{chain}/{pair}"
TIMEOUT_SECONDS = 15


class ProviderError(Exception):
    """The quote could not be obtained or verified. Never hide this."""


def _http_get_json(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise ProviderError("DEX Screener request failed: %s" % exc) from exc


def _candidates(payload):
    if not isinstance(payload, dict):
        raise ProviderError("unexpected API payload shape: %r" % type(payload))
    if isinstance(payload.get("pair"), dict):
        return [payload["pair"]]
    pairs = payload.get("pairs")
    if isinstance(pairs, list):
        return [p for p in pairs if isinstance(p, dict)]
    raise ProviderError("API payload has neither 'pair' nor 'pairs'")


def fetch_pair_price(chain, pair_address, fetcher=None, timeout=TIMEOUT_SECONDS):
    """Fetch and strictly verify one pair quote.

    Returns {"chain", "pair", "price_usd"}. Raises ProviderError on any
    mismatch, missing price, or transport failure. `fetcher` is an
    injectable (url, timeout) -> parsed-JSON callable for offline tests.
    """
    if not chain or not pair_address:
        raise ProviderError("chain and pair_address are both required")
    url = API_URL.format(chain=chain, pair=pair_address)
    get = fetcher if fetcher is not None else _http_get_json
    try:
        payload = get(url, timeout)
    except ProviderError:
        raise
    except Exception as exc:  # visible, never synthetic
        raise ProviderError("DEX Screener request failed: %s" % exc) from exc

    want_chain = str(chain).lower()
    want_pair = str(pair_address).lower()
    for item in _candidates(payload):
        got_chain = str(item.get("chainId", "")).lower()
        got_pair = str(item.get("pairAddress", "")).lower()
        if got_chain != want_chain or got_pair != want_pair:
            continue
        raw_price = item.get("priceUsd")
        try:
            price = float(raw_price)
        except (TypeError, ValueError):
            price = -1.0
        if not math.isfinite(price) or price <= 0:
            raise ProviderError(
                "pair %s has no usable priceUsd: %r" % (pair_address, raw_price)
            )
        return {"chain": chain, "pair": pair_address, "price_usd": price}
    raise ProviderError(
        "no pair matching chain=%r pair=%r in API response" % (chain, pair_address)
    )
