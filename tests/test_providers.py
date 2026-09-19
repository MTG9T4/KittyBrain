"""Provider strict-match and visible-error tests (SPEC §3.3). Offline."""
import unittest

from cat import BRAND
from cat import providers


def stub(payload=None, error=None, capture=None):
    def run(url, timeout):
        if capture is not None:
            capture.append((url, timeout))
        if error is not None:
            raise error
        return payload

    return run


GOOD = {"chainId": "solana", "pairAddress": "AbC123", "priceUsd": "12.50"}


class FetchTest(unittest.TestCase):
    def test_pair_shape_happy_path(self):
        capture = []
        quote = providers.fetch_pair_price(
            "solana", "abc123", fetcher=stub({"pair": dict(GOOD)}, capture=capture)
        )
        self.assertAlmostEqual(quote["price_usd"], 12.50)
        self.assertEqual(quote["chain"], "solana")
        self.assertIn("solana", capture[0][0])
        self.assertIn("abc123", capture[0][0])

    def test_pairs_shape_picks_strict_match(self):
        payload = {
            "pairs": [
                {"chainId": "ethereum", "pairAddress": "abc123", "priceUsd": "1.0"},
                dict(GOOD),
            ]
        }
        quote = providers.fetch_pair_price("solana", "ABC123", fetcher=stub(payload))
        self.assertAlmostEqual(quote["price_usd"], 12.50)

    def test_chain_mismatch_raises(self):
        payload = {"pair": dict(GOOD, chainId="ethereum")}
        with self.assertRaises(providers.ProviderError):
            providers.fetch_pair_price("solana", "abc123", fetcher=stub(payload))

    def test_pair_mismatch_raises(self):
        payload = {"pair": dict(GOOD, pairAddress="zzz999")}
        with self.assertRaises(providers.ProviderError):
            providers.fetch_pair_price("solana", "abc123", fetcher=stub(payload))

    def test_empty_pairs_raises(self):
        with self.assertRaises(providers.ProviderError):
            providers.fetch_pair_price("solana", "abc123", fetcher=stub({"pairs": []}))

    def test_missing_pair_key_raises(self):
        with self.assertRaises(providers.ProviderError):
            providers.fetch_pair_price("solana", "abc123", fetcher=stub({}))

    def test_missing_price_raises(self):
        bad = dict(GOOD)
        del bad["priceUsd"]
        with self.assertRaises(providers.ProviderError):
            providers.fetch_pair_price("solana", "abc123", fetcher=stub({"pair": bad}))

    def test_bad_price_raises(self):
        for bad_price in ("abc", "0", "-2", "", "nan", "inf", "-inf"):
            payload = {"pair": dict(GOOD, priceUsd=bad_price)}
            with self.assertRaises(providers.ProviderError, msg=repr(bad_price)):
                providers.fetch_pair_price("solana", "abc123", fetcher=stub(payload))

    def test_transport_error_wrapped_and_visible(self):
        with self.assertRaises(providers.ProviderError) as ctx:
            providers.fetch_pair_price(
                "solana", "abc123", fetcher=stub(error=RuntimeError("boom-7"))
            )
        self.assertIn("boom-7", str(ctx.exception))

    def test_user_agent_derives_from_brand(self):
        self.assertEqual(providers.USER_AGENT, "%s/0.1" % BRAND)


if __name__ == "__main__":
    unittest.main()
