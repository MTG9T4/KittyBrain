"""Engine decision, warmup, and reset tests (SPEC §3.2). Offline."""
import unittest

from cat import BRAND
from cat import engine


def feed(eng, prices, start_ts=0.0, step=1.0):
    out = None
    for i, price in enumerate(prices):
        out = eng.add_sample(price, start_ts + i * step)
    return out


class BrandTest(unittest.TestCase):
    def test_single_placeholder_constant(self):
        self.assertEqual(BRAND, "KITTYBRAIN")
        self.assertFalse(hasattr(engine, "USER_AGENT_BRAND"))


class ClassifyTest(unittest.TestCase):
    def test_exact_positive_boundary_is_neutral(self):
        self.assertEqual(engine.classify_spread(0.003), engine.SIGNAL_NEUTRAL)

    def test_exact_negative_boundary_is_neutral(self):
        self.assertEqual(engine.classify_spread(-0.003), engine.SIGNAL_NEUTRAL)

    def test_just_above_threshold_is_positive(self):
        self.assertEqual(engine.classify_spread(0.0030001), engine.SIGNAL_POSITIVE)

    def test_just_below_threshold_is_negative(self):
        self.assertEqual(engine.classify_spread(-0.0030001), engine.SIGNAL_NEGATIVE)

    def test_zero_is_neutral(self):
        self.assertEqual(engine.classify_spread(0.0), engine.SIGNAL_NEUTRAL)


class ActivityTest(unittest.TestCase):
    def test_zero_spread_has_idle_glow(self):
        self.assertEqual(engine.activity_from_spread(0.0), 0.12)

    def test_formula_spot_check(self):
        self.assertAlmostEqual(engine.activity_from_spread(0.01), 0.42)
        self.assertAlmostEqual(engine.activity_from_spread(-0.01), 0.42)

    def test_saturates_at_one(self):
        self.assertEqual(engine.activity_from_spread(0.03), 1.0)
        self.assertEqual(engine.activity_from_spread(0.50), 1.0)
        self.assertEqual(engine.activity_from_spread(-0.50), 1.0)


class WarmupTest(unittest.TestCase):
    def test_none_until_sample_20(self):
        eng = engine.ObservationEngine()
        for i in range(19):
            self.assertIsNone(eng.add_sample(100.0, float(i)))
        self.assertTrue(eng.status()["warming_up"])
        obs = eng.add_sample(100.0, 19.0)
        self.assertIsNotNone(obs)
        self.assertFalse(eng.status()["warming_up"])
        self.assertEqual(obs["sample_count"], 20)

    def test_status_counts(self):
        eng = engine.ObservationEngine()
        self.assertEqual(eng.status()["sample_count"], 0)
        self.assertEqual(eng.status()["needed"], 20)
        eng.add_sample(100.0, 0.0)
        self.assertEqual(eng.status()["sample_count"], 1)


class DecisionTest(unittest.TestCase):
    def test_flat_series_is_neutral(self):
        eng = engine.ObservationEngine()
        obs = feed(eng, [100.0] * 20)
        self.assertEqual(obs["signal"], engine.SIGNAL_NEUTRAL)
        self.assertAlmostEqual(obs["spread"], 0.0)
        self.assertEqual(obs["activity"], 0.12)
        self.assertAlmostEqual(obs["ma_fast"], 100.0)
        self.assertAlmostEqual(obs["ma_slow"], 100.0)

    def test_step_up_is_positive(self):
        eng = engine.ObservationEngine()
        obs = feed(eng, [100.0] * 15 + [101.0] * 5)
        self.assertAlmostEqual(obs["ma_fast"], 101.0)
        self.assertAlmostEqual(obs["ma_slow"], 100.25)
        self.assertGreater(obs["spread"], 0.003)
        self.assertEqual(obs["signal"], engine.SIGNAL_POSITIVE)
        self.assertGreater(obs["activity"], 0.0)

    def test_step_down_is_negative(self):
        eng = engine.ObservationEngine()
        obs = feed(eng, [100.0] * 15 + [99.0] * 5)
        self.assertLess(obs["spread"], -0.003)
        self.assertEqual(obs["signal"], engine.SIGNAL_NEGATIVE)

    def test_small_drift_stays_neutral(self):
        eng = engine.ObservationEngine()
        obs = feed(eng, [100.0] * 15 + [100.1] * 5)
        self.assertEqual(obs["signal"], engine.SIGNAL_NEUTRAL)

    def test_deterministic(self):
        first = feed(engine.ObservationEngine(), [100.0] * 15 + [101.0] * 5)
        second = feed(engine.ObservationEngine(), [100.0] * 15 + [101.0] * 5)
        self.assertEqual(first, second)

    def test_long_run_bounded_buffer_monotonic_count(self):
        eng = engine.ObservationEngine()
        obs = feed(eng, [100.0] * 60)
        self.assertEqual(obs["sample_count"], 60)
        self.assertLessEqual(len(eng._samples), engine.SLOW_WINDOW)
        self.assertEqual(obs["signal"], engine.SIGNAL_NEUTRAL)


class ResetTest(unittest.TestCase):
    def test_explicit_reset_restarts_warmup(self):
        eng = engine.ObservationEngine()
        feed(eng, [100.0] * 20)
        self.assertFalse(eng.status()["warming_up"])
        eng.reset()
        self.assertTrue(eng.status()["warming_up"])
        self.assertIsNone(eng.add_sample(100.0, 1000.0))
        self.assertEqual(eng.status()["sample_count"], 1)

    def test_gap_over_90s_auto_resets(self):
        eng = engine.ObservationEngine()
        feed(eng, [100.0] * 20, start_ts=0.0)
        self.assertFalse(eng.status()["warming_up"])
        self.assertIsNone(eng.add_sample(100.0, 19.0 + 91.0))
        self.assertTrue(eng.status()["warming_up"])
        self.assertEqual(eng.status()["sample_count"], 1)

    def test_gap_of_exactly_90s_keeps_buffer(self):
        eng = engine.ObservationEngine()
        feed(eng, [100.0] * 20, start_ts=0.0)
        obs = eng.add_sample(100.0, 19.0 + 90.0)
        self.assertIsNotNone(obs)


class InvalidInputTest(unittest.TestCase):
    def test_bad_prices_raise(self):
        eng = engine.ObservationEngine()
        for bad in (0.0, -1.0, float("nan"), float("inf")):
            with self.assertRaises(ValueError, msg=repr(bad)):
                eng.add_sample(bad, 0.0)

    def test_bad_timestamp_raises(self):
        eng = engine.ObservationEngine()
        for bad in (float("nan"), float("inf")):
            with self.assertRaises(ValueError, msg=repr(bad)):
                eng.add_sample(100.0, bad)


if __name__ == "__main__":
    unittest.main()
